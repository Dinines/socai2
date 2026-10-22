# v1 连接与配置交接

[返回入口](README.md)。2026-10-22。基础设施地址由16:02白名单核对，v1.0.0发布后16:48再次采集[实际配置快照](service-runtime-snapshot.json)。15个选定容器running，7个业务服务healthy；仅API/Agents镜像改变，其他13个选定容器配置与镜像保持。业务验证、生产tenant/凭据/预算和切换offset见[生产接入](production.md)。[发布前快照](runtime-snapshot.json)及最初SSH超时保留为历史。

## 1. 基础设施连接表

| 服务 | 项目连接地址 / 协议 | 数据对象与用户名 | 配置变量 | 凭据/运行依据 |
| --- | --- | --- | --- | --- |
| Kafka | `192.168.1.21:19093`，SSL，CA及IP/主机名校验 | raw/fused/事件/异常5个topic，详见Kafka篇 | `KAFKA_BOOTSTRAP_SERVERS/KAFKA_SECURITY_PROTOCOL/KAFKA_SSL_CAFILE` | 21 `certificates/socai2-ca.crt`；当前SSL不等于客户端认证/Topic ACL |
| PostgreSQL | `192.168.1.21:5432/aisoc`，TLS verify-full | runtime=`aisoc_app`，owner=`aisoc`仅迁移 | `DATABASE_URL/PGSSLROOTCERT`；libpq可用`sslmode=verify-full` | `private/runtime.env`、API/Fusion/Agents各env；不是历史sting库/角色，也不是旧15432说明 |
| Redis | `192.168.1.21:6379`，当前`redis://`，ACL账号 `socai2` | API DB8、Fusion DB9、Agents DB10、Actions DB11；enrichment和TI当前均DB12 | 每个服务分别设置`REDIS_URL` | `private/shared-services.json`与各服务env；分配按实际URL；TI/enrichment当前共用DB12，不能宣称全部隔离 |
| OpenSearch | 宿主`http://192.168.1.21:9200`；TI用`spirithub-opensearch-1:9200`，通过`spirithub_default`网络 | `socai2-threatintel-iocs`、`socai2-threatintel-actors` | TI：`OPENSEARCH_HOST/PORT/USER/PASSWORD/INDEX_IOC/INDEX_ACTOR`；API另有`OPENSEARCH_URL` | 当前现有入口无认证；本轮核TI主机和索引；宿主地址/容器DNS按所在网络选择 |
| ClickHouse | HTTP `192.168.1.21:8123`、native `192.168.1.21:9000`；API/Fusion生效HOST均为该IP | DB=`aisoc`，项目用户=`socai2_lake` | `CLICKHOUSE_HOST/PORT/DATABASE/USER/PASSWORD`；两个服务`AISOC_DISABLE_CLICKHOUSE=false`等实际开关各异 | `private/full-support-20261021/lake.env`；已核HOST/9000/aisoc/socai2_lake，密码仍走受控文件 |
| Neo4j | `bolt://192.168.1.21:7687`，管理Web7474 | 用户`neo4j`；节点按tenant，Technique共享 | `NEO4J_URI/USER/PASSWORD`；API`AISOC_DISABLE_NEO4J=false` | `private/full-support-20261021/graph.env`；身份专用config另有database字段；当前未新增Bolt TLS |
| Qdrant | `http://192.168.1.21:6333`，gRPC6334，API key | TI集合`socai2_threatintel_iocs/actors`，1536维 | API：`QDRANT_URL/QDRANT_API_KEY`；TI：`QDRANT_HOST/PORT/API_KEY/COLLECTION_IOC/COLLECTION_ACTOR` | `private/vector-1d.env`及TI env；0.6B/1024维验证集合与TI1536维不同，不可混用 |

本轮确认TI与enrichment的REDIS_URL均指向DB12；保留这个共享事实，不在文档梳理中改DB或执行清理。对外业务查询优先走API，后端不依赖Redis内部key作持久合同。[配置历史及生效层](../../operations/configuration.md)、[full净化运行回执](../../operations/full-support-migration.json)

ClickHouse项目账号在full阶段单独创建；本轮从API/Fusion生效env核到了相同HOST/PORT/DB/USER。密码不公开，元数据核对不等于重新执行了湖查询。

## 2. 应用服务地址与使用者

