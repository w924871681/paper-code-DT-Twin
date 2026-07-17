# -*- coding: utf-8 -*-
"""Independent publication plots for the released Fig. 6, Fig. 8, and Fig. 9 CSVs."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


FIGURE_SIZES: Mapping[str, tuple[float, float]] = {
    "fig6_paired_instantiation": (7.48, 3.05),
    "fig8_budget_architecture": (7.48, 3.05),
    "fig9_bank_adaptation_margin": (7.48, 3.25),
}


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"Empty figure data: {path}")
    return rows


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans"],
            "font.size": 7.2,
            "axes.titlesize": 8.0,
            "axes.labelsize": 7.2,
            "xtick.labelsize": 6.6,
            "ytick.labelsize": 6.6,
            "legend.fontsize": 6.5,
            "axes.linewidth": 0.7,
            "lines.linewidth": 1.1,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def _layout_audit(fig: plt.Figure) -> dict[str, Any]:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bounds = fig.bbox
    out_of_bounds = []
    # Font hinting can extend a glyph a few pixels beyond its logical canvas
    # box even when it is fully visible.  Six pixels at 100-dpi audit render
    # is a conservative anti-aliasing tolerance, not a clipping allowance.
    tolerance = 6
    for text in fig.findobj(match=plt.Text):
        if not text.get_visible() or not text.get_text().strip():
            continue
        box = text.get_window_extent(renderer=renderer)
        if box.x0 < bounds.x0 - tolerance or box.y0 < bounds.y0 - tolerance or box.x1 > bounds.x1 + tolerance or box.y1 > bounds.y1 + tolerance:
            out_of_bounds.append(text.get_text())
    overlaps = []
    for axis_index, ax in enumerate(fig.axes):
        for direction, labels in (("x", ax.get_xticklabels()), ("y", ax.get_yticklabels())):
            boxes = [label.get_window_extent(renderer=renderer) for label in labels if label.get_visible() and label.get_text()]
            for left, right in zip(boxes, boxes[1:]):
                if left.overlaps(right):
                    overlaps.append({"axis": axis_index, "direction": direction})
    return {
        "out_of_bounds_text": out_of_bounds,
        "tick_label_overlaps": overlaps,
        "status": "PASS" if not out_of_bounds and not overlaps else "FAIL",
    }


def _save(fig: plt.Figure, output_dir: Path, stem: str) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    qa_dir = output_dir / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    audit = {"figure": stem, **_layout_audit(fig)}
    metadata = {
        "Title": stem,
        "Author": "Released deterministic reporting code",
        "Subject": "Public CSV figure reconstruction",
        "CreationDate": None,
        "ModDate": None,
    }
    fig.savefig(output_dir / f"{stem}.pdf", format="pdf", metadata=metadata)
    fig.savefig(output_dir / f"{stem}.png", format="png", dpi=600, pil_kwargs={"compress_level": 6})
    plt.close(fig)
    with Image.open(output_dir / f"{stem}.png") as image:
        image.convert("L").convert("RGB").save(
            qa_dir / f"{stem}_grayscale.png", dpi=(600, 600)
        )
    (qa_dir / f"{stem}_layout_audit.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8"
    )
    if audit["status"] != "PASS":
        raise RuntimeError(f"Layout audit failed for {stem}: {audit}")
    return audit


def plot_fig6(data_dir: Path, output_dir: Path) -> dict[str, Any]:
    rows = _read(data_dir / "fig6_paired_instantiation_data.csv")
    if len(rows) != 80:
        raise ValueError("Fig. 6 requires exactly 80 paired cases")
    categories = (
        ("beneficial alternative", "Beneficial alternative", "#0072B2", "o"),
        ("reference retained", "Reference retained", "#666666", "s"),
        ("harmful alternative", "Harmful alternative", "#D55E00", "X"),
    )
    counts = Counter(row["selection_category"] for row in rows)
    _style()
    fig, axes = plt.subplots(1, 2, figsize=FIGURE_SIZES["fig6_paired_instantiation"])
    fig.subplots_adjust(left=0.085, right=0.985, top=0.90, bottom=0.27, wspace=0.28)
    for ax, reference_key, proposed_key, title in (
        (axes[0], "pt_ft_wmse", "proposed_wmse", "(a) WMSE"),
        (axes[1], "pt_ft_worst10", "proposed_worst10", "(b) Worst-10% error"),
    ):
        values = [100.0 * float(row[key]) for row in rows for key in (reference_key, proposed_key)]
        upper = max(values) * 1.055
        ax.plot((0, upper), (0, upper), color="#222222", lw=0.75, ls=(0, (3, 2)), zorder=1)
        for key, label, color, marker in categories:
            subset = [row for row in rows if row["selection_category"] == key]
            ax.scatter(
                [100.0 * float(row[reference_key]) for row in subset],
                [100.0 * float(row[proposed_key]) for row in subset],
                s=19 if marker != "X" else 27,
                marker=marker,
                facecolors="white" if marker != "X" else color,
                edgecolors=color,
                linewidths=0.8,
                label=f"{label} ({counts[key]})",
                zorder=2,
            )
        ax.set_xlim(0, upper)
        ax.set_ylim(0, upper)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel(r"PT+FT ($\times 10^{-2}$)")
        ax.set_ylabel(r"Proposed method ($\times 10^{-2}$)")
        ax.set_title(title, loc="left")
        ax.grid(color="#E1E1E1", lw=0.45, ls=(0, (2, 2)))
        ax.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.045))
    return _save(fig, output_dir, "fig6_paired_instantiation")


def plot_fig8(data_dir: Path, output_dir: Path) -> dict[str, Any]:
    filtering = _read(data_dir / "fig8_candidate_filtering_data.csv")
    selection = _read(data_dir / "fig8_architecture_selection_data.csv")
    budgets = [row["budget_tier"] for row in filtering]
    tick_labels = [f"{tier.title()}\n(n={row['case_count']})" for tier, row in zip(budgets, filtering)]
    models = []
    for row in sorted(selection, key=lambda item: int(item["architecture_order"])):
        if row["model_configuration"] not in models:
            models.append(row["model_configuration"])
    matrix = np.asarray(
        [
            [
                float(next(row["selection_rate"] for row in selection if row["budget_tier"] == tier and row["model_configuration"] == model))
                for tier in budgets
            ]
            for model in models
        ]
    )
    _style()
    fig, axes = plt.subplots(1, 2, figsize=FIGURE_SIZES["fig8_budget_architecture"], gridspec_kw={"width_ratios": [0.85, 1.35]})
    fig.subplots_adjust(left=0.075, right=0.925, top=0.90, bottom=0.25, wspace=0.42)
    x = np.arange(len(budgets))
    width = 0.34
    initialized = [float(row["initialized_candidates_per_case"]) for row in filtering]
    feasible = [float(row["feasible_candidates_per_case_mean"]) for row in filtering]
    bars1 = axes[0].bar(x - width / 2, initialized, width, color="white", edgecolor="#666666", hatch="///", label="Initialized candidates")
    bars2 = axes[0].bar(x + width / 2, feasible, width, color="#56B4E9", edgecolor="#0072B2", label="Feasible candidates")
    axes[0].bar_label(bars1, fmt="%.0f", padding=2, fontsize=6.5)
    axes[0].bar_label(bars2, fmt="%.0f", padding=2, fontsize=6.5)
    axes[0].set_xticks(x, tick_labels)
    axes[0].set_ylim(0, 8.4)
    axes[0].set_ylabel("Candidates per case")
    axes[0].set_title("(a) Candidate filtering", loc="left")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc="lower center", bbox_to_anchor=(0.255, 0.025), ncol=2)
    axes[0].spines[["top", "right"]].set_visible(False)
    image = axes[1].pcolormesh(
        np.arange(len(budgets) + 1),
        np.arange(len(models) + 1),
        matrix * 100.0,
        cmap="Blues",
        vmin=0,
        vmax=50,
        shading="flat",
    )
    axes[1].invert_yaxis()
    axes[1].set_xticks(np.arange(len(budgets)) + 0.5, tick_labels)
    axes[1].set_yticks(np.arange(len(models)) + 0.5, models)
    axes[1].set_title("(b) Final model selection", loc="left")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = 100 * matrix[i, j]
            axes[1].text(j + 0.5, i + 0.5, f"{value:.0f}%", ha="center", va="center", color="white" if value >= 32 else "#222222", fontsize=6.6)
    axes[1].text(
        1.0,
        -0.17,
        "Cell labels: selection rate (%)",
        transform=axes[1].transAxes,
        ha="right",
        va="top",
        fontsize=6.2,
        color="#444444",
    )
    return _save(fig, output_dir, "fig8_budget_architecture")


def plot_fig9(data_dir: Path, output_dir: Path) -> dict[str, Any]:
    bank = _read(data_dir / "fig9_bank_size_data.csv")
    steps = _read(data_dir / "fig9_adaptation_steps_data.csv")
    margin = _read(data_dir / "fig9_margin_data.csv")
    _style()
    fig = plt.figure(figsize=FIGURE_SIZES["fig9_bank_adaptation_margin"])
    outer = fig.add_gridspec(1, 3, width_ratios=(1.0, 1.14, 1.0), left=0.075, right=0.985, top=0.88, bottom=0.24, wspace=0.43)
    ax_a = fig.add_subplot(outer[0, 0])
    middle = outer[0, 1].subgridspec(2, 1, hspace=0.10)
    ax_b1 = fig.add_subplot(middle[0, 0])
    ax_b2 = fig.add_subplot(middle[1, 0], sharex=ax_b1)
    ax_c = fig.add_subplot(outer[0, 2])

    x_a = np.asarray([float(row["retained_architectures"]) for row in bank])
    y_a = np.asarray([1000 * float(row["diagnostic_wmse"]) for row in bank])
    ax_a.plot(x_a, y_a, color="#0072B2", marker="o", markerfacecolor="white")
    ax_a.axvspan(4, 6.15, color="#0072B2", alpha=0.08, lw=0)
    ax_a.annotate("Saturation after 4", xy=(4, y_a[3]), xytext=(3.1, 4.48), arrowprops={"arrowstyle": "->", "lw": 0.7}, fontsize=6.4)
    ax_a.set_xticks(x_a)
    ax_a.set_xlabel("Retained architectures")
    ax_a.set_ylabel(r"Diagnostic WMSE ($\times 10^{-3}$)")
    ax_a.set_title("(a) Candidate-bank size", loc="left")

    x_b = np.asarray([float(row["adaptation_steps"]) for row in steps])
    y_b1 = np.asarray([1000 * float(row["selected_check_wmse_mean"]) for row in steps])
    y_b2 = np.asarray([100 * float(row["selection_agreement_with_50"]) for row in steps])
    ax_b1.plot(x_b, y_b1, color="#0072B2", marker="o", markerfacecolor="white")
    ax_b1.set_ylabel("Check WMSE\n" + r"($\times 10^{-3}$)")
    ax_b1.set_title("(b) Fixed adaptation budget", loc="left")
    ax_b1.tick_params(labelbottom=False)
    ax_b2.plot(x_b, y_b2, color="#D55E00", marker="s", markerfacecolor="white")
    ax_b2.set_ylabel("Agreement\n(%)")
    ax_b2.set_xlabel("Adaptation steps")
    shown = [0, 2, 3, 4, 5]
    ax_b2.set_xticks(x_b[shown], [f"{x_b[index]:g}" for index in shown])
    ax_b2.set_ylim(45, 104)

    x_c = np.asarray([100 * float(row["minimum_improvement"]) for row in margin])
    alt = np.asarray([100 * float(row["alternative_selection_rate"]) for row in margin])
    harmful = np.asarray([100 * float(row["harmful_selection_rate"]) for row in margin])
    ax_c.plot(x_c, alt, color="#0072B2", marker="o", markerfacecolor="white", label="Alternative selection")
    ax_c.plot(x_c, harmful, color="#D55E00", marker="s", markerfacecolor="white", label="Harmful selection")
    ax_c.axvline(10, color="#555555", ls=(0, (3, 2)), lw=0.75)
    ax_c.axhline(5, color="#777777", ls=(0, (1, 2)), lw=0.75)
    ax_c.text(10.35, 67, "10% threshold", rotation=90, va="top", fontsize=6.1, color="#444444")
    ax_c.text(5.2, 6.7, "5% criterion", fontsize=6.1, color="#555555")
    ax_c.set_xticks(x_c, [f"{value:g}" for value in x_c])
    ax_c.set_ylim(0, 70)
    ax_c.set_xlabel("Minimum improvement (%)")
    ax_c.set_ylabel("Rate (%)")
    ax_c.set_title("(c) Threshold calibration", loc="left")
    handles, labels = ax_c.get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc="lower center", bbox_to_anchor=(0.83, 0.02), ncol=1)
    for ax in (ax_a, ax_b1, ax_b2, ax_c):
        ax.grid(axis="y", color="#E1E1E1", lw=0.45, ls=(0, (2, 2)))
        ax.spines[["top", "right"]].set_visible(False)
    return _save(fig, output_dir, "fig9_bank_adaptation_margin")


def plot_all(data_dir: str | Path, output_dir: str | Path) -> dict[str, dict[str, Any]]:
    data = Path(data_dir).resolve()
    output = Path(output_dir).resolve()
    return {
        "fig6": plot_fig6(data, output),
        "fig8": plot_fig8(data, output),
        "fig9": plot_fig9(data, output),
    }


__all__ = ["FIGURE_SIZES", "plot_all", "plot_fig6", "plot_fig8", "plot_fig9"]
