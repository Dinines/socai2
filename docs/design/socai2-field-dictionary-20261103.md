# 新库表字段字典

2026-11-06当前：增量126增加Case分类、截止时间和当前证据索引指针，本机隔离库已核对29表/462列；结构化字典现37枚举/39 JSON合同。原123为29表/458列，124增加固定source_namespace，125仅增加函数。原迁移和历史记录保留；字段合同不等于生产已接入。最新[页面数据交接](../investigation/socai2-page-data-handoff-20261106.md)，此前[关系批次](../investigation/socai2-case-relations-20261104.md)及[实现交接](socai2-schema-implementation-20261103.md)按各自日期阅读。来源：[结构化字典](socai2-data-contract-20261103.json)、[JSON schema](socai2-json-contracts-20261103.schema.json)。

## 1. 全表规则

- **tenant_id**：{"type": "uuid", "nullable": false, "default": null, "meaning": "服务端租户；每表必有；引用 public.tenants(id)"}
- **identity**：{"name": "id", "type": "uuid", "nullable": false, "default": "application UUID", "meaning": "新记录UUID；外部任意文本ID另存，不能强转"}
- **key_rule**：所有实体 PRIMARY KEY(id), UNIQUE(tenant_id,id)；内部FK含tenant_id及所需父ID；关系表按所列联合PK
- **timestamps**：timestamptz，输入带时区，UTC存储；发生时间未知为NULL，不用NOW替代；created_at允许transaction_timestamp()
- **enums**：text+命名CHECK；API同一枚举字典；拒绝未知业务写入值，来源原值仍保存在材料；不使用中文标签入库
- **json**：JSON字段必须引用本文contract；NULL为未记录/不可得，[]为已读取且为空；禁止无定义的万能data/extra列
- **immutable**：材料/分诊反馈/诊断终态/结果/版本/活动追加；引用父对象不物理级联删除；应用无历史UPDATE/DELETE权限
- **users**：public.users.id为UUID，旧表无(tenant_id,id)唯一键；先FK(id)，服务端在事务内校验同租户/可授权目标，禁止以用户名代外键；不宣称普通FK校验了租户
- **writers**：列的写入权按表owner和字段说明划分；来源同步不得覆盖人工管理；GET无写回
- **deletion**：业务接口不物理删除审计原件；成员移出仅删除当前关系并追加活动；保留/脱敏策略另作显式运维，不自动级联
- **rls**：新schema开启并FORCE RLS，USING/WITH CHECK tenant_id=public.current_tenant_id()；缺租户拒绝，不复制旧NULL旁路。复用db/rls.py按事务set_config，Fusion异步入口亦须设置；实际运行角色/权限待部署预检。 无新数据写入前仍须验证运行角色；不会自动切换旧业务写入。

## 2. 枚举定义

| 名称 | 允许值 | 语义 |
| --- | --- | --- |
| severity | info、low、medium、high、critical | 来源五级，NULL未知；页面高/中/低不反向丢弃critical/info |
| alert_status | new、in_progress、completed、unknown | 业务处理；旧fp/false_positive→completed并保留误报；unknown仅无法映射历史 |
| work_status | new、in_progress、resolved、unknown | 事件和Case业务处理；Run完成不自动resolved |
| disposition | true_positive、false_positive、benign、needs_review | 告警判定；NULL尚未判断；benign=正常/授权，needs_review=需人工确认 |
| assignment_state | unassigned、assigned、unresolved | 明确未分配/已解析用户/来源负责人无法解析；unresolved保留原值 |
| score_state | not_provided、not_computed、disabled、failed、available、legacy_unverified | 仅available可作为已知有效评分；其他数值原件留材料 |
| time_source | source、derived_source、unknown | 发生时间不以接收时间补造 |
| run_kind | alert_basic、incident_diagnosis、baseline、ai_question | 五业务流程中四个真实机器执行；人工任务无Run |
| run_state | pending_update、running、unknown、completed、failed、cancelled | pending仅baseline；unknown仍占其执行槽；completed指机器已结束 |
| run_trigger | ingested、refresh、case_created、members_changed、manual、question、retry | 入口原因；来源未知不靠标题猜 |
| delivery | none、partial、complete、unknown | 产物交付完整性，独立执行状态与结论有效性 |
| step_kind | stage、model、tool、graph、render | 一次实际调用一行；父阶段不重复计成本 |
| step_state | planned、running、completed、failed、timeout、cancelled、skipped、unknown | 成功空查询=completed+returned_rows=0，失败rows=NULL |
| read_state | not_read、read、missing、denied、failed | 成员材料读取；read还需material_id |
| analysis_state | not_analyzed、analyzed、unresolved、excluded | 未分析/已分析/分析后未决/明确排除 |
| result_kind | baseline、ai_saved | 正式历史；未保存对话不进results |
| origin | model、human、system、legacy | 结论来源；系统交接不冒充模型有效结论 |
| validation | not_checked、accepted、rejected、system_only、legacy_unverified | 程序采纳校验状态，不等同事实绝对正确 |
| conclusion_state | supported、uncertain、unavailable | 有依据/未决/无结论；unavailable正文可有handoff，不写有效结论 |
| task_state | not_started、in_progress、completed、cancelled | 完成须反馈；已完成仍可编辑为新版本 |
| message_role | user、assistant | 原始模型system/tool交换存artifacts，不伪造用户对话 |
| message_state | accepted、running、completed、failed、cancelled、unknown | 消息交付状态；Run负责实际执行状态 |
| actor_type | user、service、model、legacy_unknown | ID和名称快照；历史缺人不以当前负责人填充 |
| object_type | host、user、ip、domain、url、file、hash、process、email、application、cloud_resource、technique、other | 来源对象；other须原类型，host/user同名不得合并 |
| object_role | entity、ioc、both | 对象与IOC来源类别；不自动提升威胁判定 |
| asset_match | matched、ambiguous、not_found、not_checked | 库存匹配状态；matched须来源引用和依据 |
| ref_kind | source_event、threshold_candidate、sequence_candidate、related_record | 检测参与/候选与因果不混淆 |
| membership_source | fusion、manual、incident_link、move、legacy | 关系写入来源 |
| material_state | complete、truncated、summary_only、unavailable | 原件保留状态，完整只表示保存材料完整，不代表输入覆盖全 |
| diagnosis_state | running、completed、failed、cancelled、unknown | 事件诊断尝试，终态不可变 |
| change_kind | initial、unchanged、expanded、revised、withdrawn、not_comparable | 比较基线明确，initial无比较引用 |
| approval_requirement | required、not_required、unknown | 未记录不等于无需审批 |
| activity_result | succeeded、failed、skipped | 活动目标的实际处理结果，不用计数代目标 |
| artifact_kind | input_snapshot、model_request、model_response、tool_request、tool_response、domain_analysis、deep_analysis、attack_chain、attack_path、alert_graph、report_json、report_markdown、attachment、source_snapshot、handoff、query_plan、alert_explanation、case_evidence_index | 稳定类别；126增加有版本的案件证据目录 |
| case_classification | true_positive、informational、false_positive | Case明确管理分类；NULL为未设置，不继承Incident/Alert |
| assessment_kind | triage、human_feedback | 自动与人工独立不可变历史 |
| scope_kind | whole_case、selected_alerts、explicit_objects | 结果/人工反馈范围的声明，不等于已证明覆盖 |

## 3. 每表字段

每表另有id UUID NOT NULL与tenant_id UUID NOT NULL；UUID由应用分配，tenant来自服务端。PRIMARY KEY(id)、UNIQUE(tenant_id,id)，tenant引用public.tenants。

### 3.1 socai2.alerts

写入者：Fusion写来源；管理API写管理字段/当前引用。可变性：current。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| source_namespace | text | 否 | — | 来源系统命名空间，不是原厂名称 |
| source_alert_id | text | 是 | — | 接入来源编号；允许非UUID |
| vendor_alert_id | text | 是 | — | 厂商原始告警编号；与接入编号分开 |
| connector_id | uuid | 是 | — | 已有连接器引用，同租户校验 |
| connector_type | text | 是 | — | 接入类型原值，不代替original_vendor |
| original_vendor | text | 是 | — | 明确原厂，未知NULL |
| source_identity_key | text | 否 | — | Fusion已计算稳定身份键；与namespace组成幂等键 |
| title | text | 否 | — | 接收到的标题；未知来源用显式缺失显示，不编造内容 |
| description | text | 是 | — | 来源说明；人工补充用评论 |
| category | text | 是 | — | 来源类别，不拿判定替代 |
| severity | TEXT / severity | 是 | — | 当前来源严重程度 |
| severity_raw | text | 是 | — | 未映射来源等级原文 |
| event_time | timestamptz | 是 | — | 真实发生时间 |
| event_time_source | TEXT / time_source | 否 | unknown | 发生时间依据 |
| first_seen_at | timestamptz | 是 | — | 已收到材料中首次活动时间 |
| last_seen_at | timestamptz | 是 | — | 已收到材料中末次活动时间 |
| ingested_at | timestamptz | 否 | transaction_timestamp() | 首次接收时间 |
| source_updated_at | timestamptz | 否 | transaction_timestamp() | 本地保存新材料的时间 |
| business_updated_at | timestamptz | 否 | transaction_timestamp() | 实际业务字段变更时间；GET不更新 |
| handling_status | TEXT / alert_status | 否 | new | 业务处理状态 |
| disposition | TEXT / disposition | 是 | — | 当前采用判定；与latest反馈或分诊配套 |
| owner_id | uuid | 是 | — | public.users.id |
| assignment_state | TEXT / assignment_state | 否 | unassigned | 分配状态 |
| owner_source_value | text | 是 | — | unresolved时原负责人值 |
| assigned_at | timestamptz | 是 | — | 最近分配操作时间 |
| tags | text[] | 否 | {} | 业务标签；资产标签从库存读取 |
| priority_value | numeric(5,2) | 是 | — | 已有优先级0到100，不以分诊分数填充 |
| priority_state | TEXT / score_state | 否 | not_provided | 优先级评分状态 |
| priority_source | text | 是 | — | 评分生产者/模型版本 |
| priority_basis | JSONB / priority_basis | 是 | — | 评分来源依据；无值不造理由 |
| closed_at | timestamptz | 是 | — | 当前完成周期关闭时间；重开后置空，旧值在活动中 |
| closed_by | uuid | 是 | — | 明确用户关闭人；自动关闭记录活动服务身份 |
| reopened_at | timestamptz | 是 | — | 最近明确重开时间 |
| latest_material_id | UUID → alert_materials | 是 | — | 同告警最新有效材料 |
| latest_triage_id | UUID → alert_assessments | 是 | — | 同告警kind=triage记录 |
| latest_feedback_id | UUID → alert_assessments | 是 | — | 同告警kind=human_feedback记录 |
| row_version | bigint | 否 | 1 | 管理乐观锁；每次实际写入+1 |
| latest_explanation_id | UUID → artifacts | 是 | — | 同告警kind=alert_explanation的有效Explain材料；GET不生成并写业务时钟 |

- UNIQUE(tenant_id,source_namespace,source_identity_key)
- event_time_source=unknown iff event_time IS NULL；first/last均有值时first<=last
- assigned iff owner_id非空；unresolved须owner_source_value
- priority available须数值+source；其他state数值NULL；0<=value<=100
- latest三引用包含tenant_id+alert_id校验；物理FK后置以解循环；kind由受控写入检查

### 3.2 socai2.alert_materials

