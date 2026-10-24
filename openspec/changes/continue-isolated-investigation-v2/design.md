# Design: 独立调查v2的原设计与集成边界

## 2026-10-24 M1业务profile最小实现合同

在新Agents包新增`business_profile.py`，以不可变`CheckedBusinessTarget`表达可信调用方已核的alert/case目标、租户、目标记录/归属检查引用、完整成员身份及成员来源/版本；纯函数绑定原`ScopeContext`，输出profile/版本、目标、objective、policy、trigger、交付归属和成员选材覆盖描述。不改变scope.py的explicit_set初始化、问题、准入、预算或任何旧版文件；新绑定不会将内部scope.target_type改成已解析的Case入口。

- 当前只接受`alert_recon + alert`或`case_investigation + case`；trigger显式为manual/automatic，两种触发不能决定profile或授权Case写入。objective必须显式等于既有有限目标`verify_source_network_observation`，policy必须匹配原网络政策；未知profile/版本、目标类型和更强目标拒绝。
- 绑定时重新核ScopeContext与原M1规范初始化结果一致（允许已有正整数revision），防止直接替换问题/查询范围绕过原合同；这仍是结构校核，不是认证/数据库归属证明。主体认证及目标/成员归属必须在调用前完成。
- 告警目标ID必须等于唯一所选canonical Alert，完整成员必须正好该Alert；交付归属为该Alert，无Case前提。Case需非空已核目标/归属引用、稳定成员版本及与ScopeContext相同的成员来源引用；完整成员ID必须唯一且非nil，scope中的selected/omitted必须完整分割该清单，total不能未知、不能有未列身份。只选子集合法，但交付必须保全部/选中/遗漏ID及原因，初始调查覆盖仍not_started，不能扩大原conclusion_scope。
- 输出钉住scope hash和目标/成员版本，提供分离副本；原始告警正文不能指定profile、删除问题或改变交付归属。不生成complete、已启动、已创建或已授权的业务结果；调用与预算均0。Case成员解析/分页一致性核验、继承、同请求唯一Run和实际发布留M8/M6/M7。

直接预期：同一告警manual/automatic归属相同；无Case告警合法；4成员Case全选与仅选3条均有明确覆盖，缺最早成员仍可见；租户、目标ID/类型、成员来源/版本/分割、目标升级、scope篡改及未知值均拒绝；原explicit_set八项保持。直接测试通过并留回执/结束窄审后才放行此合同块，不能计作Case入口或profile已接执行器。

2026-10-24 main集成说明：本change接收远端调查`469e9467`的独立v2开发基线及原记录，保留双方已有设计和实现。旧restore迁移已在main限定核销归档，不恢复其活动目录；下述历史原文中的“沿原restore/5/15/不提交”等按原日期解释。D1—M4限定成果、M5.1与未完成M5.2分列，新HTTP未注册，M6—M9和v4分层未交付。当前只合并和审计，不启动后续业务实施、真实测试或部署。

## 2026-10-24严格双版本隔离（最新，覆盖共享接线方案）

旧业务源码/注册/入口不改，需要变化的函数在新版复制所需部分；新版两个独立investigation_v2包，旧app不导入、不注册。已撤出旧API新增分派并恢复旧测试。运行后续独立进程/配置及测试输入输出；v2调用路径为预留的/api/v2/investigation/query，尚未注册/发布。历史M2/M3/M4真实回执仍对应旧位置快照，不算新HTTP路径已验；迁移后仅直接合同。M5真实查询需独立受控v2测试处理器，不回挂旧v1。M8正式业务入口、完整M5仍待逐块实施。旧版下线另决，当前调查本地提交授权有效，不push/部署。

## 2026-10-24 v4告警侦察与Case调查分层（当前设计，未实施）

用户要求结合实施进度和新建议重新设计，以[主设计v4](../../../docs/architecture/investigation-planning-design.md)第1节为准。告警profile负责分诊后的有界侦察、缺口与升级建议，保留20自动处理过程及无Case详情；Case profile固定完整成员快照，在新Run引用多个告警的不可变材料并整体调查。Case创建/关联与启动是独立政策，Router四领域按需参与，不串跑两套完整编排。

