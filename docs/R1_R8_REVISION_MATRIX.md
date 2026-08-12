# R1--R8 revision matrix

This matrix records the evidence used for the post-review revision. The
scientific protocol and frozen headline results are unchanged.

| Item | Revision action | Evidence used | Status |
| --- | --- | --- | --- |
| R1: method increment and optimization object | Added an explicit comparison with frozen-bank selection, PT+FT, NAS, and meta-NAS; separated cross-architecture adaptation from the relative-margin rule; moved the optimizer-matched diagnostic into the main paper. | Main Sections 1, 5.2, and 5.5; Supplementary Tables S1--S3. | Closed. |
| R2: candidate-bank robustness | Added the three-seed source-initialization results to the main paper and clarified that the screened architecture list is fixed. | `results/robustness/source_bank_seed.csv`; Supplementary Section S7.1. | Partially closed. Complete 66-configuration re-screening on independent screening pools has not been run. |
| R3: reliability statistics | Added the center-cluster bootstrap interval for the paired MSE reduction, the center-cluster interval for the all-case harmful-selection rate, and the interpretation of the 5% calibration tolerance. | `results/audited_provenance/main_evaluation_analysis.json`; `results/figure_data/fig6_paired_instantiation_data.csv`; 4000-repetition center-cluster bootstrap. | Closed for the frozen evaluation. |
| R4: baseline fairness | Expanded the H-Meta-NAS-based search protocol and moved the SGD/MSE/50 optimizer-matched comparison into the main paper. | Frozen method configurations; `results/supplementary/optimizer_matched_control_summary.csv`. | Closed with a stated boundary: initializations and selection rules remain method-specific. |
| R5: deployment evidence | Added per-architecture CPU/GPU latency, serialized state size, and peak GPU allocation; summarized ranges and limitations in the main paper. | `results/pre_submission_enhancements/hosting/hosting_profile_summary.csv` and `hosting_profile_correlations.csv`. | Closed by measurement plus scope reduction. No hardware guarantee or cross-platform claim is made. |
| R6: DT/JNCA positioning | Reframed the title, abstract, introduction, system model, and conclusion around the predictive-model component of a DT and linked prediction to monitoring and resource-management decisions. | Revised manuscript Sections 1, 3, and 6. | Closed. |
| R7: external recalibration failure | Defined calibrated-deployment fallback to the adapted reference when no margin is eligible; retained the frozen Alibaba result only as a transfer audit. | Main Sections 4.7 and 5.6; Supplementary Sections S2.2 and S7.2. | Closed. |
| R8: metadata | Retained the existing metadata checklist and did not invent author, affiliation, CRediT, funding, ORCID, or contact information. | `AUTHOR_METADATA_REQUIRED.md`. | Open pending author-supplied values or confirmation of an anonymous-review workflow. |

## Experiment decision

The revision reuses frozen results and adds only a center-level statistical
reanalysis. The optimizer-matched table was moved into the main paper, while
the full hardware table was added to the supplementary material and summarized
in the main paper. Repeating the main experiment or adding a second hardware
device is not required for the present scoped claims.

One genuinely new experiment remains advisable for full closure of R2:

1. preregister at least three independent architecture-screening pools;
2. keep the 66-configuration space, A57 reference, retention rule, source
   recipe, and target protocol fixed;
3. reconstruct the bank for every screening pool without using the main
   held-out centers;
4. evaluate the reconstructed banks on a separate untouched robustness pool;
5. report per-configuration retention frequency, bank-size distribution,
   Jaccard similarity to the frozen bank, final selected-architecture
   frequency, paired MSE reduction with a center-cluster interval, and harmful
   selection rate.

This experiment should be presented as a robustness study. It must not be
used to retune the frozen headline method after inspecting the main test set.
