"""Build the public complete-archive from an explicit allowlist.

Only Git-tracked files are packaged, so a dirty or untracked working tree can
never leak into a release archive. The archive is checked by the release
hygiene guard and a SHA256 sidecar plus SHA256SUMS.txt are emitted next to it.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_release_hygiene import check_archive

ALLOWLIST = (
    # manuscript and supplementary sources and PDFs
    "paper/manuscript.pdf",
    "paper/manuscript.tex",
    "paper/supplementary.pdf",
    "paper/supplementary.tex",
    "paper/figures/",
    "paper/tables/",
    "paper_assets/current_figures/",
    # full frozen scientific result set and provenance
    "results/README.md",
    "results/main/",
    "results/figure_data/",
    "results/robustness/",
    "results/supplementary/",
    "results/pre_submission_enhancements/",
    "results/audited_provenance/",
    "results/h_meta_nas_recovery_v1/",
    # frozen protocol, code, and experiments (review-round excluded)
    "configs/",
    "core/",
    "anchor_safe_selector/",
    "source_prior_bank/",
    "main_evaluation/",
    "shared/",
    "experiments/__init__.py",
    "experiments/h_meta_nas_recovery.py",
    "experiments/main/",
    "experiments/robustness/",
    "experiments/supplementary/",
    "experiments/pre_submission/",
    "reporting/",
    "scripts/",
    "tests/",
    # public documentation allowlist
    "docs/DATA_AVAILABILITY.md",
    "docs/FIGURE_REPRODUCTION.md",
    "docs/INTERNAL_PROVENANCE_NAMES.md",
    "docs/METHOD.md",
    "docs/PAPER_RESULT_MAPPING.md",
    "docs/REPRODUCIBILITY.md",
    # data documentation and frozen split manifest
    "data/README.md",
    "data/alibaba2018/README.md",
    "data/synthetic/",
    # public metadata, provenance, and assets
    "README.md",
    "CITATION.cff",
    "LICENSE",
    "CHANGELOG.md",
    "RELEASE_NOTES_v1.2.5.md",
    "FILE_INDEX.csv",
    "COPY_MAP.csv",
    "RESTRUCTURE_REPORT.json",
    "assets/",
    "audit/",
    "environment.yml",
    "requirements.txt",
    "pyproject.toml",
)

REQUIRED_SENTINELS = (
    "paper/manuscript.pdf",
    "paper/supplementary.pdf",
    "results/main/",
    "results/figure_data/",
    "results/robustness/",
    "results/supplementary/",
    "results/pre_submission_enhancements/",
    "results/audited_provenance/",
    "docs/DATA_AVAILABILITY.md",
    "docs/REPRODUCIBILITY.md",
    "FILE_INDEX.csv",
)


def tracked_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return [n for n in result.stdout.decode("utf-8", errors="replace").split("\0") if n]


def blob_bytes(root: Path, name: str) -> bytes:
    """Read a path's committed blob bytes, independent of checkout EOL settings."""
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"HEAD:{name}"],
        check=True,
        capture_output=True,
    )
    return result.stdout


def ensure_clean_tagged_head(root: Path, version: str) -> list[str]:
    errors: list[str] = []
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        check=True,
        capture_output=True,
    )
    if status.stdout:
        errors.append("working tree is not clean; refusing to package uncommitted content")
    describe = subprocess.run(
        ["git", "-C", str(root), "describe", "--exact-match", "HEAD"],
        check=True,
        capture_output=True,
    )
    tag = describe.stdout.decode("utf-8", errors="replace").strip()
    if tag != version:
        errors.append(f"HEAD is not exactly tagged {version!r} (got {tag!r})")
    return errors


def _matches(name: str) -> bool:
    for entry in ALLOWLIST:
        if entry.endswith("/"):
            if name.startswith(entry):
                return True
        elif name == entry:
            return True
    return False


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--version", required=True, help="release tag, e.g. v1.2.5")
    args = parser.parse_args()

    root = ROOT
    args.out_dir.mkdir(parents=True, exist_ok=True)
    archive_path = args.out_dir / f"msa_dti_{args.version}_complete.zip"

    guard_errors = ensure_clean_tagged_head(root, args.version)
    if guard_errors:
        print("RELEASE-PACKAGE: FAIL")
        for error in guard_errors:
            print(error)
        return 1

    selected = sorted(name for name in tracked_files(root) if _matches(name))
    missing_sentinels = [
        sentinel
        for sentinel in REQUIRED_SENTINELS
        if not any(
            name == sentinel if not sentinel.endswith("/") else name.startswith(sentinel)
            for name in selected
        )
    ]
    if missing_sentinels:
        print("RELEASE-PACKAGE: FAIL")
        for sentinel in missing_sentinels:
            print(f"missing required archive content: {sentinel}")
        return 1

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in selected:
            archive.writestr(name, blob_bytes(root, name))

    hygiene = check_archive(archive_path)
    if hygiene:
        print("RELEASE-PACKAGE: FAIL")
        for error in hygiene:
            print(error)
        return 1

    digest = sha256(archive_path)
    sidecar = archive_path.with_name(archive_path.name + ".sha256")
    sidecar.write_text(f"{digest}  {archive_path.name}\n", encoding="utf-8")
    sums_path = args.out_dir / "SHA256SUMS.txt"
    sums_path.write_text(f"{digest}  {archive_path.name}\n", encoding="utf-8")

    print(f"RELEASE-PACKAGE: PASS")
    print(f"archive: {archive_path}")
    print(f"entries: {len(selected)}")
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
