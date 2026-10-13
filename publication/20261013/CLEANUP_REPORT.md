# Repository cleanup execution report

Branch: `publish/current-evidence-20261013`, created from
`d9c37592b8293dc9a2726392915b6ed365e89aa5`.

Completed: current-manuscript navigation in the root and `paper/README.md`,
new `paper/current/` directory, experiment reproduction entrypoints, and
`.gitignore` entries for reproducible LaTeX build byproducts (`*.fls`,
`*.fdb_latexmk`, `*.blg`). Fresh working-copy inspection found no tracked
cache files eligible for automatic deletion. **Zero tracked files were
deleted or moved.** All original frozen code, results, older manuscripts,
figures, tables and prior public links remain available.

Final closure decision: the four exact root-level historical manuscript paths
in [CLEANUP_PLAN.md](CLEANUP_PLAN.md) are **KEEP**; deletion is not approved
for this round. The 52-path inventory records the reference/dependency basis.
No approval-dependent deletion has occurred. The manuscript corrections add
only necessary navigation and publication-state documentation;
there is no directory restructuring or deletion of research evidence.

Earlier full-evidence publication validation: `git diff --check` passed; the branch diff from the recorded
`main` baseline has no deleted paths. `scripts/verify_repository.py` passed all
public-repository, numerical-consistency, privacy, checksum and release-hygiene
checks. Before the Data Availability closure revision, the current manuscript
files matched their source ZIP byte-for-byte. The earlier Data Availability closure permitted changes only
to `main.tex`'s Data Availability and its newly compiled main PDF; the other
23 scientific members remain byte-identical to that baseline.
The `v1.2.7` tag still points to
`b679181b3133ab9c3058afcde421d36380001f14`; its Release ID,
description and 30 asset IDs, names, sizes, digests and timestamps matched the
saved before snapshot. The prior light-evidence Release likewise matched its
saved description and single attachment. No historical Tag or Release was
edited.

The previous Data Availability manuscript-only Release and its closure checks are recorded
separately in [FINAL_PUBLICATION_CLOSURE_REPORT.md](FINAL_PUBLICATION_CLOSURE_REPORT.md). The revised 16-page main
PDF passed three-run compilation, page comparison and clean-ZIP rebuild
checks with an identical PDF hash. The Supplementary remains unchanged at
15 pages in that version; its package passed CRC and all 29 internal member hashes. See
[build details](../../paper/current/BUILD_INFO.md) and
[exact source diff](../../paper/current/SOURCE_MINIMAL_DIFF.patch).
The four previous Data Availability manuscript-only Release attachments passed anonymous HTTP 200,
byte-count and SHA-256 checks; the 30-member ZIP passed CRC. Fresh before/after
GitHub comparisons confirmed the `v1.2.7` tag, its Release ID and 30 assets,
the light evidence Release's single asset, and the expanded evidence
Release's nine assets unchanged, including bodies, IDs, names, sizes, digests
and timestamps. The main branch remains at
`d9c37592b8293dc9a2726392915b6ed365e89aa5`; PR #9 remains a draft and unmerged.

The current correction is limited to one public-availability sentence in
Supplementary §S7.4 and its corresponding PDF. The main source/PDF and all
other scientific members from the previous manuscript-only version are KEEP.
The new [Supplementary correction Release entry](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/manuscript-suppfix-20261013)
is separate from every historical Release. Its build and publication
acceptance are recorded in the current
[publication status](MANUSCRIPT_PUBLICATION_STATUS.md) and
[Supplementary build details](../../paper/current/SUPPLEMENTARY_BUILD_INFO.md).
This correction authorizes no file deletion, relocation or evidence cleanup.
