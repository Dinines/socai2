**实施状态更新（2026-10-21）：** 用户随后已授权实施；本地源码、真实图/四Agent消费/Run工件和Markdown已走通，未发布。实际成果、首轮失败与修正后全新案例见[本批回执](attack-chain-path-local-20261021.md)，用法见[模块说明](../architecture/attack-chain-path.md)。未参与实现者deep_functional_tests结束独审限定ACCEPT、0阻塞，原5/15保持。下文“仅规划”保留当时事实，不覆盖本更新。

# 攻击链与Attack Path接入调查计划

2026-10-21。用户要求规划把已有攻击链/图谱能力接入调查，并核清是否只是尚未开启。本轮仅源码核对与规划，未改业务代码、配置或运行，未测试/调用模型/发布。沿[现有change](../../openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/tasks.md)2.1/3.1/3.4/4.1及B5实施，不另建产品任务树；实际完成仍5/15。

## 1. 结论与当前状态

**原有算法、接口、图写入函数已经迁入，但不只是缺一个开关。** API full配套已经配置Neo4j并补APOC，旧实测仅证明Case→Alert的PG两节点回退；不能再把本轮工作描述为“装full即可”。需补可信数据投影、真实Case/tenant交接、调查实际消费及按Run交付。原编排和算法复用，不合并四Agent、Router与Graph。

| 已有能力 | 原实现/开关 | 当前缺口与本轮处理 |
| --- | --- | --- |
| Fusion候选链 | `AttackChainGrouper`，`AISOC_ATTACK_CHAIN_GROUPING_ENABLED`源码默认true；Redis滚动TTL默认3600秒，输出enrichments.attack_chain | 沿用，不改算法/分数；不拿其chain_id充当Case ID或API chain_signature，本轮不重做Fusion |
| Case Attack Chain | `GET /api/v1/cases/{case_id}/attack-chain?window=24h`，PG共享实体候选、最多3跳/50条、规则评分 | 接到调查预取；不依赖Neo4j或LLM，没命中也要可说明查询范围/原因 |
| Case Attack Path | `GET /api/v1/graph/attack-path/{case_id}`，Neo4j查询；缺图时可PG回退 | 查询/写入函数都有，Case/告警业务未自动投影；需补数据与返回合同，不把回退图称为Neo4j完整路径 |
| Graph开关和身份 | Agents `AISOC_GRAPH_ENABLED`；API full层Neo4j disable=false；已有tenant reader机制 | 配置是必要条件之一；查各调用路径的reader/tenant和真实消费，不为图读取扩大模型/只读服务的写权限 |
| 调查消费 | 默认四节点已有ContextBundle；Router专业函数支持可选bundle；自动Graph末端有attack_path节点 | bundle无Case链/路径字段；Router未传bundle；Deep未读bundle/findings；末端查询不能倒算已进入前面模型 |

源码：[链算法](../../services/api/app/services/attack_chain.py)、[链API](../../services/api/app/api/v1/endpoints/attack_chain.py)、[图服务](../../services/api/app/services/graph_service.py)、[图API](../../services/api/app/api/v1/endpoints/graph.py)、[AttackPath agent](../../services/agents/app/agents/attack_path_agent.py)。旧配套状态见[full回执](full-support-migration.md)，上批真实调查边界见[逐步案例](investigation-functional-20261021.md)。

## 2. 这次怎样接：Case优先，自动告警沿Alert起点

本批先完成**已有真实Case的调查**，再接自动告警的canonical Alert起点。自动Run有可核实的同tenant真实Case关联时用Case分支；无Case时，候选链复用原seed_alert_id算法、图上下文用已有Alert邻居/影响范围。Case专用AttackPath明确not_linked，不伪造Case、不将canonical Alert ID、Fusion incident或Run.case_id历史占位当作Case。

