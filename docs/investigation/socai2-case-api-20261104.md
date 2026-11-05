# 新表 Case 写入、手动启动与页面读取合同

当前补充：本页下方部署/表数量为原Case HTTP批次记录。最新合同已增加事件关联与移动、H任务和baseline/prepare，124后为29表459列；新版单开服务，见[关联](socai2-case-relations-20261104.md)、[H/prepare](socai2-human-tasks-20261104.md)和[独立服务OpenAPI](../design/socai2-independent-api-v2.openapi.json)。`covers_current_members`仅表示成员覆盖，不证明覆盖后来更新的材料/H；C使用领取时冻结版本，需要新事实时显式准备并启动下一轮。

2026-11-04。本批将新 `socai2` Case 数据和完整基础调查接到独立 HTTP 路径。页面保持现状；当前功能只针对新表中已存在的告警，Fusion 告警/事件新表写入、历史迁移和生产切换尚未实施。业务表仍为 29 表 458 列，原枚举与通用 JSON 合同不变。

## 1. 入口与边界

全部路径位于 `/api/v1/socai2/cases`，现有 `/api/v1/cases` 合同保留。使用现有 `cases:read`/`cases:write` 鉴权；租户和操作人只取认证上下文，写入再核对 `public.users.id/tenant_id`，不接收请求体伪造的租户、操作人、执行器或预算。

`SOCAI2_CASE_API_ENABLED` 默认 false，未启用返回 503。已注册路由，但本批没有修改运行环境或部署；启用前必须完成123迁移和相应数据入口。不会在请求失败时查旧表、隐式复制旧告警，或切回旧调查。测试仅在现有独立合成库启用注入服务。

| 方法和相对路径 | 请求 | 返回与用途 |
| --- | --- | --- |
| POST 空路径 | operation_key、title、description、severity、tags、alert_ids | Case ID、范围版本、初始 pending Run ID；至少1条已有新表告警 |
| GET `/{case_id}` | UUID | Case业务字段、当前成员、当前采用判断的来源/覆盖、待更新/活跃基础记录 |
| PUT `/{case_id}/members` | operation_key、expected_scope_revision、完整 alert_ids | 新范围版本、被更新/新建的 pending ID；空集合允许保存，但不能启动空范围 |
| GET `/{case_id}/history` | limit 1..100、可选 cursor | baseline Run（含pending）和正式保存AI Result；未保存AI执行不列入正式历史 |
| POST `/{case_id}/runs/{run_id}/start` | operation_key、expected_scope_revision、成对有时区窗口、可选 comparison_result_id | 同步执行后重新读取最新 Run 详情；重发原请求不重派 |
| GET `/{case_id}/runs/{run_id}` | UUID | 真实状态/停止、成员覆盖、步骤、调用与用量、工件目录、结果关联和启动条件 |
| GET `/{case_id}/results/{result_id}` | UUID | 正式结果全文、逐成员覆盖、来源Run、明确关联的C6详细快照及报告工件ID |
| GET `/{case_id}/runs/{run_id}/artifacts/{artifact_id}` | UUID | 该案该轮原JSON/文本及元数据、hash、留存说明；验证内容hash，不执行外部blob读取 |
| GET `/{case_id}/runs/{run_id}/materials/{material_id}` | UUID | 基础Run冻结的材料版本；不跟随告警latest指针，不读取未冻结版本 |

请求/核心返回类型在 `case_contracts.py`；运行时OpenAPI记录枚举、空值、UUID、时间与输入上限。Case资料/Run/Result分别有明确模型；可变产物保原带版本JSON合同。Case标题200字符、描述20,000字符、标签最多50个且每项128字符；成员最多200，重复成员/标签、空白标题、额外请求字段拒绝。空/已解决Case的其他特殊动作仍不开放。

## 2. 写入与执行

创建使用服务端由租户和 operation_key 派生的 Case 身份。并发同请求落到同一行并核原请求指纹，不靠“先查询再插入”判断不存在。Case、成员、scope_revision=1、pending Run和活动同事务提交；任一成员缺失或跨租户，整个事务回滚。初始Run明确保存 `trigger=case_created`、`purpose=建立案件的初始分析`，不把这句入口说明当调查结论。

成员更新复用已验证的 Case→Run 锁与版本校验。连续修改未启动范围更新同一pending；Run已经领取则保持其冻结材料，变化维护下一条pending。请求重发回原变更回执，旧版本409，无写入一半的成员关系。

手动启动核认证操作人，使用服务端固定上限：4模型、4Tool、24,000 tokens、120秒、每查询200行。客户端不能传入预算或网关。沿原 `start_full` 提交running后执行C1–C6，不建调度器、后台队列或自动下一轮。响应重新读取数据库当前状态；同请求重发可以读到running/unknown/已完成，不能把领取Claim误当最新状态。执行/响应异常返回503和Run读取路径，不把供应商或数据库原异常回显；取消继续沿原unknown保护处理。

