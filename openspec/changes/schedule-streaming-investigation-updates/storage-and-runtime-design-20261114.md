# 分析任务持久化与执行生命周期

2026-11-14目标设计。通用三表及本地生命周期已按增量128在隔离开发库实现并验证，见[第1步回执](../../../docs/operations/evidence/analysis-lifecycle-20261114-01/README.md)；正式环境未迁移，Redis调度、Case专用结构及公共任务接口仍待后续接入。服务内部schema为socai2；类型、空值、键和读侧来源以下文为准。V1迁移123–126及历史记录保留，实施时新增增量迁移。主要流程见[design](design.md)，内部队列见[queue](queue-dispatch-design-20261114.md)。

## 1. 保存职责

PostgreSQL保存任务、每次尝试、时间、原件关联和检查资格，是查询依据；Redis只保存可领取的task_id和正在执行的索引。Redis键存在、TTL、队列位置不能当作任务结果或自动资格。运行进程中的future/执行句柄决定本地是否实际结束，Redis运行集合是其镜像。

新增4张内部表：analysis_tasks、analysis_attempts、analysis_subject_state、case_alert_exclusions；另为incidents增加active_case_id，为cases增加第13节的续接关系/接收目标字段。case_incidents继续保存全部实际关联，不另增follow_new_alerts与事件指针重复表达活跃目标。Case相关结构随阶段4实施；现有runs、run_members、artifacts、results、assessment/diagnosis、case_activities及人工tasks/task_revisions继续使用，不新增Case分组表或告警活跃目标字段。

以下表中的NN表示非空，?表示可空；所有时间为timestamptz，ID为UUID，计数/序号有非负或正值检查。tenant_id与主体ID分别保存，不拼接成长业务ID。跨表引用须同时检查租户和实际主体。

## 2. analysis_tasks：持久受理记录

| 字段 | 类型/空值 | 含义 |
| --- | --- | --- |
| id / tenant_id | uuid NN | 对外task_id、租户；主键(tenant_id,id) |
| kind | text NN | alert_triage / incident_diagnosis / case_investigation / knowledge_sync |
| subject_type / subject_id | text、uuid NN | alert/incident/case及原主体ID；kind与type有对应检查 |
| intent | text NN | initial/check/rerun/targeted/synthesis；targeted/synthesis仅用于case_investigation且source=user；retry不是新的外部意图 |
| source | text NN | ingress/case_create/periodic/user/knowledge，按实际来源记录 |
| operation_key | uuid NN | 受理幂等键；外部传入，内部由本次来源操作产生并在重送时复用 |
| request_hash | text NN | 主体、意图及实际请求字段摘要，不含变化中的当前材料 |
| request_payload | jsonb NN | 按intent校验的业务参数；普通请求为空对象，定向保存问题/显式范围/工具，综合保存所选定向result_id；不是排队时复制的全量材料 |
| submitted_at / submitted_by | time NN、uuid ? | 真实受理时点；系统触发的操作人按配置/既有约定 |
| state | text NN | accepted/waiting/running/completed/failed/skipped/merged，内部状态 |
| reason_code / error_detail | text ?、jsonb ? | 原因及必要脱敏错误，不存凭据 |
| merged_into_task_id | uuid ? | 仅merged时指向同主体有效根任务；禁止自指/循环，只允许归入未运行待办 |
| retry_count | integer NN | 已实际启动的自动重试次数，默认0；排队/扫描不加1 |
| retry_limit / retry_delay_seconds | integer NN | 受理时策略快照；新通知不重置已有根任务策略 |
| next_retry_at | time ? | 已安排故障重试的最早时间，终止/开始重试时清空 |
| started_at / ended_at | time ? | 根任务第一次实际尝试开始/最终本地收尾；从未执行的跳过started_at为空 |
| observed_input_digest | text ? | 检查时观察到的材料摘要，仅触发/防止重复自动失败，不是本轮分析范围 |
| source_run_id / source_result_id | uuid ? | 知识维护的真实A来源；分析任务不借此伪造已执行 |
| last_enqueued_at | time ? | 最近成功追加Redis的时间，仅投递记账 |

唯一键(tenant_id,kind,operation_key)用于同操作重放；内容不同409。建立主体+submitted_at的查询索引及state索引；**不建同主体只能有一份等待task的唯一约束**。数据库主体外键按kind校验，可用约束触发器复用现有租户校验模式；不可让任务引用不存在/跨租户主体。合并关系只由单一调度器维护，原触发记录不删除。