推荐不自动创建Case或重写旧Run。原链内部已支持seed_alert_id，但当前公开接口仍从Case取种子；本计划明确新增一个薄的 `GET /api/v1/alerts/{alert_id}/attack-chain?window=24h` 入口，仅校验同租户告警并调用原算法，不改评分/窗口。Alert邻居和blast-radius/alert/{id}查询已有；称“告警关联/影响范围”，不冒充Case攻击路径。这个薄接口是必要接线增量，不是已有开关。多个Case关联无法唯一确定时保留歧义，走Alert材料，不任取一个Case。

最小数据流：

```text
Case调查POST / 自动Run的真实Case或canonical Alert
  → API按tenant读取PG真实Case及告警，或种子Alert
  → 确定性投影Host/User、Alert、IOC/Technique；有真实Case再连Case关系
  → 原Attack Chain算法 + Case Path或Alert邻居/影响范围（同Run预取一次）
  → 有界摘要交给当前编排的模型，完整有界结果交给Run工件
  → 原四节点 / Router / Graph继续各自流程
  → 步骤审计、链图工件、Markdown按Run可读取
```

**先在调查准备阶段定向补齐当前Case/Alert图**，不先做全平台实时同步、全量历史回填、outbox或后台修复队列。投影是依据PG已有事实写图的确定性业务操作，由可信API完成；模型只读，不提供任意写图工具。Case创建/告警变更后的持续同步后续有实际需要再接，不作为本次基本功能前置。模型新提出的IOC/主机/关系仅作假设，不能直接写成观测事实。PG告警投影也只表示“来源告警报告的关联”，不因存入PG就成为独立核实的入侵事实；记录来源Alert ID，对模型继续作为不可信资料处理。

## 3. 按以下顺序实施

| 顺序 | 输入与复用点 | 最小改动与交付 | 进入下一步的依据 |
| --- | --- | --- | --- |
| 1 目标与材料交接 | 正式Case调查参数、PG关联告警；自动Run当前Alert与已有Case关联 | 显式交接真实case_id/alert_id/tenant；Case代理虽然只传最新3条raw_alert.alerts，Case链种子仍由原API从全部关联告警取最早event_time，不拿最新3条首项替代 | 能准确说明本次Case、种子、实体/事件时间和裁剪范围；Case不适用时切Alert起点；Case路径明确not_linked |
| 2 准备可读图数据 | 当前Case关联告警或自动种子Alert已有的用户/主机/IOC/技术 | 复用graph_service upsert，按实体→告警→Case顺序；补直接阻断的节点键/tenant/边端点合同。只投影本次范围，缺字段不补猜值 | 真Neo4j返回实际Host/User等节点及有效边；与PG两节点回退区分 |
| 3 接原查询到调查预取 | 原Case链/路径；薄Alert链入口及已有Alert邻居/影响范围，已有读图身份 | ContextBundle追加可选链/图材料、Case/Alert锚点和来源状态；同Run预取一次，摘要有界，不按每个Agent重新拉一遍 | PG链和Neo4j图材料能分别取到；Case路径与Alert邻居明确分型，空/失败/not_linked/回退可辨 |
| 4 接模型和原编排 | 已取得且已记录来源的链/图材料 | 默认四节点用bundle；Router显式传bundle；Deep原用户输入加入有界链/图摘要；原末端AttackPath优先复用本Run材料，保原节点和输出 | 实际模型可见消息含对应材料及未知边界，不能只看state有字段；不增加固定模型调用次数 |
| 5 结果与交接 | 原事件/工件/报告出口 | 保存本Run链/图结构、查询范围/来源/错误/摘要及实际采用记录；Markdown引用关系依据，沿现API读工件 | 接口可取并与该Run输入、实际模型材料对应；结束独审及本地版本后阶段发布 |

这些是原任务内的实施顺序，不增加五个独立change、第二套完成标准或复杂准入框架。本轮只交规划，未开始上表实施。

## 4. 已核实的直接接线问题

### 数据写入不是原来已经自动发生

