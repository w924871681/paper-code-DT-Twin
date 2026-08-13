# Final MSA-DTI consistency report

## Audit scope

This report records the final public repository consistency audit for the
manuscript, supplementary material, canonical implementation, frozen results,
formal tables, figures, PDFs, and public reproduction package. Dynamic Git
state is reported outside this tracked document after push so that this report
does not become stale when it is committed.

## Frozen scientific/reproducibility release

Release `v1.2.2` is the frozen scientific/reproducibility release and points
to commit `1fcdea25b60ce940efc306018dff45a8de44da2c`.

All commits on `main` after this release are restricted to documentation or
comment-only consistency cleanup. The cumulative post-release path set is:

- `README.md`
- `docs/FINAL_MSA_DTI_CONSISTENCY_REPORT.md`
- `reporting/frozen.py`

The `reporting/frozen.py` change is docstring-only. No post-release commit
changes executable behavior, manuscript scientific content, configurations,
experimental results, tables, figures, or the reproducibility protocol.

## Manuscript and supplementary consistency

| Item | Evidence checked | Status |
| --- | --- | --- |
| Title and MSA-DTI naming | Current manuscript and supplementary source/PDF text | PASS |
| Candidate terminology | 66 indexed configurations; 6 retained configurations; 5 executable architectures; 7 candidates; A57 | PASS |
| Target protocol | SGD, MSE, 50 updates, LR 0.01, common support budget, no candidate-specific early stopping | PASS |
| Selection and isolation | Fixed reference, tau=0.10, disjoint pools, post-freeze test use | PASS |
| Baseline and Alibaba wording | PT+FT, MeDeT-based, few-/zero-shot NAS, externally cited meta-NAS work distinguished from reproduced baselines, non-redistribution statement | PASS |
| Data Availability | Current v1.2.2 release link and official Alibaba source | PASS |

## Canonical code/config mapping

| Claim | Canonical implementation/config | Status |
| --- | --- | --- |
| 66/6/5/7 candidate bank and A57 | `configs/methods/candidate_space_cfg.py`, `core/space/`, frozen provenance | PASS |
| Operation/parameter limits and feasibility | `core/space/profile.py`, `main_evaluation/pipeline.py` | PASS |
| SGD/MSE/50 and tau=0.10 selection | `main_evaluation/pipeline.py`, `configs/methods/main_evaluation_cfg.py` | PASS |
| Canonical adaptation and selection | `optim.SGD`, squared-error mean loss, fixed-reference 10% margin; check/test selection flags false | PASS |
| Main held-out evaluation and baselines | `main_evaluation/`, method configs, public result records | PASS |
| Diagnostics and Alibaba transfer | Public scripts, released figure data, and bootstrap records | PASS |

## Numerical consistency

- PT+FT MSE `0.005120`, MSA-DTI MSE `0.004219`, paired MSE reduction `14.60%`: PASS.
- 80 cases; 33 retained references; 47 alternatives; 44 beneficial; 3 harmful; 3.75% all-case harmful rate: PASS.
- Few-shot NAS MSE `0.007105`; runtime `5.676 +/- 0.059` s; 6.25 adapted models: PASS.
- Alibaba aggregate reduction `4.29%`; paired reduction `4.20%`; 95% CI `[2.03%, 6.70%]`; all-case harmful rate `6.25%`; conditional harmful rate `17.54%`: PASS.
- Released CSV data, reporting code, manuscript, supplementary material, and table/figure displays use consistent frozen values and display-only rounding: PASS.

## Current formal tables

The current main-manuscript external formal tables are:

1. `paper/tables/table1_configuration.tex`, rendered as Table 1.
2. `paper/tables/table4_target_cost.tex`, rendered as Table 3.

`PAPER_TABLE_NAMES` contains precisely these two externally reconstructed
tables. The optimizer-matched diagnostic is defined inline as Table 2 from
the same frozen data reported in Supplementary Table S2. Table 1 uses MSE
(with no WMSE), SGD/MSE/50, LR 0.01, the 10% rule, and the 66/6/5/7 candidate
description. Table 2 records MSA-DTI runtime `5.676 +/- 0.059` s and 6.25
adapted models. Other files under `paper/tables/` are historical/public
reproducibility assets; supplementary tables are defined inline.

## Figure consistency

Fig. 1--5 are checksum-bound fixed assets. Fig. 6--12 are reconstructed by
`reporting/final_figures.py` from released CSV data. Figure reconstruction and
asset validation pass. Fig. 6 contains MSA-DTI and no RB-DTI or RCF-DTI.

## PDF terminology audit

The main PDF has `WMSE = 0`, `RB-DTI = 0`, `RCF-DTI = 0`, `MSA-DTI > 0`, and
`v1.2.2 > 0`. The supplementary PDF has `RB-DTI = 0`, `RCF-DTI = 0`, and
`MSA-DTI > 0`.

## Repository completeness

- Reproducibility-required tracked but unpushed files: 0.
- Reproducibility-required untracked files: 0.
- Restricted Alibaba raw/processed data and model checkpoints are not
  redistributed. Environments, caches, LaTeX intermediates, and local run
  outputs remain local-only or ignored.
- Level-C checksum-bound bootstrap assets retain their v1.2.0 provenance;
  v1.2.2 is the current archived consistency release.

## Post-release documentation/comment cleanup classification

The README current-release wording was synchronized to v1.2.2. The
`reporting/frozen.py` module docstring was made count-independent to describe
the current formal table set. These are documentation/comment-only changes.
No manuscript, supplementary material, configuration, implementation logic,
result, table, figure, experiment, or scientific protocol changed.

## Final dynamic verification

| Check | Final result |
| --- | --- |
| `python scripts/verify_repository.py` | PASS_PUBLIC_REPOSITORY_VERIFICATION |
| `python -m pytest` | PASS -- 13 passed |
| `python scripts/run_smoke_test.py` | PASS_CPU_SMOKE_TEST |
| `python scripts/generate_paper_outputs.py` | PASS_FROZEN_TABLES_AND_FIGURES / PASS_PAPER_OUTPUT_VALIDATION |
| Current-version and stale-phrase static audit | PASS |
| Formal-table reconstruction | PASS |
| Figure-data reconstruction | PASS |
| PDF terminology audit | PASS |

## Remaining issues

None.

## Final verdict

**FINAL REPOSITORY CONSISTENCY = PASS**

**FINAL SUBMISSION PACKAGE CONSISTENCY = PASS**

**ZERO KNOWN STATIC INCONSISTENCIES = PASS**

**ZERO KNOWN DYNAMIC INCONSISTENCIES = PASS**

**REPOSITORY / REPRODUCIBILITY WORKSTREAM = FROZEN**

Release v1.2.2 remains the frozen scientific/reproducibility release. The
current `main` branch contains only post-release documentation and comment-only
cleanup commits. These changes do not alter executable behavior, the
manuscript's scientific content, configurations, experimental results, tables,
figures, or reproducibility protocol.
