# 字段对齐第4批：共享读取、成员关系与业务时间

2026-11-02。[第1—3批](field-alignment-fix3-20261102.md)之后，本批补 S1-02、S3-03/04/05、S4-02/07 和 S5-01 的读取断点。**本地实现及直接验证完成，尚未部署或验收远端页面；列表条件、管理写入、Case原文语义／Tool明细和报告仍有后续工作。** HEAD保持 `b400fd0`，四批修改未再次提交或推送。

## 已改处理逻辑

| 项目 | 当前行为 | 边界 |
| --- | --- | --- |
| 原始厂商、来源编号 | 新共享`alert_projection`由告警列表／详情、事件成员、告警上下文及Case使用。原厂仅取已保存raw_event或其raw_data中的明确`original_vendor`／CEF `deviceVendor`；来源编号取Fusion identity.source_alert_id，external_id另列 | 原厂未知返回null，不从connector_type、identity.source、metadata.product推测；这些字段可能描述中转平台。保持身份算法与原材料，未要求上游新增字段；其他未明确表示原厂的格式保持未知 |
| IOC、逐成员对象及阶段 | ORM补映射迁移001已有`alerts.iocs`。共享对象读取合并affected_*、entities、iocs；列表／详情、事件、Case和rail可读。事件返回逐成员objects和带canonical source_alert_id的object_links，并集仍保留；各成员每个已有战术去重计1，附总和可能超过告警数的提示 | 对象边表示本成员报告了此对象，不证明因果。检测标签不当攻击事实，不由技术号猜战术；旧图已有边不删除或重写 |
| 负责人读取 | 列表／详情、事件成员、告警上下文输出assigned_to_id、assigned_at，并按同租户User.username批量解析名称 | 找不到名称仍保留负责人ID，不能表示未分配。没有把affected_users当负责人；未修改改派／级联写入 |
| 资产及匹配依据 | 现有processing-context查询补assets.tags、实际name/FQDN/IP命中项，以及同租户关联表保存的match_field/confidence。查找键也读取entities-only主机。事件GET可用`include_assets=true`取得逐成员资产视图 | 复用原每次21行读取／最多20行返回和失败状态。事件一次最多读取前20成员资产，asset_coverage列已读／省略成员；单成员可继续用其processing-context读取。库存是当前快照，不是告警时刻资产状态，不把no_match/unavailable当资产不存在 |
| 当前多Case关系 | 事件GET新增`include_investigations=true`，沿已有cases:read权限及read_related查询，成员返回case_ids与case_ids_truncated；不请求时为null。告警上下文继续返回当前多Case及固定Run选取范围；v1详情／列表提供case_links_url | case_id明确标记legacy单值，不代替当前关系。当前Case最多50条并保留截断标志。旧单字段写入口留兼容，后续第6批处理明确关联写合同，不做破坏多Case的双向单值同步 |
| 旧图选取范围 | `_anchor`改为只认Case.alert_ids；单值Alert.case_id不再扩成员，也不能证明手动指定告警属于Case。仅有一个当前Case时可定位，多个时仍标歧义。图准备补读已有IOC | 旧图、旧报告不回填；当前图准备不是本次v2 Run证据，也不改已冻结Run的成员 |
| 发生时间／业务时间／材料新鲜度 | 事件first_seen取min(member.event_time)。新增updated_at取成员业务更新时间；source_updated_at保留分诊／可选Run材料新鲜度。关联调查只改变后者。旧告警详情缺narrative时仅生成响应文字，不UPDATE、commit或修改ORM对象 | 事件自身状态／负责人等尚待第6批持久化；那时须纳入updated_at，不能把生成概况或Run进度当业务修改。旧数据中已经受入库默认值／GET污染的时间不批量回填 |
| 检测与同次分诊字段进Case | A中保存source、detection（规则、标签、Fusion分数／等级／依据、计算状态、时间／来源完整性元数据），T从同一次triage事件取confidence、verdict、理由、findings、proposed_actions、Run/事件ID和时间。指纹包含新增字段，新增field_projection_schema区分本次结构 | T是已有分析判断，分数是对配对判定的信心，不是风险；不与当前人工disposition或Alert.ai_score混配。旧Fusion评分保留且标legacy_unverified；显式unknown/disabled/failed不显示残留分数 |

