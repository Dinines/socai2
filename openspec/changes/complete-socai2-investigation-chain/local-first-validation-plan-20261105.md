# 本机数据环境与分阶段模型验证计划

2026-11-06最新追加测试已结束，沿[本次有界计划](additional-validation-20261106.md)新增三案/15次DeepSeek，累计63/69；数据库126现29表462列，本机API已加载。48GET/674项、557页面检查/87视图通过，原模板三案可查看；两个C3拒收和语义质量问题保留。当前统一读[测试及字段功能交接](../../../docs/investigation/investigation-test-handoff-20261106.md)。下文48/50、33/50及459列为历史时点，部署模型仍待下一轮。

2026-11-05最新案例对比：已按用户要求执行local-eval-20261105-01/02/03（每组2告警/2日志），新增15次DeepSeek、本机累计48/50。保现有算法/提示词、4模型/4工具/48k/120秒单轮边界和原页面模板。日志经Kafka入湖且逐值读回，3案件当前判断均为model/accepted/partial/uncertain，不能称3次确定良恶判对。原答保持，质量问题单独记录。

| 固定样例 | 当前真实结果 | 主要评估发现 |
| --- | --- | --- |
| 01 账户清点与报表复制（预期正常） | A0/A1/I/C完成；C6待核，查网络/认证各0行 | 缺授权/完成数据，允许待核；A1“已发生复制”及领域“外部共享”无据，C6主结论未扩大完成结果 |
| 02 内存转储与归档（预期恶意意图） | A0/A1/I/C完成；C6敏感但暂不能定性，查进程2行/网络0行 | 识别敏感命令，风险区分偏保守；PID688身份、文件落地、外传未证实 |
| 03 删除恢复副本命令与单文件改名（预期恶意意图） | A1/I/C3输出引用校验失败；C6仍调用、完成并采用，无C4查询 | C6误将process_start及单file_rename扩大为删除/加密成功，并把--note写成勒索说明已生成；质量不通过 |

15个provider响应均completed；03失败属于输出依据角色/成员范围不满足合同，不是服务不可用或入湖格式错误。本轮未调提示词或放宽校验。资产/SOP已种入且标题FTS通过，但C2知识工具因预算保留未取，不能称消费了SOP。共同operator-0与顺序执行使后组A可见此前合成历史；预期标签始终隔离，3样本不计算总体准确率。01/02无来源领域误判not_applicable与03事实扩大归入原3.10后续，不重跑或覆盖旧批。H不在三组单轮计划内，3.16保持待办，服务器模型仍延期。

证据：[对比回执](../../../docs/operations/evidence/investigation-repair-20261105/local-comparison-summary.json)、[离线核对脚本](../../../docs/operations/evaluate_local_comparison_20261105.py)、[原模板截图](../../../docs/operations/evidence/investigation-repair-20261105/local-comparison-cases.png)。30驱动/配置和31页面检查最新通过；页面检查首轮假定所有A必有解释而1项失败，现按保存指针校核，未补造字段。独立只读窄审/root/review_design_audit限定ACCEPT夹具/驱动、0必须修；独立3新增用例及15请求无oracle通过，明确模型质量不通过，不核销4.1整体实施审计。

2026-11-05当前状态：本机环境与入湖已核，a–g累计33/50次模型尝试。g首轮首次保存有效模型Case判断并覆盖2成员、2次真实湖查询；H限定授权已保存，下一C因H与必需I摘要挤占8KiB视图而在模型调用前停止，仍未完成全链质量验收。C6强制收尾及业务字段分离已通过限定PG/原页面验证，3.15完成；3.16跟进H后容量。d-r2/g在原模板可查看，原失败和原答保留。服务器模型按用户选择延期，不连接VPN。当前证据见[限定汇总](../../../docs/operations/evidence/investigation-repair-20261105/local-c6-business-fields-summary.json)，下文a/b/c状态为各批历史，不能代替当前状态。

## 1. 环境分工

