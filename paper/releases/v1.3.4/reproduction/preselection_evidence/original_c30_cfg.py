# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class C30Cfg:
    """Frozen C3-0 causal diagnostic. No Test data are materialized."""

    protocol_version: str = "c3_0_fixed_anchor_recipe_and_c1_oracle_v1_0"
    data_seed: int = 2904
    train_seed: int = 2904
    source_centers: int = 20

    # New diagnostic-only target pool; not used by C1/C2/C23/E2E/Pool-K.
    diagnostic_pool: Tuple[int, int, int] = (900, 20, 180000)
    H_list: Tuple[int, ...] = (1, 4)
    K_list: Tuple[int, ...] = (10, 20)
    architecture_count: int = 66
    anchor_arch_idx: int = 57

    output_root: str = "outputs/c30_d2904_t2904"
    final_internal_audit: str = "outputs/final_e2e_c23_d2904_t2904/final/audit/final_e2e_c23_audit.json"
    expected_internal_decision: str = "PASS_FINAL_E2E_C23_COMPLETE_AND_AUDITED"
    external_audit: str = "outputs/final_e2e_c23_external_d2904_t2904/audit/external_baseline_audit.json"
    expected_external_decision: str = "PASS_FINAL_E2E_C23_EXTERNAL_BASELINES_COMPLETE_AND_AUDITED"
    external_source_manifest: str = "outputs/final_e2e_c23_external_d2904_t2904/source_assets/source_assets_manifest.json"
    expected_source_decision: str = "PASS_EXTERNAL_SOURCE_ASSETS_FROZEN"

    c1_bank_path: str = "outputs/formal_c1_seed2904/shared_artifacts/ours_weight_bank_source_pooled_c1_v1_src20.pt"
    c1_bank_sha256: str = "bb3a655606af3b554a8f088bb1d2f3f8d9f190b0911a812fd3755d3de3216b9d"

    # D1/D2 strong fixed-target recipe, inherited from frozen PT+FT baseline.
    sgd_steps: int = 50
    sgd_lr: float = 1e-2
    sgd_grad_clip: float = 1.0

    # D3/D4 current C2.3 STD50 recipe.
    huber_steps: int = 50
    huber_lr: float = 3e-4
    huber_delta: float = 0.2
    huber_grad_clip: float = 5.0

    bootstrap_repeats: int = 4000
    eps: float = 1e-12

    # Diagnostic interpretation thresholds; not method hyperparameters.
    dominant_effect_mean: float = 0.05
    oracle_headroom_mean: float = 0.10
    oracle_headroom_ci_low: float = 0.05
    realizable_headroom_mean: float = 0.03
    realizable_headroom_ci_low: float = 0.0

    known_used_center_ranges: Tuple[Tuple[int, int], ...] = (
        (0, 219),
        (420, 839),
    )


CFG = C30Cfg()


def config_dict() -> Dict[str, object]:
    return asdict(CFG)
