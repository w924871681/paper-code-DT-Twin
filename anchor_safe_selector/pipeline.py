# -*- coding: utf-8 -*-
from __future__ import annotations

import gc
import json
import os
import time
from collections import Counter, defaultdict
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np
import torch

from configs.methods.anchor_safe_selector_cfg import CFG, config_dict
from source_prior_bank.pipeline import (
    _adapt_sgd_mse,
    _check_oracle,
    _evaluate,
    _load_strong_manifest,
    _load_strong_model,
)
from core.methods.ours.paper_engine import _load_prior_model
from core.methods.ours.stage2_runtime import (
    candidate_backend_context,
    candidate_device,
    synchronize_if_cuda,
)
from core.space import profile_arch
from shared.data_access import get_support_validation_check
from shared.evaluation.common import (
    atomic_json,
    build_runtime,
    feasible_indices,
    file_sha256,
    load_frozen_assets,
    load_json,
)


def _pool_ids(pool: Sequence[int]) -> set[int]:
    start, count, _offset = [int(x) for x in pool]
    return set(range(start, start + count))


def _pool_jobs(pool: Sequence[int], smoke: bool = False) -> List[Tuple[int, int, int]]:
    start, count, _offset = [int(x) for x in pool]
    jobs = [
        (cid, H, K)
        for cid in range(start, start + count)
        for H in CFG.H_list
        for K in CFG.K_list
    ]
    return jobs[:2] if smoke else jobs


def _validate_margin_grid() -> bool:
    vals = tuple(float(x) for x in CFG.margin_grid)
    return (
        len(vals) == len(set(vals))
        and tuple(sorted(vals)) == vals
        and all(0.0 < x < 1.0 for x in vals)
    )


def preflight(project_root: str, out_path: str) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    paths = {
        "source_prior_bank_audit": os.path.join(root, CFG.source_prior_bank_audit_path),
        "source_prior_bank_analysis": os.path.join(root, CFG.source_prior_bank_analysis_path),
        "source_prior_bank_manifest": os.path.join(root, CFG.source_prior_bank_manifest_path),
        "c1_bank": os.path.join(root, CFG.c1_bank_path),
    }
    checks: Dict[str, bool] = {
        f"{name}_exists": os.path.isfile(path) for name, path in paths.items()
    }
    upstream: Dict[str, Any] = {}

    dev_ids = _pool_ids(CFG.selector_dev_pool)
    final_ids = _pool_ids(CFG.final_pool)
    prior_ids: set[int] = set()
    for lo, hi in CFG.known_used_center_ranges:
        prior_ids.update(range(int(lo), int(hi) + 1))

    if all(checks.values()):
        source_prior_bank_audit = load_json(paths["source_prior_bank_audit"])
        source_prior_bank_analysis = load_json(paths["source_prior_bank_analysis"])
        source_prior_bank = _load_strong_manifest(root, paths["source_prior_bank_manifest"])
        checks.update(
            {
                "source_prior_bank_audit_pass": source_prior_bank_audit.get("decision")
                == CFG.expected_source_prior_bank_audit_decision,
                "source_prior_bank_analysis_requires_selector_revision": source_prior_bank_analysis.get(
                    "decision"
                )
                == CFG.expected_source_prior_bank_analysis_decision,
                "source_prior_bank_frozen": source_prior_bank.get("decision")
                == CFG.expected_source_prior_bank_decision,
                "source_prior_bank_target_unused": not bool(
                    source_prior_bank.get("target_pool_used")
                    or source_prior_bank.get("historical_pool_k_used")
                    or source_prior_bank.get("test_used")
                ),
                "source_prior_bank_asset_count_12": len(source_prior_bank.get("assets", {}))
                == len(CFG.H_list) * len(CFG.compact_arch_indices),
                "source_prior_bank_analysis_bound_by_audit": str(
                    source_prior_bank_audit.get("analysis_sha256", "")
                ).lower()
                == file_sha256(paths["source_prior_bank_analysis"]).lower(),
                "source_prior_bank_bound_by_audit": str(
                    source_prior_bank_audit.get("bank_manifest_sha256", "")
                ).lower()
                == file_sha256(paths["source_prior_bank_manifest"]).lower(),
                "c1_bank_hash_bound": file_sha256(paths["c1_bank"]).lower()
                == CFG.c1_bank_sha256.lower(),
                "dev_pool_no_prior_overlap": len(dev_ids & prior_ids) == 0,
                "final_pool_no_prior_overlap": len(final_ids & prior_ids) == 0,
                "dev_final_disjoint": len(dev_ids & final_ids) == 0,
                "dev_pool_count": len(dev_ids) == int(CFG.selector_dev_pool[1]),
                "final_pool_count": len(final_ids) == int(CFG.final_pool[1]),
                "candidate_set_frozen": tuple(
                    source_prior_bank.get("candidate_arch_indices", ())
                )
                == tuple(CFG.compact_arch_indices),
                "anchor_A57": CFG.anchor_arch_idx == 57,
                "margin_grid_valid": _validate_margin_grid(),
                "target_steps_50": CFG.target_steps == 50,
                "same_case_seed_policy": CFG.target_seed_policy
                == "same_case_seed_for_all_candidates",
            }
        )
        upstream = {
            name: {"path": path, "sha256": file_sha256(path)}
            for name, path in paths.items()
        }

    decision = (
        "PASS_ANCHOR_SAFE_SELECTOR_PREFLIGHT_READY"
        if checks and all(checks.values())
        else "FAIL_ANCHOR_SAFE_SELECTOR_PREFLIGHT"
    )
    obj = {
        "study": "c3_2_selector_preflight",
        "decision": decision,
        "protocol": config_dict(),
        "checks": checks,
        "upstream_dependencies": upstream,
        "historical_pool_k_reused": False,
        "test_used": False,
    }
    atomic_json(obj, out_path)
    return obj


