# H-Meta-NAS five-repeat frozen target-side runtime audit

- Decision: `PASS_H_META_NAS_FIVE_REPEAT_FROZEN_RUNTIME_AUDIT`
- Five repetitions complete: `True`
- Frozen performance unchanged: `True`
- Protocol deviation/amendment recorded: `True`
- Amendment scope: verification tolerance only; no model, search, adaptation, data, seed, warm-up, synchronization, or timing setting changed.
- Legacy 43.061-s run counted: `False`
- Legacy compatibility decision: not fully compatible because the legacy timer included Check/Test work, omitted initial feasible-population construction, lacked an overall pre-timer synchronization, and lacked a final post-Test synchronization.
- Timing unit used for paper comparison: mean seconds per target case over each complete 80-case repetition.
- Held-out test evaluation: outside the timer, after selection, equivalence-check only.

| Repeat | Cases | Total (s) | Mean/case (s) |
|---:|---:|---:|---:|
| 1 | 80 | 2446.007690 | 30.575096 |
| 2 | 80 | 1459.698936 | 18.246237 |
| 3 | 80 | 1407.393890 | 17.592424 |
| 4 | 80 | 1416.078506 | 17.700981 |
| 5 | 80 | 1410.608540 | 17.632607 |

Five-repeat mean +/- sample SD: **20.349469 +/- 5.722416 s/case**.

Environment: `NVIDIA GeForce RTX 3060 Laptop GPU`, Python `3.11.15`, PyTorch `2.5.1+cu121`, CUDA `12.1`.
