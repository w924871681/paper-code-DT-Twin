from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import torch


METHODS = (
    "ours_c32_locked",
    "pt_ft",
    "medet_style",
    "scratch50",
    "meta_nas_lite",
    "zero_nas",
    "zero_nas_ft",
)
IDENTITY_FIELDS = ("case_key", "center_id", "H", "K", "budget_tier", "center_type", "target_seed", "method")
ARCHITECTURE_FIELDS = ("arch_idx", "arch_key", "family", "selector")
FEASIBILITY_FIELDS = (
    "feasible",
    "hard_feasible",
    "params",
    "flops",
    "candidate_count",
    "adapted_candidate_count",
    "max_online_gradient_steps_per_candidate",
)
METRIC_FIELDS = ("validation", "check", "test")
OVERALL_FIELDS = (
    "N_total",
    "N_feasible",
    "feasible_rate",
    "test_mse_mean",
    "test_mae_mean",
    "test_worst10_mean",
    "case_cvar90_mse",
    "params_mean",
    "flops_mean",
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run(*argv: str) -> str:
    completed = subprocess.run(argv, text=True, capture_output=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _same_selected(record_a: dict[str, Any], record_b: dict[str, Any], fields: tuple[str, ...]) -> bool:
    return all(record_a.get(field) == record_b.get(field) for field in fields)


def _same_numeric_tree(a: Any, b: Any, tolerance: float) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_same_numeric_tree(a[key], b[key], tolerance) for key in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same_numeric_tree(x, y, tolerance) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= tolerance
    return a == b


def compare_historical(historical_root: Path, current_root: Path) -> dict[str, Any]:
    tolerance = 1e-12
    method_checks: dict[str, Any] = {}
    for method in METHODS:
        historical_path = historical_root / "methods" / f"{method}.json"
        current_path = current_root / "methods" / f"{method}.json"
        historical = _load(historical_path)
        current = _load(current_path)
        historical_records = historical["records"]
        current_records = current["records"]
        keys_equal = set(historical_records) == set(current_records)
        identity_equal = keys_equal
        architecture_equal = keys_equal
        feasibility_equal = keys_equal
        metrics_equal = keys_equal
        non_timing_records_equal = keys_equal
        if keys_equal:
            for key in sorted(historical_records):
                old = historical_records[key]
                new = current_records[key]
                identity_equal &= _same_selected(old, new, IDENTITY_FIELDS)
                architecture_equal &= _same_selected(old, new, ARCHITECTURE_FIELDS)
                feasibility_equal &= _same_selected(old, new, FEASIBILITY_FIELDS)
                metrics_equal &= _same_selected(old, new, METRIC_FIELDS)
                old_without_time = {name: value for name, value in old.items() if name != "online_seconds"}
                new_without_time = {name: value for name, value in new.items() if name != "online_seconds"}
                non_timing_records_equal &= old_without_time == new_without_time
        passed = all(
            (
                keys_equal,
                len(historical_records) == len(current_records) == 80,
                identity_equal,
                architecture_equal,
                feasibility_equal,
                metrics_equal,
                non_timing_records_equal,
                current.get("run_mode") == "formal",
                current.get("decision") == "C33_LOCKED_METHOD_COMPLETE",
            )
        )
        method_checks[method] = {
            "historical_sha256": _sha256(historical_path),
            "current_sha256": _sha256(current_path),
            "record_count_historical": len(historical_records),
            "record_count_current": len(current_records),
            "case_identities_exact": keys_equal and identity_equal,
            "architectures_and_selection_exact": architecture_equal,
            "feasibility_and_complexity_exact": feasibility_equal,
            "validation_check_test_metrics_exact": metrics_equal,
            "all_non_timing_record_fields_exact": non_timing_records_equal,
            "runtime_fields_excluded_as_environment_dependent": True,
            "status": "PASS" if passed else "FAIL",
        }

    historical_analysis_path = historical_root / "analysis" / "c33_locked_analysis.json"
    current_analysis_path = current_root / "analysis" / "main_evaluation_analysis.json"
    historical_analysis = _load(historical_analysis_path)
    current_analysis = _load(current_analysis_path)
    old_overall = {row["method"]: row for row in historical_analysis["overall"]}
    new_overall = {row["method"]: row for row in current_analysis["overall"]}
    overall_checks: dict[str, Any] = {}
    for method in METHODS:
        fields = {
            field: {
                "historical": old_overall[method][field],
                "current": new_overall[method][field],
                "absolute_difference": abs(float(old_overall[method][field]) - float(new_overall[method][field])),
                "within_tolerance": abs(float(old_overall[method][field]) - float(new_overall[method][field])) <= tolerance,
            }
            for field in OVERALL_FIELDS
        }
        overall_checks[method] = {
            "fields": fields,
            "historical_online_seconds_mean": old_overall[method]["online_seconds_mean"],
            "current_online_seconds_mean": new_overall[method]["online_seconds_mean"],
            "runtime_excluded_as_environment_dependent": True,
            "status": "PASS" if all(item["within_tolerance"] for item in fields.values()) else "FAIL",
        }

    paired_equal = _same_numeric_tree(
        historical_analysis["paired_ours_vs_baselines"],
        current_analysis["paired_ours_vs_baselines"],
        tolerance,
    )
    selected_tokens_equal = historical_analysis["ours_selected_tokens"] == current_analysis["ours_selected_tokens"]
    passed = (
        all(item["status"] == "PASS" for item in method_checks.values())
        and all(item["status"] == "PASS" for item in overall_checks.values())
        and paired_equal
        and selected_tokens_equal
    )
    return {
        "schema": "historical-output-comparison-v1",
        "scope": "frozen locked main-evaluation replay",
        "historical_root": str(historical_root),
        "current_root": str(current_root),
        "absolute_tolerance": tolerance,
        "timing_policy": "online runtime is environment-dependent and is reported but excluded from equality",
        "method_records": method_checks,
        "overall_metrics": overall_checks,
        "paired_ours_vs_baselines_within_tolerance": paired_equal,
        "ours_selected_token_counts_exact": selected_tokens_equal,
        "historical_analysis_sha256": _sha256(historical_analysis_path),
        "current_analysis_sha256": _sha256(current_analysis_path),
        "decision": "PASS_HISTORICAL_OUTPUT_COMPARISON" if passed else "FAIL_HISTORICAL_OUTPUT_COMPARISON",
    }


def capture_environment(repo_root: Path, bootstrap_zip: Path, ledger: dict[str, Any]) -> dict[str, Any]:
    driver = _run(
        "nvidia-smi",
        "--query-gpu=name,driver_version,memory.total",
        "--format=csv,noheader,nounits",
    )
    gpu_name, driver_version, memory_mib = (part.strip() for part in driver.split(",", 2))
    exact_tag = _run("git", "-C", str(repo_root), "describe", "--tags", "--exact-match")
    worktree_status = _run("git", "-C", str(repo_root), "status", "--porcelain=v1")
    worktree_diff = _run("git", "-C", str(repo_root), "diff", "--binary", "HEAD")
    return {
        "schema": "cuda-replay-environment-v1",
        "operating_system": platform.platform(),
        "python_version": sys.version,
        "python_executable": sys.executable,
        "conda_environment": os.environ.get("CONDA_DEFAULT_ENV", ""),
        "torch_version": torch.__version__,
        "torch_cuda_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "torch_cuda_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0),
        "gpu_total_memory_bytes": torch.cuda.get_device_properties(0).total_memory,
        "nvidia_smi_gpu_name": gpu_name,
        "nvidia_driver_version": driver_version,
        "nvidia_smi_total_memory_mib": int(memory_mib),
        "git_commit": _run("git", "-C", str(repo_root), "rev-parse", "HEAD"),
        "git_branch": _run("git", "-C", str(repo_root), "branch", "--show-current"),
        "git_exact_tag": exact_tag or None,
        "git_worktree_dirty": bool(worktree_status),
        "git_worktree_status": worktree_status.splitlines(),
        "git_worktree_diff_sha256": hashlib.sha256(worktree_diff.encode("utf-8")).hexdigest(),
        "prepared_release": "v1.1.3",
        "published_bootstrap_release": "v1.1.2",
        "bootstrap_path": str(bootstrap_zip),
        "bootstrap_bytes": bootstrap_zip.stat().st_size,
        "bootstrap_sha256": _sha256(bootstrap_zip),
        "replay_started_at": ledger["started_at"],
        "replay_ended_at": ledger["ended_at"],
        "replay_device": ledger["device"],
        "source_training_repeated": ledger["source_training_repeated"],
    }


def copy_evidence(current_root: Path, replay_root: Path, archive_root: Path) -> None:
    shutil.copy2(replay_root / "frozen_main_evaluation_ledger.json", archive_root / "CUDA_REPLAY_LEDGER.json")
    for name in ("logs",):
        shutil.copytree(replay_root / name, archive_root / name, dirs_exist_ok=True)
    for name in ("preflight", "methods", "analysis", "audit"):
        shutil.copytree(current_root / name, archive_root / name, dirs_exist_ok=True)


def write_manifest(archive_root: Path) -> None:
    files = []
    for path in sorted(item for item in archive_root.rglob("*") if item.is_file()):
        if path.name in {"OUTPUT_MANIFEST.json", "SHA256SUMS.txt"}:
            continue
        files.append(
            {
                "path": path.relative_to(archive_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    (archive_root / "OUTPUT_MANIFEST.json").write_text(
        json.dumps({"schema": "cuda-replay-output-manifest-v1", "files": files}, indent=2) + "\n",
        encoding="utf-8",
    )
    checksum_files = sorted(item for item in archive_root.rglob("*") if item.is_file() and item.name != "SHA256SUMS.txt")
    lines = [f"{_sha256(path)}  {path.relative_to(archive_root).as_posix()}" for path in checksum_files]
    (archive_root / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare and archive a completed frozen CUDA replay.")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--historical-root", type=Path, required=True)
    parser.add_argument("--current-root", type=Path, required=True)
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--bootstrap-zip", type=Path, required=True)
    parser.add_argument("--archive-root", type=Path, required=True)
    args = parser.parse_args()
    paths = {name: value.resolve() for name, value in vars(args).items()}
    archive_root = paths["archive_root"]
    archive_root.mkdir(parents=True, exist_ok=True)

    ledger = _load(paths["replay_root"] / "frozen_main_evaluation_ledger.json")
    audit = _load(paths["current_root"] / "audit" / "c33_audit.json")
    if ledger.get("decision") != "PASS_FROZEN_MAIN_EVALUATION_REPLAY":
        raise RuntimeError("Replay ledger is not PASS_FROZEN_MAIN_EVALUATION_REPLAY")
    if audit.get("decision") != "PASS_C33_LOCKED_EVALUATION_COMPLETE_AND_AUDITED":
        raise RuntimeError("Formal audit did not pass")

    comparison = compare_historical(paths["historical_root"], paths["current_root"])
    if comparison["decision"] != "PASS_HISTORICAL_OUTPUT_COMPARISON":
        raise RuntimeError("Historical output comparison failed")
    environment = capture_environment(paths["repo_root"], paths["bootstrap_zip"], ledger)
    if not environment["torch_cuda_available"]:
        raise RuntimeError("CUDA is unavailable in the archival environment")

    copy_evidence(paths["current_root"], paths["replay_root"], archive_root)
    (archive_root / "CUDA_ENVIRONMENT.json").write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
    (archive_root / "HISTORICAL_OUTPUT_COMPARISON.json").write_text(
        json.dumps(comparison, indent=2) + "\n", encoding="utf-8"
    )
    (archive_root / "README.md").write_text(
        "# CUDA frozen main-evaluation replay archive\n\n"
        "The public bootstrap was verified and staged, all seven frozen methods ran on CUDA, "
        "the locked analysis and formal audit passed, and all non-timing outputs matched the "
        "historical frozen run. Source-initialization training was not repeated.\n\n"
        f"- Ledger: `{ledger['decision']}`\n"
        f"- Formal audit: `{audit['decision']}`\n"
        f"- Historical comparison: `{comparison['decision']}`\n",
        encoding="utf-8",
    )
    write_manifest(archive_root)
    print("PASS_FINALIZED_CUDA_REPLAY_ARCHIVE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
