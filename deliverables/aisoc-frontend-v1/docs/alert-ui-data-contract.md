# 告警 UI 字段对照：完整讨论参考

> 便携参考副本。当前确认口径请先读 [当前字段对照](data-mapping.html)。本文件包含先前讨论和不同日期的结果；旧 ID / 库存、只讨论不改页面的阶段说明不代表当前交付状态。包外源码链接已转换为仓库路径文字。

[返回交接导航](../guide.html)

# 当前告警 UI 与 socai2 数据合同核对（讨论稿）

**更新至2026-10-25：告警列表及概览侧栏的字段展示标准已由用户确认。** 列表九列见2.1，等级和处理状态映射见2.3，侧栏标准见2.5，同一条21落库告警的列表与侧栏实例见2.6。已确认的展示含义与后端待补接口/关联分别记录；完整详情、事件和Case仍保留原讨论边界。

**最新范围：用户要求恢复原设计稿及原展示数据，去掉本轮21快照、只读、缺口等页面标签。页面已恢复；本文仅保留真实字段映射和待补齐项，不再据此修改页面。新增3条重放数据和原始证据保留，不覆盖原展示。**

2026-10-24。用户已确认：**以 socai2 当前已落地流程为准，原版 AiSOC 只作参考。** 本稿对应 `prototypes/security-pages` 已确认的告警列表、侧栏、完整详情与操作。最初为静态讨论稿；用户随后授权20选样→21重放→真实读取→前端展示，实际结果见第7节和重放回执（仓库参考路径：`docs/operations/alert-ui-replay-20261024.md`）。本轮未改服务端流程或接口，未确认的写入语义仍保留待议。

**核对层次：** ①现有21发布/实值回执；②本地模型与API源码；③未落地设计。①证明记录时的实例和发布范围，不能证明当前每条都有值；②不能自动证明生产接口含最新本地改动；调查 v2 未注册入口、20专用 overlay 不计为21已交付。

## 1. 数据与流程基线

- 主告警：`public.alerts`。Fusion 将原始告警融合、落库并交付；只有 canonical Alert ID 用来关联后续处理。
- 来源身份/事件：`alerts.enrichment_data.socai2_fusion`，下文简写 **F**；其中 `delivery_snapshot.fused.alert` 简写 **S**，是首次来源快照。
- 首次分诊：`public.investigation_events.kind='triage_verdict'` 的 `payload` 简写 **T**。按已确认的告警→Run关联查，而非仅按时间随意挑事件。
- 调查账本：`public.investigation_runs` (**R**)、`public.investigation_events` (**E**)、`public.investigation_artifacts` (**K**)；同Run `K.kind='graph_result'` 的 `content::jsonb` 简写 **G**，同Run `E.kind='graph_result'` 的 `payload` 简写 **GE**。**这是21口径；不能套用20的graph_state/report_markdown名称。**
- 自动Run定位沿已验取数：`R.raw_alert->>'id'=alerts.id::text`，结合租户及已知入口。旧自动 `R.case_id` 可能装的是告警ID，**不能把它当业务Case关联**。
- 自动分诊可关闭告警，也可升级调查。无Case仍可有自动Run。业务Case关系和运行状态、完成度是不同概念。
- 所有查询/关联先限定同租户；聚合先各表独立聚合，避免events×artifacts×costs乘积。

## 2. 列表和概览侧栏

### 2.1 告警列表九列：原始字段对照（2026-10-25）

**本次仅整理文档，页面、设计、示例数据、交互均不修改。** 顺序严格对应当前`alertListLayout`；选择框是UI状态，不是数据库业务列。后续用户追加概览侧栏字段盘点，见2.5；完整详情和操作接口不在本小步新增核对范围。

取数基线：**192.168.1.21 → PostgreSQL数据库 `aisoc` → schema `public`**。下表省略`public.`前缀；所有关联须限定同一`tenant_id`。实值依据为2026-10-24 **21:01:09（UTC+08）**留存的真实数据库结构及三条重放结果，该三条盘点阶段未重新访问服务器；随后2026-10-25 10:02:43（UTC+08）定向只读复查其中一条，见2.6。不能把这些样例外推为全库数据分布。接口栏仅说明当前本地代码核对结果，不冒充本轮线上HTTP实测。

| 顺序 / 原页面列 | 原始数据库字段 | 取数与业务含义 | 三条真实样例 / 当前缺口 |
| --- | --- | --- | --- |
| 1 告警名称 | `alerts.title` | 当前canonical告警的标题；点击对象使用同一行`alerts.id` | 三条均有值，例如`Office启动隐藏PowerShell [DEMO-FIN-11]`。可直接对应，不用AI摘要替换 |
| 2 严重程度 | `alerts.severity` | 已确认：critical/high→高，medium→中，low/info→低。用户所说Inform对应当前canonical值info；不把Inform当已证实的库中原值 | 三条样例均high；显示、筛选、统计、导出统一此分组，原值不改写 |
| 3 告警时间 | `alerts.event_time` | 该行保存的告警发生时刻，timestamptz；按北京时间展示，排序使用完整时刻 | 第一条`2026-10-24 03:51:40.277842+00`→11:51:40。实库允许NULL，且来源缺时间时Fusion会回填当前时间，因此不保证每条都是上游明确报告时间 |
| 4 资产标签 | `assets.tags` | 已确认是资产表标签，不是alerts.tags；具体关联、聚合及填充由后端处理，本轮不设计实现 | 三条样例未匹配资产；保留数据缺口记录，不改现有页面或示例标签 |
| 5 处理状态 | `alerts.status` | 告警业务处理状态；不从`investigation_runs.status`或自动调查完整性推导 | 一条`triaged`、两条`resolved`。已确认`new/triaging/triaged`归新建/待处理，`in_progress/investigating`归进行中，`resolved/closed`归完成；启动调查算进行中，分配不触发进行中；其他历史枚举归组待定 |
| 6 类别（战术标签） | `alerts.mitre_tactics` | 本次按用户“战术标签”口径记录，取MITRE战术，不能读通用分类alerts.category或技术ID mitre_techniques | 三条样例均为["Execution"]；按原值中文展示，多战术保留原始数组供后端组织。本轮不改页面列名 |
| 7 检测源 | `alerts.enrichment_data #>> '{socai2_fusion,identity,source}'` | 用户明确含义：日志来自哪个厂商/产品。Fusion入口有source字段，落库保存在JSON中，主表没有同名独立列；来源标识是否已能表达原始厂商需由后端确认 | 本次source=showcase-security-sensor是测试来源，不能冒充某个厂商；中转平台与原始日志厂商可能不同 |
| 8 受影响资产 | 既有资产关联中的`assets.name`；账户名候选为`alerts.affected_users`或`entities`中user值 | 已确认使用关联资产名称；告警有账户名也可以显示。具体关联/组织由后端处理，不把受影响账户当负责人 | 三条有源主机和demo账户名，无台账关联；本轮不新增主资产选择或资产匹配设计 |
| 9 负责人 | 现有候选`alerts.assigned_to_id`，相关用户表由后端管理 | 已确认含义为“分配给哪个用户处理”。本轮取数方案允许留空，不强行确定用户显示名、表关系或改现有页面 | 三条assigned_to_id均NULL；“留空”不是删除列，也不清空原示例负责人 |

**后端承接：** 资产标签的关联和填充、关联资产名称的组织、负责人表管理均交由后端处理，本轮不细化或实现。已有查询样例仅作为实库核对依据保留于[只读SQL](alert-ui-snapshot-queries.sql)，不作为新实现要求。本轮没有改页面、数据库、SQL或接口。

### 2.2 “没有”的具体含义：单独登记

| 类型 | 列 / 实际情况 | 后续需要补齐 |
| --- | --- | --- |
| 有字段，本次为空 | 负责人：assigned_to_id=NULL | 真实分配业务及用户目录读取。不能把空值说成系统没有负责人字段 |
| 已明确改用战术来源 | 原通用category为空，但本列按战术标签读mitre_tactics | category空值不再作为本列缺口；仅在mitre_tactics本身为空时登记缺失，不按标题补造 |
| 有表，但关系没建立 | 受影响资产、资产标签：无alert_asset_correlations记录 | 实体匹配资产台账，维护assets.tags；本次不证明台账全库为空 |
| 没有同名直接列，但有JSON来源 | 检测源：没有alerts.source，有Fusion identity.source | 明确JSON读取与产品名称字典；缺路径的旧记录另定回退规则 |
| 库有对应字段/关系，现有列表响应未完整声明 | 负责人ID/姓名、资产关联ID/标签、检测源独立字段 | 本地AlertResponse未声明这些列表展示字段，不能只改前端字段名完成接入。已有affected数组也不等于资产关联 |
| 结构与接口假设不同 | 告警时间：实库event_time可空，本地模型/AlertResponse按非空处理 | 核实历史空时间行及缺省来源；不能在UI静默替换created_at并称原始发生时间 |

