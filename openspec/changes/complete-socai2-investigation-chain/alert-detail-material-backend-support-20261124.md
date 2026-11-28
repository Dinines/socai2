# 告警详情第 3 步：已有分诊与材料读取支撑

2026-11-24。沿 [第 3 步工作单](alert-chain-acceptance-plan-20261124.md)只提供现行合同、既有回执和有界读取定位。SpiritHub 修改页面；账号工作保持停止。服务端不新增材料或版本、不运行模型，不实现历史目录、同版本来源新接口、UID/湖查询、评论或连续接收，不部署或推送。

## 本步步骤与直接出口

1. 优先复用 `.local/validation/alert-a-run-support-20261124-01/page-selector-private.json` 及其原始 HTTP 回执，核同告警详情、`triage.source_run_id`、指定 Run 结果、解释工件/引用、`input_material_id` 和已保存材料的身份链。旧失效 IO 定位不再重试。先通过源码及原回执核清已有字段，再补必要现场 GET。
2. 从该 A Run 告警及此前 `alert-review-availability-20261124-01/attempt-03/` 已核正式主体中固定最多三个告警，均须属于原 `spirithub-pagination-20261124-01` 已授权批次。每个告警最多两个不同的已存材料版本：优先当前/冻结材料，再只读定位一个不同的旧版本。若原回执没有版本目录，按固定租户/告警查询至多一个旧材料的元数据；不扫描其他主体，不读取新湖数据。
3. 使用既有材料 GET 核对应主体、材料 ID、revision、来源范围和正文；检查 OCSF 非空内容以及富化为空/无内容条件是否有正式正例。原件与所选版本一致，缺失/保留状态分别记录，不能把最新来源分区当作旧版本来源。缺无富化或历史正例时明确留缺证，不制造输入或重跑分析。
4. 从实际 DTO、数据库字段、保存和读取实现明确 `ocsf_json` 的类型与空值语义，复用现有材料响应用例，并用实际序列化适配器做必要的离线原始 JSON 类型读回检查。此检查不创建数据库记录，不等于真实材料正例。
5. 完成后交固定选择器、工程检查、字段来源及未验边界。业务值、正文和私有身份仅保存在 `.local/validation/alert-detail-material-support-20261124-01/`。无直接服务端阻断则不改业务代码。

## 字段来源与保存边界

### 同一告警的事实、检测、分诊和人工结果

| 读取位置 | 来源和使用口径 |
| --- | --- |
| `/alerts/{alert_id}` 的 `facts` | 告警事实及已保存业务字段。`facts.id` 固定详情主体；`severity/severity_raw` 不当作模型分诊置信度。 |
| `material.id/content_url/detection/source_scope` | 当前材料的身份、检测标签和来源范围。检测标签、规则与 `detection.confidence_value/confidence_state/score_source` 属于接收/融合侧信息；现行投影在可用时把融合置信度乘 100 保存。没有值不推算分数。 |
| `triage` | 已发布分诊，来源由 `source_run_id` 和 `input_material_id` 固定。`confidence` 为 0–1，`confidence_percent` 仅在 `score_state=available` 且非 null 时乘 100；0 是有效值。`valid_for_current_input` 要求当前材料一致、freshness 为 current、Run completed。 |
| `feedback` | 独立已保存人工判断，保留其 `kind/verdict/rationale/actor/assessed_at`。不能把人工正文当检测原文或新的模型结论；当前判定展示沿既有人工/AI 来源规则，不改业务合同。 |
| `/alerts/{alert_id}/analysis/runs/{source_run_id}` | 固定 Run 的 `StageEntry`。解释位于 `explanation.content`，包括 `body/source_refs/recommendations/limitations/generation_method`；先检查 `available/reason`。解释按同 Run、同告警、kind 读取，并校验内容 hash 和大小；有解释不代表结论质量通过。 |
| `result.input_material_id` | 此轮输入冻结版本，不能换成 `facts.latest_material_id`。材料正文沿 `/alerts/{alert_id}/materials/{material_id}` 读取。 |

检测侧 `material.detection` 与 AI 的 `triage.attck_mappings` 来源不同；分诊 ATT&CK 与该分诊 Run 的解释工件匹配，是否可作当前判断还需看分诊有效性。执行状态、解释是否可读、当前指针/新鲜度、业务结论及人工结果分别表达。

### `content_json.ocsf_json` 的类型与空值

