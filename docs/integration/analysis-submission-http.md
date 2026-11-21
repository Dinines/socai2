# 事件与案件异步提交接口

2026-11-21，21 正式版 `c173-release-20261121-03` 提供异步事件诊断、Case 后轮调查及任务读取。建案返回 `allocations[]`，已受理的首轮从 `initial_task.status_url` 查进度。[正式合同与调用示例](c173-backend-handoff-20261121.md) · [实际验收](../../docs/operations/evidence/c173-bounded-json-20261121-01/README.md)

2026-11-15 历史验证。**事件E37已在候选源码接通并完成本地完整流程验证，尚未部署到本地18024或21。** 当前源码候选80操作（新增Case investigations；首轮切换已删除E11/E13）；21实际64操作、静态Swagger71，[本机旧服务仍在运行、未切候选](../operations/evidence/http-local-runtime-review-20261115-01/README.md)。该次测试描述当时待统一发布的版本，不可把新请求体发给仍为同步合同的已部署E37。Case新的异步POST已挂载并完成真实调度/保存/HTTP读回：新批20次受理、41次终态读取/原key回放通过；另28次7A和47次7B已结束样本只读通过。模型和查询使用替身，正式TCP/真实模型验收仍待后续。

事件已通过真实隔离PG、专用Redis、实际A/I执行器及受控模型的“提交→任务保存→消费→Run/诊断保存→HTTP读取”。本批103次无凭据HTTP请求通过，含范围/覆盖及失败、unknown样本；HTTP本身不调用模型。另只读复用已结束的真实模型样本，其正文质量NOT_PASSED保留。见[验收回执](../operations/evidence/incident-async-http-20261115-01/README.md)。

对外默认内部可信，不需要登录、Token或角色。事件与Case路由分开注册，内部调查执行器与对外HTTP分开；无旧同步兼容入口。告警通过正常入站自动分诊，候选已移除E36。

