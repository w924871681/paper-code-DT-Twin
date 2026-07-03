# -*- coding: utf-8 -*-
from __future__ import annotations

import copy
import csv
import gc
import json
import math
import os
import random
import time
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from configs.methods.main_evaluation_cfg import CFG, config_dict
from core.methods.ours.adapt import adapt_steps
from core.methods.ours.paper_engine import _load_prior_model
from core.methods.ours.stage2_runtime import (
    candidate_backend_context,
    candidate_device,
    synchronize_if_cuda,
)
from core.space import build_model, profile_arch
from shared.data_access import get_support_validation_check, get_test_only
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


def _norm_rel(path: str) -> str:
    return str(path).replace("\\", os.sep).replace("/", os.sep)


def _pool_ids(pool: Sequence[int]) -> set[int]:
    start, count, _offset = [int(x) for x in pool]
    return set(range(start, start + count))


def _jobs(smoke: bool = False) -> List[Tuple[int, int, int]]:
    start, count, _offset = CFG.locked_pool
    jobs = [
        (cid, H, K)
        for cid in range(start, start + count)
        for H in CFG.H_list
        for K in CFG.K_list
    ]
    return jobs[:2] if smoke else jobs


def _safe_torch_load(path: str, device: torch.device):
    try:
        return torch.load(path, map_location=device, weights_only=True)
    except TypeError:
        return torch.load(path, map_location=device)


def _asset_full(project_root: str, item: Mapping[str, Any]) -> str:
    return os.path.abspath(os.path.join(project_root, _norm_rel(str(item["path"]))))


def _validate_manifest_assets(
    project_root: str, manifest: Mapping[str, Any]
) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    seen: set[Tuple[str, str]] = set()
    for name, item in manifest.get("assets", {}).items():
        full = _asset_full(project_root, item)
        key = (full, str(item.get("sha256", "")).lower())
        if key in seen:
            continue
        seen.add(key)
        if not os.path.isfile(full):
            errors.append(f"missing:{name}:{full}")
        elif file_sha256(full).lower() != key[1]:
            errors.append(f"hash:{name}:{full}")
    return len(errors) == 0, errors




def _load_strong_manifest(project_root: str, manifest_path: str) -> Dict[str, Any]:
    obj = load_json(manifest_path)
    if obj.get("decision") != CFG.expected_source_prior_bank_decision:
        raise RuntimeError("source-prior-bank evaluation strong bank is not frozen PASS")
    if bool(
        obj.get("target_pool_used")
        or obj.get("historical_pool_k_used")
        or obj.get("test_used")
    ):
        raise RuntimeError("source-prior-bank evaluation strong bank contains forbidden data use")
    ok, errors = _validate_manifest_assets(project_root, obj)
    if not ok:
        raise RuntimeError(f"source-prior-bank evaluation strong assets invalid: {errors}")
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
    path = _asset_full(project_root, item)
    model = build_model(
        A[idx], input_dim=input_dim, H=H, L=L, device=str(device)
    )
    state = _safe_torch_load(path, device)
    model.load_state_dict(state, strict=True)
    return model