def _planned_candidates(feasible: set[int]) -> List[Tuple[str, int, str]]:
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


def run_candidate_pool(
    project_root: str,
    bank_manifest_path: str,
    out_path: str,
    device: str,
    safe_mode: str,
    pool_role: str,
    smoke: bool = False,
) -> Dict[str, Any]:
    if pool_role not in {"selector_dev", "final"}:
        raise ValueError("pool_role must be selector_dev or final")
    pool = CFG.selector_dev_pool if pool_role == "selector_dev" else CFG.final_pool
    root = os.path.abspath(project_root)
    preflight_path = os.path.join(root, CFG.output_root, "preflight", "anchor_safe_selector_preflight.json")
    if not os.path.isfile(preflight_path):
        raise FileNotFoundError("Run C3-2 preflight first")
    if load_json(preflight_path).get("decision") != "PASS_ANCHOR_SAFE_SELECTOR_PREFLIGHT_READY":
        raise RuntimeError("C3-2 preflight is not PASS")

    strong_manifest = _load_strong_manifest(root, bank_manifest_path)
    run_mode = "smoke" if smoke else "formal"
    # C3-2 always reuses the frozen formal source-prior-bank evaluation bank. Smoke only shortens
    # the target-center jobs; it must not create or require a second bank.
    if str(strong_manifest.get("run_mode")) != "formal":
        raise RuntimeError("C3-2 requires the frozen formal source-prior-bank evaluation bank")

    start, count, offset = pool
    cfg, cache, A, requested, safe = build_runtime(
        device, safe_mode, ((start, count, offset),)
    )
    if len(A) != CFG.architecture_count:
        raise RuntimeError("Architecture-space mismatch")
    frozen = load_frozen_assets(root)
    L = int(cfg.main.task.L)
    jobs = _pool_jobs(pool, smoke)

    out_path = os.path.abspath(out_path)
    result = (
        load_json(out_path)
        if os.path.isfile(out_path)
        else {
            "study": f"c3_2_{pool_role}_candidate_cache",
            "decision": "C32_CANDIDATE_CACHE_IN_PROGRESS",
            "pool_role": pool_role,
            "run_mode": run_mode,
            "protocol": config_dict(),
            "pool": list(pool),
            "bank_manifest": os.path.abspath(bank_manifest_path),
            "bank_manifest_sha256": file_sha256(bank_manifest_path),
            "records": {},
            "check_used_for_training_or_candidate_admission": False,
            "check_metrics_recorded_for_pool_evaluation": True,
            "same_case_seed_for_all_candidates": True,
            "historical_pool_k_reused": False,
            "test_used": False,
        }
    )
    if str(result.get("run_mode")) != run_mode:
        raise RuntimeError("Smoke/formal outputs cannot share one result file")
    if str(result.get("pool_role")) != pool_role:
        raise RuntimeError("Candidate-cache role mismatch")
    if tuple(result.get("pool", ())) != tuple(pool):
        raise RuntimeError("Candidate-cache pool mismatch")
    if result.get("bank_manifest_sha256") != file_sha256(bank_manifest_path):
        raise RuntimeError("Strong-bank manifest changed after run began")

    records = dict(result.get("records", {}))
    total_expected = 0
    for cid, H, K in jobs:
        Xs, *_rest, tier, _ctype = get_support_validation_check(
            cfg, cache, cid, H, K
        )
        feasible = set(feasible_indices(cfg, A, tier, L, int(Xs.shape[-1]), H))
        if CFG.anchor_arch_idx not in feasible:
            raise RuntimeError(f"PT-A57 infeasible for c{cid}_h{H}_k{K}")
        total_expected += len(_planned_candidates(feasible))

    completed_before = sum(len(r.get("candidates", {})) for r in records.values())
    newly_done = 0
    global_started = time.perf_counter()

    for case_no, (cid, H, K) in enumerate(jobs, 1):
        case_started = time.perf_counter()
        Xs, ys, Xv, yv, Xc, yc, tier, ctype = get_support_validation_check(
            cfg, cache, cid, H, K
        )
        input_dim = int(Xs.shape[-1])
        feasible = set(feasible_indices(cfg, A, tier, L, input_dim, H))
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
                    int(i) for i in CFG.compact_arch_indices if i in feasible
                ],
                "test_used": False,
            }
        )
        candidates = dict(rec.get("candidates", {}))
        # One case-level seed is shared by every architecture and initialization.
        target_seed = CFG.train_seed + 1009 * cid + 37 * H + 53 * K
        planned = _planned_candidates(feasible)

        for candidate_no, (source, idx, loader) in enumerate(planned, 1):
            token = f"{source}_A{idx}"
            if token in candidates and candidates[token].get("complete"):
                if int(candidates[token].get("target_seed", -1)) != target_seed:
                    raise RuntimeError(
                        f"Cached seed-policy mismatch for {case_key} {token}"
                    )
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
                _adapt_sgd_mse(model, Xs, ys, seed=target_seed)
                metrics = _evaluate(model, Xv, yv, Xc, yc)
                synchronize_if_cuda(actual)
                del model

            params, flops = profile_arch(spec, L=L, input_dim=input_dim, H=H)
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
                "elapsed_seconds": float(time.perf_counter() - cand_started),
            }
            rec["candidates"] = candidates
            rec["complete"] = False
            records[case_key] = rec
            result["records"] = records
            newly_done += 1
            done = completed_before + newly_done
            result["completed_candidate_count"] = done
            result["expected_candidate_count"] = total_expected
            result["completed_gradient_steps"] = done * CFG.target_steps
            atomic_json(result, out_path)

            elapsed = time.perf_counter() - global_started
            remaining = max(0, total_expected - done)
            avg = elapsed / max(1, newly_done)
            eta = avg * remaining
            finish = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(time.time() + eta)
            )
            print(
                f"[C3-2][{pool_role}] case={case_no}/{len(jobs)} "
                f"candidate={candidate_no}/{len(planned)} {case_key} {token} "
                f"done={done}/{total_expected} steps={done*CFG.target_steps} "
                f"case_elapsed={time.perf_counter()-case_started:.1f}s "
                f"elapsed={elapsed/3600:.2f}h avg={avg:.1f}s "
                f"eta={eta/3600:.2f}h finish={finish}",
                flush=True,
            )
            gc.collect()
            if requested.type == "cuda":
                torch.cuda.empty_cache()

        if len(candidates) != len(planned):
            raise RuntimeError(
                f"Candidate completeness mismatch for {case_key}: "
                f"{len(candidates)}/{len(planned)}"
            )
        rows = list(candidates.values())
        if sum(r["source"] == "PT_A57" for r in rows) != 1:
            raise RuntimeError("Exactly one PT-A57 anchor is required")
        if sum(r["source"] == "LEGACY_C1_A57" for r in rows) != 1:
            raise RuntimeError("Exactly one legacy C1-A57 row is required")
        if len({int(r["target_seed"]) for r in rows}) != 1:
            raise RuntimeError("All candidates in one case must share one seed")

        rec["summary"] = {
            "pt_anchor": next(r for r in rows if r["source"] == "PT_A57"),
            "check_oracle": _check_oracle(rows),
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
        f"C32_{pool_role.upper()}_CANDIDATES_COMPLETE"
        if result.get("complete")
        else f"C32_{pool_role.upper()}_CANDIDATES_INCOMPLETE"
    )
    atomic_json(result, out_path)
    return result


