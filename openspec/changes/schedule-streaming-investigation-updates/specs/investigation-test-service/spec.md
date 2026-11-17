## ADDED Requirements

### Requirement: Test ledger publication and read API are independent of investigation execution
测试账本 SHALL 以schema_version=1保存批次、用例断言、真实业务身份映射、准备、质量及显式登记的可查阅证据。发布 SHALL 使用明确profile、原子写入和预期revision；旧revision及结束批次 MUST NOT 被覆盖追认。测试只读HTTP SHALL 独立提供批次、用例、操作、准备、质量和证据读取，分页绑定筛选与记录版本；账本错误、合法空态及未评估质量 SHALL 分开展示。HTTP启动/读取 MUST NOT 连接业务执行依赖、自动发布记录或恢复测试。

#### Scenario: A waiting operation is persisted and read after restart
- **WHEN** 显式发布真实task映射且run_id为null的批次，随后重启查阅服务
- **THEN** 同批用例和操作原值可读，Run仍为空，账本和业务记录不会因GET或启动被改写

#### Scenario: A record changes between pages
- **WHEN** 列表cursor对应的账本修订已变化或筛选不匹配
- **THEN** 返回明确cursor_stale或非法游标，不默默继续并遗漏/重复记录

#### Scenario: Evidence is missing or corrupted
- **WHEN** 查询未登记ID，或已登记原件缺失/size或hash不符
- **THEN** 未登记返回404，已登记不可读返回503；不按客户端路径读取其他文件，不返回损坏正文冒充原件

### Requirement: Reusable investigation scenarios include complete context and future dependencies
测试配套 SHALL 覆盖正常告警入站、A/I、Case完整调查、持续更新、H、定向、手动综合、采用/结束及对应HTTP保存读取，保留尚未实现能力的用例、数据和接口依赖。场景 SHALL 将告警、可查询上下文、基础/知识材料、人工输入、操作时间线及独立预期成套定义，保持来源身份/时间/原文一致；期望答案 MUST NOT 进入投递或模型输入。测试与业务Run身份 SHALL 分开，每次执行使用独立批次并保留历史证据。

#### Scenario: A Case capability has a contract but no implementation
- **WHEN** 定向或综合合同已定而实际模块或HTTP尚未交付
- **THEN** 对应场景和预期继续保留，执行状态为依赖未就绪并注明责任模块；不删除用例、不以替身标记真实全流程通过

#### Scenario: Context is prepared for a normal investigation
- **WHEN** 场景生成关联告警及认证/进程/网络上下文
- **THEN** 正常投放前核实际来源查询、时间/主体/原文及按工具语义定义的对照；生成文件存在本身不代表查询接通

#### Scenario: Model inputs do not reveal authored test identity
- **WHEN** 新测试批次生成业务材料并经实际 A/I/Case 输入构造器准备模型请求
- **THEN** 程序以中性固定来源及独立账本识别测试身份，模型业务材料不包含测试标记、批次控制字段、作者预设结论或答案；来源路由元数据不进入分析视图，原始观察、检测角色、有效0/false/空列表保持，控制原件留后台核对

### Requirement: Preparation checks and cleanup preserve unrelated data
测试服务 SHALL 使用显式profile核目标环境、当步所需数据库增量/约束、服务/消费状态、Kafka坐标、Redis任务及上下文来源，先产生检查与必要清理计划。清理 SHALL 限于明确且获准的测试资源范围，保存备份/分步回执并验证保留对象；MUST NOT 沿旧固定21脚本扩大到共享数据、全库/全卷或全部项目Topic。共享Topic消息不能按租户选择删除，无法安全划分时 SHALL 使用独立资源或新批次。未知执行和跨存储部分失败 SHALL 保留，不自动重投、重清或恢复消费者。

#### Scenario: A shared Topic contains records from other batches
- **WHEN** 清理计划发现同分区含本批及其他批次消息
- **THEN** 不执行前缀全量删除或重置共享组，改为明确独立资源/消费起点，并保留原数据和坐标

