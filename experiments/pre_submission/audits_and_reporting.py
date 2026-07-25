# -*- coding: utf-8 -*-
"""Generate no-retraining audits and manuscript-ready figures/tables."""
from __future__ import annotations

import csv
import json
import math
import os
import re
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from configs.main_cfg import get_cfg
from configs.methods.pre_submission_enhancements_cfg import CFG, config_dict
from core.space import enumerate_A_base, profile_arch
from shared.evaluation.common import atomic_json


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_csv(path: str, rows: Sequence[Mapping[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("")
        return
    columns: List[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _constraint_class(operations: float, params: float, bf: float, bp: float) -> str:
    op_bad = float(operations) > float(bf)
    p_bad = float(params) > float(bp)
    if op_bad and p_bad:
        return "both"
    if op_bad:
        return "operation_only"
    if p_bad:
        return "parameter_only"
    return "feasible"


def generate_constraint_activity(out_dir: str) -> Dict[str, Any]:
    cfg = get_cfg()
    A = enumerate_A_base(cfg.arch)
    input_dim = 25
    rows: List[Dict[str, Any]] = []
    detailed: List[Dict[str, Any]] = []

    scopes: Dict[str, List[Tuple[str, int]]] = {
        "full_66_architectures": [(f"A{i}", i) for i in range(len(A))],
        "compact_6_architectures": [(f"A{i}", i) for i in CFG.compact_arch_indices],
        "main_7_candidates": [
            ("PT_A57", 57),
            ("LEGACY_C1_A57", 57),
            *[(f"STRONG_A{i}", i) for i in CFG.compact_non_anchor_indices],
        ],
    }

    for H in CFG.H_list:
        for scope, items in scopes.items():
            for tier_name in ("tight", "medium", "loose"):
                tier = getattr(cfg.budget, tier_name)
                counts = Counter()
                for token, idx in items:
                    params, operations = profile_arch(
                        A[int(idx)], L=cfg.task.L, input_dim=input_dim, H=int(H)
                    )
                    cls = _constraint_class(operations, params, tier.flops, tier.params)
                    counts[cls] += 1
                    detailed.append(
                        {
                            "H": int(H),
                            "scope": scope,
                            "tier": tier_name,
                            "token": token,
                            "arch_idx": int(idx),
                            "family": str(A[int(idx)].family),
                            "params": int(params),
                            "estimated_operations": int(operations),
                            "classification": cls,
                        }
                    )
                rows.append(
                    {
                        "H": int(H),
                        "scope": scope,
                        "tier": tier_name,
                        "N": int(len(items)),
                        "feasible": int(counts["feasible"]),
                        "operation_only": int(counts["operation_only"]),
                        "parameter_only": int(counts["parameter_only"]),
                        "both": int(counts["both"]),
                    }
                )

    summary_path = os.path.join(out_dir, "constraint_activity_summary.csv")
    detail_path = os.path.join(out_dir, "constraint_activity_details.csv")
    _write_csv(summary_path, rows)
    _write_csv(detail_path, detailed)
    return {"summary": summary_path, "details": detail_path, "rows": rows}


def generate_safety_table(project_root: str, out_dir: str) -> Optional[str]:
    source = os.path.join(
        project_root,
        "results",
        "figure_data",
        "tableS8_safety_across_pools.csv",
    )
    if not os.path.isfile(source):
        return None

    df = pd.read_csv(source, encoding="utf-8-sig")
    alternative_rate_column = next(
        (
            name
            for name in (
                "Alternative-selection rate / all cases (%)",
                "Switch rate (%)",
            )
            if name in df.columns
        ),
        None,
    )
    harmful_rate_column = next(
        (
            name
            for name in (
                "Harmful alternatives / all cases (%)",
                "Harmful rate (%)",
            )
            if name in df.columns
        ),
        None,
    )
    required = {"Cases"}
    missing = sorted(required - set(df.columns))
    if alternative_rate_column is None:
        missing.append("alternative-selection rate column")
    if harmful_rate_column is None:
        missing.append("harmful-alternative rate column")
    if missing:
        raise ValueError(
            "Unsupported tableS8_safety_across_pools.csv schema; "
            f"missing={missing}, columns={list(df.columns)}"
        )

    alternative_rate = pd.to_numeric(df[alternative_rate_column], errors="raise")
    harmful_rate = pd.to_numeric(df[harmful_rate_column], errors="raise")
    cases = pd.to_numeric(df["Cases"], errors="raise")

    df["Alternative-conditioned harmful rate (%)"] = np.where(
        alternative_rate > 0,
        100.0 * harmful_rate / alternative_rate,
        0.0,
    )
    df["Alternative selections"] = np.rint(
        cases * alternative_rate / 100.0
    ).astype(int)
    df["Harmful selections"] = np.rint(
        cases * harmful_rate / 100.0
    ).astype(int)

    out = os.path.join(out_dir, "safety_across_pools_expanded.csv")
    df.to_csv(out, index=False, encoding="utf-8-sig")
    return out


def _method_mapping() -> Dict[str, str]:
    return {
        "Ours": "ours_c32_locked",
        "PT+FT": "pt_ft",
        "MeDeT-style": "medet_style",
        "Scratch50": "scratch50",
        "Meta+NAS-lite": "meta_nas_lite",
        "Zero-NAS": "zero_nas",
        "Zero-NAS+FT": "zero_nas_ft",
    }


def _pareto_mask(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    keep = np.ones(len(x), dtype=bool)
    for i in range(len(x)):
        for j in range(len(x)):
            if i == j:
                continue
            if x[j] <= x[i] and y[j] <= y[i] and (x[j] < x[i] or y[j] < y[i]):
                keep[i] = False
                break
    return keep


def generate_pareto_figure(project_root: str, out_dir: str) -> Dict[str, str]:
    overall_path = os.path.join(project_root, "results", "main", "overall_comparison.csv")
    runtime_path = os.path.join(project_root, "results", "supplementary", "repeated_runtime_summary.csv")
    overall = pd.read_csv(overall_path)
    runtime = pd.read_csv(runtime_path, encoding="utf-8-sig")
    overall["runtime_method"] = overall["Method"].map(_method_mapping())
    merged = overall.merge(runtime, left_on="runtime_method", right_on="method", how="inner")
    merged = merged.rename(columns={"WMSE": "MSE"})
    merged["marker_area"] = 45.0 + 12.0 * merged["adapted_candidates_mean"].astype(float)
    merged["pareto"] = _pareto_mask(
        merged["mean_seconds"].to_numpy(float), merged["MSE"].to_numpy(float)
    )

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    markers = ["o", "s", "^", "D", "P", "X", "v"]
    for marker, (_, row) in zip(markers, merged.iterrows()):
        ax.errorbar(
            float(row["mean_seconds"]),
            float(row["MSE"]),
            xerr=float(row["repeat_mean_std_seconds"]),
            fmt=marker,
            markersize=max(6.0, math.sqrt(float(row["marker_area"]))),
            capsize=3,
            label=str(row["Method"]),
        )
    frontier = merged[merged["pareto"]].sort_values("mean_seconds")
    if len(frontier) > 1:
        ax.plot(frontier["mean_seconds"], frontier["MSE"], linestyle="--", linewidth=1.0)
    ax.set_xscale("log")
    ax.set_xlabel("Target-side instantiation time (s, log scale)")
    ax.set_ylabel("Held-out test MSE")
    ax.grid(True, which="both", linestyle=":", linewidth=0.6)
    ax.legend(ncol=2, fontsize=8)
    fig.tight_layout()
    pdf = os.path.join(out_dir, "fig10_accuracy_instantiation_pareto.pdf")
    png = os.path.join(out_dir, "fig10_accuracy_instantiation_pareto.png")
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=300, bbox_inches="tight")
    plt.close(fig)

    table = os.path.join(out_dir, "fig10_accuracy_instantiation_pareto_data.csv")
    merged[
        [
            "Method", "MSE", "mean_seconds", "repeat_mean_std_seconds",
            "adapted_candidates_mean", "pareto",
        ]
    ].to_csv(table, index=False, encoding="utf-8-sig")
    return {"pdf": pdf, "png": png, "data": table}


def _center_id_from_record(key: str, rec: Mapping[str, Any]) -> Optional[int]:
    for candidate in (
        rec.get("center_id"),
        rec.get("case", {}).get("center_id") if isinstance(rec.get("case"), Mapping) else None,
        rec.get("summary", {}).get("center_id") if isinstance(rec.get("summary"), Mapping) else None,
    ):
        if candidate is not None:
            return int(candidate)
    match = re.search(r"(?:^|_)c(\d+)(?:_|$)", key)
    return int(match.group(1)) if match else None


def generate_distinct_center_retention_audit(project_root: str, out_dir: str) -> Optional[str]:
    path = os.path.join(project_root, "outputs", "c30_d2904_t2904", "oracle", "c30_c1_oracle.json")
    if not os.path.isfile(path):
        return None
    obj = _read_json(path)
    check_cases: Dict[int, List[Tuple[int, str]]] = defaultdict(list)
    val_cases: Dict[int, List[Tuple[int, str]]] = defaultdict(list)
    for key, rec in obj.get("records", {}).items():
        summary = rec.get("summary", {})
        center_id = _center_id_from_record(str(key), rec)
        if center_id is None:
            continue
        pt_check = float(summary["pt_anchor_D1"]["check"]["weighted_mse"])
        best_check = summary["c1_check_oracle"]
        if float(best_check["check"]["weighted_mse"]) < pt_check:
            check_cases[int(best_check["arch_idx"])].append((center_id, str(key)))
        if (
            str(summary["union_validation_selected_source"]) == "C1_ARCH_CANDIDATE"
            and float(summary["union_validation_selected_check_mse"]) < pt_check
        ):
            val_cases[int(summary["union_validation_selected_arch_idx"])].append((center_id, str(key)))

    rows: List[Dict[str, Any]] = []
    for idx in sorted(set(check_cases) | set(val_cases)):
        check_centers = {c for c, _ in check_cases[idx]}
        val_centers = {c for c, _ in val_cases[idx]}
        rows.append(
            {
                "arch_idx": int(idx),
                "check_true_win_cases": len(check_cases[idx]),
                "check_true_win_distinct_centers": len(check_centers),
                "validation_positive_win_cases": len(val_cases[idx]),
                "validation_positive_win_distinct_centers": len(val_centers),
                "retained_by_original_case_rule": bool(
                    len(check_cases[idx]) >= 2 or len(val_cases[idx]) >= 2
                ),
                "retained_by_two_distinct_centers": bool(
                    len(check_centers) >= 2 or len(val_centers) >= 2
                ),
                "retained_by_three_distinct_centers": bool(
                    len(check_centers) >= 3 or len(val_centers) >= 3
                ),
            }
        )
    out = os.path.join(out_dir, "architecture_retention_distinct_center_audit.csv")
    _write_csv(out, rows)
    return out


def generate_representative_case(project_root: str, out_dir: str) -> Optional[str]:
    ours_path = os.path.join(
        project_root,
        "outputs", "main_evaluation_eval_d2904_t2904", "methods", "ours_c32_locked.json",
    )
    pt_path = os.path.join(
        project_root,
        "outputs", "main_evaluation_eval_d2904_t2904", "methods", "pt_ft.json",
    )
    if not (os.path.isfile(ours_path) and os.path.isfile(pt_path)):
        return None
    ours = _read_json(ours_path).get("records", {})
    pt = _read_json(pt_path).get("records", {})
    candidates: List[Tuple[float, str, Mapping[str, Any]]] = []
    for key, rec in ours.items():
        selector = rec.get("selector", {})
        if not bool(selector.get("switched_from_pt_anchor")):
            continue
        ref_val = float(selector["anchor_validation_mse"])
        alt_val = float(selector["best_alternative_validation_mse"])
        val_gain = (ref_val - alt_val) / (abs(ref_val) + CFG.eps)
        candidates.append((float(val_gain), str(key), rec))
    if not candidates:
        return None
    median_gain = float(np.median([x[0] for x in candidates]))
    val_gain, key, rec = min(candidates, key=lambda x: abs(x[0] - median_gain))
    pt_rec = pt[key]
    test_mse = float(rec["test"]["weighted_mse"])
    ref_test_mse = float(pt_rec["test"]["weighted_mse"])
    row = {
        "selection_rule": "alternative-selected case with validation gain closest to median",
        "case_key": key,
        "center_id": int(rec["center_id"]),
        "center_type": str(rec["center_type"]),
        "budget_tier": str(rec["budget_tier"]),
        "H": int(rec["H"]),
        "K": int(rec["K"]),
        "feasible_candidates": int(rec["candidate_count"]),
        "selected_arch_idx": int(rec["arch_idx"]),
        "selected_arch_key": str(rec["arch_key"]),
        "selected_parameters": float(rec["params"]),
        "selected_estimated_operations": float(rec["flops"]),
        "reference_validation_mse": float(rec["selector"]["anchor_validation_mse"]),
        "selected_validation_mse": float(rec["selector"]["best_alternative_validation_mse"]),
        "validation_relative_gain": float(val_gain),
        "required_margin": float(rec["selector"]["margin_rel"]),
        "reference_test_mse": ref_test_mse,
        "selected_test_mse": test_mse,
        "test_relative_reduction": float((ref_test_mse - test_mse) / (abs(ref_test_mse) + CFG.eps)),
    }
    out = os.path.join(out_dir, "representative_dt_instantiation_case.csv")
    _write_csv(out, [row])
    return out


def generate_hosting_report(hosting_json: str, out_dir: str) -> Optional[Dict[str, str]]:
    if not os.path.isfile(hosting_json):
        return None
    obj = _read_json(hosting_json)
    records = pd.DataFrame(obj.get("records", []))
    if records.empty:
        return None
    out_csv = os.path.join(out_dir, "hosting_profile_summary.csv")
    records.drop(columns=["repeat_rows"], errors="ignore").to_csv(
        out_csv, index=False, encoding="utf-8-sig"
    )
    corr_rows: List[Dict[str, Any]] = []
    for (host_label, device, H), group in records.groupby(["host_label", "actual_device", "H"]):
        corr_rows.append(
            {
                "host_label": host_label,
                "actual_device": device,
                "H": int(H),
                "spearman_operations_latency": float(
                    group["estimated_operations"].corr(group["median_ms"], method="spearman")
                ),
                "spearman_parameters_state_size": float(
                    group["parameters"].corr(group["serialized_state_bytes"], method="spearman")
                ),
                "spearman_parameters_peak_memory": (
                    float(group["parameters"].corr(group["peak_device_memory_bytes"], method="spearman"))
                    if group["peak_device_memory_bytes"].notna().sum() >= 3
                    else None
                ),
            }
        )
    corr_csv = os.path.join(out_dir, "hosting_profile_correlations.csv")
    _write_csv(corr_csv, corr_rows)
    return {"summary": out_csv, "correlations": corr_csv}


def generate_alibaba_domain_report(domain_json: str, out_dir: str) -> Optional[Dict[str, str]]:
    if not os.path.isfile(domain_json):
        return None
    obj = _read_json(domain_json)
    grid_path = os.path.join(out_dir, "alibaba_domain_threshold_calibration.csv")
    _write_csv(grid_path, obj.get("calibration_grid", []))
    summary_rows = []
    for name, row in obj.get("target_summaries", {}).items():
        summary_rows.append({"setting": name, **row})
    summary_path = os.path.join(out_dir, "alibaba_domain_heldout_summary.csv")
    _write_csv(summary_path, summary_rows)
    return {"calibration": grid_path, "heldout": summary_path}


def generate_all(project_root: str, output_root: str) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    out = os.path.abspath(output_root)
    os.makedirs(out, exist_ok=True)
    result: Dict[str, Any] = {
        "study": "pre_submission_audits_and_reporting",
        "decision": "IN_PROGRESS",
        "protocol": config_dict(),
        "artifacts": {},
    }
    result["artifacts"]["constraint_activity"] = generate_constraint_activity(out)
    result["artifacts"]["safety"] = generate_safety_table(root, out)
    result["artifacts"]["fig10_pareto"] = generate_pareto_figure(root, out)
    result["artifacts"]["retention_center_audit"] = generate_distinct_center_retention_audit(root, out)
    result["artifacts"]["representative_case"] = generate_representative_case(root, out)

    hosting_json = os.path.join(root, CFG.output_root, "hosting", "hosting_profile.json")
    domain_json = os.path.join(root, CFG.output_root, "alibaba_domain", "alibaba_domain_result.json")
    result["artifacts"]["hosting"] = generate_hosting_report(hosting_json, out)
    result["artifacts"]["alibaba_domain"] = generate_alibaba_domain_report(domain_json, out)
    result["decision"] = "PASS_PRE_SUBMISSION_REPORTS_GENERATED"
    atomic_json(result, os.path.join(out, "pre_submission_report_manifest.json"))
    return result
