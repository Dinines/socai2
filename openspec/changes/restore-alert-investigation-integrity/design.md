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

## 2026-10-23 测试工具执行边界

用户随后授权迁移，保调查设计。沿原计划补测试工具与隔离接线，实际回执docs/operations/testdata-migration-execution-20261023.md；旧仅规划说明保留为当时阶段。sender/observer不成为生产接口、调查模型IO或新编排层；测试包装器仅记录并限制传输，原业务源码未改。内容质量/预算/状态展示发现另登记等待讨论，原5/15保持。

## 2026-10-23 测试数据迁移重新规划（未实施）

用户最新要求先回溯原设计再修订规划。详见docs/operations/testdata-migration-plan-20261023.md：原生成/答案分离/HTTP入口与Fusion接线已交付；拟按场景选择及source-v1 wire→Kafka有界发送→3条隔离Fusion→只读结果观察→2例自动分诊/调查推进。保持原工具/业务合同，普通payload不能直接当Kafka source-v1，模板实体/时间及真实检索来源需明确。每步直接验证，模型IO变化另作有界实测；不拓展调查编排/Purple/Honey/全量Replay。

本次只有设计文档与静态检查，不新增规格实现承诺、不执行业务测试/模型/生产访问/部署；实施时再按选定小步补必要规格与执行记录。沿原2.1/3.1/3.3/3.4/4.1，5/15不变。

## 2026-10-23 小范围结果一致与停止交接

验证记录补充：首两次模型请求均503/无回复，原证据保留，用量未知。只读对照确认同一loopback网关经自动代理发现503，显式trust_env=False则健康及五别名列表200。仅观察脚本改用直连HTTP client，另取新合成输入验证两次，仍每次2048/retry0/45秒；不改业务传输/模型配置、不重放原输入。

实施基线为方案提交`5e0ce171`。当前源码含旧C2停止/预算/partial修正，线上v1未全包含；先复用原直接测试核所采用本地行为，不把旧模型失败追认为通过。用户明确只先完成小改动，事件分析和后续架构留待讨论。

1. **人工路径**：在现Forensic节点包装返回时应用一次groundedness，run/stream共用，去掉stream末尾重复处理。新增程序维护的最小validation状态，明确仅indicator_presence检查；Responder/Report读取同一状态。已降级分支保原模型调用及原输出审计，但采用确定性待核/补证计划与现fallback报告，防止自由正文重新确认。保四节点及模型参数；将initial.run_id绑定实际ledger Run，避免结果错位。
2. **工具完成留存**：原loop对每个执行完成的工具生成一次ToolMessage正文，复用同一文本给逐次callback；记录call_id/参数/顶层结构状态、完整序列化大小与hash、实际模型可见有界文本及截断、preview。数据行中的error不等于工具错误。模型消息内容与4000字符上限保持；不复制全日志库。
3. **持久接缝**：在原ledger加窄工具回执写入，事务内保存tool_call事件与tool_result工件，检查Run/tenant和实际插入结果；冲突不覆盖旧回执、明确gap。调用失败不重跑工具，不假称持久成功。
4. **停止交接**：Deep每次完成更新本次结果，finally收束异常/超时/取消前已完成材料、用量与留存缺口；runner仅持有本Run内进度引用，以收尾外层时限造成的取消。普通取消继续传播；不建恢复框架。原报告显示已完成查询/引用、停止原因及待核事项，保空narrative而不把工具JSON当结论。

每个独立改动先直接验证；人工输入要求改变后用当前investigation/report模型各一个全新合成、已降级样例观察实际输入→回复→程序采用，最多两次请求、每次completion沿2048、retry0/45秒、不重调旧Run。若字段采用失败，保留原失败并先修对应接缝再安排不同的新样例；不为了润色重复调用。程序合同测试与模型效果分别报告；标识检查通过不代表语义正确或整体质量验收。

保持现有tenant、unknown、首次结果和预算保护。无新表/数据库迁移、部署或常驻配置修改。第一批仅当前小修范围，余下查询语义、Router扩大使用、事件对象/增量/跨事件设计另讨论。原产品15项不因本批局部完成提前勾整项。

## 2026-10-22 Kafka入口有界真实联合观察

直接合同完成后，补一个当前接点的真实存储观察，不扩业务回归。独立topic/group接收一个新合成fused信封，PG提前保存对应同tenant Alert；不重跑Fusion。Conda本地原worker.start及原schema/prepare，向本地只挂原graph路由的API发HTTP；API正常认证读取21 PG并写21 Neo4j，不跳过schema/权限或用假图驱动。

