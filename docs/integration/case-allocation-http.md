# Case成员分配与关联查询接口

2026-11-15：当前21候选18424 API/18480 Swagger为80操作、无鉴权，旧18024/18080已停止。成员分配及Case首轮合同已进入候选；原第5步72次隔离PG/ASGI请求与23项直接检查保留原批次范围。S01真实A/I保存及62次GET已通过（正文质量NOT_PASSED）；本轮[整事件与A01固定范围创建请求](../operations/evidence/streaming-case-http-20261115-01/README.md)已按顺序完成2次POST/5次GET受理验证，返回两个独立Case及真实initial任务；受理时无Run；随后[首轮结果58次GET](../operations/evidence/streaming-case-result-http-20261115-01/README.md)已通过，两案各1个Run/Result，冻结范围3/1、当前判断及首轮比较空态与保存一致。两结果accepted/uncertain/partial，不以执行完成代表质量通过。当前状态以[交接指南](../../FRONTEND_BACKEND_HANDOFF.md)为准。

第7步F4已补[事件诊断完成后容量续建的直接验收](../operations/evidence/case-trigger-fix-20261115-01/http-readback.md)：新案只有实际新增告警，保存自己的initial任务/Run/Result，关联与事件接收目标可读；测试容量2来自该批配置，正式默认100保持，尚未发布。

这组接口解决三个问题：一次选择的告警实际放进哪些案件；案件达到容量后续建到了哪里；一个事件后续的新告警由哪个案件接收。分配由调查核心完成，HTTP只接收业务输入、返回保存结果，不调用模型或调度器。默认内部可信，无登录、Token和角色校验；租户和记录操作人由服务配置提供。

路径均省略`/api/v1/socai2`。

## 四个写操作

| 功能与路径 | 输入 | 保存结果 |
| --- | --- | --- |
| 创建案件：`POST /cases` | operation_key、title；可选description/severity/tags；alert_ids和incident_ids至少一组非空 | 201。创建独立首案，按实际容量分配；必要时续建。每个新案登记自己的首轮任务，无预建Run。 |
| 关联成员/事件：`POST /cases/{case_id}/associations` | 路径case_id；operation_key、expected_scope_revision；alert_ids和incident_ids至少一组非空 | 200。核请求案版本，沿该案的续建关系找实际接收案，返回本次各案分配；明确关联整个事件时设置其接收目标。 |
| 替换本案成员：`PUT /cases/{case_id}/members` | 路径case_id；operation_key、expected_scope_revision、alert_ids（允许空数组） | 200。只移除请求案中未保留的成员；保留的仍在原案，新增部分按容量分配。空数组清空本案，不清空整串案件、不登记新任务。 |
| 移动成员：`POST /cases/{case_id}/members/move` | 路径为源case_id；operation_key、target_case_id、expected_source_scope_revision、expected_target_scope_revision、alert_ids | 200。返回源案实际移出、源版本，以及目标串实际接收/续建的分配。 |

ID均为UUID；版本为非负整数。创建标题必填，长度1–200且不能全空白；description最多20000字符，tags最多50项、每项1–128字符，重复值拒绝。显式告警/事件ID数组各最多200项且不可重复；移动必须至少选择一条。200是一次请求的显式ID个数限制，不是来源事件的成员上限。

整事件选择读取全部真实成员，不使用事件诊断本轮选入的100条代替。单案容量来自显式配置，默认100。成员已在同一续建串中时返回原归属，不复制进最新案；不同独立案件可拥有同一告警。移除产生的排除按既定规则由核心保存，后续自动跟随不会把它重新加回；用户明确重新添加单条告警才解除相应排除。

沿用原operation_key重放相同请求，返回当时保存的完整回执；即使接收案后来已改变，也不会按新目标重新分配。相同key换内容发生冲突。全部成员、关联、版本、接收指针和新任务在同一事务保存，错误不能留下部分成功。

## 分配回执

创建和关联返回`CaseAllocationReceipt`：

