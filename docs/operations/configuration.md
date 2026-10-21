# 配置与凭据使用入口

整理日期：2026-10-20。前述表格为初始化时的配置快照，1B新生效配置见文末。本页记录地址、用途和配置来源；真实密钥已按用户要求迁入本地私有目录 `.local/configuration/2026-10-20/`，由 Git 忽略，目录权限 0700、文件权限 0600。该快照采集时没有修改服务器配置、轮换密码或发起模型请求；后续1B变更单独记录。

这些是参考环境/已有基础设施的连接索引，不是新服务的生效配置。当前只部署[告警处理服务端](alert-processing-scope.md)，不建设控制台或其他管理UI；21共享服务的项目对象与业务入口按[依赖计划](dependency-migration-plan.md)分批确定。未被选用的地址、别名和凭据仅保留来源。

## 模型与应用 API

| 用途 | 地址 / 模型 | 凭据与使用边界 |
| --- | --- | --- |
| 43 对话模型 | `http://192.168.1.43:8000/v1`；`aisoc-test-investigation` | OpenAI-compatible vLLM；`connections.env` 的 `SOCAI2_CHAT_API_KEY`。保留20配置中的实际值；本轮没有重新验证服务是否强制鉴权 |
| 外部 GPT 备用入口 | `https://ergouzi.life/v1`；仅 `gpt-5.5` | 旧项目已配置的第三方兼容入口；`SOCAI2_OPENAI_API_KEY`。未本轮调用，不是 OpenAI 官方域名；不自动切换或发送业务数据 |
| 20 LiteLLM | 容器内 `http://litellm:4000/v1`；宿主机 `http://127.0.0.1:4000/v1` | 网关密钥 `SOCAI2_REFERENCE_GATEWAY_MASTER_KEY`；与43上游凭据不同 |
| 20 embedding | 容器内 `http://ollama-embedding:11434/api/embed`；宿主机 `http://127.0.0.1:11434/api/embed` | `qwen3-embedding:0.6b`，1024维，无独立 API key；仅20 loopback/Compose网络，21不能直接使用这些地址 |
| 20 控制台 | `http://192.168.1.20:3000`；同源 API 前缀 `/api/v1` | `admin@aisoc.internal`；密码在私有 `aisoc20-admin-credentials.json` |
| 21告警处理服务端 | 1F API `127.0.0.1:18000`、Fusion `127.0.0.1:18003`（21本机） | production、Bearer认证、无控制台；Agents/Actions为loopback18004/18005。实际模型与只读身份接线见文末各批，当前运行命令见[21操作说明](../../deploy/aisoc21/README.md) |

20 的 LiteLLM 配置文件定义9个别名：`aisoc-triage`、`aisoc-recon`、`aisoc-investigation`、`aisoc-copilot`、`aisoc-summary`、`aisoc-report`、`aisoc-nl`、`aisoc-hunt`、`aisoc-detection`。当前 fast/deep 都配置为 `openai/aisoc-test-investigation`，转发到43。定义9个别名不证明9个角色都已实际调用；之前只有 triage 网关 smoke。路由原件见私有 `aisoc20-litellm.yaml`。

如需从工作站访问20的 loopback 网关和 embedding，可开 SSH 隧道：

```bash
ssh -N -o ExitOnForwardFailure=yes \
  -L 14000:127.0.0.1:4000 -L 11435:127.0.0.1:11434 sting-host20
```

隧道保持期间，本机网关地址为 `http://127.0.0.1:14000/v1`，embedding 为 `http://127.0.0.1:11435/api/embed`。这不会为21的容器建立访问路径。

## 21 已有共享基础设施

下列密码以本轮只读取得的21服务器 `.env` 为准，已与旧工作站副本逐字节核对一致。保留地址和凭据不代表新 AiSOC 已完成数据库、schema、角色或卷适配。

| 服务 | 地址 / 用户 | `connections.env` 中的凭据变量 |
| --- | --- | --- |
| PostgreSQL | `192.168.1.21:5432`；用户 `sting` | `SOCAI2_POSTGRES_PASSWORD` |
| Redis | `192.168.1.21:6379` | `SOCAI2_REDIS_PASSWORD` |
| Kafka | `192.168.1.21:9092` | 既有入口无认证 |
| Qdrant | `http://192.168.1.21:6333`；gRPC 6334 | `SOCAI2_QDRANT_API_KEY` |
| Neo4j | `bolt://192.168.1.21:7687`；用户 `neo4j`；Web 7474 | `SOCAI2_NEO4J_PASSWORD` |
| ClickHouse | `http://192.168.1.21:8123`；原生9000；用户/数据库 `sting` | `SOCAI2_CLICKHOUSE_PASSWORD` |
| OpenSearch | `http://192.168.1.21:9200` | 既有入口无认证 |
| pgAdmin | `http://192.168.1.21:5050`；`admin@example.com` | `SOCAI2_PGADMIN_PASSWORD`，与数据库密码不同 |
| 管理 UI | Kafka UI `http://192.168.1.21:8090`；RedisInsight 5540；OpenSearch Dashboards 5601；Qdrant `/dashboard` | 数据操作仍使用对应服务凭据 |

