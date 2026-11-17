# 分析任务HTTP读取本地验收

2026-11-14，流式change任务2.7中的一个读取步骤。告警、事件、案件各增加列表及详情GET，共6操作；独立HTTP端口通过适配器调用核心read_task/list_tasks，不修改受理、执行、调度或表结构。

## 直接验收

[pg-02.json](pg-02.json)通过：真实本机隔离PostgreSQL `v12_upgrade_dev`，新UUID合成批次9个分析任务、7次实际核心尝试、5个保存Run及A/I/Case各1个结果。

- 38次ASGI请求：25次200、8次422、4次404、1次503。三类对象均遍历列表分页及详情，status_url、实际run_url和结果url均逐个读回。
- accepted无尝试、running准备中无Run、skipped/no_changes、failed重试后unknown本地结束、accepted等待下一次重试、completed均正确返回。未造Run，不改原unknown，队列/内部attempt ID及合并根ID不对外暴露。
- 合并的原task_id保留原身份/受理时间，跟随同一实际尝试与结果；合并关系在真实PG中显式合成保存，**不证明Redis或自动归并执行已交付**。
- 结果引用取真实result_type/id/source_run_id/kind；A/I链接返回对应Run的实际result，Case链接返回独立结果，三类ID不混用。[核心补齐回执](../analysis-task-results-20261114-01/README.md)另验同Run的human_feedback不进入分析结果。
- 同对象分页稳定、total完整，跨对象游标422；跨主体任务/不存在对象404。503由实际HTTP工厂缺任务policy产生，不是数据库故障替身，也未开展数据库故障测试。
- 14类合成业务记录完整行摘要在GET前后一致，保留所有样本，不清表。5项HTTP边界/可信接入检查、目标Ruff、OpenSpec strict和候选OpenAPI检查通过，见[检查与源码摘要](checks.json)。

[输入输出示例](examples.json)来自实际HTTP回执；[候选OpenAPI](candidate-openapi.json)共81操作，无登录/Token要求。查看[逐字段对接指南](../../../integration/analysis-tasks-http.md)。

PG运行入口：`.local/conda-envs/socai2/bin/python .local/v1.2-reader-validation/run_pg.py test_socai2_analysis_task_http_pg docs/operations/evidence/analysis-task-http-20261114-01/pg-02.json analysis_task_http`。隔离环境凭据只从私密配置读取；候选测试分页默认2/最大3用于遍历，正式样例默认50/最大100未改。

## 失败及未验边界

[pg-01.json](pg-01.json)为首次合成Case结果漏填created_at导致约束拒绝，Run/结果所在事务回滚；先前已受理记录保留。补测试必填值后新UUID批次通过pg-02，没有修改旧失败回执或清理数据。

仅ASGI加真实隔离PG，不是本地常驻服务/21的TCP验收。模型、取证工具、Redis均未调用；runner的通用model_and_lake标签不代表本批生成了模型结论。测试用例对已知失败设0秒重试仅为立即生成读侧样本，未改变正式policy。

正式本地/21与静态Swagger仍71操作，候选81操作待统一发布。新增任务GET不代表异步POST、自动建案/分诊、定向/综合或调度已实现；2.7和整个change不据此勾选完成。本步未部署、重启、Git提交或推送。
