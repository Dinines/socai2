# D6 整个 change 的范围与结束审计

本轮按负责人要求核对 `schedule-streaming-investigation-updates` 的完整范围、文档和独立结束审计；仅在真实满足条件后归档。沿已有 change 工作，不新建平行实施任务树，不借勾选或删除需求把后置事项记为完成。

## 实施前安排

1. **范围核对。** 逐条将原任务、规格要求与阶段职责对齐，区分既有交付、已明确后置和仍在本期范围的缺口；核对混合任务中的已实现/后置部分，记录后置依据及归属。先完成这一步并确认其结构一致性，再推进结束审计。
2. **文档对齐。** 在 proposal、design、tasks 与规格中统一当前边界和归档条件，保留历史原件及失败；当前进度、交接和操作入口引用同一份范围表。实现、业务验收、发布、Git 同步和归档分别表示。规格同步只允许真正完成的行为，不能将尚未交付的 SHALL 写入主规格。
3. **独立结束审计与条件归档。** 由未参与实现者核需求覆盖、接口/持久化结构、后置项归属与发布范围；业务证据部分遵守下面的数据边界。审计发现阻断只修本步必要内容并复核。全部归档条件满足后才执行正常 OpenSpec archive 和归档后校验；不使用 `--skip-specs` 或 `--no-validate` 绕过本业务 change 的未完成条件。

本轮不因文档维护启动服务、运行模型、创建调查任务、部署后端、重放数据或执行 Git 提交/推送。若核对发现这些行为仍是原交付的必要条件，保持其未完成状态和具体归属，不能以本次工作台发布代替。

## 数据边界