#### Scenario: The owner authorizes removing previous test executions
- **WHEN** 负责人明确要求清除本项目此前测试告警、事件、调查及关联信息
- **THEN** 按实际资源清单停止测试写入后清理这些运行记录及其消息、缓存和检索来源，保留结构、配置及其他项目数据，逐项核零并使查阅入口显示真实空态，不因清理自动重派或重灌旧数据

#### Scenario: A target schema does not match the selected runtime
- **WHEN** 预检发现当前模块需要的任务或Case分配增量未应用
- **THEN** 标记依赖不满足，不投放该步告警、不静默回落其他库、不对已有库运行空库初始化

### Requirement: Real model execution and model quality are assessed separately
主流程实际进入的分析环节 SHALL 使用真实模型请求并保留输入、提示/Schema、原答、查询回执、校验、装配、保存及HTTP读回。模型正文质量 SHALL 独立记录并允许后续专项处理，不作为本次流程通过门槛；程序结构、身份、材料传递、保存/读取阻断仍 SHALL 如实失败并处理。受控依赖和历史重放 SHALL 明确标记，不冒充真实模型；未走到分支 SHALL 记未覆盖，不循环采样或伪造结果满足正常路径。

#### Scenario: A real answer has quality issues but is processed correctly
- **WHEN** 模型真实原答有解释或引用问题而程序按合同保存、收尾并可读
- **THEN** 分别记录该流程实际结果和质量问题，原答及原NOT_PASSED保留；不能用accepted或HTTP成功宣称质量通过

#### Scenario: A failed answer leaves the normal success branch untested
- **WHEN** 模型格式/截断导致本轮仅验证了失败或部分交付路径
- **THEN** 保留失败路径证据和正常路径未覆盖状态，不插入伪造Result、不悄悄放宽接收规则或重派旧Run

### Requirement: The independent test service owns test records and viewer delivery
测试配套 SHALL 作为独立服务交付，包含场景/驱动、批次账本、测试只读API及4177查阅端，并有独立版本、配置、发布清单与持久证据目录。测试服务 SHALL 通过正常业务入口驱动被测服务，不复制调查执行逻辑；启动/升级/读取查阅服务 MUST NOT 自动清理、投递、调用模型或重派中断批次。测试服务发布 SHALL 不隐含调查核心发布或共享数据清理。

#### Scenario: The viewer service restarts during a test
- **WHEN** 查阅进程重启并重新读取已持久批次
- **THEN** 批次与证据仍可查，不因进程启动恢复未知执行或新建业务Run

#### Scenario: The test package is published independently
- **WHEN** 通过验收的测试服务和4177发布到明确目标
- **THEN** 记录实际服务/页面/合同版本及上游依赖，保留旧批次；调查核心、迁移与消费者不会因这次发布自动改变

### Requirement: The viewer obtains current investigation data through HTTP
4177日常查阅 SHALL 通过调查HTTP取得主体、分析任务、Run、结果、步骤和原件，通过测试只读API取得批次、准备回执、预期/核对和质量记录。业务ID/来源 SHALL 取真实响应与关联，排队无Run、失败无Result及跨Run复用保持真实；读取 MUST NOT 改业务状态或触发模型。live模式 SHALL 不依赖手工导出HTML、SQL/SSH查询生成页面；配置化同源代理 SHALL 仅提供必要只读路径。

#### Scenario: A submitted task has not created a Run
- **WHEN** 测试操作已有真实task_id而任务GET返回run_id为空
- **THEN** 4177显示受理/排队及真实原因，后续按配置刷新；不造Run或通过重发POST获取状态

#### Scenario: A user opens a large or reused artifact
- **WHEN** 步骤与原件目录通过分页返回完整引用
- **THEN** 4177沿真实content_url按需读取正文并保留来源Run/主体、可用性和hash，不以旧摘要上限截断完整目录

