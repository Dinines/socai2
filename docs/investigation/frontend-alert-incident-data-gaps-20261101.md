# 最新告警事件页面与调查实现的数据缺口对照

**后续状态：** 下文保留首次对照时的r11实现/运行基线。2026-11-01再次核实远端功能分析仍为48f54abd；当前调查已到r13，用户要求先保留报告问题、逐项确认字段缺口。最新确认及实施范围以[字段逐项确认记录](field-alignment-confirmations-20261101.md)为准，不把下文建议自动视作用户已确认的产品规则。

2026-11-01。最新页面与当前调查实现的职责一致：事件汇总告警、共同线索和关系，深入判断在 Case 中进行。数据合同尚未完全对齐；主要问题是已有字段在调查投影中遗漏、来源身份字段混用、告警状态缺少联动，以及事件页面所需的对象关系和独立管理数据尚未完整提供。

本次只分析告警页面、事件页面及它们通往 Case 的接口。调查页面布局和功能不在范围内。结论来自源码、字段合同和既有运行材料；没有新增调查、模型请求、业务查询或部署。

## 对照版本

| 对象 | 基线 |
| --- | --- |
| 远端功能分析 | `origin/codex/functional-analysis`，`48f54abd42d643ff53a71fffbb1f6045a90d9f80`，提交于 2026-10-31 19:36:51 +08:00；已 fetch 并用 ls-remote 核实 |
| 最新字段说明 | [事件与告警实际数据对照](https://github.com/Dinines/socai2/blob/48f54abd42d643ff53a71fffbb1f6045a90d9f80/docs/design/incident-alert-data-showcase.md)、[告警数据合同](https://github.com/Dinines/socai2/blob/48f54abd42d643ff53a71fffbb1f6045a90d9f80/docs/design/alert-ui-data-contract.md)、[事件页面最新决定](https://github.com/Dinines/socai2/blob/48f54abd42d643ff53a71fffbb1f6045a90d9f80/docs/design/incident-investigation-page-analysis.md)第 22—26 节 |
| 调查实现 | 工作区 HEAD `b758351d7125590c090a751837f96c86df331652`；应用源码无工作区差异。最近部署依据为 r11 / `a543ad6`，功能修复 `49a04eb`，本次没有重新连接运行服务确认 |
| 运行质量 | [当前 r11 审阅指南](review-guide-20261101.md)与[运行回执](../operations/investigation-r11-positive-fixture-20261101.json) |
| 静态字段提取 | [字段及文件 hash](../../.local/verification/frontend-investigation-alignment-20261101/comparison.json)；远端原文副本保存在同目录的 remote 子目录 |

远端最新总数为 78 告警、21 事件、21 Case、18 Run，是页面已加载集合。新增 3 事件、11 告警、2 Case、3 Run 属于明确演示；原 13 个实际 Run 是历史留存。其真实处理样本主要来自 10 月 25 日及更早，不能代表当前 r11 的线上库存或交付质量。

## 已经对齐的能力

| 页面要求 | 当前实现与可复用能力 |
| --- | --- |
| 按真实事件身份聚合成员 | [incident_reader.py](../../services/api/app/investigation_v2/incident_reader.py:111)按同租户 `enrichment_data.socai2_fusion.incident_id` 读取 canonical Alert；没有按相同场景名或主机猜成员 |
| 事件继续汇总，判断进入 Case | 事件 GET 和 AI 概况与 Case 调查分离；概况只归纳已有材料。没有必要另建一套事件调查循环 |
| 创建或关联 Case，不顺带启动调查 | [case_links.py](../../services/api/app/investigation_v2/case_links.py:86)已有创建、成员并集追加及回执；显式调查另走 v2 investigate。前端目前本地操作尚未接这些接口，不能据页面 Pending 认定后端已启动 |
| Case 关系与某次调查覆盖范围分开 | [related_investigations.py](../../services/api/app/investigation_v2/related_investigations.py:11)分别返回当前 Case 成员交集、Run 选定/实际读取成员及完整性；旧 Run 范围不会因当前成员改变而重写 |
| 新旧运行材料可发现 | [execution_index.py](../../services/api/app/investigation_v2/execution_index.py:58)提供统一执行索引，旧记录沿原账本读取。`investigations.items`只列新版 Case Run，不能将它当全部历史；旧记录入口已经存在 |
| 查询失败、成功零条、历史复用分别显示 | 已有 query_status、returned_count、source_alignment、固定租户/主机/窗口和逐行来源 ID 匹配；这些事实不用再造一套框架 |
| 来源原文与模型可见范围分开 | 已冻结 description/raw，记录原字节、hash、截断和模型省略原因。r11 两条短 raw 实际完整进入全部四次模型请求 |

## 会影响调查或跨页一致性的缺口

| 编号 | 页面字段或功能 | 当前实现及证据 | 影响与处理方向 |
| --- | --- | --- | --- |
| G01 | 检测源、来源告警 ID | [告警调查上下文](../../services/api/app/investigation_v2/alert_context_api.py:33)和[事件成员](../../services/api/app/investigation_v2/incident_reader.py:133)把 `external_id`输出为 `source_alert_id`。Fusion 同时独立保存 `identity.source_alert_id`、`identity.source`及 `external_id`，见[写入映射](../../services/fusion/app/services/alert_sink.py:247)。远端合同中已有 `external_id=NULL`而 Fusion 来源 ID 非空的实例 | **字段语义偏差。** 页面 v1 详情可读到 fusion_identity，而调查上下文却可能显示来源 ID 缺失；二者不能互为别名。应分别保留 canonical ID、Fusion 来源告警 ID、external_id、source_event_ids、来源标识及 connector ID。产品 Tool 中同名 `source_alert_id`目前实际要求 canonical ID，也应在对接中明确其含义 |
| G02 | ATT&CK 分类、规则、检测置信度及分诊依据 | [case_context](../../services/api/app/investigation_v2/case_analysis.py:247)显式告警投影没有 category、mitre_tactics/techniques、rule_id/name、confidence/label/rationale、ai_score、connector_type、fusion_identity、fusion_ioc_lookup、ai_recommendations；T 仅带 verdict/rationale/auto_closed，未带 findings/proposed_actions。主表已有相关列，见[Alert 模型](../../services/api/app/models/alert.py:33) | **已有数据未进入调查投影。** 页面能显示的检测分类和依据，模型未必能看到，可能转而依赖标题或旧摘要。raw/description可能恰好重复这些值，故不能断言每次请求都完全缺失。宜补功能所需的分类、规则、来源及置信度来源说明；分诊结论、IOC判断仍是已有分析，不能提升为独立观测证据。负责人等展示字段无须全部塞入模型 |
| G03 | 发起调查后，告警进入进行中 | [v2 start_analysis](../../services/api/app/investigation_v2/case_analysis.py:639)创建 Run 并执行分析，没有更新 Alert.status；[v2 路由](../../services/api/app/investigation_v2/case_analysis_api.py:37)也没有该联动。旧 [v1 Case 启动](../../services/api/app/api/v1/endpoints/cases.py:1678)有向 investigating 推进的逻辑 | **已确认业务语义尚未接入新版路径。** Run 可以存在而告警仍为 new/triaged。应对本次选定且符合推进条件的成员处理，保留 closed/resolved 等终态；不能顺带把事件判为处理中或已解决。具体失败时机按实际启动结果处理，不把提交按钮点击等同受理 |
| G04 | 告警及事件的所属 Case | [v2 关联](../../services/api/app/investigation_v2/case_links.py:138)写 `Case.alert_ids`和关联回执，不写 `Alert.case_id`；事件成员仍返回 `Alert.case_id`，v1 告警响应也用单值 case_id。与此同时 read_related 已正确按 Case.alert_ids 反查 | **关系读取合同不统一。** 新版上下文的 cases 可以非空，而基础告警/成员 case_id 仍为空。页面应以同一当前成员关系返回 Case 列表与覆盖数；单值 case_id不能表达多 Case。关联回执表示历史操作，不能单独当当前归属。已有部分覆盖不应在打开页面时自动补齐 |
| G05 | 缺少发生时间时保留未知 | 远端合同记录实际 PG `event_time`可 NULL；[初始 DDL](../../services/api/migrations/001_init.sql:110)也未设 NOT NULL，而 [IncidentMember](../../services/api/app/investigation_v2/incident_reader.py:33)与 v1 响应使用非空 datetime。Case 输入允许原值进入字典，但不会补来源时间依据 | **空值合同不一致。** 若实际存在空时间成员，事件 DTO 可能验证失败；这是静态条件结论，本次未触发线上反例。应允许未知并区分上游时间、Fusion 缺省生成时间和入库时间；不能用 created_at 冒充原始发生时间 |

G04 另有一个页面接入细节：最新 UI 默认把事件全部当前成员带入新 Case，但后端允许显式 subset，并返回 `selection_kind`。这保留了已有选择成员能力；前端须提交实际选择并依据返回覆盖数说明结果，不能把任意 201 当成全部成员已关联。v2 当前也不禁止有 Case 后再创建另一个 Case，页面的“已有 Case 时禁用新建”目前仅由页面限制。

## 事件页面所需的数据还不完整

| 编号 | 最新事件页面需要什么 | 当前实现的缺口 | 建议复用及边界 |
| --- | --- | --- | --- |
| G06 | 事件是什么、发生范围、逐成员时间线 | [IncidentOverview](../../services/api/app/investigation_v2/incident_reader.py:44)标题固定为首条告警标题加 Incident；成员没有来源 description，只有 saved_analysis/recommendations/triage。[summary_material](../../services/api/app/investigation_v2/incident_summary.py:55)也未提供成员来源描述和逐条 event_time，主要依靠标题与已有分析归纳 | **当前概况来源偏重既有判断。** 不适合直接冒充页面的客观事件说明。可按当前成员描述、发生时间和已保存对象生成确定性汇总，另保留有生成时间/来源/过期标记的 ai_overview；两者语义分开。不要为页面另开联合调查 |
| G07 | 为什么关联、共同对象、仅此事件关系图、阶段计数 | 当前 `_entities`把全部成员对象合成去重的 type/value 列表；IncidentMember不含逐告警实体。ATT&CK也只有并集。未返回 alert→object 边、每对象成员集合、稳定对象身份或每阶段告警数；亦未返回具体归并规则及决策依据 | **汇总投影不足。** 不能从全局实体并集恢复哪些告警共享某对象，不能把阶段并集当覆盖计数。应保留逐成员关联及来源；有明确对象 ID 就沿用，没有则保留身份未知，不能把同名对象自动合并成同一库存对象。共同线索可以据已有记录投影，归并规则未保存就继续标未知；无需恢复事件 Attack Chain/Path |
| G08 | 事件处理状态、负责人、最近管理更新、人工解决、处理活动及队列指标 | 当前 handling_status只有默认 None；没有独立 owner/priority/解决说明/事件管理 updated_at。source_updated_at是成员/分诊或关联 Run 的最大更新时间。事件路由目前提供单事件 GET、相关调查和概况 refresh，没有对应事件队列/管理写入及活动聚合合同 | **前端本地生命周期尚无完整后端承接。** 最新“默认新建、分配后处理中、人工解决并同步关闭关联告警”只是页面规则。应保存独立事件管理状态及实际受影响成员、原因和活动；source_updated_at不能当事件管理更新时间。处理中的事件按事件状态计数，24h新告警按成员发生时间去重，不能拿 running Run 数替代。原审计/时间线表可复用，无须把模型步骤当人工操作 |
| G09 | 成员表和告警列表的检测源、负责人、涉及资产与资产标签 | 事件成员没有 source 名称、assignee、逐告警对象和资产标签。v1 AlertResponse也缺负责人输出与独立检测源字段；v1详情有 fusion_identity/related_entities。[processing_context](../../services/api/app/services/processing_context.py:18)已有资产/身份/历史读取，但资产查询未取 tags，Case 模型也未消费它 | **读取合同与关联数据仍需组装。** 优先复用已存在的详情、资产与用户目录读取，并明确未匹配/未分配/未解析。affected_hosts或实体值只能表示观察到的对象，不能伪造 assets.id、OS、资产角色和标签。历史样本没有库存关联属于源数据缺口，不能归因为调查投影丢失 |

G08 的严重程度目前取成员最大等级，发生范围取成员 first_seen/last_seen。这些都是可用的派生汇总，但应保留其口径：不等于独立事件优先级，也不能与页面按成员 event_time计算的发生范围混用。事件列表、管理及活动仍需产品后端承接；这些不是本轮 r11 新引入的报告回归。

## 能力边界与容易误读的字段

| 项目 | 当前实际范围 | 对页面和调查的含义 |
| --- | --- | --- |
| 检测置信度与 AiSOC 评分 | `confidence`为 0—100 的检测/融合置信度；`ai_score`为 0—1 的分诊判定置信度，页面乘 100。远端明确正常行为也可为 96 分 | 评分高不能直接解释为威胁大，不能与 confidence替换，也不能以最大/均值生成事件风险分。G02登记的是来源字段未投影，不是要求模型把评分当事实 |
| 来源字段的冻结和可见范围 | [case_source_material](../../services/api/app/investigation_v2/case_source_material.py:38)保存每告警 description至多 4096B、raw至多 16384B，Run合计 131072B；模型来源材料总预算 8192B，每条 raw上限 2048B并受成员分摊和输入安全规则约束 | 有界输入本身不是遗漏标记缺失。长 raw和多成员下重要细节可能不在模型视图；同一 raw在页面可见不能证明模型已看到。若需要超出片段的字段，应有针对性读取，而非取消全部限制。r11短 raw完整只证明当次两条样本 |
| 补查覆盖 | [CaseTools](../../services/api/app/investigation_v2/case_analysis_tools.py:19)只有主机固定窗口的 1007 进程活动、4001 网络连接；[产品 Tool](../../services/api/app/investigation_v2/case_product_tools.py:16)为来源绑定的 CrowdStrike 当前主机详情 | 没有历史父链/PID/命令全文补查，也未提供邮箱、OAuth、云、AI代理等同等取证工具；无主机的对象通常不能使用湖工具。这是场景覆盖边界，不能因为演示出现八类对象就认定已支持八类调查，也不自动扩成全部工具实施任务 |
| 告警→事件关系 | 当前按已保存 Fusion incident_id读取，直写/旧记录可能没有该路径 | 无事件 ID的告警当前不会自动变成事件成员；用户“每条告警属于一个事件”的完整性要求仍需输入路径保证。不能按同主机/时间补造成员 |
| Explain 与已有调查 | 告警详情已有独立 Explain协议和 fallback标记；事件/Case已有分析摘要另有来源 | 未把 Explain全量送入 Case本身不是必须修复的字段缺口。Explain、分诊和历史报告均属分析，不是互相独立的新证据；无建议和无独立“待核实事项”字段也不需要补默认内容 |
| 相关告警与反馈 | processing_context历史为前 7 天、主机/账号/IP候选，最多 20 条，缺 event_time时会用 created_at；远端相关告警要求同主机最近 7 条，反馈复核候选另有语义 | 现有 helper不能直接冒充这两个页面合同。可复用查询基础，保留时间来源；人工判定、关闭、原模型判断和操作记录应分别显示。此项属于产品告警功能对接，不要求将全部历史作为 Case输入 |
| 运行入口与结果质量 | executions能发现旧 Run，但旧类型/完整度部分保持未知；r11最终仍 failed/partial | 旧材料未采集完整正文、字段为 NULL、缺关联、投影未取、语义错误需分开说明。页面样例展示“完整报告”不改变 r11真实质量状态 |

r11仍有不确定协议句式误拒、纠错指令泄入正文、混淆 Case描述与告警原文、无源推断及关系判断不稳定的问题，见[现有问题登记](review-guide-20261101.md)。补字段可以改善输入，但没有证据表明它足以解决这些内容问题，不能仅放宽校验便称调查功能验收完成。

## 建议处理顺序

1. **先修会形成错误解释的接缝。** 明确 G01 来源身份；补 G02 中调查真正需要的检测/分类/来源字段；统一 G03 启动与告警状态、G04 当前 Case关系、G05空时间合同。保留已有预算、范围和历史材料。
2. **再补事件页面读取。** 为 G06—G07提供逐成员来源说明、时间、对象关联、阶段计数和依据来源，复用现有事件成员及告警详情；不添加事件深度调查。
3. **承接已确认管理功能。** G08—G09补事件生命周期、负责人、资产关联/标签、队列统计与处理活动；前端本地状态不能作为正式后台状态。
4. **按真实场景决定额外补查。** 只有业务需要时才补当前进程/网络范围以外的读取；演示数据不增加验收承诺。r11报告具体问题继续独立保留。

本轮只新增对照报告和本地静态字段/hash记录；没有修改业务源码或原证据，没有重跑已有业务测试、创建数据、启动 Run、执行模型/Tool、部署、推送或合并。
