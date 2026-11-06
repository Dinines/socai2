# 告警事件与调查模块前后端交接指南 V1

本指南是业务后端、前端和调查模块开发者的共同入口。交付内容包括已确认的数据库结构、字段与查询合同、原产品页面功能及跳转、离线测试案例和调查运行记录。可以据此开始数据读取、页面绑定和按功能逐项联调；尚未接通的操作和模型质量问题按第八节继续验收。

数据库基线为 PostgreSQL 16 中 `socai2` schema 的 **29 张表、462 列**，对应迁移 **123–126**。原联调版本标签为 `frontend-backend-integration-v1`（`624a57de`）；本指南随其后的交接文档提交补充发布，不改写该标签或历史测试原件。本文的服务器信息来自 2026-11-06 保存的部署回执和启动配置；切换环境时以对应私有配置为准。

## 1 从哪里开始

| 接手工作 | 入口与用途 |
| --- | --- |
| 产品与前端功能 | [当前产品需求](docs/design/alert-incident-case-product-requirements.md)、[页面功能与跳转 V1](deliverables/investigation-validation-20261106/frontend-feature-list.md)：28 项功能 F01–F28、14 项跳转 J01–J14，以及输入 ID、目标页和空态。 |
| 业务后端取数 | [服务端数据交接 V1](docs/investigation/socai2-page-data-handoff-20261106.md)：权威表、联表关系、权限、分页、四段只读 SQL 和签收范围。 |
| 数据库定义 | [字段字典](docs/design/socai2-field-dictionary-20261103.md)、[机器可读字典](docs/design/socai2-data-contract-20261103.json)、[JSON 字段合同](docs/design/socai2-json-contracts-20261103.schema.json)。 |
| 数据库部署 | 21 的业务库使用[共享库安装与核验程序](deploy/database/install_aisoc21_v1.py)。新建独立库使用[V1 初始化 SQL](deploy/database/init_socai2_v1.sql)。使用条件见第三节。 |
| HTTP 合同 | [完整 OpenAPI](docs/design/socai2-independent-api-v2.openapi.json)。文件名中的 v2 是既有 API 合同版本；本次“联调 V1”是交付基线名称，不把 API 文件改名或视作另一套数据库。 |
| 字段有值和空值样本 | [字段取数清单](deliverables/investigation-validation-20261106/page-field-samples.md)：81 个主表字段及具体文件、JSON Pointer，含四案以外的补充正例。 |
| 下载案例与离线预览 | [版本交付入口](deliverables/investigation-validation-20261106/README.md)、[完整测试索引](docs/investigation/investigation-test-handoff-20261106.md)。 |
| 调查模块内部开发 | 生产连接与触发见第 2.1 节。[当前执行账本](docs/investigation/current-execution-ledger.md) · [21 生产部署与独立样本命令](deliverables/investigation-validation-20261106/processing-deployment.md) · [处理审计及剩余问题](deliverables/investigation-validation-20261106/processing-functional-audit.md)。 |

**产品页面和开发查阅页各有用途。** `prototypes/security-pages-v2/` 及产品需求说明承载原产品设计。4177 的“调查运行记录”用于开发者查看 Run、步骤、请求、原答和错误，不替代产品页面，也不作为重新设计产品功能的依据。后续前后端可按产品需求调整页面实现；调查模块可调整提示词、工具和内部步骤，但必须保持已确认字段、取值语义、关联关系和读取合同兼容。

## 2 数据在哪个环境

### 2.1 21 生产环境

21（`192.168.1.21`，SSH 别名 `sting-infra21`）的生产告警和调查共用 PostgreSQL 数据库 **`aisoc`**。Fusion 收到告警，先写 `public.alerts`。同一告警在调查模块的主表是 `socai2.alerts`，事件是 `socai2.incidents`。两处使用同一租户和业务 ID。后端查询本指南的告警、事件和 Case 字段时连接 `aisoc`，使用 `socai2` schema。

