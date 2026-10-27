## Context

AiSOC Alert.status 表示业务处理状态，调查状态属于任务；Alert.event_time 是发生时间，first_seen/last_seen 含义不同。依据 services/api/app/models/alert.py 与 docs/integration/v1/page-elements.md 的 A03/A08/A09/A17—A20。

## Decisions

- 从共享告警列派生主列表专用列，避免影响事件/Case 内嵌表。
- 主列表行投影使用 event_time；当前旧 Mock 没有该字段时，以其 first 样例值作为模拟发生时间。该兼容仅用于原型，不定义真实 API 回退。
- 日期过滤接受该表 timeField 选项，默认仍用 first；排序与 CSV 读取同一列键。
- 保留现有浅色样式、状态枚举和管理交互，不扩展状态模型。

## Validation

JS 语法；浏览器查看表头、列设置、时间双向排序、日期筛选、快捷状态筛选及导出；确认事件/Case 内嵌表未变。保留截图及简短回执，按仓库要求由未参与实现者窄审。撤回本批局部增量即可回退，无数据迁移。