这里的Case业务状态与Run执行状态是不同字段，GET不会根据Run状态改写Case。

## 3. 页面字段逐项出口

对应第一轮审计的36个调查展示字段，本批新增读取出口；是否有实际业务产出仍以来源步骤为准。

| 审计项 | API字段/来源 | 语义与当前边界 |
| --- | --- | --- |
| D01 本轮ID、Case | run.id/case_id；result.id/source_run_id | pending也有独立Run ID，Result与Run身份分开 |
| D02 调查标题 | run.title；result.title | 入口记录与正式交付标题分别保存，不能取Case标题当模型结论 |
| D03 调查类型 | run.kind；result.kind | baseline与ai_saved明确区分，人工任务不伪造成Run |
| D04 触发原因 | run.trigger | case_created/members_changed/question等；范围变化不证明此前已有有效结果 |
| D05 本轮目标 | run.purpose；result.purpose | 本轮实际目标，不能取Case.description替代 |
| D06 建立初始分析 | 初始Run的trigger和purpose | 创建事务写入入口说明；不当调查已经完成的结论 |
| D07 执行状态 | run.state/stop_reason/stop_detail | pending/running/unknown与终态直接读保存值；不由页面刷新推断 |
| D08 交付程度 | run.delivery_state；result.delivery_state | completed不代表完整交付；现有缺源仍可为partial |
| D09 本轮结论 | result.conclusion | 正式摘要在详情和history同一ResultSummary字段；未生成返回null |
| D10 结论与系统收尾 | result.conclusion_state/conclusion_origin/validation_state/closing_note | 系统交接结论为空；accepted仅是执行器校验结果，不证明事实真伪 |
| D11 主要发现 | result.findings | 保留范围、判断及真实来源引用 |
| D12 支持依据 | result.findings[].support；对应artifact/material | 每条引用保角色、路径和原件身份，不能将标签或执行回执当观察 |
| D13 反证 | result.findings[].counterevidence | 与限制分列；成功空查询不能自动成为反证 |
| D14 比较哪轮 | run/result.comparison_result_id | 精确指定旧Result，不取最新报告代替 |
| D15 输入范围变化 | delivery.detail.comparison；input_artifact_id对应C1快照 | 保存程序计算的新增/移出/共同成员；pending的当前范围在Case.members，尚无冻结输入 |
| D16 结果变化 | result.change_kind/change_summary | 无有效基线保not_comparable及原因，范围差集不冒充判断变化 |
| D17 对Case影响 | result.case_impact | 保支持变化、不能泛化、成员范围和下一步；不等于已执行处置 |
| D18 限制、未决 | result.questions、members[].limitations、delivery.detail及步骤原件 | 未执行、查空、失败和截断分别留因 |
| D19 建议 | result.recommendations | 含目标/理由/来源/审批要求；不自动创建任务、审批或执行动作 |
| D20 成员与读取数量 | current_member_count、input_member_count、read_counts、analysis_counts、Result.members | pending成员随范围维护，此时input_member_count为待启动成员数；input_artifact_id非空后才是冻结输入。当前成员、冻结输入和最终覆盖分开 |
| D21 当时输入、窗口、对象 | Run窗口/input_artifact_id；该轮artifact与materials | 冻结ID读取；新材料版本不会替换旧输入 |
| D22 逐告警判断与图 | Result.members、graph_artifact_id | 结论覆盖按逐成员保留；图派生关系不等于因果 |
| D23 记录与执行时间 | run.requested_at/started_at/ended_at/scope_updated_at | pending无开始/结束，Case业务时钟不被GET刷新 |
| D24 总耗时 | duration_seconds；elapsed_seconds/observed_at | 有开始和结束才有总耗时；运行中elapsed不是最终耗时 |
| D25 模型调用数 | usage.model_calls；steps | 统计已领取的model尝试，排除planned/skipped；不是成功答复次数 |
| D26 Tokens | usage.known_total_tokens/unknown_token_calls/total_tokens | 有任一次未知则总量null，已知累计仍保留；目录截断不补零 |
| D27 工具记录数 | artifact_counts.tool_response；tool_calls；steps | 已存返回材料数与调用尝试数分开，不把二者互相代用；复用/状态以步骤原件为准 |
| D28 费用 | usage.costs_by_currency_and_price_version/unpriced_model_calls | 按币种及计价版本分组；未定价不当免费，无真实计价验收 |
| D29 保存材料 | artifacts/artifact_counts/artifacts_truncated | 每个工件ID只计一次；目录有界但总数来自全部行，内容按明确ID读且核hash |
| D30 已开展工作与最后记录 | steps；last_recorded_at | 取Run已存记录/范围/开始/结束时间、全部步骤开始/结束、全部工件采集时间的最大值；不使用observed_at，也不受目录截断影响 |
| D31 报告正文 | result.report_artifact_id；delivery.detail_artifact_id/markdown_artifact_id | content_json/content_text包装原正文；尚无单独文件下载响应，前端可按已有正文接展示/下载 |
| D32 AI正式保存 | result.source_answer_id/saved_at/saved_by；source_answer.conversation_id/in_reply_to/answered_at/input_artifact_id | 读正式保存和原答复关联；AI生成/保存写入服务未在本批实现 |
| D33 人工反馈来源 | C1输入与source_snapshot中的固定task_revision及角色引用 | 能读已冻结事实，任务写入/编辑/完成服务仍待 |
| D34 当前采用认识 | current_assessment.value/sources/members/covers_current_members | 读明确采用版本；不会用最后Run替代，缺完整覆盖集合时返回null |
| D35 待更新范围 | baseline_records[].run.scope_revision/scope_updated_at/state、Case.members | 未启动合并、已领取冻结、下一条手动启动；scope版本变化与覆盖变化分开 |
| D36 读取一致性 | History与详情共用RunView/ResultSummary；POST start返回RunDetail | 单次读取同一只读快照；跨请求进行中状态可自然推进。历史不重复加载全文，按明确ID取详情 |

