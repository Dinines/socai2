## 2026-10-24严格双版本源码隔离与本地提交保存

用户明确旧版完全不受影响，需修改旧实现时复制到新版本函数。本批按预期卡分两步：API新records/分派移入独立investigation_v2，旧分派/旧测试恢复原件，8新合同与51原合同通过；随后9个Agents新增模块移入独立investigation_v2，85项直接合同通过。旧已跟踪services源码/旧测试相对3fa4be3无差异，旧入口不导入新包，独立新分派不回落旧工具；新URL预留且未注册。新包不是已经可用的HTTP服务或完整调查，历史真实回执不追认新路径通过。

未参与修改的audit_contracts独立窄审最终限定ACCEPT、0项剩余必须修订。已修主稿第10节“可修改共享能力”的残句，AGENTS/spec/设计均明确旧代码不改、变化复制或新增。隔离回执见docs/operations/investigation-v2-isolation-20261024.json；JSON和源码语法、OpenSpec strict、diff及敏感信息/范围扫描通过。原任务仍5/15；不发真实模型/HTTP/PG、不运行入湖、不部署或push。Windows工作树94bb52f及其干净状态保持。用户调查本地Git提交授权有效，源码/测试/设计及公开回执一并保存，.local私密运行材料不入Git。

## 2026-10-24 开源→当前→v4改动说明审阅

用户要求说明流程及具体细节如何变化。主稿第16节按13环节对照固定开源34ca18、已发布/本地/未测实际和v4目标；源依据为固定来源清单、原版分析和原批回执，未以最早项目提交或20新构建代替纯开源。`audit_contracts`限定事实审阅ACCEPT、0项必须修；两条可读性建议均采纳（candidate05直接链接，M1纯合同/真实接缝区分）。不重审v4设计、M4或全部上游源码。新增说明后的主稿SHA256 `e0ea6bda688d05c7e55d3bc549a7bb8560ace859a1337d8409455ae185c8ed50`；下方旧v4审阅hash仍表示追加第16节以前的版本。

静态40本地链接/35表/围栏/JSON、diff检查与OpenSpec strict通过；任务仍5/15。说明图13主题/52次版本切换、320px全部主题无横向溢出、暗色代表呈现通过且无pageerror；先缺Playwright自带浏览器，后复用已装Chrome临时无头上下文完成检查，未安装/升级环境或使用用户浏览器资料。说明图源码位于本任务允许的visualizations目录，不是产品页面实现或站点发布。全部检查限文档/解释交互，无业务源码修改、模型/业务服务测试、远端访问、部署/提交/push。

## 2026-10-24 v4业务分层设计结束审阅

结论：未参与本稿编写的`audit_contracts`限定设计 **ACCEPT，0项剩余必须修订**。范围为[主设计v4](../../../docs/architecture/investigation-planning-design.md)、相关OpenSpec分层需求及页面/进度一致性，不是实现、模型质量或部署验收。主稿最终SHA256 `2a4ba75d91dc414c109634985b654e3fcf6e51a4d48846ea83ecea0f815664a9`。

初审两项必须修：继承段以“版本等变化时才补查”误限新问题/覆盖不足；只要求自动启动幂等而遗漏人工重试。已明确同问题有效查询不重复，新问题/缺料/覆盖不足/冲突按政策补查；人工和自动均稳定操作键、持久意图、唯一Run，已有运行不并发，不重置额度。窄复核另清理表格“自动模式才形成意图”的残句。成员快照建议已采纳：创建仅预览，启动时固定一致成员版本及分页，等待中新增成员纳入。

新增1.9只补Case代表场景必需的多成员PG/CH资料和验证顺序，不铺全领域数据。保留20自动处理过程/无Case详情、旧首次分诊、M4限定通过/M5.1通过/M5.2未测、20只核前端构建等边界。静态检查8文件108本地链接、69表、围栏/JSON无问题，`openspec validate restore-alert-investigation-integrity --strict --no-interactive`与`git diff --check`通过，任务仍5/15。后续新增的审计链接指向已有文件；未改业务源码/测试、发模型/业务查询、访问服务器、部署/提交/push，旧失败和unknown保持。

## 2026-10-24 M4限定结束与后续M5

2026-10-24 M4限定通过：选定8例原文/采用/可读均通过，23484tokens；其中两例冲突按完整消息/9源码/调用AST等价复用。02开发18回复52185tokens，5个失败原件保持、无unknown/unsettled、费用unpriced。15项直接测试通过，未参与实现者audit_contracts限定ACCEPT/0必须修。仅network_observation.v1/Q1,Q2,Q5，非完整恶意/授权卡或全调查通过。PG临时角色NOLOGIN并撤权；M5待按小步实施，OS后置、无部署/提交/push，原5/15保持。 版本、8例清单、失败及复用证据见[主回执](../../../docs/operations/unified-investigation-implementation.md)与[机器回执](../../../docs/operations/unified-investigation-m4-20261024.json)。

## 2026-10-23 M4.5授权与验收边界（预期，非实测结论）

最新用户授权已明确：开发调试测试累计tokens不限，可持续修复复测，无需逐批再确认；真实单次调查仍有上限。原pending复测预算选择已被覆盖，不据旧记录继续等待确认。M4.5须逐个执行8个原语义组合，每个独立test Run沿M3 20000tokens/180秒、单请求45秒/2048/retry0；累计不限不允许绕过预留、单Run额度或自动重放未知请求。失败定位修复后留新版本/new trial，不清旧Run、失败/unknown和原冻结。

验收分别评价模型原文、程序采用、可读结果，8例未达预期不进入M5。当前只是固定预期/授权，尚无M4.5执行或通过结论；旧M4不通过及候选限定ACCEPT保持原范围，OS后置、5/15、不部署/提交/push不变。

## 2026-10-23 M4前批独审：直接合同限定通过，真实矩阵功能门失败

最新授权继续逐步推进M4，前批M3限定ACCEPT仅证明其当批版本与接缝。M4.1a/M4.1b/M4.2依次完成11/13/12项直接测试，版本及失败/修正见[主回执](../../../docs/operations/unified-investigation-implementation.md)。未参与实现的audit_contracts对M4.1b及M4.2最终均给出**限定ACCEPT、0剩余必须修项**；接受固定候选程序采用及持久模型gate合同，不外推真实模型或整个M4。

M4.1b审阅指出assurance与validity混用，已修后13项复测通过：finding为rule_checked/current，assessment为model_assessed/current。所核evidence_view SHA256 `3d32a65d87e11d4b75ce79d2bbf49b1aefb6f3f7975b4a9791b05e53bb472837`；analysis_adoption为`02b429762e2b0e21bfef8ea2af843e56c571e10405635ece4a44da01047c810f`，测试为`253dae6b411e2cbe6265a7e471108663df8c0346cab071fbf03894ee97f214ac`。

M4.2复用safe_ainvoke observer核实际出站预留、恢复前原reply及同complete留存，12项/0.277s通过；旧no-bypass七项直接调用通过，原contract及测试未改。execution_models SHA256 `c1ccbef026005261736e73092466f3e503843b13471cf9144165bee230b27818`，测试为`15f865a5ab4daae04a2d92a08215dfe84b80bb0e6fb01a682f3c64a096269b4e`。审阅保留完成事务中第二次取消可能留下reserved/_active的限制，保守交接且无自动恢复保证。上述直接测试真实HTTP/DB/模型均0。

