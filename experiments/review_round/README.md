# Review-round diagnostics

These scripts support the manuscript revision round only. They are **not** part
of the frozen scientific protocol and do not change the reported results.

- `bench_concurrent_reconfig.py`: concurrency stress test for the target-side
  per-case workload on one GPU. It loads the frozen source initializations at
  horizon H=4 and reports how per-case wall time scales with 1/2/4/8 concurrent
  jobs.
- `sample_size_analysis.py`: center-cluster bootstrap width/power analysis for
  the harmful-selection rate, using the already-frozen 80 held-out cases.

Both scripts require the local frozen assets (Level B/C outputs) and a CUDA
PyTorch environment. They are diagnostics for the reviewer discussion and were
not used to modify the manuscript results.
