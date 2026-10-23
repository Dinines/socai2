# v1 调查入口、逐步输出和结论读取

[返回入口](README.md)。本篇给业务后端“每一步输入什么、产出什么、到哪里读”。内部节点不等于独立HTTP接口，节点数也不等于模型调用数。[完整机制](../../architecture/investigation.md)、[实际模型/工具输入输出](../../architecture/investigation-preprocessing-tools.md)

## 1. 入口与编排选择

| 入口 | 外部输入点 | 输入/身份 | 输出点 | 当前边界 |
| --- | --- | --- | --- | --- |
| Kafka自动分诊/调查 | `socai2.alerts.fused`；由Fusion生产 | 合法fused、canonical Alert、同tenant | 确定Run、triage_verdict；按配置升级graph，Run工件/MD | v1生产worker已开启；新Run已自动交付partial调查与MD，质量未验收 |
| Case人工调查 | API `POST /api/v1/cases/{case_id}/investigate` | Bearer `cases:write`、已存在同tenant Case；body `{"alert_summary":"可选问题说明"}` | `{run_id,case_id,status,message}`，随后事件/报告 | 默认四节点；API自己从Case关联告警读事实，不接收调用者任意跨tenant原文 |
| Case可选Router | 与上一行同入口 | `AISOC_INVESTIGATE_USE_ROUTER`决定替代默认编排 | 领域结果、模板MD、Run审计 | 二选一，不是四节点后再跑Router；不由Kafka输入自动选择 |
| 独立full graph | 原Agents服务 `POST /api/v1/agent-runs` | incident_id/tenant_id/alert_summary/raw_alert及原服务认证/目标归属 | Run及graph输出；原服务状态`GET /api/v1/agent-runs/{run_id}` | 服务内部可选入口；不是正式告警投放点，不推荐上游为每条告警额外调用 |

Case创建：`POST /api/v1/cases`，至少title，关联传canonical UUID数组`alert_ids`；新增关联是`POST /cases/{case_id}/alerts`。已有告警、Fusion Incident、自动Run都不会自动保证存在Case，不能拿Incident ID拼Case路径。

## 2. 自动路径每一步的合同

| 阶段 | 实际输入 | 阶段输出内容 | 输出存放/读取 |
| --- | --- | --- | --- |
| 认领 | fused正文、canonical/tenant、持久投递状态 | Run开始意图、原输入身份；模型尚未执行 | `investigation_runs`、普通live认领事件seq=-1；初次events查询不带since才能看到-1 |
| 业务规则/上下文准备 | 告警、租户规则、组织记忆、技能、KB、近期分析员处置、身份资料 | 抑制决定或候选事实；各读取状态和采用材料 | 原抑制路径有其持久回执；正常分诊读取回执/工件与triage结果关联，不将所有消息都写成已经调用五类资料 |
| 规则或模型分诊 | 实际可用告警+已采用上下文；模型分支实际prompt | verdict、confidence、rationale、findings、proposed_actions、auto_closed；可能不调用模型 | `kind=triage_verdict`通常seq=1；真实首次模型材料可见`llm_call`通常seq=0及prompt/response工件 |
| 告警状态投影 | 首次分诊结果及原关闭保护 | disposition、ai_score、ai_summary、ai_recommendations；关闭时resolved/resolved_at，否则通常保留开放/triaged | PG alerts、`GET /api/v1/alerts/{id}`；review-only/shadow等不等价于live改告警 |
| 自动升级准备 | 未关闭且允许升级的首次结果，原告警/ContextBundle | 进入同Run的post-triage graph | 首次结论不被graph结果覆盖；没有升级事件时不能假定已调查 |
| graph: triage | 当前state、实体/技术标签及已有资料 | 原规则分级/映射、findings等state增量 | graph_step记录节点完成；完整聚合state在最终graph_result工件，不能把graph_step摘要当全量节点快照 |
| graph: enrichment | IOC、内部/外部可用增强后端 | ioc_enrichments、threat_intel/mitre_mappings等；失败/缺源状态 | graph_step、最终state；provider未配不等于已核验安全 |
| graph: investigation / Deep | 当前证据、策略/工具列表、预算；每轮模型可选择工具 | investigation_depth、查询/工具返回、findings/narrative、候选verdict/动作；可能truncated/error/预算停 | graph模型/工具可见材料在`graph_llm_exchanges`、graph_result及对应事件，按实际存在读取 |
| graph: attack_path | 已有关系图及当前调查state | 路径/影响候选、findings、评分/建议等，具体按state | graph_step + graph_result；可达候选不是确认影响，知识映射不是行为因果 |
| graph持久交付 | 最终或中断state | graph_result事件payload、JSON state、report_md/report_html、graph_usage | `investigation_events`、`investigation_artifacts`；部分结果保留partial，不把Run completed当后续完整 |

