# 告警、事件页面字段逐项对照

2026-11-02。本文回答“页面要什么字段，当前保存在哪里，哪个出口能读取，具体还差什么”。范围从 Fusion 收到数据之后开始；前置输入缺失／错误不列修复任务。页面功能由后端实现，本表不把尚未实现搜索、导出、级联等功能等同于缺字段。

## 对照版本与判定口径

- 需求固定为本地可读取的远端提交 `48f54abd42d643ff53a71fffbb1f6045a90d9f80`：`docs/design/alert-ui-data-contract.md` 的 L01—L14、4.1—4.4；`docs/design/incident-investigation-page-analysis.md` 的 17.2—17.3、22—26；`docs/design/incident-alert-data-showcase.md` 的字段表。本轮没有联网刷新远端分支。
- 后续用户明确的 [16 项决定](field-alignment-confirmations-20261101.md)覆盖上述版本中的旧待定项。调查页面本身不比较；Case／Tool 是否消费已有字段仍比较。
- 实现为本地 `b400fd05cef29075bcf2c1e73cab4bae0c6d3995` 加第 1—4 批未提交修改，不能把 HEAD 当成已经包含全部修复。本轮只核源码／迁移和既有证据，没有读取线上实际记录。
- **“字段已通”**：存在保存位置及明确读取出口；不是“线上每条都有值”。**“可派生”**：原子字段和关系具备，无须为显示另建冗余字段。**“读取缺口”**：已有保存值，指定消费出口未取。**“存储缺口”**：当前对象缺权威持久化位置。**“关联缺口”**：记录存在，但不能准确归到指定对象／范围。**“写回不一致”**：有字段，现有写入与已确认语义不一致。**“输入／历史限制”**：缺的值本来未收到或以前未保存，不造值、不列补采任务。

表内缩写：`A=alerts`；`F=A.enrichment_data.socai2_fusion`；`R=investigation_runs`；`E=investigation_events`；`K=investigation_artifacts`。模型实际表名见文末代码索引；这些缩写不是新增表。

## 1. 告警列表九列及侧栏

| 编号／页面字段 | 已确认含义 | 当前保存位置 | 当前读取出口 | 明确结论 |
| --- | --- | --- | --- | --- |
| A01 告警名称 | 原告警标题；点击使用平台告警 ID | `A.title`、`A.id` | v1 列表／详情 `title/id`；事件 `members[].title/alert_id` [C1/C3] | 字段已通。不能用标题充当唯一身份 |
| A02 严重程度 | critical/high 归高，medium 中，low/info 低 | `A.severity` | v1 `severity`；事件成员 `severity` [C1/C3] | 字段已通；三档显示可派生，不缺评分表 |
| A03 告警时间 | `event_time`；入库时间不是发生时间 | `A.event_time`；`F.event_time_source/event_time_fallback` | v1 `event_time` 和 `detection`；成员 `event_time` [C1/C2/C3] | 新写入已保留收到的时间及回退标记。历史被 NOW 代替的真发生时间不可恢复；迁移允许 NULL 而响应要求 datetime，历史 NULL 兼容仍有合同差异，不宣称旧记录已清理 |
| A04 资产标签 | 库存资产标签，不是告警标签 | `assets.tags`，同租户 `alert_asset_correlations`；当前 name/FQDN/IP 匹配 | 告警 `processing-context` 的资产结果；事件须 `include_assets=true` [C4] | 字段已通，但不内嵌在 v1 告警列表。列表接入需要使用／汇集现有资产出口。无库存匹配则没有可展示资产标签 |
| A05 处理状态 | 告警业务状态；旧 fp/false_positive 显示完成且保留误报标记 | `A.status`，判定另存 `A.disposition` | v1／事件成员分别返回 `status/disposition` [C1/C3] | 数据可支撑分组。现 `alert_status` 只把 resolved/closed 算已解决，旧 fp 分组未对齐；这是映射差异，不是缺列 [C5] |
| A06 类别 | 检测的 ATT&CK 战术标签 | `A.mitre_tactics` | v1 同名字段及 `detection.mitre_tactics`；事件成员同名字段 [C2/C3] | 字段已通；不使用 `A.category` 或技术编号替代战术 |
| A07 检测源 | 原始厂商；未知留空 | `A.raw_event.original_vendor/deviceVendor` 或已保存 `raw_data` 中同名明确字段 | 共享 `source.detection_source`，附 `detection_source_path` [C2] | 上述明确字段已通；当前读取器仅支持这两类明确键。不用 connector、identity.source、metadata.product 猜原厂；其他格式没有确认映射，不能宣称已覆盖任意厂商格式 |
| A08 资产／账户 | 上报主机、账户等对象；库存身份另列 | `A.affected_hosts/users/ips`、`A.entities/iocs`；库存 `assets.id/name` | `objects[]`；库存由 `processing-context` 提供 [C2/C4] | 已存对象与库存读取均有出口。上报主机不是库存 ID，账户／IP 不冒充库存资产 |
| A09 分配给 | 处理负责人，非受影响账户 | `A.assigned_to_id/assigned_at`；同租户 `users.id/username` | v1／事件成员 `assigned_to_id/assigned_at/assigned_to_name` [C1/C2/C3] | 字段已通；ID 有值但用户名称未匹配时仍保留 ID，不写“未分配” |
| A10 侧栏描述 | 源告警说明 | `A.description` | v1 `description` [C1] | 字段已通；不拿 ai_summary、narrative 或 Explain 替代 |
| A11 所属事件 | Fusion Incident，不是 Case | `F.incident_id` | v1 详情 `fusion_incident_id`；事件按该键查询成员 [C1/C3] | 已有归属可读。旧记录／非 Fusion 入口没有此键时不能编造事件归属；“所有入口都必有事件”当前不成立 |
| A12 已关联 Case | 当前真实 Case 成员关系，允许多个 | `aisoc_cases.alert_ids` | v1 `case_links_url`；v2 `case-links`／`investigations.cases`；事件需 `include_investigations=true` [C6] | 当前多 Case 关系已读通，最多 50 条并标截断。v1 `case_id` 和 rail Case 芯片仍是旧单值，不能作为完整当前关系 |