def preflight(project_root: str, out_path: str) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    paths = {
        "anchor_safe_selector": os.path.join(root, CFG.anchor_safe_selector_path),
        "anchor_safe_selector_analysis": os.path.join(root, CFG.anchor_safe_selector_analysis_path),
        "anchor_safe_selector_audit": os.path.join(root, CFG.anchor_safe_selector_audit_path),
        "source_prior_bank_manifest": os.path.join(root, CFG.source_prior_bank_manifest_path),
        "c1_bank": os.path.join(root, CFG.c1_bank_path),
        "external_source_manifest": os.path.join(
            root, CFG.external_source_manifest_path
        ),
        "external_audit": os.path.join(root, CFG.external_audit_path),
    }
    checks: Dict[str, bool] = {
        f"{name}_exists": os.path.isfile(path) for name, path in paths.items()
    }
    details: Dict[str, Any] = {}

    locked_ids = _pool_ids(CFG.locked_pool)
    used_ids: set[int] = set()
    for lo, hi in CFG.known_used_center_ranges:
        used_ids.update(range(int(lo), int(hi) + 1))
    overlap = sorted(locked_ids & used_ids)

    if all(checks.values()):
        selector = load_json(paths["anchor_safe_selector"])
        analysis = load_json(paths["anchor_safe_selector_analysis"])
        audit = load_json(paths["anchor_safe_selector_audit"])
        bank = _load_strong_manifest(root, paths["source_prior_bank_manifest"])
        ext_source = load_json(paths["external_source_manifest"])
        ext_audit = load_json(paths["external_audit"])
        bank_ok, bank_errors = _validate_manifest_assets(root, bank)
        ext_ok, ext_errors = _validate_manifest_assets(root, ext_source)

        checks.update(
            {
                "anchor_safe_selector_pass": selector.get("decision")
                == CFG.expected_anchor_safe_selector_decision,
                "anchor_safe_selector_analysis_allows_locked_eval": analysis.get("decision")
                == CFG.expected_anchor_safe_selector_analysis_decision,
                "anchor_safe_selector_audit_pass": audit.get("decision")
                == CFG.expected_anchor_safe_selector_audit_decision,
                "anchor_safe_selector_hash_frozen": file_sha256(
                    paths["anchor_safe_selector"]
                ).lower()
                == CFG.expected_anchor_safe_selector_sha256,
                "anchor_safe_selector_analysis_hash_frozen": file_sha256(
                    paths["anchor_safe_selector_analysis"]
                ).lower()
                == CFG.expected_anchor_safe_selector_analysis_sha256,
                "anchor_safe_selector_audit_hash_frozen": file_sha256(paths["anchor_safe_selector_audit"]).lower()
                == CFG.expected_anchor_safe_selector_audit_sha256,
                "anchor_safe_selector_bound_by_audit": str(
                    audit.get("selector_sha256", "")
                ).lower()
                == file_sha256(paths["anchor_safe_selector"]).lower(),
                "anchor_safe_selector_analysis_bound_by_audit": str(
                    audit.get("analysis_sha256", "")
                ).lower()
                == file_sha256(paths["anchor_safe_selector_analysis"]).lower(),
                "margin_exactly_10pct": abs(
                    float(selector.get("selected_margin_rel", -1.0))
                    - CFG.frozen_margin_rel
                )
                < 1e-12,
                "anchor_safe_selector_test_unused": not bool(
                    selector.get("test_used")
                    or analysis.get("test_used")
                    or audit.get("test_used")
                ),
                "source_prior_bank_pass": bank.get("decision")
                == CFG.expected_source_prior_bank_decision,
                "source_prior_bank_manifest_hash_frozen": file_sha256(
                    paths["source_prior_bank_manifest"]
                ).lower()
                == CFG.expected_source_prior_bank_manifest_sha256,
                "compact_set_exact": tuple(
                    int(x) for x in bank.get("candidate_arch_indices", ())
                )
                == tuple(CFG.compact_arch_indices),
                "source_prior_bank_assets_valid": bank_ok,
                "source_prior_bank_target_test_unused": not bool(
                    bank.get("target_pool_used")
                    or bank.get("historical_pool_k_used")
                    or bank.get("test_used")
                ),
                "c1_bank_hash_frozen": file_sha256(paths["c1_bank"]).lower()
                == CFG.c1_bank_sha256,
                "external_source_pass": ext_source.get("decision")
                == CFG.expected_external_source_decision,
                "external_audit_pass": ext_audit.get("decision")
                == CFG.expected_external_audit_decision,
                "external_source_manifest_hash_frozen": file_sha256(
                    paths["external_source_manifest"]
                ).lower()
                == CFG.expected_external_source_manifest_sha256,
                "external_audit_hash_frozen": file_sha256(
                    paths["external_audit"]
                ).lower()
                == CFG.expected_external_audit_sha256,
                "external_source_assets_valid": ext_ok,
                "external_source_target_test_unused": not bool(
                    ext_source.get("target_pool_used")
                    or ext_source.get("validation_pool_k_used")
                    or ext_source.get("check_pool_k_used")
                    or ext_source.get("test_used")
                ),
                "locked_pool_no_previous_overlap": len(overlap) == 0,
                "locked_pool_count_20": len(locked_ids)
                == int(CFG.locked_pool[1]),
                "anchor_A57": CFG.anchor_arch_idx == 57,
                "target_steps_50": CFG.fixed_target_steps == 50,
                "methods_frozen": CFG.methods
                == (
                    "ours",
                    "pt_ft",
                    "medet_style",
                    "scratch50",
                    "meta_nas_lite",
                    "zero_nas",
                    "zero_nas_ft",
                ),
            }
        )
        details = {
            "bank_asset_errors": bank_errors,
            "external_asset_errors": ext_errors,
            "anchor_safe_selector_frozen_margin_rel": selector.get("selected_margin_rel"),
            "locked_pool_overlap": overlap,
        }

    decision = (
        "PASS_MAIN_EVALUATION_LOCKED_PREFLIGHT_READY"
        if checks and all(checks.values())
        else "FAIL_MAIN_EVALUATION_LOCKED_PREFLIGHT"
    )
    obj = {
        "study": "c3_3_locked_preflight",
        "decision": decision,
        "protocol": config_dict(),
        "checks": checks,
        "details": details,
        "upstream_dependencies": {
            name: {
                "path": os.path.abspath(path),
                "sha256": file_sha256(path) if os.path.isfile(path) else None,
            }
            for name, path in paths.items()
        },
        "method_or_selector_tuning_allowed": False,
        "historical_pool_k_reused": False,
        "test_used": False,
    }
    atomic_json(obj, out_path)
    return obj


def _fixed_target_adapt(
    model: nn.Module,
    Xs: torch.Tensor,
    ys: torch.Tensor,
    *,
    seed: int,
) -> None:
    dev = next(model.parameters()).device
    seed_all(seed, dev)
    model.train()
    opt = optim.SGD(model.parameters(), lr=CFG.fixed_target_lr)
    Xd, yd = Xs.to(dev).contiguous(), ys.to(dev).contiguous()
    for _ in range(CFG.fixed_target_steps):
        opt.zero_grad(set_to_none=True)
        loss = ((model(Xd) - yd) ** 2).mean()
        if not torch.isfinite(loss):
            raise RuntimeError("Non-finite SGD/MSE target loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            model.parameters(), CFG.fixed_target_grad_clip
        )
        opt.step()


def _search_target_adapt(
    model: nn.Module, Xs: torch.Tensor, ys: torch.Tensor, *, seed: int
) -> None:
    dev = next(model.parameters()).device
    adapt_steps(
        model,
        Xs.to(dev).contiguous(),
        ys.to(dev).contiguous(),
        steps=CFG.search_target_steps,
        lr=CFG.search_target_lr,
        weight_decay=0.0,
        robust_loss_type="huber",
        huber_delta=CFG.search_target_huber_delta,
        cvar_lambda=0.0,
        prior_state=None,
        prior_group_lambdas=None,
        batch_size=0,
        use_amp=False,
        oom_to_cpu=False,
        seed=int(seed),
        max_grad_norm=CFG.search_target_grad_clip,
    )


