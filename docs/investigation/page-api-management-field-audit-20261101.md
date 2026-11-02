# 第4段：页面API与业务管理核对

**2026-11-02实施更新：** [第4批](field-alignment-fix4-20261102.md)已补S4-02共享来源/对象/负责人/同次评分，以及S4-07发生时间、成员业务updated_at和GET不写入。事件自身管理时钟随第6批写入接入；筛选/统计/导出及管理级联未完成。以下保留修前事实，尚未线上验收。

2026-11-01。以[六段计划及第1—16项决定](field-alignment-confirmations-20261101.md)为准，核对告警／事件页的读取、筛选、统计、导出及实际管理写入。**本地核对完成，归为8组对接问题；尚未修复或线上验收。** 前置输入问题继续排除，S1—S3已定位的字段／关系缺口只追踪影响，不重复立项；调查页面不作设计比对。

远端需求分支本轮`ls-remote`仍为`48f54abd42d643ff53a71fffbb1f6045a90d9f80`。本地为`b758351d7125590c090a751837f96c86df331652`加原工作区修改，版本和文件指纹见[证据索引](../operations/evidence/fusion-field-stage4-20261101/manifest.json)。本轮无业务源码修改、真实数据库写入、模型／Run／部署或真实响应动作。

## 页面功能支持表

| 功能 | 已有实现／可以复用 | 缺口与承接规则 |
| --- | --- | --- |
| 告警列表及概览侧栏 | `GET /api/v1/alerts`返回标题、描述、原等级／状态、战术、发生时间、affected_*、Fusion置信度等；分页上限200 | 原厂来源、资产ID／标签和负责人投影不足；已存数据不等于列表已经返回。来源未知留空，资产／IOC沿S1／S3 |
| 告警完整详情 | `GET /alerts/{id}`另有raw_event、source_event_ids、external_id、fusion_identity／incident_id、实体、建议及简短活动；Explain另有结构化接口和回退标记 | 来源ID应取Fusion identity.source_alert_id；v2告警上下文／事件成员同名字段却取external_id。详情也不返回负责人ID／姓名及完整规则列；不能把connector_type当原厂 |
| 搜索、筛选及排序 | 当前支持单值severity／status／category、分配给我、置信度及newest／priority；条件作用全量查询而非当前页 | search声明但未使用；时间、来源、资产标签、任意负责人等条件未接；category不是战术；中文分组及双向event_time排序未支持，见S4-01 |
| 顶部四卡 | **已有`GET /alerts/stats`总体total／by_severity／by_status**，不跟随列表筛选；可组织全部、高、待处理三卡 | 列表facets跟随过滤，不适合第9项；“调查进行中”缺真实调查阶段的告警去重聚合，不能用running Run数／处理状态替代 |
| 导出／列设置 | 列设置为UI偏好；告警列表可请求page=1、page_size=200，明确所选ID也可逐条读取详情 | 远端exportTable目前导出全部本地筛选结果，忽略勾选且不限200。按第10项，有勾选导出所选，无勾选取当前筛选／排序前200；无专用导出接口本身不是必须新增接口的理由 |
| 告警状态与分派 | PATCH能写状态、负责人／解除分派，关闭写resolved_at，审计含前后值；claim不改状态 | 单独分配不进入处理中已符合；普通PATCH无评论字段、批量关闭不等于批量全字段管理；旧终态分类、重开时间、v2启动状态见S4-03／05 |
| 当前告警反馈 | 保存判定、理由／既有学习材料；存在人工判定读取 | 当前未按误报／正常授权同步关闭，却对所有反馈写SLA resolved；不符合已定规则，见S4-04 |
| 相似历史反馈 | 候选检索、勾选ID提交、集合token及同租户更新已有 | 应用只更新disposition，不关闭；从完整候选改选子集须同步提交该子集的token合同，不扩大为全部候选 |
| 事件列表及管理 | 事件ID和PG成员已保存；已有单事件概况／调查记录读取、AI概况首次／手动刷新 | 没有承接目标事件队列的分页聚合及完整管理写入；标题、独立状态、负责人、标记、解决说明和活动缺持久化合同。`/mssp/incidents`实际是跨租户开放告警列表，不能当Fusion事件列表 |
| 事件解决／负责人联动 | 远端原型在浏览器localStorage中实现成员同步 | 第14项覆盖全部成员负责人；新确认第16项解决事件关闭全部成员但保留判定；两者均须保存前提示、真正落库并读回，不能只做提示 |
| 事件发生／更新时间 | 当前可从成员及Run材料得到各自时间 | `first_seen`不是最早event_time；`source_updated_at`是材料新鲜度，含分诊／可选Run时间；详情GET还会补写告警updated_at，见S4-07 |
| 处理活动／自动处理 | 告警audit、CaseTimeline、v1 Run事件／工件及v2 execution_index等能力存在 | 当前mini_timeline只取最多6条，还混入整个旧单Case的活动；没有统一的事件管理活动读回，见S4-08。执行结束／partial／人工关闭不能互相替代 |

