# Current manuscript publication status — final Data Availability revision

**Compilation and local package verification PASS; new public-release and
anonymous-download acceptance pending.**
The single current JNCA manuscript entry is [`paper/current/`](../../paper/current/).
Its sole source baseline is `MSA_DTI_PositiveEvidence_Mainline_20261013.zip`
(7,056,735 bytes; SHA-256
`b7e7a76dac91b5fa9b4fef91bbe5df5d1bc88f63ef3cd74cc817888e92435870`).
The source ZIP passed CRC and all 29 internal hash checks. Before this revision,
all 25 scientific members in `paper/current/` matched it byte-for-byte.

This revision is limited to the main paper's Data Availability and the PDF
compiled from that source. The revision's `main.tex` SHA-256 is
`55a5d395f1e640bfa970d7af12e3400e28b7884a8ac6fc339048256291bb8613`.
All main-paper scientific content outside that section remains unchanged.
The other 23 scientific members—Supplementary TeX/PDF, 16 figures, two
external tables and three CAS template/bibliography files—remain byte-identical
to the baseline. The Supplementary remains 15 pages.

The revised main PDF is 16 pages, 6,713,742 bytes, SHA-256
`7a6f8459cd3cf57f8e7167a8d18846ed704b1cb92bd32e43da279bb54a8d652d`.
The retained Supplementary PDF is 15 pages, 688,053 bytes, SHA-256
`6540643096e81f567dc5b4128494443cffdb92dea8864e048635953fb9e135b0`.
The local `MSA_DTI_Final_Publication_20261013.zip` is 7,070,509 bytes,
SHA-256 `412e75739676e23e8fb1e61bd3ca3355a07ad84c3afe3da653bd89f3a43af8b9`.
Its CRC and 29 internal member hashes passed; compiling a clean extraction in
three runs rebuilt the identical main PDF.

Compilation used MiKTeX-pdfTeX 4.23 / MiKTeX 25.12, CAS 2.4 (2024/05/04),
with sttools 3.5 and cm-super 0.3.4 installed. The baseline and revision each
completed three direct `pdflatex` runs with exit code 0. Compared with the
baseline compiled under the same toolchain, pages 1–14 and the portion of
page 15 before Data Availability are pixel-identical. No new Overfull Box,
unresolved-reference or visible-cropping defect was found. The CAS title-page
Overfull Box warning of 117.0831 pt exists in both builds with no visible
defect. See [build details](../../paper/current/BUILD_INFO.md),
[build log](../../paper/current/BUILD_LOG.txt) and
[exact source diff](../../paper/current/SOURCE_MINIMAL_DIFF.patch).

The separate [manuscript-only Release entry](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/manuscript-final-20261013)
is for this public-data-statement revision, not a new experiment version.
Its final ZIP, PDF hashes, actual download URLs, compiler details, page checks
and anonymous-download results will be recorded in
`FINAL_PUBLICATION_CLOSURE_REPORT.md` after acceptance. Public-release and
anonymous-download PASS are not asserted before those checks complete.

The [expanded evidence Release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-full-20261013)
retains its nine original attachments. Its
[pre-revision manuscript project ZIP](https://github.com/w924871681/paper-code-DT-Twin/releases/download/evidence-full-20261013/MSA_DTI_Current_Manuscript_PUBLIC_20261013.zip)
has 27 members, 7,049,373 bytes and SHA-256
`e50f18b2dfd0787ead977d16675c45294f79328424d4615d2cbc0fa575df99e2`;
the earlier public download matched that hash and passed CRC. Those author-
supplied main/Supplementary PDFs were 16/15 pages. The previous release's
failed local compilation attempt is historical; it does not certify the
current revised main PDF.

The [light evidence Release](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/evidence-r5-bitbrains-20261013),
`v1.2.7`, the 2026-10-11 manuscript tree and the four root-level historical
paper files are retained. PR #9 remains a draft and is not automatically
merged or marked ready for review. Final protection checks for all three
existing releases are part of the new closure acceptance.
