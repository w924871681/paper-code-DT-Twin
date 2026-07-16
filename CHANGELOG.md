# Changelog

All notable public changes to this repository are documented here. Release
dates are recorded only after a version is actually published.

## [Unreleased]

- Replace the anonymous author placeholder, add the paper DOI, and add the
  release date once the publication metadata are final.
- Publish a permanent archive URL for the checksum-tracked model assets and a
  public end-to-end training/evaluation driver before claiming Level C
  reproduction from a fresh clone.

## [1.1.0] - planned

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
  the official repository URL, and a planned v1.1.0 citation record.
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
