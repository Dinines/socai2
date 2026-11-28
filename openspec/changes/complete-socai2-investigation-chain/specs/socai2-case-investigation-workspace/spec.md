## ADDED Requirements

### Requirement: Workspaces distinguish effective risk from round opinions and show changes

4173/4177 SHALL 从相同后端生效值展示事件/Case 的严重程度及优先级；列表、详情、筛选/统计及导出同源，指定 Run 读取当轮意见。页面 SHALL 同时可查当前来源/依据、本轮意见及未应用原因、人工优先级及系统建议，不能用演示数据或当前值补历史空项。自动上调/人工升降/降低建议 SHALL 有可追溯时间线；生效修改和活动同事务保存，重复操作不重复提醒。

#### Scenario: An automatic escalation is opened from the header
- **WHEN** 当前等级中→高，用户从页头变更提示进入时间线
- **THEN** 看到真实前后值、时间、理由和来源Run，并可打开该轮意见；人工历史不被抹掉，旧轮次不读最新值冒充原意见

#### Scenario: The model recommends a downgrade without applying it
- **WHEN** 当前高、本轮建议中
- **THEN** 页面显示“建议中，当前高，未自动降低”，普通提示而非执行错误；同等级无变更提示，相同未应用建议的逐轮记录保留但不重复弹提醒；测试来源继续紫色

### Requirement: The audit workspace reads task time without replacing file logs

4177 SHALL 展示受理、确认入队、任务/尝试开始及本地结束、当前实际步骤与耗时、原状态/原因，均来自任务HTTP及真实关联。排队、准备、实际执行、预约重试、本地结束且远端unknown SHALL 分开；缺时间保持未知。页面 SHALL NOT 伪造卡死判定、堆栈或作为文件日志唯一载体。

#### Scenario: A waiting task has no confirmed enqueue or Run
- **WHEN** 已受理任务尚无确认入队时间，也无真实Run
- **THEN** 显示受理事实及未确认/未记录状态，不将等待时间写成执行时间，不借用另一任务步骤；后台异常沿配置日志文件排查

### Requirement: Internal audit flow exposes preserved node details beside the flow

4177 内部调查查阅页 SHALL 在宽屏左侧显示紧凑流程、右侧显示所选节点详情，在窄屏按上下顺序可用。详情 SHALL 来自该节点实际保存的步骤、Run 和工件，分开显示模型提示词、输入消息和约束、原答、执行/校验失败原因以及原件入口。缺失、跳过、未分派、零行和部分交付 MUST 保留实际含义，不推断成功或补造输出；选择节点不得产生模型调用或业务写入。

#### Scenario: A deep model call failed before choosing an action
- **WHEN** Deep 模型已调用但因校验失败未生成有效动作
- **THEN** 流程保留可点击的实际模型调用，右侧可查原提示词、输入、原答及校验错误，未记录动作保持未记录

#### Scenario: The reviewer switches run or selects an absent node
- **WHEN** 用户切换模块/轮次或选择没有记录的节点
- **THEN** 清除上一节点内容并显示所选轮次的空态，不把其他轮次输入输出留在详情区；节点可通过键盘选择，原件仍可单独查阅

### Requirement: Internal audit views separate business conclusions from execution and citation quality

4177 SHALL 优先展示当前source_run_id实际保存的A判断/理由、I摘要/诊断及Case结论，运行状态、交付完整性、引用质量、材料缺口和采用状态分别呈现。stage_output_saved SHALL 表示正常保存结束，不作为错误或业务结论。模型原答、程序派生输出和当前采用判断须角色明确；纯引用错误不隐藏原业务结论，历史失败状态不追认为成功。

#### Scenario: A saved stage finishes normally with citation diagnostics
- **WHEN** A/I/C结果正常保存且有独立引用问题
- **THEN** 同Run原结论可直接读取，质量问题并列显示，正常结束不报错；未采用分析不冒充当前判断

#### Scenario: A selected Run has no saved business result
- **WHEN** 所选Run没有同主体且source_run_id匹配的已保存业务结果，或只留下没有结论正文的取消/未完成记录
- **THEN** 明确显示本轮没有已保存业务结论，保留该Run原答/错误/空态入口，不用其他Run、当前采用或模型原答推断替代
- **AND** 采用状态分别说明保存时回执和快照中的当前采用；缺少当前判断来源时显示未核对，不推断已采用或未采用
- **AND** 已存在的取消/未完成记录仍展示其原状态，不把记录存在解释成已有业务结论

#### Scenario: C3 needed a section completion
- **WHEN** 同C3阶段保存初答、补答及合并结果
- **THEN** 每次实际输入/请求/原答和程序合并分别可查，字段来源可追溯，失败及未补字段如实显示

#### Scenario: Large module input is opened
- **WHEN** 用户展开超过预览长度的本Run原件
- **THEN** 沿原件入口读取完整内容，折叠只影响展示，不裁剪原件；切换Run清空旧详情，读取无业务写入或模型调用

### Requirement: Page data readiness is independent of investigation workflow maturity

本轮页面数据合同 SHALL 以字段可持久保存/回查、来源关联及确定派生规则验收，允许通过真实数据库读回与导出交接，不要求先完成模型质量、VPN对照、实时页面写表或跨域接线。已有字段但当前无样例 SHALL 标为未产生数据，不当成结构缺口。原页面模板保持，允许必要字段绑定及缺值呈现适配；缓存、示例文案和演示值不能作为唯一业务数据来源。

