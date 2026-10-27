# 事件概况与调查：评审及功能实现规划

2026-10-25创建于代码基线`a5cad61`，最初一轮仅文档/静态评审；后续已实施F1/F2及F3第一版，状态见各批次段落。2026-10-27核对源码`6044615`，完整说明见[审计导航](audit-guide-20261027.md)和[当前实现详解](current-implementation-reference-20261027.md)。上一轮[设计—实现对照](design-implementation-review-20261025.md)仅描述其当时基线，不能代替新增F1–F3审计。

## 1. 评审结论

当前功能方向是：**事件保留汇总/AI概况，Case承载深入调查，再补成员转Case及原自动政策接线。** 先审设计见[当前设计对齐](current-design-alignment-20261027.md)。下表保留原评审基线的差距分析，完成进度以各F批次及当前实现详解为准，不将旧差距表当成新增代码尚未存在。

本次需要落实的主要缺口如下。它们都是用户能看到的功能缺口，不新增权限、可用性或恢复验收门。

| 发现 | 为什么影响业务 | 本次规划的处理 |
| --- | --- | --- |
| 现有 Fusion 的 `IncidentSummary` 是 Redis 窗口数据 | 事件详情及历史概况不能只靠这个会过期的对象 | 以 PG 告警保存的 Incident 归属解析成员；单独持久保存最小概况记录 |
| 分诊先保存，然后旧路径可决定升级；尚缺事件统一展示 | 不升级的理由、已关闭成员和待处理成员也需要可见 | 事件读取层汇集每个成员的当前分诊及处理结果，升级不是汇总前提 |
| 现有确定性 narrative 和单 Alert 的 AI 说明不等于事件 AI 概况 | 多条告警、各自分诊及调查结果缺少统一解释 | 新增事件材料汇总和首次/手动概况生成，标生成时间与来源范围 |
| 历史 `incident_id`/Run `case_id` 名称存在混用 | 直接按同名字段关联会把 Alert、Incident、Case 混为一谈 | 用 canonical Alert ID 解析成员；新 Run 显式保存来源 Incident 和实际成员，不猜旧记录归属 |
| 新 v2 主要完成一次固定查询和有限事实发布 | 还不能回答事件性质、关联关系、影响和后续应查什么 | 开发真正的主分析—查询/Deep—再分析—报告闭环 |
| 当前 v2 runtime 固定手动单 Alert；Case/Deep/自动接线未完 | 不能仅给旧请求填 Incident UUID 就宣称事件调查成立 | 先交付单 Alert 分析，再接事件成员范围与原有自动触发，复用同一内核 |
| AI 文本和当前数据如果一起刷新，容易造成展示滞后或多余模型调用 | 新分诊/调查结果可能被旧文字遮住 | 当前字段直接更新；AI 首次自动、之后手动刷新；重要节点自动刷新后置 |

## 2. 当前代码可以复用什么

| 功能 | 已有代码与事实 | 本轮需求仍缺什么 |
| --- | --- | --- |
| Fusion 事件归组 | [模型及归组键](../../services/fusion/app/models/alert.py)、[Correlator](../../services/fusion/app/services/correlator.py)：按主实体/首个 tactic/窗口归组，Redis summary | 可持久读取的事件概况及统一结果视图；不改归组算法 |
| 成员归属 | [PG 写入](../../services/fusion/app/services/alert_sink.py)保存 `enrichment_data.socai2_fusion.incident_id`；[Alert API](../../services/api/app/api/v1/endpoints/alerts.py)返回 `fusion_incident_id` | 依据 PG 行取 canonical Alert 成员，提供事件读取服务；Redis 的 member ID 不直接当 API Alert ID |
| 轻量说明 | [Fusion narrative](../../services/fusion/app/services/narrative.py)为确定性说明；[Alert explain](../../services/api/app/services/alert_explain.py)提供单告警解释能力 | 事件多成员材料汇总、模型生成和概况保存；不直接拼接成“已调查结论” |
| 分诊及原自动升级 | [worker](../../services/agents/app/workers/fused_alert_consumer.py)、[persistence](../../services/agents/app/workers/triage_persistence.py)、[ledger](../../services/agents/app/investigator/ledger.py)：先保存分诊，受既有开关/政策控制升级 | 事件读取完整分诊结果；后续将选定自动入口接到新调查内核。代码有分支不代表现网已启用 |
| 现有上下文和查询 | [incident_context](../../services/api/app/services/incident_context.py)实际上是以 Alert 为锚的上下文读取；[activity_records](../../services/agents/app/investigation_v2/activity_records.py)等为调查查询材料 | 按本次目标组装上下文；该文件名本身不证明已有 Fusion Incident 概况服务 |
| v2 启动及结果 | [API start](../../services/api/app/investigation_v2/program_start_api.py)、[coordinator](../../services/agents/app/investigation_v2/program_start_coordinator.py)、[runtime](../../services/agents/app/investigation_v2/program_recon_runtime.py)、[publication](../../services/agents/app/investigation_v2/program_recon_publication_store.py)、[reader](../../services/agents/app/investigation_v2/program_result_reader.py) | 复用已有持久化与读取基础，接实际分析能力；现有 factory 独立，功能入口仍需明确注册/调用，不声称已上线 |
| 主分析/Deep 可用素材 | [v2 model 执行](../../services/agents/app/investigation_v2/execution_models.py)、[v2 Deep 合同](../../services/agents/app/investigation_v2/question_deep.py)、[旧 Deep](../../services/agents/app/investigator/deep_investigation.py)、[旧工具循环](../../services/agents/app/llm/tool_loop.py) | 适配必要能力到新业务循环；旧 Deep 存在不等于新 v2 已调用；不改写旧 Run 结果 |

