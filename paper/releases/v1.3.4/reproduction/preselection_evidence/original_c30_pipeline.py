# -*- coding: utf-8 -*-
from __future__ import annotations

import gc
import json
import math
import os
import time
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from cfg.methods.c30_cfg import CFG, config_dict
from core.methods.ours.adapt import adapt_steps
from core.methods.ours.paper_engine import _load_prior_model
from core.methods.ours.stage2_runtime import candidate_backend_context, candidate_device, synchronize_if_cuda
from core.space import build_model, profile_arch
from final_e2e.data_access import get_support_validation_check
from final_e2e_c23.common import (
    atomic_json,
    build_runtime,
    eval_metrics,
    feasible_indices,
    file_sha256,
    load_frozen_assets,
    load_json,
    seed_all,
)


def _case_jobs(smoke: bool = False):
    start, count, _offset = CFG.diagnostic_pool
    jobs = [(cid, H, K) for cid in range(start, start + count) for H in CFG.H_list for K in CFG.K_list]
    return jobs[:2] if smoke else jobs


def _load_source_manifest(project_root: str) -> Dict[str, Any]:
    path = os.path.join(project_root, CFG.external_source_manifest)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing frozen external source manifest: {path}")
    obj = load_json(path)
    if obj.get("decision") != CFG.expected_source_decision:
        raise RuntimeError("External source assets are not frozen PASS")
    if obj.get("test_used") or obj.get("target_pool_used") or obj.get("validation_pool_k_used"):
        raise RuntimeError("External source assets contain target/test use")
    for item in obj.get("assets", {}).values():
        full = os.path.join(project_root, str(item["path"]).replace("\\", os.sep).replace("/", os.sep))
        if not os.path.isfile(full):
            raise FileNotFoundError(f"Missing source asset: {full}")
        if file_sha256(full).lower() != str(item["sha256"]).lower():
            raise RuntimeError(f"Source asset hash mismatch: {full}")
    return obj


def _load_pt_anchor(
    project_root: str,
    manifest: Mapping[str, Any],
    A: Sequence[Any],
    *,
    H: int,
    tier: str,
    input_dim: int,
    L: int,
    device: torch.device,
) -> Tuple[nn.Module, Any, int]:
    bb = manifest["fixed_backbones"][f"h{H}_b{tier}"]
    idx = int(bb["arch_idx"])
    if idx != CFG.anchor_arch_idx:
        raise RuntimeError(f"Frozen PT anchor changed: expected A{CFG.anchor_arch_idx}, got A{idx}")
    spec = A[idx]
    asset = manifest["assets"][f"pt_ft_h{H}_b{tier}"]
    asset_path = os.path.join(project_root, str(asset["path"]).replace("\\", os.sep).replace("/", os.sep))
    state = torch.load(asset_path, map_location=device)
    model = build_model(spec, input_dim=input_dim, H=H, L=L, device=str(device))
    model.load_state_dict(state, strict=True)
    return model, spec, idx


