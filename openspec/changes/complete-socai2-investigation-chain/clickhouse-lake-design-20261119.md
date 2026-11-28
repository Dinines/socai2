# ClickHouse 日志湖表结构与实施规划

状态：2026-11-19湖3a–3f合同、迁移、完整保存、持久确认、真实固定范围聚合验收及基本查询已完成，均有隔离库直接验证。原48列保持，新增14列（含device_ip）见[机器字典](lake-ingress-contract-v1.json)，005与新装DDL由同一结构定义/profile生成。[3b回执](../../../docs/operations/evidence/lake-schema-3b-20261119-01/README.md)包含48项定向检查和真实测试库7组验证；新接入每次入湖400天/重试刷新已实测，旧映射规则保持。[3c回执](../../../docs/operations/evidence/lake-ingress-3c-20261119-01/README.md)记录81项程序检查和原生库8组+1项边界通过；[3d回执](../../../docs/operations/evidence/lake-consumer-3d-20261119-01/README.md)记录91项定向检查及真实Kafka/ClickHouse三组通过，[3e回执](../../../docs/operations/evidence/lake-replay-3e-20261119-01/README.md)记录30项定向检查及指定Topic真实固定范围聚合验收通过，真实报告留21；[3f回执](../../../docs/operations/evidence/lake-query-3f-20261119-01/README.md)完成29项定向检查、原生库/TCP HTTP合成及3e同批真实数据基础检索/完整原文读回。正式表和消费者尚未变更，后续[4a–4c已有告警选择/接收/持久交付](lake-alert-selection-20261119.md)已通过限定验证，全局metadata.uid/无更新合同已确认；当前进入[5a必要取证工具设计](lake-evidence-tools-design-20261119.md)，按最新要求已下载ES目标类JSON并核验，完整结构扫描及报告读回已通过；partial/缺失/数组及字段/查询设计已补，11-20已按负责人直接提供分布补齐11类各一条真实样本，随后已完成本机实际值与需求/当前映射对照及保存读回；设备资料交资产库，先核字段缺口再选工具。具体样本业务含义待确认的脱敏范围，未实施新工具。

## 1. 已核线上基线与推荐范围

[完整结构回执](../../../docs/operations/evidence/investigation-integration-audit-20261119-01/live-lake-schema-design-input.json)仅查询系统元数据：ClickHouse `23.8.16.16`，`aisoc.raw_events`共48列。引擎为`ReplacingMergeTree(ingest_time)`，分区为`(toYYYYMM(event_time), tenant_id)`，排序为`(tenant_id, event_time, class_uid, event_id)`；TTL按事件时间400天。现有列已有租户、时间、类别、源/目的主机及IP、进程、用户、文件、`ocsf_json/raw_payload`等。

推荐继续使用一张统一事件表：少量固定列承载身份、常用过滤及质量状态，完整OCSF留在`ocsf_json`，上游已有原文留在`raw_payload`。不按每个class或厂商分表，不把全部OCSF字段拆成列，不另外建立文件原件库。需要增加的是公共接入和查询能力所需的列，而不是每来一种日志就扩表。