| 阶段 | 数据、检索及执行程序 | 调查模型 | VPN |
| --- | --- | --- | --- |
| 常态开发与第一轮验收 | 本机专属PG、ClickHouse、Kafka、ZooKeeper、Redis和API/Fusion；知识沿告警标题做PG全文检索 | DeepSeek直连 | 不需要 |
| 远端模型对照 | 数据库、执行记录、工件及页面全过程仍在本机，保留配对材料和独立Run | 只切模型连接地址、认证和对应协议/profile，调用既有远端部署模型 | 仅本阶段连接 |
| 结果复核和页面开发 | 本机数据库、工件原件及离线页面导出 | 不调用 | 不需要 |

用户已确认当前知识路径是告警标题→PG全文检索，不依赖向量库或Embedding。本轮只准备上述必要数据服务与本机API/Fusion，不新增RAG，也不以Neo4j、Qdrant、Embedding或无关网关可用作为启动前提。图/向量服务和模型缓存的盘点只保留为已有资源记录。用户允许本地测试库清理重建，当前选择专属新空间隔离旧环境，旧后台任务按最新授权保持停止，不执行旧库清理、清卷或重放已结束批次；后续必要重建须明确本轮专属测试目标。

## 2. 已有本机环境

本机为arm64，Docker CLI 29.4.0、Compose v5.1.2。下表保留原资源盘点与复用选择；当前专属5项基础服务、API/Fusion及实际入湖已验证，具体身份、schema与范围见第6节，不能由此推及未启用来源或模型质量。

| 组件 | 本地已有内容 | 当前观察与下一步 |
| --- | --- | --- |
| PostgreSQL | `postgres:16-alpine`，旧`aisoc-postgres` | 旧容器保持停止；本轮专属实例healthy，已核29表459列、强RLS及受限运行角色 |
| Redis | `redis:7-alpine`，旧`aisoc-redis` | 旧容器保持停止；本轮专属实例healthy，未清旧缓存 |
| Kafka / ZooKeeper | `confluentinc/cp-kafka:7.5.0`、`cp-zookeeper:7.5.0` | 两旧容器保持停止；专属两实例healthy，三个topic及真实消息消费/发布已核 |
| ClickHouse | `clickhouse/clickhouse-server:23.8` | 旧实例保持；本轮专属实例healthy，48列表覆盖47个writer字段，reader仅SELECT、writer仅INSERT，2条本批湖日志已读回 |
| Neo4j | `neo4j:5.15-community` | `sting-aisoc-neo4j`正在运行，7474/7687绑定loopback；本轮不改动，不作为必要依赖或图查询已验收的证据 |
| 向量库 | `qdrant/qdrant:v1.7.0`，`aisoc-qdrant` | 镜像和旧容器已有，容器已停止；本轮不启动或补接向量检索 |
| Embedding | Ollama缓存`qwen3-embedding:0.6b`和`:4b` | 已确认manifest与所列layer文件存在；尚未运行模型或核完整文件hash。本轮不调用Embedding，缓存存在不代表向量质量已验证 |
| API / Fusion | 项目Python 3.12与本机当前源码 | 两应用ready，Fusion真实消费专属topic并写本轮PG/CH；模型仅API显式执行，不启动旧全套自动消费者 |

OpenSearch镜像及运行容器也已有，本轮不启用Feed供应链或修改该服务。`sting-aisoc-litellm`盘点时处于重启循环，原因未查；DeepSeek已有直连协议，不将修复这个无关网关作为第一轮前提。

启动前检查现有Compose归属、卷、端口、镜像架构、账号和依赖，避免`compose up`意外恢复旧业务worker。盘点时运行的ingest、UEBA、threatintel及realtime已按用户最新授权停止，历史数据保留；恢复旧PG/Kafka仍不属于本轮计划。本轮继续使用新专属容器、网络、卷和不冲突端口，不自动重启旧worker。PG按新服务support schema与123/124/125初始化，保留运行角色/RLS；不执行整个旧系统迁移链，也不复制21密码、原业务库或历史Run。

## 3. 已接来源与真实缺口