源码搜索中，Python `upsert_host/user/alert_node/case_node`的生产调用只见图API四个显式写端点。Case创建/关联只提交PG，Fusion/AlertsAPI没有调用这些函数；固定原版同样如此。`graph.py`“创建告警后自动写图”注释没有实际调用点支持，不能据注释称“只是迁移没开”。

原Go ingest有原事件写图，但其natural_key、Endpoint等标签及事件Alert标识，与Python Case图的id/Host/canonical Alert并不相同。本批不启动raw采集，也不将两种图模型整体重构为一套；从当前已受理告警/Case做确定性投影即可。

### 只修影响当前Case图的合同

- 节点先完整写入tenant和属性，再连边。原Case upsert会建无tenant Alert占位；Alert upsert会建无tenant Host/User占位，不能据占位节点宣称完整图。
- 核查现有节点键与同租户实体映射，防同名主机/用户串到其他租户；复用已有ID，不批量改写历史键。原单host_id/user_id参数与告警多值affected_*的交接须明确，不能只取首个就宣称覆盖全部实体。
- `get_attack_path`节点用id/value/technique_id，但边只用`.id`；IOC/Technique可能出现空target。最小对齐节点/边返回标识，使所有边端点实际存在；不改遍历/评分算法。
- 图读取沿当前Case/tenant reader和原权限；修AttackPath agent旧token名和漏tenant的调用，不给模型或永久七权限只读身份加settings:write。
- Neo4j不可用/未投影时，PG回退仍可交付，但工件记录backend/fallback/覆盖范围；接口必要的来源字段适配在实施时明确记录，不能用节点数推断来源。

这些仍是待实施设计。Alert-only只投影已有Alert及直接实体，不自动造Case；为候选链关联的其他Alert准备图时仍逐一核tenant和来源。没有在本轮对数据库、图、旧Run或模型做修改/复验。

## 5. 模型拿到什么，各套流程怎样使用

| 消费方 | 计划传入的有界内容 | 计划作用 / 保留的边界 |
| --- | --- | --- |
| Recon | 关联告警ID/事件时间、共享实体、原score、关系来源及缺口 | 整理更多候选线索；已有技术标签不当作本案发生事实 |
| Forensic | 同一材料＋原日志/增强等 | 区分已观察事件、候选关联和待核查路径；链排序不是攻击因果，图可达不是已横向移动 |
| Responder / Report | 前面实际采用的链/图摘要及原来源 | 解释进一步查哪个账号/主机、建议和报告依据；建议仍dry-run |
| Router专业Agent | 通过它们原本支持的bundle参数传入相同摘要 | 在原一次领域模型内参考上下文；不因此变成四步取证或新增工具循环，报告renderer也要展示材料来源/缺口 |
| Deep | 明确加入实际模型user/context消息，包含可继续查询的Alert/实体引用 | 模型据此选择既有日志工具验证关系；仅state/bundle/findings存有材料不算模型已消费 |
| Graph末端AttackPath | 本Run已有Case路径；未预取且条件满足时沿原调用 | 复用并保存Case图发现/提案；Alert-only邻居/影响范围分开保存，不套用Case路径阶段判断；缺Case或失败明确原因，不写成“已查明0关系” |

本批先做固定预查询和原工具消费，不新增任意Cypher/SQL给模型，也不增加一套链图推理Agent。不新增固定LLM步骤；Deep实际轮数仍由原工具循环、cap和预算决定，摘要增加的tokens如实计量。ContextBundle摘要白名单/序列化与现有LLM输入合同一起核对，不直接dump整个raw graph；被裁剪的部分在工件中说明，不能保证模型看过全部节点/边。

### 原算法含义不变

Case攻击链从同tenant全部告警找实体相交候选，不仅限于已关联Case的告警。MITRE是评分因素，不是单独入链条件。原window=24h实际按种子事件**前后各24小时**搜索；结果主要按关联分数排序，不是纯时间排序。保留原参数与算法并说明，不借本批暗改窗口/评分。

