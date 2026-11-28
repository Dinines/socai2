# 调查执行、Fusion 与模型代理的完整源码交付清单

本清单服务于本轮 `socai2` 与父工程的完整 Git 交付，不限于最近一次 18 文件运行补丁。只核源码、配置结构、依赖和已有证据入口；本次未执行 Git 写操作、构建、迁移、服务切换、数据库读取或模型调用，也未重跑已验测试。Git、`PROGRESS.md` 和父工程引用由统筹统一处理。

逐文件清单见 [source-manifest.json](../../../docs/operations/evidence/core-fusion-model-delivery-inventory-20261128-01/source-manifest.json)。清单冻结了本次读取的 HEAD/main、工作树源码指纹和归属；未 fetch，不代表远端现时状态。工作树继续被其他模块修改时，以最终纳管文件的实际后像再次核对。

## 1. 本轮应一起交付的源码

清单覆盖当时全部 **109 个 `services/` 待提交路径**，并补充部署模板、迁移安装入口及已提交依赖。分组不等于替其他模块做完独审。

| 范围 | 应交付的增量及必要依赖 | 已有证据与责任边界 |
| --- | --- | --- |
| S1/S2/S3 模型失败回执 | `services/api/app/services/llm_safety.py`；`services/api/app/socai2/` 下 `ai_delivery_store.py`、`alert_basic_executor.py`、`analysis_dispatch_types.py`、`baseline_analysis_model.py`、`baseline_failure.py`、`baseline_reasoning.py`、`case_c3_completion_flow.py`、`incident_diagnosis_executor.py`、`model_errors.py`、`model_protocol.py` | [设计/接线范围](model-failure-contract-audit-20261128.md)；[S1 独审](../../../docs/operations/evidence/model-input-guard-s1-coordinator-20261128-01/review.json)、[S2 独审](../../../docs/operations/evidence/model-envelope-s2-coordinator-20261128-01/review.json)、[S3 独审](../../../docs/operations/evidence/model-local-end-s3-coordinator-20261128-01/review.json)。当前清单不重新解释其中的运行结果 |
| 前序材料一致性 P2 | `case_previous_analysis.py` 与 `test_socai2_previous_analysis.py`；依赖 `case_citation_quality.py`、`citation_quality.py`、`case_program_output.py` 及 `test_socai2_c6_units.py` 中复用的 fixture | [P2 设计](previous-analysis-material-consistency-20261128.md)、[工程证据](../../../docs/operations/evidence/previous-analysis-normalization-p2-20261128-01/README.md)、[独审](../../../docs/operations/evidence/previous-analysis-normalization-coordinator-20261128-01/review.json)。三个新增保存/读取回归及旧实现反证已完成；既有 profile fixture 失败仍保留，未据此宣称所有历史测试通过 |
| M0f 已在 V1.1、尚需进入本次 main 合并的依赖 | `case-input-v1.json`、`case_c3_input_selection.py`、`case_followup_input.py`、`case_input_text.py`、`case_program_output.py`、`runtime_policy.py`、`token_budget.py` | 冻结 main/HEAD 差异为这七个核心文件；不能只拿未提交列表拼包而漏掉已在分支的依赖。参见[前一轮完整性核对](core-production-commit-dependencies-20261128.md) |
| I 输入后台字段筛选 | `incident-input-v1.json` 现有增量是 `raw_alert_backend_fields` 增加 `field_metadata.lake_ingress` | [字段审计](incident-input-field-audit-20261127.md)。应随对应既有输入视图功能归档；**不是尚未实施的 I 输出精简**，也不追认属于最近 18 文件运行补丁 |
| Fusion 来源标签 | `services/fusion/app/services/lake_ingress.py`、`lake_alert_receiver.py` | [候选独审](../../../docs/operations/evidence/alert-incident-tactics-example-20261126-01/independent-candidate-review.json)。按来源字段投影，不按样本值猜战术。规则 ID/名称、源置信度依赖已提交，仍须保留其 receiver、engine、projection、sink、model 接线 |
| Fusion 交付读取限制 | `lake_alert_selection.py`、`lake_alert_delivery.py`、`workers/lake_alert_delivery.py`；`test_lake_delivery_read_limits.py`；`delivery.example.json` | [设计](lake-delivery-read-limits-20261128.md)、[既有交接](../../../docs/operations/evidence/lake-delivery-read-limits-m0g-20261128-01/README.md)。交付配置覆盖的是该独立 worker 的查询/连接限制，未改变业务筛选或造数据 |
| 湖 schema、保留期、查询与接入 | 待提交 `services/api/clickhouse/001_init.sql`、`test_retention.py`、`test_retention_worker.py`、`test_lake_schema_policy.py`、`test_socai2_lake_queries.py`，以及全部九个未提交 Fusion 湖测试/辅助文件；保留已提交 `app/db/lake_columns_v1.json`、`lake_schema.py`、`lake_migrations.py`、`app/scripts/lake_schema.py`、`app/services/retention.py`、`app/workers/retention_purge.py` 和 Fusion consumer/writer/replay | [湖设计](clickhouse-lake-design-20261119.md)、[schema 证据入口](../../../docs/operations/evidence/lake-schema-3b-20261119-01/README.md)。`001_init.sql` 是新装参考；已有库升级走配置化 migration，不拿新装 SQL 覆盖旧库 |
| 风险/业务判定及 136 迁移 | 新增 `136_socai2_subject_risk_ingress.sql`，连同 `deploy/database/install_reader.py`、`subject_risk.sql`、`CURRENT.md`；风险/判定 release fragments；`socai2_test_severity.py`、风险/等级意见直接测试 | [风险入口](../../../docs/operations/evidence/subject-risk-s1-20261120-01/README.md)、[业务判定入口](../../../docs/operations/evidence/subject-business-verdict-sf04-20261120-01/README.md)。保留已提交的风险、判定生产实现及 132/134/135 迁移。136 在 132 后替换同名函数，按主体种类读取对应成员关系，并保持原租户约束；不按测试 ID 分支 |
| 任务时间和运行日志 | 任务时间、日志 release fragments；dispatch/lifecycle 示例与 fragment；`test_socai2_analysis_task_times.py`、`test_socai2_analysis_task_times_pg.py`、`test_socai2_operational_logging.py`；保留已提交的 `analysis_task_times.py`、133 迁移、API/Fusion `operational_logging.py` 和各调用点 | [时间证据入口](../../../docs/operations/evidence/analysis-task-times-s5-20261120-01/README.md)。日志 fragment 是部署依赖清单，不是新服务；缺少本轮日志独审出处的部分继续由原模块确认，不能用本次静态盘点补签 |
| 已完成续接、局部交付、材料/时钟功能的测试补交 | `test_socai2_ai_units.py`、`test_socai2_c6_units.py`、`test_socai2_transport_continuation.py`、`test_socai2_local_dependency.py`、`test_socai2_completion_clock.py`、`test_socai2_material_response.py`，以及清单中相关修改测试 | [C6 单元入口](../../../docs/operations/evidence/c6-unit-continuation-d5b-20261118-01/README.md)、[续接入口](../../../docs/operations/evidence/transport-continuation-d5c-20261118-01/README.md)、[依赖/时钟入口](../../../docs/operations/evidence/local-dependency-d5c-20261118-01/README.md)。测试替身属于测试目录，不冒充实际数据库/模型通过 |
| 核心与 HTTP 共用读取 | `page_contracts.py`、`page_reader.py`、`stage_reader.py`；Case contracts/reader/service/story，新增 `case_info.py`、`case_investigations.py`、`case_story_relations.py` 及对应测试 | E27/E29/E23 证据在[已有依赖核对](core-production-commit-dependencies-20261128.md)。Case 新增读取与对应 `investigation_http/` 接线由 HTTP 模块独审；保留全部路径，不删、不只交页面而漏核心 |
| HTTP 与 4177 页面 | 清单分别列为 `http_owner`、`viewer_owner`、`shared_http_tests`；包含全部当前修改和新增路径 | 由对应模块提交验收回执；本清单记录完整性，不扩大核心执行模块的审查结论 |

