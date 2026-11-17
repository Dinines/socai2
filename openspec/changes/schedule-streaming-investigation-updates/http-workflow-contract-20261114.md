# 调查业务流程与对外 HTTP 目标合同

2026-11-14。所属 change：`schedule-streaming-investigation-updates`。接口侧与“规划后续实施阶段目标”“阶段一实施”共同完成设计。负责人随后授权“讨论确认后可以实施”，R3/R4读取已按第8.9节完成本地实施与验证；其余仍为目标。无迁移、正式Swagger切换或部署。

**状态：Q1–Q6及第8节具体HTTP合同经核心与接口侧核对一致；R3/R4完整读取已本地验证，其他目标待实施。** 规划侧已采纳第7节路径、三层身份、五种业务状态及最小字段，并明确三个分析任务记录的持久化归属。现行服务与Swagger未改变。统一版本推进，不做新旧兼容；未定项不阻塞已定稿部分。

上游范围以[产品数据提供要求](../../../docs/integration/product-api-data-requirements-20261114.md)为准：125项功能逐项明确需要的数据、输入输出、来源表及提供方。本文落实其中启动/更新流程，不代表全部产品数据需求已经满足。R1跨主体完整目录/统计与R3/R4完整步骤工件读取均已完成本地验证、尚未发布；没有代码或表不能据此删减产品需要。内部具体实现由调查模块负责。

负责人在规划聊天中已明确：告警入站自动分诊，不提供手动启动入口；Case建案自动提交首轮，“再次调查”和事件诊断均异步提交。对外跟踪主体ID→分析任务task_id→实际执行run_id，未执行时run_id可空；内部task/pending流转不暴露给调用方。以下按此目标收口，不再保留同步/异步二选一或request_id第二套外部身份。

后续Q1–Q6已确认的定向分析/手动综合、默认补查范围、100条续建、唯一事件接收Case及两级关联列表，按第8节补充本合同。双方确认的接收资格、待核覆盖、跨Run原件链接和profile分页四项修订已落实。第7节原先已确认的基本启动路径保持其用途；新增业务不能仅靠原`operation_key + mode`或原单Case回执表达，不应在Swagger中提前声明已实现。

## 1. 本轮设计范围与分工

沿“触发→受理→执行→保存→读取→人工处理→再次调查/结案”明确每个外部调用的目的、输入、返回及后续动作，避免把内部阶段或Redis操作暴露给业务后端。

讨论分工：

- 调度规划侧确定业务意图、调度/状态规则及持久化映射，统一主设计、规格、原任务。
- 阶段一侧核实当前执行器、冻结输入、原件/结果和采用的实际约束。
- 接口侧维护本文的业务调用表、最终路径/DTO与错误说明；未定设计不先写入可用Swagger。

完成条件：每项接口均能落到确定的业务规则及保存/读取来源；双方核对后标为“设计定稿”或写明具体暂缓原因。CLI校验只检查文档结构，不代表程序已实现。

## 2. 从业务流程确定哪些地方要 HTTP

| 环节 | 谁触发、做什么 | 对外 HTTP 的职责 | 内部职责 |
| --- | --- | --- | --- |
| 新告警/首次事件 | 入站保存新告警、首次形成事件 | 不要求业务后端为每条消息另调一次启动接口 | 保存后登记A/I首轮，唯一调度器执行 |
| 用户新建Case | 后端提交选中的告警/事件和案件信息 | E01创建Case并登记首轮；用户无需再点“开始” | 保存成员/关联及首轮请求，领取后冻结实际材料 |
| 定时检查 | I每4小时、Case每6小时，期限走内部配置 | 无需后端定时调用，也不暴露定时器控制接口 | 检查状态、期限、有效输入变化，有变化才登记 |
| 用户检查更新 | 用户希望立即检查有没有尚未处理的变化 | 提交check意图；无变化不执行模型 | 执行前读取最新材料，手动可查看本案全部适用I，自动按当前活跃事件及已确认H规则检查；超过7天仍可手动检查 |
| 用户明确重跑 | 用户希望无变化也再做一轮，或处理前次失败 | 异步提交rerun意图，与check分开，返回分析任务task_id | 新任务/新尝试，保留旧失败；不等于自动故障重试 |
| 人工定向分析/手动综合 | 用户提交具体问题/方向及可选工具，结果独立交付；用户另行选择后续综合 | 分别提交并返回分析任务；读取定向结果及后续综合结果和来源关联 | 不因定向结果或建议自动续接；复用适用材料，不默认完整重跑，不自动采用 |
| 容量续建/关联查询 | Case超过100条后实际接收目标可能改变；用户浏览相关Case | 创建/关联/移入返回真实分配；查询先续建Case、再共享事件Case | 保存续建关系及事件唯一接收目标；展示/GET不改变目标或触发调查 |
| 排队与执行 | 唯一调度器领取，有名额且主体空闲才启动 | 读取请求与实际执行状态 | Redis调度、同主体串行、总N、C1–C6及内部组件调用 |
| 查看结果与依据 | 后端展示某一轮的结论、发现和未解决问题 | 复用Case、A/I结果和原件GET，沿实际ID关联 | 结果、原答、派生、引用诊断、工具回执分别保存 |
| 人工核实 | 用户建任务并提交有范围的结果 | 复用E38–E43；保存不等待模型 | 下一次检查识别有效结果变化；冻结版本后供后续调查使用 |
| 采用结果 | 用户选择某个已保存结果作为当前判断 | E63预览→E21采用→E64历史/E03当前判断 | 新鲜度及未完工作确认保持；采用不停止任务或关闭Case |
| 结案/重开 | 用户结束业务处理，或恢复处理 | E44条件→E46关闭/E47重开；事件沿E52/E53 | 真正仍运行的Case阻止关闭；已结束unknown不占槽；重开不直接执行或续期 |

查询接口不得启动模型。公开接口不接受Redis键、并发N、工具调用计划、C阶段领取/结束或任意数据库原件，模型输入由调查核心按环节生成。独立HTTP通过用例端口调用核心；核心不反向依赖HTTP包，不强制内部调用走HTTP。

## 3. 已有接口可直接承接的部分

路径统一省略 `/api/v1/socai2`。这是现有确定合同及目标复用边界，调度接线尚未实现。

| 功能及入口 | 输入 | 输出与结果 | 对新调度的要求 |
| --- | --- | --- | --- |
| Case详情 `GET /cases/{case_id}`、历史 `GET /cases/{case_id}/history`（E03/E10） | Case ID；历史limit/cursor | 当前成员/判断；每轮Run及Result摘要 | 排队请求未必已有Run，不把Case历史当请求队列 |
| Case执行 `GET /cases/{case_id}/runs/{run_id}`（E12） | Case和Run ID | 执行状态、result_ids、步骤、用量、工件和数量/截断标志 | 只代表该Run；请求自动重试需另有关联指向新Run |
| Case结果 `GET /cases/{case_id}/results/{result_id}`（E14） | Case和Result ID | 原结论、发现、未解决问题、建议、实际来源Run、交付及比较对象 | 未解决问题作为结论展示；不新增问题管理流程 |
| 原件（E15/E16/E18、E31–E35） | 主体、Run（适用时）、工件/材料ID | 完整已保存正文、来源、可用性、size/hash | 阶段一统一读取版本；不把初答/补答/合并当一次原答 |
| A/I目录与单次记录（E22–E25） | 告警/事件ID及可选Run ID | 当前指针、新鲜度、业务结果、各次Run、说明/部分正文 | 排队/自动重试仍从请求读取；分析结果由现有GET承接 |
| 创建/修改人工任务（E38/E40） | operation_key、Case范围版本；任务行版本；正文、状态、result_scope、source_refs | TaskMutation和实际修订ID；完成必须有结果及范围 | 有效正文/范围/依据变化进入后续检查；负责人/期限等变化不触发模型 |
| 告警人工判定（E48/E49） | 既有版本及operation_key、判定/理由；单条或批量 | 每条保存结果及失败 | 有效反馈先进入相关I检查，I业务更新再驱动其活跃Case；其他Case在下次调查读取，保留人工陈述角色，不直接绕过I自动触发Case |
| 采用（E63/E21/E64） | 预览；提交operation_key、expected_review_token、reason，必要时确认未完工作 | 新判断身份/版本；旧判断与采用历史保留 | 增加unfinished_analysis_tasks覆盖尚无Run的分析任务；采用不关闭Case、不取消人工任务或分析任务 |
| 评论（E58/E59） | 普通评论正文 | 已保存评论及目录 | 不自动当作调查方向或核实结果 |
| 附件（E60–E62） | 业务后端file_id、文件名、类型、大小等 | 文件关联元数据 | 文件由业务后端保存；登记附件不代表调查已读取其内容，不自动作为模型证据 |

结果身份必须分开：Case `result_ids`指向 `results.id`；A分诊结果属于 `alert_assessments`，I诊断属于 `incident_diagnoses`，不能都拼到Case结果路径。业务后端沿相应主体/Run的返回链接查，不自行猜测ID类型。

阶段一侧另核实：现有Run/trace目录上限为1000步骤、200工件，有truncated标志但该目录没有分页；已知ID的单个原件可完整读取，外部blob仍可能未加载。不能把大原件读取通过说成目录均可完整枚举。按产品R3/R4要求，超过上限仍须能发现并读取已保存记录，登记为待提供；完整步骤/工件分页与单步定位按第8.7节目标合同落实，不因启动流程没有它而取消需求。

内部执行的硬约束见[现有执行代码核对](execution-code-review-20261114.md)：baseline必须先pending再claim，可封装为一次内部领取事务；A/I由begin直接创建Run，不能预建后又原样execute。当前unknown时间约束、唯一活动索引、领取及结案检查必须随本地执行状态方案统一，不由HTTP简单改状态值绕过。该内部增量设计由规划侧维护，保留历史unknown及V1原件。

## 4. 已定稿的持久化归属与暂缓范围

| 记录 | 已确定的职责 | 对应HTTP |
| --- | --- | --- |
| socai2.analysis_tasks（目标新增） | 受理身份、主体、意图、operation_key及保存回执、业务状态、重试安排；不同请求保留独立task_id，相同key同内容重放原请求 | E01首轮回执、再次调查/事件诊断的202回执、任务列表/详情 |
| socai2.analysis_attempts（目标新增） | 每次实际尝试、attempt_no、Run关联、失败原因、实际本地开始/结束；保留各次失败 | 任务详情attempts、latest_run_id、结果链接；结案依据实际活动判断 |
| socai2.analysis_subject_state（目标新增） | 主体最近实际完成、自动检查期限/下一检查等时间依据 | 任务列表附带的主体更新摘要，不新增独立更新状态GET |
| runs/results及原件、人工任务等既有业务表 | 冻结实际输入、业务结果及原答，保持原归属；人工tasks与分析任务分开 | 复用第3节GET和人工操作；不建重复结果表 |

上述是目标设计，不表示表已经创建。内部DDL、唯一约束及领取/结束的接线由本change主设计统一；必须先定清并验证受影响持久化，再实施其依赖接口，不以临时表或空接口绕过。

| 新增合同或非本期范围 | 未定内容/原因 | 继续可用的相关能力 |
| --- | --- | --- |
| 自选调查时间窗 | 与整案实际材料冻结、自动更新比较的统一规则未定；新提交不接受window_start/window_end | 整案check/rerun；程序固定上一轮实际完整调查为比较对象，不接受comparison_result_id覆盖 |
| 人工定向分析及手动后续综合 | 业务流程已确认，按第8节细化输入/结果/引用合同，不能继续标接续规则待讨论；不设永久方向，不无条件完整重跑 | 原AI对话继续暂停；用户主动发起的一次定向分析按新确认范围提供，不据此恢复整套聊天功能 |
| 同一告警原始材料更新（RV11） | 负责人明确撤回同ID版本提交及据此重新分诊，本期不开发该入口 | 新告警首次自动分诊、有限故障重试、已有材料/历史读取保持；下游看告警范围、可用A结果和I诊断变化 |
| 附件正文进入调查 | 原125项只要求上传/下载和案件关联；模型读取正文未纳入当前页面供给要求，后续如明确新增再定合同 | E60–E62继续登记/读取文件引用，业务后端提供上传下载；不把元数据当已读证据 |

默认内部可信，不增加登录/权限设计。第7节的完整调查check/rerun与事件诊断提交只接受operation_key和mode；不接受Run ID、范围版本、比较结果、自选时间窗或内部调度参数，未知字段返回422，不静默忽略。Case建案及成员/人工管理仍保留各自明确的原业务字段与版本规则；定向问题、工具选择和手动综合来源按第8节另行明确，不能塞入mode并被静默丢弃。

## 5. 最终合同的保存/读取与直接验收要求

仅核本次功能闭环，不建设新旧版本或故障矩阵：

1. 建Case输入→Case/所选范围及首轮受理保存→后端可查询到同一首轮→实际执行冻结输入→Run/结果读回。重复提交不变成第二个首轮。
2. check无变化只留下真实检查结果、不造模型Run；有变化进入队列；rerun有明确的新请求。排队时到来的材料按实际领取时冻结，执行中输入不被回写。
3. 本请求的每次尝试及失败均可查；unknown本地收尾释放，下一任务可继续，原unknown不改成成功。自动重试默认一次/60秒由配置及实际记录反映。
4. 人工有效反馈保存→下一轮输入引用实际修订；管理字段/普通评论/附件元数据不能冒充证据或方向。
5. 结果保存、采用、结案分别验证；采用不结束任务。关闭后未开始请求不执行，重开不复活旧待办。
6. 同一目标版本的核心、API读取器、配置、数据库增量和Swagger统一；后端只依赖HTTP合同，不直连调查表或Redis。

## 6. 协作状态

规划聊天已明确采纳第7节并给出第4节持久化归属/暂缓清单；阶段一聊天补齐了真实执行与读取约束。确认依据保存在[协作记录](../../../docs/operations/evidence/http-impact-review-20261114-01/workflow-coordination.json)。本文由接口侧维护，主设计/规格/任务由规划侧统一；不改动其他聊天已验实现。

这轮完成目标接口讨论，不表示代码或数据库已实现，也不计入当前71个操作。E11 prepare→E13指定Run start不进入新目标外部流程，E36手动告警分诊退出目标对外API；统一发布前仍按已部署服务区分现状。AI对话继续暂缓。

## 7. 已确认的目标路径与字段

本节经规划侧确认，作为接口开发目标；不提供兼容别名。内部持久化增量未完成前不发布这些路由。

| 功能 | 目标路径 | 最小输入 | 成功结果 |
| --- | --- | --- | --- |
| 新建Case并提交首轮 | `POST /cases`（E01调整） | 原CaseCreate：operation_key、title、alert_ids/incident_ids及可选案件信息 | 201 CaseAllocationReceipt，含首Case及实际各案分配/首轮任务；不返回供用户再start的pending_run_id |
| Case检查/再次调查 | `POST /cases/{case_id}/investigations` | operation_key UUID、mode必填且为check/rerun | 202及分析任务回执；模型在后台执行 |
| 事件检查/诊断 | `POST /incidents/{incident_id}/diagnose`（E37调整） | operation_key UUID、mode必填且为check/rerun | 202及分析任务回执 |
| 分析任务详情 | `GET /{cases或incidents或alerts}/{id}/analysis-tasks/{task_id}` | 主体ID、分析任务ID | 对应主体的业务任务状态、实际执行及结果链接；无Run时为空 |
| 主体分析任务列表 | `GET /{cases或incidents或alerts}/{id}/analysis-tasks` | limit/cursor | 任务摘要和分页；刷新页面后可找回各次任务 |
| 自动更新资格 | 由上述列表的主体状态摘要承载，不另加GET | 主体ID | 最近实际完成时间、自动期限及下一检查时间、不可自动检查的业务原因；没有队列名/位置/键 |

E11 prepare、E13指定Run start和E36手动告警分诊不进入目标对外API；内部准备/领取方法仍由调查核心按需要保留。既有已部署接口在统一发布前保持现状，不在本轮删除代码。关联成员（E07–E09）只保存业务范围并供检查，不为此提前生成pending Run。

上表E01回执须补第8节的容量分配结果：一次选择超过100条时可能创建多个Case，各自有独立首轮task；成员追加也可能进入已续建Case。不得仍用单个case_id/scope_revision冒称覆盖全部分配。普通已有Case追加不直接重跑，但本次因容量新建的Case按已确认规则登记自己的首轮。

分析任务与人工核实任务严格区分：`analysis-tasks/{task_id}`是模型分析任务；现有`tasks/{task_id}`是用户创建的人工核实事项，不共用表或路由。

### 分析任务回执

| 字段 | 类型与含义 |
| --- | --- |
| task_id | UUID，本次对外分析任务身份；重放同operation_key保持；后端一直用它查询 |
| subject_type / subject_id | case或incident及其UUID；读取自动A任务时为alert |
| status | accepted表示已持久受理；不是模型完成或实际开始 |
| status_url | 对应主体下的分析任务详情路径 |

E01返回第8.3节CaseAllocationReceipt，各allocation含case_id、scope_revision及新案首轮任务回执。创建成功不保证立刻获得执行名额。幂等回执返回原受理身份；最新状态读GET，不通过重发POST获取进度。

### 任务详情与状态

| 内容 | 最小字段/解释 |
| --- | --- |
| 身份和意图 | task_id、subject_type、subject_id、kind、source、intent（initial/check/rerun/targeted/synthesis）；自动故障重试不另生对外task_id |
| 业务进度 | status为accepted/running/completed/failed/skipped；reason_code解释无变化、关闭前未开始、调用超时等不同原因 |
| 时间 | submitted_at；实际开始/结束时间未发生时为null，不用排队时间伪造开始时间 |
| 执行关联 | latest_run_id可空，attempts保留每次尝试的attempt_no、run_id、实际起止、失败原因及run_url；不把C3补答计成新队列尝试 |
| 结果关联 | 按结果种类提供实际ID及读取路径；无结果为空列表。Case Result、A assessment、I diagnosis不混用 |
| 自动重试 | next_retry_at与已用次数；未安排时为null/0（次数按实际记录）；时间是最早时间而非保证开始时间，不提供pending队列信息 |

accepted包含等待执行和已安排的内部重试；running只表示调查服务实际仍执行；completed只表示本轮流程正常结束，不代表结论确定、质量通过或已经采用。skipped必须区分no_changes与closed_before_start等原因。unknown原Run结果保留，本地已经收尾且不再重试的任务呈failed并说明原因，不再呈running。attempts的本地实际结束时间与Run的结果状态分别表达，不伪造未知模型结果已确定。

每次使用不同operation_key提交的请求保留各自task_id及进度，同主体忙时等待；相同operation_key同内容重放仍返回原请求。负责人2026-11-15确认移除不同请求之间的归并，已按审计F4完成本机实现及独立测试/HTTP读回；历史归并证据不作为新规则的证明。HTTP不暴露队列操作，旧记录按实际保存关系读取，不改写历史。

### 业务错误

- 422：缺字段、无效mode、不合法UUID或额外参数；本期不接受的window_start/window_end/comparison_result_id等不得静默接受。
- 404：主体、任务或结果不存在，或任务不属于该主体。
- 409：相同operation_key换了主体/意图/内容；对象已关闭需先重开；Case范围为空等无法受理的业务条件。运行中再次提交按统一队列规则受理等待，不因为没有立即名额就报执行失败。
- 服务暂不可用：未受理成功不能给虚假task_id；已经持久受理但后续调度失败，则用同task_id查实际失败原因。暂不设计通用自动恢复平台。
- POST连接断开：后端重放相同operation_key恢复原受理身份，不自动换key制造另一任务；无需理解内部队列。

## 8. 后续已确认更新对HTTP的要求

本节为核心与HTTP侧统一的目标合同，覆盖Q1–Q6、产品P3/P7–P10和R1/R3/R4。所有路径省略`/api/v1/socai2`，尚未上线；命名在本文落定，不再交由负责人决定内部命名。现有71个操作及正式Swagger在实现/验证/统一发布前保持原发布状态。

### 8.1 通用类型、任务身份和分页

