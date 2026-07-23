# v1.1.9 - revised manuscript and Fig. 10

This release is the journal-submission archive aligned to the latest supplied
LaTeX source and compiled manuscript.

## Paper alignment

The current manuscript adopts the supplied revised abstract, Introduction,
Related Work, method exposition, algorithm description, captions, result
discussion, conclusion, and reference numbering. Its Data Availability
statement points to this immutable v1.1.9 Release.

## Fig. 10 update

Fig. 10 retains the same six lower-is-better raw metrics and the same
normalization:

```text
normalized score = 100 * lowest raw value / method raw value
```

Only its presentation changes. The three resource axes now read `Target-side
time`, `Parameter count`, and `Estimated operation count`; method labels,
legend placement, font sizing, and layout follow the supplied final figure.
The canonical `reporting/final_figures.py` implementation reproduces the
updated figure from `fig10_deployment_tradeoff_data.csv`.

## Scientific invariants

No data split, random seed, candidate-bank member or order, reference
candidate, optimizer, loss, learning rate, gradient clipping, 50-update
adaptation budget, 10% selection threshold, complexity limit, plot-ready
value, or reported numerical result changes in v1.1.9.

The main held-out evaluation remains 80 cases: 47 alternative selections,
including 44 beneficial and 3 harmful under the post-selection test-MSE
audit, plus 33 reference-retained cases. Mean paired MSE reduction relative
to PT+FT remains 14.60%, and complexity-limit satisfaction remains 100%.
