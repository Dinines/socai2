## Context

功能及来源见docs/design/security-pages-replica.md。分支codex/security-pages-replica，其他未提交内容保持。事件页用用户新指定的Defender Legacy参考，Case页保留Preview参考。

## Goals / Non-Goals

已完成功能整理，当前实现三组本地mock原型；全局侧边栏及外围模块仅留名称，不按当前后端能力裁剪。不改业务服务、配置、模型、真实数据或部署。

## Decisions

- 告警、事件、Case保留各自列表/详情、横向页签或内部目录。
- 事件默认进入队列，行点击预览、标题进入详情；管理同步关联告警的负责人和解决状态。左侧按告警和事件/案件管理分组，品牌改为AiSOC。
- Case列表按Prioritize incident cases两张官方截图，保留四卡片、工具栏、筛选集、Incident/Generic名称与右侧列设置。优先级分段>85/15–85/<15；不把事件队列套为Case列表。
- 原图覆盖的区域按图复刻；只有正文的核心内容按文字实现，仅在目录出现的Similar cases只留名称，不自行补列表。
- 核心交互使用一致的mock关系与本地状态；外围动作仅保留名称。
- 用无外部依赖的HTML/CSS/JavaScript实现于prototypes/security-pages，Python标准库仅提供loopback静态文件预览。
- 文档中的示例标题、示例IP/账号/事件关系与自拟mock数据共同组成一致的数据集；不收集真实账号或凭据。
- 本地存储保留管理及演示操作，提供重置入口；跨告警/事件/Case视图共享同一实体和关系。
- 本阶段取消skip_specs并添加前端原型规格，完成与否仍以实际浏览器回执为准。

## Risks / Trade-offs

截图跨版本，Legacy与Preview分别保留。部分详情仅有抽屉图，部分Case内容只有文字说明，已在主清单注明。

## Validation

核对JavaScript语法、静态HTTP与OpenSpec strict，逐组用浏览器验证核心交互、跨页关系、空态及布局，保存代表截图。结束由未参与实现者审阅本批源码和回执；不运行业务或模型测试。
