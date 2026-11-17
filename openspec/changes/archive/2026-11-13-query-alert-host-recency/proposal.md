## Why
告警详情概况的相关告警区域需要展示同主机最近7条（F08-01，ui-discussion-principles.md第4节）。已完成的E70要求同主机且同战术或IP/哈希，不能替代这个直接查看主机近期活动的功能。

## What Changes
- 新增E71 `GET /alerts/{alert_id}/same-host-alerts`，查询真实库中同主机最新发生的其他告警。
- 返回原告警事实和双方主机对象来源；默认7条、去重且顺序明确，不写反馈、不调用模型。
- 更新HTTP交接、Swagger和功能状态；保留对外HTTP与内部调查边界及原70操作。

## Capabilities
### New Capabilities
- `alert-host-recency`: 告警详情的同主机近期告警读取。

## Impact
新增独立只读用例、HTTP端口和配置文件；无数据库迁移或旧告警合同变化。不改页面、E70规则或内部调查流程。按用户指令暂不提交或推送Git。
