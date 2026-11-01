# 调查模块最新指南与审计入口

更新日期：2026-11-01。最近核实部署为 **r13**：基于b758351的未提交工作区快照，按候选包hash固定；21独立调查API实际473应用源码一致。见[真实回执](../operations/investigation-r13-report-validation-20261101.json)。

**当前结论：完整输入和真实Tool查询通过，报告质量仍失败。** A输出截断，B虽completed/partial但语义未过，C因前提不满足跳过。具体输出和来源偏差见[当前审阅指南](review-guide-20261101.md)；OpenSpec16/17，5.3保持未完成，不重复本批。

## 1 基线与验证状态

| 对象 | 最新可确认状态 | 依据 |
| --- | --- | --- |
| 常驻版本 | `socai2-investigation-api:20261101-r13`，21的`127.0.0.1:18010`；源码目录`/opt/investigation/app` | [部署核对](../operations/evidence/investigation-r13-20261101/post-install.json)、[接入说明](resident-api-20261028.md) |
| 功能修复 | A01 进程类别/版本、A02 概况失败来源模式、D01 有界 raw 材料已交付；后续含结构化报告、A 引用映射、来源标注和证据边界提示 | [实施记录](audit-fixes-implementation-20261031.md)、[来源边界](source-boundaries-20261101.md) |
| 最新受影响直接验证 | 来源值等窄修复17个不同方法最新通过，含6新增；本批复用，业务测试重跑0，五项源码/测试指纹未变 | [直接验证回执](../operations/investigation-report-grounding-20261101.json) |
| 最新真实调查 | A failed/partial，B completed/partial但语义未过；6模型、4真实查询、0复用、20,334tokens；6调用未定价，C跳过 | [r13回执](../operations/investigation-r13-report-validation-20261101.json)、[分析](../operations/evidence/investigation-r13-20261101/review.md) |
| 原始材料与查询 | A raw371/425B、B raw219/251B，各在3轮输入完整；A查询1/1行、B查询0/0行，全部QueryFinish成功 | [输入核验](../operations/evidence/investigation-r13-20261101/verification.json)、[查询日志](../operations/evidence/investigation-r13-20261101/query-and-cost-proof.json) |
| 报告状态 | A输出3000tokens后截断，未触发纠错；B有效JSON及引用通过，但空查询反证化、未提供审批变无审批、Tool编号错误仍在 | [逐问题分析](../operations/evidence/investigation-r13-20261101/review.md)、[问题清单](review-guide-20261101.md#当前问题登记) |
| OpenSpec | 当前审计 change 16/17，旧追加 change 5/5；严格校验通过不代表完整报告验收通过 | [任务](../../openspec/changes/fix-investigation-audit-gaps/tasks.md)、[验证记录](../../openspec/changes/fix-investigation-audit-gaps/execution-validation.md) |

历史r11样本由用户选择新增并明确标记synthetic；r12/r13 A复用其原Case与两条告警/湖事件，B复用r10完整raw Case，没有新增源数据。真实API/模型/查询指系统调用实际发生，不证明示例中的端点行为或真实攻击发生。这些批次均已结束，不重试挑选结果。

## 2 当前功能范围

| 功能 | 实现与已验证范围 | 仍需区分的边界 |
| --- | --- | --- |
| F1 事件成员与分诊汇总 | 读取 canonical 成员、已存分诊和当前处置；真实 HTTP 已覆盖 | 成员状态不自动决定事件关闭 |
| F2 AI 概况 | 首次任务代码、手动刷新、失败保旧文、变化标旧；手动引用 Case 报告已真实联调 | 首次 worker 未启用；普通 GET 不生成概况，新 Run 不自动改写旧文 |
| F4 成员转 Case | 告警/事件创建或关联 Case、读取关联及历史；真实 PG/HTTP 已覆盖 | 建案成功不代表调查已执行；F5/自动建案政策仍未纳入 |
| F3 Case 调查 | 预览、原生 Tool、完整 raw、结构化报告、步骤/证据/报告读回及追加已有真实证据 | r13 A输出截断，B completed但内容偏差；结构、查询成功和语义质量分别判断 |
| 多成员与公共读取 | 成员覆盖、关系、时间线、未决问题、executions 及来源行导航已有实现 | 引用合法不证明文字有依据；时间线的同主机候选成员不等于精确来源 ID 对应 |
| 产品主机 Tool | `product_host_details` 已实现来源绑定和 CrowdStrike 当前快照，替身通过 | 真实厂商 HTTP 及模型使用未验；当前快照不证明历史状态 |
| 追加及指定查询 | `required_tools`、`refresh_queries`、H1 历史保留和适用查询复用已实现，相关真实批次有证据 | 指定 Tool 尝试可由复用满足；实际重新查询须核 query_id 和数据库执行记录 |

调查统一在 Case；Incident 保留汇总、AI 概况及结果关联。F5、专项 Deep/动态 MCP 的完整接入、首次 worker、真实厂商动作、JWT/RBAC 专项及旧 OpenSpec 2.2/2.3 不由当前结果核销。

## 3 业务调用顺序

公开前缀为 `/api/v2/investigation`。完整字段与错误见 [接口合同](interface-contracts-20261027.md)。以下是使用说明，本轮文档更新不执行调用。

1. 读取告警/事件来源，明确要调查的成员，区分 Alert、Incident、Case、Run ID。
2. `POST /case-links` 创建或关联 Case；后续显式传回执的 `selected_member_ids`，避免扩大到已有 Case 的其他成员。
3. 可选 `POST /cases/{case_id}/investigation-context` 预览材料和可用 Tool；实际启动仍重新读取并固定范围。
4. `POST /cases/{case_id}/investigate` 使用新 `operation_key`、绝对窗口、问题和选定成员，在请求内完成调查并保存。
5. 沿返回链接 GET 读取报告、步骤、证据和来源行；这些读取不重新调用模型或查询来源。
6. 追加使用新 key 和 `previous_run_id`，成员集合/窗口须与前次相同，旧报告保留。
7. 按需单独刷新事件概况并传 `include_investigations=true`，引用已有 Case 报告摘要；不等于再发深入调查。

`required_tools` 要求尝试指定工具，参数由模型在 schema 中生成。`refresh_queries=true` 禁止历史复用，但单独使用不保证模型调用 Tool。需要本次查库时同时使用两者，并检查实际执行证据。最多两轮查询决策后进入 Schema 约束报告，必要时一次纠错；总计最多 4 模型、4 数据 Tool、24,000 tokens，每次输出最多 3,000，调查循环 120 秒。`finish_analysis` 为本地结束查询信号，不查询数据。

模型报告使用当前 `alert_ref/alert_refs`（A 编号），公开结果映射为 `alert_id/alert_ids`（UUID）。校验包括结构、引用、成员完整性、明确PID/账号的来源值及有限协议/空查询原因措辞，不是通用语义判断。HTTP 200、`completed`、`partial`、JSON 合法、报告有据各自表达不同含义。

## 4 推荐阅读顺序

| 顺序 | 材料 | 用途 |
| --- | --- | --- |
| 1 | [当前审阅指南](review-guide-20261101.md) | 固定本次基线、当前问题和最短证据阅读路径 |
| 2 | [设计对齐](current-design-alignment-20261027.md)、[接口合同](interface-contracts-20261027.md) | 职责、调用、模型和 Tool 数据合同 |
| 3 | [r13实际复验原因](../operations/evidence/investigation-r13-20261101/review.md) | 同看完整输入、真实查询、A残稿和B保存报告 |
| 4 | [r10 空查询记录](../operations/evidence/investigation-audit-fixes-20261031/live-r10/review.md)、[来源核对](source-boundaries-20261101.md) | 区分旧空结果问题与 r11 非空正向样本 |
| 5 | [当前 OpenSpec 任务](../../openspec/changes/fix-investigation-audit-gaps/tasks.md)、[原结束审阅](../../openspec/changes/fix-investigation-audit-gaps/audit.md) | 原审阅仅覆盖 r3 本地交付，不能当作 r13 语义验收 |
| 6 | [证据目录](evidence-catalog-20261027.md) | 查找历史版本、冻结请求、失败及原始响应 |

## 5 审阅方法与当前安排

先固定发布版本和真实批次，再沿材料→模型请求→Tool SQL/结果→首份报告→校验反馈→纠错原答→最终保存结果检查。具体字段、文件及问题编号见 [审阅步骤](review-guide-20261101.md#审阅顺序)。已有且未变化的直接验证继续复用，不增加恢复、压力、权限专项或逐层审阅门。

用户继续后已更新独立API并完成r13 A/B固定复验，原失败和未验范围保留；本批业务测试重跑0。下一聚焦报告截断的既有一次纠错处理、空查询不构成反证、未提供不等于不存在及Tool编号一致性，使用本批反例做必要直接验证，不新增Case记忆或通用语义框架。不能只放宽规则、提高预算或循环调用来取得通过报告；新版本复验另固定范围。

## 6 历史验证索引

| 批次 | 原有结论与限制 |
| --- | --- |
| [r10](../operations/investigation-structured-report-20261031.json) | 完整 demo raw、2 次真实空查询；首次结构通过，但把空结果当反证并猜原因。r11 非空样本没有验证该推理缺陷已解决 |
| [r9](../operations/investigation-model-wait-20261031.json) | 调查等待边界修复；真实首答 JSON 无效、纠错重复 UUID，failed/partial；未实际覆盖单次超过 45 秒等待 |
| [r6–r8](../operations/investigation-protocol-uncertainty-20261031.json) | 协议/覆盖/来源标注逐步交付；各批失败、复用、未知用量及语义边界按原回执保留 |
| [r4/r5](../operations/investigation-functional-followup-20261031.json) | 预算、追加与复用功能通过，报告质量部分失败 |
| [r1 四案例](multi-case-http-20261028.md) | 207 HTTP、111 检查、3 失败、2/4 自动流程通过；不是最新线上版本 |

## 7 文件与证据核对（指南对齐阶段历史记录）


对齐前只读检查覆盖37份调查Markdown中的1041个本地文件链接，目标文件均存在（API资源地址不作本地文件处理）。四案例207份响应SHA256、请求元数据与汇总统计一致；冻结的脚本、输入和批次启动脚本3份哈希一致。这些是已有文件完整性检查，不是重新执行测试。

指南初次对齐时，最近部署回执的475份文件中，470份与当时工作区一致，5份已变化：Case执行器、模型协议、Tool模型视图、Compose、安装脚本。这与r1真实测试、r2本地准备的版本边界相符。当前测试脚本/清单也已增加必需Tool参数，阅读历史结果时应使用[当批冻结脚本](../operations/evidence/INVHTTP-20261028-01/investigation_http_cases.py)和[当批输入](../operations/evidence/INVHTTP-20261028-01/cases.json)。

对齐后，38份调查Markdown的1158个本地文件链接均能找到目标，文档内锚点静态检查无缺失。仅文档发生变化，业务源码、测试源码、机器回执和当批冻结原件保持；本次没有新增测试通过项。