M4.3沿同stage 8model/0tool/20000tokens/max_unsettled1、DB begin后180秒执行，cost cap None且无估价保unpriced。实际7responded/committed、15042tokens、7unpriced、0unknown/0unsettled；七份answers均object而合同要求list，程序全部以answer_limit拒绝，**M4功能门失败**。第8原reason仅analysis_ExecutionRejected，剩4958<需6790为按状态/冻结输入/预留规则离线推导；实际reserve前阻止、无请求、未扩额，完整8例/指令隔离及整体质量不能宣称通过。PG21事件/36工件独立读回hash/bytes/eventrefs通过，旧Run状态/计费列未改，专用PG角色NOLOGIN及撤权完成。不能用M4.1b/M4.2纯合同或新prompt候选ACCEPT替代原M4失败。详见[主回执](../../../docs/operations/unified-investigation-implementation.md)及[M4 JSON](../../../docs/operations/unified-investigation-m4-20261023.json)。

M4.3准备新增的6份衍生样例在新Run `eb431eb2-6c62-5b61-8178-ae1b14580b0f`先保存6事件/6工件并独立核对；19文件模型前冻结manifest保留不覆盖。首次run命令在CreateProcess前被自动审批拒绝，当时模型0且无started标记；补充合成来源和既配目的地证据后，同一原命令重审获批准，未绕过审批。模型失败原文/采用/用量完整保留。

独立审读原回复还发现focused整体assessment、把5分钟写成1分钟、错误冲突predicate、空/缺源的空refs肯定finding，以及execution未知写failed，不能把失败简化为数组形状。M4.4仅澄清prompt、不变采用合同，13项/0.316s和8份prompt离线合同检查通过；7原reply回放与保存采用结果一致、仍全失败，真实新模型0。新源码hash `767c6e94cdd5d3aaafc344f5d93e5844c041162f9de1311a152fad289ae44c80`，测试hash `d4f34776c1e765cd39b13fecf3f5f65c733de45109de19f9814e1cd174b6a236`；audit_contracts对该候选限定ACCEPT/0必须修，原M4不通过及第8未测保持。

audit_contracts最终明确：**M4本批不通过，修订候选限定ACCEPT/0必须修，真实复测未做。** 未见越界恶意/授权/完成定论，不替代有用交付；combined/focused均结构失败，暂不能择优或宣称成本优势。费用cost_complete=false，不能把已知费用小计0称为0成本。

当时提出新Run最多8次/30000tokens/180秒的复测预算选择，pending期间未新发模型或建身份；此为历史事实。用户后续明确测试累计tokens不限且持续修复复测无需逐批确认，已覆盖该待选事项，不再要求新确认；按顶部M4.5每Run 20000tokens/180秒推进，不采用原30000提案或重置旧批。未过M4不进M5，OS后置，5/15、旧失败/unknown及不部署/提交/push边界保持。

## 2026-10-23 M3阶段结束独审（前批限定ACCEPT）

本批按M3.1→M3.2→M3.3小步推进，25项测试及一次真实HTTP结果见[主回执](../../../docs/operations/unified-investigation-implementation.md)和[M3摘要](../../../docs/operations/unified-investigation-m3-20261023.json)。审阅发现两项问题已修正：M3.2 scope重复嵌正文改为单份原文工件与refs，随后真实PG4项通过；M3.3未知参数先持久的问题改为reserve前schema required/properties校验，新增拒绝secret/sql键的第9项后9项通过。不能将最初8项通过当作该问题已被覆盖。

真实回执为1query/1match、3events/6artifacts、独立PG读回hash/UTF-8/event refs通过、0真实模型；临时API已停，PG专用角色已NOLOGIN并撤回三表及Run UPDATE(id)授权，旧CH reader保留。Run状态/计费列不变，测试Run running非最终调查完成；程序tenant条件不等于数据库硬tenant沙箱。

未参与实现的`audit_contracts`已只读核最终state/store/wrapper及9项测试源码指纹与实测版本一致，复核JSON/SQL/probe代码、独立PG连接工件hash/UTF-8/event refs和清理回执均passed，结论为**限定ACCEPT、0剩余必须修项**。完整源码指纹见M3机器摘要，接受范围仅为M3有限模块和一次真实M2接缝，不覆盖模型、完整调查或正式发布。M3限定实现/测试完成后停止，M4/调度/M7 manifest/M8入口及读取projection/OS后置；无部署、Git提交推送，原5/15及历史失败不变，不归档整体change。

## 2026-10-23 M1/M2首工具阶段结束独审（前批）

未参与实现的`audit_contracts`分别复核M1纯范围/版本政策合同及M2 API/受限caller，结论均为**限定ACCEPT，0本批必须修项**；接受范围是本批有限网络来源观察的程序合同与查询接缝，不是模型判断、恶意/授权裁决或完整统一调查验收。主回执见[逐模块实施记录](../../../docs/operations/unified-investigation-implementation.md)。

复核依据为D1/D2/M1/API/caller各8项共40直接测试、旧工具51兼容正常exit0，D2真实3行字段/hash、D3一告警/2消息与精确关联，以及M2真实5次HTTP查询（2匹配3空，含子毫秒边界）和4认证拒绝。caller越scope在HTTP前拒绝；泛API只有认证tenant及全局bound，Run持久scope/M8接线后置。大正文、去重/冲突及上限属于直接测试证明，未冒充额外真实数据验证。pytest挂起exit1、缓存权限及历史unknown保留。

本批M2审阅/实测/当前文件hash一致：caller `services/agents/app/tools/activity_records.py` SHA256 `312a4d243b867e43b454fc79a22c0d7c41124a9915088e369d224607dbf6f971`；API `services/api/app/services/investigation_records.py` SHA256 `add5e5f3053606a59823b47dda9b7b4d31af10a3cb23a8483379d2995dfad937`。`m2-runtime.json`确认临时API已停、临时token随进程失效；writer INSERT已撤回，reader与本批合成资料保留，未改旧账号或row policy。本次收口OpenSpec1.13.0 `validate restore-alert-investigation-integrity --strict`及`git diff --check`均通过，CLI仍5/15与R02 0/17；不以格式校验代替上述验收。

当批停止于M2首工具，M3持久/额度、M4模型、统一调度和实际Run入口尚未实施接入，OS后置。无模型、部署、Git提交推送，原5/15及旧失败保持；不归档整体change，也不把局部ACCEPT外推为剩余任务完成。M3后续事实见顶部；下文M0未放行是后续数据补齐之前的历史结论。

## 2026-10-23 M0来源盘点与工具数据规划结束独审（历史阶段）

未参与本轮编写的audit_contracts只读审阅工具数据规划、M0回执及相关Git/源码，给出**限定ACCEPT，0项本轮必须修订**；仅接受来源盘点与待讨论方案，不构成M0放行或M1实施验收。另由m0_source_map/search_backends分别核最新main测试工具和检索后端，均未业务访问或改源码。用户最新要求涉及工具方案先讨论，故当前首场景/工具数据范围未定，M0尚未放行；不会绕过该门槛实现后续代码。

