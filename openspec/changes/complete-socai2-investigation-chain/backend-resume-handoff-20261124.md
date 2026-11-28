# 后端接续：已有首轮回执与统一调查读取合同

2026-11-24，组织者补齐。原后端聊天和新建接续聊天均遇到 Codex responses 403；新聊天尚未产生执行结果。本交接由当前统筹聊天依据已保存回执、源码及现场 Schema 完成，不记为接续聊天完成，也没有重跑原业务。

## 已有首轮如何接续

复用[本批安全事件到 Case 回执](es-ocsf-test-chain-20261124.md#安全事件到-case响应与原件)和[8181 案件回链](es-ocsf-test-chain-20261124.md#8181-正式案件回链与响应)。既有 Case 的首轮已结束并保存部分交付结果；4177 对同案任务、Run、结果及步骤的读取已有原批通过结论。8181 的列表、详情、成员/事件回链及历史同轮读取已有记录，统一目录/任务转发及完整结果查阅仍按原缺口跟进。

接续应沿原回执中的任务和 Run 链读取，不能因为 `baseline_records` 不再列出已结束轮次而重建案件或重新调查。原批私有材料留在原处；该交接不复制业务标识、正文或模型原答。当前无新增业务查询、写入或模型执行。

## 指定 Run 的身份解析已有合同

现行 `GET /analysis-runs/{run_id}/steps` 返回的 `RunStepPage` 顶层已包含 **`run_id`、`subject_type`、`subject_id`**，与 `RunArtifactPage` 一致。这由正式 Schema 和 `run_record_contracts.py`、`adapters/run_records.py` 共同确认。因而当前页面的 `/investigations/:runId` 刷新可以直接读取该步骤目录解析主体，**无需扫描整个目录或新增旧 `/runs/{id}/context` 的服务端兼容接口**。

| 输入/位置 | 处理及下一读取 |
| --- | --- |
| 从统一目录选中 | 使用 `items[].run_id`、`subject_type`、`subject_id` 和 `detail_url`；保留结果引用的 `source_run_id`/`url` |
| 只有路由中的 run_id | GET 对应步骤目录；使用顶层真实主体身份定位主体 Run 详情。404 保留该轮不存在，不退到 latest |
| 告警 Run | GET `/alerts/{subject_id}/analysis/runs/{run_id}` |
| 事件 Run | GET `/incidents/{subject_id}/analysis/runs/{run_id}` |
| Case Run | GET `/cases/{subject_id}/runs/{run_id}` |
| Run 已读到 | 跟随 `steps_url`、`artifacts_url` 完整分页；`artifact_refs[].content_url` 按原始来源读取，复用工件不能强改成当前主体的原件 |
| 任务未产生 Run | 按 `status_url` 读取任务；`latest_run_id` 为 null 时显示已受理/排队等实际状态，不伪造 Run |

以上路径相对于 `/api/v1/socai2`。后端返回的完整相对 URL 只做同源客户端适配，避免再次拼接出重复 `/socai2` 前缀；Origin 和端口仍走所选 profile。

## 本步平台缺少的 GET 转发

现场平台 Schema 尚无下表操作；本轮没有请求匿名或带会话业务端点来代替真实路由验收。候选实现应只补本步用到的入口、参数及类型，正式换版另按当批授权。

| 路径 | 查询参数 / 角色 |
| --- | --- |
| `/analysis-runs` | `subject_type`、`subject_id`、`run_kind`、`intent`、`state`、`time_from`、`time_to`、`limit`、`cursor`；已保存 Run 目录 |
| `/analysis-runs/{run_id}/steps` | `limit`、`cursor`、`kind`；目录兼具真实主体身份 |
| `/analysis-runs/{run_id}/steps/{step_id}` | 无查询参数；精确步骤 |
| `/analysis-runs/{run_id}/artifacts` | `limit`、`cursor`、`step_id`；原件目录及内容链接 |
| `/alerts/{subject_id}/analysis-tasks` 及 `/{task_id}` | 列表只收 `limit`、`cursor`；详情无查询参数 |
| `/incidents/{subject_id}/analysis-tasks` 及 `/{task_id}` | 同上，限定所属事件 |
| `/cases/{subject_id}/analysis-tasks` 及 `/{task_id}` | 同上，限定所属 Case；与普通人工 `/tasks` 分开 |

平台现有主体 Run 详情、trace 和工件内容转发应复用并检查返回 URL 的可达性。新版路径放入明确转发表，保留平台登录和既有路由边界，不扩大到任意上游代理。

## 页面字段适配

| 页面当前取法 | 正式合同及语义 |
| --- | --- |
| `metrics.total` | `statistics.total_runs` |
| `metrics.partial` | `statistics.by_delivery_state.partial` |
| `metrics.no_case` 用作“未升级调查” | `statistics.not_escalated_count`；无关联 Case 的 `without_related_case_count` 是另一含义 |
| `metrics.with_case` | `statistics.related_case_count`，是去重 Case 数，页面单位应与之对应 |
| `items[].kind` | `items[].run_kind` |
| `kinds`、`requested_from`、`requested_to` | 单值 `run_kind`、`time_from`、`time_to`；不得静默丢弃多选或搜索控件的既有功能要求 |
| 输入是否存在由 `input_artifact_id` 推断 | 目录使用 `input_member_count`，null 与 0 分开；是否有输入原件沿详情/工件目录核实 |
| 前端假定目录提供全部 `stop_reason`、duration 等字段 | 目录按其实际字段显示；详情才读取详情字段。用已有开始/结束时间计算时长时保留未知，不能把 null 当 0 |

正式目录不接受旧 `q`、`case_id`、`alert_id` 查询参数。已确认页面筛选需求若无法用主体/时间/状态等正式参数表达，按原 F 项明确缺口，不以当前页客户端过滤冒充全量检索。

## 验收出口与后续

本交接完成结构准备。下一步是页面/平台候选接线：同一已保存代表 Run 的目录→主体解析→详情→步骤→工件→主体回链，以及深链刷新和一次续页。保留执行、交付、业务判定、采用及质量的不同含义；原件和身份在受控端比对，向会话只回允许的检查结果。

本步不验建案/关联的 201 分配回执、后轮 202 提交、独立评论、UID 新接口或持续接收修复；这些已在[统筹审计](integration-coordination-audit-20261124.md)分配到后续各步。平台/页面正式读回通过前，统一调查入口仍标为未完成。

结构依据：[本轮三处实际 Schema](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/runtime-contract-structure.json)、`services/api/investigation_http/run_record_contracts.py`、`external_routes/run_records.py`、`external_routes/run_directory.py`、`external_routes/analysis_tasks.py`。本轮严格 OpenSpec 校验沿统筹审计回执，不以 CLI 成功代替业务验收。
