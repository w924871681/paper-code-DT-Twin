from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets/level_c_bootstrap_files.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_manifest(path: Path = MANIFEST) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "artifact", "source_relative_path", "archive_relative_path",
        "destination_relative_path", "sha256", "purpose",
    }
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Invalid Level-C bootstrap manifest columns")
    for row in rows:
        if len(row["sha256"]) != 64:
            raise ValueError(f"Invalid SHA-256 for {row['artifact']}")
        for field in ("source_relative_path", "archive_relative_path", "destination_relative_path"):
            value = Path(row[field])
            if value.is_absolute() or ".." in value.parts:
                raise ValueError(f"Non-portable {field} for {row['artifact']}")
    return rows


def verify_bundle(bundle_root: Path) -> dict[str, Any]:
    root = bundle_root.resolve()
    records: list[dict[str, str]] = []
    failures = 0
    for row in load_manifest():
        path = root / Path(row["archive_relative_path"])
        if not path.is_file():
            status = "MISSING"
        elif sha256(path).lower() != row["sha256"].lower():
            status = "MISMATCH"
        else:
            status = "OK"
        failures += status != "OK"
        records.append({"artifact": row["artifact"], "status": status})
    return {
        "decision": "PASS_LEVEL_C_BOOTSTRAP" if failures == 0 else "FAIL_LEVEL_C_BOOTSTRAP",
        "bundle_root": str(root), "file_count": len(records),
        "failure_count": failures, "records": records,
    }


def build_bundle(source_root: Path, bundle_root: Path) -> dict[str, Any]:
    source = source_root.resolve()
    bundle = bundle_root.resolve()
    records: list[dict[str, Any]] = []
    for row in load_manifest():
        src = source / Path(row["source_relative_path"])
        if not src.is_file():
            raise FileNotFoundError(src)
        actual = sha256(src)
        if actual.lower() != row["sha256"].lower():
            raise ValueError(f"Source hash mismatch for {row['artifact']}: {src}")
        dst = bundle / Path(row["archive_relative_path"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        records.append({
            "artifact": row["artifact"], "archive_relative_path": row["archive_relative_path"],
            "destination_relative_path": row["destination_relative_path"],
            "sha256": actual, "bytes": dst.stat().st_size,
        })
    metadata = {
        "schema": "level-c-bootstrap-v1", "release": "v1.1.2",
        "scope": "frozen main-evaluation replay prerequisites",
        "file_count": len(records), "files": records,
        "note": "Alibaba Cluster Trace v2018 is not redistributed in this bundle.",
    }
    (bundle / "bootstrap_manifest.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    shutil.copy2(MANIFEST, bundle / MANIFEST.name)
    return verify_bundle(bundle)


def stage_bundle(bundle_root: Path, project_root: Path, verify_only: bool = False) -> dict[str, Any]:
    bundle_check = verify_bundle(bundle_root)
    if bundle_check["failure_count"]:
        return bundle_check
    project = project_root.resolve()
    records: list[dict[str, str]] = []
    for row in load_manifest():
        src = bundle_root.resolve() / Path(row["archive_relative_path"])
        dst = project / Path(row["destination_relative_path"])
        if verify_only:
            status = "VERIFIED_NOT_STAGED"
        elif dst.is_file() and sha256(dst).lower() == row["sha256"].lower():
            status = "ALREADY_PRESENT"
        else:
            if dst.exists():
                raise ValueError(f"Refusing to overwrite mismatched destination: {dst}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            status = "STAGED"
        records.append({"artifact": row["artifact"], "status": status, "destination": str(dst)})
    return {
        "decision": "PASS_LEVEL_C_BOOTSTRAP_STAGE",
        "verify_only": verify_only, "file_count": len(records), "records": records,
    }
