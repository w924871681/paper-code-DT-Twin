# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class SourcePriorBankConfig:
    """Frozen C3-1 anchor-protected compact strong-prior protocol.

    C3-0 is treated as completed development evidence. C3-1 does not reuse
    historical Pool K and does not modify the full C3 method.
    """

    protocol_version: str = "c3_1_anchor_protected_compact_strong_prior_v1_0"
    data_seed: int = 2904
    train_seed: int = 2904
    source_centers: int = 20

    # Fresh C3-1 holdout. C3-0 used 900--919.
    fresh_pool: Tuple[int, int, int] = (920, 20, 190000)
    H_list: Tuple[int, ...] = (1, 4)
    K_list: Tuple[int, ...] = (10, 20)
    architecture_count: int = 66
    anchor_arch_idx: int = 57

    # Deterministically derived from C3-0:
    # Check-oracle true wins >=2 OR validation-positive wins >=2.
    compact_arch_indices: Tuple[int, ...] = (1, 6, 13, 55, 56, 57)
    compact_non_anchor_indices: Tuple[int, ...] = (1, 6, 13, 55, 56)
    candidate_rule_min_wins: int = 2

    output_root: str = "outputs/source_prior_bank_d2904_t2904"

    # Frozen C3-0 evidence.
    c30_preflight_path: str = "outputs/c30_d2904_t2904/preflight/c30_preflight.json"
    c30_fixed_path: str = "outputs/c30_d2904_t2904/fixed_anchor/c30_fixed_anchor.json"
    c30_oracle_path: str = "outputs/c30_d2904_t2904/oracle/c30_c1_oracle.json"
    c30_analysis_path: str = "outputs/c30_d2904_t2904/analysis/c30_analysis.json"
    c30_audit_path: str = "outputs/c30_d2904_t2904/audit/c30_audit.json"
    expected_c30_audit_decision: str = "PASS_C30_DIAGNOSTIC_COMPLETE_AND_AUDITED"
    accepted_c30_analysis_decisions: Tuple[str, ...] = (
        "PROCEED_C3_ANCHOR_PROTECTED_SEARCH",
        "PROCEED_C3_STRONG_BANK_AND_SELECTOR_RESEARCH",
    )

    # Frozen PT-A57 source asset and legacy C1 bank.
    external_source_manifest: str = (
        "outputs/shared.evaluation_external_d2904_t2904/"
        "source_assets/source_assets_manifest.json"
    )
    expected_source_decision: str = "PASS_EXTERNAL_SOURCE_ASSETS_FROZEN"
    c1_bank_path: str = (
        "outputs/formal_c1_seed2904/shared_artifacts/"
        "ours_weight_bank_source_pooled_c1_v1_src20.pt"
    )
    c1_bank_sha256: str = (
        "bb3a655606af3b554a8f088bb1d2f3f8d9f190b0911a812fd3755d3de3216b9d"
    )

    # Strong compact source training: exactly the frozen PT source recipe.
    source_epochs: int = 50
    source_lr: float = 1e-3
    source_batch_size: int = 64
    source_weight_decay: float = 0.0

    # Common target adaptation for every initialization and architecture.
    target_steps: int = 50
    target_lr: float = 1e-2
    target_grad_clip: float = 1.0

    # Frozen before opening the C3-1 Check split.
    switch_margin_rel: float = 0.01

    bootstrap_repeats: int = 4000
    eps: float = 1e-12

    # Stop / proceed gates.
    primary_gain_mean: float = 0.03
    primary_gain_ci_low: float = 0.0
    harmful_switch_rate_max: float = 0.05
    architecture_increment_mean: float = 0.03
    architecture_increment_ci_low: float = 0.0
    oracle_headroom_mean: float = 0.05
    oracle_headroom_ci_low: float = 0.0

    # Includes source/development/final pools and C3-0 diagnostic pool.
    known_used_center_ranges: Tuple[Tuple[int, int], ...] = (
        (0, 219),
        (420, 839),
        (900, 919),
    )


CFG = SourcePriorBankConfig()


def config_dict() -> Dict[str, object]:
    return asdict(CFG)
