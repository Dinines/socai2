# v1 表、数据落地与后端对接盘点

[总入口](README.md) · [连接配置](configuration.md) · [完整字段/主外键](table-fields.md) · [机器字典](data-catalog.json) · [两例实测回执](../../operations/service-v1-functional-20261022.md)

盘点范围：21上已部署的v1.0.0，生产租户 `f6a5c700-69b8-44fc-8238-609362fb1a9f`。两个新例子于2026-10-22 17:09—17:10通过正式raw Kafka投放；22:56:23（Asia/Shanghai）使用新进程、只读事务再次查询PG表/字段/约束/租户内计数和这两例的事件、工件关联及成本。数据来自真实持久结果，不是内存替身或仅函数返回。所有数量均限定该生产租户；不代表整个共享数据库，也不是未来不变的水位。

## 1. 后端首先接这些对象

| 业务对象 | 权威落地点 | 后端读取 | 关联键 / 注意 |
| --- | --- | --- | --- |
| 上游告警 | Kafka `socai2.alerts.raw` → PG `alerts` | `GET /api/v1/alerts/{canonical_id}` | `tenant_id + canonical Alert UUID`；source_alert_id是来源身份，不是PG主键 |
| 首次融合结果 | PG `alerts.enrichment_data.socai2_fusion.delivery_snapshot`；fused Kafka | Alert API、独立group消费fused | `alert_row_id/alert.id`是canonical；快照保留首次来源/融合结果，不随分诊状态变更重算 |
| Fusion关联事件 | Redis incident/correlation + PG告警中的incident_id引用 | fused / Alert中的Fusion材料 | Incident不是Case，也没有本次应接的PG incidents主表；Redis会过期 |
| 人工Case | PG `aisoc_cases` | Case API | `Case.alert_ids`为canonical UUID数组；当前自动路径不创建Case |
| 自动处理/调查Run | PG `investigation_runs` | `/api/v1/investigations`及`/{run_id}` | `tenant_id + run_id`；普通自动Run.raw_alert.id通常指canonical告警，case_id是字符串关联字段，不能盲JOIN Case |
| 第一次分诊结论 | `investigation_events.kind=triage_verdict`，同时投影`alerts.disposition/ai_*` | `/{run_id}/events`及Alert | 首次结论、模型置信度、是否自动关闭；不是后续调查最终结论 |
| 调查节点与工具 | `investigation_events` | events / explain / replay | `(tenant_id,run_id,seq)`去重；有摘要/preview，不保证每节点完整快照 |
| 调查最终/部分结果 | `graph_result`事件及同名JSON工件 | events、artifact详情 | `payload.completion`，再读JSON state；partial必须展示，不能用Run completed替代 |
| 报告正文 | `investigation_artifacts.kind=report_md`，正文`content` | `/{run_id}/artifacts/{artifact_id}` | 列表只给目录，详情JSON的content才是Markdown；自动关闭分支没有调查报告是正常的 |
| 模型交换 | `llm_prompt/llm_response`，graph内`graph_llm_exchanges` | artifact详情、llm_call事件 | 部分持久prompt副本截断；记录截断不能被称为实际模型请求截断 |
| 用量 | `aisoc_run_costs`、Run聚合、`graph_usage` | Run与成本API / 授权SQL | 成本表run_id/tenant_id为TEXT；合并前先统一类型；unpriced不能显示实际费用0 |

生产reader仅有查询权限。API在21 loopback18000、同网络`api:8000`，凭据发放/权限/tenant header详见[生产接入](production.md)。后端默认走API；直接SQL须另发受控只读身份，不复用runtime/owner或内部投影writer。

## 2. PG实际表清单与生产租户数据

下表是22:56只读盘点结果。生产总量包含发布canary＋本轮2条例子，不能把总量当成本轮新增。

