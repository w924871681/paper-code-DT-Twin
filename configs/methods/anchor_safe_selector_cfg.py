# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class AnchorSafeSelectorConfig:
    """Frozen C3-2 anchor-safe selector calibration protocol.

    C3-2 reuses the frozen C3-1 strong compact bank. It does not retrain
    source models, reopen the 66-architecture space, reuse historical Pool K,
    or read Test. The development pool calibrates one pre-registered relative
    Validation margin; the final pool is opened only after the selector file
    has been frozen.
    """

    protocol_version: str = "c3_2_anchor_safe_selector_calibration_v1_0"
    data_seed: int = 2904
    train_seed: int = 2904

    # C3-2 development and one-shot final pools.
    selector_dev_pool: Tuple[int, int, int] = (940, 20, 200000)
    final_pool: Tuple[int, int, int] = (960, 20, 210000)
    H_list: Tuple[int, ...] = (1, 4)
    K_list: Tuple[int, ...] = (10, 20)

    architecture_count: int = 66
    anchor_arch_idx: int = 57
    compact_arch_indices: Tuple[int, ...] = (1, 6, 13, 55, 56, 57)
    compact_non_anchor_indices: Tuple[int, ...] = (1, 6, 13, 55, 56)

    output_root: str = "outputs/anchor_safe_selector_d2904_t2904"

    # Frozen C3-1 evidence and assets.
    c31_audit_path: str = (
        "outputs/source_prior_bank_d2904_t2904/audit/c31_audit.json"
    )
    c31_analysis_path: str = (
        "outputs/source_prior_bank_d2904_t2904/analysis/c31_analysis.json"
    )
    c31_bank_manifest_path: str = (
        "outputs/source_prior_bank_d2904_t2904/strong_bank/"
        "c31_strong_bank_manifest.json"
    )
    expected_c31_audit_decision: str = (
        "PASS_C31_COMPACT_COMPLETE_AND_AUDITED"
    )
    expected_c31_analysis_decision: str = "REVISE_VALIDATION_SELECTOR_ONLY"
    expected_c31_bank_decision: str = "PASS_C31_STRONG_BANK_FROZEN"

    # Legacy C1-A57 remains in the candidate pool to preserve C3-1 semantics.
    c1_bank_path: str = (
        "outputs/formal_c1_seed2904/shared_artifacts/"
        "ours_weight_bank_source_pooled_c1_v1_src20.pt"
    )
    c1_bank_sha256: str = (
        "bb3a655606af3b554a8f088bb1d2f3f8d9f190b0911a812fd3755d3de3216b9d"
    )

    # Common target adaptation. Every candidate in one case uses the same
    # seed to avoid architecture-dependent stochastic trajectories.
    target_steps: int = 50
    target_lr: float = 1e-2
    target_grad_clip: float = 1.0
    target_seed_policy: str = "same_case_seed_for_all_candidates"

    # Pre-registered finite selector grid. Development selects the smallest
    # margin satisfying all safety and gain gates.
    margin_grid: Tuple[float, ...] = (0.05, 0.075, 0.10, 0.125, 0.15, 0.20)
    selector_rule: str = "smallest_eligible_margin"

    bootstrap_repeats: int = 4000
    eps: float = 1e-12

    primary_gain_mean: float = 0.03
    primary_gain_ci_low: float = 0.0
    harmful_switch_rate_max: float = 0.05
    architecture_increment_mean: float = 0.03
    architecture_increment_ci_low: float = 0.0

    # All pools used before C3-2. The C3-2 development and final pools must
    # also be mutually disjoint.
    known_used_center_ranges: Tuple[Tuple[int, int], ...] = (
        (0, 219),
        (420, 839),
        (900, 939),
    )


CFG = AnchorSafeSelectorConfig()


def config_dict() -> Dict[str, object]:
    return asdict(CFG)
