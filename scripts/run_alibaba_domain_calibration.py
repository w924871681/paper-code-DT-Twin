# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from configs.methods.pre_submission_enhancements_cfg import CFG
from experiments.pre_submission.alibaba_domain_calibration import run_alibaba_domain_calibration_and_eval


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate on 20 Alibaba machines and evaluate on 40 unseen machines.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--manifest",
        default=os.path.join(CFG.output_root, "alibaba_domain", "prepared", "real_trace_domain_manifest.json"),
    )
    parser.add_argument(
        "--bank-dir",
        default=os.path.join(CFG.output_root, "alibaba_domain", "bank"),
    )
    parser.add_argument(
        "--out",
        default=os.path.join(CFG.output_root, "alibaba_domain", "alibaba_domain_result.json"),
    )
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--safe-mode", default="gru-native")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    result = run_alibaba_domain_calibration_and_eval(
        os.path.abspath(args.project_root),
        os.path.abspath(args.manifest),
        os.path.abspath(args.bank_dir),
        os.path.abspath(args.out),
        args.device,
        args.safe_mode,
        args.smoke,
    )
    print(json.dumps({
        "decision": result["decision"],
        "domain_calibrated_tau": result.get("domain_calibrated_tau"),
        "target_summaries": result.get("target_summaries"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
