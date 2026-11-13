"""人工维护的文档注释；不参与业务服务运行。"""
# 编号稳定对应源 OpenAPI 的现有操作，不创建新业务路径。
OPERATIONS = {
1: ('新建 Case', '可用', '至少选择一个告警或事件；事件展开为成员并保留显式事件关系，合并后最多 200 条。保存后返回 pending_run_id；不自动执行。后续 E12→E13。', 'case_member_limit_exceeded:422 case_incident_not_found:404 case_source_namespace_mismatch:409 case_source_scope_unverified:409 operation_key_conflict:409'),
2: ('Case 队列与指标', '可用', 'q按标题字面包含或精确UUID；保留handling_status、severity、owner_id、assignment_state、metric、classification。time_from/time_to按business_updated_at；sort_by=business_updated_at（默认）/created_at/severity。total为全部筛选命中数，metrics为租户整体且high_severity仍只计high。未使用新增日期/排序时兼容旧v1游标。时间必须带时区，区间为[time_from,time_to)，允许单边；两端同时传时起点必须早于终点。等级info<low<medium<high<critical，未知值总在最后；同值按同方向UUID排序。每页1–50条，默认20；sort_order默认desc。改变筛选或排序后清空cursor；下一页原样传next_cursor，不自行解析。每次请求为当前只读快照，跨请求有业务更新时不是冻结导出。', 'invalid_case_cursor:422 case_cursor_filters_changed:422 invalid_list_cursor:422 list_cursor_filters_changed:422'),
3: ('Case 详情与当前判断', '可用', '读取成员、显式事件、当前采用判断、baseline_records 和资料。检查集合总数与截断标记。current_assessment 为 null 时不得挑最新 Run 当成已采用判断。', 'case_not_found:404 current_assessment_reference_invalid:409'),
4: ('更新分类和截止时间', '可用', '先 E03 读 row_version。PATCH 必须同时传 classification、due_at，null 表示清空；source=manual/import，source_note 非空。不支持负责人、标题或关闭/重开。成功 E03/E05 刷新。', 'case_not_found:404 case_row_version_conflict:409 operation_key_conflict:409'),
5: ('Case 资料与证据目录', '可用', '读取 classification、due_at、determination、assessment、evidence。not_recorded 与 evidence_count=null 不等于没有威胁；questions 沿采用来源结果读取。', 'case_not_found:404 current_assessment_reference_invalid:409'),
6: ('发布证据目录', '可用', '发布已整理的引用目录，不会生成新证据或执行模型。先 E03/E05 获取行版本和旧 artifact_id；index.supersedes_artifact_id 对应旧版本，范围需匹配当前成员。partial/unavailable 必须写 limitations；unavailable 的 entries 必须为空。对象、来源路径、hash、角色均以实际原件为准。', 'case_row_version_conflict:409 case_evidence_version_conflict:409 case_scope_revision_conflict:409 evidence_index_scope_invalid:422 evidence_source_not_found:422 evidence_source_path_not_found:422 evidence_index_digest_invalid:422 evidence_sources_do_not_cover_entry:422'),
7: ('替换完整 Case 成员', '可用', 'alert_ids 是替换后的完整集合，不能只传想删除的条目。可为空但空范围不能启动调查。保存产生范围版本及 pending 记录，不覆盖历史冻结输入。普通添加用 E08。', 'case_not_found:404 case_scope_revision_conflict:409 member_alert_not_found:404 resolved_case_scope_policy_not_enabled:409 operation_key_conflict:409'),
8: ('关联告警或事件', '可用', '先 E03 获取 expected_scope_revision。至少选择一个告警/事件；只添加关联，不从别的 Case 移除，也不自动启动。事件展开成员；返回实际新增与显式关联列表。', 'case_scope_revision_conflict:409 case_incident_not_found:404 case_member_limit_exceeded:422 case_source_namespace_mismatch:409 resolved_case_scope_policy_not_enabled:409 operation_key_conflict:409'),
9: ('在两个 Case 间移动告警成员', '可用', '先分别 E03 读取两案 scope_revision。源/目标不同；一次事务更新两案，返回 source/target 回执；不移动显式事件关系，不改历史 Run。', 'case_move_requires_different_target:422 case_move_member_not_in_source:409 case_scope_revision_conflict:409 case_member_limit_exceeded:422 operation_key_conflict:409'),
10: ('Case 调查历史', '可用', '按 next_cursor 取后续历史；类型区分 baseline 与 ai_saved，当前 Q 保存未实现。相关 A/I 运行需 E22/E23 组合，不能从 Case 历史推断全局目录。', 'case_not_found:404 invalid_history_cursor:422 invalid_history_limit:422'),
11: ('准备新一轮调查', '可用', '先 E03 读当前 scope_revision，返回 pending_run_id 和 created。仅准备，不调用模型；存在运行中记录时可保留 pending，启动资格由 E12 判断。空范围/已解决案不能直接启动。', 'baseline_scope_empty:409 baseline_scope_revision_conflict:409 resolved_case_start_policy_not_enabled:409 operation_key_conflict:409'),
12: ('读取 Case Run 与执行明细', '可用', '读取 start_eligibility、冻结成员、steps、工件、用量和结果 ID。can_start=false 时显示 reason。成员上限200、步骤1000、工件/结果各200；被截断的集合当前没有进一步分页 API，必须明确提示。读取不会继续执行。', 'case_run_not_found:404 execution_plan_link_invalid:409'),
13: ('启动指定 pending Run', '可用', '必须使用 E01/E08/E11 返回的 Run ID，先看 E12 启动资格。可选 window_start/end 同时传带时区的时间，start<=end；comparison_result_id 必须属于同案。当前是同步等待执行，不是202队列提交；POST 等待时可 GET E12 观察。超时/503/unknown 先读取该 Run，不换 operation_key 重新发起。模型质量仍未通过。', 'baseline_not_found:404 baseline_already_active:409 baseline_already_claimed:409 baseline_scope_empty:409 baseline_scope_revision_conflict:409 comparison_result_not_found:404 resolved_case_start_policy_not_enabled:409 full_baseline_executor_not_configured:503 full_executor_limits_outside_policy:422'),
14: ('读取正式结果', '可用', '返回 result、run、冻结成员、source_answer、delivery。结论、发现、questions、建议分开，questions 作为结论的一部分，不建立问题管理状态；人工确认由用户 E38 建任务。conclusion=null/validation_state=rejected 不包装成成功判断。', 'case_result_not_found:404 result_answer_link_invalid:409 result_delivery_link_invalid:409'),
15: ('读取 Case Run 工件', '可用', '先 E12/E14 取得真实 artifact_id；父 Case/Run 必须匹配。返回 artifact 元数据和 content_json/content_text/availability；HTTP200 不保证正文可得。', 'run_artifact_not_found:404 artifact_integrity_invalid:409'),
16: ('读取 Case 非 Run 来源工件', '可用', '仅适用于 run_id 为空的本案来源工件。Run 工件必须用 E15，不能以这个路径替代。', 'run_artifact_not_found:404 artifact_integrity_invalid:409'),
17: ('Case 处理活动', '可用', '包括案件、成员和显式事件匹配活动，去重保留目标及前后值，按 next_offset 分页。活动不是模型推理过程。', 'case_not_found:404 invalid_record_page:422'),
18: ('读取 Run 冻结的告警材料', '可用', 'material_id 必须由该 Run 的冻结成员输入取得。返回 AlertMaterials 原始行，不是 ContentView 包装，没有 availability 字段；保留 material_state/retention。不能用当前材料代替。', 'frozen_material_not_found:404'),
19: ('Case 助手发送问题（预留）', '未实现', '通过请求校验后返回501，无模型调用和保存。现有 DTO 只有 operation_key、question、conversation_id；产品设计的 scope 尚无字段，额外字段会422。', 'case_ai_not_implemented:501'),
20: ('保存助手回答（预留）', '未实现', '通过请求校验后返回501，没有冻结或正式结果。title/conclusion 是待保存文本，不触发执行；当前不能使用。', 'case_ai_not_implemented:501'),
21: ('显式采用其他结果（预留）', '未实现', '通过请求校验后返回501。D03 要求理由和覆盖确认，但现有 DTO 只有 operation_key/expected_scope_revision，reason 尚未实现，不能发送虚构参数。已有基础流程自动采用与本操作不同。', 'case_ai_not_implemented:501'),
22: ('告警分诊目录', '可用', 'current 是当前指针对应分诊；entries 是历史尝试。失败尝试不能覆盖有效旧结论。分页使用 next_before_run_id。', 'stage_subject_not_found:404 invalid_stage_history_limit:422'),
23: ('事件诊断目录', '可用', '区分当前诊断、最近尝试及 partial_analysis；分页使用 next_before_run_id。诊断交付完整性、review_items、成员覆盖不混为一个成功状态。', 'stage_subject_not_found:404 invalid_stage_history_limit:422'),
24: ('指定告警 A Run', '可用', '用目录返回 Run ID。检查 freshness、is_current_pointer、valid_for_current_input。TriageView.confidence 为0..1；SubjectView.triage.confidence_percent 为百分数，不能二次乘100。', 'stage_run_not_found:404'),
25: ('指定事件 I Run', '可用', '读 diagnosis、open_questions、交付与待复核字段；执行过程需 E32。保存/格式通过不代表正文质量通过。', 'stage_run_not_found:404'),
26: ('告警列表', '可用', 'q按标题字面包含或精确UUID，支持severity、handling_status（new/in_progress/completed/unknown）、owner_id、assignment_state。time_from/time_to按真实event_time，缺失不以入库时间补齐。sort_by=ingested_at（默认）/event_time/severity。filtered_total为全部筛选命中数；total和overall_stats仍为租户整体。无新增筛选/排序时旧before_id/next_before_id继续可用；新查询用cursor，before_id与cursor或新条件混用返回422。时间必须带时区，区间为[time_from,time_to)，允许单边；两端同时传时起点必须早于终点。等级info<low<medium<high<critical，未知值总在最后；同值按同方向UUID排序。每页1–50条，默认20；sort_order默认desc。改变筛选或排序后清空cursor；下一页原样传next_cursor，不自行解析。每次请求为当前只读快照，跨请求有业务更新时不是冻结导出。', 'invalid_list_cursor:422 list_cursor_filters_changed:422 page_subject_not_found:404'),
27: ('事件列表', '可用', 'q按标题字面包含或精确UUID，支持severity、handling_status（new/in_progress/resolved/unknown）、owner_id、assignment_state。severity为人工覆盖优先、否则成员最大等级；time_from/time_to要求至少一条成员告警真实event_time处于该区间，不能仅用事件首尾跨越判断。sort_by=created_at（默认）/last_activity_at（成员最晚真实发生时间）/severity。filtered_total为全部筛选命中数；total和overall_stats仍为租户整体。无新增筛选/排序时旧before_id/next_before_id继续可用；新查询用cursor，before_id与cursor或新条件混用返回422。时间必须带时区，区间为[time_from,time_to)，允许单边；两端同时传时起点必须早于终点。等级info<low<medium<high<critical，未知值总在最后；同值按同方向UUID排序。每页1–50条，默认20；sort_order默认desc。改变筛选或排序后清空cursor；下一页原样传next_cursor，不自行解析。每次请求为当前只读快照，跨请求有业务更新时不是冻结导出。', 'invalid_list_cursor:422 list_cursor_filters_changed:422 page_subject_not_found:404'),
28: ('告警详情', '可用', '返回 facts、derived、material、triage、feedback 及 analysis_url/section_urls。反馈读取不代表人工判定写入口已实现；发生时间缺失不以入库时间替代。', 'page_subject_not_found:404'),
29: ('事件详情', '可用', '返回主体事实、derived 及目录链接；诊断另取 E23，成员/对象另取 E30。资产完整资料由业务后端提供。', 'page_subject_not_found:404'),
30: ('主体分区记录', '可用', 'subject 只能 alerts/incidents；section 参见分区说明。members 仅事件，incidents 仅告警；其他错误组合404。items 随 section 变化，不能固定为一种记录。next_offset=null 结束；related_alerts 只是同类型/同命名空间/同对象键匹配，不是相似历史反馈或图探索服务。', 'page_subject_not_found:404 section_not_applicable:404 invalid_record_page:422'),
31: ('告警材料正文', '可用', '从 E28 material.id 取得版本；content_json 包含 raw_json/ocsf_json/enrichment，content_text 为 raw_text。availability 限制与缺正文必须保留，不能展示空JSON当无异常。', 'alert_material_not_found:404 material_subject_invalid:404'),
32: ('A/I Run 步骤及工件目录', '可用', 'subject=alerts/incidents，identity 为对应主体 UUID。返回 run、steps、artifacts、用量及截断标志。仅查既有记录，读取不重新执行；正文按 E33。', 'stage_run_not_found:404'),
33: ('A/I Run 工件正文', '可用', '父主体及 Run 必须匹配。返回 metadata/content_json/content_text/availability；metadata 与 Case E15 的 artifact 字段不同。', 'stage_artifact_not_found:404'),
34: ('告警非 Run 来源工件', '可用', '读取本告警 run_id 为空的来源工件，artifact_id 可由 source_artifacts 记录取得。', 'stage_artifact_not_found:404'),
35: ('事件非 Run 来源工件', '可用', '读取本事件 run_id 为空的来源工件，不能替代运行工件路径。', 'stage_artifact_not_found:404'),
36: ('手动告警分诊', '已实现', '21新独立正式服务18024已挂载/开启，读写目标aisoc。operation_key 同租户稳定映射 Run；执行异常先 E24 查询，异常回执含 run_id；其他部署未启用时503仅返回socai2_stage_execution_not_enabled。调用会执行模型，本轮入口验收未派发真实模型，结论质量以独立验收为准。', 'socai2_stage_execution_not_enabled:503 stage_subject_not_found:404 stage_execution_not_ready:409 operation_key_conflict:409'),
37: ('手动事件诊断', '已实现', '部署同E36，21新独立正式服务18024已挂载/开启。只传 operation_key，主体来自路径。执行异常先 E25 查询返回的 Run；其他部署未启用时503不产生Run。不能把路由可用当成自动消费者已开启或真实模型质量通过。', 'socai2_stage_execution_not_enabled:503 stage_subject_not_found:404 stage_execution_not_ready:409 operation_key_conflict:409'),
38: ('用户创建人工任务', '可用', '用户明确决定需要人工确认后创建；不自动从 questions 批量生成。先 E03 获取范围版本，assignee_id 由业务后端人员目录取得。origin_finding_id 需同时有 origin_result_id；引用对象必须属于本案。保存不启动调查。', 'case_scope_revision_conflict:409 task_assignee_not_in_tenant:422 task_origin_result_not_found:404 task_origin_finding_not_found:422 task_source_reference_not_found:404 task_source_reference_outside_case:422 operation_key_conflict:409'),
39: ('人工任务列表', '可用', '返回当前修订、总数和 next_offset；待办统计只计实际未结束任务。旧版本必须另用 E42/E43。', 'case_not_found:404 invalid_record_page:422'),
40: ('修订人工任务', '可用', 'PUT 为完整 TaskFields，不是局部 PATCH；先 E41 取当前字段和 row_version，再 E03 取范围版本，完整带回未修改字段。省略可选字段会取默认值，可能清空原值。completed 必须有 result_text 和 result_scope；whole_case 覆盖当前全部成员，selected_alerts 只能当前子集，explicit_objects 还需非空有效 object_keys。事实变更生成新修订，旧引用不变。', 'case_task_not_found:404 task_row_version_conflict:409 case_scope_revision_conflict:409 task_scope_outside_current_case:422 task_whole_case_scope_incomplete:422 task_object_scope_empty:422 task_objects_outside_current_scope:422 task_source_reference_not_found:404 operation_key_conflict:409'),
41: ('人工任务当前版本', '可用', '读取 task.current 及 row_version。编辑要保留原字段；负责人和完成人均由服务保存，不由客户端伪造完成时间。', 'case_task_not_found:404'),
42: ('人工任务修订历史', '可用', '使用 next_offset 分页。任务被引用时必须保存具体 revision_id，不用最新版本覆盖历史事实。', 'case_task_not_found:404 invalid_record_page:422'),
43: ('人工任务指定修订', '可用', '按引用的 revision_id 阅读当时 title/result_text/result_scope/source_refs/completed_at/by；旧版本不可变。', 'case_task_revision_not_found:404'),
44: ('Case管理信息与结案条件', '已实现', '先读取当前Case行版本、未完任务数及阻塞Run。can_close只说明状态/执行条件；requires_open_task_confirmation为true时仍须确认及理由。', 'case_not_found:404'),
45: ('修改Case基本信息', '已实现', 'PATCH局部更新；至少一个管理字段。省略保持；description/owner_id/severity可null清空，tags=[]清空；title/tags/handling_status不能null。负责人不自动改状态，已结案状态只能显式重开。回执含完整Case快照，随后可E03/E44读取；同键重放返回原回执。', 'case_not_found:404 case_row_version_conflict:409 case_owner_not_in_tenant:422 case_reopen_required:409 operation_key_conflict:409'),
46: ('结案', '已实现', '先E44提示未完任务及阻塞Run。running/unknown禁止结案；有未完任务须acknowledge_open_tasks=true及非空reason。无未完任务reason可省略。pending_update保留，不自动取消任务，不修改成员/判断；解决人及时间由服务保存。', 'case_not_found:404 case_row_version_conflict:409 case_active_run_prevents_close:409 case_open_tasks_confirmation_required:409 case_already_resolved:409 operation_key_conflict:409'),
47: ('重开Case', '已实现', '仅resolved案件可重开，恢复in_progress并记录reopened_at，清空当前结案字段；旧结案说明保留在E17活动。reason可选。不新建或启动Run，不改变人工任务/成员/判断。', 'case_not_found:404 case_row_version_conflict:409 case_not_resolved:409 operation_key_conflict:409'),
48: ('提交告警人工判定', '已实现', '单条人工判定，reason必填，追加反馈并保留模型分诊；误报/正常关闭，已关闭改真实威胁/需跟进恢复处理中。E28读feedback及facts，E30读活动，不自动改父事件/Case结论或启动模型。', 'subject_not_found:404 subject_row_version_conflict:409 operation_key_conflict:409'),
49: ('批量提交告警人工判定', '已实现', '仅用户明确选中的items，共用feedback判定和理由；逐项版本校验，整批成功或拒绝，默认配置最多100项。不会自动按相似度选中或批量改判。', 'subject_not_found:404 subject_row_version_conflict:409 operation_key_conflict:409 subject_batch_selection_invalid:422'),
50: ('管理单条告警', '已实现', 'PATCH省略保持，owner_id=null取消分配、tags=[]清空；仅分配不改状态，人工关闭须reason且保留原判定。返回保存时facts及activity_id，最新摘要沿E28读取。', 'subject_not_found:404 subject_row_version_conflict:409 operation_key_conflict:409 subject_owner_not_in_tenant:422 alert_close_reason_required:422'),
51: ('批量管理告警', '已实现', 'items带每条ID和expected_row_version，共用changes；批量整体事务，未选告警不改。设置负责人不自动关闭或重开。返回按ID排序的逐项快照和changed_count。', 'subject_not_found:404 subject_row_version_conflict:409 operation_key_conflict:409 subject_owner_not_in_tenant:422 subject_batch_selection_invalid:422 alert_close_reason_required:422'),
52: ('管理单个事件', '已实现', '分配未解决事件默认进入处理中；已解决仅改负责人不重开。显式resolved须resolution_note；severity_override非null须理由，null恢复自动等级且清空覆盖元数据；不改成员告警等级。', 'subject_not_found:404 subject_row_version_conflict:409 operation_key_conflict:409 subject_owner_not_in_tenant:422'),
53: ('批量管理事件', '已实现', '对明确选中事件应用共用changes；每项都验证版本、状态和理由，整批成功或拒绝。负责人/严重度/状态遵守单条规则，不修改其他事件或Case。', 'subject_not_found:404 subject_row_version_conflict:409 operation_key_conflict:409 subject_owner_not_in_tenant:422 subject_batch_selection_invalid:422'),
54: ('导出告警列表 CSV', '已实现', '复用相应列表的筛选和排序，导出本次只读快照的全部命中；columns为逗号分隔的公开字段路径，省略使用默认列。禁止limit/cursor/before_id/offset及未知参数；列名空白、重复或不支持返回422。UTF-8 BOM、逗号分隔、CRLF、字段名为表头；空结果200仅表头。null写\\N，空串留空；实际以反斜杠开头的字符串额外加一个反斜杠，以单引号开头或可能成为公式的字符串前加单引号，程序读取时按此规则去掉一个前缀再还原；数组/对象为JSON。文件包含完整范围，超过10000行或16MiB返回413，不返回截断文件；SQL限时30秒，超时503。Content-Disposition提供文件名；X-Export-Count为实际条数、X-Export-Observed-At为快照观察时间、X-Export-Schema=socai2.list-export.v1。仅查询，不写库或启动分析。', 'export_columns_invalid:422 export_pagination_not_supported:422 export_query_parameter_not_supported:422 export_row_limit_exceeded:413 export_size_limit_exceeded:413 export_query_timeout:503 export_snapshot_incomplete:503'),
55: ('导出事件列表 CSV', '已实现', '复用相应列表的筛选和排序，导出本次只读快照的全部命中；columns为逗号分隔的公开字段路径，省略使用默认列。禁止limit/cursor/before_id/offset及未知参数；列名空白、重复或不支持返回422。UTF-8 BOM、逗号分隔、CRLF、字段名为表头；空结果200仅表头。null写\\N，空串留空；实际以反斜杠开头的字符串额外加一个反斜杠，以单引号开头或可能成为公式的字符串前加单引号，程序读取时按此规则去掉一个前缀再还原；数组/对象为JSON。文件包含完整范围，超过10000行或16MiB返回413，不返回截断文件；SQL限时30秒，超时503。Content-Disposition提供文件名；X-Export-Count为实际条数、X-Export-Observed-At为快照观察时间、X-Export-Schema=socai2.list-export.v1。仅查询，不写库或启动分析。', 'export_columns_invalid:422 export_pagination_not_supported:422 export_query_parameter_not_supported:422 export_row_limit_exceeded:413 export_size_limit_exceeded:413 export_query_timeout:503 export_snapshot_incomplete:503'),
56: ('导出调查列表 CSV', '已实现', '复用相应列表的筛选和排序，导出本次只读快照的全部命中；columns为逗号分隔的公开字段路径，省略使用默认列。禁止limit/cursor/before_id/offset及未知参数；列名空白、重复或不支持返回422。UTF-8 BOM、逗号分隔、CRLF、字段名为表头；空结果200仅表头。null写\\N，空串留空；实际以反斜杠开头的字符串额外加一个反斜杠，以单引号开头或可能成为公式的字符串前加单引号，程序读取时按此规则去掉一个前缀再还原；数组/对象为JSON。文件包含完整范围，超过10000行或16MiB返回413，不返回截断文件；SQL限时30秒，超时503。Content-Disposition提供文件名；X-Export-Count为实际条数、X-Export-Observed-At为快照观察时间、X-Export-Schema=socai2.list-export.v1。仅查询，不写库或启动分析。', 'export_columns_invalid:422 export_pagination_not_supported:422 export_query_parameter_not_supported:422 export_row_limit_exceeded:413 export_size_limit_exceeded:413 export_query_timeout:503 export_snapshot_incomplete:503'),
57: ('事件归并统计', '已实现', '按当前租户告警选范围：source_namespace精确匹配告警来源并区分大小写；time_from/time_to按alerts.event_time，带时区，[起点,终点)，允许单边。时间条件排除未知时间，无时间条件包含。省略三个条件统计全租户。仅支持这三个参数；q/负责人/处理状态/排序/分页等返回422，顶部统计不沿用事件表格筛选。只数范围内告警，按当前关联去重事件；跨范围成员不扩入分母，无范围内成员的事件不计。处理中只按所计事件handling_status=in_progress。压缩比例=(已归并告警数-事件数)/已归并告警数，0..1乘100展示百分比；无已归并告警时null。未归并数量单列，不当成压缩成果，也不代表准确率或解决率。所有数量与observed_at来自同一只读快照，不写库、不触发归并或模型。', 'grouping_query_parameter_not_supported:422 read_dependency_missing:503 read_dependency_permission_denied:503 read_dependency_schema_mismatch:503'),
58: ('提交Case评论', '已实现', '提交operation_key和body纯文本原文（非空白，最多20000字符）。作者和时间由服务端保存；同案同键同作者同正文返回原评论，改内容或操作者409。只追加，不提供编辑/删除。允许已结案案件补充说明；更新案件业务时间和行版本，但不改变范围、处理状态、当前判断、任务或Run。评论不是已核实事实，不进入模型或自动成为任务。保存后用E59读取，E17回查活动。', 'case_not_found:404 operation_key_conflict:409 case_actor_not_in_tenant:403'),
59: ('读取Case评论', '已实现', '仅指定Case的普通评论，不混入成员告警、事件或其他案件评论。limit默认20、范围1–100，offset默认0、范围0–100000；按created_at及id升序。返回items、total、next_offset和observed_at，空集合明确为空；单次一致快照，跨页非冻结快照。只接受limit/offset，其他参数422。', 'case_not_found:404 comment_query_parameter_not_supported:422'),
60: ('登记Case附件引用', '已实现', '业务后端先上传并保存文件，再提交operation_key、file_id、file_name、mime_type、size_bytes及可选sha256。本服务保存案件关联、服务端登记人/时间和活动；同key同意图返回原记录，改意图409；同案同file_id另键重复409。元数据由业务后端声明，文件实时可用性和下载由业务后端决定。本服务不接收文件字节或下载URL、不查验文件，不启动调查或改任务/判断。已结案Case可补充资料，状态保持。E61/E62读回，E17查回执。', 'case_not_found:404 operation_key_conflict:409 attachment_already_linked:409 case_actor_not_in_tenant:403'),
61: ('读取Case附件目录', '已实现', '仅列本服务登记到本Case的附件引用，不混入其他Case、成员材料或Run报告。limit默认20(1–100)、offset默认0(0–100000)，按created_at/id升序；返回items/total/next_offset/observed_at，空集合为[]。同次只读一致快照，跨请求不冻结。只接受limit/offset。availability=managed_by_backend不代表文件探测或下载成功。', 'case_not_found:404 attachment_query_parameter_not_supported:422'),
62: ('读取Case单个附件信息', '已实现', '按Case和附件关联ID读取原file_id、名称、类型、大小、可选哈希及登记人/时间。该ID是本服务关联ID，file_id才是业务后端下载时使用的文件ID；下载地址由业务后端提供。本接口不返回文件字节或下载URL，不报告未核验的文件存在性。不存在或跨案件404，不接受查询参数。', 'case_not_found:404 case_attachment_not_found:404 attachment_query_parameter_not_supported:422'),
}
# 功能|状态|操作编号|对应调用与功能边界。可用指 HTTP，不代表页面接线/模型质量已验收。
FEATURE_MAP = '''
F01-01|需组合|26,30|列表 facts/owner_name/derived；资产标签用 section=assets 的真实库存匹配，人员/资产完整资料由业务后端补。
F01-02|已实现|26|按标题/ID、等级、状态、负责人、分配状态和真实发生时间查询全库；分配给我传实际owner_id。
F01-03|已实现；列选择由调用方处理|26|服务支持发生时间、入库时间和等级升降序，空值最后；列显隐由调用方处理，偏好持久化未实现。
F01-04|可用|26|读filtered_total和next_cursor展示筛选总数及续页；total/overall_stats保持租户整体，高等级含high/critical；before_id仅旧查询。
F01-05|可用|28|选 alert_id→详情，预览与跳转为前端交互，404展示不存在。
F01-06|已实现|26,51,54|E54按筛选和排序导出完整命中CSV，支持明确选列；E51批量管理。
F01-09|已实现|26|刷新GET；移除条件或改排序时清空cursor/before_id回首页，不触发分诊。
F01-07|可用|28|facts/owner_name/owner_resolution/derived；来源不明和时间缺失按原值展示。
F02-01|需组合|28,31,30|详情取得 material.id→正文及 section=objects/sources；检测标签不当事实结论。
F03-01|需组合|28,22,24|triage百分数与指定Run confidence区分量纲；判定/理由来自同一分诊版本。
F03-02|需组合|22,24,33|沿 explanation 实际来源定位工件读正文；GET不重新生成解释。
F03-03|需组合|22,24,32,33|目录选run_id→Run→trace→工件，保留失败尝试。
F08-01|部分实现|30,28|section=objects/related_alerts 后打开候选；服务同对象集合不等同近期同主机专项集合。
F03-04|可用|48,49,28,30|单条或明确勾选批量提交人工判定及理由；D02关闭/恢复，反馈与模型判断并存，详情及活动读回。
F03-05|部分实现|30,48|人工反馈已实现；同主机同战术/同IP哈希的最近专项候选仍未实现，一般related_alerts仅作参考。
F23-01|可用|50,51,28,30|单条/批量维护负责人、标签和状态；仅分配不改变告警状态，关闭须理由并保留原判定。
F13-01|需组合|30,29,3|section=incidents/cases→相应详情，零/一/多关系按返回值显示。
F13-02|部分实现|30,1,8,19|先查cases，选择已有案关联或新建，返回pending；打开助手/发送尚501。
F01-08|需组合|28,30,22|facts时间、section=activities与A目录按真实事件时间合并；缺时间单列。
F04-01|需组合|28,31|当前material.id→原始JSON/文本/标准化/富化，保留版本与availability。
F05-01|需组合|30,24,33,18|section=sources/source_artifacts；历史A取当轮输入工件，Case取冻结materials，不替换为当前材料。
F27-01|部分实现|22,24,33,30|建议从解释/结果取，section=responses读已有关联；审批及实际执行未接。
F06-01|已实现|27|标题/ID、有效等级、状态、负责人、分配状态和成员真实发生时间筛选全库，返回filtered_total和next_cursor。
F06-02|可用|27|读取overall_stats，按事件统计和观察时间展示。
F06-03|可用|29|incident_id→事实与派生摘要；诊断补E23。
F06-06|已实现|57|E57同一只读范围返回告警/已归并/未归并/事件/处理中数量和明确分母的压缩比例；不拼接两个列表统计。
F06-07|已实现|27,55|E27筛选排序分页；E55完整CSV导出及选列，显示列和复制链接由调用方处理；跨设备偏好无明确需求不实施。
F23-06|可用|53,29,30|批量管理明确选中的事件，各项版本校验，整体成功或拒绝；未选事件不变。
F23-02|可用|52,29,30|事件负责人、状态、标签和人工等级覆盖可写；解决/等级覆盖需理由，保留成员等级和原诊断。
F06-04|需组合|29,30|derived与section=members/objects，阶段来自真实成员材料。
F07-01|需组合|23,25,32|current与entries分别显示；current_unavailable_reason和失败尝试保留。
F06-05|需组合|30,29|members/objects/activities及关联来源按真实时间组合。
F08-02|需组合|30,23,33|members/objects及诊断依据组装本事件图；对象共现不标因果，无跨事件扩展。
F08-03|可用|30,28|subject=incidents,section=members；告警ID打开详情，按next_offset分页。
F08-04|需组合|30|objects与assets连接；assets是对象匹配边，total不是去重资产数，未匹配仍保留对象。
F23-03|可用|30|section=activities；显示matching_targets和截断，不按共享Case泛化主体活动。
F13-03|需组合|30,1,8,3|事件cases关系→新建/关联，incident_ids保留显式关系并展开成员；不自动start。
F09-01|可用|2|metrics整体四项，high_severity仅high；与筛选total分开。
F09-02|可用|2|q及已声明筛选+cursor；条件改变丢弃旧cursor。
F09-03|已实现；列选择由调用方处理|2|按业务更新时间、创建时间或等级升降序；列显隐由调用方处理，偏好持久化未实现。
F09-08|已实现|2,56|E02按业务更新时间筛选；E56完整CSV导出，支持明确选列。
F09-09|仅前端/部分|2|手动GET刷新；自动刷新调度由前端实现，当前正式接线未完成。
F09-10|可用|3|队列item.id→详情预览，保留当前列表位置。
F09-11|部分实现|2,10,22,23|运行入口需要组合；管理设置模块没有对应实现。
F09-04|可用|1,3,12|选择告警/事件创建→回执Case与pending→资料；不自动启动。
F09-05|可用|3|Case身份/资料刷新；owner_id名称由业务后端解析。
F23-04|可用|3,4,44,45,46,47|E44读取版本与结案条件，E45管理标题/说明/负责人/等级/标签及未结案状态，E46结案、E47重开；E04保持分类/期限。D01已实现，前端页面接线另验。
F14-01|需组合|3,10,12|定位baseline_records/历史→各Run状态/资格；全站提示为页面接线。
F09-06|需组合|3,39,10|范围成员/事件、历史、人工任务计数；缺数据不填0。
F10-01|可用|3,4,5|读版本→同时提交分类/期限+source_note→刷新；409保留编辑内容。
F11-01|可用|3,5|current_assessment/assessment及来源；不取最新失败Run覆盖。
F12-01|需组合|3,5,14|采用判断覆盖范围与当前成员比较，按真实freshness展示变更。
F12-02|需组合|3,14,24,25,43|按来源类型和身份打开指定结果/分诊/诊断/人工版本，不跳当前版本冒充旧引用。
F11-02|需组合|3,14,15|questions及原结论限制一并展示；用户需要时自行E38创建任务，无问题状态/关闭/合并接口。
F09-07|需组合|3,28,31|遍历当前成员读取材料阶段标签，原字段不足就显示未知。
F11-03|未实现|21|adopt返回501；D03理由/覆盖确认尚无已实现HTTP参数。
F20-01|部分实现|3,28,10,14,39,42|成员事实+Run结果+H版本按来源时间组装故事；Q保存尚缺。
F20-02|部分实现|3,28,10,39|已加载故事本地搜索/等级筛选；无全故事检索接口。
F20-03|仅前端/部分|3,28|维护当前选择ID，组合已读故事；不修改Case成员。
F20-04|未实现|19|仅助手预留501，不能将故事选中范围当新成员写入。
F20-05|需组合|14,43,28|条目保存真实主体/结果/revision_id后导航；故事页面接线待补。
F14-02|需组合|3,12|running/unknown与pending分组，can_start/reason决定启动按钮。
F14-03|可用|3,11,12|scope_revision→prepare→pending读取；准备不执行。
F14-04|可用|12,13,14|确认时间/比较对象→start；GET读进度，终态读result_ids；异常不盲目重复POST。
F16-01|需组合|10,12,14|历史→选Run→结果摘要，区分当前采用与历史结论。
F22-01|需组合|39|取完任务分页后按state计待办；不把questions纳入待办数。
F14-05|需组合|10,3,39|历史直接读；故事按F20组合，暂无独立故事接口。
F14-06|需组合|10,22,23|本案baseline/ai_saved历史和成员A/I目录分别组合；当前Q无新保存记录。
F15-01|需组合|12,14|state/delivery_state/usage/validation分开展示；none与缺值不同。
F16-02|需组合|14,13|读取当前和comparison_result_id两份结果；新启动可指定同案比较对象，不自动改历史。
F12-03|需组合|12,18,15,43|run.members指定材料、输入工件及冻结H修订，不能拿当前资料替换。
F13-04|需组合|3,28,29|Case members/linked_incidents→对应主体详情；member_count与截断保留。
F13-05|可用|26,27,3,8|分页选候选→读scope_revision→associations→刷新Case。
F13-06|可用|3,9|两案各读范围版本→move→刷新两案；事件显式关系不随告警移动。
F13-07|可用|51,28,30|对明确所选告警整体保存管理修改，各项带版本；未选对象、Case成员和结论不变。
F13-08|需组合|3,12|保存后读scope_revision/pending_run_id；提示范围更新，自动跟随/调度未实现。
F19-01|需组合|3,30,14,15|当前成员对象组合底图，已存图按graph_artifact_id读取并标历史轮次。
F19-02|仅前端/部分|30,15|布局/筛选/聚焦前端处理；节点详情来自原料，正式交互未接。
F25-01|未实现|30|related_alerts仅参考，不符合D05完整候选/窗口/来源校验能力。
F25-02|未实现||无探索查询、扩展、撤销状态服务。
F25-03|未实现||无保存恢复API，未使用探索表已删除，不能据此恢复旧表。
F25-04|部分实现|3,8|已确认真实候选可复用关联命令；候选产生和图到命令闭环缺失。
F26-01|未实现|19|对象范围问答尚501，scope字段未实现。
F21-01|需组合|3,30,5|遍历成员objects→按命名空间/类型/键聚合，连接evidence；无Case对象聚合端点。
F21-02|需组合|10,12,14,15|选择历史Run→其工件与结果，保留当轮范围。
F21-03|需组合|5,6,15|读取evidence及对应工件；发布已有目录用E06，非自动生成证据。
F21-04|需组合|15,16,18,31,33,34,35|按引用所属Case/Run/A/I选对应正文路由；availability不足保留来源。
F22-02|可用|39|当前任务/状态列表，offset分页；待办只统计not_started/in_progress。
F22-03|可用|3,38,41|用户明确创建，标题/负责人/期限/来源→回执任务；人员目录/通知由业务后端。
F22-04|可用|41,3,40|完整带回TaskFields和双版本后PUT，取消为state=cancelled，不删除旧版本。
F22-05|可用|41,3,40|completed需正文及有效result_scope；完成不会自动改调查判定。
F22-06|需组合|41,42,43|当前完成人/时间及修改历史按固定revision_id读取。
F22-07|可用|40,41,3|409保留用户输入→读最新版本→显示差异再确认；不能自动覆盖重试。
F22-08|部分实现|40,11,13|保存H仅生成修订；显式下一轮冻结新版本；自动C6复核和故事/Q仍未接。
F23-05|可用|17|读取匹配活动与目标前后值，按next_offset分页。
F24-01|已实现|58,59,17|E58追加普通评论，E59分页读取，E17查提交活动；不当作调查事实。
F24-02|本服务已实现|61,62|附件目录/信息可读，file_id供业务后端下载；本服务不探测文件实时存在性，文件下载由业务后端承接。
F24-03|本服务已实现|60,61,62|业务后端上传成功后调用E60登记案件关联，再用E61/E62读回；上传与文件保存由业务后端承接。
F26-02|未实现|19|无正式会话目录/历史读写；预留结构不算可用。
F26-03|未实现|19|产品范围选择尚无DTO字段，当前多传scope将422。
F26-04|未实现||无建议问题生成API。
F26-05|未实现|19|发送返回501，无真实工具或模型调度。
F26-06|未实现|19|问答执行和人工续接未实现；现有任务不自动恢复Q。
F26-07|未实现|20|save返回501，不会保存/采用/重跑。
F26-08|未实现|19,20|尚无冻结Q引用与连续追问服务。
F14-07|需组合|26,27,2,22,23,10|分页枚举有权读取主体→各分析/历史→按真实run_id去重；无全局Run接口，不能保证未编目运行的全量覆盖。
F15-02|需组合|22,23,10,12|统计已聚合目录并标范围/观察时间，不能声称全系统统计。
F16-03|需组合|14,15,24,25|按主体读正式结果/交付原件，questions随本轮结论；系统收尾和业务判断分开。
F15-03|需组合|12,32|state/delivery/usage/时间及unknown独立展示，费用缺失不填0。
F12-04|需组合|12,18,15,32,33|当轮input_artifact_id和冻结材料/任务版本，不加载当前替代历史。
F22-09|部分实现|38,19|用户从结论手动创建任务并带来源；询问结果仍501，不自动转任务。
F17-01|部分实现|12,32,15,33|按真实步骤/工件阅读已保存分析；Q记录缺失。
F17-02|需组合|12,32|steps按seq/parent_step_id组织；检查截断，无进一步步骤分页API。
F18-01|需组合|12,32,15,33|步骤引用工件ID→正文，依父主体取对应路径。
F17-03|需组合|12,32|execution_summary/usage/tool_calls保留未知值；能力快照不是质量证明。
F28-01|需组合|12,32,15,33|步骤中的工具调用与输入/输出工件组合查询目录。
F28-02|需组合|15,33|按真实工具回执分未查/失败/成功空/有结果；HTTP200不等于查询成功。
F18-02|需组合|15,16,18,31,33,34,35|引用→所属原件读取，保留摘要与完整正文的差别。
F19-03|需组合|14,15|graph_artifact_id→历史图，标冻结范围且只读。
F19-04|未实现||当前探索服务未实现；不能在历史图上偷偷改Case成员。
F16-04|需组合|14,15|report_artifact_id及delivery正文→报告，系统closing_note独立显示。
F18-03|仅前端/组合|14,15|读取已保存报告content_text→浏览器Blob下载；无单独文件下载API，不调用模型重写。
F27-02|需组合|14,15,24,25|按本轮recommendations展示建议目标/依据，不能显示为已执行。
F27-03|未实现||审批和意见链由业务后端承接，本服务无批准或执行接口。
F27-04|部分实现|30,15,33|responses及原件读取已有回执；Case真实执行闭环由业务后端，unknown不能自动重试。
'''
