# -*- coding: utf-8 -*-
import os, sys
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
import argparse, json, os
from c30_diagnostic.pipeline import run_fixed_anchor

def main():
    p=argparse.ArgumentParser(); p.add_argument('--root',default='.'); p.add_argument('--out',required=True); p.add_argument('--device',default='cuda'); p.add_argument('--safe-mode',default='gru-native'); p.add_argument('--smoke',action='store_true'); a=p.parse_args()
    obj=run_fixed_anchor(os.path.abspath(a.root),a.out,a.device,a.safe_mode,a.smoke); print(json.dumps({'decision':obj.get('decision'),'N_records':obj.get('N_records'),'complete':obj.get('complete'),'out':os.path.abspath(a.out)},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