| 来源 | 已有实现 | 本轮补验内容 |
| --- | --- | --- |
| 知识库 | 新C2用冻结告警标题作为检索词，查询`public.aisoc_kb_documents`；[现有导入](../../../services/api/app/api/v1/endpoints/knowledge_base.py)可切块写同表；[C2查询](../../../services/api/app/socai2/baseline_optional_sources.py)为PG英文全文检索 | 3.14核文档导入、实际落表、标题检索词、按租户FTS结果及候选模型输入；3.7再核实际发送及引用。文档是指导，不是本案授权或行为证据 |
| 向量检索 | 已有Qdrant/Embedding配置和旧知识服务路径 | 仅保留已有资源与路径边界，本轮不补向量接线或新增RAG；当前C2的PG全文检索不得写成向量检索 |
| 身份图 | 新C2已有Neo4j只读账户适配，旧链已有真实图与模型验证 | 本轮不以真实图接入作为启动前提；未启用状态明确保留，旧证据不能冒充本轮实际查询。身份背景不等于C5攻击链推断 |
| 资产 | A/C2查`public.assets`，既有资产写入API | 构造主机/FQDN/IP及缺失/歧义，核实际写入和读取；库存不证明事件发生时状态或授权 |
| 内部情报 | A/C2查`public.threat_intel_iocs`，已有内部IOC写入API | 通过实际写入路径验证类型、有效期、误报和租户；Feed写OpenSearch/Qdrant/Neo4j是另一条供应链，不默认等同PG内部IOC已填充 |
| UEBA | C2读`user_risk_profiles`，旧UEBA/Fusion链也有实际验证 | UEBA消费者写baseline/anomaly等表，尚未确认到risk profile的衔接。本轮保留该缺口，不以补齐供应链作为模型前提；直接种合成profile只能证明读取能力，不能冒充UEBA生成 |
| 湖及历史 | 已有固定主机/租户/窗口的进程、网络、认证查询及历史告警读取 | 实际Kafka→Fusion→湖/PG后按事件ID和字段读回，核窗口外/其他主机控制记录，保存全部查询工件 |

旧KB链已完成合成行直接写PG→认证API→一次真实模型输入的限定验证，[回执](../../../docs/operations/3a-kb-read.md)明确该批不是实际文档导入流程，模型也没有采用KB引用标记，不能称导入流程或引用质量通过；新C2有真实PG合成查询检查，尚不能替代本轮导入到模型的完整证明。独立`socai2_main`未挂载知识、资产、情报的管理入口；本地测试复用已有导入函数或有限入口，不为验收重建一套管理后台。

完整C2仍最多用2个工具槽，给C4留2个。开关开启不保证每轮选中知识；准备至少一项能按当前选择规则命中的知识材料，另核未选、空返回和不可用的区别。未启用图等来源不算本轮实连通过；不得为了让所有来源每轮都调用而偷偷提高预算或修改排名。

## 4. 执行顺序与停止条件

1. **本机专属环境预检和启动（3.13）。** 复用已有镜像准备专属PG/CH/Kafka/ZooKeeper/Redis及本机API/Fusion，核账号能访问目标库/表、迁移、字段和实际最小合成写入/读回；Kafka确认topic/group及消息收发。服务不可用、认证失败、授权错配、Schema/格式、应用错误分别报告。必要前提失败先定位，不派发模型；图、向量库和Embedding不列为必要前提。
2. **已有上下文的模型前准备（3.14）。** 复用数据准备工作树与现有导入代码，构造文档及本轮所需资产、内部IOC；核实际落表、告警标题→PG全文检索结果和候选输入中的来源身份，把直接种表与经过实际导入路径明确区分。3.14据此核销，不要求先有模型结果；实际材料是否发给模型、采用与引用是否正确只在3.7核销。未启用的图、向量、UEBA生成及Feed链如实列出，不为本轮补成新供应链。
3. **DeepSeek真实整链。** 不开VPN，跑授权维护、凭据访问、证据不足三类固定小案；真实入湖及A/I/C。维护案首C经过语义审阅后保存明确范围H，再启动第二C；其他两案先到首C。
4. **本机导出和原页面阅读。** 先让用户看DeepSeek实际结果。保留真实Case/Run/材料/模型/工具/H版本及当前判断来源，不要求实时服务页面接线。修导入适配器已知字段问题，再接回原五个阅读页签；不覆盖原样例和本地编辑。
5. **远端模型窗口。** 本机材料与脚本固定后再通知用户连VPN，只切换模型连接地址、认证及对应协议/profile；数据库、API/Fusion执行、记录、工件及页面全过程留在本机，不依赖远端PG/CH/Kafka或远端执行驱动。使用配对材料、独立操作ID/Run和同一预算；端点可达性、协议/profile预检通过才派发。
6. **断VPN后复核。** 结果保存在本机，语义/字段审计及页面开发均不依赖VPN。维护案需要H后第二C时，审核后安排下一模型窗口；不为了“一次跑完”跳过首C审核。

