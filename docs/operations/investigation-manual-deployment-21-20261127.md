# 21 调查服务手工部署与恢复手册

当前发布入口：2026-11-28 的[完整 main 版本发布](#12-完整-main-版本发布2026-11-28)，覆盖 SpiritHub 前端、平台后端、调查 HTTP、Fusion、调查执行和已有模型代理。构建来源必须是本轮最终推送并读回的两个 main 提交，不能用先前的局部候选代替。当前阶段完成源码整合及发布交接不等于已切换全部线上服务。

第 1–11 节保留 2026-11-27 D1/D2/D3 演练原件，**其中“当前基线”、新空库、容器名和恢复结论仅适用于该历史批次**。该批部署、一次 Case 测试及原服务恢复已执行，恢复独验通过，Case 因容量超限未通过；后续修正与实际结果见 [PROGRESS](../../PROGRESS.md)。本轮沿现有库升级，不额外建库。[历史阶段安排](../../openspec/changes/complete-socai2-investigation-chain/deployment-readiness-20261127.md) · [D1 准备](evidence/investigation-manual-d1-20261127-01/README.md) · [D2/D3 回执](evidence/investigation-manual-d2d3-20261127-01/README.md)

## 1. 部署什么

| 组件 | 本次操作 | 对外入口与职责 |
| --- | --- | --- |
| 调查 HTTP | 独立打包、停原容器、启动候选、验证并恢复 | `investigation_http.main:app`；正式宿主端口 `18024`、容器端口 `8000`；受理显式业务操作、查询保存结果 |
| A/I/Case 联合执行器 | 独立完整包与一个 dispatcher；停止和恢复只针对本次记录的原实例 | `python -m app.socai2.analysis_dispatch_runtime --profile <绝对路径>`；没有对外 HTTP 监听 |
| PostgreSQL、Redis | 复用现有服务实例，准备新空验收库及独立 Redis 逻辑库 | 不重启数据库，不清空原库/原队列 |
| 模型网关、推理/tokenizer、ClickHouse、知识依赖 | 按当前受控配置连接 | 不重新部署模型或湖，不开启新的知识后台消费 |
| Kafka/Fusion、SpiritHub 前后端、4177 查阅 | 保留运行；批准样本可经已有一次接收工具进入新库 | 不部署平台，不修改常驻消费者或其目标库；4177 用于核对实际 Run |

HTTP 不启动分析循环，也不承担模型执行。平台后端访问调查 HTTP，浏览器不直接访问模型或调查数据库。

## 2. 从 Mac 连接 21

本次 D1 已验证的接入使用现有 SSH 跳板别名，不假设 Mac 已连业务 VPN：

```sh
ssh -J sting-win57 sting-infra21-direct
```

本次路径是 Mac → Windows SSH `22` → 21 的 SSH；命令中的 `-J` 明确指定跳板，目标别名中的 `direct` 不表示 Mac 直接连 21。另有 `sting-infra21` 经 Windows `2221` 转发的既有路径，本次不以旧记录替代其当前连通核验。别名、既有备用路径和隧道排障按[SSH 接入说明](mac-ssh-relay-20261107.md)。不要重新生成或复制私钥。

需要从 Mac 查候选 HTTP 时，选择未占用的本地端口，将其显式转发到所选 21 HTTP 绑定：

```sh
# 三个变量来自本轮受控连接配置；本地绑定只用回环地址。
ssh -N -o ExitOnForwardFailure=yes \
  -L "127.0.0.1:${REVIEW_HTTP_LOCAL_PORT}:${REVIEW_HTTP_REMOTE_HOST}:${REVIEW_HTTP_REMOTE_PORT}" \
  -J sting-win57 sting-infra21-direct
```

命令前台保持，结束时只关闭该隧道。已有 4177/8080 隧道不重复建立。SSH 是访问通道；PG 自身的 `ssl=require`/`sslmode=require` 是另外一层连接配置，两者不混用。21 内部服务使用其可达地址，不把 Mac 的 `127.0.0.1:28085`、`64875` 等临时代理地址写进正式配置。

## 3. 当前恢复基线

下表取自 2026-11-27 的已有回执和一次只读快照，执行窗口前再核对。[核心核对明细](evidence/incident-input-m0b-release-assessment-20261127-01/core-deployment-notes.md)

| 项目 | 当前基线 |
| --- | --- |
| 原 HTTP | `socai2-http-incident-saved-diagnosis-read-20261126-01`；正式合同 83 个业务操作 |
| 原唯一 dispatcher | `socai2-analysis-incident-diagnosis-live-20261125-01`；镜像 `sha256:3688f5ad8c2c2144abe88ef5ce7c717f20de6a73130c2a40c9d2bf67a297cdf7` |
| dispatcher 入口 | 工作目录 `/app`；`python -m app.socai2.analysis_dispatch_runtime --profile /run/c173-release/config/dispatcher.json` |
| Docker 网络 | `socai2_default`；dispatcher 没有端口映射 |
| 原数据库 | 既有 PostgreSQL 的 `aisoc` 库、`socai2` schema；实际主机/端口/账号从原受控连接文件取 |
| 已挂载的核心修正 | A 提示 `alert-input-v1.json` 与 `token_budget.py`；完整源路径和目标路径见核心核对明细 |
| 尚未上线的 I 配置 | M0b `incident-input-v1.json`；线上仍为镜像中的旧文件，不能把本地通过写成线上已生效 |

18:50 的快照中：在途 task/attempt、未结束冻结 Run/Case 和相关 Redis 队列均为空。这个结果不能替代实际停机前的核对，也不保证后续没有新任务。

## 4. 与 SpiritHub 后端交接

正式链路：前端同源 `/api/v1/socai2` → SpiritHub 后端 bridge → 调查 HTTP。平台侧只需对接 HTTP，不需要复制调查数据库或模型连接。

| 平台配置 | 填写要求 |
| --- | --- |
| `SPIRITHUB_SOC_HTTP_BASE_URL` | 调查 HTTP 的可达 origin，如当前 `http://192.168.1.21:18024`；不附加业务前缀，bridge 会追加 |
| `SPIRITHUB_SOC_HTTP_TRUSTED_READS`、`SPIRITHUB_SOC_HTTP_TRUSTED_ORIGIN` | 沿现有可信接入设计；启用时 origin 与 base URL 一致 |
| `SPIRITHUB_SOC_TENANT_ID` | 与本轮 HTTP context、数据库身份一致 |
| `SPIRITHUB_SOC_HTTP_CREDENTIALS_FILE` | 受控映射文件，根是数组 `list[BridgeIdentity]`，每项含 `local_user_id/upstream_user_id/tenant_id/token`；两种 user ID 分别唯一，tenant 与平台配置一致，token 非空。文件不能有组/其他用户访问位；真实值不进手册或 Git |
| `SPIRITHUB_SOC_HTTP_TIMEOUT_SECONDS`、`SPIRITHUB_SOC_HTTP_EXECUTION_TIMEOUT_SECONDS`、`SPIRITHUB_SOC_HTTP_MAX_RESPONSE_BYTES` | 使用本轮显式配置；不能靠延长超时掩盖接口错配 |

平台保留自己的登录及用户映射。调查 HTTP 使用 `SOCAI2_HTTP_CONTEXT_FILE`，字段为 `tenant_id/actor_id/actor_name`，没有独立登录/换 Token 路由。当前 bridge 走可信读写必须同时满足 `SPIRITHUB_SOC_HTTP_TRUSTED_READS=true` 与 `SPIRITHUB_SOC_HTTP_TRUSTED_ORIGIN=SPIRITHUB_SOC_HTTP_BASE_URL`；只开前者可能使 GET 正常，但写请求仍走旧 `auth/me` 验证并失败。两端身份和具体业务路由也须一致；可信配置不证明全部写入口已接好。

此次演练优先复用原 HTTP origin，原 HTTP 停止后候选占用同一绑定，恢复时原容器取回；新库须准备与所选 context 一致的原生身份。这样不需要部署平台。若改用候选新端口，先直接验调查服务；平台切 origin 是单独配置动作，须记录原值和恢复方式。

当前 8181 使用本地分流代理，运行代码与工作目录存在差异，概览/采用等仍有旧接口接线，不能用其任意页面请求作为调查部署成功的唯一标准。[具体差异](evidence/investigation-release-readiness-20261127-01/README.md)

## 5. 配置文件清单

以下所有地址、端口、库名、模型和开关都写入本批 profile 或受控环境文件；密码、Token、DSN 放权限受控且忽略提交的文件。不要从旧说明复制示例值作为当前实际配置。

| 文件/配置 | 必须明确的内容 |
| --- | --- |
| HTTP 发布 JSON | `bind/port/container_port/entry/release/root/project/container/image/network/reference_container/base_image`；显式 `database/database_host/database_port/postgres_sslmode`；完整源码包、挂载、日志及预期合同。候选 `project` 和 `container` 均独立于原服务 |
| HTTP 私密 runtime JSON | `DATABASE_URL`、`SOCAI2_CASE_DATABASE_URL` 必须同一新库；`SOCAI2_SERVICE_DATABASE_NAME` 一致；不照搬本机只读候选的禁写开关 |
| HTTP context | 已存在于新库的 `tenant_id/actor_id/actor_name`；与平台映射一致 |
| HTTP 功能开关 | 按本轮业务启用 `SOCAI2_CASE_API_ENABLED/SOCAI2_PAGE_READ_ENABLED/SOCAI2_ANALYSIS_READ_ENABLED`；`SOCAI2_STAGE_EXECUTION_ENABLED`、`AISOC_STARTUP_SCHEMA_MIGRATIONS`、`AISOC_DEV_AUTH_BYPASS` 沿既有架构关闭 |
| 公用业务配置 | 同版 `SOCAI2_ANALYSIS_TASKS_CONFIG_FILE`、`SOCAI2_CASE_ALLOCATION_CONFIG_FILE`、`SOCAI2_RUN_RECORDS_CONFIG_FILE`、`SOCAI2_SUBJECT_RISK_CONFIG_FILE`、人员目录、日志 profile |
| dispatcher JSON | `enabled/tenant_id/database_url_file/database_connect_args/database_pool_size`；Redis URL 文件、两个连接超时；`lifecycle_policy_file/executor_factory/executor_config_file/logging_profile_file/dispatch` |
| dispatcher 的 `dispatch` | 显式 `namespace/max_running_tasks/poll_interval_seconds/execution_timeout_seconds/replenish_limit/priorities/receipt_directory/lock_file`；新库独立 namespace、锁和可写回执目录 |
| 执行器 JSON | `app.socai2.analysis_case_executor:executors`；A/I/Case 同一候选 PG 与策略，保留正常扫描/预算；不新增测试对象判断 |
| PG 安装 TOML | 显式数据库、owner/reader/writer/ingress 角色，`cleanup/analysis/analysis_ingress`，连接环境及 `PGPASSFILE`；不把建库和 LOGIN 角色创建误记为安装器能力 |
| 湖查询/接收 profile | PG 目标、ClickHouse 库、`scopes[].tenant_id/source_namespace/mapping_version`、同版查询 `transport`；新 PG 不会自动隔离湖数据 |

HTTP 使用 SQLAlchemy，驱动由实际连接 URL 和镜像依赖决定；本次原服务与候选读写连接均使用 `postgresql+asyncpg://`，不能假定基镜像已安装 psycopg。dispatcher 同样使用 asyncpg 及独立 `database_connect_args`。asyncpg 的 `ssl/timeout/server_settings` 不能照搬 libpq 的 `sslmode/connect_timeout/options`。本批 HTTP 普通读写和入站角色已实际连接新库，驱动探针的先前失败与修正回执均保留。

### 模型和工具连接

| 配置 | 对接说明 |
| --- | --- |
| `OPENAI_BASE_URL/LLM_BASE_URL`、`OPENAI_MODEL/LLM_MODEL/AISOC_LLM_MODEL` | 从本轮私密运行环境和已有租户模型覆盖确定最终路由；记录选定来源，不仅核某个环境变量 |
| `OPENAI_API_KEY/LLM_API_KEY`、需要时的 `LLM_GATEWAY_URL/LITELLM_MASTER_KEY` | 复用当前已验证凭据引用，不在命令行输出；区分网关凭据和供应商凭据 |
| `SOCAI2_INVESTIGATION_POLICY` 与执行器 `investigation_policy_file` | 指向同一冻结 TOML；包括上下文窗口、准备输入上限、每步输出和 Run 预算 |
| `SOCAI2_MODEL_PROTOCOL/SOCAI2_MODEL_SCHEMA_PROFILE` | 与策略中的 `model.protocol/schema_profile` 一致 |
| `model.tokenizer.endpoint/served_model/authentication/timeout_seconds/safety_tokens` | 与真实生成后端一致；不能拿网关 alias 代替 tokenizer 的真实后端名 |
| 湖/知识 | `SOCAI2_LAKE_QUERY_PROFILE_FILE`、`CLICKHOUSE_DATABASE` 等现有连接；已启用知识源所需 PG/embedding/Qdrant 与 `SOCAI2_KNOWLEDGE_PROFILE` 按当前配置保留 |

本次不通过放大额度来绕开问题。当前容量修正已上线，实际额度与来源见[核心核对](evidence/incident-input-m0b-release-assessment-20261127-01/core-deployment-notes.md#3-模型计量与必要依赖配置)。C4 v2 从湖查询 profile 取 `transport`；不能因主策略没有旧 v1 的 `query_transport` 就改动已验 v2 路径。

## 6. 先保留可恢复的原环境

本批受控配置中记录原容器名称和完整 ID、镜像 ID、原运行状态、端口、网络、入口、工作目录、restart 策略、全部环境/挂载引用和指纹。完整 `docker inspect` 可能含凭据，只保存在 21 的私密目录，不输出到聊天或提交 Git。

```sh
# 在 21 执行；变量均从已审的本批操作配置读取，目录必须是新建的独立目录。
umask 077
mkdir -m 700 "$REVIEW_BASELINE_DIR"
docker inspect "$REVIEW_OLD_HTTP" "$REVIEW_OLD_DISPATCHER" \
  > "$REVIEW_BASELINE_DIR/containers.private.json"
```

逐一保留该 inspect 引用的配置、秘密文件、只读源码挂载、已有日志/状态目录；保存权限和 SHA-256。候选文件全部写到新发布目录，**不覆盖原挂载源文件**。原镜像和原容器不删除，恢复时直接使用原容器，避免靠手工摘抄少数环境变量重造。

原库额外备份使用已有受控 libpq service/passfile，在 21 本地生成 archive；文件不下载进聊天。命令在具备匹配版本 PG 客户端的既有环境执行；若客户端在数据库容器内，连接文件与备份目录也须在该执行环境可达，不假定宿主已安装客户端。备份配置须明确原库，不能误用候选库：

```sh
PGSERVICEFILE="$REVIEW_PG_SERVICE_FILE" PGSERVICE="$REVIEW_PG_BASELINE_SERVICE" \
  PGPASSFILE="$REVIEW_PG_PASSFILE" pg_dump --format=custom --file="$REVIEW_BASELINE_DIR/original-database.dump"
pg_restore --list "$REVIEW_BASELINE_DIR/original-database.dump" \
  > "$REVIEW_BASELINE_DIR/original-database.contents"
```

原库保持运行且不清理。本次回退靠恢复原服务与连接，不把这个 dump 覆盖回原库。备份目录列举只检查 archive 可读，不能声称已做完整灾备恢复演练。

## 7. 新空验收库及一笔测试的输入

默认选择 **现有 PG 实例＋新空数据库**，不用克隆旧任务库。新库名和角色写入 profile；由现有数据库管理员连接创建数据库与 LOGIN 角色，凭据留受控文件。随后使用[当前安装入口](../../deploy/database/CURRENT.md#新独立空库)：

```sh
python3 deploy/database/install_reader.py initialize-current --profile "$REVIEW_DB_PROFILE"
python3 deploy/database/install_reader.py verify --profile "$REVIEW_DB_PROFILE"
```

沿 [reader-install.example.toml](../../deploy/database/reader-install.example.toml) 填写完整配置。使用当前新装和增量至 136，保留 V1 原件；不能只建 V1 的 29 表。此模式只用于新空专用库，不对原共享库运行。

准备正常功能所需的原生 tenant、actor、连接器、资产与人员目录。可复用[参数化身份/访问 SQL](../../deploy/aisoc21/streaming-candidate-20261115-01/database-access.sql)，按其 `expected_database/reader_role/analysis_writer_role/tenant_id/actor_id/actor_email/actor_name/candidate_id` 参数绑定新库；它要求目标身份表和 Run 为空，仅用于初始化阶段。安装器的增量授予不等于全部业务写权限已经具备。

样本使用负责人已批准的 OCSF 原件及必要资产种子，保持正常原生字段；不写页面补偿逻辑，不复制旧 task/attempt/subject_state 或改旧失败。现有一次接收入口可以将**已落湖且整个 scope 都属于批准批次**的材料写入新 PG，登记正常 A/I 初诊和事件关系，不启动长期 Fusion/Kafka 消费者。需要其公共支撑时运行：

```sh
python3 deploy/database/install_reader.py fusion-support --profile "$REVIEW_DB_PROFILE"
# 在已核接收源码/依赖的独立环境内运行；目录和解释器均来自本批配置。
cd "$REVIEW_FUSION_SOURCE_ROOT"
PYTHONPATH="$REVIEW_FUSION_SOURCE_ROOT" "$REVIEW_FUSION_PYTHON" -B \
  -m app.workers.lake_alert_delivery --profile "$REVIEW_DELIVERY_PROFILE" --once
```

接收器必须同时绑定新库 DSN 与 `receive.postgres_database`，沿现有受控 `lake_alert_delivery --once`。`--once` 表示一个有界 cycle，**不是一条记录**；scope 扫描范围须先与批准批次对齐，不能以 `limit` 冒充样本筛选。若 scope 含本轮未选数据，准备步骤尚未完成，不能开始投递。

接收去重/归并使用固定 Redis 键前缀，因此本轮使用独立空 Redis 逻辑 DB/URL；只改 dispatcher namespace 不足以隔离接收。保留原 Redis，不执行 `FLUSHDB/FLUSHALL`。HTTP/执行器/入站/湖 scope 的身份与版本必须一致，新 PG 名称不会自动隔离既有湖材料。

新 dispatcher 配置先保持 `enabled=false`。样本接收后只读核本库待执行任务属于本轮；开启后会正常执行 A/I 及周期检查。当前没有“只执行指定 Case”或“执行一笔退出”的开关，`max_running_tasks=1` 只是并发限制。测试记录需包含必要前置 A/I，不能报告成仅一次模型调用。

不默认采用旧库克隆：调度启动会处理中断的旧 attempt、补装旧任务，并扫描 I/Case；Redis 空不代表没有待执行工作。为避免旧历史触发，不新增过滤规则或修改克隆任务来假装空闲。

## 8. 冻结和构建完整服务包

代码包与私密配置分开。冻结清单至少包括：源码 revision＋实际文件 hash、镜像 ID、完整 OpenAPI、模型/输入合同、全部 profile、依赖文件、日志/回执可写目录及原环境基线。不能只凭 commit 判断脏工作区版本，也不能把旧只读 profile 原样用于可写部署。

### 调查 HTTP

本机沿现有管理器打包完整 `app` 和 `investigation_http`，`complete_packages`、`runtime_environment_file`、`runtime_mounts`、`expected_source_hashes` 和合同必须显式冻结：

```sh
python3 deploy/http-service/manage.py --profile "$REVIEW_HTTP_PROFILE" \
  package --output "$REVIEW_HTTP_PACKAGE_DIR"
```

经已验证的 SSH 跳板通道传到新目录；`scp`/`sftp` 同样显式使用 `-J sting-win57` 和目标 `sting-infra21-direct`。在 21 包目录执行：

```sh
python3 manage.py --profile profile.json build
# 完成下一节停机条件后执行 prepare/start。
python3 manage.py --profile profile.json prepare
python3 manage.py --profile profile.json start
```

`build` 使用指定基础镜像，`--pull=false --network none`；`prepare` 生成私密 runtime.env、compose.json 和 before.json；`start` 含 verify。启动前已经生成完整候选配置、日志目录和精确挂载。`replace_existing=false`，候选 **Compose project 与容器名都必须是新的**；只换容器名仍可能被 Compose 按同一 project/service 替换原容器。原端口须先释放，不使用覆盖原容器的模式。

`runtime_mounts` 每项只能是存在的单个文件，带 `source/target/sha256`，不能用它挂整个配置/日志目录。启用 `SOCAI2_LOGGING_PROFILE_FILE` 时，该 JSON 文件须以只读文件挂载；另配 `logging_directory_mount`，且只含 `source/target` 两键，source 已存在、target 精确等于日志 profile 的 `directory`，作为独立可写目录。配置与目录的属主/权限须允许所选容器用户读取或写入。

管理器核对其他运行容器快照，所以**原两个调查服务先停，再 prepare；新 HTTP start/verify 完成后才启动新 dispatcher**。后续不能因为新增了本轮 dispatcher 又重跑整套“其他容器不变”断言；后续只核本轮健康、合同、实际加载和业务读取。

`prepare` 使用独占创建私密目录/文件，不能默认重复执行；`start` 的 verify 失败也不会自动回退。build/prepare/start 任一步失败即停止后续步骤并核实际状态，按第10节恢复。prepare 若已部分落盘，先确认具体产物，再决定使用已完整准备的包或新的独立批次目录；不覆盖旧文件、不盲目重跑同一命令。

D2实做发现原服务正常停止后，旧部署器的裸`socket.bind`探测返回`EADDRINUSE`。现有`manage.py`已将prepare/local共用探测改为`SO_REUSEADDR`，仍拒绝真实监听、不设置`SO_REUSEPORT`；两项本机直接验证和第二窗口实际prepare/start已通过。切换前先保存端口监听快照；若仍有真实监听，查明并恢复，不强占。该修正只涉及部署工具，D1业务镜像及配置不变；D1原工具与失败回执保留，第二窗口使用另存的已核工具。[修正独验](evidence/investigation-manual-d2d3-20261127-01/coordinator-port-probe-review.json) · [实际启动](evidence/investigation-manual-d2d3-20261127-01/http-step-02-switch-attempt-02.json)。

### 调查核心

沿已有完整源码包准备器与构建器，构建 profile 显式选择当前基础镜像、策略、独立 tag 和输出目录：

```sh
python3 deploy/aisoc21/prepare_processing_release.py --profile "$REVIEW_CORE_BUILD_PROFILE"
python3 deploy/aisoc21/rollout_transport.py --config "$REVIEW_CORE_TRANSPORT_PROFILE" processing upload
python3 deploy/aisoc21/rollout_transport.py --config "$REVIEW_CORE_TRANSPORT_PROFILE" processing build
```

准备器将当前 `services/api/app` 的 `.py/.json` 和既有接收依赖放入冻结包，不包含独立 `investigation_http` 或其运行 SQL 资源，不能代替上面的 HTTP 包。传输 JSON 显式填写 `local_processing/processing_release/remote_root/archive_limits/evidence/transport` 及命令超时；`transport.ssh_target` 使用既有 SSH 别名，limits 按实际 manifest 文件数/字节填写。传输器验证摘要与路径后写入新目录，再调用包内 `build_processing_image.py --release-directory <目录>`，不改变服务。

准确的构建/传输模板和一次接收入口另见[核心命令说明](evidence/incident-input-m0b-release-assessment-20261127-01/manual-command-shapes.md)。准备器不会自动生成完整运行部署。dispatcher 的本批 Compose/运行定义必须同时准备，使用显式 image/env/config/mount/network、持久日志/锁/回执目录。新镜像默认 ENTRYPOINT 是 `processing_job.py`；启动联合调度必须覆盖 entrypoint，不能只改 command：

```yaml
entrypoint: ["python", "-B", "-m", "app.socai2.analysis_dispatch_runtime"]
command: ["--profile", "/run/c173-release/config/dispatcher.json"]
```

环境中的 `SOCAI2_INVESTIGATION_POLICY` 与执行器的 `investigation_policy_file` 同指新包 `/opt/processor/investigation-policy.toml`；其余依赖配置与上表一致。其余参数沿当前完整 inspect 和运行模板逐项核对。**本次运行定义已在D1生成并以停用状态通过核验**，使用下述本批入口，不执行历史批次启动器。

新完整包应将已验 A 提示、计量修正及 M0b I 配置合入对应文件并核 hash；不能遗失现行只读挂载提供的已发布修正，也不把旧单文件挂载继续盖到新镜像的候选文件上。原容器及原挂载完全保留用于恢复。单独只发布 M0b 时可新增 I 文件只读挂载，但本手册的全轮重装须冻结完整候选，不把单文件发布当完整包验收。

旧 `install_processing_release.py` 有历史固定目录和 500 项包规模限制，当前完整处理包的静态清单已超过这一上限，因此使用上面的显式传输器。保留 manifest，不复制整棵活动工作区到 `/app`。

### D1 已冻结的本批入口

本机受控根目录为`.local/validation/investigation-manual-d1-20261127-01/`。表中路径相对该目录；身份、地址、密码及远端根目录从私密文件读取，不从历史命令推断。

| 用途 | 本批入口 |
| --- | --- |
| 全部目标绑定 | `shared-binding-private.json`，含新PG、身份、HTTP最终profile及远端包/profile路径 |
| HTTP部署及实际运行环境 | `http-profile-private.json`；最终环境由绑定中的`paths.http_runtime_environment`定位，Redis已切到本批隔离库，初版另存 |
| 核心运行定义 | `core/runtime/candidate.compose.json`、`core/runtime/config/dispatcher.json`；后者当前`enabled=false`，入口覆盖、固定镜像与独立持久目录已核 |
| 共用查询 | `core/runtime/config/lake-query.json`、`core/runtime-query-connection-private.json`；使用批准上下文范围与容器网络可达地址，不能只换scope而沿用无访问能力的旧账号 |
| 一次接收证据 | `core/receive-00-evidence/`、`core/receive-01-evidence/`；1条和9条两个完整范围各接收一次，均已成功，D2不要再次执行 |
| 原HTTP恢复 | `http-baseline-private.json`，完整inspect及20份只读文件副本 |
| 原dispatcher恢复 | `core/baseline-private.tar.gz`、`core/baseline/`，完整inspect、镜像和9个原挂载；原可写运行状态继续保留 |

截至D1准备关口，新库有10条告警/材料、5个事件、10条成员关联、15个待执行任务，以及4条原生资产；52条批准上下文仍从已核原湖读取。Case、Run和analysis_attempt均为0。两个新镜像已构建，候选服务没有创建或启动；原两个调查容器继续运行。统筹已核21上的37份候选运行文件、原对象/配置/启动时间、HTTP健康及45份原只读文件。这里只完成D1，不将准备状态当作D2实际加载或D3恢复通过。

## 9. 实际停启、一次正常验证

1. **即时核对窗口。** 检查原唯一 dispatcher、实际配置、活动 task/attempt、未结束冻结 Run、待处理任务和队列。有在途工作时按原流程完成后再停；旧 profile 的冻结 Run 不能换到候选 profile 继续。18:50 的快照只作参考。
2. **只停原两个服务。** 从本批基线取原 dispatcher/HTTP 的精确名称与 ID，正常停止；不执行全栈 `compose down`，不停止 PG、Redis、湖、模型、Fusion 或平台。原容器保留。外部接收可能继续向原库写入并排队，这是正常保留行为。
3. **启动候选 HTTP。** 使用新库，按上一节 build/prepare/start 验 `/livez`、`/readyz`、`/openapi.json`、版本/文件 hash。当前正式合同 83，候选读侧为 87；以本批冻结的完整合同为准，不把历史数字写死到新 profile。
4. **启动唯一候选 dispatcher。** 新库、独立 Redis/namespace/锁/回执已绑定，批准材料已准备。将本批执行配置明确设为启用，启动一个进程；核实际镜像、配置/输入 JSON hash、运行策略及目标连接，不能仅看容器 running。
5. **完成正常业务链。** 让本批必要 A/I 前置到真实终态；发起 `POST /api/v1/socai2/cases` 前，核批准事件展开并去重后的成员告警数不超过实际加载的分配配置 `case.max_alerts`。一次请求可能按容量续建多个 Case，不能假设一次 POST 就是一案；超出时先明确本批范围，不临时放大容量。提交后核 `allocations` 仅包含本次预期的一笔新 Case，仅跟随该项返回的 `initial_task`，不再提交启动或重复建案。精确请求及回执沿本批 OpenAPI、[分配合同](../integration/case-allocation-http.md)和[首轮指南](../integration/case-initial-http.md)；没有专门的建案分配预览 HTTP，不使用已退役的外部 prepare/start 路由。
6. **独立验保存和页面读取。** 核输入成员/事件/材料关系、唯一受理、task/attempt/Run、原答、交付和采用状态；HTTP 同源读回，并沿已有 `update_processing_audit.py` 更新 4177 查固定轮。模型待复核、部分交付、失败或正文质量限制均按实际记录，不反复采样。当前平台未接完的页面不冒充已验。
7. **结束候选窗口。** 不再提交新业务；确认本轮已到终态，保留回执/原答/失败。按下一节恢复原服务。本轮不继续两轮多元 Case 测试，不做压力或并发专项。

## 10. 恢复原环境

“恢复原来的样子”指恢复原容器、镜像、配置、端口、数据库/Redis 连接和原运行状态；原数据始终保留。演练期间原接收服务产生的合法新数据不删除，也不通过全库覆盖回到过去某一秒。

1. 停止候选业务受理，确认候选模型/任务已结束，再停候选 dispatcher 和 HTTP。若存在未知执行，先保留状态并查清，不盲目重发或把候选冻结 Run 交给旧进程。
2. 确认候选释放原 HTTP 端口，原挂载源指纹与基线一致。恢复原 HTTP 容器，验其 `/readyz`、原 release/OpenAPI 和一条既有记录读取。
3. 恢复原 dispatcher 容器，核原 image、原 A/I/Case 文件及策略指纹、唯一实例和原 PG/Redis 绑定。仅启动基线记为 running 的原实例，不启动那些原本已经停止的历史容器。
4. 原容器未被删除且原配置源未改时，恢复只需要沿精确对象 `docker start`；这比重新拼凑参数更可靠：

```sh
# 仅在上面终态与端口核对完成后；变量来自本批基线，不用通配符。
docker stop "$REVIEW_CANDIDATE_DISPATCHER" "$REVIEW_CANDIDATE_HTTP"
docker start "$REVIEW_OLD_HTTP"
# 验原 HTTP 后，再恢复基线中原本在运行的 dispatcher。
docker start "$REVIEW_OLD_DISPATCHER"
```

5. 若本轮曾单独切平台 origin/本机隧道，恢复记录中的原配置；未改过则无需操作。原 4177/8181 重新读取原目标库并核同源记录。新库和候选容器/原答/回执保留，不回灌原库，不清空 Redis。

### 中途失败时

| 失败时点 | 立即恢复步骤 |
| --- | --- |
| 打包/构建/新库准备失败，原服务尚未停止 | 原服务继续运行；保留失败回执，修当前准备问题，不执行停机步骤 |
| 原服务已停，但 prepare 失败、候选尚未创建 | 无须执行不存在候选的 stop；核端口已释放，直接恢复原 HTTP、验就绪，再恢复原 dispatcher |
| 候选 HTTP 已创建或启动，但 start/verify 失败 | 先核本批候选的实际状态，只停止已存在的候选 HTTP，保留容器和日志；恢复原 HTTP/dispatcher，不继续启动候选执行器 |
| 候选 dispatcher 或业务验证失败 | 不重复提交；先保留实际任务/模型调用状态，按真实在途状态结束候选执行，再停止候选 HTTP，恢复原服务。配置或数据问题留本批修复，不改旧失败 |

不要因组合 `docker stop` 中某个容器尚不存在而跳过恢复；每个对象按本批记录单独确认。恢复操作也只针对本轮两个原服务，不启动其他历史容器。

如果原容器被误删或原挂载被修改，就不能再宣称上述简单恢复路径成立；需用保存的完整 inspect、原镜像及配置副本按原参数恢复，并另核实际结果。因此准备阶段必须先保存，并在演练中保留原对象。

## 11. 本版实做结果及未通过项

已核：服务职责、当前核心运行配置及空闲快照、HTTP/核心现有安装入口、平台连接键、空库依赖、一次接收边界、Redis 隔离及恢复步骤；远端 main 已做实际三方合并模拟。HTTP 与核心已完成限定静态复核，Compose 项目隔离、日志文件挂载、失败恢复、平台可信写入和单案分配前置均已补齐。[文档核对回执](evidence/investigation-release-readiness-20261127-01/manual-review.json)

D1已实做并独立通过：完整包/私密配置、新库及正常依赖、批准材料的一次接收、原文与关系读回、原容器及恢复文件保持。[D1独立回执](evidence/investigation-manual-d1-20261127-01/README.md)。驱动/运行网络和HTTP Redis绑定的具体问题已在配置中修正，初版与失败记录保留，未新增业务补值逻辑。

D2已实际部署并完成一次建案（1 Case/task/attempt/Run，10告警/5事件）。前置A10/I4完成、I1未形成核心结论而失败；Case的C3/C6容量预检被拦，failed/partial、生成调用0，仅有system_only说明。PG、HTTP和候选在线期间的4177固定轮数据读回一致，但Case调查业务验收未通过。

D3已完成并独立通过：原两个精确容器、镜像、Config/HostConfig/Mounts、45份原只读文件和原PG/Redis连接恢复；唯一原dispatcher运行、两候选停止；原HTTP健康、83操作完整合同与固定原材料保持。重启时间变化单独记录。新库、候选和失败证据保留，不回灌原库、不清空Redis。本轮可确认按手册部署和恢复可执行，不能据此声称Case调查成功或完整change具备发布条件。详见[本次回执](evidence/investigation-manual-d2d3-20261127-01/README.md)。

## 12. 完整 main 版本发布（2026-11-28）

### 12.1 版本与交付物

本次发布由同一份发布清单绑定 `SpiritHub main SHA`、`socai2 main SHA`、父树 `server` gitlink、各镜像 digest、源码包 SHA-256 和配置文件指纹。父树的 `server` 必须等于本次 child SHA；两个 SHA 均须已在各自远端 main 读回。后续 main 再前进时先确认新差异，不能在构建中途静默换源，也不能把可变 `latest` 标签当作版本证据。

在普通项目目录准备独立、干净的发布检出。按父提交递归检出 `server`，不要在已有 8181 活动工作区执行覆盖式拉取。保留父 main 的扫描、PDF、助手等其他模块代码；我们更新的是同一 SpiritHub 后端里的 SOC 路由和 bridge，不需要另建临时平台后端。

| 组件 | 最新源码与产物 | 启动职责 / 监听配置 |
| --- | --- | --- |
| SpiritHub 前端 | 父 main 的 `web/`、`schemas/`、`web/Dockerfile`、`deploy/nginx/`；发布 `spirithub-web:<父 SHA>` 镜像 | Nginx 提供静态页面及同源 `/api` 转发；宿主监听来自父 Compose/环境文件。8181 是当前开发入口，不是发布包。 |
| SpiritHub 后端 HTTP | 同一父 main 的 `backend/`、锁文件、bridge 合同和 `docker-compose.yml`；发布 `spirithub-backend:<父 SHA>` | 原平台登录、业务模块与 SOC bridge 共用该 API。平台 API/网络/挂载沿已审配置，bridge 指向新的调查 HTTP origin。 |
| 调查 HTTP | child main 的完整 `services/api/app` + `investigation_http`、资源与依赖；专用 HTTP 源码包/镜像 | 显式 `investigation_http.main:app`；`bind/port/container_port` 从 HTTP 发布 profile 读取。不能使用通用 API Dockerfile 的默认 CMD 代替。 |
| 调查执行 | 同一 child main 的核心 app、输入/输出合同和策略；完整 processing 镜像 | 独立唯一 dispatcher，执行 A/I/Case；没有对外 HTTP 监听。HTTP 受理任务不自动启动该进程。 |
| Fusion | child main 的 `services/fusion/`、锁文件及湖配置模板；独立 Fusion 镜像 | 主服务的 Kafka 消费、湖写入等由配置决定；HTTP `bind/port` 显式配置。独立湖告警交付 worker 与主服务分别启动。 |
| LLM 代理 | child main 的 `deploy/aisoc21/compose.gateway.yml`、`litellm.config.yaml` 与受控配置 | 复用经验证的 LiteLLM 镜像 digest，配置显式绑定模型 alias、上游地址、认证、监听和超时。`TenantChatGateway` 是执行器内的适配器，不是另一个待部署服务。 |
| 4177 内部工作台 | child main 的 `services/investigation_test/`、`deploy/investigation-test/` | 独立内部查阅服务，沿其 profile 构建和监听；不由浏览器直接连 PG，不代替平台 API。 |

“最新”指这些源码取自本轮最终 main，及运行包确实加载这些源码。第三方基础镜像、LiteLLM 和已有模型推理端沿明确的兼容版本固定，不因本次提交擅自升级成外部最新版本。旧的单文件只读挂载须逐项核对，不能让它们遮盖新镜像中的代码。

### 12.2 构建和交付命令

以下变量由本批受控配置提供，命令不包含真实连接或凭据。先在具备依赖的构建环境准备，离线目标使用准备好的镜像、静态资源和依赖；不在切换窗口临时联网安装。

父项目根目录，沿 Node 24 / npm 11 与项目锁文件：

```sh
npm ci --prefix web/tools/openapi
npm ci --prefix web
npm run api:generate --prefix web
npm run typecheck --prefix web
VITE_API_MODE=live npm run build --prefix web
docker compose --env-file "$RELEASE_PLATFORM_ENV" -f docker-compose.yml build api web
```

`SPIRITHUB_IMAGE_TAG` 在该环境文件绑定父 SHA。生成的 live/mock 类型须与合并后的 Schema 一致；若重新生成产生非预期源码差异，先解决差异并重新冻结提交，不发布未经提交的临时后像。保留父项目 Dockerfile 所需的其他模块资源、字体和许可证。

child 发布检出目录，调查 HTTP 使用覆盖完整 app 和 investigation_http 的 profile：

```sh
python3 deploy/http-service/manage.py --profile "$RELEASE_HTTP_PROFILE" \
  package --output "$RELEASE_HTTP_PACKAGE_DIR"
```

在 21 的该完整包目录执行包内脚本：

```sh
python3 manage.py --profile profile.json build
# 已完成原实例基线记录及停机条件后再准备和启动。
python3 manage.py --profile profile.json prepare
python3 manage.py --profile profile.json start
```

profile 必须显式包含完整目录、runtime 环境文件、配置挂载、日志挂载、预期路径/方法/Schema 与源码指纹。`start` 包含校验，但不自动回滚。`prepare` 创建独立文件，不盲目重复覆盖。HTTP 管理器不执行数据库迁移，也不启动 dispatcher。

调查执行沿已验完整打包/传输入口，不使用历史 18 文件局部候选代替：

```sh
python3 deploy/aisoc21/prepare_processing_release.py --profile "$RELEASE_CORE_BUILD_PROFILE"
python3 deploy/aisoc21/rollout_transport.py --config "$RELEASE_CORE_TRANSPORT_PROFILE" processing upload
python3 deploy/aisoc21/rollout_transport.py --config "$RELEASE_CORE_TRANSPORT_PROFILE" processing build
```

准备器会读取当前检出源码，因此检出必须与本批 child SHA 一致且没有源码修改。其 processing 镜像默认是单次 job；dispatcher 的受控运行定义须覆盖 entrypoint 为 `python -B -m app.socai2.analysis_dispatch_runtime`，command 为 `--profile <绝对路径>`。独立 HTTP 包与 processing 包分别冻结，不能互相代替。

Fusion 镜像和 4177 包的现有入口：

```sh
docker build -f services/fusion/Dockerfile -t "$RELEASE_FUSION_IMAGE" services/fusion
python3 deploy/investigation-test/build.py build --profile "$RELEASE_WORKBENCH_PROFILE"
```

Fusion 主服务显式运行 `uvicorn app.main:app --host <profile bind> --port <profile port>`；独立交付运行 `python -m app.workers.lake_alert_delivery --profile <绝对路径>`，两者使用各自配置和同版源码。`--once` 会实际交付一批，不能当健康检查。LiteLLM 不需要重编业务代码，用本批经审的 Compose 和已备镜像定向启动 `litellm`。

### 12.3 必须对齐的配置

| 连接 | 需要绑定的配置 |
| --- | --- |
| 浏览器 → 平台 | 前端 `VITE_API_MODE=live`；Nginx API upstream；平台 public origin、登录/Cookie 配置、宿主端口及网络。保留 main 的其他代理路由。 |
| 平台 → 调查 HTTP | `SPIRITHUB_SOC_HTTP_BASE_URL`、`SPIRITHUB_SOC_HTTP_TRUSTED_READS`、`SPIRITHUB_SOC_HTTP_TRUSTED_ORIGIN`、`SPIRITHUB_SOC_TENANT_ID`、credentials 文件及普通/执行超时、最大响应字节。Compose 必须透传配置；只改 `.env` 不证明容器已加载。 |
| 调查 HTTP → PG | `DATABASE_URL`、`SOCAI2_CASE_DATABASE_URL`、`SOCAI2_SERVICE_DATABASE_NAME` 指向当前同一业务库；context、任务策略、分配策略、读写功能、人员目录、湖查询及日志配置都显式挂载。 |
| dispatcher → PG/Redis | profile 的 database/Redis URL 文件、连接参数、lifecycle policy、namespace、锁、回执目录、执行工厂和执行器配置；与 HTTP 的租户/业务库一致。 |
| 执行器 → 模型/工具 | `SOCAI2_INVESTIGATION_POLICY` 与 executor 选择同版策略；模型解析来源、alias、协议/Schema、输入/输出预算、tokenizer 真实后端与超时、湖/知识连接。完整原件留后台，业务模型视图按既有筛选合同。 |
| Fusion → Kafka/湖/PG/Redis | 来源与租户映射、topics/consumer group、storage/ingress/consumer profile，以及 selection/receive/connections、查询 read limits；使用现有批准数据源，不新增为样本服务的匹配逻辑。 |

所有实际值保存在受控文件，发布清单仅记录引用及指纹。旧手册第 7 节的新库演练不适用于本轮。PG 使用现有库并按已装版本应用缺少的增量，保留 V1 原件与数据；`subject-risk` 入口含 132/136。ClickHouse 只按所选 storage profile 处理实际缺少的 DDL，不对旧数据清库/重放。

### 12.4 切换、最小验收和回退

1. 核对最终两 main、gitlink、包/镜像/配置指纹；保存本轮实际原容器、原镜像、运行定义与配置，停机前检查实际在途任务。原镜像和配置保留。
2. 先核现有 PG、Redis、ClickHouse、模型上游和 LiteLLM，完成必要的兼容增量。HTTP 及模型代理可读不代表消费者已启用。
3. 定向切换调查 HTTP，核 `/readyz`、OpenAPI 和实际加载源码。Q34/Q35 必须精确包含 `GET /api/v1/socai2/cases/{case_id}/investigations` 及 `GET .../investigations/{run_id}`，不能用通用 Run 详情替代 Case 定位后声称通过。
4. 按本批配置切换 Fusion/独立湖交付及唯一 dispatcher。保持原有启用范围，记录实际进程和加载版本；不能同时留下两个同范围 dispatcher 消费任务。
5. 再更新平台 api 和 web。对已备镜像可沿父 Compose 定向执行 `up -d --no-deps --no-build --pull never api`、再执行同命令的 `web`；不重启扫描、知识、数据库等无关服务。需要展示新回执时按同版 profile 更新内部 4177。
6. 使用已有批准批次做一次正常页面→平台→原生 HTTP→PG 的读回，核 Case 资料、历史目录、固定 Run/Result 与错误空态。只在发布验收范围要求新业务执行时派一笔，跟踪原任务到真实终态，保留历史失败；不以 HTTP 202、readyz 或有工件代替模型质量和业务完成。

任何切换失败先核实际状态，停止当前后续步骤。恢复本轮保存的同一组件旧镜像/Compose/配置并做对应健康与读取检查；若已切多个依赖组件，按本批清单恢复兼容组合。保留业务数据、任务/attempt/Run、原答和回执，不执行 `down -v`、清空队列或数据库回灌。数据库增量不默认有 downgrade，应用回退必须先核旧代码兼容性。

本节提供可执行入口与检查顺序，具体已发布 SHA、镜像及在线验收结果由该批回执填写。[HTTP 完整交接](../../openspec/changes/complete-socai2-investigation-chain/http-complete-delivery-handoff-20261128.md) · [核心/Fusion/代理完整交接](../../openspec/changes/complete-socai2-investigation-chain/core-fusion-model-git-handoff-20261128.md) · [前端完整交接](../../openspec/changes/complete-socai2-investigation-chain/spirithub-frontend-release-handoff-20261128.md)。尚未实施的事件输出精简不写成此次代码或部署已生效。
