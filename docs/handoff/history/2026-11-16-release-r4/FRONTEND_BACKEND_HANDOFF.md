# 告警、事件与 Case 前后端交接

> 2026-11-16当前状态：21处理保持processing r3，HTTP18024/Swagger18080及[4177](http://127.0.0.1:4177/viewer/)仍为既有版本。本机D1–D3、D4a/b及[D4c完整任务链](docs/operations/evidence/ai-case-chain-d4c-20261116-01/README.md)已完成执行/直接验证：新4告警、同Case两轮，I partial/none均可继续；9次真实模型、3处另记的响应注入、8task/6Run/46步骤/134工件/2Results。196 ASGI GET覆盖任务、全分页目录、正文、源I五份原件和前轮比较，25表读前后不变，227文件冻结一致。两Result均accepted/uncertain/partial，结论与对应C6原答一致；时间顺序正文错误及4项引用诊断保留，不等于质量通过。来源沿冻结incident_id/source_run_id取，不依赖latest；Result.source_answer是对话回答来源，本批null合法，C6模型原答沿实际Run/模型步骤/工件定位。公共DTO、租户/告警关联和预算保持，9份实际输入无tenant_uid或测试执行身份。本机静态46→47，旧46条逐值保留；本步为服务入口+ASGI GET，不冒称ASGI POST、21 TCP或新4177浏览器已验。D5/D6及整个change收口仍待，未部署、提交推送；当前状态以[PROGRESS](PROGRESS.md)为准。

**W2代理读取已验收：** 测试模块完成[34次真实GET](docs/operations/evidence/test-http-proxy-w2-live-20261115-01/tcp-02/result.json)：9次测试账本、24次业务代理、1次当前OpenAPI，全部200；Case C1→原I来源目录→返回content_url→原输入的身份/摘要及3条冻结范围一致。HTTP完成[保存回执离线复核](docs/operations/evidence/streaming-w2-http-cooperation-20261115-01/tcp-readback-review-01.json)，S04失败/3条skip、两Case原partial和initial/空比较保持。临时代理及SSH已停止、临时端口关闭；首次隧道目标误选的失败保留，未成功调用业务GET。没有业务写入、模型调用、代码或版本变更，HTTP未重复发请求；本步不覆盖Case后轮、steps直接跨Run引用或模型质量，W3/W4另步推进。

**W3页面HTTP读取已核对：** 测试模块0.3.0页面完成唯一真实浏览器联验，HTTP侧[独立复核保存回执](docs/operations/evidence/streaming-w3-http-cooperation-20261115-01/browser-readback-review-01.json)通过：26业务GET全200，7个task、4个Run及两案原Result关联正确；Case工件20/20/8共48条完整读回，C1→原I目录→原输入保持原3条范围与摘要。I失败原答、3条skip无Run、两Casepartial/initial/空比较及当前stale保持。完整浏览器记录51条中另有favicon404和2条静态缓存304，不笼统写全部200。已修共享use_case_id导致测试用例操作混入的问题；临时端口关闭、账本不变，终态30.94秒无请求。HTTP本轮0新增GET，80操作/55 GET业务合同与当前4177未改、未部署；页面整体审阅/收口由调查与测试负责，W4另步。S04正向、Case后轮、真实unknown/大原件/direct reused及模型质量未由本步覆盖。

W3已收到[测试最终冻结回执](docs/operations/evidence/test-viewer-w3-20261115-01/acceptance.json)，HTTP核23份最终文件摘要一致。末尾的轮询/页面恢复处理和C1“本案交集”摘要只做受控/离线验证，未重开浏览器；原51条请求和26次业务GET保持，详见[冻结补记](docs/operations/evidence/streaming-w3-http-cooperation-20261115-01/final-freeze-review-01.json)。

**W4包与实际代理接线已验证：** 0.4.0独立包的测试API、页面、驱动和两份OpenAPI已冻结；本机17 GET、21候选35 GET全200，后者含17次业务代理读取。整事件Case4成员/2轮/current、单案1成员/1轮/stale，新I和Case第二轮、上一轮链接及I/C6原答身份/摘要正确。15份账本/证据在一次重启前后不变，21回环18477候选最终exited/0，调查HTTP合同及容器未改；[原始请求与响应](docs/operations/evidence/streaming-w4-package-20261116-01/remote/evidence/requests.json)保留。未重跑模型或浏览器，该批当时质量NOT_PASSED、W5待；当前入口以页首W5回执为准。

更新于 2026-11-16。本文是前后端 HTTP 和组件对接的共同入口，以当前状态及实际读回为准。产品测试页接线不作为业务API交付前置；内部查阅页W3按上方单独分工推进。下面的历史部署/读回记录保留原适用版本，不表示21旧服务仍可访问。模型正文质量按负责人最新决定后置，原未通过记录保留；候选仍需完成本期实际功能验收。

**第7步五项修复已完成本机验证，整个change结束审计仍待：** F1事件分析范围已完成[同源22次HTTP读回](docs/operations/evidence/incident-case-scope-fix-20261115-01/http-readback.md)，F2管理字段修复已完成[同源24次HTTP读回](docs/operations/evidence/case-input-metadata-fix-20261115-01/http-readback.md)，F3已知失败重试已完成[同源52次HTTP读回](docs/operations/evidence/case-retry-fix-20261115-01/http-readback.md)，F4新批已完成[89次同源HTTP读回](docs/operations/evidence/case-trigger-fix-20261115-01/http-readback.md)，独立排队、历史手动检查、事件驱动及续建、重试阻隔均通过本机直接验证；F5也已完成[90次同源HTTP读回](docs/operations/evidence/execution-contract-fix-20261115-01/http-readback.md)。5项本机直接修复验证齐备，旧失败保留，完整change及21真实链/独立结束审计仍待。已有局部HTTP通过记录保留原适用范围；本轮21独立候选已完成连接及空态接入，旧失败批状态管理已完成实际保存/读回，正常业务整链仍待。最新已确认的自动更新与受理读取规则见[目标流程及验证](openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#审计修复后的目标业务流程与接口验证)：整事件关联在事件诊断业务更新后推动活跃Case，单告警关联保持固定范围；不同请求独立排队、相同key幂等。对象/关联/任务先保存，模型完成后再保存结果，接口保持无鉴权；当前21候选已加载同版代码，S01已走通真实入站至两案首轮读取；后续更新与完整change仍与调查、测试逐步验收。

**历史固定调查发布（11-13）：** 核心`v1.2-20261113-r1`与当时独立18024曾同步更新A/I及C3/Deep/C6输入和程序装配，保留原71操作合同；[原发布交接](docs/operations/evidence/fixed-investigation-release-20261113-01/handoff.md)记录该批源码、配置及读回。该21旧入口现已主动停止；当前联调使用顶部18424/18480候选。

[流式更新](openspec/changes/schedule-streaming-investigation-updates/tasks.md)第1–7步及F1–F5已完成本机程序联验；[任务生命周期](docs/operations/evidence/analysis-lifecycle-20261114-01/README.md)与[原17项PG/Redis检查](docs/operations/evidence/analysis-dispatch-20261114-01/pg-redis-05.json)保留原范围。迁移128/129现已在21候选库生效，正式aisoc当时保持原数据；现按页首授权清空选定业务表、结构保持；候选HTTP已加载[分析任务读取](docs/integration/analysis-tasks-http.md)；唯一候选调度已完成同批A/I和两案首轮，并在全部终态后停止。[统一HTTP合同](openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md)为：告警入站登记自动分诊任务，Case建案登记首轮任务，再次调查和事件诊断异步返回task_id，实际执行时才关联run_id。E11 prepare、E13 start及E36手动告警分诊在候选已退役，内部队列对调用方透明。后文71操作表只作历史追溯；人工任务/判定、结果读取、采用及管理沿当前合同。同告警新材料提交/据此重新分诊已明确撤回，不列作待开发入口。

11-14与阶段一实施、调度规划两边核对的[接口影响评估](docs/integration/investigation-api-impact-20261114.md)记录了当时旧读取器会误判新事件结果过期、存在大原件读取门槛等版本依赖。当前r2候选已统一加载相关读侧代码和异步合同；原本机受控依赖联验保持有效，21实际非空及整链功能仍按本期批次验收，不能仅以候选启动完成代替。

负责人随后明确：后续核心、独立API和Swagger按统一目标版本推进，不做新旧版本兼容工程；先定设计，接口或依赖表结构未定稿的暂缓该接口，已定稿且不受影响的部分继续开发。未来调用行为以定稿合同为准，不据上面的现行行为自行增加兼容分支。

产品/接口侧已按125项页面功能提出[功能→接口数据→来源表→提供责任清单](docs/integration/product-api-data-requirements-20261114.md)。调查模块按产品需求提供能力，不能由现有接口反推功能范围；缺少实现/表记录为待提供，真正缺业务规则才标合同待定。跨主体目录/统计及真实任务关联的完整HTTP已本地验收、待统一发布；完整步骤工件读取已完成下述本地验收，异步调查按目标合同推进；普通附件仍为业务后端存文件、调查服务存关联，不据此增加模型读取正文的要求。

后续确认已同步到[目标合同第8节](openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#8-后续已确认更新对http的要求)：Case默认100条后续建并返回真实分配；事件只有一个接收后续告警的Case；关联Case先列容量续建、再列共享事件；定向分析独立交付，由用户手动触发后续综合；补查默认前后各1小时；事件诊断默认选择最近归并100条并明确实际覆盖。定向`POST /cases/{id}/targeted-investigations`、手动综合`POST /cases/{id}/syntheses`、工具目录、Case关联列表及`/analysis-runs`完整目录/步骤/工件分页的目标路径和DTO已列在该节。Q5不做旧对象迁入/启用，Q6窗口内已受理首试跨期继续一轮但不重试，补查不另设最大跨度/裁剪/拆窗。其中统一Run目录、完整步骤/工件及分析任务读取已完成本地验证，事件E37异步提交也已本地验收，Case分配/首轮任务受理和关系查询也已本地验收，Case首轮执行及读取已联验，Case再次提交已完成受理、真实调度/保存及读回，周期边界只读也通过；不能使用本页现行单Case回执或旧同步调用推断新版本已部署。普通AI对话仍暂停。

**本期后续范围（11-15）：** 第6步Case建案首轮实际执行及结果读取已联验，第7步检查更新/再次调查已挂载，新批三任务完整闭环及周期边界读取通过，已进入当前候选代码，正式发布仍待。第8–10步人工定向、手动综合及知识后台异步维护已后置，保留设计和未完成状态，不提前开放目标接口，也不作为本期第1–7步主流程联验前置。第6步接口切换与直接验收见[HTTP配合安排](openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#819-第6步case首轮执行http配合与切换安排)；调查和HTTP两侧已完成第6步受控依赖联验，候选TCP空态已通过，真实模型和非空完整链仍待；原批本地验证不追认成21整链通过。第11步最终验证结合测试对话已有[完整测试方案](openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md)和[HTTP供给清单](openspec/changes/schedule-streaming-investigation-updates/test-interface-readiness-20261115.md)，核本期第1–7步的实际独立HTTP提交、保存及读取；第6/7步局部ASGI验证不代替最终TCP联验，后置项继续明确未实现。

**本轮本地实现：** [完整步骤与原件目录指南](docs/integration/run-records-http.md)说明新增三个GET、每个输入输出字段、正文来源链接及错误。66次本机隔离PG/ASGI请求通过，1001步骤和201原件可完整分页读取；E12/E32增加完整目录链接。该批候选代码共80操作；该批未发布；当前21候选接入状态见顶部回执。

**统一Run目录：** [接口指南](docs/integration/run-directory-http.md)说明`GET /api/v1/socai2/analysis-runs`的筛选、分页、统计、task_id/intent及结果链接。原32次隔离PG/ASGI请求和15类记录核对保留（其中1次503为依赖替身）。迁移128及该接口现已进入21 r2候选，[W2代理检查](docs/operations/evidence/test-http-proxy-w2-20261115-01/README.md)验证实际空目录；非空/跨Run读取仍待同批真实记录，正式端口未恢复。

**分析任务读取本地实现：** [三类列表/详情指南](docs/integration/analysis-tasks-http.md)说明六个GET、每个字段、状态、结果跳转及配置。38次隔离PG/ASGI请求通过，14类记录前后摘要一致。已受理无Run、重试、失败和归并原任务均可读；A/I自动执行及事件异步POST已完成下述本地联验，Case首轮已联验、检查更新/再次调查已完成执行与终态读取联验；人工任务保持独立。原批OpenAPI见[回执](docs/operations/evidence/analysis-task-http-20261114-01/README.md)；当前代码已纳入21 r2候选；新批4条accepted任务的实际TCP非空读取已通过，A/I执行后结果及原答已在62次TCP GET中核对；Case及跨Run场景按后续子步验收。

**事件异步提交本地验收：** [E37提交指南](docs/integration/analysis-submission-http.md)说明输入、202回执、轮询、幂等和错误。实际A/I handler已接：check无变化跳过且无Run，rerun完成新Run/诊断并保留旧记录，终态重放仍回原受理身份。事件同步旁路已移除；Case新的异步POST现也已挂载，验证进度见下。正式两端尚未发布此版本。

**告警自动分诊查询联验：** [查询指南](docs/integration/alert-auto-http.md)按告警详情→任务状态→Run/分诊→步骤/原件说明用途。[无鉴权联验](docs/operations/evidence/alert-auto-http-20261115-01/README.md)受控模型批28次GET、真实模型批最终30次GET通过，任务/Run/分诊及原件同源，十类记录前后不变。候选E36已移除，内部执行器保留；事件E37现已完成下述异步联验。真实模型正文质量NOT_PASSED保留。

## 接入先看这里

**事件诊断范围与覆盖：** [逐字段指南](docs/integration/incident-analysis-http.md)说明E23/E25的input_selection/analysis_coverage。已通过[103次真实隔离PG/ASGI请求及12项直接检查](docs/operations/evidence/incident-async-http-20261115-01/README.md)：含异步提交/消费、260条选入100/遗漏160、容量失败、unknown、跨期失败及既有真实模型样本读取；12类记录只读前后保持。告警Schema不变，无鉴权。该步候选OpenAPI80操作已记录，该批随后随Case关联查询为81操作；第6步首轮切换移除E11/E13后为79操作，第7步挂载Case提交后为80操作，21旧服务停止前仅64操作；当前独立候选80操作已完成空态接入，待本期整链收口后统一正式发布。

**Case分配与关联查询本地验收：** [接口指南](docs/integration/case-allocation-http.md)说明E01/E07/E08/E09的真实多案分配回执、excluded_alert_ids、首轮任务及错误；Case continuation/两级related-cases和事件接收字段已接。第5步72次隔离PG/HTTP、23项直接检查通过，依赖核心129。随后[第6步首轮执行](docs/integration/case-initial-http.md)39次HTTP及6项直接检查通过：受理时无Run，调度后沿任务读取Run、结果、判断及原件；两个旧启动入口已移除，该步79操作、无鉴权。该批模型/湖依赖使用替身；相关代码现已进入21候选，不能把该本机批次当21实际建案验收。

**Case更新受理与比较读取：** [接口指南](docs/integration/analysis-submission-http.md)说明`POST /cases/{case_id}/investigations`的check/rerun请求、202回执及错误；[本批证据](docs/operations/evidence/case-update-http-20261115-01/README.md)包含20次独占新案受理请求、28次核心已结束样本读取，前轮身份与冻结输入一致。发现并修复了结构化对象读取错误。新批已顺序执行为2个completed及1个skipped/no_changes，41次终态读取/原key回放通过且未新增任务，周期边界47 GET通过。第7步原[80操作三类Swagger包](docs/operations/evidence/case-update-http-20261115-01/swagger/manifest.json)和[发布片段](deploy/http-service/case-update-release-fragment.json)保存该批本机交付；当前21候选已使用后续完整r2包部署，真实S01受理/首轮读回已通过，后续更新另验。

**当前候选接入：** [HTTP部署步骤](deploy/http-service/README.md)、[配置字典](deploy/http-service/CONFIGURATION.md)、[Swagger部署与本机查看](deploy/api-docs/README.md)对应已运行的r2/80操作版本。18424/18480已完成启动、普通读写连接、无鉴权三类空列表及同版合同读回。PG仅需地址、端口、库名和账号密码，require TLS不要求应用CA/客户端证书。真实Kafka新批入站对象及受理任务已完成35次GET核对；A/I实际结果及原答62次GET已通过（质量NOT_PASSED），两案建案及首轮58次结果GET也已通过，下一步为后续变化/比较。旧18024/18080保持停止。

[此前普通密码连接补验](docs/operations/evidence/pg-password-connection-20261115-01/README.md)的21旧reader与本机writer分属两个环境，保留原回执。[当前候选双池回执](docs/operations/evidence/streaming-http-runtime-20261115-01/connection-01.json)已独立验证同一21候选库、普通reader/writer及TLSv1.3。零行更新回滚没有提交业务数据；旧失败批的管理状态已另行通过HTTP保存/读回；正常新批建案和首轮结果也已保存读回；后续变化及整个change结束审计仍待。

**当前候选联调：API `http://192.168.1.21:18424`，Swagger `http://192.168.1.21:18480/`。最终正式18024/18080保持停止，待整链验收及独立审计后统一发布。**

18424是独立调查HTTP服务，18480是它的Swagger；实际r2包含80个业务操作且无鉴权。旧21服务停止前曾有64操作/401与静态71操作不一致的问题，原观察保存在[差异记录](docs/operations/evidence/http-test-alignment-20261115-01/README.md)，不再作为当前运行状态。本机旧18024/18080本轮未操作，保留[最近观察](docs/operations/evidence/http-local-runtime-review-20261115-01/README.md)。候选库、正式库和示例身份不得混用；可用功能以当前合同及相应实际验收回执为准。

| 接入事项 | 直接入口 |
| --- | --- |
| HTTP 用途、参数、每个输出字段、示例、错误和实现状态 | 当前[21 Swagger](http://192.168.1.21:18480/)、[OpenAPI JSON](http://192.168.1.21:18480/handoff/openapi.json)及[同版仓库文档包](deploy/api-docs/streaming-20261115-01/handoff/manifest.json) |
| 后端自己启动本地 Swagger | [Docker 安装、架构选择、端口、API 地址及更新步骤](deploy/api-docs/README.md#后端在自己电脑启动-swagger)；无需安装调查数据库或模型 |
| Kafka 与其他组件 | [组件对接指南](docs/integration/component-handoff-current.md)：实际 Topic/消费组、消息输入输出、数据流、依赖地址、启用状态和责任边界 |
| 测试数据与可执行操作 | 当前按[S01/S04数据设计](openspec/changes/schedule-streaming-investigation-updates/test-data-design-20261115.md)准备真实Kafka批次，身份取实际落库映射。[原后端测试指南](docs/integration/backend-test-guide.md)中的旧库三案只作历史示例，不可直接在候选重放 |
| 完整目标流程测试 | [总计划](openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md)、[数据设计](openspec/changes/schedule-streaming-investigation-updates/test-data-design-20261115.md)、[供给清单](openspec/changes/schedule-streaming-investigation-updates/test-interface-readiness-20261115.md)；T2离线材料、W1及W2空态已验，S01真实入站/A/I/两案首轮及HTTP已通过；S04后轮的保存/读取与比较身份已通过，模型正文质量及完整验收仍待 |
| 测试服务与4177目标取数 | [独立服务设计](openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md)：业务走调查API，批次/质量走测试只读API；W2/W3读取与页面已验，W4完整包0.4.0已通过本机/21候选读取及重启保留；W5已接实际0.6.0；当前清理后为空，旧21工作台保持停止 |
| 4173 测试页面 | [启动、使用、样例/历史/真实数据的区别](docs/integration/test-page-4173.md) |
| 产品功能范围 | [125 项功能清单](deliverables/investigation-validation-20261106/frontend-feature-list.md)，只作为范围依据；不扩展旧 AiSOC 平台功能 |
| 产品向调查模块及业务后端提出的数据要求 | [125项逐项映射、必需输入输出、来源表及提供责任](docs/integration/product-api-data-requirements-20261114.md)；这是目标需求和缺口，不冒充已上线Swagger |
| 获取父项目中的服务源码 | 在 SpiritHub 使用 `git submodule update --init server`，按父项目固定的 server 提交读取本文件；不使用 `--remote` 自动跳到其他版本 |

推荐调用关系：`产品前端 → 业务后端 → 调查 HTTP API`。业务后端负责资产库存、资产标签和人员目录等基础能力；调查服务负责自身业务数据、执行与结果。`owner_id/assignee_id` 使用调查服务能识别的同租户用户 UUID，不能直接传姓名或未建立映射的外部人员 ID。数据库及内部缓存不作为前后端写入入口。

### 按业务调用

以下表格只保留原71操作交接基线供历史追溯，不是当前调用步骤。E11/E13/E36在当前候选均已退役，建案/首轮使用[当前指南](docs/integration/case-initial-http.md)，后续检查和再次调查使用[异步提交指南](docs/integration/analysis-submission-http.md)。路径省略`/api/v1/socai2`；参数和返回以18480当前80操作合同为准。

| 类别 | 功能和调用顺序 | 返回结果与注意点 |
| --- | --- | --- |
| 告警读取 | E26 `GET /alerts` → E28 `GET /alerts/{alert_id}` → E22 `GET /alerts/{alert_id}/analysis`；E24 读指定 Run，E32/E33 读步骤/工件 | 分开读取告警事实、当前有效分诊和历史尝试；材料正文用 E31 |
| 告警分析（历史同步入口；当前已退役） | E36 `POST /alerts/{alert_id}/analyze` | 仅记录旧流程；当前由入站登记自动任务，不调用此路径 |
| 事件读取/分析 | E27 列表 → E29 详情 → E23 诊断目录 → E25 指定 Run；E37 `POST /incidents/{incident_id}/diagnose` | 事件成员/对象等用 E30 分区读取；归并关系不等于攻击因果 |
| 创建调查 | E01 `POST /cases`，传标题、`operation_key` 和所选 `alert_ids/incident_ids` → E03 详情、E12 Run | 返回 Case、范围版本和 `pending_run_id`；创建本身不启动调查 |
| 启动/读取调查 | E13 `POST /cases/{case_id}/runs/{run_id}/start`，带 `operation_key/expected_scope_revision` → E12 Run → E14 正式结果 | start 会等待本次执行返回；连接超时或未知先查原 Run，不换 key 重跑。结果包含结论、发现、未解决问题及建议 |
| 再次调查 | E11 `POST /cases/{case_id}/baseline/prepare` → E13 start | 显式准备并启动；人工任务保存、重开 Case 均不自动启动 |
| 人工任务 | E38 创建 → E39/E41 读取 → E40 `PUT /cases/{case_id}/tasks/{task_id}` 完整修订 → E42/E43 读历史 | 创建带 Case 范围版本；修订还带任务行版本。完成必须填结果正文及适用范围；旧版本保留 |
| 告警人工判定 | E28读版本 → E48单条或E49批量提交 → E28/E30读回 | 判定及理由追加保存，误报/正常关闭，已关闭改真实威胁/需跟进恢复处理中；模型分诊保留 |
| 告警管理 | E50单条或E51批量 → E28/E30读回 | 负责人、标签、状态；人工关闭必填reason，不覆盖原判定 |
| 事件管理 | E52单条或E53批量 → E29/E30读回 | 负责人、状态、标签、人工严重度；解决和等级覆盖需理由，不改变成员等级 |
| 调查基本管理 | E44 `GET /cases/{case_id}/management` → E45 `PATCH` 同路径 → E03/E44 读回 | 可改标题、说明、负责人、严重度、标签、处理状态；只更新显式提交字段 |
| 关闭/重开 | E44 读条件和版本 → E46 `POST /cases/{case_id}/close` 或 E47 `POST /cases/{case_id}/reopen` → E17 读活动 | running/unknown 阻止关闭；未完任务要求明确确认及理由。重开恢复处理中，不重派调查 |
| 采用已有调查结果 | E63预览→E21提交operation_key/expected_review_token/reason及必要未完工作确认→E03/E64/E17读回 | 新增判断并保留旧版本；原Result、任务/Run及处理状态保持。[调用指南](docs/integration/result-adoption-http.md) |

调查没查清的内容直接写在调查结论里，例如“尚未确认这次登录是否由本人操作”。需要找人确认时，用户再建“联系本人核实登录”的任务；不会自动把每个疑问变成待办。

告警涉及设备时，调查服务到业务后端维护的现有资产库存中查找，找到就返回设备信息和标签，没找到返回空列表。查询路径是 `GET /alerts/{alert_id}/records/assets`（加上前述业务前缀），事件用 `GET /incidents/{incident_id}/records/assets`。文档编号E30只是方便查找同一个分区读取接口；`assets`填在路径最后，不是新增服务、数据表或查询参数。资产创建和标签维护由业务后端负责。

案件候选E66已发布本机和21并各11次GET读回：按当前成员或指定真实告警/对象查一层候选，返回匹配原件、时间范围和归属；明确加入复用E08。规则、字段和错误见[候选查询指南](docs/integration/case-exploration-http.md)。[E67–E69保存恢复](docs/integration/case-exploration-save-http.md)已实现并发布：读取底图、保存、恢复，固定原图/展开/画布，版本冲突409，不改变成员和Run。本机27次功能验证及两端各6GET读回通过；21本轮仅只读，未实测生产保存写入。

案件故事E65只读查询已发布本机和21并读回：`GET /cases/{case_id}/story`支持搜索、告警等级筛选和游标分页，返回原告警、调查及人工完成修订。字段、跳转及错误见[故事查询指南](docs/integration/case-story-http.md)。AI对话继续暂缓。

[E70告警相似历史复核](docs/integration/alert-review-http.md)已发布：默认按当前告警发生时间回看30天，返回最近候选及对象/战术来源；用户核对后才用E48/E49反馈。23次本机功能GET通过，正式本机8GET命中3条，21既有记录5GET为空候选，均无业务写入或模型调用。同主机最近7条已由[E71](docs/integration/alert-host-http.md)提供，匹配不要求战术相同。

### 请求、版本和错误

内部默认可信，调用不需要登录、Token或角色校验；JSON请求使用 `Content-Type: application/json`。租户及记录操作人由服务配置提供。下例只示范 Case 管理；替换 Case ID、当前版本和本次操作 UUID 后调用：

```http
PATCH /api/v1/socai2/cases/{case_id}/management
Content-Type: application/json

{
  "operation_key": "00000000-0000-4000-8000-000000000901",
  "expected_row_version": 3,
  "title": "核实异常登录",
  "handling_status": "in_progress"
}
```

成功返回 `{"case": <保存后的完整 CaseView>, "changed": true或false}`；从 `case.row_version` 取得下次管理写入的版本。省略字段保持原值；`description/owner_id/severity=null` 清空，`tags=[]` 清空标签。其他接口的请求结构不同，不能把此版本参数套用所有接口。

- `operation_key`：每次逻辑写入一个 UUID，同一意图重试沿用；改变输入后使用新 key。
- `409`：版本冲突、运行阻塞或状态不允许等；保留用户输入，读取最新对象后按 `detail` 处理。不要直接无限重试。
- `404`：对象不存在或不属于指定父主体；检查 Case/Run/材料之间的真实 ID 关系。
- `422`：参数/枚举/必填项不合法；`detail` 可能是字段错误数组，也可能是业务错误字符串。
- `501`：E19助手提问、E20保存回答尚未实现，按负责人2026-11-13要求暂缓；E21采用已有基础调查结果已实现。
- `503` 或执行请求超时：先读取原 Run；服务错误 `detail` 可能为对象，不能假定统一是字符串。
- E02/E26/E27现支持筛选、排序、分页；告警时间按event_time，事件至少一条成员告警在窗口内，Case按business_updated_at。带时区时间前闭后开；缺值始终排序在后。告警/事件filtered_total是筛选数，total/overall_stats是整体；Case total是筛选数、metrics是整体。新条件用next_cursor续页，改条件清空；旧无新增条件的before_id保留，不能混用。完整参数见[列表用法](deliverables/investigation-validation-20261106/http-handoff/README.md#列表查询怎么用)。

告警/事件写入的参数、批量选择、完整返回及错误见[后端测试指南](docs/integration/backend-test-guide.md#告警人工判定与告警事件管理)。

“已实现”只描述接口业务是否存在；当前未完成的问答及真实响应等见[接口实施计划](docs/investigation/http-implementation-plan-20261112.md)。真实模型结论质量仍未整体验收通过；页面修改不在这次后端交接范围。

后续按功能流程推进，必要读写接线与配置随功能处理。告警相关的前后端字段合同保持稳定；字段名、类型、含义、关联和接口返回确需调整时先列明影响并确认。下表保留已核验的运行配置，配置当前值不构成后续功能开发的权限前置。

本项[分诊后历史知识同步](openspec/changes/archive/2026-11-12-sync-saved-alert-knowledge/validation.md)已完成本地直接流程、独审及 21 r5 发布读回；采用原 Run trace／工件读取表达同步状态，不新增告警 DTO 字段。历史卡片及同步字段见[知识交接](docs/investigation/historical-alert-knowledge-handoff.md)。

## 1 接手入口

| 内容 | 权威资料 |
| --- | --- |
| 产品功能与规则确认 | [逐页功能清单](deliverables/investigation-validation-20261106/frontend-feature-list.md)：目的、操作结果、后端实现状态与接口；[规则记录：D01–D07 全部已确认](docs/design/investigation-product-decisions.md)；[产品需求](docs/design/alert-incident-case-product-requirements.md) |
| 功能对应字段及跳转 | [F01–F28 字段／J01–J14 跳转附录](deliverables/investigation-validation-20261106/frontend-data-navigation-contract.md) |
| 字段到存储、关联及读取 | [服务端数据交接](docs/investigation/socai2-page-data-handoff-20261106.md) |
| 当前调查表与写入边界 | 候选123–129为32表521列，见[当前安装/升级入口](deploy/database/CURRENT.md)及[实际供给](docs/operations/evidence/streaming-candidate-20261115-01/database-prepare-01.json)；[原28表职责](docs/investigation/investigation-table-scope.md)保留历史范围，资产等基础数据由业务后端负责 |
| HTTP字段审计来源 | [基于原三份资料的核对结论](deliverables/investigation-validation-20261106/http-handoff-audit/README.md)：先按告警22/事件15/调查88项，原43操作/522字段已审，Case管理增加4操作/10字段，前批告警/事件管理增加6操作/8字段，前批列表封套增加2字段，前批新增3个CSV操作，前批新增E57归并统计，前批E58/E59普通评论、本批E60–E62附件引用；该历史批次为71操作，原JSON有542个固定字段出现位置，E57新增12个、评论新增22个、附件引用新增37个、采用新增42个、故事查询新增13个、候选查询新增35个、保存恢复新增22个、告警相似复核新增27个、同主机近期查询新增12个（合计764）与35组既有动态说明；新graph/view_state展示JSON见E67–E69指南，CSV另说明104个允许列；字段说明已合入当前Swagger |
| HTTP逐项对接与在线文档 | 当前候选[21 Swagger](http://192.168.1.21:18480/)按告警/事件/调查展示80操作，实际API为18424；[运行回执](docs/operations/evidence/streaming-http-runtime-20261115-01/README.md)记录空态接入及未验边界。[本机Docker部署](deploy/api-docs/README.md)；此前71操作交接仅作历史基线 |
| HTTP功能验证与后续实施 | [本机路由/真实隔离库验证](openspec/changes/complete-socai2-investigation-chain/http-functional-validation-20261112.md)：31项检查、43操作回执，模型为替身，真实质量未核销；[未实现功能计划](docs/investigation/http-implementation-plan-20261112.md)。[统一独立入口验收](openspec/changes/archive/2026-11-12-serve-investigation-api/validation-20261112.md)已完成本机/21 TCP Case/H与SQL读回，详见下表 |
| JSON 与 HTTP 合同 | 当前[80操作OpenAPI](deploy/api-docs/streaming-20261115-01/handoff/openapi.json)；数据库/原件参考[JSON Schema](docs/design/socai2-json-contracts-20261103.schema.json)，HTTP实际结构以当前合同为准 |
| 对外与内部接口边界 | [架构说明](docs/design/investigation-http-boundary.md)：列表/详情和显式业务提交属于独立对外HTTP，调查步骤/组件调用单独维护。当前提交合同为异步diagnose/investigations；旧analyze及prepare/start外部入口已退役，内部能力按自身归属保留 |
| 有值、空值与原件 | [字段取数样例](deliverables/investigation-validation-20261106/page-field-samples.md)、[运行记录及离线材料](deliverables/investigation-validation-20261106/README.md) |
| 程序流程和模型职责 | [执行账本](docs/investigation/current-execution-ledger.md)、[每个模型环节的输入输出](docs/investigation/model-input-output-current-20261109.md) |
| 模型输入字段选择 | [第32节C3程序分工](docs/operations/evidence/case-c3-coverage-20261113-01/README.md)与[10批发布基线固定链路](docs/operations/evidence/fixed-investigation-20261113-10/README.md)已本地直接核验：C3模型五项业务问题，程序补coverage，保存/HTTP读取仍六问；Deep/C6按各自任务取材料。1新Run/5次生成，C6一次纠错后accepted/uncertain/partial并成为第3版current，4次ASGI/SQL读回一致；原A/I、H、失败及旧结果保持。HTTP字段和数据库表不变，调用方无需改合同；10批验收后已发布核心r1，独立18024已同步并完成两端既有记录读回。正文质量NOT_PASSED。11-14按负责人要求新跑[三案展示](docs/operations/evidence/fixed-investigation-20261114-01/README.md)，1案待复核并采用、2案拒收未采用；当时两端4177和4173显示三案快照；现已撤出活动展示，按页首清理回执处理。不以输入预览或结构接收追认质量。 |
| 当前固定流程与流式更新 | [固定范围调查](openspec/changes/complete-socai2-investigation-chain/fixed-flow-plan.md)保留原验收；[流式第1–7步](openspec/changes/schedule-streaming-investigation-updates/tasks.md)及五项修复已完成本机联验，当前第11步S01入站、A/I及两案首轮保存/HTTP已通过；调度执行后已停止，S04及结束审计仍待，8–10后置 |
| 已有问题与完成边界 | [问题清单](docs/investigation/current-issues.md)、[OpenSpec 任务](openspec/changes/complete-socai2-investigation-chain/tasks.md) |

## 2 当前运行环境

| 项目 | 当前值与用途 |
| --- | --- |
| 目标 | 21，SSH 别名 `sting-infra21` |
| 核心与旧服务 | 原核心`v1.2-20261113-r1` / `processing-20261113-r1`记录保留；21旧业务容器已主动停止，其他29个容器保持。见上述停止回执 |
| 数据库 | PostgreSQL 16；正式`aisoc.socai2`及共享PG保留。新候选库`socai2_streaming_20261115`已由调查方完成123–129及身份供给，32表521列；身份与数据不混用 |
| HTTP / Swagger | 旧`192.168.1.21:18024/18080`已停止；候选`18424/18480`已启动并完成空态/合同读回。候选业务前缀`/api/v1/socai2`，80操作、无鉴权；S01业务创建及首轮结果读回通过，后续变化和整个change仍待验 |
| 本机与旧入口 | 本机最近观察18024接隔离`v12_upgrade_dev`，本次未操作。21旧主/独立入口也在停止清单内，不作为可用替代入口。部署与架构见[profile](deploy/http-service/README.md) |
| 调用上下文 | 候选内部默认可信，租户及记录操作人由`SOCAI2_HTTP_CONTEXT_FILE`指定；无需登录、Token或角色。候选tenant/actor已实际建立并与应用配置核对 |
| 页面读取 | 候选配置`SOCAI2_PAGE_READ_ENABLED=true`、`SOCAI2_ANALYSIS_READ_ENABLED=true`；包括 Case/H 的 GET；列表空态及S01真实A/I/Case非空结果已读回，H等其他场景按原证据范围 |
| Case HTTP 写入 | 候选`SOCAI2_CASE_API_ENABLED=true`；同库普通writer受控连接、TLS及零行更新回滚已验。成功建案衔接Kafka实际落库及A/I处理后的事件，保存并读回Case及首轮任务；空库就绪不算成功写验收 |
| 自动消费 | 21旧Fusion/投影/Agents均已停止；候选消费与调度由调查/测试另行按本期流程启用，HTTP启动不启用它们 |
| 配置 | 当前候选[HTTP profile](deploy/http-service/streaming-20261115-01/profile.json)及[部署说明](deploy/http-service/README.md)；凭据留在受控私有文件，不继承旧容器连接 |

模型单次时限 300 秒，Case 整轮 1500 秒，最终阶段预留 300 秒；单 Run 的调用与容量限制读取策略。租户累计调用、token、未结算数量配额不限制。失败、unknown 和待复核按实际状态保存。

`aisoc_app` 获授调查表 SELECT、两个只读函数 EXECUTE 及 `public.assets/public.users` SELECT。工作台使用 `socai2_prod_reader`，按需处理使用 `socai2_prod_processor`，入站来源读取使用 `socai2_prod_ingress`。只读账号、处理账号和数据库 owner 各按职责使用。

## 3 数据库与字段关系

原正式库123–127为**28表、450列**，原职责和字典见[调查表范围](docs/investigation/investigation-table-scope.md)、[机器字典](docs/design/socai2-data-contract-current.json)。当前21候选已应用128/129，为**32表、521列**，实际迁移及身份见[供给回执](docs/operations/evidence/streaming-candidate-20261115-01/database-prepare-01.json)。下表保留原主体关系，新增分析任务/尝试/主体状态及排除关系沿[当前结构入口](deploy/database/CURRENT.md)。业务后端通过HTTP对接，不需要复制调查表或旧AiSOC公共支撑表。

| 功能 | 权威表及主要关联 |
| --- | --- |
| 告警事实与分诊 | `alerts` 的当前材料／分诊／人工反馈指针连接 `alert_materials`、`alert_assessments`；同材料的来源和对象在 `alert_source_refs`、`alert_objects` |
| 事件与诊断 | `incidents → incident_alerts → alerts`；诊断指针连接 `incident_diagnoses`，诊断尝试按 `runs.incident_id` 查 |
| Case 范围 | `cases → case_alerts/case_incidents`；成员关系与显式事件关系分别展示 |
| 冻结输入和执行 | `runs → run_members/run_steps/artifacts`；Run 固定材料版本，步骤按 `seq/parent_step_id` 组织 |
| 正式结果及当前判断 | `results/result_members` 保存各轮结果；`cases.current_assessment_id → case_assessments → case_assessment_sources/case_assessment_members` 给采用依据和覆盖范围 |
| 人工确认 | `tasks → task_revisions`；范围、正文、完成人和完成时刻读取选中的版本 |
| 活动与读取保留 | `activities → activity_targets`；`comments`、`response_links` 有读取/关联用途，完整协作和真实处置写入未交付 |
| 问答依赖保留 | `conversations/messages` 仍被当前结果及发布校验引用；问答业务未开放 |

所有关联同时限定租户和父主体。显示名称、主机名和厂商编号不能替代 UUID。当前材料、历史冻结材料与外部来源分别读取。告警交接字段调整按 [AGENTS.md](AGENTS.md#调查数据库-v1-与人工确认)先列影响并确认；其他功能所需内部调整按 OpenSpec 推进。

需要独立部署调查服务时，按[服务部署说明](deploy/http-service/README.md)及[数据库安装入口](deploy/database/CURRENT.md)执行；普通业务联调只配置HTTP地址。

## 4 页面读取合同

后续业务后端通过 **HTTP** 对接，不要求直连调查库或照搬旧 AiSOC 表。完整参数、示例、错误及缺口以[本次HTTP交接包](deliverables/investigation-validation-20261106/http-handoff/README.md)为入口；原OpenAPI保留为结构来源。

下列路径均以 `/api/v1/socai2` 为前缀。前端优先沿响应中的身份和内容链接取数；完整参数、返回类型和限制以 OpenAPI 为准。

| 页面需要的数据 | GET 路径与说明 |
| --- | --- |
| 告警／事件列表和详情 | `/alerts`、`/incidents` 及 `/{id}`；列表默认 20、上限 50，按返回游标分页 |
| 成员、对象、来源、资产、活动、相关告警、响应 | `/alerts/{id}/records/{section}`、`/incidents/{id}/records/{section}`；默认 50、上限 200，按 `next_offset` 分页 |
| 告警材料 | `/alerts/{id}/materials/{material_id}`；保留版本、hash、原描述与结构字段，正文受限时返回 availability |
| A/I 尝试与步骤 | `/{alerts或incidents}/{id}/analysis`、`/{alerts或incidents}/{id}/analysis/runs/{run_id}`；在该完整 Run 路径下追加 `/trace` 或 `/artifacts/{artifact_id}` |
| Case 队列、资料与资料字段 | `/cases`、`/cases/{case_id}`、`/cases/{case_id}/page-data`；队列的筛选总数和全租户 metrics 分开 |
| Case 历史及指定结果 | `/cases/{case_id}/history`、`/cases/{case_id}/runs/{run_id}`、`/cases/{case_id}/results/{result_id}`；历史默认 20、上限 100 |
| Case 工件与冻结材料 | `/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`、同 Run 下 `/materials/{material_id}` |
| 非 Run 来源工件 | `/alerts/{id}/artifacts/{artifact_id}`、`/incidents/{id}/artifacts/{artifact_id}`、`/cases/{case_id}/artifacts/{artifact_id}`；按真实归属读原文 |
| Case 活动 | `/cases/{case_id}/activities`；含案件、成员和显式事件的匹配活动，去重并保留目标前后值 |
| 人工任务及版本 | `/cases/{case_id}/tasks`、`/cases/{case_id}/tasks/{task_id}`、`/cases/{case_id}/tasks/{task_id}/revisions`、`/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` |

“相关告警”按**同租户、同类型、同命名空间、同对象键**匹配当前材料，可跨 Case；它不表示因果关系。错误父主体返回404，正文不可用按实际状态处理。Case Run 的成员、步骤、工件和结果集合分别检查总数及截断标志。

## 5 状态、交付和空态

| 要表达的含义 | 取值来源和展示规则 |
| --- | --- |
| 业务处理状态 | 告警／事件／Case 的状态字段；Run 结束不自动关闭案件 |
| 机器执行状态 | `run.state/stop_reason`；有工件不代表执行成功，unknown 保持未知 |
| 交付完整性 | `run.delivery_state`；`none/partial/complete/unknown` 与待复核分开 |
| 事件交付说明 | `result.diagnosis.delivery_assessment.reasons/member_coverage`；部分拒收内容可沿 `partial_analysis` 读取 |
| 事件待复核 | `delivery_assessment.review_items.state` 为 `required/none_listed/unknown`；成员、发现及问题 ID 分别列出 |
| 采用与新鲜度 | `is_current_pointer/valid_for_current_input/freshness` 以及 Case 当前判断来源；完整保存不保证当前仍可采用 |
| 业务判定和模型质量 | 判定取该环节有效结果，`accepted` 是程序校验／采用状态，不能作为准确率或正文质量结论 |

**阶段一状态：本地验收完成，待统一发布。** 七步开发实施及直接验证已收口，以下保留逐步验收范围；统一发布和发布后验证见[阶段一交付待办](openspec/changes/complete-socai2-investigation-chain/stage1-problems-and-plan-20261114.md#发布与发布后验证待办)。后续调度问题不计入阶段一待办或关闭条件。

本地待发布的A/I v4已通过[阶段一步骤1保存读取验收](docs/operations/evidence/stage1-ai-retention-20261114-01/README.md)：引用问题不删除或改判原业务结论，未知引用不伪造证据，引用解析所得的空集合不以虚构依据补齐；引用诊断在既有E32/E33工件链的`model_response.content_json.citation_review`读取，原答另关联`original_response_artifact_id`，最终结果仍从原分析入口读取。A解释模板的真实事实来源不表示模型原引用正确，需与原声明区分。HTTP字段、类型和枚举不变，质量未检查/有问题与交付完整性分开；该本地实现尚未部署，不能据此推断21已生效。

Case C3 v3/Deep v2/C6 v2已通过[步骤2保存、读回及采用验收](docs/operations/evidence/stage1-case-retention-20261114-01/README.md)，同样仅本地待发布。Case `model_response.content_json.payload`保留`raw/derived/citation_review`，原答工件、请求、步骤和hash可追溯；C3汇总在`basis.citation_review`，Deep汇总及C6 report_json在`citation_review`。模型原结论和原状态沿原Result、当前判断与历史接口读取；实际证据链接可以为空，不能把空链接当成模型未分析或把采用当成质量通过。后续模型接收相关原内容及简短质量提示，角色仍为prior_analysis。54次GET、4次采用请求通过，真实stale与人工选择保护保留；该步骤2批次未改C3额度或补答。

[步骤3 C3正常输出合同](docs/operations/evidence/stage1-c3-contract-20261114-01/README.md)也已完成本地保存读取验收：当前Case策略将C3输出额度设为8192，新请求一次要求七部分，`c3_output`配置最多5发现并以`socai2.c3-output.v1`冻结到请求边界；提示、生成Schema与接收共用该值。48项直接检查和44次GET通过，5项原文继续进入C6，原答/派生/独立诊断仍沿既有工件接口读取。旧冻结工件、C6容量、告警字段和HTTP合同保持；该步骤3批次未实施补答；补答及内部展示后来已由步骤4/7分别完成，21发布仍待办，不代表真实模型质量通过。

[步骤4有界补答](docs/operations/evidence/stage1-c3-completion-20261114-01/README.md)已本地验收：初答、补答仍各有独立model请求/原答/响应，另存`source_snapshot`类型的`c3_section_completion`保留/合并工件，C3汇总在`basis.section_completion`给出工件ID、缺失字段和`field_origins`。合并是程序装配，不冒充单次模型原答；原length/失败保留，已完成字段不被覆盖。补答失败时C3保留部分原分析及缺项供C6读取，不派发半条计划。真实内网模型仅补followups、新隔离库19次GET通过；历史首答不重派，C6及采用未在本批重验，现有预算保持。HTTP字段、迁移及告警合同不变，仍未发布。

[步骤5补查分流](docs/operations/evidence/stage1-followup-routing-20261114-01/README.md)已本地验收。C4 `followup_dispatch.routes[].activity`及Deep汇总的`activity`以`socai2.followup-activity.v1`提供程序装配的实际活动：方式、query原答/投影工件、工具、状态、返回数量、是否复用及data/empty/not_queried/failed/unknown；`new_query_attempt_count`不能当问题已回答或资料已证实。原计划目标/方式/绑定保持，human不自动建任务，graph不计外部取证。新Case真实认证查询返回2条、湖上下文实际进入C6，Result accepted/uncertain/partial及47次GET一致；首轮unknown及33次读取保留。按负责人补充授权，21湖已写6条合成演练数据，程序/HTTP尚未发布。预算、C6预留及告警合同不变。

[步骤6原件存取](docs/operations/evidence/stage1-original-retention-20261114-01/README.md)已通过本地保存读取。既有Case/A/I工件详情及告警材料详情不再因超过1 MiB拒读，`content_json/content_text`仍返回完整原件，工件按原size/hash核对；列表仍为元数据。后台A/C2/C4回执的`rows`保持原数量上限，额外探测行单独留在`overflow_rows`，完整已取得行按两段顺序拼接；不能将额外行当模型已使用材料。新Run输入工件通过source_refs关联`socai2.runtime-policy.v1`完整配置快照。阶段input指针为空时从同Run输入及子步骤沿不可变ID读取，禁止读latest补历史。历史未保存配置、未收到正文、unknown分别保留。新批7份大原件、26次GET及历史8Run/176工件/73次GET通过，告警字段与HTTP Schema不变，未发布；节点预览和结论展示已由后续步骤7完成本地验收。


[步骤7内部展示](docs/operations/evidence/stage1-viewer-20261114-01/README.md)已本地验收：同主体/source_run_id的原结论直接显示，执行、交付、引用问题、待核和保存时/当前采用分开；取消I仅有记录无正文时明确未保存结论。C3初答/补答/合并及来源分开，长原件按配置预览后完整展开；14项离线、11快照逐值读回和21项实际浏览器检查通过。本机4178预览，实际4177与核心/独立HTTP未发布，产品页面接线不据此判完成，固定HTTP合同未改。

阶段一[接口影响评估](docs/operations/evidence/stage1-viewer-20261114-01/http-impact.md)明确固定Schema相同也存在读侧兼容依赖：接口侧在同一只读PG快照对比旧/新freshness_sql，旧判stale、新判current；旧正式reader还会按1 MiB门槛拒读新大原件。核心与独立API须在整体交付时同步读侧及动态工件解释，不能只更新生成端。可信认证及docs20候选属于接口侧另一范围，不能当作本阶段字段变化。 当前收口口径见[阶段一统一目标版本交接](openspec/changes/complete-socai2-investigation-chain/stage1-problems-and-plan-20261114.md#10-阶段一稳定交接与统一目标版本)：本地验收完成，待统一发布；不开展旧版兼容层或双轨工程。

`null` 表示未记录或不可得；空数组表示对应集合为空；`0/false` 是有效值。未查、失败、成功查空分别显示，查空不证明安全。费用和 token 未知不能填零。已保存证据目录的条目数、威胁数与没有目录分别处理；威胁数为零不等于“已证明无威胁”。报告建议不得显示为已执行响应。

## 6 Case 与人工反馈操作

既有操作路径、入参及存储关系见 [Case/H 操作交接](openspec/changes/archive/2026-11-11-enable-case-human-http-flow/handoff.md)。按创建 Case 返回的 pending_run_id 显式启动首轮；人工任务通过 POST 创建、PUT 修订，使用返回的 row_version 和 current_revision_id；再次调查先 prepare 再 start。保存反馈不会自动启动调查。

人工采用与未完任务、后续调查及结案的规则见[AD01–AD06](docs/investigation/result-adoption-and-pending-work.md)。调查核心统一资格、未完工作确认、预览时效、幂等和判断历史；HTTP复用核心提供E21/E63/E64，两端服务及Swagger已同步。[后端调用指南](docs/integration/result-adoption-http.md)。采用只改变当前判断，不结束任务、Run或案件；无数据库迁移或告警字段变化。

人工结果来自 `tasks.current_revision_id → task_revisions`。每轮领取时冻结所选修订到输入工件 `task_revisions/source_materials`，正文、范围和 human_statement 归属保持，旧修订及历史输入不被覆盖。Result 的六项结论/校验/发现/问题/建议仍使用原字段合同。前次 Case/H 批次没有表列、枚举、告警交接字段或 HTTP DTO 变化。

前批本地完整路径及21原登录方式下的Case/H写读已通过；本轮可信方式另见新验收记录；产品页面交互仍需对应前端承接。[配置示例](deploy/aisoc21/case-http.env.example)说明功能写入连接，普通 API 的 DATABASE_URL 保持；不增加权限设计或确认环节。

Case基本管理现新增E44–E47：GET/PATCH `/cases/{case_id}/management`、POST `/close`与`/reopen`。局部修改省略保持；description/owner_id/severity为null清空，tags=[]清空。结案拦截running/unknown；未完人工任务须确认并填写理由，任务保留。重开恢复in_progress，不自动调查；当前结案字段清空，旧理由和前后值可从E17活动读取。所有写入带行版本及幂等键，已在本机/21各20次TCP及SQL验证。页面修改不在当前交接范围。见[本项验收](openspec/changes/archive/2026-11-12-manage-investigation-cases/validation.md)。

## 7 知识能力与当前交付范围

调查可按技术解释、取证指导、历史案例参考三个目的检索知识。资料原文和向量索引分别保存，查询后回读原文及校验内容；具体输入输出见[知识交接](docs/investigation/case-knowledge-handoff.md)、[历史卡片字段](docs/investigation/historical-alert-knowledge-handoff.md)。知识是参考材料，不是本案发生过某行为的证据。

历史固定流程已交付分诊后知识同步；本期第10步后台异步维护后置；候选已完成S01的A/I及Case首轮调度，这不代表知识异步维护已交付。知识维护属于独立组件能力，不在当前80项调查HTTP中；[组件指南](docs/integration/component-handoff-current.md)的旧主API入口须结合暂停状态读取，不能在本轮直接调用。

当前候选共有80个HTTP操作；E19提问、E20保存回答仍未实现，保留501合同。各页面AI对话（助手入口、提问/追问、会话历史、回答读取/保存）继续暂缓；告警分诊、事件诊断、Case调查及结果采用按既定范围推进。其他后置能力见[实施计划](docs/investigation/http-implementation-plan-20261112.md)，不扩展旧AiSOC功能。

API功能测试和模型结论质量分别验收：Case及告警/事件管理分别完成HTTP和数据库读回，真实完整调查的模型质量仍未通过。自动分析消费者未启用；显式调用后的内部流程由程序执行。当前部署、验收证据和后续工作以[PROGRESS](PROGRESS.md)为准，历史失败不改写；现有页面只用于测试。

### 三类列表完整导出

E54告警、E55事件、E56调查均为`GET /api/v1/socai2/{alerts|incidents|cases}/export`。输入沿用对应列表筛选和排序，加可选`columns`字段路径；不传分页参数。结果为全部命中的CSV附件、实际数量与观察时间，超过配置上限明确报错，不截断。三类公开列分别39/34/31项，逐列含义与默认列、空值/转义规则、下载例子见[HTTP指南](deliverables/investigation-validation-20261106/http-handoff/README.md#完整列表导出)。资产维护及模型流程不受影响。

### 事件顶部归并统计

E57 `GET /api/v1/socai2/incidents/grouping-summary`输入为可选告警来源和真实发生时间范围，返回总告警、已归并、未归并、去重事件及处理中事件数、压缩比例和观察时间。压缩以已归并告警为分母，空分母为null；顶部统计独立于表格关键词/负责人筛选。[逐字段说明及例子](deliverables/investigation-validation-20261106/http-handoff/README.md#事件归并统计)。

### Case普通评论

E58 `POST /cases/{case_id}/comments` 接收operation_key及非空白body，保存原文、实际作者和时间；E59 `GET` 同路径按limit/offset读取。前缀仍为`/api/v1/socai2`。同键同意图返回原评论，改意图409；E17可读活动。评论不自动作为已核实事实，任务、Run和案件判断保持；本批不含附件上传或下载。[输入输出及逐字段说明](deliverables/investigation-validation-20261106/http-handoff/README.md#case普通评论)。

### Case附件引用

附件是用户为案件补充的文件，例如工单PDF、截图或日志。业务后端负责上传/保存/下载；本服务用E60 `POST /cases/{case_id}/attachments`登记后端已保存的file_id、名称、类型、大小和可选哈希。E61 `GET`同路径分页查询，E62 `GET /cases/{case_id}/attachments/{attachment_id}`读取单项；E17查活动。返回id是关联ID，file_id用于业务后端下载。availability=managed_by_backend不表示本服务已探测文件存在或下载成功；附件不自动变成已核实事实或触发调查。[完整对接步骤](deliverables/investigation-validation-20261106/http-handoff/README.md#case附件引用)与[两端验收](openspec/changes/archive/2026-11-13-link-case-attachments/validation.md)已同步。
