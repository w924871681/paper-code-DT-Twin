# -*- coding: utf-8 -*-
from __future__ import annotations

import gc
import json
import math
import os
import random
import shutil
import time
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from configs.methods.source_prior_bank_cfg import CFG, config_dict
from core.methods.ours.paper_engine import _load_prior_model
from core.methods.ours.stage2_runtime import (
    candidate_backend_context,
    candidate_device,
    synchronize_if_cuda,
)
from core.space import build_model, profile_arch
from shared.data_access import get_support_validation_check
from shared.evaluation.common import (
    atomic_json,
    build_runtime,
    eval_metrics,
    feasible_indices,
    file_sha256,
    load_frozen_assets,
    load_json,
    seed_all,
)


def _atomic_torch_save(obj: Any, path: str) -> None:
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.{time.time_ns()}.tmp"
    torch.save(obj, tmp)
    os.replace(tmp, path)


def _case_jobs(smoke: bool = False) -> List[Tuple[int, int, int]]:
    start, count, _offset = CFG.fresh_pool
    jobs = [
        (cid, H, K)
        for cid in range(start, start + count)
        for H in CFG.H_list
        for K in CFG.K_list
    ]
    return jobs[:2] if smoke else jobs


def _load_external_source_manifest(project_root: str) -> Dict[str, Any]:
    path = os.path.join(project_root, CFG.external_source_manifest)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing frozen source manifest: {path}")
    obj = load_json(path)
    if obj.get("decision") != CFG.expected_source_decision:
        raise RuntimeError("Frozen PT source assets are not PASS")
    if obj.get("test_used") or obj.get("target_pool_used") or obj.get("validation_pool_k_used"):
        raise RuntimeError("Frozen PT source assets contain target/Pool-K/Test use")
    for item in obj.get("assets", {}).values():
        full = os.path.join(
            project_root,
            str(item["path"]).replace("\\", os.sep).replace("/", os.sep),
        )
        if not os.path.isfile(full):
            raise FileNotFoundError(f"Missing frozen source asset: {full}")
        if file_sha256(full).lower() != str(item["sha256"]).lower():
            raise RuntimeError(f"Frozen source asset hash mismatch: {full}")
    return obj


def _frozen_pt_anchor_asset(
    project_root: str,
    manifest: Mapping[str, Any],
    *,
    H: int,
) -> Tuple[str, str]:
    paths: List[Tuple[str, str]] = []
    for tier in ("tight", "medium", "loose"):
        bb = manifest["fixed_backbones"][f"h{H}_b{tier}"]
        if int(bb["arch_idx"]) != CFG.anchor_arch_idx:
            raise RuntimeError(
                f"Frozen PT anchor drift for H={H}, tier={tier}: "
                f"A{bb['arch_idx']} != A{CFG.anchor_arch_idx}"
            )
        item = manifest["assets"][f"pt_ft_h{H}_b{tier}"]
        full = os.path.join(
            project_root,
            str(item["path"]).replace("\\", os.sep).replace("/", os.sep),
        )
        paths.append((os.path.abspath(full), str(item["sha256"]).lower()))
    if len(set(paths)) != 1:
        raise RuntimeError(f"PT-A57 asset is not identical across tiers for H={H}")
    return paths[0]


def _derive_c30_compact_set(oracle: Mapping[str, Any]) -> Dict[str, Any]:
    check_wins: Counter = Counter()
    validation_positive_wins: Counter = Counter()
    for rec in oracle.get("records", {}).values():
        summary = rec["summary"]
        pt_check = float(summary["pt_anchor_D1"]["check"]["weighted_mse"])
        best_check = summary["c1_check_oracle"]
        if float(best_check["check"]["weighted_mse"]) < pt_check:
            check_wins[int(best_check["arch_idx"])] += 1
        if (
            str(summary["union_validation_selected_source"]) == "C1_ARCH_CANDIDATE"
            and float(summary["union_validation_selected_check_mse"]) < pt_check
        ):
            validation_positive_wins[
                int(summary["union_validation_selected_arch_idx"])
            ] += 1
    selected = sorted(
        idx
        for idx in set(check_wins) | set(validation_positive_wins)
        if check_wins[idx] >= CFG.candidate_rule_min_wins
        or validation_positive_wins[idx] >= CFG.candidate_rule_min_wins
    )
    return {
        "selected": selected,
        "check_true_win_counts": {
            str(k): int(v) for k, v in sorted(check_wins.items())
        },
        "validation_positive_win_counts": {
            str(k): int(v) for k, v in sorted(validation_positive_wins.items())
        },
        "rule": (
            f"check_true_wins>={CFG.candidate_rule_min_wins} OR "
            f"validation_positive_wins>={CFG.candidate_rule_min_wins}"
        ),
    }


