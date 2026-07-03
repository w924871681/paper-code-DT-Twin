# -*- coding: utf-8 -*-
from __future__ import annotations
import csv, importlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
mods=["source_prior_bank.pipeline","anchor_safe_selector.pipeline","main_evaluation.pipeline","experiments.main.pipeline","experiments.robustness.pipeline","experiments.supplementary.pipeline","reporting.reporting"]
errors=[]
for m in mods:
    try: importlib.import_module(m); print("OK",m)
    except Exception as e: errors.append((m,repr(e))); print("FAIL",m,repr(e))
required=[ROOT/"results/main/overall_comparison.csv",ROOT/"results/supplementary/adaptation_trajectory_summary.csv",ROOT/"results/supplementary/repeated_runtime_summary.csv"]
for p in required:
    print("OK" if p.exists() else "MISSING",p.relative_to(ROOT))
    if not p.exists(): errors.append((str(p),"missing"))
if errors:
    print(json.dumps(errors,indent=2)); raise SystemExit(2)
print("PASS_PUBLIC_REPOSITORY_VERIFICATION")