#### Scenario: A visible task reaches its terminal state
- **WHEN** 页面按显式配置刷新当前可见的活动任务或Run，随后读取到终态，或页面转为隐藏
- **THEN** 停止该对象的自动轮询并保留手动刷新；切换对象后迟到的旧响应不得替换新对象内容，页面读取不会重新提交分析

#### Scenario: A live batch belongs to another environment
- **WHEN** 所选live批次的环境与当前只读代理绑定不一致
- **THEN** 页面保留批次与来源说明并明确阻止该批业务读取，不把其主体ID发往错误环境，也不回落归档冒充实时结果

### Requirement: Live reads and archived evidence have explicit provenance
4177 SHALL 明确显示live/archive、环境及观察/捕获时间；存在测试batch时 SHALL 在辅助来源/测试记录中保留其身份，不要求所有业务对象都有batch，不将其作为主体导航层级。当前API不可用、未产生结果、原件不可用、未评估质量与合法空结果 SHALL 分开表示；API失败 MUST NOT 静默回退旧快照并声称实时。现有快照 SHALL 保留为可选归档；归档读取不得补造当前状态、analysis_task或模型执行。

#### Scenario: The investigation API becomes unavailable
- **WHEN** live模式读取上游失败
- **THEN** 显示不可用及最后成功观察时间，可保留标注为旧的已显示内容；不静默换库或替换为静态批次

#### Scenario: A historical batch has no analysis task records
- **WHEN** 用户明确选择该批归档查看
- **THEN** 显示原快照与捕获时间及真实空关联，不为适配新页面迁入或伪造业务记录

### Requirement: Business subjects are discovered without test ledger prerequisites
工作台 SHALL 提供Case（默认）、事件、告警三类切换，直接通过现有调查HTTP列表读取对应主体并按真实ID进入执行目录；MUST NOT 以测试批次、Operation或手工导出作为主体发现前置。同一环境/租户/类型/主体ID SHALL 只显示一项，即使多个测试账本或补证引用它。测试身份 SHALL 仅以独立紫色来源标识表达，红色保持错误语义；测试账本仅为辅助来源和核对记录。GET、页面刷新和查阅服务重启 MUST NOT 启动分析或测试。

#### Scenario: A real Case has no test ledger
- **WHEN** 调查HTTP可读Case及其执行，但没有该Case的测试账本
- **THEN** Case仍出现在默认列表并能按ID读取轮次、步骤、原件和结果；测试记录缺失不阻断业务查阅

#### Scenario: Two test records reference the same Case
- **WHEN** 原批和展示补证都引用同一Case
- **THEN** 主导航只显示一个Case，两个来源在辅助记录保留，不制造第二次业务执行或重复计数

#### Scenario: A subject has a task without a Run
- **WHEN** 主体任务已受理但未开始，或无变化检查跳过且没有新Run
- **THEN** 页面从该主体任务接口显示真实排队或skipped/no_changes，不将空Run列表解释为没有任务

### Requirement: A selected round presents its frozen upstream analysis
Case每轮 SHALL 固定选择实际Run，通过该Run输入manifest和C1工件读取告警成员、分诊与事件分析来源，组合本轮A/I/Case流程，MUST NOT 用当前latest或当前成员覆盖旧轮次。沿用/新增 SHALL 根据可核实的原主体、材料、分诊和源Run/工件身份确定；缺失来源或两个null MUST NOT 被视为沿用。来源身份、可用性、选入范围与实际交付覆盖 SHALL 分开表示，partial/none来源或选入成员数不得冒充完整结论/覆盖。事件 SHALL 独立展示多轮诊断及各轮冻结输入/结果；告警 SHALL 提供简单的事实与分诊详情，真实失败/重试可查，二者均不要求建Case。现有属性、流程组件和步骤详情 SHALL 优先复用。

#### Scenario: The whole Case grows while the independent Case remains unchanged
- **WHEN** 整案第一轮使用3条告警，第二轮使用4条，另一个单告警Case只有1轮
- **THEN** 各轮展示各自冻结范围；第二轮沿用的3份分诊、新增1份分诊及选入的新事件分析分别标明，不把上游沿用材料画成本轮再次执行

