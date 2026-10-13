# Bitbrains GWA-T-12 research assets

The research-assets ZIP includes `code/experiments/r4_r5/bitbrains_data.py`,
`bitbrains_source.py`, and `bitbrains_target.py`; preparation and source
manifests, deterministic VM identity split, 14 source/candidate checkpoints,
development and calibration candidates, selector locks, 160 held-out cases,
saved predictions/truth, bootstrap samples and figures. It is materially more
complete than the earlier light audit ZIP.

The original fastStorage workload trace is available from the
[official GWA-T-12 page](https://atlarge-research.com/gwa-t-12/). Acknowledge
Bitbrains IT Services Inc. and cite Shen, van Beek and Iosup, *Statistical
Characterization of Business-Critical Workloads Hosted in Cloud Datacenters*
(CCGrid 2015), as requested by the source. The third-party raw archive and
full trace-derived training-window/target-series NPZs are **not redistributed**
because redistribution rights for those inputs were not established. Their
hashes, VM identities and role metadata remain in the public manifests.

For saved-output verification, extract the public research-assets ZIP and run
`python verify_core_results.py` from its top-level directory with NumPy. This
recalculates 960 saved prediction/truth pairs across 160 cases, development
mapping, five-gate calibration and the VM-cluster bootstrap. Mean case-relative
MSE gain over PT+FT is 32.7045% (95% VM-cluster CI [7.6721%, 51.2506%]);
11/160 held-out harmful replacements (6.875%) exceed the empirical 5%
calibration criterion. That criterion is not a population risk guarantee.

For a new from-raw trace run, obtain the official archive, verify its SHA-256
against `bitbrains/acquisition_receipt.json`, place it under a **new** study
root's `bitbrains/raw/`, then inspect/run `bitbrains_data.py --root NEW_ROOT`.
Source training uses `bitbrains_source.py --root NEW_ROOT --device cuda`, and
the target stages use `bitbrains_target.py dev|calibration|heldout --root
NEW_ROOT`. Follow the archived protocol locks and manifests; do not copy
completed-stage locks into an active replay or overwrite original results.
This publication verified saved outputs and checkpoint hashes, **not** a
second-machine from-raw training run. The experiment is in-domain
source-trained Bitbrains evaluation, not zero-shot cross-dataset transfer.
