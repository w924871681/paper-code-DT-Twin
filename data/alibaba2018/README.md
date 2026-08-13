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

## Paper protocol: 20 source / 20 calibration / 40 held-out machines

The Alibaba experiment reported in Supplementary Section S7.3 uses three
mutually disjoint groups: 20 source machines, 20 margin-calibration machines,
and 40 held-out machines. From the repository root, run:

```powershell
python .\scripts\prepare_alibaba_domain_trace.py `
  --input .\data\alibaba2018\raw\machine_usage.tar.gz `
  --out-dir .\outputs\pre_submission_enhancements_d2904_t2904\alibaba_domain\prepared

python .\scripts\build_alibaba_domain_bank.py `
  --project-root . `
  --manifest .\outputs\pre_submission_enhancements_d2904_t2904\alibaba_domain\prepared\real_trace_domain_manifest.json `
  --out-dir .\outputs\pre_submission_enhancements_d2904_t2904\alibaba_domain\bank `
  --device cuda

python .\scripts\run_alibaba_domain_calibration.py `
  --project-root . `
  --manifest .\outputs\pre_submission_enhancements_d2904_t2904\alibaba_domain\prepared\real_trace_domain_manifest.json `
  --bank-dir .\outputs\pre_submission_enhancements_d2904_t2904\alibaba_domain\bank `
  --out .\outputs\pre_submission_enhancements_d2904_t2904\alibaba_domain\alibaba_domain_result.json `
  --device cuda
```

Do not pass `--skip-archive-hash-check` for a formal reproduction. The
prepared manifest records the verified input digest and the disjoint machine
groups; the bank manifest records the architecture-indexed source assets;
and `alibaba_domain_result.json` records the complete calibration grid and
the 160 held-out cases. Because no Alibaba-specific margin is eligible, the
reported 10% result is stored as a frozen-margin transfer audit rather than a
calibrated deployment rule.

## Legacy 20-source / 20-target protocol

The commands below reproduce an earlier 20-source/20-target diagnostic with
no independent margin-calibration group. They are retained for backward
compatibility and do **not** reproduce the Alibaba experiment reported in the
paper.

### Legacy preprocessing

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

### Legacy source-initialization bank

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

### Legacy evaluation

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
