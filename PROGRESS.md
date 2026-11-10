# 当前进度

更新于 2026-11-10。**Case Finding 来源角色生成及一次纠正反馈已完成本地验收、独审和 21 统一发布，生产读回通过。模型质量仍为 NOT_PASSED。** 工作约定见 [AGENTS.md](AGENTS.md)，前后端从[交接指南](FRONTEND_BACKEND_HANDOFF.md)进入。

## 当前运行状态

| 项目 | 已核验结果 |
| --- | --- |
| 分支与交付单元 | `V1.1`；本轮为 [align-case-finding-evidence-roles](openspec/changes/archive/2026-11-10-align-case-finding-evidence-roles/tasks.md)，一个 change 完整验收后统一发布、推送；父项目 `add-server-submoudle` 的 `server` 引用以远端实际 commit 为交付锚点 |
| 21 发布 | `v1.2-20261110-r6`，处理组件 `processing-20261110-r6`；只更新 API，五项继承服务容器保持 |
| 服务 | 6 服务健康；4177 使用独立组件 `workbench-20261110-r2`，本机 4177 是 SSH 转发到 21 |
| 正式数据 | `aisoc.socai2`，29 表、462 列；告警前后端合同、37 组枚举及 40 项 JSON 合同保持，本轮无 DDL |
| 运行接线 | Case/H GET 可读，Case HTTP 写开关关闭，自动消费者暂停；权限设计不作为功能前置 |
| 预算 | 单 Run 6 模型、4 工具、131,072 token，模型单次 300 秒、Case 1500 秒、C6 预留 300 秒；额度未提高 |
| 查阅资料 | 21 的 4177 共 29 份记录，本轮追加 3 份；233 文件／234 HTTP 核验通过。本地静态资料库合计 58 份，与 21 分开计数 |

## 本轮结果

C3/C6 的 Finding 生成按 observed／inferred／unresolved 分支约束；observed 仅以有成员依据的直接观察作支持。原接收兼容性保持，角色／直接成员错误获得一次具体反馈；标签和说明保留原来源，程序不删引用、换状态或改正文使其通过。[实现与验收](openspec/changes/archive/2026-11-10-align-case-finding-evidence-roles/validation.md)

86 项相关检查、两项真实本地 PostgreSQL 完整流程通过，覆盖纠正成功和重复错误时保留有效部分。数据库 29 表／462 列及原材料保持；测试替身单列。前批三份原答回放确认生成／反馈缺口被修正，没有改写失败原件。

独立真实本地 C1–C6 Run 共 4 调用、38,844 reported tokens，费用未知；52 次原 GET 处理函数读回及 3,225 项字段／原文／关联检查通过。6 条 observed 的支持均为相应成员的 observation，0 次纠正；实际 completed/partial，C6 采用。Deep 仍把缺少演练材料当反证、把验收场景当业务环境，C6 有查询状态合并和缺个案依据的条件性影响外推，模型质量 NOT_PASSED。[实际汇总](docs/operations/evidence/case-evidence-roles-20261110-01/execution-summary.json)

21 发布后，两案及 H 后轮 365 次 GET／16,820 项字段关联核对通过，8 次预期错误归属 404 单列。原生产数据与前批快照一致，读取前后不变；本次发布没有新生产模型作业。[发布与读取回执](docs/operations/evidence/case-evidence-roles-20261110-01/delivery-summary.json)

## 未完项与下一步

本 change 独审 ACCEPT，0 个未解决必须修正项，按本次证据收口。归档及封后校验通过。子仓库最终内容与父项目 server 引用统一推送，以实际远端分支和 gitlink 读回为交付锚点；中间修改和测试均在本地。

后续依次按独立范围推进：M01 正文主张及缺口／反证边界、真实非空知识和 H 正确使用；再处理产品 HTTP／页面 P01–P04；最后验证自动消费。主调查仍为 31/41，3.7、3.10、3.23、3.30 等整体任务未完成。知识查空不证明使用成功，H 传递不证明业务授权。问题集中在[问题清单](docs/investigation/current-issues.md)。
