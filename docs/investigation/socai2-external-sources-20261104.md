# 外部来源与补查接线

2026-11-04，OpenSpec `complete-socai2-investigation-chain` 3.6。这里只描述新服务的数据适配，不切换旧服务、不迁移业务数据、不启用供应商调用。验证结果由根任务的固定回执汇总，本文件不将替身测试写成真实供应商验收。

## 审计结论与边界

原 C2 已实际读取资产、新表同对象历史告警和内部TI；UEBA、知识、graph此前统一标未连接。C4已实际适配进程/网络湖查询，认证及来源产品主机未接。

代码中可复用的真实来源及本批用途：

| 来源 | 实际实现/数据 | 本批接线 | 不能证明什么 |
| --- | --- | --- | --- |
| UEBA风险背景 | `public.user_risk_profiles` 的既有用户风险聚合 | 同租户、明确user对象账号精确匹配；风险分数及计数是已有分析，标prior_analysis | 不是独立观察，不证明当前Case恶意；来源表无输入对象namespace |
| 知识 | `public.aisoc_kb_documents`，旧知识端点使用同表 | 本案冻结告警标题作检索键，英文FTS读取当前runbook/playbook/sop段落 | 不是案件证据，不是向量/语义检索，也不重建历史版本 |
| 外部身份图 | `incident_context.read_identity_context_for_accounts` 专用只读入口 | 明确有namespace的冻结user对象→同租户账户，返回身份/雇佣/部门/经理背景及源计数 | 不是攻击路径，不通过旧Case/Alert图锚点构图，不证明历史雇佣事实或实体唯一身份 |
| 认证活动 | 同一ClickHouse `raw_events` 的OCSF class_uid=3002 | 冻结source hostname、窗口、租户；去重后限量，原始OCSF及扁平字段保留 | 没有hostname的纯账户Case不能用此入口查；空结果不证明未登录/已授权 |
| 产品主机 | 原来源绑定的CrowdStrike `get_host` 只读适配 | 只为冻结告警明确connector_id、connector_type=crowdstrike、合法hostname提供绑定；派发时重新查同租户连接器及权限/凭据 | 当前设备快照不是历史状态、进程树、授权记录；未命中不等于安全 |

不机械复制旧 incident_context 的全量遍历；该路径部分入口会创建图节点/关联旧public告警。新 graph 适配只调用现有独立身份读会话，不初始化通用图或创建节点。身份来源返回的identity_id保作稳定来源键；缺图配置、连接异常与成功无匹配分开。

## 开关与独立数据范围

- `SOCAI2_SOURCE_UEBA_ENABLED`、`SOCAI2_SOURCE_KNOWLEDGE_ENABLED`、`SOCAI2_SOURCE_GRAPH_ENABLED`、`SOCAI2_SOURCE_PRODUCT_HOST_ENABLED` 默认false，仅true/1启用。关闭时保存未连接/未启用状态，不发来源请求。
- `SOCAI2_LAKE_DATABASE` 是服务端受校验配置，默认aisoc；独立服务设置自己的数据库名。只允许字母/下划线起始的字母数字下划线标识符，不让请求或模型选择数据库。
- 新C4目录冻结来源数据库，实际查询前核对服务配置仍一致；不一致明确拒绝本次查询。业务租户、hostname、时间、class_uid仍使用绑定参数。原旧服务的查询代码不改。
- C2的PG来源来自**该独立服务自己的数据库连接**，没有跨库隐式回退。源表缺失、列合同不符或无读取权限保存unavailable，不假装空查询成功。
- 所有适配共用原Run的4工具/4模型/24000tokens/120秒/行数上限，没有另加查询额度。可选来源即使启用，也可能因前面查询已消耗预算而标not_attempted_budget；目录存在不等于实际执行。
- 完整C1–C6执行器在C2内保留`min(2, max_tool_calls // 2)`个现有工具槽给C4，原4次总额时C2至多用2次。来源顺序仍为资产/历史/TI/UEBA/知识/身份图，达到C2边界记`tool_budget_reserved_for_evidence`及not_attempted_budget；独立调用C2仍沿原合同，不增加排序配置或总预算。