Case列表“判定” SHALL 为current_assessment.conclusion的读取别名，携带其来源、时间和适用范围，与资料/概览同源，不新增重复determination存储。无当前判断返回null；系统收尾保留system身份，技术原因从执行记录读取。分类和截止时间 SHALL 只从独立Case管理字段读取，证据/威胁计数 SHALL 使用版本化证据合同及计数状态，真实数据路径不得继承Incident分类或沿用演示数组长度计算。

#### Scenario: Data contracts are verified while a later model improvement remains pending
- **WHEN** 管理字段、当前判断、独立证据及来源已在隔离数据库保存并可按合同导出，而模型或流程仍待优化
- **THEN** 可以单独交接数据合同并继续前后端开发，模型质量任务仍保留未完成；不能把此交接说成全部页面功能或调查质量已验收

#### Scenario: A historical case has no current assessment or evidence index
- **WHEN** 读出旧Case而两个当前指针均为空
- **THEN** 判定与证据计数返回各自真实缺值及状态，原告警/材料仍可回查；不借最新Run正文、Incident分类或0计数填补

### Requirement: Real workflow exports can drive the existing review pages

按用户最新阶段目标，系统 SHALL 支持将合成输入经真实入湖、Fusion、A/I/C/H及后续C得到的保存记录导出到既有页面，不要求先完成实时服务页面接线。导出 SHALL 保留环境／租户／原Case与Run身份、冻结输入、完整查询和模型工件、结果、人工任务版本及实际当前判断来源，并附导出时间和源文件摘要；合成输入与真实执行 SHALL 分开标记，不把预置回答当模型结果。

页面 SHALL 使用原布局和阅读方式，按独立来源身份追加导出案例，不覆盖既有记录或本地编辑。不存在的字段明确缺失；unknown用量不得补零，pending_update不得充当活跃Run，系统交接不得充当有效模型结论。无法从导出取得实际依据状态时 SHALL 显示未核对，不根据成员相同自行推断current。

#### Scenario: A completed workflow is exported for product review
- **WHEN** 新构造的案例已通过真实管道和模型处理，并导出数据库及相关工件
- **THEN** 用户可在既有告警、事件、Case及每轮页面回查真实保存值和来源，页面字段缺口单列；不会为了凑齐展示补造内容，也不会自动执行模型或业务写回

#### Scenario: A pipeline phase fails before model execution
- **WHEN** 合成入湖或上下游某阶段失败
- **THEN** 保留该批实际回执并核查服务可用性、授权、数据格式与程序行为后归因；不将服务／配置问题直接归为业务代码问题，不将失败批次标作端到端成功

### Requirement: Service-backed case pages use authoritative saved state

现有Case页面 SHALL 通过同一数据适配层明确区分本地演示、真实流程导出和新服务数据，保留已确认布局。本阶段以真实导出回查作为必要验收；下列服务写入、启动和并发合同仅适用于显式服务模式，不要求完成服务表单写入才通过导出验收。服务模式 MUST 从正式API读写真实Case/Run/Result/Task，不用localStorage模拟成功，服务错误不得回退样例；既有本地记录不得自动迁移或删除，导出模式不得把本地操作宣称为已写回服务。接口沿用认证与权限，不将模型凭据下发页面。

#### Scenario: A service write fails
- **WHEN** 用户在服务模式保存H或启动调查而接口返回错误
- **THEN** 页面显示真实错误并保留可编辑输入，不写本地成功结果、不生成假Run，不自动重试启动

### Requirement: Case queue and metrics share defined server-side semantics

系统 SHALL 提供有权限边界的Case集合GET，支持标题/完整ID搜索、状态/严重程度/负责人/指标筛选、固定业务更新时间与ID排序及1至50条稳定分页，返回items、筛选后total、next_cursor和总体metrics。cursor SHALL 绑定筛选及排序；指标 SHALL 对本租户有权读取的全部案件计算，独立于表格筛选和分页，不按任务/Run条数代替Case数。列表与指标应取同一只读快照，GET不得改状态或业务时间。

四指标 SHALL 沿PRD8.1的待分配、处理中、高严重程度和待人工跟进规则，只纳入新建/处理中案件；负责人未知不得当作未分配，待人工任务按Case去重。

Case队列每项 SHALL 返回来自正式同租户 `case_alerts` 成员关系的全部告警数 `member_count`，并提供 `active_member_count`，只计告警当前处理状态为 `new` 或 `in_progress` 的成员。统计 SHALL 在服务端覆盖本案全部成员，不受页面已载入成员、可视行数或本次队列分页限制；`completed`、`unknown` 不计活跃。正常读取到空成员集合为零；旧版本响应缺少活跃统计时产品 SHALL 保持未提供，不补零。本增量仅扩展Case队列项，不改变冻结告警DTO或持久化表。

Case列表的关联威胁 SHALL 使用现有 `page_data.evidence.threat_count` 及 `state`，保留部分覆盖和缺索引/不可用含义；不得由本页告警行、战术标签或风险值临时推导。CSV仍按当前已支持的公开列选择，不能提交未被导出合同接受的页面列名。

#### Scenario: One case has several open human tasks
- **WHEN** 一个处理中Case有多项未开始/进行中的H，另有已解决Case仍留未完成任务
- **THEN** 待人工指标只将前一个Case计一次，后者不计；翻页和搜索不改变总体指标

#### Scenario: A queue filter changes
- **WHEN** 用户点击指标或改变筛选条件
- **THEN** 使用新筛选重新从首页读取，旧cursor不得混用；结果total按新条件计算，保留总体指标口径

#### Scenario: A Case contains members in different handling states
- **WHEN** 同一Case包含新建、处理中、已完成和未知状态的正式成员，队列只返回本案一项
- **THEN** `member_count`覆盖全部正式成员，`active_member_count`仅计新建和处理中成员；页面展示同一项的真实两种数量，旧响应没有活跃字段时显示未提供

