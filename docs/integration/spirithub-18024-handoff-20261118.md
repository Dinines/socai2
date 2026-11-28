# SpiritHub 与 socai2 18024 接口对接交接

**当前基线复核：2026-11-19。** 以下当前接口以 21 的 `acceptance-http-20261117-r1` 为准：[Swagger](http://192.168.1.21:18080/)、[完整 OpenAPI](http://192.168.1.21:18080/handoff/openapi.json)、[仓库同版合同](../../deploy/aisoc21/acceptance-release-20261117-01/contract/openapi.json)。18024 与 Swagger 的 80 个操作业务 Schema 已现场核为一致；调用时同时核方法/路径、请求参数与正文、响应结构、成功/错误状态及异步任务 URL。下文11-18的“现网读回”仅保留为原批次证据，不代表11-19重新读取业务记录。

现场 SpiritHub 有85个入口（79通用桥接+6本地业务），与80个上游操作匹配61个；**19个当前入口未接、19个旧代理入口已退役**。此前只比较通用桥接的“缺20个”漏计了独立附件登记入口，现已更正；其余5个本地附件/响应入口不能算上游退役。完整路径及归属见[最新现场对照](../operations/evidence/investigation-integration-audit-20261119-01/live-contract-comparison.json)。同路径不等于请求/返回兼容。

上游 `/api/v1/auth/me` 现场404，当前18024不要求旧Token。部署中的SpiritHub写桥接仍调用旧身份预检，附件上传/下载/登记也有直接身份调用；需沿SpiritHub本地登录和业务校验更新转发。向对方交付本页及同版OpenAPI后，以最新合同逐项联调；尚未发布的字段设计不能当作线上返回。

日志接入责任已按负责人更新：**SpiritHub后续直接发送我方指定Kafka Topic `socai2.spirithub.events-ocsf-v1`；我方负责全量ClickHouse存储及内部适配。** 当前Vector是已运行的过渡转发；正式直写尚未切换，需约定稳定事件身份、起始范围和切换去重。类别与工具先依据现有数据盘点，不预定只接2003/2004。见[完整审计及推进顺序](../../openspec/changes/complete-socai2-investigation-chain/independent-integration-audit-20261119.md)。

核对日期为 2026-11-18，范围为告警、事件、案件、调查分析。对接基线是 21 上实际运行的 `acceptance-http-20261117-r1`。SpiritHub 现网 Web 镜像为 `local-main-bb368df8`，API 为 `trusted-reads-20261118-01`。前端调用按现网 Web 对应 revision 核对，转发路由按 API 容器实际 OpenAPI 核对。相关旧验收文档沿用各自批次的部署状态，本篇地址和状态以本次现网读回为准。

## 地址、认证和 Swagger

| 入口 | 对接约定 |
| --- | --- |
| [SpiritHub 页面](http://192.168.1.21:8080/) | 浏览器仍在 8080 登录。前端请求同源 `/api/v1/socai2/…`，SpiritHub API 检查本地会话、权限和已配置的用户映射，再转发业务请求。 |
| [socai2 业务合同 JSON](http://192.168.1.21:18024/openapi.json) | 服务地址为 `http://192.168.1.21:18024`，业务前缀为 `/api/v1/socai2`。本版已移除用户登录、Token 和角色认证，租户及记账操作者由 18024 的运行配置确定。请求字段、枚举、版本冲突等业务校验继续生效。 |
| [Swagger UI](http://192.168.1.21:18080/) · [Swagger JSON](http://192.168.1.21:18080/handoff/openapi.json) | 一套 Swagger 按“告警、事件、调查”展示 80 个业务操作。每个操作的路径、方法、参数、请求体、响应和状态码各有条目，文末逐项给出入口。现场核对 Swagger 与实际 18024 的 80 个方法和路径一致。 |

**写请求当前断在 SpiritHub 转发层。** 现网开关 `SPIRITHUB_SOC_HTTP_TRUSTED_READS=true` 已让已授权 GET 跳过上游身份预检。转发的 POST、PATCH、PUT 仍会先调用 18024 的 `GET /api/v1/auth/me`，该地址实测 404。以创建案件为例，SpiritHub 已登记 `POST /cases`，正常登录后也要先解决该转发分支，才能到达 18024 的业务处理。对接时沿用 SpiritHub 本地鉴权，将获准的业务调用发给配置的内部 18024。`SocBridge.request` 和 `api/routes/socai2.py` 分别控制转发身份及公开路由与状态码。

以下地址省略公共前缀 `/api/v1/socai2`。返回的 `detail_url`、`status_url`、`run_url` 等业务链接已包含该前缀。浏览器经 8080 同源读取这些链接，工作台的 `get()` 和 `apiClient` 已自动拼接路径前缀，调用时只保留一次。

**现网读回**来自已有真实数据，**合同对照**来自在役 Swagger、OpenAPI 与前端代码。写操作结论按合同和转发代码给出。

## 日志直写要求：我方向 SpiritHub 提出（2026-11-19）

请将清洗后的全部 OCSF 日志直接发送到下列我方 Kafka 接入点，由我方负责 ClickHouse 全量存储、字段映射及后续已有告警/调查处理。普通活动、已有告警及 partial/unclassified 日志都应发送，接入端不要求对方按2003/2004白名单过滤。

| 项目 | 明确交接值或要求 |
| --- | --- |
| Bootstrap servers | `192.168.1.21:19093` |
| 正式接收 Topic | `socai2.spirithub.events-ocsf-v1` |
| 传输协议 | `security.protocol=SSL`，服务端证书验证开启 |
| CA | 由我方受控交付现有CA公证书；对方配置自己的CA文件路径。此监听当前 `ssl.client.auth=none`，不要求客户端证书，不使用SASL用户名/密码 |
| 网络 | 发送程序所在环境须可访问上述地址；当前SSL监听返回的broker广告地址同为`192.168.1.21:19093`。该环境的连通性尚须双方直接验证 |
| Value | 一条Kafka消息承载一个完整OCSF JSON对象，使用当前1.9.0合同；不要包装为我方内部`ocsf_event`或`RawAlert` |
| Key及身份 | 使用稳定事件身份；同一记录发送重试保持Key和事件ID，原`metadata.uid`及来源标识保留。告警更新须说明原告警关联及更新标识，不能与单纯发送重试混淆 |
| 时间及原字段 | 保留原发生时间、合同约定的时间单位/时区、来源、原字段及已有`raw_data`；不把历史事件时间改成转发时间 |
| 生产端送达 | 建议`acks=all`、启用生产者幂等，发送失败保持明确状态；这不能代替稳定业务事件身份 |
| 现有转发切换 | 约定直写开始范围及切换时间；确认直写可用后收口当前Vector过渡路径，重叠范围按稳定身份处理 |

对方需回复发送程序的运行位置、采用上述接入合同的方式、预计可联调时间，以及现有消息身份/更新语义是否一致。 3a核参考源码发现metadata.uid由ingest_id生成：当前可作为清洗记录身份，不能据此确认厂商告警长期身份。请分别说明metadata.uid、metadata.original_event_uid、finding_info.uid及Kafka Key的生命周期，尤其重新采集和告警状态更新是否保持关联。我方提供CA及当前消息合同，并完成接收和落湖；这是一份准备交付的要求，尚未向对方发送消息或实施直写切换。现有回放Topic仅作为我方测试输入，不作为对方正式发送目标。

### 落湖与回放验收的简化方案

线上已核 `aisoc.raw_events.ocsf_json`、`raw_payload` 均为String。保存各类OCSF直接复用这些列，不为每种日志或未知字段建列，不另建文件原件库。这里“完整保存”就是正文写入现有湖字段时不主动截成preview；常用主机/IP/时间/class查询字段继续投影到现有列。保存JSON无需按类别扩列；来源身份、Kafka位置、设备角色及质量状态等公共列则按[最新表结构与实施规划](../../openspec/changes/complete-socai2-investigation-chain/clickhouse-lake-design-20261119.md)设计补齐。3a已定稿14列（较原候选补device_ip）及现有48列映射；3b已注册005并在23.8隔离测试库验证，正式表仍48列。

直接读取现有Kafka的固定分区及offset范围进行测试，不必先导出一套原件或重新投递一批Kafka消息；使用独立读取进度，保留正式消费组。验收在21内比较实际读取数、去重后的稳定身份数、分组内容摘要以及解析失败/未完成数量，按租户和测试范围定位湖记录。湖端摘要由**实际存储正文**重新计算，不只读输入侧附带的hash；不人工逐条审阅正文，也不把offset跨度当成消息条数。ReplacingMergeTree按逻辑去重后的记录核验，重复输入和告警更新依合同分开。出现差异再定向定位；具体日志、ID集合、统计及hash值不默认发送Codex。

64KiB/256KiB限制来自当前写入代码，不来自这两个String列的类型；3c新裸入口已移除存储侧主动截断并验证大正文；原信封入口仍保留旧行为，页面预览单独控制。线上TTL目前仍按事件时间400天；负责人已确认本次新接入改为每次入湖400天、重试刷新，旧映射保持原口径。3b已同步条件TTL及租户清理COUNT/DELETE并通过隔离库读回；已执行测试库DDL及3c完整保存、3d隔离Kafka/持久确认合成验证，正式DDL/消费者未改；3e随后完成客户指定Topic固定范围入隔离库及聚合验收，私有报告留21。3d验证实际保存后分区提交及失败/未知停止，下一步3f基本查询。

## 1. 调查列表与详情

| 当前 SpiritHub 调用或取值 | 18024 当前合同及差异 |
| --- | --- |
| `GET /runs` | 新地址是 `GET /analysis-runs`。旧地址在 8080、18024 均实测 404。新地址在 18024 已读回数据，8080 当前未登记。 [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/directory_api_v1_socai2_analysis_runs_get) |
| `kinds`、`requested_from/to`、`q` | 改用单值 `run_kind` 和带时区的 `time_from/time_to`，按 `requested_at` 前闭后开筛选。当前还有 `subject_type`、`subject_id`、`intent`、`state`、`limit`、`cursor`。指定主体 ID 时同时发 `subject_type=alert\|incident\|case`。目录没有关键词或 Run ID 搜索参数，`kinds` 原样提交会返回 422。 |
| 详情附属列表 `alert_id`、`case_id` | 只看该告警时传 `subject_type=alert&subject_id=…`，只看案件自身的 Run 时传 `subject_type=case&subject_id=…`。旧 `case_id` 曾能表示关联范围，当前主体过滤仅匹配案件自身，关联告警和事件需先取案件成员或关联记录，再按各自主体查。 |
| `items[].kind/title/stop_reason/duration_seconds/input_artifact_id/has_case` | 列表使用 `run_kind`、可能为空的 `subject_title`、`state`、`delivery_state`、`requested_at/started_at/ended_at`、`input_member_count`、`task_id`、`intent`、`results[]`、`detail_url`。停止原因和完整工件从 Run 详情取。起止时间均存在时才计算用时。无冻结成员数量为 `null`，明确保存了空成员才是 `0`。 |
| `metrics.total/partial/no_case/with_case` | 改读 `statistics.total_runs`、`by_state`、`by_delivery_state.partial`、`without_related_case_count`、`related_case_count`。前者中的无案项数计算 Run，最后一项计算去重后的不同案件。分页用 `next_cursor`，切换筛选后从第一页开始。 |
| `GET /runs/{run_id}/context` | 旧详情入口已退役。用目录项的 `detail_url`，或保存该条的 `subject_type/subject_id/run_id` 并调用各自的 Run 详情。当前没有只传 Run ID 的通用详情接口，独立详情链接需要能恢复主体信息。 [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/alert_run_api_v1_socai2_alerts__alert_id__analysis_runs__run_id__get) ·  [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/incident_run_api_v1_socai2_incidents__incident_id__analysis_runs__run_id__get) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/run_detail_api_v1_socai2_cases__case_id__runs__run_id__get) |
| `GET /runs/{run_id}/artifact-references/{artifact_id}`、`GET /runs/{run_id}/references/{reference_type}/{reference_id}/context` | 旧全局引用查询已退役。用 Run 详情给出的 `steps_url`、`artifacts_url` 继续读，工件内容按目录或步骤引用的 `content_url` 打开，保留原主体、源 Run 和工件 ID。Case 独立结果沿 `results[].url` 读取。 [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/steps_api_v1_socai2_analysis_runs__run_id__steps_get) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/step_api_v1_socai2_analysis_runs__run_id__steps__step_id__get) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/artifacts_api_v1_socai2_analysis_runs__run_id__artifacts_get) |

`run_kind` 区分 `alert_basic`、`incident_diagnosis`、`baseline`、`ai_question`、`targeted`，任务意图由 `intent` 提供。无真实任务关联的历史记录可返回 `task_id=null` 和 `intent=null`。执行状态、交付完整性和结果可用性各读各的字段。已受理任务可能还没有 Run，任务进度读 `analysis-tasks`。

**现网读回。** 18024 无筛选目录有 14 个 Run。按真实回放告警 `7362b4a0-9253-5833-b0a4-873dbbf86753` 查询命中 1 条，Run 为 `489f1b26-1a95-55fe-af59-4c5a402cd66a`。详情状态 `completed`、交付 `complete`、结果 ID `3b450977-2915-5372-8212-8107bd8a0464`，新版工件和步骤目录读回 14 件、5 步。

SpiritHub 源码入口为 `web/src/features/investigations/api.ts`、`InvestigationListPage.tsx`、`InvestigationDetailPage.tsx` 和 `soc-workbench/api.ts`。完整合同见[分析目录](run-directory-http.md)与[步骤和工件](run-records-http.md)。

## 2. 告警筛选、分诊和材料

告警列表仍用 `GET /alerts`。旧 `GET /alerts/query` 在 8080 仍登记，18024 合同已无该地址。当前前端调 `/alerts` 却仍带部分旧查询参数。 [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/alerts_api_v1_socai2_alerts_get)

| SpiritHub 当前筛选或取值 | 18024 可用口径 |
| --- | --- |
| `handling_statuses` 多选 | 单值 `handling_status`，告警支持 `new`、`in_progress`、`completed`、`unknown`。告警已完成用 `completed`，传 `closed` 或 `resolved` 会返回 422。 |
| `severity_groups`、`severity_group` | 单值 `severity=info\|low\|medium\|high\|critical`。`high` 是精确等级，旧“高严重度”合计卡片不能直接映射成 `severity=high`。 |
| `assignment=mine`、负责人选择 | `assignment_state=unassigned\|assigned\|unresolved`，或传有效的 `owner_id` UUID。“分配给我”依赖已映射到同一人员的数据，18024 无 `mine` 参数，也没有 SpiritHub 选人器当前调用的 `GET /people`。 |
| `occurred_from/to`、关键词、排序 | `time_from/time_to` 按告警 `event_time` 过滤，传带时区时间。`q` 保留，排序用 `sort_by=ingested_at\|event_time\|severity` 和 `sort_order=asc\|desc`。 |
| `source`、`tactic`、`asset_tag`、`investigating` | 当前列表合同没有这些查询条件。展示字段可继续读取，筛选控件按当前 Swagger 支持的参数调整。 |
| `total`、`metrics`、`distribution`、`missing_time_count` | 表格命中数用 `filtered_total`，全租户基数用 `total`，摘要现有键从 `overall_stats` 取。`SubjectPage` 没有旧趋势数据和独立 `metrics`。使用 `next_cursor` 翻页，切换筛选或排序后重取首屏。旧 `before_id` 不能与游标、筛选或排序同传。 |

**现网读回。** 目前 5 条告警均为 `new/medium`。旧 `handling_statuses=closed` 和 `severity_groups=critical` 在 18024 仍是 200，`filtered_total=5`。改用 `handling_status=completed` 或 `severity=critical` 均为 200，`total=5` 且 `filtered_total=0`。`handling_status=closed` 返回 422。`handling_status=new&severity=medium&limit=1` 返回真实回放告警，并给出下一页游标。此前已登录的 8080 也实测旧状态参数未生效，且基本列表、告警详情、单份材料和分诊与 18024 同源一致。[8080 只读发布证据](../operations/evidence/spirithub-real-replay-20261118-01/README.md)

告警详情保持 `GET /alerts/{alert_id}`，使用 `facts`、`derived`、`material`、`triage`、`feedback`。分诊与历史读取靠 `/analysis` 和 `/analysis/runs/{run_id}`，列表返回 `entries` 和 `next_before_run_id`。过去的 `POST /alerts/{alert_id}/analyze` 已移除，告警正常入站触发自动分诊，分析任务查询见文末。单份材料 `GET /alerts/{alert_id}/materials/{material_id}` 可读，`GET /alerts/{alert_id}/materials` 旧版本列表没有同路径。`records/sources`、`records/source_artifacts` 可读来源和来源工件，完整材料版本列表仍需明确数据来源。 [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/alert_api_v1_socai2_alerts__alert_id__get) ·  [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/alert_analysis_api_v1_socai2_alerts__alert_id__analysis_get) ·  [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/material_api_v1_socai2_alerts__alert_id__materials__material_id__get) ·  [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/task_list_api_v1_socai2_alerts__subject_id__analysis_tasks_get)

相似告警候选仍走 `GET /alerts/{alert_id}/review-candidates`。当前用 `time_from/time_to`、`limit/cursor`，输出 `AlertReviewPage`，旧 `match/window_start/window_end/seed_object_id/offset` 不在合同内。新 `same-host-alerts` 是另一条同主机查询。 [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/candidates_api_v1_socai2_alerts__alert_id__review_candidates_get) ·  [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/recent_api_v1_socai2_alerts__alert_id__same_host_alerts_get)

SpiritHub 源码入口为 `web/src/features/soc-alerts/AlertWorkbenchList.tsx`、`AlertWorkbenchRaw.tsx` 和 `soc-workbench/SubjectFilters.tsx`。

## 3. 案件新建、关联、发起与读回

| 场景 | SpiritHub 当前调用或取值 | 18024 当前合同 |
| --- | --- | --- |
| 新建案件 | `POST /cases`，旧成功合同 200 `AssociationReceipt`。案件选择弹窗及告警／事件转案件后按顶层 `receipt.case_id` 跳转，提示保存后手动启动。 | 相同地址，201 `CaseAllocationReceipt`。请求必填 UUID `operation_key` 和 1–200 字符 `title`，`alert_ids`、`incident_ids` 至少一组非空。可选 `description`、`severity`、`tags`。用 `primary_case_id` 打开首案，`allocations[]` 表示每个实际分配的案，`receiving_case_id` 是后续接收目标。每个新案的 `allocations[].initial_task` 是首轮受理回执。 [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/create_case_api_v1_socai2_cases_post) |
| 关联到已有案件 | `POST /cases/{case_id}/associations`，同样读旧的顶层 `case_id`。 | 200 `CaseAllocationReceipt`，提交 `operation_key`、`expected_scope_revision` 和选中的主体数组。读 `allocations[].case_id/scope_revision/case_url`、新增及已有成员，按实际分配结果展示。已有案的 `initial_task` 可为空。成员替换和移动也更新为分配回执结构。 [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/associate_api_v1_socai2_cases__case_id__associations_post) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/replace_members_api_v1_socai2_cases__case_id__members_put) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/move_members_api_v1_socai2_cases__case_id__members_move_post) |
| 已有案件发起调查 | 两次调用 `POST /cases/{case_id}/baseline/prepare`、`POST /cases/{case_id}/runs/{run_id}/start`，读取预建 Run、`start_eligibility` 并提交窗口。 | 两个旧地址均已退役。改为 `POST /cases/{case_id}/investigations`，请求体为 `{"operation_key":"<UUID>","mode":"check"}` 或 `mode=rerun`。`check` 核材料是否变化，无变化可跳过，`rerun` 明确再执行。当前请求体只有这两项，旧 `expected_scope_revision`、`window_start/window_end`、`comparison_result_id` 不属于该提交接口。202 返回真实任务受理回执。 [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/case_investigation_api_v1_socai2_cases__case_id__investigations_post) |
| 受理后刷新 | 按旧 `pending_run_id` 进入 Run，再轮询。 | 从 `initial_task` 或 202 响应的 `task_id/subject_type/subject_id/status/status_url` 进入任务查询。沿任务 `attempts[].run_url`、`results[].url` 读对应版本。任务可先受理后产生 Run，`latest_run_id` 可空。 [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/task_list_api_v1_socai2_cases__subject_id__analysis_tasks_get) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/task_detail_api_v1_socai2_cases__subject_id__analysis_tasks__task_id__get) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/run_detail_api_v1_socai2_cases__case_id__runs__run_id__get) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/result_detail_api_v1_socai2_cases__case_id__results__result_id__get) |

