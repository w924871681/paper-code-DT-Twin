# MSA-DTI: 2026-10-13 evidence index

This directory separates manuscript/evidence updates from the **original frozen experimental code**. Git tag `v1.2.7` continues to refer to commit `b679181b3133ab9c3058afcde421d36380001f14`. This evidence branch does **not** modify that tag, the original Release assets, or the underlying model results.

## Current manuscript and expanded evidence

The [current manuscript](../current/) retains the previously published Data Availability revision of the main paper and corrects one public-availability sentence in Supplementary §S7.4. The [Supplementary correction Release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/manuscript-suppfix-20261013) is separate from the experiment releases; see [publication acceptance status](../../publication/20261013/MANUSCRIPT_PUBLICATION_STATUS.md) and the [Supplementary correction closure report](../../publication/20261013/FINAL_SUPPLEMENTARY_CLOSURE_REPORT.md).

The new Release's actual assets are the [complete LaTeX ZIP](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-suppfix-20261013/MSA_DTI_Final_Publication_20261013_SuppFix.zip), [unchanged main PDF](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-suppfix-20261013/main.pdf), [corrected Supplementary PDF](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-suppfix-20261013/supplementary.pdf), and [SHA-256 list](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-suppfix-20261013/SHA256SUMS.txt). All four anonymous downloads returned HTTP 200 and matched local sizes and hashes; the 32-member ZIP passed CRC. The ZIP is 7,076,672 bytes, SHA-256 `551411789fab9334a03c29d9931294aa9a10a0597038a1e6e201f9e774a7356f`. Fresh after-publication comparisons confirmed the `v1.2.7` Tag and all 30/1/9/4 protected attachments of the four prior Releases unchanged.

The [previous Data Availability manuscript Release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/manuscript-final-20261013) retains its actual public assets: [previous complete LaTeX ZIP](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-final-20261013/MSA_DTI_Final_Publication_20261013.zip), [main PDF retained in the current version](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-final-20261013/main.pdf), [previous Supplementary PDF](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-final-20261013/supplementary.pdf), and [previous SHA-256 list](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-final-20261013/SHA256SUMS.txt). All four anonymous downloads for that previous version matched local sizes and hashes; its ZIP passed CRC. The [previous closure report](../../publication/20261013/FINAL_PUBLICATION_CLOSURE_REPORT.md) preserves that acceptance record.

The [dated evidence-only Release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-full-20261013) preserves the pre-Data-Availability-revision manuscript project and standalone TeX/PDF attachments, together with the expanded experiment assets. Its actual GitHub asset records give these public downloads:

- [Earlier manuscript project ZIP, before the Data Availability revision](https://github.com/w924871681/paper-code-DT-Twin/releases/download/evidence-full-20261013/MSA_DTI_Current_Manuscript_PUBLIC_20261013.zip) — 7,049,373 bytes; SHA-256 `e50f18b2dfd0787ead977d16675c45294f79328424d4615d2cbc0fa575df99e2`.
- [R5 and Bitbrains research-assets ZIP](https://github.com/w924871681/paper-code-DT-Twin/releases/download/evidence-full-20261013/MSA_DTI_R5_Bitbrains_ResearchAssets_PUBLIC_PATHSAFE_20261013.zip) — 75,516,267 bytes; SHA-256 `7fe5c029027320866d3f2b12655d024c38b0954fcaede859bed137fc504eea4c`.
- [Causal-corrected Alibaba research-assets ZIP](https://github.com/w924871681/paper-code-DT-Twin/releases/download/evidence-full-20261013/MSA_DTI_Alibaba_CausalCorrected_PUBLIC_PATHSAFE_V2_20261013.zip) — 8,936,109 bytes; SHA-256 `41ada3a05a4896045317134177a73c23007396529f68e6515405b6f8e82c5b60`.
- [Release asset manifest](https://github.com/w924871681/paper-code-DT-Twin/releases/download/evidence-full-20261013/ASSET_MANIFEST.json) and [SHA-256 list](https://github.com/w924871681/paper-code-DT-Twin/releases/download/evidence-full-20261013/SHA256SUMS.txt).

The expanded R5/Bitbrains archive contains the earlier light-audit evidence, R5 prepared synthetic data and checkpoints, Bitbrains checkpoints, code, configuration, saved predictions/truth and statistical records. The corrected Alibaba archive contains source/preprocessing code, checkpoints, calibration, selector lock and saved held-out records. Historical absolute machine paths were redacted in separately named public derivatives; see their internal path-redaction records and regenerated manifests. For reproduction scope and exclusions, see [R5](../../reproducibility/r5/README.md), [Bitbrains](../../reproducibility/bitbrains/README.md), [Alibaba](../../reproducibility/alibaba_corrected/README.md) and the [asset inventory](../../publication/20261013/PUBLICATION_ASSET_INVENTORY.csv).

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

The current manuscript entry is `paper/current/`; its Supplementary correction uses a separate manuscript-only Release. The previous Data Availability manuscript Release, manuscript attachments in the expanded evidence Release, and the automatically generated source archive of the original `v1.2.7` tag remain historical. The experiment releases and all previous attachments are preserved without replacement.
