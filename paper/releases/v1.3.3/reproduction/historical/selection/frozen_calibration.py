"""Pure calibration policy, tested in Stage A; no final Cal data reader is invoked."""
import numpy as np

REQUIRED_IDENTITY=('protocol_sha256','feature_contract_sha256','candidate_checkpoint_map_sha256','reference_lock_sha256','selector_core_sha256','neighbor_config_sha256','seed','budget','risk_definition')

def calibrate_bound(rows,identity,expected_identity,*,stage,group):
    """Stage-8 caller must provide frozen identities; no data reader lives here."""
    if set(REQUIRED_IDENTITY)-set(identity):raise ValueError('Incomplete frozen calibration identity')
    if identity!=expected_identity:raise ValueError('Stale or mismatched calibration binding')
    if identity['budget']!='medium':raise ValueError('Only medium fits tau')
    if group=='calibration' and stage!=8:raise PermissionError('Formal calibration is Stage 8 only')
    if group not in ['calibration','dev_test_fixture']:raise PermissionError('Invalid calibration group')
    return dict(calibrate(rows),binding=identity,stage=stage,group=group,formal_calibration=group=='calibration')

def balanced(rows,key):
    vms=sorted(set(r['VM'] for r in rows))
    if not vms:raise ValueError('Empty population')
    means=[]
    for vm in vms:
        rr=[r for r in rows if r['VM']==vm]
        if len(rr)!=4 or {(r['H'],r['K']) for r in rr}!={(1,10),(1,20),(4,10),(4,20)}:raise ValueError('Incomplete VM/HK population')
        a=np.asarray([r[key] for r in sorted(rr,key=lambda r:(r['H'],r['K']))],dtype=np.float64)
        if not np.isfinite(a).all():raise ValueError('Nonfinite policy input')
        means.append(float(np.mean(a)))
    return float(np.mean(np.asarray(means,dtype=np.float64)))

def calibrate(rows,grid=(0,.05,.075,.10,.125,.15,.20)):
    curves=[];reference=None;population=None
    for tau in grid:
        rr=[r for r in rows if r['tau']==tau]
        keys={(r['VM'],r['H'],r['K']) for r in rr}
        if population is not None and keys!=population:raise ValueError('Tau populations differ')
        population=keys
        risk=balanced(rr,'E_selected');ref=balanced(rr,'E_reference')
        if reference is not None and ref!=reference:raise ValueError('Reference changed across tau')
        reference=ref
        annotated=[dict(r,harm=int(r['selected_token']!=r['reference_token'] and r['E_selected']>r['E_reference']),switch=int(r['selected_token']!=r['reference_token'])) for r in rr]
        curves.append(dict(tau=tau,risk=risk,harm=balanced(annotated,'harm'),switch=balanced(annotated,'switch')))
    ok=[r for r in curves if r['harm']<=.05]
    best=min(ok,key=lambda r:(r['risk'],-r['tau'])) if ok else None
    if best is None or best['risk']>=reference:return dict(policy='pure_reference',tau=None,reference_risk=reference,curves=curves)
    return dict(policy='selector',tau=best['tau'],risk=best['risk'],reference_risk=reference,curves=curves)
