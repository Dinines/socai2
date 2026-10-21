# 07 数据关系、测试证据与移植实施地图

> 用途：固定上游源码与历史证据分析（2026-10-20对齐）。数据关系、源码风险和既有测试可复用；旧目标合同/改造建议不作为当前强制实现。阶段与批次只引用当前路线。 当前职责见[范围](../operations/alert-processing-scope.md)，阶段退出见[路线](../operations/service-roadmap.md)，执行批次见[依赖计划](../operations/dependency-migration-plan.md)。

返回[总入口](README.md)。本章提供原版数据/测试分析和后续改造参考。当前按[服务端路线](../operations/service-roadmap.md)在限定范围内逐步移植与测试，再二次开发；涉及旧目标合同的差异不是首次移植强制重写清单。旧工程任务状态保持原事实。

## 1. 数据所有权与关联

| 数据/对象 | 参考落点 | 关键关系 | 历史对接建议（非本轮强制改造） |
| --- | --- | --- | --- |
| 来源事件与 finding | Alert 来源字段、raw_event、连接器、可选 lake | event ID、external finding ID、connector ID 各有用途 | 保留实际定位符、时间与引用，不能只存标题 |
| 告警 | PG `alerts` | canonical ID、tenant、dedup_hash、source_event_ids、Case 关联 | 改用目标身份/版本与不可变来源合同 |
| 关联摘要 | Redis IncidentSummary 及关联 key | tenant/实体/tactic → Incident ID | 不取代 stingAISOC PG membership 和历史 |
| Case | PG `aisoc_cases` 及相关协作表 | case ID/number、tenant、Alert links、owner | Case 与 Incident 分离；状态和调查执行分别记录 |
| 调查 Run | `investigation_runs` | tenant、case_id 字段、状态、输入、结果/报告和统计 | 不同参考路径会给 case_id 传不同目标含义，必须重新映射 |
| 调查步骤 | `investigation_events` | run_id、seq、kind、agent、hash、payload | 追加式记录；唯一 seq 不代表节点实际只运行一次 |
| 调查材料 | `investigation_artifacts` | run_id、artifact kind/body/引用 | 接入目标 Artifact、权限、内容 hash 和受控存储 |
| 调用成本 | `aisoc_run_costs` 及相关成本字段 | run、role/model、tokens、provenance | 聚合不替代每次真实调用；未知不当零 |
| 审批 | `agent_approvals` | tenant、Run/Case、action 与 dispatch | 绑定实际目标/参数、决策人、状态和执行结果 |
| 响应记录 | `aisoc_action_records` | action ID、tenant、status、approval_tier、JSON record | 数据库失败的降级与授权检查需明确 |
| Playbook pause | 对应 pause 表/迁移 | run、playbook/step、approval、tenant、resume | 保留暂停原因；不能冒充完整执行 checkpoint |
| 语义记忆 | PG memory 元数据 + Qdrant | tenant、item ID、来源、embedding 状态 | 原文/引用、版本和向量空间一致；未索引保持可见状态 |
| 情报投影 | Qdrant/OpenSearch/Neo4j、Feed 元信息 | IOC/actor、source、tenant/shared | 各 sink 状态独立，不能以一个计数证明全部一致 |
| 行为基线与异常 M13 | CORE Redis；独立 UEBA PG baseline/group/anomaly | tenant、实体、特征、样本、时间、来源 | 两种实现不混为同一权威；不可评分保持 unknown |
| 资产身份与暴露 M14 | 资产/漏洞库存、组织上下文和图投影 | tenant、稳定实体 ID、来源与关系 | 观测事实、业务归属、漏洞存在/被利用分别记录 |
| 规则与业务策略 M16/M18 | rule corpus、tenant overlay、business-context snapshot | rule/policy/version、作者、原因 | 管理保存与运行生效分别证明 |
| 反馈改进 M19 | override、经验、tuning proposal、eval | 原结果、人工理由、样本/版本 | 不改原判断事实，不自动把提案视为已发布 |

迁移入口：[008 investigation ledger](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/migrations/008_investigation_ledger.sql)、[055 action records](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/migrations/055_action_records.sql)、[063 cost provenance](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/migrations/063_cost_provenance.sql)、[081 playbook pauses](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/migrations/081_playbook_pauses.sql)、[083 one case table](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/migrations/083_one_case_table.sql)、[105 semantic memory](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/migrations/105_semantic_memory.sql)。这些只是相关入口，不是完整迁移依赖清单；不得挑几张表直接在现有库执行。

## 2. 旧目标合同的身份与状态差异（后续对接参考）

本节用于将来明确决定接回旧目标系统时的差异核对；独立原版移植先保留上游合同并实测，不据此提前替换消息、状态和存储。

