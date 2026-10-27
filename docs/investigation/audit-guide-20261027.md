# 调查模块详细审计导航

2026-10-27，核对基线：`6044615`，分支`codex/investigation-review-20261024`。本文组织现有文档、补充当前实现说明，供详细审计使用。本轮只做源码/文档静态核对和链接检查，没有运行业务测试、模型、数据库、任务或部署；不是新一轮独立代码验收结论。

## 1. 先确认审计对象

用户最新确定：**Fusion Incident只保留事件汇总和AI概况，深入调查在Case中进行。** 不新增Incident调查profile或另一套事件调查循环。

当前仓库中有几条不同路径，不能把它们的设计、测试数量和真实环境证据互相替代：

| 对象/路径 | 当前代码与状态 | 审计应使用的说明 |
| --- | --- | --- |
| F1/F2事件层 | API v2事件成员/分诊读取、概况保存/刷新及独立首次任务；替身直接验证，新表迁移120/任务未启用 | [当前实现详解](current-implementation-reference-20261027.md)、[F2接入说明](incident-ai-overview.md) |
| F3 Case调查 | API v2直接执行模型—进程/网络查询循环，使用既有ledger；4项替身直接验证，真实模型/PG/CH未验 | [当前实现详解](current-implementation-reference-20261027.md)、[Case调用说明](case-investigation.md) |
| fixed/program有限核对 | API网关→Agents v2、版本化状态/预留/发布/owned读取；有各自限定合同及真实接缝 | [主设计](../architecture/investigation-planning-design.md)、[历史实施记录](../operations/unified-investigation-implementation.md)、[证据目录](evidence-catalog-20261027.md) |
| 原有Agents调查 | 原graph、Router、Deep、领域角色、客户产品工具/MCP；不能据源码存在认定已接入F3 | [旧路径逐步调用](../architecture/investigation.md)、[工具目录](../architecture/investigation-tool-catalog.md) |

F3的`case_analysis.v1`没有沿用旧fixed/program的closed manifest、M3预留状态机或owned结果读者。其身份/预算/工件行为应按F3代码核对；旧路径的真实PG/HTTP/CH回执不证明F3已通过相同接缝。

## 2. 建议阅读顺序与完整入口

先审当前设计时，从[当前设计对齐](current-design-alignment-20261027.md)开始：包含职责、自动/手动触发、流程图、实际能力边界与例子；下表再用于对照代码和历史依据。

用户要求进一步细化到接口，新增[接口设计](interface-contracts-20261027.md)，覆盖事件/概况、成员转Case、Case调查/历史、内部自动入口、Tool及产品HTTP映射。拟新增接口均是设计稿，未修改业务实现或因此增加完成项。

