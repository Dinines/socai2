# 分诊保存后同步的一次直接流程

`knowledge-sync-20261112-01` 已完成：一条新合成告警、一个 A Run，使用明确标记的模板判断，通过原 `StageResultService.finish` 提交并采用后触发真实 PostgreSQL 入库、现有嵌入服务及独立 Qdrant 集合；一个历史目的只读查询和 5 个原 HTTP GET 读回。重复 finish 保持原 outcome 和两份同步工件。没有分析模型、Case Run、消费者或厂商查询。

驱动 `python -m tools.testdata.knowledge_sync.run prepare|run --config tools/testdata/knowledge_sync/local.json` 只用于该批；排他意图及源码指纹阻止重发，后续验收必须使用新批次。认证以本地适配器提供，数据库实际角色 `v12_developer`，不当作生产处理角色权限证据。原 C02 材料保持，模板判断不是模型原答或独立真值。

结果见 `docs/operations/evidence/knowledge-sync-20261112-01/local-flow/`；读取工具保存了本 Run 的判断、原 publication、意图／结果、当前卡和查询源链。SQLAlchemy 对既有循环外键产生排序警告，读取成功；未因此扩展 DDL 或重跑流程。
