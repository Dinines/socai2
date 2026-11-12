## ADDED Requirements

### Requirement: Model inputs select business information for the stage goal

每个模型环节 SHALL 先明确使用模型的原因、待完成的业务判断和输出用途，再按字段选择有助于该目标的材料。程序 MUST NOT 将原始记录、数据库对象、工具回执或上游请求整包序列化透传；只换格式、去重或未超限不构成完成。完整原件、身份、范围、版本和执行台账保持后台可回查；所选业务事实与正文保留原值/原文和角色，必要依据及反证不得因未被前序模型引用而丢弃。

#### Scenario: A model input contains an internal object index
- **WHEN** 原对象索引同时含 raw_value、normalized_value、内部索引角色和资产匹配状态，当前业务字段/对象目录已经提供同一对象
- **THEN** 按本步目标选择业务对象与必要属性，省去重复登记和内部匹配字段；原身份与来源映射后台保留，不把这份结构原样传入模型

### Requirement: Analysis models receive query results instead of execution ledgers

配置 A/I/C3/Deep/C6 输入 SHALL 只展示工具名称和程序确定的查询结果，并按业务字段提供返回记录。未查询、失败、结果未知、无结果和有结果必须区别；原因、执行说明、参数、查询时间窗、来源范围、上限、统计/截断标志和回执限制 SHALL 留在后台，不逐项打印或改写成解释性段落。引用编号及原角色保持，查询绑定和返回记录主体由程序继续校验；材料读取只提供可用状态，原缺失字段清单留后台。

#### Scenario: Intelligence was not queried
- **WHEN** 配对的威胁情报回执为 skipped，原因是无支持的冻结对象
- **THEN** 在既定成员块内只显示引用短号及“威胁情报：未查询”，不显示原因、时间窗、来源范围、上限、截断和限制说明；原回执与原失败保持可查

#### Scenario: Query has data or its result is unknown
- **WHEN** 查询有返回、失败或无法确定结果
- **THEN** 程序提供对应状态；有返回时另给按目标选择的业务记录，不用工具执行统计代替业务内容，不将失败、缺失或截断的零条结果写成查空

#### Scenario: Followup stages reuse earlier query results
- **WHEN** C3/Deep/C6 承接 A/C2 或补查结果
- **THEN** 每份回执只展示一次简短结果，不再次追加完整回执、共享查询限制或重复背景状态摘要；后台 source_map、原记录及结果恢复所需执行事实保持

### Requirement: Alert triage selects business fields before rendering its input

配置 A 模板 SHALL 根据单告警性质判断的目标选取业务字段。已识别的对象登记、接入外壳、来源范围统计和融合执行引用留后台；同材料、同含义且同值的重复对象/字段及可解析结构化文本副本不重复展示。存在不同值或独有业务属性时 SHALL 保留，不按样例值删除未知业务信息或有意义的零、false、空列表。所选字段沿原来源恢复身份和引用，原材料与公开分诊合同不变。

#### Scenario: Historical matches contain only catalog metadata
- **WHEN** A 的历史查询按对象多次匹配同一历史记录，记录仅含标题、等级、时间和厂商，且没有业务扩展、历史判断或人工正文
- **THEN** 此目录记录及匹配参数后台保留，不作为该告警的判断材料逐行上送；有独立业务字段或判断/人工正文的记录仍按原角色选入，不按良恶结论筛选

#### Scenario: Historical judgments and human statements have administrative envelopes
- **WHEN** A 选入历史分诊或人工信息
- **THEN** 程序按相应结构剔除执行身份、UUID及后台键，保留所选原文及记录背景；同回执同身份版本的重复匹配可共享正文，不同版本、角色或内容不合并

#### Scenario: A serialized material duplicates structured business fields
- **WHEN** raw_text/raw_data 是可解析对象，部分字段已在同材料结构字段中以相同值提供
- **THEN** 程序仅选入有独立业务内容的剩余字段，并保留其原文本来源；非结构化正文不语义改写，未知业务字段与真实零值等仍可见，原文本留后台不整包透传

### Requirement: Incident input selects member facts and useful prior context

配置 I 模板 SHALL 围绕既定事件的整体行为、成员意义和待核事项，提供各成员业务事实、已核验有效的 A 判断及必要背景。已识别接入外壳、来源范围台账、重复字段及无业务内容的历史目录 SHALL 留后台。筛选 SHALL 保留有业务扩展、历史判断、人工反馈或被有效 A 的结构化引用指向的历史记录，不按良恶结论或模型是否引用筛掉其他有用材料；不从旧正文猜测引用，不重写判断和人工原文。

#### Scenario: A history receipt contains repeated catalogs and useful context
- **WHEN** 多个成员冻结的历史查询包含纯标题/时间/等级目录及带判断、人工陈述或业务字段的记录
- **THEN** 无独立内容且未被有效 A 明确引用的目录不上送；其余记录保留原角色及背景，同一历史身份和完整版本的正文可在独立历史区展示一次，但每个引用仍标明原成员和原回执路径，不扩大来源范围

#### Scenario: Member evidence contains copies and administrative fields
- **WHEN** 同一成员材料的结构字段、已识别接入外壳或结构化文本副本重复表达相同值
- **THEN** 程序按同材料和语义字段合并展示，保留有独立内容的业务字段及0/false/有效空列表；不同成员事实不按值相同合并，普通正文原样保留；失效或缺失 A 不作为有效前序判断

### Requirement: C3 selects facts and knowledge for the initial investigation

配置 C3 输入 SHALL 服务于首轮调查解释和必要补查，保留成员业务事实、有效 A/I 原文及其支持/反证、相关人工信息和按已配置用途选择的知识。程序 SHALL 按已识别结构剔除重复对象/时间、接入外壳、纯目录历史及知识检索/索引台账，不能整包透传或语义改写所选正文。原件、角色、记录主体、成员范围和来源映射保持，输出及存储合同不变。

#### Scenario: Catalog history and duplicate object registries crowd the prompt
- **WHEN** C3 同时收到对象目录、重复索引行和历史查询目录
- **THEN** 已表达且无额外业务属性的登记/时间副本省去；未被前序有效引用且无业务内容的历史目录留后台；有内容、人工意见和必要支持/反证保留，同身份完整版本可共享正文但不合并引用范围

#### Scenario: Retrieved knowledge includes internal matching and source records
- **WHEN** 已按 C3 用途选入的知识含适用性计算、文档块索引或历史同步外壳
- **THEN** 只向模型提供正文、实际业务条件、必要来源名称和用途；历史事件/行为与历史判断/人工陈述分别表达，原值与有意义的0/false/空列表保持，不把相似度、同步状态或历史结论当本案事实

#### Scenario: C3 has no available tool binding
- **WHEN** 当前工具目录没有可用查询候选
- **THEN** 输入只说明无可用查询候选，不列全套不可执行能力/参数；有候选时提供选择所需业务描述及原绑定，后台目录和输出约束不变

### Requirement: Structured knowledge reaches the model as selected intact business fields

系统 SHALL 对新导入的完整 JSON 对象/数组保留完整原文块，不以字符边界切断结构；普通文档继续已有分段。调查知识索引 SHALL 继续应用已配置内容上限，超限明确拒绝，不提高预算或删除原文来适配。C3/Deep/C6 SHALL 在原件检查后按已识别结构选择技术说明、适用条件和调查方法，移除内部引用/索引字段，保留原业务值与正文、未知业务扩展、0/false/有效空列表。HTTP 字段合同、数据库表、原知识记录和历史 Run 保持。

#### Scenario: A complete JSON knowledge document exceeds the ordinary text chunk boundary
- **WHEN** 新导入 JSON 的完整对象/数组超过普通段落长度，但仍满足调查索引配置上限
- **THEN** 保存一个完整原文块并可由既有索引/读取使用；模型输入按结构字段投影，不能传入截断的半个对象

#### Scenario: An earlier frozen Run contains partial JSON chunks
- **WHEN** 旧知识记录或 Run 已保存截断片段，缺少可验证的完整文档身份
- **THEN** 不自动拼接、覆盖或重新派发；新导入资料形成新记录，离线示例与旧实际输入明确区分，不能以新示例追认旧 Run 成功

### Requirement: Deep and C6 select inputs for their separate decisions

Deep SHALL select frozen business facts for its bound question and member scope, the applicable prior answer/findings and evidence needs, relevant human material and knowledge, and their explicit support/counter dependencies. C6 SHALL select whole-case facts, effective C3/Deep business conclusions with their necessary evidence, new query results and relevant human/knowledge context. Both SHALL preserve original prose, values, roles and source scope, apply structural field selection before rendering, and leave duplicate registration, catalog-only history, execution ledgers and omission statistics backstage. HTTP/storage contracts and historical artifacts SHALL remain unchanged.

#### Scenario: A question concerns fewer members than the Case
- **WHEN** Deep is bound to a subset of members
- **THEN** unrelated member facts and other question answers are not included by default; common or unknown-scope useful context remains, and explicit cross-member supports/counters are restored with their original scope rather than relabelled as local evidence

#### Scenario: Final synthesis consumes previous answers and original plans
- **WHEN** C6 consumes accepted C3 and Deep results
- **THEN** business conclusions, alternatives, gaps, necessary sources and selected historical comparison remain visible; program-owned coverage answers and execution parameters are omitted, and a duplicate original plan is presented once as business evidence needs rather than repeated execution instructions

#### Scenario: Structural input selection is applied to old frozen material
- **WHEN** an offline preview rebuilds earlier materials using the new selectors
- **THEN** the preview identifies its offline configuration binding, preserves the originals and verifies retained references and dependencies; new inputs are not presented as a new model execution or a successful saved conclusion

### Requirement: Bounded tool results retain record associations in compact business views

Deep/C6 SHALL select business fields from bounded frozen query results before rendering. Configured internal identity fields SHALL stay backstage unless required by an explicit prior dependency. Identical business fields within the same frozen query, role and member scope MAY share presentation only while every original record key and citation remains visible and individually resolvable. Different values, conflicts, roles or queries SHALL NOT be merged. Unknown business extensions, zero, false and meaningful empty lists remain available. Existing row/storage/request limits stay in force; exceeding mandatory input capacity SHALL stop dispatch rather than truncate prose or invent a successful analysis.

#### Scenario: Several returned records repeat host and process information
- **WHEN** one frozen query returns records with identical business fields and other fields that differ
- **THEN** the common values can be shown once with every associated record and source number, while differing times, actions, results and contradictions remain separate; stored records and their original scopes are unchanged