### 2.3 用户本轮确认与状态详解（2026-10-25，仅文档）

**已明确：** 告警名称和告警时间沿用原字段；Critical/High→高、Medium→中、Low/Inform→低（canonical为info）；资产标签明确取资产表，细节交后端；类别按战术标签理解，取mitre_tactics；检测源表示原始日志厂商/产品；受影响资产显示既有关联资产名，告警账户名也可显示；负责人表示分配到哪个用户，可暂留空由后端管理。以上都不改变当前设计稿、示例数据或交互。

**处理状态已确认（2026-10-25 后续确认）：** new/triaging/triaged→新建/待处理；in_progress/investigating→进行中；resolved/closed→完成。用户明确启动调查也算进行中，分配/认领本身不改状态。此处更新业务映射，不修改页面及其现有“已解决”文案；历史fp/false_positive等其他值仍另行确认。

#### 处理状态究竟读什么

`aisoc.public.alerts.status`是当前告警的处理状态，实库为非空字符串，不是Run状态。当前PATCH请求也接收字符串，源码枚举不等于数据库全量值；本轮未全库扫描状态分布。

| 原始status | 含义/当前写入或使用路径 | 本次样例证明 | 显示分组与待确认项 |
| --- | --- | --- | --- |
| `new` | Fusion新告警INSERT写入new，即使原始输入有别的状态也不直接沿用 | 入口写入路径已核；最终三条均已被自动处理推进 | 已确认新建/待处理 |
| `triaged` | 自动分诊有结果、未自动关闭；ledger仅将原new推进triaged，已有更后状态保持 | 第一条最终triaged，disposition=true_positive | 已确认仍归新建/待处理，不能说明人工已开始 |
| `triaging` | 分诊中的语义；本地告警统计/队列把它列为未完成状态，本轮没核到实际推进它的写入样例 | 三条最终均非此值 | 已确认归新建/待处理 |
| `in_progress` | 业务处理中；告警模型和统计支持，人工PATCH可设置 | 无本次实值 | 已确认与investigating合组为进行中 |
| `investigating` | 当前Case启动调查代码会将关联告警new/triaged/triaging推进到该值；这是告警status，不是Run.running | 本地代码已核，本轮未执行此Case入口 | 已确认归进行中；用户明确启动调查算进行中，不要求必须人工直接修改状态 |
| `resolved` | 已处理完成/关闭；自动分诊满足自动关闭条件后写入，同时写resolved_at；人工/批量关闭路径也支持 | 第二、三条resolved + disposition=false_positive | 对应用户的“完成”；具体界面字样此轮不改 |
| `closed` | 关闭兼容值；人工更新/批量关闭支持，公共状态助手认作终态 | 无本次实值 | 已确认与resolved统一归完成 |
| `false_positive` / `fp` | 历史把误报放进status的兼容值；队列认作已关闭，其中false_positive受PATCH/批量关闭支持 | 本次误报写在disposition，status是resolved，并非这两个值 | 建议按兼容终态归完成；需确认。不要把所有disposition=false_positive直接当status=完成 |
| `escalated` / `snoozed` | 本地批量关闭兼容列表含这两个值；snooze主要另有snoozed_until字段，不能据此断言当前一定写status=snoozed | 无本次实值 | 若实际遇到需按后端定义兼容，不静默归完成；不新增页面状态 |
| 其他/未知字符串 | API不采用封闭枚举校验，可能存在历史或外部写入值 | 未作全库值域扫描 | 保留待核对，不能默认已完成 |

`completed`在本次三条中是**investigation_runs.status**，不是alerts.status。第一条Run已completed，但alerts.status仍triaged且graph结果partial；因此自动处理结束不能把告警列表改成完成。

#### 状态旁边几个容易混淆的原始字段

| 表字段 | 实际表示 | 对处理状态的影响 |
| --- | --- | --- |
| `alerts.disposition` | 判定结果，例如true_positive、false_positive、benign_true_positive、needs_review | 与status独立；本次自动分诊在同一流程中按条件同时更新，不能只看判定猜状态 |
| `alerts.assigned_to_id` / `assigned_at` | 分配给谁、何时分配 | 已确认分配不改状态；当前PATCH分别写这些字段 |
| `alerts.resolved_at` | 关闭路径记录的时间 | 不能仅凭非空就认定当前完成：当前PATCH支持写终态时间，但转回非终态未见同步清空逻辑，应以status为主 |
| `investigation_runs.status` | 某次自动处理Run是否running/completed/failed等 | 不用来覆盖告警处理状态 |
| `investigation_events`中graph_result的`payload.completion` | 该次调查完整性，如partial | 不等于告警完成或未完成 |

**当前实现与已确认业务规则的差异：**

- 分配与状态独立，符合此前确认。
- 自动分诊未关闭只将new推进triaged，按此前确认仍显示待处理。
- Case启动调查当前会自动推进部分关联告警为investigating；用户已确认启动调查也算进行中，此项不再是业务口径差异。其他调查入口是否同步更新alerts.status仍需按各入口核对，不能用Run.running直接替代告警状态。本轮不修改Case流程。
- 保存反馈“误报/符合预期的正常或授权行为→关闭、其余保持”已确认，但原反馈实现没有完整同步alerts.status；不能靠前端展示掩盖差异。人工直接关闭额外流程仍待定。
- 公共终态助手只列resolved/closed，队列另含false_positive/fp；未来后端应统一分组，避免不同统计口径。本轮未修。

#### 检测源字段说明

用户要的是“这条告警来自哪个厂商/产品采集上送的日志”。**这条Fusion链路有来源数据，不是没有来源：**

1. 接入对象`RawAlert.source`是必填字符串。
2. Fusion将它存入每条`alerts.enrichment_data.socai2_fusion.identity.source`；完整首发快照内也保留`delivery_snapshot.fused.alert.source`。主表没有单独名为source的列。
3. 当前列表AlertResponse没有独立检测源字段，详情有`fusion_identity.source`；后端可直接从同一条alerts记录的JSON提取来源，整理为列表返回字段，读取此来源标识本身不需要关联另一张表。是否另建厂商字典取决于规范显示名的需要。
4. 该source目前是自由来源标识，**不保证已经规范成原始日志厂商名**。经SIEM/采集平台中转时，平台来源与原始厂商可能不同；不能无条件用connector_type或connectors.name替代厂商。
5. 三条实值都是showcase-security-sensor（测试来源），不足以验证真实厂商映射。后端需按本次已定含义交付厂商/产品显示值；本轮不扩展来源表设计。

核对代码：`services/fusion/app/models/alert.py`、`services/fusion/app/services/alert_sink.py`、`services/agents/app/investigator/ledger.py`、`services/api/app/api/v1/endpoints/alerts.py`、`cases.py`、`services/api/app/services/alert_status.py`、`alert_queue.py`、`alert_bulk_close.py`。这些本地路径用于说明当前实现；未在本轮请求运行这些入口。

### 2.4 列表与侧栏共用字段盘点（2026-10-25 更新）

“有字段”表示查得到位置；空值、接口缺字段和实际未匹配要分别处理。

