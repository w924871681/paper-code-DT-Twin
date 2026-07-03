# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", required=True)
    p.add_argument("--device", default="cuda")
    p.add_argument("--safe-mode", default="gru-native")
    p.add_argument("--repeats", type=int, default=5)
    p.add_argument("--smoke", action="store_true")
    args = p.parse_args()
    root = os.path.abspath(args.project_root)
    if root not in sys.path:
        sys.path.insert(0, root)
    from experiments.supplementary.pipeline import run_repeated_runtime

    obj = run_repeated_runtime(
        root,
        None,
        args.device,
        args.safe_mode,
        smoke=args.smoke,
        repeats=args.repeats,
    )
    print(obj["decision"])
    return 0 if obj.get("complete") else 2


if __name__ == "__main__":
    raise SystemExit(main())