自动升级从`triage`开始，**不会重跑首次auto_triage**；独立full graph才包含该入口节点。Deep是调查节点内部多轮工具流程，不是每条消息必走所有工具，也没有独立“/deep”启动接口。[graph拓扑](../../../services/agents/app/graph/workflow.py)、[worker](../../../services/agents/app/workers/fused_alert_consumer.py)

普通live分诊先持久认领；费用/预算hold和unknown有其保护。原policy/memory抑制、direct/replay不是同一确认合同，不将普通live的每个seq约定套给所有分支。

### Deep单轮应该读取什么

一次模型回复可能包含最终文字，也可能包含`tool_calls`。真正工具执行必须有工具名称、实际参数、返回/错误以及下一轮采用的ToolMessage记录；工具名称列表或报告自称“已查询”不足以证明执行。后端从交换材料核对`prompt/response/tool_calls/tool results`及关联事件；旧Run不保证每项工具完整原文都存在，缺记录应标为不可回查，不能补造。

工具的HTTP目标和输入参数见[工具目录](../../architecture/investigation-tool-catalog.md)、[HTTP检索合同](../../architecture/third-party-search-contract.md)。`available=false`、成功零行、查询失败、截断分别呈现；不由200或空rows自动得到“无异常”。

## 3. 人工默认四节点：逐步输入输出

Case启动API投影最多3条关联告警到`raw_alert.alerts`，内部其他材料读取可能另有上限。这个嵌套数组不是每个消费者都会自动flatten，也不代表所有Case告警均进入了每个prompt。

| 节点 | 输入内容 | 结构输出字段 | 读取/持久化注意 |
| --- | --- | --- | --- |
| ReconAgent | 告警摘要/有界结构、IOC增强、ContextBundle、同Run知识 | `recon.iocs/related_incidents/threat_actors/attack_surface/mitre_techniques/summary` | recon、tool_call、llm_prompt/response等实际审计；完整recon state不保证独立永久工件 |
| ForensicAgent | 已有告警、Recon输出、上下文和知识 | `forensic.timeline[{ts,event,src}]/artefacts/root_cause_hypothesis/blast_radius/confidence/summary/groundedness` | 假设/影响范围是模型分析，不是原始事实；失败有兜底，需同时看error/审计 |
| ResponderAgent | Recon/Forensic及支持资料 | `responder.recommended_actions/containment_steps/eradication_steps/recovery_steps/estimated_effort_hours/risk_level/dry_run/summary` | 默认dry_run=true；建议未证明调用厂商或执行成功 |
| ReportWriterAgent | 三阶段分析、知识引用和原输入 | `report_md`，部分路径HTML视图 | MD作为`kind=report_md`持久工件；报告成功不追认事实正确 |

运行期Agents/Case代理状态可含recon/forensic/responder。冷读从ledger恢复主要是Run、审计、已存graph_result和报告，并不保证恢复完整四节点state。因此对永久后端集成，使用事件/工件/MD；若业务必须逐节点完整JSON快照，这是明确的新合同需求，当前不能假称已有。字段定义见[InvestigatorState](../../../services/agents/app/investigator/state.py)、[编排持久化](../../../services/agents/app/investigator/orchestrator.py)、[冷读层](../../../services/agents/app/api/investigation_access.py)。

