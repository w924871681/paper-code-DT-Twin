# Method mapping

The public method is a complexity-constrained few-shot digital twin model
instantiation procedure:

1. Build a compact source-initialization bank. Each candidate is an
   architecture paired with its matched source-trained initialization.
2. Apply the target model complexity limits. A candidate is feasible only when
   both its estimated operation count and parameter count are within the target
   limits.
3. Adapt every feasible candidate with the same support set, loss, optimizer,
   and update budget.
4. Compare the best alternative with a fixed reference candidate. Accept the
   alternative only if it passes the preset reference-based improvement test.
5. Return the selected architecture and target-adapted parameters as the
   target-specific digital twin model.

Estimated operation count is an architecture-level proxy for one forward
pass's inference computation. Parameter count characterizes model size. These
measures are not direct observations of device latency, memory use, or energy
consumption. Workload prediction is only the evaluation task.

The frozen numerical settings, including the common update budget and preset
margin, are documented in `README.md` under **Frozen protocol**.

Some immutable audit files, frozen source schemas, and internal implementation
identifiers retain historical experiment names for reproducibility. They are
not the public terminology used in the paper. Legacy module paths remain
importable so archived runs can be checked without changing provenance.

