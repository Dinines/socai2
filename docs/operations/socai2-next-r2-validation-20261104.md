# 独立新服务 r2 验收结束记录

r2 使用独立服务 `next-20261104-n5`，真实模型质量验收未通过，现已结束。本批没有替换原服务。r1 的原始回执和未知执行记录保持不变；r2 的失败结果不会被后续修复回填为成功。

完整机器可读回执见 [r2 汇总](socai2-next-r2-validation-20261104.json)，统计以 [最终数据库快照](evidence/socai2-next-acceptance-20261104/20261104T054920-r2-export/database-20261104T054924.json) 为准。目录内较早快照只含当时已经完成的阶段，不能代替最终快照。

## 输入与实际执行

本批核对并复用 r1 的两条告警、一个事件和两条湖事件，没有重新投递 Fusion、增加告警或增加湖记录。两条告警各核对 19 个已收到字段，两条湖事件各核对 18 个字段；来源文件哈希和逐项核对记录保存在 [reuse 回执](evidence/socai2-next-acceptance-20261104/20261104T054920-r2-export/reuse.json)。r2 使用独立的 Case 和操作键，不复用 r1 的执行请求或模型答复。

| 阶段 | 实际结果 | 输入 / 输出 / 合计 tokens | 已完成 PG 查询 |
| --- | --- | ---: | ---: |
| 第一条告警 A | `alert_answer_internal_source_alias_in_prose`，未发布有效分诊 | 2224 / 399 / 2623 | 2 |
| 第二条告警 A | 同上，未发布有效分诊 | 1963 / 378 / 2341 | 3 |
| 事件 I | `incident_answer_shape_invalid`，保留失败尝试 | 3522 / 1792 / 5314 | 0 |
| 首轮基础调查 C | C3 为 `analysis_shape_invalid`；Run 以 `no_accepted_main_analysis` 失败 | 3033 / 1436 / 4469 | 2 |

实际发生 4 次模型请求，收到 4 次答复，已报告用量合计 **14747 tokens**（输入 10742，输出 4005），费用均未定价。执行账本记录 **7 次已完成 PostgreSQL 查询**，保留结果共 1 行；另有 5 条跳过的 Tool 记录。没有执行湖查询、Deep 模型或 C6 模型。不能将这 7 次 PG 查询描述为湖查询或外部补证成功。

C 保存了系统交接 Result：`conclusion=null`、`conclusion_origin=system`、`validation_state=system_only`、`delivery_state=partial`。这不是有效模型结论，也没有自动更新 Case 当前判断。H 人工任务、范围更新准备和第二轮 C 均未派发；最终快照中任务、任务修订和 Case 当前判断均为 0 条。

## 确认的问题及边界

两份 A 答复不仅在正文中泄露内部来源别名，还把 SyntheticLab、synthetic validation 等来源/测试标签解释为良性依据。原材料没有给出人工授权，这种推断不能接受。I 与 C3 的嵌套结构未满足实际输出合同；顶层字段齐全不等于整个答复有效。

只读模型配置核查显示，当前 5 个网关别名均指向同一个上游模型名。上游元数据自报为 vLLM 托管的 Qwen3.5-9B；这是服务自报信息，不能据此独立确认权重，也没有证据证明它是固定模拟答复或缓存。r2 实际只使用 `json_object`，没有传入字段级 JSON Schema。上游接口声明支持 `json_schema` 和 `strict`，但严格结构约束能否经网关传递并实际生效，仍须通过下一候选验证。结构约束也不能代替来源角色和结论语义校验。

网关配置的 45 秒与 r1 C3 约 45 秒后进入未知状态相符，但现有日志没有足够证据确认 r1 的传输根因；本批不会把它改写为已证实的超时，也不会重试该 Run。模型元数据和能力线索见 [配置回执](evidence/socai2-next-service-20261104/r2-model-metadata/receipt.json)、[上游元数据](evidence/socai2-next-service-20261104/r2-upstream-metadata/receipt.json) 和 [Schema 元数据](evidence/socai2-next-service-20261104/r2-upstream-schema-metadata/receipt.json)。这些核查没有调用模型。

## r3 驱动准备状态

r3 驱动已准备，尚未部署或派发。执行前依赖 n6 的来源字段投影和严格 JSON Schema 修复通过验证，并冻结新的候选。r1/r2 在当前驱动中仅允许导出；r3 只允许读取并核对原始来源，禁止重新 seed，使用新的 Case 和全部新操作键，原每 Run 额度不变，总上限仍为 11 次模型调用。

H 和第二轮 C 的前置条件已收紧：首轮匹配 Run 必须 `completed`，匹配 Result 必须为 `baseline` / `model` / `accepted` 且结论非空。系统交接、失败、未知或来源不匹配均在任何后续 HTTP 写入前拒绝。5 项离线测试通过，包含批次隔离、来源复用、路由、参数传递及门槛反例；3 个驱动/测试文件 Ruff 通过。冻结哈希见 [r3 离线回执](evidence/socai2-next-service-20261104/r3-driver-offline/receipt.json)。
