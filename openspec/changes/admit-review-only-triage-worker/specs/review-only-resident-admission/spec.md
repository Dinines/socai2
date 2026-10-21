## Purpose

定义所选A/B测试租户和两条全新告警在review_only_v1下有限常驻消费的目标合同，使未审核模型建议、有效人工复核决定、持久结果与恢复证据能够逐项核查。本规格尚未实施，不代表自治质量、永久常驻或后续调查响应已经通过。

## ADDED Requirements

### Requirement: Admission requires a bounded frozen window

有限窗口 SHALL 在发送前绑定两条全新输入、租户身份、当前运行来源、所有具体调用/操作上限、故障接缝、watchdog及最终OFF恢复定义；未完成绑定时 MUST 保持worker OFF。实际SDK发送最多A一次+B一次、合计最多两次，预留单位最多40000；MUST 在真实DB时钟下重核剩余额度，禁止增额、退款、删除/过期unknown或自动重分配未用旧额度，余量不足即停止；重投不得增加模型调用。

#### Scenario: Execution bindings are incomplete
- **WHEN** 输入hash、operator、具体HTTP/SQL/发布/物理读取上限或停止恢复配置仍未冻结
- **THEN** 不启动窗口、不发送业务输入、不把change结构校验通过视为运行准入

#### Scenario: The next operation would exceed its frozen limit
- **WHEN** 下一操作将超出其所属类别的冻结上限
- **THEN** 禁止该超额操作及新的模型发送；已允许的调用仅在其他冻结额度内完成必要持久确认、预算结算与停止收尾，不因某类别恰好达到上限而丢弃已发调用的结果

#### Scenario: An unexpected tenant or offset enters the window
- **WHEN** 出现未纳入的tenant或无关新offset
- **THEN** 立即停止新输入处理和后续reader/模型调用，不为该输入新增业务写；仅对先前已允许的调用在冻结额度内完成必要持久或unknown/停止收尾，保存现场而不扩大本批范围

### Requirement: Consumption has an explicit start and service lifecycle

系统 SHALL 使用新operational group在未消费状态将main fused每partition起点显式设为冻结end，并由服务main真实startup启动受护worker。旧main、历史组及原积压 MUST 保持，不用latest代替起点或通过重放旧输入验收。

#### Scenario: The resident worker starts
- **WHEN** 冻结起点和候选配置核验完成后启动有限窗口
- **THEN** 实际group、subscription、readiness、profile、来源及挂载policy一致，并只处理冻结范围的两条新输入

#### Scenario: The bounded window ends
- **WHEN** 有限验收完成、watchdog到期或发生不可恢复失败
- **THEN** worker恢复OFF且无消费任务或inflight遗留，停止事实可查，旧组offset及旧unknown保持

### Requirement: Model advice cannot become an autonomous decision

交付 SHALL 分列原模型建议及其hash/usage/身份与有效决定；成功回复标为unreviewed/advisory，无成功回复则无模型建议。有效决定 MUST 为needs_review、confidence=null、review_required=true；兼容数值0必须标为sentinel。canonical Alert全部AI字段、状态、disposition及recommendations MUST 保持。

#### Scenario: A confident raw verdict is returned
- **WHEN** 模型返回FP或其他分类及高置信度、理由
- **THEN** 原建议完整保留但不成为有效分类或有效置信度，不触发关闭、QA、graph、playbook、审批提案或任何经验/来源/结果/SIEM写回

#### Scenario: A request uses an unprotected or incompatible path
- **WHEN** 请求来自未受护direct/replay路径、profile漂移、旧无标记快照或已开始/unknown结果
- **THEN** 保持typed hold，不绕至legacy、不补造新profile事实或重新调用模型

### Requirement: Tenant sources and usage remain attributable

本批 SHALL 用A/B各自实际配置的reader认证读取来源，区分成功、无匹配、缺源和失败；输入、实际模型可见材料、Run、来源工件、usage及成本来源 MUST 可关联，跨tenant材料不得采用。预留单位 MUST 与实际usage分列，未知费用不得写零。

#### Scenario: A source cannot be authenticated or queried
- **WHEN** reader身份、权限或来源读取失败
- **THEN** 保留明确失败/缺源状态，不把它作为合法空集或当时授权事实，不跨租户回退

#### Scenario: A and B finish their separate inputs
- **WHEN** 两条新告警经真实HTTP/Fusion/PG/Kafka进入本profile
- **THEN** 各自材料、原建议、有效决定、Run/API关系及usage可回查，重启回查不串tenant或改变首次事实

### Requirement: Durable first results govern acknowledgement and recovery

消费确认 SHALL 等待首次结果及所需工件持久确认；保存或确认失败不得越过失败offset。warm及fresh进程恢复 MUST 复用同Run首次结果、来源、profile及usage，最多一次停止到fresh进程恢复周期，不重发不明确的模型请求。

#### Scenario: Saving or confirming the result fails
- **WHEN** 本批定向故障接缝在模型结果后阻止持久确认或确认完成
- **THEN** offset不越过失败项，保留首次结果；明确可恢复时仅恢复保存/确认，额外模型调用为零

#### Scenario: A fresh process receives an already completed input
- **WHEN** 同批已完成输入在冻结的恢复周期重投
- **THEN** 复用相同Run及完整首次快照，结果和来源不变，无额外SDK发送；未知调用保持unknown而不自动重发

### Requirement: Acceptance preserves prior evidence and requires independent audit

本批 SHALL 保留旧业务材料、旧12预约/240000预留单位/3unknown完整原行、十reader、历史组offset和其他服务，不新增tenant、reader或closure policy；每tenant操作key最多一枚、权限最小且撤销后须真实认证拒绝。只有逐项直接证据和未参与实现者结束审计通过，才能声明所选窗口准入；MUST 保留原自治质量失败与C04—C11未完成事实。

#### Scenario: The change is closed successfully
- **WHEN** 本批直接验收、最终OFF、撤key及结束独审均完成
- **THEN** 更新回执/来源/PROGRESS并归档本change，只声明所选A/B、两输入及有限窗口通过，不声称永久常驻、自治质量或整体迁移完成

#### Scenario: The window stops with uncertain usage
- **WHEN** SDK是否已发送、已回复或保存结果不明确
- **THEN** 保留调用意图、预算、offset和原材料，停止并记录失败/unknown，不为补齐验收而重调或退款
