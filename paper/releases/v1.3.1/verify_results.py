"""Verify manuscript aggregates from the supplied task-level records; no model training."""
from pathlib import Path
import json
import re
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
D=ROOT/'data'
rows=pd.read_csv(D/'individual_results.csv')
assert len(rows)==8*3*120
assert rows.groupby(['method','budget']).size().eq(120).all()
assert rows.groupby(['method','budget']).VM.nunique().eq(30).all()
assert rows.resource_feasible.all()
limits={'tight':(30000,1500000),'medium':(100000,5000000),'loose':(500000,20000000)}
for budget,(p,o) in limits.items():
    r=rows[rows.budget==budget]
    assert r.params.le(p).all() and r.operations.le(o).all()

med=rows[rows.budget=='medium']
plot=pd.read_csv(D/'overall.csv').set_index('Method')
for name,g in med.groupby('method'):
    for metric in ['MAE','MSE','Worst10']:
        assert np.isclose(g[metric].mean(),plot.loc[name,metric],rtol=0,atol=1e-12),(name,metric)
    assert np.isclose(g.MSE.nlargest(12).mean(),plot.loc[name,'CVaR90'],rtol=0,atol=1e-12),name

pair=pd.read_csv(D/'paired.csv')
for method,col in [('MSA-DTI','proposed_mse'),('PT+FT','pt_ft_mse')]:
    assert np.allclose(np.sort(med[med.method==method].MSE),np.sort(pair[col]),rtol=0,atol=1e-12)
vm=pair.groupby('vm')[['pt_ft_mse','proposed_mse']].mean()
a=vm.pt_ft_mse.to_numpy();b=vm.proposed_mse.to_numpy()
ii=np.random.default_rng(20261026).integers(0,len(vm),(10000,len(vm)))
bootstrap=100*(1-b[ii].mean(axis=1)/a[ii].mean(axis=1))
gain=float(100*(1-b.mean()/a.mean()))
ci=np.quantile(bootstrap,[.025,.975]).tolist()
assert round(gain,2)==6.88
assert [round(x,2) for x in ci]==[4.26,15.95]
assert (b<a).sum()==28 and (b>a).sum()==2
counts=pair.selection_category.value_counts().to_dict()
assert counts=={'beneficial alternative':84,'reference retained':31,'harmful alternative':5}

ab=pd.read_csv(D/'ablation_individual_results.csv')
absummary=pd.read_csv(D/'ablations.csv').set_index('variant')
for name,g in ab[ab.budget=='medium'].groupby('method'):
    for metric in ['MAE','MSE','Worst10']:
        assert np.isclose(g[metric].mean(),absummary.loc[name,metric],rtol=0,atol=1e-12)
    assert np.isclose(g.MSE.nlargest(12).mean(),absummary.loc[name,'CVaR90'],rtol=0,atol=1e-12)
    assert np.isclose(g.harm_vs_reference.mean(),absummary.loc[name,'harm'],rtol=0,atol=1e-12)

role=json.loads((D/'data_roles.json').read_text(encoding='utf-8'))
assert {k:len(v) for k,v in role.items()}=={'source':20,'development':20,'calibration':20,'evaluation':30}
assert len(set(sum(role.values(),[])))==90
geometry=pd.read_csv(D/'target_windows.csv')
assert len(geometry)==200
assert geometry.groupby(['H','K']).B.nunique().eq(1).all()
for _,r in geometry.iterrows():
    last_validation_origin=r.validation_end_exclusive-r.H-1
    assert last_validation_origin+r.H<=r.decision_record
    assert r.decision_record+1>last_validation_origin+r.H

timing=pd.read_csv(D/'pipeline_timing.csv')
assert len(timing)==96 and timing.n.eq(5).all()
runtime=timing.groupby('method').mean_seconds.mean().to_dict()
assert round(runtime['MSA-DTI'],3)==8.124
assert round(runtime['PT+FT'],3)==1.971
assert timing[timing.method=='MSA-DTI'].actual_adaptations_per_run.eq(7).all()

main=(ROOT/'main.tex').read_text(encoding='utf-8')
body=main.split(r'\begin{thebibliography}')[0]
first=[]
for group in re.findall(r'\\cite\w*\{([^}]+)\}',body):
    for key in group.split(','):
        if key not in first:first.append(key)
bib=re.findall(r'\\bibitem\{([^}]+)\}',main)
assert first==bib and len(bib)==34
for p in [ROOT/'main.tex',ROOT/'supplementary.tex',*(ROOT/'tables').glob('*.tex')]:
    text=p.read_text(encoding='utf-8')
    assert not re.search(r'\bD_CAP\b|\bCAP\b|Linear[- ]D|NEW[12]|First Author|lower is better',text),p

result={'status':'PASS','methods':8,'evaluation_tasks_per_method_budget':120,
        'evaluation_VMs':30,'budgets':3,'aggregate_MSE_gain_percent':gain,
        'paired_VM_bootstrap_95_percent':ci,
        'mean_task_relative_gain_percent':float(100*(1-pair.proposed_mse/pair.pt_ft_mse).mean()),
        'selection_counts':counts,'main_references_in_first_use_order':len(bib),
        'all_main_method_deployment_checks_passed':True,
        'mean_pipeline_seconds':runtime}
print(json.dumps(result,indent=2))
