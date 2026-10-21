# 05 取证工具、知识、情报与模型（M06 / M07 / M08）

> 用途：固定上游源码与历史证据分析（2026-10-20对齐）。本轮负责调查所需工具、知识及模型服务，以实际查询和消费为验收；不以全量外部平台上线为前置。 当前职责见[范围](../../operations/alert-processing-scope.md)，阶段退出见[路线](../../operations/service-roadmap.md)，执行批次见[依赖计划](../../operations/dependency-migration-plan.md)。

返回[总入口](README.md)。这些模块共同给调查提供材料，但事实观测、参考知识和模型判断要分开保存与使用。

## 1. 数据边界

| 类型 | 例子 | 能支持什么 | 不能替代什么 |
| --- | --- | --- | --- |
| 原始/派生观测 | 来源日志、进程树、登录记录、设备状态 | 证明实体在某时发生的行为 | 工具未覆盖时间段的事实 |
| 资产/身份/业务上下文 | 设备归属、账号角色、批准变更 | 解释活动与合法性 | 当前事件的实际执行证据 |
| 外部情报 | IOC 信誉、KEV、漏洞、actor 描述 | 提供外部风险背景和关联线索 | 当前主机已被利用的直接证明 |
| 参考知识 | ATT&CK、runbook、SOP | 技术解释、调查问题、处置方法 | 本案事实、授权或已执行动作 |
| 历史经验 | Case closure、analyst disposition、组织记忆 | 先验与重复问题处理经验 | 当前告警一定 benign/恶意的保证 |
| 模型生成 | 根因假设、时间线推断、响应建议 | 分析、假设和建议 | 原始观测或真实执行回执 |

<a id="m06"></a>

## 2. ContextBundle：预取上下文

入口：[bundle.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/context/bundle.py)：`extract_entities`、`ContextBundle`、`ContextBundleBuilder`、`build_context_bundle`。

输入是 tenant、目标、摘要和 raw_alert；先识别 host/user/email/IP/domain/hash/URL 等实体，再尝试并发读取图邻域、历史记忆、UEBA、情报以及当前实现包含的其他上下文。字段和实际调用以 builder 为准，不能只看文件开头旧注释的来源数量。

| 输入/来源 | 中间产物 | 输出与失败 |
| --- | --- | --- |
| raw_alert 与 summary | `EntityRef(type,value)`；`type:value` key | 去重后的实体，需防止仅从模型文本提取的实体被当事实 |
| 图关系/影响范围 | 邻域节点、边、blast radius | 可为空；无图与无关系不能混为同一结论 |
| 历史 verdict/记忆 | 相似历史、来源 key、置信度 | 历史 prior；不应越过本案证据 |
| UEBA 基线 | 实体基线、peer group、deviation | 缺失基线时不能说行为正常 |
| 情报/身份等 | IOC、来源、上下文分类 | 传入模型的有界摘要和 errors/partial |

builder 默认单来源 timeout 3.5 秒；超时/异常填充 `errors` 并允许 partial，不强制阻止调查。移植需要确保最终报告把覆盖不足传递出去，而不是把每个可选字段都强制补齐。

## 3. 真实查询与工具面

### 3.1 API 统一只读工具

