# Complexity-Constrained Few-Shot Digital Twin Model Instantiation

This repository is the reproducibility archive for **Complexity-Constrained
Few-Shot Digital Twin Model Instantiation for Heterogeneous Multi-Center
Computing Networks**. Release `v1.1.7` synchronizes the manuscript, captions,
Fig. 1--12, plot-ready data, frozen protocols, audit evidence, and public
reproduction commands.

## What is frozen

The following scientific choices are unchanged in v1.1.7:

- data seed `2904` and source-training seeds `2904`, `2905`, `2906`;
- source, development, diagnostic, and held-out target splits;
- six retained architectures and seven initialized candidates;
- reference candidate (internal architecture index `57`);
- SGD/MSE target adaptation with exactly 50 updates and learning rate `0.01`;
- the preset 10% reference-based selection threshold;
- the optimizer, candidate bank, complexity limits, and all reported values.

The main evaluation contains 80 held-out cases. RCF-DTI selects an alternative
in 47 cases: 44 beneficial and 3 harmful under the post-selection test-MSE
audit; the reference is retained in 33 cases. These test-derived labels are
used only for reporting and never for candidate selection.

## Repository map

- `paper/`: compilable manuscript source, final PDF, tables, and Fig. 1--12.
- `paper_assets/current_figures/`: checksum-bound final Fig. 1--5 assets.
- `reporting/final_figures.py`: the only maintained Fig. 6--12 implementation.
- `results/figure_data/`: reviewer-ready CSV data for every table and
  data-driven figure.
- `configs/`, `core/`, `experiments/`: frozen protocol and experiment code.
- `results/audited_provenance/`: publishable immutable audit records.
- `scripts/`: verification, reconstruction, smoke-test, and replay commands.
- `docs/`: method, figure, provenance, availability, and reproducibility notes.
- `audit/v1.1.7/`: machine-readable and human-readable release audit evidence.

Historical internal identifiers remain only where changing them would break
the provenance chain. Their public meaning is documented in
`docs/INTERNAL_PROVENANCE_NAMES.md`; archived plotting code lives under
`reporting/legacy/` and is not a paper-figure entry point.

## Installation

Python 3.11 is the reference environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

The equivalent Conda environment is in `environment.yml`.

## Verify the repository

```powershell
python .\scripts\verify_repository.py
python -m pytest
python .\scripts\run_smoke_test.py
```

The repository audit checks frozen protocol fields, main numerical
relationships, test-set isolation, plot-ready data, checksums, imports,
version metadata, terminology, absolute paths, and privacy-sensitive strings.
The CPU smoke test does not use archived weights and does not change the
frozen experiment.

## Rebuild all paper outputs

There is one formal Level-B entry point:

```powershell
python .\scripts\generate_paper_outputs.py
```

It checksum-copies final Fig. 1--5 and regenerates Fig. 6--12 from
`results/figure_data/`. No training, selection, adaptation, bootstrap
resampling, private paths, model weights, or Alibaba raw data are required.
Generated data figures include vector PDF, 600-DPI PNG, grayscale previews,
layout audits, source hashes, and an output manifest.

The output tree is:

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

See `docs/FIGURE_REPRODUCTION.md` for the source-to-figure map and acceptance
checks. `scripts/plot_reproducible_figures.py` is retained only as a deprecated
compatibility wrapper; it calls the same canonical implementation.

## Reproducibility levels

- **Level A — repository verification:** CPU-only structural, numerical,
  protocol, leakage, terminology, privacy, and checksum checks.
- **Level B — paper reconstruction:** all tables and Fig. 1--12 from released
  files, without weights or raw Alibaba data.
- **Level C — locked evaluation replay:** the seven frozen methods from the
  checksum-bound bootstrap assets in Release `v1.1.7`, requiring CUDA.

For Level C, first verify and stage the downloaded bundle:

```powershell
python .\scripts\stage_level_c_bootstrap.py `
  --bundle-root <extracted-bundle-directory> --verify-only
python .\scripts\run_full_reproduction.py `
  --bootstrap-dir <extracted-bundle-directory> --plan-only
```

Then run either the CUDA path check or the complete locked replay:

```powershell
python .\scripts\run_full_reproduction.py `
  --bootstrap-dir <extracted-bundle-directory> --smoke
python .\scripts\run_full_reproduction.py `
  --bootstrap-dir <extracted-bundle-directory>
```

The replay uses frozen source-trained weights and does not retrain the source
bank. Its environment-dependent per-case wall-clock fields are distinct from
the manuscript's separate five-repeat, GPU-synchronized timing protocol.

## Data availability

Synthetic centers can be regenerated from `core/data/sim.py`, the frozen
configuration, and fixed seeds. Plot-ready table and figure data are tracked
in `results/figure_data/`, including all 320 case-level gains for Fig. 12(b).

The original Alibaba Cluster Trace v2018 is not redistributed. Its official
source, expected checksum and layout, preprocessing, real-bank construction,
and evaluation instructions are in `data/alibaba2018/README.md`. Released
Alibaba-derived records contain anonymized identifiers and processed
evaluation values only.

## Citation and release integrity

Use `CITATION.cff` and Release
[`v1.1.7`](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/v1.1.7).
Every release asset is covered by `SHA256SUMS.txt`; the audit report records
the Git commit, annotated tag target, release state, and asset hashes.
Author and DOI metadata remain explicitly pending.

The code is released under the MIT License.