原字段仍在冻结材料及API中；新增模型字段值共用2048字节额度，超额按完整字段省略并注明原因。对新增值在嵌套／转义前沿原输入合同检查，命中则仅模型视图省略，保存材料不改。原8192字节来源模型视图、24000总token、四次模型／四次Tool及一次纠错规则保持，不新增记忆系统或模型调用。原始OCSF被guard挡住后的必要语义投影仍是第7批，不能称已全部入模。

## 数据表及接口

**无DDL、迁移、新业务表或Fusion写入变化。** 映射已有PG iocs列，读取现有alerts、users、assets、alert_asset_correlations、aisoc_cases和调查账本。新增主要是API返回字段及Case冻结上下文字段；原档案与已结束Run的保存结果读取保持。

- v1告警列表／详情：source、detection、objects、iocs、负责人ID／时间／名称、case_links_url。原confidence平铺字段也遵守显式计算状态。
- v2事件：updated_at、tactic_counts及提示、object_links；成员对象／规则／来源／评分／负责人。资产与当前Case按上述参数显式读取，仍受原租户和权限约束。
- v2告警调查上下文：共享source/detection/objects、同次triage评分和来源、负责人；legacy_case_id与当前investigations.cases分开。
- Case：新增字段实际进入case_context、保存步骤、材料hash和有界模型视图，不只存在于DTO。旧材料hash不能冒充包含新增字段的当前材料；历史报告仍照原件读回。

## 验证与前后比对

**68个不同相关用例最新结果通过，新增9个；不是一次68项首过。** [证据目录](../operations/evidence/fusion-field-fix4-20261102/)和[回执](../operations/fusion-field-fix4-20261102.json)保留初失败、修复及定向复核：

1. 事件／关联／概况15项初14过1失败：旧测试期待external_id充当source_alert_id，按已确认口径改为来源编号空、外部编号保留，定向通过。
2. 图／rail／详情38项初37过1失败：取消GET缓存写入时，空叙述误返回空串；恢复为null，定向通过。测试对“必须UPDATE/commit”的旧预期随已确认规则改为只读。
3. 新共享字段首6项5过1错误：嵌套字符串经JSON转义后未单独经过输入guard；补原值检查及递归检查后通过，不放宽guard。新增资产覆盖／权限／负责人用例通过；同次评分、冻结副本、字段改动使hash变化及模型省略标记已验证。
4. 受影响Case实际启动／查询／读回、旧材料复用失效、原文冻结、一次纠错，以及列表租户边界通过；HTTP、DB、模型均为本地替身。负责人读取变更后只复核受影响入口，其余通过项复用。

[同输入对照](../operations/evidence/fusion-field-fix4-20261102/before-after.json)直接加载b400fd0读函数与当前读函数，使用相同合成PG行；两边均使用当前安装依赖／模型，不是完整旧部署。确认IOC从漏读到保留、来源编号从错用外部编号到接入编号、事件首次活动从入库first_seen到发生时间、同次分诊评分可读，以及只改规则名由不改变材料hash变为使hash变化。资产SQL通过PostgreSQL方言解析，**不证明真实PG查询已经执行**。

0真实业务数据库／Redis／湖／厂商／模型调用，0真实新Run／部署／上传；r13及前批原件保持。来源前置输入问题不纳入。

## 原后续安排（已由用户收口为字段工作）

2026-11-02用户随后明确功能交后端实现。以下保留本批结束时的原计划，当前不再执行列表/管理功能开发；以[最新字段支撑计划](field-alignment-impact-and-repair-plan-20261101.md#当前后续计划只收敛字段与数据支撑)为准。已有修改未自动回滚，旧回执保留当时指纹。

下一第5批接列表真实合同：搜索和时间／来源／标签／负责人条件、稳定排序、总体统计、按真实调查Run去重计数、未选择导出前200／有选择导出所选、旧fp完成分组及保留标记。第6批再做事件管理、评论、反馈、负责人及解决事件的成员级联和读回；第7批补Case语义与Tool；第8批才恢复具体报告问题。

本批是后端本地读取修复，不声称远端页面已更新或线上数据已回填。用户16项口径不重问。报告修复继续暂停、r13批次不重试、5.3未完成。前批回执保持当时指纹；重叠源码当前指纹见本批回执。
