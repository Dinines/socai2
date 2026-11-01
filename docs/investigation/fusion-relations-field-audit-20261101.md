# 第3段：事件、对象、资产与Case关系核对

2026-11-01。对应[六段计划](field-alignment-confirmations-20261101.md#分段核对计划)第3段。以远端告警／事件页和已确认口径为需求，核对Fusion收到数据后的关系处理；前置输入缺失、错误和库存未提供不列修复任务。**本地核对完成，发现5组内部缺口；未修改业务源码、未修复或线上验收。**

需求基准仍为远端`codex/functional-analysis@48f54abd42d643ff53a71fffbb1f6045a90d9f80`，本轮只读`git ls-remote`结果未变。实现基准为`b758351d7125590c090a751837f96c86df331652`加当前已有工作区修改，不能把HEAD当全部当前源码。[证据索引](../operations/evidence/fusion-field-stage3-20261101/manifest.json)保存本段相关文件指纹；本轮未部署、创建Case／Run、调用模型或真实PG／Redis／图服务。

## 已支持与缺口位置

| 页面／调查需要 | 当前实际链路 | 核对结果 |
| --- | --- | --- |
| 当前事件有哪些成员 | Fusion为每条告警保存`enrichment_data.socai2_fusion.incident_id`；`read_incident`按租户和该ID查PG，以canonical Alert.id为成员身份 | 已支持。Redis窗口结束不使已保存的成员关系消失；没有把Case或Run ID当事件ID |
| 为什么归入同一事件 | Correlator使用主对象文本与首个战术，Redis保存索引及`IncidentSummary.correlation_keys`；告警PG副本保留incident_id、完整delivery_snapshot中的输入和fusion_decision，正常引擎也保存叙述 | 不是毫无依据，但缺可直接读取的结构化归并决策；对象类型还会发生键碰撞，见S3-01／02 |
| 共同对象、逐告警连线、对象来源 | PG已有每条告警的entities、affected_*及iocs；事件读取只返回实体并集，不返回每成员的对象／IOC／战术 | 并集可展示对象列表，不能单独还原每条边和共同对象的来源；IOC还在ORM层漏读，见S3-03 |
| ATT&CK阶段条数 | PG每条告警有mitre_tactics；事件接口只有全事件去重战术列表 | 原值足够时可计算；现DTO无法直接给出阶段计数。沿用第13项，每成员在各已有阶段各计1次，不从技术或标题补战术 |
| 库存身份及资产标签 | assets有tags；alert_asset_correlations有asset_id、match_field、confidence；现processing-context可按同租户名字／FQDN／IP或显式关联查库存 | 有可复用能力，但当前查询不返回tags和关联依据，事件读取未接入；只在entities中的主机也不用于该查找，见S3-04 |
| 选择告警创建／关联Case | F4核对所选告警与事件归属，写Case.alert_ids；另存选中／新增／已存在成员及source_incident_ids的不可变回执 | 已支持部分成员、多Case、重复请求读取原回执。创建／关联不启动Run；页面打开不自动补齐成员 |
| 当前Case关系与实际调查覆盖 | read_related按Case.alert_ids读当前Case，按Run已存selected_member_ids读历史运行；read_member_ids另列；覆盖查询不限当前历史页 | 已有能力，不应只看Alert.case_id或“有Run”就判断调查完成。旧入口与新关系表达不一致，见S3-05 |
| 旧Run是否被后来成员变化改写 | 启动保存all／selected／read成员和时间窗口；结果、步骤及Markdown从当次工件读回 | 当前代码支持冻结范围。不是每次读旧报告时重算当前Case；本轮未重新启动调查或做线上成员变更试验 |

## 5组内部缺口及最小修复方向

### S3-01 归并键没有对象类型

`RawAlert.correlation_key()`为`tenant:entity_text:first_tactic`，主对象优先级是src_ip→hostname→username→domain。主机`same-text`与账号`same-text`即使是两个独立canonical告警，也得到同一个键。

本地调用真实Correlator、仅替换Redis读写后，第一条新建事件，第二条实际并入同一事件，成员数2。输入明确提供不同对象类型，因此属于内部错误归并，不是输入质量问题。最小修正是键中保留对象类型、避免把“未知”当共同对象；部署时明确新旧键兼容，不能未经核实批量重组旧事件。

影响：事件成员范围、共同线索及成员转Case可能被错误扩大；模型即使拿到完整数据也会接收一个不可靠的分组前提。属于“可能影响后续调查范围”，不等于已证明线上报告由此出错。

现有“只选一个主对象／首个战术”和Redis处理时间窗口是当前策略：默认配置窗口3600秒，合并刷新summary TTL、未刷新原索引TTL；没有按event_time差值判断窗口。这里只记录实际行为，不自动把“全对象关联／攻击链推断／调整窗口策略”另立开发需求。

### S3-02 实际归并依据没有完整持久化／读取

PG保存事件归属和delivery_snapshot，snapshot保留原输入及NEW_INCIDENT／CORRELATED决定，不能说关系全在Redis。缺的是当次命中的对象类型／值、战术、所用窗口或策略版本等明确决策记录；`correlation_keys`仅在带TTL的IncidentSummary。正常叙述能说明新建／加入及当时数量，但不是详细归并规则。检测rule_id不能冒充事件归并rule_id；另存的attack_chain也不是同一条Fusion事件关系。

最小方向：在已有Fusion元数据中随决策保存实际采用的依据，并由事件读取返回。旧记录只展示可由已有成员核实的共同线索；没有当时依据时继续显示“未提供具体归并规则”，不根据今天配置反推历史事实，也不要求上游新增归并材料。

影响：页面无法可靠回答“当时为什么归入”；调查只能把共同对象视作来源线索，不能把同事件关系当已证实攻击因果。

### S3-03 已存IOC漏读，事件投影丢失逐告警关系

1. Fusion sink把hash／domain／url及IP写入PG `alerts.iocs`，主机／账号另写entities。迁移001已有iocs列；**API Alert ORM没有映射iocs**，正常`select(Alert)`不会读出这列。
2. `incident_reader._entities`只取affected_hosts／users／ips及entities，不读iocs；事件DTO返回去重并集，IncidentMember不含逐成员实体、IOC、战术、资产关系。因而不能只靠该返回值还原“哪条告警提供哪个对象”、共同对象来源和阶段条数。
3. Case当前为每条告警分别调用`_entities([alert])`，保留已投影主机／账号的归属，**并非所有Case对象关系都丢失**；但同样漏掉仅存iocs列的对象。已有raw可能重复携带这些值，不保证每次都有，也不代替结构化读取。

本地以实际sink生成的两条投影为输入：每条iocs有一个hash和一个共同domain，事件返回只有host／user，Case共用实体提取也不含这两个IOC。首次夹具直接把iocs传入ORM时得到TypeError，暴露了更早的映射缺口；修正夹具为仅装载真实映射列后完成观察，没有给ORM临时补字段或修改业务实现。

最小方向：映射并读取已存在的iocs，构造带`source_alert_id`的逐成员对象关联；事件对象汇总和共同线索由这些关联聚合。阶段计数基于已有逐成员战术去重，不是把全局战术列表长度当告警数量。共同对象不代表实体间攻击、控制或传播关系。

已有Graph服务能保存多主机／多账号以及带source_alert_id的OBSERVED_ON、INVOLVES_USER、CONTAINS_IOC边，并明确是来源告警报告的关系；无需另造图框架。但现prepare_investigation_graph也只提取affected_*／entities，未读PG iocs；其入口是启用开关的旧v1 Case调查／图上下文，不能据此声称当前事件接口或v2 Case循环已消费这些边。告警详情rail还能从部分raw提取domain／url，属于另一读取路径，不能代替事件投影。

### S3-04 已有库存与标签没有进入所需关系视图

`processing_context.ASSETS`支持同租户查询与显式alert_asset_correlations，结果区分matched／no_match／unavailable；多候选或截断时优先级标ambiguous，已有这些能力无需重建。但是查询未选`assets.tags`，也未返回关联表的match_field／confidence。事件DTO没有库存关联；Case当前告警输入也不调用这个读取，调查应如何选择消费留第5段核对。

另一个具体遗漏：该查询仅从affected_hosts／users／ips取查找键。已有合法entities中有host而affected_hosts为空时，本地观察传入查找的hosts仍为空；不是要求上游补一个重复字段。显式关联子查询仍能独立命中，本地空返回替身不能证明线上一定查不到资产。

最小方向：在需要的告警／事件投影复用现有库存读取和显式关系，补标签及匹配来源，保留多个候选／未知状态；查找键覆盖已经保存的有类型实体。标签只取assets.tags，不用告警tags代替。观察到主机名不能自动等同库存身份，无匹配时保持普通对象；未提供库存／关联不列上游待办。“涉及资产”按已定页面口径计主机，不偷换为所有实体数。

### S3-05 Case旧单字段与当前成员集合口径并存

F4和旧`POST /cases/{case_id}/alerts`写Case.alert_ids，当前Case调查及read_related也用这个集合；F4未回写单一Alert.case_id，这是支持一告警多Case时合理的选择。可是旧Alert PATCH仍只更新Alert.case_id，IncidentMember也继续暴露这一单值。于是仅用单字段显示关系会漏掉合法Case，或显示一个未在当前Case.alert_ids中的Case。

旧图上下文`_anchor`又使用“Case.alert_ids **或** Alert.case_id”的并集；当前v2 Case调查只认前者。若两者不一致，两入口范围可能不同。不能把旧图范围自动当本次v2 Run输入，也不能声称当前F4关联失败。

最小方向：页面当前关联和调查范围统一使用已有多Case读取；梳理仍在使用的旧单字段写入口，使其走明确成员关联合同或明确其兼容含义，不靠双向同步一个单值丢掉多Case。已有link回执继续表示当次选中范围，不充当当前成员表；旧Run冻结范围和报告保留，不自动扩充或改写历史。

## 验证、边界及后续

- [本地探针](../operations/evidence/fusion-field-stage3-20261101/probe.py)记录6项不同观察：归并类型碰撞；sink保存IOC／事件归属及决策结构；ORM未映射iocs；事件／Case实体提取遗漏IOC；事件仅并集而无逐成员关系／阶段计数；库存查找漏用entities中的主机。见[Fusion两项](../operations/evidence/fusion-field-stage3-20261101/fusion-observations.json)和[API四项](../operations/evidence/fusion-field-stage3-20261101/api-observations.json)。断言确认当前行为及缺口，不是6项功能验收通过。
- 初次API夹具构造错误保留[记录](../operations/evidence/fusion-field-stage3-20261101/initial-api-failure.json)及[初版探针](../operations/evidence/fusion-field-stage3-20261101/probe-initial.py)。该次0项API观察完成；仅重做修正后的API部分，Fusion两项复用，未为凑一次全绿重跑。
- SQL执行／Redis读写使用本地替身；没有实际PG装载、TTL过期试验、图写入、库存匹配或线上数据改动。源码调用与查询投影说明可触发路径，不证明当前线上已经触发五组问题；现场Fusion版本／配置仍未核。
- Case链接、部分成员、历史范围及原报告读取按当前实现与既有直接用例核对；[Case链接用例](../../services/api/tests/test_case_links_api.py)、[成员覆盖用例](../../services/api/tests/test_related_investigations.py)本轮只读，不新增通过次数，不重跑已验流程。本轮没有模拟新的Run／模型来证明历史范围。
- 已定位的来源ID、时间、主机提取、窗口参与事件和会话断点沿用S1／S2，不重复立项；旧报告r13问题和5.3未完成状态保持。本文不能证明补齐字段就能解决报告语义问题。

下一第4段核页面API及业务管理：列表／详情、筛选排序统计导出、反馈关闭、负责人同步及提示、事件生命周期和处理活动。尤其继续核第8项首次活动时间与第15项最近更新时间：当前first_seen取成员first_seen，attach_related又把Run时间并入source_updated_at；与用户口径的差异留下一段统一处理。没有新增需要用户决定的关系口径。

## 主要代码依据

- Fusion：[归并键](../../services/fusion/app/models/alert.py)、[归并执行及TTL](../../services/fusion/app/services/correlator.py)、[实际决策／叙述](../../services/fusion/app/services/fusion_engine.py)、[PG字段和snapshot](../../services/fusion/app/services/alert_sink.py)。
- 读取：[Alert映射](../../services/api/app/models/alert.py)、[事件成员及实体汇总](../../services/api/app/investigation_v2/incident_reader.py)、[库存模型](../../services/api/app/models/asset.py)、[库存上下文](../../services/api/app/services/processing_context.py)。
- Case：[成员关联](../../services/api/app/investigation_v2/case_links.py)、[当前关系与历史覆盖](../../services/api/app/investigation_v2/related_investigations.py)、[启动冻结与结果读取](../../services/api/app/investigation_v2/case_analysis.py)、[保存报告读取](../../services/api/app/investigation_v2/case_views.py)。
- 兼容入口：[旧告警更新](../../services/api/app/api/v1/endpoints/alerts.py)、[旧Case成员及调查](../../services/api/app/api/v1/endpoints/cases.py)、[图上下文投影](../../services/api/app/services/investigation_attack_context.py)、[来源关系边](../../services/api/app/services/graph_service.py)。