def _select_with_margin(
    rows: Sequence[Mapping[str, Any]], margin_rel: float
) -> Dict[str, Any]:
    anchors = [r for r in rows if str(r["source"]) == "PT_A57"]
    if len(anchors) != 1:
        raise RuntimeError("Exactly one PT-A57 anchor row is required")
    anchor = anchors[0]
    alternatives = [r for r in rows if r is not anchor]
    best_alt = min(
        alternatives,
        key=lambda r: (
            float(r["validation"]["weighted_mse"]),
            float(r["params"]),
            float(r["flops"]),
            int(r["arch_idx"]),
            str(r["source"]),
        ),
    )
    anchor_val = float(anchor["validation"]["weighted_mse"])
    best_alt_val = float(best_alt["validation"]["weighted_mse"])
    threshold = anchor_val * (1.0 - float(margin_rel))
    selected = best_alt if best_alt_val <= threshold else anchor
    switched = selected is best_alt
    return {
        "token": str(selected["token"]),
        "source": str(selected["source"]),
        "arch_idx": int(selected["arch_idx"]),
        "arch_key": str(selected["arch_key"]),
        "family": str(selected["family"]),
        "params": float(selected["params"]),
        "flops": float(selected["flops"]),
        "validation": selected["validation"],
        "check": selected["check"],
        "switched_from_pt_anchor": bool(switched),
        "margin_rel": float(margin_rel),
        "anchor_validation_mse": anchor_val,
        "best_alternative_validation_mse": best_alt_val,
        "switch_threshold_validation_mse": threshold,
    }