writer为新本地SECRET_KEY签发的五分钟JWT，按既有合成活跃用户的PG角色/权限认证；reader为另一本地随机七权限服务身份。它们只对本地API有效，不创建21 API key或更改既有身份。保真实LiveShadowModePolicy，禁写策略不可用时不改成假策略。

仅triage入口使用观察接缝：build_state取内部准备回执，读真实Neo4j锚点邻域后主动BudgetHold；原worker拒绝提交并退出，观察不假造分诊结果。核Alert邻域5节点/4关系（Technique可已存在）、无Case边、七RO POST403、GET可读、group未提交；分诊/模型/Run/关闭未执行，finally停止本地子进程。失败、环境补依赖及实际写入数量原样登记；生产代码和部署配置不因探针而改。

## 2026-10-22 Kafka消费入口统一准备告警图

写入触发从可选Alert上下文预取移到FusedAlertTriageWorker._process_with_retry：schema通过后，每次delivery准备一次，再进入原triage及其重试。以_broker_identity取得tenant/canonical Alert，API按PG真实归属读取并投影；不使用消息里的任意图数据或Fusion incident冒充Case。用现有ContextVar隔离并传递回执，build_state仅接受匹配tenant/alert的内部回执，finally复位；信封/模型不能伪造准备成功。

prepare沿AISOC_ATTACK_CONTEXT_ENABLED和独立AISOC_INVESTIGATION_PREPARE_KEYS_FILE，不能借七权限reader写图；review-only、非live writer或tenant shadow禁写保持。HTTP200还须核顶层及projection内部tenant/alert/scope和状态，成功须包含本次source_alert_id。缺配置/政策禁写/异常明确记录，继续原分诊规则，不改原提交/坏消息DLQ与预算保护。这里只保证有配置且成功准备的本次投影，不宣称故障后自动补齐全量图。

fetch_attack_context只GET，自动Graph/Deep不再二次POST；Bundle将本次入口回执随实际查询分开保存到原Run三工件。人工Case的可信API准备不改。API _anchor内部保留已核requested_alert，显式Alert准备只投这一条；解析到真实Case则upsert该Case与当前Alert边，既有边不删。显式Case准备仍保原50条上限，不扩全量回填。

最少直接验证：schema拒绝无POST、准备先于抑制/恢复/关闭/升级、内部重试仅一次POST、tenant/canonical及writer认证、纯GET与回执消费、无配置/foreign回复/只读profile/shadow不写、当前Alert在Case前50之外仍投影。复用必要现有worker/context/API组，不新发模型、启常驻或修改Fusion，不做可用性矩阵。结束由未参与实现者审查并保留本地增量版本。

## 2026-10-21外部HTTP数据接口与Tool验证（仅设计，未实施）

用户要求先讨论第三方检索输入输出，随后明确重点是厂商已有HTTP数据接口，及自己设计Tool怎样接入、怎样证明正确执行。本增量形成docs/architecture/third-party-search-contract.md及导航，沿2.1/4.1交接；内部UnifiedQuery由adapter转厂商原GET/POST，不要求厂商改接口或实现全部算子。给出条件/字段/认证/时间/返回映射和注册→结构调用→fn→真实HTTP→ToolMessage→下一轮输入的验证判据，固定调用/脚本模型证明接线，真实模型选择按需另验。

本轮只设计与文档，不创建已交付业务规格，不改现有API/模型schema/业务源码/配置，不实现或运行Tool/HTTP替身，不连接厂商/发模型/部署。窗口、上游截断、事件ID和call id未贯穿HTTP等当前接缝明确保留。未来实施须先补必要规格/设计/任务，本轮不授权实施；原5/15、worker OFF及旧证据保持。

## 2026-10-21工具文档增量（已完成，仅文档）

用户要求把当前Tool目录、设计、执行、配置和测试方法落到仓库文档，并以“本地没有实际SIEM，假设第三方开放HTTP接口”为完整配置/测试示例。沿本change 2.1/4.1维护交接，不新增产品任务或业务规格；本增量仅文档，无代码、接口行为、运行配置或部署变更，不将本业务change改成skip_specs。

主入口docs/operations/investigation-tools.md，精确目录docs/architecture/investigation-tool-catalog.md，SIEM示例docs/operations/siem-tool-integration.md；含用户追加的Elastic/Sentinel统一条件→ES|QL/KQL→HTTP→返回映射说明。复用当前源代码和有效历史测试/实测，区分16内置/客户/MCP、固定查询与Deep模型选择、占位与缺源、已配置与实际查询、示例与已执行。原预处理文档对Bundle等过时表述只做必要订正。文档引用/示例语法及OpenSpec strict通过，未参与本轮编写者结束独审ACCEPT，见execution/audit；不发模型/HTTP/外部查询、不启worker/复放Run、不做复杂可用性测试或发布。原5/15保持，不归档。

