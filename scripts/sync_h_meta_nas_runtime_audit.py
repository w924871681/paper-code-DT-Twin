"""Publish the frozen H-Meta-NAS five-repeat runtime audit.

The source audit remains under ``outputs/``.  This script validates the
completed 5 x 80 audit, writes privacy-safe public evidence, and replaces only
the H-Meta-NAS rows in the canonical repeated-runtime presentation layer.
It never runs training, search, adaptation, or test evaluation.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SOURCE = ROOT / "outputs/h_meta_nas_five_repeat_frozen_target_side_runtime_audit"
PUBLIC = ROOT / "results/supplementary/h_meta_nas_runtime_audit"
SUMMARY_PATH = SOURCE / "h_meta_nas_five_repeat_runtime_summary.json"

JSON_ARTIFACTS = (
    "h_meta_nas_five_repeat_runtime_raw.json",
    "h_meta_nas_five_repeat_runtime_summary.json",
    "legacy_43_061_protocol_compatibility_audit.json",
    "protocol_amendments_and_execution_events.json",
)
COPY_ARTIFACTS = (
    "per_case_runtime_all_repeats.csv",
    "per_repeat_80_case_runtime.csv",
    "five_repeat_summary.csv",
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sanitize_string(value: str) -> str:
    replacements = {
        str(ROOT): "<repository>",
        str(ROOT).replace("\\", "/"): "<repository>",
    }
    for source, replacement in replacements.items():
        value = value.replace(source, replacement)
    return re.sub(
        r"(?i)[A-Z]:\\Users\\[^\\]+\\anaconda3\\envs\\rcf-dti-py311\\python\.exe",
        "python (rcf-dti-py311 environment)",
        value,
    )


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "<redacted-host>" if key == "hostname" else _sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        return _sanitize_string(value)
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate(summary: dict[str, Any], cases: list[dict[str, str]]) -> None:
    if summary.get("decision") != "PASS_H_META_NAS_FIVE_REPEAT_FROZEN_RUNTIME_AUDIT":
        raise ValueError("H-Meta-NAS audit decision is not PASS")
    if not summary.get("complete") or not summary.get("performance_unchanged"):
        raise ValueError("H-Meta-NAS audit or frozen-performance verification is incomplete")
    if (summary.get("N_repeats"), summary.get("N_cases_per_repeat"), summary.get("N_observations")) != (5, 80, 400):
        raise ValueError("H-Meta-NAS audit is not exactly 5 x 80")
    if len(cases) != 400:
        raise ValueError("H-Meta-NAS case-level audit does not contain 400 records")
    counts = {repeat: sum(int(row["repeat"]) == repeat for row in cases) for repeat in range(1, 6)}
    if counts != {1: 80, 2: 80, 3: 80, 4: 80, 5: 80}:
        raise ValueError(f"H-Meta-NAS repeat counts changed: {counts}")
    if any(row["selection_uses_check"] != "False" or row["selection_uses_test"] != "False" or row["test_evaluation_timed"] != "False" for row in cases):
        raise ValueError("H-Meta-NAS timing includes prohibited check/test selection or test timing")


def _publish_evidence(summary: dict[str, Any]) -> dict[str, str]:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    for name in COPY_ARTIFACTS:
        shutil.copyfile(SOURCE / name, PUBLIC / name)
    for name in JSON_ARTIFACTS:
        obj = json.loads((SOURCE / name).read_text(encoding="utf-8"))
        _write_json(PUBLIC / name, _sanitize(obj))

    report = _sanitize_string((SOURCE / "AUDIT_REPORT.md").read_text(encoding="utf-8"))
    (PUBLIC / "AUDIT_REPORT.md").write_text(report, encoding="utf-8")

    hashes = {path.name: _sha256(path) for path in sorted(PUBLIC.iterdir()) if path.is_file()}
    manifest = {
        "title": "H-Meta-NAS five-repeat frozen target-side runtime audit",
        "decision": summary["decision"],
        "canonical_paper_runtime_seconds_per_case": {
            "mean": summary["five_repeat_mean_seconds"],
            "sample_standard_deviation_across_repeat_means": summary["five_repeat_std_seconds"],
            "repeats": 5,
            "cases_per_repeat": 80,
        },
        "frozen_performance_unchanged": True,
        "legacy_43_061_seconds_counted": False,
        "legacy_exclusion_reason": "Incompatible timing scope, held-out test inclusion, and CUDA synchronization procedure.",
        "verification_tolerance": summary["performance_verification_tolerance"],
        "protocol_amendments_recorded": True,
        "public_artifact_sha256": hashes,
    }
    manifest_path = ROOT / "results/audited_provenance/h_meta_nas_runtime_audit_manifest.json"
    _write_json(manifest_path, manifest)
    return hashes


def _sync_runtime_tables(summary: dict[str, Any], cases: list[dict[str, str]]) -> None:
    runtime_dir = ROOT / "results/supplementary"
    raw_path = runtime_dir / "repeated_runtime_raw.csv"
    raw_rows = [row for row in _read_csv(raw_path) if row["method"] != "h_meta_nas"]
    for row in cases:
        raw_rows.append(
            {
                "complete": row["complete"],
                "repeat": row["repeat"],
                "method": "h_meta_nas",
                "case_key": row["case_key"],
                "center_id": row["center_id"],
                "center_type": row["center_type"],
                "budget_tier": row["budget_tier"],
                "H": row["H"],
                "K": row["K"],
                "online_seconds": row["online_seconds"],
                "candidate_count": row["candidate_count"],
                "adapted_candidate_count": row["adapted_candidate_count"],
                "selected_arch_idx": row["selected_arch_idx"],
                "target_seed": row["target_seed"],
                "cuda_synchronized": row["cuda_synchronized_before_and_after"],
                "test_used": row["selection_uses_test"],
                "check_used": row["selection_uses_check"],
            }
        )
    raw_rows.sort(key=lambda row: (int(row["repeat"]), row["method"], row["case_key"]))
    _write_csv(raw_path, raw_rows, list(raw_rows[0]))

    values = np.asarray([float(row["online_seconds"]) for row in cases], dtype=float)
    repeat_means = [
        float(np.mean([float(row["online_seconds"]) for row in cases if int(row["repeat"]) == repeat]))
        for repeat in range(1, 6)
    ]
    h_row = {
        "method": "h_meta_nas",
        "N_observations": 400,
        "N_repeats": 5,
        "mean_seconds": float(values.mean()),
        "std_seconds": float(values.std(ddof=1)),
        "median_seconds": float(np.median(values)),
        "q1_seconds": float(np.quantile(values, 0.25)),
        "q3_seconds": float(np.quantile(values, 0.75)),
        "min_seconds": float(values.min()),
        "max_seconds": float(values.max()),
        "repeat_mean_std_seconds": float(np.std(repeat_means, ddof=1)),
        "adapted_candidates_mean": float(np.mean([float(row["adapted_candidate_count"]) for row in cases])),
    }
    if not np.isclose(h_row["mean_seconds"], summary["five_repeat_mean_seconds"], rtol=0, atol=1e-12):
        raise ValueError("case-level H-Meta-NAS mean disagrees with audit summary")

    summary_csv = runtime_dir / "repeated_runtime_summary.csv"
    summary_rows = [row for row in _read_csv(summary_csv) if row["method"] != "h_meta_nas"]
    summary_rows.append(h_row)
    _write_csv(summary_csv, summary_rows, list(summary_rows[0]))

    repeat_path = runtime_dir / "repeated_runtime_repeat_means.csv"
    repeat_rows = [row for row in _read_csv(repeat_path) if row["method"] != "h_meta_nas"]
    for source_row in summary["repeat_results"]:
        repeat_rows.append(
            {
                "method": "h_meta_nas",
                "repeat": source_row["repeat"],
                "N_cases": source_row["N_cases"],
                "mean_seconds": source_row["mean_seconds"],
                "median_seconds": source_row["median_case_seconds"],
            }
        )
    repeat_rows.sort(key=lambda row: (row["method"], int(row["repeat"])))
    _write_csv(repeat_path, repeat_rows, list(repeat_rows[0]))

    summary_json_path = runtime_dir / "repeated_runtime_summary.json"
    combined = json.loads(summary_json_path.read_text(encoding="utf-8"))
    combined["summary"] = [row for row in combined["summary"] if row["method"] != "h_meta_nas"] + [h_row]
    combined["method_environments"] = {
        "h_meta_nas": _sanitize(summary["environment"]),
    }
    combined["method_timer_scopes"] = {"h_meta_nas": summary["timer_scope"]}
    combined["h_meta_nas_audit"] = {
        "decision": summary["decision"],
        "frozen_performance_unchanged": True,
        "verification_rtol": summary["performance_verification_tolerance"]["rtol"],
        "legacy_43_061_seconds_counted": False,
        "public_evidence": "results/supplementary/h_meta_nas_runtime_audit/",
    }
    _write_json(summary_json_path, combined)

    overall_path = ROOT / "results/main/overall_comparison.csv"
    overall = _read_csv(overall_path)
    for row in overall:
        if row["Method"] == "H-Meta-NAS":
            row["OnlineSeconds"] = str(h_row["mean_seconds"])
    _write_csv(overall_path, overall, list(overall[0]))

    tradeoff_path = ROOT / "results/figure_data/fig10_deployment_tradeoff_data.csv"
    tradeoff = _read_csv(tradeoff_path)
    for row in tradeoff:
        if row["method"] == "H-Meta-NAS":
            row["target_time_seconds"] = str(h_row["mean_seconds"])
    _write_csv(tradeoff_path, tradeoff, list(tradeoff[0]))

    # Rebuild the two presentation tables that expose runtime.  Import only
    # after the canonical source files above have been replaced.
    from reporting.frozen import public_table_rows

    public = public_table_rows(ROOT)
    for name in ("table3_overall_comparison", "table5b_online_cost"):
        rows = public[name]
        _write_csv(ROOT / f"results/figure_data/{name}.csv", rows, list(rows[0]))


def main() -> int:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    cases = _read_csv(SOURCE / "per_case_runtime_all_repeats.csv")
    _validate(summary, cases)
    _publish_evidence(summary)
    _sync_runtime_tables(summary, cases)
    print("PASS_H_META_NAS_RUNTIME_AUDIT_SYNCHRONIZED")
    print(f"mean_seconds={summary['five_repeat_mean_seconds']}")
    print(f"repeat_mean_std_seconds={summary['five_repeat_std_seconds']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
