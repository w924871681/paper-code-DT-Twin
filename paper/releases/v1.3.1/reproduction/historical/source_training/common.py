import os,json,time,hashlib,errno,sys
from pathlib import Path
from datetime import datetime,timezone
RUN=Path(r'E:\MSA_DTI_FULL_RERUN_20261022');CODE=RUN/'code';HERE=Path(__file__).resolve().parent
def utc():return datetime.now(timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def write(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+f'.{os.getpid()}.{time.time_ns()}.tmp')
    t.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    deadline=time.monotonic()+8.;delay=.01;attempts=0
    while True:
        try:
            os.replace(t,p)
            if attempts:print(f'[IO RECOVERED] {p.name}: {attempts} transient replacement retries',file=sys.stderr,flush=True)
            return
        except OSError as exc:
            transient=getattr(exc,'winerror',None) in {5,32,33} or exc.errno in {errno.EACCES,errno.EBUSY}
            if not transient or time.monotonic()>=deadline:raise
            attempts+=1;time.sleep(delay);delay=min(.25,delay*2)

def write_progress(p,obj):
    # Progress is an observer snapshot. A sharing violation must not discard
    # scientific work or terminate supervision of already-running workers.
    try:write(p,obj);return True
    except OSError as exc:
        if getattr(exc,'winerror',None) not in {5,32,33} and exc.errno not in {errno.EACCES,errno.EBUSY}:raise
        print(f'[PROGRESS WRITE DEFERRED] {p}: {exc}; next update will retry',file=sys.stderr,flush=True)
        return False
def event(kind,**kw):
    with (RUN/'WAL.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(utc=utc(),kind=kind,**kw),ensure_ascii=False)+'\n')
