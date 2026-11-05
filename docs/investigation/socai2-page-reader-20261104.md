# 告警与事件页面：新表字段读取对照

2026-11-04，OpenSpec `complete-socai2-investigation-chain` 3.3。本批补齐新表页面字段读取和A/I执行留痕出口，页面本身不改。开发仍在主目录`E:/aisoc/socai2`的`codex/case-baseline-history-20261103`分支。以下是当前新表合同，不把旧`aisoc.public.alerts`当作新`socai2.alerts`，也不回退读取旧告警数据。

核对基准为当前仓库的[产品要求](../design/alert-incident-case-product-requirements.md)、[告警字段合同](../design/alert-ui-data-contract.md)、[数据展示说明](../design/incident-alert-data-showcase.md)及[原型取数口径](../../prototypes/security-pages-v2/app.js)，结合用户已确认的16项语义。历史字段文档中尚待确认的原厂、总体统计等，以用户后续决定和本文实际新表出口为准。本批未刷新远端分支，不将旧数据库样例值冒充新表真实生产值。

## 入口和边界

新增`PageReadService`、明确类型的主体/派生字段DTO和8个OpenAPI路径模板。默认`SOCAI2_PAGE_READ_ENABLED=false`，关闭返回503；开启仍要求认证租户与`alerts:read`，Case关联目录额外要求`cases:read`。沿用只读、可重复读事务，一个响应内主字段、关系和计数来自同一快照。没有模型/Tool/外部厂商调用、缓存写入或业务时间更新。

| GET路径，统一前缀`/api/v1/socai2` | 返回 |
| --- | --- |
| `/alerts`、`/incidents` | 主体列表及同租户总体统计；limit 1–50，before_id双键分页 |
| `/alerts/{id}`、`/incidents/{id}` | 与列表同合同的主体事实、派生字段及下钻地址 |
| `/{subject}/{id}/records/{section}` | members/incidents/objects/sources/assets/cases/comments/activities/related_alerts/responses；不适用集合404 |
| `/alerts/{id}/materials/{material_id}` | 当前或历史材料的已保存原文、OCSF及富化；超128KiB返回元数据和明确原因 |
| `/{subject}/{id}/analysis/runs/{run_id}/trace` | 同主体同Run步骤、工件目录、全部模型用量及时间 |
| `/{subject}/{id}/analysis/runs/{run_id}/artifacts/{artifact_id}` | 同主体同Run工件正文；核身份、hash和大小，不加载外部blob |

`subject`仅接受alerts/incidents。集合默认50、最多200、offset最多100000；返回total、next_offset、observed_at和限制。活动只返回匹配当前主体的目标，最多200并有截断标记。步骤目录最多1000、工件目录最多200，各自有总数和截断；模型用量聚合查询全部模型步骤，最后记录时间也取全量。

列表固定按告警入库时间/事件创建时间与UUID倒序读取；不是按发生时间排序的正式交互实现。搜索、时间筛选、自选排序、导出、管理保存、级联关闭/分配由页面/业务负责人承接。已确认导出“选中则所选，否则最多前200”保留为后续操作合同，不把此GET当成已经实现导出。

## 逐项字段对照

以下共73项：告警31、事件23、共享数据19。表名均为新`socai2` schema，只有人员目录和资产台账使用已有`public.users/assets`。`facts`是明确字段类型的存储投影，`derived`是明确类型的派生投影；持久JSON正文沿用既有合同，不另造公共枚举。

### 告警字段

