# 当前进度

更新于 2026-11-10。**21 已部署当前 A/I 与 Case C1/C3/Deep/C6；两案首轮及一案人工反馈后调查已实测，保存、读取和字段对应通过，模型正文质量为 NOT_PASSED。** 工作约定见 [AGENTS.md](AGENTS.md)，前后端从[交接指南](FRONTEND_BACKEND_HANDOFF.md)进入。

## 当前运行状态

| 项目 | 已核验结果 |
| --- | --- |
| 分支 | `V1.1`；保留既有源码、测试和证据 |
| 21 发布 | `v1.2-20261110-r4`，处理组件 `processing-20261110-r4`；A/I/Case 三项 profile 与策略 hash 匹配 |
| 正式数据 | `aisoc.socai2`，29 表、462 列；37 组枚举、40 项 JSON 合同及 4 个共用定义保持 |
| 服务 | 6 服务健康；工作台独立组件 `workbench-20261110-r2` 已部署，其他服务保持前批来源和容器身份 |
| 读取与写入 | 页面及分析读取启用，Case/H GET 可读；Case HTTP 写开关关闭，自动消费者暂停；按需作业及 H 服务层验收可真实保存 |
| 时限与预算 | 模型单次 300 秒、Case 1500 秒、最终阶段预留 300 秒；单 Run 限制读取策略，租户累计三项配额不限制 |
| 数据与合同 | 本批无 DDL 或 GRANT，告警交接合同保持；两组来源原有 366 行未改写；GET 核验前后快照一致 |
| 内部查阅 | 21 的 4177 登记 20 份记录（含两案在线缓存），本机 49 份；左侧流程、右侧节点详情可查提示词、输入、输出与失败原因 |

## 已验证结果与修正

4177 节点详情已按用户要求完成：Case/A/I 节点、Deep 失败调用、冻结输入、查询零行／跳过和缺失空态均可查；切换轮次清空旧选择，原件锚点保留。30 项定向测试通过，两案 307 条 Run／步骤／工件逐值保持；200 次静态 HTTP 核对通过。工作台缓存随渲染源码更新而重新生成，未触发模型、消费者或业务写入。见[本次实施与验收](openspec/changes/complete-socai2-investigation-chain/workbench-node-inspector-20261110.md)。

批次 `case-current-flow-20261110-01` 使用两组已有演练材料，新建 2 个 Case、3 个 Run，共 8 次真实模型调用、154,491 reported tokens，费用未知。3 轮均为 `completed/partial`，最终结论拒收，两案 `current_assessment_id` 均为空。模型调用发生在本批修正发布前；当前生成约束修正尚未进行新的真实模型验收。[实测报告](openspec/changes/complete-socai2-investigation-chain/case-current-flow-20261110.md) · [逐轮统计](docs/operations/evidence/case-current-flow-20261110-01/execution-summary.json)

按用户“你帮我补充”整理的 H 明确标为助手代拟的材料完整性核查，不是业务授权或新增观察。创建、完成、仅改负责人／期限形成 3 个不可变版本；正文及完成事实保持。H 正文完整出现在后轮 C3、Deep、C6 请求中；首轮因反馈变化过期，后轮未因仅改管理字段而过期。模型仍重复部分错误推断，传递通过不等于正确理解。知识来源因工具预算预留而跳过，没有知识实际消费结论。

已修正 Deep 与 C6 生成 Schema 允许执行回执充当结论依据的偏差；查询状态仍保留在输入，C6 analysis 仍可引用覆盖信息。20 项边界测试、26 项处理／发布测试通过，5 份保存原答的离线复验确认受影响引用被生成约束拒绝，原答及失败不改写。另修正核验器对空当前判断、跨 Case 关联和活动的误判，并补齐 H 版本逐值核对。

最终 365 次真实 GET：357 次 200、8 次预期 404；16,820 项字段／正文／关联检查全部通过。独立活动复核另有 1,083 项通过，不并入前述数量。4177 静态发布核实 199 个文件、200 次 HTTP 读取，已有记录和容器保持。[读回汇总](docs/operations/evidence/case-current-flow-20261110-01/readback-03/summary.json) · [4177 回执](docs/operations/evidence/case-current-flow-20261110-01/workbench-publication.json)

## 未完项与下一步

先处理 C3 成员范围、C6 发现关联及正文事实扩大，再以独立批次核修正后的真实输出；不能重派已结束 Run。需要单独取得知识实际查询及使用证据，随后按[执行顺序](openspec/changes/complete-socai2-investigation-chain/design.md#后续工作顺序)联调页面操作与 P01–P04，再验证自动流程。3.7、3.23、3.30 等整体任务保持未完成，不归档 change。

读写权限和角色设计不作为独立前置，必要接线随功能处理；告警相关前后端字段合同保持稳定。问题、限制及验收落点统一记录在[问题清单](docs/investigation/current-issues.md)。本次 4177 实现、21 部署和交接已完成，[独立结束审计](docs/operations/evidence/workbench-node-inspector-20261110-01/independent-audit.json)为 ACCEPT，0 个未解决必须修正项。已推送 `origin/V1.1`，父项目 `add-server-submoudle` 仅更新 `server` 引用，本机父项目工作树保持；[发布回执](docs/operations/evidence/workbench-node-inspector-20261110-01/publication-initial.json)记录已验证的实现提交，收尾记录随同一分支同步父项目。不以内部查阅优化核销模型正文质量。
