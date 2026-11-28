# 当前配置索引

更新于2026-11-19。部署统一从[全模块入口](../../deploy/README.md)开始；只说明当前目标版本，不把旧分阶段样例、已结束发布或开发默认作为另一套操作方案。

## 先区分是否需要填写

| 类别 | 部署人员处理方式 |
| --- | --- |
| 部署必填 | 按环境确认地址、端口、库名、租户/actor、账号密码和私密文件路径、Topic/group、镜像/目录 |
| 保留默认 | 通常不修改模板中的并发、周期、重试、容量、分页和预算；严格JSON/TOML中仍需保留字段 |
| 启用时必填 | 启用对应功能才准备，例如知识embedding/Qdrant、情报provider、Kafka TLS等 |
| 程序生成/只读核对 | 镜像ID、配置hash、实际容器/Run/状态由构建和运行产生，不能手填为成功 |

负责人已确认PG采用用户名密码，**应用不再需要CA、客户端证书或私钥配置**。当前目标默认`sslmode=require`，保留服务器TLS而不要求客户端校验服务器证书；连接信息仍必须显式选择。这个修改尚未统一部署，历史运行清单中的verify-full只表示原实际状态。Kafka的TLS配置属于另一条连接，不随PG调整删除。

## 唯一配置说明位置