| 编号 / 页面字段 | 业务含义与表字段 | 写入/读取及现状 | 转换、空值或待讨论 |
| --- | --- | --- | --- |
| L01 告警名称 | `alerts.title`：当前告警标题 | Fusion写；列表/详情返回 | 不用Case标题或AI摘要替代 |
| L02 严重程度 | `alerts.severity`：告警等级 | Fusion写；接口直接返回 | 2026-10-25已确认critical/high→高、medium→中、low/info→低；本轮只记录口径 |
| L03 告警时间 | `alerts.event_time`：当前告警保存的发生时刻 | Fusion写；来源缺时间时可能回填当前时间，实库字段可空，见2.1 | 显示北京时间到秒，保留原时区和精度用于传输/排序；不换成created_at、first_seen_at或updated_at |
| L04 资产标签 | 同租户`alert_asset_correlations.alert_id→asset_id→assets.id`，取`assets.tags` | 资产库有字段；既有样例未匹配资产补充资料 | 不是`alerts.tags`；关联和多资产标签整理细节由后端处理。无匹配不补造标签，不凭主机名猜Windows域控 |
| L05 处理状态 | `alerts.status`：告警业务处理状态 | Fusion初始new；分诊持久化自动关闭→resolved，否则new→triaged；人工PATCH可更新 | 已确认new/triaging/triaged→新建/待处理、in_progress/investigating→进行中、resolved/closed→完成；启动调查算进行中，分配不改变状态。不是R.status或GE.completion |
| L06 类别（战术标签） | `alerts.mitre_tactics` | 本次按用户战术标签口径记录；原category是其他含义 | 战术与技术分开；不能按标题补造缺失战术 |
| L07 检测源 | `alerts.enrichment_data #>> '{socai2_fusion,identity,source}'`：已存来源标识，产品含义要求为日志来源厂商/产品 | 直接取同一条告警JSON，不需跨表关联；详情`fusion_identity.source`可取；列表响应没有独立source | 后端补列表输出及来源→厂商/产品名称映射；connector_type或采集平台名称不自动等于原始厂商 |
| L08 受影响资产 | `alerts.entities`及`affected_hosts/affected_ips/affected_users`保存关联对象；真实资产另取`assets.id/name` | 详情`related_entities`可组装对象；列表响应仅部分affected数组，不含完整entities | 用户确认优先通过资产关系取assets.name，也允许展示告警账户名；具体组装交后端。未匹配的主机名不冒充资产表名称；确认asset_id才链接资产详情，账号/IP不冒充资产UUID |
| L09 负责人 | `alerts.assigned_to_id/assigned_at`；同租户`users.id→username/email`为本地模型候选关联 | PATCH/claim写；当前AlertResponse未返回assigned_to_id/assignee；既有实值未分配 | 业务含义已确认是分配来处理告警的用户；用户允许暂留空，具体表关联/返回字段交后端。NULL是未分配；ID存在但姓名缺失是未解析；不使用affected_users当负责人 |
| L10 告警ID | `alerts.id`：canonical告警UUID | 主键、接口返回；侧栏/详情复用 | 与来源告警ID、Fusion消息ID、事件ID、CaseID、RunID分开 |
| L11 发生了什么（侧栏） | `alerts.description`：来源描述 | Fusion写；接口返回 | 与完整详情调用Explain取得的解释区分；缺失显示“来源未提供描述” |
| L12 受影响实体（侧栏/详情） | `alerts.entities`或详情`related_entities`；IOC另见F.ioc_lookup | 程序整理；实体不是“已证实受害资产” | 告警对象与库存资产关系同L08；账号/IP/文件保留类型和值 |
| L13 所属事件 | `F.incident_id`；详情`fusion_incident_id` | Fusion链有值；主Alert无独立incident_id列 | 用户要求每条告警属于一个事件；历史/直写路径可能缺，属于数据完整性缺口。现有Incident UUID不自动带原型中的事件中文标题 |
| L14 所属Case/名称 | `alerts.case_id`；同租户`aisoc_cases.id/title/case_number`；另有Case.`alert_ids`成员数组 | 两种关系存储均存在；自动样例无Case | 原型可追加到多个Case，但alerts.case_id单值。转移还是多关联必须定；不能读R.case_id代替 |

### 2.5 告警列表概览侧栏：已确认展示标准（2026-10-25）

用户已确认以下标准，并明确**只更新对照文档，页面、原有示例数据和交互不改**。侧栏从列表选中的同一条`alerts.id`取数，只有“概览”Tab。按“标题及等级/状态/战术标签 → 发生了什么 → 告警信息 → 受影响实体 → 关联事件与Case → 底部操作”的现有顺序组织，不恢复分类、相关事件/处理记录Tab或“查看相似告警”。

| 当前区域 / 字段 | 已确认取数与展示规则 | 空值、待补或边界 |
| --- | --- | --- |
| 标题 | `alerts.title`；定位使用`alerts.id` | 与列表同一告警，保持原始标题 |
| 顶部严重程度 | `alerts.severity`按critical/high→高、medium→中、low/info→低 | 与列表、筛选和统计一致 |
| 顶部处理状态 | `alerts.status`：new/triaging/triaged→新建/待处理，in_progress/investigating→进行中，resolved/closed→完成 | 启动调查算进行中；分配不改状态；不拿Run状态覆盖。文档记录统一含义，本轮不修改原界面“已解决”等字样 |
| 顶部类别标签 | `alerts.mitre_tactics`战术标签 | 不取alerts.category，不取disposition或技术编号；多战术返回列表，后端负责标准名称 |
| 发生了什么 | `alerts.description`来源描述；与本条告警对应，保持来源语义 | 缺失按“来源未提供描述”处理；不拼接分诊理由、调查结论或narrative充当来源描述。完整详情改按现有Explain请求返回内容接入，见4.1.1；侧栏仍只展示来源描述 |
| 告警信息—告警ID | `alerts.id` | canonical告警ID，不是来源消息/事件/Case/Run ID |
| 告警信息—告警时间 | `alerts.event_time`转换为北京时间，以YYYY-MM-DD HH:mm:ss展示；排序保留完整精度 | 空值展示“—”并作为后端缺口记录；不用first_seen_at、created_at或更新时间替代 |
| 告警信息—负责人 | 分配来处理告警的用户；现有候选字段`alerts.assigned_to_id` | NULL按未分配处理，本例展示“未分配”；后端未接入时允许留空。ID存在但姓名未解析不能当未分配；具体用户关联交后端，不用受影响账户填充 |
| 告警信息—检测源 | 直接读取同条告警`enrichment_data.socai2_fusion.identity.source`，读取标识不需跨表关联 | 已有厂商/产品映射则显示名称；本例只有来源标识就保留标识，不猜厂商。后端补输出字段和名称映射；旧记录缺路径的回退规则待定 |
| 告警信息—资产标签 | 通过同租户资产关系取`assets.tags` | 明确不是告警tags；关联/去重细节交后端。没有关联资产或标签为空时展示“—”，不按主机名猜资产角色 |
| 受影响实体 | 已匹配资产取`assets.id/name`；原始主机标识取`alerts.affected_hosts`，账户名取`alerts.affected_users`或entities中的user值 | 主机与账户分别展示，不能把affected_hosts说成assets.name。未匹配主机作为原对象文本；取得真实资产ID后才链接资产详情。当前最多展示4项是原型行为，不代表库中只有4项 |
| 关联事件与Case | 保留现有区域，沿用L13/L14说明 | 本轮不扩展事件/Case取数验证或页面设计；无Case不代表无所属事件 |
| 管理告警 / 打开告警页 | 均作用于当前`alerts.id` | 保留现有入口；本轮不改写接口和人工关闭流程 |

**后端承接项：** 输出侧栏所需来源字段并处理厂商/产品名称映射；维护告警与资产关系并返回资产ID、名称、标签；提供负责人身份及显示名。以上属于取数接入，不改变已确认的展示标准；本轮不新建表、接口或资产匹配流程。事件/Case区域保留，取数另行核对。侧栏来源描述与完整详情Explain请求结果是两个独立取数要求。

### 2.6 一条21实际落库告警的字段展示（2026-10-25只读复查）

北京时间**2026-10-25 10:02:43**，通过已有21 API容器的数据库连接，在只读事务内限定租户和告警ID查询`aisoc.public.alerts`及资产关系。未写库、重放、启动调查或更改页面。该记录来自此前20→21重放的测试告警，是真实落库记录，不代表真实攻击或真实厂商采集样本。

告警ID：`92070605-0aa0-5e8f-8f0f-4a44222a0146`。

#### 列表字段实例

| 列 | 本次数据库原值 | 按已确认规则的展示/缺口 |
| --- | --- | --- |
| 告警名称 | `title=Office启动隐藏PowerShell [DEMO-FIN-11]` | 原标题 |
| 严重程度 | `severity=high` | 高 |
| 告警时间 | `event_time=2026-10-24 03:51:40.277842+00:00` | 北京时间2026-10-24 11:51:40；原微秒保留在数据中 |
| 资产标签 | 关联资产查询0条 | —；不能推断资产类型或标签 |
| 处理状态 | `status=triaged` | 新建/待处理 |
| 类别（战术标签） | `mitre_tactics=["Execution"]` | 执行（Execution）；中文为展示翻译 |
| 检测源 | JSON路径`identity.source=showcase-security-sensor` | 已取到来源标识；本例无已验证的厂商显示名，不替换成Microsoft等厂商 |
| 受影响资产/账户 | 资产关系0条；`affected_hosts=["DEMO-FIN-11"]`，`affected_users=["demo.finance"]` | 资产名待关联；账户可显示demo.finance。DEMO-FIN-11只是当前告警中的主机标识，不能说已从assets.name取到 |
| 负责人 | `assigned_to_id=NULL` | 未分配（或按最终展示规则留空） |

