"""Create a provenance-bound, reporting-only H-Meta-NAS paired comparison.

This program reads two completed case-level result JSON files.  It does not
build models, load model weights, or evaluate predictions.  Its sole purpose
is to calculate paired test-WMSE gains and a center-cluster bootstrap interval.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HMETA = ROOT / "results" / "h_meta_nas_recovery_v1" / "h_meta_nas_formal.json"
DEFAULT_OUTPUT = ROOT / "results" / "audited_provenance" / "h_meta_nas_paired_comparison_v1"
DEFAULT_SEED = 11905  # Existing frozen main-reporting bootstrap seed: 2904 + 9001.
BOOTSTRAP_REPEATS = 4000
EPSILON = 1e-12


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_records(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    if not payload.get("complete"):
        raise ValueError(f"Input is not complete: {path}")
    records = payload.get("records")
    if not isinstance(records, dict):
        raise ValueError(f"Missing record mapping: {path}")
    return records


def git_revision() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def git_is_dirty() -> bool | None:
    try:
        return bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True
            ).strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return None


def repository_relative(path: Path) -> str:
    """Record checkout-portable provenance paths whenever possible."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--msa-json", type=Path, required=True, help="Completed MSA-DTI case-level JSON")
    parser.add_argument("--hmeta-json", type=Path, default=DEFAULT_HMETA, help="Completed H-Meta-NAS formal JSON")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    msa_path = args.msa_json.resolve()
    hmeta_path = args.hmeta_json.resolve()
    output_dir = args.output_dir.resolve()
    msa = load_records(msa_path)
    hmeta = load_records(hmeta_path)
    msa_keys, hmeta_keys = set(msa), set(hmeta)
    if msa_keys != hmeta_keys:
        raise ValueError(
            "Case-key mismatch: "
            f"only_msa={sorted(msa_keys - hmeta_keys)}, "
            f"only_hmeta={sorted(hmeta_keys - msa_keys)}"
        )
    if len(msa_keys) != 80:
        raise ValueError(f"Expected 80 matched cases, found {len(msa_keys)}")

    gains_by_center: dict[int, list[float]] = defaultdict(list)
    rows: list[dict[str, Any]] = []
    wins = ties = losses = 0
    for case_key in sorted(msa_keys):
        msa_record, hmeta_record = msa[case_key], hmeta[case_key]
        identity = ("center_id", "H", "K")
        if any(msa_record.get(field) != hmeta_record.get(field) for field in identity):
            raise ValueError(f"Identity mismatch for {case_key}")
        mse_msa = float(msa_record["test"]["weighted_mse"])
        mse_hmeta = float(hmeta_record["test"]["weighted_mse"])
        if not np.isfinite(mse_msa) or not np.isfinite(mse_hmeta) or mse_hmeta <= 0:
            raise ValueError(f"Invalid test WMSE for {case_key}")
        gain = (mse_hmeta - mse_msa) / (abs(mse_hmeta) + EPSILON)
        center_id = int(msa_record["center_id"])
        gains_by_center[center_id].append(gain)
        if gain > 1e-6:
            wins += 1
        elif gain < -1e-6:
            losses += 1
        else:
            ties += 1
        rows.append(
            {
                "case_key": case_key,
                "center_id": center_id,
                "H": int(msa_record["H"]),
                "K": int(msa_record["K"]),
                "msa_dti_test_wmse": mse_msa,
                "h_meta_nas_test_wmse": mse_hmeta,
                "relative_mse_reduction": gain,
                "msa_dti_wins": int(gain > 1e-6),
            }
        )

    centers = sorted(gains_by_center)
    if len(centers) != 20 or any(len(gains_by_center[c]) != 4 for c in centers):
        raise ValueError("Expected 20 centers with four H/K cases each")
    center_gains = np.asarray([np.mean(gains_by_center[c]) for c in centers], dtype=np.float64)
    rng = np.random.default_rng(int(args.seed))
    draws = rng.integers(0, len(centers), size=(BOOTSTRAP_REPEATS, len(centers)))
    bootstrap = center_gains[draws].mean(axis=1)

    output_dir.mkdir(parents=True, exist_ok=False)
    csv_path = output_dir / "per_case_h_meta_nas_vs_msa_dti.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "study": "h_meta_nas_vs_msa_dti_paired_reporting_v1",
        "decision": "COMPLETE_REPORTING_ONLY",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "methods": {"A": "MSA-DTI", "B": "H-Meta-NAS"},
        "inputs": {
            "msa_dti_case_json": {"path": repository_relative(msa_path), "sha256": sha256(msa_path)},
            "h_meta_nas_case_json": {"path": repository_relative(hmeta_path), "sha256": sha256(hmeta_path)},
        },
        "case_keys": sorted(msa_keys),
        "paired_gain_formula": "(MSE_HMeta_i - MSE_MSA_i) / abs(MSE_HMeta_i)",
        "epsilon": EPSILON,
        "sampling": {
            "unit": "target_center",
            "center_count": len(centers),
            "case_count": len(rows),
            "cases_per_center": 4,
            "case_grouping": "all four H/K cases stay together in each sampled center",
            "bootstrap_repetitions": BOOTSTRAP_REPEATS,
            "seed": int(args.seed),
            "rng": "numpy.random.default_rng",
            "interval": "percentile [2.5th, 97.5th]",
        },
        "results": {
            "mse_win_rate": wins / len(rows),
            "wins": wins,
            "ties": ties,
            "losses": losses,
            "mean_paired_mse_reduction": float(np.mean([r["relative_mse_reduction"] for r in rows])),
            "median_paired_mse_reduction": float(np.median([r["relative_mse_reduction"] for r in rows])),
            "ci_low": float(np.quantile(bootstrap, 0.025)),
            "ci_high": float(np.quantile(bootstrap, 0.975)),
        },
        "producer": {
            "script": repository_relative(Path(__file__)),
            "script_sha256": sha256(Path(__file__).resolve()),
            "git_commit": git_revision(),
            "git_worktree_dirty": git_is_dirty(),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "command": " ".join([Path(sys.executable).name, *sys.argv]),
        },
        "outputs": {"per_case_csv": repository_relative(csv_path)},
    }
    manifest_path = output_dir / "h_meta_nas_vs_msa_dti_paired_manifest.json"
    with manifest_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
