# 1F已有告警受理合同

本批范围：API/Fusion源码构建，已有告警→项目Kafka→Fusion→PG→API。Agents/Actions、采集、原始事件检测、模型和外部厂商均不启动。本文件定义编码与验收合同；实际结果与限制见[1F回执](1f-alert-chain.md)。

## HTTP受理

`POST /api/v1/alert-ingress`，Bearer认证并要求`alerts:write`。租户由认证主体确定；请求可省略tenant_id，指定其他租户则403。使用原RawAlert字段模型的来源副本，不替换Fusion的身份、指纹或状态算法。

必填：非空source/title、event_time、1—100个非空source_event_ids；severity为枚举，可用原默认medium。接受原RawAlert的实体、来源与材料字段；schema_version固定v1，未知字段拒绝。消息上限256KiB。不轮询厂商、不解析日志、不生成检测告警。

202回执包含input_id、认证tenant_id、按原算法计算的canonical_alert_id、来源ID、broker确认的topic/partition/offset及结果查询路径。202仅证明broker确认发布，`processing_confirmed=false`；最终结果通过`GET /api/v1/alerts/{canonical_alert_id}`及持久/融合消息核对。发布未确认返回503，可能已经被broker接收，不能自动重试或声称未发布。

同一告警重发遵循原版Fusion去重语义。不同event_time/source_event_ids但相同指纹是否被折叠，必须实测并记录，不能用本接口新造算法掩盖；若真实不同发生丢失，1F应记录该边界缺陷，不能整体标通过。

## 资源与启动

项目topic为socai2.alerts.raw/fused，Fusion组为socai2-fusion-consumer。新服务采用production配置，Kafka经21:19093 SSL listener、CA与IP验证，保留原production明文拒绝，不设明文豁免。PG启TLS并经21:5432访问aisoc；runtime=aisoc_app，迁移owner独立，仅迁移进程持有owner凭据。

API/Fusion首次只绑定21 loopback的18000/18003供受控测试，使用真实API key认证，无demo/匿名绕过。API其余后台worker关闭；现有禁用图/湖配置在startup生效，war-room同步可单独关闭。Fusion关闭event promotion、detection、windowed、lake、UEBA订阅、memory refresh及未接外部enrichment；只订阅项目raw告警。没有迁入或启用前端/Realtime。

## 本批直接验收

- 真实HTTP受理→raw消息坐标→Fusion决策/PG行/来源→API查询；结果ID和tenant一致。
- 未授权、缺权限、跨tenant、坏schema及非法输入拒绝；不发布被拒绝输入。
- 同投递重发与真实不同发生分别验证；不将不同发生错当重投。
- runtime数据库角色、服务实际订阅与后台任务状态可查；迁移REQUIRED/STRICT执行并核134文件ledger。
- 只用本批标记tenant、来源及API key；保留持久结果和缺陷现场，停用测试凭据。共享旧数据/卷不清理。

跨存储不是单事务；Kafka TLS没有增加topic ACL或客户身份认证。成功只覆盖本批数据链，不代表调查质量、真实响应、生产高可用或所有API路由均已验。
