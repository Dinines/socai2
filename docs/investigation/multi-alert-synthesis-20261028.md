# Case多告警综合分析：成员、关联、时间线与未决问题

2026-10-28，[后续计划](next-phase-plan-20261028.md)第4批。沿用已有Case调查入口、模型/Tool循环、Run和报告存储；本批没有新增端点、表、迁移或调查执行器。当前交付为代码及替身直接验证，未部署或验证真实模型判断质量。

## 输入与执行

继续使用`POST /api/v2/investigation/cases/{case_id}/investigate`，提交选定成员、时间窗口、问题和operation_key。调查上下文中每条A类告警新增规范化`entities`（host/user/ip及原有实体），T类分诊新增其`alert_id`，使模型可分清各材料对应成员。

模型继续按需调用现有进程、网络或产品主机Tool；最终JSON在原summary/findings/counterevidence/gaps/recommendations上增加`member_assessments`、`relationships`、`open_questions`。程序验证成员和证据引用，再补齐覆盖状态、生成来源时间线并保存报告。单次模型最大输出从1200增加为3000 tokens，以容纳逐成员输出；4次模型、4次Tool、24000总Token和120秒循环限制保持，调用前额度预检同步采用新输出上限。

## 返回合同

新内容位于既有`result.report`，结果GET和Markdown下载读取同一份已存结果。旧Run读回不补写新字段；新的追加Run照常保留原报告为H1历史判断。`case_analysis.v1`保持，属于报告的加法字段扩展。

| 字段 | 来源 | 内容 |
| --- | --- | --- |
| member_assessments | 模型判断，程序补缺 | 每条选定告警恰有一项：alert_id、status、role、summary、evidence_ids |
| member_coverage | 程序统计 | selected_count、read_count、addressed_count、unresolved_count、not_assessed_count、source_unavailable_count |
| relationships | 模型 | alert_ids、kind、assessment、basis、evidence_ids |
| timeline | 程序从来源记录生成 | timestamp、source_time、time_kind、in_window、description、candidate_member_ids、evidence_id、row_index、source_record_id |
| open_questions | 模型，程序补齐遗漏 | question、alert_ids、evidence_ids、missing_evidence、suggested_action |

### 成员覆盖

模型输出的status为`addressed`或`unresolved`；程序为遗漏成员补`not_assessed`，为未读取到材料的成员补`source_unavailable`。role为`supporting`（支持本次发现）、`background`（当前作为背景）或`undetermined`。

`addressed`只说明模型给出了有引用的成员判断，不表示攻击已证实、事实已全部核实或告警已解决。`background`不表示安全或已经证明无关。读取数量与成员判断数量分开统计。每项模型判断必须引用该成员自身A类材料，此外可以引用T/E/H。

### 关联依据

每项至少两条不同的选定告警，必须引用每条参与告警自身的A编号；kind为`shared_context`（共同实体/时间）、`behavioral_link`（行为联系）或`contradiction`（证据矛盾）。assessment为`supported`、`hypothesis`或`not_supported`，basis解释依据和限制。

共同主机、账号、IP或时间接近不能直接推成因果。未列关系不代表所有成员已经证明互不相关；`not_supported`表示这项关联未得到支持，不是证明没有任何关联。上述解释规则进入模型提示；引用校验只证明编号和范围正确，不自动证明因果判断正确。

### 来源时间线

- A类材料使用告警`event_time`，标为`alert`；成功事件湖Tool逐条使用返回记录的`event_time`，标为`event`。
- 产品当前快照使用本次读取开始时间`observed_at`，标为`snapshot`，不把`last_seen`或读取时间当成历史攻击时间。snapshot的`in_window=null`，表示历史窗口判断不适用。
- 有时区的时间统一到UTC排序。历史时间不在`[start,end)`内时`in_window=false`；缺少时间或时区时保留原source_time，timestamp/in_window为null，放在已知时间之后，并保留缺口和未决问题。
- Tool记录保留`evidence_id`与从0开始的`row_index`，可定位原结果`rows[index]`；event_id或device_id作为source_record_id。A类记录row_index为null，通过A证据定位告警。
- candidate_member_ids表示来源告警或查询主机对应的候选成员。两个告警共用一个主机时可以同时出现在候选列表，但这不是模型已分析两者或因果关联的证明。
- 失败Tool、分诊生成时间和H1历史结论不伪装成来源行为。事件湖工具沿用自身返回数量及截断限制，时间线不代表产品全量行为，重复来源不自动合并为多重证实。

