# MSA-DTI / JNCA final publication closure — 2026-10-13

**Status: PASS.** The authorized Data Availability revision, clean multi-pass
main-PDF build, complete LaTeX ZIP, independent manuscript-only publication,
anonymous download acceptance and this round's historical protection checks
are complete. PR #9 remains draft and unmerged. No scientific experiment was
run or changed for this closure.

## 唯一基准与精确修改范围

唯一基准为 `MSA_DTI_PositiveEvidence_Mainline_20261013.zip`，
7,056,735 bytes，SHA-256
`b7e7a76dac91b5fa9b4fef91bbe5df5d1bc88f63ef3cd74cc817888e92435870`。
原包 30 成员 CRC PASS，29 条内部 SHA-256 PASS；修订前 `paper/current/`
25 个科学成员全部与原包逐字节一致。

本轮仅修改 `paper/current/main.tex` 的 Data Availability 中段，以及由该源文件
重新编译得到的 `paper/current/compiled/main.pdf`。用替换前的中段恢复新源文件后，
其 SHA-256 精确回到原 `main.tex` 的
`356a4fe7fa4df3ea3c8713d3e5d461b1dc7556f744f3b36700938f418476fed1`，
证明该段之外全部字节未变。修订源 SHA-256 为
`55a5d395f1e640bfa970d7af12e3400e28b7884a8ac6fc339048256291bb8613`。
Abstract、Introduction、Related Work、Method、Conclusion、公式、算法、参考文献、
实验统计、阈值、种子、划分、作者/单位/CRediT/Funding/披露、数据集脚注均 KEEP。

## Data Availability 原文

```tex
\section*{Data Availability}

The frozen synthetic-study code, configurations, processed results,
plot-ready data, and reproduction scripts are available in GitHub Release
v1.2.7 at
\url{https://github.com/w924871681/paper-code-DT-Twin/releases/tag/v1.2.7}.
Saved predictions and targets, selection records, and statistical verification
scripts for the supplementary R5 fixed-candidate comparison and the Bitbrains
in-domain evaluation are available in a separate evidence-only Release at
\url{https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-r5-bitbrains-20261013}.
This evidence archive permits recalculation of the saved results but does not
include the original Bitbrains traces or source-model checkpoints. The
causally corrected Alibaba study is documented in a separate reproducibility
archive,
\texttt{Alibaba\_Causal\_Correction\_v1\_1\_G5\_COMPLETE\_20261011.zip},
containing the corrected code, model checkpoints, derived results, and
provenance records; this archive is not included in either public Release and
has not yet been publicly deposited. The original Alibaba Cluster Trace
v2018 and Bitbrains GWA-T-12 traces are not redistributed; their
official access links are provided in the corresponding dataset footnotes.
```

## Data Availability 完整修订英文

```tex
\section*{Data Availability}

The frozen synthetic-study code, configurations, processed results,
plot-ready data, and reproduction scripts are available in GitHub Release
v1.2.7 at
\url{https://github.com/w924871681/paper-code-DT-Twin/releases/tag/v1.2.7}.
The expanded R5 and Bitbrains assets include code, configurations, model
checkpoints, saved predictions and targets, development-set fixed-candidate
mappings, calibration and held-out records, statistical verification scripts,
and reproduction instructions. Corrected Alibaba assets include preprocessing
and evaluation code, checkpoints, six-threshold calibration records,
held-out results, and reproduction instructions. These assets are available at
\url{https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-full-20261013};
the earlier light-audit archive remains available at
\url{https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-r5-bitbrains-20261013}.
The archives exclude third-party raw traces and their full derived input
windows. R5's historical R2 development-pool RNG/raw-array provenance remains
\texttt{UNRESOLVED\_HISTORICAL\_RNG\_PROVENANCE}. Corrected Alibaba is a causal
reconstruction on a previously observed evaluation population, not a new blind
evaluation. Independent statistical recalculation of saved results does not
establish independent end-to-end training reproduction from raw data. The original Alibaba Cluster Trace
v2018 and Bitbrains GWA-T-12 traces are not redistributed; their
official access links are provided in the corresponding dataset footnotes.
```

修改原因：已公开的扩展包包含 R5/Bitbrains checkpoint 和因果纠正 Alibaba 证据，
原声明“缺少 source checkpoint”和“Alibaba 尚未公开”已过时。修订同步这些事实，
并明确原始/完整衍生输入未再分发、历史 RNG 缺口、Alibaba 先前观察群体及统计复算的边界。

