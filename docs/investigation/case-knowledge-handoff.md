# Case 知识检索与使用交接

更新于 2026-11-11。本功能由 C2 执行检索；C3、Deep、C6 消费本轮冻结片段。本地功能与 21 r3 接线证据见[验收](../../openspec/changes/archive/2026-11-11-enable-purpose-aware-case-knowledge/validation.md)，实际发布以 [PROGRESS](../../PROGRESS.md) 为准。

历史案例参考由[历史知识交接](historical-alert-knowledge-handoff.md)补充，已完成本地功能及 21 发布读回；本页下述 r3 证据适用于技术解释/取证指导，实际当前部署以根 PROGRESS 为准。

## 输入、检索与消费

| 位置 | 目标与输入 | 输出与边界 |
| --- | --- | --- |
| C2 技术解释 | 冻结材料中的命令、进程、动作；标题/规则明确标为 source_label；使用 technical_explanation 模板、资料类型与目的标签 | 技术功能、适用条件及解释边界的片段；不证明本案发生、恶意或授权 |
| C2 取证指导 | 同一冻结材料，使用 investigation_guidance 模板及独立类型/标签过滤 | 日志、字段、上下文及验证方法片段；模型建议仍只能用当前合法候选执行 |
| C3 | 本轮检索片段、用途、原文引用及真实来源状态 | 有依据的解释、未知与最多两项补查；引用不等于合理使用 |
| Deep | 当前问题与依赖可见的本轮片段 | 回答、交接或合法候选选择；本次不新增动态再检索 |
| C6 | 本轮材料、知识用途、前序结果及真实执行回执 | 结论/建议和引用；失败结论保持未采用，知识不成为独立案件观察 |

当前配置每个有主题的成员两个目的，最多 12 条查询；每目的返回最多 2 块、最低余弦相似度 0.45。实际阈值是配置，不是准确率保证。C2 复用原工具额度与来源排序，按工具预算可能跳过；无主题、未接入、未查、查空、失败保持区别。地址、模型、维度、集合、模板、类型、时限、限额全部从显式 profile 读取。

## 数据与字段对应

无数据库迁移；调查 V1 29 表、462 列及告警前后端合同不变。

| 信息 | 保存和读取位置 |
| --- | --- |
| 文档原文 | `public.aisoc_kb_documents`：`id/tenant_id/title/doc_kind/source_url/tags/chunk_index/chunk_total/content/created_at/updated_at`；原导入按正文分块 |
| 索引 | 独立 Qdrant 集合，point ID 为 PG 块 ID；payload 为 `tenant_id/doc_id/content_sha256/doc_kind/purposes/embedding_model/dimension`。hash 覆盖原文和身份/分类元数据 |
| C2 实际请求 | `run_steps.actual_args` 及 `tool_request/tool_response.actual_args.parameters.selectors[]`：`purpose/purpose_label/value/source_paths/filters/limit/score_threshold/use/profile_sha256`，仍保留成员与 object_key |
| C2 命中 | `tool_response.rows[]`：`record_id/object_key/namespace/purpose/purpose_label/use/similarity/content_sha256/limitations/record`；record 为当时 PG 回读原文，模型视图不使用 similarity/hash 作为业务依据 |
| 目标回执 | C2 `source_snapshot.sources[]` 按 `artifact_id` 关联知识工件，`source_metadata` 内保存模型/维度/集合/profile hash、`queries[]` 状态/数量/截断及 `calls[]` 请求回执；不扩展冻结 tool_exchange 顶层合同 |
| 模型输入映射 | `model_request.payload.source_map` → 同 Run 知识工件 `$.rows.N`，沿用非观察 `source_label` 角色；实际请求 body 保存片段 |
| 输出使用关系 | 解析对应 `model_response` 原答中的 source/evidence/support/counter IDs；不能以输入出现代替输出引用，更不能以引用代替校验接受或质量通过 |

知识块变化或删除后，旧索引命中不能当成现有原文；回读身份/hash 不一致时失败并保留错误，不静默回退检索。当前没有自动监听文档变化或自动重建索引；改文档后对指定块显式索引。

## HTTP 与配置

- 原 `POST /api/v1/kb/ingest` 返回各块 ID；`GET /api/v1/kb/documents/{id}` 读回基本字段。既有 `/kb/query` 保持文本检索路径，不作为本次 C2 向量检索证明。
- 新 `POST /api/v1/kb/index` 请求 `{"document_ids":["块 UUID"]}`，用原认证及 settings:write 接线。成功返回 `state/profile_sha256/collection/documents/calls`；失败返回 503 与 `detail.code/document_storage_unchanged=true`，正文保存与索引成败分开。
- `SOCAI2_KNOWLEDGE_PROFILE` 指向[配置](../../deploy/local-investigation/knowledge-profile.json)。当前使用本地 `qwen3-embedding:0.6b` 原生 1024 维；不补零或截断到其他空间。配置后的源失败不会回退为文本检索成功。
- 安装/升级：确认已有嵌入服务、专用集合名及原生维度；API 和处理入口挂载同一 profile 和受控 Qdrant key，并配置所需主机 allowlist。经原导入入口保存适用资料，按返回块 ID 索引，再核真实 C2 回执。不重建既有情报/组织记忆集合，不清库。
- 凭据只在受控文件，不写入文档、索引 payload、模型请求和页面。[生产 profile](../../deploy/aisoc21/production-v1.2.toml)的 knowledge 段定义挂载；[配置示例](../../deploy/aisoc21/production-profile.example.toml)保留显式启用说明。未配置环境保持其既有文本来源，不能据此宣称目的向量检索已启用。

## 4177

左侧 C2 的“知识库”节点，右侧按目的查看查询、来源路径、筛选、命中原文、hash、相关度、实际调用与错误；查空显示“查询完成，无符合条件的片段”，历史无目的回执显示未记录。模型节点仍可查看实际提示词、Schema、输入、原答、校验与错误；另列“已检索到 → 已进入本次输入 → 原答有结构化引用/未见结构化引用”。查看页面不触发检索或模型调用。

本地实测 6 条目的查询产生 8 条命中（4 个唯一块，有跨查询复用）；5 次模型输入均可定位知识，C3/C6 有引用，两个 Deep 无引用。8 条不能当成 8 个独立来源。召回中登录/网络主题也命中枚举方法，相关性质量和方法采用效果仍未证明；模型最终重复引用失败保留。A/I 新检索、Deep 动态再检索、独立处置检索及自动消费不在本次交付范围。
