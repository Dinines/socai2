# C03-R：review_only_v1 人审限定准入

2026-10-21。执行范围卡；root冻结采用后按本卡实施，尚未实施/验收。范围冻结不等于准入通过。本卡细化原迁移路线3A的另一条限定准入合同，不追认旧自治C03质量门通过；当前运行仍为D1镜像、27Compose/24来源层、worker OFF。正式采用须由独立审计与root adoption.json精确绑定；各小批另须对应独立准入审计，不能把范围冻结写成运行验收。

## 依据与交付口径

用户已授权按当前告警及后续处理服务端范围持续迁移、修主链阻塞、每个change结束独立审计，并统一登记暂缓原有非阻塞问题。这允许选择可明确验收的有限基线，不允许隐藏失败或把未开放自治能力写成通过。沿用[完成计划](completion-plan.md)和[服务端路线](service-roadmap.md)，不扩前端、采集、原始检测、全厂商或任意工具。

[D2](c03-triage-validity-quality.md)两次真实回复4081 tokens：case01反证FP分类/理由通过；case02时区换算错误并把窗内已授权活动判FP，分类与理由失败，case03/04未发。D2收尾、撤key后及封后审计只认可受控停止；原始回复、独立判据/gate=false、三枚key真实401及旧失败材料保持。没有已证的更强43路由，不以换未验证模型或继续重调旧例冒充修复。

D2公开交付已闭合：28个公开文件、远端573项索引、769运行Py及lock核对，交付后独审accepted。交付完成不改变D2质量失败，也不增加运行来源层或给予本卡执行权限。

选定目标为 **review_only_v1 限定迁移基线**：真实模型仅交付可回查、明确未审核的建议，所有有效决策进入needs_review人工队列；模型不能关闭告警、触发后续工作或写回经验。Q1是已经观测的模型分类/理由及gate能力缺口，未证明纯上游归因。只有本卡的代码隔离与运行验收通过，Q1才对**实际禁止的自治能力**条件延期；自治质量仍未过，原自治C03-02/03门不删除、不降阈值、不改历史判分。

## 新结果合同

- 原模型verdict/confidence/rationale、完整可见短回复与hash、输入/usage/调用身份保留为 `model_advice`，标 `unreviewed/advisory`。SDK可见的egress-restored内容不冒充provider原wire。没有成功回复则model_advice为空，不把确定性fallback当模型建议。
- 新 `effective_decision` 固定needs_review、confidence=null、review_required=true，并记录profile/version/Run/tenant/canonical Alert及来源hash。模型自报分数不成为有效置信度。若原Run/event数值通路保留0兼容值，必须有policy-sentinel标记并与effective null及原模型分数分列；**canonical Alert的全部AI字段/状态/disposition/recommendations均不写**，不用ai_score=0占位。
- Run completed/持久确认只表示这一次有限材料和建议已交付，不表示人工审核、判断正确或Case结案。完整raw与effective边界由绑定的版本化receipt及现有JSON工件承载，不能让下游重新把raw FP或.95当动作依据；不改现有公共route或LLM输出schema。旧timeline/简化projection可能仅显示effective needs_review与数值0兼容sentinel，rationale必须明确effective confidence unknown、0不是模型估计；不宣称每个旧投影都新增nullable confidence、profile或完整raw-vs-effective字段。
- profile由部署固定，默认配置值仍为legacy；未知值拒绝，不静默fallback。`review_only_v1`只能采用已经受持久delivery guard保护的ordinary Kafka Live及其既有Shadow包装。相同scope还须由worker内部标记，用户/模型字段不能选择profile。direct triage/replay/direct agent等未受护入口实际hold/禁用，不能绕到legacy自治；其后续开放另验。
- 在agent closure/QA之前、worker playbook/graph/审批/写回之前逐点阻断。memory prior suppression、跨告警pattern复用不能绕过profile；显式tenant policy suppression若遇到则typed hold，不偷偷忽略既定策略后继续模型。仅设最终NR、shadow或env OFF不算代码隔离。
- warm pending、cold PG首次结果必须原样保留本profile/version/建议/有效决定/来源/usage及无效果receipt。旧FP/BTP、旧无标记snapshot、profile漂移和started/unknown必须hold；不改写旧事实、不补填新profile、不重调模型、不把unknown变成NR成功。

## 不可降级的后续合同

C04仍须同Case/Alert/Run、已认证真实只读工具、完整必要报告及证据引用、失败/unknown和重启持久回查；C05仍须真实向量空间/来源→召回→同Run实际采用→可解析引用，质量与缺源区分。advisory标签不能替代这些验收，空/半份/无据报告不算完成。