## 8组问题与最小修复方向

### S4-01 列表查询与导出范围不符合页面合同

实际ASGI请求验证：携带search与不携带生成的SQL和参数完全相同；传start／end／source／owner／tag／ids也返回200并被忽略。有效severity=high只过滤high，不包含critical；status=new不包含triaging／triaged；category过滤通用category，不能承接已定战术标签。

newest按created_at倒序，priority按原等级再created_at倒序；两者没有event_time双向选择，也没有唯一ID作同时间的排序补充。代码注释称created_at使顺序完整，但相同时间并不唯一。本地只确认实际SQL，不冒称真实数据库分页已出现重复。

最小方向：接上页面实际条件、统一等级／状态显示分组和原值集合，增加明确event_time排序及稳定补充键；保留旧API默认排序的兼容含义。导出复用同一筛选／排序与字段映射：有选择按选中ID，无选择前min(总命中,200)，超200直接截取，不提示缩小范围后阻止。不能只在加载的一页里筛选／排序后声称全量。

### S4-02 已有字段的页面投影仍不完整

AlertResponse及AlertDetailResponse未声明assigned_to_id／assigned_at或负责人显示名，虽然ORM有列、PATCH能写、queue接口另有assigned_to_id。调用列表／详情不能靠affected_users填负责人；ID存在但姓名未解析也不能说未分配。

来源字段需分工：详情fusion_identity可提供接入来源ID，但原厂显示须有明确原值，不能回退为Splunk等中转。`alert_context_api.source.source_alert_id`与IncidentMember.source_alert_id当前都用external_id，违反第2项；这继承G01，不另把它算上游缺数据。规则ID／名称、资产标签和对象归属沿S1／S3补必要投影。

分诊ledger已保存同次verdict、confidence、rationale、findings、proposed_actions、auto_closed；写回Alert.ai_score及摘要，自动关闭才改resolved，否则仅new进triaged、其他状态保留。SavedTriage读取却漏confidence，页面若把当前Alert.disposition与旧ai_score拼接会错配。按第6项返回同次判定、分数和理由；具体Case消费留第5段核对。来源描述、Explain、既有分诊和调查报告继续分开。

### S4-03 处理状态、调查状态及统计口径不统一

`alert_status.RESOLVED_STATUSES`只有resolved／closed，fp／false_positive会被is_unresolved计为未完成；但queue自身已经把这两项排除。需统一第7项的页面分组及相关查询／统计，保留误报标记，不能仅因为disposition=误报就把未关闭记录显示完成。

三张总体卡可直接复用stats原始聚合后按已定分组计算，不需另建整套统计。列表facets仅解释当前筛选结果。“调查进行中”需要真实调查阶段／profile和仍在运行的记录按告警去重；execution_index保留旧记录与v2记录入口，但它本身不是总体卡聚合，也没有把旧分诊Run自动判成正式调查。

当前v2 `case_analysis_api → start_analysis → CaseAnalysis`只创建／执行Run，没有写选中Alert状态；旧v1 Case启动另有告警investigating写回。此为G03的当前接线缺口：真实启动的未关闭成员仍可能显示待处理。最小修复应在本次调查准入／启动得到确认后更新相应未关闭成员，不复制旧入口“先改状态再发代理请求”的时序；不回退已关闭状态、不因普通Case关联／分配而改变状态。

普通PATCH关闭可不填说明，符合第11项；但重新设为非终态时没有清理resolved_at。需让当前处理状态与当前关闭时间一致，完整历史关闭时间留实际活动，不靠一个旧resolved_at解释当前已关闭。此项静态定位，未做真实重开。

### S4-04 反馈只改判定，关闭与SLA记录相互矛盾

本地调用实际submit_alert_override，替换数据库、SLA和学习副作用，分别传false_positive、benign_true_positive、true_positive：三次UPDATE均只有disposition／updated_at，没有status／resolved_at，三次却都请求SLA resolved记录。历史apply_redisposition也只改disposition。

按已定规则：当前或勾选相似告警反馈为误报、正常／授权行为时同步关闭；真实威胁／需跟进保留原处理状态。SLA关闭事件依据实际关闭写入，不把所有改判等同关闭；保留当时人工理由及原分诊，防止报告把人工改判与旧分诊评分混成同次判断。

候选全集token不能直接用于勾选子集：本地两候选选一个时，原token在SQL前被拒；按该一个ID生成对应token后可以提交，且SQL只限该ID。这不是“后端完全不支持勾选”，是前后端提交需要对齐选择集合；保留现有集合核对，不通过扩大范围绕过校验。

