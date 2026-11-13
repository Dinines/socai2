# 告警、事件与 Case 前后端交接

更新于 2026-11-13。本文是前后端 HTTP 和组件对接的共同入口，以 21 当前部署和实际读回为准。现有页面仅用于测试；本次交接不要求修改页面，也不把页面接线作为服务验收前置。告警分诊、事件诊断、Case 调查及基本管理接口已部署；模型正文质量继续单列验收。

## 接入先看这里

**业务后端调用 `http://192.168.1.21:18024`，在 `http://192.168.1.21:18080/` 查看 Swagger。**

18024 是独立调查 API 服务，18080 是静态 Swagger。本机18024为list-export-20261113-r1-local，21正式18024为list-export-20261113-r1；两端均已挂载56操作，本机使用v12_upgrade_dev，21使用aisoc。 当前文档定义 **56 个操作：53 已实现、3 返回501**；两端实际测试与部署回执见下方入口。

| 接入事项 | 直接入口 |
| --- | --- |
| HTTP 用途、参数、每个输出字段、示例、错误和实现状态 | [21 Swagger](http://192.168.1.21:18080/)、[下载 OpenAPI JSON](http://192.168.1.21:18080/handoff/openapi.json)；仓库 [HTTP 交接包](deliverables/investigation-validation-20261106/http-handoff/README.md) |
| 后端自己启动本地 Swagger | [Docker 安装、架构选择、端口、API 地址及更新步骤](deploy/api-docs/README.md#后端在自己电脑启动-swagger)；无需安装调查数据库或模型 |
| Kafka 与其他组件 | [组件对接指南](docs/integration/component-handoff-current.md)：实际 Topic/消费组、消息输入输出、数据流、依赖地址、启用状态和责任边界 |
| 测试数据与可执行操作 | [后端联调指南](docs/integration/backend-test-guide.md)：21已存在的三条合成告警、事件、Case，读取与新建测试流程 |
| 4173 测试页面 | [启动、使用、样例/历史/真实数据的区别](docs/integration/test-page-4173.md) |
| 产品功能范围 | [125 项功能清单](deliverables/investigation-validation-20261106/frontend-feature-list.md)，只作为范围依据；不扩展旧 AiSOC 平台功能 |
| 获取父项目中的服务源码 | 在 SpiritHub 使用 `git submodule update --init server`，按父项目固定的 server 提交读取本文件；不使用 `--remote` 自动跳到其他版本 |

推荐调用关系：`产品前端 → 业务后端 → 调查 HTTP API`。业务后端负责资产库存、资产标签和人员目录等基础能力；调查服务负责自身业务数据、执行与结果。`owner_id/assignee_id` 使用调查服务能识别的同租户用户 UUID，不能直接传姓名或未建立映射的外部人员 ID。数据库及内部缓存不作为前后端写入入口。

### 按业务调用

以下路径均省略 `/api/v1/socai2`；完整参数和返回 Schema 以 Swagger 为准。E 编号可在 Swagger 搜索。

| 类别 | 功能和调用顺序 | 返回结果与注意点 |
| --- | --- | --- |
| 告警读取 | E26 `GET /alerts` → E28 `GET /alerts/{alert_id}` → E22 `GET /alerts/{alert_id}/analysis`；E24 读指定 Run，E32/E33 读步骤/工件 | 分开读取告警事实、当前有效分诊和历史尝试；材料正文用 E31 |
| 告警分析 | E36 `POST /alerts/{alert_id}/analyze`，请求含 `operation_key` | 会执行模型流程；按返回 Run 和分析结果状态判断交付，不能只看 HTTP 200 |
| 事件读取/分析 | E27 列表 → E29 详情 → E23 诊断目录 → E25 指定 Run；E37 `POST /incidents/{incident_id}/diagnose` | 事件成员/对象等用 E30 分区读取；归并关系不等于攻击因果 |
| 创建调查 | E01 `POST /cases`，传标题、`operation_key` 和所选 `alert_ids/incident_ids` → E03 详情、E12 Run | 返回 Case、范围版本和 `pending_run_id`；创建本身不启动调查 |
| 启动/读取调查 | E13 `POST /cases/{case_id}/runs/{run_id}/start`，带 `operation_key/expected_scope_revision` → E12 Run → E14 正式结果 | start 会等待本次执行返回；连接超时或未知先查原 Run，不换 key 重跑。结果包含结论、发现、未解决问题及建议 |
| 再次调查 | E11 `POST /cases/{case_id}/baseline/prepare` → E13 start | 显式准备并启动；人工任务保存、重开 Case 均不自动启动 |
| 人工任务 | E38 创建 → E39/E41 读取 → E40 `PUT /cases/{case_id}/tasks/{task_id}` 完整修订 → E42/E43 读历史 | 创建带 Case 范围版本；修订还带任务行版本。完成必须填结果正文及适用范围；旧版本保留 |
| 告警人工判定 | E28读版本 → E48单条或E49批量提交 → E28/E30读回 | 判定及理由追加保存，误报/正常关闭，已关闭改真实威胁/需跟进恢复处理中；模型分诊保留 |
| 告警管理 | E50单条或E51批量 → E28/E30读回 | 负责人、标签、状态；人工关闭必填reason，不覆盖原判定 |
| 事件管理 | E52单条或E53批量 → E29/E30读回 | 负责人、状态、标签、人工严重度；解决和等级覆盖需理由，不改变成员等级 |
| 调查基本管理 | E44 `GET /cases/{case_id}/management` → E45 `PATCH` 同路径 → E03/E44 读回 | 可改标题、说明、负责人、严重度、标签、处理状态；只更新显式提交字段 |
| 关闭/重开 | E44 读条件和版本 → E46 `POST /cases/{case_id}/close` 或 E47 `POST /cases/{case_id}/reopen` → E17 读活动 | running/unknown 阻止关闭；未完任务要求明确确认及理由。重开恢复处理中，不重派调查 |

调查没查清的内容直接写在调查结论里，例如“尚未确认这次登录是否由本人操作”。需要找人确认时，用户再建“联系本人核实登录”的任务；不会自动把每个疑问变成待办。

告警涉及设备时，调查服务到业务后端维护的现有资产库存中查找，找到就返回设备信息和标签，没找到返回空列表。查询路径是 `GET /alerts/{alert_id}/records/assets`（加上前述业务前缀），事件用 `GET /incidents/{incident_id}/records/assets`。文档编号E30只是方便查找同一个分区读取接口；`assets`填在路径最后，不是新增服务、数据表或查询参数。资产创建和标签维护由业务后端负责。

### 请求、版本和错误

请求使用 `Content-Type: application/json`、`Authorization: Bearer <现有有效凭据>`。租户从认证上下文取得，普通调用无需另设计权限体系。下例只示范 Case 管理；替换 Case ID、当前版本和本次操作 UUID 后调用：

```http
PATCH /api/v1/socai2/cases/{case_id}/management
Content-Type: application/json
Authorization: Bearer <有效凭据>

{
  "operation_key": "00000000-0000-4000-8000-000000000901",
  "expected_row_version": 3,
  "title": "核实异常登录",
  "handling_status": "in_progress"
}
```

成功返回 `{"case": <保存后的完整 CaseView>, "changed": true或false}`；从 `case.row_version` 取得下次管理写入的版本。省略字段保持原值；`description/owner_id/severity=null` 清空，`tags=[]` 清空标签。其他接口的请求结构不同，不能把此版本参数套用所有接口。

- `operation_key`：每次逻辑写入一个 UUID，同一意图重试沿用；改变输入后使用新 key。
- `409`：版本冲突、运行阻塞或状态不允许等；保留用户输入，读取最新对象后按 `detail` 处理。不要直接无限重试。
- `404`：对象不存在或不属于指定父主体；检查 Case/Run/材料之间的真实 ID 关系。
- `422`：参数/枚举/必填项不合法；`detail` 可能是字段错误数组，也可能是业务错误字符串。
- `501`：E19 助手提问、E20 保存回答、E21 显式采用其他结果尚未实现。
- `503` 或执行请求超时：先读取原 Run；服务错误 `detail` 可能为对象，不能假定统一是字符串。
- E02/E26/E27现支持筛选、排序、分页；告警时间按event_time，事件至少一条成员告警在窗口内，Case按business_updated_at。带时区时间前闭后开；缺值始终排序在后。告警/事件filtered_total是筛选数，total/overall_stats是整体；Case total是筛选数、metrics是整体。新条件用next_cursor续页，改条件清空；旧无新增条件的before_id保留，不能混用。完整参数见[列表用法](deliverables/investigation-validation-20261106/http-handoff/README.md#列表查询怎么用)。

告警/事件写入的参数、批量选择、完整返回及错误见[后端测试指南](docs/integration/backend-test-guide.md#告警人工判定与告警事件管理)。

“已实现”只描述接口业务是否存在；当前未完成的统一归并统计、问答、探索保存等见[接口实施计划](docs/investigation/http-implementation-plan-20261112.md)。真实模型结论质量仍未整体验收通过；页面修改不在这次后端交接范围。

后续按功能流程推进，必要读写接线与配置随功能处理。告警相关的前后端字段合同保持稳定；字段名、类型、含义、关联和接口返回确需调整时先列明影响并确认。下表保留已核验的运行配置，配置当前值不构成后续功能开发的权限前置。

本项[分诊后历史知识同步](openspec/changes/archive/2026-11-12-sync-saved-alert-knowledge/validation.md)已完成本地直接流程、独审及 21 r5 发布读回；采用原 Run trace／工件读取表达同步状态，不新增告警 DTO 字段。历史卡片及同步字段见[知识交接](docs/investigation/historical-alert-knowledge-handoff.md)。

## 1 接手入口

| 内容 | 权威资料 |
| --- | --- |
| 产品功能与规则确认 | [逐页功能清单](deliverables/investigation-validation-20261106/frontend-feature-list.md)：目的、操作结果、后端实现状态与接口；[规则记录：D01–D07 全部已确认](docs/design/investigation-product-decisions.md)；[产品需求](docs/design/alert-incident-case-product-requirements.md) |
| 功能对应字段及跳转 | [F01–F28 字段／J01–J14 跳转附录](deliverables/investigation-validation-20261106/frontend-data-navigation-contract.md) |
| 字段到存储、关联及读取 | [服务端数据交接](docs/investigation/socai2-page-data-handoff-20261106.md) |
| 当前调查表与写入边界 | [28 表职责／24 表实际写入](docs/investigation/investigation-table-scope.md)、[当前机器字典](docs/design/socai2-data-contract-current.json)；资产等基础数据由业务后端负责 |
| HTTP字段审计来源 | [基于原三份资料的核对结论](deliverables/investigation-validation-20261106/http-handoff-audit/README.md)：先按告警22/事件15/调查88项，原43操作/522字段已审，Case管理增加4操作/10字段，前批告警/事件管理增加6操作/8字段，前批列表封套增加2字段，本批新增3个CSV操作；当前56操作，原JSON有542个固定字段出现位置与28组动态投影，CSV另说明104个允许列；字段说明已合入当前Swagger |
| HTTP逐项对接与在线文档 | 标准Swagger按告警/事件/调查接口分类，[56操作、用途、参数、输入输出、结果和实现状态](deliverables/investigation-validation-20261106/http-handoff/README.md)；[本机Swagger](http://127.0.0.1:18080/)、[21内网Swagger](http://192.168.1.21:18080/)；[Docker部署](deploy/api-docs/README.md) |
| HTTP功能验证与后续实施 | [本机路由/真实隔离库验证](openspec/changes/complete-socai2-investigation-chain/http-functional-validation-20261112.md)：31项检查、43操作回执，模型为替身，真实质量未核销；[未实现功能计划](docs/investigation/http-implementation-plan-20261112.md)。[统一独立入口验收](openspec/changes/archive/2026-11-12-serve-investigation-api/validation-20261112.md)已完成本机/21 TCP Case/H与SQL读回，详见下表 |
| JSON 与 HTTP 合同 | [JSON Schema](docs/design/socai2-json-contracts-20261103.schema.json)、[OpenAPI](docs/design/socai2-independent-api-v2.openapi.json) |
| 对外与内部接口边界 | [架构与实际调用清单](docs/design/investigation-http-boundary.md)：列表/详情和显式analyze/diagnose/start均为对外业务接口，调查步骤与内部组件HTTP独立维护；代码分离已发布本机/21，本轮三个列表的已确认增量在该边界内实现 |
| 有值、空值与原件 | [字段取数样例](deliverables/investigation-validation-20261106/page-field-samples.md)、[运行记录及离线材料](deliverables/investigation-validation-20261106/README.md) |
| 程序流程和模型职责 | [执行账本](docs/investigation/current-execution-ledger.md)、[每个模型环节的输入输出](docs/investigation/model-input-output-current-20261109.md) |
| 模型输入字段选择 | [字段级清单](openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md)：查询只给结果及 A/I/C3 字段筛选已本地落实；原冻结 C3 离线正文7,680字符、空工具消息24字符。完整 JSON 新导入保留完整块，C3/Deep/C6 共用已识别知识的业务正文投影，[新导入离线预览](docs/operations/evidence/model-input-selection-20261112-05/README.md)不代表实际导入/运行。HTTP 路由、请求/响应字段、关联及数据库表均不变，可继续接口交接；新导入分块数量可能变化，原工件/旧知识不重写。Deep/C6 已进一步按问题/全案任务筛选，[完整输入预览](docs/operations/evidence/model-input-selection-20261112-06/README.md)分别8,768/14,080字符，原引用/范围及输出保存读取合同保持；已补[大量工具返回处理及隔离库替身保存/读取验证](docs/operations/evidence/model-input-selection-20261112-07/README.md)，结果与当前评估GET一致；真实模型质量未通过，尚未发布本轮模型修改 |
| 当前固定流程与后续更新规划 | 先完成[固定范围的一次调查](openspec/changes/complete-socai2-investigation-chain/fixed-flow-plan.md)；[本地修复与真实失败读回](openspec/changes/complete-socai2-investigation-chain/fixed-flow-validation-20261112.md)尚未发布、未整体验收，再实施[更新/流式调查](openspec/changes/schedule-streaming-investigation-updates/proposal.md)；后者为目标合同，未实施队列/自动重算 |
| 已有问题与完成边界 | [问题清单](docs/investigation/current-issues.md)、[OpenSpec 任务](openspec/changes/complete-socai2-investigation-chain/tasks.md) |

## 2 当前运行环境

| 项目 | 当前值与用途 |
| --- | --- |
| 目标 | 21，SSH 别名 `sting-infra21` |
| 发布 | `v1.2-20261112-r5`；[发布清单](deploy/aisoc21/release-v1.2.json)固定源码、镜像和挂载 |
| 数据库 | PostgreSQL 16，业务库 `aisoc`，调查 schema `socai2` |
| HTTP | 后端对接用`http://192.168.1.21:18024`，业务前缀`/api/v1/socai2`；独立服务`list-export-20261113-r1`，56操作齐全，E36/E37显式启动接口已启用，可由页面操作或后端业务逻辑调用 |
| 本机与旧入口 | 本机18024接隔离`v12_upgrade_dev`，28024经显式SSH转发接正式`aisoc`；两库记录ID不得混用。旧主18000、旧独立18020继续保留；旧独立接`socai2_next_20261104`，不作为当前对接入口。部署与架构见[profile](deploy/http-service/README.md) |
| 身份 | 用户按正常登录或有效 API key 认证；租户取认证上下文，Case/H 读取要求 `cases:read`，A/I 读取要求 `alerts:read` |
| 页面读取 | `SOCAI2_PAGE_READ_ENABLED=true`、`SOCAI2_ANALYSIS_READ_ENABLED=true`；包括 Case/H 的 GET |
| Case HTTP 写入 | `SOCAI2_CASE_API_ENABLED=true`，私密 SOCAI2_CASE_DATABASE_URL 已指向现有处理连接；建案与 H 写读已实际通过，现有页面仅作测试 |
| 自动消费 | Agents 暂停；没有自动启动 Case 或恢复消息消费的验收结论 |
| 配置 | [生产 profile](deploy/aisoc21/production-v1.2.toml)选取 [A/I/Case 策略](deploy/local-investigation/investigation-policy-case-v1.toml)；凭据留在受控私有文件 |

模型单次时限 300 秒，Case 整轮 1500 秒，最终阶段预留 300 秒；单 Run 的调用与容量限制读取策略。租户累计调用、token、未结算数量配额不限制。失败、unknown 和待复核按实际状态保存。

`aisoc_app` 获授调查表 SELECT、两个只读函数 EXECUTE 及 `public.assets/public.users` SELECT。工作台使用 `socai2_prod_reader`，按需处理使用 `socai2_prod_processor`，入站来源读取使用 `socai2_prod_ingress`。只读账号、处理账号和数据库 owner 各按职责使用。

## 3 数据库与字段关系

调查服务当前使用 **28 表、450 列**，具体职责见[调查表范围](docs/investigation/investigation-table-scope.md)，字段名、类型、枚举和空值见[当前机器字典](docs/design/socai2-data-contract-current.json)。业务后端通过 HTTP 对接，不需要复制这些表或旧 AiSOC 的公共支撑表。

| 功能 | 权威表及主要关联 |
| --- | --- |
| 告警事实与分诊 | `alerts` 的当前材料／分诊／人工反馈指针连接 `alert_materials`、`alert_assessments`；同材料的来源和对象在 `alert_source_refs`、`alert_objects` |
| 事件与诊断 | `incidents → incident_alerts → alerts`；诊断指针连接 `incident_diagnoses`，诊断尝试按 `runs.incident_id` 查 |
| Case 范围 | `cases → case_alerts/case_incidents`；成员关系与显式事件关系分别展示 |
| 冻结输入和执行 | `runs → run_members/run_steps/artifacts`；Run 固定材料版本，步骤按 `seq/parent_step_id` 组织 |
| 正式结果及当前判断 | `results/result_members` 保存各轮结果；`cases.current_assessment_id → case_assessments → case_assessment_sources/case_assessment_members` 给采用依据和覆盖范围 |
| 人工确认 | `tasks → task_revisions`；范围、正文、完成人和完成时刻读取选中的版本 |
| 活动与读取保留 | `activities → activity_targets`；`comments`、`response_links` 有读取/关联用途，完整协作和真实处置写入未交付 |
| 问答依赖保留 | `conversations/messages` 仍被当前结果及发布校验引用；问答业务未开放 |

所有关联同时限定租户和父主体。显示名称、主机名和厂商编号不能替代 UUID。当前材料、历史冻结材料与外部来源分别读取。告警交接字段调整按 [AGENTS.md](AGENTS.md#调查数据库-v1-与人工确认)先列影响并确认；其他功能所需内部调整按 OpenSpec 推进。

需要独立部署调查服务时，按[服务部署说明](deploy/http-service/README.md)及[数据库安装入口](deploy/database/CURRENT.md)执行；普通业务联调只配置 HTTP 地址及现有凭据。

## 4 页面读取合同

后续业务后端通过 **HTTP** 对接，不要求直连调查库或照搬旧 AiSOC 表。完整参数、示例、错误及缺口以[本次HTTP交接包](deliverables/investigation-validation-20261106/http-handoff/README.md)为入口；原OpenAPI保留为结构来源。

下列路径均以 `/api/v1/socai2` 为前缀。前端优先沿响应中的身份和内容链接取数；完整参数、返回类型和限制以 OpenAPI 为准。

| 页面需要的数据 | GET 路径与说明 |
| --- | --- |
| 告警／事件列表和详情 | `/alerts`、`/incidents` 及 `/{id}`；列表默认 20、上限 50，按返回游标分页 |
| 成员、对象、来源、资产、活动、相关告警、响应 | `/alerts/{id}/records/{section}`、`/incidents/{id}/records/{section}`；默认 50、上限 200，按 `next_offset` 分页 |
| 告警材料 | `/alerts/{id}/materials/{material_id}`；保留版本、hash、原描述与结构字段，正文受限时返回 availability |
| A/I 尝试与步骤 | `/{alerts或incidents}/{id}/analysis`、`/{alerts或incidents}/{id}/analysis/runs/{run_id}`；在该完整 Run 路径下追加 `/trace` 或 `/artifacts/{artifact_id}` |
| Case 队列、资料与资料字段 | `/cases`、`/cases/{case_id}`、`/cases/{case_id}/page-data`；队列的筛选总数和全租户 metrics 分开 |
| Case 历史及指定结果 | `/cases/{case_id}/history`、`/cases/{case_id}/runs/{run_id}`、`/cases/{case_id}/results/{result_id}`；历史默认 20、上限 100 |
| Case 工件与冻结材料 | `/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`、同 Run 下 `/materials/{material_id}` |
| 非 Run 来源工件 | `/alerts/{id}/artifacts/{artifact_id}`、`/incidents/{id}/artifacts/{artifact_id}`、`/cases/{case_id}/artifacts/{artifact_id}`；按真实归属读原文 |
| Case 活动 | `/cases/{case_id}/activities`；含案件、成员和显式事件的匹配活动，去重并保留目标前后值 |
| 人工任务及版本 | `/cases/{case_id}/tasks`、`/cases/{case_id}/tasks/{task_id}`、`/cases/{case_id}/tasks/{task_id}/revisions`、`/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` |

“相关告警”按**同租户、同类型、同命名空间、同对象键**匹配当前材料，可跨 Case；它不表示因果关系。错误父主体返回 404，权限不足与正文不可用分别处理。Case Run 的成员、步骤、工件和结果集合分别检查总数及截断标志。

## 5 状态、交付和空态

| 要表达的含义 | 取值来源和展示规则 |
| --- | --- |
| 业务处理状态 | 告警／事件／Case 的状态字段；Run 结束不自动关闭案件 |
| 机器执行状态 | `run.state/stop_reason`；有工件不代表执行成功，unknown 保持未知 |
| 交付完整性 | `run.delivery_state`；`none/partial/complete/unknown` 与待复核分开 |
| 事件交付说明 | `result.diagnosis.delivery_assessment.reasons/member_coverage`；部分拒收内容可沿 `partial_analysis` 读取 |
| 事件待复核 | `delivery_assessment.review_items.state` 为 `required/none_listed/unknown`；成员、发现及问题 ID 分别列出 |
| 采用与新鲜度 | `is_current_pointer/valid_for_current_input/freshness` 以及 Case 当前判断来源；完整保存不保证当前仍可采用 |
| 业务判定和模型质量 | 判定取该环节有效结果，`accepted` 是程序校验／采用状态，不能作为准确率或正文质量结论 |

`null` 表示未记录或不可得；空数组表示对应集合为空；`0/false` 是有效值。未查、失败、成功查空分别显示，查空不证明安全。费用和 token 未知不能填零。已保存证据目录的条目数、威胁数与没有目录分别处理；威胁数为零不等于“已证明无威胁”。报告建议不得显示为已执行响应。

## 6 Case 与人工反馈操作

既有操作路径、入参及存储关系见 [Case/H 操作交接](openspec/changes/archive/2026-11-11-enable-case-human-http-flow/handoff.md)。按创建 Case 返回的 pending_run_id 显式启动首轮；人工任务通过 POST 创建、PUT 修订，使用返回的 row_version 和 current_revision_id；再次调查先 prepare 再 start。保存反馈不会自动启动调查。

人工结果来自 `tasks.current_revision_id → task_revisions`。每轮领取时冻结所选修订到输入工件 `task_revisions/source_materials`，正文、范围和 human_statement 归属保持，旧修订及历史输入不被覆盖。Result 的六项结论/校验/发现/问题/建议仍使用原字段合同。前次 Case/H 批次没有表列、枚举、告警交接字段或 HTTP DTO 变化。

本地完整路径及 21 正常登录后的独立验收 Case/H 写读已通过；产品页面交互仍需对应前端承接。[配置示例](deploy/aisoc21/case-http.env.example)说明功能写入连接，普通 API 的 DATABASE_URL 保持；不增加权限设计或确认环节。

Case基本管理现新增E44–E47：GET/PATCH `/cases/{case_id}/management`、POST `/close`与`/reopen`。局部修改省略保持；description/owner_id/severity为null清空，tags=[]清空。结案拦截running/unknown；未完人工任务须确认并填写理由，任务保留。重开恢复in_progress，不自动调查；当前结案字段清空，旧理由和前后值可从E17活动读取。所有写入带行版本及幂等键，已在本机/21各20次TCP及SQL验证。页面修改不在当前交接范围。见[本项验收](openspec/changes/archive/2026-11-12-manage-investigation-cases/validation.md)。

## 7 知识能力与当前交付范围

调查可按技术解释、取证指导、历史案例参考三个目的检索知识。资料原文和向量索引分别保存，查询后回读原文及校验内容；具体输入输出见[知识交接](docs/investigation/case-knowledge-handoff.md)、[历史卡片字段](docs/investigation/historical-alert-knowledge-handoff.md)。知识是参考材料，不是本案发生过某行为的证据。

新采用的告警分诊可按当前配置同步为历史知识；保存人工任务不会自动重跑调查。知识维护走原主API的`/api/v1/kb`，不在18024的56项接口中；入口和依赖见[组件指南](docs/integration/component-handoff-current.md)。

当前56个HTTP操作中53已实现；E19提问、E20保存回答、E21显式采用其他结果未实现。统一归并统计、评论附件、探索保存等未完成范围见[接口实施计划](docs/investigation/http-implementation-plan-20261112.md)，不扩展原AiSOC其他功能。

API功能测试和模型结论质量分别验收：Case及告警/事件管理分别完成HTTP和数据库读回，真实完整调查的模型质量仍未通过。自动分析消费者未启用；显式调用后的内部流程由程序执行。当前部署、验收证据和后续工作以[PROGRESS](PROGRESS.md)为准，历史失败不改写；现有页面只用于测试。

### 三类列表完整导出

E54告警、E55事件、E56调查均为`GET /api/v1/socai2/{alerts|incidents|cases}/export`。输入沿用对应列表筛选和排序，加可选`columns`字段路径；不传分页参数。结果为全部命中的CSV附件、实际数量与观察时间，超过配置上限明确报错，不截断。三类公开列分别39/34/31项，逐列含义与默认列、空值/转义规则、下载例子见[HTTP指南](deliverables/investigation-validation-20261106/http-handoff/README.md#完整列表导出)。资产维护及模型流程不受影响。
