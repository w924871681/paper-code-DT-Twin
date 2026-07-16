# Alibaba Cluster Trace v2018

## Source and citation

Use the official [Alibaba Cluster Data repository](https://github.com/alibaba/clusterdata)
and its [Cluster Trace v2018 description](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2018/trace_2018.md).
The official page provides the trace after its access process and lists
checksums for the separate tables and complete archive.

Please cite the dataset as used in the paper:

> Alibaba Group, "Alibaba Cluster Trace Program: Cluster Trace v2018
> [dataset]," GitHub repository, 2018.

The original trace is not redistributed by this repository.

## Download object

This pipeline needs only the machine-usage table. Download either:

- `machine_usage.tar.gz` (preferred; approximately 1.7 GB), or
- `alibaba_clusterdata_v2018.tar.gz` (the complete archive), then extract its
  nested `machine_usage.tar.gz` before running preprocessing.

The expected SHA-256 for the separate `machine_usage.tar.gz` archive is:

```text
3e6ee87fd204bb85b9e234c5c75a5096580fdabc8f085b224033080090753a7a
```

Do not use an unverified third-party mirror or undocumented direct URL.

## Expected layout

```text
data/alibaba2018/
|-- raw/
|   `-- machine_usage.tar.gz
`-- processed/
```

The raw archive should contain a member whose basename is
`machine_usage.csv`. Both `raw/` and `processed/` are local-only directories
and should remain ignored by Git except for placeholder files.

## Preprocessing

From the repository root:

```powershell
python .\scripts\prepare_alibaba2018_trace.py --help
python .\scripts\prepare_alibaba2018_trace.py `
  --input .\data\alibaba2018\raw\machine_usage.tar.gz `
  --out-dir .\data\alibaba2018\processed
```

Do not pass `--skip-archive-hash-check` for a formal reproduction. It exists
only for controlled development with a different enclosing archive digest.

The preprocessing step generates:

```text
data/alibaba2018/processed/
|-- alibaba2018_machine_usage_processed.npz
`-- real_trace_manifest.json
```

The manifest records selected machines, the source/target split,
preprocessing settings, and input digest. Released code stores portable paths
and resolves them relative to the manifest.

## Build the Alibaba source-initialization bank

The semi-real evaluation uses an architecture-matched bank trained from the
processed real-trace source machines:

```powershell
python .\scripts\build_alibaba2018_bank.py --help
python .\scripts\build_alibaba2018_bank.py `
  --manifest .\data\alibaba2018\processed\real_trace_manifest.json `
  --out-dir .\outputs\full_reproduction\alibaba2018_bank `
  --device cuda
```

This long-running stage writes `real_bank_manifest.json` and the expected
`real_h*_a*.pt` files below the specified bank directory. The manifest stores
relative checkpoint paths. The separate archive in `assets/` supports the
synthetic Level-C stages; it is not a substitute for this Alibaba bank.

## Evaluation

After the bank build completes:

```powershell
python .\scripts\run_alibaba2018_evaluation.py --help
python .\scripts\run_alibaba2018_evaluation.py `
  --project-root . `
  --manifest .\data\alibaba2018\processed\real_trace_manifest.json `
  --bank-dir .\outputs\full_reproduction\alibaba2018_bank `
  --out .\outputs\full_reproduction\alibaba2018_evaluation.json `
  --device cuda
```

The workload observations come from the real production trace. The
model-complexity-limit tiers are deterministic semi-synthetic labels used to
evaluate target-specific feasibility. The experiment does not claim direct
measurement of device latency, memory use, or energy consumption.

