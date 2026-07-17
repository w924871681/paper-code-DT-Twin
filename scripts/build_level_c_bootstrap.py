from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.level_c_bootstrap import build_bundle, sha256


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the checksum-bound Level-C bootstrap directory and archive.")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--zip", action="store_true", dest="make_zip")
    args = parser.parse_args()
    result = build_bundle(args.source_root, args.bundle_root)
    if args.make_zip:
        archive = Path(shutil.make_archive(str(args.bundle_root.resolve()), "zip", root_dir=args.bundle_root.resolve()))
        result["zip"] = str(archive)
        result["zip_sha256"] = sha256(archive)
        result["zip_bytes"] = archive.stat().st_size
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["failure_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
