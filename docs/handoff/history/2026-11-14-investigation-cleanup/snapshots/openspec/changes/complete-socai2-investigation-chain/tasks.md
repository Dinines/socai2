> 历史资料：本文件保留原批次的设计、执行或评审结论，不代表当前状态或新增授权。原路径：`openspec/changes/complete-socai2-investigation-chain/tasks.md`。当前入口见[PROGRESS](../../../../../../../../PROGRESS.md)，迁移位置见[归档索引](../../../../README.md)。

# 当前任务

主调查 **31/41**，保留全部编号与原勾选状态。当前程序功能交付不代表主调查整体验收；交付及问题分别见 [PROGRESS](../../../../../../../../PROGRESS.md)、[问题清单](../../../../../../../investigation/current-issues.md)。

负责人2026-11-13确认质量问题后续解决：3.7/3.10/3.14/3.16/3.23/3.30中模型正文准确性、反馈/知识合理利用等质量部分保留未通过，退出本次固定流程发布门槛；对应程序输入、引用范围、装配及保存读取仍按已验证证据验收。自动消费、流式、对话等未实施功能继续单列，主31/41不是本阶段功能发布的阻塞，不据后置虚勾整体任务。

当前已按负责人要求发布[固定调查功能版](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/fixed-flow-release-20261113.md)：复用10批和限定独审，核心API/显式处理入口已更新并生产只读核对；外部71操作与Swagger已由[接口同步change](../../../../../../../../openspec/changes/archive/2026-11-13-sync-published-investigation-http/validation.md)完成两端发布及读回；核心发布批次未修改18024，接续同步保持原合同、无新增模型采样，不提交/推送Git；发布限定审计和回执见本阶段任务，不改变主31/41。

