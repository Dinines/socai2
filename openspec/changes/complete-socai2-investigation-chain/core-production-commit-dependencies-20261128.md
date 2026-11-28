# 核心生产依赖的提交完整性核对

本次只核规则映射、源置信度、ATT&CK 映射、事件成员统计、保存诊断读取及其直接接线；不修改生产代码、索引或服务，不重跑测试。正常 Case 的正式原生 HTTP 入口仍优先。Git 操作由统筹负责。

比较基线固定为本次开始时 `V1.1/HEAD = 6282e34db69eb0072044809b0418a9ccba3ae9fe`、本地 `main = 875ed7226e4e125d01bfc2bbc2d46ac0f5edd1fd`；当时 `origin/main` 指向同一本地对象。本次未 fetch，不据此声称远端现时状态。逐文件后像及基线指纹见[源码清单](../../../docs/operations/evidence/core-production-git-audit-20261128-01/source-manifest.json)。已有本机文件、既有部署和 Git 已提交分别判断。

## 最小依赖、共享改动与证据

| 已有设计/生产路径 | 冻结 HEAD/main 与工作树的关系 | 必须一起保留的源码及共享改动 | 现成独审/候选出处 |
| --- | --- | --- | --- |
| 原规则 ID/名称映射 | 映射主体已在 HEAD 和 main。`lake_alert_receiver.py` 当前另有未提交的标签投影，不能因此称整个规则映射未提交 | `adapt_alert` 从 `finding_info.analytic.uid/name` 取原值与来源路径，传入 `RawAlert`；`socai2_projection.project` 保存到材料 detection。既有 `alert-input-v1.json` 与规则投影直接测试也已在两基线 | [receiver 独审](../../../docs/operations/evidence/alert-rule-source-confidence-20261125-01/independent-receiver-review.json)、[原提交候选](../../../docs/operations/evidence/alert-rule-source-confidence-20261125-01/core-git-deploy-handoff.json) |
| 源置信度 | 本次核对的 `confidence.py`、`fusion_engine.py`、`socai2_projection.py`、`socai2_sink.py`、`alert_sink.py`、`models/alert.py` 当前与 HEAD/main 相同 | 原打分器、worker 配置启用接线、同材料判断和材料持久化需保留。源码已提交不等于某个运行 profile 已启用，后者不属于此 Git 结论 | [源置信度独审](../../../docs/operations/evidence/alert-confidence-core-20261125-01/independent-review.json) |
| 原始来源 ATT&CK 标签 | **必要两文件仍只在工作树**；与 HEAD/main 均不同 | `services/fusion/app/services/lake_ingress.py` 的 `_labels` 提取为 `project_labels`、增加 `finding_info.attacks` 并保持原根路径兼容；`lake_alert_receiver.py` 调用同一投影，向 RawAlert 传 tactics/techniques。不能只提交页面或模型输出读取而漏掉这两处上游生产映射 | [精确源码补丁](../../../docs/operations/evidence/alert-incident-tactics-example-20261126-01/core-candidate.patch)、[候选独审](../../../docs/operations/evidence/alert-incident-tactics-example-20261126-01/independent-candidate-review.json)、[发布独审出处](../../../docs/operations/evidence/alert-incident-tactics-example-20261126-01/independent-release-review.json) |
| 模型 ATT&CK 映射与读取 | 模型侧主体已在 HEAD/main | `alert_attck.py`、`alert_output_adapter.py`、`ai_stage_delivery.py`、`stage_results.py`、`stage_result_contracts.py` 及既有目录数据已在两基线。`page_reader.py` 中同轮映射读取也已在基线；该文件的当前未提交部分属于下述事件功能。`alert_basic_executor.py` 的新增改动由 S1/S2/S3 单独交付 | [已有源码发布审查](../../../docs/operations/evidence/alert-git-21-release-20261125-01/source-review.json)、[ATT&CK 提供者核对](../../../docs/operations/evidence/alert-incident-tactics-example-20261126-01/core-review.json) |
| 事件活跃成员、未知状态成员、检测源汇总（E27） | **核心新增字段及 SQL 聚合仍只在工作树** | `page_contracts.py::IncidentDerivedFields` 三个字段；`page_reader.py::view` 对当前成员集合的 count/filter/去重汇总。两文件与 E29 共用，不能只纳入后端响应类型或页面展示而漏 SQL | [成员汇总独审](../../../docs/operations/evidence/incident-member-aggregates-20261125-01/independent-review.json) |
| 保存的采用诊断与最近尝试分开读取（E29） | **核心和直接 HTTP 接线仍只在工作树** | `page_contracts.py` 的三个新视图；`page_reader.py` 的 `incident_detail/saved_diagnosis` 与详情分支；`investigation_http/external_routes/pages.py` 详情响应/用例接线；`investigation_http/contracts.py` 的 IncidentDetailView import/export。最后一文件还混有 Case story 和 TacticCount 改动，交统筹与相应模块合并核范围，不能当成纯 E29 整文件增量 | [E29 四文件候选](../../../docs/operations/evidence/incident-saved-diagnosis-read-20261126-01/http-candidate.json)、[独立源码审查](../../../docs/operations/evidence/incident-saved-diagnosis-read-20261126-01/independent-source-review.json)、[非测试逻辑独审](../../../docs/operations/evidence/incident-saved-diagnosis-read-20261126-01/independent-no-test-logic-review.json) |
| 事件列表同一 Run 读取复用（E23） | **`stage_reader.py` 的既有窄修正仍只在工作树** | `StageReader.page` 仅当列表项 Run ID 等于已读取 current Run 时复用同对象；其他 Run 仍各自读取。属于已保存诊断/历史读取的直接依赖，不能漏掉 | [E23 候选独审](../../../docs/operations/evidence/incident-diagnosis-live-20261125-01/independent-e23-candidate-review.json)、[发布后只读独审出处](../../../docs/operations/evidence/incident-diagnosis-live-20261125-01/independent-e23-release-read.json) |