中文翻译：冻结合成研究的代码、配置、处理结果、绘图数据和复现脚本仍可从 v1.2.7
获取。R5 与 Bitbrains 的扩展资产包括代码、配置、模型 checkpoint、保存的预测值与
真实值、开发集固定候选映射、校准和测试记录、统计验证脚本及复现说明；纠正后的
Alibaba 资产包括预处理和评价代码、checkpoint、六阈值校准记录、测试结果及复现说明。
这些资产位于 evidence-full-20261013，旧轻量包也继续保留。公开包不包括第三方原始
轨迹及其完整衍生输入窗口。R5 历史 R2 开发池 RNG/raw-array 来源仍标为
UNRESOLVED_HISTORICAL_RNG_PROVENANCE。纠正 Alibaba 是针对先前已观察评价群体
的因果重建，未构成新的完全盲测。保存结果的独立统计复算不代表已从原始数据独立
完成端到端训练复现。两数据集原始轨迹不再分发，官方下载入口保持在原数据集脚注中。

## main.tex 精确 Diff

```diff
--- baseline/main.tex
+++ final/main.tex
@@ -1212,18 +1212,21 @@
 plot-ready data, and reproduction scripts are available in GitHub Release
 v1.2.7 at
 \url{https://github.com/w924871681/paper-code-DT-Twin/releases/tag/v1.2.7}.
-Saved predictions and targets, selection records, and statistical verification
-scripts for the supplementary R5 fixed-candidate comparison and the Bitbrains
-in-domain evaluation are available in a separate evidence-only Release at
+The expanded R5 and Bitbrains assets include code, configurations, model
+checkpoints, saved predictions and targets, development-set fixed-candidate
+mappings, calibration and held-out records, statistical verification scripts,
+and reproduction instructions. Corrected Alibaba assets include preprocessing
+and evaluation code, checkpoints, six-threshold calibration records,
+held-out results, and reproduction instructions. These assets are available at
+\url{https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-full-20261013};
+the earlier light-audit archive remains available at
 \url{https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-r5-bitbrains-20261013}.
-This evidence archive permits recalculation of the saved results but does not
-include the original Bitbrains traces or source-model checkpoints. The
-causally corrected Alibaba study is documented in a separate reproducibility
-archive,
-\texttt{Alibaba\_Causal\_Correction\_v1\_1\_G5\_COMPLETE\_20261011.zip},
-containing the corrected code, model checkpoints, derived results, and
-provenance records; this archive is not included in either public Release and
-has not yet been publicly deposited. The original Alibaba Cluster Trace
+The archives exclude third-party raw traces and their full derived input
+windows. R5's historical R2 development-pool RNG/raw-array provenance remains
+\texttt{UNRESOLVED\_HISTORICAL\_RNG\_PROVENANCE}. Corrected Alibaba is a causal
+reconstruction on a previously observed evaluation population, not a new blind
+evaluation. Independent statistical recalculation of saved results does not
+establish independent end-to-end training reproduction from raw data. The original Alibaba Cluster Trace
 v2018 and Bitbrains GWA-T-12 traces are not redistributed; their
 official access links are provided in the corresponding dataset footnotes.
```

同一 patch 随完整工程 ZIP 提供。以下是已提交的本轮文件变更清单；只含 A/M，
无删除或移动，四个历史根级论文文件继续 KEEP：

```text
M	README.md
M	REPRODUCE.md
M	paper/README.md
A	paper/current/BUILD_INFO.md
A	paper/current/BUILD_LOG.txt
M	paper/current/README.md
M	paper/current/SHA256SUMS.txt
A	paper/current/SOURCE_MINIMAL_DIFF.patch
M	paper/current/compiled/main.pdf
M	paper/current/main.tex
M	paper/evidence_20261013/README.md
M	publication/20261013/CLEANUP_PLAN.md
M	publication/20261013/CLEANUP_REPORT.md
M	publication/20261013/DATA_AVAILABILITY_MINIMAL_PROPOSAL.md
M	publication/20261013/MANUSCRIPT_PUBLICATION_STATUS.md
```

closure 报告和最终验收状态文档在后续文档提交中追加；历史 `PUBLISH_FULL_RECEIPT.md`
保留其原轮内容，新的验收以本报告为准。必要导航区分 v1.2.7、旧轻量证据、扩展证据
和最新 manuscript-only Release，并给原 v1.2.7 Alibaba 正向结果增加泄漏失效的历史限定。

