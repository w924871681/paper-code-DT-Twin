# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import gc
import json
import math
import os
import platform
import random
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from configs.methods.supplementary_experiments_cfg import CFG_SUPP, config_dict
from main_evaluation.pipeline import (
    _entropy_proxy,
    _load_external_source_manifest,
    _load_fixed_source_model,
    _load_strong_manifest,
    _load_strong_model,
    _rank_score,
    _run_ours_case,
    _run_search_case,
    _sample_proxy_batch,
)
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


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def _ensure_parent(path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)


def _atomic_torch_save(obj: Any, path: str) -> None:
    path = os.path.abspath(path)
    _ensure_parent(path)
    tmp = f"{path}.{os.getpid()}.{time.time_ns()}.tmp"
    torch.save(obj, tmp)
    os.replace(tmp, path)


def _write_csv(path: str, rows: Sequence[Mapping[str, Any]]) -> None:
    _ensure_parent(path)
    fields: List[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _jobs(pool: Sequence[int], smoke: bool = False) -> List[Tuple[int, int, int]]:
    start, count, _offset = [int(x) for x in pool]
    jobs = [
        (cid, H, K)
        for cid in range(start, start + count)
        for H in CFG_SUPP.H_list
        for K in CFG_SUPP.K_list
    ]
    return jobs[:2] if smoke else jobs


def _pool_ids(pool: Sequence[int]) -> set[int]:
    start, count, _offset = [int(x) for x in pool]
    return set(range(start, start + count))


def _sync(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)




def _eta_clock(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + seconds))

def _mean(values: Iterable[float]) -> float:
    vals = [float(x) for x in values]
    return float(np.mean(vals)) if vals else float("nan")


def _cvar90(values: Iterable[float]) -> float:
    arr = np.sort(np.asarray(list(values), dtype=float))
    if arr.size == 0:
        return float("nan")
    k = max(1, int(math.ceil(0.10 * arr.size)))
    return float(arr[-k:].mean())


def _rel_gain(new: float, ref: float) -> float:
    return float((float(ref) - float(new)) / (abs(float(ref)) + CFG_SUPP.eps))


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
    ids = rng.integers(
        0, len(arr), size=(CFG_SUPP.bootstrap_repeats, len(arr))
    )
    boot = arr[ids].mean(axis=1)
    return {
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "ci_low": float(np.quantile(boot, 0.025)),
        "ci_high": float(np.quantile(boot, 0.975)),
        "n_centers": int(len(arr)),
    }


def _result_paths(project_root: str) -> Dict[str, str]:
    base = os.path.join(os.path.abspath(project_root), CFG_SUPP.output_root)
    return {
        "root": base,
        "preflight": os.path.join(base, "preflight", "supp_preflight.json"),
        "trajectory": os.path.join(base, "trajectory", "trajectory.json"),
        "trajectory_dir": os.path.join(base, "trajectory"),
        "trajectory_checkpoints": os.path.join(
            base, "trajectory", "model_checkpoints"
        ),
        "anchor_risk": os.path.join(
            base, "anchor_risk", "full_vs_no_anchor_risk.json"
        ),
        "anchor_risk_dir": os.path.join(base, "anchor_risk"),
        "runtime": os.path.join(base, "runtime", "repeated_runtime.json"),
        "runtime_dir": os.path.join(base, "runtime"),
        "optimizer": os.path.join(
            base,
            "optimizer_control",
            "optimizer_matched_control.json",
        ),
        "optimizer_dir": os.path.join(base, "optimizer_control"),
        "report": os.path.join(base, "report"),
        "audit": os.path.join(base, "audit", "supplementary_audit.json"),
    }


def _upstream_hashes(project_root: str, include_external: bool = False) -> Dict[str, str]:
    root = os.path.abspath(project_root)
    items = {
        "c31_bank_manifest": os.path.join(root, CFG_SUPP.c31_bank_manifest_path),
        "c1_bank": os.path.join(root, CFG_SUPP.c1_bank_path),
        "supp_preflight": _result_paths(root)["preflight"],
    }
    if include_external:
        items["external_source_manifest"] = os.path.join(
            root, CFG_SUPP.external_source_manifest_path
        )
    return {name: file_sha256(path) for name, path in items.items()}


def _candidate_lex(row: Mapping[str, Any]) -> Tuple[float, float, float, int, str]:
    return (
        float(row["validation"]["weighted_mse"]),
        float(row["params"]),
        float(row["flops"]),
        int(row["arch_idx"]),
        str(row["token"]),
    )


def _select_val_best(
    candidates: Sequence[Mapping[str, Any]], tokens: Sequence[str]
) -> Dict[str, Any]:
    mapping = {str(r["token"]): r for r in candidates}
    allowed = [mapping[t] for t in tokens if t in mapping]
    if not allowed:
        raise RuntimeError("No candidate available for validation-best selection")
    selected = min(allowed, key=_candidate_lex)
    return {
        "selected_token": str(selected["token"]),
        "selected_arch_idx": int(selected["arch_idx"]),
        "selector": "validation_best",
        "allowed_tokens": [str(r["token"]) for r in allowed],
    }


def _select_anchor_safe(
    candidates: Sequence[Mapping[str, Any]],
    tokens: Sequence[str],
    *,
    anchor_token: str,
    margin_rel: float,
) -> Dict[str, Any]:
    mapping = {str(r["token"]): r for r in candidates}
    if anchor_token not in mapping:
        raise RuntimeError(f"Anchor missing: {anchor_token}")
    allowed = [mapping[t] for t in tokens if t in mapping]
    anchor = mapping[anchor_token]
    if anchor not in allowed:
        allowed.append(anchor)
    alternatives = [r for r in allowed if str(r["token"]) != anchor_token]
    if alternatives:
        best_alt = min(alternatives, key=_candidate_lex)
        threshold = float(anchor["validation"]["weighted_mse"]) * (
            1.0 - float(margin_rel)
        )
        switched = float(best_alt["validation"]["weighted_mse"]) <= threshold
        selected = best_alt if switched else anchor
    else:
        best_alt = None
        threshold = None
        switched = False
        selected = anchor
    return {
        "selected_token": str(selected["token"]),
        "selected_arch_idx": int(selected["arch_idx"]),
        "selector": "anchor_safe_validation",
        "anchor_token": anchor_token,
        "margin_rel": float(margin_rel),
        "switched": bool(switched),
        "anchor_validation_mse": float(anchor["validation"]["weighted_mse"]),
        "best_alternative_validation_mse": (
            None
            if best_alt is None
            else float(best_alt["validation"]["weighted_mse"])
        ),
        "switch_threshold_validation_mse": threshold,
        "allowed_tokens": [str(r["token"]) for r in allowed],
    }


def _spearman_from_orders(order_a: Sequence[str], order_b: Sequence[str]) -> float:
    common = [x for x in order_a if x in set(order_b)]
    if len(common) <= 1:
        return 1.0
    ra = {token: i for i, token in enumerate(order_a)}
    rb = {token: i for i, token in enumerate(order_b)}
    xa = np.asarray([ra[t] for t in common], dtype=float)
    xb = np.asarray([rb[t] for t in common], dtype=float)
    if np.std(xa) <= 0 or np.std(xb) <= 0:
        return 1.0
    return float(np.corrcoef(xa, xb)[0, 1])


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------


def preflight(project_root: str, out_path: Optional[str] = None) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    paths = _result_paths(root)
    out_path = out_path or paths["preflight"]
    required = {
        "c31_bank_manifest": os.path.join(root, CFG_SUPP.c31_bank_manifest_path),
        "c1_bank": os.path.join(root, CFG_SUPP.c1_bank_path),
        "external_source_manifest": os.path.join(
            root, CFG_SUPP.external_source_manifest_path
        ),
        "ablation_candidates": os.path.join(
            root, CFG_SUPP.ablation_candidates_path
        ),
        "c33_preflight": os.path.join(root, CFG_SUPP.c33_preflight_path),
    }
    checks: Dict[str, bool] = {
        f"{name}_exists": os.path.isfile(path) for name, path in required.items()
    }
    details: Dict[str, Any] = {}

    used: set[int] = set()
    for lo, hi in CFG_SUPP.known_used_center_ranges:
        used.update(range(int(lo), int(hi) + 1))
    trajectory_overlap = sorted(_pool_ids(CFG_SUPP.trajectory_pool) & used)
    optimizer_overlap = sorted(_pool_ids(CFG_SUPP.optimizer_control_pool) & used)
    cross_overlap = sorted(
        _pool_ids(CFG_SUPP.trajectory_pool)
        & _pool_ids(CFG_SUPP.optimizer_control_pool)
    )
    checks.update(
        {
            "trajectory_pool_untouched": not trajectory_overlap,
            "optimizer_control_pool_untouched": not optimizer_overlap,
            "new_pools_disjoint": not cross_overlap,
            "trajectory_checkpoints_exact": tuple(
                CFG_SUPP.trajectory_checkpoints
            )
            == (0, 1, 5, 10, 20, 50),
            "target_recipe_frozen": (
                CFG_SUPP.target_steps == 50
                and abs(CFG_SUPP.target_lr - 1e-2) < 1e-15
                and abs(CFG_SUPP.target_grad_clip - 1.0) < 1e-15
            ),
            "runtime_repeats_at_least_five": CFG_SUPP.runtime_repeats >= 5,
            "matched_candidate_budget_12": (
                CFG_SUPP.matched_candidate_budget == 12
            ),
        }
    )

    if checks.get("c1_bank_exists"):
        checks["c1_bank_hash_frozen"] = (
            file_sha256(required["c1_bank"]).lower()
            == CFG_SUPP.c1_bank_sha256.lower()
        )
    if checks.get("c31_bank_manifest_exists"):
        manifest = load_json(required["c31_bank_manifest"])
        checks["c31_bank_decision_frozen"] = (
            manifest.get("decision") == CFG_SUPP.expected_c31_bank_decision
        )
        checks["compact_architecture_set_exact"] = tuple(
            int(x) for x in manifest.get("candidate_arch_indices", ())
        ) == tuple(CFG_SUPP.compact_arch_indices)
    if checks.get("ablation_candidates_exists"):
        ablation = load_json(required["ablation_candidates"])
        checks["ablation_complete"] = bool(ablation.get("complete")) and int(
            ablation.get("N_records", 0)
        ) == 80
    if checks.get("c33_preflight_exists"):
        c33 = load_json(required["c33_preflight"])
        checks["c33_preflight_pass"] = (
            c33.get("decision") == "PASS_C33_LOCKED_PREFLIGHT_READY"
        )

    details.update(
        {
            "trajectory_pool_overlap": trajectory_overlap,
            "optimizer_control_pool_overlap": optimizer_overlap,
            "new_pool_cross_overlap": cross_overlap,
            "required_files": {
                k: {
                    "path": v,
                    "sha256": file_sha256(v) if os.path.isfile(v) else None,
                }
                for k, v in required.items()
            },
        }
    )
    obj = {
        "study": "experiments.supplementary_preflight",
        "decision": (
            "PASS_SUPPLEMENTARY_EVIDENCE_PREFLIGHT"
            if checks and all(checks.values())
            else "FAIL_SUPPLEMENTARY_EVIDENCE_PREFLIGHT"
        ),
        "protocol": config_dict(),
        "checks": checks,
        "details": details,
        "method_retuning_allowed": False,
        "trajectory_test_used": False,
        "runtime_test_used": False,
        "optimizer_control_is_evaluation_only": True,
    }
    atomic_json(obj, out_path)
    return obj


