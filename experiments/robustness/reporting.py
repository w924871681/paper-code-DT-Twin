# -*- coding: utf-8 -*-
from __future__ import annotations
import csv, json, os
from collections import defaultdict
from typing import Any, Dict, List, Mapping, Sequence
import matplotlib.pyplot as plt
import numpy as np
from configs.methods.robustness_experiments_cfg import CFG2, config_dict
from shared.evaluation.common import atomic_json, file_sha256, load_json
from experiments.main.pipeline import _center_bootstrap, _mean, _rel_gain


def _write_csv(path: str, rows: Sequence[Mapping[str,Any]]) -> None:
    os.makedirs(os.path.dirname(path),exist_ok=True)
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with open(path,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)


def _save(fig,path):
    os.makedirs(os.path.dirname(path),exist_ok=True); fig.savefig(path,bbox_inches='tight'); fig.savefig(os.path.splitext(path)[0]+'.png',dpi=300,bbox_inches='tight'); plt.close(fig)


def _scale_rows(obj):
    b=defaultdict(list)
    for r in obj['records'].values(): b[int(r['source_scale'])].append(r)
    out=[]
    for s,vals in sorted(b.items()):
        gains=[_rel_gain(x['selected']['test']['weighted_mse'],x['anchor']['test']['weighted_mse']) for x in vals]
        by=defaultdict(list)
        for x,g in zip(vals,gains): by[int(x['center_id'])].append(g)
        ci=_center_bootstrap(by,CFG2.data_seed+701+s)
        out.append({'SourceCenters':s,'OursWMSE':_mean(x['selected']['test']['weighted_mse'] for x in vals),'A57WMSE':_mean(x['anchor']['test']['weighted_mse'] for x in vals),'WMSEGainVsA57':float(np.mean(gains)),'CI_low':ci['ci_low'],'CI_high':ci['ci_high'],'N':len(vals),'FixedUpdatesPerAsset':CFG2.source_updates_per_asset,'SameInitializationAcrossScales':True})
    return out


def _seed_rows(obj):
    b=defaultdict(list)
    for r in obj['records'].values(): b[int(r['source_seed'])].append(r)
    out=[]
    for s,vals in sorted(b.items()):
        gains=[_rel_gain(x['selected']['test']['weighted_mse'],x['anchor']['test']['weighted_mse']) for x in vals]; by=defaultdict(list)
        for x,g in zip(vals,gains): by[int(x['center_id'])].append(g)
        ci=_center_bootstrap(by,CFG2.data_seed+1701+s)
        out.append({'SourceSeed':s,'OursWMSE':_mean(x['selected']['test']['weighted_mse'] for x in vals),'A57WMSE':_mean(x['anchor']['test']['weighted_mse'] for x in vals),'WMSEGainVsA57':float(np.mean(gains)),'CI_low':ci['ci_low'],'CI_high':ci['ci_high'],'MAE':_mean(x['selected']['test']['mae'] for x in vals),'Worst10':_mean(x['selected']['test']['worst10'] for x in vals),'N':len(vals)})
    if out:
        out.append({'SourceSeed':'mean±std','OursWMSE':f"{np.mean([x['OursWMSE'] for x in out]):.8f}±{np.std([x['OursWMSE'] for x in out],ddof=1):.8f}",'A57WMSE':f"{np.mean([x['A57WMSE'] for x in out]):.8f}±{np.std([x['A57WMSE'] for x in out],ddof=1):.8f}",'WMSEGainVsA57':f"{np.mean([x['WMSEGainVsA57'] for x in out]):.8f}±{np.std([x['WMSEGainVsA57'] for x in out],ddof=1):.8f}"})
    return out


def _real_rows(obj):
    vals=list(obj['records'].values()); gains=[_rel_gain(x['selected']['test']['weighted_mse'],x['anchor']['test']['weighted_mse']) for x in vals]; oracle=[_rel_gain(x['test_oracle']['test']['weighted_mse'],x['anchor']['test']['weighted_mse']) for x in vals]; captured=[]
    for g,o in zip(gains,oracle): captured.append(g/o if o>1e-12 else (1.0 if abs(g)<1e-12 else 0.0))
    by=defaultdict(list)
    for x,g in zip(vals,gains): by[x['machine_id_hash']].append(g)
    ci=_center_bootstrap({i:v for i,v in enumerate(by.values())},CFG2.data_seed+2701)
    selected_better=sum(g>1e-6 for g in gains); selected_harm=sum(g<-1e-6 for g in gains)
    return [
        {'Measure':'Selected WMSE','Value':_mean(x['selected']['test']['weighted_mse'] for x in vals)},
        {'Measure':'A57 WMSE','Value':_mean(x['anchor']['test']['weighted_mse'] for x in vals)},
        {'Measure':'Test-oracle WMSE','Value':_mean(x['test_oracle']['test']['weighted_mse'] for x in vals)},
        {'Measure':'Selected gain vs A57','Value':float(np.mean(gains))},
        {'Measure':'Selected gain CI low','Value':ci['ci_low']},
        {'Measure':'Selected gain CI high','Value':ci['ci_high']},
        {'Measure':'Oracle gain vs A57','Value':float(np.mean(oracle))},
        {'Measure':'Mean captured oracle headroom','Value':float(np.mean(captured))},
        {'Measure':'Beneficial selected cases','Value':selected_better},
        {'Measure':'Harmful selected cases','Value':selected_harm},
    ]


