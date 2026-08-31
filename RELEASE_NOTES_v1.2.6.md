# Release Notes v1.2.6

This release synchronizes the latest supplied manuscript and supplementary
sources/PDFs with the completed H-Meta-NAS five-repeat frozen target-side
runtime audit.

## Scientific update

- Complete five 80-case H-Meta-NAS target-side timing repetitions on the
  NVIDIA GeForce RTX 3060 Laptop GPU.
- Report per-case target-side time as `20.349 ± 5.722 s`, where the dispersion
  is the sample standard deviation across the five repeat means.
- Publish all 400 sanitized case-level measurements, the five repeat summaries,
  environment metadata, protocol amendments, and the legacy-run compatibility
  audit.
- Exclude the earlier `43.061 s` measurement because it omitted initial
  candidate construction, included held-out test evaluation, and used an
  incompatible synchronization boundary.

## Integrity statement

The runtime completion reuses the frozen H-Meta-NAS configuration, source
meta-bank, 80 target cases, seeds, target search, and 50-update adaptation
budget. The selected-model and aggregate performance results remain unchanged.
The `rtol=1e-6` amendment applies only to numerical-equivalence verification;
the interrupted nine-case pre-amendment partial run remains excluded. No
MSA-DTI or other-method setting or result is modified.

## Publication package

- Adopt the supplied latest main and supplementary LaTeX sources.
- Rebuild and verify the synchronized 15-page manuscript PDF and verify the
  supplied final 9-page supplementary PDF.
- Regenerate the public runtime tables and Fig. 10 data from the canonical
  five-repeat summary.
