# Figure reproduction

## Canonical command

From the repository root:

```powershell
python .\scripts\generate_paper_outputs.py
```

This is the only formal reviewer entry point. The maintained plotting
implementation is `reporting/final_figures.py`.

## Source map

| Figure | Source | Reconstruction policy |
|---|---|---|
| Fig. 1--5 | `paper_assets/current_figures/` | Copy byte-for-byte after SHA-256 verification |
| Fig. 6 | `fig6_paired_instantiation_data.csv` | All 80 paired held-out cases |
| Fig. 7 | `fig7_heterogeneity_data.csv` | Seven precomputed center-cluster intervals |
| Fig. 8 | `fig8_candidate_filtering_data.csv`, `fig8_architecture_selection_data.csv` | Counts and selection rates by complexity-limit tier |
| Fig. 9 | `fig9_bank_size_data.csv`, `fig9_adaptation_steps_data.csv`, `fig9_margin_data.csv` | Diagnostic/development studies only |
| Fig. 10 | `fig10_deployment_tradeoff_data.csv` | `100 × lowest raw value / method value`; explicit target-side time, parameter-count, and estimated-operation-count axes |
| Fig. 11 | `fig11_architecture_complexity_data.csv` | Marker area encodes selected-case count |
| Fig. 12 | `tableS2_controlled_source_scale.csv`, `fig12_case_level_gains.csv`, `fig12_group_summary.csv` | Raw values retained; four Alibaba cases clipped only on the plot |

All paths in the table are below `results/figure_data/`.

## Acceptance checks

The generator:

- emits vector PDFs without Type 3 fonts or embedded raster panels;
- emits 600-DPI color PNGs and grayscale previews;
- checks text bounds and adjacent tick-label overlap;
- verifies Fig. 1--5 dimensions and checksums;
- records hashes for every source and output;
- does not train models, adapt candidates, select candidates, or recompute
  confidence intervals.

Fig. 6 categories are post-selection test-MSE audit labels. The same
categories appear in both panels and do not affect selection. Fig. 9 held-out
test cases are not used to select the retained architecture count, update
budget, or threshold.
