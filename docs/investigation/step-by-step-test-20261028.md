# 调查功能逐步测试（2026-10-28）

按“输入→实际输出→判定”逐项验证。真实PG追加问题在中间版本通过，但随后发现严格输出schema会影响旧模型选择Tool；已修正调用阶段，4项受影响直接用例通过。**用户明确授权后的最终版本真实PG测试未通过：首轮未知引用被拒，纠错请求因输入额度不足没有发送。不能把中间版本的通过当作最终代码全部通过。**

沿用21的`aisoc-investigation`模型配置，上游配置指向43的`openai/aisoc-test-investigation`。不做可用性、压力、恢复或权限专项；已通过且未变的查询与存取不重复执行。

## 逐步结果

| 步骤 | 输入 | 实际输出 | 判定 |
|---|---|---|---|
| 1. 定位追加失败 | 保存的Run `62c63635-c372-5f9a-8bd7-7a2c1af39013`两次可见回答 | 首次引用未知证据；第二次多出`concl`字段。诊断副本去掉该字段后可通过校验，原结果未改写 | 问题已定位；不是PG存取失败 |
| 2. 单独验证输出合同 | 旧模型、明确的8字段JSON Schema及合法证据/成员列表，无Tools | HTTP 200；字段与引用校验通过，4035已知tokens | 仅输出合同样例通过 |
| 3. 接入请求并直接验证 | 当时每轮请求同时携带schema和Tools | 4项受影响直接用例通过 | 替身能验证请求字段，但未发现真实模型的Tool选择影响 |
| 4. 真实追加问题 | 原Case、前次报告H1、两条成员告警，要求沿用材料且不重复查询 | 新Run `76d01bf5-4fd6-5885-9cc6-efd653eff12e`，1次模型、0次Tool、5677已知tokens；`completed / analysis_complete / partial` | 中间版本真实PG追加、读回与历史保留通过 |
| 5. 输出合同与Tool对照 | 完全虚构的主机`schema-tool-example-host`，要求先查进程；同一请求分别带/不带schema | 带schema：返回“等待进程证据”的报告，无Tool调用；不带schema：原生`process_activity`，参数`hostname= schema-tool-example-host, limit=20` | 发现真实功能冲突；不是完整Tool执行测试 |
| 6. 修正调用阶段 | 正常分析提供Tools且不带schema；仅最终结论纠错或无可用Tools时带schema | 正常查询、追加问题、Tool返回后的结论纠错、二次错误引用拒绝，共4项直接用例通过 | 最终修复的直接验证通过 |
| 7. 用户授权后验证最终代码 | 同一测试Case/前次Run/问题，新operation_key，仅一次追加验证 | 新Run `9bca2634-9b9c-542c-a8eb-783b8dd71e2a`：1次模型、0次Tool、5770已知tokens；未知引用被拒，之后`input_or_token_limit` | 未通过；PG读回、H1、原报告和重复只读仍通过 |

步骤5只有两次模型协议调用，分别858、666已知tokens；没有执行Tool、新建Run或读数据库。它使用虚构输入和简短协议提示，不等同于重跑完整Case上下文。步骤6沿用原测试，只修改受影响的断言与模型替身：纠错阶段没有提供Tools时，替身应返回结论。初次两个子例因此被`invalid_tool_call_protocol`拒绝，调整替身后继续验证第二次错误结论仍然失败，没有放宽业务校验。

## 真实追加例子的输入与输出

已有测试Case：`d183bc94-1584-50d6-bdb2-53e47cf7e7b3`。前次主调查Run：`f34febcf-6549-5997-b80f-e0fa9cb17ecb`。两条成员为`3fcd245d-0496-54f3-875e-f9a7eb90ae2d`和`5272ae80-b48e-5ef3-8cdd-805885a558a0`；窗口`2026-10-23T09:58:00Z`至`10:03:00Z`，结束时刻不含。

通过`POST /api/v2/investigation/cases/{case_id}/investigate`提供新operation_key、上述成员/窗口、previous_run_id，以及问题：

> 沿用前次材料，简要说明仍无法确定哪个进程发起连接的原因和下一步所需证据；无需重复查询。

