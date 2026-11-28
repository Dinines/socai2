# 后置范围与原需求保留

本文件承接 tasks 已明确后置的第 8–10 步，状态均为**后置、未实施**。本次只是分清当前交付与未来设计，不取消需求，不把登记后置当作实现或验收通过，也不新增平行任务树。当前交付、未完成条件和归档结论统一见[范围核对](closeout-scope-20261118.md)；唯一实施任务入口仍是 [tasks.md](tasks.md)。

这些要求保存在 `specs/` 之外，避免正常归档时将未实现行为同步为现行主规格。恢复实施时须在当时的活动 change 中重新声明相应 delta，复核现行主规格和依赖，完成直接验收；不能将本文件存在视为后续能力已提供。主规格中原有的告警知识提交后同步行为仍保持原合同。

## 后置归属及恢复出口

| 原阶段与任务子范围 | 保留的业务效果 | 当前状态与归属 | 恢复实施时的必要出口 |
| --- | --- | --- | --- |
| 第 8 步；原 2.4 定向、2.7 定向 HTTP | 独立定向请求、实际范围和工具、建议或结论、请求/Run/Result 可追溯；不自动综合 | 后置、未实施；仍归本 change 第 8 步设计 | 依赖第 2/6 步；受理→固定输入→执行→保存→读取；同 Case 串行，局部结果不推进全案完成基线或直接采用 |
| 第 9 步；原 2.4 综合、2.5 知识复用、2.7 综合 HTTP | 用户明确提交新综合任务，恢复适用前序和所选定向来源，完成必要全案综合 | 后置、未实施；仍归本 change 第 9 步设计 | 依赖第 7/8 步；未点击不续跑，同 key 重放返回原 task；缺前序保留缺口及旧定向结果，真实全案覆盖才推进基线 |
| 第 10 步；原 2.6、知识队列及回执 | 新采用 A 在事务内登记维护任务，A 不等待索引，同一调度器最低优先执行 | 后置、未实施；仍归本 change 第 10 步设计 | 依赖第 2/3 步；A 提交与读取、实际卡/索引回执分开；无新分析 Run、无双派发/历史回填，未知外部写不自动重试 |

第 8–10 步已明确不作本期交付前置，但必须在归档交接中继续列为未实施。其余本期未完成项不能借此后置；尤其 D5/D6 收尾、整体验收、统一交付及 Git/父项目同步保持各自判据。RV11 新材料入口、附件正文模型能力及自选执行窗口沿原范围决定，不由本次文档整理增设需求。

## 原任务全文留存

下文是混合任务在本轮拆清范围前的原文，包含原本已在本期的部分，用于追溯；不构成第二套执行清单。本期部分继续由 tasks 的同号条目承接。

### 原任务 2.4

2.4 将已完成有效H正文/范围/引用变化及撤回纳入检查，下一轮完整C1–C6；不新增H-only。实现程序固定同Case上一轮实际结束的完整Run及可用Result，失败无结论时不回退当前采用或更早结果。保留H原文/角色/版本及运行中新采用保护。直接核只有H变化也走完整调查、无采用前置和上一轮无结论空态。人工定向P3按存储第11节及HTTP合同实现targeted请求/Run/Result分类和输入/工具/局部结果字段，先独立交付建议或结论；用户手动触发后续综合才提交新task、执行时新建Run，复用适用材料完成必要关联/综合，保留原答和采用保护。核无点击不续跑、同key重放、同Case串行、来源可追溯及无必要前序时如实报告；不默认完整重跑、不伪装成已有H，不推进定向局部结果的全案完成基线/自动窗口或停止标记；综合intent=synthesis、结果为baseline，真实完整覆盖才推进。

### 原任务 2.6

2.6 新采用A事务内登记knowledge_sync，最低优先且计入N，A提交不等待索引；目标版本替换旧同步路径，显式维护经过同一保护。保留卡资格/源版本/回执，核过期源、失败不改A、未知写不自动重试、无新分析Run及无历史回填，公共告警DTO保持。