### Requirement: Current assessment shows coverage and investigation-basis status separately

案件资料及调查概览 SHALL 读取current_assessment的实际结论、来源、时间及覆盖成员；不得由最新Run标题或零散评分合成当前判断。覆盖与input_freshness SHALL 分开显示：current为“本轮调查依据未变化”，stale为“调查依据已更新，需重新调查”，unverified为“暂无法核对调查依据”，附实际原因和受跟踪范围说明。current MUST 不宣称结论正确或全部外部数据最新；过期不删除旧判断。

#### Scenario: An accepted partial assessment covers only some members
- **WHEN** 有效partial被采用，但当前判断未覆盖全部成员
- **THEN** 显示适用X/Y及未覆盖成员，同时按实际输入比较显示依据状态；不得因采用或current显示整案全部查清

#### Scenario: Human evidence is revised after adoption
- **WHEN** H结果或范围变化使当前判断的受跟踪输入过期
- **THEN** 展示更新原因、原判断及来源，并提供显式准备新一轮入口，不自动改结论、结案或启动

### Requirement: Pending and active baseline work remain distinct in the UI

页面 SHALL 分别展示待启动pending与running/unknown，允许同案活跃轮和下一pending同时可见；按钮 SHALL 使用服务端start_eligibility及真实回执。准备和启动 MUST 由用户明确触发，结束或刷新不得自动接续。服务冲突后应刷新状态并保留用户意图，不自动重派。

#### Scenario: Scope changes while a baseline is running
- **WHEN** 当前轮冻结A/B，用户加入C形成下一pending
- **THEN** 页面分别显示正在调查A/B与待启动A/B/C，旧轮结果保留原范围，当前轮结束后下一轮仍需点击启动

#### Scenario: An unknown run occupies the active slot
- **WHEN** 服务端报告unknown并拒绝新启动
- **THEN** 页面显示执行状态待核实及不能启动的实际原因，不改为已失败、已完成或提供自动重试

### Requirement: Human-task forms preserve explicit scope and immutable history

服务模式H表单 SHALL 对接任务及revision合同：完成须非空结果和明确result_scope，区分负责人、实际完成者/时间与修改者/时间，保留历史版本及来源Result。编辑 SHALL 携带expected_row_version及Case范围前提，冲突不得覆盖远端。元数据修改保留原完成事实，修改结果/范围/引用需重新确认；成员移出后的历史声明不自动缩小或扩大。

result_scope SHALL 显式列非空成员；对象仅在explicit_objects种类必须非空，其他种类允许不选对象；时间窗口 SHALL 允许两端同时null，填写时须成对有效。页面 MUST NOT 将对象或已知时间窗口变为所有H完成操作的统一必填项。

#### Scenario: A user completes a task then requests another investigation
- **WHEN** 用户明确保存有范围的人工结果
- **THEN** 先显示人工结果保存成功而非结论已更新，再允许显式prepare与start；保存H本身不得产生调查调用或pending

#### Scenario: Two users edit the same task revision
- **WHEN** 保存请求的预期任务版本已过期
- **THEN** 显示冲突、保留尚未保存的输入并提供读取当前版本的方式，不静默覆盖或本地记成功

#### Scenario: The confirmed member is known but the time window is not
- **WHEN** 用户填写非空结果、选择selected_alerts及本案成员A，对象为空且时间窗口两端为null，其他身份/版本校验有效
- **THEN** 可以完成保存，明确显示未提供对象或时间窗口，不强迫填造这些值，不扩大到其他成员

### Requirement: Investigation reading preserves real outcomes and deferred actions

历史/结果/材料页 SHALL 使用同Case同Run的已存结果与冻结来源，分别呈现目的、模型结论或系统交接、变化/影响、覆盖/限制及用量；字段缺失明确未提供，未知用量不补零。现有成员关联/移动动作 SHALL 使用正式事务接口和预期范围版本，保留旧轮。Q、响应执行、未接探索保存及通用管理 SHALL 明确不可用，不在服务模式模拟成功。

#### Scenario: Final synthesis is unavailable
- **WHEN** Run结束但仅有系统交接、预算停止或无有效模型结论
- **THEN** 页面展示实际停止原因与已保存材料，不把completed、报告存在或最新时间当成有效案件判断，也不覆盖已有判断的展示身份

#### Scenario: A user reaches a deferred AI entry
- **WHEN** 用户打开AI入口而Q仍为预留501
- **THEN** 显示AI问答暂未开放，不插入虚构模型回答、Run或已保存结果

### Requirement: Saved recommendations retain their body, target and source in read-only views

4173实际记录/Case服务模式和4177 SHALL 通过既有HTTP或同源导出显示建议原文及原始目标，动作类别不得替代正文。审批要求 SHALL 保留需要、无需及未知三态；来源引用与限制可展开。当前Case SHALL 仅从当前采用记录引用的Result读取建议，按来源分别显示；指定Run SHALL 校验主体、Result及source_run_id，不借最新或其他轮次补值。建议出现、采用来源或无需审批 SHALL NOT 表示已审批或已执行。

#### Scenario: Current adoption differs from the latest investigation
- **WHEN** 当前采用来源引用的Result与最新Run结果不同，用户随后打开另一指定Run
- **THEN** 当前来源区保留所引用Result的建议，轮次区只展示所选Run的建议；刷新或迟到响应不混用二者，正文和目标默认可读