## 流程和产物

C2沿已有事务：冻结C1→登记工具步骤/原参数并提交→来源读取→保存tool_response及C2汇总→模型按角色消费。完整来源回复受原128KiB保留上限，整行省略及数量截断明示；查询失败的rows为NULL，成功空为[]。Graph的candidate/eligible/truncated/import_timestamp_missing及映射数量在C2汇总source_metadata持久化，不能只返回空数组而丢覆盖含义。

C4沿已有问题级Deep目录：服务端生成认证或产品绑定→模型只能选B绑定→提交running/request→实际只读查询→保存原返回、字段投影和角色。产品字段标source_label；认证来源记录字段是observation，related_alert_ids仍仅查询绑定。C4模型视图改为沿持久化citation_roles传递角色，避免将产品当前状态升级为攻击行为观察。

产品主机查询读取当前状态，允许冻结范围没有历史时间窗口；认证/进程/网络湖查询仍要求有效窗口。Deep可选目录按每个绑定核对这一区别，关闭的适配不提供给模型选择。完整执行器及Deep默认网关绑定当前服务的租户数据库会话。C5保留产品查询回执，但明确省略当前快照行为边，记录`current_snapshot_not_activity`。

已知产品未配置/禁用/凭据缺失保存失败或跳过及原因；传输不确定仍保持unknown占槽，不自动重试。重复绑定返回第一次保存的回执，后来配置启用不会把旧跳过记录改成已查；新运行才重新形成目录。

## 具体字段

| 数据组 | 读取并保存的字段 | 来源角色与约束 |
| --- | --- | --- |
| UEBA主体 | profile_id、external_user_ref | 精确账户匹配，无源namespace，仅同租户候选 |
| UEBA评分 | risk_score、risk_tier、score_provenance | 原值/NULL保持；`stored_prior_analysis_calculation_unverified` |
| UEBA聚合 | failed_auth_24h、off_hours_events_7d、peer_anomaly_score | 当前聚合，不当Case窗口完整活动 |
| UEBA时钟 | last_evaluated_at、updated_at | 真实来源时钟，不生成伪历史时间 |
| 知识身份 | id、title、doc_kind、source_url | 保存当前片段来源，不另发URL抓取；标题检索取前256字符，原长度、截断标记、变换及源路径随请求保存 |
| 知识片段 | chunk_index、chunk_total、content | 原片段，有界；被guard阻止的内容不入模型 |
| 知识时钟 | created_at、updated_at | 当前版本，冻结实际返回而非以后读最新 |
| Graph身份 | identity_id/kind、employee_id/kind、account、provider | 显式稳定键及来源；不混成用户实体确认 |
| Graph组织 | employee、title、is_active、employment_type、department、manager、manager_email及各ID/kind | 当前来源标签，不当事件发生时的授权事实 |
| Graph时间/关系 | start_date、end_date、imported_at/status/raw_sha256、employee_linked、relationship_source | 原来源时间/来源关系保持；未知不补 |
| Graph数量 | candidate_count、eligible_count、source_truncated_count、expanded_mapping_count、import_timestamp_missing | C2汇总留存；有截断则coverage不完整 |
| 认证绑定 | tenant_id、hostname、UTC起止、class_uid=3002、source_database | 左闭右开窗口，固定SQL、去重后取limit+1 |
| 认证原件 | event_id/time、class_uid、全部原查询列及ocsf_json | 原件不改；空查询不构成反证 |
| 认证语义 | actor.user name/uid、activity action/outcome/session、完整端点和源路径 | 原白名单按实际值投影，不从标题补值 |
| 产品绑定 | source_alert_id、connector_id、hostname、case_id、query_id | 只能源告警与主机同配，重新核连接器；凭据不存工件 |
| 产品设备 | device_id、hostname、platform、os_version、agent_version、local_ip、external_ip | 当前产品快照，source_label |
| 产品状态 | first_seen、last_seen、containment_status、tags | 原返回保留；复合字段不被标量投影强塞模型，省略明确 |
| 产品回执 | upstream_request_id、observed_at、source_connector_id | 可追踪真实来源请求，不用模型生成来源编号 |

