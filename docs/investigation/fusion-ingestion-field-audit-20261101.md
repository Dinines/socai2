# 第1段：Fusion输入到告警入库核对

2026-11-01。**本地实现核对完成，发现字段缺口；未修复，未完成线上链路验收。** 本段以[主记录及已确认口径](field-alignment-confirmations-20261101.md)为准，从Fusion输入一直核到PostgreSQL写入，并检查其对页面及Case取数的直接影响。后续按原计划核湖事件对应，不先扩展报告框架。

远端需求分支本轮只读核实仍为`48f54abd42d643ff53a71fffbb1f6045a90d9f80`；本地HEAD为`b758351d7125590c090a751837f96c86df331652`，工作区另含既有r13改动，不能以HEAD代替全部当前源码。实际调用的Fusion文件指纹随[本地观察结果](../operations/evidence/fusion-field-stage1-20261101/observations.json)保存。

## 用户补充边界及结论重分类

用户随后明确：**Fusion前置输入数据的问题不用处理。** 以下代码观察和原始验证结果保留，但8项观察不再笼统等于8项完整修复任务。输入未提供、不准确或上游规范化造成的缺失，只记录限制，不追查、不要求上游补齐，不阻塞后续核对。

| 原编号 | 本轮保留处理范围 | 排除范围 |
| --- | --- | --- |
| S1-01 时间 | 输入已有有效时间被漏传；内部用入库时间冒充发生时间；事件汇总取错时间字段 | 追查或修复上游缺时间、错误时间、错误时区 |
| S1-02 原厂 | 已有明确原厂值正确读取；未知留空，避免拿接入平台／规则名冒充原厂 | 原厂输入缺失或无法判断；新增上游原厂采集／字段要求 |
| S1-03 身份 | 已有可区分的来源身份被Fusion旧指纹忽略、独立发生被合并 | 输入根本没有可区分身份、来源ID不稳定或错误；要求上游重新设计编号 |
| S1-04 规则／战术 | 输入或Fusion已有检测规则明确携带的值在内部丢失、未投影、误用 | 输入和现有规则均无值时补标签／推断战术或追查上游 |
| S1-05 实体 | 已收到的主机／用户／IP等未正确提取、保存和供调查使用 | 输入本来没有实体或实体本身错误；要求上游补字段 |
| S1-06 来源引用 | 已收到的引用被内部截断却未说明；窗口内已收到事件未保留关联；真实成员变化未更新时间 | 原始日志未提供、输入引用不完整或错误；追查采集和补采 |
| S1-07／08 | Fusion自行生成的评分状态及自身提升开关，继续属于内部实现范围 | 不扩展上游评分质量或检测规则质量审查 |

未知输入被下游误写为确定值、错误展示或当成事实分析，仍是我们的处理问题。仅仅因输入没有某字段而无法展示／查询，则不列为本轮修复项。下方字段表和问题表按此边界解读。

## 入口必须分开判断

| 入口 | 当前处理 | 本段结论 |
| --- | --- | --- |
| 已有告警HTTP接入 | `ExistingAlert`要求event_time、1—100个source_event_ids；source-v1配置下要求显式稳定id，接收端生成source_alert_id及认证租户，再发Kafka | 规则、战术、实体等RawAlert已有字段可直接透传；有数据能保存，不等于生产调用方已提供 |
| Kafka直接RawAlert／Fusion `/process` | 使用RawAlert模型；event_time、raw_event等可缺省；identity默认legacy-v1；`/process`把输入id加到来源事件引用 | 合同弱于已有告警HTTP接入，不能用HTTP必填证明全部Fusion输入必填；输入告警UUID也不天然是湖事件UUID |
| 规范化事件提升为告警 | `promote_normalized_event`读取OCSF；保留OCSF为raw_event；只映射部分字段；未设置source-v1身份 | 能保留有效ISO时间、特定格式的MITRE标签和部分实体；没有独立来源告警身份、规则和完整实体投影 |
| 单事件规则检测 | DetectionHit→RawAlert，保存规则ID/名称、技术列表和当前OCSF | **没传事件时间、战术列表**；仍用legacy身份 |
| 窗口／序列检测 | DetectionHit→RawAlert，实体从flat raw_data读取，保存触发时OCSF | 同样没传事件时间、战术列表；窗口命中只交付规则信息，没有全部参与事件及窗口范围 |