新外部任务成功持久化即受理。Case创建与首轮任务在同一个本地PG事务保存，成功回执记录到既有幂等活动；事务失败不返回虚假task_id。后续Redis追加失败不撤销已经保存的Case/task，保留可查询受理状态并由调度循环补投。其他已有业务写入只在原数据库事务登记直接需要的任务，不要求跨服务事务。

## 3. analysis_attempts：实际尝试记录

| 字段 | 类型/空值 | 含义 |
| --- | --- | --- |
| id / tenant_id / task_id | uuid NN | 内部尝试身份、租户、实际根任务；不新增公共第四层ID |
| attempt_no | integer NN | 同根task从1递增，唯一(tenant_id,task_id,attempt_no) |
| subject_type / subject_id / kind | text、uuid、text NN | 从task复制用于串行约束，必须与task相符 |
| run_id | uuid ? | 本次分析Run；准备失败或知识维护可空；非空Run不能属于另一attempt |
| source_run_id | uuid ? | 仅知识维护引用源A，与本次run_id不同 |
| local_state | text NN | running/ended/interrupted |
| started_at / local_ended_at | time NN、time ? | 本地实际开始与实际收尾；ended必须有local_ended_at |
| interruption_observed_at | time ? | 重启发现前进程中断的时刻，不冒充准确结束时间 |
| outcome | text ? | 完成后completed/failed/unknown；运行时为空 |
| failed_at / error_code / error_stage | time ?、text ?、text ? | 每次故障发生时点、分类和阶段，不被后续成功覆盖 |
| error_detail / retryable | jsonb ?、boolean NN | 脱敏上下文；只有明确分类可重试，默认false |
| input_artifact_id / input_digest | uuid ?、text ? | 真正开始前固定的材料清单及业务摘要；无法准备时为空 |
| previous_run_id / comparison_result_id | uuid ? | 实际上一轮与其可用结论；上一轮无结果不向更早回退 |
| policy_artifact_id | uuid ? | 实际Run/维护策略工件，关联原配置快照 |

只在决定实际尝试后创建，纯无变化/关闭跳过无attempt。期限内已受理的首次尝试不会因排队跨期被跳过；已失败后等重试的超期则停止。准备阶段开始后失败也应有attempt，但不得伪造Run、模型调用或输入。正常结束/失败/unknown均可local_state=ended；本地生命周期与模型结果分开。

对(tenant_id,subject_type,subject_id,kind)建立local_state=running的唯一索引作为数据库串行保护；alert_triage与knowledge_sync职责不同，但均受总N限制。N由唯一调度器本地活动集合控制，不做多个领取者之间的分布式额度事务。

## 4. analysis_subject_state：检查时间与失败停止依据

主键(tenant_id,subject_type,subject_id)，仅A/I/Case分析主体，不给知识维护另建自动扫描对象。

| 字段 | 类型/空值 | 用途 |
| --- | --- | --- |
| registered_at | time NN | 新建主体登记检查状态的时间；不增加旧对象启用标记 |
| next_check_at | time ? | I/Case下次检查；A无周期扫描 |
| last_normal_completed_at | time ? | 最近正常完成时点；Case只取全案baseline完成，定向不续期，非质量通过声明 |
| last_completed_attempt_id | uuid ? | 查实际完成输入/覆盖，不能指向失败/unknown或局部targeted |
| last_attempt_id | uuid ? | 最近真实尝试，用于运行历史定位（上一轮比较仍读取真实Run历史） |
| stopped_input_digest / stopped_task_id | text ?、uuid ? | unknown、不可重试或次数耗尽时的实际/已观察材料摘要及来源；未覆盖标记 |
| automatic_stop_reason | text ? | 自动停止原因；准备失败连摘要都无法建立时保留无摘要停止 |

自动期限由last_normal_completed_at或主体created_at加当前profile窗口计算，不额外维护Redis TTL。开放/关闭读原业务表；列表读侧计算eligible、auto_expires_at、next_check_at和不合资格原因。配置变化按下一次检查使用，已有任务重试策略不倒改。

eligible表示能否新受理自动检查，不代表已受理任务必须取消。七天内已受理的首次尝试即使排队跨期仍可执行，领取时保留跨期事实和实际资格观察；本轮失败后不自动重试，过期的待重试任务终止。正常完成仍用真实完成时间刷新窗口；关闭检查、最新已有范围、同主体串行及N保持。接受这一轮不放行过期后的新自动扩案/续建。无需新增超期任务队列或人工解除状态。