def _sample_proxy_batch(
    X: torch.Tensor,
    y: torch.Tensor,
    *,
    seed: int,
) -> Tuple[torch.Tensor, torch.Tensor]:
    n = int(X.shape[0])
    take = min(max(1, CFG.proxy_support_points), n)
    gen = torch.Generator(device=X.device)
    gen.manual_seed(int(seed))
    idx = torch.randperm(n, generator=gen, device=X.device)[:take]
    Xp, yp = X.index_select(0, idx), y.index_select(0, idx)
    if int(Xp.shape[0]) > CFG.proxy_batch_size:
        idx2 = torch.randperm(
            int(Xp.shape[0]), generator=gen, device=X.device
        )[: CFG.proxy_batch_size]
        Xp, yp = Xp.index_select(0, idx2), yp.index_select(0, idx2)
    return Xp, yp


def _entropy_proxy(model: nn.Module, X: torch.Tensor, y: torch.Tensor) -> float:
    model.train()
    model.zero_grad(set_to_none=True)
    loss = ((model(X) - y) ** 2).mean()
    params = [p for p in model.parameters() if p.requires_grad]
    grads = torch.autograd.grad(
        loss, params, retain_graph=False, create_graph=False, allow_unused=True
    )
    chunks = [g.detach().reshape(-1).abs() for g in grads if g is not None]
    if not chunks:
        return float("-inf")
    flat = torch.cat(chunks)
    total = flat.sum()
    if not torch.isfinite(total) or float(total.item()) <= 0.0:
        return float("-inf")
    prob = (flat / (total + 1e-12)).clamp_min(1e-12)
    return float((-(prob * prob.log()).sum()).item())


def _rank_score(
    values: Mapping[int, float], *, larger_is_better: bool
) -> Dict[int, float]:
    items = sorted(
        values.items(), key=lambda kv: kv[1], reverse=larger_is_better
    )
    n = len(items)
    if n <= 1:
        return {int(k): 1.0 for k, _ in items}
    return {
        int(k): 1.0 - float(rank) / float(n - 1)
        for rank, (k, _value) in enumerate(items)
    }


def _load_external_source_manifest(project_root: str) -> Dict[str, Any]:
    path = os.path.join(project_root, CFG.external_source_manifest_path)
    obj = load_json(path)
    if obj.get("decision") != CFG.expected_external_source_decision:
        raise RuntimeError("Frozen external source assets are not PASS")
    ok, errors = _validate_manifest_assets(project_root, obj)
    if not ok:
        raise RuntimeError(f"External source assets invalid: {errors}")
    if bool(obj.get("target_pool_used") or obj.get("test_used")):
        raise RuntimeError("External source assets used target/Test data")
    return obj


def _load_fixed_source_model(
    project_root: str,
    manifest: Mapping[str, Any],
    method: str,
    H: int,
    tier: str,
    A: Sequence[Any],
    input_dim: int,
    L: int,
    device: torch.device,
):
    bb = manifest["fixed_backbones"][f"h{H}_b{tier}"]
    idx = int(bb["arch_idx"])
    if idx != CFG.anchor_arch_idx:
        raise RuntimeError(f"Frozen {method} backbone drifted from A57")
    spec = A[idx]
    item = manifest["assets"][f"{method}_h{H}_b{tier}"]
    state = _safe_torch_load(_asset_full(project_root, item), device)
    model = build_model(spec, input_dim=input_dim, H=H, L=L, device=str(device))
    model.load_state_dict(state, strict=True)
    return model, spec, idx


def _planned_ours(feasible: set[int]) -> List[Tuple[str, int, str]]:
    planned: List[Tuple[str, int, str]] = [
        ("PT_A57", CFG.anchor_arch_idx, "strong"),
        ("LEGACY_C1_A57", CFG.anchor_arch_idx, "c1"),
    ]
    planned.extend(
        ("STRONG_COMPACT", int(idx), "strong")
        for idx in CFG.compact_non_anchor_indices
        if idx in feasible
    )
    return planned


def _candidate_lex(row: Mapping[str, Any]):
    return (
        float(row["validation"]["weighted_mse"]),
        float(row["params"]),
        float(row["flops"]),
        int(row["arch_idx"]),
        str(row["source"]),
    )


def _run_ours_case(
    project_root: str,
    strong_manifest: Mapping[str, Any],
    frozen: Mapping[str, Any],
    cfg: Any,
    A: Sequence[Any],
    requested: torch.device,
    safe_mode: str,
    Xs: torch.Tensor,
    ys: torch.Tensor,
    Xv: torch.Tensor,
    yv: torch.Tensor,
    tier: str,
    H: int,
    input_dim: int,
    L: int,
    seed: int,
):
    feasible = set(feasible_indices(cfg, A, tier, L, input_dim, H))
    if CFG.anchor_arch_idx not in feasible:
        raise RuntimeError("PT-A57 anchor is not hard feasible")
    planned = _planned_ours(feasible)
    summaries: List[Dict[str, Any]] = []
    anchor_model = None
    anchor_row = None
    best_alt_model = None
    best_alt_row = None

    for source, idx, loader in planned:
        spec = A[idx]
        actual = candidate_device(spec, requested, safe_mode)
        with candidate_backend_context(spec, actual, safe_mode):
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
                    project_root,
                    strong_manifest,
                    A,
                    H=H,
                    idx=idx,
                    input_dim=input_dim,
                    L=L,
                    device=actual,
                )
            _fixed_target_adapt(model, Xs, ys, seed=seed)
            val = eval_metrics(model, Xv, yv)
            params, flops = profile_arch(spec, L=L, input_dim=input_dim, H=H)
            row = {
                "token": f"{source}_A{idx}",
                "source": source,
                "arch_idx": int(idx),
                "arch_key": str(spec.arch_key),
                "family": str(spec.family),
                "params": float(params),
                "flops": float(flops),
                "validation": val,
                "target_seed": int(seed),
                "target_steps": CFG.fixed_target_steps,
            }
            summaries.append(row)
            if source == "PT_A57":
                anchor_model, anchor_row = model, row
            elif best_alt_row is None or _candidate_lex(row) < _candidate_lex(
                best_alt_row
            ):
                if best_alt_model is not None:
                    del best_alt_model
                best_alt_model, best_alt_row = model, row
            else:
                del model
            synchronize_if_cuda(actual)

    if anchor_model is None or anchor_row is None or best_alt_model is None:
        raise RuntimeError("Incomplete locked Ours candidate set")
    anchor_val = float(anchor_row["validation"]["weighted_mse"])
    alt_val = float(best_alt_row["validation"]["weighted_mse"])
    threshold = anchor_val * (1.0 - CFG.frozen_margin_rel)
    switched = alt_val <= threshold
    if switched:
        selected_model, selected_row = best_alt_model, best_alt_row
        del anchor_model
    else:
        selected_model, selected_row = anchor_model, anchor_row
        del best_alt_model
    selector = {
        "selector": "anchor_safe_selector_frozen_anchor_safe_compact_selector",
        "margin_rel": CFG.frozen_margin_rel,
        "anchor_validation_mse": anchor_val,
        "best_alternative_validation_mse": alt_val,
        "switch_threshold_validation_mse": threshold,
        "switched_from_pt_anchor": bool(switched),
        "selected_token": selected_row["token"],
        "candidate_validations": summaries,
        "hard_feasible_compact_indices": [
            int(i) for i in CFG.compact_arch_indices if i in feasible
        ],
        "selection_uses_check": False,
        "selection_uses_test": False,
    }
    return selected_model, A[int(selected_row["arch_idx"])], selected_row, selector, len(planned), len(planned)


