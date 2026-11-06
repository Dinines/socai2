# u03 · 出站 TCP 会话

[页面字段与当前判断](page-fields.json) · [全部 29 张表](database.json) · [逐步参数、错误与用量](stages.json)

按库中步骤序号排列。点击工件可读完整请求、原始返回或失败回执。主指针为空时，请核对 Run 冻结输入和本步关联工件。

## alert_basic · completed · 630e772b-d235-537c-a73e-db32ebe2a302

范围输入 [550d53ec](artifacts/550d53ec-b4a9-41a3-8520-c355be3d3374.json)。交付 partial。停止原因 stage_output_saved。正式 Result 0 份。模型尝试 1 次，工具尝试 3 次。

| 步骤 | 操作 | 状态 | 输入 | 输出 | 其余关联工件 |
|---|---|---|---|---|---|
| 1 · A | alert_basic_analysis | completed  | 无主工件指针 | [b7a3e75f](artifacts/b7a3e75f-9192-5377-b810-fe0490261912.json) source_snapshot |  |
| 2 · A | assets | completed  | [f3429274](artifacts/f3429274-67a2-40ac-b1f7-72ed60f0b4d1.json) tool_request · assets | [4f34d773](artifacts/4f34d773-530e-4d8c-8675-86360c7a388c.json) tool_response · 0 行 |  |
| 3 · A | history | completed  | [af3f6d73](artifacts/af3f6d73-72cd-4cc5-b59a-5f259003bc49.json) tool_request · history | [834d6490](artifacts/834d6490-fdf9-4016-8d0e-918c28057bd8.json) tool_response · 0 行 |  |
| 4 · A | threat_intel | completed  | [f8b29e34](artifacts/f8b29e34-7cd1-4111-983b-9f0860eabd4f.json) tool_request · threat_intel | [b9cc8e05](artifacts/b9cc8e05-de9a-4ad1-86e1-3981621007e0.json) tool_response · 0 行 |  |
| 5 · A | alert_triage_and_explanation | completed  | [55f0372b](artifacts/55f0372b-525f-424e-88af-90baca0dcb76.json) model_request · aisoc-investigation，2 条消息 | [9927a4c9](artifacts/9927a4c9-2ffb-4b04-8b4d-e8f0bc9e50ea.json) model_response · 有原答 |  |

## incident_diagnosis · completed · 6bcf9717-4d9f-5402-ad24-0a246fee428a

范围输入 [c55b8122](artifacts/c55b8122-3e11-4732-8e64-85d22df3631d.json)。交付 partial。停止原因 stage_output_saved。正式 Result 0 份。模型尝试 1 次，工具尝试 0 次。

| 步骤 | 操作 | 状态 | 输入 | 输出 | 其余关联工件 |
|---|---|---|---|---|---|
| 1 · I | incident_member_synthesis | completed  | 无主工件指针 | [d133d38c](artifacts/d133d38c-842c-5a28-91d6-9caf441b2b36.json) source_snapshot |  |
| 2 · I | incident_member_synthesis | completed  | [8da524c4](artifacts/8da524c4-b788-4fc3-8b79-4974f33afe46.json) model_request · aisoc-investigation，2 条消息 | [138c8d2c](artifacts/138c8d2c-540b-46f5-bb27-5a7e20147157.json) model_response · 有原答 |  |

## baseline · unknown · 42b3d4d2-af42-4dcc-b25d-54582ab5fbc3

范围输入 [13a17683](artifacts/13a17683-0e27-48fa-a88b-2c9a1af8e5e2.json)。交付 none。停止原因 executor_dispatch_uncertain。正式 Result 0 份。模型尝试 1 次，工具尝试 2 次。