def _relative_gain(new: float, ref: float) -> float:
    return (float(ref) - float(new)) / max(float(ref), CFG.eps)


def _center_bootstrap(
    records: Mapping[str, Mapping[str, Any]],
    values: Mapping[str, float],
    seed: int,
) -> Dict[str, float]:
    by_center: Dict[int, List[float]] = defaultdict(list)
    for key, value in values.items():
        by_center[int(records[key]["center_id"])].append(float(value))
    centers = sorted(by_center)
    center_values = np.asarray(
        [float(np.mean(by_center[c])) for c in centers], dtype=np.float64
    )
    rng = np.random.default_rng(int(seed))
    boots = np.empty(CFG.bootstrap_repeats, dtype=np.float64)
    for i in range(CFG.bootstrap_repeats):
        idx = rng.integers(0, len(center_values), size=len(center_values))
        boots[i] = float(np.mean(center_values[idx]))
    return {
        "mean": float(np.mean(center_values)),
        "ci_low": float(np.quantile(boots, 0.025)),
        "ci_high": float(np.quantile(boots, 0.975)),
        "N_centers": int(len(centers)),
        "N_cases": int(len(values)),
    }


def _evaluate_margin(
    records: Mapping[str, Mapping[str, Any]], margin: float, seed: int
) -> Dict[str, Any]:
    primary_values: Dict[str, float] = {}
    arch_values: Dict[str, float] = {}
    oracle_values: Dict[str, float] = {}
    switched: List[bool] = []
    harmful: List[bool] = []
    selections: Dict[str, Any] = {}

    for key, rec in records.items():
        rows = list(rec["candidates"].values())
        pt = next(r for r in rows if r["source"] == "PT_A57")
        legacy = next(r for r in rows if r["source"] == "LEGACY_C1_A57")
        selected = _select_with_margin(rows, margin)
        dual = _select_with_margin([pt, legacy], margin)
        oracle = _check_oracle(rows)
        pt_mse = float(pt["check"]["weighted_mse"])
        selected_mse = float(selected["check"]["weighted_mse"])
        dual_mse = float(dual["check"]["weighted_mse"])
        oracle_mse = float(oracle["check"]["weighted_mse"])
        primary_values[key] = _relative_gain(selected_mse, pt_mse)
        arch_values[key] = _relative_gain(selected_mse, dual_mse)
        oracle_values[key] = _relative_gain(oracle_mse, pt_mse)
        is_switched = bool(selected["switched_from_pt_anchor"])
        switched.append(is_switched)
        harmful.append(is_switched and selected_mse > pt_mse)
        selections[key] = selected

    primary = _center_bootstrap(records, primary_values, seed + 1)
    architecture = _center_bootstrap(records, arch_values, seed + 2)
    oracle = _center_bootstrap(records, oracle_values, seed + 3)
    harmful_rate = float(np.mean(harmful))
    eligible = (
        primary["mean"] >= CFG.primary_gain_mean
        and primary["ci_low"] > CFG.primary_gain_ci_low
        and harmful_rate <= CFG.harmful_switch_rate_max
        and architecture["mean"] >= CFG.architecture_increment_mean
        and architecture["ci_low"] > CFG.architecture_increment_ci_low
    )
    return {
        "margin_rel": float(margin),
        "primary_gain_over_PT": primary,
        "architecture_increment_over_dual_A57": architecture,
        "check_oracle_headroom_over_PT": oracle,
        "switch_rate": float(np.mean(switched)),
        "harmful_switch_rate_all_cases": harmful_rate,
        "harmful_switch_count": int(sum(harmful)),
        "eligible": bool(eligible),
        "selections": selections,
    }