证据：[HTTP接入](../../services/api/app/api/v1/endpoints/alert_ingress.py)、[RawAlert](../../services/fusion/app/models/alert.py)、[consumer](../../services/fusion/app/workers/consumer.py)、[同步入口](../../services/fusion/app/api/router.py)、[提升](../../services/fusion/app/services/promoter.py)、[单事件检测](../../services/fusion/app/services/detection_engine.py)、[窗口检测](../../services/fusion/app/services/windowed_detection.py)。

## 字段从输入到存储

| 需求字段 | 来源→转换／保存位置 | 当前支持与缺口 |
| --- | --- | --- |
| 检测源（原厂） | 直接输入source自由文本；提升取`metadata.product`厂商／产品标签，缺失变`ingest`；检测生成`detection:{rule_id}`；落`enrichment_data.socai2_fusion.identity.source` | **未定义独立、可确认原始厂商的字段语义**。connector_type可能是接入平台，product标签也不能无条件证明中转前的原厂。已确认未知留空；不能直接拿这些值兜底 |
| 平台告警ID | `deterministic_id()`→alerts.id→对外canonical ID | source-v1已按租户、source、connector和稳定来源UUID区分；legacy仍按特征折叠，见S1-03 |
| 接入来源编号 | HTTP source-v1从输入id生成source_alert_id→Fusion identity JSON | 直接接入有明确路径；提升和两类检测未设置，值为空。不能用external_id或湖事件ID代填 |
| 厂商编号 | 直接external_id；提升取finding.uid，回退metadata.uid，裁至512字符→alerts.external_id | 有保存路径；只按已有明确来源含义读取，输入含义不明仅记限制，不追查上游。规则检测无此投影，不能把本地规则ID当厂商告警编号 |
| 原始事件引用 | 输入source_event_ids；consumer再追加schema解析出的event_id/id/metadata.uid→JSON列 | 引用存在不证明对应湖行存在；追加去重有200项上限且不标溢出，窗口检测未交付完整参与事件，见S1-06及第2段 |
| 告警发生时间 | 直接event_time；提升解析OCSF.time；sink为None时`COALESCE($17,NOW())` | **两类规则检测漏传已有时间**；未知／非法时间变成入库时刻且无来源标记，见S1-01 |
| 首次／末次观察、更新时间 | sink未写first_seen/last_seen/created_at/updated_at；迁移默认NOW；折叠来源追加只更新source_event_ids | 这些不是发生时间范围。Redis事件first_seen取alert.created_at、last_seen在新成员时取当前时间，也不能代替第8项确定的成员最早event_time |
| 标题、描述 | RawAlert→title裁500、description原值或NULL；提升标题裁500，描述优先raw_data文本、finding.desc等，裁2000，重复标题置空 | 有基础路径；提升／检测保留的OCSF仍含输入文本。直接输入的完整title只在首次快照中，不能称主列完整无截断 |
| 严重程度／处理状态 | 直接枚举或medium默认；提升按severity_id映射；检测按规则severity；sink状态固定new | 严重程度是来源／规则分级；缺省medium不证明来源给了中危。新告警从new开始属于当前接入合同，不继承来源系统处置状态；后续状态联动在第4段核 |
| 规则ID／名称 | RawAlert.rule_id/name→独立列；两类检测从DetectionHit赋值 | **提升分支不提取厂商规则**，即使规则留在raw_data也没有独立列。已有告警HTTP有值可传；Case是否消费在第5段核 |
| ATT&CK战术／技术 | 直接数组；提升读`mitre_attck[].technique_id/tactic_names`并去重→JSON列；两类检测仅hit.mitre→技术列 | **检测生成告警战术为空**。rule.category写入描述，不是可直接用于阶段统计的战术数组；不能从标题或技术号猜标签 |
| 主机／用户／IP、IOC | RawAlert的单值hostname/username/src_ip/dst_ip等→entities、affected_*、iocs；提升与单事件检测读OCSF；窗口检测读flat字段 | 已有基础保存路径；窗口路径可能漏OCSF主机／用户；各入口domain/url/hash提取不一致。仅观察值，未证明库存资产身份或资产标签 |
| 检测置信度 | Fusion计算及TI／漏洞／UEBA等因素→整数0—100、label、rationale，另存anomaly_score | **正常计算结果及依据有落库路径**；未计算／禁用／异常时模型默认0.5、medium、空依据也被写成50分，缺少计算状态，见S1-07。不是分诊评分或独立攻击证据 |
| risk_score、tags和其他富化 | 直接RawAlert可携带；提升／检测未投影这些raw_data字段；risk参与评分；完整FusedAlert进入delivery_snapshot | **没有全部丢失**：live首次快照能保留RawAlert.tags、risk_score、enrichments、priority_score等；但sink没有写普通alerts.tags或把ML优先分写入priority。不可将快照存在当页面已接通，更不能用alert.tags代替资产tags |
| 原始材料 | 直接raw_event按所给字典保存（可为空）；提升／检测保存OCSF及其中raw_data；首次完整FusedAlert另存快照 | 没有对raw_event正文主动裁剪；snapshot超过1MiB拒绝确认交付，HTTP整包上限256KiB。保留的是入口收到的材料，未证明完整厂商原文；OCSF之外整个规范化信封并未整体保存 |

