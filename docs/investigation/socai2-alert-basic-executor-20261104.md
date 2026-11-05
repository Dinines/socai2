# A告警基本查询、分诊与解释执行

2026-11-04。`codex/case-baseline-history-20261103`，主目录直接开发。已接服务器内部入口`StageResultService.execute_alert(tenant_id, alert_id, operation_key)`，完成冻结→三类基本查询→一次模型分诊→同次解释/结果发布。**没有自动关闭、处置、启动Case、定时领取或自动重试；旧消费者和生产未切换。** I事件诊断执行器仍待下一批。

## 完整流程

1. 校验可信调用方传入的租户/告警身份，锁定告警，按operation_key创建或读回同一个`alert_basic` Run。首次保存完整输入快照并提交running；重发只读既有状态，不重新生成截止时间或执行查询/模型。
2. 从冻结对象生成确定查询参数。资产查同租户的明确主机名/IP；历史查同类型、命名空间和值的其他告警；TI查同租户当前有效、非误报的明确类型IOC。历史限定告警已知发生时间之前24小时至发生时刻，排除自己；发生时间未知时跳过历史，不能用当前时间替代。
3. 每个查询先提交运行步骤和实际参数，再执行已有SQL；保存原有界返回、行数、截断、来源限制与状态。每项最多取201行以识别超过200行；保存最多200行及128KiB完整行，超限只整行省略，记录原因。
4. 准备分诊输入：告警标签、材料原值、人工反馈和背景查询以来源别名关联。原始值及字段路径先过现有guard，单项2048字节、视图8192字节、完整消息12288字节；超限/不适合引用的路径明确记省略数，不拼接残片。原始材料始终留在冻结快照。
5. 解析同租户模型配置。实际模型请求和运行步骤先提交，再执行一次调用。服务端固定1次模型/3次查询/24000 tokens/120秒/每查200行；输出上限3000 tokens，没有新增纠错调用或增加预算。
6. 保存原回复及真实用量，拒绝不完整回复、工具协议、非法结构、重复JSON键、无效/重复来源别名及未知/不一致用量。模型只返回S编号，程序转换为本次实际可见字段的引用；背景标签或旧分析不能单独支撑明确恶意/正常/误报判定。
7. 将同次分诊、解释、建议/限制、发布回执、执行阶段及Run终态同事务保存。输入仍适用且没有较新已采用结果时更新分诊/解释指针；否则只保留历史。人工处理状态和判定保持原值。

模型未配置/视图不可用/输出不合法时保存失败尝试，保留既有成功指针。调用、取消或提交不确定时保存unknown，原operation_key重发仍不执行。没有模型产物时不会制造一个默认分数或成功分诊。

## 字段与实际落点

不新增表、列或公共枚举；原29表458列及迁移123保持。

| 字段/语义 | 保存位置 | 来源及处理 |
| --- | --- | --- |
| 告警身份/租户 | runs.alert_id / tenant_id | 可信服务端输入，经同租户告警行核对 |
| 执行类型/触发 | runs.kind / trigger | alert_basic / refresh，与Case基础调查分开 |
| 请求幂等键 | runs.operation_key / request_hash | 同租户确定性Run ID；重发不再执行 |
| 执行实现版本 | runs.executor_version | socai2.alert-basic-executor.v1 |
| 冻结输入 | runs.input_artifact_id → artifacts.input_snapshot | 材料、对象、告警事实及人工反馈，原hash/字节数核对 |
| 限制/截止时间 | runs.limits | 服务端首次事务固定，重发不刷新 |
| 执行状态/时钟/原因 | runs.state / started_at / ended_at / stop_reason | 成功、失败、unknown分开 |
| 步骤顺序与父子 | run_steps.seq / parent_step_id / kind / stage_code | A父阶段，三个tool和一个model；失败前可少于一个model |
| 查询实现 | run_steps.name / provider / implementation_version | assets/history/threat_intel，PostgreSQL及已有查询合同 |
| 实际查询参数 | run_steps.actual_args + tool_request.content_json | 冻结对象、明确租户、历史窗口、上限，不接模型SQL |
| 查询返回与观察时刻 | tool_response.rows / captured_at | 实际SQL结果；资产是当前库存，不冒充事件时刻状态 |
| 空/失败/未执行 | tool_response.state / reason / returned_rows | 成功0行、失败null、跳过null明确区分 |
| 截断/有界取数 | observed_rows_in_bounded_fetch / truncated / truncation_reasons | 不宣称全库总行数；行数及字节上限分列 |
| 查询关联 | tool_response.query_id / actual_args | 本地step身份及请求范围，非外部厂商事件ID |
| 原始模型请求 | model_request.body | model/messages/max_tokens/response_format，和实际派发一致，无凭据 |
| 来源别名与可见值 | model_request.source_map | 原材料或同Run查询工件ID、具体路径、角色、可见值hash |
| 输入省略 | model_request.input_omissions + messages中的omissions | guard、单项超限、视图超限、无法精确引用路径分开 |
| 模型原回复 | model_response.raw | 原JSON返回，不用解析后的成功文本代替原件 |
| 响应有效性 | model_response.validation_error | 已拒绝回复仍保留，不创建正式分诊 |
| 调用请求ID | run_steps.usage.request_id | 来自真实返回；未知为空 |
| token/费用 | run_steps.usage | 同次输入/输出/总token；未知不补0，费用未计价不写0 |
| 判定/理由/置信度 | alert_assessments.verdict / rationale / confidence / score_state | 一次模型产物配对；0–1是该判定置信度，不是风险分；null对应not_computed |
| 分诊依据版本 | alert_assessments.input_material_id / source_run_id / producer | 绑定原冻结材料、Run及执行器版本 |
| 同次解释 | artifacts.alert_explanation | body / generation_method=model / source_refs / generated_at |
| 建议与待核实事项 | assessment.recommendations；explanation.recommendations / limitations | 建议仅保存，审批unknown；未核实问题留限制，不自动执行 |
| 当前分诊/解释指针 | alerts.latest_triage_id / latest_explanation_id | 输入过期/较新结果存在时不覆盖 |
| 事件新鲜度 | incidents.business_updated_at / row_version | 成员分诊成功采用后刷新，沿现有告警→事件锁顺序 |
| 发布结论 | artifacts.source_snapshot的output / outcome | 记录采用与否及current/input_changed/newer_result_exists |