- UUID身份均用标准UUID字符串；时间为带时区RFC3339，未发生为null；数量为非负整数，未知值不得写0。以下`url`均为带业务前缀的相对HTTP路径，由服务返回。
- `analysis_tasks.kind=case_investigation`共用同Case串行；意图为`initial/check/rerun/targeted/synthesis`。不同请求不相互归并，分别排队，执行前读取最新材料；普通检查无业务变化则skipped/no_changes且无新attempt/Run或模型调用。相同operation_key同内容仅重放原请求；`rerun/targeted/synthesis`不因普通输入摘要未变被跳过。移除ordinary initial/check跨task归并已随F4通过本机直接验证，尚未发布。
- `RunKind/ResultKind`新增`targeted`；综合仍为`baseline`，以`task.intent=synthesis`区分，不新增另一套`synthesis`结果枚举。原A/I类型和历史AI记录只读身份保留，普通对话仍暂停。
- `TaskReceipt={task_id,subject_type,subject_id,status:"accepted",status_url}`，提交成功202。详情沿第7节增加`kind,intent,source,request`；source使用`ingress/case_create/periodic/user/knowledge`真实来源，定向/综合为user。`request`仅回显下节的业务请求，不含内部摘要/队列。内部request_payload保存相同内容供执行、重放和追溯。
- 结果引用统一`ResultRef={result_type,id,source_run_id,kind,url}`；result_type为`case_result/alert_assessment/incident_diagnosis`，kind取该结果自己的实际类型，不将A/I ID送入Case结果路径。任务`results`包含实际产生的引用，无结果为[]。
- 新列表统一`Page<T>={items:T[],total,next_cursor,observed_at}`。limit目标默认50、单页最大100，均从显式profile读取；请求省略limit时使用该profile默认，超出该profile单页最大值422；cursor不透明、最长4096，绑定租户/父对象/过滤/排序；换条件重开第一页，非法或混用游标422。total是本次同条件全量，不是当前页数；到底next_cursor=null。只取limit不截断整份目录。
- 读侧每次有自己的数据库一致观察；不宣称跨HTTP请求永久快照。排序尾键均有真实ID，运行中新增内容刷新首/尾页继续读。关联列表另以relation_revision检测会改变分类/排序的关系变化，变化时409/cursor_stale，重新读取第一页；不保存通用快照表。

任务详情五种状态仍为accepted/running/completed/failed/skipped；原Run unknown本地收尾后任务failed，原Run保持unknown且退出N。定向成功或失败只改变自身记录，均不推进全案完成输入基线、不停止主体普通自动更新，也不刷新全案自动窗口。只有真实完成固定全案范围的baseline结果才可推进全案基线；synthesis局部交付或输入过期不冒称覆盖当前新增告警。

### 8.2 定向分析、工具选择和手动综合

| 方法/路径 | 请求DTO | 成功响应 |
| --- | --- | --- |
| `POST /cases/{case_id}/targeted-investigations` | `TargetedInvestigationRequest` | 202 TaskReceipt，intent=targeted |
| `GET /cases/{case_id}/investigation-tools` | case_id；无执行参数 | `InvestigationToolsView`，仅列现有能力，不实际查询工具 |
| `POST /cases/{case_id}/syntheses` | `SynthesisRequest` | 202 TaskReceipt，intent=synthesis |
| `GET /cases/{case_id}/analysis-tasks/{task_id}` | 复用第7节 | TaskDetail及results，定向/综合各自独立可查 |
| `GET /cases/{case_id}/runs/{run_id}`、`GET /cases/{case_id}/results/{result_id}` | 复用E12/E14 | 原详情加analysis_context；工件正文沿原GET |

`TargetedInvestigationRequest`字段：

| 字段 | 类型/规则 | 含义 |
| --- | --- | --- |
| operation_key | UUID，必填 | 同主体/意图/同正文重放返回同task；不同正文409 |
| question | string，必填，去两端空白后1–4000字符 | 用户本次问题/分析方向，不是Case永久方向 |
| alert_ids | UUID[]，可省略；提供时1–200且去重校验 | 明确选定当前Case成员；200是单次请求条数校验，不是Case容量 |
| object_refs | `{alert_id:UUID,object_id:UUID}[]`，可省略；提供时1–200、不可重复 | object_id必须是alert_objects.id且属于所列告警的可用原材料；不是画布节点ID或任意SQL对象 |
| tool_names | string[]，默认[]，不重复，最多4 | process_activity/network_connections/authentication_activity/product_host_details；非空限制本次可选工具，仍可只分析材料；空表示由程序在允许能力内决定是否查询 |

alert_ids和object_refs均省略才表示执行前当前Case范围；只选对象时范围为对象所属成员，同时给两者时对象必须属于显式alert_ids，不静默扩范围。显式范围保存请求身份，受理时及执行前都核归属/可用性；不把运行中新增成员塞进已固定输入。明确空数组不是“当前全案”，返回422；工具空数组是上述已定义默认。未知工具422；已支持但本案无法执行的工具保留未执行及原因，其余分析继续，不在工具GET承诺未来执行一定成功。

`InvestigationToolsView={case_id,scope_revision,items,observed_at}`；每项`{name,label,availability,reason_code}`，availability为available/unavailable/unknown；name严格为上述四种，reason_code为空或说明缺主机、缺可靠时间、来源未配置/不可判定。工具选择不扩能力、不允许任意SQL/工具参数/执行计划。GET不调用厂商服务或模型来探活。

`SynthesisRequest={operation_key:UUID,targeted_result_ids:UUID[]}`；结果列表1–200、不可重复、必须同Case且kind=targeted。不接收比较对象、客户端全案范围或前序Run。核心执行前选择适用完整前序并固定真实材料；用户可以在模型没有建议时发起综合，也不以没有新证据拒绝。前序/原件不可用时`prerequisite_unavailable`，不得静默改为完整重跑。

E12/E14增加`analysis_context`（未适用或历史未记录为null）：`{task_id,intent,requested_scope,resolved_scope,source_results,updates_full_baseline}`。requested_scope回显本次明确选择或current_case；resolved_scope保存实际成员/对象及scope_revision并引用输入工件；source_results为ResultRef[]，保留定向与完整前序的身份；updates_full_baseline为实际保存结果，不由前端计算。定向为false；综合只有真实完整固定范围且符合保存条件才true。定向`ResultView`复用conclusion、findings、questions、recommendations等，允许只给建议及限制，不强迫结论非空；原始输入/模型答复/复用引用全部可回查。targeted不可通过E21直接覆盖全案判断；synthesis沿原采用预览/提交规则，不自动替换用户采用。

示例：

```json
{"operation_key":"00000000-0000-4000-8000-000000000101","question":"核对这次登录是否异常","alert_ids":["00000000-0000-4000-8000-000000000201"],"tool_names":["authentication_activity"]}
```

```json
{"task_id":"00000000-0000-4000-8000-000000000301","subject_type":"case","subject_id":"00000000-0000-4000-8000-000000000401","status":"accepted","status_url":"/api/v1/socai2/cases/00000000-0000-4000-8000-000000000401/analysis-tasks/00000000-0000-4000-8000-000000000301"}
```

示例身份仅示意，非联调数据。新的任务不重开旧Run；全案综合与定向task分别保留，后台共享Case串行及总N。

### 8.3 多Case分配回执

E01 `POST /cases`、E08 `POST /cases/{case_id}/associations`、E09 `POST /cases/{case_id}/members/move`保留业务请求字段（CaseCreate/AssociationRequest/MoveMembers）及版本校验；去掉创建/关联回执中的pending_run_id。显式ID数组原200传输校验不等于来源事件成员上限；选事件时读取完整成员后分配，不能只取I诊断选入的100条。

E01/E08返回`CaseAllocationReceipt`，E01成功201，E08成功200；E09成功200返回`CaseMoveReceipt={source,allocation,moved_alert_ids}`，source=`{case_id,scope_revision,removed_alert_ids,changed}`，allocation也是CaseAllocationReceipt。

| CaseAllocationReceipt字段 | 类型/含义 |
| --- | --- |
| operation_key | UUID，原操作 |
| requested_case_id | UUID或null；E01为null，E08为调用路径Case，E09为请求target_case_id |
| primary_case_id | UUID；E01新建首Case，其他为明确请求目标；不能替代实际接收者 |
| continuation_root_case_id / receiving_case_id | UUID；本次分配所属最初Case及操作结束后的接收Case |
| changed | bool，实际是否发生业务变化 |
| allocations | CaseAllocation[]，每个实际涉及的目标Case一次，按续建顺序；至少包括明确目标/接收者及已有归属 |
| incident_receivers | `{incident_id,active_case_id}`[]；本次显式关联/续建实际设置的事件接收目标，不伪造未改变事件 |
| excluded_alert_ids | UUID[]；本次来源集合中因同串既有排除而未分配的精确ID，不含已存在成员，空时为[] |

CaseAllocation=`{case_id,scope_revision,created,changed,previous_case_id,added_alert_ids,existing_alert_ids,linked_incident_ids,initial_task,case_url}`。previous_case_id可空；三个ID数组返回本次选择/分配的精确集合，不返回整个Case历史；initial_task为新案TaskReceipt或null。同串已有成员通过existing_alert_ids说明原归属，不复制进最新案；不同独立案可以共用告警。

11-15第5步细节确认：linked_incident_ids仅表示本次实际新增的显式关系；关系已存在而只改变接收目标时该数组为空，由incident_receivers表达实际切换。整事件选择尊重排除，excluded_alert_ids解释未分配成员；显式单告警重新添加按既定规则解除排除。E07允许空alert_ids，仅清空请求Case自己的成员并记排除，不创建新task、不清空续建串，回执保留当前接收者。

例：A有99条，追加5条，allocations分别返回A added=1、B created=true/added=4及B首轮task，receiving_case_id=B；再次重放原operation_key返回相同分配，不因后来已转C改写旧回执。source保留E09源案实际移出及版本，不能只返回最新接收案而丢源案变化。

E07 `PUT /cases/{case_id}/members`仍表示替换请求Case本身成员，不得清空整串；移除保留该Case范围变化/排除，新加入成员同样进入容量分配用例。目标回执为`CaseReplacementReceipt={source,allocation}`（source结构同上，allocation同上），已有请求Case中保留的成员不因replacement整体移到接收案。各入口都校验请求中实际提交的旧版本，解析出的其他接收案由事务锁保护；不要求前端猜新增Case的版本。全部分配/指针/新任务原子保存，冲突全拒，不能返回部分保存成功。

CaseView增加`continuation={root_case_id,previous_case_id,receiving_case_id}`；均为真实Case UUID，previous可空。独立新案root/receiving指向自己，非独立旧记录无该信息时为null。receiving_case_id始终沿root读取实际接收者，数据库仅root保存该指针。它只表达容量续建，不把共享事件的独立案串成前后案。仅追加既有Case不立即重跑，容量新建Case登记自己的首轮task。

### 8.4 关联Case与事件接收者

新增`GET /cases/{case_id}/related-cases?limit=50&cursor=...`，返回`RelatedCasePage=Page<RelatedCaseItem> + {case_id,relation_revision}`。完整分页在数据库范围内先排除本案并按Case ID归并，再排序；不在每页取完后才去重。

`RelatedCaseItem={case_id,title,handling_status,severity,relation_types,primary_relation,continuation,shared_incidents,case_url}`。severity可空；relation_types为`continuation/shared_incident`的非空去重数组，primary_relation命中continuation则优先它；continuation复用上一节结构，否则null。

`shared_incidents=[{incident_id,title,current_case_sources,related_case_sources}]`，两侧sources各为`explicit/member_alert`数组：explicit来自case_incidents，member_alert来自case_alerts→incident_alerts；同事件按ID去重，不把间接来源冒称显式跟随。共同事件列表按incident_id升序。关系来自真实身份，不做文字/模型相似度推荐。

列表排序固定：continuation组优先（Case created_at ASC、case_id ASC），其次仅shared_incident组（相同稳定排序）。两类都命中仍只返回一次且保留两种来源。cursor绑定relation_revision；关系改变导致候选集合/分组/顺序变化时409/cursor_stale，调用方刷新；标题等展示更新不凭空新增关系。无关联返回total=0/items=[]。

事件E29详情增加`case_receiving={active_case_id,can_receive_automatically,reason_code}`：ID可空；reason_code为空或no_target/closed/auto_window_expired。它只按接收目标存在、开放及7天资格判断，不是Run运行状态；不增加auto_enabled。同输入分析失败停止不禁止新告警加入形成新输入，automatic_attempts_stopped只用于分析任务/主体分析资格。E30 `GET /incidents/{incident_id}/records/cases`复用原完整分页/显式及共享成员标记，每项增加is_active_receiver，活动目标必须同时属于真实关联。告警E28/E30的原公共字段不改，不给告警新增active_case_id。

新建/明确关联整个事件后由本次实际接收Case承接；单条告警关联、普通check/rerun、GET和打开页面均不切换事件接收者。两级列表只导航，不改事件映射、不触发模型、不跨Case复制原件/采用判断。

### 8.5 事件选入范围与实际分析覆盖

E23/E25中事件StageEntry增加`input_selection`与`analysis_coverage`，告警StageEntry保持原合同；E29当前诊断入口沿同一事件结果引用读取，不在列表伪造一个全事件结论。

`IncidentInputSelection={policy:"recently_linked",limit,order:"linked_at_desc_alert_id_asc",captured_at,total_member_count,selected_count,omitted_count,selected_alert_ids,input_artifact_id}`。来自执行前同次观察；selected_count+omitted_count=total_member_count、selected_count等于ID数；默认limit=100。事件原表保留全部成员，Case创建/关联不使用这份有限选入集合替代事件全量。

`IncidentAnalysisCoverage={state,analyzed_count,unresolved_count,not_analyzed_count,covered_alert_ids,limitations}`；state=complete/partial/none/unknown，表示实际结论覆盖相对本轮捕获的**整个事件**；三种数量按选入集合互斥归类，未保存/不可确定时数量和covered_alert_ids为null且state=unknown，不补造0。analyzed_count表示已实际分析且有判断，unresolved_count表示已实际分析但结论待核，两者都属于已覆盖；covered_alert_ids是两组实际成员ID并集，长度等于两计数之和。已知三计数之和必须等于selected_count；omitted_count=0且not_analyzed_count=0才是全事件complete，有覆盖但不满足该条件为partial，覆盖为0为none，统计不可靠为unknown。未选入总量由input_selection.omitted_count单列，避免重复计数。

历史输入未记录选取或覆盖时相应对象为null并保留原件，不回填虚假统计。模型结果/引用及覆盖装配由核心计算，不让前端从100条倒推。100/260的输入完整正常交付可为delivery_state=complete，但analysis_coverage仍partial；执行、输入选择、覆盖、交付、质量和当前采用分别表达。

默认日志补查按相关告警真实时间前后各1小时；默认单次50条配置化，超限如实说明未取全。不另加最大跨度/裁剪/拆窗；沿现有查询超时，失败/缺时保留补查缺口与独立有效分析。实际输入容量超限任务failed/capacity_exceeded，不自动重试；原Run保留真实状态/已完成结果，不推进完整基线。

### 8.6 R1跨主体运行目录与同范围统计

新增`GET /analysis-runs`，参数为`subject_type=alert|incident|case`可选、`subject_id`可选（提供必须配type）、`run_kind`/`intent`/`state`可选、`time_from/time_to`可选（带时区、requested_at前闭后开）、limit/cursor。run_kind支持已存历史类型及新增targeted；intent取8.1枚举，历史无task的intent为null。按requested_at DESC、run_id DESC稳定排序，不枚举告警/事件/Case再拼凑。

`RunDirectoryPage=Page<RunDirectoryItem> + {statistics}`。每项字段：`run_id,subject_type,subject_id,subject_title,run_kind,intent,task_id,state,delivery_state,requested_at,started_at,ended_at,input_member_count,results,detail_url`。标题/时间/任务/未记录输入数量可空；results为ResultRef[]。A/I没有Case仍入目录；无结果失败、unknown及历史无analysis_task的真实Run保留，不能伪造Task。

`statistics={total_runs,by_state,by_delivery_state,without_related_case_count,related_case_count}`：前两分组按真实枚举计数，未出现计0；without_related_case_count为无真实关联Case的Run数，related_case_count为同范围实际关联Case去重数，不能用候选Case ID充数。Case Run取自身Case，A/I沿实际成员/事件关联计算。统计与本页过滤及数据库观察一致，不只数items。跨页实时状态变化按observed_at说明，换筛选清游标，不增加额外运营报表。

### 8.7 R3/R4完整步骤与工件目录

不增加三套主体别名，使用统一Run身份查询；先校验Run属于配置租户，再返回真实主体和原详情/正文地址。核心不依赖HTTP包。

| 方法/路径 | 参数 | 返回 |
| --- | --- | --- |
| `GET /analysis-runs/{run_id}/steps` | limit/cursor；kind可选为现有StepKind；`kind=tool`即查询目录 | `RunStepPage=Page<RunStepView> + {run_id,subject_type,subject_id}` |
| `GET /analysis-runs/{run_id}/steps/{step_id}` | run_id/step_id | RunStepView；不属于该Run返回404 |
| `GET /analysis-runs/{run_id}/artifacts` | limit/cursor；step_id可选 | `RunArtifactPage=Page<RunArtifactView> + {run_id,subject_type,subject_id}` |
| 原Case/A/I原件GET | 原路径不复制：Case `/cases/{id}/runs/{run_id}/artifacts/{artifact_id}`；A/I `/{alerts或incidents}/{id}/analysis/runs/{run_id}/artifacts/{artifact_id}` | 复用现有ArtifactContent/ContentView；调用方沿content_url打开 |

RunStepView固定公开字段：`id,run_id,seq,parent_step_id,retry_of_step_id,stage_code,kind,name,state,provider,implementation_version,question_id,started_at,ended_at,actual_args,returned_rows,error,usage,input_artifact_id,output_artifact_id,reused_artifact_id`；不存在/未记录的可空值保持null。模型正文和大型输出不塞目录，通过工件引用读；不返回tenant_id、幂等键或内部存储地址。步骤按seq ASC、id ASC；kind过滤不丢失parent_step_id，可用单步GET定位父项。 另返回`artifact_refs=[{role,artifact_id,run_id,subject_type,subject_id,content_url}]`，role为input/output/reused；沿实际工件和源Run派生，跨Run也返回真实源主体及原件地址，原三个ID字段保留。无Run的合法源工件run_id=null，使用其实际主体原件URL；实际参数/错误沿既有脱敏规则，不伪造引用或把跨Run原件加入本Run目录。

RunArtifactView：`id,run_id,step_id,kind,schema_version,mime_type,file_name,size_bytes,sha256,captured_at,material_state,content_url`；沿现有表字段命名，未记录file_name/mime_type/size_bytes/hash等可空。目录不承诺正文可用，真实availability由原件GET返回。按captured_at ASC、id ASC，包含已保存工件元数据，无正文/失败记录也不消失；不输出blob_ref。step_id过滤同时查工件直接step_id及该步骤input/output/reused_artifact_id，只在该Run所属工件内归并；引用其他Run的复用原件仍由对应真实源链接回查，不改归属。 captured_at沿真实工件记录时间，不另造created_at字段或改写为业务发生时间；event_time仍保留原含义。

**目录的total为过滤后真实总量，超过现有1000步骤/200工件仍能连续翻页；不新增整份目录总量上限。** limit的默认/最大值按8.1读取profile，仅限制一次响应。游标编码父Run/过滤/稳定排序位置；非法、别的Run或改过滤422，不把无效游标当第一页。空Run目录为items=[]/total=0，Run不存在404。已有E12/E32摘要可以继续有明确截断标志，同时提供新目录的steps_url/artifacts_url；历史正文/冻结材料路径保持原用途。新增目录和单步GET均不触发模型/工具、写业务表或直接调内部HTTP。

### 8.8 错误与自动期限的最终口径

新接口业务错误使用`{"detail":{"code":string,"message":string,"context":object}}`；FastAPI字段错误仍为422 detail数组。code至少固定下列值，HTTP错误与任务执行失败不同：

| 时点 | HTTP/状态 | code及处理 |
| --- | --- | --- |
| 请求字段/枚举/游标非法 | 422 | invalid_input/invalid_cursor；未知工具、重复ID、空显式范围、额外字段不静默接受 |
| 身份不存在或不属于该父对象 | 404 | case_not_found/analysis_task_not_found/run_not_found/step_not_found/result_not_found；合法但他案引用也不重定向 |
| operation_key重用不同内容 | 409 | operation_conflict，保留原任务/回执 |
| 关闭/空范围/版本或关联快照变化 | 409 | subject_closed/empty_scope/scope_conflict/cursor_stale；保留调用方输入，刷新后明确重提 |
| 已知结果类型不能用于综合或采用 | 409 | invalid_result_kind/result_not_adoptable；targeted不能直接覆盖全案 |
| 受理前依赖不可用 | 409 | prerequisite_unavailable；不能承诺已启动，也不偷偷完整重跑 |
| 未持久受理且服务不可用 | 503 | service_unavailable，无虚假task_id；若已持久受理仍返回原TaskReceipt供查询 |
| 受理后实际范围/前序失效 | HTTP GET 200，任务failed | invalid_input/prerequisite_unavailable；保留原request与attempt，未启动模型就不造Run |
| 实际容量不足/调用失败/未知收尾 | HTTP GET 200，任务failed | capacity_exceeded/call_timeout/execution_failed/executor_interrupted等；读原Run/结果，不能以GET成功当业务成功 |

