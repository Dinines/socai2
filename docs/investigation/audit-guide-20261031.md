# 调查模块最新指南与审计入口

更新日期：2026-10-31。当前线上r5，业务源码`3324fea`，21本机18010；472应用源码hash已核。调查统一在Case，事件负责汇总和概况。

[最新功能复验回执](../operations/investigation-functional-followup-20261031.json)：r4/r5的6个真实Run均completed/partial，纠错预算、要求的Tool调用、复用和历史读回已验证。Office新报告去除了PWS/NavVisor无源标签；网络仍有TCP/443误写HTTPS、漏逐成员判断和closed状态解释偏强的问题，完整报告语义验收未过。

**详细审计已完成：** [设计—实现—测试证据完整报告](design-implementation-audit-20261031.md)。静态核对确认两项功能缺陷：进程Tool未按事件类别筛选、失败保旧Case概况时来源模式与权限/提交顺序不一致；另有告警正文未进入Case材料的设计缺口。文档输出上限及主设计现行提示已校正；后续用户要求推进执行，三项业务问题已[实现并验证](audit-fixes-implementation-20261031.md)，之后的r3失败、r4流程通过与r5质量局限分别保留。范围、文件哈希、路由和既有证据核对见[机器清单](../operations/investigation-static-audit-20261031.json)。

## 1 基线与验证状态

审计后实施顺序已落入 [OpenSpec提案](../../openspec/changes/fix-investigation-audit-gaps/proposal.md)、[详细设计](../../openspec/changes/fix-investigation-audit-gaps/design.md)和[任务表](../../openspec/changes/fix-investigation-audit-gaps/tasks.md)：先修进程类型及概况失败路径，再补原始材料，最后组合验证已有追加修复。r3原实现及一次[独立复审](../../openspec/changes/fix-investigation-audit-gaps/audit.md)之后，r4/r5完成受影响功能验证；当前审计change16/17、旧追加change5/5，完整报告质量与归档条件仍待。未新增逐层审计门或测试框架。

| 对象 | 最新可确认状态 | 依据 |
| --- | --- | --- |
| 当前代码与测试源码 | `3324fea`，含A01/A02/D01、紧凑纠错及来源陈述修正；实际线上r5 | [修复设计](../../openspec/changes/fix-case-followup-gaps/design.md)、[测试源码](../../services/api/tests/test_case_analysis_api.py) |
| 最新本地直接验证 | 最新提示词6项受影响用例通过；其余复用既有验证，冻结重放不是新真实模型 | [最新日志](../operations/evidence/investigation-audit-fixes-20261031/live-r5/direct-tests.txt) |
| 最近真实四案例测试 | 源码`512c004`，批次`INVHTTP-20261028-01`；207次HTTP、111项检查、3项失败，2/4案例自动流程通过 | [总报告](multi-case-http-20261028.md)、[机器汇总](../operations/investigation-multi-case-summary-20261028.json) |
| 最新常驻版本与真实验证 | 20261031-r5；r4/r5共6 Run完成partial，16模型/2新湖查询/4复用；质量局限如上 | [实际回执](../operations/investigation-functional-followup-20261031.json) |
| 数据库功能表 | 迁移120/121已在10月28日记录安装，登记134→136 | [事件转Case联调](incident-case-basic-flow-20261028.md) |
| 文档更新 | 10月29日补充四案例业务解释；10月31日对齐当前入口和接口合同 | [文档目录](evidence-catalog-20261027.md) |

文件名含20261028的本地修复回执随10月29日提交保存，不能仅凭文件名判断先后。6项通过是已有验证记录，额度重建没有新模型调用。本轮已通过SSH核实r5在线状态及批次结束后账本；旧四案例行仍保留历史结果。工作区原有未提交文档修改继续保留。

## 2 当前功能范围

