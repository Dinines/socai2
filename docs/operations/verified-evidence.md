# 已有证据与未验范围

最新限定结果：[C03-R01](c03-triage-review-only.md)代码隔离与定向部署已限定验收：191项断网测试通过（22项新增、169项既有直接测试），0真实模型/新业务写；仅Agents一次构建、一次替换为19f8f1a5，review_only_v1已配置、worker OFF，七只读挂载/60秒宽限保持。旧14材料表、全部告警字段、12预约/240000预留单位/3unknown、十reader、其他35容器/18卷/134迁移及消息水位保持。首次观察脚本RLS错误与189通过/2夹具失败及恢复均保留。当前28层运行定义、185 Agents/770运行Py，prompt/lock v5不变。下一按[人审准入卡](c03-review-only-profile-plan.md)另冻R02，验两条新A/B输入的有限真实main消费与首次结果恢复；原自治质量失败、C04/C05及后续调查/响应仍待验，整体迁移未完成。

下表复用旧工程和20服务器已保存的历史记录，初始化交接时没有重跑这些业务、模型或厂商动作。1B另有21真实基础设施结果，见文末。

当前验收目标是[告警处理服务端](alert-processing-scope.md)。下表的20页面/登录等历史结果继续保留，只证明参考环境对应事实，不意味着本项目需要前端，也不证明21服务已部署。

同日新项目初始化1A另完成了只读环境盘点和依赖文件校验，见[初始化回执](initialization.md)及[依赖清单](../handoff/dependency-manifest.json)。这批新增证据仅覆盖90文件的来源一致性、13服务版本导出、上游导出脚本自测及Compose静态解析；没有重新执行下表业务/模型smoke，不扩大其验收范围。

| 场景 | 输入与实际结果 | 原件位置/限制 |
| --- | --- | --- |
| 认证/页面 | 控制台 health 200，demo=false；登录和 auth/me 返回 admin tenant | `deployment/login-check.json`；不包含密码/token |
| 接入/Fusion | golden run `5c3757a85756`，accepted1/rejected0；告警 `b6f8d542-a461-5b03-b515-6da94297b205`，high/CrowdStrike Falcon，10/10 | `deployment/golden-pipeline.log`；是合成事件，只验证到 API 读取 |
| 对话连通 | `aisoc-triage` 经 43 返回 READY，约1.409s；19输入/2输出/21总 tokens，费用unknown | `deployment/model-smoke.json`；不是调查质量 |
| 原生 embedding | 三条文本得到1,024维非零向量；约4.412s | `deployment/embedding/native-smoke.json`；单样例，不是质量集 |
| ATT&CK | 内置14项，函数可检索 T1059 等 | 新集合 `attck_techniques_qwen06b_v1`；非全量 STIX，未证明 Agent 消费 |
| TI | 原1,748项全部 source=cisa-kev/tenant=shared，重向量化后 ID/payload 不变，检索有结果 | `threatintel_iocs_qwen06b_v1`；actors0，不证明精确 CVE 召回 |
| Memory | 标记为 deployment-smoke 的中文条目经实际 HTTP 写入/召回/删除并清理 | PG/新集合回到0；不是已有真实 Case 经验 |
| 本地合同 | embedding 三项 MockTransport/数值边界检查通过，相关 Ruff/语法通过 | 可复用 `deploy/aisoc20/embedding/test_embeddings.py`；非完整上游测试集 |

服务器原件路径相对 `/home/lychee/beenuar/`。首次失败证据仍保留，例如 `deployment/embedding/memory-smoke.first-failed.json`，不能抹掉后只称首次通过。

1B新增21真实PG/Redis验收见[共享服务回执](1b-shared-services.md)：134份SQL、角色/tenant读写、Redis账号及数据单服务重启恢复已验。仅基础设施层，不替代API、Kafka或业务链验收；原20证据保持。

1C新增21真实Kafka验证见[回执](1c-shared-kafka.md)：原锁客户端、容器经LAN listener投递、消费提交位置与单broker重启恢复通过。53个旧用户topic起止offset保持；单节点/明文及探针Python版本限制单独记录，不替代API/Fusion业务链。

