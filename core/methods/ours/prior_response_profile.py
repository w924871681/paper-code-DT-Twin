# -*- coding: utf-8 -*-
"""Prior-response instantiation profile.

The profile is not a workload-prediction model.  It is a structured target-side
state representation for digital-twin model instantiation.  It records how the
frozen C1 source prior and a source-selected anchor architecture set respond to
few target support observations.

Only target support X/y are used. Validation/check/test and final pools are not
read here.
"""
from __future__ import annotations

import copy
import math
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn

from core.methods.ours.weight_bank import _build_model_auto, resolve_bank_key
from core.space.profile import profile_arch

EPS = 1e-8
PARAM_GROUPS = ("head", "recurrent", "temporal", "shared", "norm")


def _np(x: torch.Tensor) -> np.ndarray:
    return x.detach().cpu().numpy().astype(np.float64, copy=False)


def _safe_corr(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64).reshape(-1)
    b = np.asarray(b, dtype=np.float64).reshape(-1)
    if a.size < 3 or b.size != a.size or float(a.std()) < 1e-10 or float(b.std()) < 1e-10:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def _param_group(name: str) -> str:
    s = str(name).lower()
    if "norm" in s:
        return "norm"
    if "head" in s or s.endswith("bias") or "proj_out" in s or "fc_out" in s:
        return "head"
    if "gru" in s or "rnn" in s:
        return "recurrent"
    if "conv" in s or "tcn" in s or "blocks" in s:
        return "temporal"
    return "shared"


def architecture_embedding(spec, *, params: int, flops: int, max_params: float, max_flops: float) -> np.ndarray:
    fam = str(spec.family)
    onehot = [float(fam == x) for x in ("MLP", "TCN", "GRU")]
    hp = dict(spec.hparams)
    # Stable family-aware hyperparameter slots.
    if fam == "MLP":
        h = [float(hp["n_layers"]) / 4.0, float(hp["hidden_dim"]) / 128.0,
             float(hp["dropout"]) / 0.1 if 0.1 > 0 else 0.0, 0.0]
    elif fam == "TCN":
        h = [float(hp["n_blocks"]) / 4.0, float(hp["channels"]) / 32.0,
             float(hp["kernel"]) / 5.0, float(hp["dilation"]) / 2.0]
    else:
        h = [float(hp["n_layers"]) / 2.0, float(hp["hidden_dim"]) / 64.0,
             float(hp["dropout"]) / 0.1 if 0.1 > 0 else 0.0, 0.0]
    cost = [math.log1p(float(params)) / max(math.log1p(max_params), EPS),
            math.log1p(float(flops)) / max(math.log1p(max_flops), EPS)]
    return np.asarray(onehot + h + cost, dtype=np.float32)


def build_architecture_table(A_specs, *, L: int, input_dim: int, H: int) -> List[Dict[str, Any]]:
    raw = []
    for spec in A_specs:
        params, flops = profile_arch(spec, L=int(L), input_dim=int(input_dim), H=int(H), device="cpu")
        raw.append((spec, int(params), int(flops)))
    max_p = max(x[1] for x in raw); max_f = max(x[2] for x in raw)
    out = []
    for spec, params, flops in raw:
        out.append({
            "arch_idx": int(spec.arch_id), "arch_key": str(spec.arch_key), "family": str(spec.family),
            "params": params, "flops": flops,
            "embedding": architecture_embedding(spec, params=params, flops=flops, max_params=max_p, max_flops=max_f).tolist(),
        })
    return out


def select_anchor_indices(arch_table: Sequence[Mapping[str, Any]], *, families: Sequence[str], quantiles: Sequence[float]) -> List[int]:
    selected: List[int] = []
    for fam in families:
        rows = [r for r in arch_table if str(r["family"]) == str(fam)]
        rows = sorted(rows, key=lambda r: (float(r["params"]) + float(r["flops"]) / 100.0, int(r["arch_idx"])))
        n = len(rows)
        for q in quantiles:
            pos = int(round(float(q) * max(0, n - 1)))
            idx = int(rows[pos]["arch_idx"])
            if idx not in selected:
                selected.append(idx)
        # Quantile collisions are unlikely, but complete deterministically.
        for r in rows:
            if len([i for i in selected if any(int(x["arch_idx"]) == i and str(x["family"]) == fam for x in rows)]) >= len(quantiles):
                break
            idx = int(r["arch_idx"])
            if idx not in selected:
                selected.append(idx)
    return selected


