# 前轮程序观察材料的保存与读取一致性

## 本步目标和边界

本步归入 `complete-socai2-investigation-chain`，使用 spec-driven。目标是使合法前轮材料经过保存、读取后仍能按冻结来源与版本核验；真实正文、引用、范围、类型或值的改变仍必须被拒绝。仅定位并修正该一致性问题，不将调查执行成功、模型质量或页面交付混为一个结果。

当前状态为 **P2/P3 本地修正及独立验收完成**。生产仅改 `case_previous_analysis.py`；必要直接测试、已保存工件的一次本地重放及统筹独立结束审计已完成。P1 的具体运行分类仍留原私密报告，不在本文件转述。既有 21 发布批次已按其计划收尾，本步不部署、不重启服务、不创建调查任务、不调用模型，不改变历史原件或已结束批次。Git、index、PROGRESS 由统筹维护。

本步不修改告警交接字段、数据库 V1 原件、模型输出正文合同、引用权限、事件输出设计、预算或默认业务值。不新增通用恢复/测试框架，不用样本 ID、主机、来源值或厂商特判通过本案。

## 保存与读取链

| 环节 | 输入与程序职责 | 必须保留的关联或原件 |
| --- | --- | --- |
| 冻结 Case 输入 | 固定成员范围、`case_boundary.program_output`、`observation_literals`、业务字段映射与原始来源 | 原来源路径、类型、值、成员、记录分组；版本不可由当前默认替代 |
| 受理与程序装配观察描述 | C3 `typed_unit` 先以原生 `normalized` 按首次出现去重引用数组，再 `restore_observed`；部分 C6 复用 `c3.admit`，完整 C6 在完整对象上做同一归一化，再由 `observed_text` 生成 statement | receipt 保留原答单元，发布摘要是受理派生值；引用处理事实保留同源 quality/citation_review，不由模型补写程序观察正文 |
| 保存工件和发布摘要 | `Artifacts.content_json` 保存 JSONB；`baseline_store.encoded/digest` 对对象键排序后计算保存大小与摘要 | 原件、输入工件、stage delivery、已发布摘要各自 ID、SHA 和所属 tenant/Case/Run |
| 选择前轮 | `case_comparison.select_previous` 先返回选择结果，只有后续冻结事务成功才持久化；`case_previous_analysis.freeze` 读取被选 Run 的材料 | 成功冻结的指针优先；准备失败可能没有已保存指针，不能用事后当前 `latest` 替代 |
| 验证与投影 | `Sources.read/receipt` 核所有权、摘要与回执；`project.analysis` 恢复对应单元并核正文 | `summary_artifact_id`、`receipt_artifact_id`、`input_artifact_id`、`unit_path`、原始单元及映射必须同源 |
| 当前任务准备 | 前轮材料冻结位于 Case 准备事务内，之后才提交当前 Run/输入关联 | 本任务的失败与未产生 Run 状态如实保留，不补造 Run |

源码入口：`services/api/app/socai2/case_program_output.py`、`case_previous_analysis.py`、`case_comparison.py`、`baseline_store.py`、`analysis_case_executor.py` 及 `services/api/app/models/socai2.py`。

## 源级假设与分类判据

先区分两条直接同链路的源级风险：其一，受理过程先对 source 数组做既有按首次出现去重，前轮读取却直接用 receipt 原始单元重建；其二，`observed_text` 对 `row['value']` 调用未指定 `sort_keys` 的 `json.dumps`，工件哈希却使用排序后的 JSON，工件列为 JSONB。两者均可能使当前整段字符串比较失败，源码复现不能代替本笔实际分类。

定向对照先验证身份、所属、摘要、版本和回执绑定，再分别记录以下分类，完整值只留私密文件：

- 原 support 重建不等，但复用原生 `normalized` 后重建相等；归一化与同源 receipt/summary 的 processing 事实分别核对；
- 原生归一化后仍有 JSON 对象键次序差异，逐源类型、值、路径、原记录/成员组及应采用的 support 次序均一致，恢复旧键序并用旧 formatter 完整重放相等；
- 来源 ID、成员/记录分组、字段/路径、冻结版本或所选留存单元不同；
- 实际正文、类型、值或数组顺序不同，或原件/摘要/回执不可信；
- 既无直接冻结引用，也无法按原任务时间窗、提交前保存记录及同 Case 不可变 Run/来源目录唯一重建前轮身份。

