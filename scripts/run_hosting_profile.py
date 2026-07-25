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
from experiments.pre_submission.hosting_profile import run_hosting_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile the seven frozen candidates on CPU/GPU hosts.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--out",
        default=os.path.join(CFG.output_root, "hosting", "hosting_profile.json"),
    )
    parser.add_argument("--devices", default="cpu,cuda", help="Comma-separated devices, e.g. cpu,cuda")
    parser.add_argument("--safe-mode", default="gru-native")
    parser.add_argument("--warmups", type=int, default=None)
    parser.add_argument("--timed-inferences", type=int, default=None)
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--host-label", default=None, help="Stable label such as laptop_cpu_gpu or jetson_orin")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    devices = [x.strip() for x in args.devices.split(",") if x.strip()]
    result = run_hosting_profile(
        os.path.abspath(args.project_root),
        os.path.abspath(args.out),
        devices=devices,
        safe_mode=args.safe_mode,
        warmups=args.warmups,
        timed_inferences=args.timed_inferences,
        repeats=args.repeats,
        smoke=args.smoke,
        host_label=args.host_label,
    )
    print(json.dumps({"decision": result["decision"], "records": len(result["records"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
