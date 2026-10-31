## Context

这是基于 `5b95138` 的设计；用户随后要求“推进执行”，B1–B3及T6已本地实现和直接验证，实际交付状态见[执行记录](../../../docs/investigation/audit-fixes-implementation-20261031.md)。审计编号、代码位置及反例见[详细审计](../../../docs/investigation/design-implementation-audit-20261031.md)。API v2 常驻 factory、Case 同步模型/Tool 循环及现有 ledger 继续使用；旧 fixed/program 不改。

当前本地已有追加压缩、required_tools、query_status；真实 r1 批次没有这些改动。新增原始材料会改变模型输入，因此原 Office `16786 < 17018` 只保留为旧离线重建事实，不能直接成为本设计的预算验收结果。

## Goals / Non-Goals

目标是修正 A01/A02 的正常功能路径，并以最小取材合同解决 D01：来源本来存在的正文能被明确保存、有限提供给模型并追溯；来源没有、未保留、未送模型分别表达。

本批不增加 Tool 种类、厂商 HTTP、F5/自动建案、首次 worker 启用、JWT/RBAC 专项、统一恢复/预算框架、全链防篡改系统或新前端。原 4 模型/4 Tool/24000 tokens、单次输出 3000、主循环 120 秒保持。材料较多时仍可诚实停止/partial，不提限额掩盖问题。

## Decisions

### 1. A01：固定进程类语义，并阻止跨合同复用

保留 Tool 名称及 `hostname/limit` 参数，描述改为“进程活动记录”；SQL 使用 `class_uid = 1007 AND process_name != ''`。仓库已有 Process Activity=1007 的数据/测试口径；服务端 tenant、主机、半开窗口和 limit+1 规则不变。

保存返回增加 `class_uid`、`activity_id`、`action`、`outcome`。只表达实际存储值，缺失/空/未知不能解释为启动成功，也不根据一个进程名推导父子链。接线验证发现现有LLM合同禁止原始OCSF编号：模型行使用 `event_kind=process_activity`、原 action/outcome，显式列出省略的 class_uid/activity_id；原编号仍在同一证据行，不把未知活动映射为启动，也不关闭输入合同。

新进程 Tool 证据带 `query_contract: "case.process_activity.v2"`。历史复用除原材料/参数条件外，必须核对这个精确版本；缺少标记的旧结果或其他版本不复用，执行新查询。产品快照仍不复用，网络工具语义不变。本次不改 Run profile 或旧结果；旧 GET 照旧返回。

固定反例：同租户/主机/窗口内一条 1007 进程活动、一条带相同进程名的 4001 网络记录及一条其他类别记录。进程结果只能包含 1007；网络结果仍包含 4001。当前只返回预设行的湖替身不能单独证明 SQL 类型谓词正确，直接用例须同时核实际查询条件及保存/模型视图的类别字段。

### 2. A02：在同一条概况行锁下，先确定权限，再调用模型

处理顺序固定为：

1. 原认证及 `alerts:write/read` 校验，读取基础事件 overview；若请求 include=true，沿原逻辑要求 cases:read。
2. 在原事务中创建或取得 summary 行并锁定，读取锁内最新正文与 source_refs。若**已有非空旧正文且来源 include_investigations=true**，也先要求 cases:read。拒绝发生在 last_attempt 更新和模型调用之前，0 模型/0 新尝试/0 成本写入。
3. 保留基础 overview；按本次请求及旧正文所需模式，有需要才构造关联 Case overview。每个来源视图连同自己的 source_updated_at 保留，不能只删除 investigations 字段而沿用另一模式的时间戳。
4. 使用请求模式生成新概况，沿原锁完成正文或最后尝试更新。复用已锁 record，不在模型后重新读取另一份旧记录或再检查会导致回滚的回退权限。
5. 成功返回新正文及新模式；失败有旧正文时保留原正文、generated_at、source_refs、source_fingerprint，并按**旧模式当前来源**计算 stale；失败无旧正文保持 not_generated/stale=null。
6. 已准入尝试沿原事务提交 last_attempt/error/可得 usage 和可写入的成本记录。未知 usage 仍未知；不承诺 DB 提交失败自动恢复，不新增费用补偿系统。