新建已受理首轮，页面可以直接观察首轮任务。相同操作沿用 `operation_key`，提交回执的 `accepted` 固定表示已受理，实时状态以 GET `status_url` 为准。`skipped/no_changes` 允许没有 Run 或结果。失败、结果未知、部分交付分别用保存状态展示。只有已保存的结果可进入结果页。转发层需要保留当前合同的 201／202 及业务错误信息。两个旧启动地址和新任务地址都要在 8080 路由配置中对应处理。

**现网读回。** 18024 案件列表有 2 条。对一条已保存案件，已依次读取分析任务、该任务对应 Run 和结果。任务与 Run 均为 `completed`，Run 的交付为 `partial`，结果 ID 与任务引用相同。本次只读核对，创建和发起尚无新版 SpiritHub 写入回执。[已有业务首轮验收](case-initial-http.md) · [分配回执](case-allocation-http.md) · [异步提交](analysis-submission-http.md) · [任务查询](analysis-tasks-http.md)

SpiritHub 源码入口为 `web/src/features/soc-cases/CaseSelectionDialog.tsx`、`CaseInvestigationOverview.tsx`、`workbench-api.ts`，以及 `web/src/features/soc-workbench/SubjectCommands.tsx`、`api.ts`。

## 4. 同批需要对齐的事件和案件页面

