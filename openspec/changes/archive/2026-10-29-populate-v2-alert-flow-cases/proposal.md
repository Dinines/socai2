## Why
用户确认无自动创建Case也已有可供案件展示的材料，要求补齐。上一批已展示事件/单Run，Case工作区尚未整理本批六告警及其保存调查。
## What Changes
- 依据同租户三个Fusion组生成明确的本地Case集合，引用六条告警及六个既有Run，不改源case_id或调查输入。
- 补案件级调查概览、当前成员关系、可读工件/报告入口和来源活动；管理缺值与无附件/任务保持正常空态。
- 本地关联与历史Run引用分开；已有样例、浏览器编辑和V1保持。
## Capabilities
### Modified Capabilities
- frontend-versioned-investigation-workspace: local Case collections of saved alert-flow materials.
## Impact
仅V2/离线投影/直接验证/文档。无生产查询、模型、重放、后台Case创建/写入、部署、提交push。另一统一图change独立保持。
