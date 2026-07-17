# Release notes: v1.1.0

This release synchronizes the public repository with the revised paper while
keeping the Level C limitation explicit.

## Reproducibility scope

- **Level A -- CPU smoke verification:** exercises candidate construction,
  adaptation, reference-based improvement testing, and complexity-limit checks
  without archived weights.
- **Level B -- frozen paper-output reconstruction:** regenerates or verifies
  the complete paper-output package from released frozen CSV/JSON sources. Two
  independent checked runs produced identical hashes, 12 PDF figures, the
  exact six manuscript tables, and the broader checked table layer.
- **Level C -- full training and evaluation:** remains externally blocked. The
  permanent model-asset URL and the public end-to-end experiment driver are not
  yet available, so this release does not claim fresh-clone Level C
  reproducibility.

## Paper outputs

Level B produces five code-generated or redesigned figures and verifies seven
unchanged legacy PDF assets, for the 12-figure set used by the revised paper.
The revised figures are checked for vector content, 600-DPI PNG rendering,
grayscale readability, and layout. The seven unchanged assets predate this
workflow and have documented raster exceptions; their SHA-256 values are
verified before copying. `fig2.pdf` was normalized for standards-compliant PDF
parsing without a visual-content change, and both hashes are recorded.

The exact revised-manuscript Table 1--6 layer is exported in CSV and LaTeX and
includes the optimizer-matched control in Table 6. A broader checked 15-table
layer is also generated for public inspection. Data-driven figures include
companion CSV files, and all generated files are covered by a manifest.

## Numerical and labeling corrections

- The proposed-method target-side runtime is `5.676 ± 0.059 s`, based on
  repeated synchronized GPU measurements; `15.207 s` is not used as a current
  paper result.
- The Alibaba S6 value is corrected from `56.18` to `65.42` at the documented
  source-of-truth boundary.
- The selection-mechanism summary uses the audited `39 / 5 / 80` counts and
  preserves equality between a retained reference and its equivalent adapted
  candidate instead of turning insignificant floating-point differences into
  a win or loss.
- C33 is represented as a neutral retained-reference case; S5 uses the check
  set label; S7/S8 public labels and harmful-selection denominators are
  consistent; and Table 4 includes the completed configuration label.
- Immutable historical inputs are preserved under audited provenance, with
  all sanitization and numerical corrections explicitly enumerated and
  checksum-tracked.

## Data and model assets

The Alibaba workflow now documents the official Cluster Trace v2018 source,
the expected `machine_usage.tar.gz` SHA-256 value
`3e6ee87fd204bb85b9e234c5c75a5096580fdabc8f085b224033080090753a7a`,
portable preprocessing, source-bank construction, and evaluation. The workload
observations are real; the model-complexity-limit tiers are deterministic and
semi-synthetic. The original trace is not redistributed.

Large model weights remain outside ordinary Git history. Their expected
filenames and SHA-256 values are listed in `assets/model_assets.csv`. A
permanent archival URL is still required before Level C can be advertised.

## Publication checklist

Before publishing or tagging v1.1.0:

1. Replace `Anonymous authors` in `CITATION.cff` with the final author list.
2. Add the paper DOI and actual release date.
3. Publish the permanent checksum-addressed model-asset archive and update the
   asset documentation.
4. Publish and validate the complete end-to-end Level C driver.
5. Re-run repository verification, CPU smoke, two independent Level B builds,
   generated-output verification, and the automated test suite.

The canonical repository is
<https://github.com/w924871681/paper-code-DT-Twin>. Credentials, passwords, and
two-factor recovery codes must never be committed or placed in release notes;
use a GitHub App, a least-privilege personal access token, or SSH for remote
operations.