| 边界 | 参考方式 | stingAISOC 对接时的处理 |
| --- | --- | --- |
| Kafka 投递身份 | 参考 envelope 和 canonical Alert ID | 用已有 event_id；重复投递不新增业务副作用 |
| 业务版本 | 参考自动 Run 按 Alert ID + workflow version 固定 | 按 tenant+Alert ID+业务版本处理；不能忽略新版本 |
| duplicate | Fusion decision 与 sink duplicate | 目标 `business_changed=false` 不自动新调查/建案 |
| Run 目标 | incident_id/case_id 在不同路径可能承载不同标识 | 显式 target_type/id/version，禁止混同对象 |
| 状态 | Fusion 枚举、API 字符串、graph、Investigator、Case 各有词汇 | 分别建映射，不能共用一个万能 status |
| 持久结果 | 原状态字典、账本行、报告与缓存 | 冻结 Result 不改写；工作台读取可回链 |
| 超时与重试 | 各模块的 SDK/业务有限重试、fail-soft | 已发送结果未知不自动重发；实际重试单独 Call ID |

若未来决定对接旧系统，再按[其 Fusion 下游说明](/Users/lychee/Documents/project/SOCAI/docs/fusion/fused-alert-consumer-migration.md)制定专门变更；当前不做该对接，也不为它先建设双轨兼容系统。

## 3. 20 上已有实测：只证明相应范围

证据来源为[部署说明](../../deploy/aisoc20/README.md)及服务器 `/home/lychee/beenuar/deployment/`。下列运行事实来自此前保存的记录，本次文档任务未再次调用模型或重跑链路。

### E01：接入到 Fusion 告警读取

- **输入：** 明确标记的 golden pipeline 合成事件，run `5c3757a85756`，Office 启动可疑 PowerShell 场景；接入 accepted=1、rejected=0，未授权请求 401。
- **中间：** 经过 Kafka/Fusion，告警 ID `b6f8d542-a461-5b03-b515-6da94297b205` 持久化；来源和描述进入 Alert。
- **最终：** API 可读，severity=`high`、source=`CrowdStrike Falcon`，脚本 10/10 检查通过；证据 `golden-pipeline.log`。
- **限制：** 合成事件，未证明该告警已完成自动分诊、Case 调查、响应或结案；未补充完整 offset/故障语义实验。

### E02：对话模型连通

- **输入：** 一次 `aisoc-triage` 网关 smoke，路由至 43 的 `aisoc-test-investigation`。
- **中间：** 实际模型响应约 1.409 秒，usage 输入 19、输出 2、合计 21 tokens，费用 unknown。
- **最终：** 返回 `READY`；记录 `model-smoke.json`。
- **限制：** 是连通性，不是分诊分类、结构化报告、全部角色或质量评测；43 当前是 OpenAI-compatible vLLM 服务。

### E03：嵌入与三个存储/检索路径

- **输入：** 20 的 `qwen3-embedding:0.6b`；内置 ATT&CK、原 CISA KEV 和显式合成 memory note。
- **中间：** 生成原生 1,024 维非零向量；模型指纹、调用 hash/耗时和错误有记录。情报新旧 1,748 个 point ID 和 payload 对比保持一致。
- **最终：** ATT&CK 函数检索有结果；TI 语义检索返回 tenant/shared 范围的 CISA 条目；memory 经真实 HTTP 写入→召回→删除/清理，PG 与新向量集合均回到 0。
- **限制：** ATT&CK 仅 14 项，actor 0；TI 未宣称精确 CVE 命中；未证明调查 Agent 消费了检索结果或 RAG 质量通过。

原件：`embedding/native-smoke.json`、`data-sources.json`、`agents-retrieval.json`、`threatintel-retrieval.json`、`memory-smoke.json`、`final-state.json`；首次失败记录另存，没有抹去。相关本地三个合同检查通过，见 [test_embeddings.py](../../deploy/aisoc20/embedding/test_embeddings.py)。

### E04：基础服务与认证

16 个运行服务；有健康检查者 healthy；控制台 health 200、非 demo、版本 19.0.0，登录与 auth/me 通过。只证明部署与认证 smoke，不证明 WebSocket 分发、真实连接器、full profile 或完整业务闭环。

## 4. 测试源码、测试通过和业务验收分开

| 层级 | 合适的验证 | 不能冒充 |
| --- | --- | --- |
| 单元/替身 | 字段映射、解析、纯规则、调用次数、预算与错误分支 | 真实数据库事务、厂商能力、模型质量 |
| PG 集成 | 行与关系、约束、租户、冻结/提交 | Kafka offset 和真实工具执行 |
| Kafka/进程 | 消费就绪、消息坐标、落库/commit 顺序、发布和 API 读取 | 调查分析质量或真实设备状态 |
| 真模型 smoke | 路由、实际输入输出、usage、schema 接受 | 完整分类准确率、复杂分析能力 |
| 真工具/厂商 | 请求参数、回执、来源结果、效果 probe | 所有厂商/全部故障覆盖 |
| 固定质量集 | 检索相关性、支持/反证、未知与结论质量 | 单个成功样例或关键词自一致性 |