本批主方案[工具数据建议](../../../docs/architecture/investigation-tool-data-plan.md) SHA256 `c698c0945376d4fbe38867f6a0726544c8f098b77a3d368f9bf4c7721bc221f2`；[逐步记录](../../../docs/operations/unified-investigation-implementation.md) SHA256 `2a3cfb65d17794c9ff3c8aeaeff3f2db6d6d63c90556d661f7e28f84086c5c70`。两份文档12处本地链接及36条表格数据行结构通过、来源JSON可解析且明确M0待讨论；git diff --check通过。OpenSpec1.13.0在调查worktree执行`validate restore-alert-investigation-integrity --strict --no-interactive`有效，list仍5/15、R02 0/17；新增M1规格是目标而非已交付。

真实新增检查仅为测试tenant中旧合成湖事件的只读核查：15字段/1行，外联字段缺失。沙箱阻止及本轮探针UUID别名错误/修正均保留于回执；未把它归为旧network_connections根因。无新业务数据、模型、部署或Git提交推送；下方v3原hash与当时CLI未发现记录保留为历史，不追认旧失败。

## 2026-10-23 调查规划v3文档修订结束独审

root修订主文档、示例与交接入口，audit_integration只补design/execution本轮记录；未参与本轮编写的audit_contracts与audit_practicality分别只读审阅v3增量及相邻合同，均给出**限定ACCEPT，0项本轮必须修订**。前者核两维判断/范围、模型模式、预算、发布和七项意见落实；后者核材料信任边界、小模型负担、首场景验收及仅文档授权。两者均未改文件、运行业务/模型/测试或访问生产。

审阅对象为[调查模块规划设计v3](../../../docs/architecture/investigation-planning-design.md)，SHA256 `1deac54a5cfc3d764b2ec601c7993949d006060166f6e36a50365446e059e194`，695行。审阅后主文内容与该hash保持；第15节历史ACCEPT只作原范围记录，不代替本次审阅。首场景仍draft/source_unverified，恢复专项后置，接受范围仅为本次设计修订一致性和合理性，不代表来源可用、模型效果、实施或上线验收。

root另做静态校核：主文26处本地链接、1段JSON、24张Markdown表、代码围栏、修改段新增链接及冲突标记检查通过；git diff --check通过，原tasks与HEAD内容一致，仍5/15。变更限于7份Markdown设计/审计/交接文件，没有业务源码或规格变更。当前Windows环境未找到OpenSpec CLI，因此未执行本轮strict，也未安装工具；此次为文档修订，后续实施前仍须按项目要求完成strict校验。

工作树为`E:\aisoc\socai2\.local\worktrees\investigation-working`、分支`codex/investigation-working`、基线`3fa4be3`。PROGRESS普通写入曾被本机文件权限拒绝，随后获准完成相同文档写入；没有因此修改权限或扩展业务操作。Windows原分支未提交工作留原处；未启动M0来源核实、业务/模型测试、生产访问、部署或提交推送，旧失败与unknown保持。不另存设计旧稿副本。

## 2026-10-23 测试数据工具迁移结束独审

root与manual_design/deep_design分别实现工具、观察器与探针；未参与本次实现的handoff_audit只读独审，最终 **限定ACCEPT，本批0项必须修**。独立44 passed/39子项；核3条真实Fusion、2例原worker、29工件正文/hash/关联及6回复26492tokens一致。188个Agents源码和6上游原件hash保持，sender未知/隔离、observer完成语义/用量、原worker实调用/提交与清理准确；未新增审阅网络或模型。

审阅要求修README的Agents输出目录示例，已改为实际允许的仓库.local。测试身份停用/预算2 responded正确RLS补查保留；初次缺RLS空观察不冒充业务结果。Git忽略覆盖本批运行材料，无已跟踪.local文件，不误忽略代码/测试/上游。工具、接线、持久观察与partial交付接受，标记影响推理、软预算超额、报告running/Run completed及无有效取证pivot等限制保持，不追认内容质量或生产发布。详见docs/operations/testdata-migration-execution-20261023.md，原5/15不变。

root静态核20链接/围栏、diff与OpenSpec strict通过；选定源码、文档、无凭据回执及本次审阅结论留存.local/versions/testdata-migration-20261023/。共享文档含此前历史修改，快照不是独立部署包或完整工作区diff；未提交/push或部署。

## 2026-10-23 测试数据迁移修订规划结束独审

root编写；未参与本次编写的handoff_audit只读对照原回执及相关源码，指出独立DLQ/消费起点、14次业务调用轮次不能当SDK/网关物理请求总数两项遗漏。主计划已补齐，并明确测试批次标记与实际Alert/Run身份映射；窄复核最终 **限定ACCEPT，0项本轮必须修项**。

接受范围只限docs/operations/testdata-migration-plan-20261023.md的历史事实、设计和边界，不是工具实现或业务验收。审阅者未运行测试、连接生产、调模型或改文件；root仅做15本地链接/围栏、diff及OpenSpec静态检查。原5/15不变，原失败不覆盖，未实施/部署/Git提交推送。计划和审阅结论留存.local/versions/testdata-migration-plan-20261023/。

## 2026-10-23 调查小修结束独审

未参与实现的`handoff_audit`审读9业务文件、逐步回执和真实模型出站/原文/程序采用，结论限定 **ACCEPT，0项本批必须修项**。独立无外联70 passed，另核真实编译LangGraph两Run并发子任务进度及外层取消隔离PASS；复核root实际独立PG44 passed/0 skipped、SQL2、runner/报告18及逐步日志。两角色真实2回复2714tokens、原文仍有条件处置与无依据enrichment，程序采用正确；首2请求503/未知用量保留，不追认模型原文全过。

详细审计`.local/verification/investigation-result-handoff-20261023/independent-audit.md`，执行回执docs/operations/investigation-result-handoff-20261023.md。保留普通外部取消不保证最终报告、普通字典unknown不计pivot、有界工具材料而非全量原始日志等限制。代码/验证版本保存于`.local/versions/investigation-result-handoff-20261023/`；本批不部署、不推送，不扩后续调查设计，原5/15与历史失败保持。

## 2026-10-23 事件级与跨事件研究结束独审（仅文档）

root编写；未参与本次编写的resumed_projects_end_audit只读独审限定 **ACCEPT，0项本轮必须修项**。核本地Fusion键/摘要、worker单告警state与Run、Case摘要25/最终3条投影、agent-runs调用方材料、PG Chain无Incident过滤及Fusion chain；确认已有多告警与跨Incident候选，缺持续事件整体研判的判断准确。

独审本次联网只读抽核7个正文官方来源，确认Microsoft Incident cases Preview、Endpoint AIR自2026-09-01的变化、Falcon共享上下文调查Pre-beta；关联/相似与合并、候选与因果、三个同名Fusion均区分。用户随后要求整理设计、链接和参考点，新增第9节13项资料采用点索引及2项补充链接，独审再作仅该索引窄核，限定ACCEPT、0阻塞，未重复联网。

root核文档本地链接/围栏、git diff --check和OpenSpec strict通过，任务仍5/15。本次仅研究文档及交接准确性审查，不是厂商效果、本项目实现/质量或完整change验收。无生产访问、业务测试/模型/消息、部署或Git提交推送；文档前稿、最终副本、增量、hash、逐步记录及审阅结论留存.local/versions/incident-analysis-research-20261023/。研究正文见docs/architecture/incident-analysis-product-comparison-20261023.md。

## 2026-10-23 调查优化方案保存结束独审（仅文档）

