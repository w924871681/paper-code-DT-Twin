# -*- coding: utf-8 -*-
from __future__ import annotations
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import argparse
from experiments.main.pipeline import preflight

p=argparse.ArgumentParser(); p.add_argument('--project-root',default='.'); p.add_argument('--out',required=True)
a=p.parse_args(); obj=preflight(os.path.abspath(a.project_root), os.path.abspath(a.out)); print(obj['decision'])
if not obj['decision'].startswith('PASS_'): raise SystemExit(2)
