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
- **Level C -- Frozen locked-evaluation replay:** uses the published 32-file
  bootstrap package and a CUDA-capable PyTorch environment. The public driver
  stages the frozen assets, runs all seven methods, analyzes the results, and
  executes the formal audit. Repeating the separate Alibaba study additionally
  requires its original trace.

Status: The reported CUDA experiments and their frozen outputs are complete.
The public bootstrap, staging process, formal preflight, and orchestration
driver are also complete. A fresh CUDA replay through the published public
entry point has also been completed. Its ledger and formal audit outputs are
archived in the local v1.1.3 delivery and prepared for authorized Release
publication.

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
`tables/paper_csv/` and `tables/paper_latex/`. Table 4 is the
optimizer-matched control, Table 5 is the component ablation, and Table 6 is
target-side runtime and model complexity. The broader checked public tables
are written under `tables/csv/` and `tables/latex/`.

## 9. Full experiment reproduction

Download and extract the v1.1.2 bootstrap asset documented in
`assets/README.md`, then verify the package and plan without running models:

```powershell
python .\scripts\stage_level_c_bootstrap.py `
  --bundle-root <extracted-bundle-directory> --verify-only
python .\scripts\run_full_reproduction.py `
  --bootstrap-dir <extracted-bundle-directory> --plan-only
```

For a CUDA path check or the complete frozen locked evaluation:

```powershell
python .\scripts\run_full_reproduction.py `
  --bootstrap-dir <extracted-bundle-directory> --smoke
python .\scripts\run_full_reproduction.py `
  --bootstrap-dir <extracted-bundle-directory>
```

The released package passed all checksum checks and the formal locked
preflight. A fresh seven-method CUDA replay through the public driver completed
with ledger decision `PASS_FROZEN_MAIN_EVALUATION_REPLAY`; the formal audit
returned `PASS_C33_LOCKED_EVALUATION_COMPLETE_AND_AUDITED`. All non-timing
case records and reported metrics matched the historical frozen outputs.
Source training was not repeated by this evaluation replay.

The exact remaining bootstrap contents, orchestration stages, and acceptance
criteria are listed in `docs/LEVEL_C_COMPLETION_PLAN.md`.

## 10. Model assets

Large weights are not stored in ordinary Git history. The published bootstrap
archive, exact SHA-256, complete 32-file destination manifest, and staging
commands are documented in `assets/README.md`.

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

Generated outputs and checkpoints are ignored by Git. The Level-C driver
writes its ledger and logs below `outputs/full_reproduction/`; frozen method
outputs retain the repository paths required by the formal audit.

## 14. Citation

Use the release metadata in `CITATION.cff`. The source repository is
`https://github.com/w924871681/paper-code-DT-Twin`. Releases `v1.1.0`,
`v1.1.1`, and `v1.1.2` record the published revision and reproducibility
workflow. The local v1.1.3 preparation is not a published release until its
tag and Release are explicitly authorized. Author and DOI metadata remain
pending.

## 15. License

The repository code is released under the MIT License. See `LICENSE`.
