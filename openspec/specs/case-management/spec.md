# case-management Specification

## Purpose
为现有Case提供人工基本管理、结案和重开，保留调查/人工任务历史，并通过明确版本与幂等语义支持HTTP对接。

## Requirements

### Requirement: Manage existing Case fields
调查服务 SHALL 提供现有Case名称、说明、负责人、严重度、标签及未结案处理状态的HTTP局部更新，省略字段保持不变，清空仅对明确可空字段开放。更新 SHALL 使用行版本和幂等操作键，记录人工来源和活动，保持告警/事件字段及成员/结果不变。

#### Scenario: Save and read management values
- **WHEN** 同租户用户提交有效字段及当前行版本
- **THEN** 保存实际变化并返回新Case字段和行版本，GET详情/管理/列表读取一致；同键同意图重放不重复修改，过期版本或跨租户负责人拒绝

### Requirement: Close with current execution and task checks
结案 SHALL 在同一Case锁下检查当前运行和人工任务。有running或unknown调查时 SHALL 拒绝；未完人工任务 SHALL 明确展示数量且需要用户确认及非空理由。结案 SHALL 保留任务和待启动Run，记录解决人/时间/说明。

#### Scenario: Close after an explicit outstanding-task acknowledgement
- **WHEN** 没有活跃或未知Run且用户确认未完任务并提供理由
- **THEN** Case变为resolved，人工任务/历史/当前判断及待启动Run不变，关闭前后值可经活动读取

#### Scenario: Reject closure while execution is active or uncertain
- **WHEN** Case存在running或unknown Run，或未确认当前未完任务
- **THEN** 返回明确409且无业务修改，调用方可GET管理视图读取阻塞原因或任务数量

### Requirement: Reopen explicitly without execution
重开 SHALL 仅由已认证用户显式发起，将resolved Case恢复in_progress并记录重开时间，保留历史结案活动；不得自动准备或启动调查，不得改写人工任务或调查判断。

#### Scenario: Reopen and retain investigation history
- **WHEN** 用户使用当前行版本显式重开已解决Case
- **THEN** 返回in_progress及新行版本，当前结案字段清空，历史结案说明仍可查，Run数量及状态保持