写入者：Fusion材料保存。可变性：append_only。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| alert_id | UUID → alerts | 否 | — | 所属告警 |
| revision | bigint | 否 | — | 同告警材料版本，从1开始 |
| received_at | timestamptz | 否 | transaction_timestamp() | 接收时间 |
| source_version | text | 是 | — | 输入已有源版本，未知NULL |
| raw_text | text | 是 | — | 原始字符串，保留原文 |
| raw_json | JSONB / raw_payload | 是 | — | 合法JSON输入 |
| ocsf_json | JSONB / raw_payload | 是 | — | 收到的OCSF原值 |
| detection | JSONB / detection | 否 | — | 规则、ATT&CK与来源检测评分合同 |
| enrichment | JSONB / enrichment | 是 | — | 已收到富化；来源及时间 |
| source_scope | JSONB / source_scope | 否 | — | 来源引用范围、数量、截断和完整性 |
| material_state | TEXT / material_state | 否 | — | 原件留存状态 |
| sha256 | char(64) | 是 | — | 已留存字节哈希；原大小/原hash另在retention |
| retention | JSONB / retention | 否 | — | 字节数、保存形式、截断及原因 |

- UNIQUE(tenant_id,alert_id,revision)；revision>0
- 不可覆盖原材料；当前指针在同一事务更新
- raw_json是查询副本，原字节保留时才可声称逐字节一致；不强制两者都有

### 3.3 socai2.alert_source_refs

写入者：Fusion来源绑定。可变性：append_only。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| alert_id | UUID → alerts | 否 | — | 归属告警 |
| material_id | UUID → alert_materials | 否 | — | 在哪版材料中接收到 |
| source_namespace | text | 否 | — | 湖/数据源标识 |
| source_event_id | text | 否 | — | 原始事件ID，有效UUID只规范表示，不拒绝其他文本 |
| relation_kind | TEXT / ref_kind | 否 | — | 来源参与方式 |
| observed_at | timestamptz | 是 | — | 源事件时间 |
| source_path | text | 是 | — | 材料字段路径 |

- FK(tenant,alert,material)→alert_materials；UNIQUE(tenant,material,namespace,event_id,relation_kind)
- 不能为ClickHouse跨库伪造FK；引用是否查到另存Tool回执

### 3.4 socai2.alert_objects

写入者：Fusion对象提取；资产适配解析。可变性：append_only。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| alert_id | UUID → alerts | 否 | — | 来源告警 |
| material_id | UUID → alert_materials | 否 | — | 来源材料版本 |
| object_key | text | 否 | — | type+namespace+normalized值计算的稳定键 |
| object_type | TEXT / object_type | 否 | — | 有类型的对象 |
| source_type | text | 是 | — | 来源原类型；other必有 |
| object_role | TEXT / object_role | 否 | — | 实体或IOC |
| namespace | text | 否 | — | 主机域/账号域/算法等身份边界 |
| raw_value | text | 否 | — | 原对象值 |
| normalized_value | text | 否 | — | 按明确类型规则规范；不跨类型合并 |
| source_path | text | 否 | — | 来源材料字段路径 |
| attributes | JSONB / object_attributes | 否 | — | 进程/端点/哈希等类型化已收属性 |
| asset_match_state | TEXT / asset_match | 否 | not_checked | 当时库存匹配状态 |
| asset_ref | JSONB / external_ref | 是 | — | 已有库存的类型化引用 |
| match_basis | JSONB / match_basis | 是 | — | 匹配依据及时间快照 |

- UNIQUE(tenant,material,object_key,source_path)；同object_key可有多个来源路径
- matched须asset_ref及match_basis；不能把来源对象当已匹配库存
- 当前对象读取latest_material_id；历史Run使用冻结材料版，不能join当前对象代替

### 3.5 socai2.alert_assessments

写入者：分诊执行器/人工反馈API。可变性：append_only。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| alert_id | UUID → alerts | 否 | — | 所属告警 |
| kind | TEXT / assessment_kind | 否 | — | 分诊或人工反馈 |
| input_material_id | UUID → alert_materials | 是 | — | 判断依据的材料版；旧未知NULL |
| source_run_id | UUID → runs | 是 | — | 新alert_basic执行；与此告警一致 |
| legacy_execution_ref | JSONB / external_ref | 是 | — | 旧执行稳定引用，不能冒充新Run |
| verdict | TEXT / disposition | 是 | — | 同次判定 |
| rationale | text | 是 | — | 同次理由，历史缺失NULL |
| confidence | numeric(6,5) | 是 | — | 分诊置信度0..1，页面可乘100显示；人工无评分 |
| score_state | TEXT / score_state | 否 | not_provided | 计算状态 |
| recommendations | JSONB / recommendations | 是 | — | 同次建议，不与新人工判断拼接 |
| producer | text | 否 | — | 生产者及版本 |
| actor | JSONB / actor | 否 | — | 实际操作者/服务身份 |
| assessed_at | timestamptz | 否 | — | 判断发生时间 |
| operation_key | text | 否 | — | 本判断幂等键 |

- UNIQUE(tenant,operation_key)
- kind=human_feedback→confidence NULL；available→confidence非空且0<=confidence<=1
- input_material/source_run必须同告警；分诊失败不追加假判定，用Run失败事实展示

### 3.6 socai2.incidents

写入者：Fusion创建与关系维护；管理API；诊断写成功引用。可变性：current。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| source_namespace | text | 否 | — | Fusion实例/来源命名空间 |
| source_incident_id | text | 否 | — | 来源事件ID，兼容原有文本键 |
| title | text | 否 | — | 事件自身标题 |
| description | text | 是 | — | 事件自身说明，非第一条成员标题 |
| handling_status | TEXT / work_status | 否 | new | 事件业务处理状态 |
| owner_id | uuid | 是 | — | 当前明确负责人 |
| assignment_state | TEXT / assignment_state | 否 | unassigned | 未分配/已分配/原值未解析 |
| owner_source_value | text | 是 | — | 未解析来源负责人 |
| assigned_at | timestamptz | 是 | — | 最近改派时间 |
| tags | text[] | 否 | {} | 事件业务标签，成员资产标签另外派生 |
| severity_override | TEXT / severity | 是 | — | 人工事件覆盖等级；NULL=采用成员最高；不改成员 |
| severity_override_reason | text | 是 | — | 人工覆盖依据 |
| severity_override_at | timestamptz | 是 | — | 覆盖设置时间 |
| severity_override_by | uuid | 是 | — | 覆盖人 |
| priority_value | numeric(5,2) | 是 | — | 已有优先级0..100 |
| priority_state | TEXT / score_state | 否 | not_provided | 无来源不合成 |
| priority_source | text | 是 | — | 已有评分生产者 |
| priority_basis | JSONB / priority_basis | 是 | — | 评分依据 |
| resolution_note | text | 是 | — | 事件解决说明，人工解决必填 |
| resolved_at | timestamptz | 是 | — | 当前解决周期时间 |
| resolved_by | uuid | 是 | — | 解决人 |
| reopened_at | timestamptz | 是 | — | 最近明确重开时间 |
| created_at | timestamptz | 否 | transaction_timestamp() | 事件首次持久化时间 |
| business_updated_at | timestamptz | 否 | transaction_timestamp() | 自身管理或成员关联变动；移除最后成员仍更新 |
| latest_diagnosis_id | UUID → incident_diagnoses | 是 | — | 同事件最新成功诊断；失败尝试不能覆盖 |
| row_version | bigint | 否 | 1 | 管理/范围写入乐观版本 |

- UNIQUE(tenant,source_namespace,source_incident_id)
- D01已确认：override值+理由+人+时间一起设置；清除时四列一起清空，显示回成员最高
- 派生严重程度不保存冗余列；resolution字段不由Run结束写入
- 当前诊断指针FK含incident_id；最新尝试用run/diagnoses时间查，不混配

### 3.7 socai2.incident_alerts

写入者：Fusion归并/明确成员维护。可变性：current_relation。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| incident_id | UUID → incidents | 否 | — | 事件 |
| alert_id | UUID → alerts | 否 | — | 当前成员 |
| linked_at | timestamptz | 否 | transaction_timestamp() | 加入时间 |
| membership_source | TEXT / membership_source | 否 | — | 成员产生方式 |
| correlation_basis | JSONB / correlation_basis | 否 | — | 实际规则、对象类型、值、窗口及候选关系 |
| basis_version | text | 否 | — | 归并算法/合同版本 |
| source_operation_id | uuid | 否 | — | 和活动同操作ID |

- UNIQUE(tenant,alert_id)；当前单告警一个Fusion事件
- 旧事件移除+新事件加入+两个事件业务时间+活动在同事务；不覆写旧依据活动

### 3.8 socai2.incident_diagnoses

写入者：事件诊断执行器。可变性：terminal_append_only。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| incident_id | UUID → incidents | 否 | — | 事件 |
| source_run_id | UUID → runs | 否 | — | incident_diagnosis执行，同事件 |
| revision | bigint | 否 | — | 同事件尝试版本 |
| state | TEXT / diagnosis_state | 否 | — | 生成尝试状态 |
| summary | text | 是 | — | 有效概况正文，失败不伪造 |
| diagnosis | JSONB / diagnosis | 是 | — | 诊断、证据和限制 |
| open_questions | JSONB / questions | 是 | — | 待核问题 |
| input_artifact_id | UUID → artifacts | 否 | — | 冻结成员/分诊/来源材料快照 |
| source_fingerprint | char(64) | 否 | — | 实际输入指纹 |
| producer | text | 否 | — | 实现和版本 |
| requested_at | timestamptz | 否 | — | 尝试时间 |
| generated_at | timestamptz | 是 | — | 成功时间 |
| error | JSONB / error | 是 | — | 失败原因；无报错NULL |

- UNIQUE(tenant,incident,revision)；UNIQUE(tenant,source_run)
- 费用只从run_steps聚合，不复制旧summary费用
- 终态后不改正文；失败仍保留上一次成功指针

### 3.9 socai2.cases

写入者：案件管理服务。可变性：current。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| title | text | 否 | — | 名称 |
| source_namespace | text | 是 | — | 124新增；固定数据身份命名空间，绑定后不可改；旧范围未确认为NULL，不是原始来源环境 |
| source_namespace | text | 是 | — | 124新增；固定数据身份命名空间，绑定后不可改；旧范围未确认为NULL，不是原始来源环境 |
| description | text | 是 | — | 案情说明 |
| handling_status | TEXT / work_status | 否 | new | 业务状态 |
| severity | TEXT / severity | 是 | — | 当前明确案件等级 |
| severity_source | text | 是 | — | 手动设置或明确汇总规则，不从置信度猜 |
| owner_id | uuid | 是 | — | 当前负责人 |
| assignment_state | TEXT / assignment_state | 否 | unassigned | 分配状态 |
| owner_source_value | text | 是 | — | 历史未解析负责人 |
| assigned_at | timestamptz | 是 | — | 最近分配时间 |
| tags | text[] | 否 | {} | 案件标签 |
| priority_value | numeric(5,2) | 是 | — | 已有优先级 |
| priority_state | TEXT / score_state | 否 | not_provided | 评分状态 |
| priority_source | text | 是 | — | 评分生产者 |
| priority_basis | JSONB / priority_basis | 是 | — | 已有依据 |
| scope_revision | bigint | 否 | 0 | 仅当前告警成员真实变动+1 |
| current_assessment_id | UUID → case_assessments | 是 | — | 已明确采用版本；不等于最新Run |
| classification | TEXT / case_classification | 是 | — | 126新增；明确管理分类，允许清空，来源及操作人留活动 |
| due_at | timestamptz | 是 | — | 126新增；Case期限，独立于任务期限及模型预算；输入必须有时区 |
| current_evidence_artifact_id | UUID → artifacts | 是 | — | 126新增；同租户同Case的case_evidence_index/socai2.case-evidence.v1指针 |
| created_at | timestamptz | 否 | transaction_timestamp() | 创建时间 |
| created_by | uuid | 是 | — | 创建人，服务创建见活动 |
| business_updated_at | timestamptz | 否 | transaction_timestamp() | 案件业务变化 |
| resolved_at | timestamptz | 是 | — | 当前解决周期时间 |
| resolved_by | uuid | 是 | — | 明确解决人 |
| resolution_note | text | 是 | — | 解决说明，不擅自添加必填要求 |
| reopened_at | timestamptz | 是 | — | 最近重开 |
| row_version | bigint | 否 | 1 | 乐观版本 |
| legacy_ref | JSONB / external_ref | 是 | — | 导入时原Case命名空间/文本ID |

