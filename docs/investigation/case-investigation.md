# F3：Case调查第一版

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

Case已有可用查询结果只有在本次问题、成员材料及窗口形成的来源指纹一致时才复用，并保存原Run/证据引用；发生变化则重新查询。本版不把所有历史结论都视作仍然适用，也不把历史消耗重复计入本次用量。

## 范围和停止

- 每Run最多4次模型调用、4次工具调用、24000 tokens及120秒；每次模型最多输出1200 tokens。用量未知时停止，不继续花费未知额度。
- 查询仅覆盖已接入事件湖中的进程/网络记录。进程工具不提供父进程链；账号、云审计、产品专用HTTP接口等需后续按具体能力接入，不能据本版未返回记录声称这些来源已核对。
- 消息过大、达到限制、模型不可用或没有形成可引用结论时，保存已有材料和partial报告，说明停止原因。
- `Run.status=completed`表示本次执行结束；结果的`completion=conclusion_available`表示有模型结论，含缺口时为`partial`。这些字段不代表Case已解决或攻击性质已经得到独立验证。

本版使用独立`case_analysis.v1`入口和既有ledger；没有将旧fixed/program Run原地升级，也没有新增Incident调查profile。既有专项Deep/专家能力未因此全部迁移；本版主分析直接通过工具循环选择必要补查。

## 如何验证

直接运行：

```text
python -B -m unittest discover -s services/api/tests -p test_case_analysis_api.py -v
```

本轮4项通过：完整Case链路/报告读回与重复只读、空结果与查询失败区分、适用历史查询复用、未知模型用量停止。首轮发现报告时间序列化读回不一致，已修为统一ISO时间；失败场景也改为新的查询窗口，确保不复用前一个合法空结果。修后同一组直接用例通过，没有扩展测试框架或恢复/可用性测试。

验证使用实际ASGI入口、模型HTTP协议包装、SQL参数组装及保存/读取代码，ledger、模型和事件湖由替身提供。模型替身按脚本返回tool_calls，因此证明的是调用与回传链路接通；尚未证明真实模型会自主选择正确工具或给出合格业务判断。真实模型行为需按[Tool接入指南](tool-onboarding-and-flow-verification.md)在选定配置/场景中另做直接验证。

下一功能为F4：从告警/事件选择成员创建或关联Case，复用本调查入口。事件层继续保持已有汇总和AI概况。