既有 PG 库为 `sting`、`sting_fusion_test`、`sting_ueba_test`、`sting_investigation_test`。新部署先核上游迁移/角色要求并隔离资源；不覆盖旧事实或 spirithub 数据。Redis 历史开发为 DB0、测试为DB15，禁止清空全库。

## 私有文件及来源

所有下列文件都位于 `.local/configuration/2026-10-20/`，不纳入 Git：

| 文件 | 内容 / 来源 |
| --- | --- |
| `connections.env` | 35个汇总连接变量，包含现有真实密钥；使用 `SOCAI2_` 前缀区分用途 |
| `aisoc20.env` | `sting-host20:/home/lychee/beenuar/.env` 原字节快照；含认证、服务token、数据库等配置 |
| `aisoc20-admin-credentials.json` | 20 管理员账号密码原件副本 |
| `aisoc20-litellm.yaml` | 20 模型路由原件；与其 `.env` 配合解释 |
| `aisoc20-compose.override.yml` | 20 实际部署 overlay 原件 |
| `infra21-server.env` / `infra21.env` | 21 `/opt/sting-aisoc-infra/.env` 与旧工作站副本 |
| `legacy-workstation.env` / `legacy-litellm.yaml` | 旧工程 `.env` 与 LiteLLM 路由；外部 GPT 凭据来源，其他旧应用设置不是新项目默认值 |
| `inventory.json` | 原件来源、hash及变量是否已填，不含密钥明文 |

这些是迁移时点的配置快照；轮换后应更新本地受控副本。GitHub 不包含这些私有文件，换电脑时需要单独安全传输。SSH 私钥不复制，仍用当前用户 `~/.ssh/config` 的 `sting-host20`、`sting-infra21` 别名。

## 后续怎样使用

从 socai2 根目录按需加载已整理的汇总文件：

```bash
set -a
source .local/configuration/2026-10-20/connections.env
set +a
```

`connections.env` 是经过 shell 引用处理的配置清单。**当前没有业务代码读取 `SOCAI2_*`，加载不等于应用已接线。** 导入源码后将选定变量明确映射到 AiSOC 的真实变量名；不要把20整份 `.env` 当21的新部署配置，也不要同时加载旧环境快照。

例如：直连43时使用 `SOCAI2_CHAT_BASE_URL`、`SOCAI2_CHAT_MODEL`、`SOCAI2_CHAT_API_KEY`；接 LiteLLM 时使用网关地址、任务别名和网关 master key；转发到外部 GPT 的备用路由使用独立的 `SOCAI2_OPENAI_*`。它们的地址和凭据不能互换。

可公开提交的空密钥模板为根目录 [`.env.example`](../../.env.example)。生成新部署凭据时保留参考环境原件，另外创建目标环境配置，不覆盖既有快照。本轮只检查了复制一致性、权限和 Git 忽略，未调用付费 API 或重新运行数据库/模型连通测试。

## 1B实际生效配置（21共享服务）

用户确认复用21公开数据服务并允许适当重启后，已创建本项目新配置，未覆盖上述历史快照。PG使用`192.168.1.21:5432/aisoc`，owner=`aisoc`、runtime=`aisoc_app`；Redis使用21:6379，账号`socai2`，API/Fusion/Agents/Actions/TI分别分配DB8/9/10/11/12。历史`sting`凭据不作为新服务默认账号。

新凭据在21 `/opt/sting-aisoc-socai2/private/shared-services.json`、`runtime.env`，工作站受控副本为`.local/aisoc21/private/`；目录0700、文件0600、Git忽略。`runtime.env`仅为配置输入，Redis的SOCAI2变量须在后续业务编排映射到真实服务变量，当前没有业务进程读取。不要在终端输出整份配置。

Redis现有Compose增加`--aclfile /data/socai2-users.acl`，全部既有ACL及密码保持；受控原件备份在21 `private/redis-restart-before/`。新增或轮换ACL后由管理员执行`ACL SAVE`保存，不打印ACL密码hash。直接验收及边界见[1B回执](1b-shared-services.md)。

## 1C创建时的Kafka项目资源（1F生效配置见下）

