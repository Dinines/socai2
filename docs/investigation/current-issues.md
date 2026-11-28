# 调查流程与交接问题清单

执行优先级、责任及下一步统一见[当前工作清单](../../openspec/changes/complete-socai2-investigation-chain/tasks.md#当前范围与顺序)。本页保留问题及原证据边界；清单整理不将后置、未验或未发布事项改为完成。 调查迁移前须先完成[4173逐页理解、功能与数据/接口规划](../../openspec/changes/complete-socai2-investigation-chain/investigation-test-plan-20261126.md)，Case旧接线、对象/查询缺口及整页视觉差异集中见该文6.1；规划通过不代表业务已验收。

## 告警查询记录：旧对象映射与跳过显示

2026-11-25截图属于原批准组第一条旧告警。统筹复核其当前分诊指针、固定 A、三项步骤和实际接收配置后确认：原 OCSF 在 `$.unmapped.spirithub.legacy.source.ip` 有查询对象字段，旧接收配置仅选择 `src_endpoint.ip`，因此首次保存及 A 冻结对象为空。责任点是我方湖接收投影配置漏选原件实际路径。三项查询以 `no_supported_frozen_objects` 跳过，没有开始记录，返回条数为 null；结束时间只记录收尾，不能作实际耗时或查空证明。[原因独审](../operations/evidence/alert-query-skipped-display-20261125-01/independent-cause-review.json)

本次已获准的 UID 副本使用包含实际路径的当前批配置，保存和冻结了对应对象，三项查询均 completed。该证据适用于具体副本及配置，不代表历史告警已修复或所有来源路径覆盖完整。原母本及旧 Run 不回填、不重跑，已批准原始材料不改。

页面当前只显示“跳过”和“未记录”，已保存原因藏在原错误 JSON。前端按[本步方案](../../openspec/changes/complete-socai2-investigation-chain/alert-chain-acceptance-plan-20261124.md#11月25日截图复核查询跳过原因与耗时)补告警 A 的中文原因、未执行耗时和完整计划参数入口；页面修改及[限定独审](../operations/evidence/alert-query-skipped-display-20261125-01/independent-review.json)已通过：实际8181三行和一个抽屉同轮核对，完整参数、原因和null返回保持；一个用例覆盖跳过及已执行零行／真实耗时两个代表，类型检查通过。冻结 HTTP／数据合同保持，不新建告警、查询或模型调用；本轮不以显示修正追认旧查询成功。

## 告警截图复核：检测字段映射与置信度

2026-11-25，沿 F02-01、F03-01 及[告警原验收表](../../openspec/changes/complete-socai2-investigation-chain/alert-chain-acceptance-plan-20261124.md)定位负责人截图对应的既有 OCSF 告警。只读核原件、同轮原答、PG 和正式调查 HTTP，原值及正文留受控目录。该精确告警的原 OCSF 完整保存；规则名称/标识位于 `finding_info.analytic.name/uid`，源置信度枚举位于 `confidence_id`。

| 问题 | 已确认责任点 | 当前处置 |
| --- | --- | --- |
| 规则原文有值，但规范化检测规则为空 | `lake_alert_receiver.adapt_alert` 未提取源规则，进入 `RawAlert.rule_name/rule_id` 时已为空；材料、PG 与 E28 一致，不是页面漏解析 | **映射候选已修复并独审，8181 已读回旧材料原规则**。接收映射保留两条实际来源路径；页面优先规范化值，缺失时读同版 E31 并标来源。21 独立接收源码现已安装并通过实际入口加载验证；统筹独立核部署指纹，发布后同材料页面读回通过。后续获准单条测试UID副本已从Kafka首次created，规范化规则及来源在PG／E28／E31／8181一致；原材料不回填。 |
| 检测置信度显示未记录 | 当前 `detection.confidence_value` 来源是 Fusion 评分，该条首次保存的评分状态为未启用；源 OCSF 的置信度枚举完整保留，但不是这个数值字段 | **源检测展示已补齐并独审**。同材料源等级、来源整数分数与 Fusion 评分分别展示，0 保留；页头也改正 Fusion 来源标签。加载／失败、版本不符、正文不可用／保留不全和完整原件未提供分开。实际枚举正例已在8181读回，来源实际数值分数正例未验，未改HTTP合同。 |
| AI 分诊置信度显示未记录 | 同轮模型原答显式给空值；解析保留该值，assessment 记录 `not_computed`，E28 返回空值，前端取 `triage.confidence_percent` | **历史分诊未给数值，非清洗、解析或保存丢失**。页面已明确显示未评分，具体原因沿同轮判定理由，未说明则为未记录。新提示明确可合理估计时给数值；只有本轮依据不足／矛盾／明确限制导致不能估计才null，并在既有rationale说明。提示与页面已通过限定独审，21 新调度器现已实际加载新提示并通过正常调度读回；后续真实A只调用1次并完成，实际新提示已使用，但confidence仍为null；原答／解析／PG／HTTP／8181一致。**AI数值正例未取得，null具体理由语义未验**，不把非空rationale当原因通过，不追加采样。 |

告警列表侧栏已只保留 AI 结论；完整详情解释及 AI/人工判定保持。[前端侧栏回执](../operations/evidence/alert-list-preview-verdict-20261125-01/verification.json)、[检测卡回执](../operations/evidence/alert-list-preview-verdict-20261125-01/detection-display-verification.json)。此前回执保持原范围；本轮[规则映射独审](../operations/evidence/alert-rule-source-confidence-20261125-01/independent-receiver-review.json)、[源展示独审](../operations/evidence/alert-rule-source-confidence-20261125-01/independent-source-display-review.json)和[AI空值展示独审](../operations/evidence/alert-rule-source-confidence-20261125-01/independent-ai-display-review.json)分别记录当前结果，不扩大为新首次接收或整个告警模块通过。

[统筹独立复核](../operations/evidence/alert-sidebar-confidence-review-20261125-01/independent-review.json)核 9 项同源检查、3 份最终前端指纹及两步页面回执；实际 PG/E28/E31 为本轮新读回。平台本轮只核转发源码，没有另发带鉴权平台请求；不把代码核对写成平台再次实测。

负责人追问后，调查核心已确认[12 项功能所需字段及必需条件](../../openspec/changes/complete-socai2-investigation-chain/alert-required-fields-review-20261125.md)。常驻 Fusion 实际已启用，本组走独立一次性交付的关闭评分配置；不能归为 Fusion 整体未启动。21 已安装并核可加载的独立启用版，原交付配置、原答和快照保持；后续单条批准副本已取得Fusion首次保存及8181数值正例，旧条未启用仍为历史首存状态。AI 数值链已有，本轮已明确合法空值条件和沿rationale说明原因的口径；没有新增专属原因字段，不能据历史null猜原因，也不能把提示已修改写成新模型真实输出已验。[核心确认](../../openspec/changes/complete-socai2-investigation-chain/alert-confidence-core-20261125.md) · [配置及字段独审](../operations/evidence/alert-confidence-core-20261125-01/independent-review.json)。负责人再次授权后，本轮两文件安装／加载、唯一调度切换及统筹独立读回已通过，发布后8181同一告警和材料的显示再次核对通过。上轮零执行的自动审核超时回执保留；后续单条首次保存及新提示真实A已补验，具体结果与剩余AI数值／null理由语义缺口见[单条链独审](../operations/evidence/alert-score-first-receive-20261125-01/independent-closeout.json)。[本次限定发布独审](../operations/evidence/alert-rule-source-confidence-20261125-01/independent-release-resume-review.json)。

2026-11-19 [独立接入审计](../../openspec/changes/complete-socai2-investigation-chain/independent-integration-audit-20261119.md)登记 IA01–IA11：持续信封适配、湖持久确认/完整原件、class/is_alert/partial 分类、字段及取证路径、SpiritHub 写鉴权与新旧接口、SF必需产出、展示/运行记录、版本交付及过期文档入口。49项既有离线检查和7项结构探针已完成；现场版本/配置/Schema/源码指纹已复核；完整SpiritHub对照校正为19未接/19退役代理。新增只读类型盘点，统计留21，未向会话读取业务记录或执行模型，正式业务接入仍未发布。逐项影响、责任、验收与顺序集中在报告，不另建任务树；SF01–SF07及原质量后置状态保持。湖问题的[3a字段合同](../../openspec/changes/complete-socai2-investigation-chain/clickhouse-lake-design-20261119.md)及合成验证已完成；入湖400天/重试刷新已确认并在3b隔离库验证，005/新装/显式profile及TTL/租户清理条件已接线。3c进一步完成新裸入口的稳定身份、对象投影、完整正文及实际原生库读回；显式null祖先不回填、负毫秒绑定及type_uid长整数范围均已修正。3d已在合成隔离Topic/group/库完成消费与持久确认，91项定向检查和真实链三组通过，失败/未知不越位；首次分配竞态已修正。3e已将指定Topic真实固定范围写入隔离库并完成聚合核对，报告和数值留21；正式表/持续消费未更新，3f同批基本查询及完整原文关联已通过，4a规则实现与只读验证也已通过，下一步4b接收存取；来源身份语义待确认。原信封缓冲/截断及正式发布边界仍未核销。

2026-11-18当前基线：[21新版发布/清理](../operations/evidence/acceptance-release-20261117-01/README.md)及[新两段完整链](../operations/evidence/acceptance-fullflow-21-20261117-01/README.md)已完成。2告警/3上下文形成同事件/同Case两轮1→2，477份HTTP及142工件读回通过；8真实模型均stop，共45207tokens，实际并发峰值1且结束无在途。测试/HTTP限定独审与4177三类主体/两轮查阅通过。4b随后已完成来源/精确轮次链接及r8发布读回；[D5a新批](../operations/evidence/deep-unit-continuation-d5a-20261118-01/README.md)现已补齐有效Deep答案→真实C6→PG/HTTP及独立存取复核。[D5b接收/保存](../operations/evidence/c6-unit-continuation-d5b-20261118-01/README.md)已通过两个本机PG/Redis代表及142 GET，独立同包存取复核通过。[D5b采用/比较](../operations/evidence/c6-adoption-comparison-d5b-20261118-01/README.md)已通过21独立三轮直接存取及HTTP保护，独立存取复核通过。[D5c局部依赖](../operations/evidence/local-dependency-d5c-20261118-01/README.md)及实际遇到的时钟收尾阻断已通过21直接/独立验证：原初答/Deep进入C6，无图结果保存读回，硬失败新任务自动结束。[D5c调用中断/unknown](../operations/evidence/transport-continuation-d5c-20261118-01/README.md)也已完成21直接和限定独立复核：已有完整行/候选保留，unknown不生成Result，下一任务完成；原替身签名失败保留NOT_PASSED且仅新任务补验。[D6本轮候选展示](../operations/evidence/http-viewer-d6-20261118-01/README.md)已完成四代表真实TCP/浏览器及限定复核，修验局部读取和本批422/连接池配置；随后[D6正式0.6.2/r9](../operations/evidence/workbench-d6-release-20261118-01/README.md)已通过四异常代表及恢复日常两轮的HTTP/浏览器读回；模型正文未全面验收，完整覆盖和change结束审计仍待，旧原答/拒收/NOT_PASSED保持离线。

本批后置质量共5项：首轮C6影响分析的`empty_sources`与`delivery_source_coverage_missing`两项；后轮I两个open_questions声明两成员但引用只覆盖一个成员；后轮C6比较类型`withdrawn`与正文“范围扩大、核心结论不变”不一致。[自动4项及直接核对](../operations/evidence/acceptance-fullflow-21-20261117-01/final-validation.json)、[人工1项](../operations/evidence/acceptance-fullflow-21-20261117-01/manual-quality-review.json)均保留原答，不重采样；两轮Case仍accepted/uncertain/partial，未阻断下游。8份实际模型输入无控制tenant/来源标识，后台关联保持。

11-18 D5a新增真实C6一次stop/12097tokens，C3/Deep受控回放两次单列。C3回放保留1条重复引用、真实C6保留2条不适用领域缺限制说明；Deep旧inline引用及替代解释未经真值验证，正式support/counter为空，不绑定新证据。[质量回执](../operations/evidence/deep-unit-continuation-d5a-20261118-01/quality.json)保持NOT_PASSED，不再采样。预检另发现11-17完整Deep母本超过1200字结构上限，已保留失败、改选合法冻结母本，正文上限及旧失败不改。

更新于 2026-11-19。当前发布和字段合同见[交接指南](../../FRONTEND_BACKEND_HANDOFF.md)。下列未完项独立于部署、读取和字段对应验收；登记不代表修复或取消需求。历史[独立流程审查](../handoff/history/2026-11-14-investigation-cleanup/documents/docs/investigation/investigation-flow-review-20261111.md)保留当时结论，不能将其中已修复/已交付事项继续算作当前缺口。

本轮[当前功能与整体流程评审](investigation-current-review-20261114.md)按4177三案原件、当前代码和21只读状态登记RV01–RV13，逐项说明影响、优先级及直接验收。它不替代主change结束审计，不修改既有质量后置决定。

后续按[六阶段实施规划](investigation-implementation-plan-20261114.md)推进：先固定交付修正，再完成统一领取、变化传播、H复核及异步维护。负责人最新明确引用质量与正文质量分开，引用正确性一并后置；引用错误不代表结论错误，原结论及原业务判定保留，问题另记，不能仅因引用错误删除/降级待核或整份拒收。13项评审发现均有阶段和关闭证据映射；规划不代表修复，原任务勾选状态保持。

阶段1的[详细设计及OpenSpec更新](../../openspec/changes/complete-socai2-investigation-chain/stage1-problems-and-plan-20261114.md)已明确整体效果、七步依赖及直接验证，分别归入既有RV01/RV02/RV04/RV12及原件留存要求，不另建任务树。步骤1 A/I与[步骤2 Case](../operations/evidence/stage1-case-retention-20261114-01/README.md)已完成原结论保留、引用独立记录及Case下游/采用的本地验收，stale及预览令牌保护保持。[步骤3 C3](../operations/evidence/stage1-c3-contract-20261114-01/README.md)一次七部分/8192/最多5发现也已完成保存读取，48项直接检查和44次GET通过。[步骤4有界补答](../operations/evidence/stage1-c3-completion-20261114-01/README.md)也已完成一次真实模型补答与19次GET，前六字段/逐字段原答来源保持；该批当时预算及C6预留不变，当前额度按11-16授权另行提高。[步骤5补查分流](../operations/evidence/stage1-followup-routing-20261114-01/README.md)已完成本地真实查询与保存读取；[步骤6原件存取](../operations/evidence/stage1-original-retention-20261114-01/README.md)已通过7份大原件保存读取、配置快照及历史8Run模块关联验证；历史配置未保存、unknown及夹具失败保留。[步骤7展示](../operations/evidence/stage1-viewer-20261114-01/README.md)已完成14项离线、快照逐值读回及21项浏览器验证，七步限定本地证据已齐。上述回执为当时各步本机证据；后续运行以页首当前正式D6/r9及11-19现场回执为准。引用准确性/正文质量继续后置，不核销整体发现。

步骤1历史复用检查发现`test_socai2_stage_quality.py`两项旧断言要求3000字符命令及大段metadata被省略，与`field_limit=draft_limit`口径不符，原基线失败保留。本轮触及输入容量后，已按所选policy构造超字节额度材料，检查预算内3000字符原值保留、超限字段整体省略、路径和成员归属及原件不变；[最终2项直接测试](../operations/evidence/streaming-budget-20261116-01/stage-input-capacity-after-03.log)通过，只关闭这两项测试口径问题。同时发现候选env没有加载既有输入保护额度，默认60000字符；已在同镜像替代容器[补齐并无网络核验](../operations/evidence/streaming-budget-20261116-01/input-guard-finish-01.json)，未改保护规则或重做业务。最初相对policy路径、保护环境未对齐及中间失败记录保留，不追认旧批通过。

步骤2复用检查还发现历史查询重复展示断言期望2条whole-row来源，当前输入选择为0，在修改前源码同样失败；[对齐后基线](../operations/evidence/stage1-case-retention-20261114-01/baseline-aligned-tests.txt)记录27通过/1失败。其余23项旧夹具失败由调用历史装配入口、未补程序coverage导致，本轮只将6处夹具改用当前入口。历史查询选择/去重实现未改，剩余断言后续触及该输入显示时处理；本轮59项直接检查通过，未宣称全套测试通过。

## 本轮评审补充

**3c.3 对3c.2原件的只读汇总（2026-11-17）**：新[会话报告](../operations/evidence/acceptance-session-console-20261117-01/report-02-v03/report.md)按阶段读取规范回执，确认 C6 9 项之外还有 C3 6 项、I 2 项，共17项质量诊断；步骤跳过/错误另16项。C6九项原结论和四Result的accepted/uncertain/partial不变；这些是诊断记录，不代表17个独立根因，更不表示正文已全面验收。13个保存请求/109995Token来自原02真实两段，本次汇总0新模型/投递；不混入01的两次调用，01 prepared内缺快照仍显示统计未知。质量继续后置，不重采样、不阻断独立功能推进。报告自身的范围显示、坏消息兜底及attempt终态问题按3c.3独审单独修正，不与模型质量混记。

**3b C1阻断：本机续验通过，21未发布修复（2026-11-17）**：原[单段02](../operations/evidence/acceptance-singlepart-20261117-02/README.md)的Case input SQLSTATE21000及0Run/Result保持。唯一外层任务别名修正已核真实PG新旧两案，后续[本机完整续验](../operations/evidence/acceptance-case-continuation-20261117-01/README.md)在同租户两事件下完成本案1成员、正确I来源、17步骤50工件及1Result保存，168GET和26表只读核对通过；未替换21。新库漏函数EXECUTE、驱动只读锁及Run目录依赖遗漏已本地补齐，失败task/unknown attempt或Run原件保留。[测试模块独立复核](../operations/evidence/test-acceptance-case-continuation-20261117-01/independent-review-01.json)通过。成功Run的[5项引用诊断及1项历史未查误写查空](../operations/evidence/acceptance-case-continuation-20261117-01/quality-register.json)后置，不重采样或阻断后续流程；正文NOT_PASSED。3b CLI旧三个独审问题维持已修结论；21恢复/TCP/4177仍待统一发布。

新02批[质量登记](../operations/evidence/streaming-fullflow-20261116-02/quality-register.json)共19条去重程序诊断：A04分诊6条（正文引用别名及非结构化引用）、单案C3 4条（重复引用/来源成员不符）、整案R1 C6 3条（成员/领域范围不符）、单案C6 5条（重复引用/成员不符）、整案R2 C6 1条（重复引用）。同一诊断在多个工件出现只记一次，跨阶段保留传播记录，不等于19个独立根因。三Result均accepted/uncertain/partial，保留判断及原答、0质量重采样；正文质量未全面评估。程序功能通过不能追认模型质量。

2026-11-16新批I末尾8163空白、8192/length已按负责人允许重试完成[原因核查](../operations/evidence/model-output-compatibility-20261116-01/说明.txt)：实际xgrammar将非空pattern `\S`解释为整串单字，单独长度约束还拒绝正常JSON转义。相同输入1239tokens、模型/fingerprint、temperature及8192上限，仅改变3项生成Schema约束，一次重试1166/stop、正文完整且原Schema/非空/长度通过。本地提供端适配修正24项检查通过，随后已随processing r3部署且新批16次均stop；不归因于额度不足，不把旧原答改写为成功。扩展选测的4项delivery范围/格式旧断言失败，用修改前适配同样复现，保留[旧基线](../operations/evidence/model-output-compatibility-20261116-01/baseline-delivery-tests.log)。新I/Case链已按页首批次执行，正文质量仍未通过；tenant_uid过滤及D1–D4c已发布r4，其他截断/网络异常继续按D5推进。

2026-11-15，21候选S01-r3的同批A/I真实执行新增[正文观察](../operations/evidence/test-streaming-ai-20261115-01/quality-findings-01.json)：3条A原答的rationale均只有“告”，每条30个引用且大量重复；I的summary/conclusion及3个成员正文均为“A”。4个Run、4次真实生成、9次背景查询及来源/保存检查通过，只说明程序链执行，不说明benign/0.95或正文为真，质量仍为NOT_PASSED。原请求/原答和错误保持，不重采样、不改写。根侧仅离线核[已保存请求和原答](../operations/evidence/streaming-ai-20261115-01/saved-request-review-01.json)：4答均finish_reason=stop、请求额度3000，A自由正文约束允许1–4000字符；没有发现保存时截成单字的证据，根因未确认，不能直接归因模型能力或后端。沿既定质量/生成约束后置处理，未写成已修复，也不把结构覆盖3/3算正文有效。

同批[Case真实首轮](../operations/evidence/streaming-case-20261115-01/README.md)已完成两个Run、4次真实生成/4次C4、保存及58次HTTP读取，正文为正常长文本。两个Result均accepted/uncertain/partial，不能继承上游“单字”描述，也不等于正文通过。[本次质量记录](../operations/evidence/test-streaming-case-initial-20261115-01/quality-findings-01.json)保留10项引用问题：重复引用、冲突缺原始观察支持、回答无来源、影响范围缺支持等；按已确认策略保留判断、局部去重、不改原答，NOT_PASSED保持。单A01 closing_note提及“补查到网络连接”，实际C4仅process/auth，这一措辞另列待复核；正文未全面验收，不追加查询或采样。[部分交付依据](../operations/evidence/test-streaming-case-initial-20261115-01/partial-delivery-01.json)按实际记录来源缺口、预算保留的未查询、未决成员/问题等，与引用及质量分别展示。程序联验通过不核销这些问题。

原11-15[S04增量](../operations/evidence/streaming-s04-20261115-01/README.md)正确入湖、A04归入原I并完成分诊，但I在3000/length处截断，没有Case后轮；原答/保存一致、失败及134项保存检查/44GET保持其历史结论。11-16按负责人明确要求提高预算后，以新operation_key受理一次I rerun，输出4518/stop；新诊断保存后整事件Case自动扩到4成员、完成第二轮，上一轮身份和HTTP链接正确。单A01案仍1成员/1Run，旧判断stale。119项保存检查、48GET及查阅追加通过，只关闭本次正向程序链未到达缺口；W2/W3原样本范围保持，W4/W5、完整change独审及正式发布仍待。

本次[后轮质量摘要](../operations/evidence/streaming-budget-20261116-01/quality-summary.json)仍NOT_PASSED：C3记录`observed_original_fields_exceed_statement_contract`及`unknown_domain_finding`，保留原答并局部排除依赖无效项；C6仍有比较未同时引用选定前轮/当前来源、影响范围来源覆盖缺失两项问题，按既定策略保留判断。结果仍accepted/uncertain/partial；模型change_kind=withdrawn原样保存，不能从比较身份正确推导比较正文正确。I/Deep没有引用诊断不代表正文已全面验收；原两案首轮10项引用问题不改写、不反复采样。

| 评审项 | 新核实的内容 | 处理落点 |
| --- | --- | --- |
| RV01 生成与接收约束 | 登录A、C02/C03 C6三份已拒收原答均通过实际发送的Schema；重复引用及answered无依据未被生成约束阻止 | 按最新决定，当前仅处理原结论/原判定与问题分别存取的必要衔接；引用准确性及生成约束优化后置到阶段6，不以引用错误推导结论错误；旧原答/拒收保持 |
| RV02 C3输出截断 | C02在4096处截断；历史同输入8192对照实际4395tokens完整，旧接收器仍报引用问题；原失败保留 | 步骤3已本地验证8192、单次七部分、最多5发现的实际请求、保存及44次GET，引用诊断衔接复用步骤2；步骤4已有旧真实截断原答+1次真实补followups及19次GET，保留初答失败/前六字段/逐字段来源和预算；未验证真实模型普遍稳定性，未发布、不重派旧Run |
| RV04 补查目标与实际取证 | 旧三案关闭ClickHouse/产品源，4次Deep无候选/0个C4.query；步骤5先确认原演练未入湖，按负责人授权写6条演练事实及上下文 | 步骤5本地44项检查；原生C3的human/query计划→真实认证查询2条（含新增上下文）→C6→47次GET通过，原预算/预留保持。首轮传输脚本错误的unknown及33次读取保留，未重派。query原目标仍涵盖认证/网络/进程但B1仅认证，描述过宽留质量阶段，未宣称其他来源已查；程序未发布 |
| RV11 新材料入口（本期不纳入） | 原评审记录生产重投/投影恢复首次快照；负责人随后明确不需要新增同告警材料版本判断/提交或据此重新分诊 | 按流式Q3范围调整保留现状观察及原件，不标为已实现、不作为本期前置；更新按告警范围、A分诊及相关I诊断结果分别向下游传递 |
| RV12 4177结论展示 | 告警/事件“本轮交付”指向Run，正常`stage_output_saved`被归入错误；同Run的分诊判断/理由和事件诊断结论实际已保存 | P1，当前展示问题已[本地修复验收](../operations/evidence/stage1-viewer-20261114-01/README.md)：同Run原结论、正常结束、引用及采用分开，成功/失败/unknown和空态实测通过；该回执当时仅本机；现已接实际4177的W5与新批两轮，D6本次Case异常回执/局部读取失败增量已通过候选与正式4177四代表，完整覆盖仍按change范围核对 |
| RV13 入站运行及配置 | 21投影本轮三分区lag均0，Agents自动分析仍关闭；投影异常会held并退出实例 | 继续区分入站/调度/执行/交付/采用；停位与局部硬编码在触及路径内处理，不开展恢复专项 |

[离线证据及脚本](../operations/evidence/investigation-current-review-20261114-01/README.md)保留本轮取数修正记录。RV03/RV05复用M01/M02/F01/F02；RV06–RV10复用下表现有流式缺口，不另建任务树。以下已交付功能保持，CLI和本轮评审不核销主31/41。

## 本轮输出继续实施

沿既有RV01/RV02/RV12与M01/M02落点，不另建任务树：

| 问题 | 最新设计及直接验证 | 当前状态 |
| --- | --- | --- |
| 实际请求仍带tenant_uid | D1按路径/用途过滤A/I/C3/Deep/C6，原件/业务source/id/未知字段/0/false/[]保持 | 本机已修复并验证；D2三份、D4c九份新实际请求通过，后台身份/原件保留，已随r4发布，21新02的14份真实请求禁入标记0，旧16份保持 |
| 缺限制说明等质量问题仍整份拒收 | D2保留结论/判定/范围，仅记录问题；无效引用不绑定；保存/HTTP核对，旧拒收保持 | 本机功能通过；新真实链2项缺说明记录后继续，另1项C3引用覆盖保留。质量仍NOT_PASSED/未全面验收 |
| 程序原观察还原受模型正文上限误拒收 | D2程序还原1218字/32字段完整保留；模型撰写正文限制、来源与防篡改不放宽 | 本机必要装配阻断已修，独立21项含母本与保护检查通过；已随r4发布，当前21新批另验 |
| length、JSON半项及网络异常不能普遍继续 | D3–D5统一阶段回执与闭合单元恢复，C3补答失败保初答，I终结回执驱动活跃Case；超时/断连不堵独立下游/队列 | D3 C3已通过截断/空白补答→C6；D4a A/I已通过完整/partial/none保存读取。D4b门控/分配/C1冻结及D4c partial/none→同Case两轮完整链通过；D5a有效Deep答案已通过实际C6/PG/HTTP及独立复核；C6自身恢复/两类部分结果保存已通过本机PG/HTTP；采用/后轮比较已通过21独立三轮、失败身份不回退及人工保护；D5c局部依赖已通过21存取、原初答/Deep和无图结果保持；D5c第二步超时/断连/unknown本地收尾及N=1下一任务已通过21直接/限定独审；D6已核候选及正式0.6.2/r9的TCP/页面，完整覆盖/结束审计仍待 |
| C3显式空发现误使领域无效 | D3接收器曾将findings=[]当Finding依赖；仅纳入真实Finding条目，保留合法空数组及原四领域 | 已修并复验；原51通过/1失败记录保持，最终96项直接与34项独立通过，不改变旧用例预期 |
| 部分材料被误作比较基线或页面空白 | D5/D6区分可作prior_analysis、可采用、可比较；旧拒收不回填，局部读取错误留原流程 | D5b已通过21 PG/ASGI HTTP：无核心结果不可采用/比较，保留有效分析进入后轮；D6候选页面已通过部分/无核心/unknown两代表、局部原件503及GET单卡重试；正式4177已更新0.6.2/r9并验四代表及恢复日常两轮 |

完整规则与顺序见[第11步设计](../../openspec/changes/schedule-streaming-investigation-updates/stage11-output-continuation-design-20261116.md)，测试复用原TC-N01–N11及[设计回执](../operations/evidence/test-continuation-design-20261116-01/README.md)。设计/mock不证明真实模型质量或整体change完成。

## 待沟通：OCSF 资产关联 ID

2026-11-24 负责人明确今天简化，后续由负责人和清洗模块沟通，在 OCSF 中提供明确的资产关联 ID。本项状态为**待沟通、权威资产ID关联未验收**，不因查询返回 200 或已有局部正例而核销。

待确认内容：

- 资产 ID 在 OCSF 中的准确字段路径、类型及单个／多个关联的表达，关联的是哪个业务对象。
- 该 ID 对应哪一套原生资产库及其身份范围；若是来源系统设备 ID，明确到原生库存 ID 的映射，不能直接当作库存主键。
- 按 ID 查询资产及打开详情的入口，以及 ID 缺失、查无资产或关联不明确时的返回和展示。

11-24批次未实施基于端点 IP 的匹配扩展、定向对象恢复或据此补造资产，不自行猜测新的 OCSF 字段。既有主机/IP 查询规则及旧限定证据保持；权威资产 ID 的接线仍需合同明确。

11-26负责人明确授权以既有规则补齐批准OCSF组的测试资产。已向原生资产表插入四条当前可匹配记录，统筹独立数据库/HTTP读回及8181指定事件摘要通过，见[限定验收](../operations/evidence/incident-test-assets-20261126-01/independent-closeout.json)。本次没有新增匹配算法或OCSF字段。批准组另一个接收地址未进入当前对象投影，不能只靠库存插入补齐该记录；差异保留，未回填历史对象。此结果不核销权威资产ID合同或全告警资产链验收。

当前诊断、停止范围及回执见[告警资产安排](../../openspec/changes/complete-socai2-investigation-chain/alert-chain-acceptance-plan-20261124.md#资产事项转为待沟通ocsf-资产关联-id)。

## 待整理：告警负责人名称显示

2026-11-24 指定OCSF告警的负责人保存联验发现：人员选择器使用Q04的 `display_name`，列表/详情的既有 `owner_name` 由服务端读取 `username`，活动变更展示 `owner_id`。本次页面各处均对应受控选择器中的同一人员，暂未发现身份混用，但名称显示不统一、活动ID可读性不足。按负责人先完成功能、其他问题先记录的要求，本项后置、未修复；不因此改动冻结的 `owner_name` 含义或增加写入验证。后续先确定统一展示口径，再在告警范围处理。[页面身份和现有合同独审](../operations/evidence/integration-coordination-audit-20261124-01/alert-management-ocsf-owner-ui-contract-review.json)。随后负责人保存的PG/E30实际回执、请求哈希及页面已[独立核对通过](../operations/evidence/integration-coordination-audit-20261124-01/alert-management-ocsf-owner-save-review.json)，只变更负责人和相应管理元数据；名称可读性事项仍未修复。

## 事件诊断直读与页面反馈已通过；正文质量后置

2026-11-25，负责人截图显示最近一次I诊断失败且没有已发布结果。获准OCSF组内的同类记录已定位到生成前容量误拦：计量将grammar输出Schema封装加入上下文；同模型/协议/profile/冻结配置的成功回执证明provider prompt用量等于聊天模板计量。仅已验证I请求形状的窗口准入已修，累计预约、真实窗口和调度停止状态保持；29项核心/1项页面直接检查及[限定独审](../operations/evidence/incident-diagnosis-capacity-20261125-01/independent-review.json)通过。8181提示已改中文。

负责人随后明确授权限定发布21及一笔真实诊断，已完成[本轮后端验收](../operations/evidence/incident-diagnosis-live-20261125-01/README.md)：实际加载修正，唯一新Run completed/完整交付并采用，窗口51675/65536、累计预约及预算保持，请求body与旧冻结请求完全相同；旧失败原件逐字段未变。PG/HTTP独立读回及当前4177读取通过。负责人登录后实证E23默认分页超时；同Run重复构建已限定修复并发布，统筹独核实际加载及配置保持。8181正文、待核问题、最近尝试和整页刷新已与PG一致；Q09旧路径404已由平台事件身份适配限定修复并发布，实际源码/配置及原四字段合同经统筹独核；新Run概览的完成状态和保存摘要、旧Run概览的原失败/未交付及空正文均通过8181独立验收；截图仍无地址绑定，不能冒称该新Run就是截图中的事件。

保留质量未通过：新原答有两项`source_alias_in_prose`，位于`$.findings[0].limitations[0]`和`$.open_questions[0].evidence_requirements[0]`，正文质量为not_checked；不追加采样。原E23 limit=1约12秒成功、limit=20约24.45秒超时证据保留。此前修复后的E23默认历史页实测约18.3秒，性能边界保留；11-26事件首屏已移出该历史读取路径，不能以本次E29结果宣称历史接口也已加速。

11-26已完成E29事件专属保存投影、平台合同和8181概览/摘要接线，并在同一窗口限定发布21。统筹独核运行源码与配置；E29本次41.05ms，采用正文与最近尝试对既有独立PG回执一致，成员聚合与已验候选一致，固定E25旧失败保存不变。8181正文/原Run链接、列表和摘要统计/检测源、资产及刷新结果通过；首屏不再调用E23。关系图默认适配与右侧重复资料亦已限定独验。[完整结果与边界](../operations/evidence/incident-saved-diagnosis-read-20261126-01/README.md)。审核另发现并删除列表资产列的原始对象补偿；告警、事件、调查指令相关生产路径其余未发现同类测试特判。[审核范围](../operations/evidence/incident-saved-diagnosis-read-20261126-01/independent-no-test-logic-review.json)。本轮无新模型或业务写入，正文质量后置问题保持。

11-26负责人后续截图的右侧裸IP、空资料/重复告警列表，以及概览资产卡固定“总数未提供”已分别修正并在实际8181独验（[图右栏](../operations/evidence/incident-graph-selection-clarity-20261126-01/independent-review.json)、[资产卡](../operations/evidence/incident-overview-asset-count-20261126-01/independent-review.json)）。未新增接口、额外资产匹配、补偿或自动续页。

战术标签缺口已只读定位并独立复算（[核心原因](../operations/evidence/alert-incident-tactics-example-20261126-01/core-root-cause.json) · [独核](../operations/evidence/alert-incident-tactics-example-20261126-01/independent-root-cause-review.json)）：批准原组无标准检测标签；4173/8181事件卡只聚合当前成员的 `material.detection.tactics`，I输出也没有AI战术字段。限定一笔当前材料/分诊同源A原答非空，全部映射实际引用 `unmapped` 下的 `source_label`，因 `attck_evidence_unavailable` 拒收；请求Schema允许这些别名，接收只允许 `observation/human_statement`，两端约束不一致。解析和同Run保存均为null，未发现落库丢字段。历史冻结请求与当前容器可见profile各自都有五项提示/禁止其他字段与ATT&CK输出要求冲突，但两者profile哈希不同，不称同版或唯一原因。冻结HTTP/evidences字段只有source_label，是另一覆盖缺口；本笔映射并未引用这些字段。raw_text实际因input_guard排除，角色无关去重仅为静态风险，本代表无对应去重回执，不纳入已证实原因。下一步先处理A提示、Schema/接收一致性及标准行为角色，保持未知扩展和检测标注边界；保留旧模型质量未通过，不由单代表推断全组或新采样追认。

源标签正例随后按负责人明确授权完成两文件21受控链路更新及一笔真实投递，唯一Kafka/落湖/created、保存和HTTP、8181告警检测标签/事件战术卡与计数均通过统筹独验（[回执](../operations/evidence/alert-incident-tactics-example-20261126-01/README.md)）。原组保持；既有自动A/I完成、4177同Run资料可读，没有手动重派。该修正仅用于已审受控一次性进程，未全局切换常驻服务。人工源标签传递正例不能替代AI判断，A提示/证据角色/接收约束问题仍未修复；事件AI战术展示需另明确来源/聚合合同。负责人现要求[主机安全多行为上下文场景](../../openspec/changes/complete-socai2-investigation-chain/host-context-scenario-20261126.md)，先准备结构完整的独立数据包，不通过样例特判补功能。另有旧列表用例期待文案与当前资产组件不同，系静态发现且本批未执行，见资产卡前端回执；不据此追加回归或改变生产功能。

## 当前功能缺口与实施入口

- 21 手册部署演练后的 Case 容量失败仍未核销：[原部署/恢复回执](../operations/evidence/investigation-manual-d2d3-20261127-01/README.md)。M0c/M0d 与 M0e 第三步 B 本地入口修正保持；第三步 C 新批 02 已完成一次计量入口及临时连接收尾，[操作回执](../operations/evidence/case-input-capacity-m0e-20261128-02/README.md)，实际统计/最小诊断按用户限定回传保存在私密范围。当前补源码职责审阅：Case 准备字节上限、共享 classifier 字符上限、token 准入与网关重复校验，以及内容检查的原因合并；不把源码风险当未经核定的实际命中，不增预算或关闭检查，尚未实施新行为。旧批与首次连接启动失败均保留，临时 SSH 已关闭。

2026-11-18 [字段职责审查](subject-field-baseline-20261118.md)新增 SF01–SF07：系统等级意见和优先级/人工覆盖链、I/Case结构化业务判定、4173事件派生等级/建议正文/采用摘要映射和轮次口径。9次只读GET及当前真实执行快照证实缺口；这不是模型正文质量后置项，也不能以数据库可空豁免。[设计定稿](../../openspec/changes/complete-socai2-investigation-chain/subject-field-audit-20261118.md)已按负责人确认只升不降、人工升降、五档映射、时间线、任务时间和文件日志，给出S1–S7；11-20按负责人要求优先实施交接字段，[S1创建等级/优先级及统一读取](../operations/evidence/subject-risk-s1-20261120-01/README.md)、[S2独立意见/自动上调及保护](../operations/evidence/subject-risk-s2-20261120-01/README.md)、[S3人工等级/优先级及撤销管理](../operations/evidence/subject-risk-s3-20261120-01/README.md)已在候选真实隔离PG/HTTP通过。S2实测修复新direct I自身风险输出导致立即stale，旧失败保留；0真实模型，不追认质量。旧数据GET不回填、正式未发布。SF01/SF02及SF03等级接线纳入该计划，SF04–SF07其余项保留；[S4页面候选](../operations/evidence/subject-risk-s4-20261120-01/README.md)现已完成最后只读浏览器/旧记录审计及限定独审，原自动审批超时与程序/夹具失败保留。下一步按[现有HTTP真实数据接通及新批次单轮](../../openspec/changes/complete-socai2-investigation-chain/http-real-data-connection-20261120.md)推进；S5/S6和[SF05建议展示](../operations/evidence/recommendation-display-sf05-20261120-01/README.md)已通过候选限定验收；[SF06采用Result依据/原范围/未决项](../operations/evidence/assessment-basis-sf06-20261120-01/README.md)也已通过限定验收；[人工版本/工件来源链](../operations/evidence/assessment-source-http-sf06-20261120-01/README.md)已候选存取/页面验证，[SF04事件/Case业务判定](../operations/evidence/subject-business-verdict-sf04-20261120-01/README.md)已候选验证，SF07移出本期。剩余核告警取数和跳转参数、外部合同供给，以及正式版本/新真实告警联合验收，归主调查3.10/3.12/3.23/3.30，不新增独立问题管理流程。

S2定向组合另保留一项未解决检查：`test_history_duplicate_presentation_preserves_c3_and_final_dependencies` 在历史查询展示选行断言失败，尚未进入本次等级输出路径。本轮未修改其选行实现、不称整套回归全绿，待对应历史查询展示步骤处理；失败状态与其他通过项见同批[本地检查](../operations/evidence/subject-risk-s2-20261120-01/local-checks.json)。

固定调查核心v1.2-20261113-r1/当时71操作仅作历史依据。当前21处理/HTTP为20261117-r1，4177为0.6.2/r9，旧处理入口停止；本批两段正常业务链及4177三类/两轮查阅已通过，测试/HTTP限定独审通过，原A/I/C3/Deep/C6质量问题与失败保留。第1–7步/F1–F5已交付的本机边界不重新列缺口；当前未完项为下表及本轮输出继续设计、完整change结束审计和后续统一交付。第8–10步后置。

| 当前实际缺口 | 代码/行为依据 | 后续实施落点 |
| --- | --- | --- |
| 工作台正常链及4b已验，D6正式展示已验，完整覆盖待办 | 任务1/2、3a–3d、正常两段链及[4b来源/精确轮次r8发布](../operations/evidence/workbench-4b-release-20261117-01/README.md)均已完成各自出口 | D6已用21已存四代表通过候选和正式4177的TCP/浏览器；503重试沿已封候选证据与相同源码复用，恢复日常两轮目录及冻结输入通过；后续核完整change范围 |
| 整个change仍未收口 | 本轮范围、文档和独立结构审计见[结束核对](../../openspec/changes/schedule-streaming-investigation-updates/closeout-scope-20261118.md)；本期总任务核销、最新写侧统一交付/读回和Git/父项目同步保留未完成。既有工作台独立发布不替代这些条件 | 沿原2.2–2.5/2.7/3.1核清本期总项，再按3.2/4.1完成必要交付；当前不归档 |
| 异常继续的分步验收与统一交付分开 | D5各子步和D6展示沿原回执保留，最新D5写侧不能因工作台发布被视为正式同版交付；不重判旧失败/unknown，不增加模型质量采样 | 沿原4.1核对后端、HTTP、配置与工作台的实际发布范围，不能用页面版本代替写侧版本 |
| Case成员跟随已接，余项验收仍待 | r4新02已201建案并实际验证整事件Case3→4、单告警保持1成员/1轮；R2固定最近R1及Result，旧步骤/原件/结果保持 | 排除/关闭/超期沿原证据；D4b已验4总/3选/1保留仍分配Case全4，D4c已验同案两轮及next_check_at受控时钟的周期0/1分支；未等待真实4/6小时；本批显式source=user检查不作自然周期证据 |
| 一次人工定向分析与用户手动后续综合后置 | H版本与人工方向/定向请求需区分；既有保存不代表定向分析已运行 | 第8/9步保留设计、未实施，不作本期1–7验收前置；2.4/2.5 |
| 分诊完成仍等待历史知识同步，队列维护后置 | knowledge_sync.after_triage 在业务提交后等待；原回执可读但无统一调度状态 | 第10步保留设计、未实施，现状不改称后台异步已交付；2.6/2.7 |
| 自动接续的完整change核销仍待 | 原3.1/3.2/4.1保持综合项边界；[人工定向分析、手动全案综合、知识后台异步维护](../../openspec/changes/schedule-streaming-investigation-updates/deferred-scope.md)已明确后置且未实施，其余本期未完成项不能一起后置或勾选 | 三项后置能力继续保留原编号和恢复出口；其余本期缺口按原任务收口，不新建平行任务树 |

以上沿已有 [schedule-streaming-investigation-updates](../../openspec/changes/schedule-streaming-investigation-updates/tasks.md) 的11步顺序推进。任务三表、A/I执行与I周期、第5步分配、第6步Case initial及第7步持续更新已接；整体交付与结束审计仍待，D1–D4c已按本轮授权分阶段发布。告警交接字段保持；E36移除、E37异步202，Case外部旧prepare/start随首轮真实闭环后退役；正式运行以页首20261117-r1新两段批及PROGRESS为准，旧T1仅保留当时预检。

**主调查 31/41 不等于还缺十个固定流程功能。** 3.7/3.10/3.14/3.16/3.23/3.30 含正文质量及未验业务范围；3.21 为自动接续，3.12 含产品操作与暂缓范围；4.1/4.2 是整体结束审计及归档。模型质量继续后置；Q 对话、真实响应和产品页面接线不作为本次调度前置。旧可选 C3.reanalysis 不在默认链路，需另按任务目标适配后才启用。

## 已决定后置的质量及历史证据

[D4c真实任务链](../operations/evidence/ai-case-chain-d4c-20261116-01/README.md)两轮C6原答和Result都把A4网络流量说成早于A2 curl启动；各轮实际别名映射对应的原始时间分别是05:50:12与05:46:12，实际晚4分钟。第二轮沿用了该错误，不能因为比较身份为eligible或保存accepted就认定比较正文正确。该人工核对发现与4项自动引用诊断分开记录，保留全部原答/Result、不重采样；首轮I完整原答的登录到进程“8分钟”也与实际6分钟不符；该成员位于未交付的截断后部分，没有进入下游。功能链继续通过不核销这些质量问题。

11-15第6步复用后续模型输入测试时，`test_history_duplicate_presentation_preserves_c3_and_final_dependencies`预期2份历史记录但实际选择0；去掉本次新增query_preparation序列化字段的对照仍复现。本轮正常C1–C6及查询/容量保存读取已通过，旧历史夹具/引用映射问题登记后置，不修改测试期待来追认通过。来源见[第6步回执](../operations/evidence/case-initial-20261115-01/README.md)，模型正文NOT_PASSED保持。

[11-15第4步A→I](../operations/evidence/analysis-incident-auto-20261115-01/README.md)新增1合成告警/1事件、2次真实调用、2Run及保存/读回。A正文“告/需”、I正文“N/A”仍不可用，NOT_PASSED和原答保留，不追加采样。63项当前离线检查、11项PG/Redis直接检查通过；4项旧I别名重放测试在恢复本步相关修改的同配置对照中仍失败，旧profile/渲染差异登记后续，不改历史原件。

[11-14三案展示](../operations/evidence/fixed-investigation-20261114-01/README.md)新增4A/2I/3Case、19次生成，每个Run仅一次并沿现有有界纠正。E01登录A重复引用拒收；C01结论待复核且已采用，但仍有凭名称推自动化等正文问题；C02 C3达到4096输出上限截断，C6两答缺依据并有范围错配；C03 C6两答建议重复引用。后两案结论null、未采用，原答/失败及NOT_PASSED保持。C3输出长度/结构留待后续评估，本批不重派。4177和4173已同步真实保存结果与空态，未核销产品完整接线或质量项。

[11-15第3步真实A](../operations/evidence/analysis-alert-auto-20261115-01/README.md)新增1条合成告警，经正常native入站和统一Redis调度完成1次真实模型调用、1Run保存及HTTP最终30次同源读取。原答rationale仅“告”、建议reason仅“需”，正文不可用；结构/执行完成不能认作质量通过。NOT_PASSED及原答保留，沿既定后置决定不追加采样。此项不撤销已验证的入站、任务关联和保存/读取功能。

负责人2026-11-13再次明确“质量问题可以后续解决”。M01/M02、F01的反馈合理利用、F02的知识合理利用等模型正文质量项统一后置，不阻塞已验证的固定流程功能收口和新版发布；不再为它们追加模型采样。原答、失败及NOT_PASSED保持，不改成已修复。保存/读取错误、来源或成员串案、合同破坏等程序功能阻断仍需修复，不能归为正文质量后置。此前[后置决定](../../openspec/changes/archive/2026-11-11-ground-case-conclusions/scope-decision.md)与旧证据保留。

前期固定输入曾有明确的材料选择缺口；以下保留各批当时状态，相关程序修改现已随上述功能版发布，旧 Run 和失败不追认修复：原始日志很小，历史和执行台账却层层累积，04批C6在63,262字符超限前未派发。按负责人要求，先定义模型目标、禁止原始结构整包透传；[字段梳理](../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md)已完成，查询只给结果及 A/I/C3 字段筛选已本地修改并离线核验；I 当前3,047字符，原冻结 C3 仍7,680字符，成员归属/原文/原引用保持。C3 的有效 I 整体结论引用保留遗漏已按独审补齐并定向复验。完整 JSON 的新导入切片及 C3/Deep/C6 已识别知识正文投影已本地修复，[新导入离线预览](../operations/evidence/model-input-selection-20261112-05/README.md)6,930字符；没有实际导入、索引或模型调用，旧两段仍保留，不能当旧 Run 已修复。未知结构保持；[Deep/C6 整理](../operations/evidence/model-input-selection-20261112-06/README.md)已本地按指定问题/全案结论筛选，正文8,768/14,080字符，必要前序支持/反证保持。旧知识切片仍在本批冻结输入中，未手工拼接；离线重建不代表真实 C6 超限或模型质量已经通过。HTTP 字段/数据库表不变，不手工拼文档；输入变短不证明M01/F02已修复，不继续采样追求通过。

前批[固定05批](../operations/evidence/fixed-investigation-20261112-05/README.md)已实际导入/索引完整AN0846，C2两用途返回并合并一份正文进入C3/Deep/C6；行为性质问题的知识引用保存GET一致。C6正文18,563字符未再超限，但两次建议均重复N6_S9，拒收符合原答；C3仍错误使用案件外历史目录。I虽通过引用校验，仍忽略已给登录事实；模型凭名称推自动化流程的问题保留。Result rejected/partial/null且未采用，F02/M01/M02不核销。随后[离线修正](../operations/evidence/case-citation-input-20261113-01/README.md)按条筛历史并明确案件外范围；被I明确引用的N3_S238仍保留，只移除2条无依赖目录。局部纠错给字段原值、重复号和错配主体，C3/C6反馈949/467字符；原答仍拒收，70份旧文件不变。3项已有检查及限定独审通过，零新模型/数据库调用，实际纠错效果仍未验；不以缩短输入追认质量。

[固定06批三例对照](../operations/evidence/fixed-investigation-20261113-06/comparison.md)完成13次真实模型调用，均rejected/unavailable/partial且未采用。H01/H02人工原文/范围进入模型并被归因，H02未扩成全案授权；其模拟声明不能证明正常有效授权采纳。三例仍凭名称推自动化，H02正文夸大为完整行为链，M01/M02保持NOT_PASSED并停止采样。H01不可用基线却回答unchanged，生成/诊断缺口已离线修正；原拒收及当前判断为空保持，新提示真实效果未验。全部请求/原答/失败及读取快照可重放。三例知识嵌入均503，正常知识参与本批未验；预算未耗尽，不扩大预算。

06批的C3观察装配容量缺口已由[本轮程序修复](../operations/evidence/case-observation-input-20261113-01/README.md)处理：同记录/字段/同值共享展示，27来源及原值不变，1822→984；B01第2答仅新v2离线预览通过，旧v1拒收和真实Run保持。C6四份影响段缺成员依据仍拒收，当时仅离线聚焦字段/主张/候选，真实纠错效果另见07批。5项直接检查及一条隔离库替身保存读取通过不构成模型质量通过；不以连续采样处理已登记正文问题。

前批[固定07批](../operations/evidence/fixed-investigation-20261113-07/README.md)只新增一轮：原H01/A/I复用，正常知识448字符进入实际C3/C6，3次生成、41,320tokens。C6一次局部反馈后收窄影响成员，accepted/uncertain/partial并保存/GET一致；原首答拒收保持。这证明本次纠错及存取生效，不证明稳定质量；知识未被结构化引用、名称推自动化及未查写查空仍存在，不继续采样。不可比却写与历史一致的职责缺口已改为[新请求固定装配](../operations/evidence/case-fixed-comparison-20261113-01/README.md)，4项直接检查及1条隔离库替身存取通过，旧原答/采用记录不回写。该批当时模型修改尚未部署，现已随核心及独立 HTTP 功能版发布；F01/F02/M01整体仍未通过。

[按任务选择C3/C6输入](../operations/evidence/case-task-input-20261113-01/README.md)的离线实现已通过限定核验；随后[08批真实两例](../operations/evidence/fixed-investigation-20261113-08/README.md)实际使用各自新C3有效片段进入C6。B01接受待复核并采用；H01最终拒收且当前判断未覆盖，保留的B01已标为stale/human_feedback_changed。H回应了不同来源IP、启动/完成及反馈非授权等边界，名称推自动化仍存在；B01 C3/C6、H01 C3引用知识，但F01/F02/M01仍NOT_PASSED。9次生成后停止采样，预算未增加，原答与失败保持。

H01暴露实际程序缺口：N5_S87同文历史背景与N5_S94指定基线共用显示，接收只认后者，且首份纠错漏报指定基线缺失。按[第24节](../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md#24-指定比较引用与同文背景短号的职责区分)已明确输入职责及v9字段反馈；原记录/严格接收保持，两项直接检查及实际原答离线核对通过，不把H01拒收改成通过。随后[09批](../operations/evidence/fixed-investigation-20261113-09/README.md)一次新Run/4次生成，C6首答引用指定基线，v9一次重复引用纠错后accepted/uncertain/partial并采用，新鲜度current。实际未出现同文背景别名或缺基线诊断，这些分支仍只有离线证据；4次ASGI与保存一致，137份08文件保持。比较正文仍无依据地宣称本轮更充分，质量NOT_PASSED，不再采样。随后[第25节离线修复](../operations/evidence/case-deep-knowledge-20261113-01/README.md)为授权Deep增加配置化问题用途限制，不默认追加可选知识，必要前序依赖仍恢复。09实际输入重建11,921→11,235字符，105条其他记录/26依赖和55份原件保持；1项直接检查通过，0新模型/数据库调用。只解决本问题的可选知识选入，不代表F02合理使用通过。随后[第26节C6修复](../operations/evidence/case-final-knowledge-20261113-01/README.md)保留问题/用途/成员配对，避免跨问题拼接；授权单问题不选可选卡，有其他匹配问题或前序依赖仍保留。1项直接检查通过，09完整C6请求仍13,526字符/105记录/52依赖、有用知识保留，82份旧件不变；无新模型/数据库调用、未重验正文效果，其他正文错误继续后置，流式不前移。

## 待完成事项

| 编号 | 问题及影响 | 当前处理与验收落点 |
| --- | --- | --- |
| M01 | 模型扩大正文事实，结构合法不保证主张有据 | 质量 NOT_PASSED。程序覆盖和观察原值装配已直接验证；第五批命令结果边界改善；Deep 仍凭 synthetic 标签断言非生产环境，C6 替代解释将四项未查询也说成查空，两项已保存读回。另有时间间隔计算错误；固定 coverage 正确不代表其他正文正确；见[当前验收](../../openspec/changes/archive/2026-11-11-ground-case-conclusions/validation.md) |
| M01-A | 模型将 synthetic 等来源标签推成业务环境/良恶性事实 | **已知、后置，未修复**。第五批 Deep 原答及保存 GET 可复现；只应据对应业务材料或明确归属的人工陈述判断环境。按负责人决定不阻塞发布/后续功能，原质量结论保持；[10批](../operations/evidence/fixed-investigation-20261113-10/quality.json)仍从名称/标签推自动化特征，按原决定保留正文质量未通过、不追加采样 |
| M01-B | 模型自由正文将未查询写成查空 | **已知、后置，未修复**。第五批 C6 F1 替代解释与程序 coverage 的 2 查空/4 未查矛盾；原字段/原答保留，真实状态以程序回执为据。07批再次出现未查询威胁情报写成无结果，原答保持，按已确认决定不重复采样 |
| M02 | 角色引用合规与正文有据需分开持续验收 | 当前NOT_PASSED。历史各次拒收/接受及回执保留；[07批](../operations/evidence/fixed-investigation-20261113-07/README.md)一次C6局部反馈后将影响范围从A1/A2/A3收窄为A1/A3，支持引用不变，结构及引用接受并落库。但名称推自动化、未查写查空、错误比较说明仍在，接受不代表主张真实或稳定；比较固定装配的程序修复见F07 |
| F01 | H 后再次调查的传递已验证，正确利用反馈及有据结论仍未通过 | 本轮真实 HTTP 的第 2 修订进入后轮冻结及 4 份实际请求 body，后轮承认人工不是业务授权、命令结果未知；只证明本批部分利用，完整语义质量未通过。07批进一步复用H01得到accepted/uncertain/partial并保存读回，但完整语义质量仍未通过。前批修订及错误原答保留，不核销3.7 |
| F02 | 知识传递已验证，召回相关性及合理使用效果未通过 | 历史知识本地 C2 9 查询/10 行，历史卡 2 命中/1 唯一卡，5 份请求可见原分诊/人工正文及独立角色；结构化引用数组未引用历史，部分正文有提及，登录主题也命中进程卡，合理使用未证明。技术解释/方法前批证据保留；生产实际接线见根 PROGRESS。graph、自动消费和方法推动取证仍未验。[知识筛选改进](../../openspec/changes/archive/2026-11-12-refine-purpose-aware-knowledge-use/tasks.md)已实施并发布 21 r3；新批次 9 查询／5 行（3 唯一块），排除 6 次条件冲突和 2 次过期卡候选，合并 2 次跨目的正文。6 模型后 C6 仍拒收；被接受结果未结构化引用知识，合理使用质量仍未通过，不核销本项。[历史知识验收](../../openspec/changes/archive/2026-11-12-use-historical-alert-knowledge/validation.md) 本地固定流程进一步修正辅助知识范围/覆盖与同出处选取，已有历史引用保存读回；C6 建议空引用拒收，Schema 随后补齐，不追认原答。07批正常检索并向三个实际请求各提供一张448字符卡，原答未结构化引用知识，合理使用仍未证明。见[本批验证](../../openspec/changes/complete-socai2-investigation-chain/fixed-flow-validation-20261112.md)。 |
| O01 | 自动消费者暂停；恢复后的实际消费、自动分诊和建案未验收 | 本批不启动消费者；按已有服务范围单独核验，健康探针不证明处理成功 |
| W01 | Case/H 产品页面操作仍需接线验收 | 本地 13 次原 HTTP 请求及后轮版本/结果比对通过；21 r2 写入口已开放，正常登录后 8 次业务请求及任务字段匹配通过。服务端范围见 R08，产品页面操作仍未验收，不用 4177 代替 |
| P01 | 事件概览缺本次诊断入口 | 对应 J04；由成员主体及 Run UUID 打开实际诊断尝试，失败也可查 |
| P02 | 原页面 `severity_effective=medium` 显示错误 | 对应 F06；应显示“中”，保留来源为人工覆盖或成员最高值 |
| P03 | 原运行页把 `delivery_state=none` 与字段缺失混为一类 | 对应 F15；已记录 none 显示未交付，缺失按未知处理 |
| P04 | 无效告警 ID 缺明确未找到及返回入口 | 对应 J01；404 应终止下钻并允许返回 |
| P05 | 真实响应等仍有缺口；同主机近期展示E71已交付；普通案件故事E65、案件候选E66和探索保存E67–E69和相似历史复核E70已交付；文件上传/下载由业务后端负责 | 普通评论E58/E59已交付；[附件引用E60–E62](../../openspec/changes/archive/2026-11-13-link-case-attachments/validation.md)已完成F24-02/03中本服务负责的关联登记/目录/单项，业务后端文件链路未据此验收。F20非对话读取由E65完成，AI对话暂缓；E66完成F25候选查询及明确加入衔接，F25保存恢复已完成本服务HTTP能力；F27真实响应仍未完成；响应只以真实审批／动作／回执为据 |
| Q01 | 各页面AI对话暂缓（未实现） | 2026-11-13负责人明确暂缓助手入口、提问/追问、会话历史、回答读取及保存；E19/E20仍返回501。告警分诊、事件诊断、Case调查按原计划推进；E21只采用符合资格的既有基础调查结果，已交付状态保持 |
| Q02 | 人工采用核心与HTTP已交付；流式/自动反馈重算仍后置 | E63预览、E21采用、E64历史复用[AD01–AD06](result-adoption-and-pending-work.md)，本机20HTTP/SQL和21已有数据只读通过；[发布证据](../../openspec/changes/archive/2026-11-13-adopt-investigation-results/validation.md)。采用不结束任务、Run或案件；0模型、无迁移。21未做生产采用写验收；并发矩阵和流式不在本批范围 |

四项 P01–P04 是已保存的产品页面核对结论；4177 内部工作台的节点详情优化不核销这些产品页面事项。[功能与跳转清单](../../deliverables/investigation-validation-20261106/frontend-feature-list.md) · [原始页面证据](investigation-test-handoff-20261106.md#下一阶段的前后端交接验收)

审计基线、各批原答、校验、采用和读回关系分别保留。第五批执行 completed/交付 partial、C6 uncertain/accepted 并采用，不等于正文已经核实：原正文独审为 REVISE；负责人后置决定后的程序交付补充审查为 ACCEPT。第四批 rejected 原件保持，不改写采用/失败历史。

## 保留模块启用前的问题

以下属于 `services/agents` 的 Hunt，不是当前 `socai2` A/I/C/H 的执行链；生产暴露和真实多租户数据未在本轮验证。按该模块启用范围处理，不单开主线权限专项。

| 编号 | 问题及影响 | 修复与验收 |
| --- | --- | --- |
| A03 | Hunt 路由只执行认证，不消费 principal 的租户，读取与手动调度落到 default | 隔离真实 ASGI 复现两租户均用 default；从认证结果显式绑定目标并传入读写/执行，不能缺失回退；验收两个租户的下游目标匹配 |
| A04 | Hunt 数据湖失败变空列表，返回 ok=true，生成 completed/零行/error=null 的落库参数 | 隔离真实 loader→scheduler→engine→store 复现；保留采集失败/错误到接口和 Run，用正常零行与超时各一例直接验收 |

详细行号、触发、证据及限制见[独立流程审查](../handoff/history/2026-11-14-investigation-cleanup/documents/docs/investigation/investigation-flow-review-20261111.md)。Swarm/Debate 的确定性评分与模拟 token 未证实接入目标路径，按保留模块说明，不认定主线模拟冒充真实。

## 已修正并复验

2026-11-18 D5c本步：C5容量失败原会中断且C6重复建图，现仅接收明确容量失败、保存失败回执、无可用图时不回旧图，C6有效正文/Result在21保存读回。首次C1快速失败暴露本机完成时钟早于21开始时刻，原拒绝和观察收尾保留；窄修后新任务受控-10秒时钟验证数据库观察时间自动收尾，原回执/失败原因及旧7类终态记录不变，槽0。62项直接检查及限定独审通过，详见[D5c回执](../operations/evidence/local-dependency-d5c-20261118-01/README.md)。这不核销网络中断/unknown或历史模型质量。

| 编号 | 发现与修正 | 证据 |
| --- | --- | --- |
| K01 | 新分诊保存后未接知识维护 | [分诊后同步](../../openspec/changes/archive/2026-11-12-sync-saved-alert-knowledge/validation.md)已完成本地 finish→索引→检索→GET、独审及 r5 实际加载，原判断／同步回执分开；生产无新增 Run。人工反馈自动触发和历史回填未纳入，消费者保持关闭 |
| K02 | 固定06批知识503保留；新批正常查询已通过 | 原三Run集合GET200/嵌入POST503及旧诊断不变。[新批复核](../operations/evidence/knowledge-retrieval-recovery-20261113-01/README.md)发现当前本机转发缺失；按原配置临时转发后一次嵌入和9条查询成功，两个用途返回同一知识，现有程序在C3/Deep/C6各选448字符正文。当前缺转发不能倒推旧503根因；临时转发已关闭，后续Run须保持对应连接。该查询批无生成调用/写库；后续07批在整个Run保持连接，正常检索并进入实际请求，但原答未结构化引用知识，F02继续未通过 |
| R08 | Case/H HTTP 共用只读连接，正常写入未接通 | 本轮显式写连接及来源配置已上线 r2，原 GET 保持；本地正常两轮/H 修订传递与生产正常登录写读通过，无表列或告警字段变更。[交付回执](../operations/evidence/case-human-http-20261111-01/delivery-summary.json)；产品页面仍列 W01 |
| A02 | C3 提示最多两项补查，但生成/接收曾允许 12 项 | 当前冻结配置、生成/接收/partial 均限 2，三项明确拒收且零派发，历史读取和 C6 建议兼容；直接检查通过，21 r1 实际加载上限 2，发布读回通过。[本次交付](../operations/evidence/case-grounding-20261111-01/delivery-summary.json)。原审计反例保持 |
| R01 | Case/H GET 共用关闭的写开关而 503；GET 现在接受页面读取开关，写操作仍受原开关约束 | 当前两案 365 GET、16,820 检查；读取开关／租户／权限与写入拒绝定向测试 |
| R02 | 安装核验器拒绝已经人工授权的 `aisoc_app` schema USAGE | 改为核实获准 SELECT、无调查写权限及无管理权限；实际 verify 通过，未执行 GRANT 或 DDL |
| R03 | 对账脚本只在本 Case 计算相关告警，遗漏同租户跨 Case 的合法结果 | 从同一只读快照读取匹配对象及当前材料，按类型／命名空间／对象键核对关联，复验零偏差 |
| R04 | 交接文档仍显示未部署／缺权限，OpenAPI 缺来源工件、活动及事件交付字段 | 当前入口、字段与接口导出统一更新；整理前文档归档，原失败／unknown／模型原答保持 |
| R05 | Deep/C6 生成 Schema 允许接收校验禁止的执行回执结论引用 | Deep 支持／反证及 C6 结论／比较／影响／建议的枚举排除执行回执；C6 analysis 保留查询覆盖引用。20 项边界检查、5 份原答离线复验通过；真实生成效果列 M02 |
| R06 | 核验器假定当前判断非空、Case／活动仅属于单案 | 支持空判断并拒绝伪造判断；按同租户完整主体关系核 Case、活动及 `via_member_alert`，补 H 详情和全部修订逐值核对。16,820 检查及独立活动 1,083 检查通过 |
| R07 | 4177 点击节点只能跳到下方原件，Deep 无动作时缺实际失败模型入口；展示源码变化不能刷新已有缓存 | 左侧流程／右侧详情已接通提示词、输入输出、错误和原件；Deep 每次实际调用可选，冻结输入分类经独审修正。30 项定向测试、307 条记录逐值保持及浏览器宽窄屏核验通过。见[节点详情验收](../handoff/history/2026-11-14-investigation-cleanup/documents/openspec/changes/complete-socai2-investigation-chain/workbench-node-inspector-20261110.md) |
| F03 | 分别保留查询出处与历史行主体，修正 C02 A3 查询中 A1 记录的引用范围 | C3／Deep／C6、冻结依赖恢复及案件外／冲突身份直接检查通过，原路径／角色／正文保持；[本轮验收](../../openspec/changes/archive/2026-11-10-fix-case-evidence-scope-and-recovery/validation.md) |
| F04 | 来源可见性、成员覆盖、C6 本次 finding 及 conclusion／impact 覆盖可定位错误获得一次具体反馈 | PG 已验证纠正成功与仍错时部分保留，前批真实 C6 已发生一次纠正；unknown／截断不重派。本轮补角色诊断见 F06，剩余正文问题见 M01 |
| F05 | Deep handoff 生成允许空答复、网关分支丢公共必填项，与接收合同不一致 | 每个 action／Answer 分支展开完整结构与限制；真实第三轮 handoff／answer 均完整通过，前两轮原失败保留；[69 项直接检查](../operations/evidence/case-scope-recovery-20261110-01/final-contract-tests.xml) |
| F06 | C3/C6 Finding 生成与接收的角色约束不一致，有限反馈遗漏角色错误 | 已统一部署并核来源：完整状态分支限制直接观察、v2 反馈给角色与逐成员缺口；86 项检查、两项 PG 流程和一轮真实生成通过该范围，原接收兼容性及历史原件保持。[角色验收](../../openspec/changes/archive/2026-11-10-align-case-finding-evidence-roles/validation.md)；独审 ACCEPT，21 r6 生产读回通过 |
| F07 | 不可用历史的比较说明曾由模型生成，与程序已知事实冲突 | [固定装配修复](../operations/evidence/case-fixed-comparison-20261113-01/README.md)在新C6请求前冻结initial/not_comparable和固定说明，移除模型输出槽，装配后保存GET一致；可用指定历史仍由模型比较。4项直接检查及1条隔离库替身存取通过，旧无标记原答/Result不变。修复当时仅本地验证，现已随核心及独立 HTTP 功能版发布；未为该分支追加采样，不追认07批错误比较正文 |

本次 Case/H 结果见 [HTTP 功能验收](../../openspec/changes/archive/2026-11-11-enable-case-human-http-flow/validation.md)；前序结果见[程序功能验收](../../openspec/changes/archive/2026-11-11-ground-case-conclusions/validation.md)及[交付回执](../operations/evidence/case-grounding-20261111-01/delivery-summary.json)。r6 参照批次见[角色验收](../../openspec/changes/archive/2026-11-10-align-case-finding-evidence-roles/validation.md)与[逐调用汇总](../operations/evidence/case-evidence-roles-20261110-01/execution-summary.json)。前批来源范围及纠正修复见[验收报告](../../openspec/changes/archive/2026-11-10-fix-case-evidence-scope-and-recovery/validation.md)；原[Case 流程实测](../handoff/history/2026-11-14-investigation-cleanup/documents/openspec/changes/complete-socai2-investigation-chain/case-current-flow-20261110.md)和生产原答继续保留。
