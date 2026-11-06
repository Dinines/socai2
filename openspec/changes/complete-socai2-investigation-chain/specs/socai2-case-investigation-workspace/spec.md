## ADDED Requirements

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

#### Scenario: One case has several open human tasks
- **WHEN** 一个处理中Case有多项未开始/进行中的H，另有已解决Case仍留未完成任务
- **THEN** 待人工指标只将前一个Case计一次，后者不计；翻页和搜索不改变总体指标

#### Scenario: A queue filter changes
- **WHEN** 用户点击指标或改变筛选条件
- **THEN** 使用新筛选重新从首页读取，旧cursor不得混用；结果total按新条件计算，保留总体指标口径

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

### Requirement: Internal investigation changes preserve the existing business presentation contract

提示词、工具及内部执行工件演进 SHALL 由后端reader/export适配到既有业务DTO，保持Case/Run/Result/Task身份、来源关系、枚举与coverage/freshness/unknown语义；MUST NOT 要求页面解释新内部主张或步骤才能显示当前判断。实际模型判断与执行原因 SHALL 分别读取业务字段和执行记录。Case严重程度/分类/状态只读取其实际管理来源，缺值不得从模型正文推断填充；图谱共现不冒充已证实因果。公开合同如需变更 SHALL 显式规划兼容，不借内部适配静默改变。

#### Scenario: A prompt or tool changes while the saved output contract stays compatible
- **WHEN** 新Run增加工具或使用新的内部结果版本并完成合法保存
- **THEN** 原页面布局仍能读取其当前判断、历史、材料、图谱及H，技术原因在执行详情回查；旧版本仍按原来源读取，不被补造或覆盖

#### Scenario: An H and member-change loop is reviewed through an export
- **WHEN** H及成员关联/移动通过现有服务或驱动保存，真实流程及新旧版本随后导出
- **THEN** 既有页面能回查保存值、成员范围变化、pending/活跃轮与判断依据状态；导出模式不宣称本地页面操作已写回服务，实时表单不是本阶段必要验收条件
