## Why
继续调查、人工跟进和待实现的AI对话混作并列入口，用户不清楚各自效果。沿上一批反馈设计，统一提问入口并提供可阅读全案的案件故事。
## What Changes
- 增加共用案件故事时间线与Case内AI助手对话预览，明确未接模型。
- 本轮追问、任务结果带入同一助手；根据用户最新纠正，撤每条问题固定的草案／转人工按钮。真实发送执行、人工反馈及结论采用写入目标设计，未接入。
- 人工跟进统一称人工任务；保留原路由、历史及草案规则。
## Capabilities
### New Capabilities
### Modified Capabilities
- `frontend-versioned-investigation-workspace`: 案件故事、统一助手及清晰的操作职责。
## Impact
仅4174本地前端、直接测试和当前PRD。共用所有Case数据解析，不改来源记录；不发模型、工具、后端请求，不自动创建Run或触发基础更新。
