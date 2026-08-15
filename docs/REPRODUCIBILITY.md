# Reproducibility

## Level A: audit and tests

```powershell
python .\scripts\verify_repository.py
python -m pytest
python .\scripts\run_smoke_test.py
```

These CPU checks validate the frozen protocol, numerical relationships,
test-set isolation, released data, fixed-asset checksums, module imports,
version metadata, terminology, absolute paths, privacy rules, and the small
synthetic execution path. Model weights are not required.

## Level B: paper reconstruction

```powershell
python .\scripts\generate_paper_outputs.py
```

This is the only formal figure/table command. It reads released repository
files, checksum-copies Fig. 1--5, regenerates Fig. 6--12 from plot-ready CSVs,
reconstructs the manuscript Table 1--5 CSVs, and copies the exact
checksum-audited Table 1--5 LaTeX presentation assets. It does not run
training, target adaptation, candidate selection, or bootstrap resampling.

`reporting/final_figures.py` is the only maintained Fig. 6--12
implementation. The former direct plotting command is a compatibility shim
that calls this same module.

## Canonical target-side implementation

The current MSA-DTI held-out protocol uses the SGD/MSE 50-update target
adaptation and the frozen reference-margin candidate-selection implementation
in `main_evaluation/pipeline.py`, with frozen values defined in
`configs/methods/main_evaluation_cfg.py`. `core/methods/ours/adapt.py` and
`core/methods/ours/c23_mode_selector.py` contain historical or
general-purpose adaptation components retained for reproducibility and
compatibility; they are not the canonical implementation of the current
protocol.

## Manuscript build

From `paper/`, compile `manuscript.tex` with a LaTeX distribution containing
the Elsevier CAS single-column class and the packages declared in the source.
All table inputs and Fig. 1--12 are tracked beside the source. The checked
`paper/manuscript.pdf` is the result used for release verification.

## Level C: frozen locked-evaluation replay

Download the v1.1.9 bootstrap asset and verify it before execution:

```powershell
python .\scripts\stage_level_c_bootstrap.py `
  --bundle-root <extracted-bundle-directory> --verify-only
python .\scripts\run_full_reproduction.py `
  --bootstrap-dir <extracted-bundle-directory> --plan-only
```

The complete replay requires CUDA:

```powershell
python .\scripts\run_full_reproduction.py `
  --bootstrap-dir <extracted-bundle-directory>
```

It stages the exact archived files, runs the seven locked methods, analyzes
80 records per method, and executes the formal audit. It uses frozen
source-trained weights and does not retrain the source bank.

The published 32-file portable bootstrap package carries a release checksum
and includes all frozen source-initialization weights, the pooled bundle,
selector evidence, shared evaluator records, and external-baseline assets
required by the locked main evaluation. A fresh CUDA replay through this
public entry point completed on an NVIDIA GeForce RTX 3060 Laptop GPU with
ledger decision `PASS_FROZEN_MAIN_EVALUATION_REPLAY` and formal audit
`PASS_C33_LOCKED_EVALUATION_COMPLETE_AND_AUDITED`; all non-timing case
records and reported metrics matched the historical frozen outputs.

The original Alibaba trace is separate because it is not redistributed.
Follow `data/alibaba2018/README.md`.