#### Scenario: A frozen source cannot be read
- **WHEN** 当前选中Run的来源身份缺失、原件不可用或读取失败
- **THEN** 对应节点显示真实缺失/不可用/错误，保留其他已读流程；不从其他轮次或当前采用结果补成成功

#### Scenario: An incident has multiple diagnosis rounds
- **WHEN** 同事件存在首轮与增量后的两次实际诊断
- **THEN** 页面分别列出两轮及各轮自己的冻结范围、流程和结果，不用最新事件成员替换首轮输入

#### Scenario: A task has no captured HTTP exchange
- **WHEN** 业务任务可读但没有完整原始HTTP交换回执
- **THEN** 显示实际source/intent和任务关联，原请求注明未记录；不从Swagger或空request拼造请求，不因此阻断该主体查阅

### Requirement: Test execution uses explicit small data parts
独立测试执行模块 SHALL 提供一个交互式验收脚本，读取明确数据目录和profile，先校验并列出part/材料数量/执行计划，有part1时默认选择、没有时提示选段；支持显式运行及手动追加指定尚未执行part。首版工作台 SHALL 负责查阅，不以网页运行按钮为交付前提；未来增加控制时 MUST 复用相同脚本核心与执行状态。数据包 SHALL 分开告警、独立上下文、程序预期及运行配置，沿当前业务合同保留事实、时间和关联。有上下文的段 SHALL 先核ACK及真实入湖，再按数字文件顺序和配置间隔发送少量告警；下一段 SHALL 等上一段所需任务终态且结果或问题保存/读回后才可手动追加。MUST NOT 默认投放全部模板、目录或后段，MUST NOT 将Kafka ACK、固定间隔或N=1视为整组业务完成。控制入口 SHALL 归测试模块而非调查业务Swagger，查询入口保持无副作用。

#### Scenario: The directory includes several parts
- **WHEN** 用户选择含part1和part2的数据目录并发起运行
- **THEN** 只运行part1；part2在前段满足完成条件且用户明确追加前保持未发送，页面刷新不改变该状态

#### Scenario: Analysis is still running after all messages are acknowledged
- **WHEN** part1全部Kafka消息已ACK，但仍有该段所需A/I/Case任务在执行
- **THEN** 显示实际分析进度，不允许以ACK或定时间隔越过组间完成条件投放part2

#### Scenario: A terminal part contains quality diagnostics
- **WHEN** 该段真实任务终态、结果或问题已保存并读回，但模型有引用或正文诊断
- **THEN** 保留质量未通过结论，允许合同认可的后续步骤；不为取得质量通过而重采样或重派旧任务

#### Scenario: An already executed part is requested again
- **WHEN** 同一测试执行重复提交已发送part，或其发送/POST结果尚不确定
- **THEN** 先读取保存的意图和真实回执，不重复发送；已结束账本不改回运行，继续测试不得覆写旧段/原答

#### Scenario: A saved acceptance session is inspected offline
- **WHEN** 使用者status读取已准备执行及本地保存的段回执
- **THEN** 程序校验执行/段/session绑定并按声明顺序写一个新报告，实际身份只取保存记录，来源标本地观察；不读取连接凭据、不联网或重启执行，prepared状态不覆盖实际进度

#### Scenario: A claimed terminal part lacks verified saved closure
- **WHEN** 段目录已存在但回执缺失/损坏/身份不符，或终态声明没有对应保存读回、仍有未结束任务
- **THEN** 状态报告显示需核对及原件路径，不把该段当未执行或允许重发，不给下一段准入；其他可读事实和原失败保留

#### Scenario: An ended attempt has an unknown Run
- **WHEN** task已failed、attempt已结束或中断且outcome为unknown，Run为unknown，问题及保存读取回执均存在
- **THEN** 分别呈现任务、尝试和Run状态，允许下一合法未发段，保留原unknown且不重试旧操作；报告不把模型质量或无有效比较基线改成成功

