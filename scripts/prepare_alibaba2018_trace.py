# -*- coding: utf-8 -*-
from __future__ import annotations
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import argparse
from experiments.main.real_trace import prepare_alibaba_trace
p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--out-dir',required=True); p.add_argument('--skip-archive-hash-check',action='store_true')
a=p.parse_args(); obj=prepare_alibaba_trace(os.path.abspath(a.input),os.path.abspath(a.out_dir),verify_archive=not a.skip_archive_hash_check); print(obj['decision'])
