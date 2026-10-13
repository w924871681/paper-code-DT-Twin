# MSA-DTI: 2026-10-13 evidence index

This directory separates manuscript/evidence updates from the **original frozen experimental code**. Git tag `v1.2.7` continues to refer to commit `b679181b3133ab9c3058afcde421d36380001f14`. This evidence branch does **not** modify that tag, the original Release assets, or the underlying model results.

## Synthetic main-study calibration — publicly accessible now

- [Six-margin calibration table](synthetic_main_six_margin_calibration.csv)
- [Frozen selector source of truth](https://github.com/w924871681/paper-code-DT-Twin/blob/b679181b3133ab9c3058afcde421d36380001f14/results/audited_provenance/anchor_safe_selector_manifest.json), key `margin_grid_results`.
- 20 calibration centers, 80 H/K cases; empirical selection criteria: all-case harm <=5%; two mean check-MSE gains >=3%; both center-cluster 95% CI lower bounds >0.
- Margins 0.05 and 0.075 fail **only** the harm-rate criterion (6.25%). Margins 0.10, 0.125, 0.15 and 0.20 satisfy all five checks; **0.10** is the smallest eligible margin. This table reports existing frozen results; no recalibration was run.

## R5 synthetic contribution diagnostic — evidence summary

- Mean case-relative MSE improvement over a development-fixed model: **13.4803%** (95% center-cluster CI **[6.3856%, 21.0963%]**); 20 centers, 80 cases.
- **Limitation:** original R2 screening development-pool seeds/raw arrays were not recoverable. Status: `UNRESOLVED_HISTORICAL_RNG_PROVENANCE`. Treat as provenance-qualified supplementary/exploratory evidence, not an independently verified historical confirmatory test.

## Bitbrains real workload — evidence summary

- 40 held-out VMs, 160 cases; mean case-relative MSE gain over PT+FT **32.7045%** (95% VM-cluster CI **[7.6721%, 51.2506%]**).
- Held-out harmful selection 11/160 = **6.875%**, above the empirical 5% calibration criterion. The five-gate calibration selected tau=0.05 on separate calibration VMs; it is **not** a population risk guarantee.
- Aggregate mean-MSE reduction **8.0879%** is a different estimand from the case-relative mean 32.7045%.
- This is a fresh **in-domain** source-trained Bitbrains evaluation; it is **not** zero-shot transfer of frozen synthetic/Alibaba weights.

## Published light audit archive — verified public download

- [Evidence-only Release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-r5-bitbrains-20261013); tag target commit [`1adfa6231f990f8c572709fde885fac3787bd6ed`](https://github.com/w924871681/paper-code-DT-Twin/commit/1adfa6231f990f8c572709fde885fac3787bd6ed). This is separate from `v1.2.7`.
- [Download the public R5/Bitbrains light audit ZIP](https://github.com/w924871681/paper-code-DT-Twin/releases/download/evidence-r5-bitbrains-20261013/MSA_DTI_R5_Bitbrains_LightAudit_PUBLIC_REDACTED_20261013.zip) (6,063,106 bytes; SHA-256 `d3ff00a408ef65422dd23d0a28811b31e3faa179510f7781f9824394f9865789`; 620 ZIP members, CRC pass). This exact URL was obtained from the GitHub Release asset record and successfully downloaded without GitHub credentials; the downloaded bytes matched the local publication copy.
- The public ZIP is a separately named derivative of the privately supplied ZIP (original SHA-256 `f4ee388f67e2f7adf9d5791edea169e86ed9316246fe08912e9e2ea0aa597e14`; 9,000,095 bytes). The Windows local account segment was redacted in three historical JSON audit records. See `PUBLICATION_REDACTIONS.md` and the regenerated public `MANIFEST_SHA256.json` inside the ZIP. Scientific arrays, CSVs, protocol locks and verification code are unchanged. `REVIEW_DELIVERY_MANIFEST.json` is a historical manifest of the original private records and retains their pre-redaction hashes; use the public manifest for the derivative's member hashes.
- Run `python verify_core_results.py` with NumPy from the extracted archive root. It recomputes saved prediction/target metrics, development mappings, calibration, selector choices and cluster-bootstrap statistics without training. The public package passed this audit for 80 R5 cases (240 prediction/truth pairs) and 160 Bitbrains cases (960 pairs).

The ZIP excludes raw Bitbrains VM traces, original heavy synthetic/Bitbrains inputs, checkpoint weights, training caches and lengthy logs. It supports independent recalculation of **saved** core results, but cannot independently reproduce source-model training, regenerate all raw-trace windows or settle R5's historical development-pool RNG provenance. Excluded original input hashes are recorded as provenance references, not as proof that those inputs are inside the ZIP.

## Dataset attribution

[Bitbrains GWA-T-12](https://atlarge-research.com/gwa-t-12/) is the original raw workload source. Acknowledge Bitbrains IT Services Inc. and cite Shen, van Beek and Iosup, *Statistical Characterization of Business-Critical Workloads Hosted in Cloud Datacenters* (CCGrid 2015), as requested by the source. The original third-party fastStorage VM trace archive and full derived training windows are not redistributed here; obtain raw traces from the official source if a from-raw-data audit is required. The light ZIP contains only audit metadata and the saved prediction/truth arrays needed to recalculate reported held-out metrics.

The latest manuscript revision (including Bitbrains and R5 diagnostics) has a separate local LaTeX artifact and is **not** equivalent to the automatically generated source archive of the original v1.2.7 tag.
