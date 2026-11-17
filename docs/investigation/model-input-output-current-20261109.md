# 每个模型环节的输入与输出

更新于 2026-11-13。按模型调用环节列出，同一模型可以承担不同环节的任务。以下描述当前实现的输入、输出、程序职责和验证边界；实际部署状态以 [PROGRESS](../../PROGRESS.md) 为准。

固定流程代码已随21核心`v1.2-20261113-r1`和`processing-20261113-r1`发布；独立HTTP两端已同步`investigation-sync-20261113-r1`（本机-local），Swagger docs19，见[接口同步回执](../operations/evidence/investigation-http-sync-20261113-01/README.md)；实际状态以PROGRESS为准。本页只描述固定A/I→Case链，不表示自动串联、流式队列或反馈自动重算已启用。模型质量按负责人决定后置，原答、失败和NOT_PASSED保留。

最新Case实际请求使用[10批](../operations/evidence/fixed-investigation-20261113-10/README.md)：复用既有A/I、H和指定比较，只新建一个Case Run，5次生成；C3五问由程序补成六问，C6一次纠正后保存/采用，完整业务质量未通过。该批4次ASGI/真实隔离PG读回与[发布后生产既有数据只读核对](../operations/evidence/fixed-investigation-release-20261113-01/README.md)是不同证据，不混称生产新模型流程。

较早的[7次调用目录](../operations/evidence/model-io-inventory-20261109-01/README.md)、[r6角色核对](../operations/evidence/case-evidence-roles-20261110-01/execution-summary.json)及各轮失败继续保留，以下标为历史的样例不是新版重新执行。

## 共同边界

每次调用由**本环节任务指令、当次业务材料、输出 Schema**组成。C3 还单列工具目录；Deep 在其输入里带可选工具。Schema 明确输出结构和本轮可用来源/成员/对象等范围。

任务指令由代码或版本化 profile 提供，同一环节通常复用；材料、引用编号、成员及可用工具随本次请求变化。输入不是由助手临时理解后手写的案情概述。正文按原文保留，结构字段按规则整理；后台身份与状态由程序管理。

来源角色分为原始观察、上游标签、先前判断、人工陈述和实际执行回执。短号用于引用和结构化关联；它与后台 UUID 不同，也不能把源 IP、业务用户、进程、会话等业务身份一并删掉。

Case 查询来源的内部 `source_map` 同时保存 `query_alert_ids`（查询发起范围）、`record_alert_ids`（身份一致的历史记录主体）、`alert_ids`（可用于本案成员引用的范围）和 `membership_basis`（依据）。历史行须核对记录 ID 及存在的分析／反馈主体；案件外或身份不一致不猜归属。其他工具的查询绑定标为 `query_binding_only`，不构成逐行行为观察。C3、Deep、C6 均保留来源 UUID、路径、角色和原值，不回填旧工件。

C3/C6 的一次纠正反馈列具体字段路径、允许来源范围、本次 finding 编号、实际来源角色和逐成员直接观察缺口；最终 conclusion／impact 还核成员依据覆盖。observed 生成仅使用有成员依据的 observation，排除 query_binding_only；inferred 至少有支持，unresolved 至少有限制，无合格观察时不生成 observed。历史合法时间上下文接收保持。标签与说明留在带来源的成员解释等位置，不能靠删引用／换状态保留无据主张。纠正仍失败时保留有效局部，不采用无效结论。Deep query 需要已有 binding 且 answer=null；answer／handoff 需要非空 Answer，handoff 必须 unresolved 并写缺口。生成器为网关展开每个完整分支。上述内部约束不增加数据库列或改变告警 API 字段。

