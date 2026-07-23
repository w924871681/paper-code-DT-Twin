# v1.1.9 manuscript and Fig. 10 audit

## Supplied authority

- `manuscript_latest.tex.txt`
- `manuscript_latest.pdf`
- `RCF_DTI_FIG10_UPDATE_PACKAGE.zip`
- the matching final `fig10.pdf`

The supplied manuscript is the textual authority. Its temporary v1.1.6 Data
Availability reference is advanced to v1.1.9 only after the repository and
release workflow have been aligned. The Fig. 10 replacement instructions
state that only display labels and layout changed.

## Fig. 10 data and normalization

The figure continues to read the released plot-ready MSE, Worst-10%, CVaR90,
target-side time, parameter-count, and estimated-operation-count values.
For every lower-is-better axis, it computes:

```text
100 * minimum raw value / method raw value
```

No raw metric or normalized score is edited. The public generator uses the
explicit labels `Target-side time`, `Parameter count`, and `Estimated
operation count` and retains method-specific markers for redundant visual
encoding.

## Manuscript checks

- Every citation key has exactly one bibliography item.
- The manuscript contains no `WMSE` terminology.
- The supplied scientific protocol and all key numerical claims agree with
  the frozen repository evidence.
- The compiled v1.1.9 PDF must contain 20 pages, no undefined references, and
  the v1.1.9 Data Availability link.

## Frozen scope

This release does not change training, adaptation, selection, evaluation, or
bootstrap procedures. Test-derived beneficial/harmful labels remain
post-selection audit labels and never enter model selection.