| 表 | 租户内行数 | 本轮两例关联行数 | 由谁写 / 是否需要后端另供数据 |
| --- | ---: | ---: | --- |
| tenants | 1 | 复用1 | 已建生产租户，不再新建测试租户 |
| alerts | 3 | 2 | Fusion写告警、Agents投影首次分诊 |
| investigation_runs | 3 | 2 | Agents自动创建并关联告警 |
| investigation_events | 36 | 21（3＋18） | Agents写开始意图、分诊、graph、工具和用量 |
| investigation_artifacts | 35 | 21（7＋14） | Agents写正文/读取回执/报告，全部21份正文校验通过 |
| aisoc_run_costs | 5 | 3 | 例1分诊1行；例2分诊/调查2行，共8次回复、31788 tokens |
| socai2_triage_budget_reservations | 3 | 2 | 普通分诊各预留20000，均responded且已settled；不代表整条调查用量上限 |
| connectors | 0 | 0 | 直接Kafka合成输入未注册真实厂商connector；正式对接按来源配置 |
| alert_source_links | 0 | 0 | 需要有效vendor/外部finding引用；本例未提供，不造假来源行 |
| aisoc_cases | 0 | 0 | 需要人工Case输入；自动调查未建Case，不是落库失败 |
| aisoc_dead_letters | 0 | 0 | 本轮输入有效，没有Fusion失败行是预期；Agents DLQ在Kafka |
| assets / asset_vulnerabilities / alert_asset_correlations | 各0 | 不写 | 资产来源提供，告警流程不能替代CMDB/漏洞入库 |
| identity_privilege / identity_nodes / identity_edges | 各0 | 不写 | 权限/身份资料来源提供；身份上下文200/no_match不等于有HR资料 |
| aisoc_context_statements / aisoc_analyst_feedback | 各0 | 不写 | 组织事实/分析员处置来源提供；当前五类读取均200/no_match |
| aisoc_kb_documents | 0 | 不写 | KB导入后才有可消费知识；本轮未导入资料 |
| aisoc_tenant_skills / aisoc_tenant_skill_versions | 各0 | 不写 | 租户技能配置来源提供，本轮没有配置技能 |
| ueba_entity_baselines / ueba_anomalies / ueba_peer_groups | 各0 | 不写 | 规范化事件/基线计算链提供；只投RawAlert不会自动生成UEBA训练资料 |

上列25张表在本次PG元数据中均存在。普通Kafka认领复用`investigation_runs + seq=-1 triage_started`及预算表；没有独立`socai2_triage_deliveries`表，也不要求后端建一张同名表。表字段、空值与实际约束已另存[字段目录](table-fields.md)，并保留在[data-catalog.json](data-catalog.json)，未执行结构迁移或补造业务资料。

## 3. 两个例子的完整关联坐标

| 项目 | 例1：例行盘点 | 例2：未知脚本联网 |
| --- | --- | --- |
| raw Kafka | partition2 / offset45 | partition0 / offset38 |
| source_alert_id | `c3ac1e6d-980c-5077-8790-6fd698aeff2f` | `ca8fdfeb-d19d-5c6b-a84b-60a5d6f83a07` |
| canonical Alert | `bc625c39-56af-5403-a378-9bfb99c610d2` | `e5f593f0-b328-59c3-8238-379db33d8bfe` |
| Run | `4f5a0a57-050a-57a4-8443-504550fbc5fd` | `bdccd907-7f36-558f-8ed4-4be2e417b101` |
| 首次分诊/告警 | benign_true_positive /0.95，resolved，关闭时间非空 | needs_review /0.85，triaged，未关闭 |
| 调查 | 自动关闭后没有升级，未生成MD是预期 | 自动执行triage、enrichment、investigation；Deep6轮/10次工具调用；partial |
| PG事件 / 工件 | 3 / 7 | 18 / 14 |
| 用量 | 1次回复，2033 tokens | 7次回复，29755 tokens＝分诊2058＋调查27697 |
| Neo4j | Alert＋3个直接邻点/3关系 | Alert＋5个直接邻点/5关系 |
| Redis DB9 | dedup、delivery、incident均在观察时存在；恢复快照校验通过 | 同左；它们是TTL缓存，不承诺长期存在 |
| 后端读取 | Alert/Run/events/artifact目录GET均200 | 前述4项及MD正文GET均200 |

两个Run的21份工件都从PG读取了`content`正文，不只是列表；UTF-8字节数及SHA256与库内记录全部一致。22:56补查确认21份均有`event_id`关联。费用3行与Run总量吻合，8次回复均unpriced；无测量定价，不能将0USD解释为免费。

## 4. 调查每一步到底保存了什么

