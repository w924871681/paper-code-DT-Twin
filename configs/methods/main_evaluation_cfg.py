# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class MainEvaluationConfig:
    """Frozen C3 end-to-end integration and external comparison.

    C3-3 is evaluation-only. It reuses the frozen source-prior-bank evaluation strong compact bank,
    the C3-2 10% anchor-safe selector, and the previously frozen source-only
    external-baseline assets. It must not retrain source models, recalibrate
    the selector, reopen the 66-architecture search for Ours, or reuse any
    previous target pool for method development.
    """

    protocol_version: str = "c3_3_locked_e2e_external_eval_v1_0"
    data_seed: int = 2904
    train_seed: int = 2904
    source_centers: int = 20

    # One-shot locked comparison pool. Test may be opened only after each
    # method has fixed its final architecture and parameters from Support/Val.
    locked_pool: Tuple[int, int, int] = (980, 20, 220000)
    H_list: Tuple[int, ...] = (1, 4)
    K_list: Tuple[int, ...] = (10, 20)
    architecture_count: int = 66

    methods: Tuple[str, ...] = (
        "ours",
        "pt_ft",
        "medet_style",
        "scratch50",
        "meta_nas_lite",
        "zero_nas",
        "zero_nas_ft",
    )
    primary_methods: Tuple[str, ...] = (
        "ours",
        "pt_ft",
        "medet_style",
        "scratch50",
        "meta_nas_lite",
        "zero_nas_ft",
    )
    diagnostic_methods: Tuple[str, ...] = ("zero_nas",)

    output_root: str = "outputs/main_evaluation_eval_d2904_t2904"

    # Frozen C3-2 decision evidence.
    anchor_safe_selector_path: str = (
        "outputs/anchor_safe_selector_d2904_t2904/selector/"
        "anchor_safe_selector_manifest.json"
    )
    anchor_safe_selector_analysis_path: str = (
        "outputs/anchor_safe_selector_d2904_t2904/analysis/"
        "anchor_safe_selector_final_analysis.json"
    )
    anchor_safe_selector_audit_path: str = (
        "outputs/anchor_safe_selector_d2904_t2904/audit/anchor_safe_selector_audit.json"
    )
    expected_anchor_safe_selector_decision: str = "PASS_ANCHOR_SAFE_SELECTOR_FROZEN"
    expected_anchor_safe_selector_analysis_decision: str = "PROCEED_LIMITED_C3_COMPACT_ONLY"
    expected_anchor_safe_selector_audit_decision: str = (
        "PASS_ANCHOR_SAFE_SELECTOR_COMPLETE_AND_AUDITED"
    )
    expected_anchor_safe_selector_sha256: str = (
        "88505782e3b0cf7238394a380255e900d75715ccc762e6ba3041a742a7b49111"
    )
    expected_anchor_safe_selector_analysis_sha256: str = (
        "dbe01790381d69e088d7495c2075bc942ac7b91639824dd821fa9a33d4878f57"
    )
    expected_anchor_safe_selector_audit_sha256: str = (
        "3784ab52615fbc9aec795334d4ed804c6888d4f1c406cd9a008b2ce75b67c257"
    )

    # Frozen source-prior-bank evaluation strong compact bank.
    source_prior_bank_manifest_path: str = (
        "outputs/source_prior_bank_d2904_t2904/strong_bank/"
        "source_prior_bank_manifest.json"
    )
    expected_source_prior_bank_decision: str = "PASS_SOURCE_PRIOR_BANK_STRONG_BANK_FROZEN"
    expected_source_prior_bank_manifest_sha256: str = (
        "4b71e6affe3093a6a012afeea2e38000ca9ab9ae1e6991f92826bee6c9dccb2f"
    )
    anchor_arch_idx: int = 57
    compact_arch_indices: Tuple[int, ...] = (1, 6, 13, 55, 56, 57)
    compact_non_anchor_indices: Tuple[int, ...] = (1, 6, 13, 55, 56)
    frozen_margin_rel: float = 0.10

    # Frozen C1 prior used by the legacy A57 candidate and search baselines.
    c1_bank_path: str = (
        "outputs/formal_c1_seed2904/shared_artifacts/"
        "ours_weight_bank_source_pooled_c1_v1_src20.pt"
    )
    c1_bank_sha256: str = (
        "bb3a655606af3b554a8f088bb1d2f3f8d9f190b0911a812fd3755d3de3216b9d"
    )

    # Previously audited source-only PT/MeDeT assets. No retraining is allowed.
    external_source_manifest_path: str = (
        "outputs/shared.evaluation_external_d2904_t2904/source_assets/"
        "source_assets_manifest.json"
    )
    external_audit_path: str = (
        "outputs/shared.evaluation_external_d2904_t2904/audit/"
        "external_baseline_audit.json"
    )
    expected_external_source_decision: str = (
        "PASS_EXTERNAL_SOURCE_ASSETS_FROZEN"
    )
    expected_external_audit_decision: str = (
        "PASS_FINAL_E2E_C23_EXTERNAL_BASELINES_COMPLETE_AND_AUDITED"
    )
    expected_external_source_manifest_sha256: str = (
        "30042bd54eb70c8bd7722d712690ec659e9e5094ab8e14a7c436bae0a43b87a2"
    )
    expected_external_audit_sha256: str = (
        "37b44a5c26c3040922642f891b9e205c28275644f13caa4bd32e2de1c70586e0"
    )

    # Locked Ours/PT/MeDeT/Scratch target recipe.
    fixed_target_steps: int = 50
    fixed_target_lr: float = 1e-2
    fixed_target_grad_clip: float = 1.0
    fixed_target_optimizer: str = "sgd"
    fixed_target_loss: str = "mse"
    target_seed_policy: str = "same_case_seed_for_ours_candidates"

    # Frozen Meta+NAS-lite and Zero-NAS protocols inherited from the audited
    # external baseline branch. They are not tuned on centers 980--999.
    candidate_budget: int = 12
    meta_prior_weight: float = 0.60
    meta_proxy_weight: float = 0.40
    proxy_batch_size: int = 16
    proxy_support_points: int = 6
    search_target_steps: int = 50
    search_target_lr: float = 3e-4
    search_target_huber_delta: float = 0.2
    search_target_grad_clip: float = 5.0

    bootstrap_repeats: int = 4000
    eps: float = 1e-12

    # All centers used before the locked comparison pool.
    known_used_center_ranges: Tuple[Tuple[int, int], ...] = (
        (0, 219),
        (420, 839),
        (900, 979),
    )


CFG = MainEvaluationConfig()


def config_dict() -> Dict[str, object]:
    return asdict(CFG)
