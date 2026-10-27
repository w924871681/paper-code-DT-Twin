# Experiment code and source checkpoint archive

This directory contains materials linked to the v1.3.0 paper and does not change
its experimental results. The original execution code is kept as a historical
snapshot with source paths and environment assumptions; it is not advertised as
a tested one-command pipeline. Do not run historic controllers against their
original result directories. Raw Bitbrains traces are obtained separately.

## Included in the source package

- `checkpoints/`: the paper's seven source-trained candidates, one checkpoint
  per horizon (14 files). Their byte hashes match `data/source_checkpoint_identities.json`.
- `historical/baselines/`: the actual seven-baseline prefix worker and the
  extracted native main- and hardware-aware search functions. Its historical
  absolute paths and frozen protocol checks are preserved; the file requires
  path and environment mapping before rerunning.
- `historical/features/`: the feature, adaptation, and seed implementations.
  `prefix_common.py` is a function-level extraction from the shared prefix module;
  it is provided for review and is not an unchanged complete runner.
- `historical/source_training/`: source-only training scripts for the 66 C1
  candidates, MeDeT-style initialization, hardware-aware meta-initialization,
  and ranking teacher. Their path assumptions are preserved.
- `historical/code/`: model space, shared utilities, configuration, synthetic
  data generator and bank-construction code needed to inspect the workflow.
- `historical/evaluation/` and `historical/selection/`: selected scoring and
  policy code snapshots. The separately maintained `selection/replay_selection.py`
  replays saved-score decisions using the current A55 reference and tau = 0.05.
- `MANIFEST.json`: hashes of included source and checkpoint files.

The seven baselines are PT+FT, MeDeT-style, Scratch50, Meta+NAS-lite,
Zero-shot NAS, Zero-shot NAS+FT, and H-Meta-NAS-based. The source snapshots
are the task-matched implementations used by this study, not claims of full
replication of the papers that motivated the baselines.

## Additional assets in the same GitHub Release

`MSA_DTI_v1.3.0_baseline_source_assets.zip` contains 132 C1 states
(66 architectures for each horizon), two MeDeT states, the H-Meta-NAS
source object, and the source-only `pi50` teacher ranking. All 136 asset hashes
match the retained source records. PT+FT uses the paper's A57-PT checkpoints
in `checkpoints/`; Scratch50 uses its recorded random initialization rule.

`MSA_DTI_v1.3.0_preselection_initializations.zip` contains the frozen
synthetic C1 preliminary bank and the two A57 preliminary source checkpoints.
Their SHA-256 values match the historical bank configuration and source
manifest. These synthetic preliminary weights are distinct from the 14
Bitbrains source-trained checkpoints used for the final candidate bank.

## Preselection provenance and remaining boundary

The frozen bank configuration records a selection threshold of two,
architectures 1, 6, 13, 55, 56 and 57, 66 architecture configurations,
source and training seed 2904, and an A57 preliminary reference. The source
simulation and its full parameter defaults are in `historical/code/core/data/sim.py`
and `historical/code/configs/main_cfg.py`. `source_prior_bank_cfg.py` records
that the earlier C3-0 screen used centers 900--919; the later C3-1 fresh pool
(920--939) is a different validation stage and must not be substituted for it.

The original C3-0 per-case oracle/result records and its complete execution
receipt were not found in the archives checked for this release. Therefore the
six selected architectures and the manuscript's counts cannot yet be
independently reconstructed from those preliminary weights and these snapshots
alone. The raw-input full training/evaluation pipeline has not been rerun or
validated in a clean environment. Source-state identity checks and saved-score
selection replay are not equivalent to a full reproduction or an independent
blind evaluation.