#### Scenario: Recommendation reading fails or has no saved content
- **WHEN** Result读取失败、身份不匹配，或成功读取的结果没有建议
- **THEN** 失败显示可重试错误且不冒称空结果；成功空结果明确未保存建议，Incident未决问题不被转换为响应动作，unknown或缺失审批要求不显示无需审批

### Requirement: Adopted result basis preserves original scope and unresolved state

4173/4177 SHALL 按当前采用来源的Result分别展示已保存发现、支持引用、反证、问题与影响范围；所选Run展示自己的Result。发现和问题正文 SHALL 保持原文，观察/推断/待核/撤回及open/answered/unresolved/not_attempted分别呈现，不把已回答问题列为未解决。原Scope的告警、对象、时间窗、限制 SHALL 保持；当前成员覆盖另行计算。尚未读取或读取失败的来源 SHALL 明确其当前状态，不以空数组或其他轮次替代。技术结束原因 SHALL 留在执行信息，不作为业务未决事实。

#### Scenario: An adopted source includes a member later removed from the Case
- **WHEN** 当前判断引用的Result包含已移出成员，用户另选后续Run
- **THEN** 当前判断仍显示采用来源的原范围，当前覆盖单列；所选Run仅显示本轮依据和问题，切换/刷新不混用来源

#### Scenario: Saved questions are answered or not attempted
- **WHEN** 所采用Result同时保存已回答、未尝试或未解决的问题，以及已撤回的发现
- **THEN** 已回答问题和原回答单独可读，未尝试/待核保持真实状态，撤回发现不冒充有效支持；空列表、缺字段和读取失败分别显示

#### Scenario: A Run ends with a technical stop code
- **WHEN** 已保存Run带有stop_reason且其业务Result没有对应未决内容
- **THEN** 结束码仍可在执行详情回查，但不被导入或再次拼接到业务未决项/限制，旧导出原件不改写

### Requirement: Adopted human revisions and artifacts have readable frozen sources

Case详情、page_data与采用历史 SHALL 在原采用来源引用上增补构造现有读取路由所需的`task_id`、`run_id`，按同tenant/Case及被引用的版本/工件解析，其他来源类型返回null。人工来源 SHALL 读取指定TaskRevision的正文、状态、原Scope和引用，不改读任务current版本。工件 SHALL 按其原Run归属或Case级归属读取原正文并保留availability，不能将任意工件伪装为Result或自动采用新判断。4173/4177 SHALL 保持引用身份和正文来源，导出原件不改写，未知/未读取/读取失败与已读取空正文分别显示。

#### Scenario: The adopted human revision precedes the current task revision
- **WHEN** 当前采用引用旧人工版本，而任务current已经指向更新版本
- **THEN** HTTP来源提供旧版本的task_id，页面通过现有冻结版本GET显示旧版本正文、范围和引用；不使用current正文替代

#### Scenario: Adopted artifacts have different ownership and availability
- **WHEN** 采用来源分别指向Run级或Case级工件，某个工件为外部存储或读取失败
- **THEN** HTTP来源提供真实run_id或null，页面选择对应现有路由并验证返回Case/Run/工件身份；保留已成功来源，失败可只读重试，不用其他工件或Result填补

### Requirement: Event and Case results expose a saved business verdict

I 事件诊断和 C6 Case 综合 SHALL 在现有模型响应中独立输出 `business_verdict`，枚举为 `malicious`、`benign`、`false_positive`、`needs_review`。判定 SHALL 随该轮有效诊断或 Case Result 保存并通过现有 HTTP 提供，与结论正文、确定性、严重程度、人工分类及采用状态独立。原告警合同保持。缺失、非法或未能形成业务结果时 SHALL 保留可用原答与交付状态，未记录的业务判定返回 null。

#### Scenario: A completed diagnosis explicitly requires review
- **WHEN** 该轮诊断已保存且模型明确给出 `needs_review`
- **THEN** 当前诊断或指定轮次按原归属返回 `needs_review`，页面可显示待复核，旧记录缺判定时仍为 null

#### Scenario: A Case retains an older adopted result
- **WHEN** 当前采用指向一个旧的有效模型 Result，另有更新轮次或人工分类
- **THEN** 当前判断只读取该采用源的判定，指定 Result 显示自己的判定，人工分类不替代两者；没有唯一有效模型来源的采用记录返回 null

#### Scenario: The verdict unit is absent or invalid
- **WHEN** 新模型答复的判定缺失、非法或重复，仍有可用的结论单元
- **THEN** 保留可用结论与原答，标明部分交付，不由正文或现有属性猜测判定；未发布的候选判定不能成为当前判断

### Requirement: Internal investigation changes preserve the existing business presentation contract

提示词、工具及内部执行工件演进 SHALL 由后端reader/export适配到既有业务DTO，保持Case/Run/Result/Task身份、来源关系、枚举与coverage/freshness/unknown语义；MUST NOT 要求页面解释新内部主张或步骤才能显示当前判断。实际模型判断与执行原因 SHALL 分别读取业务字段和执行记录。Case严重程度/分类/状态只读取其实际管理来源，缺值不得从模型正文推断填充；图谱共现不冒充已证实因果。公开合同如需变更 SHALL 显式规划兼容，不借内部适配静默改变。

#### Scenario: A prompt or tool changes while the saved output contract stays compatible
- **WHEN** 新Run增加工具或使用新的内部结果版本并完成合法保存
- **THEN** 原页面布局仍能读取其当前判断、历史、材料、图谱及H，技术原因在执行详情回查；旧版本仍按原来源读取，不被补造或覆盖

