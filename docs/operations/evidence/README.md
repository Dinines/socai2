# 调查证据入口

当前状态见[PROGRESS](../../../PROGRESS.md)。本目录保存原始输入、请求、模型原答、错误、保存和读回回执；批次结束后不重派、不覆盖失败，也不把历史发布版本当作当前状态。

| 用途 | 批次 |
| --- | --- |
| 当前评审及4177展示问题 | [11-14评审](investigation-current-review-20261114-01/README.md)，包含Schema差异、运行只读和RV12结论展示定位 |
| 当前4177三案 | [11-14固定调查](fixed-investigation-20261114-01/README.md)，4A/2I/3Case、19次生成，质量NOT_PASSED |
| 工作台保存快照模式 | [11-14展示修正](workbench-display-fix-20261114-01/README.md)，不代表本轮修复了RV12 |
| 现行核心发布 | [固定功能发布](fixed-investigation-release-20261113-01/README.md)、[发布基线10批](fixed-investigation-20261113-10/README.md) |
| 现行独立HTTP同步 | [两端源码及既有数据读回](investigation-http-sync-20261113-01/README.md) |
| 已归档的早期批次 | [32批历史数据与原件](../../handoff/history/2026-11-14-investigation-cleanup/evidence/)、[目录及路径映射](../../handoff/history/2026-11-14-investigation-cleanup/README.md) |

仍被测试、配置或核验工具引用的旧批次原位保留，引用方见归档manifest的`protected`。日期较早不代表可删除；程序交付、模型质量、真实数据库、测试替身和生产只读证据分别解释。
