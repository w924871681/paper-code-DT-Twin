# Method and frozen scientific protocol

RCF-DTI instantiates a target-specific digital twin model in five stages:

1. Build a source-initialization bank in which each candidate is an
   architecture paired with its matched source-trained initialization.
2. Remove candidates that exceed either assigned complexity limit.
3. Adapt every feasible candidate on the same target support data using
   SGD/MSE for exactly 50 updates.
4. Compare the best alternative with the fixed reference candidate using
   validation MSE and the preset 10% threshold.
5. Return the selected feasible architecture and adapted parameters.

Estimated operation count is a model-level proxy for inference computation,
and parameter count characterizes model size. Neither is a direct measurement
of device latency, memory use, or energy consumption.

## Invariants

v1.1.7 changes presentation, packaging, audits, and public reproducibility
code only. It does not change the data split, seeds, six-architecture bank,
seven candidates, reference candidate, optimizer, loss, 50-update budget,
10% threshold, complexity limits, or any core experimental value.

The held-out test set is opened only after the candidate and adapted
parameters are fixed. "Beneficial alternative" and "harmful alternative" are
post-selection test-MSE labels used in Fig. 6 and Fig. 11; they never enter
filtering, adaptation, threshold calibration, or selection.

Historical internal names are mapped in `INTERNAL_PROVENANCE_NAMES.md`.