#### Scenario: An H and member-change loop is reviewed through an export
- **WHEN** H及成员关联/移动通过现有服务或驱动保存，真实流程及新旧版本随后导出
- **THEN** 既有页面能回查保存值、成员范围变化、pending/活跃轮与判断依据状态；导出模式不宣称本地页面操作已写回服务，实时表单不是本阶段必要验收条件

### Requirement: Spirit Hub provides four investigation product pages

Spirit Hub new web SHALL 在现有应用外壳内挂载 4173 demo web 的告警、事件、案件和执行四页，分别使用告警、事件、案件和调查分析入口。`web` SHALL 从可编辑源码独立本地运行并支持热更新，复用所选环境的平台服务。其他页面 SHALL 沿用各自的页面记忆和状态逻辑。四页的业务数据 SHALL 完全通过 `socai2` 版本配套的 HTTP 合同读取和写入，沿用告警交接字段和主体、任务、Run、Result 的既有身份与状态含义。

#### Scenario: Spirit Hub forwards an authorized investigation page request
- **WHEN** 用户通过 Spirit Hub 打开告警、事件、案件或调查分析并请求 C173 业务数据
- **THEN** 平台校验自己的会话、路由权限与租户，再经四页共用的可信 HTTP 接线转发。转发不得调用已退役的调查上游 `/api/v1/auth/me`。未登录的页面请求由平台原入口拒绝。

#### Scenario: An analyst paginates the alert list
- **WHEN** 用户打开告警列表、翻页或调整每页条数
- **THEN** 页面默认按告警时间降序、每页 8 条，提供 8、15、25 条及上一页／下一页，按 HTTP 游标和筛选总数展示当前页。调整容量、筛选或排序时从首段读取，上一页使用已读页，当前页全选以当前页告警为范围。

#### Scenario: An analyst reads the alert category and verdict
- **WHEN** 用户查看交付的告警列表，又或者以现有人工反馈操作保存了新的判定
- **THEN** ATT&CK 类别来自 `derived.tactics[].label`，无值显示「未记录」。列表、概况和告警预览各呈现一条当前判定，优先取实际保存的 `facts.disposition`，否则采用当前有效的 `triage.verdict`。无有效结论时显示「尚未判定」，实际返回待复核时呈现「待复核」。人工修改保存后，以保存读回结果更新当前判定和来源。

#### Scenario: An analyst previews an alert from the alert list
- **WHEN** 用户从告警列表打开某条告警的右侧预览
- **THEN** 预览按 4173 贴右布局依次呈现「发生了什么」、告警信息、受影响实体和已读取的事件及 Case 关系。「发生了什么」优先展示来源描述，描述为空时在同一区块展示同一告警已读取的处理活动。底栏按「管理告警」「打开告警页」排列。可用的管理操作打开当前告警的管理表单，详情操作打开同一告警的概况。

#### Scenario: An analyst reviews the explanation and related records of an alert
- **WHEN** 用户打开告警概况
- **THEN** 页面保留研判栏，并以已发布分诊的理由及同轮保存的解释正文展示「发生了什么」。已有的来源引用在表格中展示字段、原件值和来源，同一原件共用入口，可回查被引用版本或同轮工件。ATT&CK、相关告警和 Case 分区展示各自 HTTP 结果，并区分查询空态与读取失败。

#### Scenario: An analyst reads the AI conclusion in the alert list sidebar
- **WHEN** 用户从告警列表打开右侧预览并查看告警信息中的 AI 分诊
- **THEN** 该区域只展示已发布分诊结论，不展开分诊理由或置信度；无分诊时保留明确空态。完整告警详情仍按原合同展示同轮解释及独立的来源检测、AI 分诊置信度，不能用其他分数补造缺失值。

#### Scenario: An analyst distinguishes a missing detection score from a missing rule
- **WHEN** 用户查看告警概况的检测卡且检测分数缺失
- **THEN** 页面按既有 `material.detection.confidence_state` 显示未提供、未计算、未启用、计算失败或历史值未核实，未知状态才显示未记录。检测规则使用独立标签，不能把规则名称或 ID 接在检测置信度标签后；有效零值保持为零。

#### Scenario: An analyst reviews the current owner in alert management
- **WHEN** 用户打开单条告警的管理表单，且当前负责人在人员目录中有对应记录
- **THEN** 「保持不变」括号内按当前负责人 ID 显示与候选人相同的显示名，随着候选搜索及分页保留身份含义。

#### Scenario: An analyst opens the alert's original data
- **WHEN** 用户打开告警原始数据并查看一个材料版本
- **THEN** 默认显示该版本 HTTP 返回的 OCSF 原文或其空态。材料接口返回实际富化内容时，页面提供富化数据入口。

#### Scenario: An analyst reviews an alert query skipped before execution
- **WHEN** 告警 A 查询步骤保存为 `skipped`，并已返回原因及计划参数
- **THEN** 查询列表和现有抽屉展示保存的原因，已知原因用中文解释，未知或缺失原因不猜测。没有实际开始记录时用时显示“未执行”；存在有效起止时间时保留实际耗时。跳过记录不得显示为成功查空或零耗时。
- **AND** 已保存参数标为计划参数，预览可沿明确入口打开完整参数；不修改原步骤、参数、返回条数或冻结输入，也不触发新的查询或模型调用。已执行查询继续区分成功零行、有结果、失败和未知。

#### Scenario: An analyst opens the investigation directory
- **WHEN** 有对应页面访问条件的用户在 Spirit Hub 打开调查分析
- **THEN** 侧栏可进入运行目录，目录展示 `analysis-runs` 提供的列表和统计，能沿响应打开指定轮次的步骤、工件和所属告警、事件或案件

