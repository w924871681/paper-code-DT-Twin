# -*- coding: utf-8 -*-
"""Canonical publication plots for manuscript Fig. 6--12.

This is the only maintained implementation of the final data-driven figures.
It consumes the released plot-ready CSV files and never reruns training,
selection, adaptation, or bootstrap resampling.
"""

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
from matplotlib.lines import Line2D
from PIL import Image


FIGURE_SIZES: Mapping[str, tuple[float, float]] = {
    "fig6": (7.48, 3.18),
    "fig7": (7.48, 2.90),
    "fig8": (7.48, 3.18),
    "fig9": (7.48, 3.32),
    "fig10": (3.54, 3.72),
    "fig11": (7.48, 4.85),
    "fig12": (7.48, 3.05),
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
    fig, axes = plt.subplots(1, 2, figsize=FIGURE_SIZES["fig6"])
    fig.subplots_adjust(left=0.085, right=0.985, top=0.78, bottom=0.25, wspace=0.28)
    for ax, reference_key, proposed_key in (
        (axes[0], "pt_ft_wmse", "proposed_wmse"),
        (axes[1], "pt_ft_worst10", "proposed_worst10"),
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
        ax.set_ylabel(r"RCF-DTI ($\times 10^{-2}$)")
        ax.grid(color="#E1E1E1", lw=0.45, ls=(0, (2, 2)))
        ax.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.985))
    fig.text(0.277, 0.035, "(a) Test MSE", ha="center")
    fig.text(0.760, 0.035, "(b) Test Worst-10% error", ha="center")
    return _save(fig, output_dir, "fig6")


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
    fig, axes = plt.subplots(1, 2, figsize=FIGURE_SIZES["fig8"], gridspec_kw={"width_ratios": [0.85, 1.35]})
    fig.subplots_adjust(left=0.075, right=0.925, top=0.79, bottom=0.25, wspace=0.42)
    x = np.arange(len(budgets))
    width = 0.34
    initialized = [float(row["initialized_candidates_per_case"]) for row in filtering]
    feasible = [float(row["feasible_candidates_per_case_mean"]) for row in filtering]
    bars1 = axes[0].bar(x - width / 2, initialized, width, color="white", edgecolor="#666666", hatch="///", label="Before filtering")
    bars2 = axes[0].bar(x + width / 2, feasible, width, color="#56B4E9", edgecolor="#0072B2", label="After filtering")
    axes[0].bar_label(bars1, fmt="%.0f", padding=2, fontsize=6.5)
    axes[0].bar_label(bars2, fmt="%.0f", padding=2, fontsize=6.5)
    axes[0].set_xticks(x, tick_labels)
    axes[0].set_ylim(0, 8.4)
    axes[0].set_ylabel("Candidates per case")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc="upper center", bbox_to_anchor=(0.255, 0.985), ncol=2)
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
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = 100 * matrix[i, j]
            axes[1].text(j + 0.5, i + 0.5, f"{value:.0f}%", ha="center", va="center", color="white" if value >= 32 else "#222222", fontsize=6.6)
    axes[1].text(
        1.0,
        1.12,
        "Cell labels: selection rate (%)",
        transform=axes[1].transAxes,
        ha="right",
        va="bottom",
        fontsize=6.2,
        color="#444444",
    )
    fig.text(0.245, 0.035, "(a) Complexity filtering", ha="center")
    fig.text(0.720, 0.035, "(b) Selected model configurations", ha="center")
    return _save(fig, output_dir, "fig8")


