# Complexity-Constrained Few-Shot Digital Twin Model Instantiation for Heterogeneous Multi-Center Computing Networks

## 1. Paper and scope

This repository releases the code, frozen configurations, processed result
tables, and reproducibility utilities for the paper **Complexity-Constrained
Few-Shot Digital Twin Model Instantiation for Heterogeneous Multi-Center
Computing Networks**.

The task is to instantiate a target-specific digital twin model for a new or
reconfigured computing center. The center supplies few target observations and
sets local model complexity limits. Estimated operation count represents
inference computation, and parameter count represents model size; neither is a
direct measurement of latency, memory use, or energy consumption. Workload
prediction is used only as the evaluation task.

## 2. Method overview

```text
Source-initialization bank
-> filtering by target model complexity limits
-> common few-shot target adaptation
-> reference-based candidate selection
-> target-specific digital twin model
```

Each candidate couples an architecture with its matched source-trained
initialization. Candidates that exceed either target limit are removed. The
remaining feasible candidates use the same target data and adaptation
procedure. An alternative replaces the fixed reference candidate only when it
passes the reference-based improvement test.

## 3. Repository layout

- `core/`: synthetic data, architecture models, complexity profiling, and
  adaptation utilities.
- `configs/`: frozen public configurations.
- `experiments/`: locked main, robustness, and supplementary protocols.
- `reporting/`: table and figure reconstruction from released frozen results.
- `results/`: frozen results, immutable provenance where publishable, and
  checksum-tracked sanitized or narrowly corrected public copies.
- `scripts/`: verification, reconstruction, smoke-test, and full-run entry
  points.
- `assets/`: model-asset manifest and checksum instructions.
- `paper_assets/`: checksum-pinned unchanged paper-figure assets.
- `data/`: synthetic-data and Alibaba Cluster Trace instructions.
- `source_prior_bank/` and `anchor_safe_selector/`: historical internal module
  paths retained so archived experiments remain import-compatible.

Some immutable audit files, frozen source schemas, and internal implementation
identifiers retain historical experiment names for reproducibility. They are
not the public terminology used in the paper. See `results/README.md`.

## 4. Frozen protocol

- Data seed: `2904`.
- Source-initialization training seeds: `2904`, `2905`, and `2906`.
- Prediction horizons: `H in {1, 4}`.
- Support sizes: `K in {10, 20}`.
- Common target adaptation: SGD/MSE, 50 steps, learning rate `0.01`.
- Reference candidate: internal architecture index `57`.
- Reference-based improvement test: frozen `10%` validation-loss margin.
- Locked main evaluation centers: `980--999`.
- Adaptation-trajectory centers: `1080--1099`.
- Optimizer-matched-control centers: `1100--1119`.

These settings are frozen. The released scripts do not retune the candidate
bank, target updates, selection margin, seeds, or data splits.

## 5. Installation

Python 3.11 is the reference environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

For repository tests, install the optional test dependency:

```powershell
python -m pip install -e ".[test]"
```

The equivalent Conda specification is provided in `environment.yml`.

## 6. Reproducibility levels

- **Level A -- Repository verification:** checks imports, required frozen
  files, JSON/config structure, original and public-copy checksums, public
  terminology, privacy rules, and numerical consistency. It does not require
  model weights.
- **Level B -- Rebuild paper tables and figures:** uses only released
  repository files. It regenerates eight code-native figures, including
  Fig. 6, Fig. 8, and Fig. 9 from their public derived CSVs, and
  checksum-verifies and copies the four unchanged Fig. 2--5 PDFs,
  rebuilds the exact structured data for revised-manuscript Tables 1--6, and
  rebuilds the broader fifteen-table public result layer. It requires neither
  model weights nor Alibaba raw data.
- **Level C -- Full training and evaluation:** requires a CUDA-capable GPU,
  archived model assets, substantial runtime, and the original Alibaba trace.
  The public package currently exposes prerequisite validation and individual
  stages but not a released end-to-end orchestration driver.

## 7. Quick verification

From the repository root:

```powershell
python .\scripts\verify_repository.py
python .\scripts\run_smoke_test.py
```