## 2. 告警详情、原始材料与分析字段

| 编号／字段 | 页面要求／数据含义 | 当前保存位置 | 当前读取出口 | 明确结论 |
| --- | --- | --- | --- | --- |
| A13 平台告警 ID | 页面跳转、成员关系、Tool 绑定的内部身份 | `A.id`，同租户使用 | v1 `id`；事件 `members[].alert_id` [C1/C3] | 字段已通；不改为厂商／来源编号 |
| A14 源记录 ID | 接入链路保存的来源告警编号 | `F.identity.source_alert_id` | `source.source_alert_id`；事件成员 `source_alert_id` [C2/C3] | 第 4 批已改掉使用 external_id 顶替的读取；为空就留空 |
| A15 外部告警编号 | 与源记录 ID 分开的外部编号 | `A.external_id` | 详情 `external_id`、共享 `source.external_id` [C1/C2] | 字段已通，不与 A13/A14 合并 |
| A16 原始事件引用 | 告警指向的湖事件编号及完整性 | `A.source_event_ids`；`F.source_event_ids_truncated/field_metadata` | 详情 `source_event_ids/detection`；Case 冻结材料 [C1/C2/C7] | 第 1、3 批统一 ID 并补窗口引用及省略信息。上限保留，截断集合不是全部参与事件证明 |
| A17 检测规则 ID、名称 | 已有规则身份，非补查规则全文 | `A.rule_id/rule_name` | `detection.rule_id/rule_name`；Case A.detection [C2/C7] | 字段已通；原始规则缺失不按标题补造 |
| A18 ATT&CK 技术 | 与战术分开的来源标签 | `A.mitre_techniques` | v1／共享 detection／事件成员／Case [C1/C2/C3/C7] | 字段已通；字典可解释名称，不能由战术推导技术事实 |
| A19 Fusion 置信度分数 | Fusion 检测／融合分数，0—100 | `A.confidence`、`F.confidence_status` | `detection.confidence.score/status/source`，v1 平铺 confidence 同步遵守状态 [C2] | 已通；unknown/disabled/failed 不展示残留分数。旧分数标 legacy_unverified，不冒充新计算 |
| A20 Fusion 置信度等级、依据 | 与 A19 同来源 | `A.confidence_label/confidence_rationale` | `detection.confidence.label/rationale`，v1 平铺字段 [C2] | 字段已通，不将依据当独立观测 |
| A21 页面分诊评分 | 分诊 confidence，0—1 可换算 0—100；不是独立风险分 | `A.ai_score`；原始值在同次 `E(kind=triage_verdict).payload.confidence` | v1 `ai_score`；v2 `triage.confidence`、Case T [C1/C2/C3/C7] | 字段已通。要解释该分数的判定必须用同次 E；不能与当前人工 disposition 拼成一次分诊 |
| A22 当次分诊判定、理由、时间 | 同一次分析判断 | 同一 E 的 `payload.verdict/rationale/auto_closed/confidence`、`ts/run_id/id` | v2 triage／Case T [C2/C3/C7] | 字段已通，来源 ID 和时间可追溯；没有分诊事件则不虚构当次结果 |
| A23 当前判定 | 当前业务判定，不覆盖历史分诊 | `A.disposition` | v1／事件成员 `disposition` [C1/C3] | 字段已通；反馈与关闭的写回一致性见 D05 |
| A24 Explain 正文 | 请求 Explain 返回的解释，非旧摘要替身 | 现有 Explain 服务按请求返回 `summary` | `POST /api/v1/alerts/{id}/explain` [C8] | 返回合同已有；不要求预生成新表。本轮未调用生成、未验证实际返回内容质量 |
| A25 Explain 生成时间／方式 | 同次解释生成时间、是否用模型 | 同次响应 `generated_at/llm_used/llm_reason` | 同 A24 [C8] | 字段合同已有；不取 event_time/updated_at/分诊时间代替 |
| A26 Explain 关键依据 | 本次解释提取到的依据摘要 | 同次响应 `contributing_events[].label/value/annotation` | 同 A24 [C8] | 字段合同已有，最多 5 项；不是完整原文／完整取证链，不保证解析任意 full_log |
| A27 Explain 建议动作 | 与正文一并显示；空建议留空 | 同次响应 `suggested_actions` | 同 A24 [C8] | 字段合同已有；不是已批准或已执行动作 |
| A28 原始数据 | 保存的来源材料及截断说明 | PG `A.raw_event`；湖 `raw_payload/ocsf_json` | 详情 `raw_event`；Case 来源工件 [C1/C7/C9] | PG 详情原文已读通；湖第 3 批改为合法 JSON／超限包装。旧已裁坏材料未恢复；Case 模型可见性另见 T02 |
| A29 IOC 候选 | 记录中的 IP／域名／文件哈希等 | `A.iocs/entities/affected_ips` | v1 `iocs/objects`、事件对象、Case [C2/C3/C7] | ORM 原来漏映射 iocs，现已补；候选不是恶意结论 |
| A30 IOC 查询结果 | 租户库查询范围、时间、命中／失败状态 | `F.ioc_lookup` 的 indicators/matches/status/checked_at/scope/external_status | 详情 `fusion_ioc_lookup` [C1] | 已有保存值可读；no_match 不代表安全，not_configured 不代表已查外部情报 |
| A31 租户 | 真实隔离范围和租户显示名 | `A.tenant_id → tenants.id/name` | v1 暴露 tenant_id；同租户名称可联表读取 [C1] | ID 已通，名称可派生；不固定样例组织名 |
| A32 反馈判定和核查理由 | 明确告警、操作者、原判／改判、理由 | `aisoc_analyst_feedback` 的 alert_id/analyst_id/ai_disposition/analyst_disposition/reason_code/note/context/created_at | feedback 现有接口与服务 [C10] | 存储已具备，不能笼统说“没有反馈理由字段”；普通评论与按告警历史读取仍需区分，见 D03/D04 |
| A33 响应建议 | 原分析提出的动作及目标，不代表已建审批单 | `A.ai_recommendations`、T/G 的 proposed_actions | v1 `ai_recommendations/recommended_actions`、已保存分析工件 [C1/C7/C11] | 建议可读；通用建议条目没有强制 approval_id/action_id 关联，审批闭环不能按文本猜，见 D08 |
| A34 审批状态 | 已存在审批单的实际状态、决策人／时间／理由 | `agent_approvals.id/alert_id/case_id/run_id/status/decided_by_id/decided_at/decision_comment/action` | approvals 列表／详情 [C12] | 字段和读取存在。并非每条建议都有审批单；没有记录不能默认“待审核” |
| A35 执行结果 | 与真实动作绑定的结果和错误 | `aisoc_action_records.id/record` 内 status/output/error；审批 `action.dispatch.action_id/action_status` | actions 按 ID 读取；审批详情带 dispatch [C12/C13] | **审批入口复用 approval.id 作为 action.id，连接键已存在。** dispatch.state=executed 仍须结合 action_status/output，不能等同执行成功；actions.record.incident_id 在该入口写的是 Run ID 或审批 ID，不能当 Fusion Incident 键 |
| A36 Run、步骤、Tool、报告 | 真实运行状态／范围／工件，完成度另列 | R/E/K；当前 profile 与冻结成员范围 | 执行索引／Case Run 及工件读取 [C7/C14] | 已有字段可支撑保存记录展示。预览不等于完整输入输出；有工件索引不等于正文可读；completed 不等于完整报告通过 |
| A37 调用次数／token／成本 | 各自真实计量，不能以迭代数代替 | `aisoc_run_costs`、R 的 total_tokens、E 的 usage | 既有运行／用量读取 [C14] | 已有计量来源；缺价格的调用不记零成本，不重复累加多个聚合 |