- current_assessment须同Case同租户；后置FK打破建表循环
- current_evidence_artifact_id由联合FK和延迟类型检查约束；正文SHA、来源角色/成员及版本由受控写入/读取校验，不能只写任意JSON冒充完整索引
- scope_revision不由GET、任务编辑、调查进度增加
- D02已确认有效baseline自动采用、AI明确采用；D04未定入口保持关闭

### 3.10 socai2.case_alerts

写入者：成员管理事务。可变性：current_relation。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| case_id | UUID → cases | 否 | — | 当前Case |
| alert_id | UUID → alerts | 否 | — | 当前正式成员 |
| added_at | timestamptz | 否 | transaction_timestamp() | 加入时间 |
| added_by | uuid | 是 | — | 明确操作人 |
| membership_source | TEXT / membership_source | 否 | — | 加入来源 |
| source_operation_id | uuid | 否 | — | 批量实际操作 |

- UNIQUE(tenant,case,alert)；同告警可在多Case
- 不保留第二份cases.alert_ids数组作为真值
- 移动两案按ID锁Case；整体校验/修改/两个pending/活动同事务

### 3.11 socai2.case_incidents

写入者：事件关联事务。可变性：current_relation。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| case_id | UUID → cases | 否 | — | Case |
| incident_id | UUID → incidents | 否 | — | 显式关联事件 |
| linked_at | timestamptz | 否 | transaction_timestamp() | 关联时间 |
| linked_by | uuid | 是 | — | 操作者 |
| source_operation_id | uuid | 否 | — | 操作ID |

- UNIQUE(tenant,case,incident)
- 关联时并入当时成员；之后事件新增成员不自动加Case；解除事件关系不擅自删case_alerts

### 3.12 socai2.case_assessments

写入者：明确采用/案件判断服务。可变性：append_only。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| case_id | UUID → cases | 否 | — | 案件 |
| revision | bigint | 否 | — | 案件判断版本 |
| conclusion | text | 否 | — | 明确采用的判断 |
| origin | TEXT / origin | 否 | — | model/human/legacy，system交接不得采用为有效结论 |
| validity | TEXT / validation | 否 | — | 采用时有效性；不代表绝对事实证明 |
| scope_revision | bigint | 否 | — | 采用时Case范围版本 |
| formed_at | timestamptz | 否 | — | 判断形成时间 |
| adopted_at | timestamptz | 否 | — | 采用时间 |
| adopted_by | uuid | 是 | — | 人工采用时用户；基础结果自动采用NULL，actor明确service |
| actor | JSONB / actor | 否 | — | 真实采用主体；baseline自动采用记录service |
| reason | text | 是 | — | 采用/修改理由 |
| operation_key | text | 否 | — | 同一次采用幂等键 |

- UNIQUE(tenant,case,revision)；UNIQUE(tenant,operation_key)
- 正文+sources+members+Case指针+活动一次事务发布；后续新增成员不扩覆盖
- 拒绝把unavailable/system_only当有效判断；采用策略见auto_adoption_policy

### 3.13 socai2.case_assessment_sources

写入者：判断采用事务。可变性：append_only。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| case_id | UUID → cases | 否 | — | 用于父案复合FK |
| assessment_id | UUID → case_assessments | 否 | — | 采用判断 |
| result_id | UUID → results | 是 | — | 具体正式结果版本 |
| task_revision_id | UUID → task_revisions | 是 | — | 具体人工事实版本 |
| artifact_id | UUID → artifacts | 是 | — | 同案其他具体材料 |
| source_note | text | 是 | — | 此来源被采用的部分 |

- result_id/task_revision_id/artifact_id恰一非空；各自tenant+case FK
- 每类来源部分唯一，防同一assessment重复引用；不以最新task或最新report指针替代

### 3.14 socai2.case_assessment_members

写入者：判断采用事务。可变性：append_only。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| case_id | UUID → cases | 否 | — | 同案约束 |
| assessment_id | UUID → case_assessments | 否 | — | 采用判断 |
| alert_id | UUID → alerts | 否 | — | 判断明确覆盖的告警 |
| coverage_note | text | 是 | — | 范围限制；覆盖不是全告警都恶意 |

- UNIQUE(tenant,assessment,alert)；FK(tenant,case,assessment)
- 采用时成员属于当前Case且来源有适用依据；后续移出不删除该历史关系

### 3.15 socai2.runs

写入者：对应阶段执行服务；baseline由手动启动API领取。可变性：lifecycle_frozen_input。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| kind | TEXT / run_kind | 否 | — | 四机器流程明确区分 |
| alert_id | UUID → alerts | 是 | — | alert_basic归属 |
| incident_id | UUID → incidents | 是 | — | incident_diagnosis归属 |
| case_id | UUID → cases | 是 | — | baseline/ai_question归属 |
| title | text | 否 | — | 本次执行名称，pending随范围更新 |
| purpose | text | 否 | — | 本轮目标/提问 |
| trigger | TEXT / run_trigger | 否 | — | 触发原因 |
| scope_revision | bigint | 是 | — | Case成员版本；非Case NULL |
| scope_updated_at | timestamptz | 是 | — | pending最近合并范围时间 |
| scope_kind | TEXT / scope_kind | 是 | — | baseline whole_case，AI可选范围；其他流程NULL |
| window_start | timestamptz | 是 | — | 固定绝对查询起点；不适用NULL |
| window_end | timestamptz | 是 | — | 固定绝对查询终点；成对出现 |
| state | TEXT / run_state | 否 | — | 记录/执行状态 |
| operation_key | text | 是 | — | 实际执行请求幂等键，pending尚未领取可NULL |
| request_hash | char(64) | 是 | — | 规范请求指纹，与幂等键配对 |
| retry_of_run_id | UUID → runs | 是 | — | 显式重试指向旧已结束Run，不重写旧Run |
| comparison_result_id | UUID → results | 是 | — | 领取时固定的同案比较基线，可跨成员范围 |
| input_artifact_id | UUID → artifacts | 是 | — | 领取前NULL；提交running前冻结本地输入 |
| executor_version | text | 是 | — | 实际执行版本，pending NULL |
| requested_at | timestamptz | 否 | transaction_timestamp() | 记录创建/首次请求 |
| requested_by | uuid | 是 | — | 真实请求人 |
| started_at | timestamptz | 是 | — | running领取事务时间 |
| ended_at | timestamptz | 是 | — | 终态时间；unknown未确认结束NULL |
| stop_reason | text | 是 | — | 稳定原因码；不强用人类结论代替 |
| stop_detail | text | 是 | — | 可读原因 |
| delivery_state | TEXT / delivery | 否 | none | 实际产物交付 |
| limits | JSONB / limits | 是 | — | 启动时预算和查询限额快照 |
| row_version | bigint | 否 | 1 | 执行状态条件更新版本 |

- alert/incident/case恰一；kind限定对应父对象；scope_revision及scope_kind仅Case必填
- UNIQUE(tenant,kind,operation_key) WHERE operation_key IS NOT NULL；同键不同hash冲突
- UNIQUE(tenant,case) WHERE kind=baseline AND state=pending_update
- 活跃基础唯一：tenant+case WHERE kind=baseline AND state IN(running,unknown)；AI执行无共用槽唯一索引
- running/unknown须started_at+input_artifact+executor_version+operation_key；终态ended_at非空；pending无started/ended/input
- 提交running后身份/范围/输入/版本/预算不可变；状态只按合法迁移；部分索引不能代替冻结保护
- usage不存第二份累计真值，直接从model/tool叶子steps聚合，缺失保持unknown

### 3.16 socai2.run_members

写入者：范围事务/领取事务；执行器仅写读取分析状态。可变性：frozen_identity_mutable_progress。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| run_id | UUID → runs | 否 | — | Case执行；非Case成员快照存输入工件 |
| case_id | UUID → cases | 否 | — | 同案FK |
| alert_id | UUID → alerts | 否 | — | 本轮约定成员 |
| material_id | UUID → alert_materials | 是 | — | 领取选择的材料版；确实缺失NULL并标read状态 |
| triage_id | UUID → alert_assessments | 是 | — | 同告警同次分诊 |
| feedback_id | UUID → alert_assessments | 是 | — | 同告警当时人工反馈 |
| read_state | TEXT / read_state | 否 | not_read | 实际读到材料 |
| analysis_state | TEXT / analysis_state | 否 | not_analyzed | 实际分析状态 |
| omission_reason | text | 是 | — | 缺失/失败/排除的具体原因 |

- UNIQUE(tenant,run,alert)；Run同Case；材料及两个assessment FK包含alert_id
- pending可整体更新；running后禁止插删及改身份/引用，允许进度状态条件更新
- baseline成员集合必须等于领取版本Case全成员；不能材料缺失就删成员

### 3.17 socai2.run_steps

写入者：执行器记录真实阶段/调用。可变性：terminal_append_only。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| run_id | UUID → runs | 否 | — | 实际执行 |
| seq | bigint | 否 | — | 同Run显示顺序 |
| parent_step_id | UUID → run_steps | 是 | — | 同Run父阶段；不是跨Run复用 |
| retry_of_step_id | UUID → run_steps | 是 | — | 同Run失败调用的重试 |
| kind | TEXT / step_kind | 否 | — | stage/model/tool/graph/render |
| stage_code | text | 否 | — | A1/I1/C1..C6/Q1等版本化阶段码 |
| question_id | text | 是 | — | 输入计划中稳定问题ID |
| state | TEXT / step_state | 否 | — | 实际状态 |
| name | text | 否 | — | 阶段、模型或工具实际名称 |
| provider | text | 是 | — | 模型/工具提供者 |
| implementation_version | text | 是 | — | 工具合同/模型版本 |
| started_at | timestamptz | 是 | — | 真实开始 |
| ended_at | timestamptz | 是 | — | 真实完成 |
| input_artifact_id | UUID → artifacts | 是 | — | 实际输入/参数原件 |
| output_artifact_id | UUID → artifacts | 是 | — | 实际输出原件 |
| reused_artifact_id | UUID → artifacts | 是 | — | 明确复用旧材料，不记为新外部调用 |
| actual_args | JSONB / tool_args | 是 | — | 类型化查询范围/时间/上限及具体参数 |
| returned_rows | bigint | 是 | — | 成功查询实际返回行数；未知/失败不填0 |
| usage | JSONB / usage | 是 | — | 模型真实tokens/费用与已知状态；非调用父阶段NULL |
| error | JSONB / error | 是 | — | 实际错误 |

- UNIQUE(tenant,run,seq)；parent/retry同Run，禁止自指，写入校验无环
- 终态不可改；重试另行；输出/artifact须同Run；复用允许同案旧Run但来源不改
- returned_rows>=0；failed/timeout/unknown不得以0伪装空查询
- stage_code不是可猜枚举，阶段注册表按executor_version固定；历史新增执行器不改旧值

### 3.18 socai2.artifacts