Router领域分支与此表不同：按领域走一次领域分析，响应摘要及模板报告不等价于完整Forensic/Responder；不能把Router也解析为四套同名结果。

## 4. API读取顺序与样例

以下路径相对 **API服务** 的`/api/v1`，使用受控Bearer。外部查询常需`alerts:read/cases:read`；Case启动需`cases:write`。Case部分读取路由当前为已认证同tenant归属检查，不宣称它们均显式检查cases:read。API身份与内部Agents服务token不是同一合同。

| 步骤 | 请求 | 返回/用途 |
| --- | --- | --- |
| 查告警 | `GET /alerts/{canonical_alert_id}` | Alert详情、原文、disposition/状态；DB列不保证逐列同名出现在API响应 |
| 找自动分诊Run | `GET /investigations?case_id={canonical_alert_id}&limit=20` | 普通Kafka triage当前将关联字符串记为canonical Alert ID；独立graph按其Incident/已返回run_id查，不能当通用全入口过滤 |
| 找人工Run | `GET /investigations?case_id={case_uuid}&limit=20` | Case调查的ledger Run列表；也有Case下列表接口，返回封装不同 |
| Run摘要 | `GET /investigations/{run_id}` | id、status、error、tokens、费用及event/artifact数量；不是完整state接口 |
| 首次拉所有步骤 | `GET /investigations/{run_id}/events?limit=200` | items/total/since/next_seq，包含seq=-1（若有） |
| 增量拉步骤 | `GET /investigations/{run_id}/events?since={next_seq}&limit=200` | 严格`seq > since`，默认200/最大1000；since=-1会跳过-1本身 |
| 解释某步 | `GET /investigations/{run_id}/explain?step=1` | 前后步骤、focus与该事件绑定工件；seq1是普通triage结论，不是所有编排固定结论位置 |
| 工件列表 | `GET /investigations/{run_id}/artifacts` | id/kind/sha256/size_bytes/event_id/created_at |
| 工件正文 | `GET /investigations/{run_id}/artifacts/{artifact_id}` | content或blob_ref；graph_result的content需要再做JSON解析；report_md是Markdown字符串 |
| Case状态/结果代理 | `GET /cases/{case_id}/investigations/{run_id}` | 核Case和Run归属后代理Agents状态；与ledger摘要JSON不同 |
| Case Markdown | `GET /cases/{case_id}/investigations/{run_id}/report.md` | 直接Markdown文本；进行中或未生成时按状态返回非200 |

**API服务不提供这里可保证的`GET /investigations/{run_id}/report.md`路由。** 这个直接report路由属于Agents服务。无Case的自动Run在API层按“列工件→找report_md→读content”取报告，不要拼Case URL。后端需要统一下载URL时可在自己的后端封装现有工件查询，不凭文档虚构本服务路由。

只读请求示例（示例未执行，先配置API通道/地址及发放的token）：

```sh
curl --fail-with-body -H "Authorization: Bearer $STINGAISOC_API_TOKEN" \
  "$STINGAISOC_API_BASE_URL/api/v1/investigations/$RUN_ID/events?limit=200"
curl --fail-with-body -H "Authorization: Bearer $STINGAISOC_API_TOKEN" \
  "$STINGAISOC_API_BASE_URL/api/v1/investigations/$RUN_ID/artifacts"
# 选定kind=report_md或graph_result对应的ARTIFACT_ID后
curl --fail-with-body -H "Authorization: Bearer $STINGAISOC_API_TOKEN" \
  "$STINGAISOC_API_BASE_URL/api/v1/investigations/$RUN_ID/artifacts/$ARTIFACT_ID"
```

事件页为空时保留上次游标，不用`next_seq=null`清空已有位置。按`(run_id,seq)`去重，工件按id/kind/hash保留版本；选择最新graph_result/report时核created_at/id及关联事件，不把不同次结果随意拼成一份结论。[API账本路由](../../../services/api/app/api/v1/endpoints/investigations.py)、[Case代理路由](../../../services/api/app/api/v1/endpoints/cases.py)

### 结论字段的三层含义