不通过普通 `dict == dict` 把 `false`、`0` 或不同数值类型混作相同；不按字符串替换、正则删除或全文语义相似判断“只有格式差异”。数组顺序和重复项、字符串内容、未知字段、有效空集合均有原合同含义。对象键次序仅能在明确定义的 JSON 对象内部分类，不能扩展到 statement 的任意文本、来源次序或成员范围。

## 步骤、依赖与必要验证

| 步骤 | 本步工作与依赖 | 必要验证及通过证据 |
| --- | --- | --- |
| P1 源码及定向对照 | 先 strict；复核保存/读取合同；复用仅结构占位符的最小离线复现；沿本 task 直接引用或有界时点重建使用既有证据，必要时只读必需工件 | 复现注明是离线结构实验，不能冒充真实 PG；私密报告区分直接引用、时点重建、摘要、各类差异与未知，不输出实际值/布尔到会话；向统筹提交源级判断与短方案 |
| P2 最小通用修正 | 统筹独审后，仅按 P1 证据选择装配确定性、冻结版本重放或来源关联中的具体修正位置 | 不弱化来源/正文校验，不覆盖旧文本，不改用当前配置解释旧版本；无关生产文件不动 |
| P3 保存—读取直接验收 | 复用已有前轮材料和程序观察测试，仅补修正直接涉及的环节 | 合法来源输入→装配→实际保存读取→前轮投影能保持内容与关联；改值/类型/数组顺序/引用/范围仍拒绝；原件 SHA 与原失败不变；独立结束审计 |

P1 优先检查本任务是否实际保存了前轮指针；没有指针并不阻断诊断。可结合本任务时间窗、原提交/跟踪时保存的具体记录，以及同一已确认 Case 的不可变 Run/来源目录作一次有界只读，按原选择规则 `started_at DESC, id DESC` 核实当时的首条是否可唯一确定且属于提交前已记录范围。更老的稳定 Run 不构成歧义；任务窗口内出现可能改变首条的新候选，或时点/来源依据不足时，才保留未知。直接引用和按时点重建分别记载，不能把重建结论叫作被冻结的指针，也不直接使用事后当前 `latest`。补读限定固定 tenant、Case 和时间窗，确定 Run 后再按 artifact ID 读取必需工件；不扫描全表、扩展其他任务或通过新模型请求补材料。

上述时点重建仅是 P1 私密取证方法，不进入产品选择逻辑，不给 `select_previous` 或业务冻结增加回退路径；既有 Case 选择/冻结合同保持原职责。

P2 已选定只重放既有原生受理归一化。以下对象键次序方案保留为源级备选，不进入本步生产实现；不能只给当前 renderer 加排序就宣称历史兼容完成。后续若需处理该类差异，仍须先明确合法表示的验证和真实改变的拒绝方式，不以默认降级掩盖。

### P1 条件化源方案（保留备选）

P1 私密报告已由统筹在其获准的数据范围内独核，并选定下文最小 P2 落点。以下保留原条件化方案及未实施候选，不能将源码复现直接认作实际运行结论。**本步只补既有原生受理归一化，不实施 v3。**