C07仅显式人工发起且强制dry-run；C08仍须tenant、请求人/审批人、自批/越权/目标参数、PG暂停继续与dispatch逐项确认。C09执行/验证分别存，unknown不自动重发；真实厂商动作仍要明确目标、授权与批准。模型自动graph、playbook trigger、审批提案、QA、source/outcome/memory写回均在此profile之外。人工结案/反馈及受控dry-run的授权接口不因本卡获得豁免。

## C03-R01：零真实模型的代码隔离与定向部署

父为D1源码来源 `057993d4a2710182c79c33385563fca8bcf86a0f60f0f4bc8f0663cfbb43a612`，承接D2已封存的实际状态。最多五个runtime落点：新 `workers/triage_admission.py`、`models/state.py`、`agents/auto_triage_agent.py`、`workers/fused_alert_consumer.py`、`investigator/ledger.py`。ledger第五触点仅用于严格验证profile receipt并跳过整条canonical Alert UPDATE；旧legacy/triage/C04接口不得顺带重写。确需第六文件时先列具体调用阻塞与最小理由，重新审范围，不自动扩展。

本批不改prompt/lock、factory/SDK参数/egress、LLM输出schema、route、依赖、DDL或预算算法。只运行最小直接测试与候选source/mount校验，不重复父版本四次SDK传输：父同baked SDK/提示/egress证据可以继承，新增profile分支的真实PG/Kafka/reader与有限常驻留R02验。

最少直接边界：

1. 真实agent/worker接缝的受控回复含FP/.95及其原理由，closure允许、QA采样与所有effects flags/ports均打开时，原建议/hash保留、effective NR/null；close、QA、graph、playbook、approval和各种写回调用为0。
2. Live/既有Shadow、确定性无回复、direct/replay拒绝、非法/漂移profile、旧/缺snapshot与unknown hold；费用/预算确认和普通live缓存禁用保持，不加新writer包装破坏delivery guard。
3. 一次持久失败与pending/cold首次结果恢复，0额外模型；确认工件后才commit。ledger必须不执行canonical Alert UPDATE，先置有辨识度的AI字段原值并核完整保留，不能只在全null行上证明“不变”。legacy原行为直接测试保留。

先保存有限只读PG/metadata/容器快照及父hash，再cached network-none、source RO、dummy credentials/空DSN运行直接测试；由未参与实现者审源码、结果合同、失败边界和证据。新operator不导入旧prepare/finish取常量，避免全局计数hook。最多一次build、一次仅Agents容器recreate；失败保留检查点，不盲重试。

overlay仅Agents新image和 `AISOC_TRIAGE_ADMISSION_PROFILE=review_only_v1`；所有worker/effects开关仍OFF，原七只读bind、60秒停止宽限保持。新1Py预计Agents185/总770，预计28Compose/25来源层；这是计划值，须候选与实际镜像独审核对后才能写已完成。recreate时只读核host当前A10/B4 policy的字节hash、device/inode与容器实际挂载内容一致；不能仅看路径，也不能宣称已验证live预算实际采用。

退出：直接测试、候选绑定、部署前与运行后独审通过，只有Agents被替换，35其他容器/18卷/134迁移和旧业务材料保持，worker仍OFF。R01通过只证明隔离实现与指定部署，不证明新profile常驻、reader消费、PG/Kafka新分支或模型质量通过。

## C03-R02：独立有限常驻与首次结果恢复

只在R01封存后另冻具体新输入、operator、资源、启动/停止步骤与独立准入门。**不得复用旧四例、旧自治resident draft或其执行授权**；A/B各一条fresh中性身份输入，新source/rule/host/user与既有失败材料分开。新的验收针对建议持久交付与无效果，不改旧样例分类oracle，也不把raw错误翻译成质量通过。

预算上限固定：当前host policy A为86400秒/10calls/200000预留单位/3unsettled；B为86400秒/4calls/80000单位/2unsettled。当前观测各剩一次，但正式发送前须按真实DB时钟、滚动窗口、全部旧预约和unsettled重核；本卡不是额度凭证。最多A一次+B一次真实SDK调用，合计≤2、预留≤40000单位，禁止增额、退款、删除/过期unknown或把未用旧额度当自动重分配。余量不足、调用状态不明或边界不清就停止，不补第三例。

保留旧12预约/240000单位/3unknown完整原行；十reader保持，不借reader作ingest凭据。若需新A/B操作key，上限各1且权限最小，结束逐枚停用并真实401；不新增tenant/reader/closure policy。新告警/Run≤2、事件≤6、工件≤14、cost/shadow≤2、预算行≤2；QA新增0，canonical Alert全部AI字段原值保持，动作/审批/记忆写回新增0。若某种原记录因所选入口确需不同数量，必须在R02业务前独审更正明确上限，不能事后放宽。

