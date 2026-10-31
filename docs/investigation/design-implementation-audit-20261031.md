**后续处置（本地实施）：** A01/A02/D01已按[执行记录](audit-fixes-implementation-20261031.md)修复并做31项直接验证，真实部署/复验与独立结束复审待办。下文和静态清单保持修复前5b95138审计事实，表中“未改代码”等为发现时状态，不代表最新工作区。

# 调查模块设计—实现—证据详细审计

审计日期：2026-10-31。业务源码基线：`5b9513860c566ea9c7f17917ddb71cc199a1988e`。本报告记录当前工作区的静态审计结果，入口为[最新指南](audit-guide-20261031.md)，文件哈希、路由、测试定义和原件核对结果见[机器审计清单](../operations/investigation-static-audit-20261031.json)。

**结论：当前 Case 调查主流程已有实现及真实调用证据，但还不能作为“最新版本完整功能与分析质量均通过”验收。** 本次确认两项功能缺陷、一项影响取材的设计缺口；另修正文档中的两处现行说明。最近真实批次仍有追加调查失败和报告语义错误，后续本地修复尚无常驻替换、真实复验完成证据。

## 1. 范围、方法与基线

### 1.1 本次审了什么

按需求边界→设计合同→HTTP入口→业务实现→数据/模型/Tool→报告与读取→测试原件逐项追踪：

- 当前 F1 事件汇总、F2 概况、F4 成员转 Case、F3 主调查与追加问题。
- Case 成员覆盖、关系、时间线、未决问题、公共执行索引、步骤及证据导航。
- 事件湖查询和来源绑定的 CrowdStrike 主机 Tool；模型协议、预算、用量与成本记录。
- 身份/租户入口、持久化表和事务边界、常驻装配及与旧 fixed/program/Agents 路径的关系。
- 当前测试定义和既有本地、真实 PG/模型/事件湖/HTTP 证据的适用范围。

机器清单固定了 **47 个源码/迁移/部署文件**：API v2 目录 31 个 Python 文件，其中 25 个为当前模块文件（含 `__init__`），6 个为旧兼容入口或网关；另有 16 个依赖边界文件。旧网关、共享鉴权、Actions、Fusion、旧 ledger 按相关接缝核查，清单中的“有哈希”不等于对全部依赖逐行重新验收。

当前常驻 factory 装配 **19 个业务 method/path 组合，18 个不同路径**；另有 `/livez` 和 OpenAPI 路由。静态索引了 11 个直接相关测试文件、51 个 `test_` 定义，参数化子场景不据此另计。**这些数字是审计范围，不是本次测试通过数量。**

### 1.2 本次没有执行什么

没有运行业务代码、单元/集成测试、安装器、OpenSpec CLI 或真实调用；没有连接远端、模型、PG、ClickHouse 或厂商服务；没有改业务源码、权限、部署、推送或合并。只读取文件、解析 Python AST/JSON、计算本地哈希和校对文档。本报告也不是旧 Agents 全栈、完整前端或基础设施的重新审计证书。

