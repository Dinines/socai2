# 告警处理服务端：先依赖，按批次迁移

**2026-10-21追加：** 按用户要求补迁原版services/enrichment、services/threatintel、services/ueba完整源码/构建/测试及直接资源；原API/Fusion/Agents历史、图和事件查询保留。依原设计补可运行必需接线，复用21既有存储；旧依赖快照不代替本次源码，实际结果见[full配套回执](full-support-migration.md)。


2026-10-20。目标为**告警及后续数据处理服务端**，输入已有告警，交付API、消息和持久化结果。职责见[模块范围](alert-processing-scope.md)，阶段目标与退出标准见[当前路线](service-roadmap.md)，实际完成状态见[PROGRESS](../../PROGRESS.md)。本文只维护第一阶段批次输入与验收，不要求迁完整仓或控制台。

用户确认：从 `/Users/lychee/Documents/project/SOCAI/opensource/AiSOC` 参考源码直接复制相关文件，逐步迁入；必要删除、修改先讨论。参考目录只读，revision固定为 `34ca18c57dd4175539e5c6dd3d04a72dc057306b`。不引入旧SOCAI业务实现或旧任务状态。

已有分析复用用户指出的 [docs/anal](../anal/README.md)及交接版 `docs/reference/aisoc`；保留两份分析，不重复制作。其全量模块描述用于查源码，当前迁入范围按本服务职责筛选。旧相对源码/历史工程路径不作为文件已迁入的证明，实际复制按固定本地参考核对。

## 依赖迁入的顺序与完成条件

每批先写清输入、资源归属、实际调用及最终判据，再执行该批。当前1A完成的是此前90文件依赖参考快照的静态校验；其中含前端、采集等范围外依赖，不作为安装清单。阶段一结束要求范围内服务及其构建输入齐全，不要求整仓全量迁移。1B已复用21现有PG/Redis并完成直接验收，见[1B回执](1b-shared-services.md)；1F API/Fusion主链已验，1G受控Agents/Actions服务基线已验，见[回执](1g-service-baseline.md)，完整服务端尚未冻结。

| 批次 | 迁入内容与前置 | 直接验收 | 当前状态 |
| --- | --- | --- | --- |
| 1A 依赖基线 | 已存依赖声明/锁、构建配方、许可、20/21盘点；按当前服务范围选用 | 90原件来源/hash/权限一致；13服务导出及上游自测仅为参考快照验收，不等于全部需安装 | 参考快照已校验，未安装 |
| 1B PG/Redis | 复用21公开服务；新aisoc库、owner/runtime角色及Redis专用账号/逻辑库；迁入完整SQL链 | 134/134 SQL成功；真实角色/tenant读写、Redis账号及数据重启恢复；见[回执](1b-shared-services.md) | **完成（基础设施层）** |
| 1C Kafka | 已复用21:9092 Kafka7.5.0 KRaft；项目专用topic与group映射 | 原锁aiokafka消息坐标/hash、提交位置与单broker重启恢复通过；见[回执](1c-shared-kafka.md) | **完成（基础设施层）** |
| 1F 告警受理/Fusion/API | 迁入API、Fusion及其直接源码/SQL/共享文件/测试；核传输、身份、任务开关及RawAlert合同，不引入整套ingest/采集 | 带tenant/来源标记的已有告警→真实Kafka/Fusion→PG/API结果；非法输入、重投及来源关系可查；源码/镜像对应 | 主链及已列边界已验；保留原归并限制 |
| 1D 向量/嵌入 | 优先复用21 Qdrant，核版本/SDK及nofile65536；核21可达的同模型/维度embedding方案 | 21实际容器请求→非零有限1024维向量→独立测试集合写查；区分SDK兼容和检索质量；仅清理本批对象 | **完成（结构/存取/恢复）**；见[1D回执](1d-vector-embedding.md) |
| 1E 模型网关 | 原LiteLLM配方及独立凭据，接43现有服务；固定镜像ID/digest；配置范围内角色 | 21服务容器→实际角色路由→有限结构输出与usage；逐一记录启用角色，不能从一个smoke外推 | **完成（五角色路由/结构）**；见[1E回执](1e-model-gateway.md) |
| 1G 分诊调查/响应服务 | 迁入Agents、Actions及按需知识/TI/上下文适配；补齐范围内认证、Case、账本、审批、报告的数据接口和构建输入 | 通过服务端API/消息检查状态、Run/证据/结果关系；范围内代码/依赖齐全；不验前端或控制台 | **受控基线已验；审批/知识消费到后续批次** |