#### Scenario: An analyst reloads a database-backed subject
- **WHEN** 用户筛选列表、打开详情或从关联入口返回指定告警、事件或案件
- **THEN** 页面按同一主体身份呈现实际 HTTP 返回的保存字段、关联和历史，并分别表达空列表、未生成、待复核及读取失败

#### Scenario: An analyst submits a diagnosis or Case investigation
- **WHEN** 诊断、建案首轮或后轮请求返回成功受理回执
- **THEN** 页面使用回执中的案件、任务和后续 Run 或结果链接，按实际保存进度更新；重新打开仍能读取同一对象及指定轮次

### Requirement: Incident detail follows the agreed 4173 product structure

SpiritHub 事件详情 SHALL 按 4173 的事件头部和「事件概览、关联分析、成员告警、涉及对象、处理活动」五页签组织。概览 SHALL 分开呈现 ATT&CK 阶段、事件说明/判定、告警时间线与共同线索、关联 Case；成员、对象和活动 SHALL 沿原型表格与分类布局使用现有 HTTP 来源。未供字段、尚未加载、查空和读取失败 MUST 分开；不得复制原型样例值、伪造库存、攻击因果或执行成功。原有身份、材料及 Run 绑定和告警交接合同 SHALL 保持。

#### Scenario: An analyst opens incident detail from the list
- **WHEN** 用户从事件列表/预览打开某事件或直接访问其五页签
- **THEN** 头部、页签及各区沿同一事件 ID；刷新和页签切换保持身份，成员告警及材料链接指向其原身份，关联 Case 读取不创建新 Case

#### Scenario: A detail section lacks a source value or its request fails
- **WHEN** 对应字段未供、列表仍有后续游标或某区请求失败
- **THEN** 页面保持原型的分区和表头并显示对应状态，不以已加载数量冒充总量、不用活动时间补最近更新时间，也不把失败显示成成功空结果

#### Scenario: Detail presentation is validated before live integration
- **WHEN** 使用受控前端响应核验事件详情结构、页签及来源跳转
- **THEN** 结果只记为页面和请求适配验证，不计实际21数据、管理保存、诊断生成或 Case 联合验收通过

#### Scenario: Product alignment is reviewed against the prototype
- **WHEN** 核验8181事件详情与4173的产品对齐
- **THEN** 逐区比较用户内容、字段含义、顺序、主次、入口和交互；仅出现相同页签或标题、类型检查及组件用例通过不构成产品对齐通过，人工指出的内容差异须保留并逐步复验

### Requirement: Incident member activity and detection sources are aggregated for list and detail

事件列表和详情 SHALL 在事件专属derived中返回`active_member_count`、`unknown_status_member_count`和`detection_sources`，分别基于同租户当前事件的全部实际成员统计，不受成员分页影响。活跃 SHALL 仅计告警`new/in_progress`；`completed`不计，`unknown`单独统计。检测源 SHALL 沿告警既有`connector_type ?? source_namespace`取值，去重并稳定排序。原`member_count`和告警交接合同 MUST 保持。

#### Scenario: An incident contains alerts in different handling states
- **WHEN** 读取具有活跃、已关闭或未知状态成员的事件
- **THEN** 列表和详情使用相同聚合，全部数包含所有成员，活跃不包含已关闭或未知，未知数单列；事件状态和模型执行状态不改变成员处理统计

#### Scenario: Members share detection sources or there are no members
- **WHEN** 当前事件成员的检测源重复，或当前事件没有成员
- **THEN** 重复来源只返回一次，没有成员返回实际计数0和空来源数组；不回落到事件主体来源或原型样例

#### Scenario: A frontend receives a response without the new aggregate fields
- **WHEN** 事件响应缺少新字段或返回null
- **THEN** 列表与摘要明确显示未提供，保留已有成员总数，不能将缺值补成0；已供0和空数组与未提供分开

### Requirement: Incident detail reads the adopted diagnosis and latest attempt from saved data

E29 SHALL 在事件详情专属响应中提供可空的 `published_diagnosis` 和 `latest_attempt`。同一只读快照内，已采用诊断 SHALL 从 `latest_diagnosis_id` 指向的同租户、同事件、已完成保存结果读取，并核对来源 Run 的事件和类型。该投影 SHALL 只提供结果和来源 Run 标识、保存摘要、结论及页面使用的待核问题原文。最近尝试 SHALL 独立沿事件诊断 Run 的 `requested_at DESC, id DESC` 读取第一条保存的 Run 状态、交付状态、停止原因和固定链接标识。

#### Scenario: A more recent diagnosis attempt fails after an earlier result is adopted
- **WHEN** 当前采用指针仍指向已完成保存结果，另有更晚的失败 Run
- **THEN** E29 继续返回采用指针对应的保存正文和来源 Run，同时在 `latest_attempt` 返回最近失败的 Run 和其保存状态。8181 概览刷新分别跟随两个来源。

#### Scenario: No adopted diagnosis can be read for the event
- **WHEN** 当前采用指针为空，或指针对应的结果未完成、不可见或来源 Run 归属无法核对
- **THEN** E29 的 `published_diagnosis` 为 `null`，既有采用指针和独立的 `latest_attempt` 如实返回。

#### Scenario: Incident overview and history are opened in their respective views
- **WHEN** 用户进入事件概览或事件摘要，或按需打开诊断历史和指定轮次
- **THEN** 概览及摘要 SHALL 直接使用 E29 保存字段，E27 列表继续使用事件聚合合同。E23、E25 SHALL 保留历史、固定 Run、新鲜度及旧失败原义，告警合同继续沿原响应。

### Requirement: Incident queue grouping is reachable through the platform proxy

