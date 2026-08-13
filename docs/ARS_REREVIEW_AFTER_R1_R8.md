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

The complete 66-configuration screen is now repeated on two additional
20-center samples and evaluated on a fourth untouched pool. The result is
informative but negative: retained-set sizes are 6, 0, and 4, and the new
sets have Jaccard similarities of 0 and 0.429 to the frozen set. The paper
does not conceal this instability or use it to retune the headline method;
instead, it limits the bank claim and strengthens the rationale for the
protected A57 fallback. R2 is resolved by experiment and claim reduction.

Recommendation: minor revision for presentation and metadata checks.

## Reviewer B: experiments and statistics

The main paired MSE reduction now includes a center-cluster 95% interval of
[9.41%, 20.14%]. The all-case harmful-selection rate is 3.75%, with a
center-cluster interval of [0.00%, 7.50%], and the manuscript no longer
implies that the population harmful rate is proven below 5%. The 5% value is
identified as an ex ante point-estimate tolerance. R3 is resolved.

The optimizer-matched table materially improves baseline transparency. The
remaining comparisons still have method-specific source initializations and
selection rules, which the manuscript discloses. The new rescreening study
reports center-cluster intervals and harmful rates on an untouched pool. Its
gain intervals include zero, and the manuscript states this directly rather
than presenting a robustness success. The statistical interpretation is
acceptable.

Recommendation: minor revision.

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

Recommendation: minor administrative revision. The placeholders are
acceptable for anonymous review but must be replaced before a non-anonymous
final submission.

## Reviewer E: language, consistency, and integrity

The revision retains the manuscript's direct engineering style and controlled
claim strength. Terminology is now consistent around a DT predictive-model
component. No new citation, fabricated result, or unverified hardware claim
was introduced. The main and supplementary titles, tables, and fallback
wording are aligned.

Recommendation: minor revision for metadata and final copyediting only.

## Integrated decision

**Decision: Minor Revision.**

R1--R7 are closed at the manuscript level. R2 is closed by a complete
independent rescreening experiment and an appropriately narrower claim, not
by asserting stability that the data do not support. R8 remains an
administrative placeholder: acceptable for anonymous review, but author,
affiliation, corresponding-author, CRediT, and funding fields must be completed
before a non-anonymous final submission. No additional broad methodological
experiment is required for the present scoped claims.
