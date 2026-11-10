> 此文件保存 2026-11-10 整理前的过程快照，仅供追溯。当前说明见仓库入口。

# 告警、事件与调查字段取数清单

本清单按保存的 JSON 核对实际存值。四个 Qwen 案例共 8 条告警、4 个事件、15 个 Run、3 个 Case、1 份正式 Result。可从各表最右列定位到一个有值样本和一个空值样本（如有）。

主表计数只来自四个 Qwen 案例。每行分母是对应的告警、成员关系、事件、Run、Case、Result 或批次数。数值 0、布尔值 false 都算有值；空数组、显式 null 和上级对象为空分别列出。长文本仅展示开头，原文在所引位置。

## 样本位置

编号 01—04 依次为账户清点、凭据转储、文件改名、运维外连。[四案包](../../../deliverables/investigation-validation-20261106/21-qwen9b-handoff-cases-20261106.zip)解压后，`01P` 表示 `cases/01/export/three-page-gets.json`，`01C` 表示同目录的 `api-responses.json`，`01D` 表示 `database.json`。其余批次按同一规则。井号后为从文件根开始的 JSON Pointer，数字从 0 起。

| 批次 | 告警 UUID（按发生时间） | 事件 UUID | Case UUID |
| --- | --- | --- | --- |
| 01 | `11e52883-0ac7-5eb2-bd15-6a7f671d2dab`、`f869898a-f078-5042-a40e-76f5a2a9b852` | `9173ab28-8dd7-4be7-97ac-897e728d23e8` | `8550d7b3-137a-5bb4-b2e1-5d0b401eca0b` |
| 02 | `9cac6b10-5533-59ae-b965-039707ab3db7`、`5cb34e88-8155-59f1-ad1d-bb21dcc93453` | `d6584044-ceaa-4354-b4fa-df13725e43f2` | 本批未建案 |
| 03 | `ee0c97ce-e1c6-5579-86df-d786f4fe438b`、`1cbfa96c-bfbd-5f38-a2bb-bcbd5878a4be` | `6309e9bb-9e1d-45c1-834f-e3214f112af9` | `8ceb9b72-bd8e-5cf1-85a2-5dbf06841829` |
| 04 | `fb716ce4-dd14-5207-8d2d-18704492f955`、`b518e199-3998-5c43-adf5-6f9bfe106486` | `ec2d4923-02de-4cbc-9aaa-5cc9adb82151` | `d37c4b03-c893-5658-b3cf-94fdf9241281` |

## 告警及原件

| 页面字段 | 四案取值情况 | 样本值与文件内位置 |
| --- | --- | --- |
| 告警 ID | 8 有值 | `11e52883-0ac7-5eb2-bd15-6a7f671d2dab` `01P#/4/body/facts/id` |
| 来源告警 ID | 8 有值 | `f692c332-6a25-5380-ba71-943f2dde0c19` `01P#/4/body/facts/source_alert_id` |
| 标题 | 8 有值 | `Account enumeration command observed` `01P#/4/body/facts/title` |
| 描述 | 8 有值 | `Recorded endpoint action; assess its scope and outcome…` `01P#/4/body/facts/description` |
| 严重度 | 8 有值 | `medium` `01P#/4/body/facts/severity` |
| 发生时间 | 8 有值 | `2026-11-06T04:01:00Z` `01P#/4/body/facts/event_time` |
| 时间来源 | 8 有值 | `source` `01P#/4/body/facts/event_time_source` |
| 处理状态 | 8 有值 | `new` `01P#/4/body/facts/handling_status` |
| 制造商 | 8 有值 | `LabTelemetry` `01P#/4/body/facts/original_vendor` |
| 负责人 | 8 null | `null` `01P#/4/body/facts/owner_id` |
| 优先级取值 | 8 null | `null` `01P#/4/body/facts/priority_value` |
| 材料 ID | 8 有值 | `067f893c-c512-5e6a-9329-b48a5488e993` `01P#/4/body/facts/latest_material_id` |
| 原始告警正文 | 8 有值 | 对象（33 键） `01P#/6/body/content_json/raw_json` |
| 规范化事件 | 8 有值 | 对象（7 键） `01P#/6/body/content_json/ocsf_json` |
| 原件 SHA-256 | 8 有值 | `eafd7e23ee4d17ccf29b389612c311f92d109fa96cc44da933aba1…` `01P#/4/body/material/retention/original_sha256` |
| 检测规则 | 8 有值 | `endpoint-observation-0` `01P#/4/body/material/detection/rule_id` |
| 检测评分 | 8 有值 | `20.8` `01P#/4/body/material/detection/confidence_value` |
| 检测评分来源 | 8 有值 | `fusion` `01P#/4/body/material/detection/score_source` |
| 检测技术列表 | 7 空集合，1 有值 | `[]` `01P#/4/body/material/detection/techniques`；数组（1 项） `04P#/9/body/material/detection/techniques` |
| 已发布分诊 ID | 7 有值，1 null | `e9fdeebb-c3ab-5b4a-a722-553e25aa274f` `01P#/4/body/facts/latest_triage_id`；`null` `03P#/9/body/facts/latest_triage_id` |
| 模型分诊 | 7 有值，1 上级为 null | `needs_review` `01P#/4/body/triage/verdict`；`null` `03P#/9/body/triage` |
| 分诊置信度 (%) | 7 有值，1 上级为 null | `65.0` `01P#/4/body/triage/confidence_percent`；`null` `03P#/9/body/triage` |
| 同次分诊理由 | 7 有值，1 上级为 null | `Evidence is insufficient to confirm malicious intent o…` `01P#/4/body/triage/rationale`；`null` `03P#/9/body/triage` |
| 分诊 Run | 7 有值，1 上级为 null | `a7772239-243d-5b11-921e-738eaa439574` `01P#/4/body/triage/source_run_id`；`null` `03P#/9/body/triage` |