def _require_preflight(root: str) -> None:
    path = _result_paths(root)["preflight"]
    if not os.path.isfile(path):
        raise FileNotFoundError("Run supplementary preflight first")
    obj = load_json(path)
    if obj.get("decision") != "PASS_SUPPLEMENTARY_EVIDENCE_PREFLIGHT":
        raise RuntimeError("Supplementary preflight is not PASS")


# ---------------------------------------------------------------------------
# Experiment 1: 50-step adaptation trajectory
# ---------------------------------------------------------------------------


def _trajectory_candidate_plan(feasible: set[int]) -> List[Tuple[str, int, str]]:
    rows: List[Tuple[str, int, str]] = [
        ("PT_A57", CFG_SUPP.anchor_arch_idx, "strong"),
        ("C1_A57", CFG_SUPP.anchor_arch_idx, "c1"),
    ]
    rows.extend(
        (f"STRONG_A{idx}", int(idx), "strong")
        for idx in CFG_SUPP.compact_non_anchor_indices
        if int(idx) in feasible
    )
    return rows


def _load_trajectory_candidate(
    project_root: str,
    strong_manifest: Mapping[str, Any],
    frozen: Mapping[str, Any],
    A: Sequence[Any],
    *,
    H: int,
    idx: int,
    loader: str,
    input_dim: int,
    L: int,
    device: torch.device,
) -> nn.Module:
    if loader == "strong":
        return _load_strong_model(
            project_root,
            strong_manifest,
            A,
            H=H,
            idx=idx,
            input_dim=input_dim,
            L=L,
            device=device,
        )
    model, _prior = _load_prior_model(
        spec=A[idx],
        H=H,
        L=L,
        input_dim=input_dim,
        bank=frozen["bank"],
        device=device,
    )
    return model


def _support_mse(model: nn.Module, X: torch.Tensor, y: torch.Tensor) -> float:
    dev = next(model.parameters()).device
    model.eval()
    with torch.no_grad():
        pred = model(X.to(dev).contiguous())
        target = y.to(dev).contiguous()
        return float(((pred - target) ** 2).mean().item())


def _trajectory_one_candidate(
    *,
    model: nn.Module,
    token: str,
    idx: int,
    loader: str,
    spec: Any,
    Xs: torch.Tensor,
    ys: torch.Tensor,
    Xv: torch.Tensor,
    yv: torch.Tensor,
    Xc: torch.Tensor,
    yc: torch.Tensor,
    seed: int,
    params: float,
    flops: float,
    checkpoint_dir: str,
    case_key: str,
    save_checkpoints: bool,
) -> Dict[str, Any]:
    dev = next(model.parameters()).device
    seed_all(seed, dev)
    opt = optim.SGD(model.parameters(), lr=CFG_SUPP.target_lr)
    Xd, yd = Xs.to(dev).contiguous(), ys.to(dev).contiguous()
    primary = set(int(s) for s in CFG_SUPP.trajectory_checkpoints)
    dense = set(range(CFG_SUPP.dense_selection_start, CFG_SUPP.target_steps + 1))
    eval_steps = primary | dense
    trajectory: Dict[str, Any] = {}
    cumulative_adapt_seconds = 0.0

    def record(step: int) -> None:
        val = eval_metrics(model, Xv, yv)
        item: Dict[str, Any] = {
            "step": int(step),
            "validation": val,
            "cumulative_adaptation_seconds": float(cumulative_adapt_seconds),
        }
        if step in primary:
            item["support_mse"] = _support_mse(model, Xs, ys)
            item["check"] = eval_metrics(model, Xc, yc)
            if save_checkpoints:
                ckpt_path = os.path.join(
                    checkpoint_dir,
                    case_key,
                    token,
                    f"step_{step:02d}.pt",
                )
                _atomic_torch_save(
                    {
                        "case_key": case_key,
                        "token": token,
                        "arch_idx": int(idx),
                        "loader": loader,
                        "step": int(step),
                        "target_seed": int(seed),
                        "state_dict": {
                            k: v.detach().cpu().clone()
                            for k, v in model.state_dict().items()
                        },
                    },
                    ckpt_path,
                )
                item["checkpoint_path"] = os.path.relpath(
                    ckpt_path, start=os.path.dirname(checkpoint_dir)
                ).replace("\\", "/")
        trajectory[str(step)] = item

    record(0)
    for step in range(1, CFG_SUPP.target_steps + 1):
        model.train()
        _sync(dev)
        t0 = time.perf_counter()
        opt.zero_grad(set_to_none=True)
        loss = ((model(Xd) - yd) ** 2).mean()
        if not torch.isfinite(loss):
            raise RuntimeError(f"Non-finite trajectory loss: {case_key}/{token}")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            model.parameters(), CFG_SUPP.target_grad_clip
        )
        opt.step()
        _sync(dev)
        cumulative_adapt_seconds += time.perf_counter() - t0
        if step in eval_steps:
            record(step)

    return {
        "token": token,
        "loader": loader,
        "arch_idx": int(idx),
        "arch_key": str(spec.arch_key),
        "family": str(spec.family),
        "params": float(params),
        "flops": float(flops),
        "target_seed": int(seed),
        "optimizer": "SGD",
        "loss": "MSE",
        "learning_rate": float(CFG_SUPP.target_lr),
        "gradient_clip": float(CFG_SUPP.target_grad_clip),
        "early_stopping": False,
        "trajectory": trajectory,
        "complete": True,
    }


def _trajectory_case_analysis(candidate_map: Mapping[str, Any]) -> Dict[str, Any]:
    tokens = sorted(candidate_map)
    steps = sorted(
        int(s) for s in next(iter(candidate_map.values()))["trajectory"]
    )
    primary = [int(x) for x in CFG_SUPP.trajectory_checkpoints]
    orders: Dict[int, List[str]] = {}
    selections: Dict[int, Dict[str, Any]] = {}
    best_alternatives: Dict[int, Optional[str]] = {}

    for step in steps:
        rows: List[Dict[str, Any]] = []
        for token in tokens:
            cand = candidate_map[token]
            point = cand["trajectory"][str(step)]
            rows.append(
                {
                    "token": token,
                    "arch_idx": int(cand["arch_idx"]),
                    "params": float(cand["params"]),
                    "flops": float(cand["flops"]),
                    "hard_feasible": True,
                    "validation": point["validation"],
                }
            )
        order = [str(r["token"]) for r in sorted(rows, key=_candidate_lex)]
        orders[step] = order
        selection = _select_anchor_safe(
            rows,
            order,
            anchor_token="PT_A57",
            margin_rel=CFG_SUPP.frozen_margin_rel,
        )
        selections[step] = selection
        alternatives = [t for t in order if t != "PT_A57"]
        best_alternatives[step] = alternatives[0] if alternatives else None

    order50 = orders[50]
    selector50 = selections[50]["selected_token"]
    best50 = best_alternatives[50]
    stability = {}
    for step in primary:
        stability[str(step)] = {
            "spearman_rank_vs_step50": _spearman_from_orders(
                orders[step], order50
            ),
            "best_alternative_matches_step50": (
                best_alternatives[step] == best50
            ),
            "selected_token": selections[step]["selected_token"],
            "selected_matches_step50": (
                selections[step]["selected_token"] == selector50
            ),
            "switched": bool(selections[step]["switched"]),
        }

    dense_tokens = [
        str(selections[s]["selected_token"])
        for s in range(CFG_SUPP.dense_selection_start, 51)
    ]
    transitions = sum(
        int(dense_tokens[i] != dense_tokens[i - 1])
        for i in range(1, len(dense_tokens))
    )
    return {
        "orders": {str(k): v for k, v in orders.items() if k in primary},
        "selections": {
            str(k): v for k, v in selections.items() if k in primary
        },
        "stability": stability,
        "selection_trace_20_50": {
            "tokens": dense_tokens,
            "transition_count": int(transitions),
            "unique_selected_tokens": sorted(set(dense_tokens)),
            "selected_at_20": dense_tokens[0],
            "selected_at_50": dense_tokens[-1],
            "changed_between_20_and_50": dense_tokens[0]
            != dense_tokens[-1],
        },
    }


