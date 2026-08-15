"""Archive and repository hygiene guard for public releases.

The check is path/file-name based by design: it must catch internal
review/revision artifacts without failing on legitimate scientific prose such
as the word "review" inside a bibliography title or a module named
``prior_response_profile``.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

FORBIDDEN_NAME_FRAGMENTS = (
    "CODEX",
    "REREVIEW",
    "RESPONSE_DRAFT",
    "REVISION_MATRIX",
    "PATCH_TEST",
    "FINAL_REVISION_EXECUTION_REPORT",
    "PRE_SUBMISSION_ENHANCEMENTS_README",
    "ARS_REREVIEW",
    "FINAL_REVIEW_RESPONSE",
    "R1_R8",
    "REVIEW_ROUND",
)
FORBIDDEN_PATH_SEGMENTS = (
    "experiments/review_round/",
)


def _hit(name: str) -> str | None:
    normalized = name.replace("\\", "/")
    upper = normalized.upper()
    for fragment in FORBIDDEN_NAME_FRAGMENTS:
        if fragment in upper:
            return f"forbidden name fragment {fragment!r}"
    for segment in FORBIDDEN_PATH_SEGMENTS:
        if segment in normalized:
            return f"forbidden path segment {segment!r}"
    return None


def check_archive(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"archive not found: {path}"]
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    except Exception as exc:
        return [f"cannot read archive {path}: {exc}"]
    for name in sorted(names):
        reason = _hit(name)
        if reason is not None:
            errors.append(f"{name}: {reason}")
    return errors


def check_tracked_paths(root: Path) -> list[str]:
    """Check path names of all Git-tracked files in the repository tree."""
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    names = result.stdout.decode("utf-8", errors="replace").split("\0")
    errors: list[str] = []
    for name in sorted(n for n in names if n):
        reason = _hit(name)
        if reason is not None:
            errors.append(f"{name}: {reason}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", nargs="*", type=Path, help="release archives to inspect")
    parser.add_argument(
        "--repository",
        type=Path,
        help="repository root whose tracked path names are inspected",
    )
    args = parser.parse_args()

    errors: list[str] = []
    for path in args.archive:
        errors.extend(check_archive(path))
    if args.repository is not None:
        errors.extend(check_tracked_paths(args.repository))

    if errors:
        print("RELEASE-HYGIENE: FAIL")
        for error in errors:
            print(error)
        return 1
    print("RELEASE-HYGIENE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
