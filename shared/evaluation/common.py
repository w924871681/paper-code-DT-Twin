# -*- coding: utf-8 -*-
from __future__ import annotations
import copy, gc, hashlib, json, math, os, pickle, random, time
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import numpy as np
import torch

from configs.methods.shared_evaluation_cfg import CFG, config_dict
from configs.methods.target_profile_cfg import CFG as PROFILE_CFG
from core.config import load_and_merge
from core.data.v2_pools import build_v2_development_cache
from core.methods.ours.adapt import adapt_steps
from core.methods.ours.c2_adapt import adapt_prior_preserving
from core.methods.ours.c23_mode_selector import choose_mode, extract_pre_adaptation_features, predict_std_probability, safe_accept_selected_mode, vectorize_feature_dict
from core.methods.ours.paper_engine import _load_prior_model
from core.methods.ours.paper_modules import build_budget_features, build_task_features
from core.methods.ours.prior_response_profile import build_prior_response_profile, select_anchor_indices
from core.methods.ours.stage2_runtime import candidate_backend_context, candidate_device, configure_stage2_runtime, synchronize_if_cuda
from core.methods.ours.stage2_v4_c23 import admit
from core.methods.ours.weight_bank import load_weight_bank
from core.space import build_model, enumerate_A_base, is_feasible, profile_arch
from core.utils.metrics import eval_mae, eval_paper_sequence_consistency, eval_weighted_mse, eval_worst10
from shared.data_access import get_support_validation_check, get_test_only


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(obj: Any, path: str) -> None:
    path = os.path.abspath(path); os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    tmp = "%s.%s.%s.tmp" % (path, os.getpid(), time.time_ns())
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(payload); f.flush(); os.fsync(f.fileno())
    last = None
    for attempt in range(60):
        try:
            if os.path.exists(path):
                try: os.chmod(path, 0o666)
                except OSError: pass
            os.replace(tmp, path); return
        except (PermissionError, OSError) as exc:
            winerror = getattr(exc, "winerror", None)
            if isinstance(exc, OSError) and not isinstance(exc, PermissionError) and winerror not in (5, 32, 33): raise
            last = exc; time.sleep(min(0.05 * (attempt + 1), 1.0))
    for attempt in range(30):
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(payload); f.flush(); os.fsync(f.fileno())
            try: os.remove(tmp)
            except OSError: pass
            print("[WARN] atomic replace blocked; used in-place fallback: %s" % path, flush=True); return
        except PermissionError as exc:
            last = exc; time.sleep(min(0.1 * (attempt + 1), 1.0))
    raise RuntimeError("Unable to checkpoint JSON: %s" % path) from last


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f: return json.load(f)


def seed_all(seed: int, device: Optional[torch.device] = None) -> None:
    random.seed(int(seed)); np.random.seed(int(seed) % (2**32 - 1)); torch.manual_seed(int(seed))
    if device is not None and device.type == "cuda": torch.cuda.manual_seed_all(int(seed))