| 字段 | 含义 |
| --- | --- |
| operation_key | 本次原操作UUID。 |
| requested_case_id | 创建时为null；关联时为路径Case；移动中为显式目标Case。 |
| primary_case_id | 创建的首Case或明确请求的目标，不表示所有新增都进了这个案。 |
| continuation_root_case_id | 本次分配所属续建串的最初Case。 |
| receiving_case_id | 本次操作结束时，该串实际接收后续新增的Case。 |
| changed | 本次实际是否发生业务变化。 |
| allocations | 按续建顺序返回本次实际涉及的目标Case，一案一项；成员已有归属也保留。 |
| incident_receivers | 本次显式关联或续建实际设置的事件接收目标，每项incident_id、active_case_id。 |
| excluded_alert_ids | 本次来源集合中因同串排除而未分配的告警ID；不含已有归属，空时为[]。 |

每个`allocations`项：

| 字段 | 含义 |
| --- | --- |
| case_id、scope_revision | 实际案件身份及保存后的范围版本。 |
| created、changed | 是否本次新建，以及是否有实际变化。 |
| previous_case_id | 因容量续建的前一案；独立首案为null。 |
| added_alert_ids | 本次实际加入该案的告警，不是整个案的全部成员。 |
| existing_alert_ids | 本次选择中已经属于该案的告警，表示去重后的原归属。 |
| linked_incident_ids | 本次实际新增的显式事件关联；关系原有而只改变接收目标时为空，实际切换看incident_receivers。 |
| initial_task | 本次新案真实首轮受理回执；不是新案时为null。 |
| case_url | 该案件HTTP详情的相对地址，由HTTP适配补充。 |

`initial_task`包含task_id、subject_type=case、subject_id、status=accepted、status_url。accepted仅表示保存受理，不能展示成已经分析完成。[第6步首轮执行](case-initial-http.md)已通过调度、保存和读取联验，任务的最新状态仍须GET查询。最新任务状态沿status_url查询，不用重复创建接口查询进度。

替换返回`{source,allocation}`；移动返回`{source,allocation,moved_alert_ids}`。source为`{case_id,scope_revision,removed_alert_ids,changed}`，保留请求源案的真实变化。allocation为上述完整分配回执，不能只取receiving_case_id而丢弃其他案的分配。

source.changed表示源案最终是否发生变化，不只看有没有移除。原案1条替换为2条时，removed_alert_ids=[]但changed=true；仅往已有接收后案新增且请求旧案自身无变化时为false。

例如A已有99条，再关联5条：返回A新增1条，B新建并接收4条；B有自己的首轮task，receiving_case_id=B。查询A仍可看到A自己的100条和历史调查，旧Run/结论不会转移到B。

## 续建关系与两级关联列表

CaseView增加`continuation={root_case_id,previous_case_id,receiving_case_id}`。首案root/receiving初始指向自己；后续案的receiving由核心沿root解析。历史未记录时为null，不从相同标题、共享告警猜测续建。

`GET /cases/{case_id}/related-cases`只读关联列表，参数limit可省略（配置默认50）、cursor可省略。返回case_id、relation_revision、items、total、next_cursor、observed_at；total为完整关联集合的去重数，不是本页长度。

每项包含：

- case_id、title、handling_status、severity、case_url：用于识别并进入实际案件，severity可空。
- relation_types、primary_relation：`continuation`为容量续建，`shared_incident`为共享事件；两类都命中只返回一次，优先归续建组但保留两种关系。
- continuation：实际续建信息；不适用为null。
- shared_incidents：共同事件的incident_id、title及两侧current_case_sources/related_case_sources；`explicit`表示显式关联事件，`member_alert`表示通过成员告警推导，不能混称显式跟随。

顺序固定为续建组优先、仅共享事件其次；各组按Case创建时间、UUID升序。游标绑定关系摘要，关系变化导致旧游标失效时返回409/cursor_stale，重取第一页。标题等展示字段更新不产生虚假关联。无关联返回total=0、items=[]。查看列表不会切换事件接收者或启动调查。

## 事件接收目标

`GET /incidents/{incident_id}`增加事件专属`case_receiving`：