使用21:9092的EXTERNAL listener，现有KRaft集群。项目topic为`socai2.alerts.raw`、`socai2.alerts.fused`（各3分区）、`socai2.alerts.fused.dlq`（1分区），均RF1、minISR1、保留7天，本批没有业务数据。Fusion与Agents真实变量映射见[kafka-resources.json](../../deploy/aisoc21/kafka-resources.json)；计划的业务group尚未有服务启动。

Fusion使用`KAFKA_CONSUMER_GROUP=socai2-fusion-consumer`；Agents构造器默认`aisoc-agents-triage`，main尚未传入group_id，不能假设Fusion变量对Agents也生效，1G须单独接线。Fusion默认DLQ在PG；创建Agents Kafka DLQ topic不证明Fusion会往Kafka发DLQ。

现有broker为PLAINTEXT、无认证。1C仅在合成测试探针中选用development transport，原版production/staging拒绝明文已实际调用验证，未设置`AISOC_ALLOW_CLEARTEXT_KAFKA`。业务部署的传输方案到1F明确，不能用启动失败后改默认环境来隐式跳过保护。源码客户端0.10.0与两项依赖按原锁hash安装在21 `client-1c/packages/`，探针容器Python3.12.15，服务Python3.11仍须实际构建验证。

## 1F生效配置与操作凭据

新运行配置在21 `/opt/sting-aisoc-socai2/private/api-1f.env`、`fusion-1f.env`；owner迁移配置为`migrate-1f.env`，不交给API/Fusion运行容器。`app-1f.json`记录生成的签名/metrics/vault密钥及测试身份；工作站受控副本在`.local/aisoc21/private/`，0700/0600，Git忽略。测试API key已停用，不能把旧key当当前管理员凭据。

新服务使用`aisoc_app`及PG `sslmode=verify-full`，`PGSSLROOTCERT=/run/certs/ca.crt`；Kafka为21:19093、`KAFKA_SECURITY_PROTOCOL=SSL`、`KAFKA_SSL_CAFILE=/run/certs/ca.crt`，不设明文豁免。当前资源映射见[kafka-resources.json](../../deploy/aisoc21/kafka-resources.json)。旧connections.env与1B runtime.env仍是原时点索引，不同时加载到1F服务。

CA公证书在21 `certificates/socai2-ca.crt`；CA私钥/服务证书及旧Compose/PG配置备份在受控`private/transport-1f/`，不入Git。Kafka只新增TLS listener；PG只开启TLS并reload，旧服务原入口继续保留。服务证书有效90天，续签必须保持SAN/IP、CA校验及单服务恢复验证，见[1F回执](1f-alert-chain.md)。

## 1D向量与embedding生效配置

21 embedding仅`127.0.0.1:11435`和socai2网络内`http://ollama-embedding:11434/api/embed`可达，无独立API key，不向LAN发布；Ollama0.40.6/qwen3-embedding:0.6b原生1024维，16核/32GiB。资源与固定image ID在[compose.embedding.yml](../../deploy/aisoc21/compose.embedding.yml)维护，API/Fusion环境未改。

依赖探针的受控Qdrant key只在21 `private/vector-1d.env`及工作站`.local/aisoc21/private/vector-1d.env`，0600/Git忽略。它是共享服务key，非集合级权限；只向临时探针注入，未擅自挂载20的业务overlay。模型/调用与来源清单见[1D回执](1d-vector-embedding.md)。共享Compose的nofile65536已生效；旧配置备份位于21 `private/vector-1d/compose-before.yml`，不能用旧备份覆盖后来其他服务变更。

## 1E网关配置

21网关为`127.0.0.1:14000/v1`、socai2网络内`http://litellm:4000/v1`。配置见[compose.gateway.yml](../../deploy/aisoc21/compose.gateway.yml)、[派生路由](../../deploy/aisoc21/litellm.config.yaml)及[资源映射](../../deploy/aisoc21/gateway-resources.json)，原件在[infra/litellm/config.yaml](../../infra/litellm/config.yaml)。仅五角色，45秒超时、重试0、fallback空，均转发43已有模型；未发布copilot/nl/hunt/detection。

43凭据参数和新生成master key在21 `private/gateway-1e.env`；仅客户端所需的网关master key及地址在`private/gateway-client-1e.env`，不包含43 provider key。工作站对应`.local/aisoc21/private/`，0700/0600、Git忽略。`OPENAI_BASE_URL/OPENAI_API_KEY`及`LLM_GATEWAY_URL/LITELLM_MASTER_KEY`用于后续实际服务映射；`LLM_GATEWAY_API_KEY`为本批探针读取字段。当前没有把这些新配置加载到API/Fusion，不同时加载旧快照。