def load_frozen_assets(project_root: str) -> Dict[str, Any]:
    paths = {
        "bank": os.path.join(project_root, CFG.c1_bank_path),
        "c23_identity": os.path.join(project_root, CFG.c23_identity_path),
        "c23_stage1d": os.path.join(project_root, CFG.c23_stage1d_path),
        "c23_q2": os.path.join(project_root, CFG.c23_q2_path),
        "stage2_profiles": os.path.join(project_root, CFG.stage2_dev_profiles_path),
        "stage2_selection": os.path.join(project_root, CFG.stage2_selection_path),
        "source_pi50": os.path.join(project_root, CFG.source_pi50_path),
    }
    for name, path in paths.items():
        if not os.path.isfile(path): raise FileNotFoundError("Missing frozen asset %s: %s" % (name, path))
    if file_sha256(paths["bank"]).lower() != CFG.c1_bank_sha256.lower(): raise RuntimeError("C1 bank hash mismatch")
    identity = load_json(paths["c23_identity"]); s1d = load_json(paths["c23_stage1d"]); q2 = load_json(paths["c23_q2"])
    if identity.get("protocol_version") != CFG.expected_c23_protocol: raise RuntimeError("C23 identity protocol mismatch")
    if identity.get("decision") != CFG.expected_c23_dev_decision: raise RuntimeError("C23 development is not PASS")
    if s1d.get("decision") != CFG.expected_c23_stage1d_decision: raise RuntimeError("C23 Stage1D is not PASS")
    if q2.get("decision") != CFG.expected_c23_q2_decision: raise RuntimeError("C23 Q2 is not PASS")
    if bool(identity.get("test_used")) or bool(s1d.get("gates", {}).get("test_unused")) is not True or bool(q2.get("gates", {}).get("test_unused")) is not True:
        raise RuntimeError("C23 Test-isolation evidence is invalid")
    if int(identity.get("max_online_gradient_steps_per_candidate", -1)) != 50: raise RuntimeError("C23 max online steps mismatch")
    _meta, bank = load_weight_bank(paths["bank"], map_location="cpu")
    profiles = load_json(paths["stage2_profiles"])
    architecture_tables = {int(H): {int(r["arch_idx"]): dict(r) for r in rows} for H, rows in profiles["architecture_tables"].items()}
    anchors = {str(H): select_anchor_indices(list(architecture_tables[int(H)].values()), families=PROFILE_CFG.families, quantiles=PROFILE_CFG.anchor_quantiles) for H in CFG.H_list}
    pi_obj = load_json(paths["source_pi50"])
    pi50 = list(map(float, pi_obj["pi50"]))
    if len(pi50) != CFG.architecture_count: raise RuntimeError("pi50 length mismatch")
    return {"paths": paths, "identity": identity, "stage1d": s1d, "q2": q2, "bank_meta": _meta, "bank": bank, "profiles_obj": profiles, "architecture_tables": architecture_tables, "anchor_indices": anchors, "pi50": pi50, "hashes": {k: file_sha256(v) for k, v in paths.items()}}


def build_runtime(device: str, safe_mode: str, blocks: Sequence[Tuple[int, int, int]]):
    requested = torch.device(device)
    if requested.type == "cuda" and not torch.cuda.is_available(): raise RuntimeError("CUDA requested but unavailable")
    safe = configure_stage2_runtime(requested, safe_mode)
    cfg = load_and_merge("ours", main_module="configs.main_cfg", methods_pkg="configs.methods", smoke=False)
    cfg.main.sim.seed = CFG.data_seed; cfg.main.split.n_train_centers = CFG.source_centers; cfg.main.device = str(requested)
    cache = build_v2_development_cache(cfg, blocks=tuple(blocks))
    A = enumerate_A_base(cfg.main.arch)
    if len(A) != CFG.architecture_count: raise RuntimeError("Architecture-space mismatch: %s" % len(A))
    return cfg, cache, A, requested, safe


def feasible_indices(cfg, A: Sequence[Any], tier: str, L: int, input_dim: int, H: int) -> List[int]:
    return [i for i, spec in enumerate(A) if bool(is_feasible(spec, cfg.main.budget, str(tier), int(L), int(input_dim), int(H)))]


def case_features(cfg, tier: str, H: int, K: int, dtype: torch.dtype) -> Tuple[List[float], List[float]]:
    bf = float(getattr(cfg.main.budget, tier).flops); bp = float(getattr(cfg.main.budget, tier).params)
    maxf = float(cfg.main.budget.loose.flops); maxp = float(cfg.main.budget.loose.params)
    b = build_budget_features(budget_flops=bf, budget_params=bp, tier_name=tier, max_flops=maxf, max_params=maxp, device=torch.device("cpu"), dtype=dtype)
    c = build_task_features(H=H, K=K, max_H=max(CFG.H_list), max_K=max(CFG.K_list), device=torch.device("cpu"), dtype=dtype)
    return b.detach().cpu().reshape(-1).tolist(), c.detach().cpu().reshape(-1).tolist()