任务reason_code沿核心固定集合，并含prerequisite_unavailable。无变化skipped/no_changes；关闭前未开始skipped/closed_before_start；重试安排accepted/retry_scheduled，停止重试failed/retry_stopped或retry_exhausted。不可重试unknown本地结束后的任务failed，原Run unknown不改。

Q5：不做旧对象迁入、识别/回填/激活，不新增auto_enabled或激活HTTP，也不在本轮清库。Q6：期限内正式受理的自动首次尝试跨7天仍执行该轮，仍核关闭、同主体/N、最新已有材料和无变化；它不准许超期新自动扩案/续建。跨期不得自动重试，已失败等待重试跨期也停止。正常完成刷新窗口，排队/失败不续期；不能把auto_window_expired作为取消已受理首次尝试的skipped原因。主体资格过期与已受理任务可继续执行可以同时成立，前端分别显示，不据资格关闭任务。

### 8.9 交付顺序和直接验证

本合同确认不代表实现。通用R3先作为独立只读步骤：三类真实Run→步骤/工件两页以上→单步定位/原内容URL→数据库数量/身份一致；覆盖1000/200旧上限，验证过滤游标/父Run不混用、空态/404/422和无业务写入。核心用例在新专用只读模块，HTTP只做参数/错误/序列化，不修改调查执行器或强制内部走HTTP。

本次R3/R4落点（任务2.7的局部，不提前勾整项）：

1. 新增专用核心只读用例，复用已有事务边界及runs/run_steps/artifacts，不迁移表、不导入执行器；HTTP适配器构造正文URL，通过独立端口接入三个GET。
2. 增加独立读取配置文件及profile选择，明确默认50/最大100。无配置或配置非法503；目录每页和总数来自同一只读快照，游标按Run、过滤及固定顺序验证。
3. 在本机隔离PG以新批次保存A/I/Case Run、1001步骤/201工件及跨Run引用；通过ASGI请求连续翻页、定位单步、读取真实正文URL，对照SQL身份/数量。另核空目录、错误父Run、过滤/游标错误、配置上限及读取前后无业务变更。
4. 必要检查仅本模块PG功能、受影响HTTP边界、OpenAPI三个新操作和strict；保存本批回执到docs/operations/evidence/run-records-20261114-01。旧E12/E32摘要新增目录链接随本步骤接线，原公开字段不改；原摘要有界、完整目录无总量截断。
5. 保存实际结果并更新交接中的本地实现状态；本步不发布服务/静态Swagger，不提交或推送，不把阶段一、任务2.7或整个change标完成。

随后R1统一目录/统计、任务读侧和定向/综合/分配等各按原任务依赖逐步验证；本轮不要求一次实现全部。普通H、告警管理、附件/资产等既有边界保持。Q1–Q6及查询跨度已确认，不保留陈旧用户待决项；P5自选完整调查时间窗及模型附件正文为本期外扩展。发布/推送仍按整个change收口及明确授权。

### 8.10 R3/R4本地实施回执

2026-11-14，[本批证据](../../../docs/operations/evidence/run-records-20261114-01/README.md)与[接口指南](../../../docs/integration/run-records-http.md)：第8.7节三个GET和E12/E32目录链接已实现，独立只读核心模块通过HTTP端口接入；原字段不变、不增加数据库迁移。原件按实际captured_at/id排序，第8.7节已纠正不存在的created_at字段。

本机隔离PG新批次66次ASGI请求通过：Case 1001步骤/201工件读全，A/I无Case Run可读，单步、父步骤和跨Run/无Run原件可定位；筛选/游标/空态/404/422/503及配置上下限验证通过。GET前后6类测试记录完整行摘要一致。另通过3项HTTP边界、2项可信接入检查及候选OpenAPI检查。早期测试环境及合成数据准备失败原件保留，未改失败为成功。

本步仅任务2.7局部完成；不勾2.7或整change，R1和task等按主规划继续。候选74操作，正式两端/Swagger仍71操作；未部署、未提交推送、无模型/工具调用。本地配置与两端发布清单片段已准备，统一发布后仍需实际版本/配置及TCP读回。

### 8.11 R1已有数据读取：本轮实施边界

负责人要求继续实现，并明确本聊天只负责后端接口；调查执行、调度、模型、业务表实现由调查侧负责。2026-11-14调查规划侧核实analysis_tasks/analysis_attempts/analysis_subject_state尚无实现/可用读取接口。R1完整接口须真实左关联同租户attempt.run_id→task_id/intent；不按trigger猜测，不把所有记录恒填null当成最终接口。

本步解决“无法从统一入口的数据层完整发现既有Run及其统计”的已定稿部分，仍属于原2.7：

1. 基于现有runs新增专用只读目录用例；subject_type/id、run_kind、state、requested_at前闭后开筛选，requested_at DESC/id DESC游标。复用显式读取profile页额度，不修改R3行为，不设全目录总量上限。
2. 统计先按完整筛选范围计算，分页不缩小统计：总数、所有Run状态/交付枚举计数、无真实Case关联的Run数、实际Case去重数。Case取自身；A沿case_alerts；I取case_incidents显式关联与incident_alerts→case_alerts共享成员的并集，关系为当前观察、不冒充执行时关系。
3. 页内批量读取真实A assessment、I diagnosis、Case result，保留失败/unknown/无结果Run。冻结输入数量只读run_members或已保存的A/I输入快照；未知为null，不能数主体当前成员。公开URL由HTTP适配层生成，核心不依赖HTTP。
4. 本步基础结果不伪填task_id/intent，公开完整DTO仍按8.6保持两字段及intent输入。待调查侧提供真实task/attempt可筛选读取后再接通完整HTTP路由；本步不挂载GET /analysis-runs、不发布临时删字段版本、不为缺表加动态兼容分支。
5. 直接验证使用本机隔离PG新UUID/受控日期的A/I/Case记录，核混合分页/相同时刻ID排序、时间和主体筛选、无结果失败/unknown、重复Case关联和多结果不放大计数、冻结数量与当前数量区别、空集/游标/参数错误、读取前后SQL内容一致。已有HTTP结构/依赖检查只验证本次公开DTO及适配，不冒称新HTTP调用已可用。不得建替身任务表或修改真实业务数据来绕过缺项。
6. 证据保存到docs/operations/evidence/run-directory-20261114-01；更新接口供给要求和交接，准确标明“R1基础读取本地完成，任务关联/intent筛选/完整HTTP接线待提供”。不勾整个2.7，不发布、推送或推进调查核心任务。


8.11本步结果：已有数据基础读取、公开查询/响应合同及URL适配已完成本地直接验证。证据见[run-directory-20261114-01](../../../docs/operations/evidence/run-directory-20261114-01/README.md)：新UUID的8个Run，筛选窗内7个、边界外1个；9次成功基础读取及参数/游标/未接intent验证、9次现有HTTP详情/结果GET，12类记录前后行内容摘要一致。无模型/工具调用，未新建任务表或改调查执行。task_id/intent真实关联及intent筛选仍依赖调查侧第1步；R1完整DTO要求显式字段，因此基础结果不能冒充完整响应。GET /analysis-runs未注册，候选仍74操作；正式服务/Swagger未变，未提交推送。

### 8.12 R1真实任务关联与完整HTTP接线

调查侧已提供迁移128、AnalysisTasks/AnalysisAttempts及真实用例，并在本机隔离库完成首轮验证（analysis-lifecycle-20261114-01/pg-02.json）。本步接续8.11，目标是后端可通过一个GET读取三类分析记录及真实任务意图；只实施R1，不实施任务详情接口、调度、模型、页面或数据库迁移。

1. 目录按同租户runs→attempts.run_id→tasks.id左关联。迁移128保证非空run_id唯一；历史无attempt的task_id/intent返回null，已受理但尚无Run的任务不造目录行。不按trigger推导意图，不增加缺表兼容分支。
2. intent和已有筛选共同作用于目录及完整范围统计，在同一只读快照内执行；分页不改变统计。保留8.11冻结输入数、实际结果引用及关系去重语义。
3. 在独立HTTP包新增GET /api/v1/socai2/analysis-runs，通过端口/适配器调用只读用例；采用既有内部可信上下文、显式读取配置和结构化错误。输出完整RunDirectoryPage，参数错误422、数据库或配置不可用503，合法空集200。
4. 直接验证：保留8.11有效用例，新增核心accept→start_attempt→创建真实合成Run/输入→bind_run的保存读取，核实任务关联/intent筛选、历史null及无Run任务不混入；通过ASGI实际路由读回、分页、结果URL和错误，核数据库前后摘要不变。仅在隔离PG创建新UUID批次，不调用模型，不复写旧测试。
5. 运行直接PG测试、受影响HTTP边界与可信接入检查、候选OpenAPI及strict校验；证据置于run-directory-http-20261114-01。成功后同步接口指南、功能清单及交接状态，标明本地完成、待统一发布；不勾整个2.7，不部署/重启/提交推送。


8.12本步结果：完整R1 GET已接通同租户真实任务关联、intent筛选和同范围统计，历史无关联返回null，无Run任务不产生目录项。证据见[run-directory-http-20261114-01](../../../docs/operations/evidence/run-directory-http-20261114-01/README.md)：新UUID共11个Run（8历史合成、3经实际任务用例绑定），3任务/3尝试；32次ASGI请求（1次503为依赖替身）、10次基础读取及15类记录前后摘要核对通过。首次目录未创建导致回执写出失败及第二次测试错误取submit.id的失败保留，新批次修正为task_id后通过。未复写旧数据或任务表。

5项HTTP边界/可信接入检查、目标Ruff、strict及候选OpenAPI通过，候选75操作、正式71操作。调查侧确认Case关闭字段只有活动语义description更新（不增/改类型），本地结束unknown不阻塞、准备中attempt无Run也阻塞；HTTP边界断言仅放行这三处已确认说明，其他旧字段继续严格核对。接口指南、125项功能映射和交接已对齐。依赖迁移128及配套ORM，发布片段已列前提；本步未部署/重启、未Git提交推送、未模型或工具调用，2.7及整个change保持未完。下一独立接口步骤为任务详情/列表读侧，待核心最终回执后按原规划推进。

### 8.13 三类主体的分析任务详情与列表HTTP

调查侧第1步最终pg-05已提供核心read_task/list_tasks及实际生命周期数据。按既有授权接第7节六个GET，目的是后端可查询“已受理但尚无Run”的任务、重试及失败原因，并追到真实分析记录/结果；不实现POST受理、自动生产者、Redis、执行器、页面或迁移。

1. 为alerts/incidents/cases分别注册列表和详情路由，通过专用端口/适配器调用AnalysisTaskService。沿同一目标版本，不兼容旧别名、不嵌内部HTTP。业务上下文沿内部可信配置，读取policy显式选择既有analysis-tasks.json。
2. TaskDetail返回第7节身份、来源/意图、状态/原因、实际时间、request、retry_count/next_retry_at、latest_run_id、attempts及results。request仅回显业务request_payload；不暴露task内部行、attempt ID、合并根ID、队列或输入摘要。归并原task_id保留，实际尝试由核心解析；waiting投影accepted，unknown原Run不改写。attempt加可空run_url，结果URL按真实类型生成。
3. 列表按submitted_at DESC/id DESC稳定分页，limit/cursor规则同8.1，返回完整total/observed_at和核心update_state资格摘要。资格不代表调度器已经运行，不改任务状态。主体不存在或任务不属于该主体404；参数/游标422；配置或读取依赖异常503。
4. 实施前发现核心results暂缺真实结果kind，已向核心提供方明确要求按8.1直接输出result_type/id/source_run_id/kind四字段；不在HTTP按Run意图猜结果类型，不挂不完整版本。核心方负责该读取供给及定向验证，接口方继续其他已定稿接线。
5. 本机隔离PG新UUID批次通过真实核心受理/尝试保存构造A/I/Case任务，验证accepted无Run、准备期running、skipped、延迟重试accepted、failed/unknown本地结束、completed及归并读取；实际HTTP分页、主体归属、参数错误及真实Run/结果URL核对。GET前后相关记录摘要应一致，禁止模型调用或改旧数据。复用核心生命周期已过证据，不重做整套调度/恢复测试。
6. 新证据存analysis-task-http-20261114-01，完成后同步接口逐字段指南、候选OpenAPI、交接及功能映射；检查直接PG、受影响HTTP边界/可信接入及strict。只收口本步，不勾整个2.7、不统一发布/重启/Git推送。


8.13本步结果：六个GET已实现并本地验收，核心results已按8.1补齐真实四字段，HTTP仅加URL；无旧字段兼容别名。TaskDetail补status_url供列表跳转，update_state为eligible/last_normal_completed_at/auto_expires_at/next_check_at/ineligible_reason，资格与实际调度分开展示。证据见[analysis-task-http-20261114-01](../../../docs/operations/evidence/analysis-task-http-20261114-01/README.md)：9任务/7尝试/5Run及三类结果，38次ASGI请求（25成功/8参数错误/4未找到/1实际缺配置503），14类记录前后摘要一致。首次测试合成结果漏created_at的约束失败保留，新UUID批次补齐后通过；未改旧记录。

5项HTTP边界/可信接入、目标Ruff、strict及81操作候选OpenAPI通过。逐字段/状态/请求响应/错误/配置指南、功能映射及发布片段已更新；正式71操作未变，未部署/重启/Git，也没有调用模型、Redis或取证工具。分析任务GET完成不代表异步POST/自动生产者/定向综合完成，2.7及change仍未完成。后续外部提交接口待调度侧对应受理和执行用例明确完成后再接，避免HTTP冒称已经启动。

### 8.14 本轮统一发布授权与执行条件

2026-11-14，负责人在本接口聊天明确授权：“在合适的时候可以推送一版到21及git 不要鉴权 文档要最新 接口要更新”。该授权适用于本轮统一接口交付，达到条件后直接执行，不重复询问。按已有Git目标同步V1.1、main及SpiritHub的add-server-submoudle分支server引用；使用已安装socai2-git-sync固定流程，只提交本批审阅过的内容，不夹带共享工作树其他修改。

发布条件沿根AGENTS及本change第11步：对应业务/接口完整流程验证、文档交接和未参与实现者结束审计完成后统一发布；单步读取通过不触发零散发布。当前R1/R3/R4及六个任务GET已本地验收，整个change及后续异步提交尚未完成，不能提前标完整交付。

发布目标以独立对外HTTP服务、配套必要核心/增量依赖及Swagger为一套版本；对外接口内部默认可信，无登录、Token或角色鉴权。两端环境/CPU架构/profile独立，不能将本机配置直接套到21。不由本聊天恢复自动消费者、增加模型执行或修改产品页面。

统一发布时以实际冻结源码重新生成OpenAPI、功能状态/参数/输入输出/错误说明、README和交接导航；按最终接口数核对，不能直接部署过期候选Swagger。发布后核对21实际版本、加载配置、无鉴权请求及保存结果读回，再保存回执并执行一次最终Git/父项目同步。当前81操作是本地候选，正式71操作保持，授权记录本身不代表已经部署或推送。


### 8.15 异步提交受理层：就绪核对与本步实施

负责人要求继续确认调度进展并接能接的异步提交接口，保持无鉴权。2026-11-14调查侧明确：第2步调度仍在实现，当前无队列业务handler或调度验收；I真实handler在原步骤4、Case在步骤6。稳定供给为AnalysisTaskService.submit：先保存PG任务，返回task_id/subject_type/subject_id/status=accepted；调度负责补投last_enqueued_at为空的持久任务，HTTP不操作Redis。故本步只能完成受理接线，不能挂载为已具备执行能力的公开接口。

本步解决已定合同的请求校验、持久受理及回执查询接线，仍属2.7，不新增任务树：

1. 新增公开请求AnalysisSubmitRequest（operation_key UUID、mode必填check/rerun，拒绝额外字段）和TaskReceipt（task_id/subject_type/subject_id/status=accepted/status_url）。I与Case使用同一业务输入，来源与记录人取可信服务配置，不接受客户端伪传身份或内部kind。
2. 独立HTTP端口/适配器只调用核心submit，固定kind与source=user；已有事务提交成功才返回回执，不提前创建Run。将核心operation_key_conflict/subject_scope_empty映射到目标operation_conflict/empty_scope；关闭409、缺主体404、参数422、读取/保存未确认503。重放同key同内容给原回执，最新进度走GET。
3. 两个目标POST写入独立路由模块，但不注册到正式main、不替换旧E37、不加入正式/81操作候选Swagger。只有核心相应handler实际可消费并验证闭环后再统一启用；本步不启动调度、Redis、模型、自动消费者或旧同步执行旁路。
4. 使用单独测试ASGI应用挂载目标POST与已有task GET，真实隔离PG/新UUID批次验证：两类成功受理→数据库任务保存→status_url读取、同key重放不多建、冲突409、关闭/空范围409、父对象404、请求枚举/UUID/额外字段422；任务无Run/attempt、无模型调用。已有人工tasks不混用。终态后重放仍返回原受理回执、GET返回真实终态。结果注明只验受理，不冒称后台执行已通。
5. 保存请求/响应及核心边界证据至analysis-submit-preparation-20261114-01，补目标字段/错误/激活依赖说明及未挂载的提交合同OpenAPI；实际main的路由/无鉴权检查和已有HTTP边界应保持通过。strict通过后实施，完成后同步交接/进度。正式服务和Git不在此步骤发布。


8.15本步结果：调查侧已明确当前没有可开放的I/Case异步执行入口；本轮仅完成已定合同的受理适配及未注册路由。证据见[analysis-submit-preparation-20261114-01](../../../docs/operations/evidence/analysis-submit-preparation-20261114-01/README.md)：26次独立测试应用请求通过，真实PG保存2任务/2登记、无attempt/Run；相同操作重放、终态重放、冲突/关闭/空范围/参数错误及status_url读回符合合同，6类既有数据摘要保持。5项HTTP边界/可信接入、目标Ruff、strict通过。结果仅证明受理层，不证明调度/后台执行；未调用Redis或模型。

目标请求/回执/错误和未注册合同OpenAPI已保存，README/交接/功能供给状态对齐。正式main不挂载Case新POST、不替换同步E37，候选仍81、正式71；后续等调查侧I步骤4/Case步骤6的真实handler、运行配置和闭环回执后激活。此次无业务表/调度/页面修改，无服务发布/重启或Git提交推送，统一发布授权仍按8.14执行。


8.15依赖进展（2026-11-15）：已读回调查侧[通用调度pg-redis-02](../../../docs/operations/evidence/analysis-dispatch-20261114-01/pg-redis-02.json)，15项全部通过，真实PG/专用Redis、可控执行器/时钟、真实模型0，deployed=false，运行期间源码未变。analysis_dispatch_runtime及示例profile存在，默认disabled；实际A/I/Case handler仍未注册。HTTP的submit/GET字段不变，无需新增pending或收尾补写记录。当前只更新指南/交接/README依赖状态，两个POST仍不注册，81候选/71正式保持，不将通用队列验收替代I步骤4/Case步骤6的实际业务闭环；未改程序或服务，未提交或推送Git。


同日依赖补验回执为[pg-redis-03](../../../docs/operations/evidence/analysis-dispatch-20261114-01/pg-redis-03.json)，16项通过，新增“已被显式rerun覆盖的等待重试跳过且保留原失败”。HTTP任务状态说明已明确：skipped可有既往失败attempt/Run，不能清空历史或当成从未尝试；retry_count保持、next_retry_at清空。复用该真实回执通过一次离线HTTP适配/DTO核对，见[合同回执](../../../docs/operations/evidence/analysis-task-http-20261114-01/skipped-retry-contract-20261115.json)，未重跑模型/数据库/HTTP或增改公开字段；主应用及未挂载POST边界保持。


通用调度最终依赖回执为[pg-redis-05](../../../docs/operations/evidence/analysis-dispatch-20261114-01/pg-redis-05.json)，17项全部通过，真实模型0、未部署、运行期间源码未变；新增验证覆盖“首次材料读取失败尚无摘要，恢复可读后按实际摘要判断”。04因专用Redis端口变化导致连接检查失败、未进入业务用例，保留失败原件，不作为通过依据。当前指南/交接已切换05/17；skipped重试DTO核对仍引用03对应原记录，无需重跑或覆盖。HTTP字段、无鉴权、两类POST未注册及统一发布条件均保持。

### 8.16 告警自动分诊查询联验与事件异步入口的推进顺序

2026-11-15负责人要求先与调查侧核对告警自动分诊查询，再接事件异步诊断，测试和文档同步、保持无鉴权。本轮仍是原任务2.7，先实施第3步的HTTP读回，不把A/I/Case执行器一起展开。