def plot_fig9(data_dir: Path, output_dir: Path) -> dict[str, Any]:
    bank = _read(data_dir / "fig9_bank_size_data.csv")
    steps = _read(data_dir / "fig9_adaptation_steps_data.csv")
    margin = _read(data_dir / "fig9_margin_data.csv")
    _style()
    fig = plt.figure(figsize=FIGURE_SIZES["fig9"])
    outer = fig.add_gridspec(1, 3, width_ratios=(1.0, 1.10, 1.0), left=0.070, right=0.965, top=0.83, bottom=0.26, wspace=0.48)
    ax_a = fig.add_subplot(outer[0, 0])
    ax_b1 = fig.add_subplot(outer[0, 1])
    ax_b2 = ax_b1.twinx()
    ax_c = fig.add_subplot(outer[0, 2])

    x_a = np.asarray([float(row["retained_architectures"]) for row in bank])
    y_a = np.asarray([1000 * float(row["diagnostic_wmse"]) for row in bank])
    ax_a.plot(x_a, y_a, color="#0072B2", marker="o", markerfacecolor="white")
    ax_a.axvspan(4, 6.15, color="#0072B2", alpha=0.08, lw=0)
    ax_a.annotate("Saturation after 4", xy=(4, y_a[3]), xytext=(3.1, 4.48), arrowprops={"arrowstyle": "->", "lw": 0.7}, fontsize=6.4)
    ax_a.set_xticks(x_a)
    ax_a.set_xlabel("Retained architectures")
    ax_a.set_ylabel(r"Diagnostic MSE ($\times 10^{-3}$)")

    x_b_values = np.asarray([float(row["adaptation_steps"]) for row in steps])
    x_b = np.arange(len(x_b_values))
    y_b1 = np.asarray([1000 * float(row["selected_check_wmse_mean"]) for row in steps])
    y_b2 = np.asarray([100 * float(row["selection_agreement_with_50"]) for row in steps])
    line_mse = ax_b1.plot(x_b, y_b1, color="#0072B2", marker="o", markerfacecolor="white", label="Check MSE")[0]
    ax_b1.set_ylabel(r"Check MSE ($\times 10^{-3}$)", color="#0072B2")
    ax_b1.tick_params(axis="y", colors="#0072B2")
    line_agree = ax_b2.plot(x_b, y_b2, color="#D55E00", marker="s", markerfacecolor="white", label="Agreement")[0]
    ax_b2.set_ylabel("Agreement with 50-update result (%)", color="#D55E00")
    ax_b2.tick_params(axis="y", colors="#D55E00")
    ax_b1.set_xlabel("Target updates")
    ax_b1.set_xticks(x_b, [f"{value:g}" for value in x_b_values])
    ax_b2.set_ylim(45, 104)
    ax_b1.legend([line_mse, line_agree], ["Check MSE", "Selection agreement"], frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.25), ncol=1)

    x_c = np.asarray([100 * float(row["minimum_improvement"]) for row in margin])
    alt = np.asarray([100 * float(row["alternative_selection_rate"]) for row in margin])
    harmful = np.asarray([100 * float(row["harmful_selection_rate"]) for row in margin])
    ax_c.plot(x_c, alt, color="#0072B2", marker="o", markerfacecolor="white", label="Alternative selection")
    ax_c.plot(x_c, harmful, color="#D55E00", marker="s", markerfacecolor="white", label="Harmful selection")
    ax_c.axvline(10, color="#555555", ls=(0, (3, 2)), lw=0.75)
    ax_c.axhline(5, color="#777777", ls=(0, (1, 2)), lw=0.75)
    ax_c.text(10.35, 67, r"$\tau=10\%$", rotation=90, va="top", fontsize=6.1, color="#444444")
    ax_c.text(5.2, 6.7, "5% criterion", fontsize=6.1, color="#555555")
    ax_c.set_xticks(x_c, [f"{value:g}" for value in x_c])
    ax_c.set_ylim(0, 70)
    ax_c.set_xlabel(r"Selection threshold $\tau$ (%)")
    ax_c.set_ylabel("Rate (%)")
    handles, labels = ax_c.get_legend_handles_labels()
    ax_c.legend(handles, labels, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.25), ncol=1)
    for ax in (ax_a, ax_b1, ax_c):
        ax.grid(axis="y", color="#E1E1E1", lw=0.45, ls=(0, (2, 2)))
        ax.spines[["top", "right"]].set_visible(False)
    ax_b2.spines["top"].set_visible(False)
    fig.text(0.190, 0.035, "(a) Retained architectures", ha="center")
    fig.text(0.515, 0.035, "(b) Fixed 50-update budget", ha="center")
    fig.text(0.835, 0.035, "(c) Threshold calibration", ha="center")
    return _save(fig, output_dir, "fig9")


