# 调查 HTTP 完整提交与统一发布交接

本清单扩展本 change 的 [Case 依赖审计](case-m0g-http-pg-audit-20261128.json)，交给统筹核对当前项目与父项目的最终提交。范围是当前调查 HTTP 的全部源码、合同、依赖及发布入口，不限于 Q34/Q35 注册行。

完整清单的初次审计只核源码、配置字段和证据路径；后续指定的 HTTP 边界离线检查及有界修复见末节。初次审计未检查 Git，后续仅按统筹明确要求执行指定 `git show` 读已提交源码；未操作 index/提交/分支或根 PROGRESS，未构建、迁移、部署、重启、探测现役服务、提交业务任务或调用模型。下面的“包含”“接线”都是源码结论，不代表当前 main、镜像或现役服务已经包含。

## 可逐路径核对的提交清单

完整展开文件表见 [源码清单 JSON](http-complete-delivery-source-inventory-20261128.json)。它保留旧依赖清单的路径，并增加整个 HTTP 包、主应用静态导入关系、完整打包目录、路由声明、配置字段、SQL 引用和已有测试/独审入口。统筹应拿这份清单与最终暂存及提交树核对；本文件不把历史 Git 审计当作当前差异。

| 交付部分 | 必须覆盖的源码/合同入口 | 核对重点 |
| --- | --- | --- |
| 原生 HTTP 全包 | `services/api/investigation_http/` 全部文件 | `main.py`、`dependencies.py`、`ports.py`、`errors.py`、各 `*_contracts.py`、`contracts.py`、`record_links.py`、`csv_export.py`、全部 adapters/routes 同批交付。逐文件列表在 `native_package_files`。 |
| Q33 关系故事 | 核心 `case_story.py`、`case_story_contracts.py`、`case_story_relations.py`；HTTP `story_contracts.py`、`adapters/case_story.py`、`external_routes/story.py` | 保留 `view=related`、focus 与成员关系读取；相关故事中的 Run/Result 链接依赖 `adapters/run_directory.py`。 |
| Q34/Q35 调查目录与定位 | 核心 `case_investigations.py`、`case_story_relations.py`；HTTP `case_investigation_contracts.py`、`adapters/case_investigations.py`、`external_routes/case_investigations.py` | 还依赖 `story_contracts.py`、`adapters/case_story.py`、`adapters/run_directory.py`、共享 `contracts.py` 及 services/dependencies/ports/main；不能仅收 main 注册行。 |
| Q36 信息摘要 | 核心 `case_info.py`、`case_service.py`；HTTP `case_info_contracts.py`、`external_routes/cases.py`、`contracts.py` | `TacticCount` 核心定义在 `app/socai2/page_contracts.py`；此前 Case 缺口是 HTTP 的导出，不能误写成新建核心类。 |
| Case 列表及既有 Case 操作 | `case_contracts.py`、`case_reader.py`、`case_service.py`、`case_relationship_reader.py`，及分配/成员/管理/采用/评论/附件/页面数据/探索/人工任务相关核心与合同 | `active_member_count`、共享 URL、分配受理与任务关联必须与当前整包一致。完整静态依赖表包含函数内延迟导入。 |
| 告警/事件读取与管理 | `page_reader.py`、`page_contracts.py`、`stage_reader.py`、`stage_read_contracts.py`、`program_facts.py`、`read_sources.py`、`subject_risk*.py`，及 alert_review/hosts、grouping、subject_management | 当前 `investigation_http/contracts.py` 也导入 `IncidentDetailView`、`IncidentSubjectView/Page` 等；整文件提交须携带对应定义与读取依赖，不能沿用“Case 最小 hunk”范围漏掉已实现内容。 |
| 显式提交及任务进度 | 见下节 POST → 任务落库 → GET 的完整链 | 不能把 202 受理当执行完成，不能漏 policy、writer 和独立 dispatcher 接线。 |
| Run/Result/步骤/工件与数据湖 | HTTP `run_record_contracts.py`、`run_directory_contracts.py`、`lake_contracts.py`、对应 adapters/routes；核心 `run_records.py`、`run_directory.py`、`lake_queries.py`、`lake_query_contracts.py`、`lake_hostname.py` | 目录、详情、定位的响应合同不同；保留原读取入口。SQL/JSON 等非 Python 资源也要随源码包交付。 |
| 共用运行依赖 | `app/models/`、`app/db/`、`app/core/`，`app/_health.py`、`app/api/v1/deps.py`，以及 `app/socai2/` 的静态可达文件 | `main_static_local_import_closure` 给出来源、导入位置及源码散列；全量 app 包保留包内动态导入与资源，外部 factory 仍按所选配置核对。静态可达不等于启动时执行。 |
| 构建、部署、规格和交接 | `services/api/pyproject.toml`、`services/api/poetry.lock`、`services/api/Dockerfile`；`deploy/http-service/manage.py`、`CONFIGURATION.md`、`README.md`、相关 release fragment；数据库入口；本 change 与既有前后端交接文档 | 只提交非私密源码/模板。私密运行配置、实际连接与业务证据仍留受控位置。 |

