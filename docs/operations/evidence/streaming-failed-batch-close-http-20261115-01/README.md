# S01旧失败批：通过既有HTTP停止后续分析

2026-11-15。按调查第11步分工处理，仅限[旧批实际保存快照](../test-streaming-s01-ingress-20261115-01/readback/alerts-pg.json)中的3条告警和1个事件。旧批来源范围错误及失败结论保留，不能算新批入站通过。

实际调用21候选`http://192.168.1.21:18424/api/v1/socai2`，无Authorization、Token或登录。现有告警/事件`PATCH /{alerts|incidents}/{id}/management`足够完成，不改业务代码、合同或数据库结构，不新增取消接口，不直写SQL。

| 对象 | 实际ID | 结果 |
| --- | --- | --- |
| 告警 | `03c0764c-43a1-5906-8db9-425755afe9ed` | `new → completed`，版本2→3 |
| 告警 | `978aaa6e-4ff8-549a-a01b-d31ac7f3c1c7` | `new → completed`，版本2→3 |
| 告警 | `c7769f40-6390-5ffc-ac8e-d809d34b9639` | `new → completed`，版本2→3 |
| 事件 | `9d80ff2b-af0a-4d33-95bb-2fe273cbc53c` | `new → resolved`，版本4→5 |

4次操作原因均为“验收批来源范围失败，停止后续分析”，活动中保存并读回；事件的`resolution_note`同文。每次使用已保存的独立operation_key和操作前实际row_version。

**直接结果：** 30次实际TCP请求（4 PATCH、26 GET）全部200，保存/详情/活动核对通过。变化仅限处理状态、关闭/解决时间与人员、事件解决说明及业务版本/更新时间；原材料、原6条来源引用、判定、分诊/反馈/诊断指针保持，4次`feedback_id`均为空。4条原任务仍为accepted，无attempt、Run和result；本轮没有启动调度或模型。

既有调度器在后续领取时会检查主体已关闭并按`closed_before_start`跳过。**本回执尚未执行该领取/跳过动作**，不将accepted改写为skipped。关闭旧批并没有修复其错误来源，也不代替r3新批、正常建案或真实模型整链验收。

证据：

- [执行脚本](close_failed_batch.py)、[冻结来源及操作键](plan.json)、[实际请求](requests.json)。脚本拒绝已有plan的再次运行，避免盲目重复写入。
- [操作前11次读取](before.json)、[告警1](patch-01.json)、[告警2](patch-02.json)、[告警3](patch-03.json)、[事件](patch-04.json)。
- [操作后11次读取](after.json)、[4条活动读取](activities.json)、[断言结果](result.json)。

本步骤设计在[HTTP工作安排](../../../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md)与[第11步设计](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-candidate-design-20261115.md)；执行前OpenSpec严格校验通过。未发布/重启服务或推送Git。
