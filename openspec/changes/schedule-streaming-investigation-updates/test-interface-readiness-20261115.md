# 测试所需模块与HTTP接口供给清单

更新于2026-11-16，配套[完整测试规划](full-flow-test-plan-20261115.md)和[数据设计](test-data-design-20261115.md)。本文件列责任、依赖和交付要求；当前运行基线见总计划7.1，新要求见本页“本轮新增供给”。旧T1/候选/W步骤保持历史适用范围，不作为当前配置。

**T1历史快照（2026-11-15，旧服务暂停前）：** 当时21库为127/28表450列，HTTP64操作/静态Swagger71，无凭据GET401；[原始证据](../../../docs/operations/evidence/investigation-test-preflight-20261115-01/README.md)保持。随后另建候选并接入r2 HTTP，不能用本段旧版本/旧库作为本轮目标或当前阻断。原步骤8–10/IF09、IF10、IF12后置保留设计，不作为本期1–7验收前置。IF07仅initial首轮，IF08才check/rerun；当时80操作候选已撤E11/E13；随后正式发布状态以总计划7.1和最新实测为准。

## 1. 谁先提供接口

**2026-11-15候选衔接记录（历史）：** [T2离线材料](../../../docs/operations/evidence/test-streaming-data-t2-20261115-01/README.md)、[S01发送器](../../../docs/operations/evidence/test-streaming-sender-20261115-01/README.md)及[W2组件/TCP空态和错误](../../../docs/operations/evidence/test-http-proxy-w2-20261115-01/README.md)已通过；W2非空/跨Run已通过，W3页面已完成本步只读联验，W4包仍待。[候选数据库准备](../../../docs/operations/evidence/streaming-candidate-20261115-01/database-prepare-01.json)为123–129、32表/521列、同候选tenant/actor；[HTTP r2候选18424/18480](../../../docs/operations/evidence/streaming-http-runtime-20261115-01/final-readback-01.json)已实际接入并通过80操作/无鉴权/三类空态及Swagger合同核对。入站按[最新ingress.json](../../../deploy/aisoc21/streaming-candidate-20261115-01/ingress.json)及[r3 ready-02](../../../docs/operations/evidence/streaming-ingress-20261115-01/ready-02.json)完成实际就绪；首批来源失败保留，入口修复[21项直接检查](../../../docs/operations/evidence/test-source-scope-fix-20261115-01/README.md)与[r3新批两道真实复验](../../../docs/operations/evidence/test-streaming-s01-ingress-20261115-02/README.md)均通过。入站时为新12上下文、3A/1I/3真实来源/4accepted任务及0Run/模型；随后[真实A/I保存核验](../../../docs/operations/evidence/test-streaming-ai-20261115-01/README.md)已通过，4task/4attempt/4Run及4真实生成，模型正文NOT_PASSED；[本步62次HTTP结果读取](../../../docs/operations/evidence/streaming-ai-http-20261115-01/result.json)已通过。入站实际映射与[35次HTTP非空GET](../../../docs/operations/evidence/streaming-ingress-http-20261115-02/README.md)已同源核对通过。[旧服务暂停回执](../../../docs/operations/evidence/streaming-old-services-pause-20261115-01/pause-01.json)保持；旧版本和旧ID不作候选依据。HTTP空态不等于业务写入；成功建案并入S01真实来源→Kafka→A/I→首次整事件建案，同key和管理编辑复用该Case。供给和最小顺序见[当前T2入口](../../../tools/testdata/STREAMING.md)。

顺序为：**明确业务操作/测试预期 → 功能模块给出用例及数据合同，HTTP侧共同定公开合同 → 各自实现 → 模块直接验证 → HTTP联合验收 → 4177/产品前端按合同接入。** 已定稿接口直接复用，不因本文件重新审批；未完成实现也先把测试数据和用例列全。