2026-11-13 已按当前代码与发布证据整理[实际功能缺口](../../../../../../../investigation/current-issues.md#当前功能缺口与实施入口)。下一阶段复用[流式更新任务](../../../../../../../../openspec/changes/schedule-streaming-investigation-updates/tasks.md)：先统一队列/领取保护，再接更新触发与成员跟随，再补 H 的 C6-only，最后知识异步维护及接口交接；固定输入/保存读取不重做，主任务不因计划更新而虚勾。

当前[第32节](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md#32-c3业务判断与程序覆盖记录分工)已本地实现C3五项业务判断、程序补coverage及原六问存取；7项定向场景通过。[10批一个最新固定Run](../../../../../../../operations/evidence/fixed-investigation-20261113-10/README.md)复用原A/I/事件/H，5次生成后C6一次纠错accepted/uncertain/partial并采用，4次ASGI/SQL读回一致。影响Deep拒收及原答/旧行保持，两端4177只保留最新批，正文质量NOT_PASSED、HTTP/表不变；10批验收当时未发布，随后已完成上述核心及HTTP同步，流式后置。[限定独审通过](../../../../../../../operations/evidence/fixed-investigation-20261113-10/audit.md)；主31/41不核销。

前批[第31节](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md#31-i前序判断中的空项与程序标记)已完成I前序材料的未引用空限制来源与精确程序标记筛选；[两项既有检查、四份完整输入离线重建及限定独审](../../../../../../../operations/evidence/case-incident-context-20261113-01/README.md)通过。原答/失败、业务限制、原范围、必要引用及124份旧件保持，未新增模型或存取验收。

前批[第30节](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md#30-有结果的背景查询只提供业务记录)已完成按工具与精确字段路径整理非空背景返回，保留必要业务事实与原引用。[一项直接检查、冻结完整输入和明确合成正结果预览](../../../../../../../operations/evidence/case-query-results-20261113-01/README.md)及限定独审通过，检查/脚本失败原件与113份旧件保留；未新增模型或存取验收，主任务状态保持。

本轮[第29节](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md#29-工具只向模型提供任务所需的业务内容)已清理C3/Deep/C6完整消息中的工具台账，保留短结果、业务值、必要候选及引用。[两项既有检查、四份完整输入重建及限定独审](../../../../../../../operations/evidence/case-tool-input-20261113-01/README.md)通过；113份原件/原答保持，零新模型/数据库调用。HTTP/表/输出Schema保持，4177仍只留最新已执行批次；主31/41、质量NOT_PASSED、流式后置不变。

前批[第28节](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md#28-当前采用判断的原成员范围)已补当前采用判断的原成员范围，沿C3/Deep/C6保留，当前引用仍只归属原范围与本案交集。[一项既有检查和四份已存请求离线核对](../../../../../../../operations/evidence/case-assessment-scope-20261113-01/README.md)及限定独审完成；原文、H依据、前序依赖、目标及69份前批文件保持。首次测试断言错误保留，修正及标题补齐后同项通过；零新模型/数据库调用，不改HTTP/表，主任务未核销。

前批[第27节](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md#27-c6指定比较基线的必要判断内容)已完成C6指定基线原发现/未决问题/影响边界的选择、09冻结预览及[一条替身模型/真实PG保存读取](../../../../../../../operations/evidence/case-comparison-basis-20261113-01/README.md)，限定独审通过。1项既有检查通过，原答/失败保持，0新真实模型；PG用例未显式关联事件，不作为新增完整A/I→Case验收。4177随后按负责人要求只留该最新批次，原展示已备份；不核销主任务。

当前3.12子范围已按[固定结果人工采用](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/result-adoption.md)完成核心预览/资格、幂等保存、判断历史读取和[单Case隔离PG流程](../../../../../../../operations/evidence/case-result-adoption-20261113-01/README.md)。未完任务/Run保持，旧Run不覆盖较新人工采用，后来显式启动Run按原规则自动采用，H后stale且无自动执行。脚本状态断言失败保留，按同Case回执续验通过；核心批0模型/HTTP，无迁移。随后[本机三个HTTP适配](../../../../../../../operations/evidence/case-result-adoption-http-20261113-01/README.md)已20请求/SQL及限定独审通过；正式发布与Swagger由[独立采用change](../../../../../../../../openspec/changes/archive/2026-11-13-adopt-investigation-results/validation.md)交付，不重复测试或提前勾主任务。

已完成[第26节C6知识选择](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md#26-c6知识与待核问题的对应)的[本地程序及离线核验](../../../../../../../operations/evidence/case-final-knowledge-20261113-01/README.md)：同一待核问题内匹配用途/成员，仅授权不独立选可选卡，必要依赖恢复。1项既有检查一次通过；09完整请求仍13,526字符，105条记录/52依赖及知识卡保持，82份旧件不变。重建脚本字段顺序/round缺失失败保留并定向修正。零新模型/数据库调用，不改已答计算、HTTP/表/输出或旧答，修后未派发，主任务不核销。

已完成[第25节Deep授权知识选择](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md#25-deep授权问题的可选知识)的[本地实现及离线预览](../../../../../../../operations/evidence/case-deep-knowledge-20261113-01/README.md)：授权问题不默认追加可选知识，前序明确依赖仍恢复。1项既有检查通过；09实际输入程序重建11,921→11,235字符，仅去除无引用依赖的可选卡，105条其他记录/26依赖及55份09原件保持。零新模型/数据库调用，不改HTTP/表、C3/C6、原答及流式；修后未派发，质量未追认，不核销3.14/3.30。随后C6限定修复见上。

已按[09批计划](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/fixed-flow-plan.md#比较引用修复的一次真实核验2026-11-13)完成[一次真实固定Run](../../../../../../../operations/evidence/fixed-investigation-20261113-09/README.md)：复用08 Case/H/A/I及已接受B01基线，4次生成。C6首答引用指定基线，一次v9纠错后接受待复核并采用，新鲜度current；4次ASGI读回及请求/原答一致，137份08文件保持。未触发同文背景别名和缺基线诊断，不扩大真实通过范围；正文质量NOT_PASSED。本机静态84，未加单测/新业务实现/HTTP或表变更。其后Deep授权知识的限定修复见上，流式后置。

已完成[08批两例真实核验及实际缺口小修](../../../../../../../operations/evidence/fixed-investigation-20261113-08/README.md)：两Run/9次生成，B01接受并采用，H01最终拒收、当前判断未覆盖；各自新C3有效片段进入C6，原件与7次ASGI读回一致。第24节明确指定比较基线与同文背景短号的职责，并补一次纠错中的基线/当前依据诊断；两项不同直接检查、真实原答离线重放及[限定独审](../../../../../../../operations/evidence/fixed-investigation-20261113-08/audit.md)完成，08批结束时新预览未派发，随后09实测见上。正文质量NOT_PASSED、原拒收保持，本机静态83；未改HTTP/表/采用合同、不发布、流式后置，主任务不核销。

2026-11-13 前批输入选择：按[第23节](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md#23-按判断目标选择c3c6材料)完成[任务导向的C3/C6材料选择](../../../../../../../operations/evidence/case-task-input-20261113-01/README.md)：C3形成初步解释/必要补查，C6复核证据并形成综合结论；移出无判断内容的历史、非必要I总览及后台字段，C6不默认叠加A/I历史和C3成员/领域矩阵，所需支持/反证按冻结依赖恢复。无C3回退、独立人工/历史业务记录和未知值保持。5项不同直接检查及87份前批原件/68条成员事实核对完成，[限定独审](../../../../../../../operations/evidence/case-task-input-20261113-01/audit.md)通过，新C3/C6仅离线输入预览；未调用模型或数据库、未改旧原答。07批真实接受/采用及质量NOT_PASSED、固定比较程序修复证据仍保留。本机静态81份；对应3.10/3.30限定范围，未核销3.16/F02/M01或31/41，HTTP/表/输出合同不变，模型未部署、流式后置。

本地续修 A/I 一次引用纠正、C6 缺依据反馈、同一历史记录的程序展示去重及配置 Case 实际消息检查；固定原件、原答和失败不改写。[验证记录](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/fixed-flow-validation-20261112.md)分别说明替身保存/采用验证、真实模型和 GET 读回，未以输入可用或代码完成核销整体质量与本任务树。

本轮已完成[字段梳理第18节](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md#18-离线修正历史选择与引用反馈)和[离线回执/独审](../../../../../../../operations/evidence/case-citation-input-20261113-01/README.md)：C3单条历史选择与案件外分组、C3/C6错误字段反馈。3项已有检查通过，角色键补充后仅定向复验历史选择；原件70份不变，103条保留记录/引用逐值保持，旧原答继续拒收。未调用模型/数据库/网络，不部署、不改HTTP/表合同；对应3.10/3.23/3.30限定子范围，主任务计数和质量未通过保持。

负责人进一步明确：先说明模型任务，再选择有用字段，禁止原始数据整包透传；查询只给结果。长期规则已写入 AGENTS，具体[字段梳理](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md)覆盖 A/I/C3/Deep/C6。查询结果展示已本地修改、离线重建并通过限定静态独审；对象、历史、知识等后续字段选择按表逐项实施，不把梳理完成写成全部代码已生效，不增加模型采样。

当前按负责人“逐步整理每次模型输入”顺序，[A 输入业务字段](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md#10-按环节实施先整理-a)及[I 成员事实/有效 A/必要历史](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md#11-i按事件诊断整理成员和历史)已本地实施并离线重建。I 当前3,047字符/71行，8项直接检查通过；[第12节 C3](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md#12-c3首轮调查的事实前序判断与知识)已本地实施，正文7,680字符/102来源，6项直接检查通过，I 整体依赖遗漏经独审修正并定向2项通过。第13节完整 JSON 新导入分块及 C3/Deep/C6 的知识正文投影已本地实施，5项不同直接检查通过，独审数值缺口修复后定向2项及限定复核通过；样例业务正文448字符，新导入离线 C3 预览6,930字符，原冻结 C3 仍7,680字符。HTTP 字段合同/数据库表不变，新导入分块数量可能变化，旧数据不重写；该离线批未实际导入、索引或派发模型，后续固定05批的实际结果见上文。第14/15节 Deep/C6 已本地按任务筛选，完整输入8,768/14,080字符、原文和必要依赖保持；7项不同直接检查及限定独审通过。不新增真实模型调用。局部完成不勾选主调查未完项。

按[后续工作顺序](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/design.md#后续工作顺序)推进：有据结论程序范围与 [Case/H 正常 HTTP 操作](../../../../../../../../openspec/changes/archive/2026-11-11-enable-case-human-http-flow/tasks.md)已统一发布，M01-A/M01-B 按负责人决定后置、质量 NOT_PASSED 保持。当前按[知识使用位置](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/design.md#知识库使用位置与本地嵌入)完成本地 C2 检索→C3 输入/引用→Deep/C6 复用，21 r3 已统一发布并读回；知识合理使用质量仍单列；A/I 与动态补检索不扩入首项。[历史告警知识](../../../../../../../../openspec/changes/archive/2026-11-12-use-historical-alert-knowledge/tasks.md)已补齐 C2 历史参考及模型传递，并完成 21 发布读回；该 change 已归档并推送；后续 [refine-purpose-aware-knowledge-use](../../../../../../../../openspec/changes/archive/2026-11-12-refine-purpose-aware-knowledge-use/tasks.md)已交付用途筛选、模型去重／选择及历史选入更新，经一次直接流程和独审后发布 `v1.2-20261112-r3`，知识写读及 4177 已核验，质量仍未通过。[分诊后知识同步](../../../../../../../../openspec/changes/archive/2026-11-12-sync-saved-alert-knowledge/tasks.md)已完成本地直接验收、独审及 r5 实际加载读回，不改变主调查完成计数。页面数据对应、自动处理继续保留。每项只做改动相关检查和一条代表性完整路径，证据跨关联主任务复用；不重复 56 项审查或开展可用性矩阵，一个 change 统一发布/推送。

本轮另按负责人要求完成[HTTP功能直接验证与后续规划](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/http-functional-validation-20261112.md)：本机原路由/真实隔离库31项检查通过，43操作有回执，模型替身不核销真实质量。随后复用[serve-investigation-api](../../../../../../../../openspec/changes/archive/2026-11-12-serve-investigation-api/tasks.md)完成独立入口：21:18024统一43操作并接正式aisoc，本机与21各9次TCP Case/H及SQL读回一致，旧服务保持。对应3.12的入口子项，不勾整体。随后[manage-investigation-cases](../../../../../../../../openspec/changes/archive/2026-11-12-manage-investigation-cases/tasks.md)已完成E44–E47管理/结案/重开，本机与21各20次TCP和SQL读回通过、docs6同步；随后[manage-alert-incident-operations](../../../../../../../../openspec/changes/archive/2026-11-13-manage-alert-incident-operations/validation.md)完成E48–E53告警反馈及告警/事件单条、批量管理，两端各86次TCP及SQL逐值读回通过；当前53操作、docs7，原47合同不变。后续按[接口实施计划](../../../../../../../investigation/http-implementation-plan-20261112.md)继续补列表筛选/排序等，主任务计数保持。

## 尚未完成

按负责人关于大量工具返回的补充，第16节已本地实现：保留现有查询/请求容量边界，补普通查询字段按记录关联的共同值展示及内部身份筛选；1项已有字段检查及1项正常隔离库替身保存/读取流程通过，结果/当前评估GET一致。[07批证据](../../../../../../../operations/evidence/model-input-selection-20261112-07/README.md)明确区分合成预览、实际替身请求、accepted/partial结果与前置脚本失败；不新增翻页、模型摘要或压力测试，真实模型质量和旧失败不追认。

第14/15节已依次完成 Deep/C6 的本地程序筛选和[完整输入预览](../../../../../../../operations/evidence/model-input-selection-20261112-06/README.md)，7项不同直接检查通过；范围/引用补充定向复验及限定独审通过。该批没有新模型/数据库/HTTP调用；随后07批替身保存读取证据如上。固定05批已补实际导入与真实固定流程失败读回证据；07批补了一次接受并采用的C6保存读取，正文质量仍未通过，保持表结构及接口合同，不提前勾选以下整体任务。

- [ ] 3.7 完成正常 Kafka/Fusion→A/I/C→H→下一轮 C 的实际业务闭环，确认人工版本进入输入并影响依据或待核事项，结果保存后可读。已有链路和 H 传递证据复用；真实知识使用、完整结论质量及远端模型对照未验范围仍保留，对照不作为下一功能前置。
- [ ] 3.10 补齐 A/I/C3/Deep/C6 的结论依据、来源/范围、查询状态和效果边界。当前 Case 子范围由 ground-case-conclusions 处理审计 A01/A02；来源角色与有限纠正复用，A/I 其余范围仍保留，不随子 change 完成整项勾选。不另建通用语义评判或复杂测试框架。
- [ ] 3.12 完成当前 Case/H 正常操作和产品页面数据对应。F01–F28 的存储/读取与证据目录已验范围复用，实际 HTTP 写操作及 H 进入后轮已有限定证据，自动反馈复核另由流式 change 实施；P01–P04 产品页面非当前后端前置，4177 不代替产品页面；普通评论、附件引用及[E65案件故事](../../../../../../../../openspec/changes/archive/2026-11-13-query-case-story/validation.md)已独立交付，不核销本任务整体；[E66案件候选](../../../../../../../../openspec/changes/archive/2026-11-13-query-case-exploration-candidates/validation.md)已独立交付，[探索保存E67–E69](../../../../../../../../openspec/changes/archive/2026-11-13-save-case-exploration/validation.md)已独立交付，[E70相似历史复核](../../../../../../../../openspec/changes/archive/2026-11-13-query-alert-review-candidates/validation.md)已独立交付，[E71同主机近期查询](../../../../../../../../openspec/changes/archive/2026-11-13-query-alert-host-recency/validation.md)已独立交付，外部响应仍后置，Q对话按负责人要求暂缓。
- [ ] 3.14 由 [enable-purpose-aware-case-knowledge](../../../../../../../../openspec/changes/archive/2026-11-11-enable-purpose-aware-case-knowledge/tasks.md)接通 C2 按目标的本地嵌入检索、后续模型使用及 4177 展示，完成适用真实知识从既有导入/索引/检索入口进入调查并合理用于补查或解释。已有资产、SOP 和全文检索证据保留；查空或直接 seed 不代替实际使用，身份图/UEBA 等未验范围单列，不提前勾选整体任务。
- [ ] 3.16 核验加入实质人工材料后，必要事实、所选 H 版本、原计划及指定比较进入下一轮 C3/C6；可选历史不挤占必需输入。第19节已完成本地字段选择、H实际source_refs修复及[冻结C01离线预览](../../../../../../../operations/evidence/case-human-input-20261113-01/README.md)，2项直接检查通过；H字段补齐后仅定向复验1项，限定独审通过。随后[隔离库H保存读取](../../../../../../../operations/evidence/case-human-persistence-20261113-01/README.md)补齐C3/Deep/C6、指定基线、原计划与H/结果/当前判断读回，模型和查询全替身，限定独审通过；两次验证脚本问题保留，第二批仅只读补完余项，没有第三次流程。随后06批无H/核查H/限定模拟H三场景13次真实调用均拒收，H归因和范围有实际证据，完整结论质量与有效授权正向采纳仍未通过；07批复用H01及原A/I，C6一次纠错后接受并采用，完整质量仍未通过；不可用比较改由程序冻结装配并经直接检查/替身存取，旧边界保持。原文/范围/旧失败保持，不重派旧Run或提前勾选。
- [ ] 3.21 补齐自动处理的实际消费、分诊及应触发的后续业务。代码/镜像/配置来源、公共表读取及 Fusion 归并已有证据，网关超时已按当前策略修正；Agents 暂停，自动消费尚未验收，保留原位点与 unknown。必要接线随功能处理。
- [ ] 3.23 继续验收 A 的输入覆盖和正文依据，保留描述、人工正文、未知业务值、0/false/有效空列表。五字段映射与保存/读取已接入；历史截断、重复引用和语义问题仍保留，整体未核销，五字段不套用于 I/Case。
- [ ] 3.30 完成 Case C1/C3/Deep/C6 的实际结论质量与业务闭环。ground-case-conclusions 只交付当前 Deep/C6 依据与 C3 补查约束；来源范围/角色等已交付证据复用，实际知识与产品操作继续按 3.7/3.10/3.12/3.16 共用一条相应功能链的证据，不重复执行或提前勾选整体完成。
- [ ] 4.1 主调查实施达到范围后，由未参与实现者完成结束审计，修正实际阻塞，保留失败、unknown 和暂缓项。各独立 change 的限定审计不替代主调查审计。
- [ ] 4.2 主调查实施和审计达标后再同步规格并归档；当前仍未满足，不因本轮资料整理而勾选。

本轮固定流程的四项直接修复、一次真实 A/I→Case 和保存读回见[2026-11-12 验证](../../../../../../../../openspec/changes/complete-socai2-investigation-chain/fixed-flow-validation-20261112.md)。A2 修后仅离线重建，C6 建议 Schema 随拒收补齐；原 Result partial/rejected/null 保留。上述未完任务不因此勾选，流式继续后置。

## 已完成的限定范围

以下仅保留交付内容；原始任务描述、调用数量、历史失败和对应回执集中在[整理前任务记录](../../../../../2026-11-11-local-cleanup/investigation-change/tasks.md)，没有重新执行或扩大验收结论。

- [x] 1.1 归并后台、设计和预览到普通项目目录，保留迁移与备份记录。
- [x] 1.2 承接已确认调查表及独立数据库验证；当前表设计由字段字典和迁移 123–126 描述。
- [x] 1.3 承接 C 存储、C1–C6 手动执行及 Case HTTP/读取组件。
- [x] 1.4 承接 Fusion writer、Case 桥接和 A/I 冻结、发布及新鲜度读取。
- [x] 2.1 提供 Q 发送、保存和采用三个明确未实现的预留接口。
- [x] 2.2 核验 Q 占位响应、请求边界和无业务执行，导出 OpenAPI。
- [x] 2.3 同步调查范围、规格与实施记录；CLI 检查不代表功能完成。
- [x] 3.1 接通 A 基本查询/分诊，保存真实请求、返回、步骤、用量和解释。
- [x] 3.2 接通 I 事件诊断，保存成员范围、诊断、发现/待核及来源。
- [x] 3.3 完成告警/事件字段 DTO 和读取出口；产品页面交互另验。
- [x] 3.4 接通显式事件关联和成员移动，保持租户、命名空间、范围和历史。
- [x] 3.5 实现 H 任务/版本写读、冻结引用和显式 prepare，保存 H 不自动执行 C。
- [x] 3.6 接通必要外部来源适配，区分缺源、空结果、失败与不确定；替身验证不代表厂商实连。
- [x] 3.8 实现 C6 资源预留及必要输入容量处理，unknown 用量保持未知。
- [x] 3.9 接通直接 query 与问题级 Deep 分流、绑定和引用。
- [x] 3.11 提供 Case 集合、指标、筛选分页、判断覆盖和 H 历史读取。
- [x] 3.13 建立本机独立数据环境并验证数据路径，原环境/数据保留。
- [x] 3.15 C6 不因 C3 失败被直接阻断；系统收尾与业务判断分开，unknown 不追认成功。
- [x] 3.17 完成三组新增案例的本地链路与读取；原事实扩大问题及质量失败保留。
- [x] 3.18 完成正式数据的本机只读 profile 接入及限定读取验证。
- [x] 3.19 完成三条演练告警的 Fusion、Case 调查及读取；不代表模型整体质量通过。
- [x] 3.20 按明确授权补齐既有只读函数访问，并完成字段/关联核对。
- [x] 3.22 A/I 按有效结果区分交付完整性，待核与执行状态单列。
- [x] 3.24 4177 提供告警输入输出对比及实际原件入口。
- [x] 3.25 完成一次告警任务指令对照，未采用的退化方案及原结果保留。
- [x] 3.26 完成九份冻结材料的一轮告警测试及工作台整理，正文问题单列。
- [x] 3.27 完成事件结构模板和四块输出适配的限定离线验证。
- [x] 3.28 完成事件候选的一次真实模型调用及输入/输出展示。
- [x] 3.29 完成事件输入输出接入、字段兼容、保存/读取及发布，正文质量问题保留。
- [x] 3.31 完成当前流程发布、功能/表字段/API 交接及远端/父项目同步。
- [x] 3.32 完成 4177 左侧流程与右侧节点详情，实际提示词、输入输出、错误和空态可查。

## 直接证据入口

- [当前程序功能交付](../../../../../../../../openspec/changes/archive/2026-11-11-ground-case-conclusions/validation.md)、[Case 来源范围与纠正](../../../../../../../../openspec/changes/archive/2026-11-10-fix-case-evidence-scope-and-recovery/validation.md)、[Finding 角色参照批次](../../../../../../../../openspec/changes/archive/2026-11-10-align-case-finding-evidence-roles/validation.md)。
- [Case 实际流程与 H 传递](../../../../documents/openspec/changes/complete-socai2-investigation-chain/case-current-flow-20261110.md)、[发布与交接核验](../../../../documents/openspec/changes/complete-socai2-investigation-chain/release-current-20261110.md)、[4177 节点详情](../../../../documents/openspec/changes/complete-socai2-investigation-chain/workbench-node-inspector-20261110.md)。
- [事件接入](../../../../evidence/incident-boundary-integration-20261108-01/summary.json)、[字段及模型交接](../../../../../../../../FRONTEND_BACKEND_HANDOFF.md)。
- [历史任务与计划](../../../../../2026-11-11-local-cleanup/investigation-change/tasks.md)保留各批验收边界，旧 r13/5.3 未随本轮核销；Q 实际业务仍后置。
