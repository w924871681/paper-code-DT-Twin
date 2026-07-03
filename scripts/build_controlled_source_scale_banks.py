# -*- coding: utf-8 -*-
import argparse, os
from experiments.robustness.pipeline import build_controlled_source_scale_banks
p=argparse.ArgumentParser(); p.add_argument('--project-root',default='.'); p.add_argument('--out-dir',required=True); p.add_argument('--device',default='cuda'); p.add_argument('--safe-mode',default='gru-native'); p.add_argument('--smoke',action='store_true')
a=p.parse_args(); obj=build_controlled_source_scale_banks(os.path.abspath(a.project_root),os.path.abspath(a.out_dir),a.device,a.safe_mode,a.smoke); print(obj['decision'])
