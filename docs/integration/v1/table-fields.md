# 当前数据库设计与字段字典：告警、调查及直接支撑数据

更新：2026-10-23。本篇回答“目前数据存在哪里、有哪些表、为什么这样关联、每个字段是什么含义、允许什么值”。面向接入后端和数据开发，描述**已存在的数据设计**。页面应展示什么属于另一份[产品建议](page-elements.md)；按页面编号取数的SQL/HTTP见[接入附件](page-data-mapping.md)。

## 1. 范围与阅读约定

本字典完整覆盖此前实际盘点的**25张相关表、428个字段**，不是共享PostgreSQL所有业务表的全集。其中六张核心表167列于2026-10-23 16:42再次只读核对列名/类型；其余19张表261列和全部约束沿2026-10-22 22:56元数据。每表行数也固定于22:56的样例生产租户，不是实时数量。

物理结构来自[data-catalog.json](data-catalog.json)；字段业务含义另外核迁移、写入者和读取代码。源码补充只解释字段，不能覆盖实际数据库列/类型/默认/约束，也不能把本地新增输出称为线上已部署。本轮拆分没有再次访问生产、运行模型或改表。

| 文档标记 | 怎么理解 |
| --- | --- |
| **DB约束** | 实际元数据中的CHECK/PK/FK/UNIQUE；数据库会按约束校验。每表下保留约束原文 |
| **API校验** | 某个接口允许的输入集合；不保证所有写入路径都经过该接口，不等于DB枚举 |
| **程序约定** | 当前读写程序实际使用的值；普通TEXT/VARCHAR/JSON字段可以扩展，不能当封闭PG枚举 |
| **示例/已观察** | 只证明样例出现该值，不穷尽所有合法值 |
| **自由值/未统一** | 没有确认封闭取值集合，保留原值；不得自行补枚举 |

这25表已盘点的字段中没有独立PostgreSQL ENUM类型；所谓“枚举”主要由CHECK、API或应用约定表达。字段列出完整SQL `data_type / udt_name`、可NULL及数据库默认；varchar长度/numeric精度未被该次元数据采集覆盖，不按早期DDL猜当前值。ARRAY的`_uuid`/`_text`分别是UUID[]/TEXT[]，JSONB数组不是SQL ARRAY。

NULL、空数组、0、false含义不同。默认值是省略列时的数据库表达式，显式写NULL不自动采用默认；字段可NULL不等于业务允许随意缺失。有列、表有行或约束存在，都不代表对应功能已经填入丰富数据。

<a id="database-connection"></a>

## 2. 数据位置、租户与对象关系

### 2.1 数据库位置与连接

| 项目 | 直接交接值 |
| --- | --- |
| 数据库类型 | PostgreSQL |
| 地址 / 端口 | `192.168.1.21:5432` |
| 数据库名 | `aisoc` |
| 表命名空间 | `public`；既有实际盘点按 `information_schema.columns.table_schema='public'` 读取，连接后也可用下方 SQL 确认 |
| 当前生产租户 | `f6a5c700-69b8-44fc-8238-609362fb1a9f` |
| 连接加密 | TLS，`sslmode=verify-full`，使用运维发放的 CA |
| 账号 / 密码 | 使用已授权的数据库查询账号；当前服务运行角色是 `aisoc_app`，不代表已经另行发放查询账号。凭据不放在文档中 |
| 现有配置位置 | 21 主机 `/opt/sting-aisoc-socai2/private/runtime.env` 及各服务受控 env；由运维交接所需连接信息，无需复制整个目录 |
| 原始结构证据 | [data-catalog.json](data-catalog.json)：实际盘点的25表428字段及约束 |

这些是当前项目库，不是20参考页面自己的数据库，也不是旧 `sting` 库或旧15432端口。沿用已发放连接即可；本次未创建数据库账号或更改权限。详细连接配置仍见 [configuration.md](configuration.md)。

```sql
SELECT current_database(), current_schema(), current_schemas(false);
SELECT to_regclass('public.alerts'), to_regclass('public.investigation_runs'),
       to_regclass('public.investigation_events'), to_regclass('public.investigation_artifacts');
```

查询时每个事务绑定租户，并在 SELECT 中显式加 tenant 条件：

```sql
BEGIN READ ONLY;
SELECT set_config('app.current_tenant_id', 'f6a5c700-69b8-44fc-8238-609362fb1a9f', TRUE);
-- SELECT ... WHERE tenant_id = 'f6a5c700-69b8-44fc-8238-609362fb1a9f'::uuid;
ROLLBACK;
```

`app.current_tenant_id` 是当前代码使用的变量名；只设置变量不能替代显式过滤。下面所有关联都包含租户，避免同名目标或历史资料串读。



<a id="table-overview"></a>

### 2.2 表的职责分组

