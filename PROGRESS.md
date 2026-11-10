# 当前进度

更新于 2026-11-10。**Case 查询主体、有限引用纠正、背景取证和 Deep 生成合同修复已完成本地验收、独立结束审计及 21 统一发布，生产读取核验通过。模型质量仍为 NOT_PASSED。** 工作约定见 [AGENTS.md](AGENTS.md)，前后端从[交接指南](FRONTEND_BACKEND_HANDOFF.md)进入。

## 当前运行状态

| 项目 | 已核验结果 |
| --- | --- |
| 分支与交付单元 | `V1.1`；本轮为 [fix-case-evidence-scope-and-recovery](openspec/changes/archive/2026-11-10-fix-case-evidence-scope-and-recovery/tasks.md)，一个 change 完整验收后统一发布、推送；父项目 `add-server-submoudle` 的 `server` 引用以远端实际 commit 为交付锚点 |
| 21 发布 | `v1.2-20261110-r5`，处理组件 `processing-20261110-r5`；只更新 API，五项继承服务保持容器身份 |
| 服务 | 6 服务健康；4177 使用独立组件 `workbench-20261110-r2`，本机 4177 是 SSH 转发到 21 |
| 正式数据 | `aisoc.socai2`，29 表、462 列；告警前后端合同、37 组枚举及 40 项 JSON 合同保持，本轮无 DDL |
| 运行接线 | Case/H GET 可读，Case HTTP 写开关关闭，自动消费者暂停；权限设计不作为功能前置 |
| 预算 | 单 Run 6 模型、4 工具、131,072 token，模型单次 300 秒、Case 1500 秒、C6 预留 300 秒；额度未提高 |
| 查阅资料 | 21 的 4177 共 26 份记录，本轮追加 6 份，原记录保持；524 文件／525 HTTP 核验通过。本地静态资料库合计 55 份，与 21 分开计数 |

## 本轮结果

查询发起成员与历史返回行主体分开保留，C02 的 A3 查询中 A1 记录按核验身份映射，C3／Deep／C6 均保留原路径、角色和原文。C3/C6 对可定位的来源、成员覆盖和本次发现关联错误最多纠正一次；unknown、截断和无预算不再派发纠正。Deep 每个生成分支含完整必填项及限制，与接收合同一致。背景来源按显式配置和已有配对回执排序，仍预留后续工具额度。[实现与验收](openspec/changes/archive/2026-11-10-fix-case-evidence-scope-and-recovery/validation.md)

最终 69 项定向检查通过；真实本地 PostgreSQL 的三项完整流程通过，覆盖纠正成功、纠正仍错时保留部分结果，以及 H→下一轮的保存和读回。29 表／462 列前后不变，原描述及业务值保持。模型与数据湖替身结果单列，不当作真实模型质量。

另外三次独立本地真实调查共 14 次模型调用、161,323 reported tokens，费用未知；160 个原 GET 处理函数读回和 9,819 项字段／原文／关联检查通过。三轮都是 completed/partial：一轮 C6 纠正后采用，两轮最终结论拒收；最后一轮 Deep handoff／answer 已完整通过，但 C3/C6 仍存在标签冒充观察及正文扩大。程序校验、交付、采用与模型质量分别记录，不报告准确率。[逐轮汇总](docs/operations/evidence/case-scope-recovery-20261110-01/execution-summary.json)

21 发布后对既有两案及 H 后轮执行 365 次 GET、16,820 项字段与关联核对，全部通过；8 次预期的错误父主体 404 单列，读取前后数据保持。本轮没有生产业务写入或重派已结束 Run。[发布与读取回执](docs/operations/evidence/case-scope-recovery-20261110-01/delivery-summary.json)

## 未完项与下一步

本 change 的程序修复经独审 ACCEPT，0 个未解决必须修正项，按本次证据收口。主调查继续单独处理模型来源角色及正文质量、真实非空知识的使用、页面操作 P01–P04 和自动消费。知识查空不证明使用成功，H 传递不证明业务授权；3.7、3.23、3.30 等整体任务保持未完成。所有问题集中在[问题清单](docs/investigation/current-issues.md)。
