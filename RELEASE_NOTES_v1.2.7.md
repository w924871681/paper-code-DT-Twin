# Release Notes v1.2.7

This release synchronizes the supplied latest manuscript and supplementary
LaTeX sources and PDFs with the completed reviewer-evidence audit. It is a
manuscript, reporting, and release-metadata update over v1.2.6.

## Manuscript update

- Clarify where MSA-DTI sits in the Digital Twin instantiation workflow and
  state that later online model updates are outside the present scope.
- Restore the retained `ref4` bibliography entry to the DT-background citation
  group, eliminating the sole orphan reference found by repository validation.
- Clarify that deployment feasibility is assessed using the predefined
  operation-count and parameter-count limits, without claiming universal
  latency or memory guarantees.
- Add the paired held-out MSE comparison table for all major baselines,
  including the frozen H-Meta-NAS comparison.
- Add the frozen-bank step-0/step-50 paired diagnostic and its confidence
  interval.
- Add the zero-training threshold-one/two/three screening sensitivity and the
  explicit boundary on what cannot be reconstructed from the frozen bank.
- State explicitly that the analytical sufficient condition does not provide
  an empirical bound on the validation-error term.

## Integrity statement

All newly reported statistics come from the completed offline audit of frozen
results. No model was retrained, no target adaptation was rerun, no held-out
test setting was tuned, and no frozen configuration, model weight, data split,
candidate bank, optimizer, adaptation budget, selection threshold, selected
model, or performance output was changed.

## Publication package

- Rebuild the 15-page main-manuscript PDF from the corrected v1.2.7 source and
  adopt the supplied 10-page supplementary PDF.
- Synchronize repository documentation, citation metadata, version checks, and
  release packaging to v1.2.7.
- Publish checksum-bound paper-alignment, complete-repository, figure-code,
  Level-C bootstrap, and CUDA replay assets through the existing release
  workflow.
- Regenerate the current manuscript Figure 5 from the canonical
  `results/main/overall_comparison.csv` H-Meta-NAS row through both its
  dedicated CLI and the formal paper-output entry point.
- Keep the v1.2.7 tag, code snapshot, manuscript PDFs, and release packages on
  the same final commit; the figure-code bundle includes the Figure 5
  generator, canonical CSV, and generated PDF.
- Publish the synchronized main manuscript and supplementary material as
  directly downloadable `.tex` and `.pdf` assets. The supplementary PDF is
  rebuilt from the current 11-page LaTeX source rather than the stale 10-page
  binary previously tracked in the repository.