## 3. 事件列表、详情与关系字段

事件默认七列是 I02、I04、I05、I06、I07、I08、I09。成员表复用 A01/A02/A05/A07/A08/A09；成员发生时间保留自己的 `event_time`，不是把每一行改成事件最早时间。

| 编号／字段 | 页面要求／数据含义 | 当前保存位置 | 当前读取出口 | 明确结论 |
| --- | --- | --- | --- | --- |
| I01 事件 ID／成员集合 | 同租户 Fusion Incident 及其 canonical 告警成员 | `F.incident_id`，各成员 `A.id/tenant_id` | `read_incident` 按租户＋incident_id 查 PG [C3] | 归属已持久化可读，不依赖 Redis 窗口存活；旧无归属行不能补造 |
| I02 事件名称 | 事件显示名／人工改名后的名称 | 当前只有成员 `A.title` | 当前 `title = "Incident: " + 首条成员.title` [C3] | 默认名称可派生；**独立事件标题／人工改名持久化缺失**，不能说已支持保存改名 |
| I03 事件说明 | 事件层说明；AI 概况注明生成来源 | 当前成员 description、保存的 `fusion_incident_summaries.summary_text` 等 | `ai_overview/ai_overview_metadata`；成员材料可追溯 [C3/C15] | 已保存 AI 概况可读；**独立人工事件说明缺持久化位置**。AI 概况缓存不是事件业务主记录 |
| I04 严重程度 | 当前成员最高等级作为聚合值 | 各成员 `A.severity` | `read_incident.severity` 按等级顺序取最大 [C3] | 聚合字段已通；独立人工覆盖值未保存，不把成员最大值称人工设定 |
| I05 处理状态 | 独立的新建／处理中／已解决状态 | 当前无 Fusion Incident 业务状态记录 | `handling_status` 默认 None [C3/C15] | **存储缺口**。不能由 Case.status、Run.status 或所有成员关闭推定 |
| I06 事件负责人 | 事件级负责人及分配时间 | 只有各告警 assigned_to_id/assigned_at；无事件级位置 | 成员负责人可读，overview 无独立负责人 [C3] | **存储缺口**。成员一致也不能证明事件已经分配；用户要求同步覆盖时仍要保存事件自身值 |
| I07 涉及资产 | 远端 22.10／24 的主机数与主机名称；不是对象总数 | 成员 `affected_hosts` 及 typed objects；库存另见 A04/A08 | `members[].objects`、事件 entities/object_links [C2/C3] | 主机集合去重可派生；不把 user/ip/domain 加入主机数。库存资产数须另按真实资产 ID 去重，不能偷换现页面口径 |
| I08 活跃／全部告警 | 完整成员数及未完成成员数 | 成员 `A.id/status` | member_count、by_status、members [C3] | 总数已返回，活跃数可按已确认完成分组派生；旧 fp 映射差异沿 A05。不需新增计数表 |
| I09 最近更新时间 | 事件自身和成员变化；Run 进度不计 | 当前仅 `A.updated_at`；没有事件自身业务时钟 | `updated_at=max(member.updated_at)`；source_updated_at 另含分析材料时间 [C3/C6] | **成员部分已通；事件自身部分存储缺口**。成员移出／清空时也不能只依赖剩余成员最大值；须有事件业务更新时间 |
| I10 首次活动 | 当前成员告警发生时间的最小值 | 成员 `A.event_time` | `first_seen=min(member.event_time)` [C3] | 第 4 批已对齐用户第 8 项。旧缺时间／被回退的事实沿 A03，不以 created_at 修补 |
| I11 最近活动／发生范围终点 | 区分成员最后发生时间与单告警累计活动末尾 | `A.event_time` 与 `A.last_seen` 均存在 | 当前 `last_seen=max(member.last_seen)` [C3] | **当前返回值不是 max(member.event_time)**。若页面范围表示成员告警发生时间范围，终点应从 event_time 派生；若展示累计活动末尾用 last_seen。两字段不能同名互代；不新增时间列 |
| I12 分类 | 事件人工分类，非 ATT&CK 战术 | 当前无事件级分类位置 | 无相应业务读回 [C3/C15] | **存储缺口**；不由 category／disposition／战术标签填充 |
| I13 优先级 | 事件人工优先级 | 当前无事件级位置；Alert.priority 与 Case.priority 属其他对象 | overview 无独立优先级 [C3] | **存储缺口**；不把分诊 confidence 换成事件优先级 |
| I14 优先级评分／因素 | 页面保留的评分及依据；未评分为空 | 无对应事件评分／因素记录 | 无对应事件字段 [C3] | **已评分数据不能支撑；空态可支撑**。不要求本轮新增评分算法；后端实现评分后须保存分数、来源及因素，不能用 ai_score 顶替 |
| I15 事件标签 | 事件自身标签 | 当前仅告警 tags、资产 tags；无事件级位置 | overview 无事件标签 [C3/C15] | **存储缺口**；两类已有 tags 都不是事件 tags |
| I16 解决说明、解决人、解决时间 | 事件的解决事实，说明必填 | 当前无事件级位置 | 无事件业务读回 [C3/C15] | **存储缺口**；成员 resolved_at、Case 关闭或 Run 结束不能代替 |
| I17 ATT&CK 阶段数量 | 每成员在每个自带战术计 1 次，同战术去重 | 成员 `A.mitre_tactics` | `tactic_counts/tactic_count_notice` [C3] | 已返回；总和可超过成员数，提示已在返回合同中；不是攻击阶段事实认定 |
| I18 检测技术并集 | 成员已有技术标签集合 | 成员 `A.mitre_techniques` | overview／成员 mitre_techniques [C3] | 字段已通，不自动补战术或技术 |
| I19 实际归并依据 | Fusion 当次的归并决定及范围 | `F.correlation_basis` 和首份 delivery_snapshot | `members[].correlation_basis` [C3/C16] | 第 2 批已持久化／读回：policy_version、entity_type/value、tactic、key、window、decision/reason/decided_at。旧未记录依据保持空 |
| I20 共同线索 | 当前成员共同报告的同类型对象 | 逐成员 objects | `members[].objects/object_links` [C3] | 按 type/value 计算共享成员数可派生；不把“共同线索”写成当时归并原因 |
| I21 告警—对象关系图 | 哪条告警报告哪个对象 | canonical Alert ID＋typed objects | `object_links[].source_alert_id/type/value` [C3] | 关系已读通。这里的 source_alert_id 是平台告警 ID，与 A14 同名不同含义，消费方必须按此合同绑定，不能传给源记录查询 |
| I22 库存信息／匹配依据 | 当前库存标签、关键性、匹配来源 | assets、alert_asset_correlations | include_assets 的成员 assets，带 lookup_matches／correlations／状态 [C4] | 字段已通但有界：事件先读 20 成员，每成员最多 20 资产，asset_coverage 标省略；不能把该子集当完整库存总数。当前库存不是历史告警时点库存 |
| I23 关联调查／Case | 当前成员真实参与的 Case 和固定 Run 范围 | `aisoc_cases.alert_ids`；Run profile／冻结 selected_member_ids | include_investigations、case_ids、executions 索引 [C6/C14] | 已读通且有截断／权限边界；不能把旧 Alert.case_id 或重载 Run.case_id 当唯一关系 |
| I24 处理活动 | 属于本事件及被变更成员的实际操作 | 只有通用 audit_log、告警与 Case／Run 各自记录 | 无完整 Fusion Incident 业务活动集合；告警 rail 仍串入旧 Case 全部活动 [C11] | **事件活动存储／关联合同缺口**。复用通用审计设施即可，不需要新通用审计框架；必须准确记录事件键和涉及成员 |