| 页面或功能 | 路径、参数及渲染差异 |
| --- | --- |
| 事件列表 | 保留 `GET /incidents`，旧 `GET /incidents/query` 已退役。共有筛选同告警列表。事件状态为 `new/in_progress/resolved/unknown`，排序为 `created_at/last_activity_at/severity`。时间条件匹配成员告警发生时间，当前 `SubjectPage` 同样用 `filtered_total`、`next_cursor`、`overall_stats`，而且摘要计数应按各键的实际含义展示。 [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/incidents_api_v1_socai2_incidents_get) |
| 事件详情与诊断 | 详情 `GET /incidents/{incident_id}` 增加 `case_receiving`，显示接收案、自动接收资格及原因。诊断详情 `/analysis/runs/{run_id}` 增加 `input_selection`、`analysis_coverage`，页面可据此区分已选成员、已分析成员及整体覆盖。旧同步 `POST /incidents/{incident_id}/diagnose` 的地址保留，成功合同从 200 诊断结果改为 202 任务回执，使用 `operation_key` 和 `mode=check\|rerun`，之后读事件任务。 [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/incident_api_v1_socai2_incidents__incident_id__get) ·  [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/incident_analysis_api_v1_socai2_incidents__incident_id__analysis_get) ·  [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/incident_diagnosis_api_v1_socai2_incidents__incident_id__diagnose_post) ·  [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/task_detail_api_v1_socai2_incidents__subject_id__analysis_tasks__task_id__get) |
| 案件列表及详情 | `GET /cases` 的多值 `handling_statuses/severities` 改为单值 `handling_status/severity`，`updated_from/to` 改为 `time_from/time_to`，这里按业务更新时间过滤。`sort_by` 支持 `business_updated_at/created_at/severity`，`q`、`owner_id`、`assignment_state`、`metric`、`classification` 保留。列表使用 `items/total/next_cursor/metrics`，详情、历史仍用对应 Case UUID。查询续建和共享事件关联案使用新增的 `related-cases`。 [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/case_queue_api_v1_socai2_cases_get) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/case_detail_api_v1_socai2_cases__case_id__get) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/history_api_v1_socai2_cases__case_id__history_get) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/related_cases_api_v1_socai2_cases__case_id__related_cases_get) |
| 告警、事件、案件导出 | 三个 `/export` 地址仍在，按当前筛选和 `columns` 返回 CSV。旧的 `ids`、`limit`、`cursor` 及旧复数筛选项不在 18024 导出合同。前端的“导出所选”需要明确另行取数，不能把普通筛选 CSV 当已选记录。 [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/export_alerts_api_v1_socai2_alerts_export_get) ·  [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/export_incidents_api_v1_socai2_incidents_export_get) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/export_cases_api_v1_socai2_cases_export_get) |
| 详情分区与案件故事 | 告警／事件的通用记录分区使用 `limit/offset`，旧 `material_id/include_related` 不在当前查询合同。案件故事 `GET /cases/{case_id}/story` 改用 `q/severity/limit/cursor`，旧 `kind/alert_ids/severity_groups/offset` 不在合同。当前没有旧 `/cases/{case_id}/objects`、`/cases/{case_id}/references/{type}/{id}/context` 的直接等价地址。 [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/records_api_v1_socai2__subject___identity__records__section__get) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/read_story_api_v1_socai2_cases__case_id__story_get) |
| 案件探索 | 候选查询用 `alert_id/object_id/time_from/time_to/limit/cursor`。旧 `exploration-preview` 及历史 `explorations` 列表、详情和 POST 路由已退役。先读 `exploration-base`，用 `GET/PUT /exploration` 读最近快照或保存，按当前快照指纹和版本字段提交。 [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/candidates_api_v1_socai2_cases__case_id__exploration_candidates_get) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/read_base_api_v1_socai2_cases__case_id__exploration_base_get) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/read_api_v1_socai2_cases__case_id__exploration_get) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/save_api_v1_socai2_cases__case_id__exploration_put) |
| 结果与案件助手 | `GET /cases/{case_id}/results/{result_id}` 增加对比上下文链接，采用前可以读取 `adoption-preview`。案件助手的旧 `GET /ai/messages` 已无上游地址，发送与保存两个 POST 仍在 Swagger，当前标为预留并返回 501，不能按已提供能力接线。 [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/preview_result_adoption_api_v1_socai2_cases__case_id__results__result_id__adoption_preview_get) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/ask_api_v1_socai2_cases__case_id__ai_messages_post) ·  [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/save_api_v1_socai2_cases__case_id__ai_messages__message_id__save_post) |