| 分类 | 表 / 字段数 | 业务职责 |
| --- | --- | --- |
| 业务核心：告警、案件与调查结果 | [alerts](#alerts) / 63列 | 已有告警的持久主记录，保存来源/融合投影及当前处理状态；不是Run结果表。 |
| 业务核心：告警、案件与调查结果 | [aisoc_cases](#aisoc_cases) / 48列 | 人工案件容器：成员告警、人工状态/协作、SLA和关案资料；不能用它承载不存在的自动Case。 |
| 业务核心：告警、案件与调查结果 | [investigation_runs](#investigation_runs) / 18列 | 一次分诊或调查执行的生命周期和用量表，不等于一次完整安全事件或Case。 |
| 业务核心：告警、案件与调查结果 | [investigation_events](#investigation_events) / 13列 | 按执行步骤留存的事件账本。kind不同，payload合同不同。 |
| 业务核心：告警、案件与调查结果 | [investigation_artifacts](#investigation_artifacts) / 10列 | 按Run/步骤保存较大的结果文本、模型交换、图快照和报告。 |
| 业务核心：告警、案件与调查结果 | [aisoc_run_costs](#aisoc_run_costs) / 15列 | 按(run_id,tenant_id,请求模型)累计的成本/调用遥测，不是一调用一行。 |
| 接入身份与来源关联 | [tenants](#tenants) / 15列 | 租户隔离、套餐与配置根表；租户层级为自关联。catalog中本生产租户1行，其余租户不在本字典数据观察范围。 |
| 接入身份与来源关联 | [connectors](#connectors) / 29列 | 租户内连接器实例、认证/连接配置及采集健康状态；connector_type为类型标识，id为实例标识。 |
| 接入身份与来源关联 | [alert_source_links](#alert_source_links) / 15列 | 同一告警可对应多个来源系统finding；每个(alert_id,vendor,external_id)只有一行，保存最新回写尝试而非完整历史。 |
| 运行保护与失败留存 | [socai2_triage_budget_reservations](#socai2_triage_budget_reservations) / 9列 | 普通Kafka分诊请求的持久预算预留；按Run一行。charged_tokens是保守预留，不是provider实际Token或金额；未确认调用保留并发槽。 |
| 运行保护与失败留存 | [aisoc_dead_letters](#aisoc_dead_letters) / 12列 | 流水线拒绝输入的可查询摘要；用于解释拒绝原因，不是可重放完整原始消息仓库。 |
| 资产与漏洞上下文 | [assets](#assets) / 19列 | 资产库存/CMDB基础资料，可被告警处理上下文读取；本次catalog租户内0行，不表示功能已验证或无其他租户数据。 |
| 资产与漏洞上下文 | [asset_vulnerabilities](#asset_vulnerabilities) / 21列 | 资产漏洞发现记录；asset_id关联资产；同CVE可在多个资产/扫描器形成多条。补丁窗口三列是设计与运行资料，不能假设基本漏洞API已经写满。 |
| 资产与漏洞上下文 | [alert_asset_correlations](#alert_asset_correlations) / 8列 | 告警到资产/漏洞的关联表；alert_id是逻辑关联而非数据库外键；asset/vuln删除时只清空对应引用。 |
| 身份与权限上下文 | [identity_privilege](#identity_privilege) / 8列 | 轻量账号权限背景表，按(tenant_id,principal)唯一；不同于identity_nodes图节点的整数权限等级。 |
| 身份与权限上下文 | [identity_nodes](#identity_nodes) / 13列 | 身份关系图的节点表；(tenant_id,source_system,external_id)唯一。不等于Neo4j投影或identity_privilege小表。 |
| 身份与权限上下文 | [identity_edges](#identity_edges) / 10列 | 身份图有向关系；同租户source/target/type唯一。两端分别外键到节点，但这不是复合租户外键，查询仍需tenant条件。 |
| 组织记忆、反馈、知识与技能 | [aisoc_context_statements](#aisoc_context_statements) / 10列 | 从结构化分析员反馈编译的可读组织经验陈述；按租户/理由/范围/范围值唯一，达到佐证门槛才更新。不是模型自动生成任意事实的表。 |
| 组织记忆、反馈、知识与技能 | [aisoc_analyst_feedback](#aisoc_analyst_feedback) / 12列 | 结构化分析员判定反馈的逐条记录，保留原AI判定、人工判定、理由与上下文，供经验陈述统计。catalog无tenant/alert/users外键。 |
| 组织记忆、反馈、知识与技能 | [aisoc_kb_documents](#aisoc_kb_documents) / 12列 | 知识库文本分块表，一行一个chunk。每个chunk独立UUID；同一次导入共享标题等资料，未见独立父document_id，不能把id当整篇文档公共ID。 |
| 组织记忆、反馈、知识与技能 | [aisoc_tenant_skills](#aisoc_tenant_skills) / 18列 | 租户技能当前状态，一租户一个skill_id一行；与版本表分开。技能body用于程序读取，source_yaml用于保留作者文本。 |
| 组织记忆、反馈、知识与技能 | [aisoc_tenant_skill_versions](#aisoc_tenant_skill_versions) / 17列 | 技能内容版本快照，(tenant_id,skill_id,version)唯一；内容新增版本，回放引用/激活/退役戳可后补，因此不能称每列绝不更新。 |
| UEBA基线、异常与同群 | [ueba_entity_baselines](#ueba_entity_baselines) / 11列 | 实体的逐特征在线行为基线；非实体总名单，只有被送入处理的实体会形成记录。catalog没有tenant+entity唯一约束或tenant外键。 |
| UEBA基线、异常与同群 | [ueba_anomalies](#ueba_anomalies) / 14列 | UEBA评分达到阈值后持久化的异常记录；低于阈值不建此行，不等于全部事件或所有实体状态。 |
| UEBA基线、异常与同群 | [ueba_peer_groups](#ueba_peer_groups) / 8列 | 外部指定的同伴组统计；id为文本主键且catalog为全表唯一，并非(tenant,id)复合主键。 |


### 2.3 核心关系与身份语义


| 表 | 存什么 | 关键字段 / 如何关联 |
| --- | --- | --- |
| `public.alerts` | 告警基本信息、来源快照、融合说明、首次分诊投影、当前处理状态 | 主键 `id`；`tenant_id`；来源和首次快照在 `enrichment_data` |
| `public.investigation_runs` | 一次分诊/调查的运行信息、状态、起止时间、总用量 | 主键 `id`；`case_id` 是字符串目标，不是 Case 外键；另有 `raw_alert` |
| `public.investigation_events` | 首次分诊结论、调查完成度、处理步骤、工具调用记录 | `run_id → investigation_runs.id`；`kind` 区分事件；结构内容在 JSONB `payload` |
| `public.investigation_artifacts` | 调查结果 JSON、Markdown 报告、模型交换、链图快照、资料读取回执 | `run_id` 关联运行；可用 `event_id` 关联事件；`kind` 区分内容；正文在 TEXT `content` |
| `public.aisoc_run_costs` | 按 Run 和模型角色汇总的调用数、Token、费用来源 | `run_id`、`tenant_id` **为 TEXT**，关联 UUID 表时用 `r.id::text`、`r.tenant_id::text` |
| `public.aisoc_cases` | 人工 Case 的标题、状态、成员告警、责任与协作资料 | `id`；`alert_ids` 是 UUID 数组；自动调查可以没有 Case |

**报告正文直接查 `investigation_artifacts`：`kind='report_md'` 的 `content`。调查结果直接查同表：`kind='graph_result'` 的 `content`，解析成 JSON。** 不需要为了展示这两项再查 Kafka、Redis、Neo4j 或模型服务。

最常用的关系：

```text
同租户 alerts.id
  └─ 普通自动路径：investigation_runs.case_id = alerts.id::text
       （本次两例也可由 investigation_runs.raw_alert->>'id' 核对）
       ├─ investigation_events.run_id = investigation_runs.id
       ├─ investigation_artifacts.run_id = investigation_runs.id
       └─ aisoc_run_costs.run_id = investigation_runs.id::text

人工路径：aisoc_cases.id::text → investigation_runs.case_id
Case成员：alerts.id = ANY(aisoc_cases.alert_ids)，同时限定双方tenant_id
```

上图是两类已知入口，不是任意 Run 都适用的猜测规则。独立 graph 的目标还可能是 Fusion Incident。不要将所有 `run.case_id` 强转 UUID JOIN `aisoc_cases`。`alerts.enrichment_data.socai2_fusion.incident_id` 是融合分组，PG 没有供本流程使用的独立 `incidents` 主表。




| ID | 产生位置 | 关联方式 |
| --- | --- | --- |
| source_alert_id | 上游稳定告警UUID | 与tenant/source/connector组成source-v1身份，不等于PG alerts.id |
| canonical Alert ID | Fusion确定性UUID | alerts.id、fused.id/alert_row_id/alert.id；Case.alert_ids用这个UUID |
| source_event_ids/external_id | 上游原事件/finding引用 | 回溯原厂资料，不作为canonical指纹的替代 |
| Fusion incident_id | Fusion关联器 | Redis摘要；PG在alerts.enrichment_data.socai2_fusion.incident_id留关联，无独立PG incidents主表 |
| Case ID | Case API | 正式PG表aisoc_cases.id；与Incident并非自动一对一 |
| Run ID | Agents对应入口 | investigation_runs.id；事件/工件通过run_id关联 |
| Run.case_id | 外部关联字符串 | VARCHAR(200)，不是Case外键；普通自动分诊常为Alert UUID，人工为Case，独立graph可为Incident |

后端应保存自己触发时取得的tenant+Alert/Case/Run对应关系；不要对Run.case_id无条件CAST UUID后JOIN Case。自动升级沿同Run时`start_run ON CONFLICT DO NOTHING`通常保留首次Alert关联。



当前“调查”不是一张大结果表：`investigation_runs`存执行元信息，`investigation_events`存过程/结论事件，`investigation_artifacts`存正文，`aisoc_run_costs`存用量来源。`aisoc_cases`是人工案件容器，`alerts`是告警当前记录；它们不能互相替代。

应用关联与数据库外键分别描述：例如Run的`case_id`是字符串目标、成本表的run/tenant是TEXT、Case成员是UUID数组，不能因为名称像ID就假设数据库建立了FK。即使两端都有tenant列，关联时仍须显式限定同租户。

<a id="tables"></a>

## 3. 逐表设计、字段含义与实际约束

下面每张表先说明一行代表什么及写读用途，再列**全部字段**。字段的“取值/格式”与“业务含义”结合阅读；引用编号在本表后给出源码定位。所有样例内容和JSON键都只描述结构，不提供凭据值。


<a id="alerts"></a>

### 3.1 `alerts`

已有告警的持久主记录，保存来源/融合投影及当前处理状态；不是Run结果表。

关联与边界：tenant_id→tenants为实际FK；case_id/connector_id/assigned_to_id/parent_alert_id仅逻辑关联，不能写成已存在FK。source不在独立列，从enrichment_data.socai2_fusion.identity.source读。

字段数 **63**；2026-10-22 22:56样例租户行数 **3**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `uuid_generate_v4()` | 本系统规范告警ID，后续Alert、Run目标和图投影的关联键 | UUID；不是上游source_alert_id | Fusion AlertSink/HTTP submit生成或传入canonical ID（S1、S2、S3） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 告警所属租户 | UUID；实际FK tenants.id，删除租户级联删除 | 所有写入/读取按租户限定（S1、S2、S3） |
| `title` | character varying / varchar；非NULL | 无默认 | 来源告警标题 | 字符串；无枚举；Fusion写入截取500字符 | AlertSink写来源title；API列表/详情读取（S1、S2、S3） |
| `description` | text / text；可NULL | 无默认 | 来源告警描述/摘要 | 可空文本；不是融合说明或AI分诊理由 | AlertSink写来源description（S1、S2、S3） |
| `severity` | character varying / varchar；非NULL | `'medium'::character varying` | 告警严重程度 | 程序常用info=信息、low=低、medium=中、high=高、critical=严重；此实际表无severity CHECK | Fusion Severity枚举及API规范化/升级处理；不能用Case的DB CHECK约束套此列（S1、S2、S3、S4） |
| `status` | character varying / varchar；非NULL | `'new'::character varying` | 告警当前业务处理状态 | 无DB CHECK，PATCH为str非封闭枚举；已见程序new=新建、triaged=已分诊、triaging=分诊中、in_progress=处理中、investigating=调查中、resolved=已解决、false_positive=按误报关闭、closed=关闭；旧ORM注释还出现fp，非统一推荐写值 | Fusion写new；Agents初次结论写triaged或resolved；人工调查可写investigating；读者的终态口径不同须明确（S1、S2、S3、S4、S5） |
| `priority` | integer / int4；可NULL | `50` | 告警一般优先级整数 | ORM注释0—100、DB默认50；无实际CHECK；Alert PATCH仅int，无已核统一范围校验 | API人工更新/队列相关读取；不是Fusion ML priority_score或上下文priority_score（S1、S2、S3） |
| `category` | character varying / varchar；可NULL | 无默认 | 来源/业务分类 | 可空自由字符串；无统一枚举 | HTTP提交/现有告警读写模型（S1、S2、S3） |
| `mitre_tactics` | jsonb / jsonb；可NULL | `'[]'::jsonb` | 来源/映射的MITRE战术列表 | JSON数组，常用字符串如execution；没有数据库逐元素约束 | Fusion AlertSink写来源tactics；映射不等于已证实攻击（S1、S2、S3） |
| `mitre_techniques` | jsonb / jsonb；可NULL | `'[]'::jsonb` | 来源/映射的MITRE技术列表 | JSON数组，常用技术ID如T1059.001；不是数据库枚举 | Fusion/人工提交写；报告和查询读取（S1、S2、S3） |
| `connector_id` | uuid / uuid；可NULL | 无默认 | 来源连接器实例标识 | 可空UUID；实际约束目录没有此列FK | Fusion写上游连接器ID；不等于来源系统名称（S1、S2、S3） |
| `connector_type` | character varying / varchar；可NULL | 无默认 | 接入连接器类型代码 | 可空字符串，依来源扩展；无统一DB枚举 | Fusion写来源connector_type；空值不能从identity.version推断（S1、S2、S3） |
| `source_event_ids` | jsonb / jsonb；可NULL | `'[]'::jsonb` | 与告警关联的来源事件/引用ID列表 | JSON数组；元素通常字符串，可能含来源事件ID和来源告警ID；不是发生次数 | Fusion写/去重路径追加有界引用；不保证事件正文存在（S1、S2、S3） |
| `ocsf_class_uid` | integer / int4；可NULL | 无默认 | 来源携带的OCSF事件类标识 | 可空整数；无本表枚举CHECK | Fusion直接保留来源ocsf_class_uid；不据此声称规范化事件支路执行（S1、S2、S3） |
| `ai_score` | double precision / float8；可NULL | 无默认 | AI分诊置信度投影 | 程序采用浮点0—1；无DB范围CHECK；null=未提供 | Agents persist_auto_triage写confidence；与融合confidence和调查G.confidence分开（S1、S2、S3、S5） |
| `ai_summary` | text / text；可NULL | 无默认 | AI分诊说明/理由投影 | 可空文本；现自动路径可能包含结论、置信度、理由的拼接；不是统一最终调查摘要 | Agents写入有界rationale；准确阶段字段优先triage_verdict payload（S1、S2、S3、S5） |
| `ai_recommendations` | jsonb / jsonb；可NULL | `'[]'::jsonb` | AI分诊结构化建议投影 | JSON数组；空数组=未提供结构建议；元素由建议合同决定，不是执行记录 | Agents写proposed_actions/recommendations；API归一化返回（S1、S2、S3、S5） |
| `false_positive_score` | double precision / float8；可NULL | 无默认 | 早期AI/ML误报倾向分数栏位 | 可空浮点；无DB范围约束；不能等同disposition或ai_score | ORM定义保留；当前Fusion主写入未列此字段，本次不确认常驻填充（S1、S2、S3） |
| `anomaly_score` | double precision / float8；可NULL | 无默认 | Fusion异常评分 | 程序浮点0—1约定；无DB CHECK | Fusion ML scorer产出，AlertSink写fused.anomaly_score（S1、S2、S3） |
| `iocs` | jsonb / jsonb；可NULL | `'[]'::jsonb` | 来源提取的IOC列表 | JSON数组；本项目写入通常含type/value；非外部TI查询结果 | Fusion _iocs写；与enrichment_data.ioc_lookup和调查ioc_enrichments分开（S1、S2、S3） |
| `entities` | jsonb / jsonb；可NULL | `'[]'::jsonb` | 来源关联实体列表 | JSON数组，常用{type,value}；type为来源/代码约定，不是本表枚举 | Fusion _entities写；API组合related_entities（S1、S2、S3） |
| `raw_event` | jsonb / jsonb；可NULL | `'{}'::jsonb` | 来源原始载荷正文 | JSON对象约定，字段随来源变化；不是整个Kafka信封 | Fusion/submit保留原raw_event，不保证外部所有原文齐全（S1、S2、S3） |
| `dedup_hash` | character varying / varchar；可NULL | 无默认 | 告警去重指纹 | 可空字符串；哈希格式按来源fingerprint实现，不自行假定全部为SHA256 | Fusion alert.fingerprint写，按tenant+hash查重；实际约束目录不含该列唯一约束（S1、S2、S3） |
| `case_id` | uuid / uuid；可NULL | 无默认 | 告警关联人工Case标识 | 可空UUID；实际约束目录没有Case FK | 人工创建/关联Case或merge路径维护；自动调查不保证设置（S1、S2、S3） |
| `first_seen` | timestamp with time zone / timestamptz；可NULL | `now()` | 告警记录首次见到时间 | 可空timestamptz，实际DB默认now()；不等于first_seen_at | Fusion未显式传入时取DB默认；不能声称始终等于来源event_time（S1、S2、S3） |
| `last_seen` | timestamp with time zone / timestamptz；可NULL | `now()` | 告警记录最近见到时间 | 可空timestamptz，默认now()；不保证去重每次都更新 | 存量读写字段；当前去重追加ID语句未更新此列（S1、S2、S3） |
| `event_time` | timestamp with time zone / timestamptz；可NULL | `now()` | 来源告警发生时间 | 可空timestamptz，DB默认now()；Fusion源缺失时COALESCE到当前时间 | AlertSink写来源event_time；不能当上游采集时间（S1、S2、S3） |
| `resolved_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 告警被解决/终止处理的记录时间 | 可空timestamptz；null不等于运行失败 | 自动关闭写now；PATCH终态写时间；读取时结合status（S1、S2、S3、S5） |
| `created_at` | timestamp with time zone / timestamptz；可NULL | `now()` | 本系统告警记录创建时间 | 可空timestamptz，DB默认now() | 入库产生；列表newest按此时间而非event_time（S1、S2、S3） |
| `updated_at` | timestamp with time zone / timestamptz；可NULL | `now()` | 告警记录最近更新时间 | 可空timestamptz，DB默认now()；是否更新依写入路径 | ORM更新/自动分诊等显式刷新；不是每个调查事件时间（S1、S2、S3） |
| `snoozed_until` | timestamp with time zone / timestamptz；可NULL | 无默认 | 暂缓进入工作队列的截止时间 | 可空timestamptz；不是解决时间 | snooze服务写；队列根据时间过滤（S1、S2、S3、S6） |
| `snoozed_by_id` | uuid / uuid；可NULL | 无默认 | 最后设置暂缓的用户ID | 可空UUID；FK users.id，用户删除置空 | snooze操作记录执行者（S1、S2、S3、S6） |
| `disposition` | text / text；可NULL | 无默认 | 当前分诊/人工判定投影 | 无DB CHECK；反馈API集合true_positive=真阳性、benign_true_positive=良性真阳性、false_positive=误报、benign=良性旧值、escalate=升级；自动分诊另可写needs_review=待复核，不能把反馈集合当全库枚举 | 自动分诊与feedback override写；历史首次结论读Run事件（S1、S2、S3、S7、S5） |
| `first_seen_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 首次人工认领/确认时间，供响应时效指标使用 | 可空timestamptz；null=未记录；不是来源首次发生或浏览页时间 | 当前claim路径COALESCE写一次；旧模型/指标注释称首次查看不能作实际写入事实（S1、S2、S3、S6） |
| `confidence` | integer / int4；可NULL | 无默认 | Fusion融合置信评分整数 | DB CHECK允许null或0—100 | AlertSink由round(confidence_score*100)写；不是恶意概率或AI模型置信度（S1、S2、S3、S8） |
| `confidence_label` | text / text；可NULL | 无默认 | Fusion融合置信等级 | DB CHECK：high=高、medium=中、low=低，或null | Fusion confidence_label写；读者按带宽显示（S1、S2、S3、S8） |
| `confidence_rationale` | jsonb / jsonb；可NULL | 无默认 | Fusion各评分因子解释 | JSON数组约定，元素factor/label/value/weight/contribution；无JSON schema CHECK | AlertSink保存每个评分因子model_dump（S1、S2、S3） |
| `narrative` | text / text；可NULL | 无默认 | 确定性的融合关联说明 | 可空文本；可含建议但不是LLM最终调查报告 | Fusion写，旧行API详情可能懒生成并缓存（S1、S2、S3） |
| `affected_ips` | jsonb / jsonb；非NULL | `'[]'::jsonb` | 便于查询的关联IP集合 | JSON字符串数组约定，非空列默认[] | 当前本地AlertSink显式写；旧ORM注释“仅demo写”已不代表当前实现（S1、S2、S3） |
| `affected_hosts` | jsonb / jsonb；非NULL | `'[]'::jsonb` | 便于查询的关联主机集合 | JSON字符串数组约定，默认[] | 当前AlertSink _affected写；不是受害主机确认名单（S1、S2、S3） |
| `affected_users` | jsonb / jsonb；非NULL | `'[]'::jsonb` | 便于查询的关联账号集合 | JSON字符串数组约定，默认[] | 当前AlertSink _affected写；不等于处理人（S1、S2、S3） |
| `affected_assets` | jsonb / jsonb；非NULL | `'[]'::jsonb` | 关联资产的冗余集合 | JSON数组，默认[]；没有统一逐元素DB约束 | ORM字段/存量支路保留；当前Fusion主INSERT不写，不承诺已自动匹配资产（S1、S2、S3） |
| `parent_alert_id` | uuid / uuid；可NULL | 无默认 | 合并后父/保留告警标识 | 可空UUID；实际表无自FK | 合并功能使用，非Fusion Incident标识；本次未运行合并（S1、S2、S3、S9） |
| `child_alert_ids` | jsonb / jsonb；非NULL | `'[]'::jsonb` | 并入本告警的子告警ID集合 | JSON数组，默认[]；非UUID[]且无元素FK | 告警合并功能维护；不用于计算来源事件次数（S1、S2、S3、S9） |
| `is_merged` | boolean / bool；非NULL | `false` | 该告警是否作为被吸收项合并 | 布尔，默认false；不表示Fusion完成 | 合并服务配合parent_alert_id维护（S1、S2、S3、S9） |
| `assigned_to_id` | uuid / uuid；可NULL | 无默认 | 当前负责人用户ID | 可空UUID；实际目录无此列FK | PATCH/claim/release维护；姓名需人员目录（S1、S2、S3、S6） |
| `assigned_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 最近分配负责人时间 | 可空timestamptz | PATCH/claim相关路径维护；释放语义按实际路径（S1、S2、S3、S6） |
| `enrichment_data` | jsonb / jsonb；非NULL | `'{}'::jsonb` | 补充数据与Fusion交付元信息容器 | JSON对象，默认{}；本项目socai2_fusion含identity/incident_id/ioc_lookup/delivery_snapshot | AlertSink写首交付快照；扩展容器不是固定业务枚举（S1、S2、S3） |
| `tags` | jsonb / jsonb；非NULL | `'[]'::jsonb` | 当前告警标签集合 | JSON数组约定，默认[]；不等于首次来源S.tags | API人工更新/来源适配；Fusion主INSERT未同步来源tags（S1、S2、S3） |
| `idempotency_key` | text / text；可NULL | 无默认 | HTTP直接提交告警的幂等键 | 可空文本；程序入口约束长度，租户范围部分唯一索引见迁移，不是catalog.constraints中的UNIQUE | submit重试查已有行；Kafka主链按自身去重，不默认写此键（S1、S2、S3、S10） |
| `rule_id` | text / text；可NULL | 无默认 | 来源检测规则ID | 可空文本，无枚举 | Fusion/submit直接保留，不从标题解析（S1、S2、S3） |
| `rule_name` | text / text；可NULL | 无默认 | 来源检测规则名称 | 可空文本，无枚举 | Fusion保留；有rule_id不保证名称非空（S1、S2、S3） |
| `triage_groundedness` | double precision / float8；可NULL | 无默认 | 分诊理由提及的标识在输入证据中出现的比例 | 程序约定0—1；null=未评分；无DB CHECK | 分诊标识存在性校验结果投影；不是语义事实正确率（S1、S2、S3、S11、S5） |
| `triage_ungrounded` | boolean / bool；可NULL | 无默认 | 是否因标识证据不足而降级自动关闭结论 | 可空布尔：true=该门禁降级；false=未如此降级；null=未记录 | Agents persist_auto_triage写；needs_review可能有其他原因（S1、S2、S3、S11、S5） |
| `is_synthetic` | boolean / bool；非NULL | `false` | 是否被生成器标记为合成告警 | 布尔默认false；false仅表示未标记，不能单独证明真实传感器来源 | 迁移054/种子或测试生产者约定；当前raw已有告警样例即便标签synthetic也不保证自动写此列（S1、S2、S3、S12） |
| `synthetic_source` | text / text；可NULL | 无默认 | 生成合成数据的工具/来源名 | 可空自由文本；迁移例seed_demo/demo-producer/golden-pipeline只是示例 | 生成器显式填写；不从source或tags自动猜（S1、S2、S3、S12） |
| `synthetic_scenario` | text / text；可NULL | 无默认 | 合成场景标识 | 可空自由文本，无封闭枚举 | 生成器可选填写（S1、S2、S3、S12） |
| `external_id` | text / text；可NULL | 无默认 | 来源外部记录引用 | 可空文本；不等于canonical Alert ID，也不保证等于source_alert_id | Fusion直接保留来源external_id（S1、S2、S3） |
| `priority_score` | integer / int4；可NULL | 无默认 | 资产重要性/身份权限/已利用漏洞加权的上下文优先级快照栏位 | 可空整数；无DB CHECK；null=未持久评分，不等于0；不是FusedAlert浮点ML priority_score | 迁移085设计；当前processing-context动态priority不代表已写此列，主Fusion INSERT未写（S1、S2、S3、S13） |
| `priority_rationale` | jsonb / jsonb；非NULL | `'[]'::jsonb` | 上下文优先级的因子贡献快照栏位 | JSON数组默认[]；逐元素无数据库约束 | 迁移085设计；不可把动态processing-context.rationale当本列已持久（S1、S2、S3、S13） |
| `session_id` | uuid / uuid；可NULL | 无默认 | 来源会话/凭据/流分组ID | 可空UUID；实际FK sessions.id删除置空 | Fusion会话支路确定后随AlertSink写；无上下文保持null（S1、S2、S3、S14、S15） |
| `session_key_kind` | text / text；可NULL | 无默认 | 会话键依据类型的冗余副本 | 本表无CHECK；Session消费程序集合vendor_session=厂商会话、vendor_credential=厂商凭据、vendor_flow=厂商流、derived=推导分组 | Fusion KEY_KINDS校验后写；derived不等于已验证真实会话（S1、S2、S3、S14、S15） |
| `originating_human` | text / text；可NULL | 无默认 | 会话上下文所报告的发起人 | 可空字符串，不是users.id或负责人FK | Fusion会话上下文复制；无上游依据不补造（S1、S2、S3、S14、S15） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `ck_alerts_confidence_label_enum`：`CHECK (((confidence_label IS NULL) OR (confidence_label = ANY (ARRAY['high'::text, 'medium'::text, 'low'::text]))))`
- `ck_alerts_confidence_range`：`CHECK (((confidence IS NULL) OR ((confidence >= 0) AND (confidence <= 100))))`
- `alerts_session_id_fkey`：`FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL`
- `alerts_snoozed_by_id_fkey`：`FOREIGN KEY (snoozed_by_id) REFERENCES users(id) ON DELETE SET NULL`
- `alerts_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `alerts_pkey`：`PRIMARY KEY (id)`

**字段解释依据**：

- S1：[ services/api/app/models/alert.py ](../../../services/api/app/models/alert.py)
- S2：[ services/fusion/app/services/alert_sink.py ](../../../services/fusion/app/services/alert_sink.py)
- S3：[ services/api/app/api/v1/endpoints/alerts.py ](../../../services/api/app/api/v1/endpoints/alerts.py)
- S4：[ services/api/app/services/alert_status.py ](../../../services/api/app/services/alert_status.py)
- S5：[ services/agents/app/investigator/ledger.py ](../../../services/agents/app/investigator/ledger.py)
- S6：[ services/api/app/services/alert_queue.py ](../../../services/api/app/services/alert_queue.py)
- S7：[ services/api/app/api/v1/endpoints/feedback.py ](../../../services/api/app/api/v1/endpoints/feedback.py)
- S8：[ services/api/migrations/040_critical_severity_alert_confidence.sql ](../../../services/api/migrations/040_critical_severity_alert_confidence.sql)
- S9：[ services/api/app/services/case_depth.py ](../../../services/api/app/services/case_depth.py)
- S10：[ services/api/migrations/044_alerts_idempotency_key.sql ](../../../services/api/migrations/044_alerts_idempotency_key.sql)
- S11：[ services/api/migrations/051_triage_groundedness.sql ](../../../services/api/migrations/051_triage_groundedness.sql)
- S12：[ services/api/migrations/054_alert_provenance.sql ](../../../services/api/migrations/054_alert_provenance.sql)
- S13：[ services/api/migrations/085_asset_context_scoring.sql ](../../../services/api/migrations/085_asset_context_scoring.sql)
- S14：[ services/api/migrations/102_sessions.sql ](../../../services/api/migrations/102_sessions.sql)
- S15：[ services/fusion/app/services/sessions.py ](../../../services/fusion/app/services/sessions.py)

<a id="aisoc_cases"></a>

### 3.2 `aisoc_cases`

人工案件容器：成员告警、人工状态/协作、SLA和关案资料；不能用它承载不存在的自动Case。

关联与边界：alert_ids为UUID[]逻辑成员无元素FK；实际tenant_id可空且目录无FK。queue/policy/merged_into有实际FK。tags当前API为对象，不能套Alert标签数组。

字段数 **48**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `gen_random_uuid()` | 人工案件容器ID | UUID主键 | Case API生成；不同于Fusion Incident或Run（S1、S2、S3、S4） |
| `tenant_id` | uuid / uuid；可NULL | 无默认 | 案件所属租户 | 实际DB可空UUID且此目录无tenant FK；API/ORM通常要求当前租户 | 必须按实际表可空记录，不能把ORM nullable=False误写成DB约束（S1、S2、S3、S4） |
| `title` | text / text；非NULL | 无默认 | 案件标题 | 非空TEXT；创建API min_length=3，DB无该长度CHECK | Create/Update Case写（S1、S2、S3、S4） |
| `description` | text / text；可NULL | 无默认 | 案件描述 | 可空TEXT | Case API写；不是自动最终调查报告（S1、S2、S3、S4） |
| `severity` | text / text；非NULL | `'medium'::text` | 案件严重程度 | DB CHECK及API集合info=信息、low=低、medium=中、high=高、critical=严重 | Case API/战情室升级写；默认medium（S1、S2、S3、S4） |
| `status` | text / text；非NULL | `'new'::text` | 案件业务生命周期状态 | DB CHECK：new=新建、triaged=已分诊、investigating=调查中、contained=已控制、resolved=已解决待关案、closed=已关案 | API常规只允许状态图前向边，reopen另入口；API接收旧别名后先归一化，见status_contract（S1、S2、S3、S4、S5） |
| `assignee` | text / text；可NULL | 无默认 | 案件负责人文本标识 | 可空TEXT；API自由字符串，不保证UUID或姓名 | Case API主要读写此列；不自动与assigned_to_id保持一致（S1、S2、S3、S4） |
| `mitre_techniques` | jsonb / jsonb；可NULL | `'[]'::jsonb` | 案件关联MITRE技术 | JSON数组约定，默认[] | Case API接受list[str]；技术标签不是证实攻击链（S1、S2、S3、S4） |
| `alert_ids` | ARRAY / _uuid；可NULL | `ARRAY[]::uuid[]` | 案件成员告警ID | PostgreSQL UUID[]数组，默认空；不是JSONB；没有数组元素FK | Create/Add Alerts/合并维护，按同tenant校验成员（S1、S2、S3、S4） |
| `observable_graph` | jsonb / jsonb；可NULL | `'{}'::jsonb` | 案件人工可观测对象图 | JSON对象，常用nodes/edges；节点API kind集合ip=IP、user=账号、host=主机、domain=域名、hash=哈希、file=文件、process=进程、alert=告警 | POST observables合并节点/边；不是Neo4j当前图或Run的alert_graph同一存储（S1、S2、S3、S4） |
| `evidence_chain` | jsonb / jsonb；可NULL | `'[]'::jsonb` | 案件材料处理/保管的审计链 | JSON数组；条目含action/actor/时间/前后hash等按custody合同 | _append_custody尽力追加；不等于逐结论证据支持关系，也不能承诺失败永不缺记录（S1、S2、S3、S4） |
| `compliance_frameworks` | ARRAY / _text；可NULL | `ARRAY[]::text[]` | 案件适用的合规框架代码 | PostgreSQL TEXT[]；API list[str]；无统一DB枚举 | Case API写，实际值依业务标注（S1、S2、S3、S4） |
| `opened_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 案件开立时间 | 非空timestamptz默认now() | 创建Case写；不是Run开始时间（S1、S2、S3、S4） |
| `triaged_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 案件进入分诊完成状态的记录时间 | 可空timestamptz | 状态转换路径维护；需按实际记录而非从Run推断（S1、S2、S3、S4） |
| `resolved_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 案件进入已解决状态的时间 | 可空timestamptz | Case状态转换写；resolved仍可能待关案（S1、S2、S3、S4） |
| `closed_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 案件最终关案时间 | 可空timestamptz | 进入closed/合并被吸收案件等写；与resolved_at分开（S1、S2、S3、S4） |
| `created_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 案件记录创建时间 | 非空timestamptz默认now() | 创建写；不等于源告警发生时间（S1、S2、S3、S4） |
| `updated_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 案件记录最近修改时间 | 非空timestamptz默认now() | Case API各更新路径维护；不是完整审计历史（S1、S2、S3、S4） |
| `created_by` | text / text；可NULL | 无默认 | 案件创建者文本标识 | 可空TEXT，当前API可写邮箱/调用主体字符串 | 与created_by_id分开，不自动等同UUID（S1、S2、S3、S4） |
| `tags` | jsonb / jsonb；可NULL | `'{}'::jsonb` | 案件标签/元数据 | JSONB，实际DB默认{}；当前Case API为dict[str,str]，ORM旧mapped list存在形状差异 | 以当前Case API/实际正文解释，不套Alert tags数组（S1、S2、S3、S4） |
| `sla_due_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 旧/基础SLA到期时间 | 可空timestamptz | Create/Update API显式接受；与sla_deadline、ack_due_at、resolve_due_at不自动等价（S1、S2、S3、S4） |
| `case_number` | text / text；可NULL | 无默认 | 供人员引用的案件编号 | 可空TEXT，实际目录无UNIQUE约束；迁移另有索引时需单独核 | Case创建使用编号生成；不能用ORM非空/unique声明覆盖实表约束（S1、S2、S3、S4） |
| `priority` | text / text；可NULL | 无默认 | 案件优先级文本 | 可空TEXT；ORM默认medium为应用默认非DB默认；无实际DB枚举CHECK | 旧ORM/已有业务路径使用；不等于Alert priority整数（S1、S2、S3、S4） |
| `case_type` | text / text；可NULL | 无默认 | 案件业务类型 | 可空TEXT；ORM默认security_incident=安全事件为程序默认/例，不是封闭枚举 | 队列规则可按case_type匹配，当前CreateCaseRequest不暴露此项（S1、S2、S3、S4） |
| `mitre_tactics` | jsonb / jsonb；非NULL | `'[]'::jsonb` | 案件关联MITRE战术 | JSON数组约定，非空默认[] | ORM/迁移保留；当前主要Case API技术列表与此列不等价（S1、S2、S3、S4） |
| `assigned_to_id` | uuid / uuid；可NULL | 无默认 | 案件负责人用户UUID栏位 | 可空UUID；实际目录无users FK | ORM/迁移字段；主要Case API assignee是独立文本列，不承诺同步（S1、S2、S3、S4） |
| `assigned_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | UUID负责人分配时间 | 可空timestamptz | ORM/已有路径字段；不从assignee文本更新时间自行推造（S1、S2、S3、S4） |
| `created_by_id` | uuid / uuid；可NULL | 无默认 | 案件创建者用户UUID栏位 | 可空UUID；无目录内FK | ORM/迁移字段，与created_by文本分开（S1、S2、S3、S4） |
| `sla_deadline` | timestamp with time zone / timestamptz；可NULL | 无默认 | 旧ORM的SLA截止时间栏位 | 可空timestamptz | 保留历史结构，不能当作sla_due_at的数据库别名；本次未确认统一写入（S1、S2、S3、S4） |
| `sla_breached` | boolean / bool；非NULL | `false` | SLA违反标记栏位 | 布尔默认false；不是根据当前时间自动变化的生成列 | ORM/相关业务路径使用；未被计算/更新时false不能证明未超时（S1、S2、S3、S4） |
| `ioc_ids` | jsonb / jsonb；非NULL | `'[]'::jsonb` | 案件关联IOC标识集合 | JSON数组默认[]，无元素FK | ORM/迁移保留；不等于observable_graph内所有IOC（S1、S2、S3、S4） |
| `artifact_ids` | jsonb / jsonb；非NULL | `'[]'::jsonb` | 案件关联材料ID集合 | JSON数组默认[]，无元素FK | ORM/迁移保留；不等于每个Run所有工件自动汇总（S1、S2、S3、S4） |
| `ticket_refs` | jsonb / jsonb；非NULL | `'[]'::jsonb` | 旧案件外部工单引用集合 | JSON数组默认[] | ORM字段；现ITSM关联主要另表case_external_refs，不能假设双向同步（S1、S2、S3、S4、S6） |
| `summary` | text / text；可NULL | 无默认 | 案件摘要文本栏位 | 可空TEXT | ORM/既有人工业务路径；无统一自动调查总结写入保证（S1、S2、S3、S4） |
| `resolution` | text / text；可NULL | 无默认 | 案件解决/关案说明 | 可空TEXT | ORM/合并等路径可写；非Run verdict（S1、S2、S3、S4） |
| `lessons_learned` | text / text；可NULL | 无默认 | 案件复盘经验文本 | 可空TEXT | ORM/存量业务设计保留，不保证反馈/知识自动同步（S1、S2、S3、S4） |
| `queue_id` | uuid / uuid；可NULL | 无默认 | 案件队列关联 | 可空UUID；实际FK case_queues.id删除置空 | 迁移086；业务队列解析函数可能动态选队列，不能仅凭函数返回断言该列已持久（S1、S2、S3、S4、S7、S8） |
| `sla_policy_id` | uuid / uuid；可NULL | 无默认 | 应用于案件的SLA策略关联 | 可空UUID；实际FK case_sla_policies.id删除置空 | 迁移086/编排规则设计；本次未声称当前案件实际挂策略（S1、S2、S3、S4、S7、S8） |
| `ack_due_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 首次确认的SLA截止时间 | 可空timestamptz | case_orchestration计算ack目标；列存在不保证已持久该目标（S1、S2、S3、S4、S7、S8） |
| `resolve_due_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 解决案件的SLA截止时间 | 可空timestamptz | case_orchestration计算resolve目标；与关案/ack期限分开（S1、S2、S3、S4、S7、S8） |
| `acknowledged_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 案件首次被确认接手时间 | 可空timestamptz | war_room acknowledge以COALESCE保留首次；不是Alert.first_seen_at（S1、S2、S3、S4、S7、S9） |
| `escalation_level` | integer / int4；非NULL | `0` | 案件升级层级/升级次数记录 | 整数默认0，无DB范围CHECK | war_room escalate将级别+1并升critical；不等于severity字符串（S1、S2、S3、S4、S7、S9） |
| `reopened_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 最近一次重新打开的时间 | 可空timestamptz；null表示未记录重开 | 明确reopen接口写；不能用普通PATCH逆向改变历史（S1、S2、S3、S4、S10） |
| `reopen_count` | integer / int4；非NULL | `0` | 已记录的重开次数 | 整数默认0；只统计此字段存在后记录 | reopen接口递增；不是历史事实绝对全量（S1、S2、S3、S4、S10） |
| `reopen_reason` | text / text；可NULL | 无默认 | 最近一次重开的理由 | 可空TEXT；reopen API要求理由，DB不强制非空 | 重开时写；历史null不补造（S1、S2、S3、S4、S10） |
| `merged_into_id` | uuid / uuid；可NULL | 无默认 | 本案件被并入的保留案件ID | 可空UUID；实际自FK aisoc_cases.id删除置空 | case_depth合并保留两条记录并关闭被吸收项；不是删除被合并案件（S1、S2、S3、S4、S11） |
| `merged_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 案件被合并时间 | 可空timestamptz | case_depth merge写；不同于updated_at/closed_at（S1、S2、S3、S4、S11） |
| `merged_by` | text / text；可NULL | 无默认 | 执行案件合并的主体文本 | 可空TEXT，无人员FK | case_depth merge记录actor；不强制是用户UUID（S1、S2、S3、S4、S11） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `aisoc_cases_severity_check`：`CHECK ((severity = ANY (ARRAY['info'::text, 'low'::text, 'medium'::text, 'high'::text, 'critical'::text])))`
- `aisoc_cases_status_check`：`CHECK ((status = ANY (ARRAY['new'::text, 'triaged'::text, 'investigating'::text, 'contained'::text, 'resolved'::text, 'closed'::text])))`
- `aisoc_cases_merged_into_id_fkey`：`FOREIGN KEY (merged_into_id) REFERENCES aisoc_cases(id) ON DELETE SET NULL`
- `aisoc_cases_queue_id_fkey`：`FOREIGN KEY (queue_id) REFERENCES case_queues(id) ON DELETE SET NULL`
- `aisoc_cases_sla_policy_id_fkey`：`FOREIGN KEY (sla_policy_id) REFERENCES case_sla_policies(id) ON DELETE SET NULL`
- `aisoc_cases_pkey`：`PRIMARY KEY (id)`

**字段解释依据**：

- S1：[ services/api/migrations/012_case_management.sql ](../../../services/api/migrations/012_case_management.sql)
- S2：[ services/api/migrations/083_one_case_table.sql ](../../../services/api/migrations/083_one_case_table.sql)
- S3：[ services/api/app/models/case.py ](../../../services/api/app/models/case.py)
- S4：[ services/api/app/api/v1/endpoints/cases.py ](../../../services/api/app/api/v1/endpoints/cases.py)
- S5：[ services/api/app/services/case_status.py ](../../../services/api/app/services/case_status.py)
- S6：[ services/api/migrations/035_case_external_refs.sql ](../../../services/api/migrations/035_case_external_refs.sql)
- S7：[ services/api/migrations/086_case_orchestration.sql ](../../../services/api/migrations/086_case_orchestration.sql)
- S8：[ services/api/app/services/case_orchestration.py ](../../../services/api/app/services/case_orchestration.py)
- S9：[ services/api/app/services/war_room.py ](../../../services/api/app/services/war_room.py)
- S10：[ services/api/migrations/090_case_reopen.sql ](../../../services/api/migrations/090_case_reopen.sql)
- S11：[ services/api/app/services/case_depth.py ](../../../services/api/app/services/case_depth.py)

<a id="investigation_runs"></a>

### 3.3 `investigation_runs`

一次分诊或调查执行的生命周期和用量表，不等于一次完整安全事件或Case。

关联与边界：tenant_id→tenants为FK；case_id是varchar目标，无Case FK。events/artifacts按run_id关联；成本表用TEXT run_id/tenant_id。

字段数 **18**；2026-10-22 22:56样例租户行数 **3**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `uuid_generate_v4()` | 一次分诊/调查执行的Run标识 | UUID主键 | ledger start_run或自动入口认领时产生（S1、S2、S3、S4） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | Run所属租户 | UUID；FK tenants.id级联删除 | ledger绑定租户；所有结果关联同tenant（S1、S2、S3、S4） |
| `case_id` | character varying / varchar；非NULL | 无默认 | 历史命名的运行目标字符串 | 非空varchar；无Case外键；可能为Alert UUID文本、Case UUID文本或Fusion Incident/其他已知目标 | 人工Case传Case ID；自动Kafka传Alert ID；必须按入口/快照验证目标类型（S1、S2、S3、S4） |
| `alert_summary` | text / text；可NULL | 无默认 | 该次运行收到的告警/目标摘要 | 可空文本；不是当前Alert.description的自动更新副本 | 启动入口冻结输入摘要；可包含融合说明（S1、S2、S3、S4） |
| `raw_alert` | jsonb / jsonb；可NULL | 无默认 | 启动输入的告警材料快照 | 可空JSON对象约定；不同入口形状不同 | start_run/自动分诊记录来源正文；不是最终调查结果（S1、S2、S3、S4） |
| `model_used` | character varying / varchar；可NULL | 无默认 | 入口/模型选型的字符串记录 | 自由字符串；例如kafka:auto_triage:claimed=认领、kafka:auto_triage:llm=模型分诊路径，均为程序例非真实模型ID | 启动/自动分诊更新；真实模型解析名读成本行resolved_model（S1、S2、S3、S4） |
| `status` | character varying / varchar；非NULL | `'running'::character varying` | 程序运行生命周期状态 | 无DB CHECK；ledger主要约定running=运行中、completed=执行结束、failed=执行失败；不是调查业务完成度 | complete_run等写；completed仍可能GE.completion=partial（S1、S2、S3、S4） |
| `error` | text / text；可NULL | 无默认 | Run执行错误文本 | 可空文本；null不表示调查完整或无工具错误 | 失败/结束路径写；部分错误可在graph结果内而本列null（S1、S2、S3、S4） |
| `total_tokens` | integer / int4；非NULL | `0` | 该Run记录的模型输入输出token总和 | 整数默认0，无DB非负CHECK；未知用量不能因0当零消耗 | 分诊和后续graph用量合并；不以Deep自有tokens字段替代（S1、S2、S3、S4） |
| `total_cost_usd` | numeric / numeric；非NULL | `0` | Run网关已测量费用累计 | numeric；仅measured_call_count>0时有测量意义；旧迁移前值可能为估算遗留 | 063后complete_run只写measured；不能加估算或把0当免费（S1、S2、S3、S4、S5） |
| `iterations` | integer / int4；非NULL | `0` | Run入口定义的迭代/步骤计数 | 整数默认0，无DB范围CHECK；不是统一模型调用数或Deep推理轮数 | 自动分诊、graph、人工路径传入各自iterations；具体Deep读G.investigation_depth.iterations（S1、S2、S3、S4） |
| `started_at` | timestamp with time zone / timestamptz；非NULL | `now()` | Run执行启动时间 | 非空timestamptz默认now() | 认领/启动写；自动Run包含首次分诊（S1、S2、S3、S4） |
| `completed_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | Run终态记录时间 | 可空timestamptz；运行中通常null | complete_run/自动分诊完成更新；不能用G.completed_at替代（S1、S2、S3、S4） |
| `created_at` | timestamp with time zone / timestamptz；非NULL | `now()` | Run数据库记录创建时间 | 非空timestamptz默认now() | 首次INSERT生成；与started_at语义分开（S1、S2、S3、S4） |
| `measured_call_count` | integer / int4；非NULL | `0` | 费用由网关报告的调用数 | 整数默认0；0=无测量，不等于已测0美元 | 成本追踪及Run聚合写；与total_cost_usd联合读取（S1、S2、S3、S4、S5） |
| `estimated_cost_usd` | numeric / numeric；非NULL | `0` | 未获网关计价、按具体模型公开价格估算的费用和 | numeric；仅estimated_call_count>0时为有效估计；与实测分开 | 063后成本汇总写；标注估算（S1、S2、S3、S4、S5） |
| `estimated_call_count` | integer / int4；非NULL | `0` | 被公开价格估算的调用数 | 整数默认0 | 成本追踪按每次唯一provenance分类累计（S1、S2、S3、S4、S5） |
| `unpriced_call_count` | integer / int4；非NULL | `0` | 既无网关费用也无可用估价的调用数 | 整数默认0；大于0表示费用不完整 | 成本追踪累计；不是失败次数（S1、S2、S3、S4、S5） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `investigation_runs_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `investigation_runs_pkey`：`PRIMARY KEY (id)`

**字段解释依据**：

- S1：[ services/api/migrations/008_investigation_ledger.sql ](../../../services/api/migrations/008_investigation_ledger.sql)
- S2：[ services/api/app/models/investigation.py ](../../../services/api/app/models/investigation.py)
- S3：[ services/agents/app/investigator/ledger.py ](../../../services/agents/app/investigator/ledger.py)
- S4：[ services/agents/app/graph/runner.py ](../../../services/agents/app/graph/runner.py)
- S5：[ services/api/migrations/063_cost_provenance.sql ](../../../services/api/migrations/063_cost_provenance.sql)

<a id="investigation_events"></a>

### 3.4 `investigation_events`

按执行步骤留存的事件账本。kind不同，payload合同不同。

关联与边界：run_id与tenant_id各自FK；UNIQUE(run_id,seq)。seq分区不保证时间单调；工件event_id可关联本表，不能视为结论支持关系。

字段数 **13**；2026-10-22 22:56样例租户行数 **36**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `uuid_generate_v4()` | 单条处理事件ID | UUID主键 | ledger生成，用于工件关联与读取去重（S1、S2、S3） |
| `run_id` | uuid / uuid；非NULL | 无默认 | 所属Run标识 | UUID；FK investigation_runs.id级联删除 | 所有事件绑定一个Run（S1、S2、S3） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 事件所属租户 | UUID；FK tenants.id级联删除 | 写入与读取租户范围；不得只凭seq串Run（S1、S2、S3） |
| `seq` | integer / int4；非NULL | 无默认 | Run内部写入方分配的序号 | 整数；DB UNIQUE(run_id,seq)；可负数；不是全局单调时间游标 | 自动认领-1、分诊0/1、graph低序号、工具10000+等为程序约定；冲突不覆盖（S1、S2、S3） |
| `ts` | timestamp with time zone / timestamptz；非NULL | `now()` | 事件业务处理/记录时间 | 非空timestamptz默认now() | record_event可传timestamp；工具旧版多为批量留存时间，不是来源事件发生时间（S1、S2、S3） |
| `kind` | character varying / varchar；非NULL | 无默认 | 事件类别 | 自由varchar无DB CHECK；StepKind枚举只覆盖一部分，另有triage_started/triage_verdict/graph_step/graph_result/graph_usage等程序类别 | 按kind解释payload；常用值中文说明见json_contracts.event_kinds，非完整封闭集合（S1、S2、S3） |
| `agent` | character varying / varchar；非NULL | 无默认 | 产生事件的角色/执行者标识 | 自由varchar；例如auto_triage、deep-investigator及graph节点角色，不是人员姓名枚举 | 事件生产者写；不代表一定调用模型（S1、S2、S3） |
| `summary` | text / text；非NULL | 无默认 | 该步骤简述 | 非空文本；record_event截取8000字符 | ledger写，摘要不是完整工具结果或证据结论（S1、S2、S3） |
| `payload` | jsonb / jsonb；可NULL | 无默认 | 事件类别专有的结构化详情 | 可空JSONB；必须按kind/schema_version解释，无统一全字段schema | triage结果/graph完成度/工具参数/用量等；具体常用键见json_contracts（S1、S2、S3） |
| `input_hash` | character varying / varchar；可NULL | 无默认 | 步骤输入序列化内容摘要 | 可空字符串，程序多用64字符SHA256；无DB格式CHECK | 按各writer被哈希对象解释；可能针对截断前输入，不能反推全文可取（S1、S2、S3） |
| `output_hash` | character varying / varchar；可NULL | 无默认 | 步骤输出序列化内容摘要 | 可空字符串，程序多用SHA256 | 新工具事件hash为保留result_text，模型hash按交换记录；不同于工件整体sha256（S1、S2、S3） |
| `duration_ms` | integer / int4；非NULL | `0` | 写入方提供的步骤耗时毫秒 | 整数默认0，无DB非负CHECK；旧工具0可表示未传测量值 | 新工具有单次计时，graph节点/LLM按对应计时；需版本语义不能统一0=瞬时成功（S1、S2、S3） |
| `created_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 事件行落库时间 | 非空timestamptz默认now() | INSERT生成；可与ts不同（S1、S2、S3） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `investigation_events_run_id_fkey`：`FOREIGN KEY (run_id) REFERENCES investigation_runs(id) ON DELETE CASCADE`
- `investigation_events_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `investigation_events_pkey`：`PRIMARY KEY (id)`
- `investigation_events_run_id_seq_key`：`UNIQUE (run_id, seq)`

**字段解释依据**：

- S1：[ services/api/migrations/008_investigation_ledger.sql ](../../../services/api/migrations/008_investigation_ledger.sql)
- S2：[ services/agents/app/investigator/ledger.py ](../../../services/agents/app/investigator/ledger.py)
- S3：[ services/agents/app/investigator/state.py ](../../../services/agents/app/investigator/state.py)

<a id="investigation_artifacts"></a>

### 3.5 `investigation_artifacts`

按Run/步骤保存较大的结果文本、模型交换、图快照和报告。

关联与边界：run/tenant/event各有FK但不是复合跨租户约束；event_id可空。同Run同kind可多份，固定artifact_id读取，不跨Run拼结果。

字段数 **10**；2026-10-22 22:56样例租户行数 **35**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `uuid_generate_v4()` | 一份留存材料的唯一标识 | UUID主键 | ledger新建；回看版本固定此ID（S1、S2、S3） |
| `run_id` | uuid / uuid；非NULL | 无默认 | 材料所属Run | UUID；FK investigation_runs.id级联删除 | 读取必须按tenant/run/artifact共同绑定（S1、S2、S3） |
| `event_id` | uuid / uuid；可NULL | 无默认 | 可选的关联处理事件 | 可空UUID；FK investigation_events.id级联删除 | 仅建立步骤关联，不能直接视为该材料支持某项结论（S1、S2、S3） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 材料所属租户 | UUID；FK tenants.id级联删除 | 与Run/事件同租户；外键单独存在不等于复合跨租户约束（S1、S2、S3） |
| `kind` | character varying / varchar；非NULL | 无默认 | 材料类型 | 自由varchar无DB CHECK；常用graph_result/report_md/llm_prompt/llm_response/graph_llm_exchanges/*_read/链图/tool_result等，不是完整枚举 | 按kind决定content解析方式；tool_result为本地新版未部署（S1、S2、S3） |
| `content` | text / text；可NULL | 无默认 | 内联留存正文 | 可空TEXT；JSON工件需解析文本、Markdown直接读取；有界保留不是外部原始全量备份 | ledger保存实际字符串；有blob_ref而content空不能直接称无报告（S1、S2、S3） |
| `blob_ref` | text / text；可NULL | 无默认 | 可选外置对象引用 | 可空文本；URI/键格式随存储实现，未确认统一协议或已启用外置读取 | 接口可返回引用；不能承诺仅有引用就能下载正文（S1、S2、S3） |
| `sha256` | character varying / varchar；非NULL | 无默认 | 材料保存正文/字节的SHA256 | 非空字符串；程序64位小写hex惯例，DB无长度或hex CHECK | 内联工件对UTF-8 content计算；不证明分析真实或未截断（S1、S2、S3） |
| `size_bytes` | integer / int4；非NULL | `0` | 材料保存内容的字节大小 | 整数默认0；程序内联按UTF-8 bytes计 | 不是字符数；tool_result内部result_size_bytes可能指截断前外部序列化结果，两者不同（S1、S2、S3） |
| `created_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 此材料记录的生成/保存时间 | 非空timestamptz默认now() | 版本定位时间；不是来源行为发生时间（S1、S2、S3） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `investigation_artifacts_event_id_fkey`：`FOREIGN KEY (event_id) REFERENCES investigation_events(id) ON DELETE CASCADE`
- `investigation_artifacts_run_id_fkey`：`FOREIGN KEY (run_id) REFERENCES investigation_runs(id) ON DELETE CASCADE`
- `investigation_artifacts_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `investigation_artifacts_pkey`：`PRIMARY KEY (id)`

**字段解释依据**：

- S1：[ services/api/migrations/008_investigation_ledger.sql ](../../../services/api/migrations/008_investigation_ledger.sql)
- S2：[ services/agents/app/investigator/ledger.py ](../../../services/agents/app/investigator/ledger.py)
- S3：[ services/api/app/api/v1/endpoints/investigations.py ](../../../services/api/app/api/v1/endpoints/investigations.py)

<a id="aisoc_run_costs"></a>

### 3.6 `aisoc_run_costs`

按(run_id,tenant_id,请求模型)累计的成本/调用遥测，不是一调用一行。

关联与边界：三列TEXT组成PK，无Run/tenant FK；需显式租户与字符串转型关联。实测/估算/未计价按来源分开。

字段数 **15**；2026-10-22 22:56样例租户行数 **5**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `run_id` | text / text；非NULL | 无默认 | 费用聚合所属Run目标 | TEXT；无FK；通常UUID文本 | CostTracker写；关联investigation_runs需r.id::text，不能假设费用行必有Run（S1、S2、S3） |
| `tenant_id` | text / text；非NULL | 无默认 | 费用记录租户 | TEXT；无FK | 成本追踪上下文写；与UUID tenant关联时需显式转换及租户过滤（S1、S2、S3） |
| `model` | text / text；非NULL | 无默认 | 本次请求所用模型别名/标识，聚合维度 | TEXT；与run_id/tenant_id组成复合主键；无枚举 | 按请求别名聚合，如aisoc-triage/aisoc-investigation；不等于解析后的真实模型（S1、S2、S3） |
| `total_prompt_tokens` | integer / int4；非NULL | `0` | 此Run此模型行累计输入token | 整数默认0 | _flush_to_db按记录累加；不是单次调用输入量（S1、S2、S3） |
| `total_completion_tokens` | integer / int4；非NULL | `0` | 此Run此模型行累计输出token | 整数默认0 | _flush_to_db累加；总token等于两列之和（S1、S2、S3） |
| `total_cost_usd` | double precision / float8；非NULL | `0` | 兼容旧读者保留的实测费用累计列 | float8；063后measured-only；历史值未经测量计数不能认实测 | writer与measured_cost_usd写同一实测和；勿将两列相加（S1、S2、S3） |
| `total_latency_ms` | double precision / float8；非NULL | `0` | 此Run此模型各调用延迟之和 | float8毫秒；可含小数；不是Run壁钟耗时 | CostTracker按调用累计；并发/外围阶段使其不同于结束减开始（S1、S2、S3） |
| `call_count` | integer / int4；非NULL | `0` | 此模型聚合行记录的调用次数 | 整数默认0；不保证覆盖没有回执/未计量的未知请求 | CostTracker记录数累加；Run总调用数对各模型行求和（S1、S2、S3） |
| `recorded_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 此聚合行最近写入时间 | timestamptz默认now()，upsert更新now() | 不是首个/最后一个模型实际调用精确时间（S1、S2、S3） |
| `measured_cost_usd` | double precision / float8；非NULL | `0` | 网关明确返回的费用累计 | float8；有效性同时看measured_call_count | 当前writer写网关实测和；0且计数>0才表示测得零（S1、S2、S3） |
| `measured_call_count` | integer / int4；非NULL | `0` | 计入实测费用的调用次数 | 整数默认0 | measured来源计数，与估算/未计价按调用互斥（S1、S2、S3） |
| `estimated_cost_usd` | double precision / float8；非NULL | `0` | 按具体已解析模型价格估算的费用和 | float8；仅估计，不计入measured和 | 没有网关报价但可识别具体模型价目时写（S1、S2、S3） |
| `estimated_call_count` | integer / int4；非NULL | `0` | 计入估算费用的调用数 | 整数默认0 | 成本来源estimated累计（S1、S2、S3） |
| `unpriced_call_count` | integer / int4；非NULL | `0` | 未能计价的调用数 | 整数默认0 | 既无实测又无估价时计入；不表示免费或失败（S1、S2、S3） |
| `resolved_model` | text / text；可NULL | 无默认 | 网关返回的具体模型标识 | 可空TEXT；非枚举 | 聚合时保留非空解析模型；一行可能多个调用，不能据一个字符串承诺逐调用模型未切换（S1、S2、S3） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `aisoc_run_costs_pkey`：`PRIMARY KEY (run_id, tenant_id, model)`

**字段解释依据**：

- S1：[ services/api/migrations/020_soc_metrics_h2.sql ](../../../services/api/migrations/020_soc_metrics_h2.sql)
- S2：[ services/api/migrations/063_cost_provenance.sql ](../../../services/api/migrations/063_cost_provenance.sql)
- S3：[ services/agents/app/core/cost_telemetry.py ](../../../services/agents/app/core/cost_telemetry.py)

<a id="tenants"></a>

### 3.7 `tenants`

租户隔离、套餐与配置根表；租户层级为自关联。catalog中本生产租户1行，其余租户不在本字典数据观察范围。

字段数 **15**；2026-10-22 22:56样例租户行数 **1**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `uuid_generate_v4()` | 租户内部主键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | Tenant ORM、bootstrap/租户开通服务写基础资料；开通来源两列另用SQL同步。治理驻留两列只确认DDL与服务纯函数，未核通用DB写入口。（S1、S2、S3、S4） |
| `name` | character varying / varchar；非NULL | 无默认 | 租户显示名称；开通服务采用申请企业名。 | VARCHAR自由文本；catalog未记录字符长度；无已确认封闭枚举。 | Tenant ORM、bootstrap/租户开通服务写基础资料；开通来源两列另用SQL同步。治理驻留两列只确认DDL与服务纯函数，未核通用DB写入口。（S1、S2、S3、S4） |
| `slug` | character varying / varchar；非NULL | 无默认 | 租户可读短标识，数据库全表唯一；开通服务分配避免冲突。 | 自由VARCHAR；数据库UNIQUE；开通路径按企业名分配短标识。catalog未记录varchar长度，不据ORM长度冒充实库长度。 | Tenant ORM、bootstrap/租户开通服务写基础资料；开通来源两列另用SQL同步。治理驻留两列只确认DDL与服务纯函数，未核通用DB写入口。（S1、S2、S3、S4） |
| `plan` | character varying / varchar；可NULL | `'starter'::character varying` | 套餐/服务方案标签，非数据库枚举；开通流程可写 managed-beta。 | 自由VARCHAR，无DB CHECK。已核默认starter=入门套餐、初始化示例enterprise=企业套餐、开通writer managed-beta=托管试用；这是已见值示例，非完整支持套餐枚举。 | Tenant ORM、bootstrap/租户开通服务写基础资料；开通来源两列另用SQL同步。治理驻留两列只确认DDL与服务纯函数，未核通用DB写入口。（S1、S2、S3、S4） |
| `is_active` | boolean / bool；可NULL | `true` | 租户是否启用。 | BOOLEAN：true=是/启用该标记，false=否/未启用；具体业务含义见本列说明。 | Tenant ORM、bootstrap/租户开通服务写基础资料；开通来源两列另用SQL同步。治理驻留两列只确认DDL与服务纯函数，未核通用DB写入口。（S1、S2、S3、S4） |
| `settings` | jsonb / jsonb；可NULL | `'{}'::jsonb` | 租户设置对象；开通与设置接口写入，键由各功能约定。 | JSON对象，开放键。已核开通键managed、branding、aisoc_credential_key_fingerprint、rbac_seed_roles、starter_detections、starter_playbooks、provisioned_from_waitlist_id、provisioned_at；只保存凭据指纹而非明文。PATCH /tenants/me/settings接受dict。 | Tenant ORM、bootstrap/租户开通服务写基础资料；开通来源两列另用SQL同步。治理驻留两列只确认DDL与服务纯函数，未核通用DB写入口。（S1、S2、S3、S4） |
| `limits` | jsonb / jsonb；可NULL | `'{}'::jsonb` | 租户资源/功能限额对象，不等于每个键均已强制执行。 | JSON对象，开放键。已核开通写alerts_per_day=50000、investigations_in_flight=25、managed_offering=true；这些只是该开通路径示例，不是固定DB默认及完整限额合同。 | Tenant ORM、bootstrap/租户开通服务写基础资料；开通来源两列另用SQL同步。治理驻留两列只确认DDL与服务纯函数，未核通用DB写入口。（S1、S2、S3、S4） |
| `created_at` | timestamp with time zone / timestamptz；可NULL | `now()` | 租户记录创建时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | Tenant ORM、bootstrap/租户开通服务写基础资料；开通来源两列另用SQL同步。治理驻留两列只确认DDL与服务纯函数，未核通用DB写入口。（S1、S2、S3、S4） |
| `updated_at` | timestamp with time zone / timestamptz；可NULL | `now()` | 租户记录最近更新时点；ORM更新时写，不可仅凭DB默认推定所有外部SQL自动维护。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | Tenant ORM、bootstrap/租户开通服务写基础资料；开通来源两列另用SQL同步。治理驻留两列只确认DDL与服务纯函数，未核通用DB写入口。（S1、S2、S3、S4） |
| `parent_tenant_id` | uuid / uuid；可NULL | 无默认 | MSSP父租户标识；可为空，引用同表，父租户删除时置空。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | Tenant ORM、bootstrap/租户开通服务写基础资料；开通来源两列另用SQL同步。治理驻留两列只确认DDL与服务纯函数，未核通用DB写入口。（S1、S2、S3、S4） |
| `mssp_role` | text / text；非NULL | `'standalone'::text` | 租户在MSSP层级中的角色。 | DB CHECK封闭枚举：standalone=独立租户；parent=MSSP父租户；child=MSSP子租户。 TEXT自由文本；无已确认封闭枚举。 | Tenant ORM、bootstrap/租户开通服务写基础资料；开通来源两列另用SQL同步。治理驻留两列只确认DDL与服务纯函数，未核通用DB写入口。（S1、S2、S3、S4） |
| `provisioned_from_waitlist_id` | uuid / uuid；可NULL | 无默认 | 本租户由哪条等候名单申请开通；可为空，申请删除时置空。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | Tenant ORM、bootstrap/租户开通服务写基础资料；开通来源两列另用SQL同步。治理驻留两列只确认DDL与服务纯函数，未核通用DB写入口。（S1、S2、S3、S4、S5） |
| `provisioned_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 开通服务建立租户的时刻；与created_at用途不同，旧/非该路径租户可为空。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | Tenant ORM、bootstrap/租户开通服务写基础资料；开通来源两列另用SQL同步。治理驻留两列只确认DDL与服务纯函数，未核通用DB写入口。（S1、S2、S3、S4、S5） |
| `data_region` | text / text；可NULL | 无默认 | 租户声明的数据驻留区域标签；无数据库封闭区域清单。 | 自由TEXT区域标签/NULL，无DB枚举；治理函数使用策略对象的region，未核该列的通用持久写入入口。 | 确认迁移088列设计；当前Tenant ORM未映射这两列。本轮未确认将此列加载进治理策略及更新的完整接线，不能据此宣称运行强制生效。（S1、S2、S3、S4） |
| `residency_enforced` | boolean / bool；非NULL | `false` | 驻留限制开关设计；true要求相关写入/导出遵守声明区域，不代表所有数据库读写均自动受此列约束。 | BOOLEAN：true=是/启用该标记，false=否/未启用；具体业务含义见本列说明。 | 确认迁移088列设计；当前Tenant ORM未映射这两列。本轮未确认将此列加载进治理策略及更新的完整接线，不能据此宣称运行强制生效。（S1、S2、S3、S4） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `tenants_mssp_role_check`：`CHECK ((mssp_role = ANY (ARRAY['standalone'::text, 'parent'::text, 'child'::text])))`
- `tenants_parent_tenant_id_fkey`：`FOREIGN KEY (parent_tenant_id) REFERENCES tenants(id) ON DELETE SET NULL`
- `tenants_provisioned_from_waitlist_fk`：`FOREIGN KEY (provisioned_from_waitlist_id) REFERENCES aisoc_waitlist_entries(id) ON DELETE SET NULL`
- `tenants_pkey`：`PRIMARY KEY (id)`
- `tenants_slug_key`：`UNIQUE (slug)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/api/app/models/tenant.py:13 ](../../../services/api/app/models/tenant.py:13)
- S3：[ services/api/app/services/tenant_provision/provisioner.py:381 ](../../../services/api/app/services/tenant_provision/provisioner.py:381)
- S4：[ services/api/migrations/088_data_governance.sql:75 ](../../../services/api/migrations/088_data_governance.sql:75)
- S5：[ services/api/app/services/tenant_provision/provisioner.py:490 ](../../../services/api/app/services/tenant_provision/provisioner.py:490)

<a id="connectors"></a>

### 3.8 `connectors`

租户内连接器实例、认证/连接配置及采集健康状态；connector_type为类型标识，id为实例标识。

字段数 **29**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `uuid_generate_v4()` | 连接器实例主键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 所属租户标识，数据库外键引用tenants。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4） |
| `name` | character varying / varchar；非NULL | 无默认 | 连接器实例显示名称。 | VARCHAR自由文本；catalog未记录字符长度；无已确认封闭枚举。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4） |
| `connector_type` | character varying / varchar；非NULL | 无默认 | 连接器实现/目录类型标识；不是实例ID，也不等同writeback vendor。 | 自由VARCHAR；创建API按运行连接器目录校验，因此支持集合依目录变化，无DB封闭枚举；splunk等仅示例。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4） |
| `connector_config` | jsonb / jsonb；可NULL | `'{}'::jsonb` | 非认证连接参数，具体结构由连接器类型决定。 | JSON对象，类型相关开放结构。API说明poll interval/region/log filters等；参考采集writer还将checkpoint对象并入connector_config.checkpoint，不能预设各类型统一键。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4） |
| `auth_config` | jsonb / jsonb；可NULL | `'{}'::jsonb` | 连接器认证配置；ORM声明应用层加密，不能当作可公开展示的普通配置。 | JSON对象，API经get_vault().encrypt_dict入库；确切加密包格式由vault实现决定，本字典不展开凭据值。API响应主动省略该列。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4） |
| `is_enabled` | boolean / bool；可NULL | `true` | 实例是否启用的配置开关。 | BOOLEAN：true=是/启用该标记，false=否/未启用；具体业务含义见本列说明。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4） |
| `health_status` | character varying / varchar；可NULL | `'unknown'::character varying` | 实例健康状态标签，API测试连接及OAuth刷新等路径更新。 | 应用已核unknown=尚未确定，healthy=健康，unhealthy=不健康；DB无CHECK，因此不能宣称这三个是所有存量可出现值。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4、S5） |
| `last_sync` | timestamp with time zone / timestamptz；可NULL | 无默认 | 最后同步/轮询周期时点；包含空轮询，不代表收到事件。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4、S5） |
| `events_ingested` | bigint / int8；可NULL | `0` | 参考采集writer按成功接受的events_added累加；不等于完整入湖或最终告警数。 | 整数计数，DB无非负CHECK。参考采集成功累加events_added/events_dropped，失败累加error_count；不等于全链入湖成功/死信条数。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4、S5） |
| `created_at` | timestamp with time zone / timestamptz；可NULL | `now()` | 连接器实例记录创建时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4） |
| `updated_at` | timestamp with time zone / timestamptz；可NULL | `now()` | 实例记录更新时间，ORM维护；不能把默认now解释为所有更新自动触发。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4） |
| `category` | character varying / varchar；非NULL | `''::character varying` | 连接器类别标签，实例创建时按目录/请求确定。 | 自由VARCHAR；创建API优先request.category，其次目录category，再回退uncategorized=未分类。不是DB枚举。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4） |
| `last_health_check` | timestamp with time zone / timestamptz；可NULL | 无默认 | 最近连接健康检查时点，API测试连接路径更新。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4、S5） |
| `error_count` | integer / int4；可NULL | `0` | 参考采集writer在轮询失败时累加的错误次数，未见成功时清零。 | 整数计数，DB无非负CHECK。参考采集成功累加events_added/events_dropped，失败累加error_count；不等于全链入湖成功/死信条数。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4、S6） |
| `tags` | jsonb / jsonb；可NULL | `'[]'::jsonb` | 连接器实例标签数组。 | JSON数组；API/ORM标签列表约定，不是数据库text[]；数据库无JSON形状CHECK。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4） |
| `schema_fingerprint` | text / text；可NULL | 无默认 | 上次已知输入形状指纹，供漂移比较；尚无非空采样时可为空。 | 设计为排序去重顶层字段名集合的SHA256十六进制字符串；NULL直到非空采样。DB是自由TEXT，无长度/hex CHECK。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4、S5） |
| `last_schema_drift_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 最近检测到输入schema漂移的时点。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4、S7） |
| `last_drift_details` | jsonb / jsonb；可NULL | 无默认 | 最近schema漂移的详情；不代表全部漂移历史。 | JSON对象/NULL。参考scheduler写added、removed、sample_event_count、new_fingerprint、previous_fingerprint等；因为旧键列表未留存，previous_keys=[]，added会是当前全键集合，不能当精确增删历史。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4、S7、S8） |
| `events_dropped` | integer / int4；非NULL | `0` | 连接器丢弃事件计数；与dead-letter记录数不保证相等。 | 整数计数，DB无非负CHECK。参考采集成功累加events_added/events_dropped，失败累加error_count；不等于全链入湖成功/死信条数。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4、S5） |
| `last_event_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 最近实际收到事件的时刻，和空轮询也会前进的last_sync分开。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4、S5） |
| `last_event_kind` | text / text；可NULL | 无默认 | 最近实际事件种类标签，供入流验证/预览说明。 | 自由TEXT；迁移示例alert/audit/webhook/push不是枚举。参考scheduler实际在accepted>0时写connector_type，不能按上述四值硬编码。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4、S5、S9） |
| `ingest_token` | text / text；可NULL | 无默认 | 该实例推送入口使用的不透明令牌；未生成可为空，数据库唯一；属于敏感凭据。 | TEXT自由文本；无已确认封闭枚举。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4） |
| `oauth_provisioned` | boolean / bool；非NULL | `false` | 实例是否通过托管OAuth流程创建；用于刷新归属及凭据管理方式。 | BOOLEAN：true=是/启用该标记，false=否/未启用；具体业务含义见本列说明。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4） |
| `allowed_capabilities` | jsonb / jsonb；可NULL | 无默认 | 实例允许能力清单，用于缩减连接器类声明的能力；NULL表示不额外缩减。 | NULL=不缩减类默认能力；非NULL JSON字符串数组=显式允许清单（空数组表示不允许任何能力）。pull_alerts=拉告警、query_logs=查日志只是示例，完整集合由连接器能力目录决定。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4） |
| `oauth_refresh_failures` | integer / int4；非NULL | `0` | 连续OAuth刷新失败次数，成功后重置为0。 | INTEGER整数；除下列CHECK外无已确认范围约束。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4） |
| `oauth_last_refresh_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 最近一次OAuth刷新成功时刻。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4） |
| `last_outage_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 本轮故障开始时刻的设计状态；恢复时清除，供故障时长与补采判断。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | API connectors/OAuth维护实例与凭据，oauth_refresh更新刷新状态。采集字段补核本地原版参考副本connector_repo/scheduler；未校该副本与当前部署镜像一致，不作为已运行证明。（S1、S2、S3、S4、S5、S6） |
| `last_backfill_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 补采触发/尝试时间戳，参考scheduler在启动一次补采前记录，即使补采失败仍保留；不表示补采成功。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | 参考scheduler._record_backfill_run在触发一次性补采前记戳；connector_repo.record_backfill_run入库。未核部署运行。（S1、S2、S3、S4、S10） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `connectors_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `connectors_pkey`：`PRIMARY KEY (id)`
- `connectors_ingest_token_key`：`UNIQUE (ingest_token)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/api/app/models/connector.py:13 ](../../../services/api/app/models/connector.py:13)
- S3：[ services/api/app/api/v1/endpoints/connectors.py:813 ](../../../services/api/app/api/v1/endpoints/connectors.py:813)
- S4：[ services/api/app/workers/oauth_refresh.py:405 ](../../../services/api/app/workers/oauth_refresh.py:405)
- S5：[ .local/initialization/full-source-staging/services/connectors/app/db/connector_repo.py:175 ](../../../.local/initialization/full-source-staging/services/connectors/app/db/connector_repo.py:175)
- S6：[ .local/initialization/full-source-staging/services/connectors/app/db/connector_repo.py:220 ](../../../.local/initialization/full-source-staging/services/connectors/app/db/connector_repo.py:220)
- S7：[ .local/initialization/full-source-staging/services/connectors/app/db/connector_repo.py:285 ](../../../.local/initialization/full-source-staging/services/connectors/app/db/connector_repo.py:285)
- S8：[ .local/initialization/full-source-staging/services/connectors/app/scheduler.py:683 ](../../../.local/initialization/full-source-staging/services/connectors/app/scheduler.py:683)
- S9：[ .local/initialization/full-source-staging/services/connectors/app/scheduler.py:745 ](../../../.local/initialization/full-source-staging/services/connectors/app/scheduler.py:745)
- S10：[ .local/initialization/full-source-staging/services/connectors/app/scheduler.py:851 ](../../../.local/initialization/full-source-staging/services/connectors/app/scheduler.py:851)

<a id="alert_source_links"></a>

### 3.9 `alert_source_links`

同一告警可对应多个来源系统finding；每个(alert_id,vendor,external_id)只有一行，保存最新回写尝试而非完整历史。

字段数 **15**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `uuid_generate_v4()` | 来源关联记录主键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | alert_source_link.upsert_link记录来源关联；record_writeback更新最新回写结果，siem_writeback提供应用状态。（S1、S2、S3、S4） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 关联所属租户，数据库外键引用tenants。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | alert_source_link.upsert_link记录来源关联；record_writeback更新最新回写结果，siem_writeback提供应用状态。（S1、S2、S3、S4） |
| `alert_id` | uuid / uuid；非NULL | 无默认 | 对应告警ID，外键引用alerts；删除告警级联删除该关联。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | alert_source_link.upsert_link记录来源关联；record_writeback更新最新回写结果，siem_writeback提供应用状态。（S1、S2、S3、S4） |
| `vendor` | text / text；非NULL | 无默认 | 回写调度使用的来源厂商ID，和connector_type不同。 | 自由TEXT。程序可调度集合splunk=Splunk、elastic=Elastic、sentinel=Microsoft Sentinel、qradar=IBM QRadar、defender=Microsoft Defender；其他vendor仍可存储但dispatchable=false，不是DB封闭枚举。 | alert_source_link.upsert_link记录来源关联；record_writeback更新最新回写结果，siem_writeback提供应用状态。（S1、S2、S3、S4） |
| `connector_instance_id` | uuid / uuid；可NULL | 无默认 | 产生来源finding的连接器实例ID；catalog没有到connectors的外键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | alert_source_link.upsert_link记录来源关联；record_writeback更新最新回写结果，siem_writeback提供应用状态。（S1、S2、S3、S4） |
| `external_id` | text / text；非NULL | 无默认 | 厂商系统finding原生标识；本地upsert会去掉两侧空白并拒绝空值。 | TEXT自由文本；无已确认封闭枚举。 | alert_source_link.upsert_link记录来源关联；record_writeback更新最新回写结果，siem_writeback提供应用状态。（S1、S2、S3、S4） |
| `external_url` | text / text；可NULL | 无默认 | 来源finding链接；未核统一URL校验，不能保证可访问。 | TEXT自由文本；无已确认封闭枚举。 | alert_source_link.upsert_link记录来源关联；record_writeback更新最新回写结果，siem_writeback提供应用状态。（S1、S2、S3、S4） |
| `last_disposition` | text / text；可NULL | 无默认 | 最新一次尝试回写的业务判定，不等于告警当前状态。 | 当前SIEM回写可处理集合（DB无CHECK；并非所有值都执行关闭）：true_positive=真阳性；benign_true_positive=良性真阳性/合法活动命中；false_positive=误报；benign=旧有良性标签；escalate=升级处理。 | alert_source_link.upsert_link记录来源关联；record_writeback更新最新回写结果，siem_writeback提供应用状态。（S1、S2、S3、S4） |
| `last_writeback_action` | text / text；可NULL | 无默认 | 最近回写动作类型，不等于动作已实际执行。 | 自由TEXT；已见程序动作close=关闭来源finding、escalate=升级、refuse=拒绝默认；动作可从下游结果传入，不能作为DB封闭枚举。 | alert_source_link.upsert_link记录来源关联；record_writeback更新最新回写结果，siem_writeback提供应用状态。（S1、S2、S3、S4） |
| `last_writeback_status` | text / text；可NULL | 无默认 | 最近回写尝试的结果状态。 | 当前WritebackOutcome程序集合（DB无CHECK）：executed=厂商调用实际执行；dry_run=仅演练；refused=被拒绝；simulated=无实际厂商调用的模拟；failed=调用/处理失败；skipped=跳过。 | alert_source_link.upsert_link记录来源关联；record_writeback更新最新回写结果，siem_writeback提供应用状态。（S1、S2、S3、S4） |
| `last_writeback_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 记录最近回写结果时的数据库时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | alert_source_link.upsert_link记录来源关联；record_writeback更新最新回写结果，siem_writeback提供应用状态。（S1、S2、S3、S4） |
| `last_writeback_detail` | text / text；可NULL | 无默认 | 最近回写结果的原因/说明文本。 | 自由TEXT；当前SIEM结果常截到2000字符，但通用record_writeback接受str，不存在DB长度约束或全路径统一上限保证。 | alert_source_link.upsert_link记录来源关联；record_writeback更新最新回写结果，siem_writeback提供应用状态。（S1、S2、S3、S4） |
| `executed` | boolean / bool；非NULL | 无默认 | 该记录所描述的最新回写是否实际执行厂商调用；false包括仅计划、拒绝、无凭据模拟；不能只用status推断。 | BOOLEAN：true=是/启用该标记，false=否/未启用；具体业务含义见本列说明。 | alert_source_link.upsert_link记录来源关联；record_writeback更新最新回写结果，siem_writeback提供应用状态。（S1、S2、S3、S4） |
| `created_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 首次建立该来源关联的时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | alert_source_link.upsert_link记录来源关联；record_writeback更新最新回写结果，siem_writeback提供应用状态。（S1、S2、S3、S4） |
| `updated_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 来源信息或回写状态最近一次更新的数据库时刻。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | alert_source_link.upsert_link记录来源关联；record_writeback更新最新回写结果，siem_writeback提供应用状态。（S1、S2、S3、S4） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `alert_source_links_alert_id_fkey`：`FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE CASCADE`
- `alert_source_links_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `alert_source_links_pkey`：`PRIMARY KEY (id)`
- `uq_alert_source_link`：`UNIQUE (alert_id, vendor, external_id)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/api/app/services/alert_source_link.py:132 ](../../../services/api/app/services/alert_source_link.py:132)
- S3：[ services/api/app/services/alert_source_link.py:194 ](../../../services/api/app/services/alert_source_link.py:194)
- S4：[ services/api/app/services/siem_writeback.py:84 ](../../../services/api/app/services/siem_writeback.py:84)

<a id="socai2_triage_budget_reservations"></a>

### 3.10 `socai2_triage_budget_reservations`

普通Kafka分诊请求的持久预算预留；按Run一行。charged_tokens是保守预留，不是provider实际Token或金额；未确认调用保留并发槽。

字段数 **9**；2026-10-22 22:56样例租户行数 **3**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `run_id` | uuid / uuid；非NULL | 无默认 | 预留所属Run主键，同时外键引用investigation_runs，一Run最多一份预留。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | agents triage_budget.reserve / Invocation.before_request/responded/no_request维护。（S1、S2、S3、S4、S5） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 预算归属租户，外键引用tenants。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | agents triage_budget.reserve / Invocation.before_request/responded/no_request维护。（S1、S2、S3、S4、S5） |
| `policy_sha256` | character varying / varchar；非NULL | 无默认 | 形成该预留时规范化预算策略内容的SHA256，不是请求正文hash。 | 程序输出64位小写SHA256十六进制；内容含policy字段与schema_version/per_request_reserved_tokens/prompt_byte_cap/output_token_cap；DB仅varchar，catalog未采长度与hex正则。 | agents triage_budget.reserve / Invocation.before_request/responded/no_request维护。（S1、S2、S3、S4、S5） |
| `charged_tokens` | integer / int4；非NULL | 无默认 | 本次请求计入窗口限额的预留Token数；当前程序常量20000，不随实际响应退款。 | INTEGER；DB CHECK >0；当前reserve恒写RESERVED_TOKENS=20000，是预留额度，不是已消耗Tokens。 | agents triage_budget.reserve / Invocation.before_request/responded/no_request维护。（S1、S2、S3、S4、S5） |
| `reserved_at` | timestamp with time zone / timestamptz；非NULL | `clock_timestamp()` | 数据库预留时刻，clock_timestamp()；用于窗口调用数/预留量统计。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | agents triage_budget.reserve / Invocation.before_request/responded/no_request维护。（S1、S2、S3、S4、S5） |
| `request_started_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 发请求前持久标记的请求意图时刻；即使此后停止也不保证请求已实际发出。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | agents triage_budget.reserve / Invocation.before_request/responded/no_request维护。（S1、S2、S3、S4、S5） |
| `settled_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 确定responded或no_request后的结算时刻；未知调用继续为空。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | agents triage_budget.reserve / Invocation.before_request/responded/no_request维护。（S1、S2、S3、S4、S5） |
| `outcome` | character varying / varchar；非NULL | `'reserved'::character varying` | 预算生命周期结果；未知响应情况仍保留reserved，而不是增加unknown枚举。 | DB CHECK封闭枚举：reserved=已预留但调用结果尚未结清；responded=已观察到模型响应并结清；no_request=确认没有发出请求并结清。 VARCHAR自由文本；catalog未记录字符长度；无已确认封闭枚举。 | agents triage_budget.reserve / Invocation.before_request/responded/no_request维护。（S1、S2、S3、S4、S5） |
| `observed_tokens` | integer / int4；可NULL | 无默认 | 响应usage_metadata.total_tokens观察值；无有效usage可为空，不是charged_tokens。 | INTEGER/NULL；DB CHECK >=0；responded程序仅接受整数0..20000或None，范围上界是应用规则而非DB CHECK。 | agents triage_budget.reserve / Invocation.before_request/responded/no_request维护。（S1、S2、S3、S4、S5） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `socai2_triage_budget_reservations_charged_tokens_check`：`CHECK ((charged_tokens > 0))`
- `socai2_triage_budget_reservations_check`：`CHECK (((((outcome)::text = 'reserved'::text) AND (settled_at IS NULL)) OR (((outcome)::text <> 'reserved'::text) AND (settled_at IS NOT NULL))))`
- `socai2_triage_budget_reservations_check1`：`CHECK ((((outcome)::text <> 'responded'::text) OR (request_started_at IS NOT NULL)))`
- `socai2_triage_budget_reservations_observed_tokens_check`：`CHECK ((observed_tokens >= 0))`
- `socai2_triage_budget_reservations_outcome_check`：`CHECK (((outcome)::text = ANY ((ARRAY['reserved'::character varying, 'responded'::character varying, 'no_request'::character varying])::text[])))`
- `socai2_triage_budget_reservations_run_id_fkey`：`FOREIGN KEY (run_id) REFERENCES investigation_runs(id)`
- `socai2_triage_budget_reservations_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id)`
- `socai2_triage_budget_reservations_pkey`：`PRIMARY KEY (run_id)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/agents/app/workers/triage_budget.py:87 ](../../../services/agents/app/workers/triage_budget.py:87)
- S3：[ services/agents/app/workers/triage_budget.py:112 ](../../../services/agents/app/workers/triage_budget.py:112)
- S4：[ services/agents/app/workers/triage_budget.py:37 ](../../../services/agents/app/workers/triage_budget.py:37)
- S5：[ deploy/aisoc21/migrations/001_triage_budget.sql:4 ](../../../deploy/aisoc21/migrations/001_triage_budget.sql:4)

<a id="aisoc_dead_letters"></a>

### 3.11 `aisoc_dead_letters`

流水线拒绝输入的可查询摘要；用于解释拒绝原因，不是可重放完整原始消息仓库。

字段数 **12**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `gen_random_uuid()` | 拒绝记录主键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | Fusion PostgresDLQ与UEBA DeadLetterSink写；health读取。ack两列确认DDL和读取，当前本轮未确认人工ack写入路径。（S1、S2、S3、S4） |
| `tenant_id` | uuid / uuid；可NULL | 无默认 | 可识别的所属租户；信封在租户解析前损坏或租户不合法时可为空，不猜租户。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | Fusion PostgresDLQ与UEBA DeadLetterSink写；health读取。ack两列确认DDL和读取，当前本轮未确认人工ack写入路径。（S1、S2、S3、S4） |
| `topic` | text / text；非NULL | 无默认 | 输入/拒绝消息来自的topic名称，非固定枚举。 | TEXT自由文本；无已确认封闭枚举。 | Fusion PostgresDLQ与UEBA DeadLetterSink写；health读取。ack两列确认DDL和读取，当前本轮未确认人工ack写入路径。（S1、S2、S3、S4） |
| `reason` | text / text；非NULL | 无默认 | 拒绝原因文本；不同生产者可写不同原因，无数据库封闭理由清单。 | TEXT自由文本；无已确认封闭枚举。 | Fusion PostgresDLQ与UEBA DeadLetterSink写；health读取。ack两列确认DDL和读取，当前本轮未确认人工ack写入路径。（S1、S2、S3、S4） |
| `schema_version` | text / text；非NULL | `'unknown'::text` | 被处理信封版本标记；默认unknown，UEBA writer写ueba.raw_events.v1。 | TEXT自由文本；无已确认封闭枚举。 | Fusion PostgresDLQ与UEBA DeadLetterSink写；health读取。ack两列确认DDL和读取，当前本轮未确认人工ack写入路径。（S1、S2、S3、S4） |
| `payload_excerpt` | text / text；非NULL | `''::text` | 被拒消息摘要/截断片段；不是完整原文，不保证是可解析JSON。 | TEXT，Fusion/UEBA当前writer最多2000字符；可能截断JSON；该字符上限是程序约定，DB无CHECK。 | Fusion PostgresDLQ与UEBA DeadLetterSink写；health读取。ack两列确认DDL和读取，当前本轮未确认人工ack写入路径。（S1、S2、S3、S4） |
| `source_event_id` | text / text；可NULL | 无默认 | 生产者可提供的原始事件ID；可为空，无到事件表的外键。 | TEXT自由文本；无已确认封闭枚举。 | Fusion PostgresDLQ与UEBA DeadLetterSink写；health读取。ack两列确认DDL和读取，当前本轮未确认人工ack写入路径。（S1、S2、S3、S4） |
| `occurred_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 拒绝记录入表时刻，当前writer省略该列使用DB now；不等同原事件发生时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | Fusion PostgresDLQ与UEBA DeadLetterSink写；health读取。ack两列确认DDL和读取，当前本轮未确认人工ack写入路径。（S1、S2、S3、S4） |
| `acknowledged_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 人工/运维确认该拒绝记录的时间设计列；本轮未确认具体writer。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | 迁移053保留确认状态列；health读acknowledged_at导出是否确认。未核到当前确认写入入口，不称无writer。（S1、S2、S3、S4） |
| `acknowledged_by` | text / text；可NULL | 无默认 | 确认者文本身份设计列；不是users外键，本轮未确认具体writer。 | TEXT自由文本；无已确认封闭枚举。 | 迁移053保留确认状态列；health读acknowledged_at导出是否确认。未核到当前确认写入入口，不称无writer。（S1、S2、S3、S4） |
| `topic_partition` | integer / int4；可NULL | 无默认 | 原Kafka记录分区；没有对应Kafka记录的拒绝路径留空。 | INTEGER整数；除下列CHECK外无已确认范围约束。 | Fusion PostgresDLQ与UEBA DeadLetterSink写；health读取。ack两列确认DDL和读取，当前本轮未确认人工ack写入路径。（S1、S2、S3、S4） |
| `kafka_offset` | bigint / int8；可NULL | 无默认 | 原Kafka记录偏移；可与topic及partition联合定位，不是跨分区游标。 | BIGINT整数；除下列CHECK外无已确认范围约束。 | Fusion PostgresDLQ与UEBA DeadLetterSink写；health读取。ack两列确认DDL和读取，当前本轮未确认人工ack写入路径。（S1、S2、S3、S4） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `aisoc_dead_letters_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `aisoc_dead_letters_pkey`：`PRIMARY KEY (id)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/fusion/app/services/dlq_sink.py:44 ](../../../services/fusion/app/services/dlq_sink.py:44)
- S3：[ services/ueba/app/services/dead_letters.py:49 ](../../../services/ueba/app/services/dead_letters.py:49)
- S4：[ services/api/app/api/v1/endpoints/health.py:577 ](../../../services/api/app/api/v1/endpoints/health.py:577)

<a id="assets"></a>

### 3.12 `assets`

资产库存/CMDB基础资料，可被告警处理上下文读取；本次catalog租户内0行，不表示功能已验证或无其他租户数据。

字段数 **19**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `gen_random_uuid()` | 资产主键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 资产所属租户，外键引用tenants。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `asset_type` | text / text；非NULL | `'host'::text` | 库存资产类别，数据库CHECK限定。 | DB CHECK封闭枚举：host=主机；container=容器；cloud_resource=云资源；user_account=用户账号；service=服务；network_device=网络设备；domain=域名；ip=IP地址。 TEXT自由文本；无已确认封闭枚举。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `name` | text / text；非NULL | 无默认 | 资产名称/显示标识。 | TEXT自由文本；无已确认封闭枚举。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `fqdn` | text / text；可NULL | 无默认 | 资产完整域名文本；接口未限定必须是有效DNS名。 | TEXT自由文本；无已确认封闭枚举。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `ip_addresses` | ARRAY / _text；可NULL | 无默认 | 资产IP地址文本列表；数据库为text[]，不是inet[]。 | TEXT[]字符串数组；API list[str]，没有DB inet格式校验，不能据类型保证每项合法IP。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `cloud_provider` | text / text；可NULL | 无默认 | 云平台标签；迁移注释列aws/gcp/azure/other为示例，不是DB枚举。 | 自由TEXT；迁移示例aws=亚马逊云、gcp=谷歌云、azure=微软云、other=其他，非完整枚举。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `cloud_region` | text / text；可NULL | 无默认 | 云区域文本。 | TEXT自由文本；无已确认封闭枚举。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `cloud_account` | text / text；可NULL | 无默认 | 云账号/订阅标识文本。 | TEXT自由文本；无已确认封闭枚举。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `os` | text / text；可NULL | 无默认 | 操作系统名称文本。 | TEXT自由文本；无已确认封闭枚举。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `os_version` | text / text；可NULL | 无默认 | 操作系统版本文本。 | TEXT自由文本；无已确认封闭枚举。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `criticality` | text / text；非NULL | `'medium'::text` | 业务资产重要性，不是告警严重度或调查置信度。 | DB CHECK封闭枚举：critical=严重/最高级；high=高；medium=中；low=低；info=信息。 TEXT自由文本；无已确认封闭枚举。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `tags` | ARRAY / _text；可NULL | 无默认 | 资产分类标签列表。 | TEXT[]字符串数组；元素未见数据库格式/封闭枚举约束。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `owner_email` | text / text；可NULL | 无默认 | 资产负责人邮箱文本；当前AssetCreate为str，非EmailStr校验。 | 自由TEXT。API仅str，未校验邮箱格式。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `last_seen` | timestamp with time zone / timestamptz；非NULL | `now()` | 库存最近观测到资产的时间；此API创建默认当前时间，非告警last_seen。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `first_seen` | timestamp with time zone / timestamptz；非NULL | `now()` | 库存首次观测/创建资产时点；默认当前时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `metadata` | jsonb / jsonb；非NULL | `'{}'::jsonb` | 资产扩展属性对象；ORM属性名asset_metadata，对应DB列metadata。 | JSON对象，API接收任意dict；无统一必备键和DB JSON schema。参考漏洞同步给自动资产写source=scanner等来源元数据，仅为一个writer形状。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `created_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 资产记录创建时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |
| `updated_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 资产记录更新时间；迁移含资产更新触发器设计，catalog未采触发器，本轮未重核线上触发器状态。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | assets API create/update写基础资产；processing_context按主机/IP或alert_asset_correlations查资产。（S1、S2、S3、S4、S5） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `assets_asset_type_check`：`CHECK ((asset_type = ANY (ARRAY['host'::text, 'container'::text, 'cloud_resource'::text, 'user_account'::text, 'service'::text, 'network_device'::text, 'domain'::text, 'ip'::text])))`
- `assets_criticality_check`：`CHECK ((criticality = ANY (ARRAY['critical'::text, 'high'::text, 'medium'::text, 'low'::text, 'info'::text])))`
- `assets_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `assets_pkey`：`PRIMARY KEY (id)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/api/migrations/013_asset_inventory.sql:7 ](../../../services/api/migrations/013_asset_inventory.sql:7)
- S3：[ services/api/app/api/v1/endpoints/assets.py:43 ](../../../services/api/app/api/v1/endpoints/assets.py:43)
- S4：[ services/api/app/api/v1/endpoints/assets.py:143 ](../../../services/api/app/api/v1/endpoints/assets.py:143)
- S5：[ services/api/app/services/processing_context.py:19 ](../../../services/api/app/services/processing_context.py:19)

<a id="asset_vulnerabilities"></a>

### 3.13 `asset_vulnerabilities`

资产漏洞发现记录；asset_id关联资产；同CVE可在多个资产/扫描器形成多条。补丁窗口三列是设计与运行资料，不能假设基本漏洞API已经写满。

字段数 **21**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `gen_random_uuid()` | 漏洞发现记录主键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 所属租户，外键引用tenants。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5） |
| `asset_id` | uuid / uuid；非NULL | 无默认 | 被发现有该漏洞的资产，外键引用assets，删除资产级联删除。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5） |
| `cve_id` | text / text；可NULL | 无默认 | CVE编号文本；当前API未校验CVE正则。 | TEXT自由文本；无已确认封闭枚举。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5） |
| `title` | text / text；非NULL | 无默认 | 漏洞发现标题。 | TEXT自由文本；无已确认封闭枚举。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5） |
| `description` | text / text；可NULL | 无默认 | 漏洞描述文本。 | TEXT自由文本；无已确认封闭枚举。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5） |
| `severity` | text / text；非NULL | `'medium'::text` | 漏洞严重度，数据库CHECK限定。 | DB CHECK封闭枚举：critical=严重/最高级；high=高；medium=中；low=低；info=信息。 TEXT自由文本；无已确认封闭枚举。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5） |
| `cvss_score` | double precision / float8；可NULL | 无默认 | CVSS数值分数；API为float，DB未设置0—10范围CHECK。 | DOUBLE PRECISION/NULL；标准含义为CVSS评分，通常0—10，但当前API仅float、catalog无范围CHECK，不能声称DB已强制。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5） |
| `cvss_vector` | text / text；可NULL | 无默认 | CVSS向量字符串；未核解析/版本格式校验。 | TEXT自由文本；无已确认封闭枚举。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5） |
| `epss_score` | double precision / float8；可NULL | 无默认 | EPSS利用预测分数；设计注释0—1，当前API/DB未强制该范围。 | DOUBLE PRECISION/NULL；迁移注释约定0—1，API float/DB未强制范围。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5） |
| `is_exploited` | boolean / bool；非NULL | `false` | 库存中是否标记为已被利用；不自动意味着此租户资产已遭入侵。 | BOOLEAN：true=是/启用该标记，false=否/未启用；具体业务含义见本列说明。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5） |
| `source` | text / text；非NULL | 无默认 | 扫描器/漏洞来源名称文本。 | 自由TEXT。扫描器名称；tenable/qualys/trivy仅迁移示例，不是封闭枚举。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5） |
| `external_id` | text / text；可NULL | 无默认 | 扫描器原生finding标识文本。 | TEXT自由文本；无已确认封闭枚举。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5） |
| `first_found` | timestamp with time zone / timestamptz；非NULL | `now()` | 首次发现漏洞的时间，默认当前时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5、S6） |
| `last_found` | timestamp with time zone / timestamptz；非NULL | `now()` | 最近发现漏洞的时间，默认当前时间；当前新增API不是重新扫描更新证明。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5、S6） |
| `remediated_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 修复时间；为空表示未记录修复，而非证明漏洞依旧可利用。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5） |
| `metadata` | jsonb / jsonb；非NULL | `'{}'::jsonb` | 漏洞扩展属性对象；ORM属性asset_metadata对应DB metadata。 | JSON对象、开放扩展；当前API任意dict，参考漏洞同步writer写plugin_id（可能空）；非统一封闭schema。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5、S6） |
| `created_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 漏洞记录创建时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5） |
| `environment` | text / text；可NULL | 无默认 | 补丁策略环境桶；迁移设计按主机归类test/prod，未知主机按prod处理。 | 应用设计/参考writer约定test=测试环境、prod=生产环境；无法判定按prod；DB无CHECK。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5、S6） |
| `patch_due_date` | date / date；可NULL | 无默认 | 首次物化时按first_found计算的补丁到期日；迁移明确重复拉取不应顺延。 | DATE，序列化YYYY-MM-DD；参考writer初次插入时由classify_environment+patch_due_for计算，复扫仅touch不延后。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5、S6、S7） |
| `patch_status` | text / text；非NULL | `'tracked'::text` | 补丁跟踪/到期/告警提升生命周期标签；catalog没有CHECK约束。 | 当前参考writer集合tracked=正在跟踪、overdue=已过期、promoted=已提升为告警；DB无CHECK。参考SQL的resolved指告警status更新，并未确认本列写resolved，勿扩成该枚举。 | 当前assets API创建漏洞基础资料；另已静态核本地原版参考connectors.vulnerabilities的首次插入/复扫touch，以及vuln_promotion_sql的补丁状态变更。参考副本未校到当前运行镜像，不证明相关writer已部署/运行。（S1、S2、S3、S4、S5、S6、S7） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `asset_vulnerabilities_severity_check`：`CHECK ((severity = ANY (ARRAY['critical'::text, 'high'::text, 'medium'::text, 'low'::text, 'info'::text])))`
- `asset_vulnerabilities_asset_id_fkey`：`FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE`
- `asset_vulnerabilities_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `asset_vulnerabilities_pkey`：`PRIMARY KEY (id)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/api/migrations/013_asset_inventory.sql:40 ](../../../services/api/migrations/013_asset_inventory.sql:40)
- S3：[ services/api/app/api/v1/endpoints/assets.py:81 ](../../../services/api/app/api/v1/endpoints/assets.py:81)
- S4：[ services/api/app/models/asset.py:45 ](../../../services/api/app/models/asset.py:45)
- S5：[ services/api/migrations/100_vuln_patch_windows.sql:5 ](../../../services/api/migrations/100_vuln_patch_windows.sql:5)
- S6：[ .local/initialization/full-source-staging/services/connectors/app/vulnerabilities.py:84 ](../../../.local/initialization/full-source-staging/services/connectors/app/vulnerabilities.py:84)
- S7：[ .local/initialization/full-source-staging/services/connectors/app/vuln_promotion_sql.py:15 ](../../../.local/initialization/full-source-staging/services/connectors/app/vuln_promotion_sql.py:15)

<a id="alert_asset_correlations"></a>

### 3.14 `alert_asset_correlations`

告警到资产/漏洞的关联表；alert_id是逻辑关联而非数据库外键；asset/vuln删除时只清空对应引用。

字段数 **8**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `gen_random_uuid()` | 关联记录主键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | ORM存在，processing_context已读该表；本轮在当前业务源码未核到构造/INSERT writer，保留为设计关联表，不能称表不存在或一定没有writer。（S1、S2、S3、S4） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 关联所属租户，外键引用tenants。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | ORM存在，processing_context已读该表；本轮在当前业务源码未核到构造/INSERT writer，保留为设计关联表，不能称表不存在或一定没有writer。（S1、S2、S3、S4） |
| `alert_id` | uuid / uuid；非NULL | 无默认 | 对应告警UUID，catalog没有引用alerts的外键；必须与tenant一起关联。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | ORM存在，processing_context已读该表；本轮在当前业务源码未核到构造/INSERT writer，保留为设计关联表，不能称表不存在或一定没有writer。（S1、S2、S3、S4） |
| `asset_id` | uuid / uuid；可NULL | 无默认 | 匹配到的资产，可为空，数据库外键引用assets。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | ORM存在，processing_context已读该表；本轮在当前业务源码未核到构造/INSERT writer，保留为设计关联表，不能称表不存在或一定没有writer。（S1、S2、S3、S4） |
| `vuln_id` | uuid / uuid；可NULL | 无默认 | 匹配到的漏洞发现记录，可为空，数据库外键引用asset_vulnerabilities。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | ORM存在，processing_context已读该表；本轮在当前业务源码未核到构造/INSERT writer，保留为设计关联表，不能称表不存在或一定没有writer。（S1、S2、S3、S4） |
| `match_field` | text / text；非NULL | `'ip'::text` | 产生关联的匹配依据标签，默认ip；非数据库枚举，未确认完整应用值集合。 | 自由TEXT，无DB CHECK；默认ip=IP匹配；完整writer值集合未核，不列成封闭枚举。 | ORM存在，processing_context已读该表；本轮在当前业务源码未核到构造/INSERT writer，保留为设计关联表，不能称表不存在或一定没有writer。（S1、S2、S3、S4） |
| `confidence` | double precision / float8；非NULL | `1.0` | 关联置信度数值，默认1.0；catalog无0—1 CHECK，未核统一算法writer。 | DOUBLE PRECISION，默认1.0；数据库无0—1范围CHECK；本轮未核统一评分writer。 | ORM存在，processing_context已读该表；本轮在当前业务源码未核到构造/INSERT writer，保留为设计关联表，不能称表不存在或一定没有writer。（S1、S2、S3、S4） |
| `created_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 关联记录创建时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | ORM存在，processing_context已读该表；本轮在当前业务源码未核到构造/INSERT writer，保留为设计关联表，不能称表不存在或一定没有writer。（S1、S2、S3、S4） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `alert_asset_correlations_asset_id_fkey`：`FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE SET NULL`
- `alert_asset_correlations_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `alert_asset_correlations_vuln_id_fkey`：`FOREIGN KEY (vuln_id) REFERENCES asset_vulnerabilities(id) ON DELETE SET NULL`
- `alert_asset_correlations_pkey`：`PRIMARY KEY (id)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/api/migrations/013_asset_inventory.sql:68 ](../../../services/api/migrations/013_asset_inventory.sql:68)
- S3：[ services/api/app/models/asset.py:70 ](../../../services/api/app/models/asset.py:70)
- S4：[ services/api/app/services/processing_context.py:28 ](../../../services/api/app/services/processing_context.py:28)

<a id="identity_privilege"></a>

### 3.15 `identity_privilege`

轻量账号权限背景表，按(tenant_id,principal)唯一；不同于identity_nodes图节点的整数权限等级。

字段数 **8**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `gen_random_uuid()` | 权限背景记录主键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | processing_context按lower(principal)查询；DDL说明写前小写，但本轮未核到实际通用writer，不把注释当已执行标准化。（S1、S2、S3） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 所属租户，外键引用tenants。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | processing_context按lower(principal)查询；DDL说明写前小写，但本轮未核到实际通用writer，不把注释当已执行标准化。（S1、S2、S3） |
| `principal` | text / text；非NULL | 无默认 | 日志中的账号主体标识；设计约定小写，查询也按小写匹配。 | 自由TEXT；唯一键(tenant_id,principal)本身区分大小写。DDL注释要求应用小写，processing_context lower(principal)读取；实际写入标准化未核。 | processing_context按lower(principal)查询；DDL说明写前小写，但本轮未核到实际通用writer，不把注释当已执行标准化。（S1、S2、S3） |
| `privilege_tier` | text / text；非NULL | `'standard'::text` | 账号常驻权限等级的文本枚举。 | DB CHECK封闭枚举：standard=标准权限；elevated=提升权限；admin=管理员；domain_admin=域管理员。 TEXT自由文本；无已确认封闭枚举。 | processing_context按lower(principal)查询；DDL说明写前小写，但本轮未核到实际通用writer，不把注释当已执行标准化。（S1、S2、S3） |
| `is_service` | boolean / bool；非NULL | `false` | 是否服务账号。 | BOOLEAN：true=是/启用该标记，false=否/未启用；具体业务含义见本列说明。 | processing_context按lower(principal)查询；DDL说明写前小写，但本轮未核到实际通用writer，不把注释当已执行标准化。（S1、S2、S3） |
| `is_break_glass` | boolean / bool；非NULL | `false` | 是否紧急备用/破窗账号标记。 | BOOLEAN：true=是/启用该标记，false=否/未启用；具体业务含义见本列说明。 | processing_context按lower(principal)查询；DDL说明写前小写，但本轮未核到实际通用writer，不把注释当已执行标准化。（S1、S2、S3） |
| `source` | text / text；可NULL | 无默认 | 提供该权限资料的来源文本。 | TEXT自由文本；无已确认封闭枚举。 | processing_context按lower(principal)查询；DDL说明写前小写，但本轮未核到实际通用writer，不把注释当已执行标准化。（S1、S2、S3） |
| `updated_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 资料更新时点，默认now；未核writer，不承诺每次修改自动刷新。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | processing_context按lower(principal)查询；DDL说明写前小写，但本轮未核到实际通用writer，不把注释当已执行标准化。（S1、S2、S3） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `ck_identity_privilege_tier`：`CHECK ((privilege_tier = ANY (ARRAY['standard'::text, 'elevated'::text, 'admin'::text, 'domain_admin'::text])))`
- `identity_privilege_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `identity_privilege_pkey`：`PRIMARY KEY (id)`
- `identity_privilege_tenant_id_principal_key`：`UNIQUE (tenant_id, principal)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/api/migrations/085_asset_context_scoring.sql:35 ](../../../services/api/migrations/085_asset_context_scoring.sql:35)
- S3：[ services/api/app/services/processing_context.py:34 ](../../../services/api/app/services/processing_context.py:34)

<a id="identity_nodes"></a>

### 3.16 `identity_nodes`

身份关系图的节点表；(tenant_id,source_system,external_id)唯一。不等于Neo4j投影或identity_privilege小表。

字段数 **13**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `gen_random_uuid()` | 身份图内部节点ID。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | identity_graph API create_node通过ORM写NodeCreate字段，包括last_activity；API读列表/详情。未确认独立实时身份评分或活动同步器，不能据列存在承诺自动维护。（S1、S2、S3、S4） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 节点所属租户，外键引用tenants。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | identity_graph API create_node通过ORM写NodeCreate字段，包括last_activity；API读列表/详情。未确认独立实时身份评分或活动同步器，不能据列存在承诺自动维护。（S1、S2、S3、S4） |
| `node_type` | text / text；非NULL | 无默认 | 节点类别，数据库CHECK限定。 | DB CHECK封闭枚举：human_user=人员账号；service_account=服务账号；device=设备；application=应用；group=组；role=角色。 TEXT自由文本；无已确认封闭枚举。 | identity_graph API create_node通过ORM写NodeCreate字段，包括last_activity；API读列表/详情。未确认独立实时身份评分或活动同步器，不能据列存在承诺自动维护。（S1、S2、S3、S4） |
| `external_id` | text / text；非NULL | 无默认 | 来源系统内主体标识，如邮箱/UPN/ARN/object ID；示例不是格式穷举。 | TEXT自由文本；无已确认封闭枚举。 | identity_graph API create_node通过ORM写NodeCreate字段，包括last_activity；API读列表/详情。未确认独立实时身份评分或活动同步器，不能据列存在承诺自动维护。（S1、S2、S3、S4） |
| `display_name` | text / text；可NULL | 无默认 | 主体显示名称。 | TEXT自由文本；无已确认封闭枚举。 | identity_graph API create_node通过ORM写NodeCreate字段，包括last_activity；API读列表/详情。未确认独立实时身份评分或活动同步器，不能据列存在承诺自动维护。（S1、S2、S3、S4） |
| `source_system` | text / text；非NULL | 无默认 | 身份资料来源系统标识，如okta/azure_ad/aws_iam；无DB枚举。 | TEXT自由文本；无已确认封闭枚举。 | identity_graph API create_node通过ORM写NodeCreate字段，包括last_activity；API读列表/详情。未确认独立实时身份评分或活动同步器，不能据列存在承诺自动维护。（S1、S2、S3、S4） |
| `risk_score` | double precision / float8；非NULL | `0.0` | 身份风险分数，数据库限定0—100；本字段存在不证明已实现自动评分。 | DOUBLE PRECISION；DB CHECK 0..100。API仅float，数据库范围约束生效；未核自动评分来源。 | identity_graph API create_node通过ORM写NodeCreate字段，包括last_activity；API读列表/详情。未确认独立实时身份评分或活动同步器，不能据列存在承诺自动维护。（S1、S2、S3、S4） |
| `privilege_tier` | integer / int4；非NULL | `0` | 整数权限级别，0—3；与identity_privilege的文本tier不同。 | INTEGER；DB CHECK 0..3，迁移含义0=标准权限、1=提升权限、2=管理员、3=超级管理员。与identity_privilege.domain_admin不能自动一一等同。 | identity_graph API create_node通过ORM写NodeCreate字段，包括last_activity；API读列表/详情。未确认独立实时身份评分或活动同步器，不能据列存在承诺自动维护。（S1、S2、S3、S4） |
| `is_active` | boolean / bool；非NULL | `true` | 节点所代表主体是否启用；实际DB是boolean，不能沿当前ORM误写的String(10)理解成文本列。 | BOOLEAN：true=是/启用该标记，false=否/未启用；具体业务含义见本列说明。 | identity_graph API create_node通过ORM写NodeCreate字段，包括last_activity；API读列表/详情。未确认独立实时身份评分或活动同步器，不能据列存在承诺自动维护。（S1、S2、S3、S4、S5） |
| `last_activity` | timestamp with time zone / timestamptz；可NULL | 无默认 | 主体最近活动时间，NodeCreate可由调用者提供；未证明有后台自动更新器。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | identity_graph.NodeCreate包含last_activity，可在create_node时传入；未确认自动活动同步更新器。（S1、S2、S3、S4） |
| `attributes` | jsonb / jsonb；非NULL | `'{}'::jsonb` | 节点扩展属性JSON对象；API接受任意dict，不是封闭schema。 | JSON对象；对应API接收任意dict，未定义封闭子键/统一证据链接结构，DB未设JSON shape CHECK。 | identity_graph API create_node通过ORM写NodeCreate字段，包括last_activity；API读列表/详情。未确认独立实时身份评分或活动同步器，不能据列存在承诺自动维护。（S1、S2、S3、S4） |
| `created_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 身份节点记录创建时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | identity_graph API create_node通过ORM写NodeCreate字段，包括last_activity；API读列表/详情。未确认独立实时身份评分或活动同步器，不能据列存在承诺自动维护。（S1、S2、S3、S4） |
| `updated_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 身份节点记录更新时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | identity_graph API create_node通过ORM写NodeCreate字段，包括last_activity；API读列表/详情。未确认独立实时身份评分或活动同步器，不能据列存在承诺自动维护。（S1、S2、S3、S4） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `identity_nodes_node_type_check`：`CHECK ((node_type = ANY (ARRAY['human_user'::text, 'service_account'::text, 'device'::text, 'application'::text, 'group'::text, 'role'::text])))`
- `identity_nodes_privilege_tier_check`：`CHECK (((privilege_tier >= 0) AND (privilege_tier <= 3)))`
- `identity_nodes_risk_score_check`：`CHECK (((risk_score >= (0.0)::double precision) AND (risk_score <= (100.0)::double precision)))`
- `identity_nodes_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `identity_nodes_pkey`：`PRIMARY KEY (id)`
- `identity_nodes_tenant_id_source_system_external_id_key`：`UNIQUE (tenant_id, source_system, external_id)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/api/migrations/018_identity_graph.sql:8 ](../../../services/api/migrations/018_identity_graph.sql:8)
- S3：[ services/api/app/api/v1/endpoints/identity_graph.py:43 ](../../../services/api/app/api/v1/endpoints/identity_graph.py:43)
- S4：[ services/api/app/api/v1/endpoints/identity_graph.py:130 ](../../../services/api/app/api/v1/endpoints/identity_graph.py:130)
- S5：[ services/api/app/models/identity_graph.py:26 ](../../../services/api/app/models/identity_graph.py:26)

<a id="identity_edges"></a>

### 3.17 `identity_edges`

身份图有向关系；同租户source/target/type唯一。两端分别外键到节点，但这不是复合租户外键，查询仍需tenant条件。

字段数 **10**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `gen_random_uuid()` | 身份关系主键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | identity_graph create_edge通过ORM写Node/Edge请求合同；evidence为调用方对象，未推导统一证据ID关系。（S1、S2、S3、S4） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 关系所属租户，外键引用tenants。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | identity_graph create_edge通过ORM写Node/Edge请求合同；evidence为调用方对象，未推导统一证据ID关系。（S1、S2、S3、S4） |
| `source_id` | uuid / uuid；非NULL | 无默认 | 有向关系起点节点ID，外键引用identity_nodes。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | identity_graph create_edge通过ORM写Node/Edge请求合同；evidence为调用方对象，未推导统一证据ID关系。（S1、S2、S3、S4） |
| `target_id` | uuid / uuid；非NULL | 无默认 | 有向关系终点节点ID，外键引用identity_nodes。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | identity_graph create_edge通过ORM写Node/Edge请求合同；evidence为调用方对象，未推导统一证据ID关系。（S1、S2、S3、S4） |
| `edge_type` | text / text；非NULL | 无默认 | 有向关系类别，数据库CHECK限定；候选横向移动不等于确认攻击。 | DB CHECK封闭枚举：member_of=属于组；manages=管理；owns=拥有；delegates_to=委派给；authenticated_to=认证到；assumed_role=扮演角色；accessed=访问；created=创建；lateral_movement_candidate=候选横向移动关系（未确认）。 TEXT自由文本；无已确认封闭枚举。 | identity_graph create_edge通过ORM写Node/Edge请求合同；evidence为调用方对象，未推导统一证据ID关系。（S1、S2、S3、S4） |
| `weight` | double precision / float8；非NULL | `1.0` | 关系权重数值，默认1.0，无DB范围CHECK；API可提交float。 | DOUBLE PRECISION，默认1.0；无DB范围CHECK，API接受float；不是已确认概率。 | identity_graph create_edge通过ORM写Node/Edge请求合同；evidence为调用方对象，未推导统一证据ID关系。（S1、S2、S3、S4） |
| `valid_from` | timestamp with time zone / timestamptz；非NULL | `now()` | 关系有效起始时间，默认now；API EdgeCreate不直接接收此项。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | identity_graph create_edge通过ORM写Node/Edge请求合同；evidence为调用方对象，未推导统一证据ID关系。（S1、S2、S3、S4） |
| `valid_until` | timestamp with time zone / timestamptz；可NULL | 无默认 | 关系有效终止时间，可为空；不代表无效关系已自动清理。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | identity_graph create_edge通过ORM写Node/Edge请求合同；evidence为调用方对象，未推导统一证据ID关系。（S1、S2、S3、S4） |
| `evidence` | jsonb / jsonb；非NULL | `'{}'::jsonb` | 关系证据/来源对象，API接受任意dict；不能当统一调查结论支持合同。 | JSON对象；对应API接收任意dict，未定义封闭子键/统一证据链接结构，DB未设JSON shape CHECK。 | identity_graph create_edge通过ORM写Node/Edge请求合同；evidence为调用方对象，未推导统一证据ID关系。（S1、S2、S3、S4） |
| `created_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 关系记录创建时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | identity_graph create_edge通过ORM写Node/Edge请求合同；evidence为调用方对象，未推导统一证据ID关系。（S1、S2、S3、S4） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `identity_edges_edge_type_check`：`CHECK ((edge_type = ANY (ARRAY['member_of'::text, 'manages'::text, 'owns'::text, 'delegates_to'::text, 'authenticated_to'::text, 'assumed_role'::text, 'accessed'::text, 'created'::text, 'lateral_movement_candidate'::text])))`
- `identity_edges_source_id_fkey`：`FOREIGN KEY (source_id) REFERENCES identity_nodes(id) ON DELETE CASCADE`
- `identity_edges_target_id_fkey`：`FOREIGN KEY (target_id) REFERENCES identity_nodes(id) ON DELETE CASCADE`
- `identity_edges_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `identity_edges_pkey`：`PRIMARY KEY (id)`
- `identity_edges_tenant_id_source_id_target_id_edge_type_key`：`UNIQUE (tenant_id, source_id, target_id, edge_type)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/api/migrations/018_identity_graph.sql:37 ](../../../services/api/migrations/018_identity_graph.sql:37)
- S3：[ services/api/app/api/v1/endpoints/identity_graph.py:64 ](../../../services/api/app/api/v1/endpoints/identity_graph.py:64)
- S4：[ services/api/app/api/v1/endpoints/identity_graph.py:194 ](../../../services/api/app/api/v1/endpoints/identity_graph.py:194)

<a id="aisoc_context_statements"></a>

### 3.18 `aisoc_context_statements`

从结构化分析员反馈编译的可读组织经验陈述；按租户/理由/范围/范围值唯一，达到佐证门槛才更新。不是模型自动生成任意事实的表。

字段数 **10**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `uuid_generate_v4()` | 经验陈述记录主键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | analyst_feedback.record_disagreement统计DISTINCT analyst_id，compose_statement生成文本，UPSERT；active_statements过滤过期。（S1、S2、S3、S4） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 逻辑租户归属；catalog没有tenants外键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | analyst_feedback.record_disagreement统计DISTINCT analyst_id，compose_statement生成文本，UPSERT；active_statements过滤过期。（S1、S2、S3、S4） |
| `statement` | text / text；非NULL | 无默认 | 应用依据结构化理由及上下文生成的可读经验句，不等于独立核实安全事实。 | TEXT自由文本；无已确认封闭枚举。 | analyst_feedback.record_disagreement统计DISTINCT analyst_id，compose_statement生成文本，UPSERT；active_statements过滤过期。（S1、S2、S3、S4） |
| `reason_code` | text / text；非NULL | 无默认 | 编译陈述所依据的分析员理由代码；程序闭集，数据库自由text。 | 程序REASON_CODES闭集（DB没有CHECK）：known_admin_tool=已知合法管理工具；approved_pentest=获批渗透测试；expected_service_account=预期服务账号行为；known_scanner=已知授权扫描器；business_application=获准业务应用；bad_detection_logic=检测逻辑错误（转检测工程）；missing_context=缺失上下文（转检测工程）；true_positive_confirmed=确认真阳性。 | analyst_feedback.record_disagreement统计DISTINCT analyst_id，compose_statement生成文本，UPSERT；active_statements过滤过期。（S1、S2、S3、S4、S5） |
| `scope` | text / text；非NULL | 无默认 | 陈述作用范围类别；由理由代码映射，数据库未设CHECK。 | 程序理由映射闭集（DB没有CHECK）：rule=检测规则；entity=账号/主机实体；binary=进程或二进制；tenant=整个租户。 | analyst_feedback.record_disagreement统计DISTINCT analyst_id，compose_statement生成文本，UPSERT；active_statements过滤过期。（S1、S2、S3、S4、S5） |
| `scope_value` | text / text；非NULL | `''::text` | 具体适用规则/二进制/实体或tenant标识；不是固定外键。 | 程序取值：rule取context.rule_id或rule_name；binary取process_name或hash_sha256；entity取user_name或hostname；都没有则空字符串；tenant固定"tenant"。不是统一UUID格式。 | analyst_feedback.record_disagreement统计DISTINCT analyst_id，compose_statement生成文本，UPSERT；active_statements过滤过期。（S1、S2、S3、S4、S5） |
| `observations` | integer / int4；非NULL | `1` | 同理由/范围下不同分析员的佐证人数，不是反馈行数或事件数。 | INTEGER；当前程序COUNT(DISTINCT analyst_id)，DB无>=1 CHECK。门槛按reason为1或2，不是模型置信度。 | analyst_feedback.record_disagreement统计DISTINCT analyst_id，compose_statement生成文本，UPSERT；active_statements过滤过期。（S1、S2、S3、S4、S6） |
| `expires_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 陈述过期时间；NULL按程序表示永久，非空只读未过期项。 | TIMESTAMPTZ/NULL。当前理由TTL：approved_pentest 14天，expected_service_account 180天，known_scanner与business_application 365天，其余None=永久；读取仅保留NULL或>now。 | analyst_feedback.record_disagreement统计DISTINCT analyst_id，compose_statement生成文本，UPSERT；active_statements过滤过期。（S1、S2、S3、S4） |
| `created_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 陈述首次形成记录时刻。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | analyst_feedback.record_disagreement统计DISTINCT analyst_id，compose_statement生成文本，UPSERT；active_statements过滤过期。（S1、S2、S3、S4） |
| `updated_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 最近一次UPSERT重编译/佐证更新时刻。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | analyst_feedback.record_disagreement统计DISTINCT analyst_id，compose_statement生成文本，UPSERT；active_statements过滤过期。（S1、S2、S3、S4） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `aisoc_context_statements_pkey`：`PRIMARY KEY (id)`
- `uq_context_statement`：`UNIQUE (tenant_id, reason_code, scope, scope_value)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/api/migrations/052_analyst_feedback.sql:35 ](../../../services/api/migrations/052_analyst_feedback.sql:35)
- S3：[ services/api/app/services/analyst_feedback.py:237 ](../../../services/api/app/services/analyst_feedback.py:237)
- S4：[ services/api/app/services/analyst_feedback.py:331 ](../../../services/api/app/services/analyst_feedback.py:331)
- S5：[ services/api/app/services/analyst_feedback.py:72 ](../../../services/api/app/services/analyst_feedback.py:72)
- S6：[ services/api/app/services/analyst_feedback.py:293 ](../../../services/api/app/services/analyst_feedback.py:293)

<a id="aisoc_analyst_feedback"></a>

### 3.19 `aisoc_analyst_feedback`

结构化分析员判定反馈的逐条记录，保留原AI判定、人工判定、理由与上下文，供经验陈述统计。catalog无tenant/alert/users外键。

字段数 **12**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `uuid_generate_v4()` | 反馈记录主键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | feedback override路径收集告警上下文并调用analyst_feedback.record_disagreement插入；API校验人工判定/理由。（S1、S2、S3、S4） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 反馈所属逻辑租户UUID，无DB外键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | feedback override路径收集告警上下文并调用analyst_feedback.record_disagreement插入；API校验人工判定/理由。（S1、S2、S3、S4） |
| `alert_id` | uuid / uuid；可NULL | 无默认 | 被反馈告警UUID，无DB外键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | feedback override路径收集告警上下文并调用analyst_feedback.record_disagreement插入；API校验人工判定/理由。（S1、S2、S3、S4） |
| `ai_disposition` | text / text；非NULL | 无默认 | 反馈发生时保存的原AI/告警判定，可能为空；不等于后续最新调查结论。 | 自由文本/可空；该入口写请求original_verdict，本轮只确认corrected_verdict闭集校验，不能把人工判定集合当DB原判定枚举。 | feedback override路径收集告警上下文并调用analyst_feedback.record_disagreement插入；API校验人工判定/理由。（S1、S2、S3、S4） |
| `analyst_disposition` | text / text；非NULL | 无默认 | 分析员提交的新判定，API校验特定集合；不等于告警status。 | 反馈API corrected_verdict校验集合，DB无CHECK：true_positive=真阳性；benign_true_positive=良性真阳性/合法活动命中；false_positive=误报；benign=旧有良性标签；escalate=升级处理。 | feedback override路径收集告警上下文并调用analyst_feedback.record_disagreement插入；API校验人工判定/理由。（S1、S2、S3、S4） |
| `reason_code` | text / text；非NULL | 无默认 | 分析员给出的结构化理由代码，程序字典校验。 | 程序REASON_CODES闭集（DB没有CHECK）：known_admin_tool=已知合法管理工具；approved_pentest=获批渗透测试；expected_service_account=预期服务账号行为；known_scanner=已知授权扫描器；business_application=获准业务应用；bad_detection_logic=检测逻辑错误（转检测工程）；missing_context=缺失上下文（转检测工程）；true_positive_confirmed=确认真阳性。 | feedback override路径收集告警上下文并调用analyst_feedback.record_disagreement插入；API校验人工判定/理由。（S1、S2、S3、S4、S5） |
| `scope` | text / text；非NULL | 无默认 | 理由对应的作用范围，由服务从reason_code确定。 | 程序理由映射闭集（DB没有CHECK）：rule=检测规则；entity=账号/主机实体；binary=进程或二进制；tenant=整个租户。 | feedback override路径收集告警上下文并调用analyst_feedback.record_disagreement插入；API校验人工判定/理由。（S1、S2、S3、S4、S5） |
| `scope_value` | text / text；非NULL | `''::text` | 根据context选出的范围键；同context_statements的聚合键。 | 程序取值：rule取context.rule_id或rule_name；binary取process_name或hash_sha256；entity取user_name或hostname；都没有则空字符串；tenant固定"tenant"。不是统一UUID格式。 | feedback override路径收集告警上下文并调用analyst_feedback.record_disagreement插入；API校验人工判定/理由。（S1、S2、S3、S4、S5） |
| `analyst_id` | text / text；非NULL | 无默认 | 分析员身份文本，用于DISTINCT佐证人数统计；非users外键。 | TEXT。调用方user.user_id以文本传递，用于去重统计；非外键。 | feedback override路径收集告警上下文并调用analyst_feedback.record_disagreement插入；API校验人工判定/理由。（S1、S2、S3、S4） |
| `note` | text / text；非NULL | `''::text` | 分析员补充说明自由文本。 | TEXT自由文本；无已确认封闭枚举。 | feedback override路径收集告警上下文并调用analyst_feedback.record_disagreement插入；API校验人工判定/理由。（S1、S2、S3、S4） |
| `context` | jsonb / jsonb；非NULL | `'{}'::jsonb` | 生成/限定经验陈述的告警背景对象；当前反馈路径提供有限规则/主机/用户/进程/哈希字段。 | JSON对象。当前_statement_context构造rule_id、rule_name、hostname、user_name、process_name、hash_sha256（值可空）；通用record_disagreement接受dict，compose_statement还可读time_window。不是DB JSON schema约束。 | feedback override路径收集告警上下文并调用analyst_feedback.record_disagreement插入；API校验人工判定/理由。（S1、S2、S3、S4） |
| `created_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 反馈记录写入时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | feedback override路径收集告警上下文并调用analyst_feedback.record_disagreement插入；API校验人工判定/理由。（S1、S2、S3、S4） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `aisoc_analyst_feedback_pkey`：`PRIMARY KEY (id)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/api/migrations/052_analyst_feedback.sql:9 ](../../../services/api/migrations/052_analyst_feedback.sql:9)
- S3：[ services/api/app/api/v1/endpoints/feedback.py:94 ](../../../services/api/app/api/v1/endpoints/feedback.py:94)
- S4：[ services/api/app/services/analyst_feedback.py:266 ](../../../services/api/app/services/analyst_feedback.py:266)
- S5：[ services/api/app/services/analyst_feedback.py:72 ](../../../services/api/app/services/analyst_feedback.py:72)

<a id="aisoc_kb_documents"></a>

### 3.20 `aisoc_kb_documents`

知识库文本分块表，一行一个chunk。每个chunk独立UUID；同一次导入共享标题等资料，未见独立父document_id，不能把id当整篇文档公共ID。

字段数 **12**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `gen_random_uuid()` | 当前知识文本块UUID，每块独立生成。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | knowledge_base.ingest将content切块并逐行INSERT；搜索按content全文检索，列表偏重chunk_index=0。（S1、S2、S3、S4） |
| `tenant_id` | uuid / uuid；可NULL | 无默认 | 文本块逻辑租户归属；catalog无tenants外键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | knowledge_base.ingest将content切块并逐行INSERT；搜索按content全文检索，列表偏重chunk_index=0。（S1、S2、S3、S4） |
| `title` | text / text；非NULL | 无默认 | 该块所属导入资料标题，多块重复保存。 | TEXT自由文本；无已确认封闭枚举。 | knowledge_base.ingest将content切块并逐行INSERT；搜索按content全文检索，列表偏重chunk_index=0。（S1、S2、S3、S4） |
| `source_url` | text / text；可NULL | 无默认 | 来源链接文本；可为空，不等于已验证可访问来源。 | TEXT自由文本；无已确认封闭枚举。 | knowledge_base.ingest将content切块并逐行INSERT；搜索按content全文检索，列表偏重chunk_index=0。（S1、S2、S3、S4） |
| `doc_kind` | text / text；非NULL | `'runbook'::text` | 资料类别，数据库CHECK及API Literal限定。 | DB CHECK封闭枚举：runbook=运行手册；policy=策略/政策；playbook=处置剧本；sop=标准操作流程；wiki=知识Wiki；other=其他。 TEXT自由文本；无已确认封闭枚举。 | knowledge_base.ingest将content切块并逐行INSERT；搜索按content全文检索，列表偏重chunk_index=0。（S1、S2、S3、S4） |
| `content` | text / text；非NULL | 无默认 | 当前chunk文本，不一定是整篇原文。 | TEXT自由文本；无已确认封闭枚举。 | knowledge_base.ingest将content切块并逐行INSERT；搜索按content全文检索，列表偏重chunk_index=0。（S1、S2、S3、S4） |
| `chunk_index` | integer / int4；可NULL | `0` | 该次导入中的分块序号，程序从0开始；DB未设非负CHECK。 | INTEGER整数；除下列CHECK外无已确认范围约束。 | knowledge_base.ingest将content切块并逐行INSERT；搜索按content全文检索，列表偏重chunk_index=0。（S1、S2、S3、S4） |
| `chunk_total` | integer / int4；可NULL | `1` | 本次导入的总分块数，每块重复写入；DB未设正数CHECK。 | INTEGER整数；除下列CHECK外无已确认范围约束。 | knowledge_base.ingest将content切块并逐行INSERT；搜索按content全文检索，列表偏重chunk_index=0。（S1、S2、S3、S4） |
| `tags` | ARRAY / _text；可NULL | `ARRAY[]::text[]` | 知识资料标签text数组。 | TEXT[]字符串数组；元素未见数据库格式/封闭枚举约束。 | knowledge_base.ingest将content切块并逐行INSERT；搜索按content全文检索，列表偏重chunk_index=0。（S1、S2、S3、S4） |
| `created_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 知识块写入时间，同次导入由程序使用同一now。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | knowledge_base.ingest将content切块并逐行INSERT；搜索按content全文检索，列表偏重chunk_index=0。（S1、S2、S3、S4） |
| `updated_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 知识块更新时点，导入时同created_at；未据此承诺已有编辑流程。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | knowledge_base.ingest将content切块并逐行INSERT；搜索按content全文检索，列表偏重chunk_index=0。（S1、S2、S3、S4） |
| `created_by` | text / text；可NULL | 无默认 | 导入者文本身份，当前API写user.email，兜底system，不是users UUID外键。 | TEXT自由文本；无已确认封闭枚举。 | knowledge_base.ingest将content切块并逐行INSERT；搜索按content全文检索，列表偏重chunk_index=0。（S1、S2、S3、S4） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `aisoc_kb_documents_doc_kind_check`：`CHECK ((doc_kind = ANY (ARRAY['runbook'::text, 'policy'::text, 'playbook'::text, 'sop'::text, 'wiki'::text, 'other'::text])))`
- `aisoc_kb_documents_pkey`：`PRIMARY KEY (id)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/api/migrations/016_knowledge_base.sql:4 ](../../../services/api/migrations/016_knowledge_base.sql:4)
- S3：[ services/api/app/api/v1/endpoints/knowledge_base.py:226 ](../../../services/api/app/api/v1/endpoints/knowledge_base.py:226)
- S4：[ services/api/app/api/v1/endpoints/knowledge_base.py:232 ](../../../services/api/app/api/v1/endpoints/knowledge_base.py:232)

<a id="aisoc_tenant_skills"></a>

### 3.21 `aisoc_tenant_skills`

租户技能当前状态，一租户一个skill_id一行；与版本表分开。技能body用于程序读取，source_yaml用于保留作者文本。

字段数 **18**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `gen_random_uuid()` | 当前技能行UUID。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 技能所属租户，外键引用tenants。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4） |
| `skill_id` | text / text；非NULL | 无默认 | 作者提供、跨版本稳定的kebab-case技能标识，数据库正则限定。 | DB CHECK正则^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$：总长3—63，小写字母/数字/中划线，首尾须字母或数字。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4） |
| `version` | integer / int4；非NULL | `1` | 服务端分配的内容版本，初始1；解析body变更才递增，YAML纯格式变化不递增。 | INTEGER，DB CHECK >=1；应用仅解析body变更时递增，格式化YAML不递增。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4） |
| `status` | text / text；非NULL | `'draft'::text` | 技能生命周期状态，数据库CHECK限定；激活还有回放引用/版本约束。 | DB CHECK封闭枚举：draft=草稿；backtested=已关联回放评估；active=已激活；retired=已退役。 TEXT自由文本；无已确认封闭枚举。 激活还需两个回放ID与版本检查；DB三值逻辑边界见backtest_version，不能把应用校验当纯DB强制。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4） |
| `name` | text / text；非NULL | 无默认 | 技能显示名称。 | TEXT自由文本；无已确认封闭枚举。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4） |
| `owner` | text / text；非NULL | 无默认 | 技能负责人的文本标识，供追问业务规则；不是users外键。 | 自由TEXT、应用要求非空负责人，非users外键，不保证是邮箱。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4） |
| `expires_at` | timestamp with time zone / timestamptz；非NULL | 无默认 | 技能到期/复审时刻，非空；解析/解析器读取排除过期技能。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4） |
| `body` | jsonb / jsonb；非NULL | 无默认 | 解析后的技能对象，实际运行读取源，不从当前YAML重新推测。 | JSON对象；TenantSkill.as_dict确认键id、name、owner、expires_at(ISO时间字符串)、applies_when、match{techniques,rule_ids,sources,keywords:字符串数组}、guidance、verdict_guidance、required_evidence、escalate_when、plan、expected_pivots(各字符串数组)、min_pivots(整数)。这是应用schema，DB无JSON schema CHECK。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4、S5） |
| `source_yaml` | text / text；非NULL | 无默认 | 原作者YAML文本，保留编辑格式/注释；不是JSON。 | UTF-8 YAML文本，作者格式/注释保留；应用解析器校验，DB TEXT不验证YAML。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4） |
| `backtest_evaluation_id` | uuid / uuid；可NULL | 无默认 | 候选技能回放评估ID，外键引用aisoc_replay_evaluations。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4） |
| `backtest_baseline_id` | uuid / uuid；可NULL | 无默认 | 比较基线回放评估ID，外键引用同表。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4） |
| `backtest_version` | integer / int4；可NULL | 无默认 | 挂接回放评估时对应的技能内容版本；修改body后清空。 | INTEGER/NULL；DB active CHECK比较backtest_version=version，且要求两个评估ID非空。SQL CHECK对NULL表达式可返回UNKNOWN，不能把该CHECK独自描述成backtest_version强制非空；store.activate另行比较并拒绝不匹配。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4） |
| `activated_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 当前版本最近激活时刻，内容修改时清空。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4） |
| `activated_by` | uuid / uuid；可NULL | 无默认 | 激活人users UUID，可空，用户删除时置空。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4） |
| `created_by` | uuid / uuid；可NULL | 无默认 | 最初作者users UUID，可空，用户删除时置空。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4） |
| `created_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 当前技能行创建时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4） |
| `updated_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 技能保存/状态等最近更新时刻。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | tenant_skills.store保存/内容变更递增版本、挂回放结果、激活/退役；当前schema与store均核到。（S1、S2、S3、S4） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `aisoc_tenant_skills_active_is_backtested`：`CHECK (((status <> 'active'::text) OR ((backtest_evaluation_id IS NOT NULL) AND (backtest_baseline_id IS NOT NULL) AND (backtest_version = version))))`
- `aisoc_tenant_skills_skill_id_check`：`CHECK ((skill_id ~ '^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$'::text))`
- `aisoc_tenant_skills_status_check`：`CHECK ((status = ANY (ARRAY['draft'::text, 'backtested'::text, 'active'::text, 'retired'::text])))`
- `aisoc_tenant_skills_version_check`：`CHECK ((version >= 1))`
- `aisoc_tenant_skills_activated_by_fkey`：`FOREIGN KEY (activated_by) REFERENCES users(id) ON DELETE SET NULL`
- `aisoc_tenant_skills_backtest_baseline_id_fkey`：`FOREIGN KEY (backtest_baseline_id) REFERENCES aisoc_replay_evaluations(id) ON DELETE SET NULL`
- `aisoc_tenant_skills_backtest_evaluation_id_fkey`：`FOREIGN KEY (backtest_evaluation_id) REFERENCES aisoc_replay_evaluations(id) ON DELETE SET NULL`
- `aisoc_tenant_skills_created_by_fkey`：`FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL`
- `aisoc_tenant_skills_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `aisoc_tenant_skills_pkey`：`PRIMARY KEY (id)`
- `aisoc_tenant_skills_tenant_id_skill_id_key`：`UNIQUE (tenant_id, skill_id)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/api/migrations/070_tenant_skills.sql:53 ](../../../services/api/migrations/070_tenant_skills.sql:53)
- S3：[ services/api/app/services/tenant_skills/store.py:174 ](../../../services/api/app/services/tenant_skills/store.py:174)
- S4：[ services/api/app/services/tenant_skills/models.py:147 ](../../../services/api/app/services/tenant_skills/models.py:147)
- S5：[ services/api/app/services/tenant_skills/models.py:183 ](../../../services/api/app/services/tenant_skills/models.py:183)

<a id="aisoc_tenant_skill_versions"></a>

### 3.22 `aisoc_tenant_skill_versions`

技能内容版本快照，(tenant_id,skill_id,version)唯一；内容新增版本，回放引用/激活/退役戳可后补，因此不能称每列绝不更新。

字段数 **17**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `gen_random_uuid()` | 技能历史版本记录UUID。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | store._record_version复制当前body及作者资料；_stamp_version补回放、激活、退役信息。（S1、S2、S3、S4） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 版本所属租户，外键引用tenants。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | store._record_version复制当前body及作者资料；_stamp_version补回放、激活、退役信息。（S1、S2、S3、S4） |
| `skill_row_id` | uuid / uuid；非NULL | 无默认 | 当前技能行引用，外键aisoc_tenant_skills，删除当前行级联历史。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | store._record_version复制当前body及作者资料；_stamp_version补回放、激活、退役信息。（S1、S2、S3、S4） |
| `skill_id` | text / text；非NULL | 无默认 | 作者稳定技能标识快照；版本表无与当前表相同的正则CHECK。 | TEXT自由文本；无已确认封闭枚举。 | store._record_version复制当前body及作者资料；_stamp_version补回放、激活、退役信息。（S1、S2、S3、S4） |
| `version` | integer / int4；非NULL | 无默认 | 该历史内容版本号，数据库限定>=1。 | INTEGER，DB CHECK >=1；唯一键(tenant_id,skill_id,version)。 | store._record_version复制当前body及作者资料；_stamp_version补回放、激活、退役信息。（S1、S2、S3、S4） |
| `name` | text / text；非NULL | 无默认 | 该版显示名称快照。 | TEXT自由文本；无已确认封闭枚举。 | store._record_version复制当前body及作者资料；_stamp_version补回放、激活、退役信息。（S1、S2、S3、S4） |
| `owner` | text / text；非NULL | 无默认 | 该版负责人文本快照。 | 自由TEXT、应用要求非空负责人，非users外键，不保证是邮箱。 | store._record_version复制当前body及作者资料；_stamp_version补回放、激活、退役信息。（S1、S2、S3、S4） |
| `expires_at` | timestamp with time zone / timestamptz；非NULL | 无默认 | 该版技能过期时点快照。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | store._record_version复制当前body及作者资料；_stamp_version补回放、激活、退役信息。（S1、S2、S3、S4） |
| `body` | jsonb / jsonb；非NULL | 无默认 | 该版解析后的技能内容快照。 | JSON对象；TenantSkill.as_dict确认键id、name、owner、expires_at(ISO时间字符串)、applies_when、match{techniques,rule_ids,sources,keywords:字符串数组}、guidance、verdict_guidance、required_evidence、escalate_when、plan、expected_pivots(各字符串数组)、min_pivots(整数)。这是应用schema，DB无JSON schema CHECK。 | store._record_version复制当前body及作者资料；_stamp_version补回放、激活、退役信息。（S1、S2、S3、S4、S5） |
| `source_yaml` | text / text；非NULL | 无默认 | 记录该内容版本时保存的YAML；当前行纯格式再保存不一定回写该快照。 | UTF-8 YAML文本，作者格式/注释保留；应用解析器校验，DB TEXT不验证YAML。 | store._record_version复制当前body及作者资料；_stamp_version补回放、激活、退役信息。（S1、S2、S3、S4） |
| `backtest_evaluation_id` | uuid / uuid；可NULL | 无默认 | 该版挂接的候选回放评估引用，可后补。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | store._record_version复制当前body及作者资料；_stamp_version补回放、激活、退役信息。（S1、S2、S3、S4、S4） |
| `backtest_baseline_id` | uuid / uuid；可NULL | 无默认 | 该版挂接的基线回放评估引用，可后补。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | store._record_version复制当前body及作者资料；_stamp_version补回放、激活、退役信息。（S1、S2、S3、S4、S4） |
| `authored_by` | uuid / uuid；可NULL | 无默认 | 该版作者users UUID，可空，用户删除置空。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | store._record_version复制当前body及作者资料；_stamp_version补回放、激活、退役信息。（S1、S2、S3、S4） |
| `authored_at` | timestamp with time zone / timestamptz；非NULL | `now()` | 该内容版本生成/写入时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | store._record_version复制当前body及作者资料；_stamp_version补回放、激活、退役信息。（S1、S2、S3、S4） |
| `activated_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 该版激活时间戳，可后补。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | store._record_version复制当前body及作者资料；_stamp_version补回放、激活、退役信息。（S1、S2、S3、S4、S4） |
| `activated_by` | uuid / uuid；可NULL | 无默认 | 激活该版的人users UUID，可空。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | store._record_version复制当前body及作者资料；_stamp_version补回放、激活、退役信息。（S1、S2、S3、S4、S4） |
| `retired_at` | timestamp with time zone / timestamptz；可NULL | 无默认 | 该版退役时间戳，可后补；不是删除时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | store._record_version复制当前body及作者资料；_stamp_version补回放、激活、退役信息。（S1、S2、S3、S4、S4） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `aisoc_tenant_skill_versions_version_check`：`CHECK ((version >= 1))`
- `aisoc_tenant_skill_versions_activated_by_fkey`：`FOREIGN KEY (activated_by) REFERENCES users(id) ON DELETE SET NULL`
- `aisoc_tenant_skill_versions_authored_by_fkey`：`FOREIGN KEY (authored_by) REFERENCES users(id) ON DELETE SET NULL`
- `aisoc_tenant_skill_versions_backtest_baseline_id_fkey`：`FOREIGN KEY (backtest_baseline_id) REFERENCES aisoc_replay_evaluations(id) ON DELETE SET NULL`
- `aisoc_tenant_skill_versions_backtest_evaluation_id_fkey`：`FOREIGN KEY (backtest_evaluation_id) REFERENCES aisoc_replay_evaluations(id) ON DELETE SET NULL`
- `aisoc_tenant_skill_versions_skill_row_id_fkey`：`FOREIGN KEY (skill_row_id) REFERENCES aisoc_tenant_skills(id) ON DELETE CASCADE`
- `aisoc_tenant_skill_versions_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `aisoc_tenant_skill_versions_pkey`：`PRIMARY KEY (id)`
- `aisoc_tenant_skill_versions_tenant_id_skill_id_version_key`：`UNIQUE (tenant_id, skill_id, version)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/api/migrations/070_tenant_skills.sql:132 ](../../../services/api/migrations/070_tenant_skills.sql:132)
- S3：[ services/api/app/services/tenant_skills/store.py:222 ](../../../services/api/app/services/tenant_skills/store.py:222)
- S4：[ services/api/app/services/tenant_skills/store.py:291 ](../../../services/api/app/services/tenant_skills/store.py:291)
- S5：[ services/api/app/services/tenant_skills/models.py:183 ](../../../services/api/app/services/tenant_skills/models.py:183)

<a id="ueba_entity_baselines"></a>

### 3.23 `ueba_entity_baselines`

实体的逐特征在线行为基线；非实体总名单，只有被送入处理的实体会形成记录。catalog没有tenant+entity唯一约束或tenant外键。

字段数 **11**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `gen_random_uuid()` | 实体基线记录UUID。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | BaselineService.get_or_create/update写feature_stats与窗口；本库observation_count/created_at存在但当前ORM未映射，不能推定观测计数已被维护。（S1、S2、S3、S4、S5） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 基线逻辑租户归属，catalog无tenants外键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | BaselineService.get_or_create/update写feature_stats与窗口；本库observation_count/created_at存在但当前ORM未映射，不能推定观测计数已被维护。（S1、S2、S3、S4、S5） |
| `entity_type` | character varying / varchar；非NULL | 无默认 | 被建模实体类型，HTTP API有枚举约定，DB没有CHECK。 | UEBA HTTP API实体类型约定（DB无CHECK，非所有旁路writer强制）：user=用户；device=设备；ip=IP地址；service_account=服务账号；ai_agent=AI智能体；mcp_server=MCP服务。 | BaselineService.get_or_create/update写feature_stats与窗口；本库observation_count/created_at存在但当前ORM未映射，不能推定观测计数已被维护。（S1、S2、S3、S4、S5、S6） |
| `entity_id` | character varying / varchar；非NULL | 无默认 | 来源提供的实体标识文本，不是assets/users外键。 | VARCHAR自由文本；catalog未记录字符长度；无已确认封闭枚举。 | BaselineService.get_or_create/update写feature_stats与窗口；本库observation_count/created_at存在但当前ORM未映射，不能推定观测计数已被维护。（S1、S2、S3、S4、S5） |
| `feature_stats` | jsonb / jsonb；非NULL | `'{}'::jsonb` | 各特征Welford累计统计对象，不是每次观测原文。 | JSON对象：{特征名:{mean:均值,M2:离均差平方和,count:该特征观测数,std:样本标准差}}；特征名开放，Welford累计更新，DB无JSON shape CHECK。 | BaselineService.get_or_create/update写feature_stats与窗口；本库observation_count/created_at存在但当前ORM未映射，不能推定观测计数已被维护。（S1、S2、S3、S4、S5、S4） |
| `window_start` | timestamp with time zone / timestamptz；非NULL | 无默认 | 创建基线时now减baseline_window_days的窗口标记；当前update不移动起点/剔除旧样本，不可宣称严格滑动窗口。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | BaselineService.get_or_create/update写feature_stats与窗口；本库observation_count/created_at存在但当前ORM未映射，不能推定观测计数已被维护。（S1、S2、S3、S4、S5） |
| `window_end` | timestamp with time zone / timestamptz；非NULL | 无默认 | 最近一次基线update的处理时刻，不是输入事件原时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | BaselineService.get_or_create/update写feature_stats与窗口；本库observation_count/created_at存在但当前ORM未映射，不能推定观测计数已被维护。（S1、S2、S3、S4、S5） |
| `observation_count` | integer / int4；非NULL | `0` | 迁移预留的观测次数列，DB默认0；当前ORM未映射/常规update未写，不能据此判断真实样本数。 | INTEGER，DB默认0，当前ORM未映射、常规BaselineService不更新。要看实际样本数应按feature_stats[feature].count，不能拿这列0判断无样本。 | BaselineService.get_or_create/update写feature_stats与窗口；本库observation_count/created_at存在但当前ORM未映射，不能推定观测计数已被维护。（S1、S2、S3、S4、S5） |
| `created_at` | timestamp with time zone / timestamptz；可NULL | `now()` | 数据库基线记录创建时间；当前ORM未映射，使用DB默认。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | BaselineService.get_or_create/update写feature_stats与窗口；本库observation_count/created_at存在但当前ORM未映射，不能推定观测计数已被维护。（S1、S2、S3、S4、S5） |
| `updated_at` | timestamp with time zone / timestamptz；可NULL | `now()` | 基线ORM更新时点。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | BaselineService.get_or_create/update写feature_stats与窗口；本库observation_count/created_at存在但当前ORM未映射，不能推定观测计数已被维护。（S1、S2、S3、S4、S5） |
| `peer_group_id` | character varying / varchar；可NULL | 无默认 | 可选同伴组标识；不是成员ID逗号列表。当前baseline update未写本列，不能自动推定已关联分组。 | 自由VARCHAR/NULL，逻辑组ID无FK；当前BaselineService.get_or_create/update未写该列。ORM旧注释“逗号分隔实体ID”与PeerGroup实际用途不一致，不采纳。 | BaselineService.get_or_create/update写feature_stats与窗口；本库observation_count/created_at存在但当前ORM未映射，不能推定观测计数已被维护。（S1、S2、S3、S4、S5） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `ueba_entity_baselines_pkey`：`PRIMARY KEY (id)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/ueba/app/models/ueba.py:24 ](../../../services/ueba/app/models/ueba.py:24)
- S3：[ services/ueba/app/services/baseline.py:132 ](../../../services/ueba/app/services/baseline.py:132)
- S4：[ services/ueba/app/services/baseline.py:25 ](../../../services/ueba/app/services/baseline.py:25)
- S5：[ services/ueba/alembic/versions/0004_baseline_peer_group_and_column_parity.py:33 ](../../../services/ueba/alembic/versions/0004_baseline_peer_group_and_column_parity.py:33)
- S6：[ services/ueba/app/api/routes.py:73 ](../../../services/ueba/app/api/routes.py:73)

<a id="ueba_anomalies"></a>

### 3.24 `ueba_anomalies`

UEBA评分达到阈值后持久化的异常记录；低于阈值不建此行，不等于全部事件或所有实体状态。

字段数 **14**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid / uuid；非NULL | `gen_random_uuid()` | 异常记录UUID。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | ScoringService.score_event写异常；API ack更新acknowledged。z_scores为存在但当前ORM未映射列，实际逐特征分数在features。（S1、S2、S3、S4） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 异常所属逻辑租户UUID，catalog无外键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | ScoringService.score_event写异常；API ack更新acknowledged。z_scores为存在但当前ORM未映射列，实际逐特征分数在features。（S1、S2、S3、S4） |
| `entity_type` | character varying / varchar；非NULL | 无默认 | 异常所关联实体类别，DB没有CHECK。 | UEBA HTTP API实体类型约定（DB无CHECK，非所有旁路writer强制）：user=用户；device=设备；ip=IP地址；service_account=服务账号；ai_agent=AI智能体；mcp_server=MCP服务。 | ScoringService.score_event写异常；API ack更新acknowledged。z_scores为存在但当前ORM未映射列，实际逐特征分数在features。（S1、S2、S3、S4、S5） |
| `entity_id` | character varying / varchar；非NULL | 无默认 | 来源实体标识，不是assets/users外键。 | VARCHAR自由文本；catalog未记录字符长度；无已确认封闭枚举。 | ScoringService.score_event写异常；API ack更新acknowledged。z_scores为存在但当前ORM未映射列，实际逐特征分数在features。（S1、S2、S3、S4） |
| `event_type` | character varying / varchar；非NULL | 无默认 | 触发评分的事件类型标签；可由源事件/OCSF字段派生，非封闭枚举。 | VARCHAR自由文本；catalog未记录字符长度；无已确认封闭枚举。 | ScoringService.score_event写异常；API ack更新acknowledged。z_scores为存在但当前ORM未映射列，实际逐特征分数在features。（S1、S2、S3、S4） |
| `anomaly_score` | double precision / float8；非NULL | 无默认 | 特征z-score合成值，可与同伴组偏离平均；程序上限10，不是概率或风险百分比。 | DOUBLE PRECISION；程序先sqrt(sum(z²))封顶10，有同伴分数时两者平均；只有>=配置anomaly_threshold才落异常行，DB无范围CHECK。 | ScoringService.score_event写异常；API ack更新acknowledged。z_scores为存在但当前ORM未映射列，实际逐特征分数在features。（S1、S2、S3、S4） |
| `risk_level` | character varying / varchar；非NULL | 无默认 | 程序按合成分数映射的风险等级；DB自由varchar。 | 程序分类（DB无CHECK）：critical=合成分>=6；high=4<=分<6；medium=未达4但>=配置anomaly_threshold；low=剩余。由于低于anomaly_threshold通常不落异常表，不能宣称所有等级都有样例。 | ScoringService.score_event写异常；API ack更新acknowledged。z_scores为存在但当前ORM未映射列，实际逐特征分数在features。（S1、S2、S3、S4） |
| `features` | jsonb / jsonb；非NULL | `'{}'::jsonb` | 本次各特征观测值和基线mean/std/z_score对象；不可评分z_score可为null。 | JSON对象：{特征名:{value:本次观测值,mean:基线均值,std:基线标准差,z_score:偏离值或null}}；特征名开放，null表示不可评分，不填0。 | ScoringService.score_event写异常；API ack更新acknowledged。z_scores为存在但当前ORM未映射列，实际逐特征分数在features。（S1、S2、S3、S4） |
| `z_scores` | jsonb / jsonb；非NULL | `'{}'::jsonb` | 迁移保留的独立JSON列；当前ORM/ScoringService不写，默认{}不是证据“无异常”。 | JSONB默认{}；当前ORM未映射/ScoringService未写此列，实际z-score在features[特征].z_score。不能仅凭默认{}判断没算分。 | ScoringService.score_event写异常；API ack更新acknowledged。z_scores为存在但当前ORM未映射列，实际逐特征分数在features。（S1、S2、S3、S4） |
| `peer_group_id` | character varying / varchar；可NULL | 无默认 | 本次评分使用/请求的同伴组标识，可为空，无FK。 | VARCHAR自由文本；catalog未记录字符长度；无已确认封闭枚举。 | ScoringService.score_event写异常；API ack更新acknowledged。z_scores为存在但当前ORM未映射列，实际逐特征分数在features。（S1、S2、S3、S4） |
| `peer_deviation_score` | double precision / float8；可NULL | 无默认 | 同伴组偏离分数；样本/方差不足等不可评分时为空，不补0。 | DOUBLE PRECISION/NULL，程序RSS封顶10；组不存在/样本不足/无可评分特征返回NULL；DB无范围CHECK。 | ScoringService.score_event写异常；API ack更新acknowledged。z_scores为存在但当前ORM未映射列，实际逐特征分数在features。（S1、S2、S3、S4） |
| `source_event_id` | character varying / varchar；可NULL | 无默认 | 触发异常的来源事件标识文本，可空，无外键。 | VARCHAR自由文本；catalog未记录字符长度；无已确认封闭枚举。 | ScoringService.score_event写异常；API ack更新acknowledged。z_scores为存在但当前ORM未映射列，实际逐特征分数在features。（S1、S2、S3、S4） |
| `detected_at` | timestamp with time zone / timestamptz；可NULL | `now()` | 异常记录生成时点，DB默认now，不必等于源事件发生时间。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | ScoringService.score_event写异常；API ack更新acknowledged。z_scores为存在但当前ORM未映射列，实际逐特征分数在features。（S1、S2、S3、S4） |
| `acknowledged` | boolean / bool；非NULL | `false` | 异常是否被API人工确认；true不自动表示风险已消除。 | BOOLEAN：true=是/启用该标记，false=否/未启用；具体业务含义见本列说明。 | ScoringService.score_event写异常；API ack更新acknowledged。z_scores为存在但当前ORM未映射列，实际逐特征分数在features。（S1、S2、S3、S4、S6） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `ueba_anomalies_pkey`：`PRIMARY KEY (id)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/ueba/app/models/ueba.py:52 ](../../../services/ueba/app/models/ueba.py:52)
- S3：[ services/ueba/app/services/scoring.py:115 ](../../../services/ueba/app/services/scoring.py:115)
- S4：[ services/ueba/alembic/versions/0004_baseline_peer_group_and_column_parity.py:33 ](../../../services/ueba/alembic/versions/0004_baseline_peer_group_and_column_parity.py:33)
- S5：[ services/ueba/app/api/routes.py:73 ](../../../services/ueba/app/api/routes.py:73)
- S6：[ services/ueba/app/api/routes.py:180 ](../../../services/ueba/app/api/routes.py:180)

<a id="ueba_peer_groups"></a>

### 3.25 `ueba_peer_groups`

外部指定的同伴组统计；id为文本主键且catalog为全表唯一，并非(tenant,id)复合主键。

字段数 **8**；2026-10-22 22:56样例租户行数 **0**。

| 字段 | SQL类型 / 可NULL | 数据库默认 | 业务含义 | 取值、格式与约束层级 | 写入/使用及依据 |
| --- | --- | --- | --- | --- | --- |
| `id` | character varying / varchar；非NULL | 无默认 | 外部指定同伴组标识；如部门/角色/网段组，text主键全表唯一，不是UUID。 | VARCHAR自由文本；catalog未记录字符长度；无已确认封闭枚举。 | PeerGroupService按租户与组ID读、创建/累计统计；当前member_count取首个特征count，不能解释为去重成员人数。（S1、S2、S3、S4） |
| `tenant_id` | uuid / uuid；非NULL | 无默认 | 所属逻辑租户，catalog无tenants外键。 | UUID；格式xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx。 | PeerGroupService按租户与组ID读、创建/累计统计；当前member_count取首个特征count，不能解释为去重成员人数。（S1、S2、S3、S4） |
| `label` | character varying / varchar；非NULL | 无默认 | 同伴组显示名称；创建未给label时用组ID。 | VARCHAR自由文本；catalog未记录字符长度；无已确认封闭枚举。 | PeerGroupService按租户与组ID读、创建/累计统计；当前member_count取首个特征count，不能解释为去重成员人数。（S1、S2、S3、S4） |
| `entity_type` | character varying / varchar；非NULL | 无默认 | 组对应实体类别，API约定见UEBA entity_type；数据库没有CHECK。 | UEBA HTTP API实体类型约定（DB无CHECK，非所有旁路writer强制）：user=用户；device=设备；ip=IP地址；service_account=服务账号；ai_agent=AI智能体；mcp_server=MCP服务。 | PeerGroupService按租户与组ID读、创建/累计统计；当前member_count取首个特征count，不能解释为去重成员人数。（S1、S2、S3、S4、S5） |
| `feature_stats` | jsonb / jsonb；非NULL | `'{}'::jsonb` | 组内特征累计Welford统计。 | JSON对象：{特征名:{mean:均值,M2:离均差平方和,count:该特征观测数,std:样本标准差}}；特征名开放，Welford累计更新，DB无JSON shape CHECK。 | PeerGroupService按租户与组ID读、创建/累计统计；当前member_count取首个特征count，不能解释为去重成员人数。（S1、S2、S3、S4、S6） |
| `member_count` | integer / int4；非NULL | `0` | 当前实现取首个特征的累计count；是观测计数代理，不能当独立成员人数。 | INTEGER，默认0；当前update取首个特征的count，不去重实体；不是准确组成员数量，catalog无非负CHECK。 | PeerGroupService按租户与组ID读、创建/累计统计；当前member_count取首个特征count，不能解释为去重成员人数。（S1、S2、S3、S4） |
| `created_at` | timestamp with time zone / timestamptz；可NULL | `now()` | 同伴组数据库记录创建时间，当前ORM未映射，使用DB默认。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | PeerGroupService按租户与组ID读、创建/累计统计；当前member_count取首个特征count，不能解释为去重成员人数。（S1、S2、S3、S4） |
| `updated_at` | timestamp with time zone / timestamptz；可NULL | `now()` | 组统计最近ORM更新时刻。 | TIMESTAMPTZ带时区时间；JSON/API通常ISO 8601，显示时可转换时区；NULL与未记录不同于零。 | PeerGroupService按租户与组ID读、创建/累计统计；当前member_count取首个特征count，不能解释为去重成员人数。（S1、S2、S3、S4） |

**实际约束**（按已采集pg_constraint原文；不包含全部索引/触发器/RLS）：

- `ueba_peer_groups_pkey`：`PRIMARY KEY (id)`

**字段解释依据**：

- S1：[ docs/integration/v1/data-catalog.json ](../../../docs/integration/v1/data-catalog.json)
- S2：[ services/ueba/app/models/ueba.py:85 ](../../../services/ueba/app/models/ueba.py:85)
- S3：[ services/ueba/app/services/peer_group.py:21 ](../../../services/ueba/app/services/peer_group.py:21)
- S4：[ services/ueba/app/services/peer_group.py:67 ](../../../services/ueba/app/services/peer_group.py:67)
- S5：[ services/ueba/app/api/routes.py:73 ](../../../services/ueba/app/api/routes.py:73)
- S6：[ services/ueba/app/services/baseline.py:25 ](../../../services/ueba/app/services/baseline.py:25)


<a id="json-contracts"></a>

## 4. JSON、事件与工件的结构

JSONB和TEXT正文都有按kind变化的结构，不能把下列JSON键当成独立表列。具体字段存在与缺失继续按[逐字段审计](ui-functional-data-audit.md)判断；生产旧Run和本地新版分别读取。

### 4.1 告警来源与Fusion JSON

| 键 / 值 | 含义与边界 |
| --- | --- |
| `socai2_fusion.identity` | version/source/source_alert_id/connector_id；来源身份 |
| `socai2_fusion.incident_id` | 融合分组UUID文本，不是Case |
| `socai2_fusion.ioc_lookup` | indicators[{ioc_type,value}]/status/scope/matches/checked_at/external_status等；只说明实际来源范围，不命中不判安全 |
| `socai2_fusion.delivery_snapshot.fused.alert` | 首次融合交付的来源告警快照；当前Alert状态和标签可与快照不同 |
| `limit` | 不是严格JSONB schema；版本和可选键须按实际记录处理。 |

### 4.2 调查事件kind与payload

程序约定/已查writer和StepKind；非数据库CHECK、非完整闭合集合。

| 键 / 值 | 含义与边界 |
| --- | --- |
| `recon` | 侦察阶段记录 |
| `forensic` | 取证分析阶段记录 |
| `responder` | 响应建议阶段记录 |
| `reporter` | 报告角色记录 |
| `report` | 报告步骤记录 |
| `error` | 错误步骤 |
| `tool_call` | 工具执行记录；旧版预览、新版本地附结构状态/留存引用 |
| `llm_call` | 模型交换步骤 |
| `llm_prompt` | 模型输入记录类别 |
| `llm_response` | 模型输出记录类别 |
| `evidence_cited` | 证据引用步骤 |
| `decision_reason` | 决策理由步骤 |
| `debate` | 多假设讨论记录 |
| `triage_started` | 分诊处理认领，不能单凭它证明模型已调用 |
| `triage_verdict` | 首次分诊结论及恢复/用量材料 |
| `graph_step` | graph节点完成记录 |
| `graph_result` | graph结果索引与业务完成度 |
| `graph_usage` | 后续graph用量汇总 |

不同事件的payload按各自类型读取：

| 键 / 值 | 含义与边界 |
| --- | --- |
| `triage_verdict` | verdict/confidence/rationale/auto_closed/findings/proposed_actions；recovery含alert_id/run_id/incident_id/workflow_version/cost等。首次分诊和最终调查分开。 |
| `graph_result` | payload.completion=completed（程序交付完整）/partial（部分结果）；另含status/verdict/artifacts/result_sha256等。completion在事件，未保证工件G有同名键；也不等于内容质量验收。 |
| `graph_step` | payload.node是节点名；当前旧记录不含完整节点输入输出。 |
| `tool_call` | 旧生产payload为tool/args/result_preview；新本地写结构status/available/call_id/iteration/结果hash/截断等，result_text在tool_result工件。 |
| `llm_call` | agent/model/purpose/timestamp/duration_ms/input_hash/output_hash/prompt_truncated/response_truncated；提示和回复原件按工件，不保证全量。 |
| `graph_usage` | usage含调用/输入输出tokens/费用来源累计，按schema_version解释，不把模型行计数当全量请求尝试。 |

### 4.3 工件类型及本地工具结构

以下是本流程常用程序类别，不是完整枚举；DB无kind CHECK。

| 键 / 值 | 含义与边界 |
| --- | --- |
| `graph_result` | 自动graph最终采用状态JSON文本，raw_alert/findings/verdict/confidence/confidence_basis/budget字段/investigation_depth/context_bundle等；status可能为运行中快照。 |
| `report_md` | Markdown持久报告正文 |
| `report_html` | HTML报告正文，当前V1不是必须交付 |
| `llm_prompt` | 有界模型输入文本 |
| `llm_response` | 有界模型可见回复文本 |
| `graph_llm_exchanges` | 后续graph模型交换数组JSON文本 |
| `attack_chain` | 候选告警链及实体关系图快照JSON |
| `attack_path` | Case路径及状态快照JSON；无Case可not_linked |
| `alert_graph` | Alert直接邻域/可达性快照JSON |
| `knowledge_base_read` | 知识读取回执，status/source/received_count/adopted_count/citations/cited_sources等 |
| `identity_context_read` | 身份资料读取回执，含匹配/采用/限制信息 |
| `organisation_memory_read` | 组织记忆读取回执 |
| `recent_dispositions_read` | 近期人工处置读取回执 |
| `tenant_skill_read` | 技能源回执，含selection/skills/valid_count；无统一adopted_count |
| `tool_result` | 10-23本地新版单次结果JSON；tool/args/call_id/iteration/status/available/result_text/result_size_bytes/result_sha256/result_truncated/duration_ms；尚未部署。 |

`content`是TEXT，JSON工件先解析，Markdown直接读取；`blob_ref`只是外置指针，是否可读须另确认。同Run同kind可能多份，固定artifact_id或明确最新选择，不能跨Run拼接正文。

本地tool_loop程序约定，非DB CHECK；目前保存的两例仅success实值。

| 键 / 值 | 含义与边界 |
| --- | --- |
| `success` | 非空list，或顶层available/ok为true且rows不是空数组；仅程序分类，不保证有有效证据 |
| `empty` | 成功返回但为空，不代表安全 |
| `unavailable` | 数据源/工具不可用 |
| `error` | 调用或返回错误 |
| `unknown` | 返回包络无法可靠分类，保守未知 |

ledger_status=recorded是留存成功；与业务查询status不同。tool_result不保存临时pending；trace在事务成功后记录ledger_event_id/ledger_artifact_id。




### 4.4 状态、时间和用量的不同层次

| 层次 | 实际位置 | 必须区分的含义 |
| --- | --- | --- |
| 告警当前业务状态 | `alerts.status` | 当前处理状态，不从Run completed推导已解决 |
| 首次分诊 | `triage_verdict`事件payload及Alert投影 | TP/FP/BTP/needs_review等；与后续调查结论分别保留 |
| Run执行状态 | `investigation_runs.status` | 程序运行中/结束/失败，不等于是否查清 |
| 调查完成度 | `graph_result`事件payload.completion | 旧生产例为partial；不是同名工件顶层completion列；其他入口缺失时保持未知 |
| 调查结论 | `graph_result`工件content解析的verdict/confidence | 当次分析；不能覆盖首次分诊理由和置信度 |
| 来源、处理与持久时点 | Alert.event_time、事件ts、created_at等 | 业务发生、过程记录、入库是不同时间；first_seen_at也不等于first_seen |
| 费用来源 | measured/estimated/unpriced相关列 | 未计价次数大于0不能把金额0解释为免费；tokens、预算预留单位、迭代数与调用数各有定义 |


Case状态DB值、API兼容别名、转移规则各有层次：

| 键 / 值 | 含义与边界 |
| --- | --- |
| `alert` | 告警业务状态，无DB封闭枚举；不同API/队列终态判断存在差异，不能统一把false_positive/fp等同Case closed。 |
| `run` | 程序运行状态running/completed/failed为当前主要约定，无DB CHECK。 |
| `completion` | graph_result事件payload.completion completed/partial是程序交付完整性，不是Run.status或人工复核。 |
| `verdict` | 分析判断；首次triage和最终graph分别取，不是处理状态。 |
| `case_db_check` | new=新建；triaged=已分诊；investigating=调查中；contained=已控制；resolved=已解决但尚待关案；closed=已关案 |
| `case_api_aliases` | open=归一化为new；in_progress=归一化为investigating；pending=归一化为contained；pending_closure=归一化为contained；cancelled=归一化为closed |
| `case_transitions` | new→triaged→investigating；investigating→contained或resolved；contained→resolved；resolved→closed；closed无常规前向边，重开走独立reopen。 |

费用来源：

| 键 / 值 | 含义与边界 |
| --- | --- |
| `measured` | 网关明报费用；measured_call_count>0时数额才有实测意义 |
| `estimated` | 按已解析具体模型价格估计，单独标注 |
| `unpriced` | 既无实测又无估价；不能显示免费 |
| `limit` | 每次按三类之一记录，但历史或无回执尝试可能缺计数；Run.total_cost_usd与成本行total_cost_usd不应重复相加。 |


事件发生时间、模型/工具查询时间、入库时间分别保留；统一对外ISO8601带时区。risk_score缺失/null是未知，明确0不是缺失。fused.confidence_score 0–1、PG confidence 0–100、分诊ai_score/模型自报confidence和风险优先级不同。

`measured_call_count=0`时total_cost_usd数字0不能显示为实际免费；estimated与measured分开，unpriced保留。报告/工具错误/部分结果不改写成“未发现攻击”；旧Run与失败证据不由这次文档补齐或重调。


<a id="other-stores"></a>

## 5. PG以外的存储分工

以下仅说明当前体系中的职责与已核边界；不是把其他存储对象添加到本篇25张PG表或428列计数里。


| 存储 | 对象 | 输入→输出 | 接口边界 |
| --- | --- | --- | --- |
| Redis Fusion DB9 | aisoc:fusion:dedup:*、correlation:*、incident:*、delivery:v1:*，chain:*等TTL状态 | 告警/异常→去重/关联/恢复/评分 | key内部格式不是对外长期合同，Incident不是PG独立表 |
| ClickHouse aisoc.raw_events | event_id/tenant_id UUID、event_time DateTime64(3,UTC)、实体/进程/OCSF/raw数据 | Kafka规范化事件→湖→SQL/调查工具 | ReplacingMergeTree(ingest_time)，不是实时唯一主键；去重查询按FINAL或适当LIMIT 1 BY |
| ClickHouse其他定义 | aisoc.alert_metrics、aisoc.ioc_enrichments等DDL | 以实际writer/已有资料为准 | DDL存在不等于每张表已持续写入或有完整数据 |
| OpenSearch | socai2-threatintel-iocs / socai2-threatintel-actors | TI导入/Feed代码→IOC/actor检索 | 仅IOC/actor项目索引已有基本实证；原始事件全文索引未接 |
| Neo4j | Alert/Host/User/IOC/Case、共享Technique；OBSERVED_ON/INVOLVES_USER/MAPS_TO/CONTAINS_IOC/CONTAINS_ALERT等 | 已有关系及候选PG投影→上下文/Path | v1.0.0已部署；本轮两Alert直接关系3/5条已读回；关系连通不等于攻击因果 |
| Qdrant | socai2_threatintel_iocs / socai2_threatintel_actors（1536维） | TI向量集合→语义读者 | 已配置/创建但已有实测为空；1D1024维smoke集合不作同空间证据 |

[ClickHouse DDL](../../../services/api/clickhouse/001_init.sql)、[Redis关联器](../../../services/fusion/app/services/correlator.py)、[图写读实现](../../../services/api/app/services/graph_service.py)、[TI存储实现](../../../services/threatintel/app/storage/opensearch.py)、[full净化回执](../../operations/full-support-migration.json)。



## 6. 查询约定、现有证据与后续使用


API在事务里设置`app.current_tenant_id`，同时加tenant条件。直连后端也必须每次事务绑定并显式过滤，连接池归还后下次重设；变量不是`app.tenant_id`。

```sql
BEGIN READ ONLY;
SELECT set_config('app.current_tenant_id', '实际租户UUID', TRUE);
-- 随后所有SELECT仍加 tenant_id = 实际租户UUID
ROLLBACK;
```

当前若干RLS policy包含`current_tenant_id() IS NULL`兼容分支，部分内部角色还可绕过RLS；**未设置变量不能当作自动拒绝跨tenant查询**。直查沿用已授权的只读身份和表范围，并显式绑定/过滤租户；连接凭据由运维交接，不把runtime/owner作为后端管理员发放。[RLS实际实现](../../../services/api/app/db/rls.py)、[初始policy](../../../services/api/migrations/002_rls.sql)、[补充policy](../../../services/api/migrations/060_rls_coverage.sql)

可交给数据后端的完整只读样例见[read-results.sql](examples/read-results.sql)：Alert→常见自动Run→步骤→工件摘要，以及独立Case关系读取。样例只读、不执行DDL/INSERT/UPDATE/DELETE，不修改历史步骤或报告。另有[本轮两个真实Run SQL](examples/production-two-examples.sql)，按实际字段整理；实际定向PG查询及正文校验见[核验回执](../../operations/service-v1-functional-20261022.md)。



**字典解释与数据验证分开：** 两条生产合成告警及21工件证明所选数据可读取，不证明25表每列都有业务实值。支撑表空、未配置来源、结构字段尚未落库、只有本地内存结果等情况，按[可得性审计](ui-functional-data-audit.md)保留；缺失不能自动解释为安全/正常。

本轮静态复核覆盖25/25表与428/428列解释、元数据一致性、重要枚举层级、页面90项编号迁移与文档链接。没有重跑业务测试或新增生产查询。索引和性能、完整RLS政策、未盘点的外围表、所有JSON动态键及其他存储全字段，不作为本字典已经完成全面审计的内容。

使用顺序：理解本篇实际设计 → 阅读[页面建议](page-elements.md)判断需要哪些信息 → 按[取数/SQL/HTTP附件](page-data-mapping.md)做接口聚合 → 用[审计](ui-functional-data-audit.md)核验实值与空态条件。

本轮补充说明：

- 源码定义不等于当前生产版本已有输出；10-23 tool_result仅本地。
- catalog.constraints不含全部索引/触发器/RLS；未列UNIQUE约束不能外推不存在唯一索引。
- 实际DB与ORM不一致以实表为准：Case tenant_id可空、case_number可空、tags默认对象，Alert时间列实际可空。
- 没有schema/check约束的自由字段不应列成唯一合法值集合；示例、API集合、程序约定必须显式区分。
