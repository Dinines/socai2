# 支持服务与查阅模块配置

填写方式沿[四类配置标记](../../deploy/README.md#配置分四类)：保留默认仍须保留严格配置中的字段；“启用时必填”只在使用该依赖时准备；只读核对不要求填写。

2026-11-15。本页补齐UEBA、Enrichment、ThreatIntel、Actions、Agents保留开关及查阅模块。它们不是第二套调查执行流程；本轮告警/事件/Case统一由[联合调度器](deployment-processing.md)执行。参数来自当前源码loader；已经保留的服务不因本文自动启用新采集、自动响应或旧消费者。

下表“源默认”用于说明未配置行为，不能直接当成所选部署值。目标地址、端口、库、租户及开关须写入本轮env/profile文件。Python Settings和Go Config通常启动时加载，改文件后正常重启对应进程；不承诺热加载。敏感项只给字段名与用途。共享Compose的镜像、user、ports、env_file、volumes、networks、read_only、tmpfs、cpus、mem_limit、restart、healthcheck等含义见[统一部署入口](../../deploy/README.md)。

## UEBA：全部14项

来源：[core/config.py](../../services/ueba/app/core/config.py)。部署只写下列首选变量名，不并列配置loader接受的同义旧名字。

| 参数 | 类型/源默认 | 用途与必填条件 | 填写方式 |
| --- | --- | --- | --- |
| `DATABASE_URL` | 私密URL | 行为基线/异常结果的PG连接，服务启用时明确配置 | 启用时必填 |
| `KAFKA_BOOTSTRAP_SERVERS` | string | 消费及输出broker，启用时必填；TLS字段见[Kafka说明](deployment-datastores.md) | 启用时必填 |
| `KAFKA_INPUT_TOPIC` | string，aisoc.raw_events | 行为原始事件输入；本次21观察为socai2.raw_events.v1 | 启用时必填 |
| `KAFKA_OUTPUT_TOPIC` | string，ueba.anomalies | 异常输出；21观察为socai2.ueba.anomalies.v1 | 启用时必填 |
| `KAFKA_CONSUMER_GROUP` | string，ueba-service | 独立消费位点；21观察为socai2.ueba.v1 | 启用时必填 |
| `BASELINE_WINDOW_DAYS` | int，30天 | 建立行为基线的时间范围；不等于调查活动窗口 | 保留默认 |
| `ANOMALY_THRESHOLD` | float，3 | 异常评分阈值 | 保留默认 |
| `PEER_GROUP_MIN_SIZE` | int，3 | 同类群体对比最少成员 | 保留默认 |
| `MIN_BASELINE_SAMPLES` | int，30 | 建立可用基线的最少样本 | 保留默认 |
| `SCORING_BATCH_SIZE` | int，100 | 一批评分最多输入条数 | 保留默认 |
| `OTEL_ENDPOINT` | URL，源localhost:4317 | 追踪采集端；未供给时显式决定是否使用 | 启用时必填 |
| `SERVICE_NAME` | string，aisoc-ueba | 观测服务名称 | 保留默认 |
| `HOST` | string，0.0.0.0 | 应用监听地址；Compose显式uvicorn命令优先核实际启动参数 | 启用时必填 |
| `PORT` | int，8004 | 应用端口；宿主18006映射是另一个配置 | 启用时必填 |

“调查读取UEBA上下文”“Fusion把UEBA加进评分”“UEBA消费原始事件”是三处独立配置，不可由任意一个开关推断另外两个已启用。实际查询来源与tenant/对象/时间应在同批验收读回。

## Enrichment：全部30项

来源：[config.go](../../services/enrichment/internal/config/config.go)。全部由受控env文件注入；外部provider只有实际配置且允许访问时才可用，空key不表示已查询。当前源码对整数解析采用`Atoi`，部署应填写合法整数，不能依赖无效字符串的回落。

| 参数 | 类型/源默认 | 用途 | 填写方式 |
| --- | --- | --- | --- |
| `HTTP_PORT` | string，8082 | HTTP监听端口 | 保留默认 |
| `REDIS_URL` | 私密URL | enrichment缓存连接；21观察DB12，不是默认localhost/1 | 启用时必填 |
| `CACHE_TTL_SECONDS` | int，3600秒 | 缓存有效期 | 保留默认 |
| `CACHE_MAX_MEMORY` | string，256mb | 当前Config读取但服务未使用，修改不会改变Redis或容器内存额度 | 保留默认（当前未接线） |
| `RATE_LIMIT_RPS` | int，100 | 当前Config读取但服务未使用，不宣称实际限速已生效 | 保留默认（当前未接线） |
| `RATE_LIMIT_BURST` | int，50 | 当前Config读取但服务未使用，不宣称实际突发限速已生效 | 保留默认（当前未接线） |
| `LOG_LEVEL` | string，info | 日志等级 | 保留默认 |
| `ABUSEIPDB_API_KEY` | 私密字符串，空 | AbuseIPDB凭据 | 启用时必填 |
| `VIRUSTOTAL_API_KEY` | 私密字符串，空 | VirusTotal凭据 | 启用时必填 |
| `SHODAN_API_KEY` | 私密字符串，空 | 当前仅Config加载，未接到本服务provider；本轮无需填写 | 保留默认（当前未接线） |
| `GREYNOISE_API_KEY` | 私密字符串，空 | GreyNoise凭据 | 启用时必填 |
| `URLSCAN_API_KEY` | 私密字符串，空 | 当前仅Config加载，未接到本服务provider；本轮无需填写 | 保留默认（当前未接线） |
| `IPINFO_API_KEY` | 私密字符串，空 | 当前仅Config加载，未接到本服务provider；本轮无需填写 | 保留默认（当前未接线） |
| `CYBLE_API_KEY` / `CYBLE_BASE_URL` | 私密字符串/URL，空 | Cyble账号及服务地址，启用该provider时明确提供 | 启用时必填 |
| `RECORDED_FUTURE_API_KEY` | 私密字符串，空 | Recorded Future凭据 | 启用时必填 |
| `MANDIANT_API_KEY` / `MANDIANT_API_SECRET` | 私密字符串，空 | Mandiant凭据对 | 启用时必填 |
| `ANOMALI_USERNAME` / `ANOMALI_API_KEY` / `ANOMALI_BASE_URL` | 账号/私密值/URL，空 | Anomali连接 | 启用时必填 |
| `XFORCE_API_KEY` / `XFORCE_API_PASSWORD` | 私密字符串，空 | X-Force凭据对 | 启用时必填 |
| `FLASHPOINT_API_KEY` | 私密字符串，空 | Flashpoint凭据 | 启用时必填 |
| `INTEL471_USERNAME` / `INTEL471_API_KEY` | 账号/私密值，空 | Intel471连接 | 启用时必填 |
| `DOMAINTOOLS_USERNAME` / `DOMAINTOOLS_API_KEY` | 账号/私密值，空 | DomainTools连接 | 启用时必填 |
| `RISKIQ_USERNAME` / `RISKIQ_API_KEY` | 账号/私密值，空 | RiskIQ连接 | 启用时必填 |
| `CROWDSTRIKE_INTEL_CLIENT_ID` / `CROWDSTRIKE_INTEL_CLIENT_SECRET` | 账号ID/私密值，空 | CrowdStrike情报连接 | 启用时必填 |

上述key仅说明配置位置，不授权实际请求外部厂商。当前调查的工具权限和来源仍按所选策略限定；服务可达但没provider结果不能报告已有情报命中。

## ThreatIntel：当前配置

来源：[app/config.py](../../services/threatintel/app/config.py)。数据库服务本身配置见[数据存储](deployment-datastores.md)；此处为该模块的客户端及采集间隔。

| 参数 | 类型/源默认 | 用途与边界 | 填写方式 |
| --- | --- | --- | --- |
| `APP_NAME` / `VERSION` / `ENVIRONMENT` | string，AiSOC ThreatIntel/0.1.0/development | 进程身份及环境；部署明确production | 保留默认 |
| `AISOC_THREATINTEL_SERVICE_TOKEN` | 私密字符串，空 | Actor HTTP内部调用凭据；与对外调查HTTP可信模式不同 | 启用时必填 |
| `REDIS_URL` | 私密URL | 去重Bloom及缓存连接 | 启用时必填 |
| `BLOOM_CAPACITY` | int，10000000 | 当前Settings值未传入Bloom构造器，修改不会改变实际容量；不代表Redis磁盘容量 | 保留默认（当前未接线） |
| `BLOOM_ERROR_RATE` | float，0.001 | 当前Settings值未传入Bloom构造器，修改不会改变实际误判率；不是模型准确率 | 保留默认（当前未接线） |
| `OPENSEARCH_HOST` / `OPENSEARCH_PORT` | string/int，源opensearch/9200 | 情报索引服务；当前网络目标spirithub-opensearch-1 | 启用时必填 |
| `OPENSEARCH_USER` / `OPENSEARCH_PASSWORD` | 账号/私密值，空 | 服务要求认证时提供 | 启用时必填 |
| `OPENSEARCH_INDEX_IOC` / `OPENSEARCH_INDEX_ACTOR` | string | IOC与Actor索引；21观察socai2-threatintel-iocs/actors | 启用时必填 |
| `QDRANT_HOST` / `QDRANT_PORT` | string/int，源qdrant/6333 | 情报向量服务，不是embedding地址 | 启用时必填 |
| `QDRANT_API_KEY` | 私密字符串，空 | 向量访问凭据 | 启用时必填 |
| `QDRANT_COLLECTION_IOC` / `QDRANT_COLLECTION_ACTOR` | string | 两类情报集合，不与调查知识集合混用 | 启用时必填 |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | URI/账号/私密值 | 情报图连接；部署不能使用源码演示密码 | 启用时必填 |
| `KAFKA_BOOTSTRAP_SERVERS` | string | 情报输出broker；21当前为空，不由其他模块的Kafka可达推断已输出 | 启用时必填 |
| `KAFKA_TOPIC_THREAT_INTEL` | string，aisoc.threat_intel | 情报消息输出Topic | 启用时必填 |
| `KAFKA_TOPIC_IOC` | string，aisoc.ioc_enrichments | IOC富化消息输出Topic | 启用时必填 |
| `TAXII_URL` / `TAXII_API_ROOT` | URL/string，空 | TAXII服务及API根路径 | 启用时必填 |
| `TAXII_USERNAME` / `TAXII_PASSWORD` | 账号/私密值，空 | TAXII认证 | 启用时必填 |
| `TAXII_COLLECTION_IDS` | 逗号分隔string，空 | 采集集合ID，不是Qdrant集合 | 启用时必填 |
| `MISP_URL` / `MISP_API_KEY` | URL/私密值，空 | MISP采集连接 | 启用时必填 |
| `MISP_VERIFY_SSL` | bool，true | MISP TLS校验，不通过关闭它修复证书配置 | 保留默认 |
| `OTX_API_KEY` / `OTX_BASE_URL` | 私密值/URL | OTX凭据与目标；是否出网由环境限制 | 启用时必填 |
| `CISA_KEV_URL` | URL | CISA KEV源，可在所选环境明确使用适用镜像地址 | 启用时必填 |
| `OPENCTI_URL` / `OPENCTI_TOKEN` | URL/私密值，空 | OpenCTI连接 | 启用时必填 |
| `OPENCTI_VERIFY_SSL` | bool，true | OpenCTI TLS校验 | 保留默认 |
| `TAXII_POLL_INTERVAL` | int，900秒 | TAXII轮询间隔 | 保留默认 |
| `MISP_POLL_INTERVAL` | int，1800秒 | MISP轮询间隔 | 保留默认 |
| `OTX_POLL_INTERVAL` | int，1800秒 | OTX轮询间隔 | 保留默认 |
| `OPENCTI_POLL_INTERVAL` | int，1800秒 | OpenCTI轮询间隔 | 保留默认 |
| `CISA_KEV_POLL_INTERVAL` | int，86400秒 | CISA轮询间隔；本部署只配置这一名称，不使用旧CISA_POLL_INTERVAL别名 | 保留默认 |
| `AISOC_AIRGAPPED` | bool，源false、所选环境明确 | 限制外部feed注册/请求 | 保留默认 |
| `AISOC_AIRGAP_ALLOWLIST` | string数组 | 允许的目标，开启内网限制时应包含实际需要的内部依赖 | 启用时必填 |

这些服务的轮询不是Case自动调查轮询。没有新情报源准备/采集回执，不声称自动消费已启用。

## Actions：全部14项Settings及连接

来源：[ActionsSettings](../../services/actions/app/core/config.py)。本轮不执行响应动作，不因调查模型提出建议而实际封禁、发信、删邮件。该模块保留自己的内部调用配置，不复用调查HTTP的运行身份。

| 参数 | 类型/源默认 | 用途与必填条件 | 填写方式 |
| --- | --- | --- | --- |
| `AISOC_API_BASE_URL` | URL，源http://aisoc-api:8000 | 回写适用业务API的地址 | 启用时必填 |
| `AISOC_API_SERVICE_TOKEN` | 私密字符串，空 | Actions调用业务API凭据 | 启用时必填 |
| `AISOC_CREDENTIAL_KEY` | 私密字符串，空 | 解密vault:v1内容需要的Fernet key | 启用时必填 |
| `AISOC_CREDENTIAL_KEY_ROTATION_FROM` | 私密逗号列表，空 | 读取历史加密数据的轮换旧key | 启用时必填 |
| `AISOC_FEATURE_CHATOPS_VERIFY` | bool，true | 交互核实能力开关；本轮不触发 | 保留默认 |
| `AISOC_FEATURE_MAILBOX_REMEDIATION` | bool，false | 邮件修复动作开关，保持原边界 | 保留默认 |
| `AISOC_CHATOPS_RESPONSE_SECRET` | 私密字符串，空 | 回调令牌HMAC签名 | 启用时必填 |
| `AISOC_CHATOPS_TIMEOUT_SECONDS` | int，900秒 | 核实提示有效时间 | 保留默认 |
| `AISOC_ACTIONS_PUBLIC_URL` | URL，源http://localhost:8003 | 回调链接中的可访问地址 | 启用时必填 |
| `AISOC_ACTIONS_SERVICE_TOKEN` | 私密字符串，空 | 调用Actions写操作的凭据，与API_SERVICE_TOKEN用途不同 | 启用时必填 |
| `AISOC_DEV_MODE` | bool，false | 开发模式；正式不启 | 保留默认 |
| `AISOC_ACTIONS_REQUIRE_PRINCIPAL` | bool，false | 动作请求是否必须带身份 | 保留默认 |
| `AISOC_ACTIONS_REQUIRE_APPROVER` | bool，true | 审批是否必须有可解析审批人 | 保留默认 |
| `AISOC_CHATOPS_APPROVERS` | JSON字符串或`file:`路径，空 | 平台用户到审批身份的映射，不由模型生成 | 启用时必填 |
| `DATABASE_URL` / `REDIS_URL` | 私密URL | 已部署模块持久状态/缓存连接，由实际env文件明确，Settings表之外的服务依赖 | 启用时必填 |

## Agents保留状态

当前自动分诊入口在统一调度，Agents旧Kafka消费者保持`AISOC_AGENT_KAFKA_DISABLE=1`。21只读清单已核该值。不要同时启两套消费者分析同一告警；不将旧worker的模型重试/补偿参数重新列为本轮操作路径。

当前保留启动开关包括`AISOC_PLAYBOOK_SEED_DISABLE`（禁自动播种）、`AISOC_ATTCK_STARTUP_DISABLE`（禁启动ATT&CK导入）、`AISOC_ATTCK_INDEX_DISABLE`（禁启动向量索引）、`AISOC_HUNT_SCHEDULER_DISABLE`（禁旧狩猎调度）。它们为字符串布尔配置，需根据保留服务的已选env明确设置；不要仅因连接了Qdrant/OpenAI就让启动过程生成新索引。`DATABASE_URL`、`REDIS_URL`及服务网络沿明确保留配置，不用于当前A/I/Case调度器。

## 工作台、测试API与Swagger

新测试服务唯一入口为[deploy/investigation-test/README.md](../../deploy/investigation-test/README.md)，列全只读账本、调查上游、页面配置及CLI。W1账本/8个GET、W2只读代理、W3页面及[W4完整包0.4.0](evidence/streaming-w4-package-20261116-01/README.md)已按各自范围验证；W4还提供package-build.json与candidate-21.json，配置和账本外置，21回环18477候选经35GET及一次重启后正常停止。W5已切到实际4177/0.6.0；按负责人授权清理后账本为空，新数据未投递。Swagger部署全部参数见[deploy/api-docs/README.md](../../deploy/api-docs/README.md)，业务HTTP配置见[deploy/http-service/README.md](../../deploy/http-service/README.md)。

[processing_audit_view.json](processing_audit_view.json)只控制查阅呈现：

| 字段 | 类型/当前值 | 含义 | 填写方式 |
| --- | --- | --- | --- |
| `preview_characters` | int，6000 | 页面正文预览字符数；不截断PG原件，不限制模型输入 | 保留默认 |
| `local_preview.host` | string，127.0.0.1 | 独立预览绑定地址 | 保留默认 |
| `local_preview.port` | int，4178 | 独立预览端口，不修改实际4177 | 保留默认 |

[workbench-display-current.json](../../deploy/aisoc21/workbench-display-current.json)是**已部署展示状态清单**：`mode=live_http`、`read_only=true`、`database_url`为空，通过同源代理读调查HTTP及测试账本。实际0.6.0/4177运行、活动批次为0；`runtime_source/deployment_root/state_root`定位已冻结包与包外状态，`receipt/http_receipt/data_reset_receipt`追溯部署、读取与清理。它不是运行profile；运行参数用[release-4177.json](../../deploy/investigation-test/release-4177.json)。旧静态导出不作为当前展示数据，不能从清理备份自动恢复。

本轮所有模块验收均应记录代码/配置身份、实际输入和读回。支持服务的健康探针只说明进程或特定依赖，不替代Kafka告警→事件→调查及HTTP/展示的同批整体验收。