| 操作 | 触发方式和可查询的数据 |
| --- | --- |
| 收到一条新告警 | Fusion 提交告警并发布 `socai2.alerts.fused` 通知。接入进程从启用时的位置开始消费，按租户及 ID 核对已落库的原始快照，把告警、材料、来源、对象、工件、事件和成员关系写入 `socai2`。写入成功后才确认消息，重复投递沿用同一告警 ID。 |
| 分析告警、诊断事件 | 有权限的调用者分别执行 `alert`、`incident` 作业。此时才产生相应的 `runs`、`run_steps` 与工件。只有接入记录时，执行历史可以为空。 |
| 建立 Case 并执行调查 | 调用者执行 `case-create` 选择成员，再用 `case-prepare` 准备该轮，最后用 `case-start` 启动。按 `tenant_id` 和 `case_id` 查各轮，再按 `run_id` 查步骤和工件。Case 调查须显式启动。 |
| 查看运行进度 | 4177 工作台以专用账号 `socai2_prod_reader` 只读访问调查表。刷新页面只读取已经提交的记录，处理作业与工作台可以独立运行。默认查看业务租户 `00000000-0000-0000-0000-000000000001`。 |

生产处理作业使用 `socai2_prod_processor` 和 ClickHouse 的 `aisoc.raw_events`。读取原告警快照的接入进程使用 `socai2_prod_ingress`。生产安装已核对 V1 的 29 表、462 列和全部表的强制租户隔离。既有六张告警、事件相关表的结构与授权指纹与安装前一致。进程状态、消息消费和实际调查执行应分别核对。[接入进程](deploy/aisoc21/production_projection.py) · [按需作业](deploy/aisoc21/production_processing.py)

### 2.2 21 合成测试材料的来源

| 项目 | 地址或数据空间 | 用途及配置来源 |
| --- | --- | --- |
| 主机 | `192.168.1.21`，已有 SSH 别名 `sting-infra21` | 访问内网需要工作站到该主机的网络；当前只读交接也可完全使用第六节离线包。 |
| PostgreSQL | `192.168.1.21:5432`，数据库 **`socai2_processing_handoff`**，schema **`socai2`** | M01/S02/U03 合成测试及交接复查使用的独立数据库，运行角色为 `socai2_processing_job`。生产查询使用第 2.1 节的数据库和租户。 |
| PostgreSQL 依赖 | 同一数据库的 `public` schema | 租户、用户、API key/RBAC、资产、威胁情报、知识和用户风险等支持表；不计入 29 张调查表。 |
| ClickHouse | **`socai2_next_validation.raw_events`** | 此批测试读取的湖表，用户名为 `socai2_next_reader_20261104`。连接参数取测试作业 `runtime.env` 的 `CLICKHOUSE_*`。 |
| Redis | 取该作业 `runtime.env` 的 `REDIS_URL` | 复用配置中的基础设施；不作为案件、Run 或正式结果的权威存储。 |
| 模型 | 作业内 `http://litellm:4000/v1`，别名 `aisoc-investigation` | 21 网关转 43 的 `192.168.1.43:8000`，已保存路由为 Qwen3.5-9B 对应别名。协议 `chat_completions`、Schema profile `vllm_grammar_v1`。`litellm` 是容器网络名，不能直接当工作站地址。 |
| 测试作业入口 | `/opt/sting-aisoc-socai2/ops/processing.py` | 三案回执使用 `releases/processing-20261106-r3/processing_host.py` 按需执行。 |

固定租户为 `6aff0ef7-c670-5a84-a2ee-83d73e25b964`，测试操作者为 `0fa5e92d-8c36-5a4b-8bd4-8120b15356bd`。它们用于本次合成样例，不是所有部署的默认租户。[安装回执](docs/operations/socai2-processing-install-20261106.json) · [实际模型路由](docs/operations/evidence/ie-audit-20261106-a1/model-route.json)

另有历史独立验证库 `socai2_next_20261104`，其 API 配置在 `private/next-20261104/api.env`，21 上的 API 为 loopback `127.0.0.1:18020`。这不是上述 `socai2_processing_handoff` 库的 HTTP 服务。四案小模型试验也使用各自隔离库；复查四案优先按包内原件及 manifest，不用同名标题跨库关联。

### 2.3 本机 Mac 验证环境

