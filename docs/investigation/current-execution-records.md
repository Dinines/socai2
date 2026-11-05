# 调查执行记录逐Run索引

配合[当前执行账本](current-execution-ledger.md)阅读。本页仅整理已保存的真实合成样本记录，取数时点2026-11-05 00:13:44 UTC（北京时间08:13:44），本次没有重新读取线上状态。这是实际执行到达情况，不是当前全部代码和分支已成功验收的声明。

[数据库取回原件](/E:/aisoc/socai2/docs/operations/evidence/socai2-kafka-chain-20261105/k2/20261105T001341-export/database-20261105T001344.json)；SHA256 `19bdc122dc79fade626634351948cb0ce8efffecb7ab31e5b937be8bc696da5f`。原件未修改。

26条Run、162条Step、361份工件（包含无Run的Fusion首份材料）。保存了4份Case结果，采用判断0份。

下表的输入/输出ID是原件`artifacts[]`的id，内容在content_json/content_text；按ID搜索即可看到实际请求、原答、查询或报告。model_request保存派发用的协议正文；其存在不证明远端执行成功，凭据不在工件里。Step的主输出之外还可能有多份工件，因此逐Run也列出全部工件目录。

关联行数是这份数据库快照中的记录数，不等于本次执行的INSERT/UPDATE次数；没有事务前后快照的写入不伪称已还原。完整写入规则见[逐表写点](current-database-write-catalog.md)。