## 2026-10-21链/图接入开始实施（本地，不发布）

用户已明确按既定计划实施、保原算法/流程，本地测通后用一个完整新告警案例解释逐步输入/输出/读取，复杂可用性后置，暂不发布。本次授权覆盖此前“仅规划”限制；原任务2.1/3.1/3.4/4.1记录本批成果，不预先勾完整任务或归档。

必要接口接缝具体化：除计划中的Alert薄链入口，沿graph路由增GET investigation-context读取同tenant链/图资料，增POST同路径仅作有权限的确定性定向投影；复用原算法/upsert/查询，无新表或通用框架。Case调查POST在可信API内投影后启动原编排；自动Alert可用单独配置的tenant写入凭据调用受限prepare，模型及永久七权限只读身份不获写权限。读取与写入凭据分开，缺写凭据明确未投影/回退，不借GET隐式写Neo4j。新接线以AISOC_ATTACK_CONTEXT_ENABLED显式开启，本地开启、现21常驻配置保持。

API返回统一的有界attack_context：明确Case/Alert锚点、原链、CasePath或Alert邻居/影响范围、source/status/error/查询范围；Agents Bundle显式采用，默认/Router/Deep原模型调用不增加固定步骤，按Run保存attack_chain/attack_path（Alert图另型）工件及实际摘要。真实验证只用本批新Case/三告警和必要控制，优先跑默认四节点一个完整案例，最多4次模型请求、每次completion2048/SDK retry0/45秒；失败不自动重试。必要直接测试覆盖其他消费接缝，不跑三套模型矩阵。旧失败/unknown、算法、预算、工作者开关与正式topic保持，无部署/Git提交推送/厂商动作。

## 最新规划：攻击链/Attack Path接入调查（2026-10-21）

用户本轮要求规划，并询问是否只是既有功能未开启。已核原算法/查询/图写入函数和配置都有，但固定原版及当前Case/告警业务均未自动调用图投影；Router/Deep与Case路径材料也未完整交接。不是只翻开关，也不是迁移时删掉已有自动图逻辑。详细实施顺序与最少验证见[专项计划](../../../docs/operations/attack-chain-path-integration-plan.md)。

沿原2.1/3.1/3.4/4.1及B5：先已有Case/同tenant输入与可信PG材料，调查准备阶段定向复用upsert补图，原Attack Chain/Path预取一次，有界摘要进入默认/Router/Deep实际模型消息，原G4复用材料；按Run事件/工件与Markdown交付。不合并编排、不改链评分/时间默认、不新建raw采集或图平台，不新增固定模型调用。直接缺口只修Case/Alert/tenant交接、当前投影的节点/边ID和来源状态合同。模型不可写图，原写接口权限不扩大。

本批先Case调查，再接自动Alert起点：无Case或Case关联有歧义时，候选链通过计划中的薄Alert读取入口调用原seed算法，图上下文复用已有Alert邻居/影响范围；Case专用路径明确not_linked，不伪造Case/改写旧Run。薄入口是本次明确的必要接线增量，不称已有开关。计划规定代表三告警Case、原直接测试、一个代表真实模型消费及按Run读取；复杂恢复/冗余/压力、全库回填及模型质量矩阵后置。

**当前仅规划和只读源码核对**，未改业务代码、开关、写数据库/图、发模型或部署；原5/15不变，不创建另一套产品任务树、不归档未完成change。此前78项和31995tokens是上批实测，不能用于追认本计划实现。

本批默认调查另真实复现单项IOC增强HTTP400：Agents发送type，原Go服务要求ioc_type。沿3.1同批只修这一请求字段（保原工具签名/返回/固定增强流程），复用已有直接工具测试并以一个保留文档域名经现有无provider服务验证HTTP合同；不重跑模型、不改IOC提取算法、默认端口或开启厂商来源。原400及报告保持，单项/批量增强分别记录。

### 本地实测发现的最小功能修正

本批Deep真实请求已穿过认证/API到ClickHouse；authentication_events原SQL以IPv6列source_ip比较空字符串，真实query_log确认CANNOT_PARSE_IPV6。沿3.1/4.1仅修该参数化查询与IPv6空值合同，复用原直接测试并追加该SQL回归；不改表/算法/占位后端、不部署。模型旧结果不重调，本地原查询函数借21已有只读湖仓验证一次新查询；其余缺源/预算和质量问题记录后置。

