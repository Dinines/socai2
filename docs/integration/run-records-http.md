# 调查步骤与原件目录 HTTP 接口

2026-11-15更新：完整步骤/原件三个GET、[统一Run列表](run-directory-http.md)及A/I/Case读取已进入当前21候选18424/18480的80操作合同，默认内部可信、无鉴权，旧18024/18080已停止。此前本机隔离验证、41次Case终态请求和47次周期边界读取保留原范围；本轮S01-r3的[真实A/I 62次GET](../operations/evidence/streaming-ai-http-20261115-01/README.md)也已通过，17步骤/45份Run工件目录和29份必要正文同源，质量NOT_PASSED保留，见[本步HTTP计划](../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#已有ai任务执行后的http联验2026-11-15)。整体正式发布仍待，本机旧服务本轮未操作。以下路径均省略`/api/v1/socai2`。

11-15[告警自动分诊查询联验](alert-auto-http.md)已完成，候选移除旧E36；原批OpenAPI/验收计数保留历史时点。已完成的第6步合同见[79操作快照](../operations/evidence/case-initial-http-20261115-01/candidate-openapi.json)；当前第7步[80操作候选](../operations/evidence/case-update-http-20261115-01/candidate-openapi.json)已装入21候选；Case本轮真实建案/执行尚待A/I通过。

## 用途与调用

告警分诊、事件诊断和Case调查使用同一组读取入口。已知Run ID后，查看完整步骤及保存原件；失败、unknown或没有结果的Run也能读。查询不启动调查、不调用模型或工具、不改业务数据。

| 方法和路径 | 输入 | 输出与操作结果 |
| --- | --- | --- |
| `GET /analysis-runs/{run_id}/steps` | run_id必填UUID；limit、cursor、kind可选 | 完整步骤分页。kind为stage/model/tool/graph/render；kind=tool只看工具步骤 |
| `GET /analysis-runs/{run_id}/steps/{step_id}` | 两个UUID必填 | 单个真实步骤，可沿parent_step_id定位父步骤。步骤不属于该Run则404 |
| `GET /analysis-runs/{run_id}/artifacts` | run_id必填；limit、cursor、step_id可选 | 本Run原件元数据分页；沿content_url读取原正文 |

Case原Run详情E12和告警/事件trace E32新增`steps_url`、`artifacts_url`。旧摘要仍有截断标记；需要全量时跟随新链接连续翻页。单次步骤摘要最多1000项、原件摘要最多200项，不再限制新目录能发现的总量。

**第7步比较读取（三任务闭环及周期样本读取已检）：** Case E12与E14响应顶层增加`previous_run_url`、`comparison_result_url`，分别进入同案冻结的上一实际Run和已选可用Result；ID为空或历史未记录则链接为null。E12的`run.comparison_context`、E14的`result.comparison_context`保存`previous_run_id/comparison_result_id/state/reason_code`；state为initial、eligible或unavailable。不可比较仍保留上一Run链接，原因区分前轮无可用结果、原输入不可读、范围不可读、范围无交集及结论不可用；不寻找更早采用结果补位。现有Case历史/故事/采用视图只复用核心四字段，不附这两个HTTP专属链接。契约详见[§8.21](../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#821-第7步case持续更新与上一轮比较http对齐和验收安排)，[本批证据](../operations/evidence/case-update-http-20261115-01/README.md)包含28次真实读取、5轮Run/Result及3次无变化跳过，核前轮失败时保留该Run、不可退到更早成功结果，19类记录前后不变。真实读取发现并修正HTTP把核心结构化对象当字典的问题，原失败保留；8个替身场景已改用实际返回类型并通过。Case investigations已完成真实执行及终态回放，41请求中21类记录不变；周期样本47 GET中两批各23类记录不变。Run顶层observed_at是每次查询时间，可推进；冻结comparison_context及原始内容保持不变。

默认每页50、最多100，来自显式[配置文件](../../deploy/http-service/run-records.json)，不是数据库表字段。部署时用`SOCAI2_RUN_RECORDS_CONFIG_FILE`选择绝对路径，见[配置及发布清单](../../deploy/http-service/README.md#完整步骤和原件读取本地实施待统一发布)。修改每页数量不必改代码。未知或重复查询参数返回422。

### Case使用了事件结论时如何核对范围

F1修复已完成[22次同源HTTP只读验证](../operations/evidence/incident-case-scope-fix-20261115-01/http-readback.md)，已进入21候选、正式发布仍待。通过Case Run的工件目录找到C1上下文，沿`content_url`读取，其`content_json.incidents.<incident_id>.diagnosis_scope`记录本轮实际选用的事件诊断范围；这不是新路由或新增的顶层HTTP DTO。

| 冻结字段 | 后端读取用途 |
| --- | --- |
| source_run_id、input_artifact_id、source_fingerprint | 定位本次使用的I Run及其原输入，核来源摘要；不能换成事件当前最新诊断 |
| input_selection | 该来源I原本选入哪些告警、选入/遗漏多少；含全部原选入范围，不随Case成员缩写 |
| analysis_coverage | 该来源I实际覆盖和待核/未分析的区别；已选入不等于已分析，待核可以属于已覆盖 |
| case_selected_alert_ids | I选入成员与本Case成员的交集 |
| case_covered_alert_ids | I实际覆盖与本Case成员的交集；概要/结论只能在这个范围关联使用 |

相邻`member_ids/case_member_ids`仍表示事件与Case的成员关系，不能拿它们当I分析范围。Case自身成员不会因I只分析1条而缩小；逐条发现/问题保留自己的原scope，关联使用交集。缺来源或范围不可用时保留原可用性及原因，不以当前事件成员补齐。C3/C6保存的model_request工件在`content_json.payload.source_map`保留实际引用关联及original_scope，可沿相同工件读取入口核对。旧Run没有该结构时不回填。

本批旧I捕获3条、只分析1条，Case仍3成员；后来事件增加第4条并保存新I，旧Case原件和来源不变。I工件元数据在`metadata`，Case工件元数据在`artifact`；两者正文均读`content_json`，保持各自现有响应合同。

### 管理变化后如何读取已有分诊

F2已通过[24次同源HTTP读回](../operations/evidence/case-input-metadata-fix-20261115-01/http-readback.md)，已进入21候选、正式发布仍待。只改负责人或标签，Case仍能使用同原材料上已完成的分诊及配对查询；检查没有业务变化时任务返回`skipped/no_changes`，没有新Run。有效人工判定作为独立材料保存，在本批明确的手动check中与原分诊一起进入新调查，旧轮原件保持。

| 读取位置/字段 | 含义与使用方式 |
| --- | --- |
| 告警GET的facts与triage | facts返回最新负责人、标签和人工判定指针；triage仍是原模型分诊及其source_run_id，两者分别保存 |
| A历史响应freshness、valid_for_current_input | 仍表示原历史请求与当前完整输入是否一致。管理/反馈编辑后可为stale/false；不能把它直接当成Case是否允许使用这份已有分析的判断 |
| Case C1 `content_json.alerts.<alert_id>.triage_usable`、triage、queries、feedback | 表示这轮实际选入的分诊是否可用，并保留原分诊、配对工具回执和独立人工反馈。同原材料且已完成的A可作为prior_analysis使用，不把管理修改或人工意见当成修改原模型结论 |
| Case任务和Run/Result | 管理后的check可跳过；有效新材料后的手动check另存新Run/Result。按原task查询状态，读取旧轮仍是旧范围和旧材料 |

公开A字段合同没有修改；本批只证明管理变化不会误删Case可用的分诊，以及手动检查正确保留反馈，不证明新的自动触发链已实施。

步骤按`seq ASC,id ASC`，原件按`captured_at ASC,id ASC`。表中没有created_at，不伪造该字段。返回next_cursor非空时继续携带同一Run和筛选条件请求；limit可调整。每次响应为同一只读数据库快照，observed_at表示这次观察时刻；正在运行的Run后续还可能新增记录，跨页不是冻结整个调查的快照。

## 分页输出

```json
{
  "run_id": "00000000-0000-4000-8000-000000000101",
  "subject_type": "case",
  "subject_id": "00000000-0000-4000-8000-000000000102",
  "items": [],
  "total": 0,
  "next_cursor": null,
  "observed_at": "2026-11-14T14:00:00Z"
}
```

上例为结构示例。subject_type为alert/incident/case，subject_id是真实所属主体；total是当前过滤条件命中的真实数量，不是本页长度。已有Run无记录时返回该空结构；不存在的Run返回404。

## 每个步骤展示什么

| 字段 | 含义 |
| --- | --- |
| id、run_id、seq | 步骤ID、所属Run及本Run内顺序 |
| parent_step_id、retry_of_step_id | 父步骤及被重试步骤；没有则null，不因过滤而丢失关联 |
| stage_code、kind、name | 业务阶段代号、步骤类型和记录名称 |
| state | planned/running/completed/failed/timeout/cancelled/skipped/unknown，按真实记录返回 |
| provider、implementation_version、question_id | 执行提供方、实现版本及关联问题标识，未记则null |
| started_at、ended_at | 实际开始、结束时间，未发生或未记则null |
| actual_args | 保存的实际参数对象，不执行其中的操作 |
| returned_rows | 工具实际返回行数；null表示未记，不当作0 |
| error、usage | 已保存的错误及用量对象；未记录则null，不编造失败原因或费用 |
| input_artifact_id、output_artifact_id、reused_artifact_id | 原有输入、输出及复用原件ID，不改其保存归属 |
| artifact_refs | 每项含role（input/output/reused）、artifact_id、run_id、subject_type、subject_id、content_url |

大段模型输入、输出和查询结果通过原件引用读取，不塞进步骤目录。跨Run复用时artifact_refs给出源Run与源主体；无Run的合法来源原件，其run_id为null，链接指向该主体的来源原件接口。

例如Case某步骤复用了告警分诊原件，返回的引用结构如下；点击链接打开告警原件，不把它算成本Case新产生的材料：

```json
{
  "role": "reused",
  "artifact_id": "00000000-0000-4000-8000-000000000103",
  "run_id": "00000000-0000-4000-8000-000000000104",
  "subject_type": "alert",
  "subject_id": "00000000-0000-4000-8000-000000000105",
  "content_url": "/api/v1/socai2/alerts/00000000-0000-4000-8000-000000000105/analysis/runs/00000000-0000-4000-8000-000000000104/artifacts/00000000-0000-4000-8000-000000000103"
}
```

## 每个原件展示什么

| 字段 | 含义 |
| --- | --- |
| id、run_id、step_id | 原件ID、所属Run、实际产生步骤；未记录步骤则null |
| kind、schema_version | 材料类别及内容结构版本，沿现有记录 |
| mime_type、file_name | 内容类型和文件名；未记录文件名则null |
| size_bytes、sha256 | 已保存的大小及摘要；未记录则null |
| captured_at | 原件实际记录时间 |
| material_state | complete/truncated/summary_only/unavailable；缺正文的元数据也保留在目录 |
| content_url | 现有正文GET地址；目录不返回content_json、content_text或内部blob_ref |

step_id过滤包括该步骤直接产生，以及该步骤input/output/reused ID指向的本Run原件，按原件ID自然去重。其他Run的复用原件只出现在步骤artifact_refs中。目录存在不代表正文可用；打开正文后按原接口availability判断，例如外部存储正文未加载仍如实返回。

## 错误

| HTTP | code | 意义及处理 |
| --- | --- | --- |
| 404 | run_not_found | Run不存在或不属于服务配置的数据范围 |
| 404 | step_not_found | 步骤不存在或不属于路径指定Run；包括artifacts的step_id筛选 |
| 422 | invalid_cursor | 游标损坏、换Run、换目录或换筛选；用新条件重新取第一页 |
| 422 | invalid_input | 超过配置单页上限、未知或重复查询参数 |
| 422 | detail数组 | UUID、枚举、数字等字段格式错误，沿FastAPI字段说明修正 |
| 503 | service_unavailable | 读取配置缺失/非法、读取开关未启用或数据库读取不可用 |

业务错误示例：`{"detail":{"code":"invalid_cursor","message":"分页游标无效或不属于当前查询","context":{}}}`。内部可信上下文沿独立服务现有配置提供，无新增登录、Token或角色要求。

## 验证及剩余边界

[本批回执](../operations/evidence/run-records-20261114-01/README.md)：本机隔离PG新数据、66次ASGI请求；Case的1001步骤分11页、201原件分3页读全，另核A/I无Case记录、跨Run及无Run来源正文、过滤、错误和空态。GET前后行内容摘要一致，无模型或工具调用。ASGI是程序内HTTP验证，不冒充正式TCP或21验收。

当前候选Swagger和服务已使用80操作统一合同，正式发布仍在整个change交付/审计收口后进行。上述原批次OpenAPI保留历史时点；统一Run列表和调度已有本机程序验证，本轮21真实A/I保存与读取已通过（模型质量NOT_PASSED），Case链及完整结束审计仍待。
