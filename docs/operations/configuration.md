# 当前配置索引

更新于2026-11-15。部署统一从[全模块入口](../../deploy/README.md)开始；只说明当前目标版本，不把旧分阶段样例、已结束发布或开发默认作为另一套操作方案。

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
| 核心构建、处理profile、投影及传输 | [处理链](deployment-processing.md) | 当前candidate build/transport及production-profile模板 |
| 对外HTTP、读写连接、可信上下文、查询/任务策略 | [HTTP逐项表](../../deploy/http-service/CONFIGURATION.md) | 当前streaming候选profile及受控runtime JSON |
| Swagger | [Swagger](../../deploy/api-docs/README.md) | 同批OpenAPI、Compose及明确env |
| LiteLLM路由、模型上游、tokenizer、Token/时限、输入输出合同 | [模型](deployment-models.md) | compose.gateway、litellm.config、investigation-policy-case-v1及三份IO |
| Ollama嵌入、C2知识与Qdrant集合 | [知识](deployment-models.md) | compose.embedding、knowledge-profile.json |
| PG、Redis、Kafka、ClickHouse、Qdrant、Neo4j、OpenSearch | [数据湖与数据库](deployment-datastores.md) | 选定服务配置+模块连接profile；不以厂商默认替代实际配置 |
| PG新装/升级/普通运行角色 | [数据库当前入口](../../deploy/database/CURRENT.md)及[参数表](deployment-datastores.md) | reader-install及123–129增量，不改冻结V1 |
| UEBA、Enrichment、ThreatIntel、Actions及Agents保留开关 | [支持服务](deployment-support-services.md) | 当前各模块loader及受控env；未启功能不自动启用 |
| 测试账本/只读API | [测试服务](../../deploy/investigation-test/README.md) | read-only/upstream/viewer三份显式profile；W4包另用package-build.json及candidate-21.json，账本与配置外置 |
| Docker验收CLI | [专用镜像与挂载](../../deploy/investigation-test/acceptance-docker.md) | acceptance-image.json固定基础/平台/依赖；acceptance.env选择只读材料、只读配置、独立持久结果及网络/非root用户。profile.connection_files与嵌套secrets均为稳定容器路径；默认network=none，不联启业务服务 |
| 4177、展示预览 | [查阅模块](deployment-support-services.md#工作台测试api与swagger) | workbench-display-current.json为实际0.6.0/HTTP/空态清单；运行profile为release-4177.json；旧processing_audit_view.json只供离线归档 |

地址、端口和模型不是在业务代码里手工替换的常量；部署人员修改选定配置文件，启动器加载后核实际镜像/挂载/参数。默认值调整须区分模型调用时限、整Run预算、调度轮询和自动更新周期，不能把一个数同时套给各层。

## 证据和维护

[21脱敏只读清单](evidence/deployment-docs-20261115-01/runtime.json)保存服务身份、端口、挂载、资源上限及非秘密配置；[本轮候选](evidence/streaming-candidate-20261115-01/README.md)保存实际包/镜像及待就绪项。没有读取密码、私钥或输出完整环境。

本页整理前内容已按原字节保存在[历史快照](../handoff/history/2026-11-15-deployment-docs/README.md)。其中旧日期、旧数据库、29表462列和A/I分步状态均不作为当前操作入口。当前目标结构是32表521列；正式仍127后的28表450列，实际是否升级必须读回。
