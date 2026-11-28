# 告警第 4 步：管理、人工反馈与活动读回支撑

2026-11-24。沿 [第 4 步工作单与用户确认规则](alert-chain-acceptance-plan-20261124.md#用户确认后的规则与执行步骤)恢复 F23-01、F03-04 及对应活动读取。用户已明确取消批量标签、告警最后成功保存为准、失败不自动补交；本次按该范围修改告警行为，不重复索要授权。SpiritHub 负责表单和浏览器，后端负责最小实现及隔离真实保存。账号/资产保持停止，复用 Q04 目录；不改正式告警、不调用模型、不部署、提交或推送，事件/Case 和独立评论等不扩展。

## 原有效证据及本步缺口

| 已有来源 | 可复用结论 / 限制 |
| --- | --- |
| `spirithub-alert-owners-20261123-01` 与 Q04 正式回执 | 原核准人员分配、改派、版本递增以及同 ID 详情、负责人列表和活动读回通过。不把其负责人检查扩大为标签/全部状态分支或多页最新活动已验。 |
| `attck-display-20261123-01` 及 [ATT&CK 展示/冻结说明](alert-attck-mappings-20261123.md) | 本机隔离真实保存已核改派及四种人工判定，原 AI、材料、冻结快照与 Run 关联保持；当时使用受控模型替身，不能称正式模型或本轮新增执行。 |
| `deploy/http-service/verify_subject_management.py` | 有历史闭环方法，涵盖关闭/重开、标签、批量幂等/冲突及原结果保持。脚本同时涉及事件/Case，本步不整体执行，也不把脚本存在当本轮通过。 |
| 本步须补 | 单条标签替换/清空/省略保持；旧版本的后一次明确字段成功保存；批量仅选中、逐条反馈与状态联动；batch tags 拒绝无写；同 ID 详情、筛选列表和最新活动首屏/必要两页读回。原旧版本冲突证据不代表此次规则。 |

## 最小环境与实施顺序

1. **只读环境预检及活动排序判因。** 复用 `.local/validation/e54-selection-candidate-20261123-01/runtime.json` 的本机隔离 PostgreSQL、其既有 `http-env.json`，及 `q04-owner-candidate-20261123-01` 的租户、操作者、目录 profile。核库名、loopback 地址、既有主体/目录和来源文件，不重建库、不修改原夹具。对既有隔离告警活动用 `limit=1` 与数据库按实际时间的最新记录对照；先判定 `order_by(id)` 是否阻断最新读回。若确认，先在本文补最小排序修正/合同影响并交组织者判断，不直接扩改。
2. **独立隔离批次和候选入口。** 在同一已确认隔离库的新批次创建仅用于本步的合成告警：两条后端流程代表、一条未选中对照，以及两条留给前端直接保存的代表。来源按 profile 使用 `lyc` 前缀。不新建账号/人员投影，不产生事件/Case。沿现有数据/阶段保存助手准备明确标为夹具的材料、受控已存分诊及冻结快照；不调用模型或自动执行器。另起 loopback HTTP 进程，读写同一隔离库，加载现有 Q04 身份与目录配置；不切换 21。
3. **直接管理保存验证。** 单条标签整体替换、[] 清空、省略保持；两次明确保存使用不同操作键，后次携旧版本覆盖所改字段，其他字段从最新行保留。复用既有仅改派/关闭及冻结证据，按本段必要操作核同 ID 详情、筛选列表、活动和 PG，不新增并发矩阵。
4. **直接反馈与批量验证。** 两条明确勾选告警用同一判定/理由，各新增反馈；核既有关单/重开、逐项 ID/feedback_id/activity_id、未选中不变及原评估保持。批量管理拒绝显式 tags，包括 []/null，参数拒绝不产生主体或活动写入。行版本继续递增，旧请求版本不再作为告警拒绝条件。既有回执字段保留，前端成功不展示 changed_count；失败不自动重试或补交。
5. **前端接线与交接。** 提供私有 candidate profile、真实 HTTP 入口、限定测试 ID、现有目录 ID 和当前版本。前端保存与刷新必须全部指向该隔离入口，不能让未接管写路由回落到正式平台。候选接线由 SpiritHub 执行。后端完成直接验收后交来源、结果和未验边界，等待组织者独立复核。

原活动判因与启动回执保留在 `.local/validation/alert-management-feedback-support-20261124-01/`。本次新规则保存使用独立 `alert-management-feedback-support-20261124-02/`，读写仍限原本机隔离 PG，新候选加载本次源码。所有地址、端口、库/租户、页长和时限由显式 profile 提供；凭据、业务值和原始回执只留私有目录。实施前严格校验，失败不自动换键补交。

## 保存合同与活动排序判定

### 现行请求和保存语义

路径以 `/api/v1/socai2` 为前缀。单条管理 `PATCH /alerts/{id}/management`，单条反馈 `POST /alerts/{id}/feedback`；批量分别为 `POST /alerts/management-batch`、`POST /alerts/feedback-batch`。单条带 `operation_key/expected_row_version`，批量带同一 `operation_key` 及 `items[].id/expected_row_version`，共同字段分别放在 `changes` 或 `feedback` 中。批量上限来自管理配置，不能从当前页条数推断。

| 字段/行为 | 实际口径 |
| --- | --- |
| `owner_id` | 省略保持，null 取消分配；指定同租户已有人员。仅改负责人时可以省略理由，处理状态和人工判定保持原值。 |
| `tags` | 仅单条告警完整集合替换；省略保持，[] 清空，null 拒绝；原 50 项/128 字符、非空白不重复限制保持。告警批量管理任何显式 tags 均 422 且无写，Schema 不再列为批量可写字段。事件合同保持。 |
| `handling_status` | new/in_progress/completed；显式 null 拒绝。直接提交 completed 必须有非空白 reason；关闭/重开更新对应时间和操作者，保留原 disposition。 |
| 人工反馈 | `disposition` 与非空白 `reason` 必填，理由原文保存。false_positive/benign 使非 completed 告警关闭；已 completed 改 true_positive/needs_review 则恢复 in_progress，清关闭字段并记录重开时间；其他状态保持。每次新增 human_feedback，不覆盖原 triage。 |
| 版本与操作键 | 按 UUID 排序锁全部最新目标，再计算并保存明确字段及既有联动。告警 expected_row_version 保留正整数格式但不作为过期拒绝条件；后成功保存的明确字段生效，未提交字段保持最新值。事件/Case 原规则不改。同键同意图仍可读原回执，同键不同意图仍冲突；前端请求失败后结束，不自动重试、补交或刷新版本再提交。 |
| 单条/批量回执 | 单条为 `kind/facts/changed/feedback_id/activity_id`；批量为 `operation_key/items/changed_count`，items 按 UUID 排序，不能按用户选择顺序对应。管理的 feedback_id 为 null；反馈为新 ID。changed_count 统计 changed=true，不是选择条数。 |
| 无变化与活动 | 管理仅在实际字段变化时推进主体行版本；合法但无实际变化的操作仍写活动/目标及幂等回执。反馈新增记录与最新指针，不能按相同判定当作无变化。批量共用 activity_id，各告警通过 matching_targets 读取自身 before/after/result_state。 |

只提交 reason 不是合法管理变更；管理附言保存在活动，不能据此声称独立评论功能已交付。原 A 结果、材料和冻结工件不由这些写操作更新；人工作业可能改变当前输入比较的新鲜度，这与旧工件不变分开核对。

依据：[请求/回执 DTO](../../../services/api/app/socai2/subject_management_contracts.py)、[原子保存服务](../../../services/api/app/socai2/subject_management.py)、[既有路由](../../../services/api/investigation_http/external_routes/subject_management.py)。

### 已确认的最新活动读回阻断（最小修正已获准，本段复验）

复用原 Q04 隔离告警和既有活动，没有新增写入。`preflight-04/` 已实际读取 `records/activities?limit=1`，并用同库、同租户、同告警的只读 SQL 对照：活动数超过该页长，HTTP 首项等于 UUID 升序首项，但不等于 `occurred_at DESC, id DESC` 的最新活动。现有页面只排序已加载记录，不能把未取到的最新操作补入首屏；因此本步不能据全量 ID 排序或成功提示宣称“保存后刷新可见最新操作”。

组织者独立核对后已接受最小修正：仅 `PageReader.records` 的告警 `activities` 分区按 `occurred_at DESC, id DESC` 排序后应用现有 offset/limit。时间相同用 ID 作为确定性次序。保持 RecordPage 字段、分页参数/总数、活动目标关联、告警行版本、所有保存规则和其他分区行为；不新增索引、游标或通用时间线框架。影响仅为该分区分页返回顺序，原按 ID 的旧 offset 页位置不再表示同一条活动。

已在同一 change 的 `alert-incident-management` 规格增量补“告警活动按实际时间倒序分页”的直接场景，严格校验通过后完成该排序分支修改。直接复验仍须复用同一既有告警 `limit=1` 首项与真实最新活动比较，再用必要的前后两页核无重复、总数/next_offset 和 matching_targets 保持；后续本批真实管理/反馈保存再核最新活动首屏读回。用户插入资产匹配优先项时，这些修复后复验尚未执行，不记已通过。

首次探针错误地要求既有 PG 数据目录位于批次目录，实际原 profile 使用受控临时目录；第二次受到沙箱连接限制，第三次误用 TCP 管理连接而认证失败。原三次失败保留，修正为原设施既有 Unix socket 后第四次完整只读预检通过。未修改数据库认证或账号配置。

## 实际结果与候选交接

用户要求先补资产并核接口后，本步停在可恢复边界：新隔离候选已启动，`candidate-start-checks.json` 的启动检查通过，保存的源码指纹与当前 `page_reader.py` 一致；修前源码指纹与第 3 步交接一致。原候选保持。进程状态的本机沙箱探针被限制，启动及 OpenAPI 回执仍完整保留；没有因该探针重新启动服务。

### 2026-11-24 接续：隔离 PostgreSQL 与实际 HTTP 保存读回

实施前 OpenSpec 严格校验通过。接续预检通过原 Unix socket 查实际隔离 PostgreSQL，并核同库 Q04 告警、候选进程监听、运行 OpenAPI、四个写入路由和人员目录。原 02 配置对应来源的告警、反馈及活动均为零。首次预检受沙箱限制，获准后只读复核通过。候选已加载告警批量专用 Schema 及活动排序源码。当时的隔离 writer 已具备告警更新及活动写入，缺反馈表 INSERT。本步给该隔离角色补该表的 INSERT，沿原 reader/writer、租户、人员目录和 HTTP 入口验证。

复用原 02 候选，在已核隔离库种入同批五条合成告警，后端两条、页面两条及一条未勾选对照。合成分诊使用已有持久化助手保存固定模板和冻结材料。首个夹具原件引用缺字段路径，保存被拒绝，管理 HTTP 尚未发送。接续先读回五条已存材料及唯一未发布 Run，补 `source_path` 后完成原 Run 并保存其余夹具。两次尝试各自保留，实际新模型调用为零。

后端直接验证通过。实际 27 次隔离 HTTP 请求包含 6 次成功保存及 1 次批量标签拒绝。核对单条标签替换、清空和省略，无理由负责人修改的旧版本请求成功并保留这期间的最新标签，批量改派对已相同的条目返回成功且只变更需改派的一项。勾选两条同判定和理由，分别保存反馈，关闭后再恢复处理中。最终按 HTTP 返回的同一 ID 对照数据库、列表筛选、详情、活动首项及目标前后值。四条独立反馈、六条活动、未勾选对照、保留给页面的两条记录、原分诊、材料与冻结工件均已核对。来源与行值仅在隔离机内比较。

接续工作目录为 `.local/validation/alert-management-feedback-execution-20261124-01/`。`preflight-02/verification.json` 为隔离预检，`backend-01/` 保留夹具首次失败，`backend-02/verification.json`、`backend-02/http-requests/` 和该目录的前后 PostgreSQL 快照供复核。

### 21 联调环境切换

负责人在本机后端直接验收后指定本步剩余联调在 21 完成。本机五条夹具、六条保存活动、四条人工反馈及新增的隔离 writer INSERT 授权均按实际状态保留。两条预留页面告警仍未执行管理或反馈，本机专用写入代理和页面测试均未启动。后续 8181 仅提供页面，管理、反馈及配套读取通过 21 的 SpiritHub 平台和调查 HTTP 使用 21 实际库存储。[页面环境接续](alert-list-detail-closeout-20261124.md#第-4-步21-联调环境)

#### 实际预检与发布范围

`sting-infra21` 的 Windows `2221` 转发本次拒绝连接，`sting-infra21-direct` 从 Mac 直连超时。复用两边既有 SSH 配置，经 `sting-win57` 跳板到 `sting-infra21-direct` 成功。首次远端探针使用的主机环回不是该发布端口的绑定地址；按在运容器实际 HostIp 读回后通过。复用本机 28084 仅获取了调查 HTTP 的运行 Schema。28081 的根路径返回平台前端 HTML，平台 API 的实际合同和源码从 21 的平台容器内读取。

| 范围 | 2026-11-24 在运结论 |
| --- | --- |
| 调查 HTTP | 容器 `socai2-http-c173-q04-release-20261123-01`，运行版本同名，镜像 ID 前缀 `5ef0f0bac602`。同版 `readyz`、OpenAPI、Q04 均为 200，83 个业务操作，四个告警管理／反馈写入及列表、详情、活动均登记。运行源码和 Schema 仍采用告警旧版本拒绝、批量管理共用含标签 Schema、活动按 ID 分页。仅改负责人可省略理由已存在。 |
| 调查 PostgreSQL | 读写 profile 同地址同库，实际写连接在 `aisoc`。配置的调查操作者启用，告警 UPDATE、反馈 INSERT、活动及目标 INSERT 均具备。21 所需权限与本机隔离库的初始权限不同，本轮 21 发布无需追加授权或迁移。 |
| SpiritHub API | `spirithub-api-1` 实际运行 `spirithub-backend:trusted-c173-20261123-01`。平台 Schema 和固定可信上游均读回 200，上游 release 与 18024 直读一致，未带会话的列表返回 401。E48–E51 及配套列表、详情、活动和 Q04 均已登记。已核既有浏览器操作者仍有平台桥接映射，Q04 仍有两名独立负责人选项。平台映射的租户配置与调查服务自己的业务上下文分别固定，浏览器操作与实际会话待联验。 |

发布候选 `c173-alert-management-20261124-01` 以在运镜像 ID 和实际文件摘要为基线。三份源文件的基线逐字节对上，补丁仅含下表变更。已在此基线上应用补丁，三个组包文件均通过 Python 编译检查。现网与工作树的 `external_routes/subject_management.py` 摘要一致，复用现有路由。

| 调查 HTTP 文件 | 发布差异 |
| --- | --- |
| `app/socai2/subject_management.py` | 仅告警锁定最新行后应用明确字段，旧的客户端行版本继续接受。事件沿原版本检查。 |
| `app/socai2/subject_management_contracts.py` | 告警单条及批量的版本说明同步为新语义。告警批量管理使用专用变更合同，拒绝显式 `tags`，告警单条标签和事件合同保持既有口径。 |
| `app/socai2/page_reader.py` | 仅告警 `activities` 按 `occurred_at DESC, id DESC` 后分页。组包保留现网 Q04 和当时已发布的 ATT&CK 读取条件。 |

运行更新目标仅为独立调查 HTTP。沿 Q04 的离线镜像和独立容器交付方式，以当前发布的应用内容、配置及挂载生成候选，只替换上述三份程序并标记新的 HTTP release。切换时保留原 Q04 容器和镜像作回退，核绑定端口、实际源码摘要、同库配置、83 个业务操作、三处合同差异和既有 Q04。平台业务转发已具备所需路径及固定上游，其独立文档声明与新 HTTP Schema 的同步由平台对接接续确认。Swagger 也有自己的发布版本，联验依据实际 HTTP 的 OpenAPI。

21 正常操作联验只使用此前确认的 OCSF 数据组，经 Kafka 发布者送入并保存后按同源告警 ID 接续。调查核心执行交付对应来源、持久化告警 ID 及原材料和 A 分诊的保存关系。8181 沿既定操作验收单条标签、无理由负责人修改及所选反馈，本会话核对同一 ID 的 21 PostgreSQL、HTTP 及活动。既有定向拒绝、失败无补交及跨页选择证据按原范围复用。[指定数据及发送职责](es-ocsf-test-chain-20261124.md#当前告警验收的数据来源与发送职责)

工程回执在 `.local/validation/alert-management-feedback-execution-20261124-01/remote-preflight-jump-02.json`。审查包清单为同目录 `review-21/manifest.json`，逐项差异为 `http-step4-review.patch`。其中包含在运基线、新文件和补丁摘要；私有映射、账户身份和业务回执不进入审查包。

#### 21 独立调查 HTTP 已切换并读回

[三文件独立审查](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/alert-management-21-package-review.json) 11 项通过。切换前重新核对 Q04 的在运容器、镜像、三个旧源码摘要及不变的管理路由。离线组包对完整应用逐文件比对，差异仅为三份获审文件；候选 OpenAPI 的路由及非本步 Schema 与基线一致。首次切换前检查把 Q04 每次生成的 `observed_at` 纳入目录相等判断，停在创建候选前。只读复核确认原容器继续服务、其他容器一致，之后按目录内容与分页字段核对，并分别校验两次观察时间格式。

`c173-alert-management-20261124-01` 已在 21:18024 运行。独立容器 `socai2-http-c173-alert-management-20261124-01`，容器 ID 前缀 `53257c6ed679`，镜像摘要前缀 `fe1f65c38579`。实际 `/readyz`、`/openapi.json`、`/api/v1/socai2/people` 返回 200。运行时源码摘要逐项对上，83 个业务操作及告警写合同通过；Q04、运行配置及其他运行容器核对保持。原 Q04 容器停止留作回退。`deploy-21-prepare-01.json`、`deploy-21-cutover-01.json`、`deploy-21-inspect-01.json` 与最终 `deploy-21-cutover-02.json` 在同一受控工作目录。[部署工程回执](../../../docs/operations/evidence/alert-management-feedback-21-20261124-01/deployment.json)

#### 21 合成夹具的创建和撤回记录

按原安排，在已发布 HTTP 使用的 `aisoc.socai2`，沿现有 writer 和业务上下文一次性保存了三条独立 `lyc` 合成告警。其中两条原拟供选择，一条原拟作对照。每条绑定当前材料、固定模板分诊及其冻结输入，三条在同一事务保存。告警、分诊、材料和冻结工件曾经在 PostgreSQL 与 21 HTTP 逐项读回一致。该回执只记录创建时的基线。分析任务、模型调用及事件／Case 关联均为零。[原夹具基线](../../../docs/operations/evidence/alert-management-feedback-21-20261124-01/fixture-baseline.json)

负责人改用指定 OCSF Kafka 入站链后，三条夹具及其选择器从本轮验收撤回。撤回时三条仍存在，行版本与创建后快照一致，反馈指针、人工反馈行、直接活动和活动目标均为零。前端确认本批管理和反馈写入为零。三条夹具已在后续授权清理中删除。21 原始基线和选择器保存在本发布目录的 `private/step4-fixture/` 及本机受控归档。[撤回时的只读回执](../../../docs/operations/evidence/alert-management-feedback-21-20261124-01/fixture-exclusion.json)

#### 指定 OCSF 首条的 21 只读基线

从原首段归档取 ACK、湖原文确认、成功交付回执和裸 OCSF。先在本机核归档与冻结文件逐字节一致、ACK 只命中一条冻结原件、UID 和湖交付证明一致。沿首段已存告警 ID，仅查 21 当前调查租户中该 ID 的不可变接收回执、告警、材料及 A Run。接收回执记录 Kafka 入站命名空间，告警事实使用 Fusion 存储命名空间，两者分别按各自字段核对。PG 原件及 HTTP `content_text` 均与冻结行逐字节一致，`content_json.ocsf_json` 同源一致。

同一告警在 21 当前 `c173-alert-management-20261124-01` 的 8 次 GET 均为 200，包含同 ID 列表、详情、原材料、来源、当前 A 分诊、冻结输入及保存前活动快照。A 的 Run、分诊和材料 ID 对上当前 PG。首份读回脚本语法检查及随后错误比较两个命名空间的尝试均保留，修正后仍只核原告警 ID，业务写请求为零。[首条工程回执](../../../docs/operations/evidence/alert-management-feedback-21-20261124-01/first-kafka-source-http-readback.json)

8181 首条只读选择器在 `.local/validation/alert-kafka-http-first-20261124-01/page-selector-private.json`，包含固定告警、材料、A Run、查询和保存前版本。同目录保留 PG、HTTP 与 ACK 绑定的受控回执。核心随后交齐本组 10 条告警，统筹已按冻结来源和同源读取复核。[组交接独立复核](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/approved-ocsf-group-handoff-review.json)

#### 21 历史测试数据清理和 8181 回验

按负责人授权和统筹独立确认的范围，三个截图 ID 逐一对上原夹具创建记录，26 条旧分页告警和 1 条旧资产告警逐一对上原 Kafka ACK、归档原文及 PostgreSQL 接收回执。清理集合与指定 10 条告警互斥，关联事件和 Case 的已存成员均属于待删集合。两件测试资产由原创建回执确认，其中一件曾动态匹配当前告警，持久化资产引用和外部外键引用均为零。[身份与保护复核](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/historical-test-cleanup-protection-review.json)

21 PostgreSQL 在写入锁内重核外键、分析主体映射和精确主键，备份并读回候选行后提交删除。共删除 30 条告警、27 个专属事件、1 个专属 Case、2 件测试资产及各自专属记录，共 29 张表 1,542 行。不可变回执和循环外键维护设置仅限该事务连接，并在校验保留记录和提交前恢复。目标主键读回为零，保留记录指纹在事务内一致。正式调查 HTTP 上旧 30 条详情全部返回 404，当前 10 条详情及材料全部返回 200，材料正文摘要一致。[PostgreSQL 和 HTTP 工程回执](../../../docs/operations/evidence/alert-management-feedback-21-20261124-01/historical-test-cleanup-postgres.json) · [独立复核](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/historical-test-cleanup-pg-review.json)

ClickHouse 按租户及 Kafka 坐标、来源和湖引用备份并删除 27 条历史湖记录，完成后按同一筛选读回为零。当前 10 条告警湖记录及独立湖中的 52 条上下文均核对冻结原件，两个当前 Kafka 主题可读取。Fusion Redis 对四类各 27 个精确候选键核归属，历史专属存量为零。当前调度器 Redis 以已删的 56 个任务逐一核对正常队列、待处理队列和运行提示，四类引用均为零。Redis 实际删除为零。历史 Kafka 消息、原执行回执和离线原件归档保留。[湖和 Redis 工程回执](../../../docs/operations/evidence/alert-management-feedback-21-20261124-01/historical-test-cleanup-stores.json) · [跨存储独立复核](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/historical-test-cleanup-storage-review.json)

8181 实际刷新及独立复核通过。列表精确显示指定 10 条，旧 30 条均未出现，三条截图夹具详情提示未找到。代表告警的原文、材料、时间和指定 A Run 对上正式读取，清理回验期间页面业务写入为零。[页面回验](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/historical-test-cleanup-browser-review.json)

#### 21 指定 OCSF 管理操作的保存前基线

负责人要求继续后，按最终核心映射顺序固定前两条供操作，第三条为未勾选对照。正式调查 HTTP 列表的 10 条身份与最终映射一致。前三条通过 18 次 GET 和同一租户的只读 PostgreSQL 查询，核对管理字段和行版本、当前人工反馈、最新活动、原始材料摘要、已完成的 A Run 及其冻结输入。基线选择器另记录该租户可用于改派的现有人员。[基线独立复核](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/alert-management-ocsf-baseline-review.json)

受控选择器和基线在 `.local/validation/alert-management-ocsf-21-20261124-01/`，已经统筹交接给前端。前端从现有 8181 会话逐次写第一条，调查 HTTP 以实际活动的 `detail.request_key`、`operation_receipt` 和 PostgreSQL 对应行核对，按明确字段及表单版本重算保存意图摘要。浏览器证据覆盖页面操作、确认反馈和刷新读回，保存请求的信息由活动回执和摘要验证。

8181 已实际保存标签替换和无理由负责人修改，两笔均通过统筹独审。两笔各有一个正式活动及对应 PostgreSQL 回执，行版本各推进一次。负责人来自现有人选目录，请求意图匹配新表单的当前版本及单独的 `owner_id`。原标签、状态和人工判定保持，另外两条告警的管理事实和活动保持。此次实际交互使用当前版本，旧版本正例仍缺实际页面证据。调查 HTTP 核验业务写入为零。[两笔保存回执](../../../docs/operations/evidence/alert-management-feedback-21-20261124-01/ocsf-single-management-two-saves.json) · [标签独审](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/alert-management-ocsf-first-save-review.json) · [负责人独审](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/alert-management-ocsf-owner-save-review.json)

标签和负责人保存各自的首次页面取证与补充只读回执均保留。首次后台核对整份分诊投影摘要失败，定向复核确认差异仅在 `triage.freshness` 和 `triage.valid_for_current_input`。详情按完整输入快照重算两字段，原分诊评估、A Run、材料和冻结输入对上保存前指纹。同一告警的正式材料及冻结输入接口均返回 200。[受控回执索引](../../../docs/operations/evidence/alert-management-feedback-21-20261124-01/ocsf-single-management-two-saves.json)

8181 原文和解释引用报错定位到候选代理依赖的本机 `28084` SSH 隧道断开。原转发恢复后，前端对指定组代表告警的原文、解释引用和固定 A 入口完成只读回验，统筹独审通过。[材料及 A 页面恢复独审](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/alert-material-restored-page-independent-review.json)

#### 三笔单条管理和两笔批量反馈收口

恢复材料读取后，8181 在同一操作告警显式提交一次 `tags: []`。按第三笔活动的实际操作键只读核对 PostgreSQL 和 E30，页面输入和保存意图摘要一致，标签清空且行版本只推进一次。负责人、状态、人工判定和反馈、材料及固定 A 结果保持，单条管理期间另外两条告警的管理事实和活动一致。读取回执留在同一受控目录的 `readback-04-private.json` 和 `readback-04-verification.json`。标签替换、无理由更换负责人和标签清空三笔均已独审通过。[单条管理收口独审](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/alert-management-ocsf-single-save-closeout.json)

8181 明确勾选两条操作告警，以相同的 `false_positive` 和同一理由提交一次。统筹核对实际保存意图、每条独立反馈、各自的关闭状态和最新 E30 活动。未勾选对照及原材料、原分诊和冻结输入通过保留核对。受控快照为 `root-feedback-readback-01-private.json`，首次比对的时间显示格式和活动投影字段差异按原回执留存。[批量误报独审](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/alert-management-ocsf-batch-close-review-02.json)

跳板到 21 的连接阻断及暂停时的状态保留在原检查点。11 月 25 日恢复本机原有两条转发，统筹复核了连接及 `28081` 的实际平台目标，均通过。[原检查点](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/alert-management-ocsf-step4-current-checkpoint.json) · [转发恢复独审](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/alert-tunnels-restored-independent-review-20261125.json) · [平台目标独审](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/alert-platform-forward-target-independent-review-20261125.json)

连接恢复后，8181 对原两条告警一次提交 `needs_review`，沿用同一功能联验理由。统筹用 6 次 HTTP GET 和 PostgreSQL、E30 只读回执核对实际操作键、页面提交字段及保存意图摘要，20 项检查通过。两条告警各新增一条独立反馈，均由已关闭恢复处理中。两次批量共保存四条独立反馈，误报历史、负责人、标签、原材料、原 A 分诊和冻结输入均核对保留，第三条未勾选对照与初始基线一致。末笔受控快照为 `root-feedback-readback-02-private.json`。[批量重开独审](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/alert-management-ocsf-batch-reopen-review.json)

第 4 步正常管理和人工反馈流程已通过并交负责人查看。负责人保存使用当前表单版本，旧版本表单的实际页面提交仍未覆盖。选择器、列表和活动的负责人名称可读性问题已登记后置。两次人工判定用于功能联验。[第 4 步独立收口](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/alert-management-ocsf-step4-closeout.json) · [负责人名称显示问题](../../../docs/investigation/current-issues.md#待整理告警负责人名称显示)
