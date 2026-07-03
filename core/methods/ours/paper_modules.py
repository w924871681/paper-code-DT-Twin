# core/methods/ours/paper_modules.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import torch
import torch.nn as nn

from core.methods.ours.condition import build_portrait_signature_v5


PARAM_GROUPS = ("shared", "temporal", "recurrent", "norm", "head")
GROUP_TO_ID = {name: i for i, name in enumerate(PARAM_GROUPS)}
TIER_TO_ID = {"tight": 0, "medium": 1, "loose": 2}


def parameter_group(name: str) -> str:
    s = str(name).lower()
    if "norm" in s:
        return "norm"
    if "head" in s or "proj_out" in s or "fc_out" in s or s.endswith("bias"):
        return "head"
    if "gru" in s or "rnn" in s:
        return "recurrent"
    if "conv" in s or "tcn" in s:
        return "temporal"
    return "shared"


def build_budget_features(
    *,
    budget_flops: float,
    budget_params: float,
    tier_name: str,
    max_flops: float,
    max_params: float,
    device: torch.device,
    dtype: torch.dtype,
) -> torch.Tensor:
    """Build a label-free deployment-boundary descriptor."""
    bf = torch.tensor(float(budget_flops), device=device, dtype=dtype)
    bp = torch.tensor(float(budget_params), device=device, dtype=dtype)
    mf = max(1.0, float(max_flops))
    mp = max(1.0, float(max_params))
    base = torch.stack([
        torch.log1p(bf.clamp_min(0.0))
        / torch.log1p(torch.tensor(mf, device=device, dtype=dtype)),
        torch.log1p(bp.clamp_min(0.0))
        / torch.log1p(torch.tensor(mp, device=device, dtype=dtype)),
    ])
    tier = torch.zeros(3, device=device, dtype=dtype)
    tier[TIER_TO_ID.get(str(tier_name), 1)] = 1.0
    return torch.cat([base, tier], dim=0)


def build_task_features(
    *,
    H: int,
    K: int,
    max_H: int,
    max_K: int,
    device: torch.device,
    dtype: torch.dtype,
) -> torch.Tensor:
    """Encode the known target task configuration without using target labels."""
    h = torch.tensor(float(H), device=device, dtype=dtype).clamp_min(1.0)
    k = torch.tensor(float(K), device=device, dtype=dtype).clamp_min(1.0)
    mh = torch.tensor(float(max(1, int(max_H))), device=device, dtype=dtype)
    mk = torch.tensor(float(max(1, int(max_K))), device=device, dtype=dtype)
    return torch.stack([
        h / mh,
        k / mk,
        torch.log1p(h) / torch.log1p(mh),
        torch.log1p(k) / torch.log1p(mk),
    ])


