from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from scripts.level_c_bootstrap import ROOT, stage_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify and stage a Level-C bootstrap bundle into repository-relative paths.")
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = stage_bundle(args.bundle_root, args.project_root, args.verify_only)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["decision"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