侧栏“发生了什么”的来源描述原文：

> WINWORD.EXE spawned powershell.exe with hidden window on DEMO-FIN-11 under demo.finance. Parent PID 4100, child PID 4200. No payload contents or approval records supplied.

含义：WINWORD.EXE在主机DEMO-FIN-11上以demo.finance账户启动隐藏窗口的PowerShell；父进程PID 4100、子进程PID 4200；来源没有提供载荷内容或审批记录。此段仅解释来源描述，不追加恶意/授权判定。

只读原始回执与查询脚本保存在`.local/verification/alert-ui-replay-20261024/example-readonly-20261025.json`及同名`.py`；本条未查询事件/Case或调查Run。

#### 同一条告警的概览侧栏实例（用户已确认）

**标题：** Office启动隐藏PowerShell [DEMO-FIN-11]  
**顶部标签：** 高 · 新建／待处理 · 执行

**发生了什么：** WINWORD.EXE在主机`DEMO-FIN-11`上，以`demo.finance`账户启动了隐藏窗口的PowerShell。父进程PID为4100，子进程PID为4200；来源未提供载荷内容和审批记录。

上述中文是来源描述的译意，用于本对照文档展示；数据库description原文仍为英文。不据此宣称已有自动翻译功能或预生成AI解释。

| 告警信息 | 本例展示 |
| --- | --- |
| 告警ID | `92070605-0aa0-5e8f-8f0f-4a44222a0146` |
| 告警时间 | 2026-10-24 11:51:40（北京时间） |
| 负责人 | 未分配 |
| 检测源 | `showcase-security-sensor` |
| 资产标签 | — |

**受影响实体：** 主机`DEMO-FIN-11`（affected_hosts原对象，尚无资产表关联）；账户`demo.finance`（affected_users）。本例不能生成已关联资产的详情链接，待后端返回真实资产ID后接入。原始记录另有affected_ips，本例未将其扩展为新的资产条目，不代表原告警没有IP数据。

**关联事件与Case：** 保留既有区域；本次只读查询未包含关联事件或Case，不填入猜测的名称或关联状态。  
**底部入口：** 保留“管理告警”“打开告警页”，均指向本条告警。

## 3. 顶部统计、筛选与排序

| 控件 | 取数/行为 | 当前差异与待定 |
| --- | --- | --- |
| 全部告警 | 对同租户、同筛选范围的alerts计数；API total/facets | 是否随快捷筛选变化需确定；不能按当前页计数 |
| 高严重程度 | 按L02显示映射聚合`facets.by_severity` | 已确认高包括critical+high，计数/筛选/导出必须同一规则 |
| 待处理 | `alerts.status`聚合 | 用户已确认new/triaging/triaged均归新建/待处理；统计必须覆盖三者，不能直接使用语义更宽的unresolved计数 |
| 调查进行中 | 关联R.status及真实调查阶段 | 不能把triaged或所有running Run都算正式调查，running可能只是分诊；多Run按告警去重。缺统一聚合字段 |
| 全部/分配给我 | `alerts.assigned_to_id=current_user.user_id` | API有assigned_to_me；不是将负责人字符串与头像姓名比较 |
| 高中低、三种状态快捷筛选 | 对映射后的枚举组过滤，结果统计一致 | 现有severity/status参数是单值等于，不支持一个“高”同时覆盖两个原值或一个“进行中”覆盖多个原值 |
| 时间范围 | 按`alerts.event_time`边界，统一时区 | 当前list_alerts无起止时间参数 |
| 搜索名称/ID | title与canonical ID的搜索 | 当前list_alerts虽然接收search，但未用入查询过滤，不能视为可用 |
| 其他来源/资产标签/负责人筛选 | 各字段对应查询及资产/人员关联 | 当前list_alerts只支持部分条件；不能在一页结果上过滤后宣称全量 |
| 时间/等级双向排序 | event_time升降；等级按确认后的顺序 | 当前sort=newest实际created_at倒序，priority为原等级排序+created_at倒序；缺event_time和双向选择。分页需稳定二级键 |
| 导出/列设置/分页 | 展示字段映射用于导出；分页取完整过滤集合 | 列设置是UI偏好；导出全部筛选结果还是仅所选需明确，不能只导出已加载页却标全部 |

## 4. 完整告警详情

### 4.0 概况页：字段核对与最新功能口径（2026-10-25）

用户要求沿用列表/侧栏的核对方式继续详情页。仅整理字段及业务歧义，不修改页面、示例数据、操作或后台流程。页面以`prototypes/security-pages/alert-detail.js`实际渲染为准：公共头部及关系条、概况、时间线、原始数据、响应。本轮先核对公共头部和概况；另外三个Tab保留4.2/4.3的既有盘点，尚未完成本轮逐项确认。

**本轮追加确认：** Explain按当前请求方式由对接方调用，选取原版侧栏部分结构化信息映射到新版已有区域，不以预生成为当前接入前提。相关告警、Case关联、判定反馈与相似告警复核只写功能说明；具体查询、匹配、存储和操作规则由后端实现，Case/反馈进一步细节待对应功能建设后再讨论，页面保持现状。见4.1.1—4.1.2。

**实值依据：** 北京时间2026-10-25 **10:16:07**，在21的`aisoc`数据库对同一租户、同一告警`92070605-0aa0-5e8f-8f0f-4a44222a0146`及其关联Run做只读查询，补核告警详情字段、来源快照、分诊/调查结论和租户名称。资产关系/负责人复用10:02:43回执；本轮未重新扫描资产表。原始回执和脚本见`.local/verification/alert-ui-replay-20261024/detail-readonly-20261025.json`及同名`.py`。这是此前重放的测试告警，不是新增真实攻击样本；未调用Explain、详情HTTP懒写入口或调查启动接口。

#### A. 可复用已确认口径的元素

标题、严重程度、处理状态、战术标签，以及“告警属性”中的负责人、告警时间、检测源、告警ID和资产标签，复用第2节标准。本例仍是原标题、高、待处理、Execution；未分配、资产标签无关联。详情中的“检测类别”同样应取战术标签`alerts.mitre_tactics`，不另取`alerts.category`。这一映射不表示本轮已修改页面字段名。

#### B. 详情新增元素：字段、实值和待确认项

