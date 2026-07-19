# v1.1.5 paper-alignment audit

Status: complete. The tag, Release, six versioned assets, workflow verification,
and independent post-publication download checks all passed.

## Frozen boundary

The v1.1.5 work changes only public paper mapping, reporting code, fixed
figure assets, derived figure data, documentation, and release packaging. It
does not change model weights, frozen configurations, seeds, data splits,
candidate bank, optimizer, target adaptation budget, selection threshold, or
core reported metrics.

## Required checks

- [x] exact manuscript Table 1--5 mapping
- [x] latest Fig. 1 checksum synchronized
- [x] Fig. 6--12 deterministic code generation
- [x] Fig. 10--12 visual and layout audit
- [x] repository verification
- [x] CPU smoke test
- [x] paper-output generation and validation
- [x] full pytest (13 passed)
- [x] clean second generation with 106 identical generated-file hashes
- [x] tag and GitHub Release v1.1.5 published
- [x] all Release assets downloaded and checksum verified

## Publication record

- Release commit: https://github.com/w924871681/paper-code-DT-Twin/commits/v1.1.5
- Tag: https://github.com/w924871681/paper-code-DT-Twin/tree/v1.1.5
- Release: https://github.com/w924871681/paper-code-DT-Twin/releases/tag/v1.1.5
- Pull request: https://github.com/w924871681/paper-code-DT-Twin/pull/1
- Release assets:
  - `level_c_bootstrap_v1.1.5.zip` and sidecar
  - `cuda_replay_evidence_v1.1.5.zip` and sidecar
  - `paper_alignment_v1.1.5.zip` and sidecar

## Published asset checksums

- `level_c_bootstrap_v1.1.5.zip`:
  `365df44a8cf4de1cabb21dd21aa6e865aff83a3f30d083e91caf18ed744ef650`
- `cuda_replay_evidence_v1.1.5.zip`:
  `40c2bca3909142326df77f7af5c1698c6bbcc152eb7d36b28c147f0d4aa8a215`
- `paper_alignment_v1.1.5.zip`:
  `302a834d05560db5b886ff720c8d9383accd077f333e1f06636106364c304a82`

Release workflow:
https://github.com/w924871681/paper-code-DT-Twin/actions/runs/29697500846