查询引用发布时只允许同租户、同告警、同Run且已完成步骤所绑定的返回工件，核hash和字节数。查询背景是source_label；历史分诊是prior_analysis，人工反馈是human_statement；回执不变成observation。原材料引用支持精确数组索引；含点等不能精确表示的原键保留原件并显式省略。

## 具体例子

**正常分析：** 收到进程告警，材料明确`pid=42`和`argv=["app.exe","synthetic"]`，并有主机/域名对象。实际测试SQL各返回一条资产、24小时内同对象历史告警和内部TI；同名其他租户及30小时前记录均未进入结果。替身模型给出`needs_review/confidence=0.3`与“授权待确认”，分诊和解释指向同Run/原材料。原人工`completed/benign`没有被改写，C1仍可把此分诊作为已有分析判断读取。

**查空与缺源：** 没有发生时间时历史步骤为skipped/history_window_not_defined；资产读取权限不可用为failed/source_unavailable；TI成功零行则completed/0。三者分别保存，模型输入明确其差异，不把零行当成安全证明。

**执行中材料更新：** 模型执行期间收到材料第2版，原Run仍使用第1版；完成后保留第1版分诊及解释，发布原因input_changed，当前指针不被覆盖。

**失败与重发：** 模型请求提交失败时调用次数为0；已得到回复但正式发布提交失败时，回复保留，分诊/解释/指针整批回滚。两者都保留unknown；相同operation_key只读回，不重派。

## 验证与未完成范围

- 9个新检查与5个受影响A/I/Case输入回归最新通过。首次9项被测试夹具的跨租户写入方式触发RLS拒绝；改用对应租户事务后8过、1项多Run测试被45秒测试驱动总时限中断。调整测试驱动时限并补字段路径guard后，只定向复核3项，全部通过。业务120秒上限和预算未改；首轮失败原件保留。
- PostgreSQL和三类查询SQL在21已有独立合成验证库实际执行；模型为替身，缺源用例中资产错误为替身，其余有明确记录。4批受限角色/隧道已清理。没有真实模型/湖/厂商/生产调用、新容器、DDL、部署或提交推送。
- 初次静态检查的两处括号错误及一处未用测试导入已修正；之后6文件Ruff通过。模型输出[专用schema](../design/socai2-alert-basic-answer-v1.schema.json)从运行时导出，原公共合同不变。
- [本批回执](../operations/socai2-alert-basic-20261104.json)绑定源码及四份原始结果。原r13暂停/5.3未完成，本批不证明真实模型语义质量。
- 已有四条A/I只读接口可读新分诊及解释；步骤/用量/原调用的完整页面DTO仍属OpenSpec 3.3。实际消费Fusion产物的生产接线、旧消费者适配仍待后续切换，不能只开Fusion新writer就声称全链上线。I执行、事件Case关系、H与外部来源仍待；Q继续只预留接口。