`main.py` 当前选中的 router 均列在 JSON 的 `registered_router_roots_in_main`；`pages.router` 还嵌入 `subject_management.router`。`external_routes/stage_execution.py` 文件存在，但未由当前原生 main 注册。完整源码打包不构成将内部执行路由加入对外 API 的要求。`case_ai` 的已有保留入口也不能仅凭注册推断功能已开放。

## Q34/Q35 的发布落点

当前本地源代码同时有：

- `GET /api/v1/socai2/cases/{case_id}/investigations` → `CaseInvestigationPage`。
- `GET /api/v1/socai2/cases/{case_id}/investigations/{run_id}` → `CaseInvestigationLookup`。
- `POST /api/v1/socai2/cases/{case_id}/investigations` → `AnalysisTaskReceipt`，方法不同，不代替以上 GET。

Q35 从租户/Case 范围的调查关系读取指定 Run。`case_story_relations.py` 保留属于本 Case 的 baseline Run，是否已有 Result 不是该分支的必要条件。URL 适配依次依赖 `adapters/case_investigations.py` → `adapters/case_story.py.investigation_urls` → `adapters/run_directory.py.run_url/result_urls`。

先前冻结的原生 HTTP `main.py` 缺少这组 GET 的导入与注册；同期窄范围 dispatcher 发布源码不包含 HTTP 更新。这是既有源码快照结论。本轮未复查现役服务，也不把本地完整注册当作已经发布。定位仍使用 `/investigations/{run_id}`，不能用返回 `RunDetailWithDirectories` 的 `/runs/{run_id}` 替代后追认旧批通过。既有失败保留，统一 HTTP 发布后按该批实际实例做直接验收。

既有平台候选代理源码有 Q34/Q35 转发声明，桥接使用配置字段 `soc_http_base_url` 等并保留原路径；这不证明现役代理选择了哪个原生实例。平台最终提交、代理配置及运行连接由统筹与前端负责，本轮没有操作父项目。

## 已实现 POST 与后续执行的完整接线