| 层次 | 实际约束和返回语义 |
| --- | --- |
| 数据库 / ORM | `alert_materials.ocsf_json` 为可空 JSONB；ORM 为 `object | None`，没有限制只能为 JSON 对象的约束。可存对象、数组、字符串、数字、布尔或 JSON null。 |
| 现行接收投影 | `socai2_projection.project` 选择字典类型的 `raw_event.ocsf_event`，或带整型 `class_uid` 的原对象；通常生成对象或 None。不把任意根部标量自动识别成 OCSF 文档。对象内部的 0、false、空列表不因真假值被整体删除。 |
| 保存助手 | JSON 字段只在 `v is not None` 时序列化，0、false、[]、{} 均保留。None 传空值，不以 `if v` 过滤。此结论不表示接收投影会生成所有 JSON 根类型。 |
| 指定材料读取 | 精确按租户、告警和材料 ID 查找，`raw_json/ocsf_json/enrichment` 经 JSON 解码返回，不强制转对象、不合并到当前版本。SQL NULL 和 JSON null 在此返回中均为 null；两者无法从该响应区分。 |
| DTO / HTTP | `ContentView.content_json` 是 Any；材料读取的实际包络含 `raw_json/ocsf_json/enrichment`，`content_text` 对应保存的 `raw_text`。适配器保留 JSON 类型及数值，不把 0、false、[] 转成缺正文。 |

页面判定正文存在应区分 null/未提供与已有 JSON 值。`{}` 是已保存的空对象；`[]`、0、false 是可读的 JSON 值，不能通过 `Boolean(value)`、只接收对象的 `record()` 或统一 `Object.keys(...).length` 将它们变成“未返回”。空对象可以说明没有字段，仍不可改写成未保存。类型可读不等于该值符合完整 OCSF 业务文档规范。

当前原文入口按所选材料的 `ocsf_json`，旧用例若仅把零值放在 `raw_json` 或 `content_text`，不再证明当前 OCSF 入口应显示它；应保留原失败原因，按当前字段和类型分别核验，不能为通过旧断言恢复旧入口。

富化判断与 OCSF 原文存在性分开。富化 null、空对象、仅版本标记或无内容项不能凭包络存在就当作补充数据；已有补充项中的有效 0/false 不丢弃。当前常规投影的 `enrichment` 自带 `schema_version/items`，包含第一融合结果引用、会话信息等保存项，不能仅凭它非 null 就声称已做威胁情报查询。本批按实际保存结构没有取得无富化的正式正例，具体页面空态仍需受控用例支撑。

结构依据：[数据库原定义](../../../services/api/migrations/123_socai2_page_data_model.sql)、[ORM](../../../services/api/app/models/socai2.py)、[接收投影](../../../services/fusion/app/services/socai2_projection.py)、[保存助手](../../../services/fusion/app/services/socai2_sink.py)、[内容 DTO](../../../services/api/app/socai2/page_contracts.py)、[精确 JSON 编解码](../../../services/api/app/socai2/material_json.py)、[HTTP 序列化适配](../../../services/api/investigation_http/adapters/material_response.py)。

### 解释引用的归属保证及现成来源

`EvidenceRef` 只有 `type/id/external/source_path/row_keys/role`，没有 `run_id`、`subject_id` 或 `content_url`。**现行 A 分诊发布路径的校验保证，与这个通用引用结构本身的能力要分开。**

- `alert_material` 必须属于该轮冻结 `source.members[].material`；A 的输入按同租户、同告警选择当前材料并冻结。发布时只接受完整材料、允许的来源角色及实际存在的字段路径；路径值不能为 null，但 0、false、[] 不因此失效。它属于本告警的冻结版本，不保证仍是详情当前最新版本。
- A 的 `artifact` 只接受本 Run 的输入快照，或按同租户、同告警、同 Run、工具步骤输出、schema 和完整性校验得到的工具回执。任意复用工件 ID、另一 Run 工件或无 Run 的来源工件不能直接冒充此路径允许的引用。历史分析/人工内容可位于本轮快照内，引用角色仍为 prior_analysis/human_statement，不能改成独立观察。
- 解释工件自身保存在同告警、同 Run，并在读取时核归属与完整性；读取方法不会再次遍历并验证全部历史引用。不能据通用 `EvidenceRef`，给任意旧/外部保存内容承诺“引用一定属于当前页面 Run”。Case/I 的引用规则也不能套用 A 的限制。
- 现成取源：本轮工件目录 `/analysis-runs/{run_id}/artifacts` 按真实 `id` 查其 `content_url`；步骤 `artifact_refs[]` 还带真实来源 `run_id/subject_type/subject_id/content_url`，支持跨 Run 复用。遇到这些来源链接应直接沿用，不能改拼当前 Run。材料使用已验证的同告警冻结 `material_id`；来源工件目录 `/alerts/{id}/records/source_artifacts` 的 `content_url` 属于无 Run 的来源读取，不混入当前 A Run。