扫描和领取均先构建当前业务摘要。与last_completed_attempt实际输入相同则no_changes；与stopped_input_digest相同则automatic_attempts_stopped；摘要确实不同才允许新自动任务。已有停止原因但当前无法取得可靠摘要时，不猜“新材料”并自动重试，保留原因，其他主体继续。明确手动rerun可重新尝试；无需人工解锁/核实动作。Case此处的完成/停止摘要属于完整调查，targeted局部结果及synthesis前序不足不写入这些标记；实际全案输入的综合失败才沿完整调查规则处理。

容量不足的停止判断另核原attempt保存的容量配置：同有效输入且配置未变不重复尝试；相关容量配置已变时允许重新预检，实际可执行才恢复处理，不给未知故障普遍重置重试额度。复用停止task关联的策略/测量工件，不新增恢复表。

新主体自动首轮没有已完成输入时按本轮实际选定范围分析，不伪造既有覆盖。Case上一轮比较仍读取同案真实Run历史。仅正常完成才推进last_completed_attempt/last_normal_completed_at；I按选定范围完成不代表覆盖全部事件成员。终止失败保存停止摘要，不冒充成功覆盖；新材料后正常完成清除旧停止标记，原失败task/attempt仍保留。本期不识别或迁入上线前旧对象，不保留旧对象手动/批量激活分支；负责人计划自行准备空库，本设计不执行清库。

## 5. 跟随、排除与材料清单

incidents增加active_case_id uuid NULL，默认NULL，指向同租户cases，并要求存在对应case_incidents关联；按tenant_id/active_case_id建立反查索引。它是事件后续告警及I结果自动更新的唯一接收目标，不是执行状态。case_incidents保留事件与多个独立Case的全部关系；不新增每条关系的follow_new_alerts布尔值。没有明确Case关联时目标为空，明确整事件操作时指定，不猜选。告警沿case_alerts可关联多个Case，不添加active_case_id或全局唯一归属约束。

明确整事件新建/关联将其活跃目标设为本次实际接收Case，保留旧关系；同key重放不回拨目标，普通check/rerun和单告警关联不切换目标。达到case.max_alerts并续建时，同事务仅将active_case_id仍等于旧Case的事件转到新Case，并保存新的事件关联；已经属于其他独立Case的活跃目标不动。scope_revision和case_activities继续记录真实成员/目标变化，不为每次变化预建pending Run。

case_alert_exclusions字段为tenant_id、case_id、alert_id（联合主键/同租户外键）、excluded_at、excluded_by、operation_key；记录当前显式排除，操作历史仍写case_activities。续接分配查询同一最初Case下的既有成员和排除记录，不能把旧Case移出的告警又自动加入后续Case；明确重新添加才取消相应排除并分配至当前接收Case。独立Case串之间不扩大排除。原活动不删，事件成员变化不能删除/绕过排除。

在现有artifacts中保存本轮内部输入清单，不将其整个透传给模型。清单至少含实际告警成员身份、原材料引用及可用性、选入A的业务值/结果身份/来源、Case实际相关且选入的I诊断业务值/结果身份/覆盖范围/可用性、有效人工输入原文/范围/引用及capture时间。原材料现有版本仅供追溯，不新增来源版本判断或提交入口。摘要对确定排序的实际业务部分计算，来源ID/时间等仅追溯字段不单独触发，不比较全数据库对象，也不增加模型价值判断。

I输入清单不包含自己的诊断输出；Case清单不包含本轮自己的结果作为新材料，避免自循环。I无论来自手动接口还是告警驱动诊断，其新结果只参与该事件当前活跃Case的自动触发比较；历史关联Case不能因扫描全局最新I而轮番自动更新。活跃指针本身不算材料变化，切换后按新目标实际范围/上游业务输入检查。手动调查仍可按本案原范围使用适用I，保留prior_analysis和原覆盖；更大事件诊断不扩大Case成员。旧Run仍引用当时I结果；已有告警晚到首次A、有效H规则保持。已有A/I原件及可用性结构复用，不新增结果版本表或改变告警公共字段。

模型/模块实际输入、初答/补答、工具回执、原输出和保存装配沿既有工件单独保留。业务摘要只用于变化检查，不能代替完整原件、质量诊断或现有采用新鲜度校验。

## 6. Run约束如何调整

现有123迁移含runs_one_pending_baseline、runs_one_active_baseline（running/unknown）、guard_run和runs_end_fields；baseline_store.claim/结案检查也将unknown当活动。只增加Redis队列而不调整这些点，会让旧unknown继续挡住执行。

