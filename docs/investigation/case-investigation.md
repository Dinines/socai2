**最新部署与验收（2026-11-01）：** r13已部署；A输出截断，B completed/partial但语义未过，C跳过。见[本批分析](../operations/evidence/investigation-r13-20261101/review.md)。下方本地修复和早期部署说明按当时批次阅读，完整报告质量及5.3仍未通过。

**2026-11-01阅读说明：** 本文保留F3初版和早期验证，现行模型/Tool/停止合同已对齐 r11。最新结果是完整 raw 与真实非空查询通过、报告 failed/partial；问题保留，见[当前审阅指南](review-guide-20261101.md)。当前Case调用见[流程与追加问题](case-first-version-20261028.md)，实际验证及部署边界见[最新指南](audit-guide-20261031.md)。事件结果关联、产品主机Tool和真实联调已有后续记录，文末“尚未接通”仅为当批状态。

# F3：Case调查第一版

**2026-11-01 r12实际复验：** 上述本地上下文及校验修复已部署；A/B两次主调查均failed/partial，4真实查询/0复用/8模型25783tokens。完整raw和纠错反馈隔离已核，报告仍有无源PID/用户、空查询原因编造与协议误拒；C未满足前提而跳过。详见[真实回执](../operations/investigation-r12-report-validation-20261101.json)和[原因分析](../operations/evidence/investigation-r12-20261101/review.md)。不新增Case记忆系统，5.3仍未完成；下方未部署描述仅为此前本地阶段。

**2026-11-01本地后续修复（未部署）：** 原文模型视图保留来源路径；追加调查保留有界未决条目及原Run引用；纠错反馈不再暴露内部错误码，并拒收已知指令泄漏；修正协议空格/状态/引号误拒。沿用现有账本，暂不新增Case文档记忆系统。14个受影响直接方法最新结果通过，真实模型效果未验，详见[回执](../operations/investigation-report-context-20261101.json)和[当前审阅指南](review-guide-20261101.md)。

**2026-10-28初版补全：** 已增加只读材料预览、逐步输入输出读取、Markdown下载及关联旧报告的追加问题/显式重查，详见[当前完整接口与例子](case-first-version-20261028.md)。本轮7个调查直接用例及1个历史列表用例通过；以下4项为此前验证记录。按用户最新要求只完成Case创建后的调查，不再推进Case触发或F5。

2026-10-27审计补充：[完整实现详解](current-implementation-reference-20261027.md)列出逐步输入输出、实际ledger结构、模型/Tool消息、状态及待审计边界；[审计导航](audit-guide-20261027.md)区分本版与历史fixed/program证据。

2026-10-25。按用户最新确定的边界，Incident保留F1汇总和F2 AI概况，真正的调查分析在Case中进行。本版已实现Case的“读取已有材料→模型分析→按需查询→再次分析→报告保存/读回”。功能代码和4个直接用例已完成，未部署或进行真实PG、模型、事件湖调用。

## 如何调用

入口已注册到独立v2兼容结果/启动app，也可单独用`app.investigation_v2.case_analysis_api:create_app`创建应用。

`POST /api/v2/investigation/cases/{case_id}/investigate`：

```json
{
  "operation_key": "33333333-3333-4333-8333-333333333333",
  "start": "2026-10-25T10:00:00Z",
  "end": "2026-10-25T10:05:00Z",
  "question": "核对这些告警是否有进程和网络行为证据支持，说明关系、影响和缺口。"
}
```

Case必须已存在并有成员。默认选择启动时的全部Case成员；可显式传`selected_member_ids`选择子集。窗口需要时区，最多7天，结束时刻不包含在查询中。复用原`investigation:run`、`cases:read`、`alerts:read`权限。

返回Run ID、真实Case ID、本次成员/窗口、结构化结果和Markdown。读取进展或已保存结果：

`GET /api/v2/investigation/cases/{case_id}/investigations/{run_id}`。

同一个operation key、同一请求只读取已开始的Run，不重跑模型或查询；不同意图使用同一key返回409。Case以后新增成员，不会改变历史Run已经固定的范围。新范围要显式发起新Run。

## 调查实际做什么

1. 从PG读取真实Case、canonical成员Alert及最新已保存分诊，不由客户端摘要替代成员读取。Run固定Case/成员/窗口/问题，保留来源Incident作为引用。
2. 模型看到已有告警、分诊材料和可用Tool定义，决定是否补查、查哪种来源。来源告警是待核材料，分诊判断与事实分开。
3. 当前接通`process_activity`和`network_connections`：对Case成员主机按固定绝对窗口查询进程、路径/hash/账号或网络连接。不限TCP/443；模型不能自行更换tenant、扩大主机范围或编写SQL。
4. 工具结果以带call_id的真实Tool消息回到下一轮模型，包含来源记录ID、范围、可用性及截断信息。完整结果与模型实际收到的视图都保存到原ledger工件。
5. 模型给出摘要、带真实证据编号的发现、反证、缺口和建议。不存在的证据引用不会成为正常结论；空结果、查询失败、截断等限制继续保留。
6. 保存Case所属Run、步骤、结构化结果及Markdown，报告附证据索引；不自动改变Case/Alert/Incident状态，不执行建议动作。

