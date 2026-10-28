import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'): os.environ[k]='1'
import sys,pathlib,json,csv,io,zipfile,datetime,hashlib,math,time,traceback
import numpy as np,torch
BASE=pathlib.Path(__file__).resolve().parent
ROOT=pathlib.Path(__file__).resolve().parent.parent
HIST=ROOT/'reproduction'/'historical'
sys.path[:0]=[str(HIST/'code'),str(HIST/'features'),str(ROOT/'selection')]
from core.space import ArchSpec,build_model,profile_arch
from core.methods.ours.stage2_runtime import configure_stage2_runtime,candidate_backend_context
from frozen_features import causal_features,raw_role_bounds
from frozen_adapt import _fixed_target_adapt
from frozen_seed import seed_all
from frozen_policy import gate,rank
from replay_selection import LIMITS
NORM=json.loads((ROOT/'data/source_normalization.json').read_text(encoding='utf8'))
ARCH=json.loads((ROOT/'data/candidate_architectures.json').read_text(encoding='utf8'))
Q=ARCH['qaxis'];DEVICE=torch.device('cuda')
DTYPE=np.dtype([('timestamp','<i8'),('raw','<f8',(10,))])
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def write(p,x):
 p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def seed(vm,h,k):return int.from_bytes(hashlib.sha256(f'external-v133|{vm}|{h}|{k}'.encode()).digest()[:4],'big')
def load_raw(source,member,start,n):
 with zipfile.ZipFile(source) as z, z.open(member) as f:
  reader=csv.reader(io.TextIOWrapper(f,encoding='utf-8-sig',newline=''),delimiter=';');header=[x.strip().strip('"') for x in next(reader)]
  timestamp_name='Timestamp' if 'Timestamp' in header else 'Timestamp [ms]'
  fields=[timestamp_name]+NORM['raw_metric_columns'];ix=[header.index(x) for x in fields]; rows=[];t0=None
  for j,row in enumerate(reader):
   if j<start:continue
   if len(rows)==n:break
   t=row[ix[0]].strip()
   try: timestamp=int(float(t))
   except ValueError:
    date=datetime.datetime.strptime(t,'%d.%m.%Y %H:%M:%S');t0=t0 or date;timestamp=int((date-t0).total_seconds())
   vals=[]
   for idx in ix[1:]:
    try:vals.append(float(row[idx].strip().replace(',','.')))
    except (ValueError,IndexError):vals.append(float('nan'))
   rows.append((timestamp,vals))
  if len(rows)!=n:raise ValueError('SHORT_INPUT')
 return np.array(rows,dtype=DTYPE)
def calc(raw,h,k):
 b=raw_role_bounds(h,k);T=b['validation'][1]-1;B=b['test'][1]-b['test'][0]-96-h+1
 f=causal_features(raw['timestamp'],raw['raw'],NORM)
 so=np.arange(95,95+k);vo=np.arange(b['validation'][0]+95,b['validation'][1]-h)
 def labels(o):
  z=raw['raw'][o[:,None]+np.arange(1,h+1),3];return (z/100).astype(np.float32),np.isfinite(z).all(1)&(z>=0).all(1)
 ys,ms=labels(so);yv,mv=labels(vo)
 if not ms.all():raise ValueError('INVALID_SUPPORT_LABEL')
 vo=vo[mv];yv=yv[mv]
 if len(vo)<B:raise ValueError('INSUFFICIENT_VALIDATION_LABELS')
 def inputs(o):return np.stack([f[i-95:i+1] for i in o]).astype(np.float32)
 return dict(T=T,B=B,Xs=inputs(so),ys=ys,Xv=inputs(vo),yv=yv,n_validation=len(vo))
def cp_path(q,h):
 names={'PT_A57_ref':'A57-PT','C1_A57_pair':'A57-C1'}
 p=ROOT/'reproduction/checkpoints'/f'{q}_H{h}.pt'
 return p if p.exists() else p.with_name(f'{names.get(q,q)}_H{h}.pt')
