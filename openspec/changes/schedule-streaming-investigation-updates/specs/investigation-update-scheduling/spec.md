## ADDED Requirements

### Requirement: The validation service ships as an independent read-only package
The system SHALL package the test API, viewer, explicit ledger publication CLI, current fixture drivers, required contracts, configuration examples and versioned compatibility manifest independently from the investigation deployment. Runtime configuration and retained ledger/evidence SHALL be external to the release. Serving, restarting or replacing the read service SHALL NOT execute tests, publish records, send data or start investigation processing.

#### Scenario: A package runs outside the source workspace
- **WHEN** the package is extracted with explicit configuration and matching dependencies
- **THEN** its service, viewer, test API schema and fixture drivers are available from the packaged files, and the manifest identifies the required investigation contract and unsupported capabilities

#### Scenario: A read service restarts against retained records
- **WHEN** the candidate read service is stopped and started with the same retained ledger and evidence
- **THEN** the original records and evidence remain byte-identical and readable without executing a test or creating an investigation Run

#### Scenario: The authorized 4177 viewer entry is published
- **WHEN** the explicitly configured read-only test service is published to the selected 4177 entry with viewer enabled
- **THEN** the site root and previous index bookmark redirect to the same HTTP viewer, which reads the bound investigation environment and retained test ledger; prior snapshots remain preserved and opening the viewer does not start an investigation

#### Scenario: A reader opens one Case execution
- **WHEN** the reader chooses a Case and a saved execution in the primary viewer
- **THEN** the page displays its actual stage and child-step flow with adjacent input, prompt, output, original model reply and error inspection; historical selection stays bound to that Run, while test plans, preparation and quality records remain available separately

### Requirement: PostgreSQL deployment uses password credentials without client certificate setup
本轮目标部署 SHALL 使用显式数据库地址、端口、库名及账号密码连接PG，不要求应用部署者配置CA证书、客户端证书或私钥。连接模板 SHALL 默认`sslmode=require`，保持服务端已有TLS而不引入客户端证书校验要求；活动处理、入站、调度、HTTP和PG安装入口 SHALL 使用相同口径，不自动回退旧认证配置。历史冻结发布/记录及Kafka传输配置 SHALL 保持各自范围。

#### Scenario: Deploy the current processing and HTTP services without CA files
- **WHEN** 部署者提供有效普通账号密码与明确PG目标，未提供CA/客户端证书/私钥
- **THEN** 当前profile及运行装配可通过，数据库连接成功；错误密码失败且不输出密码。HTTP读写和执行器均不要求额外证书文件，不改变业务合同

### Requirement: Initial analyses are submitted automatically without a second start action
系统 SHALL 在新告警/首次事件保存后登记各自首轮分析，并在用户创建Case时同事务保存Case、所选范围分配和首轮分析task。首个Case仍由用户手动创建；系统 MUST NOT 为尚未建立调查入口的事件自动建Case或要求用户再次prepare/start。已存在调查串达到配置的告警关联上限时 SHALL 按下文规则自动续建关联Case并登记其首轮task。入站和业务HTTP SHALL 不等待模型，告警分诊没有对外手动启动入口。本期 SHALL 只提供告警首次自动分诊及同次任务已确认的有限故障重试，不新增同告警原材料新版本入口或据此重新分诊；现有重放语义和历史原件保持。

#### Scenario: A user creates a Case from an incident
- **WHEN** E01成功保存用户选择的Case和事件成员
- **THEN** 返回Case和首轮task_id；任务已持久受理但可以没有run_id，后台按容量执行完整C1–C6

#### Scenario: An alert joins an existing incident
- **WHEN** 新A3入站且A1/A2已经分诊
- **THEN** 仅登记A3分诊，事件/已跟随Case在后续检查识别变化，不重分诊A1/A2，也不要求调用方为A3手动发请求

### Requirement: An incident routes ongoing updates to one active Case
系统 SHALL 保留事件与多个Case的实际关联，允许这些Case相互独立且没有续接关系；每个事件 SHALL 另持久保存最多一个活跃接收Case，允许为空。活跃表示后续告警及I诊断更新的接收目标，不表示正在执行。事件新增告警及I新结论 SHALL 仅驱动当前活跃Case的自动更新，历史关联Case MUST NOT 因同事件变化全部扩范围或重跑。

明确整事件新建/关联 SHALL 将本次实际接收Case保存为该事件活跃目标，保留旧关联和原Run；普通查询、check/rerun、单告警关联及同operation_key重放 MUST NOT 抢回后续已切换的目标。告警 SHALL 可以关联多个独立Case，无告警活跃目标或全局唯一Case归属限制；不新增同告警原材料更新或重新分诊功能。

#### Scenario: An incident belongs to independent Cases
- **WHEN** 事件E关联独立Case A和B，最近明确整事件关联的接收者是B，随后E增加告警D
- **THEN** 保留E到A/B的关联且不建立A/B续接关系；只有B在合资格检查时纳入D，A范围和已固定Run不变

#### Scenario: A single alert is added to several Cases
- **WHEN** 用户将告警D分别关联独立Case A和B
- **THEN** 两个成员关联都合法，不选择告警的活跃Case，也不改变D所属事件的活跃接收目标

### Requirement: Incident diagnosis selects recent memberships with explicit coverage
事件 SHALL 保留全部成员与原件，不因模型容量停止接收或自动拆事件。单次诊断上限 SHALL 从独立profile配置incident.max_alerts_per_diagnosis读取，默认100；按incident_alerts.linked_at DESC、alert_id ASC选取最近归并成员，真实告警发生时间保留其原意。初轮、周期/手动check及rerun SHALL 共用该策略，实际执行前重新选择并固定；运行中成员变化不得改写本轮输入。

Run输入/结果/读取 SHALL 保存选中成员及材料引用、事件当时总成员数、选择依据与上限、未选数量和实际交付范围。系统 MUST NOT 将部分范围的判断当作全事件判断，也不得将选入输入等同于已经成功分析。范围覆盖与执行/交付状态 SHALL 分开：选中范围正常完成可结束本轮，但事件整体仍可部分覆盖。未选原件和历史诊断 SHALL 保留，不自动分批补跑或借历史结论伪造本轮完整覆盖。

