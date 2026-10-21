# 3A-06：KB读取认证、引用及实际采用文本

状态：2026-10-20已限定验收，见[3A-06回执](3a-kb-read.md)。下文保留实施前范围、判据及实测阻塞后的修订；改动前值在受控kb-read-3a-before目录。下一单项为[3A-07近期分析员处置读取与采用来源](3a-dispositions-plan.md)，完整知识/引用/调查质量未通过。

本批只接通已有告警分诊使用的租户runbook读取：标准身份 → 当前PostgreSQL全文检索 → reader port → 实际prompt → 引用与持久工件。已有向量/ATT&CK/TI索引、旧SOCAI资料盘点或API可查询，不等于这条路径已消费，也不计作检索质量通过。较大嵌入模型、向量空间比较和全量知识导入仍按[知识复用计划](knowledge-data-reuse-plan.md)及3C另做。

## 已静态证实的当前行为

| 位置 | 源码事实及直接影响 |
| --- | --- |
| [API知识路由](../../services/api/app/api/v1/endpoints/knowledge_base.py) `retrieve_runbooks_for_triage` | `GET /api/v1/kb/runbooks/for-triage`仍仅校验`X-AiSOC-Service-Token`；无Bearer principal、tenant交集或明确读取permission。查询前已有RLS设置和SQL tenant条件，不能因此宣称请求身份正确。此前3A记录的实际401仍需在本批操作前重新复现。 |
| 同文件`query_kb`、[权限目录](../../services/api/app/core/rbac_catalog.py)、[权限表](../../services/api/app/core/security.py) | 现有`POST /kb/query`明确需要`knowledge_base:read`。该权限存在，viewer持有，静态`api_service`不持有；文件开头“query未授权、没有KB权限”的旧注释与当前实现冲突。本批依据实际permission与[身份解析](../../services/api/app/api/v1/deps.py)，不能照旧注释选`settings:read`、`alerts:read`或万能key。API-key scopes是显式权限来源，不自动继承账号全部角色权限。 |
| API `triage_retrieval_sql` | 当前使用PG `english`全文检索，只匹配`content`；`plainto_tsquery`、`ts_rank`、同分按row ID、默认3条；只取runbook/playbook/sop，不走embedding或`/kb/query`的LLM synthesis。现有cutoff仅检查`created_at <= as_of`，拒绝数亦仅按创建时间统计；未核`updated_at`，不能据此声称可还原后来被编辑的旧正文。 |
| [Agents KB reader](../../services/agents/app/context/knowledge_base.py) `fetch_runbooks` | 仍发共享X头；缓存键只有tenant/cutoff/limit/query，未绑定URL或凭据，且先命中缓存再检查凭据。关闭、无tenant/query/token、HTTP/连接/JSON错误都可呈现空`RunbookRetrieval`，无法区分确认无命中与读取失败。网络失败当前不返回过期缓存，但新身份/地址可复用尚在TTL内的旧缓存。 |
| 同文件`_contain`、`RunbookRetrieval.as_state` | 未验证返回tenant等于请求tenant；坏行被部分忽略，数值强转仍可能抛错，非字典JSON对象也可能被缓存。`as_state`没有保留已有`created_at`/score，也没有正文hash或确切版本事实。API的`doc_id`是chunk行UUID，不是另一个完整文档实体ID。 |
| API `get_document`、`KBDocResponse` | 引用对应的`GET /kb/documents/{id}`目前返回最多200字符`content_preview`，不能仅凭此GET核完整片段的主张。新回执须保存实际采用原文及其hash，不把可解析ID外推成全文可核；核Run工件使用独立操作身份，不扩大KB reader权限。 |
| 同文件`render_for_prompt`、`citation_basis`、`unresolvable_citations` | 渲染还会按整块预算截取/停止，但引用表和引用校验基于所有retrieved rows；极限长度或较大top-k下，工件中的完整content/可引用marker可能多于模型实际看见的内容。当前标题、段落、总块预算并非同一份最终采用记录。 |
| [worker](../../services/agents/app/workers/fused_alert_consumer.py) `_attach_runbooks` | query由summary加rule_name/rule_id、最多400字符生成；没有query会直接跳过。没有runbook且没有注入拒绝时直接返回，失败状态和空结果不进state。对全部词做PG查询可能很严格，应记录实际query和命中，不能用不会命中的空样例证明“隔离成功”。 |
| [reader port](../../services/agents/app/workers/triage_persistence.py)、[frozen reader](../../services/agents/app/replay/shadow.py) | `retrieve_runbooks`是现有`CUTOFF`源：live传`as_of=None`，frozen从snapshot传split，caller不能指定cutoff。`_account`对没有echo的结果计`cutoff_not_honoured`，但仍把其rows交给worker；只有计数不等于阻止晚到材料进入历史prompt。 |
| [分诊prompt](../../services/agents/app/agents/auto_triage_agent.py)、[state记录](../../services/agents/app/models/state.py)、[账本](../../services/agents/app/investigator/ledger.py) | KB已有nonce fence、边界说明、扫描后清理、`[KBn]`提示及无法解析引用告警。现有literal prompt/response各最多8000字符，hash覆盖完整值并有截断标志；没有独立KB读取/最终采用工件。不能把存在引用标记或完整hash写成模型引用准确。 |