| 提供方 | 必须提供 | 不替代的职责 |
| --- | --- | --- |
| 产品/前端侧 | 操作意图、必需展示/跳转字段、空态和错误处理；复用既有125项与后续P项 | 不负责设计调查存储，不直接查库/Redis、不补造业务判断；页面完成不是后端测试前置 |
| 调查功能模块 | 可调用用例/端口、输入输出类型、状态/错误、真实存储来源、迁移/配置依赖、最小成功/失败样本与读回 | 不依赖对外HTTP包；C1–C6内部阶段无需逐个暴露HTTP |
| 调查HTTP后端 | 最终path/method、DTO/OpenAPI、状态码/错误、幂等与分页、真实task/Run/Result/原件链接；挂载和配置说明 | 通过核心用例实现，不重复调查业务、不暴露Redis或内部领取操作 |
| 业务后端/来源模块 | 资产/人员、文件、日志/知识等实际来源的接入或准备方式及身份映射；响应执行仍属其边界 | 无调查写入口的来源不能让测试驱动随意造业务表或假回执 |
| 独立测试服务 | 场景/批次、准备、步骤驱动、预期与实际核对、质量问题、只读测试API和4177发布 | 不实现另一套调查算法，不创建伪造A/I/Case结果；不把测试metadata加入业务DTO |

需要先有**两层合同**，不是先让前端发明接口，也不是等所有HTTP实现后才写测试。模块可以先直接验证；最终HTTP链必须等对应路由及真实用例接通。一个依赖未就绪只阻断依赖它的用例，其他已定能力继续。

## 2. 每项供给的最小交付内容

1. 业务目的、输入字段/类型/空值/范围、返回字段及语义，相关当前合同链接和版本。
2. 内部用例位置/签名及所需配置；对外操作的method/path、状态码、错误体和实际OpenAPI。仅定义了路由但未挂载要明确标出。
3. 写入成功后如何读取同一对象，主体→task→attempt/Run→结果→步骤/原件的真实关系；无Run、无结果、失败/unknown如何表示。
4. 幂等键、版本、范围冻结、分页、来源可用性及副作用规则，最小成功/空态/失败示例。示例必须标示意或实际批次，不能混用环境ID。
5. 数据库增量、来源适配、服务版本和profile依赖；附不含秘密的运行方法及可使用的独立样本。
6. 就绪证据：模块直接存取、HTTP实际调用/读回及相应未验边界；不能用Swagger生成或200代替功能完成。

公共告警字段保持冻结合同；确需变更按项目既有规则另列影响并确认。此表不增加常规权限审批、临时兼容接口或占位实现。

## 3. 供给与缺口登记

状态是2026-11-15文档/源码核对快照，执行前按实际证据刷新。“本地已验”区分提供方原批与测试侧F4/F5独立新批，不表示21或本机常驻服务已验；各用例只按已覆盖变体登记，不能把52组或21整链整体标通过。路径省略`/api/v1/socai2`，测试专属接口另用独立前缀。