1F新增[真实告警主链验收](1f-alert-chain.md)：14次HTTP检查、原锁源码镜像、134文件严格检查及70项相关测试；保留原版归并限制和首次失败回执。Kafka/PG TLS与API身份边界为本批范围，未调用模型/真实厂商。

当前范围尚未验：完整自动分诊升级、Case调查各入口、完整知识检索/引用质量、实际事件/已有UEBA信号消费、真实厂商查询、审批后响应效果、结案反馈及服务端隔离/容量。已限定的PG上下文、组织记忆、技能、KB与近期处置读取/消费见下文各批，不外推完整能力。按[服务端路线](service-roadmap.md)选批补齐。

历史参考中独立UEBA生产、原始事件检测和前端实时展示也没有完成相应验收；这些能力不纳入当前职责，保留未验事实，不列为本轮待办。

1D新增[21向量/embedding验收](1d-vector-embedding.md)：真实3条1024维有限非零向量→独立集合3点写读/自向量查询→Qdrant同镜像/卷重建后ID/payload恢复→仅清理本批集合。nofile实际65536，embedding16核/32GiB，3项合同测试另计；首次盘点遗漏符号链接导致的启动前失败保留。未接业务overlay，SDK、检索质量及调查实际消费仍未验。

1E新增[21真实五角色网关验收](1e-model-gateway.md)：triage/recon/investigation/summary/report各一次真实43请求，JSON字段/值、response deployment header与实际路由、463/153/616 tokens对应；缺key401、错误key400/no_db_connection及未发布/未知alias400。首次探针因预期401/403而失败，已保留。仅路由/结构验收；工具、调查质量、tenant/BYOK、Case/Run和超时故障未验，费用unknown。

1G新增[受控服务基线](1g-service-baseline.md)：591原件、6个必要差异、8个新增服务文件；123项测试。两Run各4次真实模型/18事件，首次5731实际tokens被原版重复记11462，修复独立Run实际与账本均5718、unpriced4。实际只读工具依赖未接而失败，正确标失败；两Run的API持久报告在Agents重启后hash保持，Case仍new。Actions仅真实HTTP dry-run，未验厂商/审批；2个测试API key已停用401，34个已有容器与18卷保持。费用unknown，API numeric零默认需结合provenance解读。

知识复用新增[数据清单](knowledge-data-inventory.json)、[本地模型清单](embedding-local-inventory.json)及[20/21资源快照](embedding-host-inventory.json)：只读hash/计数/show，无导入、推理或索引；4B声明2560维不等于本项目实际输出已验。后续见[复用计划](knowledge-data-reuse-plan.md)。

2A新增[去重/关联核对](2a-dedup-correlation.md)：8次原版投递复现2个阻塞点；成员重投计数问题已作单文件修复，25项测试与独立实体3次真实投递通过，2A-01发生记录合同仍未定。失败复验2条已受理样本保留，全批13次投递/34项HTTP检查；原5条PG材料不变，其余35容器/18卷保持，2测试key停用401，网关计数与1G相同。2A整体未通过；模型、厂商及质量未扩验。

2A-01后续[独立上游告警身份](2a-source-identity.md)限定通过：两锁环境95项测试，12条broker投递/41项HTTP验收检查，新增7行保留独立原文、时间、external_id及持久incident关联；旧HTTP/Kafka样本均保留ID，API/Fusion重启后11条回查保持。旧12行不可变材料摘要不变，134迁移不变，其余34容器/18卷保持，3测试key停用401，模型网关计数不增。旧折叠结果未重建，完整缓存丢失/并发/风险重投未外推。

2B-01新增[风险累计回执](2b-risk-idempotence.md)：真实HTTP链先复现30→近60分/计数1→2，单文件修复后新样例重投30分/1次不变；40项测试及真实Redis32次重复/64条不同告警并发、超50条展示上限、短TTL边界通过。实际confidence0.572→PG/API57，与RBA30和API存储priority50分开。Fusion重启后风险/材料保持，旧19行/其他35容器/18卷/134迁移不变，2key停用401，模型计数不增。ML状态503、完整缓存丢失/持久风险账本/跨实体事务及处理规则真实消费未验，整个2B未完成。