1. 调查侧负责正常入站保存与首轮任务同事务登记、A执行器/调度接线和新批验收；接口侧复用该批tenant/alert/task/run身份与既有查询，不新增告警字段或HTTP触发入口，不重复模型调用。只有通过正常入站及真实执行器的样本才作为自动业务联验依据；旧合成任务只能证明读取合同。
2. 核对告警详情的最新材料/分诊、分诊目录及指定Run、analysis-tasks列表/详情、统一Run目录、步骤及工件链接，验证task→attempt→Run→分诊来源一致。没有结果的任务/Run仍保留真实状态，不按HTTP成功推断模型判断有效。沿显式配置提供内部可信业务上下文，所有请求不带凭据。
3. 直接测试只GET调查侧已结束的新批数据，逐个跟随公开来源链接；在读取前后比较该批相关记录，证明查询不创建任务/Run、不改分诊或原件。运行必要HTTP边界/无鉴权检查与OpenSpec strict，保存实际请求/响应、SQL读回及源码摘要到alert-auto-http-20261115-01。保留原自动执行与模型质量边界，不做压力/恢复矩阵。
4. A核心接线通过且查询验证通过后，按已确认统一目标移除E36手动分诊对外入口并更新候选OpenAPI、说明及受影响直接测试；保留内部执行器供调度使用。正式服务仍在统一发布时切换，不另设兼容版本。
5. 本步通过后再开始I入口：先取得第4步真实I handler、配置及提交→执行→诊断保存证据，再将E37从同步执行切为既定202任务回执。用实际提交/任务/Run/结果完成一次对应联验，并补幂等及直接错误验证。Case新POST仍等自己的核心依赖，不因I就绪一起开放。
6. 当前开始时A仍在接线、I handler尚未提供。依赖未就绪时记录实际未验范围，不挂仅能保存任务但无法执行的异步接口。每一步分别回报结果，整个change通过交接和独审后按8.14统一发布/推送。

8.16本步结果：调查侧正常入站/真实A执行器受控模型批pg-redis-05已通过；HTTP侧复用其已结束样本完成28次无凭据GET，任务/尝试/Run/分诊和保存材料同源，十类记录摘要前后不变。随后复用调查侧real-01的一次真实模型样本，28次同源读取通过；针对另1份无Run的入站原件补核告警级目录/正文，最终30次GET通过，5步骤/13份Run工件及1份入站原件全部可读。证据见[alert-auto-http-20261115-01](../../../docs/operations/evidence/alert-auto-http-20261115-01/README.md)。首轮沙箱拒绝本机PG连接的失败保留，0次HTTP/业务写入；后续只读复验不创建新数据或调用模型。

E36外部手动告警入口及外部ExecutionBackend的A执行分支已移除，内部A执行器保留；9项直接HTTP边界/内部可信/独立应用检查、Ruff及strict通过，原告警公共字段不变。候选OpenAPI为80操作且无security，正式两端/静态Swagger仍71操作。原实时模型答复正文不可用，质量NOT_PASSED保留，不把completed/HTTP成功追认质量。指南、功能供给要求、README/交接及HTTP进度已同步。

下一依赖为调查侧原第4步真实I执行器及配置：本步明确未提供，不提前把E37切为202；Case新POST也未挂载。2.7及整个change不勾完成，未部署、重启、提交或推送，继续按8.14统一交付。

### 8.17 第4步事件异步提交与覆盖读取：接口实施安排

2026-11-15调查侧已开始第4步设计及核心实施；负责人已要求在告警查询核对后接事件异步诊断，保持无鉴权、同步测试和文档。本阶段业务效果是：后端显式提交检查/重跑后立即取得真实任务身份，通过GET读进度、诊断结果及本轮选入/实际覆盖范围；GET不触发分析，不把事件全量成员当成全部已分析。

本步范围仅I的对外提交及读取，复用第7/8.5节定稿合同。不做Case自动执行、Case接收关系、知识后台任务、页面、模型质量专项或新旧同步兼容；无部署/Git。核心models、stage_reader/读取合同、分析受理/调度/执行器由调查侧维护，接口侧只改独立HTTP及交接。

1. **先核供给并独立准备路由。** 既有AnalysisTaskService.submit持久受理、task GET和R1保持；将事件提交和Case草稿拆成可分别注册的路由，避免启用I时意外开放Case。实际I handler、可消费profile及正常入站/执行保存样本尚未提供时，独立main继续原同步E37，不提前暴露只能受理的202。
2. **事件读取单独建模。** E23列表的current/entries和E25详情增加可空input_selection/analysis_coverage。核心按该Run冻结输入和真实输出提供第8.5节字段，历史未记录返回null；不得在HTTP从当前成员重新计算。使用事件专用Entry/Page，保留告警E22/E24的StageEntry/Page字段、类型和空值口径；E29沿已有analysis_url和结果指针读取，不提前加Case接收关系。R1/任务results保持真实来源链接，不复制覆盖摘要。
3. **供给就绪后一次切换E37。** 请求必填operation_key UUID、mode=check/rerun，额外字段/查询参数422；成功202回原task_id/status_url。旧同步E37路由和对外同步I执行适配退出该路径，不提供参数兼容分支，也不影响内部执行器。Case新POST继续不挂载，E36保持移除；80个操作中的E37替换合同，不增加操作数。内部可信身份来自显式配置，HTTP不调用Redis/模型、不创建Run。
4. **直接联验。** 复用既有26次受理验证及A读取有效证据，补本次真实I handler配合下的HTTP提交→数据库任务→调度执行→Run/诊断→GET同源读取；核同key原回执、无变化check不产生Run、显式rerun独立任务/Run。覆盖读取用核心已生成的超过上限/未分析/待核样本，核选入ID及总数、互斥计数、全事件partial与delivery区别；历史null、失败/unknown保留原状态。只补受影响请求/结果，不重做通用调度或质量采样。
5. **验证与完成边界。** 使用独立新批或调查侧明确交接的已结束样本，记录实际请求、状态URL、任务/Run/结果/原件身份及SQL读回；纯GET前后摘要不变。HTTP受理可以新增任务，但不冒称自己完成执行；调度由调查侧实际运行。相关路由/无鉴权/告警Schema不变及strict检查通过后，保存incident-async-http-20261115-01证据，更新候选OpenAPI、输入输出/错误指南、功能供给与根交接。每步通过才进入依赖步骤，2.7/change和发布任务仍按完整范围收口，不提前勾选。

双方接线约定已确认：调查侧在`stage_read_contracts.py`新增`IncidentStageEntry/IncidentStagePage`并由`stage_reader.py`事件分支提供，告警共享原类型不变；A/I共用现有dispatcher/runtime，核心提供明确的A/I factory配置。接口侧待类型实际落地后经`investigation_http/contracts.py`导出，E23/E25使用事件专用response_model；不在核心类型尚不存在时加入会破坏主应用导入的占位代码。事件/Case提交路由已分别装配，原受理请求/响应合同保持、两个目标POST仍未激活。实现供给与成功样本未到前，只记录准备完成，不把DTO声明当成业务读取验收。

读取接线准备结果：核心事件子类落地后，HTTP已导出4个专用类型并仅替换E23/E25的response_model。11项直接HTTP序列化/既有边界/可信接入/独立应用检查通过，事件新对象在current/entries/详情中保留，历史缺失为null，告警JSON及Schema不增加事件字段。测试使用显式读取替身、0次PG/模型请求；真实范围/覆盖的保存读回仍待核心样本，不记完成。首次Schema断言误以为必有default:null导致失败，原两次失败保留，修正断言且核实际HTTP空值后通过。详见[事件HTTP准备回执](../../../docs/operations/evidence/incident-async-http-20261115-01/README.md)和[逐字段指南](../../../docs/integration/incident-analysis-http.md)。候选仍80操作，E37同步200、Case新POST未挂，未部署或推送。

8.17最终本步结果（前段准备状态保留追溯）：调查侧交付实际A/I执行器及可消费配置后，事件E37已切为202，仅挂incident_router；对外同步执行路由/适配/请求体退出，Case新POST保持未挂。实际隔离PG/专用Redis/受控模型完成check无变化→skipped且无Run、rerun→新Run及诊断保存，终态同key返回原回执，HTTP不操作队列/模型。103次HTTP请求（91 GET、12 POST）通过，含260成员选100/漏160、100待核、容量失败、unknown、跨期首试失败及已结束真实模型批只读；同Run来源与12类记录只读摘要核对通过。12项直接HTTP/边界测试、目标Ruff、strict通过；告警共享合同不变、无鉴权。真实模型正文质量NOT_PASSED保留，本HTTP批新增真实模型调用为0。

最终[80操作候选OpenAPI](../../../docs/operations/evidence/incident-async-http-20261115-01/candidate-openapi.json)、[汇总及原始回执](../../../docs/operations/evidence/incident-async-http-20261115-01/README.md)、接口指南/功能供给清单及HTTP发布依赖同步。核心旧样本任务/Run配对错误和测试UTC/描述断言失败均保留，修正来源或测试后通过，未改写旧业务记录。本步本地完成不等于整个2.7/change完成；Case后续、统一独审/发布保留，正式本地/21及71操作Swagger未变，未提交推送。

### 8.18 第5步Case成员分配与受理：HTTP配合安排

2026-11-15，负责人授权调查侧继续第5步，双方共同完成设计、实现及HTTP直接联验，暂不部署。业务效果为：创建/替换/关联/移入后，后端明确知道告警实际分到哪些Case、每案的范围版本和新案首轮任务；读取续建关系、两级关联Case及事件后续告警的实际接收目标。沿第8.3/8.4节已确认规则实施，不再新增业务待决项。

本步只受理新案首轮任务，不执行Case调查；Case investigations POST继续不挂载。E11/E13外部旧执行入口的统一退役留实际Case执行切换阶段，不增加双模式兼容。不修改A交接字段、模型、普通AI对话或产品页面，不启动调度消费，不部署/推送。

**双方分工与供给：** 调查侧负责Case增量存储/迁移、事务分配、排除与接收目标、核心DTO/读写服务、配置及核心直接测试；HTTP侧只改investigation_http的公开DTO、端口/适配、路由、错误和交接。核心业务模块不导入HTTP包。

| 接口落点 | 核心供给/公开结果 | 本步HTTP操作结果 |
| --- | --- | --- |
| E01 POST /cases | 保留CaseService.create_case签名，公开CaseAllocationReceipt | 成功201；新案及分配/版本持久保存，新案initial_task为真实accepted回执，无pending_run_id |
| E08 POST /cases/{case_id}/associations | 保留associate，公开CaseAllocationReceipt | 成功200；按实际接收案分配并返回全部本次涉及案，不假设路径Case接收所有新增 |
| E07 PUT /cases/{case_id}/members | 保留change_members，公开CaseReplacementReceipt | 成功200；source说明请求案实际移除/版本，allocation说明新增实际分配，保留成员不整体搬移 |
| E09 POST /cases/{case_id}/members/move | 保留move_members，公开CaseMoveReceipt | 成功200；源案变化和目标实际分配同时返回，所有保存/任务受理原子完成 |
| Case详情及所有既有CaseView使用处 | CaseView.continuation，由核心沿root读取实际receiving | 返回真实root/previous/receiving；历史未记录按已定null规则，不由HTTP猜补 |
| GET /cases/{case_id}/related-cases | read_related_cases(tenant_id,case_id,limit=None,cursor=None) | 返回case_id/relation_revision/items/total/next_cursor/observed_at；续建优先、共享事件其次、同案去重；读操作不切接收目标 |
| E29事件详情 | 事件专用SubjectView子类及case_receiving | 真实目标、自动接收资格和原因；无目标为ID=null/false/no_target，不将运行状态当资格 |
| E30事件records/cases | 原RecordPage事件cases行增加is_active_receiver | 保留完整关联及原分页，只标真实接收者；告警cases行不增加此字段 |

核心DTO集中在case_allocation_contracts.py，initial_task提供task_id/subject_type/subject_id/status，分配及关联行提供真实Case身份；HTTP仅补status_url和case_url。共享CaseView的continuation从核心合同导出。E29使用事件专用response_model，避免新增字段被共享模型裁掉；不改共享告警SubjectView/SubjectPage。E30沿原通用路径及dict行返回，在Swagger字段说明中明确事件cases专属字段，不为了字段说明复制一条业务路由。

字段细节已与核心确认：linked_incident_ids只含新增显式关联，既有关系的接收目标切换用incident_receivers；公开分配回执同步核心新增excluded_alert_ids，说明因同串排除未分配的来源成员；E07空数组为合法清空本案，不按创建空范围拒绝。以上为既定行为的结果表达，未新增业务流程。

SOCAI2_CASE_ALLOCATION_CONFIG_FILE显式配置case.max_alerts、source_page_size、default_limit/max_limit，任务受理沿既有AnalysisTaskPolicy文件。默认容量100和关联分页默认50均由配置供给；HTTP不自建另一套参数默认，也不静默回落到旧数据库。无配置/依赖不能保存时返回503，不返回伪任务。其余错误沿8.8：参数422、对象不存在404、操作/范围冲突或关闭409、关联游标失效409/cursor_stale；具体核心错误名交接后仅在本步HTTP适配映射，不全局改旧接口错误。

**实施顺序及直接验收：**

1. 先完成本节及核心第5步设计，strict通过；取得实际DTO、方法、显式配置、增量迁移、核心错误映射和可读样本后再接线，不先导入未落地类或开放假返回接口。
2. 先接四个写接口与URL装配，用新隔离批次验证99+5→100/4、新案独立initial_task、受理后无attempt/Run；整事件成员来自完整集合（260成员不能截成I的100），每条新增/已有归属及版本可读。测试原key重放原分配、请求内容/版本冲突无部分保存；E07保留/移除/新增及E09源/目标同时核对，复用核心有效证据，不另建通用事务或恢复测试框架。
3. 写入通过后接Case continuation、两级关联与事件接收查询，核两类同时命中只返回一次但保留依据、真实分页/游标变化、无关联空集及关闭/过期接收原因。沿已保存核心样本核字段来源与只读前后记录保持，不在HTTP计算容量、资格或关联关系。
4. 同步公开输入输出/错误、功能供给清单、Swagger候选和发布片段；本步预计新增一个related-cases GET，候选80→81操作，四个写操作替换合同。直接HTTP/无鉴权/边界检查必须保持告警合同及内部服务依赖方向；Case新异步POST继续404。正式两端服务和Swagger不随本步更新。
5. 结果记在本步HTTP回执并交调查侧统一更新tasks/PROGRESS。只在保存及读取取得真实证据后记本步本地完成；新案自动执行、周期更新、定向/综合及整个change结束审计/统一发布保留各自后续步骤。

8.18本步最终结果：核心129/真实分配用例交接后，四个写入口及相关查询已完成本地验收。35次HTTP验证创建99+5分配、替换/移动/空替换、历史幂等及冲突、完整263成员事件与排除回执；29次验证两级关系完整分页/真实来源/游标变化、事件接收资格及A字段保持，其中1次新建用于实际游标失效；7次定向核原案1→2纯新增时source.changed=true，以及Case管理回执/详情continuation一致。另1次只读GET确认告警E30关联事件不透出内部active_case_id或事件详情专用case_receiving，保留原业务及关联字段。72次共使用真实隔离PG和ASGI路由，无凭据；只读阶段13类记录摘要保持。23项直接HTTP/边界检查、目标Ruff和strict通过。第一次离线夹具修改冻结DTO失败保留，改model_copy后通过；核心相应不可变DTO赋值由调查侧修复并完成真实PG验证，HTTP不原地改核心回执。

Case详情/列表/管理及管理操作回执沿root读真实接收者；related-cases仅同串项提供continuation，共享事件独立串为null，仍保留真实关系依据。全部新案首轮任务只accepted，无attempt/Run，Case investigations仍404。实际执行第6步、周期跟随第7步，本步无模型或Redis调用。最终[回执/示例](../../../docs/operations/evidence/case-allocation-http-20261115-01/README.md)、[81操作候选OpenAPI](../../../docs/operations/evidence/case-allocation-http-20261115-01/candidate-openapi.json)、[逐字段指南](../../../docs/integration/case-allocation-http.md)及[HTTP发布依赖](../../../deploy/http-service/case-allocation-release-fragment.json)已同步；正式两端/71操作Swagger未变，未部署/提交推送，不勾整个2.7/change完成。

### 8.19 第6步Case首轮执行：HTTP配合与切换安排

2026-11-15，本节先明确第6步的HTTP范围及直接验收。调查侧负责Case执行器、执行前材料和配置冻结、C1–C6接线及核心验证；HTTP侧负责公开入口边界、真实任务/Run/结果读取联验与交接。调查侧已确认并提供核心执行器；本步[HTTP闭环回执](../../../docs/operations/evidence/case-initial-http-20261115-01/README.md)已通过39次请求及6项直接检查，候选已切换为79操作、无鉴权。真实模型/21发布及第7步仍未完成。

**业务效果与范围：** 业务后端调用E01建案，沿各案initial_task.status_url查询；调度实际执行后，可从任务中的attempts.run_url、results[].url查看同一Case/Run的执行和结论，再进入完整步骤/工件及原件。创建回执仍表示受理，HTTP不等待模型、不消费队列、不自己创建Run或猜测结果。续建产生的每个新案沿自己的真实任务读取。E01/E07/E08/E09第5步分配合同、告警字段及事件异步接口保持。

本步只验证首轮initial。Case手动check/rerun及其无变化跳过、完成输入基线和上一轮比较属于第7步；`POST /cases/{case_id}/investigations`本步继续不挂载。8.15中“Case第6步handler就绪后激活”的早期安排在此细化：initial执行器可用不足以证明check/rerun已交付，须第7步实际行为通过后再开放。负责人随后将第8–10步人工定向、手动综合及知识后台异步维护明确后置，保留设计、未实现状态和未开放的入口；本期后续主流程联验覆盖第1–7步，不以这些后置项为前置。配套六组全功能测试不在本步实施。第11步最终验证须结合测试对话已有[完整调查测试方案](full-flow-test-plan-20261115.md)及[模块/HTTP供给清单](test-interface-readiness-20261115.md)，按本期第1–7步实际就绪能力选取对应用例，复用本步证据，不另建平行测试方案。届时沿方案核独立HTTP实际TCP提交/读取及持久数据；本地ASGI结果不能冒充第11步最终验证。第8–10步仍后置，当前安排不代表已开展最终验证、部署或模型调用。

**对外入口的统一切换：** 第6步真实首轮执行和读取验证通过后，移除候选外部E11 `POST /cases/{case_id}/baseline/prepare`、E13 `POST /cases/{case_id}/runs/{run_id}/start`及对应端口方法/不再使用的HTTP合同导出。它们不在候选Swagger出现，也不保留同步兼容路由；核心内部准备和执行能力继续由调度调用。本步已删除两项，实际候选81→79操作；第7步挂载investigations后预计80，以当时实际OpenAPI核对为准。21当前实际64操作、静态Swagger71，本机旧服务仍在运行、未切候选，本步不部署。

| 功能和读取入口 | 调查侧须提供的真实保存内容 | HTTP核对结果 |
| --- | --- | --- |
| E01建案分配回执、Case分析任务列表/详情 | 新案独立initial任务、真实attempt/Run关联、状态及结束原因 | 受理时无假Run；执行后原task_id仍能查询，链接属于本案；failed/unknown保留真实含义 |
| GET /analysis-runs，按subject_type=case及subject_id筛选 | 该批Run与task_id/intent=initial、实际输入范围和结果关联 | 目录、统计和任务读回对应同一Run；未产生Run的任务不伪装成执行记录 |
| E12 GET /cases/{case_id}/runs/{run_id}，E14结果详情 | 执行前保存的范围/配置、执行及交付状态、真实Result/引用 | 入队后准备前的新材料能在冻结输入中找到；运行中到达材料不改变本Run；结果URL与SQL来源一致 |
| Run步骤/工件完整目录、单步/原件GET | 现有C1–C6保存的输入、工具回执、模型原答、校验及有效局部结果 | 可按实际保存ID定位并读取；缺时、查询失败、截断或容量失败仍能查到对应回执及已保存部分，不伪造成功正文 |

默认补查前后各1小时、日志单次50条及容量限制由核心显式profile负责。HTTP不新增时间窗/日志条数/模型参数，也不在读取层补默认配置。若实际保存结构影响公开DTO，先按具体受影响字段核对再接，不预先放宽或复制核心合同；内部执行配置、队列和原始异常不进入公开任务JSON。

**按依赖逐步验收：**

