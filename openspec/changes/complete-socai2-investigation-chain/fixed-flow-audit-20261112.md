# 固定流程局部程序修复独立审计

日期：2026-11-12。审查者未参与本轮实现；依据 AGENTS.md，对本轮固定流程范围作独立静态审查和已保存证据核对。仅写本文件，没有运行测试、模型、数据库、网络或部署，也没有修改原答、证据或业务代码。

**结论：本次局部程序修复限定审计通过；完整固定链路与模型质量未通过；本轮未部署。** 当前限定范围内未发现尚未修复的程序阻断。本审计不替代主 change 的整体结束审计，不具备主 change 归档结论，不核销 3.10／3.14／3.30、F02 或既有质量问题；主任务仍为 31/41。

## 范围与依据

核对了[固定流程计划](fixed-flow-plan.md)、[规格增量](specs/socai2-investigation-data/spec.md)、[实施验证](fixed-flow-validation-20261112.md)、当前 PROGRESS／交接指南／知识交接及问题清单。代码范围限于知识引用与覆盖、同出处用途筛选、A 配置输入构造、C6 建议生成约束，以及对应直接断言和必要调用链。其他未提交的图表清理、页面与部署文档工作不在本次程序审查范围。

已读批次 [fixed-investigation-20261112-01](../../../docs/operations/evidence/fixed-investigation-20261112-01/flow/plan.json) 的冻结计划、执行回执、数据库与 HTTP 导出、验证汇总、知识引用读回，以及后补的 A2／C6 离线诊断。测试执行结果采用实施验证中已记录的直接检查结果，独审只核断言与实现的对应关系，不重复执行或把各轮数量相加为新的覆盖总数。

## 程序结论与审计问题收口

1. **知识辅助引用与本案覆盖分开。** [case_source_scope.py](../../../services/api/app/socai2/case_source_scope.py) 按已选知识的查询成员与角色判断辅助适用范围；[baseline_analysis_contract.py](../../../services/api/app/socai2/baseline_analysis_contract.py) 和 [baseline_delivery_contract.py](../../../services/api/app/socai2/baseline_delivery_contract.py) 均将知识排除在成员、结论和影响的依据覆盖之外。observed／冲突仍要求直接 observation，历史分诊和人工正文没有变成本案观察。C3 局部保留复用严格解析，纠错使用相同范围与覆盖判断。
2. **用途和成员必须来自同一 origin。** [knowledge_model_input.py](../../../services/api/app/socai2/knowledge_model_input.py) 先筛本阶段目的，再从这些出处判断成员关联；没有把两个出处的不同条件拼接成一个适用条件。Deep／C6 的必要前序依赖仍从本 Run 冻结来源恢复，保留 knowledge、历史主体、角色和原 ref；保存投影继续通过 source_map 恢复原引用，未修改 A/I 告警交接字段或数据库合同。
3. **A 输入只检查实际使用的消息。** [alert_basic_contract.py](../../../services/api/app/socai2/alert_basic_contract.py) 的 render_messages 默认保持旧行为；[alert_model_boundary.py](../../../services/api/app/socai2/alert_model_boundary.py) 只在配置模板路径跳过未使用的旧 JSON 消息。原件字段 guard、单字段与准备预算、必需来源缺失拒绝及实际模板完整消息检查保持。A2 的最终离线重建为 140 来源、34,458 字节；旧模式仍拒绝，原失败 Run 保留，未再派发。此前诊断中的 150 来源／35,432 字节是定位记录，不代替最终实际 build 回执。
4. **C6 建议生成约束与原拒收语义一致。** legacy delivery_format 与 configured final_format 共用 constrain_recommendations，仅复制并收紧生成 Schema 的独立引用数组；无可用来源时禁止生成建议，避免最少一项与最多零项冲突。共享 Recommendation 仍用原 Refs，实际接收仍按 recommendation_needs_sources 拒绝空引用，合法独立分析仍可局部保留。没有新增模型纠错次数，也没有替模型补引用。

独审发现的两处问题已由实施者修正并复核：

| 发现 | 最小修正及最终状态 |
| --- | --- |
| C6 结论／影响只核覆盖，可能附带查询范围不相交的知识；纠错同样跳过该检查 | 有成员范围的知识引用现在调用 knowledge_context，无交集拒收；纠错同口径，非知识既有规则保持。组合断言包含错误成员的 C6 引用。已关闭本项程序问题。 |
| 将最少一项直接加入共享 Recommendation 会使 restore_final 提前失败，丢失原本可保留的独立分析 | 已改为仅收紧生成 Schema。现有用例同时检查空引用拒收及 FinalReview.partial 保留全员分析；本批真实 C6 原答离线复验仍拒收，并保留相同业务正文和引用。已关闭本项回归。 |

