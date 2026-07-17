# Release notes: v1.1.1

This maintenance release strengthens figure reproducibility without changing
the frozen method, data splits, selected models, or reported conclusions.

## Fig. 6, Fig. 8, and Fig. 9

- Adds six public derived CSV files covering paired locked-case metrics,
  candidate filtering, model-configuration selection, candidate-bank size,
  adaptation steps, and the minimum-improvement diagnostic.
- Adds an independent plotting command:
  `python scripts/plot_reproducible_figures.py`.
- Integrates the same plotting implementation into the Level B one-command
  paper-output reconstruction.
- Produces pure-vector PDFs, 600-DPI PNGs, grayscale previews, and layout-audit
  JSON files. Fig. 2--5 remain unchanged historical assets.

## Verification

- Repository verification, CPU smoke testing, Level B reconstruction,
  generated-output verification, and the full test suite pass.
- Released text hashes verify consistently across Windows CRLF and Unix LF
  checkouts.

## Level C boundary

This release does not claim fresh-clone Level C reproduction. The archived
weights and Alibaba source archive exist in the custodian workspace, but a
permanent public asset location, complete bootstrap packaging, a validated
end-to-end driver, and a CUDA-enabled runtime check are still required. Level A
and Level B remain fully public and do not require those assets.