### S4-05 普通告警评论和批量管理未完整承接

普通PATCH接受status、priority、tags、assigned_to_id／assignee、case_id；comment会被明确拒绝。关闭说明选填不代表用户填写后可以丢弃。远端管理表单会把普通评论写入告警comments，但后端没有对应普通告警评论写入／读取合同，不能借反馈reason或Case评论代替。

已有bulk-close能按ID关闭、可选comment并留批次审计，但不等于批量分派／一般评论接口；批次审计无单一resource_id，不会被当前按单告警resource_id读取的mini_timeline自然展示。纯条件批量关闭的OPEN_STATUSES还漏triaged，而显示待处理包含triaged；显式ID路径不受此项限制。

最小方向：围绕现有管理保存动作补实际评论保存和可追到每条目标告警的变更记录，明确批量各目标结果；复用现有状态／分派能力。不增加手动关闭必填说明或新的用户审批步骤。状态写入枚举应明确映射，不把中文／原型New等文本直接作为后端任意status字符串写入。

### S4-06 事件管理缺后端持久化与成员联动

现有Fusion事件归属是告警JSON中的incident_id；`fusion_incident_summaries`保存AI概况和来源指纹，并不是事件管理表。IncidentOverview标题由首个成员标题拼接、等级取成员最高值，handling_status固定空；没有独立负责人、事件标记、解决说明的写入／读回。现有事件API只有单事件GET、investigations、overview/refresh，不能承接事件列表及管理表单。

最小方向：以既有Fusion Incident UUID保存事件业务管理字段、活动及当前成员聚合；不拿aisoc_cases代替事件，不另建事件调查循环。按已定规则实现：

- 改派负责人覆盖全部当前成员的负责人，包括已有负责人的记录；保存前在表单内提示覆盖范围，仅标题等变化不触发该联动。
- 手动解决事件须填写事件解决说明，同步关闭全部成员告警但保留各自判定；保存前提示全部关闭范围。本轮用户已明确确认第16项。
- 使用原“保存”动作，提示无需再加确认弹窗；提示、持久化、成员联动、变更记录及读回一起才算功能完成。
- 告警／Run结束不反向自动解决事件；已有关联Case及历史Run材料不因事件管理被改写。自动事件AI概况不能当业务状态。

事件列表／统计从事件业务状态及明确成员聚合，排除把Run数、Case数或所有实体数当事件指标。远端统计卡整体口径保留；具体事件列的现成过滤、排序、批量管理都需要真实后端承接，浏览器localStorage保存不等于正式写回。

### S4-07 发生时间、业务更新时间与材料新鲜度混用

第8项事件首次活动应为成员最早event_time；read_incident当前取min(first_seen)。第15项业务最近更新时间包括事件及成员变化，但`source_updated_at`还包含分诊记录时间，attach_related在纳入调查材料时再取Run起止时间；这应继续用于材料新鲜度，不能直接改名当业务更新时间。

新增一条实际路径：`GET /alerts/{id}`遇无narrative的旧告警，会本地生成叙述并UPDATE narrative、updated_at、commit。单独本地调用该handler、替换叙述生成及数据库后，捕获到该写语句。普通查看因此可能改变事件成员的更新时间，与用户明确“普通查看不改变业务更新时间”冲突。

最小方向：从正确的event_time聚合活动范围，业务更新时间覆盖实际管理／成员变化；叙述缓存、概况生成及Run材料更新使用各自时间，不污染业务时钟。S1-06来源追加未更新updated_at继续沿用处理，不能只换读字段而漏掉真实成员材料变化。保持概况stale判断所需材料指纹，不为页面时钟修正取消材料变化检测。

### S4-08 处理活动存在来源混用和读取覆盖缺口

mini_timeline只取最多6条CaseTimeline与Alert审计；Case部分仅按旧单Alert.case_id过滤，没有逐告警来源条件。本地构造同Case、metadata.alert_id明确指向另一成员的评论，真实build_mini_timeline仍把它放进当前告警时间线。可以作为有来源标注的Case活动展示，不能解释成当前告警自己的处理事实；多Case关联问题沿S3-05。

时间线也没有自动合并完整的发生／检测／入库／分诊／正式调查／反馈历史。已有v1事件与工件读取、v2 execution_index可复用，但旧Run存在不证明正式调查，completed也不覆盖partial。当前通用audit列表没有resource_id查询参数，不能拿一页租户审计在浏览器过滤后称本告警完整历史。

最小方向：以canonical告警／事件及实际操作目标组织活动，保留来源类型和操作者；按真实时间分页读取。没有检测时间就不造“发生后15秒”，没有记录就不从updated_at推导历史。事件操作及批量动作要能回到目标成员，Run进度可显示在活动但不改业务更新时间。

