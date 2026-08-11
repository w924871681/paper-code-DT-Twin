# Final MSA-DTI consistency report

## Audit metadata

- Audit date: 2026-08-11
- Repository: `w924871681/paper-code-DT-Twin`
- Audited manuscript: `paper/manuscript.tex`
- Audited supplementary: `paper/supplementary.tex`
- Release version: v1.2.2
- Frozen release commit: `1fcdea25b60ce940efc306018dff45a8de44da2c`
- Post-release documentation baseline at audit start:
  `6f58fb52b1b555c992d04b1ffcc7d47fd5bda17d`

## Hotfix result

| File | Change | Status |
| --- | --- | --- |
| `README.md` | Current citation-release link updated; the separate Level-C v1.2.0 bootstrap reference is retained. | PASS |
| `docs/FINAL_MSA_DTI_SYNC_AUDIT.md` | Canonical target-side mapping corrected to `main_evaluation/pipeline.py` and `main_evaluation_cfg.py`; historical/general-purpose components are explicitly non-canonical. | PASS |
| `docs/FINAL_MSA_DTI_CONSISTENCY_REPORT.md` | Formal audit report added. | PASS |
| `paper/manuscript.tex`, `paper/manuscript.pdf` | Data Availability release reference synchronized to v1.2.2; no scientific source, result, or protocol changed. | PASS |

## Manuscript and supplementary consistency

| Item | Evidence checked | Status |
| --- | --- | --- |
| Title and MSA-DTI naming | Current manuscript and supplementary source/PDF text | PASS |
| Candidate terminology | 66 indexed configurations; 6 retained configurations; 5 executable architectures; 7 candidates; A57 | PASS |
| Target protocol | SGD, MSE, 50 updates, LR 0.01, common support budget, no candidate-specific early stopping | PASS |
| Selection and isolation | Fixed reference, tau=0.10, fallback/UnsupportedLimit, disjoint pools, post-freeze test use | PASS |
| Baseline and Alibaba wording | PT+FT, MeDeT-based, few-/zero-shot NAS, H-Meta-NAS-based, non-redistribution statement | PASS |
| Data Availability | Current v1.2.2 release link and official Alibaba source | PASS |

## Canonical code/config mapping

| Claim | Canonical implementation/config | Status |
| --- | --- | --- |
| 66/6/5/7 candidate bank and A57 | `configs/methods/candidate_space_cfg.py`, `core/space/`, frozen provenance | PASS |
| Operation/parameter limits and feasibility | `core/space/profile.py`, `main_evaluation/pipeline.py` | PASS |
| SGD/MSE/50 and tau=0.10 selection | `main_evaluation/pipeline.py`, `configs/methods/main_evaluation_cfg.py` | PASS |
| PT+FT, MeDeT, few-/zero-shot NAS, H-Meta-NAS-based | `main_evaluation/`, method configs, public result records | PASS |
| Optimizer diagnostic, dual-limit stress, profiling, source sensitivity | `experiments/supplementary/`, `experiments/robustness/`, `scripts/run_*` | PASS |
| Alibaba transfer and statistics | Alibaba preparation/evaluation scripts; released figure data and bootstrap records | PASS |

## Numerical, table, figure, and PDF audit

- PT+FT MSE `0.005120`, MSA-DTI MSE `0.004219`, and paired MSE reduction `14.60%`: PASS.
- 80 cases; 33 retained references; 47 alternatives; 44 beneficial; 3 harmful; 3.75% all-case harmful rate: PASS.
- H-Meta-NAS-based MSE `0.013747`; runtime `5.676 +/- 0.059` s; 6.25 adapted models: PASS.
- Alibaba paired reduction `4.20%`, 95% CI `[2.03%, 6.70%]`, and harmful rate `6.25%`: PASS.
- Tables map from released CSV data through `reporting/` and `paper/tables/`; display-only rounding is consistent: PASS.
- Fig. 1--5 are checksum-bound assets; Fig. 6--12 use `reporting/final_figures.py` and released CSV data: PASS.
- Fig. 6 text layer: `RB-DTI = 0`, `RCF-DTI = 0`, `MSA-DTI present = YES`: PASS.
- Main PDF: `WMSE = 0`, `RB-DTI = 0`, `RCF-DTI = 0`, `MSA-DTI > 0`, `v1.2.2 > 0`: PASS.
- Supplementary PDF: `RB-DTI = 0`, `RCF-DTI = 0`, `MSA-DTI > 0`: PASS.

## Repository completeness and release parity

- Tracked but unpushed reproducibility-required files: 0.
- Untracked reproducibility-required files: 0.
- Release-only large assets: checksum-bound Level-C assets remain in v1.2.0.
- Restricted files excluded: Alibaba raw/processed data and model checkpoints.
- Local-only ignored files: environments, caches, LaTeX intermediates, and run outputs.
- Public unexplained `RCF-DTI`: 0; public unexplained `RB-DTI`: 0. Historical identifiers are documented only in provenance/legacy context.
- Release `v1.2.2` resolves to the frozen scientific and reproducibility
  commit `1fcdea25b60ce940efc306018dff45a8de44da2c`.
- At the start of this final dynamic re-audit, `origin/main` was one
  documentation-only audit-report cleanup commit ahead at
  `6f58fb52b1b555c992d04b1ffcc7d47fd5bda17d`.
- No manuscript, implementation, configuration, result, table, figure,
  experiment, or scientific protocol changed after the `v1.2.2` release
  commit.

## Final dynamic re-audit

The complete verification suite was rerun on the current `main` branch after
the release-parity wording correction. The final Git state is collected again
after this documentation-only report commit is pushed; `v1.2.2` remains the
immutable frozen scientific/reproducibility release.