#### Scenario: An internal identifier is cited by an earlier accepted answer
- **WHEN** a prior answer explicitly cites a query field normally excluded as internal identity
- **THEN** the exact frozen dependency remains visible with its original role and record association instead of silently dropping or relabelling the citation

### Requirement: Identical frozen history rows share presentation without losing citations

I/C3/Deep/C6 SHALL 合并同一冻结查询回执内、同一历史记录版本、同角色与适用范围、展示值逐值相同的重复行正文，并列保留各原始来源编号及其路径。完整回执、数量、原文和前序依赖 MUST 保持可回查；不同身份、版本、角色或内容不得合并，不得合并来源适用范围。I/C3 的独立历史区可共享同一身份/完整版本的正文，保留每份原引用及其成员范围/记录主体；这不改变各来源的归属。此变化仅去除重复展示，不提高输入或 Run 预算、不裁正文，也不将相似记录当成同一事实。

#### Scenario: Matching the same historical alert by host and user repeats its row
- **WHEN** 同一回执的两行拥有相同 record_id、完整 record 和展示值，且角色与范围相同
- **THEN** 模型看到一次正文及两个来源编号，两编号仍分别解析到各自原行，前序依赖均可恢复；查询返回行数保持原值

#### Scenario: Final input repeats material fields and selected business limitations
- **WHEN** Deep/C6 的同材料、同语义字段、同角色/范围的值重复，或按目标选入的非查询回执来源有逐值相同的业务 limitations
- **THEN** 材料正文并列保留各来源编号，必要的业务限制可共享展示；查询执行限制只在后台留存，不经共享段落重新上送。原记录、引用映射与前序结论不改写，不合并不同字段/值/来源范围

### Requirement: Fixed A and I citation rejection has one bounded correction

配置 A/I 模板时，对完整、可解析且仅包含已知来源/角色/成员范围错误的回复，系统 SHALL 在同一 Run 内最多反馈一次具体错误，并使用相同冻结输入、来源编号和 Schema 重新接收完整回复。原答、错误及纠正请求/原答分别保存，第二次仍执行完整校验；MUST NOT 靠程序去重、补引用、改判或放宽成员范围使原答通过。每次调用均重新核对已冻结的调用数、总 token 和 deadline，未知执行、截断、协议/形状/安全失败不重派。

#### Scenario: A repeats a visible source and I cites a different member
- **WHEN** 配置 A 返回重复引用，或 I 的问题/成员引用了声明范围外的来源，且本 Run 尚有预算
- **THEN** 反馈使用模型实际看到的字段路径、短号及来源角色/成员映射；最多一次纠正，纠正通过后按原保存/采用合同交付，失败仍保留原局部结果与错误

#### Scenario: Correction has no remaining budget or its execution is uncertain
- **WHEN** 已达到一次纠正上限、调用/token/deadline 不足，或发生未知/不完整执行
- **THEN** 停止额外派发并如实记录原因，原判断与原件保留，不另建 Run 重采样

### Requirement: Case citation feedback covers required empty references

C3/C6 的有界反馈 SHALL 与接收器一致识别已分析或未决成员的依据缺失，以及 C6 建议空引用。生成约束、校验拒收和局部保留仍各自生效；MUST NOT 因某错误漏报而跳过可用的一次纠正，也不得因此新增纠正次数或捏造来源。

#### Scenario: A final recommendation lacks evidence
- **WHEN** C6 完整原答中建议的引用为空，或 unresolved 成员没有所需本案依据
- **THEN** 在原一次纠错中指明具体路径；没有充分依据时模型可删除无据建议或明确未分析，但程序不改写原答。预算不足或仍失败按原局部结果/拒收规则保存读取

### Requirement: Configured alert input validates the actual rendered messages

配置 A 模板时，来源构造 SHALL 保留原件字段检查与准备上限，随后校验本次实际发送的完整模板消息。未使用的旧 JSON 消息 MUST NOT 因自身序列化长度阻断符合配置模板限制的输入；旧模式仍按原消息检查。不得放宽安全判定、提高阈值、截断原文或重派已失败 Run 来代替修复。

#### Scenario: Unused legacy serialization exceeds its message cap
- **WHEN** 同一合法来源的旧 JSON 消息超过消息上限，但实际模板文本、来源和预算检查均满足
- **THEN** 配置路径生成并检查实际模板；旧模式仍拒绝超限消息，任何原件或实际模板的非法内容仍按原规则拒绝

#### Scenario: A configured Case message fits but JSON quoting exceeds the cap
- **WHEN** 配置 C3/Deep/C6 的实际消息字符串满足原长度与内容检查，但额外 JSON 引号及转义使检查副本超过长度上限
- **THEN** 检查实际消息字符串及重叠窗口，原件检查保持；不得降低敏感内容检查或提高长度阈值，真正超限的消息仍拒收

### Requirement: Fixed investigation knowledge references remain contextual without covering current members

固定 C3/C6 SHALL 允许本轮已选知识作为其查询适用成员的辅助解释、非 observed 推理及补查参考，保留原历史主体、版本及来源角色；这些引用 MUST NOT 被映射成本案观察，也不得计入成员或最终结论/影响的依据覆盖。知识与本步的目的和成员关联 SHALL 同时来自同一检索出处；程序接收、局部保留及有界纠错诊断使用一致规则。原始材料、人工陈述和前序判断的既有角色/范围校验保持，历史原答和失败不回写。

#### Scenario: A member explanation compares current observations with a historical card
- **WHEN** 模型为 A3 同时引用本案材料及本轮按 A3 主题检索的历史卡，原历史成员不属于本案
- **THEN** 保留两种来源的不同身份并允许辅助比较；只有非知识的本案来源计入 A3 覆盖，历史记录不被改成 A3 的观察

#### Scenario: A conclusion relies only on historical or technical knowledge
- **WHEN** 已分析成员或结论/实际影响声明覆盖某成员，但该成员的引用只有知识
- **THEN** 拒绝缺少本案依据的覆盖并给出同一缺口诊断；不得补引用、缩小原答范围或追认旧失败为成功

#### Scenario: Deduplicated origins have different purposes and members
- **WHEN** 同一知识块分别被 A1 的技术解释查询和 A2 的取证指导查询命中，当前 Deep 只针对 A1
- **THEN** 不把两个出处的条件拼接成适用于 A1 的取证指导；必要前序引用依赖仍按原规则保留且注明其角色

### Requirement: Configured Case followup model boundary
The system SHALL provide configured Deep and final-delivery calls with frozen business materials, effective prior judgments, and their explicit evidence dependencies, while restoring program-owned output fields without changing the stored Case contract.

#### Scenario: Prior judgments and citations are handed to the next stage
- **WHEN** a configured Deep or final-delivery request is assembled
- **THEN** effective C3 judgments and applicable Deep answers retain their original prose and scope, structured support and counterevidence map to currently visible sources, and unavailable dependencies are explicitly recorded instead of invented or silently inherited

#### Scenario: Program-owned fields are restored
- **WHEN** a configured model response is received
- **THEN** the program restores the bound Deep question identity, C6 member/object aliases and recommendation identities, and the fixed initial comparison where no historical result exists, before applying the original validation and persistence contract

#### Scenario: Deep sees query status without citing it as substantive evidence
- **WHEN** a configured Deep request includes execution receipts alongside business sources
- **THEN** the receipts remain visible with their original role, but the generated support/counter source enumeration excludes execution receipts in agreement with the existing receive validator; if no eligible sources exist the arrays can only be empty, and an unresolved answer must still explain its limitations

#### Scenario: Final conclusions use substantive references while analysis retains execution context
- **WHEN** a configured C6 request includes execution receipts
- **THEN** conclusion, comparison, impact and recommendation reference slots exclude those receipt IDs as required by their existing parser, without narrowing the analysis slots that may describe query coverage or removing receipts from the input

#### Scenario: Final recommendations cannot be generated with an empty evidence array
- **WHEN** C6 emits a recommendation
- **THEN** its generation schema and receiver both require at least one visible substantive source; no extra model call, invented reference, or rewrite of an old rejected answer is used to satisfy the rule

#### Scenario: Old execution remains readable
- **WHEN** a Run has no configured Case boundary or a previous stored result is read
- **THEN** the original execution/read contract remains available and no historical source, answer, state or profile is rewritten

### Requirement: Case C1 freezes paired query receipts for configured C3 input

配置选择新版 Case 输入时，C1 SHALL 在读取当前成员及有效 A 指针的同一快照中冻结该 A Run 实际工具步骤的回执，登记版本、原工件身份、完整性及逐路径来源角色。C3 SHALL 从冻结副本生成结构模板文本并恢复原七类输出合同；MUST NOT 从“最新查询”补写旧快照或将 prior_analysis/execution_receipt 提升为 observation。现有数据库表列、原字段与原 GET 合同保持。

#### Scenario: Query receipt and selected triage belong to the same execution
- **WHEN** 新 Case profile 启动且当前 A 输入有效、工具步骤 output 指向已保存回执
- **THEN** C1 冻结精确配对的回执及返回内容，C3 按程序状态区分未查、失败、查空和有返回，并引用本 Run 的冻结路径

#### Scenario: Historical context has no query extension
- **WHEN** 读取没有查询扩展版本的旧 C1 快照
- **THEN** 按旧合同读取，不查询或补写后来回执，不声称旧模型已看过这些材料

#### Scenario: Extended input freshness changes
- **WHEN** 有效 A 配对、实际回执或支持的扩展版本与冻结来源不符
- **THEN** 应用侧当前判断读取、采用、系统收尾和证据目录统一返回非 current，保持原判断与历史工件；旧 V1 数据库函数不单独代替扩展检查

#### Scenario: C3 restores aliases and keeps independent valid units
- **WHEN** 配置模板输入后的 C3 返回成员/对象短号和七类业务内容
- **THEN** 程序只恢复冻结身份与来源关系，沿现有绑定、角色、范围及局部校验处理，不补造模型结论；有界空引用纠正仍使用模型看过的短号命名空间

### Requirement: Case input candidates preserve frozen material and prior-analysis provenance

Configured Case input candidates SHALL render the complete selected material through structural rules, preserve meaningful unknown values and original prose, and distinguish observations, labels, prior analyses, human statements and execution receipts. Incident findings and open questions MUST retain their own declared scope. Additional A receipts MUST match the frozen accepted triage Run, tenant and alert and remain distinguishable from the historical C1 snapshot. Candidate short identifiers MUST restore the existing analysis contract without inventing judgments or changing stored originals. Offline conversion is not a model, storage or deployment acceptance result.

