# 历史测试业务数据清空回执

2026-11-16。负责人明确允许删除历史测试告警、事件、调查及关联信息，并在共享 aisoc 整表方案自动审核首次拒绝后，追加“给全权限 删除”“整表清空方”。按冻结表清单执行整表 TRUNCATE，无 CASCADE、DROP DATABASE 或清卷。

[汇总回执](outcome-summary.json)：本机与 21 共 **18 数据库、635 张选定业务表、106415 行**已清空，逐库读回为 0，schema 前后相同；**4 张湖表 147 行、8 个向量集合 20 点、26 个 Redis 键**已清空。**120 个 socai2 Topic、128 分区**的起止 offset 相等，移除当时仍保留的 39 条消息，Topic 和其他命名空间保持。offset 累计值不归零。

当前 4177 的 3 个活动批次撤出，业务告警/事件/Case 及批次四个真实 HTTP 列表均空，见[最终读回](final-readback-01.json)。未重新投递告警、重跑模型或导入旧记录。

| 范围 | 原始回执 |
| --- | --- |
| 21 的 9 数据库，含共享 aisoc 选定业务表 | [执行清单](reset-pg-remote-authorized.json)、[逐库结果](reset-pg-remote-authorized-01.jsonl) |
| 本机 2 数据库、V12 7 数据库 | [本机](reset-pg-local-01.jsonl)、[V12](reset-pg-local-v12-01.jsonl) |
| 湖、知识、队列、缓存 | 本目录 `reset-lake-*`、`reset-vector-*`、`reset-kafka-*`、`reset-redis-*` 原件及对应明确资源清单 |
| 4177 活动账本 | [删除及摘要](reset-ledger-remote-02.jsonl)；只剩锁文件，没有可见批次/证据文件 |
| 消费停止及服务恢复 | [Fusion 停止](stop-fusion-01.json)，调度仍 created 未启动；8 个为清理临时启动的本机服务已恢复 exited，58477 预览已关闭；随后[停止本机旧 4173 演示](stop-old-preview-4173.json)，不继续展示旧快照 |

账号、租户、凭据、配置、迁移/表结构及其他项目不在清理表清单内。私密恢复备份分别保存在 21 `/opt/sting-aisoc-socai2/private/test-data-reset-20261116-01/` 与本机 `.local/test-data-reset-20261116-01/`；这些不接活动数据源或模型。仓库历史回执和旧模型原答保留用于审计，未改写为成功。

执行中本机旧 V12 tmpfs 空间不足，临时从 256 MiB 调至 512 MiB 完成清理后已恢复 256 MiB，未重建或删卷。Redis 空密码的只读盘点失败、账本根路径第一次摘要拒绝均在变更前停止；修正后新回执通过，原失败保留。首次共享库自动审核拒绝已由本轮更具体授权解决，当前无待批准清理。
