# I 事件诊断输出结构审计与最小方案

状态：源码/结构审计与推荐方案已通过统筹正式独核，方案未实施；未修改提示、Schema、接收器、预算或保存合同。沿用本 change，只补审计与设计，不新增空规格、不改变整个 change 的规格设置。报告仅依据明确源码/Schema 和替身检查，不将业务/模型正文作为证据；本步骤不发起业务查询或模型调用，不操作数据库或 21。

## 1. 结论与本轮边界

当前 I 并非只让模型给出事件结论：它还必须对每个选入成员输出 `assessment`、状态、引用和限制。成员条数被 Schema 固定为 N；当前接收器只有收齐诊断四字段和有效成员全集才生成 `IncidentOutput`。这构成明确的结构性增长项，也让事件结论依赖逐成员输出完整。它不是线上实际输出增长测量，更不能据此断言某次失败由输出长度造成。

程序已拥有成员目录、选入数量、身份/来源映射；**这些事实不能证明模型已分析成员，也不能替模型生成成员判断**。建议把输出重心放回事件判断，保留由模型明确声明并经程序校验的短成员状态与证据，取消强制逐成员长正文。此方案涉及内部合同与下游材料语义，不能仅改一句 prompt 或用程序补全文冒充兼容。

## 2. 当前真实调用链

以下均为仓库源码事实，未推定远端已加载该版本。

| 环节 | 实际责任与依赖 | 源码入口 |
| --- | --- | --- |
| 提示 | 当前提示来自 `incident-input-v1.json.system_prompt`，规定 summary 写主要行为、conclusion 写判断与理由，逐成员给简短 assessment；再拼接独立等级意见与事件判定规则。旧 `incident_diagnosis_contract.PROMPT` 不能代替实际提示审计 | `incident_model_boundary.py:202`、`incident-input-v1.json` |
| Schema | `candidate_schema` 从旧字段约束生成别名输出：`diagnosis`、`members`、`findings`、`open_questions`，再加 `severity_opinion`、`business_verdict`。`members.minItems=maxItems=N`，并非可省略的目录回显 | `incident_output_adapter.py:39`、`structured_output.py:101` |
| 调用与预算 | 一次 I 请求；`max_tokens` 取现有 `model.output_tokens["I"]`，先计量实际请求再做既有预算检查。本审计不读取运行值、不提高预算 | `incident_diagnosis_executor.py:102` |
| 协议与接收 | 先检查单 choices、finish 为 stop/length、正文/工具协议，以及已报告且不超预留的 usage，再按闭合单元接收。实际主路径是 `ai_delivery_store.receive_payload → ai_stage_delivery.receive`，不是直接调用旧 `parse` 就完成交付 | `ai_delivery_store.py:17`、`ai_stage_delivery.py:106` |
| 接收门槛 | `diagnosis` 必须有 summary/conclusion/source_ids/limitations；有效 members 的身份集合必须等于冻结目录。缺成员时可保留独立有效单元，但没有正式 `IncidentOutput`。not_reviewed 仍是显式成员行，不等于已分析 | `ai_stage_delivery.py:198` |
| 装配 | 程序恢复成员真实 ID、来源引用和范围；每条成员 assessment 投影成 `member:<身份>` finding，再合并事件级 findings，问题编号也由程序生成 | `ai_stage_delivery.py:59`、`:92`、`:211` |
| 保存 | `finish` 将 summary、diagnosis.conclusion/findings/source_refs/limitations/program_facts/delivery_assessment、open_questions 和业务判定保存。`assess` 只依据经接收的成员状态算覆盖与待核；缺失/not_reviewed 不能报完整。等级意见另经原单元/来源校验、候选与应用流程 | `stage_results.py:327`、`incident_delivery.py:32`、`subject_risk_opinions.py:128` |

`severity_opinion` 和 `business_verdict` 在 Schema 必填，并分别接收；不能把“诊断四字段 + 成员全集可形成核心结果”误写成“其他字段不用接收/缺失仍完整”。单元缺失/无效、交付完整性、业务判定与质量各自保留。

## 3. 哪些字段随成员增长

