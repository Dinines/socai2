# 历史告警知识与模型交接

本功能的设计、实施和验收状态见 [OpenSpec](../../openspec/changes/archive/2026-11-12-use-historical-alert-knowledge/tasks.md)，当前部署以 [PROGRESS](../../PROGRESS.md) 为准。技术解释/取证指导共用配置和来源链见[知识交接](case-knowledge-handoff.md)。本轮补齐历史案例参考，不改变原 C2 `history` 的同对象/事件窗口查询。

21 `v1.2-20261112-r1` 已实际发布并读回：一张已有演练告警卡完成 3 次 HTTP 入库/索引/GET和一次历史目的只读检索，4177 从实际 37 份追加至 38 份。没有生产分析 Run、自动入库或自动消费，临时 key 已撤销并核 401。本地模型质量仍为 NOT_PASSED，见[交付回执](../operations/evidence/historical-knowledge-20261112-01/delivery-summary.json)。

## 功能与接口

| 操作 | 接口与结果 |
| --- | --- |
| 保存历史卡片 | `POST /api/v1/kb/alert-experiences`，请求 `alert_ids: UUID[]`；返回逐条 `stored/document_id/source/verification/indexed=false` 或 `not_imported/reason` |
| 显式索引 | `POST /api/v1/kb/index`，请求 `document_ids`；核当前数据库来源与卡片一致后建立向量，入库成功与索引成功分别记录 |
| 读取完整卡片 | `GET /api/v1/kb/alert-experiences/{document_id}`，返回 `document_id/card`；普通文档 GET 的基本字段合同保持 |
| C2 检索 | 同一 Run 的知识工具增加 `historical_case_reference`，无新增生成模型或独立工具额度 |
| 内部查看 | 4177 C2 知识节点按目标显示原查询和结果，模型节点关联卡片与分诊/人工字段引用 |

使用原 KB 读写接线，不新增角色/审批流程。每次指定明确告警，服务端按认证租户读取；本功能未启用自动入库或自动知识消费。没有材料、事件时间、历史判断、或超过配置大小时返回未入库原因。快照不可拆散，不静默截断理由或人工正文。相同内容对应同一个文档 ID，新的来源内容形成另一快照。

## 数据及字段对应

调查 V1 表、列、枚举、告警 DTO 及其前后端取数关系保持。无 DDL。历史卡片复用 KB 文档表，不修改告警记录。

| 卡片字段 | 原始来源及含义 |
| --- | --- |
| `source.alert_id/material_id/material_revision/material_sha256` | `alerts.latest_material_id → alert_materials`，历史告警与材料原版本 |
| `source.triage_id/feedback_id` | `alerts.latest_triage_id/latest_feedback_id → alert_assessments`；保留当时选中版本 |
| `event`、`detection` | 原告警标题、事件时间、命名空间、厂商、等级，以及材料检测描述；来源标签 |
| `observations[]` | profile 指定材料路径、原值及 `historical_material` 标记；不成为本案 observation 引用 |
| `objects[]` | 对应材料的对象类型、命名空间、键、原规范值和路径 |
| `triage` | 原 verdict/rationale/recommendations/producer/actor/assessed_at 等，角色 `prior_analysis` |
| `feedback` | 原人工陈述字段，角色 `human_statement`；是否真有业务授权须看该原文和范围 |
| `material_alignment` | 判断与卡片材料的实际关联：same_material/different_material/unknown/not_recorded |
| `verification` | `not_independently_verified`；入库不增加可信等级，不将人工或历史模型输出升级为真值 |
| `limitations` | 历史范围、选取字段、建议未执行等边界；不存在的误报条件或处置结果不补写 |

`public.aisoc_kb_documents.content` 保存上述完整 JSON；`doc_kind=other`、独立 purpose tag、`chunk_index=0/chunk_total=1`。稳定 ID 包含租户及卡片摘要，索引核源内容。Qdrant 保留既有 payload 字段，并为历史卡片增加 `source_alert_id/event_epoch`。索引值与 PG hash 不一致仍失败，不把故障解释成查空。

C2 请求仍在 `actual_args.parameters.selectors[]`；历史目的的 `filters` 包含 `event_start/event_before/exclude_alert_ids`。默认回看 90 天、每主题 1 卡、相关度阈值 0.45，具体以 profile 为准。区间为 `[Case.window_start−90 天, Case.window_start)`，排除本轮全部成员。缺时间边界不生成历史查询，已有两个目的保持各自条件。

命中保存到原 `tool_response.rows[].record`：`history` 保存卡片的来源/观察/版本状态，`triage/feedback` 单独保存；原 `content` 仍保留序列化原件。`history.source_version_state` 区分 current/superseded/source_missing；旧快照不冒充新判断。元数据位于 C2 summary 的 `source_metadata`，没有新增 tool_response 顶层字段。

## 给模型的内容与任务

| 环节 | 实际输入和要求 |
| --- | --- |
| C2 | 程序构造查询并冻结卡片；没有模型生成的历史事实 |
| C3 | 本案材料与历史卡片并列；原历史观察/来源标签为非本案观察，分诊与人工正文各自独立引用。比较相同条件和缺失条件，形成解释及最多两项问题 |
| Deep | 复用已冻结且可见的卡片，结合当前问题/工具结果参考验证方法；不因历史内容扩大查询实体、时间或工具参数 |
| C6 | 用本案证据决定本案结论，历史只供对比与建议；明确不适用及未验证条件，不能继承历史判定、授权或已执行状态 |

模型视图去掉相似分/hash 和重复序列化正文，保留可读结构与原文。引用路径为知识工件 `$.rows.N`、`$.rows.N.record.triage`、`$.rows.N.record.feedback`；角色分别 source_label/prior_analysis/human_statement。`record_alert_ids` 指向原历史告警，`query_alert_ids` 只说明本次查询由哪些成员产生，不能互换。

4177 同时呈现“已检索”“已进入本次请求”“原答有结构化引用/未见结构化引用”和校验结果；引用存在不等于合理采用。页面仅使用保存记录，不再检索。缺范围、未查、查空和失败按实际原因显示。

当前没有结构化误报经验自动抽取、真实处置结果回灌、A/I 历史知识消费或 Deep 动态再检索。历史结论可能本身有错误；持续模型正文问题仍按问题清单记录，不由此次传递验收核销。
