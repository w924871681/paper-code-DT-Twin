# /new_exercise/cfg/methods/medet_cfg.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Tuple


@dataclass
class MeDeTCfg:
    """
    MeDeT-style baseline (paper-faithful):
      - fixed backbone (no arch search)
      - MAML/FOMAML meta-training on meta-train taskset
      - few-shot adaptation on each meta-test task

    Our scenario adaptation:
      - regression loss (mse/mae), keep bi-level structure unchanged
      - enforce hard budget gate as deployability protocol
      - crucial: enable within-type vs cross-type evaluation to expose MeDeT limitation
    """
    name: str = "MeDeTStyle"

    # ---- Fixed backbone from A_base ----
    fixed_arch_key: str = "TCN_B3_C32_K3_Dil1"

    # ---- Meta-learning algorithm ----
    meta_algo: Literal["maml"] = "maml"
    first_order: bool = True          # True=FOMAML (recommended), False=2nd-order MAML
    meta_iters: int = 400
    meta_batch_tasks: int = 8

    outer_lr: float = 1e-3
    weight_decay: float = 0.0
    grad_clip: float = 1.0

    # ---- Inner-loop during meta-train ----
    inner_steps: int = 5
    inner_lr: float = 1e-2
    inner_batch_size: int = 16

    # ---- Few-shot adaptation on meta-test ----
    adapt_steps: int = 50             # align with protocol Tadapt=50
    adapt_lr: float = 1e-2
    adapt_batch_size: int = 16

    loss: Literal["mse", "mae"] = "mse"

    # ---- Budget protocol ----
    enforce_hard_budget: bool = True

    # ---- Key setting to reproduce MeDeT limitation ----
    # meta-train only on same-type tasks; evaluate both in-type and cross-type
    meta_train_types: Tuple[str, ...] = ("A",)
    meta_test_in_types: Tuple[str, ...] = ("A",)
    meta_test_out_types: Tuple[str, ...] = ("B", "C")

    # ---- Runtime ----
    seed: int = 2026
    device: str = "cuda"
    use_amp: bool = False
    torch_compile: bool = False
    smoke_max_centers: int = 6

    def validate_against_main(self, main_cfg) -> None:
        assert main_cfg.arch.total_size() == 66
        if main_cfg.budget.hard_filter:
            assert self.enforce_hard_budget, "MainCfg.budget.hard_filter=True requires enforce_hard_budget=True"
        # sanity for types
        for t in self.meta_train_types + self.meta_test_in_types + self.meta_test_out_types:
            assert t in ("A", "B", "C"), f"Unknown center type '{t}'"