已实际分析但结论待核的成员 SHALL 作为unresolved记录并计入已覆盖；analyzed/unresolved/not_analyzed互斥且已知数量合计为selected_count。事件覆盖complete SHALL 同时满足未选数量为0及选入成员均已实际分析；无法确定的统计保持unknown，不以假0或选入数量代替实际覆盖。

检查 SHALL 先重新选择、再比较选中成员及其可用A/反馈的有效业务输入；未选成员的A变化不单独导致重复分析同一输入。结果校验/新鲜度 SHALL 按实际选中范围与策略处理，不能仅因事件总量超过上限拒收局部有效诊断。Case成员归入 SHALL 独立读取事件完整成员，不能以I选中清单截断Case来源；I部分覆盖/失败/超限不得阻断Case用自己的成员和可用材料调查。

#### Scenario: An incident contains more members than one diagnosis accepts
- **WHEN** 事件已有260条且单次上限100，执行前选择最近归并100条
- **THEN** 事件260条均保留，Run保存100条选入范围和160条未选限制；结果只对实际覆盖负责，Case关联仍可读取全部260条

#### Scenario: A late alert has an older occurrence time
- **WHEN** 一条发生时间较早的告警刚归并到事件，且它按归并次序处于最近100条
- **THEN** 它进入本轮候选范围，模型仍看到原发生时间；运行中再到的成员不被记成本轮已分析

#### Scenario: An analyzed member still needs verification
- **WHEN** 模型已分析某选入成员但其结论仍待核
- **THEN** 该成员记unresolved并计入本轮实际覆盖，待核状态保留；不会误记为未分析或确定判对

### Requirement: Case consumes the frozen scope of an incident diagnosis
Case SHALL 在执行前固定所选I诊断的来源Run、输入工件、原选入范围及实际交付覆盖；事件当前成员、I选入成员及已分析成员 SHALL 分别表达。I概要/结论的成员关联 SHALL 限于已保存实际覆盖与Case成员的交集，并保留原选入范围；逐条发现/问题 SHALL 保留原scope，不能改写成Case独有发现。Case自身调查范围 MUST NOT 被I选入范围缩小。缺范围、来源不一致或无可用交集 SHALL 记录原因并保留其他材料分析，MUST NOT 以事件全部成员补造覆盖。新输入、后续来源映射及HTTP工件读取 SHALL 使用同一冻结范围，后来的新I或事件扩员不得改写旧Run。

#### Scenario: A Case contains members not selected by the diagnosis
- **WHEN** 事件有A/B/C，I仅选入并实际分析A，Case包含A/B/C
- **THEN** Case仍调查A/B/C；I结论只能关联A，B/C不成为该诊断已分析成员；I原输入、Case冻结输入和HTTP读取保持该关系

#### Scenario: Some selected members were not analyzed
- **WHEN** I选入A/B，保存的交付记录表明A待核但已分析、B未分析
- **THEN** 原选入范围保留A/B，实际覆盖只含A；Case不将B计为I已分析或把待核A误记为未覆盖

#### Scenario: A cross-member finding overlaps only part of the Case
- **WHEN** I发现的原scope为A/B，Case只包含A/C
- **THEN** 发现仍声明原范围A/B，Case关联仅为A，不将发现改写成A独有，也不关联C

#### Scenario: Diagnosis scope is unavailable or changes after the Case starts
- **WHEN** 所选I缺少可信冻结范围，或Case开始后事件增加成员/产生新诊断
- **THEN** 缺范围时记录不可用而不猜测；已冻结Run保持原范围和原来源，其他Case材料仍可分析，读取不补写最新状态

### Requirement: Capacity failures preserve completed work without retry loops
I和Case模型步骤 SHALL 按完整请求、输出预留和安全余量预检实际容量，条数上限不替代测量。超过输入/上下文或相关预算限制时 SHALL 记录失败原因、准备范围和测量，保留已完成模块结果及完整原始输入输出，结束本轮并释放本地占用；不得伪造成功、全量覆盖或模型已执行。系统 MUST NOT 因容量不足自动再删成员、截正文、拆分综合或将同输入投入pending重试。

同一有效输入和相关容量配置的周期检查 SHALL 不反复创建模型尝试；输入或容量配置变化可重新检查，明确rerun也须通过预检。先前诊断/采用判断及失败历史 SHALL 保留，其他任务继续调度。没有覆盖全部目标时不得推进为完整完成基线。

#### Scenario: A bounded Case still exceeds the model context
- **WHEN** Case只有40条但下一模型步骤的完整请求超限，已有步骤保存了有效输出
- **THEN** 保留这些输出和超限输入/测量，当前task如实失败收尾且不自动重试；N=1时下一主体可继续，未发送请求不计为模型执行

### Requirement: Case membership capacity routes overflow into linked successor Cases
单Case关联上限 SHALL 从profile读取case.max_alerts，目标默认100。系统 SHALL 保存续接最初Case、前一Case及当前接收Case的关联，使用已有Case ID；自动事件跟随、手动检查补入和手工添加/移入 SHALL 共用当前接收Case路由，不因请求指定旧Case就继续向旧Case塞入新成员。

当前接收Case满额且确有未分配告警时 SHALL 自动创建关联后续Case，将接收目标改到新Case并为其登记首轮task；后续新增继续加入该Case直至满额，再续建下一Case。批量/首次选择跨越上限 SHALL 依次填充当前及后续Case，不静默丢弃溢出成员、不预建空Case、不重排旧Case成员或Run。此串内重复告警 SHALL 返回既有归属，显式排除不得被后续跟随加回；不同独立调查串仍可关联同一告警。

事件全部关联 SHALL 复用case_incidents保留，唯一自动接收目标 SHALL 保存于incidents.active_case_id，不仅存于内存/Redis；Case续接字段只表达满额续建。新Case SHALL 保存前一Case及最初Case的身份关联，旧告警、Run和结果仍归旧Case；已有Case ID足以定位关系，不新增对外分组ID。

续建 SHALL 只转交活跃目标仍指向旧接收者的事件，保留旧Case成员及事件参考；已经切换到独立Case的事件不得被抢回。用户只选单告警不得借续建扩大成整事件跟随。每个Case SHALL 独立保存任务/Run/判断/生命周期，新Case首轮不把前案Run作为自己的上一轮，也不自动继承全案结论或触发跨Case综合；满额旧Case仍可处理其原范围的合法更新。

