"""Post-global-seal future evaluator. Never imported by selection/adaptation processes."""
import os
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='1'
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
import argparse,gc,io,sys,time,traceback,zipfile
from common import *
from metrics import task_metrics
sys.path.insert(0,str(REPO));sys.path.append(str(HISTORY/'code'))
import torch
import torch.profiler._cupti_monitor
import torch.xpu
import torch.mtia
from core.space import ArchSpec,build_model,profile_arch
from core.methods.ours.stage2_runtime import configure_stage2_runtime,candidate_backend_context
from frozen_features import causal_features
DTYPE=np.dtype([('timestamp','<i8'),('raw','<f8',(10,))])

def tensorhash(st):return digest({k:arrhash(v.detach().cpu().numpy()) for k,v in sorted(st.items())})
def load_state(path):
    st=torch.load(io.BytesIO(path.read_bytes()),map_location='cpu',weights_only=True)
    require(isinstance(st,dict) and all(isinstance(v,torch.Tensor) and torch.isfinite(v).all().item() for v in st.values()),'BAD_SEALED_STATE')
    return st

def forward(st,spec,c,xf):
    model=build_model(spec,25,c['H'],96,device='cuda');model.load_state_dict(st,strict=True);model.eval();before=tensorhash(model.state_dict());tick=time.perf_counter()
    with candidate_backend_context(spec,torch.device('cuda'),'gru-native'),torch.no_grad():
        p=model(torch.from_numpy(xf).cuda().contiguous()).detach().cpu().numpy().astype(np.float64)
    torch.cuda.synchronize();seconds=time.perf_counter()-tick
    require(np.isfinite(p).all(),'NONFINITE_FUTURE_PREDICTION');require(before==tensorhash(model.state_dict()),'INFERENCE_UPDATED_WEIGHTS')
    del model;gc.collect();torch.cuda.empty_cache();return p,seconds