#### Scenario: A cloud or email record has no fields in the old scalar projection
- **WHEN** its complete frozen material is rendered by the candidate
- **THEN** nonempty business structures, meaningful zero/false/empty values and original text remain addressable, with structural omissions recorded separately

#### Scenario: A shared incident finding is relevant to one Case member
- **WHEN** the candidate presents that finding
- **THEN** it retains the original scope and prior-analysis role, marks any scope outside this Case, and does not promote the finding or its unavailable references into direct observations

#### Scenario: A historical triage claim disagrees with a paired execution receipt
- **WHEN** saved receipts from that same frozen triage Run are included in an offline candidate
- **THEN** the original claim remains unchanged, the verified execution state is shown separately, and the candidate records that these receipts were not in the original C1 snapshot

#### Scenario: Nested wrappers repeat metadata and empty optional fields
- **WHEN** a candidate renders material, prior findings, scopes, receipts, program facts and tool descriptions
- **THEN** configured structural paths determine which administrative or empty optional fields stay in the ledger; unknown business values and meaningful zero/false/empty values survive, prior prose is not rewritten, and shared presentation never merges distinct evidence identities
- **AND** a same-material offline comparison records the removed paths, retained observations, scopes, references and complete request sizes without claiming model quality or production acceptance

#### Scenario: A known field is presented by its business meaning
- **WHEN** a configured structural path and value type match an existing reviewed dictionary
- **THEN** the candidate may render the dictionary meaning while retaining the original value and source mapping; unknown values and unrelated nested paths are not interpreted by key-name similarity
- **AND** a tool's technical return-field list stays in the ledger only when its business capability description is complete and all those fields are recognized; otherwise the list remains visible

### Requirement: Configured event model boundaries preserve frozen business data and stored field contracts

启用事件输入输出profile时，I SHALL 从完整冻结成员材料按结构模板生成模型输入，保留非空业务说明、原始正文、当前有效A理由和未知业务字段；已知管理字段/空可选值及重复索引 MAY 留后台。查询回执 SHALL 来自冻结采用A的同Run、同租户/成员且由实际工具步骤指向，随I输入冻结并校验完整性。程序 SHALL 提供真实查询执行事实，历史判断不得代替回执；新快照新鲜度包含回执，旧输入继续按原合同比较。四块模型输出 SHALL 由程序恢复原身份及既有保存字段，不修改原告警描述、关系或历史结果。策略、模板、指令及版本指纹 SHALL 走配置与发布来源；完整请求计量和局部有效内容保留规则继续适用。

#### Scenario: Prior triage says empty but its actual query was skipped
- **WHEN** 当前有效A理由声称查空，而同Run回执为skipped且returned_rows为null
- **THEN** I输入保留A原文为已有分析，另提供未执行查询的回执，不补0行或改写原理由；查询返回与回执保持各自角色

#### Scenario: Event output uses short member aliases
- **WHEN** 模型按profile返回diagnosis、members、findings、open_questions，引用与成员通过原校验
- **THEN** 程序恢复原UUID、生成稳定形状的成员/发现/问题编号，保存原summary/conclusion/findings/source_refs/open_questions/limitations；原GET可按原身份读取描述、成员、材料、诊断与来源工件

#### Scenario: Existing event results are read after selecting a new profile
- **WHEN** 已存在不含查询回执版本标记的旧I冻结输入，进程改选新版profile
- **THEN** 原历史内容不改写，新鲜度仍沿旧快照合同；只有实际相关输入改变才失效，新增无步骤指针的孤立工件不作为已执行回执

### Requirement: Development triage can explicitly disable tenant aggregate quotas

按用户2026-11-07明确决定，部署配置 SHALL 通过已有空 `AISOC_TRIAGE_BUDGET_POLICY_FILE` 关闭可选的租户调用次数、累计token及未结算数量限制；所有租户均不再查询该限额文件。初始化与升级配置 SHALL 同步，不使用大整数伪装无限额。已有执行领取、用量记录、同Run幂等和未知调用防重派 MUST 保留，不能清账或跳消费位点制造恢复。

#### Scenario: A new tenant uses the unlimited development configuration
- **WHEN** 预算策略路径明确为空且该租户进行正常分析
- **THEN** 此层返回无租户额度策略，不因原文件缺少租户行或三项总额度而拒绝；其他实际处理条件仍按既有合同验证，消费进度与结果另行留证

### Requirement: Independent A and I content survives invalid references without adopting unsupported judgments

A/I SHALL 保存完整模型原答及逐项校验结果，并对完整、身份确定、用量已知的答复逐项保留可独立验证的内容；MUST NOT 从截断的错误列表推断其他项全部有效。A 核心判断和建议 SHALL 分开校验；I 总摘要/结论不能证明独立有效时 SHALL 为空，保留合法成员/发现/问题。局部诊断 SHALL 关联原答，非采用结果不得替换既有当前判断；历史运行详情 MAY 返回 `partial_analysis`。JSON 不可解析、必要身份缺失/重复及 unknown 执行 SHALL 不挽救或重新调用。

#### Scenario: One A recommendation has an invalid reference
- **WHEN** A 核心判断通过完整校验而其中一条建议引用无效
- **THEN** 保留原核心判断、其他合法建议和原答，明确排除项；若核心判断本身也无效则不采用，不补造 needs_review 来冒充模型回答

#### Scenario: One I member cites another member's material
- **WHEN** I 各成员身份完整，但一项引用越界，其他成员/发现/问题可独立验证
- **THEN** 保存这些有效内容和局部诊断，`conclusion=null` 且必有关联原答的工件 ID；既有有效诊断指针保持，执行失败与局部内容可读分别表达

### Requirement: Known structured facts come from frozen program sources

程序 SHALL 从同轮冻结来源提供可追溯 `program_facts`，分别标识活动、告警、入库与实际 Run 执行时间及其单位/来源，不要求模型重新生成已有事实。日志等级、告警等级、事件派生等级和 Case 既有严重度 SHALL 区分；事件按现有成员最大值/人工覆盖规则计算，不将部分成员冒充完整事件。标签 SHALL 使用配置中的版本化释义与出处，未知标签保留 unknown。事实 SHALL 随实际输入传递到 A/I 结果与 C6 报告；不机械修改模型自由正文，也不由标签或角色推断授权/攻击成功。

#### Scenario: The source lacks an activity clock or complete incident members
- **WHEN** 原件没有有效活动时间，或 Case 仅冻结了事件的部分成员
- **THEN** 活动时间明确缺失而非借用告警/入库时间；事件自动等级不可声称完整，列明缺少成员，已有人工覆盖可独立保留；Case 未设置严重度仍空

#### Scenario: A historical diagnosis has no program facts
- **WHEN** 读取旧诊断、告警说明或报告
- **THEN** 可选事实字段缺失仍符合合同；新正常诊断保持原 source_refs 必填，局部诊断必须关联原答且总判断为空，不回写旧记录

### Requirement: Processing candidates and runtime profiles have verifiable configuration sources

构建与按需处理 SHALL 由显式文件选择目标镜像、架构、数据库、模型、网络资源与调查策略；缺配置或身份不符 MUST 失败。候选 SHALL 冻结完整运行源码、策略及逐文件 hash，构建前与镜像内核源码全集，清除基础镜像旧源码，核基础与候选实际镜像身份。运行安装 SHALL 复用应用完整 policy 校验并保存 profile/policy 指纹，启动核一致性；构建/断网内存自检 MUST NOT 被标成正式服务或真实模型验收。

#### Scenario: An unchanged release name points to changed source
- **WHEN** 同名候选目录、镜像标签、文件全集或 hash 与冻结清单不同
- **THEN** 拒绝覆盖或执行，保留旧候选并使用新标识；运行配置更改后须重新生成对应运行环境，不悄悄切换数据库、模型或预算

### Requirement: Case classification and deadline have explicit persisted meanings

Case SHALL 独立保存可空classification及due_at。classification非空值 SHALL 为true_positive、informational或false_positive，null表示未设置；不得从Incident/成员告警继承，也不得从模型正文或conclusion_state推断。due_at SHALL 保存含时区的案件期限，不得以任务期限、Run超时或自动SLA代替。管理保存或有来源的导入 SHALL 沿现有Case版本检查，将实际值与活动中的操作者、时间、来源及前后值同事务保存；清空用null，历史行不回填推测值。

#### Scenario: A user clears the case classification and changes its deadline
- **WHEN** 操作者明确将案件分类清空并修改案件截止时间，当前Case版本匹配
- **THEN** 保存null分类与实际含时区期限及变更来源，原任务期限、当前判断、成员范围版本和Run保持；不自动改变案件处理状态、产生pending或执行调查

#### Scenario: An older case has no new management values
- **WHEN** 增量迁移后的旧Case没有明确来源的分类或截止时间
- **THEN** 两字段均为null，既有Incident分类、任务due_at及模型结论仍可单独读取，不被复制来填满页面

### Requirement: Case evidence entries are versioned and traceable

系统 SHALL 复用artifacts保存kind为case_evidence_index、schema_version为socai2.case-evidence.v1的不可变索引，由cases.current_evidence_artifact_id指定当前版本；MUST 校验同租户同Case、工件kind、JSON Schema及每个来源的归属/冻结成员范围。新工件、指针和变更活动 SHALL 同事务发布，旧索引保持，历史读取不得追随当前指针。索引 SHALL 保存scope_revision、实际纳入成员、前版引用、available/partial/unavailable状态及条目。

发布 SHALL 沿现有Case行锁检查预期row_version、当前索引指针及scope_revision，过期发布拒绝。前版引用 MUST 等于事务内实际当前索引且同Case同kind，首次为null。同一索引的evidence_id MUST 唯一，重复ID直接拒绝；关联成员 MUST 非空且属于索引冻结成员。

条目 SHALL 具有稳定evidence_id、名称/类型、关联成员、可空对象、原始材料引用、verdict及来源、可空威胁身份和处置引用、active/withdrawn状态。evidence_id MUST NOT 由数组位置、标题或单独文件hash替代；同一条目跨版本保持ID。verdict SHALL 为malicious、suspicious、clean、unknown或conflicting；非unknown必须有来源，冲突保双方，不提升source_label/prior_analysis/human_statement为独立观察。威胁身份 SHALL 使用明确来源的namespace/key/label，不从自由正文提取补造。原文/附件继续引用原材料，来源缺失不得假装已回查。

