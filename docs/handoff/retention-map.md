# 当前代码 数据与资料保留清单

更新于2026-11-14。当前工作从[PROGRESS](../../PROGRESS.md)和[交接指南](../../FRONTEND_BACKEND_HANDOFF.md)进入；历史原文从[归档索引](history/README.md)查阅。文件年龄不等于无用，有运行、测试或合同依赖的材料继续保留。

## 当前保留范围

| 类别 | 保留位置及原因 |
| --- | --- |
| 业务与运行代码 | `services/`、当前部署/启动脚本及配置；资料归档不修改运行行为 |
| 现行调查设计 | 主调查`design.md`、模型字段设计、采用规则，以及流式change的设计/规格/任务；主调查31/41与流式未实施状态保持 |
| 数据合同 | [当前机器字典](../design/socai2-data-contract-current.json)、[数据交接](../investigation/socai2-page-data-handoff-20261106.md)、OpenAPI及JSON合同；当前28表450列。冻结V1的29表462列、迁移123–126和原始需求继续保留 |
| 当前评审和验收 | [11-14评审](../investigation/investigation-current-review-20261114.md)、三案原件、固定功能发布及HTTP同步回执；失败、unknown和NOT_PASSED不改写 |
| 4177和4173 | 当前三案保存快照、生成工具、已备份展示及demo原有编辑；本轮不重建或清空页面数据 |
| 测试样本与历史工具依赖 | `tools/testdata/`及仍被程序/配置引用的早期证据和文档；本轮保留项及引用方见归档manifest的`protected` |
| 当前本机发布基底 | `.local/unified-release/v1.2-20261113-r1/`、`.local/processing-release/processing-20261113-r1/`；由当前发布配置引用 |
| 旧配置仍引用的本机包 | `v1.2-20261108-r3`、`v1.2-20261108-r5`、`processing-20261108-r2`原位保留，存在不代表当前运行版本 |
| 其他本机资料 | `.local`环境/凭据/配置、运行数据、未提交的`tools/model-preflight/`及其他任务目录保持 |
| 上游与需求原件 | [固定上游参考](../reference/aisoc/README.md)、[需求原件](../requirements/AI%20SOC2.docx)、来源manifest保持 |

## 历史资料

[11-14整理](history/2026-11-14-investigation-cleanup/README.md)归档130份旧文档/汇总和32个旧证据批次；21份无当前配置/进程引用的本机旧发布产物移至`.local/archive/2026-11-14-investigation-cleanup/`。所有移动保存路径、字节和摘要；仅Markdown查阅副本调整链接，原始字节另存。当前入口的原文也已保存，逐批流水从历史读。

[11-11整理](history/2026-11-11-local-cleanup/README.md)及更早原件保持；其“当前r6”等表述只适用于当时，本轮已更新实际保留基底。没有清理数据库/卷、删除模型原答、追认失败、启用消费者或归档未完成业务change。