2B-02新增[处理规则回执](2b-policy-versions.md)：83项相关测试、旧实现5项新回归失败；真实API/PG及生产方法验证v1/v2内容指纹、实际30秒缓存后切换、恢复v1、tenant/权限与真实探针依赖失败，25项HTTP检查。只更新/重启API与Agents，22旧告警hash/其他34容器/18卷/134迁移保持，3key停用401，模型计数不增。抑制为直接调用实际worker方法，摘要为运维证据；自动Kafka分诊、抑制持久账本及完整模型消费到3A另验。

2C-01新增[历史IOC消费回执](2c-ioc-consumption.md)：旧SOCAI有日期/来源的一条历史domain，经真实HTTP/Kafka/Fusion/PG/API查询与冻结，6投递/5新行、21项HTTP检查及62项测试通过；历史命中弱、不加权，no_match与unavailable分开。单独SDK探针切换闭合端口/真实PG验证失败与恢复，未停共享PG；API/Fusion重启后首次证据保持。25旧行/其他34容器/18卷/134迁移保持，2key和2标记IOC停用，模型计数不增。整个2C、Agents旧增强工具和调查知识消费未通过。

2C-02新增[PG处理上下文回执](2c-processing-context.md)：6条真实受理的标记告警、现有表中合成资产/权限/漏洞材料→实际原算法706/435/B280，原严重度/priority不变；无匹配/明确关联/修复漏洞排除/过去而非未来告警及真实PG SAVEPOINT错误恢复通过。30项测试、38项HTTP检查；仅API更新/重启，30旧行/其他35容器/18卷/134迁移保持，3key停用，模型计数不增。是当前只读视图及合成合同验收，不是生产CMDB/HR/扫描器、普通日志/UEBA或LLM消费通过。

2C-03新增[事件/UEBA来源回执](2c-event-ueba-sources.md)：21 ClickHouse无业务表/旧UEBA六表精确0行，20 UEBA空、原始事件仅一条且无可用ClickHouse；50项替身合同测试和真实API/Agents缺源调用分开。12项HTTP检查、3次停用复核、3次Agents生产方法调用；旧36告警/134迁移保持，3key停用，无模型/服务变更。初次末尾快照断言失败原因未定，未重放工具而单独复核36容器/18卷一致；失败材料保留。来源读取成功、真实数据消费、数据行隔离均未验，下一项3A-01。

3A-01新增[规则抑制回执](3a-policy-suppression.md)：83项相关测试；真实PG run/event事务错误回滚/恢复，两个tenant/不可变输入/shadow与replay分开；真实SSL Kafka实际worker单分区3输入/1确认DLQ，提交位置1→1（无账本及DLQ则停止）→2（原位置恢复，不重发）→3。只更新并重启Agents，142锁依赖/源码hash对应，旧36告警/2Run/36事件及其他35容器/18卷/134迁移保持，3key停用；新增3回执含1合成revision的probe-only记录，失败探针保留。无新模型/厂商调用，常驻worker、真实模型分诊、初始group位置和完整3A仍待3A-02。

3A-02新增[真实模型分诊回执](3a-model-triage.md)：独立SSL测试group显式起点0，生产worker实际调用21网关→43；6成功回复6629/777/7406 tokens与Run/成本行一致、unpriced6/费用unknown，7Run含独立连接失败fallback。首轮标签污染中不足样例FP0.95不接受；另3条新盲测TP/BTP/needs_review，不覆盖旧Run。46原测试/66明确HTTP检查、同group重启position4/3/无新调用通过。PG shadow观察保证原告警人工状态不变，无真实动作；旧38告警/5Run/39事件等材料及36容器/18卷/134迁移保持，3key停用。缺失risk被当0、五类context401、MITRE名称错配/外部授权未核实是实测限制，完整质量不通过。

3A-03新增[风险分语义回执](3a-risk-score.md)：184项相关测试、33项HTTP检查；四类真实输入经API/SSL Kafka/Fusion/PG及生产worker投影分别为null/null/0/0.8，四行关联同一事件。一次真实21→43回复needs_review，自报0.95，1239/106/1345 tokens与Run/成本行一致、unpriced1/费用unknown。三服务定向重启后回查一致，旧45告警/12Run/52事件等材料及其他33容器/18卷/134迁移保持，3key停用；不重做数值评分。五类context401、引用质量与完整服务端基线仍未过，下一[3A-04组织记忆认证及失败语义](3a-org-memory-plan.md)。

