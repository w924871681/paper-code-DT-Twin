"""Backward-compatible import shim for the v1.1.7 final figure module.

New code must import :mod:`reporting.final_figures`.  This module intentionally
contains no plotting implementation.
"""

from .final_figures import (
    FIGURE_SIZES,
    plot_all,
    plot_fig6,
    plot_fig7,
    plot_fig8,
    plot_fig9,
    plot_fig10,
    plot_fig11,
    plot_fig12,
)

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
