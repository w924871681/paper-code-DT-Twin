# Few-Shot Digital Twin Model Instantiation under Resource Constraints

This repository contains the code, frozen configurations, processed result tables,
and lightweight reproducibility evidence for the paper:

**Few-Shot Digital Twin Model Instantiation under Resource Constraints in Heterogeneous Multi-Center Computing Networks**

Workload prediction is used only as an evaluation task. The research target is
few-shot, resource-constrained digital-twin model instantiation.

## Method overview

Architecture-indexed source-prior bank
-> hard resource feasibility
-> fixed 50-step target adaptation
-> PT-A57 anchor-safe selection
-> target-specific digital twin model

## Repository layout

- `core/`: architecture space, data generation, adaptation, and metrics.
- `source_prior_bank/`: compact architecture-indexed source-prior bank.
- `anchor_safe_selector/`: development-calibrated anchor-safe selector.
- `main_evaluation/`: locked multi-method evaluation.
- `experiments/main/`: main experiments and component ablations.
- `experiments/robustness/`: source-scale, source-seed, and semi-real diagnostics.
- `experiments/supplementary/`: adaptation trajectory, anchor-risk, repeated-runtime,
  and optimizer-matched controls.
- `configs/`: frozen public configurations.
- `scripts/`: reproducibility entry points.
- `results/`: processed paper tables and lightweight reproducibility results.

## Frozen protocol

- Data seed: `2904`
- Source-bank seeds: `2904`, `2905`, and `2906`
- Horizons: `H in {1, 4}`
- Support sizes: `K in {10, 20}`
- Target adaptation: SGD/MSE, 50 steps, learning rate 0.01
- Anchor-safe selector: PT-A57 with a frozen 10% validation margin
- Locked main evaluation centers: 980--999
- Adaptation-trajectory centers: 1080--1099
- Optimizer-matched-control centers: 1100--1119

## Quick verification

```powershell
python .\scripts\verify_repository.py
```

## Reproducing paper outputs

```powershell
python .\scripts\generate_paper_outputs.py --help
```

Full training and evaluation require the frozen model assets listed in
`assets/model_assets.csv`. Large weights are distributed through the paper release
or archival repository rather than normal Git history.

## Data availability

Synthetic centers are generated from fixed code and seeds. Alibaba Cluster Trace
2018 is not redistributed in this repository; download and preprocessing instructions
are provided under `data/alibaba2018/`.


## Public release scope

This is the first public release (`v1.0.0`). It uses public method names and excludes internal development identifiers, local paths, raw Alibaba data, model checkpoints, caches, and machine-specific outputs.