def build_case_profile(Xs, ys, A, architecture_table, anchor_indices, bank, input_dim: int, H: int, K: int, L: int, device: torch.device) -> Dict[str, Any]:
    return build_prior_response_profile(X_support=Xs, y_support=ys, A_specs=A, arch_table=list(architecture_table.values()), anchor_indices=anchor_indices, bank=bank, input_dim=input_dim, H=H, K=K, L=L, value_dim=12, max_h=max(CFG.H_list), steps=PROFILE_CFG.trace_steps, lr=PROFILE_CFG.trace_lr, weight_decay=PROFILE_CFG.trace_weight_decay, delta=PROFILE_CFG.trace_huber_delta, internal_folds=PROFILE_CFG.internal_folds, max_grad_norm=PROFILE_CFG.max_grad_norm, device=device)


def eval_metrics(model, X, y) -> Dict[str, float]:
    dev = next(model.parameters()).device; model.eval()
    with torch.no_grad():
        pred = model(X.to(dev).contiguous()); target = y.to(dev).contiguous()
        return {"weighted_mse": float(eval_weighted_mse(pred, target)), "mae": float(eval_mae(pred, target)), "worst10": float(eval_worst10(pred, target, p=0.10))}


def _loss(model, X, y) -> float:
    return float(eval_metrics(model, X, y)["weighted_mse"])


def run_c23_candidate(spec, *, bank, identity, Xs, ys, Xv, yv, Xc, yc, H: int, K: int, L: int, input_dim: int, requested: torch.device, safe_mode: str, seed: int, force_mode: Optional[str] = None, safe_fallback: bool = True) -> Tuple[torch.nn.Module, Dict[str, Any]]:
    actual = candidate_device(spec, requested, safe_mode)
    with candidate_backend_context(spec, actual, safe_mode):
        model, prior_state = _load_prior_model(spec=spec, H=int(H), L=int(L), input_dim=int(input_dim), bank=bank, device=actual)
        direct_support = _loss(model, Xs, ys); direct_val = _loss(model, Xv, yv); direct_check = eval_metrics(model, Xc, yc)
        features = extract_pre_adaptation_features(direct_support_loss=direct_support, direct_val_loss=direct_val, Xs=Xs, ys=ys, Xv=Xv, yv=yv, H=H, K=K, family=str(spec.family))
        prob = float(predict_std_probability(identity["controller"], vectorize_feature_dict(features).reshape(1, -1))[0])
        mode = str(force_mode or choose_mode(prob, float(identity["selected_mode_probability_threshold"])))
        if mode not in ("REG50", "STD50"): raise ValueError("force_mode must be REG50 or STD50")
        if mode == "REG50":
            effective = float(identity["frozen_base_lambda"]) * (20.0 / float(K))
            adapt_info = adapt_prior_preserving(model, Xs, ys, prior_state=prior_state, steps=50, lr=CFG.adapt_lr, prior_lambda=effective, huber_delta=CFG.huber_delta, seed=seed, max_grad_norm=CFG.grad_clip)
        else:
            adapt_steps(model, Xs.to(actual).contiguous(), ys.to(actual).contiguous(), steps=50, lr=CFG.adapt_lr, weight_decay=0.0, robust_loss_type="huber", huber_delta=CFG.huber_delta, cvar_lambda=0.0, prior_state=prior_state, prior_group_lambdas=None, batch_size=0, use_amp=False, oom_to_cpu=False, seed=seed, max_grad_norm=CFG.grad_clip)
            adapt_info = {"prior_lambda": 0.0, "adapt_steps_done": 50.0}
        selected_val = _loss(model, Xv, yv)
        acceptance = safe_accept_selected_mode(direct_val=direct_val, selected_val=selected_val, selected_mode=mode, tau=float(identity["selected_acceptance_tau"]))
        if not safe_fallback: acceptance = dict(acceptance, accepted_adaptation=True, final_mode=mode, selected_steps=50)
        if not acceptance["accepted_adaptation"]:
            model, _prior2 = _load_prior_model(spec=spec, H=int(H), L=int(L), input_dim=int(input_dim), bank=bank, device=actual)
        final_val = eval_metrics(model, Xv, yv); final_check = eval_metrics(model, Xc, yc)
        model.eval()
        with torch.no_grad(): predc = model(Xc.to(actual).contiguous())
        cons, parts = eval_paper_sequence_consistency(predc, yc.to(actual).contiguous())
        synchronize_if_cuda(actual)
        return model, {"features": features, "prob_std50": prob, "pre_adaptation_mode": mode, "acceptance": acceptance, "direct_support_mse": direct_support, "direct_val_mse": direct_val, "direct_check": direct_check, "adapt_info": adapt_info, "final_val": final_val, "final_check": final_check, "check_sequence_consistency": float(cons), "check_sequence_parts": parts, "formal_score": float(final_val["weighted_mse"] + CFG.dt_star_beta * cons), "one_branch_only": True, "max_gradient_steps": 50, "test_used": False}