分配、必要Case/首轮task创建及接收目标更新 SHALL 在同一个短PG事务中按最初Case串行校验容量，事务外投递队列；同operation_key重放返回原实际分配。创建/关联/移入回执 SHALL 明确实际接收Case、新建Case及首轮task，并以excluded_alert_ids说明本次源事件成员中因本串显式排除而未分配的精确集合；读取可定位整串关系与当前接收Case，MUST NOT 把新Case收到的成员伪报为原Case新增。

自动新增/续建 SHALL 遵守当前接收Case的关闭和自动期限规则；不能借创建新Case绕过停止条件。旧Case关闭不得隐式关闭其他后续Case。成员数量上限 MUST NOT 代替实际模型上下文测量；历史旧Case不自动拆分或改写旧Run。

Case关系读取 SHALL 区分满额续建关系与共享事件关系；用于关联Case列表时 SHALL 优先展示同串续建Case，其次展示其他共享事件Case，排除本案并按Case ID去重。共享事件 SHALL 返回真实事件身份及显式关联/成员归属来源，MUST NOT 因展示关联自动续接两案、开启跟随或触发调查；当前相似Cases占位不代表已有列表交付。

#### Scenario: A batch crosses the current Case capacity
- **WHEN** 当前Case A已有99条，首次收到5条未在同串关联的告警，上限为100
- **THEN** A接收1条，新建关联Case B接收4条，当前接收目标为B；保存B首轮task，A原Run输入不变，回执分别给出A/B的真实分配

#### Scenario: Later manual and automatic additions address the original Case
- **WHEN** A已满且当前接收Case为B，后续事件跟随或从A发起的手工添加带来新告警
- **THEN** 共用路由将新告警加入B；B未满时不另建Case，B满后的下一条才创建关联C并更新接收目标

#### Scenario: A replay contains members already assigned to earlier Cases
- **WHEN** 同operation_key重放或跟随源再次列出已分配到A/B的告警
- **THEN** 返回原回执或既有成员归属，不在当前Case重复关联、不重复创建Case/task；明确排除仍保持

#### Scenario: The same incident feeds two independent investigations
- **WHEN** 同一事件关联独立A/B且只有B是活跃目标，B满额后新告警使其续建B2
- **THEN** 仅B2与B建立续接关系，事件活跃目标改为B2，A/B历史关联保持；未来新告警只进入B2

#### Scenario: An older Case continues after its event changed receiver
- **WHEN** 事件E已从A切换到独立B，用户之后向A手工加入告警导致A续建A2
- **THEN** A2关联A但E的活跃目标仍为B；A历史事件关联不使A2自动取得E接收权

#### Scenario: Related Cases have overlapping relationship reasons
- **WHEN** B为当前Case A的容量续建关联，C为独立Case且与A共享事件，B也与A共享事件
- **THEN** 展示时B在第一类、C在第二类，B只出现一次，排除A本身；共同事件不赋予C续接关系

#### Scenario: The current receiving Case is closed
- **WHEN** 当前接收Case已关闭而事件继续增加告警
- **THEN** 不通过新建Case绕过关闭限制，原告警正常保存；其他Case的历史与独立状态保持

### Requirement: Material checks compare meaningful saved inputs on configurable schedules
事件/Case SHALL 分别按默认4小时/6小时的独立profile配置检查有效业务输入；I SHALL 比较本轮按最近归并策略选中的告警ID集合、可用A分诊业务内容及有效告警反馈，Case SHALL 另纳入有效H正文/范围/引用与撤回。告警材料链中的Case自动检查 SHALL 只对本案明确关联且作为活跃接收者的事件比较当前输入对应I的本地终结回执；完整/部分/不可用回执均可供Case继续自己的原材料分析，不把失败称为有效诊断。I尚未完成、等待合法重试或仅有旧stale诊断 SHALL 不触发；变化摘要 SHALL 使用冻结业务输入、可用单元内容及可用性，不使用错误时间、重试次数、Run/工件ID。相同输入已有可用I时，后来的失败不得用空内容替换该有效内容制造变化。程序 MUST NOT 仅比较数量或全行版本，也不新增模型调用判断价值。晚到A仍先供I检查，不得绕过I直接触发Case；单告警首次A晚到仅在下次调查读取。手动/自动I同规则，只更新当前活跃Case；手动Case调查使用原范围适用I，不改变事件接收者。

结果/回执变化 SHALL 单向作用于下游，I不得触发自身/A，Case不得反向或自循环；采用、知识维护及纯管理元数据不单独触发。上游失败/无内容 SHALL 如实表达，Case可在I终结后带缺口继续；相同输入和相同可用内容的重复失败不得反复生成调查。原关闭、期限、唯一接收目标、执行前重核及停止摘要规则保持，失败输入不得冒充成功覆盖。

#### Scenario: Alert identities stay unchanged while triage becomes available
- **WHEN** 上轮使用A1/A2且A2分诊尚未完成，后续A2可用结论保存
- **THEN** 事件下一次检查提交I，不重跑A1/A2；Case等当前输入的I本地终结回执后再检查，单告警Case不直接触发；仅A2的执行ID/时间变更而内容相同不触发

#### Scenario: New members make the previous diagnosis stale
- **WHEN** 事件新增告警但新I尚未完成，之前I变为stale
- **THEN** Case不把旧I消失或告警增加单独当作自动调查触发；跟随及容量续建先核当前输入的I任务已本地终结且回执保存，再按事件全部成员分配，不用I选入范围裁剪成员

#### Scenario: A terminal incident attempt has no usable model conclusion
- **WHEN** 新输入对应I已耗尽允许的重试或不可重试并本地结束，保存partial/none回执，事件有合资格活跃Case
- **THEN** 该Case下一次检查可识别此新输入并用自身原件继续，I缺口可读；重复同输入同内容回执不反复触发，其他历史Case与单告警Case不跟随

#### Scenario: An incident attempt is waiting for its allowed retry
- **WHEN** I第一次连接前失败，任务仍accepted等待重试
- **THEN** 失败attempt可读但不作为终结材料信号提前触发Case；最后一次本地收尾并保存回执后才按同一变化规则处理

#### Scenario: Only Case overlap changes for the same diagnosis
- **WHEN** I原业务结论和实际分析范围不变，仅Case手动增减成员使与I的交集改变
- **THEN** 该交集变化不冒充新I结论自动触发；手动check仍识别Case范围变化，实际执行始终按冻结范围关联依据

