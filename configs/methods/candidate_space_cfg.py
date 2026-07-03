# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Tuple


@dataclass(frozen=True)
class V2Cfg:
    protocol_version: str = "v2_support_aware_risk_controlled_conditional_admission_v1"
    data_seed: int = 2904
    train_seed: int = 2904
    H_list: Tuple[int, ...] = (1, 4)
    K_list: Tuple[int, ...] = (10, 20)
    num_architectures: int = 66
    stage1_k: int = 36
    stage2_k: int = 12
    target_adapt_steps: int = 50
    fixed_gamma: float = 0.50
    disagreement_penalty: float = 0.20

    # Development pools that have already been exposed and are therefore used
    # only for method development / risk calibration in V2.
    dev_blocks: Tuple[Tuple[int, int, int], ...] = (
        (20, 50, 10000),
        (70, 50, 20000),
        (120, 50, 30000),
        (170, 50, 40000),
    )
    dev_center_start: int = 20
    dev_center_end: int = 219
    expected_dev_centers: int = 200
    expected_dev_cases: int = 800

    # Two final pools are frozen before any V2 model result is seen.
    final_pool_a_start: int = 220
    final_pool_a_count: int = 50
    final_pool_a_seed_offset: int = 50000
    final_pool_b_start: int = 270
    final_pool_b_count: int = 50
    final_pool_b_seed_offset: int = 60000
    expected_final_cases_per_pool: int = 200

    # Profile construction.
    bootstrap_count: int = 8
    max_K: int = 20
    value_dim: int = 12
    dynamic_feature_version: str = "multiscale_temporal_signature_v1"

    # Residual ensemble.
    outer_folds: int = 5
    ensemble_size: int = 3
    controller_epochs: int = 25
    controller_lr: float = 2e-3
    controller_weight_decay: float = 1e-4
    state_hidden_dim: int = 96
    state_embed_dim: int = 48
    budget_hidden_dim: int = 32
    budget_embed_dim: int = 16
    case_hidden_dim: int = 24
    case_embed_dim: int = 12
    fusion_hidden_dim: int = 96
    residual_hidden_dim: int = 96

    # Controller losses.
    regret_temperature: float = 0.20
    score_temperature: float = 0.35
    pairwise_margin: float = 1e-6
    contrastive_margin: float = 0.015
    safety_margin: float = 0.0
    listwise_weight: float = 1.0
    pairwise_weight: float = 0.35
    topk_weight: float = 0.25
    safety_weight: float = 3.0
    contrastive_weight: float = 1.5

    # Source-support / OOD reliability.
    support_k: int = 7
    support_tau_quantile: float = 0.75
    support_floor: float = 0.05
    agreement_tau_quantile: float = 0.75
    agreement_floor: float = 0.05

    # Benefit predictor.
    benefit_hidden_dim: int = 32
    benefit_epochs: int = 120
    benefit_lr: float = 5e-3
    benefit_weight_decay: float = 1e-4
    benefit_temperature: float = 2.5e-4
    benefit_floor: float = 0.05
    benefit_ceiling: float = 0.95
    calibration_centers_per_fold: int = 20
    final_calibration_centers: int = 20

    # Candidate composition.
    min_conditional_slots: int = 0
    max_conditional_slots: int = 12
    low_support_threshold: float = 0.30
    high_support_threshold: float = 0.70

    # Acceptance gates.
    bootstrap_repeats: int = 4000
    cvar_q: float = 0.90
    recall36_noninferiority: float = -0.02
    e2e_noninferiority_margin: float = 1e-4
    subgroup_mean_regret_margin: float = 1e-4
    subgroup_cvar_margin: float = 5e-4
    min_fold_wins: int = 4
    min_support_lambda_separation: float = 0.05


CFG = V2Cfg()


def config_dict():
    return asdict(CFG)
