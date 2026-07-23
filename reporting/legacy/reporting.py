# -*- coding: utf-8 -*-
"""Legacy pre-v1.1.9 reporting implementation.

Retained only to audit archived workflows. It is not a formal paper-figure
entry point and must not be used to replace v1.1.9 assets.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np

EPS = 1e-12
ARCH_LABELS = {
    1: "A1 (MLP-L2)",
    6: "A6 (MLP-L3)",
    13: "A13 (MLP-L4)",
    55: "A55 (GRU-H16)",
    56: "A56 (GRU-H32)",
    57: "PT-A57",
}
METHOD_ORDER = [
    "Ours",
    "PT+FT",
    "MeDeT-style",
    "Meta+NAS-lite",
    "Zero-NAS+FT",
    "Scratch50",
    "Zero-NAS",
]
HATCHES = {57: "", 55: "//", 56: "\\", 6: "..", 13: "xx", 1: "oo"}


def _configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif"],
            "font.size": 8.5,
            "axes.titlesize": 9.0,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.5,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.linewidth": 0.8,
        }
    )


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out: List[Dict[str, Any]] = []
    for row in rows:
        converted: Dict[str, Any] = {}
        for k, v in row.items():
            if v is None:
                converted[k] = v
                continue
            s = v.strip()
            if s == "":
                converted[k] = ""
                continue
            try:
                converted[k] = int(s)
                continue
            except Exception:
                pass
            try:
                converted[k] = float(s)
                continue
            except Exception:
                pass
            converted[k] = s
        out.append(converted)
    return out


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _ensure(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _save_figure(fig: plt.Figure, path: Path) -> None:
    _ensure(path.parent)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.03)
    fig.savefig(path.with_suffix(".png"), dpi=600, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def _mean(values: Iterable[float]) -> float:
    vals = [float(x) for x in values]
    return float(np.mean(vals)) if vals else float("nan")


def _rel_gain(selected: float, anchor: float) -> float:
    return (float(anchor) - float(selected)) / (abs(float(anchor)) + EPS)


def _cluster_bootstrap(
    values_by_center: Mapping[Any, Sequence[float]], seed: int, repeats: int = 4000
) -> Dict[str, float]:
    centers = sorted(values_by_center, key=str)
    center_means = np.asarray(
        [np.mean([float(x) for x in values_by_center[c]]) for c in centers], dtype=float
    )
    if center_means.size == 0:
        return {"mean": float("nan"), "ci_low": float("nan"), "ci_high": float("nan")}
    rng = np.random.default_rng(seed)
    draws = np.empty(repeats, dtype=float)
    n = len(center_means)
    for i in range(repeats):
        idx = rng.integers(0, n, size=n)
        draws[i] = float(np.mean(center_means[idx]))
    return {
        "mean": float(np.mean(center_means)),
        "ci_low": float(np.quantile(draws, 0.025)),
        "ci_high": float(np.quantile(draws, 0.975)),
    }


def _fmt(x: Any, digits: int = 4) -> str:
    if x is None or x == "":
        return "--"
    if isinstance(x, str):
        return x
    if isinstance(x, (bool, np.bool_)):
        return "Yes" if bool(x) else "No"
    try:
        v = float(x)
    except Exception:
        return str(x)
    if math.isnan(v):
        return "--"
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:.{digits}f}"


def _pct(x: Any, digits: int = 2) -> str:
    if x is None or x == "":
        return "--"
    try:
        v = float(x)
    except Exception:
        return str(x)
    if math.isnan(v):
        return "--"
    return f"{100.0 * v:.{digits}f}"


def _latex_escape(s: Any) -> str:
    text = str(s)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    return text


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"No rows for {path}")
    _ensure(path.parent)
    fields: List[str] = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _write_latex_table(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[Tuple[str, str]],
    caption: str,
    label: str,
    wide: bool = False,
    align: str | None = None,
    notes: Sequence[str] | None = None,
) -> None:
    _ensure(path.parent)
    env = "table*" if wide else "table"
    if align is None:
        align = "l" + "c" * (len(columns) - 1)
    lines = [
        f"\\begin{{{env}}}[t]",
        "\\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        "\\small",
        f"\\begin{{tabular}}{{{align}}}",
        "\\toprule",
        " & ".join(_latex_escape(h) for _, h in columns) + r" \\",
        "\\midrule",
    ]
    for row in rows:
        vals = [_latex_escape(row.get(key, "--")) for key, _ in columns]
        lines.append(" & ".join(vals) + r" \\")
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    if notes:
        lines.append("\\begin{minipage}{0.98\\linewidth}\\footnotesize")
        for note in notes:
            lines.append(_latex_escape(note) + r"\\")
        lines.append("\\end{minipage}")
    lines.append(f"\\end{{{env}}}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _paths(root: Path) -> Dict[str, Path]:
    return {
        "ours": root / "outputs/main_evaluation_eval_d2904_t2904/methods/ours_c32_locked.json",
        "pt": root / "outputs/main_evaluation_eval_d2904_t2904/methods/pt_ft.json",
        "main_csv": root / "outputs/experiments.main_d2904_t2904/report/tables/table_main_results.csv",
        "ablation": root / "outputs/experiments.main_d2904_t2904/ablation/ablation_candidates.json",
        "selector": root / "outputs/anchor_safe_selector_d2904_t2904/selector/anchor_safe_selector_manifest.json",
        "c32_final": root / "outputs/anchor_safe_selector_d2904_t2904/final/c32_final_candidates.json",
        "scale": root / "outputs/experiments.robustness_d2904_t2904/source_scale_controlled/controlled_source_scale_eval.json",
        "seed": root / "outputs/experiments.robustness_d2904_t2904/source_seed/source_seed_eval.json",
        "real": root / "outputs/experiments.robustness_d2904_t2904/real_diagnostics/real_candidate_diagnostics.json",
        "coverage": root / "outputs/experiments.robustness_d2904_t2904/architecture_coverage/architecture_coverage.json",
    }


def _validate_inputs(paths: Mapping[str, Path]) -> None:
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required experiment inputs:\n" + "\n".join(missing))
    decisions = {
        "ours": "C33_LOCKED_METHOD_COMPLETE",
        "pt": "C33_LOCKED_METHOD_COMPLETE",
        "ablation": "PASS_FINAL_ABLATION_RESOURCE_BANK_ORACLE",
        "selector": "PASS_C32_SELECTOR_FROZEN",
        "c32_final": "C32_FINAL_CANDIDATES_COMPLETE",
        "scale": "PASS_CONTROLLED_SOURCE_SCALE_EVAL",
        "seed": "PASS_SOURCE_SEED_ROBUSTNESS_EVAL",
        "real": "PASS_REAL_CANDIDATE_DIAGNOSTICS",
        "coverage": "PASS_ARCHITECTURE_COVERAGE_ANALYSIS",
    }
    for key, expected in decisions.items():
        obj = _load_json(paths[key])
        actual = obj.get("decision")
        if actual != expected:
            raise RuntimeError(f"{key}: expected {expected}, got {actual}")


def _main_records(ours_obj: Mapping[str, Any], pt_obj: Mapping[str, Any]):
    return ours_obj["records"], pt_obj["records"]


def _main_rows(main_csv: Path) -> List[Dict[str, Any]]:
    rows = _read_csv(main_csv)
    by = {str(r["Method"]): r for r in rows}
    out = []
    for name in METHOD_ORDER:
        if name not in by:
            continue
        r = by[name]
        out.append(
            {
                "Method": name,
                "MAE": _fmt(r["MAE"], 5),
                "WMSE": _fmt(r["WMSE"], 6),
                "Worst-10%": _fmt(r["Worst10"], 6),
                "CVaR90": _fmt(r["CVaR90_WMSE"], 6),
                "FR (%)": _fmt(100 * float(r["FeasibleRate"]), 1),
                "Online (s)": _fmt(r["OnlineSeconds"], 3),
            }
        )
    return out


def _fairness_rows() -> List[Dict[str, Any]]:
    return [
        {"Method": "PT+FT", "Structure": "Fixed A57", "Source knowledge": "Pooled pretraining", "Target update": "SGD/MSE-50", "Candidates": "1", "Hard feasibility": "Checked"},
        {"Method": "MeDeT-style", "Structure": "Fixed A57", "Source knowledge": "Meta initialization", "Target update": "SGD/MSE-50", "Candidates": "1", "Hard feasibility": "Checked"},
        {"Method": "Scratch50", "Structure": "Fixed A57", "Source knowledge": "Random initialization", "Target update": "SGD/MSE-50", "Candidates": "1", "Hard feasibility": "Checked"},
        {"Method": "Meta+NAS-lite", "Structure": "Proxy Top-12", "Source knowledge": "Legacy C1 bank", "Target update": "Adam/Huber-50", "Candidates": "≤12", "Hard feasibility": "Before search"},
        {"Method": "Zero-NAS", "Structure": "Proxy Top-1", "Source knowledge": "Legacy C1 prior", "Target update": "None", "Candidates": "0", "Hard feasibility": "Before search"},
        {"Method": "Zero-NAS+FT", "Structure": "Proxy Top-12", "Source knowledge": "Legacy C1 bank", "Target update": "Adam/Huber-50", "Candidates": "≤12", "Hard feasibility": "Before search"},
        {"Method": "Ours", "Structure": "Frozen six-architecture bank", "Source knowledge": "Strong indexed priors + PT-A57", "Target update": "SGD/MSE-50", "Candidates": "≤7", "Hard feasibility": "Before adaptation and output"},
    ]


def _configuration_rows(ours_obj: Mapping[str, Any]) -> List[Dict[str, Any]]:
    p = ours_obj["protocol"]
    return [
        {"Category": "Data", "Item": "Main source centers", "Setting": str(p["source_centers"])},
        {"Category": "Data", "Item": "Locked target centers", "Setting": "20 (centers 980–999)"},
        {"Category": "Data", "Item": "Main paired cases", "Setting": "80"},
        {"Category": "Target", "Item": "Prediction horizons", "Setting": "H ∈ {1, 4}"},
        {"Category": "Target", "Item": "Support sizes", "Setting": "K ∈ {10, 20}"},
        {"Category": "Model", "Item": "Offline architecture space", "Setting": str(p["architecture_count"])},
        {"Category": "Model", "Item": "Frozen compact architectures", "Setting": "A1, A6, A13, A55, A56, A57"},
        {"Category": "Adaptation", "Item": "Target update", "Setting": "SGD/MSE, 50 steps"},
        {"Category": "Adaptation", "Item": "Learning rate / clipping", "Setting": f"{p['fixed_target_lr']} / {p['fixed_target_grad_clip']}"},
        {"Category": "Selection", "Item": "Safety anchor", "Setting": "PT-A57"},
        {"Category": "Selection", "Item": "Frozen switch margin", "Setting": "10% validation improvement"},
        {"Category": "Statistics", "Item": "Uncertainty estimation", "Setting": "Center-cluster bootstrap, 4,000 repeats"},
        {"Category": "Protocol", "Item": "Test usage", "Setting": "Opened only after final model selection"},
    ]


def _paired_stats(ours: Mapping[str, Any], pt: Mapping[str, Any], metric: str, seed: int) -> Dict[str, Any]:
    by_center: Dict[int, List[float]] = defaultdict(list)
    for key in sorted(set(ours) & set(pt)):
        ro, rp = ours[key], pt[key]
        by_center[int(ro["center_id"])].append(
            _rel_gain(ro["test"][metric], rp["test"][metric])
        )
    return _cluster_bootstrap(by_center, seed)


def _robustness_rows(ours: Mapping[str, Any], pt: Mapping[str, Any]) -> List[Dict[str, Any]]:
    specs = [
        ("H/K", lambda r: f"H={r['H']}, K={r['K']}"),
        ("Budget", lambda r: str(r["budget_tier"]).capitalize()),
        ("Center type", lambda r: str(r["center_type"])),
    ]
    out: List[Dict[str, Any]] = []
    for i, (category, labeller) in enumerate(specs):
        groups: Dict[str, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))
        for key in sorted(set(ours) & set(pt)):
            ro, rp = ours[key], pt[key]
            label = labeller(ro)
            groups[label][int(ro["center_id"])].append(
                _rel_gain(ro["test"]["weighted_mse"], rp["test"]["weighted_mse"])
            )
        for j, (label, by_center) in enumerate(sorted(groups.items())):
            stat = _cluster_bootstrap(by_center, 2904 + 100 * i + j)
            n_cases = sum(len(v) for v in by_center.values())
            out.append(
                {
                    "Category": category,
                    "Group": label,
                    "WMSEGain": stat["mean"],
                    "CI_low": stat["ci_low"],
                    "CI_high": stat["ci_high"],
                    "N_cases": n_cases,
                    "N_centers": len(by_center),
                }
            )
    return out


def _ablation_rows(ablation_obj: Mapping[str, Any]) -> List[Dict[str, Any]]:
    labels = [
        ("full_method", "Full method"),
        ("legacy_source_bank", "Legacy prior bank"),
        ("pt_a57_only", "PT-A57 only"),
        ("dual_init_a57", "Dual-initialization A57"),
        ("without_anchor_protection", "Without anchor protection"),
        ("without_hard_feasibility", "Without hard-feasibility filtering"),
    ]
    records = list(ablation_obj["records"].values())
    pt = [r["variants"]["pt_a57_only"] for r in records]
    out = []
    for key, label in labels:
        vals = [r["variants"][key] for r in records]
        out.append(
            {
                "Variant": label,
                "MAE": _mean(x["test"]["mae"] for x in vals),
                "WMSE": _mean(x["test"]["weighted_mse"] for x in vals),
                "Worst10": _mean(x["test"]["worst10"] for x in vals),
                "GainVsPT": _mean(
                    _rel_gain(a["test"]["weighted_mse"], b["test"]["weighted_mse"])
                    for a, b in zip(vals, pt)
                ),
                "FeasibleRate": _mean(float(x["selected_hard_feasible"]) for x in vals),
            }
        )
    return out


def _mechanism_rows(
    ours: Mapping[str, Any], pt: Mapping[str, Any], main_csv: Path
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    vals = list(ours.values())
    switched = [r for r in vals if bool(r["selector"].get("switched_from_pt_anchor"))]
    beneficial = 0
    harmful = 0
    for r in switched:
        rp = pt[r["case_key"]]
        g = _rel_gain(r["test"]["weighted_mse"], rp["test"]["weighted_mse"])
        if g > 1e-6:
            beneficial += 1
        elif g < -1e-6:
            harmful += 1
    retained = len(vals) - len(switched)
    distribution = Counter(int(r["arch_idx"]) for r in vals)
    mechanism = [
        {"Measure": "Anchor retention rate", "Value": retained / len(vals)},
        {"Measure": "Non-anchor switch rate", "Value": len(switched) / len(vals)},
        {"Measure": "Beneficial switches / all cases", "Value": beneficial / len(vals)},
        {"Measure": "Harmful switches / all cases", "Value": harmful / len(vals)},
        {"Measure": "Beneficial switches / switched cases", "Value": beneficial / max(1, len(switched))},
        {"Measure": "Mean adapted candidates", "Value": _mean(r["adapted_candidate_count"] for r in vals)},
        {"Measure": "Feasible-output rate", "Value": _mean(float(r["feasible"]) for r in vals)},
        {"Measure": "Selected PT-A57 cases", "Value": distribution.get(57, 0)},
        {"Measure": "Selected A55 cases", "Value": distribution.get(55, 0)},
        {"Measure": "Selected A56 cases", "Value": distribution.get(56, 0)},
        {"Measure": "Selected A6 cases", "Value": distribution.get(6, 0)},
        {"Measure": "Selected A13 cases", "Value": distribution.get(13, 0)},
        {"Measure": "Selected A1 cases", "Value": distribution.get(1, 0)},
    ]
    main = _read_csv(main_csv)
    efficiency = []
    for r in main:
        if str(r["Method"]) not in METHOD_ORDER:
            continue
        efficiency.append(
            {
                "Method": str(r["Method"]),
                "OnlineSeconds": float(r["OnlineSeconds"]),
                "AdaptedCandidates": float(r["AdaptedCandidates"]),
                "Params": float(r["Params"]),
                "FLOPs": float(r["FLOPs"]),
                "FeasibleRate": float(r["FeasibleRate"]),
            }
        )
    return mechanism, efficiency


def _source_scale_rows(scale_obj: Mapping[str, Any]) -> List[Dict[str, Any]]:
    buckets: Dict[int, List[Mapping[str, Any]]] = defaultdict(list)
    for r in scale_obj["records"].values():
        buckets[int(r["source_scale"])].append(r)
    out = []
    for scale, vals in sorted(buckets.items()):
        by: Dict[int, List[float]] = defaultdict(list)
        for r in vals:
            by[int(r["center_id"])].append(
                _rel_gain(r["selected"]["test"]["weighted_mse"], r["anchor"]["test"]["weighted_mse"])
            )
        stat = _cluster_bootstrap(by, 3600 + scale)
        out.append(
            {
                "SourceCenters": scale,
                "OursWMSE": _mean(r["selected"]["test"]["weighted_mse"] for r in vals),
                "A57WMSE": _mean(r["anchor"]["test"]["weighted_mse"] for r in vals),
                "Gain": stat["mean"],
                "CI_low": stat["ci_low"],
                "CI_high": stat["ci_high"],
                "N": len(vals),
            }
        )
    return out


def _source_seed_rows(seed_obj: Mapping[str, Any]) -> List[Dict[str, Any]]:
    buckets: Dict[int, List[Mapping[str, Any]]] = defaultdict(list)
    for r in seed_obj["records"].values():
        buckets[int(r["source_seed"])].append(r)
    out = []
    for seed, vals in sorted(buckets.items()):
        by: Dict[int, List[float]] = defaultdict(list)
        for r in vals:
            by[int(r["center_id"])].append(
                _rel_gain(r["selected"]["test"]["weighted_mse"], r["anchor"]["test"]["weighted_mse"])
            )
        stat = _cluster_bootstrap(by, 4600 + seed)
        out.append(
            {
                "SourceSeed": seed,
                "OursWMSE": _mean(r["selected"]["test"]["weighted_mse"] for r in vals),
                "A57WMSE": _mean(r["anchor"]["test"]["weighted_mse"] for r in vals),
                "Gain": stat["mean"],
                "CI_low": stat["ci_low"],
                "CI_high": stat["ci_high"],
                "MAE": _mean(r["selected"]["test"]["mae"] for r in vals),
                "Worst10": _mean(r["selected"]["test"]["worst10"] for r in vals),
                "N": len(vals),
            }
        )
    return out


def _real_rows(real_obj: Mapping[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    vals = list(real_obj["records"].values())
    selected_gains = [
        _rel_gain(r["selected"]["test"]["weighted_mse"], r["anchor"]["test"]["weighted_mse"])
        for r in vals
    ]
    oracle_gains = [
        _rel_gain(r["test_oracle"]["test"]["weighted_mse"], r["anchor"]["test"]["weighted_mse"])
        for r in vals
    ]
    by_machine: Dict[str, List[float]] = defaultdict(list)
    for r, g in zip(vals, selected_gains):
        by_machine[str(r["machine_id_hash"])].append(g)
    ci = _cluster_bootstrap(by_machine, 5904)
    rows = [
        {
            "Method": "Ours",
            "WMSE": _mean(r["selected"]["test"]["weighted_mse"] for r in vals),
            "MAE": _mean(r["selected"]["test"]["mae"] for r in vals),
            "Worst10": _mean(r["selected"]["test"]["worst10"] for r in vals),
        },
        {
            "Method": "PT+FT",
            "WMSE": _mean(r["anchor"]["test"]["weighted_mse"] for r in vals),
            "MAE": _mean(r["anchor"]["test"]["mae"] for r in vals),
            "Worst10": _mean(r["anchor"]["test"]["worst10"] for r in vals),
        },
        {
            "Method": "Test oracle (diagnostic)",
            "WMSE": _mean(r["test_oracle"]["test"]["weighted_mse"] for r in vals),
            "MAE": _mean(r["test_oracle"]["test"]["mae"] for r in vals),
            "Worst10": _mean(r["test_oracle"]["test"]["worst10"] for r in vals),
        },
    ]
    captured = []
    for g, o in zip(selected_gains, oracle_gains):
        if o > EPS:
            captured.append(g / o)
    diag = {
        "selected_gain": float(np.mean(selected_gains)),
        "selected_ci_low": ci["ci_low"],
        "selected_ci_high": ci["ci_high"],
        "oracle_gain": float(np.mean(oracle_gains)),
        "captured_headroom": float(np.mean(captured)) if captured else float("nan"),
        "beneficial": int(sum(g > 1e-6 for g in selected_gains)),
        "harmful": int(sum(g < -1e-6 for g in selected_gains)),
        "N": len(vals),
    }
    return rows, diag


def _bank_size_rows(ablation_obj: Mapping[str, Any]) -> List[Dict[str, Any]]:
    out = []
    records = list(ablation_obj["records"].values())
    for size in range(1, 7):
        vals = [r["bank_sizes"][str(size)] for r in records]
        out.append(
            {
                "Architectures": size,
                "WMSE": _mean(x["test"]["weighted_mse"] for x in vals),
                "MAE": _mean(x["test"]["mae"] for x in vals),
                "Worst10": _mean(x["test"]["worst10"] for x in vals),
                "SwitchRate": _mean(float(x["switched"]) for x in vals),
            }
        )
    return out


def _oracle_rows(ablation_obj: Mapping[str, Any]) -> Tuple[List[Dict[str, Any]], List[float], List[float]]:
    records = list(ablation_obj["records"].values())
    full = [r["variants"]["full_method"] for r in records]
    pt = [r["variants"]["pt_a57_only"] for r in records]
    oracle = [r["oracle"] for r in records]
    regrets = [float(x["test_oracle_regret"]) for x in oracle]
    rows = [
        {"Measure": "Full method WMSE", "Value": _mean(x["test"]["weighted_mse"] for x in full)},
        {"Measure": "PT-A57 WMSE", "Value": _mean(x["test"]["weighted_mse"] for x in pt)},
        {"Measure": "Test-oracle WMSE", "Value": _mean(x["test_oracle"]["weighted_mse"] for x in oracle)},
        {"Measure": "Mean selector-to-oracle regret", "Value": _mean(regrets)},
        {"Measure": "Full matches Test oracle", "Value": _mean(float(x["full_matches_test_oracle"]) for x in oracle)},
        {"Measure": "Check matches Test oracle", "Value": _mean(float(x["check_matches_test_oracle"]) for x in oracle)},
    ]
    return rows, [x["test_oracle"]["weighted_mse"] for x in oracle], [x["test"]["weighted_mse"] for x in full]


def _coverage_rows(coverage_obj: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for r in coverage_obj["rows"]:
        if int(r["ArchIdx"]) not in (1, 13):
            continue
        if str(r["Outcome"]) not in ("test", "test_selected_only"):
            continue
        cases = int(r["Cases"])
        feasible_rate = r.get("FeasibleRate")
        feasible_cases = None
        if feasible_rate not in (None, ""):
            try:
                fv = float(feasible_rate)
                if not math.isnan(fv):
                    feasible_cases = max(1, int(round(cases * fv)))
            except Exception:
                pass
        selected = int(r.get("SelectedCount") or 0)
        beneficial = int(r.get("SelectedBeneficialCount") or 0)
        harmful = int(r.get("SelectedHarmfulCount") or 0)
        rescue = r.get("UniqueRescueCount")
        rows.append(
            {
                "Dataset": str(r["Dataset"]),
                "Architecture": f"A{int(r['ArchIdx'])}",
                "Cases": cases,
                "FeasibleCases": feasible_cases if feasible_cases is not None else "--",
                "Selected": selected,
                "Beneficial": beneficial,
                "Harmful": harmful,
                "SelectionPrecision": beneficial / selected if selected else float("nan"),
                "UniqueRescue": int(rescue) if rescue not in (None, "") and not (isinstance(rescue, float) and math.isnan(rescue)) else "--",
                "UniqueRescueRate": (float(rescue) / feasible_cases) if feasible_cases and rescue not in (None, "") else float("nan"),
            }
        )
    return rows


def _select_from_candidates(candidates: Mapping[str, Mapping[str, Any]], margin: float, outcome: str) -> Tuple[Mapping[str, Any], Mapping[str, Any], bool]:
    anchor = candidates.get("PT_A57_A57") or candidates.get("PT_A57")
    if anchor is None:
        raise KeyError("PT anchor not found")
    alternatives = [c for k, c in candidates.items() if c is not anchor]
    best = min(alternatives, key=lambda x: float(x["validation"]["weighted_mse"])) if alternatives else anchor
    switched = float(best["validation"]["weighted_mse"]) <= float(anchor["validation"]["weighted_mse"]) * (1.0 - margin)
    selected = best if switched else anchor
    return selected, anchor, switched


def _safety_rows(
    selector_obj: Mapping[str, Any],
    c32_final_obj: Mapping[str, Any],
    ours: Mapping[str, Any],
    pt: Mapping[str, Any],
    ablation_obj: Mapping[str, Any],
    real_obj: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    out = []
    selected_margin = float(selector_obj["selected_margin_rel"])
    dev = selector_obj["margin_grid_results"][f"{selected_margin:.6f}"]
    out.append({"Pool": "Selector development", "Outcome": "Check", "Cases": 80, "SwitchRate": dev["switch_rate"], "HarmfulRate": dev["harmful_switch_rate_all_cases"], "Role": "Calibration"})

    harmful = switched = 0
    for r in c32_final_obj["records"].values():
        selected, anchor, sw = _select_from_candidates(r["candidates"], selected_margin, "check")
        if sw:
            switched += 1
            if float(selected["check"]["weighted_mse"]) > float(anchor["check"]["weighted_mse"]) * (1.0 + 1e-6):
                harmful += 1
    n = len(c32_final_obj["records"])
    out.append({"Pool": "C3-2 independent final", "Outcome": "Check", "Cases": n, "SwitchRate": switched / n, "HarmfulRate": harmful / n, "Role": "Independent selector validation"})

    switched = harmful = 0
    for k, r in ours.items():
        if bool(r["selector"].get("switched_from_pt_anchor")):
            switched += 1
            if float(r["test"]["weighted_mse"]) > float(pt[k]["test"]["weighted_mse"]) * (1.0 + 1e-6):
                harmful += 1
    n = len(ours)
    out.append({"Pool": "C3-3 locked comparison", "Outcome": "Test", "Cases": n, "SwitchRate": switched / n, "HarmfulRate": harmful / n, "Role": "Primary locked evaluation"})

    full = [r["variants"]["full_method"] for r in ablation_obj["records"].values()]
    ptv = [r["variants"]["pt_a57_only"] for r in ablation_obj["records"].values()]
    switched = sum(bool(x.get("switched")) for x in full)
    harmful = sum(bool(a.get("switched")) and float(a["test"]["weighted_mse"]) > float(b["test"]["weighted_mse"]) * (1.0 + 1e-6) for a, b in zip(full, ptv))
    n = len(full)
    out.append({"Pool": "Additional ablation pool", "Outcome": "Test", "Cases": n, "SwitchRate": switched / n, "HarmfulRate": harmful / n, "Role": "Post-freeze stress analysis"})

    switched = harmful = 0
    for r in real_obj["records"].values():
        if bool(r["selection"].get("switched")):
            switched += 1
            if float(r["selected"]["test"]["weighted_mse"]) > float(r["anchor"]["test"]["weighted_mse"]) * (1.0 + 1e-6):
                harmful += 1
    n = len(real_obj["records"])
    out.append({"Pool": "Alibaba semi-real", "Outcome": "Test", "Cases": n, "SwitchRate": switched / n, "HarmfulRate": harmful / n, "Role": "External distribution analysis"})
    return out


def _write_main_tables(
    out: Path,
    config_rows: List[Dict[str, Any]],
    fairness_rows: List[Dict[str, Any]],
    main_rows: List[Dict[str, Any]],
    ablation_rows: List[Dict[str, Any]],
    mechanism: List[Dict[str, Any]],
    efficiency: List[Dict[str, Any]],
    seed_rows: List[Dict[str, Any]],
    real_rows: List[Dict[str, Any]],
    real_diag: Mapping[str, Any],
) -> None:
    csvdir = out / "main/tables/csv"
    texdir = out / "main/tables/latex"
    _write_csv(csvdir / "table1_experimental_configuration.csv", config_rows)
    _write_csv(csvdir / "table2_baseline_fairness.csv", fairness_rows)
    _write_csv(csvdir / "table3_overall_comparison.csv", main_rows)

    ab_fmt = [
        {
            "Variant": r["Variant"],
            "MAE": _fmt(r["MAE"], 5),
            "WMSE": _fmt(r["WMSE"], 6),
            "Worst-10%": _fmt(r["Worst10"], 6),
            "Gain vs PT (%)": _pct(r["GainVsPT"], 2),
            "FR (%)": _fmt(100 * r["FeasibleRate"], 1),
        }
        for r in ablation_rows
    ]
    _write_csv(csvdir / "table4_component_ablation.csv", ab_fmt)

    mech_fmt = []
    for r in mechanism:
        name = r["Measure"]
        v = r["Value"]
        if "rate" in name.lower() or "switches /" in name.lower():
            text = _pct(v, 2)
        elif "candidates" in name.lower():
            text = _fmt(v, 2)
        else:
            text = _fmt(v, 0)
        mech_fmt.append({"Measure": name, "Value": text})
    eff_fmt = [
        {
            "Method": r["Method"],
            "Online (s)": _fmt(r["OnlineSeconds"], 3),
            "Candidates": _fmt(r["AdaptedCandidates"], 2),
            "Params": _fmt(r["Params"], 0),
            "FLOPs": _fmt(r["FLOPs"], 0),
            "FR (%)": _fmt(100 * r["FeasibleRate"], 1),
        }
        for r in efficiency
    ]
    _write_csv(csvdir / "table5a_selection_mechanism.csv", mech_fmt)
    _write_csv(csvdir / "table5b_online_cost.csv", eff_fmt)

    gen_rows = []
    for r in seed_rows:
        gen_rows.append(
            {
                "Study": "Source-bank seed",
                "Setting": str(r["SourceSeed"]),
                "Ours WMSE": _fmt(r["OursWMSE"], 6),
                "Reference WMSE": _fmt(r["A57WMSE"], 6),
                "Gain (%)": _pct(r["Gain"], 2),
                "95% CI (%)": f"[{_pct(r['CI_low'], 2)}, {_pct(r['CI_high'], 2)}]",
            }
        )
    gen_rows.append(
        {
            "Study": "Alibaba semi-real",
            "Setting": "20 target machines / 80 cases",
            "Ours WMSE": _fmt(real_rows[0]["WMSE"], 6),
            "Reference WMSE": _fmt(real_rows[1]["WMSE"], 6),
            "Gain (%)": _pct(real_diag["selected_gain"], 2),
            "95% CI (%)": f"[{_pct(real_diag['selected_ci_low'], 2)}, {_pct(real_diag['selected_ci_high'], 2)}]",
        }
    )
    _write_csv(csvdir / "table6_generalization.csv", gen_rows)

    _write_latex_table(
        texdir / "table1_experimental_configuration.tex",
        config_rows,
        [("Category", "Category"), ("Item", "Item"), ("Setting", "Setting")],
        "Frozen experimental configuration.",
        "tab:configuration",
        wide=False,
        align="lll",
    )
    _write_latex_table(
        texdir / "table2_baseline_fairness.tex",
        fairness_rows,
        [("Method", "Method"), ("Structure", "Structure choice"), ("Source knowledge", "Source knowledge"), ("Target update", "Target update"), ("Candidates", "Candidates"), ("Hard feasibility", "Hard feasibility")],
        "Compared methods and fairness settings.",
        "tab:fairness",
        wide=True,
        align="llllcl",
        notes=["Ours and PT+FT use the same PT-A57 anchor and the same SGD/MSE-50 target-update protocol."],
    )
    _write_latex_table(
        texdir / "table3_overall_comparison.tex",
        main_rows,
        [("Method", "Method"), ("MAE", "MAE"), ("WMSE", "WMSE"), ("Worst-10%", "W10"), ("CVaR90", "CVaR90"), ("FR (%)", "FR"), ("Online (s)", "Time (s)")],
        "Overall comparison under the locked evaluation protocol.",
        "tab:overall",
        wide=True,
        align="lcccccc",
    )
    _write_latex_table(
        texdir / "table4_component_ablation.tex",
        ab_fmt,
        [("Variant", "Variant"), ("MAE", "MAE"), ("WMSE", "WMSE"), ("Worst-10%", "W10"), ("Gain vs PT (%)", "Gain"), ("FR (%)", "FR")],
        "Ablation of the main method components.",
        "tab:ablation",
        wide=True,
        align="lccccc",
        notes=["The no-feasibility variant is diagnostic only; its lower error is accompanied by infeasible outputs."],
    )
    _write_latex_table(
        texdir / "table5a_selection_mechanism.tex",
        mech_fmt,
        [("Measure", "Measure"), ("Value", "Value")],
        "Selection behavior of the frozen method on the locked test pool.",
        "tab:mechanism",
        wide=False,
        align="lc",
    )
    _write_latex_table(
        texdir / "table5b_online_cost.tex",
        eff_fmt,
        [("Method", "Method"), ("Online (s)", "Time (s)"), ("Candidates", "Candidates"), ("Params", "Params"), ("FLOPs", "FLOPs"), ("FR (%)", "FR")],
        "Target-side computation and deployment characteristics.",
        "tab:cost",
        wide=True,
        align="lccccc",
    )
    _write_latex_table(
        texdir / "table6_generalization.tex",
        gen_rows,
        [("Study", "Study"), ("Setting", "Setting"), ("Ours WMSE", "Ours"), ("Reference WMSE", "Reference"), ("Gain (%)", "Gain"), ("95% CI (%)", "95% CI")],
        "Additional generalization evidence across source-bank seeds and semi-real workload traces.",
        "tab:generalization",
        wide=True,
        align="llcccc",
        notes=["The Alibaba result is an external semi-real analysis; its confidence interval overlaps zero and is not used as the primary superiority claim."],
    )


def _write_supp_tables(
    out: Path,
    robustness: List[Dict[str, Any]],
    scale_rows: List[Dict[str, Any]],
    seed_rows: List[Dict[str, Any]],
    bank_rows: List[Dict[str, Any]],
    oracle_rows: List[Dict[str, Any]],
    real_rows: List[Dict[str, Any]],
    real_diag: Mapping[str, Any],
    coverage_rows: List[Dict[str, Any]],
    safety_rows: List[Dict[str, Any]],
) -> None:
    csvdir = out / "supplement/tables/csv"
    texdir = out / "supplement/tables/latex"
    rob_fmt = [
        {
            "Category": r["Category"],
            "Group": r["Group"],
            "Gain (%)": _pct(r["WMSEGain"], 2),
            "95% CI (%)": f"[{_pct(r['CI_low'],2)}, {_pct(r['CI_high'],2)}]",
            "Cases": r["N_cases"],
            "Centers": r["N_centers"],
        }
        for r in robustness
    ]
    scale_fmt = [
        {
            "Source centers": r["SourceCenters"],
            "Ours WMSE": _fmt(r["OursWMSE"], 6),
            "A57 WMSE": _fmt(r["A57WMSE"], 6),
            "Gain (%)": _pct(r["Gain"], 2),
            "95% CI (%)": f"[{_pct(r['CI_low'],2)}, {_pct(r['CI_high'],2)}]",
        }
        for r in scale_rows
    ]
    seed_fmt = [
        {
            "Source seed": r["SourceSeed"],
            "Ours WMSE": _fmt(r["OursWMSE"], 6),
            "A57 WMSE": _fmt(r["A57WMSE"], 6),
            "Gain (%)": _pct(r["Gain"], 2),
            "95% CI (%)": f"[{_pct(r['CI_low'],2)}, {_pct(r['CI_high'],2)}]",
        }
        for r in seed_rows
    ]
    bank_fmt = [
        {
            "Architectures": r["Architectures"],
            "WMSE": _fmt(r["WMSE"], 6),
            "MAE": _fmt(r["MAE"], 5),
            "W10": _fmt(r["Worst10"], 6),
            "Switch rate (%)": _pct(r["SwitchRate"], 2),
        }
        for r in bank_rows
    ]
    oracle_fmt = [
        {"Measure": r["Measure"], "Value": _pct(r["Value"], 2) if "regret" in r["Measure"].lower() or "matches" in r["Measure"].lower() else _fmt(r["Value"], 6)}
        for r in oracle_rows
    ]
    real_fmt = [
        {"Method": r["Method"], "WMSE": _fmt(r["WMSE"], 6), "MAE": _fmt(r["MAE"], 5), "W10": _fmt(r["Worst10"], 6)}
        for r in real_rows
    ]
    real_fmt.extend(
        [
            {"Method": "Selected gain vs PT", "WMSE": _pct(real_diag["selected_gain"], 2) + "%", "MAE": "--", "W10": "--"},
            {"Method": "Oracle gain vs PT", "WMSE": _pct(real_diag["oracle_gain"], 2) + "%", "MAE": "--", "W10": "--"},
            {"Method": "Captured oracle headroom", "WMSE": _pct(real_diag["captured_headroom"], 2) + "%", "MAE": "--", "W10": "--"},
        ]
    )
    coverage_fmt = []
    for r in coverage_rows:
        coverage_fmt.append(
            {
                "Dataset": r["Dataset"],
                "Arch": r["Architecture"],
                "Selected": r["Selected"],
                "Beneficial": r["Beneficial"],
                "Harmful": r["Harmful"],
                "Selection precision (%)": _pct(r["SelectionPrecision"], 2),
                "Unique rescue": r["UniqueRescue"],
                "Unique rescue rate (%)": _pct(r["UniqueRescueRate"], 2),
            }
        )
    safety_fmt = [
        {
            "Pool": r["Pool"],
            "Outcome": r["Outcome"],
            "Cases": r["Cases"],
            "Switch rate (%)": _pct(r["SwitchRate"], 2),
            "Harmful rate (%)": _pct(r["HarmfulRate"], 2),
            "Role": r["Role"],
        }
        for r in safety_rows
    ]
    maps = {
        "tableS1_robustness_details.csv": rob_fmt,
        "tableS2_controlled_source_scale.csv": scale_fmt,
        "tableS3_source_bank_seed.csv": seed_fmt,
        "tableS4_bank_size.csv": bank_fmt,
        "tableS5_oracle_diagnostics.csv": oracle_fmt,
        "tableS6_alibaba_semi_real.csv": real_fmt,
        "tableS7_architecture_coverage.csv": coverage_fmt,
        "tableS8_safety_across_pools.csv": safety_fmt,
    }
    for name, rows in maps.items():
        _write_csv(csvdir / name, rows)

    specs = [
        ("tableS1_robustness_details.tex", rob_fmt, [("Category","Category"),("Group","Group"),("Gain (%)","Gain"),("95% CI (%)","95% CI"),("Cases","Cases"),("Centers","Centers")], "Detailed robustness results.", "tab:supp_robustness"),
        ("tableS2_controlled_source_scale.tex", scale_fmt, [("Source centers","Sources"),("Ours WMSE","Ours"),("A57 WMSE","A57"),("Gain (%)","Gain"),("95% CI (%)","95% CI")], "Compute-matched source-scale study.", "tab:supp_scale"),
        ("tableS3_source_bank_seed.tex", seed_fmt, [("Source seed","Seed"),("Ours WMSE","Ours"),("A57 WMSE","A57"),("Gain (%)","Gain"),("95% CI (%)","95% CI")], "Source-bank training-seed robustness.", "tab:supp_seed"),
        ("tableS4_bank_size.tex", bank_fmt, [("Architectures","Architectures"),("WMSE","WMSE"),("MAE","MAE"),("W10","W10"),("Switch rate (%)","Switch rate")], "Compact-bank size analysis.", "tab:supp_bank"),
        ("tableS5_oracle_diagnostics.tex", oracle_fmt, [("Measure","Measure"),("Value","Value")], "Oracle diagnostics on the additional evaluation pool.", "tab:supp_oracle"),
        ("tableS6_alibaba_semi_real.tex", real_fmt, [("Method","Method / measure"),("WMSE","WMSE"),("MAE","MAE"),("W10","W10")], "Semi-real Alibaba workload results and oracle headroom.", "tab:supp_alibaba"),
        ("tableS7_architecture_coverage.tex", coverage_fmt, [("Dataset","Dataset"),("Arch","Arch."),("Selected","Selected"),("Beneficial","Beneficial"),("Harmful","Harmful"),("Selection precision (%)","Precision"),("Unique rescue","Rescue"),("Unique rescue rate (%)","Rescue rate")], "Coverage contribution of the two low-frequency MLP candidates.", "tab:supp_coverage"),
        ("tableS8_safety_across_pools.tex", safety_fmt, [("Pool","Pool"),("Outcome","Outcome"),("Cases","Cases"),("Switch rate (%)","Switch rate"),("Harmful rate (%)","Harmful rate"),("Role","Role")], "Observed selector safety across development, locked, stress, and semi-real pools.", "tab:supp_safety"),
    ]
    for name, rows, cols, caption, label in specs:
        _write_latex_table(texdir / name, rows, cols, caption, label, wide=True, align="llcccc" if len(cols)==6 else None)


def _plot_main_figures(
    out: Path,
    ours: Mapping[str, Any],
    pt: Mapping[str, Any],
    robustness: List[Dict[str, Any]],
    main_csv: Path,
    selector_obj: Mapping[str, Any],
) -> None:
    fdir = out / "main/figures"
    common = sorted(set(ours) & set(pt))

    # Fig. 6: paired comparison with mechanism-grounded classification.
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.15))
    categories = {
        "Beneficial switch": [],
        "Anchor-equivalent": [],
        "Harmful switch": [],
    }
    for key in common:
        r = ours[key]
        if not bool(r["selector"].get("switched_from_pt_anchor")):
            categories["Anchor-equivalent"].append(key)
        else:
            gain = _rel_gain(r["test"]["weighted_mse"], pt[key]["test"]["weighted_mse"])
            categories["Beneficial switch" if gain > 1e-6 else "Harmful switch"].append(key)
    for ax, metric, title in zip(axes, ("weighted_mse", "worst10"), ("WMSE", "Worst-10%")):
        all_x = np.asarray([pt[k]["test"][metric] for k in common], dtype=float)
        all_y = np.asarray([ours[k]["test"][metric] for k in common], dtype=float)
        for label, keys in categories.items():
            if not keys:
                continue
            x = [pt[k]["test"][metric] for k in keys]
            y = [ours[k]["test"][metric] for k in keys]
            marker = {"Beneficial switch": "o", "Anchor-equivalent": "x", "Harmful switch": "^"}[label]
            ax.scatter(x, y, s=23, marker=marker, alpha=0.78, label=label)
        lo, hi = min(all_x.min(), all_y.min()), max(all_x.max(), all_y.max())
        ax.plot([lo, hi], [lo, hi], linestyle="--", linewidth=0.9)
        ax.set_xlabel("PT+FT")
        ax.set_ylabel("Ours")
        ax.set_title(f"({chr(97 + list(axes).index(ax))}) {title}")
        ax.ticklabel_format(axis="both", style="sci", scilimits=(-2, 2))
    axes[0].legend(frameon=False, loc="best")
    fig.text(0.5, -0.02, "44 beneficial switches, 33 anchor-equivalent cases, and 3 harmful switches", ha="center")
    fig.tight_layout()
    _save_figure(fig, fdir / "fig6_paired_ours_vs_pt.pdf")

    # Fig. 7: robustness with center-cluster CIs.
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.65))
    for ax, category, title in zip(axes, ["H/K", "Budget", "Center type"], ["(a) Horizon and support", "(b) Deployment budget", "(c) Center type"]):
        rows = [r for r in robustness if r["Category"] == category]
        x = np.arange(len(rows))
        y = np.asarray([100 * r["WMSEGain"] for r in rows])
        lo = np.asarray([100 * (r["WMSEGain"] - r["CI_low"]) for r in rows])
        hi = np.asarray([100 * (r["CI_high"] - r["WMSEGain"]) for r in rows])
        ax.bar(x, y, yerr=np.vstack([lo, hi]), capsize=2.5)
        ax.axhline(0, linewidth=0.8, linestyle="--", color="gray")
        ax.set_xticks(x)
        ax.set_xticklabels([r["Group"] for r in rows], rotation=22 if category == "H/K" else 0, ha="right" if category == "H/K" else "center")
        ax.set_title(title)
        if ax is axes[0]:
            ax.set_ylabel("WMSE reduction relative to PT+FT (%)")
    fig.tight_layout()
    _save_figure(fig, fdir / "fig7_heterogeneous_robustness.pdf")

    # Fig. 8: budget changes feasible candidates and selected architecture shares.
    budgets = ["tight", "medium", "loose"]
    budget_records = {b: [r for r in ours.values() if r["budget_tier"] == b] for b in budgets}
    budget_tick_labels = [f"{b} (n={len(budget_records[b])})" for b in budgets]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.15))
    means = [_mean(r["adapted_candidate_count"] for r in budget_records[b]) for b in budgets]
    axes[0].bar(np.arange(len(budgets)), means)
    axes[0].set_xticks(np.arange(len(budgets)))
    axes[0].set_xticklabels(budget_tick_labels)
    axes[0].set_ylabel("Adapted initialized candidates per case")
    axes[0].set_title("(a) Candidate adaptation load")
    axes[0].set_ylim(0, max(means) + 1.35)
    for i, m in enumerate(means):
        axes[0].text(i, m + 0.14, f"{m:.2f}", ha="center", va="bottom", fontsize=7)
    arch_order = [57, 55, 56, 6, 13, 1]
    bottom = np.zeros(len(budgets), dtype=float)
    for arch in arch_order:
        vals = []
        for b in budgets:
            rs = budget_records[b]
            vals.append(sum(int(r["arch_idx"]) == arch for r in rs) / max(1, len(rs)))
        axes[1].bar(np.arange(len(budgets)), vals, bottom=bottom, label=ARCH_LABELS[arch], hatch=HATCHES.get(arch, ""), edgecolor="black", linewidth=0.4)
        bottom += np.asarray(vals)
    axes[1].set_xticks(np.arange(len(budgets)))
    axes[1].set_xticklabels(budget_tick_labels)
    axes[1].set_ylim(0, 1)
    axes[1].set_ylabel("Selection proportion")
    axes[1].set_title("(b) Target-specific architecture selection")
    axes[1].legend(frameon=False, ncol=2, fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, -0.20))
    fig.subplots_adjust(bottom=0.31, wspace=0.30)
    _save_figure(fig, fdir / "fig8_budget_architecture_behavior.pdf")

    # Fig. 9: accuracy-cost tradeoff, log x-axis.
    rows = _read_csv(main_csv)
    fig, ax = plt.subplots(figsize=(4.9, 3.35))
    label_offsets = {
        "Ours": (6, -3),
        "PT+FT": (6, 4),
        "MeDeT-style": (6, 4),
        "Scratch50": (6, 4),
        "Zero-NAS": (6, 4),
        "Meta+NAS-lite": (-88, 5),
        "Zero-NAS+FT": (6, 5),
    }
    for r in rows:
        method = str(r["Method"])
        xval, yval = float(r["OnlineSeconds"]), float(r["WMSE"])
        ax.scatter(xval, yval, s=54)
        ax.annotate(method, (xval, yval), xytext=label_offsets.get(method, (4, 4)), textcoords="offset points", fontsize=7)
    ax.set_xscale("log")
    ax.set_xlabel("Mean target-side online time (s, log scale)")
    ax.set_ylabel("Test WMSE")
    ax.set_title("Accuracy–online cost tradeoff")
    ax.margins(x=0.10, y=0.08)
    fig.tight_layout()
    _save_figure(fig, fdir / "fig9_accuracy_online_cost.pdf")

    # Fig. 10: margin calibration, separated panels.
    grid = [selector_obj["margin_grid_results"][k] for k in sorted(selector_obj["margin_grid_results"], key=float)]
    margins = np.asarray([100 * float(x["margin_rel"]) for x in grid])
    gain = np.asarray([100 * float(x["primary_gain_over_PT"]["mean"]) for x in grid])
    gain_lo = np.asarray([100 * float(x["primary_gain_over_PT"]["ci_low"]) for x in grid])
    gain_hi = np.asarray([100 * float(x["primary_gain_over_PT"]["ci_high"]) for x in grid])
    harmful = np.asarray([100 * float(x["harmful_switch_rate_all_cases"]) for x in grid])
    switch = np.asarray([100 * float(x["switch_rate"]) for x in grid])
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8))
    axes[0].errorbar(margins, gain, yerr=np.vstack([gain - gain_lo, gain_hi - gain]), marker="o", capsize=2.5)
    axes[0].axvline(10, linestyle="--", linewidth=0.9)
    axes[0].set_xticks([5, 7.5, 10, 12.5, 15, 20])
    axes[0].set_xticklabels(["5", "7.5", "10", "12.5", "15", "20"])
    axes[0].set_xlabel("Anchor margin (%)")
    axes[0].set_ylabel("WMSE reduction relative to PT+FT (%)")
    axes[0].set_title("(a) Predictive gain")
    axes[1].plot(margins, harmful, marker="s", label="Harmful-switch rate")
    axes[1].plot(margins, switch, marker="o", linestyle="--", label="Switch rate")
    axes[1].axvline(10, linestyle="--", linewidth=0.9)
    axes[1].axhline(5, linestyle=":", linewidth=0.9, color="gray")
    axes[1].annotate("Registered safety limit", xy=(20, 5), xytext=(-2, 4), textcoords="offset points", fontsize=6.8, ha="right")
    axes[1].set_xticks([5, 7.5, 10, 12.5, 15, 20])
    axes[1].set_xticklabels(["5", "7.5", "10", "12.5", "15", "20"])
    axes[1].set_xlabel("Anchor margin (%)")
    axes[1].set_ylabel("Rate (%)")
    axes[1].set_title("(b) Safety–coverage tradeoff")
    axes[1].legend(frameon=False)
    fig.tight_layout()
    _save_figure(fig, fdir / "fig10_margin_safety.pdf")


def _plot_supp_figures(
    out: Path,
    scale_rows: List[Dict[str, Any]],
    seed_rows: List[Dict[str, Any]],
    bank_rows: List[Dict[str, Any]],
    oracle_mse: List[float],
    full_mse: List[float],
    ablation_obj: Mapping[str, Any],
    real_obj: Mapping[str, Any],
    coverage_rows: List[Dict[str, Any]],
) -> None:
    fdir = out / "supplement/figures"

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.95))
    x = [r["SourceCenters"] for r in scale_rows]
    axes[0].plot(x, [r["OursWMSE"] for r in scale_rows], marker="o", label="Ours")
    axes[0].plot(x, [r["A57WMSE"] for r in scale_rows], marker="s", label="Scale-matched A57")
    axes[0].set_xlabel("Source centers")
    axes[0].set_ylabel("Test WMSE")
    axes[0].set_title("(a) Compute-matched performance")
    axes[0].legend(frameon=False)
    axes[0].text(0.03, 0.04, "Same initialization; 2,000 source updates per asset", transform=axes[0].transAxes, fontsize=6.6)
    y = np.asarray([100 * r["Gain"] for r in scale_rows])
    lo = np.asarray([100 * (r["Gain"] - r["CI_low"]) for r in scale_rows])
    hi = np.asarray([100 * (r["CI_high"] - r["Gain"]) for r in scale_rows])
    axes[1].errorbar(x, y, yerr=np.vstack([lo, hi]), marker="o", capsize=2.5)
    axes[1].axhline(0, linewidth=0.8, linestyle="--", color="gray")
    axes[1].set_xlabel("Source centers")
    axes[1].set_ylabel("WMSE reduction relative to A57 (%)")
    axes[1].set_title("(b) Relative gain with 95% CI")
    fig.tight_layout()
    _save_figure(fig, fdir / "figS1_controlled_source_scale.pdf")

    fig, ax = plt.subplots(figsize=(4.8, 3.1))
    x = np.arange(len(seed_rows))
    y = np.asarray([100 * r["Gain"] for r in seed_rows])
    lo = np.asarray([100 * (r["Gain"] - r["CI_low"]) for r in seed_rows])
    hi = np.asarray([100 * (r["CI_high"] - r["Gain"]) for r in seed_rows])
    ax.bar(x, y, yerr=np.vstack([lo, hi]), capsize=3)
    ax.axhline(0, linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([str(r["SourceSeed"]) for r in seed_rows])
    ax.set_xlabel("Source-bank training seed")
    ax.set_ylabel("WMSE gain vs same-seed A57 (%)")
    ax.set_title("Source-bank training-seed robustness")
    fig.tight_layout()
    _save_figure(fig, fdir / "figS2_source_bank_seed_robustness.pdf")

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8))
    axes[0].plot([r["Architectures"] for r in bank_rows], [r["WMSE"] for r in bank_rows], marker="o")
    axes[0].set_xlabel("Unique architectures in compact bank")
    axes[0].set_ylabel("Test WMSE")
    axes[0].set_title("(a) Prediction quality")
    axes[1].plot([r["Architectures"] for r in bank_rows], [100 * r["SwitchRate"] for r in bank_rows], marker="s")
    axes[1].set_xlabel("Unique architectures in compact bank")
    axes[1].set_ylabel("Switch rate (%)")
    axes[1].set_title("(b) Selection coverage")
    fig.tight_layout()
    _save_figure(fig, fdir / "figS3_bank_size_saturation.pdf")

    records = list(ablation_obj["records"].values())
    regrets = np.asarray([100 * float(r["oracle"]["test_oracle_regret"]) for r in records])
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    axes[0].scatter(oracle_mse, full_mse, s=20, alpha=0.75)
    lo0, hi0 = min(min(oracle_mse), min(full_mse)), max(max(oracle_mse), max(full_mse))
    axes[0].plot([lo0, hi0], [lo0, hi0], linestyle="--", linewidth=0.9)
    axes[0].set_xlabel("Test-oracle WMSE")
    axes[0].set_ylabel("Full-method WMSE")
    axes[0].set_title("(a) Selector versus oracle")
    sorted_r = np.sort(regrets)
    axes[1].plot(sorted_r, np.arange(1, len(sorted_r) + 1) / len(sorted_r))
    axes[1].set_xlabel("Selector-to-oracle regret (%)")
    axes[1].set_ylabel("Empirical CDF")
    axes[1].set_title("(b) Oracle-regret distribution")
    fig.tight_layout()
    _save_figure(fig, fdir / "figS4_oracle_diagnostics.pdf")

    vals = list(real_obj["records"].values())
    selected_gain = np.asarray([100 * _rel_gain(r["selected"]["test"]["weighted_mse"], r["anchor"]["test"]["weighted_mse"]) for r in vals])
    oracle_gain = np.asarray([100 * _rel_gain(r["test_oracle"]["test"]["weighted_mse"], r["anchor"]["test"]["weighted_mse"]) for r in vals])
    order = np.argsort(oracle_gain)[::-1]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.95))
    axes[0].scatter(oracle_gain, selected_gain, s=22, alpha=0.75)
    lo, hi = min(oracle_gain.min(), selected_gain.min()), max(oracle_gain.max(), selected_gain.max())
    axes[0].plot([lo, hi], [lo, hi], linestyle="--", linewidth=0.9)
    axes[0].axhline(0, linewidth=0.8, color="gray")
    axes[0].axvline(0, linewidth=0.8, color="gray")
    axes[0].set_xscale("symlog", linthresh=5)
    axes[0].set_yscale("symlog", linthresh=5)
    axes[0].set_xlabel("Test-oracle WMSE reduction relative to A57 (%)")
    axes[0].set_ylabel("Selected WMSE reduction relative to A57 (%)")
    axes[0].set_title("(a) Selected versus oracle gain")
    axes[1].plot(np.arange(1, len(order) + 1), oracle_gain[order], label="Test oracle", linewidth=1.1)
    axes[1].plot(np.arange(1, len(order) + 1), selected_gain[order], label="Selected", linewidth=1.1)
    axes[1].axhline(0, linewidth=0.8, color="gray")
    axes[1].set_xlabel("Cases ranked by oracle gain")
    axes[1].set_ylabel("WMSE reduction relative to A57 (%)")
    axes[1].set_title("(b) Semi-real gain by case rank")
    axes[1].legend(frameon=False)
    fig.tight_layout()
    _save_figure(fig, fdir / "figS5_alibaba_oracle_headroom.pdf")

    datasets = []
    for r in coverage_rows:
        if r["UniqueRescue"] == "--":
            continue
        label = r["Dataset"].replace("ControlledScale1040-1059", "Controlled scale").replace("SourceSeed1060-1079", "Source seed").replace("AblationPool1000-1019", "Ablation").replace("AlibabaSemiReal", "Alibaba")
        datasets.append((label, r))
    unique_labels = []
    for label, _ in datasets:
        if label not in unique_labels:
            unique_labels.append(label)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1))
    width = 0.34
    x = np.arange(len(unique_labels))
    for j, arch in enumerate(["A1", "A13"]):
        rescue = []
        precision = []
        for label in unique_labels:
            match = next((r for l, r in datasets if l == label and r["Architecture"] == arch), None)
            rescue.append(100 * float(match["UniqueRescueRate"]) if match and not math.isnan(float(match["UniqueRescueRate"])) else 0.0)
            precision.append(100 * float(match["SelectionPrecision"]) if match and not math.isnan(float(match["SelectionPrecision"])) else 0.0)
        axes[0].bar(x + (j - 0.5) * width, rescue, width=width, label=arch)
        axes[1].bar(x + (j - 0.5) * width, precision, width=width, label=arch)
    for ax, title, ylabel in zip(axes, ["(a) Unique leave-one-out rescue", "(b) Precision when selected"], ["Rescue rate among feasible cases (%)", "Beneficial selections (%)"]):
        ax.set_xticks(x)
        ax.set_xticklabels(unique_labels, rotation=20, ha="right")
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.legend(frameon=False)
    fig.tight_layout()
    _save_figure(fig, fdir / "figS6_a1_a13_coverage.pdf")


def _write_captions(out: Path) -> None:
    text = r"""# JNCA实验图建议标题与用途

