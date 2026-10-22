# v1 Kafka告警输入与融合输出

[返回入口](README.md)。正式已有告警从raw进入，生产者不写fused，不直接入PG。所有JSON例子均为接口说明，未向broker发送。

## 1. Topic清单

| Topic | 生产者→消费者 | 变量/消费组 | 输出意义与状态 |
| --- | --- | --- | --- |
| `socai2.alerts.raw` | 上游已有告警→Fusion | `KAFKA_TOPIC_ALERTS_RAW`；group=`socai2-fusion-consumer` | 正式输入；已部署并有真实交付证据 |
| `socai2.alerts.fused` | Fusion→Agents/独立后端读者 | `KAFKA_TOPIC_ALERTS_FUSED`；Agents group=`socai2-agents-v1-prod-20261022` | 融合并持久后的告警；v1生产Agents常驻已开启；不是调查结论topic |
| `socai2.alerts.fused.dlq` | Agents坏schema/失败→运维 | `KAFKA_TOPIC_ALERTS_FUSED_DLQ` | 带original和失败阶段；不当Fusion输入DLQ |
| `socai2.raw_events.v1` | 外部规范化事件→Fusion湖/UEBA | Fusion `KAFKA_TOPIC_RAW_EVENTS`；UEBA `KAFKA_INPUT_TOPIC`、group=`socai2.ueba.v1` | 历史取证/行为基线支路，非本轮上游告警合同 |
| `socai2.ueba.anomalies.v1` | UEBA→Fusion可选信号 | UEBA `KAFKA_OUTPUT_TOPIC`；Fusion `KAFKA_TOPIC_UEBA_ANOMALIES` | 基线异常；Fusion常驻加分开关仍false |

原资源记录raw/fused各3分区、Agents DLQ1分区，RF1/minISR1、保留7天。它是[创建时资源记录](../../../deploy/aisoc21/kafka-resources.json)，不是本轮实时broker快照；事件支路分区不从该旧文件推断。该文件早期“Agents group变量未接”已过时，现[main.py](../../../services/agents/app/main.py)已传group。

## 2. raw输入字段

完整例子见[raw-alert.json](examples/raw-alert.json)。正文为单个UTF-8 JSON object，不是`events:[...]`批量信封；一次消息一条已有告警。

| 字段 | 类型 | v1正式生产者约定 | 当前接收器事实 |
| --- | --- | --- | --- |
| schema_version | string | 固定`v1` | 缺省按v1，未知版本进入Fusion PG DLQ |
| identity_version | string | 显式`source-v1` | 缺省是旧`legacy-v1`；不设置会进入旧去重合同 |
| tenant_id | UUID string | 已建立且受控映射的真实租户 | 模型必填；正文UUID合法不等于租户已授权 |
| source_alert_id | UUID string | 稳定的上游告警UUID，重发保持 | source-v1必填；不能用source_event_ids或external_id替代 |
| id | UUID string | 建议等于上游告警UUID | 模型可缺省随机；Fusion随后改为canonical ID |
| source/title | string | 稳定来源、非空标题；标题按落库500字符以内 | RawAlert必填但Kafka模型没有HTTP入口的同等长度校验 |
| connector_id | UUID/null | 有真实连接器时传，且重投保持 | 参与身份指纹；null也参与，不能在重发时随意补换 |
| connector_type/external_id/rule_id/rule_name | string/null | 原厂类型、原finding ID、规则溯源 | 不替代source_alert_id；external_id不参与canonical指纹 |
| source_event_ids | string[] | 明确原事件引用，建议非空 | Kafka模型允许默认[]；它是来源事件，不是告警身份 |
| severity/status | enum string | severity=`info/low/medium/high/critical`；新告警status建议`new` | status模型枚举另含acknowledged/in_progress/resolved/suppressed/fused；PG新行仍固定new |
| event_time | ISO8601/null | 传带时区实际发生时间，推荐UTC `Z` | 可空；不要用落库时间冒充事件发生时间 |
| created_at | ISO8601 | 可传上游创建时间 | 模型缺省接收时间；与event_time不同 |
| src_ip/dst_ip/hostname/username/file_hash/domain/url | string/null | 从真实资料取值，缺失保持null/省略 | 不猜补实体；用户名字段是username |
| mitre_tactics/mitre_techniques/tags | string[] | 仅传上游实际提供的标签 | 技术知识映射不证明现场行为 |
| raw_event | object | 上游告警原始正文 | 当前范围内；不要求生产者做采集/规范化 |
| risk_score | number/null | 无评分时null/省略，明确0保留0 | 有限float，未统一强制0–1或0–100，双方约定来源尺度 |
| ocsf_class_uid | integer/null | 有对应分类再传 | 可空 |

这是对现有模型给出的**生产者约定**，其中“建议非空/带时区/长度”不是声称现有Kafka接收器已实现所有限制。[完整RawAlert](../../../services/fusion/app/models/alert.py)、[信封校验](../../../services/fusion/app/services/event_schema.py)

## 3. key、身份与投递确认

推荐Kafka key为`tenant_id`的UTF-8字节，沿现有测试producer约定。当前Fusion不读取key/headers进行tenant绑定，tenant取消息正文；fused发布也未设置key，不能承诺全链同实体固定分区顺序。

