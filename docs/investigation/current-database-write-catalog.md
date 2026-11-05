# 当前数据库写点明细

配合[当前执行账本](current-execution-ledger.md)阅读。以下逐项从当前业务源码与自动采用函数提取；每项有源文件、行号、调用函数、操作、目标、字段及完整表达式。不是某次Run实际执行的SQL日志。

共 124 个写点；字段值和WHERE条件完整保留在[JSON明细](current-database-write-catalog.json)及链接源码中。`**values`等动态字段保留代码表达式，不能当成字段已展开。

| 序号 | 函数/源代码 | 操作 | 目标 | 显式字段或参数 |
|---|---|---|---|---|
| 1 | [alert_basic_executor.py:47 step](/E:/aisoc/socai2/services/api/app/socai2/alert_basic_executor.py:47) | INSERT | socai2.run_steps | id, tenant_id, run_id, seq, kind, stage_code, name, state, parent_step_id, implementation_version, actual_args, started_at |
| 2 | [alert_basic_executor.py:100 execute](/E:/aisoc/socai2/services/api/app/socai2/alert_basic_executor.py:100) | UPDATE | socai2.run_steps | input_artifact_id, provider |
| 3 | [alert_basic_executor.py:115 execute](/E:/aisoc/socai2/services/api/app/socai2/alert_basic_executor.py:115) | UPDATE | socai2.run_steps | output_artifact_id, usage |
| 4 | [alert_basic_executor.py:119 execute](/E:/aisoc/socai2/services/api/app/socai2/alert_basic_executor.py:119) | UPDATE | socai2.run_steps | state, ended_at, error |
| 5 | [alert_basic_executor.py:151 execute](/E:/aisoc/socai2/services/api/app/socai2/alert_basic_executor.py:151) | UPDATE | socai2.run_steps | state, ended_at, output_artifact_id, usage, error |
| 6 | [alert_basic_executor.py:163 execute](/E:/aisoc/socai2/services/api/app/socai2/alert_basic_executor.py:163) | UPDATE | socai2.run_steps | state, error |
| 7 | [alert_basic_executor.py:166 execute](/E:/aisoc/socai2/services/api/app/socai2/alert_basic_executor.py:166) | UPDATE | socai2.runs | state, stop_reason, row_version |
| 8 | [alert_basic_executor.py:175 fail](/E:/aisoc/socai2/services/api/app/socai2/alert_basic_executor.py:175) | UPDATE | socai2.run_steps | state, ended_at, error |
| 9 | [alert_basic_executor.py:177 fail](/E:/aisoc/socai2/services/api/app/socai2/alert_basic_executor.py:177) | UPDATE | socai2.runs | state, ended_at, stop_reason, row_version |
| 10 | [alert_basic_executor.py:207 background](/E:/aisoc/socai2/services/api/app/socai2/alert_basic_executor.py:207) | UPDATE | socai2.run_steps | input_artifact_id, provider |
| 11 | [alert_basic_executor.py:241 background](/E:/aisoc/socai2/services/api/app/socai2/alert_basic_executor.py:241) | UPDATE | socai2.run_steps | state, ended_at, output_artifact_id, returned_rows, error |
| 12 | [baseline_analysis.py:123 execute](/E:/aisoc/socai2/services/api/app/socai2/baseline_analysis.py:123) | INSERT | socai2.run_steps | id, tenant_id, run_id, seq, kind, stage_code, state, name, implementation_version, started_at, input_artifact_id |
| 13 | [baseline_analysis.py:158 execute](/E:/aisoc/socai2/services/api/app/socai2/baseline_analysis.py:158) | INSERT | socai2.run_steps | id, tenant_id, run_id, seq, parent_step_id, kind, stage_code, state, name, provider, implementation_version, started_at |
| 14 | [baseline_analysis.py:169 execute](/E:/aisoc/socai2/services/api/app/socai2/baseline_analysis.py:169) | UPDATE | socai2.run_steps | input_artifact_id |
| 15 | [baseline_analysis.py:186 execute](/E:/aisoc/socai2/services/api/app/socai2/baseline_analysis.py:186) | UPDATE | socai2.run_steps | output_artifact_id, usage |
| 16 | [baseline_analysis.py:190 execute](/E:/aisoc/socai2/services/api/app/socai2/baseline_analysis.py:190) | UPDATE | socai2.run_steps | state, ended_at, error |
| 17 | [baseline_analysis.py:230 execute](/E:/aisoc/socai2/services/api/app/socai2/baseline_analysis.py:230) | UPDATE | socai2.run_steps | state, error |
| 18 | [baseline_analysis.py:247 finish](/E:/aisoc/socai2/services/api/app/socai2/baseline_analysis.py:247) | UPDATE | socai2.run_steps | state, ended_at, output_artifact_id, usage, error |
| 19 | [baseline_analysis.py:259 finish](/E:/aisoc/socai2/services/api/app/socai2/baseline_analysis.py:259) | UPDATE | socai2.run_members | analysis_state |
| 20 | [baseline_analysis.py:273 finish](/E:/aisoc/socai2/services/api/app/socai2/baseline_analysis.py:273) | UPDATE | socai2.run_steps | state, ended_at, output_artifact_id, error |
| 21 | [baseline_deep.py:127 execute](/E:/aisoc/socai2/services/api/app/socai2/baseline_deep.py:127) | INSERT | socai2.run_steps | id, tenant_id, run_id, seq, kind, stage_code, question_id, name, state, implementation_version, started_at, input_artifact_id |
| 22 | [baseline_deep.py:192 finish](/E:/aisoc/socai2/services/api/app/socai2/baseline_deep.py:192) | UPDATE | socai2.run_steps | state, ended_at, output_artifact_id, error |
| 23 | [baseline_delivery.py:123 execute](/E:/aisoc/socai2/services/api/app/socai2/baseline_delivery.py:123) | INSERT | socai2.run_steps | id, tenant_id, run_id, seq, kind, stage_code, name, state, implementation_version, started_at, input_artifact_id |
| 24 | [baseline_delivery.py:218 finish](/E:/aisoc/socai2/services/api/app/socai2/baseline_delivery.py:218) | UPDATE | socai2.run_steps | state, ended_at, output_artifact_id, error |
| 25 | [baseline_delivery.py:240 save_markdown](/E:/aisoc/socai2/services/api/app/socai2/baseline_delivery.py:240) | INSERT | socai2.artifacts | id, tenant_id, case_id, run_id, step_id, kind, schema_version, content_text, mime_type, sha256, size_bytes, captured_at, material_state, created_by, source_refs, retention |
| 26 | [baseline_enrichment.py:55 artifact](/E:/aisoc/socai2/services/api/app/socai2/baseline_enrichment.py:55) | INSERT | socai2.artifacts | id, tenant_id, case_id, run_id, step_id, kind, schema_version, content_json, mime_type, sha256, size_bytes, captured_at, material_state, source_refs, created_by, retention |
| 27 | [baseline_enrichment.py:96 execute](/E:/aisoc/socai2/services/api/app/socai2/baseline_enrichment.py:96) | INSERT | socai2.run_steps | id, tenant_id, run_id, seq, kind, stage_code, state, name, implementation_version, started_at, input_artifact_id |
| 28 | [baseline_enrichment.py:120 execute](/E:/aisoc/socai2/services/api/app/socai2/baseline_enrichment.py:120) | UPDATE | socai2.run_steps | state, ended_at, output_artifact_id |
| 29 | [baseline_enrichment.py:126 execute](/E:/aisoc/socai2/services/api/app/socai2/baseline_enrichment.py:126) | UPDATE | socai2.run_steps | state, error |
| 30 | [baseline_enrichment.py:175 source](/E:/aisoc/socai2/services/api/app/socai2/baseline_enrichment.py:175) | INSERT | socai2.run_steps | id, tenant_id, run_id, seq, parent_step_id, kind, stage_code, state, name, provider, implementation_version, started_at, actual_args |
| 31 | [baseline_enrichment.py:182 source](/E:/aisoc/socai2/services/api/app/socai2/baseline_enrichment.py:182) | UPDATE | socai2.run_steps | input_artifact_id |
| 32 | [baseline_enrichment.py:229 source](/E:/aisoc/socai2/services/api/app/socai2/baseline_enrichment.py:229) | UPDATE | socai2.run_steps | state, ended_at, output_artifact_id, returned_rows, error |
| 33 | [baseline_evidence.py:91 prepare](/E:/aisoc/socai2/services/api/app/socai2/baseline_evidence.py:91) | UPDATE | socai2.run_members | read_state |
| 34 | [baseline_evidence.py:101 prepare](/E:/aisoc/socai2/services/api/app/socai2/baseline_evidence.py:101) | INSERT | socai2.run_steps | id, tenant_id, run_id, seq, kind, stage_code, state, name, implementation_version, started_at |
| 35 | [baseline_evidence.py:105 prepare](/E:/aisoc/socai2/services/api/app/socai2/baseline_evidence.py:105) | UPDATE | socai2.run_steps | state, ended_at, output_artifact_id |
| 36 | [baseline_evidence.py:177 query](/E:/aisoc/socai2/services/api/app/socai2/baseline_evidence.py:177) | INSERT | socai2.run_steps | id, tenant_id, run_id, seq, kind, stage_code, question_id, parent_step_id, name, state, provider, implementation_version, started_at, actual_args |
| 37 | [baseline_evidence.py:185 query](/E:/aisoc/socai2/services/api/app/socai2/baseline_evidence.py:185) | UPDATE | socai2.run_steps | input_artifact_id |
| 38 | [baseline_evidence.py:240 query](/E:/aisoc/socai2/services/api/app/socai2/baseline_evidence.py:240) | UPDATE | socai2.run_steps | state, ended_at, output_artifact_id, returned_rows, error |
| 39 | [baseline_evidence.py:249 query](/E:/aisoc/socai2/services/api/app/socai2/baseline_evidence.py:249) | UPDATE | socai2.run_steps | state, error |
| 40 | [baseline_executor.py:28 record](/E:/aisoc/socai2/services/api/app/socai2/baseline_executor.py:28) | INSERT | socai2.run_steps | id, tenant_id, run_id, seq, kind, stage_code, name, state, started_at, implementation_version |
| 41 | [baseline_executor.py:32 record](/E:/aisoc/socai2/services/api/app/socai2/baseline_executor.py:32) | UPDATE | socai2.run_steps | state, ended_at, output_artifact_id |
| 42 | [baseline_graph.py:48 execute](/E:/aisoc/socai2/services/api/app/socai2/baseline_graph.py:48) | INSERT | socai2.run_steps | id, tenant_id, run_id, seq, kind, stage_code, name, state, implementation_version, started_at, input_artifact_id |
| 43 | [baseline_graph.py:58 execute](/E:/aisoc/socai2/services/api/app/socai2/baseline_graph.py:58) | UPDATE | socai2.run_steps | state, ended_at, output_artifact_id |
| 44 | [baseline_reanalysis.py:151 execute](/E:/aisoc/socai2/services/api/app/socai2/baseline_reanalysis.py:151) | INSERT | socai2.run_steps | id, tenant_id, run_id, seq, kind, stage_code, name, state, implementation_version, started_at, input_artifact_id |
| 45 | [baseline_reasoning.py:132 uncertain](/E:/aisoc/socai2/services/api/app/socai2/baseline_reasoning.py:132) | UPDATE | socai2.run_steps | state, error |
| 46 | [baseline_reasoning.py:166 call](/E:/aisoc/socai2/services/api/app/socai2/baseline_reasoning.py:166) | INSERT | socai2.run_steps | id, tenant_id, run_id, seq, kind, stage_code, parent_step_id, question_id, state, name, provider, implementation_version, started_at |
| 47 | [baseline_reasoning.py:179 call](/E:/aisoc/socai2/services/api/app/socai2/baseline_reasoning.py:179) | UPDATE | socai2.run_steps | input_artifact_id |
| 48 | [baseline_reasoning.py:194 call](/E:/aisoc/socai2/services/api/app/socai2/baseline_reasoning.py:194) | UPDATE | socai2.run_steps | output_artifact_id, usage |
| 49 | [baseline_reasoning.py:198 call](/E:/aisoc/socai2/services/api/app/socai2/baseline_reasoning.py:198) | UPDATE | socai2.run_steps | state, ended_at, error |
| 50 | [baseline_reasoning.py:231 call](/E:/aisoc/socai2/services/api/app/socai2/baseline_reasoning.py:231) | UPDATE | socai2.run_steps | state, ended_at, output_artifact_id, usage, error |
| 51 | [baseline_store.py:90 event](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:90) | INSERT | socai2.activities | id, tenant_id, operation_id, actor, action, subject_case_id, occurred_at, summary, detail |
| 52 | [baseline_store.py:96 event](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:96) | INSERT | socai2.activity_targets | id, tenant_id, activity_id, **{field: target_id}, before_value, after_value, result_state |
| 53 | [baseline_store.py:139 replace_members](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:139) | UPDATE | socai2.cases | source_namespace |
| 54 | [baseline_store.py:150 replace_members](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:150) | DELETE | socai2.case_alerts | 详见完整表达式/SQL |
| 55 | [baseline_store.py:153 replace_members](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:153) | INSERT | socai2.case_alerts | id, tenant_id, case_id, alert_id, added_by, membership_source, source_operation_id, added_at |
| 56 | [baseline_store.py:158 replace_members](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:158) | UPDATE | socai2.cases | scope_revision, row_version, business_updated_at |
| 57 | [baseline_store.py:162 replace_members](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:162) | INSERT | socai2.runs | id, tenant_id, case_id, kind, title, purpose, trigger, scope_revision, scope_updated_at, scope_kind, state, requested_by, requested_at |
| 58 | [baseline_store.py:169 replace_members](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:169) | UPDATE | socai2.runs | scope_revision, scope_updated_at, row_version |
| 59 | [baseline_store.py:192 refresh_members](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:192) | DELETE | socai2.run_members | 详见完整表达式/SQL |
| 60 | [baseline_store.py:194 refresh_members](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:194) | INSERT | socai2.run_members | id, tenant_id, case_id, run_id, alert_id, material_id, triage_id, feedback_id, read_state, omission_reason |
| 61 | [baseline_store.py:205 save_input_artifact](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:205) | INSERT | socai2.artifacts | id, tenant_id, case_id, run_id, step_id, kind, schema_version, content_json, mime_type, sha256, size_bytes, captured_at, material_state, source_refs, created_by, retention |
| 62 | [baseline_store.py:270 claim](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:270) | UPDATE | socai2.runs | state, input_artifact_id, operation_key, request_hash, executor_version, limits, started_at, requested_by, window_start, window_end, comparison_result_id, row_version |
| 63 | [baseline_store.py:416 publish](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:416) | UPDATE | socai2.run_members | read_state, analysis_state, omission_reason |
| 64 | [baseline_store.py:419 publish](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:419) | UPDATE | socai2.runs | state, ended_at, stop_reason, stop_detail, delivery_state, row_version |
| 65 | [baseline_store.py:425 publish](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:425) | INSERT | socai2.results | id, tenant_id, case_id, kind, source_run_id, purpose, input_artifact_id, comparison_result_id, graph_artifact_id, report_artifact_id, created_at, operation_key, **values |
| 66 | [baseline_store.py:432 publish](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:432) | INSERT | socai2.result_members | id, tenant_id, case_id, result_id, run_id, alert_id, **vals |
| 67 | [baseline_store.py:490 prepare_model_view](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:490) | UPDATE | socai2.run_members | read_state |
| 68 | [baseline_store.py:503 mark_unknown](/E:/aisoc/socai2/services/api/app/socai2/baseline_store.py:503) | UPDATE | socai2.runs | state, stop_reason, row_version |
| 69 | [case_relations.py:78 associate](/E:/aisoc/socai2/services/api/app/socai2/case_relations.py:78) | INSERT | socai2.case_incidents | id, tenant_id, case_id, incident_id, linked_at, linked_by, source_operation_id |
| 70 | [case_relations.py:83 associate](/E:/aisoc/socai2/services/api/app/socai2/case_relations.py:83) | UPDATE | socai2.cases | row_version, business_updated_at |
| 71 | [case_service.py:40 create_case](/E:/aisoc/socai2/services/api/app/socai2/case_service.py:40) | INSERT | socai2.cases | id, tenant_id, title, description, severity, severity_source, tags, created_by |
| 72 | [case_service.py:54 create_case](/E:/aisoc/socai2/services/api/app/socai2/case_service.py:54) | UPDATE | socai2.runs | trigger, purpose |
| 73 | [case_service.py:116 prepare_baseline](/E:/aisoc/socai2/services/api/app/socai2/case_service.py:116) | INSERT | socai2.runs | id, tenant_id, case_id, kind, title, purpose, trigger, scope_revision, scope_updated_at, scope_kind, state, requested_by, requested_at |
| 74 | [human_task_service.py:139 write](/E:/aisoc/socai2/services/api/app/socai2/human_task_service.py:139) | INSERT | socai2.tasks | id, tenant_id, case_id, current_revision_id, origin_result_id, origin_finding_id, created_at, created_by, updated_at |
| 75 | [human_task_service.py:142 write](/E:/aisoc/socai2/services/api/app/socai2/human_task_service.py:142) | INSERT | socai2.task_revisions | **values |
| 76 | [human_task_service.py:144 write](/E:/aisoc/socai2/services/api/app/socai2/human_task_service.py:144) | UPDATE | socai2.tasks | current_revision_id, updated_at, row_version |
| 77 | [human_task_service.py:146 write](/E:/aisoc/socai2/services/api/app/socai2/human_task_service.py:146) | UPDATE | socai2.cases | business_updated_at, row_version |
| 78 | [incident_diagnosis_executor.py:35 step](/E:/aisoc/socai2/services/api/app/socai2/incident_diagnosis_executor.py:35) | INSERT | socai2.run_steps | id, tenant_id, run_id, seq, kind, stage_code, name, state, parent_step_id, started_at, implementation_version |
| 79 | [incident_diagnosis_executor.py:58 stop](/E:/aisoc/socai2/services/api/app/socai2/incident_diagnosis_executor.py:58) | UPDATE | socai2.run_steps | state, ended_at, error |
| 80 | [incident_diagnosis_executor.py:61 stop](/E:/aisoc/socai2/services/api/app/socai2/incident_diagnosis_executor.py:61) | UPDATE | socai2.runs | state, ended_at, stop_reason, row_version |
| 81 | [incident_diagnosis_executor.py:63 stop](/E:/aisoc/socai2/services/api/app/socai2/incident_diagnosis_executor.py:63) | UPDATE | socai2.incident_diagnoses | state, error |
| 82 | [incident_diagnosis_executor.py:109 execute](/E:/aisoc/socai2/services/api/app/socai2/incident_diagnosis_executor.py:109) | UPDATE | socai2.run_steps | input_artifact_id, provider |
| 83 | [incident_diagnosis_executor.py:123 execute](/E:/aisoc/socai2/services/api/app/socai2/incident_diagnosis_executor.py:123) | UPDATE | socai2.run_steps | output_artifact_id, usage |
| 84 | [incident_diagnosis_executor.py:154 execute](/E:/aisoc/socai2/services/api/app/socai2/incident_diagnosis_executor.py:154) | UPDATE | socai2.run_steps | state, ended_at, output_artifact_id, usage, error |
| 85 | [stage_results.py:50 artifact](/E:/aisoc/socai2/services/api/app/socai2/stage_results.py:50) | INSERT | socai2.artifacts | id, tenant_id, **{key: run[key]}, run_id, step_id, kind, schema_version, content_json, mime_type, sha256, size_bytes, captured_at, material_state, source_refs, retention |
| 86 | [stage_results.py:174 begin](/E:/aisoc/socai2/services/api/app/socai2/stage_results.py:174) | INSERT | socai2.runs | **run, tenant_id, title, purpose, trigger, state, operation_key, request_hash, input_artifact_id, executor_version, requested_at, started_at, limits, requested_by |
| 87 | [stage_results.py:182 begin](/E:/aisoc/socai2/services/api/app/socai2/stage_results.py:182) | INSERT | socai2.incident_diagnoses | id, tenant_id, incident_id, source_run_id, revision, state, input_artifact_id, source_fingerprint, producer, requested_at |
| 88 | [stage_results.py:253 finish](/E:/aisoc/socai2/services/api/app/socai2/stage_results.py:253) | INSERT | socai2.alert_assessments | id, tenant_id, alert_id, kind, input_material_id, source_run_id, verdict, rationale, confidence, score_state, recommendations, producer, actor, assessed_at, operation_key |
| 89 | [stage_results.py:262 finish](/E:/aisoc/socai2/services/api/app/socai2/stage_results.py:262) | UPDATE | socai2.incident_diagnoses | state, summary, diagnosis, open_questions, generated_at |
| 90 | [stage_results.py:271 finish](/E:/aisoc/socai2/services/api/app/socai2/stage_results.py:271) | UPDATE | socai2.alerts / incidents (stage kind) | **values |
| 91 | [stage_results.py:275 finish](/E:/aisoc/socai2/services/api/app/socai2/stage_results.py:275) | UPDATE | socai2.incidents | 详见完整表达式/SQL |
| 92 | [stage_results.py:283 finish](/E:/aisoc/socai2/services/api/app/socai2/stage_results.py:283) | UPDATE | socai2.runs | state, ended_at, stop_reason, delivery_state, row_version |
| 93 | [stage_results.py:286 finish](/E:/aisoc/socai2/services/api/app/socai2/stage_results.py:286) | UPDATE | socai2.run_steps | state, ended_at, output_artifact_id |
| 94 | [stage_results.py:310 stop](/E:/aisoc/socai2/services/api/app/socai2/stage_results.py:310) | UPDATE | socai2.runs | state, ended_at, stop_reason, row_version |
| 95 | [stage_results.py:313 stop](/E:/aisoc/socai2/services/api/app/socai2/stage_results.py:313) | UPDATE | socai2.incident_diagnoses | state, error |
| 96 | [125_socai2_baseline_input_freshness.sql:119 auto_adopt_baseline_result](/E:/aisoc/socai2/services/api/migrations/125_socai2_baseline_input_freshness.sql:119) | INSERT INTO | socai2.case_assessments | 详见完整表达式/SQL |
| 97 | [125_socai2_baseline_input_freshness.sql:121 auto_adopt_baseline_result](/E:/aisoc/socai2/services/api/migrations/125_socai2_baseline_input_freshness.sql:121) | INSERT INTO | socai2.case_assessment_sources | 详见完整表达式/SQL |
| 98 | [125_socai2_baseline_input_freshness.sql:123 auto_adopt_baseline_result](/E:/aisoc/socai2/services/api/migrations/125_socai2_baseline_input_freshness.sql:123) | INSERT INTO | socai2.case_assessment_members | 详见完整表达式/SQL |
| 99 | [125_socai2_baseline_input_freshness.sql:126 auto_adopt_baseline_result](/E:/aisoc/socai2/services/api/migrations/125_socai2_baseline_input_freshness.sql:126) | UPDATE | socai2.cases | 详见完整表达式/SQL |
| 100 | [125_socai2_baseline_input_freshness.sql:128 auto_adopt_baseline_result](/E:/aisoc/socai2/services/api/migrations/125_socai2_baseline_input_freshness.sql:128) | INSERT INTO | socai2.activities | 详见完整表达式/SQL |
| 101 | [125_socai2_baseline_input_freshness.sql:132 auto_adopt_baseline_result](/E:/aisoc/socai2/services/api/migrations/125_socai2_baseline_input_freshness.sql:132) | INSERT INTO | socai2.activity_targets | 详见完整表达式/SQL |
| 102 | [125_socai2_baseline_input_freshness.sql:135 auto_adopt_baseline_result](/E:/aisoc/socai2/services/api/migrations/125_socai2_baseline_input_freshness.sql:135) | INSERT INTO | socai2.activity_targets | 详见完整表达式/SQL |
| 103 | [correlator.py:76 correlator](/E:/aisoc/socai2/services/fusion/app/services/correlator.py:76) | Redis set | Redis DB 13 | 详见完整表达式/SQL |
| 104 | [correlator.py:146 correlator](/E:/aisoc/socai2/services/fusion/app/services/correlator.py:146) | Redis set | Redis DB 13 | 详见完整表达式/SQL |
| 105 | [deduplicator.py:49 deduplicator](/E:/aisoc/socai2/services/fusion/app/services/deduplicator.py:49) | Redis set | Redis DB 13 | 详见完整表达式/SQL |
| 106 | [delivery_recovery.py:145 delivery_recovery](/E:/aisoc/socai2/services/fusion/app/services/delivery_recovery.py:145) | Redis set | Redis DB 13 | 详见完整表达式/SQL |
| 107 | [entity_risk.py:283 entity_risk](/E:/aisoc/socai2/services/fusion/app/services/entity_risk.py:283) | Redis sadd | Redis DB 13 | 详见完整表达式/SQL |
| 108 | [entity_risk.py:284 entity_risk](/E:/aisoc/socai2/services/fusion/app/services/entity_risk.py:284) | Redis expire | Redis DB 13 | 详见完整表达式/SQL |
| 109 | [entity_risk.py:287 entity_risk](/E:/aisoc/socai2/services/fusion/app/services/entity_risk.py:287) | Redis zadd | Redis DB 13 | 详见完整表达式/SQL |
| 110 | [entity_risk.py:288 entity_risk](/E:/aisoc/socai2/services/fusion/app/services/entity_risk.py:288) | Redis expire | Redis DB 13 | 详见完整表达式/SQL |
| 111 | [entity_risk.py:364 entity_risk](/E:/aisoc/socai2/services/fusion/app/services/entity_risk.py:364) | Redis hset | Redis DB 13 | 详见完整表达式/SQL |
| 112 | [entity_risk.py:365 entity_risk](/E:/aisoc/socai2/services/fusion/app/services/entity_risk.py:365) | Redis expire | Redis DB 13 | 详见完整表达式/SQL |
| 113 | [entity_risk.py:367 entity_risk](/E:/aisoc/socai2/services/fusion/app/services/entity_risk.py:367) | Redis zadd | Redis DB 13 | 详见完整表达式/SQL |
| 114 | [entity_risk.py:369 entity_risk](/E:/aisoc/socai2/services/fusion/app/services/entity_risk.py:369) | Redis expire | Redis DB 13 | 详见完整表达式/SQL |
| 115 | [lake_writer.py:498 flush](/E:/aisoc/socai2/services/fusion/app/services/lake_writer.py:498) | INSERT | ClickHouse socai2_next_validation.raw_events | columns, default_id_form |
| 116 | [socai2_sink.py:98 _write](/E:/aisoc/socai2/services/fusion/app/services/socai2_sink.py:98) | INSERT | socai2.alerts | values |
| 117 | [socai2_sink.py:113 _write](/E:/aisoc/socai2/services/fusion/app/services/socai2_sink.py:113) | INSERT | socai2.artifacts | values |
| 118 | [socai2_sink.py:123 _write](/E:/aisoc/socai2/services/fusion/app/services/socai2_sink.py:123) | INSERT | socai2.alert_materials | values |
| 119 | [socai2_sink.py:127 _write](/E:/aisoc/socai2/services/fusion/app/services/socai2_sink.py:127) | INSERT | socai2.alert_source_refs | values |
| 120 | [socai2_sink.py:130 _write](/E:/aisoc/socai2/services/fusion/app/services/socai2_sink.py:130) | INSERT | socai2.alert_objects | values |
| 121 | [socai2_sink.py:134 _write](/E:/aisoc/socai2/services/fusion/app/services/socai2_sink.py:134) | UPDATE | socai2.alerts | 详见完整表达式/SQL |
| 122 | [socai2_sink.py:140 _write](/E:/aisoc/socai2/services/fusion/app/services/socai2_sink.py:140) | INSERT | socai2.incidents | values |
| 123 | [socai2_sink.py:146 _write](/E:/aisoc/socai2/services/fusion/app/services/socai2_sink.py:146) | INSERT | socai2.incident_alerts | values |
| 124 | [socai2_sink.py:152 _write](/E:/aisoc/socai2/services/fusion/app/services/socai2_sink.py:152) | UPDATE | socai2.incidents | 详见完整表达式/SQL |
