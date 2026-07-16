# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class FinalPaperExperimentsCfg:
    """Frozen final paper experiment protocol.

    This package does not retune the C3-3 method. It runs only the missing
    analyses required by the final paper and then consolidates them with the
    already locked C3-3 external comparison.
    """

    protocol_version: str = "experiments.main_v1_0"
    data_seed: int = 2904
    train_seed: int = 2904
    target_seeds: Tuple[int, ...] = (2904, 2905, 2906)
    H_list: Tuple[int, ...] = (1, 4)
    K_list: Tuple[int, ...] = (10, 20)
    architecture_count: int = 66
    bootstrap_repeats: int = 4000
    eps: float = 1e-12

    # New, disjoint synthetic pools. These are analysis/evaluation only.
    ablation_pool: Tuple[int, int, int] = (1000, 20, 230000)
    seed_pool: Tuple[int, int, int] = (1020, 20, 240000)
    source_scale_pool: Tuple[int, int, int] = (1040, 20, 250000)
    known_used_center_ranges: Tuple[Tuple[int, int], ...] = (
        (0, 219),
        (420, 839),
        (900, 999),
    )

    # Frozen final method.
    anchor_arch_idx: int = 57
    compact_arch_indices: Tuple[int, ...] = (1, 6, 13, 55, 56, 57)
    compact_non_anchor_indices: Tuple[int, ...] = (1, 6, 13, 55, 56)
    frozen_margin_rel: float = 0.10
    target_steps: int = 50
    target_lr: float = 1e-2
    target_grad_clip: float = 1.0

    # Development-derived deterministic candidate order for bank-size study.
    # Size=1 means A57 with PT/C1 dual initializations; later sizes add one
    # strong non-A57 architecture in this frozen order.
    bank_size_order: Tuple[int, ...] = (55, 56, 6, 13, 1)
    bank_sizes: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)

    # Source-scale diagnostic. Source centers are nested prefixes.
    source_scales: Tuple[int, ...] = (10, 20, 30, 40, 50)
    source_epochs: int = 50
    source_lr: float = 1e-3
    source_batch_size: int = 64
    source_weight_decay: float = 0.0

    # Semi-real Alibaba 2018 machine-usage protocol.
    real_source_machines: int = 20
    real_target_machines: int = 20
    real_min_points: int = 820
    real_max_points_per_machine: int = 1200
    real_source_windows_per_machine: int = 100
    real_source_epochs: int = 50
    real_source_lr: float = 1e-3
    real_source_batch_size: int = 64
    real_source_weight_decay: float = 0.0
    real_trace_expected_archive_sha256: str = (
        "3e6ee87fd204bb85b9e234c5c75a5096580fdabc8f085b224033080090753a7a"
    )
    real_trace_download_url: str = (
        "http://aliopentrace.oss-cn-beijing.aliyuncs.com/"
        "v2018Traces/machine_usage.tar.gz"
    )

    output_root: str = "outputs/experiments.main_d2904_t2904"

    # Frozen C3-3 evidence.
    c33_root: str = "outputs/main_evaluation_eval_d2904_t2904"
    c33_analysis_path: str = (
        "outputs/main_evaluation_eval_d2904_t2904/analysis/main_evaluation_analysis.json"
    )
    c33_audit_path: str = (
        "outputs/main_evaluation_eval_d2904_t2904/audit/c33_audit.json"
    )
    c33_ours_path: str = (
        "outputs/main_evaluation_eval_d2904_t2904/methods/ours_c32_locked.json"
    )
    c33_pt_path: str = (
        "outputs/main_evaluation_eval_d2904_t2904/methods/pt_ft.json"
    )
    expected_c33_audit_decision: str = (
        "PASS_C33_LOCKED_EVALUATION_COMPLETE_AND_AUDITED"
    )
    expected_c33_analysis_decision: str = (
        "C33_LOCKED_COMPARISON_COMPLETE_REPORT_AS_OBSERVED"
    )

    # Frozen C3-2 margin evidence.
    anchor_safe_selector_path: str = (
        "outputs/anchor_safe_selector_d2904_t2904/selector/anchor_safe_selector_manifest.json"
    )
    expected_anchor_safe_selector_decision: str = "PASS_C32_SELECTOR_FROZEN"

    # Frozen C3-1 strong bank and legacy C1 bank.
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

    # Frozen external PT/MeDeT source assets.
    external_source_manifest_path: str = (
        "outputs/shared.evaluation_external_d2904_t2904/source_assets/"
        "source_assets_manifest.json"
    )

    # Required final artifacts. The audit checks all of them.
    required_tables: Tuple[str, ...] = (
        "table_baseline_fairness.csv",
        "table_main_results.csv",
        "table_hk_robustness.csv",
        "table_budget_robustness.csv",
        "table_center_type_robustness.csv",
        "table_ablation.csv",
        "table_resource_constraint_ablation.csv",
        "table_seed_robustness.csv",
        "table_real_trace.csv",
        "table_source_scale.csv",
        "table_bank_size.csv",
        "table_oracle_diagnostics.csv",
        "table_mechanism_cost.csv",
    )
    required_figures: Tuple[str, ...] = (
        "fig_paired_ours_vs_pt.pdf",
        "fig_heterogeneous_robustness.pdf",
        "fig_budget_architecture_behavior.pdf",
        "fig_accuracy_online_cost.pdf",
        "fig_margin_safety.pdf",
        "fig_source_scale.pdf",
        "fig_bank_size.pdf",
        "fig_oracle_diagnostics.pdf",
    )


CFG = FinalPaperExperimentsCfg()


def config_dict() -> Dict[str, object]:
    return asdict(CFG)