| 功能 | 实现与已验证范围 | 仍需区分的边界 |
| --- | --- | --- |
| F1 事件成员与分诊汇总 | 读取canonical成员、已存分诊和当前处置；真实HTTP覆盖 | 成员状态不自动决定事件关闭 |
| F2 AI概况 | 首次任务代码、手动刷新、失败保旧文、变化标旧；手动引用Case报告已真实联调 | 首次worker未启用；普通GET不生成概况，新Run不自动改写旧文 |
| F4 成员转Case | 从告警或事件创建/关联Case、读取关联和历史；真实PG及HTTP覆盖 | 建案成功不代表调查已执行；自动建案政策/F5不在当前目标 |
| F3 Case调查 | 预览、主分析、按需Tool查询、步骤与证据、报告下载、历史及追加问题已有代码；主流程有真实PG/模型/事件湖/HTTP证据 | 旧r1四案例主调查completed/partial；r3曾2 failed/partial；后续r4/r5六Run completed/partial，报告质量仍有限 |
| 多成员与公共读取 | 成员覆盖、关系、时间线、未决问题、executions及证据/来源行导航已有代码及真实案例读取 | 编号合法不等于结论语义正确，未选成员不能计入Run覆盖 |
| 产品主机Tool | `product_host_details`已接通来源连接器和CrowdStrike主机快照，替身验证通过 | 真实厂商账号/HTTP与模型使用该Tool未验证；当前快照不证明历史状态 |
| 最新追加修复 | `required_tools`、精简模型材料和`query_status`已在本地实现并做受影响直接验证 | r4/r5已真实覆盖追加、指定Tool及复用；语义质量仍未完整通过 |

F5、自动目标政策、专项Deep/动态MCP的完整接入、真实厂商动作及用户JWT/RBAC专项均不由上述结果证明。旧fixed/program的真实回执只解释各自路径，不能替代Case证据；旧OpenSpec 2.2/2.3仍按其原范围保留未完成。

## 3 业务调用顺序

公开前缀为`/api/v2/investigation`。字段、错误和JSON示例见[接口合同](interface-contracts-20261027.md)；服务访问方式见[常驻入口](resident-api-20261028.md)。

1. **读取来源。** 查看事件汇总、告警调查上下文，明确要调查的成员；Alert、Incident、Case、Run ID分别使用。
2. **创建或关联Case。** `POST /case-links`完成成员组织。后续调查明确传回执中的`selected_member_ids`，避免把目标Case的其他成员意外纳入。
3. **可选材料预览。** `POST /cases/{case_id}/investigation-context`返回范围、材料和可用Tool；实际启动会重新读取并固定本次范围。
4. **发起一次调查。** `POST /cases/{case_id}/investigate`携带新`operation_key`、窗口、问题及选定成员。程序在本次请求内完成模型和Tool循环，保存步骤与报告。
5. **阅读与追溯。** 沿结果链接读取Markdown、步骤、证据和来源行；这些GET查看已保存内容，不重新查询。告警/事件/Case的executions筛选可定位同一Run。
6. **按需追加问题。** 新key和`previous_run_id`创建新Run；成员集合与窗口须和前次相同，旧报告保留。`refresh_queries=true`禁止历史查询复用；它本身不要求模型一定调用Tool。
7. **按需刷新事件概况。** 手动`overview/refresh?include_investigations=true`引用已有Case报告摘要；这是单独的摘要调用，不重新深入调查。

最新本地合同允许在第4或第6步传`required_tools:["network_connections"]`，要求结论形成前尝试该工具；参数仍由模型在当前Tool schema内生成。允许复用时，命中已有查询也算一次工具尝试；失败/不可用结果不因此变成成功证据。若同时需要实际重新查询，使用`refresh_queries=true`。该字段不属于材料预览接口；当前r5已支持，旧r1不支持。

## 4 推荐阅读顺序

| 顺序 | 材料 | 用途 |
| --- | --- | --- |
| 1 | [当前设计对齐](current-design-alignment-20261027.md) | 职责、触发和功能连接 |
| 2 | [接口合同](interface-contracts-20261027.md)、[Case流程示例](case-first-version-20261028.md) | 请求、返回、模型/Tool协议与追加行为 |
| 3 | [四案例总报告](multi-case-http-20261028.md)及其四份逐步记录 | 看业务动作如何进入实际模型、查询及读回步骤 |
| 4 | [最新修复设计](../../openspec/changes/fix-case-followup-gaps/design.md)、[待办](../../openspec/changes/fix-case-followup-gaps/tasks.md) | 区分原失败、本地修复及待真实复验 |
| 5 | [常驻服务记录](resident-api-20261028.md)、[事件与Case联调](incident-case-basic-flow-20261028.md) | 最近保存的部署和迁移状态 |
| 6 | [证据目录](evidence-catalog-20261027.md) | 当前材料、冻结脚本/输入、原始响应和旧路径历史 |