#### Scenario: Only management or reference output changes
- **WHEN** 仅修改负责人/标题/标签、同值保存、读取状态或产生知识索引回执
- **THEN** 不因此启动新一轮分析，原结果新鲜度和采用限制仍保持

#### Scenario: A manually refreshed incident diagnosis changes Case input
- **WHEN** 用户通过既定异步事件诊断接口提交rerun，随后保存了活跃接收Case可用的新I结论，告警ID集合没有变化
- **THEN** 活跃Case下一次合资格检查识别上游变化，其他历史关联Case不因此自动重跑；不要求A重新分诊，也不因I自己的结论再次诊断I

#### Scenario: An automatically refreshed incident diagnosis changes Case input
- **WHEN** 事件因新成员或可用A分诊变化完成新的诊断
- **THEN** 仅当前活跃Case按与手动诊断相同的规则自动检查该可用I输入，实际执行前固定它及原始依据；不反向触发A/I

#### Scenario: An incident result arrives while a Case is running
- **WHEN** Case已保存本轮上游输入后，相关I才产生新的可用结论
- **THEN** 保留本轮输入及独立有效输出；下一次自动检查重核事件活跃目标，只有仍由本Case接收才因新I更新，不改写本轮覆盖，不要求上游全部结束后才允许Case执行

### Requirement: Automatic checks respect rolling windows and business lifecycle
系统 SHALL 从profile分别读取事件/Case自动窗口，默认7天；从最近正常完成分析的实际时间起算，无正常完成时用对象创建时间。扫描、通知、排队、失败、unknown及无变化跳过 MUST NOT 续期。开放对象在期限内外 SHALL 均允许手动check/rerun。关闭停止自动检查，重开本身不启动或续期。超期 SHALL 停止新受理自动任务；期限内已受理但尚未执行的任务 SHALL 允许执行这一轮，仍核关闭、当前输入、同主体串行及N，但不得因排队超期直接跳过。该轮失败 MUST NOT 自动重试，已等待的故障重试在关闭/超期时终止；运行中到期允许收尾。

本期 SHALL 按上线后新建对象进入流程，不新增上线前旧对象识别、迁入、批量激活或手动启用分支。用户计划上线前自行准备空库不代表本change执行清库；本轮设计/后续增量结构工作不得据此删除当前数据库。

#### Scenario: An automatic task waits beyond its window
- **WHEN** 自动check在窗口内已受理，排队时窗口结束，尚未有一次实际尝试且主体仍开放
- **THEN** 领取后按最新已有范围及变化检查执行这一轮；记录跨期事实，失败不自动重试，其他任务持续调度；不因该已受理任务放行新的自动扩案/续建任务

#### Scenario: An accepted late task completes normally
- **WHEN** 窗口内已受理的任务跨期后执行并正常完成
- **THEN** 沿统一规则用实际正常完成时间刷新活动窗口；排队或开始本身不续期，失败不恢复自动检查

#### Scenario: A manual analysis completes after automatic checks expired
- **WHEN** 开放Case超过7天后手动提交并正常完成一轮
- **THEN** 以真实完成时间恢复自动窗口，点击/入队本身不刷新；历史失败和停止原因仍可追溯

#### Scenario: A subject closes before a retry
- **WHEN** 原尝试已失败并等待重试，期间对象关闭或自动期限结束
- **THEN** 保留原失败attempt，终止该任务后续重试并记录原因，不把已有执行改成从未执行，也不自动重开

### Requirement: Whole incident associations follow explicit Case boundaries
新建或明确关联整个事件的开放Case SHALL 保存实际关联和事件唯一活跃接收目标，合资格检查/准备时纳入当前新增成员；单告警选择 MUST NOT 隐式跟随其事件。人工移出Case SHALL 保存排除直到明确重加；事件移出成员不得反向删除已选Case材料。关闭/超期不得发起新的自动扩范围/续建；已受理任务按上文执行原主体已有材料。Case上限 SHALL 按100条配置及续建分配规则执行，不默默丢弃关联；事件单次诊断选取规则不截断关联来源。

#### Scenario: Following an incident encounters an explicit exclusion
- **WHEN** Case跟随E1，A2已显式移出，E1随后增加A3
- **THEN** Case补入A3但不加回A2；显式重新加入A2才取消排除，旧Run输入不变

#### Scenario: A new Case enters normal scheduling
- **WHEN** 上线后用户创建Case并明确关联整个事件
- **THEN** 保存Case、事件关联/活跃目标和首轮task，直接按正常生命周期调度；不要求额外手动启用或识别旧数据批次

### Requirement: One dispatcher enforces capacity without head of line blocking
系统 SHALL 由唯一调度器领取task/pending，多个生产者仅追加；总N为正整数配置默认1，同主体同分析kind最多一个本地活动执行。pending优先且最多检查本轮开始P条，忙或未到重试时间放回尾部；余下容量按Case>A>I>知识维护处理普通队列，各队列最多其开始长度。N MUST NOT 被误用为最多检查条数，不批量重写队列或从中间重排，不在每个HTTP worker启动领取循环。

#### Scenario: Pending contains ten requests for an active Case
- **WHEN** N=2、A已运行，pending10条全属A而普通队列有空闲B
- **THEN** 本轮最多逐条检查这10条后转普通队列，B可使用第二个名额，不立即再从pending头无限读取A

#### Scenario: Multiple producers append while dispatching
- **WHEN** HTTP和定时检查同时追加候选
- **THEN** 各自只保存/追加task，唯一调度器逐条领取；允许重复候选，所有真实开始仍经过主体占用和N检查

### Requirement: Queue polling uses a configurable one minute default
dispatch.poll_interval_seconds SHALL 来自显式profile，默认60秒；每轮先收尾实际已结束任务，再领取并填充空位。执行 SHALL 异步运行，不能在领取循环等待整轮模型；该间隔 MUST 与4/6小时材料检查、故障重试等待分别配置。

#### Scenario: Three slots are free at a tick
- **WHEN** N=3且存在三个不同主体的可执行任务
- **THEN** 同一tick可启动三个任务，不解释为每分钟最多一个；重试达到最早时间仍需等实际tick和空位

### Requirement: Independent requests are checked before execution
不同operation_key的initial/check请求 SHALL 各自保留task并入队，不做跨task归并；同operation_key同请求 SHALL 重放原task。主体忙的请求 SHALL 放pending，等待不占N；领取后读取最新业务材料，无变化只记录skipped/no_changes、无attempt/Run或模型调用。有变化才先保存本轮范围再执行。新请求 MUST NOT 绕过同主体已等待重试的时间/次数或同材料自动停止摘要；显式rerun保留独立重做意图。内部pending对调用方透明。

