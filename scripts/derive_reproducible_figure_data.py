# -*- coding: utf-8 -*-
"""Derive the public Fig. 6/8/9 CSV layer from frozen experiment records.

Fig. 6 and Fig. 8 require the custodian-side locked-evaluation JSON files.
Fig. 9 is derived entirely from sources already released in this repository.
The resulting compact CSV files are versioned so plotting never requires
private paths, model weights, or a rerun of training/evaluation.
"""

from __future__ import annotations

import argparse
import csv
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ours-json", type=Path)
    parser.add_argument("--pt-ft-json", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/figure_data")
    args = parser.parse_args()
    if bool(args.ours_json) != bool(args.pt_ft_json):
        parser.error("--ours-json and --pt-ft-json must be supplied together")
    if args.ours_json:
        derive_fig6_fig8(args.ours_json, args.pt_ft_json, args.output_dir)
    derive_fig9(args.output_dir)
    print(f"Wrote reproducible figure data to {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
