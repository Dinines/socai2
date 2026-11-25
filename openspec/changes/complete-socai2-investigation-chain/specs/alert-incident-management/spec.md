## ADDED Requirements

### Requirement: 告警活动按实际时间倒序分页
系统 SHALL 对告警 `records/activities` 先按 `occurred_at` 倒序、同时间按 `id` 倒序确定次序，再应用已有 `offset/limit`；首屏 SHALL 包含该告警可见的最新活动。字段、目标关联、总数和 `next_offset` 合同 SHALL 保持，其他分区不受该排序规则影响。

#### Scenario: 保存后小页长仍能读取最新活动
- **GIVEN** 同一告警有超过一页的已存活动，UUID 次序与实际发生时间不同
- **WHEN** 管理或人工反馈保存后以 `offset=0` 和小页长读取告警活动
- **THEN** 首项为实际时间最新活动，同时间以 ID 倒序稳定排序，后续分页保持该次序且保留对应 matching_targets

### Requirement: 告警人工操作以最后成功保存的明确字段为准
告警单条及批量管理、人工反馈 SHALL 在同一事务中锁定最新主体，再仅应用本次明确提交的修改及既有状态联动；MUST NOT 因请求中旧 `expected_row_version` 拒绝告警保存。该字段 SHALL 保留兼容和基本格式校验，实际行版本仍按既有规则递增。未提交字段、原 AI 分诊和历史评估 SHALL 保持；事件及 Case 的并发校验不变。既有操作键和回执格式保持，不新增重试或恢复流程。

#### Scenario: 旧页面提交后一次明确修改
- **WHEN** 两次不同操作键的告警保存先后成功，后一次携带旧版本并仅提交部分字段
- **THEN** 后一次明确提交的值保存到最新行，未提交字段保留前次最新值，不返回旧版本冲突，实际行版本反映保存结果

#### Scenario: 勾选告警批量人工判定
- **WHEN** 调用方为明确选择的告警提交同一人工判定和理由
- **THEN** 每个选中告警各新增一条反馈并沿原规则关闭或重开；未选择主体保持，原 AI 和历史反馈保留，批量回执按 ID 对应实际结果

### Requirement: 告警标签仅允许单条修改
单条告警管理 SHALL 保留标签整体替换、空数组清空和省略保持的合同。告警 `management-batch` MUST 拒绝任何显式 tags 字段，不静默忽略，不部分写入；事件标签合同不变。

#### Scenario: 批量管理带标签
- **WHEN** 告警批量管理 changes 显式带 tags，包括空数组或 null
- **THEN** 返回参数错误并保持全部选中记录和活动不变；单条对应操作仍沿其原字段合同处理

### Requirement: Q04 reads scoped Spirit Hub owner projections

已登记的 Spirit Hub 启用人员通过稳定平台 UUID 对应当前正式调查租户。调查侧 SHALL 使用不可登录的业务身份并保持现有 `owner_id` 保存合同。Q04 SHALL 只返回当前租户、显式配置范围内的该类人员，沿用 `items[].id`、`username` 和 `display_name`。

#### Scenario: Search and page available people
- **WHEN** 调用方按 `q`、`offset` 和 `limit` 读取 Q04
- **THEN** 按姓名或账号匹配已映射人员，稳定排序，并返回 `total` 和 `next_offset`

#### Scenario: Look up a person by stable ID
- **WHEN** Q04 请求指定 `user_id`
- **THEN** 只返回该租户、范围内已核验的业务人员，其他身份返回空页

#### Scenario: Assign and reassign the same alert
- **WHEN** 操作者先后选择两名已映射人员，以当时的版本和各自操作键提交现有管理 PATCH
- **THEN** 已有管理接口按原规则保存 `owner_id`、行版本和活动，列表和同 ID 详情读回实际末次选择
