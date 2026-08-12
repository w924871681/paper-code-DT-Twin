"""Regenerate Supplementary Fig. 11 with terminology-only corrections."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reporting.final_figures import CANVAS_SIZES, plot_fig9


def main() -> int:
    # Match the established Fig. 11 aspect ratio; all other plotting settings
    # are inherited verbatim from the canonical configuration-analysis plot.
    CANVAS_SIZES["fig9"] = (7.85, 2.80)
    audit = plot_fig9(
        ROOT / "results" / "figure_data",
        ROOT / "paper" / "figures",
        output_stem="fig11",
    )
    print(json.dumps(audit, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
