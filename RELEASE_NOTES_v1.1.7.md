# v1.1.7 - current journal manuscript alignment

This release aligns the public repository with the current journal-draft
LaTeX source and PDF supplied after v1.1.6 was published.

## What changed

- Replaces the archived manuscript source/PDF with the current abstract,
  Introduction, Related Work, proposed-method presentation, algorithm,
  experimental discussion, conclusion, and Data Availability text.
- Synchronizes the exact current Table 1--5 LaTeX layouts.
- Uses `MSE` throughout the formal manuscript and table presentation layer.
  Historical frozen fields containing `WMSE` remain documented compatibility
  identifiers; their values use the uniform horizon weighting and equal the
  MSE reported in the paper.
- Removes two bibliography entries that are no longer cited.
- Updates README, METHOD, reproducibility documentation, citation metadata,
  audits, packaging, and release checks to v1.1.7.

## Scientific invariants

v1.1.7 does not change the data split, random seeds, six-architecture
candidate bank, seven initialized candidates, reference candidate, optimizer,
MSE loss, 50-update target adaptation, 10% selection threshold, complexity
limits, or any core experimental value.

The main held-out evaluation remains 80 cases: 47 alternative selections,
including 44 beneficial and 3 harmful under the post-selection test-MSE
audit, plus 33 reference-retained cases. Mean paired MSE reduction relative
to PT+FT remains 14.60%, and complexity-limit satisfaction remains 100%.

## Reproducibility

The release contains the current manuscript source/PDF, Fig. 1--12,
plot-ready data, exact Table 1--5 assets, the single maintained Fig. 6--12
implementation, frozen evidence, and SHA-256 manifests.

The original Alibaba Cluster Trace v2018 is not redistributed. Its official
source, checksum, preprocessing, and evaluation procedure are documented;
only anonymized processed values are released.
