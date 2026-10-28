import os,sys,zipfile
from common import *
sys.path.insert(0,str(CODE))
import numpy as np
from experiments.r4_r5 import bitbrains_data as data
def main(j):
    lk=read(RUN/'BITBRAINS_INPUT_LOCK.json');root=Path(lk['root']);split=read(root/'bitbrains/proposed_stable_hash_split_manifest.json');norm=read(root/'bitbrains/data/source_normalization.json')
    sources=sorted([m for m in split['machines'] if m['group']=='source'],key=lambda x:x['selection_rank_0based']);records=[]
    folder=RUN/'source_tasks';folder.mkdir(exist_ok=True)
    with zipfile.ZipFile(root/'bitbrains/raw/gwa_t_12_fastStorage.zip') as z:
        for cid,m in enumerate(sources):
            # The native archive column is mislabeled [ms]; the sealed reader
            # and identity manifest use the original numeric seconds.
            t,a=data.read_member(z,m);keep=(t>=int(m['source_first_seconds']))&(t<int(m['source_end_exclusive_seconds']));t=t[keep];a=a[keep]
            assert len(t)>=250
            for H in [1,4]:
                for K in [10,20]:
                    cut=96+H+K-1;sup=data.complete_origins(a[:cut],H);query=data.complete_origins(a[cut:],H)
                    assert len(sup)>=K and len(query)>0
                    xs,ys=data.windows(t[:cut],a[:cut],norm,H,sup[:K]);xq,yq=data.windows(t[cut:],a[cut:],norm,H,query)
                    p=folder/f's{cid}_h{H}_k{K}.npz';np.savez_compressed(p,Xs=xs,ys=ys,Xq=xq,yq=yq)
                    records.append(dict(ordinal=cid,VM=m['vm_id'],H=H,K=K,support_raw=[0,cut],query_raw=[cut,len(t)],query_windows=len(query),path=str(p),sha256=sha(p)))
            print('Source tasks',cid+1,'/20',flush=True)
    p=RUN/'SOURCE_TASKS_LOCK.json';write(p,dict(status='PASS',records=records,native_contiguous_support=True,raw_segments_disjoint=True,source_role='original Source20 first 24h; no target arrays',normalization_sha256=sha(root/'bitbrains/data/source_normalization.json')))
    write(RUN/'receipts/jobs'/f"{j['id']}.json",dict(job_id=j['id'],status='PASS',utc=utc(),outputs={str(p):sha(p)},new_cases=80))
if __name__=='__main__':main(read(sys.argv[1]))
