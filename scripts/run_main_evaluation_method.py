# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from configs.methods.main_evaluation_cfg import CFG
from main_evaluation.pipeline import run_method


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=CFG.methods, required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--safe_mode", default="gru-native")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    out = os.path.join(ROOT, CFG.output_root, "methods", args.method + ".json")
    result = run_method(
        ROOT, args.method, out, args.device, args.safe_mode, args.smoke
    )
    print(
        json.dumps(
            {
                "method": args.method,
                "decision": result.get("decision"),
                "N_records": result.get("N_records"),
                "expected": result.get("expected_records"),
                "complete": result.get("complete"),
                "out": out,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