**当前审计状态：** 第7步5项已采纳问题按F1–F5逐项修复，F1已通过[22次同源只读GET](../operations/evidence/incident-case-scope-fix-20261115-01/http-readback.md)，F2也已通过[24次同源只读GET](../operations/evidence/case-input-metadata-fix-20261115-01/http-readback.md)，F3已通过[52次同源只读GET](../operations/evidence/case-retry-fix-20261115-01/http-readback.md)，F4也已通过[89次同源GET](../operations/evidence/case-trigger-fix-20261115-01/http-readback.md)，F5也已通过[90次同源GET](../operations/evidence/execution-contract-fix-20261115-01/http-readback.md)；上述通过记录限原测试范围，不代表新规则或整体验收通过，暂不部署。最新规则及直接验证见[HTTP目标流程](../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#审计修复后的目标业务流程与接口验证)。

自动更新的目标分工已确认：整事件关联按“告警变化→事件诊断业务更新→该事件活跃Case检查”推进；单告警关联保持固定范围，分诊晚到不直接触发Case，下次调查读取。建案首轮、手动check/rerun和有效人工任务结果仍按原规则处理。不同请求分别排队，相同operation_key同内容只返回原任务；这些新增约束尚待修复验证，调用方不需新增HTTP请求或传内部调度参数。

## 目标功能与路径

| 功能 | 目标POST | 操作结果 |
| --- | --- | --- |
| 事件检查更新或重新诊断（本地已验） | `/api/v1/socai2/incidents/{incident_id}/diagnose` | 持久受理成功返回202及task_id/status_url；不等待诊断完成 |
| 案件检查更新或再次调查（本地闭环已验） | `/api/v1/socai2/cases/{case_id}/investigations` | 持久受理成功返回202及task_id/status_url；已验证重复key、参数错误、真实执行/保存/读回；无变化跳过不产生Run，再次调查生成新Run |

case_id和incident_id是已有主体UUID。两种请求体相同：

```json
{"operation_key":"00000000-0000-4000-8000-000000000701","mode":"check"}
```

| 输入字段 | 类型及含义 |
| --- | --- |
| operation_key | 必填UUID，表示本次操作；相同操作重放沿用原key。换对象或mode但复用同key返回409 |
| mode | 必填check或rerun。check要求调查核心检查当前材料是否变化，无变化可跳过；rerun明确要求重新分析，仍遵守主体状态和统一调度 |

不接收额外请求字段或查询参数。业务来源固定user、记录人来自服务配置；调用方不传tenant、actor、kind、source、队列、模型参数、比较对象或自选时间窗。

## 成功回执与后续读取

目标返回202：

```json
{
  "task_id":"00000000-0000-4000-8000-000000000702",
  "subject_type":"incident",
  "subject_id":"00000000-0000-4000-8000-000000000703",
  "status":"accepted",
  "status_url":"/api/v1/socai2/incidents/00000000-0000-4000-8000-000000000703/analysis-tasks/00000000-0000-4000-8000-000000000702"
}
```

| 输出字段 | 含义 |
| --- | --- |
| task_id | 已保存的原任务ID，同key同内容不多建 |
| subject_type、subject_id | 真实受理对象的类型和ID |
| status | 固定accepted，表示受理回执，不表示已经开始或完成 |
| status_url | [任务详情GET](analysis-tasks-http.md)的真实相对路径；继续读取实际状态、尝试、Run和结果 |

即使任务之后已经完成或跳过，重放相同POST仍返回原受理回执；最新状态读status_url。事件批已验证跳过后重放仍为accepted回执、GET如实为skipped，不创建新任务或Run；Case也已验证完成/跳过后的原key重放，21类记录摘要保持不变。

读取业务对象不必等待模型完成：对象、关联和异步任务先保存，尚未实际执行时Run可以为空，结果列表可以为空；HTTP仍用accepted表达等待。执行前才冻结本轮材料；失败保留对象、原有效结果和失败记录，不能因为最新任务失败就清空旧结论，也不能因旧结论存在就把最新任务显示为完成。GET不启动分析。

Case已知未发送的连接故障按冻结策略最多自动重试一次，仍查询原task；不用再次POST制造新任务。结果未知的超时不自动重试，旧Run保留unknown而本地已结束任务可为failed。具体等待、耗尽和原件读取见[任务重试说明](analysis-tasks-http.md#case已知故障的一次重试)，F3本地同源读回已通过，正式服务尚未发布。

受理只调用调查核心AnalysisTaskService.submit，事务提交后才生成回执；HTTP不直接操作Redis或启动模型。调查侧负责将已持久任务补入队列，入队暂时失败不撤销已保存任务。事件真实handler领取、执行、保存及读回已本地验证；服务发布仍按整个change统一进行。

调用顺序：提交E37 → GET status_url → 如有latest_run_id/结果链接，读取事件诊断详情 → 需要原件时沿trace进入步骤和工件目录。`check`无变化返回任务`skipped`、`reason_code=no_changes`且无Run；`rerun`本批保存独立的新Run和诊断，旧诊断/输入不覆盖。失败或unknown沿原状态显示，不把202当完成，也不自动换key反复提交。`input_selection`和`analysis_coverage`的每个字段、部分覆盖及空值含义见[事件读取指南](incident-analysis-http.md)。

Case 调用顺序：`POST /cases/{case_id}/investigations` → GET 回执的status_url → 任务attempts中的run_url和results中的url → E12/E14返回的previous_run_url、comparison_result_url。链接只取本轮冻结记录，不随最新调查漂移，具体空值和比较原因见[结果读取指南](run-records-http.md)。

Case 本轮真实受理示例（隔离开发数据，不是21可运行样本）：

```json
{"task_id":"131d7607-99c7-4952-907d-25ed17d50b39","subject_type":"case","subject_id":"32ddf37a-6f0c-5571-b22c-40eef480a37f","status":"accepted","status_url":"/api/v1/socai2/cases/32ddf37a-6f0c-5571-b22c-40eef480a37f/analysis-tasks/131d7607-99c7-4952-907d-25ed17d50b39"}
```

[请求及固定operation_key](../operations/evidence/case-update-http-20261115-01/sample.json)、[实际20次请求/保存回执](../operations/evidence/case-update-http-20261115-01/admission-pg-01.json)保留原批。该回执的accepted永远表示原受理身份。现initial和rerun均completed，各有一个Run/Result；check为skipped/no_changes、attempts/results为空、latest_run_id=null。终态重放仍返回上面的原回执，GET保留实际终态。见[41次终态读取/原key回放](../operations/evidence/case-update-http-20261115-01/execution-read-pg-03.json)及[实际终态/比较示例](../operations/evidence/case-update-http-20261115-01/examples.json)。HTTP不启动消费；已结束样本不重复执行。

## 错误

| HTTP / code | 含义和处理 |
| --- | --- |
| 404 / subject_not_found | 路径中的对象不存在 |
| 409 / operation_conflict | 同kind、同操作编号已用于不同主体或mode；保留原任务，勿盲目换key重复操作 |
| 409 / subject_closed | 对象已关闭，按原管理流程重开后再明确发起新操作 |
| 409 / empty_scope | 事件或案件没有可分析成员 |
| 422 / 字段校验detail数组 | UUID、mode、必填字段不合法，或额外请求字段 |
| 422 / invalid_input | 不支持的查询参数等输入错误 |
| 503 / service_unavailable | 受理配置不可用或数据库保存未确认；不返回虚假task_id。同key重放可恢复已持久的原受理身份 |

业务错误为`{"detail":{"code":"operation_conflict","message":"同一操作编号已用于不同请求","context":{}}}`。核心operation_key_conflict及subject_scope_empty仅在HTTP适配层映射为目标code；不修改内部调用合同。

## 配置与验证材料

[本轮回执](../operations/evidence/analysis-submit-preparation-20261114-01/README.md)与[实际请求/响应](../operations/evidence/analysis-submit-preparation-20261114-01/examples.json)包含26次独立测试应用请求、两个真实任务、无attempt/Run、幂等及6类既有数据前后保持。只有合成主体和任务，无模型、Redis或取证工具调用。

[当前已联验候选OpenAPI](../operations/evidence/case-update-http-20261115-01/candidate-openapi.json)包含事件和Case POST/202，共80操作、无security要求。[三类Swagger包](../operations/evidence/case-update-http-20261115-01/swagger/manifest.json)包含请求、返回、错误及实际隔离示例；静态包已更新，21尚未发布，历史快照保持原批次。

HTTP仍显式配置读写数据库和`SOCAI2_HTTP_CONTEXT_FILE`（租户、记录人）、`SOCAI2_ANALYSIS_TASKS_CONFIG_FILE`（任务策略）。记录人用于保存关联，需是当前环境有效用户记录，不是调用方登录校验。当前第6步执行侧单独配置[统一调度器](../../deploy/local-investigation/analysis-aic-dispatch.example.json)及[A/I/Case执行器](../../deploy/local-investigation/analysis-aic-executors.example.json)，factory为`app.socai2.analysis_case_executor:executors`；替换原A/I工厂，不启动第二个调度器。HTTP服务不承担执行器生命周期。

[HTTP发布片段](../../deploy/http-service/analysis-tasks-release-fragment.json)列明读取依赖（含incident_inputs.py）及核心组合片段，供整个change统一打包；不是可直接执行的发布profile。[Case容量分配及首轮任务受理](case-allocation-http.md)已本地验收；[第6步Case首轮](case-initial-http.md)已完成实际执行和读取联验，第7步check/rerun已完成受理→实际执行→HTTP读回；周期样本只读也通过。[第7步HTTP片段](../../deploy/http-service/case-update-release-fragment.json)须与同版核心analysis-case片段一起装配。按11-15最新范围，第8–10步定向分析、手动综合及知识后台异步维护后置，保留设计、未实现状态，不提前开放接口或作为本期第1–7步主流程联验前置。

本轮未重启或发布服务、未提交推送。发布授权保持，满足整个change验收/交接/独审后统一同步21、Git、Swagger和交接文档。
