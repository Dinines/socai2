## Why
用户要求告警主表仅严重程度和告警时间排序，调整列顺序并避免排序引起列宽跳动。
## What Changes
严重程度第二列、告警时间第三列（不计勾选列）；其余表头为静态文本。排序标识区分未排序/升序/降序；固定各列宽度并支持水平滚动。
## Capabilities
### Modified Capabilities
- `security-reference-ui-prototype`: 主告警列表排序与稳定布局。
## Impact
仅前端原型主告警表及文档，无后端或部署。
