## Purpose

记录截至2026-10-23已有证据支持、并按2026-10-24用户安排收尾的告警与调查服务端迁移基线合同。正式已有告警经Kafka/Fusion进入自动分诊、关闭或实际调查，人工调查、所选工具/PG知识、链图及结果/Markdown读取已有各自证据。合同不等于所有场景、来源、分支或模型语义质量通过；partial、错误及unknown保持原判定。

适用版本须分开：`Validate manual findings before downstream adoption`和`Preserve completed tool material through investigation stop`为10月23日已验本地交付，当时未部署；其余接线按v1、full及各原回执的条件适用，UEBA联动本地联合通过不代表常驻开启。线上v1与本地小修不得合并成一个已发布版本，收尾未重新验证生产运行态。

背景事件入湖及相关调查验证由独立调查开发承接，本change不重复或代其验收；完整向量/全部来源、上游占位、独立调查新设计、报告/预算等质量完善及运行专项不作为本次收尾前置。将来行为变化使用独立change。详见docs/operations/migration-closeout-20261024.md；原失败/权限/预算/unknown/积压及真实响应审批约束保持。

## ADDED Requirements

### Requirement: Validate manual findings before downstream adoption

人工四节点调查 SHALL 在Forensic完成后、Responder和Report采用前执行相同的程序校验，run与stream MUST 使用同一规则及实际Run身份。校验只声明其标识匹配能力，不能把匹配通过当业务断言验真；既有角色、模型参数及四次调用上限保持。

#### Scenario: A forensic output cites an unsupported indicator
- **WHEN** Forensic结论被已有标识检查降级
- **THEN** 响应和报告采用明确待核状态及补证交接，模型原候选仍留审计；返回结构与持久报告一致，不以末尾单独降分代替前置采用

#### Scenario: The model input or output requirement changes
- **WHEN** 本批修改模型可见输入或输出采用要求
- **THEN** 先完成直接请求/解析/下游合同测试，再以当前模型及全新隔离样例有界核查实际请求、回复、采用；替身与真实结果分别记录，失败不被后续修正覆盖

### Requirement: Preserve completed tool material through investigation stop

工具执行 SHALL 每次完成即记录结构状态及模型实际可见内容，并在Deep异常、时限或graph外层时限收尾时保留已完成材料。MUST 区分原始结果指纹、保存正文、展示preview及裁剪；未持久成功明确gap，不重跑查询补造回执。保原消息文本、轮数与token/时间上限，不新增总结模型调用。

#### Scenario: A data row contains an error field
- **WHEN** 调用顶层成功但rows内数据包含error文本，或顶层状态超出200字符展示范围
- **THEN** 使用顶层结构及实际异常识别执行状态，preview不参与判断，成功空结果和缺源分别记录

#### Scenario: A later call exceeds the deadline
- **WHEN** 至少一次工具完成后，下一模型/工具异常或Deep/graph到时停止
- **THEN** 已完成参数、调用状态及模型可见正文仍有回执或明确留存缺口；partial交接列停止原因与未完成材料，不把末工具JSON作为narrative，不继续新模型调用

#### Scenario: A tool receipt cannot be persisted
- **WHEN** 工具事件/正文写入失败或与旧seq冲突
- **THEN** 不覆盖旧回执、不报告新的持久成功，记录留存缺口并继续交付已有partial材料；工件仅关联实际同tenant/Run事件


### Requirement: Prepare the alert graph at the Kafka investigation intake

Agents SHALL 在合法fused Kafka告警的公共消费入口、原恢复/抑制/模型分诊之前，按真实tenant及canonical Alert准备图；MUST 复用原可信API、独立writer和PG归属校验，不修改Fusion或等到形成Case/升级Deep才写。正常写权限及功能配置缺失、政策禁写或准备失败均为明确缺口，不宣称投影成功，不改变原分诊、DLQ和offset确认合同。

#### Scenario: A valid live alert is consumed
- **WHEN** schema合法的fused消息进入live消费入口，原profile/shadow允许写且链图开关与独立writer可用
- **THEN** 先以消息的已选canonical Alert和tenant请求原prepare，再进入原triage；后续抑制、关闭、首次结果恢复或升级均不跳过该入口准备，内部triage重试不重复POST

#### Scenario: A real isolated delivery prepares the graph before triage
- **WHEN** 本地原Kafka消费者读取独立测试topic中的全新合成告警，准备请求经原API认证读取真实PG并写入Neo4j
- **THEN** 在分诊入口能核同tenant/canonical Alert的成功回执及真实图节点/关系；有界观察可在此主动hold且不提交offset，不将该接缝验证称为完整分诊、模型调查、Fusion新联合或常驻启用

