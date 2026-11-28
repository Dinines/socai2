# 从产品功能到接口与数据的提供要求

正式 C173 的逐功能 HTTP 映射见第 7 节。第 1–6 节和第 8 节保留需求设计及分阶段核对。当前接口与外部依赖见统一交接。[C173 后端联调交接清单](c173-backend-handoff-20261121.md)

初版2026-11-14，现行合同核对更新于2026-11-20。**正式产品将采用4173告警、事件和调查功能/设计；每个非暂缓功能都须有HTTP及真实数据库支撑。先确定用户要完成什么，再核对接口和存取，不能按已有代码缩减产品范围。** AI聊天、人工定向分析、真实响应审批执行沿负责人最新答复继续暂缓，混合功能中的普通读写仍纳入。

依据为[125项逐页功能](../../deliverables/investigation-validation-20261106/frontend-feature-list.md)（告警22、事件15、调查88）及[已确认产品规则](../design/investigation-product-decisions.md)。第5节保留后续已确认增量，不混入125项计数。第7节已逐项映射现行method/path，配套[结构清单](product-api-data-requirements-20261114.coverage.json)含请求参数、请求/响应Schema、HTTP处理函数、用例端口、核心文件及内部来源表；仅含结构，不含业务数据。

**11-20 的供给核对覆盖全部 125 项的功能归属。** 10 项整行暂缓，其余 115 项保留当时普通功能，映射到 76 个操作。当时的正式环境为 80 个操作，完整候选为 82 个操作，新增两项为日志湖只读查询，两者各有 2 个 AI 预留 501。Case 和事件的风险与人工优先级字段在相同路径上存在版本差异。132 增量当时已通过候选隔离 PostgreSQL 验证，新批接收、任务、Run 和模型调用均为 0。[11-20 回执](../operations/evidence/http-real-data-20261120-01/README.md)

## 1. 谁负责什么

| 责任方 | 要交付什么 |
| --- | --- |
| 产品/接口侧（本清单） | 功能目的、操作结果、必需数据、输入输出、跳转身份、空态和直接验收；明确提出缺口，不让前端接受不完整拼接 |
| 调查模块 | 按清单保存和提供事实、分析进度、结论、依据、历史、人工反馈和关联；设计其内部存储及查询用例，并说明数据是否完整、哪些尚未提供 |
| 独立HTTP服务 | 将已定稿的用例转换为对外HTTP及Swagger，稳定表达参数、返回字段、错误和实现状态；不把内部调度、阶段或数据库操作暴露给调用方 |
| 业务后端 | 资产库存/标签、人员目录、文件上传下载、真实响应审批和执行；通过确定的接口提供所需资料/回执，不要求复制旧AiSOC的表 |
| 产品前端 | 展示、选中、跳转、画布和已取得内容的下载；不得靠枚举所有主体来补服务缺少的完整调查目录，也不得自己推测业务状态 |

后文数据库名均为`socai2`命名空间中的表；它们说明**服务内部取数来源**，不是要求前端或业务后端直接查库。新增存储由提供方设计，本文不指定DDL或队列实现。保留原数据不等于建设旧接口兼容层；核心、HTTP、存储和Swagger按同一个目标版本推进。

### 实现状态的口径

- **已有供给**：现有文档/代码已有对应能力；功能核对不代替原发布验收，也不表示页面已接入。
- **待提供**：产品要求清楚，缺少实现、完整读取或接线。缺表、缺接口不是取消需求或业务规则未定的理由。
- **合同待定**：确实缺少业务规则或输入约定；保留需求及未定内容，该接口暂不实施，其他定稿能力继续。
- **外部提供**：属于业务后端；调查侧仍须明确需要哪些资料和如何关联。
- **明确暂停/非本期**：只有负责人已决定暂停或没有纳入确认范围的能力，才能如此标记。

## 2. 告警页面：需要提供什么

下表A1–A8是需求分组，不是接口编号；逐项F编号及现行路径见第7节。旧E编号仅用于追溯71操作历史包；E11/E13/E36已退役，E01/E08/E37的当前请求/回执也不能套用旧样例。

| 需求及用户得到的结果 | 输入 → 必须返回的数据/操作结果 | 内部来源与提供方 | 供给要求与缺口 |
| --- | --- | --- | --- |
| **A1 列表、详情和导出**：找到告警，预览后进入同一条详情 | 搜索/等级/处理状态/负责人/发生时间/排序/游标，或alert_id → ID、名称、等级、真实告警时间及来源、类别、检测源、状态、负责人ID/名称/解析情况、涉及资产及库存标签；筛选命中数、整体指标、下一页；完整筛选结果CSV | `alerts`；检测/对象取`alert_materials`、`alert_objects`；负责人和库存由业务后端提供；调查服务提供完整查询 | 已有E26/E28/E30/E54。缺时间不能拿入库时间顶替；资产标签不能拿告警标签顶替；统计范围明确。选列/预览是前端交互，不新增偏好平台 |
| **A2 检测依据、原始记录和历史来源**：知道收到什么、从哪里来 | alert_id/material_id或历史run_id → 原始JSON/文本、标准化和富化内容、检测规则/ATT&CK标签、材料版本、来源命名空间/ID/路径、可用性；能打开当轮冻结版本 | `alert_materials`、`alert_source_refs`、`alert_objects`；历史取`run_members`、`artifacts`；调查模块 | 已有E28/E30/E31及原件读取。历史输入不得换成当前材料；缺原件与有效空内容分开。同ID新材料/重新分诊提案已撤回，见第5节P4 |
| **A3 当前分诊、解释与过程**：理解判断，并追到依据和失败尝试 | alert_id → 当前有效分诊的判定/置信度及量纲/理由/形成时间/来源Run、解释和引用；run_id → 该次执行、步骤及原件；分析任务ID → 自动分析进度 | `alert_assessments`、`alerts`当前指针、`runs`、`run_steps`、`artifacts`；新分析任务记录由调查模块提供 | 自动入站分诊、三类分析任务GET、A目录/Run/步骤读取已在正式80操作中；当前有效结果与最新失败尝试分别返回，不提供手动analyze。共用任务时间投影已在S5候选验证，正式未升级；本批不重派旧A。 |
| **A4 人工判定和单条/批量管理**：记录人工意见、分配及处理状态 | 明确alert_ids、版本、operation_key、判定/理由或管理字段 → 实际保存身份/版本/状态及活动；冲突返回明确错误 | 人工判定在`alert_assessments`，管理在`alerts`，活动在`activities`/`activity_targets`；调查模块 | E48–E51已有。按D02关闭/恢复；保留模型判断。有效反馈供后续事件/Case检查，不自动替用户关闭事件/Case |
| **A5 同主机和相似历史参考**：核对相近告警，点开真实来源 | alert_id及已约定的查询范围/游标 → 候选ID、名称、等级、时间、匹配对象/战术及原件来源、所属范围 | `alerts`、`alert_objects`、`alert_materials`、关联表；调查模块 | E70相似历史、E71同主机最近7条已有，两者规则分开。文件以明确算法哈希匹配，不能仅凭文件名认定同一文件；不自动复制判定 |
| **A6 所属事件/Case及纳入调查**：从单条告警进入集合调查 | alert_id → 实际incident_ids/case_ids；选择已有Case或新建信息/成员/版本 → 实际关联、新案及首轮任务（新建时） | `incident_alerts`、`case_alerts`、`case_incidents`、`cases`；新首轮任务由调查模块保存 | 现行建案POST返回201/allocations，各新Case含initial_task；关联返回实际分配，不能再用pending_run_id或假定只产生一个Case。正式已挂任务/首轮链，页面本批已修调用；已有案关联不等于已分析，助手暂缓。 |
| **A7 发生与处理时间线**：分清先发生什么、后处理什么 | alert_id → 发生/检测时间、分诊开始结束、人工处理活动，每项带类型、实际时间和可回查身份 | `alerts`、`runs`、`activities`/`activity_targets`；调查模块 | E28/E30/E22已有数据可组合，但缺时单列；排序不能伪造时间；点条目打开该来源 |
| **A8 响应建议及已有处理记录**：区分建议和真的执行过 | alert_id及实际来源Run → 建议动作、目标、理由、限制；已有外部动作ID/状态/回执及来源 | `alert_assessments`、`artifacts`、`response_links`；建议与关联由调查模块提供，真实动作由业务后端提供 | A的result.recommendations及explanation.content.recommendations可沿现行HTTP读取，已有responses关系可读；只显示真实已存内容。审批/新执行按11-20决定暂缓，不能把建议或链接当回执。 |

## 3. 事件页面：需要提供什么