### 未决问题与完整度

open_questions的alert_ids为空表示本次全案，非空必须是所选成员；evidence_ids可以为空，表示没有可引用依据。每项说明问题、缺少什么和建议下一步。建议只是文字，不执行处置，也不自动追加调查。

如果模型遗漏未决项，程序为未完成成员、hypothesis关联和时间未知记录补保守问题，或复用覆盖相同成员/全案的已有问题；不编造已取得的新证据。未决问题进入gaps，报告completion保持partial。模型完全没有返回新数组时仍可保存原结论，但全部未提供逐项判断的成员标not_assessed，不凭原findings自动推成逐成员完成。

范围外成员、重复成员判断、未知证据或缺少参与成员自身A引用均不被接受。2026-10-28真实PG联调后，首次不合法结论在剩余预算内允许一次校验反馈：步骤保存`case_analysis_validation`、合法证据编号和成员UUID，下一轮模型按字段诊断纠正或先调用Tool。原回复保存在账本，但从下一轮输入移除，避免重复臆造内容；不放宽校验或增加4次模型/24000 tokens/120秒限制。再次不合法或没有剩余调用轮次时停止为`invalid_or_unreferenced_conclusion`，保存partial报告。模型HTTP读取超时60秒、连接超时10秒，仍受整次120秒限制，不自动重发超时请求。

追加问题的模型输入省略前次报告派生的timeline/member_coverage，并提供omitted_report_fields；H1证据和原报告完整保存。纠错只发送具体字段错误，不重复完整schema。真实PG主调查通过，但最终追加模型仍返回不合格字段，见[联调结果与剩余问题](real-pg-test-20261028.md)。

## 三告警直接例子

以下为测试替身提供的数据和模型回复，不是真实厂商或真实模型判断：A1与A2涉及host-01/alice，时间相邻；A3涉及printer-03/bob。工具返回host-01的一条PowerShell进程记录E1。

| 成员 | 模型判断 | 返回状态 |
| --- | --- | --- |
| A1 | 已读取进程记录，引用A1/E1 | addressed / supporting |
| A2 | 外联与进程之间仍缺直接联系，引用A2 | unresolved / supporting |
| A3 | 另一主机和账号，当前作为背景，引用A3 | addressed / background |

报告仅把A1/A2列入shared_context关系，basis明确“共主机和时间接近，不能推断因果”；未决问题是“外联是否由可疑进程发起”，注明还缺进程与连接的直接关联记录。成员统计为选定3、读取3、给出判断2、未明确1，completion=partial。

时间线依次为A1、E1进程记录、A2、A3（A1与E1在例子中时间相同）；E1保留`event-7001`、`row_index=0`，候选成员为A1/A2。报告GET和Markdown都保留同一套结果。若模型漏掉A3，A3变为not_assessed；若另选A4但读不到材料，则A4为source_unavailable。

## 实现与验证

- [综合分析合同、引用校验、时间线及渲染](../../services/api/app/investigation_v2/case_synthesis.py)
- [现有Case循环接入](../../services/api/app/investigation_v2/case_analysis.py)
- [模型HTTP输出额度](../../services/api/app/investigation_v2/case_analysis_models.py)
- [多告警直接用例](../../services/api/tests/test_case_synthesis.py)

4个新增用例覆盖三成员完整输出/保存/读回、遗漏与不可读成员及待核关联、范围外成员/未知引用、缺少时间与窗口外记录。受影响的7个Case流程用例、2个产品Tool用例通过；产品用例额外核对快照时间线类型和历史窗口不适用。未重复Actions厂商HTTP映射、告警/事件模块或恢复/可用性专项。

上述使用真实ASGI路由、模型HTTP协议、结果生成和保存代码，数据库、模型与查询来源为替身；不代表真实模型关联质量已验。OpenSpec CLI在当前Shell不可用，未执行其严格校验或归档。不新增迁移、部署或远端推送。