### 原任务 2.7

2.7 依目标合同完成E01、Case investigations、E37及analysis-tasks列表/详情，列表附主体摘要，每个task_id及其重试持续可查，旧merged只读追溯；移除目标E11/E13/E36外部入口，不做兼容分支。阶段4补Case续建关系、事件全部关联及唯一活跃Case、创建/关联/移入的真实分配回执；关系读取明确容量续建和共享事件来源，供关联列表时按这两类优先级去重展示，当前相似Cases占位不算已实现；提供I选入成员/事件总量/未选范围/实际交付覆盖读取及容量失败原件，区分部分事件覆盖与交付状态；补齐定向提交和手动后续综合的异步合同，沿三层身份分别读取任务/Run/结果及真实来源；路径和字段按已确认HTTP合同第8节实现，不在本设计轮改已发布API。采用预览加入unfinished_analysis_tasks，原结果/步骤/工件读取保持。承接产品R1跨A/I/Case完整Run目录和同范围统计，R3/R4完整步骤/工件分页及定位，包含无Case、无结果失败/unknown且不受旧总量截断；调查核心提供用例、路径沿已确认HTTP合同。基本读取随阶段2、对应写入口随3/4，不留到最后；同步独立HTTP、Swagger、配置示例/部署清单和4177。受影响投影路径同步RV13可变配置及held定位/接续说明，保留未知不跳位，不扩展恢复专项。

## 原定向与综合规格全文

### Requirement: User directed analysis may deliver a recommendation or a conclusion independently
人工定向分析 SHALL 允许围绕用户问题/方向及可选现有工具形成建议、结论或待核事项，不强制新增证据或重跑完整Case链。结果 SHALL 保存实际范围、所用材料/工具及未执行原因，建议不得冒充执行、局部判断不得冒充全案覆盖或自动采用。定向结果交付后 SHALL 结束该次任务，可在同次回答中给出继续综合的建议及原因，MUST NOT 因该建议或保存结果自动提交后续综合任务；不另开模型调用判断其价值，不设置永久方向字段。

定向任务 SHALL 使用kind=case_investigation、intent=targeted，RunKind/ResultKind=targeted；请求及实际输入分别保存，明确范围执行前重核，缺省范围按执行前当前Case。工具 SHALL 限现有允许的只读工具，不接收任意SQL或连接参数。结果沿任务/Run/Result与工件读取，不复用暂停的AI会话，也不新增公共执行身份层。局部成功/失败 MUST NOT 推进全案完成基线、刷新自动窗口或设置/清除主体自动更新的失败停止标记；MUST NOT 作为上一轮完整调查或直接采用的全案判断。

#### Scenario: Existing evidence supports advice without a new observation
- **WHEN** 用户指定一个问题，模型根据已保存材料给出下一步建议而未取得新证据
- **THEN** 可以保存并交付该次定向结果，明确来源及限制，不为满足流程而伪造发现或自动重跑全案

#### Scenario: A targeted result recommends updating the overall analysis
- **WHEN** 定向分析得到可能影响全案的新发现或新判断，并建议后续综合
- **THEN** 先保存和交付定向结果并结束本次任务；未收到用户手动触发时不生成续接任务，周期检查也不因该结果自身自动续跑

#### Scenario: A targeted tool is known but unavailable for this Case
- **WHEN** 用户选择现有支持工具，但本案没有执行该工具所需的可靠时间或来源条件
- **THEN** 保存未执行原因，保留其他分析及建议；不编造查询结果，也不因该局部问题停止普通全案更新

### Requirement: Users explicitly submit subsequent synthesis as a separate asynchronous task
后续全案综合 SHALL 由用户手动触发，持久受理新的task并返回task_id，实际执行时再关联新的run_id；原定向任务、Run、结果和输入输出 SHALL 保持原样。续接 SHALL 关联选定的定向结果与实际使用的完整调查记录，在执行前保存真实材料身份/版本/范围及必要前序，再复用适用证据完成必要的关联整理和全案综合，不一律重跑已有检索和分析。新结果 MUST NOT 冒称覆盖未纳入材料、伪造新的工具执行或自动覆盖当前采用判断。

