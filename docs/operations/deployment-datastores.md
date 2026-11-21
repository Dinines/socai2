# 数据湖与数据库部署、配置说明

填写方式沿[四类配置标记](../../deploy/README.md#配置分四类)：保留默认仍须保留严格配置中的字段；“启用时必填”只在使用该依赖时准备；只读核对不要求填写。

更新于2026-11-15。本页解释本项目使用的存储及其连接配置，配合[统一部署入口](../../deploy/README.md)、[处理链配置](deployment-processing.md)和[模型与知识配置](deployment-models.md)使用。部署按本轮目标配置选择一条路径；运行观察只用于核对实际差异，不是另一套安装方案。

## 存储职责与实际位置

下表是[2026-11-15只读运行清单](evidence/deployment-docs-20261115-01/runtime.json)的观察值。容器运行、端口可达不代表业务已启用。第11步新库、Topic、账号和运行连接仍待准备；不得把正式`aisoc`当作独立验收库。

| 存储 | 用途、主要使用者 | 21观察到的服务与入口 | 持久目录（容器内） |
| --- | --- | --- | --- |
| PostgreSQL 16.15 | 告警、事件、Case、任务/执行/原件索引；核心和HTTP | `spirithub-postgres-1`；应用连接`192.168.1.21:5432`，容器没有直接发布5432，不能据此删掉既有转发入口 | `/var/lib/postgresql/data`，具名卷`spirithub_postgres-data` |
| Redis 7 | Fusion去重/关联缓存、内部调度task/pending及运行集合；其他模块缓存 | `sting-infra21-redis-1`，`192.168.1.21:6379` | `/data`，具名卷`sting-infra21_redis` |
| Kafka（镜像cp-kafka 7.5.0） | 输入告警/原始事件、归并输出；消费组记录位点 | `sting-infra21-kafka-1`。21 的 Fusion 和 UEBA 使用同机 `kafka:29092`，共享 TLS 监听为 `192.168.1.21:19093` | `/var/lib/kafka/data`，具名卷`sting-infra21_kafka` |
| ClickHouse 23.8 | 数据湖：原始事件及调查日志补查；Fusion写、调查读 | `sting-infra21-clickhouse-1`；Native `9000`，HTTP `8123` | `/var/lib/clickhouse`，具名卷`sting-infra21_clickhouse` |
| Qdrant 1.7.0 | 向量检索；知识与情报使用各自collection | `sting-infra21-qdrant-1`；HTTP `6333`、gRPC `6334` | `/qdrant/storage`，具名卷`sting-infra21_qdrant` |
| Neo4j 5.15 Community | 图关系来源、情报图；调查图来源当前关闭 | `sting-infra21-neo4j-1`；Bolt `7687`、管理HTTP `7474` | `/data`，具名卷`sting-infra21_neo4j`；插件另挂`/plugins` |
| OpenSearch 2.15 | 情报IOC/Actor检索索引，不是调查主库或日志湖 | `spirithub-opensearch-1:9200`，仅容器网络，情报服务加入`spirithub_default` | `/usr/share/opensearch/data`，具名卷`spirithub_opensearch-data` |

数据库共享基础设施的定义来自21实际Compose（路径保存在运行清单），本仓库没有一份可覆盖全部共享数据库的总Compose。新部署应在所选环境明确准备这些依赖；不要执行参考工程Compose来重建已有基础设施，也不要根据历史端口自动回落到另一套Kafka或数据库。

## 配置装载与生效规则

1. 数据库服务端参数写在该服务的Compose、`postgresql.conf`/`redis.conf`/Kafka属性、ClickHouse XML等受控配置文件中；凭据进入私密文件。
2. 业务模块的连接地址、库名、角色、TLS和超时写在选定profile或其指定的私密env/URL文件中。进程读取环境变量是装载方式，部署值仍由文件提供，不能依赖操作者终端残留。
3. 调度器/连接池/模型等启动时加载的配置修改后，重启对应进程才生效。数据库参数按自身reload/restart规则执行；不能只改文档就认为运行值改变。
4. 必填表示“启用该依赖时必须提供”。示例值不是线上默认；实际值必须与本轮身份和资源清单一致。秘密只说明用途、来源和挂载位置，不在回执输出连接串、密码或API key。

## PostgreSQL

### 本轮认证口径

**目标部署只填写地址、端口、库名、用户名和密码；应用不配置CA、客户端证书或私钥。** `sslmode=require`由模板给定，一般不修改，用于保留数据库已有TLS；它不要求客户端校验服务器证书。密码仍通过私密URL文件或PGPASSFILE提供，文件只是保存密码的方式，不是额外密钥。

21 的独立 UEBA 实例使用账号密码和 `verify-full`。其 `PGSSLROOTCERT` 用于校验 PostgreSQL 服务端。2026-11-21 在同容器用现行 asyncpg 连接做只读核验，当前配置通过 TLS 和主机名校验。临时移除该变量后返回 `ClientConfigurationError`。[实测回执](evidence/c173-kafka-plaintext-20261121-01/README.md#postgresql-核验)

[本次只读认证核对](evidence/deployment-docs-20261115-01/pg-auth-readback.json)显示21应用网络规则为`host all all all scram-sha-256`，没有客户端证书要求；容器内local/回环维护连接另为trust，不能用维护免密码证明应用密码已验证。原已发布profile采用verify-full，负责人本轮要求取消客户端CA配置；修改后的目标尚未正式发布。服务端自己的TLS证书/私钥保留，Kafka的CA也不在此次调整范围。

### 数据库与角色

目标结构为迁移123–129及reader依赖：`socai2`业务Schema **32表521列**。正式21仍为127后的28表450列，不能用代码已经支持128/129来证明正式库已升级。版本、安装入口和增量顺序以[CURRENT.md](../../deploy/database/CURRENT.md)为准。

| 身份/参数 | 类型、必填 | 用途与配置要求 | 填写方式 |
| --- | --- | --- | --- |
| `database` / `postgres.database` | 非空标识符，必填 | 实际连接的数据库；候选为`socai2_streaming_20261115`，不是Schema名称 | 部署必填 |
| `admin_role` / `postgres.admin_user` | 角色名，安装时必填 | 创建/升级时的受控管理连接；不交给HTTP或模型执行器 | 部署必填 |
| `function_owner` | 角色名，必填 | reader函数的属主；按安装器验证选择，不能随意用HTTP账号替代 | 部署必填 |
| `reader_role` | 角色名，必填 | HTTP查询所需只读权限及函数执行；新表SELECT由增量入口补齐 | 部署必填 |
| `analysis.writer_role` / `postgres.processor_role` | 角色名，写功能必填 | Task、Run、结果及Case操作的普通运行角色 | 部署必填 |
| `analysis_ingress.role` / `postgres.ingress_role` | 角色名，入站时必填 | 告警/事件入站及初始任务登记；与分析执行的职责分开 | 部署必填 |
| `default_tenant` / `tenant_id` | UUID，必填 | 数据隔离与任务/主体范围；HTTP、入站、执行器及测试数据必须一致 | 部署必填 |

候选owner/reader/writer和tenant/actor的唯一命名见[identity.json](../../deploy/aisoc21/streaming-candidate-20261115-01/identity.json)。该文件描述目标身份，不创建数据库或用户，`credentials_created=false`时不能启动业务服务。

### 安装profile逐项

入口：[reader-install.example.toml](../../deploy/database/reader-install.example.toml)，加载器：[install_reader.py](../../deploy/database/install_reader.py)。所有值由选定文件明确提供；不把示例`replace_*`传入实际安装。

| 字段 | 类型/示例 | 含义、约束和生效 | 填写方式 |
| --- | --- | --- | --- |
| `database`、`admin_role`、`function_owner`、`reader_role` | string | 见角色表；安装前按显式目标核对 | 部署必填 |
| `transport` | string，`libpq` | 选择连接方式；同机容器入口可选加载器支持的`docker_socket`，不是自动环境回落 | 保留默认 |
| `psql_argv` | string数组，`["psql","-X","-w"]` | 可执行程序及固定参数；`-X`忽略个人psql配置，`-w`不交互索要密码；不放密码 | 保留默认 |
| `timeout_seconds` | 正整数，120秒 | 安装命令整体等待上限，不是模型或单条SQL预算 | 保留默认 |
| `environment.PGHOST` | string | 目标地址；经SSH转发时填写实际连接地址，不自动换目标 | 部署必填 |
| `environment.PGPORT` | 数字字符串，5432 | PostgreSQL入口端口，不是应用HTTP端口 | 部署必填 |
| `environment.PGSSLMODE` | string，`require` | 模板默认，账号密码认证并保留TLS，不要求客户端CA | 保留默认 |
| `environment.PGPASSFILE` | 私密文件路径 | libpq密码文件，权限0600；不要把密码放命令行或提交到Git | 部署必填 |
| `cleanup.lock_timeout_seconds` | 正整数，3秒 | 127清理/新装期间等锁上限；普通升级不隐含清理 | 保留默认 |
| `cleanup.statement_timeout_seconds` | 正整数，30秒 | 127操作单SQL限时 | 保留默认 |
| `analysis.lock_timeout_seconds` | 正整数，3秒 | 128/129增量等锁上限 | 保留默认 |
| `analysis.statement_timeout_seconds` | 正整数，30秒 | 128/129增量单SQL限时 | 保留默认 |
| `analysis_ingress.lock_timeout_seconds` | 正整数，3秒 | 入站授权/安装等锁上限 | 保留默认 |
| `analysis_ingress.statement_timeout_seconds` | 正整数，30秒 | 入站安装单SQL限时 | 保留默认 |

新专用**空库**用`initialize-current`；已有库依次用缺少的`analysis-lifecycle`、`case-allocation`增量，最后`verify`。三者都通过同一个`install_reader.py --profile <明确文件>`入口。空库初始化不得作用于已有业务库；不运行冻结V1安装器替代当前增量。

### 应用连接与查询限时

| 参数 | 类型/当前目标示例 | 用途 | 填写方式 |
| --- | --- | --- | --- |
| `DATABASE_URL` | 私密URL，必填 | 模块基础连接；驱动须匹配异步/同步调用，例如异步模块使用`postgresql+psycopg`或所选配置明确的`asyncpg`，不能机械互换 | 部署必填 |
| `SOCAI2_CASE_DATABASE_URL` | 私密URL，启用写操作时必填 | HTTP写侧独立连接；普通GET保持读侧连接，详见[HTTP部署](../../deploy/http-service/README.md) | 部署必填 |
| `SOCAI2_SERVICE_DATABASE_NAME` | string，必填 | 目标库身份核对值；必须等于实际连接库 | 部署必填 |
| `PGSSLMODE` | string，`require` | 保留默认TLS连接模式；不再设置PGSSLROOTCERT、PGSSLCERT或PGSSLKEY | 保留默认 |
| `DATABASE_POOL_SIZE` | int，处理profile示例2 | 进程连接池常驻额度；每个进程都有自己的池，不等于模型任务N | 保留默认 |
| `DATABASE_MAX_OVERFLOW` | int，示例1 | 超过池基础大小时的额外连接数；计算总连接数须乘进程数 | 部署必填 |
| `DATABASE_POOL_RECYCLE_SECONDS` | int，源默认300秒 | 连接回收周期；启动时装载 | 保留默认 |
| 调度`database_url_file` | 私密URL文件，必填 | 统一调度器读取连接；不是直接把URL写到公开JSON | 部署必填 |
| 调度`database_pool_size` | int，示例5 | 调度器池大小；实现固定`max_overflow=0` | 保留默认 |
| 调度`database_connect_args.sslmode` | string，`require` | 所选psycopg连接使用密码，无CA必填 | 保留默认 |
| 调度`database_connect_args.connect_timeout` | int，5秒 | 建立数据库连接的等待时间 | 保留默认 |
| 调度`database_connect_args.options` | string | 示例`-c statement_timeout=10000 -c lock_timeout=5000`，单位毫秒；限制运行SQL/锁等待，不是任务执行时限 | 保留默认 |

### 服务端运行参数

下列值来自本次管理连接的`pg_settings`；角色/会话可覆盖的值不代表每个应用会话相同。`postmaster`需重启服务，`sighup`可重载；会话参数应在应用连接中设置。参数范围及具体生效规则见[PostgreSQL 16配置说明](https://www.postgresql.org/docs/16/runtime-config.html)。

| 参数 | 本次观察 | 影响/单位 | 生效 | 填写方式 |
| --- | --- | --- | --- | --- |
| `data_directory` | `/var/lib/postgresql/data` | 持久数据目录；实际挂具名卷 | 重启 | 程序生成/只读核对 |
| `listen_addresses` / `port` | `*` / 5432 | 容器监听地址及端口；不等于宿主机公开映射 | 重启 | 程序生成/只读核对 |
| `max_connections` | 100 | 整个实例连接上限，各业务库共享 | 重启 | 程序生成/只读核对 |
| `shared_buffers` | 16384×8KiB=128MiB | PG共享缓冲区；不是整个容器内存额度 | 重启 | 程序生成/只读核对 |
| `work_mem` | 4096KiB | 每个排序/哈希操作的预算，不能直接当作全实例内存上限 | 会话/配置 | 程序生成/只读核对 |
| `maintenance_work_mem` | 65536KiB | 维护操作内存 | 会话/配置 | 程序生成/只读核对 |
| `max_wal_size` / `min_wal_size` | 1024 / 80MiB | WAL检查点相关预算，不是数据库大小上限 | 重载 | 程序生成/只读核对 |
| `wal_level` | `replica` | WAL记录级别 | 重启 | 程序生成/只读核对 |
| `archive_mode` | `off` | 本次未启WAL归档；不能声称已具备归档恢复 | 重启 | 程序生成/只读核对 |
| `synchronous_commit` | `on` | 事务提交等待持久化策略 | 会话/配置 | 程序生成/只读核对 |
| `ssl` | `on` | 服务端TLS | 重载 | 程序生成/只读核对 |
| `ssl_cert_file` / `ssl_key_file` | 数据目录下`socai2-tls/server.crt` / `server.key` | 服务端证书/私钥；私钥内容不读出 | 重载 | 程序生成/只读核对 |
| `ssl_ca_file` | 空 | 服务端未配置客户端证书CA；当前目标应用无需客户端证书 | 重载 | 程序生成/只读核对 |
| `statement_timeout` | 5000ms | 本次只读探针会话设置；**不是生产全局5秒默认** | 会话/配置 | 程序生成/只读核对 |
| `lock_timeout` / `idle_in_transaction_session_timeout` | 0 / 0ms | 本次会话未设限制；业务profile可单独限制 | 会话/配置 | 程序生成/只读核对 |

备份至少保存所选库的逻辑备份、角色/授权、迁移账本及配置版本；在新库恢复并`verify`后读回同批记录，不能覆盖原库验证。普通`pg_dump`不包含整个实例的角色。备份是否定期执行、最近可恢复点，本批未验证，不以持久卷存在推断已有备份。

## Redis

PostgreSQL保存任务/执行事实，Redis承载调度队列和运行占用。`pending`是内部实现，对前后端透明；HTTP读取task_id及Run，不读取Redis键。不要用Redis键TTL替代数据库中的上次活动时间和7天窗口。

| 参数 | 类型/示例 | 用途与约束 | 填写方式 |
| --- | --- | --- | --- |
| `REDIS_URL` | 私密URL | 模块连接，含ACL账号、密码、主机、端口、逻辑DB；文档只展示脱敏结构 | 部署必填 |
| 调度`redis_url_file` | 绝对文件路径 | 调度读取私密URL；独立验收须选明确逻辑DB和namespace | 部署必填 |
| 调度`redis_socket_timeout_seconds` | number，5秒 | Redis命令响应限时 | 保留默认 |
| 调度`redis_connect_timeout_seconds` | number，5秒 | Redis建连限时 | 保留默认 |
| `dispatch.namespace` | string，`socai2-analysis` | 键前缀，结合tenant区分队列；候选使用独立前缀 | 部署必填 |
| `REDIS_POOL_SIZE` | int，API源默认20 | API客户端池；不是Redis服务最大连接数 | 保留默认 |
| 服务`port` / `bind` | int/address | 监听设置；本次宿主入口6379 | 启用时必填（存储管理） |
| 服务`aclfile` / ACL账号规则 | 私密文件/规则 | 允许的命令、键范围和账号；不在文档列密码hash | 启用时必填（存储管理） |
| 服务`dir` / `dbfilename` / `appenddirname` | 路径/文件名 | RDB/AOF保存位置；应落持久卷，不放tmpfs | 启用时必填（存储管理） |
| 服务`save` | 周期规则 | RDB快照触发条件；本批未读回实际规则 | 启用时必填（存储管理） |
| 服务`appendonly` / `appendfsync` | bool/enum | AOF开关及刷盘策略；本批未读回，不能由挂了`/data`推断开启 | 启用时必填（存储管理） |
| 服务`maxmemory` / `maxmemory-policy` | bytes/enum | 内存上限及驱逐策略；调度状态不能按普通缓存随意驱逐。实际值需通过受控`CONFIG GET`核对 | 启用时必填（存储管理） |

本次连接观察：API使用DB8、Fusion DB9、Agents DB10、Actions DB11、Enrichment/ThreatIntel共享DB12；只是现状，不作为候选自动分配规则。逻辑DB不隔离CPU/内存，也不提供独立持久化文件。

RDB和AOF是不同的持久化机制，备份/恢复须匹配实际启用方式；先核配置和最后成功状态，再复制或制作一致备份。[Redis官方持久化说明](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)。本轮不执行`FLUSHDB/FLUSHALL`、删除队列或改持久化策略。

## Kafka

### 服务与Topic

| 参数 | 类型/观察值或目标 | 含义 | 填写方式 |
| --- | --- | --- | --- |
| `KAFKA_PROCESS_ROLES` | `broker,controller` | 本实例同时承担KRaft两类角色 | 程序生成/只读核对 |
| `KAFKA_NODE_ID` | int，1 | KRaft节点身份；不是客户端client_id | 程序生成/只读核对 |
| `KAFKA_CONTROLLER_QUORUM_VOTERS` | `1@kafka:29093` | 控制器成员及内部地址 | 程序生成/只读核对 |
| `KAFKA_CONTROLLER_LISTENER_NAMES` | `CONTROLLER` | 控制器监听名称 | 程序生成/只读核对 |
| `KAFKA_LISTENERS` | 地址列表 | 当前INTERNAL29092、EXTERNAL9092、CONTROLLER29093、SECURE19093 | 程序生成/只读核对 |
| `KAFKA_ADVERTISED_LISTENERS` | 可达地址列表 | 客户端随后连接的地址；项目TLS入口公布`192.168.1.21:19093` | 程序生成/只读核对 |
| `KAFKA_LISTENER_SECURITY_PROTOCOL_MAP` | 名称:协议列表 | SECURE 为 SSL，INTERNAL 为 PLAINTEXT。21 的 Fusion 和 UEBA 使用 INTERNAL | 程序生成/只读核对 |
| `KAFKA_LOG_DIRS` | `/var/lib/kafka/data` | 消息及位点日志的持久目录 | 程序生成/只读核对 |
| `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR` | int，1 | 位点内部Topic副本数 | 程序生成/只读核对 |
| `KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR` | int，1 | 事务内部Topic副本数 | 程序生成/只读核对 |
| `KAFKA_TRANSACTION_STATE_LOG_MIN_ISR` | int，1 | 事务内部Topic最小同步副本 | 程序生成/只读核对 |
| Topic分区数 / `replication.factor` | int | 创建时明确；分区影响并行与顺序，不是模型并发额度。独立测试Topic当前未创建 | 部署必填 |
| Topic `min.insync.replicas` | int | 写入确认所需同步副本数；单节点不能配置成需要两节点才能写 | 部署必填 |
| Topic `retention.ms` / `retention.bytes` | int，毫秒/字节 | 时间和大小保留上限；读回实际Topic配置，不能把7天调查窗口当作Kafka保留期 | 部署必填 |
| Topic `cleanup.policy` | enum | 日志清理方式；告警消息不能未经设计改成按key压缩丢掉历史 | 部署必填 |

`listeners`是服务监听，`advertised.listeners`是返回给客户端的连接地址；只转发bootstrap端口而不让后者可达，会出现“能连上但不能消费”。[Kafka 3.5配置参考](https://kafka.apache.org/35/generated/kafka_config.html)。

### 客户端逐项

所有Python Kafka模块复用[kafka_security.py](../../services/fusion/app/core/kafka_security.py)。文件装载后启动/重启对应生产者或消费者生效，不更改已有消费组位点。

| 参数 | 类型/目标值 | 含义 | 填写方式 |
| --- | --- | --- | --- |
| `KAFKA_BOOTSTRAP_SERVERS` | string，21 内部 `kafka:29092` | 初始 broker 地址。候选联验使用独立 Topic 和消费状态 | 按部署 profile |
| `KAFKA_SECURITY_PROTOCOL` | enum，21 内部 `PLAINTEXT` | 对应已选监听的协议。启用 SASL 时填写 SASL 字段 | 按部署 profile |
| `KAFKA_SSL_CAFILE` | 文件路径 | SSL 配置中的服务端 CA。21 同机明文 profile 已移除此项 | 按部署 profile |
| `KAFKA_SSL_CERTFILE` / `KAFKA_SSL_KEYFILE` | 私密文件路径，可选 | 需要客户端证书认证时成对提供；不与CA混用 | 启用时必填 |
| `KAFKA_SASL_MECHANISM` | string，可选 | 仅SASL协议时必填，须与broker一致 | 启用时必填 |
| `KAFKA_SASL_USERNAME` / `KAFKA_SASL_PASSWORD` | 私密值，可选 | SASL账号凭据；当前SSL不代表已经启SASL | 启用时必填 |
| `ENVIRONMENT` | string，`production` | 传输校验所用环境标签 | 保留默认 |
| `AISOC_ALLOW_CLEARTEXT_KAFKA` | bool，21 内部 profile 为 true | 21 的 Fusion 和 UEBA 使用 Docker 内部监听的显式选择 | 按部署 profile |
| `KAFKA_TOPIC_ALERTS_RAW` | string | 输入告警Topic | 部署必填 |
| `KAFKA_TOPIC_ALERTS_FUSED` | string | Fusion归并输出Topic | 部署必填 |
| `KAFKA_TOPIC_RAW_EVENTS` | string | 原始事件Topic，供数据湖写入/适用上下文 | 部署必填 |
| `KAFKA_TOPIC_ALERTS_FUSED_DLQ` | string | 使用该消费者时的失败消息Topic；不等于调度pending | 部署必填 |
| `KAFKA_CONSUMER_GROUP` | string | 消费位点身份；独立测试新group，不重置正式group | 部署必填 |
| `KAFKA_TOPIC_UEBA_ANOMALIES` | string | Fusion读取的UEBA输出；仅相应能力启用时使用 | 部署必填 |

投影自己的`topic/group/client_id`及拉取超时、单次条数见[处理链逐项表](deployment-processing.md)。完整验收需要记录Topic、partition、offset、事件ID/归并ID和落库引用，不能只证明发送成功。Kafka的保留日志不替代PG/湖备份，恢复或重新消费必须新批次、明确起点，不能重投已结束批次追认成功。

### 21 正式证书信任核验

2026-11-21 切换前，在正式 Fusion 容器使用 SSL 监听 `19093` 对比两种信任配置。带当时的 `KAFKA_SSL_CAFILE` 时通过证书校验并读取 Kafka 元数据。容器默认信任库校验返回 OpenSSL 19，签发链含未受信任的自签名证书。这份结果针对共享 SSL 监听。

### 21 Kafka 内部连接

Fusion 和 UEBA 现用 Docker 网络 `sting-infra21_default` 内的 `kafka:29092`。已验证客户端明文收发、就绪状态和原消费位点。共享 SSL 监听继续提供外部接入。UEBA 的 `PGSSLROOTCERT` 属于 PostgreSQL 连接配置。[客户端 profile](../../deploy/aisoc21/c173-release-20261121-03/kafka-internal.json) · [实测回执](evidence/c173-kafka-plaintext-20261121-01/README.md)

## ClickHouse 数据湖

### 数据与写入、查询关系

当前项目落在`<选定库>.raw_events`，建表源为[001_init.sql](../../services/api/clickhouse/001_init.sql)，Fusion使用[lake_writer.py](../../services/fusion/app/services/lake_writer.py)写入48个明确列。库名由连接配置传入并替换SQL中的限定名，不因源模板含`aisoc`就固定写正式库。

日志补查按tenant、对象、事件时间筛选；Case默认在相关告警最早/最晚时间前后各扩1小时、每次最多50条，缺少时间记录补查缺口。两个告警相隔较久时不自动裁剪或分段；查询超时/失败保留缺口及其他分析。日志结果上限不是Case成员上限，也不是输入Token保证。

| 参数 | 类型/目标示例 | 含义、必填及限制 | 填写方式 |
| --- | --- | --- | --- |
| `CLICKHOUSE_HOST` / `lake.host` | string，21地址 | Native客户端的目标；启用湖时必填 | 启用时必填 |
| `CLICKHOUSE_PORT` / `lake.port` | int，9000 | Native端口；不能把HTTP8123填给Native驱动 | 启用时必填 |
| `CLICKHOUSE_DATABASE` / `lake.database` | 标识符 | 写入和查询的选定库，候选若隔离应两端一致 | 启用时必填 |
| `SOCAI2_LAKE_DATABASE` | 标识符 | 调查查询构造使用的库名；与连接目标一致 | 启用时必填 |
| `CLICKHOUSE_USER` / `lake.reader_role` | string | 读侧账号；Fusion另用所选写账号，不能给查询配置管理账号 | 启用时必填 |
| `CLICKHOUSE_PASSWORD` | 私密字符串 | 对应账号密码，由受控文件注入 | 启用时必填 |
| `lake.container` | string | 安装/核验所选ClickHouse容器；不是客户端DNS自动替代值 | 启用时必填 |
| `AISOC_LAKE_WRITER_ENABLED` | bool，启用时true | 是否把原始事件写入湖；不依赖是否提升成告警 | 保留默认 |
| `AISOC_LAKE_BATCH_SIZE` | int，源默认100条 | 缓冲累计达到条数时写入；测试可显式缩小 | 保留默认 |
| `AISOC_LAKE_BATCH_MAX_AGE_SECONDS` | float，源默认2秒 | 未满批的最长刷新周期；不是保留期 | 保留默认 |
| `case.query_window.before_seconds` / `after_seconds` | int，各3600秒 | 调查补查窗口前后扩展；受选定执行器profile控制 | 保留默认 |
| `case.log_query.max_rows_per_query` | int，50 | 单次日志条数上限；不自动无限翻页 | 保留默认 |
| 调查策略的工具超时/额度 | 见[模型与策略表](deployment-models.md) | 查询失败、查空、未查分别记录，不能将超时记为0条安全结论 | 保留默认 |

当前Native客户端路径没有可由上述字段开启的`secure`/TLS参数，不能写“9000已加密”；若部署需要ClickHouse TLS，应先实现并验证客户端接线，再公开对应配置。HTTP8123只说明服务入口，不另生成一个本轮查询执行路径。

### 数据目录、保留和分层

| 项目 | 当前源码配置 | 作用与注意 | 填写方式 |
| --- | --- | --- | --- |
| 表引擎 | `ReplacingMergeTree(ingest_time)` | 同排序键的替换在合并时发生，不保证每次查询已无重复 | 程序生成/只读核对 |
| 分区 | `toYYYYMM(event_time), tenant_id` | 按月与租户分区；读回实际`SHOW CREATE TABLE`才能确认已部署 | 程序生成/只读核对 |
| 排序键 | `tenant_id, event_time, class_uid, event_id` | 支持租户/时间查询；event_id用于来源追踪 | 程序生成/只读核对 |
| 基础TTL | `toDateTime(event_time) + INTERVAL 400 DAY` | 源SQL删除上限；不是本次已执行清理的证据 | 程序生成/只读核对 |
| 同源统计/IOC表TTL | 365天 / 30天 | 分别作用于统计聚合与IOC富化表，不等于raw_events保留期 | 程序生成/只读核对 |
| 可选分层文件 | [storage-policy.xml](../../services/api/clickhouse/tiering/storage-policy.xml) | 定义冷盘目录`/var/lib/clickhouse/cold/`及存储策略；未证明21已加载 | 程序生成/只读核对 |
| 可选分层SQL | [002_tiering.sql](../../services/api/clickhouse/tiering/002_tiering.sql) | 30天转冷、400天删除；必须先装存储策略，不能直接执行缺少磁盘的SQL | 程序生成/只读核对 |
| `move_factor` | 0.1 | 分层策略的空间阈值参数，不是日志抽样率 | 程序生成/只读核对 |
| 服务`path`、`tmp_path`、`storage_configuration` | XML路径/结构 | 数据、临时目录和磁盘/卷；要落实际存在的持久空间 | 程序生成/只读核对 |
| 服务`max_server_memory_usage`等资源限制 | 按所选服务配置 | 本次没有读回，不据容器Memory=0推断数据库内部无上限 | 程序生成/只读核对 |

TTL在后台合并等过程中处理，并非时间一到就同步逐行删除；需要以实际表定义和数据读回验收。[ClickHouse MergeTree TTL说明](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/mergetree)。

现有湖写入是best-effort：失败会记录并丢弃本批缓冲，不能宣称零丢失或已自动补写。最终Kafka验收必须实际查到预期日志及对象/时间/来源；仅Fusion进程健康不足以验收。备份使用选定版本支持的备份/一致快照方案，目标另库/另路径，恢复后按tenant、event_id及范围核对；本批没有实施备份任务。

## Qdrant

| 配置 | 类型/目标 | 含义 | 填写方式 |
| --- | --- | --- | --- |
| 服务镜像/`storage.storage_path` | 固定镜像、路径 | 当前1.7.0，持久数据在`/qdrant/storage`，不要使用临时根层保存向量 | 启用时必填 |
| `service.http_port` / `service.grpc_port` | int，6333/6334 | 两种协议入口，客户端需匹配 | 启用时必填 |
| `QDRANT__SERVICE__API_KEY` | 私密字符串 | 服务端访问key，不能与LiteLLM key混用；本次不输出值 | 启用时必填 |
| `QDRANT_URL`或知识profile向量endpoint | HTTP URL | 调查知识连接，详见[知识profile](deployment-models.md) | 启用时必填 |
| `QDRANT_HOST` / `QDRANT_PORT` / `QDRANT_API_KEY` | 地址/int/私密值 | ThreatIntel客户端配置；服务端有key时客户端也须提供 | 启用时必填 |
| `QDRANT_COLLECTION_IOC` / `QDRANT_COLLECTION_ACTOR` | string | 情报两类collection，当前观察`socai2_threatintel_iocs`、`socai2_threatintel_actors` | 启用时必填 |
| collection `vectors.size` / `distance` | int/enum | 向量维度和距离；必须与embedding输出相同，不能仅靠同名模型认为兼容 | 启用时必填 |
| collection分片/副本数 | int | 创建时固定资源选择；本批未调整或重建collection | 启用时必填 |
| 快照目录及磁盘容量 | path/bytes | 快照也占磁盘，不等于已有外部备份 | 启用时必填 |

知识collection和情报collection分开；当前知识1024维不能写入要求1536维的情报集合。具体知识集合、模型、维度、top_k、超时及结果限制见模型配置页，不重复维护第二套值。已有集合维度不符时报错并调查来源，不能删除重建以“修复”配置。备份需同时记录collection参数和embedding版本，恢复到新名字核对后才考虑切换。

## Neo4j

| 配置 | 类型/本次观察或源码入口 | 含义 | 填写方式 |
| --- | --- | --- | --- |
| `NEO4J_URI` | URI，`bolt://192.168.1.21:7687` | 客户端图协议；7474是管理HTTP，不是Bolt连接 | 启用时必填 |
| `NEO4J_USER` / `NEO4J_PASSWORD` | 账号/私密值 | 图查询账号；初装服务端`NEO4J_AUTH`属于秘密文件，不公开 | 启用时必填 |
| `NEO4J_server_memory_heap_initial__size` | string，512m | 初始JVM堆 | 保留默认/只读核对 |
| `NEO4J_server_memory_heap_max__size` | string，1g | 最大JVM堆，不包括page cache及进程全部内存 | 保留默认/只读核对 |
| `NEO4J_PLUGINS` | JSON数组，`["apoc"]` | 本轮使用已提供插件，不凭部署脚本临时联网升级 | 保留默认/只读核对 |
| `NEO4J_dbms_security_procedures_unrestricted` | string，`apoc.*` | 允许的过程范围，属于服务配置；不自动扩大业务模型工具权限 | 保留默认/只读核对 |
| `/data` / `/logs` / `/plugins`挂载 | 目录 | 图持久数据、日志、插件文件；当前插件宿主目录见运行清单 | 启用时必填 |
| `SOCAI2_SOURCE_GRAPH_ENABLED` | bool，目标false | 调查是否读取图来源；有Neo4j容器不表示调查已启图 | 保留默认/只读核对 |

本轮保留图来源关闭；不因整理配置启用图或重跑索引。Community版本的备份/恢复须按实际版本能力选离线dump或一致磁盘快照，不把其他版本的在线备份指令当成可用。恢复后核节点/关系及租户来源，模型建议不作为图中既成事实。

## OpenSearch

| 配置 | 类型/本次观察或源码默认 | 含义 | 填写方式 |
| --- | --- | --- | --- |
| `discovery.type` | string，`single-node` | 当前单节点部署；不宣称有多节点容灾 | 保留默认/只读核对 |
| `OPENSEARCH_JAVA_OPTS` | string，`-Xms512m -Xmx512m` | JVM初始/最大堆；不限制所有进程内存 | 保留默认/只读核对 |
| 数据目录挂载 | `/usr/share/opensearch/data` | 索引持久数据；位于具名卷 | 启用时必填 |
| `OPENSEARCH_HOST` / `OPENSEARCH_PORT` | string/int，`spirithub-opensearch-1`/9200 | ThreatIntel客户端；所选容器需处于该网络 | 启用时必填 |
| `OPENSEARCH_USER` / `OPENSEARCH_PASSWORD` | 私密值，可选 | 服务启认证时提供；空值不意味着任意部署都无认证 | 启用时必填 |
| `OPENSEARCH_INDEX_IOC` | string，`socai2-threatintel-iocs` | IOC全文/字段查询索引 | 启用时必填 |
| `OPENSEARCH_INDEX_ACTOR` | string，`socai2-threatintel-actors` | Actor检索索引 | 启用时必填 |
| `OPENSEARCH_URL` | URL | 使用URL连接的API模块配置；并非ThreatIntel的HOST字段别名 | 启用时必填 |
| 服务TLS、安全插件和快照repository | 所选服务配置 | 本次只读清单未确认这些值，不生成“已安全配置/已备份”的结论 | 启用时必填 |

OpenSearch不是Case判断的权威存储；同步失败不能改写PG中既有结论。备份应使用实际配置的snapshot repository，并记录索引映射/版本，恢复到独立索引后核查询结果。本轮不创建repository、重建索引或启动外部情报采集。

## 容量、磁盘和最小读回

本次七类数据库容器均未发现Docker `Memory`上限或`StorageOpt`磁盘配额，数据目录均为持久卷；这不证明宿主文件系统、数据库内部配额或磁盘永远有空间。Docker `ShmSize=64MiB`是`/dev/shm`，不是PG数据盘。`tmpfs size`是对应挂载的单独容量，`mem_limit`是内存，二者都不是整机根分区大小。

此前耗尽的是本机隔离PG的256MiB tmpfs，本次21候选目录所在文件系统另有约848GiB可用，证据见[资源核对](evidence/streaming-candidate-20261115-01/resource-readback.json)。遇到空间错误先核**报错容器、实际数据路径、挂载类型、该挂载的`df`与inode**，再核数据库日志/WAL/临时文件；不能根据宿主根目录剩余容量排除局部挂载耗尽。

部署读回按实际选定资源完成：PG库/角色/迁移/样本关联，Redis目标DB/namespace/队列身份，Kafka Topic/group/位点，湖的实际表定义及同事件日志，向量集合维度/模型，图/情报索引来源及启用状态。需要回退应用时保存旧镜像/profile并停止新入站/调度后切换；已经保存的Run、失败、原答和增量数据不删除，数据库不靠降级DDL强行匹配旧代码。
