# Data availability

The repository includes source code, frozen configurations, processed result
tables, and scripts for rebuilding the revised manuscript's exact structured
table data and complete figure set. Synthetic multi-center data can be
regenerated from the released simulator and fixed seeds.

Full training reruns require the archived model assets listed in
`assets/model_assets.csv`. A permanent public model-asset URL and the public
end-to-end driver are not yet available, so this repository does not claim
complete Level C reproduction from a fresh clone. The asset manifest and
`scripts/verify_assets.py` provide exact filenames and SHA-256 validation once
the archive is available.

The original Alibaba Cluster Trace v2018 is available from Alibaba Group and
is not redistributed here. `data/alibaba2018/README.md` identifies the exact
download object, official source, expected layout, checksum, preprocessing
command, real source-bank build, and evaluation entry point.

Level B reads only files released in the repository and requires neither model
weights nor the Alibaba archive.

