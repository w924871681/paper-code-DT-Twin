# Repository cleanup plan — 2026-10-13

The working branch starts from `main` commit
`d9c37592b8293dc9a2726392915b6ed365e89aa5`. Its 379 tracked files were
inspected before adding the current manuscript. The exact per-file sizes,
SHA-256 values, reference counts and referrers for 52 manuscript/figure paths
are in [REPOSITORY_CLEANUP_INVENTORY.csv](REPOSITORY_CLEANUP_INVENTORY.csv).
No tracked `.aux`, `.fls`, `.fdb_latexmk`, `.pyc` or `.DS_Store` files were found.

## Executed without deleting scientific material

- Create `paper/current/` as the only current manuscript entry, using
  byte-identical supplied TeX, PDF, figure, table and template files.
- Change the root and `paper/README.md` navigation to label the 2026-10-11
  directory and original `paper/manuscript.*` files as historical.
- Ignore future harmless LaTeX `.fls`, `.fdb_latexmk` and `.blg` build outputs.

## Exact tracked paths requiring user approval before any HEAD deletion

**Final closure decision:** deletion of all four paths below is not approved
for this round. Their current status is **KEEP**. This closure performs only
necessary documentation/navigation consistency changes, with no directory
restructuring or historical-evidence deletion.

| Path | Bytes | SHA-256 | Text reference count | Recovery anchor |
| --- | ---: | --- | ---: | --- |
| `paper/manuscript.pdf` | 3,226,919 | `e07bc8023379470051279aea30e803498d79580591fe5cda197290bf5a2954b0` | 4 | `v1.2.7` / `b679181b3133ab9c3058afcde421d36380001f14` |
| `paper/manuscript.tex` | 57,722 | `16640e0c3a431faf83b8b0a735c6d3fce9ce08f4a042935731d10c1973610c91` | 4 | Same |
| `paper/supplementary.pdf` | 292,478 | `bbf2388ffa6eacbcc8db50c2ec9a59aa405c5bf86d12d44b8ec50f0d73e7ddd1` | 7 | Same |
| `paper/supplementary.tex` | 35,672 | `b011f2103ed393729c06300842131d051a2ff752a235fafeb13982e524e69d7c` | 8 | Same |

These four are older root-level manuscript snapshots, so they can confuse
readers after `paper/current/` exists. They also carry frozen historical
value and are cited by existing repository text. **No deletion is proposed
for automatic execution.** If the owner later approves removal from the
current branch, first replace all affected links with dated historical links,
then run `git diff --name-status`, reference checks, and frozen-tag/Release
comparisons. Git history and the `v1.2.7` tag must remain untouched. Approval
should identify these exact paths; no broad wildcard deletion is authorized.

The dated `paper/manuscript_20261011/` snapshot, frozen `paper/figures/` and
`paper/tables/`, evidence manifests, code, configs, results, audit records and
old Release assets are **KEEP**. `paper_assets/current_figures/` is
**MOVE_OR_DOCUMENT**: despite its name it belongs to the historical frozen
figure pipeline; existing references make relocation risky, so it stays in
place and is clarified by navigation. Uncertain files default to KEEP.