def _run_search_case(
    method: str,
    frozen: Mapping[str, Any],
    cfg: Any,
    A: Sequence[Any],
    requested: torch.device,
    safe_mode: str,
    Xs: torch.Tensor,
    ys: torch.Tensor,
    Xv: torch.Tensor,
    yv: torch.Tensor,
    tier: str,
    H: int,
    input_dim: int,
    L: int,
    seed: int,
):
    feasible = feasible_indices(cfg, A, tier, L, input_dim, H)
    if not feasible:
        raise RuntimeError("No hard-feasible architecture")
    Xp, yp = _sample_proxy_batch(Xs.to(requested), ys.to(requested), seed=seed)
    proxy_raw: Dict[int, float] = {}
    for idx in feasible:
        spec = A[idx]
        actual = candidate_device(spec, requested, safe_mode)
        with candidate_backend_context(spec, actual, safe_mode):
            seed_all(seed + idx, actual)
            proxy_model = build_model(
                spec, input_dim=input_dim, H=H, L=L, device=str(actual)
            )
            proxy_raw[idx] = _entropy_proxy(
                proxy_model, Xp.to(actual), yp.to(actual)
            )
            del proxy_model
            synchronize_if_cuda(actual)
    proxy_rank = _rank_score(proxy_raw, larger_is_better=True)

    if method == "meta_nas_lite":
        source_rank = _rank_score(
            {i: float(frozen["pi50"][i]) for i in feasible},
            larger_is_better=True,
        )
        fused = {
            i: CFG.meta_prior_weight * source_rank[i]
            + CFG.meta_proxy_weight * proxy_rank[i]
            for i in feasible
        }
        shortlist = sorted(feasible, key=lambda i: (-fused[i], i))[
            : CFG.candidate_budget
        ]
        adapt = True
        selector_name = "frozen_meta_prior_plus_proxy_top12_valbest"
    elif method == "zero_nas":
        shortlist = sorted(feasible, key=lambda i: (-proxy_rank[i], i))[:1]
        adapt = False
        selector_name = "frozen_zero_proxy_top1_no_ft"
    elif method == "zero_nas_ft":
        shortlist = sorted(feasible, key=lambda i: (-proxy_rank[i], i))[
            : CFG.candidate_budget
        ]
        adapt = True
        selector_name = "frozen_zero_proxy_top12_ft50_valbest"
    else:
        raise ValueError(method)

    selected_model = None
    selected_spec = None
    best_row = None
    summaries: List[Dict[str, Any]] = []
    adapted_count = 0
    for idx in shortlist:
        spec = A[idx]
        actual = candidate_device(spec, requested, safe_mode)
        with candidate_backend_context(spec, actual, safe_mode):
            model, _prior = _load_prior_model(
                spec=spec,
                H=H,
                L=L,
                input_dim=input_dim,
                bank=frozen["bank"],
                device=actual,
            )
            if adapt:
                _search_target_adapt(model, Xs, ys, seed=seed + idx)
                adapted_count += 1
            val = eval_metrics(model, Xv, yv)
            params, flops = profile_arch(spec, L=L, input_dim=input_dim, H=H)
            row = {
                "arch_idx": int(idx),
                "arch_key": str(spec.arch_key),
                "family": str(spec.family),
                "params": float(params),
                "flops": float(flops),
                "validation": val,
            }
            summaries.append(row)
            lex = (
                float(val["weighted_mse"]),
                float(params),
                float(flops),
                int(idx),
            )
            if best_row is None or lex < best_row[0]:
                if selected_model is not None:
                    del selected_model
                selected_model = model
                selected_spec = spec
                best_row = (lex, row)
            else:
                del model
            synchronize_if_cuda(actual)
    if selected_model is None or selected_spec is None or best_row is None:
        raise RuntimeError("Search baseline failed to select a model")
    selector = {
        "selector": selector_name,
        "shortlist": [int(x) for x in shortlist],
        "selected_arch_idx": int(best_row[1]["arch_idx"]),
        "candidate_validations": summaries,
        "selection_uses_check": False,
        "selection_uses_test": False,
    }
    return selected_model, selected_spec, best_row[1], selector, len(shortlist), adapted_count


