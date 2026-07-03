# -*- coding: utf-8 -*-
import argparse, os
from experiments.robustness.reporting import generate_v2_report
p=argparse.ArgumentParser(); p.add_argument('--project-root',default='.'); p.add_argument('--out-dir',required=True)
a=p.parse_args(); obj=generate_v2_report(os.path.abspath(a.project_root),os.path.abspath(a.out_dir)); print(obj['decision'])
