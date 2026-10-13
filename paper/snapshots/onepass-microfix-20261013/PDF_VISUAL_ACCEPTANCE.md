# PDF_VISUAL_ACCEPTANCE

**Verdict: PASS**

Final PDF formatting acceptance for the authorized one-pass microfix. This is a layout/content-rendering check, not a new scientific review. No source, PDF, figure, experiment, or author research code was changed in this acceptance step.

## Final files checked

| File | Pages | Bytes | SHA-256 |
|---|---:|---:|---|
| `build/revised/main.pdf` | 16 | 6714049 | `60206ea71d4ee7531b2058d00f3903a96a77aea25e6fad03bcd1b80b99458853` |
| `build/supplementary_final/supplementary.pdf` | 15 | 759225 | `528a4ae7f3762f3e2cb104f34e2161842b362b312ddf5db5877e0d70dfd5edd8` |

## Visual coverage and result

- Reviewed all 16 main pages and all 15 supplementary pages in the final contact sheets.
- Inspected full-size main pages 7, 8, 10, and 13, and supplementary pages 4, 12, and 13.
- No clipped text, overlapping text, cut-off captions, or new formatting defects were found in the reviewed final rendering.
- Main pages 7-8: the extended paired-initialization definition and neighboring Algorithm 1 / Eq. (12) remain readable and properly spaced.
- Main page 10: Figure 5 and its added NAS-label sentence fit without caption overlap.
- Main page 13: both authorized heterogeneous-bank wording changes fit normally with Tables 3 and 4.
- Supplementary page 4: Table S3 shows `Strict MSE wins (%)` within the column; its numerical values and footnote digits match the baseline, including 71.25%, 13 retained cases, and the 7.7 x 10^-9 bound. The original footnote wording remains intact.
- Supplementary page 12: `Frozen Bitbrains data protocol.` has its own paragraph above the table; the complete unnumbered table has exactly 8 body rows, fits within the text width, and has no collision with its note or the dataset footnote. Rendered facts include 1,082 eligible VMs, 86,400 s / 86,107 s, the 899,799-903,397 s span, and window tuples `(10, 1,351, 628, 627)`, `(20, 1,346, 625, 625)`, `(10, 1,346, 624, 624)`, and `(20, 1,342, 621, 621)`.
- Supplementary page 13: the following five-criterion table remains Table S9, with normal spacing and readable text. Existing supplementary captions remain Table S1 through Table S10; the protocol table introduced no numbered caption.

## Machine checks

- All 31 PDF pages have nonempty extracted text; main minimum 1,927 characters, supplementary minimum 2,534 characters.
- Main has 8 URI annotations; supplementary has 2. All baseline URI targets are retained. The new public protocol ZIP URI is embedded on supplementary page 12 and the two relative source paths render fully.
- Independently hashed all 21 fixed project resource files against the baseline: all are byte-identical, including the 16 figure files and 2 external table files. Current source hashes match the final scope receipt, whose result is PASS.
- Final supplementary log has zero overfull warnings. The main log retains the preexisting CAS `maketitle` warning: `Overfull \hbox (117.0831pt too wide) detected at line 103`. The same warning occurs in the baseline and main page 1 is raster-identical to the baseline. This unchanged template warning is not a new local formatting defect.

**Acceptance boundary:** PASS is limited to the authorized final PDF formatting, rendered text, embedded URI presence, and frozen-resource checks above. No new academic findings or scientific changes are proposed. Detailed machine evidence is in `PDF_QA_RECEIPT.json`.