| 页面元素 | 原始表字段/来源 | 本例实值 | 含义与待确认项 |
| --- | --- | --- | --- |
| 头部置信度 | `alerts.confidence`、`confidence_label`；原因在`confidence_rationale` | 80、high | 用户已确认使用Fusion检测/融合置信度，本例对应80/100；不用分诊模型的ai_score替代 |
| 头部评分（当前页面的风险评分位置） | 最新确认使用`alerts.ai_score`，即AiSOC分诊模块写入的评分 | 本例0.85；按当前页面100分制展示为85/100 | 产品评分栏目选用分诊模块结果；原字段实际保存该次分诊判定的confidence，保留这一来源含义。无需另找独立风险评分字段，不使用上游0.92；本轮只更新映射，不改页面或原值 |
| 发生了什么—Explain解释 | `POST /api/v1/alerts/{alert_id}/explain`返回`summary` | 本轮仅核源码与原版调用方式，未发送Explain请求 | 按现有接口由对接方调用，结果填入新版“发生了什么”；不再等待预生成结果落库，也不用ai_summary或narrative冒充Explain |
| 解释生成时间 | 同一次Explain响应的`generated_at` | 无本轮实调返回值 | 转为北京时间展示；不使用告警时间、updated_at或分诊时间；原页面文案本轮不改 |
| 关键证据 | Explain的`contributing_events[]`：label/value/annotation | 源码最多返回5项；本例源记录仅含full_log及approval_status，提取结果可能只有基础属性 | 作为告警依据摘要使用，不代表完整取证链；实际字段限制见4.1.1，不能承诺能自动解析full_log中的进程/PID |
| Explain正文中的结论、问题等内容 | 随Explain实际summary正文返回，按返回内容展示 | 当前结构没有独立的待核实事项字段，正文仍可能包含结论或需核查的问题 | 用户明确不要求固定“待核实事项”功能或字段；不单独做语义提取、不要求后端补齐，不拼接其他Run的内容 |
| 属性—源记录ID | `alerts.enrichment_data #>> '{socai2_fusion,identity,source_alert_id}'`；external_id/source_event_ids为另两组字段 | source_alert_id=`bb2b7738-b521-5ff3-ad5a-fb832e3f02ba`；external_id=NULL；本例source_event_ids含同值 | 推荐按来源告警ID解释该项，不能拼SRC-加canonical ID；本例值相同不证明来源告警ID与事件ID永远等价，字段名/含义待确认 |
| 属性—租户 | `alerts.tenant_id → public.tenants.id/name`，同租户鉴权 | stingAISOC Production | 有现成数据，不固定为Contoso；是否继续展示该属性由用户确认 |
| 关联实体与IOC | 资产/账户沿用第2节；IOC结果在`alerts.enrichment_data.socai2_fusion.ioc_lookup` | IP候选10.78.10.11、198.51.100.41；status=no_match、matches=[]、external_status=not_configured | 查询范围仅当前租户PG IOC库；应表达“租户IOC库未命中／外部情报未配置”，不能据此说IP安全或全库无情报 |
| MITRE ATT&CK | `alerts.mitre_tactics`和`alerts.mitre_techniques` | Execution、T1059.001 | 战术和技术分开展示，中文/技术名称由字典映射；不能因战术为执行就硬补T1059.001 |
| 相关告警／相似历史 | 查询同一主机最近发生的7条告警，展示名称、等级、时间 | 本轮仅写功能描述，未查询候选集合 | 让分析人员查看该主机近期告警上下文；具体查询交后端，不作为反馈相似告警复核的同一集合 |
| 当前判定 | 展示当前告警的判定；已有主表字段alerts.disposition可作实现参考 | 本例主表true_positive、后续调查needs_review/partial，差异保留记录 | 本轮只定义查看/人工反馈功能；判定优先级、更新和持久规则待后续功能建设时细化 |
| 判定反馈与理由 | 查看判定，选择反馈结果并记录核查理由 | 本轮未提交反馈 | 页面保持当前选项和交互；按4.1.2描述功能，具体后端实现及接口合同后续细化 |
| 关系条、Case卡、关联与启动入口 | 查看关联Case，创建或选择已有Case并关联当前告警；保留发起AI调查入口 | 本轮未关联Case或启动调查 | 本轮仅说明功能；沿用现有布局和交互，Case/调查细节后续随功能建设细化 |

**三个分数的实际写入含义：** Fusion落库将`fused.confidence_score × 100`写入alerts.confidence；自动分诊持久化把本次判定的confidence写入alerts.ai_score，同时把rationale写入ai_summary；来源risk_score保存在首发快照。本例的80、0.85、0.92是三个不同语义的数值，不能用任一值填满头部两个评分位置。

**头部两项最新确认（2026-10-25）：** 置信度取Fusion的alerts.confidence，本例80/100；页面评分使用AiSOC分诊模块的alerts.ai_score，本例0.85，换算为85/100。此前“独立风险评分字段待补”的要求撤回；用户所指的AiSOC自身评分即当前分诊结果，不另设计评分算法。保留ai_score在代码中由分诊confidence写入的事实，不把上游risk_score混入。

**当前确认边界：** 头部置信度和评分均已明确取数。Explain采用当前请求及返回结构，解释正文和建议动作一并放在“发生了什么”区域，建议为空时内容留空；相关告警、Case和反馈已记录功能说明，后端负责具体规则。后续继续核对其余属性及时间线、原始数据、响应，本轮仍不改页面或覆盖当前判定。

### 4.1 概况、关联与反馈

| 字段/功能 | 表字段或来源 | 语义和缺口 |
| --- | --- | --- |
| Explain解释/生成时间 | 现有Explain响应summary/generated_at | 用户已确认由对接方按请求方式调用；字段选用见4.1.1，不以预生成或新建结果表为前提 |
| Explain结构化依据及正文内容 | 有contributing_events时选取其中的依据；summary正文可能包含结论、待核查问题等 | 随实际返回结构展示，不预设必有固定栏目；无需从正文专门解析出“待核实事项”，也不将其列为后端缺口 |
| 头部检测置信度 | 已确认使用`alerts.confidence/confidence_label`：Fusion检测/融合置信度，0—100 | 不用T.confidence或ai_score替代；NULL是未评估 |
| 头部评分（当前页面的风险评分位置） | 已确认取`alerts.ai_score`，展示时由0—1换算为0—100 | 本例0.85→85/100；这是用户选定的AiSOC分诊模块评分，不另要求风险分字段。NULL保留未评分含义，不以Fusion或上游值回填；页面本轮不改 |
| 属性中的状态/负责人/时间/等级/检测源/类别/资产标签/ID | 复用L02—L10 | 同一字段跨列表/侧栏/详情同口径 |
| 源记录ID | `F.identity.source_alert_id`，另有`alerts.external_id/source_event_ids` | 上游告警ID与来源事件引用不一定同一东西；不用SRC-加canonical ID拼造 |
| 租户 | `alerts.tenant_id→tenants.id/name` | 实际鉴权租户，不能固定Contoso |
| MITRE | `alerts.mitre_tactics/mitre_techniques` | 有技术ID才展示；名称字典另映射，类别不能硬补技术编号 |
| IOC | F.ioc_lookup的indicators、matches、status、checked_at、scope；实体中IP/文件只是候选 | 候选不等于恶意；未查/无匹配/查询失败要区分 |
| 相关告警/相似历史 | 同主机最近发生的7条告警 | 展示名称、严重程度、告警时间；查询由后端实现，见4.1.2 |
| 当前判定 | 查看当前记录的告警判定，主表alerts.disposition为已有实现参考 | 当前主表与后续调查判定不同的实例已留证；本轮仅说明功能，具体更新和优先级规则待反馈功能建设后细化 |
| 反馈选项/理由 | 用户选择判定并填写核查依据，保存反馈 | 保留现有功能形态；本轮不指定存储表或接口，待反馈功能建设后细化 |
| 相似历史批量复核 | 推荐同主机同战术、或共享IP/文件哈希等IOC的近期告警，展示最近5条供人工选择复核 | 功能说明见4.1.2；匹配、排序、候选合并及后续处理规则交后端，本轮不设计算法或改接口 |
| 已关联Case名称/编号 | 展示当前关联Case的名称和编号，并可进入Case查看 | 页面保留；具体关系和数据合同后续随Case功能细化 |
| 最近活跃7个Case/名称搜索 | 打开关联弹框后可从最近活跃Case中选择，也可搜索目标Case | 维持现有选择体验；后端查询和匹配细节本轮不展开 |
| 新Case默认名 | 未关联Case时可新建，名称沿用当前页面默认告警描述；已有关联时新建入口不可选 | 保留当前页面交互；名称校验和创建/关联过程待后续功能细化 |

#### 4.1.1 Explain请求与原版侧栏信息选用

**用户确认：** 当前使用请求触发的Explain，由对接方自行调用；选择原版Explain侧栏中的部分信息填入新版已有区域。此前“提前生成”是未来方向，不作为当前接入前提。本轮只交接调用方式和返回结构，没有请求模型、恢复原版弹框、增加按钮或修改新版页面。

**最新澄清：按实际返回结构和内容展示，不预设固定问题栏目。** summary作为完整解释正文，其中可能自然包含分析结论、待核查的问题或其他说明；不需要专门识别、提取成“结论/待核实事项”等额外字段。contributing_events、suggested_actions等已有结构化字段按返回情况选用。当前原型的示例分栏不构成后端必须返回同名字段的要求；原文将“待核实事项”列为待补字段的表述已撤回。本轮只修正文档，不调整现有页面。

**最新区域安排：** 原版Explain侧栏的“发生了什么”正文和“建议动作”一起放进新版概况的“发生了什么”区域。摘要取summary；建议取suggested_actions的title/rationale，按返回结构展示。没有建议时建议内容留空，不固定生成动作，也不把它转移为另一个必填功能。此前将Explain建议安排到“响应详情”的说明由本条覆盖；本轮只调整交接文档，页面保持现状。

原版`ExplainDrawer.tsx`先调用`alertsApi.explain(alert.id)`，结构化接口返回后按字段展示；另有Agents NDJSON流式兼容路径。本次交接主接口与原版首选一致：

```http
POST /api/v1/alerts/{alert_id}/explain
Authorization: Bearer <对接方获授权的令牌>
X-AiSOC-Tenant-ID: <当前租户UUID>
Accept: application/json
```