3A-04新增[组织记忆回执](3a-org-memory.md)：194项测试、46项显式HTTP检查；真实API已复现并修复旧X头401/缺scope仍200，现每tenant reader正常、越权/写入拒绝，真实过期缓存2→1、强制刷新撤销401/无旧材料和恢复通过。工件位置真实PG除零使Run/事件/工件0/0/0，独立probe-only同Run恢复1/1/1且重试不追加；一次真实模型输入含采用语句并needs_review，1377/146/1523 tokens与账本一致、unpriced1/费用unknown。API/Agents重启回查及UID10001真实读取通过，旧49告警/既有账本、其他34容器/18卷/134迁移保持；3操作key停用，2枚A/B只读reader key保留30天。实际分析员编译写入、当时其余四类context、引用/整体质量未过；技能后续见下条。

3A-05新增[技能读取回执](3a-tenant-skill.md)：347项测试（API142/Agents205）、48项最终HTTP检查；旧Bearer/X头401已复现，实际Bearer/settings:read、tenant交集、写入拒绝、有效/过期/退休及当前版本解析、刷新撤销失败/无旧材料和恢复已验。生产选择方法验证rule/source/原始MITRE/平局/无匹配，保留加法权重；实际PG工件故障回滚及独立probe-only同Run恢复已验。一次HTTP→SSL Kafka→Fusion→worker→21网关→43实际模型采用skill-a-rule@v2确切文本及组织记忆，needs_review/自报0.95，1572/105/1677 tokens与Run/成本行一致、unpriced1/费用unknown；事后合成头v3未覆盖原v2事件/工件。API/Agents定向重启后工件保持，当前A读取v3、B读取v1、原model Run仍v2；旧50告警/15Run/57事件/20工件/14成本行及其他34容器/18卷/134迁移保持。3操作key停用401，2枚settings:read reader保留且200，原org凭据hash与alerts:read保持；首次verify及finish输出解析失败单列保留，受控恢复未重复重启或重发输入/模型。4条failed/probe-only FK行不是replay/编写/激活成绩，失败prompt投影不是第二次模型调用。该批当时KB/处置/身份仍401，deep investigation旧版本pin与完整质量未过；KB后续见下条，旧回执不改写。

3A-06新增[KB读取回执](3a-kb-read.md)：236项测试（API38/Agents198）及实际Bearer/knowledge_base:read、tenant交集/写入拒绝、PG全文匹配、缓存撤销后仍可用/强制刷新失败及恢复通过。生产SQL的真实PG检查核创建后、修改后cutoff分别排除1、总2且不双计；frozen reader只采用能证明有效的行，未重建旧正文。六条KB资料为直接合成读样例，不是生产SOP或已有向量索引质量。

一次真实ingress→SSL Kafka→Fusion→worker→21网关→43模型，实际prompt7861字符、未截断，包含KB1及既有org/skill块；模型needs_review/自报0.95，1955/140/2095 tokens与CostTracker/Run/成本行一致、unpriced1/费用unknown。model_citations=[]、unresolvable_citations=[]，只能证明来源已提供，不能称引用质量通过。初次8717及第二次8105的预算预检均无模型，随后只压缩本批合成文本/标题并保留旧新hash/时间，再等义精简KB inline note，检查点恢复未重发告警或追加模型。prompt-v2测试197过/1原措辞断言失败保留，恢复原短语后prompt-v3的198项通过；API38项保持通过，没有删断言或扩运行依赖。