## 正文图

- **Fig. 6.** Paired case-level comparison between Ours and PT+FT on the locked test pool. The point categories follow the actual selector decision rather than floating-point equality.
- **Fig. 7.** WMSE reductions relative to PT+FT under different prediction horizons, support sizes, deployment budgets, and center types. Error bars denote center-cluster 95% bootstrap confidence intervals.
- **Fig. 8.** Effect of deployment budgets on adapted initialized candidates and target-specific architecture selection.
- **Fig. 9.** Accuracy–online cost tradeoff. The horizontal axis uses a logarithmic scale, and all markers have the same size.
- **Fig. 10.** Development-calibrated basis of the frozen 10% anchor margin. The threshold controls empirical switching risk but is not a worst-case guarantee.

## 补充材料图

- **Fig. S1.** Compute-matched and initialization-controlled source-scale analysis.
- **Fig. S2.** Robustness to source-bank training seeds.
- **Fig. S3.** Compact-bank size saturation.
- **Fig. S4.** Selector-to-oracle diagnostic analysis.
- **Fig. S5.** Selected-versus-oracle gain diagnostics on the Alibaba semi-real workload traces.
- **Fig. S6.** Conditional coverage contribution of A1 and A13.
"""
    (out / "JNCA_FIGURE_CAPTIONS.md").write_text(text, encoding="utf-8")


def _write_layout(out: Path) -> None:
    text = r"""# JNCA论文实验编排建议

