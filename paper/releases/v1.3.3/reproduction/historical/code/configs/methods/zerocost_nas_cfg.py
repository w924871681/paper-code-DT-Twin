# cfg/methods/zerocost_nas_cfg.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class ZeroCostNASCfg:
    # proxy type (paper spirit: entropy-like zero-cost proxy)
    proxy_type: str = "entropy"

    # proxy batch control
    proxy_batch_size: int = 16
    proxy_seed: int = 2026
    sample_without_replacement: bool = True

    # === key switch for your narrative ===
    # If False: do NOT pre-filter by budget before proxy ranking (keeps many infeasible candidates).
    # This exposes the drawback: large non-deployable area => wasted scoring/adaptation time.
    pre_filter_budget: bool = False

    # If True (recommended when pre_filter_budget=False):
    # Top-K is selected purely by proxy, even if infeasible.
    # Deployability is checked only at the final selection stage (after adaptation),
    # so infeasible candidates consume adaptation budget but will be discarded.
    allow_infeasible_in_topk: bool = True

    # adaptation hyperparams for Top-K (fairness protocol still uses cfg.main.search.T_adapt_steps)
    adapt_lr: float = 1e-3
    adapt_weight_decay: float = 0.0

    # optional: fixed budget tier for ablation; normally tier should come from simulator per center
    budget_tier: str = "loose"

CFG = ZeroCostNASCfg()