root修订方案和交接记录；未参与本次编写的resumed_projects_end_audit只读对照before四文件增量，抽核人工run/stream及校验顺序、typed认证/网络查询、Deep异常与trace落库、工具preview、Identity/Cloud解析和Router汇合，结论限定 **ACCEPT，0项本轮必须修项**。既有v1例2参数误填、六轮十工具、27697/20000及末工具JSON与回执一致；C2 source05未终审和未全发布事实保持。

三批结果/交接→查询/场景→共享结构/扩展自洽，四合同属目标、首批不全做，Router扩大使用前修正可独立提前；验收材料均为未来要求。AGENTS、PROGRESS、execution明确用户只要求方案保存，不构成实施授权。47本地链接及围栏通过，原任务5/15保持；root另核git diff --check和OpenSpec strict通过。审核未联网、改文件或跑业务测试。

仅确认本次文档事实、建议及边界，不是业务实现、质量或发布验收。前稿、修订稿、增量和检查/审阅记录保存在.local/versions/investigation-plan-review-20261023/；原历史证据不改写。无业务源码/合同/运行修改、新业务测试/模型/消息/生产访问/部署，不归档或Git提交推送。

## 2026-10-22 两个暂停项目恢复结束独审

实现/执行/记录root；未参与实现者`resumed_projects_end_audit`只读结束独审，**限定ACCEPT，0项本轮必须修项**。独立核3份payload/expected的manifest hash、HTTP/raw/fused坐标、三份snapshot规范hash及原FusedAlert正文等价（信封alert_row_id/persist_outcome另核）、8字段保留、答案四键未入消息、source_event_ids原引用+上游Alert ID符合原worker合同。原3Alert/new/无Case、6消息、关联Run0/模型0、未启动Fusion消费循环、group_id=None/禁提交、独立topic/Redis前缀与临时进程停止均有原探针及回执支持。未重新联网/执行测试或业务，根原8离线＋2替身合同结果仅复用。

独审核初始before9项hash、工具/探针本轮无改，237行原产品文/hash与旧独审吻合；本次只同步后来v1发布/两例/留存缺口并完成交接，不实施未选定优化，原任务逐行仍5/15。首次本地材料观察对source_event_ids完全相同的假设错误及修正已保留，无业务重发；旧attempt01保持。原始独审回复留.local/versions/two-projects-resume-20261022/independent-audit.txt，工具结果见docs/operations/testdata-tools-20261022.md及docs/handoff/testdata-tools-20261022.json，步骤见docs/operations/two-projects-resume-20261022.md。

root另做64本地链接/围栏/机器JSON、git diff --check及restore strict检查，选定非私有文件/合成回执/逐步日志按项目路径留存该版本目录，排除private签名配置与凭据。范围只限本次恢复交付；不追认调查/关联质量、生产offset恢复或完整change完成，不新增部署、worker配置变化、模型/厂商动作或Git提交推送。生产v1沿此前授权保持。

## 2026-10-22 两例落地及数据盘点结束独审

未参与实现者 `v1_two_examples_audit` 直接读取本地真实PG正文/元数据/图缓存回执，独立重算21份工件字节/hash通过，核21份event关联、成本3行/8回复31788tokens、25表428字段及约束、两例发送/读取坐标均与原回执一致，最终交接正文限定ACCEPT、0项本轮收口阻塞。机器字典未含凭据或prompt正文。完整逐步骤原文留存及调查质量不通过；graph_step仅node、tool preview200、prompt副本截断、seq后写低值问题已说明。分类源码未改，不由本批追认旧质量或原5/15完成。SQL实际执行校验由root在只读事务完成9 SELECT通过，不冒称独审者重新运行。新版交接包94331字节/26项，manifest覆盖17份正文及7份辅助文件，SHA256 `ac6d29a15d6ad2117bc1147f917219c0ca4216047c5cf135273f69f8cce8e058`；124链接/3锚点/7JSON、diff/OpenSpec strict通过，旧包不覆盖。v1_two_examples_audit随后独立窄核最终ZIP、17+7文件及manifest/本地一致、无私有配置或prompt正文，限定ACCEPT、0收口阻塞；只读SQL执行回执为readonly开启/9SELECT成功，原留存/质量不通过结论保持。见[回执](../../../docs/operations/service-v1-functional-20261022.md)。

## 2026-10-22 后端对接发布文档v1结束独审

root编写docs/integration/v1/五篇文档及JSON/env/只读SQL示例；backend_kafka_inventory、backend_database_inventory只读提供topic/schema及表关系事实。未参与研究/编写的backend_v1_doc_audit结束独审**限定ACCEPT，0项本批必须修项**。核正式Kafka输入/HTTP告警仅测试、source-v1稳定身份、PG确认后fused与DLQ、API与Agents路由、Case/Run归属、各步state/事件/工件/Markdown持久边界、公开Compose端口与迁移DDL；不把fused当调查完成、graph_step当完整节点JSON、Run completed当业务结案。root在审查前已将独立graph入口修为原Agents `/api/v1/agent-runs`，Agents/Actions内部端口核为8084/8085。

本轮21最初SSH超时，用户告知恢复后，root只读Docker元数据白名单15容器，2026-10-22 16:02（Asia/Shanghai）配置见docs/integration/v1/runtime-snapshot.json。独审仅对新增配置做窄复核，**限定ACCEPT，0功能或凭据泄漏阻塞**：CH192.168.1.21:9000/aisoc/socai2_lake、TI OS主机、TI/enrichment共享Redis DB12、worker实际disable1/升级0/Router0/profile、Fusion空/Agents127.0.0.1:9的enrichment目标及镜像一致；快照仅白名单/URL结构/秘密有无布尔，无密码/token值。审阅要求将DSN说明精确为“API转换sslmode，Fusion去驱动后缀后交原生asyncpg解析”，root已更正，无需新测试。

结论只覆盖可交接的文档v1，不代表发布服务、业务依赖/模型重新验收或启用常驻。root最终静态验证Raw/Fused模型及canonical/tenant、4份JSON、86本地链接/1锚点、2段shell示例语法、diff/OpenSpec严格校验通过；没有实际执行示例HTTP/SQL、发消息/模型、业务库或图写、部署/重启/启worker或Git提交推送。容器运行/health来自元数据，不等于新的业务连通检查。旧5/15、未知/质量失败、本地候选未部署与测试工具未完进展保持；后端查询优先API，真实凭据仍在受控文件。完整目录、净化运行快照和包内manifest随v1交付，文档包仅选定文档/示例，不夹带private或业务源码。

## 2026-10-22 智能调查产品与工程建议既有结束独审（收尾补记）

原root编写方案，product_design_review仅只读提供产品建议；未参与编写的tender_document_final_audit原会话最终回复为**限定ACCEPT、0项阻塞**。原root因usage limit中断未回写，本次只补记已有结果，没有新发起审计。核原审阅会话01a1623d-629a-7903-8ce2-8548addab345最终回复与当前正文：237行，SHA256 `da49036cddf0a7c8740deedcbcf980c995ded91b2e865633f1d769cf54e3ca10`一致。

最终复核确认新增两段准确：风险优先级/研判/自动化资格应分别表达，当前build_state未完整传递route_to/tags/category且worker不据此选择Router；Case按事件时间最多投影3条告警至raw_alert.alerts，Router/领域消费者不自动展开，实际条数/遗漏提示与有界摘要属于建议。其余原已审结论保持。本次仅核文件hash并找回结果，未重跑业务检查；原回复本地副本及续接见[两会话收尾](../../../docs/handoff/session-closeout-20261022.md)。