#### Scenario: The earlier request already covered the update
- **WHEN** 同Case的T1、T2分别入队，T1完成时已覆盖T2提出的全部材料
- **THEN** T2仍可独立查询，执行前比较后记录无变化，不生成新Run或模型调用

#### Scenario: New material arrives while the earlier request is running
- **WHEN** T1已开始并固定输入，T2入队且有新的适用业务材料
- **THEN** T2等同主体空闲后再读取最新材料，保留T1输入，按自己的手动/自动规则比较并执行，不丢请求或同主体并行

#### Scenario: Different intents remain independent
- **WHEN** 同Case有普通check、显式rerun或后续定向/综合请求
- **THEN** 各请求保留意图且同Case串行；普通材料无变化不能吞掉明确rerun/定向/综合请求

### Requirement: Business records are readable before asynchronous analysis completes
A/I/Case SHALL 先在短事务持久保存业务对象、关联及异步task，再由调度器启动模型分析。模型未返回时业务记录及任务 SHALL 已可独立查询，Run/结果可为空或运行中；接收事务 MUST NOT 等待模型。完成后另存结果及更新关联，失败 MUST 保留对象、旧结果及失败记录。

#### Scenario: Model response has not arrived
- **WHEN** 告警、事件或Case已受理且模型尚未返回
- **THEN** 独立读取可见主体、已保存关联及任务状态，模型完成后才读到本轮新结果，不因等待或失败撤销原记录

### Requirement: Executors capture current inputs before analysis and never expand completed coverage
调度通知 SHALL 仅表达主体和意图，执行器 SHALL 在实际开始前读取最新全部有效材料并再次比较，先保存真实范围、版本、模块输入和配置再调用模型。check无变化 SHALL 只记task跳过、无假Run。运行中新材料 MUST NOT 修改已记录起始输入，结束只保存本轮结果/状态，不从最新列表伪造覆盖。全部原始/派生输入输出与错误 SHALL 保留。

#### Scenario: A fourth alert arrives before execution begins
- **WHEN** 调度发现A/B/C需调查，真正准备时D已加入
- **THEN** 读取并先保存A/B/C/D作为本轮范围，随后执行；不必固守旧排队列表

#### Scenario: A fifth alert arrives after input capture
- **WHEN** R2已保存A/B/C/D输入，E在运行中到达
- **THEN** R2只覆盖其保存范围，下次检查识别E；R2完成不能将E记作已分析

### Requirement: Conclusion comparison uses the previous actual investigation
Case SHALL 固定同Case最近一次实际执行且本地已结束的完整调查为比较对象，排队/跳过不算上一轮。上一轮无可用结论 SHALL 保留Run及原因并明确不可比较，不回退到当前采用或更早结果。变化检查的已覆盖基线 SHALL 另取最近正常完成的实际输入；比较在现有C6完成，不新增比较模型调用。

上一轮已验证身份/范围的部分单元 SHALL 可作为有明确来源及限制的prior_analysis供后轮使用，但不得因此产生比较Result。存在完整核心结论、accepted且满足冻结身份/全案范围及原Result约束时，partial/uncertain/length或独立质量诊断 MUST NOT 单独取消比较资格。历史拒收/unknown/系统收尾不得经新读取规则改为有效结论，失败或unknown不得刷新正常完成基线/自动窗口。

#### Scenario: The previous attempt has no conclusion
- **WHEN** R1已结束但failed/unknown或没有可比结论，R2开始
- **THEN** R2记录previous_run_id=R1及无可比结论原因，不冒充与更早采用判断比较，也不称R1材料已完成覆盖

#### Scenario: The previous attempt retained findings without a conclusion
- **WHEN** R1有来源可核实的F1但无合格最终结论，R2开始
- **THEN** R2可选入F1作为受限历史分析，同时previous_run_id=R1、comparison_result_id为空及不可比原因保持；不把F1当作全案结论

### Requirement: Transient failures receive bounded delayed retries
已确认暂时故障且无未知在途动作的task SHALL 按受理时策略最多自动重试一次，默认retry.max_retries=1、retry.delay_seconds=60。重试沿原task_id新建attempt/Run；实际开始重试才增加次数。扫描/放回/新通知 MUST NOT 刷新失败时间或额度。响应超时/结果未知、质量/格式/引用、配置/参数/预算错误不得靠队列重试；局部有效分析按阶段一保留。

#### Scenario: A connection fails before the request is sent
- **WHEN** T1首次尝试R1在10:00确定发生可重试连接故障
- **THEN** 保存原失败并最早10:01可重试；第二次实际尝试仍失败则终止，保留两次历史，不自动第三次

#### Scenario: Uncertain or exhausted input is checked repeatedly
- **WHEN** 某材料已以unknown、不可重试或次数耗尽终止，普通扫描再次发现同份材料
- **THEN** 跳过并记automatic_attempts_stopped，不以另一个task重置预算、不伪造完成覆盖；实际新输入或明确rerun仍可执行

### Requirement: Locally ended unknown outcomes never block the queue
本地执行返回、异常或配置超时完成取消/收尾后 SHALL 记录真实本地结束并释放主体和总槽；原Run unknown及旧ended_at空值 SHALL 保留，不能伪造远端明确失败。系统 MUST NOT 要求人工确认/解除unknown，不因历史unknown阻止新分析或结案；本地仍实际执行时不得提前释放。N仅表示本地活动执行。

局部调用unknown且本地已结束时 SHALL 保存阶段回执并允许独立下游按已冻结材料继续，不能因它终止整个可执行路径。未确定usage SHALL 保持未知并保留该次最大预算预留，不按零费用/零消耗释放本轮预算。若余量不足，仅跳过受影响调用并继续程序收尾；最终Run unknown时仍使用工件交付，不伪造terminal Result或远端成功。

#### Scenario: A timeout occurs with capacity one
- **WHEN** N=1、A等待回复超时并已完成本地收尾
- **THEN** task A失败、attempt记local_ended_at、Run保留unknown，不自动重试；队列继续启动B，无人工解除步骤

