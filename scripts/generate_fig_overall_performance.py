"""Regenerate the manuscript's overall-performance figure.

The values, panel order, palette, hatching, axes, and tick locations reproduce
the frozen eight-method comparison.  MSA-DTI is explicitly identified as the
proposed method with ``(ours)`` in both the legend and row labels.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "paper" / "figures"

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

# Frozen values shown in Error (x 10^-2), transcribed from the audited figure.
PANELS = (
    ("MAE", (5.382, 6.409, 12.562, 6.428, 13.500, 6.654, 9.047, 4.866), (0, 17.0), (0, 4, 8, 12)),
    ("MSE", (0.512, 0.712, 2.620, 0.711, 3.039, 0.753, 1.375, 0.422), (0, 3.8), (0.0, 0.8, 1.6, 2.4, 3.2)),
    ("Worst-10% error", (1.908, 2.417, 7.330, 2.650, 7.519, 2.854, 4.725, 1.576), (0, 9.1), (0, 2, 4, 6, 8)),
    ("CVaR90", (1.387, 2.240, 8.688, 1.909, 11.063, 1.878, 3.696, 1.171), (0, 14.2), (0, 3, 6, 9, 12)),
)

COLORS = ("#6e8fb3", "#8db8b0", "#c6c2bd", "#d9a25f", "#c77979", "#b39bbc", "#8f99a6", "#4f7f5c")


def main() -> None:
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
    fig, axes = plt.subplots(2, 2, figsize=(6.62, 4.38))
    fig.subplots_adjust(left=0.180, right=0.970, bottom=0.180, top=0.840, wspace=0.620, hspace=0.720)

    y = np.arange(len(METHODS))
    for index, (ax, (panel, values, xlim, ticks)) in enumerate(zip(axes.flat, PANELS)):
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
            # Values remain to the right of their bars and inside their panel.
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
    # Column-major ordering preserves the two-row legend arrangement.
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

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_DIR / "fig_overall_performance.pdf", format="pdf")
    fig.savefig(OUTPUT_DIR / "fig_overall_performance.png", dpi=300)


if __name__ == "__main__":
    main()
