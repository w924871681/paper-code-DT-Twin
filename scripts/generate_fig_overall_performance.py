"""Regenerate the current manuscript Figure 5 from canonical frozen results."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reporting.overall_performance import generate_overall_performance


def main() -> None:
    generate_overall_performance(
        ROOT / "results" / "main" / "overall_comparison.csv",
        ROOT / "paper" / "figures",
        png_dpi=300,
    )


if __name__ == "__main__":
    main()