def run_select(raw,vm,h,k,out):
 d=calc(raw,h,k); scores=[];keys={};out.mkdir(parents=True,exist_ok=True)
 for q in Q:
  spec=ArchSpec(**ARCH['specs'][q]);resources=ARCH['resources_by_H'][str(h)][q];pa,op=profile_arch(spec,96,25,h)
  if (pa,op)!=(resources['params'],resources['operations']):raise ValueError('RESOURCE_MISMATCH')
  keys[q]=[pa,op,spec.arch_id,q];sd=seed(vm,h,k);seed_all(sd,DEVICE)
  model=build_model(spec,25,h,96,device=str(DEVICE)); loaded=torch.load(cp_path(q,h),map_location='cpu',weights_only=True);model.load_state_dict(loaded.get('state_dict',loaded),strict=True)
  with torch.backends.cudnn.flags(enabled=False):_fixed_target_adapt(model,torch.from_numpy(d['Xs']),torch.from_numpy(d['ys']),seed=sd)
  model.eval()
  with candidate_backend_context(spec,DEVICE,'gru-native'),torch.no_grad():
   pred=model(torch.from_numpy(d['Xv']).to(DEVICE)).cpu().numpy().astype(np.float64)
  loss=float(np.square(pred-d['yv'].astype(np.float64)).mean())
  if not math.isfinite(loss):raise ValueError('NONFINITE_VALIDATION')
  scores.append(loss);torch.save({a:b.detach().cpu() for a,b in model.state_dict().items()},out/(q+'.pt'));del model
 actions={}
 for budget,(pl,ol) in LIMITS.items():
  feas=[q for q in Q if keys[q][0]<=pl and keys[q][1]<=ol]
  if 'A55' not in feas:raise ValueError('A55_INFEASIBLE')
  e={'qaxis':Q,'F':feas,'keys':keys};a,_=gate(e,scores,'A55',.05,False)
  actions[budget]={'selected':rank(e,a,scores),'feasible':feas,'admissible':a}
 result={'vm':vm,'h':h,'k':k,'T':d['T'],'B':d['B'],'n_validation':d['n_validation'],'scores':dict(zip(Q,scores)),'actions':actions,'weights':{q:sha(out/(q+'.pt')) for q in Q}}
 write(out/'selection.json',result);return result
def run_eval(raw,sel,out):
 h=sel['h'];T=sel['T'];B=sel['B'];f=causal_features(raw['timestamp'],raw['raw'],NORM);o=np.arange(T,T+B)
 x=np.stack([f[i-95:i+1] for i in o]).astype(np.float32);z=raw['raw'][o[:,None]+np.arange(1,h+1),3];mask=np.isfinite(z).all(1)&(z>=0).all(1);y=(z/100).astype(np.float32)
 if not mask.any():raise ValueError('NO_VALID_TEST_LABELS')
 metrics={}
 for q in Q:
  if sha(out/(q+'.pt'))!=sel['weights'][q]:raise ValueError('CHANGED_WEIGHT')
  spec=ArchSpec(**ARCH['specs'][q]);model=build_model(spec,25,h,96,device=str(DEVICE));model.load_state_dict(torch.load(out/(q+'.pt'),map_location='cpu',weights_only=True));model.eval()
  with candidate_backend_context(spec,DEVICE,'gru-native'),torch.no_grad():p=model(torch.from_numpy(x).to(DEVICE)).cpu().numpy().astype(np.float64)
  if not np.isfinite(p).all():raise ValueError('NONFINITE_TEST_PREDICTION')
  err=p[mask]-y[mask].astype(np.float64);w=np.square(err).mean(1);n=max(1,round(.1*len(w)))
  metrics[q]={'MSE':float(w.mean()),'MAE':float(np.abs(err).mean()),'Worst10':float(np.sort(w)[-n:].mean()),'N_valid':int(mask.sum()),'B':B};del model
 write(out/'test_metrics.json',metrics);return metrics