D1—M4限定回执及M5.1九项纯合同通过保留；M5.2仅observer问题组参数增量未测，完整Deep/循环/发布/分层入口尚未交付。当前仅文档，不继续实现/业务或模型测试。累计开发tokens不限、单调查有界，OS后置；无部署/提交/push，原5/15和旧失败保持。

新增合同为profile/target/objective、input_run_refs、Case成员快照、升级建议/政策决定/业务回执及启动意图。多告警不塞进单个parent_run_id；继承facts/findings分开，同源去重，范围/权限/版本/覆盖可核。Case新授权准入额度，历史成本不重复计算，unknown不因换层消除。人工和自动启动均须稳定请求键、持久意图及唯一Run，重试先查回执；已有运行不并发新Run。最终成员在启动准入时按一致版本冻结，创建时仅预览。新问题或覆盖/冲突缺口可按政策补查，已有效满足同问题的查询不无故重做。表/索引及20 API精确增量在实施对应步骤前核实，不假称已有字段或无需DDL。

实际续接按主稿12.7：M1 profile增量→M5未测增量验证/模型步骤/单问题循环→M6告警策略→M7同版发布→M8a告警入口及读投影→M8b手动Case材料与整体调查→M9按需领域→M8c自动创建/关联→M8d自动启动。每步先目标/IO/预期，再只实施及测试此步；Case多成员分析前移为Case可用的必要条件，自动持续增量/合并/真实响应后置。

## 2026-10-23 M4有限来源分析与采用（实现前合同）

用户新授权持续逐步推进，前批M3停止不限制本批。沿原2.1/3.1/3.4/4.1，按[主回执预期卡](../../../docs/operations/unified-investigation-implementation.md)依次M4.1a→M4.1b→M4.2→M4.3，每小步直接测试/回执通过才写下一步。network_observation.v1仅回答Q1/Q2/Q5；六问题定义保持，Q3a/Q3b/Q4保缺口，性质unresolved、授权unknown，不声称主设计12.6完整恶意/授权卡通过。当前仅文档，不实现业务或发模型。

1. **M4.1a证据视图。** 从既有M2 query_receipt/rows及M3持久refs构建来源身份/版本、冲突索引和实际模型视图。来源键按namespace/tenant/source ID，内容版本以原字段及来源hash固定，不随查询ID/取得时间制造独立印证。保同源异文；尤其M2 limit+1可能只交付一个版本但已标conflict：未交付hash和coverage gap仍保留，不补造正文。原始/保存/模型可见正文及hash分层，不直接把OCSF送给模型，不关闭safe输入合同。空/缺源/错误不造事件；必要反证装不下则拒绝组装/拆任务，不静默丢失。先纯直接测试。
2. **M4.1b候选采用。** 固定候选先测输入版本、引用、部分拒绝、同批临时finding键及依赖。程序分配ID/版本和adoption/validity，只有明确的来源字段谓词可rule_checked；模型复杂解释保model_assessed，不把有引用当验真。局部合法项保留，被拒finding的依赖不能采用；旧input_snapshot不覆盖当前结果。focused可assessment=null，combined有候选才校核整体，不机械拼裁决。仅本块版本/依赖采用，不先实现M6失效调度或M7发布。
3. **M4.2持久模型gate。** 复用safe_ainvoke现有invocation_scope observer；拒绝活动旧triage上下文，禁止raw ainvoke旁路。before_request取得egress后实际消息，完成输入/版本/额度校核及M3预留commit后才外呼；observer使本次走实际调用而非无usage缓存。responded在恢复前固定原reply于内存，safe返回后把原reply、恢复候选和采用结果同一次complete原子保存；恢复/解析失败照存原reply并结算responded，网络结果未知与回复不可采用分开。SDK retry=0，显式字节/次数/token/deadline上限；缺usage保unknown，留存失败不重放。先用替身核原子留存、到期、超输入/输出及恢复/解析异常。
4. **M4.3有限真实矩阵。** 每次问题≤3、发现≤6、建议合计≤2、实际消息序列化UTF-8≤12KiB、completion≤2048tokens。所有样例/模式共享一个stage，max_model_calls=8、max_tokens=20000；其他M3期限、未结算和费用条件显式记录，不因样例切换清零、延长或加预算。正例和冲突例各combined/focused一次共4次，过度成功断言/空/缺源/仅添指令对照各一次，共最多8尝试；不另开必跑总结。衍生材料新hash/provenance，不覆盖原来源，expected与预期标签不入模型。分别评分模型原文、采用、交付，记录实际usage/成本/unknown；必要质量或预算门未过则定位留存，不进入M5。