#### Scenario: A context reader is used during an escalation
- **WHEN** 自动Graph/Deep预取该Alert的链图上下文
- **THEN** 只执行GET并采用匹配tenant/Alert的可信消费入口准备回执；不在读取中再次POST，不接受消息或模型伪造的回执，不因有真实Case而混淆Alert入口来源

#### Scenario: The graph preparation is not allowed or fails
- **WHEN** 缺独立writer、writer复用reader、review-only/shadow禁止写，或HTTP拒绝/异常/成功回复身份不匹配
- **THEN** 不越权写、不把失败当成功空图，记录明确状态/原因；旧triage、预算、DLQ和offset规则保持，功能未启用时不新增请求

#### Scenario: The current alert belongs to a large case
- **WHEN** 显式Alert准备解析到同tenant真实Case且当前Alert不在Case前50条之内
- **THEN** 仍投影这条已核当前Alert及其实体，并仅补真实Case关联；不批量改投整个Case、不创建虚假Case，显式Case准备的原有上限保持

### Requirement: Preserve the upstream UEBA trigger contracts

系统 SHALL 沿用原UEBA的上游事件投喂与直接HTTP评分入口，并明确租户、实体、数值特征、来源字段和输出交接；MUST 区分共享normalized消息、UEBA预提取兼容消息及HTTP字段，不以新实体名单策略或滑动窗口改造替代本批接入说明。基线样本不足不得解释成已证明正常，既有算法/权限及原测试保持。

#### Scenario: An upstream normalized event names a user and a host
- **WHEN** 合法tenant的normalized信封具有ocsf_event、user及hostname且能提取数值特征
- **THEN** 原提取器按user优先选择一个实体参与评分和基线更新，不宣称同一消息自动对全部实体建基线；共享topic使用其原normalized合同

#### Scenario: An upstream producer supplies an explicit entity and features
- **WHEN** UEBA兼容预提取消息提供合法tenant、entity_id及至少一个可数值化特征
- **THEN** 沿原entity_type/entity_id/features进入计算，预提取来源字段使用event_id；该格式不被宣称兼容共享topic的其他消费者

#### Scenario: A caller scores an entity over HTTP
- **WHEN** 具有服务认证及tenant作用域的调用方提交原HTTP评分请求
- **THEN** 沿原source_event_id与实体/特征评分并持久，返回异常或null，不声称HTTP调用自动发布Kafka异常；null也不得单独当作实体正常的证明

#### Scenario: Fusion consumes a matching behavioral anomaly
- **WHEN** UEBA联动开启且告警实体在同tenant有有效异常缓存
- **THEN** 沿原risk_level规则采用最高等级的一项信号，调整confidence/anomaly并保留说明；不叠加多个实体、不改变priority或原上游risk_score。关闭或无匹配时不加UEBA分；文档记录开关、topic、TTL及实例的实际验证边界

#### Scenario: A real UEBA anomaly reaches Fusion through Kafka
- **WHEN** 独立测试实体已有满足原门槛的基线，原UEBA Kafka消费者收到偏离输入并实际生成异常
- **THEN** 核对真实PG异常与输出消息、Fusion实际缓存及后续新告警的保存/发布分数；保留source/anomaly/alert ID与消息坐标，不以手写异常或内存替身冒充真实联合验证，不连带启用正式消费或模型

### Requirement: Authentication lake queries respect the stored IP type

认证事件补查 SHALL 使用与原湖仓IPv6 source_ip列兼容的非空地址过滤，并保留租户/用户/时间窗口和行数约束。查询失败与成功空结果 MUST 继续分别表达；本地修正不得追认此前失败或触发旧模型Run重放。

#### Scenario: A user has no matching authentication event
- **WHEN** 已接入的原IPv6事件表收到合法参数化用户认证补查
- **THEN** 非空IP过滤不因空字符串转换失败，返回原ToolResult成功/空行或匹配行；不将零行单独解释为账号安全

### Requirement: Single IOC enrichment uses the upstream service contract

调查单项IOC增强 SHALL 沿原工具参数传值，以Go增强服务要求的value/ioc_type字段请求，不以type代替ioc_type。MUST 保持来源为空时不作已证明安全的判断，不开启新的provider或改变IOC提取算法。

#### Scenario: Recon enriches one extracted domain
- **WHEN** 调查调用原enrich_ioc工具并配置可达的原增强服务
- **THEN** 请求使用合法value/ioc_type，得到原服务返回或明确错误；不因字段错配固定返回HTTP400，也不把无来源零分当信誉通过

### Requirement: Investigations consume existing chain and path context

调查 SHALL 复用原Case攻击链算法、Case路径查询及图投影函数，按真实Case/tenant/关联告警准备可追溯的链/图上下文。MUST 区分已有函数、已开启配置、已投影数据、模型实际消费及Run持久结果；不得仅开启full或graph开关便宣称端到端完成。具体实现/验证/发布范围以链图及v1回执为准，不将PG回退、候选关系或未验分支写成完整因果路径。