| 输出块 | 当前约束与增长来源 | 判断职责 |
| --- | --- | --- |
| `members[N]` | 强制 N 行；每行 assessment 与 limitations 必填。Text 上限 3000 字符，limitations 至多 10 条；这是宽松 Schema 上界，不是实际长度/token 数 | 模型声明该成员是否分析、判断是否未决；程序只能校验和统计 |
| `diagnosis` | 固定四字段；summary/conclusion 各使用 Text，limitations 最多 20 条。若正文重复逐成员复述，仍可变长，但没有 Schema 要求 N 段 | 事件层面的主要行为、解释、依据与重要限制 |
| `findings` | 最多 8 条，每条 statement/limitations 较宽；成员范围与来源数组可随覆盖范围增长。保存结果另拼上 N 条成员 finding | 只写新增事件发现、差异或冲突，不能把相关性当因果 |
| `open_questions` | 最多 10 条；每条 text、材料需求与成员范围仍占输出 | 只写影响结论的必要待核问题，不为填满列表制造事项 |
| `severity_opinion` | 一个独立单元，不要求逐成员重复；reason 为 Text，confirmed/potential 各至多 12 条，limitations 至多 12 条，各正文均使用宽 Text。它也占同一答复预算，不能漏审 | 安全影响等级及已确认/潜在影响依据，与恶意概率或执行成功分开 |
| `business_verdict` | 单个枚举；**没有新增 rationale 字段**，理由要求使用已有结论/依据/限制表达 | 本轮范围的 malicious/benign/false_positive/needs_review 判断 |

约束来源：`incident_diagnosis_contract.py:31`、`incident_output_adapter.py:26`、`severity_opinion.py:16`、`business_verdict.py:14`。固定模型输出上限不会消除 N 行必填正文的竞争；字符上限不等于 token 配额或实际输出。

## 4. 模型判断与程序恢复的边界

| 模型必须明确给出 | 程序已有或可确定恢复 |
| --- | --- |
| 事件结论、理由、证据不足与相互冲突 | Run/主体/版本/保存身份、冻结成员目录及选入/未选入数量 |
| 成员的 summarized/unresolved/not_reviewed 声明与所依据资料 | 别名到真实 ID、来源 ID 到原件/路径、范围合法性和重复/缺失校验 |
| 事件发现、未决问题、等级意见与业务判定 | F/Q 编号、原件 hash、使用量状态、调用/交付状态及保存时间 |
| 哪些资料支持哪项判断，是否存在限制/反证 | 对已经接收的成员声明计算 analyzed/not_reviewed/missing/unresolved 目录与数量 |

有材料不等于已阅读；有来源引用不证明正文真实；“未确定”不等于“未阅读”。程序不得根据成员数量、原告警分诊、最高等级或缺正文自动填 summarized、benign 或任何 assessment。

## 5. 建议的最小结论型方案（未实施）

保留一次 I 调用、现有输入、现有预算和核心交付门槛，优先减少要求模型生成的重复正文。仍有 N 行状态/来源引用的少量线性开销，不承诺输出长度成为常数：

1. `diagnosis` 继续保留四字段：summary 只概括事件行为，conclusion 集中表达整体判断及理由，source_ids 只放支持这份判断的证据，limitations 只列影响整体结论且未在局部交代的重要缺口。
2. `members` 继续逐一明确覆盖 N 个冻结成员，但最小候选行仅保留 `alert_ref / state / source_ids`。不再强制每行生成 assessment 和 limitations。它是模型的覆盖声明，不是程序从目录自动生成；缺行、重复、来源越界、不支持的分析状态仍按原接收边界处理。summarized/unresolved 必须有该成员的可见依据，not_reviewed 不冒充已分析。
3. 有业务意义的成员差异、冲突与限制由模型写在已有 `findings/open_questions` 中并声明真实范围；事件结论本身仍保留必要依据。没有实际发现/问题可给空数组，不机械为每个成员补一条 finding、问题或模板说明。
4. `severity_opinion` 保留独立等级及依据职责；reason 只解释影响等级，confirmed/potential 与 limitations 只保留必要项，不复制全部诊断或逐成员报告。`business_verdict` 保持枚举，理由留在 conclusion。本轮只登记共享 Text 上限过宽及总预算竞争；下一实施设计在现有 I 配额内协调各正文约束，不增加预算，不凭未测结果报效率收益。
5. 程序从真实声明生成覆盖统计，恢复身份/来源/编号与保存合同；停止将“只有状态与引用”的成员行合成为有正文的 member finding。实际事件 findings 保持原范围，不改成某个成员独有事实；旧工件和旧投影按原版本可读。

