## ADDED Requirements

### Requirement: E54 exports selected alerts

告警 CSV 导出 E54 SHALL 接受可省略的重复 `ids` 查询参数，每项为告警 `facts.id` 的 UUID。提供时，导出范围为当前租户内这些 ID 与既有筛选条件的交集，使用原排序、列及文件上限。省略该参数时，导出当前租户完整的筛选结果。

#### Scenario: Export checked alerts
- **WHEN** 请求携带多个 `ids` 以及已有筛选或排序
- **THEN** CSV 按既有排序导出符合条件的同租户选中告警，重复 ID 只生成一行，未知或跨租户 ID 不生成数据行

#### Scenario: No selected alert matches
- **WHEN** 提供的有效 UUID 在当前租户与筛选范围内均不匹配
- **THEN** 返回含列头及零行的成功 CSV

#### Scenario: Validate selected alert IDs
- **WHEN** E54 的 `ids` 包含无效 UUID 或空项，或事件及 Case 导出携带 `ids`
- **THEN** 返回 422