| 需求及用户得到的结果 | 输入 → 必须返回的数据/操作结果 | 内部来源与提供方 | 供给要求与缺口 |
| --- | --- | --- | --- |
| **E1 列表、预览、指标及导出**：定位需要处理的一组告警 | 搜索/状态/等级/负责人/时间/排序/游标，或incident_id → ID/标题/状态/有效等级及来源、成员数、对象/资产数、负责人；筛选总数/下一页、整体指标、归并统计及口径；CSV | `incidents`、`incident_alerts`、`alerts`、`alert_objects`；人员/库存由业务后端提供 | E27/E29/E55/E57已有。近24小时新增按事件数；归并统计同一范围，不能把当前页当全量；列选择不写业务数据 |
| **E2 单条/批量管理**：明确责任、人工等级及解决理由 | 明确事件集合、版本、operation_key、负责人/状态/标签/等级覆盖及理由 → 保存后的字段/版本/活动 | `incidents`、`activities`、`activity_targets`；调查模块 | 单条/批量管理已有实际存取；132候选另提供priority_value/priority_reason/clear_priority_override，正式旧库/Schema未含该增量。覆盖理由与风险来源按S3合同，不改成员告警等级。 |
| **E3 概览、当前诊断与再诊断**：理解整个事件，不把某条告警当事件结论 | incident_id → 事实/真实活动范围/缺失时间数、当前诊断结论/发现/未解决问题/来源Run/新鲜度；check或rerun → 分析任务回执及后续状态/结果 | `incidents`、`incident_diagnoses`、`incident_alerts`、成员`alerts`、`runs`、`run_steps`、`artifacts`及新任务/尝试记录；调查模块 | 正式已挂异步diagnose及任务列表/详情、事件范围/实际覆盖。没有诊断仍读事实，失败尝试不覆盖有效判断；SF04独立结构化业务判定仍缺，共用任务时间S5候选已验（正式未升级），不以正文或supported/uncertain顶替。 |
| **E4 时间线、关系图、成员和资产**：解释为何关联，并逐条复核 | incident_id及分页 → 成员告警ID/名称/等级/时间、关联来源和依据、共同对象及其原件、节点/边及来源、库存匹配/标签 | `incident_alerts`、`alerts`、`alert_materials`、`alert_objects`，诊断图可取`artifacts`；库存由业务后端提供 | E30等已有；图限定当前事件，关系不等于攻击因果；点成员→告警，点对象/边→真实来源；完整成员可遍历，缺失/截断必须可见 |
| **E5 处理活动**：知道谁何时改过什么 | incident_id及分页 → 操作者/时间/动作/前后值/理由/目标及结果 | `activities`、`activity_targets`；调查模块 | E30已有；活动要关联真实事件和目标，不能只有无对象的文字 |
| **E6 进入、新建或关联Case**：把整组事件纳入持续调查 | incident_id → 显式关联Case及共享告警关系；选择已有案或建案 → 成员/事件关联、范围版本、新案首轮任务 | `case_incidents`、`case_alerts`、`incident_alerts`、`cases`；整事件跟随/显式排除由调查模块设计保存 | 既有关联/新建接口复用；整事件明确加入后，由唯一接收Case跟随后续成员，全部历史关联仍保留。仅选告警不取得事件接收权；实际分配与两级关联见P8/P9 |

## 4. 调查页面及调查记录：需要提供什么

| 需求及用户得到的结果 | 输入 → 必须返回的数据/操作结果 | 内部来源与提供方 | 供给要求与缺口 |
| --- | --- | --- | --- |
| **C1 案件列表、指标和预览**：安排案件处理 | 搜索/状态/等级/负责人/日期/排序/游标 → 案件摘要、筛选总数/下一页、四项指标、CSV；case_id → 预览与详情 | `cases`、成员关系、人工`tasks`及当前判断；调查模块 | E02/E03/E56已有。刷新只重读；全局调查入口须能进入R1完整目录。管理设置仅占位，不据此增加配置平台 |
| **C2 建案、资料及管理**：为明确范围建立工作区，调整责任或结案 | 名称/所选告警或事件及案件信息 → case_id、范围、首轮任务；case_id/版本及管理字段、结案/重开理由和必要确认 → 保存回执、条件与活动 | `cases`、`case_alerts`、`case_incidents`、`activities`/`activity_targets`；新任务记录由调查模块提供 | 基本管理、关闭/重开、容量分配/续建、initial_task及实际执行读取已有接口/存储；关闭以实际仍执行为条件。132人工优先级/风险合同只在候选验证；正式能力、当前源码及新批实际执行分别记录。 |
| **C3 当前采用判断、覆盖和采用历史**：明确当前认可什么及适用边界 | case_id → 当前判断/未解决问题/形成与采用时间/来源/覆盖/新鲜度；候选result_id → 比较预览、未完人工及分析任务；确认版本/理由 → 新判断及历史 | `case_assessments`、`case_assessment_sources`、`case_assessment_members`、`results`、`result_members`、`tasks`、`task_revisions`、`artifacts`，新分析任务记录 | Case详情返回current_assessment及sources；按sources.result_id读取同源Result的findings/questions/recommendations，正式代表GET已与PG核对。采用预览已含未结束分析任务；采用不取消它们。SF06采用Result摘要/范围/未决项及人工版本/工件原文候选接线已验，完整产品接入仍待；技术停止码留执行信息。 |
| **C4 案件故事**：串起事实发生和认识变化 | case_id、搜索/等级/游标 → 告警、调查、已完成人工修订等条目的类型/时间/摘要/身份/范围/来源 | `alerts`、`runs`、`results`、`tasks`/`task_revisions`及成员关系；调查模块 | E65已有非对话范围。点告警/Run/修订回实际记录；无时间单列，不把运行中当已有结论。AI问答暂不要求 |
| **C5 启动、进度与调查概览**：提交后知道是否受理、是否执行及到哪里看结果 | case_id、operation_key、check/rerun → 分析task_id及查询位置；task_id → accepted/running/completed/failed/skipped、原因、实际时间、每次Run和结果链接；case_id → 主体更新摘要及人工待办数 | 目标`analysis_tasks`、`analysis_attempts`、`analysis_subject_state`；已有`runs`、`results`、人工`tasks`；调查模块 | 正式已挂POST investigations及六个主体analysis-tasks GET，202/initial_task不是完成。Case/Incident传operation_key和mode=check/rerun，不用prepare/start；无Run保留真实任务状态。S5候选已补首次/最近入队、attempt入队、active_step及服务端耗时；正式未升级，仍按部署版本选合同。 |
| **C6 历史轮次和结果比较**：查看每轮输入与变化，不改历史 | case_id及游标/run_id/result_id → 原因/范围/执行与交付状态/用量、冻结输入引用、比较对象及变化 | `runs`、`run_members`、`results`、`result_members`、`artifacts`、`task_revisions`；调查模块 | 既有E10/E12/E14等复用；目标比较上一轮实际完整调查，由程序选定，前轮无结论如实为空，不用当前采用结果或更早结论替代 |
| **C7 正式成员及变更**：明确本案调查谁，添加/移动后知道什么未分析 | case_id；所选告警/事件及范围版本、目标案（移动时） → 真实新增/去重/移动结果、范围版本、当前成员、未覆盖成员及待更新提示 | `case_alerts`、`case_incidents`、`incident_alerts`、`cases`；跟随排除记录由调查模块提供 | 现行分配/移动/完整替换用例已落库，返回实际Case及范围版本；唯一事件接收者、显式排除和周期跟随沿已确认规则。读取不触发跟随；正式自动运行、最新写侧与新批验收分开核验，不把HTTP存在当自动消费已启用。 |
| **C8 关系图、候选、保存恢复**：探索线索后明确决定是否加入案件 | case_id/起点对象或告警/查询时间范围 → 图及来源、候选/匹配依据/归属；保存版本/底图/展开及画布 → 可恢复的保存身份 | `artifacts`（图及探索保存）、`alerts`/`alert_objects`/`alert_materials`和成员关系；调查模块 | E66–E69及E08已有。保存不加成员、不生成Run；新结果不替换已保存底图。D05候选查询自选时间范围已确认，与“调查执行自选时间窗”分开 |
| **C9 对象与证据**：按主机等对象或按调查找到材料 | case_id及对象键/类型或run_id → 对象、关联告警、实际证据索引/覆盖/来源与可用性，能回查材料/查询/人工修订 | `alert_objects`、`run_members`、`artifacts`、`results`及人工修订；库存资料由业务后端提供 | 既有E05/E06和原件读取可组合。没有索引为未记录，有效空索引才是0；摘要不冒充完整原件；正文/引用读取见R3/R4 |
| **C10 人工核实任务**：用户主动找人确认，并让有效事实进入下一次调查 | case_id、版本、事项/负责人/期限/来源；完成时结果正文及适用成员/对象/时间 → 任务、修订、完成人/修改人、待办数与历史 | `tasks`、`task_revisions`、`activities`/`activity_targets`；调查模块 | 普通人工任务及修订读写已提供；有效完成/修订/撤回进入后续check的已有证据沿流式change复用，最新写侧交付仍单列。元数据变更不当新事实，409保留输入，不自动把未决项建任务；问答入口暂缓。 |
| **C11 活动、评论与文件关联**：保留协作记录和可下载资料 | case_id及分页；评论正文；业务后端file_id/名称/类型/大小 → 活动、评论、案件文件关联及可供后端查下载的ID | `activities`/`activity_targets`、`comments`、`artifacts`（附件元数据）；文件字节和下载由业务后端保存/提供 | E17/E58–E62已有调查侧能力；外部上传下载需业务后端对接。普通评论不是已核实事实，附件元数据不等于模型读过正文 |
| **C12 AI对话及保存回答**：保留设计范围，但当前不开发 | 全案/告警/对象/结果/人工事实的提问上下文、问题、回答、引用和保存结果 | 现有`conversations`/`messages`及结果引用只是结构来源，不据表存在宣称功能可用 | 负责人明确暂停F26-01–08、F20-04及其他页面的问答部分；E19/E20预留501不算实现，不纳入当前提供方开发清单 |
| **R1 跨主体调查目录及统计**：找到没有Case的告警分诊、事件诊断及各案调查 | 已有页面要求的主体/轮次/状态/时间阅读范围、分页 → **范围内完整**的Run目录（包括无结果的失败/unknown）、总数/下一页、状态/交付/输入数量/时间/摘要/父主体及实际Case关联；同范围统计 | `runs`为完整记录来源，关联`alerts`/`incidents`/`cases`及结果、成员；调查模块提供统一查询用例，HTTP侧出正式合同 | 正式已有GET /analysis-runs及真实task/intent关联、分页和同范围统计；详情使用返回detail_url，不存在通用GET /analysis-runs/{run_id}。尚无Run的受理任务从主体任务GET查询，不计成Run。 |
| **R2 单轮概览、结果与冻结输入**：知道调查了谁、得出什么、还有哪些限制 | 实际subject_id/run_id/result_id → 目标/原范围、结论/发现/未解决问题/变化/影响、执行/交付/引用诊断、输入版本、用量及停止原因 | `runs`、`run_steps`（过程/用量）、`run_members`、`results`/`result_members`、`alert_assessments`、`incident_diagnoses`、`artifacts`；冻结引用再关联`alert_materials`/`alert_source_refs`/`task_revisions`；调查模块 | E12/E14/E24/E25等已有，阶段一读取器须统一版本。新任务失败尝试关联`analysis_attempts`，旧失败Run独立保留；告警/事件/Case结果不能混用ID；保存成功、HTTP成功不表示模型判断正确 |
| **R3 分析过程、步骤及输入输出原件**：按步骤读完实际过程并定位失败 | 主体/run_id，步骤或工件身份及续页 → 有序父子步骤、状态/错误/用量、输入输出/复用引用、冻结能力摘要、原件正文和可用性 | `run_steps`、`artifacts`、`runs`；调查模块提供完整可遍历目录及实际原件读取 | 正式已有完整steps、单step及artifacts三个GET，按next_cursor遍历并沿content_url读取原件。旧Run/trace摘要可能有上限，不代表完整目录被截断；S5实际任务入队/active_step增量未提供。 |
| **R4 查询及证据回查**：知道实际查了什么，并核对每项依据 | run_id、查询步骤/来源引用 → 来源、实际参数、状态、结果/原件及错误；引用能定位当轮材料/人工版本/回执 | `run_steps`、`artifacts`、`alert_materials`/`alert_source_refs`、`task_revisions`、`response_links` | 正式完整步骤/工件目录及kind=tool过滤可用；参数、状态及原件按真实步骤保存/读取。未查、失败、查空、未知分别表达，执行回执供人复核，不全部透传模型。 |
| **R5 历史关系图**：重现当轮图，选择继续探索时进入当前案 | result_id → 当轮节点/边/来源及缺图原因；case_id → 当前探索入口 | `results`、`artifacts`及Case身份；调查模块 | 既有图读取/探索可组合，历史图只读；跳转不重写旧图，无图不借另一轮图替代 |
| **R6 报告、建议与真实响应**：交接结果，区分建议、批准与执行 | run_id/result_id → 已保存报告/收尾说明及建议动作/目标/理由/限制；外部动作身份 → 审批意见、实际状态、回执及来源 | `results`、`artifacts`、`response_links`；调查模块给报告/建议/关联，业务后端给审批/执行及回执 | Result GET已提供findings/questions/recommendations及报告引用，正式代表与PG一致；SF05建议及SF06采用Result依据/未决项候选展示已验，人工版本/工件原文已通过本次候选接线验证，不另调用模型。已有响应关联保留，审批/新执行暂缓；下载已有报告由前端处理。 |

