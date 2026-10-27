import os,sys,random,hashlib
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='1'
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
from common import *
sys.path.insert(0,str(CODE))
import numpy as np
import torch
torch.set_num_threads(1);torch.set_num_interop_threads(1)
torch.use_deterministic_algorithms(True)
from experiments.r4_r5 import r5,bitbrains_data as data
from main_evaluation import pipeline as native
from core.space import build_model,profile_arch
from core.methods.ours.stage2_runtime import candidate_backend_context,configure_stage2_runtime
from core.methods.ours.weight_bank import make_bank_key_shared
REAL=Path(read(RUN/'BITBRAINS_INPUT_LOCK.json')['root']);DEVICE=torch.device('cuda')
configure_stage2_runtime(DEVICE,'gru-native')
CFG,ARCH=r5.cfg_arch()
DS=read(REAL/'bitbrains/data/bitbrains_dataset_manifest.json')
ASSETS=read(REAL/'bitbrains/source_checkpoint_manifest.json')['checkpoints']
def seed(s):r5.seed(int(s))
def case_seed(c,base=2904):return base+int(hashlib.sha256(c['machine_id'].encode()).hexdigest()[:8],16)+37*c['H']+53*c['K']
def role(c,name):
    x,y=data.load_role(REAL,c,name,allow_test=name=='test');return torch.from_numpy(x),torch.from_numpy(y)
def source_task(cid,H,K):
    with np.load(RUN/'source_tasks'/f's{cid}_h{H}_k{K}.npz',allow_pickle=False) as a:return tuple(torch.from_numpy(a[k].copy()) for k in ['Xs','ys','Xq','yq'])
def build(idx,H,state=None,s=2904):
    seed(s);m=build_model(ARCH[idx],input_dim=25,H=H,L=96,device='cuda')
    if state is not None:m.load_state_dict(state,strict=True)
    return m
def update(m,x,y,steps,s,search=False):
    if steps!=50:raise ValueError('native main adaptation is exactly 50 steps')
    # Backend guard is explicit and independent of model class introspection.
    with torch.backends.cudnn.flags(enabled=False):
        if search:native._search_target_adapt(m,x,y,seed=s)
        else:native._fixed_target_adapt(m,x,y,seed=s)
def pred(m,x,idx):
    m.eval()
    with candidate_backend_context(ARCH[idx],DEVICE,'gru-native'),torch.no_grad():return m(x.to(DEVICE).contiguous()).detach().cpu().numpy()
def metrics(p,y):
    z=np.asarray(p,dtype=float)-np.asarray(y,dtype=float);se=np.square(z).mean(1)
    return dict(weighted_mse=float(se.mean()),mae=float(abs(z).mean()),worst10=float(np.sort(se)[-max(1,round(.1*len(se))):].mean()))
def progress(j,done,total,detail):write_progress(RUN/'progress'/f"{j['id']}.json",dict(completed_cases=done,total_cases=total,detail=detail,utc=utc()))
def finish(j,outputs,**kw):
    write(RUN/'receipts/jobs'/f"{j['id']}.json",dict(job_id=j['id'],status='PASS',utc=utc(),outputs={str(p):sha(p) for p in outputs},**kw))
