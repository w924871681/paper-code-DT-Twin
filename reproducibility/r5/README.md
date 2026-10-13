# R5 synthetic contribution diagnostic

The 2026-10-13 research-assets archive includes the actual `r5/data.npz`,
`r5/data_manifest.json`, source/candidate checkpoints and bank manifests under
`r5/assets/`, complete per-case development/evaluation records, saved
predictions and truth, bootstrap samples, protocol locks, code and figures.
This extends the separately preserved light audit archive.

To verify saved results, extract the research-assets ZIP to a fresh directory
and run `python verify_core_results.py` from its top-level directory with
NumPy installed. It checks member hashes, 80 evaluation cases, 240
prediction/truth pairs, selector choices, development-fixed mapping and the
4,000-draw center-cluster bootstrap. Mean case-relative Test-MSE improvement
over Dev-Fixed-Best is 13.4803% (95% center-cluster CI [6.3856%, 21.0963%]).

The source and staging commands are in `code/experiments/r4_r5/r5.py` (`prep`,
`lock`, `dev`, `eval`) and the protocol lock. Re-execution must use a **new**
study root with independently obtained/prepared inputs and a new replay lock;
the archived completed run refuses implicit overwrite. No model training or
checkpoint inference was repeated for this publication.

**Historical limit:** the original R2 screening development-pool seeds and
raw arrays were not recoverable. Status:
`UNRESOLVED_HISTORICAL_RNG_PROVENANCE`. The newly available R5 data and
checkpoints cannot retroactively establish that historical nonoverlap. Treat
the result as provenance-qualified supplementary/exploratory evidence.
