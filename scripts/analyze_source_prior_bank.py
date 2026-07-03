# -*- coding: utf-8 -*-
import argparse
import json
import os
import sys

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from source_prior_bank.pipeline import analyze


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    p.add_argument("--holdout", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    obj = analyze(os.path.abspath(a.root), a.holdout, a.out)
    print(json.dumps(obj, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
