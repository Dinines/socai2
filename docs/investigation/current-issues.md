# 调查流程与交接问题清单

2026-11-17当前基线：[21新版发布/清理](../operations/evidence/acceptance-release-20261117-01/README.md)及[新两段完整链](../operations/evidence/acceptance-fullflow-21-20261117-01/README.md)已完成。2告警/3上下文形成同事件/同Case两轮1→2，477份HTTP及142工件读回通过；8真实模型均stop，共45207tokens，实际并发峰值1且结束无在途。测试/HTTP限定独审与4177三类主体/两轮查阅通过。模型正文未全面验收，D5a异常PG/C6目标、D5/D6及4b自动接线仍待，旧原答/拒收/NOT_PASSED保持离线。

本批后置质量共5项：首轮C6影响分析的`empty_sources`与`delivery_source_coverage_missing`两项；后轮I两个open_questions声明两成员但引用只覆盖一个成员；后轮C6比较类型`withdrawn`与正文“范围扩大、核心结论不变”不一致。[自动4项及直接核对](../operations/evidence/acceptance-fullflow-21-20261117-01/final-validation.json)、[人工1项](../operations/evidence/acceptance-fullflow-21-20261117-01/manual-quality-review.json)均保留原答，不重采样；两轮Case仍accepted/uncertain/partial，未阻断下游。8份实际模型输入无控制tenant/来源标识，后台关联保持。

更新于 2026-11-17。当前发布和字段合同见[交接指南](../../FRONTEND_BACKEND_HANDOFF.md)。下列未完项独立于部署、读取和字段对应验收；登记不代表修复或取消需求。历史[独立流程审查](../handoff/history/2026-11-14-investigation-cleanup/documents/docs/investigation/investigation-flow-review-20261111.md)保留当时结论，不能将其中已修复/已交付事项继续算作当前缺口。

本轮[当前功能与整体流程评审](investigation-current-review-20261114.md)按4177三案原件、当前代码和21只读状态登记RV01–RV13，逐项说明影响、优先级及直接验收。它不替代主change结束审计，不修改既有质量后置决定。

后续按[六阶段实施规划](investigation-implementation-plan-20261114.md)推进：先固定交付修正，再完成统一领取、变化传播、H复核及异步维护。负责人最新明确引用质量与正文质量分开，引用正确性一并后置；引用错误不代表结论错误，原结论及原业务判定保留，问题另记，不能仅因引用错误删除/降级待核或整份拒收。13项评审发现均有阶段和关闭证据映射；规划不代表修复，原任务勾选状态保持。

阶段1的[详细设计及OpenSpec更新](../../openspec/changes/complete-socai2-investigation-chain/stage1-problems-and-plan-20261114.md)已明确整体效果、七步依赖及直接验证，分别归入既有RV01/RV02/RV04/RV12及原件留存要求，不另建任务树。步骤1 A/I与[步骤2 Case](../operations/evidence/stage1-case-retention-20261114-01/README.md)已完成原结论保留、引用独立记录及Case下游/采用的本地验收，stale及预览令牌保护保持。[步骤3 C3](../operations/evidence/stage1-c3-contract-20261114-01/README.md)一次七部分/8192/最多5发现也已完成保存读取，48项直接检查和44次GET通过。[步骤4有界补答](../operations/evidence/stage1-c3-completion-20261114-01/README.md)也已完成一次真实模型补答与19次GET，前六字段/逐字段原答来源保持；该批当时预算及C6预留不变，当前额度按11-16授权另行提高。[步骤5补查分流](../operations/evidence/stage1-followup-routing-20261114-01/README.md)已完成本地真实查询与保存读取；[步骤6原件存取](../operations/evidence/stage1-original-retention-20261114-01/README.md)已通过7份大原件保存读取、配置快照及历史8Run模块关联验证；历史配置未保存、unknown及夹具失败保留。[步骤7展示](../operations/evidence/stage1-viewer-20261114-01/README.md)已完成14项离线、快照逐值读回及21项浏览器验证，七步限定本地证据已齐。上述回执为当时各步本机证据；后续运行以页首当前r4回执为准。引用准确性/正文质量继续后置，不核销整体发现。

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
| RV12 4177结论展示 | 告警/事件“本轮交付”指向Run，正常`stage_output_saved`被归入错误；同Run的分诊判断/理由和事件诊断结论实际已保存 | P1，当前展示问题已[本地修复验收](../operations/evidence/stage1-viewer-20261114-01/README.md)：同Run原结论、正常结束、引用及采用分开，成功/失败/unknown和空态实测通过；该回执当时仅本机；现已接实际4177的W5与新批两轮，异常回执/局部读取失败展示增量仍待D6 |
| RV13 入站运行及配置 | 21投影本轮三分区lag均0，Agents自动分析仍关闭；投影异常会held并退出实例 | 继续区分入站/调度/执行/交付/采用；停位与局部硬编码在触及路径内处理，不开展恢复专项 |

[离线证据及脚本](../operations/evidence/investigation-current-review-20261114-01/README.md)保留本轮取数修正记录。RV03/RV05复用M01/M02/F01/F02；RV06–RV10复用下表现有流式缺口，不另建任务树。以下已交付功能保持，CLI和本轮评审不核销主31/41。

## 本轮输出继续实施

沿既有RV01/RV02/RV12与M01/M02落点，不另建任务树：