接受范围仅产品工程建议文档，不代表方案已选定实施、产品质量/21发布/常驻准入通过。测试数据工具增量真实联测和结束独审仍未完成，原5/15与历史失败保持。

## 2026-10-22 标书需求与迁移评估文档结束独审

root负责主文、原件164条功能矩阵和交接记录；migration_evidence_review只读核支撑模块/Fusion/分诊及固定上游归属。未参与编写的tender_document_final_audit完成结束独审，**限定ACCEPT，0项本轮文档交付阻塞**。仅确认本轮评估的需求定位、证据与建议，不构成产品功能/质量验收、21发布或常驻准入。

独立核AI SOC2.docx及XML hash与基线一致；35子组、164个唯一REQ-P同原件逐字对应（仅去段尾空白），六模块细项17/22/42/20/37/26，无遗漏。P124技术选型、SFT/RAG/编排/证据及P412六项指标均覆盖；主文与矩阵569个本地文件/锚点引用0缺失。root文档检查复核同样通过，原tasks仍15项/5勾，OpenSpec strict和本轮相关diff检查通过。

审阅提出两处判据表述：P226要求分析“可能”行为，不能以尚无确认事实反证完全没有分析；P345要求评估能力，质量评估失败不能反证没有评估。两行已改为部分满足并分别注明有效性/真实来源、产品化人审反馈与试点评估缺口，复核通过。收尾时共享仓库新增本地镜像回执，已将主文更新为API5a1e1fd8/Agents49643b84完成构建/离线核验，下一步阶段发布准备；不继续列未构建，不改其他批次历史事实。

审阅后主文SHA256 `845814402ce712510b0ed9457f1a73a5b7196e979e1f3696811c601a709ced4c`，矩阵 `90090772b08ee6fc525fe1ad3f00e9d83e1ee6647bb0ddc2a4e1bc01c8e458f0`。原件映射与文档核验记录在`.local/review/tender-assessment-20261022/`，不含业务凭据。新增GET /alerts筛选/search和UEBA最近50条限制仅静态登记原问题表，不称线上复现或本轮新阻塞。

审阅者全程只读，无改文件/联网/业务测试/模型/运行操作；本轮root也未改业务源码、调用模型/业务HTTP、发消息、写业务库/图、操作Docker或21部署。需求原件、旧失败、unknown、worker OFF、R02及原5/15保持，不归档、Git提交或推送。交付：[详细评估](../../../docs/operations/tender-requirements-assessment-20261022.md)、[逐条矩阵](../../../docs/requirements/socai2-requirements-matrix-20261022.md)。

## 2026-10-22 本地候选镜像构建与离线核验结束独审

root负责环境/镜像导入构建、必要helper适配及探针；candidate_image_verification_plan只读建议最小检查。未参与实现的candidate_images_end_audit结束独审**限定ACCEPT，0项本轮剩余阻塞**。核精确父ID、19源码、固定manifest、本地BuildKit单节点/context Host、RootFS前缀与配置继承、两镜像probe19hash/7排除项/385和129导入/4方法，实际受限argv、exit0/stderr空及定向清理0。15份证据hash/当前helper hash与文档/JSON一致，原15项/5勾不变。

本轮helper仅因实际环境修可选Config字段、显式验证本地BuildKit/context；三次失败、最初导出拒绝后用户明确授权及OrbStack恢复11既有本地容器均保留，不称全程无本地容器启动。审查者只读，无Docker/网络/业务测试或文件修改。OpenSpec strict/diff/3本地链接通过；结论只覆盖API5a1e1fd8/Agents49643b84本地构建与离线检查，不批准21部署、实际业务质量或常驻，不重跑前批100/模型，不归档/Git提交。详见[本轮回执](../../../docs/operations/investigation-candidate-images-20261022.md)。

## 2026-10-22 候选组合与构建准备结束独审

root负责组合/取证/记录，candidate_build_recipe_review负责最小配方助手，candidate_combination_plan只读建议测试范围。未参与实现者candidate_preparation_audit只读结束独审**限定ACCEPT，0项本轮剩余阻塞**：19份review/隔离组合/context hash一致，7excluded为candidate05原件，Deep仅摘要变体；full bundle定向取证与UEBA保持、父ID语义、Agents55/API45隔离测试及4方法router登记证据一致。

独审提出助手未绑定清单身份、文档所述构建后父层/启动配置比较尚未实现两点，已最小补齐固定manifest SHA及实际执行分支比较并复核。默认plan通过且images_built=false，真实Docker分支只静态审；本地daemon未运行，本轮无镜像构建/部署/常驻。独审未重跑业务测试、联网或调用Docker。新回执/机器摘要/AGENTS/进度/原任务一致，15项/5勾及旧质量失败保持；不批准实际镜像、运行/质量或发布，不归档。详见[本批回执](../../../docs/operations/investigation-candidate-build-20261022.md)。

## 2026-10-22阶段收口与选定源码副本结束独审

实现与记录root；b6_responsibility_closeout、release_diff_inventory仅只读提供责任/来源建议。未参与实现者stage_closeout_audit结束独审**限定ACCEPT，0项本轮阻塞**。核docs/operations/investigation-stage-closeout-20261022.md、机器摘要、本地review副本及原任务/来源：API7＋Agents12共19，18原样复制、Deep从已匹配candidate05原件只加Bundle摘要；24修改＋2新增正好对应19候选＋7排除，原业务工作区和5/15保持。

一个现有材料交接用例明确加载副本Deep，1 passed；独审未重复业务测试或扩大为19文件组合验收。审查发现副本导入后多出一个pyc，root只删本轮该派生缓存并使runner在导入前sys.dont_write_bytecode=True；独审只读复核恰好19物理.py且源码hash不变。独审所查420本地链接0缺失；root450为另一文件集，不相加称业务测试。

父版本只依据最近full回执，纯full bundle字节/hash本地缺证与最新运行态未查明确保留。本结论不批准组合/构建/发布、旧C2最终source05、常驻启用或整体质量；未新发模型/消息/后端HTTP或业务PG/图写，不归档/提交推送。具体边界见[本轮收口](../../../docs/operations/investigation-stage-closeout-20261022.md)。

## 2026-10-22关联/链图模块评估文档结束复核

编写root，module_value_assessment与roadmap_next_step_review提供只读事实/建议。未参与本轮编写者concept_docs_final_audit仅复核第11节及相应导航、PROGRESS/execution前缀，对照已有交接/回执/原任务，结论**限定ACCEPT，0文档阻塞**。基础检索/关系上下文/Run留痕可转B5→B6的判断没有扩大为跨Incident活动或行为因果；Fusion链低优先级、实际发布差异及旧C2未审边界、后续业务/数据合同优先顺序准确。

本轮339个本地链接、新module-assessment锚点及diff检查0问题；无新增业务测试、模型、网络、写库、源码/运行或部署变更。该结论仅确认评估文档准确，不批准实施/发布/常驻启用，也不补认旧质量或改变5/15。上次概念文档审查449链接与本次不同文件集339分别记录，不相加计作业务验收。

## 2026-10-22概念辨析、例子与结论存档结束独审（仅文档）

编写root；concept_document_checklist只读核容易混淆的源码事实，不参与结束审查。未参与编写者concept_docs_final_audit对照/tmp/socai2-concepts-doc-before-20261022中的本轮前备份，核架构正文、Fusion说明、导航、AGENTS、PROGRESS及execution六份增量，并抽核当前源码，结论为**限定ACCEPT，0文档阻塞**。本条只记录独立返回的结果，非新增业务验收。