直接检查记录包含 C3／后续边界 34 项、补范围后后续边界 22 项、A 的显式 profile 检查及新增断言、C6 四项定向检查和同一用例的两个 legacy 参数检查。A 检查的初始环境错误、只读 profile 替身修正均在验证文档保留；CLI／Ruff 成功不替代业务或模型质量通过。

## 真实执行和后补修复的界限

本批有 5 个新 Run：3 个 A、1 个 I、1 个 Case。数据库快照中的 7 个 model step 合计 121,299 tokens，与执行汇总一致，费用未知。A1=1、A2=0、A3=1、I=1、Case=4；Case 的 4 次包含原 Run 内一次 C3 纠错，没有另开 Run 追求通过。

| 实际环节 | 保留结论 |
| --- | --- |
| A/I | A1 重复引用拒收；A2 被旧消息检查阻断且零模型；A3 判断保存；I 因问题成员与来源成员不符拒收。失败与独立有效片段保持原状态。 |
| C3／Deep | C3 首次覆盖拒收，纠错后保留有效片段，不能把第二个 model step 的 completed 解释成完整原答接受；Deep 完成一个问题级调用，不证明新增外部证据或问题已解决。 |
| C6／保存 | 原答第二条建议缺引用而拒收。Case Run completed，但 Result 为 partial／rejected、conclusion=null、conclusion_state=unavailable，未采用；三成员 conclusion_covered 均为 false。 |
| HTTP／知识引用 | 2 次 POST 与 3 次 GET 均为 200；结果关键字段及 questions 与数据库导出一致。历史分诊原 ref 保存在 behavior_nature 的 unresolved 问题中，角色仍为 prior_analysis，不是被采用的最终结论。 |

证据：[执行](../../../docs/operations/evidence/fixed-investigation-20261112-01/flow/execution.json)、[数据库原件](../../../docs/operations/evidence/fixed-investigation-20261112-01/flow/export/database.json)、[HTTP 回执](../../../docs/operations/evidence/fixed-investigation-20261112-01/flow/api-responses.json)、[验证汇总](../../../docs/operations/evidence/fixed-investigation-20261112-01/flow/verification.json)、[知识原引用读回](../../../docs/operations/evidence/fixed-investigation-20261112-01/flow/knowledge-readback.json)。4 份 Case 请求各含 5 个知识来源；结构化引用和保存成立，但没有证明知识促成了更具体、正确的调查判断，F02 仍未通过。

真实 Run 使用初始知识辅助引用／覆盖及同出处筛选修复。A2 旧消息修复、C6 最终知识范围检查及建议生成约束在该 Run 结束后补入，不能把原真实执行记为最终代码的完整验收。独审核对冻结计划与当前源码，以下 5 个文件有后续差异（SHA-256 前 12 位）：

| 文件 | Run 冻结 | 审计时本地 |
| --- | --- | --- |
| baseline_delivery_contract.py | 246f36556223 | d466a58cb935 |
| case_citation_feedback.py | ba358a5ad797 | 93b2ee1e51a7 |
| alert_model_boundary.py | ede71cc95ec3 | 070ace14cb473 |
| case_followup_output.py | 14c40996acb8 | d81b51daed83 |
| alert_basic_contract.py | 8e6137a40114 | 7085e039dc0b |

[A2 离线重建](../../../docs/operations/evidence/fixed-investigation-20261112-01/flow/A2-rebuilt-not-dispatched.json)及 [C6 离线接收回执](../../../docs/operations/evidence/fixed-investigation-20261112-01/flow/C6-receive-after.json)中的源码 hash 与审计时文件一致。C6 原答仍按相同原因拒收，保留业务分析正文和引用一致；程序 coverage 仅因 jsonb 字段顺序产生显示差异，逐查询事实值等价。上述是离线／直接验证，没有新增模型、重写原 Run 或追认原失败。

## 交接与未验范围

本机运行记录静态包的 audit-records 实际为 69 项，包含本批；在线 4177 未发布本批内容。当前根文档和交接已区分前批图表清理与本轮固定流程，未将本轮内容写成已部署、提交、推送或更新父项目引用。

本轮没有证明有效 A/I 加完整可采用 C6 的固定调查已通过，也没有验收模型正文合理性、知识召回／合理使用效果、生产加载、自动消费、流式更新或人工反馈后的新调查。M01-A／M01-B 与 F02、模型质量 NOT_PASSED 保持；不得用本限定审计核销主任务或触发主 change 归档。