| 层 | 源码入口 | 业务责任 |
| --- | --- | --- |
| HTTP 注册与请求 | `main.py`、`external_routes/analysis_submissions.py`、`analysis_submission_contracts.py` | Case `POST .../investigations`、Incident `POST .../diagnose`；请求为 `operation_key: UUID` 与 `mode: check/rerun`，返回已持久受理的任务身份和 `status_url`。 |
| 身份、端口与 factory | `adapters/identity.py`、`dependencies.analysis_submission_service`、`ports.AnalysisSubmissions`、`adapters/services.analysis_submissions` | 从配置的业务上下文取得租户/操作者，经 `case_sessions("POST")` 选用 writer；不新增平台登录或伪造用户。 |
| 受理适配 | `adapters/analysis_submissions.py` | 将主体类型映射到任务 kind，调用核心受理，映射明确错误并补 native `status_url`；该适配不访问 Redis 或执行调查。 |
| 任务保存 | `app/socai2/analysis_tasks.py`、`analysis_task_store.py`、`analysis_task_policy.py`、`baseline_service.py`、`baseline_store.py`、`app/models/socai2.py` | 事务保存、同 operation key 重放、主体检查及任务关联；任务 policy 必须从所选配置文件加载。 |
| 进度/尝试/结果读取 | HTTP `analysis_task_contracts.py`、`external_routes/analysis_tasks.py`、`adapters/analysis_tasks.py`、`adapters/run_directory.py`；核心 `analysis_tasks.py`、`analysis_task_times.py` | 原任务 URL 查询真实尝试与结果；无 Run 不补造 Run。Run/步骤/Result 链接的共享合同与详情路由需同批可用。 |
| 任务执行（独立组件） | `app/socai2/analysis_dispatch_runtime.py`、`analysis_dispatcher.py`、`analysis_dispatch_store.py`、`analysis_dispatch_redis.py`、`analysis_dispatch_config.py`、`analysis_dispatch_types.py` | 独立 profile 指向 PG、Redis、lifecycle policy、executor factory/config 和日志；Case/Incident/Alert executor 的实现及发布由核心清单负责。HTTP 的启动、202 或 readyz 均不能证明此链已运行。 |

任务 detail 路由由 `analysis_tasks.subject_routes` 为告警、事件、Case 生成；Case 的原受理地址为 `/api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`。Q35 是按 Run 的 Case 调查定位，与任务 detail 的身份和用途不同。

## 构建、迁移与配置入口

所有实际地址、端口、库、租户、凭据、模型和时限由选定配置文件提供。以下只列字段，未读取任何配置值。

| 环节 | 工程入口 | 统一发布需核对 |
| --- | --- | --- |
| 基础依赖镜像 | `services/api/Dockerfile`，配套 `pyproject.toml`、`poetry.lock` | Dockerfile 由锁文件导出依赖。其默认 CMD 是通用 API 启动器；原生调查 HTTP 必须由专用发布配置显式指定 `investigation_http.main:app`，不能依赖默认 CMD。 |
| 完整源码包 | `deploy/http-service/manage.py` 的 `package` / `complete_package_targets` | `complete_packages` 覆盖 `app` 与 `investigation_http`；`patches` 必须与这两个目录全部源码/资源一一对应；还需 `runtime_environment_file`。清单 JSON 的 `complete_build_package_files` 可作最终 profile 的覆盖核对依据。 |
| 构建、准备、启动 | 同脚本的 `build`、`prepare`、`start` | `base_image`、`base_tag`、`image`、`platform`、`source_root`、`expected_source_hashes`、`reference_container`、`replace_existing`、`project`、`container`、`root`、超时字段；只核目标 HTTP。完整候选使用明确环境及挂载；未填写或执行实际发布 profile。 |
| 监听 | `manage.py:prepare/local` | `entry`、`bind`、`port`、`container_port`、`network`、`memory`、`tmpfs`；所生成 uvicorn/Compose 参数来自 profile。本轮不声称任何实际监听已变更。 |
| 读写数据库 | `adapters/runtime.py`、`app/db/database.py`、`app/db/case_database.py` | `DATABASE_URL`、`SOCAI2_CASE_DATABASE_URL`、`SOCAI2_SERVICE_DATABASE_NAME`、pool 字段；运行启动校验 reader/writer 的 host/port/database 一致。写入开关按既有功能配置，不新设角色专项。 |
| HTTP 功能开关 | `adapters/services.py` | `SOCAI2_PAGE_READ_ENABLED`、`SOCAI2_CASE_API_ENABLED`、`SOCAI2_ANALYSIS_READ_ENABLED`；启动还读取 `SOCAI2_STAGE_EXECUTION_ENABLED`。开关字段存在不证明当前启用。 |
| 信任上下文 | `adapters/identity.py` | `SOCAI2_HTTP_CONTEXT_FILE`，绝对路径文件字段 `tenant_id`、`actor_id`、`actor_name`。原生 API 的配置上下文与平台 JWT/bridge 分别配置；禁止以开发 bypass 代替。 |
| 任务与 Case 分配 | `analysis_task_policy.py`、`case_allocation_policy.py`；模板 `deploy/local-investigation/analysis-tasks.json`、`case-allocation.json` | `SOCAI2_ANALYSIS_TASKS_CONFIG_FILE`、`SOCAI2_CASE_ALLOCATION_CONFIG_FILE`；policy 的重试、窗口、周期、页大小/上限等字段见 JSON，不抄实际值。 |
| 导出/负责人目录/数据湖 | `list_export.py`、`owner_directory.py`、`lake_queries.py` | `SOCAI2_EXPORT_CONFIG_FILE`（max_rows/max_bytes/statement_timeout_ms）、`SOCAI2_OWNER_DIRECTORY_PROFILE_FILE`（tenant_id/user_ids）、`SOCAI2_LAKE_QUERY_PROFILE_FILE`（database/scopes/分页/窗口/结果限制/transport）；ClickHouse 连接依赖共同 settings。源码有默认导出配置文件，完整包须携带该资源；本次发布仍应显式绑定所选配置。 |
| 日志与挂载 | `manage.py:explicit_runtime_inputs/add_logging_volume`、`app/core/operational_logging.py` | `runtime_environment_file`、`runtime_mounts[].source/target/sha256`、`SOCAI2_LOGGING_PROFILE_FILE`、`logging_directory_mount.source/target`；配置只读挂载，日志目录按既有脚本单独配置。 |
| 独立执行与模型/上游 | `analysis_dispatch_runtime.py`；`deploy/local-investigation/analysis-aic-dispatch.example.json`、`analysis-aic-executors.example.json`、`analysis-dispatch-release-fragment.json` | dispatcher 字段：enabled/tenant_id/database_url_file/database_connect_args/database_pool_size/redis_url_file/Redis 时限/lifecycle_policy_file/executor_factory/executor_config_file/logging_profile_file/dispatch。模型及工具连接跟随核心 executor 与 `runtime_policy.py` 的 `SOCAI2_INVESTIGATION_POLICY`，不硬编码或从 HTTP 连通推断成功。 |

