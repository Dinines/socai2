## Why

告警主表列调整完成后，用户追加要求删除选中告警后“管理告警”中的分类。

## What Changes

- 主告警列表的所选告警管理只提供状态、分配给、评论。
- 不修改原分类数据，其他工作区及详情管理保留当前能力。

## Capabilities

### Modified Capabilities
- `security-reference-ui-prototype`: 主列表所选告警管理表单范围。

## Impact

仅前端 Mock 的 app.js 与必要说明。本规格为待验证目标；无后端、模型、部署或 Git 提交。
