# -*- coding: utf-8 -*-
import argparse
import json
import os
import sys

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from source_prior_bank.pipeline import build_strong_bank


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--device", default="cuda")
    p.add_argument("--safe-mode", default="gru-native")
    p.add_argument("--smoke", action="store_true")
    a = p.parse_args()
    obj = build_strong_bank(
        os.path.abspath(a.root),
        a.out_dir,
        a.device,
        a.safe_mode,
        a.smoke,
    )
    print(
        json.dumps(
            {
                "decision": obj.get("decision"),
                "asset_count": obj.get("asset_count"),
                "out": os.path.abspath(
                    os.path.join(a.out_dir, "source_prior_bank_manifest.json")
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
