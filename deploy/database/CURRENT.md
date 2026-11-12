# 当前调查数据库入口

2026-11-12，迁移 127 后为 **28 表、450 列**。[当前调查表职责](../../docs/investigation/investigation-table-scope.md)和[当前机器字典](../../docs/design/socai2-data-contract-current.json)列出调查交付范围。资产、用户、租户等基础数据由业务后端提供，不要求复制旧平台公共表。

## 已有调查库

本次只删除 `socai2.graph_explorations`。先部署 28 表查询适配，再使用[受限增量入口](remove_unused_graph_table.sql)，显式传入 `expected_database`、`cleanup_lock_timeout` 和 `cleanup_statement_timeout`。脚本锁表后核空、核创建结构与依赖，使用 `DROP ... RESTRICT`，任何不符均回滚；不清空数据、不删其他表。迁移 127 要求显式目标，不通过未传此配置的通用全量迁移器执行。

已有 reader profile 可配置下列节，使用 `install_reader.py remove-unused-graph --profile <选定配置>`；普通 `upgrade` 不自动删表。

```toml
[cleanup]
lock_timeout_seconds = 3
statement_timeout_seconds = 30
```

目标连接、管理员、reader 和总时限沿既有 profile；凭据不写在命令行。[配置示例](reader-install.example.toml)保留普通安装用法，清理节仅供显式选择新入口时加入。

## 新独立空库

- [init_socai2_current.sql](init_socai2_current.sql)：先检查显式目标，再应用冻结 V1 和同一迁移 127。
- [init_socai2_current_reader.sql](init_socai2_current_reader.sql)：增加既有 V1.2 reader 依赖。使用 `install_reader.py initialize-current --profile <选定配置>`，需上述 cleanup 时限及显式 owner/reader。

这些独立运行入口复用 V1 的公共依赖支撑结构，仅用于新专用空库；它们不是业务后端的公共建表清单。共享业务库必须沿现有安装及后端提供的基础数据接入，不能运行空库初始化。

## 核验与实际交付

使用 `install_reader.py verify --profile <选定配置>`；它依据 127 账本与目标表存在性，核验未清理 V1 的 29/462 或当前 28/450。旧 `install_aisoc21_v1.py verify` 及冻结 V1 自检只适用于未清理基线，不能用来否定已完成增量的当前库。

本轮 21 `aisoc`、本机 `v12_upgrade_dev` 与 `socai2_local_20261105` 均已完成。其他开发者表、公共表、历史验收库及原业务数据保留。[清理回执](../../docs/operations/evidence/graph-table-cleanup-20261112-01/delivery-summary.json) · [工作台实际装载与读取](../../docs/operations/evidence/graph-table-cleanup-20261112-01/workbench-after-cleanup.json)。