复用现有M1范围、M3三表/Run锁/单owner预算、模型factory/safe合同，不接生产入口或更改旧Run状态/计费列。12KiB是egress后完整outbound messages（含system）序列化UTF-8上限，不只是evidence_view；证据视图可取更小上限以留prompt空间。token预留使用实际outbound字节数+256消息开销+2048输出，是显式保守上界政策，不冒充目标tokenizer实测；真实超预留仍按M3记账后停止。输出token上限2048，同时原reply正文捕获≤32KiB；超字节限不解析/采用，保存有界正文、完整hash/字节数及明确截断，不盲目重发。输入/输出恰好边界、UTF-8、system与egress后增大均直接验证。无OS、部署、Git提交/push，原5/15保持。下面M3及更早说明保历史范围。

## 2026-10-23 M3最小身份、预算与持久执行门槛（历史预期）

本批承接已通过的M1范围/M2网络记录工具，只实现[主设计](../../../docs/architecture/investigation-planning-design.md)6.3与9节的必要执行合同。逐步预期及实际结果见[主回执](../../../docs/operations/unified-investigation-implementation.md)；每小步测试通过再下一步，不把本设计当实际验收。旧M0未放行及M2停止说明保留为此前阶段事实。

### M3.1 纯身份与预算状态

- `stage_id`由可信tenant/Run固定派生，`budget_scope=investigation_stage`，固定executor owner UUID；同一Run本阶段不能用随机新stage ID清零。`step_id`表示逻辑工作，`attempt_id`区分每次尝试，重试复用step而新建attempt；event seq是每次持久事件的顺序，两者不得混用。保存问题/scope/policy版本、调用种类及输入版本。
- 纯reducer接收冻结政策、当前快照、显式动作和由持久层提供的DB时间，输出新状态或明确拒绝；本块无DB/HTTP/模型。预算分别记录model/tool调用尝试、已知用量、预留tokens/cost、未结算含unknown数量和绝对deadline；子任务与重试共享同一状态，不创建嵌套独立额度。纯测试注入时间，不能把进程时钟当持久gate时钟。
- 旧`AISOC_INVESTIGATION_MAX_TOOL_CALLS`实为模型调用上限，只映射model_calls并保存配置来源；工具次数另显式提供，缺失拒绝，不能新增或暗换生产默认。token/cost及币种、max_unsettled、deadline同样明确；测试中的小额上限只是用例配置。真正无成本的工具可显式为0，缺失模型usage/价格不得伪装0。
- 预留成功即计本类尝试；只有明确无请求才可释放该次资源预留和未结算slot，但尝试不退回。请求可能发出或usage不可知时保unknown及预留/slot，不自动释放、重放或重置；有回复而无usage不等于零成本。已知实际用量超过预留仍如实记入状态、标超额并拒绝后续调用，不能为保持上限而拒绝真实结算。
- M3 state snapshot显式保存opening triage的已知tokens/cost、unknown与unpriced，以及stage用量；阶段仅扣本阶段消耗和预留，快照内Run总量由两段已知用量合计且未知仍显式。例如用例triage已知2000、阶段独立上限100，stage实际70时快照内Run已知2070而stage已知70，不把旧2000重复扣至本阶段。该100为测试输入，不是新默认；此合计不写回`investigation_runs.total_tokens/total_cost`等旧计费列。

