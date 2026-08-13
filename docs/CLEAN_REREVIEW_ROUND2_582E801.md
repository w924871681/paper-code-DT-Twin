# Clean second-round re-review of commit 582e801

## Review boundary

- Frozen input commit: `582e801afe982fc7e4edb8e52a3f4ca4c88a3b01`.
- Sole review artifacts: `paper/manuscript.pdf` and
  `paper/supplementary.pdf` as stored in that commit.
- The previous simulated decision and R1--R8 matrix were not consulted until
  the five independent reports and the initial editorial decision had been
  completed.
- Author identity, affiliation, CRediT, and funding placeholders were outside
  the scientific-review scope and remain unchanged at the author's request.

The frozen PDFs passed the local page-integrity preflight: 14 main-manuscript
pages and 9 supplementary pages, with no page-count mismatch or parser warning.

## Editorial screening

The paper is suitable for external review at the *Journal of Network and
Computer Applications*. Its focus is the predictive-model component of a
networked digital-twin platform, with workload prediction, heterogeneous
computing centers, model reuse, and constrained deployment. The principal
scope risk is that the method could be read as generic finite-bank model
selection if the connection to networked resource management is obscured.
The title, abstract, introduction, and external workload-trace evaluation make
that connection sufficiently explicit for review.

Initial editorial action: **send to review**.

## Independent reviewer reports

### R1: journal fit and originality

**Recommendation: Minor Revision. Confidence: 4/5.**

The contribution is a coherent systems-method combination: a protected
source-trained reference, a finite bank of separately source-trained models,
hard deployment filtering, common-budget adaptation, and conservative
validation-based replacement. It is distinguishable from frozen model-bank
scoring, single-model PT+FT, and target-side NAS. The contribution is more an
integration and protocol contribution than a new learning primitive, but the
paper states this boundary directly.

Strengths include the JNCA-relevant application setting, a clear optimization
object, and restrained claims about the DT predictive-model component. The
abstract, however, omitted the negative independent rescreening result and
contained 281 words, exceeding JNCA's 250-word limit.

Finding R1-W1: shorten the abstract to no more than 250 words and retain the
main result while disclosing screening instability and external-calibration
limits. Severity: Minor. Evidence: main PDF, page 1; JNCA Guide for Authors,
Abstract section.

### R2: methodology and statistics

**Recommendation: Minor Revision. Confidence: 5/5.**

The source, screening, calibration, diagnostic, robustness, and held-out pools
are separated by center identity. The test set is opened only after model
selection, and center-cluster bootstrap intervals preserve the four-case
within-center dependence. The paper reports the negative screening-stability
result, the harmful-selection interval that crosses 5%, and the Alibaba
calibration failure without converting them into positive guarantees.

No reported statistic falls within the bounded p-value, GRIM, GRIMMER, or
degrees-of-freedom recomputation procedures, so no arithmetic receipt is
applicable.

Finding R2-W1: the concise screening-rule descriptions in main Section 5.1.2
and Supplementary S2.1 are not equivalent in precision to S7.2. The former can
be read as counting any validation or check win, whereas the implemented rule
counts check-loss wins or validation-selected candidates with positive check
gain. Severity: Minor because the code and frozen result record the exact rule
and no numerical result changes. Evidence: main PDF, page 8; supplementary
PDF, pages 1 and 8.

### R3: digital-twin and workload-prediction domain

**Recommendation: Minor Revision. Confidence: 4/5.**

The paper correctly limits "instantiation" to a DT predictive-model component
and does not claim to implement sensing, synchronization, simulation, or
actuation. Workload prediction is connected to proactive resource management,
and the Alibaba trace provides a relevant external workload domain. The
synthetic benchmark remains the source of the headline result, but the paper
does not conceal this limitation.

The main domain risk is not a missing experiment but claim interpretation:
independent rescreening does not recover a stable architecture list. The
conclusion already narrows the claim; the abstract should do the same.

### R4: systems deployment and reproducibility

**Recommendation: Accept with minor clarification. Confidence: 4/5.**

Operation and parameter counts are consistently treated as deterministic
model-level indicators. The paper explicitly states that they are not latency
or memory guarantees. The main-bank operation limit is inactive, and the
expanded-bank stress audit is labeled as such. CPU/GPU latency, serialized
state size, peak GPU allocation, target-side time, and the single-host boundary
are reported. These disclosures are adequate for the scoped deployment claim;
a second hardware platform would strengthen generality but is not required.