## 4. 支撑页面操作的数据条件（不开发页面功能）

| 编号／页面使用 | 已有数据 | 对照结论／后端须遵守的字段合同 |
| --- | --- | --- |
| D01 告警统计、过滤、排序、导出 | A01—A09 的原子字段及租户；标题、时间、ID 可稳定排序；资产标签有单独关系出口 | 数据基础具备；列表具体条件和导出接口未对齐不称缺表。总体卡片不随下方筛选；有选导出所选，无选导出当前结果前 min(total,200)。原厂筛选须使用 A07 的已确认投影，不用 connector 代替 |
| D02 调查进行中统计／事件关联调查卡 | 当前 Case 成员关系、Run profile/status、固定选中成员；旧 Run 的真实阶段 E | 可按明确范围派生并按 Alert／Incident 去重，不需要给每个统计另建字段；旧自动分诊 Run 不自动算调查。仅看 A.status 无法得到准确调查卡 |
| D03 普通告警评论 | `aisoc_analyst_feedback.note` 是改判理由；CaseTimeline 是 Case 评论；audit_log 能保存通用动作 | **普通 Alert 评论合同缺口**：需稳定 comment_id、tenant_id、alert_id、author_id、body、created_at 与对应读回。不能要求每次评论都改判／挂 Case；已有通用存储可承接，不预先强制新表 |
| D04 告警完整时间线 | event_time、created_at、assigned_at、resolved_at；分诊 E、Run 时间；audit_log | 基础时间已有，**完整性和对象关联未通**：rail 上限 6；按 legacy case_id 取整 Case Timeline，无法证明每条都属于此告警；批量动作需保存 target_alert_ids 或逐告警审计，不能只保存数量 |
| D05 反馈 fp／authorized 同步关闭 | A.status/disposition/resolved_at/updated_at、反馈原件及选中 IDs | **写回不一致，不缺列**：现反馈只更新 disposition/updated_at，却记 resolved SLA；相似告警重判也不能仅改 disposition。后端按已确认规则写关闭字段、保留当次反馈与实际目标；不能以 SLA 事件证明状态已关闭 [C10] |
| D06 手动关闭／重开告警 | A.status/resolved_at；审计；评论另见 D03 | 字段足够；普通关闭说明选填。现 update 路径重开不清 resolved_at，字段组合不一致须交后端处理，不能用旧 resolved_at 推定当前已完成 [C1] |
| D07 事件改派／解决及保存前覆盖提示 | I01 完整成员 ID 集合、A09 原负责人、A05 原状态、A23 各自判定 | **影响范围可派生；事件本体字段缺口见 I05/I06/I16，活动缺口见 I24**。改派保存事件及全部成员负责人；解决保存事件及全部成员关闭字段但不覆盖 disposition。提示要基于实际成员范围，而非浏览器已加载的一页；本轮不实现级联动作 |
| D08 建议→审批→执行 | A33 建议、A34 审批、A35 动作记录；审批 ID 与动作 ID 明确相同 | **审批→执行连接键已具备**；通用建议条目→审批的稳定键未要求保存，Case 范围审批未必有 Alert ID，不能按相同目标／文字强连。页面按真实 alert_id 或精确 Run 范围读取，有关联才显示。不得将 actions.record.incident_id 当 Fusion incident_id [C12/C13] |
| D09 检测时间／完成取证时间 | 原材料存在时可保留；E 有真实阶段 ts | 没有统一 Alert.detected_at 或通用“取证完成”字段。只显示明确来源／真实步骤的时间；输入没给检测时间不列补采任务；Tool 有返回不自动生成“取证完成”，不按发生时间加固定秒数 |
| D10 事件队列卡片 | Incident 成员关系／严重程度具备；独立状态、负责人缺失 | 事件数、成员数、聚合等级可派生；“处理中”“待分配”不能准确支撑，依赖 I05/I06。不得以 Run running 或成员任一负责人补足 |
| D11 事件压缩率／攻击中断 | 当前归属可得到事件及成员数量；实际响应有动作记录 | 压缩率必须同租户、同范围、同一成员口径，不能混用全告警与部分事件；攻击中断必须准确关联真实成功执行证据，不能数标签。最新远端已换掉攻击中断卡，不新增该功能 |
| D12 启动调查与告警业务状态 | 当前 Run 有独立状态／范围；A.status 列存在 | 当前 v2 Case 启动不写 A.status；若按用户已确认“启动调查算进行中”呈现业务状态，后端需明确写回。该问题不是缺 Run 数据，不能把 Run 状态直接覆盖告警状态 [C7/C14] |

