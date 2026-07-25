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
from experiments.pre_submission.alibaba_domain_calibration import build_alibaba_domain_bank


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the six-candidate Alibaba source bank.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--manifest",
        default=os.path.join(CFG.output_root, "alibaba_domain", "prepared", "real_trace_domain_manifest.json"),
    )
    parser.add_argument(
        "--out-dir",
        default=os.path.join(CFG.output_root, "alibaba_domain", "bank"),
    )
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--safe-mode", default="gru-native")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    result = build_alibaba_domain_bank(
        os.path.abspath(args.project_root),
        os.path.abspath(args.manifest),
        os.path.abspath(args.out_dir),
        args.device,
        args.safe_mode,
        args.smoke,
    )
    print(json.dumps({"decision": result["decision"], "assets": len(result.get("assets", {}))}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
