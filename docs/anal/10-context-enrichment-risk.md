# 10 资产身份、增强、风险与历史材料

> 用途：固定上游源码与历史证据分析（2026-10-20对齐）。本轮使用已有资产、身份、漏洞及历史材料支撑告警处理，不承担资产发现、扫描、采集或通用数据湖建设。 当前职责见[范围](../operations/alert-processing-scope.md)，阶段退出见[路线](../operations/service-roadmap.md)，执行批次见[依赖计划](../operations/dependency-migration-plan.md)。

返回[总入口](README.md)或[模块总览](01-system-map.md)。本章对应 **M14/M15/M17/M18/M21**；它们影响检测、排序和调查，不是简单的一次“补字段”。

<a id="m14"></a>

## M14 资产、身份、漏洞与业务上下文

### 职责与来源

将告警中的 IP/主机/账号连接到“谁、什么资产、承担什么业务、有什么暴露和权限”。来源包括资产/漏洞录入、连接器同步、组织上下文导入、身份/云资源和图投影；来源是否存在、是否及时要单独验收。

入口：[assets.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/api/v1/endpoints/assets.py)、[context_import.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/services/context_import.py)、[incident_context.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/services/incident_context.py)、[identity_graph.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/api/v1/endpoints/identity_graph.py)、[posture.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/api/v1/endpoints/posture.py)。

| 子模块 | 输入 | 处理/存储 | 输出与下游 |
| --- | --- | --- | --- |
| 资产库存 | 标识、主机/IP、owner、criticality 等 | 创建/更新资产；按 tenant 读取 | 告警资产匹配、队列优先级、调查资产面 |
| 资产漏洞 | asset ID、CVE、CVSS/利用信息 | 保存本资产暴露，关联资产事实 | 漏洞/KEV 风险加权；不等于已经被利用 |
| 组织身份 | 部门、员工、账号、云账号、业务应用 | context import 校验 ID/枚举，建立上下文/关系 | 账号背后人员、部门、在职状态、业务责任 |
| 身份/权限图 | 用户、角色、权限、资源关系 | 图模型与受控遍历 | 特权、影响范围和可能关联路径 |
| Posture/CSPM | 资源配置、扫描请求或外部 finding | finding 生命周期、抑制/解决、扫描回执 | 配置风险；与运行时告警互为背景，不自动等同一个 Alert |
| 五维调查上下文 | tenant + Alert/entities | 有界遍历 identity/asset/cloud/business/threat | 五组数据、narrative、partial/errors |

`IncidentContext` 对各维度限量，图路径上的节点需 tenant scope，公共技术/漏洞等参考节点有明确例外；公共节点不能成为横跨私有租户资产的桥。部分维度失败保留其他维度并显式 partial。

### 状态与关键边界

资产存在不代表 owner、criticality 和漏洞扫描已更新；账号已停用、员工离职和设备隔离是不同事实。实体关联必须有匹配规则和来源，不用文本同名自动断定是同一人/设备。

API 可录入资产/扫描不证明采集连接器已持续同步；有图遍历代码不证明 Neo4j 中已经形成关系。20 未启 full 图依赖，本轮没有运行 CMDB/HR/云数据导入。

### 测试与移植

`test_context_import.py` 验字段与关系，`test_incident_context.py` 验五维结构、scope/partial，`test_posture_store.py` 验 posture 存取。后续真集成卡：一个合成员工/账号/资产/CVE/应用 → 入库和关系可读 → 同租户调查返回准确上下文，别租户不可见，缺 owner 保留未知。

移植复用实体匹配与维度接口，使用目标已有资产/身份 Provider；不要为读取一个 owner 引入整个参考图 schema。图推理留在调查层，不回塞 Fusion 主关联。

<a id="m15"></a>

## M15 多源 IOC 增强

### 正常路径

入口：[enricher.go](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/enrichment/internal/enricher/enricher.go)、[types.go](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/enrichment/internal/enricher/types.go)、[handler.go](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/enrichment/internal/handler/handler.go)。这是 Go 服务，与 Python Threatintel feed 入库是两个模块。