这些宿主端口只绑定 **21本机127.0.0.1**；其他机器的127.0.0.1不是21。容器内使用同网络服务DNS；部署外后端使用已配置代理或受控SSH转发。

| 服务 | 21本机 | 同项目网络 | 后端使用方式 |
| --- | --- | --- | --- |
| API | `http://127.0.0.1:18000` | `http://api:8000` | `/api/v1/alerts`、`/cases`、`/investigations`等业务查询主入口 |
| Fusion | `http://127.0.0.1:18003` | `http://fusion:8003` | Kafka处理服务；同步process/HTTP告警仅辅助测试，不代替正式Kafka接入 |
| Agents | `http://127.0.0.1:18004` | `http://agents:8084` | 编排及原服务结果接口；通过API代理/账本读者优先 |
| Actions | `http://127.0.0.1:18005` | `http://actions:8085`，见[1G Compose](../../../deploy/aisoc21/compose.investigation.yml) | 调查建议不是执行结果；真实动作仍需受控目标/审批 |
| enrichment | `http://127.0.0.1:18002` | `http://enrichment:8082` | IOC只读增强；没有provider来源不能把0分解释成安全 |
| UEBA | `http://127.0.0.1:18006` | `http://ueba:8004` | 基线/异常读取；Agents使用`AISOC_UEBA_URL/AISOC_UEBA_SERVICE_TOKEN` |
| ThreatIntel | `http://127.0.0.1:18008` | `http://threatintel:8005` | TI服务及OS/Qdrant；API使用`THREATINTEL_SERVICE_URL/AISOC_THREATINTEL_SERVICE_TOKEN` |

例如在工作站建立API通道（示例未执行）：

```sh
ssh -N -o ExitOnForwardFailure=yes -L 18000:127.0.0.1:18000 sting-infra21
```

Kafka必须能访问broker广告地址；单把bootstrap转发为localhost不保证后续分区连接和证书校验成功。不要关闭CA/hostname校验来配合转发。

## 3. 生产者和服务配置怎样区分

正式外部生产者只需要Kafka TLS配置、raw topic及租户/来源映射；它不用数据库密码或模型key。配置例见[kafka-client.env.example](examples/kafka-client.env.example)。其中`STINGAISOC_*`是对接程序示例参数，现有服务不会自动读取它们。

原服务各自读取如下真实变量；以下是模板，`__...__`必须由受控配置提供，不是一份可直接source的整栈env：

```dotenv
# API / Fusion 使用 SQLAlchemy asyncpg DSN；Agents可使用原postgresql DSN
DATABASE_URL=postgresql+asyncpg://aisoc_app:__ISSUED_URLENCODED_PASSWORD__@192.168.1.21:5432/aisoc?ssl=verify-full
PGSSLROOTCERT=/run/certs/ca.crt
# 每个进程只设置自己的REDIS_URL；下面例子是Fusion DB9
REDIS_URL=redis://socai2:__ISSUED_URLENCODED_PASSWORD__@192.168.1.21:6379/9
KAFKA_BOOTSTRAP_SERVERS=192.168.1.21:19093
KAFKA_SECURITY_PROTOCOL=SSL
KAFKA_SSL_CAFILE=/run/certs/ca.crt
KAFKA_TOPIC_ALERTS_RAW=socai2.alerts.raw
KAFKA_TOPIC_ALERTS_FUSED=socai2.alerts.fused
KAFKA_CONSUMER_GROUP=socai2-fusion-consumer
```

当前API/Fusion生效DSN带`sslmode=verify-full`：API连接层将其转成asyncpg的`ssl`参数；Fusion去除SQLAlchemy驱动后缀后交原生asyncpg解析DSN，Agents也用原生asyncpg；UEBA生效DSN直接使用`ssl=verify-full`。libpq/psql使用`postgresql://`与`sslmode`，不能直接使用`postgresql+asyncpg`。CA是接收机器上的挂载路径，不是远端路径自动可用。