### 实际执行顺序

批次编号保留已有记录，执行按真实依赖安排：**1B → 1C → 1F → 1D → 1E → 1G**。先用已有告警跑通非模型数据链，再增加知识/模型和调查服务；不要求所有依赖同时完成后才发现主链问题。

```text
1A参考清单
  └─1B PG/Redis─1C Kafka─1F 告警→Fusion→PG/API
                             ├─1D Qdrant/embedding
                             └─1E 模型网关
                                  └─1G Agents/Actions及所需知识接线
```

1D和1E均在1G前完成；它们可以独立核对，但默认逐批执行。每批通过后更新PROGRESS及证据，再进入下一批，不重复整仓回归。

### 计划中的源码与部署落点

只读来源固定为本地AiSOC revision；[迁移来源清单](../handoff/migration-source-map.json)记录计划迁入的根目录、关键文件、134份SQL的完整文件名和hash。该清单是计划，不是已迁入清单。

| 内容 | 计划落点 | 保留原则 |
| --- | --- | --- |
| API/Fusion/Agents/Actions服务 | 仓库 `services/<service>/` | 先复制所选Python服务完整构建上下文及直接测试，保留内部共享模块；范围外路由/任务不因文件存在而自动开放 |
| 必要TI服务 | 按实际检索路径选择 `services/threatintel/` | 只有使用该服务才构建；不以所有Feed、图/搜索sink为前置 |
| PG初始化与SQL | `infra/postgres/initdb/`、`services/api/migrations/` | 原SQL链保留；执行顺序按完整文件名，不删同编号文件或只看最大编号 |
| 21编排与角色路由 | `deploy/aisoc21/shared_1b.py`、后续`compose.services.yml`及模型配置 | PG/Redis复用共享实例；业务编排待建，不直接执行参考全量Compose；显式连接、项目资源及开关 |
| 新部署凭据 | 本地Git忽略目录；21拟用 `/opt/sting-aisoc-socai2/private/` | 新生成、目录0700/文件0600；不覆盖20/21参考快照，不进入镜像或公开config输出 |
| 新部署源码/证据 | 21拟用 `/opt/sting-aisoc-socai2/source/`、`evidence/<batch-id>/` | 执行前核路径未被占用；记录源码/镜像/overlay及批次标记，凭据和原始敏感材料不入公开证据 |

复制前检查目标冲突、受控文件和构建输入；复制后逐文件记来源/hash/修改原因。上游原件与必要补丁分别保留。仅“复制目录”不算本批通过，必须完成下列直接验收。

### 1B执行卡：复用21 PG/Redis（已完成）

**输入与前置：** 用户确认可使用21公开数据服务、可以适当重启。执行前核端口、目录、账号、库与逻辑库占用；不启动业务进程。固定源码迁入2个initdb脚本、134份SQL及LICENSE，137个原件保持字节一致。

**实际检查：**

1. 复用`spirithub-postgres-1`的PG16.15，经21:5432接入；新建`aisoc`数据库及`aisoc`/`aisoc_app`两角色，均非superuser/非BYPASSRLS。不更改旧库和旧角色。
2. 按完整文件名执行134份SQL，原文件hash、逐文件成功收据、ledger完整集合对应；仅061的集群角色属性块由基础设施管理员执行，其余schema/default grants归新owner。不能只看healthy或最大编号。
3. 两个标记tenant的runtime绑定读写、跨tenant写拒绝、DDL拒绝及新TCP连接回读通过。未绑定tenant会读到两租户，这是上游worker语义；API身份/tenant绑定仍为1F验收。
4. 复用21:6379 Redis7.4.11，账号`socai2`、逻辑库8—12分配给API/Fusion/Agents/Actions/TI。ACL拒绝FLUSHALL/FLUSHDB/CONFIG/SHUTDOWN；逻辑库分配不构成ACL安全隔离。
5. 保存现有全部ACL并增加`--aclfile /data/socai2-users.acl`；只重建Redis容器，原镜像/卷不变。原default及新账号、标记key重启后恢复；仅删除本批测试key/行。PG未重启，持久提交通过WAL及新TCP会话回读核验。

