# v1.1.6 release audit

This report is finalized by the release workflow and the post-publication
verification recorded under `audit/v1.1.6/`.

## Authority and handoff reconciliation

The supplied final handoff was checked before repository integration. Its
instructions and manuscript were readable, but the extracted
`final_figures/` directory contained only Fig. 1--5 although the handoff text
described Fig. 1--12. The supplied manifest also did not match the actual
manuscript PDF/source bytes. Fig. 3--5 in that directory conflicted with the
same handoff's terminology requirements and with the figures embedded in the
manuscript.

Following the handoff's stated authority order, v1.1.6 uses:

- the manuscript source and its explicit captions/protocol statements;
- the visually identical manuscript PDF supplied at the workspace root;
- the corrected Fig. 1--5 assets embedded in that manuscript;
- plot-ready data and frozen outputs for Fig. 6--12;
- one consolidated public implementation for regenerated figures.

No historical input overwrote the manuscript, final figures, or formal
plotting code.

## Acceptance criteria

- Frozen protocol and core numerical values unchanged.
- Test data excluded from selection and calibration.
- Fig. 1--12 synchronized with captions and manuscript.
- One formal figure/table entry point.
- Tests, manuscript build, figure generation, and repository verification
  pass.
- Annotated tag target equals the released commit.
- Release is public, non-prerelease, and marked Latest.
- Every release asset is covered by SHA-256.

Machine-readable results and final commit/tag/release identifiers are stored
in `audit/v1.1.6/`.
