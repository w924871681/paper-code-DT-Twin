# Changelog

All notable public changes to this repository are documented here. Release
dates are recorded only after a version is actually published.

## [Unreleased]

## [1.1.9] - 2026-07-23

- Adopt the latest supplied journal manuscript revision, including the revised
  abstract, Introduction, method exposition, captions, analysis, conclusion,
  citation numbering, and v1.1.9 Data Availability statement.
- Redraw Fig. 10 with explicit `Target-side time`, `Parameter count`, and
  `Estimated operation count` labels while preserving the released raw data
  and `100 × lowest raw value / method value` normalization.
- Update the single maintained Fig. 6--12 implementation, audit evidence,
  metadata, documentation, and release packaging without changing any frozen
  experimental protocol or reported result.

## [1.1.8] - 2026-07-23

- Include the exact `paper/tables/` assets in the standalone final figure-code
  package so its documented reconstruction command runs after independent ZIP
  extraction.
- Add a repository check that prevents the standalone package dependency from
  being omitted again.
- Advance the journal manuscript, Data Availability, metadata, audits, Latest
  Release, and asset names without changing code paths, protocol settings, or
  experimental values.

## [1.1.7] - 2026-07-23

- Replace the archived manuscript source with the current journal draft,
  including its revised abstract, Introduction, Related Work, proposed-method
  presentation, algorithm, conclusion, and Data Availability statement.
- Synchronize the exact current Table 1--5 LaTeX assets and use `MSE` in the
  formal manuscript layer while retaining documented historical schema names.
- Remove the two uncited bibliography entries and verify one-to-one agreement
  between citation keys and bibliography items.
- Update version metadata, repository audits, release packaging, and
  manuscript/PDF checks without changing any frozen experiment setting or
  reported numerical value.

## [1.1.6] - 2026-07-23

- Synchronize the final manuscript source/PDF, captions, Data Availability,
  and checksum-bound Fig. 1--5 assets.
- Consolidate Fig. 6--12 into `reporting/final_figures.py` with one formal
  reviewer command and plot-ready CSV inputs.
- Align figure terminology, panel-label placement, 50-update wording,
  trade-off normalization, architecture labels, and Alibaba clipping
  disclosure without changing experimental values.
- Add protocol, key-number, test-leakage, duplicate implementation,
  terminology, absolute-path, privacy, manuscript, and release audits.
- Publish the paper, complete figure/table package, frozen evidence, audit
  reports, and SHA-256 manifest in Release v1.1.6.

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