| 顺序 | 文档 | 用途和适用范围 |
| --- | --- | --- |
| 1 | [当前实现详解与API/数据合同](current-implementation-reference-20261027.md) | 本次补充；集中描述F1–F3实际入口、每步输入输出、持久化、状态、限制及待审计差异 |
| 2 | [调查主设计](../architecture/investigation-planning-design.md) | 总体问题/材料/分析/执行设计与历史规划；第0节及最新Case边界优先，历史“下一步”按原日期解释 |
| 3 | [告警—事件—Case业务流程图](../architecture/incident-investigation-flow-20261025.md) | 目标业务流程、自动/手动、跳转和例子；图中F4/F5连接不等于已经实现 |
| 4 | [实施原则](../architecture/investigation-planning-design.md#implementation-principles)与[当前功能计划](incident-investigation-implementation-plan-20261025.md) | 功能逐个直接验证；F1/F2、F3第一版已有代码，F4/F5未交付 |
| 5 | [Case调查接口与直接验证](case-investigation.md) | F3的可调用接口、工具范围、报告及替身验证边界 |
| 6 | [事件AI概况接口与任务](incident-ai-overview.md) | F2迁移、生成、读取、手动刷新、首次任务、范围和失败保留 |
| 7 | [新增Tool接入与全流程验证](tool-onboarding-and-flow-verification.md) | 从产品HTTP契约到模型发现/调用/回传/采用的接入方法；真实模型验证与脚本替身须区分 |
| 8 | [证据与历史文档全目录](evidence-catalog-20261027.md) | 按路径提供全部相关回执、失败原件、历史审计、场景和OpenSpec文档链接 |

## 3. 核对需求、代码、证据时的对应关系

| 审计问题 | 主要代码 | 当前证据能证明什么 |
| --- | --- | --- |
| Incident成员从哪来、是不是canonical Alert | [incident_reader](../../services/api/app/investigation_v2/incident_reader.py) | F1接口/SQL替身直接用例；PG真实读取兼容性不由这些用例证明 |
| 所有分诊结果是否汇入事件、是否混用Case ID | 同上，查询`triage_verdict`及`Run.raw_alert.id` | [F1直接用例](../../services/api/tests/test_investigation_incident_api.py)；不把普通AI文本当作已保存分诊 |
| 概况何时更新、失败会不会清空旧文 | [incident_summary](../../services/api/app/investigation_v2/incident_summary.py)、[worker](../../services/api/app/investigation_v2/incident_summary_worker.py) | [F2直接用例](../../services/api/tests/test_investigation_incident_summary.py)，与F1相关4项合计8项；不是12项互不重复的验证 |
| Case成员/窗口如何固定，谁实际执行 | [case_analysis](../../services/api/app/investigation_v2/case_analysis.py)、[Case路由](../../services/api/app/investigation_v2/case_analysis_api.py) | [F3直接用例](../../services/api/tests/test_case_analysis_api.py)；当前执行位置为API v2进程 |
| 模型是否真的收到Tool定义和ToolMessage | [模型协议](../../services/api/app/investigation_v2/case_analysis_models.py)、[Case工具](../../services/api/app/investigation_v2/case_analysis_tools.py) | 替身用例覆盖HTTP消息字段/参数/回传；不证明真实模型自主选对或业务判断正确 |
| 工件、报告、状态怎样落库和读回 | [case_analysis](../../services/api/app/investigation_v2/case_analysis.py)、[ledger模型](../../services/api/app/models/investigation.py) | F3替身保存/读回；不是旧M7 manifest/owned校验已复用的证明 |
| 真实查询和真实PG证据在哪 | [M6.2c回执](../operations/investigation-fixed-runtime-seam-20261024.json)、[M7c回执](../operations/investigation-publication-pg-seam-20261024.json)、[M8 PG准入回执](../operations/investigation-program-admission-pg-20261025.json) | 分别只证明fixed一次真实查询、原Run发布冷读、program零工具/模型准入；范围见各自`limits` |

F1–F3现有直接测试结果来自2026-10-25实施记录。本次没有重跑，未将它们改写成2026-10-27新测试或新的真实环境证据。F3有4项，F1/F2相关集合有8项，最多描述为两套共12项不同用例；不能将历史“F1 4 + F2集合8”再相加为12。

## 4. 当前已知未交付项

- F4：告警/Incident选择成员后创建或关联Case的新v2入口，尚未实现。原有v1 Case创建/加成员接口存在，不等于F4已接通。
- F5：原自动分诊/升级政策接入新Case内核，尚未实现。分诊worker已有旧升级分支；不能据其存在说新版Case自动调查已启用。
- F3真实模型自主选工具、结果解释及业务质量，真实PG/CH完整链路均未验证。
- 产品HTTP Tool、动态客户/MCP能力和专项Deep/领域角色没有全部接入F3。F3目前只有两个Case事件湖工具。
- 新表迁移120、事件首次概况任务和新v2应用尚未部署/启用；权限专项继续暂停。
- OpenSpec任务2.2/2.3仍未核销；F3替身功能用例不能把历史整项标完成。

## 5. 文档补全及需特别审计的内容

本次新增了当前实现详解和完整证据目录，并补正几处旧说明：F2不因F3实现就自动拿到Case结果；Tool目录必须区分旧Agents注册与新Case组装；Case复用只检查当前来源指纹，不主动探测后端数据/模型版本变化；120秒只覆盖主循环；读回与证据引用校验各有具体边界。

细节及源码定位见[当前实现详解第8节](current-implementation-reference-20261027.md#review-boundaries)。这些是供审计判断的事实与待核点，本轮没有修改业务代码，也没有添加审计门、权限测试或恢复测试。
