# 告警、事件与 Case 前后端交接

**21 正式服务已更新到 `c173-release-20261121-04`。** HTTP 18024 和 Swagger 18080 共 82 个业务操作，调查运行目录已提供「未升级调查」计数与卡片标记。[正式验收](docs/operations/evidence/c173-escalation-release-20261121-04/README.md)

产品端接入 C173 时，从交接清单查看正式接口、页面跳转参数、调用示例、联调检查项，以及业务后端需要回填的依赖。[C173 后端联调交接清单](docs/integration/c173-backend-handoff-20261121.md)

2026-11-17 历史记录。21 当时部署processing-20261117-r1、完整HTTP `acceptance-http-20261117-r1`、同版Swagger及4177 r8（0.6.1）。**当时正式 API 为[18024](http://192.168.1.21:18024)，Swagger为[18080](http://192.168.1.21:18080/)，80个业务操作，无登录或Token要求，公共告警字段合同不变。** 正式aisoc仍32表521列；调查历史按授权备份清理，账号/租户/来源配置保留。[发布与核零](docs/operations/evidence/acceptance-release-20261117-01/README.md)之后，已完成[新两段完整测试](docs/operations/evidence/acceptance-fullflow-21-20261117-01/README.md)。

本批2告警/3上下文形成1事件、1Case各两轮。477份HTTP成功回执、142份累计工件、真实首轮201建案和后轮202检查及比较身份已核；[HTTP模块11组独立复核](docs/operations/evidence/acceptance-fullflow-21-20261117-01/independent-http-review.json)通过。8次模型均stop，4项自动引用问题和1项人工比较正文问题仍保留，两轮Case均accepted/uncertain/partial。质量问题不阻断合法下游，程序通过不代表模型质量通过。

[统一设计§12](openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md#12-测试模块与调查工作台统一需求2026-11-17)的工作台任务1/2已发布：[4177](http://127.0.0.1:4177/viewer/)默认Case，事件/告警各自列表；Case及事件按实际轮次查看，告警显示单次分诊。Case“进程活动及后续外联调查”首轮冻结1条、后轮2条，上游沿用/新增、HTTP接入、C3具体领域、C4查询、C6原答及问题均可查。[实际浏览器](docs/operations/evidence/acceptance-fullflow-21-20261117-01/viewer-browser-01.json)与[代理读回](docs/operations/evidence/acceptance-fullflow-21-20261117-01/viewer-http-verification.json)通过。后台tenant/来源关联保存，8份模型输入无控制身份。

[统一材料及Docker入口](tools/testdata/ACCEPTANCE.md)3a–3d已完成并用于本批：首段检查通过后显式append，同一Case续跑，程序按保存ID去重汇总并生成[输入/Schema/原答报告](docs/operations/evidence/acceptance-fullflow-21-20261117-01/results/report-01/report.md)。[测试模块10组限定独审](docs/operations/evidence/acceptance-fullflow-21-20261117-01/independent-test-review.json)通过；未新增业务路由/告警DTO。4b[来源识别子步](docs/operations/evidence/workbench-test-source-20261117-01/README.md)随后完成本机验证与限定独审：新来源配置以lyc开头，页面通过现有HTTP按所选Run冻结来源识别，全量/部分测试分别标识，无需先发布账本；后台来源/tenant保留，20项A/I/C3/Deep/C6消息检查无注入的控制标记。[报告指定主体/Run跳转](docs/operations/evidence/workbench-deeplink-20261117-01/README.md)随后通过本机验收与限定复核：report/session可选独立展示配置，Case首轮/后轮精确打开，缺失或错环境不回落latest；原HTTP合同不变。4b现已按负责人要求[发布21并读回](docs/operations/evidence/workbench-4b-release-20261117-01/README.md)：新页面、配置和验收工具已上线，辅助账本保持。[最终报告](docs/operations/evidence/workbench-4b-release-20261117-01/report-02/report.md)可直接打开同Case两轮，实际4177核冻结1/2、紫色逐轮来源、刷新/重载及错误目标不回latest。旧来源telemetry-channel-02显式兼容，新来源默认lyc；本批0新业务写/模型，[测试模块最终限定独审](docs/operations/evidence/test-workbench-4b-release-20261117-01/independent-release-review-01.json)7组通过、无未关闭发现。D5a异常PG/C6存取、D5/D6及整个change仍未完成；旧失败与原答保留离线，清理前记录见[历史快照](docs/handoff/history/2026-11-17-acceptance-release/FRONTEND_BACKEND_HANDOFF.md)。

| 接入事项 | 当前入口 |
| --- | --- |
| HTTP接口、字段、示例、错误 | [21 Swagger](http://192.168.1.21:18080/)、[同版OpenAPI](http://192.168.1.21:18080/handoff/openapi.json)、[本轮合同](deploy/aisoc21/acceptance-release-20261117-01/contract/openapi.json) |
| 完整部署配置 | [完整核心release](deploy/aisoc21/acceptance-release-20261117-01/release.json)、[4177/验收工具4b配置](deploy/investigation-test/releases/workbench-4b-20261117-01/release.json)、[HTTP profile](deploy/aisoc21/acceptance-release-20261117-01/http-profile.json)、[部署步骤](deploy/http-service/README.md) |
| 任务及执行读取 | [统一分析记录](docs/integration/run-directory-http.md)、[任务列表/详情](docs/integration/analysis-tasks-http.md)、[步骤/工件完整分页](docs/integration/run-records-http.md) |
| 受理及Case关系 | [异步提交](docs/integration/analysis-submission-http.md)、[Case首轮](docs/integration/case-initial-http.md)、[分配与关联查询](docs/integration/case-allocation-http.md) |
| 真实执行展示 | [4177](http://127.0.0.1:4177/viewer/)，经SSH隧道访问21，只读业务HTTP与测试账本；来源标识按本轮冻结告警识别，报告指定Run直达，紫色测试标识不进入分析模型 |
| 配置及字段合同 | [配置索引](docs/operations/configuration.md)、[数据库当前入口](deploy/database/CURRENT.md)、[页面字段/跳转](deliverables/investigation-validation-20261106/frontend-data-navigation-contract.md) |

告警入站后自动登记首次分诊，事件诊断及Case首轮/更新经唯一联合调度器执行。HTTP受理返回task时Run可为空，沿task→attempt→Run→steps/artifacts完整分页和返回的content_url读取；建案不再调用旧E11/E13，旧手动告警E36已退役。查询不会启动分析。Case更新用正式check/rerun语义，不能以重新建案替代。

D1–D4c改变模型业务视图及异常材料接线，公开告警字段和租户/来源关联保持。新C1的incident.analysis_material冻结原I主体、Run和来源工件；读取不得用latest替换。Result.source_answer是对话回答来源，null合法；C6原答通过实际Run、模型步骤与Result.delivery的来源查阅。执行状态、交付完整性、待复核、采用状态及质量分别解释。

预算保持窗口65536，A/I/Deep输出8192、C3/C6输出16384，I4h/Case6h与7天窗口不变。新02增量通过明确HTTP check验证，不宣称自然周期等待已验。厂商/UEBA/graph等未配置来源仍显示真实未查或失败原因。完整当前状态见[PROGRESS](PROGRESS.md)，之前候选端口及逐批验证细节保存在[本轮更新前快照](docs/handoff/history/2026-11-16-release-r4/FRONTEND_BACKEND_HANDOFF.md)。

推荐调用关系：`产品前端 → 业务后端 → 调查HTTP API`。资产库存及人员目录由业务后端维护；owner_id/assignee_id必须是同租户有效用户UUID。基础连接、tenant和actor来自显式服务配置，模型输入不包含后台tenant_uid；原始告警及关联仍保存。

### 按业务调用

以下表格只保留原71操作交接基线供历史追溯，不是当前调用步骤。E11/E13/E36在当前版本均已退役，建案/首轮使用[当前指南](docs/integration/case-initial-http.md)，后续检查和再次调查使用[异步提交指南](docs/integration/analysis-submission-http.md)。路径省略`/api/v1/socai2`；参数和返回以18080当前80操作合同为准。

| 类别 | 功能和调用顺序 | 返回结果与注意点 |
| --- | --- | --- |
| 告警读取 | E26 `GET /alerts` → E28 `GET /alerts/{alert_id}` → E22 `GET /alerts/{alert_id}/analysis`；E24 读指定 Run，E32/E33 读步骤/工件 | 分开读取告警事实、当前有效分诊和历史尝试；材料正文用 E31 |
| 告警分析（历史同步入口；当前已退役） | E36 `POST /alerts/{alert_id}/analyze` | 仅记录旧流程；当前由入站登记自动任务，不调用此路径 |
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
| 采用已有调查结果 | E63预览→E21提交operation_key/expected_review_token/reason及必要未完工作确认→E03/E64/E17读回 | 新增判断并保留旧版本；原Result、任务/Run及处理状态保持。[调用指南](docs/integration/result-adoption-http.md) |

调查没查清的内容直接写在调查结论里，例如“尚未确认这次登录是否由本人操作”。需要找人确认时，用户再建“联系本人核实登录”的任务；不会自动把每个疑问变成待办。

告警涉及设备时，调查服务到业务后端维护的现有资产库存中查找，找到就返回设备信息和标签，没找到返回空列表。查询路径是 `GET /alerts/{alert_id}/records/assets`（加上前述业务前缀），事件用 `GET /incidents/{incident_id}/records/assets`。文档编号E30只是方便查找同一个分区读取接口；`assets`填在路径最后，不是新增服务、数据表或查询参数。资产创建和标签维护由业务后端负责。

案件候选E66已发布本机和21并各11次GET读回：按当前成员或指定真实告警/对象查一层候选，返回匹配原件、时间范围和归属；明确加入复用E08。规则、字段和错误见[候选查询指南](docs/integration/case-exploration-http.md)。[E67–E69保存恢复](docs/integration/case-exploration-save-http.md)已实现并发布：读取底图、保存、恢复，固定原图/展开/画布，版本冲突409，不改变成员和Run。本机27次功能验证及两端各6GET读回通过；21本轮仅只读，未实测生产保存写入。

案件故事E65只读查询已发布本机和21并读回：`GET /cases/{case_id}/story`支持搜索、告警等级筛选和游标分页，返回原告警、调查及人工完成修订。字段、跳转及错误见[故事查询指南](docs/integration/case-story-http.md)。AI对话继续暂缓。

[E70告警相似历史复核](docs/integration/alert-review-http.md)已发布：默认按当前告警发生时间回看30天，返回最近候选及对象/战术来源；用户核对后才用E48/E49反馈。23次本机功能GET通过，正式本机8GET命中3条，21既有记录5GET为空候选，均无业务写入或模型调用。同主机最近7条已由[E71](docs/integration/alert-host-http.md)提供，匹配不要求战术相同。

### 请求、版本和错误

内部默认可信，调用不需要登录、Token或角色校验；JSON请求使用 `Content-Type: application/json`。租户及记录操作人由服务配置提供。下例只示范 Case 管理；替换 Case ID、当前版本和本次操作 UUID 后调用：

```http
PATCH /api/v1/socai2/cases/{case_id}/management
Content-Type: application/json

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
- `501`：E19助手提问、E20保存回答尚未实现，按负责人2026-11-13要求暂缓；E21采用已有基础调查结果已实现。
- `503` 或执行请求超时：先读取原 Run；服务错误 `detail` 可能为对象，不能假定统一是字符串。
- E02/E26/E27现支持筛选、排序、分页；告警时间按event_time，事件至少一条成员告警在窗口内，Case按business_updated_at。带时区时间前闭后开；缺值始终排序在后。告警/事件filtered_total是筛选数，total/overall_stats是整体；Case total是筛选数、metrics是整体。新条件用next_cursor续页，改条件清空；旧无新增条件的before_id保留，不能混用。完整参数见[列表用法](deliverables/investigation-validation-20261106/http-handoff/README.md#列表查询怎么用)。

告警/事件写入的参数、批量选择、完整返回及错误见[后端测试指南](docs/integration/backend-test-guide.md#告警人工判定与告警事件管理)。

“已实现”只描述接口业务是否存在；当前未完成的问答及真实响应等见[接口实施计划](docs/investigation/http-implementation-plan-20261112.md)。真实模型结论质量仍未整体验收通过；页面修改不在这次后端交接范围。

后续按功能流程推进，必要读写接线与配置随功能处理。告警相关的前后端字段合同保持稳定；字段名、类型、含义、关联和接口返回确需调整时先列明影响并确认。下表保留已核验的运行配置，配置当前值不构成后续功能开发的权限前置。

本项[分诊后历史知识同步](openspec/changes/archive/2026-11-12-sync-saved-alert-knowledge/validation.md)已完成本地直接流程、独审及 21 r5 发布读回；采用原 Run trace／工件读取表达同步状态，不新增告警 DTO 字段。历史卡片及同步字段见[知识交接](docs/investigation/historical-alert-knowledge-handoff.md)。

## 1 接手入口

| 内容 | 权威资料 |
| --- | --- |
| 产品功能与规则确认 | [逐页功能清单](deliverables/investigation-validation-20261106/frontend-feature-list.md)：目的、操作结果、后端实现状态与接口；[规则记录：D01–D07 全部已确认](docs/design/investigation-product-decisions.md)；[产品需求](docs/design/alert-incident-case-product-requirements.md) |
| 功能对应字段及跳转 | [F01–F28 字段／J01–J14 跳转附录](deliverables/investigation-validation-20261106/frontend-data-navigation-contract.md) |
| 字段到存储、关联及读取 | [服务端数据交接](docs/investigation/socai2-page-data-handoff-20261106.md) |
| 当前调查表与写入边界 | 正式 `aisoc.socai2` 应用增量 130–135，实际为 35 张表、566 列。[正式验收](docs/operations/evidence/c173-escalation-release-20261121-04/README.md) |
| HTTP字段审计来源 | [基于原三份资料的核对结论](deliverables/investigation-validation-20261106/http-handoff-audit/README.md)：先按告警22/事件15/调查88项，原43操作/522字段已审，Case管理增加4操作/10字段，前批告警/事件管理增加6操作/8字段，前批列表封套增加2字段，前批新增3个CSV操作，前批新增E57归并统计，前批E58/E59普通评论、本批E60–E62附件引用；该历史批次为71操作，原JSON有542个固定字段出现位置，E57新增12个、评论新增22个、附件引用新增37个、采用新增42个、故事查询新增13个、候选查询新增35个、保存恢复新增22个、告警相似复核新增27个、同主机近期查询新增12个（合计764）与35组既有动态说明；新graph/view_state展示JSON见E67–E69指南，CSV另说明104个允许列；字段说明已合入当前Swagger |
| HTTP逐项对接与在线文档 | 正式 API 18024 与 Swagger 18080 使用同版 82 个操作。[C173 后端联调交接清单](docs/integration/c173-backend-handoff-20261121.md) · [正式 Swagger](http://192.168.1.21:18080/) · [当前发布回执](docs/operations/evidence/c173-escalation-release-20261121-04/README.md) |
| HTTP功能验证与后续实施 | [本机路由/真实隔离库验证](openspec/changes/complete-socai2-investigation-chain/http-functional-validation-20261112.md)：31项检查、43操作回执，模型为替身，真实质量未核销；[未实现功能计划](docs/investigation/http-implementation-plan-20261112.md)。[统一独立入口验收](openspec/changes/archive/2026-11-12-serve-investigation-api/validation-20261112.md)已完成本机/21 TCP Case/H与SQL读回，详见下表 |
| JSON 与 HTTP 合同 | HTTP 请求和响应以本版 OpenAPI 为准。数据库与原件可以查阅既有 JSON Schema。[正式 OpenAPI 下载](http://192.168.1.21:18080/handoff/openapi.json) · [同版仓库快照](deploy/aisoc21/c173-release-20261121-04/contract/openapi.json) · [原件 JSON Schema](docs/design/socai2-json-contracts-20261103.schema.json) |
| 对外与内部接口边界 | [架构说明](docs/design/investigation-http-boundary.md)：列表/详情和显式业务提交属于独立对外HTTP，调查步骤/组件调用单独维护。当前提交合同为异步diagnose/investigations；旧analyze及prepare/start外部入口已退役，内部能力按自身归属保留 |
| 有值、空值与原件 | [字段取数样例](deliverables/investigation-validation-20261106/page-field-samples.md)、[运行记录及离线材料](deliverables/investigation-validation-20261106/README.md) |
| 程序流程和模型职责 | [执行账本](docs/investigation/current-execution-ledger.md)、[每个模型环节的输入输出](docs/investigation/model-input-output-current-20261109.md) |
| 模型输入字段选择 | [第32节C3程序分工](docs/operations/evidence/case-c3-coverage-20261113-01/README.md)与[10批发布基线固定链路](docs/operations/evidence/fixed-investigation-20261113-10/README.md)已本地直接核验：C3模型五项业务问题，程序补coverage，保存/HTTP读取仍六问；Deep/C6按各自任务取材料。1新Run/5次生成，C6一次纠错后accepted/uncertain/partial并成为第3版current，4次ASGI/SQL读回一致；原A/I、H、失败及旧结果保持。HTTP字段和数据库表不变，调用方无需改合同；10批验收后已发布核心r1，独立18024已同步并完成两端既有记录读回。正文质量NOT_PASSED。11-14按负责人要求新跑[三案展示](docs/operations/evidence/fixed-investigation-20261114-01/README.md)，1案待复核并采用、2案拒收未采用；当时两端4177和4173显示三案快照；现已撤出活动展示，按页首清理回执处理。不以输入预览或结构接收追认质量。 |
| 当前固定流程与流式更新 | [第1–7步及当前任务](openspec/changes/schedule-streaming-investigation-updates/tasks.md)沿各批证据；D1–D4c已发布r4，新02正常完整链已通过，8–10后置，D5a异常PG/C6目标未完成，D5/D6整体及change结束审计仍待 |
| 已有问题与完成边界 | [问题清单](docs/investigation/current-issues.md)、[OpenSpec 任务](openspec/changes/complete-socai2-investigation-chain/tasks.md) |

## 2 当前运行环境

21 当前 HTTP 18024、Swagger 18080 与联合调度运行 `c173-release-20261121-04`。业务路径前缀为 `/api/v1/socai2`。正式调查库为 `aisoc.socai2`，Fusion 和 4177 分别使用当前配置。[正式读回](docs/operations/evidence/c173-escalation-release-20261121-04/README.md)

### 2026-11-17 环境记录

| 项目 | 当前值与用途 |
| --- | --- |
| 目标 | 21，SSH 别名 `sting-infra21` |
| 核心与旧服务 | processing-20261117-r1的Fusion和唯一联合调度器运行，旧r4、旧Agents及旧独立消费者停止；实际容器和镜像见本轮发布回执 |
| 数据库 | 正式aisoc.socai2为32表521列，普通密码/TLS require；当前身份沿r4配置，旧候选或本机历史库不混用 |
| HTTP / Swagger | 192.168.1.21:18024/18080运行acceptance-http-20261117-r1，业务前缀/api/v1/socai2，80操作、无鉴权。旧18424/18480候选停止；本批真实两段完整链已通过，质量和未覆异常分开记录 |
| 本机与旧入口 | 本机最近观察18024接隔离`v12_upgrade_dev`，本次未操作。21旧主/独立入口也在停止清单内，不作为可用替代入口。部署与架构见[profile](deploy/http-service/README.md) |
| 调用上下文 | 候选内部默认可信，租户及记录操作人由`SOCAI2_HTTP_CONTEXT_FILE`指定；无需登录、Token或角色。候选tenant/actor已实际建立并与应用配置核对 |
| 页面读取 | 候选配置`SOCAI2_PAGE_READ_ENABLED=true`、`SOCAI2_ANALYSIS_READ_ENABLED=true`；包括 Case/H 的 GET；列表空态及S01真实A/I/Case非空结果已读回，H等其他场景按原证据范围 |
| Case HTTP 写入 | 候选`SOCAI2_CASE_API_ENABLED=true`；同库普通writer受控连接、TLS及零行更新回滚已验。成功建案衔接Kafka实际落库及A/I处理后的事件，保存并读回Case及首轮任务；空库就绪不算成功写验收 |
| 自动消费 | 21新版Fusion及唯一联合调度器运行，旧Fusion/投影/Agents停止；本批已实际消费5条新材料并完成A/I/Case，HTTP启动不隐式启用消费者 |
| 配置 | 当前版本[HTTP profile](deploy/aisoc21/acceptance-release-20261117-01/http-profile.json)及[部署说明](deploy/http-service/README.md)；凭据留在受控私有文件，不继承旧容器连接 |

模型单次时限 300 秒，Case 整轮 1500 秒，最终阶段预留 300 秒；单 Run 的调用与容量限制读取策略。租户累计调用、token、未结算数量配额不限制。失败、unknown 和待复核按实际状态保存。

`aisoc_app` 获授调查表 SELECT、两个只读函数 EXECUTE 及 `public.assets/public.users` SELECT。工作台使用 `socai2_prod_reader`，按需处理使用 `socai2_prod_processor`，入站来源读取使用 `socai2_prod_ingress`。只读账号、处理账号和数据库 owner 各按职责使用。

## 3 数据库与字段关系

原正式库123–127为**28表、450列**，原职责和字典见[调查表范围](docs/investigation/investigation-table-scope.md)、[机器字典](docs/design/socai2-data-contract-current.json)。当前21候选已应用128/129，为**32表、521列**，实际迁移及身份见[供给回执](docs/operations/evidence/streaming-candidate-20261115-01/database-prepare-01.json)。下表保留原主体关系，新增分析任务/尝试/主体状态及排除关系沿[当前结构入口](deploy/database/CURRENT.md)。业务后端通过HTTP对接，不需要复制调查表或旧AiSOC公共支撑表。

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

需要独立部署调查服务时，按[服务部署说明](deploy/http-service/README.md)及[数据库安装入口](deploy/database/CURRENT.md)执行；普通业务联调只配置HTTP地址。

## 4 页面读取合同

后续业务后端通过 **HTTP** 对接，不要求直连调查库或照搬旧 AiSOC 表。完整参数、示例、错误及缺口以[本次HTTP交接包](deliverables/investigation-validation-20261106/http-handoff/README.md)为入口；原OpenAPI保留为结构来源。

下列路径均以 `/api/v1/socai2` 为前缀。前端优先沿响应中的身份和内容链接取数；完整参数、返回类型和限制以 OpenAPI 为准。

告警列表和详情的 `triage.attck_mappings` 返回当前有效 AI 分诊的 ATT&CK 映射（本地已验）。每项含 `tactic_id`、`tactic_name`、`technique_id`、`technique_name` 和 `source_refs`，战术和技术各自可空。显式无映射为 `[]`，旧结果、映射不可用或当前分诊失效为 `null`。前端按有效 AI 战术优先、`derived.tactics` 检测标签兜底取类别，来源标识由前端展示。[字段和验证](openspec/changes/complete-socai2-investigation-chain/alert-attck-mappings-20261123.md)

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

“相关告警”按**同租户、同类型、同命名空间、同对象键**匹配当前材料，可跨 Case；它不表示因果关系。错误父主体返回404，正文不可用按实际状态处理。Case Run 的成员、步骤、工件和结果集合分别检查总数及截断标志。

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

**阶段一状态：本地验收完成，待统一发布。** 七步开发实施及直接验证已收口，以下保留逐步验收范围；统一发布和发布后验证见[阶段一交付待办](openspec/changes/complete-socai2-investigation-chain/stage1-problems-and-plan-20261114.md#发布与发布后验证待办)。后续调度问题不计入阶段一待办或关闭条件。

A/I v4原结论保留已通过[阶段一步骤1保存读取验收](docs/operations/evidence/stage1-ai-retention-20261114-01/README.md)：引用问题不删除或改判原业务结论，未知引用不伪造证据，引用解析所得的空集合不以虚构依据补齐；引用诊断在既有E32/E33工件链的`model_response.content_json.citation_review`读取，原答另关联`original_response_artifact_id`，最终结果仍从原分析入口读取。A解释模板的真实事实来源不表示模型原引用正确，需与原声明区分。HTTP字段、类型和枚举不变，质量未检查/有问题与交付完整性分开；当前20261117-r1包含上述实现；原本机证据仍只代表当批，21新业务实证见页首两段测试。

Case C3 v3/Deep v2/C6 v2已通过[步骤2保存、读回及采用验收](docs/operations/evidence/stage1-case-retention-20261114-01/README.md)，同样仅本地待发布。Case `model_response.content_json.payload`保留`raw/derived/citation_review`，原答工件、请求、步骤和hash可追溯；C3汇总在`basis.citation_review`，Deep汇总及C6 report_json在`citation_review`。模型原结论和原状态沿原Result、当前判断与历史接口读取；实际证据链接可以为空，不能把空链接当成模型未分析或把采用当成质量通过。后续模型接收相关原内容及简短质量提示，角色仍为prior_analysis。54次GET、4次采用请求通过，真实stale与人工选择保护保留；该步骤2批次未改C3额度或补答。

[步骤3 C3正常输出合同](docs/operations/evidence/stage1-c3-contract-20261114-01/README.md)也已完成本地保存读取验收：当前Case策略将C3输出额度设为8192，新请求一次要求七部分，`c3_output`配置最多5发现并以`socai2.c3-output.v1`冻结到请求边界；提示、生成Schema与接收共用该值。48项直接检查和44次GET通过，5项原文继续进入C6，原答/派生/独立诊断仍沿既有工件接口读取。旧冻结工件、C6容量、告警字段和HTTP合同保持；该步骤3批次未实施补答；补答及内部展示后来已由步骤4/7分别完成，21发布仍待办，不代表真实模型质量通过。

[步骤4有界补答](docs/operations/evidence/stage1-c3-completion-20261114-01/README.md)已本地验收：初答、补答仍各有独立model请求/原答/响应，另存`source_snapshot`类型的`c3_section_completion`保留/合并工件，C3汇总在`basis.section_completion`给出工件ID、缺失字段和`field_origins`。合并是程序装配，不冒充单次模型原答；原length/失败保留，已完成字段不被覆盖。补答失败时C3保留部分原分析及缺项供C6读取，不派发半条计划。真实内网模型仅补followups、新隔离库19次GET通过；历史首答不重派，C6及采用未在本批重验，现有预算保持。HTTP字段、迁移及告警合同不变，仍未发布。

[步骤5补查分流](docs/operations/evidence/stage1-followup-routing-20261114-01/README.md)已本地验收。C4 `followup_dispatch.routes[].activity`及Deep汇总的`activity`以`socai2.followup-activity.v1`提供程序装配的实际活动：方式、query原答/投影工件、工具、状态、返回数量、是否复用及data/empty/not_queried/failed/unknown；`new_query_attempt_count`不能当问题已回答或资料已证实。原计划目标/方式/绑定保持，human不自动建任务，graph不计外部取证。新Case真实认证查询返回2条、湖上下文实际进入C6，Result accepted/uncertain/partial及47次GET一致；首轮unknown及33次读取保留。按负责人补充授权，21湖已写6条合成演练数据，程序/HTTP尚未发布。预算、C6预留及告警合同不变。

[步骤6原件存取](docs/operations/evidence/stage1-original-retention-20261114-01/README.md)已通过本地保存读取。既有Case/A/I工件详情及告警材料详情不再因超过1 MiB拒读，`content_json/content_text`仍返回完整原件，工件按原size/hash核对；列表仍为元数据。后台A/C2/C4回执的`rows`保持原数量上限，额外探测行单独留在`overflow_rows`，完整已取得行按两段顺序拼接；不能将额外行当模型已使用材料。新Run输入工件通过source_refs关联`socai2.runtime-policy.v1`完整配置快照。阶段input指针为空时从同Run输入及子步骤沿不可变ID读取，禁止读latest补历史。历史未保存配置、未收到正文、unknown分别保留。新批7份大原件、26次GET及历史8Run/176工件/73次GET通过，告警字段与HTTP Schema不变，未发布；节点预览和结论展示已由后续步骤7完成本地验收。


[步骤7内部展示](docs/operations/evidence/stage1-viewer-20261114-01/README.md)已本地验收：同主体/source_run_id的原结论直接显示，执行、交付、引用问题、待核和保存时/当前采用分开；取消I仅有记录无正文时明确未保存结论。C3初答/补答/合并及来源分开，长原件按配置预览后完整展开；14项离线、11快照逐值读回和21项实际浏览器检查通过。本机4178预览，实际4177与核心/独立HTTP未发布，产品页面接线不据此判完成，固定HTTP合同未改。

阶段一[接口影响评估](docs/operations/evidence/stage1-viewer-20261114-01/http-impact.md)明确固定Schema相同也存在读侧兼容依赖：接口侧在同一只读PG快照对比旧/新freshness_sql，旧判stale、新判current；旧正式reader还会按1 MiB门槛拒读新大原件。核心与独立API须在整体交付时同步读侧及动态工件解释，不能只更新生成端。可信认证及docs20候选属于接口侧另一范围，不能当作本阶段字段变化。 当前收口口径见[阶段一统一目标版本交接](openspec/changes/complete-socai2-investigation-chain/stage1-problems-and-plan-20261114.md#10-阶段一稳定交接与统一目标版本)：本地验收完成，待统一发布；不开展旧版兼容层或双轨工程。

`null` 表示未记录或不可得；空数组表示对应集合为空；`0/false` 是有效值。未查、失败、成功查空分别显示，查空不证明安全。费用和 token 未知不能填零。已保存证据目录的条目数、威胁数与没有目录分别处理；威胁数为零不等于“已证明无威胁”。报告建议不得显示为已执行响应。

## 6 Case 与人工反馈操作

既有操作路径、入参及存储关系见 [Case/H 操作交接](openspec/changes/archive/2026-11-11-enable-case-human-http-flow/handoff.md)。按创建 Case 返回的 pending_run_id 显式启动首轮；人工任务通过 POST 创建、PUT 修订，使用返回的 row_version 和 current_revision_id；再次调查先 prepare 再 start。保存反馈不会自动启动调查。

人工采用与未完任务、后续调查及结案的规则见[AD01–AD06](docs/investigation/result-adoption-and-pending-work.md)。调查核心统一资格、未完工作确认、预览时效、幂等和判断历史；HTTP复用核心提供E21/E63/E64，两端服务及Swagger已同步。[后端调用指南](docs/integration/result-adoption-http.md)。采用只改变当前判断，不结束任务、Run或案件；无数据库迁移或告警字段变化。

人工结果来自 `tasks.current_revision_id → task_revisions`。每轮领取时冻结所选修订到输入工件 `task_revisions/source_materials`，正文、范围和 human_statement 归属保持，旧修订及历史输入不被覆盖。Result 的六项结论/校验/发现/问题/建议仍使用原字段合同。前次 Case/H 批次没有表列、枚举、告警交接字段或 HTTP DTO 变化。

前批本地完整路径及21原登录方式下的Case/H写读已通过；本轮可信方式另见新验收记录；产品页面交互仍需对应前端承接。[配置示例](deploy/aisoc21/case-http.env.example)说明功能写入连接，普通 API 的 DATABASE_URL 保持；不增加权限设计或确认环节。

Case基本管理现新增E44–E47：GET/PATCH `/cases/{case_id}/management`、POST `/close`与`/reopen`。局部修改省略保持；description/owner_id/severity为null清空，tags=[]清空。结案拦截running/unknown；未完人工任务须确认并填写理由，任务保留。重开恢复in_progress，不自动调查；当前结案字段清空，旧理由和前后值可从E17活动读取。所有写入带行版本及幂等键，已在本机/21各20次TCP及SQL验证。页面修改不在当前交接范围。见[本项验收](openspec/changes/archive/2026-11-12-manage-investigation-cases/validation.md)。

## 7 知识能力与当前交付范围

调查可按技术解释、取证指导、历史案例参考三个目的检索知识。资料原文和向量索引分别保存，查询后回读原文及校验内容；具体输入输出见[知识交接](docs/investigation/case-knowledge-handoff.md)、[历史卡片字段](docs/investigation/historical-alert-knowledge-handoff.md)。知识是参考材料，不是本案发生过某行为的证据。

历史固定流程已交付分诊后知识同步；本期第10步后台异步维护后置；候选已完成S01的A/I及Case首轮调度，这不代表知识异步维护已交付。知识维护属于独立组件能力，不在当前80项调查HTTP中；[组件指南](docs/integration/component-handoff-current.md)的旧主API入口须结合暂停状态读取，不能在本轮直接调用。

当前版本共有80个HTTP操作；E19提问、E20保存回答仍未实现，保留501合同。各页面AI对话（助手入口、提问/追问、会话历史、回答读取/保存）继续暂缓；告警分诊、事件诊断、Case调查及结果采用按既定范围推进。其他后置能力见[实施计划](docs/investigation/http-implementation-plan-20261112.md)，不扩展旧AiSOC功能。

API功能测试和模型结论质量分别验收：Case及告警/事件管理分别完成HTTP和数据库读回，真实完整调查的模型质量仍未通过。自动分析消费者未启用；显式调用后的内部流程由程序执行。当前部署、验收证据和后续工作以[PROGRESS](PROGRESS.md)为准，历史失败不改写；现有页面只用于测试。

### 三类列表完整导出

E54告警、E55事件、E56调查均为`GET /api/v1/socai2/{alerts|incidents|cases}/export`。输入沿用对应列表筛选和排序，加可选`columns`字段路径；不传分页参数。结果为全部命中的CSV附件、实际数量与观察时间，超过配置上限明确报错，不截断。三类公开列分别39/34/31项，逐列含义与默认列、空值/转义规则、下载例子见[HTTP指南](deliverables/investigation-validation-20261106/http-handoff/README.md#完整列表导出)。资产维护及模型流程不受影响。

### 事件顶部归并统计

E57 `GET /api/v1/socai2/incidents/grouping-summary`输入为可选告警来源和真实发生时间范围，返回总告警、已归并、未归并、去重事件及处理中事件数、压缩比例和观察时间。压缩以已归并告警为分母，空分母为null；顶部统计独立于表格关键词/负责人筛选。[逐字段说明及例子](deliverables/investigation-validation-20261106/http-handoff/README.md#事件归并统计)。

### Case普通评论

E58 `POST /cases/{case_id}/comments` 接收operation_key及非空白body，保存原文、实际作者和时间；E59 `GET` 同路径按limit/offset读取。前缀仍为`/api/v1/socai2`。同键同意图返回原评论，改意图409；E17可读活动。评论不自动作为已核实事实，任务、Run和案件判断保持；本批不含附件上传或下载。[输入输出及逐字段说明](deliverables/investigation-validation-20261106/http-handoff/README.md#case普通评论)。

### Case附件引用

附件是用户为案件补充的文件，例如工单PDF、截图或日志。业务后端负责上传/保存/下载；本服务用E60 `POST /cases/{case_id}/attachments`登记后端已保存的file_id、名称、类型、大小和可选哈希。E61 `GET`同路径分页查询，E62 `GET /cases/{case_id}/attachments/{attachment_id}`读取单项；E17查活动。返回id是关联ID，file_id用于业务后端下载。availability=managed_by_backend不表示本服务已探测文件存在或下载成功；附件不自动变成已核实事实或触发调查。[完整对接步骤](deliverables/investigation-validation-20261106/http-handoff/README.md#case附件引用)与[两端验收](openspec/changes/archive/2026-11-13-link-case-attachments/validation.md)已同步。