def _loss_stats(model: nn.Module, X: torch.Tensor, y: torch.Tensor, delta: float) -> Dict[str, float]:
    model.eval()
    with torch.no_grad():
        pred = model(X)
        err = pred - y
        mse = torch.mean(err.square())
        mae = torch.mean(err.abs())
        abs_err = err.abs(); d = torch.tensor(float(delta), device=err.device, dtype=err.dtype)
        quad = torch.minimum(abs_err, d); huber = torch.mean(0.5 * quad.square() + d * (abs_err - quad))
        yvar = torch.var(y, unbiased=False).clamp_min(1e-5)
        ystd = torch.sqrt(yvar)
        return {
            "nmse": float((mse / yvar).item()),
            "nmae": float((mae / ystd).item()),
            "huber": float(huber.item()),
            "residual_bias": float((torch.mean(err).abs() / ystd).item()),
            "residual_std": float((torch.std(err, unbiased=False) / ystd).item()),
        }


def _gradient_stats(model: nn.Module, X: torch.Tensor, y: torch.Tensor, delta: float) -> Dict[str, float]:
    model.train(); model.zero_grad(set_to_none=True)
    pred = model(X); err = (pred - y).abs(); d = torch.tensor(float(delta), device=err.device, dtype=err.dtype)
    q = torch.minimum(err, d); loss = torch.mean(0.5 * q.square() + d * (err - q)); loss.backward()
    group_sq = defaultdict(float); total_g2 = 0.0; total_p2 = 0.0
    for name, p in model.named_parameters():
        total_p2 += float(torch.sum(p.detach().float().square()).item())
        if p.grad is None:
            continue
        g2 = float(torch.sum(p.grad.detach().float().square()).item())
        total_g2 += g2; group_sq[_param_group(name)] += g2
    total_g = math.sqrt(max(total_g2, 0.0)); total_p = math.sqrt(max(total_p2, 0.0))
    frac = np.asarray([group_sq[g] / max(total_g2, EPS) for g in PARAM_GROUPS], dtype=np.float64)
    entropy = float(-np.sum(frac[frac > 0] * np.log(frac[frac > 0])) / math.log(len(PARAM_GROUPS))) if np.any(frac > 0) else 0.0
    out = {"log_grad_norm": math.log1p(total_g), "grad_param_ratio": total_g / max(total_p, EPS), "grad_group_entropy": entropy}
    for g, v in zip(PARAM_GROUPS, frac.tolist()): out[f"grad_frac_{g}"] = float(v)
    model.zero_grad(set_to_none=True)
    return out


def _relative_displacement(model: nn.Module, prior_state: Mapping[str, torch.Tensor]) -> float:
    d2 = 0.0; p2 = 0.0
    for name, p in model.named_parameters():
        if name not in prior_state: continue
        p0 = prior_state[name].to(device=p.device, dtype=p.dtype)
        d2 += float(torch.sum((p.detach() - p0).float().square()).item())
        p2 += float(torch.sum(p0.float().square()).item())
    return math.sqrt(max(d2, 0.0)) / max(math.sqrt(max(p2, 0.0)), EPS)


def _adapt_one_step(model: nn.Module, opt: torch.optim.Optimizer, X: torch.Tensor, y: torch.Tensor, delta: float, max_grad_norm: float) -> None:
    model.train(); opt.zero_grad(set_to_none=True)
    pred = model(X); err = (pred - y).abs(); d = torch.tensor(float(delta), device=err.device, dtype=err.dtype)
    q = torch.minimum(err, d); loss = torch.mean(0.5 * q.square() + d * (err - q)); loss.backward()
    if float(max_grad_norm) > 0:
        torch.nn.utils.clip_grad_norm_(model.parameters(), float(max_grad_norm))
    opt.step()


