import os,sys,pathlib,json,hashlib,time,subprocess,datetime,traceback
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
BASE=pathlib.Path(__file__).resolve().parent;PROJECT=BASE.parent;sys.path.insert(0,str(PROJECT))
import external_runner as er
import torch

def sha(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  for x in iter(lambda:f.read(1048576),b''):h.update(x)
 return h.hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf8'))
def write(p,x):
 p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_name(p.name+'.tmp');temp.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(temp,p)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def verify():
 protocol=read(BASE/'RETRY_PROTOCOL.json')
 if sha(__file__)!=protocol['retry_runner_sha256'] or sha(PROJECT/'external_runner.py')!=protocol['original_runner_sha256'] or sha(PROJECT/'PROTOCOL_LOCK.json')!=protocol['original_protocol_sha256']:raise ValueError('LOCK_CHANGED')
 for c in protocol['cases']:
  if sha(PROJECT/'validation_run_v2'/c['id']/'failure.json')!=c['original_failure_sha256']:raise ValueError('ORIGINAL_FAILURE_CHANGED')
 return protocol

def one(phase,c):
 torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True);er.configure_stage2_runtime(er.DEVICE,'gru-native')
 p=BASE/'cases'/c['id'];p.mkdir(parents=True,exist_ok=True)
 if phase=='select':
  b=er.raw_role_bounds(c['H'],c['K']);T=b['validation'][1]-1
  raw=er.load_raw(c['archive'],c['member'],c['start'],T+1);er.run_select(raw,c['vm'],c['H'],c['K'],p)
 elif phase=='evaluate':
  s=read(p/'selection.json');n=s['T']+s['B']+c['H'];raw=er.load_raw(c['archive'],c['member'],c['start'],n);er.run_eval(raw,s,p)
 else:raise ValueError('BAD_PHASE')

def main():
 protocol=verify();phase=sys.argv[1]
 if phase in ('select_one','eval_one'):
  c=next(x for x in protocol['cases'] if x['id']==sys.argv[2]);one('select' if phase=='select_one' else 'evaluate',c);return
 if phase!='run':raise ValueError('BAD_PHASE')
 original=read(PROJECT/'PROTOCOL_LOCK.json')
 for path,h in original['frozen_file_hashes'].items():
  if sha(path)!=h:raise ValueError('ORIGINAL_FROZEN_INPUT_CHANGED')
 cases=protocol['cases'];write(BASE/'STATUS.json',{'stage':'RETRY_SELECTION','completed':0,'total':len(cases),'updated_utc':now()})
 for i,c in enumerate(cases):
  p=BASE/'cases'/c['id'];p.mkdir(parents=True,exist_ok=True)
  if not (p/'selection.json').exists() and not (p/'selection_failure.json').exists():
   with (p/'selection.log').open('wb') as log:r=subprocess.run([sys.executable,__file__,'select_one',c['id']],stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
   if r.returncode:write(p/'selection_failure.json',{'exit_code':r.returncode,'log_sha256':sha(p/'selection.log'),'utc':now()})
  write(BASE/'STATUS.json',{'stage':'RETRY_SELECTION','completed':i+1,'total':len(cases),'last':c['id'],'updated_utc':now()});print('retry selection',i+1,'/',len(cases),flush=True)
 receipts=[]
 for c in cases:
  p=BASE/'cases'/c['id'];s=p/'selection.json';f=p/'selection_failure.json'
  if not s.exists() and not f.exists():raise ValueError('RETRY_SELECTION_INCOMPLETE')
  if s.exists():
   data=read(s)
   for q,h in data['weights'].items():
    if sha(p/(q+'.pt'))!=h:raise ValueError('RETRY_WEIGHT_DRIFT')
  x=s if s.exists() else f;receipts.append({'id':c['id'],'sha256':sha(x),'status':'selected' if s.exists() else 'failed'})
 seal=BASE/'RETRY_ACTION_SEAL.json';write(seal,{'retry_protocol_sha256':sha(BASE/'RETRY_PROTOCOL.json'),'receipts':receipts,'sealed_utc':now(),'retry_future_opened':False})
 write(BASE/'RETRY_FUTURE_OPEN.json',{'seal_sha256':sha(seal),'utc':now()})
 valid=[c for c in cases if (BASE/'cases'/c['id']/'selection.json').exists()]
 for i,c in enumerate(valid):
  p=BASE/'cases'/c['id'];m=p/'test_metrics.json'
  if not m.exists() and not (p/'eval_failure.json').exists():
   with (p/'evaluate.log').open('wb') as log:r=subprocess.run([sys.executable,__file__,'eval_one',c['id']],stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
   if r.returncode:write(p/'eval_failure.json',{'exit_code':r.returncode,'log_sha256':sha(p/'evaluate.log'),'utc':now()})
  write(BASE/'STATUS.json',{'stage':'RETRY_EVALUATION','completed':i+1,'total':len(valid),'last':c['id'],'updated_utc':now()});print('retry evaluation',i+1,'/',len(valid),flush=True)
 write(BASE/'STATUS.json',{'stage':'RETRY_COMPLETE','total':len(cases),'selection_success':len(valid),'evaluation_success':sum((BASE/'cases'/c['id']/'test_metrics.json').exists() for c in valid),'updated_utc':now()})
if __name__=='__main__':main()