历史按 `requested_at`（基础Run）或 `saved_at`（正式AI结果）及带类型身份稳定倒序；游标保时间+身份，同时间记录不因翻页漏掉或重复。尚无正式Result时返回null，不编造展示结论。AI正式保存的每个Result保独立身份；人工作业仍由后续任务接口读取。

## 4. 一致性、完整性与有界读取

所有GET通过 `REPEATABLE READ, READ ONLY` 事务读取同一快照并设置本租户RLS参数，代码同时限定tenant/Case/Run。读取期间其他事务修改成员，不会把旧范围版本与新成员混成一份返回；GET不创建分析、调用模型、生成报告或更新业务时间。

Case成员/当前判断成员与来源、Run成员/工件/结果关联、Result成员各最多返回200；步骤最多1,000，明确返回truncated与数量。用量对省略的模型步骤保持未知，不假装统计完整。当前判断覆盖集合不完整时返回null，不能从截断集合推出全覆盖。

`last_recorded_at`从全部保存的运行时钟、步骤和工件聚合，与目录上限无关；不是页面访问时间。AI正式保存结果另保saved_at，不能拿保存动作改写原Run耗时。

工件先读元数据，超过128KiB或大小未知不加载正文，返回明确availability；外部blob仅返回可用性，不回显私有位置、不自动下载。已留存JSON/文本内容须通过hash检查。C6详细快照从对应C6终态回执解析，并核同Case/Run及实际Result ID；其他保存路径没有C6配套明细时返回null，不找“最新一份”补造关联。

## 5. 具体例子

**首次建案。** 已有新表告警A1；POST创建返回Case C1、scope_revision=1、Run R1。GET历史立即返回R1 pending_update，started_at/result为空。用户POST启动R1，后台执行后响应读到completed/partial及Result X1；GET X1取得本轮结论、比较、影响、成员覆盖和三类报告工件关联。

**运行期间新增成员。** R1模型已领取时，先加入A2，再加入A3；两次PUT返回同一个R2 pending ID，scope_revision递增。R1详情仍只有A1，当前成员数为3；启动R2返回409，R2保持待更新。R1结束也不自动启动R2，旧范围结果不会覆盖当前判断。再次GET R2得到可启动的业务条件，实际权限仍由认证校验。

**旧材料与新材料。** R1冻结material v1后，告警latest更新到v2。R1的materials/v1可读；用R1请求v2返回404，避免页面展示的新原文与历史结论依据混配。

**执行不可确认。** 模型传输抛错，POST返回503及Run读取路径；GET显示unknown、缺失用量和已有步骤，正式结果列表为空。重发原请求只读取该记录，没有第二次模型调用。

## 6. 验证和下一步

本批11项不同新检查、2项事务回归的最新结果均通过，分5批完成，不合称一次首过。ASGI实际路由、真实权限依赖与21原独立合成PG参与验证；认证身份、模型和湖返回明确替身，未验证真实登录服务或模型语义。最初SSH连接超时，0检查执行/0角色创建；用户恢复网络后继续同库验证，前次失败记录保留。首轮8过2夹具失败；补夹具后又暴露开始必需字段及blob_ref类型错误，两项原失败均保留。修正后定向复验，另补目录截断最后时间、AI来源对话并复核基础/AI结果，未变通过项复用。最终明细见 [本批回执](../operations/socai2-case-api-20261104.json)，可交前端的[运行时OpenAPI](socai2-case-api-20261104.openapi.json)与实际路由一致。

后续优先Fusion告警/材料/对象/来源、事件/成员/诊断的新表写入适配和字段逐项对照，再补事件显式关联Case/移动等数据事务、外部来源及H/Q业务服务。旧告警/事件、旧历史及页面尚未切换；新接口能读出已生成数据不代表生产数据已经进入新表或完整调查质量通过。报告修复继续暂停、r13不重试、5.3未完成。
