# -*- coding: utf-8 -*-
from __future__ import annotations

import copy
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

from configs.methods.main_experiments_cfg import CFG, config_dict
from main_evaluation.pipeline import (
    _asset_full,
    _fixed_target_adapt,
    _load_external_source_manifest,
    _load_strong_manifest,
    _load_strong_model,
    _safe_torch_load,
    _validate_manifest_assets,
)
from core.config import load_and_merge
from core.data.v2_pools import build_v2_development_cache
from core.methods.ours.paper_engine import _load_prior_model
from core.methods.ours.stage2_runtime import (
    candidate_backend_context,
    candidate_device,
    configure_stage2_runtime,
    synchronize_if_cuda,
)
from core.space import build_model, enumerate_A_base, profile_arch
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

def _atomic_torch_save(obj: Any, path: str) -> None:
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.{time.time_ns()}.tmp"
    torch.save(obj, tmp)
    os.replace(tmp, path)


def _pool_ids(pool: Sequence[int]) -> set[int]:
    start, count, _offset = [int(x) for x in pool]
    return set(range(start, start + count))


def _jobs(pool: Sequence[int], smoke: bool = False) -> List[Tuple[int, int, int]]:
    start, count, _offset = [int(x) for x in pool]
    rows = [
        (cid, H, K)
        for cid in range(start, start + count)
        for H in CFG.H_list
        for K in CFG.K_list
    ]
    return rows[:2] if smoke else rows


def _rel_gain(new: float, ref: float) -> float:
    return float((float(ref) - float(new)) / (abs(float(ref)) + CFG.eps))


def _mean(xs: Iterable[float]) -> Optional[float]:
    vals = list(xs)
    return float(np.mean(vals)) if vals else None