写入者：输入冻结器/各执行器/附件保存。可变性：append_only。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| alert_id | UUID → alerts | 是 | — | 非Case告警材料归属 |
| incident_id | UUID → incidents | 是 | — | 非Case事件材料归属 |
| case_id | UUID → cases | 是 | — | Case材料归属 |
| run_id | UUID → runs | 是 | — | 存在时必须与其父对象一致 |
| step_id | UUID → run_steps | 是 | — | 实际产生步骤，须属于run_id |
| kind | TEXT / artifact_kind | 否 | — | 材料类别 |
| schema_version | text | 否 | — | 结构合同版本 |
| content_json | JSONB / artifact_payload | 是 | — | 结构化保存内容 |
| content_text | text | 是 | — | 原始文本/Markdown |
| blob_ref | text | 是 | — | 受控内部对象存储键，不是任意远端URL |
| mime_type | text | 否 | — | 实际内容类型 |
| file_name | text | 是 | — | 附件显示名，不作路径 |
| sha256 | char(64) | 是 | — | 已留存规范字节哈希 |
| size_bytes | bigint | 是 | — | 已留存字节数 |
| captured_at | timestamptz | 否 | — | 记录取得时间 |
| event_time | timestamptz | 是 | — | 材料中的发生时间，未知NULL |
| material_state | TEXT / material_state | 否 | — | 完整/截断/摘要/不可用 |
| source_refs | JSONB / evidence_refs | 否 | — | 来源和原材料引用；可为空数组但明确是无来源记录 |
| retention | JSONB / retention | 否 | — | 原件大小/原hash/保存大小/截断范围 |
| created_by | uuid | 是 | — | 人工上传人；自动来源由Run/Step明确 |

- alert/incident/case恰一；run为空允许普通附件；step非空要求run非空
- 三种content存储恰一；unavailable允许全空但retention.reason必填
- 同Run产物跨层父对象用复合FK或约束trigger检查；JSON引用需应用解析验证，不声称FK已校验
- 旧证据复用只引用原artifact，不改归属；哈希不是事实真实性证明
- source_snapshot允许raw_payload；schema按kind选择，不把anyOf形式通过当业务语义通过；原模型输出可以是无效JSON，保content_text

### 3.19 socai2.results

写入者：Case结果发布服务/AI明确保存API。可变性：append_only。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| case_id | UUID → cases | 否 | — | 案件 |
| kind | TEXT / result_kind | 否 | — | baseline/ai_saved |
| source_run_id | UUID → runs | 否 | — | 实际来源执行，同Case |
| source_answer_id | UUID → messages | 是 | — | AI保存必有，baseline NULL |
| title | text | 否 | — | 正式记录标题；AI保存可自定义 |
| purpose | text | 否 | — | 本轮目标 |
| conclusion | text | 是 | — | 有效/不确定结论；无结论NULL |
| conclusion_state | TEXT / conclusion_state | 否 | — | 有依据/未决/无法给出 |
| conclusion_origin | TEXT / origin | 否 | — | 模型/人工/系统来源 |
| validation_state | TEXT / validation | 否 | — | 程序采用或拒绝状态 |
| closing_note | text | 否 | — | 每轮收尾说明，系统失败交接也有 |
| findings | JSONB / findings | 否 | — | 稳定条目ID、依据、反证和限制 |
| questions | JSONB / questions | 否 | — | 本轮问题/答案/缺口 |
| recommendations | JSONB / recommendations | 否 | — | 建议含稳定proposal_id、目标、理由及审批要求 |
| comparison_result_id | UUID → results | 是 | — | 明确同案已有结果；首次NULL |
| change_kind | TEXT / change_kind | 否 | — | 比较类型 |
| change_summary | text | 是 | — | 相比基线输入/证据/判断变化 |
| case_impact | JSONB / case_impact | 否 | — | 作用范围、可调整认识、不能推广处 |
| input_artifact_id | UUID → artifacts | 否 | — | 实际当时输入 |
| graph_artifact_id | UUID → artifacts | 是 | — | 本轮图，无图NULL；不借另一轮冒充 |
| report_artifact_id | UUID → artifacts | 是 | — | 同版报告，无报告NULL |
| supersedes_result_id | UUID → results | 是 | — | 明确修订另建版本，不能自指或跨案 |
| delivery_state | TEXT / delivery | 否 | — | 正式交付完整性 |
| created_at | timestamptz | 否 | — | 执行产物形成时间 |
| saved_at | timestamptz | 否 | transaction_timestamp() | 正式保存时间；AI保存与答复时间不同 |
| saved_by | uuid | 是 | — | 明确AI保存人；baseline由服务保存 |
| operation_key | text | 否 | — | 正式保存请求幂等键 |
| edited_fields | text[] | 否 | {} | 保存AI答案时用户改过的字段名；正文修改须origin=human且重新校验；原消息不改 |
| edit_note | text | 是 | — | 可选修改说明，不强制增加页面输入 |

- baseline→source run kind=baseline且终态；ai_saved→assistant completed消息及ai_question Run
- UNIQUE(tenant,source_run) WHERE kind=baseline AND supersedes_result_id IS NULL；修订只能显式关联链
- UNIQUE(tenant,source_answer) WHERE kind=ai_saved AND supersedes_result_id IS NULL；同答复重复保存返回原结果
- unavailable须conclusion NULL；system_only不能显示模型有效结论
- 结果/成员覆盖/工件同事务发布；运行中无最终结果；json数组内稳定ID唯一且引用同案合法来源
- supersedes_result_id非空时UNIQUE(tenant,supersedes_result_id)防分叉；修订需同Case/source_run/source_answer且不改原记录；报告重新渲染产生新工件
- AI正文被修改不能沿用原答复的accepted校验状态；仅改标题不改变结论来源

### 3.20 socai2.result_members

写入者：结果发布事务。可变性：append_only。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| case_id | UUID → cases | 否 | — | 父案校验 |
| result_id | UUID → results | 否 | — | 正式结果 |
| run_id | UUID → runs | 否 | — | 与result.source_run一致 |
| alert_id | UUID → alerts | 否 | — | 来自本轮run_members |
| assessment_state | TEXT / analysis_state | 否 | — | 实际逐成员分析状态 |
| conclusion_covered | boolean | 否 | false | 结论明确适用，不代表恶意 |
| assessment | text | 是 | — | 本成员发现或未决说明 |
| limitations | text | 是 | — | 限制 |
| evidence_refs | JSONB / evidence_refs | 否 | — | 明确材料及行/字段定位 |

- UNIQUE(tenant,result,alert)；FK(result,run,case)和(run,case,alert)组合
- conclusion_covered=true要求实际分析及可核依据；AI局部答复不得覆盖整案

### 3.21 socai2.tasks

写入者：人工事项API。可变性：current_pointer。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| case_id | UUID → cases | 否 | — | 所属Case |
| current_revision_id | UUID → task_revisions | 否 | — | 当前完整版本；延迟FK同事务插入 |
| origin_result_id | UUID → results | 是 | — | 同Case引出事项的结果 |
| origin_finding_id | text | 是 | — | 该结果findings中的稳定条目ID |
| created_at | timestamptz | 否 | transaction_timestamp() | 任务创建 |
| created_by | uuid | 是 | — | 创建者 |
| updated_at | timestamptz | 否 | transaction_timestamp() | 最新实际编辑 |
| row_version | bigint | 否 | 1 | 防旧表单覆盖 |

- 不在tasks复制title/state/result等第二份当前值；join current_revision即可
- current_revision属于本task同案；循环FK DEFERRABLE INITIALLY DEFERRED
- origin_finding要求origin_result并验证条目存在
- task与revision UUID在同事务预生成；延迟当前指针FK不等于忽略完整性

### 3.22 socai2.task_revisions

写入者：每次人工事项保存事务。可变性：append_only。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| case_id | UUID → cases | 否 | — | 同案FK |
| task_id | UUID → tasks | 否 | — | 事项 |
| revision | bigint | 否 | — | 从1开始，每次有效编辑+1 |
| title | text | 否 | — | 任务事项，非空 |
| description | text | 是 | — | 工作说明 |
| assignee_id | uuid | 是 | — | 同租户可选负责人，NULL未分配 |
| due_at | timestamptz | 是 | — | 截止时间，可空 |
| state | TEXT / task_state | 否 | — | 四种人工状态 |
| result_text | text | 是 | — | 事实反馈，completed必填非空 |
| result_scope | JSONB / scope | 是 | — | 确认范围；完成时须明确，如未知部分写limitations |
| source_refs | JSONB / evidence_refs | 否 | [] | 可选资料，不强制上传 |
| completed_at | timestamptz | 是 | — | 本次进入完成状态的真实时间 |
| completed_by | uuid | 是 | — | 本次实际完成人，不是assignee |
| changed_at | timestamptz | 否 | transaction_timestamp() | 版本编辑时间 |
| changed_by | uuid | 否 | — | 实际编辑人 |

- UNIQUE(tenant,task,revision)；completed必须有result_text/result_scope/completed_at/completed_by
- 完成后只修正文时保留原完成时间/人，changed记录编辑；重开后清当前完成字段，旧版本不改
- 状态不为completed不自动清除已有反馈正文；取消不算完成
- 保存版本→更新指针+乐观版本→活动同事务

### 3.23 socai2.conversations

写入者：Case问答服务。可变性：current。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| case_id | UUID → cases | 否 | — | 明确案件上下文 |
| title | text | 是 | — | 会话标题 |
| created_by | uuid | 否 | — | 发起用户 |
| created_at | timestamptz | 否 | transaction_timestamp() | 创建 |
| updated_at | timestamptz | 否 | transaction_timestamp() | 有真实消息或标题变化时更新 |
| row_version | bigint | 否 | 1 | 标题编辑版本 |

- 会话不能换Case；租户由服务端取得

### 3.24 socai2.messages

写入者：Case问答发送/执行回写服务。可变性：terminal_append_only。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| case_id | UUID → cases | 否 | — | 显式同案约束 |
| conversation_id | UUID → conversations | 否 | — | 会话 |
| sequence | bigint | 否 | — | 同会话顺序 |
| role | TEXT / message_role | 否 | — | user或assistant |
| content | text | 是 | — | 真实问题/答复；失败且无答复NULL |
| state | TEXT / message_state | 否 | — | 收取/答复状态 |
| in_reply_to | UUID → messages | 是 | — | assistant指具体用户问题；同会话 |
| source_run_id | UUID → runs | 是 | — | 真实ai_question执行；用户消息NULL |
| input_artifact_id | UUID → artifacts | 是 | — | assistant实际输入；不能保存时重新读取 |
| source_refs | JSONB / evidence_refs | 是 | — | 实际引用；无结果NULL |
| client_request_key | text | 否 | — | 发送/答复去重键，客户端重发不重复执行 |
| created_at | timestamptz | 否 | transaction_timestamp() | 发送/占位时间 |
| answered_at | timestamptz | 是 | — | 实际回答完成 |
| error | JSONB / error | 是 | — | 调用失败状态 |

- UNIQUE(tenant,conversation,sequence)；UNIQUE(tenant,conversation,client_request_key)
- user必须content非空；completed assistant必须content+source_run+input_artifact+answered_at
- 重试追加新assistant/Run关联同一用户问题，旧消息不改为成功；重复保存同答复不新调用
- 保存AI读取本消息冻结输入，不因当前Case成员后来变化改历史来源；原范围以source_run为准，权限另校验

### 3.25 socai2.graph_explorations