The smoke test runs on CPU without archived weights. It builds feasible and
infeasible candidates, applies two common target-adaptation steps, executes the
reference-based improvement test, and checks that the selected candidate
satisfies both complexity limits.

## 8. Rebuild tables and figures

```powershell
python .\scripts\generate_paper_outputs.py --help
python .\scripts\generate_paper_outputs.py
```

The default output directory is `outputs/paper_outputs`. The command rebuilds
the code-native scenario schematic, source-center-scale line plot,
accuracy--complexity 3D scatter, target robustness radar plot, and
generalization forest plot. It also rebuilds Fig. 6, Fig. 8, and Fig. 9 from
the six versioned CSVs under `results/figure_data/`. Each data-driven figure
has public source data, and all eight generated figures receive vector-PDF,
600-DPI PNG, grayscale, and layout checks. Fig. 2--5 are checksum-verified and
copied from `paper_assets/legacy_figures/`, yielding the complete 12-figure
set cited by the revised paper.

To rebuild only Fig. 6, Fig. 8, and Fig. 9:

```powershell
python .\scripts\plot_reproducible_figures.py
```

The revised manuscript's exact Table 1--6 data are written under
`tables/paper_csv/` and `tables/paper_latex/`; this includes the
optimizer-matched control in Table 6. The broader checked public tables are
written under `tables/csv/` and `tables/latex/`.

## 9. Full experiment reproduction

First verify the archived model files:

```powershell
python .\scripts\verify_assets.py --asset-dir <path>
python .\scripts\run_full_reproduction.py --asset-dir <path> --plan-only
python .\scripts\run_full_reproduction.py --asset-dir <path> `
  --alibaba-archive .\data\alibaba2018\raw\machine_usage.tar.gz
```

The permanent model-asset archive URL and public end-to-end driver are not yet
available. Consequently, this repository does not claim Level C from a fresh
clone. `--plan-only` validates supplied assets and writes a non-executing plan.
Without `--plan-only`, the wrapper requires the exact Alibaba archive and an
available CUDA device, then returns an explicit blocked status while the public
driver is unavailable; it never reports that training ran when it did not.

The exact remaining bootstrap contents, orchestration stages, and acceptance
criteria are listed in `docs/LEVEL_C_COMPLETION_PLAN.md`.

## 10. Model assets

Large weights are not stored in ordinary Git history. Expected filenames and
SHA-256 values are listed in `assets/model_assets.csv`. See
`assets/README.md` for the expected directory tree and verification behavior.
Until a permanent archive URL is published, Level C remains externally
blocked.

## 11. Synthetic data

Synthetic centers are generated by `core/data/sim.py` from frozen code,
configurations, and seeds. The public split summary is
`data/synthetic/split_manifest.json`. The smoke test uses a smaller independent
synthetic center and never changes the frozen main experiment.

## 12. Alibaba Cluster Trace

The original Alibaba Cluster Trace v2018 is not redistributed. The released
experiment uses real `machine_usage` observations and deterministic
semi-synthetic model-complexity-limit tiers. Download, checksum,
preprocessing, real-bank construction, and evaluation instructions are in
`data/alibaba2018/README.md`.

## 13. Expected outputs

Level A prints `PASS_PUBLIC_REPOSITORY_VERIFICATION`. Level B creates:

```text
outputs/paper_outputs/
|-- figures/
|-- figure_data/
|-- tables/csv/
|-- tables/latex/
|-- tables/paper_csv/
|-- tables/paper_latex/
|-- paper_output_validation.json
`-- paper_outputs_manifest.json
```

Generated outputs and checkpoints are ignored by Git. Level C writes only
below `outputs/full_reproduction/` unless an explicit output directory is
supplied.

## 14. Citation

Use the release metadata in `CITATION.cff`. The source repository is
`https://github.com/w924871681/paper-code-DT-Twin`. Releases `v1.1.0` and
`v1.1.1` record the public revision workflow; author and DOI metadata remain
pending.

## 15. License

The repository code is released under the MIT License. See `LICENSE`.