- `alert_id`为canonical告警UUID，例如`92070605-0aa0-5e8f-8f0f-4a44222a0146`；该结构化接口**不需要请求体**，服务端按租户查询告警。
- 当前源码权限为`alerts:read`；请求可能生成模型解释，并记录用量/审计，不是读取已保存的解释。基地址/网络访问方式见生产接入说明（仓库参考路径：`docs/integration/v1/production.md#2-结果读取与凭据`），不把21的loopback地址当外部公开地址。
- 返回一个JSON对象。`summary`可能来自模型或规则回退，调用方可用`llm_used/llm_source/llm_reason`识别；成功响应不必然表示模型成功执行。
- 429按返回的Retry-After处理；失败或取消不以旧告警内容冒充新结果。本轮不指定新版的自动调用时机、缓存或重试实现，由对接方接入时处理。

| Explain返回字段 | 数据结构 | 新版保留位置/用途 |
| --- | --- | --- |
| `summary` | string | “发生了什么”的解释正文；其中包含的结论、问题等随正文展示，不额外按语义拆成固定字段 |
| `generated_at` | ISO时间字符串 | 同一份解释的生成时间，转换为北京时间；不称为告警发生时间 |
| `contributing_events` | `{label, value, annotation}[]` | 有内容时选取简要依据展示；label是字段名、value是值、annotation是补充说明。为空不补造证据，也不据此强制新增固定栏目 |
| `suggested_actions` | `{title, rationale, playbook_id, priority}[]` | 与summary一同放进“发生了什么”区域的建议动作部分；展示动作标题及原因，其他结构按需要选用。没有建议时内容留空，不补默认动作；不再指定放到响应Tab |
| `mitre_techniques` | `{id, name, tactic_names, description, url}[]` | 现有MITRE ATT&CK区域可使用技术说明，不在解释卡片内重复另建一套区域 |
| `rule_lineage` | 规则ID/名称/说明、匹配方式与置信度等对象 | 当前选用范围不新增规则来源板块；保留接口能力供后续需要时使用 |
| `historical_fp_rate` | 误报率、样本量、范围、回看天数及说明等对象 | 当前选用范围不新增历史误报率板块，也不将其当作本告警判定 |
| `alert_id` | string | 校验返回结果属于当前告警，避免切换告警后混用 |
| `llm_used / llm_source / llm_reason` | boolean/string/string | 供调用方判断解释生成方式及回退原因，不另加本轮页面标签 |

**当前返回的边界：**

- `contributing_events`不是完整取证链，也没有证据库ID。当前实现最多返回5项，每项value最多160字符，先取Severity、Source、AI score，再从raw_event顶层提取账户/IP/主机/进程等。Source取connector_type或platform，与本稿列表“日志来源厂商”字段含义不同；AI score来自分诊模块，与本次用户选定的页面评分同源；Explain内保留其返回值，不再算一套分数。调用方选用与解释相关的项，避免把基础属性或分数当作恶意证据。
- 本例raw_event只有full_log和approval_status、connector_type为空；按已核提取函数只能得到Severity/Source/AI score这类基础项，不会自动从full_log解析出PID或从affected_hosts补主机。此为已存数据结合源码的推导，**不是本轮Explain实际返回**。
- 返回没有独立的“待核实事项”字段，**这不是需要补齐的功能或字段缺口**。用户明确根据实际返回内容展示：summary里出现结论或待核查问题，就随正文呈现；不做专门语义解析或强制拆栏目，也不从suggested_actions、其他Run中拼造该内容。
- suggested_actions是按告警条件整理的建议，包含动作标题、原因、优先级和可选playbook引用；本次将其与解释正文放在同一“发生了什么”区域。它没有统一目标资产、审批状态或执行结果，本区不强求这些字段，也不把建议当成审批单或已执行动作；无建议时建议内容留空。

**原版兼容路径参考：** Agents接口`POST /api/v1/explain`接收`{alert, alert_id, tenant_id}`并返回NDJSON；summary来自`kind=delta, section=summary`片段，另有evidence/mitre/next_step/done/error帧。它与结构化JSON不是同一种返回，且当前实现依赖传入alert对象，不能只传ID就假设会补查完整告警。原版在结构化调用失败后有流式回退，429不回退；本轮不要求新版照搬回退机制，也不把该流式路径当已完成21联调。

源码依据：结构化接口（仓库参考路径：`services/api/app/api/v1/endpoints/alert_explain.py`）、返回结构及生成逻辑（仓库参考路径：`services/api/app/services/alert_explain.py`）、流式接口（仓库参考路径：`services/agents/app/api/explain.py`）；原版前端参考`SOCAI/opensource/AiSOC/apps/web/src/components/alerts/ExplainDrawer.tsx`及`src/lib/api.ts`。本轮为静态核对，没有发送Explain请求，不能承诺本例实际summary内容或语言。

#### 4.1.2 相关告警、Case关联与判定反馈：功能说明

用户明确**只说明功能是什么，具体规则由后端实现**。页面布局、字段、按钮和已有交互保持原样；下表不指定数据库关系、匹配算法、写入接口或批量处理策略。

| 功能 | 面向用户的用途与操作 | 本轮保留的展示要求 |
| --- | --- | --- |
| 相关告警 | 查看当前主机最近发生的其他告警，帮助了解近期活动上下文 | 查询最近7条，按告警发生时间由新到旧展示；保留告警名称、严重程度和时间，可进入对应详情。查询与主机关联由后端实现 |
| Case关联 | 查看告警归属的Case；通过“关联到”选择已有Case，或在允许时新建Case并关联 | 保留当前弹框、已有/新建Tab、最近活跃Case及搜索体验；已关联时新建不可选，未关联时可新建。创建、关联及后续调查的具体规则待Case功能建设后细化 |
| 判定与反馈 | 查看当前判定；人工选择真实威胁、误报、正常/授权行为或需人工跟进，填写核查理由并保存 | 保留当前选项、理由输入和保存反馈交互。已有“误报/正常授权则关闭、其他不变”讨论记录保留；实际判定更新、存储与关闭过程待反馈功能建设后细化 |
| 反馈后的相似告警复核 | 帮助分析人员复核与当前告警相似的近期告警，推荐同一主机且同一战术，或共享同个IOC（如IP、文件哈希）的告警 | 展示最近5条候选，人工勾选需要复核的告警并提交/应用反馈。具体匹配、时间范围、候选合并、排序、去重和批量结果处理交后端，不在本文展开；没有对应IOC时不补造 |

“相关告警”的最近7条用于查看主机活动上下文；“反馈后的相似告警复核”的最近5条用于人工反馈复核，两者用途和候选范围分开。描述候选条件不表示系统已完成查询或自动判定这些告警性质相同。

### 4.2 时间线

| 生命周期记录 | 取数 | 禁止混用/待补齐 |
| --- | --- | --- |
| 告警发生 | `alerts.event_time` | 实际发生时间，非created_at |
| 告警被检测到 | 来源明确检测时间/S或raw中的已确认字段 | 无统一detected_at。不能按发生时间+15秒生成 |
| 告警入库 | `alerts.created_at` | 不冒充上游采集时间 |
| 分诊开始/结束 | E.kind=triage_started/triage_verdict，取ts | 首次分诊与深入调查分开 |
| 调查启动/结束 | R.started_at/completed_at，结合E真实阶段 | 自动Run开始可能是分诊开始。R.completed不等于调查完整成功 |
| 完成取证 | E真实步骤/结果及其ts | 没有通用完成取证字段；工具有返回也不等于完成取证。不能按+120秒补 |
| 分配/状态修改/关联Case/反馈 | `audit_log`实际记录及payload，Case记录另有case_timeline_events | `assigned_at/resolved_at`只能补当前时间点，不能重建全部历史；仅该告警相关记录，不把同Case全部操作算到它头上 |
| 关闭 | `alerts.resolved_at`与明确的关闭/状态审计 | 反馈路径会写SLA resolved事件但未同步alerts.status，不能单凭该事件断言告警已关闭 |
| 顺序/执行人 | 各真实事件ts倒序，保留秒和来源；审计actor对应身份 | 详情mini_timeline最多6项，不等于完整分页历史；不能从updated_at造“状态改变” |

### 4.3 响应与自动处理过程

