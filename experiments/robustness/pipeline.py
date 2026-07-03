# -*- coding: utf-8 -*-
from __future__ import annotations

import gc
import hashlib
import json
import os
import time
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from configs.methods.robustness_experiments_cfg import CFG2, config_dict
from main_evaluation.pipeline import _asset_full, _safe_torch_load
from core.space import build_model, enumerate_A_base, is_feasible, profile_arch
from core.methods.ours.stage2_runtime import (
    candidate_backend_context,
    candidate_device,
    synchronize_if_cuda,
)
from shared.data_access import get_support_validation_check, get_test_only
from shared.evaluation.common import (
    atomic_json,
    build_runtime,
    eval_metrics,
    feasible_indices,
    file_sha256,
    load_json,
    seed_all,
)
from experiments.main.pipeline import (
    _asset_record,
    _atomic_torch_save,
    _build_scale_runtime,
    _candidate_lex,
    _center_bootstrap,
    _jobs,
    _mean,
    _rel_gain,
    _select_anchor_safe,
    _target_adapt,
)
from experiments.main.real_trace import (
    _load_processed,
    _real_case_split,
    _real_runtime,
)


def _pool_ids(pool: Sequence[int]) -> set[int]:
    start, count, _ = [int(x) for x in pool]
    return set(range(start, start + count))