| 环节 | 要解决的问题 | 当前实现与边界 |
| --- | --- | --- |
| A 告警分诊 | 一条告警如何定性，依据是什么 | 五字段、模板输入已部署 21 |
| I 事件诊断 | 既定成员合起来说明什么，还缺什么 | 四块输出、模板输入已部署 21 |
| C3 主分析 | 全案初步解释、关键发现与必要补查 | 模板输入和七块输出、五个业务问题及程序coverage已发布核心21 |
| Deep | 一个指定问题如何查、答或交接 | 文本输入、四项输出已部署 21；问题号由程序恢复 |
| C6 最终分析 | 综合补查作出最终结论、影响及变化 | 完整前序交接与身份恢复已部署 21；固定首次比较与建议编号由程序提供 |
| C3.reanalysis | 新证据到来后重新作初步综合 | 现有可选入口，不是默认链额外必经调用；采用独立 JSON 输入装配 |

下列结构是**模型需要输出的字段清单**，不是编造的模型答复。完整实际答复见每节链接。

## 1. A：单条告警分诊

输入形式：固定任务指令 + 程序按结构生成的业务文本 + 五字段 Schema。

输入内容：

- 告警发生的行为、主体、对象、时间、action/outcome、进程/命令、连接端点等有值业务字段，以及非空采集说明。
- 检测标签、上游等级等背景，按来源角色区分，不能充当恶意或授权证明。
- 程序安排的资产、历史告警、威胁情报三类基本查询，只提供必要业务结果；未查询仅写“未查询”，失败/未知/无结果分别表达。不把查询参数、耗时、条数和执行限制输入给模型。
- 可用人工反馈、历史判断原文；实际原件与本轮来源编号。

无意义空字段和声明为后台管理的结构字段不进入业务文本；未知有意义分支、`0/false` 不通用删除。不会把后台用户 UUID 当作业务用户名。

输出完整结构：

```text
verdict: true_positive | false_positive | benign | needs_review
confidence: 0..1 | null
rationale: 判断理由
evidence_ids: [本轮来源编号]
recommendations: [{reason: 尚需核实什么, source_ids: [相关来源编号]}]
```

这里的定性是有据的威胁、描述被反驳的误报、行为真实且有正常/授权依据，或证据不足。`confidence` 是判断自评，不是风险分。

程序负责关联原告警/Run/材料、真实查询状态、来源还原、验证及存储；原解释字段由事实模板和模型理由装配，模型不再生成独立完整报告或后台身份。当前 `evidence_ids` 至少 1 项；确定性定性的主引用限原始观察或人工陈述，引用合法仍不能保证理由正确。

历史实际：[网络告警输入](../operations/evidence/model-io-inventory-20261109-01/A-network/input.txt) · [原答](../operations/evidence/model-io-inventory-20261109-01/A-network/output-original.txt)。登录截断、进程引用失败也在[目录](../operations/evidence/model-io-inventory-20261109-01/README.md)，不只展示成功例子。

依据：[输入边界](../../services/api/app/socai2/alert_model_boundary.py)、[输出适配](../../services/api/app/socai2/alert_output_adapter.py)、[配置与指令](../../services/api/app/socai2/alert-input-v1.json)。

## 2. I：既定事件的整体诊断

输入形式：固定任务指令 + 按成员/业务块组织的文本 + 四块 Schema。

输入内容：事件既定范围与说明、每条告警的冻结业务材料、可用且同材料版本的 A 分诊、同A Run查询中的相关业务结果、适用人工陈述以及必要活动时间。成员用短号；无有效A判断或缺少材料如实表达，不能用过期分析顶替。查询参数、执行限制、计数、后台版本和重复历史留在原件/账本。

**不重新决定这些告警该不该归并，不输出归并关联评分，不改变 A 的判定。** 模型说明整体行为、已有材料支持的解释和影响整体判断的缺口。

输出完整结构：