**凭据差异：** 原`20_runtime_role_password.sh`会将`SELECT set_config(...)`的密码值输出。原件保留，部署生成副本用静默psql及`\getenv`读取环境变量，避免密码出现在输出和psql参数。非敏感哨兵原版→补丁→原版负对照及补丁真实凭据检查通过。

**交付/通过：** [来源清单](../handoff/1b-import-manifest.json)、[补丁记录](../../deploy/aisoc21/postgres-init-patch.json)、[实际证据](1b-shared-services.md)齐备。API迁移ledger已记134文件，但1F仍需核真实API严格模式和启动行为；当前没有业务服务部署。

**恢复：** 共享实例禁止`down -v`、清库或回滚旧业务数据；本批专属库和凭据保留现场。Redis变更前Compose/ACL在21私有目录备份；恢复配置时必须保留项目ACL文件及用户，避免恢复旧命令后账号丢失。不以反向SQL还原共享实例。

### 1C执行卡：复用21 Kafka（已完成）

**输入：** 1B通过；优先使用21:9092既有Kafka，核真实版本、集群ID、listener可达性、持久化及当前消费者。上游Kafka/ZooKeeper7.5.0只作来源参考，不为版本一致而重复部署或替换现有broker；兼容差异留证。

**链路与通过：** 使用项目专用topic/group及批次标记消息→producer返回partition/offset→consumer读取相同payload/hash；准备告警raw/fused/DLQ名称与配置映射，不能让新消费者误读旧topic。必要时按已授权范围单独重启服务并核恢复，不默认重启整套基础设施。业务入口仍以1F认证接口为准，现有broker无认证不能当业务身份边界。

**实际结果：** 21现有cp-kafka7.5.0采用KRaft，保留原实例/卷，无新增ZooKeeper。原锁aiokafka0.10.0在缓存Python3.12容器中经21:9092真实投递与消费，offset0/1→只提交1→单broker重启→续读offset1→新写读offset2→独立回放0/1/2通过。53个旧用户topic起止offset保持，测试topic/group已清理；项目3个业务topic保留为空。来源、真实坐标和配置映射见[1C回执](1c-shared-kafka.md)及[资源映射](../../deploy/aisoc21/kafka-resources.json)。实际服务Python3.11构建到1F验证，不将基础设施探针视为完整业务通过。

**启动边界：** 原生产/staging明文拒绝保持，未设置豁免；现有broker无认证、RF1，不当外部身份边界或高可用证据。1F启用业务进程前必须明确传输配置。Agents默认组名未从环境读取，1G需显式传入项目group_id；不因写入映射文件就宣称已经接线。

**恢复：** 只暂停本项目producer/consumer，保留topic、消息坐标及cluster ID；不停止共享broker作为日常项目回退，不清空既有topic。仅清理明确归属本批的测试对象。

### 1F执行卡：第一条告警数据链（主链已验）

**输入：** 1B/1C基础设施层通过；迁入API、Fusion完整构建上下文、原测试和SQL。先核1C的明文/生产启动边界，保留原生产拒绝保护；明确传输方案后再启业务。先准备范围内启动配置，再构建两个源码镜像，记录固定revision、文件hash、镜像ID/digest和适配差异。

**受理方案：** 首版以 `RawAlert` 为内部合同，API已增加仅接收已有告警的薄适配：认证主体确定tenant → 校验/必要字段映射 → 投递项目raw topic → 返回受理ID/来源引用；不做厂商轮询、日志解析或原始事件检测。HTTP受理成功只表示已接收/发布，最终状态另由查询/消息取得。接口已定稿并实现为`POST /api/v1/alert-ingress`，请求/回执及验收范围见[合同](1f-alert-ingress-contract.md)。