写入者：用户探索保存API。可变性：current。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| case_id | UUID → cases | 否 | — | 所属案 |
| base_result_id | UUID → results | 是 | — | 明确起始调查结果 |
| base_graph_artifact_id | UUID → artifacts | 是 | — | 该结果图；无图不借其他Run |
| base_input_artifact_id | UUID → artifacts | 否 | — | 起点成员/证据快照，包含无基础结果时的起点 |
| graph_state | JSONB / graph | 否 | — | 节点、边、展开/选择/布局和来源 |
| created_at | timestamptz | 否 | transaction_timestamp() | 首次保存 |
| created_by | uuid | 否 | — | 创建人 |
| updated_at | timestamptz | 否 | transaction_timestamp() | 实际保存 |
| updated_by | uuid | 否 | — | 最近保存人 |
| row_version | bigint | 否 | 1 | 画布并发编辑 |

- base_result/base_graph须同案且确实对应；重置才改基底，保存不改Case成员
- graph_state不是调查产物，不能替换results.graph_artifact_id

### 3.26 socai2.activities

写入者：实际业务事务。可变性：append_only。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| operation_id | uuid | 否 | — | 一次批量操作分组，所有目标同ID |
| actor | JSONB / actor | 否 | — | 真实人/服务身份和名称快照 |
| action | text | 否 | — | 受版本控制业务动作码，见action_registry合同 |
| subject_alert_id | UUID → alerts | 是 | — | 主对象告警 |
| subject_incident_id | UUID → incidents | 是 | — | 主对象事件 |
| subject_case_id | UUID → cases | 是 | — | 主对象Case |
| occurred_at | timestamptz | 否 | transaction_timestamp() | 实际操作时间 |
| summary | text | 否 | — | 可读操作摘要，不能替代结构目标 |
| detail | JSONB / activity_detail | 否 | — | 请求原因和未完成原因，不复制完整原件 |

- 三个subject恰一非空；各FK含tenant；不再用无约束subject_type+id
- UNIQUE(tenant,operation_id,id)仅查询分组，不强限一次operation只有一活动
- 活动随事实事务提交；失败事务不能留成功活动，失败请求单独audit而非业务成功

### 3.27 socai2.activity_targets

写入者：批量实际写入事务。可变性：append_only。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| activity_id | UUID → activities | 否 | — | 所属实际活动 |
| alert_id | UUID → alerts | 是 | — | 被处理告警 |
| incident_id | UUID → incidents | 是 | — | 被处理事件 |
| case_id | UUID → cases | 是 | — | 被处理Case |
| task_id | UUID → tasks | 是 | — | 被处理任务 |
| run_id | UUID → runs | 是 | — | 被操作执行 |
| result_id | UUID → results | 是 | — | 被采用/保存结果 |
| comment_id | UUID → comments | 是 | — | 评论 |
| before_value | JSONB / activity_value | 是 | — | 相关变更字段前值；新建NULL |
| after_value | JSONB / activity_value | 是 | — | 相关变更字段后值；移除NULL |
| result_state | TEXT / activity_result | 否 | — | 实际成功/跳过/失败 |
| reason | text | 是 | — | 跳过/失败原因 |

- 七个目标引用恰一非空；按各列部分UNIQUE(tenant,activity,target)；全部FK含tenant
- 每个实际目标一行，无200条截断；显示数量由行数计算
- before/after只保存改变字段与版本，不泄漏凭据/整份日志

### 3.28 socai2.comments

写入者：对象普通评论API。可变性：current_with_activity_history。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| alert_id | UUID → alerts | 是 | — | 所属告警 |
| incident_id | UUID → incidents | 是 | — | 所属事件 |
| case_id | UUID → cases | 是 | — | 所属Case |
| body | text | 否 | — | 普通评论非空 |
| author_id | uuid | 否 | — | 实际作者 |
| author_name_snapshot | text | 否 | — | 当时显示名 |
| created_at | timestamptz | 否 | transaction_timestamp() | 创建 |
| edited_at | timestamptz | 是 | — | 实际编辑时间 |
| edited_by | uuid | 是 | — | 实际编辑人 |
| row_version | bigint | 否 | 1 | 并发编辑 |

- 三父恰一非空；FK含tenant；编辑前后内容记活动
- 管理备注选填意味着不创建评论行，不创建空body

### 3.29 socai2.response_links

写入者：建议到既有审批执行的关联服务。可变性：append_only。

| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |
| --- | --- | --- | --- | --- |
| alert_id | UUID → alerts | 是 | — | 告警所属来源 |
| incident_id | UUID → incidents | 是 | — | 事件所属来源 |
| case_id | UUID → cases | 是 | — | Case所属来源 |
| result_id | UUID → results | 是 | — | 正式结果建议 |
| proposal_id | text | 是 | — | recommendations中稳定ID；需result_id |
| legacy_proposal_ref | JSONB / external_ref | 是 | — | 没有新result时已有建议/执行来源 |
| external_namespace | text | 否 | — | 已有审批执行服务命名空间 |
| approval_id | text | 是 | — | 真实审批ID，不强转UUID |
| action_id | text | 是 | — | 真实动作ID，批准不等于执行 |
| linked_at | timestamptz | 否 | transaction_timestamp() | 关系建立 |
| receipt_artifact_id | UUID → artifacts | 是 | — | 已有实际回执快照，同归属 |

- alert/incident/case恰一；result+proposal或legacy_proposal恰一来源；approval/action至少一个
- 结果建议须同案且proposal存在；旧actions.incident_id不直接充当Fusion事件
- 同来源/同namespace/同approval/action去重，NULL分支分别部分唯一；重试动作另行
- 审批状态/执行状态由已有服务读取或明确时间回执，连接表不发明执行状态

## 4. JSON内部字段和类型

对象默认拒绝未定义字段；原始payload、工具注册参数、活动白名单是明确例外。JSON引用仍须服务端做来源/租户/范围验证，数据库JSON类型检查不代替语义校验。

### external_ref

外部事实稳定引用，不用裸ID；resolved由读取结果记录，不暗示有FK

```json
{
  "type": "object",
  "properties": {
    "namespace": {
      "type": "string"
    },
    "object_type": {
      "type": "string"
    },
    "id": {
      "type": "string"
    },
    "version": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "captured_at": {
      "anyOf": [
        {
          "type": "string",
          "format": "date-time"
        },
        {
          "type": "null"
        }
      ]
    }
  },
  "required": [
    "namespace",
    "object_type",
    "id",
    "version",
    "captured_at"
  ],
  "additionalProperties": false
}
```

### actor

真实主体；模型/服务要名称版本；人id指public.users

```json
{
  "type": "object",
  "properties": {
    "type": {
      "enum": [
        "user",
        "service",
        "model",
        "legacy_unknown"
      ]
    },
    "user_id": {
      "anyOf": [
        {
          "type": "string",
          "format": "uuid"
        },
        {
          "type": "null"
        }
      ]
    },
    "name_snapshot": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "service_name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "service_version": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    }
  },
  "required": [
    "type",
    "user_id",
    "name_snapshot",
    "service_name",
    "service_version"
  ],
  "additionalProperties": false,
  "allOf": [
    {
      "if": {
        "properties": {
          "type": {
            "const": "user"
          }
        }
      },
      "then": {
        "properties": {
          "user_id": {
            "type": "string",
            "format": "uuid"
          },
          "name_snapshot": {
            "type": "string",
            "minLength": 1
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "type": {
            "enum": [
              "service",
              "model"
            ]
          }
        }
      },
      "then": {
        "properties": {
          "service_name": {
            "type": "string",
            "minLength": 1
          }
        }
      }
    }
  ]
}
```

### error

真实失败信息，不以空查询代替；不含凭据

```json
{
  "type": "object",
  "properties": {
    "code": {
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "retryable": {
      "type": "boolean"
    },
    "occurred_at": {
      "type": "string",
      "format": "date-time"
    }
  },
  "required": [
    "code",
    "message",
    "retryable",
    "occurred_at"
  ],
  "additionalProperties": false
}
```

### retention

完整存储与输入完整性不同；未知大小不可填0

```json
{
  "type": "object",
  "properties": {
    "original_size_bytes": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "retained_size_bytes": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "original_sha256": {
      "anyOf": [
        {
          "type": "string",
          "pattern": "^[a-f0-9]{64}$"
        },
        {
          "type": "null"
        }
      ]
    },
    "retained_sha256": {
      "anyOf": [
        {
          "type": "string",
          "pattern": "^[a-f0-9]{64}$"
        },
        {
          "type": "null"
        }
      ]
    },
    "truncated": {
      "type": "boolean"
    },
    "reason": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "omitted_paths": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "required": [
    "original_size_bytes",
    "retained_size_bytes",
    "original_sha256",
    "retained_sha256",
    "truncated",
    "reason",
    "omitted_paths"
  ],
  "additionalProperties": false
}
```

### scope

明确范围；空数组不意味着整案；whole_case也冻结成员ID

```json
{
  "type": "object",
  "properties": {
    "kind": {
      "enum": [
        "whole_case",
        "selected_alerts",
        "explicit_objects"
      ]
    },
    "alert_ids": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "uuid"
      }
    },
    "object_keys": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "window_start": {
      "anyOf": [
        {
          "type": "string",
          "format": "date-time"
        },
        {
          "type": "null"
        }
      ]
    },
    "window_end": {
      "anyOf": [
        {
          "type": "string",
          "format": "date-time"
        },
        {
          "type": "null"
        }
      ]
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "required": [
    "kind",
    "alert_ids",
    "object_keys",
    "window_start",
    "window_end",
    "limitations"
  ],
  "additionalProperties": false
}
```

### evidence_ref

每条引用准确定位来源；由程序按type校验相应字段及作用域

```json
{
  "type": "object",
  "properties": {
    "type": {
      "enum": [
        "alert_material",
        "artifact",
        "task_revision",
        "result",
        "external"
      ]
    },
    "id": {
      "anyOf": [
        {
          "type": "string",
          "format": "uuid"
        },
        {
          "type": "null"
        }
      ]
    },
    "external": {
      "anyOf": [
        {
          "$ref": "#/$defs/external_ref"
        },
        {
          "type": "null"
        }
      ]
    },
    "source_path": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "row_keys": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "role": {
      "enum": [
        "observation",
        "source_label",
        "prior_analysis",
        "human_statement",
        "execution_receipt"
      ]
    }
  },
  "required": [
    "type",
    "id",
    "external",
    "source_path",
    "row_keys",
    "role"
  ],
  "additionalProperties": false,
  "allOf": [
    {
      "if": {
        "properties": {
          "type": {
            "const": "external"
          }
        }
      },
      "then": {
        "properties": {
          "id": {
            "type": "null"
          },
          "external": {
            "$ref": "#/$defs/external_ref"
          }
        }
      },
      "else": {
        "properties": {
          "id": {
            "type": "string",
            "format": "uuid"
          },
          "external": {
            "type": "null"
          }
        }
      }
    }
  ]
}
```

### evidence_refs

已采用或可回查引用集合；禁止占位符

```json
{
  "type": "array",
  "items": {
    "$ref": "#/$defs/evidence_ref"
  }
}
```

### priority_basis

优先级已有评分方法和原始依据；不新造算法

```json
{
  "type": "object",
  "properties": {
    "method": {
      "type": "string"
    },
    "version": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "computed_at": {
      "anyOf": [
        {
          "type": "string",
          "format": "date-time"
        },
        {
          "type": "null"
        }
      ]
    },
    "inputs": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/evidence_ref"
      }
    },
    "explanation": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    }
  },
  "required": [
    "method",
    "version",
    "computed_at",
    "inputs",
    "explanation"
  ],
  "additionalProperties": false
}
```

### raw_payload

来源原JSON不限制厂商扩展；不是内部业务状态容器

```json
{
  "type": [
    "object",
    "array",
    "string",
    "number",
    "boolean",
    "null"
  ]
}
```

### detection

检测语义有则保留；评分状态与值配套，标签不当攻击事实

