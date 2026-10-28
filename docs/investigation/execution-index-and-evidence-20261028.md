# 公共调查索引与证据跳转

2026-10-28，[后续计划](next-phase-plan-20261028.md)第5批代码完成。新增统一执行索引、Case证据/来源记录读取和报告导航；复用已有Run、步骤及工件，没有新表、迁移、模型调用或查询执行入口。尚未部署，直接验证使用数据库、模型和来源替身。

## 接口

统一前缀`/api/v2/investigation`；以下均为GET，沿用`cases:read`、`alerts:read`与当前租户身份。

| 路径 | 输入 | 输出 |
| --- | --- | --- |
| `/executions` | alert_id、incident_id、case_id恰有一个；limit默认20、1–50；cursor可选 | source、items、next_cursor，按started_at/Run ID倒序 |
| `/executions/{run_id}` | Run UUID | 单次执行的类型、状态、已知范围和原生读取地址 |
| `/cases/{case_id}/investigations/{run_id}/evidence` | 当前Case及Run | 本Run已存证据索引：evidence_id、kind、tool、available、row_count、detail_url |
| `…/evidence/{evidence_id}` | 如A1/T1/E1/H1 | 完整已存证据、来源链接、Tool准备/返回步骤链接、来源行链接 |
| `…/evidence/{evidence_id}/rows/{row_index}` | 从0开始的记录下标 | 该行原始规范化内容、来源记录ID、查询来源和证据返回地址 |

没有筛选或同时给多个业务筛选返回422。告警/事件/Case或Run不存在返回404；未知证据/行404；已有Run但尚无最终结果工件返回409 `case_evidence_not_ready`，执行中仍可使用原steps接口读取已保存步骤。索引游标绑定当前租户及业务筛选，不可挪到另一个来源。

索引与证据路由注册到当前`application:create_app`、Case独立factory，以及原program结果/启动组合factory。原`/runs/{run_id}`兼容读取路径保持独立，没有与新`/executions`冲突。

## 索引关联与旧记录边界

当前Case分析满足`analysis_profile=case_analysis.v1`，返回`run_type=case_analysis`、`native_reader=case_analysis`，保留scope、status、result_available、completion、stop_reason、最多800字符summary及summary_truncated。结果、步骤、报告、证据均指向该Case/Run既有路径，另有execution_url和前次调查previous_result_url。

- 按告警或事件筛选，以Run保存的selected_member_ids与当前来源成员相交；只在同Case内但没有被Run选入的告警不算覆盖。
- 按Case筛选，新版Run按保存的Case归属返回；即使当前Case已移除某成员，旧Run范围仍不改写。
- matched_member_ids表示当前筛选成员与原Run范围的交集；独立按Run ID读取时此字段为null，因为没有当前业务筛选。
- 不属于该profile的记录，仅凭明确的`raw_alert.id`关联来源告警。Case筛选下，这只说明其来源告警是当前Case成员，不能说明旧Run归属于该Case。

旧/其他记录返回`run_type=legacy_or_other`、`native_reader=legacy_ledger`，profile采用已存值或null；case_id、scope、result_available、completion、stop_reason及新版报告摘要均为null。result_url指向原`/api/v1/investigations/{run_id}`，steps_url指向原events，artifacts_url指向原工件列表；report_url/evidence_url为null。

旧Run的completed仅是原执行状态。索引不从历史重载的case_id推定真实Case归属，也不猜fixed/program正式发布完整度。没有明确来源告警的旧记录不会被强行塞入告警/事件/Case列表；知道Run ID时仍可读取索引元数据和原账本地址。旧fixed/program正式结果网关继续按原合同单独使用，本索引没有重新解析或改写其manifest。

## 报告到证据的导航

Case启动返回和结果GET新增顶层`navigation`；结果未就绪为null。导航由已保存result派生，不修改result正文或历史工件：

