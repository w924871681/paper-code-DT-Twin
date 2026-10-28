# 新增验证：输入、时序与划分核验

检查日期：2026-10-28。范围是新验证的输入解析、特征、窗口和角色定义；本记录不声称全面独立重训或核实全部历史使用情况。

## 原始指标和输入顺序

`external_runner.py` 的 `load_raw` 按 v1.3.3 `data/source_normalization.json` 的 `raw_metric_columns` 名称从 CSV 表头定位十列（而非依赖 Materna 原始列位置），再调用同一 `frozen_features.causal_features`。十列依次为 CPU 核数、CPU 额定容量、CPU 使用 MHz、CPU 使用率、内存额定容量、已用内存、磁盘读、磁盘写、网络接收和网络发送；`CPU usage [%]` 在 raw 数组下标 3。Materna 文件还包含额外的内存使用百分比与磁盘大小列，但不属于模型十列。

Bitbrains 文件头 `Timestamp [ms]` 与数值量级不符：例 `fastStorage/2013-8/1009.csv` 前两条时间戳为 1376314846、1376315146，差 300，数值对应 2013 年 Unix 秒。历史 `export_prefix.py` 将字段原样转整数；新 `load_raw` 也原样读取，未进行毫秒转换，因此两者一致。Materna `Materna-Trace-1/01.csv` 示例首两条为 `05.11.2015 00:00:00`、`05.11.2015 00:05:00`；新代码解析为相对于首条的秒数，间隔 300。特征函数的时间间隔通道使用相邻秒数之差除以 1200。不能据 Bitbrains 列名将其数值解释为实际的毫秒值。

Materna 选定 30 台 VM 的前 3000 条记录，结构预检发现 3 台各有一次非 300 秒间隔；新实验保留实际间隔。预测的 H 表示记录数，不应将所有预测统一声称为严格固定分钟数。

## 两个旧前缀的逐元素比对

方法：从 `MSA_DTI_T7_LIMITED_BITBRAINS_REAL_20261025/ROLE_LOCK.json` 读取案例和原始归档，调用新 `external_runner.load_raw` 读取原案例的 `native_start` 至 `native_start+T`，与旧 `prefix/<slug>/prefix.bin` 按同一结构化 dtype 比较时间戳和十列原始指标，使用 `numpy.array_equal(..., equal_nan=True)` 比较数值。再将同一旧前缀分别输入新 `external_runner.calc` 和 v1.3.3 的 `reproduction/historical/features/prefix_common.py` 的 `prefix_selection`，检查 `Xs`、`ys`、`Xv` 和 `yv`。

| 旧前缀 | 行数 | 时间戳和十列 | 支持输入/标签及验证输入/标签 | T / B | 验证窗口 |
| --- | ---: | --- | --- | --- | ---: |
| `vm1009_H1_K10` | 1553 | 全部相同（NaN 等值比较） | 四项逐元素相同 | 1552 / 627 | 1351 |
| `vm1009_H4_K20` | 1560 | 全部相同（NaN 等值比较） | 四项逐元素相同 | 1559 / 621 | 1342 |

这两个是使用历史数据进行的接口比对，并非对所有新增样本和所有权重训练过程的逐条独立复现。对新实验全部 236 个选择记录，保存的验证窗口数均介于 1342 和 1351；10 或 20 是参数更新所用支持窗口数量，选择还使用后续验证窗口。

## 未来标签索引与角色范围

对 `external_runner.calc`：支持起点 `95..95+K-1`；验证起点从验证段起点加 95 开始、结束于 `validation_end-H-1`，标签索引为起点加 `1..H`。`T=validation_end-1`，所以最后一个验证标签不晚于 T。`run_eval` 的预测起点为 `T..T+B-1`，标签从 `T+1` 开始；预测输入可包含已观测历史，未来标签不用于适配和选择。两种极端 H/K 设置与原 `prefix_selection` 的训练和验证张量及原始 T/B 一致，如上表。

Bitbrains 新实验使用 29 台，它们全部属于原 `data_roles.json` 的 evaluation VM；`PROTOCOL_LOCK.json` 的新段起点分别为 native 行 3287 或 3288，恰为对应旧 `native_start` 加 3000。原稿 `target_windows.csv` 中 evaluation 案例最后一个预测目标的相对索引最大为 2183，因此新段在该版论文已记录的评估目标之后。此时间顺序不单独证明新段在更广泛的历史研究过程中从未被查看或使用，也不能将相同 VM 的前后片段算作不同独立 VM。

## 重要执行边界

新 `external_runner.py` 的第 30–32 行在 `for j,row in reader` 取得一行后才检查 `len(rows)==n`。选择阶段因此会额外取得一次首条后续 CSV 行，由 CSV 解析器分隔为字符串；该行的 CPU 字段没有进入 `rows`，也没有转换为数值、保存、用于适配或选择。可说未来标签没有用于适配及模型选择，但不可说新选择进程在物理读取层面绝未读取未来记录。历史 `export_prefix.py` 则明确限制读取次数，不发生该预取。要声称严格物理隔离，需先修改并重新验证，不能事后把已完成运行视作具备该属性。

Materna 的首次选择尝试曾因小数逗号被误判为无效标签而失败，修复后的版本将逗号转换为小数点，并在重新固定代码后运行；保留两次锁及失败记录。Bitbrains 的 11 个失败案例在其余 225 个案例测试开启后采用新进程重试，重试选择封存后才运行这些案例的测试，因此不能声称全部 236 个案例均在任何测试结果开启前整体封存。
