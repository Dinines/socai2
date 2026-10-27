## Why
用户要求从20已有测试告警选几条在21重放，通过21真实表字段核对新版告警UI，并将实际处理结果展示在告警页面；事件和Case页面暂不对接。此前仅静态讨论不能代替真实读取。
## What Changes
选3条已有合成告警，经21现有source-v1 Kafka入口逐条重放，保来源映射/发送intent与ACK，观察现有分诊/调查，查询真实alerts/Run账本和直接关联表。保存数据库字段→实际值映射，将脱敏快照用于告警页面展示；无值不造，不从原型补Run或Case。
## Capabilities
### Modified Capabilities
- `security-reference-ui-prototype`: 真实21告警快照展示。
## Impact
新测试输入及其自然处理结果写入21已授权入口；允许原有自动模型流程但不提高预算/重试unknown，不改生产服务或部署。只前端告警展示与本批工具/回执，Case/事件页面不对接。