def calibrate_selector(
    project_root: str, dev_candidates_path: str, out_path: str
) -> Dict[str, Any]:
    _ = os.path.abspath(project_root)
    dev = load_json(dev_candidates_path)
    if not dev.get("complete"):
        raise RuntimeError("C3-2 selector-development candidate cache is incomplete")
    if str(dev.get("pool_role")) != "selector_dev":
        raise RuntimeError("Expected selector_dev candidate cache")
    if tuple(dev.get("pool", ())) != tuple(CFG.selector_dev_pool):
        raise RuntimeError("Selector-development pool mismatch")
    records = dev["records"]

    grid_results: Dict[str, Any] = {}
    eligible: List[float] = []
    for i, margin in enumerate(CFG.margin_grid):
        item = _evaluate_margin(records, float(margin), CFG.train_seed + 100 * i)
        # The full selections remain in the development result for audit.
        grid_results[f"{float(margin):.6f}"] = item
        if item["eligible"]:
            eligible.append(float(margin))

    selected_margin = min(eligible) if eligible else None
    decision = (
        "PASS_ANCHOR_SAFE_SELECTOR_FROZEN"
        if selected_margin is not None
        else "FAIL_ANCHOR_SAFE_SELECTOR_NO_SAFE_MARGIN"
    )
    result = {
        "study": "c3_2_selector_calibration",
        "decision": decision,
        "protocol": config_dict(),
        "selector_rule": CFG.selector_rule,
        "selected_margin_rel": selected_margin,
        "eligible_margins": eligible,
        "margin_grid_results": grid_results,
        "dev_candidates_path": os.path.abspath(dev_candidates_path),
        "dev_candidates_sha256": file_sha256(dev_candidates_path),
        "selection_uses": "development Check only for finite-grid calibration",
        "final_pool_opened": False,
        "historical_pool_k_reused": False,
        "test_used": False,
    }
    atomic_json(result, out_path)
    return result


