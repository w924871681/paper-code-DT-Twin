# Level C status and completion boundary

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

## What has not been newly rerun

The current Python installation is CPU-only even though the machine has an
NVIDIA GPU. Therefore the seven-method CUDA replay has not been executed in
this release session. This is a runtime validation gap for the newly published
path; it is not a claim that the frozen historical outputs are unverified or
that their model assets are absent.

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

## Remaining acceptance item

To claim a newly executed Level-C replay, archive the CUDA environment, GPU and
driver versions, runtime ledger, stage logs, output manifest, and successful
formal audit. Full from-raw Alibaba repetition should be reported separately
because its license-controlled source archive is external to this release.
