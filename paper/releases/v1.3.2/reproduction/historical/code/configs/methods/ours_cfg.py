# cfg/methods/ours_cfg.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class OursCfg:
    """Formal source-prior configuration after the fixed-split selection study.

    The shared prior is no longer trained by Reptile.  It uses the empirically
    selected compute-matched pooled source protocol (C1): pooled source
    pretraining followed by 180 pooled supervised refinement updates for every
    (horizon, architecture) entry.  The target-side paper protocol remains the
    common 66-architecture space, 36->12 admission, 50 update steps, one
    restart, and the same hard FLOPs/parameter constraints.
    """

    name: str = "OursPaperAlignedSourcePriorV1"
    runner_version_tag: str = "paper_aligned_source_prior_v1"
    bank_version_tag: str = "source_pooled_c1_v1"
    # The condition controller is retrained because its teacher evaluations
    # depend on the selected source prior.
    control_version_tag: str = "source_pooled_c1_v1"

    # ----- frozen shared source prior (formal C1) -----
    prior_type: str = "source_pooled_c1"
    source_prior_seed: int = 2026
    source_prior_force_retrain: bool = False
    source_prior_resume: bool = True

    # B0 phase used in the method-selection experiment.
    source_pretrain_K: int = 10
    source_pretrain_epochs: int = 10
    source_pretrain_lr: float = 1e-3
    source_pretrain_batch_size: int = 64
    source_pretrain_loss: str = "mse"

    # Compute-matched C1 refinement: 3 epochs x 6 tasks x 10 inner updates.
    source_refine_updates: int = 180
    source_refine_lr: float = 1e-3
    source_refine_batch_schedule: Tuple[int, int] = (10, 20)
    source_refine_loss: str = "huber"
    source_weight_decay: float = 0.0

    # ----- split condition encoders -----
    state_hidden_dim: int = 128
    state_embed_dim: int = 32
    budget_hidden_dim: int = 32
    budget_embed_dim: int = 16
    task_feature_dim: int = 4
    task_hidden_dim: int = 32
    task_embed_dim: int = 16
    condition_dim: int = 64
    condition_hidden_dim: int = 64
    arch_use_task: bool = True
    # The formal condition controller keeps the structural residual free of
    # deployment-budget information.  Budget affects candidate admission via
    # the explicit compatibility score and hard feasible-first rule, while the
    # adaptation controller still receives the deployment budget.
    admission_use_budget_condition: bool = False
    adaptation_use_budget_condition: bool = True

    # ----- global-prior-anchored structural admission -----
    arch_residual_alpha_max: float = 0.35
    arch_residual_alpha_init: float = 0.05
    control_anchor_loss_weight: float = 0.10
    admission_budget_weight: float = 0.35
    admission_budget_score_enable: bool = True
    cand_stage1_k: int = 36
    cand_stage2_k: int = 12
    diversity_admission_enable: bool = True
    stage1_min_per_family: int = 4
    stage2_min_per_family: int = 2
    feasible_first_admission: bool = True

    # ----- legacy meta fields retained only for old diagnostics -----
    # The formal path does not call Reptile when prior_type=source_pooled_c1.
    do_meta_train: bool = False
    meta_epochs: int = 3
    meta_tasks_per_epoch: int = 20
    archs_per_task: int = 12
    inner_steps: int = 5
    inner_lr: float = 1e-3
    meta_step_size: float = 0.20
    meta_seed: int = 2026
    meta_use_all_support_sizes: bool = True

    # ----- offline condition/control learning -----
    control_train_retrain: bool = False
    control_train_centers: int = 0
    control_use_all_support_sizes: bool = True
    control_train_epochs: int = 5
    control_teacher_archs_per_task: int = 12
    control_teacher_adapt_steps: int = 20
    # Structural supervision is based on post-adaptation prediction quality.
    # Hard feasibility is handled by the separate resource-aware admission
    # layer, so the teacher no longer adds an implicit budget penalty.
    control_teacher_feasibility_penalty: float = 0.0
    control_inner_steps: int = 5
    control_lr: float = 5e-4
    control_weight_decay: float = 1e-5
    control_structure_loss_weight: float = 1.0
    control_adaptation_loss_weight: float = 0.25
    control_seed: int = 2026
    control_require_bank_provenance: bool = True

    # ----- target-side condition-modulated adaptation -----
    adapt_steps: int = 50
    adapt_lr: float = 3e-4
    adapt_weight_decay: float = 0.0
    adapt_batch_size: int = 0
    huber_delta: float = 0.2
    modulation_min: float = 0.50
    modulation_max: float = 1.50
    prior_lambda_min: float = 0.0
    prior_lambda_max: float = 1e-3
    max_grad_norm: float = 5.0

    # ----- final feasible decision -----
    selection_mode: str = "validation_first"
    selection_rel_slack: float = 0.005
    selection_abs_slack: float = 1e-8
    dt_star_beta: float = 0.15
    consistency_eta: Tuple[float, float, float] = (
        1.0 / 3.0,
        1.0 / 3.0,
        1.0 / 3.0,
    )

    # ----- artifacts -----
    bank_path: Optional[str] = None
    control_path: Optional[str] = None

    # ----- reproducibility / progress -----
    adapt_seed: int = 2026
    progress_print_every: int = 1

    # ----- ablation-compatible switches -----
    ablation_tag: str = "full"
    condition_ablation_mode: str = "full"
    adapt_condition_scale_enable: bool = True
    cond_prior_mod_enable: bool = True
    feasible_decision_enable: bool = True


CFG = OursCfg()
