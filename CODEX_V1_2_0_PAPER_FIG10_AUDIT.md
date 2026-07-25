# v1.2.0 manuscript, Fig. 10, hosting, and Alibaba audit

## Supplied authority

- `paper/manuscript.tex`
- `paper/manuscript.pdf`
- `paper/figures/fig10.pdf`
- `paper/figures/fig12.pdf`
- `results/figure_data/fig12_case_level_gains.csv`
- `results/figure_data/fig12_group_summary.csv`
- `results/pre_submission_enhancements/hosting/`
- `results/pre_submission_enhancements/alibaba_domain/`

The manuscript source and compiled PDF are the textual authorities for the
v1.2.0 release. The compiled PDF contains 22 pages and the v1.2.0 Data
Availability reference.

## Fig. 10 scope

Fig. 10 retains the released normalized multi-axis comparison. The figure
continues to read the public raw MSE, Worst-10%, CVaR90, target-side
instantiation time, parameter-count, and estimated-operation-count values.
For every lower-is-better axis, the displayed score remains:

```text
100 * minimum raw value / method raw value
```

The v1.2.0 release does not change the Fig. 10 raw values or normalization.
The new hardware-profile evidence is reported separately in the manuscript
and public result files. It supports the interpretation that estimated
operation count and parameter count describe complementary hosting
properties; it is not used to alter Fig. 10 values.

## Fig. 12 and Alibaba update

Fig. 12 now contains 400 released case-level gains:

- 240 source-training-seed cases;
- 160 held-out Alibaba cases.

The Alibaba panel uses the frozen `tau = 0.10` zero-recalibration rule.
One Alibaba case is below -25% and is clipped only for display; all original
values remain in the released CSV and statistical analysis.

The formal Alibaba protocol uses:

- 20 source machines;
- 20 disjoint calibration machines, yielding 80 calibration cases;
- 40 disjoint held-out machines, yielding 160 target cases;
- source-only normalization;
- frozen architecture definitions, complexity limits, target adaptation,
  and threshold grid;
- held-out target results opened only after selector values are frozen.

The held-out reference and selected mean MSE values are approximately
0.001337 and 0.001279, giving a 4.29% aggregate reduction. The mean
case-level reduction is 4.20%, with a machine-clustered 95% confidence
interval of [2.03%, 6.70%]. There are 57 alternative selections: 47
beneficial and 10 harmful. No Alibaba-specific threshold satisfies all
pre-registered calibration criteria.

## Scientific boundaries

This release does not change the frozen 80-case main synthetic comparison,
data seeds, source-training seeds, main candidate-bank identities, reference
candidate, target optimizer, 50-update adaptation budget, complexity
limits, or the 10% main selector threshold.

The Alibaba result supports a positive average external-domain transfer
effect under the frozen rule. It does not establish a
distribution-independent 5% harmful-selection guarantee.

## Release acceptance checks

The v1.2.0 tag and release must be created only after all of the following
complete successfully:

```text
python -m pytest
python scripts/verify_repository.py
python scripts/run_smoke_test.py
```

The public repository verification must report:

```text
PASS_PUBLIC_REPOSITORY_VERIFICATION
```

The release tree must not contain raw Alibaba traces, processed trace arrays,
model weights, local absolute paths, user identifiers, or untracked
experimental output directories.