| Check | Final rerun result |
| --- | --- |
| `python scripts/verify_repository.py` | PASS_PUBLIC_REPOSITORY_VERIFICATION (exit 0) |
| `python -m pytest` | PASS -- 13 passed (exit 0) |
| `python scripts/run_smoke_test.py` | PASS_CPU_SMOKE_TEST (exit 0) |
| `python scripts/generate_paper_outputs.py` | PASS_FROZEN_TABLES_AND_FIGURES / PASS_PAPER_OUTPUT_VALIDATION (exit 0) |
| Git diff `v1.2.2..origin/main` | Documentation-only: `docs/FINAL_MSA_DTI_CONSISTENCY_REPORT.md` |
| PDF terminology audit | PASS: main `WMSE=0`, `RB-DTI=0`, `RCF-DTI=0`, `MSA-DTI=44`, `v1.2.2=2`; supplementary `RB-DTI=0`, `RCF-DTI=0`, `MSA-DTI=11` |
| Formal table reconstruction | PASS: `PAPER_TABLE_NAMES = (table1_configuration, table4_target_cost)`; both tracked tables are byte-identical to generated tables; Table 1 has `MSE` and no `WMSE` |
| Figure-data reconstruction | PASS: checksum-bound Fig. 1--5 and released-data Fig. 6--12 validated by the reconstruction script; Fig. 6 has no `RB-DTI` or `RCF-DTI` and retains `MSA-DTI` |

The frozen protocol and released records were also rechecked without
recalculation or modification: reference A57; SGD/MSE, 50 target updates,
LR 0.01; relative margin 0.10; 80 held-out cases; 33 reference retentions,
47 alternatives, 44 beneficial selections, and 3 harmful selections. The
released records retain PT+FT MSE 0.005120, MSA-DTI MSE 0.004219, paired MSE
reduction 14.60%, H-Meta-NAS-based MSE 0.013747, MSA-DTI runtime
5.676 +/- 0.059 s with 6.25 adapted models, and Alibaba paired reduction
4.20% (95% CI [2.03%, 6.70%], harmful rate 6.25%).

README, CITATION, package metadata, and the manuscript Data Availability
statement identify v1.2.2 as the current release. The separate Level-C
bootstrap provenance remains at v1.2.0. No untracked reproducibility-required
file was found, and no tracked scientific/reproducibility file was modified.

## Final static-cleanup audit

Two non-scientific static inconsistencies were removed after Release v1.2.2:

1. The README current-release description was synchronized from the historical
   v1.2.1 wording to the current archived Release v1.2.2.
2. The `reporting/frozen.py` module docstring was updated from the obsolete
   phrase "five exact current-manuscript tables" to the count-independent
   phrase "exact current-manuscript formal tables".

The second change is comment/docstring-only and does not alter executable
behavior. No manuscript, supplementary material, configuration,
implementation logic, result, table, figure, experiment, or scientific
protocol changed.

| Check | Final result |
| --- | --- |
| `python scripts/verify_repository.py` | PASS_PUBLIC_REPOSITORY_VERIFICATION (exit 0) |
| `python -m pytest` | PASS -- 13 passed (exit 0) |
| `python scripts/run_smoke_test.py` | PASS_CPU_SMOKE_TEST (exit 0) |
| `python scripts/generate_paper_outputs.py` | PASS_FROZEN_TABLES_AND_FIGURES / PASS_PAPER_OUTPUT_VALIDATION (exit 0) |
| README current-release wording | PASS — v1.2.2 |
| `reporting/frozen.py` current-table docstring | PASS — count-independent wording |
| Executable diff after v1.2.2 cleanup | PASS — none; `reporting/frozen.py` is docstring-only |
| Scientific/reproducibility diff | PASS — none |

## Resolved final issue

The prior audit failed because Table 1 retained the historical public label
`WMSE`, while the manuscript and canonical generator use `MSE`. The tracked
Table 1 label was changed to `MSE`; no value or scientific protocol changed.
The complete reconstruction and validation suite were rerun successfully.

## Current formal table set

Current main-manuscript external formal tables: 2.

1. `paper/tables/table1_configuration.tex`, rendered as Table 1.
2. `paper/tables/table4_target_cost.tex`, rendered as Table 2.

Other files under `paper/tables/` are not referenced by the current manuscript
and are retained as historical/public reproducibility assets. Supplementary
tables are defined inline in `paper/supplementary.tex` and audited separately.

The canonical generator is now aligned with the current manuscript's two
formal external tables rather than the historical Table 1--5 assumption.

## Remaining issues

None.

## Final verdict

**FINAL REPOSITORY CONSISTENCY = PASS**

**FINAL SUBMISSION PACKAGE CONSISTENCY = PASS**

The final manuscript, supplementary material, canonical implementation,
frozen results, current formal tables, figures, PDFs, and Release v1.2.2 are
mutually consistent at the frozen scientific/reproducibility commit.

The current GitHub `main` branch remains scientifically and reproducibly
consistent with Release v1.2.2 and contains only post-release documentation
and comment-only cleanup commits. No scientific result or protocol changed
after the v1.2.2 release commit.

The final static-cleanup commit is documentation/comment-only. Its exact
identifier, the resulting ahead count, and the complete post-release file
list are obtained from Git after push rather than pre-stated in the content
of the commit itself.

**REPOSITORY / REPRODUCIBILITY WORKSTREAM = FROZEN**

Release v1.2.2 remains the frozen scientific/reproducibility release.

The current `main` branch contains only post-release documentation and
comment-only cleanup commits. These changes do not alter executable behavior,
the manuscript's scientific content, configurations, experimental results,
tables, figures, or reproducibility protocol.
