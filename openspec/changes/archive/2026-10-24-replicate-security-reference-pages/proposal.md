## Why

用户要求另开分支，以官方图片和正文复刻告警、事件、Case三组页面，允许mock数据；后续明确先整理功能，事件页指定Defender investigate-incidents，外围导航仅留名称。

## What Changes

- 保存docs/design/security-pages-replica.md，列核心功能、交互及原图索引。
- 明确图片区分、正文补充及mock建议，不按当前后端能力裁剪。
- 继续实现独立本地前端，文档样例与mock数据共用关系；外围导航仅留名称。
- 事件包含第600页参考的多事件队列及详情；左侧告警、事件分开，顶栏改为AiSOC和本地盾牌图标。

## Capabilities

### New Capabilities

- `security-reference-ui-prototype`：三个主入口及mock浏览、管理、关系图和调查材料交互，未接业务服务。

### Modified Capabilities

无。既有服务、20展示和调查/数据评估规格保持。

## Impact

新增prototypes/security-pages的静态HTML/CSS/JavaScript、示例数据及本地启动入口，更新清单、change及PROGRESS。用户允许文档数据及自拟mock账号/数据；不改变服务端、真实数据/模型/响应/部署，不Git提交/推送。
