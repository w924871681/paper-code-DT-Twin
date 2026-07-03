# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Tuple


@dataclass(frozen=True)
class PriorResponseProfileCfg:
    protocol_version: str = "prior_response_instantiation_profile_v1"
    data_seed: int = 2904
    train_seed: int = 2904

    # Frozen development boundary. Final pools 220--319 are forbidden.
    center_start: int = 20
    center_end: int = 219
    expected_centers: int = 200
    H_list: Tuple[int, ...] = (1, 4)
    K_list: Tuple[int, ...] = (10, 20)
    expected_profiles: int = 800
    expected_cases: int = 800

    # Frozen shared source prior.
    weight_bank_path: str = (
        "outputs/formal_c1_seed2904/shared_artifacts/"
        "ours_weight_bank_source_pooled_c1_v1_src20.pt"
    )
    expected_prior_type: str = "source_pooled_c1"
    expected_bank_version: str = "source_pooled_c1_v1"

    # Structured anchor set: three source-prior anchors per family selected at
    # low/middle/high complexity quantiles without using target labels.
    anchors_per_family: int = 3
    anchor_quantiles: Tuple[float, ...] = (0.00, 0.50, 1.00)
    families: Tuple[str, ...] = ("MLP", "TCN", "GRU")

    # Support-internal prior-response trace. These steps do not replace the
    # formal 50-step adaptation; they only measure early compatibility.
    trace_steps: Tuple[int, ...] = (0, 1, 3, 5)
    trace_lr: float = 3e-4
    trace_weight_decay: float = 0.0
    trace_huber_delta: float = 0.2
    internal_folds: int = 2
    max_grad_norm: float = 5.0

    # Architecture-aware center-disjoint ranking audit.
    outer_folds: int = 5
    global_pca_dim: int = 12
    anchor_pca_dim: int = 10
    rank_ridge_alpha: float = 40.0
    max_pairs_per_case: int = 320
    boundary_rank: int = 12
    topk_fine: int = 12
    topk_coarse: int = 36
    bootstrap_repeats: int = 4000
    min_fold_wins: int = 4
    family_noninferiority: float = -0.02

    # Full-role acceptance: the true profile must beat both the no-profile
    # context baseline and matched shuffled profiles. There is deliberately no
    # "coarse-only" acceptance branch.
    primary_metrics: Tuple[str, ...] = ("ndcg12", "boundary_auc")
    support_metrics: Tuple[str, ...] = ("kendall", "pairwise_auc", "ndcg36")


CFG = PriorResponseProfileCfg()


def config_dict():
    return asdict(CFG)