入口：[agent_tools.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/agent_tools.py)，内部适配在 [services/agent_tools](https://github.com/beenuar/AiSOC/tree/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/services/agent_tools)。

| 路由 | 输入 | 服务端职责 | 输出/验收 |
| --- | --- | --- | --- |
| `GET /agent-tools/backends` | 认证身份 | 枚举本 tenant 连接器、可用能力与 registry 状态 | 区分“没有后端”和“后端清单不可读” |
| `POST /agent-tools/siem-search` | indicator_type、value、since_hours、limit | 选本 tenant SIEM，生成后端查询；调用方不提交任意字段/查询文本 | 来源、查询结果、错误与覆盖 |
| `POST /agent-tools/vendor-read` | capability、target、可选 vendor、allowlist params | 选择连接器、解密服务端凭据、限定只读动词 | 厂商只读结果；不允许参数夹带替代凭据 |
| `POST /agent-tools/hunt-plan/execute` | 结构化 hunt plan | 生成受控数据湖查询并执行 | 实际事件、计划与结果；未配数据湖要诚实失败 |

这些路由从认证用户取 tenant，没有让模型自由选择 tenant。新增工具时优先采用“结构化意图 → 服务端查询”，不要让模型直接拼任意 SQL/SPL/ES|QL 或拿到连接密钥。

### 3.2 Case Investigator 工具

[tools.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/investigator/tools.py) 提供 IOC enrichment、Case/关联告警读取、关键词 MITRE 映射等；[splunk_evidence.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/investigator/splunk_evidence.py) 定位源连接器并查询证据。新增统一工具面并不意味着所有旧 wrapper 已迁移。

`fetch_related_alerts` 出错可返回空列表、`enrich_ioc` 出错返回 error dict。调用方必须按明确状态解释，不能统一按列表/字典真假判断有无威胁。各入口的服务 token、tenant 和返回形状也应逐条核对。

### 3.3 可选支撑

| 模块 | 功能输入 → 输出 | 20 的已知范围/移植注意 |
| --- | --- | --- |
| Enrichment，Go 服务 | IOC(type/value) → 信誉、风险、分类、漏洞、来源与时间 | full profile 未启；不能假定 VirusTotal 等厂商渠道可用 |
| UEBA | 行为事件/实体 → 基线、偏离与 anomaly | 参考 full 服务未启；stingAISOC 有自己的实现，按 Provider 接入 |
| 图谱/Attack Path | 实体及关系 → 邻域、路径、范围 | 没有运行图与实际数据的证据，不宣称攻击链已通 |
| Lake / Hunt | 时间范围/结构计划 → 历史日志和命中 | ClickHouse、OpenSearch、外部 SIEM 的方言和职责不能混用 |

源码：[enricher/types.go](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/enrichment/internal/enricher/types.go)、[enricher.go](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/enrichment/internal/enricher/enricher.go)、[UEBA main](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/ueba/app/main.py)、[lake.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/lake.py)、[hunts.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/hunts.py)。

<a id="m07"></a>

## 4. 情报采集与多存储

入口：[Threatintel main](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/threatintel/app/main.py)、[pipeline.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/threatintel/app/feeds/pipeline.py)、[scheduler.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/threatintel/app/feeds/scheduler.py)、[qdrant.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/threatintel/app/storage/qdrant.py)。

数据通路：Feed client / STIX parser → 规范化 IOC/actor → Redis Bloom 去重 → 尝试 OpenSearch、Qdrant、Neo4j → 可选 Kafka。客户端包含 CISA KEV、TAXII、MISP、OpenCTI、OTX 等，存在适配不表示已配置凭据或成功采集。

当前 pipeline 为各 sink 分别记录成功数量或不可达 `None`；不是跨所有存储的原子提交。Bloom 先记后写多个 sink，后续缺失补偿/重新采集行为需单独设计，不应以某个 sink 成功计数推断所有投影一致。

Qdrant 查询使用 tenant/shared 范围；公开情报可以共享，私有情报不可只因相似度高而跨租户返回。KEV 是已知被利用漏洞目录，虽经上游通用 IOC 管线存储，不应向用户包装成全部是网络地址型 IOC。

## 5. 五类知识/记忆实现

| 路径 | 来源、存储和检索 | 调用关系与边界 |
| --- | --- | --- |
| ATT&CK corpus | 本地 STIX；允许时 CDN；否则内置精简集；可向量化 | `mitre_full` 的语义函数在本次 `agents/app` 搜索中只有定义，没有找到内部调用方；关键词映射与向量检索需分开 |
| Threatintel vectors | Feed 规范化 IOC/actor → 独立集合 → 语义搜索 | 维度/模型、tenant/shared、来源 payload 必须保留 |
| Semantic memory | API 录入、runbook/Case closure → PG 元数据 + Qdrant | 写入成功但 embedding 失败可存在待索引状态；不能只查 PG 数量 |
| Institutional/organisation memory | 分析员教导、处置反馈、历史 prior → key/value 或语句 | 自动分诊已有实际读取；不是通用文档向量库 |
| Knowledge base | 租户 runbook/SOP/文章 → 文档/块及全文查询 | 自动分诊通过 reader 调 API 读取，使用全文 `ts_rank` 等；不是已经接到 semantic memory 的同一 RAG |

入口：[mitre_full.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/tools/mitre_full.py)、[semantic_memory.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/services/semantic_memory.py)、[semantic memory API](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/semantic_memory.py)、[knowledge_base.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/knowledge_base.py)、[runbook reader](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/context/knowledge_base.py)、[memory manager](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/memory/manager.py)。

runbook reader 包含数量/长度限制、不可信材料封装、注入过滤与 citations。拒绝一个可疑知识块不应等同判定告警恶意或禁止整租户分诊。引用应能解析至文档和块；“模型写了引用格式”不等于引用已经有效。

## 6. 上游嵌入与 20 部署补丁分开

| 项目 | 原参考路径 | 20 的部署专用处理 |
| --- | --- | --- |
| ATT&CK | 默认 OpenAI embedding；请求 3,072 维；原 Qdrant search 调用 | 本地 `qwen3-embedding:0.6b` 原生 1,024 维；新集合、稳定 UUID、HTTP search |
| Semantic memory | 1,536 维；由独立 backend 选择向量服务 | 同一本地模型，严格维度/数量/非零检查；新集合 |
| Threatintel | 1,536 维；fastembed 路径及不可用时降级需核对 | 移除本部署路径零向量降级；重新嵌入到新集合；原 payload/ID 保留 |

20 接线不修改本地 `opensource/AiSOC` 或服务器原始源码；由 [prepare.py](../../../deploy/aisoc20/embedding/prepare.py) 校验固定源 hash，生成服务专用副本并只读挂载。公共调用模块见 [aisoc_local_embeddings.py](../../../deploy/aisoc20/embedding/aisoc_local_embeddings.py)。因此分析“原参考代码”和“当前容器行为”必须说明 overlay。

当前实际数据：ATT&CK 内置 14 项、CISA KEV 1,748 项、actor 0、语义记忆清理后 0。不是全量 ATT&CK 或真实业务 Case。语义检索连通不证明精确 CVE 命中，也不证明调查 RAG 质量。

本地 Ollama 在 20 的 CPU 上运行；43 承担对话模型。Qdrant 进程 nofile 已由 1,024 调到 65,536；它是部署进程资源限制，不能解释成 Qdrant 只能存 1,024 条数据。客户端/服务端版本兼容仅对当前实际操作做过定向验证。

<a id="m08"></a>

## 7. 模型工厂、租户路由和成本

入口：[factory.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/llm/factory.py)、[routing.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/llm/routing.py)、[model_pins.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/llm/model_pins.py)、[llm_resolver.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/security/llm_resolver.py)、[contract.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/llm/contract.py)、[cost_telemetry.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/core/cost_telemetry.py)。

```text
认证 tenant → 租户模型许可/BYOK 解析 → request-scoped llm_override
→ role pin / 网关 alias → 路由与配对凭据 → make_chat_model
→ safe_ainvoke / 结构化解析 → 依据校验 → 调用与成本记录
```

当前源码角色有 `triage/recon/investigation/copilot/summary/report/nl/hunt/detection` 九种。20 既有部署记录描述七个对话别名接到 43，并只实测 `aisoc-triage`；**不能据此宣称另外角色全部已测或九种 alias 均已配置**。启用 Hunt/Detection 等功能前需核对实际网关配置、角色名与模型调用。

模型工厂不等于完整运行合同。新的节点仍需受控输入、超时/预算、结构 schema、调用记录和可见失败。上下文变量隔离 BYOK 比修改全局环境更适合并发；实际 tenant/权限仍由入口校验。

成本实现区分 gateway 实测、具体模型价目估算、unpriced。`aisoc-*` 是别名，不能按名称随意套单价。usage 缺失和费用未知保留 unknown/null；本地模型没有外部账单不意味着测得总成本为零。参考 `aisoc_run_costs` 聚合也不能直接替代 stingAISOC 每次实际调用的 model_calls/Artifact 合同。

## 8. 可复用部分与验收

优先复用 tenant 后端枚举、只读结构参数、来源信息、知识引用、模型路由隔离和成本 provenance。目标产品的 Markdown 知识按已确认的统一 intake/knowledge_type 实现，不照搬五套内部工作流。

| 场景 | 输入 → 中间产物 → 最终判据 |
| --- | --- |
| 只读取证 | 同 tenant 的实体与窗口 → 实际连接器请求、查询记录 → 返回事件有来源；越权请求没有厂商调用 |
| 依赖故障 | 无后端/超时/合法零命中 → 不同 provider 状态 → 报告不把故障解释为安全 |
| 知识检索 | 固定文档与 query → embedding 指纹、候选、ACL 回查 → 相关片段、版本/hash 与 citation 对应 |
| 模型路由 | 两 tenant/role → mock 请求或有界实际调用 → endpoint、model、credential scope 正确且不泄密 |
| 成本 | 有/无 gateway cost 与 usage → 独立调用记录 → 实测/估算/未知不混算 |

参考测试：`test_context_bundle.py`、`test_splunk_evidence.py`、`test_triage_knowledge_base.py`、`test_llm_contract.py`、`test_model_router.py`、API `test_semantic_memory.py`。20 的三项 embedding 合同检查与真实索引/检索 smoke 见 [07](07-data-tests-porting.md)，不代表上述所有测试通过。
