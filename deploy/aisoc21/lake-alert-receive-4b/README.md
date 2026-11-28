# 湖告警4b：首次接收、初诊登记及完整原文

本目录是候选配置，尚未发布到正式消费者。入口是`LakeAlertReceiver.receive(row, decision=...)`，接收3f/4a取得的完整湖版本；4c再接持续交付。连接配置和凭据沿受控运行配置，不能把示例库名当作已选择的部署目标。

1. 选择[4a profile](../lake-alert-selection-4a/selection.example.json)及[receive profile](receive.example.json)。前者绑定ClickHouse库、租户/来源/映射与候选规则；后者明确PostgreSQL库、RawAlert来源、字段投影、大小/时间预算及初诊重试参数。租户隔离与全局`metadata.uid`身份分别处理。
2. 对目标PG应用[增量130](../../database/lake_alert_receipts.sql)：`install_reader.py lake-alert-receipts --profile <显式配置>`。需已有V1及128、配置已有reader和analysis_ingress角色；不重建旧库。当前新装入口在配置analysis_ingress时使用同一增量。迁移不启动消费者或初诊执行器。
3. 用receive profile的`material_bytes`、`snapshot_bytes`、`initial_analysis`建立`Socai2AlertSink`，与真实`FusionEngine`一起传给receiver。参数不一致即拒绝；正文接收、首次快照生成/恢复/缓存及PG读回使用相应预算。示例为32MiB正文信封和64MiB完整快照，是应用预算，不是ClickHouse/PostgreSQL字段长度上限。信封可能重复包含正文，不应把预算解释成原始Kafka消息大小。
4. 一次PG事务写入全局来源回执、告警、完整材料、来源引用、事件成员及首次A/I任务。只有事务提交成功后返回`created`；相同ID同版本返回首次保存的`duplicate`，不追加材料/初诊、不覆盖人工字段。`held`、`failed`、`unknown`均不能视为交付成功。缓存缺失或冲突不能伪造原Fusion结果。

必要字段无法可靠投影时保留明确hold，例如标题缺失、严重度未知/未映射。device.hostname可用于hostname投影，device.ip另保留对象索引；设备IP不伪装成源IP。完整OCSF和原JSON字符串保存在材料中，收到的Kafka OCSF正文可通过湖版本读取；raw_payload仅对应可选raw_data，缺失为空不表示OCSF原件缺失。

当前不可变来源的发现类在配置`initial_activity_ids=[0,1,99]`时可接收明确告警的Unknown/Create/Other，不修改其原活动值。Update/Close、失效状态、ID/字段冲突及同ID异文仍待核。未指定新配置的旧v2 profile沿原Create规则；v1历史规则保持。

## 读取合同

外部告警字段和路径保持既有合同，材料接口返回原`ContentView`：

- `GET /api/v1/socai2/alerts/{alert_id}`取得材料的`content_url`。
- `GET /api/v1/socai2/alerts/{alert_id}/materials/{material_id}`：`content_text`为完整OCSF原JSON；`content_json.ocsf_json`保留精确JSON数字；`content_json.raw_json.field_metadata.lake_ingress.lake_ref`冻结湖关联，旁侧`lake_database`记录目标库。
- 将lake_ref的`event_id`用于`GET /api/v1/socai2/lake/events/{event_id}/material`，其他查询参数为`source_namespace`、`mapping_version`、`source_version`、`event_time`、`class_uid`；tenant由既有HTTP业务上下文提供。该接口的ocsf_json读取完整Kafka OCSF正文，raw_payload读取可选raw_data，来源/版本错配不回落latest。
- 首次结果沿`GET /api/v1/socai2/alerts/{alert_id}/artifacts/{artifact_id}`读取。新湖快照标记`fusion.first-result.v2`，数字规范化摘要兼容JSONB数值写法；旧v1保留原摘要和恢复语义。
- A/I初诊通过既有`.../analysis-tasks/{task_id}`读取，状态字段是`status`。本步登记为`accepted`，无attempt/Run；不能写成已完成分诊/诊断。

验收及未验边界见[4b当前批次](../../../docs/operations/evidence/lake-alert-receive-4b-20261119-03/README.md)。完整正文仍留受控存储，不因前端读取需要送入模型提示词。