def plot_fig7(data_dir: Path, output_dir: Path) -> dict[str, Any]:
    rows = _read(data_dir / "fig7_heterogeneity_data.csv")
    _style()
    fig, axes = plt.subplots(1, 2, figsize=FIGURE_SIZES["fig7"])
    fig.subplots_adjust(left=0.105, right=0.985, top=0.94, bottom=0.27, wspace=0.48)
    for ax, panel, color in (
        (axes[0], "H/K", "#0072B2"),
        (axes[1], "Center type", "#D55E00"),
    ):
        subset = [row for row in rows if row["panel"] == panel]
        y = np.arange(len(subset))[::-1]
        means = np.asarray([float(row["gain_percent"]) for row in subset])
        lows = np.asarray([float(row["ci_low_percent"]) for row in subset])
        highs = np.asarray([float(row["ci_high_percent"]) for row in subset])
        ax.errorbar(
            means,
            y,
            xerr=np.vstack((means - lows, highs - means)),
            fmt="o",
            color=color,
            mfc="white",
            mec=color,
            capsize=2.5,
            lw=1.0,
        )
        for yi, mean_value, low, high in zip(y, means, lows, highs):
            ax.text(high + 0.6, yi, f"{mean_value:.2f}", va="center", fontsize=6.4)
        ax.axvline(0, color="#555555", lw=0.75, ls=(0, (3, 2)))
        ax.set_yticks(y, [row["group"] for row in subset])
        ax.set_xlim(-5, 36)
        ax.set_xticks((0, 10, 20, 30))
        ax.set_ylim(-0.65, max(y) + 0.65)
        ax.set_xlabel("MSE reduction relative to PT+FT (%)")
        ax.grid(axis="x", color="#D9D9D9", lw=0.45, ls=(0, (2, 2)))
        ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.280, 0.035, "(a) Prediction horizon and support size", ha="center")
    fig.text(0.755, 0.035, "(b) Target-center type", ha="center")
    return _save(fig, output_dir, "fig7")


def plot_fig10(data_dir: Path, output_dir: Path) -> dict[str, Any]:
    rows = _read(data_dir / "fig10_deployment_tradeoff_data.csv")
    axes_meta = (
        ("mse", "MSE"),
        ("worst10", "Worst-10%"),
        ("cvar90", "CVaR90"),
        ("target_time_seconds", "Time"),
        ("parameter_count", "Parameters"),
        ("estimated_operation_count", "Operations"),
    )
    angles = np.linspace(0, 2 * np.pi, len(axes_meta), endpoint=False)
    closed = np.r_[angles, angles[0]]
    raw = {
        key: np.asarray([float(row[key]) for row in rows], dtype=float)
        for key, _ in axes_meta
    }
    scores = {
        key: 100.0 * np.min(values) / values
        for key, values in raw.items()
    }
    styles = (
        ("#0072B2", "s", "-", 1.2),
        ("#E69F00", "^", "-", 1.2),
        ("#009E73", "D", "-", 1.2),
        ("#D55E00", "o", "-", 2.0),
    )
    _style()
    fig, ax = plt.subplots(figsize=FIGURE_SIZES["fig10"], subplot_kw={"projection": "polar"})
    fig.subplots_adjust(left=0.12, right=0.88, top=0.91, bottom=0.25)
    ax.set_theta_offset(0)
    ax.set_theta_direction(1)
    ax.set_xticks(angles, [label for _, label in axes_meta])
    ax.set_ylim(0, 100)
    ax.set_yticks((25, 50, 75, 100))
    ax.set_rlabel_position(3)
    ax.grid(color="#B9C0C7", lw=0.55, ls=(0, (2, 2)))
    for index, (row, (color, marker, linestyle, linewidth)) in enumerate(zip(rows, styles)):
        values = np.asarray([scores[key][index] for key, _ in axes_meta])
        values = np.r_[values, values[0]]
        ax.plot(
            closed,
            values,
            color=color,
            marker=marker,
            ls=linestyle,
            lw=linewidth,
            ms=4.0,
            label=row["method"],
        )
        ax.fill(closed, values, color=color, alpha=0.045)
    fig.legend(
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.035),
        ncol=2,
        columnspacing=1.1,
        handlelength=2.1,
    )
    fig.text(
        0.5,
        0.005,
        "Normalized score = 100 × best / method; all six raw metrics are lower-is-better.",
        ha="center",
        fontsize=5.8,
    )
    return _save(fig, output_dir, "fig10")