真实PG在KB工件INSERT处除零使probe-only Run/事件/工件0/0/0，同Run恢复1/1/1、重复不追加。模型Run有2事件/5工件（org、skill、KB读取与prompt/response），probe-only另1事件/1 KB工件；首次事务、hash及API关系和API/Agents定向重启回查保持，其他34容器/18卷/134迁移保持。旧51告警/17Run/60事件/25工件/15成本行、6 shadow配置/10决策/2规则/5 org/10技能/12版本/4 failed FK材料全部保留；新增1告警、2Run（含probe-only）、3事件、6工件、1成本行、1 shadow决策及6 KB行，总告警52。3操作key停用401，2 KB reader保留且200，原org/skill四枚key及env/mount/hash/scopes保持；非root重启后A/B KB各1、org均success、skill A v3/B v1。该批十五层定义，当时处置/身份两类reader401及完整质量未过；处置后续见下文。


3A-07新增[近期处置回执](3a-dispositions.md)：最终396项（API91/Agents305）及60项显式HTTP检查；五条合成反馈在真实PG/API核同rule优先于更新entity、A/B隔离、空集/写入拒绝及创建cutoff仅1条/排除2条。实际撤销后缓存仍成功、TTL0刷新401无旧材料与恢复，闭合URL失败恢复通过；异常payload/时间echo为单元/投影证据。生产SQL的同PG会话SAVEPOINT错误/恢复不等于HTTP或共享PG outage验收；无DDL/约束放宽。

一次真实ingress→SSL Kafka→Fusion→无group/无commit捕获→生产worker→21网关→43，三条个人意见/1336字符块进入7355字符的完整safe-call输入，原org success、技能读取success但selection no_match、KB no_match。模型needs_review/自报0.65，1779/130/1909 tokens与Run/成本行一致、unpriced1/费用unknown；note和反馈ID精确提及均0，rationale概括参考不证明因果采用或质量，未追加调用索取引用。模型Run2事件/6工件，独立probe-only故障回滚0/0/0→同Run恢复1/1/1且重复不追加；该失败投影没有调用模型。

初394项通过后收尾独立进程导入出现ImportError，保留失败raw；移除新reader对app.agents包初始化依赖，用两种新进程导入顺序核对固定的闭合词表与原件一致，最终396项通过。仅Agents额外重建为90126c76，常驻非root读取处置A3/B1及原org/skill/KB均成功；模型及成功重启工件核对来自首48407679镜像，最终镜像模型未重测。后半只读检查点恢复无新重启、key mutation、输入或模型；不是全首次通过。

旧52告警/19Run/63事件/31工件/16成本行、6 shadow配置/11决策/2规则/5 org/10技能/12版本/4 failed FK/6 KB全保持；新增1告警、2Run（含probe-only）、3事件、7工件、1成本行、1 shadow决策、5反馈，总告警53。其他34容器/18卷/134迁移保持，只更新API/Agents，三操作key停用401，两枚新alerts:read reader保留200，原六枚reader凭据和权限保持。该批十六层定义，当时身份reader401，后续见下文；created cutoff不是反馈编辑历史，完整调查/质量及常驻消费仍未过。


3A-08新增[身份读取回执](3a-identity-read.md)：496项（API108/Agents388）、62项HTTP；Bearer/graph:read/严格图tenant、27合成节点/22关系、native cutoff先filter再limit及图源配置移除503/查询错误恢复已验。7候选只1可采用，晚3/未知3；全部业务历史未知，后来修改部门/经理两属性不能由旧split还原。图READ_ACCESS非DB只读角色，未加TLS或通用初始化。

一次真实HTTP→SSL Kafka→Fusion→worker→21/43，身份1进入6931字符完整prompt；needs_review/自报0.65，1646/135/1781 tokens与账本一致，unpriced1/费用unknown，模型提及单列观察，来源ID/路径hash供工件追溯，不作因果质量。模型7工件、独立probe1；真实PG工件回滚/恢复/重复及API/Agents重启保持。首after脚本TEXT绑定UUID失败时无输入/模型，仅修operator后从旧矩阵继续，初版无独立source/hash备份，失败raw保留。

旧53告警/21Run/66事件/38工件/17成本行全部保持；新增后54/23/69/46/18、shadow决策13，其他34容器/18卷/134迁移保持。图与history探针后快照全hash一致。三操作key401、两新reader200，原八枚和四类原查询保持，该批五类reader接通/十七层；后续3A-09见下文，完整质量与常驻准入未过。