## 事件及其成员

| 页面字段 | 四案取值情况 | 样本值与文件内位置 |
| --- | --- | --- |
| 事件 ID | 4 有值 | `9173ab28-8dd7-4be7-97ac-897e728d23e8` `01P#/14/body/facts/id` |
| 事件标题 | 4 有值 | `关联事件 · Account enumeration command observed` `01P#/14/body/facts/title` |
| 管理状态 | 4 有值 | `new` `01P#/14/body/facts/handling_status` |
| 负责人 | 4 null | `null` `01P#/14/body/facts/owner_id` |
| 有效严重度 | 4 有值 | `medium` `01P#/14/body/derived/severity_effective` |
| 严重度来源 | 4 有值 | `member_max` `01P#/14/body/derived/severity_source` |
| 单独指定严重度 | 4 null | `null` `01P#/14/body/facts/severity_override` |
| 成员数量 | 4 有值 | `2` `01P#/14/body/derived/member_count` |
| 去重对象数 | 4 有值 | `2` `01P#/14/body/derived/object_count` |
| 首个活动时刻 | 4 有值 | `2026-11-06T04:01:00Z` `01P#/14/body/derived/first_activity_at` |
| 末个活动时刻 | 4 有值 | `2026-11-06T04:01:15Z` `01P#/14/body/derived/last_activity_at` |
| 成员告警 ID | 8 有值 | `11e52883-0ac7-5eb2-bd15-6a7f671d2dab` `01P#/16/body/items/0/id` |
| 归并方法 | 8 有值 | `primary-entity-v2` `01P#/16/body/items/0/correlation_basis/method` |
| 成员归并原因 | 8 有值 | `no_index` `01P#/16/body/items/0/correlation_basis/reason` |
| 归并对象键 | 8 有值 | 数组（1 项） `01P#/16/body/items/0/correlation_basis/object_keys` |
| 具体归并规则 ID | 8 null | `null` `01P#/16/body/items/0/correlation_basis/rule_id` |
| 归并窗口起点 | 8 null | `null` `01P#/16/body/items/0/correlation_basis/window_start` |
| 归并窗口终点 | 8 null | `null` `01P#/16/body/items/0/correlation_basis/window_end` |
| 已发布诊断 ID | 2 有值，2 null | `911891fd-121d-5533-87a6-b42f302b565c` `01P#/14/body/facts/latest_diagnosis_id`；`null` `02P#/13/body/facts/latest_diagnosis_id` |
| 已发布诊断摘要 | 2 有值，2 上级为 null | `Incident 9173ab28-8dd7-4be7-97ac-897e728d23e8 aggregat…` `01P#/15/body/current/result/summary`；`null` `02P#/14/body/current` |
| 本案诊断尝试的状态 | 4 有值 | `completed` `01P#/15/body/entries/0/run/state` |
| 诊断尝试的停止原因 | 4 有值 | `stage_output_saved` `01P#/15/body/entries/0/run/stop_reason` |

## 调查 Run、Case 与正式结果

