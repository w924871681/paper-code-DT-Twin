# Data availability

The reported results were obtained from completed experiments. The repository
includes source code, frozen configurations, processed result
tables, and scripts for rebuilding the revised manuscript's exact structured
table data and complete figure set. Synthetic multi-center data can be
regenerated from the released simulator and fixed seeds.

The v1.1.2 GitHub Release publishes a checksum-bound 32-file bootstrap archive.
`assets/level_c_bootstrap_files.csv` maps every archived file to its portable
repository destination, and the public driver replays the frozen locked main
evaluation after staging. Source-initialization training is not repeated by
this replay. A fresh CUDA execution through the public entry point is reported
separately from the historical frozen outputs.

The original Alibaba Cluster Trace v2018 is available from Alibaba Group and
is not redistributed here. `data/alibaba2018/README.md` identifies the exact
download object, official source, expected layout, checksum, preprocessing
command, real source-bank build, and evaluation entry point.

Level B reads only files released in the repository and requires neither model
weights nor the Alibaba archive.