3A-09新增[受控复验回执](3a-triage-admission.md)：三个固定中性输入原样经HTTP/SSL Kafka/Fusion/生产worker调用真实模型，实际prompt6484/7086/6421字符，TP/BTP/needs_review，4841+382=5223 tokens、unpriced3/费用unknown，51项显式HTTP（另3最终poll及SDK内部请求分列）。分类3/3但p01时间窗/未授权理由不受支持，完整质量不通过。每例2事件/7工件及五类来源/实际messages/hash/usage/手工状态关系已核；p02身份1且授权只来自合成CR。

真实broker7 publish/8 delivery，五次模型方法替身加一次失败fallback、无额外真实模型；实复现schema/ledger False静默commit、冷重入方法，暖重投通用Run变化、PG暖恢复五类来源皆not_requested。PG错误且DLQ未确认offset0，恢复或实际确认后1；同group短时idle无新处理，不外推崩溃/rebalance。三例质量和broker替身证据分开，worker准入不通过。

旧54告警/23Run/69事件/46工件/18成本行与知识材料保持，新增3告警/5Run/8事件/31工件/3成本行/5 shadow决策，该批后57/28/77/77/21、shadow18。36容器/18卷/134迁移保持，无运行改动/重启，十枚reader保持、三操作key401。broker导入及finish错误保留，finish首次完整stderr未独立保存；只读恢复无重复副作用。后续3A-10-01见下文，[总计划](3a-worker-reliability-plan.md)其余子项仍规划。

3A-10-01新增[持久确认/坏消息回执](3a-triage-durability.md)：143项窄测试、26项显式HTTP，单次真实认证HTTP→SSL Kafka/Fusion→PG告警及7次独立broker发布/8次交付已核；4次模型方法替身、0真实模型/0新成本行。旧镜像坏schema和ledger False静默commit已复现，新镜像schema/缺ID先拒绝并真实DLQ确认后提交；无pool且DLQ未确认offset0，仅恢复DLQ确认后同消息到1，pool仍None。未知UUID tenant先方法后真实PG FK失败，不证明模型前授权。正常Run/一事件/五来源工件与实际读取相同，无伪造prompt/response/usage；重启/API/手工状态保持。

旧57告警/28Run/77事件/77工件/21成本行及14表材料保持，新增后58/29/78/82/21、shadow19。仅Agents更新为24071dd2并完成一次同容器重启，35其他容器/18卷/134迁移保持；18 Compose层、十枚reader保持、三操作key401。初次136通过/7新增替身失败及部署Env顺序断言保留；只修新增测试和operator，部署恢复不再构建/重建。该批当时冷重投/缓存来源/SDK预算及p01质量未修；后续普通live保护见下文，完整准入仍未过。

3A-10-02新增[首次结果/重投保护回执](3a-triage-recovery.md)：207项首轮窄测试、55项显式HTTP（6 ingress链检查+49 finish）。三条真实HTTP→SSL Kafka/Fusion→PG信封进入6个新topic/5group，3次发布/7次交付/3次方法替身，0真实模型。真实工件SQL除零后只有claim/start保留，DLQ未确认offset0；同worker仅恢复保存，完整persist tuple/hash及五来源工件保持且reader/方法不重进。fresh进程复用完成结果不改产品；独立OS进程实际重叠只有A进入方法，B unknown确认DLQ；开始后exit23的新进程同offset不再调用。真实PG lookup错误/恢复、Btenant claim拒绝已核，p01旧真实Run只读lookup保留1687 tokens/unpriced1、缺失字段unknown，无重放。

旧58告警/29Run/78事件/82工件/21成本行及14表材料保持，新增3/3/5/10/0后61/32/83/92/21、shadow21。两完成Run重启前后整产品相同，unknown开始事件保持；默认时间线[-1,1]可读、负cursor真实422，reaper状态变化不授权重调。仅Agents更新f7737abd/十九层、17源码层，35其他容器/18卷/134迁移保持，十枚reader原文件/hash/metadata/scopes保持、三操作key401。无失败恢复/重跑；SDK预算、负cursor与p01质量仍阻止完整准入，下一3A-10-03。