本轮继续沿用String保存JSON。线上版本不适合直接照搬当前文档的新JSON类型；官方将新JSON的生产可用基线标在25.3，不为此次接入附带升级ClickHouse。参考：[JSON官方说明](https://clickhouse.com/docs/reference/data-types/newjson)。

## 2. 一行的含义和身份合同

一行代表一条上游清洗记录的一个完整内容版本。相同来源记录与相同内容的发送/消费重试复用湖身份；内容发生变化保留新版本。多条清洗记录是否对应同一厂商告警由后续告警合同确认，不能只凭湖ID推断。湖中日志并不等于调查告警，所有类别都保存，告警选择在后续独立进行。

新增接入按以下职责区分身份：

| 身份 | 含义与用途 |
| --- | --- |
| `event_id` | 我方湖内稳定UUID；由明确版本的确定性算法生成，供取证和去重；已有记录ID不追改 |
| `tenant_id + source_namespace` | 身份所属范围；不同租户/来源的相同上游ID不得碰撞，来源来自配置绑定 |
| `source_event_id` | 上游原始事件ID，String保存；可以是非UUID，不替换上游原值 |
| `source_version` | 本版采用完整输入的精确规范化摘要；metadata.version是OCSF版本，不是事件修订号。所有上游原字段进入摘要，不额外加入我方接收时钟、Kafka位置或投影字段 |
| Kafka坐标 | 定位本行所代表的输入消息及固定范围回放；不能将offset本身当成来源业务ID |

有可靠来源身份时，以租户、来源命名空间、原事件ID和版本共同生成湖内ID。缺来源ID时，用集群/Topic/partition/offset生成可重读的输入身份，明确它只能保证同一Kafka记录的重读去重；跨Topic回放若要复用身份，必须携带原坐标/来源映射，不能仅凭正文相同合并可能独立发生的事件。

当前`event_to_row`仅把可解析为UUID的来源ID写入event_id，否则让数据库随机生成，这不适用于该接入的稳定回放要求。此次应在新接入适配层生成稳定湖ID并原样保留上游ID。告警source-v1及材料关联沿其现有合同单独核对，不能把新的湖ID直接替换已有告警/材料ID。

上游参考代码的metadata.uid由ingest_id生成，故本版只承诺清洗记录身份；厂商告警的长期ID、业务更新关联及重新采集语义仍需对方确认。这不阻止本版列迁移及清洗记录落湖。摘要规则只作用于程序身份识别，不摘要改写业务正文。Kafka坐标列保留本行代表的投递位置，不承诺永久保存所有重复到达的位置；重复投递数量在受控批次回执中对账，本阶段不新增逐次投递账本。

## 3. 字段设计：复用和建议新增

### 3.1 保留的核心列

| 列 | 已有类型 | 本次约定 |
| --- | --- | --- |
| `event_id / tenant_id` | UUID | 湖身份确定性生成；租户由接入配置解析，不能缺失或临时随机生成 |
| `event_time` | DateTime64(3, UTC) | 严格读取OCSF.time整数毫秒；遵守对应class的主时间含义。缺失/非法固定epoch哨兵并标记，不使用Kafka时间或now兜底 |
| `ingest_time` | DateTime64(3, UTC) | 实际入湖写入时间，同时是现有ReplacingMergeTree版本列；不能混称首次发现或事件时间 |
| `class_uid/category_uid/activity_id` | UInt32 | 采用原分类，不因已有告警入口只支持几类而丢弃其他类；class 0保留其含义 |
| `severity_id / severity` | UInt8 / String | 上游日志等级，不当作I/Case当前业务等级 |
| `source_ip/dest_ip` | IPv6 | 明确源、目的角色，合法IPv4转为映射地址；缺失/非法与真实地址区分，原值在JSON保留 |
| `src_hostname/dst_hostname` | String | 新接入按源/目的端点映射；旧数据的历史混合语义不批量改写 |
| `user_name/process_name/file_path`等 | String等 | 作为已有工具需要的公共投影；按具体class确定字段角色，原层级仍保留 |
| `ocsf_json` | String + ZSTD | 完整收到的OCSF字段和未知扩展字段；取消存储侧主动preview替换 |
| `raw_payload` | String + ZSTD | 有效OCSF已有raw_data保留；缺失不制造原文。无法解析的输入可保存接收到的原载荷并明确invalid状态，不伪造合法OCSF |

### 3.2 首期定稿增加14列（当前线上均不存在）

| 列 | 建议类型 | 新接入要求与用途 | 旧行默认 |
| --- | --- | --- | --- |
| `source_namespace` | LowCardinality(String) | 必需；稳定来源范围，供身份计算及取证来源限定；不能用产品显示名称代替 | 空表示未知 |
| `source_event_id` | String | 原始上游ID；缺失须进入明确的Kafka坐标身份分支 | 空表示未知 |
| `source_version` | String | 事件版本/规范化摘要，区分重试与更新 | 空表示未知 |
| `is_alert` | Nullable(UInt8) | 只允许NULL/0/1，分别代表未提供或无法确认/明确否/明确是；不由class机械填充 | NULL |
| `device_hostname` | String | 保存device.hostname；与网络源/目的端点分开，供设备活动取证 | 空表示未知 |
| `device_ip` | Nullable(IPv6) | 保存device.ip，IPv4映射IPv6；支持只有设备IP的检索，不写成网络源IP | NULL |
| `event_time_source` | LowCardinality(String) | 新行ocsf_time_ms/missing/invalid；Kafka时间另列保存，不改变重读后的排序键 | unknown |
| `parse_status` | LowCardinality(String) | ok/partial/unclassified/invalid_json/invalid_utf8/non_object/tombstone；只说明解码及映射状态，不宣称完整OCSF认证 | unknown |
| `mapping_version` | LowCardinality(String) | 标识投影规则版本，解释同一路径的角色及后续兼容 | 空表示未知 |
| `kafka_cluster` | LowCardinality(String) | 输入集群的稳定逻辑标识，不用可变bootstrap地址作为身份 | 空表示未知 |
| `kafka_topic` | LowCardinality(String) | 实际输入Topic，区分正式直写/回放 | 空表示未知 |
| `kafka_partition` | Nullable(Int32) | 实际分区，非负；NULL表示旧记录未知 | NULL |
| `kafka_offset` | Nullable(Int64) | 实际offset，非负；0合法，不能代表未知 | NULL |
| `kafka_timestamp` | Nullable(DateTime64(3, UTC)) | Kafka记录时间，供重读与未知事件时间诊断；不能不加说明称为发生时间或首次接收时间 | NULL |

这14列为3a定稿合同，不是已实施迁移；相比原13列增加device_ip，是因为已有source_ip/dest_ip只承载网络两端，不能承担设备IP角色。source_namespace/ID/version是身份和来源查询字段；Kafka坐标是长期追溯字段；其余用于真实类别选择、设备角色和质量解释。只用于测试批次、错误详情、投影字段的精细缺失说明等，优先留在受控回执或既有后台JSON元数据，不因此继续加业务列。文件的`hash_sha256`是已有文件IOC列，不能借用为整条消息摘要。

新增列对旧行保持未知；不把所有旧行默认填成SpiritHub、不补造is_alert=false，也不为补齐字段回写旧正文。首次只验新增接入批次，旧数据继续可读。

## 4. 映射规则和查询职责

设备/进程活动通过device_hostname定位设备；网络活动分别通过source_ip/src_hostname与dest_ip/dst_hostname定位连接两端，不能把观察流量的设备当作连接源。旧src_hostname有设备名混用，新工具应按mapping_version或明确的旧行兼容路径读取，而不是统一覆盖原列。

按租户、允许的来源范围、对象角色、class和时间窗口检索。Case取证需要配套使用新来源/设备列，以及明确的IP-only路径；加了列但查询仍只看旧src_hostname，不算功能完成。所有技术元数据留后台，不因此整包送分析模型。

JSON中的少量类别专用字段先按固定工具合同解析；待实际类型盘点表明DNS/HTTP/注册表等有数据且有业务用途时，再判断哪些字段需要独立查询列。此时才定义具体字段和必要索引，不预建全部OCSF字段表。

## 5. 引擎、排序、分区与时间

本期以现有表增量补列，不同时改变分区、排序或重建历史数据。现有key能支持租户和时间范围查询，但它以整个ORDER BY键判断重复，不只看event_id；同一事件版本的event_time/class必须保持稳定，不允许把处理时的now写成重试后的新事件时间。

ReplacingMergeTree后台合并不是唯一约束，合并前查询仍须按已定义身份去重。现有C4的窗口去重可复用并补新来源语义，不能靠“等待合并”完成验收。[官方引擎说明](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/replacingmergetree)

保持月粒度，不增加按主机、IP、事件ID或每种class的分区；当前“月份+tenant”的分区作为既有结构保留。后续确有多租户规模问题再单独评估按月分区、tenant放排序前缀的迁移，不将其混入首次接入。[官方分区说明](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/custom-partitioning-key)

新接入的OCSF.time只按整数毫秒解释，不沿用旧received_time按数值大小猜秒/毫秒的方式。缺失、null或非法时，event_time使用固定`1970-01-01T00:00:00.000Z`哨兵，event_time_source分别为missing/invalid；不能用Kafka时间兜底，否则同一来源记录在不同投递位置重试会改变ORDER BY键。合法数值0仍标ocsf_time_ms，不能仅凭日期值判断缺时。新映射的可靠业务窗口必须过滤time_source，未知时间可按ingest_time、身份及坐标读取。

**已确认保留策略：本次新接入按每次实际入湖起算400天，重试写入会延长。** ingest_time继续由ClickHouse本次INSERT生成；不新增首次入湖时间列，不改原OCSF.time。仅对配置列出的新mapping_version使用ingest_time，旧行及旧映射仍按原event_time上限；表TTL的两个分支见候选SQL，天数和适用版本通过显式profile生成。

保留策略还涉及`retention.py`的DELETE和`retention_purge.py`的预览COUNT：现代码都按event_time，且租户策略可能短于表TTL上限。3b须让新映射分支同样按ingest_time/400天，旧映射保留现有租户策略；预览和删除共用同一条件，不修改其他数据类。未核清正在运行的清理任务或尚未统一两条删除路径前，不启用新接入写入。此处目标已在3b代码及隔离测试库实现，正式表TTL和实际清理进程尚未更新。

## 6. 本阶段目标、范围与配置

本阶段完成后的业务效果：我方指定Kafka Topic的日志能完整写入同一ClickHouse事件表；稳定身份可支持重读及更新区分；失败或未知不被消费确认跳过；可按来源、设备/网络端点、类别及可靠时间读取，并从查询结果关联完整OCSF。落湖步骤不依赖提前启用告警分诊或模型，普通活动、class 0和partial一样保存。

本阶段纳入列合同、增量迁移、入站适配、完整保存、持久确认、直接回放及基本查询。14个新增列及现有48列已逐列定用途、类型和映射；不为每个OCSF字段加列。新增检测规则、全部类别工具、模型正文质量重采样、数据库升级、排序/分区重构、性能/容灾专项、全仓回归不属于此阶段。既有告警字段、主体ID及材料关联合同继续保留。

运行配置必须一并设计，不把地址、开关或时限写死在适配代码中：

| 配置部分 | 需明确的合同 |
| --- | --- |
| 输入profile | 明确目标环境、broker/TLS/CA引用、实时或回放Topic、独立consumer group、起始范围；不自动回落其他profile |
| 后台身份 | tenant及source_namespace绑定、允许的来源范围；测试source/connector_type使用lyc开头的中性值，业务观察不加此前缀 |
| 映射及身份 | mapping_version、来源ID/版本规则、时间单位/时区和缺失处理；未知不默认为false或已知来源 |
| 写入及确认 | 默认启用落湖；批量大小、最大等待、请求时限及必要消息大小配置；成功回执对应实际持久写入，不能只对应内存缓冲 |
| 保留及读取 | 新接入每次入湖400天/旧映射原口径已确认；显式配置适用版本、天数、查询范围/页长，页面预览与完整原文读取分开；DDL及清理接线实施前线上仍保持原值 |
| 下游开关 | 普通日志落湖独立于已有告警选择；分类和模型执行只在对应后续步骤明确配置，不因开启湖写入自动开启通用promotion/native detection |

## 7. 实施顺序与每步完成出口

下表是[现有接入阶段计划](spirithub-integration-check-20261118.md#2026-11-19-最新接入方向及本阶段步骤)第3步的展开，不是新增任务树。每次执行一行，完成本行输入→处理→保存→读取验证并记录结果后，再推进依赖行；本地分步验证不触发逐次发布。

| 顺序 / 原任务 | 本步要完成的具体结果 | 依赖和直接验收 | 状态 |
| --- | --- | --- | --- |
| 3a / 3.7、3.21：定稿字段与映射合同 | 将本页每列补成字段字典：类型、必填时点、旧行默认、来源路径、未知/冲突处理、查询用途；明确来源版本、湖ID、时间与TTL口径；列清增量DDL和受影响写/读路径 | 使用已核48列、来源Schema与配置；用合成结构验非UUID身份、false/null、设备与源端点不同、时间缺失的规则；缺失业务选择只阻止对应规则定稿，不重新等待整个审计 | **3a已完成**；机器字典、3a SQL参考和6组合成规则检查已保存；005在3b注册 |
| 3b / 3.7、3.21：兼容迁移与列读回 | 在受控验证库按既有lake_migrations机制增加定稿列，同步新装DDL；旧数据保留，新增字段读作unknown/NULL，不伪造回填 | 依赖3a列合同；用当前结构的旧格式合成行验证升级后仍可读，再写一份新结构验证类型、NULL和字段读回；迁移重复运行不改变已有数据。迁移记录和实际列结构都要读回 | **3b已完成**；005/新装/profile同源；48项定向检查和23.8隔离库7组验证通过，正式表未改 |
| 3c / 3.7、3.21：入站适配与完整保存 | 将裸OCSF适配为我方写入视图，生成稳定湖ID、保留上游ID/版本，映射device/src/dst及已有查询列；取消存储侧preview替换 | 依赖3b；合成正常、partial/class0、缺ID/时间、false/null、非UUID来源及超过旧阈值的材料走转换→真实测试CH保存→读回。同版本重读身份稳定，真实更新保留新版本，未知字段和原文保持 | **3c已完成**；实际适配→原生INSERT→完整读回通过，未接消费者/分类/模型 |
| 3d / 3.7、3.21：Kafka与持久确认接线 | 订阅配置指定Topic，按实际持久写入回执提交各分区连续已确认位点；缓冲接收不算持久成功；失败/未知留在未确认范围 | 依赖3c；复用当前消费者/湖写入测试，只补一个正常小批和一次受控写失败：不得清空未确认状态后继续提交，不跨失败位置。低流量批次也能按配置落盘，未知先按稳定身份读回确认；不建设新恢复框架 | **3d已完成**；91项定向检查及真实Kafka/原生库三组通过，失败/未知不越位；首次分配竞态修正，01失败保留，正式未发布 |
| 3e / 3.7、3.21：真实固定范围聚合验收 | 直接读现有Kafka固定范围，写本步明确配置的测试范围；按新版本/重复版本/未持久化状态对账，从湖内实存正文重算分组摘要 | 依赖3d和保留策略已明确；正常、partial、未分类/异常均有去向；消息数不等于offset跨度，物理行数不等于逻辑版本数；不逐条人工看正文、不先额外导出原件或重投Kafka。真实报告留21，只回传执行/验证状态 | **3e已完成**；实际固定范围→隔离库保存→独立group确认→库内正文重算/聚合核对通过，报告留21；不代表正式持续消费已发布 |
| 3f / 3.7、3.10：基本查询及原文关联 | 查询使用正确的来源/设备/源端点/目的端点/时间语义；支持当前批次需要的host或IP入口，查询结果可关联完整OCSF | 依赖3e；同批记录按已有索引字段查回，unknown时间不会混成发生时间，设备不会冒充连接源；旧记录按明确兼容方式读取。缺字段、查空和失败分别返回 | **限定步骤已完成**；3e既有真实数据基础检索/完整原文读回通过；实际角色/类别覆盖单独记录，正式持续接入未发布 |

实施3a前重新运行主change strict校验；之后规格变动时再校验。3b–3f保存相应配置、源码版本、必要测试、写入回执与读回结果；不重派已结束批次，不覆盖旧失败。新增列/写入/查询须同一交付包接线，不能只交一个建表脚本。

## 8. 与后续事项的依赖和责任

| 后续事项 | 何时推进、由谁负责 | 完成判据 |
| --- | --- | --- |
| 对方正式直写Kafka | 我方已准备地址/Topic/TLS/CA交接；SpiritHub确认发送位置、事件ID/更新语义和切换安排。对方切换不阻止我方利用现有过渡Topic开发落湖 | 对方运行环境连通，生产端实际送达与我方接收一致，过渡转发切换范围明确；不能将同时双发计成独立新告警 |
| 现有类别与告警规则（接入步骤4） | 3f后按受控盘点确定本批类/字段，双方确认已有告警含义；我方实现配置化筛选和稳定关联 | 非告警只保存、已有告警进入A/I，partial不静默丢弃；原身份/材料可读，不打开通用promotion代替适配 |
| 新工具及真实Case（接入步骤5） | 我方基于实际类别选择一项确需工具，定义对象角色、时间范围、返回字段；再走一条真实Case | 湖查询→C4业务结果→C6保存→HTTP/4177读回；重用已验材料，质量后置保持，不重复全模型采样 |
| SpiritHub接口及产品联调（步骤6） | 我方提供最新80操作Swagger/Schema；SpiritHub负责桥接/页面。合同准备可先行，接线依各功能准备程度逐项验证 | 修退役auth/me、19未接/19退役代理、201/202和任务轮询后，完成一条产品保存读回业务链；附件本地接口单独按归属核 |
| 等级/优先级及运行记录字段 | 沿原S1–S7，由对应后端与页面落实；不作为日志落湖前置，不重开设计 | 分步复用该计划的真实保存/读取证据；SF04–SF07未覆盖项及旧质量失败不顺带核销 |
| change收口 | 我方合并本阶段与原任务的真实完成证据，按原change范围交接和独立结束审计 | 未参与实现者结束审计、必要直接验收及交接完成后，在获准范围统一发布/读回/推送/父项目同步；不每个小修都更新21 |

## 9. 已确认选择与尚待对外确认

| 项目 | 当前建议/已知事实 | 谁提供结论、影响哪一步 |
| --- | --- | --- |
| 保留期从哪里起算 | **负责人已确认**本次新接入按每次入湖400天，重试写入刷新；旧行保持原口径 | 3a已定稿；3b同步表TTL与租户清理分支，3e再验证历史回放。无需重复索要该选择 |
| 源事件ID及更新语义 | 保留上游原ID，区分原事件/版本/发送重试。来源不确定时只承诺Kafka同记录重读去重，不冒称跨Topic业务去重 | 已定本版清洗记录级metadata.uid/完整内容版本规则；SpiritHub后续确认业务告警更新关联，影响告警分类及直写切换，不阻止3b列迁移 |
| 统计进入Codex的范围 | 盘点已经在21完成，统计仍属数据；仅需经用户脱敏确认的class/is_alert组合计数、固定字段覆盖，不需要主机/IP/账号或正文 | 由负责人完成脱敏并确认目标服务。仅影响Codex据真实分布确定分类/新工具的后续判断；不阻止代码/Schema层的3a–3d准备 |
| 正式直写可达性及切换时间 | 地址`192.168.1.21:19093`、SSL和目标Topic已明确，CA由我方提供；发送环境尚需实际联调 | SpiritHub给出运行位置与时间，双方核对应接入配置；不把当前转发成功当对方直写已完成 |

本轮3a已将原13列候选补为14列定稿合同，定稿不代表已部署。普通内部技术选择沿已授权方向处理，不另设角色/读写权限审批；确需变更冻结告警交接合同时才按项目原规则列具体兼容影响。

## 10. 湖3a交付与下一次起点

3a已形成[完整逐列机器字典](lake-ingress-contract-v1.json)和[精确增量SQL候选](lake-ingress-add-columns-v1.sql)，保留现有48列并追加14列；来源版本、未知值、角色、时间和保留规则已明确。3a批次当时仅在本change内评审，随后3b已注册005并准备部署清单，不含数据回填、历史列修改和批量清理。

[3a验证回执](../../../docs/operations/evidence/lake-contract-3a-20261119-01/README.md)使用合成结构验证合同，6组直接检查及脚本Ruff通过；首次脚本风格检查失败已保留并修正。未运行Kafka消费、ClickHouse DDL/写入、模型、服务部署或Git同步，不能据此称落湖已可用。

3b现已完成：005、新装/profile与条件TTL/清理接线通过定向程序检查及23.8隔离库读回。3c现也已通过实际适配、原生保存及完整读回，下一次仅从3d Kafka与持久确认接线开始；3c不代替实际消费位点验收。正式表及消费者尚未更新。

## 11. 3a精确映射与实施接线

### 11.1 来源、字段和身份

机器字典逐一列出48个现有列的类型、来源、转换、兜底和含义，以及14个新增列的默认值和校验。新裸OCSF仅以profile绑定租户/来源/connector_type，正文同名字段仍完整保留但不控制路由。原activity/session扩展的内部语义不从任意标准字段猜造；此profile默认不启用该扩展，原值仍在完整JSON。

上游已核参考代码`normalized.go`用ingest_id生成event_id，`ocsf.go`将其写入metadata.uid；`metadata.original_event_uid`、`finding_info.uid`、event_fingerprint和Kafka Key职责不同，本版不互相替代。该结论来自交接参考源码，不据此声称已检查所有实际消息或对方未来直写实现。OCSF本身也区分本记录uid和来源系统original_event_uid，见[1.9元数据Schema](https://raw.githubusercontent.com/ocsf/ocsf-schema/v1.9.0/objects/metadata.json)。

本版source_version是**完整收到内容**的精确规范化SHA256摘要；保留全部未知字段及上游日志元数据，不擅自剔除所谓易变字段。仅不额外混入我方时钟、Kafka位置和派生投影。对象键按Unicode码点排序、数组保序，布尔/数字/字符串/null分别编码，数字先区分整数写法和小数/指数写法，再在同一种写法内用精确十进制规范化，不经float丢失长整数；重复JSON键、非有限数和非法Unicode按异常输入保留。规范化对象及UUIDv5输入元组在当前机器合同和3c实现检查中固定；3a未发布草案的数值写法冲突已在3c修正，历史参考保留。正式v1交付后改变这些规则须另立显式映射版本。

metadata.uid存在时，湖UUID由合同版本、tenant、source_namespace、原ID、source_version生成；缺ID使用集群/Topic/partition/offset及内容版本。后者只保证同一Kafka记录重读稳定，不能承诺跨Topic去重。来源日志元数据被重新生成时完整内容版本也改变；一条厂商告警关联多条接入记录的问题留给对方确认与后续告警适配，不能提前合并丢掉内容。

### 11.2 角色、partial和完整正文

- `device.hostname/device.ip`分别进入device_hostname/device_ip；网络两端只进入src/dst列。device.name是显示名，不自动等同hostname。IPv4用映射IPv6；新增device_ip缺失/非法为NULL，旧IP/端口列保持原类型及哨兵，匹配时结合原字段存在性，不将哨兵当实际对象。
- 认证class3002的user_name取user.name，其他类取actor.user.name；进程class1007的process_name取process.name，其他类取actor.process.name。目标缺失时不拿行为主体补成同一对象；文件SHA256识别algorithm_id=3及一致算法名称，不能把消息摘要塞进文件IOC列。[OCSF指纹Schema](https://raw.githubusercontent.com/ocsf/ocsf-schema/v1.9.0/objects/fingerprint.json)
- 对角色字段及is_alert，只在根路径**不存在**时读取`unmapped.spirithub.partial_fields`的同角色路径；显式null/非法/冲突不隐式回退。class/category/activity始终保留根分类，不恢复目标class把partial伪装完整。is_alert只接受bool或整数0/1，未提供/非法为NULL，2003/2004/高严重度不能代填true。
- 有效对象的ocsf_json保存收到的完整UTF-8 JSON文本，不插入或覆盖`_socai2_storage`，不替换成preview。raw_data字符串原样进入raw_payload，非字符串保存其JSON表示，0/false不变空。异常JSON/非对象保留UTF-8原载荷，非法UTF-8用base64可逆保存并标invalid_utf8；tombstone与空字节的状态不同。错误不因此变成合法OCSF。

### 11.3 时间、查询与可兼容边界

本profile按[OCSF1.9主时间合同](https://raw.githubusercontent.com/ocsf/ocsf-schema/v1.9.0/events/base_event.json)处理time整数毫秒；活动类通常是发生时间，Finding类可能是发现建立时间，不把后者当作原行为时间证明。以当前23.8系列的[DateTime64版本文档](https://raw.githubusercontent.com/ClickHouse/ClickHouse/v23.8.1.2992-lts/docs/en/sql-reference/data-types/datetime64.md)限定可投影区间1900至2299年，越界完整保留但投影为invalid；实际绑定由3c在23.8.16.16验证。

新映射可靠时间窗口要求event_time_source=ocsf_time_ms；缺时的固定哨兵只用于满足既有非空列/稳定排序键，另按ingest_time或记录身份检索。旧行unknown走明确旧兼容分支，不追写历史。查询仍在合并前按既有ORDER BY身份去重，不能只等后台合并；来源、设备/端点、有效IP和时间质量与查询一起接入。主机存储保留原值，3f需保证冻结对象的大小写规范化与查询一致。

### 11.4 文件接线与3b出口

| 步骤 | 现有入口 | 必须同步的具体变化 |
| --- | --- | --- |
| 3b | `services/api/app/db/lake_migrations.py`、`services/api/clickhouse/001_init.sql` | 004后新增前向迁移；追加14列与告警标记/非负Kafka坐标约束；显式库profile渲染候选SQL；旧列/排序/分区不变，不MATERIALIZE历史列或索引 |
| 3b | `services/api/app/services/retention.py`、`services/api/app/workers/retention_purge.py`及相应profile | 新映射的每次入湖400天与旧租户事件时间策略分支一致；COUNT/DELETE共享条件，表TTL与新装/升级配置同版。读清理开关只输出配置结构/状态，不查询客户记录 |
| 3c | `services/fusion/app/services/lake_writer.py`、新入站适配及现有材料保存路径 | 独立处理裸OCSF与原信封；字典要求的字段/身份/原文转换，取消本接入存储截断；命名列INSERT包含新列，ingest_time取实际INSERT时间；保存/读回证明完整性 |
| 3d | `services/fusion/app/workers/consumer.py`、`services/fusion/app/core/config.py`、运行profile/部署示例 | 在全局json反序列化之前保留原字节和ConsumerRecord坐标，错误载荷也有落湖去向；topic/租户/来源显式绑定，持久确认后推进分区连续位点 |
| 3f及后续Case | `baseline_evidence_tools.py`、`baseline_semantics.py`、`baseline_dispatch.py`及工具合同 | 来源和对象角色、device/IP入口、时间质量、完整JSON关联与字段集合校验同步；原冻结工具版本可识别，不能只增加列而沿用旧src_hostname过滤 |

3b进入数据库前先核实际列类型与引擎；同名列类型不一致时停止该迁移，不用IF NOT EXISTS掩盖不一致。列追加与新装DDL保持同一合同，约束对旧默认NULL/空值兼容，迁移账本及system.columns/TTL读回。仅用受控测试库中的旧格式行、新格式行及重复写入检查兼容和保留表达式；尚不消费Kafka或触发模型。TTL变更与正在运行的清理任务必须统一后才允许3c/3d开始新接入写入。

### 11.5 湖3b实施落点（2026-11-19）

本步只交付62列结构、显式存储profile、005前向迁移、新装渲染及保留清理接线。先核48旧列、已有新增列类型/默认值、引擎/键/TTL，再执行追加；不兼容时停止。迁移账本必须实际写入并读回；修正既有同步ClickHouse客户端被直接await及账本INSERT形态问题。新装与升级使用同一列定义和同一profile，未选择profile时迁移及湖清理拒绝执行，不回落到其他库。既有001–004编号保留。

顺序：①补齐profile/DDL/清理条件及必要接线；②定向检查配置拒绝、COUNT/DELETE同条件和旧接口兼容；③在21的独立`lyc_lake_3b_*`合成验证库执行旧48列升级、新装、重复迁移、旧行默认值/新列读回、重写后保留期和租户清理。只返回合成检查与结构元数据。正式`aisoc.raw_events`、Kafka/消费者、模型均不操作。

`MODIFY TTL`显式使用`materialize_ttl_after_modify=0`，不主动重算旧分片；原旧映射TTL不变，新映射入湖时间规则作用于后续INSERT。该设置在[23.8源码](https://raw.githubusercontent.com/ClickHouse/ClickHouse/v23.8.1.2992-lts/src/Core/Settings.h)中默认开启，本步需在真实23.8验证关闭后的迁移不生成TTL历史mutation。验收通过以实际结构/保存读回/迁移账本/清理结果为据，不以CLI校验代替。

### 11.6 湖3c实施安排（2026-11-19）

本步依赖已验3b，只交付裸OCSF适配和完整保存/读回。新增Fusion内部适配入口，接收原始bytes（含tombstone）及独立Kafka坐标，以显式profile绑定tenant/source/connector/database/OCSF版本；不从正文选择租户或把裸输入猜成原信封。原`event_to_row`、告警材料ID和原消费者分支保留，新入口不调用其截断函数。62列中ingest_time由实际INSERT生成，其余61列按3a字典产生。

步骤与直接验收：

1. 实现严格JSON及精确内容摘要、UUIDv5身份、角色/partial/时间投影和完整材料保存；用合成普通/未知class、partial、缺ID/时间、false/null、长整数/小数及异常载荷核规则。显式null或非法祖先对象不能误判成“路径缺失”而从partial_fields回填。
2. 在现有LakeWriter上复用客户端和类型绑定，增加明确的新批次保存入口；只在同步INSERT返回后给保存回执，未配置/未连接拒绝，执行异常保留未知结果并抛出，不返回假成功、不自动重试。该入口在3c直接调用，3d才对接Kafka连续位点与批次调度；不借此宣称旧缓冲消费者已可靠。
3. 使用已存在的Fusion依赖镜像启动一次性验证进程，在全新`lyc_lake_3c_*`隔离库由真实clickhouse-driver完成原字节→实际适配→原生INSERT→SELECT读回。检查完整ocsf_json/raw_payload（包括超过旧64/256KiB阈值）、新列角色、身份重试/更新、缺时稳定、错误材料可逆、旧信封兼容；程序比较字节/长度/摘要及逻辑版本数，结果只输出合成检查状态。保留3b表和正式表，不读取客户记录。

时间绑定需要额外直接核查：本机驱动DateTime64实现对负epoch的datetime小数先取整，可能把-1ms错写为999ms。新入口将按列的毫秒刻度绑定精确整数，核-1ms、1900及2299边界的实际读回；不改旧信封的时间合同。参考[驱动类型文档](https://clickhouse-driver.readthedocs.io/en/latest/types.html)及当前已安装实现，以23.8真实绑定结果为准。

通过后更新本清单及PROGRESS，记录失败/修正和未验范围，下一步3d。排除持续订阅、Kafka提交/真实回放、告警筛选、取证工具/模型、正式服务发布及Git同步；不新增通用恢复框架或全仓回归。

3c补核[OCSF1.9字典](https://raw.githubusercontent.com/ocsf/ocsf-schema/v1.9.0/dictionary.json)：type_uid为long_t，单独按非负Int64校验并完整留JSON，不套用class/category/activity列的UInt32范围；机器合同同步补明。此项只影响解析质量标记，不改列结构或冻结告警合同。原生01批通过后另用02批两条合成记录定向验证，不重派01批。

3c收口回归复现合同内冲突：旧数值规范化把整数和等值小数合并，但time/class的整数写法校验会产生不同投影/排序键。当前未发布v1合同修正为integer/decimal两类标签（小数1.00与1e0仍等价，整数1与小数1.0分开），避免同湖ID跨排序键；不加入派生投影或时钟。3a历史参考脚本及01/02批不追改，新增03独立批次验证最终适配器的完整流程和两个数值写法输入。正式源未接通，不存在需重写的正式v1湖身份。

### 11.7 湖3d实施安排（2026-11-19）

本步只完成指定裸OCSF输入的Kafka消费→3c实际INSERT→分区提交，以及失败/未知的停止和读回。复用Fusion启动/关闭、Kafka安全配置和LakeWriter；裸输入使用独立consumer group及无反序列化的客户端，避免旧信封、告警和UEBA分支提交本接入位点。新接入profile默认启用，必须同时显式选择3c来源/库及3b存储策略；旧入口的best-effort缓冲合同不冒称已修复。正式部署仍须同版交付005、TTL、API清理策略及Fusion配置。

1. 配置与调度：消费profile明确broker、独立group、首次起点、批量上限、最长等待、请求/轮询及消息大小限制，复用现有TLS/CA配置文件。禁用自动提交及隐式offset重置；仅新组无位点时按显式策略从当前最早位置开始，已有位点越界时报错。每次getmany返回的分区批次依次处理，无需等下一条消息或凑满批量；空闲等待有界。所有类别及异常字节交3c适配，不接promotion、告警或模型。
2. 持久确认：一分区一批、串行写入，核保存回执覆盖本批全部位置后，仅commit该分区最后处理offset+1。offset可自然不连续，不以数字跨度充当消息数；消费位置与已提交位置分开。持久失败、回执不全或commit失败即停止整个新接入循环，清除ready，不处理后续批次；此前独立分区已完成的提交保留，后续分区不提交。保留本次已拉取但未提交的范围，不清空后继续。
3. 未知与生命周期：INSERT异常先按稳定身份及完整保存内容做只读核对，区分已见、未见和查询未知；核对不改写原未知结果，不自动补写或自动越位提交。native调用被取消时先等驱动线程结束再释放连接锁，保留未提交范围并核对；停机不因flush/关闭提交未确认输入。分区撤销后停止本接入，不能跨代提交旧批次；重启由明确运维操作处理，沿原group重读前核对未知范围，不扩为自动恢复框架。
4. 直接验证：复用3c及旧消费者定向测试，增加正常分区批次/低流量、受控INSERT失败、已写但回执未知、取消及撤销时的提交边界。使用21全新lyc测试Topic/group及隔离ClickHouse库跑真实Kafka→原生INSERT→读回→broker committed核验；仅合成输入、一个受控数据库拒绝及一次回执丢失替身，不操作客户Topic/旧group/正式表。失败场景有后续同分区输入，证明不能被成功覆盖；小批验证完整正文和异常材料可读回。

证据保存至`docs/operations/evidence/lake-consumer-3d-20261119-01/`，区分真实Kafka/ClickHouse与注入边界替身，冻结源码、非私密配置、状态及失败回执。完成后下一项仍为3e真实固定范围聚合验收；3f查询、分类/新工具/Case、模型、正式部署和Git同步不在本步。按[aiokafka手工提交说明](https://aiokafka.readthedocs.io/en/stable/consumer.html#manual-vs-automatic-committing)使用显式分区offset+1；再平衡期间不提交失去的分区。

### 11.8 湖3e实施安排（2026-11-19）

本步只完成指定Topic的固定范围聚合验收，不发布服务或推进3f查询。复用3b建表/迁移、3c原字节适配/保存以及3d的分区整批持久确认；新增受控验收入口及必要的聚合比较。先用合成输入直接验证重复、更新、非法材料及边界裁剪，再在21全新`lyc_lake_3e_*`库读取真实指定Topic。真实正文、统计、身份、摘要、范围及查询结果都留21的受控目录，只回传预先限定的执行/验证状态。

1. 显式profile选择Topic、broker/TLS、独立lyc消费组、来源/租户/映射、隔离库、批量和时限。只处理`socai2.spirithub.events-ocsf-v1`，不额外复制/重投记录，也不顺带读取历史回放Topic。首先通过只读metadata确认Topic存在，再冻结每分区当前最早/结束位点到私有范围文件。手工assign/seek，不加入业务组；新组必须无旧位点，新库必须为空。当前保留范围不代表Kafka中已过期的历史。
2. 逐分区仅处理冻结的[start,end)内记录，复用3d实际保存→分区commit逻辑；结束后的新增消息即使预取也不得保存或提交。空洞不按记录计数，扫描进度与最后实际提交分开；不得用向end提交来补空洞。超时、达到显式条数上限、范围在读取中失效、保存/提交未知都保留部分状态并判未通过，不重派已结束批次。
3. 输入侧仅在内存保留稳定身份、内容摘要及聚合指标，不另存正文副本。区分消息数、不同逻辑版本数、重复投递及同来源ID的更新版本；质量/class分组只进入私有报告。湖侧直接读取实际保存的完整正文重新计算材料摘要、内容版本和湖身份，核对范围/角色之外的本步公共身份与质量字段，并对逻辑版本集合及分组摘要比较；不把输入摘要或保存回执当作湖侧读回结果。
4. ReplacingMergeTree允许重复物理行后续合并。以稳定版本身份比较，不要求物理行数等于消息数；同身份且规范化内容等价的多种原文本写法，只要求保留完整的某个实际收到的版本原文，单列重复/原文变体统计，不宣称逐投递副本永久存在。缺ID时仍按原Kafka坐标区分记录。损坏/截断的实存正文、缺版本、多余版本、排序键或解析状态错配必须判失败。
5. 直接检查只覆盖本入口的范围边界、重复/更新、正文损坏识别和失败不越位，复用3c/3d既有测试，不扩展故障矩阵。真实批次通过必须同时满足冻结范围读取完成、每次实际写入确认、broker已提交位点等于各分区最后实际保存offset+1、湖内逻辑集合与重算内容摘要相符；空输入不能冒称接入验收通过。普通活动、class0/partial和异常材料按实际出现情况保存，不为凑覆盖向客户Topic造数据。

公开证据放`docs/operations/evidence/lake-replay-3e-20261119-01/`，包括候选代码、配置结构、合成验证及无数据状态回执。私有聚合报告和冻结范围文件在21保存并读回核验；一旦失败先定位本步阻断，不以再次完整重放掩盖未知。通过并回报后下一项为3f基本查询及原文关联；正式部署、旧消费组变更、告警/模型和Git同步仍不在本步。

### 11.9 湖3f实施安排（2026-11-19）

#### 11-20历史批次重入湖及5001读回（本轮授权步骤）

负责人已审阅并确认UID诊断清单可读：原目标库中仅按UID列或完整JSON内metadata.uid也未找到该样本。随后明确授权将原数据重新入库，并允许删除旧数据。本轮采用已有适配、持久保存/确认及整批验收代码；只重建当前测试湖的记录，不变更业务映射、对外合同或服务部署。

- 固定目标：`lyc_lake_3e_actual_20261119_01.raw_events`。负责人允许删除的范围只用于该表旧记录；保留数据库/表结构、迁移账本、其他表/库、旧证据及PG调查业务数据。不会切换到另一个库掩盖旧查询查空。
- 固定输入：已有历史回放Topic `socai2.spirithub.events-ocsf-v1.replay-20261118`，归档交付范围为分区0、offset `[0,22580)`，期望22580条。沿原OCSF消息字节消费，保留metadata.uid，不重跑normalizer、不重投Kafka。独立新lyc消费组，不重置旧组。
- 顺序：只读检查Topic仍完整保留该范围、5001样本所在Kafka位置的UID/内容版本与本机样本一致、既有62列/005可用→记录旧表Schema及清理前计数（私有）→仅TRUNCATE目标raw_events并核空→复用run_replay固定范围入湖→核冻结范围、实际消费/持久确认及库内逻辑版本/正文重算一致→仅按原5001 UID查回并核其完整原文→更新本机5001直观说明。
- 失败边界：源范围/样本/结构未通过时不删旧记录；清理后若发生失败/unknown，保留新批次状态/位点/部分数据，定向排查，不盲目清空重派。重复写入按既定身份处理，400天由本次入湖起算。已结束旧批次不改写为新结果。
- 必要验证：复用3c/3d/3e既有有效证据及未变核心代码；本轮运行直接相关的replay检查，预检和实际入湖后核完整输入→保存→读取，5001查找不带Topic/来源/类别/版本过滤；内容版本只用于查到后的原文一致性验证。公共回执只含执行/验收状态，真实值/新统计留私有文件。

本步完成效果：这批历史OCSF在同一个明确目标湖可查询，原5001 UID和完整正文可读回。本轮不触发A/I、Case、模型、正式持续消费者或Git发布，也不把新取证工具算作已完成。源码、显式配置及回执目录为`docs/operations/evidence/history-lake-reload-20261120-01/`。

[本轮回执](../../../docs/operations/evidence/history-lake-reload-20261120-01/README.md)已通过：预检后仅清理指定raw_events旧记录，原表结构/迁移账本保留；22580条固定范围回放、持久确认/整批正文读回及5001仅按UID查询/完整JSON一致通过。当前仍使用原库，未切换目标。新的5001实际保存说明已在本机生成，旧查空材料保持历史状态。映射规则未改，5001资产关联/必要取证工具仍按5a后续推进。

本步完成来源限定的基本检索和完整材料关联，使用3e已保存批次只读验证，不重新消费Kafka、补写真实湖行或启动Case/模型。现有C4 v1仅按src_hostname和三类class查询，且没有来源限制；新能力通过共用核心查询服务、外部调查HTTP用例端口及内部C4 v2接线，旧冻结v1按原合同识别。旧信封身份、告警DTO/材料关联及已发布HTTP字段不改。新增两个只读HTTP入口是候选合同，正式80操作合同暂不替换。

1. 显式查询profile绑定数据库和允许的tenant/source_namespace/mapping_version范围、页长、时间窗和查询/连接/关闭/结果大小限制；不得从客户端正文选库或缺配置回落到正式库。查询按设备、源端点、目的端点分别接受host/IP；主机比较采用明确ASCII小写规范，IPv4和映射IPv6按同一地址比较，空值及未指定地址不作为有效IP目标。存储原值保持。稳定版本先按原排序键去重，再应用对象/时间过滤和分页，避免过滤先命中旧副本。
2. 新映射event时间查询只包含event_time_source=ocsf_time_ms；ingest时间可检索缺时/非法材料。旧映射必须显式允许空source/mapping范围，以legacy_event或ingest读取；旧混合src_hostname只作为legacy_host入口，不伪称设备或可靠连接源。新映射不得走legacy口径。分页有界、游标绑定完整筛选和profile，不声称并发写入时是历史快照。
3. 搜索返回身份、质量、对象角色及完整材料引用；材料读取按tenant/source/mapping、event_id/source_version/event_time/class_uid精确定位，返回完整ocsf_json/raw_payload及编码/完整性状态，不生成preview。旧preview/旧原件不确定明确标记，不用新规则补造原文。复用已能结束本地驱动的owned查询；完成查空、已知失败、执行未知保持区别，未完成结果不能冒充空集合或完整原件。
4. 外部入口归investigation_http，经用例端口调用核心：POST /api/v1/socai2/lake/events/search、GET /api/v1/socai2/lake/events/{event_id}/material。同步候选OpenAPI及请求/返回说明。C4 v2复用相同来源、角色、时间及完整行查询；只升级现有进程/网络/认证三类，不新增分类器或其他类别工具。绑定的来源和版本留后台，模型候选只见业务对象及角色；旧v1绑定、原答及对象投影保持可识别，不静默转成v2。
5. 先用合成输入验证角色隔离、主机大小写/映射IP、租户/来源范围、重复合并前分页、时间质量、完整大正文、旧行/旧preview、查空/失败/未知及v1兼容；复用已有owned查询和C4测试，不扩展故障矩阵。再使用21上3e已入湖数据，通过候选HTTP实际查询→材料引用→完整读回比较并核C4 v2实际查询。参数、字段值、类别/数量、摘要和报告都留21，仅回传固定执行/验证状态。实际批次未具备的对象角色/时间质量类别不伪造覆盖，合成结果与实际覆盖分别记录。

证据放`docs/operations/evidence/lake-query-3f-20261119-01/`。本步通过后3a–3f的候选存取链具备直接证据，但正式持续接入、全部类别取证、Case业务联验及主change结束审计仍未完成；发布/提交按统一交付规则另行推进，不在本步自动执行。

#### 3f直接验证发现与收敛（2026-11-19）

02候选的真实批次验证停在some_scoped_query_verified；未冒称主机/IP实际链通过。检查发现原搜索合同强制selector，会使缺少可用主机/IP的已保存材料没有基础检索入口。补为可选selector：未指定时按明确tenant/source/mapping及有界event/ingest窗口浏览，类过滤、先去重后分页、完整原文引用均保持；指定时继续严格按对象角色查找。C4 v2仍必须绑定冻结对象，不把无对象浏览开放成模型扩查。补直接验证无selector分页/时间质量/正文关联，实际覆盖与缺失原因留私有报告。原失败保留，新批次只读复验，不重新入湖。

#### 3f结果（2026-11-19）

03合成及同批真实只读验证均通过。程序29项定向检查通过；与最新正式80操作比较，候选仅新增2项湖读取入口、既有路径和Schema不变。受控21目录保留01/02失败及03成功的私有回执，公开仅固定验证状态及结构元数据。正式核心/HTTP镜像和启动时间保持11-17 r1，正式raw_events仍48列。本步不核销3.7/3.10/3.21整体任务，实际C4类别覆盖不能由合成三类均通过推断。完整交接、配置、源码及证据见[3f回执](../../../docs/operations/evidence/lake-query-3f-20261119-01/README.md)。