#### Scenario: An evidence index is revised
- **WHEN** 某条证据的判断变化或条目被撤回并发布新索引
- **THEN** 稳定条目ID保持、更新依据与前版可查，旧工件不覆盖；只更新材料目录，不自动采用案件结论、启动Run或增加C必需输入

#### Scenario: A proposed index references another case or tenant
- **WHEN** 当前指针指向异案工件，或条目引用不属于允许租户/成员范围的材料
- **THEN** 拒绝发布指针及索引，不以JSON形状合法代替归属验证，既有当前版本保持

#### Scenario: A stale writer attempts to replace a revised evidence index
- **WHEN** 当前索引已更新，但发布请求仍携带旧Case版本或旧当前指针
- **THEN** 拒绝该次发布，已保存改判/撤回及当前指针保持，不能用任意supersedes引用绕过；同一索引的重复条目ID也拒绝而不静默去重

### Requirement: Normal final delivery records an evidence directory without inferring judgments

C6 SHALL 在结果发布的同一事务中，使用现有索引存储及来源校验，登记冻结材料中明确注册的观察字段和适用 H 版本。每份不可变材料 SHALL 只有一个稳定 material 身份，多个字段不增加条目数；模型段落、图节点和查询回执不自动成为独立证据。没有证据级合法判定来源时，性质 SHALL 为 unknown、威胁和处置保持空。目录能力及未登记来源 SHALL 明确列在限制中，不把零威胁数解释为已排除风险。

#### Scenario: Final delivery creates an index or encounters a validation failure
- **WHEN** 原冻结成员、输入和当前目录仍适用，正常 C6 发布
- **THEN** 目录、当前指针、活动、报告及结果同事务提交；成功空目录为 available/0，来源缺失为 partial，生成校验失败为 unavailable/null；重复同 Run 不增加版本，事务失败不留下孤立目录或指针

#### Scenario: An existing directory contains a manual withdrawal or judgment
- **WHEN** C6 遇到人工发布的目录，或已有 withdrawn、明确 verdict、threat 或 remediation 的条目
- **THEN** 保留当前目录并记录跳过原因，不自动恢复条目、清空判断或处置；后续目录合并须显式维护。Run 期间指针/成员改变、旧目录合同或 hash 错误也保留旧指针并记录原因

### Requirement: Evidence and threat counts are reproducible from selected saved entries

独立证据条目数 SHALL 对当前明确选定索引中active且适用于当前Case成员的evidence_id去重；告警原文、来源快照、Finding、对象和图节点不自动计为条目。关联威胁数 SHALL 对这些条目中malicious/suspicious且具有非空威胁身份的(namespace,key)去重，clean/unknown/conflicting不计；不得按显示名、材料数或对象数猜测。读出 SHALL 携带计数状态、索引身份、覆盖范围及可定位来源。

适用 SHALL 要求条目的全部关联成员仍属于当前Case；部分移出的多成员条目整条退出当前计数但保留历史回查，MUST NOT 以取交集缩小其事实范围。成员范围变化 SHALL 返回partial及被排除/未覆盖范围。

#### Scenario: Several entries refer to the same threat
- **WHEN** 两条有效证据具有不同evidence_id但引用相同namespace/key的威胁，另有clean及未提供威胁身份的条目
- **THEN** 独立条目按各有效ID计数，前两条威胁合计一次，clean及缺威胁身份条目不增加威胁数；数量不表示攻击次数或案件已定性

#### Scenario: There is no saved index or the known index is partial
- **WHEN** Case没有证据索引，或已选索引只覆盖部分当前成员
- **THEN** 前者计数null且状态not_recorded；后者可返回已存适用条目的计数（含0）并标partial及覆盖限制。可用索引为空/全撤回/全部范围排除时条目数0，适用条目全clean/unknown/conflicting或无威胁身份时威胁数0；不可用或引用失效为null并带限制，成员变化不改写历史索引

### Requirement: Explicit remote profiles support read-only access to approved production data

经用户 2026-11-07 明确授权，本机读取服务 SHALL 通过显式配置文件选择正式数据库、既有只读角色和唯一业务租户，MUST NOT 隐式回退到历史或合成测试库。环境地址、端口、凭据、TLS 和超时 SHALL 来自配置文件；数据库连接 SHALL 验证服务端证书和身份，转发地址与证书身份可分别配置。该新增模式不改变下方本机隔离实验模式的既有数据归属。

#### Scenario: The local read-only API connects through an SSH forward
- **WHEN** 用户选择远端只读 profile
- **THEN** 读取服务核对实际数据库/角色、TLS、只读事务和 schema，使用独立本机访问凭据绑定唯一租户与读取权限；GET 返回已有记录或真实空态，不创建生产用户或更新认证使用记录

#### Scenario: Configuration or a request would broaden access
- **WHEN** 必要配置缺失、数据库身份不符、TLS 校验失败、只读角色拥有调查表写权限，或客户端发起写方法
- **THEN** 启动或请求明确拒绝，不降低 TLS、不回退测试库、不执行生产写入，也不启动调查、模型或后台消费者

### Requirement: Reader fixes ship through shared initialization and upgrade sources

按用户 2026-11-07 开发授权，读取账号 SHALL 具备调查表及 `public.assets/public.users` 的 SELECT，以及 Case 新鲜度所需两个函数的 EXECUTE。应用 SHALL 使用认证租户过滤并只投影页面字段。数据库修复 MUST 同步维护新库初始化、现有库增量升级与实际读取验证；两种路径 SHALL 复用同一份增量，保留 V1 建表原件。部署目标和角色 MUST 来自显式配置，不依赖默认连接。缺读取依赖 MUST 报可识别服务错误，不返回伪装的业务空态。

#### Scenario: A fresh environment receives the reader fixes
- **WHEN** 部署方在新库初始化 V1.2 读取能力，或为已部署 V1 执行增量升级
- **THEN** 两条路径得到相同的必要读取能力，资产关联和非空负责人可通过现有接口取回；升级不重放 V1、不改既有表结构和业务数据，重复授权可安全执行

### Requirement: Domain focus remains separate from finding scope

C3/C6 领域 `alert_ids` SHALL 表示本领域关注成员，发现 `alert_ids` SHALL 表示该发现完整涉及范围。领域 MAY 引用与关注成员相交的相关跨成员发现，MUST 保留发现原成员范围，不能自动扩展领域关注或把发现缩为交集；无成员交集、未知发现及超出冻结 Case 的成员仍无效。领域工件 SHALL 分别保存领域关注范围和发现范围，旧工件未记录领域关注时不得反推。

#### Scenario: An identity analysis focuses on one member of a shared finding
- **WHEN** 身份领域关注 A2，引用 F1(A1,A2,A3)，F1 的范围和来源均有效
- **THEN** 接受这一相关引用，领域仍关注 A2，F1 仍保留 A1/A2/A3；此引用不自动决定领域适用性或扩大任何成员结论

#### Scenario: A domain references a finding with no focused member
- **WHEN** 领域只关注 A2，而被引发现只涉及 A1
- **THEN** 将该关联标为无关范围，不能通过缩改发现成员使其合法；局部失效由引用处理规则收口

### Requirement: Citation failures preserve independent analysis and permit one bounded correction

C3/C6 SHALL 分别保存原答、反馈、纠正答、逐项诊断和可用交付。对完整回答中 answered/已分析/有发现却空引用的字段，系统 MAY 返回具体路径、原因及本轮可引用来源，要求一次纠正或明确未解决；同一份 C3/C6 最多一次纠正，计入原 Run 次数、时间和 tokens，并保护 C6。模型调用 unknown、超时和非完整答复 MUST NOT 自动重派。

#### Scenario: One answer has an empty citation list
- **WHEN** 已完整收到答复，问题或其他要求证据的结构化字段没有引用，且同 Run 额度充足
- **THEN** 原答先保存，反馈只列实际可用编号及角色/成员，纠正后重新完整校验；不能为过校验自动补编号。额度不足或第二次仍错误时记录原因并保留独立有效部分

#### Scenario: A final conclusion depends on an invalid source
- **WHEN** C6 总判断依据无效，但部分成员、发现或问题仍有有效来源
- **THEN** 无依据的总判断不可采用，可用片段保存为 partial/rejected，conclusion 为 null 且 conclusion_covered=false，旧 Case 判断不覆盖；坏 JSON 或必要身份不明确不能形成可采用交付。保留首答片段时关联首答 ID，纠正失败答另留回执

### Requirement: Stored non-run sources and case activities are directly readable

后端 SHALL 提供非 Run 的告警/事件/Case 来源正文读取，按认证租户、父主体、空 Run 归属、原版本和 hash/长度校验；外置、超限或不完整内容 SHALL 如实标记，GET 不产生业务写入。Case 活动 SHALL 汇总显式主体/目标及当前成员告警、显式关联事件的活动，以唯一活动 ID 去重，保存的步骤不混作业务活动计数。

#### Scenario: A client reads a source artifact outside a Run
- **WHEN** 客户端用主体 ID 和来源工件 ID 请求正文
- **THEN** 正确归属可返回原版本，错误父主体或租户返回 404，完整性不符不返回正文；保留截断原件时标 retained 状态，不能称全文可用

#### Scenario: One activity matches both the case and a member
- **WHEN** 同一活动同时具有 Case 主体及成员告警目标
- **THEN** Case 活动列表和总数只计算一次，分页保持相同范围；不混入无关主体活动，并明确成员活动使用当前 Case 关系

### Requirement: Local data services remain independent of remote model connectivity

本阶段验证 SHALL 复用本机已有镜像建立专属PG、ClickHouse、Kafka、ZooKeeper、Redis及本机API/Fusion，以隔离测试空间保存真实流程材料，保留旧数据；按用户授权停止的旧后台任务不得随本轮自动恢复。知识检索 SHALL 沿冻结告警标题→PG全文检索；Neo4j、向量库及Embedding MUST NOT 作为本轮启动前提，不新增RAG。DeepSeek直连验证 SHALL 不依赖VPN或21数据服务；远端已部署模型仅在用户连接VPN的阶段调用，只切换模型连接地址、认证及对应协议/profile，数据库、执行记录、工件及页面全过程 SHALL 保留在本机，不改用远端数据库或执行驱动。镜像已存在或容器已启动 MUST NOT 被当作目标身份、权限、schema或供应链已经通过。