VPN阶段提供固定、有限次的本地执行命令，日志/意图/回执实时落盘，运行不依赖聊天连接持续在线。聊天重连后先读取回执，不重新提交；调用超时或结果不明保留unknown，不自动重试，也不自动切成DeepSeek继续同一Run。用户决定连接/断开VPN，本轮不更改系统VPN或路由。

两模型各三类小案：维护案最多11次模型调用，其余各7次，每模型最多25次、合计50次；这是固定上限，已发生用量单列。a5+b4+c5已累计14次，后续仍计入本机50次总上限，不重新获得整份额度；旧k5/k2的额度不滚入。每个新完整C继续48000保守单位、4模型、4工具、120秒，A/I额度保持；本轮不调用Embedding。

两条链使用语义等价、可核对ID映射的合成输入和上下文，各自独立产生A/I结果，不能让远端模型偷偷复用DeepSeek结论。这是整链对照；上游A/I结果不同会影响C输入，不据此宣称C请求除模型外逐字相同。

## 5. 数据与页面验收

- 入湖：原事件ID、时间、主机、用户、进程/网络/认证字段、raw/OCSF逐值读回；单列同主机窗口内背景和范围外对照。
- 上下游：告警和事件实际关系、材料版本、来源角色、A/I真实请求与结果、C1冻结范围、C2来源选择、C3计划、C4查询、C5图和C6结果逐项回查。
- 语义：进程启动成功不等于任务完成，TCP/443不等于已证明HTTPS/外传，库存/知识/历史评分不等于本案证据，H只确认声明范围。
- 数据库：Case/Run/Result/H身份和关联、当前判断采用来源、覆盖及实际freshness、unknown用量与缺失字段；GET不改业务时间。
- 页面：真实导出原件与manifest/hash保留；critical不降成high，`available`优先级状态不写成`known`，审批未知不写成无需审批，pending不冒充活跃；系统交接不冒充模型结论。原字段缺口逐项列出，不用默认值补齐。
- 质量报告：有效答复、良恶反转、可接受待复核、无依据事实、引用错误、调用/解析/环境失败分别统计；失败也展示真实回执，不挑成功结果替换。

## 6. 已完成工作与停留位置

容量预留、query/Deep分流、集合GET等代码与限定验证保留；此前n15及125只更新21独立新服务。当前本机C3目录/C6提示及C3绑定动态Schema已完成最小调整，c使用冻结候选已执行结束，不再将当前源码一概描述为与n15逐文件相同；旧发布与原证据不改写，不为本轮恢复远端数据服务。

本机环境证据见[回执](../../../docs/operations/evidence/investigation-repair-20261105/local-environment/receipt.json)：专属5项基础服务healthy、API/Fusion ready；PG29表459列、29张调查表及7张背景表强RLS、受限角色和回滚跨租户探针通过；CH48列覆盖47个writer字段，精确读写权限核对通过；Kafka三个专属topic。初ZK健康检查参数、CH线程池配置及DDL注释分号切分错误修后通过，原失败保留，不称一次全绿。旧`aisoc-ingest/ueba/threatintel/realtime`均停止，历史数据保留。

`local-maintenance-20261105a`的本机原件目录为`.local/local-investigation/validation/local-maintenance-20261105a/`：`ingest-outcome-20261105T102106442066Z.json`记录2告警、1事件、2条湖日志，`lake-readback.json`保存事件ID与原OCSF核对；`20261105T102032487568Z-context-seed.json`记录1项资产直接写表、真实KB ingest函数生成2个SOP块、两标题FTS及受限API角色读回。该导入不经过HTTP权限依赖链，未验HTTP导入鉴权；3.14只部分完成。C2本轮实际选择TI/UEBA，知识未进入调查，不把准备成功称为模型采用/引用成功。

