# Historical minimal Data Availability proposal — authorized closure revision

The author authorized the final publication closure task to apply the necessary
Data Availability correction. The original proposal below is retained as a
historical record, not the exact final replacement: the closure task also
requires explicit RNG/raw-array, previously observed population and from-raw
training limitations. The final wording and exact `SOURCE_MINIMAL_DIFF.patch`
are documented in [FINAL_PUBLICATION_CLOSURE_REPORT.md](FINAL_PUBLICATION_CLOSURE_REPORT.md). Only that section of
`main.tex` and its corresponding compiled main PDF may change.

The byte-identical pre-revision 2026-10-13 author manuscript remains preserved
in `evidence-full-20261013`; none of that release's attachments is overwritten.
At the time this historical proposal was written, no `.tex` or PDF file had
been changed. The first sentence
about the frozen `v1.2.7` synthetic study and the final third-party-source
sentence can remain as supplied. The middle sentences now describe the former
light archive and say corrected Alibaba has not been publicly deposited;
publication has made those statements stale.

## Exact pre-revision middle passage

```tex
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
has not yet been publicly deposited.
```

## Historical proposed replacement of only that passage

```tex
The supplementary R5 fixed-candidate comparison, Bitbrains in-domain
evaluation, and causally corrected Alibaba study have source code,
configurations, checkpoints, saved predictions and targets, statistical
verification records, and reproducibility notes in the dated evidence-only
Release at
\url{https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-full-20261013}.
The earlier R5/Bitbrains light-audit Release remains available at
\url{https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-r5-bitbrains-20261013}.
These archives permit independent recalculation of saved results, but do not
redistribute the third-party Bitbrains or Alibaba raw traces or their full
trace-derived input windows. R5's historical development-pool RNG provenance
remains unresolved; the corrected Alibaba result is a causal reconstruction
on a previously observed evaluation population.
```

中文说明（历史提案）：当时正文仍称 Bitbrains 没有 source checkpoint，且 Alibaba 纠正包尚未公开；新
Release 已公开可合规分发的 checkpoint、保存结果与统计证据。建议仅替换这段资料可得性文字，
保留旧轻量包的历史链接和原始数据官方获取脚注，同时准确写明第三方原始/完整衍生窗口未再分发、
R5 历史 RNG 缺口及 Alibaba 证据等级。本轮作者已授权执行必要的 Data Availability 修订，
并要求补齐准确限制说明；最终修订另存论文工程、SHA-256 和独立 manuscript-only Release，
不覆盖任何既有发布资产。最终英文与精确 Diff 以新的发布收口报告为准。
