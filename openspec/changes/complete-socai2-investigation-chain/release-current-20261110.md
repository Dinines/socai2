# 当前流程发布与交接核验

2026-11-10，项目负责人明确要求把当前内容发布到 21，统一前后端交接、功能和表字段说明，登记已有问题，测试页面需求与数据流程对应，修正问题后推送远端及父项目。

## 范围与直接验收

- 发布当前 A/I 与 Case C1/C3/Deep/C6 程序、模板、输出适配、策略和读取代码；显式选择 Case 策略。仅更新 API、按需处理镜像及工作台源码；Fusion、Agents、projection、gateway 按现场定义继承。自动消费者保持暂停，Q 保持预留状态。
- 使用现有 `release_12.py` 和配置文件，冻结实际工作区源码、固定镜像 ID，核对运行加载的 A/I/Case 三项 profile、策略 hash、读取开关和原有服务配置。更换发布指针前验证；保留回退文件和已有数据。
- 29 表、462 列及迁移 123–126 保持；本批不提出或实施表设计、权限、隔离变更。字段字典、JSON 合同和 OpenAPI 按实际实现核对，修正说明和导出不代表修改数据库。
- 交接入口只陈述当前配置、功能、字段和空态；过程快照进入历史目录。功能清单继续使用 F01–F28/J01–J14；当前页面差异和模型质量问题集中登记，不能当作已完成。
- 复用已保存的隔离 PG 流程证据，补本次打包、策略、读取和 DTO 定向测试；正式库只读核对目录、字段/关系、GET、错误归属和读取前后数据一致性。无新增真实模型实验，测试结果不认定模型质量。
- 推送当前 `V1.1` 分支，按父项目远端 `add-server-submoudle` 最新提交仅更新 `server` gitlink；不覆盖父项目并发提交。

## 当前发布与配置

21 已激活 `v1.2-20261110-r2`，处理镜像 `processing-20261110-r2`。API 与工作台更新；Fusion、Agents、projection、gateway 的容器身份保持，六服务健康。读取、实际策略及 API 只读权限在激活前核验，启动迁移关闭，自动消费者暂停。

| 对象 | 已核验身份 |
| --- | --- |
| API 镜像 | `sha256:c6d4515729345181c59ea7960ff3cfb0549f3e2cbec6084704e3d8f69fd0af69`，586 个源码文件 |
| 处理镜像 | `sha256:df86e69caf87a4ec76e179e4fbe636085ca5e93b5cb0233db0d4b33649afda52`，648 个文件 |
| 统一 manifest | `6a9c3351c3d0650147a248c16b4806f6cad4ca15312a10218d46da61ed2de4c3` |
| 策略 | `investigation-policy-case-v1.toml`，SHA-256 `ea886f6aba7858d7a894efb2659d78d11299e2e30ca40956fcbd80ef0b2f2130` |
| profile | `socai2.alert-boundary.v1`、`socai2.incident-boundary.v1`、`socai2.case-boundary.v1` |
| 读取与写入 | PAGE_READ／ANALYSIS_READ 启用，CASE_API 关闭；Case/H GET 走读取开关，写操作仍受 Case 开关限制 |

[激活回执](../../../docs/operations/evidence/current-release-20261110-01/unified-activate-20261110T070702690795Z.json)包含实际运行镜像、644 个工作台绑定文件、策略、只读核验及当前入口。保留发布前的镜像、Compose 与配置快照。本批无 DDL、GRANT、自动消费恢复或真实模型调用。

## 实际发现与修正

1. 首轮部署后的 Case/H GET 返回 503，因为依赖函数共用关闭的写开关。`socai2_cases.py/socai2_tasks.py` 根据请求方法选择允许页面读取的分支，认证、租户、权限及写开关保持。定向用例覆盖开关组合及写入拒绝，修复后部署 r2 再读回。
2. 结构安装核验器把已获准的 API schema USAGE 当异常。核验改为检查获准 SELECT、无调查写权限／schema CREATE／管理旁路；实际 `verify` 通过，前后保护指纹相同。没有执行授权语句。
3. 相关告警查询可在同租户内跨 Case 匹配。核对器原来仅从本案数据计算期望值，现从同一只读快照核匹配对象及当前材料，按类型、命名空间、对象键比较。这个修正没有改变业务接口。
4. OpenAPI 和交接说明存在缺项或过期表述。完整导出同步为 44 个路径、48 个方法，补齐来源工件、Case 活动及事件交付字段，6 份设计导出及 2 份对应镜像保持当前实现。正文上限由策略读取，当前 1,048,576 字节；Case 限额按 Run 冻结值读取。

