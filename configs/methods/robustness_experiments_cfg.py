# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class FinalPaperExperimentsV2Cfg:
    """Corrected, controlled final-paper diagnostic protocol.

    V2 does not retune the frozen C3 method. It corrects the source-scale
    causal control, evaluates source-bank training-seed robustness, records
    candidate-level semi-real diagnostics, and quantifies architecture
    coverage/leave-one-out contribution.
    """

    protocol_version: str = "experiments.robustness_0"
    data_seed: int = 2904
    target_eval_seed: int = 2904
    source_seeds: Tuple[int, ...] = (2904, 2905, 2906)
    source_scales: Tuple[int, ...] = (10, 20, 30, 40, 50)
    H_list: Tuple[int, ...] = (1, 4)
    K_list: Tuple[int, ...] = (10, 20)
    compact_arch_indices: Tuple[int, ...] = (1, 6, 13, 55, 56, 57)
    anchor_arch_idx: int = 57
    architecture_count: int = 66
    frozen_margin_rel: float = 0.10

    # Equal-compute source training. 2000 updates equal the old scale-20
    # reference: 50 epochs × 20 centers × ceil(100/64)=2000 updates.
    source_count_reference: int = 20
    source_updates_per_asset: int = 2000
    source_batch_size: int = 64
    source_lr: float = 1e-3
    source_weight_decay: float = 0.0
    checkpoint_every_updates: int = 100

    target_steps: int = 50
    target_lr: float = 1e-2
    target_grad_clip: float = 1.0
    bootstrap_repeats: int = 4000
    eps: float = 1e-12

    # Corrected source-scale study replaces the prior result on the same
    # evaluation pool. No hyperparameter is selected from this pool.
    source_scale_pool: Tuple[int, int, int] = (1040, 20, 250000)
    # New untouched pool for source-bank seed robustness.
    source_seed_pool: Tuple[int, int, int] = (1060, 20, 260000)
    known_used_center_ranges: Tuple[Tuple[int, int], ...] = (
        (0, 219), (420, 839), (900, 1059)
    )

    output_root: str = "outputs/experiments.robustness_d2904_t2904"
    old_result_root: str = "outputs/experiments.main_d2904_t2904"
    old_audit_path: str = (
        "outputs/experiments.main_d2904_t2904/audit/final_exp_audit.json"
    )
    old_ablation_path: str = (
        "outputs/experiments.main_d2904_t2904/ablation/ablation_candidates.json"
    )
    old_real_manifest_path: str = (
        "outputs/experiments.main_d2904_t2904/real_trace/processed/real_trace_manifest.json"
    )
    old_real_bank_dir: str = (
        "outputs/experiments.main_d2904_t2904/real_trace/bank"
    )
    anchor_safe_candidates_path: str = (
        "outputs/anchor_safe_selector_d2904_t2904/final/anchor_safe_candidates.json"
    )
    main_evaluation_ours_path: str = (
        "outputs/main_evaluation_eval_d2904_t2904/methods/ours.json"
    )
    main_evaluation_pt_path: str = (
        "outputs/main_evaluation_eval_d2904_t2904/methods/pt_ft.json"
    )

    expected_old_audit_decision: str = (
        "PASS_FINAL_PAPER_EXPERIMENTS_COMPLETE_AND_AUDITED"
    )


CFG2 = FinalPaperExperimentsV2Cfg()


def config_dict() -> Dict[str, object]:
    return asdict(CFG2)
