# 告警列表第 2 步：负责人身份与读取支撑

2026-11-24。本步支撑 [告警列表读取](alert-list-detail-closeout-20261124.md#第-2-步设计--告警列表读取)，仅复用已获准的两名 Q04 平台人员、现有正常登录回执和已保存负责人管理告警。服务端不新建人员或投影，不改角色或密码，不更新负责人，不部署或推送。列表页面由前端会话实施。

## 本步安排与直接验收

1. 从原平台人员清单、创建脚本和登录回执核身份来源与凭据留存。正式人员来源为 `.local/validation/spirithub-alert-owners-20261123-01/platform-users.json`；隔离候选的 `directory.json` 不作为正式人员范围。现有候选登录主体取 `.local/validation/spirithub-alert-a-run-20261124-01/platform-test-principal.json`，桥接身份不自动当成本人负责人身份。
2. 沿已有运行 profile 核实际调查数据库与发行号，按上述固定人员 UUID 分别 GET `/people?user_id=…`，再查询当前登录主体。直接核平台 UUID、Q04 `items[].id` 的同一关系，区分目录失败、无映射和已映射。
3. 对两名负责人分别读取至多五条告警，按旧管理来源核对；未命中则保留结果。从本次已读到的负责人告警明确冻结一组新定位，再 GET 同 ID 详情及 Q04，核 `facts.id/owner_id`、`owner_name`、`assignment_state` 与既有列表包络。新定位不当作旧管理批次恢复，不遍历全库或改数据。
4. 交付已证实的身份关系、现有凭据或选择器文件路径和未验边界。仅有启用账号或调查侧投影不证明浏览器登录、权限或“分配给我”正例通过。当前会话无映射时不能以空列表代替缺映射。

业务值、凭据和完整回执留在 `.local/validation/alert-owner-identity-support-20261124-01/`；会话及仓库仅保存结构、检查结果和路径。检查前执行现有 change 的 OpenSpec 严格校验。必要调用全部只读；未完成或失败保留原结果，不覆盖旧批次。

## 读取合同

Q04 的 `GET /api/v1/socai2/people` 接收 `user_id`（UUID）、`q`（最长 200）、`offset`（默认 0）、`limit`（默认 50，上限 200），响应为 `items/total/offset/limit/next_offset/observed_at`。`items[]` 为 `id/username/display_name`；正式两名人员沿平台 UUID 投影，所选 `id` 直接用于 `owner_id`。本人查询应使用实际平台会话的 `user.id`，不能使用桥接服务操作者代替。

告警列表沿原合同：`items[].facts.id/owner_id/assignment_state` 与顶层行 `owner_name`；`total` 和 `overall_stats` 保持总体统计，`filtered_total` 是当前筛选分母，续页使用原条件及 `next_cursor`。本步不更改字段、统计或筛选合同。

## 账号相关范围已按最新指令暂缓

组织者曾追加单账号恢复方案的只读核查；已有读取回执保存在本批受控目录，未执行账号或会话变更。随后用户明确“就账号的这个不用管”。按这一最新指令立即停止登录恢复、密码重置方案及进一步现场路由核查，不再提出账号动作审批，也不修改密码、角色、映射或人员 profile。

**已映射人员的实际登录正例标为用户明确暂缓，未通过，不阻塞后续告警步骤。** 不把人员启用、Q04 命中、负责人告警可读或现有管理员能力核查当作本人浏览器正例。已完成的只读回执保留原样，不继续扩展账号问题。

## 负责人读取结果

正式调查环境、两名平台 UUID 与 Q04 `items[].id`、名称快照均通过。已有正常登录回执对应的主体在当前正式 Q04 无同 ID 项；这是本人映射缺失，不是“我的告警为空”。

两名负责人各一页的有界列表读取通过，行中负责人均符合筛选，`total/overall_stats/filtered_total/next_cursor` 包络保持。该范围未命中旧管理来源；`attempt-01/` 保留这一失败，不能据此认定旧记录不存在。从本次已读列表明确冻结的新负责人告警，在 `attempt-02/` 通过同 ID 详情、行版本、负责人、名称和分配状态核对，并再次确认该负责人是 Q04 的同一平台身份。

受控定位为 `.local/validation/alert-owner-identity-support-20261124-01/page-selector-private.json`，包含 `selected_person`、`owner_alert`、`people_query`、`current_login` 及来源/读回文件路径。可用现有正常登录账号测试显式 `owner_id` 筛选；本人正例需以该负责人自己的真实平台登录主体验证。

原创建脚本使用临时随机密码，人员文件只保存 `id/username/display_name`；现有证据未提供这两名人员的可复用密码或会话。调查侧非登录投影不等于平台不能登录，但目前不能声称已有“映射人员实际登录”正例。该缺项现按上述最新指令暂缓。本步没有服务端合同或业务代码修改。

工程检查见 [本步回执](../../../docs/operations/evidence/alert-owner-identity-support-20261124-01/README.md)。本次只读支撑到此结束；告警列表实际页面验收由前端和组织者分别收口，后续详情读取按下一次派工执行。
