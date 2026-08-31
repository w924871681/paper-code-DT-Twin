"""Canonical generator for the current manuscript's overall-performance figure.

Only the audited H-Meta-NAS values are loaded dynamically. All other plotted
values and every visual setting remain frozen to the accepted manuscript
figure. This module performs reporting only; it does not run experiments.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


FIGURE_STEM = "fig_overall_performance_ours"
FIGURE_SIZE = (6.62, 4.38)
METHODS = (
    "PT+FT",
    "MeDeT",
    "Random init.",
    "Few-shot NAS",
    "Zero-shot NAS",
    "Zero-shot NAS+FT",
    "H-Meta-NAS",
    "MSA-DTI (ours)",
)

# Frozen values shown in Error (x 10^-2). The H-Meta-NAS slots are populated
# from the audited canonical CSV at generation time.
PANEL_TEMPLATES = (
    ("MAE", (5.382, 6.409, 12.562, 6.428, 13.500, 6.654, None, 4.866), (0, 17.0), (0, 4, 8, 12)),
    ("MSE", (0.512, 0.712, 2.620, 0.711, 3.039, 0.753, None, 0.422), (0, 3.8), (0.0, 0.8, 1.6, 2.4, 3.2)),
    ("Worst-10% error", (1.908, 2.417, 7.330, 2.650, 7.519, 2.854, None, 1.576), (0, 9.1), (0, 2, 4, 6, 8)),
    ("CVaR90", (1.387, 2.240, 8.688, 1.909, 11.063, 1.878, None, 1.171), (0, 14.2), (0, 3, 6, 9, 12)),
)

H_META_NAS_INDEX = METHODS.index("H-Meta-NAS")
H_META_NAS_COLUMNS = ("MAE", "WMSE", "Worst10", "CVaR90_WMSE")
EXPECTED_H_META_NAS_LABELS = ("9.027", "1.357", "4.615", "3.493")
COLORS = ("#6e8fb3", "#8db8b0", "#c6c2bd", "#d9a25f", "#c77979", "#b39bbc", "#8f99a6", "#4f7f5c")


def load_h_meta_nas_values(canonical_results: str | Path) -> tuple[float, ...]:
    """Load audited H-Meta-NAS metrics and convert them to panel units."""
    path = Path(canonical_results)
    with path.open(newline="", encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if row["Method"] == "H-Meta-NAS"]
    if len(rows) != 1:
        raise ValueError(f"Expected one H-Meta-NAS row in {path}, found {len(rows)}")
    values = tuple(float(rows[0][column]) * 100.0 for column in H_META_NAS_COLUMNS)
    labels = tuple(f"{value:.3f}" for value in values)
    if labels != EXPECTED_H_META_NAS_LABELS:
        raise ValueError(f"Audited H-Meta-NAS labels changed: {labels}")
    return values


def panel_data(
    canonical_results: str | Path,
) -> tuple[tuple[str, tuple[float, ...], tuple[float, float], Sequence[float]], ...]:
    """Insert only audited H-Meta-NAS values into the frozen panel data."""
    audited_values = load_h_meta_nas_values(canonical_results)
    panels = []
    for (panel, values, xlim, ticks), audited_value in zip(PANEL_TEMPLATES, audited_values):
        plotted_values = list(values)
        plotted_values[H_META_NAS_INDEX] = audited_value
        panels.append((panel, tuple(plotted_values), xlim, ticks))
    return tuple(panels)


def build_figure(canonical_results: str | Path):
    """Build the frozen-layout Figure 5 from the canonical result row."""
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.0,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=FIGURE_SIZE)
    fig.subplots_adjust(left=0.180, right=0.970, bottom=0.180, top=0.840, wspace=0.620, hspace=0.720)

    y = np.arange(len(METHODS))
    for index, (ax, (panel, values, xlim, ticks)) in enumerate(zip(axes.flat, panel_data(canonical_results))):
        bars = ax.barh(y, values, height=0.68, color=COLORS, edgecolor="#5d5d5d", linewidth=0.55)
        bars[-1].set_hatch("//")
        ax.set_yticks(y, METHODS)
        ax.invert_yaxis()
        ax.set_xlim(*xlim)
        ax.set_xticks(ticks)
        ax.xaxis.grid(True, linestyle=":", color="#d7d7d7", linewidth=0.55)
        ax.set_axisbelow(True)
        ax.tick_params(axis="both", length=4, width=0.8, pad=2)
        for spine in ax.spines.values():
            spine.set_linewidth(0.8)
            spine.set_color("black")
        for label in ax.get_yticklabels():
            if label.get_text() == "MSA-DTI (ours)":
                label.set_fontweight("bold")

        offset = (xlim[1] - xlim[0]) * 0.030
        for pos, value in enumerate(values):
            ax.text(
                value + offset,
                pos,
                f"{value:.3f}",
                va="center",
                ha="left",
                clip_on=True,
                fontsize=7.0,
                fontweight="bold" if pos == len(values) - 1 else "normal",
            )
        ax.set_xlabel(r"Error ($\times 10^{-2}$); lower is better", labelpad=6)
        ax.text(0.5, -0.50, f"({chr(ord('a') + index)}) {panel}", transform=ax.transAxes, ha="center", va="top", fontsize=8.0)

    legend_handles = [
        Patch(facecolor=color, edgecolor="#5d5d5d", linewidth=0.55, hatch="//" if method == "MSA-DTI (ours)" else "", label=method)
        for method, color in zip(METHODS, COLORS)
    ]
    fig.legend(
        handles=(legend_handles[0], legend_handles[1], legend_handles[2], legend_handles[3], legend_handles[4], legend_handles[5], legend_handles[7], legend_handles[6]),
        ncol=4,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        frameon=False,
        fontsize=7.5,
        handlelength=1.35,
        handleheight=0.7,
        handletextpad=0.55,
        columnspacing=1.45,
        borderaxespad=0.0,
    )
    return fig


def generate_overall_performance(
    canonical_results: str | Path,
    output_dir: str | Path,
    *,
    png_dpi: int = 300,
) -> dict[str, str]:
    """Generate the current manuscript Figure 5 without running experiments."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    pdf_path = output / f"{FIGURE_STEM}.pdf"
    png_path = output / f"{FIGURE_STEM}.png"
    fig = build_figure(canonical_results)
    try:
        fig.savefig(pdf_path, format="pdf")
        fig.savefig(png_path, dpi=png_dpi)
    finally:
        plt.close(fig)
    return {"pdf": str(pdf_path), "png": str(png_path)}


__all__ = [
    "EXPECTED_H_META_NAS_LABELS",
    "FIGURE_SIZE",
    "FIGURE_STEM",
    "H_META_NAS_INDEX",
    "METHODS",
    "PANEL_TEMPLATES",
    "build_figure",
    "generate_overall_performance",
    "load_h_meta_nas_values",
    "panel_data",
]
