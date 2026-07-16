# Result layers and terminology

The result tree has two deliberately different layers.

- `main/`, `robustness/`, and `supplementary/` preserve frozen or
  checksum-tracked corrected source schemas used by historical experiment
  code. Their columns may retain internal identifiers such as `Ours`, `A57`,
  or `FLOPs`; these are provenance fields, not recommended public paper terms.
- `figure_data/` is the public presentation layer. Its labels use the revised
  paper terminology, and `reporting/frozen.py` derives cross-file values before
  rounding.
- `audited_provenance/` contains publishable immutable audit files, path-only
  sanitized copies with both hashes, and the manifest for narrowly corrected
  stale diagnostics.

No correction changes the frozen method, seeds, data split, hyperparameters,
or selected models. See
`audited_provenance/NUMERICAL_CORRECTIONS.json` for original-package hashes,
corrected hashes, and exact reasons.

