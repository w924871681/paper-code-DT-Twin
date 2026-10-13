# Reproduction routes for the 2026-10-13 current paper

Start at [the current manuscript](paper/current/) and its separate
[Supplementary §S7.4 correction Release entry](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/manuscript-suppfix-20261013).
This manuscript-only correction updates one public-availability sentence in
Supplementary §S7.4 and keeps the main source/PDF from the
[previous Data Availability revision](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/manuscript-final-20261013).
It introduces no new experiment or recalibration. Compilation and download acceptance are
recorded in [publication status](publication/20261013/MANUSCRIPT_PUBLICATION_STATUS.md).
The manuscript attachments in the expanded evidence Release are retained as
the earlier version. The original synthetic main
study remains anchored to the unchanged [v1.2.7 frozen release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/v1.2.7)
and its commit `b679181b3133ab9c3058afcde421d36380001f14`.

The [2026-10-13 research-assets archive](https://github.com/w924871681/paper-code-DT-Twin/releases/download/evidence-full-20261013/MSA_DTI_R5_Bitbrains_ResearchAssets_PUBLIC_PATHSAFE_20261013.zip) has separate `r5/`, `bitbrains/`,
`code/`, and `audit/` paths. From an extracted copy, run
`python verify_core_results.py` with NumPy to recompute the saved development,
calibration and held-out prediction metrics and bootstrap statistics. This
verification does **not** train models. See [R5](reproducibility/r5/README.md)
and [Bitbrains](reproducibility/bitbrains/README.md) for the scope of available
inputs and the additional steps needed for from-source reproduction.

The separately published [corrected Alibaba archive](https://github.com/w924871681/paper-code-DT-Twin/releases/download/evidence-full-20261013/MSA_DTI_Alibaba_CausalCorrected_PUBLIC_PATHSAFE_V2_20261013.zip) includes
`README_REPRODUCE.md`, the fixture-tested `audit/rebuild_raw_prefix.py`,
protocols, source checkpoints, corrected calibration, held-out results and
figures. See [corrected Alibaba](reproducibility/alibaba_corrected/README.md).
Its original third-party raw data must be obtained separately.

Scientific limits: R5's historical R2 development-pool RNG provenance is
`UNRESOLVED_HISTORICAL_RNG_PROVENANCE`; Bitbrains is in-domain source-trained
evaluation, not zero-shot transfer; corrected Alibaba failed all six five-gate
calibration margins and deployed the adapted reference fallback. The
publication process did not retrain or recalibrate any experiment.