核对包括：Incident与Fusion链四种成员组合及P→A→B同Incident异链；Chain ID内部续组/交付/留存与下游业务未消费的区别；战术只影响链阶段/位置；PG链的Alert种子、前后各24h、3轮、50候选、跨Case与签名；Case Path为已有关系子图、无Case仍有Alert可达图；普通自动调查不建Case、Playbook无原生create_case但可另行接入、外部ticket与Hunt/KEV专用分支。未将推演算实测，未将讨论变成删链、合并对象、修改算法或建Case实施。

审查时449个本地链接（URL解码后）及5个新显式锚点0缺失，git diff --check通过；root另核Markdown围栏、原任务5/15及变更前OpenSpec strict。文档见[概念讨论与例子](../../../docs/architecture/attack-chain-path.md#concepts)。本次无业务源码/配置、模型、消息/写库、部署/重启或Git提交推送，worker OFF、旧质量失败/未发布限制保持，change不归档。

## 2026-10-22 Kafka入口真实联合结束独审

探针/执行/回执：root；joint_probe_design只读方案核对；未参与实现者joint_graph_audit结束独审限定**ACCEPT，0项接线阻塞**。核attempt3真实原消费循环→prepare→本地原API认证/PG→21 Neo4j，分诊入口前成功回执及直接邻域5节点4边、canonical/tenant/provenance一致，readerPOST403/GET200、hold1次、未确认offset、新Case/Run0、业务triage/模型未执行且本地进程已停。静态与实证未混作完整调查通过。

审查指出GET blast_radius另有14可达候选，经共享Technique可关联同tenant历史测试资料，已在正文、JSON和原问题清单明确不作当前确认影响；累计PG合成夹具2条含attempt2失败，未只报告成功1条。旧失败/5/15、Fusion/部署及常驻边界保持。独审仅本地只读核源码、文档与已生成证据，未重跑业务、联网或发模型；root另核15份选定版本原件/副本/归档一致、strict/diff及Fusion/服务锁无变化。版本依赖基线与既有本地增量，不是发布包；见docs/operations/kafka-graph-joint-20261022.md及机器回执。

## 2026-10-22本地Conda依赖统一补齐结束独审

实现/安装/回执：root；agents_dependency_audit只读检查Agents声明与导入；dependency_final_audit未参与实现，以只读方式结束独审，最终限定**ACCEPT，0剩余阻塞**。核56项精确pin与公开/本地清单一致、两服务声明及递归extras满足，初批90项Python/37项Conda包计划和安装记录，旧项目editable仅新env移除，最终pip check及Conda激活加载通过。审查指出SQLAlchemy2.1.4超出instrumentor支持范围，root仅本地覆盖2.0.52并保初批证据；最终API追踪实际启用、33+32离线检查及71+14直接测试通过，结果不重复累加。

原服务pyproject/lock、业务源码、旧socai环境/源码及21部署保持；依赖回执明确Kafka联合仍未成功、attempt2仅留新合成PG行且无topic/消息，attempt3未执行。审查未重跑业务、安装、联网或调用模型；root最后strict/diff及本地16份版本一致性核验另列，不扩大为独审全业务/真实联合/发布批准。见docs/operations/local-dependencies-20261022.md和机器回执；5/15、不启常驻和旧失败保持。

## 2026-10-22 Kafka消费入口写图结束独审

实现：root；新增Kafka入口测试：kafka_graph_tests；kafka_graph_design_review仅提供只读设计建议。未参与实现者kafka_graph_audit结束独审**限定ACCEPT，0项剩余阻塞**。先有本change规格/设计与strict，再改4个生产文件及必要直接合同；Fusion源码未改。新入口在schema后/原triage前每delivery准备一次、内部重试共享回执，后续fetch纯GET，Case真实边沿原MERGE保留。

独审核tenant/canonical Alert及独立writer、reply身份/来源、review-only/shadow和ContextVar隔离，显式Alert超Case前50条仍投当前告警。审查发现新prepare从build_state求类别漏category，root改取原消息类别并补窄例；UUID新回执规范比较保持原Run/ID合同。已独立核Conda三组日志24＋47＋14=85 passed，16份本地版本当前原件/副本/归档及manifest一致、归档hash匹配。root另核468个本地链接、strict、diff与Fusion源码零差异；不混称独审重跑业务测试。

本批仅本地接线/直接替身合同验证，无新真实broker/业务PG/Neo4j、模型/正式消息、旧Run/unknown重放、部署/重启或Git提交推送。Conda环境已按用户要求创建，初轮缺依赖/网络/离线缓存及收集失败保留，不计业务通过。旧C2质量修改仍不在本次发布批准范围；worker OFF、5/15与旧质量失败保持，完整change不归档。见docs/operations/kafka-graph-intake-20261022.md及机器回执。

## 2026-10-22阶段交接与本地保版结束独审

编写与保版：root；next_step_review和handoff_evidence_review仅提供只读证据核对。未参与实现者stage_handoff_audit结束独审**限定ACCEPT，0剩余阻塞**。本轮仅B5→B6交接、根入口/导航时态订正和.local/versions/attack-chain-path-20261022选定文件保版，无业务源码/配置修改、新业务测试、HTTP/消息/模型、部署/重启或Git提交推送。

独审核关键Run/用量/图节点边/工件与原证据一致，已发布I2正常usage保护、本地两处合同/链图及旧C2未终审修改分开。36份原件/副本/归档及manifest一致，Git基线存在，无私有env或HTTP观察路径、未发现高信号凭据。快照依赖基线，不是独立安装包或已审发布包；局部质量失败、常驻worker OFF和完整5/15保持。

发现docs/README仍有旧“最新只规划/下一项分诊”现时表述，root最小修为2026-10-22交接入口及明确历史，独审只读确认。链接检查0缺失、diff检查通过；root另完成OpenSpec strict和源归档本地检查，不以这些检查新增业务通过计数。完整change不归档，此审查不代替其结束独审、整体质量或C2发布批准。详情见docs/operations/investigation-stage-handoff-20261022.md与机器摘要。

## 2026-10-21外部HTTP/Tool验证设计结束独审

编写root，case_source_review只读提供固定源码/合同建议。未参与本轮编写者deep_functional_tests只读核docs/architecture/third-party-search-contract.md与当前调用接缝，结论**ACCEPT，无阻塞**。外部厂商原HTTP合同保持，UnifiedQuery仅内部使用，不虚增能力；SIEM复用与独立Tool边界清楚，示例vendor_host_events明确不存在。参数/认证/映射/分页及窗口/截断/event.id限制准确，registry无通用schema校验、execute(name,args)不携call id/tenant如实说明。

HTTP适配、直接Tool、脚本模型交接和真实模型选择的证明范围明确；call id/下一轮ToolMessage及最终工件充分区分，不强迫真实模型才证明接线，也不把HTTP200或正确答案当正确执行。独审未改文件、跑业务测试或调用HTTP/模型/基础设施。root只作6 JSON/12文件引用、静态时间及strict/diff检查；本轮仅设计，无新实施，原5/15、worker OFF与旧证据保持。

## 2026-10-21Tool文档结束独审

本轮编写：root（指南/导航及过时说明订正）、router_functional_tests（精确目录）、case_source_review（SIEM示例与Elastic/Sentinel拆解）。未参与本轮编写者deep_functional_tests对照当前API/Agents及固定原版connectors源码只读独审，结论**ACCEPT，无剩余阻塞**。

固定16/条件customer/MCP、固定预取与Deep自主调用的区别，SIEM hours→since_hours、凭据/非秘密配置、四产品允许集、新adapter接线和未迁独立服务均准确。新增Elastic/Sentinel的统一条件、ES|QL/KQL、认证/端点、结果展平及静态缺口如实说明；自研第三方可映射JSON，不预设SQL。已按审查修正假模型测试定位和24000阈值字符/字节区别。另核预处理文档本次Bundle/case_id/认证查询限定、导航和配置链接，无误。

示例未执行、厂商兼容未实测、代码未部署及旧失败边界保持。root仅作12 JSON/5 shell语法、92处文件引用、OpenSpec strict及diff检查；独审未修改文件或运行测试/translator、HTTP、模型、基础设施。无业务/运行变更，原5/15及worker OFF保持，不归档、不Git提交。

## 2026-10-21链图本地实施结束独审

未参与本批实现的deep_functional_tests只读审查源码/直接测试/真实模型观察及API工件，限定ACCEPT，无本批阻塞。原链算法和三种编排保留；GET只读、prepare写权限与tenant正确、七RO不能投影。新Case四次实际模型输入含相同3490字符摘要，三工件/图边端点/hash/Markdown读取一致；首Run取消预取的失败保原，两个全新Case8回复32329tokens，不追认首失败为通过。候选5条是本Case2＋同tenant历史3，不当作确认攻击。独审本地复跑22项通过（重叠不累加）；API109及Agents120沿实施工具/日志，不冒称独审复跑。

持续同步/解绑旧边清理和本批未做Router/Deep真实模型矩阵为保留限制，不阻塞本次新Case接线。原5/15和未部署状态保持，不归档。审查未改业务源、发模型、访问基础设施或部署。详情与输入输出见docs/operations/attack-chain-path-local-20261021.md。

# 完整性评估与修复规划独审

2026-10-21。实现/整理：root。三路只读源评估：api_auth_review、fusion_review、triage_review；probes由triage_review保存，root复跑。最终规划独审：未参与文档/探针实现的api_auth_review；triage_review另核I2描述与范围一致性。

## 结论

**accept，仅评估与修复规划通过。** 不认可产品修复完成、自治质量通过或运行启用；change继续活动，不归档。当前4项评估/规划任务完成，11项后续实施/交付任务未完成；旧R02暂缓，原0/17保持。

## 独立复核

- 四服务1578个固定上游原件均在，68修改、0缺失；770运行Py、prompt lock1、Compose28共799项hash零差异。
- 12份原Dockerfile/pyproject/lock保留，未删除原路由声明，API/Fusion双schema一致；静态编译/引用检查不冒充完整运行依赖或所有接口验收。
- api_auth_review和root均复跑未改写生产函数的AST探针：warm/cold提前return跳过升级，graph.complete_run默认0覆盖usage，随后首次分诊投影拒读，与assessment一致。内存替身、0真实网络/PG/Kafka/SDK/模型，不声称21已发生故障。
- I1临时裁剪、I2本地保护与上游graph组合、I3原HTTP入口与本地持久合同组合、I4上游缺源语义归属准确。修复设计保留必要既有修复，不全盘回退或简单解除全部开关。
- R02原五文件hash零差异；旧独审三份绑定仍匹配，0/17，仅新增status暂缓，不作为功能前置。CLI仍列ready的边界已在根说明和context标明。
- 完整告警/调查目标包含自动分诊、自动关闭和自动升级；playbook/反馈一体保留不额外改测；可用性专项后置，不扩大采集、原始检测、前端或真实响应授权。

## 规划校验与修订

严格 `openspec validate --all --strict --no-interactive --json`：两活动change均通过。根入口/本批/相关权威文档395个本地链接无缺失。规划审查中root收紧F3：按原HTTP入口的完整处理合同与Kafka对齐，不另创含糊的预览模式。

原探针第一次缺注入time的NameError明确记为探针错误，修正后才复现I2；原始失败摘要及更正保存在probes/result.json，未当产品运行失败。旧批次回执、来源清单和质量失败未改写。

本轮仅文档、规划和只读源探针；未改运行源码/依赖/Compose，未做部署、模型、消息、业务PG或真实厂商操作，未Git提交/推送。后续产品实施需按本change待办推进，不以本规划独审代替实施结束审计。

## 后续原则同步（2026-10-21）

用户再次明确全部一体模块可整体原样迁入、不额外改测，冗余设计及服务可用性测试/修复后置。proposal/design/tasks/spec及assessment补充段已同步：I2仅正常graph用量/结果问题列当前修复，特殊故障恢复接续后置，不先增加通用阶段/恢复框架。纯文档change prioritize-functional-completeness另经api_auth_review结束独审通过；没有重跑本评估源探针或改写原证据，本change仍4/15，产品修复未实施。

## 后续总规划衔接（2026-10-21）

用户要求整体规划并强调自动调查。当前completion-plan统一B1—B6执行，原F编号改作问题类别；proposal/design/tasks/spec明确自动分诊后实际关闭或自动升级、无需人工再点的取证/知识/分析与结果/报告交付。沿用本产品任务树，4/15不变，未归档或实施产品；总规划文档另由plan-alert-investigation-migration记录审计，不重跑原源码或探针验证。

## 2026-10-21 自动调查触发澄清独审

**本节关于“用户新增规则触发目标”的解读已撤销。** 用户随后明确是在讨论原有代码设计，并非提出新需求。原过程记录保留如下，其规划接受结论不再作为新增规则合同的依据；纠正结果见后续勘误记录。

用户澄清按配置规则（例如告警等级）触发调查，命中启用条件即自动开始。root同步总计划、范围、proposal/design/spec/tasks及PROGRESS；triage_review未参与修改，独立核对源码与规划后accept：目标与当前普通worker未关闭后升级、业务规则无investigate动作、playbook已有severity过滤/investigate步骤分别说明；保留原能力复用候选，未预建新规则平台或扩大可用性矩阵。实际阈值/启用范围尚未指定，当前仍只规划、worker OFF、任务4/15不变。活动change严格校验通过；无产品代码、部署、模型或消息操作，旧归档规划与历史回执未改写。

## 2026-10-21 原版设计讨论勘误

用户明确上述讨论是在核对原代码设计，不是新目标。root撤回误加的规则合同、优先级和命中/未命中/停用专项要求，恢复原spec段落及3.3任务；范围、总计划、proposal/design/PROGRESS同步纠正。只读核固定上游确认：playbook已有severity/tags条件和investigate步骤；普通worker另有分诊未关闭后run_escalation路径，不能因后者没有等级筛选而推断整个原版无规则驱动设计。Case/参数/认证接缝仅按静态事实登记到upstream-issues，未当作真实故障或已验能力，不追加playbook改测任务。

triage_review未参与编辑，结束独审accept：新增需求已撤回、两条原路径及静态限制表述准确，playbook额外改测/可用性后置、4/15及未实施边界保持。活动change严格校验1/1通过。无产品、部署、模型、消息或远端操作；原归档与冻结回执保持。
# 2026-10-22 v1.0.0服务发布结束独审

未参与实现者 `service_v1_release_audit` 先审具体operator/plan/overlay，再独立核实际回执和Run工件，结论**限定 ACCEPT，0项本轮必须修正/发布阻塞**。核新生产tenant/reader-writer最小身份、预算仅生产授权、一次性新组起点、原group/unknown保持、模型摘要一致、两服务healthy/readyz及fused订阅。独立比对15容器快照恰仅API/Agents改变、其余13对象一致；新raw Kafka合成告警15事件/14工件、5个授权GET200、新组仅p1前进一条且追平end，普通预算responded/settled。

7个可见回复28216tokens（首次2048/graph26168），graph/报告running且completion partial、六轮/软预算、缺源和不受支持结论如实保留；不宣称自治质量、硬预算边界、全部迁移或标书满足。首次及Deep3—6轮仅持久prompt副本截断，不称实际请求截断。旧C2/原5/15不改，无旧输入重发/Git提交/厂商执行。独审同时扫描公开新增材料，生成token/私钥模式0命中。详见[发布回执](../../../docs/operations/service-v1-release-20261022.md)和[JSON](../../../docs/handoff/service-v1-release-20261022.json)。最终包/manifest窄复核仍限定ACCEPT：21项、60156字节，13份正文及6份辅助文件与当前源码一致，SHA256 `89e3b927c677ae08263a5ad38a40d0a0b124a9dbe2c23e30aeb9c5c5cd16e803`，凭据模式0命中。本条不重复业务/模型验证。


## 2026-10-23 页面V1字段文档与取数证据结束独审

未参与编写者 `ui_display_audit` 独立核本批文档、线上原GET/工件及本地持久化/冷读样例，最终限定 **ACCEPT，0项本批必须修**。发现的图范围路径和“节点数/类型数”措辞已修：当次范围取 graph_result.context_bundle.attack_context.query_scope，工件JSON先解析content；样例3跳可达6节点、5类型。交接JSON所保留Alert/Run/上下文、工件片段/MD与原件逐值一致，原件及本地源码hash匹配。

验收范围为[产品展示说明](../../../docs/integration/v1/alert-investigation-ui.md)与[字段实值](../../../docs/integration/v1/ui-field-verification-20261023.json)：四页/90项信息的取数、空态、线上/本地/数据库/待补边界；41 GET200、21工件hash与字节、8本地定向用例。不代表前端实现、所有status分支、完整schema/RLS、调查内容质量或生产发布通过。两次探针初始失败与search无效问题保留，原5/15/旧失败不改。

独审版本SHA256：文档 `2c60fd6e8014370255c91b8e86fa983760eaca46c1535ab0c2459a56d03a70ed`；验证JSON `18fa682ea34e073519668173a6d9a01684963e8a6d3ad38ae45658b432819419`。当时选定版本及manifest曾保存于 `.local/versions/ui-display-v1-20261023/`；用户随后要求清理旧文档版本，该文档副本包已删除，原始验证数据保持。以上hash是当时审查版本，新统一文档的审查另记下节。没有新模型/Kafka/部署/业务改码/Git提交推送；专用临时PG已stop并自动删除。


## 2026-10-23 数据库直查与唯一最新文档增量独审

未参与编写者 `ui_display_audit` 对数据库映射及后续合并做窄独审，最终 **限定ACCEPT，0本批必须修项**。核六核心表和类型、SQL38列、每例8条JSON路径；纠正first_seen_at为claim路径首次人工认领/确认，非页面查看或自动分诊时间。合并后的90项页面信息、数据库字段、HTTP和实值/SQL附件齐全，主文档及索引链接有效；两份旧稿和指定旧文档快照包已按用户要求删除。

唯一主文档为[alert-investigation-ui.md](../../../docs/integration/v1/alert-investigation-ui.md)，SHA256 `6e4ccc0c7e7df8730bc5df140992cf4f90f34d778c81a91f70fe867361e9e63a`。不再保存另一份文档副本；当前校核元数据在 `.local/verification/ui-v1-20261023/latest-document-check.json`。旧审查hash为历史事实，不能代替本版本hash。结论仅覆盖文档映射/合并完整性；新增SQL仅静态校核，无生产重跑/新模型/改表/部署/Git提交推送，原5/15及旧失败保持。


## 2026-10-23 文档按页面/表/取数/HTTP顺序重排独审

未参与编写者 `ui_display_audit` 窄复核后 **限定ACCEPT，0本批必须修项**。四主部分及补充章节符合用户顺序；第1章90项产品字段无丢失，第3章数据映射和六组新SQL的表列与目录一致，HTTP方法/用途与源码一致（escalate仅升等级），链接有效。线上/本地/空态/完成度语义保持。新增查询仅静态核对，未运行生产SQL，原41 GET/21工件/8用例证据复用。

唯一主文档SHA256 `5fb8885e8ab241d3c97af7ae79698610bedf5fbf4534e292aafd2308318d3a9d`，当前静态核查元数据覆盖 `.local/verification/ui-v1-20261023/latest-document-check.json`，未新建旧版本副本。结论仅覆盖本轮文档重排及映射，未改业务代码/数据库/服务，无新模型或Git提交推送，原5/15及旧质量/预算/unknown记录保持。


### 2026-10-23 页面示意附件结束独审

未参与实现者 `ui_display_audit` 只读复核7份示意与主文档/实值JSON，首次指出I12混用调查材料与首次Fusion快照；已明确 `graph_result.raw_alert` 本例无status，`source_snapshot.status=new`仅属首次交付快照。修后限定 **ACCEPT，0本批必须修项**：四页七图、90项字段各覆盖一次且名称一致，时间/状态/用量/工件实值匹配，生产/本地及拟建控件边界明确，所有相对链接有效。独审不覆盖渲染，主执行者另以Mermaid 11.12.0实际渲染7/7并核布局；之后仅调字号、换行宽度和短分区标题。最终文件hash见 `.local/verification/ui-v1-20261023/wireframes/document-check.json`。


## 2026-10-23 页面功能必要性与数据可得性结束独审

`ui_display_audit`核原版render/handler与90项必要性、`local_display_data`核90项路径/值/空态及版本边界，两者再审最终合稿，均**限定ACCEPT，0本批必须修项**。发现的A27组合字段、技能源采用数、工具默认零耗时、报告空态及MD/JSON发现ID冲突均修正；最终D01—D08为文档已修，G01—G08是后续接入条件。

独立复算21份工件正文hash/字节及21个Run/事件关联；六核心表167列、7份本地源码/测试证据和2份本地样例hash保持。主执行者静态核90编号/名称、七Mermaid用途声明、164本地链接/51源行有效、凭据特征0命中；本轮未重新渲染截图。原change strict本轮已通过，未扩业务测试。结论只覆盖文档、产品取舍及读合同，不代表所有90项非空、页面/聚合后端实现或调查质量验收。

最新[审计](../../../docs/integration/v1/ui-functional-data-audit.md)SHA256 `f3eee64388b9b6fad4baf5c78d479d672a28c0ab3aef4dde9966506a4e24b567`；[JSON](../../../docs/integration/v1/ui-functional-data-audit.json)SHA256 `95be20e995c31a7a47f47016a69009c354a220e0b69b37a8928081f65fd41b5d`。独审选定版本hash保留在JSON，最终只补审计回执；最终文件与链接校核元数据在`.local/verification/ui-v1-20261023/final-audit-check.json`，不另存旧主文档副本。原5/15与旧失败保持，无业务改码/新模型/部署/Git提交推送。