写入依据：[AlertSink的SQL和参数](../../services/fusion/app/services/alert_sink.py)、[初始表默认值](../../services/api/migrations/001_init.sql)、[实体／标签列](../../services/api/migrations/042_alerts_schema_drift_fix.sql)、[首次材料快照](../../services/fusion/app/services/delivery_recovery.py)、[评分](../../services/fusion/app/services/confidence.py)、[Fusion处理](../../services/fusion/app/services/fusion_engine.py)。

## 已定位的问题及功能影响

| 编号 | 可复核的断点 | 页面／调查影响 | 最小处理方向 |
| --- | --- | --- | --- |
| S1-01 | detection_engine.py:335、windowed_detection.py:613构造RawAlert未传event_time；alert_sink.py:84补NOW；first_seen/last_seen另为默认入库时间 | 时间排序、时间线和事件首次活动会偏移；Case材料中的告警时间也偏移，按该时间选调查窗口可能错过真实日志。当前Case查询窗口来自请求，不声称代码自动由告警时间生成 | 两类检测传递有效来源时间；无有效时间明确未知及时间来源，避免把入库时间冒充发生时间；事件首次活动按已定min(member.event_time)。窗口检测还需区分触发时间与覆盖范围 |
| S1-02 | provenance.py:99—105、promoter.py:123—130只提供连接器／产品标签，identity.source又参与指纹 | 原厂可能被显示成接入平台或规则名称；分析人员和模型对来源能力的理解会偏差 | 仅消费已有明确原厂值，未知空；不新增上游字段要求。**不要为了显示原厂改identity.source，避免改变canonical ID** |
| S1-03 | promoter和两类检测默认legacy-v1；alert.py:130—140指纹不含connector、external_id、event_time、source_event_ids；PG存在时worker直接恢复首份结果 | 不同来源记录可能成为同一告警，正文、时间及成员数量只反映首次记录；这会改变统计和调查范围。HTTP source-v1已解决不同稳定上游UUID的独立保存，不能把此问题泛化到所有入口 | 针对输入已有可区分身份却被忽略的情况，修正Fusion内部独立发生／重投区分；保留旧行与首份材料，不能用随机ID或改标题绕去重。输入无稳定身份不在本轮修复范围 |
| S1-04 | promoter.py:390未赋rule_id/name；DetectionHit只有category/mitre，两个builder未赋mitre_tactics | 规则信息停在raw，阶段数量和类别会少算／未分类；tactic参与correlation_key，缺失还可能改变归并分组 | 已有明确规则／战术有值就映射并注明来源；规则本身的战术与输入检测标签应保留各自含义，不能直接把category或技术号推断成战术；下游继续检查独立投影 |
| S1-05 | windowed_detection.py:611—623只用flat src_ip/hostname/host/user，无OCSF device/actor回退，也不取dst_ip；promoter／单事件检测不取domain/url等 | 对象表、共享线索缺项；Case只从affected_hosts及host entities收集主机。若全为空，case_analysis_tools.schemas直接不提供湖查询工具，即使raw里有主机也不会自动补出 | 为明确支持的来源格式统一已知实体提取，保留字段来源／角色；未知不猜；库存资产与标签匹配留第3段，不要求Fusion凭观察名创造资产 |
| S1-06 | alert_sink.py:118追加来源达到200后停止，无完整性标记，且不更新last_seen/updated_at；首次raw及快照冻结；窗口hit不含参与事件清单 | 来源列表不能证明完整覆盖；后到材料不在首份raw中；成员数据变化可能不触发事件最近更新时间；调查逐行来源匹配可能只能覆盖部分事件 | 首份证据保持不变，显式记录追加引用的完整性／溢出与业务更新时间；窗口命中交付有界成员及覆盖范围。不要把全部重复投递刷新为新活动；湖内完整证据在第2段核 |
| S1-07 | FusedAlert默认0.5/medium/[]；engine评分失败仅日志；sink仍写50/medium/[] | 页面和Case难区分“已算得50”与“未算出的默认值”；分数外观可能过度确定 | 保留Fusion评分来源，增加最小计算状态或未知表达；不借triage分数补位，不把分数当独立事实。正常评分及依据的保存路径无需重建 |
| S1-08 | consumer.py:131仅用event_promotion_enabled决定订阅；因lake／detector也可订阅；437无条件调用promote | 当只想归档或检测、关闭提升时，仍可能额外产生提升告警，改变列表数量／事件成员 | 在实际提升分支检查该开关。当前线上开关及是否已发生此现象未核实，不能声称生产正在重复产告警 |

