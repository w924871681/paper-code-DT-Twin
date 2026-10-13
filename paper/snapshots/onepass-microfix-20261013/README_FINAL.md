# MSA-DTI current manuscript project — Supplementary status correction (2026-10-13)

This manuscript-only correction starts from the previous public
`manuscript-final-20261013` LaTeX ZIP. The main TeX and its 16-page PDF are
byte-identical to that Release (SHA-256:
`55a5d395f1e640bfa970d7af12e3400e28b7884a8ac6fc339048256291bb8613`
and `7a6f8459cd3cf57f8e7167a8d18846ed704b1cb92bd32e43da279bb54a8d652d`).
The sole new source edit replaces one publication-status sentence in
Supplementary Section S7.4. The corresponding Supplementary PDF was rebuilt
from that source and remains 15 pages. The 16 figures, two external tables,
and three supplied CAS files remain byte-identical to the previous Release.

Extract the ZIP to a writable directory in a complete TeX Live or MiKTeX
environment. Compile each source in a clean working directory; run pdflatex
three times for resolved references:

    pdflatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
    pdflatex -interaction=nonstopmode -halt-on-error -file-line-error supplementary.tex

The actual Supplementary build used MiKTeX-pdfTeX 4.23, CAS 2.4
(2024/05/04), `--disable-installer -recorder`, `SOURCE_DATE_EPOCH=1791849600`,
and `FORCE_SOURCE_DATE=1`. Read SUPPLEMENTARY_BUILD_INFO.md and
SUPPLEMENTARY_BUILD_LOG.txt for this correction; BUILD_INFO.md and
BUILD_LOG.txt preserve the earlier main-paper build record. No personal
absolute path or research data is required to compile the project.

SHA256SUMS.txt covers the 25 scientific project files. The
SOURCE_MINIMAL_DIFF.patch contains only the S7.4 sentence correction relative
to `manuscript-final-20261013`. No experiments, model training, calibration,
or statistical recomputation were performed.

Current manuscript-only Release:
https://github.com/w924871681/paper-code-DT-Twin/releases/tag/manuscript-suppfix-20261013
Previous main Data Availability revision:
https://github.com/w924871681/paper-code-DT-Twin/releases/tag/manuscript-final-20261013
Expanded experimental evidence:
https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-full-20261013
Frozen synthetic study:
https://github.com/w924871681/paper-code-DT-Twin/releases/tag/v1.2.7
