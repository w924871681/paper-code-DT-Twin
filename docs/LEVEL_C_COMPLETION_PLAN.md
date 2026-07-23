# Level C public-path validation completed

The historical results and code are retained from actual runs. A mandatory
full retraining is not needed to establish that provenance. Level C is split
into a now-completed publication path and a separate new-execution check.

## Completed public prerequisites

- The 32-file portable bootstrap package is published with a release checksum.
- The package includes all frozen source-initialization weights, the pooled
  bundle, selector evidence, shared evaluator records, and external-baseline
  assets needed by the locked main evaluation.
- Public build, verification, and repository-relative staging commands are
  available.
- The public driver stages the package and orchestrates the frozen preflight,
  seven locked methods, analysis, and formal audit without retuning.
- The released package was built from the custodian workspace with every hash
  matching and passed `PASS_C33_LOCKED_PREFLIGHT_READY` after staging.

## New public-path CUDA replay completed

Status: The reported CUDA experiments and their frozen outputs are complete.
The public bootstrap, staging process, formal preflight, and orchestration
driver are also complete. A fresh CUDA replay through the published public
entry point completed on an NVIDIA GeForce RTX 3060 Laptop GPU. The ledger is
`PASS_FROZEN_MAIN_EVALUATION_REPLAY`, and the formal audit is
`PASS_C33_LOCKED_EVALUATION_COMPLETE_AND_AUDITED`. All non-timing case records
and reported metrics matched the historical frozen outputs.

The original Alibaba trace is a separate external prerequisite. It is not
redistributed. Repeating the Alibaba preprocessing, real source-bank build,
and evaluation also requires a CUDA environment and substantial runtime.

## Commands

Verify the package and inspect the exact stage plan without CUDA:

```powershell
python .\scripts\run_full_reproduction.py `
  --bootstrap-dir <extracted-bundle-directory> --plan-only
```

Execute a short CUDA path check:

```powershell
python .\scripts\run_full_reproduction.py `
  --bootstrap-dir <extracted-bundle-directory> --smoke
```

Execute the complete frozen locked main evaluation:

```powershell
python .\scripts\run_full_reproduction.py `
  --bootstrap-dir <extracted-bundle-directory>
```

The formal run is complete only when the ledger decision is
`PASS_FROZEN_MAIN_EVALUATION_REPLAY` and the formal audit passes. Source-bank
training is not repeated by this driver because the released archive freezes
the source initializations used by the reported evaluation.

## Completion boundary

The CUDA environment, GPU and driver versions, runtime ledger, stage logs,
output manifest, formal audit, and historical comparison are archived with
Release v1.1.9. The historical experiment is complete, public packaging is
complete, and the fresh CUDA replay is complete. Source-initialization training
was not repeated. Full from-raw Alibaba repetition remains separate because
its license-controlled source archive is external to this release.
