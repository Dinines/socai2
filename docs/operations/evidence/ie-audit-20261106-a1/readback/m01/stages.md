# m01 · Web 证书替换

[页面字段与当前判断](page-fields.json) · [全部 29 张表](database.json) · [逐步参数、错误与用量](stages.json)

按库中步骤序号排列。点击工件可读完整请求、原始返回或失败回执。主指针为空时，请核对 Run 冻结输入和本步关联工件。

## alert_basic · failed · deecdaf8-12f9-5236-8631-d54fa32f649a

范围输入 [5ab26462](artifacts/5ab26462-0aed-4483-a7ec-86d66c309187.json)。交付 none。停止原因 alert_decision_basis_not_direct。正式 Result 0 份。模型尝试 1 次，工具尝试 2 次。

| 步骤 | 操作 | 状态 | 输入 | 输出 | 其余关联工件 |
|---|---|---|---|---|---|
| 1 · A | alert_basic_analysis | failed alert_decision_basis_not_direct | 无主工件指针 | 无主工件指针 |  |
| 2 · A | assets | completed  | [b20cdc88](artifacts/b20cdc88-25c1-48b7-afda-af0eb4944525.json) tool_request · assets | [b585d8d0](artifacts/b585d8d0-7982-4f5e-9bfa-59e88751c1dd.json) tool_response · 0 行 |  |
| 3 · A | history | completed  | [84eb9d36](artifacts/84eb9d36-02aa-4d67-88fb-aaeeb97933e9.json) tool_request · history | [2ed43d38](artifacts/2ed43d38-b60e-4a69-b551-fa602e7377c4.json) tool_response · 0 行 |  |
| 4 · A | threat_intel | skipped no_supported_frozen_objects | [a4c098c3](artifacts/a4c098c3-6392-4775-8aa8-4ae7d932044d.json) tool_request · threat_intel | [82b3bb1f](artifacts/82b3bb1f-907c-4e0f-8b93-5579c8b059dc.json) tool_response · skipped |  |
| 5 · A | alert_triage_and_explanation | failed alert_decision_basis_not_direct | [c0fa2885](artifacts/c0fa2885-1d17-44c5-9829-915370e054f6.json) model_request · aisoc-investigation，2 条消息 | [816aec0c](artifacts/816aec0c-2421-4677-aa14-13b1ebd8dd5f.json) model_response · 有原答，alert_decision_basis_not_direct |  |

## incident_diagnosis · completed · 5e3f4a5b-15ba-5f4f-9273-29514661649f

范围输入 [a7dfd38e](artifacts/a7dfd38e-11d3-4b29-94d9-01bdb6938cbb.json)。交付 partial。停止原因 stage_output_saved。正式 Result 0 份。模型尝试 1 次，工具尝试 0 次。

| 步骤 | 操作 | 状态 | 输入 | 输出 | 其余关联工件 |
|---|---|---|---|---|---|
| 1 · I | incident_member_synthesis | completed  | 无主工件指针 | [cea47d9e](artifacts/cea47d9e-69bf-52e5-9e87-7a8ae5772449.json) source_snapshot |  |
| 2 · I | incident_member_synthesis | completed  | [4a000518](artifacts/4a000518-7bec-4df6-9e22-514af662ac2b.json) model_request · aisoc-investigation，2 条消息 | [59a199ea](artifacts/59a199ea-c676-462d-977e-30ddaabe8ee1.json) model_response · 有原答 |  |

## baseline · unknown · 0e85ecb5-db82-4dc4-8561-da5fce18c744

范围输入 [6e4189f2](artifacts/6e4189f2-00cf-4392-bfb4-b5e8afa85663.json)。交付 none。停止原因 executor_dispatch_uncertain。正式 Result 0 份。模型尝试 1 次，工具尝试 2 次。

