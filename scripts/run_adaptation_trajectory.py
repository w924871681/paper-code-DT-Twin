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
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--no-save-checkpoints", action="store_true")
    args = p.parse_args()
    root = os.path.abspath(args.project_root)
    if root not in sys.path:
        sys.path.insert(0, root)
    from experiments.supplementary.pipeline import run_adaptation_trajectory

    obj = run_adaptation_trajectory(
        root,
        None,
        args.device,
        args.safe_mode,
        smoke=args.smoke,
        save_checkpoints=not args.no_save_checkpoints,
    )
    print(obj["decision"])
    return 0 if obj.get("complete") else 2


if __name__ == "__main__":
    raise SystemExit(main())
