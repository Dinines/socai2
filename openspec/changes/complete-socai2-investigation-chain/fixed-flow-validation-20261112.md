# 固定 A/I → Case 本轮实施与验证

2026-11-12，限定于[固定流程计划](fixed-flow-plan.md)的输入、知识交接、综合结论合同和保存读取；未做流式更新、队列、人工反馈重算或部署。主 change 仍未整体验收，不归档、不核销 3.10/3.14/3.30、F02 或模型质量。

## 实际缺口与修正

1. C3 允许有归因的历史比较，但接收器曾将 `alert_ids=[]` 的知识引用一律判为成员错位。现在已选知识可按 `query_alert_ids` 作辅助解释/推理/补查参考；原历史主体与角色保留，所有知识都不计入本案成员依据覆盖。C3/C6 接收、局部保留和一次纠错采用同一规则，observed/冲突仍要求本案直接观察。
2. 合并后的知识曾分别检查“有某目的”和“有某成员”，错误组合不同查询出处。现在目的与成员必须来自同一个 origin；前序确实引用的必要依赖继续保留。独审另发现 C6 结论/影响未检查知识适用成员，已补齐，其他非知识引用的既有规则保持。
3. A2 在发送模型前被未使用的旧 JSON 消息阻断。原来源合格，旧消息 73,726 字符触发 60,000 字符限制；实际配置模板重建为 34,458 字节、140 来源。来源构造与旧消息渲染现在分开：配置路径仅构造来源，再检查实际模板；旧模式、原字段检查、准备上限及实际消息 guard 都保持。未提高阈值或裁正文。
4. C6 建议的生成 Schema 允许空 `source_ids`，但原接收器要求有来源。已在生成 Schema 加最少一项约束并保持非回执枚举，不增加纠错次数、不补引用或改写旧失败。独审指出共享接收类型加限制会破坏 partial；已将限制仅保留在新/旧生成层，原接收语义和独立有效分析保留不变。

以上均为内部输入/生成/接收修复；无数据库迁移，A/I 对外字段、告警材料及关联合同保持。`case-input-v1.json` 的内容 hash 随提示修正变化，新 Run 选择新内容，旧冻结配置和原答不回写。

## 直接检查

- 修复前、扩展 A2 范围和补 C6 生成约束前分别执行主 change 严格校验通过。
- C3/后续边界两个模块 34 项通过；补 C6 适用范围后，后续边界 22 项通过。
- A 模块先因未显式指定 profile 出现 10 项环境错误；显式设置 `SOCAI2_INVESTIGATION_POLICY=.../investigation-policy-ai-v1.toml` 后 9 项通过。新断言起初修改了只读 profile 的临时副本，改为显式替身 profile 后该项通过；业务实现不靠修改配置阈值通过。
- C6 最少引用的生成/接收、原正常最终输出、纠错/部分保留与非回执约束定向检查通过。原正常/空引用的 legacy 生成约束另在原两参数用例通过；本批实际 C6 原答[离线复验](../../../docs/operations/evidence/fixed-investigation-20261112-01/flow/C6-receive-after.json)仍拒收且保留相同业务分析，程序 coverage 仅有 jsonb 字段显示顺序差异、事实值等价。未跑全仓回归、压力/恢复矩阵或多模型比较。
- 受影响业务代码/测试 Ruff、`git diff --check` 通过。旧文件换行提示不是本轮代码错误。
- [离线重建及读回断言](../../../docs/operations/evidence/fixed-investigation-20261112-01/verify.py)成功；A2 旧模式仍拒绝，实际模板可生成，原失败 Run 未重派。

## 01批真实固定流程