```json
{
  "type": "object",
  "properties": {
    "rule_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "rule_name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "tactics": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "techniques": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "labels_provided": {
      "type": "boolean"
    },
    "confidence_state": {
      "enum": [
        "not_provided",
        "not_computed",
        "disabled",
        "failed",
        "available",
        "legacy_unverified"
      ]
    },
    "confidence_value": {
      "anyOf": [
        {
          "type": "number",
          "minimum": 0,
          "maximum": 100
        },
        {
          "type": "null"
        }
      ]
    },
    "confidence_label": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "confidence_rationale": {
      "anyOf": [
        {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        {
          "type": "null"
        }
      ]
    },
    "score_source": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "ocsf_class_uid": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    }
  },
  "required": [
    "rule_id",
    "rule_name",
    "tactics",
    "techniques",
    "labels_provided",
    "confidence_state",
    "confidence_value",
    "confidence_label",
    "confidence_rationale",
    "score_source",
    "ocsf_class_uid"
  ],
  "additionalProperties": false,
  "allOf": [
    {
      "if": {
        "properties": {
          "confidence_state": {
            "const": "available"
          }
        }
      },
      "then": {
        "properties": {
          "confidence_value": {
            "type": "number",
            "minimum": 0,
            "maximum": 100
          },
          "score_source": {
            "type": "string",
            "minLength": 1
          }
        }
      },
      "else": {
        "properties": {
          "confidence_value": {
            "type": "null"
          }
        }
      }
    }
  ]
}
```

### enrichment

保留Fusion收到的富化，项目按来源类型受控；源扩展只留raw

```json
{
  "type": "object",
  "properties": {
    "schema_version": {
      "type": "string"
    },
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "kind": {
            "type": "string"
          },
          "source": {
            "type": "string"
          },
          "collected_at": {
            "anyOf": [
              {
                "type": "string",
                "format": "date-time"
              },
              {
                "type": "null"
              }
            ]
          },
          "source_path": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ]
          },
          "value": {
            "$ref": "#/$defs/raw_payload"
          }
        },
        "required": [
          "kind",
          "source",
          "collected_at",
          "source_path",
          "value"
        ],
        "additionalProperties": false
      }
    }
  },
  "required": [
    "schema_version",
    "items"
  ],
  "additionalProperties": false
}
```

### source_scope

来源范围上限/截断明确，bounded observed不冒充完整参与集合

```json
{
  "type": "object",
  "properties": {
    "kind": {
      "enum": [
        "explicit_sources",
        "bounded_observed_references",
        "sequence_candidates",
        "unknown"
      ]
    },
    "received_count": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "retained_count": {
      "type": "integer",
      "minimum": 0
    },
    "complete": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ]
    },
    "truncated": {
      "type": "boolean"
    },
    "window_start": {
      "anyOf": [
        {
          "type": "string",
          "format": "date-time"
        },
        {
          "type": "null"
        }
      ]
    },
    "window_end": {
      "anyOf": [
        {
          "type": "string",
          "format": "date-time"
        },
        {
          "type": "null"
        }
      ]
    },
    "omission_reason": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    }
  },
  "required": [
    "kind",
    "received_count",
    "retained_count",
    "complete",
    "truncated",
    "window_start",
    "window_end",
    "omission_reason"
  ],
  "additionalProperties": false
}
```

### object_attributes

已收到进程/网络/文件的必要投影；缺失NULL，不从标题猜。IP用inet形式校验，端口0..65535，PID文本保跨平台原值

```json
{
  "type": "object",
  "properties": {
    "hostname": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "username": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "ip": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "hash_algorithm": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "hash_value": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "pid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "parent_pid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "process_name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "process_path": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "command_line": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "parent_process_name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "parent_command_line": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "session_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "src_ip": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "src_port": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0,
          "maximum": 65535
        },
        {
          "type": "null"
        }
      ]
    },
    "dst_ip": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "dst_port": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0,
          "maximum": 65535
        },
        {
          "type": "null"
        }
      ]
    },
    "dst_hostname": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "protocol": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "action": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "outcome": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "direction": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "bytes_sent": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "bytes_received": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    }
  },
  "required": [],
  "additionalProperties": false
}
```

### match_basis

库存匹配要给出方法和查询时间；只匹配主机不能推同账号

```json
{
  "type": "object",
  "properties": {
    "method": {
      "type": "string"
    },
    "matched_fields": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "checked_at": {
      "type": "string",
      "format": "date-time"
    },
    "inventory_version": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "candidate_count": {
      "type": "integer",
      "minimum": 0
    }
  },
  "required": [
    "method",
    "matched_fields",
    "checked_at",
    "inventory_version",
    "candidate_count"
  ],
  "additionalProperties": false
}
```

### correlation_basis

实际归并依据；候选时序不自动升级因果

```json
{
  "type": "object",
  "properties": {
    "method": {
      "type": "string"
    },
    "rule_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "object_keys": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "window_start": {
      "anyOf": [
        {
          "type": "string",
          "format": "date-time"
        },
        {
          "type": "null"
        }
      ]
    },
    "window_end": {
      "anyOf": [
        {
          "type": "string",
          "format": "date-time"
        },
        {
          "type": "null"
        }
      ]
    },
    "reason": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "relation_strength": {
      "enum": [
        "shared_object",
        "window_candidate",
        "sequence_candidate",
        "manual",
        "legacy_unverified"
      ]
    },
    "source_refs": {
      "$ref": "#/$defs/evidence_refs"
    }
  },
  "required": [
    "method",
    "rule_id",
    "object_keys",
    "window_start",
    "window_end",
    "reason",
    "relation_strength",
    "source_refs"
  ],
  "additionalProperties": false
}
```

### question

问题有稳定ID与证据要求；Deep只围绕问题加深

```json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    },
    "text": {
      "type": "string"
    },
    "scope": {
      "$ref": "#/$defs/scope"
    },
    "evidence_requirements": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "state": {
      "enum": [
        "open",
        "answered",
        "unresolved",
        "not_attempted"
      ]
    },
    "answer": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "evidence_refs": {
      "$ref": "#/$defs/evidence_refs"
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "required": [
    "id",
    "text",
    "scope",
    "evidence_requirements",
    "state",
    "answer",
    "evidence_refs",
    "limitations"
  ],
  "additionalProperties": false
}
```

### questions

本次提出/回答/未决问题

```json
{
  "type": "array",
  "items": {
    "$ref": "#/$defs/question"
  }
}
```

### finding

发现的原文、依据和反证独立，不用高置信度替代来源

```json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    },
    "statement": {
      "type": "string"
    },
    "state": {
      "enum": [
        "observed",
        "inferred",
        "unresolved",
        "withdrawn"
      ]
    },
    "scope": {
      "$ref": "#/$defs/scope"
    },
    "support": {
      "$ref": "#/$defs/evidence_refs"
    },
    "counterevidence": {
      "$ref": "#/$defs/evidence_refs"
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "required": [
    "id",
    "statement",
    "state",
    "scope",
    "support",
    "counterevidence",
    "limitations"
  ],
  "additionalProperties": false
}
```

### findings

逐项发现与证据

```json
{
  "type": "array",
  "items": {
    "$ref": "#/$defs/finding"
  }
}
```

### recommendation

可追踪建议；稳定proposal_id供审批关联；审批缺失unknown

```json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    },
    "action_type": {
      "type": "string"
    },
    "targets": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "object_key": {
            "type": "string"
          },
          "display_name": {
            "type": "string"
          }
        },
        "required": [
          "object_key",
          "display_name"
        ],
        "additionalProperties": false
      }
    },
    "reason": {
      "type": "string"
    },
    "approval_requirement": {
      "enum": [
        "required",
        "not_required",
        "unknown"
      ]
    },
    "source_refs": {
      "$ref": "#/$defs/evidence_refs"
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "required": [
    "id",
    "action_type",
    "targets",
    "reason",
    "approval_requirement",
    "source_refs",
    "limitations"
  ],
  "additionalProperties": false
}
```

### recommendations

同一次分析的建议列表，不含假执行状态

```json
{
  "type": "array",
  "items": {
    "$ref": "#/$defs/recommendation"
  }
}
```

### diagnosis

事件级汇总诊断，不冒充Case全流程

```json
{
  "type": "object",
  "properties": {
    "conclusion": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "validation_state": {
      "enum": [
        "not_checked",
        "accepted",
        "rejected",
        "system_only",
        "legacy_unverified"
      ]
    },
    "findings": {
      "$ref": "#/$defs/findings"
    },
    "source_refs": {
      "$ref": "#/$defs/evidence_refs"
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "required": [
    "conclusion",
    "validation_state",
    "findings",
    "source_refs",
    "limitations"
  ],
  "additionalProperties": false
}
```

### case_impact

描述影响，不自动改变当前判断或案件状态

```json
{
  "type": "object",
  "properties": {
    "summary": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "supported_changes": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "cannot_generalize": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "affected_scope": {
      "$ref": "#/$defs/scope"
    },
    "next_steps": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "required": [
    "summary",
    "supported_changes",
    "cannot_generalize",
    "affected_scope",
    "next_steps"
  ],
  "additionalProperties": false
}
```

### limits

实际启动时约束，非全局可变配置引用；未知项NULL

```json
{
  "type": "object",
  "properties": {
    "max_model_calls": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "max_tokens": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "max_tool_calls": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "max_rows_per_query": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "deadline_at": {
      "anyOf": [
        {
          "type": "string",
          "format": "date-time"
        },
        {
          "type": "null"
        }
      ]
    },
    "policy_version": {
      "type": "string"
    }
  },
  "required": [
    "max_model_calls",
    "max_tokens",
    "max_tool_calls",
    "max_rows_per_query",
    "deadline_at",
    "policy_version"
  ],
  "additionalProperties": false
}
```

### usage

零与未知分开；只在真实叶子调用计费，父阶段NULL

```json
{
  "type": "object",
  "properties": {
    "input_tokens": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "output_tokens": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "cached_input_tokens": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "reasoning_tokens": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "total_tokens": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "cost": {
      "anyOf": [
        {
          "type": "number",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "currency": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "price_version": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "usage_state": {
      "enum": [
        "reported",
        "partial",
        "unavailable",
        "not_applicable"
      ]
    },
    "cost_state": {
      "enum": [
        "priced",
        "unpriced",
        "not_applicable"
      ]
    },
    "request_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    }
  },
  "required": [
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "reasoning_tokens",
    "total_tokens",
    "cost",
    "currency",
    "price_version",
    "usage_state",
    "cost_state",
    "request_id"
  ],
  "additionalProperties": false,
  "allOf": [
    {
      "if": {
        "properties": {
          "cost_state": {
            "const": "priced"
          }
        }
      },
      "then": {
        "properties": {
          "cost": {
            "type": "number",
            "minimum": 0
          },
          "currency": {
            "type": "string",
            "minLength": 1
          },
          "price_version": {
            "type": "string",
            "minLength": 1
          }
        }
      },
      "else": {
        "properties": {
          "cost": {
            "type": "null"
          }
        }
      }
    }
  ]
}
```

### tool_args

scope/window/limit在统一外壳；parameters依name+contract_version的工具参数schema校验

```json
{
  "type": "object",
  "properties": {
    "tool_name": {
      "type": "string"
    },
    "contract_version": {
      "type": "string"
    },
    "scope": {
      "$ref": "#/$defs/scope"
    },
    "limit": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "parameters": {
      "type": "object"
    }
  },
  "required": [
    "tool_name",
    "contract_version",
    "scope",
    "limit",
    "parameters"
  ],
  "additionalProperties": false
}
```

### input_snapshot

冻结实际上下文，不仅保高层说明；model_view使用原始request工件