## Supplementary、图表和模板逐字节一致性

其余 23 个科学成员全部与唯一基准逐字节相同。Supplementary 保留原 15 页 PDF，
源码没有重新排版或改变。下表哈希同时是基准和最终哈希：

| 文件 | SHA-256 | 状态 |
| --- | --- | --- |
| `cas-common.sty` | `e95a01f4b33531d01ade231669fcc1e42f52193dddcb22ead5b63240eb952f8f` | KEEP |
| `cas-model2-names.bst` | `6f6204eb7670d762042ab363c2d05cf87196052bfbdf6dbee51a1327a8ce479a` | KEEP |
| `cas-sc.cls` | `5030545ed09c770afa31004817bf8626ca7f311cf795e6c2825ecae113bb42e9` | KEEP |
| `compiled/supplementary.pdf` | `6540643096e81f567dc5b4128494443cffdb92dea8864e048635953fb9e135b0` | KEEP |
| `figures/fig1.pdf` | `422b4e57c1c310e539844af139d24bd31dd6b815034df9323ace87ccc0d06062` | KEEP |
| `figures/fig10.pdf` | `eafa68535fdc3357d91d6e3f7ca3bc9b71c5cab46109d92295e12c11918bd88e` | KEEP |
| `figures/fig11.pdf` | `1ec9b0f5f78bdf600eb779e4985ddbfd8a1e9db78cd98b57231b9a08b09d005f` | KEEP |
| `figures/fig12.pdf` | `4588c761660b3d74bb00758b688c7dece8fb13c4ac8a326c14d5d32d41ac0d33` | KEEP |
| `figures/fig2.pdf` | `fd1aaeb94288e8c125ae65924997752b7be4ae29d6d11cab304add4992441ba8` | KEEP |
| `figures/fig3.pdf` | `651624d984f5ef6b6a0ceec033d6a2648f6214b470da01a26c2ba30837c83bf3` | KEEP |
| `figures/fig5.pdf` | `7c4297342930093b3b5a0ddf736464a4f31cdbca560723253f07902089d2dfed` | KEEP |
| `figures/fig6.pdf` | `40bfbf673a6ae68d87a1feed5727c9ad690090cdbeb86625c76ae0268cd63bf3` | KEEP |
| `figures/fig7.pdf` | `0e83ecd59a7f21c228af6cbd4d699275b80530749ba1a7d67128b5e3becdb835` | KEEP |
| `figures/fig8.pdf` | `75232e2b067797a00adff61a3f953108de428e4ff5a695f794c2392546fbdb6e` | KEEP |
| `figures/fig9.pdf` | `5d8938af626e7cdccf01608c87496c914accac612cd0a07d5f41e15e34b47ba8` | KEEP |
| `figures/fig_alibaba_corrected_calibration.pdf` | `d0acc06f3929ff2e690eb6dc8d844e42c330be3c50e783eb53913290f3521c9a` | KEEP |
| `figures/fig_alibaba_corrected_heldout.pdf` | `dd349e3d36b0ff837af4b66377a6cf4f5ad112479ec310427fd2ff916ee78eb4` | KEEP |
| `figures/fig_bitbrains_gain.pdf` | `853a287ebda3692adb07919c101ef72277179e55fb47a38d815b4ca4b19e251b` | KEEP |
| `figures/fig_overall_performance_ours.pdf` | `55572e4452460c0202e1a04a6492ed1fc9beaf4e48fc71ae3f012bcae84bee4b` | KEEP |
| `figures/fig_r5_devfixed_gain.pdf` | `d2c952abf9eab11327655c93d2b47858e8394f4c00e0d43954ba8f9aa82f29ab` | KEEP |
| `supplementary.tex` | `7f13409419410c255c92da562cb20535eee796fa823bb90a2c1e2eb2ff1d4063` | KEEP |
| `tables/table1_configuration.tex` | `4d0aa2c3dd26ca04969949ebe27ab50c48df8deb5542cab47ba385dbffbf79a7` | KEEP |
| `tables/table3_target_cost.tex` | `d932f1add1d34e9d606de9b482e82442e2f81525482ad1051bd8afc1270fba00` | KEEP |

## 编译、日志与页面验收