| 服务 | 除基础连接外的当前配置/位置 | 要点 |
| --- | --- | --- |
| Fusion | `KAFKA_CONSUMER_GROUP=socai2-fusion-consumer`；`KAFKA_TOPIC_RAW_EVENTS=socai2.raw_events.v1`；`KAFKA_TOPIC_UEBA_ANOMALIES=socai2.ueba.anomalies.v1` | 入湖full已接，`AISOC_UEBA_FUSION_ENABLED=false`仍保持；直接Kafka的source-v1字段由生产者设置 |
| Agents | `KAFKA_CONSUMER_GROUP=socai2-agents-v1-prod-20261022`，DLQ回退为`socai2.alerts.fused.dlq`；`AISOC_AGENT_KAFKA_DISABLE=0` | `AISOC_AGENT_ESCALATE_TO_GRAPH=1`、`AISOC_INVESTIGATE_USE_ROUTER=0`、profile=`legacy`；`AISOC_ATTACK_CONTEXT_ENABLED=true`，原持久/预算/unknown保护保持 |
| UEBA | `KAFKA_INPUT_TOPIC=socai2.raw_events.v1`、`KAFKA_OUTPUT_TOPIC=socai2.ueba.anomalies.v1`、group=`socai2.ueba.v1` | 自己的PG迁移；输入是事件，不是RawAlert |
| API/Fusion湖 | `CLICKHOUSE_PORT=9000/CLICKHOUSE_DATABASE=aisoc/CLICKHOUSE_USER=socai2_lake` | 已核HOST=192.168.1.21，PASSWORD取lake.env；HTTP8123与native9000不要互换 |
| TI OpenSearch | `OPENSEARCH_INDEX_IOC=socai2-threatintel-iocs`、`OPENSEARCH_INDEX_ACTOR=socai2-threatintel-actors` | 已核HOST=spirithub-opensearch-1、PORT=9200；既有airgap/Feed0事实保持，非原始日志全文索引 |
| TI Qdrant | `QDRANT_COLLECTION_IOC=socai2_threatintel_iocs`、`QDRANT_COLLECTION_ACTOR=socai2_threatintel_actors` | 1536维配置不证明已有真实向量或完整RAG |

## 4. 凭据与完整运行配置从哪里交接

21基目录：`/opt/sting-aisoc-socai2/`。`private/`为受控配置，`certificates/socai2-ca.crt`为发放的CA公证书。后端查询使用单独发放、绑定tenant及权限的Bearer；不要复用已撤销测试key、owner数据库角色或内部通用服务token。

| 用途 | 21现有受控文件 |
| --- | --- |
| PG/Redis基本配置 | `private/shared-services.json`、`private/runtime.env`、`api-1f.env/fusion-1f.env/agents-1g.env/actions-1g.env` |
| 湖/图 | `private/full-support-20261021/lake.env`、`graph.env` |
| UEBA/Agents消费上下文 | `private/ueba.env`、`private/agents-ueba.env` |
| enrichment | [compose.enrichment.yml](../../../deploy/aisoc21/compose.enrichment.yml)的env_file |
| TI及API代理 | `private/threatintel-full-20261021.env`、`private/full-threatintel-20261021/api-threatintel.env` |
| 模型网关/只读工具身份/租户reader | [配置索引](../../operations/configuration.md)及[工具使用](../../operations/investigation-tools.md)中的专用只读挂载 |

早期env后还有Compose/后续env_file覆盖，不应只source旧1G文件恢复整套服务。完整运行叠加顺序沿[21部署说明](../../../deploy/aisoc21/README.md)，本包不另造精简Compose或执行重建。用户名/库名可以写入此表，密码、token、CA私钥只通过受控文件交接。

## 5. 当前调用接线与服务地址的区别

v1.0.0将Agents的`ENRICHMENT_SERVICE_URL`由禁用目标改为`http://enrichment:8082`，新Run实际处理2个IOC；无恶意命中不证明良性。Fusion的该URL仍为空。Agents的`AISOC_UEBA_URL=http://ueba:8004`、API的`THREATINTEL_SERVICE_URL=http://threatintel:8005`保持；新Run的UEBA读取失败、Agents TI归因401仍需按来源不可用处理，不能由容器healthy宣称全部调用成功。

Kafka worker真实变量是`AISOC_AGENT_KAFKA_DISABLE`：当前0开启，1关闭；`AISOC_TRIAGE_WORKER_ENABLED`不是当前worker_enabled函数读取的开关，勿依赖该名字配置常驻消费。源码见[worker_enabled](../../../services/agents/app/workers/fused_alert_consumer.py)、[IOC调用者](../../../services/agents/app/investigator/tools.py)、[API DSN归一化](../../../services/api/app/db/database.py)。