```json
{
  "type": "object",
  "properties": {
    "schema_version": {
      "type": "string"
    },
    "run_kind": {
      "enum": [
        "alert_basic",
        "incident_diagnosis",
        "baseline",
        "ai_question"
      ]
    },
    "scope_revision": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "scope": {
      "$ref": "#/$defs/scope"
    },
    "source_materials": {
      "$ref": "#/$defs/evidence_refs"
    },
    "prior_results": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "uuid"
      }
    },
    "task_revisions": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "uuid"
      }
    },
    "comparison_result_id": {
      "anyOf": [
        {
          "type": "string",
          "format": "uuid"
        },
        {
          "type": "null"
        }
      ]
    },
    "projection_version": {
      "type": "string"
    },
    "omissions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "source_ref": {
            "$ref": "#/$defs/evidence_ref"
          },
          "reason": {
            "type": "string"
          }
        },
        "required": [
          "source_ref",
          "reason"
        ],
        "additionalProperties": false
      }
    },
    "captured_at": {
      "type": "string",
      "format": "date-time"
    }
  },
  "required": [
    "schema_version",
    "run_kind",
    "scope_revision",
    "scope",
    "source_materials",
    "prior_results",
    "task_revisions",
    "comparison_result_id",
    "projection_version",
    "omissions",
    "captured_at"
  ],
  "additionalProperties": false
}
```

### model_exchange

记录实际请求/响应与provider参数；外部协议payload保原始形状

```json
{
  "type": "object",
  "properties": {
    "schema_version": {
      "type": "string"
    },
    "provider": {
      "type": "string"
    },
    "model": {
      "type": "string"
    },
    "direction": {
      "enum": [
        "request",
        "response"
      ]
    },
    "payload": {
      "$ref": "#/$defs/raw_payload"
    },
    "captured_at": {
      "type": "string",
      "format": "date-time"
    },
    "request_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "usage": {
      "anyOf": [
        {
          "$ref": "#/$defs/usage"
        },
        {
          "type": "null"
        }
      ]
    }
  },
  "required": [
    "schema_version",
    "provider",
    "model",
    "direction",
    "payload",
    "captured_at",
    "request_id",
    "usage"
  ],
  "additionalProperties": false
}
```

### tool_exchange

返回状态、实际查询、行和完整性；无结果不能造空rows

```json
{
  "type": "object",
  "properties": {
    "schema_version": {
      "type": "string"
    },
    "tool_name": {
      "type": "string"
    },
    "contract_version": {
      "type": "string"
    },
    "actual_args": {
      "$ref": "#/$defs/tool_args"
    },
    "state": {
      "enum": [
        "planned",
        "running",
        "completed",
        "failed",
        "timeout",
        "cancelled",
        "skipped",
        "unknown"
      ]
    },
    "rows": {
      "anyOf": [
        {
          "type": "array",
          "items": {
            "$ref": "#/$defs/raw_payload"
          }
        },
        {
          "type": "null"
        }
      ]
    },
    "returned_rows": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "truncated": {
      "type": "boolean"
    },
    "query_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "error": {
      "anyOf": [
        {
          "$ref": "#/$defs/error"
        },
        {
          "type": "null"
        }
      ]
    },
    "captured_at": {
      "type": "string",
      "format": "date-time"
    }
  },
  "required": [
    "schema_version",
    "tool_name",
    "contract_version",
    "actual_args",
    "state",
    "rows",
    "returned_rows",
    "truncated",
    "query_id",
    "error",
    "captured_at"
  ],
  "additionalProperties": false,
  "allOf": [
    {
      "if": {
        "properties": {
          "state": {
            "const": "completed"
          }
        }
      },
      "then": {
        "properties": {
          "rows": {
            "type": "array",
            "items": {
              "$ref": "#/$defs/raw_payload"
            }
          },
          "returned_rows": {
            "type": "integer",
            "minimum": 0
          },
          "error": {
            "type": "null"
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "state": {
            "enum": [
              "failed",
              "timeout",
              "cancelled",
              "unknown",
              "skipped",
              "planned",
              "running"
            ]
          }
        }
      },
      "then": {
        "properties": {
          "rows": {
            "type": "null"
          },
          "returned_rows": {
            "type": "null"
          }
        }
      }
    }
  ]
}
```

### analysis_block

领域/Deep分析保持统一证据结构，domain不是新增四套状态机

```json
{
  "type": "object",
  "properties": {
    "schema_version": {
      "type": "string"
    },
    "domain": {
      "type": "string"
    },
    "questions": {
      "$ref": "#/$defs/questions"
    },
    "findings": {
      "$ref": "#/$defs/findings"
    },
    "recommendations": {
      "$ref": "#/$defs/recommendations"
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "required": [
    "schema_version",
    "domain",
    "questions",
    "findings",
    "recommendations",
    "limitations"
  ],
  "additionalProperties": false
}
```

### graph

历史图和探索图共同数据形状但不同存储责任；edge必须有来源和强度

```json
{
  "type": "object",
  "properties": {
    "schema_version": {
      "type": "string"
    },
    "nodes": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {
            "type": "string"
          },
          "type": {
            "enum": [
              "host",
              "user",
              "ip",
              "domain",
              "url",
              "file",
              "hash",
              "process",
              "email",
              "application",
              "cloud_resource",
              "technique",
              "other"
            ]
          },
          "label": {
            "type": "string"
          },
          "object_key": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ]
          },
          "alert_ids": {
            "type": "array",
            "items": {
              "type": "string",
              "format": "uuid"
            }
          },
          "source_refs": {
            "$ref": "#/$defs/evidence_refs"
          }
        },
        "required": [
          "id",
          "type",
          "label",
          "object_key",
          "alert_ids",
          "source_refs"
        ],
        "additionalProperties": false
      }
    },
    "edges": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {
            "type": "string"
          },
          "from": {
            "type": "string"
          },
          "to": {
            "type": "string"
          },
          "relation": {
            "type": "string"
          },
          "strength": {
            "enum": [
              "observed",
              "inferred",
              "candidate"
            ]
          },
          "source_refs": {
            "$ref": "#/$defs/evidence_refs"
          },
          "limitations": {
            "type": "array",
            "items": {
              "type": "string"
            }
          }
        },
        "required": [
          "id",
          "from",
          "to",
          "relation",
          "strength",
          "source_refs",
          "limitations"
        ],
        "additionalProperties": false
      }
    },
    "layout": {
      "anyOf": [
        {
          "type": "object",
          "additionalProperties": {
            "type": "object",
            "properties": {
              "x": {
                "type": "number"
              },
              "y": {
                "type": "number"
              }
            },
            "required": [
              "x",
              "y"
            ],
            "additionalProperties": false
          }
        },
        {
          "type": "null"
        }
      ]
    },
    "expanded_node_ids": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "selected_node_ids": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "required": [
    "schema_version",
    "nodes",
    "edges",
    "layout",
    "expanded_node_ids",
    "selected_node_ids",
    "limitations"
  ],
  "additionalProperties": false
}
```

### report_result

结构报告与results同版，不让渲染另生事实

```json
{
  "type": "object",
  "properties": {
    "schema_version": {
      "type": "string"
    },
    "result_id": {
      "type": "string",
      "format": "uuid"
    },
    "title": {
      "type": "string"
    },
    "conclusion": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "closing_note": {
      "type": "string"
    },
    "findings": {
      "$ref": "#/$defs/findings"
    },
    "questions": {
      "$ref": "#/$defs/questions"
    },
    "recommendations": {
      "$ref": "#/$defs/recommendations"
    },
    "case_impact": {
      "$ref": "#/$defs/case_impact"
    }
  },
  "required": [
    "schema_version",
    "result_id",
    "title",
    "conclusion",
    "closing_note",
    "findings",
    "questions",
    "recommendations",
    "case_impact"
  ],
  "additionalProperties": false
}
```

### handoff

无有效模型结论仍保存实际停止说明

```json
{
  "type": "object",
  "properties": {
    "schema_version": {
      "type": "string"
    },
    "stop_reason": {
      "type": "string"
    },
    "summary": {
      "type": "string"
    },
    "successful_steps": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "uuid"
      }
    },
    "failed_steps": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "uuid"
      }
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "required": [
    "schema_version",
    "stop_reason",
    "summary",
    "successful_steps",
    "failed_steps",
    "limitations"
  ],
  "additionalProperties": false
}
```

### query_plan

计划阶段问题到工具映射；仅计划不计调用

```json
{
  "type": "object",
  "properties": {
    "schema_version": {
      "type": "string"
    },
    "questions": {
      "$ref": "#/$defs/questions"
    },
    "planned_queries": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "question_id": {
            "type": "string"
          },
          "args": {
            "$ref": "#/$defs/tool_args"
          },
          "reason": {
            "type": "string"
          }
        },
        "required": [
          "question_id",
          "args",
          "reason"
        ],
        "additionalProperties": false
      }
    }
  },
  "required": [
    "schema_version",
    "questions",
    "planned_queries"
  ],
  "additionalProperties": false
}
```

### artifact_payload

content_json按artifacts.kind选择下列具体合同；禁止仅靠宽泛JSON通过

```json
{
  "anyOf": [
    {
      "$ref": "#/$defs/input_snapshot"
    },
    {
      "$ref": "#/$defs/model_exchange"
    },
    {
      "$ref": "#/$defs/tool_args"
    },
    {
      "$ref": "#/$defs/tool_exchange"
    },
    {
      "$ref": "#/$defs/analysis_block"
    },
    {
      "$ref": "#/$defs/graph"
    },
    {
      "$ref": "#/$defs/report_result"
    },
    {
      "$ref": "#/$defs/raw_payload"
    },
    {
      "$ref": "#/$defs/handoff"
    },
    {
      "$ref": "#/$defs/query_plan"
    },
    {
      "$ref": "#/$defs/alert_explanation"
    }
  ]
}
```

### activity_detail

活动原因/入口与实际影响；不以展示文案充字段

```json
{
  "type": "object",
  "properties": {
    "schema_version": {
      "type": "string"
    },
    "reason": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "request_key": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "source": {
      "type": "string"
    },
    "expected_version": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "actual_version": {
      "anyOf": [
        {
          "type": "integer",
          "minimum": 0
        },
        {
          "type": "null"
        }
      ]
    },
    "notes": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "required": [
    "schema_version",
    "reason",
    "request_key",
    "source",
    "expected_version",
    "actual_version",
    "notes"
  ],
  "additionalProperties": false
}
```

### activity_value

被改字段的类型化值由target_type字段白名单检查；原件/凭据不进入活动

```json
{
  "type": "object",
  "additionalProperties": {
    "type": [
      "string",
      "number",
      "boolean",
      "null",
      "array",
      "object"
    ]
  }
}
```

### alert_explanation

告警Explain独立于当前判定和原始说明；保留正文、生成方式/时间、依据与建议

```json
{
  "type": "object",
  "properties": {
    "schema_version": {
      "type": "string"
    },
    "body": {
      "type": "string"
    },
    "generation_method": {
      "enum": [
        "source",
        "template",
        "model",
        "legacy"
      ]
    },
    "generated_at": {
      "type": [
        "string",
        "null"
      ],
      "format": "date-time"
    },
    "source_refs": {
      "$ref": "#/$defs/evidence_refs"
    },
    "recommendations": {
      "$ref": "#/$defs/recommendations"
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "required": [
    "schema_version",
    "body",
    "generation_method",
    "generated_at",
    "source_refs",
    "recommendations",
    "limitations"
  ],
  "additionalProperties": false
}
```

## 5. 关系、索引及写入规则

### composite_unique_keys

