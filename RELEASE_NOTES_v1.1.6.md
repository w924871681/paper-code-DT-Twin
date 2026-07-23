# v1.1.6 — final manuscript and reproducibility synchronization

This release synchronizes the manuscript, captions, Data Availability,
Fig. 1--12, plot-ready data, public plotting implementation, documentation,
and release evidence.

## Scientific invariants

v1.1.6 does not change the data split, random seeds, six-architecture
candidate bank, seven initialized candidates, reference candidate, optimizer,
MSE loss, 50-update target adaptation, 10% selection threshold, complexity
limits, or any core experimental value.

The main held-out evaluation remains 80 cases: 47 alternative selections,
including 44 beneficial and 3 harmful under the post-selection test-MSE
audit, plus 33 reference-retained cases. Mean paired MSE reduction relative
to PT+FT remains 14.60%, and complexity-limit satisfaction remains 100%.

## Paper and figures

- Adds the compilable manuscript source, final PDF, tables, and Fig. 1--12.
- Binds final Fig. 1--5 to SHA-256 checksums.
- Makes `reporting/final_figures.py` the only maintained Fig. 6--12
  implementation.
- Rebuilds Fig. 6--12 from released plot-ready CSVs without training,
  adaptation, selection, or bootstrap resampling.
- Adds vector, 600-DPI, grayscale, layout, terminology, and caption checks.

## Audit and reproducibility

- Expands verification for frozen protocol fields, key numerical
  relationships, test leakage, duplicate plotting code, absolute paths,
  privacy-sensitive strings, version metadata, and generated outputs.
- Adds the figure source map and historical-identifier mapping.
- Includes manuscript, plotting/data, complete-paper, Level-C, CUDA evidence,
  audit, and SHA-256 release assets.

The original Alibaba Cluster Trace v2018 is not redistributed. Its official
source, checksum, preprocessing, and evaluation procedure remain documented;
only anonymized processed values are released.
