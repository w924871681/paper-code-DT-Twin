# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from typing import Any, Dict

from configs.methods.main_experiments_cfg import CFG, config_dict
from shared.evaluation.common import atomic_json, file_sha256, load_json


def audit(project_root: str, result_root: str) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    result_root = os.path.abspath(result_root)
    paths = {
        "preflight": os.path.join(result_root, "preflight", "final_exp_preflight.json"),
        "ablation": os.path.join(result_root, "ablation", "ablation_candidates.json"),
        "seeds": os.path.join(result_root, "seeds", "seed_robustness.json"),
        "scale_bank": os.path.join(result_root, "source_scale", "banks", "source_scale_bank_manifest.json"),
        "scale_eval": os.path.join(result_root, "source_scale", "source_scale_eval.json"),
        "real_manifest": os.path.join(result_root, "real_trace", "processed", "real_trace_manifest.json"),
        "real_bank": os.path.join(result_root, "real_trace", "bank", "real_bank_manifest.json"),
        "real_eval": os.path.join(result_root, "real_trace", "real_eval.json"),
        "report": os.path.join(result_root, "report", "final_report_manifest.json"),
    }
    checks: Dict[str, bool] = {f"{k}_exists": os.path.isfile(v) for k, v in paths.items()}
    details: Dict[str, Any] = {}
    if all(checks.values()):
        objs = {k: load_json(v) for k, v in paths.items()}
        checks.update(
            {
                "preflight_pass": objs["preflight"].get("decision") == "PASS_FINAL_PAPER_EXPERIMENTS_PREFLIGHT",
                "ablation_pass": objs["ablation"].get("decision") == "PASS_FINAL_ABLATION_RESOURCE_BANK_ORACLE",
                "ablation_records_80": int(objs["ablation"].get("N_records", -1)) == 80,
                "ablation_test_not_used_for_selection": not bool(objs["ablation"].get("selection_uses_test")),
                "seeds_pass": objs["seeds"].get("decision") == "PASS_FINAL_THREE_TARGET_SEEDS",
                "seed_records_240": int(objs["seeds"].get("N_records", -1)) == 240,
                "seed_test_not_used_for_selection": not bool(objs["seeds"].get("selection_uses_test")),
                "scale_bank_pass": objs["scale_bank"].get("decision") == "PASS_FINAL_SOURCE_SCALE_BANKS",
                "scale_bank_assets_60": int(objs["scale_bank"].get("completed_assets", -1)) == 60,
                "scale_bank_test_unused": not bool(objs["scale_bank"].get("test_used")),
                "scale_eval_pass": objs["scale_eval"].get("decision") == "PASS_FINAL_SOURCE_SCALE_EVAL",
                "scale_eval_records_400": int(objs["scale_eval"].get("N_records", -1)) == 400,
                "scale_eval_test_not_used_for_selection": not bool(objs["scale_eval"].get("selection_uses_test")),
                "real_manifest_pass": objs["real_manifest"].get("decision") == "PASS_REAL_TRACE_PREPARED",
                "real_processed_hash": file_sha256(objs["real_manifest"]["processed_npz"]) == objs["real_manifest"]["processed_sha256"],
                "real_bank_pass": objs["real_bank"].get("decision") == "PASS_REAL_SOURCE_BANK",
                "real_bank_assets_12": int(objs["real_bank"].get("completed_assets", -1)) == 12,
                "real_bank_test_unused": not bool(objs["real_bank"].get("test_used")),
                "real_eval_pass": objs["real_eval"].get("decision") == "PASS_REAL_TRACE_EVAL",
                "real_eval_records_80": int(objs["real_eval"].get("N_records", -1)) == 80,
                "real_eval_test_not_used_for_selection": not bool(objs["real_eval"].get("selection_uses_test")),
                "report_pass": objs["report"].get("decision") == "PASS_FINAL_PAPER_TABLES_AND_FIGURES",
                "method_retuning_disabled": not bool(objs["report"].get("method_retuning_allowed")),
            }
        )
        tables_dir = os.path.join(result_root, "report", "tables")
        figures_dir = os.path.join(result_root, "report", "figures")
        for name in CFG.required_tables:
            checks[f"table_{name}_exists"] = os.path.isfile(os.path.join(tables_dir, name))
        for name in CFG.required_figures:
            checks[f"figure_{name}_exists"] = os.path.isfile(os.path.join(figures_dir, name))
            checks[f"figure_{os.path.splitext(name)[0]}_png_exists"] = os.path.isfile(
                os.path.join(figures_dir, os.path.splitext(name)[0] + ".png")
            )
        details = {
            "hashes": {k: file_sha256(v) for k, v in paths.items()},
            "tables_dir": tables_dir,
            "figures_dir": figures_dir,
        }
    decision = (
        "PASS_FINAL_PAPER_EXPERIMENTS_COMPLETE_AND_AUDITED"
        if checks and all(checks.values())
        else "FAIL_FINAL_PAPER_EXPERIMENTS_AUDIT"
    )
    obj = {
        "study": "experiments.main_audit",
        "decision": decision,
        "protocol": config_dict(),
        "checks": checks,
        "details": details,
        "method_retuning_allowed": False,
        "historical_pool_k_reused": False,
    }
    atomic_json(obj, os.path.join(result_root, "audit", "final_exp_audit.json"))
    return obj
