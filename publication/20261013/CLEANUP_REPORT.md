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

Pending owner approval: the four exact root-level historical manuscript paths
in [CLEANUP_PLAN.md](CLEANUP_PLAN.md). The 52-path inventory records the
reference/dependency basis. No approval-dependent deletion has occurred.

Final validation: `git diff --check` passed; the branch diff from the recorded
`main` baseline has no deleted paths. `scripts/verify_repository.py` passed all
public-repository, numerical-consistency, privacy, checksum and release-hygiene
checks. The current manuscript files match their source ZIP byte-for-byte.
The `v1.2.7` tag still points to
`b679181b3133ab9c3058afcde421d36380001f14`; its Release ID,
description and 30 asset IDs, names, sizes, digests and timestamps matched the
saved before snapshot. The prior light-evidence Release likewise matched its
saved description and single attachment. No historical Tag or Release was
edited.
