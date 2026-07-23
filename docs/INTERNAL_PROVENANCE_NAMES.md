# Internal provenance names

Some frozen filenames and record keys retain historical identifiers so their
checksums and audit chain remain valid. They are not current paper terms.

| Historical identifier | Public meaning |
|---|---|
| `Ours`, `ours_c32_locked` | RCF-DTI |
| `PT-A57`, `pt_ft` | the fixed reference candidate / PT+FT baseline |
| `source_prior_bank` | source-initialization bank |
| `anchor_safe_selector` | reference-regularized candidate selection |
| `hard_feasibility` | filtering by both model complexity limits |
| `WMSE` in frozen schemas | historical field name for the uniformly horizon-weighted value; with the released uniform weights it equals the MSE reported in the paper |

These identifiers may occur in immutable provenance JSON, archived experiment
paths, compatibility modules, and checksum manifests. Public captions,
tables, figures, README text, and current documentation use RCF-DTI and the
paper's terminology.

`reporting/legacy/` contains archived plotting/reporting implementations for
auditing old runs. It is excluded from the formal paper-figure path.