3A-10-03-01新增[请求/cursor回执](3a-triage-request.md)：实际SDK默认root retry2/timeout None已重现并修至0/45；整次await45秒截止，真实API既有start-only cursor由422修至200。189项相关测试（含实际SDK/HTTP替身，非真实43故障）、71项显式HTTP与API/Agents重启回查通过，0新输入/模型。14表旧材料、十枚reader、34其他容器/18卷/134迁移保持；完整03/质量/worker准入未过，下一03-02。

3A-10-03-02新增[持久额度/停止回执](3a-triage-budget.md)：263项测试、137项真实API检查、6次broker发布/14交付、5次HTTP模型替身开始、0真实模型。项目库备份在独立临时库恢复并核旧14表/134迁移；新增一独立预算表。原子claim/预约、三类上限、跨进程重叠、同group积压恢复及10.012917秒stop在所列边界通过。5预约/100000预留单位非实际usage，三未知及A积压保留；旧材料、35其他容器/18卷/十reader保持，三操作key401，当前21层Agents更新。失败与显式调额度保留，完整质量/worker准入仍false。

## 3A-11-01最新只读准入复核

3A-11-01只读准入复核已完成，见[回执](3a-admission-review.md)：旧p01时间/授权错误未被indicator gate识别；常驻Agents审批提案guard实际True且缺Kafka bootstrap/TLS，旧调查工具身份仍缺。三未知预约及A积压保持，0模型/消息/offset提交/运行改动；完整准入未过。下一[3A-11-02配置补齐](3a-triage-admission-config-plan.md)，保持worker禁用，然后单独修提示词/复验质量。

审批提案guard未显式禁用、常驻Agents缺Kafka bootstrap/TLS；worker关闭使其未作为常驻消费者运行，隔离探针通过不证明这些环境项已接。五reader不替代旧工具service身份。旧回执保持；本批无运行改动，三未知预约及A积压不清理/重调。

## 3A-11-02最新配置验收

3A-11-02常驻分诊配置补齐已限定验收，见[回执](3a-triage-admission-config.md)：仅Agents同镜像重建一次，新增四项环境值，复用原只读CA；审批提案guard现False、Kafka SSL/主机名校验及六组offset读取通过。旧14表/三unknown/A积压/十reader/其他35容器/18卷/134迁移保持，0模型/消息/提交。当前22层、19源码层，worker仍OFF；下一[3A-11-03理由提示词修复](3a-triage-reasoning-plan.md)，完整准入/质量未过。

当前补齐的是transport及审批提案禁用，不含常驻topic/group/DLQ项目映射；五reader与通用工具身份仍分开。A积压与unknown不清理/重调；p01理由仍未修，不能将配置就绪当质量或常驻准入。


## C01最新限定验收

C01（[回执](c01-fusion-delivery.md)、[JSON](c01-fusion-delivery.json)）已限定验收并经独立结束/撤key后审计：107项测试，真实PG/Redis/SSL Kafka故障接缝和首次快照恢复、部署后HTTP；6项HTTP、17次发送尝试/16确认、23次物理交付与回读含审计4次，0真实模型。两类探针失败与恢复、两次计数补充均保留；不能外推永久unknown、全Redis丢失、旧无snapshot历史恢复或整体迁移完成。

C03-02受控停止证据见[回执](c03-triage-quality.md)：1真实模型/1998 tokens，实际needs_review/0.65未达冻结TP/理由判据，后三例停止；技术PG/API/usage/offset通过。原启动权限失败在业务发送前，独审后只改脚本读mode；3新操作key已撤销401，当前运行与25/22层保持、workerOFF。不以收尾审计通过代替四例质量或完整迁移通过。

C03-02B新复验见[回执](c03-triage-quality-recheck.md)：新case01一次真实模型1808+110=1918 tokens，TP/.95分类与技术持久链通过，但无据断言未授权违反冻结理由判据，后三例未发。3操作key已停用/401，0运行变化/重启/DDL，旧6预约/3unknown和十reader保持；当前累计7预约/140000预留单位，非实际usage。下一另卡0模型最小授权澄清后再冻质量输入，worker仍OFF。

