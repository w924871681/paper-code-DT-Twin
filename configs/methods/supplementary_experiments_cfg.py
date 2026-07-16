# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class SupplementaryEvidenceCfg:
    """Frozen supplementary experiment protocol for the final JNCA paper.

    This protocol does not retune the final method. It adds four diagnostics:
    (1) a fixed 50-step adaptation trajectory on an untouched pool;
    (2) Full-vs-No-anchor risk analysis from existing candidate-level results;
    (3) five-repeat CUDA-synchronized online-time measurement;
    (4) an optional optimizer-matched 12-candidate search control.
    """

    protocol_version: str = "experiments.supplementary_v1_0"
    data_seed: int = 2904
    train_seed: int = 2904
    H_list: Tuple[int, ...] = (1, 4)
    K_list: Tuple[int, ...] = (10, 20)
    architecture_count: int = 66
    bootstrap_repeats: int = 4000
    eps: float = 1e-12

    # Untouched diagnostic/evaluation pools.
    trajectory_pool: Tuple[int, int, int] = (1080, 20, 270000)
    optimizer_control_pool: Tuple[int, int, int] = (1100, 20, 280000)
    runtime_pool: Tuple[int, int, int] = (980, 20, 220000)
    known_used_center_ranges: Tuple[Tuple[int, int], ...] = (
        (0, 219),
        (420, 839),
        (900, 1079),
    )

    # Frozen final method.
    anchor_arch_idx: int = 57
    compact_arch_indices: Tuple[int, ...] = (1, 6, 13, 55, 56, 57)
    compact_non_anchor_indices: Tuple[int, ...] = (1, 6, 13, 55, 56)
    frozen_margin_rel: float = 0.10
    target_steps: int = 50
    target_lr: float = 1e-2
    target_grad_clip: float = 1.0
    trajectory_checkpoints: Tuple[int, ...] = (0, 1, 5, 10, 20, 50)
    dense_selection_start: int = 20
    save_model_checkpoints: bool = True

    # Runtime repetition.
    runtime_methods: Tuple[str, ...] = (
        "ours_c32_locked",
        "pt_ft",
        "medet_style",
        "scratch50",
        "meta_nas_lite",
        "zero_nas",
        "zero_nas_ft",
    )
    runtime_repeats: int = 5
    runtime_warmups_per_method: int = 1

    # Optional optimizer-matched search control.
    matched_candidate_budget: int = 12
    matched_meta_prior_weight: float = 0.60
    matched_meta_proxy_weight: float = 0.40
    common12_prior_weight: float = 0.60
    common12_proxy_weight: float = 0.40
    proxy_batch_size: int = 16
    proxy_support_points: int = 6

    output_root: str = "outputs/experiments.supplementary_d2904_t2904"

    # Frozen assets and existing evidence.
    c31_bank_manifest_path: str = (
        "outputs/source_prior_bank_d2904_t2904/strong_bank/"
        "c31_strong_bank_manifest.json"
    )
    expected_c31_bank_decision: str = "PASS_C31_STRONG_BANK_FROZEN"
    c1_bank_path: str = (
        "outputs/formal_c1_seed2904/shared_artifacts/"
        "ours_weight_bank_source_pooled_c1_v1_src20.pt"
    )
    c1_bank_sha256: str = (
        "bb3a655606af3b554a8f088bb1d2f3f8d9f190b0911a812fd3755d3de3216b9d"
    )
    external_source_manifest_path: str = (
        "outputs/shared.evaluation_external_d2904_t2904/source_assets/"
        "source_assets_manifest.json"
    )
    ablation_candidates_path: str = (
        "outputs/experiments.main_d2904_t2904/ablation/"
        "ablation_candidates.json"
    )
    c33_preflight_path: str = (
        "outputs/main_evaluation_eval_d2904_t2904/preflight/c33_preflight.json"
    )


CFG_SUPP = SupplementaryEvidenceCfg()


def config_dict() -> Dict[str, object]:
    return asdict(CFG_SUPP)
