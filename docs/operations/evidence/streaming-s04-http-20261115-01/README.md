# S04 失败路径 HTTP 读回

2026-11-15。**44次无鉴权TCP GET通过；S04成功更新链未通过。** API仍为21候选18424，Swagger18480/80操作。测试独占Kafka增量投放及唯一最终保存快照，调查独占执行与停止；HTTP只读，不手动check/rerun、不直接查库或写业务、不启动模型，也没有重复上一批58GET。

## 实际发生的结果

| 对象 | HTTP实际读回 | 对接含义 |
| --- | --- | --- |
| 新A04 | 告警`d7bc92ec-691e-5b45-bc03-ccb85367dba8`，Run `e2e3e80e-031c-5641-909e-6f913cf50e16` completed；直接来源仅E13 `324ddc21-7635-5ab6-be3b-c339bd6aeacb` | 来源、材料和结果均可读取；completed不表示模型正文已全面验收 |
| 原事件 | `263a1c58-e9c6-4ba4-9204-3b0568970551`成员变为4，新Run `c119d6be-e735-5189-a6d2-8db8490ab84d` failed，错误`model_response_not_complete` | 本轮固定选入4条，但analysis_coverage=unknown，不能将选入数冒充分析覆盖 |
| 失败诊断 | `8f82c04a-4e3b-53f8-9d97-8eed33cd9180`为failed；summary、diagnosis、generated_at均null | 失败记录可查，不能展示成有效结论或用空正文冒充成功 |
| 旧事件诊断 | current_pointer仍为`d45f13bd-ce73-5dd0-8907-5dd215455ba1`；current.freshness=stale、valid_for_current_input=false | 旧结论保留用于追溯；存在current不等于适用于目前4条成员 |
| 停止后的检查 | 3条check均skipped/automatic_attempts_stopped，0attempt/Run；事件update_state.eligible=false，ineligible_reason=model_response_not_complete | 没有自动重试；next_check_at不保证再次执行。失败task的retry_count=0、next_retry_at=null |
| 整事件案及单A01案 | 仍分别3和1成员，各仅原initial任务/Run/Result，当前assessment保持；comparison_context=initial，两个比较链接均null | I没有新的有效诊断，所以没有Case后轮；没有可供本批验证的前后轮比较，不构造CaseR2 |

## 核对范围和原件

[读取结果](result.json)记录31次详情/目录/来源GET和13份新增Run原件GET，共44次且全部200；5条新任务、2次attempt/Run、7步骤、18份新Run工件目录与同源保存一致。告警原材料及E13来源原件另包含在31次请求中。Case只核本次失败后的成员、任务/历史、当前判断和原Run比较空态，没有重新读取旧案全部原件。

- [冻结读取计划](plan.json)、[31次响应](get-01.json)、[13份原件响应](content-01.json)、[只读脚本](read_failure.py)。首次HTTP及离线断言直接通过，未重复请求。
- 测试唯一[保存快照](../test-streaming-s04-20261115-01/analysis-pg-01.json)，SHA `0af1dc0ae2b9b709070459c1d74e669d31a375a36514322dd25276d5ee8e4af3`；[实际身份map](../test-streaming-s04-20261115-01/actual-analysis-map-01.json)及[入站验收](../test-streaming-s04-20261115-01/ingress-acceptance-01.json)。本目录supplied两个JSON仅为取得时测试map的逐字副本，用于固定验证输入，不另造身份或新快照。
- [134项失败保存核对](../test-streaming-s04-20261115-01/failure-record-validation-01.json)通过，测试[统一结论](../test-streaming-s04-20261115-01/acceptance-01.json)已纳入本次44GET，明确failed_success_path_failure_evidence_verified；[旧六Run和原件保持](../test-streaming-s04-20261115-01/upstream-preservation-01.json)有独立保存证据。最终测试map与本目录固定身份、Run、任务及旧案基线一致。
- [失败分析](../test-streaming-s04-20261115-01/failure-analysis-01.json)确认实际I模型请求max_tokens=3000、finish_reason=length、输入6499/output3000，原答截于source_refs。原请求、响应及独立原答正文均经HTTP逐字读回。Case C3/C6的8192是另一环节配置，不能据此宣称本次I也使用8192；本轮没有改额度或重跑。
- 当前可读[失败I Run](http://192.168.1.21:18424/api/v1/socai2/incidents/263a1c58-e9c6-4ba4-9204-3b0568970551/analysis/runs/c119d6be-e735-5189-a6d2-8db8490ab84d)及[原任务](http://192.168.1.21:18424/api/v1/socai2/incidents/263a1c58-e9c6-4ba4-9204-3b0568970551/analysis-tasks/4abd74b8-28fc-4109-9462-5dc471e409c3)，不需要Token。

失败任务/停止原因/原件保留和HTTP表达均符合实际保存，本步未发现需修改的HTTP合同或路由问题。事件新诊断、活跃Case后轮及比较的正向业务效果仍未完成；调查模块定位事件输出截断，本轮原答及NOT_PASSED不追认、不重采样。整个change、W2–W4、结束审计和正式发布均不由本回执核销。