```text
diagnosis: {
  summary: 主要发生了什么,
  conclusion: 整体判断及理由,
  source_ids: [依据],
  limitations: [整体限制]
}
members: [{
  alert_ref: 成员短号,
  state: summarized | unresolved | not_reviewed,
  assessment: 该成员对整体判断的意义,
  source_ids: [依据], limitations: [局部限制]
}]
findings: [{
  statement: 新增事件级关键发现,
  state: inferred | unresolved,
  alert_refs: [原适用成员], source_ids: [依据], limitations: [限制]
}]
open_questions: [{
  text: 待核问题, alert_refs: [相关成员],
  source_ids: [提出问题的依据], evidence_requirements: [还需取得什么]
}]
```

程序恢复真实成员身份、生成发现编号、装配原诊断/发现/问题字段与来源。四块分别承担整体判断、成员解释、事件级新增发现、后续缺口；不是四份重复报告。没有额外发现/问题时相应列表为空。

筛选后的真实[05批I完整输入](../operations/evidence/fixed-investigation-20261112-05/flow/I-model-input-exact.txt)及保存见[05批回执](../operations/evidence/fixed-investigation-20261112-05/README.md)；10批复用已有I，没有再执行I。历史[原输入](../operations/evidence/model-io-inventory-20261109-01/I/input.txt)/[原答](../operations/evidence/model-io-inventory-20261109-01/I/output-original.txt)的整体引用失败继续保留。

依据：[输入边界](../../services/api/app/socai2/incident_model_boundary.py)、[输出适配](../../services/api/app/socai2/incident_output_adapter.py)、[配置与指令](../../services/api/app/socai2/incident-input-v1.json)。

## 3. C3：Case 初步主分析

输入形式：本阶段指令 + 结构化业务材料转换的文本 + 可用工具说明/绑定 + 七块 Schema。

输入内容：

- 冻结成员、调查窗口、必要对象；后台 Case/Run/租户身份由程序持有。
- 完整材料按业务字段投影，保留明确原始观察、非空正文及未知业务分支；输入检查排除的正文另记限制，不能称读过全部原文。
- 同材料有效A分诊及必要依据；I优先使用整体结论、相关发现和待核问题，去掉重复概览、空限制和已知程序标记，保留业务限制、原范围及历史判断角色。
- 适用H版本的反馈原文、范围和依据；C2实际取得的必要业务背景、活动时间和来源标签。历史案例卡片保留原历史主体/材料版本，分诊和人工原文各自引用，不能成为本案观察；详见[历史知识交接](historical-alert-knowledge-handoff.md)。
- 模型回答五类业务问题：原始事实、行为联系、行为性质、授权、影响。第六问coverage由程序按真实材料/查询/保留结果生成，不让模型分析执行台账；保存和GET仍为六问。行为联系不等于重新审批事件归并。
- 可用工具目录仅保留选择补查所需的能力、支持问题及合法binding；查询参数、执行限制和范围台账由程序保存。工具数量不由领域数推导。

输出完整结构：

```text
summary: 全案初步解释
members: [{
  alert_id: 成员短号,
  state: analyzed | unresolved | not_analyzed,
  summary: 该成员的分析, evidence_ids: [依据], limitations: [限制]
}]
findings: [{
  id: 本答复内发现编号,
  state: observed | inferred | unresolved,
  statement: inferred/unresolved 的发现内容（observed 不由模型输出此字段）, alert_ids: [原涉及成员],
  support_ids: [支持], counter_ids: [反证],
  alternatives: [替代解释], limitations: [限制]
}]
questions: [{
  id: 五类业务问题之一（不输出coverage）,
  state: answered | unresolved | not_applicable,
  answer: 答案, evidence_ids: [依据], limitations: [限制]
}]
domains: [{
  name: identity | cloud | phishing | insider,
  applicability: applicable | not_applicable | undetermined,
  reason: 为何适用或不确定, alert_ids: [本领域关注成员],
  finding_ids: [相关发现编号], limitations: [限制]
}]
conflicts: [{
  id: 本答复内冲突编号, finding_ids: [冲突发现],
  state: resolved | unresolved,
  explanation: 冲突/消解依据, evidence_ids: [来源]
}]
followups: [{
  question_id: 所服务的问题, alert_ids: [成员],
  mode: query | deep | graph | human,
  objective: 补查目标, required_evidence: 所缺证据,
  source_ids: [提出该需求的依据], object_keys: [对象短号],
  binding_id: 目录中绑定短号 | null,
  priority: decision_critical | supporting
}]
```

