# /new_exercise/cfg/methods/pretrain_ft_cfg.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class PretrainFTCfg:
    """
    Method-specific config: Pretrain + Fine-tune (baseline)
    Core protocol (must NOT drift):
      - Fixed architecture s0 from the SAME A_base (|A|=66).
      - Pooled pretrain on meta-train centers, then K-shot fine-tune on each new center.
      - Must follow MainCfg.task.{L,H_list,K_list,support/val/test ratios} and MainCfg.budget hard gate.

    We lock down the backbone choice to avoid unfair "structure tuning" for a fixed-arch baseline.
    """
    name: str = "PretrainFT"

    # ==========================================================
    # (口径1) Fixed backbone selection: LOCKED
    # ==========================================================
    # selection_mode controls how we bind to A_base:
    # - "by_hparams": match the discrete hyperparams (robust if you keep arch space definition)
    # - "by_key": match arch_key (strong binding to enumerator naming)
    selection_mode: Literal["by_hparams", "by_key"] = "by_hparams"

    # ---- Locked backbone (recommended): TCN_B3_C32_K3_Dil1 ----
    fixed_family: Literal["TCN", "GRU", "MLP"] = "TCN"
    tcn_n_blocks: int = 3
    tcn_channels: int = 32
    tcn_kernel: int = 3
    tcn_dilation: int = 1

    # Optional strong binding: only used when selection_mode="by_key"
    # This must exactly match core/space/enumerator.py naming rule.
    fixed_arch_key: Optional[str] = None  # e.g., "TCN_B3_C32_K3_Dil1"

    # ==========================================================
    # (口径2) Pooled pretraining hyperparams
    # ==========================================================
    pretrain_epochs: int = 50
    pretrain_lr: float = 1e-3
    weight_decay: float = 0.0
    batch_size: int = 64

    # ==========================================================
    # Few-shot fine-tuning on new center (align with Tadapt=50)
    # ==========================================================
    ft_steps: int = 50
    ft_lr: float = 1e-2
    ft_batch_size: int = 16

    # ==========================================================
    # Budget protocol (hard gate)
    # ==========================================================
    enforce_hard_budget: bool = True  # if fixed s0 violates budget -> DT* not deployable

    # Selection criterion inside a new center (for potential checkpointing)
    select_on: Literal["val_mse", "val_mae"] = "val_mse"

    # Implementation knobs
    use_amp: bool = False
    torch_compile: bool = False

    # -------------------------
    # Strict sanity: lock-down protocol alignment
    # -------------------------
    def validate_against_main(self, main_cfg) -> None:
        # task protocol already locked by global sanity_check_protocol()
        assert hasattr(main_cfg, "task") and hasattr(main_cfg, "budget") and hasattr(main_cfg, "arch")

        # must follow hard gate if main uses hard filter
        if getattr(main_cfg.budget, "hard_filter", True):
            assert self.enforce_hard_budget, (
                "MainCfg.budget.hard_filter=True but PretrainFTCfg.enforce_hard_budget=False. "
                "This breaks the deployability protocol."
            )

        # LOCKED backbone rule: we do not allow budget-conditioned backbone switching
        assert self.fixed_family == "TCN", "Baseline backbone is locked to TCN for clean comparison."
        assert (self.tcn_n_blocks, self.tcn_channels, self.tcn_kernel, self.tcn_dilation) == (3, 32, 3, 1), (
            "Baseline backbone hyperparams are locked to (B3,C32,K3,Dil1). "
            "Do not tune baseline backbone."
        )

        if self.selection_mode == "by_key":
            assert isinstance(self.fixed_arch_key, str) and len(self.fixed_arch_key) > 0, (
                "selection_mode='by_key' requires fixed_arch_key."
            )