- **首次分诊**：triage_verdict.payload的verdict/confidence/rationale/findings/auto_closed，是首次处理决定。review-only可能有策略哨兵值，按原admission/recovery字段解释，不能把数字0一律解释成模型测得0置信。
- **后续graph**：graph_result事件的`payload.completion=completed|partial`、status/verdict/result_sha256；同名工件中读findings/confidence/verdict/investigation_depth等实际state。`graph_usage`是后续图用量，Run总量可能另含首次分诊，不重复相加。
- **业务落地**：Alert disposition/status/resolved_at、Case status、报告中的建议分别表达；Run completed可能只说明首次分诊已落账，不能单独解释成后续graph完整、事实已确认或业务已结案。

[示例payload](examples/result-events.json)只说明结构，不是实际Run、真实模型或质量通过证明。当前没有独立统一`/conclusion`接口，也没有全编排统一结构化“证据→finding→结论”输出合同；四个共享合同仍是[建议](../../architecture/investigation-product-engineering-roadmap-20261022.md)。

本轮真实例子另确认：外层graph使用低seq、工具使用10000+，高seq工具可先入库、低seq graph_result后入库。`since`不是严格写入时间游标，运行中只追max(seq)可能漏后写的低seq。取得调查交付后须从不带since的首页重新分页补齐，按(run_id,seq)去重；首屏不传since才能包含-1。完整读取与留存边界见[数据盘点](page-data-mapping.md#5-给后端的读取顺序与分页约束)。

## 5. 链图及版本边界

| 能力 | 数据入口/输出 | 本版发布状态 |
| --- | --- | --- |
| 原Case Attack Path | API `GET /graph/attack-path/{case_id}`；已有Neo4j关系/PG回退 | full已有基本实证，PG回退2节点1关系不等于行为链 |
| 原Case相关告警链 | API `GET /cases/{case_id}/attack-chain?window=24h`；按PG已有实体/时间排序 | 原有能力，与Fusion内部链不是一个对象 |
| 新Alert链、统一调查上下文GET/POST | `/alerts/{id}/attack-chain`、`/graph/investigation-context`；可信PG投影Neo4j | 已随v1.0.0发布；新Run取得PG投影success、Alert图成功及同Run工件 |
| Kafka分诊前统一写图、Bundle/Router/Deep新摘要与工件 | Agents消费fused之后、triage之前；图和Run工件 | 已随v1.0.0常驻生效，新Run有prepare成功及三个链图工件；不代表内容质量通过 |
| 旧C2预算/结论等质量修正 | 工作区另有尚未终审/未入候选的差异 | 不因候选镜像存在而认定包含全部修正 |

## 6. 常用支撑读取入口

| 功能 | 输入点 | 输出点/权限 |
| --- | --- | --- |
| 告警资产/权限/漏洞/先前告警 | `GET /alerts/{id}/processing-context` | 每维matched/no_match/not_requested/unavailable；alerts:read |
| 历史事件SQL | `POST /lake/sql`，body `{sql,row_cap,timeout_seconds}`；`GET /lake/schema` | columns/rows/row_count等；lake:query / lake:read_schema |
| 现有调查工具 | `GET /graph/investigate/tools`、`POST /graph/investigate/query` | tool/available/rows/row_count/reason；query需lake:query |
| PG知识读取 | `/kb`的检索/读取路由 | 文档块及引用；knowledge_base:read；`POST /kb/query`可按请求触发LLM，不把它当无副作用探活 |
| IOC | `/threat-intel/iocs`等tenant接口，或受控TI/enrichment服务 | 命中/来源/时间；threat_intel:read；历史匹配不自动升级证据强度 |
| UEBA | 内部UEBA认证API，按tenant/entity读取 | feature_stats、window、异常；token及X-AiSOC-Tenant-ID；不把最近50条匹配限制隐去 |

process_tree/mailbox_activity/oauth_grants/persistence等现有工具有明确not_ingested/unavailable分支；本包不把工具名当成已经具备相应原始数据。[full现状](../../operations/full-support-migration.md)
