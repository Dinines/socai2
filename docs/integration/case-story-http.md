# 案件故事查询：后端调用指南

本轮实现 E65 `GET /api/v1/socai2/cases/{case_id}/story`。用途是把本案告警、历次基础调查和人工完成结果按实际时间集中读取。AI对话已暂缓，本接口只读已有数据，不生成分析或改变案件。正式环境状态见[交接入口](../../FRONTEND_BACKEND_HANDOFF.md)；本机验收证据见[本批记录](../operations/evidence/case-story-20261113-01/README.md)。

## 输入与调用

```http
GET /api/v1/socai2/cases/<真实Case UUID>/story?limit=20&q=主机名
```

| 输入 | 含义 |
| --- | --- |
| case_id | 路径中的案件UUID，须来自当前环境真实回执 |
| q | 可选，最多200字符；去首尾空白，按字面子串搜索，大小写不敏感。`%`和`_`按普通字符处理 |
| severity | 可选，info/low/medium/high/critical；只过滤告警条目，保留调查及人工结果作上下文 |
| limit | 默认20，1–100 |
| cursor | 上页next_cursor原样传回；更换案件、关键词或等级后清空，不传空字符串 |

q检索：告警标题/说明及最新材料中的主机、账号对象值；调查标题/目的及已保存结果的标题、结论、变化摘要；人工任务标题/说明及确认结果。先检索整个案件范围，再取当前页，不限于已加载记录。查询不解析原始日志JSON，也不搜索其他案件。

## 输出的每个新增字段

| 字段 | 含义与结果 |
| --- | --- |
| items | 本页故事条目 |
| total | 筛选后全部故事条目数；不是告警数或当前页数量 |
| next_cursor | 下一页游标；null表示结束 |
| observed_at | 本次读取时间，用于说明观察时点，不当作事件时间 |
| items[].id | 稳定键：`alert:`、`investigation:`或`human_result:`加源UUID |
| items[].kind | alert告警、investigation基础调查、human_result人工完成修订 |
| items[].occurred_at | 条目真实时间；null表示未知并排在最后 |
| items[].time_source | event_time、started_at、ended_at、completed_at或unknown |
| items[].alert | 告警的既有AlertFacts全部字段，其他类型为null；字段定义沿E28，未改告警合同 |
| items[].run | 调查的既有RunView，其他类型为null；执行状态和交付完整性分别读取 |
| items[].results | 该终态Run保存的全部baseline ResultView，按saved_at/id升序。保留每份结论、发现、待核事项、影响和范围；未产出或尚在运行时为空，不补造结论 |
| items[].task_revision | 完成时不可变TaskRevisionView，保留result_text、result_scope、完成时间及来源；其他类型为null |
| items[].is_current_task_revision | 此完成版本是否仍为任务当前版本；false表示历史版本仍可阅读，不能当成当前已完成状态。其他类型为null |

嵌套AlertFacts、RunView、ResultView、TaskRevisionView复用原合同，全部字段类型和含义在Swagger Models中展开；合成完整输入输出和422/404示例在[HTTP目录E65](../../deliverables/investigation-validation-20261106/http-handoff/endpoints.md#e65)。

告警时间取event_time；completed/failed/cancelled调查取ended_at，running/unknown取started_at；待启动调查没有实际开始时间，保持null。人工结果取completed_at。按该时间倒序，同时间按条目id倒序，未知最后。每次请求是只读一致快照，跨页期间源记录变化时应重新从首页读取。

## 查看详情和后续操作

| 条目 | 回查接口 |
| --- | --- |
| 告警 | E28 `/alerts/{alert.id}`；检测战术用E31材料，设备库存/标签用E30 records/assets |
| 调查 | E12 `/cases/{case_id}/runs/{run.id}`；每份结果用E14 `/cases/{case_id}/results/{results[].id}` |
| 人工结果 | E43 `/cases/{case_id}/tasks/{task_revision.task_id}/revisions/{task_revision.id}`；当前任务另用E41读取 |

选择条目由调用方保存选中ID，不会修改Case成员；查询不会启动模型、自动创建任务或采用结果。人工完成结果属于历史陈述，不自动证明已核实或当前任务已结束。

## 错误

- 404 `case_not_found`：案件不存在或不在当前租户。
- 422字段错误数组：UUID、limit、severity或字符串长度不合法。
- 422 `story_query_parameter_not_supported`：未知或重复查询参数。
- 422 `invalid_story_cursor`：游标损坏；从首页重新读取。
- 422 `story_cursor_filters_changed`：游标来自其他案件/租户或筛选已改变；清空后读取。
- 503 `socai2_case_api_not_enabled`表示读取配置尚未启用。