Case图主要表达Case→Alert→Host/User→IOC/Technique。它不是已经实现完整进程树、账户认证传播因果或真实横向移动还原；缺少上游日志的数据继续unknown。读图只返回节点/边也不能证明所有来源都已采集。

## 6. 输出在哪里取

沿现有API，不先建新查询平台：

- 当前Case链：`GET /api/v1/cases/{case_id}/attack-chain?window=24h`。
- 当前Case图：`GET /api/v1/graph/attack-path/{case_id}`。
- 自动Alert链：拟新增`GET /api/v1/alerts/{alert_id}/attack-chain?window=24h`，保原seed算法；现有`GET /api/v1/graph/neighbors/alert/{alert_id}`和`/graph/blast-radius/alert/{alert_id}`用于告警邻居/影响范围。不是无Case完整AttackPath。
- 本Run实际查了什么/采用了什么：`GET /api/v1/investigations/{run_id}/events`与`/explain?step=N`。
- 本Run当时的链/图结果：`GET /api/v1/investigations/{run_id}/artifacts`，再`/artifacts/{id}`。计划在现工件表增加链/图用途的kind与元数据，名称在实现时固定；不只留热内存、不以当前图重查询代替当时材料。
- Markdown：`GET /api/v1/cases/{case_id}/investigations/{run_id}/report.md`。

链/图工件至少关联tenant、Run、真实Case/seed Alert，保存查询窗口、选用来源/回退及错误、原有界节点边/链结果、模型实际可见摘要。关系指向原Alert/实体；关联评分不是恶意概率，不写成已确认攻击。

## 7. 最少功能验证与本地交付

复用原`test_attack_chain.py`、`test_attack_path_agent.py`及受影响bundle/Router/报告直接测试，仅补接缝必要断言，不跑全仓/长稳/恢复矩阵。

一个新Case样例包含三条共享账号/主机的告警（异常登录→PowerShell→异常外联），事件时间和实体显式填好。验证：

1. 原链能返回另外两条候选及共享实体；不把只有一个Case关联告警误判为“无法搜其他告警”。
2. 原图通过可信投影具有Case/Alert/Host/User等真实节点和有效关系，不接受只有Case/Alert回退图作为完整成功。
3. 同批用一个canonical Alert起点核薄入口和邻居/影响范围；无Case不能生成Case路径。一个不共享实体或范围外的控制告警不错误入链；一次跨tenant读取不返回本Case/Alert材料。只做必要身份/功能验证，不扩安全/故障矩阵。
4. 代表模型的实际可见输入包含链/图摘要；默认/Router/Deep的接缝先靠原直接测试验证，真实模型只选一个代表Case，不因三种编排重复跑一轮矩阵，不为模型输出写得漂亮重试。
5. 正常结果、成功0条、无Case、缺源/回退都能解释；所选Run事件、链/图工件和Markdown能读取并对应实际材料。

不重放上批失败/unknown Run，不全量回填旧数据，不改模型预算、自动关闭阈值或真实响应开关。连接恢复、全图性能、可用性/冗余及因果算法质量继续后置。结束做一次未参与实现者审计，保留本地版本，按阶段统一发布，不自动提交/推送Git。

## 8. 本次规划交付

本轮仅交付这份可实施设计，并同步现有OpenSpec proposal/design/spec场景与任务引用、总计划及PROGRESS；strict校验和一次独立规划审查不代表功能已经实现/开启。用户当前要求“规划”，不在本轮变更生产开关、写图或新增模型调用。

规划结束独审：未参与本计划编写的deep_functional_tests只读核源码/合同与规划，限定ACCEPT，无阻塞；确认Case/Alert分型、原算法、来源/缺口与待实施状态。strict校验、文档链接与diff格式检查通过。没有新增业务功能或运行验收，原任务5/15保持。
