import csv,datetime,hashlib,json,os,sys
from pathlib import Path
import numpy as np

DTYPE=np.dtype([('timestamp','<i8'),('raw','<f8',(10,))])

def require(v,m):
    if not v:raise RuntimeError(m)


def digest(x):return hashlib.sha256(canon(x).encode()).hexdigest()


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8388608),b''):h.update(b)
    return h.hexdigest()


def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def write(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp')
    tmp.write_text(canon(x)+'\n',encoding='utf-8');os.replace(tmp,p)


def arrhash(a):
    a=np.ascontiguousarray(a);return digest(dict(dtype=str(a.dtype),shape=list(a.shape),bytes=hashlib.sha256(a.tobytes()).hexdigest()))


class Guard:
    def __init__(self,reads,writes):self.reads={str(Path(p).resolve()) for p in reads};self.writes=[Path(p).resolve() for p in writes];self.events=[];self.active=False
    def hook(self,event,args):
        if not self.active:return
        if event=='open':
            p,mode,flags=args
            if isinstance(p,int):raise PermissionError('UNLISTED_FD')
            p=Path(os.fsdecode(p)).resolve();writing=bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_APPEND|os.O_TRUNC))
            output=any(p.is_relative_to(x) for x in self.writes)
            ok=output or (str(p) in self.reads and not writing)
            self.events.append(dict(event='open',path=str(p),write=writing,allowed=ok))
            if not ok:raise PermissionError('CAPABILITY_DENIED:'+str(p))
        elif event.startswith(('socket.','subprocess.')) or event in ('os.system','ctypes.dlopen'):
            self.events.append(dict(event=event,allowed=False));raise PermissionError('EXTERNAL_CAPABILITY_DENIED')
        elif event=='import' and any(x in args[0] for x in ('cache_v2','data_v2','evaluate')):
            self.events.append(dict(event=event,module=args[0],allowed=False));raise PermissionError('OLD_OR_EVALUATOR_IMPORT_DENIED')
    def __enter__(self):sys.addaudithook(self.hook);self.active=True;return self
    def __exit__(self,*x):self.active=False


def prefix_selection(c,p,norm):
    from frozen_features import causal_features,raw_role_bounds
    T,H,K=c['T'],c['H'],c['K'];bounds=raw_role_bounds(H,K)
    require(p.stat().st_size==(T+1)*DTYPE.itemsize,'PREFIX_MIXED_OR_TRUNCATED')
    rows=np.frombuffer(p.read_bytes(),dtype=DTYPE);t=rows['timestamp'].copy();raw=rows['raw'].copy();f=causal_features(t,raw,norm)
    so=np.arange(95,95+K,dtype=np.int64);lo,hi=bounds['validation'];vo=np.arange(lo+95,hi-H,dtype=np.int64)
    def labels(o):
        ix=o[:,None]+np.arange(1,H+1);require(ix.max()<=T,'LABEL_OUTSIDE_PREFIX')
        cpu=raw[ix,3];return (cpu/100).astype(np.float32),np.all(np.isfinite(cpu)&(cpu>=0),axis=1)
    sy,sm=labels(so);vy,vm=labels(vo);require(sm.all(),'SUPPORT_INVALID');vo=vo[vm];vy=vy[vm]
    require(len(vo)>=c['B'] and vo[-1]+H==T,'MATURE_ENDPOINT_OR_COUNT_INVALID')
    def inputs(o):return np.stack([f[i-95:i+1] for i in o]).astype(np.float32)
    require(not(set((so[:,None]+np.arange(1,H+1)).ravel())&set((vo[:,None]+np.arange(1,H+1)).ravel())),'SUPPORT_VAL_OVERLAP')
    return dict(Xs=inputs(so),ys=sy,Xv=inputs(vo),yv=vy,origins=vo,support_origins=so,features=f,timestamps=t,raw=raw)

