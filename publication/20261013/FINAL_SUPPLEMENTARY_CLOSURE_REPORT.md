# MSA-DTI / JNCA Supplementary §S7.4 final publication closure

**Status: PASS (2026-10-13).** The sole scientific source edit is the correction of one obsolete public-deposit sentence in Supplementary §S7.4. The 15-page Supplementary PDF was recompiled from the revised source. The previously published 16-page main PDF and `main.tex` retain their exact SHA-256 values. The new complete LaTeX archive and four Release attachments passed local, clean-extraction, anonymous-download and historical-version checks.

## Unique baseline and exact authorized edit

The modification baseline is the already public [`manuscript-final-20261013` Release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/manuscript-final-20261013), not an older author ZIP. Its complete LaTeX archive `MSA_DTI_Final_Publication_20261013.zip` is 7,070,509 bytes, SHA-256 `412e75739676e23e8fb1e61bd3ca3355a07ad84c3afe3da653bd89f3a43af8b9`; all 30 ZIP members passed CRC. Before editing, the repository and this archive agreed on all three mandated input hashes:

| Baseline input | SHA-256 |
| --- | --- |
| `main.tex` | `55a5d395f1e640bfa970d7af12e3400e28b7884a8ac6fc339048256291bb8613` |
| `main.pdf` | `7a6f8459cd3cf57f8e7167a8d18846ed704b1cb92bd32e43da279bb54a8d652d` |
| `supplementary.tex` | `7f13409419410c255c92da562cb20535eee796fa823bb90a2c1e2eb2ff1d4063` |

Location: `paper/current/supplementary.tex`, §S7.4 *Causally corrected Alibaba workload evaluation*, original lines 881–883. The exact original sentence was:

> A separate corrected reproducibility archive retains protocol locks, model checkpoints, case-level records, and plots; it has not yet been publicly deposited.

Its exact replacement is:

> The corrected reproducibility archive containing protocol locks, model checkpoints, case-level records, and plots is publicly available in the dated evidence-only Release cited in the main manuscript's Data Availability statement.

中文含义：包含协议锁定记录、模型检查点、逐案例结果及图表的因果纠正实验复现归档，现已通过正文 Data Availability 所引用的独立证据 Release 公开。该事实对应已发布的 [`evidence-full-20261013`](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-full-20261013)。

The exact source diff, relative to the prior manuscript-only Release, is:

```diff
--- manuscript-final/supplementary.tex
+++ suppfix/supplementary.tex
@@ -881,3 +881 @@
-claims. A separate corrected reproducibility archive retains protocol locks,
-model checkpoints, case-level records, and plots; it has not yet been
-publicly deposited. The third-party raw trace and large corrected input/label
+claims. The corrected reproducibility archive containing protocol locks, model checkpoints, case-level records, and plots is publicly available in the dated evidence-only Release cited in the main manuscript's Data Availability statement. The third-party raw trace and large corrected input/label
```

Byte comparison confirms that replacing the old sentence with the requested new sentence exactly produces the revised `supplementary.tex`; no other source bytes changed. The new source is 51,376 bytes, SHA-256 `c5492e3bf77085c1802424b916d663cbd1953348ba8a1ade999c6a6d7c4958f6`.

## Science and PDF checks

Relative to the previous manuscript-only Release, the 25 scientific project members differ only in `supplementary.tex` and the PDF compiled from it; the other 23 are byte-identical. In particular, `main.tex` remains 63,762 bytes with SHA-256 `55a5d395f1e640bfa970d7af12e3400e28b7884a8ac6fc339048256291bb8613`, and `main.pdf` remains 6,713,742 bytes, 16 pages, SHA-256 `7a6f8459cd3cf57f8e7167a8d18846ed704b1cb92bd32e43da279bb54a8d652d`. All 16 figures, two external tables and three CAS/template files are unchanged. Experimental numbers, confidence intervals, thresholds, conclusions, citations, formulas, captions and section numbering were not edited.

The prior and revised Supplementary sources were each compiled in separate clean directories with MiKTeX-pdfTeX 4.23 (MiKTeX 25.12), the supplied CAS 2.4 (2024/05/04) files, `SOURCE_DATE_EPOCH=1791849600` and `FORCE_SOURCE_DATE=1`. Each completed three successful passes of:

```text
pdflatex --disable-installer -interaction=nonstopmode -halt-on-error -file-line-error -recorder supplementary.tex
```

Both final-pass diagnostic lists were empty. The revised PDF is 15 pages, 741,823 bytes, SHA-256 `019c03ec74a02459168433161db4c1236e3999c448ec2b31d2bb498dd5265272`. No new unresolved references, blank pages, overfull/underfull boxes or text clipping were found. Page 11, containing the replacement sentence, was rendered and visually checked: the text is legible within the text block and does not overlap its figure, caption, following raw-data sentence or footer. The main PDF was carried forward byte-for-byte, not rebuilt or replaced.

## Complete deliverable and independent package check

The distinct `MSA_DTI_Final_Publication_20261013_SuppFix.zip` includes `main.tex`, the unchanged `main.pdf`, revised `supplementary.tex`, its newly compiled `supplementary.pdf`, all figures, two external tables, supplied CAS/bibliography files, `README_FINAL.md`, `SHA256SUMS.txt`, the one-sentence `SOURCE_MINIMAL_DIFF.patch`, and main/Supplementary build records. It has 32 members, passed ZIP CRC, and all 25 internal scientific-file SHA-256 entries matched. A complete fresh extraction compiled the revised Supplementary in three passes to a **byte-identical** PDF. The public-package screen found no personal Windows paths, credentials, private keys, raw third-party trace directories or checkpoints in this manuscript package.