#### Scenario: An investigation prepares a real case graph
- **WHEN** 已授权Case调查读取同tenant真实PG Case及关联告警
- **THEN** 由可信API在本次调查范围定向准备原实体、告警和Case关系，不将模型推断写为观测；投影节点携带正确租户/标识，边的source/target可解析到实际节点，完整图与PG回退分别记录

#### Scenario: An automatic run has no real case association
- **WHEN** 自动Run没有可核实的同tenant真实Case关联或存在歧义
- **THEN** 以同tenant canonical Alert为原链算法种子，并复用已有Alert邻居/影响范围查询；Case专用路径明确not_linked，不将Alert ID、Fusion incident或旧Run占位当Case，不自动创建Case或改写旧Run。薄Alert链读取入口须先核告警归属，原Case接口、算法/窗口/评分保持

#### Scenario: Projection and read credentials remain distinct
- **WHEN** API或后台服务为同tenant真实Case/Alert准备图资料
- **THEN** Case写入口可在可信API内确定性投影；独立准备POST要求Case/Alert写权限，GET只查原资料；模型和七权限只读凭据不得因此得到写图权限，缺写配置明确记录，不在读取中隐式投影Neo4j

#### Scenario: Existing orchestrations use the retrieved context
- **WHEN** 同Run已经成功取得有界链/图材料或明确缺源结果
- **THEN** 默认四节点、Router专业分支及Deep通过各自现有输入接缝实际获得摘要与来源/缺口，保持原编排和固定模型调用次数；仅state中存在字段不足以证明消费，末端AttackPath优先复用本Run已取材料

#### Scenario: The case has an empty chain or only a fallback graph
- **WHEN** 查询成功无候选、图缺源/失败或返回PG重建关系
- **THEN** 分别记录窗口/来源/错误或回退和覆盖范围，不解释为已证明无攻击、完整传播路径或关系因果；候选评分不作为恶意概率

#### Scenario: A client retrieves the material used by one run
- **WHEN** 客户端读取该tenant有权访问的Run事件、工件及Markdown
- **THEN** 能定位该Run实际使用的Case/seed Alert、链/图有界结构、查询范围、来源/状态和实际模型摘要，而不是只取热内存或用当前图重查询替代历史采用材料；仍沿原工件读取权限，不给模型/只读服务新增写图权限

### Requirement: Preserve upstream full support capabilities

系统 SHALL 按固定上游设计保留历史事件补查、Attack Path、UEBA、事件检索、IOC信誉增强及OpenSearch原版索引/检索所需的服务源码、直接依赖和接口，并做确认现有功能可运行的最少验证。MUST 区分缺少运行配置/事件数据、未接通和上游尚未实现的后端；后者登记后置，不以新设计代替原码迁移。

#### Scenario: A required full support service has not been copied
- **WHEN** 现有调查查询代码依赖尚未迁入的上游服务或直接资源
- **THEN** 整体迁入固定原件并按原接口补必要接线，记录实际基本验证与未配置来源，不把原样复制或替身测试宣称为真实厂商或生产历史整链通过

### Requirement: Migration records source understanding and architecture handoff

迁移 SHALL 在范围内实际接入和验证的同时，对照固定版本官方说明记录功能入口、调用关系及证据，区分已实现、未接通、禁用、未验和声明未实现。MUST 维护服务/模块职责、关键对象/数据流、配置依赖及二开扩展点；文档声明或源码存在不得直接记成运行完成，不因对照发现非阻塞上游缺口而无边界扩大修复。

#### Scenario: A documented capability differs from its actual code path
- **WHEN** 官方说明宣称某项范围内功能，而实际源码或接入链存在缺口
- **THEN** 记录说明出处、实际源码/调用和验证边界，标明缺失类型及当前迁移影响，按必要修复或暂缓处理，并在架构交接中呈现相关扩展位置

### Requirement: Preserve complete alert and investigation functionality

迁移 SHALL 保留固定上游告警与调查所需源码、依赖、主要编排及接口；目标包含自动分诊、按策略自动关闭、自动升级调查和人工调查，不以review_only永久替代。已验必要修复 MUST 保留，未接/禁用/已验/已启用分别声明。

#### Scenario: A temporary baseline restricts a required capability
- **WHEN** 原模块和路由仍存在但被本地白名单或profile阻止
- **THEN** 登记为待恢复功能，按关联身份和调用合同最小修复，不报告源码丢失或功能已完成

### Requirement: Current report delivery requires Markdown only