| 服务 | 本机连接 | 数据空间与身份 |
| --- | --- | --- |
| PostgreSQL | `127.0.0.1:15432` | **`socai2_local_20261105`**；schema `socai2`。API 角色 `local_socai2_api`，Fusion 角色 `local_socai2_fusion`。 |
| ClickHouse | native `127.0.0.1:19000`；HTTP `127.0.0.1:18123` | **`socai2_local_validation.raw_events`**；读角色 `local_socai2_reader`、写角色 `local_socai2_writer`。 |
| Kafka | `127.0.0.1:19092` | `socai2.local.20261105.alerts.raw`、`.raw_events`、`.alerts.fused`；Fusion group 为 `socai2.local.20261105.fusion`。 |
| Redis | `127.0.0.1:16379`，DB 0 | 专用本机容器，不清空历史数据。 |
| API / Fusion | `127.0.0.1:18020` / `127.0.0.1:18021` | API 前缀 `/api/v1/socai2`；Bearer API key 认证。运行代码来自本机 checkout，不会因 Git 更新自动重启。 |
| 产品原型 / 运行记录 | `127.0.0.1:4174` / `127.0.0.1:4177` | 产品原型默认读取保存的样例。4177 可以按第七节启动，查看数据库中最近更新的 Case，也可离线浏览导出的记录。 |
| 模型 | 当前私有配置为 DeepSeek `deepseek-flash` | `deepseek_responses / standard`。改测内网已部署模型只切模型配置，过程数据仍可留本机；新测试需独立批次和明确额度。 |

连接地址和角色由 [config.py](deploy/local-investigation/config.py) 组装，容器端口见 [compose.yml](deploy/local-investigation/compose.yml)，应用启动见 [run.py](deploy/local-investigation/run.py)。当前知识查询使用 PostgreSQL 全文检索：以冻结告警标题构造检索词，读取知识文档；没有向量库、Embedding、Neo4j 或 OpenSearch 的必需前置依赖。来源查询是否实际执行，以该 Run 的步骤和工件为准。

## 3 表结构与初始化

### 3.1 29 张表的功能分组

| 功能 | `socai2` 表 |
| --- | --- |
| 告警、材料、对象、分诊与人工反馈 | `alerts`、`alert_materials`、`alert_source_refs`、`alert_objects`、`alert_assessments` |
| 事件、成员及诊断 | `incidents`、`incident_alerts`、`incident_diagnoses` |
| 案件、成员、当前判断及来源 | `cases`、`case_alerts`、`case_incidents`、`case_assessments`、`case_assessment_sources`、`case_assessment_members` |
| 执行、冻结成员、步骤和工件 | `runs`、`run_members`、`run_steps`、`artifacts` |
| 正式结果及结果成员 | `results`、`result_members` |
| 人工任务和版本 | `tasks`、`task_revisions` |
| 助手会话、消息及探索画布 | `conversations`、`messages`、`graph_explorations` |
| 活动、目标前后值、评论和响应关联 | `activities`、`activity_targets`、`comments`、`response_links` |

数据库名和 schema 名不同。线上查询案件时，先连接数据库 `aisoc`，再查询表 `socai2.cases`。所有联查限定授权 `tenant_id`，再按主体 UUID 和明确保存的指针关联。案件信息看 `Case`，每轮执行看 `Run`，正式结果看 `Result`，当前采用的判断看 `assessment`。

### 3.2 部署文件

| 文件 | 职责 |
| --- | --- |
| [21 业务库安装程序](deploy/database/install_aisoc21_v1.py) | 在已有公共表的 `aisoc` 中安装冻结的四个迁移，以单一事务建调查对象和[运行角色授权](deploy/database/aisoc21_processing_access.sql)。`inspect` 看安装前目录，`rehearse` 完整预演后回滚，`apply` 提交，`verify` 复核目录、权限和既有告警表指纹。 |
| [init_socai2_v1.sql](deploy/database/init_socai2_v1.sql) | 在新的、独立的 UTF-8 PostgreSQL 16 数据库初始化已确认 V1；包含公共依赖、123–126 和校验。完整 V1 再运行只核对，部分安装或结构不符会拒绝。 |
| [123](services/api/migrations/123_socai2_page_data_model.sql) | 原始调查 schema 基线。 |
| [124](services/api/migrations/124_socai2_case_source_binding.sql)、[125](services/api/migrations/125_socai2_baseline_input_freshness.sql)、[126](services/api/migrations/126_socai2_case_page_data.sql) | 依次补 Case 来源命名空间、更新采用前的新鲜度判定、补分类/期限/当前证据索引指针；保留历史迁移原件。 |
| [ORM](services/api/app/models/socai2.py) | 应用中的表映射。 |
| [目录回查 SQL](docs/operations/read_socai2_v1_catalog.sql) | 查询列、约束、索引和 RLS 等实际目录，用于和 V1 定义对账。 |
| [Case 回查 SQL](docs/investigation/socai2-page-data-readback-20261106.sql) | 当前判断、证据目录及相关表的只读联查。 |

