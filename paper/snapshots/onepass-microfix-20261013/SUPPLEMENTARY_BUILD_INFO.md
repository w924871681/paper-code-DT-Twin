# Supplementary status-correction PDF build record

Source baseline: the public `manuscript-final-20261013` project. Only the one
publication-status sentence in Supplementary Section S7.4 was replaced.
The main TeX and main PDF retained SHA-256
`55a5d395f1e640bfa970d7af12e3400e28b7884a8ac6fc339048256291bb8613`
and `7a6f8459cd3cf57f8e7167a8d18846ed704b1cb92bd32e43da279bb54a8d652d`.

Compiler: MiKTeX-pdfTeX 4.23 (MiKTeX 25.12), supplied CAS single-column 2.4
(2024/05/04). Source and supplied project assets were copied to independent,
clean baseline and revised build directories. Each completed three successful
passes of:

    pdflatex --disable-installer -interaction=nonstopmode -halt-on-error -file-line-error -recorder supplementary.tex

The process environment set `SOURCE_DATE_EPOCH=1791849600` and
`FORCE_SOURCE_DATE=1`. No package dependency needed repair in this round.
The revised output is 15 pages, 741,823 bytes, SHA-256
`019c03ec74a02459168433161db4c1236e3999c448ec2b31d2bb498dd5265272`.
See `SUPPLEMENTARY_BUILD_LOG.txt` and
`SUPPLEMENTARY_SOURCE_MINIMAL_DIFF.patch`. The existing `BUILD_INFO.md`,
`BUILD_LOG.txt`, and `SOURCE_MINIMAL_DIFF.patch` record the earlier main-paper
Data Availability revision and are retained as historical build evidence.
