# Data availability

Release
[`v1.1.7`](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/v1.1.7)
contains the manuscript source/PDF, Fig. 1--12, plot-ready figure data,
structured tables, frozen configurations, reproduction code, audit evidence,
and SHA-256 checksums.

Synthetic multi-center data can be regenerated from the released simulator,
configurations, and fixed seeds. Level B requires neither model weights nor
the Alibaba archive. The exact anonymized case-level values used in
Fig. 12(b), including the four Alibaba gains below -25%, are tracked in
`results/figure_data/fig12_case_level_gains.csv`.

The original Alibaba Cluster Trace v2018 is available from Alibaba Group and
is not redistributed. `data/alibaba2018/README.md` records the official
source, expected checksum and layout, preprocessing procedure, real
source-bank construction, and evaluation entry point. Public derived records
contain anonymized identifiers and processed evaluation values only.