F5/自动 Case 政策、JWT/RBAC 专项、首次 worker 启用、真实厂商验证不因本报告自动恢复。按既定[实施原则](../architecture/investigation-planning-design.md#implementation-principles)，后续只补受具体问题影响的必要直接验证。

### 1.3 证据不能跨版本借用

| 层次 | 可确认事实 | 不能据此声称 |
| --- | --- | --- |
| 本地最新源码 | `5b95138`，包含 `required_tools`、追加材料精简、`query_status` | 常驻已经运行这些修复 |
| 最新本地修复记录 | 6 项受影响直接用例通过；Office 额度重建 19137→16786，记录剩余 17018，余量 232 | 真实模型会产生合格追加结论；任何输入都能通过额度检查 |
| 最近真实四案例 | `512c004`；镜像 r1，批次 `INVHTTP-20261028-01` | 是对 `5b95138` 的验证 |
| 常驻安装回执 | r1 镜像 `sha256:2fde05d545c3ce9f042f180e91cc38dec30bf85e939f686b7a13dc6d04d27b98` | 当前远端状态仍相同；本次没有重连确认 |
| 迁移回执 | 120/121 已记录安装，登记数 134→136 | 任意环境均已安装或迁移状态已重新核查 |
| 历史 fixed/program | 各阶段有独立合同及替身/真实原件 | Case 已继承其 M3 预留、M7 manifest 核验或恢复保证 |

依据：[本地修复任务](../../openspec/changes/fix-case-followup-gaps/tasks.md)、[本地额度重建](../operations/investigation-followup-fix-local-20261028.json)、[真实批次汇总](../operations/investigation-multi-case-summary-20261028.json)、[常驻回执](../operations/investigation-api-resident-20261028.json)、[迁移与业务联调](incident-case-basic-flow-20261028.md)。

本次重新计算：207 个响应正文 SHA256 全部匹配各案例 summary；3 个冻结的脚本/输入文件全部匹配 execution-observation。部署 bundle 的 475 个文件中 470 个与当前工作区一致，5 个不同：Case 内核、模型协议、事件湖工具、Compose、安装器。这些差异与后续修复范围相符，历史文件没有被覆盖为新版本。

## 2. 发现与优先级

P2 表示影响正常功能或调查判断，需要在相关功能验收前处理；P3 表示说明不一致。D01 单列为取材设计缺口，不伪称既有明确接口合同的回归。以下代码问题均为静态控制流/数据流确认，未制造新的真实运行失败。

| 编号 | 类别/优先级 | 结论 | 当前处理 |
| --- | --- | --- | --- |
| A01 | 功能缺陷 / P2 | `process_activity` 可能把非进程活动事件当作进程执行证据 | 未改业务代码 |
| A02 | 功能缺陷 / P2 | 基础概况刷新失败并保留旧 Case 概况时，过期标记及权限/提交顺序不一致 | 未改业务代码 |
| D01 | 设计缺口 / 建议优先处理 | Case 的告警投影遗漏已有正文和原始材料，限制真正分析并影响来源变化识别 | 已记录，未扩展合同或功能 |
| A03 | 文档 / P3 | 当前接口合同仍写模型输出上限 1200，源码实际 3000 | 本次修为 3000 |
| A04 | 文档 / P3 | 主设计顶部仍将 F4、事件 Case 结果回显标为未接通，并指向旧审计入口 | 本次更新当前入口；历史正文保留 |

### A01：进程工具混入其他事件类别

**位置：** [case_analysis_tools.py](../../services/api/app/investigation_v2/case_analysis_tools.py) 第 19–21、58–67 行；[lake_writer.py](../../services/fusion/app/services/lake_writer.py) 第 321–342 行。

工具向模型声明查询“进程执行记录”，实际条件只有 `process_name != ''`。网络工具另行使用 `class_uid = 4001`，但进程工具没有限定类别，返回列也没有 `class_uid`、`activity_id` 或动作/结果。

本仓库入湖逻辑独立写入 `class_uid` 和 `process_name`，不会把进程名限制在进程类事件。因此，在同一租户、主机、窗口内，**一条 `class_uid=4001` 且含进程名的网络事件同时满足两个工具条件**。它能被包装成“进程执行”结果，模型看不到其实际类别；其他带进程名的事件也有同样问题。即使后续结论引用了合法 E 编号，类型误解仍能进入报告。

这是查询谓词与工具语义的直接冲突，不依赖模型是否“听话”。现有 [Case 直接用例](../../services/api/tests/test_case_analysis_api.py) 第 50–55 行返回预设记录，不执行 SQL 谓词，因此其通过不能排除本问题；本批真实空结果也没有证明混合类别正确。

**建议：**先对齐该工具的含义。若保留进程活动定义，限定仓库相应事件类别，并保留足够的活动/动作字段区分启动等行为；若要返回所有进程相关事件，应更名/改说明并保留事件类型，不能统称执行记录。修复后只需一个同主机同窗口混合进程类与网络类的直接用例，核对返回集合和模型可见类型，不需要扩大压力或恢复测试。

### A02：失败保旧概况时，返回材料和权限检查晚于模型调用

**位置：** [incident_api.py](../../services/api/app/investigation_v2/incident_api.py) 第 58–70 行；[incident_summary.py](../../services/api/app/investigation_v2/incident_summary.py) 第 44–52、145–157、185–244 行；[rls.py](../../services/api/app/db/rls.py) 第 53–60 行。

触发条件：事件已经保存过 `include_investigations=true` 的概况；调用方随后使用默认 `false` 刷新，模型不可用、调用失败或返回无效正文，代码按约定保留旧文及旧 `source_refs`。

存在两个同源后果：

1. **错误的过期标记。** 本次只构造基础 overview，没有 `investigations`；失败后却用它与旧 Case 概况的来源指纹比较，返回 `is_stale=true`。即使事件和 Case 都没有变化，也会如此。随后普通 GET 会根据旧 `source_refs` 补上关联调查，可能又返回 `is_stale=false`。这使同一份保存正文的状态随读取路径变化。
2. **有实际模型尝试后才拒权并回滚。** 具备 `alerts:write/read`、没有 `cases:read` 的用户可以进入默认基础刷新；只有失败保留 Case 概况时才在第 69 行触发 `cases:read` 检查。若模型已经返回无效正文及 usage，成本写入和最后尝试元数据已在事务内准备，随后 403 触发依赖回滚。结果是实际模型尝试发生，但本轮尝试及费用记录没有提交。该路径会拒绝返回 Case 正文，**不属于已证实的数据泄露**。

现有[失败保旧用例](../../services/api/tests/test_investigation_incident_summary.py)覆盖基础概况，[Case 概况用例](../../services/api/tests/test_related_investigations.py)覆盖成功引用及后续变化；尚未覆盖两种模式切换后的失败返回。

**建议：**明确本次请求在失败时允许返回哪份旧正文，并在模型调用前确定相应权限；保留 Case 来源旧文时，按旧来源模式重建返回材料再计算 stale。权限、尝试记录和外部调用顺序一起处理，不能只把布尔值改掉。必要直接验证为：来源不变的 Case 概况→基础刷新失败，以及无 `cases:read` 时的同路径；核对返回/拒绝时机及尝试记录即可，不恢复 JWT 专项。

### D01：已有告警正文未进入 Case 的冻结证据材料

**位置：** [case_analysis.py](../../services/api/app/investigation_v2/case_analysis.py) 第 184–207、497–552 行；[Alert 模型](../../services/api/app/models/alert.py) 第 21、100–102 行；[Case 模型](../../services/api/app/models/case.py) 第 27 行。

A 证据目前只包含标题、时间、级别/状态/处置、连接器、主机/实体、事件 ID、最多 600 字符旧 AI 摘要。已有的 `Alert.description`、`Alert.raw_event` 和 `Case.description` 没有进入当前冻结材料，也没有可供模型按需读取这些正文的 Tool。两个事件湖工具只返回有限投影，产品工具只返回当前主机快照。

这不是抽象假设：冻结的 [Office 原始告警 HTTP 正文](../operations/evidence/INVHTTP-20261028-01/results/office-powershell/001-source-0.response.txt) 包含描述中的父/子 PID 和“未提供 payload/审批记录”的限制，`raw_event` 还包含 `full_log`、`approval_status`。当前 A 投影没有这些字段；其 `source_event_ids` 只是引用，不会自动取回正文。标题、旧 AI 解释与分诊理由不能替代可区分来源的原始内容。

因此应区分两种缺口：“原系统没有证据”与“原系统有字段，但 Case 本次未取材”。目前报告容易只能笼统保留缺口。另一个后果是 `source_hash/material_hash` 仅覆盖当前投影：若只修改 description/raw_event，哈希不变，不能把它解释为整份告警未变；这也限制历史查询复用的来源变化判断。

**建议：**在现有预算内明确最小必要原始字段、来源及截断/省略说明，保存对应原件或可核验引用，再构建有界模型视图。不要把整个任意 JSON 无限制塞进模型，也不要把补充材料当成已核实事实。先用现有 Office 材料对照“来源已有→冻结证据→模型视图”即可确定最小合同，再做必要直接验证。本次未替用户扩展设计或实现。

### A03/A04：文档错误已在本轮校正

[case_analysis_models.py](../../services/api/app/investigation_v2/case_analysis_models.py) 第 9 行是 `MAX_OUTPUT_TOKENS = 3000`；[接口合同](interface-contracts-20261027.md) 的模型段落已改为同值。24000 总额度、4 次模型、4 次工具及主循环 120 秒保持原解释。

[主设计](../architecture/investigation-planning-design.md)顶部更新至当前指南，说明 F4 和事件 Case 结果回显已有实现，F5 未接通。下面 10 月 25 日等历史结论不重写为当前事实。两项修改只纠正文档，不关闭 A01、A02、D01 或真实验证缺口。

## 3. 需求与实现逐项对照

| 需求/设计 | 实际实现 | 审计结论与限制 |
| --- | --- | --- |
| Alert、Incident、Case、Run 分工 | F1 按告警存储的 Fusion 归属取成员；F4 组织 Case；F3 保存实际 Case ID 和选定成员/窗口 | 当前边界基本一致；Case 收录成员不等于每个 Run 都分析该成员 |
| F1 分诊与人工处置分开 | `incident_reader` 用 `raw_alert.id` 关联最新 `triage_verdict`，另取当前 Alert disposition | 未从任意 Run.case_id 猜 Alert/Case 关系；无分诊不伪造 verdict |
| F2 当前字段与 AI 正文分开 | 独立 summary 表、source fingerprint、首次尝试/手动刷新、失败保旧 | 无普通 GET 生成；模式切换失败存在 A02；worker 未启用 |
| F4 选择告警/事件成员建案或关联 | `case_links` 校验当前来源、租户、目标状态；事务保存 Case 与回执 | 同 key 同意图只读；新建 201、重复 200；不顺带启动模型 |
| F3 明确范围、预览与执行 | `CaseAnalysisScope` 固定成员/绝对时间/问题，preview 不创建 Run；启动重新读取 | 最大窗口 7 天；预览不是后续不变保证；部分成员不可读有缺口 |
| 一次操作可追踪、重复不补跑 | tenant/key 派生 Run；actor/Case/request 入 intent；已存在只读 | 不是异步队列或恢复系统；同 key 不续跑、不同 key 可另发起 |
| 模型按需使用真正 Tool 协议 | 原生 tool_calls、服务端名称/参数校验、tool_call_id 回传 | 正常 Tool 轮与最终 schema 分开；不允许模型指定租户/时间窗/任意 SQL |
| 必需补查 | `required_tools` → 原生 function tool_choice；不可用/未遵守即停止 | 意味着尝试，失败也算已尝试；允许历史命中，不保证新查或成功 |
| 进程、网络取证 | 服务端注入 tenant/主机/固定窗口，参数化 SQL，limit+1 判断截断 | SQL 范围受控；进程类别语义有 A01；不提供父进程树/命令行全文 |
| 产品取证 | 来源 Alert→确切 Connector→允许主机→Actions get_host→映射结果 | 只支持当前范围的 CrowdStrike 主机快照；真实厂商未验；不复用旧快照 |
| 追加问题与历史复用 | 新 key+previous_run_id；同 Case/成员集合/窗口；H1 标明旧判断；按材料哈希和查询参数复用 | `refresh_queries=true` 禁止复用但不要求调用；来源投影限制见 D01；湖回填不改变材料哈希 |
| 多成员综合与结论校验 | 每个可读成员对应自身 A；关系必须含选定成员；未知引用拒绝；遗漏补未评估 | 校验结构与引用存在性，不证明引用语义、因果或攻击成立 |
| 时间线、未决问题 | 保存告警/Tool 行时间与来源；缺失时间/窗口外标记；未解决成员补问题 | 时间靠近不等于因果；产品 observed_at 是当前快照时间 |
| 报告、步骤、证据读回 | tenant+Case+Run+profile 筛选，保存 JSON/Markdown，GET 仅读账本 | 保存 hash 但读回不做完整 hash/manifest 验证；原始模型 HTTP 全包也未全量保存 |
| Alert/Incident 关联及 executions | 按 Case 当前关系与 Run 冻结成员分别查询；覆盖统计独立于页内结果 | 未选成员不会冒充 Run 已调查；概况只引用有界已存报告摘要 |
| 事件保持简单 | 手动 include_investigations 取已有 Case 摘要再总结 | 不新增 Incident 深入分析循环；新 Run 不自动重写概况 |
| F5/自动政策 | 当前 factory 没有 Case 自动接线 | 未完成且不纳入当前目标，不能用旧自动 Deep 流程代替 |

代码入口：[incident_reader](../../services/api/app/investigation_v2/incident_reader.py)、[incident_summary](../../services/api/app/investigation_v2/incident_summary.py)、[case_links](../../services/api/app/investigation_v2/case_links.py)、[case_analysis](../../services/api/app/investigation_v2/case_analysis.py)、[case_synthesis](../../services/api/app/investigation_v2/case_synthesis.py)、[related_investigations](../../services/api/app/investigation_v2/related_investigations.py)、[execution_index](../../services/api/app/investigation_v2/execution_index.py)。

## 4. 接口和应用装配

当前 [application:create_app](../../services/api/app/investigation_v2/application.py) 在 query factory 上装配 Alert、Incident、Case、case-links、executions。常驻镜像启动该 factory，**不等于启动旧 program-start/result 网关**。完整字段仍以[接口合同](interface-contracts-20261027.md)和当前源码为准。

| 接口组（前缀 `/api/v2/investigation`） | 作用与主要权限 | 对数据/外部调用的影响 |
| --- | --- | --- |
| `GET /alerts/{id}/investigation-context` | 告警上下文；alerts:read、cases:read | 读取已存关联 |
| `GET /incidents/{id}` | 当前汇总和保存概况；alerts:read；引用 Case 正文时再需 cases:read | 不生成模型正文 |
| `GET /incidents/{id}/investigations` | 关联调查；alerts:read、cases:read | 读取有界列表与全体覆盖 |
| `POST /incidents/{id}/overview/refresh` | alerts:write/read；显式引用 Case 时 cases:read | 一次概况模型调用、保存元数据；A02 另见上文 |
| `POST/GET /case-links` | 写需 cases:write/read、alerts:read；读需 cases:read、alerts:read | POST 仅组织 Case；GET 仅读回执 |
| `POST /cases/{id}/investigation-context` | cases:read、alerts:read | 预览，读取来源和可用 Tool，不调用模型/Tool 查询 |
| `POST /cases/{id}/investigate` | investigation:run、cases:read、alerts:read | 创建 Run，同步模型/Tool 循环和保存 |
| Case history/result/steps/report/evidence/row 共 8 个 GET | cases:read、alerts:read | 已存数据；行索引须合法；无结果时不伪造报告 |
| `GET /executions`、`GET /executions/{run_id}` | cases:read、alerts:read | 当前 Case 结果与旧执行按各自路径导航 |
| `POST /query` | lake:query | 旧受界 activity_records 独立协议；不是 Case 的两种 Tool 名称 |

Case/Incident 等新路由另要求显式 Bearer。共享 CurrentUser 决定 tenant/actor，调用方不能通过业务 body 覆盖租户。DB 查询继续带 tenant 条件，迁移 120/121 启用并 FORCE RLS。这里是静态合同确认，不能外推为所有角色、撤权缓存或数据库角色实际权限已验。

`/query` 沿用共享认证，未加其他新路由的 `_explicit_bearer`；共享认证在 dev 模式保留无凭据 demo 分支。部署时须按实际 auth 配置理解其行为。本次没有确认现网启用该分支，不将其报告成已发生的未授权访问；既有 API Key 正常调用也不能代替 JWT/RBAC 专项。

## 5. 持久化、运行边界与模型证据

### 5.1 数据写入和读回

| 对象 | 真实存储/事务行为 | 需要保留的解释 |
| --- | --- | --- |
| Case 关联 | migration121 复合 tenant/key 主键；同 key advisory lock；Case 变更和 receipt 同事务 | 不回填 Alert.case_id；查询 Case.alert_ids/links 才是本路径关系 |
| AI 概况 | migration120 复合 tenant/incident 主键；行锁串行协调首次/手动尝试 | 最新正文与最后尝试是不同字段；失败应保留原正文来源 |
| Case Run | 复用 investigation_runs，profile=`case_analysis.v1`，case_id 为实际 Case UUID 的字符串 | 数据库该列仍非 Case FK；不能给所有旧 Run 重新解释归属 |
| 步骤和工件 | 每步 event+artifact 提交，提交后重设事务内 RLS；记录 SHA/字节数 | 中途步骤可能已持久化；不是从开始到报告的一笔长事务 |
| 终止结果 | finish 保存 result、Markdown、结束 event 和 Run 状态 | completed 只说明 analysis_complete；有 gaps 时仍 partial |
| 只读接口 | 筛选 tenant/Case/Run/profile 后解析保存 JSON | 没有旧 M7 manifest 全链核验；“有 hash”与“读时验证 hash”分开 |

参考：[Case 内核](../../services/api/app/investigation_v2/case_analysis.py)、[Case 关联](../../services/api/app/investigation_v2/case_links.py)、[工件模型](../../services/api/app/models/investigation.py)、[120](../../services/api/migrations/120_fusion_incident_summaries.sql)、[121](../../services/api/migrations/121_investigation_case_links.sql)。

### 5.2 预算与异常：已知限制，不另立恢复专项

- Case 限额为 4 次模型、4 次 Tool、24000 tokens；模型单次最多输出 3000；循环时间限额 120 秒。前置材料/工具初始化、模型配置和最终持久化不在这一计时块内。
- 调用前按序列化输入字节、工具/schema 和预留输出估算额度，随后使用 provider usage 记已知量。它不是精确 tokenizer，也没有旧 M3 的统一预留账本、USD 上限或租户累计额度准入。
- 用量未知时停止继续查询/分析，不把未知当零；成本表写入失败会留下缺口，但不抹掉本 Run 已记录的用量。
- Run 在 execute 前提交。工具构造/开始记录/配置等在主循环 try 之外，最终 finish 也在外部；外部取消和部分 DB 异常可以留下 running/部分账本。同 key 重读不续跑。配置 resolver 对多类失败自身已降级，不能把“没有配置”误写为必然异常；没有统一终态封存仍是边界。
- 旧 [reaper](../../services/agents/app/investigator/run_reaper.py) 经 [ledger.fail_stale_runs](../../services/agents/app/investigator/ledger.py) 第 752–763 行按 status/started_at 扫全表，没有 Case profile 排除。若共享库中启用且超过其阈值，可能将遗留 Case Run 标 failed，但不会产生 Case 专用终止报告。这不是 Case 恢复能力；本次未查询当前 reaper 开关。

上述与[早期边界记录](current-implementation-reference-20261027.md#review-boundaries)一致，不能以“完整审计”为由自动新增恢复、压力、取消或复杂并发项目。

### 5.3 模型与证据的实际强度

模型输入有来源不确定性、空结果、旧判断和只读限制；Tool 参数由 Pydantic 及本次范围校验。结论 schema 枚举当前合法证据/成员，服务端再次校验并最多纠错一次。这些措施能约束结构，不能核实自然语言是否正确表达了来源。

模型返回在校验后保存规范化 assistant 消息及 usage，未保存完整原始 HTTP envelope；某些无效协议会在规范化记录前停止。Tool 保存完整的**当前工具返回投影**及其模型视图，不等于保存原厂商/原事件全文。产品快照映射也只保留约定字段。这些范围应在审计取证时明确。

材料中的指令按数据处理、工具名白名单、SQL 参数绑定及来源连接器绑定构成现有防线；本次没有进行提示注入攻击试验或完整安全评估，不能声明所有恶意内容风险已消除。

## 6. 测试覆盖和真实结果

### 6.1 当前测试源码覆盖

| 测试文件 | 当前定义数 | 覆盖内容与替身边界 |
| --- | ---: | --- |
| [test_investigation_incident_api.py](../../services/api/tests/test_investigation_incident_api.py) | 4 | F1 成员/分诊/处置/404；ASGI、SQL 替身 |
| [test_investigation_incident_summary.py](../../services/api/tests/test_investigation_incident_summary.py) | 4 | 生成、标旧、保旧、首次任务与材料上限；DB/模型替身 |
| [test_case_links_api.py](../../services/api/tests/test_case_links_api.py) | 5 | create/attach/同 key、范围、无效来源、链接与 Case 历史；DB 替身 |
| [test_case_analysis_api.py](../../services/api/tests/test_case_analysis_api.py) | 10 | 主链、纠错、空/失败、复用、未知用量、预览/读回、追加和必需 Tool；DB/湖/模型 HTTP 替身 |
| [test_case_synthesis.py](../../services/api/tests/test_case_synthesis.py) | 4 | 多成员/关系/时间线/缺口、越界引用；沿 Case 替身链 |
| [test_related_investigations.py](../../services/api/tests/test_related_investigations.py) | 3 | 当前关联与冻结范围、分页/覆盖、Case 概况引用及标旧 |
| [test_investigation_navigation.py](../../services/api/tests/test_investigation_navigation.py) | 3 | 三种索引、证据行、历史复用、旧路径导航 |
| [test_case_product_tool.py](../../services/api/tests/test_case_product_tool.py) | 2 | 来源绑定、模型→Actions HTTP 请求、正常/空/失败；上游替身 |
| [test_case_host_http.py](../../services/actions/tests/test_case_host_http.py) | 1（参数化 3 场景） | Actions 主机适配器正常/空/失败；厂商 HTTP MockTransport |
| [test_investigation_records.py](../../services/api/tests/test_investigation_records.py) | 8 | 独立 activity_records 的源字段、范围、hash、截断及错误 |
| [test_investigation_v2_query_api.py](../../services/api/tests/test_investigation_v2_query_api.py) | 7 | 独立 query 的认证/租户/分派/生命周期；不是 Case 真实湖验收 |

前八个 API 文件共 35 个定义；加 Actions 的 1 个和独立 query/records 的 15 个，共 51 个。方法数不是场景数、执行次数或通过数；本次全部仅静态索引。历史阶段“4/8/…项通过”和最新“6项通过”不相加为一个全量测试成绩。

最新 6 项本地记录没有附完整逐项执行清单及独立日志，因而只按[原回执](../operations/investigation-followup-fix-local-20261028.json)与提交/任务说明认定其有限范围，不冒称当前 51 个定义全跑过。后续保存受影响用例名称、基线和输出即可提升可归属性，无须为此重跑未变化部分。

### 6.2 真实四案例：HTTP 成功与业务成功不同

| 案例 | 自动流程 | 真实记录所支持的结果 | 未关闭问题 |
| --- | --- | --- | --- |
| [Office→PowerShell](cases-20261028/office-powershell.md) | 未通过 | 主调查 completed/partial；追加 failed/input_or_token_limit | 追加纠错预算失败及成员未评估；本地压缩只是修复证据，待真实结果 |
| [LSASS/SMB 子集](cases-20261028/lsass-smb-subset.md) | 通过 | 两成员建 Case，但 Run 只选一名；两个 Tool 成功空结果 | 报告将 T1 叫作成员、把空结果说成查询失败、把旧摘要截断泛化为告警截断；内容审阅未通过 |
| [归档/上传](cases-20261028/archive-upload.md) | 通过 | 主调查、保存和导航完成，保留 partial/证据缺口 | 不等于归档或外传已经证实 |
| [网络阳性/复用](cases-20261028/network-positive-reuse.md) | 未通过 | 主调查及追加均可保存；追加没有调用 Tool | 未进入复用路径，不能把 tool_calls=0 当作复用通过；required_tools 修复待真实复验 |

机器总计：**4 案例、2 流程通过、207 HTTP、111 检查、3 失败；6 Run、5 completed、1 failed；4 次主调查均 completed；16 次模型、8 次 Tool、63937 已知 tokens、unknown_usage=false。** 207 次 HTTP 为 202 个 200 与 5 个 201。状态码反映接口成功返回，报告的 stop_reason/completion 与业务检查须另读。

本次核验原件哈希和汇总一致性，未重新访问这些 Run。四案例使用已有模拟业务材料，通过真实服务/模型/数据库/事件湖执行；“真实调用”不等于真实攻击或真实厂商环境。

### 6.3 已有证据与尚缺证据

| 能力 | 已有证据 | 当前结论 |
| --- | --- | --- |
| Case 建案、范围、主分析、步骤/报告/关联读取 | ASGI 替身、迁移/PG联调、r1真实HTTP | 实现与主链存在性成立，不替代最新版本全通过 |
| 追加压缩/required_tools/query_status | 最新本地直接用例、离线额度重建 | 本地修复已有记录；真实追加和语义验收未关闭 |
| 真实事件湖查询 | 早期专项与真实批次 | 来源调用存在；混合事件类型 A01 尚无相应直接覆盖 |
| 产品主机工具 | API/Actions 两侧替身证据 | 无真实厂商凭据/HTTP、无模型实际使用厂商 Tool 的证明 |
| F2 首次 worker | 代码及替身 | 无启用回执；不能声称当前会自动首次生成 |
| 鉴权 | 路由/CurrentUser/RLS 静态链和普通 API Key HTTP | 不覆盖完整 JWT、撤权/缓存或当前数据库权限专项 |
| 前端 | 本报告核接口、导航和Markdown下载 | 没有完整页面交互验收；API 已有不等于前端入口已交付 |
| 旧自动/F5 | 历史 Agents 路径和各自证据 | 新 Case 自动政策未实现，旧 OpenSpec 2.2/2.3 不核销 |

## 7. 后续处理顺序与验收方式

1. **先处理 A01/A02。** 修正工具证据类型和概况失败模式；只做上文明确的必要直接验证，保存失败前提、修复差异和结果。不重启权限或恢复专项。
2. **明确 D01 最小取材合同。** 用已有 Office 原件核对原始字段、冻结材料、模型视图的差异，再决定哪些字段应进入；明确省略和来源限制，避免继续把旧 AI 解释当原始事实。
3. **准备具体的修复版本核对材料。** 列源码基线、镜像、迁移需求、受影响文件和调用字段。r1 不能接收 r2 的 required_tools；部署仍需独立授权，本次不执行。
4. **版本实际更新后，只复验受影响业务。** Office 追加应产生有效结论或诚实缺口；网络追加应实际进入指定 Tool/适用复用路径；LSASS 检查空结果、成员 ID 和摘要截断语义。保留旧失败，不用新成功覆盖旧证据。
5. **根据功能目标判断关闭。** 除了 HTTP 和结构检查，还要查看关键结论是否被所引来源支持、未选成员是否仍不计覆盖、历史报告是否保持原样。partial 可以是正确结果，不要求为了“通过”强行得出攻击成立或安全结论。

每项关闭只需关联明确的源码修复、对应直接验证和实际适用版本；不引入逐层独审门或额外冗余框架。部署、厂商验证、worker启用、F5 和 JWT 专项分别保留既定授权边界。

## 8. 本轮交付与可复核性

- 本报告：设计、实现、接口、存储、模型/Tool、测试与真实证据的完整对照及问题清单。
- [机器审计清单](../operations/investigation-static-audit-20261031.json)：47 个实现/依赖文件哈希、11 个测试文件及定义位置、19 个路由、207 个正文哈希、3 个冻结文件、475 项部署 bundle 对照。
- [最新指南](audit-guide-20261031.md)：增加本报告入口及当前结论；[接口合同](interface-contracts-20261027.md)和[主设计当前提示](../architecture/investigation-planning-design.md)纠正 A03/A04。

本次没有修改业务源码、测试源码或既有证据原件，没有将任何未运行检查写成通过。此前工作区的文档和其他未提交材料保留。

收尾静态检查：47 个实现/依赖文件和 11 个测试文件哈希保持；相关 Python AST 解析无错误；39 份调查 Markdown 的 1223 个本地文件链接及文档锚点无缺失，`git diff --check` 无空白错误。以上是文件/语法检查，不是执行测试。
