# F3：Case已知失败重试的HTTP读回

2026-11-15。**F3核心新批次的HTTP读回通过，可收口本项；F4/F5和整个change验收仍未完成。** 本轮只新增直接读取测试和交接说明，不改业务代码、不部署、不消费任务或调用模型。

来源为核心[pg-03](pg-03/result.json)及其[保存快照](pg-03/snapshot.json)。真实隔离`v12_upgrade_dev`，强制只读数据库连接，独立HTTP应用以真实核心读取器和显式可信上下文经ASGI读取。核心使用6次合成模型回复、4次合成连接故障、0真实模型；本次新增模型/执行/写入均为0。不是21 TCP、真实模型或Kafka完整链验收。

[http-read-01.json](http-read-01.json)首轮52次无鉴权GET通过：4个Case及原task、6次attempt/Run、2份Result、模型步骤和20份请求/回复工件均按实际保存关联读取；15张直接相关表的本租户计数/摘要前后一致。核心10份源码摘要与[source-hashes](pg-03/source-hashes.json)一致。

| 场景 | 公开任务/Run读回 | 原件与结果 |
| --- | --- | --- |
| C3 ConnectTimeout后成功 | 同task两次attempt、不同Run；第1次failed且Run有ended_at，第2次completed；retry_count=1、next_retry_at=null | 原失败请求/故障回执保留，成功Run另存Result，不覆盖第一次 |
| C6 PoolTimeout重试耗尽 | 同task两次attempt均failed，最终reason_code=retry_exhausted、retry_count=1，无第三次尝试 | 两轮各自完成的C3请求/回复和C6失败请求/故障回执都可读；未创建假成功Result |
| C3 ReadTimeout结果未知 | task已本地收尾为failed/call_timeout；仅1次attempt，outcome=unknown、retryable=false、retry_count=0 | 原Run保持unknown且ended_at仍null，本地attempt已有local_ended_at；原请求及未知故障回执保留，未补成成功/确定失败 |
| unknown后的另一Case | 在原任务本地结束后开始，正常completed，有实际Result | 结合核心N=1实际调度证据证明本地槽已释放；本次HTTP只核结束记录，不重新启动调度器 |

两份核心等待快照表明重试等待对外为accepted/retry_scheduled；冻结next_retry_at相对首次failed_at为60秒，第二次attempt在该时刻之后开始。核心使用一致测试时钟偏移0/61/122秒，正式配置未改；本次只读核保存时刻，不声称实际等待了60秒或在HTTP中观察到等待中间态。`retryable=true`表示故障分类，是否还有次数看task最终状态及next_retry_at；耗尽后不再自行重投。

首次失败与C3原件还逐一对照[connect首次快照](pg-03/connect-first-snapshot.json)、[pool首次快照](pg-03/pool-first-snapshot.json)，原记录未在重试中改写。核心pg-01（把公开accepted误断言为内部waiting）与pg-02（测试时钟未同步C1导致PG拒绝）原失败保留，不重派；本次HTTP首轮直接通过。

复现入口：[validate_http_readback.py](validate_http_readback.py)；检查代码：[test_socai2_case_retry_http_pg.py](../../../../services/api/tests/test_socai2_case_retry_http_pg.py)。使用显式受控`--config`、已结束`--source`和新的`--output`路径，拒绝覆盖旧回执。公开路径/DTO保持80操作且OpenAPI与原7C候选一致，无新增鉴权；[任务指南](../../../../docs/integration/analysis-tasks-http.md#case已知故障的一次重试)说明调用方如何处理状态。最终发布包待F4/F5、完整流程及独立审计完成后统一冻结，本回执不授权发布。