#### Scenario: A later part has a record before its predecessor
- **WHEN** 保存目录出现跳段执行，或前段仍未确认完成而后段已有记录
- **THEN** 报告按声明顺序列出矛盾并要求先核对，不自动填补前段、忽略后段或发送下一段

#### Scenario: One next part is explicitly appended to the same session
- **WHEN** 使用者明确append同一冻结session的下一未发送part，前段保存闭环且实时目标、身份和执行状态核对通过
- **THEN** 只发送所选段，先核context实际入湖，再逐告警等分诊终态，检查本段事件和原Case；累计实际身份与本段发送数分列，旧段与原答不覆盖，未知操作不重试

#### Scenario: Appended material updates an existing case
- **WHEN** 本段材料影响前段已创建的Case，或自动任务已形成实际后轮
- **THEN** 沿原Case ID执行check而不重建或强制rerun；整案按真实成员扩展，固定告警范围保持；分别核各轮冻结成员、前轮比较和本轮新增Run/Result，成员变化但缺少覆盖当前范围的新Run或新Run无Result时明确记录问题，首轮结果不能充当后轮交付

#### Scenario: Live state disagrees with the saved append candidate
- **WHEN** 本地状态给出下一候选，但实时前段任务未结束、主体/执行关联已不符、本段身份已存在，或同路径连接配置摘要已不同于前段真实预检
- **THEN** 保存需核对的原因并停止本次投递，不用离线状态绕过实时核对，也不自动恢复或重发已有操作

#### Scenario: An interactive operator views or leaves a prepared execution
- **WHEN** 使用者打开session后只查看、输入空行、退出或遇到EOF
- **THEN** 只呈现同一prepared的计划与保存事实并写外部交互观察回执，不读取连接凭据、不投递、不取消远端任务或永久关闭执行；之后可用新输出目录重开，旧段与未发段状态保持

#### Scenario: An interactive operator explicitly executes one displayed part
- **WHEN** 使用者明确选择显示的首段或下一可追加段
- **THEN** 重新核对当前状态后仅调用原run或append一次；候选变化要求重新选择，返回后读保存状态，绝不自动执行后段；无默认首段时需明确输入段名

#### Scenario: Finishing interaction leaves some parts unsent
- **WHEN** 使用者选择结束并报告，而仍有未发段或需核对的旧执行
- **THEN** 单独保存结束原因、报告入口及未发/阻断状态；结束交互不表示全部执行成功，不改写旧段或允许重派未知操作

### Requirement: Acceptance materials have one documented format and explicit conversion
新材料 SHALL 使用scenario.json及partN/alerts、partN/context的单记录JSON目录，沿当前入站告警与上下文合同。场景配置、明确环境profile及投递段的告警 SHALL 必须提供；独立上下文 SHALL 按场景需要，声明验证查询时必须提供可查来源，资产/知识/人工材料及扩展预期 SHALL 明确可选和接入状态。旧v2 JSONL/模板 SHALL 离线转换到新目录并记录数量、字段及关联校验，原件与旧失败保持；不得从嵌入telemetry伪造独立上下文或混入作者答案/旧模型结论。新执行身份映射 SHALL 独立且跨part一致，后台tenant/来源关联保留，测试控制信息不进入模型。

#### Scenario: Existing S01 and S04 materials are converted
- **WHEN** 转换已准备的v2首批与追加材料
- **THEN** 逐条生成part1与part2，数量和事实/引用对应原件，执行台账及答案留旁路，不发送数据、不修改旧执行结果

#### Scenario: Optional context is absent
- **WHEN** 场景仅提供告警且未声明验证日志查询
- **THEN** 可运行适用告警/事件流程并明确日志查询未覆盖；声明必须查询而缺来源的场景在投放前报告材料缺项

#### Scenario: An offline package is inspected without executing
- **WHEN** 使用者提供scenario、显式profile和按part分段的业务输入，或从支持的旧v2材料转换
- **THEN** 程序按当前业务格式校验并列出数量、来源关系与Case计划，默认只选存在的part1，无part1时要求明确选择；不联网、不生成新执行或修改原目录，旧身份必须在实际发送前另行绑定为新执行