def run_method(
    project_root: str,
    method: str,
    out_path: str,
    device: str,
    safe_mode: str,
    smoke: bool = False,
) -> Dict[str, Any]:
    if method not in CFG.methods:
        raise ValueError(f"Unknown C3-3 method: {method}")
    root = os.path.abspath(project_root)
    preflight_path = os.path.join(
        root, CFG.output_root, "preflight", "main_evaluation_preflight.json"
    )
    if not os.path.isfile(preflight_path):
        raise FileNotFoundError("Run C3-3 preflight first")
    preflight_obj = load_json(preflight_path)
    if preflight_obj.get("decision") != "PASS_MAIN_EVALUATION_LOCKED_PREFLIGHT_READY":
        raise RuntimeError("C3-3 preflight is not PASS")

    start, count, offset = CFG.locked_pool
    cfg, cache, A, requested, safe = build_runtime(
        device, safe_mode, ((start, count, offset),)
    )
    if len(A) != CFG.architecture_count:
        raise RuntimeError("Architecture-space mismatch")
    frozen = load_frozen_assets(root)
    strong_manifest = _load_strong_manifest(
        root, os.path.join(root, CFG.source_prior_bank_manifest_path)
    )
    source_manifest = _load_external_source_manifest(root)
    L = int(cfg.main.task.L)
    jobs = _jobs(smoke)
    run_mode = "smoke" if smoke else "formal"
    out_path = os.path.abspath(out_path)

    upstream_hashes = {
        "preflight": file_sha256(preflight_path),
        "anchor_safe_selector": file_sha256(os.path.join(root, CFG.anchor_safe_selector_path)),
        "source_prior_bank_manifest": file_sha256(
            os.path.join(root, CFG.source_prior_bank_manifest_path)
        ),
        "external_source_manifest": file_sha256(
            os.path.join(root, CFG.external_source_manifest_path)
        ),
        "c1_bank": file_sha256(os.path.join(root, CFG.c1_bank_path)),
    }
    result = (
        load_json(out_path)
        if os.path.isfile(out_path)
        else {
            "study": "c3_3_locked_external_comparison",
            "method": method,
            "decision": "MAIN_EVALUATION_METHOD_IN_PROGRESS",
            "run_mode": run_mode,
            "protocol": config_dict(),
            "pool": list(CFG.locked_pool),
            "upstream_hashes": upstream_hashes,
            "records": {},
            "selection_uses_check": False,
            "selection_uses_test": False,
            "test_opened_only_after_final_model_fixed": True,
            "method_or_selector_tuning_allowed": False,
            "historical_pool_k_reused": False,
        }
    )
    if result.get("method") != method:
        raise RuntimeError("Method cache mismatch")
    if result.get("run_mode") != run_mode:
        raise RuntimeError("Smoke/formal outputs cannot share one file")
    if tuple(result.get("pool", ())) != tuple(CFG.locked_pool):
        raise RuntimeError("Locked pool mismatch")
    if result.get("upstream_hashes") != upstream_hashes:
        raise RuntimeError("Frozen upstream asset changed after run began")

    records = dict(result.get("records", {}))
    started = time.perf_counter()
    new_count = 0
    cumulative_adaptations = sum(
        int(r.get("adapted_candidate_count", 0)) for r in records.values()
    )

    for case_no, (cid, H, K) in enumerate(jobs, 1):
        Xs, ys, Xv, yv, Xc, yc, tier, ctype = get_support_validation_check(
            cfg, cache, cid, H, K
        )
        case_key = f"c{cid}_h{H}_k{K}_b{tier}"
        if case_key in records and bool(records[case_key].get("complete")):
            continue
        input_dim = int(Xs.shape[-1])
        seed = CFG.train_seed + 1009 * cid + 37 * H + 53 * K
        online_started = time.perf_counter()

        if method == "ours":
            (
                selected_model,
                selected_spec,
                selected_row,
                selector,
                candidate_count,
                adapted_count,
            ) = _run_ours_case(
                root,
                strong_manifest,
                frozen,
                cfg,
                A,
                requested,
                safe,
                Xs,
                ys,
                Xv,
                yv,
                tier,
                H,
                input_dim,
                L,
                seed,
            )
        elif method in ("pt_ft", "medet_style"):
            selected_model, selected_spec, selected_idx = _load_fixed_source_model(
                root,
                source_manifest,
                method,
                H,
                tier,
                A,
                input_dim,
                L,
                requested,
            )
            if selected_idx not in feasible_indices(
                cfg, A, tier, L, input_dim, H
            ):
                raise RuntimeError(f"Frozen {method} A57 is infeasible")
            _fixed_target_adapt(selected_model, Xs, ys, seed=seed)
            val = eval_metrics(selected_model, Xv, yv)
            params, flops = profile_arch(
                selected_spec, L=L, input_dim=input_dim, H=H
            )
            selected_row = {
                "source": method.upper(),
                "arch_idx": int(selected_idx),
                "arch_key": str(selected_spec.arch_key),
                "family": str(selected_spec.family),
                "params": float(params),
                "flops": float(flops),
                "validation": val,
            }
            selector = {
                "selector": "frozen_source_only_A57",
                "selection_data": "source_only_pi50",
                "selection_uses_check": False,
                "selection_uses_test": False,
            }
            candidate_count = adapted_count = 1
        elif method == "scratch50":
            idx = CFG.anchor_arch_idx
            if idx not in feasible_indices(cfg, A, tier, L, input_dim, H):
                raise RuntimeError("Scratch A57 is infeasible")
            selected_spec = A[idx]
            seed_all(seed, requested)
            selected_model = build_model(
                selected_spec,
                input_dim=input_dim,
                H=H,
                L=L,
                device=str(requested),
            )
            _fixed_target_adapt(selected_model, Xs, ys, seed=seed)
            val = eval_metrics(selected_model, Xv, yv)
            params, flops = profile_arch(
                selected_spec, L=L, input_dim=input_dim, H=H
            )
            selected_row = {
                "source": "SCRATCH",
                "arch_idx": idx,
                "arch_key": str(selected_spec.arch_key),
                "family": str(selected_spec.family),
                "params": float(params),
                "flops": float(flops),
                "validation": val,
            }
            selector = {
                "selector": "fixed_A57_random_initialization",
                "selection_uses_check": False,
                "selection_uses_test": False,
            }
            candidate_count = adapted_count = 1
        else:
            (
                selected_model,
                selected_spec,
                selected_row,
                selector,
                candidate_count,
                adapted_count,
            ) = _run_search_case(
                method,
                frozen,
                cfg,
                A,
                requested,
                safe,
                Xs,
                ys,
                Xv,
                yv,
                tier,
                H,
                input_dim,
                L,
                seed,
            )

        # The final architecture and parameters are now fixed. Check is only
        # reported, and Test is materialized only after this point.
        online_seconds = float(time.perf_counter() - online_started)
        check = eval_metrics(selected_model, Xc, yc)
        Xt, yt = get_test_only(cfg, cache, cid, H, K)
        test = eval_metrics(selected_model, Xt, yt)
        params, flops = profile_arch(
            selected_spec, L=L, input_dim=input_dim, H=H
        )
        record = {
            "complete": True,
            "method": method,
            "case_key": case_key,
            "center_id": int(cid),
            "center_type": str(ctype),
            "budget_tier": str(tier),
            "H": int(H),
            "K": int(K),
            "feasible": True,
            "hard_feasible": True,
            "candidate_count": int(candidate_count),
            "adapted_candidate_count": int(adapted_count),
            "arch_idx": int(selected_row["arch_idx"]),
            "arch_key": str(selected_row["arch_key"]),
            "family": str(selected_row["family"]),
            "params": float(params),
            "flops": float(flops),
            "validation": selected_row["validation"],
            "selector": selector,
            "check": check,
            "test": test,
            "online_seconds": online_seconds,
            "target_seed": int(seed),
            "selection_uses_check": False,
            "selection_uses_test": False,
            "test_opened_after_selection": True,
            "max_online_gradient_steps_per_candidate": int(
                CFG.fixed_target_steps
                if method
                in {
                    "ours",
                    "pt_ft",
                    "medet_style",
                    "scratch50",
                }
                else (CFG.search_target_steps if adapted_count else 0)
            ),
        }
        records[case_key] = record
        cumulative_adaptations += int(adapted_count)
        result["records"] = records
        result["N_records"] = len(records)
        result["expected_records"] = len(jobs)
        result["complete"] = len(records) == len(jobs) and all(
            bool(r.get("complete")) for r in records.values()
        )
        atomic_json(result, out_path)

        new_count += 1
        elapsed = time.perf_counter() - started
        remaining = max(0, len(jobs) - len(records))
        eta = elapsed / max(1, new_count) * remaining
        print(
            f"[C3-3:{method}] case={case_no}/{len(jobs)} {case_key} "
            f"candidates={candidate_count} adapted={adapted_count} "
            f"total_adaptations={cumulative_adaptations} "
            f"gradient_steps={cumulative_adaptations*50} "
            f"selected=A{record['arch_idx']} test_mse={test['weighted_mse']:.6g} "
            f"elapsed={elapsed/3600:.2f}h eta={eta/3600:.2f}h",
            flush=True,
        )
        del selected_model
        gc.collect()
        if requested.type == "cuda":
            torch.cuda.empty_cache()

    result["decision"] = (
        "MAIN_EVALUATION_LOCKED_METHOD_COMPLETE"
        if result.get("complete")
        else "MAIN_EVALUATION_LOCKED_METHOD_INCOMPLETE"
    )
    atomic_json(result, out_path)
    return result


