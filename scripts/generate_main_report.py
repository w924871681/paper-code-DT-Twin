# -*- coding: utf-8 -*-
from __future__ import annotations
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import argparse
from experiments.main.reporting import generate_report
p=argparse.ArgumentParser(); p.add_argument('--project-root',default='.'); p.add_argument('--result-root',required=True)
a=p.parse_args(); obj=generate_report(os.path.abspath(a.project_root),os.path.abspath(a.result_root)); print(obj['decision'])