class MLPEncoder(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int, out_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(int(in_dim), int(hidden_dim)),
            nn.LayerNorm(int(hidden_dim)),
            nn.GELU(),
            nn.Linear(int(hidden_dim), int(out_dim)),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class MaskedSoftmaxFusion(nn.Module):
    """Fuse a fixed set of branches with exact branch masking.

    A disabled branch receives zero probability rather than a zero input through
    a biased encoder. This avoids the train/inference mismatch observed in the
    diagnostic implementation where f_task(0) was still non-zero.
    """

    def __init__(self, branch_dims: Tuple[int, ...], condition_dim: int):
        super().__init__()
        if len(branch_dims) < 2:
            raise ValueError("MaskedSoftmaxFusion requires at least two branches")
        self.branch_dims = tuple(int(x) for x in branch_dims)
        self.condition_dim = int(condition_dim)
        self.projections = nn.ModuleList([
            nn.Linear(dim, self.condition_dim) for dim in self.branch_dims
        ])
        self.gate = nn.Sequential(
            nn.Linear(sum(self.branch_dims), self.condition_dim),
            nn.GELU(),
            nn.Linear(self.condition_dim, len(self.branch_dims)),
        )
        self.out = nn.Sequential(
            nn.LayerNorm(self.condition_dim),
            nn.Linear(self.condition_dim, self.condition_dim),
            nn.GELU(),
            nn.Linear(self.condition_dim, self.condition_dim),
        )

    def forward(
        self,
        embeddings: Tuple[torch.Tensor, ...],
        active: Tuple[bool, ...],
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        if len(embeddings) != len(self.branch_dims) or len(active) != len(self.branch_dims):
            raise ValueError("Fusion branch count mismatch")
        if not any(bool(x) for x in active):
            ref = embeddings[0]
            z = torch.zeros(self.condition_dim, device=ref.device, dtype=ref.dtype)
            w = torch.zeros(len(active), device=ref.device, dtype=ref.dtype)
            return z, w

        gated_inputs = tuple(
            emb if bool(flag) else torch.zeros_like(emb)
            for emb, flag in zip(embeddings, active)
        )
        logits = self.gate(torch.cat(gated_inputs, dim=-1))
        mask = torch.tensor(active, device=logits.device, dtype=torch.bool)
        logits = logits.masked_fill(~mask, torch.finfo(logits.dtype).min)
        weights = torch.softmax(logits, dim=-1)
        projected = [proj(emb) for proj, emb in zip(self.projections, gated_inputs)]
        fused = sum(weights[i] * projected[i] for i in range(len(projected)))
        return self.out(fused), weights


class AnchoredStructuralPriorModulator(nn.Module):
    """Bounded target residual around the transferable global prior.

    rho_c = pi + alpha_c * Delta_c,
    alpha_c in [0, alpha_max], Delta_c in [-1, 1].

    The residual head is zero-initialized, so a newly trained controller starts
    exactly from the global meta-prior instead of freely rewriting the ranking.
    """

    def __init__(
        self,
        condition_dim: int,
        hidden_dim: int,
        num_arch: int,
        alpha_max: float,
        alpha_init: float,
    ):
        super().__init__()
        self.alpha_max = float(alpha_max)
        if not (0.0 < float(alpha_init) < self.alpha_max):
            raise ValueError("alpha_init must be in (0, alpha_max)")
        self.map = nn.Sequential(
            nn.Linear(int(condition_dim), int(hidden_dim)),
            nn.GELU(),
            nn.Linear(int(hidden_dim), int(hidden_dim)),
            nn.GELU(),
        )
        self.residual_head = nn.Linear(int(hidden_dim), int(num_arch))
        self.alpha_head = nn.Linear(int(hidden_dim), 1)

        nn.init.zeros_(self.residual_head.weight)
        nn.init.zeros_(self.residual_head.bias)
        nn.init.zeros_(self.alpha_head.weight)
        p0 = float(alpha_init) / self.alpha_max
        p0 = min(max(p0, 1e-4), 1.0 - 1e-4)
        nn.init.constant_(self.alpha_head.bias, torch.logit(torch.tensor(p0)).item())

    def forward(
        self,
        condition: torch.Tensor,
        pi: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        h = self.map(condition)
        residual = torch.tanh(self.residual_head(h))
        # Centering removes a ranking-irrelevant common shift and makes the
        # trust-region penalty easier to interpret.
        residual = residual - residual.mean(dim=-1, keepdim=False)
        alpha = self.alpha_max * torch.sigmoid(self.alpha_head(h)).squeeze(-1)
        rho = pi + alpha * residual
        return rho, alpha, residual


class AdaptationController(nn.Module):
    """Generate parameter-group update scales and prior preservation strength."""

    def __init__(
        self,
        condition_dim: int,
        hidden_dim: int,
        modulation_min: float,
        modulation_max: float,
        prior_lambda_min: float,
        prior_lambda_max: float,
    ):
        super().__init__()
        self.modulation_min = float(modulation_min)
        self.modulation_max = float(modulation_max)
        self.lambda_min = float(prior_lambda_min)
        self.lambda_max = float(prior_lambda_max)
        self.trunk = nn.Sequential(
            nn.Linear(int(condition_dim), int(hidden_dim)),
            nn.GELU(),
            nn.Linear(int(hidden_dim), int(hidden_dim)),
            nn.GELU(),
        )
        self.mod_head = nn.Linear(int(hidden_dim), len(PARAM_GROUPS))
        self.lambda_head = nn.Linear(int(hidden_dim), 1)

    def forward(self, condition: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        h = self.trunk(condition)
        mod01 = torch.sigmoid(self.mod_head(h))
        modulation = self.modulation_min + (self.modulation_max - self.modulation_min) * mod01
        lam01 = torch.sigmoid(self.lambda_head(h)).squeeze(-1)
        prior_lambda = self.lambda_min + (self.lambda_max - self.lambda_min) * lam01
        return modulation, prior_lambda


class PaperConditionStack(nn.Module):
    """Split-condition controller for the formal C1 pipeline.

    The controller keeps two logically distinct condition paths:

    * architecture admission: target-center state + task descriptor;
    * parameter adaptation: target-center state + deployment budget.

    Resource information still participates in architecture admission through
    the explicit budget-compatibility score and hard feasible-first rule.  This
    separation is essential for the fixed 2x2 admission study because it lets
    the structural condition residual and the resource term be switched on and
    off independently without changing the adaptation controller.
    """

    def __init__(
        self,
        *,
        portrait_dim: int,
        budget_dim: int,
        task_dim: int,
        num_arch: int,
        state_hidden_dim: int,
        state_embed_dim: int,
        budget_hidden_dim: int,
        budget_embed_dim: int,
        task_hidden_dim: int,
        task_embed_dim: int,
        condition_dim: int,
        condition_hidden_dim: int,
        arch_residual_alpha_max: float,
        arch_residual_alpha_init: float,
        modulation_min: float,
        modulation_max: float,
        prior_lambda_min: float,
        prior_lambda_max: float,
    ):
        super().__init__()
        self.state_encoder = MLPEncoder(portrait_dim, state_hidden_dim, state_embed_dim)
        self.budget_encoder = MLPEncoder(budget_dim, budget_hidden_dim, budget_embed_dim)
        self.task_encoder = MLPEncoder(task_dim, task_hidden_dim, task_embed_dim)

        self.arch_fusion = MaskedSoftmaxFusion(
            (state_embed_dim, budget_embed_dim, task_embed_dim), condition_dim
        )
        self.adapt_fusion = MaskedSoftmaxFusion(
            (state_embed_dim, budget_embed_dim), condition_dim
        )
        self.prior_modulator = AnchoredStructuralPriorModulator(
            condition_dim,
            condition_hidden_dim,
            num_arch,
            alpha_max=arch_residual_alpha_max,
            alpha_init=arch_residual_alpha_init,
        )
        self.adaptation_controller = AdaptationController(
            condition_dim,
            condition_hidden_dim,
            modulation_min,
            modulation_max,
            prior_lambda_min,
            prior_lambda_max,
        )

    def encode_split(
        self,
        portrait: torch.Tensor,
        budget_features: torch.Tensor,
        task_features: torch.Tensor,
        *,
        use_state: bool = True,
        use_budget: bool = True,
        use_budget_in_admission: bool | None = None,
        use_budget_in_adaptation: bool | None = None,
        use_task_in_admission: bool = True,
    ) -> Dict[str, torch.Tensor]:
        # ``use_budget`` is retained as a backward-compatible default.  New
        # callers should specify the admission/adaptation budget switches
        # explicitly so the two effects cannot be conflated.
        if use_budget_in_admission is None:
            use_budget_in_admission = bool(use_budget)
        if use_budget_in_adaptation is None:
            use_budget_in_adaptation = bool(use_budget)

        hs = self.state_encoder(portrait)
        hb = self.budget_encoder(budget_features)
        ht = self.task_encoder(task_features)
        arch_condition, arch_gate = self.arch_fusion(
            (hs, hb, ht),
            (
                bool(use_state),
                bool(use_budget_in_admission),
                bool(use_task_in_admission),
            ),
        )
        adapt_condition, adapt_gate = self.adapt_fusion(
            (hs, hb),
            (bool(use_state), bool(use_budget_in_adaptation)),
        )
        return {
            "arch_condition": arch_condition,
            "adapt_condition": adapt_condition,
            "arch_gate": arch_gate,
            "adapt_gate": adapt_gate,
        }

    def forward(
        self,
        portrait: torch.Tensor,
        budget_features: torch.Tensor,
        task_features: torch.Tensor,
        pi: torch.Tensor,
        *,
        use_state: bool = True,
        use_budget: bool = True,
        use_budget_in_admission: bool | None = None,
        use_budget_in_adaptation: bool | None = None,
        use_task: bool = True,
        use_prior_modulation: bool = True,
        use_adaptation_modulation: bool = True,
    ) -> Dict[str, torch.Tensor]:
        enc = self.encode_split(
            portrait,
            budget_features,
            task_features,
            use_state=use_state,
            use_budget=use_budget,
            use_budget_in_admission=use_budget_in_admission,
            use_budget_in_adaptation=use_budget_in_adaptation,
            use_task_in_admission=use_task,
        )
        if use_prior_modulation:
            rho, alpha, residual = self.prior_modulator(enc["arch_condition"], pi)
        else:
            rho = pi
            alpha = torch.zeros((), device=pi.device, dtype=pi.dtype)
            residual = torch.zeros_like(pi)

        if use_adaptation_modulation:
            modulation, prior_lambda = self.adaptation_controller(enc["adapt_condition"])
        else:
            modulation = torch.ones(len(PARAM_GROUPS), device=pi.device, dtype=pi.dtype)
            prior_lambda = torch.zeros((), device=pi.device, dtype=pi.dtype)

        return {
            **enc,
            # Backward-compatible alias used by old diagnostics.
            "condition": enc["arch_condition"],
            "rho": rho,
            "arch_alpha": alpha,
            "arch_residual": residual,
            "modulation": modulation,
            "prior_lambda": prior_lambda,
        }


@dataclass
class ConditionArtifact:
    portrait_dim: int
    budget_dim: int
    task_dim: int
    num_arch: int
    pi: torch.Tensor
    state_dict: Dict[str, torch.Tensor]
    config: Dict[str, float | int | str]


def portrait_from_support(X_support: torch.Tensor) -> torch.Tensor:
    portrait, _ = build_portrait_signature_v5(X_support, normalize=True)
    return portrait