## 5. 新流程的必要数据和真正未定的部分

125项是原页面范围，后续明确决定通过下面增量覆盖旧流程；不另算成“已经实现”的125项，也不悄悄加入额外产品功能。

| 编号/来源 | 产品要求及必须提供的数据 | 当前边界及提供责任 |
| --- | --- | --- |
| **P1 建案和异步调查**（F09-04、F14-01–04、事件诊断） | 建案自动首轮；再次调查/事件诊断提交后立即取得task_id，刷新能继续查看；无Run时仍能读受理/失败原因，重试保留同任务及各次Run | 正式已有建案201/allocations/initial_task、异步I/Case 202和任务GET，原执行/存取证据保留；本批4173已修为该合同，未启动新模型。三条旧prepare/start/analyze入口不存在，不保留同步别名。 |
| **P2 持续更新与采用**（F13-08、F22-08、F16-02、F11-03） | 成员、可用告警分诊、事件诊断及有效人工事实变化可被识别；当前范围是否已调查、上一实际完整调查比较、尚未开始的分析任务可读；采用前可见所有未完工作 | 任务/尝试/主体状态、采用预览及上一实际Run比较已有实现/读回；最新H后轮等写侧仍按流式change交付范围核验，本批不以路由存在宣称自动链全部通过。事件新成员只跟随唯一接收Case，历史关联不广播；定向后续综合暂缓。 |
| **P3 人工定向分析及手动后续综合**（新增业务流程已确认） | 输入本次问题/方向、相关成员/对象及可选现有工具；异步返回任务，读取独立结果的建议、结论、依据和限制。用户明确选择后续全案综合，再受理新的任务，保留前后任务/Run/结果关联 | **流程已确认，11-15按负责人要求后置，尚未实现/开放，不作为本期第1–7步主流程联验前置。** 定向结果可以只有建议，不强求新证据；全案综合复用适用材料，不能无条件完整重跑或自动改变采用判断。正式提交/读取字段及跨Run引用按目标HTTP合同8.2，不新增永久方向字段；普通AI聊天仍暂停 |
| **P4 同ID新材料入口及重新分诊**（RV11原提案） | 保留已有入站原件、来源及历史冻结记录；下游更新按P2看范围和上游分析结果 | **负责人已明确不纳入本期。** 撤回新增版本提交、版本判断及据此重新分诊的提案，不再列为待提供入口；首次自动分诊的有限故障重试仍保持，不能混称重新分诊 |
| **P5 自选调查执行时间窗** | 尚未确定它应如何改变整案调查范围、冻结材料和跨轮比较 | 业务规则未定，暂不新增提交参数。不是D05的候选查询时间范围，也不妨碍列表日期筛选和人工结果已有时间范围 |
| **P6 模型读取附件正文** | 原125项只要求文件上传/下载和案件关联；没有据此要求模型自动读取、分析文件 | 不作为当前页面缺失功能要求开发。若后续明确纳入，再定义正文取得、引用和证据角色；现有文件功能C11继续对接 |
| **P7 自动调查的默认补查范围** | 按本次相关告警真实发生时间前后各扩展1小时，完整调查取本轮成员、定向分析取相关成员；保存实际范围及来源。缺时记录该项补查缺口，其他分析保留，未查不当查空 | 默认补查范围/单次条数沿现行policy与工具实现配置，Case执行器已完成构造接线；本批尚未执行新Run，不能以构造通过宣称真实工具覆盖通过。湖工具剩余缺口仍按5a设计及直接验收推进，缺时/查空/失败保持区别。 |
| **P8 Case容量续建与唯一事件接收目标** | 单Case默认最多100条，确有溢出时新建关联后续Case，自动/手工新增都找到实际接收者；返回请求Case、各Case实际分配、去重/新增成员、新Case及首轮任务。一个事件保留全部Case关联，但只有一个Case接收其后续新告警 | 现行分配、关联、首轮任务/执行及读取已提供，正式存在这些操作；周期跟随及最新更新写侧沿原交付证据核实际运行，不在本批重新派旧任务。容量默认100配置化，不代表100条模型质量已通过。 |
| **P9 关联Cases列表与跳转**（原型曾用“相似 Cases”名称） | 输入当前case_id及分页 → 第一类显示满额续建的同串Case，第二类显示共享事件的其他Case；每项含Case身份/标题/状态、关系类型、共同事件及来源、可跳转身份。排除自身、按Case去重，两类都命中时优先第一类但保留关系依据 | 正式已有GET /cases/{case_id}/related-cases及分页；取cases续建关系、case_incidents和共享成员推导，不是E30告警/事件→Case接口。它属于125项之外已确认增量，结构清单单列，不新增相似度算法。 |
| **P10 事件诊断范围与实际输入超限** | 事件保留全部告警；每轮默认取最近归并的100条，按归并先后而非发生时间选择。返回事件总数、本轮选入成员/数量、实际分析范围及未覆盖限制，并保留历史诊断。事件/Case即使不足100条也要检查实际输入容量 | 事件范围/实际覆盖合同已在正式I读取中；Case按当前阶段独立保存限制与部分交付。新批未执行，实际工具/模型覆盖仍须验；输入超限保留已完部分和原答，不反复采样或把局部当全范围。 |
| **P11 新对象入口与已受理任务跨期** | 上线后新对象按正常流程；不增加旧对象识别、回填、激活或auto_enabled。7天窗口内正式受理的自动首次尝试，排队跨期仍可做该轮，但不自动重试；已失败等重试跨期停止 | **Q5/Q6已确认。** 任务状态和主体自动资格分别返回：资格过期不取消已受理首试；关闭/串行/N/无变化检查保持，不据跨期受理放行新自动扩案或续建。正常完成刷新窗口，排队/失败不续期；本轮不清库 |

