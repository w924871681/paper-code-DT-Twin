# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", required=True)
    args = p.parse_args()
    root = os.path.abspath(args.project_root)
    if root not in sys.path:
        sys.path.insert(0, root)
    from experiments.supplementary.pipeline import analyze_anchor_risk

    obj = analyze_anchor_risk(root)
    print(obj["decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