`source-manifest.json.release_fragment_dependencies` 展开全部既有 release fragment 的源码依赖，不只列 dirty 文件；`static_local_import_dependencies` 另用 AST 收集当前 API/Fusion Python 增量的直接本仓库 import，包含湖查询、HTTP 材料适配和测试辅助文件。扫描未执行 import，也不宣称解析动态导入或完整传递依赖。`direct_dependency_paths` 同时记录依赖在 HEAD/main 是否存在及是否等于当前源码。列表不能代替最终组合后像的独审。

## 2. 配置和脚本交付边界

以下模板及其 README 一起归档：`deploy/local-investigation/` 的分析 dispatch、lifecycle、task-times、operational-logs、subject-risk、subject-business-verdict fragments；`deploy/aisoc21/lake-storage-3b/`、`lake-ingress-3c/`、`lake-consumer-3d/`、`lake-replay-3e/`、`lake-query-3f/`、`lake-alert-selection-4a/`、`lake-alert-receive-4b/`、`lake-alert-delivery-4c/`。已提交的 selection/receive/query/storage 示例也是必要依赖。

`deploy/aisoc21/spirithub-ocsf-forward/` 和 `opensearch-dashboards-json-fix/` 标记为独立部署责任范围。其中 `aisoc21.env`、`forward.toml`、`type-inventory.aisoc21.json` 等需由责任模块判断是否为可纳管模板或实机材料；本次未输出其值，未替其纳管，也未删除。不能对这些目录直接套用源码全选结论。

