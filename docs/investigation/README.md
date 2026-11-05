# 当前调查模块

开发目录 `E:/aisoc/socai2`，分支 `codex/case-baseline-history-20261103`。直接在分支开发，独立服务与原服务分开；页面不在本轮修改范围。

按以下顺序阅读：

1. [当前执行账本](current-execution-ledger.md)：Kafka/Fusion→A告警→I事件→Case C1—C6→H人工跟进；每步输入、处理、输出、Run/Step和数据库修改，含完整例子。
2. [当前审计与修复状态](current-investigation-audit-20261105.md)：五项问题的实际处理、测试证据及C6剩余额度缺口。
3. [数据库写入目录](current-database-write-catalog.md)与[只读查账SQL](current-execution-readback.sql)：124个写点、源文件指纹，以及按tenant/case/run读取原件的方法。
4. [已保存执行记录索引](current-execution-records.md)：固定实测快照里的26个Run、162个Step、361个工件；它是原始执行证据，不是当前修复后的重跑结果。
5. [我们的主设计](../architecture/investigation-planning-design.md)、[字段字典](../design/socai2-field-dictionary-20261103.md)与[OpenSpec任务](../../openspec/changes/complete-socai2-investigation-chain/tasks.md)。

当前实现保持同Case基础调查单活跃、手动启动；H保存反馈后由用户prepare/start下一轮，Q仅保留501接口。已完成代码修复和隔离PG验证不代表常驻服务已更新或真实模型整链验收通过。C6输入已不丢必要事实、人工反馈和原计划，但固定样本的完整请求仍超过剩余共享预算，当前判断不被系统交接覆盖。

[开源版本实现](../architecture/opensource-investigation-implementation.md)仅作能力基线。各批次原请求、原答、失败回执保留在原路径，不能重写成当前成功证据。