原 `POST /api/v1/alerts/submit` 明确绕过Kafka/Fusion直写库，**不作为主链通过的替代入口**。1F可先用内部受控producer定向定位Fusion，但对外受理验收仍需上述认证/授权合同；不能只用脚本直投Kafka就宣称外部接入完成。

**配置与直接验收：**

- API正常运行迁移器时显式要求迁移与严格模式；原脚本只有 `AISOC_MIGRATIONS_STRICT=1` 才在SQL失败时退出失败。核全部文件状态及实际schema，不以sentinel、HTTP200或最大编号判断。
- Fusion先关闭原始事件提升、单事件/窗口检测和lake writer；保留告警sink、去重关联及范围内风险。实际检查消费者订阅集合，只允许项目raw告警及明确选用的上下文信号，不消费普通事件检测流。
- 一条标记告警→HTTP受理/消息坐标→Fusion决策→PG行及来源→读取API，逐段对应。保存每段ID、时间和最终值；同投递重发、真实不同发生、坏schema、未授权/跨tenant各做直接边界。
- 基线不启动Agents/Actions，避免最小数据链测试触发模型或响应。外部增强未接时记录partial/不可用，不伪造无威胁或增强成功。

**实际结果：** [1F回执](1f-alert-chain.md)含两镜像/原锁依赖核验、134文件严格迁移检查、14次真实HTTP检查与70项相关测试。新服务使用production、非root、只读文件系统；仅loopback18000/18003，Kafka19093 SSL及PG verify-full。不同发生按原指纹折叠，新增来源保留，不能宣称独立发生语义通过；2A继续核对。未知版本DLQ的tenant/source未解析，以broker坐标回查；首次验收脚本假设已纠正并保留失败回执。

**恢复：** 停受理入口及本项目消费者，保留topic/offset与已写行；回退到上一固定源码镜像和配置。数据语义错误先保留失败告警/决策，不清库、改原证据或盲目重放消息。

### 1D执行卡：向量与embedding（结构/存取已验）

**输入：** 1B/1C通过，优先在1F后执行；优先复用21现有Qdrant并选择独立集合，核兼容性及卷归属，复现20的Ollama0.40.6/qwen3-embedding:0.6b指纹、原生1024维和CPU运行事实。20的loopback地址不作为21服务地址。

**链路与通过：** 21实际调用三条有标记文本→有限非零1024维向量→测试集合写入/读取/查询→相同ID/payload可查；核Qdrant实际进程nofile。生成embedding适配前仍核固定源hash，兼容改动另记。只证明结构/存取连通，调查实际消费在第三阶段验收。

**恢复：** 停新依赖或恢复前一镜像/模型配置；保留模型和集合指纹，不向不同模型空间混写；仅清理明确记录的本批point/集合。

**实际结果：** [1D回执](1d-vector-embedding.md)记录21独立Ollama0.40.6/qwen0.6b、16核/32GiB、3条有限非零1024维向量、独立集合写查及Qdrant定向重建后的恢复；实际进程nofile65536。仅清理本批集合，其余31已有容器与18卷名保持；SDK兼容和业务检索消费未验。

### 1E执行卡：角色模型路由（五角色路由/结构已验）

**输入：** 43现有服务地址/模型与受控凭据，21独立LiteLLM配置；部署前固定实际镜像digest，不用浮动标签表示可复现版本。

**链路与通过：** 在21服务容器中对即将启用的角色做有界调用，保存路由、模型、schema响应、耗时和真实usage；费用无来源时记unknown。未启用的角色标明未测，不为copilot/前端等范围外功能扩大调用矩阵。不改43服务或自动切换外部付费模型。

**恢复：** 停新网关/恢复前一路由，不重发已完成业务调用；保留失败样例、模型/配置指纹和实际usage。