| 页面内容 | 取数 | 语义/缺口 |
| --- | --- | --- |
| 响应建议/原因/目标 | 响应Tab后续核对实际处置/调查建议，如alerts.ai_recommendations或T/G.proposed_actions | 最新确认Explain.suggested_actions与其正文一起放在概况“发生了什么”，不要求响应Tab重复展示。本Tab具体数据接入后续核对；本轮保留现有页面 |
| 审批状态/执行结果 | 必须关联真实建议→审批→执行回执；G.executed_actions仅按记录范围展示 | 当前字段映射尚未证实统一审批/执行连接键；不应默认“待审核/未执行”来冒充已建审批单。需与响应模块合同单独核对 |
| Run ID/执行状态 | R.id/status/error/started_at/completed_at | completed只表示结束；无Run是“尚无自动处理记录” |
| 完成度/停止原因 | GE.completion；G.error/budget_exhausted_reason/investigation_depth等，依版本 | partial/unknown原样保留；不拿completed覆盖partial |
| 步骤名称/角色/输入输出 | E.kind/agent/summary/payload/input_hash/output_hash，K关联正文 | 旧graph_step仅node，不能保证每步都有输入/输出；缺正文明确未留存 |
| 查询/工具参数/返回 | E.kind=tool_call的payload.tool/args/result_preview；新tool_result仅对实际已发布版本采用 | 旧结果可能截断，不能标完整返回或根据200字preview判成功 |
| 调查发现/建议 | G.findings/proposed_actions；阶段区分首次分诊T | 不将建议记为已执行；不把调查结论覆盖首次分诊原件 |
| 调查报告 | K.kind=report_md的content/blob_ref | 有工件记录不代表正文可读；缺报告不重新触发生成，Markdown不按JSON解析 |
| 调用次数/tokens | `aisoc_run_costs.call_count`等用量行；R.total_tokens；E.graph_usage辅助核对 | iterations不是模型次数；计费未知不是0成本，避免多个聚合重复累计 |

### 4.4 管理告警及其他操作

下表保留已核旧技术路径作后续参考；Case关联、调查与反馈本轮只按4.1.2交接功能说明，不以此表预定新模块接口或实现规则。

| 操作 | 实际写入/入口 | 差异 |
| --- | --- | --- |
| 管理告警—处理状态 | PATCH alerts/{id} 写alerts.status，终态路径写resolved_at，并记录audit_log | 中文分组不能直接反向猜写入枚举；进入“进行中”可由明确修改状态或启动调查触发，不能由分配触发 |
| 管理告警—负责人 | PATCH assignee/assigned_to_id 写alerts.assigned_to_id/assigned_at；claim原子认领本人 | 用户已确认分配不变状态；人员选项需同租户目录，不用固定Alex |
| 管理告警—评论 | 当前原型写alert.comments数组；Alert模型无comments列，PATCH不接受comment | 需要另定告警备注/历史存储接口；不能借用反馈reason或Case评论来冒充普通告警评论 |
| 批量管理 | 对所选canonical Alert IDs更新，权限和租户一致 | 逐条还是批量原子、部分失败回执需约定；已有bulk-close不等于批量支持全部字段 |
| 关联/新建Case | Case创建/成员追加与Alert.case_id更新是不同路径 | 需要统一关系所有权与一致性，不能靠前端两次无事务写保证；是否允许替换关联待讨论 |
| 发起AI调查 | POST cases/{id}/investigate，Case成员集合准备输入 | 实际新增Run与Case关系写入分开反馈，不承诺整个流程一次成功 |

## 5. 必须逐项讨论的流程规则

### D1 处理状态：先定义业务动作，再定中文映射

已核：原前端使用new/triaged/investigating/resolved/false_positive；API模型注释含new/triaging/in_progress/resolved/fp/closed；自动持久化实际写triaged或resolved；is_unresolved只明确resolved/closed为终态。不同层存在词表漂移，不能挑一个文件就宣布统一。

**最新已确认（2026-10-25，仅映射规则，未改代码）：**

- `new/triaging/triaged` → 新建／待处理；自动分诊不代表已开始处理，快捷筛选和待处理计数覆盖三者。
- `in_progress/investigating` → 进行中；启动调查也算进行中，覆盖此前“只有人工直接改状态才进入进行中”的限制。仍以alerts.status取数，不从Run.running直接推导。
- `resolved/closed` → 完成。
- 分配/认领与状态独立；当前claim写assigned_to_id/assigned_at及首次确认first_seen_at，不改status。

其余待讨论：
- `fp/false_positive`是历史兼容状态，和disposition误报不是同一列；此次确认不包含这两个原值的归组。
- 未识别值保留原值/待核对，不默认新建或完成，也不能从工作队列丢弃。
- 启动调查应体现进行中已明确；除已核Case入口外，其他入口的状态写入是否一致还需核对。

**读写不对称：** 多个原值可以归同一个展示组，但用户选择“进行中”到底写哪个canonical状态必须明确。不按显示中文反向猜原值。

### D2 判定和关闭

**2026-10-25范围更新：** 当前只按4.1.2交接功能说明，具体实现随反馈功能建设后再细化。下方保留此前已讨论的行为和已核差异作为后续参考，不作为本轮要求实现接口或继续推导规则的任务。

**用户已确认（2026-10-24，仅规则记录，未实现）：** 页面实际按钮名为“保存反馈”。保存后的状态行为如下：

| 反馈选项 | 告警处理状态 |
| --- | --- |
| 误报 | 关闭告警 |
| 符合预期的正常或授权行为 | 关闭告警 |
| 真实威胁 | 保持原状态 |
| 需人工跟进 | 保持原状态 |

“保持原状态”不等于改为进行中，也不自动重开已关闭告警。上述规则针对当前告警保存反馈；相似历史批量反馈是否同步关闭尚未确认，不外推。

**人工直接关闭：** 需要额外流程，具体流程待定；不能把此前“通过管理告警直接关闭”的讨论提议当已确认方案。

**实现差异待后续处理：** 当前feedback写disposition，还写SLA resolved事件，未同时改变alerts.status；即使escalate也进入同一记录路径。后续应让实际状态、关闭时间和关闭记录与上述规则一致，不能对所有反馈记录关闭。本次没有改该接口。终态具体写resolved还是closed、正常/授权行为具体写benign还是benign_true_positive，仍需对齐字段合同，不在本条中擅自确定。

### D3 告警、事件、Case、Run

本节技术问题后置；当前Case关联仅按4.1.2描述功能，页面保持现状。

用户确认“告警必属于事件、Case可无”。落地需确保所有入口都提供F.incident_id；缺的历史记录不能生成假的事件。Case关联单值与成员数组须统一：改关联是转移还是多Case？创建/关联成功后不应隐式冒充调查已启动。

### D4 发起AI调查的实际目标

以下为后续Case功能细化时的参考，本轮不展开或实现。

现有Case调查接口从Case.alert_ids组装多告警输入；告警页按钮关联到已有Case后发起，可能调查整个Case，不只是当前告警。需要明确按钮含义、进入哪个页面、是否新增Run。未发布v2 profile/成员快照设计不能当现有行为。创建/关联成功但启动失败需分开提示，不能重试时重复建Case。

### D5 Explain请求与响应

用户已确认按当前请求方式使用Explain，调用及字段选用见4.1.1。summary正文、选用的contributing_events以及suggested_actions建议动作放在同一“发生了什么”区域；建议为空时内容留空，无需等预生成持久化。正文中可能出现结论或待核查问题，随实际内容展示，不单独解析成必填字段。实际审批/执行仍属响应模块，Explain建议不等于已执行动作。当前页面不改。

## 6. 核对依据与后续讨论顺序

1. 当前UI：[app.js](../app.js)、[alert-detail.js](../alert-detail.js)。
2. 已落地数据回执/具体SQL：取数映射（仓库参考路径：`docs/integration/v1/page-data-mapping.md`）、数据库字段字典（仓库参考路径：`docs/integration/v1/table-fields.md`）、21发布与自动链（仓库参考路径：`docs/integration/v1/production.md`）。发布回执中的历史任务完成数不是本稿的新验收结论。
3. 字段与写入：Alert模型（仓库参考路径：`services/api/app/models/alert.py`）、Fusion落库（仓库参考路径：`services/fusion/app/services/alert_sink.py`）、分诊持久化（仓库参考路径：`services/agents/app/investigator/ledger.py`）、资产模型（仓库参考路径：`services/api/app/models/asset.py`）、用户模型（仓库参考路径：`services/api/app/models/tenant.py`）。
4. 读取/操作：告警接口（仓库参考路径：`services/api/app/api/v1/endpoints/alerts.py`）、状态公共函数（仓库参考路径：`services/api/app/services/alert_status.py`）、详情聚合（仓库参考路径：`services/api/app/services/alert_rail.py`）、反馈接口（仓库参考路径：`services/api/app/api/v1/endpoints/feedback.py`）、Case接口（仓库参考路径：`services/api/app/api/v1/endpoints/cases.py`）、调查账本模型（仓库参考路径：`services/api/app/models/investigation.py`）。
5. 原版参考：`SOCAI/opensource/AiSOC/apps/web/src/lib/api.ts`、`AlertDetailView.tsx`，仅用于识别原展示和规范化歧义；20 overlay不能直接替代21取数。

