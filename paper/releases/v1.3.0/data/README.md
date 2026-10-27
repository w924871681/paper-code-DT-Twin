# Numerical records

All error columns are in their original numeric units unless a column name
explicitly contains "percent" or "pct". Manuscript tables and chart labels may
display scaled units; this changes labels, not the stored values.

| File | Role |
|---|---|
| individual_results.csv | 2,880 task records: eight methods × three budgets × 120 tasks |
| baseline_summary.csv | Exact method/budget aggregates and paired uncertainty summaries |
| overall.csv | Four medium-budget metrics for Figure 5 |
| paired.csv | 120 paired MSA-DTI/PT+FT tasks; selection categories are relative to adapted A55 |
| subgroups.csv | Task-relative gains and paired-VM intervals for Figure 7 |
| source_sensitivity.csv | Six source-pool/seed conditions for Figure 8 and Table S8 |
| filtering.csv, selection.csv | Candidate counts and record-level selection frequencies for Figure 9 |
| ablations.csv | Exact medium-budget values for the seven component-control rows |
| ablation_individual_results.csv | 2,160 task-level rows for six component variants at three budgets |
| candidate_subset.csv | Nested candidate subsets and independently calibrated margins |
| adaptation_updates.csv | Update-count sensitivity and agreement with the 50-update selections |
| margin_calibration.csv | Seven margin settings on 80 calibration tasks |
| matched_controls.csv | Matched-optimizer and shared-shortlist comparisons |
| preselection_sensitivity.csv, preselection_pool_sizes.csv | Development-pool architecture-preselection sensitivity |
| cost.csv | Display aggregates for model complexity and target-pipeline timing |
| pipeline_timing.csv | 96 method/condition summaries, each based on five timed repetitions |
| inference_latency.csv | CPU/GPU forward-pass latency and model complexity |
| data_roles.json | Disjoint source/development/calibration/evaluation identities: 20/20/20/30 |
| target_windows.csv | Native record offsets and causal selection geometry for calibration/evaluation |
| source_normalization.json | Source-fitted feature scales |
| candidate_architectures.json | Seven model records, architecture definitions, and horizon-specific resource counts |
| source_checkpoint_identities.json | Fourteen source checkpoint hashes and model identities |
| reference_selection.csv | Development assessment, universal feasibility, and reference designation |
| figure_layout_checks.json | Automated experimental-chart text-bound checks |

Record aliases: PT_A57_ref denotes A57-PT; C1_A57_pair denotes A57-C1.
A56, A57-C1, and A57-PT share an executable one-layer GRU-32 structure but
have different source-trained weights. Each has a separate checkpoint for H = 1
and H = 4. ARCH_57 in fixed-model baseline output denotes architecture A57.

In paired.csv, proposed_* columns contain MSA-DTI results. In
individual_results.csv, harm_vs_reference compares with that method's
reference; it is undefined for methods without a reference-based policy.
Reference retention contributes zero to MSA-DTI's harm denominator, which is
all 120 tasks. CVaR90_case is the 12-task tail metric used in the article;
columns explicitly marked CVaR90_VM_supplement are a different VM-level
aggregation and are not used in the main table.

target_windows.csv uses zero-based indices relative to native_start.
The last validation label is observed by decision_record; forecast targets
begin at the following record. B counts rolling forecast origins.

In matched_controls.csv, common_A55 and common_A57 identify the
reference-containing, task-specific shortlists. The corresponding
validation-minimum variants use the same source candidates and adaptation.

initialized_candidates_per_case in filtering.csv is the bank size before
feasibility filtering. logical_adaptations in the main task records and
actual_adaptations_per_run in the timing records describe their respective
execution accounting; the latter is seven for every MSA-DTI timing setting.

Statistical intervals are descriptive paired-VM percentile intervals. They
are not simultaneous confidence statements across all comparisons.
