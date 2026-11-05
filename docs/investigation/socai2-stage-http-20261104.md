# 独立服务的告警基本分析、事件诊断与后续调查入口

2026-11-04。本说明对应 `app.socai2_main:app` 独立应用的当前接口合同。A/I执行器复用已验证实现，新增两条用户显式调用入口；它们不替代旧版服务、不启动旧版消费者，也不会自动建立或执行Case。独立应用另包含Case、人工任务H和预留问答Q接口。

完整合同见[独立服务OpenAPI v2](../design/socai2-independent-api-v2.openapi.json)，导出脚本为[export_socai2_independent_api_20261104.py](../operations/export_socai2_independent_api_20261104.py)。导出只构建运行时OpenAPI，不启动应用生命周期或连接数据库。该合同说明当前代码；部署、真实模型及湖的验收以独立服务对应批次回执为准，不能用OpenAPI导出当作验收结果。

## 两条执行入口

| 阶段 | 方法与路径 | 明确负责的工作 |
| --- | --- | --- |
| A 告警基本分析 | POST `/api/v1/socai2/alerts/{alert_id}/analyze` | 冻结单告警材料与已有人类反馈，查询资产、同对象历史告警、内部TI，形成同次分诊及Explain |
| I 事件诊断 | POST `/api/v1/socai2/incidents/{incident_id}/diagnose` | 冻结完整成员、归并依据及有效的成员A结果，形成事件整体诊断与未决问题；不重复A查询 |

共同请求只有 `{"operation_key":"UUID"}`，额外字段拒绝。告警/事件ID来自路径；租户及操作者来自认证身份，不接收客户端指定的tenant、actor、模型、自由SQL、预算或期限。沿用Bearer JWT/API key认证与 `alerts:write` 权限，需具体同租户用户；workload身份拒绝。`SOCAI2_STAGE_EXECUTION_ENABLED` 默认false，关闭返回503。

两接口同步等待执行尝试完成，再读取同一个Run的 `StageEntry`。输入和调用请求先提交后执行外部调用；操作键确定本租户内同一Run身份。原键原内容重发读取原执行，不再派发，原键用于另一个对象/阶段/操作者返回409。已有执行尚未完成时可读到running，不代表重复启动。A固定1次模型、最多3次SQL查询；I固定1次模型、0次外部查询；两者仍各受24000 tokens/120秒等原服务端预算限制。

执行入口不做自动重试。业务/模型失败可以以HTTP 200返回 `run.state=failed/unknown` 等真实状态；HTTP成功只说明取回记录，不说明分析成功。未预期执行或读取错误返回503和确定的run_id，调用方先按run_id读取，不换操作键盲目重派。未认证401、权限不足403、对象不存在404、操作键冲突409、请求格式错误422均保留对应语义。

## 23项字段与来源

| 项 | 字段 | 来源与含义 |
| --- | --- | --- |
| S01 | 路径 `alert_id/incident_id` | 明确本轮对象，仅限认证租户；不是Case范围 |
| S02 | 请求 `operation_key` | UUID幂等键；确定本次执行Run身份，不是业务结论ID |
| S03 | `run.id/kind` | `socai2.runs` 的真实执行ID与alert_basic/incident_diagnosis |
| S04 | `run.requested_by` | 服务端从认证用户保存的用户ID；旧内部调用未提供时为null |
| S05 | `run.requested_at/started_at/ended_at` | 本轮实际保存时钟，未知结束时间null |
| S06 | `run.state` | 执行状态，与诊断/分诊内容及当前采用分开 |
| S07 | `run.executor_version` | 实际A或I执行器版本 |
| S08 | `run.input_artifact_id` | 同Run不可变输入工件ID；HTTP返回身份，不把冻结原文展开 |
| S09 | `run.stop_reason/delivery_state` | 本次停止原因与交付状态；有结果不等于完整Case调查 |
| S10 | `freshness` | 当前输入与本Run冻结输入比较：current/stale/unverified/unavailable |
| S11 | `is_current_pointer` | 结果是否被当前latest指针采用；可采用但已过期 |
| S12 | `valid_for_current_input` | 当前指针、current、Run completed；I另须accepted，不能只看指针 |
| S13 | A `result.id/input_material_id/source_run_id` | `alert_assessments` 同次分诊、输入材料和Run的明确配对 |
| S14 | A `result.verdict/rationale` | 同次模型分诊与理由；不改告警人工判定/处理状态 |
| S15 | A `result.confidence/score_state` | 同次分析置信度及计算状态；不是Fusion检测置信度，不把高分直接当高风险 |
| S16 | A `result.recommendations` | 保存的建议；不自动创建任务、审批或处置 |
| S17 | A `result.producer/actor/assessed_at` | 分诊实际产生方、作者元数据和时间；认证请求者另在run.requested_by |
| S18 | `explanation.artifact_id/available/reason/content` | 同Run Explain；按留存状态、大小和hash核对后可读，否则明确原因 |
| S19 | I `result.id/source_run_id/revision/state` | `incident_diagnoses` 的真实诊断尝试与不可混用的版本 |
| S20 | I `result.summary/diagnosis/open_questions` | 整体诊断、结构化分析和未决问题；保完整成员覆盖及来源角色 |
| S21 | I `result.input_artifact_id/source_fingerprint` | 同次冻结输入身份/指纹；不等同当前仍有效 |
| S22 | I `result.producer/requested_at/generated_at/error_code` | 本次实际生成来源/时钟/结构化失败码，未知字段保null |
| S23 | `result/explanation` 的null | 尚无有效产物或本类型不适用，不能前端补造默认结论 |

