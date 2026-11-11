# 告警、事件与 Case 前后端交接

更新于 2026-11-11。本文是功能、数据库、字段和接口的共同入口，以 21 当前部署和实际读回为准。告警分诊、事件诊断、Case C1/C3/Deep/C6 输入输出已部署；数据读取验收通过，模型正文质量继续单列验收。

后续按功能流程推进，必要读写接线与配置随功能处理。告警相关的前后端字段合同保持稳定；字段名、类型、含义、关联和接口返回确需调整时先列明影响并确认。下表保留已核验的运行配置，配置当前值不构成后续功能开发的权限前置。

## 1 接手入口

| 内容 | 权威资料 |
| --- | --- |
| 功能及跳转 | [产品需求](docs/design/alert-incident-case-product-requirements.md)、[F01–F28／J01–J14 清单](deliverables/investigation-validation-20261106/frontend-feature-list.md) |
| 字段到存储、关联及读取 | [服务端数据交接](docs/investigation/socai2-page-data-handoff-20261106.md) |
| 表和列 | [字段字典](docs/design/socai2-field-dictionary-20261103.md)、[机器可读字典](docs/design/socai2-data-contract-20261103.json) |
| JSON 与 HTTP 合同 | [JSON Schema](docs/design/socai2-json-contracts-20261103.schema.json)、[OpenAPI](docs/design/socai2-independent-api-v2.openapi.json) |
| 有值、空值与原件 | [字段取数样例](deliverables/investigation-validation-20261106/page-field-samples.md)、[运行记录及离线材料](deliverables/investigation-validation-20261106/README.md) |
| 程序流程和模型职责 | [执行账本](docs/investigation/current-execution-ledger.md)、[每个模型环节的输入输出](docs/investigation/model-input-output-current-20261109.md) |
| 已有问题与完成边界 | [问题清单](docs/investigation/current-issues.md)、[OpenSpec 任务](openspec/changes/complete-socai2-investigation-chain/tasks.md) |

## 2 当前运行环境

| 项目 | 当前值与用途 |
| --- | --- |
| 目标 | 21，SSH 别名 `sting-infra21` |
| 发布 | `v1.2-20261111-r1`；[发布清单](deploy/aisoc21/release-v1.2.json)固定源码、镜像和挂载 |
| 数据库 | PostgreSQL 16，业务库 `aisoc`，调查 schema `socai2` |
| HTTP | 21 回环 `127.0.0.1:18000`，业务前缀 `/api/v1/socai2` |
| 开发查阅 | 21 回环 `127.0.0.1:4177`，工作台组件 `workbench-20261110-r2`；本机沿[SSH 转发](docs/operations/mac-ssh-relay-20261107.md)访问 |
| 身份 | 用户按正常登录或有效 API key 认证；租户取认证上下文，Case/H 读取要求 `cases:read`，A/I 读取要求 `alerts:read` |
| 页面读取 | `SOCAI2_PAGE_READ_ENABLED=true`、`SOCAI2_ANALYSIS_READ_ENABLED=true`；包括 Case/H 的 GET |
| Case HTTP 写入 | `SOCAI2_CASE_API_ENABLED=false`；页面不得将未开放写操作显示为已保存。按需处理作业使用专用身份和调用者权限 |
| 自动消费 | Agents 暂停；没有自动启动 Case 或恢复消息消费的验收结论 |
| 配置 | [生产 profile](deploy/aisoc21/production-v1.2.toml)选取 [A/I/Case 策略](deploy/local-investigation/investigation-policy-case-v1.toml)；凭据留在受控私有文件 |

模型单次时限 300 秒，Case 整轮 1500 秒，最终阶段预留 300 秒；单 Run 的调用与容量限制读取策略。租户累计调用、token、未结算数量配额不限制。失败、unknown 和待复核按实际状态保存。

`aisoc_app` 获授调查表 SELECT、两个只读函数 EXECUTE 及 `public.assets/public.users` SELECT。工作台使用 `socai2_prod_reader`，按需处理使用 `socai2_prod_processor`，入站来源读取使用 `socai2_prod_ingress`。只读账号、处理账号和数据库 owner 各按职责使用。

## 3 数据库与字段关系

已确认结构为 **29 表、462 列、37 组枚举、40 项 JSON 合同**；JSON Schema 另含 4 个共用定义。迁移 123–126、初始化 SQL、ORM 和字段字典共同描述该结构。2026-11-10 逐列核对类型及可空性无偏差，表、约束、索引、RLS、触发器与函数指纹在发布前后完全一致。