## 对接后验收

1. 打开 SpiritHub 调查列表，从一条有主体和 Run ID 的记录进入详情。比对 18024 的 `run_id`、`subject_id`、`state`、`delivery_state` 和结果链接，逐页检查目录计数、步骤及工件可读。
2. 对同一条告警做一次命中和一次排除筛选，确认网页实际发送单值参数，命中数等于 `filtered_total`，翻页沿用当前筛选。用同样的方法检查事件和案件列表。
3. 用一条约定的测试数据经 SpiritHub 新建案件，核对 201、实际案 ID、`allocations[].initial_task.status_url`，再读任务、Run、结果及成员归属。已有案件提交 `check` 或 `rerun` 时核对 202 与实际任务终态，查看页面能打开对应保存结果。
4. 使用测试替身时沿下表 Swagger 的字段、类型、状态码、空值和链接生成数据。先验证 8080 的路由和参数，再用同一主体 ID 核对 18024 的保存记录。

[当前发布回执](../operations/evidence/acceptance-release-20261117-01/README.md) · [SpiritHub 已登录读回](../operations/evidence/spirithub-real-replay-20261118-01/release-verification.json) · [18080 版本清单](http://192.168.1.21:18080/handoff/manifest.json)

## 18024 Swagger 逐操作索引

索引以方法和 URL 模板匹配 8080 实际登记的路由，80 个操作中 61 个同路径，19 个尚待登记。“已登记”仅表示存在路由，实际可用性以上文差异和现网读回为准。规格变化按两端 OpenAPI 的字段、类型、约束和成功码比对。预留 501 条目另作标记。18024 OpenAPI 的 SHA-256 为 `c79e3042273e0c711be97227cf37d9c424ff0619f9b10df6910440e490269277`。

### 告警

| 方法和地址 | 8080 合同对照 | 文档 |
| --- | --- | --- |
| `GET /alerts` | 查询规格变化、响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/alerts_api_v1_socai2_alerts_get) |
| `GET /alerts/export` | 查询规格变化、响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/export_alerts_api_v1_socai2_alerts_export_get) |
| `GET /alerts/{alert_id}` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/alert_api_v1_socai2_alerts__alert_id__get) |
| `GET /alerts/{alert_id}/analysis` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/alert_analysis_api_v1_socai2_alerts__alert_id__analysis_get) |
| `GET /alerts/{alert_id}/analysis/runs/{run_id}` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/alert_run_api_v1_socai2_alerts__alert_id__analysis_runs__run_id__get) |
| `GET /alerts/{alert_id}/materials/{material_id}` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/material_api_v1_socai2_alerts__alert_id__materials__material_id__get) |
| `GET /alerts/{alert_id}/review-candidates` | 查询规格变化、响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/candidates_api_v1_socai2_alerts__alert_id__review_candidates_get) |
| `GET /alerts/{alert_id}/same-host-alerts` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/recent_api_v1_socai2_alerts__alert_id__same_host_alerts_get) |
| `GET /alerts/{identity}/artifacts/{artifact_id}` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/alert_source_artifact_api_v1_socai2_alerts__identity__artifacts__artifact_id__get) |
| `GET /alerts/{subject_id}/analysis-tasks` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/task_list_api_v1_socai2_alerts__subject_id__analysis_tasks_get) |
| `GET /alerts/{subject_id}/analysis-tasks/{task_id}` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/task_detail_api_v1_socai2_alerts__subject_id__analysis_tasks__task_id__get) |
| `PATCH /alerts/{alert_id}/management` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/manage_alert_api_v1_socai2_alerts__alert_id__management_patch) |
| `POST /alerts/feedback-batch` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/feedback_batch_api_v1_socai2_alerts_feedback_batch_post) |
| `POST /alerts/management-batch` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/manage_alerts_api_v1_socai2_alerts_management_batch_post) |
| `POST /alerts/{alert_id}/feedback` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/feedback_api_v1_socai2_alerts__alert_id__feedback_post) |