本批仅master服务身份，无虚拟密钥DB；错误key返回原版400/no_db_connection。网关key与43参数不可互换。43沿用参数的值已存在固定上游源码中，不作为保密凭据或43强制鉴权已验证的证明；本批未把该值新增到公开文件。启动/停止和验证限制见[1E回执](1e-model-gateway.md)。

## 1G实际服务与知识候选

Agents/Actions分别使用21 `private/agents-1g.env`、`actions-1g.env`，工作站受控副本在`.local/aisoc21/private/`；使用aisoc_app/TLS及Redis DB10/11。Agents加载独立1E网关客户端配置，不含43 provider参数；成本信任显式`AISOC_GATEWAY_COST_TRUST=0`，未定价调用不当免费。选定路由范围由`AISOC_SCOPED_BASELINE=1`控制，自动worker/记忆写回关闭。新增入口在21 loopback18004/18005；2个标记API key已停用，JWT到期不等于共享签名密钥已轮换。

`app-1g.json`、`app-1g-cost.json`仅含受控测试身份，不能公开或当永久操作凭据；首次错误账本与修复复验分别保留。原Kafka组环境接线已在Agents main加入，但worker未启动，不等于消费验收。

用户允许充分调配已有数据/模型及20、21资源；本地4B模型manifest/blob已核，未改变生效embedding配置。后续跨机服务地址、身份、集合和维度由[知识复用计划](knowledge-data-reuse-plan.md)在实际部署时记录，不能预写为已接通。

## 2A运行与测试身份

Fusion继续读取原`private/fusion-1f.env`，仅用[2A Compose叠加层](../../deploy/aisoc21/compose.correlation-2a.yml)指定修复镜像，未改业务配置/数据库schema/ID算法。21 `private/app-2a.json`及本地受控副本只用于本批标记身份，0600/Git忽略；2枚API key已停用并实测401。历史测试凭据不能作为后续管理员入口。

## 2A-01实际身份合同

[identity叠加层](../../deploy/aisoc21/compose.identity-2a.yml)将API身份配置为`source-v1`，读取原api-1f.env/fusion-1f.env；无新模型/基础设施凭据。新请求须显式稳定UUID id，版本/source_alert_id由服务设置；PG前置查询识别有记录的精确旧HTTP投递，旧Kafka继续legacy。服务切换必须先consumer后publisher；回退先停输入和核已受理队列，见[运行合同](2a-source-identity.md)。

21 `private/app-identity-2a.json`及工作站受控副本为本批三枚测试key，0600/Git忽略，已全部停用401；未复活此前2A key。数据库schema/134迁移均未变，身份与incident_id放现有enrichment_data的socai2_fusion命名空间，不改写旧材料。

## 2B-01风险批次

服务env、评分权重和API镜像保持；当前Fusion及完整Compose层见[风险回执](2b-risk-idempotence.md)。本批两tenant/两key的受控原件为21 `private/app-risk-2b.json`及工作站`.local/aisoc21/private/app-risk-2b.json`（0700目录/0600文件/Git忽略）；两key已停用401，不作运维身份复用。RBA实际配置指纹在回执；尚未补配Fusion租户认证材料，ML状态接口503的实际限制保留。

## 2B-02规则批次

原api-1f.env/agents-1g.env保持，未增加服务凭据；新镜像通过[policy层](../../deploy/aisoc21/compose.policy-2b.yml)加载。规则内容仍在aisoc_business_context_rule_sets现有YAML/enabled/updated_at列，新增指纹是内容身份，不是持久单调计数。受控测试身份原件为21 `private/app-policy-2b.json`及工作站`.local/aisoc21/private/app-policy-2b.json`，0700/0600/Git忽略，3key已停用401。实际采用及cache/stale_cache/unavailable状态见[规则回执](2b-policy-versions.md)。

## 2C-01本地IOC配置

原私有env不变，[IOC层](../../deploy/aisoc21/compose.ioc-2c.yml)只覆盖Fusion `AISOC_FUSE_ENRICHMENT=true`、`AISOC_TENANT_IOC_MATCH=1`、`ENRICHMENT_SERVICE_URL=`空值，使其仅读当前tenant的PG IOC存储。未部署Go或引入外部provider凭据，不接触IOC域名。测试身份在21 `private/app-ioc-2c.json`及工作站`.local/aisoc21/private/app-ioc-2c.json`，0700/0600/Git忽略，2key已停用。历史来源与置信默认/衰减限制见[回执](2c-ioc-consumption.md)。

## 2C-02 PG上下文

无新服务凭据/env/依赖；[context层](../../deploy/aisoc21/compose.context-2c.yml)只更新API镜像。GET alerts/{id}/processing-context使用正常alerts:read身份，tenant从认证主体获取，仅读该tenant现有PG表；不修改原分数或队列。本批身份在21 `private/app-context-2c.json`及本地`.local/aisoc21/private/app-context-2c.json`，0700/0600/Git忽略，3key停用401。合成资料与当前读取/as-of边界见[回执](2c-processing-context.md)。