[批次配置/驱动](../../../docs/operations/evidence/fixed-investigation-20261112-01/config.json)复用 C02 三条原材料并分配新身份，固定成员、事件关系和时间窗口。现有本机有效 A/I 候选均为替身历史，故本批按服务入口各做一次 A，再做一次 I，然后按原 HTTP 创建/启动一个 Case。仅认证和模型 SSH 传输适配；数据库、C2、服务执行、保存和 GET 都是真实路径。知识沿既有索引查询，没有再导入/索引历史卡，也没有自动消费或真实厂商查询。

[原执行记录](../../../docs/operations/evidence/fixed-investigation-20261112-01/flow/execution.json)：共 7 次真实模型，121,299 tokens，费用未知。A1=1、A2=0、A3=1、I=1、Case=4；Case 沿本 Run 原有一次纠错，未另开 Run。处理标签 A1/A2/A3 按驱动顺序，不等同每个模型输入按成员排序后的短号。

| 环节 | 实际结果 | 解释 |
| --- | --- | --- |
| 登录告警 A | failed / alert_answer_source_invalid | 模型重复引用；正文由 synthetic 标签推环境的已知质量问题保留 |
| 网络告警 A | failed / alert_model_view_unavailable，零模型 | 上述旧消息检查阻断；修后只用同一冻结材料离线重建，不改旧结果 |
| 进程告警 A | completed | 判断保存；不能推广为所有 A 已通过 |
| I | failed / incident_source_wrong_member | 待核问题声明模型短号 A2/A3，却引用 A1 的 hostname/user。独立有效内容按原 partial 规则保留，整体失败不追认 |
| C1/C2 | 3 告警/1 事件冻结；知识 5 行 | 当前 A/I 的实际可用/失败状态进入冻结材料；失败诊断未冒充可用前序 |
| C3 | 首次 coverage 拒收，纠错后 partial | 知识不代替成员覆盖，独立有效问题中有历史分诊引用 |
| Deep | completed | 原适用问题路径执行；不因此宣称新增外部证据 |
| C6 | recommendation_needs_sources 拒收 | 第二条建议缺少依据。生成约束随后补齐；本原答保持失败，未重派 |
| 保存/读取 | Run completed；Result partial/rejected；conclusion=null；未采用 | 数据库、结果 GET、Case GET 对缺失结论含义一致 |

[验证汇总](../../../docs/operations/evidence/fixed-investigation-20261112-01/flow/verification.json)与[知识读回](../../../docs/operations/evidence/fixed-investigation-20261112-01/flow/knowledge-readback.json)证明：4 份 Case 请求各含 5 个知识来源；C3/C6 的行为性质问题引用历史分诊，C6 独立保留的问题保存了同一知识工件 `$.rows.4.record.triage` 的 `prior_analysis` 原引用，GET 正文和引用与库中一致。输入存在、结构化引用、独立保留与全局结论接受分开统计。该问题仍是泛化的缺口表述，未证明知识推动了更具体的调查或合理定性，F02 保持未通过。

本次直接流程证明了失败、局部结果及知识原引用的保存读取；**没有证明一条有效 A/I 加完整可采用 C6 的固定流程已通过**。M01-A/M01-B 按既有决定后置；本批时间差“22秒”等正文错误保持原件，不靠重复采样改结论。

## 02–04批续修与真实边界

本地另补 A/I 同 Run 最多一次引用纠正及 C6 空建议/成员依据的具体反馈；不重派旧 Run，不增加总 token 或 deadline。A/I ai-v1/case-v1 profile 允许最多两次调用，纠正仍需满足预算。输入修复先合并同回执同版本的重复历史展示，后将 Case 消息检查改为实际文本；完整原件与旧失败保持。