当前21的SSL验证服务端证书/主机名，不含已确认的broker客户端认证和Topic ACL。接入方须由受控生产者配置tenant/source映射及网络/写权限；不能用HTTP API key、Kafka key或正文tenant UUID替代这条边界。[transport实现](../../../services/fusion/app/core/kafka_security.py)

source-v1 canonical计算：

1. 将`identity_version, tenant_id, source, connector_id, source_alert_id`组成object，UUID规范化为字符串、空connector为JSON null。
2. 用Python `json.dumps(fields, sort_keys=True)`的默认转义和分隔符编码后SHA256。跨语言实现不能擅自改为紧凑JSON。
3. `uuid5(namespace=a15c0c00-0000-5568-a150-c000000a1e77, name=tenant_id+":"+fingerprint)`。

同tenant/source/connector/source_alert_id得到同canonical；不同上游告警ID各存一行。`id`、source_event_ids、external_id都不代替此组合。已存在同身份结果时优先恢复首次持久快照，不把修改正文后的重投解释成更新接口。精确算法见[deterministic_id/fingerprint](../../../services/fusion/app/models/alert.py)。

生产者保存broker返回的topic/partition/offset；这只是受理。Fusion实际顺序是校验/规范ID→恢复首次结果或处理→PG确认→fused发送确认→提交raw的offset+1。发布后提交失败可能再次产生同canonical fused，所以独立读者应幂等。发送超时先查原坐标/稳定身份，不新造上游UUID掩盖未知结果。

订阅方使用自己的group，例如`partner-backend-results-v1`，不要复用Fusion/Agents服务group抢分区。新group显式商定起点；服务源码常用latest，不等于可以重置旧group或跳过既有积压。本文不创建group或提交offset。

## 4. fused输出

完整例子见[fused-alert.json](examples/fused-alert.json)，仅为可能结构，分数和关联不是实测结论。

| 字段 | 类型/值 | 使用方法 |
| --- | --- | --- |
| id / alert_row_id / alert.id | canonical UUID | 正常交付三者一致，供查PG/API；上游ID在alert.source_alert_id |
| tenant_id / alert.tenant_id | UUID | 必须一致；后端按tenant+canonical关联 |
| persist_outcome | inserted / duplicate | 本次持久结果；不是分诊结论 |
| fusion_decision | new_alert / duplicate / correlated / new_incident | Fusion处理决定；duplicate不等于业务无效告警 |
| incident_id / duplicate_of | UUID/null | 聚合/重复引用；不等于人工Case UUID |
| alert | RawAlert object | 包含发生时间、原文、来源；id已规范化 |
| enrichments / narrative | object / string或null | 增强与解释；来源/可用性仍需核 |
| confidence_score / confidence_label / confidence_rationale | 0–1 / high-medium-low / array | 融合置信信息；PG/API confidence为整数0–100，不与ai_score或risk_score混算 |
| anomaly_score / priority_score / exploit_in_wild | number / number / bool | 原评分输出，PG/API priority不是无条件相同尺度 |
| fused_at / session_id / session_key_kind / originating_human | 时间/可空附加项 | 按实际存在读取，不据共享实体推定因果 |

[输出模型](../../../services/fusion/app/models/alert.py)、[确认持久与发布实现](../../../services/fusion/app/workers/consumer.py)。目前没有本轮已确认的“最终调查完成Kafka topic”；结论从Run/事件/工件API读取。

## 5. 失败输出

| 失败阶段 | 输出点 | 内容/确认语义 |
| --- | --- | --- |
| Fusion已解码但schema/模型不合法 | PG `aisoc_dead_letters` | topic/reason/schema_version/source_event_id/topic_partition/kafka_offset/payload_excerpt；excerpt最多2000字符，不是完整重放原文 |
| Fusion无法确认DLQ或PG持久/输出发布 | 原分区hold，保留offset | 不当作正常处理完成；查原坐标和服务日志 |
| Agents schema/triage/persist失败且耗尽处理 | `socai2.alerts.fused.dlq` | alert_id/canonical_alert_id/tenant/source/attempts/failure_stage/error/dead_lettered_at/original；DLQ确认后提交 |
| 预算hold或旧unknown | 原消息未确认/原记录保持 | 不自动塞入毒消息DLQ，不自动重发模型 |

非JSON坏字节可能在反序列化阶段报错，不能承诺都会生成上述PG DLQ。[Fusion DLQ](../../../services/fusion/app/services/dlq_sink.py)、[Agents DLQ与提交](../../../services/agents/app/workers/fused_alert_consumer.py)

## 6. 其他输入与HTTP测试入口

`raw_events.v1`要求规范化事件信封：`schema_version:v1`、UUID tenant、`ocsf_event` object；用于湖和UEBA。不要往共享此topic只发`features`评分object，因为Fusion也订阅且会拒绝缺失的ocsf_event。UEBA异常输出含entity_type/entity_id/anomaly_score/risk_level/features/detected_at；详见[完整输入输出样例](../../architecture/ueba.md)。

`POST /api/v1/alert-ingress`是测试辅助：把ExistingAlert转raw并回202及坐标，服务端还会代填tenant/source-v1字段；**直接Kafka没有代填**。`POST /api/v1/alerts/submit`直接入PG、绕过融合，不能用来验证正式Kafka链。HTTP存在及旧HTTP实证保留，不作为正式上游接入方案。