def _internal_response_trace(
    *, spec, prior_state: Mapping[str, torch.Tensor], X: torch.Tensor, y: torch.Tensor,
    input_dim: int, H: int, L: int, steps: Sequence[int], lr: float, weight_decay: float,
    delta: float, folds: int, max_grad_norm: float, device: torch.device,
) -> Dict[str, float]:
    steps = tuple(sorted(set(int(s) for s in steps)))
    max_step = max(steps)
    fold_records: List[Dict[str, float]] = []
    n = int(X.shape[0]); folds = max(2, min(int(folds), n))
    for f in range(folds):
        qmask = (torch.arange(n) % folds) == f
        tmask = ~qmask
        if int(tmask.sum()) < 3 or int(qmask.sum()) < 1: continue
        model = _build_model_auto(spec, input_dim=int(input_dim), H=int(H), L=int(L), device=device)
        model.load_state_dict(prior_state, strict=True)
        opt = torch.optim.Adam(model.parameters(), lr=float(lr), weight_decay=float(weight_decay))
        rec: Dict[str, float] = {}
        initial = _loss_stats(model, X[qmask], y[qmask], delta)
        rec["query_nmse_t0"] = initial["nmse"]
        rec["query_huber_t0"] = initial["huber"]
        for t in range(1, max_step + 1):
            _adapt_one_step(model, opt, X[tmask], y[tmask], delta, max_grad_norm)
            if t in steps:
                st = _loss_stats(model, X[qmask], y[qmask], delta)
                rec[f"query_nmse_t{t}"] = st["nmse"]
                rec[f"query_huber_t{t}"] = st["huber"]
                rec[f"disp_t{t}"] = _relative_displacement(model, prior_state)
        fold_records.append(rec)
    if not fold_records:
        return {"valid_folds": 0.0}
    out: Dict[str, float] = {"valid_folds": float(len(fold_records))}
    keys = sorted(set().union(*(r.keys() for r in fold_records)))
    for k in keys:
        vals = [r[k] for r in fold_records if k in r]
        out[f"{k}_mean"] = float(np.mean(vals)); out[f"{k}_std"] = float(np.std(vals))
    base = out.get("query_nmse_t0_mean", 1.0)
    for t in steps:
        if t == 0: continue
        v = out.get(f"query_nmse_t{t}_mean", base)
        out[f"query_gain_t{t}"] = float((base - v) / max(abs(base), 1e-5))
        disp = out.get(f"disp_t{t}_mean", 0.0)
        out[f"gain_per_move_t{t}"] = float(out[f"query_gain_t{t}"] / max(disp, 1e-5))
    return out


def _compact_observation_block(X: torch.Tensor, y: torch.Tensor, *, value_dim: int, max_h: int) -> Tuple[np.ndarray, List[str]]:
    xa = _np(X); ya = _np(y)
    if ya.ndim == 3: ya = ya.mean(axis=-1)
    values = xa[:, :, :value_dim]
    if xa.shape[-1] >= value_dim * 2:
        mask = np.clip(xa[:, :, value_dim:value_dim * 2], 0.0, 1.0)
    else:
        mask = (np.abs(values) > 1e-12).astype(np.float64)
    feats: List[float] = []; names: List[str] = []
    avail = mask.mean(axis=(0, 1)); vol = values.std(axis=(0, 1))
    rough = np.mean(np.abs(np.diff(values, axis=1)), axis=(0, 1)) if values.shape[1] > 1 else np.zeros(value_dim)
    for prefix, arr in (("avail", avail), ("vol", vol), ("rough", rough)):
        feats += [float(np.mean(arr)), float(np.std(arr)), float(np.min(arr)), float(np.max(arr))]
        names += [f"obs_{prefix}_{s}" for s in ("mean", "std", "min", "max")]
    # Low-variance response summaries; no high-dimensional per-channel correlations.
    t = np.linspace(-1.0, 1.0, ya.shape[0])
    last = values[:, -1, :]
    for h in range(max_h):
        if h < ya.shape[1]:
            yh = ya[:, h]
            corr = np.asarray([_safe_corr(last[:, j], yh) for j in range(last.shape[1])])
            feats += [float(yh.mean()), float(yh.std()), float(np.mean(np.abs(np.diff(yh)))) if len(yh) > 1 else 0.0,
                      _safe_corr(yh, t), float(np.mean(np.abs(corr))), float(np.max(np.abs(corr))) if corr.size else 0.0]
        else:
            feats += [0.0] * 6
        names += [f"srv_h{h}_{s}" for s in ("mean", "std", "rough", "trend", "xy_absmean", "xy_absmax")]
    feats += [float(X.shape[0]) / 20.0, float(ya.shape[1]) / max_h]
    names += ["support_fraction", "horizon_fraction"]
    return np.nan_to_num(np.asarray(feats, dtype=np.float32), nan=0.0, posinf=20.0, neginf=-20.0), names