| ID/提供方 | 需要的接口或模块合同 | 核对时状态与待供给 | 解锁用例/原步骤 |
| --- | --- | --- | --- |
| IF00 测试服务/运行维护 | 显式环境profile、只读预检、精确清理plan/回执、版本和实际能力清单 | 旧清理工具是旧public/21专用；T1只读检查与W1账本组件已完成，候选profile和真实入站/来源准备已验，no_cleanup保持；通用清理执行不由本批验收，W4/W5独立包部署仍待 | F00；T1/T3 |
| IF01 入站/Fusion/socai2直存 | RawAlert/source-v1与日志事件信封；fused持久身份；当前native入站用例、事件归并、重复/held语义 | A/I原生接线已本地验；21候选入站资源/Fusion r3就绪、修复直接21项及新批12上下文→3告警两道真实验证通过；旧批来源失败保留，新批来源范围正确，同批35次HTTP非空读取已通过。配置AISOC_ALERT_STORE_SCHEMA=socai2，由consumer→Socai2AlertSink同事务保存材料/initial任务。旧projection保持停止；不能用测试脚本直插socai2替代Kafka验收 | F01/F02；主步骤3/4 |
| IF02 来源/知识模块与业务后端 | 日志导入和process_activity/network_connections/authentication_activity查询；资产/账号、C2知识三目的检索、工具目录可用性 | 本批1条资产已导入并普通reader读回；A的资产/历史/情报9次真实PG查询通过，I沿配对回执。账号用途未单独接入；[2份知识正常导入/reader读回/真实embedding索引检索](../../../docs/operations/evidence/test-streaming-case-initial-20261115-01/source-acceptance-01.json)已通过（4适用行、2排除、历史3次查空），[两Case实际C2使用和C4查询](../../../docs/operations/evidence/test-streaming-case-initial-20261115-01/case-validation-01.json)已核（知识4/2行、两案各2次日志补查），[同Run 58次HTTP结果读取](../../../docs/operations/evidence/streaming-case-result-http-20261115-01/result.json)已通过，质量问题及partial状态保持 | F00/F05/F11；T3 |
| IF03 调度/任务核心 | accept/check、attempt/Run绑定、N/串行/有限重试/unknown收尾、周期扫描及持久任务读取 | 通用生命周期/Redis及A/I/Case执行器已本地联验；21唯一调度已完成本批4task/4attempt/4Run、4真实生成并正常停止；旧4task实际跳过无attempt/Run，程序保存核验通过、正文质量NOT_PASSED。知识后台异步仍后置；既有可控依赖证据仅验证对应程序行为 | F02–12；步骤1–10 |
| IF04 HTTP读侧 | 三类主体analysis-tasks列表/详情；`/analysis-runs`；`/{run_id}/steps`、单步和artifacts；A/I结果与原件GET | R1/R3/R4、公共任务GET及A/I读回已本地验；21 r2/80操作候选TCP空态及S01新批A/I材料、来源、成员、任务非空读取已通过；同批4Run结果/17步骤/45原件目录及29正文的62次GET已通过；两Case首轮58GET、S04失败44GET及W2真实非空/跨Run来源34GET已验；Case正向更新比较未通过，正式服务待统一发布 | F02/F13；2.7 |
| IF05 I模块+HTTP | `POST /incidents/{id}/diagnose`，mode=check/rerun；I首轮/周期执行、选入范围和实际覆盖 | E37异步202及真实handler已本地联验；运行前核实际路由和迁移128，不能调用旧同步旁路 | F03/F06；步骤4 |
| IF06 Case分配模块+HTTP | E01创建、E07替换、E08关联、E09移动；CaseAllocation/Replacement/MoveReceipt（含excluded_alert_ids）；related-cases、事件case_receiving | 整理期间新增[核心验收](../../../docs/operations/evidence/case-allocation-20261115-01/README.md)和[HTTP供给指南](../../../docs/integration/case-allocation-http.md)，本地分配/受理/读取已供给，依赖129；本批执行前仍核实际TCP/配置，Case执行不在本步 | F04；步骤5 |
| IF07 Case执行模块+HTTP | E01受理后自动首轮，C1–C6/Deep执行；E12/E14及原件；Case investigations check/rerun归IF08 | **development=local_verified，candidate_http=nonempty_verified，real_initial=flow_passed_quality_deferred**：原受控依赖开发证据保持；21同批两Case已完成4次真实生成/4次真实C4查询，277保存核验和58GET通过，均accepted/uncertain/partial，质量NOT_PASSED。W2代理读回原Run/Result已验，正式发布仍待；下方79操作只保留历史证据 | F05/F13；步骤6 |
| IF08 Case更新/H+HTTP | `POST /cases/{id}/investigations` check/rerun；整事件I→活跃Case、单告警固定范围、有效H、独立排队/执行前检查、冻结与上一轮比较 | **development=local_verified，audit=F1–F5_fixed_final_audit_pending，candidate_S04=failed_I_output_truncated**：F1/22 GET、F2/24 GET、F3/52 GET局部齐备，原80操作保持。F4测试侧31项离线及新磁盘隔离PG/Redis六组流程、独立retry_guard通过；同批78+11次PG强制只读/ASGI GET通过，19/10表摘要保持。F5源码已修，提供方28+84项离线及测试侧新PG/Redis A→I→Case/Deep/C6四组检查通过（5份模拟回复、0真实模型），同批90次GET及19表前后摘要核对通过。旧失败原件保留；21 S04已真实执行，I output3000/length失败、3等待check跳过、0新Case，134失败保存检查及44GET通过，W2只读同源状态已验；正向更新/比较未通过 | F06/F07；步骤7；TC-Q02/Q03、C07–C11/H01–H02/R03/E02；A02/I01/C01模型前可读断言 |
| IF09 定向模块+HTTP | `POST /cases/{id}/targeted-investigations`、`GET /cases/{id}/investigation-tools`及analysis_context | 目标HTTP8.2已定稿、待实现。给出真实范围/工具选择/targeted结果及不自动综合规则 | F08；步骤8 |
| IF10 综合模块+HTTP | `POST /cases/{id}/syntheses`；targeted_result_ids、适用前序、source_results、updates_full_baseline | 合同已定稿、待实现；需prerequisite_unavailable和跨Run来源可读，不增加“重新全跑”兜底 | F09；步骤9 |
| IF11 管理/采用/配套HTTP | E63预览→E21采用→E64历史；E44–47；列表/导出、评论/附件引用、故事/探索、相似/同主机查询 | 既有功能/证据复用；预览需覆盖未开始分析任务，运行中采用保护/关闭与新生命周期联验。真实文件上传下载由业务后端供给 | F07/F10/F14；2.7 |
| IF12 知识后台模块 | A提交后knowledge_sync、源资格及卡/向量回执，C2检索仍用真实来源 | 同步知识已有；非阻塞低优先队列待步骤10，不能将旧同步成功当新异步验收 | F11；步骤10 |
| IF13 测试服务+4177 | 批次/用例/准备/操作映射/质量只读HTTP；4177经HTTP读取调查任务/Run/结果/原件，独立发布 | W1账本与8GET、W2组件及候选TCP空态/错误已通过；W2本批真实非空及C1→原I输入跨Run来源34GET/107检查通过；[W3页面0.3.0](../../../docs/operations/evidence/test-viewer-w3-20261115-01/README.md)本机临时服务→21候选浏览器只读联验已通过；W4包/W5及测试服务21部署未完成，整体不是runtime_ready。静态/SQL历史回看不算新HTTP接线 | F00/F13/F15；测试服务交付 |

