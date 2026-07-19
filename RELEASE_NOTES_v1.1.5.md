# v1.1.5 — paper alignment and frozen publication

This release aligns the public repository with the current manuscript while
leaving the frozen protocol, model weights, data splits, seeds, candidate bank,
optimizer, adaptation budget, selection threshold, and core numerical results
unchanged.

## Paper alignment

- The exact manuscript layer now maps Table 1--5 to configuration, fairness,
  overall comparison, optimizer-matched control, and component ablation.
- Runtime and model complexity remain available in the broader public result
  layer and are not presented as a manuscript Table 6.
- The latest Fig. 1 is synchronized as a checksum-bound fixed asset.
- Fig. 6--12 are rebuilt from released CSV data. Fig. 10 is the current
  deployment trade-off radar, Fig. 11 is the two-dimensional architecture
  complexity--performance map, and Fig. 12 releases all 320 case-level gains.
- Fig. 12 explicitly identifies four Alibaba cases below -25%, with a minimum
  gain of -360.3%.

## Release assets

The Level-C bootstrap and sanitized CUDA evidence ZIP payloads are
byte-identical to their verified v1.1.4 counterparts and are renamed only to
unify the v1.1.5 asset set:

- `level_c_bootstrap_v1.1.5.zip`: 64,258,937 bytes,
  SHA-256 `365df44a8cf4de1cabb21dd21aa6e865aff83a3f30d083e91caf18ed744ef650`
- `cuda_replay_evidence_v1.1.5.zip`: 239,612 bytes,
  SHA-256 `40c2bca3909142326df77f7af5c1698c6bbcc152eb7d36b28c147f0d4aa8a215`
- matching `.sha256` sidecars
- `paper_alignment_v1.1.5.zip` and its sidecar, containing generated
  Tables 1--5, Fig. 1--12, figure data, validation report, and manifest
- the finalized paper-alignment audit is available in the repository at
  `CODEX_V1_1_5_PAPER_ALIGNMENT_AUDIT.md`

## Verification

The release is accepted only after repository verification, CPU smoke test,
paper-output generation and validation, full pytest, a clean second generation,
and post-publication asset/hash checks all pass.
