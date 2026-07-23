# v1.1.7 paper-alignment audit

## Authority

The current journal-draft LaTeX source and `初稿.pdf` supplied on
2026-07-23 are the authority for manuscript prose, equations, algorithm
presentation, captions, Table 1--5 layout, and Data Availability wording.
Frozen repository outputs remain the authority for protocol settings and
reported numerical values.

The supplied current LaTeX differs materially from the v1.1.6 manuscript in
the abstract, Introduction, Related Work, proposed-method presentation,
algorithm pseudocode, experimental discussion, conclusion, and availability
statement. Those changes are presentation changes and do not alter the
implemented frozen protocol.

## Asset reconciliation

- Supplied Fig. 1 and Fig. 3--5 match the tracked checksum-bound assets.
- Supplied Fig. 2 has different page-canvas placement, but its visible
  content and the trimmed manuscript rendering match the tracked final Fig. 2
  asset. The existing checksum-bound asset is retained.
- Fig. 6--12 remain generated from released plot-ready data by
  `reporting/final_figures.py`.
- The supplied Table 1--5 LaTeX files are synchronized into `paper/tables/`.

## Terminology and bibliography

The manuscript and formal table layer use `MSE`. Historical internal fields
whose names contain `WMSE` remain compatibility identifiers and are mapped in
`docs/INTERNAL_PROVENANCE_NAMES.md`; uniform horizon weights make the released
values equal to the paper's MSE definition.

The two bibliography entries removed from Related Work were also removed from
the bibliography. Verification requires exact agreement between cited keys
and bibliography keys.

## Acceptance criteria

- Current LaTeX source and compiled PDF agree.
- Formal Table 1--5 assets contain no `WMSE` display label.
- Frozen protocol and core numerical values are unchanged.
- Test data remain excluded from selection and calibration.
- Fig. 1--12 and the single public figure implementation remain valid.
- Tests, manuscript build, output generation, and repository verification
  pass.
- The annotated v1.1.7 tag resolves to the released commit.
- The public Release is non-draft, non-prerelease, Latest, and all assets are
  covered by SHA-256.
