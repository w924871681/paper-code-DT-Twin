# -*- coding: utf-8 -*-
"""Frozen configuration for the pre-submission enhancement experiments.

This module is intentionally separate from the frozen main-paper configs.
The experiments below must not overwrite the locked C3-3 results.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class PreSubmissionEnhancementsCfg:
    protocol_version: str = "pre_submission_enhancements_v1_0"
    data_seed: int = 2904
    train_seed: int = 2904
    H_list: Tuple[int, ...] = (1, 4)
    K_list: Tuple[int, ...] = (10, 20)
    compact_arch_indices: Tuple[int, ...] = (1, 6, 13, 55, 56, 57)
    compact_non_anchor_indices: Tuple[int, ...] = (1, 6, 13, 55, 56)
    anchor_arch_idx: int = 57

    # Frozen main selector used as the no-recalibration external control.
    frozen_margin_rel: float = 0.10
    threshold_grid: Tuple[float, ...] = (0.05, 0.075, 0.10, 0.125, 0.15, 0.20)
    allowed_harmful_rate: float = 0.05
    minimum_mean_gain: float = 0.0
    require_positive_ci_low: bool = True
    bootstrap_repeats: int = 4000
    eps: float = 1e-12

    # Alibaba split. All three machine groups are mutually disjoint.
    alibaba_source_machines: int = 20
    alibaba_calibration_machines: int = 20
    alibaba_target_machines: int = 40
    alibaba_min_points: int = 820
    alibaba_max_points_per_machine: int = 1200
    alibaba_source_windows_per_machine: int = 100
    alibaba_source_epochs: int = 50
    alibaba_source_lr: float = 1e-3
    alibaba_source_batch_size: int = 64
    alibaba_source_weight_decay: float = 0.0
    alibaba_expected_archive_sha256: str = (
        "3e6ee87fd204bb85b9e234c5c75a5096580fdabc8f085b224033080090753a7a"
    )

    # Target adaptation is unchanged from the frozen main method.
    target_steps: int = 50
    target_lr: float = 1e-2
    target_grad_clip: float = 1.0

    # Hosting-profile protocol.
    hosting_warmups: int = 100
    hosting_timed_inferences: int = 1000
    hosting_repeats: int = 5
    hosting_batch_size: int = 1
    hosting_profile_center_id: int = 980
    hosting_profile_support_size: int = 10

    # Frozen model assets used by the hosting experiment.
    strong_bank_manifest_path: str = (
        "outputs/source_prior_bank_d2904_t2904/strong_bank/"
        "c31_strong_bank_manifest.json"
    )
    c1_bank_path: str = (
        "outputs/formal_c1_seed2904/shared_artifacts/"
        "ours_weight_bank_source_pooled_c1_v1_src20.pt"
    )

    output_root: str = "outputs/pre_submission_enhancements_d2904_t2904"


CFG = PreSubmissionEnhancementsCfg()


def config_dict() -> Dict[str, object]:
    return asdict(CFG)
