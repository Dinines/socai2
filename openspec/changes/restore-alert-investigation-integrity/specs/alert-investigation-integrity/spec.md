## Purpose

定义完整告警和调查迁移的目标行为，使原有分诊、自动关闭、自动升级、人工调查及结果交付能够保持业务联系，必要租户和证据边界不因解除临时限制而丢失。本规格是待实施的修复目标，不能作为当前功能、模型质量或运行已通过的证明。

迁移同时承担固定官方文档与源码功能对照、当前架构与二开扩展点梳理，随实际批次记录，不扩为全平台重构或无限上游审计。

当前阶段按2026-10-21最新指示仅先接通正式告警输入到实际自动调查、已配置工具/知识调用及基本结果/报告/关联记录读取。已有B4 case02证据可复用；partial、缺源、模型/报告及计量质量问题保留，迁移后评估，不要求全部入口/分支或这些后续完整目标先完成。已修代码不回退，不追加复杂可用/冗余测试、重复组合/全量校验/冻结、多轮审计或新控制框架；既有保护保持。

## ADDED Requirements

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

告警和调查入口 SHALL 按功能矩阵恢复；Case/Run的tenant归属校验 MUST 独立于临时入口限制，解除限制不得允许跨tenant发起或读取调查。playbook/反馈及真实厂商动作不得因开放调查被连带开启。

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

实际工具/知识查询 SHALL 使用所需租户身份，成功、无匹配、不可用及失败 MUST 分开呈现。模型可见材料、来源引用、结论及报告可回查，不以缺源推断不存在关联或安全。 当前第一步验收复用实际执行和基本结果可读取的证据；已发现的内容/引用/深度质量缺陷保留失败并登记迁移后评估，不作为接通前置。

#### Scenario: A graph source is disabled or lacks credentials
- **WHEN** 工具返回error或available=false
- **THEN** 调查材料明确标缺源/失败，不转换成“0个邻居”的成功查询；不伪造来源或完整调查结论

### Requirement: Deferral does not fabricate completeness or require unrelated work

所有一体模块/依赖 SHALL 可整体原样迁入，不额外修改或测试，playbook/反馈只是当前例子；冗余设计及服务可用性相关测试和修复登记后置，不作为当前功能迁移前置。MUST 保留旧失败、unknown和真实响应审批约束，验证仅针对本次实际功能变化的完整性、正确性；未专项验证不得写成已测通过。

#### Scenario: A retained dependency is outside the current work
- **WHEN** 迁入告警或调查时包含一体模块/依赖，包括playbook或反馈
- **THEN** 保留实现及依赖，标为未专项验证，不为拆除而改主链，也不声称已启用或专项通过