本次只审阅测试入口和部分代表性断言，未运行上游整套测试，未验证其 CI 当前是否全绿。文件清单见 [08](08-source-index.md)。

## 5. 面向移植的最小验收卡

这些是可选取的后续卡，不要求一次跑完整矩阵。每批只选正常路径和直接相关关键边界。

| 卡 | 输入 | 中间产品 | 最终判据 |
| --- | --- | --- | --- |
| T01 输入边界 | 一条合法事件、一条坏 schema、冲突 tenant | validation/拒绝记录、来源坐标 | 合法进入；非法不产生错误归属的 Alert |
| T02 真实发生与重投 | 同投递重发；同指纹但真实新发生 | event/Alert/version/membership | 重投无新副作用，新发生不被永久吞掉 |
| T03 Fusion 到调查受理 | created、updated、duplicate | PG Inbox/Decision/Command、Kafka offset | 事务持久后确认；duplicate 不凭空新建 Run |
| T04 自动分诊 | 恶意、授权扫描、误报各一例，模型可替身 | 发送输入、parsed verdict、依据和 tier | 分类语义正确；合法触发不当误报；恶意不误关 |
| T05 一个只读调查 | 显式目标和问题、有限日志 | 实际工具参数、原材料、Evidence/引用、模型输入 | 结论能回链；不只生成计划；无证据表达 unknown |
| T06 知识检索 | 固定文章和版本、一个查询 | chunk hash、embedding 指纹、过滤和 citation | 命中相关片段；私有资料不串 tenant；失败不伪装无命中 |
| T07 调查交付 | 同一 Run 的完整步骤 | PG Result、Artifact、文件投影、事件 | API/文件/事件引用同一冻结结果，不拼接多个 Run 的局部成功 |
| T08 审批/dry-run | 提案、参数、审批人与请求人 | policy、approval、dispatch 和 executor 调用计数 | 未批准不写厂商；dry-run 无真实写；不自批越权 |
| T09 一种真实动作 | 受控测试目标及批准请求 | operation ID、回执、read-back | 按目标状态判效果；超时 unknown 不自动重发 |
| T10 Case 结案 | 调查结论、残余风险、处置结果 | 状态、分析员、证据、closure 记录 | Case 与 Run 状态分离；未解问题保留；反馈可追溯 |
| T11 实时交付 | 两租户客户端、同一 Run 进度 | 认证票据、tenant 路由、持久状态 | 只收到本租户；页面完成状态可与权威库核对 |

本次独立 AiSOC 移植优先核对 20 的既有环境，使用隔离测试数据和来源明确的样本，凭据不出日志；不自动改动 21 的旧建设服务。上述卡中专属 stingAISOC 身份/Outbox 的项目，只有后续决定改造或对接时才执行，不能用于要求原版在初次移植时先换架构。

## 6. 源码风险与待核清单

下表是有界静态分析结论；不是完整安全审计。影响及最小处理围绕实际移植，不默认建设通用可靠性框架。