本轮增量扫描只保存源码路径、行号和类别：`connections.example.json` 的凭据 URI 命中为显式示例占位；`test_socai2_operational_logging.py` 的命中属于传输异常测试的替身配置。所审核心/Fusion生产增量未见按样本 ID、主机或测试前缀分支的特判，未见新增空实现伪造业务成功。S1/S2/S3 保留原始失败/unknown 与三值发送事实；P2 仅对派生副本重放归一化后比较，不改原件。扫描不是全仓密钥证明，其他模块路径仍需其源码/材料审查。

## 3. 构建与启动入口

下列是由源码核出的命令结构，变量由受控 profile 给出；本轮未运行这些命令。运行镜像、地址、租户、凭据、端口、超时与预算不在本文填写。

| 服务/用途 | 仓库入口与命令结构 | 关键边界 |
| --- | --- | --- |
| API/调查执行依赖镜像 | 从仓库根执行 `docker build -f services/api/Dockerfile -t "$API_IMAGE" services/api`；21 的既有构建变体为 `deploy/aisoc21/build/Dockerfile.api` | 保留该服务 `pyproject.toml`、`poetry.lock` 和 app 包。API 镜像默认启动 `app.scripts.serve`，这不自动启动调查 dispatcher |
| 独立调查执行器 | `PYTHONPATH="$REPO/services/api" SOCAI2_INVESTIGATION_POLICY="$INVESTIGATION_POLICY" "$PYTHON" -m app.socai2.analysis_dispatch_runtime --profile "$DISPATCH_PROFILE"` | absolute profile；`executor_factory` 选择 `app.socai2.analysis_case_executor:executors` 接齐 A/I/Case；HTTP worker 不导入启动循环。按配置锁文件保持单实例，退出处理 SIGTERM/SIGINT |
| 既有 processing 构建工具 | `"$PYTHON" deploy/aisoc21/prepare_processing_release.py --profile "$BUILD_PROFILE"`；远端 `install_processing_release.py "$RELEASE_NAME" "$ARCHIVE_SHA256" < "$ARCHIVE"`；`build_processing_image.py --release-directory "$RELEASE_DIRECTORY"` | builder 收集 API app 的 `.py/.json` 及 smoke Fusion；会纳入工作树后像，不能把它误称为只打包最近 18 文件。processing 镜像默认入口为单次 job，不能代替 dispatcher。源码/运行 profile/镜像指纹按已有发布流程冻结；历史脚本的固定路径不代表已完成全仓配置清理 |
| Fusion 主服务 | `docker build -f services/fusion/Dockerfile -t "$FUSION_IMAGE" services/fusion`；显式配置的启动命令为 `uvicorn app.main:app --host "$FUSION_BIND_HOST" --port "$FUSION_PORT"`，工作目录为 `services/fusion` 或镜像对应 app 目录 | 默认 Dockerfile 有默认端口，实际部署须由审过的 Compose/profile 显式覆盖。主服务包含 Kafka 消费、Redis、可选湖 writer 和 PG sink；不能由其存活推断独立湖告警交付 worker 已启用 |
| 独立湖告警交付 | `PYTHONPATH="$REPO/services/fusion" "$PYTHON" -m app.workers.lake_alert_delivery --profile "$DELIVERY_PROFILE"`；Compose 模板 `deploy/aisoc21/lake-alert-delivery-4c/compose.candidate.yml` | 与 Fusion Kafka consumer、调查 dispatcher 是三个进程。`--once` 会进行一轮业务交付，`--stage-only` 也可能写交付台账；均不能用作纯只读健康检查 |
| 模型代理 | `deploy/aisoc21/compose.gateway.yml` 的 `litellm` 服务，挂载 `litellm.config.yaml`；用完成私密绑定的 Compose 文件执行 `docker compose -f "$GATEWAY_COMPOSE" up -d --no-deps litellm` | LiteLLM 使用现成镜像，不是本仓库另一个推理实现；`TenantChatGateway` 是执行器内的调用适配器，不是可另启的 HTTP 代理服务。旧 `gateway_1e.py` 的 `start/verify/linkage` 是历史操作入口，不能直接拿来重启/探测本轮环境 |

部署入口覆盖执行器/Fusion/代理三个范围；平台后端、调查 HTTP、前端由相应模块交接。未定位到另一份需要另启的独立 LLM proxy 实现，不编造服务或要求重新部署推理模型。

## 4. 配置字段与依赖顺序