当前 C3 响应的 `followups` 上限来自冻结 profile 的 `c3_output.max_followups=2`，提示、生成 Schema、普通接收和 partial 一致。超限原答明确失败，不能截成前两项；历史工件恢复及 C6 建议保持原容量。实现及验收见 [有据结论变更](../../openspec/changes/archive/2026-11-11-ground-case-conclusions/validation.md)，21 已核实际加载上限 2。

四个领域共用一次 C3 调用，不是四个模型；跨成员发现保留原范围。程序恢复身份短号、校验来源/范围、纠正或保留独立有效局部，再按原合同保存和调度。模型可选的图/人工需求不等于已生成图、已创建任务或已完成人工确认。

七块结构和四领域沿用既有Case职责；模型输出五问，程序补齐保存六问。observed发现由模型选择必要原始依据，字段原文由程序装配；推断和未决正文仍由模型判断。保留后的局部结果重新计算coverage，不用完整原答的覆盖追认被拒部分。

最新实际：[10批完整请求（全部消息/Schema）](../operations/evidence/fixed-investigation-20261113-10/flow/R01/review/call-01-C3-full-input.txt) · [业务输入](../operations/evidence/fixed-investigation-20261113-10/flow/R01/review/call-01-C3-input.txt) · [原答](../operations/evidence/fixed-investigation-20261113-10/flow/R01/review/call-01-C3-answer.txt)。五问接收及六问装配已验证；名称推断自动化等正文质量仍未通过。

依据：[输入边界](../../services/api/app/socai2/case_model_boundary.py)、[输出合同](../../services/api/app/socai2/baseline_analysis_contract.py)、[身份适配](../../services/api/app/socai2/case_output_adapter.py)。

## 4. Deep：一个问题的补查决策

当前输入为本阶段指令、按业务结构生成的文本、当前可用工具说明和 Schema。使用与 C3 相同的冻结来源；提供本次问题及补查目的、C3 对该问题的判断和引用依赖、相关观察/反证/人工陈述、实际查询结果。明确范围之外的非人工材料可省略，必要引用仍恢复并保留原范围；不缩窄真实工具绑定。

C3 前序判断仅用于定位本问题，必须核对其原始支持；结构通过不证明正文为真。Case 登记 title/description 在原件保留，模型视图按配置排除，历史引用恢复也应用相同投影；任务目的与独立人工陈述保持。reason、答案和限制均遵守相同来源边界，需要目录外资料时交接，不能把本次未提供确认写成现实无人确认。工具只给必要业务结果和最短状态：未查询、查询失败、结果未知、无结果或有结果。行数、截断、参数和执行限制保存在程序回执，不追加到模型正文；返回行与本案成员的真实归属仍需保留，不能把相关范围说明误删成“无用元数据”。

当前模型输出四项，原数据库合同仍保留程序补回的问题号：

```text
action: query | answer | handoff
binding_id: 可选查询绑定 | null
reason: 为什么查询、回答或交接
answer: null | {
  state: supported | unresolved,
  text: 单问题答案,
  support_ids: [支持], counter_ids: [反证],
  alternatives: [替代解释], limitations: [仍不能确定什么]
}
```

`query` 时答案为 null，执行一个已有 binding 后再以实际返回决定下一步；`answer/handoff` 时 binding 为 null。`handoff` 必须未决；`answer` 也可以未决。程序记录执行结果，不因已返回 answer 就把问题视为确定解决。

