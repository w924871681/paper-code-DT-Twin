# Final Review Response Draft (MSA-DTI / JNCA)

本文件用于 response-to-reviewers，不自动并入论文正文。每项按
`accepted and revised`、`clarified`、`not adopted with justification` 分类。

---

## Accepted and revised

### R1（H-Meta-NAS 数值不一致）

> Thank you for identifying this inconsistency. The manuscript and the
> previously hard-coded Fig. 5 value retained an outdated H-Meta-NAS summary,
> whereas the audited current result is MSE = 0.013574. We synchronized the
> manuscript, Fig. 5, plotting source, and release-facing result tables to the
> audited H-Meta-NAS record. This is a reporting/provenance correction and does
> not require rerunning MSA-DTI or changing any headline result.

已修改：正文 H-Meta-NAS MSE `0.013747` -> `0.013574`；Fig. 5 四项 H-Meta-NAS 数值同步为
audited canonical 值；Fig. 5 生成脚本更新并注明 source of truth。

### R1（metric provenance 的 terminology 部分）

> Thank you for raising the metric-provenance issue. We verified that the
> historical `WMSE`/`weighted_mse` field in frozen repository artifacts uses
> uniform horizon weights. Under this setting, it is numerically identical to
> the MSE reported in the manuscript, so there are not two different headline
> metrics. To prevent confusion, we standardized the current public-facing
> repository outputs and documentation to `MSE`/`mse`, while preserving
> immutable historical provenance records and documenting `WMSE` as a legacy
> alias. No experimental value or headline result changes.

### R6（workload forecasting 的概念澄清）

> We clarified the role of workload forecasting in Section 3.1. Workload
> forecasting is used as a representative evaluation task to assess the quality
> of the instantiated center-specific DT model. It is not an additional
> component of MSA-DTI. MSA-DTI itself instantiates the architecture--parameter
> pair, and DT_c remains explicitly defined as a model instance rather than the
> complete DT system.

已修改：正文 §3.1 在 DT_c 定义后追加两句澄清，不新增 forecasting module、框图或 keyword。

### runtime scope wording

> We have revised the runtime statement to report only the measured scope: one
> instantiation case on one GPU. Concurrent-case scaling and platform-level
> scheduling are outside the present evaluation. We therefore avoid inferring an
> unmeasured break-even reconfiguration frequency.

已修改：正文删除 `covers low-frequency instantiation`，替换为仅报告实测范围。

### candidate screening retention rule 表述统一

> We unified the screening retention-rule wording across the main text,
> Supplementary S2.1, S7.2, and the configuration table with the frozen rule
> actually implemented: a configuration is retained when it records at least two
> check-oracle wins over A57, or at least two validation-selected positive check
> wins over A57. No screening threshold, retained list, frozen bank, or headline
> result changes.

---

## Clarified（不改变核心定位）

### R2（deployment limits 术语）

> We agree that operation count and parameter count are model-level complexity
> indicators rather than direct hardware-latency or memory guarantees. The
> manuscript already states this distinction explicitly. We retain the term
> "deployment limits" because these indicators are subjected to hard feasibility
> bounds in Eq. (2): the indicators specify the measured model-level quantities,
> while the limits define the admissible set. We do not interpret these limits as
> device-specific latency, memory, or energy guarantees.

### R3（algorithm / novelty / relative margin 定位）

> We agree that the relative margin is a conservative replacement rule rather
> than the source of the predictive gain, and the revised manuscript states this
> explicitly in the component analysis. We use the term "algorithm" to denote the
> complete target-side instantiation procedure in Algorithm 1, not to claim a new
> optimizer or learning primitive. The contribution lies in jointly
> operationalizing hard feasibility filtering, common-budget adaptation of
> reusable architecture--initialization pairs, finite-set target selection, and
> reference-based replacement under limited target data and deployment limits.

---

## Not adopted with justification

### R4（wild-cluster bootstrap / cluster-jackknife）

> We appreciate the concern about inference with 20 center clusters. The
> manuscript deliberately does not use the current center-cluster bootstrap
> interval to claim that the population harmful-selection rate is below 5%; it
> explicitly states that the 95% interval [0.00%, 7.50%] does not establish such
> a guarantee. The 5% value is an ex-ante calibration tolerance rather than a
> population-level safety claim. Because the statistical conclusion is already
> conservative and does not depend on the upper bound being below 5%, we do not
> introduce an additional inferential procedure as a new acceptance criterion.

### R5（MeDeT / H-Meta-NAS exhaustive best-practice tuning）

> The external baselines are explicitly described as task-matched /
> method-based implementations rather than exact reproductions of the original
> systems. Their protocol differences are reported in the Supplementary Material,
> and the main paper additionally provides an optimizer-matched diagnostic under
> common target cases, deployment limits, SGD/MSE, and 50 target updates. We
> corrected the H-Meta-NAS numerical reporting inconsistency identified by the
> reviewer. We do not add an unbounded method-specific hyperparameter search,
> because that would introduce different tuning budgets across methods and move
> beyond the controlled comparison protocol.

### Dedicated Limitations section

> We agree that these limitations should be explicit. They are reported at the
> corresponding evidence locations and summarized in the Conclusion. We retain
> this evidence-linked presentation to avoid duplicating the same limitations in
> a separate section.

### 增加 model-zoo / deployment-aware selection / drift references

不根据盲审中的 `[UNVERIFIED]` 线索机械加引用。仅在人工确认（文献真实存在、与本文直接相关、
当前 Related Work 确实遗漏、会影响 novelty positioning）后加入。不自动生成或臆造参考文献。

### break-even deployment frequency / concurrency

> We have revised the runtime statement to report only the measured scope: one
> instantiation case on one GPU. Concurrent-case scaling and platform-level
> scheduling are outside the present evaluation. We therefore avoid inferring an
> unmeasured break-even reconfiguration frequency.

### energy estimate

> The manuscript treats operation count and parameter count as model-level
> complexity indicators and explicitly does not interpret them as direct
> device-specific energy guarantees. Energy profiling would require a separate
> hardware-level measurement protocol and is outside the scope of the current
> model-instantiation study.

### `workload prediction` keyword

不加。workload forecasting 是 representative evaluation task，而不是本文算法主题；加入会误导为
forecasting-algorithm 论文。

### CVaR90 -> TVaR

不改。CVaR90 是通用风险度量术语，除非 JNCA style guide 明确要求，否则保持。

### 额外报告 aggregate MSE reduction

不新增第二 headline reduction 口径。当前使用 mean paired MSE reduction + paired cluster CI，
更适合 case-paired comparison；再并列 ratio-of-means reduction 会增加解释负担与口径混乱。

### 第二真实数据集

不补。Alibaba 已定位为 external workload-domain transfer audit，并主动报告 original
reliability criterion 未复现；第二个真实 trace 属于 external-validity extension，不是修复当前
headline validity 的必要实验。

---

## Submission metadata TODO（不自动填写）

- Author list
- CRediT authorship contribution statement
- Funding
- DOI
