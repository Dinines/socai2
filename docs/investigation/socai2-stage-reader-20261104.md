# A/I读取与Case C1新鲜度：字段和使用合同

2026-11-04。本批接通新表告警基本分析/事件诊断的四条只读接口，以及C1冻结时的新鲜度判断。沿用29表458列；没有页面修改或生产切换。实际A/I查询/模型执行器仍待接，本批验证的是已保存结果的真实读取与消费，不是推理质量。

## 1. 解决的问题与实际流程

`latest_triage_id/latest_diagnosis_id`表示最近一次被采用的成功结果。材料或成员随后变化，指针仍可保留这份历史结果，不能仅凭“指针存在”声称它适用于当前输入。

1. A/I发布和读取共用 `stage_inputs.SOURCE_SQL`；从上批存储模块原样抽取，原输入版本与指纹含义不变。
2. C1原来的单条快照SQL内增加比较：同一数据库快照选取当前材料/成员/分诊/反馈/业务字段，核对应Run和冻结工件的归属、类型及版本，再比较完整JSONB输入。没有先读指针、后读变化材料的双时点拼接。
3. 数据库只返回四态结果，不把用于比较的完整原文复制进C1。C1原128KiB、模型8192字节/字段2048字节上限不变。
4. 新冻结C1仅将输入仍current的分诊和已接受成功诊断提供给模型。过期、无法验证的正文仍保存在冻结上下文，可供查账；不再生成它们的可用模型引用。人工反馈仍有独立human_statement身份。
5. 新GET接口在REPEATABLE READ、READ ONLY事务内读取当前指针、结果与历史，返回有效性和失败尝试，不生成解释、不更新业务时间。已冻结旧Run不重新读取当前数据或改写原件。

旧v1上下文兼容：新增字段有默认值，历史已保存的diagnosis_usable值保留；没有triage_usable的旧快照按原冻结引用读取。只有新启动Run采用本批新鲜度规则，不把旧Run重新解释成今天的状态。

## 2. 四条接口

共同前缀 `/api/v1/socai2`，需要现有 `alerts:read` 权限，租户来自认证主体。独立配置 `SOCAI2_ANALYSIS_READ_ENABLED=false` 默认关闭，不依赖是否启用Case接口。

| 方法与路径 | 输出 |
| --- | --- |
| GET /alerts/{alert_id}/analysis | 当前分诊及Explain、A历史执行 |
| GET /incidents/{incident_id}/analysis | 当前诊断、I历史执行与失败尝试 |
| GET /alerts/{alert_id}/analysis/runs/{run_id} | 本告警指定A执行结果 |
| GET /incidents/{incident_id}/analysis/runs/{run_id} | 本事件指定I执行结果 |

历史默认20条、上限50，按requested_at和Run ID倒序，使用before_run_id继续向前；游标必须属于本租户、本对象及同类执行。每页同时提供独立current结果，不受历史翻页影响。跨租户/跨对象/错类Run返回404，缺权限403，未启用503。这里没有新增列表筛选、导出或管理动作。

[运行时OpenAPI](socai2-stage-reader-20261104.openapi.json)已导出到设计树；DTO结果正文选择明确字段，不输出tenant_id、operation_key、request_hash、blob地址或冻结原文。历史Explain按对应Run确定工件ID读取，不能混用另一轮最新解释。正文超过128KiB、非完整留存、外部/缺失内容、hash/大小不一致时返回不可用原因，不返回残缺正文。

## 3. 20项字段明细

| 项 | 字段 | 来源与口径 |
| --- | --- | --- |
| V01 | subject_id / kind | 明确告警或事件身份；不是Case ID |
| V02 | current_pointer_id | alerts.latest_triage_id / incidents.latest_diagnosis_id |
| V03 | current | 当前指针对应的Run和结果；可过期，不自动清除历史 |
| V04 | current_unavailable_reason | 指针结果缺可验证Run时明确提示，不冒充当前有效 |
| V05 | freshness | current / stale / unverified / unavailable |
| V06 | is_current_pointer | 此结果是否仍为当前采用指针；与新鲜度分开 |
| V07 | valid_for_current_input | 当前指针＋current＋Run completed；I还须diagnosis.validation_state=accepted |
| V08 | run.id/kind/state | 实际runs记录，含running/unknown/failed等 |
| V09 | requested/started/ended | 数据库保存的本轮时钟，未知结束时间NULL |
| V10 | executor_version/input_artifact_id | 执行来源和不可变输入身份，不返回全文 |
| V11 | stop_reason/delivery_state | 实际停止与交付状态；有结果不等于完整调查 |
| V12 | 分诊结果正文 | 同次assessment的verdict/rationale/confidence/score_state/recommendations/actor/producer/assessed_at |
| V13 | input_material_id | 分诊绑定的材料版本，与当前latest材料可不同 |
| V14 | explanation | 本Run工件ID、available/reason/content；按hash和大小核对 |
| V15 | 诊断结果正文 | 同次diagnosis的revision/state/summary/diagnosis/open_questions/producer及时间 |
| V16 | source_fingerprint | 诊断原输入指纹；不直接把它等同当前有效 |
| V17 | error_code | 失败尝试的结构化code；不返回任意异常堆栈 |
| V18 | entries/next_before_run_id | 全状态历史，稳定双键分页，不仅成功记录 |
| V19 | C1 triage_freshness/triage_usable | 新冻结时校验；过期结果保账本但不作为本轮可用模型输入 |
| V20 | C1 diagnosis_freshness/diagnosis_usable | 还核成功/accepted/Case成员交集；范围超出Case仍明确限制 |

current表示输入与冻结内容相同，不是对结论真伪的保证。stale表示内容发生变化；unverified表示旧版/未知冻结合同；unavailable表示缺对应Run/完整输入等。I失败尝试也可有current输入，但valid_for_current_input必为false。

## 4. 例子

**材料变化。** A1基于M1得到分诊T1，事件I1得到D1。M2到来后，两指针仍指T1/D1；GET显示is_current_pointer=true、freshness=stale、valid_for_current_input=false。新Case Run保留它们的历史正文并说明过期，模型视图不再把它们当本轮可用分析。

**新一轮失败。** D1成功后D2失败，D1仍是current指针，D2保留在历史并有error_code；若D1输入没变，它仍可用。不会用D2的状态覆盖D1结论。

**旧记录无完整来源。** 旧分诊只有assessment没有source_run_id时，列表能明确指出当前指针无法验证；不反查旧表或拼出一份新的输入。旧Run已经冻结的材料和显示状态保持原值。

## 5. 验证和剩余工作

7项新ASGI/独立PG检查及受影响回归见[本批固定回执](../operations/socai2-stage-reader-20261104.json)。真实受限PostgreSQL、实际路由和权限依赖；认证主体为替身，无真实登录、模型、湖或业务数据调用。

首轮2过5失败，独立读取参数在子查询被推断为text导致uuid比较失败；显式CAST后定向复核。另1条测试把来源路径中的raw_json字样误认作原文泄露，改为验证真实原文标记后通过。原件均保留，不重写首轮结果。只读事务中并发材料更新不改变该事务的前后读数，UPDATE被数据库拒绝；新事务能看到stale。

下一仍是A常规查询/分诊、I诊断的真实执行适配、请求/回复/步骤/usage留存；完整告警/事件页面DTO、显式Case事件关系、H/Q及外部来源也待接。C2相似历史告警是历史背景（排除本案成员），不属于本批“当前分析”新鲜度合同。生产旧消费者仍未迁移，不能仅启用此读取开关就称新链路上线。旧r13报告修复暂停、5.3未完。