目标增量迁移与核心修改：

1. E01/成员变更不再创建pending Run。Case在实际执行准备事务里创建pending_update、写完整成员/输入并领取running；保留内部guard_run要求，不暴露prepare/start步骤。
2. 原baseline活动唯一索引调整为running约束，unknown不再永久阻塞；新attempt活动索引核实际本地活动。claim、结案、采用预览都依据actual attempt/本地占用，不仅看Run枚举。
3. 保留runs_end_fields语义：旧unknown的ended_at仍为空，**不修改历史unknown为failed、不补假结束时间**。本轮实际本地结束写analysis_attempts.local_ended_at，任务记failed/call_timeout等原因。
4. A/I通过各自begin创建一次Run并关联attempt；避免先建Run导致begin认为幂等重放而不执行。自动重试使用新执行operation_key（可由task_id+attempt_no内部派生），外部task的operation_key不变。
5. 统一切换时停用旧执行入口及旧分析消费者，确认旧本地执行进程已结束再启唯一调度器。历史Run无attempt也仍可读，不伪造新attempt/时间；历史unknown不阻塞新队列。重启处理仅见下节最小规则。
6. 阶段4增量加入RunKind/ResultKind的targeted，按真实局部材料保存成员及输入，不套用baseline的完整结果守卫或ai_question会话要求；普通调查与synthesis仍走baseline。新枚举同步来源外键/作用域检查、历史读取及采用资格，不能只改Python枚举。所有Case类型仍受同一attempt串行约束。

Case尚有本地实际running阻止结案；已结束unknown允许按既有业务条件结案。排队任务不占槽，关闭后领取记skipped/closed_before_start。原未完人工任务确认规则保持。

## 7. 本地收尾与最小重启处理

正常异常/超时统一在执行器finally记录真实结束，再释放运行集合；完成事件由同一调度线程处理，不让执行线程直接读写队列。若数据库写回暂失败，释放本地名额并保留可重写的收尾回执，不重派模型；任务读侧明确保存尚未确认，不能报成功。该短回执补写不增加模型重试次数，不建设恢复平台。

进程重启必须先确认旧唯一调度进程已退出（部署层单实例约束，不增加业务人工核实流程）。将其遗留running attempts标记interrupted、记录发现时间；已有Run仍running的标记unknown并留原输入，不能伪造准确结束时间。任务failed/executor_interrupted，停止同材料自动重试，清理本命名空间活动索引，再继续其他任务。未开始的accepted/waiting任务按原状态/重试时间补入Redis，重复可接受；不清历史数据、不FLUSHALL、不重跑已终止任务。

## 8. 对外字段来源与错误

| HTTP字段/内容 | 持久化来源 |
| --- | --- |
| task_id、subject、intent、submitted_at | 原analysis_tasks行；幂等重放保持同ID |
| status、reason_code、起止、next_retry_at、retry_count | 有效根任务及真实attempt投影；waiting/merged不作为公共枚举 |
| latest_run_id、attempts（attempt_no/run_id/时间/原因） | 根任务的analysis_attempts；无Run时null；列表不暴露内部attempt UUID |
| 结果ID/URL | 按实际run_id查Case results、A assessment、I diagnosis，不猜目标结果 |
| 主体自动更新摘要 | analysis_subject_state + 原主体状态/created_at + 当前profile |
| unfinished_analysis_tasks | 非终态有效根任务去重；投影task_id/意图/业务状态，不含队列 |
| unfinished_runs | 实际运行attempt关联Run，不把已本地结束unknown算进去 |

归并后的原task_id一直可查，服务端跟随内部root返回实际进度和关联，原触发时间仍为原值；若root已有失败重试历史，显示其真实时间，不伪装成新任务独立执行。人工核实任务路由/表不变。采用review_token包含有效分析任务与原有未完工作，继续使用原acknowledge_pending_work，不增一套确认流程。

公共reason_code最少固定：no_changes、closed_before_start、automatic_attempts_stopped、retry_scheduled、retry_stopped、capacity_exceeded、call_timeout、executor_interrupted、retry_exhausted、invalid_input、prerequisite_unavailable、execution_failed。自动资格过期可在主体资格/停止重试原因中表达，不能据此跳过窗口内已受理的首次尝试。更多原始错误在脱敏detail/原工件表达，不把队列名写进DTO。

POST成功持久受理返回202（E01沿创建回执同时返回任务）；同operation_key换意图/主体/正文409，已关闭/空范围409，父主体或任务不匹配404，未知/非法输入422。未持久受理的服务错误不得返回task_id；持久后Redis投递故障仍通过原task查询，不能迫使调用方换key。