实际编译器：`MiKTeX-pdfTeX 4.23 (MiKTeX 25.12)`；CAS single-column 模板
2.4（2024/05/04），供稿模板字节未变。补齐 MiKTeX `sttools` 3.5 的 `stfloats`
与 CM-Super 0.3.4 Type 1 字体；CM-Super 官方包 SHA-256 为
`20c2d49533dd96e24915a9b5ba13138f69e4f3bf4ef47ceea179d1c8c5a3bce0`。
通过 direct pdflatex 绕开 latexmk 的 Perl 依赖，未升级或修改论文模板。

```text
pdflatex --disable-installer -interaction=nonstopmode -halt-on-error -file-line-error -recorder main.tex
SOURCE_DATE_EPOCH=1791849600; FORCE_SOURCE_DATE=1
```

原稿基准和修订稿各运行三轮，全部 exit 0；交叉引用与参考文献解析完成。
新正文仍为 16 页，Data Availability 在第 15 页。前 14 页及第 15 页该节之前
区域与同环境的原稿编译结果逐像素一致。16 页缩略图及第 1/15/16 页大图通过视觉
检查，链接合法换行、无新增裁切/公式重叠/异常空白页。
原 CAS `\maketitle` 的 `Overfull \hbox (117.0831pt too wide)` 警告在基准与
新版均存在，没有可见裁切；未为消除既有模板警告修改未授权的正文。
无新增 Overfull Box、未解析引用或 rerun 警告，相关字体均为 Type 1。

ZIP 的全新解压副本通过 CRC 与 29 条成员哈希，并再次三轮编译为 16 页；
重建正文 PDF 与交付正文 PDF **字节级 SHA-256 完全一致**：
`7a6f8459cd3cf57f8e7167a8d18846ed704b1cb92bd32e43da279bb54a8d652d`。
工程内 `BUILD_INFO.md` 和 `BUILD_LOG.txt` 记录实际命令与日志摘要，
`SOURCE_MINIMAL_DIFF.patch` 记录唯一 TeX 修改；原始本地编译日志保留在独立 build 目录。

## 本地交付与新 GitHub Release

本地独立交付目录为本任务目录中的 `deliverables/`，原始 ZIP 未被覆盖。
完整工程含当前 main.tex/main.pdf、未变的 supplementary.tex/supplementary.pdf、
16 图、2 外置表、3 CAS 文件、README_FINAL、成员 SHA256SUMS、精确 patch 和编译记录。
共 30 ZIP 成员，CRC PASS，无个人绝对路径。

