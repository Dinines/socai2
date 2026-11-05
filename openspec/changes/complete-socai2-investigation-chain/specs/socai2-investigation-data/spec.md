## ADDED Requirements

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

模型输入 SHALL 按阶段任务组织必需语义组，在预算内优先保留成员核心事实、同次已有判断及理由、适用人工限定和明确反证；可合并重复身份/来源元数据，但 MUST 保持值、类型、来源及成员映射。完整材料保存在库，实际模型视图 SHALL 分别说明材料保存完整性、分诊适用性和实际可见性，MUST NOT 将prepared或发送成功等同模型完整阅读。

#### Scenario: Optional raw leaves compete with received detection context
- **WHEN** I在核心事实、同次分诊及时间之后仍需选择检测规则/评分与可选原始叶字段
- **THEN** 先轮询各成员的已有detection原值，再填可选元数据及原始叶字段，仍标source_label；单项guard和大小上限保持，无法容纳的项按原路径明确记录省略，不改为观察或提升模型预算

#### Scenario: Repeated metadata displaces a valid triage
- **WHEN** 原冻结输入含有效同次分诊，但平铺重复元数据占用视图额度
- **THEN** 先去重复并为必需组预留空间，完整保留判定及配对理由/评分；不能只留分数或把省略分诊标成已发送

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

#### Scenario: A completed task is renamed without changing feedback
- **WHEN** 任务只改标题、负责人或期限且完成事实不变
- **THEN** 不因revision ID变化将已冻结反馈判为失效

#### Scenario: Material changes after a result was adopted
- **WHEN** 同一成员收到新材料或人工反馈发生实质变化
- **THEN** 读取当前判断返回输入过期及原因；历史Run、结果和采用事实保留，下一轮由用户明确启动

### Requirement: Evidence hashes and background selection preserve meaning

系统 SHALL 保留明确SHA256字段及明确声明SHA-256算法的有效原值和路径，冲突保留双方，不从长度推断算法。C2 SHALL 在原Tool总预算及C4预留额度内按冻结对象相关性选择来源，保存优先级依据和未执行原因；空查询也计调用。

#### Scenario: A case has explicit IOC and user selectors
- **WHEN** 情报与UEBA已连接且具有冻结的合法对象
- **THEN** 它们优先于通用历史查询；主机/仅检测等不同对象组合有不同选择，超预算来源仍明确跳过

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
