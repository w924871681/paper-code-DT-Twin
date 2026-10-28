"""Replay saved adapted states on the original traces; no model training."""
import argparse,pathlib,zipfile,hashlib,json,tempfile,shutil,math,torch
import portable_inference_core as er

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
a=argparse.ArgumentParser();a.add_argument('--materna',type=pathlib.Path,required=True);a.add_argument('--bitbrains',type=pathlib.Path,required=True);a.add_argument('--states',type=pathlib.Path,required=True);a.add_argument('--device',choices=['cpu','cuda'],default='cuda');a.add_argument('--smoke',action='store_true');args=a.parse_args()
p=pathlib.Path(__file__).resolve().parent;protocol=json.loads((p/'protocol.json').read_text(encoding='utf8'));records={r['case_id']:r for r in (json.loads(x) for x in (p/'case_records.jsonl').read_text(encoding='utf8').splitlines())};archives={'materna':args.materna,'bitbrains':args.bitbrains}
for source in archives:
 if sha(archives[source])!=protocol[source+'_archive_sha256']:raise ValueError('Trace archive hash mismatch: '+source)
cases=protocol['cases']
if args.smoke:cases=[next(c for c in cases if c['source']==source) for source in ('materna','bitbrains')]
er.DEVICE=torch.device(args.device);torch.set_num_threads(1);torch.use_deterministic_algorithms(True);er.configure_stage2_runtime(er.DEVICE,'gru-native')
with zipfile.ZipFile(args.states) as z, tempfile.TemporaryDirectory(prefix='msadti-replay-',dir=p) as tmp:
 for index,c in enumerate(cases):
  rec=records[c['id']];s=rec['selection'];folder=pathlib.Path(tmp)/c['id'];folder.mkdir()
  for q,h in s['weights'].items():
   dest=folder/(q+'.pt')
   with z.open(c['id']+'/'+q+'.pt') as src,dest.open('wb') as dst:shutil.copyfileobj(src,dst)
   if sha(dest)!=h:raise ValueError('State hash mismatch '+c['id']+' '+q)
  raw=er.load_raw(archives[c['source']],c['member'],c['start'],s['T']+s['B']+c['H']);actual=er.run_eval(raw,s,folder)
  for q in er.Q:
   for metric in ('MSE','MAE','Worst10'):
    if not math.isclose(actual[q][metric],rec['test_metrics'][q][metric],rel_tol=1e-6,abs_tol=1e-12):raise ValueError('Metric mismatch '+c['id']+' '+q+' '+metric)
   if actual[q]['N_valid']!=rec['test_metrics'][q]['N_valid']:raise ValueError('Mask mismatch '+c['id'])
  print('PASS',index+1,'/',len(cases),c['id'],flush=True)
print('PASS: inference replay; this does not retrain source or target models')

