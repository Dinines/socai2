## Why
事件列表的攻击中断卡片缺实际记录，标签与告警页的资产标签含义不一致，箭头易被误认为展开告警，相关主机和缺失事件状态也不够清晰。用户要求逐项核对并选择改用有关联调查的事件指标。

## What Changes
- 攻击中断卡片改为有关联调查的事件，排除仅分诊未升级的Run。
- 事件标签采用成员关联资产标签，列出相关主机；保留事件管理标记原值。
- 换侧栏预览图标，明确缺失的是事件处理状态；侧栏单列已有告警评分及其判定，不代填事件优先级。
- 产品参考与七项数据说明更新到既有设计文档，不新增评分算法或后台功能。

## Capabilities
### Modified Capabilities
- frontend-versioned-investigation-workspace: clarify incident queue context and metric semantics.

## Impact
仅4174本地前端、直接测试、对应文档。保全部样例和历史；无后端、生产、模型、部署或Git提交推送。