`manage.py` 支持的动作为 `package`、`prepare`、`build`、`start`、`verify`、`local`。调用模板为 `python deploy/http-service/manage.py --profile <已绑定的发布 profile> <action>`；`package` 还要提供新的 `--output`。这只是源码入口说明，本轮未调用这些动作。

数据库入口是 `deploy/database/init_socai2_current.sql` 与 `init_socai2_current_reader.sql`；SQL 引用图见清单 JSON。保留 V1 的 123–126 原件；后续相关增量有 127–136，包含任务生命周期、Case 分配、数据湖接收、风险、任务时间、业务判定、Run 决策及风险初始化函数。`deploy/database/subject_risk.sql` 同时引用 132 与 136，不应只检查 init 根文件的第一层引用。

这些是完整组件的迁移来源，不是要求对既有库重跑全部脚本。统筹应按目标库已有迁移记录选择必要增量；Q34/Q35、Q36 和故事关系本身是读取组合，不据此宣称新增表必需。`manage.py` 不负责迁移。通用 `app/scripts/run_migrations.py` 会遍历其迁移目录，且 `DATABASE_MIGRATION_URL` 未设时回落 `DATABASE_URL`；因此不作为本次调查库的无条件一键升级入口，更不能从启动成功推定所需迁移全部生效。

## 已有测试、独审及未验边界

本轮不重跑业务测试，只检查源码与已知证据路径。`test_source_inventory` 列出静态引用 HTTP 或其直接核心入口的测试，附本地测试 helper 依赖。关键直接测试包括：

