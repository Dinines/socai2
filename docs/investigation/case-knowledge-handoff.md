# Case 知识检索与使用交接

更新于 2026-11-12。本功能由 C2 执行检索；C3、Deep、C6 消费对应 Run 的冻结片段。用途／条件筛选、模型去重和按任务选取已随 21 `v1.2-20261112-r3` 发布并读回，见[前批用途筛选验收](../../openspec/changes/archive/2026-11-12-refine-purpose-aware-knowledge-use/validation.md)及 [PROGRESS](../../PROGRESS.md)。

当前 r5 的分诊后同步及本地／生产证据边界由[历史知识交接](historical-alert-knowledge-handoff.md)补充，与技术解释／取证指导共用存储，通过目的标签及适用条件隔离选择；不需要为每个用途新建物理知识库。

## 输入、检索与消费

| 位置 | 目标与输入 | 输出与边界 |
| --- | --- | --- |
| C2 技术解释 | 冻结材料中的命令、进程、动作；标题/规则明确标为 source_label；使用 technical_explanation 模板、资料类型与目的标签 | 技术功能、适用条件及解释边界的片段；不证明本案发生、恶意或授权 |
| C2 取证指导 | 同一冻结材料，使用 investigation_guidance 模板及独立类型/标签过滤 | 日志、字段、上下文及验证方法片段；模型建议仍只能用当前合法候选执行 |
| C3 | 本轮检索片段、用途、原文引用及真实来源状态 | 有依据的解释、未知与最多两项补查；引用不等于合理使用 |
| Deep | 当前问题与依赖可见的本轮片段 | 回答、交接或合法候选选择；本次不新增动态再检索 |
| C6 | 本轮材料、知识用途、前序结果及真实执行回执 | 结论/建议和引用；失败结论保持未采用，知识不成为独立案件观察 |

已部署的[用途筛选与任务选取](../../openspec/changes/archive/2026-11-12-refine-purpose-aware-knowledge-use/tasks.md)：每个有主题的成员三个目的，相同目的／文本／命名空间／过滤范围与适用字段合并，最多 12 条查询；每次最多获取 8 个候选，技术／方法最多各 2 块，历史最多 1 卡，余弦阈值保持 0.45。相似度只排序候选，不能绕过适用条件。C2 复用原工具额度与来源排序，不循环补搜；无主题、未接入、未查、原始查空、全部筛除、失败分别记录。

文档沿原入口使用 `knowledge:<目的>` 与 `applies:<字段语义键>=<值>` 标签。例如 `applies:ocsf.process.name=powershell.exe`，路径与规范化由 profile 定义。至少一个主题条件匹配且无冲突；声明条件缺失时排除，明确带 `applicability:generic` 的技术／方法资料可保留未知条件，但仍须主题匹配且无冲突。旧文档不自动改标，仍可直接读回。

C3／Deep／C6 按块身份和内容版本去重，原检索行保持；`source_map[].knowledge.origins` 记录所有原路径和用途。Deep 的可选目的为取证指导／历史参考，按问题成员与原查询主题映射选取，历史空成员范围不代表全案通用；前序引用的卡片及其分诊／反馈原角色优先恢复。C6 只补未决问题的可选知识。知识上限分别为 12,000／8,000／8,000 字符，预算不足省略整条可选内容，不裁正文；必要依赖仍受现有整体输入上限约束。

本地固定流程修复（尚未发布）：已选知识按查询适用成员作辅助参考，所有知识都不计入本案成员/结论/影响覆盖；C3/C6 接收和纠错一致。合并条目的目的与成员范围须来自同一 origin，必要前序引用依赖保留。一次新批知识原引用已保存并由 GET 读回，但 C6 仍因建议缺依据拒收，生成 Schema 已补齐最少一个来源；合理使用和整体固定流程尚未通过。见[固定流程验证](../../openspec/changes/complete-socai2-investigation-chain/fixed-flow-validation-20261112.md)。

本地知识正文整理（尚未发布）：新导入的完整 JSON 对象/数组保留一个原文块，普通文本仍按既有规则分段；超过现有索引配置上限仍拒绝索引，不扩大预算。C3/Deep/C6 在原件检查后共用结构化业务字段投影，已识别技术知识保留说明、平台、日志及核查方法原文，内部对象引用/版本字段留后台，普通正文与未知结构不语义改写。实际样例845字符原文生成448字符[模型正文](../operations/evidence/model-input-selection-20261112-05/knowledge-model-content.txt)；[离线回执](../operations/evidence/model-input-selection-20261112-05/README.md)明确没有导入/索引/模型调用。旧碎片不自动合并或重写，后续使用完整原件重新导入/索引；本步不改变 HTTP 字段、关联、存储列或表结构，新导入返回的块数量可能变化。下一次整体发布需同时包含 API 分块代码与处理侧正文投影；知识正文整理尚未发布。随后 [Deep/C6](../operations/evidence/model-input-selection-20261112-06/README.md)已完成本地按任务筛选及知识卡外壳清理，保留原用途/成员条件、知识版本和前序必要依赖；本批仅复用旧冻结材料，旧 JSON 切片未改。合理使用质量和完整固定流程仍未通过。

## 数据与字段对应

本项无数据库迁移，告警前后端合同不变；调查当前28表/450列来自独立的空表清理，V1 29表/462列保留作基线，见[表职责](investigation-table-scope.md)。知识表及下列存取字段不受本次模型输入整理影响。