2C-03只读核查未添加lake/UEBA服务凭据或改服务配置，见[回执](2c-event-ueba-sources.md)。临时测试key位于21 `private/app-sources-2c.json`及工作站`.local/aisoc21/private/app-sources-2c.json`，3key已停用；不作为生产Agents API凭据。当前Agents调查工具尚缺该身份，不能因API端口可达就记已接线。

3A-01仅加Agents镜像层，运行环境与挂载不变。`private/app-suppression-3a.json`及工作站受控副本的3key已停用；独立`private/probe-suppression-3a.env`从原Agents配置取DB、从Fusion取既有Kafka/TLS值，只给有界探针，不加载到常驻服务。细节见[回执](3a-policy-suppression.md)。

3A-02没有新常驻配置或模型凭据；短时key在21 `private/app-model-triage-3a.json`及工作站受控副本，3key停用。独立`private/probe-model-triage-3a.env`沿原模型/DB配置并复用Fusion Kafka/TLS，只对探针额外禁审批；两个新tenant用现有PG shadow表开启观察。模型失败只改独立进程的OPENAI_BASE_URL至本地闭合端口，未停共享网关/43。见[回执](3a-model-triage.md)。

3A-03没有新常驻配置/凭据或依赖；`private/app-risk-score-3a.json`及工作站受控副本的3key已停用。`private/probe-risk-score-3a.env`复用现有Agents模型/DB和Fusion Kafka/TLS，只供有界探针、额外禁审批；两个新tenant的PG shadow行保留。当前risk-score Compose层只改三服务镜像。证据见[回执](3a-risk-score.md)，该批当时五类context401尚未修复，后续org/skill/KB读取分别见下文。

3A-04新增Agents只读目录`/opt/sting-aisoc-socai2/private/org-memory-3a/`→`/run/secrets/org-memory`，UID/GID10001、0700，keys.json0600，`AISOC_ORG_MEMORY_KEYS_FILE=/run/secrets/org-memory/keys.json`。映射仅A/B测试tenant，各有独立reader API key（alerts:read、30天、禁口令登录用户），两key保留，到期为2026-11-19T07:52:59.737539Z；三枚短时操作key停用。原件在21 `private/app-org-memory-3a.json`、`private/probe-org-memory-3a.env`、`private/runtime-env-before-org-memory-3a.json`，工作站受控副本位于`.local/aisoc21/private/`，0600/Git忽略。API未配置新共享token；当时其他四类reader仍401，技能后续见3A-05。目录挂载允许原子替换keys.json并保留权限，下一读重新选映射；服务端单独撤销与数据编辑删除最多等待缓存剩余TTL120秒，缓存内逐条核expires_at。需要即时停止采用该tenant材料时移除映射并核not_configured；不能将强制TTL0探针写成默认即时撤销。细节见[回执](3a-org-memory.md)。

## 3A-05技能专用读取身份

[tenant-skill层](../../deploy/aisoc21/compose.tenant-skill-3a.yml)新增`AISOC_TENANT_SKILLS_KEYS_FILE=/run/secrets/tenant-skill/keys.json`及只读挂载`/opt/sting-aisoc-socai2/private/tenant-skill-3a/`→`/run/secrets/tenant-skill`。宿主目录UID/GID10001、0700，keys.json0600，tenant UUID→独立reader key；只配置原A/B测试tenant，各key仅settings:read、30天、禁口令登录用户，不扩大或复用原组织记忆alerts:read key。两reader到期为2026-11-19T08:36:24.337460Z，最终HTTP200；三短时操作key停用并实际401，见[回执](3a-tenant-skill.json)。

受控原件在21 `private/app-tenant-skill-3a.json`、`private/probe-tenant-skill-3a.env`、`private/runtime-env-before-tenant-skill-3a.json`，工作站副本仅在`.local/aisoc21/private/`，0700/0600、Git忽略；不将key写入文档、Git或镜像。目录挂载支持原子替换文件并保留权限，读取先核映射，缓存按tenant/地址/身份隔离；默认120秒不保证服务端即时撤销/到期/编辑/退休，缓存逐项核expires_at，刷新失败不采用旧材料。需即时停止采用某tenant技能时移除对应映射并核unavailable/not_configured。

旧组织记忆两枚reader及其映射/env/挂载保持，各自权限不互换。技能GET采用标准Bearer/settings:read/tenant交集，旧X头单独不授权；该批当时KB/处置/身份三类reader仍401，KB后续见下条。不得用万能共享key或技能key绕过其他reader身份。

