# Paper-result mapping

The released files below are the numerical and asset sources of truth for
v1.1.9 paper outputs.

| Paper content | Frozen or checksum-tracked source | Rebuilt output |
|---|---|---|
| Table 1: experimental configuration | `configs/main_cfg.py`, frozen method configs, corrected mechanism summary | `table1_configuration.csv` |
| Table 2: compared methods and fairness | `results/main/baseline_fairness.csv` | `table2_fairness.csv` |
| Table 3: overall comparison | `results/main/overall_comparison.csv` | `table3_overall.csv` |
| Table 4: optimizer-matched control | `results/supplementary/optimizer_matched_control_summary.csv` from the independent control target pool | `table4_matched_control.csv` |
| Table 5: component ablation | `results/main/component_ablation.csv` | `table5_ablation.csv` |
| Runtime and model complexity (public supplementary layer) | `results/supplementary/repeated_runtime_summary.csv`, selected-model complexity | broader public CSV/LaTeX outputs; not a manuscript Table 6 |
| Fig. 1: scenario | `paper_assets/current_figures/fig1.pdf` and `.png` | checksum-verified copy |
| Fig. 2--5: method, bank, filtering, adaptation/selection | `paper_assets/current_figures/fig2`--`fig5` PDF/PNG assets | checksum-verified copies |
| Fig. 6: paired instantiation | locked proposed-method and PT+FT records | `fig6_paired_instantiation_data.csv` |
| Fig. 7: heterogeneity | `tableS1_robustness_details.csv` | `fig7_heterogeneity_data.csv` |
| Fig. 8: filtering and selection | locked proposed-method records | candidate-filtering and architecture-selection CSVs |
| Fig. 9: bank/steps/threshold | bank-size, adaptation-trajectory, and sanitized margin results | three Fig. 9 CSVs |
| Fig. 10: normalized target-side trade-off | overall comparison plus repeated target-side runtime | `fig10_deployment_tradeoff_data.csv`; labels distinguish target-side time, parameter count, and estimated operation count |
| Fig. 11: complexity--performance map | locked architecture coverage plus frozen architecture complexity | `fig11_architecture_complexity_data.csv` |
| Fig. 12(a): controlled source scale | `tableS2_controlled_source_scale.csv` | source-scale panel |
| Fig. 12(b): seed and Alibaba case distributions | frozen 240 source-seed and 80 anonymized Alibaba evaluation records | `fig12_case_level_gains.csv` and `fig12_group_summary.csv` |

The exact five-table manuscript layer is generated under `tables/paper_csv/`
and `tables/paper_latex/`. The broader checked presentation layer remains
under `tables/csv/`, `tables/latex/`, and `results/figure_data/`. Cross-file
values are derived before rounding. The public proposed runtime is
`5.676 +/- 0.059 s`; the earlier one-pass diagnostic remains historical
provenance only.

Table 4 uses a disjoint optimizer-control target pool. The controlled
source-scale, source-seed, and Alibaba studies are separate diagnostic pools;
none is used to tune a reported method.

Release v1.1.9 changes the revised manuscript, Fig. 10 presentation, reporting
code, and public documentation only. It does not change frozen configurations, model
weights, seeds, data splits, candidate bank, optimizer, adaptation budget,
selection threshold, or core numerical results.