续接 SHALL 共用同Case串行、Case优先级、全局N和已有失败规则；手动续接意图不能被普通check吞掉，同operation_key重放仍返回原task，不新增对外身份层。仅因没有新证据或模型未建议继续 MUST NOT 拒绝用户手动综合；必要前序材料不可用时应如实记录，不能以局部结果代替缺失的全案依据。

综合任务 SHALL 使用kind=case_investigation、intent=synthesis，RunKind/ResultKind仍为baseline；不新增synthesis结果枚举。客户端提交同Case的targeted_result_ids，程序确定适用完整前序，并将实际复用来源与上一轮比较对象分别记录；前序/范围不足时记录prerequisite_unavailable，不伪造完整交付。只有真实完成本轮固定全案输入才推进完成基线和活动窗口，普通initial/check与定向/综合不得互相归并。

#### Scenario: A user requests synthesis after a targeted conclusion
- **WHEN** 用户对已保存定向结果手动触发后续综合，此时同Case仍有其他任务运行
- **THEN** 返回新的task_id并等待；真正开始时创建新Run并固定实际复用材料，保留各来源及原定向记录，完成后可分别读取定向与全案结果

#### Scenario: A user repeats the same continuation submission
- **WHEN** 用户以相同operation_key和相同内容重送手动综合请求
- **THEN** 返回原task_id，不新增一次逻辑任务；普通check不能替代这次明确的综合请求

#### Scenario: Reused materials cannot support the requested synthesis
- **WHEN** 续接执行前无法取得必要的完整调查材料
- **THEN** 记录实际缺口，不伪造全案覆盖或悄悄重跑完整链；此前已交付的定向结果仍可读取

## 原知识异步维护规格全文

### Requirement: Adopted alert triage can synchronize knowledge after commit
系统 SHALL 仅为本次新采用且材料对应的A，在业务事务内保存持久知识维护task；A提交完成 MUST NOT 等待嵌入/索引。knowledge_sync由同一调度器最低优先级执行并计入总N，不新建分析Run，沿原卡片身份/源资格/配置时限保存回执。统一目标版本替换旧提交后等待路径，显式维护也经过执行保护，MUST NOT 同时双派发或扫描历史回填。

#### Scenario: A newly adopted triage commits while synchronization is enabled
- **WHEN** 同步配置开启且新A判断被采用
- **THEN** A与维护意图持久化后A即可结束，后续任务保存卡/索引；受理不等于已可检索

#### Scenario: Synchronization is disabled or the result is ineligible for triggering
- **WHEN** 同步关闭、事务失败、A未采用/unknown、只重读，或仅Case H/告警人工反馈变化
- **THEN** 不自动派发知识维护，不改原判断和历史

#### Scenario: The source changes during synchronization
- **WHEN** 待领取维护的源已被更新，或索引过程中源变化
- **THEN** 重新核资格并保存被替代/来源变化回执，旧卡保留，不把过期卡报告为当前有效

### Requirement: Knowledge synchronization receipts remain separate from triage results
系统 SHALL 沿原A Run trace/工件读取维护意图、实际源版本、配置、起止、卡片及索引状态；内部knowledge任务不进入公共分析任务列表，不改变告警交接字段。失败 MUST NOT 回滚业务判断、伪造成功或自动重放未知外部写；模型分析和知识维护的状态分别保存。

#### Scenario: A card is stored but indexing fails
- **WHEN** 卡片已保存而索引明确失败
- **THEN** 保留卡及失败回执，A仍保持真实完成/采用状态，不称知识已可检索

#### Scenario: An external write is unconfirmed
- **WHEN** 知识写请求已发出但结果未知
- **THEN** 保留未知回执，本地收尾释放名额，不自动重试未知写、不要求人工解锁队列

