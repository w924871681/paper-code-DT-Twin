# Current MSA-DTI manuscript — final Data Availability revision, 2026-10-13

This directory is the **single current manuscript entry** for the JNCA paper.
Its sole scientific baseline is the author-provided
`MSA_DTI_PositiveEvidence_Mainline_20261013.zip` (SHA-256
`b7e7a76dac91b5fa9b4fef91bbe5df5d1bc88f63ef3cd74cc817888e92435870`).
The closure revision updates only `main.tex`'s Data Availability and the main
PDF compiled from that revision. All other main-paper scientific content is
unchanged. The Supplementary TeX/PDF, 16 figure PDFs, two external tables and
three CAS template/bibliography files remain byte-identical to the source
ZIP: 23 unchanged scientific members. `SHA256SUMS.txt` records the current
25 scientific files.

- [Current main paper PDF](compiled/main.pdf) (16 pages) and [source](main.tex)
- [Unchanged Supplementary PDF](compiled/supplementary.pdf) (15 pages) and [source](supplementary.tex)
- [Figures](figures/), [tables](tables/), and [SHA-256 checksums](SHA256SUMS.txt)
- [Final manuscript-only Release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/manuscript-final-20261013)
- [Complete final LaTeX ZIP](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-final-20261013/MSA_DTI_Final_Publication_20261013.zip), [released main PDF](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-final-20261013/main.pdf), [released Supplementary PDF](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-final-20261013/supplementary.pdf), and [release SHA-256 list](https://github.com/w924871681/paper-code-DT-Twin/releases/download/manuscript-final-20261013/SHA256SUMS.txt)
- [Compilation and publication acceptance status](../../publication/20261013/MANUSCRIPT_PUBLICATION_STATUS.md)
- [Final closure acceptance report](../../publication/20261013/FINAL_PUBLICATION_CLOSURE_REPORT.md)
- [Build details](BUILD_INFO.md), [build log](BUILD_LOG.txt), and [exact source diff](SOURCE_MINIMAL_DIFF.patch)

Compile a clean writable copy using `latexmk -pdf main.tex` in a complete
LaTeX environment with the supplied CAS files. The Supplementary source is
unchanged, so its verified author-supplied PDF is retained. Final compilation,
local package checks and page checks passed: the revised main PDF was compiled
in three successful direct `pdflatex` runs, and a clean extraction of the final
ZIP rebuilt the identical PDF. The toolchain used MiKTeX-pdfTeX 4.23,
MiKTeX 25.12 and CAS 2.4 (2024/05/04). All four new release attachments were
downloaded anonymously with HTTP 200 and matched their local sizes and
SHA-256 values; the 30-member ZIP passed CRC. The scientific source/PDF
publication commit is
[`4e8bf03558340506c47b6187f2a4e7642ecb2708`](https://github.com/w924871681/paper-code-DT-Twin/commit/4e8bf03558340506c47b6187f2a4e7642ecb2708).
See the closure report above for final acceptance.

The [expanded evidence Release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-full-20261013)
retains the pre-Data-Availability-revision manuscript attachments and the
expanded experiment assets. The
[light evidence Release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-r5-bitbrains-20261013),
historical `v1.2.7` tag, and `paper/manuscript_20261011/` remain unchanged.
Internal review materials from the source ZIP are excluded from public
manuscript packages. Author, affiliation, CRediT and disclosure details remain
as supplied.
