# 调查历史单页迁移

2026-11-26，所属 change 为 `complete-socai2-investigation-chain`。案件故事已完成独立验收，本步按负责人最新两张截图和 4173 已有多事件 Case 修正调查历史。先完成本阶段规格与直接判据，再实施。

## 目的、范围和效果

8181 现并读 E10 和遗留 `/runs?case_id`，后者无对应原生合同而返回 404。组件默认取首轮，把历史变成窄目录与详情并排。4173 无明确 Run 时呈现纵向卡片，显式打开后才显示固定轮工作台。

本步完整迁移历史目录与固定轮入口外壳，覆盖类型/执行/交付、保存摘要、四项投入、冻结输入数和时间、打开调查、工具记录入口、精确深链、切轮与返回。复用已验 StoryRelations 的全案来源及冻结输入规则。没有 Run 参数时不挂载详情，不从第一页推断默认轮。原失败、无结果、未知用量按实际记录保留。

不迁移其它 Case 子页、五个共用 Run 正文视图、调查执行明细或管理写操作。CaseEvidence 当前复用旧 CaseInvestigations 的入口保持。共享 RunWorkspace 只做本页嵌入所需身份、参数与结果归属处理，不改变独立告警/事件工作台。助手、正式21发布、Git交付、新Case/Run/Kafka/模型均不在本步。冻结告警合同、E10默认历史、R1全局目录和现有调查受理 POST 不变。

## HTTP 与来源

新增普通 Case 读取操作（前缀 `/api/v1/socai2`）：

| 接口 | 请求与响应 |
| --- | --- |
| `GET /cases/{case_id}/investigations` | 仅 `limit`（默认20，1–100）和 `cursor`（最多2048字符）。返回 `CaseInvestigationPage`。 |
| `GET /cases/{case_id}/investigations/{run_id}` | 同一 Case 范围精确定位；不依赖已加载页面。返回 `CaseInvestigationLookup`。 |

未知/重复查询参数、坏游标返回422；不属于该 Case 合法范围或不存在的 Run 返回404。读失败和查空区分。保留同路径已有 POST 的受理行为，读操作不调用它。

`CaseInvestigationPage` 包含 `case_id,items,total,next_cursor,observed_at,limitations`。`CaseInvestigationLookup` 包含 `case_id,item,observed_at,limitations`。列表与定位共用同一关系查询、卡片投影和已保存结果选择。每项 `CaseInvestigationCard` 复用 `InvestigationRef` 的原主体、Run、标题、状态、交付、请求时间、detail_url、结果引用及来源证明，另给：

| 字段 | 来源及空值口径 |
| --- | --- |
| `started_at,ended_at` | Run 实际保存的带时区时间，可空。 |
| `duration_seconds` | 两个有效已保存时间的秒差；缺时间或非法顺序为null，不用请求时间或页面等待时长代替。未结束的卡用状态表达。 |
| `input_member_count` | StoryRelations 已校验原输入 ID 集合长度；缺供/未核实为null，已证明空集合为0。暂定成员不能充当冻结输入。 |
| `tool_record_count` | 同轮全部已保存 `steps.kind=tool` 条目数，包括 planned/skipped。卡片标签为“工具记录”，不当作实际工具调用次数。 |
| `usage.model_calls` | 同轮已保存 model 步骤数，沿现行口径排除 planned/skipped。 |
| `usage.total_tokens` | 只有该轮所有上述模型步骤都有已报告合法 total_tokens 才给合计，否则null。无模型调用且已确认记录完整时为0。 |
| `usage.known_total_tokens,unknown_token_calls` | 复用 usage_totals 的已报告小计及未知调用数；部分已知不冒充完整合计。只投影本页所需字段。 |
| `preview` | null 或 `{result_id,result_type,kind,source_field,text}`。固定同轮已保存结果，text保留原文，前端按原型最多显示200字并可回原件。 |

### 关联范围与结果选择

列表/定位共享 `explicit_run_sources + StoryRelations.runs`。纳入本案基础 Run、同案已保存跟进结果的原 Run、由正式引用或已核冻结成员交集关联的 A/I Run；不以当前事件成员、当前指针或页面已载入项伪造原轮范围。Run ID 去重，多条来源保留，独立重试 Run 各自成卡。显式来源成立而冻结输入缺供的卡可以显示，但输入数仍为null并保留限制。