def preflight(project_root: str, out_path: str) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    paths = {
        "c30_preflight": os.path.join(root, CFG.c30_preflight_path),
        "c30_fixed": os.path.join(root, CFG.c30_fixed_path),
        "c30_oracle": os.path.join(root, CFG.c30_oracle_path),
        "c30_analysis": os.path.join(root, CFG.c30_analysis_path),
        "c30_audit": os.path.join(root, CFG.c30_audit_path),
        "external_source_manifest": os.path.join(root, CFG.external_source_manifest),
        "c1_bank": os.path.join(root, CFG.c1_bank_path),
    }
    checks: Dict[str, bool] = {
        f"{name}_exists": os.path.isfile(path) for name, path in paths.items()
    }
    derived: Dict[str, Any] = {}
    overlap: List[int] = []

    start, count, _offset = CFG.fresh_pool
    fresh_ids = set(range(start, start + count))
    for lo, hi in CFG.known_used_center_ranges:
        overlap.extend(sorted(fresh_ids.intersection(range(lo, hi + 1))))

    if all(checks.values()):
        c30_audit = load_json(paths["c30_audit"])
        c30_analysis = load_json(paths["c30_analysis"])
        c30_oracle = load_json(paths["c30_oracle"])
        source_manifest = _load_external_source_manifest(root)
        derived = _derive_c30_compact_set(c30_oracle)

        checks.update(
            {
                "c30_audit_pass": (
                    c30_audit.get("decision") == CFG.expected_c30_audit_decision
                ),
                "c30_analysis_allows_source_prior_bank": (
                    c30_analysis.get("decision")
                    in set(CFG.accepted_c30_analysis_decisions)
                ),
                "c30_fixed_hash_bound": (
                    file_sha256(paths["c30_fixed"]).lower()
                    == str(c30_audit.get("fixed_sha256", "")).lower()
                ),
                "c30_oracle_hash_bound": (
                    file_sha256(paths["c30_oracle"]).lower()
                    == str(c30_audit.get("oracle_sha256", "")).lower()
                ),
                "c30_analysis_hash_bound": (
                    file_sha256(paths["c30_analysis"]).lower()
                    == str(c30_audit.get("analysis_sha256", "")).lower()
                ),
                "compact_set_deterministic": (
                    tuple(derived.get("selected", ()))
                    == tuple(CFG.compact_arch_indices)
                ),
                "anchor_in_compact_set": (
                    CFG.anchor_arch_idx in CFG.compact_arch_indices
                ),
                "non_anchor_set_exact": (
                    tuple(
                        x
                        for x in CFG.compact_arch_indices
                        if x != CFG.anchor_arch_idx
                    )
                    == tuple(CFG.compact_non_anchor_indices)
                ),
                "fresh_pool_no_known_overlap": len(overlap) == 0,
                "fresh_pool_count": len(fresh_ids) == count,
                "source_assets_pass": (
                    source_manifest.get("decision")
                    == CFG.expected_source_decision
                ),
                "source_assets_target_unused": not bool(
                    source_manifest.get("target_pool_used")
                    or source_manifest.get("validation_pool_k_used")
                    or source_manifest.get("check_pool_k_used")
                    or source_manifest.get("test_used")
                ),
                "c1_bank_hash_bound": (
                    file_sha256(paths["c1_bank"]).lower()
                    == CFG.c1_bank_sha256.lower()
                ),
                "anchor_A57": CFG.anchor_arch_idx == 57,
                "target_steps_50": CFG.target_steps == 50,
                "switch_margin_frozen": 0.0 < CFG.switch_margin_rel < 0.10,
            }
        )

    decision = (
        "PASS_SOURCE_PRIOR_BANK_PREFLIGHT_READY"
        if checks and all(checks.values())
        else "FAIL_SOURCE_PRIOR_BANK_PREFLIGHT"
    )
    obj = {
        "study": "c3_1_compact_preflight",
        "decision": decision,
        "protocol": config_dict(),
        "paths": paths,
        "checks": checks,
        "derived_candidate_evidence": derived,
        "fresh_pool_overlap": overlap,
        "historical_pool_k_reused": False,
        "test_used": False,
    }
    atomic_json(obj, out_path)
    return obj


def _iter_source_batches(
    cfg: Any,
    cache: Any,
    *,
    H: int,
    batch_size: int,
    epoch: int,
) -> Iterable[Tuple[torch.Tensor, torch.Tensor]]:
    rng = random.Random(CFG.train_seed + 10007 * int(H) + int(epoch))
    centers = list(range(CFG.source_centers))
    rng.shuffle(centers)
    for cid in centers:
        Xs, ys, Xv, yv, *_ = get_support_validation_check(
            cfg, cache, cid, H, max(CFG.K_list)
        )
        X = torch.cat([Xs, Xv], dim=0)
        y = torch.cat([ys, yv], dim=0)
        gen = torch.Generator(device=X.device)
        gen.manual_seed(
            CFG.train_seed + 101 * int(H) + 1009 * int(cid) + int(epoch)
        )
        order = torch.randperm(
            int(X.shape[0]), generator=gen, device=X.device
        )
        for left in range(0, int(X.shape[0]), int(batch_size)):
            idx = order[left : left + int(batch_size)]
            yield X.index_select(0, idx), y.index_select(0, idx)


def _asset_record(path: str, project_root: str, **extra: Any) -> Dict[str, Any]:
    return {
        "path": os.path.relpath(path, project_root).replace("\\", "/"),
        "sha256": file_sha256(path),
        **extra,
    }


