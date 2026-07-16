# Paper-result mapping

The following released files are the numerical sources of truth for public
paper outputs.

| Paper content | Frozen or checksum-tracked source | Rebuilt output |
|---|---|---|
| Experimental configuration | `configs/main_cfg.py`, main evaluation/experiment configs, and corrected mechanism summary | exact revised-paper `table1_configuration.csv` |
| Compared methods and fairness | `results/main/baseline_fairness.csv` | exact revised-paper `table2_fairness.csv` |
| Overall accuracy and complexity | `results/main/overall_comparison.csv` | exact revised-paper `table3_overall.csv`; public Table 3; 3D figure data |
| Component ablation | `results/main/component_ablation.csv` | exact revised-paper `table4_component_analysis.csv`; public Table 4 |
| Repeated target-side time | `results/supplementary/repeated_runtime_summary.csv` | exact revised-paper Table 5; runtime columns and 3D marker sizes |
| Optimizer-matched control | `results/supplementary/optimizer_matched_control_summary.csv` | exact revised-paper `table6_matched_control.csv` |
| Selection mechanism | corrected `results/main/mechanism_and_cost.csv` | public Table 5a |
| Horizon/support and center-type robustness | `results/main/horizon_support_robustness.csv`, `center_type_robustness.csv` | robustness table and radar data |
| Controlled source-center scale | `results/robustness/controlled_source_scale.csv` | Table S2 and source-scale figure data |
| Source-initialization seeds | `results/robustness/source_bank_seed.csv` | Table S3, generalization table, and forest data |
| Alibaba semi-real evaluation | `results/main/alibaba_semi_real.csv` and `results/robustness/alibaba_oracle_diagnostics.csv` | Table S6, generalization output, and forest data |
| Architecture coverage | corrected `results/robustness/architecture_coverage.csv` | Table S7 |
| Bank size | `results/main/bank_size.csv` | Table S4 |

The exact six-table manuscript layer is generated under
`tables/paper_csv/` and `tables/paper_latex/`. The broader presentation layer is
under `results/figure_data/`. Cross-file values are derived before rounding.
In particular, the public proposed runtime is `5.676 +/- 0.059 s`, not the
earlier one-pass diagnostic retained in historical provenance.

Some immutable audits and frozen source schemas retain historical identifiers.
See `results/audited_provenance/SANITIZATION_MANIFEST.json` and
`NUMERICAL_CORRECTIONS.json` for the exact integrity boundary.