### 11-20供给核对后的实际缺口

| 边界 | 当前结论与下一动作 |
| --- | --- |
| 已有HTTP/真实存取 | 任务受理/读取、Run目录、完整步骤/工件、建案分配、采用、普通人工任务/评论、附件引用、探索保存均有当前核心和存储入口。沿原证据复用；本批只读代表及结构核对不替代各功能的完整产品接入 |
| SF04 业务判定 | 已在候选打通 I/C6 输出、134 保存、当前/指定轮次 HTTP 与既有页面展示。`business_verdict` 与确定性、人工分类分别读取。正式环境和最终真实批一起验收。 |
| SF05 建议正文 | [候选展示及限定独审](../operations/evidence/recommendation-display-sf05-20261120-01/README.md)已通过：4173 Case服务模式、Alert/Case记录页及4177建议正文/目标/审批/引用同源，当前采用与指定轮次分开。正式产品接线及4173 Alert服务入口仍须分别处理 |
| SF06 当前判断依据/未决项 | [采用Result的依据/原范围/未决项](../operations/evidence/assessment-basis-sf06-20261120-01/README.md)已通过候选实际读取/页面及限定独审；旧导出空投影与技术结束码混入已修。[人工版本/工件来源链](../operations/evidence/assessment-source-http-sf06-20261120-01/README.md)随后已候选存取/三端页面验证；正式产品接入仍待，不关闭整个SF06 |
| S5/S6 时间及日志 | S5候选已验证first/last/attempt入队、同响应observed_at、真实active_step及耗时；133未发布。S6实际文件日志、任务关联、持久挂载和轮转已通过[候选限定验收](../operations/evidence/analysis-file-logs-s6-20261120-01/README.md)；0Run/模型，正式未发布，不新增脱敏专项 |
| 正式/候选版本 | 正式 80 个操作已与 Swagger 核对。候选 82 个操作包含两个湖读取接口，132–134 的风险、任务入队和业务判定字段已候选验证。正式统一切换及新真实批次读回仍待 |
| 人员选择、资产目录 | 业务后端给出 HTTP 合同，含可写回的身份及查找返回。调用要求已列入交接。负责人 11-21 确认附件联调移出本期。 |
| 告警取数和页面跳转 | 已提供现有取数接口，主体、轮次和资源 ID 的代表跳转通过候选 PG/TCP 验收。正式版本和新真实数据的联验仍待。登录、界面转发设施和SF07来源/轮数展示移出本期。 |
| 最终验收 | 正式版本统一与新选真实告警一轮合并。按同版配置、库及HTTP对照写入、读取、跳转和真实流程。 |

### SF04事件与Case业务判定

`business_verdict` 允许 `malicious`（恶意）、`benign`（正常或已授权）、`false_positive`（检测或归因前提不成立）、`needs_review`（证据不足定性或仍有冲突）。`null` 表示该份记录未保存有效判定。读端保留原结论、确定性、人工分类及新鲜度。字段是模型意见，采用动作保留原来源。

| 位置 | 读取字段与归属 |
| --- | --- |
| `GET /incidents`、`GET /incidents/{incident_id}` | `business_verdict` 沿 `facts.latest_diagnosis_id` 读原诊断。 |
| `GET /incidents/{incident_id}/analysis`、`GET /incidents/{incident_id}/analysis/runs/{run_id}` | `current.result.business_verdict`、`entries[].result.business_verdict`、指定轮次的 `result.business_verdict` 各读自己的 `incident_diagnoses`。范围沿现有选入与覆盖字段。 |
| `GET /cases/{case_id}/history`、`GET /cases/{case_id}/results/{result_id}` | `items[].result.business_verdict` 或 `result.business_verdict` 原样读 `results`。 |
| `GET /cases/{case_id}`、`GET /cases/{case_id}/page-data`、`GET /cases/{case_id}/assessments` 和采用预览 | 分别读取 `current_assessment.business_verdict`、`assessment.business_verdict`、`items[].business_verdict` 或预览中的当前/候选字段。采用记录按原来唯一有效的模型 Result 来源读取。 |

本步用隔离 PostgreSQL 和真实回环 HTTP 验证保存、读取与采用旧结果。模型返回用本地夹具，正式环境及最后新真实告警轮次待联验。[验收回执](../operations/evidence/subject-business-verdict-sf04-20261120-01/README.md)

### SF05建议字段的页面接线

本轮候选展示沿用已有HTTP和数据库字段，源码、直接检查、实际读取/浏览器及限定独审均已通过，范围见[本批回执](../operations/evidence/recommendation-display-sf05-20261120-01/README.md)。产品接线应遵守以下对应关系，不新增同义接口：

| 阅读入口 | 已有取数与显示规则 |
| --- | --- |
| 当前Case采用来源 | `GET /cases/{case_id}`取得`current_assessment.sources[].result_id`，按来源逐一`GET /cases/{case_id}/results/{result_id}`；先校验Result、Case及返回Run关联，再逐来源展示，不从history最新记录补值。仅有人工版本或工件的来源不伪造建议 |
| 指定Case轮次 | `GET /cases/{case_id}/runs/{run_id}`列出的Result或明确选择的Result；读取后须校验`result.id`、`result.case_id`、`result.source_run_id`及返回`run`，切换和刷新保持所选轮次 |
| 指定Alert轮次 | `GET /alerts/{alert_id}/analysis/runs/{run_id}`的已存`result.recommendations`；4173记录页另按冻结`latest_triage_id`显示当前分诊来源，原件不改写 |
| 建议卡片 | `reason`是正文，`action_type`是辅助类别；`targets[].display_name/object_key`保持原目标。`source_refs`的类型、标识、角色、字段路径和记录键，以及`limitations`分别展开；不根据当前成员补目标 |
| 审批与空态 | `approval_requirement=required/not_required/unknown`分别显示需要/无需/未知，缺失也未知。审批要求与实际审批/执行分开；成功空列表、没有建议字段和读取失败分别显示，失败保留只读重试。Incident的`open_questions`不充当建议 |

4173服务模式本步只改Case建议绑定，Alert服务详情入口仍未实现；4173实际记录和4177分别按其来源验证，不能互相代替完整产品接入。4177收尾报告的建议继续标明报告来源，不冒充正式或已采用Result。SF06当前判断依据/未决项的投影另步处理。

### SF06采用Result的依据、范围与未决项接线

沿上述采用来源与指定Run的Result读取复用现有字段，候选实现、直接检查、真实HTTP/PG/浏览器及限定独审通过，范围见[本批回执](../operations/evidence/assessment-basis-sf06-20261120-01/README.md)。产品读取需保留以下语义：

| 保存字段 | 阅读规则 |
| --- | --- |
| `findings[].statement/state` | 原文与observed/inferred/unresolved/withdrawn状态分别显示，待核和撤回不充当已证实支持；不只截取摘要前三条 |
| `findings[].support/counterevidence/limitations` | 支持、反证及限制分开，保留EvidenceRef的类型、身份、来源角色、字段路径和记录键；人工陈述不因位于support就变成独立机器证据 |
| `questions[].text/state/answer` | 已回答问题及其保存的answer单列；open/unresolved/not_attempted按原状态保留。没有回答正文不补造答案，不把未尝试等同于已查空 |
| `questions[].evidence_requirements/evidence_refs/limitations` | 按原值阅读所需证据、来源及限制，不改写为新工具执行计划 |
| 发现/问题的`scope`及`case_impact.affected_scope` | 原告警、对象、时间窗和限制保持，包括后来移出的成员；`current_assessment.members`原覆盖与当前成员覆盖分开。`case_impact`的summary/supported_changes/cannot_generalize/next_steps分别呈现 |
| 空态与执行信息 | 空数组与缺字段、来源未读取/未导出、身份不符或读取失败分开；`run.stop_reason`仅作执行详情，不拼接到业务未决项/限制，不按保留字删除原始正文 |

前批单步仅处理Result来源，人工反馈版本/纯工件当时明确“正文未读取”；本批完整来源接线见下节，仍不从最新Result替代，也不能据此关闭整个SF06。当前采用新鲜度、当前覆盖、结论与模型质量沿原合同分开。