def build_strong_bank(
    project_root: str,
    out_dir: str,
    device: str,
    safe_mode: str,
    smoke: bool = False,
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    preflight_path = os.path.join(root, CFG.output_root, "preflight", "source_prior_bank_preflight.json")
    if not os.path.isfile(preflight_path):
        raise FileNotFoundError("Run source-prior-bank evaluation preflight first")
    if load_json(preflight_path).get("decision") != "PASS_SOURCE_PRIOR_BANK_PREFLIGHT_READY":
        raise RuntimeError("source-prior-bank evaluation preflight is not PASS")

    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    manifest_path = os.path.join(out_dir, "source_prior_bank_manifest.json")

    cfg, cache, A, requested, safe = build_runtime(device, safe_mode, ())
    if len(A) != CFG.architecture_count:
        raise RuntimeError("Architecture-space mismatch")
    L = int(cfg.main.task.L)
    X0, *_ = get_support_validation_check(
        cfg, cache, 0, CFG.H_list[0], max(CFG.K_list)
    )
    input_dim = int(X0.shape[-1])
    source_manifest = _load_external_source_manifest(root)

    run_mode = "smoke" if smoke else "formal"
    manifest: Dict[str, Any]
    if os.path.isfile(manifest_path):
        manifest = load_json(manifest_path)
        if manifest.get("protocol", {}).get("protocol_version") != CFG.protocol_version:
            raise RuntimeError("Existing source-prior-bank evaluation bank manifest has a different protocol")
        if str(manifest.get("run_mode")) != run_mode:
            raise RuntimeError(
                "Smoke/formal outputs cannot share one directory. "
                "Delete outputs/source_prior_bank_d2904_t2904 before the formal run."
            )
    else:
        manifest = {
            "study": "c3_1_compact_strong_source_bank",
            "decision": "SOURCE_PRIOR_BANK_STRONG_BANK_IN_PROGRESS",
            "run_mode": run_mode,
            "protocol": config_dict(),
            "source_centers": list(range(CFG.source_centers)),
            "candidate_arch_indices": list(CFG.compact_arch_indices),
            "source_recipe": {
                "optimizer": "Adam",
                "loss": "MSE",
                "epochs": 1 if smoke else CFG.source_epochs,
                "lr": CFG.source_lr,
                "batch_size": CFG.source_batch_size,
                "weight_decay": CFG.source_weight_decay,
                "source_data": "support_plus_validation_K20",
            },
            "assets": {},
            "target_pool_used": False,
            "historical_pool_k_used": False,
            "test_used": False,
        }

    epochs = 1 if smoke else CFG.source_epochs
    jobs = [
        (int(H), int(idx))
        for H in CFG.H_list
        for idx in CFG.compact_arch_indices
    ]
    started = time.perf_counter()
    completed_before = len(manifest.get("assets", {}))
    completed_now = 0

    for job_no, (H, idx) in enumerate(jobs, 1):
        spec = A[idx]
        key = f"h{H}_a{idx}"
        out_file = os.path.join(out_dir, f"strong_h{H}_a{idx}.pt")

        existing = manifest.get("assets", {}).get(key)
        if (
            existing
            and os.path.isfile(out_file)
            and file_sha256(out_file).lower()
            == str(existing.get("sha256", "")).lower()
        ):
            continue

        if idx == CFG.anchor_arch_idx:
            source_path, source_hash = _frozen_pt_anchor_asset(
                root, source_manifest, H=H
            )
            shutil.copy2(source_path, out_file)
            if file_sha256(out_file).lower() != source_hash.lower():
                raise RuntimeError("Copied PT-A57 anchor hash mismatch")
            manifest["assets"][key] = _asset_record(
                out_file,
                root,
                H=H,
                arch_idx=idx,
                arch_key=str(spec.arch_key),
                family=str(spec.family),
                provenance="exact_frozen_PT_A57_copy",
                original_sha256=source_hash,
                epochs_completed=CFG.source_epochs,
            )
        else:
            actual = candidate_device(spec, requested, safe)
            checkpoint = out_file + ".progress.pt"
            with candidate_backend_context(spec, actual, safe):
                seed = CFG.train_seed + 101 * H + idx
                seed_all(seed, actual)
                model = build_model(
                    spec,
                    input_dim=input_dim,
                    H=H,
                    L=L,
                    device=str(actual),
                )
                opt = optim.Adam(
                    model.parameters(),
                    lr=CFG.source_lr,
                    weight_decay=CFG.source_weight_decay,
                )
                start_epoch = 0
                if os.path.isfile(checkpoint):
                    state = torch.load(checkpoint, map_location=actual)
                    model.load_state_dict(state["model"], strict=True)
                    opt.load_state_dict(state["optimizer"])
                    start_epoch = int(state.get("next_epoch", 0))
                    print(
                        f"[source-prior-bank evaluation][Bank] resume H={H} A={idx} "
                        f"next_epoch={start_epoch}",
                        flush=True,
                    )

                train_started = time.perf_counter()
                last_loss = None
                for epoch in range(start_epoch, epochs):
                    losses: List[float] = []
                    for Xb, yb in _iter_source_batches(
                        cfg,
                        cache,
                        H=H,
                        batch_size=CFG.source_batch_size,
                        epoch=epoch,
                    ):
                        model.train()
                        opt.zero_grad(set_to_none=True)
                        pred = model(Xb.to(actual).contiguous())
                        loss = ((pred - yb.to(actual).contiguous()) ** 2).mean()
                        if not torch.isfinite(loss):
                            raise RuntimeError(
                                f"Non-finite source loss H={H} A={idx}"
                            )
                        loss.backward()
                        opt.step()
                        losses.append(float(loss.detach().item()))
                    last_loss = float(np.mean(losses))
                    _atomic_torch_save(
                        {
                            "model": {
                                k: v.detach().cpu()
                                for k, v in model.state_dict().items()
                            },
                            "optimizer": opt.state_dict(),
                            "next_epoch": int(epoch + 1),
                        },
                        checkpoint,
                    )
                    elapsed = time.perf_counter() - train_started
                    done_epochs = max(1, epoch - start_epoch + 1)
                    eta = (
                        elapsed / done_epochs
                        * max(0, epochs - epoch - 1)
                    )
                    print(
                        f"[source-prior-bank evaluation][Bank] job={job_no}/{len(jobs)} "
                        f"H={H} A={idx} {spec.arch_key} "
                        f"epoch={epoch+1}/{epochs} loss={last_loss:.6g} "
                        f"elapsed={elapsed/3600:.2f}h eta={eta/3600:.2f}h",
                        flush=True,
                    )
                synchronize_if_cuda(actual)
                _atomic_torch_save(
                    {
                        k: v.detach().cpu()
                        for k, v in model.state_dict().items()
                    },
                    out_file,
                )
                if os.path.isfile(checkpoint):
                    os.remove(checkpoint)
                del model, opt
            params, flops = profile_arch(
                spec, L=L, input_dim=input_dim, H=H
            )
            manifest["assets"][key] = _asset_record(
                out_file,
                root,
                H=H,
                arch_idx=idx,
                arch_key=str(spec.arch_key),
                family=str(spec.family),
                provenance="PT_recipe_source_only_rebuild",
                epochs_completed=epochs,
                final_source_loss=last_loss,
                params=float(params),
                flops=float(flops),
            )

        completed_now += 1
        manifest["completed_assets"] = len(manifest["assets"])
        manifest["expected_assets"] = len(jobs)
        atomic_json(manifest, manifest_path)
        elapsed = time.perf_counter() - started
        done = completed_before + completed_now
        remaining = max(0, len(jobs) - done)
        avg = elapsed / max(1, completed_now)
        eta = avg * remaining
        finish = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(time.time() + eta)
        )
        print(
            f"[source-prior-bank evaluation][Bank] assets={done}/{len(jobs)} "
            f"elapsed={elapsed/3600:.2f}h avg={avg:.1f}s "
            f"eta={eta/3600:.2f}h finish={finish}",
            flush=True,
        )
        gc.collect()
        if requested.type == "cuda":
            torch.cuda.empty_cache()

    # Re-verify every asset before freezing the manifest.
    for key, item in manifest["assets"].items():
        full = os.path.join(root, str(item["path"]).replace("/", os.sep))
        if not os.path.isfile(full):
            raise FileNotFoundError(f"Missing source-prior-bank evaluation strong asset: {full}")
        if file_sha256(full).lower() != str(item["sha256"]).lower():
            raise RuntimeError(f"source-prior-bank evaluation strong asset hash mismatch: {full}")
    if len(manifest["assets"]) != len(jobs):
        raise RuntimeError(
            f"source-prior-bank evaluation strong bank incomplete: "
            f"{len(manifest['assets'])}/{len(jobs)}"
        )
    manifest["decision"] = "PASS_SOURCE_PRIOR_BANK_STRONG_BANK_FROZEN"
    manifest["asset_count"] = len(manifest["assets"])
    manifest["manifest_frozen_at_unix_s"] = time.time()
    atomic_json(manifest, manifest_path)
    return manifest