1. **原生受理归一化优先。** 若本次差异都能由原生 `case_citation_quality.normalized` 后直接调用旧 `observed_text` 逐字解释，P2 优先仅在 `case_previous_analysis.py` 的程序观察重建处复用同一受理派生规则，再保留现有完整文本相等校验。原单元、原 support 数组及原答不修改，来源/范围/正文检查不放宽，不修改 `observed_text`、runtime policy 或配置版本。本步已选该方案，不另增旧路径或回退分支。新增局部 review 仅用于重建验证，不伪装成历史处理回执或写回旧工件。
2. **处理事实按同源核对，不能增设日志门槛。** summary 的 stage delivery 指向 receipt，receipt 的 input/original 指向同一冻结材料。C3 和部分 C6 的 `quality.processing` 经 `remap_review` 使用原单元 bracket path；完整 C6 的全对象归一化使用 dotted path。离线分类复用这两种既有路径，记录原生 before/after 与同源 processing 的对应或缺口，不能只因路径表示不同判错，也不把必须有新增日志另设为业务校验条件。
3. **确有残留键序差异时，才讨论受限旧版重放。** 仅对原始留存 finding 不含 statement 的程序观察，读取保存文本中已知 support 组的 JSON 槽位。每个 ID 必须属于本 finding 的冻结来源；所示字段/路径、原记录/成员组必须和该来源映射相同；严格 JSON 解码拒绝重复键、非有限数、非旧 compact 编码及额外正文，逐源排序编码比较保留数组顺序及 int/float/bool/string/null 区别。只在本地边界副本中恢复这些对象键次序，其他字段和规范内容须完全相同。最后用不变的 support 顺序和相应旧 v1/v2 formatter 完整重放，结果必须逐字等于保存文本。模型/人工撰写的正文不进入此通路。
4. **旧 v2 显示行拆合的边界。** v2 分组键包含 JSON 字符串，同字段同值的两份来源可能仅因原对象键次序不同显示为两行，JSONB 后又变成一行。不能用当前重建文本的严格前缀提前将它判为真实分组错误。按原保存行逐源恢复键次序后，原 formatter 自行重现这些显示行；真正的来源归属、字段、成员/记录组、support 顺序/重数改变仍不能重现。源级检查包含该直接影响场景及来源/字段/类型/数组/顺序改变仍拒绝。该受限候选最多增加 `case_program_output.py` 的内部验证辅助；若原生归一化已解释阻断，整个键序兼容实现后置。
5. **保留拒绝和证据。** 无论选择何种窄修，所有权、SHA/size、原件、身份、引用、范围和版本校验不移除。仍不能重放的单元保留原具体错误与 StoreError/任务失败链，不跳过、不补默认值、不写历史原件。不将旧失败追认成功。
6. **直接验证复用现成原件。** P1 的原 support 直接重建、原生归一化直接重建、原 support 键序重放、归一化后键序重放分别保留。P2 只补实际修正直接影响的测试并复用已保存/读回工件做一次本地重放；原答、原 statement、SHA 和旧失败保持不变。不建库、表、持久业务样本或真实模型任务，不追加 PG 访问。

旧严格前缀原型与第一次分类保持原件。补充原型和分类位于 `.local/validation/previous-analysis-consistency-20261128-01/legacy_order_replay_prototype.py`、`replay_saved_legacy_groups.py` 和 `legacy-order-replay-01/`，只复用现有已保存工件，没有增加 PG、网络或模型调用。它们是离线诊断代码，不是已安装的生产能力或通用兼容框架。

### 已选定的最小 P2 落点：重放原生受理归一化

统筹已确认本阶段执行此范围。源级键序复现和备选解析保留为后置资料，不随本步实现：

- 生产改动仅落 `case_previous_analysis.py` 中 `findings/observed` 且原单元没有 statement 的现有核验分支。复用原生 `normalized({"findings": [raw_unit]}, review)["findings"][0]` 作为观察描述重建输入；review 为局部重建对象，不覆写 receipt 的原单元或原 processing。之后仍调用冻结边界的旧 `observed_text` 并执行完整文本相等判断，仍抛原 `previous_analysis_program_observation_mismatch`，其他身份、范围、SHA 和正文检查原位保留。
- 对 C3、部分 C6、完整 C6，引用按首次出现去重这一派生规则相同；不同 processing 路径是诊断记录的来源表示，不能成为额外业务准入条件。不新增 processing 写回、补齐或通用日志适配。
- 必要直接用例放在现有 `test_socai2_previous_analysis.py`：以真实原生受理函数形成“原单元保留重复引用、发布值按首次出现去重”的工件，确认前轮读取得到同一原发布 statement，原单元/旧 review 不变；覆盖 C3 及 C6 完整/部分接线。复用已有损坏/跨主体/范围拒绝测试，补一个实际正文改变仍触发原校验的对照即可，不展开 JSON 兼容矩阵。
- 只复用当前已保存/读回工件做一次本地程序重放，记录校验路径与保存/读取的来源关联；原件 SHA、旧失败和已保存 statement 不改。没有新真实 Run、Case、模型测试、数据库写入或部署。局部验证通过仍不代表旧调查任务通过或本 change 收口。