def generate_v2_report(project_root: str, out_dir: str) -> Dict[str,Any]:
    root=os.path.abspath(project_root); v2=os.path.join(root,CFG2.output_root); out_dir=os.path.abspath(out_dir); tdir=os.path.join(out_dir,'tables'); fdir=os.path.join(out_dir,'figures')
    scale=load_json(os.path.join(v2,'source_scale_controlled','controlled_source_scale_eval.json')); seeds=load_json(os.path.join(v2,'source_seed','source_seed_eval.json')); real=load_json(os.path.join(v2,'real_diagnostics','real_candidate_diagnostics.json')); coverage=load_json(os.path.join(v2,'architecture_coverage','architecture_coverage.json'))
    expected=[(scale,'PASS_CONTROLLED_SOURCE_SCALE_EVAL'),(seeds,'PASS_SOURCE_SEED_ROBUSTNESS_EVAL'),(real,'PASS_REAL_CANDIDATE_DIAGNOSTICS'),(coverage,'PASS_ARCHITECTURE_COVERAGE_ANALYSIS')]
    for o,d in expected:
        if o.get('decision')!=d: raise RuntimeError(f'Input not PASS: {o.get("decision")}')
    sr=_scale_rows(scale); tr=_seed_rows(seeds); rr=_real_rows(real); cr=coverage['rows']
    _write_csv(os.path.join(tdir,'table_source_scale_controlled.csv'),sr); _write_csv(os.path.join(tdir,'table_source_bank_seed_robustness.csv'),tr); _write_csv(os.path.join(tdir,'table_real_candidate_oracle_diagnostics.csv'),rr); _write_csv(os.path.join(tdir,'table_architecture_coverage.csv'),cr)
    fig,ax=plt.subplots(figsize=(6.5,4.3)); ax.plot([x['SourceCenters'] for x in sr],[x['OursWMSE'] for x in sr],marker='o',label='Ours'); ax.plot([x['SourceCenters'] for x in sr],[x['A57WMSE'] for x in sr],marker='s',label='Scale-matched A57'); ax.set_xlabel('Number of source centers'); ax.set_ylabel('Test WMSE'); ax.set_title('Compute-matched source-scale analysis'); ax.legend(); _save(fig,os.path.join(fdir,'fig_source_scale_controlled.pdf'))
    numeric=[x for x in tr if isinstance(x['SourceSeed'],int)]; fig,ax=plt.subplots(figsize=(6.5,4.3)); ax.bar([str(x['SourceSeed']) for x in numeric],[100*x['WMSEGainVsA57'] for x in numeric]); ax.axhline(0,linewidth=.8); ax.set_xlabel('Source-bank training seed'); ax.set_ylabel('WMSE gain vs same-seed A57 (%)'); ax.set_title('Source-bank seed robustness'); _save(fig,os.path.join(fdir,'fig_source_bank_seed_robustness.pdf'))
    focus=[x for x in cr if int(x['ArchIdx']) in (1,13) and x.get('UniqueRescueCount') is not None]; fig,ax=plt.subplots(figsize=(8.5,4.5)); labels=[f"{x['Dataset']} A{x['ArchIdx']}" for x in focus]; vals=[int(x['UniqueRescueCount']) for x in focus]; ax.barh(labels,vals); ax.set_xlabel('Unique leave-one-out rescue cases'); ax.set_title('Coverage contribution of A1 and A13'); _save(fig,os.path.join(fdir,'fig_architecture_coverage_a1_a13.pdf'))
    vals=list(real['records'].values()); anchor=np.asarray([x['anchor']['test']['weighted_mse'] for x in vals]); selected=np.asarray([x['selected']['test']['weighted_mse'] for x in vals]); oracle=np.asarray([x['test_oracle']['test']['weighted_mse'] for x in vals]); fig,ax=plt.subplots(figsize=(6.5,4.5)); ax.scatter(anchor,selected,s=20,alpha=.7,label='Selected'); ax.scatter(anchor,oracle,s=20,alpha=.7,label='Test oracle'); lo=min(anchor.min(),selected.min(),oracle.min()); hi=max(anchor.max(),selected.max(),oracle.max()); ax.plot([lo,hi],[lo,hi],linestyle='--',linewidth=1); ax.set_xlabel('A57 WMSE'); ax.set_ylabel('Candidate WMSE'); ax.set_title('Alibaba selector and oracle headroom'); ax.legend(); _save(fig,os.path.join(fdir,'fig_real_oracle_headroom.pdf'))
    manifest={'study':'experiments.robustness_report','decision':'PASS_FINAL_PAPER_EXPERIMENTS_V2_REPORT','protocol':config_dict(),'tables':['table_source_scale_controlled.csv','table_source_bank_seed_robustness.csv','table_real_candidate_oracle_diagnostics.csv','table_architecture_coverage.csv'],'figures':['fig_source_scale_controlled.pdf','fig_source_bank_seed_robustness.pdf','fig_architecture_coverage_a1_a13.pdf','fig_real_oracle_headroom.pdf'],'input_sha256':{'scale':file_sha256(os.path.join(v2,'source_scale_controlled','controlled_source_scale_eval.json')),'seeds':file_sha256(os.path.join(v2,'source_seed','source_seed_eval.json')),'real':file_sha256(os.path.join(v2,'real_diagnostics','real_candidate_diagnostics.json')),'coverage':file_sha256(os.path.join(v2,'architecture_coverage','architecture_coverage.json'))}}
    atomic_json(manifest,os.path.join(out_dir,'v2_report_manifest.json')); return manifest