四项输出已经接入执行器，程序绑定 `question_id` 后沿原校验、保存和读取路径。生成 Schema 的支持／反证来源排除 `execution_receipt`，查询状态与来源映射仍完整保留。每个 query／answer／handoff 分支分别带齐必填项和限制，避免供应商语法丢失公共约束；handoff 必须给出未决答案及限制。r6 参照批次 `case-evidence-roles-20261110-real-01` 的真实 handoff／answer 均完整并通过生成 Schema 和接收校验；query 分支有离线合同检查，没有新增真实 query 采样。各轮截断、缺字段及拒收原答保留。

最新实际：[授权问题完整请求](../operations/evidence/fixed-investigation-20261113-10/flow/R01/review/call-02-C4-deep-full-input.txt)/[业务输入](../operations/evidence/fixed-investigation-20261113-10/flow/R01/review/call-02-C4-deep-input.txt)/[原答](../operations/evidence/fixed-investigation-20261113-10/flow/R01/review/call-02-C4-deep-answer.txt)；[影响问题完整请求](../operations/evidence/fixed-investigation-20261113-10/flow/R01/review/call-03-C4-deep-full-input.txt)/[原答](../operations/evidence/fixed-investigation-20261113-10/flow/R01/review/call-03-C4-deep-answer.txt)。前者handoff/unresolved有效，后者重复引用拒收，不作为C6有效判断。授权问题不默认附加可选知识，已被必要前序明确依赖的来源仍恢复。没有为验证query分支新增真实调用。

依据：[输入构建](../../services/api/app/socai2/case_followup_input.py)、[输出恢复](../../services/api/app/socai2/case_followup_output.py)、[Deep 执行](../../services/api/app/socai2/baseline_deep.py)。

## 5. C6：最终案件判断与报告内容

当前输入围绕最终判断选择冻结业务事实、适用H、C3有效发现/业务问题/冲突以及必要原依据。前序members/domains不再整块重复输入，coverage留给程序；同一原计划只显示一次。Deep仅传有效答案及支持/反证/未决，原计划只保留目的和执行结果，查询完成与问题解决分开。前序结构化引用映射到本轮可见来源，缺失明确记录，历史正文和跨成员范围保持；前序判断仍不是独立观察。

前序引用指向整份事件诊断或材料元数据时，按配置关联已呈现明细，不重复塞入整份 JSON。对 C4 材料投影，仅在原件身份、路径、角色、成员及未转换值一致时合并来源编号；映射枚举或冲突值保留。新增查询保留同一行的字段关系、必要行为、原范围和“仅查询绑定”限制。没有有效 C3 时不伪造前序结论，按现有独立最终分析/系统收尾路径处理。

C6 逐项复核前序正文及问题状态，缺资料的适用问题保持 unresolved；`conflicts` 仅表达互不相容的有据主张，行为与来源标签可以同时成立。C6 的 coverage 由程序从真实材料读取、查询和保留分析状态装配，逐项保留查空/未查/失败/未知；已证影响、可能风险及未知分开；原始正文不会被程序改写为通过。当前 Case 新响应的冲突必须逐 finding/成员覆盖其直接 observation 支持，至少两个不同原始来源；生成、接收、一次反馈及 partial 共用此约束，有观察依据的 inferred 仍可保留。来源合法不代表正文互斥，历史读取合同保持。

模型输出如下；首次无历史或没有可用的指定比较依据时，`comparison`由程序冻结并恢复；可比时才由模型说明相对指定基线的变化：

```text
analysis: {
  summary, members, findings, questions, domains, conflicts, followups
}
conclusion: {
  text: 最终结论, state: supported | uncertain,
  alert_ids: [适用成员], support_ids: [依据], limitations: [限制]
}
closing_note: 本轮收尾说明
comparison: {
  kind: initial | unchanged | expanded | revised | withdrawn | not_comparable,
  summary: 相对指定历史结果的变化 | null, support_ids: [依据]
}
impact: {
  summary: 影响判断, alert_ids: [受影响成员], support_ids: [依据],
  supported_changes: [有据变化], cannot_generalize: [不能外推什么],
  next_steps: [还需做什么]
}
recommendations: [{
  action_type: investigate | contain | remediate | monitor,
  object_keys: [目标对象], reason: 建议理由,
  source_ids: [依据], limitations: [限制]
}]
```

