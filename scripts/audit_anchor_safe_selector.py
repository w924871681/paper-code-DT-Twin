# -*- coding: utf-8 -*-
import argparse, json, os, sys
_PROJECT_ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _PROJECT_ROOT not in sys.path: sys.path.insert(0,_PROJECT_ROOT)
from anchor_safe_selector.pipeline import audit

def main():
    p=argparse.ArgumentParser(); p.add_argument('--root',default='.'); p.add_argument('--preflight',required=True); p.add_argument('--dev-candidates',required=True); p.add_argument('--selector',required=True); p.add_argument('--final-candidates',required=True); p.add_argument('--analysis',required=True); p.add_argument('--out',required=True); a=p.parse_args()
    obj=audit(os.path.abspath(a.root),a.preflight,a.dev_candidates,a.selector,a.final_candidates,a.analysis,a.out)
    print(json.dumps(obj,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