新 [manuscript-only Release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/manuscript-final-20261013)，ID `411461046`，
Tag `manuscript-final-20261013`，目标为本轮科学源/PDF发布提交
[`4e8bf03558340506c47b6187f2a4e7642ecb2708`](https://github.com/w924871681/paper-code-DT-Twin/commit/4e8bf03558340506c47b6187f2a4e7642ecb2708)。
[当前论文固定入口](https://github.com/w924871681/paper-code-DT-Twin/tree/4e8bf03558340506c47b6187f2a4e7642ecb2708/paper/current)
与 [PR #9](https://github.com/w924871681/paper-code-DT-Twin/pull/9) 保留可审查源文件。
后续验收文档提交只同步事实，不再修改这份 LaTeX 或 PDF。

以下实际 URL 均来自 GitHub 资产 API；无 Authorization/.netrc 登录信息的
新会话下载全部四个附件，HTTP 200、字节数与 SHA-256 均一致，ZIP CRC PASS：

| 真实公开下载 | Bytes | SHA-256 | 匿名验收 |
| --- | ---: | --- | --- |
| [main.pdf](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-final-20261013/main.pdf) | 6,713,742 | `7a6f8459cd3cf57f8e7167a8d18846ed704b1cb92bd32e43da279bb54a8d652d` | HTTP 200; hash PASS |
| [MSA_DTI_Final_Publication_20261013.zip](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-final-20261013/MSA_DTI_Final_Publication_20261013.zip) | 7,070,509 | `412e75739676e23e8fb1e61bd3ca3355a07ad84c3afe3da653bd89f3a43af8b9` | HTTP 200; CRC PASS |
| [SHA256SUMS.txt](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-final-20261013/SHA256SUMS.txt) | 264 | `dcd6b82c3bfa5760dfe397e966b2489d9430ac6a31e3ee7812a14b93c4ffcd54` | HTTP 200; hash PASS |
| [supplementary.pdf](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-final-20261013/supplementary.pdf) | 688,053 | `6540643096e81f567dc5b4128494443cffdb92dea8864e048635953fb9e135b0` | HTTP 200; hash PASS |

GitHub 固定发布提交中的 main.tex/main.pdf/supplementary.tex/supplementary.pdf
另行匿名下载，全部与本地当前文件哈希一致；上传 Git tree 与本地已审查树完全相同。

## 本轮重新查询的历史保护验收

`v1.2.7` Tag 完整 ref JSON 与本轮操作前快照逐字段相同，仍为
`b679181b3133ab9c3058afcde421d36380001f14`。Release ID `379563925`、
名称/描述/Tag/时间戳等全部未变，原 30 附件如下逐项保持。
Light Release `411251612` 的 1 附件及 Full Evidence Release `411350775` 的
9 附件和其 Release 字段亦全部相同。每个附件比较 ID、名称、大小、digest、
创建/更新时间、内容类型和真实下载 URL，仅忽略正常增长的 download_count。
本轮 `PROTECTED_HISTORY_VERIFICATION.json` SHA-256：
`0c5c69c3c75c1dcdd90b09b2751cdf0bd66f890e5e174f6db253d846be857464`。

| 原资产 ID | 名称 | Bytes | SHA-256 | before/after |
| ---: | --- | ---: | --- | --- |
| 548262778 | `fig1.pdf` | 1,882,938 | `54869cfba26b78804426b5a31812828b12364ee58cd7cbf1f11d75f65cd9541c` | unchanged |
| 548262898 | `fig2.pdf` | 769,988 | `be4ba889e4d64879b6805f2af55e3140eaad87708fe22e0d13e4b0886704955f` | unchanged |
| 548262905 | `fig3.pdf` | 473,188 | `9e090b38dfba4205b2078e7ddfd0a70b3128657ce2a23e56bbf8cc3f5fb49abb` | unchanged |
| 548262914 | `fig5.pdf` | 66,530 | `484d4cc596ef253febc639a35fc7835f5fa24fb1b573102cdc5332c7a7260622` | unchanged |
| 548262915 | `fig_overall_performance_ours.pdf` | 25,789 | `5ab0446efcc4645d22da4aacaa4efcc553197a4c1b73d519f7975199ece9047a` | unchanged |
| 548262917 | `repeated_runtime_summary.csv` | 1,788 | `96743546996ff16a571a80856577ff436f5f2869d753cedac5afeee1510a2722` | unchanged |
| 548262923 | `repeated_runtime_summary.json` | 6,234 | `9ae75a63f8daca8a3d242bc903651b8dc922f93c76a1122d4dc16d5d413f299f` | unchanged |
| 548262930 | `deployment_tradeoff_radar_data.csv` | 639 | `563a8618667ebe69931813aae6c0a65427ce8ed69b77a68caf46811ad1d44883` | unchanged |
| 548262931 | `h_meta_nas_current_large_window_runtime_manifest.json` | 7,032 | `a123944aed9ada1a02f63a28d6963cd8d4c2e46837668a1997ccc01ef2af7834` | unchanged |
| 548262932 | `h_meta_nas_current_large_window_runtime_raw.json` | 295,639 | `26337c9d9b922f2e30f5d9d045a7f3c9cd6854620c45940a8bc2749e9e9e3e77` | unchanged |
| 548270071 | `level_c_bootstrap_v1.2.7.zip` | 64,258,937 | `365df44a8cf4de1cabb21dd21aa6e865aff83a3f30d083e91caf18ed744ef650` | unchanged |
| 548270078 | `cuda_replay_evidence_v1.2.7.zip.sha256` | 98 | `0bb47594c8eff9b15fe04f18038ad3277290c3faa3e947c49f260ca722192167` | unchanged |
| 548270079 | `cuda_replay_evidence_v1.2.7.zip` | 239,612 | `40c2bca3909142326df77f7af5c1698c6bbcc152eb7d36b28c147f0d4aa8a215` | unchanged |
| 548270081 | `level_c_bootstrap_v1.2.7.zip.sha256` | 95 | `6ec1ffda853361ac028947cb53d755241dcfc94b9b0768d7c55ab99f3728f550` | unchanged |
| 548270082 | `paper_alignment_v1.2.7.zip` | 10,527,416 | `4bf8b06f746c42746d748252c5bf2eb7f9e3ac4ff7197647a12a9197dfa8b15f` | unchanged |
| 548270092 | `msa_dti_v1.2.7_complete.zip` | 43,069,520 | `c317e78abbd272cc5870a39acb673f48b7ccba05a7c515c8a322fab06bb803e6` | unchanged |
| 548270093 | `paper_alignment_v1.2.7.zip.sha256` | 93 | `38e3a97402e6ba333a675022476aa25af118da681663faebdeb02f11c6a6e8b0` | unchanged |
| 548270100 | `msa_dti_v1.2.7_complete.zip.sha256` | 94 | `73708434a2c0b89638b70fd8222ff6cded16ef207fda2b4f7399e048b5aaa1a6` | unchanged |
| 548270105 | `MSA_DTI_FIGURE_CODE_v1.2.7.zip` | 6,042,751 | `8bc63df7438bfb43661356786b6c451c7882d6fe87eb27733db200a176e3a344` | unchanged |
| 548270108 | `MSA_DTI_FIGURE_CODE_v1.2.7.zip.sha256` | 97 | `0384d3ddc78d835185fb790a53a0c604df5ef17d93d0d54756968b0b18743201` | unchanged |
| 548270110 | `SHA256SUMS.txt` | 477 | `7922d1aad4e1f3ad6da4e7b6d1709927dd1b80134959422f2d8471deee18e218` | unchanged |
| 548270116 | `manuscript.tex` | 57,722 | `16640e0c3a431faf83b8b0a735c6d3fce9ce08f4a042935731d10c1973610c91` | unchanged |
| 548270119 | `manuscript.pdf` | 3,226,919 | `e07bc8023379470051279aea30e803498d79580591fe5cda197290bf5a2954b0` | unchanged |
| 548270121 | `supplementary.tex` | 35,672 | `b011f2103ed393729c06300842131d051a2ff752a235fafeb13982e524e69d7c` | unchanged |
| 548270128 | `supplementary.pdf` | 292,478 | `bbf2388ffa6eacbcc8db50c2ec9a59aa405c5bf86d12d44b8ec50f0d73e7ddd1` | unchanged |
| 548273748 | `V1.2.7_FINAL_ASSET_SHA256SUMS.txt` | 1,893 | `0ed63cb0e39b924573084a2502d3ff47dbd7715f9925a646687258d292ad0e74` | unchanged |
| 630005340 | `MSA_DTI_Manuscript_20261011_SHA256SUMS.txt` | 298 | `148079d0e0f84014a370bf631edf26a659448ec8a899ef63545a8e0dc2640d45` | unchanged |
| 630005342 | `MSA_DTI_Supplementary_20261011.pdf` | 330,680 | `155f27aa8864b133c71c54e122482d817bec6d59edea2da63821aa110e7dcfc6` | unchanged |
| 630005344 | `MSA_DTI_Manuscript_v1.2.7_20261011.zip` | 6,354,734 | `f9d6685eede09e061763e0f7a0c05c0eedaecc83a31073a6a7b10994d1aefe04` | unchanged |
| 630005346 | `MSA_DTI_Main_20261011.pdf` | 3,454,633 | `4f3232c55344f288ccf4f2fd6352b9772e74c2bd2c972c394436645206be31be` | unchanged |

main 仍为 `d9c37592b8293dc9a2726392915b6ed365e89aa5`；发布变更保留在
`publish/current-evidence-20261013` 和 draft PR #9。没有 force push、旧 Tag 移动、
旧 Release 编辑、附件覆盖、历史改写、自动合并或 Ready for Review 操作。
四个旧根级论文文件明确未获本轮删除授权，全部保留。

最终仓库检查：`git diff --check` PASS；
`python scripts/verify_repository.py` 返回 `PASS_PUBLIC_REPOSITORY_VERIFICATION`，
包含冻结协议、数值一致性、隐私、哈希、论文对齐与 release hygiene 检查。
60 个相关 Markdown 相对链接无缺失，当前 25 条科学文件 SHA-256 全部通过。
本轮 Git diff 只有新增/修改路径，没有删除、移动或历史内容误改。

## 剩余事项

本轮发布收口没有未完成项。作者最后确认、PR 合并及 ChatGPT 针对性版本一致性
验收仍由作者决定，本轮不自动执行。作者/单位/CRediT 等供稿信息及模板 First Author
页脚保持供稿原状。既有 R5 历史 RNG 缺口、第三方数据未再分发、Alibaba 非新盲测
群体和 from-raw 独立训练未执行等研究证据限制已准确保留；本轮未扩大证据等级。
