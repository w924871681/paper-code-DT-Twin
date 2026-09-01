"""Regenerate the canonical Supplementary Fig. 11 configuration analysis."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reporting.final_figures import plot_fig11


def main() -> int:
    audit = plot_fig11(
        ROOT / "results" / "figure_data",
        ROOT / "paper" / "figures",
    )
    print(json.dumps(audit, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
