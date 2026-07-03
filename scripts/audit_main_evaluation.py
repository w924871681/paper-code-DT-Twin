# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from configs.methods.main_evaluation_cfg import CFG
from main_evaluation.pipeline import audit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=CFG.output_root)
    args = ap.parse_args()
    out_root = args.root if os.path.isabs(args.root) else os.path.join(ROOT, args.root)
    result = audit(ROOT, out_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["decision"].startswith("PASS_"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