## 9. 定向验收与限制

实施时用隔离PG及可控执行器直接核：Case+task原子保存、无提前Run；两次attempt原件可读；旧unknown不阻塞N=1后续任务；无变化无Run；晚到A同ID更新；排队任务纳入采用预览；原task_id归并后可读。测试无需真实超时远端服务或构建恢复矩阵。

人工定向及手动续接的业务流程已确认，输入/结果字段按第11节及已确认HTTP合同实施；自选时间窗仍是未定扩展，模型读取附件正文非本期要求。负责人已明确不纳入RV11同告警新材料入口或重新分诊，原入站/历史材料结构保持，不再等待该来源合同。其他需求已明确但实现缺失应标待提供，不因没有表而取消需求，不建猜测占位表。上述4张表是本轮定稿的内部调度/跟随范围；实际迁移编号在实施时按仓库增量顺序分配，不能覆盖其他聊天迁移。

## 10. 产品R1/R3/R4的完整读取供给

需求见[产品清单](../../../docs/integration/product-api-data-requirements-20261114.md)。调查核心提供统一读取用例，经独立HTTP端口适配；目标路径已与HTTP对齐为GET /analysis-runs及/analysis-runs/{run_id}/steps、steps/{step_id}、artifacts（均在/api/v1/socai2下），具体DTO见[合同第8节](http-workflow-contract-20261114.md#8-后续已确认更新对http的要求)。本节不在代码中新增路由，不建设独立统计/查询平台。

| 内部读取用例职责 | 输入范围 | 必须提供的结果和来源 |
| --- | --- | --- |
| 跨A/I/Case运行目录及统计 | 配置租户，现有页面主体/轮次/状态/时间范围，limit/cursor | 从runs出发返回真实Run、父主体、已有task/attempt关联（历史可空）、执行/交付状态、实际时间/输入数量、真实结果摘要/链接及Case关系；同范围总数和状态/交付统计由数据库计算 |
| Run步骤目录及步骤定位 | 实际主体/run_id，limit/cursor；定位时step_id | run_steps稳定排序分页，保留seq/parent_step_id、真实状态/错误/用量及输入输出引用；父步骤跨页仍可按身份定位 |
| Run工件目录及工件定位 | 实际主体/run_id，limit/cursor；已知artifact_id | artifacts的完整可遍历目录，身份/类型/来源步骤/可用性/大小；正文沿既有原件GET逐件读取，不把正文全塞列表 |
| 查询目录及证据回查 | 同Run内实际工具步骤及其来源引用 | 复用步骤分页/定位，返回真实参数、未查/失败/查空/复用/未知等状态和原件引用；复用旧Run原件按实际父主体/来源定位，不复制为本轮新结果 |

目录以真实Run为单位去重，关联多个Case/多个结果不得重复计数。无Case的A/I、无结果失败及unknown均保留；不能从结果表或Case列表反推全部Run。公共分析任务尚无Run时仍留task目录，不制造Run加入统计。Run状态与本地执行状态分别表示，历史记录缺task/attempt不能伪造关联。

统计与目录使用相同筛选范围，返回统计观察时间，不能只数本页。Case关系必须为真实业务关联并注明含义，当前关联不冒充执行时已冻结关联；候选Case ID不算实际归属。结果类型分别为Case Result、A assessment、I diagnosis，缺结果为空。

分页采用稳定排序键加唯一ID的游标，校验游标的主体/过滤条件；运行目录按requested_at DESC/id DESC，步骤按seq ASC/id ASC，工件按captured_at ASC/id ASC。单页默认50、上限100为目标profile值，页上限不是总量截断；1000步骤/200工件旧上限不得继续作为目录可发现总量上限。运行中的新增记录在刷新后可见，返回观察范围/续页信息，不承诺跨多次HTTP请求建立长事务快照。原件缺失/外部blob未加载如实返回，目录完整不伪装原文一定存在。

步骤目录保留input/output/reused_artifact_id并派生artifact_refs，按实际工件与Run关联返回role、artifact_id、源run_id、真实主体及content_url；复用跨Run原件不改归属或伪造成本轮产物。单件正文沿已有Case/A/I原件GET，无须复制三套新目录。目录参数/错误保持必要脱敏，不暴露连接密钥或blob内部地址。

直接验收并入2.7：一个包含A/I/Case、无Case及无结果失败/unknown的固定夹具核目录/统计不重不漏；分页能发现并定位超过原上限的步骤/工件，引用恢复到正确原件；读取不调用模型、不改运行状态。只补受影响查询测试，不重跑阶段一、全仓或真实模型。

## 11. 人工定向与手动后续综合

负责人已确认：针对问题/工具的一次定向分析先独立交付建议或结论；后续全案综合由用户手动触发，详见[Q1](stage-2-5-design-review-20261114.md)。不按永久方向字段变更触发完整调查，也不因模型建议继续自动建任务。

核心与HTTP已确认以下执行分类；这是目标枚举增量，尚未迁移或修改代码：

| 业务 | analysis_tasks.kind / intent | RunKind / ResultKind | 基线及比较 |
| --- | --- | --- | --- |
| 普通完整调查 | case_investigation / initial、check、rerun | baseline / baseline | 按实际完整调查确定上一轮；正常完成更新全案输入基线 |
| 一次人工定向 | case_investigation / targeted | targeted / targeted | 局部结果不参与上一轮完整调查选择，不更新全案完成基线或自动窗口，不设置/清除主体自动停止标记 |
| 用户手动全案综合 | case_investigation / synthesis | baseline / baseline | task意图区分生成方式；保留真实完整范围，只有实际完成该全案输入才更新完成基线及窗口；按完整调查规则比较 |

不复用暂停的ai_question/ai_saved或source_answer_id，不新增synthesis结果枚举。所有Case意图共享同一个kind和主体串行约束、Case优先级及总N；不能因RunKind不同多占一个同Case槽。targeted/synthesis/rerun只按同operation_key重放，不与普通initial/check相互归并。定向或综合失败仍保留每次attempt，但不会仅因局部/复用前序问题阻止普通全案更新；只有完整调查对实际全案输入的失败才按第4节登记该输入停止依据。

### 11.1 受理和实际输入

定向request_payload保存question、可选alert_ids/object_refs/tool_names，具体HTTP字段校验以[目标合同](http-workflow-contract-20261114.md)为准；综合保存非空targeted_result_ids。所有来源必须同租户、同Case；原请求内容用于幂等比较，不因排队期间材料变化而改写。执行前再次校验明确范围/引用，再保存真实材料和配置。未指定告警范围时取执行前当前Case；明确范围不因最新成员变化自动扩大。引用已失效时记录invalid_input及缺口，不静默换成另一对象。

定向模型只承担所问问题的判断：提供用户问题、实际相关成员的业务材料、适用A/I及必要历史分析、适用有效H、选定工具取得的业务记录；每类只保留对本问题有用途的字段，历史判断保持prior_analysis、H保持human_statement。不把完整Case对象/旧报告/工具回执整包透传。返回建议和/或结论、必要依据及待核事项；程序保存实际范围、工具执行/未执行事实和原始IO，不要求模型编写调度台账，不强迫产生新证据。

工具仅限现有只读process_activity、network_connections、authentication_activity及有对应连接来源的product_host_details；不接受任意SQL、连接地址或越权参数。未知工具拒绝；已知但本Case缺条件/不可用的工具保留未执行缺口，其他分析继续。时间和日志条数沿第12节，调用次数/超时沿本轮实际策略；工具目录读取不发模型、不执行查询。

### 11.2 独立结果、复用与完成

定向结果使用现有results保存结构及targeted类型：conclusion可空，findings/recommendations/questions按实际内容返回，图/报告无产出则为空；保留source_run_id、input_artifact_id及真实范围。它可独立完整交付一次问题分析，但不因此成为全案结果或可采用的全案判断；全案采用沿后续合格baseline及既有明确操作。未点综合就结束，不靠结果保存或模型建议自动续跑。

综合是独立异步task，实际执行才创建新的attempt/Run；原定向task/Run不重开、不覆盖。核心执行前选择适用的完整调查来源，冻结选定定向结果、必要原证据、当前适用H和前序来源映射；source_run/result与“上一轮比较对象”分别保存。复用证据保持原主体/版本/原件位置，不伪造再次查询。当前范围不能由可用前序支持时记录prerequisite_unavailable和缺口，不静默跑整条C1–C6或冒称覆盖后来新增告警；单纯没有新证据或模型未建议综合不构成拒绝原因。

适用材料恢复后按必要的关联整理与综合处理，模型只接收完成全案判断所需业务视图；全量原件留后台。结果沿baseline读取、比较、新鲜度和采用保护；不会直接替换当前采用判断。实际材料未全部完成时不推进全案完成基线。task、attempt、Run、Result与工件分别可读，公共仍只有主体、task_id、run_id三层执行身份，Result/工件是输出引用。材料复用需改适配层后才能执行，当前C5/C6不能据此宣称已支持跨Run续接。

## 12. 默认查询范围与日志上限

Q2按已确认前后各1小时和缺时保留分析设计。profile增加case.query_window.before_seconds/after_seconds（默认各3600）及case.log_query.max_rows_per_query（本轮设计默认50）；保留原case.max_rows_per_query政策上限，日志实际上限取两者较小值，不改既有公共Limits字段含义。受影响profile读取、请求构造和工具参数校验一起接线，不能保留代码中的隐含50门槛；本轮未改实际配置。

复用Run输入/策略及工具请求/回执工件，保存相关告警身份/材料版本/真实发生时间、派生起止、扩展量与配置版本、实际行数上限、已取条数及截断状态。无需新增查询配置或截断表。缺时间保留目标和原因，已有分析继续；条数超限可多取1条探测，已取得原件留后台，不伪造总量或未读取记录。不另设最大时间跨度、裁剪或自动拆窗；沿现有配置的单次查询超时收尾，超时/失败保存补查缺口。默认不自动翻页，有限结果不能表示完整覆盖；既有模型输入容量约束照常适用，执行台账不整包进入分析输入。

## 13. Case上限100与后续接收路由

case.max_alerts目标默认100，配置化；它限制单Case关联，不限制来源事件保存，也不保证模型能装下100条。现有200硬门槛在阶段4改为统一分配入口，不能只将报错数字改为100。来源成员可分页读取，单Case上限不得成为来源成员总量截断；首次创建、手工关联/移入、跟随检查和执行准备均复用同一分配用例。

仅在cases增量增加以下可空自关联字段；保留原件，不建设上线前存量回填/迁入逻辑。新建的独立首Case保存root=self和receiving=self；后续Case只保存root及previous，receiving由最初Case维护。

| 字段 | 含义 |
| --- | --- |
| continuation_root_case_id | 本串最初Case ID；首Case指向自己，后续Case指向同一个最初Case |
| previous_case_id | 因容量续建的前一Case；首Case为空，后续Case指向续建前接收者 |
| receiving_case_id | 仅最初Case保存当前接收新告警的Case ID；后续Case为空，读取时沿root解析 |

三者均引用同租户cases；建立root查询索引及previous定位索引。创建后续Case时检查root/previous属于同串，禁止自指前驱和关系成环，不能将普通相关Case误作同一续接串。当前接收指针只能指向同串Case；路由字段不作为模型分析材料，不因指针切换单独重跑旧Case或续期。

事件完整关联由case_incidents保存，一个事件可以关联多个无续接关系的独立Case；事件自动接收由incidents.active_case_id唯一指定。Case的root/previous/receiving只表达满额续建，不能因共享事件就把独立Case归成同串。事件自动新增先读active_case_id；手工指定Case新增沿该Case的root/receiving解析。续建时在同事务保留旧事件参考行、建立新关联、更新root.receiving_case_id，并仅转交当前active_case_id确实指向旧接收者的事件。旧告警/Run/结果仍归旧Case，不复制旧原件充当新Case成员。

所有生产者经同一业务用例区分事件自动路由和手工指定Case路由，再解析实际接收Case。短PG事务锁定最初Case并重新核接收者、开放状态和当前数量；涉及活跃目标切换时同步保存事件行及实际关联，防止并发切换覆盖新目标。显式跨Case移入沿既有确定顺序锁相关行。重复operation_key先返回原回执；自动续建分配不重复加入同串已有关联。将新增成员填入当前Case余量，确有溢出时创建后续Case、关联新成员、登记其initial task、转交仍属于旧Case的活跃事件并更新接收指针，直到本批分配完。事务只处理业务保存，不调用模型、不持有Redis锁或做跨库事务；提交后沿原机制投递task。

原Case任务不会改成替新Case执行。若A的检查发现溢出并建B，就为B登记自己的首轮task；A原task仍只比较/执行A，新Run始终归真实Case。后续向B追加成员沿既有周期/手动检查；不为每条到达重新发initial或修改正在运行的Run输入。每Case拥有独立任务、历史、采用与状态；没有新增第四层公共业务ID。

回执/读侧提供请求Case、实际接收Case、各Case实际新增/已有成员及版本、新建Case及对应首轮task、root/previous/current关系，以及事件全部关联Case和唯一活跃目标；幂等回放保持原分配，即便当前接收者后来又改变。E01/E08使用CaseAllocationReceipt，E09额外保留源Case移出与版本；E07只替换请求Case自身的移除/保留部分，新增沿相同容量分配，返回源变化和实际分配，不清空整串或移走本应保留的旧成员。所有入口复用同一短事务和容量校验，具体公开字段以HTTP合同8.3为准。CaseView中的receiving_case_id沿root解析，不能把后续Case数据库中为空的指针误作无接收者。

GET /cases/{case_id}/related-cases在数据库候选范围先排除本案、按Case ID归并来源，再按容量续建优先、仅共享事件其次排列；组内created_at ASC/id ASC。共同事件按实际case_incidents或case_alerts→incident_alerts产生，保留本案和关联案各自explicit/member_alert来源，同案命中两组只展示一次。relation_revision是相关候选Case身份、关系分组/来源与稳定排序依据的确定摘要，游标绑定该摘要；关系变化导致旧游标失效则409/cursor_stale、刷新第一页，不新建关系版本表或长事务快照。只读展示不切接收者、不触发模型，不额外保存推导Case对照表。原型原有相似Case占位不作为该关系列表的交付；第5步已实现本地核心及HTTP关系读取，见[本步回执](../../../docs/operations/evidence/case-allocation-20261115-01/README.md)，不扩展相似度推荐。关联不复制旧原件/结果或生成跨Case综合，新Case首次比较对象为空。

自动新增以事件指定接收者的开放/7天资格判断；指定目标可为空，有目标也不代表当前有自动资格。接收资格与同材料分析失败停止分开：automatic_attempts_stopped不阻止真实新告警加入，加入后按新的输入摘要检查。旧Case关闭不自动关闭后续Case，指定接收Case关闭或自动超期时停止追加，不自动回退历史Case或通过续建绕过限制。手动操作仍受关闭约束，超自动期限可显式check/关联；普通手动调查不抢回事件接收权，全部采用、反馈和旧Run原件保持原主体。

## 14. 事件单次范围与实际容量收尾

profile新增incident.max_alerts_per_diagnosis，默认100，独立于case.max_alerts。I加载时读取事件全量计数并按incident_alerts.linked_at DESC、alert_id ASC选取最多N条；计数和所选范围来自同次执行前的数据库观察。成员原表、原材料和其他诊断不删，不能先被旧200加载门槛截断再宣称完成选取。分页/成员查询保持完整可遍历；本轮I限制不限制Case从事件完整成员分配。

沿现有Run输入/策略/结果工件保存：选择依据和配置上限、选入告警ID/材料及A引用、事件当时总数、未选数量、输入捕获时间、实际输出覆盖。实际原件留在原存储并保留引用，不将全部未选正文放进模型。本轮成员索引只表达真实选入输入，不将未选成员记已处理；模型未发出、没有该成员的实际分析或覆盖不可确定时，不伪造已分析。对外读侧需明确完整/部分事件范围及限制，执行/交付/质量状态沿各自定义独立展示。

事件读侧input_selection与analysis_coverage按HTTP合同8.5由实际工件/成员状态派生，不改告警StageEntry。已分析但结论待核的unresolved仍属已覆盖，covered_alert_ids为analyzed与unresolved对应ID并集；三种已知计数（analyzed/unresolved/not_analyzed）之和为selected_count。相对捕获事件全部成员，omitted_count=0且not_analyzed_count=0才是complete；无覆盖为none，部分为partial，无法确定为unknown且计数不填假0。它描述范围是否经过分析，不代表结论已证实、已人工复核或质量通过。

I检查摘要按当前选择及其可用A/反馈业务输入生成，未选成员的A变化不单独触发同输入再分析。选取策略/额度变化后重建选择、实际输入变化才新分析；无变化不运行。输出装配、存储覆盖和新鲜度校验须同时适配选入范围，不能拿全事件成员集合拒绝合格局部结果，也不能把本轮选择外的成员标已覆盖。Case采用I仍核实际范围/可用性并保留prior_analysis；I缺失或容量失败不成为Case全流程的等待门。

实际请求仍逐步骤测量上下文及输出预留；保存原请求准备件、测量和政策。容量超限时停止本轮、保留已完成模块及原始输入输出，task如实failed且不入pending自动重试，Run保留真实状态/交付限制，正常完成基线不推进。已有诊断/采用不被失败覆盖；本地收尾释放名额。无须另加分批汇总、自动缩减成员、模型语义压缩或容量恢复服务；同输入/配置不反复尝试，变化后重新预检沿第4节。