这是一个明确的新成员输出形状候选，而非已兼容的替换。下一步若采用，需要先补规格/版本与必要保存/读取接线，再在同一窄步验证；本轮没有修改其 Schema 或尝试用空字符串、占位正文和默认判断绕过旧必填条件。

## 6. 兼容影响与未验边界

| 依赖 | 影响和必须保留的含义 |
| --- | --- |
| 内部生成/接收 | `BoundaryMember` 与候选 Schema、闭合单元接收、`project_incident` 要按版本共同调整；仅改 prompt 会仍被旧必填约束要求输出。核心诊断门槛与显式覆盖保持，成员行缺正文不能当成虚构的发现 |
| 已存诊断与分析接口 | `IncidentOutput.findings → diagnosis.findings` 当前混有成员评述。新方案若只保留事件发现，JSON 列表类型虽可不变，内容语义仍变化；`delivery_assessment.member_coverage` 和 review_items 必须继续来自真实成员声明。`StageReader` 将这些诊断及 analysis_coverage 对外返回，不能宣称无合同影响 |
| 事件详情摘要 | `PublishedIncidentDiagnosis` 读取 summary/conclusion/open_questions，业务判定单独读取；可保持现有字段名/类型/空值语义，但这只说明已审服务端合同可保留，**未核真实 8181 页面实现**，后续仍需对应字段接线核对 |
| Case 当前首选材料 | `baseline_context.capture → case_incident_material.freeze/project` 从 `stage_delivery.retained_units/use.material_paths` 与 `model_response.received_analysis` 提取 analysis_material，`case_input_text.py:220` / `case_update_inputs.py:35` 优先消费它。project 按 diagnosis.* / members / findings / open_questions 还原；成员状态单元不能继续被标作有实质正文的发现。须同步版本、来源范围和正文 hash 解释，旧工件原内容不改写 |
| Case 既有诊断后备路径 | 无上述材料时，`case_input_text.py:230` 把 diagnosis.findings 作为 prior_analysis；`case_incident_scope.py:55` 依赖实际分析覆盖而非目录；`case_update_inputs.py:35` 读取保存的 member_coverage。删除成员正文会改变可用先前判断与变化比较，不能自动补全文或扩大范围 |
| 动态查阅页 | `frozen_sources.mjs:82` 按 `$.members[...]` 统计保留成员单元，`execution_flow.mjs:254` 读取 assessment/statement/text 等正文。新形状需要明确显示模型声明的状态与证据，不能把“保留了一个状态单元”显示为已有成员结论。当前 4177 静态快照和真实 8181 均未验 |
| 等级意见 | `subject_risk_opinions` 独立校验/保存/应用，候选版本和来源须保持；不能因压缩诊断而掉落等级意见，也不能让等级替代业务判定 |

本轮没有改告警分诊字段、事件/Case 取数合同或历史材料。上述候选若进入实施，需要明确受影响的成员结构、`diagnosis.findings` 语义、页面与 Case 消费范围；不能以“内部压缩”名义追认合同变更。本轮不新增算法、自动续写或补偿逻辑。

## 7. 证据与验收

统筹已执行必要的 4 项既有结构检查：无 members 不形成正式结果、missing/not_reviewed 覆盖为 partial、恢复冻结身份与来源；并用 1/2 个纯合成成员别名生成 Schema 核对成员数量与必填约束。证据位于 `.local/validation/incident-output-structure-coordinator-20261128-01/`。不重复跑回归、不新增测试框架。

[统筹正式独审](../../../docs/operations/evidence/incident-output-structure-coordinator-20261128-01/review.json)已通过，26 项源码指纹与当前源一致；验收范围仅为结构审计和未实施方案。代码与 S3 证据保持冻结，不启动方案实施或新增模型测试。

本审计的源指纹、必要检查引用与正式独审状态见 [证据目录](../../../docs/operations/evidence/incident-output-structure-audit-20261128-01/README.md)。报告仅依据明确源码/Schema 和替身检查，不将业务/模型正文或录制材料作为证据；不以此概括其他协作步骤的搜索过程。检查只证明当前结构和接线事实，不证明模型正文质量、准确率、线上输入/输出大小或压缩收益。最小方案尚未实施，真实 PG/HTTP、4177/8181、远端版本及真实模型均未验。
