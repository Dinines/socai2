# Case调查报告 a280c884-0abd-458d-bb66-13c06fe9ca5b

告警A1和A2针对主机investigation-ch-20261023-01-host在09:59:00和10:01:00分别报告网络活动，对应事件ID c9ee6c8a-d44d-5ffe-a456-594b5555a87c和951c5352-2df4-53d8-a431-b2763fea5e6e。网络细节E2显示这两次连接均为TCP/443至::ffff:198.51.100.70，来源IP均为::ffff:192.0.2.70。进程活动E1在相同时间窗口返回空结果，提示该窗口可能缺少进程活动记录或工具未覆盖相关进程。

## 发现与依据
- 告警A1与A2的记录在E2中得到部分印证：两次网络连接的event_id与告警中的source_event_ids完全匹配，连接目标均为198.51.100.x，来源IP均为192.0.2.70。时间间隔2分钟。（依据：[A1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/A1), [A2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/A2), [E2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E2)）
- 时间窗口内的进程活动查询E1返回空结果，与告警主张“待核网络活动”形成缺口。空记录无法确认是否存在未上报或未被该工具的进程捕获的活动。（依据：[A1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/A1), [A2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/A2), [E1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E1)）

## 成员覆盖与判断
选定2条，读取2条；给出判断0条，尚未明确2条，未逐项分析0条，材料不可读0条。
给出判断不等于证实攻击或已解决；背景成员不等于已证明安全。
- 3fcd245d-0496-54f3-875e-f9a7eb90ae2d [unresolved/supporting]：A1在E2中得到部分网络细节印证，进程和活动上下文仍空缺，不能直接断定为安全或告警错误。（依据：[A1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/A1), [E2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E2), [E1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E1)）
- 5272ae80-b48e-5ef3-8cdd-805885a558a0 [unresolved/supporting]：A2在E2中得到部分网络细节印证，进程和活动上下文仍空缺，不能直接断定为安全或告警错误。（依据：[A2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/A2), [E2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E2), [E1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E1)）

## 跨告警关联依据
共同实体或时间接近不等于因果关系。
- 3fcd245d-0496-54f3-875e-f9a7eb90ae2d, 5272ae80-b48e-5ef3-8cdd-805885a558a0 [shared_context/supported]：两条告警均指向同一主机、同一来源IP、同一目标IP段，且时间间隔仅2分钟，E2显示的两个网络连接与告警source_event_ids匹配。（依据：[A1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/A1), [A2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/A2), [E2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E2)）

## 来源时间线
按来源时间排列；候选成员仅表示查询主机/来源范围的匹配，不证明因果。
- 2026-10-23T09:59:00+00:00 [告警时间]：合成测试待核网络活动 c9ee6c8a-d44d-5ffe-a456-594b5555a87c（依据：[A1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/A1)；来源记录：见原告警；候选成员：3fcd245d-0496-54f3-875e-f9a7eb90ae2d）
- 2026-10-23T09:59:00+00:00 [来源事件时间]：未知进程：::ffff:192.0.2.70 → ::ffff:198.51.100.70:443（依据：[E2/rows/0](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E2/rows/0)；来源记录：c9ee6c8a-d44d-5ffe-a456-594b5555a87c；候选成员：3fcd245d-0496-54f3-875e-f9a7eb90ae2d, 5272ae80-b48e-5ef3-8cdd-805885a558a0）
- 2026-10-23T10:01:00+00:00 [告警时间]：合成测试待核网络活动 951c5352-2df4-53d8-a431-b2763fea5e6e（依据：[A2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/A2)；来源记录：见原告警；候选成员：5272ae80-b48e-5ef3-8cdd-805885a558a0）
- 2026-10-23T10:01:00+00:00 [来源事件时间]：未知进程：::ffff:192.0.2.70 → ::ffff:198.51.100.70:443（依据：[E2/rows/1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E2/rows/1)；来源记录：951c5352-2df4-53d8-a431-b2763fea5e6e；候选成员：3fcd245d-0496-54f3-875e-f9a7eb90ae2d, 5272ae80-b48e-5ef3-8cdd-805885a558a0）
- 2026-10-23T10:02:00+00:00 [来源事件时间]：未知进程：::ffff:192.0.2.70 → ::ffff:198.51.100.71:443（依据：[E2/rows/2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E2/rows/2)；来源记录：a2a124b2-69aa-50ab-a88f-0e1486958f72；候选成员：3fcd245d-0496-54f3-875e-f9a7eb90ae2d, 5272ae80-b48e-5ef3-8cdd-805885a558a0）

