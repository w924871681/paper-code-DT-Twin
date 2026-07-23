# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
import math
import os
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np

from configs.methods.main_experiments_cfg import CFG, config_dict
from shared.evaluation.common import atomic_json, file_sha256, load_json
from .pipeline import _center_bootstrap, _mean, _rel_gain


METHOD_LABELS = {
    "ours_c32_locked": "Ours",
    "pt_ft": "PT+FT",
    "medet_style": "MeDeT-style",
    "scratch50": "Scratch50",
    "meta_nas_lite": "Meta+NAS-lite",
    "zero_nas": "Zero-NAS",
    "zero_nas_ft": "Zero-NAS+FT",
}


def _write_csv(path: str, rows: Sequence[Mapping[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        raise ValueError(f"No rows for {path}")
    fields: List[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _save_figure(fig, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    png = os.path.splitext(path)[0] + ".png"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _method_records(root: str) -> Dict[str, Dict[str, Any]]:
    out = {}
    for method in METHOD_LABELS:
        p = os.path.join(root, CFG.c33_root, "methods", f"{method}.json")
        obj = load_json(p)
        if not obj.get("complete"):
            raise RuntimeError(f"Incomplete C3-3 method {method}")
        out[method] = obj["records"]
    return out


def _overall_table(methods: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for method, mapping in methods.items():
        vals = list(mapping.values())
        rows.append(
            {
                "Method": METHOD_LABELS[method],
                "MAE": _mean(r["test"]["mae"] for r in vals),
                "WMSE": _mean(r["test"]["weighted_mse"] for r in vals),
                "Worst10": _mean(r["test"]["worst10"] for r in vals),
                "CVaR90_WMSE": float(
                    np.mean(
                        sorted(float(r["test"]["weighted_mse"]) for r in vals)[
                            -max(1, int(math.ceil(0.1 * len(vals)))) :
                        ]
                    )
                ),
                "FeasibleRate": _mean(float(r.get("feasible", True)) for r in vals),
                "OnlineSeconds": _mean(float(r.get("online_seconds", 0.0)) for r in vals),
                "Params": _mean(float(r.get("params", 0.0)) for r in vals),
                "FLOPs": _mean(float(r.get("flops", 0.0)) for r in vals),
                "AdaptedCandidates": _mean(float(r.get("adapted_candidate_count", 0)) for r in vals),
            }
        )
    return rows


def _paired_summary(
    ours: Mapping[str, Any], base: Mapping[str, Any], metric: str, seed: int
) -> Dict[str, Any]:
    by_center: Dict[int, List[float]] = defaultdict(list)
    win = tie = loss = 0
    tol = 1e-6
    for key in sorted(set(ours) & set(base)):
        ro, rb = ours[key], base[key]
        a = float(ro["test"][metric])
        b = float(rb["test"][metric])
        by_center[int(ro["center_id"])].append(_rel_gain(a, b))
        rel = (b - a) / (abs(b) + CFG.eps)
        if rel > tol:
            win += 1
        elif rel < -tol:
            loss += 1
        else:
            tie += 1
    stat = _center_bootstrap(by_center, seed)
    return {**stat, "wins": win, "ties": tie, "losses": loss, "N": win + tie + loss}


def _group_robustness(
    ours: Mapping[str, Any], pt: Mapping[str, Any], field: str
) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[float]] = defaultdict(list)
    for key in sorted(set(ours) & set(pt)):
        ro, rp = ours[key], pt[key]
        if field == "HK":
            label = f"H={ro['H']},K={ro['K']}"
        else:
            label = str(ro[field])
        buckets[label].append(
            _rel_gain(ro["test"]["weighted_mse"], rp["test"]["weighted_mse"])
        )
    return [
        {"Group": k, "WMSEGainVsPT": float(np.mean(v)), "N": len(v)}
        for k, v in sorted(buckets.items())
    ]


def _ablation_tables(ablation: Mapping[str, Any]):
    records = ablation["records"]
    variants = [
        "full_method",
        "legacy_source_bank",
        "pt_a57_only",
        "dual_init_a57",
        "without_anchor_protection",
        "without_hard_feasibility",
    ]
    rows = []
    for v in variants:
        selected = [r["variants"][v] for r in records.values()]
        pt = [r["variants"]["pt_a57_only"] for r in records.values()]
        harmful = sum(
            1
            for a, b in zip(selected, pt)
            if bool(a.get("switched"))
            and float(a["test"]["weighted_mse"])
            > float(b["test"]["weighted_mse"]) * (1.0 + 1e-6)
        )
        rows.append(
            {
                "Variant": v,
                "MAE": _mean(x["test"]["mae"] for x in selected),
                "WMSE": _mean(x["test"]["weighted_mse"] for x in selected),
                "Worst10": _mean(x["test"]["worst10"] for x in selected),
                "WMSEGainVsPT": _mean(
                    _rel_gain(a["test"]["weighted_mse"], b["test"]["weighted_mse"])
                    for a, b in zip(selected, pt)
                ),
                "HarmfulSwitchRate": harmful / max(1, len(selected)),
                "FeasibleOutputRate": _mean(
                    float(x["selected_hard_feasible"]) for x in selected
                ),
            }
        )
    resource = [r for r in rows if r["Variant"] in ("full_method", "without_hard_feasibility")]
    return rows, resource


def _bank_size_table(ablation: Mapping[str, Any]) -> List[Dict[str, Any]]:
    records = ablation["records"]
    rows = []
    for size in CFG.bank_sizes:
        sels = [r["bank_sizes"][str(size)] for r in records.values()]
        rows.append(
            {
                "UniqueArchitectures": int(size),
                "WMSE": _mean(x["test"]["weighted_mse"] for x in sels),
                "MAE": _mean(x["test"]["mae"] for x in sels),
                "Worst10": _mean(x["test"]["worst10"] for x in sels),
                "SwitchRate": _mean(float(x["switched"]) for x in sels),
            }
        )
    return rows


def _oracle_table(ablation: Mapping[str, Any]) -> List[Dict[str, Any]]:
    records = list(ablation["records"].values())
    full = [r["variants"]["full_method"] for r in records]
    pt = [r["variants"]["pt_a57_only"] for r in records]
    oracle = [r["oracle"] for r in records]
    return [
        {
            "Measure": "Full method WMSE",
            "Value": _mean(x["test"]["weighted_mse"] for x in full),
        },
        {
            "Measure": "PT-A57 WMSE",
            "Value": _mean(x["test"]["weighted_mse"] for x in pt),
        },
        {
            "Measure": "Test oracle WMSE",
            "Value": _mean(x["test_oracle"]["weighted_mse"] for x in oracle),
        },
        {
            "Measure": "Full/Test-oracle regret",
            "Value": _mean(x["test_oracle_regret"] for x in oracle),
        },
        {
            "Measure": "Full matches Test oracle",
            "Value": _mean(float(x["full_matches_test_oracle"]) for x in oracle),
        },
        {
            "Measure": "Check matches Test oracle",
            "Value": _mean(float(x["check_matches_test_oracle"]) for x in oracle),
        },
    ]


def _seed_table(seed_obj: Mapping[str, Any]) -> List[Dict[str, Any]]:
    buckets: Dict[int, List[Mapping[str, Any]]] = defaultdict(list)
    for r in seed_obj["records"].values():
        buckets[int(r["target_seed"])].append(r)
    rows = []
    for seed, vals in sorted(buckets.items()):
        gains = [
            _rel_gain(x["ours"]["test"]["weighted_mse"], x["pt_ft"]["test"]["weighted_mse"])
            for x in vals
        ]
        rows.append(
            {
                "TargetSeed": seed,
                "OursWMSE": _mean(x["ours"]["test"]["weighted_mse"] for x in vals),
                "PTWMSE": _mean(x["pt_ft"]["test"]["weighted_mse"] for x in vals),
                "WMSEGainVsPT": float(np.mean(gains)),
                "OursMAE": _mean(x["ours"]["test"]["mae"] for x in vals),
                "OursWorst10": _mean(x["ours"]["test"]["worst10"] for x in vals),
            }
        )
    if rows:
        rows.append(
            {
                "TargetSeed": "mean±std",
                "OursWMSE": f"{np.mean([r['OursWMSE'] for r in rows]):.8f}±{np.std([r['OursWMSE'] for r in rows], ddof=1):.8f}",
                "PTWMSE": f"{np.mean([r['PTWMSE'] for r in rows]):.8f}±{np.std([r['PTWMSE'] for r in rows], ddof=1):.8f}",
                "WMSEGainVsPT": f"{np.mean([r['WMSEGainVsPT'] for r in rows]):.8f}±{np.std([r['WMSEGainVsPT'] for r in rows], ddof=1):.8f}",
            }
        )
    return rows


def _scale_table(scale_obj: Mapping[str, Any]) -> List[Dict[str, Any]]:
    buckets: Dict[int, List[Mapping[str, Any]]] = defaultdict(list)
    for r in scale_obj["records"].values():
        buckets[int(r["source_scale"])].append(r)
    return [
        {
            "SourceCenters": scale,
            "OursWMSE": _mean(x["ours"]["test"]["weighted_mse"] for x in vals),
            "A57WMSE": _mean(x["a57"]["test"]["weighted_mse"] for x in vals),
            "WMSEGainVsA57": _mean(
                _rel_gain(x["ours"]["test"]["weighted_mse"], x["a57"]["test"]["weighted_mse"])
                for x in vals
            ),
            "OursWorst10": _mean(x["ours"]["test"]["worst10"] for x in vals),
        }
        for scale, vals in sorted(buckets.items())
    ]


def _real_table(real_obj: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for method in ("ours", "pt_ft", "scratch50"):
        vals = [r[method]["test"] for r in real_obj["records"].values()]
        rows.append(
            {
                "Method": {"ours": "Ours", "pt_ft": "PT+FT", "scratch50": "Scratch50"}[method],
                "WMSE": _mean(x["weighted_mse"] for x in vals),
                "MAE": _mean(x["mae"] for x in vals),
                "Worst10": _mean(x["worst10"] for x in vals),
                "N": len(vals),
            }
        )
    return rows


def _mechanism_cost(methods: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for method, mapping in methods.items():
        vals = list(mapping.values())
        row = {
            "Method": METHOD_LABELS[method],
            "OnlineSeconds": _mean(float(r.get("online_seconds", 0.0)) for r in vals),
            "AdaptedCandidates": _mean(float(r.get("adapted_candidate_count", 0)) for r in vals),
            "MaxStepsPerCandidate": max(int(r.get("max_online_gradient_steps_per_candidate", 0)) for r in vals),
            "Params": _mean(float(r.get("params", 0.0)) for r in vals),
            "FLOPs": _mean(float(r.get("flops", 0.0)) for r in vals),
            "FeasibleRate": _mean(float(r.get("feasible", True)) for r in vals),
        }
        if method == "ours_c32_locked":
            tokens = Counter(str(r["selector"].get("selected_token", "PT_A57")) for r in vals)
            switched = [r for r in vals if bool(r["selector"].get("switched_from_pt_anchor"))]
            pt_map = methods["pt_ft"]
            harmful = sum(
                1
                for r in switched
                if float(r["test"]["weighted_mse"])
                > float(pt_map[r["case_key"]]["test"]["weighted_mse"]) * (1.0 + 1e-6)
            )
            row.update(
                {
                    "AnchorRetentionRate": sum(1 for r in vals if not bool(r["selector"].get("switched_from_pt_anchor"))) / len(vals),
                    "SwitchRate": len(switched) / len(vals),
                    "HarmfulSwitchRate": harmful / len(vals),
                    "SelectedArchitectureDistribution": json.dumps(dict(tokens), ensure_ascii=False),
                }
            )
        rows.append(row)
    return rows


def _fairness_table() -> List[Dict[str, Any]]:
    return [
        {"Method": "PT+FT", "StructureChoice": "Fixed A57", "SourceKnowledge": "Pooled source pretraining", "TargetUpdate": "SGD/MSE-50", "MaxAdaptedCandidates": 1, "HardFeasibility": "Checked"},
        {"Method": "MeDeT-style", "StructureChoice": "Fixed A57", "SourceKnowledge": "Meta initialization", "TargetUpdate": "SGD/MSE-50", "MaxAdaptedCandidates": 1, "HardFeasibility": "Checked"},
        {"Method": "Scratch50", "StructureChoice": "Fixed A57", "SourceKnowledge": "Random initialization", "TargetUpdate": "SGD/MSE-50", "MaxAdaptedCandidates": 1, "HardFeasibility": "Checked"},
        {"Method": "Meta+NAS-lite", "StructureChoice": "Proxy Top-12", "SourceKnowledge": "Legacy C1 prior bank", "TargetUpdate": "Adam/Huber-50", "MaxAdaptedCandidates": 12, "HardFeasibility": "Before search"},
        {"Method": "Zero-NAS", "StructureChoice": "Proxy Top-1", "SourceKnowledge": "Legacy C1 prior", "TargetUpdate": "None", "MaxAdaptedCandidates": 0, "HardFeasibility": "Before search"},
        {"Method": "Zero-NAS+FT", "StructureChoice": "Proxy Top-12", "SourceKnowledge": "Legacy C1 prior bank", "TargetUpdate": "Adam/Huber-50", "MaxAdaptedCandidates": 12, "HardFeasibility": "Before search"},
        {"Method": "Ours", "StructureChoice": "Frozen six-architecture compact bank", "SourceKnowledge": "Strong architecture-indexed priors + PT-A57 anchor", "TargetUpdate": "SGD/MSE-50", "MaxAdaptedCandidates": 7, "HardFeasibility": "Before adaptation and final output"},
    ]


def generate_report(project_root: str, result_root: str) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    result_root = os.path.abspath(result_root)
    report_dir = os.path.join(result_root, "report")
    tables_dir = os.path.join(report_dir, "tables")
    figures_dir = os.path.join(report_dir, "figures")
    os.makedirs(tables_dir, exist_ok=True); os.makedirs(figures_dir, exist_ok=True)

    methods = _method_records(root)
    c32 = load_json(os.path.join(root, CFG.anchor_safe_selector_path))
    ablation = load_json(os.path.join(result_root, "ablation", "ablation_candidates.json"))
    seeds = load_json(os.path.join(result_root, "seeds", "seed_robustness.json"))
    scale = load_json(os.path.join(result_root, "source_scale", "source_scale_eval.json"))
    real = load_json(os.path.join(result_root, "real_trace", "real_eval.json"))
    for name, obj, decision in (
        ("ablation", ablation, "PASS_FINAL_ABLATION_RESOURCE_BANK_ORACLE"),
        ("seeds", seeds, "PASS_FINAL_THREE_TARGET_SEEDS"),
        ("scale", scale, "PASS_FINAL_SOURCE_SCALE_EVAL"),
        ("real", real, "PASS_REAL_TRACE_EVAL"),
    ):
        if obj.get("decision") != decision:
            raise RuntimeError(f"{name} is not complete")

    main_rows = _overall_table(methods)
    ours, pt = methods["ours_c32_locked"], methods["pt_ft"]
    hk_rows = _group_robustness(ours, pt, "HK")
    budget_rows = _group_robustness(ours, pt, "budget_tier")
    type_rows = _group_robustness(ours, pt, "center_type")
    ablation_rows, resource_rows = _ablation_tables(ablation)
    seed_rows = _seed_table(seeds)
    scale_rows = _scale_table(scale)
    real_rows = _real_table(real)
    bank_rows = _bank_size_table(ablation)
    oracle_rows = _oracle_table(ablation)
    mechanism_rows = _mechanism_cost(methods)
    fairness_rows = _fairness_table()

    table_map = {
        "table_baseline_fairness.csv": fairness_rows,
        "table_main_results.csv": main_rows,
        "table_hk_robustness.csv": hk_rows,
        "table_budget_robustness.csv": budget_rows,
        "table_center_type_robustness.csv": type_rows,
        "table_ablation.csv": ablation_rows,
        "table_resource_constraint_ablation.csv": resource_rows,
        "table_seed_robustness.csv": seed_rows,
        "table_real_trace.csv": real_rows,
        "table_source_scale.csv": scale_rows,
        "table_bank_size.csv": bank_rows,
        "table_oracle_diagnostics.csv": oracle_rows,
        "table_mechanism_cost.csv": mechanism_rows,
    }
    for name, rows in table_map.items():
        _write_csv(os.path.join(tables_dir, name), rows)

    # Fig. paired Ours vs PT+FT. Anchor-retained cases are mechanism-level
    # equivalents and are not reclassified by tiny floating-point differences.
    common = sorted(set(ours) & set(pt))
    beneficial = anchor_equivalent = harmful = 0
    for k in common:
        ro = ours[k]
        if not bool(ro["selector"].get("switched_from_pt_anchor")):
            anchor_equivalent += 1
        else:
            rel = _rel_gain(ro["test"]["weighted_mse"], pt[k]["test"]["weighted_mse"])
            if rel >= -1e-6:
                beneficial += 1
            else:
                harmful += 1
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.1))
    for ax, metric, title in zip(axes, ("weighted_mse", "worst10"), ("WMSE", "Worst-10%")):
        x = np.asarray([pt[k]["test"][metric] for k in common], dtype=float)
        y = np.asarray([ours[k]["test"][metric] for k in common], dtype=float)
        ax.scatter(x, y, s=22, alpha=0.75)
        lo, hi = min(x.min(), y.min()), max(x.max(), y.max())
        ax.plot([lo, hi], [lo, hi], linestyle="--", linewidth=1)
        ax.set_xlabel("PT+FT"); ax.set_ylabel("Ours"); ax.set_title(title)
    axes[0].text(0.03, 0.97, f"{beneficial} beneficial / {anchor_equivalent} anchor-equivalent / {harmful} harmful", transform=axes[0].transAxes, va="top", fontsize=8)
    _save_figure(fig, os.path.join(figures_dir, "fig_paired_ours_vs_pt.pdf"))

    # H/K and center-type robustness.
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.8))
    for ax, rows, title in zip(axes, (hk_rows, budget_rows, type_rows), ("H/K", "Budget", "Center type")):
        ax.bar([r["Group"] for r in rows], [100 * r["WMSEGainVsPT"] for r in rows])
        ax.axhline(0, linewidth=0.8); ax.set_ylabel("WMSE gain vs PT+FT (%)"); ax.set_title(title)
        ax.tick_params(axis="x", rotation=25)
    _save_figure(fig, os.path.join(figures_dir, "fig_heterogeneous_robustness.pdf"))

    # Budget performance + architecture selection behavior.
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.1))
    axes[0].bar([r["Group"] for r in budget_rows], [100 * r["WMSEGainVsPT"] for r in budget_rows])
    axes[0].set_ylabel("WMSE gain vs PT+FT (%)"); axes[0].set_title("Prediction gain by budget")
    budget_tokens: Dict[str, Counter] = defaultdict(Counter)
    for r in ours.values(): budget_tokens[str(r["budget_tier"])][str(r["selector"].get("selected_token", "PT_A57"))] += 1
    budgets = sorted(budget_tokens); tokens = sorted(set().union(*(set(c) for c in budget_tokens.values())))
    labels = [f"{b} (n={sum(budget_tokens[b].values())})" for b in budgets]
    bottom = np.zeros(len(budgets))
    for token in tokens:
        vals = np.asarray([budget_tokens[b][token] / max(1, sum(budget_tokens[b].values())) for b in budgets], dtype=float)
        axes[1].bar(labels, vals, bottom=bottom, label=token); bottom += vals
    axes[1].set_title("Selected-candidate proportions by budget"); axes[1].set_ylabel("Proportion"); axes[1].legend(fontsize=7)
    _save_figure(fig, os.path.join(figures_dir, "fig_budget_architecture_behavior.pdf"))

    # Accuracy-online cost.
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    for row in main_rows:
        ax.scatter(row["OnlineSeconds"], row["WMSE"], s=55)
        ax.annotate(row["Method"], (row["OnlineSeconds"], row["WMSE"]), xytext=(4, 4), textcoords="offset points", fontsize=8)
    ax.set_xscale("log"); ax.set_xlabel("Mean target-side online time (s, log scale)"); ax.set_ylabel("Test WMSE"); ax.set_title("Accuracy–online cost tradeoff")
    _save_figure(fig, os.path.join(figures_dir, "fig_accuracy_online_cost.pdf"))

    # Margin safety from frozen C3-2 development results.
    grid = [c32["margin_grid_results"][k] for k in sorted(c32["margin_grid_results"], key=float)]
    fig, ax1 = plt.subplots(figsize=(6.8, 4.4)); ax2 = ax1.twinx()
    margins = [100 * x["margin_rel"] for x in grid]
    ax1.plot(margins, [100 * x["primary_gain_over_PT"]["mean"] for x in grid], marker="o", label="WMSE gain")
    ax2.plot(margins, [100 * x["harmful_switch_rate_all_cases"] for x in grid], marker="s", linestyle="--", label="Harmful switch")
    ax1.axvline(100 * CFG.frozen_margin_rel, linestyle=":", linewidth=1)
    ax1.set_xlabel("Anchor margin (%)"); ax1.set_ylabel("WMSE gain (%)"); ax2.set_ylabel("Harmful switch rate (%)"); ax1.set_title("Safety basis of the frozen 10% margin")
    _save_figure(fig, os.path.join(figures_dir, "fig_margin_safety.pdf"))

    # Source scale.
    fig, ax = plt.subplots(figsize=(6.5, 4.3))
    ax.plot([r["SourceCenters"] for r in scale_rows], [r["OursWMSE"] for r in scale_rows], marker="o", label="Ours")
    ax.plot([r["SourceCenters"] for r in scale_rows], [r["A57WMSE"] for r in scale_rows], marker="s", label="A57")
    ax.set_xlabel("Number of source centers"); ax.set_ylabel("Test WMSE"); ax.set_title("Source-center scale"); ax.legend()
    _save_figure(fig, os.path.join(figures_dir, "fig_source_scale.pdf"))

    # Bank size.
    fig, ax = plt.subplots(figsize=(6.5, 4.3))
    ax.plot([r["UniqueArchitectures"] for r in bank_rows], [r["WMSE"] for r in bank_rows], marker="o")
    ax.set_xlabel("Retained architectures"); ax.set_ylabel("Test WMSE"); ax.set_title("Retained architecture count")
    _save_figure(fig, os.path.join(figures_dir, "fig_bank_size.pdf"))

    # Oracle diagnostics.
    ab_records = list(ablation["records"].values())
    full_mse = np.asarray([r["variants"]["full_method"]["test"]["weighted_mse"] for r in ab_records])
    oracle_mse = np.asarray([r["oracle"]["test_oracle"]["weighted_mse"] for r in ab_records])
    fig, axes = plt.subplots(1, 2, figsize=(9.3, 4.1))
    axes[0].scatter(oracle_mse, full_mse, s=22, alpha=0.75); lo, hi = min(oracle_mse.min(), full_mse.min()), max(oracle_mse.max(), full_mse.max()); axes[0].plot([lo, hi], [lo, hi], linestyle="--", linewidth=1); axes[0].set_xlabel("Test oracle WMSE"); axes[0].set_ylabel("Full method WMSE"); axes[0].set_title("Selector vs oracle")
    regrets = 100 * np.asarray([r["oracle"]["test_oracle_regret"] for r in ab_records])
    axes[1].hist(regrets, bins=15); axes[1].set_xlabel("Oracle regret (%)"); axes[1].set_ylabel("Cases"); axes[1].set_title("Oracle-regret distribution")
    _save_figure(fig, os.path.join(figures_dir, "fig_oracle_diagnostics.pdf"))

    pt_paired = _paired_summary(ours, pt, "weighted_mse", CFG.train_seed + 9001)
    summary = {
        "study": "final_paper_experiment_consolidation",
        "decision": "PASS_FINAL_PAPER_TABLES_AND_FIGURES",
        "protocol": config_dict(),
        "tables": {name: os.path.join(tables_dir, name) for name in table_map},
        "figures": {name: os.path.join(figures_dir, name) for name in CFG.required_figures},
        "paired_ours_vs_pt": pt_paired,
        "source_inputs": {
            "c33_analysis": file_sha256(os.path.join(root, CFG.c33_analysis_path)),
            "anchor_safe_selector": file_sha256(os.path.join(root, CFG.anchor_safe_selector_path)),
            "ablation": file_sha256(os.path.join(result_root, "ablation", "ablation_candidates.json")),
            "seeds": file_sha256(os.path.join(result_root, "seeds", "seed_robustness.json")),
            "source_scale": file_sha256(os.path.join(result_root, "source_scale", "source_scale_eval.json")),
            "real": file_sha256(os.path.join(result_root, "real_trace", "real_eval.json")),
        },
        "method_retuning_allowed": False,
    }
    atomic_json(summary, os.path.join(report_dir, "final_report_manifest.json"))
    with open(os.path.join(report_dir, "FINAL_EXPERIMENT_INDEX_CN.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("# 最终论文实验输出索引\n\n")
        f.write("所有新增实验完成后统一生成，未在任何最终池上重新调参。\n\n")
        for name in CFG.required_tables: f.write(f"- 表：`tables/{name}`\n")
        for name in CFG.required_figures: f.write(f"- 图：`figures/{name}`（同时生成 PNG）\n")
    return summary
