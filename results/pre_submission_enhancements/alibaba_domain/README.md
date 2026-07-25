# Alibaba External-Domain Evaluation

This directory contains anonymized processed evidence for the formal
Alibaba Cluster Trace v2018 evaluation.

Protocol:

- 20 source machines;
- 20 disjoint domain-calibration machines (80 cases);
- 40 disjoint held-out target machines (160 cases);
- source-only normalization;
- frozen six-architecture definitions and complexity limits;
- frozen target adaptation procedure;
- independent threshold calibration before opening held-out target results;
- zero-recalibration reporting with the previously frozen tau = 0.10 rule.

The original Alibaba trace, processed arrays, model weights, and local file
paths are not redistributed.
