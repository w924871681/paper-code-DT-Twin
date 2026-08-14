# v1.2.3 - Final submission release

This release is the final submission package after first-round blind review and
the corresponding review-consistency / provenance cleanup. It supersedes the
earlier v1.2.3 tag/release that pointed to a reverted predictive-model framing
on a side branch.

## Changes

- H-Meta-NAS reporting correction: manuscript MSE `0.013747` -> `0.013574`;
  Fig. 5 regenerated from the audited canonical values.
- Public `WMSE` -> `MSE` terminology cleanup across plot-ready data and current
  reporting code; internal frozen schemas retain `WMSE` as a documented legacy
  alias.
- Candidate screening retention-rule wording unified to the frozen
  check-oracle / validation-selected positive-check rule.
- Workload-forecasting clarification in Section 3.1.
- Runtime scope wording (removed the unmeasured low-frequency assumption).
- Data Availability, README, and current-release documentation updated to v1.2.3.

## Provenance

- v1.2.2 remains frozen and unmodified.
- `NUMERICAL_CORRECTIONS.json` is updated as a current mutable correction
  manifest; prior corrected hashes are preserved.

## Verification

- `verify_repository.py`: PASS
- `pytest`: 13 passed
- `generate_paper_outputs.py` / `validate_paper_outputs.py`: PASS
- Main manuscript and Supplementary compiled.

No scientific protocol, experiment, data split, seed, candidate bank, optimizer,
margin, or headline number changed.
