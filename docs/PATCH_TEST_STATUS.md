# 补丁测试状态

已完成以下工程测试：

1. `python -m compileall`：新增 Python 文件全部通过语法编译；
2. 无训练审计与报告脚本：在用户上传的公开仓库结果表上运行成功，生成 constraint activity 表、跨池 safety 表及新 Fig.10 Pareto 图；
3. Alibaba 完整链路冒烟测试：使用 82 台人工生成机器轨迹，完成
   - 20/20/40 source/calibration/held-out 划分；
   - 12 个来源权重资产的 smoke 训练；
   - calibration 和 held-out evaluation；
   - 当无阈值满足预注册条件时，正确返回 `domain_calibrated_tau = null`，没有使用 held-out 结果反向选阈值；
4. Hosting profile 冒烟测试：使用兼容的测试权重完成 7 个候选、两个预测跨度的 CPU 测量链路。

这些测试仅验证代码结构、恢复机制、数据隔离和输出格式。人工轨迹与测试权重不构成论文实验结果。正式论文结果必须在原始 Alibaba 数据、冻结正式权重和目标硬件上重新运行。