## 3A-06 KB专用读取身份

[kb-read层](../../deploy/aisoc21/compose.kb-read-3a.yml)增加`AISOC_TRIAGE_KB_KEYS_FILE=/run/secrets/triage-kb/keys.json`及只读目录`/opt/sting-aisoc-socai2/private/kb-read-3a/`→`/run/secrets/triage-kb`。宿主UID/GID10001、0700，keys.json0600，tenant UUID→各自reader key；仅配置A/B测试tenant，每key只含knowledge_base:read、30天，到期2026-11-19T09:05:50.327428Z。3短时操作key停用401，2 KB reader最终200；原组织记忆alerts:read与技能settings:read四枚key、各映射/env/挂载/hash保持，权限不能互换或当公共API身份。

受控原件在21 `private/app-kb-read-3a.json`、`private/probe-kb-read-3a.env`、`private/runtime-env-before-kb-read-3a.json`，工作站仅`.local/aisoc21/private/`，0700/0600、Git忽略；凭据不进Git、文档、镜像。内部KB GET使用标准Bearer/knowledge_base:read/tenant交集，X头不授权；reader尝试告警ingress、KB ingest/delete被拒绝。

读取先核专用映射，缓存绑定tenant/URL/凭据hash/query/limit/cutoff。映射移除/轮换在缓存前生效；原子替换keys.json时保持权限。默认120秒缓存不保证API端撤销/到期/文档更新或删除即时生效；需要立即停止某tenant采用时移除其映射并核unavailable/not_configured。PG全文查询不配置新embedding/模型服务，保守cutoff排除后来修改的行但不重建旧正文。当前二十一层运行及恢复见[21说明](../../deploy/aisoc21/README.md)，实际采用/模型引用与限制见[回执](3a-kb-read.md)；该批当时处置/身份reader仍401，处置后续见下条。


## 3A-07近期处置专用读取身份

[dispositions层](../../deploy/aisoc21/compose.dispositions-3a.yml)新增`AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE=/run/secrets/dispositions/keys.json`及只读目录`/opt/sting-aisoc-socai2/private/dispositions-3a/`→`/run/secrets/dispositions`。宿主UID/GID10001、目录0700、keys.json0600，tenant UUID→独立reader key；仅A/B测试tenant，每key仅alerts:read、30天，到期2026-11-19T09:43:22.888022Z。三操作key已停用且401，两reader最终200；alerts:read为现有scope，不是本接口独占权限。原org两枚alerts:read、skill两枚settings:read、KB两枚knowledge_base:read及各映射/env/mount/hash/scopes保持，八枚reader按用途独立映射，不共用万能key。

受控原件在21 `private/app-dispositions-3a.json`、`private/probe-dispositions-3a.env`、`private/runtime-env-before-dispositions-3a.json`，工作站仅`.local/aisoc21/private/`，0700/0600、Git忽略；不输出整份配置或把凭据写入文档、Git、镜像。GET feedback/recent-dispositions使用标准Bearer/alerts:read/tenant交集与显式RLS，旧X头不授权；新reader写告警ingress/反馈均被拒绝。

专用映射检查先于缓存，缓存绑定tenant/URL/凭据hash/rule/entities/limit/cutoff。原子替换keys.json须保持权限；移除映射后核unavailable/not_configured。默认120秒不保证服务端单独撤销/到期或note编辑删除即时生效；真实撤销后有效缓存仍成功，强制TTL0刷新401且无旧材料，不能写成默认即时撤销。created cutoff没有反馈内容历史，不设置新模型/embedding服务。该批当时身份reader401，后续接线见下条；当前运行及失败恢复见[21说明](../../deploy/aisoc21/README.md)和[本批回执](3a-dispositions.md)。


## 3A-08身份reader与专用图配置

[identity-read层](../../deploy/aisoc21/compose.identity-read-3a.yml)在Agents增加`AISOC_TRIAGE_IDENTITY_KEYS_FILE=/run/secrets/triage-identity/keys.json`，宿主`private/identity-read-3a`只读挂载；API增加`AISOC_IDENTITY_GRAPH_CONFIG_FILE=/run/secrets/identity-graph/config.json`，宿主`private/identity-graph-3a`只读挂载。两目录均UID/GID10001、0700/0600。API保留AISOC_DISABLE_NEO4J=true，独立lazy连接不调用通用init/schema；graph config仅uri/username/password/database，值只放受控文件，原Bolt未新增TLS。

仅A/B两枚graph:read reader保留200，到期2026-11-19T10:31:59.338283Z，三操作key已停用401；原四类八枚reader及state/map hash、scope、env/mount保持，总十枚分别映射。graph:read是已有权限，非本接口专属scope。新受控state/probe/env原件为21 `private/app-identity-read-3a.json`、`probe-identity-read-3a.env`、`runtime-env-before-identity-read-3a.json`，工作站在Git忽略的`.local/aisoc21/private/`。