#### Scenario: VPN is unavailable during normal development
- **WHEN** 用户未连接VPN
- **THEN** 本机数据构造、入湖、上下游、DeepSeek、结果导出及页面复核仍可继续；不后台反复探测21或重派远端模型请求

#### Scenario: Chat disconnects after a model dispatch
- **WHEN** 固定批次已保存派发意图，聊天或VPN连接随后中断
- **THEN** 本机有限执行脚本保留已发生的回执，重连先核状态；结果不明保留unknown，不自动重试、改模型或重复同一操作

### Requirement: Existing context integrations are validated along their actual producer and reader paths

系统 SHALL 复用已有知识导入及本轮所需资产、内部IOC路径，在模型前核对实际导入、目标存储、告警标题检索词、PG全文检索结果、租户范围及候选输入；实际模型发送、采用与引用 SHALL 在后续真实调查阶段单独验收，不作为模型前准备的完成前提。PG知识FTS与向量检索、UEBA anomaly表与risk profile、Feed存储与PG内部IOC SHALL 分别说明已有证据和未接边界，不因某服务可用就宣称另一路已接；本轮不启用的身份图、向量、UEBA生成及Feed链不要求补齐。直接种入合成行的验证 SHALL 明确只证明相应读写路径；工具总预算和C4预留保持，来源按本change的有界相关性规则选择。

#### Scenario: Title-based knowledge retrieval is ready before the model runs
- **WHEN** 文档经已有导入路径写入本轮专属PG，冻结告警标题的全文检索按租户返回可回查材料，候选输入及来源已核对
- **THEN** 模型前准备可完成，随后由真实调查核实际发送和引用；不等待已有模型结果，也不启动向量库或Embedding来替代当前FTS路径

#### Scenario: A knowledge document is retrieved but not used by the investigation
- **WHEN** 文档已导入且可检索，但本轮因范围、选择或预算未将它送入模型
- **THEN** 保存导入与检索证据并明确未采用原因，不称模型已阅读该文档，也不把知识指导当作本案授权证明

### Requirement: Configured lake storage and retained traffic remain queryable

Fusion湖写入 SHALL 对显式event_id与数据库默认ID两种INSERT都使用经标识符校验的配置库名；MUST NOT 因SQL硬编码将新空间数据写到旧湖。调查查询 SHALL 使用冻结来源库、租户、主机、左闭右开时间窗和事件类别，按实际事件ID核查返回集合。测试夹具期望及控制角色 MUST 与投放材料分离。

已有OCSF traffic的bytes/bytes_in/bytes_out/packets/packets_in/packets_out SHALL 作为带原路径的非负整数观察提供给调查投影，明确in为目的到源、out为源到目的。明确0 MUST 保留；未提供、非法或超限值 MUST NOT 补0或从其他字段猜测。流量计数 MUST NOT 被描述为包内容、授权或外传成功证明。此增量不要求新表或新增模型调用。

#### Scenario: A default event ID is inserted into the independent lake
- **WHEN** 未提供有效事件UUID而使用数据库默认ID，配置指向新湖空间
- **THEN** INSERT仍显式指向配置新库，不能回退到aisoc.raw_events

#### Scenario: Context includes another endpoint and out of scope controls
- **WHEN** 同主机时间窗内记录不同目的地址流量，同时有其他主机、窗口前及恰好窗口结束的记录
- **THEN** 主机范围网络Tool保留不同目的地址上下文，排除三类范围外记录；计数原值与来源路径保留，不能将近邻记录直接标为告警来源或因果证据

### Requirement: Verdict evaluation distinguishes errors from abstention

验收 SHALL 仅将已确认良性判为恶意、已确认恶意判为良性计为方向性误判。已确认良性或恶意输出needs_review MAY 作为证据不足时的保守结果接受，SHALL 单独统计待复核率，不计误判，也不计确定判对。没有独立真值的样本 MUST NOT 用于宣称误判率或准确率；其确定定性仍须核对证据依据。调用失败、无有效答复、引用错误和事实编造 SHALL 独立统计，MUST NOT 通过改写成needs_review消除。

#### Scenario: A benign sample remains unresolved
- **WHEN** 样本真值已确认良性，模型基于可见证据输出needs_review并准确说明待核原因
- **THEN** 记为可接受待复核，不记良恶误判；仍核对来源、范围、事实和执行结果

#### Scenario: A synthetic label is the only justification for benign
- **WHEN** 未确认真值的样本仅凭Synthetic、fixture或用户名被判为benign
- **THEN** 记录无充分依据的确定判断，不直接计方向性误判，也不将测试标签作为良性真值

### Requirement: Model contracts separate evidence identity from presentation

新模型请求 SHALL 选择在本次已收到文本中不存在的局部来源编号前缀；历史原文、结构化值和持久引用 MUST 保持，不重命名历史事实。结构化来源数组 SHALL 是正式引用的唯一依据；正文中的当前有效编号只作展示诊断，不隐式补入引用。未知或跨成员编号 MUST 拒绝；历史分析中的字符串 MUST NOT 充当原始对象名称豁免。

#### Scenario: A history paragraph contains an earlier source alias
- **WHEN** 历史分析包含S14或N1_S14，而本轮也包含不同来源
- **THEN** 本轮选择未出现在输入中的新前缀，保存原来源路径/hash与实际发送值，历史段落不改写

#### Scenario: A visible inline alias is omitted from the structured list
- **WHEN** A/I正文写了本轮可见且范围正确的编号，但没有把它写入结构化数组
- **THEN** 记录展示warning，正式引用仍严格使用原数组，不补号或扩大来源；不存在或越界编号继续拒绝

### Requirement: Provider schema capabilities do not relax local result checks

显式选择vllm_grammar_v1配置时，系统 SHALL 在预留及记录请求前从发送Schema中省略不支持的uniqueItems；本地重复ID检查 MUST 保持。默认standard配置 MUST 不变，不根据HTTP失败自动重试或切换弱JSON模式。

#### Scenario: A conflict repeats one finding twice
- **WHEN** 兼容Schema生成了重复finding_ids
- **THEN** 本地拒绝，不能因为供应商不支持uniqueItems而采纳

#### Scenario: DeepSeek rejects a referenced nullable object branch
- **WHEN** DeepSeek Responses协议的规范Schema在anyOf分支使用本地$ref
- **THEN** 在计量和持久化前仅展开该分支的定义，保留anyOf、null、必填/额外属性/长度/范围等全部约束；普通属性和数组元素引用保持共享，不改成不支持的object类型数组，也不修改规范输出或本地业务校验。循环、缺失、非本地及含兄弟约束的引用明确拒绝，不能静默丢约束或重试

#### Scenario: A provider returns an HTTP error without a model answer
- **WHEN** A/I/C3/Deep/C6调用收到HTTP错误或httpx传输异常
- **THEN** 保存有界的错误类型、HTTP状态及允许的code/type/param/message，去除配置密钥、常见凭据文本和URL，不保存原错误全文或请求头；非JSON、过大或不支持的正文明确省略。回执raw为null，用量未知。明确400/422 Schema拒绝在回执提交后收口failed并释放基础Run；其他无法确定执行结果的异常保持unknown。当前有效判断保持，无自动重试或协议降级

### Requirement: Context and judgment bases retain distinct meanings

告警时间引用 MAY 附在行为发现中作为上下文，但observed MUST 另有每个涉及成员的实际observation；其他标签、旧判断或人工陈述不能以此例外升格。领域关联已知发现 SHALL 与领域适用性分开，三种适用性均可关联范围正确的发现，非applicable MUST 解释限制。新A定性结果 SHALL 单独保存具体decision_basis，类型与判定一致、来源在正式证据数组内且均为observation或human_statement；needs_review使用null。该校验不是自然语言主张真实性证明。

#### Scenario: A timestamp accompanies a process observation
- **WHEN** 行为发现引用该成员的原始进程记录并附该成员告警时间
- **THEN** 保持时间的source_label角色并作为上下文；只引用时间、用标题替代观察或引用另一成员时间仍不能通过

#### Scenario: Labels are mixed into a benign judgment basis
- **WHEN** benign的decision_basis引用厂商、测试标签或旧分诊，即使总证据数组另含进程观察
- **THEN** 拒绝该定性依据；不会自动改判、采用或把行为存在当成正常/授权依据

### Requirement: 新版独立服务与原版并存

新版 SHALL 使用独立应用入口、端口及现有数据库实例上的独立空间，MUST NOT 替换原服务、改写旧业务表或抢占旧Kafka消费者。身份认证 SHALL 使用新库中的真实身份，凭据不进入验收工件；不通过开发身份绕过证明接口可用。

#### Scenario: 独立部署与真实合成验收
- **WHEN** 启动新版并验证收到的合成告警经过A/I/C/H和用户显式新一轮C
- **THEN** 核对新表、实际模型及湖查询的来源和输出，同时确认旧容器身份/镜像/启动时间不变；固定样本的原请求、答复及失败保留，fixture写湖不冒充采集消费者验证

### Requirement: Distinct investigation stages preserve their own facts

系统 SHALL 区分A告警基本查询/分诊、I事件诊断、C完整Case基础调查和H人工确认的输入范围、保存记录与来源角色。系统 MUST 从Fusion收到数据后保留已有材料及关联，不把缺失上游输入列为本change补数任务。

#### Scenario: Alert and incident analyses precede a case
- **WHEN** 收到告警并归入事件，之后由用户纳入Case
- **THEN** A保存告警查询/分诊与解释，I保存成员汇聚诊断；C读取适用材料并执行整案调查，不能将A的基本查询或Fusion归并摘要标为已完成的C调查

### Requirement: Analysis execution has traceable persisted output

A/I执行 SHALL 保存该次冻结输入、实际查询/模型请求回复、步骤、用量和结果，成功空查询、不可用、失败及用量未知 MUST 分别表达。结果与当前指针采用 SHALL 同事务校验来源、范围版本和较新采用，旧范围结果保留历史。

#### Scenario: Materials change before an analysis finishes
- **WHEN** 已冻结的A或I输入在其结果发布前发生变化
- **THEN** 原结果仅按原范围保存并标明不再适用，不覆盖当前有效指针，不将新材料拼进旧请求

#### Scenario: A query returns no records
- **WHEN** 受限查询成功但返回零行
- **THEN** 保存查询范围、状态及零行事实，不自动推导攻击不存在或关系被否定