| 本次模式 | 旧正文模式 | 额外 cases:read | 成功返回 | 失败返回 |
| --- | --- | --- | --- | --- |
| 基础 | 无/基础 | 不要求 | 新基础正文/来源 | 旧基础来源；无旧文则未生成 |
| 基础 | Case | 调用模型前要求 | 新基础正文/来源 | 旧 Case 正文及当前 Case 来源视图 |
| Case | 无/基础 | 调用模型前要求 | 新 Case 正文/来源 | 旧基础来源；无旧文则未生成 |
| Case | Case | 调用模型前要求 | 新 Case 正文/来源 | 旧 Case 正文及当前 Case 来源视图 |

这会收紧“无 cases:read 用户刷新已有 Case 概况”的行为，明确采用前置 403；不采用调用模型后再隐藏旧文/拒绝的办法。普通 GET 的来源模式和权限规则保持，与失败刷新在来源未变时得到相同 stale。

首次 worker 仍只做其基础概况首次尝试；已有 last_attempt 的跳过规则保持，不赋予 worker 新 Case 读取行为。实现可提取小型锁内生成/返回组装函数，不新增服务或权限抽象层。

### 3. D01：有界冻结正文，单独构建模型视图

请求接口不增加必填字段。新 Run 的 context 增加 `source_material_schema: "case.source-material.v1"`、`case_material.description`；选定 A 证据的 data 增加 `source_material.description/raw_event`。均来自本次已核 tenant/Case/Alert 读取，不根据标题补造原始字段，不新增产品请求。

每个来源字段统一保存下列最小形状：

| 字段 | 目标含义 |
| --- | --- |
| source_path | 明确为 Case.description、Alert.description 或 Alert.raw_event，连同现有对象 ID 定位 |
| status | missing / empty / present；null 为 missing，空文本或空 JSON 容器为 empty |
| encoding | utf8 或 canonical_json_utf8 |
| sha256 / original_bytes | 截断前完整字段的指纹与字节数；missing 时为 null/0 |
| retained_bytes / text | 本 Run 实际保留的 UTF-8 文本；missing 为 0/null |
| truncated / omission_reason | 是否少于来源全文；理由为 field_limit/run_limit，未省略为 null |
| model_blocked | 完整来源单独经现有模型输入合同检查的结果；不是正文缺失或未冻结 |

raw_event 使用排序键、紧凑分隔符、非 ASCII 转义的确定 JSON 编码；其 hash 是**当前 JSON 数据的 canonical hash**，不是厂商原始网络包 hash。截断 JSON 只当文本保存，不能再称完整可解析 JSON。空字段有正常编码/hash，missing 不伪造内容。描述保持原文，不改写审批、父子关系或语气。

规划固定以下上限作为本版本政策，实施时以常量记录：

| 层次 | 上限与顺序 |
| --- | --- |
| 单字段冻结 | Case.description 4 KiB；每 Alert.description 4 KiB，raw_event 16 KiB |
| 全 Run 新增来源正文冻结 | 合计 128 KiB；先 Case，再按现有 event_time/id 顺序逐 Alert 的 description、raw_event；超限仍记录字段 hash/长度和省略原因 |
| 模型新增来源正文 | 合计最多 8 KiB；Case 最多 1 KiB，其余字节按可读成员均分，每成员 description 优先最多 1 KiB、raw_event 最多 2 KiB；未用份额可保持不用，避免复杂重分配 |

所有字节裁剪保完整 UTF-8 字符。8 KiB 仅为新增正文限额，元数据仍计入原整体输入预检；不声称模型请求总量只有 8 KiB，也不保证任何规模 Case 都能在 24000 内完成。