## 最新增量：调查模块本地功能实测（2026-10-21）

用户已要求开始测试，并同意真实部署样例、公开案例和新隔离样例均可使用。本增量覆盖此前“仅文档/不发模型”的阶段限制，沿原2.1/3.3/3.4/4.1记录，不新增产品任务树或预先勾完成。先复用Router 12项及Deep 8项直接测试，再本地运行原默认四节点、Router与Deep各一次，使用21既有模型网关及只读查询服务，保存各步真实可见输入/输出、工具请求/返回、usage与Markdown；不把替身测试当真实模型/工具证明。

20仅有已调查的Golden pipeline样例，本次只作历史对照，不重调。公开事件只取官方叙述事实，测试实体/字段明确标为派生或合成，不伪称原始日志。三种路径先用三条新输入；Router首例因明确lab来源在分诊即关闭，另加一次独立公开事件叙述以观察领域分支，四个新Run累计最多16次模型回复，每次completion沿原2048上限，SDK测试进程显式retry=0/timeout=45秒，Deep沿原6轮/120秒及20k预算接缝；累计观察usage达60k即不开始后续路径。所有执行逐路径串行，不为得到预期答案重调。无DATABASE_URL的本地组件测试只保存本地工件，不声称新增生产Case/Run持久或Kafka自动触发已验；原主链证据另引用。

不改常驻worker、部署、正式topic或旧unknown/积压，不做厂商动作、全链恢复/可用性矩阵、PDF/HTML专项。仅准备一次性观察脚本，不改变业务源码；如发生当前主功能阻塞，按原change先记录最小差异再修。结束做一次未参与实现者审计，保留本地版本，按阶段发布，不自动提交/推送Git。

## 当前分诊与调查分析的实施切分（2026-10-21）

用户追加要求预处理、工具决策/执行及每次模型目的/输入/输出详述，交付[专篇](../../../docs/architecture/investigation-preprocessing-tools.md)：按真实入口投影/字段裁剪、固定查询、Router代码领域路由和Deep结构化tool_calls分开；逐模型表与静态JSON/HTTP/ToolMessage示例用于解释，不冒充新实测。Case嵌套/真实时间默认/参数校验边界仅记录，未决定改变输入或新增框架。当前无规格级行为变化，沿2.1/4.1分析交接，原任务及运行保护保持。

本轮讨论澄清同步至调查说明/评价：Case `/investigate`用Router开关二选一，Kafka graph/deep保持独立；Router专业分支一次领域模型，不内含旧四节点，其确定性响应摘要/报告不能作完整取证/响应计划等价替换。graph外层控制仍固定，模型主要在deep内部选择查询。固定官方未找到旧四节点弃用计划，不据演进先后预定替代/裁剪。本增量仅说明原实现，无新合同、实现、配置或完成承诺。

用户最新强调调查设计本身很重要：[专项评价](../../../docs/architecture/investigation-design-review.md)对比默认Case四节点与graph/deep目的、输入输出及四Agent的分工价值/限制，并核固定官方路线/变更日志/Case文档。将官方陈述、当前调用和工程推断分开；证据支持演进并存，不将自动/人工等同两套必须串跑的架构，不由文档设计意图追认实测质量。当前先分析，不实施合并/裁剪或新模型比较。

Fusion阶段后先交接[分诊](../../../docs/architecture/triage.md)的实际字段、规则/模型、策略关闭和升级，按原支持/默认/当前配置/实证分别列；不预定接入所有Fusion字段或按route_to切换编排。调查按[逐调用说明](../../../docs/architecture/investigation.md)区分自动post-triage graph、默认人工四节点及Router/full；每步明确触发、实际输入、模型角色/可见提示、工具服务/查询参数、返回采用、分支循环与结束、审计/持久落点。可变deep调用用原C2的真实逐轮记录举例，不把六轮上限当固定六阶段，不索取隐藏推理。

推进顺序为原机制交接→共同功能取舍→只针对确定差异的最小修改→复用直接测试/必要本地联动→一次结束独审和本地版本→阶段发布。当前仅前一项分析/规划，不做业务修改、测试/模型、线上核验或发布；新行为届时补现有规格/设计，沿原15任务记录，不先增加全入口测试、通用审计框架或可用性矩阵。原报告/预算/partial失败与未部署源码修正分别标明，不能由本次说明追认为已通过。

## 此前真实联合验证（2026-10-21）