首次 API key 已过期，以同一测试用户已有密码正常登录后复验，没有创建用户或扩权。初始 401、r1 的 503、相关告警期望值错误及早期测试失败均保留。字段类型核验曾误把逻辑 `enum/ref/json` 名称直接当 SQL 类型，JSON 检查曾未解引用外部 Schema；最终校验分别规范化类型和展开引用后通过，没有据此修改数据库或原件。

## 功能、数据库与字段验收

| 层次 | 结果及证据 |
| --- | --- |
| 数据库结构 | 29 表、462 列逐列类型／可空性一致；表、列、约束、索引、RLS、触发器和函数的发布前后指纹完全一致。[字段](../../../docs/operations/evidence/current-release-20261110-01/dictionary-catalog-final.json)、[安装核验](../../../docs/operations/evidence/current-release-20261110-01/database-install-verify-final.txt) |
| JSON 合同 | 40 合同、37 枚举、44 个 Schema 定义（含 4 个共用定义）与运行合同一致。[核验](../../../docs/operations/evidence/current-release-20261110-01/json-contract-final.json) |
| 真实 GET | 两案 299 请求：291 次 200、8 次错误父归属的预期 404；13,098 项字段、正文和关联检查，0 偏差，读取前后快照一致。[汇总](../../../docs/operations/evidence/current-release-20261110-01/readback-03/summary.json) |
| 定向流程 | 81 项通过，2 项数据库专用检查跳过；复用 C1/C3 和 Deep/C6 已保存的隔离 PG 实测。[流程输出](../../../docs/operations/evidence/current-release-20261110-01/flow-tests.txt) |
| 发布 | 18 项通过，三项 profile 和实际读取权限核验通过。[测试](../../../docs/operations/evidence/current-release-20261110-01/release-tests.txt) |
| 读取接口 | 42 项不同检查最终通过；其中容量断言按显式当前策略修正后单独复验，原失败保留。[初次记录](../../../docs/operations/evidence/current-release-20261110-01/read-gate-tests.txt)、[修正复验](../../../docs/operations/evidence/current-release-20261110-01/read-gate-corrected.txt) |
| 工作台资料 | 21 静态条目 7→16，追加 9 份隔离 PG 导出；481 文件及 482 项 HTTP／字节检查通过。容器、其他条目和原件保持。[回执](../../../docs/operations/evidence/current-release-20261110-01/workbench-publication.json) |

两个正式库 Case 分别是 `2b37f5b3-862b-52cc-84bd-86db50dd3ad4`（基础 Run completed/partial、模型来源结果）和 `5942734d-1bea-5c0b-97fe-0d9ccde01858`（failed/partial、系统收尾）。测试覆盖主体、材料、分诊／诊断、成员、历史、结果、报告／图／步骤工件、当前判断、证据、活动及相关告警，未把模型正文或系统说明当独立真值。

## 交接、独立审计与发布

当前入口统一为[前后端交接指南](../../../FRONTEND_BACKEND_HANDOFF.md)，包含 F01–F28/J01–J14、数据库／JSON／HTTP 合同、字段样例、读取权限、状态和空态。整理前的入口保存到[历史索引](../../../docs/handoff/history/2026-11-10-current-handoff-cleanup.json)，原件、失败、unknown 和模型原答不改写。

未参与实施者的独立结束审计为 **ACCEPT，限本批部署、读取和字段交接范围**。复跑 21 项检查全过；独立补核两案 15 条活动、32 条目标的正文、关联、总数和分页，共 171 项通过，此数字不计入原 13,098。审计指出的正文大小、Case 预算、写入状态和路径说明已修正复查。[独审回执](../../../docs/operations/evidence/current-release-20261110-01/independent-audit.json)

Git 发布在以上步骤之后执行；先推送 `origin/V1.1`，再根据父项目远端 `add-server-submoudle` 最新提交仅更新 `server` gitlink。父项目本机分支与远端分叉，使用独立临时 Git 元数据保留其工作目录和其他提交；不使用强推覆盖远端。

本次不归档整个 change。模型质量仍为 NOT_PASSED，H 后完整真实调查、知识实际消费、自动消费者、四项原页面显示问题及未开放业务均保留在[问题清单](../../../docs/investigation/current-issues.md)，不以本批发布核销。