ATT&CK 两个生产文件的当前后像均与既有 `core-candidate.json` 的候选源指纹相同。E29 四文件的逐项指纹比较也保存在本次清单；共享文件不靠旧批整文件 hash 追认新增改动。E27 的旧候选早于 E29，不能要求其旧整文件 hash 等于当前组合后像。

另有两个相邻交付项应由统筹归回各自已验范围，不混入 S1/S2/S3 的 17 文件部署包：

- 湖告警交付读取限制：`lake_alert_selection.py::validate_read_limits`、`lake_alert_delivery.py` 的配置/扫描接线、`workers/lake_alert_delivery.py::open_delivery` 三个文件仍只在工作树。它们解决独立交付扫描的实际配置接线，不是样本数量特判；既有出处为[read-limits 交接](../../../docs/operations/evidence/lake-delivery-read-limits-m0g-20261128-01/README.md)和[对应设计](lake-delivery-read-limits-20261128.md)。本次未重新读取该批运行值或追认完整线上验收。
- `incident-input-v1.json` 仍有单一后台字段过滤增量 `field_metadata.lake_ingress`。这是输入视图已有工作，与尚未实施的 I 输出精简不同；应对照[事件输入字段审计](incident-input-field-audit-20261127.md)及[原候选入口](../../../docs/operations/evidence/host-context-two-round-20261127-01/core-m0-engineering.json)归属，不因“仅一行”直接混包或当作已在 HEAD。

S1/S2/S3 已验文件沿既有精确清单交付。M0f 七文件已在本次冻结 HEAD，但本地 main 尚不含其增量；不能把“V1.1 已提交”写成“main 已同步”。两基线间本次核对范围内的差异即该组 M0f 文件。

## 测试源与实际实现边界

本次没有重跑测试。提交时应保留已有直接检查源码，尤其以下文件不在两份冻结基线中：`services/api/tests/test_socai2_incident_member_aggregates.py`、`test_socai2_incident_saved_diagnosis.py`，以及 `services/fusion/tests/test_lake_alert_receiver.py`、`test_lake_delivery_read_limits.py`。后者的 receiver 检查还引用 `.lake_ingress_cases` 和 `.test_lake_alert_selection`，须一并核现成测试源依赖。测试替身只存在测试目录，不可把已有替身检查写成真实模型或数据库验收。

对上表生产改动逐段核对后，未发现这些增量按某个 Case/告警 ID、主机名、样本标题或 `lyc` 前缀分支返回伪造业务结论。证据范围限于所列路径和改动，不能推成全仓结论：

- 规则与来源标签按字段路径和类型取原值，缺少/类型不符保留问题或拒绝；没有为页面补固定战术或从名字猜 ATT&CK ID。
- `FusedAlert` 确有原有的 0.5 数值默认值，但同时默认 `confidence_status=unknown`。材料投影仅在同材料且状态为 computed 时输出评分；unknown/disabled/failed 输出对应状态及空评分。不能把类默认值本身当作“生产已经填了有效分数”，也不能据此泛称别的消费者没有问题。
- `alert_attck.receive` 校验目录、战术技术组合和行为引用，独立保存 invalid/missing 单元；没有把无效映射改成有效映射。该可选映射与主体分析交付分开处理，不是将原失败回复重写为成功。
- E27 对真实当前成员集合做 SQL 汇总；E29 从正式采用指针读取已保存诊断，同时单独读取最近尝试的原状态。它没有拿最近失败 Run 的工件拼成采用诊断；未验来源保持空态。
- E23 只复用同一 Run 的已读对象，仍通过同一个 `entry` 保存和返回原 Run 状态及有效性条件，不回填失败为 completed。

本表用于避免漏交生产依赖，不扩大服务端职责至新采集、原始检测、整个平台改造或全仓审计。平台普通 POST 缺口与正式原生单笔验证仍按[§13](model-failure-contract-audit-20261128.md#13-s1s2s3-限定发布与单笔-case-验证安排)分别收口。
