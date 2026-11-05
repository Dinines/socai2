# Fusion 新表写入：字段、事务与 Case 衔接

2026-11-04。新写入器已接入 Fusion 的可选持久化入口，使用原 `socai2` 29表/458列，没有本批DDL。`AISOC_ALERT_STORE_SCHEMA` 默认 `public`，显式选择 `socai2` 才使用新写入器；本批未改环境、未部署、未切换生产，不双写、不在失败后回退旧表。页面未改，Fusion前置输入问题仍排除。

本批已完成告警、不可变材料、来源引用、对象、事件、事件成员与首次投递快照的原子写入。**没有生成告警分诊或事件诊断**：这两类结果需要A/I自己的真实执行与产物，不能用Fusion归并说明填充。Case仍手动启动完整基础调查，范围变化与单活跃规则保持。

## 1. 实际流程

1. 现有worker规范化来源ID、确定告警身份；通过所选sink查PG首次结果。已有首次快照时按原结果恢复，没有证据的旧行保持阻断，不凭当前输入补造快照。
2. 首次Fusion结果通过原身份/hash/1MiB上限校验。写入器核租户及连接器归属，锁规范告警行；告警、首次快照、材料v1、来源/对象、事件和成员全部在同一PG事务中保存，COMMIT成功后才返回durable。
3. worker再从所选PG库表确认首次快照后发布。缓存丢失后重投仍读取首次结果，不重新归并。PG失败或延期外键提交失败均不发布。
4. 相同输入重投不增加材料、关系或业务时间；`id/created_at`这两个可重新生成的接收字段不参与材料身份。不同收到材料按内容hash生成新版本，首次快照和旧材料不改。旧版本重投不回退latest指针。
5. 当前告警的标题、标签、严重程度、事件时间等沿首次规范行保留，人工管理值不被重投覆盖；新来源全文进入新材料，`latest_material_id/source_updated_at`推进，已知发生时间更新first/last，实际成员所在事件刷新业务时间。人工移动后的事件关系不被Fusion改回。
6. Case从新表已有告警建案，C1冻结实际材料ID、对象/来源及事件成员关系；C4按冻结材料读OCSF进程/网络语义。原文不塞进C1背景摘要，不提高原8192/2048字节模型视图预算。

单条写入锁顺序为告警→事件，批量逐条事务；后续事件管理/移动服务需与此顺序协调。新对象只做明确字段投影及精确字符串身份，不猜厂商、哈希算法、因果链或真实受影响资产。不同来源的对象以连接器ID或来源名隔离。

## 2. RawAlert 全部33字段对照

所有收到的RawAlert字段完整保存在 `alert_materials.raw_json`，原日志位于其中的 `raw_event`；下表列出额外结构化出口及语义。物理 `raw_text` 保存明确的OCSF raw_data文本，`ocsf_json`供必要语义读取。OCSF与信封activity都存在时，投影额外记录信封块和来源标记，原始两份值仍完整保存在raw_json，冲突不择值覆盖。