`StageEntry` 不输出内部request_hash、operation_key、连接凭据或blob地址。完整Run步骤、请求/返回及用量在已有告警/事件页面分析数据接口中按合同读取；本执行响应不另复制这些大对象。未提供或无法确认的用量/费用仍是null，不用0伪装已知。

## 结果读取与流程衔接

读取仍使用[四条A/I只读接口](socai2-stage-reader-20261104.md)：对象 `/analysis` 和指定 `/analysis/runs/{run_id}`。需要 `alerts:read` 与独立 `SOCAI2_ANALYSIS_READ_ENABLED`，GET不生成新分析。历史分页不会隐藏独立的当前指针；旧无来源Run、过期、失败尝试明确区分。

推荐显式顺序是：Fusion已入新表 → A告警基本分析 → I事件诊断 → 用户创建/修改Case → 用户启动完整基础调查C1–C6。A与I都不会自动接续下一阶段。完整基础调查包含背景、四领域主分析、必要字段/问题级Deep、来源图和正式交付，不等同A基本查询。

人工任务H由用户补充系统尚未接入的事实。H保存本身不创建或启动机器Run；成员未变而需吸收新反馈时，调用Case `/baseline/prepare`，再显式调用 `/runs/{run_id}/start`。prepare只生成/复用pending，运行中仍单活跃，下一轮手动启动。字段、并发及4个例子见[人工任务与准备下一轮](socai2-human-tasks-20261104.md)。Q接口仅预留，正常业务请求仍501。

## 四个具体例子

1. **两条告警构成事件。** PowerShell进程告警A1与网络连接告警A2先分别调用A，得到各自分诊T1/T2；调用I读取完整成员及有效同次分诊，保存D1。共享主机/时间只能作为关联线索，不能据此证明进程发起了连接；未决问题保留，C阶段可继续补证。
2. **用户因等待时间重发。** 客户端再次向A1提交同一个operation_key，返回同Run现状，不再调用模型。若此前Run未知，则保unknown，用户应查看记录；新operation_key表示新的一次显式执行，不是默认重试手段。
3. **执行中材料更新。** A1已冻结M1，M2到来后完成的T1仍保历史及对应Explain；结果不会作为M2有效分诊采用。GET的freshness/valid_for_current_input明确说明失效，新C1不把过期结论当本轮可用分析。
4. **人工确认改变后续分析。** 首轮Case结果不能判断进程任务是否授权；用户完成H，仅确认A1为授权维护，并明确A2连接归属未知。prepare+start建立第二轮C，冻结H的准确revision与A1范围，和指定首轮Result比较；不会把A1的授权泛化给A2，也不会重跑A/I或覆盖首轮报告。

## 验证边界

A/I底层执行器的独立PG检查见[告警执行器](socai2-alert-basic-executor-20261104.md)和[事件执行器](socai2-incident-diagnosis-executor-20261104.md)。H/prepare本批10+5项及6项受影响回归见[固定汇总](../operations/socai2-human-tasks-20261104.json)。这些历史汇总保持原验证边界；本文和新版OpenAPI不追加或替代它们的测试结论。真实Bearer认证、独立服务、实际模型及验证湖的结果需看当前验收批次。
