# Current MSA-DTI manuscript — 2026-10-13

This directory is the **single current manuscript entry** for the JNCA paper. It
reproduces the scientific source and supplied compiled outputs of the author-
provided `MSA_DTI_PositiveEvidence_Mainline_20261013.zip` (SHA-256
`b7e7a76dac91b5fa9b4fef91bbe5df5d1bc88f63ef3cd74cc817888e92435870`).
The two TeX sources, two PDFs, 16 figure PDFs, two external TeX tables, and
three CAS template/bibliography files are byte-identical to that source ZIP.
`SHA256SUMS.txt` covers those 25 source files. The historical `v1.2.7` tag and
`paper/manuscript_20261011/` are archived versions, not the current paper.

- [Main paper PDF](compiled/main.pdf) (16 pages) and [source](main.tex)
- [Supplementary PDF](compiled/supplementary.pdf) (15 pages) and [source](supplementary.tex)
- [Figures](figures/), [tables](tables/), and [SHA-256 checksums](SHA256SUMS.txt)

Compile in a new writable copy with `latexmk -pdf main.tex` and
`latexmk -pdf supplementary.tex`. Do not replace the supplied PDFs with local
recompilations: the published PDF bytes are the author-supplied versions.

The source ZIP's internal review materials under `audit/` and its preliminary
README were excluded from the public publication package; no scientific
source, figure, table, or compiled PDF was edited. Author/affiliation/CRediT
details remain as supplied, without inferred additions.
