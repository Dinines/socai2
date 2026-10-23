# 告警与调查 V1：页面取数映射、SQL与HTTP附件

[页面展示建议](page-elements.md) · [当前数据库设计与字段字典](table-fields.md) · [完整审计](ui-functional-data-audit.md)

本篇连接“产品希望展示什么”和“当前数据如何读取”。它保留原90项字段映射、六组SQL例子和已有HTTP接口，不另定义页面需求或数据库结构。表与字段含义以数据库字典为准，A01—A40/I01—I50仍与页面建议和七图一致。

数据库：PostgreSQL `192.168.1.21:5432 / aisoc / public`；凭据与租户设置见[数据库字典](table-fields.md#database-connection)和[连接配置](configuration.md)。例子是既有合成告警的持久结果，版本/空值/本地未部署边界保留。本轮文档拆分没有重跑SQL、HTTP或模型。

<a id="mapping"></a>

## 1. 按功能从数据库取数，并给出实例

第1.1—1.2节逐项对应页面字段；第1.3节说明需要聚合而不是直接读列的信息；第1.4节用已经处理过的两条合成告警演示取数。先用租户和Alert/Run定位，再读取具体字段，避免将不同Run的资料拼在一起。

### 1.1 告警功能与字段取数映射

为避免重复长路径，定义三个读取表达式（只是本文简写，不是新列或视图）：

```sql
-- a 表示 public.alerts
-- F：来源身份、IOC检索、分组及首次交付材料
a.enrichment_data -> 'socai2_fusion'
-- S：首次融合时保存的来源告警快照
a.enrichment_data #> '{socai2_fusion,delivery_snapshot,fused,alert}'
-- T：本Run首次分诊事件
-- public.investigation_events WHERE kind='triage_verdict'，读取 payload
```

下表 ID 对应[页面建议第1.2—1.3节](page-elements.md)的 A01—A40；同一信息在列表/详情重复时合并列出。

| 页面信息 / ID | 表和具体字段或 JSON 路径 | 当前数据说明 |
| --- | --- | --- |
| 标题、来源摘要、告警ID A01/A06/A10/A22 | `alerts.title / description / id` | 两例实值；description 是来源描述 |
| 来源系统 A02/A13 | `alerts.enrichment_data #>> '{socai2_fusion,identity,source}'` | 两例 `v1-functional-test`；**没有 alerts.source 列** |
| 接入类型、来源告警/连接器ID A13/A14 | `alerts.connector_type`；F.`identity.source_alert_id/connector_id`；另有 `alerts.connector_id` 列 | 来源告警ID有值；本例接入类型/连接器ID为空 |
| 发生、入库、首次/最近出现、更新时间 A03/A17—A20 | `alerts.event_time / created_at / first_seen / last_seen / updated_at` | 均有值；不要混用时间语义；`first_seen_at` 是另一个首次人工认领/确认时间字段（当前claim路径写入，非页面查看或自动分诊时间） |
| 解决时间 A21 | `alerts.resolved_at` | 自动关闭例有值；未关闭例为空 |
| 等级、分诊结论、业务状态 A04/A07/A08 | `alerts.severity / disposition / status` | 分别展示；首次结论原件再查 T.`verdict` |
| AI分诊置信度、理由 A11/A33/A34 | `alerts.ai_score / ai_summary`；准确阶段字段 T.`confidence/rationale/verdict`，时间为事件 `ts` | 95%/85%为分诊置信度；理由优先结构T，不解析拼接摘要 |
| 负责人 A12 | `alerts.assigned_to_id / assigned_at` | 两例均未分配；姓名需接人员目录，本批未核人员表映射 |
| 来源事件引用 A15 | `alerts.source_event_ids / external_id` | 引用ID不是事件正文；不能把数组长度当发生次数 |
| 检测规则 A16 | S.`rule_id/rule_name`；数据库另有 `alerts.rule_id/rule_name` | 16:42复核两例主表及S的rule_id有值，分别为v1-functional-rule-1/-2；rule_name均空，不补造名称 |
| 分类、标签 A23 | `alerts.category / tags`；首次来源标签另在S.`tags` | 本例当前tags空而S.tags含synthetic，两个口径不能混用 |
| 主机、用户、IP、实体 A05/A24 | `alerts.affected_hosts / affected_users / affected_ips / entities / iocs` | 有值；entities/iocs保留type/value；页面group/label/pivot是组装信息 |
| 源IP、目的IP A25 | S.`src_ip/dst_ip` | 两例源IP有值，调查例目的IP有值、关闭例目的IP为空；不要从affected_ips顺序推断源/目的 |
| 进程、命令、端口及其他扩展 A26/A27 | `alerts.raw_event ->> 'process_name'/'command_line'/'destination_port'`；S.`domain/url/file_hash` | 两例进程/命令有值；仅调查例端口443，关闭例无端口键；两例domain/url/file_hash均空。扩展不是全部来源统一必填字段 |
| MITRE战术/技术 A28 | `alerts.mitre_tactics / mitre_techniques` | 技术ID是映射，不代表完整攻击链 |
| 原始数据 A29 | `alerts.raw_event`；完整首次来源快照另查S | raw_event不是整个Kafka信封 |
| Fusion分组、Case A30 | F.`incident_id`；`alerts.case_id` | 两例有Fusion Incident，无Case |
| 融合说明/评分因子 A31/A32 | `alerts.narrative / confidence / confidence_label / confidence_rationale` | 与AI置信度分开；直查旧行narrative空时不触发HTTP的懒生成 |
| 是否自动关闭 A35 | T.`auto_closed` + `alerts.status/resolved_at` | 首次处理事实与当前业务状态联合看 |
| 分诊发现/建议 A36 | T.`findings/proposed_actions`；`alerts.ai_recommendations` | 本例结构建议为空；HTTP recommended_actions是归一化输出，无同名列 |
| IOC查询/覆盖 A37 | F.`ioc_lookup`，内含`indicators/status/scope/matches/checked_at/external_status` | no_match仅适用于已查来源；未配置外部情报不等于安全 |
| 调查入口/最新状态 A09 | runs + events + artifacts，见第1.2节 | 无独立latest_investigation列，接入方按Run关联后聚合 |
| 资产/身份/漏洞/历史告警 A38 | `assets`、`alert_asset_correlations`、`identity_privilege`、`asset_vulnerabilities`、历史`alerts` | 连接键和字段见[数据库字典](table-fields.md)；本租户样例未匹配这些补充资料 |
| 当前查询范围、新鲜度、外部历史/UEBA状态 A39/A40 | HTTP `processing-context` 执行时生成；没有同名持久结果表 | 直查方可按自己的查询范围展示；要复现原返回语义可参考原服务函数，不能SELECT一个不存在的processing_context表 |

告警列表排序、关键词、来源、时间、对象过滤可以由接入方直接在 `alerts` 查询上实现。现有 HTTP 的 search 未生效、列表缺source等限制保留记录，**不阻止本次按表直查**。统计要使用与列表一致的租户及过滤条件。

### 1.2 调查功能与字段取数映射

约定 `r=investigation_runs`、`e=investigation_events`、`k=investigation_artifacts`；`G` 为同Run `kind='graph_result'` 工件的 `content::jsonb`；`GE` 为 `kind='graph_result'` **事件**的 `payload`。不要把TEXT工件当JSONB列直接用箭头，也不要把Markdown转成JSON。

| 页面信息 / ID | 表和具体字段 / 取法 | 当前数据说明 |
| --- | --- | --- |
| 标题、Run/目标、等级/来源 I01/I02/I04 | `r.id/case_id/raw_alert/alert_summary`；关联当前`alerts`或已确认的`aisoc_cases` | 显示标题可取目标title；不存在统一的r.title/target_type列 |
| 触发方式 I03 | e的`triage_started/triage_verdict`及T.`recovery`，结合已知入口 | 自动两例已确认；无统一trigger_type列，其他来源不猜 |
| 运行状态/时间/耗时 I05/I08/I09 | `r.status/error/started_at/completed_at`；耗时为时间差 | completed只表示运行结束；Run耗时包含首次分诊 |
| 调查完成度 I06/I18/I42 | GE.`completion`；G.`budget_exhausted/budget_exhausted_reason/error` | **完成度在事件payload**，本例G本身没有completion键 |
| 调查结论/置信度 I07/I15 | G.`verdict/confidence/confidence_basis` | partial例needs_review/0.19，不覆盖T的0.85 |
| 报告是否可读 I10 | 同Run k.`kind='report_md'`，检查`content/blob_ref` | 有目录项不保证正文已可读取；两例中仅调查例有MD |
| 调查负责人/人工复核 I11 | 当前无统一Run级责任人/复核持久字段 | 不能用Case负责人或告警状态冒充人工复核结论 |
| 当次告警/对象/查询范围 I12—I14 | G.`raw_alert`；e工具调用的`payload.args`；G.`context_bundle.attack_context.query_scope` | 用快照区分当前Alert；没有统一所有查询的绝对起止字段 |
| 总摘要/分析记录 I16/I17 | G.`findings`；当前无统一final_summary | findings含过程/判断/错误，不全是已确认事实；depth.narrative本例为工具JSON，不作总摘要 |
| 缺源和停止交接 I19 | G.`investigation_depth.unavailable_data/coverage_notes/truncated`；本地另有`stop_reason/error` | 旧生产和本地新版字段分别处理 |
| 建议/执行动作/根因 I20—I22 | G.`proposed_actions/executed_actions`；根因目前无统一已验证合同 | 本例动作为空；人工阶段状态不保证独立持久化，见第1.3节 |
| 材料目录/正文 I23/I24 | k.`id/kind/created_at/event_id/sha256/size_bytes/content/blob_ref` | content内可有JSON或MD；本次21份正文已核字节/hash |
| 工具调用/旧返回预览 I25/I41 | e中`kind='tool_call'`，`payload.tool/args/result_preview`、`duration_ms` | 旧生产预览约200字符，不是完整返回；本例duration_ms=0为默认/未测，显示“未提供”，不当实测0毫秒。旧payload无统一status，不从预览推导成功 |
| 新版单次工具结果 I26/I27 | k中`kind='tool_result'`的JSON；G.`investigation_depth.tool_trace/ledger_gaps` | **本地已测未发布**；用相同ledger表，没新增tool_results表 |
| IOC增强 I28 | G.`ioc_enrichments` | 值对应各IOC；来源空/engines=0不代表良性 |
| 资料读取/已采用引用 I29/I30 | k中五类`*_read`工件的JSON，具体kind见[数据库字典的JSON与工件说明](table-fields.md#json-contracts) | 本例有回执、无匹配知识；回执不是实时源表内容 |
| 关联图/候选链/Case路径 I31—I35 | k中`alert_graph/attack_chain/attack_path`；G.`context_bundle.attack_context.query_scope/queried_at` | 本次快照已在PG；查看既有调查无需重新连接Neo4j |
| 证据—结论引用 I36 | k.`event_id`仅关联步骤；尚无统一每条结论evidence_ids合同 | 不能把event_id当结论逐项证据关系 |
| 处理步骤/节点 I37/I38 | e.`id/ts/seq/kind/agent/summary/payload`；graph_step的`payload.node` | 按ts展示，seq不是严格写入游标 |
| 模型调用/留存范围 I39/I40 | e中llm_call；k中`llm_prompt/llm_response/graph_llm_exchanges` | 截断和hash按实际记录保留；并非每节点都有完整输入输出 |
| 报告内容/版本/Case报告 I43—I45 | k中`kind='report_md'`的`content`；k.`id/created_at/sha256/size_bytes` | 自动、人工持久报告可走同表；有Case才另外关联Case |
| Token/调用数/费用/模型 I46—I49 | r.`total_tokens`及各费用计数；`aisoc_run_costs`各模型行；e中`graph_usage` | call_count来自用量表；不要把r.iterations当模型次数；unpriced>0不能解释为免费 |
| 推理轮数/查询类别/查询记录数 I50 | G.`investigation_depth.iterations/distinct_pivots/ledger_rows`；或统计工具事件 | 6轮、7类、10条记录各有含义，不叫10条已证实证据 |

### 1.3 需要聚合或当前没有持久字段的信息

| HTTP/页面字段 | 直查时怎么处理 |
| --- | --- |
| `fusion_identity/fusion_ioc_lookup/fusion_incident_id` | 分别从alerts.enrichment_data.socai2_fusion的identity/ioc_lookup/incident_id提取 |
| `related_entities/mini_timeline/recommended_actions` | API组装的展示结构；底层是实体、处理/审计记录、建议资料。第一版可直接展示本文已确认的实体与Run事件，不创建同名表假设 |
| `processing-context.dimensions/query/queried_at/priority/partial` | 查询当场生成；数据源表见[数据库字典](table-fields.md)，评分是程序计算。不能用Alert.priority冒充上下文priority |
| Run的`event_count/artifact_count/model_costs` | 分别聚合events、artifacts、aisoc_run_costs；先各自聚合再关联，避免事件×工件×模型行乘积 |
| `latest_investigation/report_available/target_type/trigger_type` | 页面所需聚合/推导信息；当前无统一同名列。按已确认关联取数，未知就标未知 |
| 人工`recon/forensic/responder`独立卡片 | 主要是运行state；本地有采用样例，但未确认全部阶段结构长期单独落库。永久报告查report_md、步骤查events，不能SELECT不存在的forensic表 |

### 1.4 逐功能查询实例

以下实例使用同一生产租户中既有的两条合成告警，查询结果取自已核验资料。片段使用psql变量；通用数据库客户端请改为驱动的绑定参数。下列六组展示SQL未逐段重跑；16:42审计使用独立只读探针复核原始表值，详见第3章。

```sql
\set tenant_id 'f6a5c700-69b8-44fc-8238-609362fb1a9f'
\set alert_id 'e5f593f0-b328-59c3-8238-379db33d8bfe'
\set run_id 'bdccd907-7f36-558f-8ed4-4be2e417b101'
BEGIN READ ONLY;
SELECT set_config('app.current_tenant_id', :'tenant_id', TRUE);
-- 执行所需SELECT，最后ROLLBACK。
```

#### 1.4.1 功能：展示告警来源、时间、摘要、对象和状态

适用页面：告警列表/详情，A01—A08、A13、A17、A22、A25。

```sql
SELECT a.id, a.title, a.description, a.severity, a.status,
       a.event_time, a.created_at, a.disposition, a.ai_score,
       a.enrichment_data #>> '{socai2_fusion,identity,source}' AS source,
       a.affected_hosts, a.affected_users,
       a.enrichment_data #>> '{socai2_fusion,delivery_snapshot,fused,alert,src_ip}' AS src_ip,
       a.enrichment_data #>> '{socai2_fusion,delivery_snapshot,fused,alert,dst_ip}' AS dst_ip
FROM public.alerts a
WHERE a.tenant_id=:'tenant_id'::uuid AND a.id=:'alert_id'::uuid;
```

实际显示：来源`v1-functional-test`；标题`V1 functional example 2: unfamiliar script with outbound connection`；发生时间`2026-10-22 17:10:17.571282 +08:00`；等级high；业务状态triaged；主机`v1-functional-host-2`；源/目的IP为`192.0.2.82 → 203.0.113.82`。description说明脚本内容、执行结果、授权仍未知，不能将这段来源摘要改写为已确认入侵。

完整告警字段查询见附件 [ui-alert-fields.sql](examples/ui-alert-fields.sql)。顶部统计和分页使用与列表相同的租户/筛选条件；不要只统计已加载一页。

#### 1.4.2 功能：从告警找到调查，并展示Run状态和耗时

适用页面：告警“查看调查”入口、调查列表，A09、I01—I10。

```sql
SELECT r.id AS run_id, r.case_id AS target_id, r.status,
       r.started_at, r.completed_at,
       extract(epoch FROM (r.completed_at-r.started_at)) AS elapsed_seconds,
       r.total_tokens, r.error
FROM public.investigation_runs r
WHERE r.tenant_id=:'tenant_id'::uuid AND r.case_id=:'alert_id'
ORDER BY r.started_at DESC, r.id DESC;
```

本例查到Run `bdccd907-7f36-558f-8ed4-4be2e417b101`，执行状态completed，总耗时约21.86秒，total_tokens=29755。这是已确认的自动Alert路径；人工Case用Case ID查，未知入口先核对目标类型。是否确实进入调查再看下一例的graph事件/工件，不能把所有分诊Run计入调查列表。

#### 1.4.3 功能：分开展示首次分诊、调查完成度和最终调查结论

适用页面：告警AI分诊、调查结论卡，A33—A35、I06/I07/I15/I18。

```sql
-- 首次分诊和调查完成度分别是事件payload，不覆盖成同一个status。
SELECT e.kind, e.ts, e.payload->>'verdict' AS verdict,
       e.payload->>'confidence' AS confidence,
       e.payload->>'rationale' AS rationale,
       e.payload->>'auto_closed' AS auto_closed,
       e.payload->>'completion' AS investigation_completion
FROM public.investigation_events e
WHERE e.tenant_id=:'tenant_id'::uuid AND e.run_id=:'run_id'::uuid
  AND e.kind IN ('triage_verdict','graph_result')
ORDER BY e.ts, e.seq;

-- 调查置信度/停止原因取最终结果工件；不要误取首次分诊置信度。
SELECT k.id AS artifact_id,
       k.content::jsonb->>'verdict' AS investigation_verdict,
       k.content::jsonb->>'confidence' AS investigation_confidence,
       k.content::jsonb->>'budget_exhausted_reason' AS stop_reason,
       k.content::jsonb #> '{investigation_depth,unavailable_data}' AS missing_data
FROM public.investigation_artifacts k
WHERE k.tenant_id=:'tenant_id'::uuid AND k.run_id=:'run_id'::uuid
  AND k.kind='graph_result' AND k.content IS NOT NULL
ORDER BY k.created_at DESC, k.id DESC LIMIT 1;
```

| 页面字段 | 实际值 | 应如何展示 |
| --- | --- | --- |
| 首次分诊结论/置信度 | needs_review / 0.85 | AI首次分诊：待复核，85% |
| Run执行状态 | completed | 执行结束 |
| 调查完成度 | partial | 部分完成 |
| 调查结论/置信度 | needs_review / 0.19 | 调查结论：待复核，19% |
| 停止原因 | token budget exhausted (27697 of 20000) | 保留预算停止说明 |
| 缺失数据 | process_tree、network_connections | 提示本次未能检查对应数据 |

对照自动关闭例：Alert `bc625c39-56af-5403-a378-9bfb99c610d2`、Run `4f5a0a57-050a-57a4-8443-504550fbc5fd`，首次BTP/0.95、auto_closed=true、告警resolved；只有分诊，没有graph结果或Markdown，页面应显示“未启动调查”。

#### 1.4.4 功能：展示/下载Markdown报告

适用页面：调查详情“报告”，I10、I43—I45。

```sql
SELECT k.id AS artifact_id, k.created_at, k.sha256, k.size_bytes,
       k.content, k.blob_ref
FROM public.investigation_artifacts k
WHERE k.tenant_id=:'tenant_id'::uuid AND k.run_id=:'run_id'::uuid
  AND k.kind='report_md'
ORDER BY k.created_at DESC, k.id DESC LIMIT 1;
```

本例报告工件ID `72e0c864-41a0-4096-bfa2-8aa0ebe3a641`，content是Markdown，UTF-8大小6413字节；正文与hash已核对。可以直接渲染或下载content，不需要Case，也不重新生成报告。报告原文含旧status=running等质量问题，页面头部仍按Run状态和graph事件完成度显示；不能悄悄重写旧报告。

#### 1.4.5 功能：查看调查过程、查询记录、知识与图材料

适用页面：调查详情“过程/证据与关联”，I23—I42。

```sql
-- 过程和实际工具调用：包括seq=-1，按处理时间展示。
SELECT e.id, e.ts, e.seq, e.kind, e.agent, e.summary,
       e.payload, e.duration_ms
FROM public.investigation_events e
WHERE e.tenant_id=:'tenant_id'::uuid AND e.run_id=:'run_id'::uuid
ORDER BY e.ts, e.seq, e.id;

-- 材料目录；按artifact_id取正文，或在本SELECT按需加content。
SELECT k.id, k.kind, k.event_id, k.created_at, k.size_bytes,
       k.sha256, k.content IS NOT NULL AS has_inline_content
FROM public.investigation_artifacts k
WHERE k.tenant_id=:'tenant_id'::uuid AND k.run_id=:'run_id'::uuid
ORDER BY k.created_at, k.id;
```

本例18条事件、14份工件；其中10条tool_call有tool/args/result_preview，旧预览约200字符。graph_step只有node，不表示该节点独立完整输入输出可读。常见材料取法和实值如下：

| 功能 | 在工件content解析后取什么 | 本例实值 |
| --- | --- | --- |
| 知识读取 | kind=knowledge_base_read的status、received_count、adopted_count、citations | no_match、0、0、[] |
| 候选告警链 | kind=attack_chain的attack_chain.status/data.chain | empty、[]；entity_graph仍有节点边 |
| Case路径 | kind=attack_path的attack_path.status/error | not_linked、no_linked_case |
| 告警关系图 | kind=alert_graph的alert_graph.data.neighbors | 5个直接邻居 |
| 图可达范围 | 同工件alert_graph.data.blast_radius | 3跳可达6个节点，含起点，共5种类型；不是6受害主机 |
| 当次图查询范围 | kind=graph_result的context_bundle.attack_context.query_scope | projection_alert_limit=50、truncated=false |

需要原文时按 `tenant_id + run_id + artifact_id` 从工件表取content；JSON类型解析，Markdown直接读字符串。本地新版的tool_result也在同一工件表，但这两个旧生产Run没有此新类型，不能指望查出完整单次返回。

#### 1.4.6 功能：展示Token、模型调用数和费用

适用页面：调查详情“运行信息”，I46—I50。

```sql
SELECT c.model, c.resolved_model, c.call_count,
       c.total_prompt_tokens, c.total_completion_tokens,
       c.measured_call_count, c.measured_cost_usd,
       c.estimated_call_count, c.estimated_cost_usd, c.unpriced_call_count
FROM public.aisoc_run_costs c
WHERE c.tenant_id=:'tenant_id' AND c.run_id=:'run_id'
ORDER BY c.model;
```

本例首次分诊2058 tokens/1次调用，后续调查27697 tokens/6次调用，合计29755 tokens/7次；7次均未计价，页面显示“费用未计价”。推理轮数6、查询类别7、工具记录10来自调查结果/事件，不能与调用数混用。费用表已经按模型聚合，不要再JOIN多条事件和工件造成重复求和。

上述片段执行完以`ROLLBACK;`结束只读事务。已有完整样例脚本见 [production-two-examples.sql](examples/production-two-examples.sql)，原9个SELECT实际执行通过；这些新增展示片段按已核字段和实值整理，未逐段执行。16:42独立审计探针的只读结果不能代替这些片段自身的执行验收。

<a id="http"></a>

## 2. 已有 HTTP 后端接口

### 2.1 地址和认证

API在21主机为`http://127.0.0.1:18000`，同项目容器网络为`http://api:8000`。18000只绑定21本机loopback；远端后端通过获授权代理/隧道或同网络访问，不能直接把自己机器的127.0.0.1当21。

查询使用已发放的`Authorization: Bearer <reader>`及`X-AiSOC-Tenant-ID: f6a5c700-69b8-44fc-8238-609362fb1a9f`。已有reader主要用于查询，写操作按各自权限另行接入。凭据交接及详细配置见 [production.md](production.md)、[configuration.md](configuration.md)。下表列完整业务路径。

### 2.2 告警查询接口

| 方法与路径 | 用于哪个功能 | 主要请求参数 | 返回内容 / 当前边界 |
| --- | --- | --- | --- |
| `GET /api/v1/alerts` | 告警列表、统计、分页 | page/page_size；severity/status/category；assigned_to_me；min_confidence/confidence_label；sort | items、total、page、pages、facets；本次200。min_confidence是Fusion评分；search参数当前无效；未实现来源/发生时间/对象筛选 |
| `GET /api/v1/alerts/{alert_id}` | 告警详情 | canonical Alert UUID | title/description/时间/对象/分诊投影/raw_event；另有fusion_identity/fusion_ioc_lookup/fusion_incident_id及展示结构；本次200 |
| `GET /api/v1/alerts/{alert_id}/processing-context` | 当前资料覆盖/补充上下文 | alert_id | dimensions、query、queried_at、priority、partial等；动态查询视图。本次200，但样例大多no_match/not_configured |
| `GET /api/v1/alerts/{alert_id}/attack-chain?window=24h` | 当前候选告警链 | alert_id、window | chain、entity_graph、generated_at等；本次200，chain为空 |
| `GET /api/v1/graph/investigation-context?alert_id={alert_id}&window=24h` | 当前图资料综合查询 | alert_id、window | attack_chain/attack_path/alert_graph、query_scope、queried_at；本次200。回看历史调查优先用该Run工件 |

列表page_size默认25、最大200；`sort=priority`实际按严重程度再created_at，`sort=newest`按created_at，均不是event_time排序。source只在详情的fusion_identity中，当前列表不带；直查数据库不受该返回形状限制。

### 2.3 调查、步骤、工件和报告查询接口

| 方法与路径 | 用于哪个功能 | 参数/返回 | 验证边界 |
| --- | --- | --- | --- |
| `GET /api/v1/investigations` | 调查列表/目标运行历史 | case_id（目标字符串）、status、limit；返回Run数组 | 本次200；默认50、最大200，仅最近N条，无全量总数/游标，不能按partial过滤 |
| `GET /api/v1/investigations/{run_id}` | Run头部、状态、用量 | Run字段、event_count、artifact_count、model_costs | 本次200；不直接返回全部报告/最终调查JSON |
| `GET /api/v1/investigations/{run_id}/events` | 分诊、完成度、过程 | since、limit（默认200、最大1000）；items/total/since/next_seq | 本次200；首次不传since才包含seq=-1；seq不是严格写入游标 |
| `GET /api/v1/investigations/{run_id}/artifacts` | 材料目录/报告定位 | 工件数组：id/kind/event_id/hash/bytes/时间 | 本次200；只有元数据，无正文 |
| `GET /api/v1/investigations/{run_id}/artifacts/{artifact_id}` | 读取具体材料和Markdown | content、blob_ref和元数据 | 本次21份正文均可读且字节/hash匹配；JSON需解析content，MD直接取content |
| `GET /api/v1/cases`、`GET /api/v1/cases/{case_id}` | 人工Case列表/详情 | Case及成员告警信息 | 本次只查列表，返回空；详情入口源码已存在 |
| `GET /api/v1/cases/{case_id}/investigations` | 人工Case运行历史 | Case下Run列表 | 原入口存在，本次生产租户没有Case，未重验 |
| `GET /api/v1/cases/{case_id}/investigations/{run_id}` | 人工Case运行结果 | Case/Run结果 | 原入口存在，本次未重验 |
| `GET /api/v1/cases/{case_id}/investigations/{run_id}/report.md` | 人工Case报告 | Markdown正文 | 原入口存在，本次无Case，使用通用工件取报告 |

不存在通用`GET /api/v1/investigations/{run_id}/report.md`读取合同。无Case报告按“目录→report_md工件ID→详情content”读取。

运行中事件读取需按事件ID去重并回看，不能只追max(seq)；终态重新拉取/分页核对total，防止高序号工具记录先到、低序号graph结果后到造成漏读。

### 2.4 已有操作接口（本次未执行）

下面是现有源码入口，用于后续选定的人工作业功能；列出不代表本次已完成生产操作验收，也不要求通过直接UPDATE表来触发调查。

| 方法与路径 | 请求/用途 | 需要区分的语义 |
| --- | --- | --- |
| `POST /api/v1/cases` | title；可带description/severity/alert_ids等，创建Case | alert_ids使用canonical Alert UUID；不因创建成功就认定调查已完成 |
| `POST /api/v1/cases/{case_id}/alerts` | alert_ids，关联已有告警 | 仅建立Case成员关系 |
| `POST /api/v1/cases/{case_id}/investigate` | 可带alert_summary，启动人工调查 | 返回run_id后持续读取实际结果；这一步会执行调查 |
| `PATCH /api/v1/alerts/{alert_id}` | status/priority/tags/assigned_to_id（别名assignee）/case_id | 只能更新接受的字段；不能在此随意提交模型结论或正文 |
| `POST /api/v1/alerts/{alert_id}/claim` | 认领当前未分配告警 | 已被他人认领可409；首次成功claim写first_seen_at |
| `POST /api/v1/alerts/{alert_id}/snooze` | duration_minutes或until | 暂缓队列展示，不等于解决告警 |
| `POST /api/v1/alerts/{alert_id}/escalate` | 提高严重程度一级 | **不是启动调查接口** |
| `POST /api/v1/alerts/bulk-close` | alert_ids或限定过滤条件；close_status/max_count/comment等 | 批量业务关闭；不等于调查完成或厂商响应动作 |

### 2.5 用已有HTTP拿到本例报告

```text
1. GET /api/v1/alerts/e5f593f0-b328-59c3-8238-379db33d8bfe
2. GET /api/v1/investigations?case_id=e5f593f0-b328-59c3-8238-379db33d8bfe&limit=20
3. GET /api/v1/investigations/bdccd907-7f36-558f-8ed4-4be2e417b101
4. GET /api/v1/investigations/bdccd907-7f36-558f-8ed4-4be2e417b101/events?limit=1000
5. GET /api/v1/investigations/bdccd907-7f36-558f-8ed4-4be2e417b101/artifacts
6. GET /api/v1/investigations/bdccd907-7f36-558f-8ed4-4be2e417b101/artifacts/72e0c864-41a0-4096-bfa2-8aa0ebe3a641
```

第4步分别取triage_verdict与graph_result事件，第6步响应JSON的content就是Markdown。以上路径已有实读；若选其他Run，应使用其实际工件ID，不能复用本例固定ID。

## 3. 实例及验证时点

各章的数据可用性按以下状态理解，不能把它们互相替代：

| 标记 | 意义 | 上线判断 |
| --- | --- | --- |
| **线上实值** | 本次从 21 HTTP 或 PG 读到了实际值 | 可据该路径对接；仍需处理其他告警缺值 |
| **线上空值** | 接口/字段存在，本次值为 null、空数组或未命中 | 可做明确空态；不能宣称丰富资料已具备 |
| **数据库实值/空值** | PG 已确认，但当前业务 API 没返回 | 后端需要聚合/补字段，浏览器不直连数据库 |
| **本地已测** | 当前本地代码有可验证输出，未部署 | 仅进入开发版能力，不能当作生产现成字段 |
| **待补** | 只有设计、源码入口或不稳定文本，没有已确认的读取合同 | 不作为现成可用；排入后端最小补齐项 |

本次 2026-10-23 **14:39（UTC+8）** 实读：41 个 GET 全部 200；2 条既有合成告警的 21 份工件正文 UTF-8 字节数、SHA256 全部匹配。生产镜像 API `5a1e1fd8cf08`、Agents `49643b84b8f7`。生产租户 `f6a5c700-69b8-44fc-8238-609362fb1a9f`，告警列表共 3 条，Case 列表为空。

**16:42新增审计复核**：PG只读事务确认六核心表167列与原目录一致，定向重读两例Alert/Run、21事件、21工件和3成本行；21份工件字节/hash及Run/事件关联一致。10个查询GET均200，但无匹配关键词仍返回3条，确认search缺陷保持。镜像未变，租户仍3 Alert/3 Run/0 Case。processing-context等动态结果沿用14:39证据，未在16:42重查。完整逐项结论见[审计附件](ui-functional-data-audit.md)和[脱敏JSON](ui-functional-data-audit.json)。

此前字段核验阶段另跑本地隔离 PG 两例“超时停止/模型报错”，实际 ledger 写入及持久结果读取通过，连同直接交接用例 **8 passed**。模型和查询工具为替身，PG 为独立临时容器/临时表；不是新真实模型调查，也不是本地 HTTP 全链验收。人工四节点校验信息复用当天已留存的真实模型采用样例，未再次调用模型。

完整脱敏实值、查询路径、正文校验和本地样例见 [字段验证数据](ui-field-verification-20261023.json)。自动关闭/自动调查样例分别对应JSON的 `online_samples.closed/partial`；两个本地样例在 `local_samples`。

此前数据库映射补充和结构调整只复用已有证据；后续本轮审计另有上述16:42只读复核。各阶段均未新调用模型、改变表结构、业务源码或部署。本地暂存测试容器已经清理。首次取数误查source列、首次本地连接被沙箱拒绝的记录保留；修正后分别取数/测试通过，不改写原失败。

