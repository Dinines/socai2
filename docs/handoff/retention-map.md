# 当前代码、数据与资料保留清单

日常接手从[前后端交接](../../FRONTEND_BACKEND_HANDOFF.md)及 [PROGRESS](../../PROGRESS.md)进入。当前入口维护一份有效状态，已结束批次按[历史索引](history/README.md)追溯；文件日期不能单独作为删除或移动依据。

## 当前工作入口

| 类别 | 位置与用途 | 整理规则 |
| --- | --- | --- |
| 业务源码 | `services/api/app/socai2/`、Fusion 接线及既有依赖 | 在普通项目目录维护；本轮无业务代码变更 |
| 模型配置与合同 | `services/api/app/socai2/` 内运行合同、[模型交接](../investigation/model-input-output-current-20261109.md) | 由显式 profile 选择，保留冻结映射和原件 |
| 部署与接入 | [21 部署](../../deploy/aisoc21/README.md)、`current-rollout.json`、`release-v1.2.json`、`production-v1.2.toml`、`workbench-current.json` | 当前 r6 发布包原位保留；仅整理本地文件不触发部署 |
| 4177 工具 | `docs/operations/processing_*`、`update_processing_audit.py` 及发布清单列出的脚本 | 属于当前代码，即使文件名有日期也不归档 |
| 测试工具与样本 | [tools/testdata](../../tools/testdata/README.md)、Case/事件/告警各批工具 | 当前测试仍用的原答、fixture 和驱动保留原路径 |
| 数据设计与字段 | [字段字典](../design/socai2-field-dictionary-20261103.md)、[数据交接](../investigation/socai2-page-data-handoff-20261106.md)、迁移 123–126 | 当前 29 表、462 列；不因文件日期改名或清理结构 |
| 原始证据 | `docs/operations/evidence/<batch>/`、调查交付目录 | 实际输入、提示、模型原答、失败、unknown 和读取回执保留，不以成功批次覆盖 |
| 工作台资料 | [运行记录](../../deliverables/investigation-validation-20261106/README.md#调查运行记录页) | 本机静态资料与 21 站点分别管理；本轮不删记录、不改页面数据 |
| 上游参考 | [固定源码分析](../reference/aisoc/README.md)及来源清单 | 唯一模块参考入口；`docs/anal` 保留到参考/归档的导航 |
| 需求原件 | [AI SOC2](../requirements/AI%20SOC2.docx) | 原字节不改写 |

## 本地归档及保留

本轮归档明细见[本地整理记录](history/2026-11-11-local-cleanup/README.md)。22 个已结束的发布源码包和产物共 7,667 文件移入 `.local/archive/2026-11-11-local-cleanup/`，原字节和可执行位保持。私有逐文件清单留在归档目录，不进入 Git；旧包内路径仍按原批次解释，恢复时按映射还原，不直接作为当前启动入口。

两个 r6 包保留在 `.local/unified-release/`、`.local/processing-release/`。另外三个包仍被既有 A/I 发布配置引用，保留原位：`v1.2-20261108-r3`、`v1.2-20261108-r5` 和 `processing-20261108-r2`。它们的存在不表示当前运行版本；未为整理而改写配置。

`.local` 的环境、配置、证据和其他任务目录，以及 `runtime-data/`、未提交的 `tools/model-preflight/` 保持。数据库/卷、私密配置、既有失败原答和已结束批次不清空、不重派。较早但仍被构建或测试引用的源码与样本继续保留。

## 历史来源

初始迁入清单、固定上游和原工程保留边界见[整理前保留清单](history/2026-11-11-local-cleanup/retention-map.md)及 [handoff-manifest.json](handoff-manifest.json)。历史回执里的路径、hash 和状态只说明当时来源，不充当当前实施完成证明。其他活动 OpenSpec 的完成勾选不等于已通过独审，本轮没有代为归档这些功能 change。