```text
IOC(type/value/force) → 类型校验 → 可选 Redis 缓存
→ 按类型选择已配置 provider → 并发请求 → 合并有效结果
→ 写缓存 → 风险/来源/时间等统一结果
```

| 输入/输出 | 具体含义 | 衔接 |
| --- | --- | --- |
| `ioc_type/value/force` | IP/domain/hash/URL 等；force 绕缓存 | API handler 与 wrapper 的字段拼写要核对，不能只看函数名 |
| 信誉、risk、confidence | 多源结果的合并值 | 供 Fusion confidence 或调查参考；不是当前事件恶意证明 |
| classification | tactics/techniques/actor/campaign/malware | 参考情报映射，不是实际攻击链 |
| geo/WHOIS/DNS/open ports | IOC 背景 | 暴露状态的观测时间与来源重要 |
| vulnerabilities/brand/darkweb 等 | 对应 provider 返回内容 | 未配置或未命中不能填成虚构内容 |
| sources、cached、timestamp | 哪个渠道何时贡献 | 用于判断缓存陈旧性、覆盖和引用 |

未配置 client 可以 no-op；个别 provider 失败不阻止其他结果合并。全渠道无有效结果时仍可能返回仅含 IOC/时间的空背景对象；这个 HTTP 成功不能被解释成“所有渠道查证安全”。原始错误和覆盖信息应在目标 Provider 合同中保留。

缓存 key 在本路径以类型和值构造；若后续放入私有 tenant 情报或 BYOK 特有结果，必须重新检查 scope，不能默认共享缓存仍然正确。Enrichment 的字段枚举也不证明所有类型都在 `Enrich` switch 中被实现。

测试入口：[merge_test.go](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/enrichment/internal/enricher/merge_test.go)。最小卡：一个 IOC 两个替身来源（一成功一超时）→ sources/合并结果和错误覆盖 → 返回部分结果且不伪造全成功；真渠道用受控一个 IOC，记录实际 provider 和时间。

20 没有运行这个 full 服务及商业渠道验收。移植先选当前调查需要的一种来源，不一次接全商业客户端。

<a id="m17"></a>

## M17 风险累积、置信度与优先级

本模块不是一个万能分数。至少四类评分必须分开：

| 评分 | 输入/算法 | 输出/用途 | 关键限制 |
| --- | --- | --- | --- |
| Fusion anomaly/priority | 严重度、实体存在性、技术数量等固定特征；训练后模型，否则启发式 | FusedAlert 两个 0—1 分数 | 模型字段有值不证明 ML 已训练 |
| Detection confidence | severity、ML、技术覆盖、TI、上游 risk、IOC 等加权 | 0—1、high/medium/low、因素链 | 是检测置信，不是调查结论或响应权限 |
| RBA 实体风险 | 多条告警按严重度给实体加点并衰减 | 实体累计分、贡献告警、promoted 状态/实体队列 | 与主 Incident 关联和 Case 生命周期分开 |
| 工作台 priority | severity base × 资产/身份/漏洞因素并限幅 | API 排序分数和 rationale | 与 Fusion priority_score 不同尺度，不能混存比较 |

入口：[ml_scorer.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/fusion/app/services/ml_scorer.py)、[confidence.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/fusion/app/services/confidence.py)、[entity_risk.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/fusion/app/services/entity_risk.py)、[alert_priority.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/services/alert_priority.py)。

MLScorer 初始模型为空、缓冲在进程内；足量数据后可训练 IsolationForest/LightGBM。未训练直接走启发式，不应写成“默认就有经过验证的智能异常模型”。需要检查 status、实际训练输入和版本，不能只看类名。

Confidence 使用基值和有限因子，阈值默认 high≥0.70、low<0.40；后续 UEBA/漏洞/prior 仍可改变结果。移植应保留每个因素实际值与解释，避免给业务用户承诺统计校准概率。

RBA 处理 user/host/src_ip/domain，按 tenant Redis hash/ZSET 维护分数、contributors 和 top-N。默认阈值 80、半衰期 14,400 秒、窗口 86,400 秒，严重度点数来自配置。Fusion 在非重复告警处理的后段调用 observe，选最高 promotion 写入 narrative。实体 promoted 不等于持久 Case 已创建。