def main(args):
    global_gate(args.global_seal_sha256)
    torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True);configure_stage2_runtime(torch.device('cuda'),'gru-native')
    torch.zeros(1,device='cuda').sum().item()
    # Preload codecs before exact per-case file capabilities are active.
    warm=io.BytesIO();np.savez(warm,x=np.zeros(1));warm.seek(0)
    with np.load(warm,allow_pickle=False) as z:require(z['x'][0]==0,'NUMPY_WARMUP')
    role=read(HISTORY/'ROLE_LOCK.json');cases=[c for c in role['cases'] if c['role']=='evaluation'][args.worker::args.workers]
    manifest=read(HISTORY/'OUTPUT_HASHES.json')['files'];norm=read(HISTORY/'frozen/source_normalization.json');arch=read(HISTORY/'code/Q7_ARCHITECTURES.json')
    bindings=read(RUN/'baseline/EVALUATION_ACTIONS_PRELABEL.json');protocol=read(RUN/'PROTOCOL_LOCK.json')
    allframework=read(RUN/'framework/EVAL_DEPLOYMENT_ACTIONS_PRELABEL.json');extra=read(ROOT/'ADDITIONAL_CONTROLS_PRELABEL.json')
    allframework+=extra['deployment']
    grid=read(RUN/'framework/actions/evaluation_all_tau_actions.json')+extra['same_tau']
    grid=[a for a in grid if a['tau'] is not None and a['method'] in ['CAP_A55','MEAN_A55','D_LINEAR_A55','ORIGINAL_FULL','ORIGINAL_PAIR']]
    sources=list(Path(torch.__file__).parent.rglob('*.py'))+list(Path(torch.__file__).parent.rglob('*.pyc'))+list((REPO/'core').rglob('*.py'))+list((REPO/'configs').rglob('*.py'))+list((HISTORY/'code').rglob('*.py'))+list(ROOT.glob('*.py'))
    started=time.time()
    for ci,c in enumerate(cases):
        out=ROOT/'case_cache'/c['slug'];out.mkdir(parents=True,exist_ok=True)
        receipt=out/'receipt.json'
        if receipt.exists():
            old=read(receipt);require(old['global_seal_sha256']==args.global_seal_sha256,'CACHE_GLOBAL_SEAL_CHANGED')
            for n,h in old['files'].items():require(sha(out/n)==h,'EVAL_CACHE_CHANGED')
            continue
        selected=[r for r in bindings if r['case_id']==c['case_id']]
        require(len(selected)==21,'BASELINE_CASE_ACTIONS')
        oldfolder=HISTORY/'evaluation_payload/evaluation'/c['slug'];rawpath=oldfolder/'evaluation_only.bin';qpath=oldfolder/'future_evaluation.npz';prefix=HISTORY/'prefix'/c['slug']/'prefix.bin'
        qweights={q:HISTORY/'selection'/c['slug']/(q+'.adapted.pt') for q in Q7}
        reads=[rawpath,qpath,prefix,*qweights.values(),*[Path(r['action_path']) for r in selected],*[Path(r['model_path']) for r in selected],*sources]
        guard=Guard(reads,[out]);case_started=time.time();physical=0;reuseq=0;reusenew=0;seconds_total=0;prediction_files={};records=[];forward_ledger=[]
        try:
            with guard:
                for p in [rawpath,qpath,prefix,*qweights.values()]:
                    relative=str(p.relative_to(HISTORY)).replace('\\','/');require(sha(p)==manifest[relative]['sha256'],'HISTORICAL_EVAL_BINDING:'+relative)
                raw=np.frombuffer(rawpath.read_bytes(),dtype=DTYPE);require(len(raw)==c['T']+c['B']+c['H'],'RAW_FUTURE_LENGTH');require(raw[:c['T']+1].tobytes()==prefix.read_bytes(),'FUTURE_PREFIX_MISMATCH')
                f=causal_features(raw['timestamp'],raw['raw'],norm);origins=np.arange(c['T'],c['T']+c['B'],dtype=np.int64);xf=np.stack([f[o-95:o+1] for o in origins]).astype(np.float32)
                cpu=raw['raw'][origins[:,None]+np.arange(1,c['H']+1)[None,:],3];mask=np.all(np.isfinite(cpu)&(cpu>=0),axis=1);targets=(cpu/100).astype(np.float32)
                with np.load(qpath,allow_pickle=False) as z:
                    require(np.array_equal(origins,z['origins']) and np.array_equal(mask,z['label_mask']) and np.array_equal(targets,z['targets'],equal_nan=True),'COMMON_TARGET_AXIS_MASK_MISMATCH')
                    qp=z['predictions'].copy();qloss=np.square(qp[:,mask]-targets[None,mask].astype(np.float64)).mean(axis=2)
                    require(np.array_equal(qloss,z['valid_losses']) and np.array_equal(qloss.mean(axis=1),z['E_obs']),'Q7_CACHE_METRIC_MISMATCH')
                qmetrics={q:task_metrics(qp[i],targets,mask) for i,q in enumerate(Q7)};qmkeys={};cache={}
                for i,q in enumerate(Q7):
                    st=load_state(qweights[q]);th=tensorhash(st);key=digest(dict(case_id=c['case_id'],spec=arch['specs'][q],tensor_sha256=th,input_sha256=arrhash(xf),backend='cuda/gru-native'));cache[key]=dict(predictions=qp[i],metrics=qmetrics[q],origin='existing_Q7');qmkeys[q]=key;del st
                baseline=[]
                for binding in selected:
                    ap=Path(binding['action_path']);mp=Path(binding['model_path']);require(sha(ap)==binding['action_sha256'] and sha(mp)==binding['model_sha256'],'BASELINE_ACTION_OR_WEIGHT_CHANGED')
                    a=read(ap);require(a['case']==c and a['status']=='PREFIX_ACTION_SEALED' and a['future_arrays_loaded'] is False,'BASELINE_SEAL_STATUS')
                    spec=ArchSpec(**a['spec']);pa,op=profile_arch(spec,96,25,c['H']);require((pa,op)==(a['params'],a['operations']),'BASELINE_RESOURCE_MISMATCH');st=load_state(mp);th=tensorhash(st);require(th==a['tensor_sha256'],'BASELINE_TENSOR_IDENTITY')
                    key=digest(dict(case_id=c['case_id'],spec=a['spec'],tensor_sha256=th,input_sha256=arrhash(xf),backend='cuda/gru-native'))
                    if key in cache:
                        pred=cache[key]['predictions'];met=cache[key]['metrics'];origin=cache[key]['origin'];reuseq+=int(origin=='existing_Q7');reusenew+=int(origin=='new_forward');secs=0.
                    else:
                        pred,secs=forward(st,spec,c,xf);met=task_metrics(pred,targets,mask);physical+=1;seconds_total+=secs;origin='new_forward';cache[key]=dict(predictions=pred,metrics=met,origin=origin)
                        pf=key+'.npz';buf=io.BytesIO();np.savez_compressed(buf,predictions=pred);(out/pf).write_bytes(buf.getvalue());prediction_files[key]=pf
                    limits=protocol['budgets']['limits'][a['budget']];resource_ok=pa<=limits['params_max'] and op<=limits['operations_max'] and a['selected_arch'] in a['feasible_arch_indices'];require(resource_ok,'INFEASIBLE_BASELINE_ACTION')
                    row=dict(case_id=c['case_id'],VM=c['VM'],H=c['H'],K=c['K'],B=c['B'],budget=a['budget'],method=BASELINE_NAMES[a['method']],source_method=a['method'],selected_token='ARCH_'+str(a['selected_arch']),selected_arch=a['selected_arch'],selected_identity=key,params=pa,operations=op,feasible_ids=a['feasible_arch_indices'],feasible_count=len(a['feasible_arch_indices']),resource_feasible=bool(resource_ok),reference_token=None,E_reference=None,harm_vs_reference=None,selected_at_floor=False,deployment_tau=None,deployment_policy='native_baseline',logical_adaptations=a['logical_adaptations'],physical_adaptations_recorded=a['new_adaptations'],online_seconds_observed=a['online_seconds_observed'],timing_scope=a['timing_mode'],prediction_origin=origin,**met)
                    baseline.append(row);forward_ledger.append(dict(method=a['method'],budget=a['budget'],model_sha256=a['model_sha256'],tensor_sha256=th,cache_key=key,prediction_origin=origin,new_forward_seconds=secs));del st
                pt={r['budget']:r for r in baseline if r['method']=='PT+FT'}
                def annotate(r):
                    ref=pt[r['budget']];same=r['selected_identity']==ref['selected_identity'];d=r['MSE']-ref['MSE'];r.update(E_PT_FT=ref['MSE'],Worst10_PT_FT=ref['Worst10'],PT_model_identity=ref['selected_identity'],same_action_vs_PT=bool(same),harm_vs_PT=int(d>0),benefit_vs_PT=int(d<0),action_class_vs_PT='same_action' if same else 'alternative_better' if d<0 else 'alternative_worse' if d>0 else 'alternative_equal_risk',gain_vs_PT=ref['MSE']-r['MSE'])
                    if same:require(r['MSE']==ref['MSE'],'SAME_ACTION_DIFFERENT_RISK')
                    return r
                records=[annotate(r) for r in baseline];taurows=[]
                def framework_row(a,mode):
                    q=a['selected_token'];ref=a['reference_token'];key=arch['resources_by_H'][str(c['H'])][q];limits=protocol['budgets']['limits'][a['budget']];feasible=key['params']<=limits['params_max'] and key['operations']<=limits['operations_max'] and q in a['feasible_ids'];require(feasible,'INFEASIBLE_FRAMEWORK_ACTION')
                    er=qmetrics[ref]['MSE'];es=qmetrics[q]['MSE'];fo=min(qmetrics[x]['MSE'] for x in a['feasible_ids']);ao=min(qmetrics[x]['MSE'] for x in a['admissible_ids'])
                    r=dict(a,method=FRAMEWORK_NAMES.get(a['method'],a['method']) if mode=='deployment' else a['method'],source_method=a['method'],selected_arch=arch['specs'][q]['arch_id'],selected_identity=qmkeys[q],params=key['params'],operations=key['operations'],feasible_count=len(a['feasible_ids']),resource_feasible=bool(feasible),E_reference=er,harm_vs_reference=int(q!=ref and es>er),same_action_vs_reference=q==ref,oracle_F=fo,oracle_A=ao,gate_loss=ao-fo,within_loss=es-ao,total_regret=es-fo,logical_adaptations=7,physical_adaptations_recorded=0,prediction_origin='existing_Q7',timing_scope='historical_cached_framework_no_new_online_timing',**qmetrics[q]);return annotate(r)
                records.extend(framework_row(a,'deployment') for a in allframework if a['case_id']==c['case_id'])
                taurows.extend(framework_row(a,'same_tau') for a in grid if a['case_id']==c['case_id'])
                write(out/'DEPLOYED_METRICS.json',records);write(out/'SAME_TAU_METRICS.json',taurows);write(out/'FORWARD_LEDGER.json',forward_ledger)
                write(out/'INPUT_IDENTITY.json',dict(case=c,raw_sha256=sha(rawpath),Q7_cache_sha256=sha(qpath),prefix_sha256=sha(prefix),X_sha256=arrhash(xf),targets_sha256=arrhash(targets),origins_sha256=arrhash(origins),mask_sha256=arrhash(mask),N_valid=int(mask.sum()),global_seal_sha256=args.global_seal_sha256))
            require(all(e['allowed'] for e in guard.events),'EVALUATION_CAPABILITY_DENIED')
            write(out/'ACCESS_LOG.json',dict(pid=os.getpid(),global_seal_sha256=args.global_seal_sha256,future_process=True,events=guard.events))
            files={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name not in ['receipt.json','FAILURE.json']}
            write(receipt,dict(status='COMPLETE',case_id=c['case_id'],global_seal_sha256=args.global_seal_sha256,created_utc=now(),files=files,logical_baseline_prediction_requests=21,new_baseline_forwards=physical,Q7_prediction_reuses=reuseq,new_prediction_cache_reuses=reusenew,historical_Q7_predictions_reused=7,new_adaptations=0,new_forward_seconds=seconds_total,wall_seconds=time.time()-case_started))
            write(ROOT/'progress'/f'eval_w{args.worker}.json',dict(status='RUNNING',completed=ci+1,total=len(cases),last_case=c['case_id'],pid=os.getpid(),elapsed_seconds=time.time()-started))
            print('Eval',args.worker,ci+1,'/',len(cases),c['slug'],'new_forwards',physical,flush=True)
        except BaseException as ex:
            write(out/'FAILURE.json',dict(error=repr(ex),traceback=traceback.format_exc(),global_seal_sha256=args.global_seal_sha256,events=guard.events,future_already_opened=True,utc=now()));raise
    write(ROOT/'progress'/f'eval_w{args.worker}.json',dict(status='COMPLETE',completed=len(cases),total=len(cases),pid=os.getpid(),elapsed_seconds=time.time()-started))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--global-seal-sha256',required=True);p.add_argument('--worker',type=int,default=0);p.add_argument('--workers',type=int,default=2);main(p.parse_args())
