# Data availability

Release
[`v1.2.7`](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/v1.2.7)
contains the manuscript source/PDF, Fig. 1--12, plot-ready figure data,
structured tables, frozen configurations, reproduction code, audit evidence,
and SHA-256 checksums.

The release also contains all 400 sanitized H-Meta-NAS target-side timing
records, the five repeat summaries, environment metadata, protocol amendments,
and the compatibility audit that excludes the legacy 43.061-s measurement.

Synthetic multi-center data can be regenerated from the released simulator,
configurations, and fixed seeds. Level B requires neither model weights nor
the Alibaba archive. The exact anonymized case-level values used in Fig. 12(b), including
160 held-out Alibaba cases and the one gain below -25%, are tracked in
`results/figure_data/fig12_case_level_gains.csv`.

The original Alibaba Cluster Trace v2018 is available from Alibaba Group and
is not redistributed. `data/alibaba2018/README.md` records the official
source, expected checksum and layout, source-only preprocessing, the
disjoint 20/20/40 machine split, real source-bank construction,
independent threshold calibration, and held-out evaluation entry point. Public derived records
contain anonymized identifiers and processed evaluation values only.