有界窗口建议≤10分钟，operator不得循环发样例。仅新operational group消费既有fused topic：

1. worker停止时封存真实main fused topic每partition当前end。原 `socai2-agents-triage` 三个partition的commit=None和当前90条历史保留；旧6预算组/4质量组及其DLQ均不动，届时有新增既有组也纳保护。历史区间显式排除，不声称积压处理通过，不附加旧归档/模型重放。新review-only operational group在未消费状态显式commit冻结end；不能拿`auto_offset_reset=latest`代替起点。
2. 核本项目窗口物理输入仅这两条；未纳入tenant/identity或无关新offset出现立即停止，不继续reader/模型/新业务写。若不能证明这一入口边界，不启窗口；不为此建设通用allowlist框架。逐tenant reader真实认证/缺源语义与预算须在该候选/容器实际采用。
3. 常驻必须由服务 `main` 的真实startup启动worker，核正确的新group、subscription/readiness、有限watchdog与正常stop，不用只调用triage方法替代。启动前重建Agents容器并核policy bind device/inode/hash及实际profile/group/source；即使R01已挂载正确也须确认期间没有atomic replace。旧常驻容器可能仍绑定旧inode，不以host A10文件存在声称resident已采用。此为容器recreate，使用同一R01镜像，不二次build。
4. fresh A/B经真实HTTP/Fusion/PG/Kafka→resident→Run/API，保实际raw建议/effective NR/null/来源/usage/成本与无效果关系。SDK retry/45秒及预算仍按父合同，0额外模型用于重投。新profile下任何模型建议含错误也保raw、保持未审核；只能验隔离合同，不因此放宽报告/来源身份。
5. 在本批连接/consumer上冻结一个定向保存/确认故障接缝，证明未持久确认不越过offset、warm保存恢复；用同批已经完成的PG首次结果进行fresh-process Kafka重投/重启回查，保持同Run且0额外SDK。故障只作用本批，不停止共享PG/Kafka、不新DDL。若真实SDK是否已发/回复不明，保留unknown并结束，绝不为补“恢复通过”重发。
6. 最多一个停止→fresh进程启动的恢复周期，最终明确OFF并核无消费任务/inflight；启动和最终OFF所需的同服务配置/recreate次数在R02 operator冻结时列明。所有旧组offset/旧unknown不变。原main group不seed、不回退；新group只推进这两条范围，超界立即停。停止/恢复证据必须来自本profile，而非旧自治draft。

R02不新增产品源码；临时启用配置、总HTTP/SQL/发布/物理读取上限、故障接缝和最终OFF定义须在发送前具体绑定，不能凭本规划启动资源。结束核旧材料、35其他容器/18卷/134迁移、十reader及旧预约保持，操作key撤销、实际offset/首次快照/0effects，经独立结束审计才可称“review_only_v1在所选A/B、两新输入及有限窗口的准入通过”。

后续最少同链材料可考虑A用CloudTrail disabled的客观alarm与受控 `raw_event.trail` 标识，为同Case调查及人工发起C07 cloud dry-run pack复用；B独立资料验tenant/recovery。这不是本卡已冻结输入，不预定raw分类/追旧分数。Fusion不持久化tags；若后续pack需要cloud-misconfig tag，须明确人工API PATCH及read-back，不能声称原raw tag已保留。R01不为此创建topic/group/key/额度或业务材料。

## 完成判定、暂停与回退

R01与R02分别change、分别独审；不得用R01通过代替R02，不得用R02有限准入替代旧自治C03质量通过。两批完成后，可把这个**限定profile**作为C04—C11后续主线的输入合同；是否允许同profile日后持续常驻，须C11明确准入tenant、输入/预算、运维与人工复核责任后再定，不授权永久无人值守或自动响应。

第五阶段仍须一组同tenant/Alert/Case/Run贯穿Fusion→人审队列→经人选择的调查/知识→人工发起dry-run/审批→模拟验证→人工结案反馈，证据、身份、持久结果与批准控制闭合。C04/C05质量、C07/C08批准控制、C09 unknown及C10人审核不能延期成“系统可启动”；相关开放入口有阻塞则不能冻结。最终能力矩阵须写“review-only限定迁移基线”，自治判断/自动关闭/QA/自动升级/真实响应均未通过且禁止；Q1仍列已知缺口和重新开放所需原质量独审。

失败先停新输入/worker/dispatch，保存已有Run、SDK意图、预算、offset与原材料；先判定是否已发送/已确认，再决定同Run可恢复步骤。回退先停消费者，仅回退本批Agents image/profile配置；不能撤销PG/消息、删除预约、重放旧unknown或将原失败改通过。回到legacy默认值并不构成允许开启自治worker，worker/effects仍必须OFF。