`first-outcome-20261105T102314887150Z.json`及`exports/20261105T102314778605Z/`保存a批5次真实DeepSeek尝试（A0/A1/I/C3/C6）、4 Run、28 Step、66工件。A0/A1/I发布成功不等于全部语义已验；C6原答缺必填`analysis.followups`，`delivery_shape_invalid`阻止模型结果发布，留下1份system_only、0案件判断采用、0 H任务。源数据、请求和原答完整保留，未执行H/第二C；a不重派，不宣称完整调查通过。

另有必须分开的输入容量/能力暴露缺口：a的C1已生成3个湖工具binding，C3目录却因`binding_catalog_input_limit`全部裁剪，实际`tool_options=[]`，模型没有可选query；Deep又因C6资源预留跳过，本C实际0湖查询。湖数据存在、C1有绑定不等于模型看到查询能力或已消费补证，不将此问题归为C6输出漏字段。

修复与限定证据：[C3离线回放](../../../docs/operations/evidence/investigation-repair-20261105/local-a-c3-catalog-replay.json)保持a原事实、来源映射和覆盖，7930B≤8192B；3个绑定按共同scope无损分组成为第3条user消息，全部messages12220B≤12288B，DeepSeek完整wire17363B，guard在裁剪前及全部发送消息上检查，绑定map/Schema与实际提供目录一致。[C6诊断](../../../docs/operations/evidence/investigation-repair-20261105/local-a-diagnosis.json)确认漏followups及domain引用成员范围问题；仅澄清提示，候选完整请求增66B，数据/Schema/原48k预算与输出上限不变。23项直接检查和独立代码窄审限定ACCEPT，不证明模型会选择查询或输出正确。

`local-maintenance-20261105b`的`preflight-outcome-20261105T104841365519Z.json`及`ingest-outcome-20261105T104856193160Z.json`证明预检和2告警/1事件/2湖日志；`first-outcome-20261105T104937560207Z.json`与`exports/20261105T104937427659Z/`保存后续4次模型尝试、4 Run、26 Step、56工件。A0/A1/I发布，C3原答`followups[1]`选择B1 `network_connections`，`object_keys`却包含host和目的IP，绑定只允许host，以`followup_binding_object_mismatch`严格拒收。模型服务正常，C6未调用，1份system_only、0案件判断采用、0 H；Case实际湖补查0。b已结束，不写成运行中或成功；后续C3动态Schema修复及c结果见下文，不重派a/b或改写原答。


C3绑定约束已落实为仅供新完整C使用的动态Followup Schema：相同alert_ids/对象集合的binding合组，query成员精确匹配且对象只能取绑定子集；非query保原Context范围、binding_id为null。standard发送Schema含uniqueItems，vllm兼容发送仍沿原profile去除此关键字，但canonical解析器继续拒绝重复成员。协议转换后只将C3发送Schema的根$defs及对应$ref等价短命名，不改事实、提示、输出字段或枚举；A/I/Deep/C6路径不改。59个不同纯检查最新通过，独审复跑其中11项并限定ACCEPT。

[动态Schema容量回执](../../../docs/operations/evidence/investigation-repair-20261105/execution-schema-capacity-20261105.json)对3份历史输入及a/b共5份固定两成员输入、两协议各测一次，共10格均保3个binding并通过完整wire准入。候选新完整C预算48000不回写历史24000；保输出上限、C6预留与原件hash，最小余158，b的DeepSeek请求17311→17458B、原C6预留27076后余210。b原答在新wire校验中被拒；合法host-only正例仅为内存构造，未修改或采用原答。离线准入不证明一般Case容量、实际模型遵守约束或结果质量。