| 环节 | 已保存 | 本例证据 | 后端能否拿到完整原文 |
| --- | --- | --- | --- |
| Kafka输入/首次融合 | PG告警原文、source-v1身份、delivery_snapshot/fused | 两条canonical与输入身份匹配 | 本例已有；Broker保留期与Redis TTL另算 |
| 普通认领 | seq=-1 `triage_started` | 两Run均存在 | 开始意图，不证明模型已回复；首次events不传since才含-1 |
| 五类资料读取 | 5份`*_read`JSON工件，状态/来源/采用计数 | 两例均HTTP200、no_match | 有完整读取回执；没有匹配资料，不能声称真实知识已消费 |
| 首次模型分诊 | llm_call、prompt/response工件、triage_verdict | 两例回复完整，首次prompt副本截断 | 回复可回查；请求全文不能靠截断副本重建 |
| graph triage / enrichment / investigation | 各1个graph_step、最终聚合state | 例2 seq2/3/4，payload仅`{node}`，input/output_hash均null | **没有每节点完整独立输入/输出快照**；最终state不能替代逐节点快照 |
| Deep模型6轮 | graph_llm_exchanges，final graph_result内合并交换 | 6个回复完整；前2轮prompt完整，第3—6轮副本8000字符截断 | **不能完整重建后4轮实际请求** |
| 10次工具 | tool_call参数/名称、`result_preview` | 例2 seq10000—10009；preview最多200字符 | **不能保证完整工具返回**；graph_result.messages为空，不能假定另有全量ToolMessage归档 |
| attack_path节点 | 本次没有该节点完成事件 | 调查节点后外层token预算停止 | **未执行，不伪装成有该节点输出**；已有attack_path工件是上下文读取结果且无Case |
| 调查交付 | graph_result事件/JSON、graph_usage、3类链图、MD/HTML | 例2全部落库，report_md正文可读 | 聚合partial结果已留存；Run completed与graph/report running存在差异 |

结论：**主链和结果已落地；“每一步完整原文都已保存”不成立。** 本轮只做测试和交接盘点，不修改旧工件补造正文、不重放输入或提高预算掩盖问题。留存完善项沿原问题表后续评估。

## 5. 给后端的读取顺序与分页约束

1. 上游保存source身份及Kafka发送坐标；收到fused后保存tenant、canonical Alert、Fusion Incident。独立订阅group，不复用生产Agents group。
2. 用canonical Alert读取Alert，普通自动路径再查`GET /api/v1/investigations?case_id={canonical_alert_id}&limit=20`；已取得run_id后保存本地关联。不要将Incident/Alert UUID直接当Case UUID。
3. 首次读取`GET /api/v1/investigations/{run_id}/events`不传since；用triage_verdict区分是否自动关闭。关闭分支不要求graph或报告。
4. 未关闭且已开启升级时，等实际graph_result/工件；没有它只能记待获取/调查失败或未知，不能仅凭Run.status=completed宣称全调查完成。读取graph_result.payload.completion和JSON state，同时展示partial/缺源原因。
5. 列artifacts，再按实际kind/id取content。报告、原始交换、工具preview分别处理，不能把preview当全部证据。
6. 当前seq混用外层0—6和工具10000+，**不是严格按写入时间递增的游标**。工具高seq可先写，graph_result低seq后写；运行中只追max(seq)可能漏步骤。获得调查交付后，从不带since的首页重新分页直到结束，按(run_id,seq)去重补齐；时间线按ts展示、同时间再按seq。`since=-1`会排除-1开始事件。

SQL拷贝入口：[两个真实Run的只读查询](examples/production-two-examples.sql)。该脚本不写表、不建视图、不改变旧记录，包含输入身份、Run、步骤、正文/摘要、成本、graph完成语义的查法。已在21只读事务中执行9个SELECT全部成功。Backend不要直接写调查账本或由数据库状态反向伪造模型步骤。

## 6. 其他存储应不应该新增数据

| 存储 | 本例核对 | 对接要求 |
| --- | --- | --- |
| Kafka | 两条raw真实ack；fused生产组各处理1条，提交追平观察end | 保存坐标/幂等身份，fused不等于调查完成通知 |
| Redis DB9 | 精确key只读查到dedup/incident及验证过的delivery快照 | 只作缓存/运行状态，不能替代PG结果长期保存；本例TTL已记到回执 |
| Neo4j | 两个同tenant Alert的直接关系3条和5条真实读回 | 用于关联上下文；可达/技术映射不等于确认行为因果 |
| ClickHouse aisoc.raw_events | 本轮只投已有告警，未投规范化事件；工具可用零行已留存 | 不要求每条RawAlert都写历史事件表；历史事件由相应上游按独立合同提供 |
| OpenSearch / Qdrant | 本轮没有TI/知识导入，不制造IOC/向量行 | 它们是资料来源；不存在“每条告警必须各写一行”的合同 |
| UEBA / KB / 资产 / 身份 | 本生产tenant相关PG表当前0行，五类读取no_match | 接口可达不等于资料覆盖；需后端/上游按模块合同提供资料 |

当前例2仍有TI归因401、部分processing-context BufferError、process_tree缺父进程字段/network_connections查询失败、零行及六轮及软20k预算超限等真实边界，见[测试回执](../../operations/service-v1-functional-20261022.md)。这些不能改写成“所有模块正常”；对接交付成立的部分是输入、关联、自动执行、已有结果的持久化与读取。
