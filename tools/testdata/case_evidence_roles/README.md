# Case Finding 来源角色验证

复用 `../case_integration/run.py` 执行 `config.json` 中的本机真实 PG 完整场景，模型和工具明确为替身。`replay.py` 只读保存的 C3/C6 请求及原答，分别检验生成约束、接收结果与一次纠正反馈，不调用模型或数据库；使用 `PYTHONPATH=services/api`。

`real-model.json` 配合 `../case_scope_recovery/real_model.py` 的 `prepare / run / export`，冻结源码与材料、执行一个独立正常 Run、导出原件及 GET。再由 `../case_scope_recovery/verify_local.py --config <文件>` 核字段与读取前后数据。所有配置显式选择本机隔离库与现有模型网关，预算沿正式策略。

Python 使用 `.local/conda-envs/socai2/bin/python`。同批禁止重派；源码或配置变化使用新批次，不覆盖原答、失败或 unknown。既有回执与边界见[本次验收](../../../openspec/changes/archive/2026-11-10-align-case-finding-evidence-roles/validation.md)，不能把替身结果、HTTP 成功或模型结构接收当作正文质量通过。