这些是静态事实，不是本批真实HTTP、PG检索或模型质量验收。注入守卫注释中的历史检测率也不是本项目当前测得结果。

## 本批最小实施范围

1. 只改上述内部GET为标准Bearer身份与`knowledge_base:read`，请求tenant与principal tenant一致，省略tenant时采用自身；拒绝越权后再设同一tenant的RLS和查询参数。X头不授予权限，保留既有SQL排序、文档种类和live不带cutoff的语义，不借机改写`/kb/query`、ingest/delete或全局RBAC。
2. Agents新增独立`AISOC_TRIAGE_KB_KEYS_FILE`受控tenant→key映射，复用现有凭据helper的专用env参数。每个A/B测试tenant的reader key只含`knowledge_base:read`，不扩大组织记忆或技能key，不回退它们的映射/共享token；目录0700、文件0600、只读目录挂载、非root运行。先核现有scope校验和账号状态，按短期操作key与保留reader分别记录失效时间和撤销。未配置tenant明确不可用，不全库补发key。
3. 沿现有`retrieve_runbooks` port保留`RunbookRetrieval`兼容形态，增加typed读取事实，至少区分success、no_match、disabled、unavailable、not_requested。记录reason、tenant、来源、query/limit、请求/实际cutoff、read_at、HTTP、cache来源/年龄/TTL、返回/采用/拒绝数量；空query是未请求，真实200无命中才是no_match，全部被注入拒绝也另有明确拒绝原因。无法确认tenant、cutoff、row ID/类型/索引、有限score或响应结构时不可用，不能伪装空结果。
4. 凭据配置在缓存查询前读取，缓存按tenant/URL/凭据hash/规范化query/limit/cutoff隔离，不把token放进回执。TTL默认120秒，刷新失败不采用过期材料；映射移除/轮换与地址变化不命中旧身份缓存。缓存有效不证明服务端撤销、文档删除/修改即时生效，验收强制刷新故障须明示为探针配置，不能当默认即时撤销证明。
5. 将实际采用片段及引用表与最终渲染预算统一：每条保留chunk行ID、title/kind、chunk_index/total、来源URL、created_at/updated_at、raw/adopted正文hash、截断或拒绝事实；只有真正进入prompt的marker参与引用解析。模型实际看见的清理/限长文本和nonce边界块另存hash与字面值，避免渲染后再裁剪却保留旧引用表。单条900字符、总正文3000、envelope3400、默认top-k3和query400先保留并明确计算标题/边界开销；这都是字符限制，不当作模型token预算。
6. frozen reader仍由split决定cutoff，不得接caller时间或用“现在”冒充冻结。必须核服务端echo与请求是同一时刻，并逐条验证可用时间；不honour的响应明确失败且不采用rows，保留拒绝计数。实施前以真实PG复现“created早、updated晚”边界；若无版本历史，保守排除split之后被修改的行，报告排除原因，不能宣称重建其旧正文或完整历史语料。无时间戳材料明确未能证明历史有效，不默默纳入“冻结通过”。不改既有snapshot源及skills_under_test例外。
7. 新增KB读取/采用工件与verdict payload，沿现有首次写入事务持久化；记录可解析marker、实际模型引用及无法解析引用，区分“已提供”与“模型确实引用”。同Run重试不替换/追加，工件写失败回滚并沿既有durability保护。原组织记忆/技能工件、原事实及旧回执不改写；不把首次工件冻结外推成整个Run完全不可变。

