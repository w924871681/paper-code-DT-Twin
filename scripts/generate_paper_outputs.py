# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reporting import generate


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild released paper tables and figures from frozen CSV/JSON sources."
    )
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--output-root", default="outputs/paper_outputs")
    args = parser.parse_args()
    result = generate(args.project_root, args.output_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("PASS_FROZEN_TABLES_AND_FIGURES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