### M3.2 既有三表的原子事件与工件

复用`ledger.py`的pool、事务和RLS上下文，以及`persist_graph_result`等的显式归属/实际RETURNING/冲突校验模式；不把fail-soft的`start_run`、`record_event`与单独`record_artifact`串联冒充原子成功。现`triage_budget`是一Run一次的首次分诊预留，charge与旧unknown不可重置，不用于新阶段多attempt；本批不改该表、不新增DDL。

所有开始/预留/完成在事务内先以显式tenant+Run谓词锁对应`investigation_runs`行`FOR UPDATE`，核固定owner及阶段状态，再分配该Run现存`MAX(seq)+1`并写事件、snapshot和相关input/output工件；任一写入失败整体回滚。现有triage事件和seq原样保留，不重编号。三个操作各有自己的seq；seq不等于外呼完成顺序或全局提交游标。只支持本批单一owner与遵循该锁的执行器，不允许旧graph/Deep writer并行，也不声称支持多进程恢复。

开始事件`unified_execution_started`保存schema/executor版本、身份、初始scope/policy、预算配置/来源及triage期初摘要；必须确认该Run无既往统一阶段标记或事件后才可zero-start。第二次begin即拒绝，不因输入相同返回一个新零状态；归属、begin或工件写入失败时外呼0。deadline以DB时间建立/核对，并受上级截止时间约束，保留收尾时间；不通过重开执行器延长。

预留事务提交成功后才允许执行一次对应外呼，固定attempt与输入hash/ref；并行子任务经同一Run锁不能多取最后一份额度/slot。调用结果在完成事务中与输出原文工件、完成事件及state snapshot一起提交；该snapshot含opening triage、stage已知用量、两段聚合总量和分别保留的unknown/unpriced，不另更新Run计费列。snapshot只放状态与小refs，输入/输出正文各存独立工件，不在每个snapshot重复嵌入。工件归属须显式核tenant/run/event，保完整已保存正文hash/字节；M2来源完整hash与其有界正文层次继续区分。

完成同attempt同指纹的重送只确认原回执，不在快照中重复累计；异文拒绝覆盖。完成失败保原未结算预留和留存缺口，不假称结果已持久、不重新查询；若提交结果未知，也不自动重放或释放。本阶段每次已知用量仅计入state snapshot一次，再与显式opening triage合计，unknown/unpriced另列；M3只锁定/读取Run，不更新`total_tokens/total_cost`等计费列、status或completed_at，也不改triage记录或历史工件。旧计费列不能完整表达unknown/unpriced，不能拿它们代替本快照；读取projection留M8讨论。M7统一manifest、正式交付与完成通知不在本块。

### M3.3 持久gate与一次受控工具接缝

M3.1离线直接测试通过才写持久层；M3.2直接合同通过才接包装器。包装器只接受已开始且owner匹配的阶段，经持久预留提交后执行已受M1约束的M2 `activity_records`；开始/预留失败、超限、到期或身份不符时实际外呼0。调用后必须原子完成才返回持久refs；失败交接区分已执行结果与未保存结果。M2泛API仍只做认证tenant/权限及全局bound，本包装器不声称已完成M8生产入口/持久scope授权服务。

最少验证先以替身检查事务中途失败全回滚、并发最后slot、旧seq保留、重复begin与重复完成、未知/无请求/超额及快照内Run两段汇总，并核Run计费列不变；随后受控合成新Run（必要的分诊期初/旧seq也是新测试资料）真实PG验证同样原子性，并只发一次已验M2查询核正确UUID/来源hash及原子refs。所有故障/拒绝对照不发模型或新增真实外部请求，原triage及历史unknown不动；真实读回成功才放行M3。无模型、OS、部署、提交推送，不接完整循环或旧Run恢复。