| 批次 | 实际执行 | 真实模型 / tokens | 保存读取边界 |
| --- | --- | --- | --- |
| [02](../../../docs/operations/evidence/fixed-investigation-20261112-02/flow/readback-verification.json) | 登录 A 两次引用仍失败；网络 A 有效采用；I 预算不足、C3 输入超限均零派发 | 3 / 21,474 | Case system_only/partial；A/I 和 Case 数据库与GET一致 |
| [03](../../../docs/operations/evidence/fixed-investigation-20261112-03/flow/readback-verification.json) | I 一次成员引用错误，剩余预算不足以纠正；C3 两次后接受；C6超限零调用 | 3 / 78,610 | 保留I partial及系统收尾，数据库与GET一致 |
| [04](../../../docs/operations/evidence/fixed-investigation-20261112-04/flow/readback-verification.json) | 沿用 A/I；C3及两项Deep各一次；完整C6仍超限，零调用 | 3 / 71,059 | 当前判断为系统收尾，不是可采用模型结论；数据库与GET一致 |

03批早期离线脚本曾按 schema 误取领域分析工件，漏带C3；其58,170字符不是完整实际C6。改为按实际C3步骤的 output_artifact_id 取件后，03/04完整C6分别为63,036/63,262字符，确实超过原60,000限制。旧错误诊断工件保留，不作为验收。随后同值材料/共同限制共享展示的04离线输入为58,540字符，未再次发送模型。

当前负责人转而要求逐字段检查输入用途，禁止将原始结构和执行台账整包提供给模型。长期原则和[字段清单](model-input-field-review-20261112.md)已落实；查询只给结果的本地修改复用04冻结快照离线生成，C6为38,152字符，全部296个来源、记录和程序coverage保持。A/I/C3/Deep/C6的4项直接检查及限定静态独审通过；这些均为离线代码/展示证据，零新增模型或数据库写入，不能追认04真实C6执行成功。对象、历史、知识的字段选择仍待实施；原计划的一条新增替身Case保存/采用/GET验证尚未执行，不在本次字段整理中冒称已验。

## 05批：当前输入的真实执行与完整知识

2026-11-13收尾。[固定05批](../../../docs/operations/evidence/fixed-investigation-20261112-05/README.md)使用当前源码和本机隔离库，复用全部A结果，新建I和显式关联事件的Case；正常导入/索引1块完整AN0846，原4块及旧集合保持。C2按技术解释/取证指导命中两行，后续各步共用一份448字符知识正文。实际正文I/C3/Deep授权/Deep性质/C6分别为3,047/9,802/12,214/12,258/18,563字符；前序原答与此前冻结预览不同，不能作为同条件压缩对照。

新增真实生成共8次、97,835 tokens，费用未知；I、C3、C6均只使用原流程最多一次纠错，没有额外采样。I引用校验后保存partial；C3仍有案件外历史目录错用，保留独立有效部分；两个Deep已执行但未取得新外部证据。C6首次及纠错原答均在第二条建议重复N6_S9，按原规则拒收。Result为rejected/partial/conclusion=null，没有case_assessment。知识在行为性质Deep和C6问题中结构化引用，C6保留问题的原工件/角色已保存GET读回，不能因此认定F02合理使用通过。

[核对回执](../../../docs/operations/evidence/fixed-investigation-20261112-05/flow/readback-checks.json)及[限定独审](../../../docs/operations/evidence/fixed-investigation-20261112-05/audit.md)核实8份实际请求/原答与数据库一致、正式结果/Case GET为空结论和未采用。I忽略已给登录事实、Deep从名称推断自动化流程等正文问题保持原答。该批没有输入超限或新程序误拒证据；真实有效C6、完整固定调查、F02/M01仍未通过。

## 交接与下一步

本机静态包已导入01–03、07批替身Case及固定05批，共73份；04批尚未导入。21的4177仅追加固定05批静态记录，42→43份、80文件/81静态HTTP通过，旧记录及容器保持；未部署本轮模型代码、未改消费者。2026-11-13本机复查SSH中转不可达、4177无监听，[本机读回记录](../../../docs/operations/evidence/fixed-investigation-20261112-05/workbench-readback.json)与远端发布回执分开，当前不冒称本机入口可用。

