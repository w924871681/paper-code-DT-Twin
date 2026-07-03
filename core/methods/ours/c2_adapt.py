# -*- coding: utf-8 -*-
"""C2 prior-preserving fixed-step adaptation.

The prediction objective remains Adam + Huber for exactly 50 steps. C2 adds a
single normalized parameter-preservation term around the architecture-indexed
source initialization. The normalization is per parameter tensor with a scale
floor so zero or near-zero biases cannot dominate the penalty.
"""
from __future__ import annotations

from typing import Dict, Mapping

import torch
import torch.nn as nn
import torch.optim as optim

from core.methods.ours.adapt import _base_loss, _iter_minibatches


def clone_prior_state(model: nn.Module) -> Dict[str, torch.Tensor]:
    return {
        name: p.detach().cpu().clone()
        for name, p in model.named_parameters()
        if p.requires_grad
    }


def normalized_prior_penalty(
    model: nn.Module,
    prior_state: Mapping[str, torch.Tensor],
    *,
    scale_floor: float = 1e-4,
    epsilon: float = 1e-12,
) -> torch.Tensor:
    terms = []
    floor = float(scale_floor)
    eps = float(epsilon)
    for name, p in model.named_parameters():
        if (not p.requires_grad) or name not in prior_state:
            continue
        p0 = prior_state[name].to(device=p.device, dtype=p.dtype)
        ref_scale = torch.mean(p0.detach().float().pow(2)).to(dtype=p.dtype)
        ref_scale = torch.clamp(ref_scale, min=floor)
        terms.append(torch.mean((p - p0).pow(2)) / (ref_scale + eps))
    if not terms:
        return torch.zeros((), device=next(model.parameters()).device)
    return torch.stack(terms).mean()


def relative_drift(
    model: nn.Module,
    prior_state: Mapping[str, torch.Tensor],
    *,
    scale_floor: float = 1e-4,
    epsilon: float = 1e-12,
) -> float:
    values = []
    with torch.no_grad():
        for name, p in model.named_parameters():
            if (not p.requires_grad) or name not in prior_state:
                continue
            p0 = prior_state[name].to(device=p.device, dtype=p.dtype)
            ref = torch.mean(p0.float().pow(2)).clamp_min(float(scale_floor))
            val = torch.mean((p - p0).float().pow(2)) / (ref + float(epsilon))
            values.append(float(torch.sqrt(val.clamp_min(0.0)).item()))
    return float(sum(values) / max(1, len(values)))


def adapt_prior_preserving(
    model: nn.Module,
    X_tr: torch.Tensor,
    y_tr: torch.Tensor,
    *,
    prior_state: Mapping[str, torch.Tensor],
    steps: int,
    lr: float,
    prior_lambda: float,
    huber_delta: float = 0.2,
    weight_decay: float = 0.0,
    batch_size: int = 0,
    seed: int = 0,
    max_grad_norm: float = 5.0,
    scale_floor: float = 1e-4,
    epsilon: float = 1e-12,
) -> Dict[str, float]:
    dev = next(model.parameters()).device
    X = X_tr.to(dev)
    y = y_tr.to(dev)
    model.train()
    opt = optim.Adam(
        model.parameters(), lr=float(lr), weight_decay=float(weight_decay)
    )

    base_acc = 0.0
    prior_acc = 0.0
    total_acc = 0.0
    updates = 0
    for t in range(int(steps)):
        for Xb, yb in _iter_minibatches(
            X, y, int(batch_size), seed=int(seed) + 1000 * t
        ):
            opt.zero_grad(set_to_none=True)
            pred = model(Xb)
            base_loss, _ = _base_loss(
                pred,
                yb,
                loss_type="huber",
                huber_delta=float(huber_delta),
                trimmed_ratio=0.0,
            )
            prior_pen = normalized_prior_penalty(
                model,
                prior_state,
                scale_floor=float(scale_floor),
                epsilon=float(epsilon),
            )
            loss = base_loss + float(prior_lambda) * prior_pen
            loss.backward()
            if float(max_grad_norm) > 0.0:
                torch.nn.utils.clip_grad_norm_(
                    model.parameters(), max_norm=float(max_grad_norm)
                )
            opt.step()
            base_acc += float(base_loss.detach().item())
            prior_acc += float(prior_pen.detach().item())
            total_acc += float(loss.detach().item())
            updates += 1

    denom = max(1, updates)
    return {
        "adapt_loss_base": base_acc / denom,
        "adapt_loss_prior_normalized": prior_acc / denom,
        "adapt_loss_total": total_acc / denom,
        "adapt_steps_done": float(updates),
        "prior_lambda": float(prior_lambda),
        "relative_drift_final": relative_drift(
            model,
            prior_state,
            scale_floor=float(scale_floor),
            epsilon=float(epsilon),
        ),
    }
