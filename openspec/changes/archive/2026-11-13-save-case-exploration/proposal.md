## Why
E66 已能查询案件关系图候选，但用户展开线索、调整画布后无法保存并继续。补齐既有 F25-03；不扩展调查或 AI 对话功能。

## What Changes
- 新增读取当前探索底图、保存探索、恢复最近保存三项独立 HTTP 操作。
- 保存服务端核对的底图与匹配对象，以及客户端的展开选择、位置和视角；固定原底图，不随新调查替换。
- 复用 artifacts 的独立 source_snapshot schema 和活动回执；不建表、不改告警合同，不生成 Run 或修改成员。

## Capabilities
### New Capabilities
- `case-exploration-persistence`: 案件探索进度保存与恢复。

## Impact
独立核心用例及外部 HTTP 端口、Swagger、交接和两端独立 API 发布；既有 66 操作保持。模型与消费服务不变。
