# Level C completion plan

Level C is technically achievable, but the current public release does not yet
claim it. The experiments are not missing from the custodian workspace; the
remaining gap is a portable, permanently hosted bootstrap package plus an
executed CUDA verification of the public orchestration path.

## What already exists

- The 12 architecture-matched source-initialization weights and the pooled
  historical bundle listed in `assets/model_assets.csv` exist and have matching
  SHA-256 values.
- The original Alibaba `machine_usage.tar.gz` archive exists in the custodian
  workspace and matches the checksum documented under `data/alibaba2018/`.
- Individual public entry points exist for the locked main evaluation,
  component and robustness studies, Alibaba preprocessing/evaluation, and
  paper-output reconstruction.
- `environment.yml` specifies a CUDA-enabled Conda environment using Python
  3.11 and `pytorch-cuda=12.1`.

## What the public bootstrap package must additionally contain

The 13-file flat weight archive is necessary but not sufficient for a portable
fresh-clone run. The final evaluation code also verifies exact frozen evidence
and baseline initialization records. A release bootstrap bundle therefore
needs:

1. the frozen shared-evaluator identity and qualification JSON files;
2. the exact source-initialization-bank manifest that binds the 12 weights;
3. the frozen 10% selector manifest, its analysis, and its audit binding;
4. the external-baseline initialization manifest, audit, and two additional
   unique baseline weight files;
5. a portable destination manifest mapping every archived file to the relative
   path expected by the released code.

These files exist locally. They must be copied without content changes because
the released preflight checks intentionally bind their hashes.

## Public driver requirements

The completed driver must perform and record the following stages:

1. verify repository files, bootstrap hashes, Alibaba archive hash, and CUDA;
2. stage the bootstrap bundle into portable repository-relative paths;
3. run the frozen preflight and all seven locked main-evaluation methods;
4. analyze and audit the locked evaluation before downstream studies run;
5. execute component, robustness, supplementary, and Alibaba stages without
   retuning the frozen method;
6. rebuild paper outputs and run Level A and Level B verification again;
7. write a machine-readable stage ledger containing commands, return codes,
   start/end times, output hashes, and resume status.

## Acceptance criteria

Level C can be marked complete only after all of the following are true:

- the bootstrap bundle has a permanent public URL and published SHA-256;
- a fresh clone can receive the bundle without private absolute paths or
  unpublished files;
- the driver finishes on a CUDA-enabled machine and every scientific audit
  returns its documented PASS decision;
- regenerated result tables agree with the released frozen values within the
  declared deterministic or numerical tolerances;
- the exact environment, GPU model, driver version, runtime, and final output
  manifest are archived.

Until then, `scripts/run_full_reproduction.py` correctly reports Level C as
blocked instead of presenting a validation-only plan as an executed rerun.