以上按顶部重分类，仅保留Fusion及下游造成的具体实现问题，不新建通用上下文／记忆层。输入不足不转成开发任务；纯显示缺口、内部存储缺口、归并语义及调查可用工具缺口分别处理。

## 验证与尚未证实的范围

- 本轮只执行[一份本地字段观察脚本](../operations/evidence/fusion-field-stage1-20261101/probe.py)，14项观察首次运行均符合当前代码行为。输入显式合成，覆盖提升／两类检测构造、规则标签、时间、实体、来源身份、raw保留、快照冻结、评分参数与去重SQL边界。**这是复现缺口，不是14项需求验收通过。** 未执行检测规则匹配、完整worker、真实PG／Redis／Kafka／湖／模型；没有重新跑已通过业务测试。
- 正向能力复用[2A来源身份历史验收](../operations/2a-source-identity.md)：已有告警HTTP→Fusion→PG曾验证不同来源UUID独立、重投保首份材料及关联。该证据不覆盖本次规范化提升／检测入口，也不证明当前部署全部源码／配置一致。
- 当前仓库未包含`services/ingest/internal/normalizer/normalizer.go`；不把Fusion注释中的旧说明当实际核验。按用户最新边界，上游normalizer、原厂／时间／原文等输入质量不再追查，不列待办或验收阻塞。本段只对Fusion接收到数据后的行为负责。
- 本轮未连接21核实际Fusion配置／源码或新增导出。读取本机SSH配置被文件权限拒绝，未尝试其他身份或更改权限；这不阻碍本地核对，也不将历史配置当作当前事实。需求Git分支只读查询成功。
- r11专用fixture和r13现有Case材料不能证明经当前Fusion完整接入。r13报告问题仍独立保留，未重试，5.3仍未完成。

下一进入第2段：对Fusion已收到的事件和引用，核内部写湖、关联、类别／主机／时间映射、Tool条件及窗口参与事件追溯。输入未提供日志或引用错误只记限制，不追查采集或补采。第3段再核归并关系与资产，第4段核业务写读，第5段核模型实际可见材料；不以本段发现代替后续完成。