1. 双方对齐本节与核心第6/7步设计，运行本change strict。核心交付实际Case factory/profile、冻结/保存说明、可独占HTTP建案的隔离tenant/记录人/来源告警，以及新批次task、Run、Result和关键工件ID。此前只做设计和读取接线核查，不先删除可用入口或挂载未可执行的POST。
2. 复用第5步建案和通用任务/Run/原件读取的有效检查。选核心交付的一组正常材料，通过E01真实保存新案及initial任务，由真实调度/Case执行器完成首轮，再沿公开链接读回。模型/工具如使用受控替身须明确记录，不以HTTP成功判断模型正文质量。
3. 使用核心本批已保存的准备前/运行中材料变化、缺时/查询失败/截断、容量失败样本定向读取，核实际范围、状态、结果及原件，不为HTTP重新调用模型或重建故障矩阵。读取前后仅核本批直接涉及记录保持；核心失败或unknown原件不改写。
4. 首轮闭环通过后，移除外部E11/E13并做直接路由/端口边界检查：旧POST不可调用且不在OpenAPI，Case investigations仍未挂载，既有GET可用；保持无鉴权、核心不反向依赖HTTP包。只补本步必要测试，不重跑告警/事件及全仓回归。
5. 保存本步新证据，生成当前候选OpenAPI，原位更新交接/指南/功能状态及发布依赖；报告真实调用数和未验边界。第7步入口及整个change完成状态保持未完；不部署、重启、提交或推送。

本步结果：独占2告警通过E01建案，4次受理/读取→真实调度及C1–C6（2次模型替身、0真模型）→18次正常GET；只读复用核心5个已结束边界Case另17次GET。task/attempt/Run/Result/当前判断及原件来源一致，19类记录前后摘要保持，未重派已结束任务。E11/E13外部路由、端口及无用导出已移除，核心内部原语保留；6项直接检查通过。原测试预期/配置/地址/时间编码失败及修正保留于[回执](../../../docs/operations/evidence/case-initial-http-20261115-01/README.md)，不算业务bug修复。候选OpenAPI、首轮指南和发布依赖已更新；测试模块IF07只补development证据，21/runtime保持待发布。

### 8.20 测试模块协作与问题修复

2026-11-15，负责人要求结合实际需求、接口文档和设计完善测试方案，并按测试结果修复问题。测试模块维护现有完整测试规划、供给清单和实际预检回执；HTTP侧核对产品功能与公开合同，负责接口问题、文档修正及定向复验；调查核心问题交原负责聊天处理。测试环境以负责人在测试对话最新确认的21为准，本机旧版服务与本轮独立ASGI验证分开记录，见[本机实际状态](../../../docs/operations/evidence/http-local-runtime-review-20261115-01/README.md)；本机已有隔离/离线验证只保留其真实适用范围。当前T1只读，暂不部署、清理、投放或调用模型。

本轮先收口T1发现的接口版本差异：读取测试模块[实际预检](../../../docs/operations/evidence/investigation-test-preflight-20261115-01/runtime.json)，以method/path比较实际HTTP与原交接合同，区分已交付功能在当前部署缺失、候选未发布及已明确后置三类；分别核无凭据读取、实际OpenAPI和静态Swagger，不用健康200推断业务可用。当前记录显示21为main-a6660267-20261114、64个业务操作，原71合同中的7项缺失，无凭据业务GET返回401；128/129增量未在21应用。不能据此把仓库候选已实现能力改成未开发，也不能未经实际读回继续写“21已挂载71项”。

**直接步骤与完成判据：**

1. 与测试模块对齐IF07/08的第6/7步边界、IF09/10/12后置范围，以及125项功能/P项到用例输入、预期保存/输出、跳转/空态/错误的映射。测试模块原位补方案，不另建测试任务树。
2. 保留原失败，保存本次版本/操作差异及来源hash；用当前源码既有无鉴权与HTTP边界检查判断是否在候选复现。只核这次差异直接相关的路由、业务上下文和分层，不启动服务或重跑全仓。
3. 确认是代码问题时，先写清具体输入和预期、定向复现后修改本模块，再核保存及公开读取；若是部署版本差异，记未解决的运行缺口，修正当前交接描述并保留统一发布依赖，不能靠改文档或离线通过关闭21失败。探针错误交测试模块修复并新增回执，不覆盖旧记录。
4. 每条问题保存需求/合同依据、实际请求和结果、关联主体/task/Run、影响、副作用及安全重放判断、责任模块、修复和复验记录。状态区分待定位、已复现、已修复待复验、复验通过、待发布或依赖未就绪；原失败始终可追溯。只修当步阻断，再进入下一用例。

本轮输出为实际差异/定向检查证据及已修正的当前交接。第6/7步真实供给及第11步TCP最终验证继续按8.19进行，T1预检或本地检查不核销它们；模型正文质量与程序问题分开，原NOT_PASSED及unknown保持。

本轮结果：测试模块已提供[实际HTTP与静态Swagger对照](../../../docs/operations/evidence/investigation-test-preflight-20261115-01/http.json)。静态docs19/71与实际64操作不一致，可信上下文未加载；当前源码的7项既有路由均在，5项既有可信/合同/分层检查通过，没有以此证明21已修好。已修正README、交接、部署与测试指南、功能清单及PROGRESS的当前HTTP描述；[差异及修复记录](../../../docs/operations/evidence/http-test-alignment-20261115-01/README.md)保留原失败与定向检查。测试侧探针已区分HTTP数字状态与正文status，并按正确配置键及Swagger入口追加回执。

负责人在测试对话进一步要求先单点后集成，且“21上版本和设计不一致，那就等发布”。测试方案按模块单点→接口合同→局部集成→端到端设置准入；本次运行差异均登记待发布阻断，T1收口后不继续运行测试，不针对旧版临时补功能或部署。候选代码、接口就绪和21实际验收保持分别记录。

### 8.21 第7步Case持续更新与上一轮比较：HTTP对齐和验收安排

2026-11-15，调查模块按负责人授权开始第7步整体设计。本节先核已有合同和缺口，再与核心确认具体供给；**当前Case investigations已完成三任务真实执行与HTTP读回，候选80操作；20次受理、28次7A只读、41次终态读取/原key回放、47次7B只读通过。本步HTTP开发联验与文档已收口，正式候选TCP和统一发布仍属后续。** 第8–10步继续后置，21/T1仍awaiting_release。本节是既有第7步的HTTP配合，不新建任务树或完成计数。

