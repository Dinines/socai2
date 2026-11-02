# 字段对齐第2批：告警身份、归并依据与提升开关

2026-11-02。接续[第1批](field-alignment-fix1-20261101.md)和[8批修复顺序](field-alignment-impact-and-repair-plan-20261101.md)。本批完成 S1-03/08、S3-01/02 的本地修改、必要验证和基线比对；尚未部署或真实数据库验收。基线提交仍为 `b400fd0`，第1、2批修改均在工作区，未再次提交或推送。

## 处理逻辑

| 问题 | 本批处理 | 保留的边界 |
| --- | --- | --- |
| S1-03 不同发生被旧内容指纹折叠 | 提升、单事件检测、窗口检测在收到明确事件 ID 时使用 `event-v1`。指纹包含租户、连接器、来源、事件 ID、生成路径及规则 ID；同源重投稳定，不同事件/连接器/规则/路径保持独立。事件 ID 沿第1批统一优先级和UUID表示 | 不用时间或标题猜身份；没有来源 ID 的输入继续原 legacy 行为，不列补采任务。窗口身份指本次触发事件，不声称已经补齐窗口内所有参与事件（S1-06仍待） |
| S3-01 不同类型对象同名误归并 | 键使用 `entity-v2` 命名空间及类型、值、战术的JSON编码，防止主机/账号同名和分隔符碰撞。没有主对象时以本告警身份隔离 | 主对象顺序仍为源IP→主机→账号→域名；仍取首个战术，仍按处理时间索引TTL归并；不引入全实体关系推断或事件时间窗口 |
| S3-02 真实归并依据不完整 | Correlator返回当次结构化依据，经 FusedAlert、首次快照及PG告警JSON保存。事件成员与告警调查上下文接口读回同一保存值 | 旧记录没有依据返回空，不从今天的成员字段重构过去的决策。Case模型消费这些字段不在本批，仍属后续投影工作 |
| S1-08 提升开关仅控制订阅 | 实际提升分支检查 `event_promotion_enabled`；关闭后仍执行已有写湖、单事件检测和窗口检测 | 不改变检测开关、检测命中规则、输入校验或厂商告警入口 |

### 历史兼容

- `legacy-v1` 和 `source-v1` 的指纹/UUID算法保持；API镜像模型已与Fusion模型逐字节同步。现有HTTP告警入口仍由服务端选择这两个既有版本，并清空调用方给出的内部事件身份字段，不将入口切到 `event-v1`。
- 新事件身份未命中PG时，有限查询旧指纹候选。仅当旧快照有效、连接器/来源/规则相符、首次快照实际记录同一来源事件，且原生成路径可由既有构造格式辨认时，复用旧身份和首次结果。**不把PG后来追加的来源引用当首份原文，也不把同标题当同一次发生。**
- 旧生成路径缺少独立字段：规则/窗口依据既有 `detection:` 来源和对应固定描述前缀区分；无法证明时不猜。匹配限于可定位的旧指纹候选，不声称能识别标题或实体已变化的所有历史重投。旧行无快照时不能据其内容证明是同一事件；损坏快照沿既有拒绝规则处理。
- 归并时不读取旧无类型Redis索引，新旧键隔离；旧PG事件和冻结Run不重组。上线切换后新成员可能进入新的事件，而不是续接旧无类型窗口。已经确认属于旧首份事件的重投仍读回原事件ID。
- 旧快照可缺少新增可选字段，原存储字节保持。没有批量回填、修改旧报告或恢复此前被折叠掉的原文。

## 数据表与接口

本批**无DDL、无迁移、无新增表**。复用 `alerts.enrichment_data.socai2_fusion`：

| JSON路径 | 内容 |
| --- | --- |
| `identity.version` | 新生成路径可为 `event-v1`；既有版本保持 |
| `identity.event_id` / `identity.origin` | 收到的来源事件编号及 promotion/rule/window；不伪造厂商 `source_alert_id` |
| `correlation_basis` | policy_version、entity_type/value、tactic、correlation_key、window_seconds、window_basis、max_alerts、decision、reason、decided_at |
| `delivery_snapshot.fused.correlation_basis` | 同一首次决策的冻结副本，与原文及其他首次结果共同校验 |