| 字段 | 含义 |
| --- | --- |
| active_case_id | 后续新告警唯一接收Case；未设置为null。 |
| can_receive_automatically | 当前是否满足目标存在、开放及自动窗口条件；不代表正在执行。 |
| reason_code | 可接收时为null；否则为no_target、closed或auto_window_expired。 |

`GET /incidents/{incident_id}/records/cases`保持原分页和完整关联，每项增加is_active_receiver。多个历史/共享关联案仍保留，只标明其中真实的接收目标。告警详情与告警cases行不增加这些字段。

明确关联整个事件可以设置其接收目标；单条告警关联、普通调查、GET或打开页面都不会抢回接收权。接收案关闭或过期时，不能通过自动续建绕过限制；同输入分析失败停止标记不等于禁止新告警加入。本步仅提供相关核心用例与查询，周期自动跟随在后续第7步接通。

## 错误、配置和验收状态

| HTTP / code | 含义及调用方处理 |
| --- | --- |
| 404 / case_not_found、member_alert_not_found、case_incident_not_found | 案件、所选告警或事件不存在；检查输入身份，不把失败当空列表。 |
| 409 / operation_conflict | 同操作key已用于不同请求；保留原key查询或重放原请求，不用改key掩盖未知保存结果。 |
| 409 / scope_conflict | 请求案范围版本已变；重新读版本并明确本次选择。 |
| 409 / subject_closed | 涉及的案件已关闭，不能通过续建绕过关闭。 |
| 409 / empty_scope | 所选事件没有可用成员；不留下空新案/伪任务。E07合法空数组不属于此错误。 |
| 409 / case_continuation_unavailable | 旧案未记录续建身份；不猜补或自动迁入。 |
| 409 / case_source_namespace_mismatch、case_source_scope_unverified | 来源不一致或来源范围无法确认，整笔拒绝。 |
| 409 / case_move_member_not_in_source | 所选移出告警已不在请求源案；刷新成员后明确操作。 |
| 409 / cursor_stale | 关联集合或顺序改变；从第一页重新读取。 |
| 422 / case_move_requires_different_target、invalid_input、invalid_cursor | 目标与源案相同、分页/查询参数不合法或游标不属于当前查询。 |
| 422 / detail数组 | 请求字段、UUID、重复ID、额外字段等校验失败。 |
| 503 / service_unavailable | 配置或保存依赖不可用；未确认保存不返回假任务。同key可读回已持久回执。 |

业务错误格式为`{"detail":{"code":"scope_conflict","message":"scope_conflict","context":{}}}`。code是稳定处理依据，message用于说明；不依赖message判断业务分支。[实际请求/返回示例](../operations/evidence/case-allocation-http-20261115-01/examples.json)来自本轮隔离数据，不能把其中UUID用于21正式库。

配置文件由`SOCAI2_CASE_ALLOCATION_CONFIG_FILE`明确指定，包含容量、来源读取批量及关联列表默认/最大页数；任务策略沿已有`SOCAI2_ANALYSIS_TASKS_CONFIG_FILE`，身份沿`SOCAI2_HTTP_CONTEXT_FILE`。核心和HTTP使用相同版本，不添加旧回执兼容分支。

先应用核心增量129再加载本版ORM/读写代码；正式环境本轮未迁移。统一打包依赖见[HTTP发布片段](../../deploy/http-service/case-allocation-release-fragment.json)，本地和21各自沿明确profile，不因架构不同共用启动文件。片段不是可单独执行的部署profile。

本步安排和最终结果见[OpenSpec 8.18](../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#818-第5步case成员分配与受理http配合安排)。99+5、完整263成员事件、多案历史回执、替换/移动/排除、关系分页和游标失效、事件接收资格均已真实保存读回。Case详情/列表/管理GET及管理回执的continuation一致；只读阶段13类记录摘要保持。核心显式分配和跟随用例已验，周期跟随尚未接入。

**第5步历史边界：** 本批新案只登记initial任务，均accepted、无attempt/Run，零模型/Redis/Case执行调用。后续[第6步独立批](case-initial-http.md)已执行首轮并读回；Case investigations仍404，待第7步。普通AI对话继续暂停，未部署、提交或推送。
