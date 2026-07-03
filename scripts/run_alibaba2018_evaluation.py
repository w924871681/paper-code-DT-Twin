# -*- coding: utf-8 -*-
from __future__ import annotations
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import argparse
from experiments.main.real_trace import run_real_eval
p=argparse.ArgumentParser(); p.add_argument('--project-root',default='.'); p.add_argument('--manifest',required=True); p.add_argument('--bank-dir',required=True); p.add_argument('--out',required=True); p.add_argument('--device',default='cuda'); p.add_argument('--safe-mode',default='gru-native'); p.add_argument('--smoke',action='store_true')
a=p.parse_args(); obj=run_real_eval(os.path.abspath(a.project_root),os.path.abspath(a.manifest),os.path.abspath(a.bank_dir),os.path.abspath(a.out),a.device,a.safe_mode,a.smoke); print(obj['decision'])