| 范围 | 必需结构 |
| --- | --- |
| Dispatcher | `enabled`、`tenant_id`、`database_url_file`、`database_connect_args`、`database_pool_size`、`redis_url_file`、Redis socket/connect timeout、`lifecycle_policy_file`、`executor_factory`、`executor_config_file`、`logging_profile_file`、`dispatch`。其中 `dispatch` 含 namespace、并发/轮询/执行时限、补充限制、priorities、receipt_directory、lock_file |
| A/I/Case executor | `investigation_policy_file`；`incident.{max_alerts_per_diagnosis,scan_batch_size}`；`case.{scan_batch_size,query_window.{before_seconds,after_seconds},log_query.max_rows_per_query}`。选择的 TOML 与 `SOCAI2_INVESTIGATION_POLICY` 加载的指纹必须一致 |
| 模型/调查策略 | TOML 的 `case`、`alert_basic`、`incident_diagnosis` 各自的调用/工具/token/查询/期限预算；`model.{alias,protocol,schema_profile,context_tokens,max_prepared_bytes,final_reserved_input_tokens,final_reserved_calls,output_tokens,tokenizer}`；`alert_io`、`incident_io`、`case_io`、`query_transport`、`tools`、`labels`、`views`。环境字段 `SOCAI2_MODEL_PROTOCOL`、`SOCAI2_MODEL_SCHEMA_PROFILE` 与所选策略保持一致。实际 LLM 配置仍由 `resolve_llm_config` 解析，返回 `allowed/base_url/model/api_key/source/reason` 等字段 |
| LiteLLM | `model_list[].{model_name,litellm_params.{model,api_base,api_key}}`、`litellm_settings`、`router_settings`、`general_settings.master_key`；Compose 的 image、env_file、ports、volumes、command、healthcheck。凭据/地址/上游模型值只在受控配置中绑定 |
| 湖存储/消费 | storage 的 `database`、`retention.{ingest_mapping_versions,ingest_days,legacy_days}`；ingress 的租户、来源命名空间、mapping/OCSF version、Kafka cluster/topics、storage_policy_file；consumer 的 enabled、bootstrap_servers、group_id、initial_offset、batch/fetch/timeout 限制 |
| 湖交付 | selection/receive/connection 三份文件绑定；`runtime` 的聚合/去重/置信度开关；`read_limits` 五字段 `max_records/max_result_bytes/query_timeout_seconds/connect_timeout_seconds/send_receive_timeout_seconds`。连接结构包括 PG DSN/pool/connect timeout、ClickHouse host/port/database/user/password/secure/verify、Redis url/connect/socket timeout |
| 日志 | `service/instance/directory/level/format/max_bytes/backup_count`；日志目录单独受控挂载，不能将错误正文、API body 或凭据加入公共发布回执 |

建议启动次序按实际依赖执行：先核基础 PG/Redis/ClickHouse 与受控迁移，再准备现有模型上游/LiteLLM 和配置，随后启动 HTTP/查询依赖、Fusion 消费/交付，再启动唯一的 dispatcher，最后由前端读回。独立 worker 的自动消费开关按本次既有授权保持；代码已提交不能证明自动链路已启用。

迁移入口：`deploy/database/install_reader.py <mode> --profile "$DATABASE_PROFILE"`，现有 mode 含 `verify`、`analysis-lifecycle`、`lake-alert-receipts`、`lake-alert-deliveries`、`subject-risk`、`analysis-task-times`、`business-verdict`、`run-escalation-decision`。`subject-risk` 安装入口接 132/136；新装与旧库升级使用各自模式。湖 DDL 入口为 `python -m app.scripts.lake_schema --profile "$STORAGE_PROFILE" --output "$SQL_OUTPUT"`，升级为同一入口的 `--apply`。后者是实际写库操作，本轮未执行。

## 5. 健康、回退与未验边界

Fusion HTTP 有 `/livez`、`/readyz`，readiness 结合订阅/worker 状态；LiteLLM Compose 配的是 `/health/liveliness`，只表示代理存活，不是模型正文质量验收。dispatcher 与独立湖交付 worker 没有单独 HTTP 健康口，应按对应现有进程、锁、日志/回执与任务只读入口核对；不得为做健康检查而提交新任务或重复 POST。

回退复用本批保存的原镜像/容器配置/候选文件指纹及恢复计划。dispatcher 先停止接新工作并确认已有任务的本地结束，再恢复原实例；Fusion/代理使用原经审 Compose 和镜像定向恢复。不删除 PG/ClickHouse 数据、回写历史原答、清空队列或重放未知副作用。数据库没有在本次源码盘点中验证 downgrade，不能把服务回退等同数据库回退。

本次已核：源码 diff、文件归属、main/HEAD 完整性、release fragment 直接依赖、启动/配置字段、增量特判与疑似凭据坐标。未核：当前线上服务实际加载指纹、真实 profile 值、实际迁移状态、模型输出质量、所有 HTTP/页面组合后像、实机部署材料是否可公开。本批真实运行、4177 导出与读取回执继续留在原私密材料中，由统筹按已有授权独审；本文不转述结果，也不据盘点完成宣称整个 change 已通过。
