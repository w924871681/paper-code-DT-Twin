from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.main.real_trace import build_real_bank


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Alibaba v2018 architecture-matched source bank.")
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--safe-mode", default="gru-native")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    result = build_real_bank(str(args.project_root.resolve()), str(args.manifest.resolve()), str(args.out_dir.resolve()), args.device, args.safe_mode, args.smoke)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("decision") == "PASS_REAL_SOURCE_BANK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