#### Scenario: Two case scopes share the same first part
- **WHEN** 场景同时声明按事件建案和按固定告警建案，并在后续part检查两者
- **THEN** 计划保留各自材料别名与范围，不预造未来主体ID或将固定告警案自动扩大；数字文件顺序不替代业务关联，独立context只能引用已准备的当前或前序段

#### Scenario: Material templates become a new execution
- **WHEN** 使用者明确prepare新execution_id并提供目标tenant一致的材料和profile
- **THEN** 程序统一映射全包告警/来源及嵌套来源身份，保存old→new和冻结wire后重新读取；保留原时间/正文/实体，不在prepare联网投递，新ID不被解释为已经隔离历史归并或查询

#### Scenario: One part runs through real processing
- **WHEN** 使用者显式run已准备的首段，所需连接和本场景新身份/实体检查通过
- **THEN** 程序按context ACK→实际湖读回→逐告警发送及A终态→必要I check→Case受理与终态→PG/HTTP同源读回执行，持久保存每步意图/回执；质量问题单列不阻断合法下游，unknown不盲重派，其他part保持未执行

### Requirement: The acceptance script runs from a versioned Docker image
交互验收脚本 SHALL 连同所需依赖按明确版本打包为Docker镜像；材料/配置 SHALL 从只读挂载读取，结果/回执 SHALL 写入持久结果目录，凭据不得烘入镜像或报告。脚本 SHALL 通过显式profile连接已有PG、湖、Kafka和业务HTTP，不在容器内启动另一套被测服务。启动 SHALL 先校验并列计划，不自动清库、启消费者或投放；退出和重启 SHALL 保留原执行回执，未知操作不得盲目恢复。数据库核对 SHALL 仅用于验收脚本必要事实检查，工作台仍只读业务HTTP。

#### Scenario: The acceptance container exits after a part
- **WHEN** Docker中的交互脚本完成一段并退出
- **THEN** 宿主挂载目录仍有该段请求/回执/验收结果及身份映射，重启能读取这些记录且不会自动重发

#### Scenario: A dedicated acceptance image starts without an operation
- **WHEN** 以固定基础和依赖构建的验收镜像启动且未明确指定操作
- **THEN** 入口展示验收命令帮助，不启动查阅服务或投递；八个命令沿同一验收实现，运行所需驱动包含在镜像中，不依赖宿主源码或Python环境

#### Scenario: The same prepared session is opened in a later container
- **WHEN** 新容器按相同容器内路径挂载原只读材料/配置与持久结果，并选择已有prepared
- **THEN** 冻结的配置引用、身份及旧回执保持，查看和报告不读取业务凭据或联网；新操作输出另建，旧段和未知状态不重派，容器退出后报告和可见输入输出仍可从宿主读回

### Requirement: Test observations and evidence are assembled by the execution program
测试执行模块 SHALL 自动保存每步意图、原始请求/回执、实际主体/task/attempt/Run/结果映射、检查及原件索引，按真实记录计算数量、usage与质量诊断。最终报告 SHALL 分步列通过/失败/未覆盖，核本段告警保存、事件关联、所需任务/Run/结果、追加后轮及冻结前轮、PG/湖必要事实和业务HTTP读回，附工作台及证据入口；检查范围取当前场景，不扩为全表全接口对账。相同执行源码 SHALL 能通过更换材料和配置运行另一个小场景，不要求Codex或使用者逐批写执行脚本、补身份或手工编写账本。测试精确核对 SHALL 由程序执行，不新增模型调用来生成计数、篡改原答或判定测试通过；正文质量未全面评估必须保持。

#### Scenario: The operator switches to another data package
- **WHEN** 用户提供另一份符合合同的小数据包与显式配置
- **THEN** 同一执行入口完成适用步骤并生成可查询状态和证据，无需修改执行源码；未进入的业务分支如实未覆盖

