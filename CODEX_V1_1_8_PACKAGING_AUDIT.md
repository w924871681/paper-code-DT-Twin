# v1.1.8 packaging audit

## Reason for the patch

After v1.1.7 was published and its repository workflows passed, the standalone
final figure-code ZIP was downloaded into an empty directory and executed.
The unified reconstruction command correctly failed because the ZIP did not
contain the tracked `paper/tables/` presentation assets required by the
current generator.

The repository and complete v1.1.7 archive were not affected. The defect was
limited to the standalone ZIP assembly list.

## Resolution

v1.1.8 adds `paper/tables/` to the standalone package assembly and verifies
that the release workflow contains this copy step. The final acceptance test
downloads the published standalone ZIP, checks its SHA-256, extracts it into
an empty directory, and runs:

```text
python scripts/generate_paper_outputs.py
python scripts/validate_paper_outputs.py
```

Both commands must pass without access to the source checkout.

## Scientific invariants

No experiment code, data split, random seed, candidate bank, reference
candidate, optimizer, loss, 50-update budget, 10% threshold, complexity
limit, plot-ready value, figure implementation, or reported result changes in
v1.1.8.

## Release acceptance

- Local repository verification, CPU smoke, paper generation, validation,
  pytest, manuscript build, and visual QA pass.
- Main and tag GitHub Actions pass.
- The annotated tag resolves to the released main commit.
- Release v1.1.8 is public, non-prerelease, and Latest.
- Every published asset has a GitHub SHA-256 digest and checksum coverage.
- The independently extracted standalone package passes reconstruction.
