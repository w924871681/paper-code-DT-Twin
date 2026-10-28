"""Seven paper baselines on physically prefix-only input. No future inference.

One worker owns whole cases, so cross-method/budget cache writes never race.
Run engineering before production. Production additionally requires the parent
PROTOCOL_LOCK.json and baseline/ENGINEERING_PASS.json.
"""
import os
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='1'
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
import argparse,copy,gc,hashlib,importlib.util,io,json,random,sys,time,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent
RUN=HERE.parent
REAL=Path('D:/审稿/MSA_DTI_T7_LIMITED_BITBRAINS_REAL_20261025')
OLD=Path('E:/MSA_DTI_FULL_RERUN_20261022')
REPO=Path('D:/审稿/paper-code-DT-Twin-fullrelease-20261013')
sys.path.insert(0,str(REPO));sys.path.append(str(REAL/'code'))
import numpy as np
import torch
import torch.profiler._cupti_monitor
import torch.xpu
import torch.mtia
from core.config import load_and_merge
from core.space import enumerate_A_base,build_model,profile_arch
from core.methods.ours.stage2_runtime import configure_stage2_runtime,candidate_backend_context
from core.methods.ours.weight_bank import make_bank_key_shared
from core.utils.metrics import eval_mae,eval_weighted_mse,eval_worst10
import native_main as native
import native_hmeta as hm
spec=importlib.util.spec_from_file_location('t7_prefix_common',REAL/'code/common.py');m2=importlib.util.module_from_spec(spec);spec.loader.exec_module(m2)
import frozen_features
read,sha,write,digest,arrhash=m2.read,m2.sha,m2.write,m2.digest,m2.arrhash
METHODS=('pt_ft','medet_style','scratch50','meta_nas_lite','h_meta_nas','zero_nas','zero_nas_ft')
DEVICE=torch.device('cuda')
def state(m):return {k:v.detach().cpu().clone() for k,v in m.state_dict().items()}
def statehash(st):return digest({k:arrhash(v.numpy()) for k,v in sorted(st.items())})
def savept(p,st):
 b=io.BytesIO();torch.save(st,b);p.write_bytes(b.getvalue())
def loadpt(p):return torch.load(io.BytesIO(p.read_bytes()),map_location='cpu',weights_only=True)
def build(idx,H,st,seed):
 native.seed_all(seed,DEVICE);m=build_model(ARCH[idx],25,H,96,device='cuda')
 if st is not None:m.load_state_dict(st,strict=True)
 return m
def metric_pred(m,x,y,idx):
 m.eval()
 with candidate_backend_context(ARCH[idx],DEVICE,'gru-native'),torch.no_grad():
  p=m(x.to(DEVICE).contiguous());yy=y.to(DEVICE).contiguous()
  val={'weighted_mse':float(eval_weighted_mse(p,yy)),'mae':float(eval_mae(p,yy)),'worst10':float(eval_worst10(p,yy,p=.10))}
  pred=p.detach().cpu().numpy()
 if not np.isfinite(pred).all() or not all(np.isfinite(list(val.values()))):raise RuntimeError('NONFINITE_VALIDATION')
 return val,pred
