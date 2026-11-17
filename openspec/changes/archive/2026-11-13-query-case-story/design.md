# 案件故事只读查询

## HTTP与业务口径

GET `/api/v1/socai2/cases/{case_id}/story`，即E65。输入：Case UUID、可选q（去首尾空白，最多200字符）、severity（原告警五级枚举）、limit（默认20，1–100）、cursor（上页原样传回，最多2048字符）。未知/重复参数、错误游标及跨Case/筛选复用游标返回422；Case不存在404。读取复用既有Case读配置和身份，不另设权限流程。

返回items、total（全部筛选命中条目数）、next_cursor、observed_at。每个条目有稳定id（类型+源UUID）、kind、occurred_at、time_source，并且只有对应类型的alert、run/results、task_revision/is_current_task_revision有值。告警直接复用AlertFacts；调查直接复用RunView及ResultView；人工结果直接复用TaskRevisionView，不改字段、原文、枚举或原来源关系。告警战术/资产等仍从既有E31/E30组合读取，不在故事接口复制库存服务。

- alert：仅当前Case成员，时间严格取event_time；未知为空，不补入库时间。E28/E30/E31按alert.id回查。
- investigation：本案全部baseline Run，每Run一条；终态completed/failed/cancelled按ended_at，running/unknown按started_at，pending_update无实际开始时间，置空。只对终态读取其已存baseline Results；活跃Run不提前显示结论。每份结果保留自己的id、来源Run、范围及状态；E12/E14回查。未产出结果返回空列表，不伪造结论。
- human_result：本案所有已完成的不可变任务修订，按completed_at；旧完成版本在任务重开/编辑后仍保留，并标is_current_task_revision，避免当作当前待办状态。E43按case/task/revision回查。

q是字面、不区分大小写的子串匹配，不把%/_当通配符。告警检索title/description及其最新材料中host/user对象的raw_value/normalized_value；调查检索title/purpose及已存结果的title/conclusion/change_summary；人工结果检索title/description/result_text。不会把内部JSON键或全库记录当搜索内容。severity仅筛选告警条目，调查与人工结果仍保留作上下文，不把案件等级冒充每轮或任务等级。所有过滤先在数据库执行再分页。

按occurred_at倒序NULLS LAST、稳定id倒序。游标绑定租户、Case与筛选；改变条件从首页开始。单请求REPEATABLE READ READ ONLY；跨请求是实时读取，不承诺快照长期冻结，源时间/内容变化后应刷新。游标只定位，不构成授权。

## 分层与验证

新`case_story_contracts.py`/`case_story.py`负责合同和只读用例，独立`external_routes/story.py`经port/adapter调用，不在路由写SQL，不改变CaseService或执行器。无迁移、写入、模型调用、消费者或页面修改。

先strict校验，再实现；复用已有边界检查及原64操作结构比较。用本机独立合成批次真实TCP/PG核对混合排序、未知时间、搜索与等级、连续分页、源记录跳转、历史人工版本及读取前后不变。合成Run/Result仅验证读取，不算模型验收。完成文档及未参与实现者结束审计后，再按本批授权安排统一发布，不将本机候选说成21已上线。