| 项 | 页面数据 | 存储或计算来源 | 实际读取出口/空值语义 |
| --- | --- | --- | --- |
| A01 | 告警ID | alerts.id UUID | facts.id，不能与来源ID/RunID混用 |
| A02 | 告警名称 | alerts.title text | facts.title，不用AI摘要替换 |
| A03 | 来源说明 | alerts.description nullable text | facts.description，独立于Explain |
| A04 | 严重程度 | alerts.severity/severity_raw | facts原值；derived.severity_group将critical/high→high、medium→medium、low/info→low，未知null |
| A05 | 告警发生时间 | alerts.event_time nullable timestamptz | facts.event_time，不用入库时间补空；保UTC时区与精度 |
| A06 | 时间可信来源 | alerts.event_time_source枚举 | facts.event_time_source；source/derived_source/unknown |
| A07 | 首末活动时间 | alerts.first_seen_at/last_seen_at | facts同名，独立于该条event_time |
| A08 | 入库时间 | alerts.ingested_at | facts.ingested_at；列表当前固定分页时钟 |
| A09 | 材料更新时间 | alerts.source_updated_at | facts.source_updated_at，不冒充处理活动 |
| A10 | 业务更新时间 | alerts.business_updated_at | facts.business_updated_at，GET不刷新 |
| A11 | 处理状态 | alerts.handling_status | facts；new/in_progress/completed/unknown，与Run及判定分开 |
| A12 | 当前判定/误报标记 | alerts.disposition | facts.disposition；derived.false_positive仅按当前判定，不能据此推导关闭 |
| A13 | 负责人ID及分配状态 | alerts.owner_id/assignment_state/owner_source_value/assigned_at | facts原值；未分配与ID未解析分开 |
| A14 | 负责人姓名 | 同租户public.users.id→username | owner_name；owner_resolution为unassigned/resolved/unresolved，不用受影响账号代替 |
| A15 | 检测源原厂 | alerts.original_vendor | facts.original_vendor；未知null，不拿Splunk/connector_type补原厂 |
| A16 | 接入来源编号 | alerts.source_alert_id | facts.source_alert_id，沿用户确认口径 |
| A17 | 厂商原始告警编号 | alerts.vendor_alert_id | facts.vendor_alert_id，独立于接入来源编号 |
| A18 | 来源环境/连接器 | alerts.source_namespace/connector_id/connector_type | facts；保环境区分，不输出内部source_identity_key |
| A19 | 原通用分类 | alerts.category | facts.category，不冒充ATT&CK战术 |
| A20 | 检测规则 | 当前alert_materials.detection.rule_id/rule_name | material.detection；已有则返回，不猜或补查规则正文 |
| A21 | 战术/技术标签 | 当前material.detection.tactics/techniques | material.detection；derived.tactics去掉同告警重复战术后计数，仍是检测标签 |
| A22 | 检测置信度 | material.detection.confidence_state/value/label/rationale/score_source | material.detection，未算/失败不能补50或拿分诊替代 |
| A23 | 同次分诊判断/理由 | alerts.latest_triage_id→alert_assessments | triage.id/source_run_id/input_material_id/verdict/rationale/producer/assessed_at配对 |
| A24 | 分诊评分 | 同一assessment.confidence/score_state | triage.confidence及confidence_percent；available才换算×100，0有效、未知不补0 |
| A25 | 分诊适用性 | 同Run、同告警、材料配对、freshness SQL、Run状态 | triage.freshness/run_state/valid_for_current_input；人工改判不与旧分诊评分混配 |
| A26 | 当前人工反馈 | alerts.latest_feedback_id→alert_assessments.kind=human_feedback | feedback保actor/判定/理由/时间，独立于triage |
| A27 | 优先级 | alerts.priority_value/state/source/basis | facts；0与null分开，不当作分诊置信度 |
| A28 | 告警标记 | alerts.tags | facts.tags，不能用作资产标签 |
| A29 | 关闭/重开信息 | alerts.closed_at/closed_by/reopened_at | facts原值；不按时间非空反推当前状态 |
| A30 | 当前材料及Explain身份 | alerts.latest_material_id/latest_explanation_id | facts指针；material元数据与正文地址，Explain从已有analysis出口读 |
| A31 | 并发版本 | alerts.row_version | facts.row_version；只读返回，管理写入尚非本批 |

### 事件字段

| 项 | 页面数据 | 存储或计算来源 | 实际读取出口/空值语义 |
| --- | --- | --- | --- |
| I01 | 事件ID及来源身份 | incidents.id/source_namespace/source_incident_id | facts；不拿任意成员ID冒充事件 |
| I02 | 独立名称 | incidents.title | facts.title |
| I03 | 独立说明 | incidents.description | facts.description；诊断另从analysis读 |
| I04 | 事件处理状态 | incidents.handling_status | facts；不按负责人或Run完成推导事件状态 |
| I05 | 负责人/分配 | incidents.owner_id/assignment_state/owner_source_value/assigned_at | facts及同租户owner_name/owner_resolution |
| I06 | 事件标记 | incidents.tags | facts.tags；独立于成员及资产标签 |
| I07 | 自动严重度 | 当前全部成员alerts.severity最高已知级 | derived.severity_auto；未知成员数单列，无已知值为null |
| I08 | 人工覆盖严重度 | incidents.severity_override | facts及derived.severity_effective；覆盖优先，不修改成员 |
| I09 | 覆盖理由/人/时间 | incidents.severity_override_reason/by/at | facts；derived.severity_source标manual_override/member_max/null |
| I10 | 优先级及依据 | incidents.priority_value/state/source/basis | facts，不聚合成员分诊分数 |
| I11 | 解决说明/人/时间 | incidents.resolution_note/resolved_by/resolved_at | facts；无值不编造已解决理由 |
| I12 | 重开时间 | incidents.reopened_at | facts原值 |
| I13 | 创建时间 | incidents.created_at | facts；事件列表固定分页时钟 |
| I14 | 最近业务更新时间 | max(incidents.business_updated_at,全部成员alerts.business_updated_at) | derived.updated_at；facts仍保事件自身时钟，不混入source_updated_at/Run进度 |
| I15 | 最早活动时间 | min(当前成员alerts.event_time) | derived.first_activity_at；符合用户“事件包含告警最早时间”，成员未知数另列 |
| I16 | 最晚活动时间 | max(当前成员alerts.event_time) | derived.last_activity_at，未知不补NOW |
| I17 | 成员总数 | incident_alerts全部当前成员 | derived.member_count；不受members返回页大小影响 |
| I18 | 对象总数 | 当前成员当前材料的namespace/type/object_key去重 | derived.object_count；与库存资产数不同 |
| I19 | ATT&CK阶段计数 | 当前成员当前材料detection.tactics | derived.tactics，每成员每阶段最多1；带“阶段之和可能超过告警数”提示 |
| I20 | 当前诊断身份 | incidents.latest_diagnosis_id | facts；已有analysis返回状态、正文、未决、来源与新鲜度，不用归并摘要替代 |
| I21 | 全部事件/处理中/活跃/未知 | incidents处理状态总体聚合 | overall_stats.total/in_progress/active/unknown；活跃仅new和in_progress |
| I22 | 待分配/24h新告警/高等级 | 全部unassigned；成员event_time在最近24h的事件去重；有效严重度为high/critical | overall_stats.unassigned/new_alerts_24h/high_severity；与本地原型口径一致，包含未分配的已解决事件 |
| I23 | 队列压缩基础计数/版本 | 全部incident_alerts的告警去重数；incidents.row_version | overall_stats.grouped_alert_count和total可供计算；facts.row_version，不从当前页算总体压缩 |

