# MSA-DTI / JNCA — 最后一次定向微修冻结单（KEEP / MODIFY）

**状态：经作者本轮讨论后的最终限定修改范围；不属于新的模拟审稿任务。**

**唯一修改基准**：`MSA_DTI_Final_Publication_20261013_SuppFix.zip`  
ZIP SHA-256：`551411789fab9334a03c29d9931294aa9a10a0597038a1e6e201f9e774a7356f`  
现有 `main.tex` SHA-256：`55a5d395f1e640bfa970d7af12e3400e28b7884a8ac6fc339048256291bb8613`  
现有 `supplementary.tex` SHA-256：`c5492e3bf77085c1802424b916d663cbd1953348ba8a1ade999c6a6d7c4958f6`  
公开论文基准：[manuscript-suppfix-20261013](https://github.com/w924871681/paper-code-DT-Twin/releases/tag/manuscript-suppfix-20261013)。绝不使用仓库 `main` 或旧 Release 中的历史论文替代基准。

## A. 总体裁决

| 编号 | 决定 | 允许修改的位置 | 理由和边界 |
|---|---|---|---|
| S1 Few-shot / 验证标签 | **KEEP** | 无 | Abstract 已写 small support + separate labeled validation，§3.1 和 §5.1.1 已区分 K/V 并给出合成验证窗口数。再扩写会重复。不得暗示总目标监督仅 K=10/20。 |
| S2 Bitbrains 协议 | **MODIFY（证据前置）** | 仅 `supplementary.tex` 的 §S7.5 | 从已冻结原始代码/配置/manifest/逐案例 metadata 核查后，增加一个简短协议表或等效紧凑段落；不得猜测数值。 |
| S3 严格胜率 | **MODIFY-LITE** | 仅 Supplementary Table S3 一列名称 | 将 `MSE win rate (\%)` 改为 `Strict MSE wins (\%)`；所有表格数值/脚注不变。 |
| S4 双 A57 校准对照 | **MODIFY** | 仅 `main.tex` §4.4 的原控制定义句 | 补足“两个 A57 都适应、使用同一 τ 在验证集选择、选中模型 check loss 为比较分母、源训练并非仅随机种子差异”；不改公式。 |
| S5 LogME / JMLR 文献 | **KEEP** | 无 | 当前短句概括没有声称模型库排序或部署约束首次由本稿提出，已把完整联合流程作为区别；不需要加长 Related Work。原论文确有资源约束和 B-Tuning，后续如收到真人审稿明确意见再定点回应。 |
| S6 NAS 名称 | **MODIFY-LITE** | 仅 `main.tex` Figure 5 图注一句 | 不改图内标签或图文件；让独立阅读 Fig.5 的读者知道 NAS 名称是任务化/based 控制而非原算法精确复现。Table 2/3 已有近邻方法说明，默认 KEEP。 |
| S7 cross-architecture gain | **MODIFY** | 仅 `main.tex` §5.5 两处 | 改成“完整异构候选库流程收益”，避免误认纯架构因果效应。 |
| S8 离线总成本 | **KEEP** | 无 | 已明确在线/目标侧计时边界和额外工作，不主张完整训练和准备成本占优。 |
| S9 作者/机构/CRediT | **DEFER** | 当前禁止修改 | 留到作者确定后，在投稿材料阶段一次性完成。 |

**硬冻结**：Abstract、Introduction 其余内容、Conclusion、13 个编号主公式、Algorithm 1、原合成统计与六阈值校准、Alibaba 纠正结果、Bitbrains 数值、R5 数值与来源限定、全部 16 个图文件、两张外置表、参考文献条目、Data Availability、原 `v1.2.7` Tag 和 Release 资产都不得修改；不重训、不调参、不新实验、不删除负面结果、不动 PR #9 的合并状态。

## B. 精确英文修改及中文释义

### S4 — 正文 §4.4，仅替换原配对初始化控制定义句

**Original（原句）：**

> The paired-initialization control uses a second source-trained initialization of the reference architecture and provides a same-architecture control for source-initialization effects.

**Revised English（完整替换）：**

> The paired-initialization control adapts both source-trained A57 candidates on the same support set and applies the same relative-margin rule at each $\tau$ to select one using validation loss. The selected model's check-set loss is the paired-control denominator; because the two source-training recipes differ, this is a same-architecture selection control rather than a random-seed-only comparison.

**中文翻译：** 配对初始化对照在同一支持集上适配两个经过源训练的 A57 候选，并对每一个 τ 使用相同的相对门槛规则，依据验证损失选出其中一个。所选模型的检查集损失构成配对对照的分母；由于两个候选的源训练方案不同，该对照属于同架构选择控制，而不是只改变随机种子的比较。

**原因：** 与现有 Supplementary §S2.2 完整定义对齐，避免首次阅读将 G_pair 错解为第二个 A57 单模型的损失。不得改 Eq.(12) 或补充 S2.2 既有文字。

### S7 — 正文 §5.5，两处精确替换

**Original 1：**

> The reference-only and two-reference-initialization variants do not reproduce the cross-architecture gain.

**Revised English 1：**

> The reference-only and two-reference-initialization variants do not reproduce the gain of the complete heterogeneous-bank pipeline.

**中文翻译 1：** 仅保留参考模型和双参考初始化的变体未能重现完整异构候选库流程的收益。

**Original 2：**

> The cross-architecture gain remains sensitive to source training.

**Revised English 2：**

> The heterogeneous-bank pipeline gain remains sensitive to source training.

**中文翻译 2：** 异构候选库完整流程的收益仍对源训练方式敏感。

**原因：** 所有收益数值保持；避免将含来源训练差异的完整流程收益错误归因于架构本身。

### S3 — Supplementary Table S3，仅改列标题

**Original：** `MSE win rate (\%)`  
**Revised：** `Strict MSE wins (\%)`  
**中文：** 严格数值意义的 MSE 获胜比例。  
**原因：** 保留原 71.25% 和“其中 13 次源于最多 7.7×10^-9 数值差”的现有脚注，不误认为全部胜利代表有益模型替换。若表头布局受影响，可更短地写作 `Strict wins (\%)`，表注已明确依据 test MSE。

### S6 — 正文 Figure 5，仅修改图注末尾

**Original：**

> Predictive performance on the held-out target cases. Panels (a)--(d) show MAE, MSE, Worst-10\% error, and CVaR90, respectively. Lower values are better.

**Revised English：**

> Predictive performance on the held-out target cases. Panels (a)--(d) show MAE, MSE, Worst-10\% error, and CVaR90, respectively. Lower values are better. NAS-related labels denote task-matched control implementations, not exact reproductions of published algorithms.

**中文翻译：** 留出目标案例的预测性能。(a)–(d) 分别展示 MAE、MSE、Worst-10% 误差与 CVaR90；数值越低越好。NAS 相关标签指针对当前任务匹配实现的对照方法，并非发表算法的完整精确复现。

**原因：** 满足独立看图的准确命名要求，不重画/更换 Figure 5，不更改实验比较。

### S2 — Supplementary §S7.5，仅补一张紧凑 Bitbrains 协议表／等价短段

**原文已有事实（必须保留）：** fastStorage 含 1,250 VMs；有预注册质量筛选；按稳定身份选择 100 台；source/development/calibration/held-out 为 20/20/20/40 VMs；按源统计量归一化；H={1,4} 为未来原生记录，K={10,20} 为支持窗口；5 条件校准及相应结果均已明确。

**唯一可新增的科学信息**（仅用冻结资产确认后插入，不重复现有事实）：

1. 预先规定的筛选谓词/阈值、筛选后实际候选 VM 数；应标注该数是否在身份选择前计算。
2. 来源与目标各阶段的时间划分规则及观察跨度；如各 VM 的真实记录时间不同，应给范围或划分规则，不能捏造统一日期。
3. 25 输入通道的实际字段映射与原有因果滞后/掩码规则（只给必要的简要归类，详情引用公开代码）。
4. H/K 情况下 target-side support、validation、calibration check、held-out test 的实际窗口数；若每 VM 不一致，给校验过的范围，不把窗口数量称为独立标注数。
5. 1 条准确的可访问代码/manifest 相对路径或不可变 GitHub 资产入口，避免在论文中写个人电脑绝对路径。

**执行前提与STOP**：先在现有 R5/Bitbrains 公开扩展 Release、原本地冻结运行的配置、`bitbrains_data.py`、`bitbrains_target.py`、role manifests、per-case CSV/JSON 中获取具体数值。允许只读解析和现有汇总核算，禁止重训、重划分、重造历史数组或以新筛选规则填空。凡没有确切证据的字段不得发明；如完整过滤后数量/逐案例验证数不可恢复，先标明 `NOT_RECOVERABLE_FROM_FROZEN_RECORD`，仅写现有可证实内容并报告缺口，不能将未验证范围写进 Supplementary。

**形式与版面**：优先用 1 张小型协议表（不多于约 6–8 行）或一个紧凑段落，放在 §S7.5 第一段后、完整五条件校准表之前。不重复现有 20/20/20/40、结果、CI 或源训练成本段落；新增内容以读者理解标签/时间预算为目的。

## C. 唯一推荐执行流程（交给 Codex 实施）

1. 先确认本表三个基准哈希、工作目录/PR #9 状态。按上述原句进行严格匹配，原句不在文件中就 STOP。
2. **先只读取冻结 Bitbrains 数据协议资产，生成 `BITBRAINS_PROTOCOL_EVIDENCE.md`**：每个新增数字必须注明来源相对路径、字段键、原记录值和单位。找不到不填数；发现与论文现有事实冲突要 STOP，请作者裁决。
3. 完成 S2、S3、S4、S6、S7 指定源码修改；S1、S5、S8 全部 KEEP，S9 延后。所有其他科学文件内容保持不变。
4. 重新编译正文和 Supplementary，检查图注、Table S3 列宽、S7.5 表格溢出/分页；必要时只调本次新增表本身的字号/列宽，不改旧实验图或旧表。
5. 生成完整 LaTeX ZIP、两份 PDF、SHA256SUMS、`SOURCE_MINIMAL_DIFF.patch`、`FINAL_ONEPASS_MICROFIX_REPORT.md`，按旧版逐文件复核只有 `main.tex`、`supplementary.tex`、两份相应重编译 PDF（和必要新文档）改变；所有图/原表/参考文献/公式数值 KEEP。
6. 只使用独立新发布标记/Tag 归档此稿，既有 `v1.2.7`、light/full evidence、历史 manuscript Releases 必须原封不动。PR #9 仍 Draft，不合并、不清理历史。
7. 交付路径/真实 GitHub 地址/文件大小/哈希/版本保护快照。**完成一次人工核对和论文内容冻结，不再运行新的模拟审稿或启动新实验。** 除投稿身份信息、期刊强制格式或未来出现的可证实 P0 错误外，不再进行科学内容循环修改。

## D. 交付时的三项通过标准

- **真实性**：S2 每个具体筛选、时间和窗口数都有冻结资产对应，S4 校准选择器定义与 Supplementary 一致，S7 不含架构单因素因果暗示。
- **最小性**：`git diff` 只命中 S2、S3、S4、S6、S7 指定位置；正文 Abstract、Introduction、Conclusion 及全部冻结统计、公式、图片不变。若仅新增 S2 表，新的 Supplementary 页数增加是正常现象，不得为维持 15 页挤压其他内容。
- **投稿收口**：主文和补充 PDF 可编译，访问入口正确，新版 GitHub 哈希匹配，全部历史 Tag/Release 原样保留。S9 作者、单位、通讯和 CRediT 作为正式投稿信息另行完成。