**实际结果：** 21固定LiteLLM1.106.0、loopback14000，triage/recon/investigation/summary/report五别名各一次真实43调用；JSON对象及字段/值通过，deployment header与实际43路由对应，共616 tokens，费用unknown。重试0/fallback空；错误key原版400/no_db_connection保留。其余33已有容器/18卷名保持，API/Fusion配置未接模型，工具/调查消费未验，见[1E回执](1e-model-gateway.md)。

### 1G执行卡：调查与响应服务基线

已执行受控人工调查/API持久交付及Actions dry-run，见[1G回执](1g-service-baseline.md)；完整审批和知识消费按后续阶段。已有知识及本地4B候选允许复用和20/21分担，见[计划](knowledge-data-reuse-plan.md)。

**输入：** 1D/1E及1F通过；迁入Agents/Actions及所选知识路径的直接输入。先构建、检查import与依赖，再分别启动。

**子步：** 先启动Agents的人工只读调查入口，显式关闭Kafka自动分诊/自动升级和记忆自动写回，核启动时知识索引/默认剧本/后台任务的实际副作用；随后启动Actions内部服务并保持真实写动作关闭。第三阶段再逐批启用自动分诊、检索消费和记忆，第四阶段再验剧本/审批/执行。

**通过：** 人工只读调用有可回查Run/状态/实际工具模型记录；Case/账本/报告数据接口可读；Actions未授权请求拒绝，dry-run不发真实厂商写调用。Realtime目标缺失只能影响非必要推送，不得导致Run持久化、状态查询或报告丢失。服务入口的基本授权在此核对，完整审批及效果验证仍在第四阶段。

**恢复：** 暂停本项目新Run受理和相关worker，保留已受理Run及账本；恢复前一镜像/配置，不将queued/running或动作unknown直接改成成功，也不重发副作用操作。

### 启动配置核对表（API/Fusion已在1F生效，其余待对应批次）

| 对象 | 首次基线计划 | 源码依据/实施要求 |
| --- | --- | --- |
| API迁移 | `AISOC_MIGRATIONS_REQUIRED=1`、`AISOC_MIGRATIONS_STRICT=1` | `app/scripts/run_migrations.py`；initdb和API runner的结果分别检查 |
| Fusion事件支路 | `AISOC_EVENT_PROMOTION_ENABLED=false`、`AISOC_DETECTION_ENGINE_ENABLED=false`、`AISOC_WINDOWED_DETECTION_ENABLED=false`、`AISOC_LAKE_WRITER_ENABLED=false`、`AISOC_UEBA_FUSION_ENABLED=false` | 首条链尚未接外部UEBA，先禁其订阅；后续2C按外部合同启用。`app/core/config.py`及worker订阅条件；不是仅删除Compose服务名 |
| API范围外定时任务 | OAuth、digest、hunt/retro-hunt、report、phishing、retention、webhook及shadow/autonomy/approval-expiry/war-room按当前批次关闭 | 使用真实源码配置名；审批到期等范围内任务到相应批次启用，其他lifespan任务逐个核查，不虚构总开关 |
| Agents初始启动 | `AISOC_AGENT_KAFKA_DISABLE=1`、`AISOC_AGENT_ESCALATE_TO_GRAPH=0`、`AISOC_AGENT_MEMORY_SUPPRESSION=0`、`AISOC_AGENT_MEMORY_WRITEBACK=0` | 第一阶段人工只读入口；3A/3C再有界启用并验证实际消费 |
| Actions/授权 | 非demo/非dev、独立服务token；真实写动作默认关闭 | 对两类Actions入口分别核策略及principal传递，不用一个开关推断所有路径安全 |
| UI/Realtime/采集 | 不部署，不构建Node/ingest | 核API/Agents内相关调用是否可降级；必要最小适配保留来源与失败回执 |

API/Fusion实际设置见1F回执；Agents/Actions受控设置和实测见[1G回执](1g-service-baseline.md)。这里只列已核源码或明确待检查的控制项。缺少必要开关、授权绑定或真实ready检查时，作为对应批次的最小适配/阻塞项解决，不通过删测试、伪造healthy或全量重写规避。