完整业务字段以目标HTTP合同为准，本文不复制第二套DTO。仅Case构造受理回执不足以证明实际执行；IF07开发补证验证了受控依赖下的执行与读取，仍不证明21或真实模型链通过。相关读取就绪不表示定向/综合提交已实现。

### IF07开发供给补证（T1结束后，不改21快照）

完整供给以[Case首轮HTTP交接指南](../../../docs/integration/case-initial-http.md)和[最终验收回执](../../../docs/operations/evidence/case-initial-http-20261115-01/README.md)为入口；79操作候选Swagger的预览方法见[文档包说明](../../../deploy/api-docs/README.md)。这些均为待发布开发交付，不改变21就绪结论。

2026-11-15收到HTTP协作回执，已只读核对现有证据：独占开发批`case-initial-http-20261115-01`的[创建](../../../docs/operations/evidence/case-initial-http-20261115-01/create-pg-01.json)、[执行](../../../docs/operations/evidence/case-initial-http-20261115-01/consume-01.json)、[正常读取](../../../docs/operations/evidence/case-initial-http-20261115-01/read-pg-02.json)及[边界读取](../../../docs/operations/evidence/case-initial-http-20261115-01/boundary-pg-04.json)通过。真实隔离PG/Case程序，模型及湖为明确替身；本批2次模型替身、0真实模型。边界读取复用核心已结束的5个Case，涵盖容量失败、后续案完成、缺时、查询失败和冻结成员；未重复消费旧批。

