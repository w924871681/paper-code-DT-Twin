# Recovered C3-0 preselection evidence

These original historical files were recovered on 2026-10-28 from the former
C3-0 project. They concern the synthetic architecture-development screen used
before the Bitbrains source-training and evaluation stages. The result files
and historical logs are preserved byte-for-byte, including their historical
local project paths; those paths are provenance, not portable commands.

`c30_preflight.json`, `c30_fixed_anchor.json`, `c30_c1_oracle.json`,
`c30_analysis.json` and `c30_audit.json` contain the saved preflight, fixed
reference, per-case candidate results, analysis and completion audit. The
source asset manifest connects the historical PT-A57 anchors to the published
preselection asset. Historical C3-0 code snapshots are included for inspection;
they depend on the original project and do not alone constitute a standalone
raw-data-to-results pipeline.

The 80 cases cover center IDs 900--919 and H/K combinations (1,10), (1,20),
(4,10), (4,20), using 3,528 feasible candidate results. The verifier checks the
original audit hashes, candidate completeness, recorded best candidates,
fixed-reference metrics, development-pool configuration and recomputes both
win criteria. The six selected architecture configurations and their
(check-oracle wins, validation-selected positive check wins) are:

| Configuration | Counts |
| --- | --- |
| A1 | (1, 2) |
| A6 | (2, 1) |
| A13 | (2, 1) |
| A55 | (3, 2) |
| A56 | (2, 0) |
| A57 | (6, 7) |

Run the standard-library verification:

```text
python verify_c30_recovered.py
```

For additional identity checks, download
`MSA_DTI_v1.3.0_preselection_initializations.zip` from the archived
[v1.3.0 release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/v1.3.0)
and pass its local path as the first argument. Its published SHA-256 is
`88c001ce4274e41694eac7700d1af40688f24523f9b3c5acd5ca3e9c540aa27b`.
The C1 bank and PT-A57 H1/H4 initialization hashes then bind to the saved
historical results and source-asset manifest. `VERIFICATION_20261028.json`
records this check with the published bundle supplied.

This verification recomputes decisions from stored historical scores; it is
not a claim of retraining or a complete reproduction of the Bitbrains
experiments. The Bitbrains analysis remains a retrospective, non-blind
evaluation on a single trace; role-disjoint VM lists do not by themselves
establish independence from earlier research use.