if __name__=='__main__':
 torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True);configure_stage2_runtime(DEVICE,'gru-native')
 if sys.argv[1]=='smoke':
  h,k=1,10;b=raw_role_bounds(h,k);T=b['validation'][1]-1;B=b['test'][1]-b['test'][0]-96-h+1
  raw=np.zeros(T+B+h,dtype=DTYPE);raw['timestamp']=np.arange(len(raw))*300;raw['raw'][:]=1;raw['raw'][:,3]=40+5*np.sin(np.arange(len(raw))/13)
  p=BASE/'engineering_full_chain';s=run_select(raw[:T+1],'synthetic-smoke',h,k,p);m=run_eval(raw,s,p)
  assert len(m)==7 and set(s['actions'])==set(LIMITS)
  print(json.dumps({'status':'PASS','synthetic_only':True,'candidates':len(m),'budgets':len(s['actions'])}))
 elif sys.argv[1] in ('select','seal','evaluate'):
  lock=json.loads((BASE/'PROTOCOL_LOCK.json').read_text(encoding='utf8'))
  if sha(__file__)!=lock['runner_sha256']:raise ValueError('RUNNER_CHANGED_AFTER_LOCK')
  for path,h in lock['frozen_file_hashes'].items():
   if sha(path)!=h:raise ValueError('FROZEN_INPUT_CHANGED')
  phase=sys.argv[1];cases=lock['cases'];runroot=BASE/'validation_run_v2'
  if phase=='select':
   for idx,c in enumerate(cases):
    p=runroot/c['id'];p.mkdir(parents=True,exist_ok=True)
    if (p/'selection.json').exists() or (p/'failure.json').exists():continue
    h,k=c['H'],c['K'];b=raw_role_bounds(h,k);T=b['validation'][1]-1
    try:
     raw=load_raw(c['archive'],c['member'],c['start'],T+1)
     run_select(raw,c['vm'],h,k,p)
    except Exception as ex:
     write(p/'failure.json',{'stage':'selection','error':repr(ex),'traceback':traceback.format_exc()})
    print('selection',idx+1,'/',len(cases),c['id'],flush=True)
   print('selection complete; run seal separately',flush=True)
  elif phase=='seal':
   receipts=[]
   for c in cases:
    p=runroot/c['id'];f=p/'selection.json';fail=p/'failure.json'
    if not f.exists() and not fail.exists():raise ValueError('SELECTION_INCOMPLETE')
    if f.exists():
     s=json.loads(f.read_text(encoding='utf8'))
     for q,h in s['weights'].items():
      if sha(p/(q+'.pt'))!=h:raise ValueError('BAD_WEIGHT')
    target=f if f.exists() else fail;receipts.append({'id':c['id'],'file':str(target),'sha256':sha(target),'status':'selected' if f.exists() else 'failed'})
   write(runroot/'ACTION_SEAL.json',{'protocol_sha256':sha(BASE/'PROTOCOL_LOCK.json'),'receipts':receipts,'future_opened':False})
   print('selection actions sealed:',len(receipts),flush=True)
  else:
   seal=runroot/'ACTION_SEAL.json';s=json.loads(seal.read_text(encoding='utf8'))
   if s['protocol_sha256']!=sha(BASE/'PROTOCOL_LOCK.json'):raise ValueError('PROTOCOL_CHANGED')
   for r in s['receipts']:
    if sha(r['file'])!=r['sha256']:raise ValueError('ACTION_CHANGED')
   openfile=runroot/'EVALUATION_OPEN.json'
   if not openfile.exists():write(openfile,{'action_seal_sha256':sha(seal),'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event':'future_labels_opened'})
   elif json.loads(openfile.read_text(encoding='utf8'))['action_seal_sha256']!=sha(seal):raise ValueError('EVALUATION_SEAL_CHANGED')
   for idx,c in enumerate(cases):
    p=runroot/c['id'];sp=p/'selection.json'
    if not sp.exists() or (p/'test_metrics.json').exists() or (p/'eval_failure.json').exists():continue
    try:
     selected=json.loads(sp.read_text(encoding='utf8'));n=selected['T']+selected['B']+c['H']
     raw=load_raw(c['archive'],c['member'],c['start'],n);run_eval(raw,selected,p)
    except Exception as ex:write(p/'eval_failure.json',{'stage':'evaluation','error':repr(ex),'traceback':traceback.format_exc()})
    print('evaluation',idx+1,'/',len(cases),c['id'],flush=True)
   print('evaluation finished; preserve all failures',flush=True)
 else:raise ValueError('unknown phase')