**用户最新执行位置与发布节奏覆盖下文初案：** UEBA/Fusion原源码在本地进程运行，连接21已有PG/Redis/Kafka做真实联合验证；不在21启动临时业务实例、不上传本地源码。通过后先保留本地版本/测试回执，需要时构建本地镜像；按阶段统一发布，不因每次更新或测试通过自动部署21。本批无发布操作。下文临时Fusion/UEBA均改指本地独立进程，独立topic/group及原样本/真实结果核对方案保持。

用户明确要求联合验证，补原8个内存边界例子未覆盖的UEBA实际评分→真实Kafka→Fusion。仅在21运行已有UEBA/Fusion镜像及原类，不上传本地业务源码、不改常驻容器/全局Agents开关。使用已有受控测试tenant A、三个唯一实体和独立短期topic/group；以原BaselineService.update为每实体录入30个80/120交替样本，再各经原UEBA Kafka消费者处理一个outlier，验证medium/high/critical真实PG异常及消息、Fusion缓存和真实告警保存/发布。正常控制和关闭联动控制各一条，所有source ID新建，不重放旧unknown或正式topic。

临时Fusion显式禁用raw归档/提升/检测及不相关RBA/chain/prior，使用原真实PG/Redis/Kafka配置和既有只读CA；临时UEBA只订阅本批输入。真实数据以本批前缀和ID留证，不对旧记录计数/冻结或清理；完成后移除临时容器及含凭据的临时环境文件，保留可核对结果。不得用直接写假异常或调用HTTP score代替原Kafka消费者真实生成/发布，不扩到模型或长期可靠性专项。

## 当前UEBA/Fusion联动例子（2026-10-21）

用户已要求实际跑几例联动评分，并写清加分与开启/关闭配置。本批沿2.1/4.1增加最少功能验证：关闭、开启无信号、medium/high/critical、多实体取最高、跨tenant及实体不匹配，共8个例子；复用原10项UEBA信号测试，不扩可用性或长期基线专项。例子运行原FusionWorker异常消息分支→UebaSignalCache→FusionEngine及原启发式/置信度，PG/Redis/Kafka交付使用已有内存边界；不得写成真实broker、常驻启用或UEBA新异常生成已验。原计划上传源码至21隔离容器被自动审批以私有源码跨主机传输拒绝，未执行；改用本地临时venv和公开依赖，不上传源码、不连接业务服务、不改21常驻配置、不发模型或正式业务输入。文档记录实际分数及配置应用/续期/先后顺序边界，原代码和旧证据保持。

## 当前UEBA增量：按上游投喂触发

用户澄清按原设计由上游决定哪些事件/实体送入UEBA，本批只讲清触发格式和配置接缝，不新增实体名单控制或滑动窗口算法。当前共享输入topic是`socai2.raw_events.v1`，主接入样例使用含`tenant_id/event_id/ocsf_event`的v1信封；UEBA从user→device→ip固定择一，提取数值特征后按旧基线评分并更新。纯预提取消息是UEBA原兼容合同，`event_id`映射为内部source_event_id，但同一共享topic的Fusion要求ocsf_event，不能将其当共享流的通用消息。

直接HTTP `/api/v1/ueba/score`由调用方给`entity_type/entity_id/features/source_event_id`，需要原服务认证与tenant绑定，只评分/持久，不发布Kafka异常。说明包含正确JSON实例及基线/异常输出，保留冷启动unknown、累计统计和现有算法；原122项/基线消费回执复用，新说明仅作必要的零服务解析核对，无新复杂测试/框架。细节见[UEBA模块说明](../../../docs/architecture/ueba.md)。

## 2026-10-21二开分析方式（最新）

按用户最新说明，本轮先规划并记录整条路线及讨论点，后续先共享支撑能力：UEBA → 威胁情报/IOC → 20上一版既有知识库，再进入Fusion → 分诊 → 调查/攻击路径 → Markdown交付。UEBA重点实体启用及基线/时间参数、输入输出、偏离算法；IOC先做命中/未命中查询，暂不考虑数据量；知识库历史经验后看。基础属性表、工作卡及纪要见[逐模块设计](../../../docs/operations/module-review-plan.md)，顺序表见[总计划](../../../docs/operations/completion-plan.md)。当前仅规划/只读核对，不改变运行、业务合同或15项完成状态；具体新行为在模块范围明确后按OpenSpec实施，不合并原编排或新增全平台前置。

2026-10-21最新报告范围：当前只交付Markdown生成、持久及读取；PDF暂缓，HTML非本轮前置。复用已有有效MD证据，不增加报告模型/格式专项，既有代码和历史结果保留。

## 当前阶段优先口径

