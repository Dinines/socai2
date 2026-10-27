## Why

用户逐项适配 AiSOC 告警主列表，要求只留一个状态、移除分类、将两列活动时间收敛为告警时间。本次只调整该表，承接已归档原型，其他工作区和后端不变。

## What Changes

- 告警主表保留处理状态，移除调查状态与分类列；类别保留。
- 告警时间使用发生时间语义，列设置、排序、日期筛选和导出一致。
- 保留原筛选行及工具栏；详情、统计、事件与 Case 的内嵌表不在本次范围。

## Capabilities

### Modified Capabilities
- `security-reference-ui-prototype`: 告警主列表的展示字段适配；管理结果在展示该字段的位置保持一致。

## Impact

仅 prototypes/security-pages/app.js 及直接说明/验收记录。数据仍为 Mock，无服务端、生产、模型、部署或 Git 提交。以下规格是本批目标，验收后同步。