def analyze_final(
    project_root: str,
    selector_path: str,
    final_candidates_path: str,
    out_path: str,
) -> Dict[str, Any]:
    _ = os.path.abspath(project_root)
    selector = load_json(selector_path)
    if selector.get("decision") != "PASS_ANCHOR_SAFE_SELECTOR_FROZEN":
        raise RuntimeError("C3-2 selector is not frozen PASS")
    final = load_json(final_candidates_path)
    if not final.get("complete") or str(final.get("pool_role")) != "final":
        raise RuntimeError("C3-2 final candidate cache is incomplete")
    if tuple(final.get("pool", ())) != tuple(CFG.final_pool):
        raise RuntimeError("C3-2 final pool mismatch")
    margin = float(selector["selected_margin_rel"])
    if margin not in tuple(float(x) for x in CFG.margin_grid):
        raise RuntimeError("Frozen selector margin is outside the registered grid")

    records = final["records"]
    evaluated = _evaluate_margin(records, margin, CFG.train_seed + 9000)
    primary = evaluated["primary_gain_over_PT"]
    architecture = evaluated["architecture_increment_over_dual_A57"]
    harmful_rate = float(evaluated["harmful_switch_rate_all_cases"])
    primary_pass = (
        primary["mean"] >= CFG.primary_gain_mean
        and primary["ci_low"] > CFG.primary_gain_ci_low
        and harmful_rate <= CFG.harmful_switch_rate_max
    )
    architecture_pass = (
        architecture["mean"] >= CFG.architecture_increment_mean
        and architecture["ci_low"] > CFG.architecture_increment_ci_low
    )

    selected_sources: Counter = Counter()
    selected_arches: Counter = Counter()
    by_group: Dict[str, Dict[str, List[float]]] = {
        "H": defaultdict(list),
        "K": defaultdict(list),
        "budget_tier": defaultdict(list),
        "center_type": defaultdict(list),
    }
    harmful_cases: List[Dict[str, Any]] = []
    selections = evaluated["selections"]
    for key, rec in records.items():
        selected = selections[key]
        pt = rec["summary"]["pt_anchor"]
        pt_mse = float(pt["check"]["weighted_mse"])
        sel_mse = float(selected["check"]["weighted_mse"])
        gain = _relative_gain(sel_mse, pt_mse)
        selected_sources[str(selected["source"])] += 1
        selected_arches[int(selected["arch_idx"])] += 1
        by_group["H"][str(rec["H"])].append(gain)
        by_group["K"][str(rec["K"])].append(gain)
        by_group["budget_tier"][str(rec["budget_tier"])].append(gain)
        by_group["center_type"][str(rec["center_type"])].append(gain)
        if selected["switched_from_pt_anchor"] and sel_mse > pt_mse:
            harmful_cases.append(
                {
                    "case_key": key,
                    "selected_source": selected["source"],
                    "selected_arch_idx": selected["arch_idx"],
                    "relative_gain": gain,
                }
            )

    group_summary = {
        axis: {
            key: {
                "N_cases": len(values),
                "case_mean_gain": float(np.mean(values)),
                "positive_case_rate": float(np.mean(np.asarray(values) > 0)),
            }
            for key, values in groups.items()
        }
        for axis, groups in by_group.items()
    }

    if primary_pass and architecture_pass:
        decision = "PROCEED_LIMITED_C3_COMPACT_ONLY"
        next_step = (
            "Freeze the source-prior-bank evaluation six-architecture bank and the C3-2 margin. "
            "Do not reopen the 66-architecture search."
        )
    elif primary_pass and not architecture_pass:
        decision = "STOP_COMPLEX_ARCH_SEARCH_KEEP_A57_SOURCE_SELECTION"
        next_step = (
            "The selector is safe, but non-A57 structures do not retain the "
            "registered incremental gain on the one-shot final pool."
        )
    elif primary["mean"] >= CFG.primary_gain_mean and harmful_rate > CFG.harmful_switch_rate_max:
        decision = "STOP_SELECTOR_EXPANSION_USE_MORE_CONSERVATIVE_ANCHOR"
        next_step = (
            "The one-shot final pool still violates the harmful-switch gate. "
            "Do not tune another threshold on this pool."
        )
    else:
        decision = "STOP_COMPLEX_ARCH_SEARCH_FIXED_PT_A57"
        next_step = (
            "The frozen selector does not provide stable final-pool gain. "
            "Retain PT-A57 as the deployment-safe default."
        )

    result = {
        "study": "c3_2_final_analysis",
        "decision": decision,
        "recommended_next_step": next_step,
        "protocol": config_dict(),
        "frozen_margin_rel": margin,
        "selector_sha256": file_sha256(selector_path),
        "final_candidates_sha256": file_sha256(final_candidates_path),
        "comparisons": {
            "compact_selector_over_PT": primary,
            "architecture_increment_over_dual_A57": architecture,
            "check_oracle_headroom_over_PT": evaluated[
                "check_oracle_headroom_over_PT"
            ],
        },
        "selection_safety": {
            "switch_rate": evaluated["switch_rate"],
            "harmful_switch_rate_all_cases": harmful_rate,
            "harmful_switch_count": evaluated["harmful_switch_count"],
            "harmful_cases": harmful_cases,
            "selected_sources": dict(selected_sources),
            "selected_arch_indices": {
                str(k): int(v) for k, v in sorted(selected_arches.items())
            },
        },
        "group_summary": group_summary,
        "gates": {
            "primary_gain_pass": bool(primary_pass),
            "architecture_increment_pass": bool(architecture_pass),
            "historical_pool_k_unused": True,
            "test_unused": True,
        },
        "final_pool_used_once_for_method_decision": True,
        "test_used": False,
    }
    atomic_json(result, out_path)
    return result


