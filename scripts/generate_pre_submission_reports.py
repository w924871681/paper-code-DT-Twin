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
from experiments.pre_submission.audits_and_reporting import generate_all


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate no-retraining audits, Fig.10 Pareto, and enhancement tables.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--output-root",
        default=os.path.join(CFG.output_root, "report"),
    )
    args = parser.parse_args()
    result = generate_all(os.path.abspath(args.project_root), os.path.abspath(args.output_root))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