JSON 键序兼容解析、v3 renderer、runtime policy 和默认配置均明确后置，不能随该一文件窄修一并进入生产；不添加额外降级路径。新增产品规格只覆盖受理派生与前轮重建的一致性，键序兼容仍仅保留源级备选说明。

### v3 的同步影响（源级备选，非本步先行实施项）

若后续确需让新生成的 JSON 表示及分组键确定化，须明确新冻结版本，不能全局改排序后以新默认解释旧材料。此升级当前后置；其最少同步点已核清：

| 位置 | 后续 v3 的必要影响 |
| --- | --- |
| `case_program_output.py` | `VERSION` 作为新生成 v3，`READ_VERSIONS` 保留 v1/v2/v3；显式按冻结版本区分 v1 布局、v2 旧分组键与 v3 排序后的值/分组键，不能把原 `== VERSION` 直接改常量后让 v2 落入 v1 分支 |
| `runtime_policy.load_case_profile` | 可读版本集合由 v1/v2 扩到 v1/v2/v3，历史配置仍可读取，未知版本仍拒绝 |
| `RuntimePolicy.require_execution_profiles` | 新执行合同若切 v3，则要求 v3 且 `c3_coverage is True`；这是新任务入口的同步切换，不是在旧边界上更改版本，不能只改可读集合而遗漏此处 |
| `case-input-v1.json` | 默认 `program_output.version` 同步为 v3，instruction 和 coverage 语义保持；配置身份摘要随文件变化，新冻结记录保存实际版本，历史 profile 与工件不回填 |

P2 生产范围已由统筹选定为既有原生受理归一化的一文件修正；上述 v3 备选不构成部署、模型测试、配置发布或四文件扩展的执行决定。

必要直接测试复用：`services/api/tests/test_socai2_previous_analysis.py` 的前轮留存、损坏/跨主体拒绝和范围检查，以及 `test_socai2_quality_continuation.py` 的程序拥有正文校验。只补 C3、部分 C6、完整 C6 原生受理后的文件保存/读取，以及真实正文改变仍被拒绝的对照；不增加对象键序兼容测试，不扩大到全仓回归、压力矩阵或新真实 Case 模型测试。

## 证据与交接

源级设计与规格保存在本 change。本步私密材料入口为 `.local/validation/previous-analysis-consistency-20261128-01/`，原任务和诊断仍在 `.local/validation/model-exception-release-prep-20261128-01/`，不覆盖前轮证据。

会话只接收源码分析、Schema、方案和报告路径。新增实际差异值及运行布尔留私密报告，由统筹按用户确认的脱敏范围独审。CLI 校验、源级复现或文件生成均不代表实际业务通过。

P2 代码及直接用例已完成：新增 C3、C6.partial、C6.complete 三项原生受理→文件保存→读取用例通过；绑定修正前 `project` 时三项均触发原 `previous_analysis_program_observation_mismatch`。统筹的既有定向组为 16 项通过、1 项旧夹具身份检查失败；该失败在旧 `project` 下同样发生于 `case_model_boundary.selected_profile`，本步保留后置，不改旧夹具或放宽身份校验。统筹另行完成 C6.partial 新用例的独立前后对照，复用这些证据，不重复全组测试。

本地工件重放仅执行一次，使用 P1 已保存的历史冻结成员范围隔离验证器；结果、来源关联及原件前后摘要保存在 `.local/validation/previous-analysis-normalization-p2-20261128-01/actual-replay-01/`，不在此公开实际布尔或投影内容。工程交接入口为 [P2 验证记录](../../../docs/operations/evidence/previous-analysis-normalization-p2-20261128-01/README.md)。P2/P3 已通过[统筹独立结束审计](../../../docs/operations/evidence/previous-analysis-normalization-coordinator-20261128-01/review.json)：获准最小报告确认完整本地读取、原文/引用/摘要与旧原件保持。实际工件使用历史冻结成员范围隔离验证器；本次没有新 PG 写入或真实任务重跑，不追认旧失败成功，也不核销整个 change、模型质量或 8181 交付。
