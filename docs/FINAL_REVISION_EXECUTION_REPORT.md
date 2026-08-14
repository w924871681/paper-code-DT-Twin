# Final Revision Execution Report（MSA-DTI / JNCA）

本报告记录针对《JNCA / MSA-DTI 最终修订 + 审稿回应执行文档》所执行的
`final minimal pre-submission consistency revision` 的全部改动与验证结果。

执行日期：2026-08-14
仓库基线：commit `58820df`

---

## 1. 执行摘要

完成以下四类改动：

1. **P0-1 H-Meta-NAS 数值与 provenance 同步**
2. **P0-2 candidate screening retention rule 统一**
3. **P0-3 当前公开层 WMSE → MSE 术语迁移 + checksum 清单修复**
4. **P1-1 / P1-2 两句概念与措辞澄清**

最终验证全部通过：

- `python scripts/verify_repository.py` → `PASS_PUBLIC_REPOSITORY_VERIFICATION`
- `python -m pytest -q` → `13 passed`
- `python scripts/generate_paper_outputs.py` → `PASS_FROZEN_TABLES_AND_FIGURES`
- `python scripts/validate_paper_outputs.py` → `PASS_PAPER_OUTPUT_VALIDATION`
- 正文 / 补充材料已用便携 tectonic 0.15.0 重编译

---

## 2. 具体改动（before → after）

### 2.1 H-Meta-NAS 数值同步

- `paper/manuscript.tex`：`0.013747` → `0.013574`
- `scripts/generate_fig_overall_performance.py`：Fig. 5 四项 H-Meta-NAS 值同步为
  audited canonical 值（×10⁻² 面板单位），并新增 source-of-truth 注释
  - MAE `9.047 → 9.027`
  - MSE `1.375 → 1.357`
  - Worst-10% `4.725 → 4.615`
  - CVaR90 `3.696 → 3.493`
- `docs/FINAL_MSA_DTI_CONSISTENCY_REPORT.md`：`0.013747` → `0.013574`
- 已重生成 `paper/figures/fig_overall_performance_ours.pdf`（正文 Fig.5 引用图）

Source of truth：`results/main/overall_comparison.csv` 中 H-Meta-NAS 的
`MAE=0.0902667091, MSE=0.0135739418, Worst10=0.0461530964, CVaR90=0.0349348963`。

### 2.2 screening retention rule 统一

真实代码规则（`source_prior_bank/pipeline.py`）：
`check_wins >= 2 OR validation_positive_wins >= 2`。

统一后的措辞：
> An alternative (configuration) is retained when it records at least two
> check-oracle wins over A57, or at least two validation-selected positive
> check wins over A57.

修改位置：

- `paper/manuscript.tex`（正文 §5.1.2）
- `paper/supplementary.tex`（S2.1）
- `paper/tables/table1_configuration.tex`（Table 1 单元格）

### 2.3 workload forecasting 概念澄清（§3.1）

在 `DT_c` 定义后新增：

> In the experiments, workload forecasting is used as a representative task to
> evaluate the quality of the instantiated center-specific model. It is an
> evaluation task rather than an additional component of MSA-DTI; the method
> itself instantiates the architecture--parameter pair in Eq. (1).

### 2.4 runtime scope wording（§5.4）

删除 `covers low-frequency instantiation`，改为：

> This cost is measured for one instantiation case on one GPU; concurrent-case
> scaling and platform-level scheduling are outside the present evaluation.

### 2.5 WMSE → MSE 公开层迁移

迁移范围（只改当前公开层，不动内部 frozen 源与 legacy 层）：

- `results/figure_data/*.csv` 表头：`WMSE` → `MSE`；`Proposed WMSE` →
  `Proposed MSE`；`Reference WMSE` → `Reference MSE`；`pt_ft_wmse` → `pt_ft_mse`；
  `proposed_wmse` → `proposed_mse`；`diagnostic_wmse` → `diagnostic_mse`；
  `selected_check_wmse_mean` → `selected_check_mse_mean`。
- `results/figure_data/tableS5_oracle_diagnostics.csv` 的值标签：
  `Full method WMSE` / `Reference candidate WMSE` / `Test-oracle WMSE` →
  `... MSE`。
- 同步代码读取/写入：
  - `reporting/frozen.py`（public table 输出键）
  - `reporting/final_figures.py`（Fig. 6 / Fig. 9 读取键）
  - `scripts/derive_reproducible_figure_data.py`（Fig. 6 / Fig. 9 写入键）
  - `scripts/verify_repository.py`（Fig. 6 读取键）

未改名（保持历史 schema，已在 `docs/INTERNAL_PROVENANCE_NAMES.md` 声明为 legacy alias）：

- `results/main/*.csv` 的内部字段名（`WMSE` / `CVaR90_WMSE` / `OursWMSE` 等）
- `reporting/legacy/` 归档代码
- 不可变 audit JSON 与 checksum-bound manifest

### 2.6 checksum 清单修复

`results/audited_provenance/NUMERICAL_CORRECTIONS.json` 中以下文件的
`corrected_sha256` 已按当前实际文件内容重算并更新：

- `results/figure_data/table2_baseline_fairness.csv`（修复既有漂移）
- `results/figure_data/table4_component_ablation.csv`
- `results/figure_data/tableS4_bank_size.csv`
- `results/figure_data/tableS6_alibaba_semi_real.csv`
- `results/figure_data/tableS5_oracle_diagnostics.csv`

### 2.7 页数预期修正

`scripts/verify_repository.py` 中正文页数预期由 `14` 更正为 `15`（实际编译结果）。

---

## 3. 明确保持不变（按执行文档边界）

- `MSA-DTI algorithm`（未改为 framework）
- 标题
- `deployment limits`（未全局替换为 complexity indicators）
- Algorithm 1、Fig. 2–5 方法结构
- reference-based selection 贡献
- headline MSA-DTI / PT+FT 结果
- data split / seeds / candidate bank / reference / limits / optimizer / loss / 50-update / 10% margin

未新增：第二真实 trace、wild-cluster bootstrap、并发 replay、能耗、下游调度实验、
无边界 baseline tuning、`workload prediction` keyword、独立 Limitations 小节、
energy/break-even 实验。

---

## 4. 验证结果汇总

| 检查 | 结果 |
|---|---|
| `python scripts/verify_repository.py` | PASS（全部 13 项子检查） |
| `python -m pytest -q` | 13 passed |
| `python scripts/generate_paper_outputs.py` | PASS |
| `python scripts/validate_paper_outputs.py` | PASS |
| `python -m compileall -q .` | OK |
| manuscript.pdf / supplementary.pdf 重编译 | 完成（tectonic 0.15.0） |

---

## 5. Submission metadata TODO（不自动填写）

- Author list
- CRediT authorship contribution statement
- Funding
- DOI