Case baseline 卡优先 E10 相同原始结果：同租户、Case、Run 下 `kind=baseline AND supersedes_result_id IS NULL`，V1 唯一索引保证至多一个。没有原件时，从同轮实际结果按 `saved_at DESC,id DESC` 选择。非baseline的保存跟进优先同轮最新 ai_saved，没有则同轮真实结果按相同顺序选择；无结果为空。卡的 run_kind 始终取 Run，不能因为预览是 ai_saved 改造 Run 类型。同一 Run 的全部真实 Result 引用继续可选，不能隐藏其它保存版本。

固定结果后，Case 先用同一行 conclusion；为空则用有正文的 closing_note，source_field=closing_note，页面标“系统说明”。A 用原轮 rationale，I 用原轮 summary。无原件或该原件没有正文时 preview=null，链接仍保留。无需模型摘要、文字改写或跨轮补值。

去重后按 `requested_at DESC,run_id DESC` 键集分页，游标绑定本目录、租户和 Case。total按完整合法 Run 集合计数，页面与计数使用同一只读快照。仅批量读取本页 Run 的卡片列、工具计数和全部有效模型 usage；不取前1000步骤冒充全量，不逐卡装配完整 trace。既有来源与冻结核验复用，不新增另一套关系规则。

## 页面与交互

新建 `CaseInvestigationHistory.tsx` 和局部 CSS，只替换 CaseWorkbenchDetail 的 investigations 分支。默认一轮一卡；标题24px/600、上下4px，标题区下距22px；卡21px内距、8px圆角、16px卡间距；卡题14px/650；四项指标四列、16px间隔、上分割线、16px上内距、18px上下距，1000px下两列。按产品现有主题适配，保留原型的读序与动作位置。

卡片显示实际类型/执行状态/交付完整性、标题、原摘要预览、耗时/工具记录/模型调用/Tokens、冻结输入数与实际开始时间，以及“打开调查”。工具记录可点进同一 Run 的 tools 视图。缺耗时/输入/用量分别按未知显示，0保持0；无法核实的冻结输入不用当前成员数替代。

URL无run且无合法result-only深链时仅展示卡片目录。显式 `run` 用精确 Case+Run 读取，分页外也能打开。Case result-only 旧链接先沿 E14 解出源 Run，再规范化 URL。`run+result` 必须与原主体、源Run和返回引用一致；不合法不改取首轮。Case/A/I详情各用已有原主体固定路径，原结果不经通用 context 猜主体。

固定轮外壳包含“返回调查历史”、当前轮可分页选择、标题、真实输入和开始、类型/执行/交付标签，再进入共用五视图。切轮保留合法view与process的mode，清理旧result和轮内选中；显式选结果保留该结果身份。各视图链接保持当前原轮。返回目录恢复已读列表与可定位原卡，不自动进入首轮；浏览器前进后退和刷新按URL还原。

## 分工与必要验收

| 步骤 | 实施与通过证据 |
| --- | --- |
| 1. HTTP | 两GET、同范围定位及正式DTO；复用既有隔离PG夹具，核正常Case/A/I、多个来源去重、原baseline/ai_saved选择、失败无结果、正确工具记录及用量、冻结null/0、一页续读及分页外定位。只补直接受影响断言，保持E10/R1及已有POST的Schema/路由兼容。 |
| 2. 平台 | 只登记两GET，保留现有五条候选GET和其它回退。沿标准可信HTTP、只读PG和普通平台登录，配置化选择候选。公开Schema和原查询/错误透传，确认实际加载指纹。 |
| 3. 前端 | 冻结合同后可先写未挂载组件。HTTP直接验证及平台兼容核验通过后一次挂载。类型检查；定向核默认仅目录、正常打开/工具入口、固定run/result、切轮保留view及返回、错误/空态。复用既有用例，不为CSS加镜像测试，不跑全仓。 |
| 4. 统筹 | 用已有正式Case正常登录：完整卡片默认页及原型同视口；数量、摘要身份及四指标回同源HTTP/PG；打开一轮、工具入口、切另一已有原轮、返回与刷新。原旧失败保留；未在真实案出现的历史多Result/未知边界沿隔离直验说明。 |

每步通过后再进入依赖步骤。先运行 `openspec validate complete-socai2-investigation-chain --strict --no-interactive`，实现后以实际证据勾本步。原件留 `.local/validation/case-history-migration-20261126-01/`，公开工程回执在 `docs/operations/evidence/case-history-migration-20261126-01/`。独立验收不以HTTP成功或组件测试代替实页结果。