| 页面字段 | 四案取值情况 | 样本值与文件内位置 |
| --- | --- | --- |
| Run ID | 15 有值 | `3ece2370-1f19-4c60-9b59-5731d5ef43e7` `01D#/runs/0/id` |
| Run 主体类型 | 15 有值 | `baseline` `01D#/runs/0/kind` |
| 执行状态 | 15 有值 | `failed` `01D#/runs/0/state` |
| 交付状态 | 15 有值 | `partial` `01D#/runs/0/delivery_state` |
| 停止原因 | 15 有值 | `model_view_not_ready` `01D#/runs/0/stop_reason` |
| 实际结束时间 | 12 有值，3 null | `2026-11-06T04:15:52.797526+00:00` `01D#/runs/0/ended_at`；`null` `02D#/runs/0/ended_at` |
| 每批的 Case 总数 | 4 有值 | `1` `01P#/2/body/total` |
| Case ID | 3 有值 | `8550d7b3-137a-5bb4-b2e1-5d0b401eca0b` `01C#/0/body/case/id` |
| Case 标题 | 3 有值 | `账户清点与报表复制 local-deployed-20261106-01` `01C#/0/body/case/title` |
| 背景描述 | 3 有值 | `同一主机先执行账户信息查询，随后执行向内部共享目录复制报表的命令。核查用途、执行结果及授权。` `01C#/0/body/case/description` |
| 管理状态 | 3 有值 | `new` `01C#/0/body/case/handling_status` |
| 负责人 | 3 null | `null` `01C#/0/body/case/owner_id` |
| 人工分类 | 3 null | `null` `01C#/0/body/page_data/classification` |
| 截止时间 | 3 null | `null` `01C#/0/body/page_data/due_at` |
| Case 成员数 | 3 有值 | `2` `01C#/0/body/member_count` |
| 关联事件数 | 3 有值 | `1` `01C#/0/body/linked_incident_count` |
| 已采用的当前文字 | 3 有值 | `案件性质待核实。本案涉及 2 条告警，当前调查尚不足以确认行为性质和影响范围，需继续核查。` `01C#/0/body/page_data/determination` |
| 当前文字来源 | 3 有值 | `system` `01C#/0/body/page_data/assessment/origin` |
| 当前文字有效性 | 3 有值 | `system_only` `01C#/0/body/page_data/assessment/validity` |
| 来源 Result ID | 1 有值，2 null | `3152e631-51d7-4936-9d43-07866149c897` `01C#/0/body/page_data/assessment/sources/0/result_id`；`null` `03C#/0/body/page_data/assessment/sources/0/result_id` |
| 来源工件 ID | 1 null，2 有值 | `null` `01C#/0/body/page_data/assessment/sources/0/artifact_id`；`95291c7c-d336-4f60-a07d-f0f140cd88e0` `03C#/0/body/page_data/assessment/sources/0/artifact_id` |
| 当前判断覆盖的告警 | 3 空集合 | `[]` `01C#/0/body/page_data/assessment/alert_ids` |
| 输入新鲜度 | 3 有值 | `current` `01C#/0/body/current_assessment/input_freshness/state` |
| 独立证据状态 | 3 有值 | `not_recorded` `01C#/0/body/page_data/evidence/state` |
| 独立证据数 | 3 null | `null` `01C#/0/body/page_data/evidence/evidence_count` |
| 关联威胁数 | 3 null | `null` `01C#/0/body/page_data/evidence/threat_count` |
| 正式 Result ID | 1 有值 | `3152e631-51d7-4936-9d43-07866149c897` `01C#/4/body/result/id` |
| Result 对应 Run | 1 有值 | `3ece2370-1f19-4c60-9b59-5731d5ef43e7` `01C#/4/body/result/source_run_id` |
| Result 来源 | 1 有值 | `system` `01C#/4/body/result/conclusion_origin` |
| Result 校验状态 | 1 有值 | `system_only` `01C#/4/body/result/validation_state` |
| 结果覆盖关系行数 | 1 有值 | `2` `01C#/4/body/member_count` |
| 案件影响 | 1 有值 | 对象（5 键） `01C#/4/body/result/case_impact` |
| 图工件 ID | 1 有值 | `d147d884-081f-478c-9d4b-9c8716ab0021` `01C#/4/body/result/graph_artifact_id` |
| Markdown 报告工件 ID | 1 有值 | `1984b310-dca0-408b-ac45-314670659ad2` `01C#/4/body/delivery/markdown_artifact_id` |
| 对比结果 ID | 1 null | `null` `01C#/4/body/result/comparison_result_id` |