2026-10-21用户最新收窄：先接通告警正式输入→Fusion/持久化/分诊→无需人工再点的实际调查/工具知识→基本结果报告和关联记录可取。已有B4 case02可复用作第一步证据，partial/缺源/质量失败保持，不把全部B1—B6或其他入口/分支设为前置。算法/模型、报告、deep/用量完善及复杂可用/冗余校验迁移后评估；停止反复组合、全量hash水位计数冻结、多轮审计和验收框架。已修代码保留，只有源码/依赖/配置接口缺口致主链根本无法执行或结果取不回时当前最小接入。下文原设计及质量修复是历史实施记录，后续排期受本节覆盖。

## Context

评估和来源核对见[assessment.md](assessment.md)。源码保留完整，完整功能目标却与旧review_only/白名单开放面不一致；发现I2/I3组合缺陷和I4继承缺源语义问题。用户已在完成范围讨论后授权开始执行并允许并行worker；本change按B1—B6实施，不能用旧“仅规划”阻止已授权工作。源码理解、官方功能对照及二开架构梳理与实际迁移同步进行。

## Goals / Non-Goals

按固定上游完整迁移告警/调查，包括自治能力；保留必要本地修复，用少量代表业务验证确认输入→实际调用/材料→最终关系。playbook/反馈原样保留并后置额外工作；可用性专项登记，不先做启动退出恢复矩阵，不迁前端/采集/检测，不更换编排框架。

补充总原则：所有一体模块/依赖都可整体原样迁入，不额外修改或测试，playbook/反馈不是唯一适用项。不为拆分、美化、额外封装或统一架构改造上游；对本次未变的依赖不增加专项验收。只修直接缺失功能、正常业务结果错误和实际接入必需项。

## 2026-10-21 full配套原版迁移

沿已有服务关系迁入services/enrichment、services/threatintel、services/ueba的固定上游tracked原件（含模块测试、锁、构建和UEBA自身迁移），不覆盖已适配API/Fusion/Agents。ClickHouse DDL、Neo4j运行迁移及原Compose参考已存在，只补缺少的图声明资源。沿已有PG/Kafka/Redis、ClickHouse/OpenSearch/Neo4j接线，不新增框架或替换存储；按用户最新要求，以最少已有模块测试和实际基本调用核可运行性。外部厂商凭据/Feed未配、没有历史事件输入、原版not_ingested或未接全文索引等，分别记录，不伪造真实数据或补做新后端。复杂运行恢复、模型质量和暂未使用模块的额外验证仍后置。

## Decisions

F1—F5为问题类别，不是要求全部串行完成的前置；实际顺序以[总执行计划](../../../docs/operations/completion-plan.md)B1—B6为准。B1处理F3，B2处理F1默认入口和F4工具，B3处理所用知识，B4处理F2正常结果及F5完整自动链，B5补F1其他入口/输出，B6交付。默认调查无需等所有路由恢复，自动调查也不依赖所有兄弟入口先完成。

1. 按“源码完整、功能被挡、依赖未接、实际缺陷”分流。1578原件均存在、未丢路由声明，不回退source-v1、null风险分、tenant reader或交付保护。
2. **F1：核现有入口/依赖清单并解耦身份。** 复用已有清单，在investigate中把Case所属tenant检查与AISOC_SCOPED_BASELINE解耦；恢复router/graph及报告等所需功能前核Run归属。保留未专项的一体模块/真实响应边界，不直接关整个baseline放行所有路由，不另建入口治理框架。
3. **F2：优先修正常调查的用量/结果组合。** 先修现有graph.complete_run调用参数和汇总口径，避免正常graph完成将已有用量写零或使分诊结果拒读；保持首次材料与现有防重复调用保护。优先使用已有Run/事件/工件，不预先另建阶段账本、关联Run层或通用恢复框架。仅warm/cold、故障重投后调查接续等可用性问题登记暂缓；若在本次实际业务路径直接造成调查缺失，再按功能缺陷最小修复。验证仅核正常升级及其实际结果/用量，不展开恢复矩阵。
4. **F3：修融合入口组合。** 按原入口声明的完整处理语义保持FusedAlert外部响应，通过共用必要处理接缝统一HTTP/Kafka的身份、首次结果和tenant约束；不另创预览模式或保留共享dedup却不同持久结果的分叉。只补两入口顺序与跨tenant直接验证。
5. **F4：接实调查上下文。** 补默认/自动调查实际使用工具的认证和可用数据源，区分error与合法空结果；知识向量模型/维度/集合按所用路径最小对齐，核实际召回进入报告的可解析引用。缺外部日志等如实partial，不建设采集替代物。
6. **F5：恢复完整自治与自动调查。** 在该自动路径所需的入口/身份、F2正常业务问题及实际使用的F4工具/知识满足后，由真实告警触发自动分诊、按策略关闭或无需人再点的升级取证/知识查询/分析与可查结果/报告。不得以仅创建Run或人工调用triage代替；不等F1所有其他入口都完成。不为拆开一体的playbook/反馈改其代码或增加专项测试，只核当前变化并复用已有证据。原graph若缺必要持久/报告出口最小补接已有机制，R01原实现/证据保留，不能简单切legacy/删guard视为通过；旧质量失败不改；在本批必要受控功能验收前不提前启用，满足后按既有执行授权定向接入，真实厂商执行仍受授权约束。
7. 记录R02暂缓侧附文件，不改原五个计划文件/hash、0/17或将其归档。继续维护最小OpenSpec任务和独审，不扩为每次SQL/metrics都重新冻结的仪式。