`local-maintenance-20261105c`在API重启加载冻结源码后，完成prepare、SOP/资产准备、preflight及Kafka入湖2告警/1事件/2湖日志，再完成第一轮实际执行。C3阶段及模型completed，新动态Schema经真实请求通过；C6阶段及模型failed，原因delivery_shape_invalid。c共4 Run、69工件、5次模型，a5+b4+c5累计14次仍计入本机50次总上限；0案件判断采用、0 H，未执行H/第二C。[c原件诊断](../../../docs/operations/evidence/investigation-repair-20261105/local-c-diagnosis.json)确认C6唯一Schema错误为多余analysis.conflicts_note:null，发送合同additionalProperties=false且未定义该字段，Pydantic为extra_forbidden；provider completed、2698输出tokens小于3000、无incomplete，完整wire18656B，当前Schema/prepare重建及回显Schema与原请求一致。进程/网络两次正式Lake query各返回1行，无Deep；C4中间视图已有9个湖字段（进程5、网络4），7854B；C6第二次bounded_input优先放入冻结必需事实/原计划，9个湖字段均以model_view_budget_exhausted省略，最终视图7940B。C6的source_map无query_binding_only湖行，只保留2项queries/routes执行元数据，原计划到projection的链接及Tool原件仍完整。这是自身二次输入投影的容量缺口，不能把查询完成说成模型已消费返回事实；与provider输出违约分开登记。诊断另列缺证据却判领域不适用、只见元数据却评价查询未给关联字段的语义限制；内存仅移除conflicts_note可过结构校验也不等于质量通过，不保存或采用该改写。不连续微调提示或重派结束批次。以下离线修复保留这次失败原件，不回算或重派c；修后没有新增模型调用。用户已决定稍后再测服务器模型，本轮不建立VPN连接。


C6投影修复及[只读回放回执](../../../docs/operations/evidence/investigation-repair-20261105/final-query-projection-20261105.json)：仅final_delivery从本轮已核hash的完整query_projection构造字段候选，不再继承C4已裁剪的9项列表；原C4/Deep工件保持。共同查询元数据无损提为query_context，缺键、null和不同值不合并。非空查询保一行最低实质证据，缺少最低项或受guard/容量阻断则明确拒绝；过程命令与actor进程、源端点与目的端点分开，同一行端口不串到其他记录，产品快照仍为source_label。source ref、原字段路径/transform/conflict和query_binding_only保持，首次投影与最终wire裁剪后同步projected_fields/visible_fields。

c候选从完整投影27字段中保命令、目的IP、目的端口3项，其余24项均明确列省略；进程1/13、网络2/14都是partial，不称完整原始日志或全部字段已读。原22项必需依据的ref与值hash全部保留，新required为25项。视图7919B≤8192、全部消息11695B≤12288、完整DeepSeek wire18850B；原C3实际usage7738，加当前3000输出及256余量后，48000总预算仍余18156，budget_reason与final_wire_reason均为None。输出Schema除本次SourceId枚举逐值保持，c原答仍extra_forbidden且不采用。独立审阅复跑10项并内存重建以上完整请求，限定ACCEPT；未查询数据库、调用模型或改写原件。

41项不同相关检查最新通过，非首次全绿：首轮39过1旧24k容量回归失效，原17744B限额下保最低目的IP/端口后的必要wire为18043B、超299；按新最低证据要求明确拒绝，不涨旧预算或删证据维持旧通过断言。历史紧缩可行性不再代表修后该旧包可准入。量测脚本初次把图的query_binding_only混入湖字段清单而KeyError，后按真实projection ID筛选修正，初次未产生回执、原件保持。以上只证明候选离线可行；provider额外字段问题、模型实际消费修后输入和有效C→H→下一C仍待新批验收。

`repair-k5`模型调用为0，4条告警已写PG、实际2个事件、湖中本批4个ID均0行。根因为测试连接复用了只允许`aisoc.*`的原Fusion湖账号，而目标是`socai2_next_validation`；服务可达、登录成功、目标表含全部47写入列，离线格式检查通过。[诊断](../../../docs/operations/evidence/investigation-repair-20261105/repair-k5/ingest-diagnosis.json)保留，旧批不重派。

