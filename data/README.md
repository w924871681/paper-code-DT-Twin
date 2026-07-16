# Data

## Synthetic centers

Synthetic centers are regenerated from `core/data/sim.py`, the frozen
configuration, and fixed seeds. `synthetic/split_manifest.json` records the
public source and target pools used by the released protocol.

## Alibaba Cluster Trace v2018

The original Alibaba trace is externally hosted and is not redistributed.
Only real workload observations are used; the model-complexity-limit tiers are
deterministic semi-synthetic labels. See `alibaba2018/README.md` for the exact
download object, checksum, local directory layout, preprocessing, real-bank
construction, and evaluation commands.