身份缓存默认300秒，映射先于绑定tenant/URL/凭据hash/accounts/limit/cutoff的缓存；有效缓存不即时重验撤销/到期/图修改，实际TTL0刷新401且无旧材料。轮换保持权限，不能改用旧reader或通用共享token。专用配置移除实际200→503→200，但这不改变图账号的数据库权限。五类读取已接通，3A-09复验与准入阻塞见下文，不启worker或graph。


## 3A-09受控复验身份与探针参数

没有新常驻配置或reader key，原十枚及五目录/env/map hash/scopes保持。三枚短时操作key位于21 `private/app-triage-admission-3a.json`及本地Git忽略受控副本，已全部撤销401；`private/probe-triage-admission-3a.env`仅供探针，不加载常驻服务。只挂固定inputs.json，不把同目录rubric/评分材料挂入模型进程。

本批只在探针工厂构造ChatOpenAI时设max_retries=0/request_timeout=45，并留默认/实际SDK client设置；生产根client retry2/timeout None未改，网关retry0不替代SDK限制。模型开始/ack检查点存在后不重跑；finish只读恢复没有再次变更key。默认来源TTL仍原四类120/身份300秒。后续[3A-10](3a-worker-reliability-plan.md)分批处理准入可靠性，不自动开放常驻。

## 3A-10-01操作身份与运行配置保持

本批没有新增reader、常驻env或挂载，原五目录/十枚key及state/map/scopes/hash均保持；凭据保持不外推重启后十枚旧查询重测。三枚短时操作key在21受控`private/app-triage-durability-3a.json`，已全部停用401；`private/probe-triage-durability-3a.env`只供探针，工作站副本仍在Git忽略目录，0700/0600，不进入镜像或公开材料。

[第十八层](../../deploy/aisoc21/compose.triage-durability-3a.yml)只更新Agents image，原worker OFF及五类TTL保持；修复未改变生产SDK默认重试/超时或新设模型预算。Env列表顺序差异不是配置值变化，恢复以排序hash及原挂载核验，没有再次构建/重建。当前运行和回退见[21说明](../../deploy/aisoc21/README.md)，限定验收与剩余缺口见[回执](3a-triage-durability.md)。

## 3A-10-02操作身份及持久开始语义

[第十九层](../../deploy/aisoc21/compose.triage-recovery-3a.yml)只更新Agents image，无新reader、常驻env/mount或DDL。原十枚reader文件/hash/metadata/scopes保持；三枚短时操作key在21受控`private/app-triage-recovery-3a.json`，已全部停用401；`private/probe-triage-recovery-3a.env`仅供探针，受控副本继续0700/0600、Git忽略，不进镜像或公开配置。

普通Kafka live入口复用现Run和seq=-1开始事件，未完成不自动超时抢占；同worker待持久完整材料最多128槽，进程退出不能恢复则停unknown。没有生产SDK预算新开关；负seq增量cursor仍422。原policy/memory抑制、direct triage/replay及五类TTL保持；当前命令和回退见[21说明](../../deploy/aisoc21/README.md)，有限保证见[回执](3a-triage-recovery.md)。

## 3A-10-03-01当前请求/cursor层

[第二十层](../../deploy/aisoc21/compose.triage-request-3a.yml)仅更新API/Agents为triage-request-3a-20261020，原env和五类reader挂载保持。无新增运行开关：triage角色factory默认SDK retry0/timeout45，auto-triage整次调用45秒截止；显式factory参数可覆盖默认，不外推其他角色或全入口。since最小值-1，仍严格增量，不新增事件。实际[回执](3a-triage-request.md)含189项/71项HTTP及限制，当前完整命令见[21说明](../../deploy/aisoc21/README.md)。

本批三操作key仅cases:read及拒绝样例alerts:read，保存在受控private/app-triage-request-3a.json和本地.local/aisoc21/private同名文件，均已停用401；原十枚reader与图配置hash/metadata/scopes保持，没有新reader或probe env。未实现持久租户调用/tokens预算，03-02待验。

## 3A-10-03-02当前额度/停止层

[第二十一层](../../deploy/aisoc21/compose.triage-budget-3a.yml)只更新Agents为triage-budget-3a-20261020，API保留triage-request，原env/五reader挂载保持。新增AISOC_TRIAGE_BUDGET_POLICY_FILE=/run/secrets/triage-budget/policy.json和只读目录挂载；宿主private/triage-budget-3a归UID/GID10001、0700，policy.json0600。文件只映射A/B测试tenant，最终各24小时/3次/60000预留单位/最多2未结算；当前未知占位与额度保留，不自动清账。文件不含reader key，作用是尝试额度，不是供应商usage/费用上限或所有入口统一预算。