SpiritHub SHALL 显式转发调查 HTTP 已有的 `GET /incidents/grouping-summary`，静态汇总路径在事件 UUID 详情路径前匹配，不将 `grouping-summary` 校验为事件 ID。代理 SHALL 保留既有来源/时间条件和完整汇总响应；统计口径由调查读取层负责，不在前端或平台代理按当前列表页重算。原事件详情 UUID 校验、告警交接合同及业务写入路由 MUST 保持。

#### Scenario: An analyst opens the incident queue compression card
- **WHEN** 事件列表读取无条件或带既有来源/时间条件的归并汇总
- **THEN** 平台代理调用同名调查 HTTP 汇总路径并保留参数与响应，不能报事件资源地址无效，也不触发诊断、模型或业务写入

#### Scenario: Grouping has no denominator or its request fails
- **WHEN** 调查 HTTP 返回实际零计数及空压缩率，或汇总读取失败
- **THEN** 真实零和空压缩率沿原合同展示，失败保持读取失败，不补造0或根据已载入事件行数猜测压缩率

### Requirement: Incident list assets and preview use the agreed product structure

SpiritHub事件列表 SHALL 将预览图标放在事件标题右侧，资产和资产标签沿同事件原生资产查询读取，不固定显示未提供。事件摘要 SHALL 按4173真实导入事件的标题/状态、事件概述、事实、解决说明、资产、关联告警和底部动作组织；保留已有事件聚合并明确空态。列表与摘要资产区 MUST 只展示真实资产，不通过额外对象匹配/未匹配合并补入原始主机或IP。原始对象留在涉及对象与关系图功能中；未完整加载的集合不得用当前页或匹配边数冒充资产总数。

#### Scenario: An analyst opens the incident preview from its title row
- **WHEN** 用户点击事件标题右侧预览图标或事件行
- **THEN** 摘要保持该事件身份，概述/判定/优先级使用实际保存字段，未知字段不复制样例；底部先打开事件关联分析页，再提供已有管理入口

#### Scenario: Asset matches or members span more than the preview
- **WHEN** 同一资产有多条对象匹配边，或对象/成员尚有后续页
- **THEN** 库存资产按asset_id去重，资产区预览前五项、成员前四项并可查看全部；只有完整集合的去重数量能称总量，部分集合标明已载入。资产区不得额外读取对象来补齐展示

#### Scenario: An asset read is empty, missing or failed
- **WHEN** 对象/资产读取成功为空、仍在加载、缺供字段或返回失败
- **THEN** 页面分别表达实际状态；失败/未供不得显示0或无资产，原始对象未匹配库存不等于没有涉及对象

#### Scenario: The overview displays the number of involved assets
- **WHEN** 概览沿已有同事件资产查询读取涉及资产
- **THEN** 只有成功且完整的集合 SHALL 展示按asset_id去重的数量，完整空集合显示0；分页未完、缺供或失败保持真实状态，不自动遍历分页，不把对象数或匹配边数当资产总数，保留原资产页入口

### Requirement: Detection-source labels reach incident stage coverage

已提供的检测来源标签 SHALL 经正常入站与材料保存进入既有事件成员聚合，保留源标签与AI映射的不同来源角色。标签传递不得依赖测试样例或新增页面补值。

#### Scenario: A detection source explicitly provides OCSF native tactics
- **WHEN** 正常入站的OCSF Detection Finding在 `finding_info.attacks[].tactic.uid` 或对应技术字段明确提供标签
- **THEN** 通用投影 SHALL 从同一冻结原件传递已提供的标签到既有RawAlert及材料检测标签字段，事件沿既有当前成员聚合展示；既有根标签兼容和类型问题语义保持，不由厂商自由文本或AI推断补造标签，不更改原件或回填历史材料

### Requirement: Incident relationship graph preserves the original product design

事件关联分析 SHALL 沿4173的三栏关系工作区展示圆形类型图标节点、曲线关联、图例、自动/网格布局、类型多选、同类型显示分组、缩放及时间回放。告警、对象和边的选择 SHALL 联动右侧业务上下文，保留已读取事件成员及当前材料的准确来源。共享告警/Case图及公共字段合同 MUST 保持。

#### Scenario: An analyst focuses an alert, object or relationship
- **WHEN** 用户在左栏、画布或关系列表选择一项
- **THEN** 画布和右栏联动到该项及其真实关联，告警按发生时间排序，未知时间置后；筛选或回放移除该项时不能残留其他视图的详情

#### Scenario: The inspector explains a selected address without repeating alerts
- **WHEN** 右侧显示选中的IP或其它材料对象/分组
- **THEN** SHALL 用明确的已选类型与原值说明当前选择，不显示空的对象资料或重复的相关告警列表；保留分组成员、左栏既有高亮及告警/连线来源入口。材料引用关系不得被改写为攻击角色或因果关系

#### Scenario: The analyst groups or filters objects
- **WHEN** 用户切换对象类型或相似节点分组
- **THEN** 分组只折叠同类型节点的显示，保留namespace/type/key精确对象身份、各成员及材料来源边；不得将此显示分组称作已计算相似度或攻击路径

#### Scenario: Only part of an incident graph has loaded
- **WHEN** 成员或对象仍有未载入页、读取失败或缺少发生时间
- **THEN** 页面分别说明已载入范围、读取状态及未知时间，不能以当前画布节点数冒充全量成员或资产总数；失败不显示为真实空图

### Requirement: Case relationship reading preserves authoritative bases and the agreed three-column design