- Q33/Q34/Q35/Q36 与列表：`test_socai2_case_story_related_pg.py`、`test_socai2_case_investigations_pg.py`、`test_socai2_case_info_pg.py`、`test_socai2_case_queue_pg.py`；history/info 测试还依赖 story-related 测试的公共建数 helper。
- POST/任务：`test_socai2_analysis_submission_pg.py`、`test_socai2_case_submission_http.py`、`test_socai2_analysis_task_http_pg.py`、`test_socai2_case_initial_http_pg.py`，以及既有任务 policy/timing/dispatch 直接测试。
- 合同/读取：`test_socai2_http_boundary.py`、`test_socai2_trusted_http.py`、`test_socai2_run_directory_pg.py`、`test_socai2_run_records_pg.py`、既有事件读取及成员聚合测试。

所有上述测试路径均在 `services/api/tests/`。完整清单同时记录已有独审/回执位置，关键批次目录为 `docs/operations/evidence/` 下的 case-story-migration、case-history-migration、case-info-migration、case-list-migration、analysis-task-http、analysis-task-times-s5、case-initial-http、execution-contract-fix、run-directory、run-records、trusted-http 及 incident-detail-ui/member-aggregates/diagnosis-live。JSON 中给出准确文件路径；本轮没有读取里面的业务值或重新判定其通过情况。

现有新 rerun 的原生 HTTP/PG 回执保持在受控的本机批次目录；此前 Q35 失败继续保留，不补发 GET、不换地址追认。本次源码交接不更新该批验收结论，也不导出模型原答或业务正文。

## 统一发布后的最小直接验收与回滚入口

发布执行与最终暂存由统筹负责。所需证据应绑定同一个已发布 HTTP 实例及其配置：

1. 核对最终提交树、完整源码包与实例实际加载源码；用 `manage.py:verify` 对照 `/readyz`、`/openapi.json`、`expected_openapi_file`、`expected_operations` 和镜像。方法数相同不能单独证明 Q34/Q35 已注册，因此需精确核对路径/方法/Schema。该脚本还比对其他既有容器快照。
2. 从既有批准的验收身份读取 Q34/Q35、Q36/故事及受影响列表字段，对照目标库持久记录；定位与详情保持不同合同。已有 POST 接线用批准批次的原任务身份核对受理、attempts、Run、Result 与查询地址，不能为源码交接新派任务。
3. 独立 dispatcher 的版本、配置和运行证据单列；模型/上游调用结果、交付状态及质量结论继续区分。HTTP 健康、202、工件存在均不足以代替业务与模型验收。

脚本当前没有 `rollback` 动作，也不会在 `start` 失败时自动恢复旧版本。统一发布前必须把目标 HTTP 原 image、Compose、私密 runtime.env、只读配置挂载与必要数据库兼容性检查绑定到发布回执。发生回滚时使用该保存的旧 Compose/镜像/配置恢复同一目标 HTTP，随后做对应健康与合同核对；不重建数据库、不清数据，也不顺带重启 dispatcher 或其他项目。具体旧工件由统筹绑定，本轮未读取运行值，因而没有产出可直接执行的回滚 profile。

完成源码清单只表示交接材料齐备；最终 Git 提交、父项目引用、构建与现役业务验收仍应由负责组件给出独立证据。不能据此勾选整个 change 完成或归档。

## 完整交付前 HTTP 边界检查的有界修复

本步处理同一 HTTP 边界测试首次直接运行暴露的两个断言阻断：`errors.py` 在 adapter 之外导入核心日志实现；`IncidentSubjectView` 已有 `business_verdict` 未被旧合同兼容检查归一化。本步不增加业务字段、不修改告警合同、不操作 Git/index/根 PROGRESS，不连接真实数据库、服务或模型。

