# Model assets and Level-C bootstrap

Large model weights are distributed in GitHub Release assets, not ordinary
Git history. Release `v1.1.9` publishes:

- `level_c_bootstrap_v1.1.9.zip` - 32 frozen files required by the locked
  main-evaluation preflight;
- `cuda_replay_evidence_v1.1.9.zip` - sanitized completed replay evidence;
- `paper_alignment_v1.1.9.zip` - regenerated tables, figures, plot-ready data,
  and validation manifests;
- `rcf_dti_v1.1.9_complete.zip` - manuscript, figures, code, data, configs,
  documentation, and audit evidence;
- `RCF_DTI_FIGURE_CODE_FINAL_V1_1_9.zip` - standalone final plotting package;
- sidecars and the combined `SHA256SUMS.txt`.

The Level-C and CUDA-evidence ZIP payloads are byte-identical to the verified
v1.1.4-v1.1.8 payloads; only their v1.1.9 release filenames change:

- Level-C size: `64,258,937` bytes; SHA-256
  `365df44a8cf4de1cabb21dd21aa6e865aff83a3f30d083e91caf18ed744ef650`.
- CUDA evidence size: `239,612` bytes; SHA-256
  `40c2bca3909142326df77f7af5c1698c6bbcc152eb7d36b28c147f0d4aa8a215`.

Verify downloaded assets:

```powershell
Get-FileHash .\<asset>.zip -Algorithm SHA256
python .\scripts\verify_release_evidence.py `
  .\cuda_replay_evidence_v1.1.9.zip
```

`model_assets.csv` is the 13-weight flat inventory.
`level_c_bootstrap_files.csv` maps all 32 archived files to their portable
repository destinations.

## Verify and stage

```powershell
python .\scripts\stage_level_c_bootstrap.py `
  --bundle-root <extracted-bundle-directory> --verify-only
python .\scripts\stage_level_c_bootstrap.py `
  --bundle-root <extracted-bundle-directory>
python .\scripts\preflight_main_evaluation.py
```

The expected decision is `PASS_C33_LOCKED_PREFLIGHT_READY`.

The Alibaba Cluster Trace v2018 is not included and is not redistributed.
See `data/alibaba2018/README.md`.