#### Scenario: Incident synthesis reads member triage
- **WHEN** I冻结事件成员及已有分诊
- **THEN** 在同一输入快照核验分诊来源Run完成、材料配对及输入仍有效，过期或无法验证的分诊正文仅保原件，不进入模型；旧冻结输入按其原合同读取

#### Scenario: Incident synthesis must cover every member
- **WHEN** I准备模型输入并接收模型答复
- **THEN** 保留完整成员目录与逐成员已读/未决/未读状态，无法容纳目录或答复漏成员时明确失败，发现仅引用实际可见且属于其范围成员的来源，不凭归并依据制造独立观察事实

### Requirement: Compact model inputs preserve required meaning and actual visibility

模型输入 SHALL 按阶段任务组织语义组，在预算内优先保留成员核心事实、适用人工限定和明确反证；I的同次分诊及配对理由仍为必要输入。C3/C6的A/I参考判断 SHALL 为可选原子组，不得挤出必要事实/H；C6实际补查、执行计划和有效指定比较仍为必要输入。可合并重复身份/来源元数据，但 MUST 保持值、类型、来源及成员映射。完整材料保存在库，实际模型视图 SHALL 分别说明材料保存完整性、分诊适用性和实际可见性，MUST NOT 将prepared或发送成功等同模型完整阅读。

#### Scenario: Optional raw leaves compete with received detection context
- **WHEN** I在核心事实、同次分诊及时间之后仍需选择检测规则/评分与可选原始叶字段
- **THEN** 先轮询各成员的已有detection原值，再填可选元数据及原始叶字段，仍标source_label；单项guard和大小上限保持，无法容纳的项按原路径明确记录省略，不改为观察或提升模型预算

#### Scenario: Repeated metadata displaces a valid triage
- **WHEN** I的冻结输入含有效同次分诊，但平铺重复元数据占用视图额度
- **THEN** 先去重复并为必需组预留空间，完整保留判定及配对理由；旧模式维持原配对评分，新结构profile可将评分元数据留后台；不能只留分数或把省略分诊标成已发送

#### Scenario: Human feedback competes with historical A and I judgments in C
- **WHEN** C3或C6收到适用H，必要事实/H及指定比较与A/I参考竞争8192B视图
- **THEN** 先保必要组，再将A/I判定/评分/理由/限制/来源整组放入或明确省略；不得因可选I摘要放不下阻断可容纳的完整必要输入，也不得丢H、反证或把省略参考标为已读；完整消息和wire仍核原上限

#### Scenario: A mandatory group still cannot fit
- **WHEN** 去重后必需组仍超过既有预算或单项边界
- **THEN** 在模型调用前记录明确容量限制，不切断关键原值、不缩小成员范围后宣称完整、不自动增加预算或调用

### Requirement: Validation distinguishes presentation from source and scope errors

模型输出 SHALL 使用与本地形状校验一致的请求合同；事件级背景只能用于明确事件背景位置，不能取得虚构成员归属。正文中合法且已有结构化引用的编号 SHALL 仅记录展示warning，未知/错配/跨成员来源和事实角色升级 MUST 阻止正式采纳。原回复及版本化分类诊断 MUST 留存，能检查的多个错误应在同次校验报告，无法检查的项目标not_checked。

#### Scenario: A correctly bound source identifier appears in prose
- **WHEN** 正文编号属于本次实际可见来源、对应结构化引用已包含它，且来源范围合法
- **THEN** 保留原答与展示warning，继续其余校验，不仅因此拒收整份分析；不能据此认定其自然语言判断正确

#### Scenario: Incident context is cited as member evidence
- **WHEN** 模型将无成员归属的事件背景放进成员发现的source_ids
- **THEN** 拒收并记录准确范围错误；Schema不得把该背景列入成员来源候选，也不得由服务端补造成员归属

#### Scenario: Formatting and scope violations coexist
- **WHEN** 可解析答复同时包含展示问题和来源范围错误
- **THEN** 同次记录可检查的问题，范围错误继续阻止采纳；不靠下一次真实模型调用才发现第二项错误

### Requirement: A case has one claimed baseline and coalesced pending work

同Case SHALL 只有一个活跃基础调查Run，unknown仍占槽。领取状态、范围冻结及并发校验 MUST 在外部执行前以数据库事务提交；未领取pending可合并，领取后必须冻结。系统 SHALL 使用用户手动启动，不新增定时领取或自动接续。

#### Scenario: Two alerts arrive around a baseline claim
- **WHEN** 第一个告警触发的pending已在事务中领取，外部执行尚未开始，第二个告警被纳入Case
- **THEN** 第二个告警更新Case范围及下一条pending，不修改已领取Run输入；若用户启动下一轮则返回活跃冲突，当前轮结束后仍需手动启动

#### Scenario: Multiple scope edits occur before claim
- **WHEN** 用户连续修改范围且pending尚未被领取
- **THEN** 更新同一条pending及其范围版本，调查历史保留该待更新记录，不为每次编辑创建一条等待执行的队列任务

### Requirement: Baseline investigation delivers a full traceable case result

C SHALL 执行C1范围准备、C2背景查询、C3共享四领域分析、C4必要取证与问题级Deep、C5有来源图以及C6最终交付，逐项记录实际执行/跳过/限制。最终结论、比较、Case影响、报告与正式结果 MUST 使用同版来源，结果发布及有效当前判断采用须原子保存。模型或来源不足时 SHALL 保留明确系统交接，不伪造完整结论。

#### Scenario: A valid current baseline is delivered
- **WHEN** 完整基础调查产生校验通过且覆盖当前有效范围的结果
- **THEN** 保存同版Result、结论/closing_note、比较与影响、JSON/Markdown和实际用量，并按有效性规则自动更新Case当前判断

#### Scenario: Final synthesis is unavailable
- **WHEN** 基础调查缺少有效最终模型输出或预算不足
- **THEN** 保存系统交接和停止原因，不用待核实的草稿替换当前判断，不提升原预算或自动重试

### Requirement: Readers expose evidence validity and stable relationships

页面数据出口 SHALL 区分当前指针与适用性、活动Run与pending、处理状态与判定、材料时间与业务时间。历史读取 MUST 使用已冻结材料；新C输入仅消费适用的同次分诊/成功诊断，过期或无法验证内容保留账本而不作当前模型判断。告警/事件/Case关系须有同租户可校验身份及范围版本。

#### Scenario: An old diagnosis remains stored
- **WHEN** 事件成员变化而旧诊断仍可读取
- **THEN** 显示其原范围及过期状态，新C模型输入不将其视为有效诊断，旧Run冻结内容不被重写

#### Scenario: A frontend requests an incident field
- **WHEN** 新页面读取事件独立标题、负责人、人工覆盖严重度或最近业务更新时间
- **THEN** DTO从明确事件事实或已定义成员派生读取，人工覆盖值与自动汇总值分开；不能用任意单条成员告警的字段冒充事件自身管理事实

#### Scenario: Page records or execution directories are paged
- **WHEN** 读取告警/事件列表、关系集合或A/I执行目录
- **THEN** 返回明确总数和下一页或截断标记，总体统计和模型用量不依赖当前返回页，未知用量保持未知；GET不改业务状态或更新时间

#### Scenario: A subject is linked to shared case activity
- **WHEN** 读取告警/事件活动或Case关联
- **THEN** 活动须有明确主体或目标，不能混入共享Case的全部操作；显式事件关联与仅共享成员区分，Case目录额外检查cases:read

### Requirement: Explicit case associations and moves are atomic

系统 SHALL 区分显式事件链接与实际新增成员，在同一事务内保存成员关系、范围版本、pending记录和操作回执；重复操作 MUST 返回原结果。两个Case移动 SHALL 按稳定Case ID顺序加锁并校验两端版本，任意失败整体回滚。已领取Run及历史结果 MUST 保持原范围。租户及收到的身份命名空间 SHALL 一致，Case清空后仍保留固定绑定；上游未提供的来源环境 MUST NOT 由fusion.v1或connector推断。

#### Scenario: Only an explicit incident link is added
- **WHEN** 事件成员已经全部在Case中，用户新增该事件的显式链接
- **THEN** 保存事件链接与活动，但不增加范围版本或创建新pending；响应分别返回新增链接及新增告警

#### Scenario: A selected incident cannot supply all members
- **WHEN** 创建或关联所选事件中存在缺失事件、空事件、不可用成员、跨租户/命名空间或最终范围超过200
- **THEN** 整体拒绝，不能部分创建Case或截断成员后成功

#### Scenario: A move competes with another move or baseline claim
- **WHEN** 两个Case反向移动并发，或源Case领取与移动并发
- **THEN** 使用Case锁和范围版本决定顺序，冲突方明确拒绝；若已领取则保持原冻结范围并生成下一pending，不丢成员或改旧输入

#### Scenario: A move is not committed yet
- **WHEN** 移动事务已经删除源成员但尚未完成目标写入
- **THEN** 其他读者仍读取已提交原数据，失败则两端都回滚，成功后两端变化一起可见

### Requirement: Followup declarations and final execution context stay bound

C3及C6中的followup SHALL 仅引用所声明成员拥有的冻结对象；关系核验可声明多个成员并使用其对象并集，不能将Case内其他成员的对象悄然挂到单成员建议。此声明校验 MUST NOT 改变Deep整案问题与固定Tool binding的执行范围。

C6 SHALL 将已执行原计划的initial_analysis_artifact_id及followup_index与其原建议内容、成员范围和执行状态对应；原计划内容 MUST 作为必要输入受原guard、单项/总输入及剩余额度限制，不能被可选压缩移除后仍继续报告其执行含义。后续再分析的新建议 MUST 与原计划区分，不按新数组顺序承接旧执行状态。流程完成、已有回答及人工确认 SHALL 分开表达，不将执行记录用作行为或授权事实。

#### Scenario: A followup selects an object owned only by another member
- **WHEN** followup只声明A0，却选择仅属于A1的冻结对象
- **THEN** 拒绝该输出；若合法关系核验同时声明A0/A1，则允许使用两者对象并集；已有历史原答不改写

#### Scenario: Reanalysis reorders or replaces followups before final delivery
- **WHEN** C4已记录原计划执行，而最新分析新增或调换建议
- **THEN** C6仍读取原计划工件与原序号，状态只匹配原建议；最新建议仅作为新提议