当前阶段 SHALL 交付可生成、持久保存并按Case/Run读取的Markdown调查报告。MUST 将PDF及HTML额外交付登记后置，不以这些格式的生成、测试或修复作为当前迁移完成前置；已有格式源码、依赖和历史结果保留，复用有效Markdown证据，不增加报告模型调用。

#### Scenario: Markdown is available for an investigation
- **WHEN** 原调查已生成并保存与Case/Run关联的Markdown且可读取
- **THEN** 当前报告格式交付条件满足，不因PDF或HTML专项未完成而阻止本轮迁移收尾

### Requirement: Automatic investigation executes without a second manual trigger

系统 SHALL 在真实告警触发自动分诊后，按策略自动关闭或自动升级并实际执行调查。需要调查时 MUST 无需人工再次点击即可执行所需只读取证、知识/上下文查询和分析，并保存可查询的结果、证据及必要报告；仅创建Run、返回建议或人工直调triage不得替代自动主线。真实厂商动作不随调查自动获得执行权限。

#### Scenario: An alert requires investigation
- **WHEN** 自动分诊和策略判定该告警需要调查
- **THEN** 自动进入原调查编排，采用实际工具/资料并交付与告警/Run关联的结果和报告，调查阶段实际执行情况可查

#### Scenario: An alert satisfies the closure policy
- **WHEN** 自动分诊具有支持证据且满足原关闭策略
- **THEN** canonical Alert实际保存关闭状态及依据，无需人再点关闭；缺证、失败或未确认不得伪装成关闭成功

### Requirement: Restore investigation entry points without losing ownership checks

告警和调查入口 SHALL 按本次选定功能矩阵恢复实际所需入口，其他入口保留未验；Case/Run的tenant归属校验 MUST 独立于临时入口限制，解除限制不得允许跨tenant发起或读取调查。playbook/反馈及真实厂商动作不得因开放调查被连带开启。

#### Scenario: A required investigation endpoint is restored
- **WHEN** 启用原人工/自动调查或报告交付入口
- **THEN** 对应业务能力可调用且必要身份校验保留，其他tenant不能取得Case/Run或报告

### Requirement: Triage and investigation retain distinct stage facts

自动升级 SHALL 保留首次分诊结果并呈现正常调查推进，已有防重复调用保护保持。正常调查完成 MUST 不覆盖分诊usage为默认零，结果与用量可解释且首次结果仍可读取；仅特殊故障/恢复场景的自动接续能力先登记后置，不为此新增通用阶段账本或恢复框架。

#### Scenario: Investigation follows a persisted triage result
- **WHEN** 有效策略要求由已持久分诊进入调查
- **THEN** 调查实际推进，首次分类/材料/usage保持，不因共享Run总量变化导致原分诊结果被拒读

### Requirement: Fusion entry points share compatible identity and result semantics

同一告警经HTTP或Kafka处理 SHALL 保持兼容的canonical身份、首次材料及持久结果；共享去重状态不得产生无对应结果的互相阻塞。tenant MUST 在写入任何处理状态前绑定认证主体，原FusedAlert响应合同保留。

#### Scenario: The same input enters through both processing interfaces
- **WHEN** 同一来源告警先后经HTTP和Kafka进入
- **THEN** 复用可证明的首次结果且不重复评分，不因一入口缺首次快照而破坏另一入口的处理合同

### Requirement: Investigation distinguishes unavailable sources from empty evidence

实际工具/知识查询 SHALL 使用所需租户身份，成功、无匹配、不可用及失败 MUST 分开呈现。实际已留存的模型可见材料、来源标记、结果及报告可按Run回查；须保留正文、preview、裁剪及未留存差异，不保证全步骤原文完整或引用语义正确，不以缺源推断不存在关联或安全。 当前第一步验收复用实际执行和基本结果可读取的证据；已发现的内容/引用/深度质量缺陷保留失败并登记迁移后评估，不作为接通前置。

#### Scenario: A graph source is disabled or lacks credentials
- **WHEN** 工具返回error或available=false
- **THEN** 调查材料明确标缺源/失败，不转换成“0个邻居”的成功查询；不伪造来源或完整调查结论

### Requirement: Deferral does not fabricate completeness or require unrelated work

所有一体模块/依赖 SHALL 可整体原样迁入，不额外修改或测试，playbook/反馈只是当前例子；冗余设计及服务可用性相关测试和修复登记后置，不作为当前功能迁移前置。MUST 保留旧失败、unknown和真实响应审批约束，验证仅针对本次实际功能变化的完整性、正确性；未专项验证不得写成已测通过。

#### Scenario: A retained dependency is outside the current work
- **WHEN** 迁入告警或调查时包含一体模块/依赖，包括playbook或反馈
- **THEN** 保留实现及依赖，标为未专项验证，不为拆除而改主链，也不声称已启用或专项通过