| 步骤 | 操作 | 状态 | 输入 | 输出 | 其余关联工件 |
|---|---|---|---|---|---|
| 1 · C1.executor | execution_plan | completed  | 无主工件指针 | [4861eba9](artifacts/4861eba9-b3fe-4c6f-bd28-0e9d2fa33dd2.json) source_snapshot · execution_plan |  |
| 2 · C2 | baseline_background_enrichment | completed  | [8f8d4965](artifacts/8f8d4965-1129-4e33-b200-227576e5f2f8.json) source_snapshot | [1333abb0](artifacts/1333abb0-4ab6-447f-9fbe-1aef3c813e48.json) source_snapshot |  |
| 3 · C2 | ueba | completed  | [d2aaa4a2](artifacts/d2aaa4a2-13c4-4fc9-8f90-661232eded96.json) tool_request · ueba | [cf6e7827](artifacts/cf6e7827-aaf3-47f0-9728-05c5bfdd6285.json) tool_response · 0 行 |  |
| 4 · C2 | assets | completed  | [4be02154](artifacts/4be02154-dc94-4022-ac91-5593fa277036.json) tool_request · assets | [80d665ca](artifacts/80d665ca-757f-4c97-8455-6de1604877c9.json) tool_response · 0 行 |  |
| 5 · C2 | history | skipped tool_budget_reserved_for_evidence | [00cd4682](artifacts/00cd4682-4e87-4524-baac-7b25ff026f1d.json) tool_request · history | [6ed4b7ff](artifacts/6ed4b7ff-6ce2-4564-acc7-cf3cd5d70230.json) tool_response · skipped |  |
| 6 · C2 | knowledge | skipped tool_budget_reserved_for_evidence | [9fbe8a9d](artifacts/9fbe8a9d-0eb3-4af7-b1ee-0bfa1d7b9eb1.json) tool_request · knowledge | [26cbb640](artifacts/26cbb640-7848-4807-a328-6a8de9525ff3.json) tool_response · skipped |  |
| 7 · C2 | threat_intel | skipped no_supported_frozen_objects | [629acef7](artifacts/629acef7-90f2-479b-ac83-68483f55a8c0.json) tool_request · threat_intel | [28d15c9c](artifacts/28d15c9c-769f-40e5-8121-6119059f51b8.json) tool_response · skipped |  |
| 8 · C2 | graph | skipped source_not_connected | [2e8d7eff](artifacts/2e8d7eff-4551-4e2b-b814-208df929cd27.json) tool_request · graph | [7c5f12ef](artifacts/7c5f12ef-a741-4bc8-ad4c-9c14a2adc852.json) tool_response · skipped |  |
| 9 · C4.materials | frozen_material_semantics | completed  | 无主工件指针 | [6f9d0932](artifacts/6f9d0932-0559-4a53-8984-0a0c1fa19525.json) source_snapshot · materials |  |
| 10 · C3 | initial_main_and_domain_analysis | unknown analysis_dispatch_uncertain | [c6aecbea](artifacts/c6aecbea-5e81-4704-b646-003a47cea2a7.json) source_snapshot | 无主工件指针 |  |
| 11 · C3 | main_with_domain_views | unknown analysis_dispatch_uncertain | [2fc4a079](artifacts/2fc4a079-70a0-45ac-9fa0-71c5af9d3e37.json) model_request · aisoc-investigation，3 条消息 | [4d4d751f](artifacts/4d4d751f-bafe-4119-a0d2-2218451f7542.json) model_response · 无原答，HTTP 408，model_transport_error |  |
| 12 · C6 | system_closing | completed investigation_execution_uncertain | [6e4189f2](artifacts/6e4189f2-00cf-4392-bfb4-b5e8afa85663.json) input_snapshot | [96ff5f4e](artifacts/96ff5f4e-a40e-42c6-bbdc-a39e1aafd526.json) source_snapshot · partial | [325c0c41](artifacts/325c0c41-00a1-44bd-8d73-cc57426082e4.json)、[347971f8](artifacts/347971f8-4cae-4c1e-9173-0f078f4ccaff.json)、[4adb9cc5](artifacts/4adb9cc5-2b32-4a77-be3e-e5b5d93214aa.json) |

C6 [system](artifacts/325c0c41-00a1-44bd-8d73-cc57426082e4.json) 报告中的结论为「案件性质待核实。本案涉及 1 条告警，当前调查尚不足以确认行为性质和影响范围，需继续核查。」。本轮交接回执 [96ff5f4e](artifacts/96ff5f4e-a40e-42c6-bbdc-a39e1aafd526.json) 标记 `partial`，覆盖 0/1。正式 Result 为 `无`。