def run_adaptation_trajectory(
    project_root: str,
    out_path: Optional[str],
    device: str,
    safe_mode: str,
    smoke: bool = False,
    save_checkpoints: Optional[bool] = None,
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    _require_preflight(root)
    paths = _result_paths(root)
    if out_path is None:
        out_path = (
            paths["trajectory"].replace(".json", "_smoke.json")
            if smoke
            else paths["trajectory"]
        )
    save_checkpoints = (
        CFG_SUPP.save_model_checkpoints
        if save_checkpoints is None
        else bool(save_checkpoints)
    )
    cfg, cache, A, requested, safe = build_runtime(
        device, safe_mode, (CFG_SUPP.trajectory_pool,)
    )
    L = int(cfg.main.task.L)
    frozen = load_frozen_assets(root)
    strong_manifest = _load_strong_manifest(
        root, os.path.join(root, CFG_SUPP.c31_bank_manifest_path)
    )
    jobs = _jobs(CFG_SUPP.trajectory_pool, smoke)
    run_mode = "smoke" if smoke else "formal"
    upstream_hashes = _upstream_hashes(root, include_external=False)
    result = (
        load_json(out_path)
        if os.path.isfile(out_path)
        else {
            "study": "fixed_50_step_adaptation_trajectory",
            "decision": "TRAJECTORY_IN_PROGRESS",
            "run_mode": run_mode,
            "protocol": config_dict(),
            "pool": list(CFG_SUPP.trajectory_pool),
            "records": {},
            "upstream_hashes": upstream_hashes,
            "selection_uses_test": False,
            "test_used": False,
            "method_retuning_allowed": False,
            "save_model_checkpoints": bool(save_checkpoints),
        }
    )
    if result.get("run_mode") != run_mode:
        raise RuntimeError("Smoke/formal trajectory outputs cannot share one file")
    if result.get("upstream_hashes", upstream_hashes) != upstream_hashes:
        raise RuntimeError("Frozen upstream asset changed during trajectory run")
    records: Dict[str, Any] = dict(result.get("records", {}))
    started = time.perf_counter()
    completed_candidates = sum(
        len(r.get("candidates", {})) for r in records.values()
    )
    total_planned_estimate = len(jobs) * 7

    for case_no, (cid, H, K) in enumerate(jobs, 1):
        Xs, ys, Xv, yv, Xc, yc, tier, ctype = get_support_validation_check(
            cfg, cache, cid, H, K
        )
        case_key = f"c{cid}_h{H}_k{K}_b{tier}"
        if case_key in records and bool(records[case_key].get("complete")):
            continue
        input_dim = int(Xs.shape[-1])
        feasible = set(feasible_indices(cfg, A, tier, L, input_dim, H))
        if CFG_SUPP.anchor_arch_idx not in feasible:
            raise RuntimeError(f"A57 infeasible in trajectory case {case_key}")
        plan = _trajectory_candidate_plan(feasible)
        seed = CFG_SUPP.train_seed + 1009 * cid + 37 * H + 53 * K
        case_record = dict(
            records.get(
                case_key,
                {
                    "complete": False,
                    "case_key": case_key,
                    "center_id": int(cid),
                    "center_type": str(ctype),
                    "budget_tier": str(tier),
                    "H": int(H),
                    "K": int(K),
                    "target_seed": int(seed),
                    "candidates": {},
                    "test_used": False,
                },
            )
        )
        candidates = dict(case_record.get("candidates", {}))
        case_started = time.perf_counter()

        for cand_no, (token, idx, loader) in enumerate(plan, 1):
            if token in candidates and bool(candidates[token].get("complete")):
                continue
            spec = A[idx]
            actual = candidate_device(spec, requested, safe)
            with candidate_backend_context(spec, actual, safe):
                model = _load_trajectory_candidate(
                    root,
                    strong_manifest,
                    frozen,
                    A,
                    H=H,
                    idx=idx,
                    loader=loader,
                    input_dim=input_dim,
                    L=L,
                    device=actual,
                )
                params, flops = profile_arch(
                    spec, L=L, input_dim=input_dim, H=H
                )
                candidates[token] = _trajectory_one_candidate(
                    model=model,
                    token=token,
                    idx=idx,
                    loader=loader,
                    spec=spec,
                    Xs=Xs,
                    ys=ys,
                    Xv=Xv,
                    yv=yv,
                    Xc=Xc,
                    yc=yc,
                    seed=seed,
                    params=float(params),
                    flops=float(flops),
                    checkpoint_dir=paths["trajectory_checkpoints"],
                    case_key=case_key,
                    save_checkpoints=save_checkpoints,
                )
                del model
                synchronize_if_cuda(actual)
            completed_candidates += 1
            case_record["candidates"] = candidates
            records[case_key] = case_record
            result["records"] = records
            atomic_json(result, out_path)
            elapsed = time.perf_counter() - started
            avg = elapsed / max(1, completed_candidates)
            remaining = max(0, total_planned_estimate - completed_candidates)
            print(
                f"[Trajectory] case={case_no}/{len(jobs)} "
                f"candidate={cand_no}/{len(plan)} {case_key}/{token} "
                f"completed_candidates={completed_candidates} "
                f"gradient_steps={completed_candidates*50} "
                f"elapsed={elapsed/3600:.2f}h eta~={avg*remaining/3600:.2f}h "
                f"finish~={_eta_clock(avg*remaining)}",
                flush=True,
            )
            gc.collect()
            if requested.type == "cuda":
                torch.cuda.empty_cache()

        case_record["candidates"] = candidates
        case_record["analysis"] = _trajectory_case_analysis(candidates)
        case_record["complete"] = True
        case_record["case_seconds"] = float(time.perf_counter() - case_started)
        records[case_key] = case_record
        result["records"] = records
        result["N_records"] = len(records)
        result["expected_records"] = len(jobs)
        result["complete"] = len(records) == len(jobs) and all(
            bool(r.get("complete")) for r in records.values()
        )
        atomic_json(result, out_path)

    result["decision"] = (
        "PASS_FIXED_50_STEP_TRAJECTORY_COMPLETE"
        if result.get("complete")
        else "TRAJECTORY_INCOMPLETE"
    )
    atomic_json(result, out_path)
    if result.get("complete") and not smoke:
        summarize_adaptation_trajectory(root, result)
    return result


def summarize_adaptation_trajectory(
    project_root: str, obj: Optional[Mapping[str, Any]] = None
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    paths = _result_paths(root)
    obj = obj or load_json(paths["trajectory"])
    records = list(obj["records"].values())
    primary = [int(x) for x in CFG_SUPP.trajectory_checkpoints]
    candidate_rows: List[Dict[str, Any]] = []
    case_rows: List[Dict[str, Any]] = []
    checkpoint_rows: List[Dict[str, Any]] = []

    for rec in records:
        candidate_map = rec["candidates"]
        analysis = rec["analysis"]
        for token, cand in candidate_map.items():
            for step in primary:
                point = cand["trajectory"][str(step)]
                candidate_rows.append(
                    {
                        "case_key": rec["case_key"],
                        "center_id": rec["center_id"],
                        "H": rec["H"],
                        "K": rec["K"],
                        "budget_tier": rec["budget_tier"],
                        "token": token,
                        "arch_idx": cand["arch_idx"],
                        "step": step,
                        "support_mse": point["support_mse"],
                        "validation_wmse": point["validation"]["weighted_mse"],
                        "check_wmse": point["check"]["weighted_mse"],
                        "check_mae": point["check"]["mae"],
                        "check_worst10": point["check"]["worst10"],
                        "cumulative_adaptation_seconds": point[
                            "cumulative_adaptation_seconds"
                        ],
                    }
                )
        trace = analysis["selection_trace_20_50"]
        case_rows.append(
            {
                "case_key": rec["case_key"],
                "center_id": rec["center_id"],
                "H": rec["H"],
                "K": rec["K"],
                "budget_tier": rec["budget_tier"],
                "selected_at_20": trace["selected_at_20"],
                "selected_at_50": trace["selected_at_50"],
                "changed_20_to_50": trace["changed_between_20_and_50"],
                "selection_transitions_20_50": trace["transition_count"],
                "unique_selected_tokens_20_50": "|".join(
                    trace["unique_selected_tokens"]
                ),
                "rank_spearman_20_vs_50": analysis["stability"]["20"][
                    "spearman_rank_vs_step50"
                ],
                "selected_20_matches_50": analysis["stability"]["20"][
                    "selected_matches_step50"
                ],
            }
        )

    for step in primary:
        step_candidates = [r for r in candidate_rows if r["step"] == step]
        selected_check: List[float] = []
        selected_val: List[float] = []
        rank_rho: List[float] = []
        selector_agree: List[float] = []
        best_alt_agree: List[float] = []
        per_case_time: List[float] = []
        for rec in records:
            selected_token = rec["analysis"]["stability"][str(step)][
                "selected_token"
            ]
            point = rec["candidates"][selected_token]["trajectory"][str(step)]
            selected_check.append(float(point["check"]["weighted_mse"]))
            selected_val.append(float(point["validation"]["weighted_mse"]))
            rank_rho.append(
                float(
                    rec["analysis"]["stability"][str(step)][
                        "spearman_rank_vs_step50"
                    ]
                )
            )
            selector_agree.append(
                float(
                    rec["analysis"]["stability"][str(step)][
                        "selected_matches_step50"
                    ]
                )
            )
            best_alt_agree.append(
                float(
                    rec["analysis"]["stability"][str(step)][
                        "best_alternative_matches_step50"
                    ]
                )
            )
            per_case_time.append(
                sum(
                    float(c["trajectory"][str(step)]["cumulative_adaptation_seconds"])
                    for c in rec["candidates"].values()
                )
            )
        checkpoint_rows.append(
            {
                "step": step,
                "candidate_check_wmse_mean": _mean(
                    r["check_wmse"] for r in step_candidates
                ),
                "selected_check_wmse_mean": _mean(selected_check),
                "selected_validation_wmse_mean": _mean(selected_val),
                "rank_spearman_vs_50_mean": _mean(rank_rho),
                "selector_agreement_with_50": _mean(selector_agree),
                "best_alternative_agreement_with_50": _mean(best_alt_agree),
                "cumulative_adaptation_seconds_per_case_mean": _mean(
                    per_case_time
                ),
            }
        )

    by_step = {int(r["step"]): r for r in checkpoint_rows}
    ref0 = float(by_step[0]["selected_check_wmse_mean"])
    ref20 = float(by_step[20]["selected_check_wmse_mean"])
    for row in checkpoint_rows:
        value = float(row["selected_check_wmse_mean"])
        row["selected_check_reduction_vs_step0"] = _rel_gain(value, ref0)
        row["selected_check_reduction_vs_step20"] = _rel_gain(value, ref20)

    summary = {
        "study": "fixed_50_step_adaptation_trajectory_summary",
        "decision": "PASS_TRAJECTORY_SUMMARY_GENERATED",
        "N_cases": len(records),
        "N_candidate_checkpoint_rows": len(candidate_rows),
        "checkpoints": checkpoint_rows,
        "stability_20_to_50": {
            "changed_case_rate": _mean(
                float(r["changed_20_to_50"]) for r in case_rows
            ),
            "mean_transition_count": _mean(
                r["selection_transitions_20_50"] for r in case_rows
            ),
            "zero_transition_case_rate": _mean(
                float(r["selection_transitions_20_50"] == 0)
                for r in case_rows
            ),
            "mean_rank_spearman_20_vs_50": _mean(
                r["rank_spearman_20_vs_50"] for r in case_rows
            ),
            "selected_20_matches_50_rate": _mean(
                float(r["selected_20_matches_50"]) for r in case_rows
            ),
        },
        "claim_boundary": (
            "The result may support sufficiency under the evaluated fixed "
            "protocol if the 20-to-50 loss and ranking changes are small. "
            "It does not establish global optimality of 50 steps."
        ),
        "test_used": False,
    }
    atomic_json(
        summary,
        os.path.join(paths["trajectory_dir"], "trajectory_summary.json"),
    )
    _write_csv(
        os.path.join(paths["trajectory_dir"], "trajectory_checkpoint_summary.csv"),
        checkpoint_rows,
    )
    _write_csv(
        os.path.join(paths["trajectory_dir"], "trajectory_case_stability.csv"),
        case_rows,
    )
    _write_csv(
        os.path.join(paths["trajectory_dir"], "trajectory_candidate_checkpoints.csv"),
        candidate_rows,
    )
    return summary


# ---------------------------------------------------------------------------
# Experiment 2: Full vs No-anchor risk analysis from existing candidates
# ---------------------------------------------------------------------------


def analyze_anchor_risk(
    project_root: str, out_path: Optional[str] = None
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    _require_preflight(root)
    paths = _result_paths(root)
    out_path = out_path or paths["anchor_risk"]
    source_path = os.path.join(root, CFG_SUPP.ablation_candidates_path)
    source = load_json(source_path)
    if not bool(source.get("complete")):
        raise RuntimeError("Ablation candidate result is incomplete")

    variants = ("full_method", "without_anchor_protection")
    case_rows: List[Dict[str, Any]] = []
    by_variant: Dict[str, List[Dict[str, Any]]] = {v: [] for v in variants}

    for case_key, rec in sorted(source["records"].items()):
        token_map = {str(r["token"]): r for r in rec["candidates"]}
        anchor = token_map["PT_A57"]
        anchor_mse = float(anchor["test"]["weighted_mse"])
        row: Dict[str, Any] = {
            "case_key": case_key,
            "center_id": int(rec["center_id"]),
            "H": int(rec["H"]),
            "K": int(rec["K"]),
            "budget_tier": str(rec["budget_tier"]),
            "anchor_test_wmse": anchor_mse,
        }
        for variant in variants:
            sel = rec["variants"][variant]
            token = str(sel["selected_token"])
            selected_mse = float(sel["test"]["weighted_mse"])
            switched = token != "PT_A57"
            regret = float(
                (selected_mse - anchor_mse)
                / (abs(anchor_mse) + CFG_SUPP.eps)
            )
            tol = 1e-12
            beneficial = bool(switched and regret < -tol)
            harmful = bool(switched and regret > tol)
            equivalent = bool(switched and not beneficial and not harmful)
            item = {
                "case_key": case_key,
                "center_id": int(rec["center_id"]),
                "variant": variant,
                "selected_token": token,
                "selected_test_wmse": selected_mse,
                "anchor_test_wmse": anchor_mse,
                "switched": switched,
                "beneficial_switch": beneficial,
                "harmful_switch": harmful,
                "equivalent_switch": equivalent,
                "switch_regret": regret,
            }
            by_variant[variant].append(item)
            prefix = "full" if variant == "full_method" else "no_anchor"
            row.update(
                {
                    f"{prefix}_selected_token": token,
                    f"{prefix}_selected_test_wmse": selected_mse,
                    f"{prefix}_switched": switched,
                    f"{prefix}_beneficial_switch": beneficial,
                    f"{prefix}_harmful_switch": harmful,
                    f"{prefix}_switch_regret": regret,
                }
            )
        row["no_anchor_additional_switch"] = bool(
            row["no_anchor_switched"] and not row["full_switched"]
        )
        case_rows.append(row)

    summaries: List[Dict[str, Any]] = []
    for variant in variants:
        rows = by_variant[variant]
        switched = [r for r in rows if r["switched"]]
        beneficial = [r for r in rows if r["beneficial_switch"]]
        harmful = [r for r in rows if r["harmful_switch"]]
        regrets = [float(r["switch_regret"]) for r in switched]
        harmful_regrets = [float(r["switch_regret"]) for r in harmful]
        summaries.append(
            {
                "variant": variant,
                "N_cases": len(rows),
                "N_switches": len(switched),
                "switch_rate": len(switched) / max(1, len(rows)),
                "N_beneficial_switches": len(beneficial),
                "beneficial_switch_rate_all_cases": len(beneficial)
                / max(1, len(rows)),
                "N_harmful_switches": len(harmful),
                "harmful_switch_rate_all_cases": len(harmful)
                / max(1, len(rows)),
                "beneficial_precision_among_switches": len(beneficial)
                / max(1, len(switched)),
                "mean_switch_regret": _mean(regrets),
                "median_switch_regret": (
                    float(np.median(regrets)) if regrets else None
                ),
                "worst10_switch_loss_cvar90": _cvar90(regrets),
                "harmful_switch_regret_mean": _mean(harmful_regrets),
                "harmful_switch_regret_cvar90": _cvar90(harmful_regrets),
                "max_switch_regret": max(regrets) if regrets else None,
                "test_wmse_mean": _mean(
                    r["selected_test_wmse"] for r in rows
                ),
            }
        )

    additional = [r for r in case_rows if r["no_anchor_additional_switch"]]
    comparison = {
        "N_additional_no_anchor_switches": len(additional),
        "additional_beneficial": sum(
            int(r["no_anchor_beneficial_switch"]) for r in additional
        ),
        "additional_harmful": sum(
            int(r["no_anchor_harmful_switch"]) for r in additional
        ),
        "additional_equivalent": sum(
            int(
                not r["no_anchor_beneficial_switch"]
                and not r["no_anchor_harmful_switch"]
            )
            for r in additional
        ),
        "paired_test_wmse_difference_no_anchor_minus_full": _mean(
            float(r["no_anchor_selected_test_wmse"])
            - float(r["full_selected_test_wmse"])
            for r in case_rows
        ),
    }
    obj = {
        "study": "full_vs_no_anchor_risk_from_existing_candidate_results",
        "decision": "PASS_ANCHOR_RISK_ANALYSIS_COMPLETE",
        "source_path": source_path,
        "source_sha256": file_sha256(source_path),
        "metric_definition": {
            "switch_regret": (
                "(selected_test_wmse-anchor_test_wmse)/anchor_test_wmse"
            ),
            "beneficial_switch": "switched and switch_regret < 0",
            "harmful_switch": "switched and switch_regret > 0",
            "worst10_switch_loss": (
                "mean of the largest ceil(10% * N_switched) switch regrets"
            ),
        },
        "summary": summaries,
        "comparison": comparison,
        "case_records": case_rows,
        "no_new_model_run": True,
        "selection_retuning": False,
    }
    atomic_json(obj, out_path)
    _write_csv(
        os.path.join(paths["anchor_risk_dir"], "full_vs_no_anchor_risk_summary.csv"),
        summaries,
    )
    _write_csv(
        os.path.join(paths["anchor_risk_dir"], "full_vs_no_anchor_risk_cases.csv"),
        case_rows,
    )
    return obj


# ---------------------------------------------------------------------------
# Experiment 3: five-repeat CUDA-synchronized online time
# ---------------------------------------------------------------------------


def _execute_online_method(
    *,
    method: str,
    project_root: str,
    strong_manifest: Mapping[str, Any],
    source_manifest: Mapping[str, Any],
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
) -> Tuple[nn.Module, Dict[str, Any], int, int]:
    if method == "ours_c32_locked":
        model, _spec, row, selector, candidate_count, adapted_count = _run_ours_case(
            project_root,
            strong_manifest,
            frozen,
            cfg,
            A,
            requested,
            safe_mode,
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
        return model, {"row": row, "selector": selector}, candidate_count, adapted_count

    if method in ("pt_ft", "medet_style"):
        model, spec, idx = _load_fixed_source_model(
            project_root,
            source_manifest,
            method,
            H,
            tier,
            A,
            input_dim,
            L,
            requested,
        )
        if idx not in feasible_indices(cfg, A, tier, L, input_dim, H):
            raise RuntimeError(f"Frozen {method} A57 is infeasible")
        from main_evaluation.pipeline import _fixed_target_adapt

        _fixed_target_adapt(model, Xs, ys, seed=seed)
        val = eval_metrics(model, Xv, yv)
        return (
            model,
            {"row": {"arch_idx": idx, "validation": val}, "selector": "fixed_A57"},
            1,
            1,
        )

    if method == "scratch50":
        from main_evaluation.pipeline import _fixed_target_adapt

        idx = CFG_SUPP.anchor_arch_idx
        if idx not in feasible_indices(cfg, A, tier, L, input_dim, H):
            raise RuntimeError("Scratch A57 is infeasible")
        seed_all(seed, requested)
        model = build_model(
            A[idx], input_dim=input_dim, H=H, L=L, device=str(requested)
        )
        _fixed_target_adapt(model, Xs, ys, seed=seed)
        val = eval_metrics(model, Xv, yv)
        return (
            model,
            {"row": {"arch_idx": idx, "validation": val}, "selector": "scratch_A57"},
            1,
            1,
        )

    model, _spec, row, selector, candidate_count, adapted_count = _run_search_case(
        method,
        frozen,
        cfg,
        A,
        requested,
        safe_mode,
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
    return model, {"row": row, "selector": selector}, candidate_count, adapted_count


def run_repeated_runtime(
    project_root: str,
    out_path: Optional[str],
    device: str,
    safe_mode: str,
    smoke: bool = False,
    repeats: Optional[int] = None,
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    _require_preflight(root)
    paths = _result_paths(root)
    if out_path is None:
        out_path = (
            paths["runtime"].replace(".json", "_smoke.json")
            if smoke
            else paths["runtime"]
        )
    requested_device = torch.device(device)
    if requested_device.type != "cuda" and not smoke:
        raise RuntimeError(
            "Formal repeated runtime must use CUDA. Use --smoke for CPU checks only."
        )
    repeats = int(repeats or CFG_SUPP.runtime_repeats)
    if repeats < 5 and not smoke:
        raise ValueError("Formal runtime evidence requires at least five repeats")

    cfg, cache, A, requested, safe = build_runtime(
        device, safe_mode, (CFG_SUPP.runtime_pool,)
    )
    L = int(cfg.main.task.L)
    frozen = load_frozen_assets(root)
    strong_manifest = _load_strong_manifest(
        root, os.path.join(root, CFG_SUPP.c31_bank_manifest_path)
    )
    source_manifest = _load_external_source_manifest(root)
    jobs = _jobs(CFG_SUPP.runtime_pool, smoke)
    methods = list(CFG_SUPP.runtime_methods)
    run_mode = "smoke" if smoke else "formal"
    upstream_hashes = _upstream_hashes(root, include_external=True)
    result = (
        load_json(out_path)
        if os.path.isfile(out_path)
        else {
            "study": "cuda_synchronized_repeated_online_runtime",
            "decision": "RUNTIME_IN_PROGRESS",
            "run_mode": run_mode,
            "protocol": config_dict(),
            "upstream_hashes": upstream_hashes,
            "timer_scope": (
                "candidate instantiation, prior restoration, target adaptation, "
                "validation evaluation, and final selection; excludes data "
                "construction, Check, Test, reporting, and source training"
            ),
            "records": {},
            "repeats": int(repeats),
            "methods": list(methods),
            "pool": list(CFG_SUPP.runtime_pool),
            "warmup_complete": False,
            "test_used": False,
            "check_used": False,
            "environment": {
                "python": platform.python_version(),
                "torch": torch.__version__,
                "device_request": str(requested),
                "cuda_available": torch.cuda.is_available(),
                "cuda_device_name": (
                    torch.cuda.get_device_name(requested)
                    if requested.type == "cuda"
                    else None
                ),
                "cuda_version": torch.version.cuda,
                "cudnn_version": (
                    torch.backends.cudnn.version()
                    if torch.backends.cudnn.is_available()
                    else None
                ),
            },
        }
    )
    if result.get("run_mode") != run_mode:
        raise RuntimeError("Smoke/formal runtime outputs cannot share one file")
    if result.get("upstream_hashes", upstream_hashes) != upstream_hashes:
        raise RuntimeError("Frozen upstream asset changed during runtime study")
    if int(result.get("repeats", repeats)) != repeats:
        raise RuntimeError("Runtime repeat count changed after the run began")
    if tuple(result.get("methods", methods)) != tuple(methods):
        raise RuntimeError("Runtime method list changed after the run began")
    if tuple(result.get("pool", CFG_SUPP.runtime_pool)) != tuple(CFG_SUPP.runtime_pool):
        raise RuntimeError("Runtime pool changed after the run began")
    records: Dict[str, Any] = dict(result.get("records", {}))

    # One unreported warm-up per method on the first case.
    if not bool(result.get("warmup_complete")):
        cid, H, K = jobs[0]
        Xs, ys, Xv, yv, _Xc, _yc, tier, _ctype = get_support_validation_check(
            cfg, cache, cid, H, K
        )
        input_dim = int(Xs.shape[-1])
        seed = CFG_SUPP.train_seed + 1009 * cid + 37 * H + 53 * K
        for method in methods:
            for _ in range(CFG_SUPP.runtime_warmups_per_method):
                model, _info, _n, _a = _execute_online_method(
                    method=method,
                    project_root=root,
                    strong_manifest=strong_manifest,
                    source_manifest=source_manifest,
                    frozen=frozen,
                    cfg=cfg,
                    A=A,
                    requested=requested,
                    safe_mode=safe,
                    Xs=Xs,
                    ys=ys,
                    Xv=Xv,
                    yv=yv,
                    tier=tier,
                    H=H,
                    input_dim=input_dim,
                    L=L,
                    seed=seed,
                )
                del model
                _sync(requested)
                gc.collect()
                if requested.type == "cuda":
                    torch.cuda.empty_cache()
            print(f"[Runtime:Warmup] method={method} complete", flush=True)
        result["warmup_complete"] = True
        atomic_json(result, out_path)

    total = repeats * len(methods) * len(jobs)
    done = len(records)
    started = time.perf_counter()
    new_done = 0

    for repeat in range(repeats):
        # Deterministic rotation reduces method-order drift across repeats.
        shift = repeat % len(methods)
        method_order = methods[shift:] + methods[:shift]
        for method in method_order:
            for case_no, (cid, H, K) in enumerate(jobs, 1):
                Xs, ys, Xv, yv, _Xc, _yc, tier, ctype = get_support_validation_check(
                    cfg, cache, cid, H, K
                )
                case_key = f"c{cid}_h{H}_k{K}_b{tier}"
                key = f"r{repeat+1}_{method}_{case_key}"
                if key in records and bool(records[key].get("complete")):
                    continue
                input_dim = int(Xs.shape[-1])
                seed = CFG_SUPP.train_seed + 1009 * cid + 37 * H + 53 * K
                _sync(requested)
                t0 = time.perf_counter()
                model, info, candidate_count, adapted_count = _execute_online_method(
                    method=method,
                    project_root=root,
                    strong_manifest=strong_manifest,
                    source_manifest=source_manifest,
                    frozen=frozen,
                    cfg=cfg,
                    A=A,
                    requested=requested,
                    safe_mode=safe,
                    Xs=Xs,
                    ys=ys,
                    Xv=Xv,
                    yv=yv,
                    tier=tier,
                    H=H,
                    input_dim=input_dim,
                    L=L,
                    seed=seed,
                )
                _sync(requested)
                elapsed = float(time.perf_counter() - t0)
                selected_arch = int(info["row"]["arch_idx"])
                records[key] = {
                    "complete": True,
                    "repeat": int(repeat + 1),
                    "method": method,
                    "case_key": case_key,
                    "center_id": int(cid),
                    "center_type": str(ctype),
                    "budget_tier": str(tier),
                    "H": int(H),
                    "K": int(K),
                    "online_seconds": elapsed,
                    "candidate_count": int(candidate_count),
                    "adapted_candidate_count": int(adapted_count),
                    "selected_arch_idx": selected_arch,
                    "target_seed": int(seed),
                    "cuda_synchronized": requested.type == "cuda",
                    "test_used": False,
                    "check_used": False,
                }
                del model
                done += 1
                new_done += 1
                result["records"] = records
                result["N_records"] = len(records)
                result["expected_records"] = total
                result["complete"] = len(records) == total
                atomic_json(result, out_path)
                wall = time.perf_counter() - started
                avg = wall / max(1, new_done)
                eta = avg * max(0, total - done)
                print(
                    f"[Runtime] repeat={repeat+1}/{repeats} "
                    f"method={method} case={case_no}/{len(jobs)} {case_key} "
                    f"online={elapsed:.4f}s candidates={candidate_count} "
                    f"adapted={adapted_count} progress={done}/{total} "
                    f"elapsed={wall/3600:.2f}h eta={eta/3600:.2f}h "
                    f"finish~={_eta_clock(eta)}",
                    flush=True,
                )
                gc.collect()
                if requested.type == "cuda":
                    torch.cuda.empty_cache()

    result["decision"] = (
        "PASS_REPEATED_CUDA_RUNTIME_COMPLETE"
        if result.get("complete") and requested.type == "cuda" and repeats >= 5
        else (
            "PASS_RUNTIME_SMOKE_COMPLETE"
            if result.get("complete") and smoke
            else "RUNTIME_INCOMPLETE"
        )
    )
    atomic_json(result, out_path)
    if result.get("complete") and not smoke:
        summarize_repeated_runtime(root, result)
    return result


def summarize_repeated_runtime(
    project_root: str, obj: Optional[Mapping[str, Any]] = None
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    paths = _result_paths(root)
    obj = obj or load_json(paths["runtime"])
    records = list(obj["records"].values())
    raw_rows = sorted(
        records,
        key=lambda r: (int(r["repeat"]), str(r["method"]), str(r["case_key"])),
    )
    summary_rows: List[Dict[str, Any]] = []
    repeat_rows: List[Dict[str, Any]] = []
    for method in CFG_SUPP.runtime_methods:
        rows = [r for r in records if r["method"] == method]
        vals = np.asarray([float(r["online_seconds"]) for r in rows], dtype=float)
        repeat_means: List[float] = []
        for repeat in sorted(set(int(r["repeat"]) for r in rows)):
            rv = [
                float(r["online_seconds"])
                for r in rows
                if int(r["repeat"]) == repeat
            ]
            repeat_mean = _mean(rv)
            repeat_means.append(repeat_mean)
            repeat_rows.append(
                {
                    "method": method,
                    "repeat": repeat,
                    "N_cases": len(rv),
                    "mean_seconds": repeat_mean,
                    "median_seconds": float(np.median(rv)),
                }
            )
        summary_rows.append(
            {
                "method": method,
                "N_observations": int(vals.size),
                "N_repeats": len(repeat_means),
                "mean_seconds": float(vals.mean()),
                "std_seconds": float(vals.std(ddof=1)) if vals.size > 1 else 0.0,
                "median_seconds": float(np.median(vals)),
                "q1_seconds": float(np.quantile(vals, 0.25)),
                "q3_seconds": float(np.quantile(vals, 0.75)),
                "min_seconds": float(vals.min()),
                "max_seconds": float(vals.max()),
                "repeat_mean_std_seconds": (
                    float(np.std(repeat_means, ddof=1))
                    if len(repeat_means) > 1
                    else 0.0
                ),
                "adapted_candidates_mean": _mean(
                    r["adapted_candidate_count"] for r in rows
                ),
            }
        )
    summary = {
        "study": "cuda_synchronized_repeated_online_runtime_summary",
        "decision": "PASS_RUNTIME_SUMMARY_GENERATED",
        "environment": obj.get("environment", {}),
        "timer_scope": obj.get("timer_scope"),
        "summary": summary_rows,
        "test_used": False,
        "check_used": False,
    }
    atomic_json(
        summary, os.path.join(paths["runtime_dir"], "repeated_runtime_summary.json")
    )
    _write_csv(
        os.path.join(paths["runtime_dir"], "repeated_runtime_raw.csv"), raw_rows
    )
    _write_csv(
        os.path.join(paths["runtime_dir"], "repeated_runtime_repeat_means.csv"),
        repeat_rows,
    )
    _write_csv(
        os.path.join(paths["runtime_dir"], "repeated_runtime_summary.csv"),
        summary_rows,
    )
    return summary


# ---------------------------------------------------------------------------
# Experiment 4: optimizer-matched 12-candidate control (optional enhancement)
# ---------------------------------------------------------------------------


def _proxy_and_source_ranks(
    *,
    feasible: Sequence[int],
    frozen: Mapping[str, Any],
    A: Sequence[Any],
    requested: torch.device,
    safe_mode: str,
    Xs: torch.Tensor,
    ys: torch.Tensor,
    H: int,
    input_dim: int,
    L: int,
    seed: int,
) -> Tuple[Dict[int, float], Dict[int, float], Dict[int, float]]:
    Xp, yp = _sample_proxy_batch(Xs.to(requested), ys.to(requested), seed=seed)
    proxy_raw: Dict[int, float] = {}
    for idx in feasible:
        spec = A[idx]
        actual = candidate_device(spec, requested, safe_mode)
        with candidate_backend_context(spec, actual, safe_mode):
            seed_all(seed + int(idx), actual)
            model = build_model(
                spec, input_dim=input_dim, H=H, L=L, device=str(actual)
            )
            proxy_raw[int(idx)] = _entropy_proxy(
                model, Xp.to(actual), yp.to(actual)
            )
            del model
            synchronize_if_cuda(actual)
    proxy_rank = _rank_score(proxy_raw, larger_is_better=True)
    source_rank = _rank_score(
        {int(i): float(frozen["pi50"][i]) for i in feasible},
        larger_is_better=True,
    )
    fused = {
        int(i): CFG_SUPP.matched_meta_prior_weight * source_rank[int(i)]
        + CFG_SUPP.matched_meta_proxy_weight * proxy_rank[int(i)]
        for i in feasible
    }
    return source_rank, proxy_rank, fused


def _top_indices(scores: Mapping[int, float], count: int) -> List[int]:
    return [
        int(i)
        for i, _v in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[
            : int(count)
        ]
    ]


def _common12_indices(
    feasible: Sequence[int], fused: Mapping[int, float]
) -> List[int]:
    anchor = CFG_SUPP.anchor_arch_idx
    if anchor not in feasible:
        raise RuntimeError("A57 is infeasible in optimizer control")
    alternatives = [i for i in _top_indices(fused, len(fused)) if i != anchor]
    return [anchor] + alternatives[: CFG_SUPP.matched_candidate_budget - 1]


def _adapt_c1_union(
    *,
    indices: Sequence[int],
    frozen: Mapping[str, Any],
    A: Sequence[Any],
    requested: torch.device,
    safe_mode: str,
    Xs: torch.Tensor,
    ys: torch.Tensor,
    Xv: torch.Tensor,
    yv: torch.Tensor,
    Xc: torch.Tensor,
    yc: torch.Tensor,
    H: int,
    input_dim: int,
    L: int,
    seed: int,
    case_key: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, torch.Tensor]]]:
    from main_evaluation.pipeline import _fixed_target_adapt

    rows: List[Dict[str, Any]] = []
    states: Dict[str, Dict[str, torch.Tensor]] = {}
    for pos, idx in enumerate(indices, 1):
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
            # The same case seed is deliberately used for all candidates.
            _fixed_target_adapt(model, Xs, ys, seed=seed)
            val = eval_metrics(model, Xv, yv)
            chk = eval_metrics(model, Xc, yc)
            params, flops = profile_arch(spec, L=L, input_dim=input_dim, H=H)
            token = f"C1_A{idx}"
            rows.append(
                {
                    "token": token,
                    "arch_idx": int(idx),
                    "arch_key": str(spec.arch_key),
                    "family": str(spec.family),
                    "params": float(params),
                    "flops": float(flops),
                    "hard_feasible": True,
                    "validation": val,
                    "check": chk,
                    "target_seed": int(seed),
                    "target_optimizer": "SGD",
                    "target_loss": "MSE",
                    "target_steps": 50,
                    "target_lr": CFG_SUPP.target_lr,
                }
            )
            states[token] = {
                k: v.detach().cpu().clone() for k, v in model.state_dict().items()
            }
            del model
            synchronize_if_cuda(actual)
        print(
            f"[OptimizerControl] {case_key} adapted_union_candidate="
            f"{pos}/{len(indices)} A{idx}",
            flush=True,
        )
    return rows, states


def run_optimizer_matched_control(
    project_root: str,
    out_path: Optional[str],
    device: str,
    safe_mode: str,
    smoke: bool = False,
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    _require_preflight(root)
    paths = _result_paths(root)
    if out_path is None:
        out_path = (
            paths["optimizer"].replace(".json", "_smoke.json")
            if smoke
            else paths["optimizer"]
        )
    cfg, cache, A, requested, safe = build_runtime(
        device, safe_mode, (CFG_SUPP.optimizer_control_pool,)
    )
    L = int(cfg.main.task.L)
    frozen = load_frozen_assets(root)
    strong_manifest = _load_strong_manifest(
        root, os.path.join(root, CFG_SUPP.c31_bank_manifest_path)
    )
    jobs = _jobs(CFG_SUPP.optimizer_control_pool, smoke)
    run_mode = "smoke" if smoke else "formal"
    upstream_hashes = _upstream_hashes(root, include_external=False)
    result = (
        load_json(out_path)
        if os.path.isfile(out_path)
        else {
            "study": "optimizer_matched_12_candidate_control",
            "decision": "OPTIMIZER_CONTROL_IN_PROGRESS",
            "run_mode": run_mode,
            "protocol": config_dict(),
            "upstream_hashes": upstream_hashes,
            "pool": list(CFG_SUPP.optimizer_control_pool),
            "records": {},
            "selection_uses_check": False,
            "selection_uses_test": False,
            "test_opened_after_all_selectors_fixed": True,
            "method_retuning_allowed": False,
        }
    )
    if result.get("run_mode") != run_mode:
        raise RuntimeError("Smoke/formal optimizer outputs cannot share one file")
    if result.get("upstream_hashes", upstream_hashes) != upstream_hashes:
        raise RuntimeError("Frozen upstream asset changed during optimizer control")
    records: Dict[str, Any] = dict(result.get("records", {}))
    started = time.perf_counter()
    new_cases = 0

    for case_no, (cid, H, K) in enumerate(jobs, 1):
        Xs, ys, Xv, yv, Xc, yc, tier, ctype = get_support_validation_check(
            cfg, cache, cid, H, K
        )
        case_key = f"c{cid}_h{H}_k{K}_b{tier}"
        if case_key in records and bool(records[case_key].get("complete")):
            continue
        input_dim = int(Xs.shape[-1])
        seed = CFG_SUPP.train_seed + 1009 * cid + 37 * H + 53 * K
        feasible = feasible_indices(cfg, A, tier, L, input_dim, H)
        if len(feasible) < CFG_SUPP.matched_candidate_budget:
            raise RuntimeError(
                f"Only {len(feasible)} feasible candidates in {case_key}; need 12"
            )

        source_rank, proxy_rank, fused = _proxy_and_source_ranks(
            feasible=feasible,
            frozen=frozen,
            A=A,
            requested=requested,
            safe_mode=safe,
            Xs=Xs,
            ys=ys,
            H=H,
            input_dim=input_dim,
            L=L,
            seed=seed,
        )
        meta12 = _top_indices(fused, CFG_SUPP.matched_candidate_budget)
        zero12 = _top_indices(proxy_rank, CFG_SUPP.matched_candidate_budget)
        common12 = _common12_indices(feasible, fused)
        union = sorted(set(meta12) | set(zero12) | set(common12))

        candidate_rows, states = _adapt_c1_union(
            indices=union,
            frozen=frozen,
            A=A,
            requested=requested,
            safe_mode=safe,
            Xs=Xs,
            ys=ys,
            Xv=Xv,
            yv=yv,
            Xc=Xc,
            yc=yc,
            H=H,
            input_dim=input_dim,
            L=L,
            seed=seed,
            case_key=case_key,
        )
        token_for = {int(r["arch_idx"]): str(r["token"]) for r in candidate_rows}
        meta_tokens = [token_for[i] for i in meta12]
        zero_tokens = [token_for[i] for i in zero12]
        common_tokens = [token_for[i] for i in common12]

        # All selectors are fixed before Test is materialized.
        selections = {
            "meta_top12_sgd_mse50_valbest": _select_val_best(
                candidate_rows, meta_tokens
            ),
            "zero_top12_sgd_mse50_valbest": _select_val_best(
                candidate_rows, zero_tokens
            ),
            "common12_sgd_mse50_valbest": _select_val_best(
                candidate_rows, common_tokens
            ),
            "common12_sgd_mse50_anchor_safe": _select_anchor_safe(
                candidate_rows,
                common_tokens,
                anchor_token=token_for[CFG_SUPP.anchor_arch_idx],
                margin_rel=CFG_SUPP.frozen_margin_rel,
            ),
        }

        # Frozen final Ours reference on the same untouched pool.
        (
            ours_model,
            ours_spec,
            ours_row,
            ours_selector,
            ours_candidate_count,
            ours_adapted_count,
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
        ours_state = {
            k: v.detach().cpu().clone() for k, v in ours_model.state_dict().items()
        }
        ours_check = eval_metrics(ours_model, Xc, yc)
        del ours_model

        # PT-A57 reference under the same SGD/MSE-50 recipe.
        from main_evaluation.pipeline import _fixed_target_adapt

        pt_spec = A[CFG_SUPP.anchor_arch_idx]
        pt_device = candidate_device(pt_spec, requested, safe)
        with candidate_backend_context(pt_spec, pt_device, safe):
            pt_model = _load_strong_model(
                root,
                strong_manifest,
                A,
                H=H,
                idx=CFG_SUPP.anchor_arch_idx,
                input_dim=input_dim,
                L=L,
                device=pt_device,
            )
            _fixed_target_adapt(pt_model, Xs, ys, seed=seed)
            pt_validation = eval_metrics(pt_model, Xv, yv)
            pt_check = eval_metrics(pt_model, Xc, yc)
            pt_state = {
                k: v.detach().cpu().clone()
                for k, v in pt_model.state_dict().items()
            }
            del pt_model
            synchronize_if_cuda(pt_device)

        # Test opens only now, after every selector above is frozen.
        Xt, yt = get_test_only(cfg, cache, cid, H, K)
        row_map = {str(r["token"]): r for r in candidate_rows}
        for token, state in states.items():
            row = row_map[token]
            idx = int(row["arch_idx"])
            spec = A[idx]
            actual = candidate_device(spec, requested, safe)
            with candidate_backend_context(spec, actual, safe):
                model = build_model(
                    spec,
                    input_dim=input_dim,
                    H=H,
                    L=L,
                    device=str(actual),
                )
                model.load_state_dict(state, strict=True)
                row["test"] = eval_metrics(model, Xt, yt)
                del model
                synchronize_if_cuda(actual)

        def eval_state(spec: Any, state: Mapping[str, torch.Tensor]) -> Dict[str, float]:
            actual = candidate_device(spec, requested, safe)
            with candidate_backend_context(spec, actual, safe):
                model = build_model(
                    spec,
                    input_dim=input_dim,
                    H=H,
                    L=L,
                    device=str(actual),
                )
                model.load_state_dict(state, strict=True)
                metrics = eval_metrics(model, Xt, yt)
                del model
                synchronize_if_cuda(actual)
                return metrics

        ours_test = eval_state(ours_spec, ours_state)
        pt_test = eval_state(pt_spec, pt_state)
        for sel in selections.values():
            selected = row_map[str(sel["selected_token"])]
            sel["validation"] = selected["validation"]
            sel["check"] = selected["check"]
            sel["test"] = selected["test"]

        # Test-oracle diagnostics are report-only and do not change selection.
        test_oracles: Dict[str, Any] = {}
        for name, tokens in {
            "meta12": meta_tokens,
            "zero12": zero_tokens,
            "common12": common_tokens,
        }.items():
            best = min(
                (row_map[t] for t in tokens),
                key=lambda r: (
                    float(r["test"]["weighted_mse"]),
                    float(r["params"]),
                    float(r["flops"]),
                    int(r["arch_idx"]),
                ),
            )
            test_oracles[name] = {
                "token": best["token"],
                "test": best["test"],
            }

        records[case_key] = {
            "complete": True,
            "case_key": case_key,
            "center_id": int(cid),
            "center_type": str(ctype),
            "budget_tier": str(tier),
            "H": int(H),
            "K": int(K),
            "target_seed": int(seed),
            "feasible_count": len(feasible),
            "meta12_indices": meta12,
            "zero12_indices": zero12,
            "common12_indices": common12,
            "adapted_union_indices": union,
            "source_rank": {str(k): float(v) for k, v in source_rank.items()},
            "proxy_rank": {str(k): float(v) for k, v in proxy_rank.items()},
            "fused_score": {str(k): float(v) for k, v in fused.items()},
            "candidate_rows": candidate_rows,
            "selections": selections,
            "ours_compact_anchor_safe": {
                "selected_token": ours_selector["selected_token"],
                "selected_arch_idx": int(ours_row["arch_idx"]),
                "candidate_count": int(ours_candidate_count),
                "adapted_candidate_count": int(ours_adapted_count),
                "selector": ours_selector,
                "validation": ours_row["validation"],
                "check": ours_check,
                "test": ours_test,
            },
            "pt_a57": {
                "selected_arch_idx": CFG_SUPP.anchor_arch_idx,
                "validation": pt_validation,
                "check": pt_check,
                "test": pt_test,
            },
            "test_oracles": test_oracles,
            "selection_uses_check": False,
            "selection_uses_test": False,
            "test_opened_after_all_selectors_fixed": True,
        }
        result["records"] = records
        result["N_records"] = len(records)
        result["expected_records"] = len(jobs)
        result["complete"] = len(records) == len(jobs) and all(
            bool(r.get("complete")) for r in records.values()
        )
        atomic_json(result, out_path)
        new_cases += 1
        elapsed = time.perf_counter() - started
        eta = elapsed / max(1, new_cases) * max(0, len(jobs) - len(records))
        print(
            f"[OptimizerControl] case={case_no}/{len(jobs)} {case_key} "
            f"union={len(union)} ours_adapted={ours_adapted_count} "
            f"elapsed={elapsed/3600:.2f}h eta={eta/3600:.2f}h "
            f"finish~={_eta_clock(eta)}",
            flush=True,
        )
        del states, ours_state, pt_state
        gc.collect()
        if requested.type == "cuda":
            torch.cuda.empty_cache()

    result["decision"] = (
        "PASS_OPTIMIZER_MATCHED_12_CANDIDATE_CONTROL_COMPLETE"
        if result.get("complete")
        else "OPTIMIZER_CONTROL_INCOMPLETE"
    )
    atomic_json(result, out_path)
    if result.get("complete") and not smoke:
        summarize_optimizer_matched_control(root, result)
    return result


def summarize_optimizer_matched_control(
    project_root: str, obj: Optional[Mapping[str, Any]] = None
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    paths = _result_paths(root)
    obj = obj or load_json(paths["optimizer"])
    records = list(obj["records"].values())
    method_extractors = {
        "ours_compact_anchor_safe": lambda r: r["ours_compact_anchor_safe"],
        "pt_a57": lambda r: r["pt_a57"],
        "meta_top12_sgd_mse50_valbest": lambda r: r["selections"][
            "meta_top12_sgd_mse50_valbest"
        ],
        "zero_top12_sgd_mse50_valbest": lambda r: r["selections"][
            "zero_top12_sgd_mse50_valbest"
        ],
        "common12_sgd_mse50_valbest": lambda r: r["selections"][
            "common12_sgd_mse50_valbest"
        ],
        "common12_sgd_mse50_anchor_safe": lambda r: r["selections"][
            "common12_sgd_mse50_anchor_safe"
        ],
    }
    summary_rows: List[Dict[str, Any]] = []
    case_rows: List[Dict[str, Any]] = []
    for method, extractor in method_extractors.items():
        values = [extractor(r) for r in records]
        summary_rows.append(
            {
                "method": method,
                "N_cases": len(values),
                "test_wmse_mean": _mean(v["test"]["weighted_mse"] for v in values),
                "test_mae_mean": _mean(v["test"]["mae"] for v in values),
                "test_worst10_mean": _mean(v["test"]["worst10"] for v in values),
                "case_cvar90_wmse": _cvar90(
                    v["test"]["weighted_mse"] for v in values
                ),
                "adapted_candidate_count": (
                    12
                    if "top12" in method or "common12" in method
                    else (
                        _mean(
                            extractor(r).get("adapted_candidate_count", 1)
                            for r in records
                        )
                    )
                ),
            }
        )
        for rec, value in zip(records, values):
            case_rows.append(
                {
                    "method": method,
                    "case_key": rec["case_key"],
                    "center_id": rec["center_id"],
                    "H": rec["H"],
                    "K": rec["K"],
                    "budget_tier": rec["budget_tier"],
                    "test_wmse": value["test"]["weighted_mse"],
                    "test_mae": value["test"]["mae"],
                    "test_worst10": value["test"]["worst10"],
                }
            )

    ours_by_key = {
        r["case_key"]: r["ours_compact_anchor_safe"] for r in records
    }
    pairwise: Dict[str, Any] = {}
    for method, extractor in method_extractors.items():
        if method == "ours_compact_anchor_safe":
            continue
        by_center: Dict[int, List[float]] = defaultdict(list)
        for rec in records:
            ours = ours_by_key[rec["case_key"]]
            other = extractor(rec)
            by_center[int(rec["center_id"])].append(
                _rel_gain(
                    ours["test"]["weighted_mse"],
                    other["test"]["weighted_mse"],
                )
            )
        pairwise[method] = _center_bootstrap(
            by_center, CFG_SUPP.train_seed + 1701 + len(method)
        )

    summary = {
        "study": "optimizer_matched_12_candidate_control_summary",
        "decision": "PASS_OPTIMIZER_CONTROL_SUMMARY_GENERATED",
        "summary": summary_rows,
        "paired_ours_relative_to_controls": pairwise,
        "claim_boundary": (
            "The matched controls isolate optimizer/loss/step-count and candidate-"
            "budget differences for the search baselines. They do not prove that "
            "the compact bank alone causes every performance gain."
        ),
        "selection_uses_test": False,
        "test_opened_after_all_selectors_fixed": True,
    }
    atomic_json(
        summary,
        os.path.join(
            paths["optimizer_dir"], "optimizer_matched_control_summary.json"
        ),
    )
    _write_csv(
        os.path.join(
            paths["optimizer_dir"], "optimizer_matched_control_summary.csv"
        ),
        summary_rows,
    )
    _write_csv(
        os.path.join(
            paths["optimizer_dir"], "optimizer_matched_control_cases.csv"
        ),
        case_rows,
    )
    return summary


# ---------------------------------------------------------------------------
# Report and audit
# ---------------------------------------------------------------------------


def generate_report(project_root: str) -> str:
    root = os.path.abspath(project_root)
    paths = _result_paths(root)
    os.makedirs(paths["report"], exist_ok=True)
    sections = [
        "# Supplementary Evidence Index",
        "",
        "This directory contains additional evidence only. The frozen final method is not retuned.",
        "",
    ]
    files = {
        "Trajectory": os.path.join(paths["trajectory_dir"], "trajectory_summary.json"),
        "Anchor risk": paths["anchor_risk"],
        "Repeated runtime": os.path.join(paths["runtime_dir"], "repeated_runtime_summary.json"),
        "Optimizer-matched control": os.path.join(
            paths["optimizer_dir"], "optimizer_matched_control_summary.json"
        ),
    }
    for title, path in files.items():
        sections.append(f"## {title}")
        if os.path.isfile(path):
            obj = load_json(path)
            sections.append(f"- Decision: `{obj.get('decision')}`")
            sections.append(f"- File: `{os.path.relpath(path, root).replace(os.sep, '/')}`")
            sections.append(f"- SHA-256: `{file_sha256(path)}`")
        else:
            sections.append("- Not generated yet.")
        sections.append("")
    sections.extend(
        [
            "## Claim boundaries",
            "",
            "- Trajectory evidence may support that 50 steps are sufficient under the evaluated protocol; it cannot establish global optimality.",
            "- Anchor protection is justified through switching-risk metrics, not only mean WMSE.",
            "- Runtime comparisons are valid only for the recorded hardware/software environment and synchronized timer scope.",
            "- Optimizer-matched controls are enhancement evidence and do not isolate the compact bank as the sole causal factor.",
            "",
        ]
    )
    out = os.path.join(paths["report"], "SUPPLEMENTARY_EVIDENCE_INDEX.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(sections))
    return out


def audit(project_root: str, out_path: Optional[str] = None) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    paths = _result_paths(root)
    out_path = out_path or paths["audit"]
    checks: Dict[str, bool] = {}
    details: Dict[str, Any] = {}

    checks["preflight_pass"] = os.path.isfile(paths["preflight"]) and load_json(
        paths["preflight"]
    ).get("decision") == "PASS_SUPPLEMENTARY_EVIDENCE_PREFLIGHT"

    if os.path.isfile(paths["trajectory"]):
        obj = load_json(paths["trajectory"])
        checks["trajectory_complete"] = (
            obj.get("decision") == "PASS_FIXED_50_STEP_TRAJECTORY_COMPLETE"
        )
        checks["trajectory_test_unused"] = not bool(obj.get("test_used"))
        details["trajectory_records"] = len(obj.get("records", {}))
    else:
        checks["trajectory_complete"] = False
        checks["trajectory_test_unused"] = False

    if os.path.isfile(paths["anchor_risk"]):
        obj = load_json(paths["anchor_risk"])
        checks["anchor_risk_complete"] = (
            obj.get("decision") == "PASS_ANCHOR_RISK_ANALYSIS_COMPLETE"
        )
        details["anchor_risk_cases"] = len(obj.get("case_records", []))
    else:
        checks["anchor_risk_complete"] = False

    if os.path.isfile(paths["runtime"]):
        obj = load_json(paths["runtime"])
        checks["runtime_complete"] = obj.get("decision") in {
            "PASS_REPEATED_CUDA_RUNTIME_COMPLETE",
            "PASS_RUNTIME_SMOKE_COMPLETE",
        }
        checks["runtime_test_unused"] = not bool(obj.get("test_used"))
        checks["runtime_check_unused"] = not bool(obj.get("check_used"))
        details["runtime_records"] = len(obj.get("records", {}))
    else:
        checks["runtime_complete"] = False
        checks["runtime_test_unused"] = False
        checks["runtime_check_unused"] = False

    if os.path.isfile(paths["optimizer"]):
        obj = load_json(paths["optimizer"])
        checks["optimizer_control_complete"] = (
            obj.get("decision")
            == "PASS_OPTIMIZER_MATCHED_12_CANDIDATE_CONTROL_COMPLETE"
        )
        checks["optimizer_selection_test_unused"] = not bool(
            obj.get("selection_uses_test")
        )
        checks["optimizer_test_opened_after_selection"] = bool(
            obj.get("test_opened_after_all_selectors_fixed")
        )
        details["optimizer_records"] = len(obj.get("records", {}))
    else:
        checks["optimizer_control_complete"] = False
        checks["optimizer_selection_test_unused"] = False
        checks["optimizer_test_opened_after_selection"] = False

    required_checks = [
        "preflight_pass",
        "trajectory_complete",
        "trajectory_test_unused",
        "anchor_risk_complete",
        "runtime_complete",
        "runtime_test_unused",
        "runtime_check_unused",
        "optimizer_control_complete",
        "optimizer_selection_test_unused",
        "optimizer_test_opened_after_selection",
    ]
    decision = (
        "PASS_SUPPLEMENTARY_EVIDENCE_COMPLETE_AND_AUDITED"
        if all(checks.get(k, False) for k in required_checks)
        else "SUPPLEMENTARY_EVIDENCE_INCOMPLETE"
    )
    obj = {
        "study": "experiments.supplementary_audit",
        "decision": decision,
        "checks": checks,
        "details": details,
        "required_checks": required_checks,
        "method_retuning_allowed": False,
    }
    atomic_json(obj, out_path)
    generate_report(root)
    return obj
