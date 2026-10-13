# Current MSA-DTI manuscript — Supplementary §S7.4 correction, 2026-10-13

This directory is the **single current manuscript entry** for the JNCA paper.
Its sole scientific baseline is the author-provided
`MSA_DTI_PositiveEvidence_Mainline_20261013.zip` (SHA-256
`b7e7a76dac91b5fa9b4fef91bbe5df5d1bc88f63ef3cd74cc817888e92435870`).
The main source/PDF retain the previous Data Availability revision. This
correction changes only one public-availability sentence in Supplementary
§S7.4 and the PDF built from that source. Relative to the previous
`manuscript-final-20261013` version, the other 23 scientific members remain
byte-identical. Relative to the original author ZIP, all 16 figure PDFs,
two external tables and three CAS template/bibliography files remain
byte-identical: 21 unchanged scientific members. All Supplementary text
outside the corrected sentence is unchanged. `SHA256SUMS.txt` records the
current 25 scientific files.

- [Current main paper PDF](compiled/main.pdf) (16 pages) and [source](main.tex)
- [Current Supplementary PDF](compiled/supplementary.pdf) (15 pages) and [source](supplementary.tex)
- [Figures](figures/), [tables](tables/), and [SHA-256 checksums](SHA256SUMS.txt)
- [Current Supplementary correction Release entry](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/manuscript-suppfix-20261013)
- Planned current release downloads (publication and anonymous verification pending): [complete LaTeX ZIP](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-suppfix-20261013/MSA_DTI_Final_Publication_20261013_SuppFix.zip), [main PDF](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-suppfix-20261013/main.pdf), [corrected Supplementary PDF](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-suppfix-20261013/supplementary.pdf), and [SHA-256 list](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-suppfix-20261013/SHA256SUMS.txt)
- [Previous Data Availability manuscript Release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/manuscript-final-20261013): [previous complete LaTeX ZIP](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-final-20261013/MSA_DTI_Final_Publication_20261013.zip), [main PDF retained in the current version](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-final-20261013/main.pdf), [previous Supplementary PDF](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-final-20261013/supplementary.pdf), and [previous release SHA-256 list](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-final-20261013/SHA256SUMS.txt)
- [Compilation and publication acceptance status](../../publication/20261013/MANUSCRIPT_PUBLICATION_STATUS.md)
- [Previous Data Availability closure report](../../publication/20261013/FINAL_PUBLICATION_CLOSURE_REPORT.md)
- [Main build details](BUILD_INFO.md), [main build log](BUILD_LOG.txt), and [main Data Availability diff](SOURCE_MINIMAL_DIFF.patch)
- [Supplementary build details](SUPPLEMENTARY_BUILD_INFO.md), [Supplementary build log](SUPPLEMENTARY_BUILD_LOG.txt), and [Supplementary single-sentence diff](SUPPLEMENTARY_SOURCE_MINIMAL_DIFF.patch)

Compile a clean writable copy in a complete LaTeX environment with the supplied
CAS files. Run each of the following commands three times in sequence:

```text
pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -recorder main.tex
pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -recorder supplementary.tex
```

The recorded compiler and environment settings in the build details support
byte-identical rebuilds. When Perl is installed, `latexmk -pdf main.tex` and
`latexmk -pdf supplementary.tex` are alternatives. The Supplementary build
and acceptance records are separate from the main records linked above. For the previous
Data Availability revision, compilation, local package and page checks passed:
the revised main PDF was compiled
in three successful direct `pdflatex` runs, and a clean extraction of the final
ZIP rebuilt the identical PDF. The toolchain used MiKTeX-pdfTeX 4.23,
MiKTeX 25.12 and CAS 2.4 (2024/05/04). All four previous release attachments were
downloaded anonymously with HTTP 200 and matched their local sizes and
SHA-256 values; the 30-member ZIP passed CRC. The scientific source/PDF
publication commit is
[`4e8bf03558340506c47b6187f2a4e7642ecb2708`](https://github.com/w924871681/paper-code-DT-Twin/commit/4e8bf03558340506c47b6187f2a4e7642ecb2708).
That acceptance belongs to the previous Data Availability version; consult
the current publication status for this Supplementary correction's acceptance.

The [expanded evidence Release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-full-20261013)
retains the pre-Data-Availability-revision manuscript attachments and the
expanded experiment assets. The
[previous manuscript-only Release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/manuscript-final-20261013),
the
[light evidence Release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-r5-bitbrains-20261013),
historical `v1.2.7` tag, and `paper/manuscript_20261011/` remain unchanged.
Internal review materials from the source ZIP are excluded from public
manuscript packages. Author, affiliation, CRediT and disclosure details remain
as supplied.