def plot_fig11(data_dir: Path, output_dir: Path) -> dict[str, Any]:
    rows = _read(data_dir / "fig11_architecture_complexity_data.csv")
    _style()
    fig, ax = plt.subplots(figsize=FIGURE_SIZES["fig11"])
    fig.subplots_adjust(left=0.105, right=0.75, top=0.95, bottom=0.14)
    x = np.asarray([float(row["estimated_operation_count"]) / 1e6 for row in rows])
    y = np.asarray([float(row["mean_paired_mse_reduction_percent"]) for row in rows])
    params = np.asarray([float(row["parameter_count"]) for row in rows])
    counts = np.asarray([float(row["selected_cases"]) for row in rows])
    norm = matplotlib.colors.LogNorm(vmin=2000, vmax=85000)
    for role, marker in (("alternative", "o"), ("reference", "s")):
        indices = [index for index, row in enumerate(rows) if row["role"] == role]
        scatter = ax.scatter(
            x[indices],
            y[indices],
            s=35 + 10 * counts[indices],
            c=params[indices],
            cmap="viridis",
            norm=norm,
            marker=marker,
            edgecolor="white",
            linewidth=0.8,
            zorder=3,
        )
    offsets = {
        "3-layer MLP-32": (0.045, 1.15),
        "4-layer MLP-32": (0.045, -1.05),
        "Alt. GRU-16": (0.055, 1.15),
        "Alt. GRU-32": (-0.255, 1.30),
        "Ref. GRU-32": (-0.235, 1.15),
    }
    for index, row in enumerate(rows):
        dx, dy = offsets[row["configuration"]]
        harmful = int(row["harmful_selected_cases"])
        harm = f"; h={harmful}" if harmful else ""
        label = (
            f"{row['configuration']}\n"
            f"{float(row['mean_paired_mse_reduction_percent']):.2f}%{harm}"
        )
        ax.text(x[index] + dx, y[index] + dy, label, fontsize=7.0, va="center")
    ax.axhline(0, color="#555555", lw=0.75, ls=(0, (3, 2)))
    ax.set_xlim(0.10, 1.12)
    ax.set_ylim(-2.4, 34.5)
    ax.set_xlabel(r"Estimated operation count ($\times 10^6$)")
    ax.set_ylabel("Mean paired MSE reduction (%)")
    ax.grid(color="#D0D0D0", lw=0.45)
    cbar_ax = fig.add_axes((0.81, 0.56, 0.035, 0.31))
    colorbar = fig.colorbar(scatter, cax=cbar_ax)
    if colorbar.solids is not None:
        colorbar.solids.set_rasterized(False)
    colorbar.set_label(r"Parameter count ($\times 10^3$)")
    colorbar.set_ticks((2000, 5000, 10000, 20000, 50000, 80000))
    colorbar.set_ticklabels(("2", "5", "10", "20", "50", "80"))
    role_handles = [
        Line2D([], [], marker="o", ls="", color="#238A8D", label="Alternative"),
        Line2D([], [], marker="s", ls="", color="#238A8D", label="Reference"),
    ]
    size_handles = [
        Line2D([], [], marker="o", ls="", color="#238A8D", ms=np.sqrt(35 + 10 * n) / 1.55, label=str(n))
        for n in (5, 15, 30)
    ]
    first = fig.legend(
        handles=role_handles,
        title="Candidate role",
        frameon=False,
        loc="center left",
        bbox_to_anchor=(0.79, 0.37),
    )
    fig.add_artist(first)
    fig.legend(
        handles=size_handles,
        title="Selected cases",
        frameon=False,
        loc="center left",
        bbox_to_anchor=(0.79, 0.14),
    )
    return _save(fig, output_dir, "fig11")


