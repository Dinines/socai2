# 调查历史资料归档

2026-11-14，按负责人要求归档旧设计、评审、执行记录和不再使用的产物。当前工作从[PROGRESS](../../../../PROGRESS.md)、[前后端交接](../../../../FRONTEND_BACKEND_HANDOFF.md)及[11-14评审](../../../investigation/investigation-current-review-20261114.md)进入；本目录的版本、日期、授权和完成声明仅适用于原批次。

## 已归档内容

| 内容 | 位置与数量 |
| --- | --- |
| 旧设计和研究 | [架构资料](documents/docs/architecture/)、[设计与页面评审](documents/docs/design/)；现行合同和确认规则保留原位 |
| 旧调查评审与执行说明 | [调查历史](documents/docs/investigation/)，包括旧版“当前实现”、早期审计和执行交接 |
| 旧执行回执与隔离服务记录 | [操作历史](documents/docs/operations/)，原失败、未知执行和未通过结论保持 |
| 主调查早期验收材料 | [限定验收及评审](documents/openspec/changes/complete-socai2-investigation-chain/)，仅移动历史附件，主change仍31/41 |
| 上述文档与汇总 | 共128份Markdown、2份JSON；Markdown增加历史标识并调整链接，原字节存于[originals.zip](originals.zip) |
| 无现行程序/配置依赖的旧证据 | [32个完整批次](evidence/)，共561个文件；模型原答、快照和回执原字节保留 |
| 本机旧发布包与产物 | `.local/archive/2026-11-14-investigation-cleanup/`，21项、6,561文件、812,924,248字节；包含旧核心/处理源码包和早期离线发布包，不进入Git |
| 整理前的当前入口 | [进度](snapshots/PROGRESS.md)、[任务](snapshots/openspec/changes/complete-socai2-investigation-chain/tasks.md)、[OpenSpec入口](snapshots/openspec/README.md)、[保留清单](snapshots/docs/handoff/retention-map.md) |

仓库资料共移动691个文件、21,124,247字节；本机产物另行归档。文件只是搬移，没有以归档回收磁盘空间或删除业务数据。[manifest.json](manifest.json)逐项记录原路径、目标路径、字节数、模式、前后SHA和引用调整；237份移动或改写文档的整理前字节保存在ZIP中。

## 保留与查阅

现行设计、未完成需求、数据库/JSON/OpenAPI合同、11-14评审和三案原件、当前发布基线、工作台输出及有测试/配置依赖的旧样本保留原位。保留依据在manifest的`protected`中，日常入口见[保留清单](../../retention-map.md)。活动change不因文件较早或任务打勾而被视为已完成。

旧JSON、原始回执和包内路径仍是原批次值，不改写为新执行事实。查旧路径时先查manifest的`moves`和`files`；本机产物逐文件清单在私有归档中的`manifest.json`，公开清单只保存包级摘要。需要恢复时按映射还原到不存在的目标，不能覆盖当前文件；本次没有执行恢复或重派旧批次。

[链接检查](link-validation.json)核对2,508处重定位链接，没有新增目标缺失；其中43处历史链接在整理前已失效，保留并单列，不补造旧证据。

## 验证范围

直接检查文件字节与模式、原文ZIP、受影响链接、现行代码/配置/4177文件不变以及主调查41项任务状态。对本机42个容器的挂载和进程路径做只读核对，所移发布包未被引用。当前引用保留了旧工具兼容路径，不因归档修改业务代码或启动器。

[最终验证](validation-final-02.json)通过，[首次回执](validation.json)及[现行文件基线](protected-files.json)保留；[独立审计](../../../../openspec/changes/archive/2026-11-14-archive-investigation-history-20261114/audit.md)限定ACCEPT，本整理change已归档。没有数据库写入、服务重启、模型请求、4177重建、Git提交或推送；RV12页面问题仍为已定位未修复，模型质量仍NOT_PASSED。

封后首次检查因问题清单并行新增实施规划引用而记录FAIL，见[原回执](validation-final.json)。[差异核对](concurrent-document-addition.json)确认只有该新增段落，旧正文及归档重定位一致；并行新文件和引用均原样保留，再验通过。该记录不是业务或模型失败，不覆盖原核验结果。