| 问题 | 最新设计及直接验证 | 当前状态 |
| --- | --- | --- |
| 实际请求仍带tenant_uid | D1按路径/用途过滤A/I/C3/Deep/C6，原件/业务source/id/未知字段/0/false/[]保持 | 本机已修复并验证；D2三份、D4c九份新实际请求通过，后台身份/原件保留，已随r4发布，21新02的14份真实请求禁入标记0，旧16份保持 |
| 缺限制说明等质量问题仍整份拒收 | D2保留结论/判定/范围，仅记录问题；无效引用不绑定；保存/HTTP核对，旧拒收保持 | 本机功能通过；新真实链2项缺说明记录后继续，另1项C3引用覆盖保留。质量仍NOT_PASSED/未全面验收 |
| 程序原观察还原受模型正文上限误拒收 | D2程序还原1218字/32字段完整保留；模型撰写正文限制、来源与防篡改不放宽 | 本机必要装配阻断已修，独立21项含母本与保护检查通过；已随r4发布，当前21新批另验 |
| length、JSON半项及网络异常不能普遍继续 | D3–D5统一阶段回执与闭合单元恢复，C3补答失败保初答，I终结回执驱动活跃Case；超时/断连不堵独立下游/队列 | D3 C3已通过截断/空白补答→C6；D4a A/I已通过完整/partial/none保存读取。D4b门控/分配/C1冻结及D4c partial/none→同Case两轮完整链通过；Deep/C6自身恢复和网络异常待D5 |
| C3显式空发现误使领域无效 | D3接收器曾将findings=[]当Finding依赖；仅纳入真实Finding条目，保留合法空数组及原四领域 | 已修并复验；原51通过/1失败记录保持，最终96项直接与34项独立通过，不改变旧用例预期 |
| 部分材料被误作比较基线或页面空白 | D5/D6区分可作prior_analysis、可采用、可比较；旧拒收不回填，局部读取错误留原流程 | 已设计，待存取/HTTP/4177联验 |

完整规则与顺序见[第11步设计](../../openspec/changes/schedule-streaming-investigation-updates/stage11-output-continuation-design-20261116.md)，测试复用原TC-N01–N11及[设计回执](../operations/evidence/test-continuation-design-20261116-01/README.md)。设计/mock不证明真实模型质量或整体change完成。

## 当前功能缺口与实施入口

固定调查核心v1.2-20261113-r1/当时71操作仅作历史依据。当前21处理/HTTP为20261117-r1，4177为r7，旧处理入口停止；本批两段正常业务链及4177三类/两轮查阅已通过，测试/HTTP限定独审通过，原A/I/C3/Deep/C6质量问题与失败保留。第1–7步/F1–F5已交付的本机边界不重新列缺口；当前未完项为下表及本轮输出继续设计、完整change结束审计和后续统一交付。第8–10步后置。

| 当前实际缺口 | 代码/行为依据 | 后续实施落点 |
| --- | --- | --- |
| 工作台主体/轮次与Docker验收已发布，4b自动接线待完成 | 任务1/2、3a–3d已完成，21新批两段及[实际展示](../operations/evidence/acceptance-fullflow-21-20261117-01/viewer-browser-01.json)通过；普通主体不再依赖账本导航 | 4b补报告指定主体/Run链接及自动派生来源账本；本批辅助账本为既有发布入口补证，不冒称自动化。A/I概览通用卡片部分无对应字段显示“未记录”，阶段状态及原分析可读，展示细化登记后续 |
| 新版已运行，完整change尚未收口 | 本批2告警/同案两轮及477份HTTP已通过；no_changes无新执行，4177正常流程已验；未等待自然4/6小时，模型正文未全面评估 | 4b自动接线及D5/D6/完整覆盖与结束审计继续按原顺序；不将已部署等同于change完成 |
| 事件终结材料继续已发布，异常余项仍待 | D4b门控/冻结与D4c当前任务链已核；partial/none均推进同Case两轮、原4成员保持、无变化不重复；HTTP同源 | D1–D4c已按明确授权分阶段发布；本机两轮与21新02三次Case结果均待复核/部分交付，模型质量独立保留 |
| Case成员跟随已接，余项验收仍待 | r4新02已201建案并实际验证整事件Case3→4、单告警保持1成员/1轮；R2固定最近R1及Result，旧步骤/原件/结果保持 | 排除/关闭/超期沿原证据；D4b已验4总/3选/1保留仍分配Case全4，D4c已验同案两轮及next_check_at受控时钟的周期0/1分支；未等待真实4/6小时；本批显式source=user检查不作自然周期证据 |
| 一次人工定向分析与用户手动后续综合后置 | H版本与人工方向/定向请求需区分；既有保存不代表定向分析已运行 | 第8/9步保留设计、未实施，不作本期1–7验收前置；2.4/2.5 |
| 分诊完成仍等待历史知识同步，队列维护后置 | knowledge_sync.after_triage 在业务提交后等待；原回执可读但无统一调度状态 | 第10步保留设计、未实施，现状不改称后台异步已交付；2.6/2.7 |
| 自动接续的完整change验收仍待 | 处理已部署r4，新02正常业务链通过；旧Agents关闭，质量未全面通过 | 完成输出继续D1–D6、完整覆盖核对及结束审计，不以局部通过勾整体验收 |

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