def plot_fig12(data_dir: Path, output_dir: Path) -> dict[str, Any]:
    scale = _read(data_dir / "tableS2_controlled_source_scale.csv")
    cases = _read(data_dir / "fig12_case_level_gains.csv")
    summary = {row["group"]: row for row in _read(data_dir / "fig12_group_summary.csv")}
    _style()
    fig, (ax_a, ax_b) = plt.subplots(
        1,
        2,
        figsize=FIGURE_SIZES["fig12"],
        gridspec_kw={"width_ratios": (0.82, 1.18)},
    )
    fig.subplots_adjust(left=0.075, right=0.985, top=0.95, bottom=0.24, wspace=0.40)

    source_n = np.asarray([float(row["Source centers"]) for row in scale])
    means = np.asarray([float(row["Gain (%)"]) for row in scale])
    intervals = [
        [float(value.strip()) for value in row["95% CI (%)"].strip("[]").split(",")]
        for row in scale
    ]
    low = np.asarray([item[0] for item in intervals])
    high = np.asarray([item[1] for item in intervals])
    ax_a.fill_between(source_n, low, high, color="#0072B2", alpha=0.17, linewidth=0, label="95% CI")
    ax_a.plot(source_n, means, color="#0072B2", marker="o", label="Mean gain")
    for xv, yv in zip(source_n, means):
        ax_a.text(xv, yv + 0.42, f"{yv:.2f}", ha="center", fontsize=6.4)
    ax_a.axvline(20, color="#0072B2", ls=(0, (1, 2)), lw=0.9)
    ax_a.axhline(0, color="#0072B2", ls=(0, (3, 2)), lw=0.8)
    ax_a.text(20.7, 8.6, "Main source scale", rotation=90, va="top", fontsize=6.2)
    ax_a.set_xticks(source_n)
    ax_a.set_ylim(-0.45, 9.6)
    ax_a.set_xlabel("Number of source centers")
    ax_a.set_ylabel("MSE reduction relative to\nthe matched reference (%)")
    handles, labels = ax_a.get_legend_handles_labels()
    ax_a.legend(handles[::-1], labels[::-1], frameon=False, loc="upper right")
    ax_a.grid(color="#D4D4D4", lw=0.45, ls=(0, (2, 2)))
    ax_a.spines[["top", "right"]].set_visible(False)

    groups = ("Source seed 2904", "Source seed 2905", "Source seed 2906", "Alibaba")
    labels = ("Source seed 2904", "Source seed 2905", "Source seed 2906", "Alibaba v2018")
    colors = ("#56A0D3", "#F4A261", "#79C48C", "#E77C7C")
    mean_colors = ("#E67E22", "#D73027", "#8C564B", "#9C89B8")
    y_positions = np.arange(4)[::-1]
    rng = np.random.default_rng(2904)
    xmin = -25.0
    for y_pos, group, label, color, mean_color in zip(y_positions, groups, labels, colors, mean_colors):
        values = np.asarray([float(row["gain_percent"]) for row in cases if row["group"] == group])
        visible = values[values >= xmin]
        violin = ax_b.violinplot(
            visible,
            positions=[y_pos + 0.08],
            vert=False,
            widths=0.55,
            showmeans=False,
            showmedians=False,
            showextrema=False,
        )
        for body in violin["bodies"]:
            vertices = body.get_paths()[0].vertices
            vertices[:, 1] = np.maximum(vertices[:, 1], y_pos + 0.08)
            body.set_facecolor(color)
            body.set_edgecolor("none")
            body.set_alpha(0.32)
        ax_b.boxplot(
            visible,
            positions=[y_pos + 0.08],
            vert=False,
            widths=0.10,
            patch_artist=True,
            showfliers=False,
            boxprops={"facecolor": "white", "edgecolor": "#222222", "linewidth": 0.7},
            medianprops={"color": "#222222", "linewidth": 0.8},
            whiskerprops={"color": "#555555", "linewidth": 0.7},
            capprops={"color": "#555555", "linewidth": 0.7},
        )
        jitter = rng.uniform(-0.055, 0.055, size=len(visible))
        ax_b.scatter(visible, y_pos - 0.13 + jitter, s=8, color=color, alpha=0.65, edgecolor="none")
        clipped = values[values < xmin]
        if len(clipped):
            ax_b.scatter(
                np.full(len(clipped), xmin + 1.0),
                y_pos - 0.13 + rng.uniform(-0.05, 0.05, size=len(clipped)),
                marker="<",
                s=22,
                color=mean_color,
                alpha=0.85,
                clip_on=False,
            )
        info = summary[group]
        mean_value = float(info["mean_gain_percent"])
        ci_low = float(info["ci_low_percent"])
        ci_high = float(info["ci_high_percent"])
        ax_b.errorbar(
            mean_value,
            y_pos + 0.26,
            xerr=np.asarray([[mean_value - ci_low], [ci_high - mean_value]]),
            fmt="D",
            color=mean_color,
            mfc=mean_color,
            capsize=2.5,
            lw=0.9,
            ms=4.2,
        )
        ax_b.text(ci_high + 1.7, y_pos + 0.26, f"{mean_value:.2f}", va="center", fontsize=6.5)
    ax_b.axvline(0, color="#0072B2", ls=(0, (3, 2)), lw=0.8)
    ax_b.set_yticks(y_positions, labels)
    ax_b.set_xlim(-25, 75)
    ax_b.set_xticks((-20, 0, 20, 40, 60))
    ax_b.set_ylim(-0.58, 3.58)
    ax_b.set_xlabel("MSE reduction relative to the matched reference (%)")
    ax_b.text(-24.2, -0.50, "4 cases below -25% (minimum -360.3%)", fontsize=6.2)
    ax_b.grid(axis="x", color="#D4D4D4", lw=0.45, ls=(0, (2, 2)))
    ax_b.spines[["top", "right"]].set_visible(False)
    fig.text(0.265, 0.07, "(a) Source-center scale", ha="center", fontsize=7.2)
    fig.text(0.75, 0.07, "(b) Case-level gain distributions", ha="center", fontsize=7.2)
    return _save(fig, output_dir, "fig12")


def plot_all(data_dir: str | Path, output_dir: str | Path) -> dict[str, dict[str, Any]]:
    data = Path(data_dir).resolve()
    output = Path(output_dir).resolve()
    return {
        "fig6": plot_fig6(data, output),
        "fig7": plot_fig7(data, output),
        "fig8": plot_fig8(data, output),
        "fig9": plot_fig9(data, output),
        "fig10": plot_fig10(data, output),
        "fig11": plot_fig11(data, output),
        "fig12": plot_fig12(data, output),
    }


__all__ = [
    "FIGURE_SIZES",
    "plot_all",
    "plot_fig6",
    "plot_fig7",
    "plot_fig8",
    "plot_fig9",
    "plot_fig10",
    "plot_fig11",
    "plot_fig12",
]
