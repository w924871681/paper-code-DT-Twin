# -*- coding: utf-8 -*-
import argparse, json, os, sys
_PROJECT_ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _PROJECT_ROOT not in sys.path: sys.path.insert(0,_PROJECT_ROOT)
from anchor_safe_selector.pipeline import run_candidate_pool

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',default='.')
    p.add_argument('--bank-manifest',required=True)
    p.add_argument('--out',required=True)
    p.add_argument('--pool-role',choices=('selector_dev','final'),required=True)
    p.add_argument('--device',default='cuda')
    p.add_argument('--safe-mode',default='gru-native')
    p.add_argument('--smoke',action='store_true')
    a=p.parse_args()
    obj=run_candidate_pool(os.path.abspath(a.root),a.bank_manifest,a.out,a.device,a.safe_mode,a.pool_role,a.smoke)
    print(json.dumps({k:obj.get(k) for k in ('decision','pool_role','N_records','completed_candidate_count','complete')},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