Finding R4-W1: distinguish the protected pooled-source A57 reference from the
separately trained A57 paired-initialization candidate. Without that
distinction, Table S5's zero-size fallback row and the A57 entries in nonempty
retained lists appear contradictory. Severity: Minor. Evidence: supplementary
PDF, pages 1, 5, and 8.

### R5: adversarial, language, and integrity review

**Recommendation: Minor Revision. Confidence: 4/5.**

No singleton defect invalidates the central frozen-bank result. The strongest
counterargument is that unstable candidate discovery weakens any claim of a
generally recoverable architecture set. The manuscript already concedes this
in the main results and conclusion, so it does not rise to Major or Critical.
No fabricated citation, hidden test-based selection, unsupported hardware
guarantee, or main/supplement numerical contradiction was found.

CRITICAL findings: none.

MAJOR findings: none.

The only actionable integrity issue is the two A57 candidate identities and the
screening-rule paraphrase identified independently by R2 and R4.

## Initial editorial synthesis

Decision before revision: **Minor Revision**.

Risk summary:

| Decision class | Risk |
| --- | --- |
| Reject | Low; no fatal scope, integrity, or methodological defect found. |
| Major Revision | Low; no new experiment or re-analysis is required. |
| Minor Revision | High before the local fixes because of abstract compliance and method-description precision. |
| Accept | Plausible after the two local corrections and final verification. |

Required actions:

1. Reduce the abstract from 281 to at most 250 words while preserving the
   principal result and disclosing the screening-stability and transfer limits.
2. State the implemented screening rule exactly and consistently.
3. Define the protected and separately trained A57 candidates explicitly and
   use those meanings in Table S5's
   retained-set interpretation.

No additional experiment is requested.

## Revision applied

- Rewrote the abstract to 234 words. It now retains the main 14.60% paired MSE
  reduction and its cluster interval, and adds the Alibaba calibration and
  independent-rescreening boundaries.
- Replaced the broad screening-rule paraphrase in the main manuscript and S2.1
  with the exact two-branch rule verified against the authorized project code
  and frozen result JSON.
- Defined the protected pooled-source A57 reference and the separately
  source-trained A57 paired-initialization candidate. Clarified that Table S5
  sizes and Jaccards count discovered configurations before adding the
  protected reference.
- No result, figure, table value, citation, experiment output, author field,
  CRediT field, or funding field was changed.

## Terminal re-review

The revised manuscript and supplementary material were recompiled from LaTeX.
The main manuscript remains 14 pages and the supplement remains 9 pages. Both
PDFs passed the page-integrity preflight. All 23 rendered pages were inspected;
no clipped text, overlap, broken glyph, missing figure, unreadable table, or
page-transition defect was found. The repository verifier returned
`PASS_PUBLIC_REPOSITORY_VERIFICATION`, and all 13 tests passed.

Five-seat closure:

| Seat | Closure verdict | Basis |
| --- | --- | --- |
| R1: journal fit and originality | Accept | Abstract is 234 words and now carries the principal boundary conditions. |
| R2: methodology and statistics | Accept | The exact frozen screening rule is stated consistently; no result or analysis changed. |
| R3: DT and workload-prediction domain | Accept | The predictive-component scope and limits on architecture discovery and domain calibration remain explicit. |
| R4: systems deployment | Accept | The two A57 candidate identities and retained-set counting convention are now unambiguous. |
| R5: adversarial and integrity | Accept | No Critical or Major issue remains; compilation, visual, and repository checks pass. |

### Final editorial decision

**Accept for scientific content in the anonymous-review version.**

Estimated residual decision risk after revision:

| Outcome | Risk |
| --- | --- |
| Reject | Low |
| Major Revision | Low |
| Minor Revision | Low to moderate, mainly journal/editor preference rather than an identified unresolved defect |
| Accept | Highest among the four simulated outcomes |

This simulated decision is not a prediction or substitute for JNCA's actual
editorial process. Author names, affiliations, corresponding-author details,
CRediT roles, and funding remain an administrative submission hold for a
non-anonymous package; they do not reopen the scientific decision and were
intentionally left unchanged.
