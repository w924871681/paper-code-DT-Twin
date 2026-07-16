from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reporting.frozen import validate_output


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Level-B figures and exact revised-paper tables.")
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs/paper_outputs")
    args = parser.parse_args()
    result = validate_output(args.output_root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("PASS_PAPER_OUTPUT_VALIDATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
