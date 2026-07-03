# -*- coding: utf-8 -*-
from __future__ import annotations
import os
from typing import Any, Dict
from configs.methods.robustness_experiments_cfg import CFG2, config_dict
from shared.evaluation.common import atomic_json, file_sha256, load_json


def run_v2_audit(project_root: str, out_path: str) -> Dict[str,Any]:
    root=os.path.abspath(project_root); v2=os.path.join(root,CFG2.output_root)
    paths={
        'preflight':os.path.join(v2,'preflight','v2_preflight.json'),
        'scale_banks':os.path.join(v2,'source_scale_controlled','banks','controlled_source_scale_bank_manifest.json'),
        'scale_eval':os.path.join(v2,'source_scale_controlled','controlled_source_scale_eval.json'),
        'seed_banks':os.path.join(v2,'source_seed','banks','source_seed_bank_manifest.json'),
        'seed_eval':os.path.join(v2,'source_seed','source_seed_eval.json'),
        'real_diag':os.path.join(v2,'real_diagnostics','real_candidate_diagnostics.json'),
        'coverage':os.path.join(v2,'architecture_coverage','architecture_coverage.json'),
        'report':os.path.join(v2,'report','v2_report_manifest.json'),
    }
    expected={'preflight':'PASS_FINAL_PAPER_EXPERIMENTS_V2_PREFLIGHT','scale_banks':'PASS_CONTROLLED_SOURCE_SCALE_BANKS','scale_eval':'PASS_CONTROLLED_SOURCE_SCALE_EVAL','seed_banks':'PASS_SOURCE_SEED_BANKS','seed_eval':'PASS_SOURCE_SEED_ROBUSTNESS_EVAL','real_diag':'PASS_REAL_CANDIDATE_DIAGNOSTICS','coverage':'PASS_ARCHITECTURE_COVERAGE_ANALYSIS','report':'PASS_FINAL_PAPER_EXPERIMENTS_V2_REPORT'}
    checks={}; hashes={}; objs={}
    for k,p in paths.items():
        checks[f'{k}_exists']=os.path.isfile(p)
        if os.path.isfile(p): objs[k]=load_json(p); hashes[k]=file_sha256(p); checks[f'{k}_decision']=objs[k].get('decision')==expected[k]
    if 'scale_banks' in objs: checks['scale_bank_count']=len(objs['scale_banks'].get('assets',{}))==60
    if 'scale_eval' in objs: checks['scale_eval_count']=len(objs['scale_eval'].get('records',{}))==400
    if 'seed_banks' in objs: checks['seed_bank_count']=len(objs['seed_banks'].get('assets',{}))==36
    if 'seed_eval' in objs: checks['seed_eval_count']=len(objs['seed_eval'].get('records',{}))==240
    if 'real_diag' in objs: checks['real_diag_count']=len(objs['real_diag'].get('records',{}))==80
    if 'scale_banks' in objs:
        items=list(objs['scale_banks'].get('assets',{}).values()); by={}
        for x in items: by.setdefault((x['H'],x['arch_idx']),set()).add(x['initialization_seed'])
        checks['same_initialization_across_scales']=all(len(v)==1 for v in by.values())
        checks['fixed_updates_across_scales']=all(int(x['fixed_updates'])==CFG2.source_updates_per_asset for x in items)
    decision='PASS_FINAL_PAPER_EXPERIMENTS_V2_COMPLETE_AND_AUDITED' if checks and all(bool(v) for v in checks.values()) else 'FAIL_FINAL_PAPER_EXPERIMENTS_V2_AUDIT'
    obj={'study':'experiments.robustness_audit','decision':decision,'protocol':config_dict(),'checks':checks,'artifact_sha256':hashes}
    atomic_json(obj,os.path.abspath(out_path)); return obj
