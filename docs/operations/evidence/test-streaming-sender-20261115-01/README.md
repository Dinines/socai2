# S01分阶段发送器直接验证

2026-11-15。依据[同一T2后续子步设计](../../../../openspec/changes/schedule-streaming-investigation-updates/test-data-design-20261115.md#t2后续子步s01分阶段kafka发送与即时持久化)，完成prepare/validate/send最小适配，当前未获实际资源就绪通知，**未执行真实Kafka投放或CH/PG写入**。

新增`streaming_send.py`显式绑定新batch与候选资源，固定S01-context十二条、S01-alerts三条；不提供S04、清理或调查执行入口。现有`source_wire`/schema/hash/私密Kafka加载复用，原逐消息ACK逻辑提取为`alert_kafka.send_records`，旧`send_kafka`的run_id-topic限制保留。新prepare不打开expected/identity-map/actions控制文件；独立wire/profile/资源回执及源码摘要冻结，实际身份仍由落库读回取得。

[16项及2个子断言](sender-tests-01.json)通过，包括12项新阶段检查与4项受影响旧发送检查。覆盖schema/新batch独立于topic、12/3分阶段、答案隔离、同tenant key/原字节发送、intent先落盘、ACK只算accepted、unknown/错ACK/取消后停止、已知发送前失败、固定receipt拒重派、缺/错真实入湖回执阻断告警、错误资源/tenant/profile/hash/transport/S04拒绝。全部使用明确受控producer及resource/readback形状夹具，未接真实broker或查询服务；其中fixture声明`source=real_lake_readback`只为校验门控字段，并附`test_origin`明确模拟，不能当真实通过证据。

[Ruff](ruff-01.json)和[OpenSpec strict](strict-01.json)通过。原T2/W2已过组件未重跑，旧数据/原件未改；测试仅在临时目录生成新身份材料。首次Ruff报告导入排序和两处测试写法，已修正；本次没有业务失败或历史unknown被追认。

实际下一步及配置/命令见[当前T2入口](../../../../tools/testdata/STREAMING.md#当前s01分阶段投递入口)。调查方负责资源/Fusion并通知就绪，测试随后冻结一个新的实际batch/expected：先context Kafka→湖原件/0额外业务，再alerts Kafka→3A/同一I/3成员/4条accepted初始任务，0attempt/Run/模型，HTTP方复用真实identity-map只读联验。本回执只证明发送组件边界，不证明实际入站、模型质量或完整调查通过。
