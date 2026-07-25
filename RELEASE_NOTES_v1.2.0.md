# v1.2.0 - hosting and Alibaba external validation

This release extends the journal-submission archive with real hardware
profiling and a stricter external-domain evaluation.

## Hardware profiling

- Six unique retained architectures are profiled for H in {1, 4}.
- Measurements cover an Intel Core i7-12700H CPU and an NVIDIA RTX 3060
  Laptop GPU.
- Batch size is one, with 100 warm-ups and five repetitions of 1000 timed
  inferences.
- Estimated operation count is compared with median inference latency.
- Parameter count is compared with serialized model size.

## Alibaba external-domain protocol

- 20 source machines;
- 20 disjoint calibration machines, yielding 80 calibration cases;
- 40 disjoint held-out machines, yielding 160 target cases;
- source-only normalization;
- frozen architecture definitions, complexity limits, target adaptation,
  and threshold grid;
- held-out target results opened only after selector values are frozen.

Under zero recalibration with the previously frozen 10% rule, the held-out
aggregate MSE reduction is 4.29%. The mean case-level reduction is 4.20%,
with a machine-clustered 95% confidence interval of [2.03%, 6.70%].
There are 57 alternative selections: 47 beneficial and 10 harmful. No
Alibaba-specific threshold satisfies every preregistered calibration
criterion.

## Scientific boundaries

The frozen 80-case main synthetic comparison, data seeds, source-training
seeds, candidate-bank identities, reference candidate, target optimizer,
50-update adaptation budget, complexity limits, and 10% main selector
threshold are unchanged. The Alibaba result supports positive average
external transfer but does not establish a distribution-independent 5%
harmful-selection guarantee.