### 关系、材料与执行字段

| 项 | 页面数据 | 存储或计算来源 | 实际读取出口/边界 |
| --- | --- | --- | --- |
| X01 | 事件成员及归并依据 | incident_alerts→alerts | records/members，linked_at/membership_source/correlation_basis/basis_version及成员事实 |
| X02 | 告警所属事件 | incident_alerts→incidents | records/incidents；当前关系和依据，不能按标题猜 |
| X03 | 对象/IOC与告警边 | alert_objects，限定当前材料 | records/objects保成员/材料/namespace/type/role/path/attributes；用于已有关系图，不是因果图 |
| X04 | 来源记录及候选关系 | alert_source_refs，限定当前材料 | records/sources保source_event_id/relation_kind/source_path/observed_at；完整性见material.source_scope |
| X05 | 库存资产名称及标签 | 同租户public.assets，精确主机名/FQDN/IP匹配 | records/assets；asset_id/name/tags等为台账值，返回object_id/alert_id/material_id和match_basis |
| X06 | 库存匹配不确定性 | 当前台账查询，非持久身份确认 | assets.limitations明确无namespace台账、多匹配均保留；total计对象-资产边，不能冒称唯一资产数 |
| X07 | 相关告警候选 | 当前材料对象同namespace/type/object_key | records/related_alerts，排除当前范围；不等于攻击因果/完整历史日志/已选反馈目标 |
| X08 | Case关联 | case_alerts与case_incidents分别查询 | records/cases有via_member_alert/explicit_incident_link；共享成员不自动当显式事件关联，要求cases:read |
| X09 | 评论 | comments的准确alert_id或incident_id | records/comments保body、作者快照、创建/编辑时间；不借用其他Case评论 |
| X10 | 处理活动 | activities明确subject或activity_targets准确目标 | records/activities保actor/action/summary/detail/occurred_at及匹配目标的before/after/result/reason；不混入共享Case全部活动 |
| X11 | 审批与执行引用 | response_links的准确主体 | records/responses保external_namespace/proposal/legacy_ref/approval/action/receipt ID；仅引用不等于获批或已执行 |
| X12 | 原始材料及留存状态 | alert_materials指定告警/版本 | materials入口返回raw_json/raw_text/ocsf_json/enrichment、material_state/retention；超限明确，不拿摘要冒充全文 |
| X13 | 基础调查执行中 | runs.kind=baseline且running，关联冻结run_members | 告警overall_stats.investigating按告警去重；每主体derived.baseline_execution_counts分running/unknown，A/I不计入 |
| X14 | A/I步骤/输入输出/错误 | run_steps按当前主体Run身份 | trace.steps保seq/父步骤/kind/stage/state/name/参数/返回行数/工件ID/错误与时间 |
| X15 | 模型Token及费用 | 全部model步骤usage | trace.usage区分已知合计/未知调用/total=null；费用按币种和计价版本分组，不跨币种相加 |
| X16 | Tool调用数/耗时/最后记录 | 全部步骤/工件及Run时钟 | trace.tool_calls/duration_seconds/last_recorded_at；阶段父节点不重复计模型用量，未结束不编完成耗时 |
| X17 | 工件目录及正文可用性 | artifacts同租户/主体/Run | trace目录无blob地址；正文入口校验hash、size、128KiB界限，保外部/超限/损坏等原因 |
| X18 | 分页和总体口径 | 主体双键分页；关系固定ID排序offset | total/next_before_id/next_offset；overall_stats不依赖分页。跨页并发变化不保证跨请求快照一致 |
| X19 | Explain、诊断、Case结果导航 | 已有A/I analysis四GET与Case API | analysis_url/Case ID用于读取已有同轮产物；本批不在GET启动调查或合成新报告 |