按新版 [AGENTS.md](../../../AGENTS.md#codex-和-gpt-服务的数据边界)，Codex/GPT 默认仅接收接口/消息 Schema、合同字段、层级、类型及约束。本轮可核对代码和规格结构；不将业务原件、样本、模型原答、HTTP/数据库返回、截图或数据提取摘要送入会话或其他 GPT 审计者。

负责人本轮进一步明确“不用管真实的数据”。因此本轮只核结构、需求归属与文档，不要求重新提供脱敏回执，也不读取既有业务封包或开展新真实数据验证。既有分步通过、失败、unknown及质量后置结论均按原记录保留；本轮不重新评价这些业务结论。结构审计和CLI校验不能据此宣称整个change新增通过或替代尚未完成的交付。

本轮独立审计使用不继承业务数据的新上下文，遵循同一边界。可以登记证据文件的引用位置；未经确认，不读取其数据正文或把工具计算的业务摘要转交审计者。

## 通过条件

| 条件 | 必须具备的判据 |
| --- | --- |
| 范围一致 | 原任务和全部规格要求都有明确归属；后置依据及未交付行为保留，不以大项勾选掩盖子项 |
| 实现和合同一致 | 本期字段、枚举、关联、生命周期和 HTTP 合同由实际实现承接；告警交接字段冻结约定保持 |
| 直接业务验收 | 必要的输入、处理、保存和读取有对应有效证据；正常、失败、unknown 及模型质量边界分别记录 |
| 统一交付范围 | 原交付任务要求的后端、HTTP、工作台和配置发布范围分别核清；独立工作台发布不能代替后端交付 |
| 独立结束审计 | 覆盖本次 change 的已定范围；审计者指出的阻断已关闭，或在有明确依据的后置范围中保留 |
| 规格与归档 | 只同步已交付要求；正常归档及归档后的 active/archived strict 检查通过，迁移后的引用仍可追溯 |

上述是判据而非完成声明；本轮结构范围和未完成条件如下。

## 本期、后置与未完成对照

| 原任务 | 本期范围/保留状态 | 后置部分 | 本次处理 |
| --- | --- | --- | --- |
| 1.1、2.1 | 规划与共同任务/执行生命周期；原已勾选保持 | 无 | 保留原完成状态，不重写历史验收 |
| 2.2、2.3 | 自动首轮、周期/生命周期、Case关联与容量、统一执行及范围冻结；已有分步实施记录，总项未勾选 | 无新增后置 | 不把D6展示验收代替所有业务子项的综合核销 |
| 2.4 | 有效H更新、上一实际完整调查比较、人工采用保护；总项未勾选 | 人工定向分析、手动全案综合（第8–9步） | 本期正文只承接普通H/比较，原混合任务全文及后置验收出口保留 |
| 2.5 | 当前C2/C3/Deep/C6知识与输入筛选、查询窗口、日志/输入容量；总项未勾选 | 手动综合的知识复用依第9步恢复 | 不移除本期知识筛选；移出未交付的综合能力声明 |
| 2.6 | 无本期新增异步维护交付 | 知识后台异步维护（第10步），完整任务未实施 | 原号及未勾选保留；移出当前历史知识delta，不改现行提交后同步主规格 |
| 2.7 | 普通异步提交、任务/Run/结果/完整目录、Swagger、配置及4177；总项未勾选 | 定向/综合HTTP（第8–9步） | 本期读取、比较合同保持，原后置HTTP要求留存 |
| 3.1 | 代表性完整闭环与各依赖真实/受控边界；原总项未勾选 | 已决定的模型正文质量问题继续单独后置 | 复用原记录，不重采样、不将结构核对写成新增业务通过 |
| 3.2 | 文档/交接与完整change独立结束审计；原总项未勾选 | 无新增后置 | 本轮完成范围、文档及独立结构/关键接线审计；限定审计不整体核销原任务 |
| 4.1 | 最新本期后端/HTTP/配置的统一交付、实际读回、Git/父项目同步及条件归档 | 无新增后置 | 独立工作台发布不能代替最新D5写侧交付；保持未完成，不以整理文档补勾 |

后置三项的完整原文、依赖、阶段归属和恢复出口见[后置范围](deferred-scope.md)。它们不再进入本期规格同步，但保留未实施状态。其余当前范围未闭合的综合任务不以“后置”核销。任务勾选是原总项状态，不表示各分步都没有实施；具体子步沿下述原记录追溯。

## 需求与代码、直接验证入口

下表是**结构映射**：模块/测试入口存在可用于定位，不代表本轮执行了这些测试，也不代表所有场景已通过。完整规格条目到本表的映射在下一节逐条列出，后置原条款单独保留。

| 组 | 本期职责/原任务 | 实现与合同入口 | 直接验证入口 | 原设计/记录入口 |
| --- | --- | --- | --- | --- |
| A | 持久任务、唯一调度、轮询、有限重试、unknown收尾；2.1/2.3 | [任务存储](../../../services/api/app/socai2/analysis_task_store.py)、[调度器](../../../services/api/app/socai2/analysis_dispatcher.py)、[调度生命周期](../../../services/api/app/socai2/analysis_dispatch_store.py)、[执行合同校验](../../../services/api/app/socai2/analysis_dispatch_runtime.py) | [调度组件](../../../services/api/tests/test_socai2_analysis_dispatch.py)、[PG调度](../../../services/api/tests/test_socai2_analysis_dispatch_pg.py)、[任务PG](../../../services/api/tests/test_socai2_analysis_tasks_pg.py) | [存储设计](storage-and-runtime-design-20261114.md)、[队列设计](queue-dispatch-design-20261114.md)、[原验证记录](validation.md) |
| B | A/I/Case首轮与对象先保存；2.2/2.3 | [A执行器](../../../services/api/app/socai2/analysis_alert_executor.py)、[I执行器](../../../services/api/app/socai2/analysis_incident_executor.py)、[Case执行器](../../../services/api/app/socai2/analysis_case_executor.py) | [A入站](../../../services/api/tests/test_socai2_alert_ingress.py)、[I后轮](../../../services/api/tests/test_socai2_incident_streaming.py)、[Case首轮PG/HTTP](../../../services/api/tests/test_socai2_case_initial_http_pg.py) | [A设计](stage3-alert-ingress-design-20261115.md)、[I设计](stage4-incident-diagnosis-design-20261115.md)、[Case首轮](stage6-case-execution-design-20261115.md) |
| C | I选入范围、Case接收/跟随/容量、冻结范围、下游变化；2.2/2.3/2.5 | [Case分配](../../../services/api/app/socai2/case_allocation.py)、[I范围](../../../services/api/app/socai2/case_incident_scope.py)、[变化输入](../../../services/api/app/socai2/case_update_inputs.py)、[扫描器](../../../services/api/app/socai2/case_update_scanner.py)、[输入容量](../../../services/api/app/socai2/baseline_capacity.py) | [分配PG/HTTP](../../../services/api/tests/test_socai2_case_allocation_http_pg.py)、[I边界PG](../../../services/api/tests/test_socai2_incident_boundary_pg.py)、[更新PG/HTTP](../../../services/api/tests/test_socai2_case_update_http_pg.py)、[容量保留](../../../services/api/tests/test_socai2_case_preflight_retention.py) | [分配设计](stage5-case-allocation-design-20261115.md)、[后轮设计](stage7-case-updates-design-20261115.md) |
| D | 有效H、上一轮比较、采用保护；2.4本期部分 | [执行输入](../../../services/api/app/socai2/case_execution_input.py)、[比较](../../../services/api/app/socai2/case_comparison.py)、[上一轮材料](../../../services/api/app/socai2/case_previous_analysis.py)、[采用](../../../services/api/app/socai2/case_adoption.py) | [比较HTTP](../../../services/api/tests/test_socai2_case_comparison_http.py)、[上一轮材料](../../../services/api/tests/test_socai2_previous_analysis.py)、[采用PG](../../../services/api/tests/test_socai2_case_adoption_pg.py) | [后轮比较设计](stage7-case-updates-design-20261115.md)、[D5b设计及原记录](stage11-output-continuation-design-20261116.md) |
| E | 本期知识筛选、模型输入、查询窗口与条数；2.5 | [知识视图](../../../services/api/app/socai2/knowledge_model_input.py)、[业务视图](../../../services/api/app/socai2/model_input_view.py)、[查询快照](../../../services/api/app/socai2/case_query_snapshot.py)、[工具约束](../../../services/api/app/socai2/baseline_evidence_tools.py) | [知识筛选](../../../services/api/tests/test_case_purpose_knowledge.py)、[输入冻结](../../../services/api/tests/test_socai2_case_execution_input.py)、[精简视图](../../../services/api/tests/test_socai2_compact_model_input.py) | [Case首轮设计](stage6-case-execution-design-20261115.md)、[知识规格](specs/case-purpose-knowledge/spec.md) |
| F | 普通异步提交、三层身份、完整目录和读取；2.7本期部分 | [提交合同](../../../services/api/investigation_http/analysis_submission_contracts.py)、[任务合同](../../../services/api/investigation_http/analysis_task_contracts.py)、[目录合同](../../../services/api/investigation_http/run_directory_contracts.py)、[核心目录用例](../../../services/api/app/socai2/run_directory.py) | [提交PG](../../../services/api/tests/test_socai2_analysis_submission_pg.py)、[任务PG/HTTP](../../../services/api/tests/test_socai2_analysis_task_http_pg.py)、[目录PG](../../../services/api/tests/test_socai2_run_directory_pg.py) | [HTTP合同](http-workflow-contract-20261114.md)、[模块供给清单](test-interface-readiness-20261115.md) |
| G | 阶段回执、局部截断、可用内容/采用/比较、异常后继续；D1–D6 | [阶段回执](../../../services/api/app/socai2/stage_delivery.py)、[C3接收](../../../services/api/app/socai2/case_c3_delivery.py)、[Deep接收](../../../services/api/app/socai2/case_deep_delivery.py)、[C6接收](../../../services/api/app/socai2/case_c6_delivery.py)、[执行器](../../../services/api/app/socai2/baseline_executor.py) | [C6单元](../../../services/api/tests/test_socai2_c6_units.py)、[局部依赖](../../../services/api/tests/test_socai2_local_dependency.py)、[传输中断](../../../services/api/tests/test_socai2_transport_continuation.py)、[收尾时钟](../../../services/api/tests/test_socai2_completion_clock.py)、[交付保存](../../../services/api/tests/test_socai2_baseline_delivery.py) | [D1–D6设计及分步记录](stage11-output-continuation-design-20261116.md) |
| H | 测试账本、材料合同、准备边界、分段执行、Docker及报告；3.1/3.2配套 | [账本](../../../services/investigation_test/store.py)、[材料合同](../../../tools/testdata/acceptance_contract.py)、[执行会话](../../../tools/testdata/acceptance_session.py)、[交互入口](../../../tools/testdata/acceptance_console.py)、[报告](../../../tools/testdata/acceptance_report.py)、[独立打包](../../../deploy/investigation-test/build.py) | [账本测试](../../../services/investigation_test/tests/test_ledger.py)、[材料测试](../../../tools/testdata/tests/test_acceptance_materials.py)、[执行测试](../../../tools/testdata/tests/test_acceptance_execution.py)、[保存读回](../../../tools/testdata/tests/test_acceptance_saved_readback.py)、[打包测试](../../../deploy/investigation-test/test_build.py) | [完整测试规划](full-flow-test-plan-20261115.md)、[配套设计](test-service-and-4177-http-20261115.md) |
| V | 4177主体/轮次/原件、错误和空态、来源及精确跳转；2.7/D6 | [查阅入口](../../../services/investigation_test/viewer.py)、[页面](../../../services/investigation_test/web/viewer.js)、[状态](../../../services/investigation_test/web/viewer_state.mjs)、[交付展示](../../../services/investigation_test/web/delivery_view.mjs)、[报告链接](../../../tools/testdata/acceptance_report_links.py) | [页面接口](../../../services/investigation_test/tests/test_viewer.py)、[交付视图](../../../services/investigation_test/tests/test_delivery_view.mjs)、[流程视图](../../../services/investigation_test/tests/test_execution_flow.mjs)、[精确跳转](../../../tools/testdata/tests/test_acceptance_report_links.py) | [4177设计](test-service-and-4177-http-20261115.md)、[D6原发布入口](../../../docs/operations/evidence/workbench-d6-release-20261118-01/README.md) |
| I | 运行配置、会话保存、生成约束兼容；2.3/2.5/2.7交付依赖 | [运行政策](../../../services/api/app/socai2/runtime_policy.py)、[生成合同](../../../services/api/app/socai2/model_protocol.py)、[数据库接线目录](../../../services/api/app/db/)、[21部署入口](../../../deploy/aisoc21/README.md) | [生成兼容](../../../services/api/tests/test_socai2_vllm_text_compatibility.py)、[数据库URL](../../../services/api/tests/test_db_url_normalize.py) | [候选/配置设计](stage11-candidate-design-20261115.md)、[密码连接判据](pg-password-validation-20261115.md) |

## 当前delta逐条归属

这里只列规格标题和上表归属；标题不是通过声明。`historical-alert-knowledge`的两条异步修改、`case-human-http-flow`的定向/综合两条及混合子条款已移到后置记录。当前主规格不在本轮修改。

| 规格 | Requirement | 组 |
| --- | --- | --- |
| `case-human-http-flow` | Human feedback remains an explicit versioned input to the next investigation | D |
| `case-human-http-flow` | New analyses preserve human scope and later adoption decisions | D |
| `case-human-http-flow` | Case comparison identity is frozen and readable | D |
| `case-purpose-knowledge` | Model knowledge inputs are deduplicated and selected for the current task | E |
| `case-purpose-knowledge` | Stage templates distinguish knowledge from current evidence | E |
| `investigation-test-service` | Test ledger publication and read API are independent of investigation execution | H |
| `investigation-test-service` | Reusable investigation scenarios include complete context and future dependencies | H |
| `investigation-test-service` | Preparation checks and cleanup preserve unrelated data | H |
| `investigation-test-service` | Real model execution and model quality are assessed separately | H |
| `investigation-test-service` | The independent test service owns test records and viewer delivery | H |
| `investigation-test-service` | The viewer obtains current investigation data through HTTP | V |
| `investigation-test-service` | Live reads and archived evidence have explicit provenance | V |
| `investigation-test-service` | Business subjects are discovered without test ledger prerequisites | V |
| `investigation-test-service` | A selected round presents its frozen upstream analysis | V |
| `investigation-test-service` | Test execution uses explicit small data parts | H |
| `investigation-test-service` | Acceptance materials have one documented format and explicit conversion | H |
| `investigation-test-service` | The acceptance script runs from a versioned Docker image | H |
| `investigation-test-service` | Test observations and evidence are assembled by the execution program | H |
| `investigation-test-service` | Test source identity is configured and classified per frozen round | V |
| `investigation-test-service` | Acceptance reports open exact saved subject runs | V |
| `investigation-update-scheduling` | The validation service ships as an independent read-only package | H |
| `investigation-update-scheduling` | PostgreSQL deployment uses password credentials without client certificate setup | I |
| `investigation-update-scheduling` | Initial analyses are submitted automatically without a second start action | B |
| `investigation-update-scheduling` | An incident routes ongoing updates to one active Case | C |
| `investigation-update-scheduling` | Incident diagnosis selects recent memberships with explicit coverage | C |
| `investigation-update-scheduling` | Case consumes the frozen scope of an incident diagnosis | C |
| `investigation-update-scheduling` | Capacity failures preserve completed work without retry loops | C |
| `investigation-update-scheduling` | Case membership capacity routes overflow into linked successor Cases | C |
| `investigation-update-scheduling` | Material checks compare meaningful saved inputs on configurable schedules | C |
| `investigation-update-scheduling` | Automatic checks respect rolling windows and business lifecycle | C |
| `investigation-update-scheduling` | Whole incident associations follow explicit Case boundaries | C |
| `investigation-update-scheduling` | One dispatcher enforces capacity without head of line blocking | A |
| `investigation-update-scheduling` | Queue polling uses a configurable one minute default | A |
| `investigation-update-scheduling` | Independent requests are checked before execution | A |
| `investigation-update-scheduling` | Business records are readable before asynchronous analysis completes | B |
| `investigation-update-scheduling` | Executors capture current inputs before analysis and never expand completed coverage | C |
| `investigation-update-scheduling` | Conclusion comparison uses the previous actual investigation | D |
| `investigation-update-scheduling` | Transient failures receive bounded delayed retries | A |
| `investigation-update-scheduling` | Locally ended unknown outcomes never block the queue | A |
| `investigation-update-scheduling` | Task and attempt history is persistent and private scheduling stays internal | A |
| `investigation-update-scheduling` | Active executors use one complete target contract | A |
| `investigation-update-scheduling` | The target HTTP version submits analyses asynchronously | F |
| `investigation-update-scheduling` | Cross subject run discovery and statistics are complete within the requested scope | F |
| `investigation-update-scheduling` | Step and artifact directories remain fully discoverable beyond page limits | F |
| `investigation-update-scheduling` | Automatic investigations provide traceable windows for time bounded queries | E |
| `investigation-update-scheduling` | Log evidence queries use configurable bounded result sizes | E |
| `investigation-update-scheduling` | Test executions use the real execution flow presentation | V |
| `investigation-update-scheduling` | 普通入站账号的会话写入上下文 | I |
| `investigation-update-scheduling` | 模型生成约束的显式兼容与原合同校验 | I |
| `investigation-update-scheduling` | Model views exclude transport metadata while retaining business facts | E |
| `investigation-update-scheduling` | Quality diagnostics preserve conclusions and do not reject the whole answer | G |
| `investigation-update-scheduling` | Every stage saves a complete receipt without inventing model content | G |
| `investigation-update-scheduling` | Truncated replies retain closed independent units and continue downstream | G |
| `investigation-update-scheduling` | Previous partial analysis and comparable conclusions remain distinct | G |
| `investigation-update-scheduling` | Local call failures do not cancel independent downstream work | G |
| `investigation-update-scheduling` | Continuation acceptance includes reproducible truncation and transport mocks | G |

## 既有证据与本轮验证边界

这里只保留原记录入口，不读取业务内容、不摘取原答或数据摘要，也不将本轮结构检查反写进旧封包。第1–7步沿[validation](validation.md)及各阶段设计中的原记录；D5a沿[Deep保存与C6使用](../../../docs/operations/evidence/deep-unit-continuation-d5a-20261118-01/README.md)，D5b沿[C6接收保存](../../../docs/operations/evidence/c6-unit-continuation-d5b-20261118-01/README.md)和[采用及比较](../../../docs/operations/evidence/c6-adoption-comparison-d5b-20261118-01/README.md)，D5c沿[局部依赖](../../../docs/operations/evidence/local-dependency-d5c-20261118-01/README.md)和[中断/收尾](../../../docs/operations/evidence/transport-continuation-d5c-20261118-01/README.md)，D6沿[候选读取](../../../docs/operations/evidence/http-viewer-d6-20261118-01/README.md)和[正式工作台发布](../../../docs/operations/evidence/workbench-d6-release-20261118-01/README.md)。

本轮必要检查包含OpenSpec strict、需求标题逐条归属、后置原文保留、文档相对链接和独立结构复核；独审另对D5/D6接收→继续→保存→读取及本地收尾→释放→调度做有界静态接线核对。没有运行业务测试、数据库/HTTP读取、浏览器验收、模型或服务发布。对历史分步结论的引用不等于本轮重新作出业务证明；模型正文质量后置及原NOT_PASSED继续保留。

## 本轮结构检查

| 检查 | 本轮结果 | 适用边界 |
| --- | --- | --- |
| `openspec validate schedule-streaming-investigation-updates --strict --no-interactive` | 通过 | 只证明change格式与delta合法 |
| 当前Requirement逐条映射 | 56条各对应一次，无遗漏或重复 | 是需求结构覆盖，不是业务场景通过计数 |
| OpenSpec实际delta解析 | `openspec show schedule-streaming-investigation-updates --json --deltas-only`解析出56条，正文规范空白后与当前规格逐一一致 | 修正重复ADDED分节导致比较读取要求被漏读的问题；仅strict通过不足以证明可同步清单完整 |
| 后置原文与任务标识 | 4条完整Requirement、原混合任务和相关子条款保留；11个原任务编号/勾选保持 | 后置功能仍未实施，本期总项不因此核销 |
| 当前delta与主规格 | ADDED/MODIFIED标题对应正确；主规格未改动 | 未执行同步或归档 |
| 文档链接与格式 | 本change及相关当前入口的本地目标存在，允许文件链接的行号后缀；`git diff --check`通过 | 未读取链接指向的业务原件内容 |

以上检查仅针对本轮文档结构，不新增业务测试或运行数据结论。独立审计发现移出的H/定向职责区分句未完整留存，已补入后置原文并由审计者复核关闭。最终实际解析检查另发现`case-human-http-flow`重复ADDED分节造成比较读取要求被遗漏，已合并分节并核对全部正文，没有删改该要求或场景。独立审计范围、逐项结果和仍未满足的归档条件见[audit.md](audit.md)。

## 归档判断与后续责任

本轮独立结构审计及关键接线补查已完成，无未关闭的本轮结构问题；整个change仍不归档。人工定向分析、手动全案综合、知识后台异步维护已经有明确后置归属，不是当前阻断；本期总任务的核销及4.1完整交付仍未完成，不能以限定结构审计或已发布的4177代替最新写侧交付、实际读回与Git/父项目同步。3.2的本轮文档和结构审计进展单独记录，不据此勾选整个综合任务。

后续仍沿原tasks处理：先按已存分步记录核清本期2.2–2.5/2.7/3.1总项覆盖；缺口只补直接必要验证，并遵守当时数据边界。完整结束审计结论与必要交付具备后再核销3.2/4.1，不能追加采样后置质量问题来替代功能核对。当前轮不要求用户提供真实数据，也不因文档收口另启模型或发布。

满足条件后执行正常OpenSpec归档并同步当前delta，不能使用 `--skip-specs` / `--no-validate`。归档会使相对目录多一层，需按原目标重算change内部指向仓库的链接，并同步PROGRESS、交接、导航和问题清单的活动入口；旧封包及原件保持原路径、原内容。之后对主规格、剩余active changes和归档目录做strict及链接检查。本轮没有执行archive，没有主规格同步或归档回执。