def _mean(values: Iterable[float]) -> Optional[float]:
    vals = list(values)
    return float(np.mean(vals)) if vals else None


def _cvar90(values: Iterable[float]) -> Optional[float]:
    arr = np.sort(np.asarray(list(values), dtype=float))
    if arr.size == 0:
        return None
    k = max(1, int(math.ceil(0.1 * arr.size)))
    return float(arr[-k:].mean())


def _relative_gain(new: float, ref: float) -> float:
    return float((float(ref) - float(new)) / (abs(float(ref)) + CFG.eps))


def _center_bootstrap(
    values_by_center: Mapping[int, Sequence[float]], seed: int
) -> Dict[str, Any]:
    arr = np.asarray(
        [np.mean(values_by_center[c]) for c in sorted(values_by_center)],
        dtype=float,
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
    ids = rng.integers(0, len(arr), size=(CFG.bootstrap_repeats, len(arr)))
    boot = arr[ids].mean(axis=1)
    return {
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "ci_low": float(np.quantile(boot, 0.025)),
        "ci_high": float(np.quantile(boot, 0.975)),
        "n_centers": int(len(arr)),
    }


def analyze(project_root: str, result_root: str) -> Dict[str, Any]:
    _ = os.path.abspath(project_root)
    result_root = os.path.abspath(result_root)
    payloads: Dict[str, Any] = {}
    for method in CFG.methods:
        path = os.path.join(result_root, "methods", f"{method}.json")
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        payload = load_json(path)
        if not payload.get("complete"):
            raise RuntimeError(f"Incomplete method: {method}")
        payloads[method] = payload

    rows = {m: p["records"] for m, p in payloads.items()}
    overall: List[Dict[str, Any]] = []
    for method in CFG.methods:
        mapping = rows[method]
        feasible = [r for r in mapping.values() if bool(r.get("feasible"))]
        overall.append(
            {
                "method": method,
                "N_total": len(mapping),
                "N_feasible": len(feasible),
                "feasible_rate": float(len(feasible) / max(1, len(mapping))),
                "test_mse_mean": _mean(
                    r["test"]["weighted_mse"] for r in feasible
                ),
                "test_mae_mean": _mean(r["test"]["mae"] for r in feasible),
                "test_worst10_mean": _mean(
                    r["test"]["worst10"] for r in feasible
                ),
                "case_cvar90_mse": _cvar90(
                    r["test"]["weighted_mse"] for r in feasible
                ),
                "online_seconds_mean": _mean(
                    r.get("online_seconds", 0.0) for r in feasible
                ),
                "params_mean": _mean(r.get("params", 0.0) for r in feasible),
                "flops_mean": _mean(r.get("flops", 0.0) for r in feasible),
            }
        )

    ours = rows["ours"]
    paired: Dict[str, Any] = {}
    for method in CFG.methods:
        if method == "ours":
            continue
        base = rows[method]
        common = sorted(set(ours) & set(base))
        metric_results: Dict[str, Any] = {}
        wins = 0
        for metric in ("weighted_mse", "mae", "worst10"):
            by_center: Dict[int, List[float]] = defaultdict(list)
            for key in common:
                ro, rb = ours[key], base[key]
                go = float(ro["test"][metric])
                gb = float(rb["test"][metric])
                by_center[int(ro["center_id"])].append(_relative_gain(go, gb))
                if metric == "weighted_mse":
                    wins += int(go < gb)
            metric_results[metric] = _center_bootstrap(
                by_center, CFG.train_seed + 701 + len(method) + len(metric)
            )
        paired[method] = {
            "N_common": len(common),
            "mse_win_rate": float(wins / max(1, len(common))),
            "relative_gains": metric_results,
        }

    ours_sources = Counter(
        str(r.get("selector", {}).get("selected_token", "PT_A57"))
        for r in ours.values()
    )
    summary = {
        "study": "c3_3_locked_external_analysis",
        "decision": "MAIN_EVALUATION_LOCKED_COMPARISON_COMPLETE_REPORT_AS_OBSERVED",
        "protocol": config_dict(),
        "overall": overall,
        "paired_ours_vs_baselines": paired,
        "ours_selected_tokens": dict(ours_sources),
        "primary_methods": list(CFG.primary_methods),
        "diagnostic_methods": list(CFG.diagnostic_methods),
        "test_used_only_after_each_final_model_was_fixed": all(
            bool(p.get("test_opened_only_after_final_model_fixed"))
            for p in payloads.values()
        ),
        "method_or_selector_tuning_after_this_pool_allowed": False,
        "historical_pool_k_reused": False,
    }
    out_dir = os.path.join(result_root, "analysis")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "main_evaluation_analysis.json")
    atomic_json(summary, json_path)

    csv_path = os.path.join(out_dir, "main_evaluation_overall.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(overall[0].keys()))
        writer.writeheader()
        writer.writerows(overall)

    report = [
        "# C3 Locked End-to-End External Comparison",
        "",
        "This pool is evaluation-only. No method or selector retuning is allowed.",
        "",
        "| Method | Feasible | MSE | MAE | Worst-10% | CVaR90 | Online s | Params | FLOPs |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in overall:
        report.append(
            "| {method} | {feasible_rate:.1%} | {test_mse_mean:.8f} | "
            "{test_mae_mean:.8f} | {test_worst10_mean:.8f} | "
            "{case_cvar90_mse:.8f} | {online_seconds_mean:.3f} | "
            "{params_mean:.1f} | {flops_mean:.1f} |".format(**row)
        )
    report.extend(["", "## Paired Ours comparisons", ""])
    for method, comp in paired.items():
        gain = comp["relative_gains"]["weighted_mse"]
        report.append(
            f"- Ours vs {method}: N={comp['N_common']}, "
            f"MSE win={comp['mse_win_rate']:.3f}, "
            f"gain={100*gain['mean']:.3f}% "
            f"(95% CI {100*gain['ci_low']:.3f}%, "
            f"{100*gain['ci_high']:.3f}%)."
        )
    report_path = os.path.join(out_dir, "main_evaluation_report.md")
    with open(report_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(report) + "\n")
    return summary


def audit(project_root: str, result_root: str) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    result_root = os.path.abspath(result_root)
    preflight_path = os.path.join(result_root, "preflight", "main_evaluation_preflight.json")
    analysis_path = os.path.join(result_root, "analysis", "main_evaluation_analysis.json")
    # Budget tier is data-derived; build expected identity without tier.
    expected_identity = {
        (cid, H, K) for cid, H, K in _jobs(False)
    }
    checks: Dict[str, bool] = {
        "preflight_exists": os.path.isfile(preflight_path),
        "analysis_exists": os.path.isfile(analysis_path),
    }
    expected_upstream = {
        "preflight": file_sha256(preflight_path) if os.path.isfile(preflight_path) else None,
        "anchor_safe_selector": file_sha256(os.path.join(root, CFG.anchor_safe_selector_path)),
        "source_prior_bank_manifest": file_sha256(os.path.join(root, CFG.source_prior_bank_manifest_path)),
        "external_source_manifest": file_sha256(os.path.join(root, CFG.external_source_manifest_path)),
        "c1_bank": file_sha256(os.path.join(root, CFG.c1_bank_path)),
    }
    method_info: Dict[str, Any] = {}
    key_sets: List[set[str]] = []
    for method in CFG.methods:
        path = os.path.join(result_root, "methods", f"{method}.json")
        present = os.path.isfile(path)
        info: Dict[str, Any] = {"present": present}
        if present:
            obj = load_json(path)
            records = obj.get("records", {})
            identities = {
                (int(r["center_id"]), int(r["H"]), int(r["K"]))
                for r in records.values()
            }
            rows = list(records.values())
            info.update(
                {
                    "complete": bool(obj.get("complete")),
                    "N_records": len(records),
                    "expected_records": obj.get("expected_records"),
                    "same_pool": tuple(obj.get("pool", ()))
                    == tuple(CFG.locked_pool),
                    "identity_exact": identities == expected_identity,
                    "all_complete": all(bool(r.get("complete")) for r in rows),
                    "all_feasible": all(bool(r.get("feasible")) for r in rows),
                    "selection_check_unused": all(
                        not bool(r.get("selection_uses_check")) for r in rows
                    ),
                    "selection_test_unused": all(
                        not bool(r.get("selection_uses_test")) for r in rows
                    ),
                    "test_after_selection": all(
                        bool(r.get("test_opened_after_selection")) for r in rows
                    ),
                    "test_metrics_finite": all(
                        np.isfinite(float(r["test"]["weighted_mse"]))
                        and np.isfinite(float(r["test"]["mae"]))
                        and np.isfinite(float(r["test"]["worst10"]))
                        for r in rows
                    ),
                    "protocol_exact": json.dumps(obj.get("protocol"), sort_keys=True) == json.dumps(config_dict(), sort_keys=True),
                    "method_tuning_disabled": not bool(
                        obj.get("method_or_selector_tuning_allowed")
                    ),
                    "historical_pool_k_unused": not bool(
                        obj.get("historical_pool_k_reused")
                    ),
                    "run_mode_formal": obj.get("run_mode") == "formal",
                    "decision_complete": obj.get("decision") == "MAIN_EVALUATION_LOCKED_METHOD_COMPLETE",
                    "top_level_check_unused": not bool(obj.get("selection_uses_check")),
                    "top_level_test_unused": not bool(obj.get("selection_uses_test")),
                    "upstream_hashes_exact": obj.get("upstream_hashes") == expected_upstream,
                }
            )
            if method == "ours":
                info["margin_exact"] = all(
                    abs(
                        float(r["selector"].get("margin_rel", -1.0))
                        - CFG.frozen_margin_rel
                    )
                    < 1e-12
                    for r in rows
                )
                info["candidate_set_locked"] = all(
                    set(
                        int(x)
                        for x in r["selector"].get(
                            "hard_feasible_compact_indices", []
                        )
                    ).issubset(set(CFG.compact_arch_indices))
                    for r in rows
                )
                info["same_case_seed"] = all(
                    len(
                        {
                            int(x["target_seed"])
                            for x in r["selector"].get(
                                "candidate_validations", []
                            )
                        }
                    )
                    == 1
                    for r in rows
                )
                info["ours_candidate_budget_exact"] = all(
                    int(r.get("candidate_count", -1)) in {4, 7}
                    and int(r.get("adapted_candidate_count", -1)) == int(r.get("candidate_count", -2))
                    for r in rows
                )
            elif method in {"pt_ft", "medet_style", "scratch50"}:
                info["fixed_candidate_budget_exact"] = all(
                    int(r.get("candidate_count", -1)) == 1
                    and int(r.get("adapted_candidate_count", -1)) == 1
                    for r in rows
                )
            elif method in {"meta_nas_lite", "zero_nas_ft"}:
                info["search_candidate_budget_exact"] = all(
                    int(r.get("candidate_count", -1)) == CFG.candidate_budget
                    and int(r.get("adapted_candidate_count", -1)) == CFG.candidate_budget
                    for r in rows
                )
            elif method == "zero_nas":
                info["zero_nas_budget_exact"] = all(
                    int(r.get("candidate_count", -1)) == 1
                    and int(r.get("adapted_candidate_count", -1)) == 0
                    for r in rows
                )
            key_sets.append(set(records))
        method_info[method] = info
        checks[f"method_{method}_valid"] = present and all(
            bool(v) for k, v in info.items() if k != "N_records" and k != "expected_records"
        ) and int(info.get("N_records", -1)) == 80 and int(info.get("expected_records", -1)) == 80

    checks["same_case_keys_all_methods"] = bool(key_sets) and all(
        keys == key_sets[0] for keys in key_sets[1:]
    )
    if os.path.isfile(preflight_path):
        checks["preflight_pass"] = load_json(preflight_path).get("decision") == "PASS_MAIN_EVALUATION_LOCKED_PREFLIGHT_READY"
    if os.path.isfile(analysis_path):
        analysis = load_json(analysis_path)
        checks["analysis_complete"] = analysis.get("decision") == "MAIN_EVALUATION_LOCKED_COMPARISON_COMPLETE_REPORT_AS_OBSERVED"
        checks["analysis_no_retuning"] = not bool(analysis.get("method_or_selector_tuning_after_this_pool_allowed"))
        checks["analysis_test_order_pass"] = bool(analysis.get("test_used_only_after_each_final_model_was_fixed"))
    decision = (
        "PASS_MAIN_EVALUATION_LOCKED_EVALUATION_COMPLETE_AND_AUDITED"
        if checks and all(checks.values())
        else "FAIL_MAIN_EVALUATION_LOCKED_EVALUATION_AUDIT"
    )
    result = {
        "study": "c3_3_locked_audit",
        "decision": decision,
        "protocol": config_dict(),
        "checks": checks,
        "methods": method_info,
        "preflight_sha256": file_sha256(preflight_path)
        if os.path.isfile(preflight_path)
        else None,
        "analysis_sha256": file_sha256(analysis_path)
        if os.path.isfile(analysis_path)
        else None,
        "method_result_sha256": {
            method: file_sha256(
                os.path.join(result_root, "methods", f"{method}.json")
            )
            for method in CFG.methods
            if os.path.isfile(
                os.path.join(result_root, "methods", f"{method}.json")
            )
        },
        "historical_pool_k_reused": False,
        "test_used_for_selection": False,
        "method_or_selector_retuning_allowed": False,
    }
    out_path = os.path.join(result_root, "audit", "main_evaluation_audit.json")
    atomic_json(result, out_path)
    return result
