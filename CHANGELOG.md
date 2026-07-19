# Changelog

All notable public changes to this repository are documented here. Release
dates are recorded only after a version is actually published.

## [Unreleased]

## [1.1.5] - 2026-07-20

- Align the exact manuscript layer to Tables 1--5; keep runtime and model
  complexity in the broader public supplementary layer.
- Synchronize the latest Fig. 1 asset and publish checksum-bound PDF/PNG
  assets for current Fig. 1--5.
- Replace the previous paper-figure mapping with reproducible Fig. 6--12,
  including the current deployment radar, two-dimensional architecture
  complexity--performance map, and exact case-level Fig. 12 distributions.
- Release all 320 Fig. 12 case-level gains and explicitly verify the four
  Alibaba cases below -25%.
- Unify README, Data Availability, citation metadata, release notes, and
  Release assets at v1.1.5 without changing the frozen protocol or core
  reported results.

## [1.1.4] - 2026-07-17

- Prepare v1.1.4 as a public-packaging and privacy patch without changing the
  frozen protocol or reported results.
- Sanitize machine-specific paths from public CUDA evidence, add ZIP privacy
  and checksum verification, and record a main-evaluation code manifest.
- Isolate CUDA smoke and formal output roots so both modes can run in sequence
  without manual cleanup.
- Synchronize repository, manuscript availability, Release, and asset status.

## [1.1.3] - 2026-07-17

- Correct revised-paper Table 4--6 filenames and Level B
  mappings: optimizer-matched control, component ablation, then runtime and
  model complexity.
- Align the Fig. 7 score definition, Fig. 11 averaging description, data
  availability statement, and Level-C status with the final manuscript.
- Extend the release workflow to publish a checksum sidecar and verify the
  uploaded bootstrap by downloading it again.
- Execute the seven-method frozen main-evaluation replay on CUDA, complete the
  formal audit, and archive the ledger, environment, logs, output manifest,
  and historical-output comparison for the v1.1.3 delivery.
- Replace the anonymous author placeholder, add the paper DOI, and add the
  release date once the publication metadata are final.

## [1.1.2] - 2026-07-17

### Added

- A checksum-bound 32-file Level-C bootstrap manifest plus public build and
  staging commands.
- A working frozen locked-main-evaluation driver for all seven methods with a
  resumable machine-readable execution ledger and per-stage log hashes.
- A release bootstrap archive whose staged contents pass the formal frozen
  main-evaluation preflight.

### Clarified

- Existing frozen outputs remain evidence from the actual historical runs.
  The remaining validation item is a new CUDA replay of the published path,
  not proof that the historical results or code were fabricated.

## [1.1.1] - 2026-07-17

### Added

- Public derived CSVs and independent plotting code for Fig. 6, Fig. 8, and
  Fig. 9.
- Pure-vector PDFs, 600-DPI PNGs, grayscale previews, and programmatic layout
  checks for those three reconstructed figures.

### Changed

- Level B now reconstructs eight figures and preserves only Fig. 2--5 as
  checksum-verified historical PDFs.
- Text-integrity checks now canonicalize Git line endings so the same released
  hashes verify on Windows and Linux.

## [1.1.0] - 2026-07-17

### Changed

- Aligned the repository title, terminology, method description, and public
  result labels with the revised manuscript.
- Reorganized the documentation around three explicit reproducibility levels:
  CPU smoke verification (Level A), frozen table/figure reconstruction (Level
  B), and full training/evaluation (Level C).
- Corrected the proposed-method runtime to the repeated synchronized GPU result
  of `5.676 ± 0.059 s`; the earlier one-pass diagnostic is retained only as
  historical provenance.
- Corrected the released source-scale, source-seed, Alibaba, architecture
  coverage, component-analysis, and mechanism summaries at their documented
  source-of-truth boundary. This includes the corrected S6 value `65.42`, the
  neutral retained-reference handling for C33, the check-set label for S5, the
  S7/S8 public labels, harmful-selection denominators, and the completed Table
  4 configuration label.
- Documented the Alibaba Cluster Trace v2018 checksum, portable preprocessing
  paths, real source-bank construction, and the boundary between real workload
  observations and deterministic semi-synthetic complexity-limit tiers.
- Replaced incomplete licensing and citation metadata with the full MIT text,
  the official repository URL and a v1.1.0 citation record.
- Documented the model-asset manifest and verification workflow without
  committing large weights to ordinary Git history.

### Added

- CPU smoke, repository verification, asset verification, Alibaba bank-build,
  full-reproduction wrapper, and frozen paper-output entry points.
- A frozen reporting workflow that produces the revised paper's complete set
  of 12 PDF figures: five code-generated or redesigned figures and seven
  checksum-verified unchanged assets.
- Exact manuscript Table 1--6 exports in CSV and LaTeX, including the
  optimizer-matched control, plus a broader checked 15-table public layer.
- Companion CSV data for data-driven figures, grayscale/layout checks, raster
  audits, and a generated-file manifest.
- Automated repository, numerical-consistency, reproducibility, and CI checks.
- Public method, data-availability, reproducibility, paper-result mapping,
  model-asset, result-provenance, and release documentation.

### Known external prerequisite

Level C is intentionally reported as blocked: a permanent public model-asset
archive URL and the public end-to-end experiment driver are not yet available.
Level A and Level B do not depend on those assets.

## [1.0.0] - 2026-07-03

- Initial public repository snapshot associated with the manuscript.