`window_basis=processing_time_index_ttl` 明示现有窗口含义。`reason` 区分无索引、摘要缺失、成员达到上限、命中归并和已有成员；不是检测规则命中理由，也不是攻击因果。

新增可选读取：事件GET的 `members[].correlation_basis`，告警 `investigation-context` 的 `correlation_basis`。普通查看不新增写入；历史无记录为null。其余页面字段、列表、管理及Case评分投影本批未修。

主要代码：[身份模型](../../services/fusion/app/models/alert.py)、[事件身份提取](../../services/fusion/app/services/event_schema.py)、[三入口之一：提升](../../services/fusion/app/services/promoter.py)、[归并执行](../../services/fusion/app/services/correlator.py)、[首次材料兼容](../../services/fusion/app/services/delivery_recovery.py)、[消费分支](../../services/fusion/app/workers/consumer.py)、[PG参数](../../services/fusion/app/services/alert_sink.py)、[事件读回](../../services/api/app/investigation_v2/incident_reader.py)。

## 验证与前后比对

最新 **66个相关测试用例（含参数场景）通过**：Fusion56、事件/告警上下文API3、HTTP告警入口7。新增测试19个参数场景/用例，其中Fusion17、API2。首次Fusion收集因新测试导入路径不正确而停止，未执行用例；修为 `tests.test_process_delivery` 后56项执行通过。API3项首过，后续模型同步及入口清理只执行受影响的7项；不重跑已通过且未变的用例。日志保留原错误与后续结果。已有 `datetime.utcnow()` 弃用警告未在本批扩改。

验证使用真实构造器、worker、归并和快照代码，PG/Redis/Kafka/ML边界均为替身。覆盖三个入口的独立发生/重投、不同连接器、规则及生成路径、缺失身份保留、metadata.uid；旧快照兼容和其他来源不误复用；对象类型/未知对象/分隔符/旧索引隔离；实际依据进入INSERT参数和快照、重投不重算；成员上限与摘要缺失；提升开关两种状态；接口读回及旧记录空值。

[比较脚本](../operations/evidence/fusion-field-fix2-20261102/compare_baseline.py)读取 `b400fd0` 源码并对相同合成输入执行，见[结果](../operations/evidence/fusion-field-fix2-20261102/before-after.json)：

| 场景 | 基线 | 当前 |
| --- | --- | --- |
| 相同正文、不同事件ID，三个生成入口 | 每个入口的两次发生都得到同一告警ID | 各自得到两个告警ID；重投仍得到原ID |
| 同名主机和账号 | 同一个归并键 | 不同键 |
| 两个无对象的不同告警 | 同一个unknown键 | 按告警身份分开 |
| 关闭提升、两类检测均命中 | 处理3条告警，湖写入函数1次 | 仅两条检测告警，湖写入函数仍1次 |
| 既有legacy/source身份 | 原UUID | 相同UUID |

上述是本地处理与参数验证，不是真实PG/Redis/Kafka/湖写入；没有新Run、模型调用或部署。Ruff语法/未定义引用检查（19个业务/测试文件）及diff空白检查通过；API/Fusion镜像模型内容一致。完整文件指纹、验证范围见[回执](../operations/fusion-field-fix2-20261102.json)。

## 后续

第1、2批本地完成；下一第3批处理已收到的时间、实体、规则/战术、参与事件与完整性、评分计算状态，以及湖动作/会话、hash算法、raw截断和查询副本。第4—8批继续原顺序；用户16项决定不重问。报告修复仍暂停，r13不重试，5.3仍未完成。第一批回执保持当时指纹；本批同时修改的event_schema/promoter/consumer以本批新指纹为准，不覆盖旧证据。