## 5. 从保存数据到当前 Case／Tool 的逐字段比较

| 编号／字段 | 已保存位置 | 当前消费结果 | 确认结论 |
| --- | --- | --- | --- |
| T01 来源、规则、战术／技术、Fusion 评分、同次分诊评分 | A/F；同次 triage E | Case A.source/A.detection、T 实际冻结、入 hash 和有界模型投影 [C2/C7] | 第 4 批已补。新增字段值共用 2048 字节、原文视图 8192 字节；超限／guard 省略有标记，不声称每次模型能看到全部 |
| T02 OCSF 进程 PID、命令行、父进程等 | 输入存在时保存在 A.raw_event、Case 冻结来源、湖 ocsf_json | OCSF 整段命中原输入 guard 时，模型不能看原段；当前无这些必要语义字段的独立安全投影 [C7/C9] | **读取／投影缺口（S5-02）**；不是没有保存原文。保 guard 和预算，按确切源路径投影已存值，不从标题／旧报告补造 |
| T03 进程名称、路径、SHA256、账户 | 湖 process_name/file_path/hash_sha256/user_name | process_activity SELECT 已取 [C9/C17] | 已通；file_path 是湖 file.path 的当前映射，不能自动称可执行命令行；算法不明的 hash 不填 SHA256 |
| T04 进程类别、活动、动作、结果 | 湖 class_uid/activity_id/action/outcome | process_activity SELECT 已取 [C17] | 已通；未知动作／结果不证明进程启动成功 |
| T05 进程会话 ID | 湖 session_id | process_activity SELECT 未取 [C9/C17] | **读取缺口（S5-03）**；不需新列 |
| T06 进程 PID／父进程／命令行细节 | 有则存湖 ocsf_json/raw_payload，无独立上述平铺列 | process_activity 未取 JSON，也未解析上述已有值 [C9/C17] | **读取缺口（S5-03）**；与 T02 分别是 Tool 和告警模型视图两条路径，不能只补一条就称全通 |
| T07 网络源／目标 IP、目标端口、协议、进程、主机、时间／ID | 湖 source_ip/dest_ip/dst_port/protocol/process_name/src_hostname/event_time/event_id | network_connections SELECT 已取 [C17] | 已通；TCP/443 仍不能直接证明 HTTPS |
| T08 网络源端口 | 湖 src_port | network_connections 未取 [C9/C17] | **读取缺口（S5-03）** |
| T09 网络目标主机名 | 湖 dst_hostname | network_connections 未取 [C9/C17] | **读取缺口（S5-03）** |
| T10 网络动作／结果 | 湖 action/outcome | network_connections 未取 [C9/C17] | **读取缺口（S5-03）**；否则不能仅从连接记录判断允许／阻断／成功 |
| T11 网络会话 ID | 湖 session_id | network_connections 未取 [C9/C17] | **读取缺口（S5-03）** |
| T12 告警—查询行对应及重投去重 | source_event_ids 对 event_id；tenant/time/class/host；查询工件 | 精确来源匹配；查询先按 tenant/event_time/class/event_id 去重后限量，process.v3/network.v2 [C7/C17] | 第 1、3 批已补；仅同主机不是来源匹配；保原限额、省略和失败／空结果区别；旧结果不能冒充新合同结果 |