当前手动单 Alert、TCP/443 固定来源核对及有限报告已经有实现和阶段证据。它是可复用基础，但不等于完整调查。旧 `Run.status` 也不能替代新发布结果中的实际停止/完成信息。

## 3. 五个功能批次

用户已要求继续实施。所有批次遵守[调查模块实施原则](../architecture/investigation-planning-design.md#implementation-principles)：以功能为目标，逐个实现和直接验证，不扩展冗余/可用性/恢复测试，不为测试增加过多辅助代码。

每批直接实现可展示功能并做最小直接验证。修复该批真实缺陷即可，不再拆成大量“合同—替身—冻结恢复—独审”微阶段；不反复重跑未变化的底层合同。

### F1：事件当前数据与分诊汇总

**实现状态（2026-10-25）：已完成读取功能及直接验证，未部署。** `GET /api/v2/investigation/incidents/{incident_id}`返回PG归属的canonical成员、实体/时间/严重度、各成员当前状态/处置和最新已保存分诊理由。当前人工处置与历史分诊判断分别返回；没有明确分诊记录就返回null，不用Run.case_id猜关联，也不将成员关闭当作事件关闭。无模型调用、写操作或新表。

入口已加入v2兼容结果/启动app，也可单独运行`app.investigation_v2.incident_api:create_app`。实现见[读取服务](../../services/api/app/investigation_v2/incident_reader.py)和[接口](../../services/api/app/investigation_v2/incident_api.py)。[4个直接用例](../../services/api/tests/test_investigation_incident_api.py)于本轮通过，使用实际ASGI路由及替身数据库，覆盖混合处理状态与理由、重读更新、未知分诊及404；没有进行真实PG/用户鉴权专项或业务外呼，未重跑历史合同。AI概况与调查执行/结果关联仍分别由F2/F3继续，不因本接口返回分诊Run引用而标成已经完成。

**交付：给定 Incident ID，能读到当前成员、融合信息、每条分诊理由和处理状态。** 不依赖“有没有触发调查”。

- 输入：tenant、Fusion Incident ID；成员从 PG 告警的已保存归属解析，使用真实 canonical Alert ID。
- 输出：成员列表、实体、告警时间范围、融合严重度、各成员分诊/关闭/待处理理由；暂无结果明确标记。缺少可靠关联的历史 Run 不强行归入。
- 落点：API 新增事件读取 service/endpoint；复用 `Alert.enrichment_data`、现有分诊结果/ledger。确无合适持久对象时增加一个最小事件概况 model/table，供 F2 保存文本和时间；不建设新的事件总线。
- 最小实现方式：当前字段汇读来源记录，不复制完整调查材料；只保存事件自身的概况、必要关联/人工状态。事件更新时间和 AI 生成时的来源时间/标识分别返回。
- 直接验证：同一事件含待处理、关闭和升级三种成员，读接口能同时看到理由及 canonical ID；普通读取不运行模型或调查。

### F2：事件 AI 概况

**实现状态（2026-10-25）：功能代码与直接验证完成，未部署/迁移/启用任务。** 新增手动刷新POST、读取中的生成时间/范围/过期及失败信息；概况单独保存在`fusion_incident_summaries`。独立v2首次任务按PG成员保存时间发现新事件，每个事件只做首次尝试，之后手动刷新；原Fusion代码不改。接入与返回字段见[F2说明](incident-ai-overview.md)。本轮8项相关直接用例通过（F1四项＋F2四项），使用数据库/模型HTTP替身，未做真实PG或模型调用。

F3深入调查结果尚未关联，当前概况只汇总事件与成员分诊等已接入字段，明确标记`investigation_results_status=not_linked`。后续接入Run结果时继续补入材料，不将这部分提前计为完成。

**交付：首次事件形成后有一段概况；用户能手动用最新数据刷新。**

- 输入：F1 当前成员和分诊；调查主要发现/结果只有在明确关联并接入后才可加入，当前F2尚未接入。已有材料太多时说明本次摘要覆盖范围，不以截断后的子集声称“整个事件已分析”。
- 输出：概况正文、依据的成员/Run 引用、生成时间、来源时间/标识、是否已有较新数据。初次尚无分诊/调查结果也能给出有限说明。
- 落点：新增事件 summary service，复用现有模型调用能力；在首次成员保存后挂首次生成动作，提供手动刷新 API，结果写入 F1 的最小概况记录。路由名称在实施时按现有 API 风格确定，不伪装成已存在接口。
- 直接验证：首次生成；随后新增分诊结果，当前字段已变化而旧概况标为较旧；手动刷新后文字包含新结果。概况生成不调用调查工具，不创建 Run。
- 不加重要节点自动刷新、复杂防抖调度或新模型计费体系。普通失败能显示失败/未生成且保留已有文本即可。

### F3：Case中的实际分析、补查与报告

**实现状态（2026-10-25）：第一版Case调查内核代码与4个直接用例完成。** 新增Case POST调查/GET进展结果入口，复用原ledger保存真实Case归属、成员/窗口、模型/工具步骤及报告；主分析按需选择进程/网络查询，再接收Tool消息形成带依据和缺口的结论。同源同范围的适用查询材料可复用；同key重读不执行。见[F3调用与验证说明](case-investigation.md)。使用模型HTTP/ledger/事件湖替身，未做真实PG、模型或事件湖调用；真实模型自主选工具与业务判断质量仍待选定场景直接验证。

**2026-10-25用户修订：真正调查统一在Case中，事件只保留汇总和AI概况。** F3从已有Case及其明确成员启动；首个直接场景可以是含一条Alert的Case，不另建事件调查系统。

**交付：手动启动一次Case调查，系统能说明判断依据、自动补查所缺证据，并给出结论或明确缺口。** 不再以固定TCP/443摘录作为完成标准。

新增产品查询能力按[Tool 接入与流程验证指南](tool-onboarding-and-flow-verification.md)执行：先明确 HTTP、参数/结果映射及模型注册，再从目标调查入口检查选择、调用、回传和采用。用正常/空结果/查询失败三个基本场景覆盖该能力，不把指南扩成新的多轮审计阶段。

- 输入：真实Case、canonical成员Alert、分诊、实体/时间窗口、可用上下文及适用历史材料。
- 输出：主分析判断、按需查询结果、更新后的判断、证据/反证/未解问题、停止原因和 Markdown 报告。
- 落点：独立v2 Case入口、共享ledger、模型协议及有类型的查询工具。旧fixed/program保持原解释方式；现先接主分析和进程/网络工具循环，专项Deep/专家与产品HTTP能力后续按实际缺口接入，不固定串行调用所有角色。
- 同步接线：服务端固定Case和实际成员范围，Run/证据/报告归属Case；成员的来源Incident只用于回链和已有概况，不增加事件级深入分析。停止/结果按实际工件读取。
- 入口：明确接入可调用的 API factory/路由；保存实现不等于部署。新增能力不改变已发布旧 Run 的解释方式。
- 直接验证：一个受控场景走通“主分析→一次必要查询→再分析→报告→Case/Run可读结果”；另确认缺少关键来源时报告写明未解决问题。已有查询结果能满足问题时无需为凑流程强行多查。事件回显Case结果目前未接通，不能计入F3已通过范围。

### F4：从告警/事件选择成员创建或关联Case

**交付：用户从Incident选择当前成员或子集，创建/关联Case，再从Case发起调查。**

- 输入：来源为Incident或明确Alert列表、显式选定的canonical成员、创建/关联Case目标。窗口和补充问题在随后F3启动请求传入；F4只处理成员组织。具体请求/返回见[接口设计第4节](interface-contracts-20261027.md)，不只传incident_id或一段摘要。
- 输出：创建/关联得到的Case ID、实际选入的canonical成员、来源Incident引用及后续调查入口；明确全量或子集。实际Run范围、跨告警判断、覆盖缺口和报告由F3产生；新到告警不自动加入已经开始的Run。
- 落点：事件入口只解析成员并调用Case创建/关联能力；复用F3的Case调查，不新增事件profile或另一套执行内核。不能把Incident UUID填入Case ID冒充已有支持。
- 首版关系：Incident提供已有汇总/概况及Case入口；Case负责成员组织和真正调查。跨告警综合在Case内核对关系与反证。
- 直接验证：三成员例子分别启动“全部成员”和“明确子集”，结果准确标范围；原有调查材料按适用性复用；新成员不偷偷加入已开始的 Run。

### F5：接通原有自动触发

**交付：分诊完成后，符合原升级条件且已启用时自动进入同一调查内核；事件可看见原因、进展和结果。**

- 输入：已保存的分诊结论、原升级政策及运行开关。当前 ordinary worker 对所有未自动关闭的告警（含 `needs_review`）进入升级判断，实际执行受 review-only 模式、自动升级开关与 writer 许可控制；不新增“仅建议升级才触发”的规则。自动入口沿原逐 Alert 语义，不擅自将每条升级扩大为全 Incident 调查。
- 输出：关闭该 Alert / 待处理 / 自动调查及其原因；自动 Run 与手动 Run 共用结果格式，事件能跳转到对应 Run。
- 落点：`fused_alert_consumer._maybe_escalate`所在的现有接线边界，先按已有政策创建/关联Case，再进入F3 Case内核；不无条件为每条告警新建Case，Case尚未满足条件时保留待处理原因。沿用原开关/政策，不另建规则引擎。旧playbook已有investigate路径保留，额外改造继续后置。
- 直接验证：一个允许升级场景进入调查并回写结果；一个不升级场景仍有分诊及理由。只保留一个明确执行分支，避免同一请求同时调用旧、新调查。
- 开关启用及真实环境部署仍是单独动作，本轮文档不改变运行配置。权限专项不列入这五批的功能前置门。

## 4. 建议实现取舍

1. **先读已有数据，再补少量保存。** Redis 保持原关联用途；PG 告警归属用于事件成员读取。概况正文和必要关联需要持久保存，但不复制整份证据库。
2. **事件与调查范围分开。** Incident 当前成员会变，Run 分析的是启动时选定范围。事件 AI 概况引用 Run 结论时同时说明覆盖范围。
3. **状态来源分开。** Alert 分诊/关闭、Incident 人工处理、Run 执行/停止各有含义；无事件人工状态时就返回未设置，不根据成员关闭数自动声称事件已关闭。
4. **只补需要的调用。** 主分析、查询、Deep、专家均为达到业务判断服务，不把全套角色或全部基础设施改造当成每次调查必经流程。
5. **事件范围保持简单。** 已有汇总和AI概况即可；Case承担深入调查。重要节点自动刷新后置，不新增Incident调查profile。

## 5. 一轮评审记录

作者完成需求与源码对照后，由独立评审者 `flow_plan_review` 对两份文档及必要源码做了一轮静态评审，没有修改源码、运行测试或访问真实环境。

本节为原2026-10-25评审记录，下面R0/R1的描述对应当时例子；后续已按用户要求改为Case流程和手动选择示例。本次2026-10-27是作者静态文档对齐，未重新执行独立评审，结论见[当前设计对齐第5节](current-design-alignment-20261027.md)。

- **发现并修正 1 处触发语义偏差：** 原例子只让“建议升级”的 A2 自动调查，却让未自动关闭的 A1 停留待处理；这与[worker 现有调用条件](../../services/agents/app/workers/fused_alert_consumer.py)及 F5“沿用原政策”不一致。现明确 A1/A2 都按原条件进入升级判断，例子分别关联 R0/R1、只展开 R1；F5 同步写明实际开关条件。
- **其余没有发现必须修改项：** 分诊各类结果汇入事件、动态数据与 AI 概况分开、Incident/Case 身份、手动/自动与成员覆盖、已实现/待开发标识及五批顺序均可用。
- 顺手澄清概况图的材料读取边为“仅生成动作触发后读取”，避免将数据变化误读为模型触发。

上述意见已在本轮文档中收敛。结论是可以据此进入功能开发；这是设计/计划静态评审结论，不是五批功能已实现或已通过运行验收。未另开评审轮次或附加测试门。

## 6. 本轮结束与下一步

本轮完成标准是文档保存、一次评审意见收敛、实现顺序明确。只检查文档链接和差异，不新增业务测试，不重跑旧测试，不勾选未完成的 OpenSpec 2.2/2.3。

F1/F2及F3第一版Case调查内核的代码/直接验证已完成，真实模型行为与环境接入仍按实际状态保留。下一功能F4补告警/事件转Case入口，F5接原自动政策；不再建设事件级深入分析。正式部署、权限专项仍不自动开展。
