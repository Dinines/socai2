# s02 · 审计策略及安全日志变更

[页面字段与当前判断](page-fields.json) · [全部 29 张表](database.json) · [逐步参数、错误与用量](stages.json)

按库中步骤序号排列。点击工件可读完整请求、原始返回或失败回执。主指针为空时，请核对 Run 冻结输入和本步关联工件。

## alert_basic · completed · c89507ad-437d-59ee-88e1-f66930b13145

范围输入 [28a5446b](artifacts/28a5446b-0912-49ea-965e-e9e5fdc3fa70.json)。交付 partial。停止原因 stage_output_saved。正式 Result 0 份。模型尝试 1 次，工具尝试 2 次。

| 步骤 | 操作 | 状态 | 输入 | 输出 | 其余关联工件 |
|---|---|---|---|---|---|
| 1 · A | alert_basic_analysis | completed  | 无主工件指针 | [0309b35f](artifacts/0309b35f-d9f8-5e4d-97b7-13529f3ef092.json) source_snapshot |  |
| 2 · A | assets | completed  | [957aa88b](artifacts/957aa88b-0fb8-4421-b568-f60d9a7744e6.json) tool_request · assets | [e34ce109](artifacts/e34ce109-0853-48d4-a25e-dfdd5dee9400.json) tool_response · 0 行 |  |
| 3 · A | history | completed  | [28f9f372](artifacts/28f9f372-4111-4920-a672-ee85c01c821e.json) tool_request · history | [0bfdfd83](artifacts/0bfdfd83-d37e-4089-9427-66fee15155b4.json) tool_response · 0 行 |  |
| 4 · A | threat_intel | skipped no_supported_frozen_objects | [d5dc3295](artifacts/d5dc3295-472b-41f2-ad88-734f6804f657.json) tool_request · threat_intel | [b337c132](artifacts/b337c132-bcd3-40dc-b6d3-ee1288c995ae.json) tool_response · skipped |  |
| 5 · A | alert_triage_and_explanation | completed  | [e1c80aa3](artifacts/e1c80aa3-1427-4e97-8171-ffce228302ec.json) model_request · aisoc-investigation，2 条消息 | [3483f023](artifacts/3483f023-a7ed-490b-a91a-fe8163155219.json) model_response · 有原答 |  |

## alert_basic · completed · 057c2974-8c3c-54eb-bd39-85356b4aad4c

范围输入 [5a52c9de](artifacts/5a52c9de-4499-477a-ac58-3500d2228a40.json)。交付 partial。停止原因 stage_output_saved。正式 Result 0 份。模型尝试 1 次，工具尝试 2 次。

| 步骤 | 操作 | 状态 | 输入 | 输出 | 其余关联工件 |
|---|---|---|---|---|---|
| 1 · A | alert_basic_analysis | completed  | 无主工件指针 | [8fcc9d5f](artifacts/8fcc9d5f-11e5-57b1-85a5-ac81d64e81df.json) source_snapshot |  |
| 2 · A | assets | completed  | [7eb0601d](artifacts/7eb0601d-72cf-4d58-85b8-7c8db3dcac07.json) tool_request · assets | [9022bc7c](artifacts/9022bc7c-8cd6-49dd-97db-bbf9ba43d79d.json) tool_response · 0 行 |  |
| 3 · A | history | completed  | [73554b62](artifacts/73554b62-d80a-4f7d-a659-9c44178bd057.json) tool_request · history | [58930dcd](artifacts/58930dcd-acc2-442b-ba84-0d522afe728e.json) tool_response · 2 行 |  |
| 4 · A | threat_intel | skipped no_supported_frozen_objects | [916a691b](artifacts/916a691b-7449-4fe2-adb7-d3c90b958158.json) tool_request · threat_intel | [ec8a9c3d](artifacts/ec8a9c3d-23ed-4b06-a0d8-2c4436b8b3cc.json) tool_response · skipped |  |
| 5 · A | alert_triage_and_explanation | completed  | [740941ae](artifacts/740941ae-9d67-45f6-9642-179a88713e95.json) model_request · aisoc-investigation，2 条消息 | [fa3380d0](artifacts/fa3380d0-53a7-4bc0-895c-75da1e880045.json) model_response · 有原答 |  |

## incident_diagnosis · completed · 1cd666f9-562e-53e0-b87f-6bf93e6946f0

范围输入 [e1f55869](artifacts/e1f55869-ab05-4638-9194-44946ebf46d7.json)。交付 partial。停止原因 stage_output_saved。正式 Result 0 份。模型尝试 1 次，工具尝试 0 次。

| 步骤 | 操作 | 状态 | 输入 | 输出 | 其余关联工件 |
|---|---|---|---|---|---|
| 1 · I | incident_member_synthesis | completed  | 无主工件指针 | [f28718ae](artifacts/f28718ae-aec7-5ebf-9abc-716071d539a0.json) source_snapshot |  |
| 2 · I | incident_member_synthesis | completed  | [09889f21](artifacts/09889f21-6e0f-411a-a10c-72ec1c61978f.json) model_request · aisoc-investigation，2 条消息 | [52dc9c58](artifacts/52dc9c58-93ce-40ad-a9f4-32a572fbf2f0.json) model_response · 有原答 |  |