| 序号 | Run | 对象/类型 | 状态 | 停止原因 |
|---|---|---|---|---|
| 1 | [80767d7f-0571-5cf2-acf0-8b98e4d4556d](#run-1) | Process command observed / alert_basic | completed | stage_output_saved |
| 2 | [2727184f-221c-5bb4-9c05-aa29fe9e60fd](#run-2) | Outbound connection observed / alert_basic | completed | stage_output_saved |
| 3 | [e4ca5a7b-a4f3-572b-a6a9-f360ae81f05e](#run-3) | 关联事件 · Process command observed / incident_diagnosis | completed | stage_output_saved |
| 4 | [a7c73f72-0259-4fb9-a4fe-16a7017cf4c5](#run-4) | Endpoint activity review / baseline | failed | no_accepted_main_analysis |
| 5 | [f8387216-3841-5924-afcd-1879894c7b78](#run-5) | Process command observed / alert_basic | completed | stage_output_saved |
| 6 | [89983e22-f835-533b-a194-f783eb0d7483](#run-6) | Outbound connection observed / alert_basic | completed | stage_output_saved |
| 7 | [fd8f79ef-bec2-5071-bb9e-eb394079c008](#run-7) | 关联事件 · Process command observed / incident_diagnosis | completed | stage_output_saved |
| 8 | [4d8356ef-64fa-4331-ad97-34e58eeaf8da](#run-8) | Endpoint activity review / baseline | failed | required_model_input_unavailable |
| 9 | [55f49792-8e11-5419-91d3-f207123dfbc5](#run-9) | Process command observed / alert_basic | completed | stage_output_saved |
| 10 | [c17fa3dc-f51a-5bd8-b05c-419070d59ac1](#run-10) | Outbound connection observed / alert_basic | completed | stage_output_saved |
| 11 | [12576785-caaa-5f10-9393-47ae297bd72e](#run-11) | 关联事件 · Process command observed / incident_diagnosis | completed | stage_output_saved |
| 12 | [44a7863a-5edb-4cab-9480-17b4b0c12121](#run-12) | Endpoint activity review / baseline | failed | required_model_input_unavailable |
| 13 | [2dbb194b-5cf0-4f04-aa26-c81928d0eb9b](#run-13) | Endpoint activity review / baseline | failed | required_model_input_unavailable |
| 14 | [11ce2d46-9022-5a61-9a29-a697efddcb7c](#run-14) | Process command observed / alert_basic | failed | alert_decision_basis_mismatch |
| 15 | [eaf0d23a-b085-52df-be95-21d2b6f66244](#run-15) | Outbound connection observed / alert_basic | completed | stage_output_saved |
| 16 | [9bb665cd-f20a-5790-9c7f-07b638568105](#run-16) | 关联事件 · Process command observed / incident_diagnosis | completed | stage_output_saved |
| 17 | [cabb2a3b-7d9c-4ec7-9d00-95924a87885c](#run-17) | Endpoint activity review / baseline | unknown | executor_dispatch_uncertain |
| 18 | [96e6f573-4de2-554d-8be6-1e7c1b189917](#run-18) | Process command observed / alert_basic | completed | stage_output_saved |
| 19 | [09afebcb-77f4-531f-a920-20e96f2c40c5](#run-19) | Outbound connection observed / alert_basic | completed | stage_output_saved |
| 20 | [85536dbe-b59d-50f0-bce8-6fe89c126a1c](#run-20) | 关联事件 · Process command observed / incident_diagnosis | failed | incident_source_wrong_member |
| 21 | [f5306373-9ded-437d-aaa3-6990db3f2c8d](#run-21) | Endpoint activity review / baseline | unknown | executor_dispatch_uncertain |
| 22 | [21e7edf5-4216-5534-8b05-6e733275a178](#run-22) | Process command observed / alert_basic | completed | stage_output_saved |
| 23 | [5cfd24f5-4606-5212-ab03-ce1338ff5a44](#run-23) | Outbound connection observed / alert_basic | completed | stage_output_saved |
| 24 | [25a24d2f-6633-5420-b02f-92637873f81f](#run-24) | 关联事件 · Process command observed / incident_diagnosis | completed | stage_output_saved |
| 25 | [a3bb07c3-1dfb-4c79-99db-0455cbb2bfc6](#run-25) | Endpoint activity review / baseline | unknown | executor_dispatch_uncertain |
| 26 | [2d32f7c8-4abc-4b03-bc56-58146263e7dd](#run-26) | Endpoint activity review / baseline | pending_update | — |

<a id="run-1"></a>
## 1. Process command observed · alert_basic

Run：`80767d7f-0571-5cf2-acf0-8b98e4d4556d`；对象：`5db6e9d7-59a4-56de-b5c6-2661c586faff`。

状态：`completed`；停止：`stage_output_saved`；交付：`partial`。请求 `2026-11-05T00:04:03.832809+00:00`，开始 `2026-11-05T00:04:03.832809+00:00`，结束 `2026-11-05T00:04:06.803751+00:00`。

冻结输入：`73d706c9-ba51-44f2-a203-e2b7292429b8`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 1, "incident_diagnoses": 0, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | A / stage / alert_basic_analysis | completed | — | ff2539a6-8859-5ac3-8b12-2f34bf91dba5 | {"rows": null, "error": null} |
| 2 | A / tool / assets | completed | 35299372-1f58-42dd-8e60-e497a51a4767 | 010c3613-19c9-4e3b-855f-e1cb8fad37c2 | {"rows": 0, "error": null} |
| 3 | A / tool / history | completed | 30945f57-6649-47cc-b240-2b8d22eaaae6 | 13188699-0764-48e9-b4fd-ef5f0b21155b | {"rows": 0, "error": null} |
| 4 | A / tool / threat_intel | skipped | 1cc30b39-4c09-4967-9064-3c0227d4b6df | 32398075-458b-47f0-99da-f58c9b4c3780 | {"rows": null, "error": {"code": "no_supported_frozen_objects", "message": "no_supported_frozen_objects", "retryable": false, "occurred_at": "2026-11-05T00:04:03.960402+00:00"}} |
| 5 | A / model / alert_triage_and_explanation | completed | de6cb1c0-2340-491a-b13a-2b70817fa7ec | ae7c7973-a4cd-4b82-b7fb-d8c8be067c45 | {"rows": null, "error": null} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| 73d706c9-ba51-44f2-a203-e2b7292429b8 | input_snapshot / socai2.stage-result.v1 | — |
| 35299372-1f58-42dd-8e60-e497a51a4767 | tool_request / socai2.alert-basic-executor.v3 | eaadd13a-077e-41fb-a588-85a622038093 |
| 010c3613-19c9-4e3b-855f-e1cb8fad37c2 | tool_response / socai2.alert-basic-executor.v3 | eaadd13a-077e-41fb-a588-85a622038093 |
| 30945f57-6649-47cc-b240-2b8d22eaaae6 | tool_request / socai2.alert-basic-executor.v3 | 8c967275-1bd0-413f-b7b4-d547c41bfe4b |
| 13188699-0764-48e9-b4fd-ef5f0b21155b | tool_response / socai2.alert-basic-executor.v3 | 8c967275-1bd0-413f-b7b4-d547c41bfe4b |
| 1cc30b39-4c09-4967-9064-3c0227d4b6df | tool_request / socai2.alert-basic-executor.v3 | 827db819-71b9-4f62-9662-a8a430d19bd9 |
| 32398075-458b-47f0-99da-f58c9b4c3780 | tool_response / socai2.alert-basic-executor.v3 | 827db819-71b9-4f62-9662-a8a430d19bd9 |
| de6cb1c0-2340-491a-b13a-2b70817fa7ec | model_request / socai2.alert-basic-executor.v3 | 5109f8ba-e9e9-46e5-a5c4-4731f5828598 |
| ae7c7973-a4cd-4b82-b7fb-d8c8be067c45 | model_response / socai2.alert-basic-executor.v3 | 5109f8ba-e9e9-46e5-a5c4-4731f5828598 |
| 7a516191-a442-5fc3-ac36-7965b9343fee | alert_explanation / socai2.stage-result.v1 | — |
| ff2539a6-8859-5ac3-8b12-2f34bf91dba5 | source_snapshot / socai2.stage-result.v1 | — |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-2"></a>
## 2. Outbound connection observed · alert_basic

Run：`2727184f-221c-5bb4-9c05-aa29fe9e60fd`；对象：`6d5afb10-eb6c-567d-a810-9dd469118da7`。

状态：`completed`；停止：`stage_output_saved`；交付：`partial`。请求 `2026-11-05T00:04:06.868788+00:00`，开始 `2026-11-05T00:04:06.868788+00:00`，结束 `2026-11-05T00:04:09.545915+00:00`。

冻结输入：`ef2566bf-3101-4f79-97dd-5c28e5270d61`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 1, "incident_diagnoses": 0, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | A / stage / alert_basic_analysis | completed | — | 2273508c-f0c5-5785-8d3a-15be4ef17921 | {"rows": null, "error": null} |
| 2 | A / tool / assets | completed | e4cb6202-5cbe-42c1-9ce7-58d7b662f0ea | 7d987062-033e-4204-b4a5-a1dd140db98e | {"rows": 0, "error": null} |
| 3 | A / tool / history | completed | 6ea727da-b04d-407f-9eb8-71f5985dc2c7 | 539e40ad-8654-4384-bd2c-778d38edfeed | {"rows": 1, "error": null} |
| 4 | A / tool / threat_intel | completed | 1a6b8df2-5e85-4d75-a787-4a651bc3b10a | 18e48e98-25cb-4193-b846-1b14698336f1 | {"rows": 0, "error": null} |
| 5 | A / model / alert_triage_and_explanation | completed | 83e35d54-8b51-4d94-a631-a143e164c809 | b13d86ab-95f1-4281-b0e7-60f197207350 | {"rows": null, "error": null} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| ef2566bf-3101-4f79-97dd-5c28e5270d61 | input_snapshot / socai2.stage-result.v1 | — |
| e4cb6202-5cbe-42c1-9ce7-58d7b662f0ea | tool_request / socai2.alert-basic-executor.v3 | 6b3c680d-849a-46ab-8415-a94daac42304 |
| 7d987062-033e-4204-b4a5-a1dd140db98e | tool_response / socai2.alert-basic-executor.v3 | 6b3c680d-849a-46ab-8415-a94daac42304 |
| 6ea727da-b04d-407f-9eb8-71f5985dc2c7 | tool_request / socai2.alert-basic-executor.v3 | 12f48c68-b82f-4649-9215-9fbe076f4ad3 |
| 539e40ad-8654-4384-bd2c-778d38edfeed | tool_response / socai2.alert-basic-executor.v3 | 12f48c68-b82f-4649-9215-9fbe076f4ad3 |
| 1a6b8df2-5e85-4d75-a787-4a651bc3b10a | tool_request / socai2.alert-basic-executor.v3 | 183d24eb-51c1-424e-83bf-38d65685d0de |
| 18e48e98-25cb-4193-b846-1b14698336f1 | tool_response / socai2.alert-basic-executor.v3 | 183d24eb-51c1-424e-83bf-38d65685d0de |
| 83e35d54-8b51-4d94-a631-a143e164c809 | model_request / socai2.alert-basic-executor.v3 | bcd3398d-d55e-450d-a1f9-546bd4db353d |
| b13d86ab-95f1-4281-b0e7-60f197207350 | model_response / socai2.alert-basic-executor.v3 | bcd3398d-d55e-450d-a1f9-546bd4db353d |
| 044fefa5-b501-5e42-838e-73157ae02176 | alert_explanation / socai2.stage-result.v1 | — |
| 2273508c-f0c5-5785-8d3a-15be4ef17921 | source_snapshot / socai2.stage-result.v1 | — |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-3"></a>
## 3. 关联事件 · Process command observed · incident_diagnosis

Run：`e4ca5a7b-a4f3-572b-a6a9-f360ae81f05e`；对象：`85ec64ed-64e0-4f8d-ad25-0654656df3d6`。

状态：`completed`；停止：`stage_output_saved`；交付：`partial`。请求 `2026-11-05T00:04:09.61953+00:00`，开始 `2026-11-05T00:04:09.61953+00:00`，结束 `2026-11-05T00:04:19.629106+00:00`。

冻结输入：`ce6d2f1f-6c83-4ee9-9cb9-17fc6bfbfac1`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 0, "incident_diagnoses": 1, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | I / stage / incident_member_synthesis | completed | — | c93a7fd5-f40f-556c-8276-6aa4d493a172 | {"rows": null, "error": null} |
| 2 | I / model / incident_member_synthesis | completed | 473b6f3c-4c9d-4699-9cf6-81365615d360 | e4b1553b-5f2f-4178-848f-4231d19d42ea | {"rows": null, "error": null} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| ce6d2f1f-6c83-4ee9-9cb9-17fc6bfbfac1 | input_snapshot / socai2.stage-result.v1 | — |
| 473b6f3c-4c9d-4699-9cf6-81365615d360 | model_request / socai2.incident-diagnosis-executor.v3 | 6efa09be-6b43-4aea-b1dc-584c8fe3a5ba |
| e4b1553b-5f2f-4178-848f-4231d19d42ea | model_response / socai2.incident-diagnosis-executor.v3 | 6efa09be-6b43-4aea-b1dc-584c8fe3a5ba |
| c93a7fd5-f40f-556c-8276-6aa4d493a172 | source_snapshot / socai2.stage-result.v1 | — |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-4"></a>
## 4. Endpoint activity review · baseline

Run：`a7c73f72-0259-4fb9-a4fe-16a7017cf4c5`；对象：`3f3b9e7e-227f-59f4-9d50-addf63ac3584`。

状态：`failed`；停止：`no_accepted_main_analysis`；交付：`partial`。请求 `2026-11-05T00:04:19.722355+00:00`，开始 `2026-11-05T00:04:19.823241+00:00`，结束 `2026-11-05T00:04:30.358363+00:00`。

冻结输入：`1a1a9505-748d-4ebd-bd90-7806eb33ac48`；范围版本：`1`。关联行数：{"run_members": 2, "alert_assessments": 0, "incident_diagnoses": 0, "result_members": 2}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | C1.executor / stage / execution_plan | completed | — | 8ba0fd0c-8edc-43f7-81e3-3c5c14f702ca | {"rows": null, "error": null} |
| 2 | C2 / stage / baseline_background_enrichment | completed | f2725205-28f0-4908-a042-a283550dcee3 | e69a0b70-7431-4a77-afde-4f0b4d4d0593 | {"rows": null, "error": null} |
| 3 | C2 / tool / assets | completed | 951b1191-db79-44b2-b4ea-0cf232e6f608 | b149c18b-0f05-4f60-ac67-9c01d95d9694 | {"rows": 0, "error": null} |
| 4 | C2 / tool / history | completed | 43c7e149-9fad-46d6-b01a-b7c30aabfbf6 | bb107f2f-e2f2-454b-9694-747748447485 | {"rows": 0, "error": null} |
| 5 | C2 / tool / threat_intel | skipped | 55532f09-cb33-4ece-b0ed-92219e9f4b51 | bd05c9ca-aedb-4c46-ac11-4663dda1e77b | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:04:19.962438+00:00"}} |
| 6 | C2 / tool / ueba | skipped | 299f0a89-9676-4a69-b4fd-5d8bba6f9938 | 20500056-a8d3-416f-a33f-500bde6b5763 | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:04:19.979493+00:00"}} |
| 7 | C2 / tool / knowledge | skipped | 415005ac-c395-4d1e-8c13-9e695b321d89 | 64299f13-035b-4eb5-b97d-6eb3459a257f | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:04:19.996675+00:00"}} |
| 8 | C2 / tool / graph | skipped | e4826759-b65b-4cfd-a2cc-6c534d7783df | 61407fb9-9d33-4ee6-b20b-fa58700db3c2 | {"rows": null, "error": {"code": "source_not_connected", "message": "source_not_connected", "retryable": false, "occurred_at": "2026-11-05T00:04:20.012741+00:00"}} |
| 9 | C3 / stage / initial_main_and_domain_analysis | failed | a85f5c11-5c01-4638-8c6a-040e0b3c18db | c57563f7-51d5-4662-8f97-fb665a7a9cc8 | {"rows": null, "error": {"code": "domain_finding_scope_mismatch", "message": "domain_finding_scope_mismatch", "retryable": false, "occurred_at": "2026-11-05T00:04:30.039320+00:00"}} |
| 10 | C3 / model / main_with_domain_views | failed | f8b909df-82aa-4f9b-af2c-181f3cf7849f | 8264e751-fa27-41d0-a2b6-07c22ec9630f | {"rows": null, "error": {"code": "domain_finding_scope_mismatch", "message": "domain_finding_scope_mismatch", "retryable": false, "occurred_at": "2026-11-05T00:04:30.039320+00:00"}} |
| 11 | C4.materials / stage / frozen_material_semantics | completed | — | 45db78d8-c191-46b7-8fa9-bdeac597621b | {"rows": null, "error": null} |
| 12 | C5 / graph / 0dfd489835c5a608de930ded5b51b85024d0f8ad9f8fdefaa382cadcab214d42 | completed | f2725205-28f0-4908-a042-a283550dcee3 | a4aa658d-8ee0-4051-bd14-a1044edead0d | {"rows": null, "error": null} |
| 13 | C4.routing / stage / followup_dispatch | completed | — | f361bede-5ee4-44e9-a03f-c26dd36e85d0 | {"rows": null, "error": null} |
| 14 | C6 / stage / final_delivery | skipped | 1a1a9505-748d-4ebd-bd90-7806eb33ac48 | 2a6b9f21-4e50-4eaa-a65d-e49e88747608 | {"rows": null, "error": {"code": "no_accepted_main_analysis", "message": "no_accepted_main_analysis", "retryable": false, "occurred_at": "2026-11-05T00:04:30.327040+00:00"}} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| 1a1a9505-748d-4ebd-bd90-7806eb33ac48 | input_snapshot / socai2.page-model.v1 | — |
| f2725205-28f0-4908-a042-a283550dcee3 | source_snapshot / socai2.baseline-context.v1 | — |
| 8ba0fd0c-8edc-43f7-81e3-3c5c14f702ca | source_snapshot / socai2.baseline-executor.v1 | 31b71bfd-0a8d-4c9a-a8ee-34e3c6cd603c |
| 951b1191-db79-44b2-b4ea-0cf232e6f608 | tool_request / socai2.baseline-enrichment.v1 | 1cdd47ba-a391-49b0-9655-19cc67ea621b |
| b149c18b-0f05-4f60-ac67-9c01d95d9694 | tool_response / socai2.baseline-enrichment.v1 | 1cdd47ba-a391-49b0-9655-19cc67ea621b |
| 43c7e149-9fad-46d6-b01a-b7c30aabfbf6 | tool_request / socai2.baseline-enrichment.v1 | dd15ae36-cc5b-400c-bdda-ed269c9936cf |
| bb107f2f-e2f2-454b-9694-747748447485 | tool_response / socai2.baseline-enrichment.v1 | dd15ae36-cc5b-400c-bdda-ed269c9936cf |
| 55532f09-cb33-4ece-b0ed-92219e9f4b51 | tool_request / socai2.baseline-enrichment.v1 | dca7733e-d6e1-4e5b-ae11-a2320e371ba4 |
| bd05c9ca-aedb-4c46-ac11-4663dda1e77b | tool_response / socai2.baseline-enrichment.v1 | dca7733e-d6e1-4e5b-ae11-a2320e371ba4 |
| 299f0a89-9676-4a69-b4fd-5d8bba6f9938 | tool_request / socai2.baseline-enrichment.v1 | 75418224-90db-4231-90a4-b9f7ad3038cc |
| 20500056-a8d3-416f-a33f-500bde6b5763 | tool_response / socai2.baseline-enrichment.v1 | 75418224-90db-4231-90a4-b9f7ad3038cc |
| 415005ac-c395-4d1e-8c13-9e695b321d89 | tool_request / socai2.baseline-enrichment.v1 | 8b25c986-53d9-4b24-8fd3-e31304407463 |
| 64299f13-035b-4eb5-b97d-6eb3459a257f | tool_response / socai2.baseline-enrichment.v1 | 8b25c986-53d9-4b24-8fd3-e31304407463 |
| e4826759-b65b-4cfd-a2cc-6c534d7783df | tool_request / socai2.baseline-enrichment.v1 | d0e3d76c-684f-464f-9cf5-52274221272d |
| 61407fb9-9d33-4ee6-b20b-fa58700db3c2 | tool_response / socai2.baseline-enrichment.v1 | d0e3d76c-684f-464f-9cf5-52274221272d |
| e69a0b70-7431-4a77-afde-4f0b4d4d0593 | source_snapshot / socai2.baseline-enrichment.v1 | 79655dde-3b0f-46b1-afaf-8d82d0c11a35 |
| a85f5c11-5c01-4638-8c6a-040e0b3c18db | source_snapshot / socai2.baseline-model-view.v4 | — |
| f8b909df-82aa-4f9b-af2c-181f3cf7849f | model_request / socai2.baseline-analysis.v1 | 0f8f0a88-9ce5-4ff9-8290-d2c944a700de |
| 8264e751-fa27-41d0-a2b6-07c22ec9630f | model_response / socai2.baseline-analysis.v1 | 0f8f0a88-9ce5-4ff9-8290-d2c944a700de |
| c57563f7-51d5-4662-8f97-fb665a7a9cc8 | source_snapshot / socai2.baseline-analysis.v1 | 4e03a62e-5384-4278-a2b7-9611fda80362 |
| 45db78d8-c191-46b7-8fa9-bdeac597621b | source_snapshot / socai2.baseline-evidence.v1 | 417cf8a2-0f0f-451d-a21d-faf0ddde5c41 |
| 6ae51566-d24d-4a8c-93d8-522cb4558627 | alert_graph / socai2.baseline-graph.v1 | 67b896cd-c68d-4473-96e3-27fc25773bb7 |
| a4aa658d-8ee0-4051-bd14-a1044edead0d | source_snapshot / socai2.baseline-graph.v1 | 67b896cd-c68d-4473-96e3-27fc25773bb7 |
| f361bede-5ee4-44e9-a03f-c26dd36e85d0 | source_snapshot / socai2.baseline-executor.v1 | fef786e1-532e-43fb-8efa-e793e8e6252f |
| 2a6b9f21-4e50-4eaa-a65d-e49e88747608 | source_snapshot / socai2.baseline-delivery.v1 | b1ef1995-554c-4d4b-96a1-153ebe317e26 |
| 607a2447-7443-455b-8875-e8806857f2bb | report_json / socai2.baseline-delivery.v1 | b1ef1995-554c-4d4b-96a1-153ebe317e26 |
| 06c84763-70ad-41fa-9bdf-d0d087440e5a | source_snapshot / socai2.baseline-delivery.v1 | b1ef1995-554c-4d4b-96a1-153ebe317e26 |
| 4204ea5b-cf8d-4ce2-bbc7-395e701d033d | report_markdown / socai2.baseline-delivery.v1 | b1ef1995-554c-4d4b-96a1-153ebe317e26 |

本轮Case结果：

- `e59ec36f-eb01-41a2-94a0-0c2d7b444994`：conclusion=—；origin=system；validation=system_only；delivery=partial；report_artifact_id=`607a2447-7443-455b-8875-e8806857f2bb`。

<a id="run-5"></a>
## 5. Process command observed · alert_basic

Run：`f8387216-3841-5924-afcd-1879894c7b78`；对象：`f42fdc14-f1c8-5589-837a-a4a3b2bf95c0`。

状态：`completed`；停止：`stage_output_saved`；交付：`partial`。请求 `2026-11-05T00:04:52.087233+00:00`，开始 `2026-11-05T00:04:52.087233+00:00`，结束 `2026-11-05T00:04:55.600504+00:00`。

冻结输入：`4a9c9ed6-e2e0-4a18-b54c-b1d37c527eee`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 1, "incident_diagnoses": 0, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | A / stage / alert_basic_analysis | completed | — | 73b653eb-f696-5469-912c-daa7b2309019 | {"rows": null, "error": null} |
| 2 | A / tool / assets | completed | dac52a44-d56c-4582-8681-ddd2e4931de1 | 814d8234-e88c-44b3-baf1-44d0b834250c | {"rows": 0, "error": null} |
| 3 | A / tool / history | completed | ce05dcaf-7996-4abb-a3e3-3594cbff6eb4 | c2bdea0c-65e2-4d2a-bccd-56353cf73d8e | {"rows": 0, "error": null} |
| 4 | A / tool / threat_intel | skipped | eee1a469-5a03-4378-8148-4ba51b299f23 | 6459a27e-89ad-4ca2-879c-8846328cbdea | {"rows": null, "error": {"code": "no_supported_frozen_objects", "message": "no_supported_frozen_objects", "retryable": false, "occurred_at": "2026-11-05T00:04:52.164016+00:00"}} |
| 5 | A / model / alert_triage_and_explanation | completed | ab3467fd-f46e-4e5e-b84a-088618d81e5a | 7b4c53d9-99e0-485e-9c1b-471cfebb5b4c | {"rows": null, "error": null} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| 4a9c9ed6-e2e0-4a18-b54c-b1d37c527eee | input_snapshot / socai2.stage-result.v1 | — |
| dac52a44-d56c-4582-8681-ddd2e4931de1 | tool_request / socai2.alert-basic-executor.v3 | 778d152c-b805-4e0d-bfba-bb261598105a |
| 814d8234-e88c-44b3-baf1-44d0b834250c | tool_response / socai2.alert-basic-executor.v3 | 778d152c-b805-4e0d-bfba-bb261598105a |
| ce05dcaf-7996-4abb-a3e3-3594cbff6eb4 | tool_request / socai2.alert-basic-executor.v3 | c02505da-8f66-4b65-8ea9-8d5f10382207 |
| c2bdea0c-65e2-4d2a-bccd-56353cf73d8e | tool_response / socai2.alert-basic-executor.v3 | c02505da-8f66-4b65-8ea9-8d5f10382207 |
| eee1a469-5a03-4378-8148-4ba51b299f23 | tool_request / socai2.alert-basic-executor.v3 | dd6004f8-f954-4cc2-aa51-75b489da985a |
| 6459a27e-89ad-4ca2-879c-8846328cbdea | tool_response / socai2.alert-basic-executor.v3 | dd6004f8-f954-4cc2-aa51-75b489da985a |
| ab3467fd-f46e-4e5e-b84a-088618d81e5a | model_request / socai2.alert-basic-executor.v3 | a651cb04-129b-47ac-b646-82c9a101216f |
| 7b4c53d9-99e0-485e-9c1b-471cfebb5b4c | model_response / socai2.alert-basic-executor.v3 | a651cb04-129b-47ac-b646-82c9a101216f |
| 73b653eb-f696-5469-912c-daa7b2309019 | source_snapshot / socai2.stage-result.v1 | — |
| bac86385-0bdd-5619-8651-1c5ad6f7967a | alert_explanation / socai2.stage-result.v1 | — |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-6"></a>
## 6. Outbound connection observed · alert_basic

Run：`89983e22-f835-533b-a194-f783eb0d7483`；对象：`890f55b6-8330-5136-9af6-a3bc3ce96c1c`。

状态：`completed`；停止：`stage_output_saved`；交付：`partial`。请求 `2026-11-05T00:04:55.637279+00:00`，开始 `2026-11-05T00:04:55.637279+00:00`，结束 `2026-11-05T00:04:58.132574+00:00`。

冻结输入：`4d8c0bce-59e7-458f-b312-e3f89946a716`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 1, "incident_diagnoses": 0, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | A / stage / alert_basic_analysis | completed | — | c30e03dc-3e60-5629-a8b3-a1ec3cfff786 | {"rows": null, "error": null} |
| 2 | A / tool / assets | completed | f9ab85a5-e0da-4f5e-9ee6-6877fce2fdd1 | 770ec839-0a4f-49ab-bc44-6c5cf3e22842 | {"rows": 0, "error": null} |
| 3 | A / tool / history | completed | 38bb9796-98b3-4f2b-ac2f-e422cde2a8c9 | 206c72bf-d3ab-49ea-bd22-bbe6a3583129 | {"rows": 1, "error": null} |
| 4 | A / tool / threat_intel | completed | c0006a7f-a1c4-45e8-b183-467d56cfdba5 | 3d785809-7cea-4432-96fa-0424755aa8e2 | {"rows": 0, "error": null} |
| 5 | A / model / alert_triage_and_explanation | completed | 6502a4e3-9b0d-4b0f-9efe-19e7b60cda2f | 94dac1c6-3e87-494f-bef9-ab5131f96369 | {"rows": null, "error": null} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| 4d8c0bce-59e7-458f-b312-e3f89946a716 | input_snapshot / socai2.stage-result.v1 | — |
| f9ab85a5-e0da-4f5e-9ee6-6877fce2fdd1 | tool_request / socai2.alert-basic-executor.v3 | 4856b70d-febd-4c19-977d-aaea436000c8 |
| 770ec839-0a4f-49ab-bc44-6c5cf3e22842 | tool_response / socai2.alert-basic-executor.v3 | 4856b70d-febd-4c19-977d-aaea436000c8 |
| 38bb9796-98b3-4f2b-ac2f-e422cde2a8c9 | tool_request / socai2.alert-basic-executor.v3 | e6a5112d-a717-423c-829a-668ac1ebcae8 |
| 206c72bf-d3ab-49ea-bd22-bbe6a3583129 | tool_response / socai2.alert-basic-executor.v3 | e6a5112d-a717-423c-829a-668ac1ebcae8 |
| c0006a7f-a1c4-45e8-b183-467d56cfdba5 | tool_request / socai2.alert-basic-executor.v3 | 2f0e720f-aa55-4b3e-91a0-ffe93e12506b |
| 3d785809-7cea-4432-96fa-0424755aa8e2 | tool_response / socai2.alert-basic-executor.v3 | 2f0e720f-aa55-4b3e-91a0-ffe93e12506b |
| 6502a4e3-9b0d-4b0f-9efe-19e7b60cda2f | model_request / socai2.alert-basic-executor.v3 | 03edb11d-ed1b-41e1-919a-581881303eeb |
| 94dac1c6-3e87-494f-bef9-ab5131f96369 | model_response / socai2.alert-basic-executor.v3 | 03edb11d-ed1b-41e1-919a-581881303eeb |
| 282fb575-fa85-59b7-bc9f-21471847bd4d | alert_explanation / socai2.stage-result.v1 | — |
| c30e03dc-3e60-5629-a8b3-a1ec3cfff786 | source_snapshot / socai2.stage-result.v1 | — |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-7"></a>
## 7. 关联事件 · Process command observed · incident_diagnosis

Run：`fd8f79ef-bec2-5071-bb9e-eb394079c008`；对象：`bdd4f231-53e3-4ee6-be40-c5157d4db798`。

状态：`completed`；停止：`stage_output_saved`；交付：`partial`。请求 `2026-11-05T00:04:58.207132+00:00`，开始 `2026-11-05T00:04:58.207132+00:00`，结束 `2026-11-05T00:05:07.131341+00:00`。

冻结输入：`22429762-3ff4-4636-9e25-9c3b0b28ca85`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 0, "incident_diagnoses": 1, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | I / stage / incident_member_synthesis | completed | — | b29afd2f-35b4-51e9-9728-5ac6cbe841db | {"rows": null, "error": null} |
| 2 | I / model / incident_member_synthesis | completed | e3147500-5dbe-45d6-8813-c9e0e0e927ab | 1b5faf3a-4817-4423-ac52-3775d559b892 | {"rows": null, "error": null} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| 22429762-3ff4-4636-9e25-9c3b0b28ca85 | input_snapshot / socai2.stage-result.v1 | — |
| e3147500-5dbe-45d6-8813-c9e0e0e927ab | model_request / socai2.incident-diagnosis-executor.v3 | 972c9dca-e516-42d5-bf91-b4c478a4ff08 |
| 1b5faf3a-4817-4423-ac52-3775d559b892 | model_response / socai2.incident-diagnosis-executor.v3 | 972c9dca-e516-42d5-bf91-b4c478a4ff08 |
| b29afd2f-35b4-51e9-9728-5ac6cbe841db | source_snapshot / socai2.stage-result.v1 | — |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-8"></a>
## 8. Endpoint activity review · baseline

Run：`4d8356ef-64fa-4331-ad97-34e58eeaf8da`；对象：`86a41b59-5a15-579d-b11f-9a90ae6edf3b`。

状态：`failed`；停止：`required_model_input_unavailable`；交付：`partial`。请求 `2026-11-05T00:05:07.193672+00:00`，开始 `2026-11-05T00:05:07.249282+00:00`，结束 `2026-11-05T00:05:18.289464+00:00`。

冻结输入：`476d3951-872f-419b-b0c1-cfe47689cc0f`；范围版本：`1`。关联行数：{"run_members": 2, "alert_assessments": 0, "incident_diagnoses": 0, "result_members": 2}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | C1.executor / stage / execution_plan | completed | — | e624d5c4-818d-49cb-873b-20258cbaeeca | {"rows": null, "error": null} |
| 2 | C2 / stage / baseline_background_enrichment | completed | a471e1fd-bff6-4c54-a125-a2cb95f23e67 | e8450198-c007-4a42-8b8b-7d5effd51475 | {"rows": null, "error": null} |
| 3 | C2 / tool / assets | completed | a0761222-2935-46e3-a138-a962784e3336 | 7d56e738-7929-4e55-9c1f-81db43ed3424 | {"rows": 0, "error": null} |
| 4 | C2 / tool / history | completed | dd8a450b-7bc3-4b87-80b9-0e3e402b7121 | d3d09c55-9a73-4ba8-acd6-f326f0bc2d44 | {"rows": 0, "error": null} |
| 5 | C2 / tool / threat_intel | skipped | 9599c830-81d2-4cc1-ba39-c3056c8e275b | ee8d18b0-6b38-4762-a09d-de95af13df9c | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:05:07.369274+00:00"}} |
| 6 | C2 / tool / ueba | skipped | 20deca1f-a0a9-4e71-a7eb-4acf723a9308 | 009de1ab-b0bb-42a8-8587-9bfff48e7e25 | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:05:07.385693+00:00"}} |
| 7 | C2 / tool / knowledge | skipped | cbfbffbc-cf0b-4886-a4cb-caa24d8c8f59 | 38e992ef-231c-4626-9327-47bc81b25be2 | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:05:07.401830+00:00"}} |
| 8 | C2 / tool / graph | skipped | cf8b6576-864e-4fda-b5c8-a8e5484045be | 16088657-0cce-4039-8f7e-6b497425a468 | {"rows": null, "error": {"code": "source_not_connected", "message": "source_not_connected", "retryable": false, "occurred_at": "2026-11-05T00:05:07.419156+00:00"}} |
| 9 | C3 / stage / initial_main_and_domain_analysis | completed | 542dfc99-db48-458a-99fe-922f074017c6 | 112e98d9-a8ee-412a-a675-2d12a46a5bc7 | {"rows": null, "error": null} |
| 10 | C3 / model / main_with_domain_views | completed | 3f1ef483-ff8b-46e8-8850-0f133590b916 | 0df3c017-2456-4621-be0a-361a43523110 | {"rows": null, "error": null} |
| 11 | C4.materials / stage / frozen_material_semantics | completed | — | 462940f0-7b51-43c5-b970-be095063a011 | {"rows": null, "error": null} |
| 12 | C5 / graph / 87216aada1a3c453b4ea9c1c362680805ed1ba99ac4203ea95e1deb787246488 | completed | a471e1fd-bff6-4c54-a125-a2cb95f23e67 | e689e73d-0ed0-48ce-bf01-c0128ec0e8c5 | {"rows": null, "error": null} |
| 13 | C4.routing / stage / followup_dispatch | completed | — | 10e9cd54-dbbb-458e-9529-c3b6b87d604d | {"rows": null, "error": null} |
| 14 | C6 / stage / final_delivery | skipped | 476d3951-872f-419b-b0c1-cfe47689cc0f | 1c2caac1-22a5-4a2c-941b-606f4f920d6a | {"rows": null, "error": {"code": "required_model_input_unavailable", "message": "required_model_input_unavailable", "retryable": false, "occurred_at": "2026-11-05T00:05:18.266321+00:00"}} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| 476d3951-872f-419b-b0c1-cfe47689cc0f | input_snapshot / socai2.page-model.v1 | — |
| a471e1fd-bff6-4c54-a125-a2cb95f23e67 | source_snapshot / socai2.baseline-context.v1 | — |
| e624d5c4-818d-49cb-873b-20258cbaeeca | source_snapshot / socai2.baseline-executor.v1 | 940e3cfa-3ec1-46a8-9ca4-eb79dbf09461 |
| a0761222-2935-46e3-a138-a962784e3336 | tool_request / socai2.baseline-enrichment.v1 | 47fd7ef9-a536-4e8b-98c2-c13d6a20d072 |
| 7d56e738-7929-4e55-9c1f-81db43ed3424 | tool_response / socai2.baseline-enrichment.v1 | 47fd7ef9-a536-4e8b-98c2-c13d6a20d072 |
| dd8a450b-7bc3-4b87-80b9-0e3e402b7121 | tool_request / socai2.baseline-enrichment.v1 | 605ad56a-5ceb-45f2-94fb-25e2258d015e |
| d3d09c55-9a73-4ba8-acd6-f326f0bc2d44 | tool_response / socai2.baseline-enrichment.v1 | 605ad56a-5ceb-45f2-94fb-25e2258d015e |
| 9599c830-81d2-4cc1-ba39-c3056c8e275b | tool_request / socai2.baseline-enrichment.v1 | b6b570c1-56a7-475c-8a3b-564610355a92 |
| ee8d18b0-6b38-4762-a09d-de95af13df9c | tool_response / socai2.baseline-enrichment.v1 | b6b570c1-56a7-475c-8a3b-564610355a92 |
| 20deca1f-a0a9-4e71-a7eb-4acf723a9308 | tool_request / socai2.baseline-enrichment.v1 | d77bbcde-ba22-4be2-b519-2776653735c2 |
| 009de1ab-b0bb-42a8-8587-9bfff48e7e25 | tool_response / socai2.baseline-enrichment.v1 | d77bbcde-ba22-4be2-b519-2776653735c2 |
| cbfbffbc-cf0b-4886-a4cb-caa24d8c8f59 | tool_request / socai2.baseline-enrichment.v1 | 0dd5b126-a9c8-4aa1-9696-35d77cf9066c |
| 38e992ef-231c-4626-9327-47bc81b25be2 | tool_response / socai2.baseline-enrichment.v1 | 0dd5b126-a9c8-4aa1-9696-35d77cf9066c |
| cf8b6576-864e-4fda-b5c8-a8e5484045be | tool_request / socai2.baseline-enrichment.v1 | 5d458153-f3d9-46ac-99c1-65929c91f415 |
| 16088657-0cce-4039-8f7e-6b497425a468 | tool_response / socai2.baseline-enrichment.v1 | 5d458153-f3d9-46ac-99c1-65929c91f415 |
| e8450198-c007-4a42-8b8b-7d5effd51475 | source_snapshot / socai2.baseline-enrichment.v1 | 4e44d6e9-51c9-454d-b7d9-7422b17e5ec3 |
| 542dfc99-db48-458a-99fe-922f074017c6 | source_snapshot / socai2.baseline-model-view.v4 | — |
| 3f1ef483-ff8b-46e8-8850-0f133590b916 | model_request / socai2.baseline-analysis.v1 | 0c35f976-2e8d-4486-9016-0f09d967d8cc |
| 0df3c017-2456-4621-be0a-361a43523110 | model_response / socai2.baseline-analysis.v1 | 0c35f976-2e8d-4486-9016-0f09d967d8cc |
| 0ae65286-e8e4-4709-8aa7-5e33e3334b40 | domain_analysis / socai2.baseline-analysis.v1 | 0c35f976-2e8d-4486-9016-0f09d967d8cc |
| fc77c87c-4058-4f7e-8df9-614b3cf03858 | domain_analysis / socai2.baseline-analysis.v1 | 0c35f976-2e8d-4486-9016-0f09d967d8cc |
| 685170f9-a458-4f73-ae73-959661a6f497 | domain_analysis / socai2.baseline-analysis.v1 | 0c35f976-2e8d-4486-9016-0f09d967d8cc |
| bd5ef6dd-16e2-4f08-965b-5a8e6c145ea9 | domain_analysis / socai2.baseline-analysis.v1 | 0c35f976-2e8d-4486-9016-0f09d967d8cc |
| 112e98d9-a8ee-412a-a675-2d12a46a5bc7 | source_snapshot / socai2.baseline-analysis.v1 | 08648fe3-e473-4fa7-b000-db570d467dbb |
| 462940f0-7b51-43c5-b970-be095063a011 | source_snapshot / socai2.baseline-evidence.v1 | fffadc01-e722-4aab-bbc0-93962ea0c23b |
| ccdea6d2-8016-48f6-934c-f1195fb82c04 | alert_graph / socai2.baseline-graph.v1 | c356ca67-cbde-4198-a413-ed306e2dcdef |
| e689e73d-0ed0-48ce-bf01-c0128ec0e8c5 | source_snapshot / socai2.baseline-graph.v1 | c356ca67-cbde-4198-a413-ed306e2dcdef |
| 10e9cd54-dbbb-458e-9529-c3b6b87d604d | source_snapshot / socai2.baseline-executor.v1 | b480190f-58ab-42ff-a9c0-a01fa9bfb973 |
| ae6320c2-047c-45fa-ac40-8712829f5191 | source_snapshot / socai2.baseline-evidence.v1 | — |
| 1c2caac1-22a5-4a2c-941b-606f4f920d6a | source_snapshot / socai2.baseline-delivery.v1 | 5fcff980-9f38-40be-8294-cc8289bf38d3 |
| e727f5bc-1b87-4b17-bdcd-8bac3e93e197 | report_json / socai2.baseline-delivery.v1 | 5fcff980-9f38-40be-8294-cc8289bf38d3 |
| f73f56ab-ffc2-4c95-8327-29685f8c8321 | source_snapshot / socai2.baseline-delivery.v1 | 5fcff980-9f38-40be-8294-cc8289bf38d3 |
| ff1b7e7e-9986-45b6-b3b9-f0402f3f5135 | report_markdown / socai2.baseline-delivery.v1 | 5fcff980-9f38-40be-8294-cc8289bf38d3 |

本轮Case结果：

- `dcac0281-8977-4963-b3e3-d7150e4b9e0f`：conclusion=—；origin=system；validation=system_only；delivery=partial；report_artifact_id=`e727f5bc-1b87-4b17-bdcd-8bac3e93e197`。

<a id="run-9"></a>
## 9. Process command observed · alert_basic

Run：`55f49792-8e11-5419-91d3-f207123dfbc5`；对象：`d8383265-a5fd-5e15-a9a7-75f6dec8d51a`。

状态：`completed`；停止：`stage_output_saved`；交付：`partial`。请求 `2026-11-05T00:06:04.435451+00:00`，开始 `2026-11-05T00:06:04.435451+00:00`，结束 `2026-11-05T00:06:07.51996+00:00`。

冻结输入：`f1834b96-c1aa-4d74-a164-328529c66ec5`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 1, "incident_diagnoses": 0, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | A / stage / alert_basic_analysis | completed | — | eb0602dc-b73b-509a-9310-213029318087 | {"rows": null, "error": null} |
| 2 | A / tool / assets | completed | 8a8dbe58-009c-4a64-9c1b-a5dc261af7da | 9fe09c07-a6ce-45d6-b2b0-bfe149d51590 | {"rows": 0, "error": null} |
| 3 | A / tool / history | completed | 025ba7f6-e224-4813-9103-11a047a28bbc | f25cbc9d-4d91-43db-834f-eaeba9b0b505 | {"rows": 0, "error": null} |
| 4 | A / tool / threat_intel | skipped | 3e48b25e-cfb9-4866-bcf3-a8acd729517a | 4144be19-647f-427a-b5fc-e55506b3d926 | {"rows": null, "error": {"code": "no_supported_frozen_objects", "message": "no_supported_frozen_objects", "retryable": false, "occurred_at": "2026-11-05T00:06:04.515829+00:00"}} |
| 5 | A / model / alert_triage_and_explanation | completed | 6b31045b-36e9-478c-897d-a398d76623d6 | 3050a783-5b4c-40d8-947b-d154c3f86601 | {"rows": null, "error": null} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| f1834b96-c1aa-4d74-a164-328529c66ec5 | input_snapshot / socai2.stage-result.v1 | — |
| 8a8dbe58-009c-4a64-9c1b-a5dc261af7da | tool_request / socai2.alert-basic-executor.v3 | faf8cd13-13e6-4b3a-92a4-f36ce10c66a7 |
| 9fe09c07-a6ce-45d6-b2b0-bfe149d51590 | tool_response / socai2.alert-basic-executor.v3 | faf8cd13-13e6-4b3a-92a4-f36ce10c66a7 |
| 025ba7f6-e224-4813-9103-11a047a28bbc | tool_request / socai2.alert-basic-executor.v3 | 58e6619a-2d18-4de0-8479-d394bbe8ca2f |
| f25cbc9d-4d91-43db-834f-eaeba9b0b505 | tool_response / socai2.alert-basic-executor.v3 | 58e6619a-2d18-4de0-8479-d394bbe8ca2f |
| 3e48b25e-cfb9-4866-bcf3-a8acd729517a | tool_request / socai2.alert-basic-executor.v3 | 7bdba46f-017a-4927-895e-beca59f860e5 |
| 4144be19-647f-427a-b5fc-e55506b3d926 | tool_response / socai2.alert-basic-executor.v3 | 7bdba46f-017a-4927-895e-beca59f860e5 |
| 6b31045b-36e9-478c-897d-a398d76623d6 | model_request / socai2.alert-basic-executor.v3 | 3cd2ecc5-15fe-4494-a5a4-0c050312ab75 |
| 3050a783-5b4c-40d8-947b-d154c3f86601 | model_response / socai2.alert-basic-executor.v3 | 3cd2ecc5-15fe-4494-a5a4-0c050312ab75 |
| 4bcd68a4-9215-556b-9987-4f7774607fe6 | alert_explanation / socai2.stage-result.v1 | — |
| eb0602dc-b73b-509a-9310-213029318087 | source_snapshot / socai2.stage-result.v1 | — |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-10"></a>
## 10. Outbound connection observed · alert_basic

Run：`c17fa3dc-f51a-5bd8-b05c-419070d59ac1`；对象：`408787c3-4205-5332-86de-432daf06351c`。

状态：`completed`；停止：`stage_output_saved`；交付：`partial`。请求 `2026-11-05T00:06:07.557684+00:00`，开始 `2026-11-05T00:06:07.557684+00:00`，结束 `2026-11-05T00:06:10.306353+00:00`。

冻结输入：`c58a3f7c-774e-4c7c-8fe1-7486eebc160f`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 1, "incident_diagnoses": 0, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | A / stage / alert_basic_analysis | completed | — | 062a54dd-175d-54f4-b7c4-e80974398aee | {"rows": null, "error": null} |
| 2 | A / tool / assets | completed | 3f90fab0-b967-4438-a48f-2a2db0f7567d | 63e51543-ddd9-4602-9ca0-25c4423e1e95 | {"rows": 0, "error": null} |
| 3 | A / tool / history | completed | 9489fd0f-168e-4be4-a2d4-2fe210989843 | 839a4dd6-72ee-4fbc-921f-be907f9b6106 | {"rows": 1, "error": null} |
| 4 | A / tool / threat_intel | completed | fb331fca-cae6-48a5-a985-2ea749706a6a | 8eed609f-b7dd-4c51-8f94-13575b7b6487 | {"rows": 0, "error": null} |
| 5 | A / model / alert_triage_and_explanation | completed | a5f35bb0-6200-4469-9446-9f4e95b242ff | e168ab80-b2b0-478a-bd80-54cce9eb8a93 | {"rows": null, "error": null} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| c58a3f7c-774e-4c7c-8fe1-7486eebc160f | input_snapshot / socai2.stage-result.v1 | — |
| 3f90fab0-b967-4438-a48f-2a2db0f7567d | tool_request / socai2.alert-basic-executor.v3 | e65d7377-9bd4-4f05-a96e-d673694a9e50 |
| 63e51543-ddd9-4602-9ca0-25c4423e1e95 | tool_response / socai2.alert-basic-executor.v3 | e65d7377-9bd4-4f05-a96e-d673694a9e50 |
| 9489fd0f-168e-4be4-a2d4-2fe210989843 | tool_request / socai2.alert-basic-executor.v3 | 7f0c3fbe-251f-4124-b3eb-b7a67cad397d |
| 839a4dd6-72ee-4fbc-921f-be907f9b6106 | tool_response / socai2.alert-basic-executor.v3 | 7f0c3fbe-251f-4124-b3eb-b7a67cad397d |
| fb331fca-cae6-48a5-a985-2ea749706a6a | tool_request / socai2.alert-basic-executor.v3 | fce6db85-27d8-4344-98f3-cdd09d25a05d |
| 8eed609f-b7dd-4c51-8f94-13575b7b6487 | tool_response / socai2.alert-basic-executor.v3 | fce6db85-27d8-4344-98f3-cdd09d25a05d |
| a5f35bb0-6200-4469-9446-9f4e95b242ff | model_request / socai2.alert-basic-executor.v3 | a505e381-faa4-427c-a4ca-584a4ecb1b76 |
| e168ab80-b2b0-478a-bd80-54cce9eb8a93 | model_response / socai2.alert-basic-executor.v3 | a505e381-faa4-427c-a4ca-584a4ecb1b76 |
| 062a54dd-175d-54f4-b7c4-e80974398aee | source_snapshot / socai2.stage-result.v1 | — |
| e47b1a83-b0aa-5dcd-9197-d9d76e9a8a03 | alert_explanation / socai2.stage-result.v1 | — |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-11"></a>
## 11. 关联事件 · Process command observed · incident_diagnosis

Run：`12576785-caaa-5f10-9393-47ae297bd72e`；对象：`a4f57efa-4db4-4853-8935-3556db419578`。

状态：`completed`；停止：`stage_output_saved`；交付：`partial`。请求 `2026-11-05T00:06:10.356906+00:00`，开始 `2026-11-05T00:06:10.356906+00:00`，结束 `2026-11-05T00:06:20.54418+00:00`。

冻结输入：`a356d54b-1928-4b81-962f-9677f80d918f`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 0, "incident_diagnoses": 1, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | I / stage / incident_member_synthesis | completed | — | a05aa673-9c71-5776-87d1-46ec3f3e8e18 | {"rows": null, "error": null} |
| 2 | I / model / incident_member_synthesis | completed | 28ce923d-5e69-4919-be76-bce64428d65d | 2120d481-56bf-4d1a-b00c-851f75ab8da9 | {"rows": null, "error": null} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| a356d54b-1928-4b81-962f-9677f80d918f | input_snapshot / socai2.stage-result.v1 | — |
| 28ce923d-5e69-4919-be76-bce64428d65d | model_request / socai2.incident-diagnosis-executor.v3 | 3c46b73f-e7cf-4058-8e02-5447be34a080 |
| 2120d481-56bf-4d1a-b00c-851f75ab8da9 | model_response / socai2.incident-diagnosis-executor.v3 | 3c46b73f-e7cf-4058-8e02-5447be34a080 |
| a05aa673-9c71-5776-87d1-46ec3f3e8e18 | source_snapshot / socai2.stage-result.v1 | — |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-12"></a>
## 12. Endpoint activity review · baseline

Run：`44a7863a-5edb-4cab-9480-17b4b0c12121`；对象：`7d351a36-62cd-535f-8a2a-7000debeed6f`。

状态：`failed`；停止：`required_model_input_unavailable`；交付：`partial`。请求 `2026-11-05T00:06:20.609935+00:00`，开始 `2026-11-05T00:06:20.661876+00:00`，结束 `2026-11-05T00:06:33.823221+00:00`。

冻结输入：`a582b83d-9988-43ee-ac54-c571609467ac`；范围版本：`1`。关联行数：{"run_members": 2, "alert_assessments": 0, "incident_diagnoses": 0, "result_members": 2}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | C1.executor / stage / execution_plan | completed | — | 37607f65-471c-48a8-b3f4-cf540d2af624 | {"rows": null, "error": null} |
| 2 | C2 / stage / baseline_background_enrichment | completed | e1fc7344-0570-47bb-84dc-5f4f9bb4f0e9 | 1913f9c3-9295-4838-9dfa-85219967f6dd | {"rows": null, "error": null} |
| 3 | C2 / tool / assets | completed | 78201f47-a7e8-423f-a456-f97e469465a4 | d5d87cee-03d5-473d-9434-66908a4a967b | {"rows": 0, "error": null} |
| 4 | C2 / tool / history | completed | bc365c21-39e2-4820-8482-876d98aaf476 | e2b0ff44-ac80-4dcb-997e-bb28dcf1e927 | {"rows": 0, "error": null} |
| 5 | C2 / tool / threat_intel | skipped | c84189db-6210-464f-9c64-54356970bbba | fa8e6ed9-043a-48e0-a1bb-7ad731c26933 | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:06:20.775295+00:00"}} |
| 6 | C2 / tool / ueba | skipped | e8a3aec4-3a57-4b98-914a-8d7f06e8b3e0 | c659a5ef-7346-4020-bf85-3fe4f290c206 | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:06:20.790972+00:00"}} |
| 7 | C2 / tool / knowledge | skipped | d8c3bdda-0896-4cc3-b086-38c99a223cba | faac3e44-0912-4ced-a380-0134304f565a | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:06:20.806798+00:00"}} |
| 8 | C2 / tool / graph | skipped | 6dee24ed-fee0-4bd9-ac34-c10d1dbb2f89 | 3c578f98-7e05-4bc3-986a-d2f415e45700 | {"rows": null, "error": {"code": "source_not_connected", "message": "source_not_connected", "retryable": false, "occurred_at": "2026-11-05T00:06:20.822891+00:00"}} |
| 9 | C3 / stage / initial_main_and_domain_analysis | completed | 95872890-3f67-48ac-a693-d665b60d61ef | 1fe5debd-35ca-4be3-abc5-822161d32e09 | {"rows": null, "error": null} |
| 10 | C3 / model / main_with_domain_views | completed | 0d537757-f4dc-43da-872a-dab3437e5295 | 6353424a-71b4-4210-ab0c-1d2711037109 | {"rows": null, "error": null} |
| 11 | C4.materials / stage / frozen_material_semantics | completed | — | e6817422-95c0-43a5-b25e-c0b772da1fcb | {"rows": null, "error": null} |
| 12 | C4.deep / stage / question_deep | completed | 1fe5debd-35ca-4be3-abc5-822161d32e09 | 4d76b3a4-0b5c-40e7-944f-085440676875 | {"rows": null, "error": {"code": "model_token_budget_insufficient", "message": "model_token_budget_insufficient", "retryable": false, "occurred_at": "2026-11-05T00:06:33.626890+00:00"}} |
| 13 | C4.deep / model / bounded_reasoning_step | completed | 6463c174-62c9-4e50-bb3b-80e6cf60a28d | f9e6a4b1-4cd0-4689-8e25-a5fcaca2348f | {"rows": null, "error": null} |
| 14 | C4.query / tool / 150cdd504dee73a9a5303af411a86269c6d711d83090af1c56602bc51bb96acb | completed | a6d71ae7-ef6d-4dfb-8beb-d8cae59b0262 | 3c522ad2-4fe0-436c-82c4-0bcd6193cac0 | {"rows": 0, "error": null} |
| 15 | C5 / graph / 6573f1c32e53d3ba319e604828a3b6cb8ddf7c62c1f8691f71d2eaacfac8cee8 | completed | e1fc7344-0570-47bb-84dc-5f4f9bb4f0e9 | eefff58f-6ec4-44ad-8a9e-0743fd43ff6a | {"rows": null, "error": null} |
| 16 | C4.routing / stage / followup_dispatch | completed | — | 475bf68d-c12e-45c7-b9f4-9a4cc2e57d0f | {"rows": null, "error": null} |
| 17 | C6 / stage / final_delivery | skipped | a582b83d-9988-43ee-ac54-c571609467ac | c548e36a-55c4-41d7-8cf1-a7848a9b3e0b | {"rows": null, "error": {"code": "required_model_input_unavailable", "message": "required_model_input_unavailable", "retryable": false, "occurred_at": "2026-11-05T00:06:33.798611+00:00"}} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| a582b83d-9988-43ee-ac54-c571609467ac | input_snapshot / socai2.page-model.v1 | — |
| e1fc7344-0570-47bb-84dc-5f4f9bb4f0e9 | source_snapshot / socai2.baseline-context.v1 | — |
| 37607f65-471c-48a8-b3f4-cf540d2af624 | source_snapshot / socai2.baseline-executor.v1 | 0783dabc-cb7b-45d5-b0b9-9d7a87b3e7f1 |
| 78201f47-a7e8-423f-a456-f97e469465a4 | tool_request / socai2.baseline-enrichment.v1 | 7f805174-7e3e-48ca-90dd-cf753aecde80 |
| d5d87cee-03d5-473d-9434-66908a4a967b | tool_response / socai2.baseline-enrichment.v1 | 7f805174-7e3e-48ca-90dd-cf753aecde80 |
| bc365c21-39e2-4820-8482-876d98aaf476 | tool_request / socai2.baseline-enrichment.v1 | 277104af-0d3d-4452-b7c4-f17c31d32151 |
| e2b0ff44-ac80-4dcb-997e-bb28dcf1e927 | tool_response / socai2.baseline-enrichment.v1 | 277104af-0d3d-4452-b7c4-f17c31d32151 |
| c84189db-6210-464f-9c64-54356970bbba | tool_request / socai2.baseline-enrichment.v1 | 488917db-b54b-4268-b9e2-4d6e2317be62 |
| fa8e6ed9-043a-48e0-a1bb-7ad731c26933 | tool_response / socai2.baseline-enrichment.v1 | 488917db-b54b-4268-b9e2-4d6e2317be62 |
| e8a3aec4-3a57-4b98-914a-8d7f06e8b3e0 | tool_request / socai2.baseline-enrichment.v1 | 917c8aa8-bb96-4d79-bdcb-858d4c48b914 |
| c659a5ef-7346-4020-bf85-3fe4f290c206 | tool_response / socai2.baseline-enrichment.v1 | 917c8aa8-bb96-4d79-bdcb-858d4c48b914 |
| d8c3bdda-0896-4cc3-b086-38c99a223cba | tool_request / socai2.baseline-enrichment.v1 | 8a3cda6d-be0f-4a57-9ed4-9fe1c9875324 |
| faac3e44-0912-4ced-a380-0134304f565a | tool_response / socai2.baseline-enrichment.v1 | 8a3cda6d-be0f-4a57-9ed4-9fe1c9875324 |
| 6dee24ed-fee0-4bd9-ac34-c10d1dbb2f89 | tool_request / socai2.baseline-enrichment.v1 | ee28a03b-622e-4fe3-95f0-885ae3bc9574 |
| 3c578f98-7e05-4bc3-986a-d2f415e45700 | tool_response / socai2.baseline-enrichment.v1 | ee28a03b-622e-4fe3-95f0-885ae3bc9574 |
| 1913f9c3-9295-4838-9dfa-85219967f6dd | source_snapshot / socai2.baseline-enrichment.v1 | cba0334c-45b8-4d20-a50c-3ceccdae6229 |
| 95872890-3f67-48ac-a693-d665b60d61ef | source_snapshot / socai2.baseline-model-view.v4 | — |
| 0d537757-f4dc-43da-872a-dab3437e5295 | model_request / socai2.baseline-analysis.v1 | 24eecd87-aacc-4a18-8aad-6860dd8c8623 |
| 6353424a-71b4-4210-ab0c-1d2711037109 | model_response / socai2.baseline-analysis.v1 | 24eecd87-aacc-4a18-8aad-6860dd8c8623 |
| 3f8cfd10-f066-4e60-b3e0-f7bd2226e07c | domain_analysis / socai2.baseline-analysis.v1 | 24eecd87-aacc-4a18-8aad-6860dd8c8623 |
| d925e141-1f50-42e6-a306-5e9ee62300a9 | domain_analysis / socai2.baseline-analysis.v1 | 24eecd87-aacc-4a18-8aad-6860dd8c8623 |
| ca9a0b52-224c-4d6c-8b63-d316c82ad753 | domain_analysis / socai2.baseline-analysis.v1 | 24eecd87-aacc-4a18-8aad-6860dd8c8623 |
| 0039d5ec-3f1f-4841-ac1b-683c99bbeca2 | domain_analysis / socai2.baseline-analysis.v1 | 24eecd87-aacc-4a18-8aad-6860dd8c8623 |
| 1fe5debd-35ca-4be3-abc5-822161d32e09 | source_snapshot / socai2.baseline-analysis.v1 | 6ef2877e-3b3c-4130-99a1-9b5388e564dc |
| e6817422-95c0-43a5-b25e-c0b772da1fcb | source_snapshot / socai2.baseline-evidence.v1 | ec99ee23-78e2-4152-8c5e-dd9fe2d5daa3 |
| c3a2e224-822f-400a-a60a-ae88d9bc277f | source_snapshot / socai2.baseline-evidence.v1 | — |
| 6463c174-62c9-4e50-bb3b-80e6cf60a28d | model_request / socai2.baseline-deep.v1 | 615546ba-0e37-4943-80ed-5a6cd4274052 |
| f9e6a4b1-4cd0-4689-8e25-a5fcaca2348f | model_response / socai2.baseline-deep.v1 | 615546ba-0e37-4943-80ed-5a6cd4274052 |
| a6d71ae7-ef6d-4dfb-8beb-d8cae59b0262 | tool_request / socai2.baseline-evidence.v1 | ad7696c0-9229-4829-bff6-ec0f29dd5a05 |
| 3c522ad2-4fe0-436c-82c4-0bcd6193cac0 | tool_response / socai2.baseline-evidence.v1 | ad7696c0-9229-4829-bff6-ec0f29dd5a05 |
| 530fdc65-2066-4351-8263-c8da7c203fa6 | source_snapshot / socai2.baseline-evidence.v1 | ad7696c0-9229-4829-bff6-ec0f29dd5a05 |
| b3b0087d-effa-4991-a511-92cf0f0c55b4 | source_snapshot / socai2.baseline-evidence.v1 | — |
| 5a2eb228-ed15-4094-9475-5fdb6bed1cbb | deep_analysis / socai2.baseline-deep.v1 | efe1941b-72e1-4ac2-bccc-2437771c47db |
| 4d76b3a4-0b5c-40e7-944f-085440676875 | source_snapshot / socai2.baseline-deep.v1 | efe1941b-72e1-4ac2-bccc-2437771c47db |
| 33750f71-2048-410a-9954-422fea22991b | alert_graph / socai2.baseline-graph.v1 | ea21bc06-9888-40e6-bdca-5fe8f10da146 |
| eefff58f-6ec4-44ad-8a9e-0743fd43ff6a | source_snapshot / socai2.baseline-graph.v1 | ea21bc06-9888-40e6-bdca-5fe8f10da146 |
| 475bf68d-c12e-45c7-b9f4-9a4cc2e57d0f | source_snapshot / socai2.baseline-executor.v1 | 0b14574e-2a1e-47f7-945c-6c971b4084c1 |
| 541b574d-3114-46e9-9afc-ac3d2e288150 | source_snapshot / socai2.baseline-evidence.v1 | — |
| 2edd8b35-4db4-4a60-9ec0-0067d7e37b39 | report_json / socai2.baseline-delivery.v1 | cb707c5a-c9f7-4b4e-9382-a9b6a8471c27 |
| c548e36a-55c4-41d7-8cf1-a7848a9b3e0b | source_snapshot / socai2.baseline-delivery.v1 | cb707c5a-c9f7-4b4e-9382-a9b6a8471c27 |
| e70ca90d-eb27-44fa-8469-e105869075ae | source_snapshot / socai2.baseline-delivery.v1 | cb707c5a-c9f7-4b4e-9382-a9b6a8471c27 |
| d841bd80-9e68-4a4c-9e5f-68f7693ea57c | report_markdown / socai2.baseline-delivery.v1 | cb707c5a-c9f7-4b4e-9382-a9b6a8471c27 |

本轮Case结果：

- `2ae25651-cb82-4141-acca-dc6b9574d03b`：conclusion=—；origin=system；validation=system_only；delivery=partial；report_artifact_id=`2edd8b35-4db4-4a60-9ec0-0067d7e37b39`。

<a id="run-13"></a>
## 13. Endpoint activity review · baseline

Run：`2dbb194b-5cf0-4f04-aa26-c81928d0eb9b`；对象：`3f3b9e7e-227f-59f4-9d50-addf63ac3584`。

状态：`failed`；停止：`required_model_input_unavailable`；交付：`partial`。请求 `2026-11-05T00:07:05.582396+00:00`，开始 `2026-11-05T00:07:05.626114+00:00`，结束 `2026-11-05T00:07:18.291169+00:00`。

冻结输入：`2f24b486-4363-492e-ae37-6fbf0210ec99`；范围版本：`1`。关联行数：{"run_members": 2, "alert_assessments": 0, "incident_diagnoses": 0, "result_members": 2}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | C1.executor / stage / execution_plan | completed | — | 185b1c85-4b5b-43a2-adb0-43068aca2f2f | {"rows": null, "error": null} |
| 2 | C2 / stage / baseline_background_enrichment | completed | 79491677-2298-45be-bece-a9a7113311e7 | 32c3adf3-f832-409e-ac1e-e5e1b3134c7c | {"rows": null, "error": null} |
| 3 | C2 / tool / assets | completed | 243309d5-9f2f-41ac-9253-d11343abd79d | 3fe418f7-2780-4916-9fd5-d77f705b5220 | {"rows": 0, "error": null} |
| 4 | C2 / tool / history | completed | e5b6d33d-d5d9-4e33-954d-55640ed5da66 | 71bbc6f7-205c-4a79-8409-86cbf8a991f9 | {"rows": 0, "error": null} |
| 5 | C2 / tool / threat_intel | skipped | 16b873d2-f53d-4c84-ab6e-cf544c509ee6 | 4aa06142-63d2-4c2e-8619-b091953282ef | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:07:05.738234+00:00"}} |
| 6 | C2 / tool / ueba | skipped | d08e082d-c6c8-404a-a341-3499189fd8a7 | 8112cf63-4e7b-4299-a55c-23dd252518b9 | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:07:05.759470+00:00"}} |
| 7 | C2 / tool / knowledge | skipped | 80a48f0e-ec04-4d7f-b8bb-3f4a13f3ba98 | ca2202e7-d31d-4fe6-9ea0-5ec338b2434b | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:07:05.776122+00:00"}} |
| 8 | C2 / tool / graph | skipped | 60f4354c-2466-4776-a42c-e3553962e45c | fca20c18-e5c7-492a-91db-508248df5914 | {"rows": null, "error": {"code": "source_not_connected", "message": "source_not_connected", "retryable": false, "occurred_at": "2026-11-05T00:07:05.792453+00:00"}} |
| 9 | C3 / stage / initial_main_and_domain_analysis | completed | acdae321-2fc2-4a77-bb68-7a3a6110bac7 | f28d8e84-9162-41fb-9c93-d75d10278f27 | {"rows": null, "error": null} |
| 10 | C3 / model / main_with_domain_views | completed | 3df62cb2-7348-4140-ab75-1fa0e6763dfa | f714c721-f40c-4815-87d1-d8bf1d340006 | {"rows": null, "error": null} |
| 11 | C4.materials / stage / frozen_material_semantics | completed | — | a9767f93-004d-4477-957e-b1771d27bc31 | {"rows": null, "error": null} |
| 12 | C4.deep / stage / question_deep | skipped | f28d8e84-9162-41fb-9c93-d75d10278f27 | 31a40c7f-54b6-4309-9221-098d5bc57d35 | {"rows": null, "error": {"code": "model_token_budget_insufficient", "message": "model_token_budget_insufficient", "retryable": false, "occurred_at": "2026-11-05T00:07:18.090726+00:00"}} |
| 13 | C5 / graph / c811b2449632e6fddb320f089a251625bddf773945cc17c7a6247776c37d12a8 | completed | 79491677-2298-45be-bece-a9a7113311e7 | 39aa058d-b4f0-4f38-b989-54877cb7e548 | {"rows": null, "error": null} |
| 14 | C4.routing / stage / followup_dispatch | completed | — | 71de4219-1a9d-4557-bdec-0c06a5605323 | {"rows": null, "error": null} |
| 15 | C6 / stage / final_delivery | skipped | 2f24b486-4363-492e-ae37-6fbf0210ec99 | 619d7481-eb03-45cc-a69f-6953e5cbf228 | {"rows": null, "error": {"code": "required_model_input_unavailable", "message": "required_model_input_unavailable", "retryable": false, "occurred_at": "2026-11-05T00:07:18.267045+00:00"}} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| 2f24b486-4363-492e-ae37-6fbf0210ec99 | input_snapshot / socai2.page-model.v1 | — |
| 79491677-2298-45be-bece-a9a7113311e7 | source_snapshot / socai2.baseline-context.v1 | — |
| 185b1c85-4b5b-43a2-adb0-43068aca2f2f | source_snapshot / socai2.baseline-executor.v1 | 6cfcd1f6-dd0c-42be-b1fb-0cead49e0e1d |
| 243309d5-9f2f-41ac-9253-d11343abd79d | tool_request / socai2.baseline-enrichment.v1 | 79c7532a-88f9-463b-b4f1-0e76b3476285 |
| 3fe418f7-2780-4916-9fd5-d77f705b5220 | tool_response / socai2.baseline-enrichment.v1 | 79c7532a-88f9-463b-b4f1-0e76b3476285 |
| e5b6d33d-d5d9-4e33-954d-55640ed5da66 | tool_request / socai2.baseline-enrichment.v1 | 0631d4b4-6a2f-4ca1-b589-545aae16435b |
| 71bbc6f7-205c-4a79-8409-86cbf8a991f9 | tool_response / socai2.baseline-enrichment.v1 | 0631d4b4-6a2f-4ca1-b589-545aae16435b |
| 16b873d2-f53d-4c84-ab6e-cf544c509ee6 | tool_request / socai2.baseline-enrichment.v1 | c0182559-7677-4382-ba10-a12d80b40ab5 |
| 4aa06142-63d2-4c2e-8619-b091953282ef | tool_response / socai2.baseline-enrichment.v1 | c0182559-7677-4382-ba10-a12d80b40ab5 |
| d08e082d-c6c8-404a-a341-3499189fd8a7 | tool_request / socai2.baseline-enrichment.v1 | 6763b721-8311-4e35-b76c-da08f4513ae6 |
| 8112cf63-4e7b-4299-a55c-23dd252518b9 | tool_response / socai2.baseline-enrichment.v1 | 6763b721-8311-4e35-b76c-da08f4513ae6 |
| 80a48f0e-ec04-4d7f-b8bb-3f4a13f3ba98 | tool_request / socai2.baseline-enrichment.v1 | d47f23ff-6fa7-4d1c-a725-7e39af2c590e |
| ca2202e7-d31d-4fe6-9ea0-5ec338b2434b | tool_response / socai2.baseline-enrichment.v1 | d47f23ff-6fa7-4d1c-a725-7e39af2c590e |
| 60f4354c-2466-4776-a42c-e3553962e45c | tool_request / socai2.baseline-enrichment.v1 | 827453fe-3568-4b18-bef4-4f64fad0731d |
| fca20c18-e5c7-492a-91db-508248df5914 | tool_response / socai2.baseline-enrichment.v1 | 827453fe-3568-4b18-bef4-4f64fad0731d |
| 32c3adf3-f832-409e-ac1e-e5e1b3134c7c | source_snapshot / socai2.baseline-enrichment.v1 | 737c88da-7a8d-4b59-901a-335c160daeba |
| acdae321-2fc2-4a77-bb68-7a3a6110bac7 | source_snapshot / socai2.baseline-model-view.v4 | — |
| 3df62cb2-7348-4140-ab75-1fa0e6763dfa | model_request / socai2.baseline-analysis.v1 | 83eb5795-20ac-4b5a-af56-ad71f292821e |
| f714c721-f40c-4815-87d1-d8bf1d340006 | model_response / socai2.baseline-analysis.v1 | 83eb5795-20ac-4b5a-af56-ad71f292821e |
| 440dc086-1bc5-497c-baf9-66617a5fb209 | domain_analysis / socai2.baseline-analysis.v1 | 83eb5795-20ac-4b5a-af56-ad71f292821e |
| c4d6b310-b7c2-4a2e-8385-35fc71b19d09 | domain_analysis / socai2.baseline-analysis.v1 | 83eb5795-20ac-4b5a-af56-ad71f292821e |
| 3c2b33cb-4311-4226-9b93-80112ad15e22 | domain_analysis / socai2.baseline-analysis.v1 | 83eb5795-20ac-4b5a-af56-ad71f292821e |
| cb33b4cd-5f80-4c6b-b9b9-13f0f789fc60 | domain_analysis / socai2.baseline-analysis.v1 | 83eb5795-20ac-4b5a-af56-ad71f292821e |
| f28d8e84-9162-41fb-9c93-d75d10278f27 | source_snapshot / socai2.baseline-analysis.v1 | d8b781cc-354d-4b1f-a6d2-713bb03f40f2 |
| a9767f93-004d-4477-957e-b1771d27bc31 | source_snapshot / socai2.baseline-evidence.v1 | b1be6366-7102-4201-8623-99ddb11a6ec2 |
| 7b8d95e0-9eca-4426-aec1-a052a319d443 | source_snapshot / socai2.baseline-evidence.v1 | — |
| c3b6fc54-2b71-478f-b161-90c19c5d21db | deep_analysis / socai2.baseline-deep.v1 | 2dce878c-1cd6-4f44-92a5-a06793038266 |
| 31a40c7f-54b6-4309-9221-098d5bc57d35 | source_snapshot / socai2.baseline-deep.v1 | 2dce878c-1cd6-4f44-92a5-a06793038266 |
| 3475f2d3-57be-4310-b7c8-ba6358e4b44c | alert_graph / socai2.baseline-graph.v1 | 35743db4-54e6-4445-9c27-48ccfef5d5ad |
| 39aa058d-b4f0-4f38-b989-54877cb7e548 | source_snapshot / socai2.baseline-graph.v1 | 35743db4-54e6-4445-9c27-48ccfef5d5ad |
| 71de4219-1a9d-4557-bdec-0c06a5605323 | source_snapshot / socai2.baseline-executor.v1 | 677d9e8b-fe21-4a8c-b649-a4dadd1798b8 |
| ab2f6ecf-ebb9-48f8-aaa4-c79733c0c6b1 | source_snapshot / socai2.baseline-evidence.v1 | — |
| 619d7481-eb03-45cc-a69f-6953e5cbf228 | source_snapshot / socai2.baseline-delivery.v1 | 269e5fb4-a45f-46b2-9682-1ae770b76a46 |
| eb6c9a73-5df4-487b-a993-da24e70c3678 | report_json / socai2.baseline-delivery.v1 | 269e5fb4-a45f-46b2-9682-1ae770b76a46 |
| 2d493a9a-1e4a-415f-88b8-b6b44ab55c95 | source_snapshot / socai2.baseline-delivery.v1 | 269e5fb4-a45f-46b2-9682-1ae770b76a46 |
| 0b5e4b20-dd0d-4fe2-bed3-50f244a3f680 | report_markdown / socai2.baseline-delivery.v1 | 269e5fb4-a45f-46b2-9682-1ae770b76a46 |

本轮Case结果：

- `922982dd-d84d-4469-8eac-ae9b912e89f4`：conclusion=—；origin=system；validation=system_only；delivery=partial；report_artifact_id=`eb6c9a73-5df4-487b-a993-da24e70c3678`。

<a id="run-14"></a>
## 14. Process command observed · alert_basic

Run：`11ce2d46-9022-5a61-9a29-a697efddcb7c`；对象：`d1bbfe71-9a44-5c1c-98dc-014400d25ef4`。

状态：`failed`；停止：`alert_decision_basis_mismatch`；交付：`none`。请求 `2026-11-05T00:08:29.553023+00:00`，开始 `2026-11-05T00:08:29.553023+00:00`，结束 `2026-11-05T00:08:43.361543+00:00`。

冻结输入：`ec2bdc9a-60e3-40dd-8601-578100ce476e`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 0, "incident_diagnoses": 0, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | A / stage / alert_basic_analysis | failed | — | — | {"rows": null, "error": {"code": "alert_decision_basis_mismatch", "message": "alert_decision_basis_mismatch", "retryable": false, "occurred_at": "2026-11-05T00:08:43.361543+00:00"}} |
| 2 | A / tool / assets | completed | 8f723d44-f445-4feb-9636-8b6aab396684 | 2c6cf8af-5db7-4958-a743-11b7db4e598a | {"rows": 0, "error": null} |
| 3 | A / tool / history | completed | 57b2897a-a6fc-4fb9-9548-79609e1a4e16 | f74519fa-f41f-49df-9b1b-c54499ef7f66 | {"rows": 0, "error": null} |
| 4 | A / tool / threat_intel | skipped | c5d466c4-094a-49d3-905f-2f2c75bcadf2 | 3e20deb9-621c-4e6a-a3ee-dae95592111a | {"rows": null, "error": {"code": "no_supported_frozen_objects", "message": "no_supported_frozen_objects", "retryable": false, "occurred_at": "2026-11-05T00:08:29.691760+00:00"}} |
| 5 | A / model / alert_triage_and_explanation | failed | 964b8779-1540-43ce-ac2d-ec1739761da0 | b3d1201d-6d06-49fc-815e-d2497302fd8a | {"rows": null, "error": {"code": "alert_decision_basis_mismatch", "message": "alert_decision_basis_mismatch", "retryable": false, "occurred_at": "2026-11-05T00:08:43.353350+00:00"}} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| ec2bdc9a-60e3-40dd-8601-578100ce476e | input_snapshot / socai2.stage-result.v1 | — |
| 8f723d44-f445-4feb-9636-8b6aab396684 | tool_request / socai2.alert-basic-executor.v3 | 16303429-6fdf-488a-92ce-086992d3457e |
| 2c6cf8af-5db7-4958-a743-11b7db4e598a | tool_response / socai2.alert-basic-executor.v3 | 16303429-6fdf-488a-92ce-086992d3457e |
| 57b2897a-a6fc-4fb9-9548-79609e1a4e16 | tool_request / socai2.alert-basic-executor.v3 | 868d934f-a0d8-43e7-8ebd-f24a2ac9a7d5 |
| f74519fa-f41f-49df-9b1b-c54499ef7f66 | tool_response / socai2.alert-basic-executor.v3 | 868d934f-a0d8-43e7-8ebd-f24a2ac9a7d5 |
| c5d466c4-094a-49d3-905f-2f2c75bcadf2 | tool_request / socai2.alert-basic-executor.v3 | c0fff370-feb3-4584-b95e-7d5d569f23fa |
| 3e20deb9-621c-4e6a-a3ee-dae95592111a | tool_response / socai2.alert-basic-executor.v3 | c0fff370-feb3-4584-b95e-7d5d569f23fa |
| 964b8779-1540-43ce-ac2d-ec1739761da0 | model_request / socai2.alert-basic-executor.v3 | f7bb25ea-c118-4f44-afda-4b83095e784d |
| b3d1201d-6d06-49fc-815e-d2497302fd8a | model_response / socai2.alert-basic-executor.v3 | f7bb25ea-c118-4f44-afda-4b83095e784d |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-15"></a>
## 15. Outbound connection observed · alert_basic

Run：`eaf0d23a-b085-52df-be95-21d2b6f66244`；对象：`70b9a986-44b7-5a67-8553-762d4dcd050d`。

状态：`completed`；停止：`stage_output_saved`；交付：`partial`。请求 `2026-11-05T00:08:43.415167+00:00`，开始 `2026-11-05T00:08:43.415167+00:00`，结束 `2026-11-05T00:08:54.663064+00:00`。

冻结输入：`5276017b-f87d-4184-b823-6627d0c955bd`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 1, "incident_diagnoses": 0, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | A / stage / alert_basic_analysis | completed | — | 01a91962-e7a6-560d-a129-65600fd01a38 | {"rows": null, "error": null} |
| 2 | A / tool / assets | completed | fbbf5a38-eff2-4f60-8904-b1873a7165b0 | 53672969-6a8f-4182-aeb4-811a43df6c18 | {"rows": 0, "error": null} |
| 3 | A / tool / history | completed | 65bcb833-0e58-4e0f-9532-d7ce43676331 | 36064561-855a-47a6-a468-602e248b9806 | {"rows": 1, "error": null} |
| 4 | A / tool / threat_intel | completed | 608721fc-3031-4ae4-a0dd-c3aae5fdc816 | 2ea70c53-b369-4cb7-bb3e-294c4b1c22a0 | {"rows": 0, "error": null} |
| 5 | A / model / alert_triage_and_explanation | completed | 888be656-e13c-4281-9f54-cdf236d58ff3 | 67855282-22b8-43e8-8149-6172529eaa1e | {"rows": null, "error": null} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| 5276017b-f87d-4184-b823-6627d0c955bd | input_snapshot / socai2.stage-result.v1 | — |
| fbbf5a38-eff2-4f60-8904-b1873a7165b0 | tool_request / socai2.alert-basic-executor.v3 | 8fffc574-65d2-4a73-8f46-d86803f8ae9c |
| 53672969-6a8f-4182-aeb4-811a43df6c18 | tool_response / socai2.alert-basic-executor.v3 | 8fffc574-65d2-4a73-8f46-d86803f8ae9c |
| 65bcb833-0e58-4e0f-9532-d7ce43676331 | tool_request / socai2.alert-basic-executor.v3 | b79626ad-de28-4df5-bbf1-e36e4fca9c2d |
| 36064561-855a-47a6-a468-602e248b9806 | tool_response / socai2.alert-basic-executor.v3 | b79626ad-de28-4df5-bbf1-e36e4fca9c2d |
| 608721fc-3031-4ae4-a0dd-c3aae5fdc816 | tool_request / socai2.alert-basic-executor.v3 | ed10ee50-d8ab-49d6-9061-802504857bc6 |
| 2ea70c53-b369-4cb7-bb3e-294c4b1c22a0 | tool_response / socai2.alert-basic-executor.v3 | ed10ee50-d8ab-49d6-9061-802504857bc6 |
| 888be656-e13c-4281-9f54-cdf236d58ff3 | model_request / socai2.alert-basic-executor.v3 | 9cd3c560-8b66-438a-bc3f-47ee8f6dab59 |
| 67855282-22b8-43e8-8149-6172529eaa1e | model_response / socai2.alert-basic-executor.v3 | 9cd3c560-8b66-438a-bc3f-47ee8f6dab59 |
| 01a91962-e7a6-560d-a129-65600fd01a38 | source_snapshot / socai2.stage-result.v1 | — |
| 26287152-651a-5d52-b80f-51c12978ed13 | alert_explanation / socai2.stage-result.v1 | — |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-16"></a>
## 16. 关联事件 · Process command observed · incident_diagnosis

Run：`9bb665cd-f20a-5790-9c7f-07b638568105`；对象：`4b1f85fe-b807-4823-9a25-6a024f0f0f4c`。

状态：`completed`；停止：`stage_output_saved`；交付：`partial`。请求 `2026-11-05T00:08:54.744932+00:00`，开始 `2026-11-05T00:08:54.744932+00:00`，结束 `2026-11-05T00:09:39.485796+00:00`。

冻结输入：`b3845813-d0b6-44c3-95e6-bc576dec65a9`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 0, "incident_diagnoses": 1, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | I / stage / incident_member_synthesis | completed | — | 947ce4a6-5b14-55d6-aa5a-ffbc74727643 | {"rows": null, "error": null} |
| 2 | I / model / incident_member_synthesis | completed | 45de73d5-3d6d-48bc-aa59-f0d65a0c5a18 | ba6837fc-96bd-44e1-b243-98e1d3752a55 | {"rows": null, "error": null} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| b3845813-d0b6-44c3-95e6-bc576dec65a9 | input_snapshot / socai2.stage-result.v1 | — |
| 45de73d5-3d6d-48bc-aa59-f0d65a0c5a18 | model_request / socai2.incident-diagnosis-executor.v3 | 153cbfd0-0775-456f-9260-e8b3496977a5 |
| ba6837fc-96bd-44e1-b243-98e1d3752a55 | model_response / socai2.incident-diagnosis-executor.v3 | 153cbfd0-0775-456f-9260-e8b3496977a5 |
| 947ce4a6-5b14-55d6-aa5a-ffbc74727643 | source_snapshot / socai2.stage-result.v1 | — |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-17"></a>
## 17. Endpoint activity review · baseline

Run：`cabb2a3b-7d9c-4ec7-9d00-95924a87885c`；对象：`0fc1afec-591e-5f0e-a5f9-de393866df9c`。

状态：`unknown`；停止：`executor_dispatch_uncertain`；交付：`none`。请求 `2026-11-05T00:09:39.56795+00:00`，开始 `2026-11-05T00:09:39.674165+00:00`，结束 `None`。

冻结输入：`e6fc6dc8-082d-4cdf-9140-c57f292bd3cd`；范围版本：`1`。关联行数：{"run_members": 2, "alert_assessments": 0, "incident_diagnoses": 0, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | C1.executor / stage / execution_plan | completed | — | f06f924a-97ca-4da2-bf08-b377b063b498 | {"rows": null, "error": null} |
| 2 | C2 / stage / baseline_background_enrichment | completed | aaf9c2b3-1914-47e4-84ff-7e758ae78ed9 | d25f5c18-5e6a-4857-a405-d0795d4e52be | {"rows": null, "error": null} |
| 3 | C2 / tool / assets | completed | e96849bd-f2b5-453b-8f40-683943799f5f | 3df9dee8-445e-4865-93f5-a1f4ce8d9a46 | {"rows": 0, "error": null} |
| 4 | C2 / tool / history | completed | 4cdbad97-9f18-470a-b866-af4d91471519 | 0c835268-088d-4cd0-94c1-908db48803d4 | {"rows": 0, "error": null} |
| 5 | C2 / tool / threat_intel | skipped | 6ee98274-597c-4850-a4db-f39ef90ae8cd | d1fd94c2-f97c-467c-aa69-3d7c6f52f4a3 | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:09:39.825609+00:00"}} |
| 6 | C2 / tool / ueba | skipped | be0e5bb5-cc5f-4426-b384-9796a25e1a71 | f4ee42dd-57f2-4e21-9b48-e24baa4ecc12 | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:09:39.845422+00:00"}} |
| 7 | C2 / tool / knowledge | skipped | 3ccfee6d-d7d3-45f1-b3eb-312072070bbc | 51446ef5-664e-4128-b25f-b333a9842056 | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:09:39.862123+00:00"}} |
| 8 | C2 / tool / graph | skipped | f24bcc47-e0c3-4acc-b99e-af47300f2b6a | 3050b6a2-4187-42c0-add0-490d3e0395b9 | {"rows": null, "error": {"code": "source_not_connected", "message": "source_not_connected", "retryable": false, "occurred_at": "2026-11-05T00:09:39.878501+00:00"}} |
| 9 | C3 / stage / initial_main_and_domain_analysis | unknown | 4e81860c-a35d-40ac-8a8e-cd73a1a228e3 | — | {"rows": null, "error": {"code": "analysis_dispatch_uncertain", "message": "model_dispatch:ModelCallError", "retryable": false, "occurred_at": "2026-11-05T00:09:40.158882+00:00"}} |
| 10 | C3 / model / main_with_domain_views | unknown | 25e55331-9578-4e87-8318-ea42797ba5fb | 7f629e5f-4bb0-42c7-929c-fd4a329ad0f2 | {"rows": null, "error": {"code": "analysis_dispatch_uncertain", "message": "model_dispatch:ModelCallError", "retryable": false, "occurred_at": "2026-11-05T00:09:40.158882+00:00"}} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| aaf9c2b3-1914-47e4-84ff-7e758ae78ed9 | source_snapshot / socai2.baseline-context.v1 | — |
| e6fc6dc8-082d-4cdf-9140-c57f292bd3cd | input_snapshot / socai2.page-model.v1 | — |
| f06f924a-97ca-4da2-bf08-b377b063b498 | source_snapshot / socai2.baseline-executor.v1 | efb113d3-119f-4e7a-bce8-e3decb977701 |
| e96849bd-f2b5-453b-8f40-683943799f5f | tool_request / socai2.baseline-enrichment.v1 | 5e721cfe-1a0a-4231-ad83-7ecc0f35704f |
| 3df9dee8-445e-4865-93f5-a1f4ce8d9a46 | tool_response / socai2.baseline-enrichment.v1 | 5e721cfe-1a0a-4231-ad83-7ecc0f35704f |
| 4cdbad97-9f18-470a-b866-af4d91471519 | tool_request / socai2.baseline-enrichment.v1 | e3eb7538-ac9b-4b14-8bcb-5607c1bd03ef |
| 0c835268-088d-4cd0-94c1-908db48803d4 | tool_response / socai2.baseline-enrichment.v1 | e3eb7538-ac9b-4b14-8bcb-5607c1bd03ef |
| 6ee98274-597c-4850-a4db-f39ef90ae8cd | tool_request / socai2.baseline-enrichment.v1 | ccd5fdae-558f-4e53-978a-5aa0fc6db5b0 |
| d1fd94c2-f97c-467c-aa69-3d7c6f52f4a3 | tool_response / socai2.baseline-enrichment.v1 | ccd5fdae-558f-4e53-978a-5aa0fc6db5b0 |
| be0e5bb5-cc5f-4426-b384-9796a25e1a71 | tool_request / socai2.baseline-enrichment.v1 | ec22fad4-74d2-4528-b26a-9d070e763d13 |
| f4ee42dd-57f2-4e21-9b48-e24baa4ecc12 | tool_response / socai2.baseline-enrichment.v1 | ec22fad4-74d2-4528-b26a-9d070e763d13 |
| 3ccfee6d-d7d3-45f1-b3eb-312072070bbc | tool_request / socai2.baseline-enrichment.v1 | 6fd94409-9851-4ec9-a652-fd97f98d6db9 |
| 51446ef5-664e-4128-b25f-b333a9842056 | tool_response / socai2.baseline-enrichment.v1 | 6fd94409-9851-4ec9-a652-fd97f98d6db9 |
| f24bcc47-e0c3-4acc-b99e-af47300f2b6a | tool_request / socai2.baseline-enrichment.v1 | 0e438112-ad1b-40fd-adf0-757750f39c92 |
| 3050b6a2-4187-42c0-add0-490d3e0395b9 | tool_response / socai2.baseline-enrichment.v1 | 0e438112-ad1b-40fd-adf0-757750f39c92 |
| d25f5c18-5e6a-4857-a405-d0795d4e52be | source_snapshot / socai2.baseline-enrichment.v1 | c8289a29-0e56-44da-bf76-126c98ea0f5c |
| 4e81860c-a35d-40ac-8a8e-cd73a1a228e3 | source_snapshot / socai2.baseline-model-view.v4 | — |
| 25e55331-9578-4e87-8318-ea42797ba5fb | model_request / socai2.baseline-analysis.v1 | 7e4032bf-5b74-4049-a206-8493aeec8e80 |
| 7f629e5f-4bb0-42c7-929c-fd4a329ad0f2 | model_response / socai2.baseline-analysis.v1 | 7e4032bf-5b74-4049-a206-8493aeec8e80 |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-18"></a>
## 18. Process command observed · alert_basic

Run：`96e6f573-4de2-554d-8be6-1e7c1b189917`；对象：`99f3aad0-8aba-5c4e-ba71-a01157d3fa4b`。

状态：`completed`；停止：`stage_output_saved`；交付：`partial`。请求 `2026-11-05T00:09:59.48123+00:00`，开始 `2026-11-05T00:09:59.48123+00:00`，结束 `2026-11-05T00:10:11.509601+00:00`。

冻结输入：`174dbe9f-8ec5-4116-90c9-b47520defaaf`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 1, "incident_diagnoses": 0, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | A / stage / alert_basic_analysis | completed | — | 8627229e-4207-5250-8981-500b32061961 | {"rows": null, "error": null} |
| 2 | A / tool / assets | completed | b316ec95-8850-47da-80e0-0570a2a4465d | b7b9ed90-fc47-4069-b73c-02a8639eaf96 | {"rows": 0, "error": null} |
| 3 | A / tool / history | completed | 6ff98016-9ab9-4858-b78e-1022d562b8e5 | 08130080-4879-42c9-b54a-4a995ed49c8b | {"rows": 0, "error": null} |
| 4 | A / tool / threat_intel | skipped | 8307f961-d67f-4992-afb9-6855bf29ce2b | 5d2a2d27-bb9b-4963-9220-ebd2f91e9963 | {"rows": null, "error": {"code": "no_supported_frozen_objects", "message": "no_supported_frozen_objects", "retryable": false, "occurred_at": "2026-11-05T00:09:59.561896+00:00"}} |
| 5 | A / model / alert_triage_and_explanation | completed | 020235bc-de2c-4c41-b49f-436febed7c7a | 87876787-94c4-4eb2-a999-70dd8d9e4ebd | {"rows": null, "error": null} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| 174dbe9f-8ec5-4116-90c9-b47520defaaf | input_snapshot / socai2.stage-result.v1 | — |
| b316ec95-8850-47da-80e0-0570a2a4465d | tool_request / socai2.alert-basic-executor.v3 | 514bbff4-32cc-4c2d-82c1-6138ffd889f7 |
| b7b9ed90-fc47-4069-b73c-02a8639eaf96 | tool_response / socai2.alert-basic-executor.v3 | 514bbff4-32cc-4c2d-82c1-6138ffd889f7 |
| 6ff98016-9ab9-4858-b78e-1022d562b8e5 | tool_request / socai2.alert-basic-executor.v3 | 32e263f5-34ea-4073-813c-8e4caccea822 |
| 08130080-4879-42c9-b54a-4a995ed49c8b | tool_response / socai2.alert-basic-executor.v3 | 32e263f5-34ea-4073-813c-8e4caccea822 |
| 8307f961-d67f-4992-afb9-6855bf29ce2b | tool_request / socai2.alert-basic-executor.v3 | 24e8889d-46f0-473d-ab71-47325e6fc764 |
| 5d2a2d27-bb9b-4963-9220-ebd2f91e9963 | tool_response / socai2.alert-basic-executor.v3 | 24e8889d-46f0-473d-ab71-47325e6fc764 |
| 020235bc-de2c-4c41-b49f-436febed7c7a | model_request / socai2.alert-basic-executor.v3 | d26bcab8-571b-4a36-bb4b-972613f3a4bf |
| 87876787-94c4-4eb2-a999-70dd8d9e4ebd | model_response / socai2.alert-basic-executor.v3 | d26bcab8-571b-4a36-bb4b-972613f3a4bf |
| 4418f1b3-5f58-5e15-8904-89d6b33698e3 | alert_explanation / socai2.stage-result.v1 | — |
| 8627229e-4207-5250-8981-500b32061961 | source_snapshot / socai2.stage-result.v1 | — |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-19"></a>
## 19. Outbound connection observed · alert_basic

Run：`09afebcb-77f4-531f-a920-20e96f2c40c5`；对象：`843d9870-979a-58f9-9729-bde4bc4f4c2c`。

状态：`completed`；停止：`stage_output_saved`；交付：`partial`。请求 `2026-11-05T00:10:11.54674+00:00`，开始 `2026-11-05T00:10:11.54674+00:00`，结束 `2026-11-05T00:10:26.587391+00:00`。

冻结输入：`7dea2f04-3240-44dd-b2be-0be1db937a7e`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 1, "incident_diagnoses": 0, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | A / stage / alert_basic_analysis | completed | — | 76141420-3b5a-5011-a36b-0051f967ee9f | {"rows": null, "error": null} |
| 2 | A / tool / assets | completed | 6b120ecb-6fc0-477c-b566-699aa9d302ff | 00e3cf93-711b-4a8f-8074-e17dbdbb96cd | {"rows": 0, "error": null} |
| 3 | A / tool / history | completed | 77751e1d-3484-4afb-bc6b-40c69f5c0bc4 | d10cdede-e8a2-4a8c-a7a5-a11efa295ada | {"rows": 1, "error": null} |
| 4 | A / tool / threat_intel | completed | 9d1c5996-0aa1-4b92-9728-ef777295190a | 098a8eba-4e02-401e-ba52-dfaf8894d1f3 | {"rows": 0, "error": null} |
| 5 | A / model / alert_triage_and_explanation | completed | 2b900657-6a68-4a28-bc82-18dc4165e398 | 5f233317-3cb0-43e7-8f17-52f29466d4bc | {"rows": null, "error": null} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| 7dea2f04-3240-44dd-b2be-0be1db937a7e | input_snapshot / socai2.stage-result.v1 | — |
| 6b120ecb-6fc0-477c-b566-699aa9d302ff | tool_request / socai2.alert-basic-executor.v3 | 023d8ba5-b7dd-4efc-a52a-6f028c48b8a8 |
| 00e3cf93-711b-4a8f-8074-e17dbdbb96cd | tool_response / socai2.alert-basic-executor.v3 | 023d8ba5-b7dd-4efc-a52a-6f028c48b8a8 |
| 77751e1d-3484-4afb-bc6b-40c69f5c0bc4 | tool_request / socai2.alert-basic-executor.v3 | c4ed2dec-976f-43cb-9de4-25bbb2eec49a |
| d10cdede-e8a2-4a8c-a7a5-a11efa295ada | tool_response / socai2.alert-basic-executor.v3 | c4ed2dec-976f-43cb-9de4-25bbb2eec49a |
| 9d1c5996-0aa1-4b92-9728-ef777295190a | tool_request / socai2.alert-basic-executor.v3 | 03b921c7-013c-4cde-967d-3ed9c42743f9 |
| 098a8eba-4e02-401e-ba52-dfaf8894d1f3 | tool_response / socai2.alert-basic-executor.v3 | 03b921c7-013c-4cde-967d-3ed9c42743f9 |
| 2b900657-6a68-4a28-bc82-18dc4165e398 | model_request / socai2.alert-basic-executor.v3 | 112bc4e1-e362-4dce-83a7-b66622943c18 |
| 5f233317-3cb0-43e7-8f17-52f29466d4bc | model_response / socai2.alert-basic-executor.v3 | 112bc4e1-e362-4dce-83a7-b66622943c18 |
| 76141420-3b5a-5011-a36b-0051f967ee9f | source_snapshot / socai2.stage-result.v1 | — |
| cd19769b-00c4-5054-a59a-ac36a4f58f09 | alert_explanation / socai2.stage-result.v1 | — |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-20"></a>
## 20. 关联事件 · Process command observed · incident_diagnosis

Run：`85536dbe-b59d-50f0-bce8-6fe89c126a1c`；对象：`a05560d3-0344-41a2-9288-d7a7dde65712`。

状态：`failed`；停止：`incident_source_wrong_member`；交付：`none`。请求 `2026-11-05T00:10:26.644251+00:00`，开始 `2026-11-05T00:10:26.644251+00:00`，结束 `2026-11-05T00:11:01.144066+00:00`。

冻结输入：`ffedc493-3519-4e31-ba09-df6f2bede161`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 0, "incident_diagnoses": 1, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | I / stage / incident_member_synthesis | failed | — | — | {"rows": null, "error": {"code": "incident_source_wrong_member", "message": "incident_source_wrong_member", "retryable": false, "occurred_at": "2026-11-05T00:11:01.144066+00:00"}} |
| 2 | I / model / incident_member_synthesis | failed | 9e7af1eb-2ba7-4ee6-bb50-f3eabbf7c232 | 2e8d54b5-5602-4515-b9a5-7fde2e4c279a | {"rows": null, "error": {"code": "incident_source_wrong_member", "message": "incident_source_wrong_member", "retryable": false, "occurred_at": "2026-11-05T00:11:01.135115+00:00"}} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| ffedc493-3519-4e31-ba09-df6f2bede161 | input_snapshot / socai2.stage-result.v1 | — |
| 9e7af1eb-2ba7-4ee6-bb50-f3eabbf7c232 | model_request / socai2.incident-diagnosis-executor.v3 | 881a7c1e-3fcb-42a5-a3ad-c263fa1971a4 |
| 2e8d54b5-5602-4515-b9a5-7fde2e4c279a | model_response / socai2.incident-diagnosis-executor.v3 | 881a7c1e-3fcb-42a5-a3ad-c263fa1971a4 |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-21"></a>
## 21. Endpoint activity review · baseline

Run：`f5306373-9ded-437d-aaa3-6990db3f2c8d`；对象：`af831698-f518-5840-b778-54cd2515b59b`。

状态：`unknown`；停止：`executor_dispatch_uncertain`；交付：`none`。请求 `2026-11-05T00:11:01.205072+00:00`，开始 `2026-11-05T00:11:01.279057+00:00`，结束 `None`。

冻结输入：`baae84cd-0ddb-406f-92b3-22dbba150f5c`；范围版本：`1`。关联行数：{"run_members": 2, "alert_assessments": 0, "incident_diagnoses": 0, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | C1.executor / stage / execution_plan | completed | — | d51f6f5e-4d55-4605-a4e5-07c25aeb3d0f | {"rows": null, "error": null} |
| 2 | C2 / stage / baseline_background_enrichment | completed | 9de43af2-4d4d-4ac9-b11d-ed3fade297c5 | 6d65f547-0b04-4d3f-a3a4-0ef519ce8eee | {"rows": null, "error": null} |
| 3 | C2 / tool / assets | completed | 54dfeabe-c1ce-4d04-9fe8-6cbe706175fc | 5cc2cb33-1969-4426-9a84-7739b99d5b46 | {"rows": 0, "error": null} |
| 4 | C2 / tool / history | completed | f43fd954-d964-468f-95ef-1e03a862e59b | 52d94f7b-8db0-48cf-8c9f-55e282970456 | {"rows": 0, "error": null} |
| 5 | C2 / tool / threat_intel | skipped | ae3e1a84-54ae-4d39-878f-4094ca5fe30d | f24255ee-8890-441e-9cf8-28fbf595532f | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:11:01.481593+00:00"}} |
| 6 | C2 / tool / ueba | skipped | e2b9dbf9-4c07-404e-8f6e-012c84249ae0 | a412c7cc-3588-4ac9-8bcb-a1283c598121 | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:11:01.498079+00:00"}} |
| 7 | C2 / tool / knowledge | skipped | 4321359a-40dc-4905-9adb-d8d15c057e77 | 425cce34-535f-4b75-abb4-8a9e5946aa6c | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:11:01.514595+00:00"}} |
| 8 | C2 / tool / graph | skipped | 078da562-0f4a-420a-a3f5-9bd129310889 | be4817b6-142b-477c-bc30-f9961a4b2000 | {"rows": null, "error": {"code": "source_not_connected", "message": "source_not_connected", "retryable": false, "occurred_at": "2026-11-05T00:11:01.532752+00:00"}} |
| 9 | C3 / stage / initial_main_and_domain_analysis | unknown | 913ce250-b683-43b6-8ad9-144dbe25979e | — | {"rows": null, "error": {"code": "analysis_dispatch_uncertain", "message": "model_dispatch:ModelCallError", "retryable": false, "occurred_at": "2026-11-05T00:11:01.761556+00:00"}} |
| 10 | C3 / model / main_with_domain_views | unknown | 8d0d0b57-9e0c-46b5-b32c-edf4f6d60ca3 | 9626611c-96ea-462e-927e-03ff9ff6b2c6 | {"rows": null, "error": {"code": "analysis_dispatch_uncertain", "message": "model_dispatch:ModelCallError", "retryable": false, "occurred_at": "2026-11-05T00:11:01.761556+00:00"}} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| 9de43af2-4d4d-4ac9-b11d-ed3fade297c5 | source_snapshot / socai2.baseline-context.v1 | — |
| baae84cd-0ddb-406f-92b3-22dbba150f5c | input_snapshot / socai2.page-model.v1 | — |
| d51f6f5e-4d55-4605-a4e5-07c25aeb3d0f | source_snapshot / socai2.baseline-executor.v1 | bb99e440-e094-4fc8-ae37-33d0a2b3a557 |
| 54dfeabe-c1ce-4d04-9fe8-6cbe706175fc | tool_request / socai2.baseline-enrichment.v1 | 94231d33-0c36-4577-94b4-16bf71ef9108 |
| 5cc2cb33-1969-4426-9a84-7739b99d5b46 | tool_response / socai2.baseline-enrichment.v1 | 94231d33-0c36-4577-94b4-16bf71ef9108 |
| f43fd954-d964-468f-95ef-1e03a862e59b | tool_request / socai2.baseline-enrichment.v1 | 14e35a4b-f259-4cdf-9518-b5d59b3e457f |
| 52d94f7b-8db0-48cf-8c9f-55e282970456 | tool_response / socai2.baseline-enrichment.v1 | 14e35a4b-f259-4cdf-9518-b5d59b3e457f |
| ae3e1a84-54ae-4d39-878f-4094ca5fe30d | tool_request / socai2.baseline-enrichment.v1 | 94314a4d-e50c-438f-8b50-60c974832fde |
| f24255ee-8890-441e-9cf8-28fbf595532f | tool_response / socai2.baseline-enrichment.v1 | 94314a4d-e50c-438f-8b50-60c974832fde |
| e2b9dbf9-4c07-404e-8f6e-012c84249ae0 | tool_request / socai2.baseline-enrichment.v1 | 5ef377f7-83b1-4133-b959-2ef99796f9c0 |
| a412c7cc-3588-4ac9-8bcb-a1283c598121 | tool_response / socai2.baseline-enrichment.v1 | 5ef377f7-83b1-4133-b959-2ef99796f9c0 |
| 4321359a-40dc-4905-9adb-d8d15c057e77 | tool_request / socai2.baseline-enrichment.v1 | 037fefd4-0f59-4d6a-a997-6228359926a5 |
| 425cce34-535f-4b75-abb4-8a9e5946aa6c | tool_response / socai2.baseline-enrichment.v1 | 037fefd4-0f59-4d6a-a997-6228359926a5 |
| 078da562-0f4a-420a-a3f5-9bd129310889 | tool_request / socai2.baseline-enrichment.v1 | 15e89c14-4092-4e83-aa54-ff0d30e61ae1 |
| be4817b6-142b-477c-bc30-f9961a4b2000 | tool_response / socai2.baseline-enrichment.v1 | 15e89c14-4092-4e83-aa54-ff0d30e61ae1 |
| 6d65f547-0b04-4d3f-a3a4-0ef519ce8eee | source_snapshot / socai2.baseline-enrichment.v1 | 26063555-232d-4173-8212-5a0f9ab4d89e |
| 913ce250-b683-43b6-8ad9-144dbe25979e | source_snapshot / socai2.baseline-model-view.v4 | — |
| 8d0d0b57-9e0c-46b5-b32c-edf4f6d60ca3 | model_request / socai2.baseline-analysis.v1 | 35f288be-396e-451c-8aa9-c2b6f0d72dea |
| 9626611c-96ea-462e-927e-03ff9ff6b2c6 | model_response / socai2.baseline-analysis.v1 | 35f288be-396e-451c-8aa9-c2b6f0d72dea |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-22"></a>
## 22. Process command observed · alert_basic

Run：`21e7edf5-4216-5534-8b05-6e733275a178`；对象：`ab7af404-9c9e-5d46-8201-c96a17f97a59`。

状态：`completed`；停止：`stage_output_saved`；交付：`partial`。请求 `2026-11-05T00:11:59.758053+00:00`，开始 `2026-11-05T00:11:59.758053+00:00`，结束 `2026-11-05T00:12:11.326573+00:00`。

冻结输入：`32992c4d-30fc-4535-a959-d1e5c2ac3ca3`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 1, "incident_diagnoses": 0, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | A / stage / alert_basic_analysis | completed | — | fe3238f3-3d02-5135-8cfd-1ee8155b6c50 | {"rows": null, "error": null} |
| 2 | A / tool / assets | completed | e05628fd-620e-44c3-b3ff-9b72ddb8c0b4 | 503063e8-8d48-4466-be59-a212a32bb1e3 | {"rows": 0, "error": null} |
| 3 | A / tool / history | completed | a86de083-da6e-41f0-9b4e-75f1ae187e38 | ee7df607-1d2a-4a36-b2c0-293710463b60 | {"rows": 0, "error": null} |
| 4 | A / tool / threat_intel | skipped | cd0c19cc-403e-4bb2-800d-2bdc6d6f300d | 7a66562a-37e4-4d5f-93dd-9da1ba6e5efb | {"rows": null, "error": {"code": "no_supported_frozen_objects", "message": "no_supported_frozen_objects", "retryable": false, "occurred_at": "2026-11-05T00:11:59.843453+00:00"}} |
| 5 | A / model / alert_triage_and_explanation | completed | 94f995ea-8f22-4621-8e24-ddc29b22011b | 95bb1811-a0ed-4c61-b841-4ce49818965d | {"rows": null, "error": null} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| 32992c4d-30fc-4535-a959-d1e5c2ac3ca3 | input_snapshot / socai2.stage-result.v1 | — |
| e05628fd-620e-44c3-b3ff-9b72ddb8c0b4 | tool_request / socai2.alert-basic-executor.v3 | 9da4cb27-9723-4df1-97da-6cd5c797adbf |
| 503063e8-8d48-4466-be59-a212a32bb1e3 | tool_response / socai2.alert-basic-executor.v3 | 9da4cb27-9723-4df1-97da-6cd5c797adbf |
| a86de083-da6e-41f0-9b4e-75f1ae187e38 | tool_request / socai2.alert-basic-executor.v3 | 19d114dd-1417-4637-8eaf-7f728e9912f8 |
| ee7df607-1d2a-4a36-b2c0-293710463b60 | tool_response / socai2.alert-basic-executor.v3 | 19d114dd-1417-4637-8eaf-7f728e9912f8 |
| cd0c19cc-403e-4bb2-800d-2bdc6d6f300d | tool_request / socai2.alert-basic-executor.v3 | 02f5d481-fc60-4e91-966f-f0d67da2f5c9 |
| 7a66562a-37e4-4d5f-93dd-9da1ba6e5efb | tool_response / socai2.alert-basic-executor.v3 | 02f5d481-fc60-4e91-966f-f0d67da2f5c9 |
| 94f995ea-8f22-4621-8e24-ddc29b22011b | model_request / socai2.alert-basic-executor.v3 | 9d0fc3b5-a708-45e8-85b8-6360a6714bed |
| 95bb1811-a0ed-4c61-b841-4ce49818965d | model_response / socai2.alert-basic-executor.v3 | 9d0fc3b5-a708-45e8-85b8-6360a6714bed |
| 9a27168f-cc6b-5769-a027-3ca7f545317d | alert_explanation / socai2.stage-result.v1 | — |
| fe3238f3-3d02-5135-8cfd-1ee8155b6c50 | source_snapshot / socai2.stage-result.v1 | — |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-23"></a>
## 23. Outbound connection observed · alert_basic

Run：`5cfd24f5-4606-5212-ab03-ce1338ff5a44`；对象：`b369a2bd-cc1f-54da-8fca-538f25f655b5`。

状态：`completed`；停止：`stage_output_saved`；交付：`partial`。请求 `2026-11-05T00:12:11.367018+00:00`，开始 `2026-11-05T00:12:11.367018+00:00`，结束 `2026-11-05T00:12:25.392021+00:00`。

冻结输入：`e5650a72-91f1-432f-a0b9-e43cfb765bce`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 1, "incident_diagnoses": 0, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | A / stage / alert_basic_analysis | completed | — | 498d710d-a865-5dc2-b1ca-f7911b48eba0 | {"rows": null, "error": null} |
| 2 | A / tool / assets | completed | 46fba77f-1ab4-4128-92db-ef3ad441e283 | 952f6f30-d21a-41b3-839a-3717cb597895 | {"rows": 0, "error": null} |
| 3 | A / tool / history | completed | 1bccd71e-41bb-4575-9c19-7e1faef72f13 | ee101672-77c3-4cf3-aacb-7769f20c04a7 | {"rows": 1, "error": null} |
| 4 | A / tool / threat_intel | completed | 7febf65c-ebbc-45b4-9870-c3ccd28a8747 | b6cd76d6-366f-44c6-b376-72cdf9f4e298 | {"rows": 0, "error": null} |
| 5 | A / model / alert_triage_and_explanation | completed | a32a956f-1dcf-4ef7-b343-2d8a852c4e00 | ee89d326-4ca8-476a-8b53-4f0a305f0e2e | {"rows": null, "error": null} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| e5650a72-91f1-432f-a0b9-e43cfb765bce | input_snapshot / socai2.stage-result.v1 | — |
| 46fba77f-1ab4-4128-92db-ef3ad441e283 | tool_request / socai2.alert-basic-executor.v3 | 33b88559-b330-4d06-8fc4-bf8bf16ed0cc |
| 952f6f30-d21a-41b3-839a-3717cb597895 | tool_response / socai2.alert-basic-executor.v3 | 33b88559-b330-4d06-8fc4-bf8bf16ed0cc |
| 1bccd71e-41bb-4575-9c19-7e1faef72f13 | tool_request / socai2.alert-basic-executor.v3 | 335e5481-c740-4f3d-9417-3d8f35d8a5de |
| ee101672-77c3-4cf3-aacb-7769f20c04a7 | tool_response / socai2.alert-basic-executor.v3 | 335e5481-c740-4f3d-9417-3d8f35d8a5de |
| 7febf65c-ebbc-45b4-9870-c3ccd28a8747 | tool_request / socai2.alert-basic-executor.v3 | 298d1541-6451-4f57-adf4-02277efa422e |
| b6cd76d6-366f-44c6-b376-72cdf9f4e298 | tool_response / socai2.alert-basic-executor.v3 | 298d1541-6451-4f57-adf4-02277efa422e |
| a32a956f-1dcf-4ef7-b343-2d8a852c4e00 | model_request / socai2.alert-basic-executor.v3 | e4feef2c-1aaf-46a2-bd7e-555e21e166cc |
| ee89d326-4ca8-476a-8b53-4f0a305f0e2e | model_response / socai2.alert-basic-executor.v3 | e4feef2c-1aaf-46a2-bd7e-555e21e166cc |
| 498d710d-a865-5dc2-b1ca-f7911b48eba0 | source_snapshot / socai2.stage-result.v1 | — |
| c40d9316-e459-5f7f-bf3c-e25c18df7b4f | alert_explanation / socai2.stage-result.v1 | — |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-24"></a>
## 24. 关联事件 · Process command observed · incident_diagnosis

Run：`25a24d2f-6633-5420-b02f-92637873f81f`；对象：`556b8b24-f6b3-4ebd-8dec-e779b89c1f29`。

状态：`completed`；停止：`stage_output_saved`；交付：`partial`。请求 `2026-11-05T00:12:25.441799+00:00`，开始 `2026-11-05T00:12:25.441799+00:00`，结束 `2026-11-05T00:12:53.949958+00:00`。

冻结输入：`a65df662-bf04-4cd7-9fea-19f133a43d4b`；范围版本：`None`。关联行数：{"run_members": 0, "alert_assessments": 0, "incident_diagnoses": 1, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | I / stage / incident_member_synthesis | completed | — | abc38f2d-b704-5bbb-b85d-a728a462df3a | {"rows": null, "error": null} |
| 2 | I / model / incident_member_synthesis | completed | 78a4294a-ffdc-48d3-9e92-82d3f6b4498d | aa942bf5-b65d-41b9-9666-7a5727b54c0e | {"rows": null, "error": null} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| a65df662-bf04-4cd7-9fea-19f133a43d4b | input_snapshot / socai2.stage-result.v1 | — |
| 78a4294a-ffdc-48d3-9e92-82d3f6b4498d | model_request / socai2.incident-diagnosis-executor.v3 | 53b59b8d-1c91-43f6-b1c9-a46b77cd27a3 |
| aa942bf5-b65d-41b9-9666-7a5727b54c0e | model_response / socai2.incident-diagnosis-executor.v3 | 53b59b8d-1c91-43f6-b1c9-a46b77cd27a3 |
| abc38f2d-b704-5bbb-b85d-a728a462df3a | source_snapshot / socai2.stage-result.v1 | — |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-25"></a>
## 25. Endpoint activity review · baseline

Run：`a3bb07c3-1dfb-4c79-99db-0455cbb2bfc6`；对象：`b020606b-90f9-5f02-ab9a-9d8ec740c827`。

状态：`unknown`；停止：`executor_dispatch_uncertain`；交付：`none`。请求 `2026-11-05T00:12:54.010307+00:00`，开始 `2026-11-05T00:12:54.067045+00:00`，结束 `None`。

冻结输入：`63bc4a62-f327-4cbd-83b1-e6940bded85f`；范围版本：`1`。关联行数：{"run_members": 2, "alert_assessments": 0, "incident_diagnoses": 0, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|
| 1 | C1.executor / stage / execution_plan | completed | — | 93943e63-e88b-493a-827b-dd51a6371a50 | {"rows": null, "error": null} |
| 2 | C2 / stage / baseline_background_enrichment | completed | a424d60e-8a30-4985-8dfd-34afdb92e45c | d8ae0326-24ac-44ee-8794-d29523d55916 | {"rows": null, "error": null} |
| 3 | C2 / tool / assets | completed | 79a82313-d147-4c21-9577-7589ca5d0e9f | 2c8bef5b-d176-40e6-b9db-fa1dd87d3a6b | {"rows": 0, "error": null} |
| 4 | C2 / tool / history | completed | c6e24452-a479-4b08-a92c-f8571b5eabc4 | 6ad6c0a3-e7d1-4420-bc41-11ec6252b855 | {"rows": 0, "error": null} |
| 5 | C2 / tool / threat_intel | skipped | fff0fcbf-9c75-4602-b69a-ad3314be3769 | 5760c5ad-39e1-4091-91ab-929079539d35 | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:12:54.189551+00:00"}} |
| 6 | C2 / tool / ueba | skipped | 70326b3d-75fc-4426-b9ad-4c667afb895e | fc4e8d70-6604-426a-bd79-166f19bb170a | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:12:54.209624+00:00"}} |
| 7 | C2 / tool / knowledge | skipped | 979c970c-2326-4b0c-9b9f-2a7023a912c8 | b9d0205d-743f-4465-8e6d-90f88a1148aa | {"rows": null, "error": {"code": "tool_budget_reserved_for_evidence", "message": "tool_budget_reserved_for_evidence", "retryable": false, "occurred_at": "2026-11-05T00:12:54.227444+00:00"}} |
| 8 | C2 / tool / graph | skipped | e20c7834-ca5d-49e6-a738-8df517fd1890 | 97ec9f6c-8e5b-4d71-986b-4ace866c6fe9 | {"rows": null, "error": {"code": "source_not_connected", "message": "source_not_connected", "retryable": false, "occurred_at": "2026-11-05T00:12:54.243987+00:00"}} |
| 9 | C3 / stage / initial_main_and_domain_analysis | unknown | 36577562-46aa-426c-ab47-9daafbccf783 | — | {"rows": null, "error": {"code": "analysis_dispatch_uncertain", "message": "model_dispatch:ModelCallError", "retryable": false, "occurred_at": "2026-11-05T00:12:54.493909+00:00"}} |
| 10 | C3 / model / main_with_domain_views | unknown | fb767141-42ec-4bbf-b86c-54ff890e63b5 | 98532ec5-1f11-4c71-9a5b-2e32db07abea | {"rows": null, "error": {"code": "analysis_dispatch_uncertain", "message": "model_dispatch:ModelCallError", "retryable": false, "occurred_at": "2026-11-05T00:12:54.493909+00:00"}} |

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|
| 63bc4a62-f327-4cbd-83b1-e6940bded85f | input_snapshot / socai2.page-model.v1 | — |
| a424d60e-8a30-4985-8dfd-34afdb92e45c | source_snapshot / socai2.baseline-context.v1 | — |
| 93943e63-e88b-493a-827b-dd51a6371a50 | source_snapshot / socai2.baseline-executor.v1 | 4c8f9963-52e1-497c-85f9-dc05e6df0e93 |
| 79a82313-d147-4c21-9577-7589ca5d0e9f | tool_request / socai2.baseline-enrichment.v1 | 79212bdb-133f-4759-ad99-d49d7bdb867b |
| 2c8bef5b-d176-40e6-b9db-fa1dd87d3a6b | tool_response / socai2.baseline-enrichment.v1 | 79212bdb-133f-4759-ad99-d49d7bdb867b |
| c6e24452-a479-4b08-a92c-f8571b5eabc4 | tool_request / socai2.baseline-enrichment.v1 | c7d08987-6e77-452d-907d-785e6dc1520b |
| 6ad6c0a3-e7d1-4420-bc41-11ec6252b855 | tool_response / socai2.baseline-enrichment.v1 | c7d08987-6e77-452d-907d-785e6dc1520b |
| fff0fcbf-9c75-4602-b69a-ad3314be3769 | tool_request / socai2.baseline-enrichment.v1 | 54751e8a-fe06-40e6-a0b3-e8d0dd38239a |
| 5760c5ad-39e1-4091-91ab-929079539d35 | tool_response / socai2.baseline-enrichment.v1 | 54751e8a-fe06-40e6-a0b3-e8d0dd38239a |
| 70326b3d-75fc-4426-b9ad-4c667afb895e | tool_request / socai2.baseline-enrichment.v1 | 47776f74-10b1-4b21-8cda-07da583b9719 |
| fc4e8d70-6604-426a-bd79-166f19bb170a | tool_response / socai2.baseline-enrichment.v1 | 47776f74-10b1-4b21-8cda-07da583b9719 |
| 979c970c-2326-4b0c-9b9f-2a7023a912c8 | tool_request / socai2.baseline-enrichment.v1 | 79728109-a5ec-4a7a-9794-df6685ded026 |
| b9d0205d-743f-4465-8e6d-90f88a1148aa | tool_response / socai2.baseline-enrichment.v1 | 79728109-a5ec-4a7a-9794-df6685ded026 |
| e20c7834-ca5d-49e6-a738-8df517fd1890 | tool_request / socai2.baseline-enrichment.v1 | e3b27c9a-64ec-48bc-bbde-b7efee71d450 |
| 97ec9f6c-8e5b-4d71-986b-4ace866c6fe9 | tool_response / socai2.baseline-enrichment.v1 | e3b27c9a-64ec-48bc-bbde-b7efee71d450 |
| d8ae0326-24ac-44ee-8794-d29523d55916 | source_snapshot / socai2.baseline-enrichment.v1 | 4c4f2584-c5a1-4c29-af3a-41acfebda23a |
| 36577562-46aa-426c-ab47-9daafbccf783 | source_snapshot / socai2.baseline-model-view.v4 | — |
| fb767141-42ec-4bbf-b86c-54ff890e63b5 | model_request / socai2.baseline-analysis.v1 | f3c249c2-5f28-494e-807d-8bdda78ec809 |
| 98532ec5-1f11-4c71-9a5b-2e32db07abea | model_response / socai2.baseline-analysis.v1 | f3c249c2-5f28-494e-807d-8bdda78ec809 |

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。

<a id="run-26"></a>
## 26. Endpoint activity review · baseline

Run：`2d32f7c8-4abc-4b03-bc56-58146263e7dd`；对象：`0fc1afec-591e-5f0e-a5f9-de393866df9c`。

状态：`pending_update`；停止：`None`；交付：`none`。请求 `2026-11-05T00:13:17.947002+00:00`，开始 `None`，结束 `None`。

冻结输入：`None`；范围版本：`1`。关联行数：{"run_members": 2, "alert_assessments": 0, "incident_diagnoses": 0, "result_members": 0}。

| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |
|---|---|---|---|---|---|

该Run尚无Step，不能按完成处理。

| 全部工件ID | 类型 / Schema | Step ID |
|---|---|---|

本轮Case结果：

没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。