## Risks / Trade-offs

2026-10-21讨论勘误：用户讨论原设计，不是新增等级触发需求。原playbook已有severity/tags匹配和investigate步骤，worker另有未关闭后升级；详见总计划的原版触发说明。撤回上一轮新增规则合同、优先级和命中/未命中/停用专项要求，不扩改原编排；playbook整体保留、额外改测暂缓，原B4任务不变。

- 全量解除临时限制连带撤销身份/开放副作用 → 先解耦身份和效果，按完整功能矩阵恢复。
- 保留持久保护却丢自动调查阶段 → 修阶段与usage关系，不退回重复调用模型。
- 将上游缺陷误判本地损坏 → 每项记录归属、方法探针与当前禁用边界，不声称21事故。
- 暂缓被误作通过 → 记录源码/接通/验证/启用四状态，playbook/反馈及可用性仍标未验。

## Migration Plan

评估/总规划已完成，用户已授权开始实施。当前按总表B1—B6推进最小功能工作，复用证据并仅补当前必要业务验证；B1与B2独立部分并行、B5盘点可提前。普通启动并观察真实告警自动消费属于功能接入，不重引R02常驻/恢复矩阵。运行变更只说明实际影响，不重复旧全量冻结；旧数据/unknown/预算/回执不覆盖，真实厂商副作用授权不变。

### B2/B6 正常报告正确性修复

真实新Run `7bc46722`完成默认四节点并记录8062 tokens，但报告质量未过，原结果保留，不重复调用旧输入。此为正常材料/结果接缝修复：只提升默认recon/forensic/responder/report四个system prompt版本，区分事实、假设、未知，缺日志/图/增强不能推断无入侵，测试标签不证明授权或规则误报，响应仅提案/dry-run；triage v5、其他18个prompt及schemas保持。

Report沿现有有界serializer补现有timeline条目、recommended_actions及源Alert时间/事实，避免只传数量让模型补造。保留completion上限，要求简洁且各节完整；仅按实际finish_reason=length识别截断，保留原响应/usage，交付清楚标明截断的完整回退报告，不自动重发模型，不用文本启发式宣称结论正确。KB未引用按原实录，不补造引用。验证只补材料传递、缺证与截断直接边界；0真实模型/部署，随后由root另冻新正常输入并由未参与实现者独审。

截断或调用异常保留报告工件供读取，但state.status为failed且error明确原因；REPORT事件以generation_status/report_source区分模型正文与fallback，不新增state schema。原调用响应、usage及实际marker记录保持，fallback不附加被替换正文的引用列表。运行原有1024配置与源码默认2048分别记录；旧输出未保存finish_reason，不能追称length，后续有界配置调整由root实施。

真实内容独审另确认Forensic把仅含error的enrichment cache按truthy当作证据。追加单文件最小修复：保留错误详情，显式只把成功且有实际内容的增强当证据；无primary材料且增强全失败时继续走原inconclusive gate。prompt明确失败不是取证观察、KB通用定义不是本案事实，不改工具服务或新建来源框架。


### B4实际调查结果的最小修正

C2技术材料成立而质量失败，保留原Run/判据并停止后续输入。原始告警材料仍在state但deep旧字段摘要漏传，故沿source-v1已有账号、正文/raw_event、发生时间与显式null进行有界投影，不让Fusion评分摘要代替原事实。知识映射只记为ATT&CK候选，不产生observed attack/single-stage覆盖断言；风险/关键词prior本身不确认事件，失败/缺源也不能推断误报。独立成功资料和原结论分别保留。

