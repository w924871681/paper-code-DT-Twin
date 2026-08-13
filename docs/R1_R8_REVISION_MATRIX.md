# R1--R8 revision matrix

This matrix records the evidence used for the post-review revision. The
scientific protocol and frozen headline results are unchanged.

| Item | Revision action | Evidence used | Status |
| --- | --- | --- | --- |
| R1: method increment and optimization object | Added an explicit comparison with frozen-bank selection, PT+FT, NAS, and meta-NAS; separated cross-architecture adaptation from the relative-margin rule; moved the optimizer-matched diagnostic into the main paper. | Main Sections 1, 5.2, and 5.5; Supplementary Tables S1--S3. | Closed. |
| R2: candidate-bank robustness | Repeated the complete 66-configuration rule over three screening samples and evaluated each resulting list on a fourth untouched pool. Reported retention frequency, bank sizes, Jaccard similarity, validation-only selection frequencies, paired center-cluster intervals, and harmful rates. The result is explicitly negative: screening is sample-sensitive, so the frozen bank is not claimed to be uniquely recoverable. | `results/robustness/r2_screening_stability.json`; `r2_screening_stability.csv`; Main Section 5.3; Supplementary Section S7.2. | Closed by experiment and claim reduction. |
| R3: reliability statistics | Added the center-cluster bootstrap interval for the paired MSE reduction, the center-cluster interval for the all-case harmful-selection rate, and the interpretation of the 5% calibration tolerance. | `results/audited_provenance/main_evaluation_analysis.json`; `results/figure_data/fig6_paired_instantiation_data.csv`; 4000-repetition center-cluster bootstrap. | Closed for the frozen evaluation. |
| R4: baseline fairness | Expanded the H-Meta-NAS-based search protocol and moved the SGD/MSE/50 optimizer-matched comparison into the main paper. | Frozen method configurations; `results/supplementary/optimizer_matched_control_summary.csv`. | Closed with a stated boundary: initializations and selection rules remain method-specific. |
| R5: deployment evidence | Added per-architecture CPU/GPU latency, serialized state size, and peak GPU allocation; summarized ranges and limitations in the main paper. | `results/pre_submission_enhancements/hosting/hosting_profile_summary.csv` and `hosting_profile_correlations.csv`. | Closed by measurement plus scope reduction. No hardware guarantee or cross-platform claim is made. |
| R6: DT/JNCA positioning | Reframed the title, abstract, introduction, system model, and conclusion around the predictive-model component of a DT and linked prediction to monitoring and resource-management decisions. | Revised manuscript Sections 1, 3, and 6. | Closed. |
| R7: external recalibration failure | Defined calibrated-deployment fallback to the adapted reference when no margin is eligible; retained the frozen Alibaba result only as a transfer audit. | Main Sections 4.7 and 5.6; Supplementary Sections S2.2 and S7.2. | Closed. |
| R8: metadata | Retained the existing metadata checklist and did not invent author, affiliation, CRediT, funding, ORCID, or contact information. | `AUTHOR_METADATA_REQUIRED.md`. | Open pending author-supplied values or confirmation of an anonymous-review workflow. |

## Experiment decision

The R2 experiment is complete. The original screen (centers 900--919) and two
new screens (1120--1139 and 1140--1159) use the same 66 configurations,
reference, retention rule, source recipe, and target recipe. Evaluation uses
the separate centers 1160--1179. All four oracle files report `test_used=false`,
and all three new diagnostic audits pass.

The retained sets are not stable: their sizes are 6, 0, and 4, and the two
new-set Jaccard similarities to the frozen set are 0 and 0.429. This result is
used to reduce the claim and motivate reference protection; it is not used to
retune the frozen headline method after inspecting the main test set.