### Requirement: Task and attempt history is persistent and private scheduling stays internal
系统 SHALL 持久区分主体ID/task_id/run_id，公共任务状态为accepted/running/completed/failed/skipped。任务保存受理和策略，每次attempt保存序号、真实Run/起止、失败时间/阶段/原因及原件；无Run时明确null。公共接口 MUST NOT 暴露内部pending、Redis位置/键或要求切换归并ID。已有人工tasks与analysis_tasks SHALL 分开；采用预览 SHALL 包含未有Run的有效unfinished_analysis_tasks，并保留原确认规则。

#### Scenario: A user queries a task across a retry
- **WHEN** task T1经历R1失败、等待、R2完成
- **THEN** 原T1查询显示真实业务状态及两次attempt，原R1失败时间和输入输出仍可读；不把C3补答算新attempt

#### Scenario: Adoption is previewed before a queued task has a Run
- **WHEN** Case存在已受理未执行task，用户预览采用旧结果
- **THEN** unfinished_analysis_tasks及review_token包含该有效任务，不伪造pending Run；已本地结束unknown不算仍运行

### Requirement: Active executors use one complete target contract
启用的统一调度器 SHALL 在消费前注册告警分诊、事件诊断及Case调查，并核选定配置包含现行A/I/Case输入输出合同。缺合同或仅注册旧部分执行器 MUST 直接拒绝启动，不静默回退旧模型输入或解析路径。各实际执行入口 SHALL 校验本环节合同，Case SHALL 使用与当前配置一致的冻结输入身份；历史只读不构成旧执行入口。输出额度、并发和时限 SHALL 继续配置化，不能以固定额度数值作版本判据；后置知识维护不要求启用。

#### Scenario: Missing target profile cannot activate an old model path
- **WHEN** 统一执行配置缺alert_io、incident_io或case_io之一，或只注册A/I部分handler
- **THEN** 启动报配置错误，不消费任务、不调用模型；补齐当前合同后沿唯一A/I/Case执行链处理

#### Scenario: Historical inputs remain readable without execution fallback
- **WHEN** 读取历史Run或尝试执行缺当前冻结合同的Case输入
- **THEN** 原件可按原记录读取，但执行拒绝，不通过旧模型装配补造一次新调查

### Requirement: The target HTTP version submits analyses asynchronously
E01 SHALL 返回Case与首轮分析任务，Case investigations和事件diagnose SHALL 接受operation_key+mode(check/rerun)并异步202。analysis-tasks列表/详情 SHALL 提供持久状态与真实结果链接，列表含主体更新摘要。目标版本 MUST NOT 保留旧E11/E13两阶段启动、E36手动A或同步兼容分支；未知输入422，不静默忽略旧比较/时间窗参数。人工定向及用户手动后续综合的输入/结果字段按已确认Q1流程补齐，不自动续接；默认内部窗口及日志条数按Q2提供，不新增外部时间参数。Q3不新增同告警材料版本接口或重新分诊。模型读取附件正文非本期要求，自选执行窗口是独立未定扩展，不建立猜测占位API/表。

#### Scenario: A client submits while another run is active
- **WHEN** 开放Case正在执行，用户用新operation_key提交check/rerun
- **THEN** 202返回task_id等待后续处理，不因当前无空位报执行失败；同key重放返回原身份，换内容409，关闭对象409

### Requirement: Cross subject run discovery and statistics are complete within the requested scope
调查核心 SHALL 提供同租户A/I/Case统一运行目录及同范围统计，基于真实runs及主体/结果关系，包含无Case、无结果、失败和unknown记录。系统 MUST NOT 要求前端遍历全部主体拼接、从结果存在性反推Run存在性或仅统计已加载页。目录 SHALL 提供稳定分页、真实父主体/关联、执行与交付状态、时间/输入数量/结果摘要及实际来源；多结果/多Case关联不得重复计数。尚无Run的任务从任务目录读，不伪造Run；HTTP路径由接口合同定义。

#### Scenario: A failed unassociated alert run exists outside a Case
- **WHEN** 查询范围包含一个无Case、无结果的告警失败Run，以及事件/Case调查
- **THEN** 统一目录完整返回这些实际Run，统计同范围且各Run只计一次，不依赖前端事先枚举该告警

### Requirement: Step and artifact directories remain fully discoverable beyond page limits
调查核心 SHALL 提供按Run可完整遍历的步骤和工件目录、真实身份定位及原件读取，保留步骤顺序/父子关系/状态/错误和输入输出引用。单页限制 MUST NOT 成为目录总量上限，不能以1000步骤或200工件截断替代继续读取。工具查询目录 SHALL 复用实际步骤与工件，已知原件ID可读不能替代所有目录可发现。缺失/外部原件未加载须如实区分；读取不调用模型或改变执行状态。

#### Scenario: A run contains more artifacts than the old directory cap
- **WHEN** 某Run超过200工件或1000步骤
- **THEN** 调用方可通过续页完整发现目录并逐项定位，跨页父步骤和历史复用引用仍指向真实来源，不只报告truncated而没有后续读取方式

### Requirement: Automatic investigations provide traceable windows for time bounded queries
自动调查 SHALL 在时间限定工具调用前按相关告警的最早/最晚真实发生时间生成默认查询起止，分别向前/后扩展默认3600秒，并保存实际窗口、来源和profile配置；两项扩展量 SHALL 可分别配置，不能因外部提交不收时间参数就将内部窗口一律留空。完整调查按本轮选入成员、定向问题按实际相关成员推导，不因扩大查询时间自动新增Case成员。系统 MUST 区分本轮查询窗口、候选探索日期、用户自选调查执行范围及历史知识独立回看策略。

可靠告警时间不足时 SHALL 保存受影响目标的补查缺口，保留其他分析及可用工具结果；MUST NOT 用当前/入库时间伪造发生时间、将未查询报告为查空或仅因该缺口否定全部结论。系统 SHALL 保持实际派生窗口，不另设最大时间跨度、静默裁剪或自动分窗；沿配置的单次查询超时与条数上限执行，超时/失败记录补查缺口并保留其他有效分析。

#### Scenario: An automatic Case submission contains no explicit time window
- **WHEN** 用户创建Case，未提供外部查询起止
- **THEN** 核心按真实告警时间前后各扩展配置量（默认1小时）并记录来源，正常可用的补查不因缺少用户时间参数被静默禁用；例如历史10:00/10:20对应09:00–11:20

