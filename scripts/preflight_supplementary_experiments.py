# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict


def _load_cfg(root: Path):
    cfg_path = root / "cfg" / "methods" / "experiments.supplementary_cfg.py"
    if not cfg_path.is_file():
        raise FileNotFoundError(f"Missing supplementary config: {cfg_path}")
    spec = importlib.util.spec_from_file_location("experiments.supplementary_cfg_local", cfg_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load config module: {cfg_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.CFG_SUPP, module.config_dict


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def _atomic_json(obj: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _pool_ids(pool) -> set[int]:
    start, count, _offset = [int(x) for x in pool]
    return set(range(start, start + count))


def _check_json(path: Path, name: str, checks: Dict[str, bool], details: Dict[str, Any]):
    try:
        obj = _load_json(path)
        details[name] = {"path": str(path), "loaded": True}
        return obj
    except Exception as exc:
        checks[f"{name}_json_readable"] = False
        details[name] = {
            "path": str(path),
            "loaded": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
        return None


def run_preflight(project_root: str) -> Dict[str, Any]:
    root = Path(project_root).resolve()
    cfg, config_dict = _load_cfg(root)
    out_path = root / cfg.output_root / "preflight" / "supp_preflight.json"

    required = {
        "source_prior_bank_manifest": root / cfg.source_prior_bank_manifest_path,
        "c1_bank": root / cfg.c1_bank_path,
        "external_source_manifest": root / cfg.external_source_manifest_path,
        "ablation_candidates": root / cfg.ablation_candidates_path,
        "main_evaluation_preflight": root / cfg.main_evaluation_preflight_path,
    }
    checks: Dict[str, bool] = {}
    details: Dict[str, Any] = {"required_files": {}}

    for name, path in required.items():
        exists = path.is_file()
        checks[f"{name}_exists"] = exists
        details["required_files"][name] = {
            "path": str(path),
            "exists": exists,
            "sha256": _sha256(path) if exists else None,
            "size_bytes": path.stat().st_size if exists else None,
        }

    used: set[int] = set()
    for lo, hi in cfg.known_used_center_ranges:
        used.update(range(int(lo), int(hi) + 1))
    trajectory_overlap = sorted(_pool_ids(cfg.trajectory_pool) & used)
    optimizer_overlap = sorted(_pool_ids(cfg.optimizer_control_pool) & used)
    cross_overlap = sorted(_pool_ids(cfg.trajectory_pool) & _pool_ids(cfg.optimizer_control_pool))

    checks.update({
        "trajectory_pool_untouched": not trajectory_overlap,
        "optimizer_control_pool_untouched": not optimizer_overlap,
        "new_pools_disjoint": not cross_overlap,
        "trajectory_checkpoints_exact": tuple(cfg.trajectory_checkpoints) == (0, 1, 5, 10, 20, 50),
        "target_recipe_frozen": (
            int(cfg.target_steps) == 50
            and abs(float(cfg.target_lr) - 1e-2) < 1e-15
            and abs(float(cfg.target_grad_clip) - 1.0) < 1e-15
        ),
        "runtime_repeats_at_least_five": int(cfg.runtime_repeats) >= 5,
        "matched_candidate_budget_12": int(cfg.matched_candidate_budget) == 12,
    })

    if checks["c1_bank_exists"]:
        checks["c1_bank_hash_frozen"] = _sha256(required["c1_bank"]).lower() == str(cfg.c1_bank_sha256).lower()

    if checks["source_prior_bank_manifest_exists"]:
        manifest = _check_json(required["source_prior_bank_manifest"], "source_prior_bank_manifest", checks, details)
        if manifest is not None:
            checks["source_prior_bank_decision_frozen"] = manifest.get("decision") == cfg.expected_source_prior_bank_decision
            actual_arches = tuple(int(x) for x in manifest.get("candidate_arch_indices", ()))
            checks["compact_architecture_set_exact"] = actual_arches == tuple(cfg.compact_arch_indices)
            details["source_prior_bank_manifest"]["decision"] = manifest.get("decision")
            details["source_prior_bank_manifest"]["candidate_arch_indices"] = list(actual_arches)

    if checks["external_source_manifest_exists"]:
        _check_json(required["external_source_manifest"], "external_source_manifest", checks, details)

    if checks["ablation_candidates_exists"]:
        ablation = _check_json(required["ablation_candidates"], "ablation_candidates", checks, details)
        if ablation is not None:
            checks["ablation_complete"] = bool(ablation.get("complete")) and int(ablation.get("N_records", 0)) == 80
            details["ablation_candidates"]["complete"] = ablation.get("complete")
            details["ablation_candidates"]["N_records"] = ablation.get("N_records")

    if checks["main_evaluation_preflight_exists"]:
        main_evaluation = _check_json(required["main_evaluation_preflight"], "main_evaluation_preflight", checks, details)
        if main_evaluation is not None:
            checks["main_evaluation_preflight_pass"] = main_evaluation.get("decision") == "PASS_MAIN_EVALUATION_LOCKED_PREFLIGHT_READY"
            details["main_evaluation_preflight"]["decision"] = main_evaluation.get("decision")

    details.update({
        "trajectory_pool_overlap": trajectory_overlap,
        "optimizer_control_pool_overlap": optimizer_overlap,
        "new_pool_cross_overlap": cross_overlap,
    })

    failed = sorted(name for name, ok in checks.items() if not ok)
    obj = {
        "study": "experiments.supplementary_preflight",
        "decision": "PASS_SUPPLEMENTARY_EVIDENCE_PREFLIGHT" if not failed else "FAIL_SUPPLEMENTARY_EVIDENCE_PREFLIGHT",
        "protocol": config_dict(),
        "checks": checks,
        "failed_checks": failed,
        "details": details,
        "method_retuning_allowed": False,
        "trajectory_test_used": False,
        "runtime_test_used": False,
        "optimizer_control_is_evaluation_only": True,
    }
    _atomic_json(obj, out_path)
    return obj


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    try:
        obj = run_preflight(args.project_root)
    except Exception:
        traceback.print_exc()
        return 1

    print(obj["decision"])
    if obj["failed_checks"]:
        print("FAILED_CHECKS:")
        for name in obj["failed_checks"]:
            print(f"  - {name}")
        print("REQUIRED_FILE_STATUS:")
        for name, item in obj["details"]["required_files"].items():
            status = "OK" if item["exists"] else "MISSING"
            print(f"  - {name}: {status}: {item['path']}")
    else:
        print("All supplementary preflight checks passed.")
    return 0 if obj["decision"] == "PASS_SUPPLEMENTARY_EVIDENCE_PREFLIGHT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
