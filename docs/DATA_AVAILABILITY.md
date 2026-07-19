# Data availability

The reported results were obtained from completed experiments. The repository
includes source code, frozen configurations, processed result
tables, and scripts for rebuilding the revised manuscript's exact structured
table data and complete figure set. Synthetic multi-center data can be
regenerated from the released simulator and fixed seeds.

GitHub Release
[`v1.1.5`](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/v1.1.5)
publishes the paper-aligned code and release assets. Its checksum-bound
32-file bootstrap archive is byte-identical to the verified v1.1.4 payload;
only the v1.1.5 asset filename and sidecar entry are updated.
`assets/level_c_bootstrap_files.csv` maps every archived
file to its portable repository destination, and the public driver replays the
frozen locked main evaluation after staging. Source-initialization training is
not repeated by this replay. The sanitized CUDA replay evidence is likewise a
byte-identical, hash-verified reuse of the v1.1.4 payload under its v1.1.5
asset name. The same release also provides the v1.1.5 paper-alignment archive
and checksum.

The original Alibaba Cluster Trace v2018 is available from Alibaba Group and
is not redistributed here. `data/alibaba2018/README.md` identifies the exact
download object, official source, expected layout, checksum, preprocessing
command, real source-bank build, and evaluation entry point.

Level B reads only files released in the repository and requires neither model
weights nor the Alibaba archive. The exact anonymized case-level values used by
Fig. 12(b), including all four Alibaba gains below -25%, are released in
`results/figure_data/fig12_case_level_gains.csv`.
