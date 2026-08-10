# Final MSA-DTI synchronization audit

## Scope and parity

This audit covers the public reproducibility package at the audited release
commit. `origin/main` was used as the baseline; the prior local v1.1.5 branch
was not used as a publication source. The repository contains the current
implementation, frozen configurations, deterministic split manifest, public
processed results, figure/table reporting code, reproducibility entry points,
and protocol tests required by the manuscript and supplementary material.

| Paper evidence | Public implementation / record |
| --- | --- |
| Candidate bank and 66 / 6 / 5 / 7 terminology | `configs/methods/candidate_space_cfg.py`, `core/space/`, `results/audited_provenance/` |
| Deployment limits and feasibility filtering | `core/space/profile.py`, `core/methods/ours/condition.py` |
| Target adaptation and reference-margin selection | `main_evaluation/pipeline.py` (`_fixed_target_adapt` and the frozen reference-margin candidate-selection path), `configs/methods/main_evaluation_cfg.py` |
| Main held-out evaluation and baselines | `experiments/main/`, `main_evaluation/`, `scripts/run_main_evaluation_method.py` |
| Diagnostics, dual-limit stress, source sensitivity, and profiling | `experiments/supplementary/`, `experiments/robustness/`, `scripts/run_*` |
| Alibaba transfer without restricted raw data | `scripts/prepare_alibaba2018_trace.py`, `scripts/run_alibaba2018_evaluation.py`, `data/alibaba2018/README.md` |
| Tables, figures, and public result data | `results/figure_data/`, `reporting/`, `scripts/plot_reproducible_figures.py` |
| Repository and smoke verification | `scripts/verify_repository.py`, `scripts/run_smoke_test.py`, `tests/` |

## Classification

### Canonical target-side implementation note

The current MSA-DTI held-out protocol uses the SGD/MSE 50-update target
adaptation and frozen reference-margin candidate-selection implementation in
`main_evaluation/pipeline.py`, with frozen values defined in
`configs/methods/main_evaluation_cfg.py`.

`core/methods/ours/adapt.py` and
`core/methods/ours/c23_mode_selector.py` contain historical or
general-purpose adaptation components retained for reproducibility and
compatibility. They are not the canonical implementation of the current
MSA-DTI held-out SGD/MSE and reference-margin selection protocol.

- **Class R:** tracked source, configuration, scripts, tests, public processed
  results, manuscript sources, final PDFs, figures, and documentation.
- **Class A:** optional bootstrap/checkpoint bundles are release-only; their
  checksums and acquisition instructions remain public.
- **Class L:** caches, virtual environments, LaTeX intermediates, and local
  run outputs are ignored.
- **Class S:** Alibaba raw/processed local data and all model checkpoints are
  excluded by `.gitignore`; only portable preprocessing/evaluation code and
  availability documentation are published.

## Scientific freeze

No experimental result, protocol, split, seed, baseline, candidate bank,
margin, deployment limit, or reported scientific value was changed. This
release changes public naming, source packaging, and figure labels only.

## Release rule

The release tag is created only after this commit is fast-forwarded to
`main`; the tag and GitHub Release must point to this same audited commit.
