# 02 Fusion：检测、关联与告警输出（M02）

> 用途：固定上游源码与历史证据分析（2026-10-20对齐）。本轮负责Fusion告警处理；旧工程下游合同及改造建议只作历史比较，不强制替换上游身份、状态或持久化实现。 当前职责见[范围](../../operations/alert-processing-scope.md)，阶段退出见[路线](../../operations/service-roadmap.md)，执行批次见[依赖计划](../../operations/dependency-migration-plan.md)。

返回[总入口](README.md)。本章分析参考 AiSOC；旧SOCAI下游合同仅作历史对照，见[下游迁移说明](/Users/lychee/Documents/project/SOCAI/docs/fusion/fused-alert-consumer-migration.md)。

<a id="m02"></a>

## 1. 职责与源码地图

| 环节 | 入口/核心文件 | 职责 |
| --- | --- | --- |
| 消费驱动 | [consumer.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/workers/consumer.py)：`FusionWorker` | 识别输入、检测、提升、融合、落库、发布和 offset 处理 |
| 模型 | [alert.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/models/alert.py) | RawAlert、FusedAlert、IncidentSummary、决策与置信度模型 |
| 输入校验 | [event_schema.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/event_schema.py) | 校验事件结构与必要元数据 |
| 检测/提升 | [detection_engine.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/detection_engine.py)、[windowed_detection.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/windowed_detection.py)、[promoter.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/promoter.py) | 普通事件规则、窗口检测、规范化事件到告警的转换 |
| 融合 | [fusion_engine.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/fusion_engine.py)：`process` | 去重、关联、增强、评分、解释 |
| 去重/关联 | [deduplicator.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/deduplicator.py)、[correlator.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/correlator.py) | Redis 指纹与关联索引，IncidentSummary 维护 |
| 持久化 | [alert_sink.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/alert_sink.py)：`persist` | Alert 写入、重复来源追踪、区分持久化结果 |
| 配置 | [config.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/core/config.py) | Topic、窗口、评分、RBA、外部服务与开关 |

## 2. 输入合同

输入分两类：规范化的普通活动事件，以及厂商已经判定为 finding 的告警。前者需要检测/提升，后者进入 RawAlert 路径。UEBA anomaly 消息用于更新信号缓存，不应误当告警。

| 字段组 | 代表字段 | 用途 |
| --- | --- | --- |
| 身份 | `id`、`tenant_id` | 租户隔离；处理前会重算 canonical Alert ID |
| 描述 | `source`、`title`、`description`、`severity` | 告警语义、评分和工作台展示 |
| 实体 | `src_ip`、`dst_ip`、`hostname`、`username`、`file_hash`、`domain`、`url` | 去重、关联、增强、调查定位 |
| 技术 | `mitre_tactics`、`mitre_techniques` | 关联键、解释与分析上下文 |
| 来源 | `connector_id/type`、`source_event_ids`、`ocsf_class_uid`、`rule_id/name`、`external_id` | 返回源系统、定位原日志和处置写回 |
| 时间/材料 | `event_time`、`created_at`、`raw_event`、`tags` | 时间范围、原材料和下游上下文 |

`source_event_ids` 与外部 finding ID 不可互换：前者是来源事件集合，后者用于定位源系统里的发现/案件。字符串标题不能替代连接器标识。

## 3. 正常处理路径

1. `_process_message` 检查输入类型、schema、租户等。普通事件可以记录 session、归档数据湖，并执行单事件/窗口检测。
2. `_fuse_and_persist` 追加实际来源事件 ID，再用 `RawAlert.deterministic_id()` 固定告警 ID。
3. `FusionEngine.process` 先检查指纹；命中立即返回 `DUPLICATE`，通常不再执行后续增强和评分。
4. 新指纹登记 Redis 后，按关联键查找 IncidentSummary；符合条件则合并，否则创建新摘要。
5. 非重复告警依次尝试 fuse-time enrichment、ML scoring、confidence、漏洞利用增强、UEBA、可选攻击链分组等；部分增强失败只记录错误并继续。
6. AlertSink 尝试持久化，返回明确结果；之后发布 Kafka 融合消息。消费者在处理函数正常返回后提交 offset。

这是源码顺序，不是跨 Redis、PG、Kafka 的单一事务。

## 4. 身份、去重与关联

### 4.1 去重指纹

指纹由 tenant、source、title、源/目的 IP、主机、用户、文件 hash、排序后的技术列表计算 SHA-256。**没有把发生时间、来源事件 ID 纳入指纹。** canonical ID 是 namespace 下的 UUID5，输入含 tenant 与该指纹。

Redis 指纹默认 TTL 为 300 秒。这个 TTL 不是数据库新发生分界：AlertSink 还会按 tenant + dedup_hash 判断已有行，canonical ID 也不随时间改变。因此不能把“超过 300 秒”解释为一定生成新的独立 Alert。移植时必须重新确认“真实新发生”和“重复投递”的身份规则。

`DEDUP_SIMILARITY_THRESHOLD` 虽有配置声明，本次检查的指纹 `Deduplicator` 路径只执行 Redis key 查找；不能据配置名宣称已实现语义近似去重。

### 4.2 关联键与摘要

主关联键为：

```text
tenant : 首个非空(src_ip, hostname, username, domain, unknown)
       : 首个 MITRE tactic 或 unknown
```