实际返回的报告说明历史网络记录与告警匹配，但进程来源仍缺证据。两个成员都是`unresolved`，保留共同上下文关联、两条告警时间线和两项未决问题；没有新Tool证据，因此报告为partial。历史E1/E2出现在叙述中，结构化引用只采用本次A1/A2/H1；不是本次重新查询了E1/E2。

随后的实际检查如下：

1. GET新Run结果与POST返回的result相同。
2. GET `evidence/H1`返回完整前次报告，previous_result_url指向原Run。
3. 原Markdown再次下载仍逐字相同，SHA256为`8caa5bb805969963641262a04337aff696bcd9c7740eeeb3a57ea5008f1c5bfe`。
4. 步骤详情保存当时的模型输入和schema；模型视图省略历史派生时间线/覆盖表，PG中的H1未裁剪。
5. 同operation_key重复提交返回相同结果；Case累计7个Run、45个步骤、59个工件，重复请求没有新增。之前失败Run全部保留。

执行使用一次性当前API进程及真实PG，`CurrentUser`为测试注入，API通过ASGI调用；没有验证JWT/RBAC或对外部署。报告存在措辞瑕疵和需要人工核对的关联描述，结构与引用通过不等于业务判断质量通过。

## 最终代码与剩余问题

最终代码保留原生Tool选择，不再同时发送Tools和严格response_format。模型选择输出结论后若结构或引用不合法，最多一次纠错使用当前证据和成员枚举，并省略Tools；缺少材料必须列为缺口，不在纠错阶段另行查询。未提供Tools却返回tool_calls时拒绝执行。原4次模型/4次Tool/24000 tokens/120秒预算和应用侧校验不变。

自动审批曾拒绝“读取历史调查内容再发送模型”的附加检查，也拒绝“整包上传API源码”的测试包装脚本；随后采用仅发送虚构JSON及接口定义的安全替代方案，完成步骤5。用户之后明确授权把本次API代码临时传至21，用已有合成测试Case调用原模型完成真实验证，因此执行步骤7。临时进程已经结束，没有部署常驻服务；被拒的两次操作本身未执行。

步骤7首轮结论仍引用未知证据，`case_analysis_validation`保留错误及合法A1/A2/H1。只读取回保存的请求和反馈，按当前代码重建纠错输入，得到精确预检值：

| 项目 | 额度计算值 |
|---|---:|
| messages UTF-8字节 | 12385 |
| 空Tools数组字节 | 2 |
| response_format UTF-8字节 | 3140 |
| 最大输出tokens预留 | 3000 |
| 额外预留 | 256 |
| 本次预检总需求 | 18783 |
| 总24000减去已用5770后的剩余额度 | 18230 |
| 超出 | 553 |

这里是现有“输入字节保守估计+输出预留”的准入计算，不是声称输入实际消耗了18783 tokens。第二次模型请求未发出；没有扩大预算或重启该Run。Case累计8个Run、50个步骤、66个工件，历史失败和本次结果都保留。下一单项是精简纠错输入中重复的格式/范围说明，再验证该路径；不把HTTP 200、存取通过或中间版本报告通过替代最终追加分析验收。

迁移120/121未安装，事件AI概况/F4真实写入、真实厂商HTTP、前端、部署仍未验证；不因此扩展本轮测试。OpenSpec CLI不可用，未进行严格CLI校验或归档。

## 可核对记录

- [步骤1：保存回答的字段与引用诊断](../operations/investigation-followup-step1-20261028.json)
- [步骤2：单独输出合同实测](../operations/investigation-followup-step2-20261028.json)
- [步骤4：真实PG追加的完整结果与接口状态](../operations/investigation-followup-step4-20261028.json)
- [步骤5/6：虚构输入对照、最终源码SHA256及直接验证范围](../operations/investigation-tool-schema-step5-20261028.json)
- [步骤7：最终代码真实失败结果、保存步骤及额度诊断](../operations/investigation-followup-step7-20261028.json)
- [之前的真实PG主调查、Tool结果与三入口验证](real-pg-test-20261028.md)
- [当前分析循环](../../services/api/app/investigation_v2/case_analysis.py)、[模型请求合同](../../services/api/app/investigation_v2/case_analysis_models.py)