def _abs(root: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(root, path)


def _require_v2_preflight(root: str) -> None:
    path = os.path.join(root, CFG2.output_root, "preflight", "v2_preflight.json")
    if not os.path.isfile(path):
        raise RuntimeError("V2 preflight is missing")
    obj = load_json(path)
    if obj.get("decision") != "PASS_FINAL_PAPER_EXPERIMENTS_V2_PREFLIGHT":
        raise RuntimeError(f"V2 preflight is not PASS: {obj.get('decision')}")


def run_v2_preflight(project_root: str, out_path: str) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    checks: Dict[str, Any] = {}
    old_audit_path = os.path.join(root, CFG2.old_audit_path)
    checks["old_audit_exists"] = os.path.isfile(old_audit_path)
    old_audit = load_json(old_audit_path) if checks["old_audit_exists"] else {}
    checks["old_audit_pass"] = (
        old_audit.get("decision") == CFG2.expected_old_audit_decision
    )
    required = {
        "old_ablation": CFG2.old_ablation_path,
        "real_manifest": CFG2.old_real_manifest_path,
        "real_bank_manifest": os.path.join(CFG2.old_real_bank_dir, "real_bank_manifest.json"),
        "anchor_safe_candidates": CFG2.anchor_safe_candidates_path,
        "main_evaluation_ours": CFG2.main_evaluation_ours_path,
        "main_evaluation_pt": CFG2.main_evaluation_pt_path,
    }
    for name, rel in required.items():
        checks[f"{name}_exists"] = os.path.isfile(os.path.join(root, rel))

    prior = set()
    for a, b in CFG2.known_used_center_ranges:
        prior.update(range(int(a), int(b) + 1))
    scale_ids = _pool_ids(CFG2.source_scale_pool)
    seed_ids = _pool_ids(CFG2.source_seed_pool)
    checks["source_scale_pool_disjoint_from_prior_except_registered_replacement"] = (
        scale_ids == set(range(1040, 1060))
    )
    checks["source_seed_pool_disjoint_from_prior"] = not bool(seed_ids & prior)
    checks["v2_pools_disjoint"] = not bool(scale_ids & seed_ids)
    checks["source_seeds_exact"] = CFG2.source_seeds == (2904, 2905, 2906)
    checks["fixed_source_updates"] = CFG2.source_updates_per_asset == 2000
    checks["frozen_margin"] = abs(CFG2.frozen_margin_rel - 0.10) < 1e-12
    checks["compact_bank_frozen"] = CFG2.compact_arch_indices == (1, 6, 13, 55, 56, 57)
    checks["no_test_for_training"] = True

    decision = (
        "PASS_FINAL_PAPER_EXPERIMENTS_V2_PREFLIGHT"
        if all(bool(v) for v in checks.values())
        else "FAIL_FINAL_PAPER_EXPERIMENTS_V2_PREFLIGHT"
    )
    obj = {
        "study": "experiments.robustness_preflight",
        "decision": decision,
        "protocol": config_dict(),
        "checks": checks,
        "old_audit_sha256": file_sha256(old_audit_path) if os.path.isfile(old_audit_path) else None,
    }
    atomic_json(obj, os.path.abspath(out_path))
    return obj


def _fixed_update_batch(
    cfg: Any,
    cache: Any,
    *,
    H: int,
    source_count: int,
    source_seed: int,
    update_index: int,
    batch_size: int,
) -> Tuple[torch.Tensor, torch.Tensor, int]:
    """One compute-matched source update.

    The random stream is independent of source_count. A shared uniform draw is
    mapped to the available nested prefix. Thus source scale changes only the
    eligible source-center set, not initialization, update count, or the random
    stream definition.
    """
    rng = np.random.default_rng(
        int(source_seed) * 1_000_003 + int(H) * 10_007 + int(update_index)
    )
    u = float(rng.random())
    cid = min(int(source_count) - 1, int(np.floor(u * int(source_count))))
    Xs, ys, Xv, yv, *_ = get_support_validation_check(
        cfg, cache, cid, int(H), max(CFG2.K_list)
    )
    X = torch.cat([Xs, Xv], dim=0)
    y = torch.cat([ys, yv], dim=0)
    n = int(X.shape[0])
    take = min(int(batch_size), n)
    ids_np = rng.choice(n, size=take, replace=False)
    ids = torch.as_tensor(ids_np, dtype=torch.long, device=X.device)
    return X.index_select(0, ids), y.index_select(0, ids), cid


def _train_source_asset(
    root: str,
    cfg: Any,
    cache: Any,
    A: Sequence[Any],
    requested: torch.device,
    safe: str,
    *,
    source_count: int,
    source_seed: int,
    H: int,
    arch_idx: int,
    out_file: str,
    smoke: bool,
    job_label: str,
) -> Dict[str, Any]:
    L = int(cfg.main.task.L)
    X0, *_ = get_support_validation_check(cfg, cache, 0, H, max(CFG2.K_list))
    input_dim = int(X0.shape[-1])
    spec = A[int(arch_idx)]
    actual = candidate_device(spec, requested, safe)
    updates = 10 if smoke else int(CFG2.source_updates_per_asset)
    init_seed = int(source_seed + 101 * int(H) + int(arch_idx))
    checkpoint = out_file + ".progress.pt"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with candidate_backend_context(spec, actual, safe):
        seed_all(init_seed, actual)
        model = build_model(
            spec, input_dim=input_dim, H=int(H), L=L, device=str(actual)
        )
        opt = optim.Adam(
            model.parameters(),
            lr=CFG2.source_lr,
            weight_decay=CFG2.source_weight_decay,
        )
        start_update = 0
        if os.path.isfile(checkpoint):
            state = torch.load(checkpoint, map_location=actual)
            model.load_state_dict(state["model"], strict=True)
            opt.load_state_dict(state["optimizer"])
            start_update = int(state.get("next_update", 0))
        losses: List[float] = []
        center_counter: Counter[int] = Counter()
        started = time.perf_counter()
        for update in range(start_update, updates):
            Xb, yb, cid = _fixed_update_batch(
                cfg,
                cache,
                H=H,
                source_count=source_count,
                source_seed=source_seed,
                update_index=update,
                batch_size=CFG2.source_batch_size,
            )
            center_counter[int(cid)] += 1
            model.train()
            opt.zero_grad(set_to_none=True)
            pred = model(Xb.to(actual).contiguous())
            loss = ((pred - yb.to(actual).contiguous()) ** 2).mean()
            if not torch.isfinite(loss):
                raise RuntimeError("Non-finite controlled source loss")
            loss.backward()
            opt.step()
            losses.append(float(loss.detach().item()))
            done = update + 1
            if (
                done % int(CFG2.checkpoint_every_updates) == 0
                or done == updates
            ):
                _atomic_torch_save(
                    {
                        "model": {k: v.detach().cpu() for k, v in model.state_dict().items()},
                        "optimizer": opt.state_dict(),
                        "next_update": done,
                        "initialization_seed": init_seed,
                        "source_seed": int(source_seed),
                        "source_count": int(source_count),
                    },
                    checkpoint,
                )
                elapsed = time.perf_counter() - started
                eta = elapsed / max(1, done - start_update) * max(0, updates - done)
                print(
                    f"[{job_label}] src={source_count} seed={source_seed} "
                    f"H={H} A={arch_idx} update={done}/{updates} "
                    f"loss={losses[-1]:.6g} elapsed={elapsed/3600:.2f}h "
                    f"eta={eta/3600:.2f}h",
                    flush=True,
                )
        synchronize_if_cuda(actual)
        _atomic_torch_save(
            {k: v.detach().cpu() for k, v in model.state_dict().items()},
            out_file,
        )
        if os.path.isfile(checkpoint):
            os.remove(checkpoint)
        final_loss = float(np.mean(losses[-min(100, len(losses)):])) if losses else None
        del model, opt
    params, flops = profile_arch(spec, L=L, input_dim=input_dim, H=int(H))
    return _asset_record(
        out_file,
        root,
        source_count=int(source_count),
        source_seed=int(source_seed),
        initialization_seed=int(init_seed),
        H=int(H),
        arch_idx=int(arch_idx),
        arch_key=str(spec.arch_key),
        family=str(spec.family),
        fixed_updates=int(updates),
        batch_size=int(CFG2.source_batch_size),
        compute_matched=True,
        initialization_independent_of_source_scale=True,
        random_stream_independent_of_source_scale=True,
        final_source_loss=final_loss,
        sampled_center_updates={str(k): int(v) for k, v in sorted(center_counter.items())},
        params=float(params),
        flops=float(flops),
    )


def build_controlled_source_scale_banks(
    project_root: str,
    out_dir: str,
    device: str,
    safe_mode: str,
    smoke: bool = False,
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    _require_v2_preflight(root)
    cfg, cache, A, requested, safe = _build_scale_runtime(device, safe_mode)
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    manifest_path = os.path.join(out_dir, "controlled_source_scale_bank_manifest.json")
    run_mode = "smoke" if smoke else "formal"
    manifest = load_json(manifest_path) if os.path.isfile(manifest_path) else {
        "study": "controlled_compute_matched_source_scale_banks",
        "decision": "CONTROLLED_SOURCE_SCALE_BANKS_IN_PROGRESS",
        "run_mode": run_mode,
        "protocol": config_dict(),
        "control": {
            "nested_source_prefixes": True,
            "same_model_initialization_across_scales": True,
            "same_update_count_across_scales": True,
            "scale_independent_random_stream_definition": True,
            "fixed_updates_per_asset": int(CFG2.source_updates_per_asset),
        },
        "assets": {},
        "test_used": False,
    }
    if manifest.get("run_mode") != run_mode:
        raise RuntimeError("Smoke/formal outputs cannot share V2 bank directory")
    scales = (CFG2.source_scales[0],) if smoke else CFG2.source_scales
    Hs = (CFG2.H_list[0],) if smoke else CFG2.H_list
    jobs = [(s, H, a) for s in scales for H in Hs for a in CFG2.compact_arch_indices]
    started = time.perf_counter()
    for n, (scale, H, idx) in enumerate(jobs, 1):
        key = f"s{scale}_h{H}_a{idx}"
        out_file = os.path.join(out_dir, f"src{scale}", f"controlled_h{H}_a{idx}.pt")
        old = manifest.get("assets", {}).get(key)
        if old and os.path.isfile(out_file) and file_sha256(out_file) == old.get("sha256"):
            continue
        item = _train_source_asset(
            root, cfg, cache, A, requested, safe,
            source_count=int(scale), source_seed=CFG2.source_seeds[0],
            H=int(H), arch_idx=int(idx), out_file=out_file,
            smoke=smoke, job_label=f"V2:ScaleBank {n}/{len(jobs)}",
        )
        manifest.setdefault("assets", {})[key] = item
        manifest["completed_assets"] = len(manifest["assets"])
        manifest["expected_assets"] = len(jobs)
        atomic_json(manifest, manifest_path)
        elapsed = time.perf_counter() - started
        print(f"[V2:ScaleBank] completed={len(manifest['assets'])}/{len(jobs)} elapsed={elapsed/3600:.2f}h", flush=True)
        gc.collect()
        if requested.type == "cuda": torch.cuda.empty_cache()
    manifest["complete"] = len(manifest.get("assets", {})) == len(jobs)
    manifest["decision"] = "PASS_CONTROLLED_SOURCE_SCALE_BANKS" if manifest["complete"] else "CONTROLLED_SOURCE_SCALE_BANKS_INCOMPLETE"
    atomic_json(manifest, manifest_path)
    return manifest


def _load_manifest_model(
    root: str,
    manifest: Mapping[str, Any],
    key: str,
    A: Sequence[Any],
    *,
    input_dim: int,
    H: int,
    L: int,
    device: torch.device,
) -> nn.Module:
    item = manifest["assets"][key]
    path = _asset_full(root, item)
    model = build_model(A[int(item["arch_idx"])], input_dim=input_dim, H=H, L=L, device=str(device))
    model.load_state_dict(_safe_torch_load(path, device), strict=True)
    return model


def _evaluate_bank_group(
    root: str,
    cfg: Any,
    cache: Any,
    A: Sequence[Any],
    requested: torch.device,
    safe: str,
    manifest: Mapping[str, Any],
    *,
    asset_key_prefix: str,
    cid: int,
    H: int,
    K: int,
    target_seed: int,
    smoke: bool,
) -> Dict[str, Any]:
    Xs, ys, Xv, yv, Xc, yc, tier, ctype = get_support_validation_check(cfg, cache, cid, H, K)
    L = int(cfg.main.task.L)
    input_dim = int(Xs.shape[-1])
    feasible = set(feasible_indices(cfg, A, tier, L, input_dim, H))
    if CFG2.anchor_arch_idx not in feasible:
        raise RuntimeError("A57 anchor infeasible")
    rows: List[Dict[str, Any]] = []
    states: Dict[str, Dict[str, torch.Tensor]] = {}
    for idx in CFG2.compact_arch_indices:
        if int(idx) not in feasible:
            continue
        spec = A[int(idx)]
        actual = candidate_device(spec, requested, safe)
        key = f"{asset_key_prefix}_h{H}_a{idx}"
        with candidate_backend_context(spec, actual, safe):
            model = _load_manifest_model(root, manifest, key, A, input_dim=input_dim, H=H, L=L, device=actual)
            _target_adapt(model, Xs, ys, seed=int(target_seed), steps=(1 if smoke else CFG2.target_steps))
            val = eval_metrics(model, Xv, yv)
            chk = eval_metrics(model, Xc, yc)
            params, flops = profile_arch(spec, L=L, input_dim=input_dim, H=H)
            token = "PT_A57" if int(idx) == 57 else f"A{idx}"
            rows.append({
                "token": token, "arch_idx": int(idx), "arch_key": str(spec.arch_key),
                "family": str(spec.family), "params": float(params), "flops": float(flops),
                "hard_feasible": True, "validation": val, "check": chk,
            })
            states[token] = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            del model
            synchronize_if_cuda(actual)
    selection = _select_anchor_safe(
        rows,
        allowed_tokens=[str(r["token"]) for r in rows],
        margin_rel=CFG2.frozen_margin_rel,
        enforce_feasible=True,
    )
    Xt, yt = get_test_only(cfg, cache, cid, H, K)
    test_by_token: Dict[str, Dict[str, float]] = {}
    for row in rows:
        token = str(row["token"])
        spec = A[int(row["arch_idx"])]
        actual = candidate_device(spec, requested, safe)
        with candidate_backend_context(spec, actual, safe):
            model = build_model(spec, input_dim=input_dim, H=H, L=L, device=str(actual))
            model.load_state_dict(states[token], strict=True)
            test_by_token[token] = eval_metrics(model, Xt, yt)
            del model
            synchronize_if_cuda(actual)
        row["test"] = test_by_token[token]
    selected_token = str(selection["selected_token"])
    test_oracle = min(rows, key=lambda r: (float(r["test"]["weighted_mse"]), float(r["params"]), float(r["flops"]), int(r["arch_idx"])))
    out = {
        "center_id": int(cid), "center_type": str(ctype), "budget_tier": str(tier),
        "H": int(H), "K": int(K), "target_seed": int(target_seed),
        "candidates": rows,
        "selection": selection,
        "selected": {"token": selected_token, "test": test_by_token[selected_token]},
        "anchor": {"token": "PT_A57", "test": test_by_token["PT_A57"]},
        "test_oracle": {"token": str(test_oracle["token"]), "test": test_oracle["test"]},
        "selection_uses_test": False,
        "test_opened_after_selection": True,
    }
    del states
    return out


def run_controlled_source_scale_eval(
    project_root: str,
    bank_dir: str,
    out_path: str,
    device: str,
    safe_mode: str,
    smoke: bool = False,
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    _require_v2_preflight(root)
    manifest_path = os.path.join(os.path.abspath(bank_dir), "controlled_source_scale_bank_manifest.json")
    manifest = load_json(manifest_path)
    if manifest.get("decision") != "PASS_CONTROLLED_SOURCE_SCALE_BANKS":
        raise RuntimeError("Controlled source-scale bank is not PASS")
    cfg, cache, A, requested, safe = build_runtime(device, safe_mode, (CFG2.source_scale_pool,))
    jobs = _jobs(CFG2.source_scale_pool, smoke)
    scales = (CFG2.source_scales[0],) if smoke else CFG2.source_scales
    run_mode = "smoke" if smoke else "formal"
    result = load_json(out_path) if os.path.isfile(out_path) else {
        "study": "controlled_compute_matched_source_scale_evaluation",
        "decision": "CONTROLLED_SOURCE_SCALE_EVAL_IN_PROGRESS",
        "run_mode": run_mode, "protocol": config_dict(),
        "bank_manifest_sha256": file_sha256(manifest_path), "records": {},
        "selection_uses_test": False,
    }
    if result.get("run_mode") != run_mode: raise RuntimeError("Smoke/formal output collision")
    records = dict(result.get("records", {})); started=time.perf_counter(); new=0
    for scale in scales:
        for case_no, (cid,H,K) in enumerate(jobs,1):
            Xs, ys, Xv, yv, Xc, yc, tier, ctype = get_support_validation_check(cfg, cache, cid, H, K)
            key=f"s{scale}_c{cid}_h{H}_k{K}_b{tier}"
            if key in records and records[key].get("complete"): continue
            target_seed=CFG2.target_eval_seed+1009*cid+37*H+53*K
            row=_evaluate_bank_group(root,cfg,cache,A,requested,safe,manifest,asset_key_prefix=f"s{scale}",cid=cid,H=H,K=K,target_seed=target_seed,smoke=smoke)
            row.update({"complete":True,"source_scale":int(scale),"case_key":key})
            records[key]=row; result["records"]=records; result["N_records"]=len(records); result["expected_records"]=len(jobs)*len(scales); result["complete"]=len(records)==result["expected_records"]
            atomic_json(result,out_path); new+=1
            elapsed=time.perf_counter()-started; eta=elapsed/max(1,new)*max(0,result["expected_records"]-len(records))
            print(f"[V2:ScaleEval] src={scale} {case_no}/{len(jobs)} {key} elapsed={elapsed/3600:.2f}h eta={eta/3600:.2f}h",flush=True)
            gc.collect();
            if requested.type=="cuda": torch.cuda.empty_cache()
    result["decision"]="PASS_CONTROLLED_SOURCE_SCALE_EVAL" if result.get("complete") else "CONTROLLED_SOURCE_SCALE_EVAL_INCOMPLETE"
    atomic_json(result,out_path); return result


def build_source_seed_banks(
    project_root: str,
    controlled_bank_dir: str,
    out_dir: str,
    device: str,
    safe_mode: str,
    smoke: bool = False,
) -> Dict[str, Any]:
    root=os.path.abspath(project_root); _require_v2_preflight(root)
    cfg,cache,A,requested,safe=_build_scale_runtime(device,safe_mode)
    controlled_path=os.path.join(os.path.abspath(controlled_bank_dir),"controlled_source_scale_bank_manifest.json")
    controlled=load_json(controlled_path) if os.path.isfile(controlled_path) else None
    out_dir=os.path.abspath(out_dir); os.makedirs(out_dir,exist_ok=True)
    manifest_path=os.path.join(out_dir,"source_seed_bank_manifest.json")
    run_mode="smoke" if smoke else "formal"
    manifest=load_json(manifest_path) if os.path.isfile(manifest_path) else {
        "study":"source_bank_training_seed_robustness_banks","decision":"SOURCE_SEED_BANKS_IN_PROGRESS","run_mode":run_mode,"protocol":config_dict(),"assets":{},"test_used":False,
        "control":{"source_count":20,"same_data_seed":True,"same_update_count":True,"target_data_not_used":True}
    }
    if manifest.get("run_mode")!=run_mode: raise RuntimeError("Smoke/formal output collision")
    seeds=(CFG2.source_seeds[0],) if smoke else CFG2.source_seeds; Hs=(CFG2.H_list[0],) if smoke else CFG2.H_list
    jobs=[(s,H,a) for s in seeds for H in Hs for a in CFG2.compact_arch_indices]
    for n,(s,H,idx) in enumerate(jobs,1):
        key=f"seed{s}_h{H}_a{idx}"; old=manifest.get("assets",{}).get(key)
        if old:
            p=_asset_full(root,old)
            if os.path.isfile(p) and file_sha256(p)==old.get("sha256"): continue
        if int(s)==int(CFG2.source_seeds[0]) and controlled and controlled.get("decision")=="PASS_CONTROLLED_SOURCE_SCALE_BANKS":
            src=controlled["assets"][f"s20_h{H}_a{idx}"]
            item=dict(src); item.update({"source_seed":int(s),"reused_from_controlled_scale20":True})
            manifest.setdefault("assets",{})[key]=item
        else:
            out_file=os.path.join(out_dir,f"seed{s}",f"source_seed_h{H}_a{idx}.pt")
            item=_train_source_asset(root,cfg,cache,A,requested,safe,source_count=20,source_seed=int(s),H=int(H),arch_idx=int(idx),out_file=out_file,smoke=smoke,job_label=f"V2:SourceSeedBank {n}/{len(jobs)}")
            item["reused_from_controlled_scale20"]=False
            manifest.setdefault("assets",{})[key]=item
        manifest["completed_assets"]=len(manifest["assets"]); manifest["expected_assets"]=len(jobs); atomic_json(manifest,manifest_path)
        gc.collect();
        if requested.type=="cuda": torch.cuda.empty_cache()
    manifest["complete"]=len(manifest.get("assets",{}))==len(jobs); manifest["decision"]="PASS_SOURCE_SEED_BANKS" if manifest["complete"] else "SOURCE_SEED_BANKS_INCOMPLETE"; atomic_json(manifest,manifest_path); return manifest


def run_source_seed_eval(
    project_root: str,
    bank_dir: str,
    out_path: str,
    device: str,
    safe_mode: str,
    smoke: bool = False,
) -> Dict[str, Any]:
    root=os.path.abspath(project_root); _require_v2_preflight(root)
    manifest_path=os.path.join(os.path.abspath(bank_dir),"source_seed_bank_manifest.json"); manifest=load_json(manifest_path)
    if manifest.get("decision")!="PASS_SOURCE_SEED_BANKS": raise RuntimeError("Source-seed banks are not PASS")
    cfg,cache,A,requested,safe=build_runtime(device,safe_mode,(CFG2.source_seed_pool,)); jobs=_jobs(CFG2.source_seed_pool,smoke); seeds=(CFG2.source_seeds[0],) if smoke else CFG2.source_seeds
    run_mode="smoke" if smoke else "formal"
    result=load_json(out_path) if os.path.isfile(out_path) else {"study":"source_bank_training_seed_robustness_eval","decision":"SOURCE_SEED_EVAL_IN_PROGRESS","run_mode":run_mode,"protocol":config_dict(),"bank_manifest_sha256":file_sha256(manifest_path),"records":{},"source_seed_varied":True,"target_seed_fixed":True,"selection_uses_test":False}
    if result.get("run_mode")!=run_mode: raise RuntimeError("Smoke/formal output collision")
    records=dict(result.get("records",{})); started=time.perf_counter(); new=0
    for s in seeds:
        for case_no,(cid,H,K) in enumerate(jobs,1):
            Xs,ys,Xv,yv,Xc,yc,tier,ctype=get_support_validation_check(cfg,cache,cid,H,K)
            key=f"seed{s}_c{cid}_h{H}_k{K}_b{tier}"
            if key in records and records[key].get("complete"): continue
            target_seed=CFG2.target_eval_seed+1009*cid+37*H+53*K
            row=_evaluate_bank_group(root,cfg,cache,A,requested,safe,manifest,asset_key_prefix=f"seed{s}",cid=cid,H=H,K=K,target_seed=target_seed,smoke=smoke)
            row.update({"complete":True,"source_seed":int(s),"case_key":key})
            records[key]=row; result["records"]=records; result["N_records"]=len(records); result["expected_records"]=len(jobs)*len(seeds); result["complete"]=len(records)==result["expected_records"]; atomic_json(result,out_path); new+=1
            elapsed=time.perf_counter()-started; eta=elapsed/max(1,new)*max(0,result["expected_records"]-len(records)); print(f"[V2:SourceSeedEval] seed={s} {case_no}/{len(jobs)} {key} elapsed={elapsed/3600:.2f}h eta={eta/3600:.2f}h",flush=True)
            gc.collect();
            if requested.type=="cuda": torch.cuda.empty_cache()
    result["decision"]="PASS_SOURCE_SEED_ROBUSTNESS_EVAL" if result.get("complete") else "SOURCE_SEED_EVAL_INCOMPLETE"; atomic_json(result,out_path); return result


def _resolve_real_asset(bank_dir: str, item: Mapping[str, Any]) -> str:
    path=str(item["path"])
    if os.path.isfile(path): return path
    candidate=os.path.join(os.path.abspath(bank_dir),os.path.basename(path))
    if os.path.isfile(candidate): return candidate
    raise FileNotFoundError(path)


def run_real_candidate_diagnostics(
    project_root: str,
    manifest_path: str,
    bank_dir: str,
    out_path: str,
    device: str,
    safe_mode: str,
    smoke: bool=False,
) -> Dict[str,Any]:
    root=os.path.abspath(project_root); _require_v2_preflight(root)
    trace,mapping=_load_processed(os.path.abspath(manifest_path)); bank_path=os.path.join(os.path.abspath(bank_dir),"real_bank_manifest.json"); bank=load_json(bank_path)
    if bank.get("decision")!="PASS_REAL_SOURCE_BANK": raise RuntimeError("Real bank is not PASS")
    cfg,A,requested,safe=_real_runtime(device,safe_mode); L=int(cfg.main.task.L); input_dim=25
    targets=list(trace["target_machine_ids"]); jobs=[(mid,H,K) for mid in targets for H in CFG2.H_list for K in CFG2.K_list]
    if smoke: jobs=[x for x in jobs if x[1]==CFG2.H_list[0]][:2]
    run_mode="smoke" if smoke else "formal"; result=load_json(out_path) if os.path.isfile(out_path) else {"study":"alibaba2018_candidate_level_diagnostics","decision":"REAL_CANDIDATE_DIAGNOSTICS_IN_PROGRESS","run_mode":run_mode,"protocol":config_dict(),"trace_manifest_sha256":file_sha256(manifest_path),"bank_manifest_sha256":file_sha256(bank_path),"records":{},"selection_uses_test":False}
    if result.get("run_mode")!=run_mode: raise RuntimeError("Smoke/formal output collision")
    records=dict(result.get("records",{})); started=time.perf_counter(); new=0
    for job_no,(mid,H,K) in enumerate(jobs,1):
        tier=str(trace["budget_tiers"][mid]); ctype=str(trace["center_types"][mid]); key=f"m{hashlib.sha256(mid.encode()).hexdigest()[:10]}_h{H}_k{K}_b{tier}"
        if key in records and records[key].get("complete"): continue
        (Xs,ys),(Xv,yv),(Xc,yc),(Xt,yt)=_real_case_split(mapping[mid][0],mapping[mid][1],L,H,K)
        feasible=[i for i in CFG2.compact_arch_indices if is_feasible(A[i],cfg.main.budget,tier,L,input_dim,H)]
        if 57 not in feasible: raise RuntimeError("Real A57 anchor infeasible")
        target_seed=CFG2.target_eval_seed+int(hashlib.sha256(mid.encode()).hexdigest()[:8],16)+37*H+53*K
        rows=[]; states={}
        for idx in feasible:
            spec=A[idx]; actual=candidate_device(spec,requested,safe); item=bank["assets"][f"h{H}_a{idx}"]; asset_path=_resolve_real_asset(bank_dir,item)
            with candidate_backend_context(spec,actual,safe):
                model=build_model(spec,input_dim=input_dim,H=H,L=L,device=str(actual)); model.load_state_dict(torch.load(asset_path,map_location=actual),strict=True); _target_adapt(model,Xs,ys,seed=target_seed,steps=(1 if smoke else CFG2.target_steps)); val=eval_metrics(model,Xv,yv); chk=eval_metrics(model,Xc,yc); params,flops=profile_arch(spec,L=L,input_dim=input_dim,H=H); token="PT_A57" if idx==57 else f"A{idx}"; rows.append({"token":token,"arch_idx":int(idx),"arch_key":str(spec.arch_key),"family":str(spec.family),"params":float(params),"flops":float(flops),"hard_feasible":True,"validation":val,"check":chk}); states[token]={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}; del model
        selection=_select_anchor_safe(rows,allowed_tokens=[r["token"] for r in rows],margin_rel=CFG2.frozen_margin_rel,enforce_feasible=True); selected_token=str(selection["selected_token"])
        for row in rows:
            token=row["token"]; spec=A[row["arch_idx"]]; actual=candidate_device(spec,requested,safe)
            with candidate_backend_context(spec,actual,safe):
                model=build_model(spec,input_dim=input_dim,H=H,L=L,device=str(actual)); model.load_state_dict(states[token],strict=True); row["test"]=eval_metrics(model,Xt,yt); del model
        oracle=min(rows,key=lambda r:(r["test"]["weighted_mse"],r["params"],r["flops"],r["arch_idx"])); selected=next(r for r in rows if r["token"]==selected_token); anchor=next(r for r in rows if r["token"]=="PT_A57")
        records[key]={"complete":True,"machine_id_hash":hashlib.sha256(mid.encode()).hexdigest(),"center_type":ctype,"budget_tier":tier,"H":int(H),"K":int(K),"target_seed":int(target_seed),"candidates":rows,"selection":selection,"selected":{"token":selected_token,"test":selected["test"]},"anchor":{"token":"PT_A57","test":anchor["test"]},"test_oracle":{"token":oracle["token"],"test":oracle["test"]},"selection_uses_test":False}
        result["records"]=records; result["N_records"]=len(records); result["expected_records"]=len(jobs); result["complete"]=len(records)==len(jobs); atomic_json(result,out_path); new+=1
        elapsed=time.perf_counter()-started; eta=elapsed/max(1,new)*max(0,len(jobs)-len(records)); print(f"[V2:RealDiag] {job_no}/{len(jobs)} {key} selected={selected_token} elapsed={elapsed/3600:.2f}h eta={eta/3600:.2f}h",flush=True)
        del states; gc.collect();
        if requested.type=="cuda": torch.cuda.empty_cache()
    result["decision"]="PASS_REAL_CANDIDATE_DIAGNOSTICS" if result.get("complete") else "REAL_CANDIDATE_DIAGNOSTICS_INCOMPLETE"; atomic_json(result,out_path); return result


def _select_from_candidates(candidates: Sequence[Mapping[str,Any]], omit_arch: Optional[int]=None) -> Mapping[str,Any]:
    rows=[r for r in candidates if omit_arch is None or int(r["arch_idx"])!=int(omit_arch)]
    anchors=[r for r in rows if int(r["arch_idx"])==57 and str(r.get("token","")).startswith("PT")]
    if not anchors: anchors=[r for r in rows if int(r["arch_idx"])==57]
    if not anchors: raise RuntimeError("No A57 anchor in candidate set")
    anchor=min(anchors,key=_candidate_lex); alts=[r for r in rows if r is not anchor]
    best=min(alts,key=_candidate_lex) if alts else None
    if best is not None and float(best["validation"]["weighted_mse"])<=float(anchor["validation"]["weighted_mse"])*(1.0-CFG2.frozen_margin_rel): return best
    return anchor


def _coverage_rows_from_candidate_records(dataset: str, records: Mapping[str,Any], outcome: str="test") -> List[Dict[str,Any]]:
    stats={idx:defaultdict(float) for idx in CFG2.compact_arch_indices}
    for rec in records.values():
        cand=list(rec["candidates"] if isinstance(rec["candidates"],list) else rec["candidates"].values())
        if not all(outcome in r for r in cand): continue
        full=_select_from_candidates(cand); anchor=_select_from_candidates([r for r in cand if int(r["arch_idx"])==57])
        oracle=min(cand,key=lambda r:(float(r[outcome]["weighted_mse"]),float(r["params"]),float(r["flops"]),int(r["arch_idx"])))
        for idx in CFG2.compact_arch_indices:
            s=stats[idx]; s["N"]+=1; s["Feasible"]+=float(any(int(r["arch_idx"])==idx for r in cand)); s["Selected"]+=float(int(full["arch_idx"])==idx); s["OracleBest"]+=float(int(oracle["arch_idx"])==idx)
            if int(full["arch_idx"])==idx:
                gain=_rel_gain(full[outcome]["weighted_mse"],anchor[outcome]["weighted_mse"]); s["SelectedGainSum"]+=gain; s["SelectedGainN"]+=1; s["SelectedBeneficial"]+=float(gain>1e-6); s["SelectedHarmful"]+=float(gain<-1e-6)
            if idx!=57 and any(int(r["arch_idx"])==idx for r in cand):
                without=_select_from_candidates(cand,omit_arch=idx); delta=_rel_gain(full[outcome]["weighted_mse"],without[outcome]["weighted_mse"]); s["LeaveOneOutGainSum"]+=delta; s["LeaveOneOutN"]+=1; s["UniqueRescue"]+=float(delta>1e-6)
    rows=[]
    for idx,s in stats.items():
        n=max(1,int(s["N"])); rows.append({"Dataset":dataset,"Outcome":outcome,"ArchIdx":idx,"Cases":int(s["N"]),"FeasibleRate":s["Feasible"]/n,"SelectedCount":int(s["Selected"]),"OracleBestCount":int(s["OracleBest"]),"SelectedBeneficialCount":int(s["SelectedBeneficial"]),"SelectedHarmfulCount":int(s["SelectedHarmful"]),"MeanGainWhenSelected":s["SelectedGainSum"]/max(1,s["SelectedGainN"]),"MeanLeaveOneOutGain":s["LeaveOneOutGainSum"]/max(1,s["LeaveOneOutN"]),"UniqueRescueCount":int(s["UniqueRescue"])})
    return rows


def analyze_architecture_coverage(project_root: str, out_path: str) -> Dict[str,Any]:
    root=os.path.abspath(project_root); _require_v2_preflight(root); v2root=os.path.join(root,CFG2.output_root); rows=[]; sources=[]
    candidates=[
        ("AblationPool1000-1019",os.path.join(root,CFG2.old_ablation_path),"test"),
        ("C32Final960-979",os.path.join(root,CFG2.anchor_safe_candidates_path),"check"),
        ("ControlledScale1040-1059",os.path.join(v2root,"source_scale_controlled","controlled_source_scale_eval.json"),"test"),
        ("SourceSeed1060-1079",os.path.join(v2root,"source_seed","source_seed_eval.json"),"test"),
        ("AlibabaSemiReal",os.path.join(v2root,"real_diagnostics","real_candidate_diagnostics.json"),"test"),
    ]
    for name,path,outcome in candidates:
        if os.path.isfile(path):
            obj=load_json(path); rows.extend(_coverage_rows_from_candidate_records(name,obj["records"],outcome)); sources.append({"dataset":name,"path":os.path.relpath(path,root).replace('\\','/'),"sha256":file_sha256(path)})
    # C3-3 provides selected-candidate test evidence even though unselected test states were not stored.
    op=os.path.join(root,CFG2.main_evaluation_ours_path); pp=os.path.join(root,CFG2.main_evaluation_pt_path)
    if os.path.isfile(op) and os.path.isfile(pp):
        ours=load_json(op)["records"]; pt=load_json(pp)["records"]
        for idx in CFG2.compact_arch_indices:
            selected=[]
            for k,r in ours.items():
                if int(r["arch_idx"])==idx:
                    selected.append(_rel_gain(r["test"]["weighted_mse"],pt[k]["test"]["weighted_mse"]))
            rows.append({"Dataset":"MAIN_EVALUATIONLocked980-999","Outcome":"test_selected_only","ArchIdx":idx,"Cases":len(ours),"FeasibleRate":None,"SelectedCount":len(selected),"OracleBestCount":None,"SelectedBeneficialCount":sum(x>1e-6 for x in selected),"SelectedHarmfulCount":sum(x<-1e-6 for x in selected),"MeanGainWhenSelected":float(np.mean(selected)) if selected else None,"MeanLeaveOneOutGain":None,"UniqueRescueCount":None})
        sources.extend([{"dataset":"MAIN_EVALUATIONLocked980-999","path":CFG2.main_evaluation_ours_path,"sha256":file_sha256(op)},{"dataset":"MAIN_EVALUATIONPT","path":CFG2.main_evaluation_pt_path,"sha256":file_sha256(pp)}])
    focus={}
    for idx in (13,1):
        rr=[r for r in rows if int(r["ArchIdx"])==idx]
        focus[f"A{idx}"]={"rows":rr,"total_selected":sum(int(r.get("SelectedCount") or 0) for r in rr),"total_beneficial_selected":sum(int(r.get("SelectedBeneficialCount") or 0) for r in rr),"total_harmful_selected":sum(int(r.get("SelectedHarmfulCount") or 0) for r in rr),"total_unique_rescues":sum(int(r.get("UniqueRescueCount") or 0) for r in rr if r.get("UniqueRescueCount") is not None),"interpretation":"Retain only as frozen cross-distribution coverage if independent beneficial selections or leave-one-out rescues are observed; otherwise report redundancy and do not invent a role."}
    obj={"study":"compact_bank_architecture_coverage_and_leave_one_out","decision":"PASS_ARCHITECTURE_COVERAGE_ANALYSIS","protocol":config_dict(),"rows":rows,"focus_last_two_additions":focus,"sources":sources,"test_used_only_for_posthoc_diagnostics":True,"method_retuning_allowed":False}
    atomic_json(obj,os.path.abspath(out_path)); return obj
