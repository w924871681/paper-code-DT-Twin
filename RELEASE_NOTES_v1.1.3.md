# Release notes: v1.1.3

This prepared release aligns the public repository with the final manuscript
without changing the frozen method, weights, data splits, random seeds,
candidate bank, optimizers, adaptation steps, selection threshold, or reported
numerical results.

## Paper and Level B alignment

- Corrects the exact revised-paper mapping so Table 4 is the optimizer-matched
  control, Table 5 is the component ablation, and Table 6 is target-side
  runtime and model complexity.
- Clarifies the Fig. 7 score as `100 / (1 - mean case-level paired WMSE
  reduction)` and the held-out-case averaging used by Fig. 11.
- Clarifies that Level C replays the frozen locked main evaluation and does not
  retrain the source-initialization bank.

## Release assets

The release workflow reuses the byte-identical v1.1.2 frozen bootstrap,
publishes it under the v1.1.3 asset name with a SHA-256 sidecar, downloads both
published assets, and verifies the checksum. The frozen payload remains
64,258,937 bytes with SHA-256
`365df44a8cf4de1cabb21dd21aa6e865aff83a3f30d083e91caf18ed744ef650`.

This file prepares v1.1.3 locally. No tag or GitHub Release is created until
remote publication is explicitly authorized.

## CUDA public-path validation

The published bootstrap was verified and staged in an independent directory.
Verify-only, plan-only, the seven-method CUDA smoke, and the complete frozen
main-evaluation replay passed. The final ledger is
`PASS_FROZEN_MAIN_EVALUATION_REPLAY`, the formal audit is
`PASS_C33_LOCKED_EVALUATION_COMPLETE_AND_AUDITED`, and all non-timing case
records and reported metrics match the historical frozen outputs. The local
archive is prepared for upload after explicit authorization. Source training
was not repeated.
