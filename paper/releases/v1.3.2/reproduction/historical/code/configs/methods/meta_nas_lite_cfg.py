# cfg/methods/meta_nas_lite_cfg.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MetaNasLiteCfg:
    """Unconditioned meta-architecture-search baseline.

    It receives the same source-center pool, 66-architecture search space,
    12 fully adapted target candidates, 50 target updates, and hard budgets as
    Ours.  It does not receive the center signature, condition vector,
    conditional structural prior, or condition-modulated gradient update.
    """

    name: str = "MetaNASLiteFairV4"

    # ----- meta prior construction -----
    # Use every source center available at the current source scale.
    meta_prior_centers: int = 0
    meta_prior_arch_sample: int = 24
    meta_prior_adapt_steps: int = 10
    meta_prior_adapt_lr: float = 1e-3
    meta_prior_weight_decay: float = 0.0
    meta_prior_seed: int = 2026
    meta_prior_use_all_support_sizes: bool = True

    # ----- candidate search -----
    proxy_type: str = "entropy"
    proxy_batch_size: int = 16
    proxy_seed: int = 2026
    sample_without_replacement: bool = True
    pre_filter_budget: bool = True
    allow_infeasible_in_topk: bool = False

    # blending: unconditioned source prior + target support proxy
    score_w_meta: float = 0.60
    score_w_proxy: float = 0.40

    # ----- few-shot adaptation on target center -----
    adapt_lr: float = 1e-3
    adapt_weight_decay: float = 0.0

    # ----- progress -----
    progress_print_every: int = 1


CFG = MetaNasLiteCfg()
