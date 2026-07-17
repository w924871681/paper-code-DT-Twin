# Release notes: v1.1.2

This release completes the public packaging and orchestration prerequisites for
replaying the frozen locked main evaluation. It does not change the method,
weights, frozen data splits, reported results, or Fig. 2--5.

## Level-C bootstrap package

- Adds a 32-file destination manifest covering the source-initialization
  weights, pooled historical bundle, frozen selector evidence, evaluator
  records, and external-baseline assets.
- Adds checksum-verifying build and staging commands.
- Publishes `level_c_bootstrap_v1.1.2.zip` (64,258,937 bytes), SHA-256
  `365df44a8cf4de1cabb21dd21aa6e865aff83a3f30d083e91caf18ed744ef650`.
- The Alibaba Cluster Trace v2018 is not redistributed.

## Frozen evaluation driver

- `scripts/run_full_reproduction.py` now stages the portable bundle, performs
  the locked preflight, runs all seven frozen main-evaluation methods, analyzes
  the outputs, and executes the formal audit.
- Every stage receives a timestamp, command, return code, log, and log SHA-256
  in a machine-readable ledger.
- `--plan-only` verifies the complete bundle without requiring CUDA or running
  an experiment; `--smoke` executes two locked cases per method on CUDA.

## Validation boundary

The released bundle was built from the custodian assets with all 32 hashes
matching. It was staged into a clean repository-relative layout, and the
formal locked-evaluation preflight returned `PASS_C33_LOCKED_PREFLIGHT_READY`
with every check true. A CUDA execution of the seven-method replay has not been
performed in the current CPU-only Python environment and is not claimed.