T02/T05/T06/T08—T11 是当前仍需处理的已存字段消费缺口。它们不证明 r13 报告错误由缺字段导致；r13 当时 raw 已完整进入模型仍出现无源陈述，报告问题继续单列、暂停修复。

## 6. 已改什么、数据表是否改过

| 批次 | 修前可复核断点 | 当前本地处理 | 表／列变化 | 原验证证据 |
| --- | --- | --- | --- | --- |
| 1 | 告警与湖 ID 优先级／UUID 写法不同；固定 INSERT 缺列绑定失败仍报成功 | 统一 event_id→id→metadata.uid 和有效 UUID 表示；列与行同步省略默认 ID；按确认 INSERT 记 laked，公开缓冲／失败／放弃量 | 无 DDL；使用原 PG/CH 表 | [第 1 批](field-alignment-fix1-20261101.md)：39 个相关用例最新通过；本地驱动／替身，不是实库写入 |
| 2 | 不同发生被旧内容指纹折叠；host/user 同名混并；实际归并理由未完整保存 | event-v1 明确身份、有限旧快照兼容、entity-v2 typed key；保存当次 correlation_basis；执行分支检查提升开关 | 无 DDL；F 的 identity/correlation_basis 与首份快照增加可选值 | [第 2 批](field-alignment-fix2-20261102.md)：66 个用例最新通过，初错误保留 |
| 3 | 已收时间／标签／对象／窗口引用漏传；默认 50 分；activity、hash、raw、重复查询偏差 | 保字段及来源／省略元数据；未知分数 NULL；正确算法 SHA256；JSON 有界包装；重投查询去重 | 无 DDL；原 alerts、F JSON、湖列及有界 Redis 窗口状态 | [第 3 批](field-alignment-fix3-20261102.md)：124 个用例最新通过，初失败保留 |
| 4 | IOC ORM 漏列；原厂／来源编号／负责人／资产标签／成员边／同次评分漏读，时间混用 | 共享 projection；已有 IOC 映射；typed 对象边／阶段计数；资产与多 Case 读取；业务时间单列；Case 冻结投影 | 无 DDL；映射已有 iocs 列，新增返回／冻结 JSON 字段 | [第 4 批](field-alignment-fix4-20261102.md)：68 个用例最新通过，初失败保留 |