| 功能 | 权威表及主要关联 |
| --- | --- |
| 告警事实与分诊 | `alerts` 的当前材料／分诊／人工反馈指针连接 `alert_materials`、`alert_assessments`；同材料的来源和对象在 `alert_source_refs`、`alert_objects` |
| 事件与诊断 | `incidents → incident_alerts → alerts`；诊断指针连接 `incident_diagnoses`，诊断尝试按 `runs.incident_id` 查 |
| Case 范围 | `cases → case_alerts/case_incidents`；成员关系与显式事件关系分别展示 |
| 冻结输入和执行 | `runs → run_members/run_steps/artifacts`；Run 固定材料版本，步骤按 `seq/parent_step_id` 组织 |
| 正式结果及当前判断 | `results/result_members` 保存各轮结果；`cases.current_assessment_id → case_assessments → case_assessment_sources/case_assessment_members` 给采用依据和覆盖范围 |
| 人工确认 | `tasks → task_revisions`；范围、正文、完成人和完成时刻读取选中的版本 |
| 活动和协作 | `activities → activity_targets`；`comments`、`response_links` 保存明确归属与真实回执引用 |
| 问答及探索设计 | `conversations/messages`、`graph_explorations`；有表不代表相关业务已开放 |

所有关联同时限定租户和父主体。显示名称、主机名和厂商编号不能替代 UUID。当前材料、历史冻结材料与外部来源分别读取。告警交接字段调整按 [AGENTS.md](AGENTS.md#调查数据库-v1-与人工确认)先列影响并确认；其他功能所需内部调整按 OpenSpec 推进。已完成的发布批次无 DDL 或授权变更。

部署时使用[部署说明](deploy/aisoc21/README.md)的统一发布入口。独立空库初始化使用[建表 SQL](deploy/database/init_socai2_v1.sql)，共享业务库核验使用[安装核验程序](deploy/database/install_aisoc21_v1.py)的 `verify`。不得对已有数据执行空库初始化。

## 4 页面读取合同

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

## 6 本次验证与交付边界

当前交付 [ground-case-conclusions](openspec/changes/archive/2026-11-11-ground-case-conclusions/validation.md)。C3 `followups` 上限 2 从冻结 profile 同时约束生成、接收及 partial；超限拒收，不能截断派发。冲突逐 finding/成员核直接原始支持；合法引用不代表正文互斥。历史工件可读，C6 建议不受 C3 派发上限影响。

当前模型边界中，C3/C6 的 observed finding 只选择原始观察字段，`statement` 由程序按原记录路径和值装配；inferred/unresolved 的文字由模型表达。C6 模型生成五个业务问题，程序依据材料读取、查询回执和保留分析补齐 coverage，对外仍保存六问。逐成员读取状态/限制/遗漏保存在冻结材料回执；available 仅指所选字段可读取，未记录明确 unrecorded。C4 整份回执以 execution_receipt、source_path=null 引用，零行、false 和未知值保留。

Case 登记 title/description 在原件中保留，从业务模型视图按配置排除，历史引用恢复也不能带回这两字段。命令/action/outcome 旁说明字段含义，影响问题区分观察动作、有据结果和未知影响。独立人工正文、任务目的及原始材料保持。程序不得替模型改写错误主张使之通过。

本次没有数据库 DDL、告警交接字段或 HTTP DTO 变化。`case_boundary` 的职责标记/原值表/coverage_facts 和 `followup_boundary` 是内部模型请求工件，业务页面继续按第 5 节分别表达执行、交付、采用与质量；现有 Result、报告和 4177 输入/原答/错误的读取路径保持。

直接检查通过，五批真实本地流程已保存读回，但正文仍未通过。第五批 5 调用、54 次 GET 成功，命令结果未知与程序覆盖正确；Deep 仍凭标签判断非生产环境，C6 替代解释仍误写全部查空，两项均已保存。C6 accepted/uncertain 仅表示合同接收。负责人已明确将持续模型问题登记后置，独审对程序交付范围补充 ACCEPT；模型质量仍 NOT_PASSED，原答与失败保留，不继续同类采样。

21 已统一发布 r1，实际加载的 Case profile 与本次来源一致；Case/Run/Result 三次 GET 成功，六项关键结果字段与正式库一致，读取前后快照不变。[交付回执](docs/operations/evidence/case-grounding-20261111-01/delivery-summary.json)列明一次 API 更新、其余容器保持、无生产模型作业/调查数据写入。本地静态资料 63 份，21 为 34 份（追加 5 份，原记录保持）。模型质量问题不冒称修复；产品页面 P01–P04、实际 HTTP 写操作、非空知识和自动消费按[问题清单](docs/investigation/current-issues.md)后续推进。
