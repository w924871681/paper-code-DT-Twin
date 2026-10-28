# core/methods/ours/condition.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Optional, Tuple
import torch
import torch.nn as nn

TIER_TO_ID = {"tight": 0, "medium": 1, "loose": 2}


def _normalize_vec(x: torch.Tensor) -> torch.Tensor:
    if x.numel() <= 1:
        return x
    std = x.std(unbiased=False).clamp_min(1e-6)
    return (x - x.mean()) / std


def split_monitoring_features_v5(
    X: torch.Tensor,
) -> Tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor]]:
    """Parse [values, masks, optional normalized-dt] from model input.

    The default experiment input dimension is 2*K+1. Missing values are zero
    filled, so `torch.isfinite` cannot identify missingness. This parser uses
    the explicit mask channels instead.
    """
    D = int(X.shape[-1])
    if D >= 3 and (D - 1) % 2 == 0:
        K = (D - 1) // 2
        values = X[..., :K]
        mask = X[..., K:2 * K].clamp(0.0, 1.0)
        dt = X[..., -1:]
        return values, mask, dt
    if D >= 2 and D % 2 == 0:
        K = D // 2
        values = X[..., :K]
        mask = X[..., K:2 * K].clamp(0.0, 1.0)
        return values, mask, None

    # Fallback for value-only external inputs.
    values = X
    mask = torch.isfinite(X).to(X.dtype)
    return values, mask, None