因此，当前已验证 A 解释可以在核定其 `source_run_id` 后按上述发布保证解析；页面复用组件不能只依页面当前 Run 给所有引用拼路径。已有目录/步骤有真实来源时按真实来源；没有归属证据时保留无法定位，不添加猜测或新兼容接口。

依据：[A 发布校验及保存](../../../services/api/app/socai2/stage_results.py)、[冻结输入](../../../services/api/app/socai2/stage_inputs.py)、[解释读取](../../../services/api/app/socai2/stage_reader.py)、[通用引用 DTO](../../../services/api/app/socai2/baseline_contracts.py)、[步骤真实来源解析](../../../services/api/app/socai2/run_records.py)。本批对实际解释的材料引用检查了所选版本和字段路径；对工件引用先沿已有目录解析同 Run 归属，再仅补读尚未取得的被引用工件原件，核内容可用及字段路径。没有创建或声称验证跨 Run 样本。

## 读取结果及未验边界

**已有详情→固定 A Run→解释→引用→材料的读取支撑通过。** 当前正式配置、租户和发行与既有 profile 一致。所选材料的主体、ID、revision、来源范围、保留信息和正文包络均与保存元数据一致；原 A 选择器及授权批次证据未改。

| 直接验收 | 结论 |
| --- | --- |
| 原 A 回执与本次详情/指定 Run | 同一告警、`source_run_id`、结果冻结材料和解释工件一致，解释实际可读。 |
| 有界材料读取 | 最多三个既有告警、每个至多两个已有版本的上限保持；本次所选元数据及正文读回通过，没有创建新版本。 |
| 已存解释引用 | 实际同时含材料和工件引用；材料属于该告警冻结输入，工件在已保存目录中属于指定 Run。被引用原件实际可用，字段路径可解析。 |
| 真实无富化 | 本次有界材料均有 OCSF 内容及保存的富化项，未取得“OCSF 可读且无富化入口”的正式正例。保留缺证，不扩大为全库没有。 |
| 真实不同历史版本 | 限定主体中未定位到不同的已存旧材料；历史正文正例仍缺。指定 ID 精确读取合同已经核明，不以当前材料补证。 |
| 独立来源原件 | 本告警无 Run 来源目录在本次有界读取中已到末页，但没有按显式材料引用定位到同一冻结版本的来源工件。本项保持未证明，不把 A 输入/工具回执或当前来源分区冒充它。材料自身 OCSF/原始字段及 A 引用原件已按各自范围读取。 |
| 离线类型与现有用例 | 既有材料响应测试 1 项通过；实际 DTO/适配器的 null、{}、[]、0、false、空串及含有效空值对象共 8 项类型/空值检查通过。这是离线序列化验证，不是新增真实材料样本。 |

`/alerts/{id}/records/sources` 只返回当前材料的来源引用；指定旧版本材料的 `metadata.source_version/source_scope/retention` 来自该旧版本，但不能把当前来源目录标成旧版本来源。历史版本目录和同版本来源新接口保持后续范围。

最终受控交接：`.local/validation/alert-detail-material-support-20261124-01/page-handoff-private.json` 汇总固定 A 链、所选材料、引用真实来源链接和补读状态。原 `page-selector-private.json` 包含所选材料各自路径与可用性；`explanation-reference-selector-private.json` 保留引用解析阶段的归属依据；`citation-readback-01/readback-private.json` 是后续引用原件补读。原件正文留受控文件，不进入工程回执。公开 [工程检查与读取边界](../../../docs/operations/evidence/alert-detail-material-support-20261124-01/README.md)。

本步没有发现需要修改服务端业务代码的直接阻断，没有新增接口、模型调用、数据、发布或推送。页面接线与浏览器验收由 SpiritHub/组织者另行核定；无富化、旧版本和同版本来源缺证不写成已通过。