#### Scenario: An affected query has no reliable alert time
- **WHEN** 某目标缺少可推导查询窗口的可靠告警时间
- **THEN** 记录该目标未能补查及原因，其他已有材料分析和无需时间的工具继续，缺口不改写成查空或整轮结论无效

#### Scenario: A derived query window spans widely separated alerts
- **WHEN** 相关告警真实时间相隔较远，默认派生窗口跨度较大
- **THEN** 使用该实际窗口及配置的单次查询超时/条数上限，不裁剪或自动拆窗；查询失败保存真实缺口和回执，其他有效分析继续保留

### Requirement: Log evidence queries use configurable bounded result sizes
日志补查 SHALL 使用profile中的单次条数上限，目标默认case.log_query.max_rows_per_query=50，实际值同时受本轮case.max_rows_per_query政策上限约束；构造请求及工具校验 SHALL 使用同一实际上限，不保留阻止配置调高的隐含50硬门槛。此上限 MUST NOT 解释为Case成员数、整轮所有查询累计条数或C2/知识统一条数。

工具 SHALL 按稳定顺序返回有界业务结果，可多取1条仅用于判定截断；已取得原件和实际上限、返回条数、截断/未知总量保留后台回执，不伪造完整覆盖或把执行台账整包送模型。超出时 SHALL 保留独立有效分析及结果不完整的限制，不自动无限分页或重查。模型业务视图仍受阶段输入容量约束，行数上限不等于Token适配保证。

#### Scenario: A log query has more matching records than the configured cap
- **WHEN** 单次上限为50且查询至少取得51条匹配记录
- **THEN** 业务结果最多50条，后台记录确实有额外结果及原始回执，未取得精确总数则保持未知；不自动继续翻页，不将有限结果冒充完整或拒收全部独立有效分析

#### Scenario: A profile raises the log query cap within the run policy
- **WHEN** profile将日志上限改为100且本轮政策上限允许100
- **THEN** 请求构造与工具校验均采用100，保存该次配置，旧Run的50条策略和原件不变；无需修改业务代码中的数字

### Requirement: Test executions use the real execution flow presentation
4177 SHALL 沿实际请求/触发、task/attempt、Run步骤、模型/查询/组件工件及保存结果展示一次执行，测试来源以独立紫色标识说明，不将红色错误语义用于测试身份。流程主线与组件分支、固定节点详情 SHALL 沿旧查阅布局提供，未执行和未记录不得伪造为完成。HTTP接入证据由既有测试evidence读取并绑定真实主体/task/Run；自动触发不得冒充直接HTTP受理。

#### Scenario: A first Case round has a saved HTTP receipt and its next round is automatic
- **WHEN** 查看同Case首轮和后轮
- **THEN** 首轮显示其实际建案请求与201受理回执，后轮显示自己的自动任务来源和attempt，切换轮次不沿用首轮HTTP/task；每轮均可点击阶段及组件读取本轮实际原件

### Requirement: 普通入站账号的会话写入上下文

Fusion既有会话上下文的保存与空闲关闭 SHALL 在实际所属租户的事务内设置数据库租户上下文，遵守既有RLS；父子会话关联 SHALL 在同一事务保存。逐租户关闭 SHALL 继续保留SQL租户过滤，连接结束事务后 MUST NOT 保留本次租户设置。系统 MUST NOT 通过放宽RLS、固定角色的全局租户或扩展超级用户权限实现普通入站写入。

#### Scenario: 普通账号保存会话并归还连接
- **WHEN** 普通入站账号收到包含合法会话的业务事件
- **THEN** 程序在该事件实际租户的事务内保存会话及其已签发子会话
- **AND** 事务完成或失败后连接不遗留此次租户设置

#### Scenario: 空闲关闭按实际租户执行
- **WHEN** 后台发现多个租户有符合既有空闲条件的派生会话
- **THEN** 每次关闭使用对应租户的事务上下文及SQL租户条件
- **AND** 厂商会话和其他租户不因该次关闭而被结束

### Requirement: 模型生成约束的显式兼容与原合同校验

在明确选择`vllm_grammar_v1`时，提供端Schema SHALL 避免当前语法引擎将非空正文误限制为单字符，或因自由字符串长度约束拒绝正常JSON转义。兼容转换 SHALL 只处理Schema节点，不删除同名业务属性或改写字面量；来源/成员枚举、类型、必填字段及列表容量 SHALL 保持。本地原合同的非空、长度、引用和范围校验 SHALL 继续执行，完整原答与校验结论分别保存；MUST NOT 以兼容转换或正常stop推断正文质量通过。标准profile和实际业务输入 MUST NOT 因这一转换被改写，未知调用结果不得自动重发。

#### Scenario: 正常事件正文包含多字句子与JSON转义
- **WHEN** 已选vLLM profile的事件请求含自由正文Schema
- **THEN** 提供端不使用已确认不兼容的非空pattern和自由字符串长度关键字，允许完整句子及转义表达
- **AND** 实际保存和发送使用同一转换后请求，接收后仍按原非空和长度合同验证

#### Scenario: 兼容输出仍为空白或超长
- **WHEN** 模型返回的正文违反本地非空或长度约束
- **THEN** 保留原答及校验失败，不因提供端省略关键字而接受无效业务结果

#### Scenario: 业务字段与Schema关键字同名
- **WHEN** properties、definitions或字面量中存在pattern、minLength、maxLength或uniqueItems名称
- **THEN** 转换保持这些业务名称和值，只处理对应Schema位置的约束关键字

### Requirement: Model views exclude transport metadata while retaining business facts
A/I/C3/Deep/C6实际请求 SHALL 按路径、容器类型和用途过滤tenant_uid及已识别后台/测试/答案字段，中性测试来源仅供后台识别。规则 SHALL 进入输入profile，不按样本值写死、不全文替换source/id、不改写自由正文。原数据库材料、租户隔离和来源映射 SHALL 保持；有用途的业务来源/ID、未知业务字段及0/false/有效空列表不得误删。

#### Scenario: Nested raw material contains tenant routing and business source fields
- **WHEN** 各实际构造路径读取带tenant_uid、测试传输来源和业务source/id/0/false/[]的材料
- **THEN** 模型请求没有被识别的后台路径，业务内容原值保留，数据库原件哈希及主体来源关联不变