The Case relationship page SHALL read the saved exploration through E69 and, only when no snapshot exists, read E67. A saved snapshot SHALL retain its frozen base, actual expanded relationships and sources. A requested completed baseline SHALL keep its original Run, Result and graph identities. Missing or failed reads SHALL NOT be treated as an empty graph or replaced with another investigation. Member graphs SHALL use only the returned alerts and material-version objects and SHALL NOT infer relationships from sample values or narrative text.

The page SHALL follow the 4173 three-column layout with an alert list, circular-node graph and selected-item inspector. Selection, grouping, layout, zoom and reset SHALL preserve real node/source identities and fit the default visible graph in its container. Source contents SHALL load on demand. The inspector SHALL omit empty object details and duplicate complete alert lists. Read-only migration SHALL keep deferred exploration actions visibly unavailable without calling legacy unsupported endpoints.

#### Scenario: A Case has no completed baseline or saved exploration
- **WHEN** E69 returns no snapshot and E67 returns the member base
- **THEN** the page shows the actual member alerts and material objects with only their proven associations in the three-column view
- **AND** it does not call the legacy objects route or display a read failure as zero relationships

#### Scenario: A saved exploration is reopened after another investigation
- **WHEN** E69 returns a saved snapshot
- **THEN** the page uses its original base, saved expansion sources and supported view state without replacing its Run with the latest investigation

#### Scenario: A selected completed baseline has no readable graph
- **WHEN** E67 returns the selected identity with graph_state unavailable
- **THEN** the page retains that identity and communicates the missing graph without substituting member or other-round content

#### Scenario: A node or relationship source is opened
- **WHEN** an analyst selects a node or relationship and opens its source
- **THEN** the page uses its original alert/material or Run/artifact identity and preserves the chosen graph when returning

### Requirement: Incident diagnosis failures remain understandable and traceable

事件诊断失败 SHALL 用中文说明已知原因，并保留同Run的执行状态、交付状态及原始回执入口；显示修正不得触发重试或改写采用状态。

#### Scenario: The latest incident diagnosis failed its context admission check
- **WHEN** 最近一次诊断尝试返回`model_context_capacity_exceeded`
- **THEN** 页面显示“诊断容量检查未通过”，保留实际失败/交付状态和查看本次诊断入口；不显示已生成诊断、不自动重试，旧Run原因保持可追溯

### Requirement: Case information follows the prototype with authoritative current-scope data

The Case information page SHALL present four linked metrics, a foldable case summary and member preview in the main column, and Case details, ATT&CK coverage and involved objects in the secondary column. It SHALL follow the 4173 page hierarchy and narrow-container layout. The management entry SHALL be named 管理 Case; the deadline SHALL remain a real Case field. The page SHALL NOT retain the previous five-cell scope block or duplicate standalone classification/deadline action as the target design.

Current member statistics SHALL be computed from the same Case and latest material identities. Object counts SHALL deduplicate namespace/type/key. Investigation counts SHALL use the same saved relationship scope as the Case investigation directory without reading each card or revalidating each investigation merely to count. Source tactic coverage SHALL count distinct member alerts per actual detection label. The page SHALL display that coverage as a bar chart, without inferring tactics from categories, AI text or sample values. Missing data and read errors SHALL NOT become zero.

Adopted judgment, formal business verdict, system explanation, saved sources, coverage and input freshness SHALL keep their separate existing meanings. The latest Result SHALL NOT replace the adopted pointer. Source drawers SHALL retain the saved parent Run/task and exact Result/revision/material identity. Independent evidence counts SHALL exclude raw alert materials and source snapshots.

#### Scenario: An analyst reads the Case information overview
- **WHEN** the ordinary authenticated page loads an existing Case
- **THEN** its four metrics and object/tactic previews use authoritative current-scope reads and links retain that Case
- **AND** a partial or unavailable source remains distinguishable from a confirmed empty result

#### Scenario: Current members supply source detection tactics
- **WHEN** current material detection labels are available
- **THEN** each displayed bar represents the actual distinct-alert count for its label, with the counting meaning visible
- **AND** a Case with no recorded labels displays the correct empty state without fabricated stages or nonzero values

#### Scenario: The adopted record contains a system explanation or an original saved source
- **WHEN** the summary renders that record or the analyst opens a source
- **THEN** the system explanation is not labelled a formal judgment and the source uses its original parent and saved version
- **AND** opening, folding or cancelling a drawer does not write business data or start an investigation

#### Scenario: An analyst reads saved reasoning without opening each source drawer
- **WHEN** the Case information summary is expanded and its adopted sources can be read
- **THEN** exact Result sources show their original title and Run link, saved findings, unresolved findings and questions inline, with original states and expandable scope, references, counterevidence and limitations
- **AND** saved empty lists, missing fields, source identity mismatches and read failures remain distinct, while answered questions and impact boundaries remain readable
- **AND** human revision and artifact sources preserve their saved parent identities, source notes and availability; current revisions and latest Results never replace the adopted sources

#### Scenario: A system closing note follows a failed source investigation
- **WHEN** the adopted record is a system-only explanation and its exact saved source Run reports failure
- **THEN** the page states that this source investigation failed without forming a formal conclusion and links the original investigation; detailed stop reasons, error codes and execution receipts are read in the 4177 investigation workbench
- **AND** record scope and freshness remain visible without being presented as effective analytical coverage, and reading never retries the investigation

#### Scenario: Case grading has persisted provenance
- **WHEN** the Case has saved severity or structured risk metadata
- **THEN** the information page shows the current level and its saved provenance separately from an unapplied model opinion, preserves any exact opinion source, and marks missing reason or investigation category fields explicitly
- **AND** management classification, related incident values and prototype fixture values are not substituted for an absent investigation category or grading rationale
