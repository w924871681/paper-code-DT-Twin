# R1 End-to-End Screening Stability Report

## Material Passport

- Artifact type: controlled diagnostic experiment result
- Protocol: `r1_candidate_discovery_e2e_stability_v1_0`
- Repository commit: `e705ff222e3ebdcb06a5314a3266e497df2fbdc2`
- Verification status: `PASS_R1_COMPLETE_AND_AUDITED`
- Test isolation: held-out Test was materialized only after per-case validation selection

## Pre-run audit

The frozen space contains 66 indexed configurations, with A57 as the protected reference. The screening rule retains a configuration when either screening evidence count reaches two. S0, S1, and S2 are treated as fixed inputs; no screening is rerun and no hyperparameter is retuned.

## Fixed pools and roles

- Source training: centers 0--19, data seed 2904, seed offset 0.
- Shared bank-specific calibration: centers 940--959, seed offset 200000.
- R1 held-out evaluation: centers 1180--1199, seed offset 320000, master seed 322904.
- Held-out Test was not used in source training, calibration, deployment filtering, adaptation, or selection.

## Results

| Screen | Retained configurations | Candidate-bank size | Calibrated tau | Mean paired MSE reduction vs PT+FT | 95% CI | MSE win rate | Alternative selected | Harmful / 80 | Conditional harmful rate | Limit satisfaction |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| S0 | A1, A6, A13, A55, A56, A57 | 7 | 0.075 | 10.034% | [4.602%, 16.019%] | 52.50% | 48 | 6 | 12.50% | 100.00% |
| S1 | reference fallback only | 1 | no eligible / fallback | 0.000% | [0.000%, 0.000%] | 0.00% | 0 | 0 | 0.00% | 100.00% |
| S2 | A55, A56, A57, A59 | 5 | 0.125 | 8.784% | [3.833%, 14.238%] | 41.25% | 39 | 6 | 15.38% | 100.00% |

## Candidate banks and calibration

### S0

- Retained indexed configurations: A1, A6, A13, A55, A56, A57.
- Candidate-bank size: 7.
- Candidate identities: PT_A57_A57, LEGACY_C1_A57_A57, STRONG_COMPACT_A1, STRONG_COMPACT_A6, STRONG_COMPACT_A13, STRONG_COMPACT_A55, STRONG_COMPACT_A56.
- Calibration: 0.075.
- Selected candidate counts: `{"PT_A57_A57": 32, "STRONG_COMPACT_A13": 2, "STRONG_COMPACT_A55": 21, "STRONG_COMPACT_A56": 19, "STRONG_COMPACT_A6": 6}`.
- Selected configuration counts: `{"A13": 2, "A55": 21, "A56": 19, "A57": 32, "A6": 6}`.

### S1

- Retained indexed configurations: none.
- Candidate-bank size: 1.
- Candidate identities: PT_A57_A57.
- Calibration: no eligible margin; adapted-reference fallback.
- Selected candidate counts: `{"PT_A57_A57": 80}`.
- Selected configuration counts: `{"A57": 80}`.

### S2

- Retained indexed configurations: A55, A56, A57, A59.
- Candidate-bank size: 5.
- Candidate identities: PT_A57_A57, LEGACY_C1_A57_A57, STRONG_COMPACT_A55, STRONG_COMPACT_A56, STRONG_COMPACT_A59.
- Calibration: 0.125.
- Selected candidate counts: `{"PT_A57_A57": 41, "STRONG_COMPACT_A55": 16, "STRONG_COMPACT_A56": 17, "STRONG_COMPACT_A59": 6}`.
- Selected configuration counts: `{"A55": 16, "A56": 17, "A57": 41, "A59": 6}`.

## Verification and provenance

- Verification decision: `PASS_R1_COMPLETE_AND_AUDITED`.
- Repository verification exit code: 0.
- Total runtime: 14297.241 seconds.
- Protocol manifest SHA-256: `27a3e786b7ef33b7ebdc7b4e6dd844a68f8e7204747791f4e1eeb3a181f2e7ed`.
- Generated checkpoints and result hashes are listed in `artifact_hashes.json`.
- No manuscript, Supplement, canonical figure/table, release tag, or pre-existing canonical result was intentionally modified.
- Tracked files changed during R1: 0.

## Protocol deviations

None if and only if the verification decision above is PASS. Any failed check is recorded in `verification.json` and must be treated as a deviation.
