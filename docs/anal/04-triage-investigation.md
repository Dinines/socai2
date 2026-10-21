# 04 自动分诊、调查编排与 Agent（M04 / M05）

> 用途：固定上游源码与历史证据分析（2026-10-20对齐）。本轮负责告警驱动的分诊与调查服务；不同入口分别验收，既有分析不等于已运行或已通过。 当前职责见[范围](../operations/alert-processing-scope.md)，阶段退出见[路线](../operations/service-roadmap.md)，执行批次见[依赖计划](../operations/dependency-migration-plan.md)。

返回[总入口](README.md)。本章按真实入口拆解，而不是按“Agent 名称”罗列能力。

<a id="m04"></a>

## 1. 自动分诊消费者

入口：[fused_alert_consumer.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/agents/app/workers/fused_alert_consumer.py)：`build_state`、`FusedAlertTriageWorker.triage`、`_process_with_retry`、`_maybe_escalate`。

### 输入与身份

`build_state` 要求消息包含 dict 类型 `alert`；从 envelope/alert 解析 tenant、Incident、canonical Alert 行 ID。标题与确定性 narrative 构成 summary；从 alert 提取实体、规则、来源连接器、事件 ID、raw_event 和融合置信度。

```text
run_id = UUID5(namespace, alert_row_id + ':' + WORKFLOW_VERSION)
WORKFLOW_VERSION = auto-triage-v1
```

这不是 `tenant + target_type + target_id + target_version + command` 的目标产品合同。上游 canonical Alert ID 虽通常包含 tenant，不能据此替代显式版本、授权和消息幂等检查。人工重新调查也不应该被永久折叠进相同自动分诊 Run。

### 功能顺序

| 阶段 | 输入 | 处理与输出 |
| --- | --- | --- |
| 业务规则 | 租户规则与融合告警 | suppress 可直接停止分诊；严重度、路由、标签规则修改后续视图 |
| live/shadow 选择 | tenant、告警类别、指纹 | 每条告警选择 writer；shadow 不应污染 live 结果 |
| 可信历史抑制 | evidence fingerprint、prior | 按开关与信任条件处理重复低风险结果，减少模型调用 |
| CostGovernor | tenant、指纹、预算和缓存 | 使用缓存、模型或确定性路径；保留实际 tier |
| 上下文 | 组织记忆、租户 skill、runbook、历史 disposition、身份 | 通过 reader 获取；不同 replay/freeze 路径可绑定不同 reader |
| 分诊 | 受控输入、模型/确定性规则 | verdict、confidence、findings、confidence_basis |
| 校验与落库 | 模型结果和原材料 | 解析、groundedness、置信度约束；writer/ledger 写结果 |
| 后续处理 | 分诊结果和开关 | 可升级 graph、触发 Playbook、提出审批、写回源系统等 |

`response_dispatched=False` 只说明这份分诊摘要没有直接报告响应动作，不能推断整个处理完全无副作用：可启用自动关闭、Playbook、记忆写回和源系统 writeback。审查实际开关和调用，比只读函数 docstring 更可靠。

### 分类与失败

分类包括 `true_positive`、`false_positive`、`benign`、`benign_true_positive`、`needs_review` 等规范词汇；解析层会兼容部分同义表达。合法扫描/授权测试是“真实触发但合法”，不应污染误报统计。

模型/解析失败可进入确定性分诊；高/严重告警有防止失败后误自动关闭的处理。最终结果必须保留 `tier`、fallback 原因和所用依据，不能把规则结论标作模型判断。

### Kafka 与重试边界

`_process_with_retry` 对处理/持久化异常进行有限重试，最终调用 DLQ。**当前 `_send_to_dlq` 在 producer 不可用或发送失败时记录并返回，调用方仍可能继续提交；发送只等待 `send` 的这一层。** 因此不能写成“DLQ 已可靠确认后才 commit”。

另一个边界：PG 中 `ON CONFLICT DO NOTHING` 可去掉某些重复行，不代表模型网络调用、工具或响应副作用 exactly-once。移植时采用现有 stingAISOC Inbox/Decision/Run 身份与提交规则，不复制整套旧循环。

<a id="m05"></a>

## 2. 三种调查编排，四类入口

