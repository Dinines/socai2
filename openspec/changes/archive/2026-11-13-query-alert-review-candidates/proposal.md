## Why
告警详情的人工反馈区域需要对照相似历史告警。F03-05 已有人工反馈接口，但缺全库候选查询；E30 一般共同对象关系和 E66 案件探索不能替代此规则。

## What Changes
- 增加 E70 `GET /alerts/{alert_id}/review-candidates`，按同主机且同战术、同 IP 或同明确算法哈希查询近期候选。
- 返回逐对对象及战术标签原件、时间、现有判定/处理状态、所属事件/Case 和稳定分页；人工选定后沿用现有反馈接口。
- 独立只读用例和外部 HTTP 端口，不修改旧告警字段、一般关联查询或调查流程。

## Capabilities
### New Capabilities
- `alert-review-candidates`: 告警人工复核的相似历史候选读取。

## Impact
新增一个对外 HTTP 操作、文件配置、Swagger 和交接；无迁移、模型调用或业务写入。F08-01 单纯同主机最近7条不由本项冒称完成。