## 现有能力与未验范围

- Explain已有独立结构化接口，返回summary、suggested_actions及llm_used／source／reason；列表侧栏仍取来源description。此次未调模型，也不把Explain存在当原告警事实已验证。
- 响应建议可从alerts.ai_recommendations／账本取得。审批API有alert_id／case_id／run_id和实际decision／dispatch记录；因此不能说系统没有审批执行能力。但列表未按告警／Run筛选，普通建议项到审批的统一关联未在本批原件中验证，页面只能展示能明确关联的真实审批／执行回执，不凭建议生成“待审核”状态。本段没有审批、厂商调用或执行专项测试。
- 负责人字段和用户目录都已有基础，不能以投影缺字段推断没有用户系统。实际租户目录可见范围、线上各用户姓名及真实库存命中本轮未验，不扩权限专项。
- 旧分诊写回及Case启动路径为源码核对；未重跑真实分诊、启动或当前已通过的Case关联／报告流程。报告问题r13继续保留，批次不重试，5.3不核销。

## 本地验证记录

共11项不同观察：首批前9项断言执行完成，第10项时间线夹具错误；改正夹具后仅完成该1项，另对新发现的详情GET时钟写入完成1项。**不称一次11项全通过或功能验收通过。**

- [初版探针](../operations/evidence/fusion-field-stage4-20261101/probe-initial.py)经真实alerts路由ASGI验证搜索／未声明参数，再用实际函数和捕获SQL核状态、反馈、时间。首次在构造CaseTimeline时将只读is_automated属性当可写字段，报AttributeError，属于夹具错误。
- [首次结果说明](../operations/evidence/fusion-field-stage4-20261101/initial-result.json)保留9项已执行断言和失败边界。初版只在整次成功后保存结果，因此前9项响应／SQL明细未落文件；不伪造原件、不将后续代码推导冒称原始回包。代码及工具异常位置能证明执行到第10项前，原9项未为重新得到全绿而重跑。
- [修正探针](../operations/evidence/fusion-field-stage4-20261101/probe.py)使用真实actor_type列，`--timeline-only`仅运行该项，见[时间线结果](../operations/evidence/fusion-field-stage4-20261101/timeline-followup.json)。
- [详情GET定向观察](../operations/evidence/fusion-field-stage4-20261101/read-time-followup.py)及[结果](../operations/evidence/fusion-field-stage4-20261101/read-time-followup.json)只覆盖新发现的缓存写时钟路径。叙述生成替换为固定文本，不调用模型。
- 所有DB、认证、Redis／学习副作用均使用本地替身；没有模拟SQL筛选／并发来冒充真实数据库行为。静态接口缺失、原型导出和v2启动缺状态写回另按源码登记，不计入11项执行观察。线上触发、真实管理写回及页面接入均未验。

下一第5段：沿同一条数据链核Case实际冻结来源、分诊配对、模型可见输入、Tool参数与返回、历史复用。已有字段不等于都应送模型；按功能需要判断遗漏，不新增Case记忆系统。

## 主要代码依据

- [告警列表／统计／详情／管理](../../services/api/app/api/v1/endpoints/alerts.py)、[状态分组](../../services/api/app/services/alert_status.py)、[队列与认领](../../services/api/app/services/alert_queue.py)、[批量关闭](../../services/api/app/services/alert_bulk_close.py)。
- [反馈API](../../services/api/app/api/v1/endpoints/feedback.py)、[历史改判](../../services/api/app/services/override_learning.py)、[集合token](../../services/api/app/services/memory_poisoning.py)、[分诊ledger](../../services/agents/app/investigator/ledger.py)。
- [事件API](../../services/api/app/investigation_v2/incident_api.py)、[成员读取](../../services/api/app/investigation_v2/incident_reader.py)、[调查材料附加](../../services/api/app/investigation_v2/related_investigations.py)、[AI概况表及指纹](../../services/api/app/investigation_v2/incident_summary.py)。
- [告警上下文来源字段](../../services/api/app/investigation_v2/alert_context_api.py)、[v2启动](../../services/api/app/investigation_v2/case_analysis.py)、[旧启动路径](../../services/api/app/api/v1/endpoints/cases.py)、[执行索引](../../services/api/app/investigation_v2/execution_index.py)。
- [活动读取](../../services/api/app/services/alert_rail.py)、[审计列表](../../services/api/app/api/v1/endpoints/audit.py)、[审批及派发](../../services/api/app/api/v1/endpoints/approvals.py)、[Explain](../../services/api/app/api/v1/endpoints/alert_explain.py)、[MSSP同名入口](../../services/api/app/api/v1/endpoints/mssp.py)。