| ID | 结论与性质 | 业务影响/条件 | 历史修正建议与定向验证参考 |
| --- | --- | --- | --- |
| R01 | **源码事实：** Fusion 指纹和 canonical ID 不含发生时间，sink 按 tenant+dedup_hash 去重 | 不同时刻同指纹可能落同 Alert；TTL 不自动解决 | 采用现有真实发生身份/版本；T02 |
| R02 | **源码事实：** Fusion fail-soft 持久化与 Kafka 发布分离 | 下游收到消息不代表行存在；故障可能丢失关联写入 | 采用目标 PG/Outbox；T03 |
| R03 | **源码事实：** 自动分诊 DLQ 异常被吞、循环可继续确认 | DLQ 不可用时可能越过未可靠处置消息 | 使用现有持久拒绝和连续确认机制；定向失败验证 |
| R04 | **静态语义风险：** 增强 error dict 非空，被 Recon success/cache 与 Forensic 部分可用判断接受 | 只有错误仍可能被误作存在增强材料；未真实复现 | 统一成功状态与观测列表；一条错误替身验证 |
| R05 | **源码事实：** Case API 有材料截断/最多三条告警 | 调查材料不覆盖整个 Case | 保留完整引用和实际模型视图/截断，T05/T07 |
| R06 | **源码事实：** Actions 有 PG，但保存失败会降级；读取 tenant 参数可省 | 无库时执行记录可能仅本进程；部分调用作用域需核 | 必要记录失败阻止发送、从身份绑定 tenant；T08 |
| R07 | **源码事实：** ledger 无 DSN 可 no-op，运行缓存另存 | 界面完成不等于持久证据完整 | 复用目标账本与冻结，ready/读取按实际合同；T07 |
| R08 | **源码事实：** max_tool_calls 检查比较模型 calls_made，缺 tracker 放行 | 配置名不等于严格工具预算 | 按真实调用类型计数，定向预算边界 |
| R09 | **已测部署差异：** 原 embedding 空间/SDK 与 20 不匹配，已加部署 overlay | 只记录源码 revision 不能复现容器行为 | 固定源 hash、补丁与新集合；E03；不泛化全部兼容 |
| R10 | **源码事实：** ATT&CK 语义函数在 agents/app 未见内部调用 | 索引可检索不等于调查已用 | 选一个实际消费入口，记录检索结果进入模型的证据 |
| R11 | **待核：** 多套编排、状态和路由覆盖存在差异 | 测试了一个入口却宣称全平台可用 | 先选主入口，其他路径逐项保留未验 |
| R12 | **源码事实：** 回读只在部分 live 成功动作且策略要求时执行 | succeeded 不总等于 verified；legacy 不能据此背书 | 展示 execution 与 verification 两种事实；T09 |
| R13 | **源码事实：** Feed Bloom 先去重、多 sink 各自 best-effort | 部分 sink 写失败后的再次投递/补齐待核 | 本期明确缺失状态，必要时定向补齐；不默认做全局恢复 |
| R14 | **证据缺口：** 源码九个角色，部署原记录七个别名且仅 triage smoke | 新启用 Hunt/Detection 等可能缺路由 | 启用前核实际配置并做一个有界调用，不推断全部通过 |
| R15 | **源码事实：** 独立 UEBA 为累计 Welford，window_days 不直接实现淘汰重算 | 不能宣称严格最近 30 天分布 | 明确统计语义；按本期需要决定是否修改，先验 count/mean |
| R16 | **静态语义风险：** peer 的 member_count 是观测数，裸 group ID 是主键 | 群体规模可能被误解；同名跨租户写入冲突待复现 | 不按名字解释人数；用两个合成 tenant 定向验证 |

定位细节见 02—06 和 [08](08-source-index.md)。不要因为这里列出问题就改动只读参考目录。

## 7. 当前移植顺序

职责、阶段、批次和完成状态分别在[范围](../operations/alert-processing-scope.md)、[服务端路线](../operations/service-roadmap.md)、[依赖计划](../operations/dependency-migration-plan.md)和[PROGRESS](../../PROGRESS.md)维护。本章不另立全量任务树。

当前仅完成1A依赖参考快照的静态校验；下一单项仍是1B的独立PG/Redis及初始化输入验收。后续只迁告警及后续处理服务端所需代码和依赖，不以完整上游、采集检测、UEBA生产或前端验收为条件。不续旧SOCAI Basic/OpenSpec任务。

## 8. 修改前后的检查单

开始：固定参考 revision，核对 source-snapshot；选择本迁移阶段的真实入口；列输入、产物、失败和验收；核直接调用者/被调用者及当前移植副本。

结束：记录实际迁入、适配和修复项；更新阶段证据、模块文档和已知问题；报告测试层级与依赖缺失；保留历史记录与首次失败；核对未提交差异。业务二次开发再落入明确范围的变更，不自动续用旧工程任务。

上游仓库含 [LICENSE](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/LICENSE)。复制实质代码时记录来源 revision、文件和修改，保留所需来源/许可信息；第三方 SDK、语料和模型分别核对其自身来源，不把仓库许可当所有外部资产的统一声明。

## 9. 文档维护方法

更新参考源码需先明确新版本并比较 [source-snapshot.json](../source-snapshot.json)，按变更文件定位入口和直接上下游，再更新受影响章节、测试入口与快照。文件 hash 相同只证明字节未变，不证明结论或运行有效。

本次没有同步/归档 OpenSpec、勾业务 tasks、修改参考代码或提交推送；也没有将本参考分析列为 stingAISOC 业务验收。

## 10. 初版模块分析的文档核验结果（新增路线图前）

2026-10-20：M00—M21 共 22 个总览条目各有唯一专题/边界锚点；13 份 Markdown 的 408 个本地文件与锚点引用检查通过，199 个参考文件 hash 与快照一致，66 个具名测试文件均在相关服务测试目录找到。索引提取 170 条路由声明；这是定位清单，不是 170 条接口的运行验收。

参考工作区保持 clean，`git diff --check` 通过。本轮没有执行上游业务测试集、真实模型/工具调用或部署；本文明确保留的运行与质量缺口没有因此消失。