| 项 | 输入字段 | 新表/读取位置 | 处理与限制 |
| --- | --- | --- | --- |
| R01 | `id` | alerts.id；raw_json.id | 规范告警ID由既有指纹规则确定；收到值留原件 |
| R02 | `tenant_id` | 各表tenant_id；RLS | 每事务设置本地租户，关联限定同租户 |
| R03 | `identity_version` | raw_json；首次快照 | 保legacy/source/event版本，不改既有身份规则 |
| R04 | `source_alert_id` | alerts.source_alert_id | 接入来源编号，与厂商编号分开 |
| R05 | `identity_event_id` | raw_json；首次快照 | 参与既有event-v1指纹，来源事件关系另存 |
| R06 | `identity_origin` | raw_json；首次快照 | 保promotion/rule/window，不从标题猜 |
| R07 | `source` | raw_json；objects.source_type/namespace | 没连接器ID时以明确来源名隔离对象，不能当原厂 |
| R08 | `title` | alerts.title；raw_json.title | 首次业务行保留；重投不覆盖人工标题，无500字符静默裁剪 |
| R09 | `description` | alerts.description；raw_json.description | 首次描述与后来材料版本分开 |
| R10 | `severity` | alerts.severity/severity_raw；raw_json | 使用收到的规范枚举，不能恢复上游未传的原生枚举；重投不覆盖人工等级 |
| R11 | `status` | raw_json.status | 来源状态不冒充本产品处理状态；新告警handling_status=new |
| R12 | `src_ip` | alert_objects；raw_json | 类型ip、角色both，有来源路径，不认定恶意IOC |
| R13 | `dst_ip` | alert_objects；raw_json | 同上，保双端点；相同IP不同字段保出处 |
| R14 | `hostname` | alert_objects；raw_json | 类型host、角色entity |
| R15 | `username` | alert_objects；raw_json | 类型user；与同名host的对象键分开 |
| R16 | `file_hash` | alert_objects；raw_json | 类型hash；仅OCSF明确同值algorithm时写算法，不凭长度认SHA256 |
| R17 | `domain` | alert_objects；raw_json | 原值精确匹配，不自动去点/变更大小写 |
| R18 | `url` | alert_objects；raw_json | 保完整值及来源路径 |
| R19 | `mitre_tactics` | materials.detection.tactics | 来源检测标签，不是已证实战术 |
| R20 | `mitre_techniques` | materials.detection.techniques | 同上，不按标题补标签 |
| R21 | `raw_event` | raw_json.raw_event；ocsf_json/raw_text | 原文完整；额外OCSF主机/IP/用户明确值也可进入对象索引 |
| R22 | `field_metadata` | raw_json.field_metadata；source_scope | 保原字段出处/窗口/缺失/截断信息，候选窗口不写成因果链 |
| R23 | `tags` | 首次alerts.tags；raw_json.tags | 后续来源标签留材料，重投不覆盖人工标签 |
| R24 | `risk_score` | raw_json.risk_score | 0与未知保留；源风险不直接替代本产品优先级或分诊评分 |
| R25 | `connector_id` | alerts.connector_id | 必须能证明public.connectors同租户归属 |
| R26 | `connector_type` | alerts.connector_type | 接入平台类型不填入original_vendor |
| R27 | `source_event_ids` | alert_source_refs；raw_json完整数组 | 关系去重最多200，保准确原数组下标；原数组不裁剪，scope记数量/截断 |
| R28 | `ocsf_class_uid` | materials.detection.ocsf_class_uid；原OCSF | 类别值留原义，不能跨类别查证后当成同一事实 |
| R29 | `rule_id` | materials.detection.rule_id | 有就传，不自动读取规则全文 |
| R30 | `rule_name` | materials.detection.rule_name | 有就传，未知不从告警标题补 |
| R31 | `external_id` | alerts.vendor_alert_id | 厂商告警编号，不替代接入来源编号 |
| R32 | `created_at` | raw_json.created_at | 接收模型时间留原值；不当告警发生时间，不参与重投材料身份 |
| R33 | `event_time` | alerts.event_time/source、first_seen_at/last_seen_at；raw_json | 未知为NULL，不用NOW；已知时间统一UTC，初始代表时间与后续观察范围分开 |

original_vendor只读取收到原文中明确的`original_vendor/deviceVendor`，未知NULL，不使用Splunk/connector_type或metadata.product猜原厂。字段源本来不完整，只记输入限制；本批不追查上游。

## 3. FusedAlert 全部20字段对照

首次FusedAlert完整保存在固定ID的 `artifacts(kind=source_snapshot, schema_version=fusion.first-result.v1)`。它不属于调查Run；每次投递恢复只认这一份。工件超过Case现有128KiB内容读取上限时不能称已可由页面全文加载，后续告警工件API需沿留存合同处理。

| 项 | 输入字段 | 新表/读取位置 | 处理与限制 |
| --- | --- | --- | --- |
| F01 | `id` | alerts.id；首次快照 | 必须匹配规范身份 |
| F02 | `tenant_id` | 各表tenant_id；首次快照 | 必须与RawAlert租户一致 |
| F03 | `incident_id` | incidents.id、incident_alerts.incident_id | 初始关系事务保存；人工后续移动不被重投覆盖 |
| F04 | `fusion_decision` | 首次快照 | 实际归并决定，不当业务处理状态；无可证明结果的duplicate拒绝冒充durable |
| F05 | `duplicate_of` | 首次快照 | 保原值，不制造新的告警或Case关系 |
| F06 | `alert` | 首次快照＋材料版本 | 首次模型保原样，后来输入另建版本 |
| F07 | `correlation_basis` | incident_alerts.correlation_basis＋首次快照原结构 | 显式对象键/方法/理由/强度与原件引用；processing TTL不伪造成真实活动窗口 |
| F08 | `enrichments` | 首次快照原结构 | 保原资产/背景等返回，不把任意嵌套内容直接塞模型；按类型消费仍需后续适配 |
| F09 | `anomaly_score` | 首次快照 | 既有模型无计算状态，默认0不能当已确认正常 |
| F10 | `priority_score` | 首次快照 | 同样缺可核计算状态，不直接写available优先级；本批不伪造评分来源 |
| F11 | `exploit_in_wild` | 首次快照 | 保已有检测/富化标记，不当独立攻击事实 |
| F12 | `confidence_label` | materials.detection.confidence_label | 只有computed对应available时提供标签，其他NULL |
| F13 | `confidence_score` | materials.detection.confidence_value | 明确computed才从0..1换算0..100；computed=0有效，未知不补50 |
| F14 | `confidence_rationale` | detection.confidence_rationale；首次快照结构 | 原factor/label/value/contribution/weight用JSON字符串完整保留到原字符串数组合同，首快照仍是结构化数组 |
| F15 | `confidence_status` | detection.confidence_state | computed→available、unknown→not_computed，disabled/failed原义保留；新输入未经重算不套旧评分 |
| F16 | `narrative` | 首次快照 | Fusion确定性说明，不冒充事件诊断或Case结论 |
| F17 | `session_id` | materials.enrichment的fusion_session；首次快照 | 有同份输入依据才投影，不从Case范围猜会话 |
| F18 | `session_key_kind` | 同上 | 保厂商/派生等原分组口径 |
| F19 | `originating_human` | 同上 | 来源身份，不自动认作本产品负责人 |
| F20 | `fused_at` | 首次快照 | 实际Fusion时间，物理received/ingested使用事务接收时钟，不混作发生时间 |