## 2026-10-23 统一调查M0起步与检索前提

用户已授权逐模块实施，后追加工具影响设计先讨论。沿本change 2.1/3.1/3.4/4.1，预期与实际统一见[逐步记录](../../../docs/operations/unified-investigation-implementation.md)。本轮固定M0只读范围及M1目标合同；M0核既有合成湖事件后，发现其无外联目标，不能代替候选复合场景。main最新7ea813a只有文档变化，测试工具尚无成套历史事件投放。

[工具数据建议](../../../docs/architecture/investigation-tool-data-plan.md)提出复用CH原入湖/typed查询、增加同批告警和真实来源UUID夹具，逐个补绝对窗口/逐条ID/语义字段；OS只按场景接IOC来源，独立测试索引与确定查询路线，原始事件全文/审批另议。该建议尚待讨论，M0未放行，不开始M1代码或M2工具/数据写入；spec中新增M1条款为目标，不是已实现。下文保原批次范围及历史事实。

## 2026-10-23 调查统一设计v3修订（仅文档）

用户确认先修订方案，再讨论是否推进。最新设计以[调查模块规划设计文档](../../../docs/architecture/investigation-planning-design.md)为唯一主入口；本次在基线`3fa4be3`、分支`codex/investigation-working`的独立工作树`E:\aisoc\socai2\.local\worktrees\investigation-working`整理，原目录`E:\aisoc\socai2`中的Windows环境工作及未提交内容留在原处，不混入本设计批次。

本次修订七项合同：

1. 行为性质与业务授权分别判断，未知授权不自动推出恶意，有授权记录也不自动推出行为安全。
2. 可信任务指令与告警、日志、工具返回、知识等来源材料隔离；来源正文不能更改策略、范围、能力或采用规则。
3. 结论适用范围与允许查询范围分开，查询发现的关联实体不自动成为已确认影响对象或扩大交付范围。
4. 小模型按相关问题分组调用；单组输入输出有界，跨组引用与最终综合保留来源，不要求一次输出全案全部结构。
5. 首版建议使用后续调查阶段共享预算：主分析、Deep、领域解释、修复及可选写作共用该阶段额度，Run总成本汇总首次分诊与调查两段；明确预算作用域、期初用量及unknown，不改当前配置数值。
6. manifest统一约束选定的热读、冷读、报告、流式终态通知及主API/Case投影；进度与正式发布结果分开，旧Run状态不能替代统一调查状态。
7. 分别验收模型分析质量、程序安全与交付合同、成本和时延；程序拦截错误并降为partial不计为模型判断正确。

首场景策略卡须留待M0核对实际来源与字段后确定，本次不启动M0实施或真实查询。上述内容仅为设计修订，不新增业务规格、不勾原任务、不启动业务实现/测试/模型/部署或Git提交推送；原5/15、旧失败及unknown保持。本次文档检查与独立审阅回执另行记录，不以方案修订代替通过结论。

## 2026-10-24 M5最小实施合同

M4限定放行后的下一块按M5.1纯任务/参数/去重合同→M5.2持久模型选择→M5.3单问题查询循环及真实接缝推进。第一场景只绑定Q1、一个已选成员和activity_records，程序固定父Run/scope/身份，模型仅给结构化tool/parameters/reason选择；选择不是实际执行回执。参数校验复用M1/M2，不新增任意SQL或后端。后续局部候选仅回答任务问题，保全案其他问题及未知，不形成全案报告。

父M3.begin由调用方负责，Deep不begin/重置stage。首个循环最多一次查询、两次模型选择/回答，仍消耗父调查共同额度；程序任务ID及查询签名稳定，多任务步骤/尝试身份不同。下一轮只能消费留存已确认的有界材料；unknown/留存缺口/到限不重调或追加总结。详细逐步输入输出和实值预期在唯一实施主文档；本段是实施前合同，不宣称M5已实现。沿原责任3.1/4.1分步留证，不新增任务清单完成数，5/15保持，无部署/提交/push，OS后置。
