# Model assets and Level-C bootstrap

Large model weights are distributed in the GitHub Release bootstrap archive,
not ordinary Git history. The archive also contains the exact frozen evidence
and external-baseline records required by the locked main-evaluation preflight.

Release assets:

`https://github.com/w924871681/paper-code-DT-Twin/releases/download/v1.1.5/level_c_bootstrap_v1.1.5.zip`

- Size: `64,258,937` bytes
- SHA-256: `365df44a8cf4de1cabb21dd21aa6e865aff83a3f30d083e91caf18ed744ef650`
- Sidecar: `level_c_bootstrap_v1.1.5.zip.sha256`
- File records: `32`

`https://github.com/w924871681/paper-code-DT-Twin/releases/download/v1.1.5/cuda_replay_evidence_v1.1.5.zip`

- Size: `239,612` bytes
- SHA-256: `40c2bca3909142326df77f7af5c1698c6bbcc152eb7d36b28c147f0d4aa8a215`
- Sidecar: `cuda_replay_evidence_v1.1.5.zip.sha256`

Both v1.1.5 ZIP payloads are byte-identical to their verified v1.1.4
counterparts. They are renamed and given v1.1.5 sidecars so every current
release asset uses the same version label; the payload SHA-256 values above
remain unchanged.
Verify either downloaded archive with its sidecar:

```powershell
Get-Content .\<asset>.zip.sha256
Get-FileHash .\<asset>.zip -Algorithm SHA256
```

The recorded digest and computed hash must match. The evidence archive can be
checked more deeply with:

```powershell
python .\scripts\verify_release_evidence.py .\cuda_replay_evidence_v1.1.5.zip
```

`model_assets.csv` retains the flat 13-weight inventory. The complete portable
mapping is `level_c_bootstrap_files.csv`; it binds each archived file to the
repository-relative destination expected by the released code.

## Verify and stage

Extract the ZIP, then run:

```powershell
python .\scripts\stage_level_c_bootstrap.py `
  --bundle-root <extracted-bundle-directory> --verify-only
python .\scripts\stage_level_c_bootstrap.py `
  --bundle-root <extracted-bundle-directory>
python .\scripts\preflight_main_evaluation.py
```

The expected preflight decision is `PASS_C33_LOCKED_PREFLIGHT_READY`.

Custodians can recreate the release archive without modifying frozen files:

```powershell
python .\scripts\build_level_c_bootstrap.py `
  --source-root <custodian-project-root> `
  --bundle-root <output-directory> --zip
```

The Alibaba Cluster Trace v2018 is not present in this archive and is not
redistributed. See `data/alibaba2018/README.md`.

## Historical flat-asset check

For a legacy directory containing only the 13 filenames listed in
`model_assets.csv`, the original verifier remains available:

```powershell
python .\scripts\verify_assets.py --asset-dir <flat-weight-directory>
```