#### Scenario: A synchronization receipt is read
- **WHEN** 用户读取原A Run的trace/工件
- **THEN** 可区分受理、被替代、卡片保存和索引完成，读取不派发新同步

## 原混合条款及本期拆分说明

下列原句一并保留上下文，不表示整句均后置。本期保留普通 H/完整调查、知识筛选、Case/A/I 调度、普通 check/rerun HTTP、补查窗口；其中人工定向、手动综合和异步知识维护部分归上表。

### 原H与定向/综合职责区分条款

来源：`case-human-http-flow` 的 `New analyses preserve human scope and later adoption decisions`。该混合段移出的原句为：

人工定向及手动后续综合 SHALL 保持与有效H更新的区别；

该约束随人工定向分析、手动全案综合（第8–9步）保留，恢复实施时仍须区分请求意图，不能把定向问题伪装为有效H更新。原段中本期H原文/范围、采用保护、附件及评论角色的要求继续留在当前delta。

### 知识复用原条款

C3、Deep、C6 SHALL 使用本Run冻结且适合本步骤的知识，按真实身份/版本去重并保留查询出处与独立角色。模型输入 SHALL 先满足本案必要材料、人工反馈、反证及前序引用，再按配置容量选完整可选条目；MUST NOT 改写正文、将同卡多命中计为独立证据或丢弃必要来源凑容量。Case自动更新和用户完整重跑仍走完整C1–C6，不新增反馈专用C6-only路径；人工定向后的手动综合按case-human-http-flow执行，复用知识仍须恢复真实来源和必要依据。

### 调度、HTTP 和窗口原条款

系统 SHALL 由唯一调度器领取task/pending，多个生产者仅追加；总N为正整数配置默认1，同主体同分析kind最多一个本地活动执行。pending优先且最多检查本轮开始P条，忙或未到重试时间放回尾部；余下容量按Case>A>I>知识维护处理普通队列，各队列最多其开始长度。N MUST NOT 被误用为最多检查条数，不批量重写队列或从中间重排，不在每个HTTP worker启动领取循环。

- **WHEN** 同Case有普通check、显式rerun或后续定向/综合请求

- **THEN** 各请求保留意图且同Case串行；普通材料无变化不能吞掉明确rerun/定向/综合请求

E01 SHALL 返回Case与首轮分析任务，Case investigations和事件diagnose SHALL 接受operation_key+mode(check/rerun)并异步202。analysis-tasks列表/详情 SHALL 提供持久状态与真实结果链接，列表含主体更新摘要。目标版本 MUST NOT 保留旧E11/E13两阶段启动、E36手动A或同步兼容分支；未知输入422，不静默忽略旧比较/时间窗参数。人工定向及用户手动后续综合的输入/结果字段按已确认Q1流程补齐，不自动续接；默认内部窗口及日志条数按Q2提供，不新增外部时间参数。Q3不新增同告警材料版本接口或重新分诊。模型读取附件正文非本期要求，自选执行窗口是独立未定扩展，不建立猜测占位API/表。

自动调查 SHALL 在时间限定工具调用前按相关告警的最早/最晚真实发生时间生成默认查询起止，分别向前/后扩展默认3600秒，并保存实际窗口、来源和profile配置；两项扩展量 SHALL 可分别配置，不能因外部提交不收时间参数就将内部窗口一律留空。完整调查按本轮选入成员、定向问题按实际相关成员推导，不因扩大查询时间自动新增Case成员。系统 MUST 区分本轮查询窗口、候选探索日期、用户自选调查执行范围及历史知识独立回看策略。

### 原测试配套范围条款

测试配套 SHALL 覆盖正常告警入站、A/I、Case完整调查、持续更新、H、定向、手动综合、采用/结束及对应HTTP保存读取，保留尚未实现能力的用例、数据和接口依赖。

本期规格明确区分可执行场景与后置能力的用例/数据合同/接口依赖，保留后者不等于定向或综合已实施。
