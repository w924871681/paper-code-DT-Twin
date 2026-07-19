# v1.1.5 paper-alignment audit

Status: in progress until the tag, Release, and asset URLs are published and
post-publication checks pass.

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
- [ ] tag and GitHub Release v1.1.5 published
- [ ] all Release assets downloaded and checksum verified

## Publication record

- Commit: pending
- Tag: pending
- Release: pending
- Pull request: pending
- Release assets: pending
