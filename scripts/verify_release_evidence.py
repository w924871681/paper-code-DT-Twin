from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import zipfile
from pathlib import Path


REQUIRED_FILES = {
    "README.md",
    "CUDA_ENVIRONMENT.json",
    "CUDA_REPLAY_LEDGER.json",
    "HISTORICAL_OUTPUT_COMPARISON.json",
    "CODE_MANIFEST.json",
    "OUTPUT_MANIFEST.json",
    "SHA256SUMS.txt",
}
REQUIRED_DIRS = {"logs", "preflight", "methods", "analysis", "audit"}
SCANNED_SUFFIXES = {".json", ".csv", ".md", ".txt", ".log", ".cff"}
PRIVATE_PATTERNS = {
    "drive_absolute_path": re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]"),
    "linux_home": re.compile(r"/home/[^/\s]+/", re.IGNORECASE),
    "macos_users": re.compile(r"/Users/[^/\s]+/", re.IGNORECASE),
    "windows_user": re.compile(r"C:\\Users\\", re.IGNORECASE),
    "d_drive": re.compile(r"D:\\", re.IGNORECASE),
    "classic_github_token": re.compile(r"ghp_", re.IGNORECASE),
    "fine_grained_github_token": re.compile(r"github_pat_", re.IGNORECASE),
    "password_assignment": re.compile(r"password\s*[:=]", re.IGNORECASE),
    "token_assignment": re.compile(r"token\s*[:=]", re.IGNORECASE),
    "recovery_secret": re.compile(r"recovery", re.IGNORECASE),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    destination = destination.resolve()
    for member in archive.infolist():
        target = (destination / member.filename).resolve()
        if destination not in target.parents and target != destination:
            raise RuntimeError(f"Unsafe ZIP member: {member.filename}")
    archive.extractall(destination)


def _archive_root(extracted: Path) -> Path:
    entries = list(extracted.iterdir())
    if len(entries) != 1 or not entries[0].is_dir():
        raise RuntimeError("Evidence ZIP must contain exactly one top-level directory")
    return entries[0]


def _verify_checksums(root: Path) -> None:
    for line in (root / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split(None, 1)
        relative = relative.strip().lstrip("*")
        path = root / relative
        if not path.is_file() or _sha256(path) != expected.lower():
            raise RuntimeError(f"Checksum mismatch: {relative}")

    manifest = json.loads((root / "OUTPUT_MANIFEST.json").read_text(encoding="utf-8"))
    for item in manifest.get("files", []):
        path = root / item["path"]
        if (
            not path.is_file()
            or path.stat().st_size != int(item["bytes"])
            or _sha256(path) != item["sha256"]
        ):
            raise RuntimeError(f"Output manifest mismatch: {item['path']}")


def _verify_privacy(root: Path) -> None:
    findings: list[str] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.suffix.lower() not in SCANNED_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in PRIVATE_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(root).as_posix()}:{name}")
    if findings:
        raise RuntimeError("Private values found in public evidence: " + ", ".join(findings))


def verify_release_evidence(zip_path: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="verify-release-evidence-") as temp:
        extracted = Path(temp)
        with zipfile.ZipFile(zip_path) as archive:
            _safe_extract(archive, extracted)
        root = _archive_root(extracted)
        missing_files = sorted(name for name in REQUIRED_FILES if not (root / name).is_file())
        missing_dirs = sorted(name for name in REQUIRED_DIRS if not (root / name).is_dir())
        if missing_files or missing_dirs:
            raise RuntimeError(f"Missing evidence structure: files={missing_files}, dirs={missing_dirs}")

        for path in root.rglob("*.json"):
            json.loads(path.read_text(encoding="utf-8"))
        ledger = json.loads((root / "CUDA_REPLAY_LEDGER.json").read_text(encoding="utf-8"))
        comparison = json.loads(
            (root / "HISTORICAL_OUTPUT_COMPARISON.json").read_text(encoding="utf-8")
        )
        if ledger.get("decision") != "PASS_FROZEN_MAIN_EVALUATION_REPLAY":
            raise RuntimeError("Formal replay PASS decision is missing")
        if comparison.get("decision") != "PASS_HISTORICAL_OUTPUT_COMPARISON":
            raise RuntimeError("Historical comparison PASS decision is missing")
        _verify_checksums(root)
        _verify_privacy(root)
        return {
            "schema": "release-evidence-verification-v1",
            "archive": zip_path.name,
            "bytes": zip_path.stat().st_size,
            "sha256": _sha256(zip_path),
            "decision": "PASS_RELEASE_EVIDENCE_VERIFICATION",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a sanitized CUDA replay Release ZIP.")
    parser.add_argument("zip_path", type=Path)
    args = parser.parse_args()
    report = verify_release_evidence(args.zip_path.resolve())
    print("PASS_RELEASE_EVIDENCE_STRUCTURE")
    print("PASS_RELEASE_EVIDENCE_CHECKSUMS")
    print("PASS_RELEASE_EVIDENCE_PRIVACY")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