## 可沿来源复核的实例

| 场景 | 实际值 | 文件内位置 |
| --- | --- | --- |
| 01 检测评分（Fusion） | `20.8` | `01P#/4/body/material/detection/confidence_value` |
| 01 同一告警的 AI 分诊置信度 (%) | `65.0` | `01P#/4/body/triage/confidence_percent` |
| 01 触发告警的原始事件 ID | `e77f837c-11be-568e-aa5a-7b8f61078967` | `01P#/6/body/content_json/raw_json/source_event_ids/0` |
| 01 对应原件命令行 | `whoami.exe /all` | `01P#/6/body/content_json/ocsf_json/process/cmd_line` |
| 04 检测技术有值 | `T1059.001` | `04P#/9/body/material/detection/techniques/0` |
| 01 成员匹配的具体归并回执 ID | `ac558534-f707-506c-8b7c-f253fa1580be` | `01P#/16/body/items/1/correlation_basis/source_refs/0/id` |
| 01 同一回执的索引时长（秒） | `3600` | `01D#/artifacts/33/content_json/fused/correlation_basis/window_seconds` |
| 01 同一回执的时长含义 | `processing_time_index_ttl` | `01D#/artifacts/33/content_json/fused/correlation_basis/window_basis` |
| 02 没有当前诊断 | `null` | `02P#/14/body/current_pointer_id` |
| 02 本次诊断尝试 ID | `366c2a66-1e6e-5d61-ac00-dce790a1ce6c` | `02P#/14/body/entries/0/run/id` |
| 02 本次诊断的停止原因 | `incident_execution_uncertain` | `02P#/14/body/entries/0/run/stop_reason` |
| 03 删除卷影告警的分诊校验失败原因 | `alert_decision_basis_not_direct` | `03P#/10/body/entries/0/run/stop_reason` |
| 02 未建案时队列总数 | `0` | `02P#/2/body/total` |
| 01 系统收尾指向正式 Result | `3152e631-51d7-4936-9d43-07866149c897` | `01P#/3/body/assessment/sources/0/result_id` |
| 03 系统收尾指向工件 | `95291c7c-d336-4f60-a07d-f0f140cd88e0` | `03P#/3/body/assessment/sources/0/artifact_id` |
| 03 该工件保存的收尾文字 | `案件性质待核实。本案涉及 2 条告警，当前调查尚不足以确认行为性质和影响范围，需继续核查。` | `03D#/artifacts/34/content_json/conclusion` |
| 04 系统收尾指向工件 | `866d3134-bbfd-4a87-b09c-799a95f0d805` | `04P#/3/body/assessment/sources/0/artifact_id` |
| 04 该工件保存的收尾文字 | `案件性质待核实。本案涉及 2 条告警，当前调查尚不足以确认行为性质和影响范围，需继续核查。` | `04D#/artifacts/29/content_json/conclusion` |

## 四案以外的有值样例

下列位置取自[已保存的历史与合同样例包](../../../deliverables/investigation-validation-20261106/socai2-investigation-tests-20261106.zip)。它们用于说明有哪些实际值，不计入上面四案的分母。

**DS** · `.local/local-investigation/validation/local-eval-20261106-01/exports/20261106T022151584841Z/api-responses.json`

| 字段 | 原始值 | 文件内位置 |
| --- | --- | --- |
| 模型 Case 当前结论 | `两成员为同主机同用户的 whoami 与 robocopy 进程启动记录，启动成功；授权、数据外传与恶意性均…` | `DS#/0/body/page_data/determination` |
| 当前判断来源 | `model` | `DS#/0/body/page_data/assessment/origin` |
| 当前判断覆盖的告警 | 数组（2 项） | `DS#/0/body/page_data/assessment/alert_ids` |
| 已接受的正式 Result | `accepted` | `DS#/4/body/result/validation_state` |
| 对应的正式 Result ID | `329e5aaa-4ba9-4bdd-ac82-1c4b629fd60d` | `DS#/4/body/result/id` |

**PD** · `.local/local-investigation/page-data-20261106T013645Z/case-page-data.json`