| 入口/编排 | 状态模型 | 正常步骤 | 特点 |
| --- | --- | --- | --- |
| 自动升级 graph | `InvestigationState` | Triage → Enrichment → Investigation → Attack Path | 自动分诊已有结果，跳过 Auto-Triage；由 writer 与配置门禁控制 |
| 手动 full graph `/agent-runs` | `InvestigationState` | Auto-Triage → 条件终止或上述后续步骤 | 是独立入口，不应当成 Case UI 唯一路径 |
| 默认 Case Investigator | `InvestigatorState` | Recon → Forensic → Responder → Report Writer | Case `/investigate` 默认使用；结构结果、报告和审计日志 |
| Router | `InvestigationState`，另有 Investigator 兼容输出 | 信号分类、选领域 Agent、顺序/并行执行、汇合与响应/报告 | Case `/triage` 使用；Case `/investigate` 可按配置切换 |

源码：[workflow.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/agents/app/graph/workflow.py)、[runner.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/agents/app/graph/runner.py)、[api/router.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/agents/app/api/router.py)、[orchestrator.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/agents/app/investigator/orchestrator.py)、[router.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/agents/app/orchestrator/router.py)、[triage.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/agents/app/api/triage.py)。

Auto-Triage 失败时 full graph 会继续升级而不是以空 verdict 完成。graph 的边结构并不表示每个阶段都有完整业务恢复能力。

## 3. 通用调查状态与节点合同

`InvestigationState` 入口：[state.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/agents/app/models/state.py)。

| 字段组 | 代表内容 | 所有者与作用 |
| --- | --- | --- |
| 标识与任务 | run_id、incident_id、tenant_id、alert_summary、raw_alert | 入口构造；不要从字段名自动推断它一定是持久 Incident |
| 上下文 | context_bundle、organisation_memory、tenant_skill、knowledge_base、identity_context | reader/provider 构造；记录真实来源与覆盖 |
| 发现 | findings、IOC enrichments、threat_intel、mitre_mappings | 节点累积；字符串发现未必具备稳定引用 |
| 结论 | verdict、confidence、confidence_basis、groundedness | 分诊与验证；相似度、模型置信度、依据校验分开 |
| 动作 | proposed_actions、executed_actions | 建议与执行记录分开；仅有前者不证明执行 |
| 执行 | status、iteration_count、max_iterations、error、timestamps | 编排层推进；不等同 Case 状态 |
| 模型记录 | messages、llm_exchanges | 可追溯辅助；不能据字段存在保证所有路径完整落库 |

| graph 节点 | 输入 | 主要处理 | 输出与限制 |
| --- | --- | --- | --- |
| Auto-Triage | 告警和上下文 | 模型分类、解析、置信度与关闭资格 | verdict/status；高置信度可提前结束 |
| Triage | 告警摘要/实体 | 关键词/风险启发式、IOC、技术映射、初始建议 | 严重度发现和提案；该节点并非另一轮必然 LLM |
| Enrichment | IOC 和状态 | 调用增强工具并汇总 | enrichments/情报；需核对依赖失败与无命中 |
| Investigation | 告警、已有发现、工具 | 调查分析与受限工具循环 | findings、判断、建议；可用工具决定事实覆盖 |
| Attack Path | 实体与图上下文 | 图关系/影响范围分析 | 路径与范围判断；无图数据不能宣称真实攻击链 |

节点文件分别在 [agents 目录](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/agents/app/agents)。Prompt、工具名和模块名称只说明意图，必须沿具体节点实际调用验证。

## 4. Case Investigator 的逐阶段输入输出

模型：[investigator/state.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/agents/app/investigator/state.py)。

| 阶段 | 输入与实现 | 结构输出 | 校验与业务限制 |
| --- | --- | --- | --- |
| Recon | 摘要、raw_alert、预取上下文；LLM + 启发式提取 IOC，调用 `enrich_ioc` | `ReconFindings`：IOCs、相关事件、actor、attack_surface、MITRE、summary | IOC/技术可能来自模型或关键词，不等同来源已经确认 |
| Forensic | 原始告警视图、Recon、增强缓存 | `ForensicFindings`：timeline、artefacts、root_cause_hypothesis、blast_radius、confidence | 零证据时抑制 artefacts、降低置信度并标 inconclusive；artefact 引用标为 hypothesis |
| Responder | 前序发现和取证结论 | `ResponderPlan`：recommended_actions、containment/eradication/recovery、risk、effort | `dry_run=True`；这是计划，不是厂商执行回执 |
| Report Writer | Case、前三阶段结构结果与依据 | report_md、report_html、审计日志 | 有模型/降级报告路径；报告生成成功不等于结论完整 |

源码：[recon_agent.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/agents/app/investigator/recon_agent.py)、[forensic_agent.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/agents/app/investigator/forensic_agent.py)、[responder_agent.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/agents/app/investigator/responder_agent.py)、[report_writer_agent.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/agents/app/investigator/report_writer_agent.py)。