`analysis` 中模型只生成五个业务问题，程序追加 coverage，存储/GET 仍有六问。observed.statement 按冻结的原来源路径和值装配；越权生成或原值超长明确拒收，partial 按保留结果重算 coverage。历史无职责标记的工件按冻结合同读取。其余使用上节 C3 的同名字段和语义，区别是 C6 的 `followups` 使用基础合同，**没有 C3 执行计划的 `binding_id/priority`**；最终建议不被当作本轮新的已执行计划。C6 结构化成员/对象使用短号，程序恢复真实身份；建议编号按顺序生成。首次比较由程序填入`initial/null/[]`；无可用比较依据时恢复已冻结的`not_comparable`，不让模型编造旧判断。有效指定比较才由模型说明变化，普通历史背景不能替代指定基线。历史成员/对象只作背景，不扩展新建议的可选目标。

材料读取状态、计数和完整逐成员state/limitations/omissions保留在冻结回执及coverage_facts；模型只接收本次判断需要的材料与缺失事实，不分析读取台账。available 不代表全文已读或业务结论已证；缺记录明确 unrecorded。C4 执行回执以整份 artifact、execution_receipt、source_path=null 引用，不能充当行为观察。

程序从同一最终结果装配原 `results`、领域、成员、证据、图和报告；实际执行/交付/采用状态由程序决定。Markdown 报告为程序渲染，没有第二次“报告写作模型”。`supported/uncertain` 是结论支持状态，当前不另设一个由 C6 重写的告警四态 verdict 或事件严重性字段。

存在重复风险：`analysis`、最终结论、影响、建议部分可重复表达。当前先补交接，保原合同；后续再比较逐项保留/修订/撤销/新增，不可静默沿用未复核的前序条目。**这一部分尚未达到全部优化要求。**

最新实际：[C6完整请求](../operations/evidence/fixed-investigation-20261113-10/flow/R01/review/call-04-C6-full-input.txt) · [业务输入](../operations/evidence/fixed-investigation-20261113-10/flow/R01/review/call-04-C6-input.txt) · [首答](../operations/evidence/fixed-investigation-20261113-10/flow/R01/review/call-04-C6-answer.txt) · [一次纠正请求](../operations/evidence/fixed-investigation-20261113-10/flow/R01/review/call-05-C6-full-input.txt) · [纠正原答](../operations/evidence/fixed-investigation-20261113-10/flow/R01/review/call-05-C6-answer.txt)。仅将impact成员范围纠正到其有据成员，最终accepted/uncertain/partial并成为第3版current；影响Deep的拒收和所有原答保留。程序接受/采用不等于正文质量通过。

依据：[当前输入筛选](../../services/api/app/socai2/case_followup_selection.py)、[输入装配](../../services/api/app/socai2/case_followup_input.py)、[最终输出合同](../../services/api/app/socai2/baseline_delivery_contract.py)、[保存和报告](../../services/api/app/socai2/baseline_delivery.py)。

## 6. C3.reanalysis：可选的补证后再分析

这个入口目前存在，但默认 C3 → 补查 → C5 → C6 链不额外执行它。不能把“代码里有模型调用”说成“每轮都调用”。

输入：冻结基础视图、新证据、前序分析摘要/补查需求、Deep 回答和图等，使用 JSON 装配。输出：基础`Analysis`七块，仍按该可选旧入口的六问合同；不能套用当前C3模型五问/程序coverage边界，`followups`不含`binding_id/priority`。它只形成新的初步分析版本，不发布最终案件结果。

该可选入口不在本次固定链验收范围，未适配为上述任务筛选合同，也没有新的真实样例。未来若启用，须先整理输入和前序引用；不能把固定链已收口写成仓库所有可选模型入口均已整理。