| 字段 | 原始值 | 文件内位置 |
| --- | --- | --- |
| 管理分类 | `true_positive` | `PD#/1/page_data/classification` |
| 截止时间 | `2026-11-12T09:00:00Z` | `PD#/1/page_data/due_at` |
| 独立证据条目 | 数组（2 项） | `PD#/1/page_data/evidence/entries` |
| 证据数 | `2` | `PD#/1/page_data/evidence/evidence_count` |
| 一个关联威胁 | `1` | `PD#/1/page_data/evidence/threat_count` |
| 有索引、关联威胁为 0 | `0` | `PD#/0/page_data/evidence/threat_count` |
| 未记录证据索引 | `not_recorded` | `PD#/3/page_data/evidence/state` |
| 未记录的威胁数 | `null` | `PD#/3/page_data/evidence/threat_count` |

**H** · `.local/local-investigation/validation/local-maintenance-20261105g/exports/20261105T133839907971Z/api-responses.json`

| 字段 | 原始值 | 文件内位置 |
| --- | --- | --- |
| 已完成人工任务 ID | `55b90d9d-89be-504f-8f10-ed52726439fc` | `H#/2/body/items/0/current/task_id` |
| 人工版本 ID | `4741995b-f5fe-4eb5-937d-094c67951d15` | `H#/2/body/items/0/current/id` |
| 状态 | `completed` | `H#/2/body/items/0/current/state` |
| 完成人 ID | `ea96ee0e-f19d-5143-a0d1-1e979e294e12` | `H#/2/body/items/0/current/completed_by` |
| 完成时间 | `2026-11-05T13:19:25.875226Z` | `H#/2/body/items/0/current/completed_at` |
| 人工回复 | `Synthetic scenario driver: inventory.ps1 on local-main…` | `H#/2/body/items/0/current/result_text` |
| 人工回复覆盖的告警 ID | `561900bc-1a00-578b-9e05-e608138fad7c` | `H#/2/body/items/0/current/result_scope/alert_ids/0` |
| 首轮判断的新鲜度 | `stale` | `H#/0/body/current_assessment/input_freshness/state` |
| 判定变旧的原因 | `human_feedback_changed` | `H#/0/body/current_assessment/input_freshness/reasons/0` |
| 第二轮实际选择的前一份 Result | `5c00d9f3-41c3-44e9-96a7-615aaf5fda64` | `H#/6/body/result/comparison_result_id` |
| 第二轮对比状态 | `not_comparable` | `H#/6/body/result/change_kind` |

## 现有样本未提供的正例

范围为四个 Qwen 案、历史包中 13 个模型批次各自最后一次导出，以及四个字段合同案最后一次读回。18 份数据库快照合计 42 条告警、17 个事件、20 个 Case、15 份 Result，按各表 ID 核重。

| 字段或功能 | 本次核对得到的范围 |
| --- | --- |
| `alerts.owner_id`, `alerts.priority_value`, `alerts.latest_feedback_id` | 42 行中这些键均存在，全部为 null。 |
| `incidents.owner_id`, `incidents.severity_override` | 17 行中这些键均存在，全部为 null。 |
| `cases.owner_id`, `cases.severity`, `cases.priority_value` | 20 行中这些键均存在，全部为 null。 |
| `alert_objects.asset_ref` | 76 行中这些键均存在，全部为 null。 |
| 评论、响应执行回执、已保存的图谱探索、对话和消息 | `comments`, `response_links`, `graph_explorations`, `conversations`, `messages` 在本范围各为 0 行。 |
| 有效的二轮模型变化结论 | 15 份 Result 中 14 份为 initial，1 份为 not_comparable。后者的比较对象有值，见 H 样例。 |

旧 Case 导出存在版本差异：20 行中有 10 行同时带有 classification 和 due_at 键。PD 样例给出这两个字段的实际值；旧导出缺键与新导出中的 null 分别解释。

## 取值边界

- 事件的活动起止时间与成员的归并窗口分别取数。活动时间有值；四案的归并窗口及具体规则 ID 为 null，归并方法、共享对象与逐成员理由有值。告警检测规则来自告警材料。
- 告警的检测评分与模型分诊置信度来自两处。事件事实和成员在诊断超时后仍有值，当前诊断与本次尝试状态各有自己的记录。
- 01 的系统文字引用正式 Result；03、04 的系统文字引用工件，正式 Result 数量为 0；02 的 Case 队列总数为 0。系统结论覆盖的告警数与 Case 的成员数分开。
- 范围仅限列出的原件。负责人、具体归并规则 ID 等在四案内为空的字段，只能确认键和值的状态。现有 H 样例证明任务及选定比较对象可记录；第二轮为 `not_comparable`，有效的第二轮变化结论仍缺样例。