## 四个完整例子

**告警概览：** 来源平台为Splunk、原厂未知、接入编号ingress-0、厂商编号vendor-0。接口返回original_vendor=null而不是Splunk。当前告警为completed/false_positive；已保存分诊为benign、置信度0.96（显示96），同次理由和Run保持配对，不能把96写成当前误报判定置信度。未知event_time仍null，明确priority_value=0仍为零。

**事件概览：** A1为critical、时间未知，A2为medium、发生于00:00。事件自身有独立名称、人工覆盖low和理由。返回severity_auto=critical、severity_effective=low；首次和末次活动都是A2时间、未知时间数1。A1同时带执行和持久化标签且执行重复一次，A2带执行，最终执行2、持久化1，成员数仍2。事件更新时间取成员业务时间01:00，不取两天后的材料接收时间。

**关系与活动：** Case C1包含A1，Case C2显式关联事件I。I的Case目录分别标注“成员关联”和“显式关联”。一条Case活动明确以A1/A2为目标，A1页面只显示A1的目标前后值；另一条同Case活动没有A1主体/目标，不进入A1活动。没有cases:read时Case目录403，但仍可读获授权告警字段。

**执行过程：** 一个A Run有两次明确的合成模型步骤，第一步上报10 tokens、第二步unknown。即使目录验证中临时只显示一条，总模型数仍2、已知tokens=10、未知调用1、total_tokens=null。工件有准确hash时可读，损坏时返回content_integrity_mismatch；用另一告警或事件ID访问该Run返回404。该例只验证账本读取，不是执行了两次真实模型，也未改变A执行预算。

## 已补齐与仍未完成

本批补的是新表到页面的读取合同：主字段、明确派生、稳定关系、已有正文和执行留痕。没有新增DDL、ORM列或公共枚举，原29表458列/迁移123保持。完整定义见[OpenAPI](../design/socai2-page-reader-v1.openapi.json)和[读取源码](../../services/api/app/socai2/page_reader.py)。

| 剩余项 | 当前能提供什么 | 后续工作 |
| --- | --- | --- |
| 事件Case关系写入/移动 | 显式链接和共享成员已分别读回 | OpenSpec 3.4接写事务/移动，不把有读能力当写入已完成 |
| H人工任务 | 新表和Case读合同已有基础 | 3.5补任务/结果写读和引用冻结 |
| 外部资产资料及其他来源 | 当前public.assets可匹配的已存字段；无匹配为空集合 | 3.6按实际来源接入，不补造设备详情、库存身份或缺失上游输入 |
| 响应审批/执行实时状态 | 稳定namespace/approval_id/action_id及已保存回执引用 | 对应响应服务读取尚未接，不能从ID推定批准人、批准时间或执行成功 |
| 正式页面交互 | 字段与总体计数可读，固定分页可用 | 搜索/筛选/自选排序/导出/级联管理由页面及业务负责人实现 |
| 生产消费者与历史数据 | 本地新接口只读新表，默认关闭 | 3.7处理生产迁移、消费者接线及真实质量；旧库/旧API未切换 |
| AI问答 | 保留原3条501接口 | 用户要求暂缓，不在本批扩展 |

## 验证

8项新检查最新通过；首7项中2过、5失败，失败分别是测试的Decimal字符串精度预期、对象缺source_path、响应引用不符合既有来源约束、错误假定另一测试租户无历史数据、步骤缺stage_code。修夹具/预期后仅复核5项通过，原件保留。随后对照原型修正待分配总体口径、补分诊有效性和明确派生类型，复核3项受影响检查并新增1项总体/基础Run统计检查，4项通过。没有降低数据库约束或增加业务预算。

原A/I读取2项PG回归、Q预留3项ASGI检查（18子场景）另列，不算本批新用例。PG为21既有独立合成库，身份替身，0真实模型/湖/厂商/生产记录调用；资产测试只向既有合成资产表写隔离fixture，没有新表或容器。固定回执见[本批验证汇总](../operations/socai2-page-reader-20261104.json)。旧r13暂停、5.3未完成，不因读字段完整而核销报告语义问题。