def _adapt_sgd_mse(model: nn.Module, Xs: torch.Tensor, ys: torch.Tensor, *, seed: int) -> None:
    dev = next(model.parameters()).device
    seed_all(seed, dev)
    model.train()
    opt = optim.SGD(model.parameters(), lr=CFG.sgd_lr)
    Xd, yd = Xs.to(dev).contiguous(), ys.to(dev).contiguous()
    for _ in range(CFG.sgd_steps):
        opt.zero_grad(set_to_none=True)
        loss = ((model(Xd) - yd) ** 2).mean()
        if not torch.isfinite(loss):
            raise RuntimeError("Non-finite SGD/MSE target loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), CFG.sgd_grad_clip)
        opt.step()


def _adapt_adam_huber(model: nn.Module, Xs: torch.Tensor, ys: torch.Tensor, *, seed: int) -> None:
    dev = next(model.parameters()).device
    adapt_steps(
        model,
        Xs.to(dev).contiguous(),
        ys.to(dev).contiguous(),
        steps=CFG.huber_steps,
        lr=CFG.huber_lr,
        weight_decay=0.0,
        robust_loss_type="huber",
        huber_delta=CFG.huber_delta,
        cvar_lambda=0.0,
        prior_state=None,
        prior_group_lambdas=None,
        batch_size=0,
        use_amp=False,
        oom_to_cpu=False,
        seed=int(seed),
        max_grad_norm=CFG.huber_grad_clip,
    )


def _metrics(model: nn.Module, Xv, yv, Xc, yc) -> Dict[str, Any]:
    return {
        "validation": eval_metrics(model, Xv, yv),
        "check": eval_metrics(model, Xc, yc),
    }


def _new_fixed_result(project_root: str, frozen_hashes: Mapping[str, str], source_manifest: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "study": "c3_0_fixed_anchor_factorization",
        "protocol": config_dict(),
        "recipes": {
            "D1_PT_A57_SGD_MSE50": "PT-A57 initialization + SGD/MSE 50",
            "D2_C1_A57_SGD_MSE50": "C1-A57 initialization + SGD/MSE 50",
            "D3_PT_A57_ADAM_HUBER50": "PT-A57 initialization + current STD50 Adam/Huber 50",
            "D4_C1_A57_ADAM_HUBER50": "C1-A57 initialization + current STD50 Adam/Huber 50",
        },
        "frozen_asset_hashes": dict(frozen_hashes),
        "source_manifest_sha256": file_sha256(os.path.join(project_root, CFG.external_source_manifest)),
        "records": {},
        "support_used_for_adaptation": True,
        "validation_used_for_diagnostic_metrics": True,
        "check_used_for_causal_diagnosis": True,
        "test_used": False,
    }


def run_fixed_anchor(project_root: str, out_path: str, device: str, safe_mode: str, smoke: bool = False) -> Dict[str, Any]:
    start, count, offset = CFG.diagnostic_pool
    cfg, cache, A, requested, safe = build_runtime(device, safe_mode, ((start, count, offset),))
    frozen = load_frozen_assets(project_root)
    source_manifest = _load_source_manifest(project_root)
    L = int(cfg.main.task.L)
    jobs = _case_jobs(smoke)
    out_path = os.path.abspath(out_path)
    result = load_json(out_path) if os.path.isfile(out_path) else _new_fixed_result(project_root, frozen["hashes"], source_manifest)
    records = dict(result.get("records", {}))
    started = time.perf_counter()
    new_cases = 0

    for case_no, (cid, H, K) in enumerate(jobs, 1):
        Xs, ys, Xv, yv, Xc, yc, tier, ctype = get_support_validation_check(cfg, cache, cid, H, K)
        case_key = f"c{cid}_h{H}_k{K}_b{tier}"
        if case_key in records and bool(records[case_key].get("complete")):
            continue
        input_dim = int(Xs.shape[-1])
        spec = A[CFG.anchor_arch_idx]
        if CFG.anchor_arch_idx not in feasible_indices(cfg, A, tier, L, input_dim, H):
            raise RuntimeError(f"A57 anchor infeasible for {case_key}")
        actual = candidate_device(spec, requested, safe)
        seed0 = CFG.train_seed + 1009 * cid + 37 * H + 53 * K
        case_started = time.perf_counter()
        rec: Dict[str, Any] = {
            "case_key": case_key,
            "center_id": int(cid),
            "center_type": str(ctype),
            "budget_tier": str(tier),
            "H": int(H),
            "K": int(K),
            "anchor_arch_idx": CFG.anchor_arch_idx,
            "arch_key": str(spec.arch_key),
            "family": str(spec.family),
            "recipes": {},
            "test_used": False,
        }

        with candidate_backend_context(spec, actual, safe):
            # Direct initialization metrics are recorded to separate source quality from target optimization.
            pt_direct, _spec, _idx = _load_pt_anchor(project_root, source_manifest, A, H=H, tier=tier, input_dim=input_dim, L=L, device=actual)
            rec["pt_direct"] = _metrics(pt_direct, Xv, yv, Xc, yc)
            del pt_direct
            c1_direct, _prior = _load_prior_model(spec=spec, H=H, L=L, input_dim=input_dim, bank=frozen["bank"], device=actual)
            rec["c1_direct"] = _metrics(c1_direct, Xv, yv, Xc, yc)
            del c1_direct

            pt_sgd, _spec, _idx = _load_pt_anchor(project_root, source_manifest, A, H=H, tier=tier, input_dim=input_dim, L=L, device=actual)
            _adapt_sgd_mse(pt_sgd, Xs, ys, seed=seed0 + 11)
            rec["recipes"]["D1"] = _metrics(pt_sgd, Xv, yv, Xc, yc)
            del pt_sgd

            c1_sgd, _prior = _load_prior_model(spec=spec, H=H, L=L, input_dim=input_dim, bank=frozen["bank"], device=actual)
            _adapt_sgd_mse(c1_sgd, Xs, ys, seed=seed0 + 23)
            rec["recipes"]["D2"] = _metrics(c1_sgd, Xv, yv, Xc, yc)
            del c1_sgd

            pt_huber, _spec, _idx = _load_pt_anchor(project_root, source_manifest, A, H=H, tier=tier, input_dim=input_dim, L=L, device=actual)
            _adapt_adam_huber(pt_huber, Xs, ys, seed=seed0 + 37)
            rec["recipes"]["D3"] = _metrics(pt_huber, Xv, yv, Xc, yc)
            del pt_huber

            c1_huber, _prior = _load_prior_model(spec=spec, H=H, L=L, input_dim=input_dim, bank=frozen["bank"], device=actual)
            _adapt_adam_huber(c1_huber, Xs, ys, seed=seed0 + 41)
            rec["recipes"]["D4"] = _metrics(c1_huber, Xv, yv, Xc, yc)
            del c1_huber
            synchronize_if_cuda(actual)

        params, flops = profile_arch(spec, L=L, input_dim=input_dim, H=H)
        rec["params"] = float(params)
        rec["flops"] = float(flops)
        rec["complete"] = True
        rec["elapsed_seconds"] = float(time.perf_counter() - case_started)
        records[case_key] = rec
        result["records"] = records
        result["N_records"] = len(records)
        result["expected_records"] = len(jobs)
        result["complete"] = len(records) == len(jobs)
        atomic_json(result, out_path)
        new_cases += 1
        elapsed = time.perf_counter() - started
        eta = elapsed / max(1, new_cases) * max(0, len(jobs) - case_no)
        print(
            f"[C3-0][Fixed] case={case_no}/{len(jobs)} {case_key} D1={rec['recipes']['D1']['check']['weighted_mse']:.6g} D2={rec['recipes']['D2']['check']['weighted_mse']:.6g} D3={rec['recipes']['D3']['check']['weighted_mse']:.6g} D4={rec['recipes']['D4']['check']['weighted_mse']:.6g} elapsed={elapsed/3600:.2f}h eta={eta/3600:.2f}h",
            flush=True,
        )
        gc.collect()
        if requested.type == "cuda":
            torch.cuda.empty_cache()

    result["decision"] = "C30_FIXED_ANCHOR_FACTORIZATION_COMPLETE" if result.get("complete") else "C30_FIXED_ANCHOR_INCOMPLETE"
    atomic_json(result, out_path)
    return result


def _new_oracle_result(frozen_hashes: Mapping[str, str], fixed_path: str) -> Dict[str, Any]:
    return {
        "study": "c3_0_c1_architecture_headroom_oracle",
        "protocol": config_dict(),
        "fixed_anchor_result": os.path.abspath(fixed_path),
        "fixed_anchor_sha256": file_sha256(fixed_path),
        "frozen_asset_hashes": dict(frozen_hashes),
        "records": {},
        "candidate_initialization": "C1_architecture_indexed_bank",
        "candidate_target_recipe": "SGD_MSE_50",
        "check_oracle_is_non_deployable": True,
        "validation_selector_is_deployable_diagnostic": True,
        "test_used": False,
    }


def run_c1_oracle(project_root: str, fixed_path: str, out_path: str, device: str, safe_mode: str, smoke: bool = False) -> Dict[str, Any]:
    if not os.path.isfile(fixed_path):
        raise FileNotFoundError(f"Run fixed-anchor diagnostic first: {fixed_path}")
    fixed = load_json(fixed_path)
    if not fixed.get("complete"):
        raise RuntimeError("Fixed-anchor diagnostic is incomplete")
    start, count, offset = CFG.diagnostic_pool
    cfg, cache, A, requested, safe = build_runtime(device, safe_mode, ((start, count, offset),))
    frozen = load_frozen_assets(project_root)
    L = int(cfg.main.task.L)
    jobs = _case_jobs(smoke)
    out_path = os.path.abspath(out_path)
    result = load_json(out_path) if os.path.isfile(out_path) else _new_oracle_result(frozen["hashes"], fixed_path)
    records = dict(result.get("records", {}))
    global_started = time.perf_counter()
    total_expected = 0
    for cid, H, K in jobs:
        Xs, ys, _Xv, _yv, _Xc, _yc, tier, _ctype = get_support_validation_check(cfg, cache, cid, H, K)
        total_expected += len(feasible_indices(cfg, A, tier, L, int(Xs.shape[-1]), H))
    completed_before = sum(len(r.get("candidates", {})) for r in records.values())
    newly_done = 0

    for case_no, (cid, H, K) in enumerate(jobs, 1):
        Xs, ys, Xv, yv, Xc, yc, tier, ctype = get_support_validation_check(cfg, cache, cid, H, K)
        case_key = f"c{cid}_h{H}_k{K}_b{tier}"
        input_dim = int(Xs.shape[-1])
        feasible = feasible_indices(cfg, A, tier, L, input_dim, H)
        if not feasible:
            raise RuntimeError(f"No feasible architectures for {case_key}")
        rec = dict(records.get(case_key, {}))
        rec.update({
            "case_key": case_key,
            "center_id": int(cid),
            "center_type": str(ctype),
            "budget_tier": str(tier),
            "H": int(H),
            "K": int(K),
            "feasible_indices": [int(i) for i in feasible],
            "test_used": False,
        })
        candidates = dict(rec.get("candidates", {}))
        seed0 = CFG.train_seed + 1009 * cid + 37 * H + 53 * K

        for pos, idx in enumerate(feasible, 1):
            k = str(idx)
            if k in candidates and bool(candidates[k].get("complete")):
                continue
            spec = A[idx]
            actual = candidate_device(spec, requested, safe)
            cand_started = time.perf_counter()
            with candidate_backend_context(spec, actual, safe):
                model, _prior = _load_prior_model(spec=spec, H=H, L=L, input_dim=input_dim, bank=frozen["bank"], device=actual)
                _adapt_sgd_mse(model, Xs, ys, seed=seed0 + 101 * idx)
                val = eval_metrics(model, Xv, yv)
                chk = eval_metrics(model, Xc, yc)
                synchronize_if_cuda(actual)
                del model
            params, flops = profile_arch(spec, L=L, input_dim=input_dim, H=H)
            candidates[k] = {
                "arch_idx": int(idx),
                "arch_key": str(spec.arch_key),
                "family": str(spec.family),
                "params": float(params),
                "flops": float(flops),
                "validation": val,
                "check": chk,
                "complete": True,
                "elapsed_seconds": float(time.perf_counter() - cand_started),
            }
            rec["candidates"] = candidates
            rec["complete"] = False
            records[case_key] = rec
            result["records"] = records
            result["completed_candidate_count"] = completed_before + newly_done + 1
            result["expected_candidate_count"] = total_expected
            atomic_json(result, out_path)
            newly_done += 1
            elapsed = time.perf_counter() - global_started
            remaining = max(0, total_expected - completed_before - newly_done)
            eta = elapsed / max(1, newly_done) * remaining
            print(
                f"[C3-0][Oracle] case={case_no}/{len(jobs)} arch={pos}/{len(feasible)} {case_key} A={idx} {spec.family} done={completed_before+newly_done}/{total_expected} elapsed={elapsed/3600:.2f}h eta={eta/3600:.2f}h",
                flush=True,
            )
            gc.collect()
            if requested.type == "cuda":
                torch.cuda.empty_cache()

        rows = list(candidates.values())
        if len(rows) != len(feasible):
            raise RuntimeError(f"Candidate completeness mismatch for {case_key}")
        best_check = min(rows, key=lambda r: (float(r["check"]["weighted_mse"]), r["params"], r["flops"], r["arch_idx"]))
        best_val = min(rows, key=lambda r: (float(r["validation"]["weighted_mse"]), r["params"], r["flops"], r["arch_idx"]))
        fixed_case = fixed["records"][case_key]
        d1 = fixed_case["recipes"]["D1"]
        d2 = fixed_case["recipes"]["D2"]
        pt_val = float(d1["validation"]["weighted_mse"])
        pt_chk = float(d1["check"]["weighted_mse"])
        c1_best_val = float(best_val["validation"]["weighted_mse"])
        if c1_best_val < pt_val:
            union_val_source = "C1_ARCH_CANDIDATE"
            union_val_check = float(best_val["check"]["weighted_mse"])
            union_val_arch = int(best_val["arch_idx"])
        else:
            union_val_source = "PT_A57_ANCHOR"
            union_val_check = pt_chk
            union_val_arch = CFG.anchor_arch_idx
        rec["summary"] = {
            "pt_anchor_D1": d1,
            "c1_anchor_D2": d2,
            "c1_check_oracle": best_check,
            "c1_validation_selected": best_val,
            "union_check_oracle_mse": min(pt_chk, float(best_check["check"]["weighted_mse"])),
            "union_check_oracle_source": "PT_A57_ANCHOR" if pt_chk <= float(best_check["check"]["weighted_mse"]) else "C1_ARCH_CANDIDATE",
            "union_validation_selected_check_mse": union_val_check,
            "union_validation_selected_source": union_val_source,
            "union_validation_selected_arch_idx": int(union_val_arch),
        }
        rec["complete"] = True
        records[case_key] = rec
        result["records"] = records
        result["N_records"] = len(records)
        result["expected_records"] = len(jobs)
        result["complete"] = len(records) == len(jobs) and all(bool(r.get("complete")) for r in records.values())
        atomic_json(result, out_path)

    result["decision"] = "C30_C1_ORACLE_COMPLETE" if result.get("complete") else "C30_C1_ORACLE_INCOMPLETE"
    atomic_json(result, out_path)
    return result


def _relative_gain(new: float, ref: float) -> float:
    return float((float(ref) - float(new)) / (abs(float(ref)) + CFG.eps))


def _center_bootstrap(values_by_center: Mapping[int, Sequence[float]], seed: int) -> Dict[str, Any]:
    centers = sorted(values_by_center)
    arr = np.asarray([np.mean(values_by_center[c]) for c in centers], dtype=float)
    if arr.size == 0:
        return {"mean": None, "median": None, "ci_low": None, "ci_high": None, "n_centers": 0}
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


def _comparison(records: Mapping[str, Any], new_path: Sequence[str], ref_path: Sequence[str], seed: int) -> Dict[str, Any]:
    by_center: Dict[int, list] = defaultdict(list)
    raw = []
    for rec in records.values():
        a: Any = rec
        b: Any = rec
        for p in new_path:
            a = a[p]
        for p in ref_path:
            b = b[p]
        g = _relative_gain(float(a), float(b))
        by_center[int(rec["center_id"])].append(g)
        raw.append(g)
    out = _center_bootstrap(by_center, seed)
    out["N_cases"] = len(raw)
    out["case_mean"] = float(np.mean(raw)) if raw else None
    out["positive_case_rate"] = float(np.mean(np.asarray(raw) > 0)) if raw else None
    return out


def analyze(project_root: str, fixed_path: str, oracle_path: Optional[str], out_path: str) -> Dict[str, Any]:
    fixed = load_json(fixed_path)
    if not fixed.get("complete"):
        raise RuntimeError("Fixed diagnostic is incomplete")
    frec = fixed["records"]
    comparisons = {
        "PT_init_over_C1_under_SGD": _comparison(frec, ("recipes", "D1", "check", "weighted_mse"), ("recipes", "D2", "check", "weighted_mse"), CFG.train_seed + 1),
        "SGD_over_Huber_with_PT_init": _comparison(frec, ("recipes", "D1", "check", "weighted_mse"), ("recipes", "D3", "check", "weighted_mse"), CFG.train_seed + 2),
        "SGD_over_Huber_with_C1_init": _comparison(frec, ("recipes", "D2", "check", "weighted_mse"), ("recipes", "D4", "check", "weighted_mse"), CFG.train_seed + 3),
        "PT_direct_over_C1_direct": _comparison(frec, ("pt_direct", "check", "weighted_mse"), ("c1_direct", "check", "weighted_mse"), CFG.train_seed + 4),
    }
    source_dominant = comparisons["PT_init_over_C1_under_SGD"]["mean"] >= CFG.dominant_effect_mean and comparisons["PT_init_over_C1_under_SGD"]["ci_low"] > 0
    recipe_stats = [comparisons["SGD_over_Huber_with_PT_init"], comparisons["SGD_over_Huber_with_C1_init"]]
    recipe_dominant = any(x["mean"] >= CFG.dominant_effect_mean and x["ci_low"] > 0 for x in recipe_stats)

    result: Dict[str, Any] = {
        "study": "c3_0_causal_diagnostic_analysis",
        "protocol": config_dict(),
        "fixed_anchor_sha256": file_sha256(fixed_path),
        "fixed_anchor_comparisons": comparisons,
        "diagnosis": {
            "source_initialization_dominant": bool(source_dominant),
            "target_recipe_dominant": bool(recipe_dominant),
        },
        "test_used": False,
    }

    if oracle_path and os.path.isfile(oracle_path):
        oracle = load_json(oracle_path)
        if not oracle.get("complete"):
            raise RuntimeError("Oracle diagnostic is incomplete")
        orec = oracle["records"]
        # Oracle records repeat fixed metrics inside summary; analyze directly.
        oracle_cmp = {
            "C1_check_oracle_over_PT_A57": _comparison(orec, ("summary", "c1_check_oracle", "check", "weighted_mse"), ("summary", "pt_anchor_D1", "check", "weighted_mse"), CFG.train_seed + 11),
            "C1_val_selected_over_PT_A57": _comparison(orec, ("summary", "c1_validation_selected", "check", "weighted_mse"), ("summary", "pt_anchor_D1", "check", "weighted_mse"), CFG.train_seed + 12),
            "Anchor_union_check_oracle_over_PT_A57": _comparison(orec, ("summary", "union_check_oracle_mse"), ("summary", "pt_anchor_D1", "check", "weighted_mse"), CFG.train_seed + 13),
            "Anchor_union_val_selected_over_PT_A57": _comparison(orec, ("summary", "union_validation_selected_check_mse"), ("summary", "pt_anchor_D1", "check", "weighted_mse"), CFG.train_seed + 14),
        }
        check_oracle = oracle_cmp["Anchor_union_check_oracle_over_PT_A57"]
        val_union = oracle_cmp["Anchor_union_val_selected_over_PT_A57"]
        oracle_headroom = check_oracle["mean"] >= CFG.oracle_headroom_mean and check_oracle["ci_low"] >= CFG.oracle_headroom_ci_low
        realizable_headroom = val_union["mean"] >= CFG.realizable_headroom_mean and val_union["ci_low"] > CFG.realizable_headroom_ci_low
        fam = Counter(str(r["summary"]["c1_check_oracle"]["family"]) for r in orec.values())
        idx = Counter(int(r["summary"]["c1_check_oracle"]["arch_idx"]) for r in orec.values())
        union_sources = Counter(str(r["summary"]["union_validation_selected_source"]) for r in orec.values())
        result["oracle_sha256"] = file_sha256(oracle_path)
        result["oracle_comparisons"] = oracle_cmp
        result["oracle_distribution"] = {
            "check_oracle_family": dict(fam),
            "check_oracle_arch_idx_top10": [{"arch_idx": int(k), "count": int(v)} for k, v in idx.most_common(10)],
            "union_validation_selected_source": dict(union_sources),
        }
        result["diagnosis"].update({
            "architecture_oracle_headroom_confirmed": bool(oracle_headroom),
            "validation_selected_headroom_confirmed": bool(realizable_headroom),
        })
        if realizable_headroom:
            decision = "PROCEED_C3_ANCHOR_PROTECTED_SEARCH"
            next_step = "Build anchor-protected candidate selection; first upgrade source bank only for candidate architectures that repeatedly win the C1 oracle."
        elif oracle_headroom:
            decision = "PROCEED_C3_STRONG_BANK_AND_SELECTOR_RESEARCH"
            next_step = "Architecture headroom exists only under oracle access; improve source priors and validation selector before any new final pool."
        else:
            decision = "STOP_COMPLEX_ARCH_SEARCH_FIXED_ANCHOR_DOMINANT"
            next_step = "Current architecture space does not show sufficient headroom over PT-A57; refocus on safe fixed-anchor adaptation rather than broader search."
    else:
        decision = "C30_FIXED_FACTORIZATION_COMPLETE_RUN_C1_ORACLE"
        next_step = "Run the C1 architecture oracle before deciding whether C3 architecture search is viable."

    result["decision"] = decision
    result["recommended_next_step"] = next_step
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    atomic_json(result, out_path)
    return result


def audit(project_root: str, fixed_path: str, oracle_path: str, analysis_path: str, out_path: str) -> Dict[str, Any]:
    fixed = load_json(fixed_path)
    oracle = load_json(oracle_path)
    analysis_obj = load_json(analysis_path)
    start, count, _ = CFG.diagnostic_pool
    expected_cases = count * len(CFG.H_list) * len(CFG.K_list)
    checks = {
        "fixed_complete": bool(fixed.get("complete")) and int(fixed.get("N_records", -1)) == expected_cases,
        "oracle_complete": bool(oracle.get("complete")) and int(oracle.get("N_records", -1)) == expected_cases,
        "fixed_test_unused": fixed.get("test_used") is False,
        "oracle_test_unused": oracle.get("test_used") is False,
        "analysis_test_unused": analysis_obj.get("test_used") is False,
        "diagnostic_pool_exact": tuple(fixed.get("protocol", {}).get("diagnostic_pool", ())) == tuple(CFG.diagnostic_pool),
        "anchor_A57_bound": all(int(r.get("anchor_arch_idx", -1)) == CFG.anchor_arch_idx for r in fixed.get("records", {}).values()),
        "four_recipes_complete": all(set(r.get("recipes", {}).keys()) == {"D1", "D2", "D3", "D4"} for r in fixed.get("records", {}).values()),
        "oracle_hard_feasible_nonempty": all(len(r.get("feasible_indices", [])) > 0 for r in oracle.get("records", {}).values()),
        "oracle_candidate_complete": all(len(r.get("candidates", {})) == len(r.get("feasible_indices", [])) for r in oracle.get("records", {}).values()),
        "internal_final_audit_bound": False,
        "external_final_audit_bound": False,
        "c1_bank_hash_bound": False,
    }
    int_path = os.path.join(project_root, CFG.final_internal_audit)
    ext_path = os.path.join(project_root, CFG.external_audit)
    bank_path = os.path.join(project_root, CFG.c1_bank_path)
    if os.path.isfile(int_path):
        checks["internal_final_audit_bound"] = load_json(int_path).get("decision") == CFG.expected_internal_decision
    if os.path.isfile(ext_path):
        checks["external_final_audit_bound"] = load_json(ext_path).get("decision") == CFG.expected_external_decision
    if os.path.isfile(bank_path):
        checks["c1_bank_hash_bound"] = file_sha256(bank_path).lower() == CFG.c1_bank_sha256.lower()
    decision = "PASS_C30_DIAGNOSTIC_COMPLETE_AND_AUDITED" if all(checks.values()) else "FAIL_C30_DIAGNOSTIC_AUDIT"
    obj = {
        "study": "c3_0_diagnostic_audit",
        "decision": decision,
        "checks": checks,
        "fixed_sha256": file_sha256(fixed_path),
        "oracle_sha256": file_sha256(oracle_path),
        "analysis_sha256": file_sha256(analysis_path),
        "analysis_decision": analysis_obj.get("decision"),
        "N_cases": expected_cases,
        "test_used": False,
    }
    atomic_json(obj, out_path)
    return obj