重要的源码风险：`enrich_ioc` 失败返回非空 error dict；Recon 以 `bool(result)` 记录 success，并将该字典放入 enrichment_cache；Forensic 的部分证据可用判断只看缓存非空。这意味着“只有增强错误”也可能被误算为有增强材料。**这是静态可定位的语义风险，尚未以实际 Run 复现；不能据此断言现有某份报告已经造假。** 移植应以明确 provider status 与有效 observation 列表判断证据。

## 5. Router 的领域协作

`classify_signals` 通过关键词和 raw keys 选择 `phishing/identity/cloud/insider`，不额外依赖 LLM 路由；完全无匹配时选择四种能力。拓扑可顺序或并行，分支结果经 `_join_states` 汇合。

这套默认“无匹配全跑”是上游策略，不应自动成为 stingAISOC 的预算和调查义务。移植时按当前问题、数据能力和授权决定领域任务；不要为复用 Router 建第二套状态、重复分诊或固定跑全部 Agent。

领域 Agent 的名字不证明有相应 IdP、云审计或邮件数据；需以绑定工具、tenant 后端、查询参数及实际返回判断。

graph Investigation 节点还实际调用了 Deep 工具循环；这不是 Case 默认四阶段统一自动追加的节点。Deep 的 registry、客户工具、MCP、coverage 和 trace 见 [M20](11-detection-hunting-feedback.md#m20)。区分“现有材料总结”和“模型实际发起补充查询”，是后续移植调查能力的重要验收点。

## 6. Prompt、工具和结果校验

- Factory 选择角色模型；`safe_ainvoke`/contract 与具体节点处理受控输入。增加节点时不能只调用 `make_chat_model` 就宣称所有 guard 生效。
- `prompt_sanitizer`、不可信数据封装和知识块过滤降低注入影响；关键词 guard 不是安全保证，工具授权必须在服务端。
- Groundedness 检查某些具体指标是否在输入材料中出现，能发现一类凭空指标；不是对时间线、根因、竞争解释或完整业务正确性的全面证明。
- Prompt/response、工具参数/结果 hash 与可见输出用于回放。移植到 stingAISOC 时按其 Artifact、Call、Step/Attempt 合同保存，不记录隐藏推理或凭据。

## 7. 预算、执行状态与持久化

默认 graph budget 为 120 秒、20,000 tokens、`max_tool_calls=8`；这些是源码默认，不是本次部署能力上限。`_budget_exhausted` 对后者实际比较 `CostTracker.calls_made` 并称 model-call budget；没有 tracker 时该检查放行。**不能把配置名解释成对所有 HTTP 工具调用的严格计数。**

Case API 采用 wall-clock timeout，并在 `_runs` 维护实时状态；调查账本另写 PG。Ledger 无 DATABASE_URL 时可 no-op，部分失败记录路径 fail-soft，自动分诊持久错误还有特定异常处理。不能统一概括为“所有路径强持久”。

`start_run`、`record_event` 的冲突忽略只能避免某些重复插入，不能证明 checkpoint 恢复、同一节点只执行一次或迟到结果不可覆盖。复杂接管不作为当前默认移植目标，但必要调用持久记录、unknown 不重发、冻结结果边界仍须保留。

## 8. 测试入口与采用建议

| 测试文件 | 主要合同 | 证据级别 |
| --- | --- | --- |
| `test_auto_triage_dispositions.py` | 授权扫描/测试、真误报、恶意、解析与超时 | 模型替身；非真实分类质量 |
| `test_auto_triage_injection.py`、`test_triage_structured_output.py` | 注入输入、结构化解析 | 合同/离线 |
| `test_auto_triage_ledger_records_the_prompt.py` | 实际送入输入的记录链 | 需结合 fixture 判断是否真 PG |
| `test_graph_runner.py` | graph 运行、预算与账本边界 | 本轮未运行 |
| `test_investigate_router_flag.py`、`test_orchestrator_router_stream.py` | 入口选编排器、流事件 | 替身不能证明领域数据可用 |
| `test_investigator_groundedness.py`、`test_investigator_completion_bound.py` | 依据约束和完成时间边界 | 不替代调查业务质量 |

优先采用逐阶段职责、真实输入进入 Prompt、无证据时诚实输出、结构结果与调用记录；将它们接入 stingAISOC 已确认的 context/evidence → triage/questions → controlled collection/domain analysis → validation/result。多假设、反证、未知和必要补查要按目标设计落实，不能以参考四个 Agent 名称代替完整调查合同。
