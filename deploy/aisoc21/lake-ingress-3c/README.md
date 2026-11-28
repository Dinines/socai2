# 湖3c：裸OCSF完整保存入口

本目录提供待统一交付的配置示例。3c已完成适配及实际ClickHouse保存/读回，[3d消费接线](../lake-consumer-3d/README.md)随后已通过隔离Kafka/持久确认验证；正式库/服务未更新。对方最终发送目标仍见[SpiritHub交接](../../../docs/integration/spirithub-18024-handoff-20261118.md)，本目录的`lyc`来源和Topic仅用于合成示例，不是替换对方目标的要求。

`ingress.example.json`绑定database、tenant_id、source_namespace、connector_type、kafka_cluster、topics、mapping_version、ocsf_version；正文中的租户/来源字段不控制路由。`storage_policy_file`相对入站profile文件目录解析，必须指向匹配的3b存储策略。漏配置、不同数据库、未授权Topic或不支持的映射版本均拒绝，不选择另一个环境。

复制为部署目录中的`ingress.json`及`storage.json`时，同时将`storage_policy_file`改为`storage.json`。按已选部署环境填写实际库/租户/来源/Topic，保持新映射400天入湖口径。`CLICKHOUSE_DATABASE`必须相同；连接及凭据继续使用Fusion已有受控配置文件，示例不含凭据。`compose.override.yml`由选定的compose配置提供`LAKE_INGRESS_PROFILE_DIR`；该层只挂载profile，不启动订阅、promotion、检测或模型。

内部使用入口为`LakeWriter.write_ocsf_batch([(原始bytes或None, KafkaPosition(...)), ...])`：

- profile通过`IngressProfile.load`加载并传给LakeWriter；Fusion启动器已接`AISOC_LAKE_INGRESS_PROFILE_FILE`，未配置时原信封入口维持原状，新裸入口拒绝调用。
- 适配后按具名61列INSERT，ingest_time省略以使用数据库本次写入时间；显式`async_insert=0`，原生INSERT确认后返回保存回执。错误不自动重试，可能已执行时回报unknown，未建立写入器客户端则not_attempted。回执包含湖身份、版本、解析状态、Kafka位置及字段问题路径，不携带正文，也不替代Kafka位点确认。
- 摘要区分整数与小数/指数写法，保持与严格整数投影一致；同类小数1.00与1e0仍规范化为同一值，避免同ID对应不同时间/class排序键。此规则在尚未发布的v1中已修正，旧合成批次不重写。
- 有效对象的ocsf_json保留收到的完整UTF-8文本，raw_data完整进入raw_payload；不调用preview截断，不添加内部元数据覆盖正文。非对象/非法JSON保留原文本；非法UTF-8用base64配合parse_status可逆保存；tombstone单独标记。
- 只做严格JSON和约定公共投影检查，不宣称完整OCSF规范校验。device/src/dst分开；class0不从partial恢复成目标class；显式null/非法祖先不触发回填。legacy activity/session扩展不推断，新原件中仍保留。
- 原`write_event`信封入口及其既有告警/材料身份保持，包括原缓冲和截断行为。本步完整保存保证仅覆盖新裸入口，旧入口不因此被描述为已完成持久确认改造。

部署前仍须完成[3b](../lake-storage-3b/README.md)迁移及实际清理进程同版配置，再同版启用3d原字节消费、批次调度和各分区连续位点。3d已实现结果未知只读核对、取消等待native结束及停止时保留未确认范围；本方法本身没有自动恢复或Kafka提交逻辑。本轮[验证回执](../../../docs/operations/evidence/lake-ingress-3c-20261119-01/README.md)区分程序检查、原生库流程及尚未接线范围。