#### Scenario: Required original followup cannot fit the existing budget
- **WHEN** 原计划内容被guard拦截、单项过大或无法在原预算内完整传入
- **THEN** 明确记录输入不可用或预算不足，不加预算、不截断改写、不发模型猜测建议含义；原账本保持

#### Scenario: Final synthesis uses a stage-specific prompt
- **WHEN** 构造C6最终交付请求
- **THEN** 使用C6完整交付规则和单一输出目标，合并与共享规则重复的提示；不继承C3初始分析的阶段目标，不以删必要计划、事实字段、来源约束或提高预算来容纳请求

#### Scenario: Final input competes with prior A or I analyses
- **WHEN** 原始事实、时间、人工反馈、已执行原计划及有效比较结论与A/I历史分析竞争C6输入容量
- **THEN** 前者为必带项；A/I参考按同次判定/评分/理由整组保留或明确省略，不拆散或改写。组成视图后仍以完整wire请求和已有usage检查共享预算，ready不能当作已获派发额度

### Requirement: Baseline adoption and reading expose input freshness

系统 SHALL 复用run_members及C1工件比较材料、分诊、反馈版本、相关事件诊断与成员、已完成人工反馈的正文/范围/引用/完成事实。发布时输入改变或不能核验 MUST 保留本轮结果且不自动采用。当前判断读取 SHALL 返回current/stale/unverified及原因，不回写历史。

current SHALL 仅表示上述受跟踪输入一致，MUST NOT 宣称外部湖、资产或情报全部最新，亦不证明结论正确。成员覆盖与依据状态 SHALL 分开表达；有效partial的自动采用政策保持，不要求所有成员均被结论覆盖。

#### Scenario: A completed task is renamed without changing feedback
- **WHEN** 任务只改标题、负责人或期限且完成事实不变
- **THEN** 不因revision ID变化将已冻结反馈判为失效

#### Scenario: Material changes after a result was adopted
- **WHEN** 同一成员收到新材料或人工反馈发生实质变化
- **THEN** 读取当前判断返回输入过期及原因；历史Run、结果和采用事实保留，下一轮由用户明确启动

#### Scenario: Human feedback changes before publication
- **WHEN** Run已冻结输入但尚未采用，当前人工结果或范围被重新确认
- **THEN** 原轮按原输入保存，发布门返回stale_input而不覆盖当前判断；不改旧H版本，不自动启动新轮

#### Scenario: Only external source data changes
- **WHEN** 外部日志或TI更新，但受跟踪的PG输入与H语义没有变化
- **THEN** 不假装已经检测到该变化；返回的依据状态限定在已跟踪输入，并保留来源时间和覆盖限制

### Requirement: Evidence hashes and background selection preserve meaning

系统 SHALL 保留明确SHA256字段及明确声明SHA-256算法的有效原值和路径，冲突保留双方，不从长度推断算法。C2 SHALL 在原Tool总预算及C4预留额度内按冻结对象相关性选择来源，保存优先级依据和未执行原因；空查询也计调用。

#### Scenario: A case has explicit IOC and user selectors
- **WHEN** 情报与UEBA已连接、具有冻结的合法对象，并与通用历史来源对当前预定义核查目标的相关性相同
- **THEN** 同级稳定排序使它们优先于通用历史查询；其他相关性按有界问题选择规则确定，超预算来源仍明确跳过，不能因固定来源类别压过更相关知识

### Requirement: Human confirmations preserve historical cited facts

H SHALL 保存人工确认内容、主体、完成时间和事实范围，并能供Case读取与引用；已保存调查引用的历史版本 MUST 冻结。完成或编辑人工任务不自动发模型/Tool、不自动解决Case。

当前任务及历史版本 SHALL 分开保存，所有状态可编辑；完成须非空结果和明确范围。服务端 MUST 校验同租户负责人、同Case来源和预期版本，以Case→Task锁和同事务回执防止脏写。实际完成者/时间 SHALL 由服务器记录，不能由负责人或客户端字段冒充；只改元数据时保留原完成事实，修改结果/范围/参考来源或重新完成时记录重新确认。

#### Scenario: A referenced human result is edited
- **WHEN** 已完成人工结果被调查引用后又被用户修订
- **THEN** 当前任务呈现修订内容，历史调查仍读取原引用版本，并可导航到当前任务

#### Scenario: Only task metadata is edited
- **WHEN** 已完成任务仅修改标题、说明、负责人或期限
- **THEN** 保存新revision及修改人/时间，原完成者/时间和事实范围保持；即使范围成员后来移出，元数据编辑也不自动重新确认或改范围

#### Scenario: A human scope is no longer wholly applicable
- **WHEN** 新C1读取已完成人工反馈，但其范围缺失、为空或包含当前Case之外的成员
- **THEN** 保留原revision和明确限制，只作为执行记录，不将整份反馈输入新模型或扩大到剩余/新增成员；旧Run已冻结的内容不回算

#### Scenario: Human feedback arrives after a baseline completes
- **WHEN** 成员范围未变、用户完成H后明确请求准备下一轮基础调查
- **THEN** Case锁内新建或复用一条manual pending，保持scope_revision，重放原操作回执；不执行模型或自动排队，后续仍须用户手动启动，领取时才冻结最新H

#### Scenario: Another baseline is active during explicit preparation
- **WHEN** 用户在同Case已有running/unknown基础Run时明确准备下一轮
- **THEN** 可以准备/复用pending，但启动仍返回单活跃冲突；当前轮结束后不自动接续，原冻结范围和反馈保持

### Requirement: Full-run resource allocation protects a feasible final synthesis

新版本完整C执行 SHALL 从显式配置读取单次 300 秒、Case 1500 秒及 C6 预留 300 秒，单次上下文、输出、整轮累计 tokens、模型/Tool 次数和存储字节上限分别管理。模型和 tokenizer 派发前 SHALL 检查截止、次数及未知用量；计量本身受扣除 C6 预留后的剩余时间约束，生成前再次检查。计量 MUST 使用协议转换后的完整请求及实际后端 tokenizer/chat template，包含消息、Schema/协议包络、安全余量和输出预留，不以字节充当 tokens。不得重置 usage、删除必要事实/H/反证/原计划或运行中自动提高额度。预留参数、配置指纹和未执行原因 SHALL 保存在同 Run 执行计划。

1.2 本地候选为 Case 6 模型/4 Tool/131072 累计 tokens、C3 输出 4096/C6 输出 8192；默认预留 C6 两次（初答及可选纠正），更低的显式调用上限只预留实际可用次数。这是开发候选，真实批次额度须另行固定，不能追认旧批。当前后端计量仅支持已核实的 chat_completions/vLLM；未支持的协议 SHALL 明确拒绝，不沿用其他后端计数冒充兼容。

#### Scenario: An optional deep step would consume final capacity
- **WHEN** 新Deep请求或其必要结果上界将挤占C6所需容量或时间
- **THEN** 不派发该可选步骤，保留问题及停止原因，使用已有材料尝试有界C6；不得仅因还有调用次数就继续消耗最终资源

#### Scenario: Complete mandatory input cannot fit
- **WHEN** 无损去重后的完整必要请求无法在既有总上限或单次输入限制内完成
- **THEN** 在真实模型调用前说明容量不足并按既有终态合同保存交接，不能让Run永久running、静默缩范围或伪造模型结论；只提前阻断所有正常小案不能算此修复通过

#### Scenario: A bounded normal case is accepted for execution
- **WHEN** 固定两成员案例包含必要事实、H与比较依据且准入通过
- **THEN** 保存可检查的C3/补查/C6资源分配，真实验收还须获得有效最终模型结果；替身、离线容纳或次数预留成功均不能代替结果质量验收

### Requirement: Deterministic followup queries do not require a deep model loop

C3本轮query建议 SHALL 选择已发送给模型的服务端合法binding，直接通过现有受限Tool执行一次；MUST NOT 为选择已明确绑定再次调用Deep模型。binding的租户、主机、窗口、来源库及查询限制由服务端决定；客户端/模型不得提交自由SQL或扩范围参数。直接查询与Deep SHALL 共享同Run额度、回执及来源去重，明确空/不可用/失败/不确定。新执行合同 SHALL 版本化，旧Run与原答保持。

#### Scenario: An explicit binding answers a requested evidence lookup
- **WHEN** C3提出query并选择当前可见、范围合法的绑定
- **THEN** 程序派发一次实际Tool或复用同Run已存回执，额外Deep模型调用为0，结果与原建议身份交C6综合

#### Scenario: A query binding is invalid or not offered
- **WHEN** 模型选择未提供、失配或越界绑定，或者本轮没有所需选择器
- **THEN** 非法模型输出拒收；实际缺能力则明确留未决/限制，不猜绑定、静默转Deep或扩大查询

#### Scenario: Direct query and deep share a question
- **WHEN** 一个question同时有确定query和动态Deep建议，或多个建议引用同一绑定
- **THEN** query按绑定复用，Deep按问题复用，两类路线不因question_id相同互相遮蔽；实际次数与复用引用可核查，不能把同源返回算多份独立证据

### Requirement: Followup priority and future suggestions remain explicit

本轮补查 SHALL 先按decision_critical/supporting优先级，再按同级query先于deep和原序号稳定调度；使用原objective/required_evidence解释需求。服务端 SHALL 留存模型建议、实际顺序、原计划工件/序号及未执行原因；优先级 MUST NOT 改变证据角色、事实归属或工具权限。C6新建议 MUST 不自动执行或承接C3原计划状态。

#### Scenario: Two questions compete for remaining resources
- **WHEN** 关键确定查询与辅助Deep同时待执行，剩余额度只足够一项并须保留C6
- **THEN** 先执行关键确定查询，其他建议记录资源原因，C6准确区分已执行、复用及未执行，不宣称全部问题已回答

#### Scenario: Final synthesis proposes another lookup
- **WHEN** C6提出未来补查建议但没有本轮可执行binding
- **THEN** 按未来建议读取与保存，不因此伪造已执行状态或启动新调用；其阶段合同与C3执行计划约束明确区分

### Requirement: Every baseline round has an explicit C6 closing

C6 SHALL 收尾，无论C3是否有被接受的分析。已知前序失败且预算允许时 SHALL 用本轮实际可见事实独立综合。无有效模型回复时 SHALL 保存system/system_only的明确业务待核判断和后续核查方向，技术失败原因单独保存在Run停止原因、步骤错误及执行工件，不伪造安全定性、发现或成员分析覆盖。没有既有人工/模型判断且范围与输入仍新鲜时 SHALL 将系统收尾保存到Case当前说明；已有有效判断 MUST 保留。数据库不可用等保存失败 MUST 如实报告，不能称已收尾。