## 四个例子

1. Case含账号Alice，风险表同租户有风险分数NULL、失败登录聚合2，另一租户也有Alice：只保存本租户行，NULL不补0；模型收到prior_analysis，不能据此断言Alice已攻击。
2. Case标题与某runbook匹配：保存命中文档段落及更新时间，提示它是处置指导。表存在但无命中为empty；表不存在/无权为unavailable；两者不产生安全结论。
3. Deep针对主机H查询认证：严格按冻结租户/主机/窗口/class3002查独立湖，保存源账户、动作、结果、会话。返回0行仍只说明该次有界查询无结果，不能否定告警或证明未授权不存在。
4. 告警A明确来自CrowdStrike连接器C且主机H，另一告警B有同名H却无connector：只提供A/C/H的产品绑定，不借用B或租户第一个连接器。产品返回当前Linux/最近在线时间是source_label，不能拼成告警时刻的进程观察；连接器禁用或缺凭据明确不可用。

## 验证范围

新增检查文件为 [test_socai2_external_sources.py](../../services/api/tests/test_socai2_external_sources.py)。PG来源与保存事务用既有独立合成库，产品/身份图/湖返回明确替身；实际独立服务的湖与模型验收由3.7的固定批次另列，不能合并称供应商/Neo4j真实查询已通过。外部完整攻击拓扑、其他供应商主机适配不在本次已支持来源目录，不能用当前身份graph或内部C5图冒充完整能力。

已完成批次（均清理受限测试角色及隧道，原回执不覆盖）：

- [045150首批](../operations/evidence/socai2-external-sources-20261104/20261104T045150/receipt.json)：9项首次通过，含UEBA/知识真实SQL、租户隔离、角色、认证持久化、产品绑定、关闭/失败/空结果区分。
- [045603边界复核](../operations/evidence/socai2-external-sources-20261104/20261104T045603/receipt.json)：3项通过，含标题检索截断、产品无窗口和C5不拼行为边、实际产品适配入口的绑定与传输不确定性。
- [045906预算复核](../operations/evidence/socai2-external-sources-20261104/20261104T045906/receipt.json)：2项通过，完整执行器C2预留2槽后C4仍能完成2次查询、总工具次数仍为4；独立C2原角色/重放合同回归通过。
- [050543角色复核](../operations/evidence/socai2-external-sources-20261104/20261104T050543/receipt.json)：产品快照的模型引用、候选角色与C5省略通过；同批新增Deep路径方法的测试断言失败，原件保留。
- [050826默认Deep路径](../operations/evidence/socai2-external-sources-20261104/20261104T050826/receipt.json)：新增方法最终通过，同时实际经过Deep默认网关、完整executor创建的默认网关、真实PG请求/结果/模型步骤保存；无窗口只提供产品绑定，第二轮模型输入仍为source_label，未把当前状态说成历史活动。
- 原[Deep空返回/预算回归](../operations/evidence/socai2-deep-20261103/20261104T050604/receipt.json)与[C4固定SQL回归](../operations/evidence/socai2-c4-20261103/20261104T050630/receipt.json)均通过。

最终为12个不同新增检查、2个已有回归最新通过，9个本批业务/测试文件Ruff通过，完整固定汇总及源码hash见[socai2-external-sources-20261104.json](../operations/socai2-external-sources-20261104.json)。累计保留4次原失败：默认网关配置导入路径错误已修；其余3次为新测试的产品字段不全、列表值误当字典、handoff替身缺unresolved答复，均只修夹具/断言，未放宽业务合同。所有批次受限角色/隧道已清理。