### 事件

| 方法和地址 | 8080 合同对照 | 文档 |
| --- | --- | --- |
| `GET /incidents` | 查询规格变化、响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/incidents_api_v1_socai2_incidents_get) |
| `GET /incidents/export` | 查询规格变化、响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/export_incidents_api_v1_socai2_incidents_export_get) |
| `GET /incidents/grouping-summary` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/read_grouping_summary_api_v1_socai2_incidents_grouping_summary_get) |
| `GET /incidents/{identity}/artifacts/{artifact_id}` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/incident_source_artifact_api_v1_socai2_incidents__identity__artifacts__artifact_id__get) |
| `GET /incidents/{incident_id}` | 响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/incident_api_v1_socai2_incidents__incident_id__get) |
| `GET /incidents/{incident_id}/analysis` | 响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/incident_analysis_api_v1_socai2_incidents__incident_id__analysis_get) |
| `GET /incidents/{incident_id}/analysis/runs/{run_id}` | 响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/incident_run_api_v1_socai2_incidents__incident_id__analysis_runs__run_id__get) |
| `GET /incidents/{subject_id}/analysis-tasks` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/task_list_api_v1_socai2_incidents__subject_id__analysis_tasks_get) |
| `GET /incidents/{subject_id}/analysis-tasks/{task_id}` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/task_detail_api_v1_socai2_incidents__subject_id__analysis_tasks__task_id__get) |
| `PATCH /incidents/{incident_id}/management` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/manage_incident_api_v1_socai2_incidents__incident_id__management_patch) |
| `POST /incidents/management-batch` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/manage_incidents_api_v1_socai2_incidents_management_batch_post) |
| `POST /incidents/{incident_id}/diagnose` | 请求规格变化、成功状态码变化、响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E4%BA%8B%E4%BB%B6/incident_diagnosis_api_v1_socai2_incidents__incident_id__diagnose_post) |

