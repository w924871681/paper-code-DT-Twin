# MSA-DTI 投稿前增强实验补丁：安装与运行

## 1. 安装方式

本补丁采用“新增文件、并行输出”的方式，不覆盖已经冻结的 C3-1/C3-2/C3-3 主实验代码与结果。

1. 先备份仓库或创建新分支：

```powershell
git checkout -b pre-submission-enhancements
```

2. 将补丁 ZIP 解压到仓库根目录，使目录合并后出现：

```text
configs/methods/pre_submission_enhancements_cfg.py
experiments/pre_submission/
scripts/run_hosting_profile.py
scripts/prepare_alibaba_domain_trace.py
scripts/build_alibaba_domain_bank.py
scripts/run_alibaba_domain_calibration.py
scripts/generate_pre_submission_reports.py
scripts/RUN_PRE_SUBMISSION_ENHANCEMENTS.ps1
```

3. 不要删除或覆盖原有 `outputs/`。新增实验默认写入：

```text
outputs/pre_submission_enhancements_d2904_t2904/
```

## 2. 先运行无需训练的审计和新 Fig.10

```powershell
python .\scripts\generate_pre_submission_reports.py `
  --project-root . `
  --output-root .\outputs\pre_submission_enhancements_d2904_t2904\report
```

主要输出：

- `constraint_activity_summary.csv`
- `constraint_activity_details.csv`
- `safety_across_pools_expanded.csv`
- `fig10_accuracy_instantiation_pareto.pdf`
- `fig10_accuracy_instantiation_pareto.png`
- `fig10_accuracy_instantiation_pareto_data.csv`
- 若原始冻结输出齐全，还会生成中心级架构保留审计和代表性 DT 实例化案例。

该步骤不训练模型，不改变主实验。

## 3. 真实承载环境实验

### 3.1 运行前检查

必须存在主实验冻结权重：

```text
outputs/source_prior_bank_d2904_t2904/strong_bank/c31_strong_bank_manifest.json
outputs/formal_c1_seed2904/shared_artifacts/ours_weight_bank_source_pooled_c1_v1_src20.pt
```

### 3.2 CPU 快速冒烟测试

```powershell
python .\scripts\run_hosting_profile.py `
  --project-root . `
  --devices cpu `
  --safe-mode default `
  --host-label laptop_cpu `
  --smoke
```

### 3.3 CPU + RTX 3060 正式测量

```powershell
python .\scripts\run_hosting_profile.py `
  --project-root . `
  --devices cpu,cuda `
  --safe-mode gru-native `
  --host-label laptop_cpu_rtx3060
```

冻结协议为：

- batch size = 1；
- 每个候选、每个预测跨度先 warm-up 100 次；
- 正式推理 1000 次；
- 重复 5 轮；
- GPU 每次计时前后执行同步；
- 不进行目标适配和模型选择，仅测量冻结候选的一次推理开销。

输出：

```text
outputs/pre_submission_enhancements_d2904_t2904/hosting/hosting_profile.json
```

完成后重新运行报告脚本，将生成：

- `hosting_profile_summary.csv`
- `hosting_profile_correlations.csv`

### 3.4 在 Jetson 等边缘设备上补测

把仓库和冻结权重复制到设备，在设备上运行：

```powershell
python .\scripts\run_hosting_profile.py `
  --project-root . `
  --devices cpu `
  --safe-mode default `
  --host-label jetson_orin `
  --out .\outputs\pre_submission_enhancements_d2904_t2904\hosting\jetson_orin.json
```

把不同设备的 JSON 复制到同一机器后合并：

```powershell
python .\scripts\merge_hosting_profiles.py `
  --inputs `
    .\outputs\pre_submission_enhancements_d2904_t2904\hosting\laptop.json `
    .\outputs\pre_submission_enhancements_d2904_t2904\hosting\jetson_orin.json `
  --out .\outputs\pre_submission_enhancements_d2904_t2904\hosting\hosting_profile.json
```

## 4. 扩大 Alibaba 并分离校准与测试

### 4.1 数据划分

补丁按机器标识符的固定 SHA-256 顺序划分：

- 20 台 source machines；
- 20 台 calibration machines；
- 40 台 held-out target machines。

归一化统计量只由 source machines 计算。复杂度档位是受控半合成标签。

### 4.2 先做冒烟测试

冒烟测试只使用少量机器、1 个来源训练 epoch 和 1 次目标更新，用于验证代码链路，不能写入论文。

```powershell
.\scripts\RUN_PRE_SUBMISSION_ENHANCEMENTS.ps1 `
  -Mode alibaba-smoke `
  -AlibabaArchive ".\data\alibaba2018\raw\machine_usage.tar.gz" `
  -Device cpu `
  -SafeMode default
```

冒烟结果和正式结果不能共用同一输出目录。正式运行前删除冒烟输出：

```powershell
Remove-Item -Recurse -Force `
  .\outputs\pre_submission_enhancements_d2904_t2904\alibaba_domain
```

### 4.3 正式运行

```powershell
.\scripts\RUN_PRE_SUBMISSION_ENHANCEMENTS.ps1 `
  -Mode alibaba-formal `
  -AlibabaArchive ".\data\alibaba2018\raw\machine_usage.tar.gz" `
  -Device cuda `
  -SafeMode gru-native
```

也可以分步运行：

```powershell
python .\scripts\prepare_alibaba_domain_trace.py `
  --input ".\data\alibaba2018\raw\machine_usage.tar.gz"

python .\scripts\build_alibaba_domain_bank.py `
  --project-root . `
  --device cuda `
  --safe-mode gru-native

python .\scripts\run_alibaba_domain_calibration.py `
  --project-root . `
  --device cuda `
  --safe-mode gru-native

python .\scripts\generate_pre_submission_reports.py
```

### 4.4 实验同时报告两种设置

1. `zero_recalibration_tau_0_10`：沿用合成开发池确定的 10% 阈值；
2. `domain_calibrated`：只在 20 台 Alibaba calibration machines 上确定阈值，再在 40 台未见机器上测试。

若没有任何阈值满足预注册条件，程序不会强行选择“最好”的阈值，而会记录：

```text
No threshold satisfied the pre-registered calibration criteria
```

这是有效的负结果，不能用 held-out target 结果反向选择阈值。

## 5. 正式运行后的关键检查

Alibaba 结果文件：

```text
outputs/pre_submission_enhancements_d2904_t2904/alibaba_domain/alibaba_domain_result.json
```

检查：

- `decision` 是否为 `PASS_ALIBABA_DOMAIN_CALIBRATION_AND_HELDOUT_COMPLETE`；
- `domain_calibrated_tau` 是否存在；
- calibration 与 target machines 是否互不重叠；
- `selection_uses_test` 是否为 `false`；
- `test_used_only_after_selector_values_frozen` 是否为 `true`；
- 比较 10% 固定阈值和域内校准阈值的 harmful rate、MSE 与置信区间；
- 不只报告相对百分比，同时报告绝对 MSE、median gain、log-ratio 和 oracle headroom。

## 6. 方法边界

该补丁不增加：

- 带宽分配；
- 部署节点选择；
- 任务卸载；
- 网络时延联合优化；
- 新的 MSA-DTI 决策变量。

新增实验只加强数字孪生模型实例化的两条证据链：

1. 模型复杂度指标与真实承载开销的关系；
2. 外部工作负载域下，固定阈值与独立域内校准的差异。