模型视图复制冻结材料后裁剪，记录各字段 `model_retained_bytes`、`model_truncated` 和 `model_omission_reason`，不覆盖冻结 text/retained_bytes。完整来源在嵌套/裁剪前单独经过既有LLM合同；被拒字段不送模型，原文仍按冻结上限保存，模型原因明确为 `llm_input_contract`。省略说明明确是来源字段省略、模型视图省略还是旧 saved_analysis 截断。完整字段/hash元数据留在工件，模型只带状态、保留文本与模型省略元数据；原始材料中的指令当数据，不参与授权或 Tool 参数范围。

当前开始步骤及结果工件可容纳上述字段；以现有结果/证据读取交付，不新建表、原件下载接口或通用材料存储系统。Case material 也须在新 result 中保留，不能只放热内存或仅指向当前 Case。超出冻结上限的全文**未被本 Run 保存**，hash 和当前来源链接不能冒充历史全文可恢复。

Case.description 属于案件背景，不新造证据编号，也不单独支持 finding；Alert 正文沿其 A 编号定位并标明来源陈述。材料补齐不改变 T/H 的历史判断身份或结论引用规则。

Office 固定样例使用已有原件：description 中父子 PID、raw_event 中 full_log/approval_status 应在上限内保留并进入模型视图，仍标记为“来源陈述”，不直接当独立证实的攻击或授权结论。

### 4. 指纹、追加与旧 Run 兼容

新 source_hash/material_hash 包含材料 schema 和各字段截断前的 hash/状态/长度。即使只改 raw_event 的裁剪尾部，新材料指纹也变化；新 Run 不复用此前查询。问题是否纳入两个 hash 的既有区别保持。

旧 Run 缺新 schema，可作为 previous_run_id 的 H1 历史判断并照常读取，但其材料 hash 不能满足新材料复用条件。H1 不改写成当前证据；新进程查询还需第 1 节 query_contract。保持 `case_analysis.v1` 识别及现有同 key intent 编码；原 operation_key 重复调用只读原结果，不升级、不补查；需要新材料用新 key。

新材料分别出现在冻结视图和已记录模型请求。组合核对显示只沿用旧压缩会使Office纠错需19650（假定旧缓存可用时18496），超过剩余17018。为保留新增来源，H1模型报告保留summary/findings/counterevidence/gaps；成员判断、关系、未决问题、建议、时间线和覆盖表只在模型视图省略，并由omitted_report_fields逐项说明。完整gaps保留，包括由未决问题/成员/关系派生的缺口，不能在明细省略后继续删掉这些gap。若all_member_ids、selected_member_ids、read_member_ids完全相同，仅模型省略前后两份重复列表，member_sets_equal=true明确三者相同；冻结范围和输出schema不变。完整H1和旧报告均不改写，省略不代表历史不存在这些内容。只要存在H1，就从A的模型视图省略saved_analysis及其旧截断标志，并列omitted_fields；此模型取材决定不再依赖查询缓存能否复用。

当前Office冻结材料通过真实执行器＋模型HTTP替身完成原错误响应的一次纠错并保存；同原usage6982下，实际纠错请求预检16929，剩余17018，余89。另一直接用例组合新材料、追加、required_tools、当前查询复用和一次纠错。数字只证明本地输入接线/预算，不证明真实模型输出质量。

固定 Office 预算回归场景必须在现有限额内到达可提交结论的纠错步骤；若新增材料使它再次被输入额度阻断，T6 判为未通过，先在现有模型视图中收敛有说明的重复信息，不能以“正确返回 input_or_token_limit”关闭原缺陷。一般超大输入仍按原停止合同处理，真实模型是否产生有效结论另由真实复验确认。

## Implementation Order

| 批次 | 工作及依赖 | 完成证据 |
| --- | --- | --- |
| B1 | A01 类型字段、查询版本及复用；依赖当前源码 | T1 查询/证据直接用例 |
| B2 | A02 锁内前置权限、失败来源模式；业务上独立，实施按 B1→B2 顺序 | T2/T3 概况直接用例 |
| B3 | D01 冻结/模型视图/指纹兼容；复用 B1 的查询版本控制 | T4/T5 材料与兼容直接用例 |
| B4 | 三者与既有追加修复组合；只在 B1–B3 完成后形成实际版本清单 | T6 受影响追加验证、可审阅更新材料；后续授权下的一次真实复验 |
| B5 | 汇总实际证据、一次结束审阅、归档前检查 | 事实与待办同步，未完成不归档 |