#### Scenario: Initial analysis is rejected

- **WHEN** C3返回的引用范围不合规但调用状态与用量已知
- **THEN** C6仍在原额度内执行，使用冻结事实及实际可见材料，不以拒收C3作为已验证分析

#### Scenario: No accepted final model reply

- **WHEN** C6回复格式不合法或模型不可用
- **THEN** 保存系统来源的业务待核判断，原因另存执行记录，C6交付阶段完成，模型失败原答保留；Case无有效旧判断且输入新鲜时可读取该收尾，不宣称有效成员覆盖

#### Scenario: An uncertain call interrupts execution

- **WHEN** 调用超时或取消且最终执行状态不明
- **THEN** 在可用存储上保存C6系统收尾，Run和原调用继续unknown并占槽，不重试、不标成正常完成

#### Scenario: A known empty provider extension is returned

- **WHEN** 最终原答仅带已确认额外字段analysis.conflicts_note且值严格为null
- **THEN** 保留原答并保存适配路径与前后hash，移除此空字段后重新执行全部原校验；其他额外字段、缺必需字段与引用错误不自动修复

#### Scenario: ClickHouse stores an IPv4 address as IPv4-mapped IPv6

- **WHEN** 原始OCSF与湖存储列分别使用IPv4和相同地址的IPv4-mapped IPv6表示
- **THEN** 按地址等价关系比较，不生成虚假矛盾；原始值与来源路径留存，真正不同的地址仍保留双方并标冲突

### Requirement: Capacity and capability claims match the validated scope

系统 SHALL 从本轮实际配置、冻结对象、工具选择器及请求容量说明可用和受限能力。四领域输出 MUST 不宣传成四次独立专家验证，200成员存储上限 MUST 不宣传为固定模型额度下的完成承诺。容量结论 SHALL 同时记录成员、必要资料/人工反馈/历史比较大小、profile和实际结果；缺源、超限和模型质量失败分别记录。

#### Scenario: Only a user object is available
- **WHEN** 案件只有用户名且没有现有认证工具要求的冻结主机
- **THEN** 明确该查询能力不适用或不可用，不编造主机绑定，也不由领域标签宣称已查认证历史

#### Scenario: Storage accepts a case larger than the model input
- **WHEN** 成员数在200以内但必要输入超限
- **THEN** 保留完整Case及已存材料，明确容量限制和本轮未分析项；不静默取前N条后宣称整案完成

### Requirement: Semantic acceptance follows facts through human feedback and final output

真实C→H→下一C验收 SHALL 逐项核对实际模型可见事实、引用、授权范围、补证结果与两轮结论变化。人工陈述 MAY 影响整案解释，但MUST保持其确认成员/对象/时间范围。程序结构校验、执行completed和needs_review MUST 不替代事实审核；复用既有良恶误判与待复核分列口径，不新增裁判模型或改写原答。

#### Scenario: A process starts and network bytes are observed
- **WHEN** 证据仅证明进程启动及端口/流量计数
- **THEN** 最终解释不得无据升级为脚本目标实现、具体应用协议、数据内容或外传成功；存在合理推断时明确依据和限制

#### Scenario: Human authorization covers one member
- **WHEN** 人工确认A在指定窗口的操作获准，但没有确认B的网络活动
- **THEN** 下一C实际读取该H版本并解释其对整案的影响，不能把B或其他时间自动列为已授权；原轮和H原版本仍可回查

#### Scenario: A new full executor uses the revised shared budget
- **WHEN** 用户启动新版本完整基础调查
- **THEN** 新Run冻结48000共享保守上限；既有Run的24000限额、原usage及失败保持，A/I上限不变；实际token用量仍取供应商回执，不把保守字节量标成实际消耗

#### Scenario: Case business fields do not contain execution diagnostics
- **WHEN** C6不能形成有效模型判断且Case需要系统收尾，或页面读取保存的Case
- **THEN** 案件摘要读取cases.description、当前判断读取case_assessments.conclusion；技术原因留在Run/步骤/工件的执行详情，不用拒收原答填充业务字段，历史版本保持可追溯

### Requirement: Published factual claims are bounded by the observed action and effect

新A/I/C3/C6执行合同 SHALL 使用版本化、有界的事实主张与来源范围；原始动作、该动作结果、命令意图、明确效果和人工陈述 MUST 区分。程序 SHALL 从冻结原件/实际查询构造可引用事实，验证效果主张所需的已登记前提，未知类型不得默认成功。当前判断、发现、摘要、领域理由、比较/影响及JSON/Markdown报告 SHALL 从同版校验后的结构化主张投影，MUST NOT 将未约束自由正文直接发布或仅验证附加主张后继续采用相矛盾正文。此约束不替代真实安全推断的事实审核，不新增裁判模型或自动修复调用。

#### Scenario: A launch and a rename are described as completed destruction
- **WHEN** 来源仅有删除命令的process_start/success及一个file_rename/success，模型声称删除、加密完成或说明文件已生成
- **THEN** 无对应明确结果的效果主张被拒，原答和字段原因保留；合法来源ID不能令其通过，C6采用既有系统收尾规则，旧有效判断和原运行结果不改写

#### Scenario: A concrete effect has sufficient scoped evidence
- **WHEN** 合法来源明确报告指定对象的删除结果，另有已关联的新文件创建和内容证据
- **THEN** 只允许各自范围内相应效果表述；删除结果不证明加密，全案影响不由单对象推定，文件创建不能单独证明内容，未知授权仍未知

#### Scenario: Valid structured claims accompany exaggerated prose
- **WHEN** 模型主张集合只含启动和改名，但自由说明中写成加密或外传完成
- **THEN** 新执行合同不得让该自由说明进入任何业务字段或报告；若其违反新输出合同则拒收并保原答，不靠改页面文字或静默删句声称模型质量通过

#### Scenario: Old outputs are read after the execution contract changes
- **WHEN** 新Run使用新的内部主张合同，用户同时读取旧版本输出
- **THEN** 按各自版本读取原件并适配现有业务出口，不给旧错误结果补造新验证状态；新Run不能自动降级为旧自由正文合同

#### Scenario: An A or I schema changes together with C
- **WHEN** 新事实主张合同改变A/I模型输出结构或实际请求
- **THEN** 实施准入分别核 A/I 完整 wire、输出预留和选定模型实际窗口；当前候选各 24000 累计 tokens/3000 输出，不能用 Case 容量代替 A/I 验证，也不能用替身计量证明未支持协议的真实兼容

### Requirement: Domain exclusion requires affirmative scoped support

领域not_applicable SHALL 具有明确可见的范围或排除依据。缺少数据、工具关闭、空查询及只有另一领域记录 MUST NOT 单独构成不适用依据；这些情形使用undetermined及限制。明确不在本轮范围只说明本轮不覆盖，MUST NOT 表述为全案不存在该风险。工具无选择器的适用性与案件领域适用性 MUST 分开。

#### Scenario: Cloud and phishing sources are absent
- **WHEN** 输入只有主机活动，没有云或邮件来源
- **THEN** cloud/phishing保持undetermined，不能因没有对应记录宣称不适用或不存在；仍可关联已有相关发现

#### Scenario: Explicit scope excludes one domain from this round
- **WHEN** 冻结调查范围明确不覆盖某领域且来源与范围有效
- **THEN** 可说明该领域本轮不适用并引用范围依据，不把范围决定写成排除该风险的事实证据

### Requirement: Evidence role catalogs guide generation without weakening rejection

A/I/C阶段 SHALL 向模型清楚区分可作直接依据的观察/有范围人工陈述、标签、历史判断和执行回执；发现及逐成员结果仍须满足各自角色和成员覆盖合同。Schema能表达的限制可前置，程序 MUST 保留完整本地验证，不自动补来源、改范围或提升角色。不同阶段 SHALL 共用动作/效果语义，防止A错误经I或C变成观察。

#### Scenario: A finding claims two members using evidence for one
- **WHEN** I发现声明A/B但引用仅覆盖A，或A的直接依据/C的observed混入source_label
- **THEN** 拒收并记录字段、角色或范围错误；不得自动补引用或缩小声明范围制造通过，已知前序失败不取消有资源的C6

### Requirement: Background selection records relevance and actual knowledge consumption

C2 SHALL 在最多2次来源调用内，依据冻结C1材料及预先定义的核查目标、合法选择器、来源能力及已有覆盖做确定性选择，为C4保留2次、总上限4次不变。问题 MUST NOT 依赖尚未发生的C3；先按问题相关性，同级按稳定既定顺序。高相关知识指导可以优于仅因存在用户名而入选的通用上下文；选中及跳过原因 SHALL 留存，不新增模型规划或暗中试查。知识导入、实际取回、进入实际模型请求、输出有效引用 SHALL 分别留证；知识指导 MUST NOT 冒充案件事实或授权。

#### Scenario: Detection guidance competes with generic context
- **WHEN** 标题检索可回答明确核查方法问题，另有未针对该问题的通用用户来源，C2只剩一席
- **THEN** 按已记录的问题相关性选择知识，保存另一来源未执行原因；真实消费验收须核请求正文及正确引用，不能只看库里有SOP或强制测试注入

#### Scenario: A selected knowledge lookup is empty
- **WHEN** 正常排序选择知识但受限查询返回零行
- **THEN** 调用计入原预算，保留空结果及范围，不宣称看过知识、不作为反证、不额外自动补查到所有来源都返回
### Requirement: Production page reads remain available independently of Case writes
The system SHALL allow authenticated, tenant-scoped Case and human-task GET routes when the page-read switch is enabled, while keeping all Case and human-task mutation routes gated by the Case API switch and write permission. Deployment verification MUST recognize the explicitly approved API read-only grants without accepting database write privileges.

#### Scenario: Read-only deployment serves Case history without enabling writes
- **WHEN** `SOCAI2_PAGE_READ_ENABLED=true` and `SOCAI2_CASE_API_ENABLED=false`
- **THEN** a caller with `cases:read` can read Case queues, details, page data, history, runs, results, artifacts, activities, frozen materials, tasks and task revisions, subject to tenant and parent ownership checks
- **AND** mutation requests remain disabled and GET requests do not write investigation data

#### Scenario: Both Case and page read switches are disabled
- **WHEN** both switches are false
- **THEN** Case and human-task reads remain unavailable
