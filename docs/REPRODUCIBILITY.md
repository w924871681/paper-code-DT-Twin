# Reproducibility

The repository exposes three deliberately separate levels.

## Level A: repository verification

```powershell
python .\scripts\verify_repository.py
python .\scripts\run_smoke_test.py
```

These CPU checks validate imports, released data, frozen configurations,
checksums, terminology, numerical consistency, and the small synthetic method
path. Model weights are not required.

## Level B: rebuild released tables and figures

```powershell
python .\scripts\generate_paper_outputs.py
```

This reads only released repository sources. It rebuilds eight code-generated
figures, including Fig. 6, Fig. 8, and Fig. 9 from six public derived CSVs;
checksum-copies unchanged Fig. 2--5; and reconstructs the manuscript tables.
No training or model weights are required.

The three reconstructed historical-result figures can also be built directly:

```powershell
python .\scripts\plot_reproducible_figures.py
```

## Level C: frozen locked-evaluation replay

Download and extract the v1.1.2 bootstrap release asset documented in
`assets/README.md`. First perform a no-training package and plan check:

```powershell
python .\scripts\stage_level_c_bootstrap.py `
  --bundle-root <extracted-bundle-directory> --verify-only
python .\scripts\run_full_reproduction.py `
  --bootstrap-dir <extracted-bundle-directory> --plan-only
```

Then use a CUDA-enabled PyTorch environment for either a short path test or the
formal frozen replay:

```powershell
python .\scripts\run_full_reproduction.py `
  --bootstrap-dir <extracted-bundle-directory> --smoke
python .\scripts\run_full_reproduction.py `
  --bootstrap-dir <extracted-bundle-directory>
```

The driver stages the exact archived files, performs the frozen preflight,
runs the seven locked methods, and—for a formal run—analyzes and audits all 80
case/configuration records per method. It writes a machine-readable ledger and
per-stage logs. It replays the target evaluation from frozen real weights; it
does not retrain the source-initialization bank.

Status: The reported CUDA experiments and their frozen outputs are complete.
The public bootstrap, staging process, formal preflight, and orchestration
driver are also complete. A fresh CUDA replay through the published public
entry point has also been completed. Its ledger, formal audit, environment,
logs, and historical comparison are archived in the local v1.1.3 delivery and
prepared for authorized Release publication.

Alibaba evaluation is separate because the original trace is not
redistributed. Follow `data/alibaba2018/README.md` for its checksum,
preprocessing, real-bank build, and evaluation commands.