| 范围 | 完整说明 | 当前配置入口 |
| --- | --- | --- |
| A/I/Case任务、队列、活动窗口、重试、容量与补查 | [处理链](deployment-processing.md) | analysis-aic-dispatch / analysis-aic-executors / analysis-tasks / case-allocation |
| C4独占查询连接与关闭观察时限 | [本机/统一策略入口](../../deploy/local-investigation/README.md#当前选用配置) | investigation-policy-case-v1.toml 的 query_transport；随下一统一发布冻结，当前源码配置不代表21已更新 |
| 核心构建、处理profile、投影及传输 | [处理链](deployment-processing.md) | 当前candidate build/transport及production-profile模板 |
| 对外HTTP、读写连接、可信上下文、查询/任务策略 | [HTTP逐项表](../../deploy/http-service/CONFIGURATION.md) | 当前streaming候选profile及受控runtime JSON |
| Swagger | [Swagger](../../deploy/api-docs/README.md) | 同批OpenAPI、Compose及明确env |
| LiteLLM路由、模型上游、tokenizer、Token/时限、输入输出合同 | [模型](deployment-models.md) | compose.gateway、litellm.config、investigation-policy-case-v1及三份IO |
| Ollama嵌入、C2知识与Qdrant集合 | [知识](deployment-models.md) | compose.embedding、knowledge-profile.json |
| PG、Redis、Kafka、ClickHouse、Qdrant、Neo4j、OpenSearch | [数据湖与数据库](deployment-datastores.md) | 选定服务配置+模块连接profile；不以厂商默认替代实际配置 |
| PG新装/升级/普通运行角色 | [数据库当前入口](../../deploy/database/CURRENT.md)及[参数表](deployment-datastores.md) | 正式123–129；4b/4c候选新增内部130/131，已验新装/重复增量，未正式应用；不改冻结V1 |
| 湖告警持久交付worker | [4c配置与运行](../../deploy/aisoc21/lake-alert-delivery-4c/README.md) | 显式delivery/selection/receive/connection文件；登记、接收后确认及unknown只读恢复已验，正式未启用 |
| UEBA、Enrichment、ThreatIntel、Actions及Agents保留开关 | [支持服务](deployment-support-services.md) | 当前各模块loader及受控env；未启功能不自动启用 |
| 测试账本/只读API | [测试服务](../../deploy/investigation-test/README.md) | read-only/upstream/viewer三份显式profile；W4包另用package-build.json及candidate-21.json，账本与配置外置 |
| Docker验收CLI | [专用镜像与挂载](../../deploy/investigation-test/acceptance-docker.md) | acceptance-image.json固定基础/平台/依赖；acceptance.env选择只读材料、只读配置、独立持久结果及网络/非root用户。profile.connection_files与嵌套secrets均为稳定容器路径；默认network=none，不联启业务服务 |
| 4177、展示预览 | [查阅模块](deployment-support-services.md#工作台测试api与swagger) | 当前0.6.2/r9沿[本批release](../../deploy/investigation-test/releases/workbench-d6-20261118-01/release.json)及[正式读回](evidence/workbench-d6-release-20261118-01/README.md)；日常18024、tenant及账本保持。旧workbench-display-current.json/release-4177.json是历史清单，processing_audit_view.json只供离线归档 |

地址、端口和模型不是在业务代码里手工替换的常量；部署人员修改选定配置文件，启动器加载后核实际镜像/挂载/参数。默认值调整须区分模型调用时限、整Run预算、调度轮询和自动更新周期，不能把一个数同时套给各层。

## 日志湖存储profile（湖3b）

[存储配置与升级入口](../../deploy/aisoc21/lake-storage-3b/README.md)提供`storage.example.json`、新装渲染/005迁移命令及compose挂载示例。`AISOC_LAKE_STORAGE_POLICY_FILE`须明确选文件，库名必须与`CLICKHOUSE_DATABASE`一致；新映射按每次入湖400天，旧映射按原租户事件时间策略。迁移和湖清理不在漏配置时回落，部署时需让实际清理进程使用同一profile。3b已在隔离库验证，正式表/服务未发布；3c/3d已完成隔离验证，3e真实固定范围聚合验收已通过，3f基本查询及完整原文关联已通过。

## 裸OCSF入站profile（湖3c）

[3c配置入口](../../deploy/aisoc21/lake-ingress-3c/README.md)通过`AISOC_LAKE_INGRESS_PROFILE_FILE`选择文件，绑定租户/来源/Topic及相对引用的3b存储策略；与Fusion的`CLICKHOUSE_DATABASE`一致。新裸入口完整保存已验，原信封行为保持。单独选择此配置不自动订阅新Topic；3d消费接线通过另一显式profile启用，正式环境尚未发布。

## Kafka持久确认profile（湖3d）

[3d配置入口](../../deploy/aisoc21/lake-consumer-3d/README.md)用`AISOC_LAKE_CONSUMER_PROFILE_FILE`选择consumer.json，独立broker/group、首次起点、批量/等待、请求及消息大小限制均显式配置；TLS/CA沿既有env文件。配套005/TTL/清理策略必须同版，旧信封路径保持。取消等待native结束，异常停止接入并保留未提交范围；[合成隔离回执](evidence/lake-consumer-3d-20261119-01/README.md)已验证实际保存后分区提交及失败/未知不越位，正式未启用。

## 固定范围落湖验收（湖3e）

[3e配置入口](../../deploy/aisoc21/lake-replay-3e/README.md)复用来源/存储/消费配置，另选limits文件明确唯一Topic及运行、消息、读回限制。使用新lyc库/group，冻结范围后只保存其中实际消息；从湖内正文重算身份/摘要。真实报告、数量/类别/范围和日志留受控环境，只取回固定执行状态。[本批真实范围验收](evidence/lake-replay-3e-20261119-01/README.md)已通过；不等于正式持续消费；后续3f查询已另有直接验收。

## 证据和维护

[21脱敏只读清单](evidence/deployment-docs-20261115-01/runtime.json)保存服务身份、端口、挂载、资源上限及非秘密配置；[本轮候选](evidence/streaming-candidate-20261115-01/README.md)保存实际包/镜像及待就绪项。没有读取密码、私钥或输出完整环境。

本页整理前内容已按原字节保存在[历史快照](../handoff/history/2026-11-15-deployment-docs/README.md)。其中旧日期、旧数据库、29表462列和A/I分步状态均不作为当前操作入口。正式结构以[数据库当前入口](../../deploy/database/CURRENT.md)及实际发布回执为准，本轮130/131只在隔离库验证，未正式应用。

### 湖3f查询profile与读取入口

[候选查询配置](../../deploy/aisoc21/lake-query-3f/README.md)通过`SOCAI2_LAKE_QUERY_PROFILE_FILE`显式选择来源/租户/映射、分页、窗口、字节及transport限制，数据库须与`CLICKHOUSE_DATABASE`一致。HTTP及内部C4 v2共用配置；新增来源/时间浏览、可选角色host/IP及完整材料读取。缺配置不回落，旧v1冻结绑定保持可识别。[3f回执](evidence/lake-query-3f-20261119-01/README.md)记录同批真实只读验证，当前候选82操作、正式80操作及48列表未变。

### 4a已有告警选择与私有只读报告

[选择profile与运行方式](../../deploy/aisoc21/lake-alert-selection-4a/README.md)当前为v2：identity_scope=global、alert_lifecycle=immutable、identity_scope_paths=[]，各规则identity_path=metadata.uid、identity_semantics_confirmed=true，依据负责人已确认的全局唯一且无更新合同；租户/来源仍限定读取归属。is_alert只接受boolean；同ID异文待核，普通日志不受选择影响。只读程序不派发A/I。[4a回执](evidence/lake-alert-selection-4a-20261119-03/README.md)保留原配置；4b另以显式initial_activity_ids支持不可变来源的Unknown/Create/Other首次接收，不改写原活动值。

### 4b首次告警接收与材料读取

[接收profile与接线](../../deploy/aisoc21/lake-alert-receive-4b/README.md)明确PG库、来源、投影、接收/快照预算与初诊登记参数；LakeAlertReceiver与Socai2AlertSink参数须一致。当前示例正文信封32MiB、快照64MiB，超预算hold，不截断原文；旧非湖路径仍默认1MiB。新湖快照采用v2数值摘要，旧v1保留原算法。材料ContentView及既有HTTP路径保持，完整Kafka OCSF与可选raw_data各按原合同读取。[真实湖→隔离PG→HTTP回执](evidence/lake-alert-receive-4b-20261119-03/README.md)已通过，初诊只accepted；后续4c见下，正式发布尚未执行。

### 4c湖告警持久交付

[delivery与连接配置](../../deploy/aisoc21/lake-alert-delivery-4c/README.md)驱动独立worker，显式给出开关、轮询、每轮交付上限、超时、Fusion参数和PG/CH/Redis连接。沿selection的有界完整扫描，131持久保存全部去向及逐次接收结果；同源锁串行，4b及确认事务提交后才推进。失败/unknown停止退出，旧receiving/unknown先只读核130回执，无证明不自动重执行。示例默认禁用，候选compose不自动重启；规则或接收配置变更拒绝覆盖旧绑定。当前[真实CLI/PG/HTTP及合成边界回执](evidence/lake-alert-delivery-4c-20261119-01/README.md)通过，正式持续进程未启用。

## 严重程度和优先级（S1 候选）

新事件及 Case 创建使用 `SOCAI2_SUBJECT_RISK_CONFIG_FILE` 显式绝对路径，示例 [subject-risk.json](../../deploy/local-investigation/subject-risk.json)。版本、未知初始等级和五档整数 0–100 映射由配置提供；保存时冻结所选版本和完整映射，GET 不重算旧状态。Fusion、HTTP 创建和可分配续案的 dispatcher 需要同版配置；合入方式见[清单](../../deploy/local-investigation/subject-risk-release-fragment.json)，不是现有线上环境已切换的声明。

## 调查异常文件日志（S6候选）

配置入口为[日志模板](../../deploy/local-investigation/operational-logging.example.json)和[HTTP配置字典](../../deploy/http-service/CONFIGURATION.md#文件日志候选配置s6)。dispatcher显式指定`logging_profile_file`；API/Fusion环境文件指定`SOCAI2_LOGGING_PROFILE_FILE`。目录/级别/JSON格式/轮转大小和份数由文件加载，按服务/实例/PID分文件；容器profile只读、日志目录持久可写。新装/升级清单在[S6片段](../../deploy/local-investigation/operational-logs-release-fragment.json)。

本步只完善运行异常记录，不新增业务接口或业务数据脱敏，不改告警/事件/Case数据库合同；旧未选日志配置的服务仍只有控制台，不以候选代码代替实际落盘证据。
