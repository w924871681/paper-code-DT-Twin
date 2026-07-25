# -*- coding: utf-8 -*-
"""Expanded Alibaba source/calibration/held-out experiment.

Protocol:
  * 20 source machines train one strong initialization per retained architecture;
  * 20 disjoint machines calibrate a domain-specific selector margin;
  * 40 further disjoint machines are opened only after the margin is frozen;
  * the frozen synthetic margin (10%) is evaluated on the same held-out targets.

The workload trace is real. Complexity tiers remain deterministic controlled
labels, so the experiment is described as semi-real.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import time
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.optim as optim

from configs.methods.pre_submission_enhancements_cfg import CFG, config_dict
from core.methods.ours.stage2_runtime import (
    candidate_backend_context,
    candidate_device,
    synchronize_if_cuda,
)
from core.space import build_model, is_feasible, profile_arch
from experiments.main.pipeline import _atomic_torch_save
from experiments.main.real_trace import (
    _collect_selected,
    _count_machines,
    _feature_matrix,
    _load_processed,
    _make_windows,
    _open_machine_usage_text,
    _real_case_split,
    _real_runtime,
    _resample_machine,
    _source_normalization,
    _stable_key,
)
from shared.evaluation.common import atomic_json, eval_metrics, file_sha256, seed_all


def _assign_types(ids: Sequence[str], target_cv: Mapping[str, float]) -> Dict[str, str]:
    ordered = sorted(ids, key=lambda m: (float(target_cv[m]), _stable_key(m)))
    n = len(ordered)
    out: Dict[str, str] = {}
    for rank, mid in enumerate(ordered):
        frac = rank / max(1, n)
        out[mid] = "A" if frac < 1 / 3 else ("B" if frac < 2 / 3 else "C")
    return out


def _assign_tiers(ids: Sequence[str]) -> Dict[str, str]:
    """Assign approximately 30% tight, 40% medium, 30% loose."""
    ordered = sorted(ids, key=lambda m: _stable_key("budget:" + m))
    n = len(ordered)
    n_tight = int(round(0.30 * n))
    n_medium = int(round(0.40 * n))
    n_tight = max(1, min(n - 2, n_tight))
    n_medium = max(1, min(n - n_tight - 1, n_medium))
    out: Dict[str, str] = {}
    for rank, mid in enumerate(ordered):
        out[mid] = "tight" if rank < n_tight else (
            "medium" if rank < n_tight + n_medium else "loose"
        )
    return out


def prepare_alibaba_domain_trace(
    input_path: str,
    out_dir: str,
    *,
    verify_archive: bool = True,
) -> Dict[str, Any]:
    input_path = os.path.abspath(input_path)
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    if not os.path.isfile(input_path):
        raise FileNotFoundError(input_path)

    archive_hash = file_sha256(input_path)
    if (
        verify_archive
        and input_path.lower().endswith((".tar.gz", ".tgz"))
        and archive_hash.lower() != CFG.alibaba_expected_archive_sha256.lower()
    ):
        raise RuntimeError(
            "Alibaba machine_usage archive SHA-256 mismatch. "
            "Use --skip-archive-hash-check only for a documented mirror."
        )

    counts = _count_machines(input_path)
    eligible = sorted(
        [m for m, n in counts.items() if n >= CFG.alibaba_min_points],
        key=_stable_key,
    )
    needed = (
        CFG.alibaba_source_machines
        + CFG.alibaba_calibration_machines
        + CFG.alibaba_target_machines
    )
    if len(eligible) < needed:
        raise RuntimeError(
            f"Only {len(eligible)} machines have >= {CFG.alibaba_min_points} points; "
            f"need {needed}."
        )

    selected = eligible[:needed]
    s0 = CFG.alibaba_source_machines
    s1 = s0 + CFG.alibaba_calibration_machines
    source_ids = selected[:s0]
    calibration_ids = selected[s0:s1]
    target_ids = selected[s1:needed]

    collected = _collect_selected(input_path, set(selected))
    resampled: Dict[str, Tuple[np.ndarray, np.ndarray, float]] = {}
    for mid in selected:
        resampled[mid] = _resample_machine(
            collected[mid], CFG.alibaba_max_points_per_machine
        )

    norm = _source_normalization([resampled[m][0] for m in source_ids])
    arrays: Dict[str, Any] = {}
    cv: Dict[str, float] = {}
    for i, mid in enumerate(selected):
        raw, mask, step = resampled[mid]
        X, y = _feature_matrix(raw, mask, step, norm)
        arrays[f"X_{i}"] = X
        arrays[f"y_{i}"] = y
        arrays[f"id_{i}"] = np.asarray(mid)
        arrays[f"step_{i}"] = np.asarray(step, dtype=np.float64)
        if mid not in source_ids:
            cv[mid] = float(np.std(y) / (np.mean(y) + 1e-6))

    npz_path = os.path.join(out_dir, "alibaba2018_domain_calibrated_processed.npz")
    np.savez_compressed(npz_path, **arrays)

    center_types = {
        **_assign_types(calibration_ids, cv),
        **_assign_types(target_ids, cv),
    }
    budget_tiers = {
        **_assign_tiers(calibration_ids),
        **_assign_tiers(target_ids),
    }

    manifest = {
        "study": "alibaba2018_domain_calibrated_semi_real_preparation",
        "decision": "PASS_REAL_TRACE_PREPARED",
        "protocol": config_dict(),
        "source": {
            "dataset": "Alibaba cluster-trace-v2018 machine_usage",
            "input_path": input_path,
            "input_sha256": archive_hash,
            "official_expected_archive_sha256": CFG.alibaba_expected_archive_sha256,
            "archive_hash_verified": (
                not input_path.lower().endswith((".tar.gz", ".tgz"))
                or archive_hash.lower() == CFG.alibaba_expected_archive_sha256.lower()
            ),
        },
        "processed_npz": npz_path,
        "processed_sha256": file_sha256(npz_path),
        "source_machine_ids": list(source_ids),
        "calibration_machine_ids": list(calibration_ids),
        "target_machine_ids": list(target_ids),
        "center_types": center_types,
        "budget_tiers": budget_tiers,
        "normalization": norm,
        "feature_definition": {
            "input_dim": 25,
            "target": "cpu_utilization",
        },
        "semi_real_note": (
            "Workload observations are real Alibaba machine-usage traces; "
            "complexity tiers are deterministic controlled labels."
        ),
        "selection_uses_test": False,
        "test_used": False,
    }
    manifest_path = os.path.join(out_dir, "real_trace_domain_manifest.json")
    atomic_json(manifest, manifest_path)
    return manifest


def _source_windows(X: np.ndarray, y: np.ndarray, L: int, H: int):
    Xw, yw = _make_windows(X, y, L, H)
    n = int(Xw.shape[0])
    take = min(CFG.alibaba_source_windows_per_machine, n)
    idx = np.linspace(0, n - 1, take, dtype=int)
    return Xw[idx], yw[idx]


def build_alibaba_domain_bank(
    project_root: str,
    manifest_path: str,
    out_dir: str,
    device: str,
    safe_mode: str,
    smoke: bool = False,
) -> Dict[str, Any]:
    del project_root
    manifest, mapping = _load_processed(manifest_path)
    cfg, A, requested, safe = _real_runtime(device, safe_mode)
    L = int(cfg.main.task.L)
    input_dim = 25
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    bank_manifest_path = os.path.join(out_dir, "domain_real_bank_manifest.json")
    run_mode = "smoke" if smoke else "formal"
    bank = (
        json.load(open(bank_manifest_path, encoding="utf-8"))
        if os.path.isfile(bank_manifest_path)
        else {
            "study": "alibaba2018_domain_real_source_bank",
            "decision": "REAL_BANK_IN_PROGRESS",
            "run_mode": run_mode,
            "protocol": config_dict(),
            "source_machine_ids": list(manifest["source_machine_ids"]),
            "candidate_arch_indices": list(CFG.compact_arch_indices),
            "source_recipe": {
                "optimizer": "Adam",
                "loss": "MSE",
                "epochs": 1 if smoke else CFG.alibaba_source_epochs,
                "lr": CFG.alibaba_source_lr,
                "batch_size": CFG.alibaba_source_batch_size,
                "weight_decay": CFG.alibaba_source_weight_decay,
            },
            "assets": {},
            "target_machines_used": False,
            "calibration_machines_used": False,
            "test_used": False,
        }
    )
    if bank.get("run_mode") != run_mode:
        raise RuntimeError("Smoke/formal outputs cannot share bank directory")

    epochs = 1 if smoke else CFG.alibaba_source_epochs
    jobs = [(int(H), int(idx)) for H in CFG.H_list for idx in CFG.compact_arch_indices]
    started_all = time.perf_counter()
    completed_new = 0

    for job_no, (H, idx) in enumerate(jobs, 1):
        key = f"h{H}_a{idx}"
        out_file = os.path.join(out_dir, f"domain_real_h{H}_a{idx}.pt")
        old = bank.get("assets", {}).get(key)
        if old and os.path.isfile(out_file) and file_sha256(out_file) == old.get("sha256"):
            continue

        spec = A[idx]
        actual = candidate_device(spec, requested, safe)
        checkpoint = out_file + ".progress.pt"
        with candidate_backend_context(spec, actual, safe):
            seed = CFG.train_seed + 101 * H + idx
            seed_all(seed, actual)
            model = build_model(spec, input_dim=input_dim, H=H, L=L, device=str(actual))
            opt = optim.Adam(
                model.parameters(),
                lr=CFG.alibaba_source_lr,
                weight_decay=CFG.alibaba_source_weight_decay,
            )
            start_epoch = 0
            if os.path.isfile(checkpoint):
                state = torch.load(checkpoint, map_location=actual)
                model.load_state_dict(state["model"], strict=True)
                opt.load_state_dict(state["optimizer"])
                start_epoch = int(state.get("next_epoch", 0))

            last_loss: Optional[float] = None
            for epoch in range(start_epoch, epochs):
                centers = list(manifest["source_machine_ids"])
                random.Random(seed + epoch).shuffle(centers)
                if smoke:
                    centers = centers[:2]
                losses: List[float] = []
                for mid in centers:
                    Xw, yw = _source_windows(mapping[mid][0], mapping[mid][1], L, H)
                    if smoke:
                        Xw, yw = Xw[:20], yw[:20]
                    generator = torch.Generator(device=Xw.device)
                    generator.manual_seed(
                        seed + epoch + int(hashlib.sha256(mid.encode()).hexdigest()[:8], 16)
                    )
                    order = torch.randperm(int(Xw.shape[0]), generator=generator)
                    for left in range(0, int(Xw.shape[0]), CFG.alibaba_source_batch_size):
                        ids = order[left : left + CFG.alibaba_source_batch_size]
                        xb = Xw.index_select(0, ids).to(actual)
                        yb = yw.index_select(0, ids).to(actual)
                        model.train()
                        opt.zero_grad(set_to_none=True)
                        loss = ((model(xb.contiguous()) - yb.contiguous()) ** 2).mean()
                        if not torch.isfinite(loss):
                            raise RuntimeError("Non-finite Alibaba source loss")
                        loss.backward()
                        opt.step()
                        losses.append(float(loss.detach().item()))
                last_loss = float(np.mean(losses))
                _atomic_torch_save(
                    {
                        "model": {k: v.detach().cpu() for k, v in model.state_dict().items()},
                        "optimizer": opt.state_dict(),
                        "next_epoch": epoch + 1,
                    },
                    checkpoint,
                )
                elapsed = time.perf_counter() - started_all
                print(
                    f"[AlibabaDomainBank] job={job_no}/{len(jobs)} H={H} A={idx} "
                    f"epoch={epoch+1}/{epochs} loss={last_loss:.6g} "
                    f"elapsed={elapsed/3600:.2f}h",
                    flush=True,
                )

            synchronize_if_cuda(actual)
            _atomic_torch_save(
                {k: v.detach().cpu() for k, v in model.state_dict().items()}, out_file
            )
            if os.path.isfile(checkpoint):
                os.remove(checkpoint)
            del model, opt

        params, operations = profile_arch(spec, L=L, input_dim=input_dim, H=H)
        bank.setdefault("assets", {})[key] = {
            "path": out_file,
            "sha256": file_sha256(out_file),
            "H": int(H),
            "arch_idx": int(idx),
            "arch_key": str(spec.arch_key),
            "family": str(spec.family),
            "epochs": int(epochs),
            "final_source_loss": last_loss,
            "params": float(params),
            "operations": float(operations),
        }
        bank["completed_assets"] = len(bank["assets"])
        bank["expected_assets"] = len(jobs)
        atomic_json(bank, bank_manifest_path)
        completed_new += 1

    bank["complete"] = len(bank.get("assets", {})) == len(jobs)
    bank["decision"] = "PASS_DOMAIN_REAL_SOURCE_BANK" if bank["complete"] else "REAL_BANK_INCOMPLETE"
    atomic_json(bank, bank_manifest_path)
    return bank


def _load_bank_model(
    bank: Mapping[str, Any], A: Sequence[Any], H: int, idx: int,
    input_dim: int, L: int, device: torch.device,
) -> torch.nn.Module:
    item = bank["assets"][f"h{H}_a{idx}"]
    model = build_model(A[idx], input_dim=input_dim, H=H, L=L, device=str(device))
    try:
        state = torch.load(item["path"], map_location=device, weights_only=True)
    except TypeError:
        state = torch.load(item["path"], map_location=device)
    model.load_state_dict(state, strict=True)
    return model


def _candidate_order(row: Mapping[str, Any]) -> Tuple[float, float, float, int]:
    return (
        float(row["validation"]["weighted_mse"]),
        float(row["params"]),
        float(row["operations"]),
        int(row["arch_idx"]),
    )


def _adapt_case_candidates(
    *,
    trace: Mapping[str, Any],
    mapping: Mapping[str, Tuple[np.ndarray, np.ndarray]],
    bank: Mapping[str, Any],
    cfg: Any,
    A: Sequence[Any],
    requested: torch.device,
    safe_mode: str,
    mid: str,
    H: int,
    K: int,
    include_test: bool,
    smoke: bool,
    selection_taus: Sequence[float] = (),
) -> Dict[str, Any]:
    L = int(cfg.main.task.L)
    input_dim = 25
    (Xs, ys), (Xv, yv), (Xc, yc), (Xt, yt) = _real_case_split(
        mapping[mid][0], mapping[mid][1], L, H, K
    )
    tier = str(trace["budget_tiers"][mid])
    feasible = [
        idx for idx in CFG.compact_arch_indices
        if is_feasible(A[idx], cfg.main.budget, tier, L, input_dim, H)
    ]
    if CFG.anchor_arch_idx not in feasible:
        raise RuntimeError("Alibaba A57 reference is infeasible")

    seed = (
        CFG.train_seed
        + int(hashlib.sha256(mid.encode()).hexdigest()[:8], 16)
        + 37 * H
        + 53 * K
    )
    rows: List[Dict[str, Any]] = []
    states: Dict[str, Dict[str, torch.Tensor]] = {}
    for idx in feasible:
        spec = A[idx]
        actual = candidate_device(spec, requested, safe_mode)
        with candidate_backend_context(spec, actual, safe_mode):
            model = _load_bank_model(bank, A, H, idx, input_dim, L, actual)
            seed_all(seed, actual)
            model.train()
            opt = optim.SGD(model.parameters(), lr=CFG.target_lr)
            for _ in range(1 if smoke else CFG.target_steps):
                opt.zero_grad(set_to_none=True)
                loss = ((model(Xs.to(actual)) - ys.to(actual)) ** 2).mean()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), CFG.target_grad_clip)
                opt.step()
            validation = eval_metrics(model, Xv, yv)
            check = eval_metrics(model, Xc, yc)
            params, operations = profile_arch(spec, L=L, input_dim=input_dim, H=H)
            token = "PT_A57" if idx == CFG.anchor_arch_idx else f"A{idx}"
            rows.append(
                {
                    "token": token,
                    "arch_idx": int(idx),
                    "arch_key": str(spec.arch_key),
                    "family": str(spec.family),
                    "params": float(params),
                    "operations": float(operations),
                    "validation": validation,
                    "check": check,
                }
            )
            states[token] = {
                k: v.detach().cpu().clone() for k, v in model.state_dict().items()
            }
            del model, opt

    frozen_case = {"candidates": rows}
    pre_test_selections = {
        f"{float(tau):.6g}": {
            "selected_token": _select_token(frozen_case, float(tau))[0],
            "switched": _select_token(frozen_case, float(tau))[1],
        }
        for tau in selection_taus
    }

    tests: Dict[str, Dict[str, float]] = {}
    if include_test:
        # The selected token for every reported threshold is fixed from
        # validation values before the test tensors are evaluated.
        for row in rows:
            token = str(row["token"])
            idx = int(row["arch_idx"])
            spec = A[idx]
            actual = candidate_device(spec, requested, safe_mode)
            with candidate_backend_context(spec, actual, safe_mode):
                model = build_model(spec, input_dim=input_dim, H=H, L=L, device=str(actual))
                model.load_state_dict(states[token], strict=True)
                tests[token] = eval_metrics(model, Xt, yt)
                del model

    return {
        "machine_id_hash": hashlib.sha256(mid.encode()).hexdigest(),
        "center_type": str(trace["center_types"][mid]),
        "budget_tier": tier,
        "H": int(H),
        "K": int(K),
        "candidates": rows,
        "pre_test_selections": pre_test_selections,
        "tests": tests,
        "selection_uses_test": False,
    }


def _select_token(case: Mapping[str, Any], tau: float) -> Tuple[str, bool]:
    rows = list(case["candidates"])
    anchor = next(row for row in rows if row["token"] == "PT_A57")
    alternatives = [row for row in rows if row["token"] != "PT_A57"]
    if not alternatives:
        return "PT_A57", False
    best = min(alternatives, key=_candidate_order)
    switched = float(best["validation"]["weighted_mse"]) <= (
        float(anchor["validation"]["weighted_mse"]) * (1.0 - float(tau))
    )
    return (str(best["token"]) if switched else "PT_A57"), bool(switched)


def _gain(new: float, ref: float) -> float:
    return float((float(ref) - float(new)) / (abs(float(ref)) + CFG.eps))


def _cluster_bootstrap(
    values: Mapping[str, Sequence[float]], seed: int
) -> Dict[str, float]:
    machine_means = np.asarray(
        [np.mean(values[mid]) for mid in sorted(values)], dtype=float
    )
    if machine_means.size == 0:
        return {"mean": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"), "N_machines": 0}
    rng = np.random.default_rng(int(seed))
    ids = rng.integers(
        0,
        len(machine_means),
        size=(CFG.bootstrap_repeats, len(machine_means)),
    )
    boot = machine_means[ids].mean(axis=1)
    return {
        "mean": float(machine_means.mean()),
        "ci_low": float(np.quantile(boot, 0.025)),
        "ci_high": float(np.quantile(boot, 0.975)),
        "N_machines": int(len(machine_means)),
    }


def _calibration_summary(
    cases: Sequence[Mapping[str, Any]], tau: float
) -> Dict[str, Any]:
    gains_by_machine: Dict[str, List[float]] = defaultdict(list)
    harmful = 0
    switched = 0
    for case in cases:
        token, did_switch = _select_token(case, tau)
        rows = {str(row["token"]): row for row in case["candidates"]}
        ref = float(rows["PT_A57"]["check"]["weighted_mse"])
        selected = float(rows[token]["check"]["weighted_mse"])
        gains_by_machine[str(case["machine_id_hash"])].append(_gain(selected, ref))
        switched += int(did_switch)
        harmful += int(did_switch and selected > ref)
    ci = _cluster_bootstrap(gains_by_machine, CFG.train_seed + int(round(1000 * tau)))
    n = len(cases)
    return {
        "tau": float(tau),
        "N_cases": int(n),
        "alternative_selections": int(switched),
        "switch_rate": float(switched / max(1, n)),
        "harmful_selections": int(harmful),
        "harmful_rate_all_cases": float(harmful / max(1, n)),
        "harmful_rate_alternatives": float(harmful / max(1, switched)),
        "mean_check_gain": float(ci["mean"]),
        "check_gain_ci_low": float(ci["ci_low"]),
        "check_gain_ci_high": float(ci["ci_high"]),
        "eligible": bool(
            harmful / max(1, n) <= CFG.allowed_harmful_rate
            and ci["mean"] >= CFG.minimum_mean_gain
            and (
                not CFG.require_positive_ci_low
                or ci["ci_low"] > 0.0
            )
        ),
    }


def _target_summary(
    cases: Sequence[Mapping[str, Any]], tau: float
) -> Dict[str, Any]:
    gains_by_machine: Dict[str, List[float]] = defaultdict(list)
    log_ratios: List[float] = []
    selected_mses: List[float] = []
    ref_mses: List[float] = []
    absolute_diffs: List[float] = []
    harmful = 0
    beneficial = 0
    switched = 0
    oracle_mses: List[float] = []

    for case in cases:
        token, did_switch = _select_token(case, tau)
        tests = case["tests"]
        ref = float(tests["PT_A57"]["weighted_mse"])
        selected = float(tests[token]["weighted_mse"])
        oracle = min(float(v["weighted_mse"]) for v in tests.values())
        selected_mses.append(selected)
        ref_mses.append(ref)
        oracle_mses.append(oracle)
        absolute_diffs.append(selected - ref)
        log_ratios.append(float(math.log((selected + CFG.eps) / (ref + CFG.eps))))
        gain = _gain(selected, ref)
        gains_by_machine[str(case["machine_id_hash"])].append(gain)
        switched += int(did_switch)
        harmful += int(did_switch and selected > ref)
        beneficial += int(did_switch and selected < ref)

    ci = _cluster_bootstrap(gains_by_machine, CFG.train_seed + 9000 + int(round(1000 * tau)))
    selected_arr = np.asarray(selected_mses, dtype=float)
    ref_arr = np.asarray(ref_mses, dtype=float)
    oracle_arr = np.asarray(oracle_mses, dtype=float)
    all_case_gains = np.asarray(
        [g for values in gains_by_machine.values() for g in values], dtype=float
    )
    return {
        "tau": float(tau),
        "N_cases": int(len(cases)),
        "N_machines": int(len(gains_by_machine)),
        "selected_mean_mse": float(selected_arr.mean()),
        "reference_mean_mse": float(ref_arr.mean()),
        "aggregate_ratio_reduction": float(
            (ref_arr.mean() - selected_arr.mean()) / (abs(ref_arr.mean()) + CFG.eps)
        ),
        "mean_case_relative_reduction": float(all_case_gains.mean()),
        "median_case_relative_reduction": float(np.median(all_case_gains)),
        "case_relative_reduction_ci_low": float(ci["ci_low"]),
        "case_relative_reduction_ci_high": float(ci["ci_high"]),
        "mean_absolute_mse_difference_selected_minus_reference": float(np.mean(absolute_diffs)),
        "median_log_mse_ratio": float(np.median(log_ratios)),
        "alternative_selections": int(switched),
        "beneficial_alternative_selections": int(beneficial),
        "harmful_alternative_selections": int(harmful),
        "harmful_rate_all_cases": float(harmful / max(1, len(cases))),
        "harmful_rate_alternatives": float(harmful / max(1, switched)),
        "test_oracle_mean_mse": float(oracle_arr.mean()),
        "test_oracle_aggregate_reduction": float(
            (ref_arr.mean() - oracle_arr.mean()) / (abs(ref_arr.mean()) + CFG.eps)
        ),
    }


def run_alibaba_domain_calibration_and_eval(
    project_root: str,
    manifest_path: str,
    bank_dir: str,
    out_path: str,
    device: str,
    safe_mode: str,
    smoke: bool = False,
) -> Dict[str, Any]:
    del project_root
    trace, mapping = _load_processed(manifest_path)
    bank_path = os.path.join(os.path.abspath(bank_dir), "domain_real_bank_manifest.json")
    bank = json.load(open(bank_path, "r", encoding="utf-8"))
    if bank.get("decision") != "PASS_DOMAIN_REAL_SOURCE_BANK":
        raise RuntimeError("Domain Alibaba source bank is not PASS")

    cfg, A, requested, safe = _real_runtime(device, safe_mode)
    calibration_machines = list(trace["calibration_machine_ids"])
    target_machines = list(trace["target_machine_ids"])
    if smoke:
        calibration_machines = calibration_machines[:2]
        target_machines = target_machines[:2]

    run_mode = "smoke" if smoke else "formal"
    result = (
        json.load(open(out_path, encoding="utf-8"))
        if os.path.isfile(out_path)
        else {
            "study": "alibaba2018_independent_domain_calibration_and_test",
            "decision": "ALIBABA_DOMAIN_EXPERIMENT_IN_PROGRESS",
            "run_mode": run_mode,
            "protocol": config_dict(),
            "trace_manifest_sha256": file_sha256(manifest_path),
            "bank_manifest_sha256": file_sha256(bank_path),
            "calibration_records": {},
            "target_records": {},
            "selection_uses_test": False,
        }
    )
    if result.get("run_mode") != run_mode:
        raise RuntimeError("Smoke/formal outputs cannot share one result file")

    cal_records = dict(result.get("calibration_records", {}))
    for mid in calibration_machines:
        for H in CFG.H_list:
            for K in CFG.K_list:
                key = f"m{hashlib.sha256(mid.encode()).hexdigest()[:10]}_h{H}_k{K}_cal"
                if key in cal_records:
                    continue
                case = _adapt_case_candidates(
                    trace=trace,
                    mapping=mapping,
                    bank=bank,
                    cfg=cfg,
                    A=A,
                    requested=requested,
                    safe_mode=safe,
                    mid=mid,
                    H=int(H),
                    K=int(K),
                    include_test=False,
                    smoke=smoke,
                    selection_taus=(),
                )
                cal_records[key] = case
                result["calibration_records"] = cal_records
                atomic_json(result, out_path)
                print(f"[AlibabaDomain] calibration {len(cal_records)} cases", flush=True)

    calibration_cases = list(cal_records.values())
    calibration_grid = [
        _calibration_summary(calibration_cases, tau) for tau in CFG.threshold_grid
    ]
    eligible = [row for row in calibration_grid if row["eligible"]]
    domain_tau = min((float(row["tau"]) for row in eligible), default=None)
    result["calibration_grid"] = calibration_grid
    result["domain_calibrated_tau"] = domain_tau
    result["calibration_complete"] = len(calibration_cases) == (
        len(calibration_machines) * len(CFG.H_list) * len(CFG.K_list)
    )
    atomic_json(result, out_path)

    target_records = dict(result.get("target_records", {}))
    for mid in target_machines:
        for H in CFG.H_list:
            for K in CFG.K_list:
                key = f"m{hashlib.sha256(mid.encode()).hexdigest()[:10]}_h{H}_k{K}_test"
                if key in target_records:
                    continue
                case = _adapt_case_candidates(
                    trace=trace,
                    mapping=mapping,
                    bank=bank,
                    cfg=cfg,
                    A=A,
                    requested=requested,
                    safe_mode=safe,
                    mid=mid,
                    H=int(H),
                    K=int(K),
                    include_test=True,
                    smoke=smoke,
                    selection_taus=tuple(
                        [CFG.frozen_margin_rel]
                        + ([] if domain_tau is None else [float(domain_tau)])
                    ),
                )
                target_records[key] = case
                result["target_records"] = target_records
                atomic_json(result, out_path)
                print(f"[AlibabaDomain] held-out {len(target_records)} cases", flush=True)

    target_cases = list(target_records.values())
    summaries = {
        "zero_recalibration_tau_0_10": _target_summary(
            target_cases, CFG.frozen_margin_rel
        )
    }
    if domain_tau is not None:
        summaries["domain_calibrated"] = _target_summary(target_cases, domain_tau)
    else:
        summaries["domain_calibrated"] = {
            "available": False,
            "reason": "No threshold satisfied the pre-registered calibration criteria",
        }

    result["target_summaries"] = summaries
    result["target_complete"] = len(target_cases) == (
        len(target_machines) * len(CFG.H_list) * len(CFG.K_list)
    )
    result["decision"] = (
        "PASS_ALIBABA_DOMAIN_CALIBRATION_AND_HELDOUT_COMPLETE"
        if result["calibration_complete"] and result["target_complete"]
        else "ALIBABA_DOMAIN_EXPERIMENT_INCOMPLETE"
    )
    result["test_used_only_after_selector_values_frozen"] = True
    atomic_json(result, out_path)
    return result
