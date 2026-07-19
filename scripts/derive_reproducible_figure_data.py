# -*- coding: utf-8 -*-
"""Derive the public Fig. 6/8/9/12 CSV layer from frozen experiment records.

Fig. 6 and Fig. 8 require the custodian-side locked-evaluation JSON files.
Fig. 9 is derived entirely from sources already released in this repository.
The resulting compact CSV files are versioned so plotting never requires
private paths, model weights, or a rerun of training/evaluation. Fig. 12 keeps
every anonymized case-level gain so the published distribution is auditable.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURES = (
    (57, "Reference GRU"),
    (56, "GRU (32 units, no dropout)"),
    (55, "GRU (16 units)"),
    (6, "3-layer MLP"),
    (13, "4-layer MLP"),
)
BUDGETS = ("tight", "medium", "loose")

FIG10_METHODS = (
    ("PT+FT", "pt_ft", "PT+FT"),
    ("Meta+NAS-lite", "meta_nas_lite", "Few-shot NAS"),
    ("Zero-NAS+FT", "zero_nas_ft", "Zero-shot NAS+FT"),
    ("Ours", "ours_c32_locked", "Proposed method"),
)


def _write(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    materialized = list(rows)
    if not materialized:
        raise ValueError(f"No rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(materialized[0]))
        writer.writeheader()
        writer.writerows(materialized)


def _records(path: Path) -> dict[str, dict[str, Any]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    records = obj.get("records")
    if not isinstance(records, dict) or len(records) != 80:
        raise ValueError(f"Expected 80 keyed records in {path}")
    return records


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def derive_fig6_fig8(ours_path: Path, pt_path: Path, output_dir: Path) -> None:
    ours = _records(ours_path)
    pt = _records(pt_path)
    if set(ours) != set(pt):
        raise ValueError("Locked proposed-method and PT+FT case keys differ")

    fig6 = []
    for case_key in sorted(ours):
        proposed = ours[case_key]
        reference = pt[case_key]
        switched = bool(proposed["selector"]["switched_from_pt_anchor"])
        relative_gain = (
            float(reference["test"]["weighted_mse"])
            - float(proposed["test"]["weighted_mse"])
        ) / float(reference["test"]["weighted_mse"])
        category = (
            "reference retained"
            if not switched
            else "beneficial alternative"
            if relative_gain > 1e-6
            else "harmful alternative"
        )
        fig6.append(
            {
                "case_key": case_key,
                "center_id": proposed["center_id"],
                "H": proposed["H"],
                "K": proposed["K"],
                "budget_tier": proposed["budget_tier"],
                "selection_category": category,
                "pt_ft_wmse": reference["test"]["weighted_mse"],
                "proposed_wmse": proposed["test"]["weighted_mse"],
                "pt_ft_worst10": reference["test"]["worst10"],
                "proposed_worst10": proposed["test"]["worst10"],
            }
        )
    counts = Counter(row["selection_category"] for row in fig6)
    expected = {"beneficial alternative": 44, "reference retained": 33, "harmful alternative": 3}
    if counts != expected:
        raise ValueError(f"Fig. 6 category counts changed: {dict(counts)}")
    _write(output_dir / "fig6_paired_instantiation_data.csv", fig6)

    initialized = max(int(row["adapted_candidate_count"]) for row in ours.values())
    filtering = []
    selection = []
    for tier in BUDGETS:
        tier_rows = [row for row in ours.values() if row["budget_tier"] == tier]
        n = len(tier_rows)
        filtering.append(
            {
                "budget_tier": tier,
                "case_count": n,
                "initialized_candidates_per_case": initialized,
                "feasible_candidates_per_case_mean": mean(
                    int(row["adapted_candidate_count"]) for row in tier_rows
                ),
            }
        )
        selected = Counter(int(row["arch_idx"]) for row in tier_rows)
        for order, (arch_idx, label) in enumerate(ARCHITECTURES):
            count = selected[arch_idx]
            selection.append(
                {
                    "budget_tier": tier,
                    "case_count": n,
                    "architecture_order": order,
                    "architecture_index": arch_idx,
                    "model_configuration": label,
                    "selection_count": count,
                    "selection_rate": count / n,
                }
            )
    _write(output_dir / "fig8_candidate_filtering_data.csv", filtering)
    _write(output_dir / "fig8_architecture_selection_data.csv", selection)


def derive_fig9(output_dir: Path) -> None:
    with (ROOT / "results/main/bank_size.csv").open(encoding="utf-8-sig", newline="") as handle:
        bank = list(csv.DictReader(handle))
    _write(
        output_dir / "fig9_bank_size_data.csv",
        (
            {
                "retained_architectures": row["UniqueArchitectures"],
                "diagnostic_wmse": row["WMSE"],
            }
            for row in bank
        ),
    )

    with (ROOT / "results/supplementary/adaptation_trajectory_summary.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        trajectory = list(csv.DictReader(handle))
    _write(
        output_dir / "fig9_adaptation_steps_data.csv",
        (
            {
                "adaptation_steps": row["step"],
                "selected_check_wmse_mean": row["selected_check_wmse_mean"],
                "selection_agreement_with_50": row["selector_agreement_with_50"],
            }
            for row in trajectory
        ),
    )

    manifest = json.loads(
        (ROOT / "results/audited_provenance/anchor_safe_selector_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    grid = sorted(manifest["margin_grid_results"].values(), key=lambda row: row["margin_rel"])
    _write(
        output_dir / "fig9_margin_data.csv",
        (
            {
                "minimum_improvement": row["margin_rel"],
                "alternative_selection_rate": row["switch_rate"],
                "harmful_selection_rate": row["harmful_switch_rate_all_cases"],
                "harmful_selection_count": row["harmful_switch_count"],
                "eligible_under_5pct_criterion": str(bool(row["eligible"])).lower(),
            }
            for row in grid
        ),
    )


def derive_fig7_fig10_fig11(output_dir: Path) -> None:
    with (ROOT / "results/figure_data/tableS1_robustness_details.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        robustness = list(csv.DictReader(handle))
    fig7 = []
    for row in robustness:
        if row["Category"] not in {"H/K", "Center type"}:
            continue
        low, high = (float(value.strip()) for value in row["95% CI (%)"].strip("[]").split(","))
        fig7.append(
            {
                "panel": "H/K" if row["Category"] == "H/K" else "Center type",
                "group": row["Group"],
                "gain_percent": row["Gain (%)"],
                "ci_low_percent": format(low, ".8g"),
                "ci_high_percent": format(high, ".8g"),
                "cases": row["Cases"],
                "centers": row["Centers"],
            }
        )
    _write(output_dir / "fig7_heterogeneity_data.csv", fig7)

    with (ROOT / "results/main/overall_comparison.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        overall = {row["Method"]: row for row in csv.DictReader(handle)}
    with (ROOT / "results/supplementary/repeated_runtime_summary.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        runtime = {row["method"]: row for row in csv.DictReader(handle)}
    fig10 = []
    for internal, runtime_key, public in FIG10_METHODS:
        row = overall[internal]
        fig10.append(
            {
                "method": public,
                "mse": row["WMSE"],
                "worst10": row["Worst10"],
                "cvar90": row["CVaR90_WMSE"],
                "target_time_seconds": runtime[runtime_key]["mean_seconds"],
                "parameter_count": row["Params"],
                "estimated_operation_count": row["FLOPs"],
            }
        )
    _write(output_dir / "fig10_deployment_tradeoff_data.csv", fig10)

    with (ROOT / "results/robustness/architecture_coverage.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        coverage = {
            int(row["ArchIdx"]): row
            for row in csv.DictReader(handle)
            if row["Dataset"] == "C33Locked980-999"
        }
    bank = json.loads(
        (ROOT / "results/audited_provenance/source_prior_bank_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assets = list(bank["assets"].values())
    arch_meta = (
        (6, "MLP3-32", "alternative"),
        (13, "MLP4-32", "alternative"),
        (55, "Alt GRU16", "alternative"),
        (56, "Alt GRU32", "alternative"),
        (57, "Ref GRU32", "reference"),
    )
    fig11 = []
    for arch_idx, label, role in arch_meta:
        complexity = [
            asset
            for asset in assets
            if int(asset["arch_idx"]) == arch_idx and "params" in asset and "flops" in asset
        ]
        if not complexity and arch_idx == 57:
            # The reference and alternative GRU32 differ only in dropout,
            # which does not change parameter or operation counts.
            complexity = [
                asset
                for asset in assets
                if int(asset["arch_idx"]) == 56 and "params" in asset and "flops" in asset
            ]
        if not complexity:
            raise ValueError(f"Missing architecture complexity for {arch_idx}")
        row = coverage[arch_idx]
        fig11.append(
            {
                "architecture_index": arch_idx,
                "configuration": label,
                "role": role,
                "parameter_count": format(mean(float(item["params"]) for item in complexity), ".10g"),
                "estimated_operation_count": format(mean(float(item["flops"]) for item in complexity), ".10g"),
                "selected_cases": row["SelectedCount"],
                "beneficial_selected_cases": row["SelectedBeneficialCount"],
                "harmful_selected_cases": row["SelectedHarmfulCount"],
                "mean_paired_mse_reduction_percent": format(
                    100.0 * float(row["MeanGainWhenSelected"] or 0.0), ".10g"
                ),
            }
        )
    _write(output_dir / "fig11_architecture_complexity_data.csv", fig11)

    with (ROOT / "results/robustness/source_bank_seed.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        seeds = [row for row in csv.DictReader(handle) if row["SourceSeed"].isdigit()]
    with (ROOT / "results/robustness/alibaba_oracle_diagnostics.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        alibaba = {row["Measure"]: float(row["Value"]) for row in csv.DictReader(handle)}
    fig12_summary = [
        {
            "group": f"Source seed {row['SourceSeed']}",
            "mean_gain_percent": format(100.0 * float(row["WMSEGainVsA57"]), ".10g"),
            "ci_low_percent": format(100.0 * float(row["CI_low"]), ".10g"),
            "ci_high_percent": format(100.0 * float(row["CI_high"]), ".10g"),
            "cases": row["N"],
        }
        for row in seeds
    ]
    fig12_summary.append(
        {
            "group": "Alibaba",
            "mean_gain_percent": format(100.0 * alibaba["Selected gain vs A57"], ".10g"),
            "ci_low_percent": format(100.0 * alibaba["Selected gain CI low"], ".10g"),
            "ci_high_percent": format(100.0 * alibaba["Selected gain CI high"], ".10g"),
            "cases": "80",
        }
    )
    _write(output_dir / "fig12_group_summary.csv", fig12_summary)

def derive_fig12(source_seed_path: Path, alibaba_path: Path, output_dir: Path) -> None:
    """Release the exact case-level gain distribution used by Fig. 12(b)."""

    source_obj = json.loads(source_seed_path.read_text(encoding="utf-8"))
    alibaba_obj = json.loads(alibaba_path.read_text(encoding="utf-8"))
    source_records = source_obj.get("records")
    alibaba_records = alibaba_obj.get("records")
    if not isinstance(source_records, dict) or len(source_records) != 240:
        raise ValueError("Fig. 12 requires exactly 240 source-seed records")
    if not isinstance(alibaba_records, dict) or len(alibaba_records) != 80:
        raise ValueError("Fig. 12 requires exactly 80 Alibaba records")

    rows: list[dict[str, Any]] = []
    for case_key, record in sorted(source_records.items()):
        seed = int(record["source_seed"])
        proposed = float(record["selected"]["test"]["weighted_mse"])
        reference = float(record["anchor"]["test"]["weighted_mse"])
        rows.append(
            {
                "group": f"Source seed {seed}",
                "case_key": case_key,
                "source_seed": seed,
                "proposed_mse": format(proposed, ".17g"),
                "matched_reference_mse": format(reference, ".17g"),
                "gain_percent": format(100.0 * (reference - proposed) / reference, ".17g"),
            }
        )
    for case_key, record in sorted(alibaba_records.items()):
        proposed = float(record["ours"]["test"]["weighted_mse"])
        reference = float(record["pt_ft"]["test"]["weighted_mse"])
        rows.append(
            {
                "group": "Alibaba",
                "case_key": record.get("machine_id_hash", case_key),
                "source_seed": "",
                "proposed_mse": format(proposed, ".17g"),
                "matched_reference_mse": format(reference, ".17g"),
                "gain_percent": format(100.0 * (reference - proposed) / reference, ".17g"),
            }
        )

    by_group = {
        group: [float(row["gain_percent"]) for row in rows if row["group"] == group]
        for group in ("Source seed 2904", "Source seed 2905", "Source seed 2906", "Alibaba")
    }
    expected_means = {
        "Source seed 2904": 10.52274902239512,
        "Source seed 2905": 13.207856064844497,
        "Source seed 2906": 11.25362479290699,
        "Alibaba": 1.9927963290380142,
    }
    for group, expected in expected_means.items():
        observed = mean(by_group[group])
        if abs(observed - expected) > 1e-10:
            raise ValueError(f"Fig. 12 mean changed for {group}: {observed}")
    extreme_alibaba = sum(value < -25.0 for value in by_group["Alibaba"])
    if extreme_alibaba != 4:
        raise ValueError(f"Expected four Alibaba gains below -25%, found {extreme_alibaba}")

    _write(output_dir / "fig12_case_level_gains.csv", rows)
    manifest = {
        "study": "fig12_case_level_gain_release",
        "decision": "PASS_FIG12_CASE_LEVEL_DATA_FROZEN",
        "derivation": "100 * (matched_reference_mse - proposed_mse) / matched_reference_mse",
        "source_sha256": {
            "source_seed_eval.json": _sha256(source_seed_path),
            "real_eval.json": _sha256(alibaba_path),
        },
        "records": {"source_seed": 240, "alibaba": 80, "total": 320},
        "group_mean_gain_percent": expected_means,
        "alibaba_gain_below_minus_25_percent_count": extreme_alibaba,
        "selection_uses_test": False,
    }
    provenance = ROOT / "results/audited_provenance/fig12_case_level_gain_manifest.json"
    provenance.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ours-json", type=Path)
    parser.add_argument("--pt-ft-json", type=Path)
    parser.add_argument("--source-seed-json", type=Path)
    parser.add_argument("--alibaba-json", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/figure_data")
    args = parser.parse_args()
    if bool(args.ours_json) != bool(args.pt_ft_json):
        parser.error("--ours-json and --pt-ft-json must be supplied together")
    if bool(args.source_seed_json) != bool(args.alibaba_json):
        parser.error("--source-seed-json and --alibaba-json must be supplied together")
    if args.ours_json:
        derive_fig6_fig8(args.ours_json, args.pt_ft_json, args.output_dir)
    derive_fig9(args.output_dir)
    derive_fig7_fig10_fig11(args.output_dir)
    if args.source_seed_json:
        derive_fig12(args.source_seed_json, args.alibaba_json, args.output_dir)
    print(f"Wrote reproducible figure data to {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