## baseline · unknown · bce317d2-8545-4297-ad87-335aade26cf7

范围输入 [385198c2](artifacts/385198c2-0256-40dc-8308-50376f3c83d6.json)。交付 none。停止原因 executor_dispatch_uncertain。正式 Result 0 份。模型尝试 1 次，工具尝试 2 次。

| 步骤 | 操作 | 状态 | 输入 | 输出 | 其余关联工件 |
|---|---|---|---|---|---|
| 1 · C1.executor | execution_plan | completed  | 无主工件指针 | [ca67e68d](artifacts/ca67e68d-f8c0-436f-b02b-daacbfa0c661.json) source_snapshot · execution_plan |  |
| 2 · C2 | baseline_background_enrichment | completed  | [25fbe526](artifacts/25fbe526-e32c-46a8-be7f-194aec631bd0.json) source_snapshot | [88f8d888](artifacts/88f8d888-94e0-45c6-9987-b3e62ee38647.json) source_snapshot |  |
| 3 · C2 | ueba | completed  | [7146bae1](artifacts/7146bae1-e25d-45c4-a9e5-da6358392587.json) tool_request · ueba | [458e6759](artifacts/458e6759-581e-46c1-bb25-380b0fa0671c.json) tool_response · 0 行 |  |
| 4 · C2 | assets | completed  | [e53a57ee](artifacts/e53a57ee-ad30-4845-b2e8-496b03c9ef6d.json) tool_request · assets | [5a7377b9](artifacts/5a7377b9-7b53-46e7-8a39-d92539ee42ef.json) tool_response · 0 行 |  |
| 5 · C2 | history | skipped tool_budget_reserved_for_evidence | [702f66eb](artifacts/702f66eb-0b73-4dcf-a524-6647f584cb1b.json) tool_request · history | [4a6c9a6b](artifacts/4a6c9a6b-12ca-4a2e-acef-31d386eaed1e.json) tool_response · skipped |  |
| 6 · C2 | knowledge | skipped tool_budget_reserved_for_evidence | [0456f5e8](artifacts/0456f5e8-6305-4f95-a54d-4dd62d750a2f.json) tool_request · knowledge | [c995dc5f](artifacts/c995dc5f-1594-461c-9750-11581d8e1018.json) tool_response · skipped |  |
| 7 · C2 | threat_intel | skipped no_supported_frozen_objects | [922ca4f8](artifacts/922ca4f8-27f9-4561-8381-984c6aaa7981.json) tool_request · threat_intel | [a475b507](artifacts/a475b507-01fd-4b68-ba2c-05d58e0c002f.json) tool_response · skipped |  |
| 8 · C2 | graph | skipped source_not_connected | [76635ba1](artifacts/76635ba1-5983-4a4d-a043-c35ee044fc2c.json) tool_request · graph | [81a5cf04](artifacts/81a5cf04-4ddf-4da9-adb8-8df315563547.json) tool_response · skipped |  |
| 9 · C4.materials | frozen_material_semantics | completed  | 无主工件指针 | [b2bdcff4](artifacts/b2bdcff4-d0be-4316-9920-c0afa472cb3c.json) source_snapshot · materials |  |
| 10 · C3 | initial_main_and_domain_analysis | unknown analysis_dispatch_uncertain | [8e687bba](artifacts/8e687bba-ef7f-4e5d-bccb-208345ac4d3a.json) source_snapshot | 无主工件指针 |  |
| 11 · C3 | main_with_domain_views | unknown analysis_dispatch_uncertain | [26b0f3ad](artifacts/26b0f3ad-2d90-48de-8250-f415b9c16025.json) model_request · aisoc-investigation，3 条消息 | [d299c08f](artifacts/d299c08f-1f92-4763-aeb5-77891b836dde.json) model_response · 无原答，HTTP 408，model_transport_error |  |
| 12 · C6 | system_closing | completed investigation_execution_uncertain | [385198c2](artifacts/385198c2-0256-40dc-8308-50376f3c83d6.json) input_snapshot | [4b809481](artifacts/4b809481-1db1-4989-b4ef-dbef1ee234da.json) source_snapshot · partial | [077b029e](artifacts/077b029e-5d17-4b75-9cb2-fc32f3cb25ad.json)、[46d6ec3f](artifacts/46d6ec3f-6596-4ee9-a029-de0d85c6a4f5.json)、[a831724b](artifacts/a831724b-4ded-48d6-bf90-86f9992bf8ce.json) |

C6 [system](artifacts/a831724b-4ded-48d6-bf90-86f9992bf8ce.json) 报告中的结论为「案件性质待核实。本案涉及 2 条告警，当前调查尚不足以确认行为性质和影响范围，需继续核查。」。本轮交接回执 [4b809481](artifacts/4b809481-1db1-4989-b4ef-dbef1ee234da.json) 标记 `partial`，覆盖 0/2。正式 Result 为 `无`。