def audit(
    project_root: str,
    preflight_path: str,
    dev_candidates_path: str,
    selector_path: str,
    final_candidates_path: str,
    analysis_path: str,
    out_path: str,
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    preflight_obj = load_json(preflight_path)
    dev = load_json(dev_candidates_path)
    selector = load_json(selector_path)
    final = load_json(final_candidates_path)
    analysis_obj = load_json(analysis_path)
    bank_path = os.path.join(root, CFG.source_prior_bank_manifest_path)
    bank = _load_strong_manifest(root, bank_path)

    expected_cases = int(CFG.final_pool[1]) * len(CFG.H_list) * len(CFG.K_list)

    def candidate_cache_valid(obj: Mapping[str, Any], role: str, pool: Sequence[int]) -> bool:
        if not obj.get("complete") or str(obj.get("pool_role")) != role:
            return False
        if tuple(obj.get("pool", ())) != tuple(pool):
            return False
        for rec in obj.get("records", {}).values():
            rows = list(rec.get("candidates", {}).values())
            feasible = set(rec.get("hard_feasible_compact_indices", ()))
            expected = 2 + sum(
                1 for idx in CFG.compact_non_anchor_indices if idx in feasible
            )
            if len(rows) != expected:
                return False
            if len({int(r.get("target_seed", -1)) for r in rows}) != 1:
                return False
            if any(int(r.get("target_steps", -1)) != CFG.target_steps for r in rows):
                return False
        return True

    selected_margin = selector.get("selected_margin_rel")

    # Recompute the finite-grid calibration and final selector from the stored
    # candidate caches. This verifies that neither Check-based post-editing nor
    # a changed threshold can be hidden behind the JSON summaries.
    recomputed_eligible: List[float] = []
    selector_grid_reproducible = True
    for i, margin in enumerate(CFG.margin_grid):
        item = _evaluate_margin(
            dev["records"], float(margin), CFG.train_seed + 100 * i
        )
        stored_item = selector.get("margin_grid_results", {}).get(
            f"{float(margin):.6f}", {}
        )
        selector_grid_reproducible &= (
            bool(item["eligible"]) == bool(stored_item.get("eligible"))
            and abs(
                float(item["primary_gain_over_PT"]["mean"])
                - float(stored_item.get("primary_gain_over_PT", {}).get("mean", float("nan")))
            ) < 1e-12
            and int(item["harmful_switch_count"])
            == int(stored_item.get("harmful_switch_count", -1))
        )
        if item["eligible"]:
            recomputed_eligible.append(float(margin))

    final_selector_reproducible = False
    if selected_margin is not None:
        final_eval = _evaluate_margin(
            final["records"], float(selected_margin), CFG.train_seed + 9000
        )
        stored_primary = analysis_obj.get("comparisons", {}).get(
            "compact_selector_over_PT", {}
        )
        stored_safety = analysis_obj.get("selection_safety", {})
        final_selector_reproducible = (
            abs(float(final_eval["primary_gain_over_PT"]["mean"]) - float(stored_primary.get("mean", float("nan")))) < 1e-12
            and int(final_eval["harmful_switch_count"])
            == int(stored_safety.get("harmful_switch_count", -1))
        )

    checks = {
        "preflight_pass": preflight_obj.get("decision") == "PASS_ANCHOR_SAFE_SELECTOR_PREFLIGHT_READY",
        "source_prior_bank_still_frozen": bank.get("decision") == CFG.expected_source_prior_bank_decision,
        "dev_candidates_complete": candidate_cache_valid(
            dev, "selector_dev", CFG.selector_dev_pool
        ),
        "selector_frozen_pass": selector.get("decision") == "PASS_ANCHOR_SAFE_SELECTOR_FROZEN",
        "selector_dev_hash_bound": selector.get("dev_candidates_sha256")
        == file_sha256(dev_candidates_path),
        "selector_margin_registered": selected_margin
        in [float(x) for x in CFG.margin_grid],
        "selector_grid_reproducible": bool(selector_grid_reproducible),
        "selector_smallest_eligible": (
            selected_margin == min(recomputed_eligible)
            if recomputed_eligible
            else False
        ),
        "final_candidates_complete": candidate_cache_valid(
            final, "final", CFG.final_pool
        ),
        "final_case_count": int(final.get("N_records", -1)) == expected_cases,
        "final_bank_hash_bound": final.get("bank_manifest_sha256")
        == file_sha256(bank_path),
        "analysis_selector_hash_bound": analysis_obj.get("selector_sha256")
        == file_sha256(selector_path),
        "analysis_final_hash_bound": analysis_obj.get("final_candidates_sha256")
        == file_sha256(final_candidates_path),
        "final_selector_validation_only_reproducible": bool(
            final_selector_reproducible
        ),
        "dev_final_disjoint": len(
            _pool_ids(CFG.selector_dev_pool) & _pool_ids(CFG.final_pool)
        )
        == 0,
        "historical_pool_k_unused": not bool(
            dev.get("historical_pool_k_reused")
            or final.get("historical_pool_k_reused")
        ),
        "test_unused": not bool(
            preflight_obj.get("test_used")
            or dev.get("test_used")
            or selector.get("test_used")
            or final.get("test_used")
            or analysis_obj.get("test_used")
        ),
    }
    decision = (
        "PASS_ANCHOR_SAFE_SELECTOR_COMPLETE_AND_AUDITED"
        if all(checks.values())
        else "FAIL_ANCHOR_SAFE_SELECTOR_AUDIT"
    )
    result = {
        "study": "c3_2_selector_audit",
        "decision": decision,
        "checks": checks,
        "preflight_sha256": file_sha256(preflight_path),
        "dev_candidates_sha256": file_sha256(dev_candidates_path),
        "selector_sha256": file_sha256(selector_path),
        "final_candidates_sha256": file_sha256(final_candidates_path),
        "analysis_sha256": file_sha256(analysis_path),
        "analysis_decision": analysis_obj.get("decision"),
        "historical_pool_k_reused": False,
        "test_used": False,
    }
    atomic_json(result, out_path)
    return result
