# PROGRESS.md 整理前历史快照

2026-11-08按用户要求迁出。本文只供追溯，**不是当前工作指令或实时进度**；其中“当前”“最新”“待授权”等均指原记录时点。现行规则见[根AGENTS](../../../AGENTS.md)，现状见[根PROGRESS](../../../PROGRESS.md)。

原正文完整保留，仅为迁移位置调整Markdown相对链接；原有Windows路径和失效引用按历史原文保留。整理说明见[归档索引](2026-11-08-root-docs-cleanup.md)。

---

# 2026-11-08 统一模型调用原则，进入Case只读梳理

用户确认的五点及第5点“明确结论与输出内容”已整理到[设计12-18](../../../openspec/changes/complete-socai2-investigation-chain/design.md#12-18按环节目标设计模型调用的共同原则2026-11-08)，并补充程序分工、来源范围、兼容、校验/局部保留、质量效率和配置原则。当前只核代码、旧Case三请求及三份云/邮件材料的纯投影，未实现Case适配；I关键发现/待核交接缺口、旧Case字段提取范围与C6重复分析负担有[离线依据](../../../docs/operations/evidence/case-boundary-design-20261108-01/current-audit.json)。0新模型、DB连接、远端、Case；A/I r5及其质量问题保持，下一按每步目标和数据合同推进。

# 2026-11-08 告警与事件正式接入21及新批对比结束

21当前v1.2-20261108-r5（处理组件r2）：A结构模板/五字段与I结构模板/四块已适配原存取字段，交付与待核分离。实际profile/策略hash/读取开关、6服务健康已核，4外围容器身份保持。用户明确批准API限定只读授权，脚本/profile/新装升级同步，无DDL/RLS/写权限变化。首轮51GET的503保留，最终51/51为200、1,910字段/内容核对一致，29表快照未变。

新批3合成告警经Fusion归1事件，3A/1I共4模型、18,233tokens、0重试、0Case。登录截断、进程重复引用失败，网络完整且needs_review，I failed/partial未采用。比历史参照输入少54.46%、总tokens少41.50%、步骤时长多27.08%；非受控AB，模型质量仍待迭代。[完整分析](../../../docs/investigation/ai-production-rollout-20261108.md)。

81不同纯检查、2隔离PG方法/8ASGI GET最新通过，3旧方法因fixture权限失败未计通过。4177读取复核已发布，共7登记，旧文件/其他批次保持，本机23登记。r2/r3配置问题、r5初次健康未就绪与审批过程均留原件。3.22/3.29限定技术接入完成，3.23质量/结束审计及1.2整体、Case后续保持，无提交推送。以下为前阶段记录。

# 2026-11-08 事件多类型实际执行与字段兼容验证

3事件/7告警/6材料经I执行器、本机隔离PG及真实21模型/tokenizer完成3次请求，9,048tokens、0重试；34个原ASGI GET确认材料/原答/片段/状态可读。三Run实际failed/partial：E1/E3单成员引用错配，E2业务术语S3被旧编号正则误认。候选I按配置只识别实际N…_S…正文引用，E2原答离线通过；旧Run与原答不改，另外两份仍拒收。正文质量未通过，批次结束不重派。

42纯检查、3隔离PG方法最新通过，26GET含2个预期404；描述、content_text/raw_json、分页/反向关系、0/false/空列表及缺材料保持。初PG断言键错误保留，模型/工具为替身。无新增全文搜索API或DDL。交接说明已澄清：run为接口单次执行对象，runs为数据库表，同一state。

本机6新增记录核18主体/34工件/6I状态；3真实测试记录已追加在线4177，13文件/14HTTP逐字通过，原3登记、容器、模型配置保持。见[摘要](../../../docs/operations/evidence/incident-integration-validation-20261108-01/summary.json)和[发布回执](../../../docs/operations/evidence/incident-integration-validation-20261108-01/workbench-publication.json)。这只发布静态快照，21按需I仍未切换；3.29、A相关3.22/3.23及整体质量未完成，Case后置，无提交推送。以下为前阶段记录。

# 2026-11-08 事件交付状态本地修复与交接

I已按实际有效保存内容区分完整/部分/无交付；未决问题与复核状态单列，明确未分析或拒收缺项仍保留。原API、模型原答、摘要/结论/成员/引用路径保持，新说明放现有diagnosis JSON可选字段；无DDL。完整事务保存和局部保留同步Run状态，过期/未采用与交付分开，失败/unknown不伪装成功。

本批51不同纯检查最新通过、7隔离PG方法通过、15 ASGI GET核对；5事件/10告警/19Run已导出并追加本机静态页，15主体/71工件逐值一致。旧批11Run/44工件逐表不变，初次展示断言失败及修复均保留。配置/部署文件来源同步并核临时包导入，0真实模型/工具/21动作；[证据](../../../docs/operations/evidence/incident-delivery-validation-20261108-01/summary.json)、[取数说明](../../../FRONTEND_BACKEND_HANDOFF.md#85-事件交付与待复核的读取本地已验21待发布)。

3.22仅I本地部分完成，A和线上验证仍待；3.29还需完整检索/空态、多类型新批实测及21同源受控发布。实际4177尚未更新，语义质量和Case后续继续独立推进；无提交推送。以下为前阶段记录。

# 2026-11-08 事件适配本地接入与存取验证

已按12-17顺序1—2接入完整冻结材料→结构化文本、同A实际回执交接、四块模型输出→原IncidentOutput。保留非空采集说明、原始正文、未知业务字段、原UUID与原查询路径；不重新归并、不改写旧分析。profile/映射/提示走配置，旧模式默认保持，新旧快照按各自版本核新鲜度。

49个不同纯检查和7个不同隔离PG方法最新通过；10个GET确认原描述、成员、材料、诊断和A回执可读。测试使用真实本机隔离PG和模型/工具替身，0真实模型。失败和修正过程保留，3事件/6告警/11Run快照已追加本机静态记录，尚未同步21的4177服务。见[证据摘要](../../../docs/operations/evidence/incident-boundary-integration-20261108-01/summary.json)及[当前输入](../../../docs/operations/evidence/incident-boundary-integration-20261108-01/input-current.txt)。最终查询标签调整由纯检查覆盖，已存PG请求保持各自实际profile指纹。

3.29仅部分完成。下一处理3.22的I交付完整性与待复核分开展示，再完成多类型新批和21按需验证；本轮不把结构/存取通过当正文质量通过。没有DDL、生产切换或提交推送，Case继续后置。以下为前阶段记录。

# 2026-11-08 下一轮先接通事件真实流程与字段兼容

按用户“规划一下后续”，在[现有12-17](../../../openspec/changes/complete-socai2-investigation-chain/design.md#12-17按模块目标梳理后续模型环节2026-11-08)记录四步计划：补完整冻结材料/非空说明/同A Run实际回执；将候选前后适配接入现有I执行器；验证落库、GET、原字段检索/成员证据关联与I交付状态；最后新批多类型事件、21按需入口和4177真实Run验证。3.29登记未完成；原字段路径、业务含义、版本新鲜度与历史读取必须保持。模型正文质量按原路线独立迭代，不把结构通过当质量通过；A候选切换与Case后续工作不纳入本轮隐含范围。本次仅规划，没有新代码、模型调用、DB测试或部署。以下为已结束实测记录。

# 2026-11-08 事件新版输入实测完成，正文质量未通过

本轮`incident-input-validation-20261108-01`使用已审阅结构映射v2文本及四块输出，对同一三告警事件调用1次，0重试，44.123秒。输入1784/输出2236/总4020tokens；对历史记录9142输入减少80.49%，不是同轮AB或提速证明。Schema、引用和原I解析通过，保留3成员评述、1事件发现和2待核问题；模型仍判待复核。正文继续扩大进程启动效果、沿用A2错误情报查空，并将时间顺序作偏强攻击链解释。action/时间字段未丢；A2原回执skipped而旧分析写查空，真实回执原本就未交I，不能归因于本次删除。见[完整结果](../../../docs/operations/evidence/incident-input-validation-20261108-01/summary.json)与[问题逐项核对](../../../docs/operations/evidence/incident-input-validation-20261108-01/semantic-review.json)。

[4177事件测试](http://127.0.0.1:4177/comparisons/incident-input-validation-20261108-01/index.html)已显示实际输入、任务指令、Schema、原答和装配结果；5文件/3下载逐字与HTTP、IAB显示核验通过。旧告警批次、远端3Case/本机6Case及容器保持。22离线复验、Ruff/JS/OpenSpec通过；13旧证据及代码hash、运行配置/模型路由不变。0业务Run/DB写入/实际补查，未改候选输入或模型原答、不切生产/不提交推送。3.28仅完成测试展示，生产存取兼容与A→I材料交接仍待，Case继续后置。以下为之前各阶段记录。

# 2026-11-08 路线确认，继续梳理各模块的模型职责

I候选按用户逐行意见升级结构映射v2：内部统计/状态大JSON/评分细节退出模型输入，异常材料限制转短句，字典解释已知类型，未知业务字段保留；无针对样例值的规则。定稿49行3607B，相对原文-85.17%，44观察字段/3分诊原文保持，22项离线与Ruff通过；旧输出合同回放相同。新输入与字段清单见12-17及evidence/incident-io-offline-20261108-02/20261108T070642943545Z。仍是本地候选，未实测模型或改正式存取/服务；旧批及中间稿保持。

事件已落地独立离线候选：输入正文24322→14782字节（-39.22%），保留当前业务观察/既有分析；四块输出通过原解析器还原为同一份3成员评述/8发现/2问题。16项最新通过、Ruff通过，初一项测试字段键错误已修；旧答引用的12项已退出新输入，按新集合拒收，未改原答冒充新结果。9份A回执只清点；非空描述等边界为合成片段验证，真实读取/冻结交接未做。见12-17及evidence/incident-io-offline-20261108-01/20261108T063458388075Z；3.27仅限定离线完成，未调用模型、写库或切换服务，Case后置。下面为前期设计讨论状态。

I兼容设计继续收敛：已核实成员评述确实保存并进入原页面findings，第一版保留简短members及模型分析限制，经程序适配原I字段；不直接采用前稿删除提案。补原件统计、字段来源/保存映射、类型化输入和未知类型回退、非空描述与0/false边界的待验清单；旧3告警description原本空，不能据此证明非空兼容。当前完成只读分析与设计，候选代码/离线装配/模型实测尚未开始，Case后置。

最新范围：先把事件诊断梳理完整，Case后续讨论。I具体候选已写入12-17：整体诊断（摘要/结论/来源）、关键发现、待核问题；程序管理目录/映射/执行信息，不再要求模型复写每条A分析。去掉members须同步处理当前成员发现与覆盖读取，不能伪造“已分析”。仅为设计提案，生产合同保持；下一核I输入业务字段、程序装配与独立验证方案，尚无新模型批次。

用户进一步明确I重点为既定事件的整体解释，删除“评审哪些关联有依据”这一任务。成员归并作为既定范围；证据引用/程序范围校验用于结果定位，不要求模型重审关联或重新分组。已同步12-17设计，本次无实现修改。

继续梳理已形成I输入/输出第一版讨论稿：行为原件与既有A判断分别提供，拟交接同A Run真实查询回执；输出围绕整体诊断、关键依据和待核事项，字段数量未定。确认Case当前模型输入未直接接收I的findings/open_questions，而数据库及读取已有这些内容，后续须明确交接；不能将建议当已执行。仅设计记录，未改源码/Schema/DDL或新发模型。

用户认可围绕业务目标优化模型输入/输出的路线，正文质量留后续多轮迭代；继续梳理后续流程。五字段只用于告警分诊候选，各模块分别明确目标、必要材料和输出合同，不能将五字段机械用于事件诊断/Case。已只读核现有I源码和保存原件：I读取成员行为、有效A分诊和归并背景，一次模型汇聚；当前7类输出，不重跑A查询、不自动创建Case。接下来以事件诊断的业务目标、A→I材料交接和程序/模型职责为讨论入口，见[设计记录](../../../openspec/changes/complete-socai2-investigation-chain/design.md#12-17按模块目标梳理后续模型环节2026-11-08)。本轮仅文档，不改业务逻辑/DDL/生产配置、不新增模型调用，旧测试质量结论保持。

# 2026-11-08 整理版单轮测试完成，4177仅展示本轮

按用户要求只跑v3，9份已有冻结材料各1次，9原答/16,918tokens、0重试，Schema/核心解析全部通过。2个良性、7个待复核，平均HTTP6.09秒；正文仍有TCP/443写HTTPS、180次运行扩大为全成功、目的分类当域名、MFA主动意图推断等错误，整体质量未通过。待复核不算方向误判；S3标签口径、S6时间计划材料限制保留，不报准确率。见[本轮报告](../../../openspec/changes/complete-socai2-investigation-chain/alert-prompt-validation-20261108.md)。

[4177本轮入口](http://127.0.0.1:4177/comparisons/alert-prompt-validation-20261108-01/index.html)已发布，29文件/27下载逐值一致、9份展示原答和34HTTP、浏览器切换/指令展开/单批列表核验通过。旧两组对照184静态文件移可恢复归档，两端hash一致；原始证据不改。远端3Case/本机6Case及全部容器保持，无重启；原模型路由/配置不变，0业务Run或DB写入。测试/发布配置及部署来源清单同步，3.26完成只代表执行和展示；生产分诊未切换，3.23与整体质量继续待。无提交推送。以下为各阶段历史记录，旧对比URL已退出当前站点。

# 2026-11-08 五字段指令v2对照结束，回到原文整理

独立24调用/46,676tokens、0重试，两组Schema/核心解析均12/12，但v2候选新增查询状态、动作效果和厂商归属错误。输入-0.81%、输出+17.26%、HTTP+18.30%；S3/S5/S6转待复核，不计方向误判但不证明改善。本候选不采用，五字段方向与原质量缺口保持。83份旧证据指纹、运行配置/模型路由不变，0业务Run/DB写入。4177已追加[双指令对照](http://127.0.0.1:4177/comparisons/alert-prompt-comparison-20261108-01/index.html)及72份下载，74文件核对、24输入/原答逐值与浏览器A1/S5验证通过；静态发布无容器重启，旧3Case/首页保持。[完整报告](../../../openspec/changes/complete-socai2-investigation-chain/alert-prompt-evaluation-20261108.md)。

用户进一步要求结合OpenAI/Claude官方提示词实践从原版优化，已完成[结构整理与逐项规则映射](../../../openspec/changes/complete-socai2-investigation-chain/alert-prompt-restructure-20261108.md)和独立v3文案。保留原具体边界，统一任务/判定/来源/事实/输出分区；v3未调用、未启用，不能复用v2测试声称通过。Ruff/JS/远端脚本语法通过；3.25比较任务完成，3.23及整体质量仍待，无提交推送。

# 2026-11-08 4177 已增加告警三组输入输出对比

按用户要求今天只补展示，后续建议沿精简输入/五字段继续开发、保留八字段对照，模型正文质量问题未继续修改。工作台首页增加[告警输入输出对比](http://127.0.0.1:4177/comparisons/alert-io-comparison-20261108-01/index.html)：9样例/36次已结束调用，实际用户输入、任务指令、输出Schema、模型原答、校验及程序装配分别可查，108份JSON可下载，tokens/耗时沿实际回执展示。没有把隔离对照登记成业务Run。

配置及发布来源已同步仓库；21仅工作台新增展示文件挂载与静态材料，r1基础发布、镜像、其他容器和远端3个Case保持。110份远端文件核对、36份展示输入/原答逐值检查、6次HTTP读回与浏览器选择/轮次/展开/导航通过；本机静态6个Case登记保持。7个既有测试最新通过，首次2个回环监听被沙箱限制，放行后定向通过；Ruff/JS语法通过。见[发布回执](../../../docs/operations/evidence/alert-io-comparison-20261108-01/workbench-publication.json)、[核验回执](../../../docs/operations/evidence/alert-io-comparison-20261108-01/workbench-verification.json)和[使用方法](../../../deliverables/investigation-validation-20261106/README.md)。3.24完成；3.23生产接入、正文质量和完整结束审计仍待，本次无新模型/业务库写入/提交推送。以下为前期实测状态。

# 2026-11-08 告警模型边界三组实测完成，正文质量未通过

用户在设计之后明确要求先跑数据。已完成隔离候选与36次真实模型比较：三旧例各两轮、六个既有合成模板的新实例各一轮，现版八字段/精简输入八字段/精简输入五字段。0重试，107,544已报告tokens，原答逐格保留。平均输入tokens为4299/1774/1600，HTTP耗时10.77/8.59/6.49秒；12/12/12份Schema有效，9/9/12份核心输出通过现有解析。前两组S1/S5/S6主要依据混入标签角色拒收，五字段组生成约束避免本批错配，但不证明正文正确。

仍有A2未查写查空、S6将180次历史扩大为全成功、名称推测和来源含混。名义六例未出现良恶方向反转；S3误报/良性标签口径及S6新时间/计划未对齐限制结论，待复核不算判对。输入只做结构处理、原文保留；五字段组同时改任务说明/Schema，不将全部效果归因于字段数。12离线适配检查通过，代码/原快照/运行配置/路由保持。见[实测分析](../../../openspec/changes/complete-socai2-investigation-chain/alert-io-evaluation-20261108.md)、[统计](../../../docs/operations/evidence/alert-io-comparison-20261108-01/summary.json)、[语义复核](../../../docs/operations/evidence/alert-io-comparison-20261108-01/semantic-review.json)。生产未接入，无DB/部署/业务Run/新4177记录，无独立结束审计；任务3.23及整体1.2质量不核销。

另核用户选中的11-07-01 history：四行来自同批两告警各两种对象匹配，不是旧批残留混入；页面为当时保存的快照。查询行数与去重告警数需区分，未删历史数据。以下为前期设计记录。

# 2026-11-08 告警输入输出设计及现版对照（设计阶段记录）

按用户最新要求只设计 A 告警，把模型限定为有明确输入/输出的判断环节。已核当前真实请求：原始观察字段在标准化/原始嵌套中重复，历史分诊随匹配关系重复，内部元数据及空值仍进入正文。已完成[设计稿](../../../openspec/changes/complete-socai2-investigation-chain/alert-judgment-design-20261108.md)、三个告警的当前输入/原答、固定模板文本、后台证据映射及[离线字节对照](../../../openspec/changes/complete-socai2-investigation-chain/alert-judgment-design-20261108/comparison.json)。核心判断输出为3项，完整 A 候选保留已有置信度/建议后为5项；程序负责其余保存/读取对象。待办 3.23 未勾选，新版生成质量、实际 tokens、后端兼容和告警全链未验证，不扩到 I/Case；本次无业务代码/部署/新模型调用。

按后续讨论补齐字段语义与输出关联：核实际 Fusion 投影、冻结输入、ORM、发布和页面读取，明确日志动作/时间/账号、上游标签、历史、人工反馈及查询回执的不同含义；列出候选输出到现有分诊/解释工件及当前指针的映射。请求前绑定身份与材料版本，输出后检查引用、字段一致性和输入新鲜度，不靠模型返还主体 ID 或名称关联。字段合同与采用规则也是验收条件，不能仅验输入缩小。

用户指出初稿历史上下文丢失，已核实：A1 自身登录结果仍在 E1；A2/A3 删除旧分诊理由后丢失历史登录成功、授权依据缺口等既有分析信息，history 查询本身又未返回历史原始动作/结果。初稿及原指标保留，语义完整性标为未通过，撤回整段历史理由默认删除规则。已列当前 RawAlert 33 顶层字段和各业务块的来源/语义/模板条件，开放厂商字段及非空资产/情报/人工输入仍需验证；先核信息完整，再衡量大小。核对 3 份旧输入与实际请求一致、原快照指纹不变；见[语义复核](../../../openspec/changes/complete-socai2-investigation-chain/alert-judgment-design-20261108/semantic-review.json)。本轮仍仅设计，无业务实现或新模型调用。

最新讨论明确：仅精简结构、去掉确定重复、将已知结构化字段按模板拼接；描述及关联告警的已有分析/建议等文本原样保留，加来源和证据号即可。程序不理解/改写自由正文，验收核原文字段完整传递；本轮不补读历史原件。设计已按此收窄，初稿仍保留为反例，没有新请求或运行修改。

# 2026-11-08 新增 A/I 交付状态待修项（仅记录）

用户确认：告警分诊和事件诊断按本阶段实际结果判断是否完整交付，待复核单独展示。已定位 A/I 共用发布逻辑固定写入 `delivery_state=partial`；本批三个 A 和一个 I 实际通过现有校验并保存，不能由该固定值推断存在交付缺项。已纳入 OpenSpec [12-13 方案](../../../openspec/changes/complete-socai2-investigation-chain/design.md#12-13ai-按本阶段结果判断交付完整性2026-11-08)及任务 3.22，补齐完整待复核、实际局部拒收、失败/unknown 与 DB/GET/4177 一致的验收条件。尚未修改业务代码、历史数据或页面，模型正文质量问题另行保留。

# 2026-11-08 1.2 续修已发布，新批走到模型最终报告

网关300秒、A判断与依据匹配约束、程序查询状态、unknown系统收尾合同已实现并发布21，版本 `v1.2-20261108-r1`。六服务和当前入口/954冻结文件核验通过，配置与部署来源同步；61纯检查、5不同隔离PG方法、43实际XGrammar的16种判断/依据组合通过。见[发布汇总](../../../docs/operations/evidence/v1.2-followup-20261108/deployment-summary.json)。

新批 `production-multialert-20261108-01` 使用tj0001、正式aisoc/socai2和3条独立演练输入，7次模型全部返回，71,576tokens，无重试。I/C3/C6各约60/66/74秒，未被旧45秒截断。三个A needs_review/null有效；C3无交集cloud引用局部排除，其他有效内容继续。一次认证查询成功0行，Deep不额外查网络而给unresolved答；C6完成，Case Run completed/partial，1份model/accepted/uncertain结果采用，关系图和3条原材料unknown证据索引保存。Case `2b37f5b3-862b-52cc-84bd-86db50dd3ad4` 的[4177工作台](http://127.0.0.1:4177/cases/19e248b1ba587dac72ea5b6b2eb76ad63c3fda14a10f144d226b1c705312d00f.html)可查。

查询正文问题仍未解决：A2输入/落库明确未查TI，但正文写查空；还发现主机名、时长、人工来源与对象关联措辞错误。程序事实正确、形式accepted和needs_review不等于语义质量通过。unknown报告修复经隔离PG验证，本批正常结束未触发该分支；旧unknown原行与24工件保持。实际认证补查和Deep答均送入最终输入，但不能称所有新建议或网络补查已执行。见[新批汇总](../../../docs/operations/evidence/production-multialert-20261108-01/summary.json)、[剩余问题](../../../docs/operations/evidence/production-multialert-20261108-01/problems.json)及[限定结束复核](../../../docs/operations/evidence/production-multialert-20261108-01/independent-review.json)。

29表199行、5Run/35Step/88工件，156正常GET/5预期错父404、7,343批量及5新增检查通过；两端4177与DB同ID和状态。首次核对器覆盖DTO键错误已只读离线修正，原响应/失败保留。Agents仍暂停，位点34/37/42、租户无限额保持，积压13条；未新增DDL/权限、H或外部材料，未提交推送。此次执行/数据闭环完成，1.2语义质量及未完成任务不核销。

# 2026-11-07 1.2 新批测试：数据可查，完整模型调查未通过

`production-multialert-20261107-02` 已执行3条演练告警→实际Fusion归并1事件→3A/1I→单Case单Run。正式current入口使用 `v1.2-20261107-r3`，归并依据已保存。5次模型尝试中3份原答、16,280已报告tokens，2次用量未知，无重试。A1采用needs_review；A2/A3核心因判断与依据冲突被拒，各2条合法建议保留。I和Case C3均HTTP408：应用300秒已生效，但运行中的LiteLLM网关仍45秒，上一轮发布漏对齐网关配置。本批只定位，未修改配置或重派。

Case `1db4d62b-2dfc-5321-bba8-99b8f9c3b35d` 的Run为unknown/none，C6仅系统收尾；无有效Case模型结论、Result或证据索引。预先的C4.materials已完成，但未进入模型决定的C4/Deep补查或C6模型总结。还发现A2把跳过TI写成查空，以及系统报告failed/partial与Run unknown/none状态不一致；共[四项待修](../../../docs/operations/evidence/production-multialert-20261107-02/problems.json)，不改写本批原答。

29表148行、5Run/29Step/59工件已保存，131个读取请求（126正常200、5预期错父404）与5,484项批量/5项新增读取检查通过。59工件hash/长度、553非空内部FK及输入原件一致；重启本机只读API加载当前路由，本机/21工作台登记相同ID集合。Agents仍暂停、提交位点34/37/42保持，积压10条。见[本批汇总](../../../docs/operations/evidence/production-multialert-20261107-02/summary.json)与[限定独审](../../../docs/operations/evidence/production-multialert-20261107-02/independent-review.json)：执行/证据ACCEPT，质量/整链NOT_PASSED。未改业务逻辑、DDL、权限或网关配置，未提交推送。3.7/3.12/3.21及完整1.2继续待；先修实际超时链路和输出/状态问题，再以新批验收。

# 2026-11-07 21 已发布统一 1.2 运行版本

用户要求先将21的混用版本统一。已按 [release-v1.2.json](../../../deploy/aisoc21/release-v1.2.json) 发布并激活 `v1.2-20261107-r3`，manifest `a222752c062aefaa2cda249e4387a03790eef4b2302ab8bcea48efd41fd9d9f9`。主API、Fusion、暂停中的Agents、调查投影和4177工作台五服务健康；正式按需入口与 `/opt/sting-aisoc-socai2/current-v1.2` 同指本份源码/profile。API567/Fusion64/Agents293文件及工作台952绑定文件逐项hash核过，28项直接/独立检查通过。旧镜像、配置和指针回退材料保留，未演练回退；r1/r2候选未部署，原预检失败保留。

正式按需入口只读check通过，使用 `aisoc`/既有processor身份、`aisoc-investigation`/`vllm_grammar_v1` 及1.2策略（单请求300秒/整轮1500秒/最终预留300秒）。API启动迁移显式false，无本批DDL、模型生成、旧调查重派或位点重置。4177 Case列表200，原Case读回3告警/1事件/5Run/30Step/67工件，共29表167行。Agents仍暂停且三项租户额度不限制，原分区位点34/37/42和7条积压保持。

[发布汇总](../../../docs/operations/evidence/v1.2-implementation-20261107/unified-release-summary.json)与[运行读回](../../../docs/operations/evidence/v1.2-implementation-20261107/unified-r3-readback.json)为当前依据。18010旧investigation-api与18020旧next-api仍保留，不能当作本次1.2入口；主API的新socai2 HTTP路由开关仍关闭，本次没有扩接口/角色，实际验证的是正式按需处理和4177读库。默认租户context/writer、跨流程已有A结果接续、Fusion新批归并依据和真实多告警/补查/H后轮仍待，不核销3.21及1.2整体质量。部署后[限定独审](../../../docs/operations/evidence/v1.2-implementation-20261107/unified-r3-postdeployment-review.json)ACCEPT/0必须修；独审依据源码、独立纯检查及19份现场回执，独审自身SSH未到远端。下方“未部署”均为此前阶段。

# 2026-11-07 Agents 三项租户总额度已取消

按用户明确要求，滚动24小时10次、20万token和最多1笔未结算三项限额已通过空 `AISOC_TRIAGE_BUDGET_POLICY_FILE` 关闭，适用于全部租户。21只重建Agents一次，沿原镜像，实际环境仅改变预算路径和消费者暂停开关；两个租户的实际 `policy_for` 均返回None。部署Compose、计划和操作脚本已同步，新初始化 `budget=null` 不再生成有限额度文件；旧预算预约和未知执行记录保持，不清历史、不重派。

实际 API/Agents 就绪均200；Agents消费者明确暂停，不把服务健康写成消费恢复。Kafka组三分区提交位点仍34/37/42，末端37/39/44，组Empty，读前后不变。本次无模型调用、业务数据写入或位点提交。见[实际配置](../../../docs/operations/evidence/v1.2-implementation-20261107/triage-unlimited-runtime.json)、[部署来源](../../../docs/operations/evidence/v1.2-implementation-20261107/triage-unlimited-deployment-sources.json)、[最终就绪](../../../docs/operations/evidence/v1.2-implementation-20261107/triage-unlimited-final-readiness.json)及[限定独审](../../../docs/operations/evidence/v1.2-implementation-20261107/triage-unlimited-limited-review.json)。下一继续核默认租户上下文/写入配置和待消费消息的实际执行状态，再验证消费恢复；单次上下文、超时和Case执行合同未因这三项取消而改动。以下无服务更新等陈述为各阶段原状态。

恢复前进一步只读核了全部7条积压及7个租户凭据映射：默认租户在全部映射中缺失，另一租户现有key有效。7条旧Agents确定性Run均无领取记录，但其中3条告警正是已结束 `production-multialert-20261107-01` 的A/I分析输入；旧Agents防重与新版人工A/I是不同账本，不能据此称未分析或直接放开重跑。位点仍未动、无新模型。见[恢复核对](../../../docs/operations/evidence/v1.2-implementation-20261107/agents-recovery-summary.json)。消费者继续暂停，恢复需同时解决默认租户映射和已处理消息的接续规则，不能跳位点；不因三项不限额而扩大为重复执行历史批次。

# 2026-11-07 1.2 实施进展：局部引用、冻结事实和按需入口配置继续落地

按用户追加的开发优先授权，给既有 reader 补 `public.assets/public.users` SELECT，取消专门读取函数方案。此前失败的 4 个资产 GET 和既有 Case GET 均 200；资产当前为空，有值资产/负责人在独立本机数据库验证。新库初始化/V1 升级共用增量，V1 原件不改；7 安装、20 读取/profile 检查通过。正式 GET 使用既有 API 进程，尚未以新代码重启，不冒充部署验证。

C3/C6 现在允许领域关注成员与跨成员发现相交的引用，保留发现全范围；领域工件另存可选 `focus_scope`，三份 JSON 合同同步且兼容历史。14 项合同检查通过。上述两项已[限定独立复核 ACCEPT](../../../docs/operations/evidence/v1.2-implementation-20261107/m0-m1-limited-review.json)，不是整个 1.2 完成。

容量和时限统一由 [配置文件](../../../deploy/local-investigation/investigation-policy.toml) 提供：单次300秒、Case1500秒、C6预留300秒；Case候选6模型/4工具/131072累计tokens，A/I各24000。C3输出4096/C6输出8192，默认留两次C6额度；更低显式次数按实际可用数保护。旧8KB/12KB/2KB门限改为文件中的准备上限，发送前由实际后端tokenizer计算完整请求、Schema/协议、安全余量和输出。计量前与生成前均检查预算，计量也受剩余时间约束。已核实际别名指向43的Qwen3.5-9B/vLLM、窗口65536；旧三告警26个必需值保持，C3/C6实测计量12688/18945tokens，0生成。当前计量只支持chat_completions，DeepSeek明确拒绝，尚未完成跨后端计量适配。

C3/C6空引用会收到具体路径、原因及当前来源列表，只纠正一次；原答、反馈、纠正答及校验分别保存。错误发现及依赖项局部排除，其他有效内容保留；C6关键判断无效时partial/rejected、conclusion=null，不自动采用。工具实际输入目录已加入用途、输入、返回字段、可答/不可答问题，认证日志明确不能查审批。

C6复用现有索引及校验器生成注册材料观察/冻结H目录，和报告/结果同事务发布。多个字段仍算一份材料，未知性质不猜；正常空目录、生成失败、过期输入分别留态。人工、撤回或已有判断目录保持，避免自动恢复撤回条目。新增Case活动去重读取及非Run来源正文入口，核租户、父主体、hash/长度；无DDL。120纯检查、22个不同隔离PG方法最新通过，模型/湖/tokenizer为替身；早期失败夹具和修正留存。两项限定独审ACCEPT，见[实施回执](../../../docs/operations/evidence/v1.2-implementation-20261107/m1-m3-local-implementation.json)、[M1/M2审查](../../../docs/operations/evidence/v1.2-implementation-20261107/m1-m2-limited-review.json)、[M3审查](../../../docs/operations/evidence/v1.2-implementation-20261107/m3-limited-review.json)。

最新续修已完成 A/I 局部引用保留、程序事实及按需入口配置的本地实现。A 核心判断严格有效时仅排除无效建议；核心无效不采用，I 总判断不通过时仍保存独立有效成员/发现/问题，旧判断保持。原答与 partial_review 分存，StageEntry.partial_analysis 可读；形状/身份不完整和 unknown 不挽救、不重派。程序从冻结材料提供名称、对象、厂商、活动/告警/入库/执行时间和各层等级，不改自由正文；事件部分成员不可推算全事件等级，Case 严重度不补值。标签按带出处版本词典解释，当前明确核对 TA0009/T1005，其他映射为 unknown。三份 JSON 合同增加可选 program_facts，A/I 解释/诊断及 C6 报告与实际输入逐值一致。

续修147核心纯检查、10个本批不同隔离PG方法最新通过，早期字段/原生UUID日期序列化问题与旧断言失败均保留；[续修回执](../../../docs/operations/evidence/v1.2-implementation-20261107/v12-followup-summary.json)、[A/I独审](../../../docs/operations/evidence/v1.2-implementation-20261107/ai-partial-limited-review.json)、[事实独审](../../../docs/operations/evidence/v1.2-implementation-20261107/program-facts-limited-review.json)。新事实输入使必需项从26增加到29，全部保持；[最新容量](../../../docs/operations/evidence/v1.2-implementation-20261107/facts-clock-capacity-token-measurement.json) C3/C6为16146/22403tokens，含输出及安全余量；本批两次冻结计量共8 tokenize、0生成，上文12688/18945仅为前候选。

21按需处理入口现在强制选择 [production profile](../../../deploy/aisoc21/production-profile.example.toml)，不回落旧镜像/库/角色/模型；策略只读挂载、安装与进程核profile/policy SHA，安装前复用完整policy校验。发布包和部署/probe入口一起更新。按需配置19项/5子检查通过，独审ACCEPT。完整源码构建已接显式build profile，21新候选 processing-20261107-r3 构建并断网核629源文件/语法/policy/C6内存收尾通过，image e349276b9289…；r2的BuildKit镜像ID解释错误保留，新候选配置经典构建器解决，5构建检查及独审通过。[候选回执](../../../docs/operations/evidence/v1.2-implementation-20261107/processing-candidate-r3.json)与[限定独审](../../../docs/operations/evidence/v1.2-implementation-20261107/processing-candidate-limited-review.json)。未执行正式install/check或切换运行服务；whole-services Projection/Fusion/Agents入口仍待适配。

仍未完成超大材料动态分配/摘要、候选实际部署配置与运行版本验证、Fusion版本/归并、Agents根因与实际消费、新真实多告警/补查/H后轮及整版审计。正式调查服务未更新，新批额度未固定，无新生成/生产业务写入/提交推送；本机隔离数据库内有明确合成测试写入。1.2尚未整体完成。

继续只读定位了两处运行根因：Fusion运行三个关键文件均为未生成correlation_basis的旧版；所核Agents三份源码与本地一致，默认租户消息却未配置预算，2026-11-06 12:09:08UTC于分区1/位点37触发KeyError→BudgetHold→消费窗口退出。目前组Empty、三分区位点差合计7，0/1/2位点34/37/42未改。下一需对齐租户/预算/context/writer和新批额度、保位点恢复并核实际分诊；本次没有恢复消费者或部署Fusion。见[诊断与原件](../../../docs/operations/evidence/v1.2-implementation-20261107/runtime-rootcause-summary.json)、[本段完整回执](../../../docs/operations/evidence/v1.2-implementation-20261107/v12-followup-summary.json)。

# 2026-11-07 版本 1.2 开始本地实施

用户已明确要求“openspec 开始实施”，并要求数据库/权限修复同时进入新库初始化与现有库升级脚本，不能仅在线上手工修改。当前开展 M0 配置与读取依赖：核实 `public.assets` 的空租户策略允许全部行，`public.users` 未启用 RLS，最初准备专门读取函数；用户随后明确要求开发优先、给足所需权限，现已取消该候选，改为既有 reader 对两表 SELECT，应用继续按认证租户过滤并只返回页面所需字段。V1 原件保持，新旧安装路径将复用同一增量并分别验证。后续仍按同一 OpenSpec 计划推进，未将任何未验任务勾选完成。

已按用户指定版本 **1.2** 合并 V1.1 F01—F16 逐项讨论、正式多告警批次和数据库/GET 新问题，统一写入[1.2 修复计划](../../../openspec/changes/complete-socai2-investigation-chain/design.md#v12-修复计划2026-11-07待实施)。12 个修复项覆盖运行配置/读取权限、完整容量/时限、程序事实/时间/等级、局部引用/跨成员领域/一次纠正、工具与摘要、归并依据/Agents、证据目录及数据交接；每项列原因、方案、代码落点和验收。按 M0—M4 推进，原修复仅回归，未生成、未实测和未接功能分开。

本次仅规划及更新任务入口；没有改业务代码、模型/工具预算、数据库权限或前端，没有新增网络/模型测试或部署，也没有创建 1.2 分支/标签、提交推送。新配置与合同数值在实施前收敛，数据库/隔离变更按既有规则确认。自动刷新/优先队列等 `inv-review.md` 想法后置；本版以 DB/GET 取数为准，前端跳转不是门槛。原模型质量与全链任务未核销。 OpenSpec strict、计划来源链接及 diff 检查通过；[限定规划复核](../../../openspec/changes/complete-socai2-investigation-chain/v1.2-planning-review-20261107.json) ACCEPT/0 必须修，仅适用于本计划。

# 2026-11-07 数据与 GET 核对：Case 详情已修复，资产读取缺权限

按用户最新范围，本轮只核数据库和读取合同，不实现或测试前端跳转。既有 `socai2_prod_reader` 的 `baseline_input_freshness(uuid,uuid)` 和 `task_feedback_signature(jsonb)` EXECUTE 已按明确授权用增量 SQL 应用；其他权限/角色/RLS/函数正文保持。原非空 Case 详情从 500 恢复 200，当前输入新鲜度为 current，但判断仍 system_only、0/3 覆盖。

同一批次只读导出 29 表/167 行与原快照一致，643 非空内部外键引用、64 个 Run 工件 GET 正文、全部 67 工件 hash、3 原始及冻结材料核对通过。135 GET 为 127 个正常成功、4 个错父子 ID 正确 404、4 个资产接口 500；6,185 项比较中 6,181 通过，失败仅为这 4 个资产状态。`public.assets` SELECT 缺失已用零行 SQL 确认，未顺带授予权限。负责人非空依赖 `public.users` 的权限也未具备，本批 owner 为空，非空路径尚未实测。

已将 F01–F28 本批数据状态、真实请求/响应及缺口补入[交接指南](../../../FRONTEND_BACKEND_HANDOFF.md#81-2026-11-07-正式库数据库与-get-核对)和[核对回执](../../../docs/operations/evidence/database-handoff-review-20261107/review.json)。三条成员归并依据未记录；Case 模型分析/独立证据目录未生成；人工任务、评论、探索、助手和响应均无本批数据；完整 Case 活动与若干服务入口待业务后端接入。不能把“已存记录可查”写成全部功能已闭环。

首轮比较器误用 Case 成员 DTO 的 id 字段，在 135 GET 保存后报 KeyError；改用真实 alert_id/incident_id 后离线对账，不重发调查。未新增模型、业务写入、前端修改或提交推送。本轮两函数授权与核查报告已限定独立复核 ACCEPT/0 必须修，见核对目录 independent-review.json；原模型质量和全链验收保持未过；下文是先前执行时点。

# 2026-11-07 多告警 Case 已执行并接入原页面，完整模型交付未通过

用户确认账号名 `tj0001` 后，已在正式 `aisoc` 默认业务租户创建该应用用户及本次最小权限：`alerts:read/write`、`cases:read/write`；无管理员权限、无数据库角色或 DDL 变更。正常 `/auth/me` 认证通过，随机密码和限时 API key 只存本机受限配置。创建前 0 用户/0 key 的预检原件保留。

本批 `production-multialert-20261107-01` 发送三条已冻结的合成登录/进程/网络告警，既有 Fusion 实际归并为事件 `dd77586c-4e3f-4de1-a4b7-18d1258189d0`。三次 A 和一次 I 均保存 `completed/partial`；A 三条为 `needs_review`。使用同一用户手动创建 Case `5942734d-1bea-5c0b-97fe-0d9ccde01858`，只启动 Run `4c870247-444c-4083-b511-db9791c32a17` 一次，实际 `failed/partial`，停止原因为 `model_view_not_ready`。共 4 次真实模型调用、13,548 已报告 tokens、费用未定价；Case 主分析/最终模型调用均为 0，没有重试。

Case 输入准备受现有 8,192B 限制，已选部分 7,778B，11 项按预算省略，其中事件诊断是必需项，导致 `required_model_input_unavailable`。三份原始 OCSF 与落库材料逐值一致，不能将此归因于原材料丢失。生产固定镜像 `socai2-processing:processing-20261106-r3` 的 `baseline_model_view.py` 与本机 hash 一致；分析/容量模块并非全部一致，已保存实际 hash，未部署替换。系统生成了交接 Result、system_only 当前判断和 C5 关系图；当前有效模型结论覆盖 0/3，不能称完整 Case 调查成功。

已导出本案 29 表：3 告警、1 事件、1 Case、5 Run、30 Step、67 工件；原页面仅追加本批生成的数据脚本，保留既有模板。166 项原件比较及 31 个视图渲染通过，浏览器已核告警原件、事件、Case、关系图和 4177。原页面展示 5 个去重对象、3 份原始材料、系统交接和真实空态；独立证据目录、H 任务、评论附件、助手与处置记录没有补造。活动 40 为 7 条业务活动 + 30 步骤 + 3 告警发生记录，不是 activities 表行数。

本机只读 API 的 21 次 GET 为 20 成功/1 失败：Case 详情因 `socai2_prod_reader` 无 `baseline_input_freshness(uuid,uuid)` 执行权限返回 500，输入新鲜度保持未知，未改数据库授权。另外三条事件成员的 `basis_version=unrecorded`，无法展示具体归并规则；事件 API 已返回 `derived.severity_effective=medium`/`member_max`，但原静态适配器仍读取 `incidents.severity=null`，显示未记录。四项问题分别登记，未在本轮修改调查逻辑或静态适配逻辑。

4177 已从正式库刷新同一 Case，返回的 5 Run/30 Step/67 工件 ID 集合与导出完全一致；另按规定用 `update_processing_audit.py --folder` 登记本机独立批次，保留原记录。原页面是固定导出，4177 是正式库刷新入口。本轮执行与查阅完成，不核销完整模型交付、原语义质量或全部前端功能验收。

补充回归 22 项为 20 通过/2 失败；去掉本批脚本引用的内存基线同样失败于旧全局样例计数、旧缓存版本断言，未顺带修改旧测试。Ruff、JavaScript 语法、OpenSpec strict、diff 检查通过；256 个公开文件未发现本次密码/API key/hash，私密文件 0600 且已忽略。初收集器非 JSON 错误与只读查询误用列名均保留说明，不修改业务原件。见[检查回执](../../../docs/operations/evidence/production-multialert-20261107-01/checks.json)。4174 原页面、18022 只读 API 及原有 4177 转发保留供查阅，未提交或推送。

[本轮结果与 F01–F28 功能读回](../../../docs/operations/evidence/production-multialert-20261107-01/summary.json) · [固定计划](../../../docs/operations/evidence/production-multialert-20261107-01/plan.json) · [完整导出](../../../docs/operations/evidence/production-multialert-20261107-01/exports/20261107T064648715936Z/manifest.json) · [页面核对](../../../docs/operations/evidence/production-multialert-20261107-01/page-verification.json) · [4177 回执](../../../docs/operations/evidence/production-multialert-20261107-01/workbench-final.json) · [实际镜像与权限](../../../docs/operations/evidence/production-multialert-20261107-01/runtime-observation.json)。

# 2026-11-07 正式数据的远端配置与只读接入已验证

用户已授权远端 profile 与 PostgreSQL TLS 适配，并随后明确要求正式环境数据：本机 API 经已有 SSH 转发读取 21 的 `aisoc.socai2`，不再选择独立测试库。只读验证，不改生产表、数据、权限或调查逻辑，Agents 与 Kafka/Fusion 后置。用户同时要求后续所有运行配置来自配置文件，禁止在代码中硬编码环境参数；已写入根 [AGENTS](../../../AGENTS.md)。旧本机启动器固定库名、端口、角色的存量问题待按范围迁移，本条不表示全仓完成整改。

已实现显式 TOML profile、受限私密配置、受管理 SSH 转发、psycopg 严格 TLS 及专用本机只读入口；保留原 asyncpg 和独立 API 禁止连接业务库的保护。用已有 `socai2_prod_reader` 实测 TLSv1.3/只读事务/身份/RLS/无调查表写权限，SQL 与 API 数量一致，13 项 HTTP 检查通过，包括列表/告警事件详情/分析记录、401、405和仅 GET 的 OpenAPI。错误证书身份拒绝。21 个不同单测最新通过，Ruff/OpenSpec/diff 检查通过；首轮验证脚本 URI 空格编码及单测替身赋值问题修正后复验，未改生产数据。API 和其数据库隧道已退出，原 4177 工作台仍 HTTP 200。入口见[启动方法](../../../deploy/local-investigation/README.md#21-正式数据只读-profile)、[实测回执](../../../docs/operations/evidence/remote-readonly-20261107/verification.json)和[检查说明](../../../docs/operations/evidence/remote-readonly-20261107/checks.json)。Case 为空，本次未验证非空生产 Case 详情；无模型/调查/生产变更/提交推送。

本次只读核对：历史 `socai2_next_20261104` 为 29 表/459 列，测试租户下 30 告警、12 事件、11 Case、49 Run、299 Step、647 工件、8 results、0 case_assessments。它保留 11 月 4—5 日隔离实验，未具备迁移 126 的三个 Case 字段；迁移登记仅见 123，不能仅按登记推断全部实际结构。既有 `socai2_processing_handoff` 实查为 29 表/462 列且三个字段俱全，但用户要正式数据，故不作为接入目标。正式 `aisoc.socai2` 实查为 29 表/462 列，业务租户 `00000000-0000-0000-0000-000000000001` 下 1 告警、1 事件、0 Case、2 Run；只代表调查 schema 已接入数据，不代表 `public.alerts` 全量。现有 `socai2_prod_reader` 无超级用户/绕过 RLS 权限，也不能读 `public.users`；本地只读入口应以本地服务凭据绑定固定租户与读取权限，不挪用生产登录密钥或新增生产授权。此前 V1 比对结论适用于所记载的环境，不代表历史库已同步；本次不升级旧库、不新建数据库。字段含义和原范围见[交接指南](../../../FRONTEND_BACKEND_HANDOFF.md)及[字段字典](../../../docs/design/socai2-field-dictionary-20261103.md)。

# 2026-11-07 V1.1 测试问题讨论与待实施方案

已按用户要求整理[本轮实施清单](../../../openspec/changes/complete-socai2-investigation-chain/design.md#v11-测试问题实施清单2026-11-07仅方案)，列明修改位置、先后依赖、参数状态及直接验收，并接回现有 tasks。顺序为事实输入→引用/领域合同→工具和摘要→容量/时限→纠正与部分交付→新批补查验收；版本/归并/Agents 原因另行核查。补齐[已有结构化事实与时间语义](../../../openspec/changes/complete-socai2-investigation-chain/design.md#已有结构化事实与时间语义2026-11-07已确认原则待实施)：固定值由程序提供，兼容回填留原值与依据；F16 原活动时间未进入输入，正文时间混用不能靠机械覆盖解决。本次整理已完成，所有业务实施仍待开展。

基于 V1.1 的签名暂存机保存材料离线分析，用户已确认：C3/C6 回答标记 answered 但引用为空时，向模型说明具体错误，让同一份回答最多纠正一次，再完整校验；原答与纠正过程保留，调用计入原预算。方案记入[现有 OpenSpec 设计](../../../openspec/changes/complete-socai2-investigation-chain/design.md#引用为空时的一次纠正方案2026-11-07已确认待实施)，状态为待实施。领域引用的成员范围规则已在后续讨论中单独确认，见下文。

已确认补充[每个工具的用途、返回材料和可解决问题](../../../openspec/changes/complete-socai2-investigation-chain/design.md#工具能力说明与证据需求选型2026-11-07已确认待实施)，让模型按调查方向与证据缺口选工具；领域与工具不作一对一绑定，审批缺口不由登录查询冒充补齐。随后确认[单次模型等待上限 300 秒、整轮上限 1,500 秒、C6 预留 300 秒](../../../openspec/changes/complete-socai2-investigation-chain/design.md#模型调用与整轮时限2026-11-07已确认待实施)，纠正调用也计入同一 Run；时间方案本身不扩大调用次数或整轮总额度。

输出截断讨论后，将[C3 4,096、C6 8,192 tokens](../../../openspec/changes/complete-socai2-investigation-chain/design.md#分阶段输出额度2026-11-07待验证方案未实施)记为待验证候选，需同时核完整请求、共享预算和 C6 预留；尚未确定增加整轮总额度，不扩大到 A/I/Deep。

F01 已确认[核对实际运行版本并补齐归并依据](../../../openspec/changes/complete-socai2-investigation-chain/design.md#核对运行版本并补齐归并依据2026-11-07已确认待实施)：当前源码已有依据生成和保存路径，先定位实际运行版本或传递缺口，复用已有字段保存真实决策，历史空依据不回填。

F06 已确认[核对 Agents 退出原因及恢复验收](../../../openspec/changes/complete-socai2-investigation-chain/design.md#agents-退出原因与恢复验收2026-11-07已确认待实施)：查明首次退出异常及对应消息，恢复后同时验证订阅健康、消费进度和实际分诊结果。前期租户不匹配可能触发预算暂停仍属候选原因，不能写成已查明；与调查同步、人工 Case 分开验证。

F05 已确认[严重性分层与检测标签释义](../../../openspec/changes/complete-socai2-investigation-chain/design.md#严重性分层与检测标签释义2026-11-07已确认待实施)。源码核对明确：事件等级按成员最高值计算，人工覆盖优先；当前诊断模型没有独立严重性输出，也不写回该等级。后续按冻结输入显式提供等级及来源，检测编号由程序查固定版本词典；模型评估与已有事实分开表达。

用户提出错误引用不应否定整轮调查，已记入[错误引用的逐项处理](../../../openspec/changes/complete-socai2-investigation-chain/design.md#错误引用的逐项处理2026-11-07已确认方向待细化)：无效引用不作依据，依赖它的结论重新核查，保留有效部分，关键依据不足的部分未解决或待复核。同步修正前述“纠正后仍整份拒收”的拟议处理；有效引用非空不等于结论已证实，具体部分采用规则仍待细化。

F14 已确认[领域关注范围与发现范围分离](../../../openspec/changes/complete-socai2-investigation-chain/design.md#领域关注范围与发现范围分离2026-11-07已确认待实施)：允许引用相关的跨成员发现，保留发现原来的范围，不强行扩大领域关注成员，也不缩小所引发现。结构合法与语义相关分别检查，领域工件、报告和摘要均须保持两种范围；具体合同待实施，历史原答不追认通过。

输入裁剪讨论后，已确认[按模型容量统一分配、必要时分组选择工具](../../../openspec/changes/complete-socai2-investigation-chain/design.md#按模型容量分配与分组选择工具2026-11-07已确认方向待细化)的方向。65K 是单次请求输入与输出共享的 token 窗口；现有 12 KiB 等固定应用限制并非按该窗口推算。当前源主机优先修复已存在，后续应统一实际请求计量并分别管理整轮预算；具体总额度、模型次数和分组条件尚未确定。

同时确认[调查摘要与增量输入](../../../openspec/changes/complete-socai2-investigation-chain/design.md#调查摘要与增量输入2026-11-07已确认方向待细化)：首次分析后不必反复发送整案，后续显式提供关键事实与来源、判断及未知项、查询状态和新增证据，必要时定向补读原件。已有结构化值由程序提取，模型推断单列；最终结论须能追溯关键证据，摘要不能丢掉反证或冒充模型自动记忆。

本次仅记录设计和讨论进度，未改业务代码或历史测试结果，未连接 VPN/内网服务，未新增模型调用、数据库变更、部署或提交推送；任务完成状态不变。剩余为参数及局部采用合同的细化、运行端事实核查和后续实施验收；`inv-review.md` 的触发更新、任务优先级及跨案图谱仍留下一阶段。新批补查验收须证明查询返回内容实际进入模型并被正确使用，不能以已有材料的图或系统收尾代替。

# 2026-11-06 联调 V1 交付复核及发布

已同步远端 624a57de，数据库 V1、字段/页面对应及交接资料经独立审阅限定 ACCEPT。新增根目录[前后端交接指南](../../../FRONTEND_BACKEND_HANDOFF.md)，列明本机与 21 库名、角色、连接配置和凭据路径、SQL/接口、测试包与签收顺序；根指南再次独审通过。旧本机初始化只准备 125 的限制已明示，完整 V1 新部署沿独立 SQL。48 保存 GET 对账、618 原页检查/95 渲染、5 运行记录测试及 ZIP CRC 通过；4177 静态查阅页已在本机打开。

用户授权 socai2 main 合并及父项目 SpiritHub/add-server-submoudle 的 server 指针更新，不再拉父仓库；实际发布以 Git 远端核对为准。[复核回执](../../../openspec/changes/complete-socai2-investigation-chain/integration-v1-release-review-20261106.md)。本轮无 DDL/模型/业务调用/部署，产品页面保持；19/26、四项页面差异、Q501、其他待接能力和模型质量继续按原范围推进。

# 2026-11-06 本轮数据与测试材料提交远程授权

用户明确要求将本轮修改、测试结果、字段对应清单及剩余问题/下轮部署模型计划提交到远程。沿origin/codex/case-baseline-history-20261103，基线5eacb314；本次包含126页面数据增量、共用存取/导出、原页字段绑定、三组追加测试与四数据合同样例、F01—F28、OpenSpec及限定审计，并将原核验ZIP逐字复制到deliverables/investigation-validation-20261106供远端下载。见[发布范围与待办](../../../openspec/changes/complete-socai2-investigation-chain/publication-20261106.md)。

当前累计63/69、19/26及模型质量未通过保持。发布不启新模型/数据库/部署，不合并main；私密配置、API Token与较早tools/model-preflight工作保持本地。下文和包内“未提交/未上传”是各批原快照，最终提交推送结果以Git与远端核对为准，不回写历史证据。

# 2026-11-06 追加三案测试与字段功能交接

用户要求继续测试并同步核数据/页面/字段对应，已追加local-eval-20261106-01/02/03，真实Kafka/Fusion/PG/CH/DeepSeek合计15调用，累计63/69，三案C6均保存。01/02的C3分别领域发现范围/补查对象范围拒收；03格式通过但效果扩大，三案整体语义质量仍未通过。旧原答/失败保持，不用剩余6次试探，部署模型留下一轮。

48次只读GET、674项比较、557原页面数据检查及87视图通过；入湖/原件逐值、当前结论/成员/图谱/执行工件关联可查。13本机模型批次与4无模型合同样例分列；F01—F28列功能→DB字段→读取→原页及空值/未接线。Case历史1条baseline与页面4条含A/I需聚合、活动混合计数、decimal编码和证据索引未生成已交代。见[统一交接](../../../docs/investigation/investigation-test-handoff-20261106.md)和[索引](../../../docs/operations/evidence/additional-tests-20261106/test-index.json)。

本轮只新增有界测试入口、回查脚本/材料和原页数据引用，为加载126代码重启本机API；不改模板、提示或执行逻辑，不连VPN、不新增DDL、不清历史、不提交推送。校验器最初包装/元数据正文比较及数字字符串问题保留，修后用原件复核。19/26不变，模型质量/完整3.12/4.1/4.2不核销。以下为各批当时状态。

本批独立结束审计限定ACCEPT/0剩余必须修，模型语义仍未通过；见[回执](../../../openspec/changes/complete-socai2-investigation-chain/additional-validation-review-20261106.md)。1272文件、约10MB本机交接ZIP已CRC/逐文件SHA及页面本地依赖核对，初包漏Logo目录已修且保留初包；未含已知运行凭据、未上传，见[打包回执](../../../docs/operations/evidence/additional-tests-20261106/package-receipt.json)。

# 2026-11-06 页面数据增量与独立交接

按用户继续推进实施D1—D3：126增加Case分类/期限/当前证据索引指针，复用工件存版本、活动存变更；当前判定复用已采用结论，共用读取/导出处理证据和威胁计数。实际本机29表462列，4案8告警为明确合成合同测试、0Run/0模型；14案含10旧案列表/详情一致，4模型/3系统/3legacy当前判断可读。原模板仅改字段/缺值/五态判定绑定，四样例和旧案例结论已浏览。见[数据交接](../../../docs/investigation/socai2-page-data-handoff-20261106.md)与[公开回执](../../../docs/operations/evidence/page-data-20261106/summary.json)。

来源校验初审指出标签/分析提升和伪造处置回执，已按登记路径、冻结角色及成员范围修复；补unknown/conflicting显示。独立结束复核限定ACCEPT/0必须修，21后端/24前端定向通过。最初PG导出UTC字符串不一致、兼容验证取值错误及测试fixture错误均保留原因，修后只读复核。模型质量与完整3.12/4.1/4.2不核销，19/26、48/50保持；没有重启常驻API、VPN/远端动作或本轮提交推送。以下为各批当时状态。

# 2026-11-06 数据合同优先修复规划

按用户“规划推进”要求，在[同一OpenSpec](../../../openspec/changes/complete-socai2-investigation-chain/design.md#页面数据合同优先推进2026-11-06)确定先字段含义→最小存储→一致读出/导出→数据交接。目标为Case分类、截止时间及当前证据索引指针三列，证据索引复用artifacts；判定复用current_assessment，证据/威胁计数有明确来源和去重规则，缺索引不造0。沿3.12及[DA01—DA06](../../../openspec/changes/complete-socai2-investigation-chain/acceptance-plan-20261104.md#页面数据合同验收da01da06)独立验收数据，不等模型/VPN/实时表单，其他已具备字段并行对接。此轮仅规划，实际29表459列、19/26及48/50保持，未改DDL、运行代码、页面或历史数据。

独立规划复核已完成：并发版本、重复ID/多成员范围及0/null口径三项澄清后ACCEPT/0剩余必须修，回执在同一设计节；不等同数据修复或整体验收完成。

# 2026-11-06 页面数据覆盖核对与推进口径

用户明确本轮只核页面数据能否保存、关联和取回，流程/算法/接口后续调整不阻碍前后端推进。[数据覆盖核对](../../../openspec/changes/complete-socai2-investigation-chain/page-data-coverage-20261106.md)实际只读检查本机29表459列及七类来源关联，缺失关联计数均0；核心案件判断、调查结果、关系图、报告、人工反馈与材料可支撑继续开发。明确缺Case分类、Case截止时间两个存储字段，另有判定/关联威胁及独立证据的数据口径待定，纳入现有R7；已有字段的样例空值不当作数据库设计错误。此前实时对接问题保留为技术参考。本轮未改DDL、代码或页面，未新增模型调用，19/26与48/50保持。

# 2026-11-06 前后端对接可行性评估

[对接评估](../../../openspec/changes/complete-socai2-investigation-chain/integration-assessment-20261106.md)确认核心Case/Run/Result/H数据及接口具备，原页真实导出与完整实时接线须分开。发现4174→18020跨域预检400（明确Disallowed CORS origin，服务livez/readyz正常）、服务启动comparison_result_id固定null、同Case快照只追加不更新、服务模式若干原页未接及内部图/阶段格式耦合；继续归3.12等原任务，不扩当前导出验收前提。原导出6项、模拟HTTP服务12项通过；首次8项被沙箱监听EPERM阻断，允许本机夹具后通过，非业务代码失败。一项内存探针复现旧判断保留/新Run追加。未使用凭据/模型、未写业务数据或改配置/代码/页面；19/26、48/50保持，未提交推送。

# 2026-11-05 R1—R8后续修复规划

基于已提交并推送的`5eacb314`，继续[现有OpenSpec](../../../openspec/changes/complete-socai2-investigation-chain/design.md)：先版本化事实/效果主张及统一业务投影，解决引用合法但正文扩大；再修C3/C6历史参考与H容量、领域/引用/知识选源，按[验收矩阵](../../../openspec/changes/complete-socai2-investigation-chain/acceptance-plan-20261104.md)推进新批DeepSeek、原模板读回和VPN远端配对。19/26任务状态保持，本机48/50尝试不变；拟议新批次数仅作计划，尚未取得额外额度。本轮仅规划，无运行代码/页面修改、模型/数据库/部署/提交推送，旧原件和tools/model-preflight工作保持。strict、链接/锚点及任务状态核对通过；[独立规划复核](../../../openspec/changes/complete-socai2-investigation-chain/followup-planning-review-20261105.md)三项澄清后ACCEPT/0必须修，不核销实施或4.1结束审计。

# 2026-11-05 提交远程分支与评审交接

用户已明确要求将当前修改提交推送至origin/codex/case-baseline-history-20261103。已整理[修改与后续评审清单](../../../docs/investigation/design-audit-and-scenario-evaluation-20261105.md#9-实施变更与后续评审记录2026-11-05提交快照)：已实施6类修改、真实样例结果、R1—R8问题及复验要求；统一README/主设计/OpenSpec当前19/26、48/50模型时点，原始失败不改写。此次为进度提交，事实扩大、H后容量和完整质量仍未验收，不归档或部署；私密配置/原件及较早tools/model-preflight工作留本地。最终提交与推送结果以Git及远端指针核对为准，下方未提交/未推送为各批当时状态。

# 2026-11-05 三组案例真实流程对比完成，分析质量未通过

按用户要求复用案例管道新增local-eval-20261105-01/02/03，共6告警/6日志：账户清点与报表复制、进程内存转储与归档、卷影删除命令与单文件改名。预期答案独立保存，不进入模型或页面。沿本机Kafka→Fusion→PG/CH→A/I→Case C1–C6执行，每组5次DeepSeek，共15次；本机累计48/50，无重试、无远端模型/VPN。三组均保存model/accepted/partial/uncertain案件判断、覆盖2成员。原页面模板和算法/提示词保持，只追加三个已核hash的导出数据脚本。

01正常意图样例缺授权/完成记录仍待核；A1扩大为已发生复制，C6主结论收回但领域结论称“外部共享”无据。02识别转储/归档敏感性但仍不定性，PID688身份与文件内容未证实。03的A1/I/C3分别因直接依据角色、成员引用范围及来源标签标成observed被拒；15个provider答复均completed，不是服务不可用或入湖格式失败。03 C6仍执行并采用，却把进程启动/一次改名扩大成卷影删除、加密成功，F2还把--note参数写成已生成勒索说明，质量不通过；未改写原答。01/02 cloud/phishing仅因无来源判not_applicable仍待修；知识库已种入并经PG标题检索，但三组C2均因证据工具预算保留而未取SOP。

[对比回执](../../../docs/operations/evidence/investigation-repair-20261105/local-comparison-summary.json)逐组记录阶段、查询ID、29表导出及当前判断；[列表截图](../../../docs/operations/evidence/investigation-repair-20261105/local-comparison-cases.png)和4174原模板可直接查看。30驱动/配置检查通过；页面检查首轮30/31，修正“所有A都有已保存解释”的旧测试假设后31/31，失败A仍显示缺解释。独立窄审验证3新增夹具、15请求无oracle、6身份/原件一致及单轮H提前拒绝，限定ACCEPT夹具/驱动，不核销模型质量与整体结束验收。Case管理字段严重程度/分类/状态仍为未记录/未设置/新建；H后容量3.16及远端对照继续待，不归档、不提交推送。

# 2026-11-05 C6收尾与案件业务字段已修，首轮DeepSeek判断已保存

C6不再以前序C3成功为前提。模型输出失败、无可用模型或执行中断时均留下系统来源的待核判断；unknown仍保持原调用状态及占槽，不伪造Result、不重试、不覆盖已有模型/人工判断。仅兼容已确认的额外空字段analysis.conflicts_note=null，原答与适配回执保留。IPv4/mapped IPv6等价形式不再误报冲突；真实不同地址保持冲突。

本机a–g累计33/50次模型尝试。d/e/f分别暴露conflict成员数、输出截断和必要输入装配问题；全部保留原失败。g首轮C3/C6接受，2次真实湖查询，案件判断覆盖2成员；结论为观察到进程启动与TCP连接，行为性质及影响待核。其后保存了限定A0授权的H；第二轮在调用模型前因8KiB视图无法同时容纳H与必需I摘要而停止，0新增模型调用，旧模型判断保留且标记材料变化。H→下一C质量闭环尚未通过，不归因DeepSeek服务不可用。云/钓鱼适用性措辞仍需质量跟进，服务器模型按用户要求延期。

按用户最新纠正，实际数据库字段分离：cases.description保存案件背景，case_assessments.conclusion保存当前业务判断，技术原因留在runs.stop_reason、run_steps.error及执行工件。页面撤掉用拒收C6原答填案件摘要/覆盖Result的逻辑；模板布局保持。d/e/f系统判断新增修正版并保留旧版本，g有效判断不改；四Case补存固定合成场景背景。d-r2/g从PG和API重新导出并在原页面读回，g关系图及已完成人工任务可查。没有改写旧Run/Result/工件，a/b/c原件保持。

[限定汇总回执](../../../docs/operations/evidence/investigation-repair-20261105/local-c6-business-fields-summary.json)：13个不同PG方法最新通过（模型/湖替身），本次字段定向2/2；原页面31项通过。独立审阅发现的两项新导入刷新问题通过撤销不必要刷新逻辑解决，保持append-only及本地编辑。API已重启且ready；真实浏览核对d/g案件资料、g关系图及H，截图保留。3.15限定完成，整体真实质量/后续轮容量/服务器对照/最终归档仍待；无提交推送。

# 2026-11-05 C6投影离线修复通过，本机结果保留待真实回归

本机专属PG/CH/Kafka/ZooKeeper/Redis五项healthy、API/Fusion ready；PG29表459列、强RLS及受限角色、CH48列覆盖47个writer字段、三个Kafka topic和真实2告警/2湖日志→1事件已核，3.13完成。四旧后台停止、历史数据及volume保留。初环境/DDL失败修后留证，不称首轮全绿；见[环境回执](../../../docs/operations/evidence/investigation-repair-20261105/local-environment/receipt.json)及[当前计划](../../../openspec/changes/complete-socai2-investigation-chain/local-first-validation-plan-20261105.md)。知识仍为告警标题→PG全文检索，不依赖图/向量/Embedding；资产/SOP函数导入、两块正文和标题FTS/API角色读回只核本批准备，HTTP导入鉴权未验，3.14未完成。

a批5次模型尝试在C6缺必填analysis.followups时拒收，另有C3能力目录被全部裁剪、Deep因C6预留跳过的问题。目录改为共同范围无损分组的第3条user消息，保留8KiB事实及12KiB全部消息限制；C6提示仅澄清必填字段/成员范围，完整请求增66B。23项直接检查及限定独审通过，见[目录回放](../../../docs/operations/evidence/investigation-repair-20261105/local-a-c3-catalog-replay.json)和[C6诊断](../../../docs/operations/evidence/investigation-repair-20261105/local-a-diagnosis.json)。b随后4次模型尝试在C3拒收：B1网络query的object_keys含host+目的IP，绑定只允许host。两批Case实际湖补查均0、0判断采用、0 H，原件保持且不重派。

C3专用动态Schema现已实现：按相同绑定成员/对象集合分组约束query，其他模式保原范围并要求binding_id=null；仅在协议转换后等价压缩发送Schema的定义名，事实、提示、canonical DTO/解析器不变，A/I/Deep/C6发送路径不受此压缩影响。新完整C仍48000/4模型/4Tool/120秒，旧Run及其原预算不变。59个不同纯检查通过，独审复跑其中11项并限定ACCEPT；[容量回执](../../../docs/operations/evidence/investigation-repair-20261105/execution-schema-capacity-20261105.json)覆盖5份固定输入×2协议共10格，均保3绑定并准入，最小余158；b的DeepSeek完整wire17458B，保C6预留27076及当前输出余量后余210。仅证明固定样本可准入，不称通用容量或真实质量闭环。

API已重启加载冻结候选；`local-maintenance-20261105c`完成prepare、SOP/资产准备、preflight及Kafka入湖2告警/1事件/2湖日志后已结束。C3阶段和模型完成，新动态Schema经真实请求通过；C6阶段和模型因delivery_shape_invalid失败。c为4 Run、69工件、5次模型，a5+b4+c5累计14次仍计入本机50次上限，0案件判断采用、0 H。原件诊断确认C6唯一Schema错误为多余analysis.conflicts_note:null，违反additionalProperties=false；provider为completed、2698输出tokens，未截断，发送与回显Schema一致。进程和网络两次真实湖查询各返回1行，无Deep；[c原件诊断](../../../docs/operations/evidence/investigation-repair-20261105/local-c-diagnosis.json)确认C4中间视图含9个湖字段（进程5/网络4），C6二次bounded_input因model_view_budget_exhausted全部省略，只剩queries/routes执行元数据。查询原件保留，但模型未收到可引用湖行，这是与输出额外字段独立的输入容量缺口，不能称模型已消费两次补证。不修改或采用c原答，当前仍无有效C→H→下一C验收。

随后仅完成C6投影的离线修复：从已核hash的本轮完整query_projection提取候选，共同查询范围/限制无损分组；保原22项必需依据，并把命令、目的IP和同一行目的端口3项设为最低必需证据。c候选27个投影字段中3可见、24明确省略，进程1/13、网络2/14均为partial；原值、角色、精确字段引用、conflict与query_binding_only保持，最终预算裁剪同步计数。见[修复回执](../../../docs/operations/evidence/investigation-repair-20261105/final-query-projection-20261105.json)：视图7919B、全部消息11695B、完整wire18850B，计原C3实际7738 tokens及3000+256输出/余量后，48k还余18156，两预算门均通过。41项不同相关检查最新通过，独审复跑其中10项及c内存重建，限定ACCEPT；非新增51项。旧24k包保最低查询证据后18043B>17744B，超299明确拒绝，不改旧预算、原件或重派。历史紧缩通过不再适用于修后最低证据要求。provider额外字段问题未解决，修后尚未新批真实回归。

a页面700px、b/c约906px的历史与真实失败展示已实际浏览。c另核原件、来源检测置信度28.2/100、Execution覆盖2告警、真实A/I/C链接、两次query各返1行，以及failed/0当前判断/0 H；c窄屏未验，不沿用a的700px结果。[页面字段回执](../../../docs/operations/socai2-local-page-field-coverage-20261105.json)现覆盖a/b/c，27项已有相关检查证据复用，本轮未重跑；不是在线数据库刷新。对象去重数不等于来源行数，case_incidents完整关系行和activity_targets前后值仍在原始导出，未查询的知识结果不补造，3.12继续未完成。

[收尾只读回执](../../../docs/operations/evidence/investigation-repair-20261105/local-environment/final-local-readiness.json)记录2026-11-05 11:40:49 UTC：API已正常重启加载最终修复，API18020/Fusion18021/页面4174均HTTP200；模型累计14、活跃或unknown Run为0、6告警/3Case/0判断采用/0 H。用户选择先保留本机结果，稍后再测服务器模型；本轮不建立VPN连接、不新增模型调用。

远端切换的本机驱动已支持新批显式backend与model/protocol/profile/base URL摘要冻结，不输出URL或凭据；配置和源码同时漂移时先核配置，拒绝后不自动导出。24项离线检查通过，独审复核其中2项；显式读取旧历史导出仍允许。这只证明本机配置边界，未来切换仍须确认无活跃Run、重启API并核实际请求身份，不代表远端已连接或验收。

数据库、执行记录、工件和页面全程本机。当前17/23；3.7/3.10/3.12/3.14/4.1/4.2保持未完成，不归档、不提交推送。下方同日历史状态不覆盖本段。

# 2026-11-05 调查审计问题的OpenSpec调整规划

按用户要求复用[complete-socai2-investigation-chain](../../../openspec/changes/complete-socai2-investigation-chain/proposal.md)，补[调整设计](../../../openspec/changes/complete-socai2-investigation-chain/design.md)、数据/页面规格及[验收条件](../../../openspec/changes/complete-socai2-investigation-chain/acceptance-plan-20261104.md)。新增3.8—3.12五项待实施：完整请求容量与C6资源预留、query直接Tool及补查优先级、能力/语义/依据状态验证、Case集合/指标/DTO、既有页面最小闭环。先后三份固定包与两成员候选核可行性，再原3.7真实C→明确范围H→下一C；单纯提前阻断不算容量修复成功，不增加原额度或删除必要依据。

已纠正活动设计中“材料/H变化不会阻止采用”的相反文字，按已有125实现说明采用前阻止、采用后保留旧判断并标依据更新；外部日志/库存/TI不冒称全部追踪。页面规划用直白的调查依据状态，和成员覆盖分开；保留部分采用与手动单活跃。Q、新领域取证、通用恢复/管理后置。当前仅规划，原13项完成记录保持，原3.7/4.1/4.2及新增五项均未勾选；无业务/页面代码修改、模型、业务库、部署、提交或推送，未用dsapi.txt。前轮审计报告与归档原件、tools/model-preflight保持。

规划独审首轮指出任务完成条件循环及H对象/时间不应统一必填，已统一设计/规格/任务/验收；复审限定ACCEPT、0剩余必须修。strict和文档检查通过，14项全量/5项归档校验通过，当前13/21、不归档。见[规划复核回执](../../../openspec/changes/complete-socai2-investigation-chain/planning-review-20261105.md)；下一实施项3.8，规划通过不核销原实施独审4.1。

# 2026-11-05 现有设计审计与场景评估

按用户选择，基于codex/case-baseline-history-20261103的a1be19316105ad9176afcadba8c4463fc50c96b1，先设计审计，再推演18个场景并评估成熟度。见[两轮报告](../../../docs/investigation/design-audit-and-scenario-evaluation-20261105.md)。保留A/I/C/H分工、冻结范围、证据与版本设计；列出C6容量阻断、query/Deep路线不一致、页面与新服务未接通、活动设计输入新鲜度文字冲突。部分采用、200成员仅存储上限、外部数据新鲜度边界和unknown不自动重试按已有规则说明，不追加通用恢复框架。

本轮离线复用固定请求大小及历史usage调用当前预算函数，3例均仍被额度门阻断；另核最终调用次数预留、29表459列/36枚举/38合同及Case集合GET缺口。仅文档审计，没有新模型/业务库访问、代码或页面修改、部署及提交推送；未使用dsapi.txt。原实施3.7/4.1/4.2、旧r13/5.3与真实C/H/第二C未通过状态保持。本批结束复核单独记录，不替代原调查实现验收。

文档结束独审ACCEPT、0剩余必须修；已收窄人工确认范围措辞，允许事实影响整案解释。54报告引用和24来源指纹保持，归档仅调整回执链接；OpenSpec all 14项、archived 5项通过。见[本批归档回执](../../../openspec/changes/archive/2026-11-05-review-investigation-design-and-scenarios/audit.md)，本次未归档原调查实施change。

# 2026-11-05 当前调查审计修复与剩余容量问题

当前分支codex/case-baseline-history-20261103，直接更新既有文档，未新建工作树。用户现已授权提交并推送当前进度至origin同名分支；不合并主分支、不部署，C6剩余额度问题保持未闭环。A01已加125增量函数迁移：按冻结成员材料/triage/feedback、事件诊断/成员、已完成H语义检查输入新鲜度；采用前stale_input不覆盖，Case读取返回input_freshness，标题/负责人等元数据变化不误判。29表459列不变，125只应用21既有隔离验证库，业务库/常驻服务未更新。A03明确400/422 Schema拒绝失败收口、ended_at及释放Run，未知用量保持；超时/其他不确定仍unknown，旧记录不批改。独立小模型Compose绑定vllm_grammar_v1，DeepSeek覆盖standard，预检校验协议/profile；原配置保持。A04补明确SHA256及冲突/遗漏。A05按冻结对象选C2来源，保存选择依据，仍给C4留2次/总4次Tool。

A02仅部分修复：C6必带事实/时间/H/原计划/有效比较，A/I参考整组可省略且留账，不拆同次评分判定理由；C3再分析原规则保持。3固定包22/22/23必需项零遗漏、视图7943/7966/7894B，但完整请求16527/17262/17939B分别超过原usage后的13458/9314/13274B，仍model_token_budget_insufficient，不能说整链通过。共享预算仍24000/4模型/3000输出，未重置usage、删必要值或重派已结束批次。下一先解决C3/Deep/C6容量分配，再固定候选同步独立服务和新批真实验收。

52纯检查与18个不同隔离PG方法最新通过（模型/湖/背景返回替身）；初离线测试调用签名错误、完整wire暴露预算问题、首H测试角色缺用户ID权限均留说明，H定向复核通过。证据见docs/investigation/current-investigation-audit-20261105.md及fix-validation-20261105T023329。124写点/57源指纹已重建。当前执行账本、README、主设计和OpenSpec原位更新；不写并行设计版本。3.7/4.1/4.2未勾选，Q501，旧r13/5.3不核销。无新真实模型/业务湖查询/生产变动；本轮不是结束独审。

# 2026-11-05 当前调查逐步骤执行账本

另从已保存数据库原件生成[26个Run逐步骤索引](../../../docs/investigation/current-execution-records.md)，含162Step/361工件目录、关联表记录数和4份结果/0采用。源SHA256保持，输入/输出指针同Run校核；取数时点2026-11-05 00:13:44 UTC，非本次线上刷新。记录生成器首7项Ruff字符串括号问题修后过，不改业务/原件。

用户要求只看现在每一步输入输出、Run与数据库修改。新增[当前执行账本](../../../docs/investigation/current-execution-ledger.md)，展开Fusion/A/I/Case/C1—C6/H/Q；明确C1—C6同Run、Deep子步骤、先占位提交后外呼、发布采用事务及真实条件。新增121个源码写点（57源文件指纹）、完整表达式JSON和按tenant/case/run查询的只读SQL；不把静态写点或活动当成通用SQL前后镜像审计。

静态校核：生成器Ruff通过（首轮5项已改）；15条SELECT经PostgreSQL方言解析和ORM字段校核，整行to_jsonb用别名id替代做限定器检查，事务包装因解析器不支持而未宣称验证；121写点/57指纹/135文件链接核对。仅文档及离线目录生成器，没有业务源码/DB修改、部署或新模型；SQL未连接执行。OpenSpec3.7/4.1/4.2保持未完成。

# 2026-11-05 Kafka整链与上下文查询实测

[完整流程、写表、模型对照和缺口](../../../docs/investigation/kafka-to-conclusion-validation-20261105.md)。n14独立服务已部署且恢复DeepSeek；k2共26模型请求/23原答/3明确400，A11/12和I5/6发布，0有效Case最终结论。9B的uniqueItems拒绝属于兼容profile未启用；C6三轮因必要输入预算在最终调用前阻断，属于装配设计；另有引用/活动成功语义错误。14不同executor PG方法最新通过但模型湖为替身，整体未验收。

复用tools/testdata新增40条上下文，经真实Kafka/Fusion进新湖；18正式Tool查询全集一致、96流量计数与原值一致，12负向对照排除，2空Case保留。见[查询摘要](../../../docs/operations/socai2-context-k4-20261105.json)。湖SQL硬编码曾使前批16合成事件误入旧库，已逐ID/原文核验精确清理并经修后Kafka恢复新库；本地路由和流量投影已修，尚未同步常驻镜像。完整证据和后续顺序在上述流程文档。OpenSpec13/16，旧r13/5.3保持；不提交推送。下方n13未部署/m4待授权属历史。

# 2026-11-05 隔离PG已验证，C6预算回归修复，n13固定

网络恢复后原5项最新通过：首批4过1失败暴露C6必要计划与重复提示挤占剩余预算，未调用最终模型或采纳。仅整理独立C6提示，保必要计划/事实/source_map/Schema及原额度，请求18871→17657B，限额17744B；定向2项通过，其余3项复用首批通过，非一次首过。模型湖替身，新增1离线回放过、原44纯检查复用，角色隧道清理。

[验收明细](../../../docs/investigation/socai2-m2-followup-fix-20261104.md)末节及[固定回执](../../../docs/operations/socai2-followup-pg-20261105.json)。n13固定621文件/550应用，较n12仅C6提示+标签；未上传部署，线上最近n9。网络阻断已解除，仍待m4额外1次授权、真实整链质量和独审归档；OpenSpec13/16。原n12/m2/m3及失败证据保持，不提交推送。

# 2026-11-05 后续建议与报告关联已本地修复，PG验证等待网络

[修改与待验明细](../../../docs/investigation/socai2-m2-followup-fix-20261104.md)末节：声明成员的对象校验、C6原计划工件/序号关联与必要内容保留已实现，最新建议不套旧执行状态；活动成功及范围语义补简短约束，无DDL/页面/调度修改。44不同本地检查最新通过，初夹具错误保留；n12固定621文件/550应用，未上传部署。

隔离PG选定5方法尚未开始：首个只读预检失败、21:22 SSH超时，0角色/数据写入。已询问网络恢复，不能称PG通过。m4额外1次仍待授权；n9最近线上、r7未启、OpenSpec13/16及真实整链/独审归档待。原n11/m2/m3材料保持。

# 2026-11-05 语义与执行边界复核

已完成本地原件/代码分析，详见[剩余语义与执行范围](../../../docs/investigation/socai2-m2-followup-fix-20261104.md)：I活动成功措辞扩大、C3人工建议文字超声明范围、已知端点与未知外传混写；均非新增数据表缺口。另确认followup对象未按所选成员核验、C6未投影原建议稳定身份，原数据已存，待最小读取/合同修复。Deep整案冻结问题和Tool binding范围、H显式结果范围保护保持，未证明实际越Case执行。

30份m2原文件hash保持、2原答当前解析器接受、4离线反例完成；不当模型新答或误判率。本轮0业务修改/真实模型/Run/部署；n11固定、m4待新增1次授权、n9线上、r7未启、OpenSpec13/16保持。审计回执docs/operations/evidence/socai2-semantic-boundaries-20261105/local-audit.json。

# 2026-11-04 m3定位Schema拒绝，修复与n11本地完成

[m3结果](../../../docs/operations/socai2-schema-probe-m3-20261104.json)：明确授权后2请求均400，无重试/模型答复，usage未知；anyOf引用分支缺type，object多类型数组也不支持。服务及配置指纹保持，原阻止已解除、本批结束不可重派。

[本地修复与下一步](../../../docs/investigation/socai2-deepseek-union-fix-20261104.md)：DeepSeek发送前仅展开anyOf引用，约束/本地合同/小模型保持；44纯+2真实隔离PG方法通过（模型湖替身），请求保存及C3/Deep/C6预算核验通过。n11固定620文件/549应用，较n10 9路径变化，未上传/部署。400兼容方向已定位，但新表达未真实复验。

m4已固定新Schema-only单次请求，512输出tokens、不重试。已询问新增1次许可，原因是m3明确2次额度已耗尽；0m4上传/调用。线上n9、r7未启，OpenSpec13/16，完整真实C/H/第二C及最终审计仍待。

# 2026-11-04 m3兼容诊断固定，上传待授权（历史，已结束）

[m3固定范围与步骤](../../../docs/investigation/socai2-schema-probe-m3-20261104.md)：两条DeepSeek输出格式对照，仅Schema/通用JSON/错误留痕代码，不含业务材料；当前nullable引用与等价内联表示，每条一次、512输出tokens、无重试。3项本地检查及编译/静态通过，尚不能确定HTTP400根因。

自动审批拒绝上传：新增m3私有代码/Schema及目的未包含在m1/m2授权中。已询问本批明确许可；0上传/预检/模型。先等待答复，允许后upload→preflight→run→export，不重跑prepare或结束批次。不绕路调用，原配置保持。n9线上、n10冻结、r7未启，OpenSpec13/16。

# 2026-11-04 m2后本地修复、待复核验收口径明确

用户确认仅良性↔恶意计误判，needs_review可接受并单列；无独立真值不算准确率，旧“9B误判”按“无充分依据的良性定性”理解。已同步OpenSpec和m2报告，不改历史原答或固定回执。

[修改与验证明细](../../../docs/investigation/socai2-m2-followup-fix-20261104.md)：I检测组优先保留，两成员检测组1→2，7926→7966B仍在8KiB内；A/I/C3/Deep/C6增加有界去凭据HTTP错误回执，原unknown/不重试/不采用保持。43不同纯检查最新通过，5不同真实PG方法通过（模型湖替身）；初夹具/导入排序问题保留。无DDL/新真实模型/部署，m2原证据hash保持。

Deep A400具体参数及小C3超时归属未定，错误留痕不等于协议修复；语义质量与完整C/H/第二C仍待。n9线上、n10冻结、r7未启、新改动仅本地，OpenSpec13/16。详见[机器回执](../../../docs/operations/socai2-m2-followup-fix-20261104.json)。

# 2026-11-04 m2真实验证结束，整体未通过（历史批次）

[逐项结果与缺口](../../../docs/investigation/socai2-model-evaluation-m2-20261104.md)：授权后8请求/5完整原答/2HTTP400/1HTTP408，0重试，22328已报tokens，3失败usage未知。0业务Run/Tool/采纳/部署，原服务及配置指纹一致。5答Schema有效、2份程序接受，仍有语义问题，不能算质量通过；[固定回执](../../../docs/operations/socai2-model-evaluation-m2-20261104.json)保19远端JSON及原件hash。

9B两A无据benign均被拦，但模型误判未改；来源role门仍不能证明授权，离线反例确认。Deep I/C3结构通过，但进程启动成功表述及人工后续项范围需修；Deep A两次400具体错误体未留存，先查请求兼容，不能归因参数量。小C3 45.136秒408、网关窄窗Timeout，时限来源未定。I预算新增少量class/time字段却省略网络detection整组，库中未丢，需调内部优先级。

本批结束不重派，不再待m2授权。n10保本地、r7未启动；先解A诊断/协议及I字段，再新候选和新批。线上最近核验n9，OpenSpec13/16、Q501、旧r13/5.3保持。

# 2026-11-04 验证准备完成，m2上传待本批授权（历史，现已授权执行）

[m2/r7验证计划与固定指纹](../../../docs/investigation/socai2-contract-validation-plan-20261104.md)：m2当前A0/A1/I/C3各双后端共8次不重试；固定同材料，显式小后端Schema兼容，0业务采纳。包与runner已固定，首次upload+preflight被自动审批以“m1授权不覆盖m2到21的数据传输”拒绝，命令未执行；已问本批授权，0新增真实模型/远端访问，等待答复，不能绕过。

不依赖授权的工作已完成：n10本地候选619文件/548应用逐字节核对，无凭据；r7新键/原材料/首C门槛驱动6检查通过，关闭r1–r6重派。原业务代码指纹及56纯/11PG证据保持。未上传n10/部署/r7调用，线上最近核验仍n9，OpenSpec13/16。下一授权后m2 upload→preflight→run→export→review，之后再按真实结果推进独立服务完整链。

# 2026-11-04 m1后合同修正：本地通过，真实质量仍待

[修复、字段、流程例子及后续](../../../docs/investigation/socai2-m1-contract-fix-20261104.md)：显式后端Schema子集、历史编号隔离、窄字面名豁免、A/I单一结构化引用、新定性依据、C时间/领域合同已本地实现。29表459列不变，工件JSON保存schema_profile/applicability，三份合同同步；原文/历史/预算保持。确定性依据门不等于语义验真，尚未证明9B结论改善。

56纯检查与11个不同PG方法最新通过（A4/I2/C3两方法/完整执行器2/C6历史1），保留初夹具、UUID扫描及两处Schema遗漏失败；模型/湖替身，既有独立PG及清理回执。20文件Ruff、三合同一致、OpenSpec strict通过。详见[机器回执](../../../docs/operations/socai2-m1-contract-fix-20261104.json)。m1原件保持，0新真实模型/部署；线上最近核验仍n9、本地v4待新候选。下一新批真实质量及C→H→第二C，再结束独审/归档；OpenSpec13/16、Q501、旧r13/5.3不变。

# 2026-11-04 m1实测结束：9B误判未改，确认Schema和引用设计问题

[实测对照与后续修法](../../../docs/investigation/socai2-model-evaluation-m1-20261104.md)：用户明确授权后12请求/11完整原答/1HTTP400，不重试；37506已报tokens，0新业务Run/Tool/采纳/部署，原服务配置保持。两A精简后输入更短，9B仍benign/.95、DeepSeek仍needs_review；Deep新版两A引用拒收。I两者待核，9B状态/引用拒收、Deep通过；C3小后端因uniqueItems不支持而400，Deep因时间角色/待定领域关联合同拒收。11答Schema有效、7解析接受不等于质量合格。

本批还确认历史来源编号重名与literal豁免过宽，不能只归因模型能力。下一先修兼容Schema和引用/语义合同，保本地严格校验；固定原件回归后再新批完整C/H/第二C。不重派m1，线上n9、本地v3未部署，OpenSpec13/16及Q501、旧r13/5.3保持。[机器汇总](../../../docs/operations/socai2-model-evaluation-m1-20261104.json)保存逐格结论/边界/证据指纹。

# 2026-11-04 m1准备阶段历史：实际调用曾待授权（现已执行）

[m1对照计划和检查](../../../docs/investigation/socai2-model-evaluation-m1-20261104.md)：12格请求固定，两条A旧/新各双后端，加当前I/C3双后端。相同材料与前序判断、相同messages/Schema/温度/输出限额，原预算内；不建业务Run/不写回结论。全部旧A可见值保留，6组输入合同检查通过，三个脚本Ruff通过。

上传到21的命令被自动审批拒绝，理由是本批冻结材料与目的地需明确授权；尚未执行上传或模型调用。已询问用户本批合成材料/12次/不重试范围，等待答复。不能声称新版已测试9B；线上n9、本地C v3未部署，OpenSpec13/16及Q501、旧r13/5.3保持。

# 2026-11-04 输入精简已实施；真实r6未通过，后续C修正仅本地

[实施与剩余明细](../../../docs/investigation/socai2-compact-input-fix-20261104.md)：n9已部署独立新服务，原服务/配置保持；分组、必需组、A/I可见性/分类校验和C提示已接。43纯+6驱动、16不同PG方法最新通过，初失败与修复回执保留。

[r6真实验收](../../../docs/operations/socai2-next-r6-validation-20261104.md)：3模型11380tokens。A0引用未配对而失败，A1/I保存；C在模型调用前因准备账本错误占用模型额度和I整对象超限停止，H/第二C未执行，本批结束不重派。随后C v3本地修正并以r6冻结原件/PG回归通过，尚未部署。OpenSpec仍13/16，后续新批真实C/H/第二C、A0引用合同及结束审计未完。Q501、旧r13/5.3不变。

# 2026-11-04 输入可精简，修订方案已梳理但尚未实施

参考开源固定版本7份源码，确认按任务字段/浅层材料/短输出值得复用，但其解析容错、小模型循环及无证据编造说明不能保证语义正确。详见[开源比较第7节](../../../docs/architecture/opensource-investigation-implementation.md#7-输入怎样精简对小模型到底有什么帮助)。

对r4/r5 I原输入做可逆分组，全部已发送值/检测字段保持，视图减少20.71%/19.52%；补回764B同次分诊后7136/7310B，仍在原额度内。见[离线回执](../../../docs/operations/socai2-compact-input-measurement-20261104.json)。这些是字节数，非tokens或模型质量；0模型/DB调用。

方案纳入[唯一主设计4.3–4.4](../../../docs/architecture/investigation-planning-design.md#43-模型输入与输出精简)及OpenSpec：无损分组、必需组、真实可见性、背景引用、展示与阻断分类、短输出及现表/工件承载。本轮仅文档/实验脚本，没有业务代码/DDL/部署/配置变更。线上n8、OpenSpec13/16保持；下一按方案本地实现，再新批完整验收。Q及旧r13/5.3不变。

# 2026-11-04 先修设计根因，停止追加模型验收

用户要求区分自身设计与模型原因。已对r4/r5七份固定原件做离线核对，0额外模型/DB调用：[明确归因明细](../../../docs/investigation/socai2-deepseek-root-cause-audit-20261104.md)。已证实输出Schema与后置条件不一致、8KiB视图丢掉有效764B分诊、可用/可见字段混用、格式错误导致整体失败、事件背景范围不明确、仅首错可见。另有供应商pattern未遵守及TCP443推HTTPS的具体输出错误，不能笼统归因参数量。

线上n8/546应用文件，原配置与四旧容器保持；r5只完成三次A/I，A0因正文编号失败，A1/I技术完成，Case未建。28纯+6驱动及C3 PG15反例通过，真实完整链未验。下一先按输入合同、可见性、引用范围、错误分层做设计与本地回放，再新批验收。OpenSpec13/16，Q501及旧r13/5.3保持。

# 2026-11-04 DeepSeek独立接入与r4结果

已按用户指定将独立新API接到deepseek-flash（n7/546应用文件），原api.env、LiteLLM配置和四个旧容器指纹保持；[配置与适配说明](../../../docs/investigation/socai2-deepseek-adapter-20261104.md)。新API直连Responses；原服务仍使用原LiteLLM。凭据不入日志、Git或候选包。

r4已结束未通过，4模型18379tokens，A0对标签/授权的判断改善；A1/I正文来源编号违规，C3单finding冲突被拒。无H/第二C。见[固定结果](../../../docs/operations/socai2-next-r4-validation-20261104.json)。n8本地对齐输出Schema和既有解析器，28纯检查/6驱动检查通过，PG反例复核中，r5未派发。OpenSpec仍13/16，质量、结束独审、归档待；旧r13/5.3不核销。

# 2026-11-04 n6/r3真实验收与模型接续

独立服务已更新n6，原服务保持；表仍29/459。字段投影/结构合同/剩余额度处理已修，18纯检查及9不同PG方法最新通过，初失败保留。真实r3四模型14666tokens，结构改善但语义未通过：A1已保存却错误从标签推无风险；C3被单finding冲突拒收，仍有无据因果与来源状态误读。没有H/第二C/真实Deep与C6验收。见[逐项结果](../../../docs/operations/socai2-next-r3-validation-20261104.md)、[字段修复](../../../docs/investigation/socai2-model-input-projection-20261104.md)。

用户允许使用ergouzi，等待API地址/已有配置位置及用户所给字符串含义确认；未猜地址、未改模型配置。已准备r4本地驱动并关闭旧三批派发，5检查通过；新模型确认后仅改新服务并固定新批。OpenSpec13/16，真实质量、结束独审、归档待完成；Q501、旧r13/5.3保持。以下按历史时点阅读。

# 2026-11-04 独立服务与真实验收

H/prepare及来源适配已完成（OpenSpec13/16），新API独立运行于21的18020，本地同端口已SSH转发，/readyz ready；原版服务保持。新PG socai2_next_20261104、CH socai2_next_validation、Redis13独立。见[独立方案](../../../docs/operations/socai2-next-service-plan-20261104.md)、[H/prepare](../../../docs/investigation/socai2-human-tasks-20261104.md)、[来源](../../../docs/investigation/socai2-external-sources-20261104.md)。

真实r1尚未通过：两A技术完成但从测试标签推良性/授权，I形状与语义失败；C3未知/503，无响应工件。已保存原件并继续修复，不重派旧批；H和第二C仍未真实执行。独立审计/归档保持待办，不将服务ready当质量通过。当前最新状态详见AGENTS顶部。Q具体实现暂缓，旧r13/5.3保持，未提交推送。

# 2026-11-04 事件Case关联与移动

[25字段、完整流程与4例](../../../docs/investigation/socai2-case-relations-20261104.md)及[19项最新通过回执](../../../docs/operations/socai2-case-relations-20261104.json)：12新+7回归，原5失败保留；双Case原子移动、并发和未提交不可见已核。增量124补固定Case来源绑定，当前29表459列，原123保持，仅独立合成PG。来源命名空间不当原始环境。OpenSpec 3.4完成、11/16，下一H人工写读/版本引用，再外部来源及迁移/真实验收；页面/生产未切换、无提交推送，Q仍暂缓，r13不恢复。

# 2026-11-04 告警/事件页面字段读取

[73项字段、8个GET模板与4例](../../../docs/investigation/socai2-page-reader-20261104.md)：新表主体字段、关系、资产、评论/活动、材料和A/I步骤用量已接只读出口，默认关闭；等级/时间/分诊语义分开，总体统计不随分页，主体/租户/Case权限明确。8新+2PG回归最新通过，另Q预留3个ASGI方法/18子场景通过；首5个夹具/预期失败保留在[固定回执](../../../docs/operations/socai2-page-reader-20261104.json)。原29表458列保持，无生产/页面切换或提交推送。OpenSpec 3.3完成、10/16，下一3.4事件Case显式关联/移动，剩余H/来源/迁移及真实验收；Q仍暂缓，r13不恢复。

# 2026-11-04 I事件诊断执行

[32字段、完整流程与4例](../../../docs/investigation/socai2-incident-diagnosis-executor-20261104.md)：完整成员及有效同次分诊冻结→一次事件模型→逐成员/跨成员诊断和未决原子发布；旧分诊与旧I输入保持兼容，过期正文不进模型。9新+5受影响回归首次通过，[5批回执](../../../docs/operations/socai2-incident-diagnosis-20261104.json)绑定实际SQL/事务及替身模型，角色隧道已清理。原29表458列不改、生产未切换、未提交推送。OpenSpec 3.2完成，当前9/16，下一3.3完整告警/事件字段DTO及逐项对照；Q仍仅预留，旧r13暂停。

# 2026-11-04 A告警基本查询与分诊执行

[28字段、流程与4例](../../../docs/investigation/socai2-alert-basic-executor-20261104.md)：新增A执行入口，三类已有SQL→一次模型→分诊/解释同事务发布，原请求回复、来源、步骤与用量留存；模型未知/失败不造成功，重复领取不重派、人工状态不改。9新+5受影响回归最新通过，[回执](../../../docs/operations/socai2-alert-basic-20261104.json)保首轮RLS夹具和测试驱动超时；既有独立PG、模型替身，无表变更/生产切换/提交推送。OpenSpec 3.1完成，下一3.2事件诊断执行；Q业务继续暂缓。

# 2026-11-04 主目录开发与OpenSpec衔接

本轮已完成[AI问答3条预留接口](../../../docs/investigation/socai2-case-ai-reserved-20261104.md)，统一501，3个直接ASGI检查通过、Ruff及OpenSpec strict通过。Q具体业务仍暂缓，下一项是OpenSpec 3.1的A实际执行适配。没有新业务库/模型/Tool访问或表变更。

开发已回到E:/aisoc/socai2的codex/case-baseline-history-20261103分支；本任务两个工作树注销，315个代码/文档/预览文件迁移一致，原有5个无关未跟踪文件保持。预览继续使用127.0.0.1:4174，未改页面逻辑。后续以[OpenSpec任务](../../../openspec/changes/complete-socai2-investigation-chain/tasks.md)为推进清单，[主设计](../../../docs/architecture/investigation-planning-design.md)在同一目录。AI问答按用户要求暂缓业务、只预留接口；旧r13暂停。此前实现和回执保持，迁移不代表新业务验收或提交。

# 2026-11-04 A/I读取与C1新鲜度

[20字段、四条只读接口及例子](../../../docs/investigation/socai2-stage-reader-20261104.md)：同快照核新鲜度、过期分析不进新C1模型视图、旧冻结不变；全状态分页及同Run Explain完整性，7新+6回归最新通过。原UUID类型失败及测试断言错误保留。默认关闭，未改表/页面/生产；实际A/I执行适配仍待。[回执](../../../docs/operations/socai2-stage-reader-20261104.json)。下方为历史批次。

# 2026-11-04 A/I结果存储

[28字段、事务与4例](../../../docs/investigation/socai2-stage-results-20261104.md)：A/I冻结输入、原子分诊/Explain/诊断发布，失败留存、引用角色、过期/乱序保护及新鲜度读取完成，10项独立合成PG检查最新通过。实际执行器、查询/模型步骤用量、新告警/事件DTO和C1新鲜度接线仍待；不把合成结果保存当真实A/I推理验证。29表458列不变，页面/生产/提交推送保持。详见[回执](../../../docs/operations/socai2-stage-results-20261104.json)。以下为历史批次。

# 2026-11-04 Fusion新表与Case链路

[53字段明细、事务及4例](../../../docs/investigation/socai2-fusion-ingestion-20261104.md)：Fusion新sink可显式选择，默认public保持。同事务原始材料/来源/对象/事件成员及首次结果，版本追加不改旧依据/人工状态，时间不倒退；候选窗口不当因果，原厂/置信度未知不补值。9writer/worker+1Case桥接最新通过，10旧路径回归通过，[回执](../../../docs/operations/socai2-fusion-ingestion-20261104.json)保导入/夹具失败；真实独立合成PG，其他边界替身，无真实模型/湖。原文与C1背景分离、进程字段和检测标签实际可读，预算未增。下一A/I实际产物写入及新告警/事件读取，不能用归并摘要冒充诊断。表/页面/部署/提交推送保持，生产消费者尚未切换，旧报告暂停/r13不重试。

# 2026-11-04 Case写入与调查读取接口

[九路径、36字段及4个例子](../../../docs/investigation/socai2-case-api-20261104.md)：新命名空间创建Case/更新成员/手动启动和历史、Run、Result、报告、冻结材料读取已接通，默认关闭。创建原子且幂等、单活跃/下一pending手动规则保持，启动返回当前保存状态。只读快照防混读，未知用量/费用、截断、最后记录、AI原答复对话与当前判断来源明确。11新+2回归最新通过，[本批回执](../../../docs/operations/socai2-case-api-20261104.json)保5批与4夹具失败；PG真实独立合成库，身份/模型/湖替身，无页面/部署/提交推送/表变更。下一Fusion告警/事件新writer与字段逐项核对，再事件Case关系和H/Q/外部来源；旧报告暂停/r13不重试。

# 2026-11-03 统一C1–C6手动执行器

[完整流程、字段和4例](../../../docs/investigation/socai2-baseline-executor-20261103.md)：新增start_full，同Run串C1/C2/C3、按问题Deep、C5与C6，逐项需求/执行/停止保快照并进入详细报告。最后一次模型调用在领取事务内保留；Token/时间仍共享原总额，不足系统交接，不加预算/队列/重试/自动下一轮。旧来源S编号不混入新综合。10新+6回归最新通过，[回执](../../../docs/operations/socai2-baseline-executor-20261103.json)保6批及指纹；既有独立合成PG，模型/湖/C2来源返回替身，角色/隧道已清理。并发加成员/重复启动/unknown占位、共享4Tool、最终Token不足及正式发布回滚已核。原29表458列/迁移/通用合同不变，页面/部署/提交推送不变。下一业务writer、手动HTTP与Run/Result/详细快照读取DTO；外部来源/H/Q和真实质量仍待，partial，旧报告暂停/r13不重试/5.3未完。

# 2026-11-03 C6最终综合、比较与原子发布

[完整流程、字段和4例](../../../docs/investigation/socai2-baseline-delivery-20261103.md)：最后一次模型合并再分析与正式交付，结论/来源/校验、closing_note、比较/影响、成员覆盖与建议真正产出；原合同JSON和Markdown由程序生成，连同正式Result/步骤/有条件采用同事务。系统交接结论为空；历史未选基线不误标首次；最终图须新鲜，成员范围不扩大全Case对象。14新+7回归最新通过，[回执](../../../docs/operations/socai2-baseline-delivery-20261103.json)保首3失败及定向修复/合同对齐记录。原表和预算保持，10批沿独立合成PG，模型/湖全替身，无页面/部署/提交推送。下一统一执行器与最终额度预留、writer/HTTP/读取DTO，再余下来源/人工和AI业务服务；真实质量未验，旧报告暂停/r13不重试。

# 2026-11-03 C5来源图及C6字段核对

[图流程、具体例子和C6字段明细](../../../docs/investigation/socai2-baseline-graph-20261103.md)：同Run从冻结成员/原字段/查询行确定构图，保强度/引用/时间/范围/省略，图步骤与工件原子保存；新证据新图，过期图不进入当前再分析。复用29表、原graph合同及预算，无页面改动。10项新检查+5项回归最新通过，[本批回执](../../../docs/operations/socai2-baseline-graph-20261103.json)保留夹具及UUID序列化失败和0测试空批次；PG为原独立合成库，模型/湖替身，9批角色/隧道清理。下一C6正式结论/交付/跨轮比较/影响/图新鲜度，再完整编排和HTTP/writers；须预留最终模型额度。外部图/主机/认证/余下背景和真实质量未验，未部署/提交推送，旧报告暂停/r13不重试。

# 2026-11-03 动态Deep和补证后再分析

[流程、字段和两个完整例子](../../../docs/investigation/socai2-baseline-deep-20261103.md)：同Run冻结问题→模型选B绑定→实际查询→重新读返回→回答/交接/额度停止，C3再分析按新证据集新增记录，旧分析不覆盖。人工反馈/历史分析与原始观察分角色，全请求/答复/参数/身份/用量留账；现表复用、无新业务DDL。10项新检查+9项回归的最新结果和消息上限失败原件见[回执](../../../docs/operations/socai2-baseline-deep-20261103.json)。PG为独立合成库，模型/CH全替身，未部署或修改页面。下一C5/C6和完整编排/HTTP，产品主机/认证等适配仍待；报告暂停/r13不重试。

# 2026-11-03 C4第一批字段读取与确定查询

[字段、表、处理逻辑及完整例子](../../../docs/investigation/socai2-baseline-c4-evidence-20261103.md)：新路径读冻结OCSF的PID/父进程/命令行/会话及完整网络端点，进程/网络固定绑定查询接同Run/预算，保存原件、状态、来源投影和新问题视图，不自动发全套查询。11项本批＋4项回归最终通过，[回执](../../../docs/operations/socai2-baseline-c4-evidence-20261103.json)保留首轮字段名错误/测试断言错误及定向验证。PG为21原独立合成库，CH全替身，测试角色/隧道清理，无新容器或真实业务调用。表/页面/部署保持。

下一动态Deep、主机产品/认证适配及补证后再分析，再C5图/C6交付；本批不是完整Deep。未知执行仍占槽、手动启动不变，不恢复报告修复或r13，不提交推送。

# 2026-11-03 C3初始主分析及领域结果

[字段/执行/例子](../../../docs/investigation/socai2-baseline-c3-20261103.md)：同Run一次共享模型调用，保全成员/六问题、四领域适用性、局部发现/冲突/替代解释及补查需求；请求先提交再派发，原答/用量留存，来源/角色/范围校验，不发布最终结果或自动采用。12项新检查+7项原回归最终通过，[回执](../../../docs/operations/socai2-baseline-c3-20261103.json)记录模型替身和PG实测边界。模型全部合成，业务表/页面/部署保持，无提交推送。下一C4必要语义与Tool/Deep、C5图、C6交付及补证后再分析，HTTP和业务writer未接；报告暂停/r13不重试。

# 2026-11-03 C2三类背景查询与模型视图

[字段、行为及例子](../../../docs/investigation/socai2-baseline-c2-20261103.md)：资产/同对象历史告警/内部TI接同Run，六来源状态/范围/时间/限制落原表；重复不重查、Run共用额度、查询未落定不能发布。模型视图原值guard、整案覆盖和8192/2048字节约束，未调用模型。11项本批+8项原流程回归最终通过，[回执](../../../docs/operations/socai2-baseline-c2-20261103.json)保原失败和逐项复用。原独立合成PG库、账号/隧道清理，无业务DDL/页面/部署/提交推送。下一C3主分析/领域→C4 Deep/Tool→C5图→C6交付，UEBA/知识/Graph来源及业务入口仍待；报告暂停/r13不重试。

# 2026-11-03 C1整案数据准备接入并验证

[字段来源/冻结规则/例子](../../../docs/investigation/socai2-baseline-c1-20261103.md)：单读视图固定Case、全成员与材料、事件诊断/归并依据、人工版本、当前判断及选用历史；保存六项初始问题和缺口。现有工件表承载C1快照，未改表/原通用合同；精确旧版本读回和引用角色校验已接。11项C1及10项原事务回归最终通过，[回执](../../../docs/operations/socai2-baseline-c1-20261103.json)保留首轮2个测试问题及复用来源。21现有独立合成库，临时账号/隧道清理。模型视图和C2-C6/HTTP未接，无页面/部署/模型Tool/提交推送，报告暂停、r13不重试。

# 2026-11-03 新socai2存储事务实现并完成真实PG验证

[实现、字段来源及边界](../../../docs/investigation/socai2-baseline-storage-20261103.md)：成员/范围版本→同一pending维护或后续新pending→冻结材料与提交running后执行→结果及自动采用原子发布→历史读取。17项不同服务/PG检查最终通过，含两种先后顺序、单次派发、提交失败不执行、回滚、旧范围和较新人工判断保护；[逐项回执](../../../docs/operations/socai2-baseline-storage-20261103.json)保首轮测试角色漏权限失败及后续定向验证。21原独立合成库，临时受限角色和隧道已清理，无新容器。123迁移等五合同文件与设计树一致，无DDL更改。

新服务尚未注册HTTP或接完整C1-C6执行器，旧业务writer保持。下一补完整C1冻结输入及后续阶段/鉴权DTO；页面未改，报告暂停，r13不重试，未部署/提交推送。

# 2026-11-03 基础调查记录新增、合并更新和竞争控制（旧122方案历史记录）

[本地实现与数据库合同](../../../docs/investigation/baseline-execution-record-20261103.md)：连续成员变化合并同一待更新Run；领取事务提交running后才执行，后续变化另建待更新Run。迁移122、Case→Run锁、唯一待更新及唯一活跃基础调查约束、启动版本冲突、幂等读回及历史读取已写入独立实现分支。78不同用例最新53通过25跳过；7个真实PG事务测试已准备但本机无引擎，迁移/真实并发/RLS尚未验。没有定时领取/结束自动接续，需明确启动；有活跃调查时拒绝本次启动但保留待更新。无页面/线上变更、模型/业务Run或提交推送，报告仍暂停。[本批回执](../../../docs/operations/case-baseline-history-20261103.json)。

# 2026-11-03 最新页面本地可访问，保存字段工作进度

远端需求更新为 c71afb5，已建立独立 codex/functional-alignment-20261103 worktree。http://127.0.0.1:4174 页面已启动；首页和27个脚本/样式资源200，浏览器案件资料页可读。当前字段修复及明细按用户要求本地提交，后续在新分支对齐三类调查流程和页面功能，不直接开始新后台实现。[目录、入口与衔接](../../../docs/investigation/local-design-preview-20261103.md)。

没有合并远端到原工作区；既有功能worktree保持。无新业务代码/业务测试、真实模型/Run、推送或部署；旧报告和证据保持。新版统一产品文档取代旧讨论作为理解入口，原85项对照保留旧版本标识。

# 2026-11-02 字段逐项对比完成

[85 项字段与数据条件明细](../../../docs/investigation/page-field-support-matrix-20261102.md)按页面需求→已存表/列/JSON→实际出口→具体差异列出，包含告警 37、事件 24、操作数据条件 12、Case/Tool 12。缺独立事件业务事实/时钟、普通评论和准确活动关系；Case 原文必要语义与湖 Tool 已存明细仍漏读。状态分组/写回不一致单列，交后端。补核审批到动作已有同 ID 连接；不能把该路径 actions.incident_id 当 Fusion Incident。

用户 16 项已确认语义补了当前状态表；旧事实注明原时点。第 1—4 批继续保留，未新改业务代码/DDL，未重跑测试或调用真实服务/模型/Run，未部署/提交/推送。来源与文档检查见[本轮清单](../../../docs/operations/page-field-support-matrix-20261102.json)。下一仅补明细 T 表已存字段消费缺口；页面功能交后端，报告暂停。

# 2026-11-02 任务收口为字段与页面数据支撑

用户明确功能由后端实现。本轮停止沿原第5批列表、第6批管理做功能开发，改为核清字段、存储、关系、语义和读取能否支撑页面；功能规则转为数据合同和后端交接项。下一先汇总已修字段及剩余数据缺口，区分可直接使用、可派生、内部缺口和输入限制。必要的数据链修复继续，功能实现不作为本轮验收条件。

仅同步文档，无新代码/测试/部署；第1—4批既有改动保留，不自动回滚。报告暂停、r13不重试、5.3未完。见[当前范围与数据计划](../../../docs/investigation/field-alignment-impact-and-repair-plan-20261101.md)。

# 2026-11-02 字段第4批共享读取本地完成

[第4批](../../../docs/investigation/field-alignment-fix4-20261102.md)补原厂/编号分工、IOC及逐成员对象/阶段、负责人、资产标签/匹配、当前多Case、同次分诊评分及Case检测字段；first_seen按发生时间，新增业务updated_at与材料source_updated_at分开，GET不再写缓存。资产读取和新增模型字段有界并明确省略，旧图选取按Case.alert_ids；无DDL，旧数据/报告不回填。

68不同相关用例最新通过（新增9），三处初失败/错误及定向复核保留；同输入基线对照与资产SQL解析通过。仅本地替身，无真实业务服务/模型/Run/部署。四批修改仍在工作区，HEAD为b400fd0。下一第5批列表合同，管理写入/级联、Case语义/Tool、报告后续仍待；r13不重试，5.3未完。[回执](../../../docs/operations/fusion-field-fix4-20261102.json)。

# 2026-11-02 字段第3批本地修复与比对完成

[第3批记录](../../../docs/investigation/field-alignment-fix3-20261102.md)补S1-01/04/05/06/07、S2-03—06：保留已有时间/对象/规则及标签，记录有限窗口来源与截断/未知状态；评分未计算入库NULL；统一activity/session，按算法读SHA256，raw有界合法JSON；两湖Tool去重后限量及新合同。复用现有PG列/JSON、CH字符串及Redis窗口状态，无DDL，API镜像同步。

124不同相关用例最新通过（Fusion115/API9，新增20），初失败及定向复核保留；6组字段与2组双Tool SQL同输入对照、SQL方言解析及23文件Ruff通过。仅本地模拟/SQLite，不证明线上验收；0真实业务服务/模型/Run/部署。第1—3批仍未再次提交，HEAD为b400fd0。下一第4批共享读取与业务时间；页面管理、Case语义/Tool及报告仍待，r13不重试、5.3未完。[回执](../../../docs/operations/fusion-field-fix3-20261102.json)。

# 2026-11-02 字段第2批本地修复与比对完成

[第2批记录](../../../docs/investigation/field-alignment-fix2-20261102.md)完成S1-03/08、S3-01/02：收到的事件身份参与新生成告警指纹，三个入口独立发生/重投分开；归并键增加类型并隔离旧索引，实际依据保存/读回；提升开关在执行分支生效。复用alerts JSON与快照，无DDL；API镜像模型同步。旧首份材料可证明同源才复用，旧PG事件/报告不重组。

66相关用例最新通过（Fusion56、API3+7），首轮测试收集导入错误原件保留；三入口/两类归并键/开关及旧身份基线对照通过。仅本地替身与INSERT参数验证，没有真实服务、Run、模型或部署。两批修改留工作区，HEAD仍b400fd0；下一第3批字段、时间和完整性。报告修复仍暂停，r13不重试，5.3未完成。详见[回执](../../../docs/operations/fusion-field-fix2-20261102.json)。

# 2026-11-01 基线提交与字段第1批修复/比对完成

按用户要求先保存本地基线`b400fd0`（339文件，r13实现/证据及六段核对，无关文件未加入），再实施[第1批S2-01/02](../../../docs/investigation/field-alignment-fix1-20261101.md)：统一来源事件ID与UUID表示，修湖默认列绑定，分开缓冲/确认写入指标，兼容旧Case引用。文档入口和任务状态已同步；修复仍留工作区，未自动第二次提交或推送。

39相关用例含参数场景最新通过，首轮Fusion34过3测试记录错误、API2过；驱动原地改变记录导致观察断言失败，修测试副本后只复核3项通过，原件保留。相同输入对照b400fd0：metadata.uid+正常行的两行批次从本地驱动绑定KeyError/计数0变为绑定2。未连真实CH、无新Run/模型/部署，不称线上验收。下一第2批身份/归并，其他字段批次及报告问题仍待，r13/5.3边界不变。

# 2026-11-01 六段字段核对完成，修复顺序已整理

[第5段Case输入/Tool](../../../docs/investigation/case-input-tool-field-audit-20261101.md)确认已有检测/分诊字段漏投影、原文缺必要语义视图、Tool漏读已存字段。4项本地观察完成；首轮脚本datetime序列化失败在首项完成前发生，初版/错误保留。r13六份请求、四份Tool原件复核：24次来源字段出现均完整，行数1/1/0/0、0复用，无新调用。

[第6段影响与修复顺序](../../../docs/investigation/field-alignment-impact-and-repair-plan-20261101.md)对照14份r13原件，确认字段缺口与报告生成/解释偏差须分别修，不能用补字段称语义通过。现有账本/H1足够，无需Case记忆层。六段仅本地核对完成；下一建议先修S2-01/02事件ID及湖列绑定，再按具体功能补字段、页面读写、Case/Tool及报告。用户16项决定保留，无新问题待答复。

本轮业务源码/部署未改、真实DB/模型/Run/湖调用0，未恢复报告修复或重跑r13。5.3仍未完，不提交/推送/合并/归档；输入本来缺失仍排除，历史证据未验范围保持。

# 2026-11-01 第4段页面API与管理本地核对完成

[第4段结果](../../../docs/investigation/page-api-management-field-audit-20261101.md)核对8组对接问题：列表查询／排序／导出、来源及负责人等投影、状态及实际调查统计、反馈关闭／SLA、评论及批量管理、事件业务持久化与联动、时间口径、活动来源。已有总体stats可复用前三卡，不能误称完全没有总体统计；当前v2启动缺Alert状态写回，事件管理仍缺完整后端。用户第16项确认解决事件关闭全部成员、保留各自判定并保存前提示。

11项不同本地观察：首批前9断言已执行，随后时间线夹具误写只读is_automated报错；初版结果仅结尾保存，9项SQL／响应明细未落文件，原脚本和执行边界已记，不伪造原件。改actor_type后只跑时间线1项；另对新发现详情GET叙述缓存更新updated_at观察1项。无业务源码修改／实际DB写入／模型／Run／部署，不能称一次11项全绿或线上验收。前四段本地核对完成，下一第5段Case材料／分诊配对／Tool；上游输入问题排除，r13不重试、5.3不核销。

# 2026-11-01 第3段事件／对象／资产／Case关系本地核对完成

[第3段结果](../../../docs/investigation/fusion-relations-field-audit-20261101.md)记录5组内部缺口：归并键未区分对象类型、实际依据未完整持久化／读取、已存IOC与逐成员对象／战术投影遗漏、库存标签及查找键遗漏、旧单case_id与当前多Case成员口径并存。已支持PG事件成员、F4显式选择及回执、历史Run冻结范围和报告原件读取，不需另建Case记忆或图框架。

6项不同本地观察：Fusion2项首次完成；初API夹具将PG iocs列传给ORM被拒，确认Alert未映射该列，修正夹具只装载真实映射列后API4项完成，Fusion未重跑，原件保留。均为当前行为观察、非验收通过；无业务源码修改／真实服务调用／Run／模型／部署。前三段本地核对完成，下一第4段页面API和管理，沿用15项已定规则，不扩上游输入问题。r13不重试、5.3仍未完。

# 2026-11-01 第2段事件湖对应本地核对完成

[第2段结果](../../../docs/investigation/fusion-lake-field-audit-20261101.md)记录6项内部问题：ID选择／规范化不一致，metadata.uid漏映射导致实际本地驱动绑定失败丢批，activity位置不一致，hash误标，raw无提示裁剪，查询未去重。13不同本地观察（会话枚举夹具修正后只复核2项，复用11项；首次原件保留），复用r13四次真实查询，A各1行分别匹配A1／A2、B各0行；不把手工fixture当Fusion入湖证据。无新业务调用／模型／Run／部署或业务源码修改，线上触发未核，问题未修复。

输入缺失／错误继续排除，仅处理收到数据后的内部缺口。前两段本地核对已完，下一第3段事件成员、归并依据、逐告警对象、库存资产／标签及Case／旧Run范围。r13不重试、5.3不核销。

# 2026-11-01 第1段Fusion入库本地核对完成

用户补充范围：Fusion前置输入数据问题不用处理。已调整[第1段结论重分类](../../../docs/investigation/fusion-ingestion-field-audit-20261101.md#用户补充边界及结论重分类)与六段计划：输入缺失／错误只记限制，不追查、不修复、不要求补齐；仅保留Fusion收到数据后的内部丢失、替换、归并、存储及下游使用问题。原14项行为观察保持，不重跑；本次仅更新范围与记录。

用户要求先重新理解整个任务，明确是Fusion。远端告警页/事件页是需求基准；当前应从Fusion输入及入库开始，核对持久化、事件湖、关联、分诊/业务管理、API、Case输入、Tool及报告能否支撑。调查页面不做设计对比，但调查实现必须检查。停止仅逐个确认UI规则，先查数据链及断点，再问真正未决的业务语义。

按[六段计划](../../../docs/investigation/field-alignment-confirmations-20261101.md#分段核对计划)完成[第1段本地字段核对](../../../docs/investigation/fusion-ingestion-field-audit-20261101.md)，下一核告警与湖事件对应。已记录8项具体问题：时间替代、原厂语义、legacy身份折叠、规则/战术遗漏、实体提取、来源完整性/更新时间、默认置信度、提升开关。直接HTTP source-v1的独立身份及已有字段保存能力同时保留，不把不同入口混为一谈。

第1—15项已定规则全部保留，第15项已确认最近更新时间包含事件及成员告警变化、排除单独调查进度；第3—6项Case输入恢复纳入链路评估。当前入口为[需求与Fusion调查实现对照](../../../docs/investigation/field-alignment-confirmations-20261101.md)，已链接第1段结果；其余五段尚未完成。当前无待答复问题。

14项synthetic本地字段行为观察首次运行确认，复现当前行为及缺口，不等于需求验收通过；无业务源码修改、真实业务服务/模型/Run或部署。线上Fusion配置/源码、未随仓库迁入的ingest normalizer仍未核；本机SSH配置读取权限拒绝，未改权限。远端需求Git基准核实仍48f54abd。r13问题与旧证据保留，不恢复旧批次，5.3未完成；不新增框架或冗余测试。

# 2026-11-01 r13真实批次结束

r13已部署，473应用源码同固定候选。A报告产生6490个尾随空白字符，输出3000tokens后截断；B虽completed/partial，仍把空查询当弱反证、未提供审批写成无审批，并混淆E1/E2。C跳过，整批语义验收未过。4查询全部QueryFinish成功、0复用，6模型20334tokens，6调用未定价；旧数据/报告与其他服务保持。原17项直接用例复用，业务重跑0；批次结束不重试，5.3/P3继续待办。见[回执](../../../docs/operations/investigation-r13-report-validation-20261101.json)与[原因分析](../../../docs/operations/evidence/investigation-r13-20261101/review.md)。

# 2026-11-01 r12后报告来源本地修复

新增PID/账号按所引原始字段核对，修正两种实际协议误拒，拒收已知空查询原因猜测/占位，并合并一次纠错的可判定错误。17个不同直接方法最新通过，含6新增；A/B原回复离线回放继续拒收坏报告，原raw/usage/预算保持，0新真实调用/部署。线上仍r12，完整报告语义及5.3未过；不新增Case记忆系统，不重跑旧批次。见[修复说明](../../../docs/investigation/report-grounding-fix-20261101.md)及[回执](../../../docs/operations/investigation-report-grounding-20261101.json)。

# 2026-11-01 r12部署与A/B真实报告复验结束

r12已部署，472应用源码同固定工作区快照。A/B各一次均failed/partial；4真实查询1/1/0/0行、0复用，8模型25783tokens，8调用未定价。raw全部完整，反馈隔离生效；来源推理错误、协议误拒和引用问题仍在，C按前提跳过。旧告警/Case/报告及其他服务保持，0业务测试重跑。见[回执](../../../docs/operations/investigation-r12-report-validation-20261101.json)与[分析](../../../docs/operations/evidence/investigation-r12-20261101/review.md)。本批不重试，P3/5.3仍待；下一修具体来源归属与证据强度，不新增Case记忆或通用框架，不归档/推送/合并。

# 2026-11-01 保留r11问题，仅更新调查文档与审阅指南

用户要求“先保留当前问题，更新调查模块的相关文档和审阅指南”。当前只文档维护：统一r11/a543ad6（功能49a04eb）基线，修正文档仍写r1/r10在线、r11待部署及旧模型/Tool合同的冲突。新入口docs/investigation/review-guide-20261101.md登记R11-01协议误拒、R11-02纠错指令入正文、R11-03来源/无源推测、R11-04关系判断，以及R10-01空查询推理真实效果未验；均保留。原结束独审标明r3本地范围，原请求/响应/失败回执不改。无业务源码/测试修改、业务测试、远端访问、部署或新Run；OpenSpec16/17、5.3未完，不归档/推送/合并。后续“继续”先沿当前文档任务理解，不自动重跑已结束批次。

# 2026-11-01 r11已部署，正向样本真实查询通过但报告仍失败

用户选择新建明确标记测试样本后，r11/a543ad6（功能49a04eb）已部署，镜像59d9fe097588…，472实际源码hash一致；专用fixture租户新增2告警+2湖事件+1Case，唯一Run22b48b78-3716-5a64-994f-788d020dc760为failed/partial。两条raw371/425B在4次模型请求均完整；2正式真实查询各1行、2独立预检查询，全部QueryFinish核实，0复用，12728tokens/4调用未定价。首份与纠错JSON及成员均有效；首份协议待核措辞被拒，纠错后空格/状态/引号句式误拒与无源“文档服务器/故意缺失”、校验指令泄入正文并存，不能只放宽规则称通过。16事件18工件、30HTTP、75远端文件hash核；额外1只读状态查询单列。旧告警整行hash及r10报告字节保持，core/agents/网关/配置/开发Key保持。见docs/operations/investigation-r11-positive-fixture-20261101.json及evidence/investigation-r11-20261101/review.md。本批结束不重试；本轮未新增功能修复，复用7项直接验证；5.3继续待办，不归档/推送/合并。下一聚焦不确定句式误拒与纠错报告质量，不扩大框架。

**2026-11-01 r11准备：** 发布包和明确标记的正向样本草案已准备，等待样本来源选择；线上仍r10、没有新调查或数据写入。见[准备回执](../../../docs/operations/investigation-r11-preparation-20261101.json)。

**2026-11-01 本地报告边界修复与数据核对：** 本地`49a04eb`已修正三阶段共用证据规则、同源分诊摘要去重及程序生成的查询状态/数量，7个受影响直接用例最新结果通过（含2新增），未部署、0新Run/模型。只读核对确认生产湖6行均3002，Office两行raw为user.session.start，另fixture租户仅3条4001；现有完整raw告警没有对应进程/网络湖记录，不能放宽过滤或改造登录数据充数。新提示词真实语义仍未验，未新增通用语义校验器。 见[结果](../../../docs/investigation/source-boundaries-20261101.md)。

**2026-10-31 r10结构化报告交付与真实空查询核验：** 源码`51086a4`已部署r10；首份正式报告使用JSON Schema，模型A引用映射公共UUID，具体校验反馈和原一次纠错/预算保持。唯一完整raw演示告警主Run `4f094ed4-b4f9-5db9-8cc2-b5f8c781858e` 为completed/partial：3模型、2真实湖查询、0复用、10292 tokens；首次报告格式/成员通过、纠错0。两次成功空查询经ClickHouse QueryFinish核实，报告却把空结果当矛盾并猜测采样/丢日志等原因，语义仍未过。 42个受影响方法最新结果通过，详情见[回执](../../../docs/operations/investigation-structured-report-20261031.json)。OpenSpec仍16/17，首次打包权限失败已修正并留证，无第二个Run/推送/合并。

**2026-10-31 r9已交付：** 用户明确确认后部署`bf2bd9c`，472源码一致。唯一追加failed/partial：JSON纠错后关系成员重复被拒；3模型回复/11740 tokens、1复用/0新湖查询，父报告保持。模型等待修复已上线，但本批最长26.50秒，未实际覆盖超过45秒。详见[回执](../../../docs/operations/investigation-model-wait-20261031.json)，OpenSpec16/17、完整报告未验收。

**2026-10-31 r8协议边界交付：** 源码`a41ae07`已上线；允许明确协议不确定表述，仍拒无据肯定/否定，10项必要直接用例通过。唯一真实追加failed/partial，首次结论UUID错误后已派发纠错，但约45秒时网关Timeout/HTTPStatusError，未得到最终回复。7540已知tokens，第三次用量未知；历史复用及旧报告保持。见[最新回执](../../../docs/operations/investigation-protocol-uncertainty-20261031.json)。16/17、不归档，当前真实阻塞为模型纠错回复未完成；共享网关配置保持。

**2026-10-31 r7来源交付：** 源码`f19cc70`已上线，程序明确展示复用来源和逐条告警匹配；30项受影响用例经一次额度修正及3项定向复核最终有通过证据。唯一真实网络追加为failed/partial：模型已识别复用及前两行对应，但纠错仍触发协议字段规则，历史判断/未匹配语义仍有偏差。3模型、1复用、0新湖查询、11341 tokens；旧报告不变。见[最新回执](../../../docs/operations/investigation-source-alignment-20261031.json)；16/17、不归档、不重复本批。

**2026-10-31 r6功能交付：** 网络协议推断及成员遗漏已修复并上线，源码`7330a7c`；29项受影响直接验证通过。仅一次真实网络追加completed/partial，两个成员均有判断，报告保留TCP/443；3模型、1历史复用、0新湖查询、12780已知tokens，父报告保持。报告仍有历史复用误称新查、误述H1及行归属错误，不能称完整语义通过。见[最新回执](../../../docs/operations/investigation-network-report-fix-20261031.json)，OpenSpec仍16/17、不归档；开发Key保持有效。

**2026-10-31 功能继续交付：** r5已上线，源码`3324fea`。本轮6个真实Run均完成并保留partial，预算纠错、原生Tool、历史复用及原报告保持已验证；16模型、2新湖查询、4复用、65209已知tokens。Office无源标签改善，网络报告仍存在TCP/443写成HTTPS、漏成员判断等质量问题；完整业务验收保持未完成。见[共享回执](../../../docs/operations/investigation-functional-followup-20261031.json)。旧追加change5/5，当前审计change16/17，不归档；开发Key持续可用。

**2026-10-31 最新功能进展：** [r3实际回执](../../../docs/operations/investigation-audit-live-r3-20261031.json)：部署完成，固定批次3主Run中1完成/partial、2因纠错预算失败，2追加未发；8模型、6湖查询、29824已知tokens。已本地修复超预算纠错输入，6项直接验证通过，未追加真实调用或部署该新修复。两个change共享此回执，当前15/17，不归档。

用户要求后续聚焦功能、减少额外设计。两个原租户的一年全API权限开发Key已按新授权创建，远端私有保存并验证4次GET/200；见[无明文凭据回执](../../../docs/operations/evidence/investigation-audit-fixes-20261031/live-r3/dev-credentials/receipt.json)。下方记录均为此前阶段。

**2026-10-31 r3实际执行授权已确认：** 用户对限定更新及固定5个Run复验确认后再次要求继续；[执行前提回执](../../../docs/operations/evidence/investigation-audit-fixes-20261031/authorized-preflight-20261031.json)记录新SSH连接超时和本机默认路由。授权已落实，剩余条件是目标连通性及既有身份核实，不再重复请求部署许可。本轮0远端命令/部署/业务调用，任务仍14/17，复用31项和结束独审。

**2026-10-31 调查本地交付继续完成：** 源码commit `bb8dbc3`；[结束独审](../../../openspec/changes/fix-investigation-audit-gaps/audit.md)0必须修，复用31项直接结果且未重跑。[提交/候选绑定](../../../docs/operations/evidence/investigation-audit-fixes-20261031/source-commit-attestation.json)核476文件内容一致（440仅换行差异）；[5份限定复验请求](../../../openspec/changes/fix-investigation-audit-gaps/retest/plan.json)已固定但未发送。任务14/17，21只读SSH连接超时；真实更新/复验、共享回执与归档完成条件待办。无部署或远端推送。

**2026-10-31 调查审计问题本地实施：** [执行记录](../../../docs/investigation/audit-fixes-implementation-20261031.md)及[回执](../../../docs/operations/investigation-audit-fixes-20261031.json)记录A01/A02/D01修复、9个新增必要直接用例及最终31个不同用例通过。Office新材料与纠错组合16929/17018、余89，保旧报告；r3候选仅本地准备，独立复审/新commit/实际更新与复验待做。OpenSpec按实绩勾选12/17，不提前归档或核销旧任务。

**2026-10-31 调查审计后OpenSpec规划：** [提案](../../../openspec/changes/fix-investigation-audit-gaps/proposal.md)、[设计](../../../openspec/changes/fix-investigation-audit-gaps/design.md)、[17项任务](../../../openspec/changes/fix-investigation-audit-gaps/tasks.md)已形成；顺序为进程证据→概况失败模式→原始取材→组合验证/交付。3项规格描述待实施合同，任务均未执行。与已有追加修复共用后续一次真实批次，各自按证据关闭；[规划校验](../../../openspec/changes/fix-investigation-audit-gaps/validation.md)使用仓库本地OpenSpec1.13.0，旧规格仅补缺失Scenario。无业务源码、测试、部署或Git提交/推送。

**2026-10-31 调查模块详细审计：** [完整报告](../../../docs/investigation/design-implementation-audit-20261031.md)覆盖需求、设计、接口、Case执行、模型/Tool、持久化与证据。确认2项功能缺陷（进程事件类别、失败概况模式切换）和1项取材设计缺口，未改业务代码；两处文档现行说明已修。静态固定47实现/依赖文件及11测试文件51定义，207原响应和3冻结文件hash一致。当前仍不能宣称最新版本完整验收；本轮无新测试、远端调用、部署或推送。

**2026-10-31 调查文档与测试基线对齐：** [最新指南](../../../docs/investigation/audit-guide-20261031.md)统一当前设计、接口、证据目录与阅读顺序。本地源码5b95138及6项受影响直接用例通过记录，与512c004/r1四案例真实HTTP分开；原111项检查3项失败保留，r2常驻替换/真实复验待做。补齐required_tools及停止原因，历史报告改指当批冻结脚本和输入。仅文档/静态核对，无新业务测试、远端调用、部署或推送。

**2026-10-28 模型预检x86_64额外交付：** 在原ARM64 r5包之外新增[Linux x86_64/amd64离线包](../../../model-preflight-x86_64-20261028T020724Z.tar.gz)、[使用说明](../../../START_HERE.x86_64.md)及[SHA256](../../../model-preflight-x86_64-20261028T020724Z.tar.gz.sha256)。使用官方Python 3.12.14 amd64基础镜像按digest重建；测试逻辑、提示词、案例、判据和自测源码保持，probe.py仅改架构帮助文字，移除旧字节码缓存。最终镜像28项禁网客户端自测通过，导出镜像全部层hash/应用文件hash、ELF x86_64、外层及包内SHA256、实际解压/docker load/案例列表及Bash启动已核；包内BUILD-INFO.json、SELFTEST.log留存来源及验证。完整包43,238,827字节，SHA256 `f4034a98ad4eae74c3237b22ed7004e162e0c808bf5104a1c1085ad2e9b28bc4`。原ARM64包和原START_HERE.md保留；未调用真实模型、修改业务源码或部署/推送，目标现场模型能力仍待实测。

**2026-10-25 调查M8a3.2限定通过：** API显式结果GET强制Bearer、复用原双read权限及可信身份转发，同版三重hash校验；33直接与独立同33、6hash/12完整HTTP重放一致。[回执](../../../docs/operations/investigation-result-gateway-20261025.json)。dev旁路只对新GET关闭，旧认证/query默认不改；仅ASGI/替身，真实PG/双进程网络下一步，无启动/账本/模型或部署。

**2026-10-25 调查M8a3.1限定通过：** 独立内部只读GET app的专用token/tenant/actor、请求覆盖拒绝/脱敏/资源所有权已过13新＋45相关及独立同58，6hash/11 ASGI重放一致。[回执](../../../docs/operations/investigation-internal-read-api-20261025.json)。外部用户read权限与真实PG仍分别待API网关/a3.3，不改旧路由/权限，无新查询模型/账本/部署。

**2026-10-24 调查M8a2限定通过：** 新owned reader按当前tenant/Run同锁核唯一begin及所有原工件归属/hash，自动恢复上下文并读同M7结果；13新＋43相关及独立同56、6hash/3组完整读回通过。[回执](../../../docs/operations/investigation-owned-reader-20261024.json)。只SQL替身，无当前Alert/新账本或调用；实际auth/permission/PG/显式HTTP下一步，不改旧入口或部署。

**2026-10-24 调查M8a1限定通过：** 历史读上下文从原owned begin重建，当前读者与原principal分开，正文/控制/profile/plan字节hash精确校验；11新＋40相关及独立同51、6hash/3组重建通过。[回执](../../../docs/operations/investigation-profile-restore-20261024.json)。仅纯恢复，实际认证/存储归属/正式HTTP与启动后续逐块；无新业务/模型/部署或合main。

**2026-10-24 调查M7c实际发布：** 原稳定Run只增1事件4工件，现6/14；全新进程读到同manifest/report/execution，原M6已核列与正文校验和不变，额外查询/模型0。临时身份已清理/子进程exit0，通知未投递。[回执](../../../docs/operations/investigation-publication-pg-seam-20261024.json)、[受控合成报告原字节示例](../../../docs/investigation/examples/fixed-recon-published-20261024.md)；160合同及probe独审43通过，真实结束独审限定ACCEPT/0必须修（独立11项/14hash、PG全14及样本/进程/权限核验）。仅有限目标complete_for_scope；M8业务入口/stream、Case与Deep价值仍待，无部署/合main。

**2026-10-24 调查M7b代码通过测试：** 21新＋128相关149项，锁内一次发布/精确manifest读，SQL双正常增加1事件4工件，重复/冷读一致；P2原source核验缺口修复，含未采用source的原M3 event/kind/hash均钉住，6红反例/源码保留。[回执](../../../docs/operations/investigation-publication-store-20261024.json)未参与实现者独立52项/6hash/7组重建限定ACCEPT、0剩余必须修。仅SQL替身，未真实PG/通知投递；c下一仅追加发布/前后冷读，无新查询或模型，旧列/历史失败保持。

**2026-10-24 调查M7a限定通过：** 16新＋112相关128项，独立当前16/5hash/5组同版包和MD重建一致，0必须修；固定section、缺evidence null、execution发布快照、基线/late settle拒绝及安全typed事实报告已实现。[回执](../../../docs/operations/investigation-publication-preparation-20261024.json)。仍仅candidate，持久/通知未尝试；下一b原子发布/读取→c真实PG，无新业务网络/模型/部署或合main，旧列/unknown/失败保持，2.2/2.3未完。

**2026-10-24 调查M6.2c真实接缝：** 11新＋101相关112项通过，probe独审P2全关联验收缺口修后15项通过；新Run实际runtime一次独立v2业务HTTP/CH、5事件10工件全部引用/hash/UTF-8读回、重复/冷读同交接不重查，模型0。CH预检另1次；新临时PG角色禁登录撤权/活动0，API核身份后停。[公开回执](../../../docs/operations/investigation-fixed-runtime-seam-20261024.json)真实结束独审限定ACCEPT/0必须修。有限ready仅来源核对，性质/授权未知，候选未M7发布；不改旧Run/旧源码，无部署/合main，下一M7同版交付，2.2/2.3未完。

**2026-10-24 调查M6.2b2控制器限定通过：** 18新＋79相关97项、独立89项子集/6hash/7观察及并发回归通过。独审P2取消窗口抢先finalize已修：重复blocked只报交接待完成，观察核已留存后才清；失败原源码/hash与反例保留。见[回执](../../../docs/operations/investigation-fixed-runtime-controller-20261024.json)。一次实际gate＋SQL/HTTP替身，不证明真实服务；持续进入c新Run/临时身份/独立v2真实PG/HTTP/CH，模型0，原入口/预算/历史失败保持，无部署/合main。

**2026-10-24 调查M6.2b1事务代码限定通过：** 实际ReconExecutionStore和M3函数在SQL事务替身下105项及独审通过，5hash/6观察一致；并发claim唯一、候选/state/未确认观察同事务，重复不覆盖，unknown不释放，通用/托管版本互拒。见[回执](../../../docs/operations/investigation-fixed-runtime-store-20261024.json)。仅代码/替身，非真实PG原子性；持续接b2控制器、c真实PG/HTTP/CH，无模型/部署/合main，2.2/2.3不勾。

**2026-10-24 调查M6.2a限定通过：** 已冻结版本化单次整窗query计划/step/attempt，claim预检不预留或授权HTTP，重复执行不接管；实际M3 unknown/超额/时限和取消保持，结束引用不覆盖。12新＋68相关及独立同80项、6hash/计划与观察一致，见[回执](../../../docs/operations/investigation-fixed-runtime-state-20261024.json)。仅纯控制；下一b原子store/真实M3门与交接保存，再c独立真实接缝，持续授权无需逐块确认；无真实业务/模型/部署/合main。

**2026-10-24 调查A3限定通过：** 投影阻断保已核材料/查询/全部来源版本refs及真实source状态，投影阻断交接保持真实来源状态，不改写为来源不可用；正常视图走原有限政策。10新＋90相关及独立同100项/4hash/10观察通过，7种正常视图前后完全相同，见[回执](../../../docs/operations/investigation-material-projection-20261024.json)。仅纯准备/结构化交接，实际持久/人工投递和M6.2运行器未验，2.2/2.3未完；无真实业务/模型/部署/合main。下一接M3 gate、固定查询/去重及保存。

**2026-10-24 调查A2限定通过：** 完成政策显式版本化，子窗口保事实但partial，完整窗口仅确认有界查询而非整体调查完成。7新＋64相关、独立同71项/3hash/12观察通过，见[回执](../../../docs/operations/investigation-window-policy-20261024.json)。A3合同已核待实现，M6.2实际执行/持久交接未验，旧回执/失败保持；无真实业务访问/模型/部署或合main。

**2026-10-24 调查A1地址接缝限定修复：** 先合同/strict，再统一Agents v2地址身份、caller/证据/Deep匹配与指纹；原字段值/路径、响应及source hash保持。8新增＋103相关共111项通过，未参与实现者独立83项/反例/7hash复核限定ACCEPT、0必须修。见[回执](../../../docs/operations/investigation-network-identity-20261024.json)与[实施记录](../../../docs/operations/unified-investigation-implementation.md)。仅离线合同，无真实业务/模型或部署/合main，旧版/API/历史失败不改。下一A2/A3精确合同，再M6.2；2.2/2.3保持未完，阶段提交/推送。

**2026-10-24 调查独立总审计与规划：** 三位新审阅者核7b7bb6b，140项合同通过/39哈希条目一致；新增反例确认A1 mapped IPv6接缝误拒P2未修，A2子窗口ready和A3程序路径模型投影限制须在M6.2前定合同。保留架构但不认定完整调查有效，见[审计与后续流程](../../../docs/investigation/independent-audit-20261024.md)。先修接缝/合同，再M6.2→M7→M8a，Case整体/自动政策前验主分析及Deep收益。本轮仅文档/离线探针，无功能修改、业务访问、模型、部署或合main；历史失败/unknown与2.2/2.3未完保持。

**2026-10-24 调查M6.1纯固定政策限定通过：** 先精确合同/预期/strict再实现，13新＋M4采用13＋视图11＋M1绑定11共48项直接通过，未参与实现者独立复跑与回执重建一致，限定ACCEPT、0必须修。正常来源产4条program事实及六问题状态；空/失败/未知/冲突/截断/不可读正文保合法事实和全部refs并partial，性质/授权仍未知。所有结果均停止，不自动补查/模型，不发布Run完成；ready只对应有限来源核对。见[回执](../../../docs/operations/investigation-fixed-recon-20261024.json)及[实施记录](../../../docs/operations/unified-investigation-implementation.md)。下一M6.2实际M3/query/去重与持久交接另验，完整2.2/2.3未勾；本批真实HTTP/PG/CH/模型/业务写入0，旧版/历史unknown/归档保持，阶段提交/推送，无部署或合main。

**2026-10-24 调查独立v2查询接缝实际通过：** 先规格/预期/strict，再共享场景卡、独立新应用及36项直接合同。02批新Run真实新HTTP→CH→PG：1命中/两对照排除，3事件/6工件独立读回，4认证反例拒绝，模型0，临时API及新PG身份已清理。01批字段假设失败保留；修为实际raw_event.telemetry[0]映射后新批次验证，未重放。见[回执](../../../docs/operations/investigation-v2-query-seam-20261024.json)及[实施记录](../../../docs/operations/unified-investigation-implementation.md)。未参与实现者独立36项及只读PG核验后限定ACCEPT、0必须修；正式M8/Deep整环/同版交付/Case继承仍未完成，tasks2.2/2.3保持未勾。旧源码/入口/历史unknown不改，无部署或合main，阶段提交/推送调查分支。

**2026-10-24 调查前置三块按步完成（前批）：** M1纯profile绑定11新＋原scope8项，I1正文45项及Unicode审阅问题修后复验，I2完整messages预算6新＋原模型15项，分别直接通过及未参与实现者窄审限定ACCEPT/0剩余必须修。tasks2.1按实际三块勾选；后续2.2/2.3未完，不归档。I2共用组装/执行前/egress的12KiB，8/10条在准备阶段明确超限，全部材料引用保留，不自动分组，不代表大材料已消费。见[实施记录](../../../docs/operations/unified-investigation-implementation.md)及[I2回执](../../../docs/operations/investigation-request-budget-20261024.json)。当批真实模型/业务HTTP/DB/写入0；随后独立查询接缝以上方回执为准。

**2026-10-24 I1来源正文局部降级限定通过：** M1保存后逐块实施I1，6新＋11视图＋13采用＋15模型合同通过；独审复现转义Unicode编码异常后已局部修复并复验，最终限定ACCEPT、0剩余必须修。有效结构事实和其他记录保留，正文缺口进入有限事实/readable，必要身份/hash/范围不放松。见[实施记录](../../../docs/operations/unified-investigation-implementation.md)及[I1回执](../../../docs/operations/investigation-optional-excerpt-20261024.json)，过程失败保留。下一块I2待做，tasks2.1未整项完成；真实模型/业务访问/写入0，旧版与生产未改。

**2026-10-24 M1业务profile纯合同限定通过：** 用户授权按步续接；在codex/investigation-review-20261024从a3a0108先补精确规格/预期并strict，再实现纯绑定。11新＋原scope8项通过，未参与实现者独立复跑并核源码hash/样例，限定ACCEPT、0必须修。支持无Case告警、触发与归属分离、4成员Case全选/部分选材及最早遗漏保留；不扩大原scope或能力。见[实施记录](../../../docs/operations/unified-investigation-implementation.md)及[回执](../../../docs/operations/investigation-profile-contract-20261024.json)。尚未接执行器/Case认证继承启动/新HTTP，模型/业务HTTP/DB/写入0；下一步I1，再I2。tasks2.1尚未整项完成，不合main或部署。

**2026-10-24调查main评审响应（仅评估/计划）：** 已拉取并快进本地main至`541511c`，新建`codex/investigation-review-20261024`。见[采用决定与后续计划](../../../docs/investigation/review-response-20261024.md)及[断网复现回执](../../../docs/operations/investigation-review-validation-20261024.json)：I1可选正文整视图失败、I2视图7882B/完整messages14194B>12288B均复现；执行器提前阻断，fake预留/模型调用0。I1/I2采纳修复、I3限定细化、I4采用程序固定查询与按需Deep分别验收。先profile合同→局部正文降级→完整请求预算，再独立v2接缝及有限告警同版交付；M5保留原接缝/真正分支价值验证，后续手动Case及按需领域/自动政策。未实施修复或新入口，services/tools/旧测试未改，无真实模型/业务写湖/生产/部署，不合main。历史结果/unknown及迁移归档保持。

**2026-10-24数据与调查重新独立设计评审：** 用户要求不受先前结论影响、不改代码。基于main a82346dd重新核需求、设计和源码，见[详细评审及双方意见](../../../docs/operations/independent-design-review-20261024.md)。总体方向合理；数据线应先审定可见证据与标签的关系、补配对评价，非法输出MCC虚高经纯内存反例重现；调查线发现可选正文异常阻断整视图、完整messages预算与视图预算不一致，版本分歧粒度及模型增量价值另列建议。未将待实现入口/Case等判成设计缺陷，未改代码/测试/配置/原设计，评审未调用模型、访问业务服务、写湖或部署；用户随后要求提交并推送本次评审与两处引用，其他未提交材料保持。

**2026-10-24数据/调查已合并并统一审计：** main5c1202b5包含数据评估cec5ea98和调查469e9467，双方源码/测试保持、旧入口不变；见[总审计与数据湖协作](../../../docs/operations/data-investigation-integration-audit-20261024.md)。数据96/39通过；新调查Agents85/API8通过；合并工具112通过但同一IPv6文本测试3子项失败，不能报全绿。另有Python3.11 Path.is_junction兼容、原MCC/批次冻结及分诊截断待处理。现有网络fixture与单批写湖工具共享，调查继续scope/查询/证据采用/额度，数据线承接准备/期望/评分；M5.2及v4分层/新入口未完成。仅合并与审计，无新模型/业务写湖/生产或部署，20/暂停规划未提交内容保持。

**2026-10-24远程同步与旧工作树清理完成：** 正常项目根目录E:/aisoc/socai2当前为codex/investigation-working；共享代码/文档已推送，远端曾核到32d00ca与本地一致。旧.local/worktrees/investigation-working已用Git安全移除；382份验证原件和171份冻结原件迁至根.local/verification与.local/versions，逐文件hash保持，5个可再生缓存删除。Windows本机适配只在被忽略.local/windows-local，原Windows分支94bb52f保留且未推送。其他机器从[调查协作入口](../../../docs/investigation/README.md)读取设计/进展/问题，后续正常合并main/其他分支；本轮无功能、模型/业务测试或部署。此记录随后随正常提交同步，最新提交以分支log为准。

**2026-10-24正常目录与跨机器协作（最新）：** 调查分支已回到普通项目根目录E:/aisoc/socai2；Windows适配复制到被忽略的.local/windows-local，Windows分支原提交保留。代码/设计/进度/已知问题/公开回执纳入Git并按用户要求推送调查分支供团队拉取评审，从[统一入口](../../../docs/investigation/README.md)阅读；后续正常合并main/其他目标分支，不在.local下开发活动分支。旧工作树在确认远程后清理，私密原始材料保留本机且不作为阅读前提。当前仅整理交接，无功能实施/业务模型测试/部署。

**2026-10-24调查严格版本隔离：** 用户明确两个互不影响的版本线；新实现移至Agents/API各自app/investigation_v2包，撤出旧API注册并恢复旧测试，已跟踪旧services文件无差异。先API新8/旧51通过，再迁Agents并85项直接合同通过；新v2 HTTP入口仍未接入，不冒称历史真实回执验证新路径。旧版/Windows/生产不改，调查本地提交已授权，暂不push/部署。见主设计1.10与实施记录顶部。

**2026-10-24调查Git保存授权与核对：** 用户明确调查设计、功能、测试及非私密回执须统一在`codex/investigation-working`本地提交；此前不提交要求针对Windows本机工作，不覆盖调查。当前保存D1—M4限定成果、M5.1及M5.2未完成增量、v4/13项对照。提交前只补查模型合同15项与问题Deep纯合同9项，均exit0；M5.2专用步骤/循环仍未完成，历史冻结回执不改。不推送/部署，不修改Windows分支，原5/15保持。

**2026-10-24开源到当前的调查改动对照（仅说明）：** 主设计新增第16节，按固定上游34ca18→当前实际→v4目标列13环节，补流程、具体行为/原因/状态证据和两实例；不把原有Deep/Router/CH/账本算新增。独立事实审阅限定ACCEPT/0必须修，静态校核通过；13主题交互对照已核，完整业务分层仍未实施。见[主稿第16节](../../../docs/architecture/investigation-planning-design.md)。本轮无业务代码/模型测试/部署/提交/push，进度停点及5/15保持。

**2026-10-24调查v4分层设计（当前，仅文档）：** 告警分诊/侦察与Case整体调查共用内核，保留20自动处理过程和无Case Run详情；Case新Run继承已核材料，创建/关联与启动独立，领域按需，成员覆盖不再默认最近3条。见[主设计v4](../../../docs/architecture/investigation-planning-design.md)第1及12.7节。实际D1—M4限定通过、M5.1纯合同9项通过；M5.2仅observer增量未测，后续实施先等待本轮方案讨论。未改业务代码/测试、调用模型、访问服务器、部署/提交/push。累计开发tokens不限、单调查有限，OS后置，原5/15及旧失败保持。

**调查M4当前结果：** 2026-10-24 M4限定通过：选定8例原文/采用/可读均通过，23484tokens；其中两例冲突按完整消息/9源码/调用AST等价复用。02开发18回复52185tokens，5个失败原件保持、无unknown/unsettled、费用unpriced。15项直接测试通过，未参与实现者audit_contracts限定ACCEPT/0必须修。仅network_observation.v1/Q1,Q2,Q5，非完整恶意/授权卡或全调查通过。PG临时角色NOLOGIN并撤权；M5待按小步实施，OS后置、无部署/提交/push，原5/15保持。 见[实施记录](../../../docs/operations/unified-investigation-implementation.md)和[机器回执](../../../docs/operations/unified-investigation-m4-20261024.json)。

**2026-10-23调查M4.5预期已固定（历史）：** 用户明确开发调试测试累计tokens不限，持续修复复测无需逐批预算确认；单次调查仍有限额，前批pending8/30000已被新授权覆盖。拟逐个复测原8个语义组合，每个独立test Run沿M3 20000tokens/180秒，请求45秒/2048/retry0，驱动无累计token硬上限；未知不自动重放，失败先定位修复/直接测试，再新版本新trial留证，不清旧Run。原文/采用/可读三层分别达标才过M4，未过不进M5。当前仅文档预期，尚无M4.5实测；见[实施卡](../../../docs/operations/unified-investigation-implementation.md)。原7回复/15042tokens失败、第8未测、19文件冻结及旧unknown保持；生产额度不改，OS后置、无部署/提交/push，5/15保持。

**2026-10-23调查M3限定完成（前批停止位置）：** 先12项纯状态通过，再4项真实PG通过，最后9项gate及1次真实HTTP通过；1匹配、3事件/6工件独立读回hash/UTF-8/关联正确，实际模型0。两处审阅问题先修后测，最终独审限定ACCEPT、0剩余必须修项，见[主回执](../../../docs/operations/unified-investigation-implementation.md)及[M3摘要](../../../docs/operations/unified-investigation-m3-20261023.json)。Run总量在原子snapshot分列opening triage/stage/unknown/unpriced，不回写旧计费/状态；测试Run running不代表最终调查完成。临时API已停，PG测试角色NOLOGIN并撤权，CH reader保留。当批M4、调度、M7 manifest、M8入口/读取projection与OS后置，无部署/提交/push，原5/15与旧失败保持。

**2026-10-23调查数据、M1与首M2工具已通过（前批停止位置）：** 用户确认CH先、OS IOC后，先D1/D2/D3通过，再M1范围、M2查询，五块各8直接共40项＋旧51兼容通过；真实3湖事件/1告警/2消息精确关联，再5次HTTP查询/4认证反例通过。M2逐条身份/原文hash/微秒半开窗口与真实来源一致，M1/M2独审限定ACCEPT0。临时API已停，writer INSERT撤回、reader保留；新账号仅表级权限，未改共享row policy。当批未发模型或持久Run、未部署/提交推送，M3以后及OS未启动；后续以顶部M3记录为准。见[逐步记录](../../../docs/operations/unified-investigation-implementation.md)。独立调查树、原5/15与旧失败保持。

**2026-10-23统一调查M0来源盘点与工具数据规划（前一阶段）：** 用户已授权逐块实施、逐块测试，又要求工具影响设计先讨论。[逐步记录](../../../docs/operations/unified-investigation-implementation.md)已固定M0/M1预期；真实只读核15字段和旧合成事件1行，缺外联目标，不能代替新场景。main已fetch到`7ea813a`，仅文档更新；现测试工具仍只有告警/结果链，没有CH历史记录或OS夹具写入。建议复用CH事件链补同批告警/来源UUID/绝对窗口，首工具逐条可追溯查询，OS IOC另步按需，详见[规划](../../../docs/architecture/investigation-tool-data-plan.md)。当时M0未放行，M1及后续代码未写；探针权限/别名错误已记录并修正，旧工具失败未追认修复。原5/15、旧质量/unknown保持，当时无业务写入/模型/部署/提交推送。

**2026-10-23调查方案重新审计及v3修订（仅文档）：** 在独立`codex/investigation-working`工作树、main基线`3fa4be3`修订[唯一设计主文档](../../../docs/architecture/investigation-planning-design.md)：行为性质与授权分开、控制指令与来源正文分开、结论覆盖与关联补查分开，允许小模型按问题组分析及必要综合；明确调查阶段共享额度/Run总成本、热读冷读与通知同版，以及有用判断/安全交付两门和成本记录。第12.6节首场景策略卡仍为候选、来源未核，未启动M0实施、业务/模型测试、生产或部署；Windows工作保留原目录，无提交推送，原5/15及旧失败保持。文档复核与静态结果见原change audit/execution，不代表业务验收。

**2026-10-24数据评估审计与合并授权：** 用户要求保存[分支审计](../../../docs/operations/data-evaluation-audit-20261024.md)并合main。实跑96测试/39子项通过；复现非法分类MCC=1.0与完整配对未锁定，E1关键输入截断仍待讨论。按阶段成果保存，不声称修复或真实模型/查询质量通过；不发模型、访问生产、写库或部署/push。实际本地Git合并另记回执，20展示与暂停规划工作保持。

**2026-10-23数据与评估E0本地完成：** 在`codex/data-evaluation`隔离工作区接上72条/36对四分类语料答案隔离、原评分器离线复用及原工具轨迹核对，见[设计](../../../docs/operations/data-evaluation-design-20261023.md)和[回执](../../../docs/operations/data-evaluation-execution-20261023.md)。79测试/39子项通过；费用unknown问题独审发现并补测修复，限定ACCEPT、0剩余必须修项。旧10模型提议/8执行（6不可用2错误），8份返回均见后续请求记录；不证明成功查询或语义采用。E1—E4未执行，登录合同改动先讨论；生成证据在已忽略.local，0新模型/业务查询/业务改码/部署/提交/push，主工作区未覆盖，原5/15保持。

**2026-10-24本地提交授权：** 用户要求将已完成的迁移收尾做一轮Git commit，随后继续规划设计。提交范围为前轮已审文档/OpenSpec归档及本条授权说明；先复查静态校核与暂存差异，不push、不改业务/运行、不重复独立调查及入湖测试。用户追加呈现相关工作交对应后端模块，本会话不规划或实施列表/筛选/统计/取数对接；实际commit以Git历史/当轮回执为准，下文“未提交”为收尾时快照。

**2026-10-24迁移基线收尾：** 用户取消本会话的测试背景事件入湖/调查联测，说明已由独立调查开发承接；本批不重复、不复验或追认其完成。已收拢[交付范围、原15项核销、版本与后续规划](../../../docs/operations/migration-closeout-20261024.md)：已有Kafka→Fusion→自动关闭/实际调查→持久结果/Markdown、人工路径、full支撑、测试工具及数据库文档按现有证据交付；partial、质量/预算/unknown失败保持。线上v1 API5a1e1fd8/Agents49643b84与本地小修分列，未新查生产。后续先讨论后端查询/列表接入，再按需求选择支撑数据、协作响应和评估/运行专项；不自动实施。migration_closeout_audit结束独审限定ACCEPT/0必须修后已归档`2026-10-24-restore-alert-investigation-integrity`，同步17条主规格；封后独立窄复核限定ACCEPT/0必须修，17条正文/适用版本、15/15限定核销、R02 0/17与原件、33份MD/1028链接及strict均通过；实际见收尾回执和归档audit。无业务改码、新测试/模型/消息/生产访问/写库/部署/Git提交推送。

以下为各日期原始阶段记录；其中5/15、worker OFF、候选未发布或“当前未完成”等只描述当时，不能覆盖10月24日收尾及10月22日v1发布事实。

**2026-10-23数据库字典与页面建议拆分完成：** 按用户要求保留两份主文档：[当前数据库设计与字段字典](../../../docs/integration/v1/table-fields.md)完整解释25表428列（含类型/空值/默认/取值约束/关联/源码依据）；[页面功能与展示要素建议](../../../docs/integration/v1/page-elements.md)直接给出四页90项建议，已去掉原系统对比。SQL/HTTP和独有样例信息合入[取数附件](../../../docs/integration/v1/page-data-mapping.md)。3份旧混合/重复文档已删除，不留跳转占位，引用统一；原实测JSON/审计证据保持。核25表428列顺序、277链接、90名称与七图一致，diff检查通过；完成度枚举纠正为completed/partial。结束独审限定ACCEPT、0交付阻塞，独立核101条约束及完整物理元数据一致。只做文档和静态核查，未新访问生产/调用模型/改表/业务改码/部署或执行Git提交推送。

**2026-10-23告警/调查功能与数据完整审计：** 已形成[审计附件](../../../docs/integration/v1/ui-functional-data-audit.md)与[90项机器矩阵](../../../docs/integration/v1/ui-functional-data-audit.json)，逐项对照原页面依据/必要新增、数据库与JSON路径、实际子项和开放条件。数据46实值/8派生/10空态/21混合/3缺合同/2仅本地；产品O36/N45/H7/X2。16:42 PG只读核六表167列、两例21事件/21工件/3成本行，10GET200但search缺陷仍在；21正文hash/字节与事件关联通过。主文档、图05/07及索引已修组合空值/采用数/工具耗时/报告空态；七图仅功能对照、截图取消。两路结束独审限定ACCEPT、0本批必须修，164链接/51源行/90字段名静态一致；未新发告警/模型、改业务码/表结构、部署或Git提交推送，原5/15及旧质量/预算/unknown保持。

**2026-10-23功能示意使用口径（最新）：** 用户取消网页截图及截图对照；此前未生成网页截图或对照附件，不继续Playwright采集。七份[功能要素示意](../../../docs/integration/v1/ui-wireframes/README.md)均在文首和Mermaid图内标注：只用于说明展示要素及字段对照，不是UI/交互设计稿，后续模块不得按图确定布局、组件、样式或交互。90字段及主文档保持，文字/编号/链接核对通过，本次未重新截图或渲染。

**2026-10-23页面示意附件：** 按用户要求将四个页面拆为[七份独立Mermaid页面示意](../../../docs/integration/v1/ui-wireframes/README.md)，覆盖告警列表/详情、调查列表及详情四页签；填入既有两例实值，90字段逐项与主文档对应，主文档正文保持不变。仅补索引及文档，未运行业务、访问生产、新发模型或部署；字段/链接核对和七图渲染通过，独审限定ACCEPT、0必须修项。

**2026-10-23测试数据工具迁移已实测：** 按用户授权完成场景选择、source-v1 Kafka wire/发送、真实Fusion探针、持久结果观察与本地两例原worker联测，见[逐步回执](../../../docs/operations/testdata-migration-execution-20261023.md)。44直接测试/39子项通过；新3条接线3Alert/6消息/0模型；另2例自动BTP关闭和NR调查partial，6回复26492tokens、29工件及MD可读。测试标记影响推理、21796/20000软预算停止及running/partial展示差异保留待讨论，无本批调查业务改动或新部署。临时进程/隧道停、2新key停用、预算2 responded；Git忽略已核并补可选输出目录，源码/测试/上游可提交。原5/15不变，不自动提交或push。

**2026-10-23调查规划主文档与换账号续接（仅文档）：** 已将完整统一设计整理为[调查模块规划设计文档](../../../docs/architecture/investigation-planning-design.md)，保留四块合同、逐步输入输出、旧模块融合及案例，汇总官方参考与采用边界。新增`codex/investigation-working`专用分支要求和M0—M9模块验收：先明确概念/功能/预期，再逐块实现、测试、留回执，通过后继续；不得等整流程写完再测。第14节包含新账号读取顺序、未提交基线注意事项和可直接发送的续接指令；旧dated正文改为跳转，其他设计入口已对齐。当前仍main，未启动统一设计实施、业务/模型测试、生产访问、部署或提交推送；原5/15与旧失败保持。

**2026-10-23统一调查四块设计（仅方案）：** 按用户允许融合现有编排的最新要求，形成[具体设计](../../../docs/architecture/investigation-planning-design.md)：问题、证据、分析判断、执行状态的字段/所有权，S0—S10输入输出，主分析/Deep/领域能力协作及现有模块复用调整。补清问题验收、整体评估采用、待复核传播、Run级序号/预算、新格式开始标记和同版manifest。独立设计审阅修订后ACCEPT、0剩余必须修项；只做文档静态校核，未改业务代码/配置、调用模型/业务测试/生产或部署，未提交推送。原5/15和旧失败保持，下一步仍为方案讨论。

**2026-10-23页面与数据库统一交接：** 用户要求先交接库表供自行查询、保留HTTP，并只保留最新文档。已合并为[唯一交接主文档](../../../docs/integration/v1/page-elements.md)：四页90项展示信息、21 PG aisoc/public六核心表、字段/JSON映射、关联及SQL、HTTP说明和实测边界。结构按用户要求调整为页面/功能/字段→数据库表→功能取数与六例→已有HTTP→补充说明。删除本轮两份dated旧稿及旧文档快照包，索引统一；实值JSON/SQL及原始测试证据保留。此前41 GET/21工件/8本地用例复用，本次仅核38列及两例8路径，无新生产查询/模型/改表/部署/提交推送；原5/15与旧失败保持。 增量独审限定ACCEPT、0必须修项；不再另存旧文档副本。

**2026-10-23测试数据迁移重新规划（仅方案）：** 已找回原会话、OpenSpec设计和attempt02完成点，形成[修订计划](../../../docs/operations/testdata-migration-plan-20261023.md)。复用已迁原件/旧有效测试，计划补正式Kafka wire与有界发送、结果观察、2例自动分诊/调查，逐项改测后再推进；明确场景/实体/时间与可查数据的区别、Replay/Quality/Purple/Honey用途。尚未实施或发起新增业务/模型测试，无生产访问/部署，原调查小修保持，5/15不变。

**2026-10-23调查小修本地完成：** 按用户逐步测试及缩小范围要求，已修人工前置校验/采用、逐工具留存/结构状态、停止交接，见[回执](../../../docs/operations/investigation-result-handoff-20261023.md)。独立PG串联44 passed、runner/报告18 passed，人工及工具直接用例逐步留证；当前模型2回复2714tokens，交付采用通过，原文遵循缺陷及先2次503未知用量保留。方案已提交5e0ce171，实施增量未部署/推送；后续设计等待讨论，原5/15不改。结束独审限定ACCEPT、0本批必须修项；本地版本与证据已保留。

**2026-10-23调查优化开始按批推进：** 用户已授权先提交后实施，明确小模型稳定输出为约束。方案新增阶段职责、有界输入、程序管理结构及事件后续路线；首批沿restore完成结果一致与停止交接的设计、本地直接校验和结束独审。当前仅准备实施基线，尚未新增业务修正/验证或发布；原5/15及旧失败保持。

**2026-10-23事件级及跨事件分析研究（仅方案）：** 用户要求参考主流安全产品评估必要性。已核本地入口/分组/图上下文与Microsoft Defender XDR、Sentinel、Security Copilot、CrowdStrike Falcon、SentinelOne官方资料，见[研究](../../../docs/architecture/incident-analysis-product-comparison-20261023.md)。当前有Case多告警和跨Incident候选检索，缺持续事件整体研判；建议事件结果→增量更新→候选关联验证，自动合并/Campaign后置。明确微软Incident cases Preview、Endpoint AIR 2026-09变化及Falcon共享上下文调查Pre-beta。统一证据材料供主分析，补查/领域分析可组合；仅保存文档，不据此启动实施、业务测试/模型/生产访问/部署，原5/15及旧失败保持。

**2026-10-23调查优化方案已修订保存（未实施）：** 根据用户“不是执行，是方案保存”，将本轮审核意见融入[原方案](../../../docs/architecture/investigation-product-engineering-roadmap-20261022.md)。首批聚焦结果一致、停止交接和已有C2取舍；第二批校正查询语义并依真实字段选择一个场景；第三批推广共享结构与扩展能力。补参数来源、API实际时间窗口、认证事件类别/结果缺口、人工校验顺序、逐次工具留存、Router未知结论及汇合、有限验收材料。仅保存文档，不启动方案实施或新业务测试/模型/部署；原5/15、v1运行及历史失败保持。

**2026-10-22两个暂停项目恢复：** 用户要求继续并逐步记录；测试工具attempt02三条新输入真实入口/Kafka/Fusion/PG通过，3Alert/new/无Case、6消息、关联Run0/模型0，隔离topic/Redis前缀，本地进程已停。原8离线＋2替身结果复用，attempt01及一次source_event_ids观察假设失败保留；产品建议已补v1已上线和两例数据事实，未实施未选定方案。见[逐步记录](../../../docs/operations/two-projects-resume-20261022.md)、[工具回执](../../../docs/operations/testdata-tools-20261022.md)。resumed_projects_end_audit结束独审限定ACCEPT、0本轮必须修项，选定版本与逐步记录已留存；原5/15/旧unknown预算/质量失败保持；无业务源码/部署配置修改、Git提交推送，生产v1维持原授权状态。

**2026-10-22 v1两例落库及后端数据盘点：** 用户授权正式服务跑1—2例后，已通过raw Kafka新增2条合成告警：例1自动BTP0.95关闭（3事件/7工件/2033tokens），例2自动NR0.85升级调查（18事件/14工件/29755tokens，graph partial）。21工件正文的UTF-8字节/hash均通过，21份event关联完整；成本3行共8回复31788tokens，全部unpriced。22:56真实PG补查生产tenant总计3Alert/3Run/36事件/35工件（含旧发布canary），选定25表428字段/实际约束已留存；23:09实际只读执行后端SQL9个SELECT通过。见[后端盘点](../../../docs/integration/v1/page-data-mapping.md)、[两例回执](../../../docs/operations/service-v1-functional-20261022.md)。graph_step仅node/无输入输出hash，工具200字符preview、prompt副本截断、seq并非严格写入游标已明示；不能宣称所有步骤原文完整或质量通过。原5/15、旧unknown/预算保持，无新部署/业务改码，v1_two_examples_audit限定ACCEPT、0本轮收口阻塞；资料包 `.local/releases/stingaisoc-backend-integration-v1.0.0-data-inventory-20261022.zip`（94331字节/26项）已生成，124链接/3锚点/7JSON、diff/OpenSpec strict通过，旧包保留。

**2026-10-22 v1.0.0服务已发布：** 用户授权开启自动分诊/调查、沿用模型并新建独立生产租户。21 API5a1e1fd8/Agents49643b84已定向部署并healthy/ready，fused常驻订阅已附着；模型摘要一致，其他13个选定容器元数据保持。生产tenant `f6a5c700-69b8-44fc-8238-609362fb1a9f`，新组 `socai2-agents-v1-prod-20261022` 起点30/32/39。单条新raw Kafka合成告警自动分诊及调查，15事件/14工件/MD读取200、新组追平end；7次回复28216tokens，graph partial/六轮及软预算超限，内容质量未验收。新租户仅1条responded/settled预留，无本批unknown；旧租户/group/unknown/预算、原5/15保持。读[生产接入](../../../docs/integration/v1/production.md)、[发布回执](../../../docs/operations/service-v1-release-20261022.md)及[JSON](../../../docs/handoff/service-v1-release-20261022.json)。未提交/推送Git，未启真实厂商动作。service_v1_release_audit结束独审限定ACCEPT、0本轮阻塞；97链接/2锚点/3段shell语法/6JSON、Raw/Fused及身份、diff/OpenSpec strict通过。服务配套文档包 `.local/releases/stingaisoc-backend-integration-v1.0.0-service-20261022.zip` 已生成，不含秘密。

**2026-10-22后端对接指引v1：** 已按用户“正式Kafka、HTTP告警仅测试”的口径整理[发布文档入口](../../../docs/integration/v1/README.md)，包含各存储连接/库表/认证配置、raw/fused/DLQ合同、告警及调查每一步输入输出、结论/工件/Markdown读取、核心关系与只读SQL。21先SSH超时，恢复后16:02已核远端15容器的生效镜像/端口/配置白名单；补实湖/TI OpenSearch/Redis DB12共享、实际worker关闭及升级0。Agents enrichment仍禁用目标，未将容器healthy当调用接通；未发业务探活。未改业务源码/数据库/运行配置或调用模型/发消息/部署，原5/15、worker OFF、候选未部署及旧失败保持；Raw/Fused模型及身份、4份JSON/86链接/1锚点/2段shell语法、diff/strict通过；backend_v1_doc_audit结束独审及新增配置窄复核限定ACCEPT。文档阅读包保存`.local/releases/stingaisoc-backend-integration-v1-20261022.zip`，包内manifest列文件/hash，不含秘密或业务源码。

**2026-10-22两会话收尾留存：** 按用户要求只做简单收尾，已整理[两个会话的完成项、停点和续接入口](../../../docs/handoff/session-closeout-20261022.md)，并选择性保存相关工具/测试/方案及非私有回执到`.local/versions/session-closeout-20261022/`。测试数据已有8项离线＋2项替身合同通过，真实attempt01在联网前配置失败，修正后未重跑，真实联测和增量结束独审待续。产品工程方案237行最终版本的原独审已完成，现找回限定ACCEPT/0阻塞并补audit；方案未进入实施。未续跑业务测试/模型、部署、启worker或Git提交，原5/15与旧失败保持。

**2026-10-22智能调查产品与工程建议：** 已形成[急需问题、优化设计与扩展路线](../../../docs/architecture/investigation-product-engineering-roadmap-20261022.md)。优先范围/真实资料、证据与结论/报告一致性、停止后的可接手结果；保留三编排，共享四个小合同，沿现有工具/策略按场景扩展，含代码落点、业务例子、分批交付和指标。只是设计建议，不把后续产品化列为当前迁移前置；现有候选已构建但不含旧C2全部修正、未部署，原5/15和旧质量失败保持。本轮未改业务源码/运行或新增模型/业务测试。

**2026-10-22标书需求与迁移评估：** 已核AI SOC2原件hash、正文/表格与三图，形成[详细评估和推进建议](../../../docs/operations/tender-requirements-assessment-20261022.md)及[35子组164条逐项矩阵](../../../docs/requirements/socai2-requirements-matrix-20261022.md)，未继承旧SOCAI完成状态。主链/Markdown基本接通不等于标书完整满足；关键差距为真实数据/调查范围、证据与时序、行为路径、完整RAG及人员/响应闭环；SFT、架构选型与六项成效单列。收尾已纳入本地两候选镜像完成的新回执，下一迁移责任为阶段发布准备与交付，不再要求重复构建。告警筛选和UEBA50条限制仅静态登记；本轮无业务代码/模型/消息/Docker/部署变更，原5/15及旧失败保持。164条原文/569链接/strict/diff核验通过，tender_document_final_audit结束独审限定ACCEPT、0文档阻塞；具体见原change审计，不代表产品验收。

**2026-10-22本地候选镜像及离线核验：** 用户明确授权完整父镜像导出后，已本地构建API5a1e1fd8/Agents49643b84；[实际回执](../../../docs/operations/investigation-candidate-images-20261022.md)记录固定父ID/19清单、层/配置继承，镜像内19hash/编译、7排除项、API385/Agents129导入及4方法通过。两次非root/只读/禁网探针exit0并删除，candidate_images_end_audit结束独审限定ACCEPT、0项本轮阻塞；不重复前批100项。helper修可选字段/显式本地BuildKit/context，三次构建停止及初拒绝后授权保留。OrbStack恢复11既有本地容器；未部署21或启其worker/发模型，5/15、旧质量及unknown保护保持。

**2026-10-22候选组合与构建准备：** [本批回执](../../../docs/operations/investigation-candidate-build-20261022.md)补核21父镜像ID与已发布full bundle/UEBA保持，19文件隔离组合100 passed（Agents55/API45）、router登记通过；API7/Agents12最小context与Docker配方准备完成，candidate_preparation_audit结束独审限定ACCEPT、0项本轮阻塞。7项后置保持父版本，Deep只追加摘要。当前本地Docker未运行，未构建镜像或发布，0新模型/业务写/常驻启用；原5/15与旧质量失败保持。前批缺证/未组合验收记录保留为历史。

**2026-10-22阶段收口与具体候选差异：** [清单](../../../docs/operations/investigation-stage-closeout-20261022.md)逐项映射10项未勾责任，整理API7＋Agents12共19运行文件审查副本；Deep从匹配candidate05的原件仅接链图摘要，7项旧C2/文案差异先不选，原工作区保留。新变体用一个已有离线材料交接用例验证，1 passed；19文件语法及来源检查通过，不代表组合/构建/发布验收。基线采用最近full记录，纯full bundle字节/hash本地缺证；stage_closeout_audit结束独审限定ACCEPT、0项本轮阻塞，仅审收口/源码副本。未发布/启worker/调用模型或写业务数据，5/15与旧失败保持。

**2026-10-22关联/链图模块阶段评估：** [评估与推进路线](../../../docs/architecture/attack-chain-path.md#module-assessment)确认已有相关告警检索、关系上下文、Run工件与基本交付，可以沿B5→B6收口；尚非跨Incident活动关联或行为路径引擎。建议先核原任务责任及候选发布差异，旧C2未终审内容不随整文件自动获准发布；再据业务目标选跨事件关联、Case自动化或行为图二开。只是评估与建议，未扩功能/模型/运行/发布；5/15、worker OFF及旧质量失败保持。

**2026-10-22链/图概念讨论已保存：** 用户要求保存辨析、例子及结论，已补[对象/ID与四项能力](../../../docs/architecture/attack-chain-path.md#concepts)、[Incident/Fusion链四种组合](../../../docs/architecture/attack-chain-path.md#membership-examples)、[调查范围](../../../docs/architecture/attack-chain-path.md#investigation-scope)、[Case/Playbook](../../../docs/architecture/attack-chain-path.md#case-automation)、[结论与未决](../../../docs/architecture/attack-chain-path.md#discussion-conclusions)，并连接Fusion清单、导航和AGENTS。Fusion链内部续组/交付/留存已实现，当前未接后续业务消费；调查PG链与Neo4j Path不复用该链，图关系不是行为因果。只保存当前事实和规则推演，不新增业务实现、自动建Case或验收结论；449个本地链接/新锚点及diff检查通过，concept_docs_final_audit结束独审限定ACCEPT、0文档阻塞。原5/15、worker OFF及旧质量失败保持。

**2026-10-22 Kafka写图真实联合已通过：** 已补齐的Conda环境、本地原Kafka消费者及API连接21 PG/Neo4j，独立topic/group一条消息在分诊入口前prepare成功，当前Alert直接邻域5节点4关系、来源一致；reader写403/读200，原GET另返14可达候选而非确认影响。观察入口主动hold，未提交offset、未建Case/Run或执行模型，临时进程已停；不重跑Fusion或部署/启常驻。累计夹具2条（旧失败1＋成功1），旧失败保持。见[真实联合回执](../../../docs/operations/kafka-graph-joint-20261022.md)，joint_graph_audit结束独审限定ACCEPT、0接线阻塞，5/15保持。

**2026-10-22先补齐本地依赖：** 用户在联合观察前要求全面检查，按API+Agents的56项运行/开发直接声明及必需extras统一解析安装；修缺包/低版本、补Conda动态库，清新环境中克隆的旧项目editable冲突，处理SQLAlchemy追踪插件的本地兼容范围。记录见[依赖回执](../../../docs/operations/local-dependencies-20261022.md)，最终65项离线核验、85项直接合同及pip check通过，未参与实现者dependency_final_audit结束独审限定ACCEPT、0剩余阻塞。未改业务源码、pyproject/lock或21部署；此前Kafka联合attempt2因缺greenlet停止，仅留一条合成PG记录、未发布消息，不改写成通过。

**2026-10-22 Kafka消费入口写图本地接通：** 按用户选择，在Agents读取合法fused Kafka消息后、分诊之前统一prepare；Fusion源码保持，后续Graph/Deep上下文纯GET。独立writer、tenant/canonical ID、review-only/shadow及原提交/预算保护保留；API显式Alert只投当前告警并补真实Case边，修正Case前50截断漏投。用户要求的Conda项目环境已建于`.local/conda-envs/socai2`，85项直接合同通过（新入口24＋既有Agents47＋API14），源码/测试/环境版本保存在本地；[用法与回执](../../../docs/operations/kafka-graph-intake-20261022.md)。本批是替身接缝验证，0新模型/真实broker/业务图写/部署，不将旧真实Case证据移作新入口实证；未参与实现者kafka_graph_audit结束独审限定ACCEPT、0剩余阻塞，16份版本核验及strict/diff通过。原5/15、常驻worker OFF及旧失败保持。

**2026-10-22阶段交接与链图保版：** 沿B5→B6汇总[功能/版本交接](../../../docs/operations/investigation-stage-handoff-20261022.md)及[机器摘要](../../../docs/handoff/investigation-stage-handoff-20261022.json)，分列已部署、本地已验与未终审差异；纠正AGENTS/总计划/导航的过时“链图仅规划”。已补`.local/versions/attack-chain-path-20261022/`的36份选定源码/测试/依赖/回执及manifest/归档，副本与归档字节一致；依赖Git基线，不是独立安装包或已审发布包。已有自动关闭/自动调查/人工与Markdown证据复用，本轮0新业务源码/测试/HTTP/模型/消息/部署，不实施假设厂商Tool。完整change5/15、常驻worker OFF、旧质量失败保持；36文件保版、文档/规格检查通过，未参与编写者stage_handoff_audit阶段独审限定ACCEPT、0剩余阻塞，不代替整体结束验收。

**2026-10-21链/图本地实施完成，暂不发布：** 保原链算法及四Agent/Router/Graph流程，补可信PG→Neo4j投影、Case/Alert查询、模型摘要与三类Run工件。新Case四次真实模型输入均含链图，Neo4j11节点15边，29事件/4工件/Markdown读回200，18388tokens；首轮3.5秒截止导致context不可用的13941tokens结果保原，修后用全新输入，本批共8回复32329tokens。API109通过/7既有livePG跳过，Agents兼容120＋2新用例通过、最终22合同复核（重叠不累加）。详见[本批回执](../../../docs/operations/attack-chain-path-local-20261021.md)及[模块用法](../../../docs/architecture/attack-chain-path.md)。未参与实现者deep_functional_tests结束独审限定ACCEPT、0阻塞；5/15保持，不归档、不部署/启worker/Git提交。

# 当前进度


**2026-10-21外部HTTP接口/Tool验证设计完成（未实施）：** 用户明确重点是厂商已有HTTP数据接口，以及自己设计Tool怎样接入、如何证明正确执行。[设计与样例](../../../docs/architecture/third-party-search-contract.md)沿内部统一查询→原厂GET/POST适配→标准行→ToolMessage，按实际厂商能力映射条件/认证/时间/字段，不要求厂商改API。区分现有SIEM工具复用与新独立Tool，给出手工HTTP、直接Tool、脚本模型交接及按需真实选择四层验证；HTTP200或模型自称查询不作执行证明。6个JSON/12处文件引用、时间示例和OpenSpec strict/diff检查通过，未参与编写者结束独审ACCEPT。只交付设计，0源码/配置/功能测试/HTTP/模型/部署；5/15、worker OFF及旧证据保持。

**2026-10-21Tool使用文档完成，结束独审ACCEPT：** 已补[执行/配置/最少测试指南](../../../docs/operations/investigation-tools.md)、[精确工具目录](../../../docs/architecture/investigation-tool-catalog.md)及[第三方SIEM接入示例](../../../docs/operations/siem-tool-integration.md)。按用户假设场景说明配置位置和适配边界，拆解Elastic/Sentinel的typed参数→统一条件→ES|QL/KQL→HTTP→结果投影；自研检索可直接转JSON，不要求SQL或采集。当前独立connectors服务未迁入，配置发现不证明可查；Sentinel认证/工作区/字段接缝仅静态说明。12个JSON/5段shell语法和92处本地文件引用通过，OpenSpec strict及diff检查通过。仅文档，无新业务测试/模型/HTTP/运行/部署，旧失败、worker OFF及5/15保持，不归档、不Git提交。

更新：2026-10-22。

**攻击链/图接入实施开始（本地，不发布）：** 用户授权按计划实施并用一个新完整告警案例交接逐步输入/输出/读取。保持原算法/三种编排，补定向可信投影、Case/Alert查询、Bundle/模型消费及Run工件；本地接21基础设施，现常驻/正式topic/旧Run保持。只做最少功能与身份测试、一个代表模型案例，复杂可用性后置；当前尚未验证完成，不提前勾完整任务。

**攻击链/图接入规划（未实施）：** 用户要求先规划，已核原查询/图写函数都在，但固定原版和当前Case/告警业务均未自动投影，且Router/Deep未完整消费链/路径，不能称只差开关。[具体计划](../../../docs/operations/attack-chain-path-integration-plan.md)按真实Case/tenant→调查准备阶段定向写图→原链/图查询→实际模型摘要→Run工件/Markdown推进，沿B5/现有OpenSpec，不改算法/合并编排/自动建Case。当前只读与文档，0新业务代码/模型/测试/图写/部署，5/15不变；规划独审ACCEPT、strict/链接/格式检查通过。

**调查功能本地实测已完成一批（2026-10-21，结束独审ACCEPT）：** [逐步案例回执](../../../docs/operations/investigation-functional-20261021.md)记录四个新本地Run、三种路径：78项直接测试通过；14次模型调用尝试/13次可见回复，已知31,995 tokens，Forensic一次无回复/执行与usage未知。Router选Identity/Cloud并交付模板MD；默认四节点交付带Forensic兜底MD；Deep执行7工具后因21,540/20,000停止、无最终narrative。两处原版合同（认证SQL IPv6空值、单项IOC字段）已最小本地修正，各有真实只读查询/服务验证，未部署。UEBA失效连接、Forensic连接错误、空结果/预算/报告质量及缺源后置登记；不重调旧Run、不启常驻，不追认完整调查/质量通过。本地13文件增量快照已保存于`.local/versions/investigation-functional-20261021/`，不含凭据。沿现有OpenSpec2.1/3.1/3.3/3.4/4.1部分成果，原5/15不变、不归档。


**调查功能实测开始：** 用户授权本地运行原四节点/Router/Deep，案例来源均可。现有Router12项、Deep8项通过但模型/部分服务为替身；20仅有已调查Golden样例，不重调。接下来采用公开事件派生的新隔离输入，连接21模型与只读工具，逐步记录实际输入/输出及Markdown；不部署、不启常驻、不改旧Run或复杂可用性专项。具体范围见现有OpenSpec执行记录，未提前勾完成。

**预处理、模型输入输出与工具调用已细拆：** 新增[专篇](../../../docs/architecture/investigation-preprocessing-tools.md)，逐调用列目的/实际输入/输出及采用，覆盖Router首次分诊和四领域、默认四节点及Deep每轮；给出schema、规范化tool_calls、HTTP/认证、ToolResult/ToolMessage示例及静态时序。明确Router无工具循环、Case嵌套alerts不flatten、模型不读取完整state/数据库，通用registry未做完整schema校验；更正认证查询默认168小时与shared schema24差异，旧源码/结果保持。本次0业务源码/配置/功能测试/模型/线上查询/部署，沿原2.1/4.1文档交接，任务状态不变。

**Router及调查方式讨论已同步：** [调查说明](../../../docs/architecture/investigation.md#5-router及full-graph的差异)补开关二选一、准确流程和与原四节点逐环节比较；专业分支各一次领域分析，响应摘要/模板Markdown不等价于完整Forensic/响应计划。与Kafka graph/deep独立、外层固定/内部动态查询，以及“较新能力不代表官方已淘汰旧链”同步到[设计评价](../../../docs/architecture/investigation-design-review.md)、模块计划及OpenSpec记录。本次仅文档，0业务源码/配置/功能测试/模型/部署，原产品完成状态不变。

**调查设计对比已补：** 按用户最新重点，[设计评价](../../../docs/architecture/investigation-design-review.md)比较默认Case四节点与graph/deep的目的、输入/输出、四Agent逐一价值/限制和官方历史依据。固定上游ROADMAP/Case文档/CHANGELOG及模块说明更支持演进并存，不能证明必须同时运行的严格互补双架构；graph本身也能人工启动。结合人工R01/自动C2说明结构化报告和多轮工具都不保证事实质量，不用不同样例tokens做性能排名。当前只读分析，未选择裁剪/合并或新发模型，既有运行及任务状态保持。

**下一模块规划及调查逐调用说明：** Fusion之后进入Agents分诊，已形成[分诊工作卡](../../../docs/architecture/triage.md)，按支持/默认/当前配置、输入实际采用、规则与模型、关闭/升级、输出审计及C1/C2对比交接。按用户补充，[调查说明](../../../docs/architecture/investigation.md)分别展开自动graph、默认人工四Agent、Router/full入口、deep每轮模型/工具参数/来源/采用/终止和审计；原C2还原为首次分诊＋6轮同一deep Agent、4次lake失败及2次知识/提取成功，旧partial/质量失败保持。记录route_to字段消费、单项IOC增强合同和Router bundle/持久边界，尚未修或新实测。当前只读分析/文档，0新业务代码/测试/模型/线上操作/发布，原15任务和5/15保持；下一步先讨论分诊取舍，再按直接差异本地验证、保留版本并阶段发布。

**Fusion阶段总结：可以继续分诊模块。** 已完成职责/输入输出/默认规则说明，复用B1身份与交付、2A独立告警关联、2B风险和2C历史IOC证据，UEBA实际异常→真实Kafka/Redis→Fusion→PG/消息5例本地联合通过。当前无阻断已有告警主链交接的已知Fusion接线问题；外部增强缺源、候选链/算法取舍、仅声明配置及复杂可用性登记后置，不追认全质量或整体change完成。[阶段小结](../../../docs/architecture/fusion.md#六当前阶段小结可以转入下游分诊)、[更新路线](../../../docs/operations/completion-plan.md)。下一模块先看Agents分诊输入/上下文、规则/模型、关闭/升级及审计交接；本次无新业务代码、模型、运行或测试，不发布21，现有本地版本/旧质量失败保持。

**UEBA/Fusion本地真实联合验证已通过：** 按用户最新要求本地运行原源码、借21 PG/Redis/Kafka，运行1c84658ebb88。三个新实体各用原BaselineService准备30样本，原Kafka消费者实际生成medium/high/critical（3.4903/4.5227/6.4891），经真实异常消息→Redis缓存→5条真实告警保存/发布。无信号0.656/0.15；三档分别0.726/0.45、0.796/0.75、0.856/1；OFF控制回基准。真实PG severity=high/status=new及priority1/risk0.5保持。5专用topic/3新group、3基线最终count31、3异常/5告警，无正式topic/旧unknown/模型，两个本地进程已停止。[对照说明](../../../docs/architecture/ueba.md#5-本地真实联合验证异常带来了什么改变)、[真实回执](../../../docs/handoff/ueba-fusion-joint-20261021.json)。本地验证后保留版本，按阶段统一发布；本批未部署21、未改常驻开关。原18项内存边界证明继续保留，不改写旧证据或勾整体change完成。

本批结束独审ACCEPT；本地验证版本保存在`.local/versions/ueba-fusion-20261021-1c84658ebb88/`，含代码快照、测试环境版本及manifest。仅本地保留，不自动Git提交/推送或部署。

**UEBA→Fusion联动例子完成：** 按用户授权，原FusionWorker异常分支→cache→原完整告警评分/交付处理的8例与原10项信号测试共18 passed；基础confidence0.656时medium/high/critical分别0.726/0.796/0.856，anomaly0.45/0.75/1，priority保持1。关闭/无信号/另一tenant或实体不加分，多实体只取最高等级。PG/Redis/Kafka为B1内存替身，不宣称真实broker、成熟异常生成或常驻启用通过；21开关仍false，0正式消息/PG写/模型/部署。[配置及结果](../../../docs/architecture/ueba.md#4-ueba与fusion联动评分开关及实测例子)、[回执](../../../docs/handoff/ueba-fusion-examples-20261021.json)。源码上传21方案被自动审批拒绝未执行，转本地临时venv；首次夹具导入错误已修，业务源码/原测试保持。沿restore 2.1/4.1记录，不勾完整产品任务、不提交。

**raw规范化事件支路暂缓（最新）：** 用户明确交其他模块处理；当前回到已有告警输入后的Fusion功能分析，不展开事件生产/规范化、入湖、检测/提升或派生会话/AI资产。`RawAlert`/`alerts.raw`及告警原正文仍属当前输入，调查读取外部历史事件与UEBA结果继续保留。[范围](../../../docs/operations/alert-processing-scope.md)、[模块计划](../../../docs/operations/module-review-plan.md)及[Fusion说明](../../../docs/architecture/fusion.md)已同步；已有源码/配置/实测保持，本次仅文档澄清，0业务代码/运行变更/新功能测试，不新增或勾选产品任务。

**Fusion进入功能理解阶段：** 按用户最新要求，先解释原模块做哪些事，再共同讨论要/不要哪些功能。[功能说明](../../../docs/architecture/fusion.md)已区分已有告警主链、normalized事件支路、辅助接口，并给出去重/关联/候选链/Case及多类评分的区别和一条告警实例。本轮只读整理，尚未做功能取舍或确定修复/启用项，0业务代码/运行变更/新测试，不以源码存在宣称全功能已启用；B1/full证据复用，change完整任务不勾选。

**依赖项用法交接继续推进：** [简明使用说明](../../../docs/operations/dependency-usage.md)补齐TI/IOC精确查询、PG租户列表、信誉增强和不调用模型的KB检索，UEBA直接复用现有说明及full证据，不改实现或重跑测试。本轮只读确认20原项目PG文档KB表存在但为空，ATT&CK/TI/语义记忆集合存在；未把集合存在当内容/21导入通过，未扩数据规模、导入或历史经验。原TI OS搜索无tenant过滤的边界已记录，当前仅作共享公开情报入口，租户私有IOC用原PG路径。0新模型/业务写/部署，不勾完整change未完项。

**UEBA首项触发合同已梳理：** 用户确认按原码由上游选择投喂，当前不新增实体名单或滚动窗口。[模块说明](../../../docs/architecture/ueba.md)已给出当前共享topic的normalized JSON、预提取兼容JSON及HTTP评分请求，明确实体优先级、数值特征、基线更新和异常输出，以及Kafka event_id/HTTP source_event_id差异。2个文档Kafka样例用原extract直接核对通过、3 JSON语法正确，复用原122+7及full基线/Agents证据，不重跑测试套件或复杂可用性专项；0新HTTP/消息/PG/模型/部署。UEBA→Fusion真实异常加分仍未证，本增量不写通过。继续沿restore 2.1/4.1部分推进，不勾完整change未完任务、不自动提交。

**二开路线已重排（最新，仅规划）：** 用户明确先规划/记录，再按UEBA → 威胁情报/IOC → 20上一版既有知识库 → Fusion → 分诊 → 调查/攻击路径 → Markdown交付推进。[总计划](../../../docs/operations/completion-plan.md)已记录整条顺序，[模块说明](../../../docs/operations/module-review-plan.md)保存共享能力基础属性表和本次讨论纪要：UEBA重点实体启用、基线时间/样本配置、输入输出及偏离机制；IOC数据量/覆盖率暂缓；知识库复用既有资料，历史经验后看。原码UEBA没有按实体名单启用配置，30天参数仅初始化时间标签、不是淘汰过期样本的滚动窗口，作为首模块待讨论项记录；20实际资料/索引待只读确认。本轮未修业务代码、运行配置或做测试/模型/部署，不勾新产品完成项；主链已通与标书完整满足仍分别判定。

**报告交付最新口径：** 用户确认当前只需Markdown能生成、持久保存并按Case/Run读取；PDF暂缓，HTML额外交付也不作本轮前置。复用已有Markdown主链证据，不重跑报告模型或增加格式专项；已有PDF源码/依赖/历史结果保留。

**full配套按原码迁移（当前）：** 用户明确历史补查、Attack Path、UEBA、事件检索、IOC增强及OpenSearch需要，复用21依赖，保证原功能基本可运行。新增原版101服务文件+图schema资源，按现有OpenSpec做必要认证/字段/配置接线。原Fusion→ClickHouse→lake SQL/调查补查已实证：同一合成事件A1行/B0行；原APOC依赖补齐后AttackPath200（PG2节点/1关系回退），首两503/跨租户404保持。UEBA原122项+7项直接测试通过，原迁移head0004、原HTTP及Kafka基线与常驻Agents实际读取通过，只有1样本不作画像/异常质量通过；enrichment已健康/HTTP200但无provider，不将零分解释安全。OpenSearch原Store合成IOC写1/搜1/精确匹配1及TI原HTTP200通过；TI airgap/Feed0、Qdrant浏览200空集合，API原代理200/source=qdrant/degraded=false已接通；基本实测及未参与实现者唯一结束独审accept，无本批新增功能阻塞，具体以[本批回执](../../../docs/operations/full-support-migration.md)为准。0新模型/厂商调用，未启全局worker或真实响应，整体迁移未完成；下列只读分析为较早状态。


**20页面/full需求只读对照：** 已按六张Case截图核固定源码、20已有Case/Run和当前部署；旧Run结构GET404而账本/MD保持，新Run三块结构GET200，原版冷恢复/页面接缝与full无关。截图告警精确对应golden pipeline合成输入。full六个可选组件、Attack Path/Chain差异及Tasks/Notes/Resolution等缺口已写[功能对照](../../../docs/operations/alert-function-alignment.md#20的case页面与full需求2026-10-21只读分析)。本次未新增模型、测试、运行代码/配置或部署，未扩大迁移职责；是否选实体图/事件湖及完整工作台留讨论。

**最新口径／第一步主链已走通：** 当前只要求正式告警输入→Fusion/持久化/分诊→自动实际执行调查→已配置工具/知识调用→基本结果/报告/关联持久记录可取得。[已有B4 case02](../../../docs/operations/integrity-autonomy-r01.md)已满足该接通口径：source4e169979→Alert17254632→Run e3d019ae，实际执行graph/deep、六工具及MITRE查询，MD/HTML与11项工件经原API取得；不需人工再点调查。复用该证据，不补其他入口或重跑模型。该次partial/质量失败仍原样保留，第一步接通不等于完整质量、常驻准入或整体迁移完成；常驻worker仍OFF。

**执行已收敛：** 算法/模型、报告、deep截断/用量及恢复问题迁移后评估，不再以修完或质量复验为第一步前置。停止重复组合测试、全量hash/水位/表计数/冻结、逐入口模型矩阵、多轮审计及自造控制脚本；复杂可用/冗余专项后置。已有代码修复不回退：graph最后一轮在指示到达前已发出，实录157项通过（4.02秒）；关闭文案39项及旧153/155等记录保留，最新源码未完成最终独审、未部署、不作真实质量通过。运行仍candidate05，八临时key已撤，旧十reader/服务身份/unknown/积压保护保持。下列较早“继续修复/质量硬门”等仅保留过程事实，当前以本条和AGENTS顶部口径为准。

**当前运行更新（优先于下列过程快照）：** candidate03组合358项Agents+25项API=383项通过并独审，B4/B5结果/用量/交付、报告及技能pin修复和原生PDF依赖已部署；新人工Run四模型10167 tokens，25事件/一MD，MD/HTML/PDF200。报告仍有意图、范围及时间表述超证据的问题，不作完整质量通过。旧Run保持并冷回查，原PDF缺库现可读取。candidate04仅改一处KB引用格式解析（32项直接测试）并配置原七权限只读服务身份，已定向更新API1be/Agentsc311健康，部署后独审及六项HTTP通过；[原28+integrity共29层](../../../deploy/aisoc21/README.md)，workerOFF；[引用/工具身份回执](../../../docs/operations/integrity-citations-tools.md)。candidate05默认两个报告节点假设/范围/处理时间投影24项直接测试及独审通过，已定向替换Agents为4ccf3a6d（全部env/7RO/60秒保持），0新模型/消息/业务写，部署后773来源/运行配置独审通过；C2图/deep修复未部署。新C六短期key当时创建、五来源及拒绝边界11项HTTP通过，C第一条经原worker实测BTP0.95/原0.85阈值自动关闭、APInew→resolved且最终PG关闭时间非空，1真实回复2174tokens；分类/理由/关闭独审通过，C2已自动调用调查/六个工具，7回复22568 tokens；首分诊NR保留且告警未关闭，但deep六步截断、graph20451超过20000边界，报告把MITRE映射和风险prior当攻击/确认事实，完整验收失败并停止后续输入。两例合计8回复24742 tokens，保留原失败、不重调；最小源码修复进行中，八枚本批短期key已停用/逐枚401；旧十reader/永久只读身份/三unknown/积压保持。

**B1限定完成、B2/B3候选已部署：** [Fusion入口回执](../../../docs/operations/integrity-b1.md)：119项直接测试、10次真实HTTP，两条新source-v1输入走通HTTP→Kafka及Kafka→HTTP，首次结果不变，跨tenant403/无效凭据401；Fusion一次更新至c52b9aac，源码/部署/结束独审通过，restore任务2.4完成，当前5/15。B2权限84、上下文44及B3组合94已做直接验证/独审；I2初轮隔离PG79漏普通SQL状态断言，后由PG错误日志发现死CASE问题，撤销其作为充分验收的结论，原结果与错误保留。修正后candidate02去重组合232项Agents+25项API=257项通过，独审核状态/iterations/error实际写入；API已定向部署至1be37c38、Agents至9f74c4a8，Fusion c52保持，worker OFF。真实人工调查、知识采用及报告验收尚待，不计作整链完成；下方前期规划与“未实施”说明保留为当时阶段记录，不覆盖本条。

**首轮人工实测与后续：** [B2/B3回执](../../../docs/operations/integrity-b2b3.md)：新Case/Run四模型8062 tokens、25事件/一MD工件、KB确切块进入四prompt但0引用，七拒读404；技术材料/租户/usage成立，报告因测试输入污染、失败增强误当证据及截断而质量未过，PDF缺原生库500。原Run保留不重调。当前B4源码151项、B5最终78项、报告修复56项直接验证及各自独审通过，组合/新业务尚待；PDF依赖候选仅隔离渲染通过，未运行发布。B1两操作key已撤401，后续两操作key及旧十reader保持，workerOFF。

**工作目的明确：** ①迁移告警及后续处理流程，确保功能/结果符合预期；②过程中理解源码并对照固定版本官方文档，识别已实现、未接通和声明未实现的功能；③形成架构/功能/扩展点梳理便于二开。官方对照及架构产物随实际批次更新，不扩大为全平台重构或无边界缺陷修复。

**开始实施：** 用户已授权按总计划执行并允许并行worker。当前并行处理B1融合入口合同、B2默认调查身份和上下文，root统筹直接测试、运行接线与跨批组合；每批由未参与实现者独审。实施状态以本条及后续回执为准，下文“仅规划”保留历史；当前尚未新增完成任务或启用自治。

**自动调查讨论勘误：** 用户询问的是原有代码设计，上一轮误记为新增规则触发需求，已撤回新增合同/优先级/专项验证要求。原版已有playbook事件/severity/tags触发及investigate步骤，另有worker分诊未关闭后升级；按原设计保留，不新增一套规则机制。仅文档纠正，无产品、部署、模型或消息操作，worker仍OFF，restore任务仍4/15。

**后续总规划：** [主执行表](../../../docs/operations/completion-plan.md)已按B1告警、B2默认人工调查、B3知识、B4自动分诊/关闭/自动调查、B5其他调查/交付、B6整体验收组织，并映射现有六阶段及restore任务；文档严格校验与未参与实现者独审通过。自动升级后实际自动取证/分析和交付结果，无需人工再点；第一实施项B1，B2独立部分可并行准备。本轮仅文档规划，无产品或运行变更，原4/15及11项未实施不变。

**最新范围/当前下一项：** 用户确认完整告警/调查及自动关闭、自动升级；playbook/反馈一体保留不额外改测，可用性专项后置。[完整性评估与修复规划](../../../openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/assessment.md)已严格校验及独审通过：1578原件无缺失，当前功能存在临时限制及阶段/usage、跨入口、上下文组合缺口；4项评估任务完成、11项修复/交付任务未完成，未改运行。旧R02[暂缓](../../../openspec/changes/admit-review-only-triage-worker/status.md)、0/17及五文件/hash保持，不作为功能前置。下文旧“下一R02”保留历史，不变更运行OFF或旧质量失败事实。

**目标：完整迁移告警及调查服务端功能，保证功能完整、结果正确。** 包含告警处理、自动分诊/关闭/升级、人工调查、工具/知识消费和报告交付。所有一体模块可原样整体迁入，不额外修改或测试；playbook/反馈专项、冗余设计及服务可用性相关测试/修复登记后置。验证仅补当前功能变化所需部分，前端/采集/原始检测/独立展示推送不在本轮职责。

## 已完成

- 2026-10-21再次同步目标与原则：优先完整迁移告警/调查并保证结果正确；所有一体模块可原样整体迁入，不额外修改或测试；冗余设计和服务可用性相关测试/修复登记后置。已收敛当前修复计划，I2正常graph用量问题与特殊故障恢复接续分开，未增加通用阶段/恢复框架；纯文档严格校验与独审通过，无运行变更或业务/可用性测试。

- 2026-10-21按用户要求接入[OpenSpec实施规范](../../../openspec/README.md)：项目配置、变更流程及入口已建立，严格校验与未参与实现者结束审计通过；C03-R02已建[待执行change](../../../openspec/changes/admit-review-only-triage-worker/proposal.md)，17项任务全部未勾选。只接入实施规范，不改变运行源码、部署、旧回执或完成状态；不导入旧SOCAI任务。

- 项目入口、[范围](../../../docs/operations/alert-processing-scope.md)、[六阶段路线](../../../docs/operations/service-roadmap.md)及[批次计划](../../../docs/operations/dependency-migration-plan.md)已按同一目标对齐；旧规划与过程记录保留为历史。
- 1A依赖参考快照：90个原件完成本地来源/Git blob/hash/权限核对，13个Python服务main/all版本导出，上游导出自测26项通过。快照包含范围外文件，不是全部安装清单。
- 20/21只读盘点：20基础Compose/官方应用revision/overlay对应；21共30容器（22运行、8退出）、18卷，与旧服务关闭回执比较无变化。证据见[初始化回执](../../../docs/operations/initialization.md)。
- 需求原件、既有分析、20适配、来源清单及受控配置位置已保留。私有凭据仅在Git忽略目录，不写入公开文档。
- 迁移规划已细化：第一阶段按1B→1C→1F→1D→1E→1G执行，每批含源码落点、输入/验收/恢复；后续2A—4D及冻结交付也已分批。计划来源清单含2个initdb脚本、134份SQL、所选Python服务上下文和直接测试候选；其中1B的137个原件已迁入，SQL已实执行；API/Fusion已执行1F；Agents/Actions已执行1G，其余按需适配仍为规划。新增静态阻塞见[已知问题](../../../docs/operations/known-issues.md)。
- 1B已复用21共享PG16.15/Redis7.4.11：新建aisoc库/两角色，134份SQL全部执行成功；绑定tenant读写、越权写/DDL拒绝通过。Redis专用账号/逻辑库与ACL持久化完成，单服务重建后账号和测试key恢复，原镜像/卷保留；其余29容器元数据未变。详见[1B回执](../../../docs/operations/1b-shared-services.md)。
- 1C已复用21 Kafka7.5.0 KRaft：项目raw/fused/Agents DLQ topic已准备；原锁aiokafka0.10.0经独立容器验证消息offset/hash、手动提交及单broker重启后的续读/新写/全量回放。53个旧用户topic起止offset不变，仅清理本批smoke topic/group。详见[1C回执](../../../docs/operations/1c-shared-kafka.md)。

- 1F已迁入API/Fusion共987个原版输入/测试（含已有134 SQL），3个原文件作最小接入/启动适配；Python3.11.17源码镜像已部署到21 loopback18000/18003。真实HTTP→项目Kafka SSL→Fusion→PG TLS→API主链、权限/跨租户拒绝、重投和坏schema持久DLQ取证完成；70项相关测试通过。见[1F回执](../../../docs/operations/1f-alert-chain.md)。

- 1D已复用21 Qdrant1.7.0，实际进程nofile65536；21独立Ollama0.40.6/qwen3-embedding:0.6b已启动，16核CPU/32GiB内存。真实3条1024维向量写读/查询及Qdrant重建恢复通过，测试集合已清理；其余31已有容器与18卷名保持。见[1D回执](../../../docs/operations/1d-vector-embedding.md)。

- 1E已在21部署固定LiteLLM1.106.0独立网关（loopback14000）：五角色分别真实调用43并通过JSON结构校验，共463输入/153输出/616 tokens，费用unknown。其余33已有容器与18卷名保持；错误key原版返回400的限制及首次探针失败保留。见[1E回执](../../../docs/operations/1e-model-gateway.md)。

- 1G已迁入Agents/Actions共591原件，6个最小差异及8个新增服务文件；21源码镜像、人工HTTP→四模型节点→18事件/报告→重启后API回查已验，Actions仅dry-run，123项直接测试通过。发现并修复同响应usage重复累计和错误工具结果被记成功；修复Run实际/账本均5718 tokens、unpriced4，首次错误Run原样保留。34个已有容器/18卷保持，测试key已停用。见[1G回执](../../../docs/operations/1g-service-baseline.md)。
- 知识复用已只读核429文件/约5GB、29份原始来源摘要及402,744行结构记录；本地4B模型摘要已核（声明2560维），允许20/21分担模型负载。已形成[复用计划](../../../docs/operations/knowledge-data-reuse-plan.md)，尚未导入、比较检索或切换模型。

- 2A已完成8次原版投递核对，复现不同发生被折叠及缓存丢失重投虚增关联数。后者仅改1个原文件修复，25项测试及独立实体3次投递复验通过；原5条PG材料保持，只重建Fusion，其余35容器/18卷保持，测试key已停用。当时发生记录合同仍待明确；后续完成见下一条，原始结果见[回执](../../../docs/operations/2a-dedup-correlation.md)。

- 2A-01已按独立上游告警合同实施source-v1，保留旧Kafka及可匹配旧HTTP身份。7个源码/测试文件差异、无DDL，95项相关测试及12条broker输入/41项HTTP检查通过；新增7行分别保留材料与持久关联，重启后可查，旧12行不可变材料不变。仅API/Fusion更新，其余34容器/18卷保持，3测试key停用，Kafka lag0。**2A限定验收通过**，见[回执](../../../docs/operations/2a-source-identity.md)。

- 2B-01已复现并修复RBA缓存失效重投重复加分：真实链修复前30→近60分/计数1→2，修复后独立样例始终30分/1次。40项相关测试、真实Redis32次同告警/64条不同告警并发及超50条展示上限重投通过。只更新/重启Fusion，19条旧材料、其他35容器/18卷、134迁移保持，2测试key停用，模型调用不增。Fusion ML状态接口仍因租户认证未配置返回503，处理规则在当时未验（后续见2B-02），见[风险回执](../../../docs/operations/2b-risk-idempotence.md)。

- 2B-02已完成稳定规则内容指纹/实际采用状态、保存失败缓存污染修复；83项相关测试通过。真实API→PG→生产applier/worker抑制方法验证v1/v2、30秒缓存、恢复、租户/权限与依赖失败，25项HTTP检查通过；只更新/重启API/Agents，22条旧材料/其他34容器/18卷/134迁移保持，3key停用，模型调用不增。自动worker仍关闭、抑制摘要尚无持久ledger，见[规则回执](../../../docs/operations/2b-policy-versions.md)。

- 2C-01已接Fusion本地IOC查询及冻结结果：复用旧SOCAI一条有来源/日期的历史指标，真实6投递/5新行验证命中、无匹配、tenant、过期/停用及重投，21项HTTP检查、62项测试通过。历史参考弱证据不增权；独立SDK故障/恢复与整服务故障分开。仅更新/重启API/Fusion，25旧材料/其他34容器/18卷/134迁移保持，2key及2标记IOC停用。见[IOC回执](../../../docs/operations/2c-ioc-consumption.md)。

- 2C-02已新增认证只读processing-context接口：合成材料在现有PG表中，资产/权限/开放漏洞实际算706，改A材料后当前视图435，另一tenant280，原告警medium/priority50不改。显式关联、无匹配、已修复/未来排除、真实PG SAVEPOINT故障恢复及API重启回查通过，30项测试/38项HTTP检查；只更新API，30旧材料/其他35容器/18卷/134迁移保持，3key停用。不是实际CMDB/HR/扫描器同步或普通日志消费，见[回执](../../../docs/operations/2c-processing-context.md)。

- 2C-03已只读核21/20事件与UEBA来源：21 ClickHouse无业务表、旧UEBA六表精确0行；20 UEBA为空，事件topic仅一条未定性消息且无可用ClickHouse。50项原工具合同测试、12项HTTP检查/3项停用复核及3次生产Agents方法调用完成，缺源明确available=false；生产Agents还缺API凭据。未变服务/配置/旧36告警/134迁移，3key停用；首次快照断言失败保留，单独复核一致。真实事件/UEBA消费仍未通过，见[回执](../../../docs/operations/2c-event-ueba-sources.md)。

- 3A-01已补规则抑制持久回执与DLQ/提交保护：现有账本保存policy_decision，原告警不改、不生成模型verdict；83项相关测试、真实PG事务失败/恢复及SSL Kafka实际worker验证offset1→1→2→3、恢复不重发/确认DLQ后提交。只更新/重启Agents，旧36告警/2Run/36事件、其他35容器/18卷/134迁移保持，3key停用；3份新回执含1份probe-only恢复记录，常驻worker仍关闭，见[回执](../../../docs/operations/3a-policy-suppression.md)。

- 3A-02已完成有界真实模型/消息/账本/API验证：首轮标签污染导致材料不足被判FP，原Run保留；另3条盲测依次TP/BTP/needs_review，独立模型失败回退needs_review。6次成功回复usage/Run/成本行均7406 tokens、unpriced6，费用unknown；46项原测试/66项HTTP检查通过。显式group起点0、最终4/3及同group重启无新调用；未改运行源码/镜像/常驻配置或重启服务，旧38告警/5Run/39事件等材料、36容器/18卷/134迁移保持，3key停用。缺失risk_score被显示0.0、五类context401及技术引用错配尚未修复，完整质量未过，见[回执](../../../docs/operations/3a-model-triage.md)。

- 3A-03已修复缺失风险分被当零分：实际ingress/Kafka/Fusion/PG/API及worker/prompt中缺失/null保持未知、0和0.8原值保留，四条独立告警关联同一事件。184项相关测试/33项HTTP检查、一次真实模型needs_review及1345 tokens账本核对、三服务重启回查通过；旧45告警及既有账本、其他33容器/18卷/134迁移保持，3key停用。未重做数值评分，五类context401及完整质量仍未过，见[回执](../../../docs/operations/3a-risk-score.md)。

- 3A-04已接每租户组织记忆读取与明确失败状态：194项测试/46项显式HTTP检查，真实PG/API有效/过期/缓存/认证失败及恢复通过；一次真实模型消费A语句仍needs_review，1523 tokens与账本一致。新读取回执/工件同事务，真实PG工件故障回滚及同Run恢复通过（独立probe-only Run）；API/Agents重启后回查及常驻身份读取通过。旧49告警/既有账本、其他34容器/18卷/134迁移保持；3操作key停用，2枚A/B只读reader key保留30天。其他四类context401及完整质量未过，见[回执](../../../docs/operations/3a-org-memory.md)。

- 3A-05技能读取认证/选择来源及事务工件已限定验收：347项测试（API142、Agents205）、48项最终HTTP检查；一次真实Fusion→worker→43模型采用skill-a-rule@v2，needs_review/自报0.95，1572/105/1677 tokens与账本一致、费用unknown。事后合成头v3与原v2工件分离，真实PG故障/同Run恢复及API/Agents重启回查通过；旧50告警/既有账本、其他34容器/18卷/134迁移保持。3操作key停用，2枚独立settings:read reader保留30天，原组织记忆身份保持；失败尝试保留，见[回执](../../../docs/operations/3a-tenant-skill.md)。4条failed/probe-only FK占位不作真实编写/回测/激活成绩。

- 3A-06 KB认证读取、保守cutoff、确切采用文本/引用及事务工件已限定验收：236项测试（API38、Agents198），真实API/PG全文检索、租户与scope拒绝、缓存失败/恢复及重启回查通过。一次真实模型prompt含KB1，返回needs_review/自报0.95，1955/140/2095 tokens与账本一致、费用unknown；实际prompt7861字符、未截断，但模型未引用KB标记，引用质量未过。8717/8105两次模型前预算预检失败保留，仅压缩本批合成资料及等义inline note后从检查点恢复，没有重发告警或追加模型。旧51告警/既有账本、其他34容器/18卷/134迁移保持；新增1告警、1真实模型Run与1独立probe-only Run、6条合成KB行。3操作key停用，2枚knowledge_base:read reader保留30天，原组织记忆/技能4key保持；见[回执](../../../docs/operations/3a-kb-read.md)。

- 3A-07近期分析员处置认证读取/采用来源及事务工件已限定验收：最终396项测试（API91、Agents305）、60项显式HTTP检查，真实API/PG规则优先与tenant隔离、created cutoff、缓存撤销/失败恢复及重启回查通过。一次真实模型prompt7355字符含三条个人意见，needs_review/自报0.65，1779/130/1909 tokens与账本一致、费用unknown；未精确提及note或反馈ID，不能证明因果采用或质量。初394项通过后独立读取发现导入环，补两项新进程测试、仅额外重建Agents，后半只读恢复未重启或重发输入/模型；最终镜像读取通过，模型未重测。旧52告警/19Run/63事件/31工件、其他34容器/18卷/134迁移保持；新增1告警、2Run（含probe-only）、7工件及5条合成反馈。3操作key停用，两枚新alerts:read reader保留30天，原六枚reader保持，见[回执](../../../docs/operations/3a-dispositions.md)。

- 3A-08身份读取已限定验收：496项（API108/Agents388）、62项HTTP；27合成节点/22关系、严格tenant/cutoff及真实图源503/查询恢复、PG工件故障/重启回查通过。一次模型身份1进入6931字符prompt，needs_review/自报0.65、1646/135/1781 tokens，费用unknown，不证明引用/质量。初次脚本TEXT参数错型在输入/模型前停止，仅修脚本并从已完成矩阵后恢复，原失败保留。旧53告警/21Run/66事件/38工件/17成本行及其他34容器/18卷/134迁移保持；原八枚reader保持，新增两枚graph:read保留30天，三操作key停用。见[回执](../../../docs/operations/3a-identity-read.md)。

- 3A-09已完成三例真实分诊及51项显式HTTP回查：TP/BTP/needs_review，5223 tokens/费用unknown；分类3/3，但p01时间窗及授权过断言保留，不能算完整质量通过。真实broker7投递/8交付、6次方法/失败替身且无额外模型，复现坏schema/ledger False静默提交、冷重投模型方法重入及暖恢复来源丢失，worker准入不通过。旧54告警/23Run/69事件/46工件/18成本行保持，该批后57/28/77/77/21；36容器/18卷/134迁移不变，无运行修改/重启。3操作key401，10reader保持；初次broker导入及finish断言失败/受控恢复保留，见[回执](../../../docs/operations/3a-triage-admission.md)。

- 3A-10-01普通分诊持久确认与坏消息已限定验收（143项测试、26项显式HTTP、0真实模型），见[回执](../../../docs/operations/3a-triage-durability.md)。两文件修复使live持久失败及已解码坏schema不再静默提交；真实broker7次发布/8次交付、4次模型方法替身，正常五类来源工件及Agents重启回查保持。旧57告警/28Run/77事件/77工件/21成本行保留，该批后58/29/78/82/21；仅Agents更新，35其他容器/18卷/134迁移保持，三操作key401、十枚reader保持。该批当时冷重投/缓存来源/SDK预算未修，后续见下条。

- 3A-10-02普通分诊首次结果/重投保护已限定验收（207项测试、55项显式HTTP、0真实模型），见[回执](../../../docs/operations/3a-triage-recovery.md)。三条真实HTTP/Fusion信封经新独立broker对象验证同worker完整保存恢复、fresh进程复用、跨进程单次认领及退出后unknown；3次发布/7次交付/3次方法替身。当前61告警/32Run/83事件/92工件/21成本行，两新Run完成、一条仅保留开始意图；旧14表材料、35其他容器/18卷/134迁移及十枚reader凭据保持，三操作key401。保护仅Kafka普通live路径，direct triage/replay及原抑制分支不扩张；负cursor真实422、生产SDK预算和完整质量仍未过，下一3A-10-03见[总计划](../../../docs/operations/3a-worker-reliability-plan.md)。

- 3A-10-03-01分诊SDK默认retry0/45秒、整次调用45秒截止及-1增量cursor已限定验收（189项测试、71项显式HTTP、0真实模型），见[回执](../../../docs/operations/3a-triage-request.md)。仅更新并重启API/Agents，旧14表材料、34其他容器/18卷/134迁移及十枚reader保持，三操作key401；无新增告警/Run/事件/工件/成本。跨进程租户额度、积压和停止恢复仍待3A-10-03-02，完整质量与worker准入未过。

- 3A-10-03-02持久分诊额度/积压/停止恢复已限定验收（263项测试、137项显式HTTP、0真实模型），见[回执](../../../docs/operations/3a-triage-budget.md)。新增项目预算表，原134迁移及旧14表材料保持；每次20000预留单位非实际usage，未知占位不自动过期。真实broker6发布/14交付/5次HTTP替身开始，保留三未知预约及一条积压；最终67告警/37Run/92事件/106工件/21成本行，5预约/100000预留单位。仅Agents更新/重启，35其他容器/18卷/十枚reader保持、三操作key401；失败与受控额度调整保留。当前A/B测试policy，完整准入与质量仍未过。

- 3A-11-01只读准入复核已完成，见[回执](../../../docs/operations/3a-admission-review.md)：旧p01时间/授权错误未被indicator gate识别；常驻Agents审批提案guard实际True且缺Kafka bootstrap/TLS，旧调查工具身份仍缺。三未知预约及A积压保持，0模型/消息/offset提交/运行改动；完整准入未过。下一[3A-11-02配置补齐](../../../docs/operations/3a-triage-admission-config-plan.md)，保持worker禁用，然后单独修提示词/复验质量。

- 3A-11-02常驻分诊配置补齐已限定验收，见[回执](../../../docs/operations/3a-triage-admission-config.md)：仅Agents同镜像重建一次，新增四项环境值，复用原只读CA；审批提案guard现False、Kafka SSL/主机名校验及六组offset读取通过。旧14表/三unknown/A积压/十reader/其他35容器/18卷/134迁移保持，0模型/消息/提交。当前22层、19源码层，worker仍OFF；下一[3A-11-03理由提示词修复](../../../docs/operations/3a-triage-reasoning-plan.md)，完整准入/质量未过。

- C01 Fusion持久交付/首次结果恢复已限定验收，见[回执](../../../docs/operations/c01-fusion-delivery.md)：107项测试，真实PG/Redis/SSL Kafka及6项HTTP；17次发送尝试/16次确认、23次物理交付/回读（含独立审计4次），0真实模型。只更新Fusion为delivery-c01，该批当时23层/20源码层；新增5告警/1DLQ，旧14表/35其他容器/18卷/134迁移、十reader、三unknown和原积压保持，2操作key401。探针断言及启动失败、无重发的恢复检查点和计数补充均保留；结束及撤key后独立审计通过，不外推全缓存丢失或整体迁移完成。

- C02分诊正文/发生时间、普通live跨告警缓存与停止清理已限定验收，见[回执](../../../docs/operations/c02-triage-material-cache-stop.md)：118项测试、一次断网生产SDK探针及部署前/后独立审计通过；仅Agents更新为triage-material-c02并设置60秒停止宽限，当前24层/21源码层。0真实模型、0新业务记录/凭据/消息；旧14表、5预约/3unknown、原积压、十reader、35其他容器/18卷/134迁移保持。首轮112通过6失败、误解析与部署挂载顺序断言失败保留；部署只读复核通过，未重复重建。direct/replay旧缓存、实际在途Docker停止和模型质量不外推。

- C03-01分诊时间/授权证据提示词v3及lock已限定验收，见[回执](../../../docs/operations/c03-triage-reasoning.md)：88项测试、一次断网生产SDK探针，完整messages6560字符/6502字节；21其他prompt与schema保持。仅Agents更新一次，60秒停止宽限继承，当前25层/22源码层，0真实模型/新业务写/凭据/消息。旧14表/5预约100000预留单位/3unknown/十reader/六group及35其他容器/18卷/134迁移保持，部署前/后独立审计通过。重复测试入口被独占门拒绝、探针前路径修正均保留，无重复test或失败probe；模型质量及常驻准入待C03-02/03。

- C03-02新理由复验已按质量失败受控停止并通过结束/撤key后独审，见[回执](../../../docs/operations/c03-triage-quality.md)：仅case01一次真实模型/1998 tokens，实际needs_review/0.65未达冻结TP判据，后三例未执行；原schema、材料/PG/API/usage/offset链通过。新增1告警/1Run/3事件/7工件/1成本/1responded预约20000单位及1shadow，0QA；旧五预约/三unknown保留。首次脚本读取权限失败发生在发送前，独审后只改0644并从未发送检查点恢复，原件保留。三操作key401，运行25层/22源码层及其他服务保持、0重启。下一用更明确恶意工件的新四例另冻结，不为旧标签改prompt或重调旧例，常驻仍OFF。

- C03-02B新case01一次真实模型1918 tokens，TP分类正确但无据断言未授权，理由质量未过；后三例未执行，3操作key已停用/401，见[回执](../../../docs/operations/c03-triage-quality-recheck.md)。02B当时v3/039f及25配置/22源码层保持，worker OFF；后续澄清见下条。 新增1告警/1Run/3事件/7工件/1成本/1responded预约20000单位及1shadow、0QA；旧6预约/120000单位/3unknown保持，累计7预约/140000单位。分类与事实支持分别审核，不以技术链通过代替质量。

- [C03-02C-01授权事实边界](../../../docs/operations/c03-triage-authorization.md)v4及lock已限定验收：88项直接测试、4个断网生产SDK完整body（7754–7814字符/7669–7729规范UTF-8字节），0真实模型/业务PG写/新消息。只更新Agents一次至9ba6，env/七只读bind/60秒宽限保持，当前26 Compose/23源码层。旧14表/7预约140000单位/3unknown/十reader及其他35容器/18卷/134迁移保持。验收脚本导入副作用已修，早期104只读SQL/4次metrics误追加的112计数文件保留并归本批，旧844冻结字节保持。模型理由质量和常驻准入仍未过，worker OFF；下一02C-02另冻新四例，不重调旧两例。

- [C03-02C-02新四例复验](../../../docs/operations/c03-triage-authorization-quality.md)已按质量失败受控停止：C03-02C-02三例实际模型共5971 tokens：前两例分类/理由通过，第三例把缺少转移证据误判为FP并推断规则误报，按冻结判据失败停止，第四例未发。三操作key已停用且实际401，技术持久链与结束独审通过；新增3告警/Run、9事件/21工件/3成本/3shadow、3responded预约60000单位，0QA。旧7预约/140000单位/3unknown保持，累计10预约/200000单位；26配置/23源码层保持，0重启。下一C03-02D-01只澄清“无法核查检测条件不等于规则误报”的最小提示词边界，先做0真实模型直接验证和独审；不重调旧三例、不改旧判据。理由/分类质量与常驻准入仍未过，worker OFF，整体迁移未完成。

- [C03-02D-01检测有效性边界](../../../docs/operations/c03-triage-detection-validity.md)v5检测有效性提示词及lock已限定验收：88项直接测试、4次断网生产SDK完整body（7827–7917字符/7742–7832规范UTF-8字节），0真实模型/新业务写。仅Agents一次更新至9cb719，原env/七只读挂载/60秒停止宽限保持，当前27配置/24源码层。旧14表、10预约/200000预留单位/3unknown、十reader、其他35容器/18卷/134迁移保持，部署前/运行/收尾三审通过。首个source stage语法错误在远端Python执行前被拒绝，原失败/恢复及父标签措辞勘误保留；未重复测试、重建或模型调用。下一C03-02D-02另冻四条新对照输入，验证有反证FP、明确授权BTP、缺证NR及事件窗外NR；本四例不复验v5 TP，后续常驻新TP仍须实际独审。旧三批质量失败与七条未发输入保持，worker OFF，质量/常驻及整体迁移未完成。

- [C03-02D-02新对照](../../../docs/operations/c03-triage-validity-quality.md)质量失败后已受控停止并完成结束、撤key后及封后独立审计：两次真实模型回复共4081 tokens；case01 FP分类/理由通过，case02时区换算错误且把窗内已授权活动判为FP，分类/理由失败，case03/04未执行。三操作key已停用并逐枚真实401，十reader及旧10预约/200000单位/3unknown保持。新增2告警/Run、6事件、14工件、2成本/2shadow、2responded预约40000单位，0QA；预约单位不是usage。告警仍new、auto_closed=false，不声称发生错误关闭。当前27配置/24来源层、184Agents/769运行Py及lock保持，0源码/Compose改动、0重启/DDL。首次发送前因本地验收算子遗留旧输入SHA/v4合同被拒绝，0业务/模型；原失败、旧stop与显式恢复审计/独立断网合同probe/新质量stop全部保留，未重复freeze、身份、额度或topic，不重调旧输入。公开交付已完成：28公开文件、远端573索引及769运行Py/lock逐hash一致，交付后独审accepted；不把技术收尾通过写成质量通过。

- [C03-R01](../../../docs/operations/c03-triage-review-only.md)代码隔离与定向部署已限定验收：191项断网测试通过（22项新增、169项既有直接测试），0真实模型/新业务写；仅Agents一次构建、一次替换为19f8f1a5，review_only_v1已配置、worker OFF，七只读挂载/60秒宽限保持。旧14材料表、全部告警字段、12预约/240000预留单位/3unknown、十reader、其他35容器/18卷/134迁移及消息水位保持。首次观察脚本RLS错误与189通过/2夹具失败及恢复均保留。当前28层运行定义、185 Agents/770运行Py，prompt/lock v5不变。下一按[人审准入卡](../../../docs/operations/c03-review-only-profile-plan.md)另冻R02，验两条新A/B输入的有限真实main消费与首次结果恢复；原自治质量失败、C04/C05及后续调查/响应仍待验，整体迁移未完成。

## 尚未完成与限制

- 2026-10-20[已有迁移审核](../../../docs/operations/migration-review-20261020.md)确认来源/部署对应合理，但发现Fusion保存/发布未确认仍提交、source-v1缺行恢复丢关联、分诊正文/时间丢失、校验前缓存及停止异常漏清理。本轮只审核，未修代码或重启；后续R1/R3见C01，R2/R4/R5见C02限定修复。此前“项目topic/group未配置”是误判，1G已设置，DLQ按项目topic派生；未验的是消费起点/逐tenant准入/持续消费。

- 1G已验所列人工入口/API持久结果及dry-run；常驻自动分诊、完整知识消费、完整调查质量、审批/真实响应未验。3A-04—06只验A/B合成组织记忆、技能、PG全文资料读取及各一次真实模型输入；KB1虽已提供但模型未引用，已有向量索引与完整知识/检索/引用质量仍未过。Agents旧只读enrich_ioc仍因增强依赖未接而失败，正确记partial/error；2C-01通过的是Fusion本地IOC路径，不等于该工具已接；报告达token上限，不外推质量，完整服务端基线未冻结。
- 原legacy告警仍保留原归并事实，不重建缺失历史；新source-v1按稳定上游UUID独立保存并关联。旧HTTP桥接仅覆盖已记录UUID且原特征/connector匹配的投递；2B-01补验了所列RBA重投/并发边界；完整缓存丢失、持久风险账本、跨实体事务与旧不可见贡献仍未验。未知schema在tenant/source解析前拒绝，未知identity已验证带tenant/来源的持久DLQ。
- API/Fusion为production配置，无demo/匿名绕过；Kafka新增19093 TLS入口，PG重载启TLS无重启，均验证CA/IP。旧Kafka明文入口保留，broker无客户认证/ACL，单节点不等于生产高可用。
- runtime角色仍保留上游未绑定tenant的worker语义；本批外部HTTP身份与指定告警查询已实测，不外推所有API路由。Redis逻辑库不是ACL隔离。
- 各批操作key已停用；组织记忆与近期处置各两枚alerts:read、技能两枚settings:read与KB两枚knowledge_base:read reader key分别受控、仅映射A/B测试tenant；另有两枚graph:read身份reader，十枚key按用途独立映射，不作万能身份。原四类默认120秒、身份300秒缓存不保证API端即时撤销/编辑/退休；组织记忆/技能逐项检查expires_at，KB时间cutoff不重建被编辑的旧正文，处置created cutoff不重建后来编辑的旧意见；deep investigation原版本pin失败仍可落当前版本，graph关闭、3B前须核。标记数据/失败证据保留。应用只在21 loopback开放，尚非LAN公开API；真实对话模型证据按各批回执区分，未做真实厂商动作。

**旧执行快照（仅保留历史，不覆盖页首新进展）：R01限定验收完成；当时下一C03-R02另冻有限常驻。** [C03-R01](../../../docs/operations/c03-triage-review-only.md)代码隔离与定向部署已限定验收：191项断网测试通过（22项新增、169项既有直接测试），0真实模型/新业务写；仅Agents一次构建、一次替换为19f8f1a5，review_only_v1已配置、worker OFF，七只读挂载/60秒宽限保持。旧14材料表、全部告警字段、12预约/240000预留单位/3unknown、十reader、其他35容器/18卷/134迁移及消息水位保持。首次观察脚本RLS错误与189通过/2夹具失败及恢复均保留。当前28层运行定义、185 Agents/770运行Py，prompt/lock v5不变。下一按[人审准入卡](../../../docs/operations/c03-review-only-profile-plan.md)另冻R02，验两条新A/B输入的有限真实main消费与首次结果恢复；原自治质量失败、C04/C05及后续调查/响应仍待验，整体迁移未完成。 不提交或推送。

历史过程及早期路线调整见[初始化过程归档](../../../docs/handoff/history/2026-10-20-initialization-progress.md)，不作为当前任务表。