| 步骤 | 操作 | 状态 | 输入 | 输出 | 其余关联工件 |
|---|---|---|---|---|---|
| 1 · C1.executor | execution_plan | completed  | 无主工件指针 | [a4964e20](artifacts/a4964e20-b73b-4022-a9f2-14face47da2b.json) source_snapshot · execution_plan |  |
| 2 · C2 | baseline_background_enrichment | completed  | [fdcf7951](artifacts/fdcf7951-2587-4583-b164-481cb403148d.json) source_snapshot | [7f6fff93](artifacts/7f6fff93-4821-47e4-b731-b08211c2de36.json) source_snapshot |  |
| 3 · C2 | threat_intel | completed  | [43c86416](artifacts/43c86416-89fd-4823-82c4-04fb52aeea50.json) tool_request · threat_intel | [b7a0d154](artifacts/b7a0d154-c9f4-4ab6-bd7a-2a5befaa1f9f.json) tool_response · 0 行 |  |
| 4 · C2 | assets | completed  | [cc04405f](artifacts/cc04405f-e216-4729-9f70-b2e31a354960.json) tool_request · assets | [6d79d565](artifacts/6d79d565-93ef-4c81-a172-de085a86a9ad.json) tool_response · 0 行 |  |
| 5 · C2 | history | skipped tool_budget_reserved_for_evidence | [cd36995b](artifacts/cd36995b-73cc-48ff-8583-94cbd6bec09c.json) tool_request · history | [1cb05f2b](artifacts/1cb05f2b-f12e-4a81-a50f-ee33bab30ee7.json) tool_response · skipped |  |
| 6 · C2 | knowledge | skipped tool_budget_reserved_for_evidence | [d0b46de0](artifacts/d0b46de0-ffbb-41d6-b4db-aba6f9bf4ba9.json) tool_request · knowledge | [28421987](artifacts/28421987-15c5-4ca0-9b13-345515d3de0a.json) tool_response · skipped |  |
| 7 · C2 | ueba | skipped no_supported_frozen_objects | [47d6d2ef](artifacts/47d6d2ef-e7c7-4c23-afae-2c27bb5ae839.json) tool_request · ueba | [dea611c8](artifacts/dea611c8-b24a-4afc-b614-fdc4a8e1e733.json) tool_response · skipped |  |
| 8 · C2 | graph | skipped source_not_connected | [479f9d7c](artifacts/479f9d7c-3f0d-495c-af9f-a0a72f3e4508.json) tool_request · graph | [0032348e](artifacts/0032348e-00a5-4147-aa82-cde55463d248.json) tool_response · skipped |  |
| 9 · C4.materials | frozen_material_semantics | completed  | 无主工件指针 | [dbf27f11](artifacts/dbf27f11-2d26-4fc4-95c5-7b5ed86df2aa.json) source_snapshot · materials |  |
| 10 · C3 | initial_main_and_domain_analysis | unknown analysis_dispatch_uncertain | [8d6ae24e](artifacts/8d6ae24e-ead8-4f69-b93c-c1ba8a14ac38.json) source_snapshot | 无主工件指针 |  |
| 11 · C3 | main_with_domain_views | unknown analysis_dispatch_uncertain | [bd9e1267](artifacts/bd9e1267-dcbd-4b79-9962-72155216eca7.json) model_request · aisoc-investigation，3 条消息 | [17769023](artifacts/17769023-211d-46e3-867a-ee5299ceb3da.json) model_response · 无原答，HTTP 408，model_transport_error |  |
| 12 · C6 | system_closing | completed investigation_execution_uncertain | [13a17683](artifacts/13a17683-0e27-48fa-a88b-2c9a1af8e5e2.json) input_snapshot | [2fca9d10](artifacts/2fca9d10-1025-455e-9958-8cdfe5256a1b.json) source_snapshot · partial | [268460e2](artifacts/268460e2-fc03-49dc-a4c6-faa27e8a1933.json)、[b7693c42](artifacts/b7693c42-895b-4292-91db-4c9ce206734a.json)、[c101853d](artifacts/c101853d-5e04-48be-b4dd-63a5d0049666.json) |

C6 [system](artifacts/c101853d-5e04-48be-b4dd-63a5d0049666.json) 报告中的结论为「案件性质待核实。本案涉及 1 条告警，当前调查尚不足以确认行为性质和影响范围，需继续核查。」。本轮交接回执 [2fca9d10](artifacts/2fca9d10-1025-455e-9958-8cdfe5256a1b.json) 标记 `partial`，覆盖 0/1。正式 Result 为 `无`。
