# -*- coding: utf-8 -*-
import argparse, os
from experiments.robustness.pipeline import run_v2_preflight
p=argparse.ArgumentParser(); p.add_argument('--project-root',default='.'); p.add_argument('--out',required=True)
a=p.parse_args(); obj=run_v2_preflight(os.path.abspath(a.project_root),os.path.abspath(a.out)); print(obj['decision'])