普通主调查按包含问题的 source_hash 查找同Case历史结果；显式追加则按不包含问题的 material_hash 和相同来源schema核对前次材料。工具/参数仍须一致且历史结果可用，保留原Run/证据引用；refresh_queries=true禁用复用。进程结果另要求case.process_activity.v2，产品当前快照不复用；该指纹不主动检测事件湖后补/更正、通用工具/模型版本或外部来源新鲜度；这些变化不会仅凭后端发生过便自动触发重查。历史消耗不重复计入本次用量。

## 范围和停止

- 当前代码常量为4次模型调用、4次工具调用、24000 tokens；120秒限制包住主分析循环，不包含前置Case读取/配置解析与最终报告持久化。每次模型最多输出3000 tokens，HTTP及bundled gateway单请求等待使用调查循环剩余时间，连接上限min(10秒,剩余时间)，直连/BYOK不添加网关timeout字段，用量未知时停止。不合法结论最多在现有预算内纠正一次，原回复与完整校验反馈留在步骤中。查询最多两轮模型决策并使用原生Tools；首份正式报告及必要时一次纠错都使用JSON Schema，不再补查。模型用当前A引用，服务端映射公开UUID。纠错采用简短专用指令和字段错误，省去已由schema提供的重复描述，源材料不变；早期版本曾通过真实追加的纠错、保存与读回，不能替代r11报告质量验收，见[逐步测试](step-by-step-test-20261028.md)步骤8–9。没有自动重发超时请求或独立USD上限/租户累计额度准入，不能等同旧M3预留账本。
- 查询仅覆盖已接入事件湖中的进程/网络记录。进程工具不提供父进程链；账号、云审计、产品专用HTTP接口等需后续按具体能力接入，不能据本版未返回记录声称这些来源已核对。
- 消息过大、达到限制、模型不可用或没有形成可引用结论时，保存已有材料和partial报告，说明停止原因。
- `Run.status=completed`表示本次执行结束；结果的`completion=conclusion_available`表示有模型结论，含缺口时为`partial`。这些字段不代表Case已解决或攻击性质已经得到独立验证。

本版使用独立`case_analysis.v1`入口和既有ledger；没有将旧fixed/program Run原地升级，也没有新增Incident调查profile。既有专项Deep/专家能力未因此全部迁移；本版主分析直接通过工具循环选择必要补查。

`read_member_ids`只表示实际读到PG成员，不是逐成员已完成调查的证明。现行结论检查结构、引用、成员完整性及有限协议措辞，但不做通用逐句语义采信；协议误拒和报告内容问题仍保留，失败/空工具结果同样有E编号。结果GET直接解析所选JSON工件，没有复用旧M7 manifest/hash整链重建。中止或try之外的异常可能留下running，不保证所有路径都会生成终止报告。详见[待审计边界](current-implementation-reference-20261027.md#review-boundaries)。

## 早期验证记录（2026-10-25）

原阶段直接验证命令如下；本轮文档维护不执行，已通过且未变的结果复用：

```text
python -B -m unittest discover -s services/api/tests -p test_case_analysis_api.py -v
```

本轮4项通过：完整Case链路/报告读回与重复只读、空结果与查询失败区分、适用历史查询复用、未知模型用量停止。首轮发现报告时间序列化读回不一致，已修为统一ISO时间；失败场景也改为新的查询窗口，确保不复用前一个合法空结果。修后同一组直接用例通过，没有扩展测试框架或恢复/可用性测试。

验证使用实际ASGI入口、模型HTTP协议包装、SQL参数组装及保存/读取代码，ledger、模型和事件湖由替身提供。模型替身按脚本返回tool_calls，因此证明的是调用与回传链路接通；尚未证明真实模型会自主选择正确工具或给出合格业务判断。真实模型行为需按[Tool接入指南](tool-onboarding-and-flow-verification.md)在选定配置/场景中另做直接验证。

2026-10-28：F4成员创建/关联Case入口及新版Case历史列表已有代码和直接替身验证，见[F4说明](case-linking-20261028.md)。转入后明确携带selected_member_ids调用本调查入口。事件层继续保持已有汇总和AI概况，F5及事件报告回显仍未接通。
