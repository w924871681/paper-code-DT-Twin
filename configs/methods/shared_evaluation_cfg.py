# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class FinalE2EC23Cfg:
    protocol_version: str = "shared.evaluation_audited_pipeline_v1_0"
    data_seed: int = 2904
    train_seed: int = 2904
    source_centers: int = 20

    H_list: Tuple[int, ...] = (1, 4)
    K_list: Tuple[int, ...] = (10, 20)
    architecture_count: int = 66
    top36: int = 36
    top12: int = 12

    c1_bank_path: str = "outputs/formal_c1_seed2904/shared_artifacts/ours_weight_bank_source_pooled_c1_v1_src20.pt"
    c1_bank_sha256: str = "bb3a655606af3b554a8f088bb1d2f3f8d9f190b0911a812fd3755d3de3216b9d"
    c23_identity_path: str = "outputs/c23_d2904_t2904/c23_identity.json"
    c23_stage1d_path: str = "outputs/c23_d2904_t2904/stage1d/c23_stage1d_joint_audit.json"
    c23_q2_path: str = "outputs/c23_d2904_t2904/stage1q2/c23_stage1q2_joint_qualification.json"
    expected_c23_protocol: str = "c2_3_budget_preserving_multimode_fixed50_v1"
    expected_c23_dev_decision: str = "PASS_C23_BUDGET_PRESERVING_MODE_RULE_FROZEN"
    expected_c23_stage1d_decision: str = "PASS_C23_STAGE1D_STRICT_JOINT_QUALIFICATION"
    expected_c23_q2_decision: str = "PASS_C23_STAGE1Q2_STRICT_JOINT_QUALIFICATION"

    # Existing profile assets and fixed Stage-2 development-center selection.
    stage2_selection_path: str = "outputs/c1r_rebase_d2904_t2904/stage2/reduced/fixed_center_selection.json"
    stage2_dev_profiles_path: str = "outputs/c1r_rebase_d2904_t2904/stage2/reduced/merged_profiles_240.json"
    source_pi50_path: str = "outputs/c1r_rebase_d2904_t2904/stage2/source_teacher_pi50.json"

    output_root: str = "outputs/shared.evaluation_d2904_t2904"
    stage2_model_path: str = "outputs/shared.evaluation_d2904_t2904/stage2/development/stage2_v4_c23_model.pkl"
    stage2_summary_path: str = "outputs/shared.evaluation_d2904_t2904/stage2/conditional/stage2_v4_c23_conditional_summary.json"
    stage3_summary_path: str = "outputs/shared.evaluation_d2904_t2904/stage3/conditional/stage3_c23_conditional_summary.json"
    stage4_summary_path: str = "outputs/shared.evaluation_d2904_t2904/stage4/conditional/stage4_c23_conditional_summary.json"

    # Stage-2 C23 re-estimation and conditional fresh confirmation.
    stage2_dev_expected_centers: int = 60
    stage2_dev_expected_cases: int = 240
    stage2_alphas: Tuple[float, ...] = (0.1, 1.0, 10.0, 100.0)
    stage2_pool_e: Tuple[int, int, int] = (420, 50, 90000)
    stage2_pool_f: Tuple[int, int, int] = (470, 50, 100000)

    # Stage-3 integration audit.
    stage3_pool_g: Tuple[int, int, int] = (520, 50, 110000)
    stage3_pool_h: Tuple[int, int, int] = (570, 50, 120000)

    # Stage-4 final-selection audit.
    stage4_pool_i: Tuple[int, int, int] = (620, 50, 130000)
    stage4_pool_j: Tuple[int, int, int] = (670, 50, 140000)

    # Final unopened Pool K.
    final_pool_k: Tuple[int, int, int] = (720, 50, 150000)

    c23_reg_base_lambda: float = 10.0
    c23_mode_threshold: float = 0.45
    c23_accept_tau: float = 0.05
    adapt_steps: int = 50
    adapt_lr: float = 3e-4
    huber_delta: float = 0.2
    grad_clip: float = 5.0
    dt_star_beta: float = 0.15

    bootstrap_repeats: int = 4000
    eps: float = 1e-12

    # Stage-2 direct PASS / EDGE gates. Lower regret is better.
    stage2_recall_ci_margin: float = -0.01
    stage2_best_ci_margin: float = -0.01
    stage2_regret_ci_margin: float = 0.00005
    stage2_edge_recall_point: float = -0.02
    stage2_edge_best_point: float = -0.02
    stage2_edge_regret_point: float = 0.00020

    # Stage-3 fixed-C23 integration gates.
    stage3_ci_noninferiority: float = -0.01
    stage3_subgroup_margin: float = -0.03
    stage3_edge_point_margin: float = -0.02

    # Stage-4 frozen selector gates, aligned with prior Stage-4 protocol.
    stage4_valonly_ci_margin: float = -0.01
    stage4_mean_regret_max: float = 0.05
    stage4_cvar90_regret_max: float = 0.15
    stage4_near_oracle_5pct_min: float = 0.80
    stage4_edge_mean_regret_max: float = 0.08
    stage4_edge_cvar90_regret_max: float = 0.20
    stage4_edge_near_oracle_5pct_min: float = 0.70

    main_methods: Tuple[str, ...] = (
        "ours_c23",
        "direct0",
        "always_reg50",
        "always_std50",
        "scratch50",
    )
    ablations: Tuple[str, ...] = (
        "no_cond_admission",
        "no_safe_fallback",
        "no_sequence_consistency",
    )


CFG = FinalE2EC23Cfg()


def config_dict() -> Dict[str, object]:
    return asdict(CFG)