合同依据沿用 [SF04 业务判定方案](subject-business-verdict-20261120.md) 的范围与“生产、保存和读取”第 3 项，以及 [Case workspace 规格](specs/socai2-case-investigation-workspace/spec.md) 的结构化业务判定要求。负责人已在 [全功能接通方案“决定与归属”](http-real-data-connection-20261120.md#决定与归属) 指明沿当前设计接通非暂缓功能，SF04 已纳入当前 change。该字段是当前诊断原指针对应的已保存模型判定，四种枚举或 null，不由 GET 补算，不属于告警合同。源码 `page_contracts.IncidentSubjectView` 与 `page_reader` 的事件分支已有对应定义和读取，本步仅校准测试。

实施顺序、必要验证及通过证据：

1. 先核 `app/core/operational_logging.py` 的既有结构化异常记录约定，保存变更前源码并运行本 change strict。然后把 HTTP 用例错误的日志实现移入 `investigation_http/adapters/`，由错误转换层传入原 logger。保持 5xx 条件、`http_use_case_failed`、operation/stage/error_code/http_status、异常结构及原 HTTP 错误转换，不增加免检例外。直接验证沿原 AST 断言，并在同一测试项使用真实日志调用和 pytest 日志捕获核对原行为。
2. 只为 `IncidentSubjectView.business_verdict` 增加明确的兼容归一化；先直接断言四态字符串枚举、可空、默认 null、非必需、当前诊断来源语义及不进入共享告警视图/事实。其余 Schema 与路径的精确比较继续保留，不通过普遍忽略新增字段来放行。
3. 仅重跑 `services/api/tests/test_socai2_http_boundary.py` 原有四项；使用本机 Python 与既有 pytest 配置，测试日志和精确源码 diff 存本地私密目录。记录命令、退出码、逐项通过/失败和测试机制；若出现其他阻断，先记录具体断言并交统筹，不扩展本步修复。由统筹独立核对后决定纳入完整提交。

通过标准是两处实现/测试修复与以上直接断言一致，四项测试全部通过；若仍有失败，保留真实结果与未执行到的边界，不称整包合同通过。

本步结果：实施前 strict 通过；新增 `adapters/operational_logging.py`，由 `errors.py` 的 provide/invoke/invoke_record 传入原 logger；真实结构化记录器、响应与 5xx/4xx 日志条件已有同一测试项的直接断言。SF04 归一化只移除已逐项断言的 `IncidentSubjectView.business_verdict`，四态/可空/非必需/来源说明与 DTO 默认 None 分别检查，共享告警视图及事实禁止新增该字段。三个实现/测试文件的 Ruff 与 AST 检查通过。

本步最终仅复验原文件四项，独审补强后的 `test-05/` 为 **4 passed、0 failed，退出码 0**。导入与真实日志、外部 OpenAPI 兼容性、核心独立导入、撤销 prepare/start 入口均通过；Q34/Q35/POST 的专门断言、最终 paths/components 严格相等及其后的 legacy alias/内部入口隔离检查均执行到。未替换原 before-openapi 快照或删减原边界断言。

最终源码仍只有一处生产分层迁移：`errors.py` 调用新增 `adapters/operational_logging.py`；日志类别、事件、字段、异常结构、触发阈值与 HTTP 错误保持。其余修改为同一测试文件中有明确来源的兼容增量断言；没有修改告警/事件/Case 生产 DTO、业务查询或写入。当前交付清单的 `native_package_source_sha256`、`main_static_local_import_closure` 与 `test_source_inventory` 已刷新最终源码散列，包含新增 adapter、errors 和测试后像；`bounded_http_boundary_fix.final_source_sha256` 绑定本步三个文件与通过批次。
中间记录均保留：`test-01/` 中新断言曾要求 OpenAPI 显式携带 `default: null`，实际 Schema 省略此键，随后改为精确核实际 Schema并单独断言 DTO 默认 None；`test-02/` 在共享 `SubjectView` 的旧 Schema 比较处暴露 `triage.description` 新增。统筹确认此描述属于已提交的 ATT&CK 显示合同后，获准只读 `git show origin/main:services/api/app/socai2/page_contracts.py`；核对文本与工作树完全一致，随后 strict 通过，再为 `SubjectView` 与继承的 `IncidentSubjectView` 断言该精确文本并仅归一化此键。没有广泛删除 description，也没有修改生产 DTO；`AlertFacts` 与旧基线仍精确相等。`test-03/` 随后到达最终 paths 比较，暴露既有 main 的 people 路由未纳入旧测试基线；该失败也保留原件。

日志验证使用合成失败 callable/StoreError 夹具，调用真实结构化记录器，由 pytest caplog 捕获；其他项使用进程内 TestClient 和导入拦截器，不连接真实数据库、服务或模型。日志、命令、逐项结果、已提交源码对照及精确 diff 保存在 `.local/validation/http-complete-source-delivery-20261128-01/http-boundary-fix-01/`。不读取运行批次私密数据，不扩跑其他历史回归，不操作 Git/index 写入或根 PROGRESS。当前同组直接核验已通过；统筹独核、完整提交和现役发布验收仍分别待完成，未核销本 change。

统筹进一步要求一次核清所有既有增量并完成同组检查。已在本地仅提取该断言的 Schema 做诊断，未把诊断当测试通过；得到全部剩余 paths/components 差异。定向已提交源码对照表保存在 `all-schema-source-provenance.source-only.json`：people/负责人目录、告警管理与批量选择、任务时间/活动步骤、Case 采用来源、其余 SF04 判定字段均已存在于 origin/main；其中告警管理、人员、任务时间、Case 页面数据及阶段读取合同的整个模块 AST 与已提交 main 一致。Case `active_member_count` 对应 [Case 列表方案](case-list-migration-20261126.md#核对后确认的本页必要接线)，事件已发布诊断/最近尝试包装对应 [事件详情交接](incident-detail-ui-handoff-20261125.md)；均为已有本 change 实现，不是本次测试修复新增业务。

集中处理实施前再次 strict 通过，只改此测试：people 先断言路径方法、四个查询参数及响应；新增组件逐一断言封闭对象的字段、类型、必需性和引用；告警批量 tags 限定与版本/选择描述仅按已提交精确合同归一化；判定字段按 SF04 四态/可空/来源逐项核对；Case 活跃成员数及事件包装按上述方案直接断言。随后才还原这些明确增量对应的旧比较形态，保留原快照和最终 paths/components 的严格相等。不得全局删除 description、跳过未知字段或替换整个 baseline。集中修改后同文件四项已全部通过，已更新完整打包文件表、导入闭包与最终源码散列；后续未执行任何 Git 操作。旧失败日志各批次均保留，最终通过结果不能代替真实 HTTP/PG/模型或发布验收。

统筹独审要求补强新增 helper 的测试有效性：旧 `AlertManagementFields` 当前不再作为独立组件引用，单条字段展开在 `AlertManagementUpdate`；兼容比较重建该旧组件前，必须从当前单条请求的实际 Schema 去掉明确的 operation_key/expected_row_version 请求外层，完整核对余下 properties/required/type/约束与旧字段模型相等，再使用该当前模型恢复引用。批量无 tags 的新组件已有精确前置比较；批量 changes 引用/描述已有完整前置断言，改为只归一化这两个已断言键。此补强实施前 strict 通过，仅修改测试，生产源码与 test-04 一致。test-05 同四项最后复验全部通过；测试后像、完整打包目录及导入闭包散列已刷新。新增 helper 中的批量字段替换已有完整前置断言，批量 changes 现仅归一化精确断言后的两个键，没有整对象覆盖未知差异。

### 本步最终源码指纹

下列 SHA-256 对应已通过的 `test-05/source/` 后像；完整 HTTP 包、依赖闭包和测试指纹见同目录源码清单 JSON。

| 源码 | SHA-256 |
| --- | --- |
| `services/api/investigation_http/errors.py` | `4bd2ebf1615fffb803d17a824d5284229e98b3576be90b31abf436c1826e6133` |
| `services/api/investigation_http/adapters/operational_logging.py` | `b06058603912e77e73ab101e60614eb73ffa8eb5ab32ee6fb707f9c0dccb33c5` |
| `services/api/tests/test_socai2_http_boundary.py` | `0f3080045e316488a9cb6f84163a5c4a91415a6a90090c5297d3ae987fb56711` |