| Release attachment | Bytes | SHA-256 |
| --- | ---: | --- |
| `MSA_DTI_Final_Publication_20261013_SuppFix.zip` | 7,076,672 | `551411789fab9334a03c29d9931294aa9a10a0597038a1e6e201f9e774a7356f` |
| `main.pdf` | 6,713,742 | `7a6f8459cd3cf57f8e7167a8d18846ed704b1cb92bd32e43da279bb54a8d652d` |
| `supplementary.pdf` | 741,823 | `019c03ec74a02459168433161db4c1236e3999c448ec2b31d2bb498dd5265272` |
| `SHA256SUMS.txt` | 272 | `40ba9e29a0d238cf493765a3df147dd87ea69a07da614f8486714ac78b2ed857` |

## GitHub publication and external verification

The new [manuscript-only Supplementary correction Release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/manuscript-suppfix-20261013) is ID `411532912`. Its Tag points to the reviewed [source/PDF commit `288da8f8214c33f30b6556795c31ea86c91c4d96`](https://github.com/w924871681/paper-code-DT-Twin/commit/288da8f8214c33f30b6556795c31ea86c91c4d96). GitHub's actual asset records yielded these URLs:

- [Complete LaTeX ZIP](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-suppfix-20261013/MSA_DTI_Final_Publication_20261013_SuppFix.zip)
- [Unchanged main PDF](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-suppfix-20261013/main.pdf)
- [Recompiled Supplementary PDF](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-suppfix-20261013/supplementary.pdf)
- [Release SHA-256 list](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-suppfix-20261013/SHA256SUMS.txt)

All four assets were actually downloaded with HTTP 200 in a session that sent no GitHub Authorization header or Cookie. Their byte counts, SHA-256 digests and bytes matched the local release assets; the downloaded ZIP passed CRC with 32 members. The four manuscript files at the fixed source commit (`main.tex`, `compiled/main.pdf`, `supplementary.tex`, `compiled/supplementary.pdf`) were separately downloaded without credentials and matched their local bytes and expected SHA-256 values. The seven current navigation/status documents contained 57 relative links, all resolving to present repository files; the new public asset URLs were verified by the anonymous downloads. The current README and evidence index distinguish this Release from the unchanged previous manuscript Release and experimental evidence Releases.

## Repository scope and historical protection

The source publication commit updated only the two Supplementary scientific files, the current SHA-256 list, new Supplementary build/diff records, and necessary manuscript navigation/status documents. `.gitattributes` now marks only `paper/current/compiled/*.pdf` as binary in Git, preventing the global text diff driver from treating PDF bytes as lines; the staged Supplementary PDF blob was independently hashed and matched the delivered PDF exactly. No historical scientific file was deleted, moved or rewritten. The previous `BUILD_INFO.md`, `BUILD_LOG.txt`, `SOURCE_MINIMAL_DIFF.patch`, `FINAL_PUBLICATION_CLOSURE_REPORT.md`, and four root-level historical manuscript files remain as evidence of earlier versions.

Fresh before/after GitHub API comparisons after the new Release was published passed:

| Protected item | Result |
| --- | --- |
| `v1.2.7` Tag | Still `b679181b3133ab9c3058afcde421d36380001f14` |
| `v1.2.7` Release ID `379563925` | All 30 original attachments and protected Release fields unchanged |
| `evidence-r5-bitbrains-20261013`, ID `411251612` | One attachment and protected fields unchanged |
| `evidence-full-20261013`, ID `411350775` | Nine attachments and protected fields unchanged |
| `manuscript-final-20261013`, ID `411461046` | Four attachments and protected fields unchanged |
| Repository main branch | Still `d9c37592b8293dc9a2726392915b6ed365e89aa5` |
| PR #9 | Open, Draft, not merged; new work remains on `publish/current-evidence-20261013` |

The comparison covered existing asset IDs, names, sizes, digests, timestamps, content types and public URLs, and protected Release metadata; only download counters were excluded. The `v1.2.7` Tag had a direct before-ref snapshot. For the other three protected Tags, the before target was taken from their saved Release `target_commitish` because a direct before-ref snapshot was not captured; the after refs matched those targets. No old Tag or Release was edited; no force push, history rewrite, `v1.2.8`, PR merge or Ready-for-Review action occurred.

The repository validator returned `PASS_PUBLIC_REPOSITORY_VERIFICATION`; `git diff --check` passed after the PDF binary attribute was made explicit. The new source/PDF publication commit has only additions or modifications, with no deleted or renamed paths. Detailed local audit records include `SUPPFIX_BUILD_QA.json`, `SCIENCE_SCOPE_VERIFICATION.json`, `PACKAGE_RESULT.json`, `FRESH_ZIP_REBUILD.json`, `PUBLIC_ZIP_SCREEN.json`, `PUBLIC_SOURCE_BYTE_VERIFICATION.json`, `ANONYMOUS_DOWNLOAD_VERIFICATION.json` and `PROTECTED_HISTORY_VERIFICATION.json`.

No task blocker remains. The author's final confirmation and any later merge of Draft PR #9 are outside this publication task. The existing R5 historical RNG/raw-array provenance gap, third-party raw-data exclusions, corrected Alibaba's previously observed population and absence of independent from-raw end-to-end training reproduction retain their previously documented scientific scope; this status correction does not enlarge the evidence claim.
