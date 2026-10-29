## Why
用户要求把上一轮字段核对中已有的告警流程业务数据同步到V2。六条实际告警已有三个Fusion组，事件页尚未展示；Run步骤遗漏11条已有事件，工件只有目录不便回查。
## What Changes
- 用已保存21六条结果追加三个事件，展示真实成员、对象、时间、基础调查和Run入口；未有事件管理值保持空态。
- 同步92条过程及可读工件内容，保留原件身份、限制和Run隔离，不导出prompt或隐藏推理。
- 修正本批涉及的统计范围、调查覆盖判断、原始对象和事件材料入口；保留原样例、告警功能和V1。
## Capabilities
### Modified Capabilities
- frontend-versioned-investigation-workspace: saved Fusion incident and Run material display.
## Impact
仅本地V2、离线导出工具、直接测试和文档。不访问远端、不改变业务服务、不运行新调查/模型/重放/响应、不部署/提交push。另一个统一图change已有增量保留，本轮不接管其任务。