依据：[再分析入口](../../services/api/app/socai2/baseline_reanalysis.py)。

## 不调用模型的步骤及当前达成程度

C1 冻结材料、C2 按策略查询背景、C4 直接执行已选 binding、C5 生成图、最终存储/报告渲染都由程序承担。Deep 是 C4 的另一条按需路线，不能与直接查询混成“每个工具调用前都问一次模型”。引用及关联纠正是同阶段最多一次的有界再调用，不是另一个业务模型，也不保证每次发生。

按用户要求逐项核对：

| 要求 | 当前达成情况与证据 |
| --- | --- |
| 先明确模型目标，再选择材料 | A/I/C3/Deep/C6分别由程序按字段路径、类型、角色和任务筛选；必要反证和引用依赖仍保留，不是手工压缩或按样例值删除 |
| 工具只给业务结果 | query_result_text统一最短状态；结构化业务行保留必要字段及归属，参数、耗时和限制在账本 |
| 模型只判断业务内容 | C3/C6五问，程序coverage及观察原值；Deep问题号、C6建议编号和固定比较由程序提供 |
| 原件和保存读取不被精简破坏 | 10批4次ASGI/真实隔离PG读回一致；核心发布只读核对同一生产Case、Result和当前判断保持；无新HTTP字段/迁移 |
| 前序结论与依据一起交接 | 10批H、有效I、指定比较及必要引用进入实际请求；拒收Deep不进入C6有效结论；缺失和失败仍记录 |
| 质量与效率分开 | 10批5次生成/65000tokens；质量NOT_PASSED，知识合理使用未证明。不是受控A/B，不报告准确率或把费用未知记零 |

当前代码与生产加载证据见[固定功能版发布](../operations/evidence/fixed-investigation-release-20261113-01/README.md)。历史[有据结论验收](../../openspec/changes/archive/2026-11-11-ground-case-conclusions/validation.md)、[角色验收](../../openspec/changes/archive/2026-11-10-align-case-finding-evidence-roles/validation.md)和[Deep/C6接入](../handoff/history/2026-11-14-investigation-cleanup/documents/openspec/changes/complete-socai2-investigation-chain/case-followup-integration-20261110.md)仍按原批次保留。

## C2 知识检索与后续模型输入

C2由程序从冻结材料生成技术解释、取证指导、历史案例参考三类有目的的查询，经本地嵌入检索，按PG身份/hash回读并冻结原文；它不是额外的诊断模型。固定模板仍由各阶段任务指令与Schema定义，知识只作为所选的参考材料。

| 消费环节 | 选择规则 |
| --- | --- |
| C3 | 按当前问题、适用成员、条件、版本和预算选择；同一来源命中不同目的只展示一次，保留目的与引用 |
| Deep | 围绕一个问题选知识；授权问题默认不追加可选知识，必要前序引用依赖仍恢复；不因覆盖全案便复制全部历史 |
| C6 | 按业务问题与原适用成员对应知识，必要依赖优先；授权问题不默认补可选卡，不重新检索 |
| A/I | 本轮没有新增知识库检索；已有基础历史查询和必要判断依赖仍按各自职责传递 |

知识正文有容量限制，优先保留必要依据，不把所有命中整包拼入提示，也不调用模型重新压缩一份摘要。历史观察属于原告警，历史分诊是旧判断，人工反馈保留原范围；不能充当本案独立证据或授权证明。新采用A分诊保存后按已发布策略同步历史卡，未采用、失败或旧重复请求不借本轮补派；Case反馈当前仍需显式下一轮，不触发自动重算。

10批中9次检索的2个用途命中合并为1张448字符卡，C3、影响Deep、C6各按任务选入，授权Deep未追加；原答未结构化引用知识，合理使用仍未证明。字段、索引、版本和入库时机见[知识交接](case-knowledge-handoff.md)、[历史卡片交接](historical-alert-knowledge-handoff.md)。