def _masked_prepare(values: torch.Tensor, mask: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    valid = (mask > 0.5) & torch.isfinite(values)
    X0 = torch.where(valid, values, torch.zeros_like(values))
    return X0, valid


def _masked_mean_std(X0: torch.Tensor, valid: torch.Tensor):
    denom = valid.sum(dim=(0, 1)).clamp_min(1).to(X0.dtype)
    mu = X0.sum(dim=(0, 1)) / denom
    xc = torch.where(valid, X0 - mu.view(1, 1, -1), torch.zeros_like(X0))
    var = (xc.pow(2).sum(dim=(0, 1)) / denom).clamp_min(0.0)
    return mu, torch.sqrt(var + 1e-8)


def _masked_abs_mean(X0: torch.Tensor, valid: torch.Tensor):
    denom = valid.sum(dim=(0, 1)).clamp_min(1).to(X0.dtype)
    return X0.abs().sum(dim=(0, 1)) / denom


def _masked_quantile(values: torch.Tensor, valid: torch.Tensor, q: float) -> torch.Tensor:
    xf = values.reshape(-1, values.shape[-1])
    vf = valid.reshape(-1, valid.shape[-1])
    out = []
    for d in range(xf.shape[-1]):
        vals = xf[vf[:, d], d]
        if vals.numel() == 0:
            out.append(torch.zeros((), device=values.device, dtype=values.dtype))
        else:
            out.append(torch.quantile(vals, q))
    return torch.stack(out, dim=0)


def _masked_corr_lag(X0: torch.Tensor, valid: torch.Tensor, lag: int) -> torch.Tensor:
    if X0.shape[1] <= lag:
        return torch.zeros(X0.shape[-1], device=X0.device, dtype=X0.dtype)
    x1 = X0[:, :-lag, :]
    x2 = X0[:, lag:, :]
    m = valid[:, :-lag, :] & valid[:, lag:, :]
    denom = m.sum(dim=(0, 1)).clamp_min(1).to(X0.dtype)
    s1 = torch.where(m, x1, torch.zeros_like(x1)).sum(dim=(0, 1))
    s2 = torch.where(m, x2, torch.zeros_like(x2)).sum(dim=(0, 1))
    mu1 = s1 / denom
    mu2 = s2 / denom
    c1 = torch.where(m, x1 - mu1.view(1, 1, -1), torch.zeros_like(x1))
    c2 = torch.where(m, x2 - mu2.view(1, 1, -1), torch.zeros_like(x2))
    cov = (c1 * c2).sum(dim=(0, 1)) / denom
    v1 = (c1.pow(2).sum(dim=(0, 1)) / denom).clamp_min(1e-8)
    v2 = (c2.pow(2).sum(dim=(0, 1)) / denom).clamp_min(1e-8)
    return (cov / torch.sqrt(v1 * v2 + 1e-8)).clamp(-1.0, 1.0)


def _missing_run_stats(valid: torch.Tensor):
    # Aggregate runs within each support window instead of concatenating all
    # windows into one artificial sequence.
    B, L, D = valid.shape
    mean_runs, max_runs, burst_counts, entropies = [], [], [], []
    for d in range(D):
        all_runs = []
        for b in range(B):
            arr = (~valid[b, :, d]).to(torch.int64).tolist()
            cur = 0
            for v in arr:
                if int(v) == 1:
                    cur += 1
                elif cur > 0:
                    all_runs.append(cur)
                    cur = 0
            if cur > 0:
                all_runs.append(cur)
        if all_runs:
            rt = torch.tensor(all_runs, device=valid.device, dtype=torch.float32)
            mean_runs.append(rt.mean())
            max_runs.append(rt.max())
            burst_counts.append(torch.tensor(float(len(all_runs)) / max(1, B), device=valid.device))
        else:
            z = torch.tensor(0.0, device=valid.device)
            mean_runs.append(z)
            max_runs.append(z)
            burst_counts.append(z)
        p = (~valid[..., d]).float().mean().clamp(1e-6, 1.0 - 1e-6)
        entropies.append(-(p * p.log() + (1.0 - p) * (1.0 - p).log()))
    return (
        torch.stack(mean_runs).to(valid.dtype),
        torch.stack(max_runs).to(valid.dtype),
        torch.stack(burst_counts).to(valid.dtype),
        torch.stack(entropies).to(valid.dtype),
    )


def build_portrait_signature_v5(
    X_sup: torch.Tensor,
    normalize: bool = True,
) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
    values, explicit_mask, dt = split_monitoring_features_v5(X_sup)
    X0, valid = _masked_prepare(values, explicit_mask)

    mu, sd = _masked_mean_std(X0, valid)
    abs_mu = _masked_abs_mean(X0, valid)
    q10 = _masked_quantile(values, valid, 0.10)
    q50 = _masked_quantile(values, valid, 0.50)
    q90 = _masked_quantile(values, valid, 0.90)
    qrange = q90 - q10
    skew_proxy = (q90 + q10 - 2.0 * q50) / (qrange.abs() + 1e-6)

    valid_ratio = valid.float().mean(dim=(0, 1)).to(X_sup.dtype)
    miss_ratio = 1.0 - valid_ratio
    if values.shape[1] > 1:
        mask_jump = (valid[:, 1:, :] != valid[:, :-1, :]).float().mean(dim=(0, 1)).to(X_sup.dtype)
        dX = X0[:, 1:, :] - X0[:, :-1, :]
        dvalid = valid[:, 1:, :] & valid[:, :-1, :]
        denom_d = dvalid.sum(dim=(0, 1)).clamp_min(1).to(X_sup.dtype)
        dmu = torch.where(dvalid, dX, torch.zeros_like(dX)).sum(dim=(0, 1)) / denom_d
        dxc = torch.where(dvalid, dX - dmu.view(1, 1, -1), torch.zeros_like(dX))
        dsd = torch.sqrt((dxc.pow(2).sum(dim=(0, 1)) / denom_d).clamp_min(0.0) + 1e-8)
        first = torch.where(valid[:, 0, :], X0[:, 0, :], torch.zeros_like(X0[:, 0, :]))
        last = torch.where(valid[:, -1, :], X0[:, -1, :], torch.zeros_like(X0[:, -1, :]))
        trend = (last - first).mean(dim=0) / max(1, values.shape[1] - 1)
        acf1 = _masked_corr_lag(X0, valid, lag=1)
        acf2 = _masked_corr_lag(X0, valid, lag=2)
    else:
        mask_jump = torch.zeros_like(mu)
        dmu = torch.zeros_like(mu)
        dsd = torch.zeros_like(mu)
        trend = torch.zeros_like(mu)
        acf1 = torch.zeros_like(mu)
        acf2 = torch.zeros_like(mu)

    vol_ratio = dsd / (sd + 1e-6)
    miss_block_mean, miss_block_max, _burst_count, miss_entropy = _missing_run_stats(valid)

    value_branch = torch.cat([mu, sd, abs_mu, q10, q50, q90, qrange, skew_proxy], dim=0)
    missing_branch = torch.cat(
        [valid_ratio, miss_ratio, mask_jump, miss_block_mean, miss_block_max, miss_entropy], dim=0
    )
    temporal_branch = torch.cat([dmu, dsd, trend, acf1, acf2, vol_ratio], dim=0)

    global_missing = miss_ratio.mean()
    global_jump = mask_jump.mean()
    global_vol = vol_ratio.mean()
    schema_coverage = (valid_ratio > 0.0).float().mean()
    difficulty = (
        0.40 * global_missing
        + 0.20 * global_jump
        + 0.20 * torch.tanh(global_vol)
        + 0.10 * torch.tanh(sd.mean())
        + 0.10 * (1.0 - schema_coverage)
    ).clamp(0.0, 1.0)
    global_branch = torch.stack(
        [global_missing, global_jump, global_vol, schema_coverage, difficulty]
    ).to(X_sup.dtype)

    if normalize:
        value_branch = _normalize_vec(value_branch)
        missing_branch = _normalize_vec(missing_branch)
        temporal_branch = _normalize_vec(temporal_branch)

    portrait = torch.cat([value_branch, missing_branch, temporal_branch, global_branch], dim=0)
    sample_gap = (
        dt.mean().detach().to(X_sup.dtype)
        if dt is not None
        else torch.tensor(1.0, device=X_sup.device, dtype=X_sup.dtype)
    )
    meta = {
        "difficulty": difficulty.detach(),
        "global_missing": global_missing.detach(),
        "global_jump": global_jump.detach(),
        "global_vol": global_vol.detach(),
        "schema_coverage": schema_coverage.detach(),
        "sample_gap": sample_gap,
    }
    return portrait, meta


def extract_monitoring_stats_v5(X_sup: torch.Tensor) -> Dict[str, float]:
    _, meta = build_portrait_signature_v5(X_sup, normalize=False)
    return {k: float(v.item()) for k, v in meta.items()}


def build_condition_vector_v5(
    X_sup: torch.Tensor,
    B_flops: float,
    B_params: float,
    tier_name: str,
    center_type: str,
    normalize: bool = True,
    return_meta: bool = False,
):
    """Build condition from observable profile and known resource limits.

    `center_type` is accepted only for backward API compatibility and is not
    encoded. A/B/C are evaluation labels, not target-side input features.
    """
    del center_type
    portrait, portrait_meta = build_portrait_signature_v5(X_sup, normalize=normalize)
    device, dtype = X_sup.device, X_sup.dtype

    Bf = torch.tensor(float(B_flops), device=device, dtype=dtype)
    Bp = torch.tensor(float(B_params), device=device, dtype=dtype)
    log_budget = torch.log1p(torch.stack([Bf.clamp_min(0.0), Bp.clamp_min(0.0)]))
    budget_balance = torch.stack([
        torch.log1p((Bf / (Bp + 1.0)).clamp_min(0.0)),
        torch.log1p((Bp / (Bf + 1.0)).clamp_min(0.0)),
    ])

    tier_oh = torch.zeros(3, device=device, dtype=dtype)
    tier_id = TIER_TO_ID.get(str(tier_name), 1)
    tier_oh[tier_id] = 1.0
    tier_scalar = torch.tensor(
        [1.0 if tier_id == 0 else (0.5 if tier_id == 1 else 0.0)],
        device=device,
        dtype=dtype,
    )
    difficulty = portrait_meta["difficulty"].reshape(1).to(dtype)
    sample_gap = portrait_meta["sample_gap"].reshape(1).to(dtype)

    meta_branch = torch.cat(
        [log_budget, budget_balance, tier_oh, tier_scalar, difficulty, sample_gap],
        dim=0,
    )
    if normalize:
        meta_branch = torch.cat([_normalize_vec(meta_branch[:4]), meta_branch[4:]], dim=0)
    cond = torch.cat([portrait, meta_branch], dim=0)

    if return_meta:
        all_meta = dict(portrait_meta)
        all_meta.update({
            "tier_id": torch.tensor(float(tier_id), device=device, dtype=dtype),
            "budget_log_flops": log_budget[0].detach(),
            "budget_log_params": log_budget[1].detach(),
        })
        return cond, all_meta
    return cond


def extract_condition_difficulty_v5(X_sup: torch.Tensor) -> float:
    _, meta = build_portrait_signature_v5(X_sup, normalize=True)
    return float(meta["difficulty"].item())


class CenterSignatureEncoderV5(nn.Module):
    def __init__(self, normalize: bool = True):
        super().__init__()
        self.normalize = bool(normalize)

    def forward(self, X_sup: torch.Tensor, B_flops: float, B_params: float, tier_name: str, center_type: str):
        return build_condition_vector_v5(
            X_sup=X_sup,
            B_flops=float(B_flops),
            B_params=float(B_params),
            tier_name=str(tier_name),
            center_type=str(center_type),
            normalize=self.normalize,
        )


class PortraitEncoder(nn.Module):
    def __init__(self, in_dim: int, out_dim: int):
        super().__init__()
        del in_dim
        hidden = max(64, int(out_dim))
        self.net = nn.Sequential(
            nn.LazyLinear(hidden),
            nn.GELU(),
            nn.Linear(hidden, out_dim),
        )

    def forward(self, X_sup: torch.Tensor) -> torch.Tensor:
        portrait, _meta = build_portrait_signature_v5(X_sup, normalize=True)
        return self.net(portrait)


class BudgetEncoder(nn.Module):
    def __init__(self, out_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(2, out_dim),
            nn.GELU(),
            nn.Linear(out_dim, out_dim),
        )

    def forward(self, B_flops: float, B_params: float, device) -> torch.Tensor:
        x = torch.tensor([B_flops, B_params], dtype=torch.float32, device=device)
        return self.net(torch.log1p(x.clamp_min(0.0)))


class ConditionFusionDynamic(nn.Module):
    def __init__(self, z_dim: int, b_dim: int, e_dim: int):
        super().__init__()
        self.z_proj = nn.Linear(z_dim, e_dim)
        self.b_proj = nn.Linear(b_dim, e_dim)
        self.gate = nn.Sequential(
            nn.Linear(z_dim + b_dim, max(16, e_dim // 2)),
            nn.GELU(),
            nn.Linear(max(16, e_dim // 2), e_dim),
            nn.Sigmoid(),
        )
        self.out = nn.Sequential(
            nn.LayerNorm(e_dim),
            nn.Linear(e_dim, e_dim),
            nn.GELU(),
            nn.Linear(e_dim, e_dim),
        )

    def forward(self, zc: torch.Tensor, bc: torch.Tensor) -> torch.Tensor:
        z = self.z_proj(zc)
        b = self.b_proj(bc)
        g = self.gate(torch.cat([zc, bc], dim=0))
        return self.out(g * z + (1.0 - g) * b)