**审计后的当前边界：** 原136次HTTP回执保留其原测试范围；5项跨模块问题已采纳，当前整体审计不通过。沿[既定顺序](stage7-case-updates-design-20261115.md#审计修复顺序与逐项验收2026-11-15)逐项修复/直接验证。F1已通过[22次同源GET](../../../docs/operations/evidence/incident-case-scope-fix-20261115-01/http-readback.md)：旧I3选1、Case仍3、C3/C6只关联原覆盖1条，新I不改旧C1，19表本批摘要不变。F2已通过[24次同源GET](../../../docs/operations/evidence/case-input-metadata-fix-20261115-01/http-readback.md)：owner/tags修改后原A及查询保留、check无变化且无Run，人工反馈后手动check另存完整Case并同时保留原A/反馈，17表本批摘要不变。公开A历史freshness合同不改，Case可用性按同原材料/已完成A独立判断。F3已通过[52次同源GET](../../../docs/operations/evidence/case-retry-fix-20261115-01/http-readback.md)：ConnectTimeout同task两个Run一次重试成功，C6 PoolTimeout耗尽后保留两轮C3原件，ReadTimeout原Run保持unknown不重试且下一案完成，15表本批摘要不变；冻结60秒门槛按核心测试时钟证据核对。三项均真实隔离PG、模型/故障替身来源、ASGI读回，0新增模型/执行/写入；失败原件保留。HTTP不实施核心，现有80操作/DTO保持。F1–F3本项可收口。F4已完成[59次局部只读核对](../../../docs/operations/evidence/case-trigger-fix-20261115-01/http-partial-readback.md)：不同key任务独立、9个no_changes无Run、旧1/新2范围、N2下B不被A阻挡、仅新I后活跃整事件Case更新及单告警范围成立；19表摘要不变。历史手动检查failed/unknown保留，full_F4_accepted=false；同key回放仅引用核心原PG/Redis证据，本轮无POST。上述59次仅为旧pg-01的历史局部结果。后续独立test-pg-01六项及test-retry-guard-01均通过，再经[89次同源GET](../../../docs/operations/evidence/case-trigger-fix-20261115-01/http-readback.md)完成读回：主批78次、19表摘要不变；重试批11次、10表摘要不变。历史手动检查成功且本案范围不扩，I完成后容量续建有实际initial/Result和接收关联；原task一次重试耗尽，新普通请求独立skipped/automatic_attempts_stopped无Run。新批在本机28413磁盘隔离库运行，22次模型替身，0真实模型；HTTP0新增执行/模型/写入。首读因测试入口遗漏分配配置返回503，已补显式配置后只读复验，旧失败不改写。F4本项可收口。F5随后通过[90次同源GET](../../../docs/operations/evidence/execution-contract-fix-20261115-01/http-readback.md)，F1–F5本机直接验证齐备，整体审计和21真实链仍待；当前不部署或推送。

#### 审计修复后的目标业务流程与接口验证

F5候选入口预检（2026-11-15）：现有HTTP分层/可信6项检查通过，公开OpenAPI与第7步候选完全一致，仍80操作、无鉴权，I/Case异步202及E11/E13/E36退役保持。已递归核11份发布片段中的108份源码及4份配置文件，F5要求的A/I/Case三类handler与现行IO合同均在核心片段；[预检回执](../../../docs/operations/evidence/execution-contract-fix-20261115-01/http-candidate-check-01.json)记录本次摘要。执行服务在启动/执行入口拒绝缺合同或旧输入，HTTP仍只负责受理和读取，不在HTTP中启动执行器或校验模型预算。预算数值继续配置化，不以8192等数值识别版本。该预检后，测试方新批A/I/Case及Deep/C6已完成90次同源GET；F5直接验证通过，整个change仍待第11步验收。预检回执本身仍只证明候选合同/清单。

2026-11-15，负责人已确认以下规则，替代旧版晚到A直接触发Case和不同请求归并的设计；**合同已定，F1–F5已本机实现及同源验证，完整链及独立结束审计仍待**。复用现有业务端口、请求和读取字段，不新增外部调度接口或上游等待屏障。

| 产品操作/变化 | 目标行为 | 后端读取与边界 |
| --- | --- | --- |
| 整事件加入Case后的自动材料更新 | 告警范围/有效分诊/有效告警反馈变化先进入I诊断；可用I的结论、依据或覆盖有业务变化，再由其唯一活跃Case检查。告警变化不直接绕过I启动Case，同值新Run不触发 | 查已有主体、关联、I task/诊断和Case task/Run，核来源及范围。成员已关联不等于已分析；新I失败不当作可用新结论向下游触发 |
| 单告警加入Case | 保持选入范围，不跟随所属事件扩员或诊断；该告警首次A晚到也不直接自动重跑Case，下次调查读最新可用结果 | 现有成员/任务/结果GET表达固定范围及实际记录；不补造自动任务，不将无新调查误报失败 |
| 建案首轮、手动check/rerun、有效H | 保留各自已确认入口和规则；手动调查不等待上游，按执行时可用材料分析，缺失如实记录。H仍按原有效正文/范围/引用及撤回处理 | 201分配回执或202受理回执后持续读原task；不让业务后端为自动链再发一次POST，不把上述材料链扩大成取消人工操作 |
| 对象先保存、模型后执行 | A/I/Case先持久业务对象、关联与异步task，模型尚未返回时即可读取；实际执行前冻结输入，完成后另存结果并更新相应关联 | accepted阶段`latest_run_id`可空、attempts/results可为空；GET无副作用。失败保留业务对象、关联、旧有效结果及失败记录，不用空结果覆盖旧结论 |
| 两个不同请求T1/T2 | 各自入队、同主体串行，实际执行前重新读取最新材料；普通检查已覆盖则skipped/no_changes，无新Run/模型；变化未覆盖则执行 | 原task_id分别查询，内部等待对外仍为accepted；相同operation_key同内容仅重放。无新增pending枚举或第二层外部任务身份 |

直接验证沿测试方案已有TC-I03/C06/C09、C07/A03/H02、Q02/Q03、C08/Q01/C05、P01/C17：每项由核心先提供实际新批任务/Run/结果和冻结工件，HTTP只补对应公开GET/必要原key回放，不重新消费已结束任务。F2核管理修改后有效分诊和原结果仍可读；F3核同task的失败尝试及一次重试、unknown不重试；F4核T2在T1开始前/交界/运行中/完成后到达、两种关联方式和各自检查范围；F5核唯一合同及实际装载配置。现有受理后未执行、无变化、原key幂等和读取无副作用证据可在原范围复用，不能证明新的自动触发规则已生效。

F1–F5修复及必要HTTP读回完成后，调查/HTTP/测试共同核对输入→任务→执行→保存→读取证据、剩余功能阻断、同版配置/迁移/OpenAPI与待提供的21候选TCP环境，再记录完整测试是否具备准入条件。该讨论不是自动批准部署或宣布验收通过；本机ASGI、模型替身、正式21实际TCP及真实模型分别记录，不互相替代。当前没有新的环境可用性结论，不使用旧18024冒充目标版。

#### 第11步HTTP准入与实际供给

2026-11-15，F5新批[90次同源GET](../../../docs/operations/evidence/execution-contract-fix-20261115-01/http-readback.md)通过，19表摘要不变；A/I/Case共3任务/Run、25步骤和69原件均已读取，C3/查询/Deep/C6当前合同与保存来源一致，0新增模型/执行/写入。至此F1–F5均具备本机直接验证及HTTP证据。**公开80操作、无鉴权及现行异步task合同可以冻结交付，进入第11步候选准备；21端到端尚不具备实际运行准入，完整change仍待交付/独立结束审计。** 同版源码和依赖冻结见[HTTP冻结清单](../../../docs/operations/evidence/execution-contract-fix-20261115-01/http-source-freeze.json)，不将旧21服务当候选。

沿[第11步既定顺序](stage11-candidate-design-20261115.md)逐步供给，不增加业务接口或兼容旧执行分支：

| 提供方/供给 | 已可用 | 仍需实际提供与核对 |
| --- | --- | --- |
| HTTP：合同与源码 | 三类主体、异步I/Case提交、任务/Run/结果/步骤/原件、范围/比较/分配/续建均有本机证据；OpenAPI80及无鉴权不变 | 将冻结的整个HTTP包和配套核心读写代码组装到候选；片段是增量清单，不能单独当可运行包。已补identity/runtime无鉴权装配依赖，正式运行仍须实测无凭据业务GET/POST |
| 调查/发布：独立21候选 | 已有部署脚本和各模块片段，可用于组装；正式旧服务状态已记录 | 提供实际候选API base URL、Swagger URL、源/镜像版本及hash、进程/容器名、启动profile及日志入口；核端口/资源后准备，不先切正式18024/18080 |
| 调查/发布：数据库与上下文 | V1及128/129增量已在本机验证 | 候选独立数据库、实际迁移回执、运行连接配置、租户及记录操作人；HTTP/入站/调度指向同一候选。服务仍内部可信，不要求调用方登录、Token或角色配置 |
| 入站/Fusion/来源模块 | Kafka合同、数据切片与来源映射设计已有 | 实际Topic/group及消费服务profile、投递地址和映射回执；提供source→canonical alert→incident的真实身份、归并及事件/上下文路由。禁止直写调查结果或人工重关联补成预期 |
| 调查/来源：模型与工具 | 当前A/I/Case合同、冻结预算/时间配置及查询准备已定 | 候选真实模型路由/模型名称与配置指纹，实际日志入源/查询及所需知识/资产来源；提供同租户/对象/时间窗的最小数据。未接来源如实标未接，不能用固定回复或合成查询代替本轮真实模型链 |
| 调查：唯一调度 | A/I/Case注册、独立任务、串行、有限重试及I驱动更新本机通过 | 一个实际候选调度器，显式任务策略、Case容量、当前IO政策、Redis namespace和消费范围；核缺合同启动拒绝及同版加载。外部HTTP不启动调度或承担内部步骤调用 |
| 测试：W1–W4与查阅 | 结束批次身份/步骤/原件GET和测试方案已供给；W1可复用结束证据 | W1测试账本只读API、W2真实调查HTTP代理、W3查阅页面、W4独立打包仍由测试侧逐步实现。先在候选联验完整分页、来源跳转、无Run/空结果/失败/unknown和真实环境ID，当前4177静态快照不算新HTTP查阅已接通 |

实际准入按小步核对：先候选版本/OpenAPI/profile/迁移及无鉴权TCP；再同环境最小业务写入→任务→实际执行→结果读取；最后依数据切片从Kafka真实投递核归并/路由、A→I→业务HTTP建Case→initial/更新、一次有效H/比较与显式rerun。每步保存实际身份和输入输出；首次对象已保存而模型尚未返回时，要观察GET可读，不能只看终态。HTTP错误、未接来源、查询空结果、分析unknown和模型正文质量分别记录。普通产品页面接线不作为后端接口验收前置，测试查阅按W1–W4设计推进。

本机隔离PG/模型替身/ASGI只证明中间程序行为；最终21必须真实模型及真实HTTP/Kafka。后置8–10、AI对话不重新列为本期接口缺口。当前没有投递、开消费者、改正式服务或推送；资料齐备后由调查/HTTP/测试共同给出实际候选准入回执。

#### 第11步首个HTTP交付子步：完整候选包与显式启动配置

2026-11-15，承接负责人继续第11步及三方先对齐设计的要求。本子步只在本机准备可交付包/manifest、候选profile及离线验证，不启动21服务、不创建库、不投Kafka、不调用模型；不改调查核心、公开DTO或新增业务接口。调查准备实际候选资源/连接/身份，测试并行收口W1。候选拟用新库 `socai2_streaming_20261115`、HTTP18424/Swagger18480，观察时空闲不等于已预留。

**现有入口问题：** `deploy/http-service/manage.py package`原为逐文件overlay；`prepare`继承reference_container的全部环境及旧挂载。直接套用无法保证新隔离库和完整同版源码。本步沿现有入口增加显式完整包/候选环境方式，不另建部署框架；原历史profile不作为候选默认值。

| 顺序 | 修改与业务效果 | 本步必要验证/通过证据 |
| --- | --- | --- |
| 1 明确完整包及配置合同 | 选定已观察的依赖基镜像ID/架构，打包F5冻结43文件HTTP包、当前完整app核心包及运行所需公开配置；新镜像内替换两个包根，避免遗留已删除模块。HTTP只挂独立入口 | 全部文件清单/hash；HTTP与F5冻结一致、核心与F5直接验证源摘要一致；秘密/缓存不入包，基镜像只提供已选依赖，不能把旧代码当当前来源 |
| 2 沿manage.py补显式候选方式 | 完整包根/文件范围明确；prepare候选只读取显式私密环境文件和显式挂载，核读写均为目标库，不继承参考容器连接/挂载。所有可变地址、端口、名称、TLS、租户/记录人和政策路径仍在profile | 使用临时目录及Docker检查替身，直接核打包文件和生成配置、原参考环境不继承、目标库不一致拒绝；不启动Docker服务或业务操作，不扩展通用部署框架 |
| 3 生成完整候选及离线交付 | `package`产生独立目录/tar、manifest和无凭据profile；运行连接/可信身份/挂载须由调查方真实供给后方可prepare。Swagger沿原80操作合同和三类文档另供候选地址 | 解包后verify_files/hash一致；从隔离包路径导入公开应用并对比80操作/无鉴权/退役路径，证明未从工作树补模块。私密文件未供给时明确不可启动，不填假可用值 |
| 4 交回调查及测试 | 同版源码/合同/依赖、profile字段、下一步TCP核验安排 | 记录包路径/hash、检查结果、实际未供给字段。后续调查组装独立21候选后核加载版本/配置/迁移与可信上下文，再开展TCP读写链；本步不以离线成功判21就绪 |

调查方需供给或确认：基镜像ID及linux/amd64依赖、网络/容器/project/root；新PG真实host/port及普通密码读写URL受控文件（按最新要求不需PG证书挂载）；真实tenant_id/actor_id/name；统一调查/任务/分配/Run读取配置路径及hash；候选私密环境文件、明确挂载源/目标/hash；实际API/Swagger URL及启动观察回执。已有只读资源证据可用来填已确认非秘密字段，未定字段单列，不能继承正式profile。最终源码包不包含运行秘密；完整包替换只发生在新镜像构建层，不删除主机源码或旧容器数据。

首轮r1离线结果（2026-11-15；PG证书前置随后取消，当前以以下r2为准）：[HTTP完整离线包](../../../docs/operations/evidence/streaming-http-candidate-20261115-01/README.md)已准备723个来源文件，完整app含SQL/JSON，663个与processing-20261115-r1共同文件摘要一致，43个HTTP冻结源码保持。解包后165个应用模块均来自该包，实际OpenAPI仍80操作/无鉴权，9类查询/任务策略及现行A/I/Case合同加载通过。12项部署工具直接检查、Swagger候选Compose解析通过；没有Docker业务启动、DB连接/写入、Kafka或模型调用。当前真实私密连接与CA摘要尚未供给，runtime_mounts的null有意使prepare拒绝；目标AMD64镜像及TCP仍待，不判运行就绪。第二次包移除了一个程序未使用的摘要环境变量，第一次离线成功原件保留；首次直接测试因未替代端口探测触发沙箱拒绝，修正测试替身后通过，未占用端口。最新HTTP/Swagger部署文档按字段说明当前候选，旧操作说明原文另存历史快照，W1已由测试侧完成，W2–W4及真实业务整链另按第11步推进。

#### 第11步HTTP窄调整：PG仅配置普通账号密码

2026-11-15负责人明确不要求PG客户端证书/CA；本步骤覆盖上文候选CA必填条件，旧离线包/回执保留原适用时点。目标是部署方只填数据库地址、端口、库名、用户名和密码，即可按当前候选连接；保留服务端TLS的默认require模式，不配置CA或客户端私钥。Kafka TLS、其他服务、业务字段、80操作合同和无鉴权方式不变，不部署或新建资源。

1. 共享连接归一化由调查模块负责：读库与Case写库复用同一入口；asyncpg的require使用不读CA文件且不验证证书的TLS上下文，psycopg使用require。HTTP不复制另一个连接实现；缺陷修复按共享模块的直接验证和同版源码收录。
2. HTTP候选环境移除PGSSLROOTCERT，runtime_mounts为空，不再要求CA摘要。prepare只核真实读写目标和账号密码，省略SSL模式时由显式候选profile的postgres_sslmode=require补入URL；不继承旧容器环境/挂载，不扩大到其他TLS配置。保留实际私密连接文件必填，不填假连接，不修改数据库对象/数据。
3. 直接验证沿既有部署测试补普通无CA读写URL→prepare→私密env/Compose读回；核目标一致、默认require、没有CA挂载。使用实际共享归一化函数核两条URL无证书依赖、HTTP应用80操作仍与原合同一致；不启动服务或连接实际DB，不把参数验证当真实TLS连接通过。
4. 在共享源码定稿后生成新完整包/manifest，解包实际导入并核当前合同/配置；更新最新部署README、四类配置字典、供给缺口和Swagger目标说明。保留旧包原件，标当前包替代；仍待真实DB/凭据及21目标镜像/TCP，之后才由调查统一推进候选运行。

本窄调整结果：[r2完整包与直接回执](../../../docs/operations/evidence/streaming-http-pg-password-20261115-01/README.md)已完成。13项工具检查通过，663共同app与processing-20261115-r2一致；解包165模块来自同包，实际读写两池均为无CA依赖的require TLS上下文，80操作/无鉴权/查询策略合同保持。profile为postgres_sslmode=require、runtime_mounts=[]，不含PGSSLROOTCERT；文档移除CA摘要前置，仅等待真实库/身份/凭据及21镜像/TCP。实际数据库连接/业务写入/启动/模型/Kafka/Git均为0；旧r1回执原件保留，不冒称实际连接已通过。

后续测试侧[普通密码真实连接补验](../../../docs/operations/evidence/pg-password-connection-20261115-01/README.md)通过：21已有普通reader require/TLS1.3且无CA，正确密码可读、错误密码28P01；本机普通LOGIN的真实HTTP两池及事务回滚、前后ASGI读取保持。该本机库SSL关闭且明确disable，不能代替21候选require写入/18424 TCP。本HTTP侧已核三个受测文件与r2完整包摘要一致，不重派已结束批次或把这些结果累计成全链验收。

#### 第11步候选实际启动与最小TCP验证

2026-11-15，沿本阶段资源供给及候选部署授权继续。调查会话已按负责人最新要求主动停止21的9个旧调查业务容器，其中含旧18024 HTTP及18080 Swagger；其他29个容器、共享PG/Kafka/Redis/模型依赖及既有数据保持。[停止回执](../../../docs/operations/evidence/streaming-old-services-pause-20261115-01/pause-01.json)只证明暂停，不是新版本发布。HTTP不恢复旧容器，本机旧服务不在该操作范围。

本步目标是让后端在同一候选库上访问真实无鉴权HTTP及对应Swagger，明确空库就绪与成功业务写入的不同完成条件；沿既有80操作和r2完整包，不改业务代码、公开字段或迁移，不调用模型。正式发布、最终Kafka整链和结束审计仍按阶段安排完成。

| 顺序 | 依赖与操作 | 直接验证及完成证据 |
| --- | --- | --- |
| 1 核实际供给 | 调查提供新库`socai2_streaming_20261115`、123–129及现行查询函数、所需public基础表、identity指定tenant/actor；owner为NOLOGIN，reader/writer为普通密码连接。受控`private/http-runtime.json`提供两条同库URL，require、无CA；不在聊天/证据暴露密码 | 核迁移/表结构回执、基础身份和普通运行连接；代码/政策/合同与r2 manifest一致。HTTP不自行新建库/角色、填假连接或混用正式数据 |
| 2 准备并启动HTTP | 核linux/amd64基镜像、网络、18424空闲；传输冻结包并核tar/manifest；沿manage.py prepare/build/start只启动候选。与调查协调其他候选容器在该短步骤内保持，以便核其他容器快照 | 实际release/image、来源hash、无旧环境继承；实际reader/writer会话连接同库、普通身份及require TLS；`/readyz`、完整OpenAPI与80操作/无security一致。失败保留真实原因，不恢复旧服务 |
| 3 空库读取及Swagger | 无Authorization读取告警/事件/Case列表及空态；HTTP快照验证结束后再启动独立18480，加载相同版本的三类合同 | 真实TCP状态/JSON、文档三个文件及摘要、Servers为18424；无新Case/task/Run/模型。连接成功、空列表或失败事务回滚不算成功业务写验收 |
| 4 Kafka真实主体后的写读 | 成功写读并入测试S01的来源→Kafka→真实A/I→首次整事件建案，引用实际canonical/incident ID，读取Case及initial task、同key重放，再用实际版本做一次管理修改并读回；调查统一安排Case受理读回与调度开始的观察点，不额外预建单告警Case | 201及同一真实Case/分配/任务身份，重放不重复创建；PATCH结果与随后GET、同库保存值一致。首次建案必须有真实来源，不预造告警/事件或直接插入Case/task/Run/Result；Case执行前观察task已受理而Run为空，原任务进入同批后续整链 |

`CaseCreate`明确要求`alert_ids`或`incident_ids`至少一项；因此空库供给只能结束前3步，成功写读依赖第4步真实入站。旧本机PG/ASGI写读与21已有reader TLS证据均保留原范围，不拼接成候选TCP成功结论。后续按下一节衔接真实A/I/Case执行及原件读回；各步据实保存回执，不重跑已通过的本机五项修复。

本子步前3步已完成：[21实际回执](../../../docs/operations/evidence/streaming-http-runtime-20261115-01/README.md)记录18424/18480均已启动、r2/80操作/三类文档同合同、同库普通reader/writer的require TLSv1.3及三类空列表200。零行UPDATE后回滚，0业务提交/模型/Kafka；旧9容器仍停止、其余29运行容器保持。最初预检脚本读取暂停回执字段的TypeError原件保留，修正后新预检通过。第4步成功写读及整链仍待；容器窗口已交还调查，测试已取得W2真实目标，不据空态勾整链任务。

#### 原生入站后的只读HTTP子步（2026-11-15）

**旧失败批状态处理例外：** 按[第11步设计](stage11-candidate-design-20261115.md)，HTTP仅对测试`test-streaming-s01-ingress-20261115-01/readback/alerts-pg.json`的实际3条告警和1个事件，通过现有管理接口关闭/解决，原因“验收批来源范围失败，停止后续分析”。先读当前版本与4条未开始任务，再以独立operation_key提交，保存请求、回执、活动和读回；核原材料、来源、判定及分析指针保持。不新增取消接口、不直写SQL、不启动调度，不把状态变化当成来源问题修复或新批通过。调度后续领取时应按`closed_before_start`跳过；未领取前如实保留accepted，不提前声称已跳过。新批继续按下述只读范围验收。 实际[30次HTTP请求](../../../docs/operations/evidence/streaming-failed-batch-close-http-20261115-01/README.md)已通过：3告警completed、1事件resolved，活动原因保存，原材料/来源/分析指针保持，4条task仍accepted且未开始；没有启动调度。

调查和测试先完成隔离Fusion入站及上下文供给，暂不开模型调度。HTTP保持已运行的18424/18480及旧服务停止状态，等待本批真实Kafka回执、canonical告警/事件映射和已保存任务身份后再读；不使用T2离线UUID猜测已存在对象，不提前建Case或直写数据。

本子步只解决“实际来源已保存后，后端能否正确读到主体、关系及待执行任务”。调查唯一负责资源/profile/Fusion及阻断修复，测试唯一负责新批分阶段投递、CH/PG断言和identity-map；HTTP取得该真实映射及落库回执后，仅执行业务GET和维护自身交接/HTTP回执，不重复查询全库或另做入站验证。预期先12条上下文入湖且不产生额外告警，再3条告警归入1事件，登记3条A及1条I initial任务。HTTP核实际batch/tenant和source→canonical→incident映射，读取告警详情/事件关联、事件详情/全量成员分页，再读4条任务及分析目录；应为accepted、source=ingress、无attempt/Run/分析结果。数量与分组由独立预期约束，并与测试实际保存回执逐项对照；不强造任务满足数量。关系/状态不一致时保留响应并反馈归属模块，只修本步直接阻断。

直接证据保存无Authorization的实际GET、请求/响应，并引用测试方同批身份映射与CH/PG断言原件；HTTP不另做同一套数据库对账。保留缺失/失败，不重跑已通过空态、配置、故障或模型矩阵。完成后仅标记入站对象/关系/任务的非空HTTP通过；A/I结论、Case建案及跨Run原件仍留S01后续。若真实身份尚未供给，本步明确待执行，不由文档检查或空列表回执代替。

**本子步实际通过：** 测试已供给`s01-ingress-20261115-02`的真实PG identity-map和上下文/告警通过回执。HTTP完成[35次TCP GET](../../../docs/operations/evidence/streaming-ingress-http-20261115-02/README.md)：3A↔新I/3成员、3实际事件来源及2页分页、3份材料及来源原件、4 accepted initial ingress任务列表/详情一致，无attempt/Run/结果。0写入/另查DB/模型。首次校验误要求公开来源包含私有tenant_id，原失败保留，按已有合同离线复验保存响应通过；没有业务修补或重发请求。只收口入站后非空读取，真实分析和Case链继续按后续步骤验收。

#### 已有A/I任务执行后的HTTP联验（2026-11-15）

**目标与当前状态：** 接续已通过的`s01-ingress-20261115-02`入站子步，证明后端能沿同一原任务读到真实告警分诊、事件诊断、实际分析范围和原答。本步已完成[62次实际TCP读回](../../../docs/operations/evidence/streaming-ai-http-20261115-01/README.md)，4个Run及结果同源；模型质量NOT_PASSED单列保留。调查负责唯一调度及profile，测试负责实际保存断言，HTTP负责本节读回和交接；根侧维护PROGRESS/tasks/stage11。A/I两侧完成后再安排HTTP建Case。本步不另提交分析、投Kafka、建Case或启停执行器；不重复已通过35次入站、空态、数据库检查或构建未变的HTTP包。

**固定输入与依赖：** 主体/原4条initial任务只取[真实入站identity-map](../../../docs/operations/evidence/test-streaming-s01-ingress-20261115-02/readback/identity-map.json)，继续使用候选18424、无鉴权、同租户。A01/A02/A03及I01任务身份保持；Run/attempt/结果/工件ID必须等待测试交付实际执行映射和保存快照，不按4条任务预填4个Run。正常调度如果产生后续I检查或重试，保留真实新增身份及原因，不用手动请求补齐。测试需同时提供执行时源码/profile摘要、实际A前序采用关系、I冻结选入与覆盖、模型/查询原件及旧关闭批任务的实际观察；后台知识或背景材料只有真实导入/查询回执才算已使用。

**短周期配置衔接（已实际对齐）：** 调查已提供[候选analysis配置](../../../deploy/aisoc21/streaming-candidate-20261115-01/analysis.json)及[同批lifecycle](../../../deploy/aisoc21/streaming-candidate-20261115-01/analysis/lifecycle.json)：I检查20秒、Case检查30秒、活动窗口86400秒、重试最多1次/等待5秒；N1、轮询1秒及A/I每Run预算以对应显式配置为准。变更前HTTP r2加载原lifecycle（活动604800秒），下述实际切换已改为同批86400秒。`AnalysisTaskStore.automatic_status`按读取端policy重新计算`auto_expires_at/eligible/ineligible_reason`，只有`next_check_at`等取保存记录；因此配置未对齐前不能把列表的自动更新资格/截止时间验收为与调度一致，截止时间会差6天。任务详情的attempt/Run/result不经过该计算。配置现已对齐，后续62次GET同时核对实际结果和1天截止时间。调查已确认由HTTP唯一负责在本步最终读回前统一lifecycle。按[配置对齐清单](../../../deploy/http-service/streaming-20261115-01/lifecycle-runtime.json)，把21同一宿主lifecycle文件只读挂载到现有SOCAI2_ANALYSIS_TASKS_CONFIG_FILE指向的/app/config/analysis-tasks.json，摘要须为4ab6f1b11d5bc3a87005c92597ccba6f6d9a58ce880417eb729d90c77941e6aa；保留已验镜像和80合同，只重建该候选HTTP容器，不构建镜像、不动Swagger/旧服务/数据库。先保存现容器/环境摘要/实际policy/合同与目标源摘要；沿原compose加单文件只读挂载后，以同镜像重新运行。核环境和其他运行参数保持、实际加载policy等于同批源、ready和OpenAPI仍同版80操作无鉴权，保护容器ID/状态不变。原compose保持供恢复，失败保存原回执、只修本次配置阻断；不重复空态或业务GET。证据保存streaming-http-lifecycle-20261115-01，实际任务/结果GET沿下述测试正式同批快照完成。[实际对齐回执](../../../docs/operations/evidence/streaming-http-lifecycle-20261115-01/README.md)已通过：仅新增同文件只读挂载并重建候选HTTP，容器内policy摘要一致；镜像/环境/80操作合同及Swagger+旧9容器保持。该配置步骤0业务GET/写入/调度；随后本节62次GET已核资格摘要和真实A/I结果。后续Case受理沿同一已对齐配置，不追改原任务。已有initial的retry_limit/retry_delay_seconds按受理时保存值保留，新5秒配置不追改旧任务；核对以真实快照为准。不修改业务实现或公开字段，不重打未改核心。

以下路径均省略`/api/v1/socai2`，输入均来自上述实际映射或响应链接，调用均为GET：

| 顺序与后端需求 | 最小调用 | 本步新增核对内容及通过证据 |
| --- | --- | --- |
| 1．确认原任务执行到哪里 | `/alerts/{id}/analysis-tasks/{task_id}`、`/incidents/{id}/analysis-tasks/{task_id}`；I出现后续任务时读其任务列表并跟随next_cursor | task→attempt→Run→result归属与测试快照相同，核真实source/intent、状态、reason_code、retry_count及时间。未开始仍无Run；failed/unknown/重试分别保留。相同Run去重读取，不用轮询制造额外业务请求 |
| 2．取得各次实际分析及当前结果 | 跟随attempt.run_url/results[].url读取`/{alerts或incidents}/{id}/analysis/runs/{run_id}`；每个主体读一次`/analysis`，再按next_before_run_id读必要后续页 | A result正文/分诊ID、I result正文/诊断ID与同Run保存值一致；current_pointer_id/current与历史entries对应真实指针。只重读主体详情的新增triage/诊断指针核对，不再读入站材料、来源或成员。最新失败不冒充当前有效分析 |
| 3．确认事件真正分析了谁 | 同一I Run响应的input_selection及analysis_coverage | 冻结selected_alert_ids、selected/omitted/total和input_artifact_id逐项对照；covered_alert_ids只在实际选入范围内。analyzed/unresolved/not_analyzed按保存语义返回，未知保持null，待核不等于未分析，不能扩大到全部当前成员；所用A结果以冻结输入指明的来源为准，不假定I使用了随后才完成的A |
| 4．追溯真实步骤、模型原答及查询来源 | `/{subject}/{id}/analysis/runs/{run_id}/trace`取得steps_url/artifacts_url；沿`/analysis-runs/{run_id}/steps`和`/analysis-runs/{run_id}/artifacts`必要分页，再跟随保存原件content_url | 按本轮真实步骤/工件目录核完整数量和归属，读取直接支持结论的冻结输入、实际模型请求/原答、校验结果和已执行查询回执，与测试保存正文/摘要一致。kind、步骤状态、来源和availability保持；目录有工件不等于正文可用，不重新调用模型/工具。正常可用内容须读到实际正文，不只验链接200 |
| 5．说明旧失败批没有再执行 | 测试提供实际观察后，仅读旧3A/1I的4个原task详情 | 应按实际保存读到closed_before_start及无新attempt/Run；若调度尚未检查就如实记待观察，不提前改成skipped。复用既有关闭回执，不重复PATCH或读取原6条错误来源 |

**逐步验证与收口：** 先收到测试完成的执行map/快照，冻结本步输入引用及摘要；按上表读取并即时保存请求/响应，再离线逐字段对照，验证脚本只使用现有公开字段，`tenant_id`等内部字段不强加到DTO。取数错误或内容/归属不一致保留原失败，反馈对应模块，只修具体阻断；不盲目重派已有任务。动态列表使用同批已保存记录与观察时间判断，不拿正在变化的当前指针反写旧Run。403/401不是本服务的接入前置，所有请求不带Authorization；对象不存在/归属不符404、参数错误422、读取依赖不可用503按现有合同保留，不专门新增故障矩阵。

执行证据使用`docs/operations/evidence/streaming-ai-http-20261115-01/`，包括来源引用/摘要、实际请求响应、逐项核对、错误及README；正文按既有受控证据规则保存，不打印凭据或隐藏推理。HTTP读取没有SQL/业务写入/模型动作，以请求记录和测试方保存证据说明范围，不另做全表摘要。只有实际执行后才能填通过/调用数，不预建Run或成功回执。HTTP正确读出失败只说明读取合同正确，不能把A/I功能失败改成成功；模型正文质量继续按已确认规则独立保留NOT_PASSED，不为本步反复采样。两方实际通过后更新交接为“A/I本步通过、Case与整体审计仍待”，不据本节计划勾完成或触发正式发布。

**本子步实际收口：** 测试正式map/快照摘要已核，62 GET全部200、无鉴权。4原initial各1attempt/Run和3分诊/1诊断、17步骤、45份Run工件元数据与29份必要正文同源；I选入/覆盖3条及原A/9查询来源保持，旧4task真实closed_before_start且无attempt/Run。HTTP实际读回同批1天auto_expires_at、已保存next_check_at。0写入/直查DB/新模型/Case，未发现本步接口程序问题。A“告”/I“A”的原答及质量NOT_PASSED保留，不把结构和读取成功写成正文合格。详见[实际回执](../../../docs/operations/evidence/streaming-ai-http-20261115-01/README.md)。下一步等调查统一安排HTTP建Case，不提前创建。

#### S01整事件及单告警Case：受理与首轮HTTP安排（2026-11-15）

**本阶段目标与本轮落点：** 复用S01真实A/I已保存结果，将整事件建立为自动接收后续事件变化的Case，另建仅含A01的固定范围对照Case，验证建案持久受理及随后首轮的保存/读回。沿原S01/S04设计的两种关联方式，本步只做S01，不投S04、不重投Kafka或重跑A/I。已沿[两份固定操作键的创建请求](../../../docs/operations/evidence/streaming-case-http-20261115-01/requests.json)完成2次POST/5次GET，持久受理通过；调查先确认Case湖/知识实际profile ready及调度停止，HTTP逐案创建并核受理时无Run。HTTP只负责这两次业务创建、受理读取和最终同Run读取；调查独占执行器，测试在执行后唯一抓保存快照。保持18424/80合同、无鉴权及已共享lifecycle，不重打包/重建HTTP，不重复62次A/I验收。

输入只来自[实际S01身份映射](../../../docs/operations/evidence/test-streaming-s01-ingress-20261115-02/readback/identity-map.json)和[真实A/I保存回执](../../../docs/operations/evidence/test-streaming-ai-20261115-01/acceptance-01.json)。当前HTTP/调查分配policy均为单案最多100条，本批3条和1条应各形成1个独立Case，无容量续建；实际分配回执仍完整保存，不能只取首案丢掉其他分配项。Case/任务/Run/Result身份由服务实际返回，不提前生成。

| 请求 | 入口与准确范围 | 受理后应有的业务效果 |
| --- | --- | --- |
| 整事件首轮 | `POST /api/v1/socai2/cases`，仅传operation_key、title、`incident_ids=[263a1c58-e9c6-4ba4-9204-3b0568970551]` | 显式关联I01及当前A01 `09e85609-d734-5b2a-81ba-d086fc81b619`、A02 `69eff99f-252e-5720-a6d4-ca556f29a557`、A03 `f4542be8-4097-59af-8a68-50c52a10f50b`；I01接收目标指向此新案。不是按诊断上限截取成员 |
| A01固定范围对照 | 同一POST入口，另一operation_key，仅传title、`alert_ids=[09e85609-d734-5b2a-81ba-d086fc81b619]` | 独立新案仅含A01，没有显式事件关联、不抢I01接收目标。与整事件案共享A01是合法独立案件；以后也不随所属事件扩员。本步只验首轮，S04更新对照留后续 |

不传租户、人员、运行窗口、模型、预算或来源配置；这些沿服务与调查显式profile。请求不写预期良恶结论或人为补充已失败的A/I正文。上游A“告”/I“A”的真实原答及质量NOT_PASSED保持，不能凭新案创建把上游质量核销。

**单告警案的上下文与范围：** 测试已核当前C1真实合同，HTTP也复核`baseline_context`及`case_incident_scope`：即使单A01案没有显式case_incidents关联，C1仍可沿A01所属事件读取I01诊断。该I的`linked_from_case=false`，来源自身的input_selection/analysis_coverage仍保留原3条；`case_selected_alert_ids`及`case_covered_alert_ids`必须仅为A01交集，保留`diagnosis_scope_extends_beyond_case`说明。不能断言C1不得出现I，也不能将其另外2条成员加入Case或扩大本案结论依据；显式事件接收目标继续指向整事件案。此项在首轮执行后的冻结C1原件读回中核对，受理时仍只核1成员/0显式事件和无Run。两份已冻结请求及operation_key保持。

**逐步操作、直接验证及出口：**

1. 先核调查实际就绪回执及调度已停止；来源准备不等于已由Case查询，未导入/未索引如实记录。对照固定request/source摘要、当前容量和已对齐lifecycle；不重新做数据库/空态或A/I全量读取。就绪前只维护方案与请求，不发POST。
2. 先提交整事件请求；保存完整201/错误原回执，再沿allocation.case_url与initial_task.status_url GET。核新案3成员/1显式事件、scope_revision、独立continuation及initial任务accepted/source=case_create，attempts/results为空、latest_run_id为空；Case详情baseline_records无Run，current_assessment为空。受理失败停在该操作，不先铺开第二案。
3. 第一案受理读回通过，再提交A01固定请求；同样保存201及Case/task GET，核仅1成员/0显式事件、独立根Case及无Run。最后只读一次I01详情case_receiving/接收目标，确认仍为整事件案；不重读其诊断原答。每步先验后续，不在请求未明时换key重建。两份operation_key和body先冻结；连接未知或保存未确认时保留失败，沿已有同key合同核对，不新造案或直接填表。
4. 向调查/测试交实际case_id/task_id、分配/受理读回及两种成员范围。此时HTTP不启动执行器、不调用旧prepare/start或另POST investigations；调查按唯一Case来源/profile启调度，测试核一次C1/C3/C6及实际选到的查询/Deep/结果，不能要求模型必须选择某工具或预填Run数。
5. 测试交真实task→attempt→Run→Result及冻结范围/原件快照后，HTTP才执行Case GET：原task、`/cases/{case_id}/runs/{run_id}`、results[].url、当前判断及必要历史；沿steps_url/artifacts_url完整分页和正文链接，核原输入、实际日志/知识/模型原答/校验/结果同源、整事件范围3与单告警范围1保持。实际Run范围与当前成员分开；首轮previous_run/comparison为真实初始值，不制造上一轮。不重复源头入站或A/I62GET，不另查库/调用模型。结构/执行/质量分别记，沿已确认规则保留模型质量NOT_PASSED及旧失败，不重采样求好答案。

准备证据和实际回执统一保存在`docs/operations/evidence/streaming-case-http-20261115-01/`。[受理回执](../../../docs/operations/evidence/streaming-case-http-20261115-01/acceptance-01.json)及[实际Case/task映射](../../../docs/operations/evidence/streaming-case-http-20261115-01/actual-case-map-01.json)已保存：整事件Case 58194401-03ca-5383-83b4-ac82886a5acd/task 413e6f0e-1dad-4750-8fa4-152344eb1438；A01案 bad63e2a-9f03-547b-8a0c-243347807c41/task 26a4fa49-3351-47eb-93fb-40c6b9528c4e。范围分别3成员/1显式I与1成员/0显式I，I接收者仍为整事件案。受理时均accepted且0attempt/Run/结果；随后唯一执行器完成两案首轮，测试277项保存核对通过，[同源结果58次GET](../../../docs/operations/evidence/streaming-case-result-http-20261115-01/README.md)已通过。两Run/Result、34步骤、96工件目录及44份必要正文一致；I原覆盖3、本案交集3/1、知识4/2条、各2次C4与原答可读，首轮比较为空。两案completed/accepted/uncertain/partial，引用质量问题保留，正文全面评估未做。失败仅修本步直接阻断。Case子步通过后由根侧统一收口，S04、代理/4177、独立结束审计与正式发布仍分别待办；本节不触发Git推送。

#### S04新增材料驱动后轮：HTTP准备与验收

2026-11-15，承接S01两案首轮验收后的下一子步。本步只核测试独占投放的E13/A04经真实Kafka归入原I、产生新诊断，再推动活跃整事件Case更新及前后轮比较。根侧核归并处理时间窗口、来源/profile和唯一调度；HTTP不投Kafka、不手动关联、不提交check/rerun、不创建新Case或另启执行器。18424/18480、80操作、无鉴权与既有HTTP镜像保持，未变合同不重建Swagger。

复用已保存整事件Case `58194401-03ca-5383-83b4-ac82886a5acd`、原Run `d1b17106-0ee7-4265-ac84-beb9ebf048eb`/Result `9cf1a538-ddf2-4df1-aa37-021cbf95d5a2`，以及固定A01 Case `bad63e2a-9f03-547b-8a0c-243347807c41`、原Run `3327b87f-f4d8-451e-b91d-39618622ead9`。新告警、task、Run、结果与工件ID只取测试本步实际映射；此时不生成预期身份或假定执行次数。

| 核对内容 | 输入与只读HTTP | 应有的业务效果和必要证据 |
| --- | --- | --- |
| 新告警及来源 | 实际A04 ID→`GET /alerts/{id}`、records/source_artifacts、records/incidents；原I详情及成员分区按真实分页 | A04关联原I，新增直接来源为真实E13，不能把告警自身ID冒充来源。I全量成员变为4；归并失败由入站实际回执记录，不能用HTTP重新关联补成预期 |
| 新A和新I分析 | 实际task→attempt.run_url及results[].url；读取新的A/I Run、输入及必要原答/查询回执，沿steps_url/artifacts_url分页 | A04自动首轮及I实际新诊断可读，I固定选入4的本轮范围、配对A与实际覆盖分别核对；覆盖以原件为准，不能用选入数或completed冒充全部分析成功。仅读取本步新增分析，不重读S01的整批A/I正文 |
| 活跃整事件案后轮 | 当前Case详情、实际新增task、后轮Run/Result、历史及本轮必要C1/C3/C6/日志原件 | I有效业务变化之后才进入Case后轮，Case/本轮实际范围应包含A04并为4条；后轮C1引用实际新I及其真实范围，不能只凭任务时间排序证明使用新诊断。阶段先后和成员跟随由测试同源快照/执行回执证明 |
| 上一轮及业务变化 | 后轮Run/Result的comparison_context、previous_run_url、comparison_result_url；沿非空链接核实际前轮，读取后轮冻结输入及change_kind/change_summary | 首个新增后轮应关联上述已保存整事件初轮；旧轮3成员/初始comparison不回写，新轮4成员。若实际产生其他前置尝试，按核心冻结的上一实际Run及不可比较原因核对，不跳过失败轮或硬填旧Result。模型业务变化正文按原文读取，不由HTTP推导新判定 |
| 单告警对照保持 | A01 Case详情、任务列表及history完整分页，与既有单案原件和本步测试快照对照 | 仍1成员/0显式事件，原initial Run和Result保持；不因I扩员或新诊断自动新增调查Run。必要的当前判断新鲜度可按真实来源变化返回，不要求整个动态Case JSON与旧时点逐字相等 |

实际执行前，由测试交唯一新增身份map、正式保存快照及核对结果，HTTP只读同批对象，保存请求/原响应/来源SHA并逐字段比对；跨Run比较所需的少量旧链接和旧冻结范围属于本项新验证，不重跑上一批58GET。新增A04后整案查询窗口按本轮成员时间重算，不能复用S01的旧排除集合；实际查询范围、日志命中和排除对照测试投放前冻结的新预期，单A01范围保持。失败仅定位本步HTTP/合同/来源关联阻断，不调用模型或回写数据修答案。C2/C4查空、未查、失败及unknown保持，结构/执行/交付/质量分开；原质量问题不重采样。

准备与最终回执目录为`docs/operations/evidence/streaming-s04-http-20261115-01/`；preparation-01保留准备时0HTTP状态，实际失败分支44GET及指南已完成，0业务写入、0直接DB查询、0新模型调用。W2非空/跨Run、W3/W4、独审和统一正式发布留后续，不能由本步预先计为通过。

**本次实际失败分支（44次同源HTTP读回已通过，正向S04仍未通过）：** 入站已确认A04为`d7bc92ec-691e-5b45-bc03-ccb85367dba8`、initial task为`e911219c-296e-5b81-a74a-54b3e3f75cc0`，E13直接来源为`324ddc21-7635-5ab6-be3b-c339bd6aeacb`，原事件已增为4成员。调查随后报告A04完成，但事件check任务`4abd74b8-28fc-4109-9462-5dc471e409c3`因`model_response_not_complete`失败，后续检查因`automatic_attempts_stopped`跳过，没有新Case Run；唯一调度已在无在途后停止。这是实际失败分支，不能继续按预期假设Case已产生第二轮。测试唯一最终快照/map已供给，[44次HTTP失败分支读取](../../../docs/operations/evidence/streaming-s04-http-20261115-01/README.md)通过：5新task、2attempt/Run、7步骤、18工件目录及13份新增Run原件正文同源；旧I指针保留但stale/valid_for_current_input=false，3后续check停止且无attempt/Run；两Case仍3/1成员、各原initial任务/Run/Result和当前判断。事件实际模型请求max_tokens=3000、finish_reason=length/output3000，原答截断及错误可查；HTTP无业务写、直接DB查询或新模型调用。不存在后轮时不构造前后比较链接，保留初轮的initial/null。原计划的成功更新/后轮比较仍未通过；不得用失败可读代替S04成功验收，也不手动重试、改旧数据或重采样。

#### W2非空代理验收：HTTP离线供给（2026-11-15）

本子步仅从已保存S01/S04回执与当前源码核对代理所需路径，测试模块独占临时代理和实际GET，调查模块负责第11步/源环境；HTTP不再重读S04的44 GET，不启动业务操作或改服务/镜像，W3/W4暂不实施。目标是让测试能沿实际来源身份取得原件，同时保留失败、未开始及旧结果的新鲜度。[配合回执和小路径map](../../../docs/operations/evidence/streaming-w2-http-cooperation-20261115-01/README.md)已准备；新增HTTP/业务操作均0，不能据离线完成宣称代理TCP通过。

1. **核合同。** 测试冻结的实际OpenAPI与当前Swagger同为80操作/55 GET、无鉴权，方法/路径和所有Schema一致；实际55 GET与原候选GET相同。Swagger字节差异仅为分类、部署状态、示例和1处POST说明，不能用文件摘要不同推断业务合同漂移，也不更换测试已冻结的实际OpenAPI。
2. **供给真实来源链。** Case C1的`content_json.incidents[id].diagnosis_scope`提供原I的`source_run_id/input_artifact_id/source_fingerprint`；由实际Run身份查询统一工件目录，匹配`items[].id`后跟随返回`content_url`读取原I输入，核来源身份和摘要。必要时再由I冻结`triage_queries[A01][0]`进入原A查询工件。两Case分别保存原I覆盖3/本案交集3和1，不能改写来源范围。原件路径必须保持原主体和Run，Case响应的`artifact`与A/I的`metadata`也原样保留。
3. **保持失败和覆盖边界。** 小map同时提供S04 A completed、I failed/model_response_not_complete、3 check skipped/automatic_attempts_stopped以及两Case首轮Run。旧I指针和原Case结果可读但当前stale；历史输入中的覆盖不代表当前有效。8份实际steps目录没有跨Run artifact_refs，本批能验证的是C1来源身份→原Run目录→原件链，不能声称真实覆盖步骤直接跨Run引用；S04无Case R2，前轮比较链接为空。

离线核对未发现本步HTTP能力缺口。实际TCP验收由测试复用原保存快照对照少量非空/分页/失败/来源请求；模型质量NOT_PASSED及S04正向更新/比较未通过保持，不另造身份、Case后轮或业务结果。后续仅接收测试实际结果并同步交接，不重做既有整批读取。

**实际验收已完成：** 测试独占执行的[W2 TCP回执](../../../docs/operations/evidence/test-http-proxy-w2-live-20261115-01/tcp-02/result.json)为34 GET（9账本、24业务代理、1当前OpenAPI），全部200、107项直接断言通过。沿整事件C1真实来源身份→原I Run目录→返回content_url读取原输入，来源摘要及3条冻结范围一致；读取S04失败/3条skip、两Case原partial、initial/空比较及必要分页。HTTP[离线复核](../../../docs/operations/evidence/streaming-w2-http-cooperation-20261115-01/tcp-readback-review-01.json)核34份响应摘要和上述字段与已保存map一致，新增请求0。没有扩展可选A01来源链，没有steps直接跨Run引用或Case R2正向覆盖。首个临时隧道误选回环目标失败保留、0业务GET成功；修正为当前21地址后本批一次通过，临时代理/SSH停止、端口关闭。0业务写/模型/测试直接SQL，业务GET正常读库；未改服务代码/版本/合同。W3/W4和整change独审另步，S04正向及模型质量未通过保持。

#### W3页面HTTP读取：路径、字段及独立核对（2026-11-15）

**目标与分工：** 页面通过HTTP浏览测试批次、实际操作、分析任务、Run、结果及来源材料，新记录不依赖人工导出HTML。测试模块负责页面/测试服务接线与直接验证；调查负责人负责整体设计和独立页面查看；HTTP侧离线核合同、提供下表和最小核验清单，最终核测试保存的页面请求/响应，不重复发GET。沿W2的80业务操作/55 GET及真实S01/S04记录，不新增业务接口、鉴权、表、模型调用或部署；W4打包另步。实施与页面验证细节由[测试服务设计](test-service-and-4177-http-20261115.md)维护，本节只负责读取合同。

**页面必须保留的真实字段与跳转：** 下表业务路径省略`/api/v1/socai2`；测试路径省略`/test-api/v1`。批次中的测试用例、操作是测试记录，不等于调查业务Case或analysis task。

| 页面位置/用户要了解什么 | 已有HTTP与DTO | 必须保持的含义、跳转及空态 |
| --- | --- | --- |
| 当前看哪个环境、数据是否实时 | `/capabilities`；`/batches`、批次返回的`detail_url` | capabilities的service_version/viewer_version、environment_label、investigation_http.contract_sha256/get_operations；batch的id/environment/mode/provenance/execution_state/quality_status/updated_at，外层revision。live/archive和观察时间明确；`runtime_verified=false`是配置描述未自检，不等于当前服务失败；不能仅凭55 GET或HTTP200标全流程通过。W2 viewer_version=null是尚无页面版本，W3实际版本由测试侧提供 |
| 本批验证什么、哪些操作执行过 | BatchView.links中的cases/operations/preparation/quality-issues；Page.items/total/next_cursor/observed_at | TestCase保留use_case_id/scenario_id/status/expected/actual/operation_ids/evidence_ids；Operation保留id/case_id/intent/execution_state/occurred_at/mappings/evidence_ids。`Operation.case_id`指测试用例ID，业务UUID在mappings.subject_id；测试expected不是实际结果。按返回游标取下一页，不能把第一页当全部 |
| 进入真实分析任务 | 从mapping的subject_type/subject_id/task_id定位`/{alerts或incidents或cases}/{id}/analysis-tasks/{task_id}` | 当前mapping没有task_url/run_url，不要求不存在的字段；仅用已返回真实身份生成这个既定入口。task_id为空时不生成task链接；若仍有真实run_id，可按对应主体/Run既有路径浏览并注明未关联任务，没有业务身份时只显示测试证据。有task后沿返回status_url、attempts[].run_url、results[].url继续 |
| 是否排队、执行过几次、为什么失败/跳过 | TaskDetail.status/reason_code、kind/intent/source、submitted_at/started_at/ended_at、retry_count/next_retry_at/latest_run_id、attempts/results | status仅accepted/running/completed/failed/skipped；unknown位于attempt.outcome或Run状态，不能新增task unknown枚举。attempt保留attempt_no/local_state/outcome/error_code/error_stage/retryable及实际时间；run_id/run_url可null，results可[]。accepted可含等待重试；retryable不等于已重试，next_retry_at不保证启动时刻。S04三skip为automatic_attempts_stopped、无attempt/Run，正常显示原因 |
| 本轮调查结果与范围 | attempts[].run_url与results[].url；Case Run/Result；A/I Run的result | A/I结果链接进入同Run详情中的result，Case进入独立Result，按result_type分流；同Run请求可复用读取，不能猜最新记录代替原任务结果。mapping.run_id和用户选中Run不能被task.latest_run_id静默替换，results按source_run_id绑定；查看另一attempt时明确切换轮次及其结果/目录。Case保留run.state、result.validation_state/conclusion_state/delivery_state与业务正文；completed/accepted/uncertain/partial是不同信息。I保留input_selection和analysis_coverage，选入/遗漏/实际覆盖与当前事件成员数分开 |
| 结果还能否用于当前材料 | A/I Run的freshness/is_current_pointer/valid_for_current_input；Case详情current_assessment.input_freshness.state/reasons | 这不是任务或质量状态。S04失败I可freshness=current但valid_for_current_input=false；两Case当前stale仍可查原结果。Case当前assessment不自动等于正在查看的历史Run，分别标明来源；没有字段或没有assessment表示未提供/暂无，不能猜fresh。A历史完整输入新鲜度也不直接决定Case是否允许引用既有分诊 |
| 与哪一轮相比、为何不能比较 | Case Run的run.comparison_context / Result的result.comparison_context；顶层previous_run_url/comparison_result_url | 保留previous_run_id/comparison_result_id/state/reason_code。initial明确首轮；unavailable显示原因并保留有值的上一Run链接；整体null表示未记录，不推断首轮。只跟真实链接，不从历史排序补一个“上一轮”。当前两案是initial及两个URL均null，没有Case R2正向样本 |
| 查看全部步骤和原件 | Case Run直接提供steps_url/artifacts_url；A/I Run以相同已知主体/Run进入`/analysis/runs/{run_id}/trace`后取这两个链接；统一`/analysis-runs/{run_id}/steps`和`/artifacts` | 页面不能止于Run/trace的内嵌截断摘要。目录保留total/next_cursor/observed_at，完整翻页；steps可按kind、artifacts可按step_id过滤，换过滤重置游标。步骤seq/parent_step_id/retry_of_step_id、stage_code/kind/name/state、error/usage、实际时间与artifact_refs分别显示；0/false/[]有效，null不能当0 |
| 原答、查询材料和跨Run来源 | 步骤artifact_refs[].content_url；工件目录items[].content_url；正文响应 | 原件保留id/run_id/kind/schema_version/mime_type/size_bytes/sha256/captured_at/material_state及availability；Case元数据键artifact，A/I为metadata。按需读取content_json/content_text，不以目录存在或HTTP200认定正文可用；原答截断、空态、不可用及错误原样可查，不改写成成功结果。补答/合并按真实步骤和工件列出，不把最后一条当整轮原答 |
| 追溯本案采用的事件材料 | 原C1的`content_json.incidents[id].diagnosis_scope`→source_run_id对应工件目录→input_artifact_id对应行返回content_url | 使用W2已验真实链与来源SHA；冻结原I范围3不能扩大为当前4，单告警案交集只有1。其他Run原件保持原主体/Run路径。steps中的role=input/output/reused同样保留来源，但当前真实样本未覆盖直接reused引用，不能报已验 |
| 质量问题、测试失败和来源证据 | BatchView.links.quality-issues；batch.evidence[].content_url | quality_status/not_assessed与零问题分开；QualityIssue的stage/category/description/status/affects_flow/evidence_ids及可空run_id保持。测试脚本/投递证据走测试evidence，业务原件走业务content_url；模型NOT_PASSED/后置不能因页面读通变成通过 |
| 加载失败与刷新 | 沿上述GET；保留HTTP状态/错误码及已读内容 | 404不存在、422参数/游标错误、503服务不可用；代理502上游不可达、504超时与合法items=[]不同。账本409 cursor_stale重新加载列表，不拼接不同revision。任务accepted/running才按显式配置刷新；completed/failed/skipped停止自动轮询，unknown尝试不触发重派。切换主体/Run后不能把迟到响应混进新对象；archive显示保存时间且不悄悄取当前环境业务结果 |

**最小页面核验与可用样本：** 复用[W2实际响应](../../../docs/operations/evidence/test-http-proxy-w2-live-20261115-01/tcp-02/result.json)及HTTP[字段映射](../../../docs/operations/evidence/streaming-w3-http-cooperation-20261115-01/field-map.json)。测试自行记录必要页面动作、实际GET、响应文件/摘要及屏幕状态；HTTP按同一回执离线核字段，根侧独立看页面，三方不重复整批请求。

1. 批次正确显示环境/live、3个测试用例和7个实际操作，expected与actual、流程失败与质量问题分开；从操作进入其实际task/Run，测试case_id没有被当成业务UUID。
2. 整事件与单告警Case分别为原3/1成员，首轮completed/accepted/uncertain/partial及当前stale同时可见；Result身份来自原任务；initial/空比较显示无可比较前轮，不造R2。
3. A04 completed、I failed/model_response_not_complete、3条check skipped/automatic_attempts_stopped均可定位；无Run显示空态，I失败原答可读且未被有效结论替代。
4. 至少一份有下一页的步骤/工件列表可以继续读取，页面数量与实际total一致；原答/材料按需展开，完整内容与返回摘要一致，不把摘要截断当原件完整。
5. 从整事件C1真实来源进入原I目录和原输入，保持原run_id/content_url/sha及3条范围；页面明确是来源分析，非同Case上一轮比较。
6. 测试证据、quality问题及archive来源可区分；错误/不可用与空列表分别显示。刷新/页面启动/查看原件均不提交任务、调用模型或走SQL/SSH生成页面。运行中轮询及错误样本可用已有替身直接验证，但须标明非本批真实运行覆盖。
7. 收口给出实际test_service/viewer版本、明确profile、必要请求及画面回执；终态停止刷新、临时服务结束。当前真实样本缺unknown、超过1MiB原件、steps直接reused和Case后轮，不为补样本启动业务；可以保留已有独立证据或标本步未覆盖，不能以组件替身追认21正向通过。

**实际缺口判断：** 当前业务读取接口足够W3现有数据浏览，没有新业务路由/DTO需求；待实施的是测试服务页面、版本声明、HTTP接线、轮询和上述显示。当前账本mappings仅身份、Case/A/I返回结构不同均是已有合同，页面据此适配，不在HTTP加兼容分支。冻结来源已可按两次来源读取定位，无需为页面加入虚构链接。前置供给时W3尚未页面验收，W2和既有ASGI/组件通过不替代本步结果；实际页面读取结果见下方，S04正向更新/比较及模型质量未通过保持。

**W3实际HTTP读回与独立核对：** 测试0.3.0页面完成[同一组浏览器读取](../../../docs/operations/evidence/test-viewer-w3-20261115-01/requests.jsonl)后，HTTP侧仅[离线核40份响应摘要及关联字段](../../../docs/operations/evidence/streaming-w3-http-cooperation-20261115-01/browser-readback-review-01.json)，没有再次发请求。51条浏览器记录为48个200、1个favicon404、2个静态304；其中26个业务GET全部200、同环境及现行合同。7task/4Run、实际results来源、A/I trace、两Case当前stale及原partial/initial/空比较保持；整事件Case48工件按20/20/8三页完整读取，游标连续且与W2目录一致。C1、原I输入和I失败原答与W2原件相同，来源Run/返回content_url/SHA和冻结3成员没有扩大到当前4成员；3条skip仍无attempt/Run。初次F05导航混入另一TestCase的问题保留发现记录，修为每页按Operation.case_id再次筛选。临时服务及SSH结束、端口关闭、账本前后相同，终态30.94秒无新请求。业务HTTP/模型/数据库结构未改，未部署或切换4177。页面整体效果和独立审阅由测试及调查负责人收口；真实unknown、大原件、steps直接reused、Case后轮及模型质量未在本步核销。

W3[测试最终冻结回执](../../../docs/operations/evidence/test-viewer-w3-20261115-01/acceptance.json)已给出0.3.0及23文件摘要；HTTP[离线核对](../../../docs/operations/evidence/streaming-w3-http-cooperation-20261115-01/final-freeze-review-01.json)一致，原51请求未增加。末尾的终态恢复、运行/中断恢复与嵌套目录轮询处理、C1本案交集摘要仅有受控/离线验证（8 Python/8 JS及保存源），未重新启动浏览器；和前述26业务GET真实验证分开记录。没有业务合同、服务部署或4177切换。

#### 最终验收从Kafka实际主体接入HTTP

负责人进一步明确：最终端到端必须从Kafka真投递开始，包含消费/落库、告警事件归并、事件路由及上下文路由、A→I→业务HTTP建案关联→Case首轮/持续更新→HTTP读回。独立Case/事件、native入口和ASGI直接测试保留其原范围，不能代替这条链。以下路径均省略`/api/v1/socai2`，已与候选OpenAPI核对；执行前仍须确认实际TCP目标及同版合同。

| 衔接步骤 | 实际来源与HTTP路径 | 必须核对的业务结果 |
| --- | --- | --- |
| Kafka投递→Fusion/调查持久化 | 生产者保存本批原文摘要及topic/partition/offset；从实际fused/持久化回执取得canonical alert ID、incident ID和来源身份，再`GET /alerts/{alert_id}`、`GET /incidents/{incident_id}` | Broker ACK只证明接收，不能当落库/分析成功；上游source_alert_id不能替代canonical UUID。核原事实、材料和来源一致，缺映射登记阻断，不从expected预造身份 |
| 核对事件归并及路由 | `GET /alerts/{alert_id}/records/incidents`与`GET /incidents/{incident_id}/records/members?limit=50&offset=0`，按分页读取全部；保留真实Fusion决策与事件映射 | 双向关联及全量成员与原投递和已定归并规则一致；实际分成多个事件就如实记录。错误归并必须作为失败处理，不用HTTP重关联或直写表把结果修成预期 |
| 上下文来源→实际分析输入 | 上下文按来源模块的真实导入/查询合同准备；沿告警`records/source_artifacts`、A/I/Case Run返回链接及`/analysis-runs/{run_id}/steps`、`/analysis-runs/{run_id}/artifacts`进入`content_url` | 对照实际source_event_ids、对象/时间窗、事件路由与查询回执，确认相关上下文到达正确分析；周边日志不能全部伪装为告警直接来源。未查/查空/失败分开，查询回执与实际模型业务输入分别核对；来源模块补自己的真实路由证据，HTTP不创建内部查询入口 |
| A→I自动任务与结论 | `/alerts/{id}/analysis-tasks`、`/incidents/{id}/analysis-tasks`→各自任务详情→返回的run_url/result url；对应`/alerts/{id}/analysis/runs/{run_id}`、`/incidents/{id}/analysis/runs/{run_id}` | 自动首轮由实际消费/调度产生，不调用退役E36或手动I诊断补齐自动链。I来源使用本批实际A，选入/覆盖及失败如实返回 |
| 业务HTTP建案/关联 | `POST /cases`传本批真实incident_ids或alert_ids；需要关联既有案时`POST /cases/{case_id}/associations`并使用GET取得的范围版本；保留独立operation_key | 201/200返回真实allocations、incident_receivers及initial_task。沿case_url/status_url读取实际新案与首轮，不直写Case、成员、task、Run或结果来补链；整事件与单告警关联分别验已确认范围规则 |
| Case首轮及后续自动更新 | 首轮沿initial_task.status_url→attempts[].run_url/results[].url；整事件后续变化继续通过Kafka投递本批新告警，沿实际新A/I及Case任务读取 | 新I业务变化后仅对应活跃Case自动检查；单告警不扩员、不因晚到A或所属I更新直接重跑；当前成员与冻结Run范围分开，F1范围不扩大。不能用手动check代替自动触发来报通过 |
| 显式操作及最终保存读回 | 独立标注的手动变体使用`POST /cases/{case_id}/investigations`或`POST /incidents/{incident_id}/diagnose`；结果沿`/cases/{case_id}/runs/{run_id}`、`/cases/{case_id}/results/{result_id}`及工件链接读取 | 同task追溯原请求/尝试/保存结果，核原件、前轮比较、覆盖及状态。手动变体不冒充自动链；GET不触发模型，原结束批次不重派，失败/旧结果保留 |

准入供给按现有IF00/01/02/04–08/13分工：调查/入站方提供同版Kafka生产消费配置及实际身份映射，来源方提供上下文入源/路由/查询回执，HTTP提供上述实际TCP路径、OpenAPI、受理/读取合同及无鉴权配置，测试方用独立预期核归并/路由与业务结果。批次映射沿既有`identity-map.json`设计记录真实source→canonical→incident→Case→task→Run→result及上下文来源，不能由expected反写。缺来源、错误映射、路由错误或尚未提供目标环境均留具体阻断，不手造关联/结果或以独立接口成功核销。当前仅更新方案，没有投递Kafka、写业务数据、启动消费者或部署。

**产品效果：** 用户可以明确检查案件是否有新材料，或要求再调查一次；调用后立即获得任务身份，通过原任务持续查询。检查无变化不产生模型Run，再次调查允许相同材料明确重做。结果既说明本轮发现，也明确相对于哪轮实际调查比较；上一轮失败、无可用结论时如实说明，不能把更早的采用判断当上一轮。自动检查与手动提交使用同一核心执行能力，对外不暴露调度器或内部步骤。

#### 已有合同与实际接线

| 项目 | 已有设计/代码 | 本步接线及边界 |
| --- | --- | --- |
| 手动检查/再次调查 | `POST /cases/{case_id}/investigations`；AnalysisSubmitRequest含必填operation_key UUID和mode=check/rerun；case_router已挂载，受理/执行/读回已验 | 复用AnalysisSubmissions和AnalysisSubmissionBackend；只调用AnalysisTaskService.submit，source=user及记录人取显式可信配置。核心7A/7B通过后，独占新批已由核心顺序消费并完成HTTP终态核对，不增加第二个执行入口 |
| 受理回执 | 202 AnalysisTaskReceipt：task_id、subject_type=case、subject_id、status=accepted、status_url | 相同key/请求返回原受理回执；最新状态读GET。主体运行中可受理等待，不能因没有即时名额报执行失败；不在HTTP创建Run或访问Redis/模型 |
| 任务/进度 | 现有Case analysis-tasks列表/详情；source/intent、原task身份、attempts、Run/Result真实链接 | 复用同DTO，检查无变化为skipped/no_changes；重试、归并和unknown保持真实状态。无Run时不造链接，任务不与人工tasks混淆 |
| 自动资格 | 任务列表update_state已有eligible、last_normal_completed_at、auto_expires_at、next_check_at、ineligible_reason | 由核心提供实际保存/计算值，HTTP不自己计算6小时或7天，不将eligible等同调度已启用。手动超期提交与自动资格分开 |
| Run/结果/原件 | E12、E14、统一Run目录、完整步骤/工件及content_url均已联验 | 复用读取并核任务→Run→Result→冻结输入；本轮范围和比较身份以执行前保存为准，后续新增材料/采用不回写历史 |
| 上一轮比较 | 现有Run/Result公开comparison_result_id，Result公开change_kind/change_summary；内部attempt已可存previous_run_id | 已与核心定稿Case专用comparison_context，字段/来源见下节；HTTP只在E12/E14响应顶层补两个URL，不改告警/事件共用Task或Stage字段，不按最新记录猜补 |

公开请求不接收expected_scope_revision、window_start/end、comparison_result_id、tenant、actor或kind，额外body/查询参数422。404主体不存在，409 operation_conflict/subject_closed/empty_scope，503 service_unavailable沿现有合同；不新增登录、Token或角色验证，不恢复E11/E13/E36。新挂一路后实际OpenAPI为80操作，无security要求；[候选合同](../../../docs/operations/evidence/case-update-http-20261115-01/candidate-openapi.json)及[三类Swagger](../../../docs/operations/evidence/case-update-http-20261115-01/swagger/manifest.json)已随本步开发联验更新，不代表21已经发布。

#### 核心需补足的比较供给

产品需求C6/P2要求能解释“为什么不可比较”和进入上一实际记录。单独comparison_result_id=null既可能是首轮，也可能是上一轮无结果，不能要求调用方自行从历史排序推断。双方已按[第7步整体设计](stage7-case-updates-design-20261115.md#上一轮比较与读取合同)定稿：Case RunView/ResultView的可空comparison_context含previous_run_id、comparison_result_id、state、reason_code，来源为执行前冻结的input manifest，GET不重新选择上一轮。

| context / 字段 | 确定含义 |
| --- | --- |
| 整体null | 历史Run未保存该结构；不能推断为首轮，不回填 |
| state=initial | 新首轮，两个ID及reason_code均null；后续增加Run不会改变它 |
| state=eligible | 该上一实际Run存在已选可用Result、原输入范围可读且与本轮有交集；两个ID均非空，reason_code=null |
| state=unavailable | 保留previous_run_id，comparison_result_id=null；reason_code为previous_result_unavailable、previous_input_unavailable、previous_scope_unavailable、previous_scope_not_overlapping或previous_conclusion_unusable |
| E12/E14 previous_run_url | 响应顶层HTTP专属字段，非空previous_run_id指向同案`/cases/{case_id}/runs/{previous_run_id}`；context/ID为空则null |
| E12/E14 comparison_result_url | 响应顶层HTTP专属字段，非空comparison_result_id指向同案`/cases/{case_id}/results/{comparison_result_id}`；context/ID为空则null |

E12从run.comparison_context、E14从result.comparison_context构造链接；E14同一source Run的核心context应一致。已有Run/Result的comparison_result_id须与context一致。其他Case详情/列表/历史/故事/采用读侧复用核心四字段和同一冻结来源，可沿既有Run/Result身份进入E12/E14，不新增HTTP字段到核心。失败或unknown已本地结束也可能是上一轮，不能回退到更早正常/已采用轮次。

“是否有新材料”的最近正常完成输入基线与上述上一实际调查不是同一对象。前者由核心负责check去重及完成覆盖；后者供结论比较和解释。原结果change_kind/change_summary仍描述业务变化，不拿task状态或结果ID变化替代。若当前持久记录不足以稳定读出比较原因，核心在设计中明确保存位置；不让HTTP访问内部数据库自行重算，也不做旧版本兼容回退。

#### 按依赖逐步实施和直接验收

| 子步 | 依赖、修改和本步结束条件 | 必要验证/证据 |
| --- | --- | --- |
| 7.1 设计与合同对齐 | 核心明确内容变化比较、周期跟随/期限、上一轮选择和比较摘要供给；HTTP核现有端口、DTO、路由及数据来源，补本节。双方记录确定的字段/用例，strict通过后再开始对应实现 | 源码核查和合同/设计链接；具体实现缺口保留，不以CLI通过宣称已供给 |
| 7.2 手动check/rerun及读取闭环 | 核心先提供可调用的真实更新执行器与新独占样本/profile；HTTP接Case比较读取并挂case_router，复用既有受理、任务及第6步完整读取 | 同一新案首轮完成→POST check无变化→skipped且无新增Run；正常材料/H变化后的check→新Run/Result；相同材料明确rerun→独立任务/Run。沿公开回执读回、核SQL来源及前轮身份，重放原key不增加任务/执行；消费由核心显式驱动，HTTP不自启 |
| 7.3 核心边界的HTTP定向读回 | 复用核心本步已结束的边界样本，不重新构造/消费故障矩阵；只补7.2未覆盖的真实读取 | 上一实际轮失败/unknown且无可用结论→不可比较且可定位原Run；不回退更早结果。自动活跃接收Case/旧Case、成员冻结、有效H/同值管理变化、超期/关闭/重开及运行中新采用按实际样本读取，核范围/资格/比较/采用来源，失败原件保持 |
| 7.4 本步文档收口 | 7.2/7.3通过后生成新候选OpenAPI/三类Swagger，更新输入输出示例、实现状态、配置/发布片段和功能清单 | 复用可信/分层/字段边界检查，核A/I合同保持，Case POST已挂、旧入口仍404；只读前后核本批直接涉及的记录，记录实际HTTP及模型次数。IF08只补development证据，21 runtime仍待统一发布 |

7.2受理错误复用既有`test_socai2_analysis_submission_pg.py`与第4步有效证据，只补Case真实应用路径：同key换mode/主体409、closed/empty拒绝、非法/额外字段422、无凭据受理，以及原task跳过/完成后重放仍返回accepted回执。若新增Case专用比较结构，仅核Case E12/E14和其来源，不能顺带更改告警合同。读取前后摘要限实际涉及的Case、任务/尝试、Run/Result/工件及本步人工反馈来源等，不重跑全仓/全库。

核心负责新批数据、真实执行器和保存、周期跟随及模型/工具；HTTP负责外部适配、路由、DTO、URL和Swagger/指南；测试模块沿既有[单点到集成方案](full-flow-test-plan-20261115.md)维护IF08供给及最终用例。不复用第6步已结束批次做新执行，不因开发验证开启21/旧本机服务，不新增真实模型质量采样。后续真实模型、TCP、4177及结束审计仍归第11步已确认范围。

当前直接结果见[本批回执](../../../docs/operations/evidence/case-update-http-20261115-01/README.md)：挂载后15项受理/可信/分层检查通过；真实PG只读发现HTTP误把核心RunView/ResultView当字典，修正为读取结构化对象后，8项实际对象替身回归及28次真实GET通过，19类记录摘要不变。原失败保留，未重派已结束任务。独占新案20请求通过，保存initial/check/rerun三个accepted任务、0attempt/Run/Result，重复key与错误请求均未多建；随后核心唯一消费三个原任务，41次终态读取/原key回放通过，保存2Run/2Result，check无变化不建Run，21类记录摘要不变。7A初始/可比/前轮失败不可比、有效H及同正文新修订已由核心执行并由HTTP只读核对；7B两个已结束批次又经47次HTTP只读，3案10Case Run、唯一事件接收者及closed资格与保存一致，每批23类记录摘要不变。真实查询中的observed_at随读取变化，测试仅对此Run顶层时间放宽，Result不假定有该字段；两次原断言失败保留，业务代码未变。第7步HTTP片段、80操作三类Swagger、实际示例及交接均已更新，新案保存快照加入仓库归档页（25案，实际4177未切换）。本步开发供给完成，21仍awaiting_release，正式候选TCP/真实模型/结束审计留后续。

#### 第7步完成后的测试交接

与测试模块[环境落实安排](full-flow-test-plan-20261115.md#51-第7步之后候选验证正式发布与读回)对齐：第7步供给收口→21隔离候选准备及就绪复核→单点/HTTP合同/局部链/完整链及定向修复→第11步交付和独审→调查负责人正式发布→发布后读回。隔离候选验证与正式发布分别留证；开发ASGI不替代候选实际TCP验证。本段只补交付责任，不启动部署、资源准备或测试执行。

HTTP侧第7步交付包须包含：与核心冻结版本一致的OpenAPI/三类Swagger及摘要；check/rerun、比较读取的请求/响应/错误与已验证样本身份；实际代码及配置依赖清单、无鉴权业务上下文和任务/读取policy的路径要求；直接验证回执及未验边界。源码片段不是可执行部署profile，不能仅按操作数量判断就绪。

调查/发布方确定21候选profile和隔离资源后，HTTP侧核实际base_url、端口、服务版本、配置来源及同环境测试身份，把**实际可访问的TCP目标**交给测试模块；未分配时明确待提供，不编造地址，不把旧18024、历史候选端口或开发样本ID当本期环境。数据库/迁移、Topic/group、Redis namespace及候选部署由调查/发布方统筹，HTTP仅供自身依赖，不自行迁移正式库或开启消费者。第7步完成回执前测试侧保持计划/既有证据核对；IF08 development与21 candidate/runtime就绪分别更新，旧T1回执不改写。