def key_for(idx,seed,recipe,source):return digest(dict(prefix=CURRENT['prefix_sha'],H=CURRENT['case']['H'],arch=idx,seed=seed,recipe=recipe,source=source,native=CURRENT['native_hash'],torch=torch.__version__,backend='cuda-gru-native'))
def cached_adapt(idx,st,source,seed,recipe,xs,ys,xv,yv):
 key=key_for(idx,seed,recipe,source);folder=CURRENT['cache']/key;folder.mkdir(parents=True,exist_ok=True);receipt=folder/'receipt.json'
 CURRENT['logical_adaptations']+=1
 if receipt.exists():
  r=read(receipt)
  for n,h in r['files'].items():assert sha(folder/n)==h,'CACHE_HASH_CHANGED'
  m=build(idx,CURRENT['case']['H'],loadpt(folder/'state.pt'),seed)
  CURRENT['cache_hits']+=1;CURRENT['events'].append(dict(kind='CANDIDATE_CACHE_REUSE',key=key,arch=idx,recipe=recipe,seed=seed))
  return m,r['validation'],r
 tick=time.perf_counter()
 if recipe=='hmeta_sgd_mse_50':
  m,_=hm._adapt_and_validate(spec=ARCH[idx],state=st,Xs=xs,ys=ys,Xv=xv,yv=yv,H=CURRENT['case']['H'],L=96,input_dim=25,device=DEVICE,seed=seed)
 else:
  m=build(idx,CURRENT['case']['H'],st,seed)
  with candidate_backend_context(ARCH[idx],DEVICE,'gru-native'):
   if recipe=='adam_huber_50':native._search_target_adapt(m,xs,ys,seed=seed)
   else:native._fixed_target_adapt(m,xs,ys,seed=seed)
 torch.cuda.synchronize();adapt_seconds=time.perf_counter()-tick
 val,pv=metric_pred(m,xv,yv,idx);ss=state(m);savept(folder/'state.pt',ss)
 b=io.BytesIO();np.savez_compressed(b,predictions=pv);(folder/'validation.npz').write_bytes(b.getvalue())
 r={'identity':key,'arch':idx,'seed':seed,'recipe':recipe,'source':source,'steps':50,'state_sha256':statehash(ss),'validation':val,'adapt_seconds':adapt_seconds,'files':{n:sha(folder/n) for n in ['state.pt','validation.npz']}}
 write(receipt,r);CURRENT['actual_adaptations']+=1;CURRENT['events'].append(dict(kind='ADAPT_COMPLETE',key=key,arch=idx,recipe=recipe,seed=seed,steps=50,seconds=adapt_seconds))
 return m,val,r
def search(method,H,tier,seed,xs,ys,xv,yv):
 # Call the exact original search routine. Its Adam adaptation passes seed
 # only to minibatch generation, so dropout RNG carries across shortlist
 # positions. Candidate-seed-only caching would change that native procedure.
 bank={make_bank_key_shared(H=H,arch_key=ARCH[i].arch_key,input_dim=25,L=96):st for i,st in C1[H].items()}
 model,spec,row,detail,count,adapted=native._run_search_case(method,{'bank':bank,'pi50':PI},CFG,ARCH,DEVICE,'gru-native',xs,ys,xv,yv,tier,H,25,96,seed)
 CURRENT['logical_adaptations']+=adapted;CURRENT['actual_adaptations']+=adapted
 CURRENT['events'].append({'kind':'NATIVE_SEARCH_COMPLETE','method':method,'budget':tier,'candidate_count':count,'actual_adaptations':adapted,'cross_candidate_rng':'original uninterrupted sequence','steps_each':50 if adapted else 0})
 selected=state(model);idx=row['arch_idx'];del model
 detail['feasible_arch_indices']=native.feasible_indices(CFG,ARCH,tier,96,25,H)
 return selected,idx,detail

def hmeta(H,tier,seed,xs,ys,xv,yv):
 feas=native.feasible_indices(CFG,ARCH,tier,96,25,H);rng=random.Random(seed);pop=rng.sample(feas,min(6,len(feas)));visited=set();rows=[];best=None;bst=None
 for generation in range(2):
  gr=[]
  for idx in pop:
   if idx in visited:continue
   st=HM['states'][hm._state_key(H,idx)];m,val,rec=cached_adapt(idx,st,HMHASH,seed+idx+10000*generation,'hmeta_sgd_mse_50',xs,ys,xv,yv)
   pa,op=profile_arch(ARCH[idx],96,25,H);row={'arch_idx':idx,'params':pa,'operations':op,'validation':val,'generation':generation,'adapt_identity':rec['identity']};rows.append(row);gr.append(row);visited.add(idx);lex=(val['weighted_mse'],pa,op,idx)
   if best is None or lex<best:best=lex;bst=state(m)
   del m
  if generation==0:
   pop=[]
   for p in sorted(gr,key=lambda r:(r['validation']['weighted_mse'],r['arch_idx']))[:3]:
    mut=hm._mutants(p['arch_idx'],feas,visited|set(pop),ARCH,rng)
    if mut:pop.append(mut[0])
   remain=[i for i in feas if i not in visited and i not in pop];rng.shuffle(remain);pop+=remain[:max(0,6-len(pop))]
 return bst,best[3],{'evaluated_candidates':rows,'feasible_arch_indices':feas}