[候选OpenAPI](../../../docs/operations/evidence/case-initial-http-20261115-01/candidate-openapi.json)实数79业务操作、无security声明，外部E11 prepare/E13 start已撤，Case investigations仍未挂载。IF08保持第7步check/rerun供给；本次仅刷新IF07开发证据，保留原错误回执，不重开T1、不更新其历史readiness快照、不将开发环境作为用户运行测试目标。21仍等待发布，正式TCP与真实模型流程验收保持未执行。

### IF08开发供给增量：受理和已结束样本读取

上述IF07的79操作/未挂Case investigations是第6步历史快照。第7步[受理和读回回执](../../../docs/operations/evidence/case-update-http-20261115-01/README.md)及[阶段摘要](../../../docs/operations/evidence/case-update-http-20261115-01/admission-readback-summary.json)已核：候选挂载80操作，无security；28次真实隔离PG/ASGI GET读取7A五轮及八任务（三次无变化），19类记录摘要未变；20次受理请求（15 POST/5 GET）保存三个accepted任务，未消费、0attempt/Run/模型。该候选OpenAPI仅挂载快照，不是最终交付Swagger；7B、7C完整新批执行和真实TCP未验。

真实读取发现HTTP把核心RunView/ResultView误当字典访问的bug，已按实际结构化对象修复并保留原失败；[功能用例TC-R03](functional-test-cases-20261115.md)明确使用实际返回类型验证适配。局部开发证据不改变T1历史快照或21 awaiting_release。测试设计现已独立覆盖业务要求，供给交接只需将用例绑定实际合同/入口和证据，不等待接口才设计预期。

设计补齐期间进一步核到核心[7B读回](../../../docs/operations/evidence/case-updates-20261115-01/read-7b-03/result.json)、[生命周期](../../../docs/operations/evidence/case-updates-20261115-01/lifecycle-02/result.json)、[自动容量续建](../../../docs/operations/evidence/case-updates-20261115-01/read-auto-capacity-01/result.json)及[HTTP来源任务消费](../../../docs/operations/evidence/case-updates-20261115-01/http-consume-01.json)均为passed：原受理三任务已由核心执行为initial completed/check skipped/rerun completed，不再停在accepted。模型为替身、真实模型0；后续HTTP终态/原key回放与最终交接待7C回执。此增量只更新当前供给，不改写前段0Run的受理时点事实。

## 4. 具体提交与读取顺序

F4原失败批的[局部读取](../../../docs/operations/evidence/case-trigger-fix-20261115-01/http-partial-read-01.json)已核：59次无鉴权GET、19表摘要保持、0写入/新执行/模型；`full_F4_accepted=false`及历史手动check failed/unknown保持。后续存储已复制到本机新磁盘隔离库28413、34表计数一致且旧数据保留；测试侧[新批直接验证](../../../docs/operations/evidence/test-f4-independent-20261115-01/README.md)六组流程及retry_guard通过（23 task/13 Run、22次模型替身、0真实模型），手动历史I检查已完成。同批[主流程78 GET](../../../docs/operations/evidence/case-trigger-fix-20261115-01/http-full-read-02.json)及[guard 11 GET](../../../docs/operations/evidence/case-trigger-fix-20261115-01/http-retry-guard-read-01.json)通过，19/10表前后摘要一致，0新执行/模型/写入；首次缺分配策略配置的关联GET 503已单独保留。PG强制只读/ASGI，不替代21 TCP；不将旧失败批的局部GET当成新批接口验收，不重派旧任务。