```json
{
  "alert_materials": [
    "tenant_id,alert_id,id"
  ],
  "alert_assessments": [
    "tenant_id,alert_id,id"
  ],
  "incident_diagnoses": [
    "tenant_id,incident_id,id"
  ],
  "case_assessments": [
    "tenant_id,case_id,id"
  ],
  "task_revisions": [
    "tenant_id,case_id,task_id,id",
    "tenant_id,case_id,id"
  ],
  "tasks": [
    "tenant_id,case_id,id"
  ],
  "runs": [
    "tenant_id,case_id,id",
    "tenant_id,alert_id,id",
    "tenant_id,incident_id,id"
  ],
  "run_members": [
    "tenant_id,case_id,run_id,alert_id"
  ],
  "run_steps": [
    "tenant_id,run_id,id"
  ],
  "artifacts": [
    "tenant_id,case_id,id",
    "tenant_id,alert_id,id",
    "tenant_id,incident_id,id",
    "tenant_id,run_id,id"
  ],
  "results": [
    "tenant_id,case_id,id",
    "tenant_id,case_id,source_run_id,id"
  ],
  "conversations": [
    "tenant_id,case_id,id"
  ],
  "messages": [
    "tenant_id,case_id,conversation_id,id",
    "tenant_id,case_id,id"
  ]
}
```

### deferred_constraints

```json
[
  "tasks.current_revision_id与task_revisions.task_id循环使用预分配UUID+DEFERRABLE INITIALLY DEFERRED",
  "alerts/incidents/cases最新指针先NULL，子行插入后同事务更新；DDL建完表再ALTER TABLE加FK",
  "runs/steps与artifacts互引先预分配UUID，输入冻结和running在同事务；延迟约束提交必须一致"
]
```

### application_invariants

```json
[
  "原子发布 JSON条目ID唯一、引用可解析且位于本轮允许来源；数据库JSON类型不能代替语义验证",
  "所有JSON evidence_ref按类型精确一个来源(id或external)，scope时间窗口成对且start<=end，alert_ids/object_keys去重",
  "detection confidence_state=available须value非空且0..100；缺标签用labels_provided=false而非声称无标签",
  "usage.tokens部分已知时显示known_sum+unknown_call_count，不给unknown补0；费用保币种/计价版，不合计不同币种",
  "案例history统一DTO将Run生命周期和Results连接；未保存AI执行不纳入正式调查历史；待更新baseline始终显示",
  "当前判断是否覆盖当前Case按assessment_members与case_alerts集合比较；scope_revision不同只说明范围曾变，不直接证明结论错误",
  "claimed后写入者必须携带run_id+expected_state/version；取消请求不等于停止证明，未知不释放槽",
  "新写入保证用户/资产/连接器同租户；历史未解析值单列，不凭名字联结"
]
```

### index_plan

```json
{
  "alerts": [
    "(tenant_id,event_time DESC,id)",
    "(tenant_id,handling_status,event_time DESC,id)",
    "(tenant_id,severity,event_time DESC,id)",
    "(tenant_id,owner_id,event_time DESC,id)"
  ],
  "incidents": [
    "(tenant_id,business_updated_at DESC,id)",
    "(tenant_id,handling_status,business_updated_at DESC,id)"
  ],
  "case_alerts": [
    "UNIQUE(tenant_id,case_id,alert_id)",
    "(tenant_id,alert_id,case_id)"
  ],
  "case_incidents": [
    "UNIQUE(tenant_id,case_id,incident_id)",
    "(tenant_id,incident_id,case_id)"
  ],
  "runs": [
    "(tenant_id,case_id,requested_at DESC,id)",
    "pending部分唯一",
    "baseline活跃部分唯一"
  ],
  "run_steps": [
    "UNIQUE(tenant_id,run_id,seq)"
  ],
  "results": [
    "(tenant_id,case_id,saved_at DESC,id)",
    "root baseline/ai_saved部分唯一",
    "supersedes部分唯一"
  ],
  "task_revisions": [
    "UNIQUE(tenant_id,task_id,revision)",
    "(tenant_id,case_id,state,due_at)"
  ],
  "messages": [
    "UNIQUE(tenant_id,conversation_id,sequence)"
  ],
  "artifacts": [
    "(tenant_id,run_id,kind,captured_at,id)",
    "(tenant_id,case_id,kind,captured_at,id)"
  ],
  "alert_objects": [
    "(tenant_id,object_type,normalized_value,alert_id)",
    "(tenant_id,material_id)"
  ],
  "activity_targets": [
    "各类型target的(tenant_id,target_id,activity_id)"
  ],
  "comments": [
    "三个对象分别(tenant_id,target_id,created_at,id)"
  ]
}
```

### artifact_contracts

```json
{
  "input_snapshot": "input_snapshot",
  "model_request": "model_exchange",
  "model_response": "model_exchange",
  "tool_request": "tool_args",
  "tool_response": "tool_exchange",
  "domain_analysis": "analysis_block",
  "deep_analysis": "analysis_block",
  "attack_chain": "graph",
  "attack_path": "graph",
  "alert_graph": "graph",
  "report_json": "report_result",
  "report_markdown": "content_text",
  "attachment": "blob_ref or content_text",
  "source_snapshot": "raw_payload",
  "handoff": "handoff",
  "query_plan": "query_plan",
  "alert_explanation": "alert_explanation"
}
```

### auto_adoption_policy

```json
{
  "eligible": "baseline completed + result.validation_state=accepted + model结论非空，非system_handoff；允许partial但仅采用conclusion_covered成员",
  "scope": "Run.scope_revision等于Case.scope_revision且冻结成员集合等于当前成员；至少一条结论覆盖成员",
  "order": "锁Case；本轮started_at之后已有判断采用则跳过，避免覆盖较新的人工/其他判断",
  "write": "新增case_assessment及sources/members，更新Case指针并写活动，同事务；重复同一result返回原采用记录",
  "ai": "仅明确采用；保存AI答案不更新Case",
  "status": "不自动改变Case处理状态；无自动启动/接续"
}
```

## 6. 已确认决定与剩余边界

| ID | 项目 | 状态 | 决定/建议 |
| --- | --- | --- | --- |
| D01 | 事件严重程度覆盖 | confirmed_by_user | 允许人工覆盖事件等级，保留自动汇总值；仅覆盖事件，不修改成员告警；记录人、时间、理由 |
| D02 | Case当前判断采用 | confirmed_by_user | 有效基础调查结果自动更新案件当前判断；AI结果仍需明确采用 |
| D03 | AI与baseline互斥 | confirmed_by_user | 仅限制基础调查单活跃；AI模型/工具问答可并行，不与基础调查共用槽 |
| D04 | 空Case/已解决Case | proposal_not_confirmed | 允许保存空案/历史；无成员禁止启动；已解决案变更不静默重开，启动前显式重开 |

D04特殊流程尚未开放，不能据建表完成推断相关API已实现。旧表历史不自动回填或迁移，当前业务写入尚未切换。

## 7. 案件读取合同

这些字段是已有新库记录的只读投影，不增加表列。对应[OpenAPI](socai2-independent-api-v2.openapi.json)。

| 读取入口／字段 | 来源与口径 |
| --- | --- |
| `GET /api/v1/socai2/cases` | 当前身份有权读取的租户案件；`limit` 1—50，默认20；标题／完整ID搜索、状态、严重程度、负责人、分配状态与指标筛选 |
| `items[].case`、`member_count`、`open_task_count`、`baseline_records` | 案件字段、当前成员数、当前未完成任务数、待启动及活跃基础调查；不从本地演示集合补齐 |
| `total` | 本次筛选后的案件总数，不等于本页条数 |
| `metrics` | 全部有权读取的待处理案件（新建／处理中），不随筛选和分页变化；待分配排除负责人无法解析，处理中按业务状态，高严重程度按`high`，待人工按有未开始／进行中任务的Case去重 |
| `next_cursor` | 按`business_updated_at/id`倒序的稳定续页位置，绑定租户与筛选；单次GET为同一只读快照，跨请求不冻结整个集合 |
| 当前判断`coverage`与`input_freshness` | 成员覆盖与受跟踪输入依据状态分开。材料、分诊／反馈、事件和H实质依据变化须核对；外部情报／湖后来变化不自动表示已重新核验 |
| `RunDetail.execution_summary` | 通过本轮已完成`C1.executor`步骤读取原始、SHA校验通过的`execution_plan`；旧轮无工件返回null，不用当前配置回填 |
| `execution_summary.capabilities` | 启动时绑定工具、可提供工具、绑定数、不支持项及未提供原因；四领域共享一次分析，200成员仅为保存上限，主机／窗口绑定不是告警归因证明 |
| `execution_summary.limits/final_reservation` | 本轮冻结的限额及最终综合预留；新完整C为48000保守单位、4模型、4工具、120秒。保守字节上界不是真实tokens，旧Run及A/I保持原额度；历史未记录项为null |
| `execution_summary.availability/artifact_id` | 原工件可用性及回查身份；不可读时不伪造能力摘要，不因GET执行查询或更新业务时间 |

新执行器版本为`socai2.baseline-executor.v2`，C3执行建议合同为`socai2.baseline-analysis.v2`，含明确绑定和优先级；C6未来建议仍使用原v1建议合同。直接query不增加Deep模型调用；查询按绑定复用、Deep按问题复用；C6通过原计划索引及`projection_id`回查对应查询材料，不能用新建议接管旧执行记录。

## 8. 页面数据合同（126增量）

`CasePageData`的版本为`socai2.case-page-data.v1`；列表`items[].page_data`、详情`page_data`、专用GET及导出`case-page-data.json`使用相同读取/计数代码。`determination`直接等于当前采用的`case_assessments.conclusion`，同时携带该判断的来源、形成/采用时间、范围；无指针为null。执行错误留原Run/Step，不填到此字段。

`PATCH /api/v1/socai2/cases/{case_id}/page-data`接收operation_key、expected_row_version、classification、due_at、source、source_note，两个业务字段需明确传入（可null）；不把省略理解为清空。`POST .../evidence-index`接收operation_key、expected_row_version、expected_current_artifact_id及index。写入要求cases:write和同租户真实用户；GET要求cases:read。幂等重放返回原回执，冲突返回409；管理变化与证据发布仅增加row_version和业务时间及活动，不更改处理状态/成员范围、不生成Run。

证据正文使用[严格Schema](../../services/api/app/socai2/case_evidence.schema.json)：schema_version、scope_revision、alert_ids、supersedes_artifact_id、availability_state、limitations、entries。条目包含稳定命名空间ID、类型/标题、成员范围、对象材料键、原始来源、verdict及其来源、可空的命名空间威胁身份及来源、可空处置回执、active/withdrawn。每次发布追加不可变工件，Case锁内比较版本、当前指针及范围；前版必须是实际当前指针。撤回/改判不覆盖前版，重复ID拒绝。

来源必须为同租户、同Case/条目成员的已保存行及有效JSON Pointer。v1支持Alert材料、C1冻结角色目录、结果的明确段落/条目范围、已完成人工任务及实际关联response_links的专用处置回执；普通模型请求不是处置回执。Alert原始材料仅登记的OCSF行为叶路径可作observation，其余保守为source_label，未注册工件格式拒绝。每组来源需覆盖条目声明成员；来源存在不代表标签的安全判断已经正确。

当前条目只取active且所有声明成员仍在本案的条目；部分成员移出时整条排除，不缩小历史范围。独立证据按稳定ID计数；关联威胁仅从malicious/suspicious且有明确威胁身份的当前条目按(namespace,key)去重，clean/unknown/conflicting不计威胁。无索引/不可得/引用失效为null；有效空索引或全撤回为0；全clean可以证据>0、威胁=0。partial同时返回已知计数和未覆盖范围，0不代表全案无威胁。详见[只读查询](../investigation/socai2-page-data-readback-20261106.sql)及[验收/边界](../investigation/socai2-page-data-handoff-20261106.md)。