旧11-14“未注册/待提供/待发布”不能覆盖11-17正式80操作及本批现场证据。Q1–Q6及查询跨度规则继续沿[目标合同第8节](../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#8-后续已确认更新对http的要求)；人工定向/手动综合、同ID新材料入口、模型读附件正文及未定执行时间窗各保留原决定，不因本次接通重启。

### SF06人工版本与工件来源HTTP接线（候选，正式未发布）

当前判断、`page-data.assessment`和采用历史/预览的`sources`在保留原引用字段的同时增补以下定位信息。字段只读关联同tenant/Case下被引用的原记录，不读Task的current指针；不改告警DTO和数据库表。旧客户端可以忽略新增字段，新页面若读到缺定位字段的旧服务响应则明确显示无法定位，不遍历任务或猜最新轮次。

| 页面内容 | HTTP与定位字段 | 数据来源与核对 |
| --- | --- | --- |
| 已采用人工反馈 | `sources[].task_revision_id` + 新增`task_id` → `GET /cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` | `case_assessment_sources`关联`task_revisions`；显示原`result_text/result_scope/source_refs`、标题/说明、版本/状态、负责人/时间记录，与任务current版本分开 |
| 已采用Run工件 | `sources[].artifact_id` + 新增非空`run_id` → `GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}` | 同Case的`artifacts.run_id`；核工件身份、正文hash/size及原availability，不借同名工件 |
| 已采用Case级工件 | `sources[].artifact_id` + 明确`run_id=null` → `GET /cases/{case_id}/artifacts/{artifact_id}` | `artifacts.run_id IS NULL`；该入口不代替Run工件读取 |

`task_id`仅人工版本来源有值，`run_id`仅Run级工件来源有值；Result来源这两个字段均为null，仍沿已有Result GET读取。工件仅显示自身保存的JSON/文本及元数据，不套用Result的发现或结论含义。`available/retained_*`保留原正文状态，外部原件未加载、正文缺失、读失败和已保存空文本分别呈现；单个失败保留其他来源并可GET重试。4173已存记录按同tenant/Case/环境和原版本/工件恢复，标明导出正文，旧导出不改写。

本步实施及实际PG/HTTP/页面验收沿[来源链单步计划](../../openspec/changes/complete-socai2-investigation-chain/http-real-data-connection-20261120.md#p2本轮单步sf06人工版本与工件的完整来源链)。采用来源的受控PG构造不等于新增人工采用API，完整产品接入和P4新真实告警批仍需各自验收。

## 6. 提供方必须给出的交付说明与直接验收

每个需求组需要回答：提供什么、由谁负责、从哪些记录取得、现有/待提供/规则待定、对应读取或写入用例。SQL、DDL、队列键和内部类名由提供方自行确定；HTTP侧负责最终路由及Swagger，不把数据库对象原样当对外数据结构。

| 要核对的内容 | 直接通过标准 |
| --- | --- |
| 展示与跳转 | 返回真实alert/incident/case/task/run/result/material/artifact或修订ID；点名称/来源能读到同一对象。分析任务ID与人工任务ID的用途、路径分开 |
| 列表完整性 | 筛选/排序后总数、续页、导出和统计范围一致；缺失或截断可见且有继续读取办法；不以当前页或已发现主体冒充全部 |
| 操作闭环 | 输入→实际保存→返回身份/版本→GET读回一致；未保存/冲突/失效明确报错，不以按钮点击或HTTP成功代替业务完成 |
| 历史与依据 | 当时的成员、材料、人工修订、报告和图可按冻结身份读回；新记录不覆盖旧失败/unknown/原答 |
| 分析状态 | 已受理、真正执行、完成/失败/跳过分别表达；业务结论、交付、覆盖、新鲜度、采用和模型质量分别读取；无结果是空态，不补造结论 |
| 依赖与空态 | 没匹配资产、人员未解析、无诊断、无报告、未知时间、查询失败/空结果和文件失效分别说明；外部提供方未验收，不记作整链完成 |
| 代码和版本边界 | 对外HTTP通过用例端口接调查核心；内部互调留在内部；一个目标版本，不增加旧API别名、兼容表或双套行为 |

本次P1只做结构核对及必要代表读取，复用有效存取证据，不重跑全表全接口矩阵。P2按[接通方案](../../openspec/changes/complete-socai2-investigation-chain/http-real-data-connection-20261120.md)逐个补实际缺口，再进入新真实批次；不能因映射写齐就勾选业务任务。

## 7. 125项逐项归属

本节按功能编号对应 2026-11-21 正式 C173 的 HTTP，公共路径前缀为 `/api/v1/socai2`。请求、返回和错误结构查同版 OpenAPI。告警和事件的分区沿详情 `section_urls`，Case 需要对象时由实际成员回到告警读取。

页面跳转使用服务返回的主体 ID、任务、Run、结果和工件链接。我方提供已实现的原型地址和 HTTP 入参示例，业务后端回填人员和资产接口。附件和已确认的暂缓项沿本期范围。每项按接口与存取来源列示，验收证据见正式回执。

[正式 OpenAPI](../../deploy/aisoc21/c173-release-20261121-03/contract/openapi.json) · [C173 对接入口](c173-backend-handoff-20261121.md) · [验收与正式读回](../../docs/operations/evidence/c173-bounded-json-20261121-01/README.md)

<!-- FEATURE_MAP_START -->
### 告警（22项）

| 功能 | 数据需求组/内部来源 | 现行HTTP（公共前缀省略） | 本次核对结论及剩余边界 |
| --- | --- | --- | --- |
| F01-01 默认九列 | A1 | `GET /alerts`<br>`GET /{subject}/{identity}/records/{section}` | **含外部待接**：现行HTTP及内部存取已定位。 人员或资产目录按交接清单与业务后端联调。 分区：alerts/records/assets。 |
| F01-02 搜索与快捷筛选 | A1 | `GET /alerts` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F01-03 排序与列选择 | A1 | `GET /alerts` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F01-04 指标与分页 | A1 | `GET /alerts` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F01-05 预览及打开详情 | A1 | `GET /alerts/{alert_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F01-06 导出与批量选择 | A1 | `GET /alerts`<br>`POST /alerts/management-batch`<br>`GET /alerts/export` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F01-09 刷新与清除条件 | A1 | `GET /alerts` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F01-07 标题、属性与来源 | A1 | `GET /alerts/{alert_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F02-01 检测信息与 ATT&CK | A2 | `GET /alerts/{alert_id}`<br>`GET /alerts/{alert_id}/materials/{material_id}`<br>`GET /{subject}/{identity}/records/{section}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 分区：alerts/records/objects,sources。 |
| F03-01 AI 分诊与评分 | A3 | `GET /alerts/{alert_id}`<br>`GET /alerts/{alert_id}/analysis`<br>`GET /alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /alerts/{subject_id}/analysis-tasks`<br>`GET /alerts/{subject_id}/analysis-tasks/{task_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F03-02 发生了什么与依据 | A3 | `GET /alerts/{alert_id}/analysis`<br>`GET /alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F03-03 查看分诊过程 | A3 | `GET /alerts/{alert_id}/analysis`<br>`GET /alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /alerts/{subject_id}/analysis-tasks`<br>`GET /alerts/{subject_id}/analysis-tasks/{task_id}` | **接口/存储已映射**：自动入站A任务及实际Run/步骤可读；不恢复已退役手动analyze。 |
| F08-01 实体、IOC 与相关告警 | A5 | `GET /alerts/{alert_id}/same-host-alerts`<br>`GET /alerts/{alert_id}`<br>`GET /alerts/{alert_id}/materials/{material_id}`<br>`GET /{subject}/{identity}/records/{section}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 分区：alerts/records/objects,related_alerts。 |
| F03-04 人工判定及理由 | A4 | `POST /alerts/{alert_id}/feedback`<br>`POST /alerts/feedback-batch`<br>`GET /alerts/{alert_id}`<br>`GET /{subject}/{identity}/records/{section}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 分区：alerts/records/activities。 |
| F03-05 相似历史复核 | A5 | `GET /alerts/{alert_id}/review-candidates`<br>`GET /alerts/{alert_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F23-01 管理告警 | A4 | `PATCH /alerts/{alert_id}/management`<br>`POST /alerts/management-batch`<br>`GET /alerts/{alert_id}`<br>`GET /{subject}/{identity}/records/{section}` | **含外部待接**：现行HTTP及内部存取已定位。 人员或资产目录按交接清单与业务后端联调。 分区：alerts/records/activities。 |
| F13-01 查看所属事件和 Case | A6 | `GET /{subject}/{identity}/records/{section}`<br>`GET /incidents/{incident_id}`<br>`GET /cases/{case_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 分区：alerts/records/incidents,cases。 |
| F13-02 关联／新建与准备调查 | A6 | `GET /{subject}/{identity}/records/{section}`<br>`POST /cases`<br>`POST /cases/{case_id}/associations`<br>`GET /cases/{case_id}`<br>`GET /cases/{subject_id}/analysis-tasks`<br>`GET /cases/{subject_id}/analysis-tasks/{task_id}` | **接口/存储已映射**：普通关联/建案返回真实allocations及initial_task；助手入口暂缓。 分区：alerts/records/cases。 |
| F01-08 时间线 | A7 | `GET /alerts/{alert_id}`<br>`GET /{subject}/{identity}/records/{section}`<br>`GET /alerts/{alert_id}/analysis` | **接口/存储已映射**：现行HTTP及内部存取已定位。 分区：alerts/records/activities。 |
| F04-01 原始记录阅读 | A2 | `GET /alerts/{alert_id}`<br>`GET /alerts/{alert_id}/materials/{material_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F05-01 来源引用与历史版本 | A2 | `GET /{subject}/{identity}/records/{section}`<br>`GET /alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /cases/{case_id}/runs/{run_id}/materials/{material_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 分区：alerts/records/sources,source_artifacts。 |
| F27-01 响应建议与自动处理 | A8 | `GET /alerts/{alert_id}/analysis`<br>`GET /alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /{subject}/{identity}/records/{section}` | **接口/存储已映射**：已保存建议及responses关联可读；新审批/执行继续暂缓，关联不证明执行成功。 分区：alerts/records/responses。 |

### 事件（15项）

| 功能 | 数据需求组/内部来源 | 现行HTTP（公共前缀省略） | 本次核对结论及剩余边界 |
| --- | --- | --- | --- |
| F06-01 列表与搜索筛选 | E1 | `GET /incidents` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F06-02 四项指标 | E1 | `GET /incidents` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F06-03 预览与进入详情 | E1 | `GET /incidents/{incident_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F06-06 处理中与队列压缩 | E1 | `GET /incidents/grouping-summary` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F06-07 刷新、日期、列和导出 | E1 | `GET /incidents`<br>`GET /incidents/export` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F23-06 批量管理事件 | E2 | `POST /incidents/management-batch`<br>`GET /incidents/{incident_id}`<br>`GET /{subject}/{identity}/records/{section}` | **含外部待接**：现行HTTP及内部存取已定位。 人员或资产目录按交接清单与业务后端联调。 分区：incidents/records/activities。 |
| F23-02 事件管理 | E2 | `PATCH /incidents/{incident_id}/management`<br>`GET /incidents/{incident_id}`<br>`GET /{subject}/{identity}/records/{section}` | 正式 132 支持事件风险、人工优先级与管理记录。人员选择由业务后端提供。 |
| F06-04 概览与 ATT&CK | E3 | `GET /incidents/{incident_id}`<br>`GET /{subject}/{identity}/records/{section}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 分区：incidents/records/members,objects。 |
| F07-01 当前诊断和最近尝试 | E3 | `GET /incidents/{incident_id}/analysis`<br>`GET /incidents/{incident_id}/analysis/runs/{run_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`POST /incidents/{incident_id}/diagnose`<br>`GET /incidents/{subject_id}/analysis-tasks`<br>`GET /incidents/{subject_id}/analysis-tasks/{task_id}` | 当前诊断、指定 Run 和最新尝试分别读取。正式判定字段为 `result.business_verdict`，未保存有效判定时为 `null`。 |
| F06-05 时间线与共同线索 | E4 | `GET /{subject}/{identity}/records/{section}`<br>`GET /incidents/{incident_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 分区：incidents/records/members,objects。 |
| F08-02 关联分析图 | E4 | `GET /{subject}/{identity}/records/{section}`<br>`GET /incidents/{incident_id}/analysis`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 分区：incidents/records/members,objects。 |
| F08-03 成员告警 | E4 | `GET /{subject}/{identity}/records/{section}`<br>`GET /alerts/{alert_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 分区：incidents/records/members。 |
| F08-04 涉及对象与资产匹配 | E4 | `GET /{subject}/{identity}/records/{section}` | **含外部待接**：现行HTTP及内部存取已定位。 人员或资产目录按交接清单与业务后端联调。 分区：incidents/records/objects,assets。 |
| F23-03 处理活动 | E5 | `GET /{subject}/{identity}/records/{section}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 分区：incidents/records/activities。 |
| F13-03 进入／创建／关联 Case | E6 | `GET /{subject}/{identity}/records/{section}`<br>`POST /cases`<br>`POST /cases/{case_id}/associations`<br>`GET /cases/{case_id}`<br>`GET /cases/{subject_id}/analysis-tasks`<br>`GET /cases/{subject_id}/analysis-tasks/{task_id}` | **接口/存储已映射**：实际allocations/initial_task及唯一事件接收者；另有Case→Case related-cases读取。 分区：incidents/records/cases。 |

### 调查与运行（88项）

| 功能 | 数据需求组/内部来源 | 现行HTTP（公共前缀省略） | 本次核对结论及剩余边界 |
| --- | --- | --- | --- |
| F09-01 四项案件指标 | C1 | `GET /cases` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F09-02 搜索筛选和分页 | C1 | `GET /cases` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F09-03 列选择与排序 | C1 | `GET /cases` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F09-08 日期范围与导出 | C1 | `GET /cases`<br>`GET /cases/export` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F09-09 手动与自动刷新 | C1 | `GET /cases` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F09-10 案件预览 | C1 | `GET /cases/{case_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F09-11 调查运行与管理设置入口 | C1 | `GET /analysis-runs`<br>`GET /cases/{case_id}/runs/{run_id}`<br>`GET /alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /incidents/{incident_id}/analysis/runs/{run_id}` | **接口/存储已映射**：统一Run目录已提供；管理设置只有未定义占位，不新增配置平台。 |
| F09-04 新建 Case | C2 | `POST /cases`<br>`GET /cases/{case_id}`<br>`GET /cases/{case_id}/runs/{run_id}`<br>`GET /cases/{subject_id}/analysis-tasks`<br>`GET /cases/{subject_id}/analysis-tasks/{task_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F09-05 资料页头与刷新 | C2 | `GET /cases/{case_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F23-04 管理 Case | C2 | `GET /cases/{case_id}`<br>`PATCH /cases/{case_id}/page-data`<br>`GET /cases/{case_id}/management`<br>`PATCH /cases/{case_id}/management`<br>`POST /cases/{case_id}/close`<br>`POST /cases/{case_id}/reopen` | 正式 132 支持 Case 风险、人工优先级、管理和关闭重开。人员选择由业务后端提供。 |
| F14-01 跨页执行提示 | C5 | `GET /cases/{case_id}`<br>`GET /cases/{case_id}/history`<br>`GET /cases/{case_id}/runs/{run_id}`<br>`GET /cases/{subject_id}/analysis-tasks`<br>`GET /cases/{subject_id}/analysis-tasks/{task_id}` | 按主体或原 task 读取任务、实际尝试、入队与观察时间，以及 `active_step`。 |
| F09-06 案件说明和范围概况 | C2 | `GET /cases/{case_id}`<br>`GET /cases/{case_id}/tasks`<br>`GET /cases/{case_id}/history` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F10-01 案件分类与截止时间 | C2 | `GET /cases/{case_id}`<br>`PATCH /cases/{case_id}/page-data`<br>`GET /cases/{case_id}/page-data` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F11-01 当前采用判断 | C3 | `GET /cases/{case_id}`<br>`GET /cases/{case_id}/page-data`<br>`GET /cases/{case_id}/results/{result_id}`<br>`GET /cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /cases/{case_id}/artifacts/{artifact_id}` | 沿 `current_assessment.sources` 读取采用依据。业务判定沿唯一采用的模型 Result 读取，产品页面接入仍待联调。 |
| F12-01 判断覆盖与依据变化 | C3 | `GET /cases/{case_id}`<br>`GET /cases/{case_id}/page-data`<br>`GET /cases/{case_id}/results/{result_id}`<br>`GET /cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /cases/{case_id}/artifacts/{artifact_id}` | 沿采用结果读原范围、依据和未决项。当前成员覆盖单独读取，产品页面接入仍待联调。 |
| F12-02 回查判断来源 | C3 | `GET /cases/{case_id}`<br>`GET /cases/{case_id}/results/{result_id}`<br>`GET /alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /incidents/{incident_id}/analysis/runs/{run_id}`<br>`GET /cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F11-02 结论中的未解决问题 | C3 | `GET /cases/{case_id}`<br>`GET /cases/{case_id}/results/{result_id}`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /cases/{case_id}/artifacts/{artifact_id}` | 沿采用 Result 读取问题、发现、原范围及其状态。技术停止码保留为执行信息，产品页面接入仍待联调。 |
| F09-07 ATT&CK 阶段与详细信息 | C2 | `GET /cases/{case_id}`<br>`GET /alerts/{alert_id}`<br>`GET /alerts/{alert_id}/materials/{material_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F11-03 显式采用其他结果 | C3 | `GET /cases/{case_id}/results/{result_id}/adoption-preview`<br>`POST /cases/{case_id}/results/{result_id}/adopt`<br>`GET /cases/{case_id}`<br>`GET /cases/{case_id}/assessments`<br>`GET /cases/{case_id}/activities` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F20-01 事实与认识时间线 | C4 | `GET /cases/{case_id}/story`<br>`GET /alerts/{alert_id}/materials/{material_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 本行普通功能保留，问答部分暂缓。 |
| F20-02 搜索与等级筛选 | C4 | `GET /cases/{case_id}/story` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F20-03 单选／多选告警 | C4 | `GET /cases/{case_id}/story`<br>`GET /alerts/{alert_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F20-04 围绕条目或全案提问 | C12 | 暂缓，无已实现操作 | **暂缓**：负责人11-20确认继续暂缓；AI两个POST仅返回501，审批执行无本服务入口，不计已接通。 |
| F20-05 回到结果和人工版本 | C4 | `GET /cases/{case_id}/story`<br>`GET /cases/{case_id}/results/{result_id}`<br>`GET /cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F14-02 活跃与待启动分开 | C5 | `GET /cases/{case_id}`<br>`GET /cases/{case_id}/runs/{run_id}`<br>`GET /cases/{subject_id}/analysis-tasks`<br>`GET /cases/{subject_id}/analysis-tasks/{task_id}` | 读取 accepted/running、准备阶段、实际步骤及本地结束。历史未知时间返回 `null`。 |
| F14-03 检查更新 | C5 | `GET /cases/{case_id}`<br>`GET /cases/{case_id}/runs/{run_id}`<br>`GET /cases/{subject_id}/analysis-tasks`<br>`GET /cases/{subject_id}/analysis-tasks/{task_id}`<br>`POST /cases/{case_id}/investigations` | **接口/存储已映射**：mode=check提交并读取原task；无变化可skipped/no_changes，无Run不伪造。 |
| F14-04 启动调查 | C5 | `GET /cases/{case_id}/runs/{run_id}`<br>`GET /cases/{case_id}/results/{result_id}`<br>`GET /cases/{subject_id}/analysis-tasks`<br>`GET /cases/{subject_id}/analysis-tasks/{task_id}`<br>`POST /cases/{case_id}/investigations` | **接口/存储已映射**：新案initial_task；再次调查mode=rerun。202只代表受理，同key读回，不调用start。 |
| F16-01 已有结果摘要 | C5 | `GET /cases/{case_id}/history`<br>`GET /cases/{case_id}/runs/{run_id}`<br>`GET /cases/{case_id}/results/{result_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F22-01 人工摘要与待办 | C5 | `GET /cases/{case_id}/tasks` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F14-05 历史与故事入口 | C5 | `GET /cases/{case_id}/history`<br>`GET /cases/{case_id}`<br>`GET /cases/{case_id}/tasks` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F14-06 历史记录分类与选择 | C6 | `GET /cases/{case_id}/history`<br>`GET /alerts/{alert_id}/analysis`<br>`GET /incidents/{incident_id}/analysis` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F15-01 状态、交付与投入 | C6 | `GET /cases/{case_id}/runs/{run_id}`<br>`GET /cases/{case_id}/results/{result_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F16-02 结果比较 | C6 | `GET /cases/{case_id}/results/{result_id}`<br>`GET /cases/{case_id}/runs/{run_id}` | **接口/存储已映射**：只读冻结comparison_context及前轮Run/结果；不提交调查，不接受客户端指定比较对象。 |
| F12-03 历史范围与冻结引用 | C6 | `GET /cases/{case_id}/runs/{run_id}`<br>`GET /cases/{case_id}/runs/{run_id}/materials/{material_id}`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F13-04 当前成员及事件 | C7 | `GET /cases/{case_id}`<br>`GET /alerts/{alert_id}`<br>`GET /incidents/{incident_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F13-05 添加告警／事件 | C7 | `GET /alerts`<br>`GET /incidents`<br>`GET /cases/{case_id}`<br>`POST /cases/{case_id}/associations`<br>`GET /cases/{subject_id}/analysis-tasks`<br>`GET /cases/{subject_id}/analysis-tasks/{task_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F13-06 移动成员 | C7 | `GET /cases/{case_id}`<br>`POST /cases/{case_id}/members/move` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F13-07 管理所选告警 | C7 | `POST /alerts/management-batch`<br>`GET /alerts/{alert_id}`<br>`GET /{subject}/{identity}/records/{section}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 分区：alerts/records/activities。 |
| F13-08 成员变化后的提示 | C7 | `GET /cases/{case_id}`<br>`GET /cases/{case_id}/runs/{run_id}`<br>`GET /cases/{subject_id}/analysis-tasks`<br>`GET /cases/{subject_id}/analysis-tasks/{task_id}`<br>`POST /cases/{case_id}/investigations` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F19-01 当前底图与阅读 | C8 | `GET /cases/{case_id}`<br>`GET /{subject}/{identity}/records/{section}`<br>`GET /cases/{case_id}/results/{result_id}`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 分区：由Case.members取得alert_id，再读alerts/records/objects。 |
| F19-02 筛选、布局与节点详情 | C8 | `GET /{subject}/{identity}/records/{section}`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 分区：由节点来源取得alert_id，再读alerts/records/objects。 |
| F25-01 推荐线索与候选预览 | C8 | `GET /cases/{case_id}/exploration-candidates` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F25-02 实体扩展与撤销 | C8 | `GET /cases/{case_id}/exploration-candidates`<br>`GET /{subject}/{identity}/records/{section}`<br>`GET /cases/{case_id}/exploration-base` | **接口/存储已映射**：现行HTTP及内部存取已定位。 分区：由候选来源取得alert_id，再读alerts/records/objects。 |
| F25-03 保存／恢复探索 | C8 | `GET /cases/{case_id}/exploration-base`<br>`GET /cases/{case_id}/exploration`<br>`PUT /cases/{case_id}/exploration` | **接口/存储已映射**：GET底图→PUT exploration保存→GET恢复；不修改成员、不生成Run。 |
| F25-04 正式加入本案 | C8 | `GET /cases/{case_id}/exploration-candidates`<br>`GET /cases/{case_id}`<br>`POST /cases/{case_id}/associations`<br>`GET /cases/{subject_id}/analysis-tasks`<br>`GET /cases/{subject_id}/analysis-tasks/{task_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F26-01 询问所选对象 | C12 | 暂缓，无已实现操作 | **暂缓**：负责人11-20确认继续暂缓；AI两个POST仅返回501，审批执行无本服务入口，不计已接通。 |
| F21-01 按对象浏览 | C9 | `GET /cases/{case_id}`<br>`GET /{subject}/{identity}/records/{section}`<br>`GET /cases/{case_id}/page-data` | **含外部待接**：现行HTTP及内部存取已定位。 人员或资产目录按交接清单与业务后端联调。 分区：由Case.members取得alert_id，再读alerts/records/objects,assets。 |
| F21-02 按调查浏览 | C9 | `GET /cases/{case_id}/history`<br>`GET /cases/{case_id}/runs/{run_id}`<br>`GET /cases/{case_id}/results/{result_id}`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F21-03 证据、威胁与覆盖 | C9 | `GET /cases/{case_id}/page-data`<br>`POST /cases/{case_id}/evidence-index`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F21-04 原件和引用回查 | C9 | `GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /cases/{case_id}/artifacts/{artifact_id}`<br>`GET /cases/{case_id}/runs/{run_id}/materials/{material_id}`<br>`GET /alerts/{alert_id}/materials/{material_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /alerts/{identity}/artifacts/{artifact_id}`<br>`GET /incidents/{identity}/artifacts/{artifact_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F22-02 列表、状态和待办数 | C10 | `GET /cases/{case_id}/tasks` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F22-03 用户新建与分配 | C10 | `GET /cases/{case_id}`<br>`POST /cases/{case_id}/tasks`<br>`GET /cases/{case_id}/tasks/{task_id}` | **含外部待接**：现行HTTP及内部存取已定位。 人员或资产目录按交接清单与业务后端联调。 |
| F22-04 编辑、取消及状态更新 | C10 | `GET /cases/{case_id}/tasks/{task_id}`<br>`GET /cases/{case_id}`<br>`PUT /cases/{case_id}/tasks/{task_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F22-05 完成结果与适用范围 | C10 | `GET /cases/{case_id}/tasks/{task_id}`<br>`GET /cases/{case_id}`<br>`PUT /cases/{case_id}/tasks/{task_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F22-06 完成人、修改人与历史 | C10 | `GET /cases/{case_id}/tasks/{task_id}`<br>`GET /cases/{case_id}/tasks/{task_id}/revisions`<br>`GET /cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F22-07 并发冲突处理 | C10 | `PUT /cases/{case_id}/tasks/{task_id}`<br>`GET /cases/{case_id}/tasks/{task_id}`<br>`GET /cases/{case_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F22-08 保存后的调查影响 | C10 | `PUT /cases/{case_id}/tasks/{task_id}`<br>`GET /cases/{subject_id}/analysis-tasks`<br>`GET /cases/{subject_id}/analysis-tasks/{task_id}`<br>`POST /cases/{case_id}/investigations`<br>`GET /cases/{case_id}/tasks/{task_id}` | **接口/存储已映射**：有效人工事实保存后进入后续check；元数据改动不当新事实，保存不自动采用或结案。 |
| F23-05 处理活动与目标 | C11 | `GET /cases/{case_id}/activities` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F24-01 评论阅读与提交 | C11 | `POST /cases/{case_id}/comments`<br>`GET /cases/{case_id}/comments`<br>`GET /cases/{case_id}/activities` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F24-02 已有附件查看／下载 | C11 | 本期暂缓 | 附件联调移出本期。 |
| F24-03 上传补充附件 | C11 | 本期暂缓 | 附件联调移出本期。 |
| F26-02 同案统一对话 | C12 | 暂缓，无已实现操作 | **暂缓**：负责人11-20确认继续暂缓；AI两个POST仅返回501，审批执行无本服务入口，不计已接通。 |
| F26-03 范围选择与问题编辑 | C12 | 暂缓，无已实现操作 | **暂缓**：负责人11-20确认继续暂缓；AI两个POST仅返回501，审批执行无本服务入口，不计已接通。 |
| F26-04 建议问题 | C12 | 暂缓，无已实现操作 | **暂缓**：负责人11-20确认继续暂缓；AI两个POST仅返回501，审批执行无本服务入口，不计已接通。 |
| F26-05 发送与只读分析 | C12 | 暂缓，无已实现操作 | **暂缓**：负责人11-20确认继续暂缓；AI两个POST仅返回501，审批执行无本服务入口，不计已接通。 |
| F26-06 失败与人工事实续接 | C12 | 暂缓，无已实现操作 | **暂缓**：负责人11-20确认继续暂缓；AI两个POST仅返回501，审批执行无本服务入口，不计已接通。 |
| F26-07 保存到调查记录 | C12 | 暂缓，无已实现操作 | **暂缓**：负责人11-20确认继续暂缓；AI两个POST仅返回501，审批执行无本服务入口，不计已接通。 |
| F26-08 引用与继续追问 | C12 | 暂缓，无已实现操作 | **暂缓**：负责人11-20确认继续暂缓；AI两个POST仅返回501，审批执行无本服务入口，不计已接通。 |
| F14-07 跨主体运行目录 | R1 | `GET /analysis-runs`<br>`GET /cases/{case_id}/runs/{run_id}`<br>`GET /alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /incidents/{incident_id}/analysis/runs/{run_id}` | **接口/存储已映射**：直接读取统一目录；尚无Run的任务从主体任务列表读取，不靠枚举全部主体拼目录。 |
| F15-02 运行统计和卡片摘要 | R1 | `GET /analysis-runs`<br>`GET /cases/{case_id}/runs/{run_id}`<br>`GET /alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /incidents/{incident_id}/analysis/runs/{run_id}`  | 统计与目录使用同一筛选范围，Run 详情沿 `detail_url`。正式返回 `statistics.not_escalated_count` 和 `items[].escalation_decision`。[未升级调查取数](run-directory-http.md#未升级调查) |
| F16-03 目标、结论、发现与限制 | R2 | `GET /cases/{case_id}/results/{result_id}`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /incidents/{incident_id}/analysis/runs/{run_id}` | 指定事件/Case 结果读取正文、发现、来源和 `business_verdict`。确定性和人工分类分别读取。 |
| F15-03 执行、交付及用量 | R2 | `GET /cases/{case_id}/runs/{run_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /cases/{subject_id}/analysis-tasks`<br>`GET /cases/{subject_id}/analysis-tasks/{task_id}` | Run 状态、交付、用量沿各记录读取。任务等待和尝试耗时由服务返回，unknown 保留真实状态。 |
| F12-04 查看当轮原始输入 | R2 | `GET /cases/{case_id}/runs/{run_id}`<br>`GET /cases/{case_id}/runs/{run_id}/materials/{material_id}`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F22-09 用户创建人工任务／询问结果 | C10 | `POST /cases/{case_id}/tasks` | **接口/存储已映射**：现行HTTP及内部存取已定位。 本行普通功能保留，问答部分暂缓。 |
| F17-01 已保存分析过程 | R3 | `GET /cases/{case_id}/runs/{run_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /analysis-runs/{run_id}/steps`<br>`GET /analysis-runs/{run_id}/steps/{step_id}`<br>`GET /analysis-runs/{run_id}/artifacts` | **接口/存储已映射**：现行HTTP及内部存取已定位。 本行普通功能保留，问答部分暂缓。 完整目录读next_cursor及content_url，不以旧trace摘要上限代替全量。 |
| F17-02 步骤账本 | R3 | `GET /cases/{case_id}/runs/{run_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /analysis-runs/{run_id}/steps`<br>`GET /analysis-runs/{run_id}/steps/{step_id}`<br>`GET /analysis-runs/{run_id}/artifacts`<br>`GET /cases/{subject_id}/analysis-tasks`<br>`GET /cases/{subject_id}/analysis-tasks/{task_id}` | 步骤目录使用游标续页，当前实际步骤沿 `active_step`，原件沿 `content_url`。 |
| F18-01 步骤输入／输出原件 | R3 | `GET /cases/{case_id}/runs/{run_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /analysis-runs/{run_id}/steps`<br>`GET /analysis-runs/{run_id}/steps/{step_id}`<br>`GET /analysis-runs/{run_id}/artifacts` | **接口/存储已映射**：现行HTTP及内部存取已定位。 完整目录读next_cursor及content_url，不以旧trace摘要上限代替全量。 |
| F17-03 当轮能力与投入 | R3 | `GET /cases/{case_id}/runs/{run_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /analysis-runs/{run_id}/steps`<br>`GET /analysis-runs/{run_id}/steps/{step_id}`<br>`GET /analysis-runs/{run_id}/artifacts` | **接口/存储已映射**：现行HTTP及内部存取已定位。 完整目录读next_cursor及content_url，不以旧trace摘要上限代替全量。 |
| F28-01 查询目录和结果 | R4 | `GET /cases/{case_id}/runs/{run_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /analysis-runs/{run_id}/steps`<br>`GET /analysis-runs/{run_id}/steps/{step_id}`<br>`GET /analysis-runs/{run_id}/artifacts` | **接口/存储已映射**：现行HTTP及内部存取已定位。 完整目录读next_cursor及content_url，不以旧trace摘要上限代替全量。 |
| F28-02 查询状态区分 | R4 | `GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /analysis-runs/{run_id}/steps`<br>`GET /analysis-runs/{run_id}/steps/{step_id}`<br>`GET /analysis-runs/{run_id}/artifacts` | **接口/存储已映射**：现行HTTP及内部存取已定位。 完整目录读next_cursor及content_url，不以旧trace摘要上限代替全量。 |
| F18-02 摘要、原文与引用 | R4 | `GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /cases/{case_id}/artifacts/{artifact_id}`<br>`GET /cases/{case_id}/runs/{run_id}/materials/{material_id}`<br>`GET /alerts/{alert_id}/materials/{material_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /alerts/{identity}/artifacts/{artifact_id}`<br>`GET /incidents/{identity}/artifacts/{artifact_id}`<br>`GET /analysis-runs/{run_id}/steps`<br>`GET /analysis-runs/{run_id}/steps/{step_id}`<br>`GET /analysis-runs/{run_id}/artifacts` | **接口/存储已映射**：现行HTTP及内部存取已定位。 完整目录读next_cursor及content_url，不以旧trace摘要上限代替全量。 |
| F19-03 历史图只读与来源 | R5 | `GET /cases/{case_id}/results/{result_id}`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F19-04 转入当前案件探索 | R5 | `GET /{subject}/{identity}/records/{section}`<br>`GET /cases/{case_id}/exploration-candidates` | **接口/存储已映射**：现行HTTP及内部存取已定位。 分区：由图来源取得alert_id，再读alerts/records/objects。 |
| F16-04 阅读报告及收尾说明 | R6 | `GET /cases/{case_id}/results/{result_id}`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F18-03 下载已有报告 | R6 | `GET /cases/{case_id}/results/{result_id}`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}` | **接口/存储已映射**：现行HTTP及内部存取已定位。 |
| F27-02 响应建议卡片 | R6 | `GET /cases/{case_id}/results/{result_id}`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /incidents/{incident_id}/analysis/runs/{run_id}` | 读取告警或 Case 已保存的建议、目标、审批要求和引用。分别按当前采用或指定轮次取数，产品页面接入仍待联调。 |
| F27-03 审批与意见 | R6 | 暂缓，无已实现操作 | **暂缓**：负责人11-20确认继续暂缓；AI两个POST仅返回501，审批执行无本服务入口，不计已接通。 |
| F27-04 执行记录与回执 | R6 | `GET /{subject}/{identity}/records/{section}`<br>`GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}` | **接口/存储已映射**：只读已有responses及工件；真实动作状态/回执由业务后端提供，新执行暂缓。 分区：按实际alert/incident归属读records/responses；Case由同源工件回查。 |


<!-- FEATURE_MAP_END -->

## 8. 11-14协作回执（历史）

阶段一侧已确认R1、R3/R4是后续提供方需求，不重开已收口的阶段一；明确失败/unknown且无结果的Run也要纳入目录，并补齐R2/E3的过程用量、冻结材料、人工修订和成员告警取数来源。

规划侧已确认R1及R3/R4由调查模块提供查询用例、接口侧确定路径；无需负责人决定内部实现。本轮已读回其后续决定：P3定向独立交付/用户手动综合、P7默认补查规则、P8容量续建/唯一事件接收目标、P9两级关联读取及P10事件诊断覆盖均已有业务要求；P4撤回，P6非本期模型能力。Q5/Q6及跨度最新确认已纳入P11；相应HTTP参数、回执和关联读取按目标合同第8节执行，不能再沿旧“方向/默认时间未定”“多Case同时跟随同事件”推进。其余逐组来源是接口侧提出的供给要求，不因该回执冒称所有功能均已验收。

回执及文档覆盖核对见[本轮证据](../operations/evidence/http-impact-review-20261114-01/README.md)。本轮未实施、发布或推送。