C03-02C-01见[回执](c03-triage-authorization.md)：v4末条/lock最小澄清、88项直接测试、四个断网SDK完整body7754–7814字符/7669–7729字节；同A五源fixture构造，不称四次真实reader或模型质量。0真实模型/业务写/broker，仅Agents更新，当前26/23层、184/769Py及lock对应。早期observer import副作用保留112新增计数并归本批（104只读SQL/4 metrics，非整批总量），原B844冻结字节保持；修订后不再追加旧目录。旧7预算140k/3unknown和十reader等保持，worker OFF，下一另冻新质量输入。

C03-02C-02见[回执](c03-triage-authorization-quality.md)：C03-02C-02三例实际模型共5971 tokens：前两例分类/理由通过，第三例把缺少转移证据误判为FP并推断规则误报，按冻结判据失败停止，第四例未发。三操作key已停用且实际401，技术持久链与结束独审通过；新增3告警/Run、9事件/21工件/3成本/3shadow、3responded预约60000单位，0QA。旧7预约/140000单位/3unknown保持，累计10预约/200000单位；26配置/23源码层保持，0重启。第三例原始FP保留于Run/Shadow，Alert仍new/disposition null、auto_closed false，不声称已发生错误关闭。下一C03-02D-01只澄清“无法核查检测条件不等于规则误报”的最小提示词边界，先做0真实模型直接验证和独审；不重调旧三例、不改旧判据。理由/分类质量与常驻准入仍未过，worker OFF，整体迁移未完成。

C03-02D-01见[回执](c03-triage-detection-validity.md)：v5检测有效性提示词及lock已限定验收：88项直接测试、4次断网生产SDK完整body（7827–7917字符/7742–7832规范UTF-8字节），0真实模型/新业务写。仅Agents一次更新至9cb719，原env/七只读挂载/60秒停止宽限保持，当前27配置/24源码层。旧14表、10预约/200000预留单位/3unknown、十reader、其他35容器/18卷/134迁移保持，部署前/运行/收尾三审通过。三份transport材料复用实际存储快照、第四份为未执行输入加A资料的构造体，均不是新reader/模型质量证明；stage执行前失败与父标签勘误保留。下一C03-02D-02另冻四条新对照输入，验证有反证FP、明确授权BTP、缺证NR及事件窗外NR；本四例不复验v5 TP，后续常驻新TP仍须实际独审。旧三批质量失败与七条未发输入保持，worker OFF，质量/常驻及整体迁移未完成。

## C03-02D-02新对照质量结果（受控停止）

[回执](c03-triage-validity-quality.md)、[JSON](c03-triage-validity-quality.json)及[证据清单](../handoff/c03-triage-validity-quality-evidence-manifest.json)：质量失败后已受控停止并完成结束、撤key后及封后独立审计：两次真实模型回复共4081 tokens；case01 FP分类/理由通过，case02时区换算错误且把窗内已授权活动判为FP，分类/理由失败，case03/04未执行。三操作key已停用并逐枚真实401，十reader及旧10预约/200000单位/3unknown保持。新增2告警/Run、6事件、14工件、2成本/2shadow、2responded预约40000单位，0QA；预约单位不是usage。告警仍new、auto_closed=false，不声称发生错误关闭。当前27配置/24来源层、184Agents/769运行Py及lock保持，0源码/Compose改动、0重启/DDL。首次发送前因本地验收算子遗留旧输入SHA/v4合同被拒绝，0业务/模型；原失败、旧stop与显式恢复审计/独立断网合同probe/新质量stop全部保留，未重复freeze、身份、额度或topic，不重调旧输入。本批6次发布尝试中raw/首次fused/quality各2；临时消费者直接交付4条，常驻raw处理推证2个slot，共6个已用/保留交付slot，不当成全部consumer yield实测。共享真实HTTP entries/reserved slots为96、Mock预检2；显式host SQL helper962次，并非全服务SQL。独审累计54只读PG/5HTTP，其中5HTTP已经包含在共享trace，不重复相加；封后审计0新增PG/HTTP。真实模型1989+2092=4081 tokens，美元成本未知。下一先另冻人审profile新准入计划，尚未实施或验收；原自治分类/理由质量及常驻准入未过，worker OFF。原C03质量硬门和本批判据保持，C04/C05调查/知识及后续响应仍待逐批验收，整体迁移未完成。