def _center_bootstrap(
    by_center: Mapping[int, Sequence[float]], seed: int
) -> Dict[str, Any]:
    arr = np.asarray(
        [np.mean(by_center[c]) for c in sorted(by_center)], dtype=float
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


def _target_adapt(
    model: nn.Module, Xs: torch.Tensor, ys: torch.Tensor, *, seed: int, steps: int
) -> None:
    dev = next(model.parameters()).device
    seed_all(seed, dev)
    model.train()
    opt = optim.SGD(model.parameters(), lr=CFG.target_lr)
    Xd, yd = Xs.to(dev).contiguous(), ys.to(dev).contiguous()
    for _ in range(int(steps)):
        opt.zero_grad(set_to_none=True)
        loss = ((model(Xd) - yd) ** 2).mean()
        if not torch.isfinite(loss):
            raise RuntimeError("Non-finite SGD/MSE target loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), CFG.target_grad_clip)
        opt.step()


def _candidate_lex(row: Mapping[str, Any]) -> Tuple[float, float, float, int, str]:
    return (
        float(row["validation"]["weighted_mse"]),
        float(row["params"]),
        float(row["flops"]),
        int(row["arch_idx"]),
        str(row["token"]),
    )


def _select_anchor_safe(
    candidates: Sequence[Mapping[str, Any]],
    *,
    allowed_tokens: Sequence[str],
    margin_rel: float,
    enforce_feasible: bool,
) -> Dict[str, Any]:
    token_map = {str(r["token"]): r for r in candidates}
    if "PT_A57" not in token_map:
        raise RuntimeError("PT_A57 anchor missing")
    anchor = token_map["PT_A57"]
    allowed = []
    for token in allowed_tokens:
        if token not in token_map:
            continue
        row = token_map[token]
        if enforce_feasible and not bool(row["hard_feasible"]):
            continue
        allowed.append(row)
    if anchor not in allowed:
        allowed.append(anchor)
    alternatives = [r for r in allowed if str(r["token"]) != "PT_A57"]
    if not alternatives:
        selected = anchor
        best_alt = None
        switched = False
    else:
        best_alt = min(alternatives, key=_candidate_lex)
        threshold = float(anchor["validation"]["weighted_mse"]) * (
            1.0 - float(margin_rel)
        )
        switched = float(best_alt["validation"]["weighted_mse"]) <= threshold
        selected = best_alt if switched else anchor
    return {
        "selected_token": str(selected["token"]),
        "switched": bool(switched),
        "selected_hard_feasible": bool(selected["hard_feasible"]),
        "anchor_validation_mse": float(anchor["validation"]["weighted_mse"]),
        "best_alternative_validation_mse": (
            None
            if best_alt is None
            else float(best_alt["validation"]["weighted_mse"])
        ),
        "margin_rel": float(margin_rel),
        "allowed_tokens": [str(r["token"]) for r in allowed],
    }


def _select_val_best(
    candidates: Sequence[Mapping[str, Any]],
    *,
    allowed_tokens: Sequence[str],
    enforce_feasible: bool,
) -> Dict[str, Any]:
    token_map = {str(r["token"]): r for r in candidates}
    allowed = []
    for token in allowed_tokens:
        if token not in token_map:
            continue
        row = token_map[token]
        if enforce_feasible and not bool(row["hard_feasible"]):
            continue
        allowed.append(row)
    if not allowed:
        raise RuntimeError("No candidate for validation-best selection")
    selected = min(allowed, key=_candidate_lex)
    return {
        "selected_token": str(selected["token"]),
        "switched": str(selected["token"]) != "PT_A57",
        "selected_hard_feasible": bool(selected["hard_feasible"]),
        "margin_rel": None,
        "allowed_tokens": [str(r["token"]) for r in allowed],
    }


def _result_paths(root: str) -> Dict[str, str]:
    out = os.path.join(root, CFG.output_root)
    return {
        "root": out,
        "preflight": os.path.join(out, "preflight", "final_exp_preflight.json"),
        "ablation": os.path.join(out, "ablation", "ablation_candidates.json"),
        "seeds": os.path.join(out, "seeds", "seed_robustness.json"),
        "scale_banks": os.path.join(out, "source_scale", "banks"),
        "scale_eval": os.path.join(out, "source_scale", "source_scale_eval.json"),
        "real_processed": os.path.join(out, "real_trace", "processed"),
        "real_bank": os.path.join(out, "real_trace", "bank"),
        "real_eval": os.path.join(out, "real_trace", "real_eval.json"),
        "report": os.path.join(out, "report"),
        "audit": os.path.join(out, "audit", "final_exp_audit.json"),
    }


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

def preflight(project_root: str, out_path: str) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    paths = {
        "main_evaluation_analysis": os.path.join(root, CFG.main_evaluation_analysis_path),
        "main_evaluation_audit": os.path.join(root, CFG.main_evaluation_audit_path),
        "main_evaluation_ours": os.path.join(root, CFG.main_evaluation_ours_path),
        "main_evaluation_pt": os.path.join(root, CFG.main_evaluation_pt_path),
        "anchor_safe_selector": os.path.join(root, CFG.anchor_safe_selector_path),
        "source_prior_bank_manifest": os.path.join(root, CFG.source_prior_bank_manifest_path),
        "c1_bank": os.path.join(root, CFG.c1_bank_path),
        "external_source_manifest": os.path.join(
            root, CFG.external_source_manifest_path
        ),
    }
    checks: Dict[str, bool] = {
        f"{name}_exists": os.path.isfile(path) for name, path in paths.items()
    }
    details: Dict[str, Any] = {}

    all_new = (
        _pool_ids(CFG.ablation_pool)
        | _pool_ids(CFG.seed_pool)
        | _pool_ids(CFG.source_scale_pool)
    )
    used: set[int] = set()
    for lo, hi in CFG.known_used_center_ranges:
        used.update(range(int(lo), int(hi) + 1))
    overlap = sorted(all_new & used)
    cross_overlap = bool(
        _pool_ids(CFG.ablation_pool) & _pool_ids(CFG.seed_pool)
        or _pool_ids(CFG.ablation_pool) & _pool_ids(CFG.source_scale_pool)
        or _pool_ids(CFG.seed_pool) & _pool_ids(CFG.source_scale_pool)
    )

    if all(checks.values()):
        main_evaluation_analysis = load_json(paths["main_evaluation_analysis"])
        main_evaluation_audit = load_json(paths["main_evaluation_audit"])
        main_evaluation_ours = load_json(paths["main_evaluation_ours"])
        main_evaluation_pt = load_json(paths["main_evaluation_pt"])
        anchor_safe_selector = load_json(paths["anchor_safe_selector"])
        source_prior_bank = _load_strong_manifest(root, paths["source_prior_bank_manifest"])
        ext_manifest = _load_external_source_manifest(root)
        bank_ok, bank_errors = _validate_manifest_assets(root, source_prior_bank)
        ext_ok, ext_errors = _validate_manifest_assets(root, ext_manifest)
        checks.update(
            {
                "main_evaluation_analysis_decision": main_evaluation_analysis.get("decision")
                == CFG.expected_main_evaluation_analysis_decision,
                "main_evaluation_audit_decision": main_evaluation_audit.get("decision")
                == CFG.expected_main_evaluation_audit_decision,
                "main_evaluation_ours_complete": bool(main_evaluation_ours.get("complete")),
                "main_evaluation_pt_complete": bool(main_evaluation_pt.get("complete")),
                "main_evaluation_no_retuning": not bool(
                    main_evaluation_analysis.get("method_or_selector_tuning_after_this_pool_allowed")
                ),
                "anchor_safe_selector_pass": anchor_safe_selector.get("decision")
                == CFG.expected_anchor_safe_selector_decision,
                "margin_exact": abs(
                    float(anchor_safe_selector.get("selected_margin_rel", -1.0))
                    - CFG.frozen_margin_rel
                )
                < 1e-12,
                "source_prior_bank_pass": source_prior_bank.get("decision")
                == CFG.expected_source_prior_bank_decision,
                "source_prior_bank_assets_valid": bank_ok,
                "external_assets_valid": ext_ok,
                "c1_bank_hash": file_sha256(paths["c1_bank"]).lower()
                == CFG.c1_bank_sha256,
                "new_pools_no_previous_overlap": len(overlap) == 0,
                "new_pools_mutually_disjoint": not cross_overlap,
                "compact_set_exact": tuple(
                    int(x) for x in source_prior_bank.get("candidate_arch_indices", ())
                )
                == CFG.compact_arch_indices,
                "target_steps_50": CFG.target_steps == 50,
                "target_seeds_exact": CFG.target_seeds == (2904, 2905, 2906),
                "source_scales_exact": CFG.source_scales
                == (10, 20, 30, 40, 50),
            }
        )
        details = {
            "new_pool_overlap": overlap,
            "bank_asset_errors": bank_errors,
            "external_asset_errors": ext_errors,
        }

    decision = (
        "PASS_FINAL_PAPER_EXPERIMENTS_PREFLIGHT"
        if checks and all(checks.values())
        else "FAIL_FINAL_PAPER_EXPERIMENTS_PREFLIGHT"
    )
    obj = {
        "study": "experiments.main_preflight",
        "decision": decision,
        "protocol": config_dict(),
        "checks": checks,
        "details": details,
        "upstream": {
            k: {
                "path": os.path.abspath(v),
                "sha256": file_sha256(v) if os.path.isfile(v) else None,
            }
            for k, v in paths.items()
        },
        "test_used": False,
        "method_retuning_allowed": False,
    }
    atomic_json(obj, out_path)
    return obj


def _require_preflight(root: str) -> None:
    path = _result_paths(root)["preflight"]
    if not os.path.isfile(path):
        raise FileNotFoundError("Run final experiment preflight first")
    if load_json(path).get("decision") != "PASS_FINAL_PAPER_EXPERIMENTS_PREFLIGHT":
        raise RuntimeError("Final experiment preflight is not PASS")


# ---------------------------------------------------------------------------
# Candidate pool for ablation, resource constraints, bank size, and oracle
# ---------------------------------------------------------------------------

def _candidate_specs(A: Sequence[Any]) -> List[Tuple[str, int, str]]:
    rows: List[Tuple[str, int, str]] = [("PT_A57", 57, "strong")]
    rows.append(("C1_A57", 57, "c1"))
    for idx in CFG.compact_non_anchor_indices:
        rows.append((f"STRONG_A{idx}", int(idx), "strong"))
    for idx in CFG.compact_non_anchor_indices:
        rows.append((f"C1_A{idx}", int(idx), "c1"))
    return rows


def _load_candidate_model(
    root: str,
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
            root,
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


def _variant_token_sets() -> Dict[str, List[str]]:
    full = ["PT_A57", "C1_A57"] + [
        f"STRONG_A{i}" for i in CFG.compact_non_anchor_indices
    ]
    legacy = ["PT_A57", "C1_A57"] + [
        f"C1_A{i}" for i in CFG.compact_non_anchor_indices
    ]
    return {
        "full_method": full,
        "legacy_source_bank": legacy,
        "pt_a57_only": ["PT_A57"],
        "dual_init_a57": ["PT_A57", "C1_A57"],
        "without_anchor_protection": full,
        "without_hard_feasibility": full,
    }


def _bank_size_tokens(size: int) -> List[str]:
    if size < 1 or size > 6:
        raise ValueError(size)
    tokens = ["PT_A57", "C1_A57"]
    for idx in CFG.bank_size_order[: max(0, size - 1)]:
        tokens.append(f"STRONG_A{idx}")
    return tokens


def run_ablation_pool(
    project_root: str,
    out_path: str,
    device: str,
    safe_mode: str,
    smoke: bool = False,
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    _require_preflight(root)
    cfg, cache, A, requested, safe = build_runtime(
        device, safe_mode, (CFG.ablation_pool,)
    )
    L = int(cfg.main.task.L)
    frozen = load_frozen_assets(root)
    strong_manifest = _load_strong_manifest(
        root, os.path.join(root, CFG.source_prior_bank_manifest_path)
    )
    jobs = _jobs(CFG.ablation_pool, smoke)
    run_mode = "smoke" if smoke else "formal"
    result = (
        load_json(out_path)
        if os.path.isfile(out_path)
        else {
            "study": "final_ablation_resource_bank_oracle_pool",
            "decision": "FINAL_ABLATION_IN_PROGRESS",
            "run_mode": run_mode,
            "protocol": config_dict(),
            "pool": list(CFG.ablation_pool),
            "records": {},
            "selection_uses_test": False,
            "test_opened_after_all_variant_selectors_fixed": True,
            "method_retuning_allowed": False,
        }
    )
    if result.get("run_mode") != run_mode:
        raise RuntimeError("Smoke/formal outputs cannot share one file")
    records = dict(result.get("records", {}))
    candidate_plan = _candidate_specs(A)
    variants = _variant_token_sets()
    started = time.perf_counter()
    completed_new = 0

    for case_no, (cid, H, K) in enumerate(jobs, 1):
        Xs, ys, Xv, yv, Xc, yc, tier, ctype = get_support_validation_check(
            cfg, cache, cid, H, K
        )
        case_key = f"c{cid}_h{H}_k{K}_b{tier}"
        if case_key in records and bool(records[case_key].get("complete")):
            continue
        Xt = yt = None
        input_dim = int(Xs.shape[-1])
        seed = CFG.train_seed + 1009 * cid + 37 * H + 53 * K
        feasible = set(feasible_indices(cfg, A, tier, L, input_dim, H))
        candidate_rows: List[Dict[str, Any]] = []
        states: Dict[str, Dict[str, torch.Tensor]] = {}

        for token, idx, loader in candidate_plan:
            spec = A[idx]
            actual = candidate_device(spec, requested, safe)
            with candidate_backend_context(spec, actual, safe):
                model = _load_candidate_model(
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
                _target_adapt(model, Xs, ys, seed=seed, steps=(1 if smoke else CFG.target_steps))
                val = eval_metrics(model, Xv, yv)
                chk = eval_metrics(model, Xc, yc)
                params, flops = profile_arch(
                    spec, L=L, input_dim=input_dim, H=H
                )
                row = {
                    "token": token,
                    "loader": loader,
                    "arch_idx": int(idx),
                    "arch_key": str(spec.arch_key),
                    "family": str(spec.family),
                    "params": float(params),
                    "flops": float(flops),
                    "hard_feasible": int(idx) in feasible,
                    "validation": val,
                    "check": chk,
                    "target_seed": int(seed),
                }
                candidate_rows.append(row)
                states[token] = {
                    k: v.detach().cpu().clone()
                    for k, v in model.state_dict().items()
                }
                del model
                synchronize_if_cuda(actual)

        # Freeze every selector before Test is materialized.
        selections: Dict[str, Dict[str, Any]] = {}
        for variant, tokens in variants.items():
            if variant == "without_anchor_protection":
                sel = _select_val_best(
                    candidate_rows,
                    allowed_tokens=tokens,
                    enforce_feasible=True,
                )
            elif variant == "without_hard_feasibility":
                sel = _select_anchor_safe(
                    candidate_rows,
                    allowed_tokens=tokens,
                    margin_rel=CFG.frozen_margin_rel,
                    enforce_feasible=False,
                )
            else:
                sel = _select_anchor_safe(
                    candidate_rows,
                    allowed_tokens=tokens,
                    margin_rel=CFG.frozen_margin_rel,
                    enforce_feasible=True,
                )
            selections[variant] = sel

        bank_selections: Dict[str, Dict[str, Any]] = {}
        for size in CFG.bank_sizes:
            bank_selections[str(size)] = _select_anchor_safe(
                candidate_rows,
                allowed_tokens=_bank_size_tokens(size),
                margin_rel=CFG.frozen_margin_rel,
                enforce_feasible=True,
            )

        # Test opens only after all selectors above are frozen.
        Xt, yt = get_test_only(cfg, cache, cid, H, K)
        token_map = {str(r["token"]): r for r in candidate_rows}
        for token, state in states.items():
            row = token_map[token]
            spec = A[int(row["arch_idx"])]
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

        # Attach selected metrics without using them for selection.
        for sel in list(selections.values()) + list(bank_selections.values()):
            selected = token_map[str(sel["selected_token"])]
            sel["validation"] = selected["validation"]
            sel["check"] = selected["check"]
            sel["test"] = selected["test"]
            sel["arch_idx"] = int(selected["arch_idx"])
            sel["arch_key"] = str(selected["arch_key"])
            sel["family"] = str(selected["family"])
            sel["params"] = float(selected["params"])
            sel["flops"] = float(selected["flops"])

        feasible_full_tokens = set(
            _variant_token_sets()["full_method"]
        )
        oracle_candidates = [
            r
            for r in candidate_rows
            if str(r["token"]) in feasible_full_tokens
            and bool(r["hard_feasible"])
        ]
        check_oracle = min(
            oracle_candidates,
            key=lambda r: (
                float(r["check"]["weighted_mse"]),
                float(r["params"]),
                float(r["flops"]),
                int(r["arch_idx"]),
                str(r["token"]),
            ),
        )
        test_oracle = min(
            oracle_candidates,
            key=lambda r: (
                float(r["test"]["weighted_mse"]),
                float(r["params"]),
                float(r["flops"]),
                int(r["arch_idx"]),
                str(r["token"]),
            ),
        )
        full_test = selections["full_method"]["test"]["weighted_mse"]
        oracle = {
            "check_oracle_token": str(check_oracle["token"]),
            "check_oracle": check_oracle["check"],
            "test_oracle_token": str(test_oracle["token"]),
            "test_oracle": test_oracle["test"],
            "full_selector_test_mse": float(full_test),
            "test_oracle_regret": float(
                (float(full_test) - float(test_oracle["test"]["weighted_mse"]))
                / (abs(float(test_oracle["test"]["weighted_mse"])) + CFG.eps)
            ),
            "full_matches_test_oracle": str(
                selections["full_method"]["selected_token"]
            )
            == str(test_oracle["token"]),
            "check_matches_test_oracle": str(check_oracle["token"])
            == str(test_oracle["token"]),
        }

        records[case_key] = {
            "complete": True,
            "case_key": case_key,
            "center_id": int(cid),
            "center_type": str(ctype),
            "budget_tier": str(tier),
            "H": int(H),
            "K": int(K),
            "candidates": candidate_rows,
            "variants": selections,
            "bank_sizes": bank_selections,
            "oracle": oracle,
            "selection_uses_test": False,
            "test_opened_after_selectors_fixed": True,
        }
        result["records"] = records
        result["N_records"] = len(records)
        result["expected_records"] = len(jobs)
        result["complete"] = len(records) == len(jobs)
        atomic_json(result, out_path)
        completed_new += 1
        elapsed = time.perf_counter() - started
        eta = elapsed / max(1, completed_new) * max(0, len(jobs) - len(records))
        print(
            f"[FinalExp:Ablation] {case_no}/{len(jobs)} {case_key} "
            f"candidates={len(candidate_rows)} elapsed={elapsed/3600:.2f}h "
            f"eta={eta/3600:.2f}h",
            flush=True,
        )
        del states
        gc.collect()
        if requested.type == "cuda":
            torch.cuda.empty_cache()

    result["decision"] = (
        "PASS_FINAL_ABLATION_RESOURCE_BANK_ORACLE"
        if result.get("complete")
        else "FINAL_ABLATION_INCOMPLETE"
    )
    atomic_json(result, out_path)
    return result


# ---------------------------------------------------------------------------
# Three target-side random seeds
# ---------------------------------------------------------------------------

def run_seed_robustness(
    project_root: str,
    out_path: str,
    device: str,
    safe_mode: str,
    smoke: bool = False,
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    _require_preflight(root)
    cfg, cache, A, requested, safe = build_runtime(
        device, safe_mode, (CFG.seed_pool,)
    )
    L = int(cfg.main.task.L)
    frozen = load_frozen_assets(root)
    strong_manifest = _load_strong_manifest(
        root, os.path.join(root, CFG.source_prior_bank_manifest_path)
    )
    jobs = _jobs(CFG.seed_pool, smoke)
    run_mode = "smoke" if smoke else "formal"
    result = (
        load_json(out_path)
        if os.path.isfile(out_path)
        else {
            "study": "final_target_seed_robustness",
            "decision": "FINAL_SEEDS_IN_PROGRESS",
            "run_mode": run_mode,
            "protocol": config_dict(),
            "pool": list(CFG.seed_pool),
            "records": {},
            "source_assets_fixed": True,
            "seed_scope": "target_adaptation_and_dropout_only",
            "selection_uses_test": False,
        }
    )
    if result.get("run_mode") != run_mode:
        raise RuntimeError("Smoke/formal outputs cannot share one file")
    records = dict(result.get("records", {}))
    started = time.perf_counter()
    completed_new = 0

    for seed_index, target_seed in enumerate(CFG.target_seeds):
        for case_no, (cid, H, K) in enumerate(jobs, 1):
            Xs, ys, Xv, yv, Xc, yc, tier, ctype = get_support_validation_check(
                cfg, cache, cid, H, K
            )
            key = f"s{target_seed}_c{cid}_h{H}_k{K}_b{tier}"
            if key in records and bool(records[key].get("complete")):
                continue
            input_dim = int(Xs.shape[-1])
            feasible = set(feasible_indices(cfg, A, tier, L, input_dim, H))
            if CFG.anchor_arch_idx not in feasible:
                raise RuntimeError("A57 anchor infeasible")
            seed = int(target_seed + 1009 * cid + 37 * H + 53 * K)
            candidate_rows: List[Dict[str, Any]] = []
            states: Dict[str, Dict[str, torch.Tensor]] = {}
            plan = [("PT_A57", 57, "strong"), ("C1_A57", 57, "c1")]
            plan.extend(
                (f"STRONG_A{i}", int(i), "strong")
                for i in CFG.compact_non_anchor_indices
                if int(i) in feasible
            )
            for token, idx, loader in plan:
                spec = A[idx]
                actual = candidate_device(spec, requested, safe)
                with candidate_backend_context(spec, actual, safe):
                    model = _load_candidate_model(
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
                    _target_adapt(model, Xs, ys, seed=seed, steps=(1 if smoke else CFG.target_steps))
                    val = eval_metrics(model, Xv, yv)
                    chk = eval_metrics(model, Xc, yc)
                    params, flops = profile_arch(
                        spec, L=L, input_dim=input_dim, H=H
                    )
                    row = {
                        "token": token,
                        "arch_idx": int(idx),
                        "arch_key": str(spec.arch_key),
                        "family": str(spec.family),
                        "params": float(params),
                        "flops": float(flops),
                        "hard_feasible": True,
                        "validation": val,
                        "check": chk,
                    }
                    candidate_rows.append(row)
                    states[token] = {
                        k: v.detach().cpu().clone()
                        for k, v in model.state_dict().items()
                    }
                    del model
                    synchronize_if_cuda(actual)
            selection = _select_anchor_safe(
                candidate_rows,
                allowed_tokens=[str(r["token"]) for r in candidate_rows],
                margin_rel=CFG.frozen_margin_rel,
                enforce_feasible=True,
            )
            Xt, yt = get_test_only(cfg, cache, cid, H, K)
            metrics_by_token: Dict[str, Dict[str, float]] = {}
            for row in candidate_rows:
                token = str(row["token"])
                spec = A[int(row["arch_idx"])]
                actual = candidate_device(spec, requested, safe)
                with candidate_backend_context(spec, actual, safe):
                    model = build_model(
                        spec,
                        input_dim=input_dim,
                        H=H,
                        L=L,
                        device=str(actual),
                    )
                    model.load_state_dict(states[token], strict=True)
                    metrics_by_token[token] = eval_metrics(model, Xt, yt)
                    del model
                    synchronize_if_cuda(actual)
            selected_token = str(selection["selected_token"])
            records[key] = {
                "complete": True,
                "target_seed": int(target_seed),
                "case_seed": int(seed),
                "center_id": int(cid),
                "center_type": str(ctype),
                "budget_tier": str(tier),
                "H": int(H),
                "K": int(K),
                "ours": {
                    "selected_token": selected_token,
                    "test": metrics_by_token[selected_token],
                    "switched": bool(selection["switched"]),
                },
                "pt_ft": {"test": metrics_by_token["PT_A57"]},
                "selection_uses_test": False,
            }
            result["records"] = records
            result["N_records"] = len(records)
            result["expected_records"] = len(jobs) * len(CFG.target_seeds)
            result["complete"] = len(records) == result["expected_records"]
            atomic_json(result, out_path)
            completed_new += 1
            elapsed = time.perf_counter() - started
            remaining = result["expected_records"] - len(records)
            eta = elapsed / max(1, completed_new) * max(0, remaining)
            print(
                f"[FinalExp:Seeds] seed={target_seed} {case_no}/{len(jobs)} "
                f"c{cid}_h{H}_k{K}_{tier} elapsed={elapsed/3600:.2f}h "
                f"eta={eta/3600:.2f}h",
                flush=True,
            )
            del states
            gc.collect()
            if requested.type == "cuda":
                torch.cuda.empty_cache()

    result["decision"] = (
        "PASS_FINAL_THREE_TARGET_SEEDS"
        if result.get("complete")
        else "FINAL_SEEDS_INCOMPLETE"
    )
    atomic_json(result, out_path)
    return result


# ---------------------------------------------------------------------------
# Source-scale bank construction and evaluation
# ---------------------------------------------------------------------------

def _build_scale_runtime(
    device: str, safe_mode: str
) -> Tuple[Any, Any, Sequence[Any], torch.device, str]:
    requested = torch.device(device)
    if requested.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    safe = configure_stage2_runtime(requested, safe_mode)
    cfg = load_and_merge(
        "ours", main_module="configs.main_cfg", methods_pkg="configs.methods", smoke=False
    )
    cfg.main.sim.seed = CFG.data_seed
    cfg.main.split.n_train_centers = max(CFG.source_scales)
    cfg.main.device = str(requested)
    cache = build_v2_development_cache(cfg, blocks=(CFG.source_scale_pool,))
    A = enumerate_A_base(cfg.main.arch)
    if len(A) != CFG.architecture_count:
        raise RuntimeError("Architecture-space mismatch")
    return cfg, cache, A, requested, safe


def _iter_source_batches(
    cfg: Any,
    cache: Any,
    *,
    H: int,
    source_count: int,
    batch_size: int,
    epoch: int,
) -> Iterable[Tuple[torch.Tensor, torch.Tensor]]:
    rng = random.Random(
        CFG.train_seed + 10007 * int(H) + 97 * int(source_count) + int(epoch)
    )
    centers = list(range(int(source_count)))
    rng.shuffle(centers)
    for cid in centers:
        Xs, ys, Xv, yv, *_ = get_support_validation_check(
            cfg, cache, cid, H, max(CFG.K_list)
        )
        X = torch.cat([Xs, Xv], dim=0)
        y = torch.cat([ys, yv], dim=0)
        gen = torch.Generator(device=X.device)
        gen.manual_seed(
            CFG.train_seed
            + 101 * int(H)
            + 1009 * int(cid)
            + 13 * int(source_count)
            + int(epoch)
        )
        order = torch.randperm(int(X.shape[0]), generator=gen, device=X.device)
        for left in range(0, int(X.shape[0]), int(batch_size)):
            idx = order[left : left + int(batch_size)]
            yield X.index_select(0, idx), y.index_select(0, idx)


def _asset_record(path: str, root: str, **kwargs: Any) -> Dict[str, Any]:
    return {
        "path": os.path.relpath(path, root).replace("\\", "/"),
        "sha256": file_sha256(path),
        **kwargs,
    }


def build_source_scale_banks(
    project_root: str,
    out_dir: str,
    device: str,
    safe_mode: str,
    smoke: bool = False,
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    _require_preflight(root)
    cfg, cache, A, requested, safe = _build_scale_runtime(device, safe_mode)
    L = int(cfg.main.task.L)
    X0, *_ = get_support_validation_check(
        cfg, cache, 0, CFG.H_list[0], max(CFG.K_list)
    )
    input_dim = int(X0.shape[-1])
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    manifest_path = os.path.join(out_dir, "source_scale_bank_manifest.json")
    run_mode = "smoke" if smoke else "formal"
    manifest = (
        load_json(manifest_path)
        if os.path.isfile(manifest_path)
        else {
            "study": "final_source_scale_banks",
            "decision": "SOURCE_SCALE_BANKS_IN_PROGRESS",
            "run_mode": run_mode,
            "protocol": config_dict(),
            "assets": {},
            "test_used": False,
            "target_pool_used": False,
        }
    )
    if manifest.get("run_mode") != run_mode:
        raise RuntimeError("Smoke/formal outputs cannot share bank directory")
    epochs = 1 if smoke else CFG.source_epochs
    jobs = [
        (scale, H, idx)
        for scale in CFG.source_scales
        for H in CFG.H_list
        for idx in CFG.compact_arch_indices
    ]
    if smoke:
        # Build one complete H=1 compact bank so the smoke evaluation can
        # exercise anchor-safe selection without missing candidate assets.
        jobs = [(CFG.source_scales[0], CFG.H_list[0], idx) for idx in CFG.compact_arch_indices]
    started = time.perf_counter()
    completed_new = 0
    for job_no, (scale, H, idx) in enumerate(jobs, 1):
        key = f"s{scale}_h{H}_a{idx}"
        scale_dir = os.path.join(out_dir, f"src{scale}")
        os.makedirs(scale_dir, exist_ok=True)
        out_file = os.path.join(scale_dir, f"strong_h{H}_a{idx}.pt")
        existing = manifest.get("assets", {}).get(key)
        if (
            existing
            and os.path.isfile(out_file)
            and file_sha256(out_file).lower()
            == str(existing.get("sha256", "")).lower()
        ):
            continue
        spec = A[idx]
        actual = candidate_device(spec, requested, safe)
        checkpoint = out_file + ".progress.pt"
        with candidate_backend_context(spec, actual, safe):
            seed = CFG.train_seed + 100003 * scale + 101 * H + idx
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
            last_loss = None
            train_started = time.perf_counter()
            for epoch in range(start_epoch, epochs):
                losses: List[float] = []
                for Xb, yb in _iter_source_batches(
                    cfg,
                    cache,
                    H=H,
                    source_count=(min(2, scale) if smoke else scale),
                    batch_size=CFG.source_batch_size,
                    epoch=epoch,
                ):
                    model.train()
                    opt.zero_grad(set_to_none=True)
                    pred = model(Xb.to(actual).contiguous())
                    loss = ((pred - yb.to(actual).contiguous()) ** 2).mean()
                    if not torch.isfinite(loss):
                        raise RuntimeError("Non-finite source-scale loss")
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
                        "next_epoch": epoch + 1,
                    },
                    checkpoint,
                )
                elapsed = time.perf_counter() - train_started
                eta = elapsed / max(1, epoch - start_epoch + 1) * max(
                    0, epochs - epoch - 1
                )
                print(
                    f"[FinalExp:ScaleBank] job={job_no}/{len(jobs)} "
                    f"src={scale} H={H} A={idx} epoch={epoch+1}/{epochs} "
                    f"loss={last_loss:.6g} elapsed={elapsed/3600:.2f}h "
                    f"eta={eta/3600:.2f}h",
                    flush=True,
                )
            synchronize_if_cuda(actual)
            _atomic_torch_save(
                {k: v.detach().cpu() for k, v in model.state_dict().items()},
                out_file,
            )
            if os.path.isfile(checkpoint):
                os.remove(checkpoint)
            del model, opt
        params, flops = profile_arch(spec, L=L, input_dim=input_dim, H=H)
        manifest.setdefault("assets", {})[key] = _asset_record(
            out_file,
            root,
            source_scale=int(scale),
            H=int(H),
            arch_idx=int(idx),
            arch_key=str(spec.arch_key),
            family=str(spec.family),
            epochs=int(epochs),
            final_source_loss=last_loss,
            params=float(params),
            flops=float(flops),
        )
        manifest["completed_assets"] = len(manifest["assets"])
        manifest["expected_assets"] = len(jobs)
        atomic_json(manifest, manifest_path)
        completed_new += 1
        elapsed = time.perf_counter() - started
        remaining = len(jobs) - len(manifest["assets"])
        eta = elapsed / max(1, completed_new) * max(0, remaining)
        print(
            f"[FinalExp:ScaleBank] completed={len(manifest['assets'])}/{len(jobs)} "
            f"elapsed={elapsed/3600:.2f}h eta={eta/3600:.2f}h",
            flush=True,
        )
        gc.collect()
        if requested.type == "cuda":
            torch.cuda.empty_cache()
    manifest["complete"] = len(manifest.get("assets", {})) == len(jobs)
    manifest["decision"] = (
        "PASS_FINAL_SOURCE_SCALE_BANKS"
        if manifest["complete"]
        else "SOURCE_SCALE_BANKS_INCOMPLETE"
    )
    atomic_json(manifest, manifest_path)
    return manifest


def _load_scale_model(
    root: str,
    manifest: Mapping[str, Any],
    A: Sequence[Any],
    *,
    scale: int,
    H: int,
    idx: int,
    input_dim: int,
    L: int,
    device: torch.device,
) -> nn.Module:
    item = manifest["assets"][f"s{scale}_h{H}_a{idx}"]
    path = _asset_full(root, item)
    model = build_model(
        A[idx], input_dim=input_dim, H=H, L=L, device=str(device)
    )
    model.load_state_dict(_safe_torch_load(path, device), strict=True)
    return model


def run_source_scale_eval(
    project_root: str,
    bank_dir: str,
    out_path: str,
    device: str,
    safe_mode: str,
    smoke: bool = False,
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    _require_preflight(root)
    manifest_path = os.path.join(
        os.path.abspath(bank_dir), "source_scale_bank_manifest.json"
    )
    manifest = load_json(manifest_path)
    if manifest.get("decision") != "PASS_FINAL_SOURCE_SCALE_BANKS":
        raise RuntimeError("Source-scale banks are not PASS")
    cfg, cache, A, requested, safe = _build_scale_runtime(device, safe_mode)
    L = int(cfg.main.task.L)
    jobs = _jobs(CFG.source_scale_pool, smoke)
    run_mode = "smoke" if smoke else "formal"
    result = (
        load_json(out_path)
        if os.path.isfile(out_path)
        else {
            "study": "final_source_scale_eval",
            "decision": "SOURCE_SCALE_EVAL_IN_PROGRESS",
            "run_mode": run_mode,
            "protocol": config_dict(),
            "bank_manifest_sha256": file_sha256(manifest_path),
            "records": {},
            "selection_uses_test": False,
        }
    )
    if result.get("run_mode") != run_mode:
        raise RuntimeError("Smoke/formal outputs cannot share one file")
    records = dict(result.get("records", {}))
    started = time.perf_counter()
    completed_new = 0
    eval_scales = (CFG.source_scales[0],) if smoke else CFG.source_scales
    for scale in eval_scales:
        for case_no, (cid, H, K) in enumerate(jobs, 1):
            Xs, ys, Xv, yv, Xc, yc, tier, ctype = get_support_validation_check(
                cfg, cache, cid, H, K
            )
            key = f"s{scale}_c{cid}_h{H}_k{K}_b{tier}"
            if key in records and bool(records[key].get("complete")):
                continue
            input_dim = int(Xs.shape[-1])
            feasible = set(feasible_indices(cfg, A, tier, L, input_dim, H))
            if CFG.anchor_arch_idx not in feasible:
                raise RuntimeError("Scale A57 anchor infeasible")
            seed = CFG.train_seed + 1009 * cid + 37 * H + 53 * K
            rows: List[Dict[str, Any]] = []
            states: Dict[str, Dict[str, torch.Tensor]] = {}
            for idx in CFG.compact_arch_indices:
                if int(idx) not in feasible:
                    continue
                spec = A[idx]
                actual = candidate_device(spec, requested, safe)
                with candidate_backend_context(spec, actual, safe):
                    model = _load_scale_model(
                        root,
                        manifest,
                        A,
                        scale=scale,
                        H=H,
                        idx=idx,
                        input_dim=input_dim,
                        L=L,
                        device=actual,
                    )
                    _target_adapt(model, Xs, ys, seed=seed, steps=(1 if smoke else CFG.target_steps))
                    val = eval_metrics(model, Xv, yv)
                    chk = eval_metrics(model, Xc, yc)
                    params, flops = profile_arch(
                        spec, L=L, input_dim=input_dim, H=H
                    )
                    token = "A57" if idx == 57 else f"A{idx}"
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
                        }
                    )
                    states[token] = {
                        k: v.detach().cpu().clone()
                        for k, v in model.state_dict().items()
                    }
                    del model
                    synchronize_if_cuda(actual)
            selection = _select_anchor_safe(
                [
                    dict(r, token=("PT_A57" if r["token"] == "A57" else r["token"]))
                    for r in rows
                ],
                allowed_tokens=[
                    "PT_A57" if r["token"] == "A57" else str(r["token"])
                    for r in rows
                ],
                margin_rel=CFG.frozen_margin_rel,
                enforce_feasible=True,
            )
            selected_token = str(selection["selected_token"]).replace(
                "PT_A57", "A57"
            )
            Xt, yt = get_test_only(cfg, cache, cid, H, K)
            test_by_token: Dict[str, Dict[str, float]] = {}
            for row in rows:
                token = str(row["token"])
                spec = A[int(row["arch_idx"])]
                actual = candidate_device(spec, requested, safe)
                with candidate_backend_context(spec, actual, safe):
                    model = build_model(
                        spec,
                        input_dim=input_dim,
                        H=H,
                        L=L,
                        device=str(actual),
                    )
                    model.load_state_dict(states[token], strict=True)
                    test_by_token[token] = eval_metrics(model, Xt, yt)
                    del model
                    synchronize_if_cuda(actual)
            records[key] = {
                "complete": True,
                "source_scale": int(scale),
                "center_id": int(cid),
                "center_type": str(ctype),
                "budget_tier": str(tier),
                "H": int(H),
                "K": int(K),
                "ours": {
                    "selected_token": selected_token,
                    "test": test_by_token[selected_token],
                },
                "a57": {"test": test_by_token["A57"]},
                "selection_uses_test": False,
            }
            result["records"] = records
            result["N_records"] = len(records)
            result["expected_records"] = len(jobs) * len(eval_scales)
            result["complete"] = len(records) == result["expected_records"]
            atomic_json(result, out_path)
            completed_new += 1
            elapsed = time.perf_counter() - started
            remaining = result["expected_records"] - len(records)
            eta = elapsed / max(1, completed_new) * max(0, remaining)
            print(
                f"[FinalExp:ScaleEval] src={scale} {case_no}/{len(jobs)} "
                f"c{cid}_h{H}_k{K}_{tier} elapsed={elapsed/3600:.2f}h "
                f"eta={eta/3600:.2f}h",
                flush=True,
            )
            del states
            gc.collect()
            if requested.type == "cuda":
                torch.cuda.empty_cache()
    result["decision"] = (
        "PASS_FINAL_SOURCE_SCALE_EVAL"
        if result.get("complete")
        else "SOURCE_SCALE_EVAL_INCOMPLETE"
    )
    atomic_json(result, out_path)
    return result