独立项目SQL见deploy/aisoc21/migrations/001_triage_budget.sql，不改134上游迁移登记，runtime不建表。实施前private/triage-budget-3a-before.dump已独立恢复验证，备份及配置在工作站.local/aisoc21/private保留，不进Git。三操作key保存在private/app-triage-budget-3a.json，B入口仅交换受控测试身份的同名-b副本；均已停用401，十reader及图配置保持。完整[回执](3a-triage-budget.md)和[21命令](../../deploy/aisoc21/README.md)包含失败/恢复；只有显式调policy才能改变准入，不退款、删除或自动重试未知。

## 3A-11-01最新只读准入复核

3A-11-01只读准入复核已完成，见[回执](3a-admission-review.md)：旧p01时间/授权错误未被indicator gate识别；常驻Agents审批提案guard实际True且缺Kafka bootstrap/TLS，旧调查工具身份仍缺。三未知预约及A积压保持，0模型/消息/offset提交/运行改动；完整准入未过。下一[3A-11-02配置补齐](3a-triage-admission-config-plan.md)，保持worker禁用，然后单独修提示词/复验质量。

审批提案guard未显式禁用、常驻Agents缺Kafka bootstrap/TLS；worker关闭使其未作为常驻消费者运行，隔离探针通过不证明这些环境项已接。五reader不替代旧工具service身份。旧回执保持；本批无运行改动，三未知预约及A积压不清理/重调。

## 3A-11-02最新配置验收

3A-11-02常驻分诊配置补齐已限定验收，见[回执](3a-triage-admission-config.md)：仅Agents同镜像重建一次，新增四项环境值，复用原只读CA；审批提案guard现False、Kafka SSL/主机名校验及六组offset读取通过。旧14表/三unknown/A积压/十reader/其他35容器/18卷/134迁移保持，0模型/消息/提交。当前22层、19源码层，worker仍OFF；下一[3A-11-03理由提示词修复](3a-triage-reasoning-plan.md)，完整准入/质量未过。

当前补齐的是transport及审批提案禁用，不含常驻topic/group/DLQ项目映射；五reader与通用工具身份仍分开。A积压与unknown不清理/重调；p01理由仍未修，不能将配置就绪当质量或常驻准入。


## C01最新限定验收

C01新增第二十三层`compose.fusion-delivery-c01.yml`只指定Fusion镜像，env/挂载/凭据保持；仅Fusion重建。回退完整定义及原配置在21 `private/completion-c01/`，工作站受控备份`.local/aisoc21/private/completion-c01/`（7文件、0600）；两个本批操作key已停用401，十枚reader及原预算policy保持。当前完整命令见[21说明](../../deploy/aisoc21/README.md)，验收见[C01](c01-fusion-delivery.md)。

## 2026-10-21调查工具原只读服务身份

API与Agents通过当前第29层 `compose.integrity.yml` 加载21私有 `private/completion-integrity-20261021/api-read-service.env`，其中仅有独立的 `AISOC_API_SERVICE_TOKEN`。值不进入日志、文档或Git；与原API→Agents专用身份、五类十枚A/B reader分开，不替换旧凭据。该身份沿用固定源码既有七权限：`alerts:read`、`cases:read`、`connectors:read`、`actions:read`、`lake:query`、`hunts:read`、`threat_intel:read`；请求必须明确存在的tenant，工具闭包从Run取得tenant，模型不能通过工具参数选tenant。该配置不授予写入或执行权限，缺少实际日志/厂商来源仍记unavailable。candidate04已部署，[运行独审](../handoff/integrity-candidate04-runtime.json)及[六项HTTP](../handoff/integrity-candidate04-http.json)已通过。

本批另建C隔离租户及六枚≤8小时临时key（一个操作、五个目的独立reader）；仅新C有限验收使用，不更改原A/B额度、unknown或积压。完整意图位于同批私有 `b4-c-identity-r01/`，五reader目录为 `b4-c-readers-r01/`；结束撤销六枚并真实核401。C五类读取当前均success-empty，来源不足不写成已有真实资产/知识。


2026-10-21本批收尾：A/B两操作key及C六短期key已全部停用，逐枚真实HTTP401；旧十枚reader仍active/未过期，五类目的映射与原发行意图一致，永久七权限只读服务身份保持。脚本前审及撤后只读独审通过，见[净化回执](../handoff/integrity-final-key-revocation.json)。C旧意图/文件及失败材料仅作取证保留，不可作为可用凭据或重放许可。