def _load_strong_manifest(
    project_root: str, manifest_path: str
) -> Dict[str, Any]:
    obj = load_json(manifest_path)
    if obj.get("decision") != "PASS_SOURCE_PRIOR_BANK_STRONG_BANK_FROZEN":
        raise RuntimeError("source-prior-bank evaluation strong bank is not frozen PASS")
    if obj.get("target_pool_used") or obj.get("historical_pool_k_used") or obj.get("test_used"):
        raise RuntimeError("source-prior-bank evaluation strong bank contains forbidden data use")
    for item in obj.get("assets", {}).values():
        full = os.path.join(
            project_root,
            str(item["path"]).replace("\\", os.sep).replace("/", os.sep),
        )
        if not os.path.isfile(full):
            raise FileNotFoundError(f"Missing source-prior-bank evaluation strong asset: {full}")
        if file_sha256(full).lower() != str(item["sha256"]).lower():
            raise RuntimeError(f"source-prior-bank evaluation strong asset hash mismatch: {full}")
    return obj


def _load_strong_model(
    project_root: str,
    manifest: Mapping[str, Any],
    A: Sequence[Any],
    *,
    H: int,
    idx: int,
    input_dim: int,
    L: int,
    device: torch.device,
) -> nn.Module:
    item = manifest["assets"][f"h{H}_a{idx}"]
    if int(item["arch_idx"]) != int(idx):
        raise RuntimeError("Strong-bank architecture index mismatch")
    path = os.path.join(
        project_root,
        str(item["path"]).replace("\\", os.sep).replace("/", os.sep),
    )
    model = build_model(
        A[idx], input_dim=input_dim, H=H, L=L, device=str(device)
    )
    state = torch.load(path, map_location=device)
    model.load_state_dict(state, strict=True)
    return model


def _adapt_sgd_mse(
    model: nn.Module,
    Xs: torch.Tensor,
    ys: torch.Tensor,
    *,
    seed: int,
) -> None:
    dev = next(model.parameters()).device
    seed_all(seed, dev)
    model.train()
    opt = optim.SGD(model.parameters(), lr=CFG.target_lr)
    Xd = Xs.to(dev).contiguous()
    yd = ys.to(dev).contiguous()
    for _ in range(CFG.target_steps):
        opt.zero_grad(set_to_none=True)
        loss = ((model(Xd) - yd) ** 2).mean()
        if not torch.isfinite(loss):
            raise RuntimeError("Non-finite target SGD/MSE loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            model.parameters(), CFG.target_grad_clip
        )
        opt.step()


def _evaluate(model: nn.Module, Xv, yv, Xc, yc) -> Dict[str, Any]:
    return {
        "validation": eval_metrics(model, Xv, yv),
        "check": eval_metrics(model, Xc, yc),
    }


def _select_with_anchor_margin(
    rows: Sequence[Mapping[str, Any]],
    *,
    anchor_source: str,
    margin_rel: float,
) -> Dict[str, Any]:
    anchors = [r for r in rows if str(r["source"]) == anchor_source]
    if len(anchors) != 1:
        raise RuntimeError("Exactly one PT anchor row is required")
    anchor = anchors[0]
    alternatives = [r for r in rows if r is not anchor]
    best_alt = (
        min(
            alternatives,
            key=lambda r: (
                float(r["validation"]["weighted_mse"]),
                float(r["params"]),
                float(r["flops"]),
                int(r["arch_idx"]),
                str(r["source"]),
            ),
        )
        if alternatives
        else None
    )
    anchor_val = float(anchor["validation"]["weighted_mse"])
    threshold = anchor_val * (1.0 - float(margin_rel))
    if (
        best_alt is not None
        and float(best_alt["validation"]["weighted_mse"]) <= threshold
    ):
        selected = best_alt
        switched = True
    else:
        selected = anchor
        switched = False
    return {
        "source": str(selected["source"]),
        "arch_idx": int(selected["arch_idx"]),
        "arch_key": str(selected["arch_key"]),
        "family": str(selected["family"]),
        "validation": selected["validation"],
        "check": selected["check"],
        "switched_from_pt_anchor": bool(switched),
        "margin_rel": float(margin_rel),
        "anchor_validation_mse": anchor_val,
        "switch_threshold_validation_mse": threshold,
        "best_alternative_validation_mse": (
            None
            if best_alt is None
            else float(best_alt["validation"]["weighted_mse"])
        ),
    }