## 未决问题
- 进程活动监听（E1）为何未返回任何记录？是否存在记录覆盖或采集工具盲区？（成员：3fcd245d-0496-54f3-875e-f9a7eb90ae2d, 5272ae80-b48e-5ef3-8cdd-805885a558a0；依据：[E1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E1)） 缺少：更长时间窗口或更细粒度的进程日志，以及执行进程的身份（账号、哈希、命令行）。；建议：扩大时间窗口、确认采集探针状态，或手动归档该主机在告警时间点的全局进程快照。
- 告警所涉目标IP是否为可信资产，还是可疑定向通信？（成员：3fcd245d-0496-54f3-875e-f9a7eb90ae2d, 5272ae80-b48e-5ef3-8cdd-805885a558a0；依据：[E2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E2)） 缺少：目标IP的注册信息、归属、在我司网络内是否存在授权映射。；建议：对198.51.100.x段进行资产登记和信誉扫描，并检查是否有安全组或WAN/DMZ段预期通信规则。
- 这两项网络活动是否属于正常业务（例如代理、补丁分发、定时任务/备份、业务扫描等）？（成员：3fcd245d-0496-54f3-875e-f9a7eb90ae2d, 5272ae80-b48e-5ef3-8cdd-805885a558a0；依据：无） 缺少：业务流程、主机角色、网络策略文档、相关系统日志。；建议：结合该主机的业务用途、网络策略与告警源的触发逻辑补充判断依据。

## 反证

## 未解问题与限制
- 进程活动E1为空，无法确认发起连接的工具或进程名，也无法判断是否存在父进程链。
- 告警文本中未明确网络活动的业务上下文（如：是否为正常代理、扫描或电信设备互联）。
- 目标IP::ffff:198.51.100.70和::ffff:198.51.100.71身份未知，无法直接判定是否为可信站点。
- 告警指示词中未包含脚本正文、请求/响应细节等进一步佐证。
- 成员3fcd245d-0496-54f3-875e-f9a7eb90ae2d：A1在E2中得到部分网络细节印证，进程和活动上下文仍空缺，不能直接断定为安全或告警错误。
- 成员5272ae80-b48e-5ef3-8cdd-805885a558a0：A2在E2中得到部分网络细节印证，进程和活动上下文仍空缺，不能直接断定为安全或告警错误。
- 未决问题：进程活动监听（E1）为何未返回任何记录？是否存在记录覆盖或采集工具盲区？
- 未决问题：告警所涉目标IP是否为可信资产，还是可疑定向通信？
- 未决问题：这两项网络活动是否属于正常业务（例如代理、补丁分发、定时任务/备份、业务扫描等）？

## 建议
- 后续增加进程树的采集（如事件范围扩大、聚合进程或补充日志），以确认发起连接的过程。
- 对目标IP进行资产与信誉核查，确认是否为可信业务伙伴或可疑命令与控制。
- 若该主机为代理或转发节点，需额外确认网络行为是否属于预期业务策略（如HTTP代理流量）。
- 考虑在相同主机上针对告警时间点的历史窗口拉取更细粒度日志（如WinEvent、代理日志、NAT网关）进行交叉验证。

## 本次范围
Case：a280c884-0abd-458d-bb66-13c06fe9ca5b
时间：2026-10-23T09:58:00+00:00 至 2026-10-23T10:03:00+00:00（不含结束时刻）
选定成员：3fcd245d-0496-54f3-875e-f9a7eb90ae2d, 5272ae80-b48e-5ef3-8cdd-805885a558a0
停止原因：analysis_complete

## 证据索引
- [A1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/A1)：告警3fcd245d-0496-54f3-875e-f9a7eb90ae2d，来源事件=c9ee6c8a-d44d-5ffe-a456-594b5555a87c
- [A2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/A2)：告警5272ae80-b48e-5ef3-8cdd-805885a558a0，来源事件=951c5352-2df4-53d8-a431-b2763fea5e6e
- [E1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E1)：process_activity，来源可用=True，记录ID=无
- [E2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E2)：network_connections，来源可用=True，记录ID=c9ee6c8a-d44d-5ffe-a456-594b5555a87c, 951c5352-2df4-53d8-a431-b2763fea5e6e, a2a124b2-69aa-50ab-a88f-0e1486958f72