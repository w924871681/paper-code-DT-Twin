# Current manuscript publication status — 2026-10-13

**Published for review:** the single current JNCA manuscript entry is
[`paper/current/`](../../paper/current/). Its 25 scientific files are byte-identical
to the author-supplied `MSA_DTI_PositiveEvidence_Mainline_20261013.zip`
(SHA-256 `b7e7a76dac91b5fa9b4fef91bbe5df5d1bc88f63ef3cd74cc817888e92435870`).
The public [manuscript project ZIP](https://github.com/w924871681/paper-code-DT-Twin/releases/download/evidence-full-20261013/MSA_DTI_Current_Manuscript_PUBLIC_20261013.zip)
adds only publication README/checksums and excludes internal review notes.
It contains 27 ZIP members, has size 7,049,373 bytes and SHA-256
`e50f18b2dfd0787ead977d16675c45294f79328424d4615d2cbc0fa575df99e2`.
The public anonymous download matched this hash and passed ZIP CRC.

The project contains `main.tex`, `supplementary.tex`, both author-supplied
compiled PDFs (16 and 15 pages), 16 figure PDFs, two external tables and
three CAS template/bibliography files. The [internal SHA-256 list](../../paper/current/SHA256SUMS.txt)
checks all scientific files. Standalone TeX and PDF attachments are also in the
[dated evidence-only Release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-full-20261013).

**Compilation verification limit:** the supplied PDFs and TeX sources were
checked against the author ZIP. A new local compilation could not be certified:
this workstation's MiKTeX `latexmk` lacked Perl, and direct `pdflatex`
reported a missing `stfloats.sty` package. This is an environment dependency,
not evidence of a TeX-source edit; no generated PDF was substituted for the
author-supplied PDFs. A clean TeX Live or complete MiKTeX environment should
run `latexmk -pdf main.tex` and `latexmk -pdf supplementary.tex` in a writable
copy for an independent build check.

The 2026-10-11 `paper/manuscript_20261011/` tree, root-level historical
`paper/manuscript.*` files and all original `v1.2.7` Release assets remain
available as frozen history, explicitly labeled as older material.