def _check_oracle(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    best = min(
        rows,
        key=lambda r: (
            float(r["check"]["weighted_mse"]),
            float(r["params"]),
            float(r["flops"]),
            int(r["arch_idx"]),
            str(r["source"]),
        ),
    )
    return {
        "source": str(best["source"]),
        "arch_idx": int(best["arch_idx"]),
        "arch_key": str(best["arch_key"]),
        "family": str(best["family"]),
        "validation": best["validation"],
        "check": best["check"],
        "non_deployable": True,
    }


def run_fresh_holdout(
    project_root: str,
    bank_manifest_path: str,
    out_path: str,
    device: str,
    safe_mode: str,
    smoke: bool = False,
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    strong_manifest = _load_strong_manifest(root, bank_manifest_path)
    run_mode = "smoke" if smoke else "formal"
    if str(strong_manifest.get("run_mode")) != run_mode:
        raise RuntimeError(
            "Smoke/formal bank and holdout modes do not match. "
            "Delete the Smoke output before the formal run."
        )
    start, count, offset = CFG.fresh_pool
    cfg, cache, A, requested, safe = build_runtime(
        device, safe_mode, ((start, count, offset),)
    )
    frozen = load_frozen_assets(root)
    L = int(cfg.main.task.L)
    jobs = _case_jobs(smoke)

    out_path = os.path.abspath(out_path)
    result = (
        load_json(out_path)
        if os.path.isfile(out_path)
        else {
            "study": "c3_1_fresh_anchor_protected_compact_holdout",
            "decision": "SOURCE_PRIOR_BANK_HOLDOUT_IN_PROGRESS",
            "run_mode": run_mode,
            "protocol": config_dict(),
            "bank_manifest": os.path.abspath(bank_manifest_path),
            "bank_manifest_sha256": file_sha256(bank_manifest_path),
            "records": {},
            "selection_frozen_before_check": True,
            "primary_selector": (
                "PT-A57 anchor protection with relative validation "
                f"margin={CFG.switch_margin_rel}"
            ),
            "check_oracle_is_non_deployable": True,
            "historical_pool_k_reused": False,
            "test_used": False,
        }
    )
    if str(result.get("run_mode")) != run_mode:
        raise RuntimeError(
            "Smoke/formal holdout outputs cannot share one result file."
        )
    if (
        result.get("bank_manifest_sha256")
        and result["bank_manifest_sha256"]
        != file_sha256(bank_manifest_path)
    ):
        raise RuntimeError("Strong-bank manifest changed after holdout began")

    records = dict(result.get("records", {}))
    global_started = time.perf_counter()
    total_expected = 0
    for cid, H, K in jobs:
        Xs, *_rest, tier, _ctype = get_support_validation_check(
            cfg, cache, cid, H, K
        )
        feasible = set(
            feasible_indices(cfg, A, tier, L, int(Xs.shape[-1]), H)
        )
        if CFG.anchor_arch_idx not in feasible:
            raise RuntimeError(f"PT-A57 infeasible for c{cid}_h{H}_k{K}")
        total_expected += 2  # PT-A57 and legacy C1-A57.
        total_expected += sum(
            1 for idx in CFG.compact_non_anchor_indices if idx in feasible
        )

    completed_before = sum(
        len(r.get("candidates", {})) for r in records.values()
    )
    newly_done = 0

    for case_no, (cid, H, K) in enumerate(jobs, 1):
        case_started = time.perf_counter()
        Xs, ys, Xv, yv, Xc, yc, tier, ctype = (
            get_support_validation_check(cfg, cache, cid, H, K)
        )
        input_dim = int(Xs.shape[-1])
        feasible = set(
            feasible_indices(cfg, A, tier, L, input_dim, H)
        )
        case_key = f"c{cid}_h{H}_k{K}_b{tier}"
        rec = dict(records.get(case_key, {}))
        rec.update(
            {
                "case_key": case_key,
                "center_id": int(cid),
                "center_type": str(ctype),
                "budget_tier": str(tier),
                "H": int(H),
                "K": int(K),
                "hard_feasible_compact_indices": [
                    int(i)
                    for i in CFG.compact_arch_indices
                    if i in feasible
                ],
                "test_used": False,
            }
        )
        candidates = dict(rec.get("candidates", {}))
        seed0 = CFG.train_seed + 1009 * cid + 37 * H + 53 * K

        planned: List[Tuple[str, int, str]] = [
            ("PT_A57", CFG.anchor_arch_idx, "strong"),
            ("LEGACY_C1_A57", CFG.anchor_arch_idx, "c1"),
        ]
        planned.extend(
            ("STRONG_COMPACT", int(idx), "strong")
            for idx in CFG.compact_non_anchor_indices
            if idx in feasible
        )

        for candidate_no, (source, idx, loader) in enumerate(planned, 1):
            token = f"{source}_A{idx}"
            if token in candidates and candidates[token].get("complete"):
                continue
            spec = A[idx]
            actual = candidate_device(spec, requested, safe)
            cand_started = time.perf_counter()
            with candidate_backend_context(spec, actual, safe):
                if loader == "c1":
                    model, _prior = _load_prior_model(
                        spec=spec,
                        H=H,
                        L=L,
                        input_dim=input_dim,
                        bank=frozen["bank"],
                        device=actual,
                    )
                else:
                    model = _load_strong_model(
                        root,
                        strong_manifest,
                        A,
                        H=H,
                        idx=idx,
                        input_dim=input_dim,
                        L=L,
                        device=actual,
                    )
                # Same seed for the two A57 initializations.
                target_seed = seed0 + 101 * idx
                _adapt_sgd_mse(model, Xs, ys, seed=target_seed)
                metrics = _evaluate(model, Xv, yv, Xc, yc)
                synchronize_if_cuda(actual)
                del model

            params, flops = profile_arch(
                spec, L=L, input_dim=input_dim, H=H
            )
            candidates[token] = {
                "token": token,
                "source": source,
                "arch_idx": int(idx),
                "arch_key": str(spec.arch_key),
                "family": str(spec.family),
                "params": float(params),
                "flops": float(flops),
                **metrics,
                "target_seed": int(target_seed),
                "target_steps": CFG.target_steps,
                "complete": True,
                "elapsed_seconds": float(
                    time.perf_counter() - cand_started
                ),
            }
            rec["candidates"] = candidates
            rec["complete"] = False
            records[case_key] = rec
            result["records"] = records
            newly_done += 1
            result["completed_candidate_count"] = (
                completed_before + newly_done
            )
            result["expected_candidate_count"] = total_expected
            result["completed_gradient_steps"] = (
                (completed_before + newly_done) * CFG.target_steps
            )
            atomic_json(result, out_path)

            elapsed = time.perf_counter() - global_started
            done = completed_before + newly_done
            remaining = max(0, total_expected - done)
            avg = elapsed / max(1, newly_done)
            eta = avg * remaining
            finish = time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(time.time() + eta),
            )
            print(
                f"[source-prior-bank evaluation][Holdout] case={case_no}/{len(jobs)} "
                f"candidate={candidate_no}/{len(planned)} "
                f"{case_key} {token} done={done}/{total_expected} "
                f"steps={done*CFG.target_steps} "
                f"case_elapsed={(time.perf_counter()-case_started):.1f}s "
                f"elapsed={elapsed/3600:.2f}h avg={avg:.1f}s "
                f"eta={eta/3600:.2f}h finish={finish}",
                flush=True,
            )
            gc.collect()
            if requested.type == "cuda":
                torch.cuda.empty_cache()

        rows = list(candidates.values())
        if len(rows) != len(planned):
            raise RuntimeError(
                f"Candidate completeness mismatch for {case_key}: "
                f"{len(rows)}/{len(planned)}"
            )
        pt_rows = [r for r in rows if r["source"] == "PT_A57"]
        c1_rows = [r for r in rows if r["source"] == "LEGACY_C1_A57"]
        if len(pt_rows) != 1 or len(c1_rows) != 1:
            raise RuntimeError("A57 source rows are incomplete")

        dual_rows = pt_rows + c1_rows
        rec["summary"] = {
            "pt_anchor": pt_rows[0],
            "legacy_c1_a57": c1_rows[0],
            "dual_a57_margin_selected": _select_with_anchor_margin(
                dual_rows,
                anchor_source="PT_A57",
                margin_rel=CFG.switch_margin_rel,
            ),
            "compact_margin_selected": _select_with_anchor_margin(
                rows,
                anchor_source="PT_A57",
                margin_rel=CFG.switch_margin_rel,
            ),
            "compact_zero_margin_diagnostic": _select_with_anchor_margin(
                rows,
                anchor_source="PT_A57",
                margin_rel=0.0,
            ),
            "compact_check_oracle": _check_oracle(rows),
        }
        rec["complete"] = True
        rec["elapsed_seconds"] = float(time.perf_counter() - case_started)
        records[case_key] = rec
        result["records"] = records
        result["N_records"] = len(records)
        result["expected_records"] = len(jobs)
        result["complete"] = (
            len(records) == len(jobs)
            and all(bool(r.get("complete")) for r in records.values())
        )
        atomic_json(result, out_path)

    result["decision"] = (
        "SOURCE_PRIOR_BANK_FRESH_HOLDOUT_COMPLETE"
        if result.get("complete")
        else "SOURCE_PRIOR_BANK_FRESH_HOLDOUT_INCOMPLETE"
    )
    atomic_json(result, out_path)
    return result


def _relative_gain(new: float, ref: float) -> float:
    return float(
        (float(ref) - float(new))
        / (abs(float(ref)) + CFG.eps)
    )


def _center_bootstrap(
    values_by_center: Mapping[int, Sequence[float]], seed: int
) -> Dict[str, Any]:
    centers = sorted(values_by_center)
    arr = np.asarray(
        [np.mean(values_by_center[c]) for c in centers], dtype=float
    )
    if arr.size == 0:
        return {
            "mean": None,
            "median": None,
            "ci_low": None,
            "ci_high": None,
            "n_centers": 0,
        }
    rng = np.random.default_rng(int(seed))
    ids = rng.integers(
        0,
        len(arr),
        size=(CFG.bootstrap_repeats, len(arr)),
    )
    boot = arr[ids].mean(axis=1)
    return {
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "ci_low": float(np.quantile(boot, 0.025)),
        "ci_high": float(np.quantile(boot, 0.975)),
        "n_centers": int(len(arr)),
    }


def _summary_mse(rec: Mapping[str, Any], key: str) -> float:
    return float(rec["summary"][key]["check"]["weighted_mse"])


def _gain_comparison(
    records: Mapping[str, Any],
    selected_key: str,
    seed: int,
) -> Dict[str, Any]:
    by_center: Dict[int, List[float]] = defaultdict(list)
    raw: List[float] = []
    for rec in records.values():
        new = _summary_mse(rec, selected_key)
        ref = _summary_mse(rec, "pt_anchor")
        gain = _relative_gain(new, ref)
        raw.append(gain)
        by_center[int(rec["center_id"])].append(gain)
    out = _center_bootstrap(by_center, seed)
    out.update(
        {
            "N_cases": len(raw),
            "case_mean": float(np.mean(raw)),
            "positive_case_rate": float(np.mean(np.asarray(raw) > 0)),
        }
    )
    return out


def _architecture_increment(
    records: Mapping[str, Any], seed: int
) -> Dict[str, Any]:
    by_center: Dict[int, List[float]] = defaultdict(list)
    raw: List[float] = []
    for rec in records.values():
        pt = _summary_mse(rec, "pt_anchor")
        dual = _summary_mse(rec, "dual_a57_margin_selected")
        compact = _summary_mse(rec, "compact_margin_selected")
        value = float((dual - compact) / (abs(pt) + CFG.eps))
        raw.append(value)
        by_center[int(rec["center_id"])].append(value)
    out = _center_bootstrap(by_center, seed)
    out.update(
        {
            "definition": "(dual_A57_check - compact_check) / PT_A57_check",
            "N_cases": len(raw),
            "case_mean": float(np.mean(raw)),
            "positive_case_rate": float(np.mean(np.asarray(raw) > 0)),
        }
    )
    return out


def analyze(
    project_root: str,
    holdout_path: str,
    out_path: str,
) -> Dict[str, Any]:
    holdout = load_json(holdout_path)
    if not holdout.get("complete"):
        raise RuntimeError("source-prior-bank evaluation fresh holdout is incomplete")
    records = holdout["records"]

    comparisons = {
        "dual_A57_margin_over_PT": _gain_comparison(
            records,
            "dual_a57_margin_selected",
            CFG.train_seed + 1,
        ),
        "compact_margin_over_PT": _gain_comparison(
            records,
            "compact_margin_selected",
            CFG.train_seed + 2,
        ),
        "compact_zero_margin_over_PT": _gain_comparison(
            records,
            "compact_zero_margin_diagnostic",
            CFG.train_seed + 3,
        ),
        "compact_check_oracle_over_PT": _gain_comparison(
            records,
            "compact_check_oracle",
            CFG.train_seed + 4,
        ),
        "architecture_increment_over_dual_A57": _architecture_increment(
            records, CFG.train_seed + 5
        ),
    }

    switched = []
    harmful = []
    non_anchor = []
    non_anchor_positive = []
    selected_sources: Counter = Counter()
    selected_arches: Counter = Counter()
    by_group: Dict[str, Dict[str, List[float]]] = {
        "H": defaultdict(list),
        "K": defaultdict(list),
        "budget_tier": defaultdict(list),
        "center_type": defaultdict(list),
    }

    for rec in records.values():
        summary = rec["summary"]
        pt = float(summary["pt_anchor"]["check"]["weighted_mse"])
        selected = summary["compact_margin_selected"]
        mse = float(selected["check"]["weighted_mse"])
        gain = _relative_gain(mse, pt)
        is_switched = bool(selected["switched_from_pt_anchor"])
        is_harmful = is_switched and mse > pt
        is_non_anchor = (
            is_switched
            and int(selected["arch_idx"]) != CFG.anchor_arch_idx
        )
        switched.append(is_switched)
        harmful.append(is_harmful)
        non_anchor.append(is_non_anchor)
        non_anchor_positive.append(is_non_anchor and mse < pt)
        selected_sources[str(selected["source"])] += 1
        selected_arches[int(selected["arch_idx"])] += 1

        by_group["H"][str(rec["H"])].append(gain)
        by_group["K"][str(rec["K"])].append(gain)
        by_group["budget_tier"][str(rec["budget_tier"])].append(gain)
        by_group["center_type"][str(rec["center_type"])].append(gain)

    group_summary = {
        axis: {
            key: {
                "N_cases": len(values),
                "case_mean_gain": float(np.mean(values)),
                "positive_case_rate": float(
                    np.mean(np.asarray(values) > 0)
                ),
            }
            for key, values in groups.items()
        }
        for axis, groups in by_group.items()
    }

    primary = comparisons["compact_margin_over_PT"]
    arch_inc = comparisons["architecture_increment_over_dual_A57"]
    oracle = comparisons["compact_check_oracle_over_PT"]
    harmful_rate = float(np.mean(harmful))

    primary_pass = (
        primary["mean"] >= CFG.primary_gain_mean
        and primary["ci_low"] > CFG.primary_gain_ci_low
        and harmful_rate <= CFG.harmful_switch_rate_max
    )
    architecture_pass = (
        arch_inc["mean"] >= CFG.architecture_increment_mean
        and arch_inc["ci_low"] > CFG.architecture_increment_ci_low
    )
    oracle_pass = (
        oracle["mean"] >= CFG.oracle_headroom_mean
        and oracle["ci_low"] > CFG.oracle_headroom_ci_low
    )

    if primary_pass and architecture_pass:
        decision = "PROCEED_LIMITED_C3_COMPACT_ONLY"
        next_step = (
            "Freeze the six-architecture strong bank and the anchor-protected "
            "selector. Do not reopen the 66-architecture search."
        )
    elif oracle_pass and not primary_pass:
        decision = "REVISE_VALIDATION_SELECTOR_ONLY"
        next_step = (
            "The strong compact bank contains Check headroom, but the frozen "
            "Validation rule does not realize it safely. Keep the bank fixed "
            "and improve only the selector on a separate development pool."
        )
    elif primary_pass and not architecture_pass:
        decision = "STOP_COMPLEX_ARCH_SEARCH_KEEP_A57_SOURCE_SELECTION"
        next_step = (
            "The primary method is safe, but non-A57 structures add less than "
            "the pre-registered threshold over dual A57. Stop architecture "
            "search and retain PT-A57 / legacy-C1-A57 source selection only."
        )
    else:
        decision = "STOP_COMPLEX_ARCH_SEARCH_FIXED_PT_A57"
        next_step = (
            "Neither deployable compact selection nor Check Oracle provides "
            "sufficient fresh-pool headroom. Retain fixed PT-A57."
        )

    result = {
        "study": "c3_1_compact_analysis",
        "decision": decision,
        "recommended_next_step": next_step,
        "protocol": config_dict(),
        "holdout_sha256": file_sha256(holdout_path),
        "comparisons": comparisons,
        "selection_safety": {
            "switch_rate": float(np.mean(switched)),
            "harmful_switch_rate_all_cases": harmful_rate,
            "harmful_switch_count": int(sum(harmful)),
            "non_anchor_switch_rate": float(np.mean(non_anchor)),
            "non_anchor_positive_count": int(sum(non_anchor_positive)),
            "selected_sources": dict(selected_sources),
            "selected_arch_indices": {
                str(k): int(v) for k, v in selected_arches.items()
            },
        },
        "group_summary": group_summary,
        "gates": {
            "primary_gain_pass": bool(primary_pass),
            "architecture_increment_pass": bool(architecture_pass),
            "oracle_headroom_pass": bool(oracle_pass),
            "historical_pool_k_unused": True,
            "test_unused": True,
        },
        "test_used": False,
    }
    atomic_json(result, out_path)
    return result


def audit(
    project_root: str,
    preflight_path: str,
    bank_manifest_path: str,
    holdout_path: str,
    analysis_path: str,
    out_path: str,
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    preflight_obj = load_json(preflight_path)
    bank = _load_strong_manifest(root, bank_manifest_path)
    holdout = load_json(holdout_path)
    analysis_obj = load_json(analysis_path)

    start, count, _offset = CFG.fresh_pool
    expected_cases = count * len(CFG.H_list) * len(CFG.K_list)
    expected_assets = len(CFG.H_list) * len(CFG.compact_arch_indices)

    candidate_complete = True
    selector_reproducible = True
    for rec in holdout.get("records", {}).values():
        candidates = list(rec.get("candidates", {}).values())
        feasible = set(rec.get("hard_feasible_compact_indices", []))
        expected = 2 + sum(
            1
            for idx in CFG.compact_non_anchor_indices
            if idx in feasible
        )
        candidate_complete &= len(candidates) == expected

        # Recompute primary selector only from Validation.
        recomputed = _select_with_anchor_margin(
            candidates,
            anchor_source="PT_A57",
            margin_rel=CFG.switch_margin_rel,
        )
        stored = rec.get("summary", {}).get("compact_margin_selected", {})
        selector_reproducible &= (
            str(recomputed["source"]) == str(stored.get("source"))
            and int(recomputed["arch_idx"]) == int(stored.get("arch_idx", -1))
        )

    checks = {
        "preflight_pass": (
            preflight_obj.get("decision") == "PASS_SOURCE_PRIOR_BANK_PREFLIGHT_READY"
        ),
        "bank_frozen_pass": (
            bank.get("decision") == "PASS_SOURCE_PRIOR_BANK_STRONG_BANK_FROZEN"
        ),
        "bank_asset_count": len(bank.get("assets", {})) == expected_assets,
        "bank_target_unused": not bool(
            bank.get("target_pool_used")
            or bank.get("historical_pool_k_used")
            or bank.get("test_used")
        ),
        "holdout_complete": bool(holdout.get("complete"))
        and int(holdout.get("N_records", -1)) == expected_cases,
        "holdout_pool_exact": tuple(
            holdout.get("protocol", {}).get("fresh_pool", ())
        )
        == tuple(CFG.fresh_pool),
        "holdout_pool_k_unused": (
            holdout.get("historical_pool_k_reused") is False
        ),
        "holdout_test_unused": holdout.get("test_used") is False,
        "analysis_test_unused": analysis_obj.get("test_used") is False,
        "candidate_complete": bool(candidate_complete),
        "selector_validation_only_reproducible": bool(selector_reproducible),
        "anchor_present_every_case": all(
            any(
                r.get("source") == "PT_A57"
                for r in rec.get("candidates", {}).values()
            )
            for rec in holdout.get("records", {}).values()
        ),
        "target_steps_fixed_50": all(
            int(row.get("target_steps", -1)) == CFG.target_steps
            for rec in holdout.get("records", {}).values()
            for row in rec.get("candidates", {}).values()
        ),
        "bank_manifest_bound": (
            holdout.get("bank_manifest_sha256")
            == file_sha256(bank_manifest_path)
        ),
        "analysis_holdout_bound": (
            analysis_obj.get("holdout_sha256")
            == file_sha256(holdout_path)
        ),
    }
    decision = (
        "PASS_SOURCE_PRIOR_BANK_COMPACT_COMPLETE_AND_AUDITED"
        if all(checks.values())
        else "FAIL_SOURCE_PRIOR_BANK_COMPACT_AUDIT"
    )
    obj = {
        "study": "c3_1_compact_audit",
        "decision": decision,
        "checks": checks,
        "preflight_sha256": file_sha256(preflight_path),
        "bank_manifest_sha256": file_sha256(bank_manifest_path),
        "holdout_sha256": file_sha256(holdout_path),
        "analysis_sha256": file_sha256(analysis_path),
        "analysis_decision": analysis_obj.get("decision"),
        "N_cases": expected_cases,
        "historical_pool_k_reused": False,
        "test_used": False,
    }
    atomic_json(obj, out_path)
    return obj
