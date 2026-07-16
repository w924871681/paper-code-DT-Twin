from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_asset_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"asset", "release_filename", "sha256", "required"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Invalid asset manifest columns")
    for row in rows:
        if len(row["sha256"]) != 64:
            raise ValueError(f"Invalid SHA-256 for {row['asset']}")
    return rows


def verify_asset_directory(asset_dir: Path) -> dict[str, Any]:
    asset_dir = asset_dir.resolve()
    rows = load_asset_manifest(ROOT / "assets/model_assets.csv")
    records = []
    failure_count = 0
    expected_names = set()
    for row in rows:
        name = row["release_filename"]
        expected_names.add(name)
        path = asset_dir / name
        if not path.is_file():
            status = "MISSING"
        elif _sha256(path).lower() != row["sha256"].lower():
            status = "MISMATCH"
        else:
            status = "OK"
        if status != "OK" and row["required"].lower() in {"yes", "true", "1"}:
            failure_count += 1
        records.append({"filename": name, "status": status})
    extras = sorted(path.name for path in asset_dir.glob("*") if path.is_file() and path.name not in expected_names) if asset_dir.is_dir() else []
    return {"asset_dir": str(asset_dir), "records": records, "extras": extras, "failure_count": failure_count}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify model-asset filenames and SHA-256 digests.")
    parser.add_argument("--asset-dir", type=Path, required=True)
    args = parser.parse_args()
    result = verify_asset_directory(args.asset_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["failure_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
