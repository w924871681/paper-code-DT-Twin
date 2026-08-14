# Final MSA-DTI consistency report (v1.2.3)

## Release lineage

- `v1.2.2` is the **historical frozen scientific/reproducibility release** and
  remains unmodified. Its tag and published artifacts are not moved, overwritten,
  or rewritten.
- `v1.2.3` is the **final submission release** produced by the review-consistency
  packaging cleanup described below.

## v1.2.3 changes

1. **H-Meta-NAS reporting correction.** The manuscript's task-matched H-Meta-NAS
   MSE was corrected from `0.013747` to the audited canonical `0.013574`. The
   manuscript Figure 5 asset (`paper/figures/fig_overall_performance_ours.pdf`)
   was regenerated so its four H-Meta-NAS values match the audited result
   (`results/main/overall_comparison.csv`: MAE 0.0902667091, MSE 0.0135739418,
   Worst-10% 0.0461530964, CVaR90 0.0349348963). The plotting source now records
   that source of truth.

2. **Public WMSE → MSE terminology cleanup.** The current public-facing layer
   (`results/figure_data/*.csv` headers and value labels, `reporting/frozen.py`,
   `reporting/final_figures.py`, `scripts/derive_reproducible_figure_data.py`,
   `scripts/verify_repository.py`) now emits `MSE`/`mse`. Internal frozen source
   schemas and `reporting/legacy/` retain `WMSE` only as a historical alias,
   documented in `docs/INTERNAL_PROVENANCE_NAMES.md`. No numerical value changed.

3. **Candidate screening retention-rule wording unified.** The main text,
   Supplementary S2.1, and Table 1 now use the frozen implemented rule
   (`check-oracle wins >= 2 OR validation-selected positive check wins >= 2`),
   matching S7.2 and `source_prior_bank/pipeline.py`. The threshold, retained
   list, frozen bank, and headline results are unchanged.

4. **Workload-forecasting clarification.** Section 3.1 states that workload
   forecasting is a representative evaluation task, not an additional MSA-DTI
   component.

5. **Runtime scope wording.** Section 5.4 reports only the measured one-GPU,
   one-instantiation-case scope and no longer infers a low-frequency deployment
   assumption.

## Provenance decision

`results/audited_provenance/NUMERICAL_CORRECTIONS.json` is a **current mutable
correction manifest** (it is read live by `scripts/verify_repository.py` and is
explicitly excluded from the immutable-audit check). For v1.2.3 its corrected
hashes were updated for the terminology-cleanup files, and the prior v1.2.2
corrected hashes are preserved in each entry's `previous_corrected_sha256` field
plus a top-level `version_history`. Historical original hashes in `FILE_INDEX.csv`
remain unchanged.

## Figure 5 asset note

- The manuscript's **Figure 5** asset is
  `paper/figures/fig_overall_performance_ours.pdf`, regenerated for v1.2.3.
- `paper_assets/current_figures/fig5.pdf` (tracked as `fig5` in
  `paper_assets/current_figures/manifest.json`) is actually the manuscript's
  **Figure 4** asset under a historical filename; its manifest checksums are
  unchanged and internally consistent.

## Final verification

| Check | Result |
| --- | --- |
| `python scripts/verify_repository.py` | PASS_PUBLIC_REPOSITORY_VERIFICATION |
| `python -m pytest -q` | 13 passed |
| `python scripts/generate_paper_outputs.py` | PASS_FROZEN_TABLES_AND_FIGURES |
| `python scripts/validate_paper_outputs.py` | PASS_PAPER_OUTPUT_VALIDATION |
| Main manuscript and Supplementary compilation | Completed |

## Verdict

**FINAL SUBMISSION PACKAGE CONSISTENCY = PASS**

**ZERO KNOWN STATIC INCONSISTENCIES = PASS**

`v1.2.2` remains frozen and unmodified. `v1.2.3` is the current final submission
release reflecting the review-consistency fixes listed above.