输入字段选择、普通工具结果筛选、07批替身存取检查和此前限定审计继续有效。本轮已完成[离线历史/纠错材料修正](../../../docs/operations/evidence/case-citation-input-20261113-01/README.md)：3项已有检查及限定独审通过，70份原件/103条保留材料不变，C3/C6局部反馈为949/467字符；不放宽依据规则、不手改原答、未追加模型采样。实际模型纠错效果未验。可采用C6与正文质量保留未完，主调查31/41，流式继续后置；不扩大为复杂推理、队列或测试框架。

随后仅补[离线纠错调用接线](../../../docs/operations/evidence/case-correction-wiring-20261113-01/README.md)：实际`ModelSteps.call`接收四份历史原答，C3/C6各一次纠正，发出的反馈与上述预览逐值相等；内存存储保留原答、拒收和工件关系。C3保留独立分析，C6Publication仍为rejected/partial/null、不具备采用资格。网关、计量和存储均为明确替身，没有真实模型、数据库、HTTP或新Run；业务代码无新增修改。首次脚本重复压缩已压缩Schema的一致性失败单独保留，改用正常Schema构造后本次核验通过。真实存取复用05/07批，不因本次重放扩大质量结论或勾选主任务。随后3.16的[H/比较/原计划输入整理](../../../docs/operations/evidence/case-human-input-20261113-01/README.md)已完成本地程序修正和同一C01快照重建：C3/C6为11,764/19,069字符，H原文/版本/范围及原计划保持，113/126个原引用与成员关系不变；2项直接检查及H字段补齐后1项定向复验通过。该批指定旧Result无有效结论，仍标不可用；7条旧H回执附件未变成可见。零新模型/数据库/网络调用，真实反馈效果、比较质量和主31/41保持未完成，流式后置。

## H输入整理后的保存读取补核（2026-11-13）

复用一条已有H后固定调查场景，隔离PostgreSQL加模型/外部查询替身，补齐两版H→显式下一轮→C3/Deep/C6→Result/当前判断与版本GET。见[独立批次](../../../docs/operations/evidence/case-human-persistence-20261113-01/README.md)及[输入原件](../../../docs/operations/evidence/case-human-persistence-20261113-01/inputs/summary.json)。H附件、版本/原文/范围、指定基线与初始C3计划引用保持；结果accepted/uncertain/partial，当前判断采用同一结论。

实际两次数据库尝试：pg-01替身取字段错误，第二轮unknown保留；pg-02两轮业务完成且结果/当前判断GET通过，尾段验证取错简版报告失败。原失败不改写，修正后仅对pg-02做只读尾段核验并通过，没有第三次完整流程或真实模型调用。本机静态4177追加两Case快照至75份，未发布。只证明程序存取接线，不证明H/比较的真实模型效果，不勾主调查3.16或核销M01/F02。

## 09批：比较引用修复的一次真实核验

[本批记录](../../../docs/operations/evidence/fixed-investigation-20261113-09/README.md)复用08同Case/A/I/H，指定已接受B01基线；一次新Run、4次生成、50,394tokens。C6首答及纠正答引用指定N5_S93；首答重复N5_S7，v9一次反馈后接受待复核并采用，新鲜度current。纠正答仅conclusion.support_ids改变，比较仍not_comparable却声称前后相同且本轮依据更充分，质量NOT_PASSED。实际未出现同文背景别名或缺基线反馈，不扩大验证范围。

C3/C6的68条成员事实及本次C3依赖保持，H原文/范围保持，知识448字符每请求一次且被C6引用；合理使用未通过。4份请求/原答与真实隔离库一致，原ASGI 4次GET一致；旧Run/Result/H和137份08文件保持。本机静态83→84，在线未更新。无预算增加、单测、额外采样、业务实现/HTTP/表/部署变更；主调查31/41及流式后置保持。限定审计见[本批audit](../../../docs/operations/evidence/fixed-investigation-20261113-09/audit.md)。