### 每批证据与推进条件

每个批次使用唯一batch ID和可识别测试tenant/告警/Case/Run，至少保存：输入来源及hash → 实际请求/消息坐标/中间行 → 最终值和ID关系；并记录源码/镜像/overlay指纹、执行命令、环境层级、测试结果、失败样例、清理范围、恢复方法和已知限制。日志/公开收据不含真实密钥或隐藏推理。

采用原测试中的直接相关节点，加本批正常路径及关键边界；替身与真实PG/Kafka/模型/厂商证据分开。任何主链缺口、越权或凭据泄漏阻止该批记通过；外部可选上下文缺失可以明确partial，不自动让整批假成功。通过后推进下一依赖批，不能将“计划已写好”或“复制已完成”记为运行验收。

首次部署的恢复是停新项目并保留现场；有业务数据后，数据库升级前先做本项目备份及受控恢复验证。应用镜像回退不等于数据库schema可反向回退；涉及不兼容schema时用并行新卷/明确的本项目恢复方案，不对旧共享库做反向SQL。

1B的SQL用于全新独立数据库；保留上游完整初始化链作为共享依赖，不为缩小职责而盲目删表/挑表。1B已以共享库执行器核对完整输入和副作用，首启原脚本保留为来源。1F/1G按实际构建需要保留共享文件，范围外代码被导入不代表其业务被启用。启动Agents/Actions前核自动升级、调度、响应开关和基础授权，限制在测试范围；不部署Connectors采集服务。

完成1B—1G后，按当前范围进入告警归并/风险/上下文、调查、响应反馈、服务端整链冻结及二次开发。已有UEBA/资产/漏洞/历史日志由外部提供，本服务验证读取和实际消费；不建设其采集/检测生产系统。ClickHouse/Neo4j/OpenSearch只有在实际只读工具或知识路径需要时才列依赖，不以启用full/extras为目标。

## 21资源映射

只读盘点见[21快照](initialization-host21.json)。现有两个Compose项目为 `sting-infra21` 和 `spirithub`；30容器中22运行、8退出，18个卷。4个旧业务容器仍为停止。以上为1A历史盘点；后续1B重建Redis、1C重启Kafka，分别留有前后元数据回执，不以旧关闭回执推断当前启动时间未变。

用户已确认优先复用21公开数据服务，并允许必要时适当重启。按数据库/角色、topic/group、集合和测试标签隔离项目对象，保留既有实例、卷与旧业务数据；逻辑分配与安全隔离分别记录。项目目录`/opt/sting-aisoc-socai2`已创建，1F已新增socai2项目、API/Fusion两个容器及私有网络，无新增数据卷。共享服务重启先核影响及备份，只处理所需单服务，并保存恢复证据。

| 依赖 | 21已有资源/占用 | 新项目处理 |
| --- | --- | --- |
| PostgreSQL | `192.168.1.21:5432`由旧shared-access发布，其他项目PG及旧数据仍在 | 已复用PG16.15及aisoc库/两角色；1F重载启TLS无重启，新服务经5432 verify-full接入 |
| Redis | `sting-infra21`发布21:6379，保留旧状态 | 已复用Redis7.4.11；专用账号、逻辑库8—12，ACL和数据单服务重启恢复通过 |
| Kafka | 21:9092已有旧Kafka；spirithub另有Redpanda | 复用Kafka7.5.0 KRaft；1F新增19093 SSL入口，Fusion项目group已接线，原9092入口保留 |
| Qdrant | 21:6333/6334现有1.7.0，1D盘点集合为空 | 已复用原镜像/卷，实际nofile65536；独立测试集合恢复后已删除，HTTP存取已验；SDK/业务检索另验 |
| embedding | 21独立Ollama0.40.6/qwen3-embedding:0.6b，loopback11435/项目网络 | 16核CPU/32GiB；与20镜像、模型/链接hash对应，1024维结构已验，业务适配未挂载 |
| Chat/LiteLLM | 43既有服务；21新固定LiteLLM1.106.0，loopback14000 | 五角色路由/JSON已验，独立master key、超时45秒/重试0/无fallback；20/43未改，1G真实调查已消费网关；知识/模型质量到3C比较 |
| 服务API | 21:8000/8080已由spirithub发布 | API127.0.0.1:18000、Fusion127.0.0.1:18003已启用；不占用原8000/8080，无控制台 |
| 后续full依赖 | 21已有8123/9000、7474/7687、9200等发布 | 优先复用公开服务；对应阶段核版本、只读权限、隔离及外部数据合同，不覆盖旧业务数据 |

