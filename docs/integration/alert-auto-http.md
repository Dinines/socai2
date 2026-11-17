# 告警自动分诊：后端查询指南

更新于2026-11-15。当前21候选API为`http://192.168.1.21:18424`，Swagger为`http://192.168.1.21:18480/`，实际80个业务操作、默认内部可信、无鉴权；旧18024/18080已停止。[S01-r3入站35次GET](../operations/evidence/streaming-ingress-http-20261115-02/README.md)已确认3条告警及4条A/I任务可读，[真实A/I的62次TCP读回](../operations/evidence/streaming-ai-http-20261115-01/README.md)已通过，任务/Run/分诊及原答同源；模型正文质量NOT_PASSED（A理由仅“告”）保留。步骤按[HTTP联验计划](../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#已有ai任务执行后的http联验2026-11-15)执行。历史本机联验保留原适用范围，不能据历史记录代替本轮真实验证；本机旧服务本轮未操作。

告警保存后，调查服务登记分析任务，后台执行分诊并保存结果。业务后端只需按告警ID查询进度及结果，无需另调用“分析告警”。候选已移除旧E36 `POST /alerts/{alert_id}/analyze`；该路径返回404，不提供兼容入口，内部执行器继续供调度调用。该删除已在21候选生效，正式发布仍待。

对外服务默认内部可信，请求无需登录、Token或角色信息。以下路径均省略`/api/v1/socai2`。

## 读取顺序与用途

| 要做什么 | GET接口与输入 | 返回什么、后端怎么用 |
| --- | --- | --- |
| 展示告警事实和当前分诊 | `/alerts/{alert_id}` | `facts`是告警自身字段，`material`是最新材料及正文链接，`triage`是当前分诊及其`source_run_id`。`triage=null`表示当前没有可读分诊，不能据此判定任务失败或未受理。 |
| 读取入站原件 | `/alerts/{alert_id}/records/source_artifacts`，跟随`content_url` | 原始入站工件属于告警，可以没有Run；它不在某次Run的工件目录中。该入口读取保留原件，不再次采集。 |
| 查看自动任务进度 | `/alerts/{alert_id}/analysis-tasks`，可传`limit/cursor` | `items`包含任务ID、真实来源、状态、尝试和结果链接；`total`为该告警全部分析任务数。新告警自动首轮为`source=ingress`、`intent=initial`。按`status_url`继续查询同一任务。 |
| 查看指定任务 | `/alerts/{alert_id}/analysis-tasks/{task_id}` | `status`说明受理/运行/结束，`attempts`保留每次实际尝试，`latest_run_id`可为空；`results`提供真正保存的分诊记录及来源链接。任务编号不是Run或分诊结果编号。 |
| 展示当前及历史分诊 | `/alerts/{alert_id}/analysis`，可传`limit/before_run_id` | `current`是当前指针对应的分析，`entries`是历史尝试；失败、未知及没有结果的Run也会保留。用`is_current_pointer`、`freshness`和`valid_for_current_input`判断是否适用于当前材料。 |
| 读取一次分析 | `/alerts/{alert_id}/analysis/runs/{run_id}` | `run`是本次执行状态，`result`是实际分诊正文，含判定、理由、置信度和建议；`explanation`和`partial_analysis`保留各自可用性，不能把局部内容当成完整分诊。任务的`run_url`和结果的`url`指向这里。 |
| 按条件查询分析记录 | `/analysis-runs?subject_type=alert&subject_id={alert_id}`，可再传`intent/state/limit/cursor` | 返回真实`task_id`、Run状态、结果链接和同范围统计。尚未产生Run的任务不会出现在这里，应从任务接口查；历史没有任务关联时`task_id=null`。 |
| 查看执行步骤和原件 | `/alerts/{alert_id}/analysis/runs/{run_id}/trace`，跟随`steps_url/artifacts_url` | 两个目录均按`limit/cursor`完整分页；步骤详情按ID定位，工件沿`content_url`读取保存正文。追溯保存内容，不触发模型或取证工具。 |

## 状态与结果的区别

- `accepted`：已经保存任务，可能尚未执行或正在等待重试。此时没有Run是正常情况。
- `running`：实际尝试已开始；准备输入时可能仍没有Run。
- `completed`：本次处理结束。业务判定仍看`result.verdict`等字段，不能把流程结束理解为告警安全或模型结论通过质量验收。
- `failed`：读取`reason_code`及各次尝试的错误；已保存的Run、原答和部分结果继续可查。
- `skipped`：本次无需执行等真实原因见`reason_code`。可能保留此前失败尝试，不能清空历史或假定从未运行。

`update_state`表示是否具备周期更新资格；告警为`not_periodic`不代表首轮自动任务未执行。自动首轮是否已受理/完成，以实际任务及结果为准。

管理字段变化不删除原分诊。F2已完成[24次同源HTTP读回](../operations/evidence/case-input-metadata-fix-20261115-01/http-readback.md)：修改负责人/标签后，Case仍使用同原材料的原A及查询回执，check无变化跳过。A历史的freshness仍按原完整输入比较，可能为stale；不要用这个字段代替Case冻结C1的triage_usable。含义及读取位置见[管理变化后的已有分诊](run-records-http.md#管理变化后如何读取已有分诊)。该修复已进入21候选；F4新批本机验证已通过，21实际执行按本轮回执核对。

## 错误与空值

对象、任务或Run不存在/不属于所查主体时返回404；错误的UUID、分页或筛选返回422；读取依赖或必需配置不可用返回503。具体错误体沿现有接口Schema，不能把503当成“无结果”。

合法的空任务列表返回200和`items=[]`；未产生结果时保留`result=null`或`results=[]`，不编造分诊。置信度不可用时保持相应空值和`score_state`。原件可能尚未保存、保留不完整或外部内容未加载，应展示其`availability`，不以HTTP 200代表正文可用。

## 本轮联验边界

[本地联验回执](../operations/evidence/alert-auto-http-20261115-01/README.md)：受控模型批28次无凭据GET、真实模型批最终30次GET通过，任务/Run/分诊同源，材料与原件正文按数据库原值返回，十类记录前后摘要相同。真实样本的5个步骤、13份Run工件及1份告警级入站原件均可查询。HTTP未调用模型、未创建业务数据。

真实样本模型正文质量为**NOT_PASSED**，接口保留原答；不把`completed`或HTTP成功当作结论质量通过。9项HTTP边界、无鉴权及独立应用检查、Ruff/OpenSpec strict已通过。[80操作候选OpenAPI](../operations/evidence/alert-auto-http-20261115-01/candidate-openapi.json)只反映候选源码，不是正式在线Swagger。

事件异步诊断已接实际执行器并完成本地提交→消费→保存→读回，候选E37已切202，见[提交指南](analysis-submission-http.md)。当前候选已包含该异步合同；正式旧服务保持停止，联调使用顶部候选入口。
