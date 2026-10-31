## ADDED Requirements

### Requirement: Process evidence preserves event class and activity meaning
Case 的 process_activity SHALL 只查询固定租户、主机、半开窗口内 class_uid=1007 且有进程名的记录，并保存 class_uid、activity_id、action、outcome。模型 SHALL 沿现有输入合同使用语义类别event_kind和原action/outcome，明确省略的原始类别/活动编号仍在证据中。系统 MUST 将其描述为进程活动，缺失动作/结果不表示执行成功，不绕过LLM原始OCSF限制。

#### Scenario: Mixed event classes share a process name
- **WHEN** 同范围存在进程类记录和带相同进程名的网络/其他类别记录
- **THEN** process_activity 只返回进程类，网络工具仍按其原类别查询，原始编号留在证据，模型可见语义类别、来源动作/结果及编号省略说明

#### Scenario: The source does not state a successful start
- **WHEN** 进程类行的动作/结果未知、为空或表示其他活动
- **THEN** 系统保留来源值/未知语义，不生成“启动成功”事实，也不推断父子进程链

### Requirement: Process query reuse requires the current query contract
新的进程查询证据 SHALL 标记 query_contract=case.process_activity.v2，复用 MUST 同时满足现有范围/材料/参数条件和精确查询合同版本；旧证据读取不得被改写。

#### Scenario: A prior result has no current query version
- **WHEN** 后续 Run 找到缺少版本或版本不同的旧 process_activity 结果
- **THEN** 不将它作为新查询复用，按本次已准入范围执行查询；旧结果、报告和原 operation_key 重读保持

#### Scenario: A compatible query is reused
- **WHEN** 旧结果具有当前查询版本且满足全部既有复用条件
- **THEN** 沿原复用分支记录新 E 引用及 reused_from，不为版本控制无故重复查询
