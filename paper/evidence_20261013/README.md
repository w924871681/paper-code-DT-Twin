# MSA-DTI: 2026-10-13 evidence index

This directory separates manuscript/evidence updates from the **original frozen experimental code**. Git tag `v1.2.7` continues to refer to commit `b679181b3133ab9c3058afcde421d36380001f14`. This evidence branch does **not** modify that tag, the original Release assets, or the underlying model results.

## Synthetic main-study calibration — publicly accessible now

- [Six-margin calibration table](synthetic_main_six_margin_calibration.csv)
- [Frozen selector source of truth](https://github.com/w924871681/paper-code-DT-Twin/blob/b679181b3133ab9c3058afcde421d36380001f14/results/audited_provenance/anchor_safe_selector_manifest.json), key `margin_grid_results`.
- 20 calibration centers, 80 H/K cases; empirical selection criteria: all-case harm <=5%; two mean check-MSE gains >=3%; both center-cluster 95% CI lower bounds >0.
- Margins 0.05 and 0.075 fail **only** the harm-rate criterion (6.25%). Margins 0.10, 0.125, 0.15 and 0.20 satisfy all five checks; **0.10** is the smallest eligible margin. This table reports existing frozen results; no recalibration was run.

## R5 synthetic contribution diagnostic — evidence summary

- Mean case-relative MSE improvement over a development-fixed model: **13.4803%** (95% center-cluster CI **[6.3856%, 21.0963%]**); 20 centers, 80 cases.
- **Limitation:** original R2 screening development-pool seeds/raw arrays were not recoverable. Status: `R5_UNRESOLVED_PROVENANCE`. Treat as provenance-qualified supplementary/exploratory evidence, not an independently verified historical confirmatory test.

## Bitbrains real workload — evidence summary

- 40 held-out VMs, 160 cases; mean case-relative MSE gain over PT+FT **32.7045%** (95% VM-cluster CI **[7.6721%, 51.2506%]**).
- Held-out harmful selection 11/160 = **6.875%**, above the empirical 5% calibration criterion. The five-gate calibration selected tau=0.05 on separate calibration VMs; it is **not** a population risk guarantee.
- Aggregate mean-MSE reduction **8.0879%** is a different estimand from the case-relative mean 32.7045%.
- This is a fresh **in-domain** source-trained Bitbrains evaluation; it is **not** zero-shot transfer of frozen synthetic/Alibaba weights.

## Complete light audit archive — publication status

As of creation of this index, the **8.6 MB** source-provided `MSA_DTI_R5_Bitbrains_LightAudit_20261013.zip` archive has **not yet been uploaded to this GitHub repository/Release**. Do not cite this index as a working download for the full R5/Bitbrains saved predictions and reproducibility scripts until the archive is uploaded and anonymous download/hash verification succeeds.

Expected SHA-256 of the locally verified source-provided archive:
`f4ee388f67e2f7adf9d5791edea169e86ed9316246fe08912e9e2ea0aa597e14`

The audit archive provides saved per-case predictions/targets, verification scripts, development candidate maps, selector locks and bootstrap samples, but **not** the original Bitbrains raw trace or checkpoint weights. Full from-raw-data training reproduction is beyond the light archive.

## Dataset attribution

Bitbrains GWA-T-12: https://atlarge-research.com/gwa-t-12/ . The official source asks users to acknowledge Bitbrains IT Services Inc. and cite Shen, van Beek and Iosup, *Statistical Characterization of Business-Critical Workloads Hosted in Cloud Datacenters* (CCGrid 2015). Original third-party raw VM traces are not redistributed here.

The latest manuscript revision (including Bitbrains and R5 diagnostics) has a separate local LaTeX artifact and is **not** equivalent to the automatically generated source archive of the original v1.2.7 tag.
