# -*- coding: utf-8 -*-
"""Rebuild current-manuscript Fig. 6--12 from public derived CSV files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reporting.final_figures import plot_all


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "results/figure_data")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/reproducible_figures")
    args = parser.parse_args()
    result = plot_all(args.data_dir, args.output_dir)
    print(json.dumps(result, indent=2))
    print("PASS_REPRODUCIBLE_FIGURES_6_TO_12")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