参考 Correlator 使用 Redis key → Incident ID，再加载 Redis 摘要；默认关联窗口 3,600 秒、每 Incident 最多 500 告警。合并更新数量、实体和技术集合。它不是 PostgreSQL 中带逐条 membership、版本和解释的 stingAISOC 合同。

另有可选攻击链分组增强，不能与上述主关联规则混写为一个算法。stingAISOC 已明确把丰富攻击链推理放在调查层，移植时应遵守该边界。

## 5. 评分与增强输出

| 输出 | 语义 | 不应如何使用 |
| --- | --- | --- |
| `anomaly_score` | 异常程度，模型/降级实现需结合 scorer 核对 | 不当恶意概率 |
| `priority_score` | 优先级排序信号 | 不替代工作台最终 priority 规则 |
| `confidence_score/label/rationale` | 检测置信度及各因素解释 | 不当调查最终结论或响应授权 |
| `enrichments` | 情报、漏洞、攻击链等附加信息 | 不把增强失败后的缺省值解释为安全 |
| `narrative` | 确定性融合解释 | 不等于模型调查报告 |
| session 字段 | 来源 session 与推导方式 | 没有 session 时不能虚构为单事件会话 |

MLScorer 被调用，不代表部署已加载训练产物或质量合格；需另外检查模型文件、加载日志和固定输入的实际结果。RBA 配置也不能单独证明其所有路径和验收目标已生效。

本版本 `MLScorer` 从未训练状态与进程内缓冲开始，未训练时直接使用严重度/实体等启发式。四类评分、RBA 实体累积和实际工作台 priority 的不同尺度详见 [M17](10-context-enrichment-risk.md#m17)；不要把字段名统一成一个“AI 风险分”。规则执行与 tenant overlay 详见 [M01/M16](11-detection-hunting-feedback.md)，CORE/独立 UEBA 区别见 [M13](09-ueba.md#m13)。

## 6. 持久化与消息合同

`PersistOutcome` 分为 `inserted`、`duplicate`、`unavailable`、`failed`。重复不新增告警行，但当前 sink 有来源事件补记逻辑；应检查实际 `source_event_ids`，不能沿用旧“重复完全无痕”的结论。

融合消息示意如下；仅表达关键字段，不是完整可提交样例：

```json
{
  "id": "canonical-alert-uuid",
  "tenant_id": "tenant-uuid",
  "incident_id": "correlation-summary-uuid-or-null",
  "fusion_decision": "new_incident",
  "alert": {"id": "canonical-alert-uuid", "source_event_ids": ["source-event-id"]},
  "alert_row_id": "sink-returned-alert-id",
  "persist_outcome": "inserted"
}
```

`_fuse_and_persist` 在持久化失败/不可用时也可继续发布带结果的消息。调用的是 `await producer.send(...)`，不能仅凭这一层 await 推断已等待 broker 最终确认；要结合返回 Future 的处理和客户端版本核对。没有发现该路径使用与 Alert 同事务的 PG Outbox。

消费循环正常返回才提交，但按当前循环结构，一条消息失败后继续处理同 partition 的更后消息，再提交更高 offset，仍可能越过前面的失败。因此“不在异常分支 commit”不等于连续可靠提交。DLQ 还需结合 `safe_record` 和所选 sink 的失败策略判断。

## 7. 最小充分测试卡

| 场景与输入 | 中间产品 | 最终应检查的值/关系 | 上游测试入口 |
| --- | --- | --- | --- |
| 合法/非法规范化事件 | 校验、检测/提升或 DLQ | 不合法输入不能伪造 Alert；拒绝可定位 topic/partition/offset | `test_event_schema.py`、`test_consumer_dlq.py` |
| 命中单事件与窗口规则 | 命中规则、实体、来源事件列表 | 仅命中时提升；组合事件引用完整 | `test_detection_engine.py`、`test_windowed_detection.py` |
| 同指纹重投 | 相同 canonical ID、dedup 决策、sink 结果 | 不新增 Alert；来源事件关系保留 | `test_alert_sink.py`、`test_alert_sink_issue_1244.py` |
| 同实体不同租户 | 关联 key 和摘要 | 不合并、ID 和来源互不串用 | `test_tenant_scope.py` |
| 真实 PG/Kafka 正常路径 | Alert 行、融合消息 | ID 一致、字段保真、API 可读；offset/发布另核 | golden pipeline |

上述单元测试的替身不能证明真实 Redis 并发、PG 约束或 Kafka 故障语义。20 已有 golden 正常路径证据；没有以此证明全部去重窗口、故障恢复或评分质量。

## 8. 移植与二次开发取舍

- 可采用：规范化事件与告警分流、来源字段贯穿、确定性解释、增强接口、具有业务断言的测试场景。
- 需改造：消息身份、持久事务、membership、Alert 版本和结果引用。stingAISOC 使用 `event_id` 投递身份与 `tenant+alert_id+alert_version` 业务身份，不能只改 topic 复用参考消费者。
- 不照搬：Redis 作为关联事实来源、时间无关指纹对真实发生的折叠、失败仍发布却被下游当持久成功、Fusion 中额外攻击链推理。
- 修改检测规则时，同时核对 promoter 字段、source links、告警文本、sink 和 UI；修改评分时分开验证确定性字段、模型加载和质量。