20当前16容器的官方应用镜像revision、基础Compose及overlay均已核对；其部署仍主要使用官方镜像，不能算作socai2源码可复现构建。20的LiteLLM配置文件与固定源码相同，运行路由另由env/overlay决定。镜像digest、挂载及已有卷归属见[20快照](initialization-host20.json)和[依赖盘点](dependency-inventory.json)。

## 软件锁与构建约束

| 路径 | 源码中的依赖依据 | 迁入和验证方式 |
| --- | --- | --- |
| Python服务 | API/Fusion/Agents/Actions及按需TI等原锁；Python3.11镜像、Poetry2.4.1/export1.9.0 | 只为选用服务建立独立环境；按原Dockerfile导出带hash依赖并require-hashes安装；13份锁属于已有参考全集，不全部安装 |
| 前端/Realtime的Node依赖 | 已有快照中保留根pnpm锁和服务npm锁 | 当前不安装Node/pnpm/npm、不迁前端或独立展示推送服务；这些原件仅保留来源信息 |
| Go（默认非前置） | 原ingest/enrichment等使用Go，告警处理核心使用Python | ingest接入/规范化不在本轮目标，不构建其Go镜像；M15若确需原Go增强服务，单列该依赖和构建批次。现有go.mod/go.sum保留为参考，不默认安装Go |
| 基础镜像 | 上游部分标签可变，如Redis7-alpine、Python3.11-slim和LiteLLM main-stable | 后续首次构建/部署保存实际digest、架构和构建日志；本轮固定源码不等于已锁住镜像或下载包 |

根目录未来接入Docker构建时，先确保 `.local/` 等私有目录被构建上下文排除，再迁入原Dockerfile。配置按真实AiSOC变量逐项映射，独立生成21凭据；只在Git忽略的受控位置保存。当前SOCAI2变量仍只是连接索引。

当前从已有告警进入Fusion及后续服务，1F已取消整套ingest、Realtime和前端作为前置。需要验证告警消息合同、授权和实际订阅；不因接口名称含raw而把原始日志检测纳入范围。原参考源码/依赖原件未删改；1B共享服务配置及对象变更以实际回执为准。

必要的删除或业务修改先形成目标、原因、受影响模块和验收，与用户讨论后再做；保留原件和差异记录。直接阻塞下一批的环境适配也要记录，不借机改架构。任何测试结果只覆盖实际输入、调用和最终值，不把静态检查、服务连通或替身自测记作业务质量通过。

## 第一阶段之后的当前批次

