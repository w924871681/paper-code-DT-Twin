# -*- coding: utf-8 -*-
"""Fixed protocol for the recovered H-Meta-NAS baseline.

This is a separate experiment, not part of the already frozen C3-3 replay.
All choices below were fixed before opening the C3-3 held-out test labels.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class HMetaNasConfig:
    protocol_version: str = "h_meta_nas_recovery_v1"
    data_seed: int = 2904
    train_seed: int = 2904
    source_centers: int = 20
    locked_pool: Tuple[int, int, int] = (980, 20, 220000)
    H_list: Tuple[int, ...] = (1, 4)
    K_list: Tuple[int, ...] = (10, 20)
    architecture_count: int = 66

    # First-order MAML over source-center tasks.  Every architecture has its
    # own meta-initialization because the released search space combines MLP,
    # TCN, and GRU models with incompatible parameter tensors.
    source_outer_iterations: int = 240
    source_architectures_per_task: int = 12
    source_inner_steps: int = 5
    source_inner_lr: float = 1e-2
    source_meta_lr: float = 1e-3

    # H-Meta-NAS evolutionary target search: two generations of six feasible
    # architectures.  This fixes the 12 adapted-candidate budget to match the
    # other target-side search baselines.
    population_size: int = 6
    generations: int = 2
    parent_count: int = 3
    target_steps: int = 50
    target_lr: float = 1e-2
    target_grad_clip: float = 1.0

    output_root: str = "outputs/h_meta_nas_recovery_v1"


CFG = HMetaNasConfig()


def config_dict() -> Dict[str, object]:
    return asdict(CFG)