def build_prior_response_profile(
    *, X_support: torch.Tensor, y_support: torch.Tensor, A_specs, arch_table: Sequence[Mapping[str, Any]],
    anchor_indices: Sequence[int], bank: Mapping[str, Mapping[str, torch.Tensor]], input_dim: int, H: int, K: int, L: int,
    value_dim: int, max_h: int, steps: Sequence[int], lr: float, weight_decay: float, delta: float,
    internal_folds: int, max_grad_norm: float, device: torch.device,
) -> Dict[str, Any]:
    X = X_support.to(device); y = y_support.to(device)
    obs, obs_names = _compact_observation_block(X, y, value_dim=value_dim, max_h=max_h)
    trace_rows: List[List[float]] = []; trace_names: List[str] | None = None; anchors_meta = []
    spec_by_idx = {int(s.arch_id): s for s in A_specs}
    table_by_idx = {int(r["arch_idx"]): r for r in arch_table}
    for aidx in anchor_indices:
        spec = spec_by_idx[int(aidx)]; rowmeta = table_by_idx[int(aidx)]
        key, hit = resolve_bank_key(bank, H=int(H), arch_key=str(spec.arch_key), K=int(K),
                                    input_dim=int(input_dim), L=int(L))
        if key is None: raise RuntimeError(f"Missing C1 prior for H={H}, arch={spec.arch_key}")
        prior_state = {k: v.detach().clone() for k, v in bank[key].items()}
        model = _build_model_auto(spec, input_dim=int(input_dim), H=int(H), L=int(L), device=device)
        model.load_state_dict(prior_state, strict=True)
        base = _loss_stats(model, X, y, delta); grad = _gradient_stats(model, X, y, delta)
        trace = _internal_response_trace(spec=spec, prior_state=prior_state, X=X, y=y, input_dim=input_dim,
                                         H=H, L=L, steps=steps, lr=lr, weight_decay=weight_decay, delta=delta,
                                         folds=internal_folds, max_grad_norm=max_grad_norm, device=device)
        values: Dict[str, float] = {}
        for k0 in ("nmse", "nmae", "huber", "residual_bias", "residual_std"): values[f"full_{k0}"] = float(base[k0])
        values.update({k0: float(v) for k0, v in grad.items()})
        values.update({k0: float(v) for k0, v in trace.items()})
        names = sorted(values)
        if trace_names is None: trace_names = names
        if names != trace_names: raise RuntimeError("Anchor trace feature mismatch")
        trace_rows.append([values[n] for n in trace_names])
        anchors_meta.append({"arch_idx": int(aidx), "arch_key": str(spec.arch_key), "family": str(spec.family),
                             "params": int(rowmeta["params"]), "flops": int(rowmeta["flops"]), "bank_hit": str(hit),
                             "embedding": list(map(float, rowmeta["embedding"]))})
        del model
        if device.type == "cuda": torch.cuda.empty_cache()
    matrix = np.nan_to_num(np.asarray(trace_rows, dtype=np.float32), nan=0.0, posinf=50.0, neginf=-50.0)
    # Family summaries are part of the center-level profile, while the complete
    # anchor matrix remains available to the architecture-aware scorer.
    fam_summary: List[float] = []; fam_names: List[str] = []
    key_names = ["full_nmse", "grad_param_ratio", "query_gain_t1", "query_gain_t3", "query_gain_t5",
                 "query_nmse_t5_mean", "query_nmse_t5_std", "gain_per_move_t5"]
    pos = {n: i for i, n in enumerate(trace_names or [])}
    for fam in ("MLP", "TCN", "GRU"):
        ids = [i for i, m in enumerate(anchors_meta) if m["family"] == fam]
        for n in key_names:
            vals = matrix[ids, pos[n]] if n in pos and ids else np.zeros(1)
            fam_summary += [float(np.mean(vals)), float(np.std(vals)), float(np.min(vals)), float(np.max(vals))]
            fam_names += [f"{fam.lower()}_{n}_{s}" for s in ("mean", "std", "min", "max")]
    compact = np.concatenate([obs, np.asarray(fam_summary, dtype=np.float32)]).astype(np.float32)
    return {
        "profile_vector": compact.tolist(), "observation_vector": obs.tolist(), "family_summary": fam_summary,
        "anchor_trace_matrix": matrix.tolist(), "anchor_trace_names": trace_names or [], "anchors": anchors_meta,
        "feature_names": {"observation": obs_names, "family_summary": fam_names,
                          "profile_vector": obs_names + fam_names},
        "dims": {"observation": int(obs.size), "family_summary": int(len(fam_summary)),
                 "profile_vector": int(compact.size), "anchor_count": int(matrix.shape[0]),
                 "anchor_trace": int(matrix.shape[1])},
    }