2A原版真实投递核对及成员重投计数修复已执行，见[回执](2a-dedup-correlation.md)；只增加Fusion源码差异层和Compose镜像叠加层，不改1F历史清单。2A-01后续已完成source-v1限定验收，见[独立身份回执](2a-source-identity.md)，旧标记保留legacy。2B-01已完成RBA风险重投修复及限定并发/重启验收，见[回执](2b-risk-idempotence.md)。2B-02规则实际指纹/方法消费/TTL/恢复已限定验收，见[回执](2b-policy-versions.md)；2C-01本地历史IOC查询/冻结证据限定验收已通过，见[回执](2c-ioc-consumption.md)；2C-02 PG材料读取/独立评分已限定验收，见[回执](2c-processing-context.md)；2C-03已核来源不足并验缺源返回，见[回执](2c-event-ueba-sources.md)，真实数据消费保持未接；3A-01规则抑制持久记录及提交保护已限定验收，见[回执](3a-policy-suppression.md)，3A-02消息/真实模型/账本/API及盲测分类已限定验收，见[回执](3a-model-triage.md)，完整质量未过；3A-03缺失风险分/显式0及来源语义已限定验收（184项测试、一次真实模型），见[回执](3a-risk-score.md)；3A-04组织记忆认证/失败状态及真实模型消费已限定验收（194项测试、一次真实模型），见[回执](3a-org-memory.md)；3A-05技能认证/读取选择、真实模型消费及重启回查已限定验收（347项测试、1677 tokens），见[回执](3a-tenant-skill.md)；3A-06 KB认证读取、保守cutoff、实际采用文本/引用及重启回查已限定验收（236项测试、2095 tokens），见[回执](3a-kb-read.md)。KB1进入真实prompt但模型未引用标记，不作引用/向量检索质量通过；3A-07近期处置认证读取/采用来源及重启回查已限定验收（396项测试、一次模型1909 tokens），见[回执](3a-dispositions.md)。三条个人意见进入实际prompt但无精确note/ID引用，不作因果采用或质量通过；独立导入环修复后最终镜像只读验证通过，模型未重测。3A-08身份认证读取/失败来源/实际采用及重启已限定验收（496项、一次模型1781 tokens），见[回执](3a-identity-read.md)。五类reader已接通，合成图读取不证明HR历史或完整质量；3A-09三例真实复验及可靠性审计已完成，见[回执](3a-triage-admission.md)：分类3/3、5223 tokens，但p01理由有缺陷，broker实复现提交/重投/来源恢复缺口，完整质量和worker准入不通过。3A-09当时运行未改；3A-10-01普通分诊持久确认/已解码坏消息已限定验收（143项测试、26项显式HTTP、0真实模型），见[回执](3a-triage-durability.md)。该批仅更新Agents；3A-10-02普通live分诊首次结果/重投保护已限定验收（207项、55项HTTP、0真实模型），见[回执](3a-triage-recovery.md)。3A-10-02完成复用、完整材料恢复及unknown停止限定通过；3A-10-03-01请求/cursor已限定验收（189项、71项HTTP、0真实模型），见[回执](3a-triage-request.md)，3A-10-03-02持久额度/积压/停止小边界已限定验收（263项、137项HTTP、0真实模型），见[回执](3a-triage-budget.md)，当前二十一层；下一3A准入剩余阻塞复核见[总计划](3a-worker-reliability-plan.md)；常驻自动分诊及完整3A另验，不外推完整缓存丢失、持久风险账本或所有风险支路。

## 3A-11-01最新只读准入复核

3A-11-01只读准入复核已完成，见[回执](3a-admission-review.md)：旧p01时间/授权错误未被indicator gate识别；常驻Agents审批提案guard实际True且缺Kafka bootstrap/TLS，旧调查工具身份仍缺。三未知预约及A积压保持，0模型/消息/offset提交/运行改动；完整准入未过。下一[3A-11-02配置补齐](3a-triage-admission-config-plan.md)，保持worker禁用，然后单独修提示词/复验质量。

审批提案guard未显式禁用、常驻Agents缺Kafka bootstrap/TLS；worker关闭使其未作为常驻消费者运行，隔离探针通过不证明这些环境项已接。五reader不替代旧工具service身份。旧回执保持；本批无运行改动，三未知预约及A积压不清理/重调。

## 3A-11-02最新配置验收

3A-11-02常驻分诊配置补齐已限定验收，见[回执](3a-triage-admission-config.md)：仅Agents同镜像重建一次，新增四项环境值，复用原只读CA；审批提案guard现False、Kafka SSL/主机名校验及六组offset读取通过。旧14表/三unknown/A积压/十reader/其他35容器/18卷/134迁移保持，0模型/消息/提交。当前22层、19源码层，worker仍OFF；下一[3A-11-03理由提示词修复](3a-triage-reasoning-plan.md)，完整准入/质量未过。

当前补齐的是transport及审批提案禁用，不含常驻topic/group/DLQ项目映射；五reader与通用工具身份仍分开。A积压与unknown不清理/重调；p01理由仍未修，不能将配置就绪当质量或常驻准入。
