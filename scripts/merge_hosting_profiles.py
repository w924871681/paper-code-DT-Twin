# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shared.evaluation.common import atomic_json, file_sha256


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge hosting-profile JSON files from multiple machines.")
    parser.add_argument("--inputs", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    records: List[Dict[str, Any]] = []
    sources = []
    seen = set()
    for path in args.inputs:
        path = os.path.abspath(path)
        obj = json.load(open(path, "r", encoding="utf-8"))
        if obj.get("decision") != "PASS_HOSTING_PROFILE_COMPLETE":
            raise RuntimeError(f"Hosting profile is not PASS: {path}")
        sources.append({"path": path, "sha256": file_sha256(path), "host_label": obj.get("host_label")})
        for row in obj.get("records", []):
            key = (
                row.get("host_label"), row.get("actual_device"), row.get("H"),
                row.get("token"), row.get("safe_mode"),
            )
            if key in seen:
                raise RuntimeError(f"Duplicate hosting row: {key}")
            seen.add(key)
            records.append(row)

    out = {
        "study": "merged_frozen_candidate_hosting_profiles",
        "decision": "PASS_HOSTING_PROFILE_COMPLETE",
        "sources": sources,
        "records": records,
        "selection_or_adaptation_performed": False,
    }
    atomic_json(out, os.path.abspath(args.out))
    print(json.dumps({"decision": out["decision"], "records": len(records)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