def run_direct_candidate(spec, *, bank, Xv, yv, Xc, yc, H, L, input_dim, requested, safe_mode):
    actual = candidate_device(spec, requested, safe_mode)
    with candidate_backend_context(spec, actual, safe_mode):
        model, _ = _load_prior_model(spec=spec, H=int(H), L=int(L), input_dim=int(input_dim), bank=bank, device=actual)
        val = eval_metrics(model, Xv, yv); chk = eval_metrics(model, Xc, yc)
        model.eval()
        with torch.no_grad(): p = model(Xc.to(actual).contiguous())
        cons, parts = eval_paper_sequence_consistency(p, yc.to(actual).contiguous())
        return model, {"final_mode": "DIRECT0", "final_val": val, "final_check": chk, "check_sequence_consistency": cons, "check_sequence_parts": parts, "formal_score": float(val["weighted_mse"] + CFG.dt_star_beta * cons), "max_gradient_steps": 0, "test_used": False}


def make_case_dict(cfg, A, table, feasible, cid, H, K, tier, ctype, Xs):
    L = int(cfg.main.task.L); b, c = case_features(cfg, tier, H, K, Xs.dtype)
    return {"case_key": "c%s_h%s_k%s_b%s" % (cid, H, K, tier), "center_id": int(cid), "center_type": str(ctype), "budget_tier": str(tier), "H": int(H), "K": int(K), "profile_key": "c%s_h%s_k%s" % (cid, H, K), "budget_features": b, "case_features": c, "candidate_indices": [int(i) for i in feasible], "feasible_indices": [int(i) for i in feasible], "families": [str(table[i]["family"]) for i in feasible], "arch_keys": [str(table[i]["arch_key"]) for i in feasible], "params": [float(table[i]["params"]) for i in feasible], "flops": [float(table[i]["flops"]) for i in feasible]}


def center_bootstrap(values_by_center: Mapping[int, Sequence[float]], seed: int) -> Dict[str, float]:
    arr = np.asarray([np.mean(values_by_center[c]) for c in sorted(values_by_center)], dtype=float)
    if arr.size == 0: return {"mean": None, "median": None, "ci_low": None, "ci_high": None, "n_centers": 0}
    rng = np.random.default_rng(int(seed)); ids = rng.integers(0, len(arr), size=(CFG.bootstrap_repeats, len(arr))); boot = arr[ids].mean(axis=1)
    return {"mean": float(arr.mean()), "median": float(np.median(arr)), "ci_low": float(np.quantile(boot, .025)), "ci_high": float(np.quantile(boot, .975)), "n_centers": int(len(arr))}


def relative_gain(new: float, ref: float) -> float:
    return float((float(ref) - float(new)) / (abs(float(ref)) + CFG.eps))


def cvar90(values: Iterable[float]) -> float:
    arr = np.sort(np.asarray(list(values), dtype=float)); k = max(1, int(math.ceil(.1 * len(arr)))); return float(arr[-k:].mean())
