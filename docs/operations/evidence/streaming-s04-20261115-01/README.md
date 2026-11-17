# S04真实增量执行

本步复用原S01来源、既有事件和两案。测试独占E13/A04 Kafka发送和保存断言，调查根对话独占唯一调度器的启停，HTTP只读实际新结果；不重投S01、不重做首轮、不新建Case。

本轮已执行，**S04完整更新/比较尚未通过**。来源预期及冻结身份见[测试目录](../test-streaming-s04-20261115-01/README.md)，实际[入站回执](../test-streaming-s04-20261115-01/ingress-acceptance-01.json)已通过：E13先入湖，A04唯一来源为E13且合入原事件，3→4成员。入站只新增1条A initial，旧两案仍3/1成员、0新Run。

[当前归并/配置预检](preflight-01.json)证明索引仍指向原I、TTL78813秒，8份运行文件及镜像保持；未改窗口/模型预算。[启动回执](start-01.json)记录原唯一容器14:07:45Z正常启动。A04完成，I检查于14:08:56Z以`model_response_not_complete`失败，3条等待检查均`skipped/automatic_attempts_stopped`，没有自动重试。当前只有2个新attempt/Run，没有Case后轮；[正常停止](stop-01.json)前所有任务终态、0在途，14:09:47Z exit0。

测试从[唯一最终快照](../test-streaming-s04-20261115-01/analysis-pg-01.json)完成[134项失败记录及保留检查](../test-streaming-s04-20261115-01/failure-record-validation-01.json)：I执行前确实选入4成员、4份当前分诊及对应12条历史/本轮A查询回执；0新Case任务/Run，原两案、旧I指针和6个既有Run/原答保持。新增2次真实生成共12027tokens（输入8709、输出3318，费用未知），7步骤/18份Run工件；新A另有1份入站原件。没有Case C4、C3/C6或新比较，不把测试直接查湖当作Case已查询。

[失败原因](../test-streaming-s04-20261115-01/failure-analysis-01.json)及根侧[原答离线核对](saved-response-review-01.json)确认：I实际请求`max_tokens=3000`，输出3000、`finish_reason=length`，5449字符正文停在引用列表；原始工件与响应中的raw完全一致，未发现保存截断。I四条成员assessment仍为“A”，A04理由仍为“告”，质量NOT_PASSED保留；扩额度也不能据此证明正文正确。Case的8192不是I的实际限额。本轮不调额度、不重采样，也不重派已结束任务；原截断失败保持。

[HTTP44次实际GET](../streaming-s04-http-20261115-01/result.json)通过：31份详情/目录/来源与13份新增Run必要正文，5新任务/2Run/7步骤/18工件目录均与上述唯一快照一致。新I诊断failed、无结论、coverage unknown；旧latest指针保留，但`freshness=stale/valid_for_current_input=false`，不冒称仍适用当前4成员。两案仍3/1成员、各原initial唯一Run/Result及assessment，comparison仍initial/null。HTTP没有业务写入、数据库或模型调用。

完整S04更新/比较仍未通过。无新CaseRun，因此本步不生成新Case查阅卡，上一轮40卡不因本次入站视为新增调查。W2非空/跨Run、W3/W4和整体独审/发布保持未完；独立读取/查阅工作可继续，不能以这些通过核销S04正向链缺口。未正式发布或提交推送。

[测试统一验收](../test-streaming-s04-20261115-01/acceptance-01.json)与[根侧收口](closure-01.json)均明确`S04_successful_update_accepted=false`。两份活动OpenSpec严格校验、根侧脚本Ruff、限定diff检查及295个文档本地链接通过；任务仍2/11、主31/41。检查通过不替代未到达的Case更新/比较。

第一次启动包装调用误以为统一汇总状态应为`passed`，实际为`ingress_passed_analysis_not_started`，在本机SSH前退出；[原失败](start-invocation-01.json)保留，改用汇总链接的实际`alerts-readback`通过回执启动，未重复启动或提交任务。测试发送前漏带Kafka TLS模块的失败另保留在其目录；补齐当前依赖后才首次实际发送，不属于消息重派。