- findings、member_assessments、relationships、open_questions：按原数组index提供evidence_links，每项包含evidence_id和url。
- timeline：按原index提供evidence_url，以及有row_index时的row_url。
- evidence：全体证据编号和详情入口。

结果还增加evidence_url、execution_url、previous_result_url。告警上下文、事件概况和Case历史提供各自的executions_url。新增导航链接不改变事件概况材料指纹，不会仅因本次增加链接就触发AI概况过期。

新生成的Markdown中，发现、成员判断、关联、未决问题和证据索引使用证据链接，时间线使用具体来源行链接。链接为API相对路径，界面可据此请求对应读取接口；不是本地文件路径，也不假设新增前端页面。旧Markdown下载保持已存原文，旧结果可通过GET新增的navigation获得同样的证据入口。

## 证据来源与Tool调用

| 证据 | 读取时提供的来源关系 |
| --- | --- |
| A类告警 | 保留当次告警材料，并给source_alert_url；该URL读取当前告警，不冒充历史快照 |
| T类分诊 | 按保存的event_id定位原分诊事件，给source_run_url/source_events_url/source_event_id；来源事件不再存在时不猜原Run |
| E类Tool | 按证据编号找到已存返回步骤，再用call_id关联此前准备步骤；给request_step_url/response_step_url，准备步骤有参数、返回步骤有证据及model_message |
| H类历史判断 | 保留当次采用的前次报告，给previous_result_url |

E类正文保留query_id、query_scope、实际source、upstream_request_id等已存在字段。行读取返回原`rows[index]`，source_record_id取event_id或device_id，未提供时保持null。查询失败或空结果没有来源行，不伪造记录。

query_execution为recorded_attempt或reused，表示原保存语义，不表示这次GET发出了查询。复用证据额外提供reused_evidence_url，指向原Run的原证据；本次准备/返回步骤仍属于本次Run。旧记录缺少完整步骤时tool_trace或request_step_url可为null，不编造调用记录。

## 一个完整跳转例子

沿用[三告警例子](multi-alert-synthesis-20261028.md)：A1/A2/A3在C1中形成R1，进程Tool返回E1，第一行是event-7001。

1. 分别用`alert_id=A1`、`incident_id=I1`、`case_id=C1`读取executions；都取得R1的同一scope、result_url和report_url。
2. 读取R1结果，选择`navigation.findings[0].evidence_links`中的E1链接。
3. 读取E1详情，沿tool_trace查看准备/返回步骤；call_id相同，准备步骤保留process_activity及参数，返回步骤保留同一E1。
4. 沿rows[0].url读取event-7001。时间线的row_url也指向同一行；整个读取过程不重新查询事件湖。
5. 追加问题生成R2并复用E1时，R2的reused_evidence_url回到R1/E1，H1回到R1报告；R1工件和下载内容保持不变。

## 直接验证与实现

3个新增ASGI直接用例覆盖三个筛选到同一结果及证据/步骤/记录、追加调查历史与复用来源、旧记录原生读取及未选成员/分页。首轮有1项测试夹具未处理SQLAlchemy游标的两个独立绑定参数，修正夹具后3项通过，业务分页逻辑未因此修改。

受影响的4个多告警、7个Case、3个告警/事件关联用例通过，共14项；没有重复厂商HTTP或可用性/恢复专项。使用实际路由、SQL生成、报告/导航逻辑，数据库/模型/来源为替身；尚未验证真实PG查询执行或前端页面。OpenSpec CLI在当前Shell不可用，未执行严格CLI校验或归档。

源码：[执行索引](../../services/api/app/investigation_v2/execution_index.py)、[报告导航](../../services/api/app/investigation_v2/case_navigation.py)、[证据读取](../../services/api/app/investigation_v2/case_evidence.py)、[路由](../../services/api/app/investigation_v2/case_analysis_api.py)、[直接用例](../../services/api/tests/test_investigation_navigation.py)。
