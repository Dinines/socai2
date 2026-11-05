# Case AI预留接口

2026-11-04。按用户要求，AI问答具体实现暂缓，本批仅增加3条预留接口，不修改页面、表结构或基础调查流程。代码在主目录`E:/aisoc/socai2`、分支`codex/case-baseline-history-20261103`。

## 接口与字段

前缀：`/api/v1/socai2/cases`。所有路径ID为UUID，所有请求须有认证及`cases:write`权限，操作主体须为用户；现有`SOCAI2_CASE_API_ENABLED`仍默认false，关闭时返回503。请求不得额外携带tenant/actor等字段。

| POST路径 | 请求字段/类型 | 当前响应 |
| --- | --- | --- |
| `/{case_id}/ai/messages` | operation_key: UUID；question: 去首尾空白后1–4000字符；conversation_id: UUID或null，默认null | 501 |
| `/{case_id}/ai/messages/{message_id}/save` | operation_key: UUID；title: 去首尾空白后1–200字符；conclusion: 去首尾空白后1–20000字符 | 501 |
| `/{case_id}/results/{result_id}/adopt` | operation_key: UUID；expected_scope_revision: 非负整数 | 501 |

响应示例：

```json
{
  "detail": {
    "code": "case_ai_not_implemented",
    "status": "not_implemented",
    "message": "AI问答功能暂未实现；本次请求未执行、保存或采用任何结果。"
  }
}
```

不会查询目标Case/消息/结果是否存在，不保存消息、Run或正式结果，不执行模型/Tool，也不领取基础调查活跃槽。认证本身沿用现有依赖。再次调用仍返回501；此时没有成功幂等记录。没有写权限/非用户工作负载返回403，未认证沿原认证拒绝，非法请求返回422。

`operation_key`和`expected_scope_revision`只预留接口形状，当前不会执行幂等写入或版本比较。未来Q实现时需补完整的上下文选择、实体归属校验、对话读取与成功响应合同，不能把占位接口当作已具备这些行为。

## 与基础调查的关系

C仍完整执行同Run的C1–C6，有效基础结果按已确认规则自动更新当前判断。Q未来发送后处理、用户明确保存才形成正式AI记录、明确采用才改变当前判断；Q实际执行未来可与C并行。本批没有实现这些Q业务，也未改变C的并发/待更新/手动启动规则。

例如Case已有一轮基础结果，用户发送“这个连接还有哪些未核实事项”：当前得到501，原结果/历史/活跃Run保持。未来恢复Q后才会生成真实答复，再由用户分别选择保存及采用。

## 实现与验证

- [类型合同](../../services/api/app/socai2/case_ai_contracts.py)、[路由](../../services/api/app/api/v1/endpoints/socai2_case_ai.py)、[生成的OpenAPI](../design/socai2-case-ai-reserved-v1.openapi.json)。
- [3个直接ASGI检查](../../services/api/tests/test_socai2_case_ai_reserved.py)通过，覆盖三条路径重发501、权限/开关/工作负载/未认证、额外字段/空问题/负版本及OpenAPI无200成功响应。认证为替身；无PG、模型或Tool访问。新测试的导入排序与嵌套with静态问题随后修正，业务测试没有失败。
- [OpenSpec任务与执行记录](../../openspec/changes/complete-socai2-investigation-chain/execution.md)。这些检查只验证预留合同，不代表AI问答功能交付或真实模型质量验收。
