import csv,json,collections,math,pathlib
p=pathlib.Path(__file__).resolve().parent;data=[json.loads(x) for x in (p/'case_records.jsonl').read_text(encoding='utf8').splitlines()];protocol=json.loads((p/'protocol.json').read_text(encoding='utf8'));summary=json.loads((p/'summary.json').read_text(encoding='utf8'));arch=json.loads((p.parent/'data/candidate_architectures.json').read_text(encoding='utf8'));axis=arch['qaxis'];limits={'tight':(30000,1500000),'medium':(100000,5000000),'loose':(500000,20000000)}
assert len(data)==len(protocol['cases'])==236
cases={c['id']:c for c in protocol['cases']};groups=collections.defaultdict(list)
for x in data:
 c=cases[x['case_id']];s=x['selection'];m=x['test_metrics'];assert s['h']==c['H'] and s['k']==c['K'];assert set(s['scores'])==set(axis)==set(m)
 for budget,(pm,om) in limits.items():
  keys={q:(arch['resources_by_H'][str(c['H'])][q]['params'],arch['resources_by_H'][str(c['H'])][q]['operations'],arch['specs'][q]['arch_id'],q) for q in axis};feasible=[q for q in axis if keys[q][0]<=pm and keys[q][1]<=om];admissible=[q for q in feasible if q=='A55' or s['scores'][q]<=.95*s['scores']['A55']];chosen=min(admissible,key=lambda q:(s['scores'][q],keys[q]));assert s['actions'][budget]=={'selected':chosen,'feasible':feasible,'admissible':admissible}
  groups[c['source'],budget].append((c['vm'],m[chosen]['MSE'],m['PT_A57_ref']['MSE'],m['A55']['MSE']))
for s in summary['results']:
 a=groups[s['source'],s['budget']];by=collections.defaultdict(list)
 for vm,*v in a:by[vm].append(v)
 assert len(by)==s['vm_count'] and len(a)==s['case_count']
 mean=[sum(sum(x[i] for x in vv)/len(vv) for vv in by.values())/len(by) for i in range(3)]
 for i,k in enumerate(('MSA-DTI','PT+FT','A55')):assert math.isclose(mean[i],s['mse_vm_mean'][k],rel_tol=1e-12,abs_tol=1e-14)
print('PASS: 236 cases, 708 selections and six VM-averaged MSE summaries')