四批数字不相加成一次验收通过数；有跨批复用／重叠。四批未再次提交、推送或部署，真实 PG／CH 和远端页面没有验收。本轮未新增业务修复，也未重跑业务测试。

## 7. 交给后端的最小字段合同与本轮剩余工作

以下是缺口所需的逻辑字段，不是声称已存在的新表，也不规定后端采用哪个 CRUD／页面实现。

| 对象 | 必须能持久化／准确关联的内容 | 现有基础和缺的部分 |
| --- | --- | --- |
| Fusion Incident 业务记录 | 同租户稳定 incident_id；人工 title/description；handling_status；assigned_to_id/assigned_at；classification；priority；tags；resolution_note/resolved_by/resolved_at；业务 created_at/updated_at | 成员归属已经在 F，概况缓存已有。缺上述独立管理事实；业务时间必须包含自身／成员变更。不能复用 Case 对象顶替 |
| 普通 Alert 评论 | comment_id、tenant_id、alert_id、author_id、body、created_at；如支持编辑再保留对应修改事实 | 有 Case 评论、反馈理由、通用审计设施；缺普通告警评论的稳定对象合同与读回 |
| 事件／告警处理活动 | activity_id、tenant_id、subject_type/id、actor、occurred_at、action、真实 before/after、批量目标 canonical IDs | 复用 audit_log；缺准确业务主体与完整目标关系，不能靠整 Case Timeline／仅数量补齐 |
| 处置关联 | 建议的稳定标识（若页面要逐建议闭环）、实际 approval_id/action_id、Alert 或固定 Run 范围、实际结果／错误 | approval→action 已存在；不能新造“待审单”。没有建议→审批连接时保持未关联，不按文本匹配 |
| Case／Tool 字段 | T02/T05/T06/T08—T11 的已存值，确切来源路径、query_contract、缺失／省略标记 | 复用冻结、guard、有界查询与工件；不新增 Case 记忆层，不增加模型调用或预算 |