讨论顺序：**列表处理状态与统计 → 等级/时间/来源 → 人员/资产映射 → 判定反馈 → 事件/Case/启动调查 → 解释、时间线、响应。** 每项记录“原值→展示值→筛选值→写入值→空值→已发布读取方式”。此前曾按授权展示真实只读快照，现已按用户最新要求恢复原页面；该次取数也不确定未决的服务端写入合同。

## 7. 21 本次实际字段值与缺口（2026-10-24 21:01 UTC+08）

本节保留当时取数及已撤回快照展示的历史回执，包含当时的文案和交互说明；当前列表及侧栏标准以第2节为准。例如resolved/closed现按“完成”分组，侧栏“发生了什么”取description，不混入分诊理由。

查询对象：**192.168.1.21 → PostgreSQL `aisoc` → schema `public`**，租户 `f6a5c700-69b8-44fc-8238-609362fb1a9f`。真实数据来自三条20测试告警的新身份重放；不是把20结果改名。以下为离线取数核对结果，不代表当前页面已接入。可直接使用[只读SQL](alert-ui-snapshot-queries.sql)查询同批告警。

| 页面信息 | 表 / 字段或路径 | 本次实值与展示 |
| --- | --- | --- |
| 告警标题 | `alerts.title` | `92070605…` = `Office启动隐藏PowerShell [DEMO-FIN-11]`，原样展示 |
| 告警时间 | `alerts.event_time` | 第一条 `2026-10-24 03:51:40.277842+00` → 北京时间11:51；不使用20:55的入库时间替代 |
| 严重程度 | `alerts.severity` | 三条均high → 高；其余等级无本批实测样本 |
| 处理状态 | `alerts.status` | 一条triaged → 新建/待处理，另外两条resolved → 已解决；分配不推导状态 |
| 检测源 | `alerts.enrichment_data#>>'{socai2_fusion,identity,source}'` | 三条 `showcase-security-sensor`；不存在`alerts.source`列 |
| 负责人 | `alerts.assigned_to_id` → `users.id,username`（同租户） | 三条NULL → 未分配；字段已有，分配/人员目录和登录身份写读未接UI |
| 受影响资产 | `alert_asset_correlations.alert_id,asset_id` → `assets.id,name` | 三条均无关联记录 → 资产匹配待补齐；仅展示`affected_hosts`报告的主机名，不伪造资产详情链接 |
| 资产标签 | 上述关联 → `assets.tags` | 无匹配资产，待补齐；`alerts.tags`或源数据synthetic标记不能替代资产角色标签 |
| 类别（当时核对） | 原候选`alerts.category`；现按确认改取`alerts.mitre_tactics` | category三条NULL；2026-10-25已明确本列按战术标签，三条mitre_tactics均Execution。页面未改 |
| 检测置信度 | `alerts.confidence` | 三条80（0—100） |
| 分诊模块评分 | `alerts.ai_score` / T.confidence | 原值0.85、0.95、0.95（0—1），底层为分诊判定置信度；2026-10-25用户确认页面评分选用此结果，100分制对应85、95、95 |
| 当前判定 | `alerts.disposition` | true_positive、false_positive、false_positive，来自自动分诊；人工反馈控件禁用并说明未接写回（当时快照状态，现已撤回） |
| 发生了什么 | `alerts.description` + T.rationale | 保留实际内容，明确自动分诊理由；没有预生成Explain，待补齐，不能用narrative冒充 |
| 原始数据 | `alerts.raw_event` | 原样JSON；没有拼接示例source_ref或假时间 |
| 事件 / Case | F.incident_id / `alerts.case_id` + `aisoc_cases.alert_ids` | 三条有真实事件UUID、无Case；仅展示关联文字，本轮不对接其页面 |
| 处理时间线 | `event_time,created_at,resolved_at,assigned_at` + E.ts/kind/summary/payload + R.completed_at | 最新在顶部；独立检测时间、完整人工变更历史待补齐，未伪造“已完成取证” |
| 自动处理过程 | R.status；GE.completion；G.budget_exhausted_reason / verdict | 三Run completed；第一条graph partial、needs_review、token budget exhausted (26309 of 20000)；其余自动分诊关闭、未调查 |
| 响应详情 | T/G.proposed_actions、G.executed_actions | 本次均无结构化响应动作；不填入虚构隔离建议，审批/执行回执后续接入 |
| 步骤 / 工具 | E.kind / payload | 旧graph_step仅节点；tool_call仅200字符预览，明示局限 |
| 报告 / 工件 | K.kind=`report_md` / `graph_result`，content、sha256、size_bytes | 原样保留第一条报告（模型内容质量未验收）；28份工件hash和字节均匹配 |
| 调用 / Tokens / 费用 | `aisoc_run_costs.call_count,total_prompt_tokens,total_completion_tokens,unpriced_call_count`；R.total_tokens | 9次调用、32667tokens，全部未定价；不能把total_cost_usd=0显示免费 |

上一轮曾将页面切换为本批三条的**只读静态快照**，含取数时间；列表筛选/排序/统计/CSV仅针对三条。此页面接入已按用户要求撤回，恢复此前设计稿、原数据和可用交互。以下描述仅记录撤回前的验证状态：“刷新”只重显快照；所有真实告警管理、反馈、Case关联、发起调查写入口均禁用并说明未接入。“分配给我”没有登录身份，显示待接入。事件/Case仍保留原型数据，不会用真实UUID打开某个虚构默认详情。

后续明确待补：人员身份与分配、实体到资产台账的匹配、资产标签维护、已确认战术标签的后端读取、Explain请求接入及返回内容选用（预生成不再是当前前提，不要求新增待核实事项字段）、已确认ai_score评分的展示接入、完整人工操作时间线、反馈关闭与响应审批写回。**没有数据不等于不存在对应表，也不等于无需建设。** 本次`is_synthetic=false`与原输入synthetic标签不一致是现有落库缺口，未修或据此把测试数据当真实攻击。


## 8. 2026-10-25 清理后六条真实重放对照

最新实值和已确认映射见本批回执（仓库参考路径：`docs/operations/alert-reset-replay-20261025.md`）。上文旧ID/计数是清理前证据，已备份，不再代表21当前库存。新六条均有真实Incident ID、无Case/资产关联/负责人。不要把`investigation_runs.case_id`（本批为告警拥有者ID）当作`alerts.case_id`。

首条`4c71eec2-77da-5b81-b68a-72801d55ea24`：`alerts.title`为Office启动隐藏PowerShell；severity=high→高；event_time=2026-10-25 03:30:16.539577+00:00；处理状态原值triaged，但有graph_step证明已进入调查，因此显示进行中。MITRE战术Execution→执行；检测源来自Fusion identity.source=showcase-security-sensor；主机DEMO-FIN-11、账户demo.finance为原始实体，尚未关联资产库存。资产标签空、负责人未分配。

Fusion置信度80；分诊ai_score=0.85→风险评分85；不得改取上游risk_score=0.92或Graph结果confidence=0.75。真实Explain HTTP200，summary及suggested_actions一起放发生了什么。该环境六条Explain均模板兜底（llm_used=false），页面不把模板称为已生成AI结论。待核实事项由返回文本自然表达，不强制结构化新增字段。

5条升级调查仍未关闭，1条FP自动关闭。6个Run completed只说明本次执行结束；5份Graph completion=partial，告警不因此改为已解决。实际工具只有result_preview（最多200字符），graph_step只有node，不虚构完整输入/输出。列表与概况保留既有分钟显示，时间线显示秒；底层保留微秒ISO发生时间用于排序/导出。

当前原型追加真实结果并保留原样例。Case与事件后端页面未接，Case/人工反馈/分配按钮仍为原浏览器本地交互，不能当作已写回21。未做全量查询，相关7条/相似5条仅从当前已取数据演示已确认功能，后端全量检索仍待实现。