API priority 当前 severity base 为 critical900/high600/medium350/low150/info50，上限1000；再按 criticality、特权、KEV 等因素调整。不要套用 Alert ORM 注释的 0—100 或 Fusion 的 0—1。单元解释中应能看到“为何排在前面”。

测试：`test_entity_risk.py`、`test_confidence.py`、`test_alert_priority.py`、`test_alert_list_priority_sort.py`。最小卡为同严重度普通资产与关键/KEV 资产 → 真实上下文、因子 → 排序正确且 severity 不被悄悄改写；RBA 另检查同告警重投、衰减和跨 tenant。

目标已有 PG RBA/版本体系优先，不复制参考 Redis 权威风险状态。模型质量和优先级产品策略分别验收。

<a id="m18"></a>

## M18 业务规则与例外

入口：[business_context/engine.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/services/business_context/engine.py)、[business_context.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/api/v1/endpoints/business_context.py)，自动分诊在模型调用之前读取并应用本 tenant 规则。

输入：版本化 tenant 规则、字段条件、severity/tag/route 等动作、匹配告警。Engine 构造 snapshot，按规则顺序求值、更新当前视图，输出 before/after、matched IDs、suppressed。命中 suppress 后短路，不能被后续规则再取消。

这与检测规则的 tenant overlay 不同：overlay 决定事件是否生成检测；business rule 作用于已成告警的后续处理视图。例如批准扫描窗口可影响路由/分诊，但不能抹除原始日志和既有事实。

更新/热加载要检查 API 持久化到 Agents reader 的真实传播；同进程 `replace` 成功不证明所有副本已同步。移植需记录实际采用版本、作者和原因，保留源事实与决策记录。

测试 `test_business_context.py`：同一告警在两个 tenant 的规则集 → 匹配/投影 → 只修改本 tenant；suppression 零模型调用；未命中保留原值；格式非法返回明确错误。当前文档没有新增自动抑制的产品批准。

<a id="m21"></a>

## M21 事件历史、会话与证据查询底座

只有当前 Alert 不足以调查前因后果。需要保存和查询来源日志、上下文窗口、会话归属，并让查询结果回到 Run/Evidence。

| 子模块 | 输入 → 处理 → 输出 | 与告警链路关系 |
| --- | --- | --- |
| Lake 写入 | 规范化事件 → 可选归档 → 历史事件 | 未提升告警的普通活动仍可能是调查证据 |
| Session | tenant/source/session key → 稳定 session ID、窗口/归属 → 事件与告警上下文 | vendor 明示和 derived 会话要分清 |
| Lake 查询 | 实体、时间窗、限制 → 受控查询 → 事件及统计 | 不把查询失败/截断误当无可疑活动 |
| 外部 SIEM 联邦查询 | tenant 后端和 indicator → 生成厂商查询 → 来源结果 | 本地没有归档时仍可能有外部原件 |
| 图/时间线投影 | 事件关系与来源 → 有界遍历/排序 → 时间线、邻域 | 投影可补背景，不能替代原始证据来源 |

入口：[lake_writer.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/fusion/app/services/lake_writer.py)、[sessions.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/fusion/app/services/sessions.py)、[lake API](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/api/v1/endpoints/lake.py)、[agent_tools API](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/api/v1/endpoints/agent_tools.py)。

Session ID 按 tenant/source/key 用 UUID5 产生；当前代码还区分 session key kind 和 originating human，并处理 derived idle close。不能从“时间接近”推断来源厂商确认了同一会话，也不能把所有没有 session 的告警填成 session of one。

湖、图、搜索是可选部署组件；CORE 接入/Fusion 成功不代表历史证据全量可查。20 没有这部分完整运行证据。移植应先接实际已有 Provider，再按实际原件/时间范围记录覆盖。

测试 `test_sessions.py` 检查 session 身份、关系和关闭；查询另用一个固定来源窗口 → 实际请求与返回 event IDs → 被 Evidence 引用并进入模型的同一材料卡。前端能显示“17 条事件”必须有真实结果依据。