预计源码限API `knowledge_base.py`；Agents `context/knowledge_base.py`、`workers/triage_persistence.py`、`replay/shadow.py`、`models/state.py`、`workers/fused_alert_consumer.py`、`agents/auto_triage_agent.py`、`investigator/ledger.py`及本批测试/部署叠加文件。已有凭据helper接口可直接复用，不默认另建通用认证层、DDL或依赖。实施前保存各文件前值及源码来源hash，必要差异逐项入新清单；若实际阻塞超出范围先修订本计划，不直接扩大工作。

## 输入 → 实际调用 → 验收结果

| 输入/故障 | 实际中间产品 | 本批通过条件 |
| --- | --- | --- |
| A/B有同关键词且正文不同的短runbook；A另有policy/wiki | 标准Bearer、SQL实际绑定tenant/kinds、真实PG/API | A只得A runbook/playbook/sop，B只得B；省略tenant归自身。不能用空租户证明隔离。 |
| 只有KB读取scope；缺scope/跨tenant/匿名/坏key/仅X头 | 真实API认证链 | 读自身200、跨tenant/缺scope403、无效身份401；reader的ingress、ingest/delete写操作拒绝。不给reader新增写权限来准备样例。 |
| 有效query、空query、真实无匹配、关闭、缺映射、错tenant key、撤销/到期、连接或数据库故障 | 生产reader/port及缓存；失败另做prompt投影 | 状态与原因可区分，失败不采用旧片段或声称租户没有文档；恢复后重新读取成功。只在新测试对象/探针进程控制故障，不重启共享PG或改全局服务。 |
| split前/后资料、全被cutoff排除、created早updated晚、缺失/不一致echo | 同一生产SQL的真实PG结果、frozen reader与method note | live正例可命中，frozen只采用能证明有效的旧材料，排除计数保留；不honour不进入prompt。不重写历史内容。 |
| 三个长片段/长标题、超预算、注入指令、伪造nonce、无效/未采用marker | 清理前扫描→预算采用→nonce block→实际引用表 | 原边界守卫继续；弃用/截断片段有事实，采用文本/hash与实际prompt一致；从未进prompt的`[KBn]`不可算已提供来源。不得用删除断言或静默扩预算解决。 |
| 一个标记告警 | 认证ingress→实际Fusion信封→生产worker/context reader→21网关→43的一次有界调用 | 捕获真实送入safe-call的query命中来源及最终块，组织记忆/技能既有能力保持。记录模型采用或未引用及理由、无效引用；若模型没引用，不写成引用质量通过，不自动补调凑结果。 |
| 本批新Run/工件故障与重试 | 真实PG事务故障、恢复、同Run/API工件回查 | 故障后不留孤立verdict/工件；恢复内容和事件关系/hash正确；同输入重试不追加；API/Agents定向重启后可回查同一来源文本。 |

样例先用可识别测试tenant及少量受控短SOP/公开资料；如选`../SOCAI/knowledge`已有材料，先核来源sidecar、实际正文和hash，只引入与该告警有关的一小份，记录“公开参考”而不是租户既定制度，不把历史版本当最新事实。旧5GB目录、40万条记录、现有向量集合均不批量复制/重建，不导入旧调查原文或机密文档。受控样例准备与reader权限分离，新增行保留，不为测试删除已有KB内容。