下一步可以直接沿 T 表补已存字段读取；独立 Incident、评论／活动按上表交后端承接。A05、D05、D06、D12 是明确的状态映射／写回合同差异，也应交后端，不能从字段表中删掉后宣称页面数据已全部一致。I11 的两个时间口径已明确拆开，页面应选择所需来源，不能把当前 last_seen 悄悄解释成 max(event_time)。

不列入本轮待办：上游没给的厂商／时间／规则／实体；不存在的库存标签；历史已经丢失的 raw／归并依据；搜索／导出／级联的页面实现；报告语义修复与新模型批次。

## 8. 代码证据索引

每项结论对应下列实际符号／路径；[本轮核对清单](../operations/page-field-support-matrix-20261102.json)固定需求 blob 和源码 SHA256，用于区分本轮文档与后续改动。

- **C1** [Alert 模型](../../services/api/app/models/alert.py)、[v1 alerts 的 AlertResponse／AlertDetailResponse／update_alert](../../services/api/app/api/v1/endpoints/alerts.py)、[初始表 event_time/iocs](../../services/api/migrations/001_init.sql)。
- **C2** [alert_projection：alert_source、alert_objects、detection_fields、triage_fields、assignee_names](../../services/api/app/services/alert_projection.py)。
- **C3** [incident_reader：IncidentOverview、IncidentMember、read_incident](../../services/api/app/investigation_v2/incident_reader.py)、[incident_api](../../services/api/app/investigation_v2/incident_api.py)。
- **C4** [processing_context：read_asset_context／lookup_params](../../services/api/app/services/processing_context.py)、[资产及关联表](../../services/api/migrations/013_asset_inventory.sql)。
- **C5** [alert_status 的 RESOLVED_STATUSES／is_unresolved](../../services/api/app/services/alert_status.py)。
- **C6** [related_investigations](../../services/api/app/investigation_v2/related_investigations.py)、[case_links](../../services/api/app/investigation_v2/case_links.py)、[Case 模型](../../services/api/app/models/case.py)。
- **C7** [case_analysis](../../services/api/app/investigation_v2/case_analysis.py)、[case_source_material](../../services/api/app/investigation_v2/case_source_material.py)、[alert_context_api](../../services/api/app/investigation_v2/alert_context_api.py)。
- **C8** [Explain 返回结构及提取](../../services/api/app/services/alert_explain.py)、[Explain 请求接口](../../services/api/app/api/v1/endpoints/alert_explain.py)。
- **C9** [lake_writer 字段／event_to_row](../../services/fusion/app/services/lake_writer.py)、[lake_material](../../services/fusion/app/services/lake_material.py)。
- **C10** [feedback](../../services/api/app/api/v1/endpoints/feedback.py)、[analyst_feedback 保存字段](../../services/api/app/services/analyst_feedback.py)。
- **C11** [alert_rail：build_mini_timeline](../../services/api/app/services/alert_rail.py)、[AuditLog 模型](../../services/api/app/models/audit.py)、[CaseTimeline 模型](../../services/api/app/models/case.py)。
- **C12** [AgentApproval 模型](../../services/api/app/models/responder.py)、[approvals：decide／_dispatch_decision](../../services/api/app/api/v1/endpoints/approvals.py)。
- **C13** [ActionRequest／ActionResult](../../services/actions/app/models/action.py)、[actions 路由的 record 保存](../../services/actions/app/api/router.py)、[action_store](../../services/actions/app/services/action_store.py)、[动作记录表](../../services/api/migrations/055_action_records.sql)。
- **C14** [investigation 模型](../../services/api/app/models/investigation.py)、[execution_index](../../services/api/app/investigation_v2/execution_index.py)、[investigations 用量／运行读取](../../services/api/app/api/v1/endpoints/investigations.py)。
- **C15** [incident_summary](../../services/api/app/investigation_v2/incident_summary.py)、[fusion_incident_summaries 表](../../services/api/migrations/120_fusion_incident_summaries.sql)。
- **C16** [correlator](../../services/fusion/app/services/correlator.py)、[alert_sink](../../services/fusion/app/services/alert_sink.py)。
- **C17** [case_analysis_tools：两组 SELECT 字段及 query_contract](../../services/api/app/investigation_v2/case_analysis_tools.py)。