## 正文必须保留

1. Table 1：冻结实验配置。
2. Table 2：基线与公平性。
3. Table 3：总体性能和可行率。
4. Fig. 6：Ours与最强基线PT+FT的配对散点。
5. Fig. 7：H/K、预算和中心类型鲁棒性。
6. Table 4：组件消融，包含来源Bank、结构选择、锚点保护与硬可行性。
7. Fig. 8：预算如何改变候选数量和最终架构选择。
8. Table 5：选择行为与在线计算代价。
9. Fig. 9：精度—在线成本权衡。
10. Fig. 10：10% margin的开发校准依据。
11. Table 6：来源Bank随机种子与Alibaba半真实泛化。

## 建议放补充材料

- 公平控制的来源规模分析；
- 候选Bank规模饱和；
- Oracle上限与selector regret；
- Alibaba候选Oracle headroom；
- A1/A13的leave-one-out rescue；
- 不同数据池的harmful-switch观测值。

## 论文主张边界

- 主优势主张来自锁定的980–999测试池：相对PT+FT，WMSE、MAE和Worst-10%分别改善14.60%、8.55%和13.76%。
- 10% margin是开发校准的风险控制阈值，不是形式化最坏情况保证。
- Alibaba是半真实外部分布验证。平均结果略优，但WMSE置信区间跨零，因此不进入摘要和Highlights。
- 来源Bank三seed可作为真正的训练随机性稳健性证据；旧目标侧三seed结果不再使用。
- A1与A13应表述为条件性、非冗余的补充覆盖，不应表述为所有场景都稳定获益。
"""
    (out / "JNCA_EXPERIMENT_LAYOUT_CN.md").write_text(text, encoding="utf-8")


def generate(project_root: str, output_root: str) -> Dict[str, Any]:
    _configure_matplotlib()
    root = Path(project_root).resolve()
    out = Path(output_root).resolve()
    _ensure(out)
    paths = _paths(root)
    _validate_inputs(paths)

    ours_obj = _load_json(paths["ours"])
    pt_obj = _load_json(paths["pt"])
    ablation_obj = _load_json(paths["ablation"])
    selector_obj = _load_json(paths["selector"])
    c32_final_obj = _load_json(paths["c32_final"])
    scale_obj = _load_json(paths["scale"])
    seed_obj = _load_json(paths["seed"])
    real_obj = _load_json(paths["real"])
    coverage_obj = _load_json(paths["coverage"])
    ours, pt = _main_records(ours_obj, pt_obj)

    config_rows = _configuration_rows(ours_obj)
    fairness_rows = _fairness_rows()
    main_rows = _main_rows(paths["main_csv"])
    robustness = _robustness_rows(ours, pt)
    ablation_rows = _ablation_rows(ablation_obj)
    mechanism, efficiency = _mechanism_rows(ours, pt, paths["main_csv"])
    scale_rows = _source_scale_rows(scale_obj)
    seed_rows = _source_seed_rows(seed_obj)
    real_rows, real_diag = _real_rows(real_obj)
    bank_rows = _bank_size_rows(ablation_obj)
    oracle_rows, oracle_mse, full_mse = _oracle_rows(ablation_obj)
    coverage_rows = _coverage_rows(coverage_obj)
    safety_rows = _safety_rows(selector_obj, c32_final_obj, ours, pt, ablation_obj, real_obj)

    _write_main_tables(out, config_rows, fairness_rows, main_rows, ablation_rows, mechanism, efficiency, seed_rows, real_rows, real_diag)
    _write_supp_tables(out, robustness, scale_rows, seed_rows, bank_rows, oracle_rows, real_rows, real_diag, coverage_rows, safety_rows)
    _plot_main_figures(out, ours, pt, robustness, paths["main_csv"], selector_obj)
    _plot_supp_figures(out, scale_rows, seed_rows, bank_rows, oracle_mse, full_mse, ablation_obj, real_obj, coverage_rows)
    _write_captions(out)
    _write_layout(out)

    paired = {
        "WMSE": _paired_stats(ours, pt, "weighted_mse", 7101),
        "MAE": _paired_stats(ours, pt, "mae", 7102),
        "Worst10": _paired_stats(ours, pt, "worst10", 7103),
    }
    manifest = {
        "study": "jnca_final_paper_reporting",
        "decision": "PASS_JNCA_FINAL_TABLES_AND_FIGURES",
        "method_retuning_allowed": False,
        "main_figures": sorted(str(p.relative_to(out)) for p in (out / "main/figures").glob("*.pdf")),
        "supplement_figures": sorted(str(p.relative_to(out)) for p in (out / "supplement/figures").glob("*.pdf")),
        "main_tables": sorted(str(p.relative_to(out)) for p in (out / "main/tables/latex").glob("*.tex")),
        "supplement_tables": sorted(str(p.relative_to(out)) for p in (out / "supplement/tables/latex").glob("*.tex")),
        "paired_ours_vs_pt": paired,
        "input_sha256": {k: _sha256(v) for k, v in paths.items()},
    }
    (out / "jnca_report_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