### 案件

| 方法和地址 | 8080 合同对照 | 文档 |
| --- | --- | --- |
| `GET /cases` | 查询规格变化、响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/case_queue_api_v1_socai2_cases_get) |
| `GET /cases/export` | 查询规格变化、响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/export_cases_api_v1_socai2_cases_export_get) |
| `GET /cases/{case_id}` | 响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/case_detail_api_v1_socai2_cases__case_id__get) |
| `GET /cases/{case_id}/activities` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/case_activities_api_v1_socai2_cases__case_id__activities_get) |
| `GET /cases/{case_id}/artifacts/{artifact_id}` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/case_source_artifact_api_v1_socai2_cases__case_id__artifacts__artifact_id__get) |
| `GET /cases/{case_id}/assessments` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/assessment_history_api_v1_socai2_cases__case_id__assessments_get) |
| `GET /cases/{case_id}/attachments` | 查询规格变化、响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/list_attachments_api_v1_socai2_cases__case_id__attachments_get) |
| `GET /cases/{case_id}/attachments/{attachment_id}` | 响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/read_attachment_api_v1_socai2_cases__case_id__attachments__attachment_id__get) |
| `GET /cases/{case_id}/comments` | 查询规格变化、响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/list_comments_api_v1_socai2_cases__case_id__comments_get) |
| `GET /cases/{case_id}/exploration` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/read_api_v1_socai2_cases__case_id__exploration_get) |
| `GET /cases/{case_id}/exploration-base` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/read_base_api_v1_socai2_cases__case_id__exploration_base_get) |
| `GET /cases/{case_id}/exploration-candidates` | 查询规格变化、响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/candidates_api_v1_socai2_cases__case_id__exploration_candidates_get) |
| `GET /cases/{case_id}/history` | 响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/history_api_v1_socai2_cases__case_id__history_get) |
| `GET /cases/{case_id}/management` | 响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/management_api_v1_socai2_cases__case_id__management_get) |
| `GET /cases/{case_id}/page-data` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/page_data_api_v1_socai2_cases__case_id__page_data_get) |
| `GET /cases/{case_id}/related-cases` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/related_cases_api_v1_socai2_cases__case_id__related_cases_get) |
| `GET /cases/{case_id}/results/{result_id}` | 响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/result_detail_api_v1_socai2_cases__case_id__results__result_id__get) |
| `GET /cases/{case_id}/results/{result_id}/adoption-preview` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/preview_result_adoption_api_v1_socai2_cases__case_id__results__result_id__adoption_preview_get) |
| `GET /cases/{case_id}/runs/{run_id}` | 响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/run_detail_api_v1_socai2_cases__case_id__runs__run_id__get) |
| `GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/artifact_content_api_v1_socai2_cases__case_id__runs__run_id__artifacts__artifact_id__get) |
| `GET /cases/{case_id}/runs/{run_id}/materials/{material_id}` | 响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/frozen_material_api_v1_socai2_cases__case_id__runs__run_id__materials__material_id__get) |
| `GET /cases/{case_id}/story` | 查询规格变化、响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/read_story_api_v1_socai2_cases__case_id__story_get) |
| `GET /cases/{case_id}/tasks` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/listing_api_v1_socai2_cases__case_id__tasks_get) |
| `GET /cases/{case_id}/tasks/{task_id}` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/detail_api_v1_socai2_cases__case_id__tasks__task_id__get) |
| `GET /cases/{case_id}/tasks/{task_id}/revisions` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/revisions_api_v1_socai2_cases__case_id__tasks__task_id__revisions_get) |
| `GET /cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/revision_api_v1_socai2_cases__case_id__tasks__task_id__revisions__revision_id__get) |
| `GET /cases/{subject_id}/analysis-tasks` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/task_list_api_v1_socai2_cases__subject_id__analysis_tasks_get) |
| `GET /cases/{subject_id}/analysis-tasks/{task_id}` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/task_detail_api_v1_socai2_cases__subject_id__analysis_tasks__task_id__get) |
| `PATCH /cases/{case_id}/management` | 响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/update_management_api_v1_socai2_cases__case_id__management_patch) |
| `PATCH /cases/{case_id}/page-data` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/update_page_data_api_v1_socai2_cases__case_id__page_data_patch) |
| `POST /cases` | 成功状态码变化、响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/create_case_api_v1_socai2_cases_post) |
| `POST /cases/{case_id}/ai/messages` | 预留 501 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/ask_api_v1_socai2_cases__case_id__ai_messages_post) |
| `POST /cases/{case_id}/ai/messages/{message_id}/save` | 预留 501 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/save_api_v1_socai2_cases__case_id__ai_messages__message_id__save_post) |
| `POST /cases/{case_id}/associations` | 响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/associate_api_v1_socai2_cases__case_id__associations_post) |
| `POST /cases/{case_id}/attachments` | SpiritHub 原生文件登记 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/create_attachment_api_v1_socai2_cases__case_id__attachments_post) |
| `POST /cases/{case_id}/close` | 响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/close_case_api_v1_socai2_cases__case_id__close_post) |
| `POST /cases/{case_id}/comments` | 请求规格变化、响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/create_comment_api_v1_socai2_cases__case_id__comments_post) |
| `POST /cases/{case_id}/evidence-index` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/publish_evidence_api_v1_socai2_cases__case_id__evidence_index_post) |
| `POST /cases/{case_id}/investigations` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/case_investigation_api_v1_socai2_cases__case_id__investigations_post) |
| `POST /cases/{case_id}/members/move` | 响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/move_members_api_v1_socai2_cases__case_id__members_move_post) |
| `POST /cases/{case_id}/reopen` | 响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/reopen_case_api_v1_socai2_cases__case_id__reopen_post) |
| `POST /cases/{case_id}/results/{result_id}/adopt` | 请求规格变化、响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/adopt_result_api_v1_socai2_cases__case_id__results__result_id__adopt_post) |
| `POST /cases/{case_id}/tasks` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/create_api_v1_socai2_cases__case_id__tasks_post) |
| `PUT /cases/{case_id}/exploration` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/save_api_v1_socai2_cases__case_id__exploration_put) |
| `PUT /cases/{case_id}/members` | 响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/replace_members_api_v1_socai2_cases__case_id__members_put) |
| `PUT /cases/{case_id}/tasks/{task_id}` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/edit_api_v1_socai2_cases__case_id__tasks__task_id__put) |