#### Scenario: A model answer is exported for the workbench
- **WHEN** 执行程序汇总该Run模型请求、原答、装配输出和质量记录
- **THEN** 原答与请求身份保持，统计只来自真实回执，装配/恢复结果不冒充原答，质量诊断不改写业务执行状态

#### Scenario: A session report aggregates cumulative saved parts
- **WHEN** report读取同一session的多段累计快照
- **THEN** 主体及执行按各自ID去重、模型按request artifact关联原答和usage，列各轮冻结成员与比较关系、阶段检查、问题和原件；报告写到新外部目录并核保存读取，不联网或新增模型，旧原件保持

#### Scenario: Saved reporting evidence is incomplete
- **WHEN** 已启动段缺快照、原答或usage，或局部回执损坏/发生冲突
- **THEN** 保留可读事实并注明未观察/统计不全及原件路径，未知数量或费用不补零，不搜索其他执行补成成功；质量诊断与流程完成分列，报告生成不证明正文正确

### Requirement: Test source identity is configured and classified per frozen round
新生成测试材料 SHALL 使用配置中以lyc开头的中性source/connector_type；后台来源及tenant关联保持，命名不得写入模型业务观察或模型消息。工作台 SHALL 从业务HTTP所选Run冻结告警来源及配置前缀判断测试材料，不依赖另行发布测试账本，不按标题或正文猜测。全部确认成员匹配显示测试数据，部分匹配显示含测试数据，来源缺失/读取失败显示未确认；历史批次登记只能用于对应实际Run的补充标识，MUST NOT 将一个主体关联过测试批次扩展为全部轮次均为测试。

#### Scenario: A new lyc source has no published test ledger
- **WHEN** 新材料source/connector_type以配置的lyc前缀开头，Run通过业务HTTP及冻结来源可读且没有测试账本
- **THEN** 所选轮次自动显示紫色测试数据标识，仍通过业务HTTP展示原流程/结果，模型消息不含路由来源标识

#### Scenario: Different rounds contain different source mixtures
- **WHEN** 同Case旧轮全部为lyc来源而后轮包含普通来源，或任一轮来源缺失
- **THEN** 按各轮冻结成员分别显示测试数据、含测试数据或来源未确认，不用当前成员、其他轮次或主体级批次关系补造身份

#### Scenario: Existing non-prefix executions are inspected
- **WHEN** 已冻结旧材料的来源不以lyc开头，但测试账本明确登记所选Run
- **THEN** 保留原来源并显示该轮登记测试关系，其他未登记轮次不继承；旧原答/业务记录不重写，新生成材料使用新命名

### Requirement: Acceptance reports open exact saved subject runs
验收报告 SHALL 根据显式展示配置和本会话保存的真实主体/Run生成工作台链接，不修改冻结会话、不探测业务连接或调用模型。配置 SHALL 绑定源会话环境与目标工作台环境；未配置时旧报告仍可生成。页面 SHALL 核对链接环境、主体和Run身份，打开指定轮次；链接目标无效或不存在时 MUST NOT 自动选择最新轮次或其他对象。

#### Scenario: The report opens either round of the same Case
- **WHEN** 已存报告包含同Case的首轮及后轮，用户分别点击其工作台链接
- **THEN** 页面通过现有业务HTTP打开对应真实Run及其冻结材料，不受当前列表首页或最新轮次影响；刷新仍保留该选择

#### Scenario: A target or its environment is unavailable
- **WHEN** 链接缺少必要字段、环境不符、Run不存在或不属于所指主体，或读取失败
- **THEN** 页面保留目标身份并显示错误/未读到，不显示另一轮作为该目标结果，也不触发任何业务执行

#### Scenario: Reports retain offline compatibility
- **WHEN** 旧会话重新生成带展示配置的报告，或者没有提供展示配置
- **THEN** 配置化链接仅由真实已存Run生成；无配置时明确无链接，两种路径均保留原件及原报告、不读取连接凭据、不产生网络调用
