# Release notes: v1.1.4

This release is a public-packaging and privacy patch. It does not change the
method, frozen protocol, model weights, data splits, random seeds, candidate
bank, optimizer, adaptation budget, selection threshold, or reported results.

## Public evidence privacy

- Replaces machine-specific absolute paths in the public CUDA replay archive
  with portable placeholders and repository-relative paths.
- Adds Release-asset privacy scanning and checksum validation.
- Publishes a sanitized CUDA replay evidence archive.

## Replay orchestration

- Separates CUDA smoke outputs from formal replay outputs.
- Allows smoke and formal replay to run sequentially without manual cleanup.
- Revalidates the frozen seven-method replay and historical-output comparison.

## Documentation

- Synchronizes README, Data Availability, reproducibility documentation,
  Level-C status, asset instructions, and Release state.
- Updates the manuscript-facing availability statement to the latest archived
  release.

No source-initialization training was repeated.