### 调查公共接口

| 方法和地址 | 8080 合同对照 | 文档 |
| --- | --- | --- |
| `GET /analysis-runs` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/directory_api_v1_socai2_analysis_runs_get) |
| `GET /analysis-runs/{run_id}/artifacts` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/artifacts_api_v1_socai2_analysis_runs__run_id__artifacts_get) |
| `GET /analysis-runs/{run_id}/steps` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/steps_api_v1_socai2_analysis_runs__run_id__steps_get) |
| `GET /analysis-runs/{run_id}/steps/{step_id}` | 待接入 | [Swagger](http://192.168.1.21:18080/#/%E8%B0%83%E6%9F%A5/step_api_v1_socai2_analysis_runs__run_id__steps__step_id__get) |
| `GET /{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}` | 已登记 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/artifact_api_v1_socai2__subject___identity__analysis_runs__run_id__artifacts__artifact_id__get) |
| `GET /{subject}/{identity}/analysis/runs/{run_id}/trace` | 响应规格变化 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/trace_api_v1_socai2__subject___identity__analysis_runs__run_id__trace_get) |
| `GET /{subject}/{identity}/records/{section}` | 查询规格变化 | [Swagger](http://192.168.1.21:18080/#/%E5%91%8A%E8%AD%A6/records_api_v1_socai2__subject___identity__records__section__get) |