[10月27日审计导航](audit-guide-20261027.md)和[10月27日实现详解](current-implementation-reference-20261027.md)保留原基线说明，不能直接用于判断最新功能是否交付。

## 5 完整审计步骤

1. 固定本地提交与工作区差异，另列部署镜像、源码清单和迁移回执；不把本地代码当作已运行版本。
2. 按第2节功能清单建立需求—接口—代码—证据对应表，标明已实现、替身已验、真实已验、失败和未覆盖。
3. 核对路由注册、参数/错误、租户与对象归属、选定成员、窗口、重复请求及只读接口行为。
4. 沿材料→模型→Tool→回传→结论检查实际输入输出，核对必需Tool、来源绑定、预算和停止原因。
5. 核对Run、步骤、完整证据与报告的保存读回，追加历史和查询复用条件，以及未选成员不被错误归属。
6. 对照材料审阅成员判断、关系和报告文字，特别检查T编号、主机身份、空结果/失败及来源覆盖含义。
7. 用当批冻结脚本、输入、响应和哈希核对测试结论；成功HTTP、结构检查和业务质量分别判断。
8. 将最新本地改动映射到原失败步骤，列出必要复验；已通过且未变化的功能复用原证据。
9. 输出基线、功能对照、分级发现、证据链接及最小后续清单，保留失败与未覆盖项。

## 6 已知缺口与后续验证

| 原问题 | 本地处理 | 剩余验证 |
| --- | --- | --- |
| Office长历史追加纠错超过输入额度 | 新原始来源保留；H1明细从模型视图显式省略，完整历史不改；当前实际替身请求16929≤17018 | 修复版本下对应追加步骤的真实模型结果与读回 |
| 网络追加没有发出所要求的Tool调用 | 显式`required_tools`及原生`tool_choice`；直接用例覆盖调用、复用及拒绝静默跳过 | 真实模型发出要求的调用并进入复用分支 |
| LSASS摘要混淆T编号、空结果/失败；网络追加误称主机 | 明确提示词语义，Tool模型视图增加`query_status` | 对照实际新输出做内容审阅；不能仅凭提示词变化核销 |
| 现有showcase缺规范化进程遥测、产品Tool未真实调用 | 保留现有数据和覆盖限制 | 需要相应来源接入后才能评估行为关联或厂商Tool质量 |

后续真实复验的具体服务更新、最多5个新Run及回退方案已列入[实施记录](audit-fixes-implementation-20261031.md)；本次已做本地实现/必要测试，未部署、修改凭据/权限、真实调用、推送或合并。首次worker与自动政策继续保持各自范围。

## 7 文件与证据核对（指南对齐阶段记录）

对齐前只读检查覆盖37份调查Markdown中的1041个本地文件链接，目标文件均存在（API资源地址不作本地文件处理）。四案例207份响应SHA256、请求元数据与汇总统计一致；冻结的脚本、输入和批次启动脚本3份哈希一致。这些是已有文件完整性检查，不是重新执行测试。

指南初次对齐时，最近部署回执的475份文件中，470份与当时工作区一致，5份已变化：Case执行器、模型协议、Tool模型视图、Compose、安装脚本。这与r1真实测试、r2本地准备的版本边界相符。当前测试脚本/清单也已增加必需Tool参数，阅读历史结果时应使用[当批冻结脚本](../operations/evidence/INVHTTP-20261028-01/investigation_http_cases.py)和[当批输入](../operations/evidence/INVHTTP-20261028-01/cases.json)。

对齐后，38份调查Markdown的1158个本地文件链接均能找到目标，文档内锚点静态检查无缺失。仅文档发生变化，业务源码、测试源码、机器回执和当批冻结原件保持；本次没有新增测试通过项。
