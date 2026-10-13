# MSA-DTI final one-pass microfix — read this first

This is the author's final strictly bounded manuscript microfix, based only on the supplied SuppFix ZIP and adopted KEEP/MODIFY taskbook. The current sources and PDFs are at this directory's root. Main:16pages;Supplementary:15pages.

Applied:S2 factual protocol insertion, S3 TableS3header, S4 paired-selector definition, S6 Figure5caption sentence, S7 two attribution phrases. S1/S5/S8 kept;S9 deferred. All original figure PDFs and external tables are unchanged. No training, new experiment, recalibration, plot redraw, or fresh simulated review occurred.

Use SOURCE_MINIMAL_DIFF.patch, MODIFICATION_RECORD.md, BITBRAINS_PROTOCOL_EVIDENCE.md, SOURCE_FREEZE_RECEIPT.json, BUILD_ONEPASS_RECEIPT.json and PDF_QA_RECEIPT.json for this revision. SHA256SUMS.txt covers all25 scientific project files. PACKAGE_SHA256SUMS.txt covers the other package members, excluding checksum files themselves.

The retained BUILD_INFO.md, BUILD_LOG.txt, SUPPLEMENTARY_BUILD_INFO.md, SUPPLEMENTARY_BUILD_LOG.txt and README_FINAL.md are historical records copied unchanged from the baseline; their prior-version statements are not the present build receipt. Original baseline checksums/diff are preserved under BASELINE_HISTORY/. The authoritative present build record is BUILD_ONEPASS_RECEIPT.json.

Recompile in a new extracted directory with an installed MiKTeX/TeX distribution and supplied CAS files: run pdflatex with the flags in BUILD_ONEPASS_RECEIPT.json three times for main.tex and three times for supplementary.tex. No author experiment scripts are part of this operation.

Independent manuscript snapshot: [manuscript-onepass-microfix-20261013](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/manuscript-onepass-microfix-20261013). All prior releases/tags/assets are preserved;PR#9 remains Draft/unmerged. The new snapshot is distinct from existing manuscript/evidence releases. Author identity/CRediT and the author's final version-consistency acceptance remain pending. No further scientific modification/review loop is authorized.