在已配置 21 的 SSH 工作站从仓库根目录执行 `python deploy/aisoc21/deploy_production_services.py apply`，可统一安装数据库、同步服务、按需作业和工作台。使用 `verify` 可单独检查服务与数据库。仅需复核表结构时，执行 `python deploy/database/install_aisoc21_v1.py verify`。[统一部署入口](deploy/aisoc21/deploy_production_services.py) · [独立消费组配置](deploy/aisoc21/compose.production-projection.yml)

若部署目标是新建的**独立空库**，以有权建表的身份运行下列命令。

```sh
psql -X -d your_investigation_db -f deploy/database/init_socai2_v1.sql
```

连接主机、用户和口令通过部署方的受控连接配置提供。脚本不创建业务租户、案例、运行账号或口令；这些由部署方单独配置。已有调查数据的库先做目录比对，不套用“空库初始化”来修补。运行角色、最小权限和租户 RLS 必须按交接方案设置，不能将建表 owner 当业务读账号。

本机验证环境通过迁移 126 形成完整的 462 列。`deploy/local-investigation/prepare.py` 单独运行只准备 123–125。复查本机既有案例时直接读取即可；正式部署按第 3.2 节区分 21 共享业务库和独立空库。

### 3.3 后续变更规则

V1 已经人工确认。新增、删除或修改表、字段、类型、默认值、可空性、键、约束、索引、关系和隔离规则，都必须先在 OpenSpec 记录原因、影响字段、旧数据和页面查询影响，取得项目负责人对明确范围的人工确认，并记确认人和日期。确认后用新的增量迁移，保留 V1 原件。普通“继续推进”、自动评审或测试通过不能替代该确认。[项目规则](AGENTS.md#调查数据库-v1-与人工确认)

## 4 连接配置与凭据保管位置

以下只交接文件位置和变量用途。真实口令、Token、完整含口令 DSN 不进入 Git、页面、截图或测试包；新接手者通过项目负责人或环境维护者取得对应权限和私有配置。

| 环境与文件 | 应取哪些项 | 用途 |
| --- | --- | --- |
| 21 `/opt/sting-aisoc-socai2/private/processing-production/` | `runtime.env`、`ingress.env` | 前者给按需处理作业，后者给生产告警接入进程，均连接业务库 `aisoc`。执行业务命令时由调用者提供其租户范围的 API key。 |
| 21 `/opt/sting-aisoc-socai2/private/production-workbench/reader.env` | `SOCAI2_AUDIT_DATABASE_URL` | 4177 使用独立只读身份、TLS 和生产租户读调查表。 |
| 本机 `.local/local-investigation/private/runtime.env` | `API_DB_PASSWORD`、`FUSION_DB_PASSWORD`；`CH_READER_PASSWORD`、`CH_WRITER_PASSWORD` | 对应第二节固定运行角色；`DATABASE_URL` 由 `config.py` 组装，不直接存于该文件。 |
| 同一本机文件 | `PG_ADMIN_PASSWORD`、`CH_ADMIN_PASSWORD` | 本机基础服务管理凭据，不给业务页面或普通 API 使用。 |
| 同一本机文件 | `READ_API_KEY`、`API_KEY` | 前者用于已有只读接口；后者包含业务写权限，不能作为前端静态文件常量。 |
| 同一本机文件 | `OPENAI_BASE_URL`、`OPENAI_MODEL`、`OPENAI_API_KEY`、`SOCAI2_MODEL_PROTOCOL`、`SOCAI2_MODEL_SCHEMA_PROFILE` | 五项共同确定模型后端；模型密钥与业务 API key 不互换。 |
| 21 `/opt/sting-aisoc-socai2/private/processing-handoff/runtime.env` | `DATABASE_URL`、`SOCAI2_SERVICE_DATABASE_NAME`、`SOCAI2_PROCESSING_DB_ROLE`、租户/操作者变量、`CLICKHOUSE_*`、`SOCAI2_LAKE_DATABASE`、`REDIS_URL`、模型变量 | 第 2.2 节合成测试作业的连接配置。完整 DSN 含密码，禁止直接打印。 |
| 21 同目录 `db-password` | `socai2_processing_job` 的数据库密码 | 与上述交接库运行角色配对，不是历史 next 库密码。 |
| 21 同目录 `job-key` | 作业的服务身份 key | 容器只读挂载到 `/run/processor/key`，通过 `SOCAI2_PROCESSING_API_KEY_FILE` 指定。不是已提供的对外 HTTP 入口。 |
| 21 `/opt/sting-aisoc-socai2/private/next-20261104/api.env`、`identity.json` | 历史独立 API 的运行配置和身份材料 | 处理作业从 `api.env` 选取部分已有湖、Redis、CA、网关配置，再生成自己的 `runtime.env`；不要混用两套库和角色。 |
| 21 `/opt/sting-aisoc-socai2/certificates/socai2-ca.crt` | 服务连接的 CA 公证书 | 作业挂载到 `/run/certs/ca.crt`；TLS 参数保持对应环境配置，不能照搬本机 `sslmode=disable`。 |

本机私有目录按 0700、文件按 0600 管理，已被 Git 忽略；从 Git 下载代码不会得到这些文件。较早的 `.local/configuration/2026-10-20/` 和 `docs/operations/configuration.md` 是历史环境索引，不能覆盖本节的 V1 交接对象。没有凭据时先使用离线案例即可进行字段和页面开发。

## 5 接口与数据库功能代码

| 能力 | 实现位置 |
| --- | --- |
| 最小 API 应用 | [socai2_main.py](services/api/app/socai2_main.py)；正式合同统一前缀 `/api/v1/socai2`。 |
| 告警、事件字段及相关记录 | [page_reader.py](services/api/app/socai2/page_reader.py)、[page_contracts.py](services/api/app/socai2/page_contracts.py)、[socai2_pages.py](services/api/app/api/v1/endpoints/socai2_pages.py)。 |
| A/I 分析目录、Run 和工件 | [stage_reader.py](services/api/app/socai2/stage_reader.py)、[stage_read_contracts.py](services/api/app/socai2/stage_read_contracts.py)、[socai2_analysis.py](services/api/app/api/v1/endpoints/socai2_analysis.py)。 |
| Case、历史、Run、Result | [case_reader.py](services/api/app/socai2/case_reader.py)、[case_contracts.py](services/api/app/socai2/case_contracts.py)、[socai2_cases.py](services/api/app/api/v1/endpoints/socai2_cases.py)。 |
| 当前判断、分类、期限、证据计数 | [case_data.py](services/api/app/socai2/case_data.py)、[case_data_contracts.py](services/api/app/socai2/case_data_contracts.py)、[证据 JSON Schema](services/api/app/socai2/case_evidence.schema.json)。 |
| 建案、准备、启动、成员关联与移动 | [case_service.py](services/api/app/socai2/case_service.py)、[case_relations.py](services/api/app/socai2/case_relations.py)。 |
| 人工任务与修订 | [human_task_service.py](services/api/app/socai2/human_task_service.py)、[human_task_contracts.py](services/api/app/socai2/human_task_contracts.py)、[socai2_tasks.py](services/api/app/api/v1/endpoints/socai2_tasks.py)。 |
| 调查内部执行与模型交换 | [socai2 模块目录](services/api/app/socai2/)、[当前执行账本](docs/investigation/current-execution-ledger.md)，按 Run 和 Step 留存，不把内部函数名作为页面固定字段。 |

读权限为 `alerts:read` 或 `cases:read`；告警/事件关联 Case 的出口同时要求 `cases:read`。写操作经服务命令、租户校验、幂等键及相应版本条件执行。后端可组装多个读取结果满足页面，例如 Case 历史需要额外组合相关 A/I；这是明确的聚合工作，不应假设单个 `/history` 已含全部执行。

保持这些语义：当前判断沿 `cases.current_assessment_id`；正式结果沿 `results.source_run_id`；步骤按 `run_steps.run_id/seq/parent_step_id`；原件用版本和实际工件 ID。`null`、未接入、有效空数组、有效计数 0 和 HTTP 失败分别处理。Run 状态、交付完整性、结论来源、模型覆盖和案件管理状态不能合为一个“成功/失败”。GET 不触发调查或隐式补写。

## 6 测试数据与离线使用

所有案例均为构造数据，执行和保存过程按各包回执区分真实模型、真实基础设施及确定性替身。模型输出不是预设真值；不可因有结论就认定语义质量合格。

| 数据包 | 解压后的阅读入口 | 适合验什么 |
| --- | --- | --- |
| [21 小模型四案包](deliverables/investigation-validation-20261106/21-qwen9b-handoff-cases-20261106.zip) | `README.md`、`preview/index.html`；每案 `cases/<编号>/export/database.json`、`three-page-gets.json`、`api-responses.json` | 8 告警、4 事件、15 Run、3 Case、1 正式 Result；已发布、拒收、超时、未建案以及关联跳转。 |
| [21 单案包](deliverables/investigation-validation-20261106/21-qwen9b-pilot-20261106.zip) | `preview/index.html` 和对应预览页 | A/I 已发布、Case 在模型调用前容量停止；27 份 GET 保存记录。 |
| [三案处理审计包](deliverables/investigation-validation-20261106/ie-processing-audit-20261106.zip) | 包内 `docs/operations/evidence/ie-audit-20261106-a1/`；当前开发查看页见第七节 | M01/S02/U03 共 10 Run、62 步骤、130 工件，C3 超时及 C6 系统收尾。受控成功链、拒收链和人工版本另列，不混作真实模型成功。 |
| [历史与数据合同包](deliverables/investigation-validation-20261106/socai2-investigation-tests-20261106.zip) | `START_HERE.md`；13 个本机模型批次和 4 个无模型合同 Case 分列 | 模型来源当前判断、图谱、分类/期限、证据及威胁计数、人工反馈；补齐四案中为空的字段。 |

完整解压后再开预览，保留相对路径。离线页来自保存的数据导出，不会连接 21 或调用模型。JSON 快照是对账和接口样例，不是可直接执行的 SQL 全库备份；不要把原租户和 ID 不加区分地导入生产库。

在项目根目录复核原交接包，并可导出 48 份已保存 GET 响应体和 4 份字段合同样例：

```sh
.local/conda-envs/socai2/bin/python docs/operations/check_investigation_handoff.py
.local/conda-envs/socai2/bin/python docs/operations/check_investigation_handoff.py --examples-dir .local/handoff-v1-api-examples
```

第二条输出目录须尚不存在；没有本机 Conda 环境时使用可用的 Python 3.9+，该检查脚本仅使用标准库。生成的 `index.json` 标明响应出处、路径与身份。先用保存响应做前端绑定，再用目标环境同权限 API 对账，不能把旧快照当作实时接口返回。

本机新测试过程通常保存在 `.local/local-investigation/validation/<批次>/`，包含计划、导出和回执；21 三案的公开原件已在 `docs/operations/evidence/ie-audit-20261106-a1/`。这些私有工作目录不随 Git 自动交接，需使用上述已提交的包。后续复测创建新的批次和操作键，保留旧失败、unknown 和用量未知；按 [后续计划](openspec/changes/complete-socai2-investigation-chain/publication-20261106.md) 先明确范围与额度。

## 7 本地查看页面

在能通过 SSH 访问 21 的工作站，从仓库根目录启动下列程序，即可打开[调查运行记录](http://127.0.0.1:4177/)。

```sh
python docs/operations/serve_processing_workbench.py --source aisoc
```

生产页从 21 的 `aisoc.socai2` 读取当前租户最近更新的五个 Case，可继续加载。选中 Case 后，每 15 秒检查已提交的运行、步骤和工件等记录；有变化才刷新该案文件，每案保留最新一份。流程节点链接到各步输入、输出与错误。告警和事件 ID 入口搜索已发布的主体快照，可在案件内核对成员和各自的执行记录。生产页使用独立缓存；尚未建案时，Case 列表为空。复查 M01/S02/U03 可打开交接包或用 `--source 21` 查询独立交接库。

在 21 上，4177 只绑定 `127.0.0.1`。需要查看服务器上的工作台时，在本机 4177 空闲的情况下运行 `ssh -N -L 127.0.0.1:4177:127.0.0.1:4177 sting-infra21`，然后打开同一地址。[工作台访问、快照与离线用法](deliverables/investigation-validation-20261106/README.md#调查运行记录页)

若需在独立资料页查阅测试人员交付的快照，可从本地批次更新静态站点。

```sh
python3 docs/operations/update_processing_audit.py --batch "本次测试导出目录"
```

该命令读取本地快照并更新静态文件；不同测试使用独立批次，同一快照重复导入去重。`--plan` 在本地无快照时可能通过 SSH 从 21 只读导出，离线查看优先用 `--batch`。保留原有批次，不把受控替身混入实际测试列表。[完整用法](deliverables/investigation-validation-20261106/README.md#调查运行记录页)

产品原型可另外启动，仍使用原有模板：

```sh
python3 -m http.server 4174 --bind 127.0.0.1 --directory prototypes/security-pages-v2
```

若端口已被对应服务占用，直接打开已有页面，不重复启动或停止其他进程。4174 的静态导出与真实服务模式需要分别签收；4177 的可读性不代替原产品页的功能验收。

## 8 联调签收顺序与剩余事项

1. 对齐数据库名、schema、租户和读权限，用字段字典及目录 SQL 核对 V1；无权访问服务器时先用离线包。
2. 按 F01–F28/J01–J14 绑定列表、详情、材料、当前判断、执行和正式结果，逐页核对至少一个有值和一个缺值场景；关联 ID 和分页口径须一致。
3. 用四案 Q01–Q04 核正常读取、未建案、分诊拒收、超时及系统判断；用历史与合同样例补模型结论、图谱、证据计数和人工版本。
4. 再按相应命令接建案、成员变更、准备/启动、分类/期限、H 任务等写操作；确认写后读回和版本冲突。页面查看不自动执行流程。

以下已知项保留在联调清单，不因此修改已确认表结构：

| 剩余项 | 当前边界与后续验收 |
| --- | --- |
| 原页四处显示差异 | 事件概览缺本次 I 诊断入口；有效严重度 `medium` 显示；Run 的 `none` 与字段缺失区分；无效告警 ID 的未找到及返回。见功能清单末尾，正式页面签收前关闭。 |
| 聚合及部分写回 | Case 的完整 A/I/C 历史、活动、全局运行列表等由业务后端组合；通用管理、协作附件、受控下载、探索保存及外部响应接线分别验收。对应存储位置已有说明，有表不等于接口已完成。 |
| 案件助手 | 提问、保存回答、显式采用三个预留入口目前返回 501，页面应标未开放。 |
| 证据索引生产 | 有合同及样例，不表示每个模型 Run 自动产出索引；缺索引保留 `not_recorded/null`，不能显示成已核对的 0。 |
| 模型结果质量 | 21 三案 C3 均 HTTP 408，已有系统收尾和当前待核判断，正式模型 Result 为 0；历史 DeepSeek 存在范围拒收和效果扩大。模型质量单独回归，不更改旧原答或伪造结果。 |
| 服务接入 | 21 区分告警接入进程、按需处理命令和 4177 只读工作台。联调应分别记录 Kafka 接入成功的告警/事件 ID，以及显式启动的 A/I/Case 的 Run ID。产品业务 HTTP 的接线由业务后端负责。 |

[完整测试交接及责任边界](docs/investigation/investigation-test-handoff-20261106.md) · [三案问题证据](deliverables/investigation-validation-20261106/processing-functional-audit.md) · [后续修复与模型计划](openspec/changes/complete-socai2-investigation-chain/publication-20261106.md)

## 9 Git 发布与父项目引用

子项目为 `Dinines/socai2`。本轮交付复核通过后，将 `codex/case-baseline-history-20261103` 的成果合并到 `main`。父项目为 `wangjuelong26/SpiritHub`，用户指定更新现有 **`add-server-submoudle`** 分支的 **`server`** 子模块指针；`.gitmodules` 中子模块名为 `socai2`，路径为 `server`，跟踪 `main`。

父项目提交只需将 gitlink 指向已在 socai2 远端存在的提交，不把父项目复制进本仓库，不重复发布父项目源码，也不修改父项目 `main`。最终发布身份以两仓库的实际提交 SHA 和远端分支核对为准。