原六轮cap不抬高；最后ToolMessage不是模型结论，达到cap或预算时交付partial/未知并保留实际已发生的调用和用量。复用原CostTracker及graph预算，把实际模型用量接原governor；已返回的一次reply可以跨越剩余额度，随后立即停止，不能继续下一模型/工具调用。原始分诊快照与graph结果/增量继续分开，旧Run不回填。只补本次变动的直接测试，由未参与实现者审计；不新建恢复框架或全来源专项。

关闭兜底finding修正仅涉及原因文案：不在原可关闭类别时明确类别原因，只有真实低于实际tenant阈值才写小于；关闭决策、策略阈值及保护不变。默认报告candidate05是独立的两文件投影修复，不与这些尚未发布的graph/deep变更混同。
## 依赖项交付简化（最新）

用户明确依赖保持原设计，当前仅要求基本功能可用以及“有哪些功能、如何使用”的简要说明（必要配置、入口/样例、输入输出）。复用已完成UEBA说明和既有运行证据，不再增加依赖原理分析、算法改造、复杂测试或专门设计；只处理阻碍实际使用的接线，其他问题登记后置，原代码/测试/保护保留。详细改造在后续二开时再做；本次不新增业务合同、任务或运行操作。

## 当前依赖增量：TI/IOC与KB使用说明

按用户简化要求，仅补[依赖使用说明](../../../docs/operations/dependency-usage.md)，复用full已有查询/接口与知识读取证据，不改API/算法/部署、不新增规格级行为或测试任务。20仅只读确认原项目文档KB表为空及相关Qdrant集合存在，不读取正文、导入或调用模型。原TI OS搜索没有tenant过滤的实际边界只登记，不把认证头当私有隔离；本轮按共享公开情报入口说明，原租户PG路径保持。后续进入Fusion，遇实际使用阻塞再按已有任务处理。
## Fusion当前讨论范围：先解释原功能

用户进一步明确，先弄明白Fusion到底做什么，再共同讨论需要/不需要哪些功能。[功能说明](../../../docs/architecture/fusion.md)仅盘点已有告警主链、normalized事件支路和辅助接口，解释身份/关联/评分/候选链/Case边界及输入输出。本轮不预定promotion修复、UEBA启用或任何删除/改造，不修改行为或运行；取舍明确后再写对应最小设计及必要规格/验证，继续沿2.1/4.1记录，不另建任务树。
# 2026-10-22 测试数据工具接入（用户授权增量）

用户要求把上游数据生成/测试能力接入并做一些测试。本批沿2.1/4.1复用固定上游34ca18c的demo-producer原件和合成场景生成器；新增独立测试适配器，将场景转换为本项目ExistingAlert/source-v1合同，预期技术/处置及评分材料单独输出，不作为raw_event或模型输入。原版producer仍面向Ingest，保留源码不等于已经适配或运行；本批使用项目告警适配器。

先做无网络生成与直接API/Fusion合同验证，再用少量全新合成告警、隔离topic/group和本地处理代码验证实际受理/持久/交付（如基础设施可用）。生成默认不发送；发送必须显式指定端点、认证、租户及有界批量，逐条记录accepted/unconfirmed，不自动重试；202不等于Fusion完成。直接测试中的PG/Redis/Kafka替身与真实基础设施结果分开记录。

不改业务算法、模型提示或原数据，不迁Ingest/raw检测支路，不启动Purple Team/Caldera/Honeytokens或常驻Agents，不调用模型、不部署或重放旧输入。范围是测试工具与本批直接验证，不承诺分诊/调查质量、关联算法质量或性能。结果、失败、源码来源及未参与实现者独审单列回执，原5/15与旧质量失败保持。
## 2026-10-24 M5最小实施合同

M4限定放行后的下一块按M5.1纯任务/参数/去重合同→M5.2持久模型选择→M5.3单问题查询循环及真实接缝推进。第一场景只绑定Q1、一个已选成员和activity_records，程序固定父Run/scope/身份，模型仅给结构化tool/parameters/reason选择；选择不是实际执行回执。参数校验复用M1/M2，不新增任意SQL或后端。后续局部候选仅回答任务问题，保全案其他问题及未知，不形成全案报告。

父M3.begin由调用方负责，Deep不begin/重置stage。首个循环最多一次查询、两次模型选择/回答，仍消耗父调查共同额度；程序任务ID及查询签名稳定，多任务步骤/尝试身份不同。下一轮只能消费留存已确认的有界材料；unknown/留存缺口/到限不重调或追加总结。详细逐步输入输出和实值预期在唯一实施主文档；本段是实施前合同，不宣称M5已实现。沿原责任3.1/4.1分步留证，不新增任务清单完成数，5/15保持，无部署/提交/push，OS后置。