def main(args):
 global CFG,ARCH,C1,C1HASH,PI,HM,HMHASH,CURRENT
 torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True);configure_stage2_runtime(DEVICE,'gru-native')
 audit=read(HERE/'ASSET_AUDIT.json');assert audit['status']=='PASS'
 for p,r in audit['assets'].items():assert sha(p)==r['sha256'],'SOURCE_ASSET_DRIFT:'+p
 if args.role!='engineering':assert (RUN/'PROTOCOL_LOCK.json').is_file() and read(HERE/'ENGINEERING_PASS.json')['status']=='PASS','PRODUCTION_GATE'
 CFG=load_and_merge('ours',main_module='configs.main_cfg',methods_pkg='configs.methods',smoke=False);ARCH=enumerate_A_base(CFG.main.arch)
 C1={};C1HASH={};MED={};PT={}
 for H in [1,4]:
  meta=read(OLD/f'source_assets/c1_H{H}.json')['states'];C1[H]={int(i):loadpt(Path(r['path']))['state_dict'] for i,r in meta.items()};C1HASH[H]={int(i):r['sha256'] for i,r in meta.items()}
  MED[H]=loadpt(OLD/f'source_assets/medet/H{H}.pt')['state_dict'];v=loadpt(REAL/f'frozen/checkpoints/PT_A57_ref_H{H}.pt');PT[H]=v.get('state_dict',v)
 PI=read(OLD/'source_assets/pi50.json')['pi50'];HM=loadpt(OLD/'source_assets/hmeta.pt');HMHASH=sha(OLD/'source_assets/hmeta.pt')
 norm=read(REAL/'frozen/source_normalization.json');lock=read(REAL/'ROLE_LOCK.json');cases=[c for c in lock['cases'] if c['role']==args.role]
 if args.case:cases=[c for c in cases if c['slug']==args.case]
 cases=cases[args.worker::args.workers]
 if args.limit:cases=cases[:args.limit]
 methods=args.methods.split(',') if args.methods else list(METHODS);assert set(methods)<=set(METHODS)
 budgets=args.budgets.split(',');assert set(budgets)<={'medium','tight','loose'}
 # Initialize optimizer machinery before entering the IO capability guard.
 dummy=torch.nn.Linear(1,1).cuda();torch.optim.SGD(dummy.parameters(),lr=.01);torch.optim.Adam(dummy.parameters());torch.zeros(1,device='cuda').sum().item();del dummy
 nativehash=digest({str(p):sha(p) for p in [HERE/'native_main.py',HERE/'native_hmeta.py',HERE/'prefix_worker.py']})
 job=f'{args.role}_w{args.worker}_n{args.workers}'+('_'+args.tag if args.tag else '');started=time.time();completed=[]
 for ci,c in enumerate(cases):
  folder=HERE/'selection'/c['slug'];folder.mkdir(parents=True,exist_ok=True);prefix=REAL/'prefix'/c['slug']/'prefix.bin';pr=read(prefix.parent/'receipt.json');assert pr['case']==c and sha(prefix)==pr['prefix_sha256']
  CURRENT={'case':c,'prefix_sha':sha(prefix),'native_hash':nativehash,'cache':HERE/'candidate_cache'/c['slug'],'logical_adaptations':0,'actual_adaptations':0,'cache_hits':0,'events':[],'proxies':{}}
  # Torch inspects Python source while seeding/profiling. Authorize source code
  # files only, never an entire data directory or arbitrary NPZ/checkpoint input.
  runtime_sources=list(Path(torch.__file__).parent.rglob('*.py'))+list(Path(torch.__file__).parent.rglob('*.pyc'))
  guard=m2.Guard([prefix,HERE/'prefix_worker.py',HERE/'native_main.py',HERE/'native_hmeta.py',*runtime_sources,*list((REPO/'core').rglob('*.py')),*list((REPO/'configs').rglob('*.py')),*list((REAL/'code').rglob('*.py'))],[HERE/'candidate_cache',folder,HERE/'progress',HERE/'logs'])
  try:
   with guard:
    d=m2.prefix_selection(c,prefix,norm);xs,ys,xv,yv=[torch.from_numpy(d[n]) for n in ['Xs','ys','Xv','yv']];case_tick=time.perf_counter()
    for method in methods:
     for tier in budgets:
      actionfile=folder/f'{method}_{tier}.json';identity=digest({'case':c,'prefix':CURRENT['prefix_sha'],'native':nativehash,'method':method,'tier':tier})
      if actionfile.exists():
       old=read(actionfile);assert old['identity']==identity and sha(folder/old['model_file'])==old['model_sha256'],'SEALED_ACTION_DRIFT';continue
      tick=time.perf_counter();before=CURRENT['actual_adaptations'];s=c['seed'];H=c['H'];detail={}
      if method in ['pt_ft','medet_style','scratch50']:
       st=PT[H] if method=='pt_ft' else MED[H] if method=='medet_style' else None
       source=audit['assets'][str(REAL/f'frozen/checkpoints/PT_A57_ref_H{H}.pt')]['sha256'] if method=='pt_ft' else audit['assets'][str(OLD/f'source_assets/medet/H{H}.pt')]['sha256'] if method=='medet_style' else 'random'
       m,val,rec=cached_adapt(57,st,source,s,'sgd_mse_50',xs,ys,xv,yv);selected=state(m);idx=57;detail={'validation':val,'adapt_identity':rec['identity']};del m
      elif method=='h_meta_nas':selected,idx,detail=hmeta(H,tier,s,xs,ys,xv,yv)
      else:selected,idx,detail=search(method,H,tier,s,xs,ys,xv,yv)
      torch.cuda.synchronize();seconds=time.perf_counter()-tick;feas=native.feasible_indices(CFG,ARCH,tier,96,25,H);assert idx in feas
      model_file=f'{method}_{tier}.pt';savept(folder/model_file,selected);pa,op=profile_arch(ARCH[idx],96,25,H)
      action={'status':'PREFIX_ACTION_SEALED','identity':identity,'case':c,'method':method,'budget':tier,'selected_arch':idx,'spec':ARCH[idx].to_dict(),'params':pa,'operations':op,'feasible_arch_indices':feas,'details':detail,'model_file':model_file,'model_sha256':sha(folder/model_file),'tensor_sha256':statehash(selected),'prefix_sha256':CURRENT['prefix_sha'],'input_hashes':{n:arrhash(d[n]) for n in ['Xs','ys','Xv','yv']},'native_hash':nativehash,'logical_adaptations':1 if method in ['pt_ft','medet_style','scratch50'] else 0 if method=='zero_nas' else 12,'new_adaptations':CURRENT['actual_adaptations']-before,'online_seconds_observed':seconds,'timing_mode':'shared_worker_not_publication_latency','future_arrays_loaded':False,'seed':s}
      write(actionfile,action);print(c['slug'],method,tier,'seconds',round(seconds,3),'actual',action['new_adaptations'],flush=True)
    CURRENT['elapsed_seconds']=time.perf_counter()-case_tick
   access={'case_id':c['case_id'],'events':guard.events,'future_capability':False,'all_access_allowed':all(e.get('allowed') for e in guard.events)};write(folder/f'ACCESS_{job}.json',access)
   assert access['all_access_allowed'],'IO_GUARD_DENIED_ACCESS_REQUIRES_ENGINEERING_REPAIR'
   stats={k:v for k,v in CURRENT.items() if k not in ['cache','proxies']};write(folder/f'RUN_{job}.json',stats);completed.append(c['slug'])
   write(HERE/'progress'/f'{job}.json',{'status':'RUNNING','completed':len(completed),'expected':len(cases),'elapsed_seconds':time.time()-started,'last_case':c['slug'],'pid':os.getpid()})
  except BaseException as ex:
   write(folder/f'FAILURE_{job}.json',{'error':repr(ex),'traceback':traceback.format_exc(),'events':guard.events});raise
  gc.collect();torch.cuda.empty_cache()
 write(HERE/'progress'/f'{job}.json',{'status':'COMPLETE','completed':len(completed),'expected':len(cases),'elapsed_seconds':time.time()-started,'pid':os.getpid()})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('role',choices=['engineering','calibration','evaluation']);p.add_argument('--worker',type=int,default=0);p.add_argument('--workers',type=int,default=1);p.add_argument('--case');p.add_argument('--limit',type=int);p.add_argument('--methods');p.add_argument('--budgets',default='medium,tight,loose');p.add_argument('--tag',default='');main(p.parse_args())
