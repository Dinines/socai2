# 分析任务列表与详情接口

2026-11-15更新：六个GET已纳入当前21候选18424及18480 Swagger，实际80操作、无鉴权，旧18024/18080已停止。[S01-r3的4条initial任务](../operations/evidence/streaming-ingress-http-20261115-02/README.md)已完成实际TCP非空读取，该入站时为accepted、无attempt/Run；后续[62次真实A/I读回](../operations/evidence/streaming-ai-http-20261115-01/README.md)已核4任务各1attempt/Run并completed、旧4任务closed_before_start及1天资格截止时间。模型正文质量仍NOT_PASSED；步骤按[本步HTTP计划](../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#已有ai任务执行后的http联验2026-11-15)完成，两Case首轮随后已真实保存并完成58GET，整个change审计仍待。此前隔离PG/ASGI验证保留原范围；最终正式发布与整个change验收仍待。本机旧服务本轮未操作。

11-15[告警自动分诊查询联验](alert-auto-http.md)已完成，候选移除旧E36；当前[第7步80操作合同](../operations/evidence/case-update-http-20261115-01/candidate-openapi.json)已包含Case check/rerun提交及读回。[Case首轮执行和读取](case-initial-http.md)沿既有入口；第8–10步定向、手动综合和知识后台异步维护后置，不因任务枚举已存在就开放入口。第7步审计F1–F5已有本机修复及同源HTTP证据，最终21端到端及独立结束审计仍待，不代表正式服务已更新。

S04实际[失败路径44次GET](../operations/evidence/streaming-s04-http-20261115-01/README.md)已通过：新增A04 task完成，I check因model_response_not_complete失败且retryable=false、retry_count=0、next_retry_at=null；后3个check为skipped/automatic_attempts_stopped，无attempt/Run。事件update_state.eligible=false、ineligible_reason为原失败原因；单看next_check_at不代表仍会执行。没有Case新任务或后轮，S04成功更新仍未通过。

## 功能和入口

分析任务记录“这次分析是否受理、是否开始、重试了几次、最终到哪里看结果”。它不同于用户创建的人工核实任务：人工事项仍走`tasks`，这里走`analysis-tasks`。GET只读取，不提交调查、不调用模型、不启动自动调度。

| 对象 | 列表GET | 详情GET |
| --- | --- | --- |
| 告警 | `/api/v1/socai2/alerts/{subject_id}/analysis-tasks` | `/api/v1/socai2/alerts/{subject_id}/analysis-tasks/{task_id}` |
| 事件 | `/api/v1/socai2/incidents/{subject_id}/analysis-tasks` | `/api/v1/socai2/incidents/{subject_id}/analysis-tasks/{task_id}` |
| 案件 | `/api/v1/socai2/cases/{subject_id}/analysis-tasks` | `/api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}` |

subject_id和task_id均为UUID。任务须属于路径中的对象。无需登录或Token，使用服务显式配置的内部可信业务上下文。

列表接受可选limit、cursor：默认每页50，最多100，均来自任务policy；cursor为上页next_cursor，最长4096字符，不能跨对象/租户使用。按submitted_at DESC、task_id DESC排序，可改变合法页大小。详情不接收查询参数；未知或重复参数均422。

## 状态和操作结果

| status | 表示什么 |
| --- | --- |
| accepted | 已受理，尚未开始或已安排重试；用next_retry_at和reason_code区分 |
| running | 调查侧实际仍在执行，包括尚未产生Run的准备阶段 |
| completed | 该任务流程正常完成；不代表结论确定、模型质量通过或结果已采用 |
| failed | 任务已经结束且失败；原因和每次尝试保留。Run结果unknown在本地收尾后可对应此状态 |
| skipped | 本次待执行工作或后续重试已跳过，例如no_changes无变化、closed_before_start开始前已关闭；此前若有失败尝试，仍保留在attempts中 |

2026-11-15补充：原任务等待重试时，若另一次明确重跑已处理相同材料，原任务可变为skipped/no_changes；原失败Run和attempts保留，retry_count不增加、next_retry_at清空。skipped不等于从未尝试，更不表示此前失败已修复。已用[真实调度回执校验HTTP响应合同](../operations/evidence/analysis-task-http-20261114-01/skipped-retry-contract-20261115.json)，字段未增改。

每次自动重试保留同一task_id，产生新的尝试序号及可能的新Run。尚未产生Run时latest_run_id/run_url为null，不能把排队当成正在分析。最新目标是不同请求分别排队、相同operation_key同内容只重放原请求；取消不同task归并及历史Case手动检查已在F4新批通过，见下方边界。已保存旧归并记录按原身份/真实关联读取，不改写历史，也不能把原归并测试当作F4已通过。

### 不同检查请求和无变化结果

F4已完成[89次同源HTTP读回](../operations/evidence/case-trigger-fix-20261115-01/http-readback.md)，本项本机直接验证通过，整体change尚未验收或正式发布；代码已进入21候选。业务后端按以下语义处理原任务，不自行合并：

- 同一个 operation_key、相同请求内容：重放原受理回执；最新进度仍 GET 原 task_id。
- 新的 operation_key：独立任务，同一案件串行；等待期间对外仍为 accepted，不新增 pending 状态。
- 普通 check 开始前比较实际材料；已被前轮处理则 skipped/no_changes，可没有 attempt、Run 或 Result。这表示本次检查未启动调查，不是查询失败。
- 手动 check 应检查全部适用事件，自动 check 只看符合自动规则的活跃事件；不能用自动任务代替手动任务。新批已确认自动跳过、手动完成并保存Result；手动使用新事件诊断时仍保留本案原告警范围。旧批failed/unknown继续保留。
- 整事件关联仅在有效事件诊断发生业务变化后推动活跃案件；单告警关联保持原范围，不因首个分诊晚到或所属事件诊断更新自动重跑。调用方不额外发手动 POST 来补成自动流程。
- 同案件原任务等待重试时，新的普通检查保留独立身份并等待；原任务针对相同材料重试耗尽后，新检查可 skipped/automatic_attempts_stopped，无attempt/Run。这不等于no_changes；它表示相同材料的自动尝试已经停止，不由业务后端换key继续重试。明确rerun仍按已有人工重跑规则处理。

### Case已知故障的一次重试

F3已通过[52次同源HTTP只读验证](../operations/evidence/case-retry-fix-20261115-01/http-readback.md)，已进入21候选、正式发布仍待。仅确认请求未发出的可重试连接/连接池故障，在没有其他未决调用时按已冻结配置安排重试；当前规则默认60秒、最多一次。调用方持续GET原task，不另发POST补重试。

| 情况 | 任务、尝试和结果如何展示 |
| --- | --- |
| 等待重试 | status=accepted、reason_code=retry_scheduled，next_retry_at给最早可执行时刻；内部waiting不新增为公开状态。retry_count只计已经开始的重试 |
| 重试成功 | 同task两次attempt、两个Run；先前failed保留，后一次completed另存结果。不能把第一次失败改成成功 |
| 一次重试耗尽 | status=failed、reason_code=retry_exhausted，retry_count=1、next_retry_at=null。单次attempt的retryable仍可为true，只说明故障分类，不表示还有下一次重试 |
| ReadTimeout等结果不确定 | task本地已结束可为failed/call_timeout，attempt为ended/unknown且有local_ended_at，原Run仍unknown且ended_at可为null；不自动重试，不据此把任务一直显示为running |
| C6失败但C3已完成 | C3原件仍沿原Run步骤/工件读取，C6故障单独保留。已有部分工件不代表整轮成功，也不需要调用方手动补内部阶段 |

本批核心使用测试时钟验证冻结60秒门槛，HTTP读取的是最终保存状态及原等待快照，不冒称正式服务实时观察或真实模型连通性通过。

## 任务详情字段

列表items与详情使用相同TaskDetail结构：

| 字段 | 含义 |
| --- | --- |
| task_id、status_url | 原受理ID及本任务详情地址；刷新页面后可据此找回 |
| subject_type、subject_id | alert/incident/case及实际对象ID |
| kind | alert_triage告警分诊、incident_diagnosis事件诊断、case_investigation案件调查；不包含内部知识同步任务 |
| intent | initial首次、check检查更新、rerun重跑、targeted定向、synthesis综合；后两类提交能力仍待后续实现，枚举存在不代表已可提交 |
| source | ingress入站、case_create建案、periodic周期、user用户、knowledge知识；沿真实受理记录，不猜来源 |
| status、reason_code | 上表业务状态及具体原因；无额外原因时reason_code为null |
| submitted_at | 本任务原始受理时间，归并后仍保留 |
| started_at、ended_at | 实际开始和本地终态时间；未发生为null，不用排队时间伪造开始 |
| request | 原业务请求；当前initial/check/rerun为{}。不返回operation台账、队列、输入摘要或内部task整行 |
| retry_count | 已实际开始的重试次数，首次不计；安排了但未开始不增加 |
| next_retry_at | 已安排重试的最早时间；不是保证启动时刻；没有则null |
| latest_run_id | 最近实际尝试所关联的Run ID；从未产生Run则null |
| attempts | 按attempt_no升序的全部实际尝试，未开始为[] |
| results | 实际保存结果的引用，未产生为[]；含各次尝试结果，不生成假成功结果 |

attempts每项：

| 字段 | 含义 |
| --- | --- |
| attempt_no | 从1开始的尝试序号，不暴露数据库attempt ID |
| run_id、run_url | 本次实际Run及详情链接；准备阶段尚无Run或准备失败时均可为null |
| started_at | 该次尝试实际开始，可能早于Run创建 |
| local_state | running实际运行、ended本地结束、interrupted已观察中断；只读真实保存状态，中断恢复接线仍属调度后续工作 |
| local_ended_at | 本地实际收尾时间；未收尾为null，不是原Run的ended_at |
| interruption_observed_at | 实际观察到中断的时间；没有为null |
| outcome | completed/failed/unknown；仍执行中为null |
| failed_at | 记录失败/未知结果的时间，无则null |
| error_code、error_stage | 保存的原因码和阶段；无则null |
| error_detail | 可空对象，允许exception_type/http_status/stage/code等受控明细；不是原始异常堆栈、提示词或凭据 |
| retryable | 是否属于可重试的已知失败；仍受剩余次数、主体状态等限制，不等于已经再次执行 |

results每项为`{result_type,id,source_run_id,kind,url}`。result_type为alert_assessment、incident_diagnosis或case_result，kind取结果本身的真实类型；告警只列triage，不把human_feedback当分析结果。告警/事件url进入Run详情的result，Case url进入独立结果详情。输出URL已通过真实HTTP读回核对。

## 列表字段

列表返回`subject_type,subject_id,items,total,next_cursor,observed_at,update_state`。total是该对象全部业务分析任务数，包含归并原任务；不是本页数量。next_cursor到底为null。items与total、更新资格使用同一只读事务；跨页请求不是永久冻结快照。主体存在但没有任务时items=[]、total=0。

update_state与任务状态分别表示，**不表示自动调度器已经启用**：

`auto_expires_at`及资格判断使用读取服务当前加载的lifecycle活动窗口计算；`next_check_at`来自保存记录。21本轮HTTP已[实际挂载同批1天窗口配置](../operations/evidence/streaming-http-lifecycle-20261115-01/README.md)，与调度lifecycle一致；原7天配置保留在冻结镜像中，当前由只读挂载覆盖。既有task的冻结重试值保持，任务详情的已保存尝试/结果不重写。配置加载及同批资格摘要/真实分析结果62次GET均已通过，见[本步计划](../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#已有ai任务执行后的http联验2026-11-15)及[实际读回](../operations/evidence/streaming-ai-http-20261115-01/README.md)。

| 字段 | 含义 |
| --- | --- |
| eligible | 核心判断该主体是否满足自动更新资格 |
| last_normal_completed_at | 最近正常完成的业务分析时间，未记录为null |
| auto_expires_at | 自动资格到期时间；告警不是周期对象，为null |
| next_check_at | 保存的下次检查时间；没有为null，不保证执行时刻 |
| ineligible_reason | not_periodic非周期、not_registered未登记、closed已关闭、expired已到期或实际停止原因；具备资格时null |

## 错误与示例

| HTTP | 情况 |
| --- | --- |
| 200 | 正常任务/列表，包括任务failed/skipped；HTTP成功不代表分析成功 |
| 404 | subject_not_found对象不存在；analysis_task_not_found任务不存在或不属于此对象 |
| 422 | UUID、页大小、游标非法，跨对象游标、未知或重复参数 |
| 503 | service_unavailable，读取配置缺失/非法或数据库依赖不可用 |

业务错误结构为`{"detail":{"code":"analysis_task_not_found","message":"该对象下的分析任务不存在","context":{}}}`；FastAPI字段校验错误为422 `{"detail":[...]}`。

[实际请求/完整响应样例](../operations/evidence/analysis-task-http-20261114-01/examples.json)包括三类列表、任务状态、详情跳转和错误。样例UUID来自本机隔离合成批次，不是21数据。发布后可按下列顺序对接：列表找任务→读取status_url→有run_url时查看执行过程→有results时读取相应结果。不要以重复提交调查代替轮询GET。

## 配置、实现与验证边界

通过`SOCAI2_ANALYSIS_TASKS_CONFIG_FILE`显式选择[任务policy](../../deploy/local-investigation/analysis-tasks.json)的绝对路径。列表读default_limit/max_limit，资格摘要沿核心窗口策略；HTTP不另建一套策略。统一发布时本机填冻结运行包的绝对路径，21为`/app/config/analysis-tasks.json`，两端数据库与CPU架构分别保留。未提供配置返回503，不切换其他库。

需同一目标库的迁移128和配套核心。HTTP端口/适配器只调用核心read_task/list_tasks；来源为analysis_tasks、analysis_attempts、analysis_subject_state和实际结果/主体表，不复制表、不修改执行器。发布片段见[HTTP任务读侧清单](../../deploy/http-service/analysis-tasks-release-fragment.json)，需与核心生命周期及R1/R3片段一起并入最终profile；本轮未执行发布。

[本批证据](../operations/evidence/analysis-task-http-20261114-01/README.md)：38次ASGI请求，9任务/5Run/三类真实保存结果；14类记录读取前后摘要一致。503测试使用真实依赖缺配置，未模拟数据库宕机。没有模型/工具调用；归并关系是显式合成保存，用来验证读取，不证明自动归并调度已实现。未改业务页面，未提交/推送或重启正式服务。
