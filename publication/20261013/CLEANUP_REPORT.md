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

Validation required after publication: review the final Git diff, verify that
only new manuscript/publication documentation and `.gitignore` changed, check
fixed current-paper links and previous historical links, and compare both
`v1.2.7` and the prior light-evidence Release against saved before snapshots.