### Requirement: Quality diagnostics preserve conclusions and do not reject the whole answer
系统 SHALL 保留引用正文混入、重复/不足/角色错误引用、证据不足及不适用领域缺限制说明等输出的原结论/判定/声明范围，记录质量问题并继续。上述问题 MUST NOT 单独造成整份拒收、删除结论或改判unavailable。非法引用不得建立有效证据绑定，合法引用可去重链接；原引用和正文保持，结论角色仍为prior_analysis而非已核实事实。结构/身份不可解释单元 SHALL 单独隔离，其他独立有效内容保留。

#### Scenario: C6 omits limitations for a non-applicable domain
- **WHEN** C6结论及身份结构完整，但有unapplied_domain_needs_limitations、重复或范围不足引用
- **THEN** 保存原结论和业务判定，另存质量问题并继续正常保存/采用资格检查，不仅因这些问题整份拒收；历史拒收不回填

### Requirement: Every stage saves a complete receipt without inventing model content
新执行 SHALL 对完整、部分和无输出使用同一阶段处理路径，沿source_snapshot保存socai2.stage-delivery.v1回执，记录实际身份/输入、原答引用及哈希、调用与本地状态、解析/截断、交付可用性、保留/缺失/无效单元、质量和下游用途。程序回执完整 MUST NOT 解释为模型答案完整。无响应 SHALL 明确no_response，不生成虚假原答或verdict。公开告警字段合同保持；原件与回执通过现有步骤/工件目录及content_url读取，GET不得重解释旧拒收为accepted。

#### Scenario: A model returns only whitespace
- **WHEN** 已收响应没有可解释业务单元
- **THEN** 原答逐字保存，回执delivery none、缺失/错误可读，下游仍可用冻结原件继续；不以补默认业务字段构造成功分析

#### Scenario: A page cannot read one artifact
- **WHEN** 某一原件缺失或HTTP读取失败，其余步骤仍可读
- **THEN** 该卡展示真实缺失/读取错误，其他流程保持可见；不能把未产生原答与读取失败混为正常空结果

### Requirement: Truncated replies retain closed independent units and continue downstream
任一阶段finish_reason=length SHALL 留截断标志并尝试严格解析；完整JSON按单元校验使用，不因length整体拒收。非完整JSON SHALL 沿原结构仅恢复已闭合、身份/范围可解释的独立单元和数组项，保存原路径/字符区间/哈希及冻结来源映射；不得补括号冒充完整答案、拼造字段或将孤立片段当事实。stop的局部结构错误使用同一保留规则，引用质量按独立规则记录。

未闭合字符串/转义/数字、冲突键或未知主体单元 SHALL 隔离；依赖它的动作不得执行。后续可使用已保留分析及独立原件；只有完整且通过冻结目标/绑定/权限检查的操作单元可派发。C3已保留项 SHALL 不因唯一补答失败而丢失，C6仍有可用材料时继续；C3补答上限配置0/1默认1，不叠加整案重试，不为A/I/Deep/C6新增自动续写。

#### Scenario: A complete answer reports length
- **WHEN** length响应含完整合法JSON及可解释业务单元
- **THEN** 保留截断诊断，单元正常传递；交付完整性按实际内容判断，结构通过不代表质量通过

#### Scenario: A finding array ends during its second item
- **WHEN** F1完整闭合且身份可核实，F2字符串中途截断，外层数组尚未闭合
- **THEN** F1进入部分回执和下游选材，F2记缺失，不补F2或抹掉F1；没有合法完整followup时零派发该动作

#### Scenario: C3 completion fails after the initial reply retained useful content
- **WHEN** 初答已有可用单元，配置允许的一次补答失败或再次截断
- **THEN** 初答/补答分别保存，独立有效单元仍供C6，不覆盖初答、不第二次补答、不自动全案重跑

#### Scenario: Deep retains an answer without a complete control decision
- **WHEN** Deep的answer对象完整且符合冻结问题和结构，action/binding_id/reason中存在缺失或冲突
- **THEN** 原answer及其状态/范围和引用质量保存为独立材料，经严格阶段回执提供给C6；不补控制字段，不派发query，不自动续写；半answer只记录缺口

#### Scenario: Deep query requires all frozen control dependencies
- **WHEN** Deep输出请求query但binding未提供、字段截断或动作组合不合法
- **THEN** 保存原答及相应缺失/无效单元，查询派发数为零，其余有效答案与独立下游继续；完整合法stop/length答复使用同一个接收器

### Requirement: Local call failures do not cancel independent downstream work
阶段 SHALL 在调用边界区分未发出故障、已发出后超时/断连、明确失败响应及工具未接通，保存真实状态和已收到且可定位的部分内容。异常后 SHALL 继续依赖齐备的独立步骤，缺硬依赖的步骤保存skip/unavailable原因，最终保存可读收尾；不得要求人工解除或阻塞其它任务。没有实际接收缓冲时不得凭空恢复正文。未知动作不重放；调用超时/预算/重试均受profile约束，既有默认60秒最多一次只适用于已确认可重试的任务失败，不因局部可选步骤重跑全案。

#### Scenario: A Deep call times out after dispatch
- **WHEN** 该调用本地已超时收尾而远端结果未知，其余事实仍可读
- **THEN** 原调用保持unknown、无自动重发；其他独立步骤及预算允许的C6继续，最终unknown收尾工件可读且释放本地槽，下一任务可执行

#### Scenario: A query response disconnects after returning complete records
- **WHEN** 网关实际保留部分已接收且可定位的完整业务记录
- **THEN** 这些记录以部分结果传递，真实中断和缺口单独保存，不声称查空/完整；无正文时明确不可用，其他材料继续分析

### Requirement: Continuation acceptance includes reproducible truncation and transport mocks
测试 SHALL 使用冻结完整A/I/C3/Deep/C6输出的派生mock，覆盖关键结构切点及固定seed的有限随机切点；保存母本哈希、字符或字节位置、派生片段哈希及独立期望。验证 SHALL 经过实际接收、恢复、后续模块输入构造，并选择代表样本核真实PG保存/HTTP/4177读取，不仅测试解析函数。异常mock SHALL 包含连接前失败、发出后超时及中断有正文/无正文；原历史不改写，不为制造length重复调用真实模型。

#### Scenario: Replaying a truncation test uses the same seed
- **WHEN** 使用同一母本/配置/seed重新生成mock
- **THEN** 切点与片段一致，可定位每个保留单元的原文；下一模块只使用校验后的完整单元，错误、缺口、调用次数和最终读取符合回执