一次模型调用只核真实消费、引用与账本关系，不以预定分类作通过条件。保留总prompt中组织记忆/技能/KB各自实际采用量，检查全prompt/response是否超过8000字符literal上限；标记不得抹去。本次有界样例应使全文可回查；记录真实input/output tokens、角色路由、CostTracker/Run/成本行一致性，费用未知仍记unknown。字符预算、token使用、引用正确性分别记录，单次成功不外推宽样本检索、分类或校准质量。

## 复用测试与退出边界

优先复用[Agents KB测试](../../services/agents/tests/test_triage_knowledge_base.py)、[replay leakage](../../services/agents/tests/test_replay_leakage.py)的runbook部分、[API retrieval测试](../../services/api/tests/test_kb_triage_retrieval_route.py)、[平台权限测试](../../services/api/tests/test_platform_route_permissions.py)及[租户隔离测试](../../services/api/tests/test_compliance_phishing_kb_tenant_isolation.py)中直接受影响的项。原API retrieval测试的“Bearer仍拒绝”是旧合同，本批须按新身份合同保留等价拒绝/允许敏感性；原HTTP替身成功不当实际认证或SQL通过。

固定上游另有`tests/isolation/test_kb_retrieval_cutoff_live.py`，本仓当前未迁入。其原seed/finally会按固定tenant删除KB行，不能直接对21套跑；复用生产`triage_retrieval_sql`和有效断言，改成新批次隔离对象、禁止全租户删除且必须执行、不许skip。源码只读参考，差异记录；只补本批正常/关键边界，相关通过后推进，不扩成全仓回归。

开始远端操作前核当前镜像/叠加层、A/B映射状态、PG表/迁移与KB既有材料摘要，保存前值；当前数据量、真实query命中、服务端认证失败方式、数据库故障传播、完整token预算及真实模型引用均**待实测**。本计划没有把它们标为已通过。

退出时交付来源差异、实际HTTP/PG/模型/工件关系回执、旧材料保留与新key生命周期、定向恢复验证及限制。预计只更新API/Agents；Fusion/Actions/基础设施保持。常驻worker、自动graph、审批、真实响应、近期处置/身份reader、旧增强工具授权及全局知识质量继续不在本批通过范围；不宣称整体3A或服务端基线冻结。

## 实施前补充约束

已核真实表created_at/updated_at均NOT NULL，不为NULL样例禁约束或改DDL；缺时间戳的reader拒绝以测试替身验证，真实PG只验合法时间边界。生产worker会拼接Fusion narrative，FTS query含该实际文字；模型前先捕获真实信封并验证原query命中，必要时只给本批新增合成A/B正文补明确标记的测试检索词，记录原/新正文hash及updated_at，不修改query或信封，不称其为split前历史正文或真实SOP质量。真实PG读取故障/恢复用同会话SAVEPOINT及生产SQL投影，不冒充线上HTTP或共享PG outage。

模型前实测完整literal为8717字符，超过原8000上限，尚未触发模型；保留原检查点。允许仅压缩本批新建A/B合成正文及标题，用真实PG唯一词项缩短测试检索词，并保留最短证据要求及synthetic标记，记录旧/新内容和标题、hash/updated_at，实际API仍须命中原query。保留原告警/信封/查询、旧组织记忆/技能、系统prompt及8000上限，从模型前检查点只读复核后继续，不重发ingress、PG故障探针或重启。

首次压缩后完整literal仍8105，未调用模型。新增必要阻塞修复限KB inline边界说明的等义精简：保留不可信DATA、可能过时/不适用/第三方或攻击者内容、不服从任何自称system/policy/playbook/manager的指令、不得改verdict/close/contain/skip/reveal、报告注入并继续忽略。共享envelope、standing system_rule、注册system prompt/lock及8000上限不改。重新执行直接Agents测试后仅重建Agents，新旧镜像及两次预算失败全部保留；从原accepted告警和probe的模型前检查点继续，不重发输入。