`repair-k6`仍是未通过离线准备的脚本草稿，准备程序在生成目录前失败，未封包、上传或派发。新本机方案另立批次，不沿用这个草稿的完成假设。

离线导入adapter/CLI已接真实导出；a实际浏览已核700px布局、历史、失败状态及原件回查。b亦实际浏览，截图约906px宽：案件资料显示2成员、0判断/0 H，历史4轮顺序C/I/A1/A0，C详情保留真实失败和绑定对象范围不符说明。四旧容器再次只读复核均exited，未删volume。[页面字段回执](../../../docs/operations/socai2-local-page-field-coverage-20261105.json)现覆盖a/b/c固定导出，27项已有相关检查证据复用，本轮未重跑。root已对c约906px实际浏览：原件可读、来源检测置信度28.2/100、Execution覆盖2告警、A/I/C真实链接、4轮历史、两次query各返1行和failed/0当前判断/0 H均核。c窄屏未验，不沿用a的700px结果；页面核对不是在线数据库刷新，也不改变失败/不采用状态。对象去重数不等于来源行数，case_incidents完整关系行和activity_targets前后值在原始导出，未检索的知识结果不补造；整个3.12仍未完成。

[最终本机就绪回执](../../../docs/operations/evidence/investigation-repair-20261105/local-environment/final-local-readiness.json)记录2026-11-05 11:40:49 UTC：API已重启加载最终修复，API18020/Fusion18021/页面4174均HTTP200；模型累计14次、活跃或unknown Run为0、6告警/3Case/0案件判断采用/0 H，0新增模型。用户已选择先保留本机结果、稍后再测服务器模型；本轮不建立VPN连接。

[本机驱动说明](../../../deploy/local-investigation/README.md)已补新批显式backend及model/protocol/profile/base URL摘要冻结，计划不导出URL明文、API key或key指纹。preflight先核模型配置及凭据，再核源码；同时漂移不会绕过配置拒绝去自动导出。24项离线检查通过，独审复跑2项，显式旧历史导出仍允许。该检查不是运行API或远端模型身份认证；后续切换仍须无活跃Run、重启API并核实际wire回执，不代表远端已连接或模型效果通过。

当前17/23；3.7、3.10、3.12、3.14及4.1/4.2仍待完成，不归档，无Git提交或推送。


### 已保存图谱与失败汇总原答回填（2026-11-05）

按用户“原模板只填数据，不改页面”的要求，本次仅调整导入数据的只读投影和选择规则。案件关系图允许读取同轮已完成 C5 的真实工件，不再因 C6 失败隐藏成功保存的图；按冻结告警来源引用映射两个告警根节点，避免图组件额外添加重复告警。c 实际页面为 12 节点、8 条连线，未按相同名称合并原件中不同来源的 IP/进程节点，也不将其称为已证实攻击链。

C3 初步分析、C6 已返回但拒收的模型正文填入原有资料摘要、调查发现、AI 分析和报告区域；统一标明“模型原答（格式校验未通过，未采用）”，并按 C6 receipt 的 markdown_artifact_id 读取真正保存的系统交接报告。原答 JSON、Run failed、Result system-only、Case assessment null 及动作记录保持，不删除多余字段重新采用，也不将原答建议变成执行动作。c 拒收的具体结构问题仍为 analysis.conflicts_note=null 属于禁止的额外字段；远端已返回完整回复，不能解释为本次服务不可用。

34 项定向检查通过（29 导入/路由/原件 + 5 既有图谱选择/探索），真实浏览核对资料摘要、12/8 关系图、完整原答及交接报告。另一个旧 aisoc20 图谱测试因测试加载器缺 createCaseAssistant 在改前与改后均失败，不宣称全量测试通过。11 份 HTML/CSS/数据集文件 hash 不变，a/b/c 数据库导出 hash 不变；渲染结构与样式未改，只让来源说明和时间文案反映实际失败状态。无模型调用、数据库写入或浏览器业务保存。此次只修复已有材料的可读性，完整 C→H→下一 C 的验收仍未完成，远端模型仍按用户要求稍后再测。详见 [回填核对回执](../../../docs/operations/evidence/investigation-repair-20261105/saved-analysis-readback-20261105.json)。
