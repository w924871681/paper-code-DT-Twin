# Result layers and terminology

The result tree has two deliberately different layers.

- `main/`, `robustness/`, and `supplementary/` preserve frozen or
  checksum-tracked corrected source schemas used by historical experiment
  code. Their columns may retain internal identifiers such as `Ours`, `A57`,
  or `FLOPs`; these are provenance fields, not recommended public paper terms.
- `figure_data/` is the public presentation layer. Its labels use the revised
  paper terminology, and `reporting/frozen.py` derives cross-file values before
  rounding. It also contains the public derived CSVs for Fig. 6, Fig. 8, and
  Fig. 9; these are the direct inputs to the independent plotting CLI.
- `audited_provenance/` contains publishable immutable audit files, path-only
  sanitized copies with both hashes, and the manifest for narrowly corrected
  stale diagnostics.
- `supplementary/h_meta_nas_runtime_audit/` contains the sanitized 5 x 80
  frozen H-Meta-NAS target-side runtime audit. Its canonical paper statistic
  is `20.349 ± 5.722 s` per case; the frozen performance result is unchanged.

No correction changes the frozen method, seeds, data split, hyperparameters,
or selected models. See
`audited_provenance/NUMERICAL_CORRECTIONS.json` for original-package hashes,
corrected hashes, and exact reasons.