材料不是首次输入时，原评分/会话不能被套到新原文上；新材料显式not_computed，仍可按first_fusion_result_reference查看首次来源。原始评分、富化和叙述不丢，但没有相应读取适配就不声称页面已能直接展示。

## 4. 关系与页面支撑

| 数据条件 | 本批可用基础 | 尚待 |
| --- | --- | --- |
| 告警与事件成员 | incident_alerts有持久化单归属及原归并依据，外键/RLS/事务验证 | 新告警/事件页面DTO，管理动作由专门实现接入 |
| 事件标题、状态、负责人 | 独立incidents行；初始标题明确由首次告警生成“关联事件 · 标题”，不是模型诊断；状态new、负责人未分配 | 后续管理写入、级联及活动目标合同 |
| 事件等级 | 从当前成员alerts.severity派生最高值；人工severity_override字段保持 | 读取聚合/人工覆盖接口，不能将首次Fusion严重程度写入人工覆盖 |
| 事件最早/最近活动 | 当前成员event_time可派生min/max；未知不造时间 | 页面聚合读取，不新增冗余计数/时间表 |
| 最近业务更新 | 真正新增材料或成员刷新告警/事件时钟；完全相同重投不刷新 | 其他管理writer同样遵守业务时间合同 |
| 告警分诊、解释 | 对应表/Run/工件合同已有；本批不创建假结果 | A流程的真实执行、结果/解释写入和当前指针 |
| 事件诊断 | incident_diagnoses结构已有，C1能发现真实事件成员；无诊断明确不可用 | I流程冻结成员、消费A结果、真实执行及诊断产物；不能用归并narrative替代 |
| Case输入 | 本批真实Fusion入库→Case创建→C1冻结→原文/C4语义→有界模型视图已验证 | Case显式关联事件/移动事务、外部来源/H/Q；生产读写迁移 |

## 5. 具体例子

**第一次与重投。** A1来自接入编号S1/厂商编号V1，Fusion归到I1。一次提交保存A1、M1、2个来源引用、对象边、I1成员和首次快照。缓存清空后再次收到同一A1，直接恢复PG首结果；M1和业务时间均不变。

**追加材料。** A1后来收到一份新原文和更晚发生时间，新增M2并推进latest，first/last覆盖已知时间。M1/首次快照不变，人工设置的completed/false_positive、标题、标签、等级保持；旧M1重投不回退latest。M2不使用M1的置信度冒充新计算。

**两个同名对象。** hostname与username均为`shared-host`，对象分别是host和user，不合成一个身份；OCSF另有目标主机/IP时分别索引，完整进程PID/命令行留在冻结原文中供C4读取。

**窗口候选。** 收到202个唯一来源ID，关系表保前200并标截断，原数组仍全量在材料中。sequence_candidate表示候选，不表示已经证实攻击顺序。对应来源路径使用原数组实际下标，重复ID不会让引用指向错误项。

## 6. 验证与下一段

9项新writer/worker检查＋1项真实Fusion材料到Case桥接检查的最新结果通过；另10项旧写入/投递本地回归通过。PG沿21现有独立合成库；Redis/Kafka发送和Fusion引擎为明确替身，没有真实模型、湖或厂商调用。桥接首导入用了错误函数名，0检查执行，角色/隧道清理后修正并通过；记录保留。原8项首轮通过，隔离原文并补端点/活动投影后定向复核3项及桥接；补核事件时间不倒退时遇到先前夹具的固定source_incident_id冲突，改为独立编号后定向通过，原失败保留。未变项复用，非一次首过。[完整回执](../operations/socai2-fusion-ingestion-20261104.json)保源码指纹、PG批次和旧路径回归。

下一段优先A告警基本查询/分诊产物、I事件诊断与新表写入链，接真实来源和评分状态；同时按数据合同补新告警/事件读取出口，再显式Case事件关系、人工/AI业务。已有消费者及处置回写仍依赖public.alerts，本配置**不能单独在生产启用**，需与读端和下游消费显式切换；旧历史不隐式迁移、不长期双写两套真值。报告修复继续暂停、r13不重试、5.3未完成。