| 信息 | 保存和读取位置 |
| --- | --- |
| 文档原文 | `public.aisoc_kb_documents`：`id/tenant_id/title/doc_kind/source_url/tags/chunk_index/chunk_total/content/created_at/updated_at`；线上仍按原正文分块，本地新导入完整 JSON 的完整块规则尚未发布，字段与旧数据保持 |
| 索引 | 独立 Qdrant 集合，point ID 为 PG 块 ID；payload 为 `tenant_id/doc_id/content_sha256/doc_kind/purposes/embedding_model/dimension`。hash 覆盖原文和身份/分类元数据 |
| C2 实际请求 | `run_steps.actual_args` 及 `tool_request/tool_response.actual_args.parameters.selectors[]`：`purpose/purpose_label/value/source_paths/filters/limit/score_threshold/use/profile_sha256`，仍保留成员与 object_key |
| C2 命中 | `tool_response.rows[]`：`record_id/object_key/namespace/purpose/purpose_label/use/similarity/content_sha256/limitations/record`；record 为当时 PG 回读原文，模型视图不使用 similarity/hash 作为业务依据 |
| 目标回执 | C2 `source_snapshot.sources[]` 按 `artifact_id` 关联知识工件，`source_metadata` 内保存模型/维度/集合/profile hash、`queries[]` 状态/数量/截断及 `calls[]` 请求回执；不扩展冻结 tool_exchange 顶层合同 |
| 选入依据 | selector 的 `facets/candidate_limit`；命中行的 `applicability/query_alert_ids/query_source_paths`；`source_metadata.queries[].candidates` 保存身份/hash、相似度、选入／筛除原因及匹配／冲突／未知条件，全部筛除为 `outcome=filtered` |
| 模型输入映射 | `model_request.payload.source_map` → 同 Run 知识工件 `$.rows.N`，沿用非观察 `source_label` 角色；实际请求 body 保存片段 |
| 输出使用关系 | 解析对应 `model_response` 原答中的 source/evidence/support/counter IDs；不能以输入出现代替输出引用，更不能以引用代替校验接受或质量通过 |

知识块变化或删除后，旧索引命中不能当成现有原文；回读身份/hash 不一致时失败并保留错误，不静默回退检索。当前没有自动监听文档变化或自动重建索引；改文档后对指定块显式索引。

## HTTP 与配置

- 原 `POST /api/v1/kb/ingest` 返回各块 ID；`GET /api/v1/kb/documents/{id}` 读回基本字段。既有 `/kb/query` 保持文本检索路径，不作为本次 C2 向量检索证明。
- 新 `POST /api/v1/kb/index` 请求 `{"document_ids":["块 UUID"]}`，用原认证及 settings:write 接线。成功返回 `state/profile_sha256/collection/documents/calls`；失败返回 503 与 `detail.code/document_storage_unchanged=true`，正文保存与索引成败分开。
- `SOCAI2_KNOWLEDGE_PROFILE` 指向[配置](../../deploy/local-investigation/knowledge-profile.json)。当前使用本地 `qwen3-embedding:0.6b` 原生 1024 维；不补零或截断到其他空间。配置后的源失败不会回退为文本检索成功。
- 安装/升级：确认已有嵌入服务、专用集合名及原生维度；API 和处理入口挂载同一 profile 和受控 Qdrant key，并配置所需主机 allowlist。经原导入入口保存适用资料，按返回块 ID 索引，再核真实 C2 回执。启用分诊后历史同步时，处理身份需知识表 SELECT/INSERT，按[历史卡片交接](historical-alert-knowledge-handoff.md)执行配置及增量脚本。不重建既有情报/组织记忆集合，不清库。
- 凭据只在受控文件，不写入文档、索引 payload、模型请求和页面。[生产 profile](../../deploy/aisoc21/production-v1.2.toml)的 knowledge 段定义挂载；[配置示例](../../deploy/aisoc21/production-profile.example.toml)保留显式启用说明。未配置环境保持其既有文本来源，不能据此宣称目的向量检索已启用。

## 4177

左侧 C2 的“知识库”节点，右侧按目的查看查询、来源路径、候选选入／排除、命中原文、hash、相关度、实际调用与错误；全部筛除单独说明，历史无目的回执显示未记录。模型节点可查看实际提示词、Schema、输入、原答、校验与错误；另列“已检索到 → 已进入本次输入 → 原答有结构化引用/未见结构化引用”、知识合并出处及未送入原因。查看页面不触发检索或模型调用。

前批用途筛选的本地一次流程有 9 条查询／5 行（3 唯一块），排除 6 次条件冲突和 2 次过期卡候选，跨目的正文合并 2 次。6 次模型调用的原答保存；C6 纠正仍拒收，Result partial/rejected、conclusion=null，模型质量 NOT_PASSED。前序已接受结果未引用知识、两个 Deep 为全案问题，因此知识依赖恢复及缩小问题范围只由直接检查支持，不能扩大实际链路结论。该批生产 7 次业务 HTTP 与 3 个只读目的查询通过，4177 当时 39 份记录，浏览器实际显示筛除与合并关联。前批失败及回执保留，不据条件过滤宣称合理使用质量通过。A/I 新检索、Deep 动态再检索、独立处置检索及自动消费不在本次交付范围。
