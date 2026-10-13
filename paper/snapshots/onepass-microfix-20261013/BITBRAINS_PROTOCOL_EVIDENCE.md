# Bitbrains protocol evidence for the one-pass S2 microfix

Status: **ALL_REQUIRED_S2_FIELDS_CONFIRMED_FROM_FROZEN_RECORDS**. This is implementation/provenance extraction under the adopted `IMPLEMENTATION_TASKBOOK.md`, not a new academic review. No author research script was executed; no training, parameter selection, new filtering, preprocessing, feature/window generation, or array regeneration was performed. `main.tex` and `supplementary.tex` were not edited by this extraction.

## Source binding and active-versus-draft decision

Preferred root: `D:/审稿/MSA_DTI_R5_Bitbrains_PathSafe_Verification_20261013/MSA_DTI_R5_Bitbrains_ResearchAssets_PUBLIC_PATHSAFE_20261013`. Paths in the fact ledger below are relative to that root unless explicitly marked task-output root.

Published asset: [frozen R5/Bitbrains path-safe ZIP](https://github.com/w924871681/paper-code-DT-Twin/releases/download/evidence-full-20261013/MSA_DTI_R5_Bitbrains_ResearchAssets_PUBLIC_PATHSAFE_20261013.zip), 75,516,267  bytes, SHA-256 `7fe5c029027320866d3f2b12655d024c38b0954fcaede859bed137fc504eea4c`. Existing GitHub snapshot at task-output root `GITHUB_PROTECTION_BEFORE.json`, key `releases[tag_name=evidence-full-20261013].assets[name=MSA_DTI_R5_Bitbrains_ResearchAssets_PUBLIC_PATHSAFE_20261013.zip]`, gives asset ID `636179851`, identical `browser_download_url`, `size=75516267`, and `digest=sha256:7fe5c029027320866d3f2b12655d024c38b0954fcaede859bed137fc504eea4c`. Snapshot SHA-256: `c4b0b97fa8f02c5871f6e247e35f1bf867631d76c284f4610c0d83677cfd8309`.

The active contract is the top-level `bitbrains/` manifest/code chain bound by `bitbrains/protocol_lock.json`, protocol ID `MSA_DTI_R4_R5_BITBRAINS_V1`, lock timestamp `2026-10-12T12:59:22.540734+00:00` before first forward. The historical `proposed` names/statuses describe pre-forward artifact creation, not a different current rule. The active data manifest binds the selected identity manifest, which binds the current raw schema manifest. Data, identity, and executable data/target/center API file hashes match the original lock.

`bitbrains/draft_cpu_le100_provenance/` is a historical CPU <= 100 draft (1,006 eligible; fixed 1800/600/300/300 segments). `bitbrains/draft_fixed60pct_partition_provenance/` is a historical no-upper-cap draft with the old fixed 1800/600/300/300 segments (1,082 eligible). Neither directory supplies facts for the S2 insertion. The final active rule allows finite nonnegative recorded CPU above 100 and uses support-length-anchored allocation. The active full diagnostics CSV independently tallies 1,250 VM rows and 1,082 eligibility=True rows **before** stable-ID ranking/selection.

The source qualification floor for eligibility is 50 complete windows for each H. The selected-source W100 construction additionally checks at least 100 origins (`bitbrains_data.py:298–301`) before sampling 100. These are different checks; the latter must not be substituted into the full-library eligibility definition.

`Bitbrains_Data_Identity_And_Causality.md` is a path-safe derivative: current SHA `d5bad7b831dd7a927affd458c2f97a61a0dde4cab428c0b85021045ca9e81b0d`, pre-redaction lock SHA `b050790fcbd79a0c551767a8683c01b40df9ed2f206513dbe49f04634cef9acc`. `MANIFEST_SHA256.json.path_redaction_original_sha256` and `.path_redaction_changed_members` explain one drive-prefix redaction. Specific new numbers therefore use unchanged code/manifests below as primary evidence. This documented path-only hash change does not conflict with the scientific protocol.

## Every proposed new quantitative or protocol item

All rows have status `CONFIRMED_FROZEN_RECORD`. Window tuples are actual window counts, not independent labeled endpoints. Repeated facts already in S7.5 (role VM sizes, recorded > 100 retention, source-only normalization, H/K meanings, results) are preserved and not re-explained in the proposed insertion.

| ID | Proposed new item | Relative source path | Field key / frozen code location | Original value / rule | Unit | Source SHA-256 | Status |
|---|---|---|---|---|---|---|---|
| E01 | Eligibility before stable-ID selection | `bitbrains/raw_schema_and_label_manifest.json` | `eligible_vm_count_for_proposed_contract` | 1082 | VMs | `d0bb8f51ed070ea10471ff32b657f7e06164ec597e2e88d8ac32684c94599eca` | CONFIRMED_FROZEN_RECORD |
| E02 | Required schema | `audit/profile_bitbrains_raw.py` | `SCHEMA and profile() lines73–79` | fixed 11 columns: Timestamp plus 10 raw metrics | columns | `8747dd00b7c4d2097deeb8d21a2a9a034a8761bc3d2edca1187a63bc7a2d3c06` | CONFIRMED_FROZEN_RECORD |
| E03 | Timestamp validity | `audit/profile_bitbrains_raw.py` | `profile() lines73–79` | all finite integer t with 1e9 <= t < 2e9; strictly increasing native sequence | Unix seconds | `8747dd00b7c4d2097deeb8d21a2a9a034a8761bc3d2edca1187a63bc7a2d3c06` | CONFIRMED_FROZEN_RECORD |
| E04 | Genuine CPU label validity | `audit/profile_bitbrains_raw.py` | `profile() lines90–107` | isfinite(cpu) & (cpu>=0); all H future labels wholly inside raw role segment | recorded percent; no upper bound | `8747dd00b7c4d2097deeb8d21a2a9a034a8761bc3d2edca1187a63bc7a2d3c06` | CONFIRMED_FROZEN_RECORD |
| E05 | Coverage threshold | `bitbrains/raw_schema_and_label_manifest.json` | `proposed_timeline.source; proposed_timeline.target; failure_reason_counts.fewer_than3000_post24h_records` | at least 3000 native records at/after first_timestamp + 86400 | records; seconds | `d0bb8f51ed070ea10471ff32b657f7e06164ec597e2e88d8ac32684c94599eca` | CONFIRMED_FROZEN_RECORD |
| E06 | Source eligibility floor | `bitbrains/raw_schema_and_label_manifest.json` | `proposed_timeline.qualification_floors.source_each_H` | 50 for each H=1,4 | complete windows per VM/horizon | `d0bb8f51ed070ea10471ff32b657f7e06164ec597e2e88d8ac32684c94599eca` | CONFIRMED_FROZEN_RECORD |
| E07 | Target eligibility floors | `bitbrains/raw_schema_and_label_manifest.json` | `proposed_timeline.qualification_floors` | support exactly K; validation 80; check 60; test 200 for every H/K | complete windows per VM/case | `d0bb8f51ed070ea10471ff32b657f7e06164ec597e2e88d8ac32684c94599eca` | CONFIRMED_FROZEN_RECORD |
| E08 | Input length | `bitbrains/data/bitbrains_dataset_manifest.json` | `L` | 96 | native records per window | `b65713aa68062cf005213a168e49493a04794f7a5e92bae4ffdc08c8d3ac634e` | CONFIRMED_FROZEN_RECORD |
| E09 | Source interval rule | `code/experiments/r4_r5/bitbrains_data.py` | `prepare() lines286–289` | records with t < t[0]+86400 | seconds from each VM first timestamp | `1d5a9d278471cf680c95f6858a7d6e11e3185bba62e55b82653e98682429f79e` | CONFIRMED_FROZEN_RECORD |
| E10 | Target interval rule | `code/experiments/r4_r5/bitbrains_data.py` | `prepare() lines330–337` | start=searchsorted(t,t[0]+86400,side='left'); retain first 3000 records | seconds; native records | `1d5a9d278471cf680c95f6858a7d6e11e3185bba62e55b82653e98682429f79e` | CONFIRMED_FROZEN_RECORD |
| E11 | Support raw length | `code/experiments/r4_r5/bitbrains_data.py` | `raw_segments() lines70–85` | 96+H+K-1 | native records | `1d5a9d278471cf680c95f6858a7d6e11e3185bba62e55b82653e98682429f79e` | CONFIRMED_FROZEN_RECORD |
| E12 | Remaining raw allocation | `code/experiments/r4_r5/bitbrains_data.py` | `raw_segments() lines70–85` | normalized .2:.1:.1 for validation/check/test; floor then largest fractional remainder, earlier segment wins tie | ratio; integer records | `1d5a9d278471cf680c95f6858a7d6e11e3185bba62e55b82653e98682429f79e` | CONFIRMED_FROZEN_RECORD |
| E13 | Channel value groups | `bitbrains/data/bitbrains_dataset_manifest.json` | `feature_channel_order_0based[0:12]` | 10 raw metrics in schema order, CPU recorded trailing 5 mean, CPU recorded diff 1 | 12value channels | `b65713aa68062cf005213a168e49493a04794f7a5e92bae4ffdc08c8d3ac634e` | CONFIRMED_FROZEN_RECORD |
| E14 | Mask group | `bitbrains/data/bitbrains_dataset_manifest.json` | `feature_channel_order_0based[12:24]` | corresponding 12 observed-valid masks in same value order | 12binary mask channels | `b65713aa68062cf005213a168e49493a04794f7a5e92bae4ffdc08c8d3ac634e` | CONFIRMED_FROZEN_RECORD |
| E15 | Trailing mean and difference | `code/experiments/r4_r5/bitbrains_data.py` | `make_features() lines138–189` | mean over current and past at most 5 filled CPU records; diff=current-minus-previous filled CPU | native-record lookback; CPU percent/100 | `1d5a9d278471cf680c95f6858a7d6e11e3185bba62e55b82653e98682429f79e` | CONFIRMED_FROZEN_RECORD |
| E16 | Gap channel | `bitbrains/data/bitbrains_dataset_manifest.json` | `feature_channel_order_0based[24]; time_gap` | native elapsed seconds /1200; first role record 0, no clipping | one channel; seconds/1200 | `b65713aa68062cf005213a168e49493a04794f7a5e92bae4ffdc08c8d3ac634e` | CONFIRMED_FROZEN_RECORD |
| E17 | Causal fill and mask rule | `code/experiments/r4_r5/bitbrains_data.py` | `make_features() lines138–189` | finite nonnegative raw values valid; invalid input forward-filled, initial 0; masks retain invalidity; mean mask all used CPU valid; diff mask current+previousCPU valid, first diff/mask 0 | values; binary masks | `1d5a9d278471cf680c95f6858a7d6e11e3185bba62e55b82653e98682429f79e` | CONFIRMED_FROZEN_RECORD |
| E18 | Role boundary reset | `bitbrains/data/bitbrains_dataset_manifest.json` | `causal_state_reset` | independently at every raw role boundary; no cross-role fill/smooth/diff/gap history | role boundary rule | `b65713aa68062cf005213a168e49493a04794f7a5e92bae4ffdc08c8d3ac634e` | CONFIRMED_FROZEN_RECORD |
| E19 | H1K10 actual window counts | `bitbrains/data/bitbrains_dataset_manifest.json` | `cases[H=1,K=10].roles.{support,validation,check,test}.selected_window_count` | [10, 1351, 628, 627] | windows per VM in ordered Support/Validation/Calibration Check/Held-out Test | `b65713aa68062cf005213a168e49493a04794f7a5e92bae4ffdc08c8d3ac634e` | CONFIRMED_FROZEN_RECORD |
| E20 | H1K20 actual window counts | `bitbrains/data/bitbrains_dataset_manifest.json` | `cases[H=1,K=20].roles.{support,validation,check,test}.selected_window_count` | [20, 1346, 625, 625] | windows per VM in ordered Support/Validation/Calibration Check/Held-out Test | `b65713aa68062cf005213a168e49493a04794f7a5e92bae4ffdc08c8d3ac634e` | CONFIRMED_FROZEN_RECORD |
| E21 | H4K10 actual window counts | `bitbrains/data/bitbrains_dataset_manifest.json` | `cases[H=4,K=10].roles.{support,validation,check,test}.selected_window_count` | [10, 1346, 624, 624] | windows per VM in ordered Support/Validation/Calibration Check/Held-out Test | `b65713aa68062cf005213a168e49493a04794f7a5e92bae4ffdc08c8d3ac634e` | CONFIRMED_FROZEN_RECORD |
| E22 | H4K20 actual window counts | `bitbrains/data/bitbrains_dataset_manifest.json` | `cases[H=4,K=20].roles.{support,validation,check,test}.selected_window_count` | [20, 1342, 621, 621] | windows per VM in ordered Support/Validation/Calibration Check/Held-out Test | `b65713aa68062cf005213a168e49493a04794f7a5e92bae4ffdc08c8d3ac634e` | CONFIRMED_FROZEN_RECORD |
| E23 | Source observed first-to-last span | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/872.csv` | `recorded timestamp at frozen source bounds[0,288): t[287]-t[0]` | 1376400953-1376314846=86107 (same for all 20 selected source VMs) | seconds | `ec215224fe0e23014f0d35d272249a346aa1a0b7958504bf52e9b5f78ef5ba07` | CONFIRMED_FROZEN_ORIGINAL_ZIP_RECORD |
| E24 | Minimum selected target-prefix observed span | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/data/target_series/11edccfb9d5df46a725365e1d7b549143bdc9d72aadba1e1c2a4cd01aad66699.npz` | `saved timestamps[-1]-timestamps[0]` | 1377301052-1376401253=899799 | seconds | `b136c02a81e897c8692bf91db63d0990b32a0b1838e6979786dffde655980df4` | CONFIRMED_FROZEN_ORIGINAL_ZIP_RECORD |
| E25 | Maximum selected target-prefix observed span | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/data/target_series/14151b6246a5beded81792315ad3da5f0c89d483e7bbee5982d1b460e675d31a.npz` | `saved timestamps[-1]-timestamps[0]` | 1377640081-1376736684=903397 | seconds | `1d8019e8b22fc3d671fa8106dfba6b4cde6a6e8344c0c433f9f1b17a2662ab1b` | CONFIRMED_FROZEN_ORIGINAL_ZIP_RECORD |

The metric-category labels used compactly in the insertion mean the exact raw mapping below; no absent metric or synthetic MKPI has been added.

| 0-based channel | Exact frozen field |
|---|---|
| 0 | CPU cores |
| 1 | CPU capacity provisioned [MHZ] |
| 2 | CPU usage [MHZ] |
| 3 | CPU usage [%] |
| 4 | Memory capacity provisioned [KB] |
| 5 | Memory usage [KB] |
| 6 | Disk read throughput [KB/s] |
| 7 | Disk write throughput [KB/s] |
| 8 | Network received throughput [KB/s] |
| 9 | Network transmitted throughput [KB/s] |
| 10 | CPU recorded trailing 5 mean |
| 11 | CPU recorded diff 1 |
| 12 | CPU cores observed-valid mask |
| 13 | CPU capacity provisioned [MHZ] observed-valid mask |
| 14 | CPU usage [MHZ] observed-valid mask |
| 15 | CPU usage [%] observed-valid mask |
| 16 | Memory capacity provisioned [KB] observed-valid mask |
| 17 | Memory usage [KB] observed-valid mask |
| 18 | Disk read throughput [KB/s] observed-valid mask |
| 19 | Disk write throughput [KB/s] observed-valid mask |
| 20 | Network received throughput [KB/s] observed-valid mask |
| 21 | Network transmitted throughput [KB/s] observed-valid mask |
| 22 | CPU recorded trailing 5 mean observed-valid mask |
| 23 | CPU recorded diff 1 observed-valid mask |
| 24 | native elapsed seconds /1200 |

Channel mapping source: `bitbrains/data/bitbrains_dataset_manifest.json.feature_channel_order_0based`, SHA-256 `b65713aa68062cf005213a168e49493a04794f7a5e92bae4ffdc08c8d3ac634e`. The raw units are those in the field names. Masks are binary; CPU-derived values use the already stated recorded CPU scaling, and the gap uses actual preceding seconds/1200.

## Frozen time partitions and exact count reconciliation

| H,K | Support raw bounds | Validation raw bounds | Check raw bounds | Test raw bounds | Actual S/V/Cal Check/Held-out Test windows per VM |
|---|---|---|---|---|---|
| 1,10 | [0,106) | [106,1553) | [1553,2277) | [2277,3000) | 10 / 1351 / 628 / 627 |
| 1,20 | [0,116) | [116,1558) | [1558,2279) | [2279,3000) | 20 / 1346 / 625 / 625 |
| 4,10 | [0,109) | [109,1554) | [1554,2277) | [2277,3000) | 10 / 1346 / 624 / 624 |
| 4,20 | [0,119) | [119,1560) | [1560,2280) | [2280,3000) | 20 / 1342 / 621 / 621 |

Bounds are0-based half-open raw-record intervals in each3,000-record target prefix, not date intervals. Source: `bitbrains/raw_schema_and_label_manifest.json.proposed_timeline.raw_target_partition_by_H_K` (SHA `d0bb8f51ed070ea10471ff32b657f7e06164ec597e2e88d8ac32684c94599eca`) and all 320 `bitbrains_dataset_manifest.json.cases[*].roles[*].raw_segment_bounds_0based_halfopen` fields (SHA `b65713aa68062cf005213a168e49493a04794f7a5e92bae4ffdc08c8d3ac634e`).

Each count tuple is identical within every relevant VM group: support covers 80 target VMs; validation is model-accessible on calibration and held-out VMs; calibration Check covers 20 calibration VMs; held-out Test covers 40 held-out VMs. Development-fixed uses support/Check only. Held-out Check remains unused. These are descriptive eligibility/role metadata; no prohibited role was generated or fed to a model by this extraction.

Reconciliation: all 320 cases x 4 raw-role count fields agree with `bitbrains/audit/raw_label_and_window_coverage.csv` columns `case_index,H,K,role,candidate_windows,valid_complete_windows,selected_windows` (SHA `16ac7cd7debdd8342254af41a46a8eee7d277a3fedfd55757bfa226ad5d1c615`); count fields also equal saved X/y shape-leading dimensions and frozen elapsed-audit `n_windows`. Every saved held-out method result's `n` in `Bitbrains_Real_Experiment_Cases.csv` (SHA `d202df22bd3cd5b9c94d21f2959422300a291c2a0f997972c1e790f2c8790163`) matches its original Test count. No new window subsampling or filtering occurred.

## Observation spans recovered from original frozen archive

Original archive: `Bitbrains_Real_Workload_FULL_20261012.zip`, 277229957 bytes, SHA-256 `f0505edce87d7115c093e8a2601cb634fbf3cb85e66d42062051a40b5ce3a5a0`. The original active data, schema, identity, and lock JSON members byte-match the preferred public copies. `msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip` has SHA-256 `11313f528a0cbcbe57e63162f8ae5a41a9c7e7c1a79872e294ff3c5bbaa2e671`, identical to the original recorded archive hash. All 20 selected source raw CSV hashes and all 80 saved target-series NPZ hashes match their frozen manifests/lock. All member reads were in memory; no raw or derived arrays were extracted or redistributed.

Observation span is explicitly `last recorded timestamp - first recorded timestamp` within an already frozen raw source segment or saved 3,000-record target prefix. It is distinct from the nominal 86,400-second source interval and from future forecast horizon elapsed time.

| Population | Original recorded first-to-last span | Unit | Source field / status |
|---|---|---|---|
| selected source VMs | 86107–86107 | seconds | original raw Timestamp column at frozen source bounds[0,288); CONFIRMED_FROZEN_ORIGINAL_ZIP_RECORD |
| dev_fixed target prefixes | 899799–902483 | seconds | saved timestamps[-1]-timestamps[0]; CONFIRMED_FROZEN_ORIGINAL_ZIP_RECORD |
| calibration target prefixes | 899799–901299 | seconds | saved timestamps[-1]-timestamps[0]; CONFIRMED_FROZEN_ORIGINAL_ZIP_RECORD |
| heldout target prefixes | 899799–903397 | seconds | saved timestamps[-1]-timestamps[0]; CONFIRMED_FROZEN_ORIGINAL_ZIP_RECORD |

All selected-target prefixes together span 899,799–903,397 seconds. The minima/maxima used in the insertion are tied to exact original members and hashes in E24/E25. A uniform calendar span is not invented. The following detailed raw-role elapsed ranges are also recovered; they are evidence only to keep the paper insertion compact.

| Group | H | K | Raw role | First-to-last observed span range | Unit |
|---|---|---|---|---|---|
| calibration | 1 | 10 | check | 216932–217233 | seconds |
| calibration | 1 | 10 | support | 31503–31503 | seconds |
| calibration | 1 | 10 | test | 216620–217820 | seconds |
| calibration | 1 | 10 | validation | 433843–434143 | seconds |
| calibration | 1 | 20 | check | 216031–216331 | seconds |
| calibration | 1 | 20 | support | 34503–34503 | seconds |
| calibration | 1 | 20 | test | 216020–217220 | seconds |
| calibration | 1 | 20 | validation | 432345–432645 | seconds |
| calibration | 4 | 10 | check | 216631–216932 | seconds |
| calibration | 4 | 10 | support | 32403–32403 | seconds |
| calibration | 4 | 10 | test | 216620–217820 | seconds |
| calibration | 4 | 10 | validation | 433243–433544 | seconds |
| calibration | 4 | 20 | check | 215731–216031 | seconds |
| calibration | 4 | 20 | support | 35403–35403 | seconds |
| calibration | 4 | 20 | test | 215720–216920 | seconds |
| calibration | 4 | 20 | validation | 432045–432345 | seconds |
| dev_fixed | 1 | 10 | check | 216921–217833 | seconds |
| dev_fixed | 1 | 10 | support | 31503–31503 | seconds |
| dev_fixed | 1 | 10 | test | 216620–219322 | seconds |
| dev_fixed | 1 | 10 | validation | 433837–434143 | seconds |
| dev_fixed | 1 | 20 | check | 216021–216931 | seconds |
| dev_fixed | 1 | 20 | support | 34503–34503 | seconds |
| dev_fixed | 1 | 20 | test | 216020–218722 | seconds |
| dev_fixed | 1 | 20 | validation | 432337–432645 | seconds |
| dev_fixed | 4 | 10 | check | 216621–217532 | seconds |
| dev_fixed | 4 | 10 | support | 32403–32403 | seconds |
| dev_fixed | 4 | 10 | test | 216620–219322 | seconds |
| dev_fixed | 4 | 10 | validation | 433237–433544 | seconds |
| dev_fixed | 4 | 20 | check | 215721–216631 | seconds |
| dev_fixed | 4 | 20 | support | 35403–35403 | seconds |
| dev_fixed | 4 | 20 | test | 215720–218421 | seconds |
| dev_fixed | 4 | 20 | validation | 432037–432345 | seconds |
| heldout | 1 | 10 | check | 216931–218121 | seconds |
| heldout | 1 | 10 | support | 31503–31503 | seconds |
| heldout | 1 | 10 | test | 216620–219017 | seconds |
| heldout | 1 | 10 | validation | 433843–434444 | seconds |
| heldout | 1 | 20 | check | 216031–217220 | seconds |
| heldout | 1 | 20 | support | 34503–34504 | seconds |
| heldout | 1 | 20 | test | 216020–218417 | seconds |
| heldout | 1 | 20 | validation | 432345–432956 | seconds |
| heldout | 4 | 10 | check | 216631–217821 | seconds |
| heldout | 4 | 10 | support | 32403–32403 | seconds |
| heldout | 4 | 10 | test | 216620–219017 | seconds |
| heldout | 4 | 10 | validation | 433243–433845 | seconds |
| heldout | 4 | 20 | check | 215731–216920 | seconds |
| heldout | 4 | 20 | support | 35403–35404 | seconds |
| heldout | 4 | 20 | test | 215720–218117 | seconds |
| heldout | 4 | 20 | validation | 432045–433254 | seconds |

Every row is computed directly from saved timestamp endpoints indexed by the original manifest raw bounds, not from regenerated windows or features. `BITBRAINS_FROZEN_ROLE_SPANS.csv` contains all 1280 case/role values, exact ZIP member source, original member SHA, half-open bounds, endpoints, and span. SHA-256 `445c321cc2aa3f116cda4092411a0d4c92aeba59df832c03d214feed36c28329`.

The public research asset intentionally withholds raw and derived arrays (`FULL_ASSET_SCOPE.md`, SHA `e30536f382d447978c8303749dfa541ffb050ae3e580bdee46cb48e2759c25f7`). That publication boundary did not make the requested fields unrecoverable because the original frozen local archive retains them. All requested S2 fields are now recovered; no required field retains `NOT_RECOVERABLE_FROM_FROZEN_RECORD` status. Monitoring arrival timestamps remain absent, as already noted in the manuscript; event-time availability limitations are preserved.

Frozen native forecast intervals are a separate field: `bitbrains/audit/native_horizon_elapsed_time_by_case_role.json.cases[*].minimum_seconds/maximum_seconds`, SHA `9b11e4a9cd623d57faf5566beb6e0bfce4c587b3d8ad78afea5cf0cad3099bc3`. These are forecast intervals, not observation spans. Existing selected-case all-role extrema:

| Group | H | Existing minimum–maximum | Unit | Status |
|---|---|---|---|---|
| dev_fixed | 1 | 299–1200 | seconds | CONFIRMED_FROZEN_RECORD; evidence only |
| dev_fixed | 4 | 1199–2400 | seconds | CONFIRMED_FROZEN_RECORD; evidence only |
| calibration | 1 | 299–900 | seconds | CONFIRMED_FROZEN_RECORD; evidence only |
| calibration | 4 | 1199–2100 | seconds | CONFIRMED_FROZEN_RECORD; evidence only |
| heldout | 1 | 299–1500 | seconds | CONFIRMED_FROZEN_RECORD; evidence only |
| heldout | 4 | 1199–2400 | seconds | CONFIRMED_FROZEN_RECORD; evidence only |

The raw schema audit H = 4 maximum 2700 seconds describes broader metadata-qualified VM prefixes; selected-case extrema describe selected 80 target VMs / four frozen raw roles. Different populations explain this difference; neither is used as an observation-span estimate.

## Original timestamp member hash ledger

The ZIP container SHA above binds every source. The per-member hashes below additionally match recorded identity/data manifests. Exact target ZIP member = `msa_dti_r4_r5_20261012/` + relative path listed; exact raw CSV member = the path following the inner-archive `!/` delimiter.

| Source VM | Original nested ZIP member | Recorded endpoints / span(seconds) | Original CSV SHA-256 |
|---|---|---|---|
| fastStorage:872 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/872.csv` | 1376314846 / 1376400953 / 86107 | `ec215224fe0e23014f0d35d272249a346aa1a0b7958504bf52e9b5f78ef5ba07` |
| fastStorage:306 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/306.csv` | 1376314846 / 1376400953 / 86107 | `cea4f959fd86ec2172a8eabd3c7b38d696c85620b714dd0d1908d56d75564c79` |
| fastStorage:323 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/323.csv` | 1376314846 / 1376400953 / 86107 | `75b0609deabdce1421481eeafc4f082cbe6ace980878bb73842e3a2d896e2c70` |
| fastStorage:44 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/44.csv` | 1376314846 / 1376400953 / 86107 | `8a6ace7a7e3f8a03abaf5c2a7cb7d52b8ba462b3ef822521b53b9cf1e132e016` |
| fastStorage:400 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/400.csv` | 1376314846 / 1376400953 / 86107 | `9f0cf3970749ae86c45cc8c1b263f650c83d78f9ade0c916a0f7ff980db7ab10` |
| fastStorage:710 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/710.csv` | 1376314846 / 1376400953 / 86107 | `6cf1fcc49614b581e621bdf45fdff448eba0c0903138ea753fdbde1fcb9efbde` |
| fastStorage:270 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/270.csv` | 1376314846 / 1376400953 / 86107 | `a277e6e36b0f9e90b136627b88c3c8a8d3424b6f3d1aea5eb3457f60ddd68f54` |
| fastStorage:471 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/471.csv` | 1376314846 / 1376400953 / 86107 | `a4e94e5ce2f18a386f67248d17cf8ee27b145230103f69fe9ad38415c938b8d2` |
| fastStorage:1181 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/1181.csv` | 1376314846 / 1376400953 / 86107 | `5bb7b889fc61b5dfe9dec2b8702850e7c0bdb9759ffa26764930576d43a9a6a1` |
| fastStorage:865 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/865.csv` | 1376314846 / 1376400953 / 86107 | `bb33139e9b179126c926c303d0e6eef5ab417e19eb423514d18e8bc6010d390b` |
| fastStorage:1050 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/1050.csv` | 1376314846 / 1376400953 / 86107 | `d463f817c4697ad35cbfae49d0df1f9fa0f22622423a25b9dd93db2e4fcb5303` |
| fastStorage:278 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/278.csv` | 1376314846 / 1376400953 / 86107 | `40d8c57c166a798028ff8c9dbcb8910b1287d1d4a7149543d8109fdf712d2d8a` |
| fastStorage:342 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/342.csv` | 1376314846 / 1376400953 / 86107 | `ecc6185f2922f99e0d9d5284a0fc0882f750adcb9bcf7accb9593a95098e1f66` |
| fastStorage:153 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/153.csv` | 1376314846 / 1376400953 / 86107 | `6bb4982133ef58fe58b43cd21d4cc306ae8914ea149d692f391467579a52e65d` |
| fastStorage:293 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/293.csv` | 1376314846 / 1376400953 / 86107 | `0b61917399890c4dc8928a6e8e6337b4c47e89dadb87b3b05e8087df6065cd0e` |
| fastStorage:1018 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/1018.csv` | 1376314846 / 1376400953 / 86107 | `a402518308adb861bf1af34d5af78ed3d01d5ad2be8859f720dfcad65a29f732` |
| fastStorage:933 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/933.csv` | 1376314846 / 1376400953 / 86107 | `e258518a92303aeac26cc721107709c242433a5af4acbfd9030fa9de798fbfa6` |
| fastStorage:20 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/20.csv` | 1376314846 / 1376400953 / 86107 | `1c30f6b818a985dc890f6ff66ed16af124508ae296f4fbf086cdc6358ebe5411` |
| fastStorage:867 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/867.csv` | 1376314846 / 1376400953 / 86107 | `5445ae9b056313353fc11830c7255d6ce05e892084ec6a67a0c6589b9b913771` |
| fastStorage:890 | `Bitbrains_Real_Workload_FULL_20261012.zip!/msa_dti_r4_r5_20261012/bitbrains/raw/gwa_t_12_fastStorage.zip!/fastStorage/2013-8/890.csv` | 1376314846 / 1376400953 / 86107 | `67500906ca17a11f107c4a0a3654acda6f82c48e973aa1eadf4c8694a0346317` |

| Target VM/group | Original target-series ZIP member | Recorded endpoints / span(seconds) | Original NPZ SHA-256 |
|---|---|---|---|
| fastStorage:1007 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/109f87201858ddf96bc750ac60c6724815f2bcb6239bf5735f7bc52223df9ecd.npz` | 1376401253 / 1377301052 / 899799 | `7d03b18dca1d173219f5e47af7816dfc85c34dd3ce922705494ba91c0d70005d` |
| fastStorage:1077 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0ff5facdae3f08b3243547f36dd8ebf7f23405675cfa580144b5687623b5a26a.npz` | 1376401253 / 1377302252 / 900999 | `1ed839fb9b4be77aa92dfcb652766d475058f2188d6ecea2b96e42f46412bbe8` |
| fastStorage:1081 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/113ba34602650493512cb9c619e9fad8bff49180532c9b6e774ddf6d6d67490e.npz` | 1376401253 / 1377301952 / 900699 | `72d0bc5349c284119d096e39cd9c9fc63663c268b1ac4be9a4172046dcb31a6f` |
| fastStorage:1124 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/10c72c0b64f1b702c9a9f29f263c119d9a482ae2282348394a026a569918a4f0.npz` | 1376401253 / 1377302252 / 900999 | `4e9cb32d4fe81e8e734754b236ac775aeff2ec2c067ecad203632ee50b83a9b3` |
| fastStorage:256 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0f72ad8fe374c4238ba015ef57c1bb2e5debf06c383837a3758f46711e04cc33.npz` | 1376401253 / 1377301952 / 900699 | `573058f8f79738d242cd49d55084b23eef3af1782a4fd35a0b04fdf22046f31b` |
| fastStorage:257 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/1121627bf9a086960317d0683bc0651124011d2117d656686b4f34b9dbc60e38.npz` | 1376401253 / 1377302252 / 900999 | `54e4a060e0dafebe9eedbb7087fd67be5c075328896d4bbdcf76e74a671f64e1` |
| fastStorage:317 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0e9487257a3e712a513a03240f52644890eaaca239d2392272b634c4f7e9c44e.npz` | 1376401253 / 1377301652 / 900399 | `badc9510083aad7c6bbc042e214278ef3422740ab7f3957db2133e73a0cd43ad` |
| fastStorage:378 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0f81d2018126f77d00cc0ee0f15e54a623cd4a1b3169722e06ca8384a86eafbc.npz` | 1376401253 / 1377301952 / 900699 | `237406efd81c3dc3aa66ceec57669ffdc2a1d78f712721187332bb16646671b8` |
| fastStorage:46 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0d26209dae9a56d6e236970121a6876cb98fdbbe06c2a56514f09b317f958500.npz` | 1376401253 / 1377301052 / 899799 | `3cb25cdb3950421c527e2a2e847c41311e05f812ebee9bdce03b979bb70ac00b` |
| fastStorage:49 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0f499494d2794a409872fba18b4763d4a7379bf16df42b7f0c57b3c7282a7a47.npz` | 1376401253 / 1377301052 / 899799 | `a283f678781629283af1c7097bdca865dde7ae246c77173d2f2a91b0ab295573` |
| fastStorage:540 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0ea6b2d3dc65aa4becae0d1067746affa8d44486179829a3d37a1fd426b5626e.npz` | 1376401253 / 1377301652 / 900399 | `1d24ec104e7e9186e17e73a94183afd9720928e2f55c0e65904f5d5be23c46bc` |
| fastStorage:567 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/110674464d3b7d3191ecfadeb4f2dfd39b8db52c9449d32a56e7b2c6d0be7cd2.npz` | 1376401253 / 1377302552 / 901299 | `9313ce2b4fab8d10dfde92df7959ee5e8073a74a772e558391f8d87b39553fcf` |
| fastStorage:666 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/116db1c04cf02e594157890deb32f545351d877e98142e59623aa214e6794f2d.npz` | 1376401253 / 1377302252 / 900999 | `be1de2ed8d2797fe02fac88002964e006d87fdbc4a71ae4dbe70628eb53f82a3` |
| fastStorage:717 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0d155603a671909334c0d2f5603ec0fde20af5b568c18ceb50b68c93c29e93ed.npz` | 1376401253 / 1377301352 / 900099 | `32b7d20dedcc99d3c1dc15cfa23c9dbe1205a7c9b88673c652b68e1c40c2c6ee` |
| fastStorage:720 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/10fa6f3d7cd49efb8d3c384343d734df8a2f1eac9dd1e460528397772ffd0b85.npz` | 1376401253 / 1377301052 / 899799 | `98dfc3c1cd3f9398c578594aef8f414aff8f488fa2abe5f63f1fa590af876607` |
| fastStorage:798 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0e576fe14c212c42db8c53731b8ca9f47e49f10702e063e3ab99444a4b8da2b9.npz` | 1376401253 / 1377302252 / 900999 | `30334f745e51d490c979f26543067de6096e1bf30bd126d893942b95c338d752` |
| fastStorage:837 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0e3e1bb3a1edbfc85b92490407acea25926a918090009d9a008fcbb94f70c4f3.npz` | 1376401253 / 1377301052 / 899799 | `3f7d583f698ec0eca432e9e4824a1a40de0dcd4456daf8b310ea95e554ef9181` |
| fastStorage:845 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0d9708241f7a3515059e30e6afca819255c12495aaa213f2dfeefad26efe68e3.npz` | 1376401253 / 1377301052 / 899799 | `fba495a9e199052cc93b37c06cc48c841b02f860170fb94e078946577389236a` |
| fastStorage:954 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/115b4ef027c9fe5033411e7fc6569e9e93499b1bf013fa80c805149b7ee61438.npz` | 1376401253 / 1377301952 / 900699 | `84b0da3ee28c3296032797db0279ba1515bc2b829ba434f7b402ee28f6e07b22` |
| fastStorage:998 / calibration | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/101656d9a608597e83de2ad777d64194d8332aeb597e7d69aca9624f4968a066.npz` | 1376401253 / 1377301052 / 899799 | `8c09162bc5159043996b09aff42a301c13ac26d4124f9daa73e9eb42114460e4` |
| fastStorage:1033 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0ca43f3a7653150ab1361b37127c83b9107c014d1f4c3bccda509b483f0d1e61.npz` | 1376401253 / 1377301352 / 900099 | `884f074478fe3adae09859f810c64eb1b417252f610dd6e42078ea22b6cd3dee` |
| fastStorage:1122 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/059b52193ca7e656e4884fe6d8dd7a1aadf66ca62d3de02a9d95057a3e355a8f.npz` | 1376401253 / 1377302252 / 900999 | `0e2c6fa820b7b18434039f8a42a898ea0fbfe2e7118c1cfb09eefe18ced60af3` |
| fastStorage:1157 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/08acba6f568065d719b9cf8d38d80cb2e7e8b06e994aa43f9f63fd44b7ae41b4.npz` | 1377598677 / 1378501160 / 902483 | `201ad74fba6eaa45882a5528b192585d2eceabea8df5352f666a101beca4d5fe` |
| fastStorage:117 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/05c0217f9438dc888030a7f2c2c303fa9e4cc864e1f9137841405f53fbe820e1.npz` | 1376401253 / 1377301952 / 900699 | `68f9e53b7fa6d784df116ccd1f770e16c8827604f40203762b09755c91beff09` |
| fastStorage:137 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0531c9f61aaafee681faf97a15cca8ef0298a6b299799e891a7d870140ee0000.npz` | 1376401253 / 1377302252 / 900999 | `fb433c2feaf872f6f425540465be4daa186ffa74652ac735126e0153d84ebedf` |
| fastStorage:177 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/06981cca18db3d98e4a49edf2c69cf746f93e426d206e28ea9653b874d49aae2.npz` | 1376401253 / 1377301952 / 900699 | `e7babded21feb335a81283016b53f4285abe17dcb395c69b8acc681b8db91289` |
| fastStorage:209 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0b8dbaa8bc7c26ea97340ad78acfd1705daaa9161ac8e4bfba0be6d9185c5d55.npz` | 1376401253 / 1377302252 / 900999 | `bb0901956ad52a43d7cdfca0d0d5c7946f896864590c8e70baa2f476b09ef215` |
| fastStorage:244 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/05c4f252e5c50673ab67a0d41d45f2dc472dfa57a64e1a7f86c5d438307aaf76.npz` | 1376401253 / 1377301952 / 900699 | `f25651f9c1d8e1cc804562fcc71259887ec5429ad61fef81e651bae832f91e17` |
| fastStorage:265 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0634ba2aa793fb977066ace197ab4ee21217d60c4cf650893f5ab86aaa9a350a.npz` | 1376401253 / 1377302252 / 900999 | `ad721e3d8633ec0291350934cde5b7dcbb222d3d6d3aff49d6af6ea864bcfd13` |
| fastStorage:34 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0975ac190e2ae832e6fbfed0655a244cf6b83afcb7b4fa4439cc90119719dfff.npz` | 1376401253 / 1377302852 / 901599 | `ae5f7fcebc0c2f4e40596fa5c8965b908b59a1a20cae9a3f6bac68846e8a9f81` |
| fastStorage:407 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/06f23940e0938c974aa487bd7f76962ca2c6938f932bc7e835bfea376cedd029.npz` | 1376401253 / 1377302552 / 901299 | `23e12668c08bc486ad4d81717315df9b85e7db45af48704af7705dc38c1bb075` |
| fastStorage:453 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/09ee183259c72b47211006937aa9add9b12bd7be752892aef05133a171dac00a.npz` | 1376401253 / 1377302252 / 900999 | `3947bbce0684c954bfca66965ef55aa540dead81d9c121303d94bc089b0b0dbe` |
| fastStorage:499 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0cfd2963a2a46e807937ca2b7f3291e02aaa158b5f58a721cbd9ab6afdfd39c3.npz` | 1376401253 / 1377301952 / 900699 | `63aaf291b90abe62a62c705c5fbb66c9e07cb19fd92bde1ef828b3da0da79ca4` |
| fastStorage:574 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/04eec84ea417750b6ead613e33e94a68a80988e884357b24f5415a96fb25a02a.npz` | 1376401253 / 1377301352 / 900099 | `9c59c844e20bbb9462b4fe629d44979a34c81a38844941ce33f8d662d706af12` |
| fastStorage:77 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/08769cd2986f94811be8275790a1e054b39d00616ccf38433056eb27737bff71.npz` | 1376401253 / 1377302252 / 900999 | `157207a06dab6506f1ed836f7cdf426678a263f87f065f59a53e664edfdadf06` |
| fastStorage:783 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0795c0d23cd0eca24f51bba304fbb609bbdf95a2aff988117e74dd45053ca888.npz` | 1376401253 / 1377302252 / 900999 | `b1d5a3ee994caa83367d95698adf63c5d7f421a7f1d984d078650febb34e50d7` |
| fastStorage:793 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0af9063b8a302c9c05f3c636ea4b8966e61252fc0b62db8946af3b295bed0063.npz` | 1376401253 / 1377302252 / 900999 | `2e9a1ae32240ba0081be8829f8872812a1801e0a51a49a949d9e67b7393395ab` |
| fastStorage:86 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/08c2a19ea47c79ac70d8842e7ec645ddc5158e75b1764139ac88b79d243515b4.npz` | 1376401253 / 1377301952 / 900699 | `ca5a34887493abf80866030469de661392c11f31a7217126b920fcdbedf8b36f` |
| fastStorage:965 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/07772a71b663f0d05e17df6b38d4318d131113d4e277731376977b57cef3ad06.npz` | 1376401253 / 1377301052 / 899799 | `0db66e19c69b221f5d068df99b5e3c5a57799bac70185aa8a868a12d2812d3cc` |
| fastStorage:979 / dev_fixed | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/0a9667c134d3d5adfcec70ba742670aa011bdb1e010051f3b2e477b559994b42.npz` | 1376401253 / 1377301052 / 899799 | `64082f3cf01dee41b85f95b861b5327d15b7431a52e60d6d54d7e7a14fa0f93d` |
| fastStorage:1002 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/11edccfb9d5df46a725365e1d7b549143bdc9d72aadba1e1c2a4cd01aad66699.npz` | 1376401253 / 1377301052 / 899799 | `b136c02a81e897c8692bf91db63d0990b32a0b1838e6979786dffde655980df4` |
| fastStorage:1072 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/15f53c833e1e88531b6d1d0c9c98d4f23bf07bd8c6611ed02856bd4b9b25b6f0.npz` | 1376401253 / 1377302552 / 901299 | `44ee340a7904ef8e32bedd37f98155b36f3797625740f6aaafc16b8ebd284fc2` |
| fastStorage:1076 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/11d8572c3ec44fe9ea58ddcfcdee11e88d4b66f12aefec8a3f9440e654ec0582.npz` | 1376646075 / 1377548873 / 902798 | `0a87758d7d6cecc8db0bec542d5aa0bf1082912069ab755099fbd4108965077d` |
| fastStorage:1095 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/182a0ebb18e29c1fe6ece4444ff210498f03e37978a44bf62e8115d9095baac0.npz` | 1376401253 / 1377301952 / 900699 | `a9eb1a4463f457ebea5720d6a2cf42ef1aad3cd7cfc9295099694f1eceeb9803` |
| fastStorage:1098 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/15b31d0f1affa3950dc6f8da09f3cf1c03d0658a74b4211bc1ebb2da30024871.npz` | 1376401253 / 1377301952 / 900699 | `39e2512531a846c7ea560642155b25023e9338efe1b15282826ae735a8df9d80` |
| fastStorage:1099 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/1853dddad281405a47f2b3519b9e6adb666626878b22311b48a854ebd1af05d3.npz` | 1376401253 / 1377301352 / 900099 | `8dfe618c539cc352d6318a0e33f73e82bd6014d787b949af8ffb7d1c5a032080` |
| fastStorage:1119 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/14a3c68f9d1cef9be7bef0797cd0c6eca65ee27565d7a5d15254532489c254a4.npz` | 1376401253 / 1377301952 / 900699 | `dad0d0e47e2d8c4010161e2d45924106481b52e6aa0ae5451793b8154f4c0250` |
| fastStorage:1120 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/153d8c908be1603d318fee797d0b61fae70a2374d40e46cb5193400728247324.npz` | 1376401253 / 1377302252 / 900999 | `b961b8b3dadf2fce15a2073ff3ede8a87c6917e428eb3198a357822a869ef173` |
| fastStorage:1158 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/13c1f43f921f9eecc71e762b9baa687b6436e1da3f77e3f5fd30dd245b7fd73d.npz` | 1376401253 / 1377302252 / 900999 | `88797658cdad702c610009a9494a768e1cdd3adbc07793a69f28ef18962e4ab1` |
| fastStorage:1194 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/136d2daf8e290de9e7d58b5911a2d2fb1a20fe432d811990730030e54c989b2c.npz` | 1376401253 / 1377301652 / 900399 | `68e2087f4683d26448384bfb8920e3bf008946eb8b75b7563d752f98ce004f65` |
| fastStorage:1206 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/11d816fc263c26a56d69f4ea770f70ca4ace74d26666c8332500a2209e37981f.npz` | 1376401253 / 1377301352 / 900099 | `f9b25307575067ae7f64e13b5c988c4548ccfd51fedb757f7467f520f6c57a85` |
| fastStorage:13 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/138966f7fc986eab7d69d8762bb2b7d2a44d82e54f7863bd2212875fe0ff790d.npz` | 1376401253 / 1377301352 / 900099 | `8095fa868f4d6459b4edf12d613d9df700bb5bb326778fed0453ed214f0a7491` |
| fastStorage:140 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/171e00dae1b2b212e424a3fce6619b38e66a92d41b81206ccc6b4838e8db304f.npz` | 1376401253 / 1377301952 / 900699 | `46285d2948dd81ac3884153ed5851ced5e50e40b2af6f4cbaead94086700ef3e` |
| fastStorage:163 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/1188257d809522119835fe18e880d4a468e2da76be02af06e90200a1e68099f9.npz` | 1376401253 / 1377302252 / 900999 | `038362d7e7397f74350f94e813d49e708aaf2767fe858cdbcbcd1a0397f665aa` |
| fastStorage:227 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/11ded379595c3399f3beb30c8940ee765f3824d66b879c42984465839f36e415.npz` | 1376741184 / 1377644281 / 903097 | `79423f1ea7da7cdb192a9126fd80416431aa959902d7b1d013a98de79324429f` |
| fastStorage:229 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/14151b6246a5beded81792315ad3da5f0c89d483e7bbee5982d1b460e675d31a.npz` | 1376736684 / 1377640081 / 903397 | `1d8019e8b22fc3d671fa8106dfba6b4cde6a6e8344c0c433f9f1b17a2662ab1b` |
| fastStorage:254 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/14194fa9ee11920bf15e4f3dc323a0a5c5f57b0eb9949d8aa4166175df1f4eba.npz` | 1376401253 / 1377302252 / 900999 | `f3e916fd2d48d6e7ad5314e6affe7eca37bec241811ac3256a94a8afbe155183` |
| fastStorage:260 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/17d8d34605a488db8095833a45d5e8a4e3e6d80f5371b9a677de232e11a459a1.npz` | 1376401253 / 1377302552 / 901299 | `d417e0187ad448809d9a7d262c6ea9663ed43fdfed90567d346711ae48aacce9` |
| fastStorage:263 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/117fb49f0d33e838af20236367af6af09db67a864eea540efa0f273c45896dac.npz` | 1376401253 / 1377301952 / 900699 | `1634fd722524b9a3c1436c3f981255645445cdbd55a9e28b5d74525dafbf6cd0` |
| fastStorage:266 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/15a63c0c92350f36993214e811739e93692f3351e105fb655c4cc9fbce38507f.npz` | 1376401253 / 1377302252 / 900999 | `b18c45341c7dd381e6bf4503a8c637f74be2e57c4a59ec304b27929fac11d314` |
| fastStorage:274 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/17e2efb661051cd2dad17ed5eeb457ab8ae066da7bc9942de93d553f7f719a82.npz` | 1376401253 / 1377301952 / 900699 | `63ecf294d6defd42cc0fcc6e620c8434fccb21a4cebd973f9a018b018bafaa6f` |
| fastStorage:349 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/17019b12fad9c3110980e97048f753dbccb8161160d78518b1a8c31072f52a22.npz` | 1376401253 / 1377302252 / 900999 | `837a981b7ce7fd0e022abdcba4769f8ce8982bbbf3bf1c5e9cf5d185f7f4570b` |
| fastStorage:353 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/136ef9f7b8e865ca3d1b254cf9d3fc220fd40b3deabe0f8467d6960aaffb0907.npz` | 1376401253 / 1377301352 / 900099 | `20fef5c4e12610441427958ff31d2e2b047d93aec49b29e51bb42bb688572399` |
| fastStorage:418 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/17fdb54636c5c34d3ce646b7599ce1bb05f10bb9fe153102ebd184fa3d603381.npz` | 1376401253 / 1377301952 / 900699 | `268dac12a7a05e671d51aad75302fe1f48d7a0dee35336638e7e0d9eafbe55dc` |
| fastStorage:478 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/13ad2c6c72a6434d9a27523839130aeb4c399ce8e2c6ea433e6ee985e648ffd5.npz` | 1376401253 / 1377302252 / 900999 | `7fcfc2177031d24b948089356f39d795f2173ef0d6fcae4532cf8144139f9f57` |
| fastStorage:491 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/15b1412a9768074ea5134c5608599ec5db4a70a2c8a86c9b72ae835eb7e9fc96.npz` | 1376401253 / 1377302252 / 900999 | `3599e513374e676808f907300b2b67c1874eb2c7810d2f48dde5eb5579202b9b` |
| fastStorage:506 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/14891838076b05aff6e87ad4cceb27aa04c5ae25159ce786c9218dc70d165428.npz` | 1376401253 / 1377301952 / 900699 | `59b71b4450b22c7dde0b77dbb8aca6e77e6fcd0cb0bfe0164003003b07675740` |
| fastStorage:518 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/179dfc57e5f3852ecaf563b200447076618747f22ee65f8084a905df92e62d2b.npz` | 1376401253 / 1377301952 / 900699 | `d7926e49fcbcdc030f140a8db02f3345b5e78046c7509f37ed7557cedd8220bd` |
| fastStorage:528 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/153eb6a9f500b4b5cfbd6c6a7bec7ee5f34e6f4dd3553296b027997d03d8f0d2.npz` | 1376401253 / 1377302252 / 900999 | `d62f221f7033ce806106b150fb687f0fd3d25c787da46b1dd7f2dc12687c98ff` |
| fastStorage:544 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/14b62e5f5b3cf06415b2863f24710e345d7c2cae3056dfad41a8380d2b75d09a.npz` | 1376401253 / 1377301952 / 900699 | `a764428151cdf2611a27d69f543757b9078a5800bc1b31bb884a279f7a3adf35` |
| fastStorage:549 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/148c8133eacaaba401d861755b20854a8d110e97802a4a8da1989f5331c303e2.npz` | 1376401253 / 1377302552 / 901299 | `290a78294449bbc2e63cc2ceb0f96362e67a67cfe48c9c005731c999ff2f9376` |
| fastStorage:581 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/12dc7f3bc9da9ee23afb144088d2247681d70c4dcbbc32a5a0867f788a043297.npz` | 1376401253 / 1377301952 / 900699 | `45372f65ee87f35e0f6c68e7c11707f5e250c8e2acf51d2dc2f5fc1b8709a62b` |
| fastStorage:588 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/128c0283d7664a977e03d450004b5b2e6168f17f8ef7b179e175d4bdbf0f5b74.npz` | 1376401253 / 1377302252 / 900999 | `fb3df326267e4f841b2d2e438cb7a6ed29497f7085083b5249ce7c97e2e2450f` |
| fastStorage:597 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/11f00fe2c32b0e8b834fb0f8d7f363828df06b339e9ad31c509224392e476ab3.npz` | 1376401253 / 1377301352 / 900099 | `b49e06f603722ff1fc88a45e528ee09116c61f00b3d6b48f264a6ab7be89799e` |
| fastStorage:609 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/11dd7f699f685fa1c0861814eeee9def621250bdd30d6b2d577e0cd1029a5a9c.npz` | 1376401253 / 1377302252 / 900999 | `bd6d5c5f54b0289cd3abdd370bd99d21dfd8969ace255f9353a9b6c237983fc6` |
| fastStorage:69 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/1762f1c7063477127f884ff4ba28dd0110750615ed71d4fcd0194771d7418abf.npz` | 1376401253 / 1377301352 / 900099 | `e691fca6e0a85858b2f0c46f2a58f3c42659638ba1e8416dc7df361a9c5c69f0` |
| fastStorage:795 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/1331bbb736fdd08de1d297377219ffe4db417b0f618c207aed4d7544b898bf99.npz` | 1376401253 / 1377301652 / 900399 | `13a570aae33fd3ee1dfae9f7090a14a9682d010f0587e925edcb969aaf41eb27` |
| fastStorage:893 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/118425f590ec0e5f5cb3f5ebe33d48d8ab80bc06a64feb2fa0de159e26a2416d.npz` | 1376401253 / 1377301052 / 899799 | `f426f7f37d0d1230a36ce3e47008d8b2c149cf03b779f3a40cec3e9d095aa3e8` |
| fastStorage:906 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/14ef5f668acfd2813367654ef2315d8f38307360c5f391b614bb2565e40525ff.npz` | 1376401253 / 1377301952 / 900699 | `26a3c5e00abfe35e2fd7b22ca2d7855a51ec1a54478143854077ceb6a7bb919b` |
| fastStorage:947 / heldout | `msa_dti_r4_r5_20261012/bitbrains/data/target_series/15eb1c35d1d6c1ebde3cee8633a06c7e0569616ab587f058ff374a074da00273.npz` | 1376401253 / 1377301952 / 900699 | `22ba2d8afc2dca7d847f41b68b8fc6bd41b10ba783450204919375ecbf1ad2a4` |

## Minimal insertion decision

Only the confirmed facts E01–E25, grouped channel mapping/causal rules, recovered time partition/observation-span rules, and the verified frozen public-asset entry are proposed for §S7.5. The proposed unnumbered insertion contains eight protocol rows (existing numbered tables retain their labels/numbers) and leaves all existing S7.5 paragraphs, calibration/result tables, figures, statistics, and costs intact. Only verified first-to-last observation spans are inserted; no uniform date is invented. No evidence conflicts with existing S7.5 facts; a STOP condition was not triggered.

The separately written `S2_PROTOCOL_INSERTION.tex` is intended immediately after the first S7.5 paragraph and before the existing full five-condition calibration table. Source label names/check/test permissions follow the frozen runtime; counts refer to windows and may share label endpoints.

## Read-only extraction receipts

- `inspect_bitbrains_frozen.py`: metadata-key inspection only.
- `extract_bitbrains_protocol_readonly.py`: parses frozen JSON/CSV counts and hash bindings; reads saved NPZ timestamp vectors and selected-source raw timestamp columns directly from the original frozen ZIP in memory.
- `BITBRAINS_FROZEN_EXTRACTION_RECEIPT.json`: exact count ranges, source hashes, withheld-path ledger, and assertions. SHA-256 `ec138b041af6056f4274dae370c5d3df515e5ed0085dedb59223fb1f9890b20f`.

All output files reside in the task-output directory; the preferred frozen asset tree is read only.
