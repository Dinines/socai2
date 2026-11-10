# Deep/C6 离线交接核对

本节的历史 `audit.py` 只读取配置指定的历史数据库导出和 C3 输入账本，不导入业务运行环境、不连接数据库、不调用模型、不创建 Case/Run。目标是核对后续步骤实际拿到什么，及输出身份字段能否在程序侧恢复。

```sh
.local/conda-envs/socai2/bin/python -m tools.testdata.case_followup_eval.audit --config tools/testdata/case_followup_eval/config.json
```

`case-followup-audit-20261109-01` 已结束。输出目录存在时拒绝覆盖；重新选择材料或扩展核对须使用新配置/批次，不能用本命令改写原回执。

输出包括：

- `summary.json`：同一历史 Run 的原件 hash/大小、来源角色、C3/Deep 到 C6 的引用同源映射、各步实际输入/输出大小。
- `deep-input-inventory.md`、`c6-input-inventory.md`：历史材料清单，正文和旧编号保持。是给开发者看的展开，不是准备发送给模型的候选提示。
- `*-output-schema-not-active.json`：Deep 去掉程序已知的 `question_id`；C6 保留六块业务输出、使用可还原的成员/对象短号。没有接入业务代码。
- `*-output-replay-not-generated.json`：由旧原答机械转换，精确还原为旧答；不是新生成，更不是纠正旧语义错误。

字段路径、文件和批次均由 `config.json` 提供。工具按完整路径修改 C6 输出身份字段，不全局替换正文中的 UUID、短号或旧引用。

同源映射仅证明同一来源路径可达，不证明可见值相同、模型理解正确或来源互相独立。旧 C3 输入账本含离线补充的同 A 回执，这些回执没有进入当时的 C1；不得追认旧执行看过它们。当前本地 C1 的实际冻结能力另见接入报告。

说明：[Deep/C6 交接分析](../../../openspec/changes/complete-socai2-investigation-chain/case-followup-handoff-20261109.md)。

用户要求查看各模型环节的完整输入和输出后，使用 `inventory-config.json` 和 `export_inventory.py` 另行只读提取 7 次已保存调用，批次为 `model-io-inventory-20261109-01`，也已结束。实际消息、输出 Schema 和可见原答逐值保留，不导出提供商隐藏推理字段，不运行或重派任何请求。业务职责及字段说明见[输入输出清单](../../../docs/investigation/model-input-output-current-20261109.md)。

## 2026-11-10 本地接入与对比

`compare.py --config comparison-config.json` 读取同一保存 Run，通过当前业务构建器生成 Deep/C6 前后输入、Schema、来源依赖和旧输出机械往返。`case-followup-comparison-20261110-01` 已固定，不覆盖重派；不连接数据库/模型，字节不是 tokens。旧 C1 未冻结的同 A 回执只作为明确的离线补充，不能追认历史模型已读。

`integration-config.json` 配置独立测试库和 Case 策略。使用既有 `tools.testdata.case_integration.run --config ... --attempt <新的批次名> --only <方法>` 执行四项：`test_case_boundary_followups_final_storage`、`test_case_boundary_followups_final_partial`、`test_case_boundary_followups_final_correction`、`test_case_boundary_followups_without_c3`。替身返回与真实 PG 保存/读回分开；不访问真实模型/湖、不改正式库和 DDL。已有 `pg-01` 至 `pg-04` 已结束，原失败留存。

保存的联合 A/I/Case 快照按 case_integration README 使用 `update_processing_audit.py --batch <case导出目录>`。`--folder` 是另一种严格的 Case 显式关联导出，不能把含通过告警关联的 I 背景材料的联合测试快照冒充该格式。

当前实现与结果：[接入报告](../../../openspec/changes/complete-socai2-investigation-chain/case-followup-integration-20261110.md)。