F3的[HTTP最终摘要](../../../docs/operations/evidence/case-retry-fix-20261115-01/http-final-summary.json)已核：52次PG强制只读/ASGI GET、15表本租户摘要不变、0模型/执行/写入，80操作不变；TC-Q02/Q03可复用核心重试及HTTP终态来源。task本地failed、attempt ended/unknown和Run unknown/ended_at空分层表达，不混同；retryable不代表尚有重试。60秒/等待中间态复用核心保存快照，本HTTP未重演，不能记真实故障或21 TCP通过。

F2的[HTTP最终摘要](../../../docs/operations/evidence/case-input-metadata-fix-20261115-01/http-final-summary.json)已核：24次真实隔离PG强制只读/ASGI GET、17表本租户摘要不变、0新执行/模型/写入，80操作不变。管理owner/tags后Case check无变化无Run，原A/3份查询保持；后续明确手动反馈check保存A与独立反馈。公开A历史freshness仍stale，Case同材料前序A可用为true，测试/消费方不得混同；见[TC-C07/A03/H02的F2局部记录](functional-test-cases-20261115.md#f2局部证据供给已核未重派)。A模型未返回的核心PG读取只补持久化观察，本HTTP批是结束后读取；自动链、实时HTTP与其他审计项另验。

F1的[范围修复HTTP摘要](../../../docs/operations/evidence/incident-case-scope-fix-20261115-01/http-final-summary.json)已核：原I3选1/覆盖1、Case3成员、C1/C3/C6范围同源；后续新I不改旧Case输入。22次真实隔离PG强制只读/ASGI GET，19表本租户摘要未变，无新业务执行/模型/写入，OpenAPI80操作未变。TC-I03/C06/C09可复用本局部证据，Case模型未返回读取可供TC-C01复用；核心历史展示测试及HTTP01/02测试断言失败原件保留，不标整组或L5通过。详细边界见[功能用例F1供给记录](functional-test-cases-20261115.md#f1局部证据供给已核未重派)。

**当前供给状态补充：** 第7步[最终开发交接](../../../docs/operations/evidence/case-update-http-20261115-01/final-summary.json)已完成136请求及终态读取，前文“7C待收口”仅保留为当时证据进度。随后独立审计未通过；F1–F5按负责人最新授权逐项修复，不能将原7C交接提升为审计/完整流程通过。全部新回执齐备后再由调查、HTTP及测试共同给出完整测试准入结论。

新增供给核对不要求新造接口：A/I/Case已保存对象/关联/task在模型未返回时，应通过现有列表/详情/任务/Run接口可读，未开始Run可空、进行中Run有真实状态、无新结果与旧结果并列可辨；完成后独立结果及来源可读，失败保留对象/旧结果。复用原202/accepted/终态/GET无副作用证据，只补实际模型未返回观察点和缺陷直接边界。整事件自动材料链经I有效业务更新，单告警固定范围/晚到A不直触Case；首轮/手动/H保留。上述为当时审计计划；当前W1/W2及21候选实际供给已验，最新进度见表及下方记录，不沿用旧等待状态。

| 流程 | 真实请求与读回 |
| --- | --- |
| 新A | 正常入站→取得canonical→`GET /alerts/{id}`和analysis-tasks→实际Run/assessment→步骤/原件；不提供E36手动触发 |
| I | 自动任务或`POST /incidents/{id}/diagnose`→202 task→任务GET→实际I Run/result→input_selection/analysis_coverage→步骤/原件 |
| 新Case | `POST /cases`→201真实allocations/各新案initial_task→任务GET→实际Run→E12/E14；不返回供调用者再次start的pending_run_id |
| Case更新 | `POST /cases/{id}/investigations`→202 task；check可skipped/no_changes且无Run，rerun实际执行新Run |
| H | POST人工tasks→PUT完整修订→当前/历史GET→下次完整调查读取对应修订；人工task与analysis-task类型不同 |
| 定向/综合 | 对应POST各返回task；E12/E14读取analysis_context；定向结果独立，综合明确选择其结果ID |
| 采用/关闭 | 各自预览/管理条件→带版本/操作键提交→当前判断/历史/活动GET；不把提交结果当执行队列控制 |
| 4177 | 测试API列batch及真实身份映射→调查API按subject/task/Run读取→分页步骤/原件→content_url原文；质量由测试API关联相同Run/工件 |

刷新与GET不启动模型，不以重新POST获取最新状态。实际业务受理失败/未知先读原操作映射和主体，不能自动换key。HTTP路由未提供、503、合法空结果和不存在的404分别显示；未完成依赖不伪装成空业务数据。

## 5. 就绪表与协作交付

每个IF在执行批次记录`contract_revision/module_revision/http_revision/profile_hash/schema_version/provider_status/evidence/blocking_cases/next_delivery`。provider_status取`contract_pending / implementation_pending / local_verified / runtime_ready`，用例结果另记，不能由runtime_ready推导passed。已定合同的未实现项用implementation_pending，不能反复要求负责人选择已确认业务规则。

T1已填写21实际就绪表，并将缺项定位到本表责任模块及原主线步骤。模块提供最小用例与样本后先验本模块；HTTP同一步完成输入→保存→读回；4177按该能力的数据合同接入。本文未要求模块为每个内部阶段增加HTTP，也不等待产品前端实现后才做服务验收。

负责人最新指定协作时点为**调查第7步完成后**。收到完成回执后，调查实现模块给出持续更新/check/rerun/H/上一轮比较的实际用例、配置及单点证据；HTTP后端给出对应最终合同、实际受理/错误/读取样本和发布依赖；测试侧据此更新IF08、数据切片、预期及分层执行顺序。先完成三方供给与计划对齐；21仍需对应版本发布并复核就绪，才进入实际运行测试。第8–10步继续后置，T1历史快照不改写。

为落实“测试/修复及第11步交付后再正式发布”，21就绪分成[候选验证部署→正式发布→发布后读回](full-flow-test-plan-20261115.md#51-第7步之后候选验证正式发布与读回)。IF00还需调查/发布方提供可执行候选profile：冻结核心/HTTP/策略版本、独立服务/端口、数据库/迁移/租户、Kafka Topic/group、Redis namespace、上下文和测试服务目标。发布fragment本身不等于已运行profile；实际候选供给已在下方当前记录核实，正式旧服务或开发ASGI不能代替。第7步交付前的等待条件仅适用于当时，第11步后续候选已按授权运行；正式发布仍需完整验收/独审。

T1只读结果见[回执及逐模块交付清单](../../../docs/operations/evidence/investigation-test-preflight-20261115-01/README.md)。随后测试侧按新授权实际执行本机F4/F5隔离批，模型/来源模拟，0真实模型；未实施业务模块、改DTO/表、启动21消费者或发布。该时点21版本差异等待候选供给；后续实际候选和运行见下方，分层顺序保持。

### F5后共同准入记录

F5[90次同源HTTP读取及最终摘要](../../../docs/operations/evidence/execution-contract-fix-20261115-01/http-final-summary.json)已核，19表保持，0新增执行/模型/写入。HTTP侧已冻结80操作合同及43份HTTP源码，发布片段补齐两个可信装配文件后为110份声明源码/4份公开配置；这是组装供给，不是完整候选包已部署。HTTP提供方的[第11步供给意见](http-workflow-contract-20261114.md#第11步http准入与实际供给)当时与测试侧结论一致：不能仅凭组装供给启动21完整测试；后续实际候选已按新授权分步运行，以下更新当前事实。

当前调查方已供给候选库/迁移/租户、Fusion r3和实际profile，HTTP18424/18480为r2/80操作、同库双池TLS。S01新批原生入站及35GET、真实A/I与62GET、两Case首轮277项保存核验及58GET已完成；正文质量和partial边界保留。最新[S04验收](../../../docs/operations/evidence/test-streaming-s04-20261115-01/acceptance-01.json)：E13先入湖/A04后入站归原I，A04完成；I真实模型length/3000而失败，无新Case任务/扩员/Run，134项失败记录核验和44GET通过，成功更新/比较未通过。旧原件保持、0重试、调度正常停止。测试侧[W1](../../../docs/operations/evidence/test-ledger-w1-20261115-01/README.md)、W2组件/TCP空态及[非空/跨Run来源](../../../docs/operations/evidence/test-http-proxy-w2-live-20261115-01/acceptance-01.json)均已验；最新34GET/107检查保留原失败和来源范围，W3页面已完成26业务GET真实浏览器读取及8Python/8JS直接检查；W4–W5仍待。责任顺序见[总计划5.4](full-flow-test-plan-20261115.md#54-f5之后的21完整测试准入与实际下一步)，不把真实业务HTTP读取计成4177接线。

PG供给条件按负责人最新决定改为普通账号密码，默认require，不要求客户端CA/证书/私钥。新r2候选取代旧r1证书前置；[独立小验证](../../../docs/operations/evidence/pg-password-connection-20261115-01/README.md)已证明21现有reader的无CA TLS1.3/正反密码，以及本机普通LOGIN经真实HTTP两池的密码/回滚写入。两环境证据分开，本机disable不算require写入；新候选库及HTTP TCP/双池TLS/空态已供给，W2代理组件/TCP空态已通过，后续真实非空/建案/结果读取见上述批次；PG连通本身不核销完整流程。

## 本轮新增供给：输入过滤与异常继续

当前processing r3、正式HTTP r2及4177 0.6.0已有整链保存/读取证据；新能力仍按“功能合同先明确→模块单点→HTTP存取→页面→21真实链”推进。调查模块维护`stage11-output-continuation-design-20261116.md`及对应spec/tasks，测试只细化TC-N01–N11，不复制业务实现任务。

| 提供方 / 既有IF | 必须补交的具体内容 | 对应测试 / 当前状态 |
| --- | --- | --- |
| 调查输入 / IF02/03/05/07 | 五阶段真实builder入口、tenant_uid/后台字段的路径规则和保留对照；最终wire、原件/来源映射及当前配置引用 | N02/L1已实现并独立15/15通过，后台原件/关联保持；N01实际21新版本就绪及N02/L2待发布/验证 |
| 调查输出 / IF03/05/07 | 各阶段闭合有效单元及必要依赖、质量与结构错误分类、stage_delivery版本/字段/保存位置；C3初答/唯一补答失效后的保留规则、Deep合法动作门槛、无有效内容及unknown收尾 | N03–07；最终字段见调查设计§3，具体实现和保存/读取样本待交接，不新建A/I/C6续写 |
| 调查持续链 / IF05/08 | I当前输入收尾回执保存后推动Case的材料比较规则；partial/unavailable与未完成/stale/同内容的差异；唯一活跃接收、单告警边界及每轮前序可用/采用/比较资格 | N10/11；待实施的新行为，旧可用I触发证据不能核销 |
| HTTP / IF04/07/13 | stage_delivery沿现有步骤/工件读取的实际样本、DTO/序列化、content_url、错误/缺失合同；同Run保存快照与TCP回执。无需为内部阶段新开路由 | N08/10/11；既有正常读取已验，本轮新样本待提供 |
| 测试服务 / IF13 | 4177节点回执、保留/缺失/原答/错误展示及单节点读取失败兜底；字段映射、受控组件及真实浏览器回执 | N09；设计完成，代码和联验待上游合同 |
| 发布/运行 / IF00 | 待测交付hash、所选profile与实际加载核对、当前PG/Kafka/Redis归属及在途状态；对应21版本发布回执 | N01及真实链；本轮仅核已存配置/回执，未重新检查21，不以设计触发清理/重启/模型 |

上述“待”仅阻断依赖的验证层，不阻断已明确的测试设计。已有HTTP合同能直接表达时复用原入口；新增内部工件不等于新增告警前后端字段。任何字段/URL尚未定稿都标待交接，不在测试期望中硬造接口。