不新增逐批独审门。已有 required_tools/压缩实现由 `fix-case-followup-gaps` 管理；本 change 负责组合版本与新问题，真实追加复验只跑一次并供两处任务引用。

## Validation Strategy

| 编号 | 最小直接场景 | 核对重点 |
| --- | --- | --- |
| T1 | 混合类别 + 旧/新进程缓存候选 | 实际 SQL 类别条件；只采用 1007；活动字段进入模型/账本；旧结果不复用、新版本仍可复用 |
| T2 | 旧 Case→基础刷新失败；旧基础→Case 刷新失败，来源均未变 | 保旧正文/来源时间/hash；对应模式 stale 与 GET 一致；失败尝试保存；无旧文和纯基础分支复用原用例 |
| T3 | 缺 cases:read 的旧 Case→基础刷新，及同权限纯基础对照 | 前者 403、模型/尝试/成本 0；后者保持原准入；不测真实 JWT/缓存撤权 |
| T4 | Office 原件 + 一个含 UTF-8 超限字段的变体 | 描述/PID/raw 字段取材、原文指纹、保存/模型裁剪分别说明、模型请求和读回对应 |
| T5 | 只变正文/原始 JSON（含超限尾部）；旧 Run/new key/旧 key | 新指纹失效复用、旧 H1 仍可读、旧 key 不升级、原 Markdown 保持 |
| T6 | 当前全部材料规则叠加 required_tools/追加纠错 | 在原预算内核实际模型输入、必要调用/适用复用、一次纠错与保存；不拿旧离线数字代替新输入 |

优先扩展现有 Case/Incident/related/navigation 用例，不为六组场景建设六套框架。场景数不预先当测试通过数；实际运行仅受影响集合，记录精确用例名、版本、输入和输出。

后续获准更新真实环境时：在已核的实际组合版本中使用新 operation_key，复验 Office 取材及追加、网络必需调用/适用复用、LSASS 成功空结果/成员编号/截断语义。A01 混合类别及 A02 模式切换以直接用例为必要关闭证据；真实环境有对应来源时再核，不为凑场景注入生产数据或制造模型故障。旧 207 响应、失败 Run 和凭据清理原件保持。

网络复用样例先由当前组合版本的新主 Run 形成适用的查询，再用新 key 追加；不能要求缺少新材料/查询合同的 r1 历史结果命中新缓存。Office/LSASS 的来源仍可复用已有模拟材料，不重新摄取或修改旧案例。

## Risks / Trade-offs

- 条件式前置 cases:read 收紧刷新权限，但消除了先收费再因保旧正文拒绝的分支；没有 Case 来源旧文的基础用户不受影响。
- 新材料增加输入、PG 工件与响应体积；上限和原预算明确限制，裁剪导致的证据不足继续报告。
- 材料版本/进程查询版本使部分旧缓存不再命中，可能消耗一次新的有界查询；不为兼容而把旧语义结果当新证据。
- hash 能识别来源变化，不能证明原始事实正确；补入正文也不保证模型语义正确，真实内容审阅继续保留。
- 不把已知取消/遗留 running、reaper、费用全局额度或 manifest 核验扩展为本轮前置任务。

## Rollout / Rollback

本轮不部署。实施完成后先保存具体 commit、测试清单、镜像/源码清单、现有服务差异与真实调用范围；实际更新仍需已有授权适用或后续明确授权。不能把旧 r2 准备标签自动当成本 change 的发布镜像，应给实际组合版本独立可追溯标识。

预计无迁移；回退仅切换已核服务版本，保留所有新旧 Run/工件。退回旧版本会重新暴露原功能缺陷，也可能不理解新材料，必须如实说明；不删除账本、不重置 operation_key、不自动重试旧 Run。结束时旧 change 与本 change 引用同一真实回执，各自只关闭实际满足的任务。
