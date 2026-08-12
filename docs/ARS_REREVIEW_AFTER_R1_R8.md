# Simulated five-seat re-review after the R1--R8 revision

## Manuscript assessed

Joint Model Selection and Adaptation for Few-Shot Predictive-Model
Instantiation in Digital Twin Platforms under Deployment Limits.

## Reviewer A: methodology and novelty

The revision now defines the target optimization object and separates the
finite pretrained candidate-bank setting from frozen model-bank selection,
single-reference PT+FT, and target-side architecture search. The component
analysis also makes clear that the relative margin is a conservative
replacement rule rather than the sole source of the accuracy gain. R1 is
substantially resolved.

The remaining methodological issue is bank-construction stability. The
three-seed experiment retrains a fixed architecture list; it does not repeat
the original screening decision. This limitation is now stated correctly,
but it leaves R2 only partially resolved.

Recommendation: major revision, focused on one candidate-screening stability
experiment.

## Reviewer B: experiments and statistics

The main paired MSE reduction now includes a center-cluster 95% interval of
[9.41%, 20.14%]. The all-case harmful-selection rate is 3.75%, with a
center-cluster interval of [0.00%, 7.50%], and the manuscript no longer
implies that the population harmful rate is proven below 5%. The 5% value is
identified as an ex ante point-estimate tolerance. R3 is resolved.

The optimizer-matched table materially improves baseline transparency. The
remaining comparisons still have method-specific source initializations and
selection rules, which the manuscript discloses. Full screening-resample
stability remains the only important missing experiment.

Recommendation: major revision because of R2; otherwise statistically
acceptable.

## Reviewer C: systems and deployment

The paper now reports per-architecture batch-one profiling on the stated CPU
and GPU, including latency, serialized size, and peak GPU allocation. It also
states that operation count and parameter count are complexity indicators,
not hardware guarantees, and that the single host is not a cross-platform
benchmark. This resolves the previous claim-evidence mismatch in R5.

A second device would strengthen the paper but is not required if the current
scope is preserved. The predictive component is now placed within DT
monitoring, synchronization, and resource-management workflows, resolving
R6.

Recommendation: minor revision.

## Reviewer D: JNCA editorial fit

The revised title and framing are more suitable for JNCA because the paper no
longer equates a workload predictor with an entire digital twin. The external
Alibaba result is treated as workload-domain transfer, and failure to obtain
an eligible domain margin now triggers a reference fallback in calibrated
deployment. R7 is resolved.

Author names, affiliations, corresponding-author information, CRediT roles,
and funding remain placeholders. These values cannot be inferred and must be
completed before a non-anonymous submission.

Recommendation: major revision until R8 is completed; editorially suitable
afterward.

## Reviewer E: language, consistency, and integrity

The revision retains the manuscript's direct engineering style and controlled
claim strength. Terminology is now consistent around a DT predictive-model
component. No new citation, fabricated result, or unverified hardware claim
was introduced. The main and supplementary titles, tables, and fallback
wording are aligned.

Recommendation: minor revision for metadata and final copyediting only.

## Integrated decision

**Decision: Major Revision.**

R1, R3, R4, R5, R6, and R7 are closed at the manuscript level. R2 is only
partially closed because architecture screening has not been repeated across
independent screening pools. R8 remains open because real submission metadata
has not been supplied. With the R2 experiment completed and R8 populated (or
an anonymous-review workflow confirmed), the expected next simulated decision
is Minor Revision rather than another broad methodological revision.
