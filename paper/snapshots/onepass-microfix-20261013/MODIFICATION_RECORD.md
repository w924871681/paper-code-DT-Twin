# Exact authorized MSA-DTI one-pass modification record

Date: 2026-10-13. Sole baseline: `MSA_DTI_Final_Publication_20261013_SuppFix.zip`, SHA-256 `551411789fab9334a03c29d9931294aa9a10a0597038a1e6e201f9e774a7356f`.

S1/S5/S8: KEEP. S9: DEFER (author/affiliation/corresponding author/CRediT). No new review, training, experiment, parameter tuning, or plot replacement.

| Operation | Scientific source | Baseline byte span | Exact new text / insertion |
| --- | --- | --- | --- |
| S4 | main.tex | [27447, 27630) | The paired-initialization control adapts both source-trained A57 candidates on<br>the same support set and applies the same relative-margin rule at each $\tau$ to<br>select one using validation loss. The selected model's check-set loss is the<br>paired-control denominator; because the two source-training recipes differ, this<br>is a same-architecture selection control rather than a random-seed-only<br>comparison. |
| S6 | main.tex | [36766, 36766) | NAS-related labels denote task-matched control implementations, not exact reproductions of published algorithms. |
| S7.1 | main.tex | [45356, 45462) | The reference-only and two-reference-initialization variants do not reproduce<br>the gain of the complete heterogeneous-bank pipeline. |
| S7.2 | main.tex | [45986, 46051) | The heterogeneous-bank pipeline gain remains sensitive to source training. |
| S3 | supplementary.tex | [15716, 15733) | Strict MSE wins (\%) |
| S2 | supplementary.tex | [41729, 41729) | 8-row unnumbered frozen Bitbrains protocol table after the first §S7.5 paragraph; exact content is in SOURCE_MINIMAL_DIFF.patch and SOURCE_APPLY_RECEIPT.json. All numbers map to BITBRAINS_PROTOCOL_EVIDENCE.md. |

Only a new-table paragraph break and noindent were added during S2 layout acceptance. All S2 scientific text/numbers stayed unchanged; see S2_LAYOUT_DELTA_RECEIPT.json.

Unchanged byte-for-byte: Abstract, other Introduction/Related Work text, Conclusion, 13 numbered main equations, Algorithm 1, existing statistics/margins/results, Alibaba correction, R5 provenance limits, 16 figure PDFs, 2 external tables, bibliography, Data Availability, and all source bytes outside the authorized spans.

Recompiled scientific outputs:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| main.tex | 64127 | `6dda115609d48d7e925cda8ee7258690d5f32c2df9e2d76645fcb29fda7d654b` |
| supplementary.tex | 53848 | `ac78343570372305625e09b635b5f8998bb453bada444628caa05b63f3d58ca8` |
| main.pdf | 6714049 | `60206ea71d4ee7531b2058d00f3903a96a77aea25e6fad03bcd1b80b99458853` |
| supplementary.pdf | 759225 | `528a4ae7f3762f3e2cb104f34e2161842b362b312ddf5db5877e0d70dfd5edd8` |
