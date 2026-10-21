# 3A-08：身份上下文读取、失败状态与时间边界

状态：**本批限定验收完成。** 实际结果见[3A-08回执](3a-identity-read.md)及[结构证据](3a-identity-read.json)。以下保留实施前规划、现场合同及时间限制；不能据此宣称HR历史、完整调查质量或常驻worker准入通过。下一项为[3A-09受控分诊复验与准入规划](3a-triage-admission-plan.md)。

本批只处理已有告警中账户的身份上下文读取：认证 → 已有图中按账户查询 → reader port → 实际采用文本 → 模型与持久工件。不建设HR/身份采集、原始事件检测、全量目录同步或身份分析生产系统；不把PG员工/权限视图、既有图节点或Neo4j端口可达写成本路径已消费。

## 实施前静态核实的路径与缺口（历史）

| 位置 | 实际实现及影响 |
| --- | --- |
| [Agents identity reader](../../services/agents/app/context/identity.py) | `fetch_identity_context`发共享X头；`AISOC_TRIAGE_IDENTITY_TTL_S`默认**300秒**。缓存键含tenant/cutoff/limit/accounts，未绑定URL或凭据，且**先命中缓存，再检查token**。关闭、缺tenant/账户/token、HTTP/连接/JSON错误都可呈现空`IdentityContext`；仅有列表不能证明已查询且无匹配。 |
| 同文件`accounts_for`、`_shape` | 按现有principal字段及affected_users取账户，归一化后默认最多5个；不查hostname。`_shape`容忍坏行、未验证tenant/账户/echo/数据类型，计数强转可能抛错；没有稳定源节点身份、来源指纹或确切采用文本。 |
| [API graph](../../services/api/app/api/v1/endpoints/graph.py) `identity_context_for_triage` | `GET /graph/identity-context`仍仅校验共享X头，tenant来自请求，无Bearer交集及明确读取permission。它不使用PG查询身份材料，不能将PG RLS当作图隔离保证。认证通过后调用当前图读取helper，再在Python按import stamp过滤。 |
| [图读取helper](../../services/api/app/services/incident_context.py) `get_identity_context_for_accounts` | 查询Neo4j的`Identity`→`Employee`→`Department`/经理，账户仅匹配`lower(i.external_id)`，有8秒查询超时。任何驱动未初始化、连接、鉴权或查询错误被捕获后返回`[]`，与真实无匹配混同；API认证修复后仍可能假报正常空结果。需同时修这条直接读取边界。 |
| 同文件`_IDENTITY_BY_ACCOUNT_CYPHER` | 当前不返回源节点ID，`DISTINCT`作用于展示字段；相同账户可有多个provider/员工关联。无明确排序，`LIMIT`发生在API的cutoff过滤**之前**，晚导入行可占满候选而遮住其后的可用行；拒绝数也只覆盖已返回候选。不能据此声称全量无匹配或完整历史。 |
| 同文件`_scoped` | 复用的通用谓词允许`tenant_id`相同或节点带global reference label。该例外是其他图维度的约定，身份链不应因混合标签跨tenant。实施时核Identity/Employee/Department/经理每个节点的严格tenant条件及跨租户边，必要改动只限本账户查询。 |
| [目录导入](../../services/api/app/services/context_import.py) | Employee以tenant前缀ID MERGE并原地更新，`updated_at=datetime()`是导入时间，返回为`imported_at`；不是HR事实有效时间，也没有旧正文版本。`is_active`由end_date是否存在推导，不代表查询时仍在职或活动获授权。导入只关联已存在Identity，不会创建尚未出现的账户节点；缺链接不是账户不存在的证明。 |
| API `_imported_at`及response | import stamp晚于split被排除；缺失/不可解析stamp原版仍保留，所有保留行都计`without_timestamp`，说明**业务事实历史有效性无法验证**。比较时可转Neo4j DateTime，但原row仍可能带驱动类型；实际HTTP序列化、UTC规范化及hash必须另核。 |
| [Neo4j初始化](../../services/api/app/db/neo4j.py)与1F配置 | 现有初始化会连接校验并自动运行图schema迁移；1F配置显式`AISOC_DISABLE_NEO4J=true`。当前实际URI、驱动状态、共享库/图对象及可用性尚未本批核验，不能直接打开初始化并向共享图写迁移来凑正例。 |
| [worker](../../services/agents/app/workers/fused_alert_consumer.py)、[frozen reader](../../services/agents/app/replay/shadow.py) | worker在空或失败时直接返回；state无独立读取失败来源。frozen向reader传split，但目前只累计echo缺失等统计后仍可交付rows，缺少拒绝未honour结果的独立守门。 |
| [分诊prompt](../../services/agents/app/agents/auto_triage_agent.py) | 身份字段多次清理/截取，默认5条、主要字段120字符，employment/end date40字符；整块实际还有3000字符上限。state中的完整记录可能多于模型看见的文字。现有“描述账户持有人，不等于活动获授权；可能过时”措辞必须保留。 |

这些均为本地源码事实；上游对“已导入”“append-only”“freeze”的描述不能代替本项目实测。

## 权限与连接方案

候选最小读取scope为已有`graph:read`：它在[权限目录](../../services/api/app/core/rbac_catalog.py)存在，[graph WS](../../services/api/app/api/v1/endpoints/graph_ws.py)也明确使用该权限。旧graph HTTP有些路由只检查登录，不是可复制的授权标准。**viewer和静态api_service并不默认持有graph:read**；[身份解析](../../services/api/app/api/v1/deps.py)优先核API key显式scopes，实施时以真实拒绝/允许路径确认，不为迁就角色扩大权限或复用旧万能key。

拟新增独立`AISOC_TRIAGE_IDENTITY_KEYS_FILE`及受控tenant→key映射；只配置A/B测试tenant，每key仅`graph:read`。保留组织记忆、技能、KB和近期处置各自key、权限、env与目录；不回退其凭据或共享token。目录0700、文件0600、UID/GID10001可读、只读目录挂载、正常非root运行。短时操作身份与常驻reader分开准备，精确到期、停用及读取状态在实际回执记录。

操作前先只读核21既有Neo4j的镜像、edition、database、账号权限、节点/关系归属及项目可用连接。优先复用已提供的服务和受控配置；若需要启用只读连接，先明确最小初始化方式，避免调用现有会执行schema迁移的启动路径。隔离按实际数据库能力和每节点tenant谓词验收，不把共享账号、只读调用或非root误写成数据库级租户隔离。不能复用时先交付明确`unavailable`及原因；不以开启采集、植入全量事件、复制旧图或清空共享库替代已有来源合同。

## 本批最小实施范围

1. 内部GET改为标准Bearer、`graph:read`及tenant交集，省略tenant取自身；拒绝越权后才绑定同一tenant查询。旧X头不授予权限。图查询中Identity、Employee、Department及经理均须严格同tenant，不向其他图维度扩展认证重构。
2. 图helper增加明确成功/空集/不可用结果或等价受控失败接口，保留既有列表调用者的兼容投影；路由与Agents不得把驱动未初始化、超时、连接/鉴权或查询错误当`no_match`。图源状态与HTTP transport状态分别保存，日志不输出凭据或不受控HR原文。
3. 保留`IdentityContext`及现有`fetch_identity_context`/reader port，增加typed读取事实：status、reason、tenant、账户/limit、source、read_at、请求/实际cutoff、cache来源/年龄/TTL、HTTP及图源状态、返回/采用/排除/无法验证数量。缺账户是未请求，真正成功空集才是无匹配；“仅找到Identity但未关联员工”不得写成账户不存在或异常事实。
4. 映射在缓存前校验，缓存按tenant/URL/凭据hash/归一化账户/limit/cutoff隔离。默认**300秒保持**，刷新失败不采用过期材料。实际API端单独撤销/到期或图数据改动仍可能在有效缓存期后才生效；强制TTL0故障探针不能算默认即时撤销。
5. 只补本查询需要的稳定源节点ID、provider/account及明确关系来源，区分同名账户、多provider/多员工关联、缺员工/部门/经理与字段未知。归一化Neo4j日期/布尔/字符串为可审计JSON，再生成当前投影hash；它不是历史版本ID。保留原字段及显示来源，不凭当前职位、离职日期或空字段推断本次活动授权。
6. 形成确定的候选排序、limit与cutoff先后合同。优先在同一生产查询按导入cutoff过滤后再选择稳定排序的有限结果，并分别记录排除；若受限读取只能计算候选子集，就明确计数范围、截断/partial，不能说全图无匹配。查询仍仅针对所给有限账户，不扩成全图扫描。实施前记录选择，不默默改返回集合。
7. 统一字段清理、采用预算及渲染：默认最多5条，主要字段120、employment/end date40，最终整块不超过原3000字符并保留完整advisory。记录原/采用字段hash、截断/拒绝事实、实际采用节点/账户及确切block/hash；auto不再二次裁剪后留下不相符来源。正常模型样例在发起前按真实messages JSON核完整8000字符账本上限，超限在模型前停，保留检查点。
8. 拟新增`identity_context_read` state/verdict payload及独立工件，与原四类来源沿首次verdict事务保存；实际字段名在实施前与测试统一。同Run重试不替换/追加，工件错误回滚；不外推整个Run/alert完全冻结。旧图资料、旧反馈/KB/技能/组织记忆及已冻结工件不改写。

预计源码限API `graph.py`、`services/incident_context.py`及必要的只读Neo4j连接适配；Agents `context/identity.py`、reader port、frozen reader、state、worker、prompt、ledger，以及本批直接测试/叠加操作文件。默认无PG DDL、运行依赖或评分算法变更；连接初始化或查询合同若扩大范围，先在本计划说明原因/影响/验收再实现。

## 时间语义必须分开记录

`imported_at`仅是当前Employee投影的导入时间；不能把它命名成HR生效日、观测到的离职时刻或整条关系路径的版本时间。部门/经理/Identity各自属性和关系也可能在之后被改写，单个Employee stamp不能证明全条路径在split前成立。

live允许读取当前导入材料，但prompt必须说明它描述持有人、可能过时、不是本次活动的授权证明。frozen必须核echo确为split、拒绝已知晚导入以及无法比较的返回，保留原拒绝/无法验证计数；不得由caller或当前时间伪造cutoff。若保留原“import cutoff后的部分上下文”能力，read/prompt/method note须明确`import_cutoff_only`、业务历史无法核实，并继续把全部采用行计入`without_timestamp`，不能因有import stamp将该计数置零。缺stamp与全部业务历史未知是两个概念，可加独立数量说明。

本批不承诺重建后来被编辑的旧HR正文或关系。严格历史质量评估不能把这类partial材料当作已证明split前的证据；需禁用该源或单列其限制。未知/错误echo不得仅计数后继续采用；未来若要完整历史合同，需要独立版本/有效期来源，另立批次，不能在此伪造历史。

## 输入 → 实际调用 → 验收

| 输入/故障 | 实际中间产品 | 通过条件与边界 |
| --- | --- | --- |
| A/B有相同账户、不同合成员工/部门/经理，另有跨tenant边/混合global标签负例 | 标准Bearer→生产Cypher，图中每节点tenant绑定 | 两边都真实非空且各得自身；跨tenant请求403，跨tenant路径不泄漏。无假“空租户隔离成功”。 |
| reader最小scope、缺scope、匿名、坏key、仅X头；reader尝试ingress/目录导入 | 真实API认证链 | 自身读取200；缺scope/越权403、无身份401；写入拒绝。只读身份不负责准备样例，不扩大旧reader scopes。 |
| 真实空集、缺账户、Identity未关联员工、多provider/多员工、active false/true/unknown | 同一实际查询、typed reader及prompt投影 | 无匹配、未请求、缺字段、歧义/partial分别可辨；不把空结果当异常账户，也不把active/title当授权。 |
| 缺配置、错tenant映射、有效cache后撤销、TTL0刷新、关闭、closed URL及图驱动查询失败/恢复 | reader、生产图helper及独立探针 | 明确unavailable及层次原因，无旧材料冒充成功；恢复可重读。禁止关闭共享Neo4j或清图制造故障；独立替身/真实图事务故障分列。 |
| split前后import、不可解析/缺stamp、晚改经理/部门、超过limit后仍有旧候选 | 生产查询→API counts→frozen port | echo/排除/计数范围真实，未honour不采用；保留业务历史无法验证事实，不能把当前路径声称完整历史。 |
| 长账户/职位/部门/经理、控制字符、预算边界 | 一次清理与采用→实际完整advisory块 | 各字段/整块限制保持，采用字面值/hash与真实prompt一致；未提供字段不能写成已提供来源。 |
| 一条新的标记告警及少量合成身份上下文 | HTTP→SSL Kafka→真实Fusion信封→生产worker→21网关/43一次调用 | 真实账户查询与采用ID/文本进入prompt；模型引用、反驳或未提到均记录，不预定分类、不追加调用。旧已接来源各按自身查询验证保持，不要求同一告警把所有材料拼满。 |
| 新读取工件插入故障、同Run恢复/重复及定向重启 | 实际PG账本事务→API工件/事件/hash回查 | 无孤立verdict/工件；恢复及first-write关系正确；只重启所需API/Agents，旧图/PG/其他容器/卷/迁移保持。 |

图样例仅新测试tenant/专用ID与少量关系，标明synthetic，不使用真实员工隐私或整目录导出。先保存现有对象摘要；若通过context import准备，明确已存在Identity的前提与导入报告，只验证这次指定样例，不外推生产HR同步。任何图数据写入均限定本批新对象，保留材料，不用MATCH全库删除或清卷恢复。

优先复用[Agents处置与身份测试](../../services/agents/tests/test_triage_dispositions_and_identity.py)、[replay leakage](../../services/agents/tests/test_replay_leakage.py)、[API triage context](../../services/api/tests/test_triage_context_routes.py)、[incident context](../../services/api/tests/test_incident_context.py)、[graph tenant isolation](../../services/api/tests/test_graph_tenant_isolation.py)及[context import](../../services/api/tests/test_context_import.py)直接相关部分；只补本批正常/关键边界；复用3A-07教训，若读取器引入新的包依赖，补独立新进程的reader先导入/worker先导入验证，避免同一pytest进程预加载掩盖循环。替身、真实图、真实PG与真实模型分别记证据，不做默认全仓回归。

退出交付来源差异、图连接/对象归属、实际API/图/采用文本/账本/usage、key生命周期及定向恢复回执。当前最小scope和连接是本地核对后的方案，真实可用性、图隔离、计数/时间语义、预算、模型消费及旧材料保持均**待实测**；常驻worker、自动graph编排、审批、真实响应和完整调查/知识质量继续不在本批完成声明内。

## 现场核实后的本批合同

21实际Neo4j5.15.0 Community的neo4j库在线，开始时0业务节点/0关系、2个默认lookup索引、无约束；全量schema初始化仍禁止。Community账号没有独立只读角色隔离（[官方权限说明](https://neo4j.com/docs/operations-manual/current/authentication-authorization/manage-users/)）；本批受控复用已有图凭据，仅向API挂载专用配置，Agents只持本接口graph:read凭据。不能把READ_ACCESS会话、硬编码读取查询和每节点tenant谓词当作数据库级租户/只读账号隔离。现有Bolt入口未新增TLS或端口，不外推图传输/生产安全通过。

API保持AISOC_DISABLE_NEO4J=true，新get_identity_read_session按专用AISOC_IDENTITY_GRAPH_CONFIG_FILE文件每请求建立READ_ACCESS session并退出关闭，无global driver、init、schema或共享图重启。新配置在private/identity-graph-3a/config.json（UID10001/目录0700/文件0600）只读挂/run/secrets/identity-graph；旧API配置及四类Agents reader八枚key保持。缺配置抛IdentityGraphNotConfigured，服务端只回受控失败原因。

账户专用Cypher先按所有节点严格tenant匹配及节点路径去重，再分类Employee导入stamp、过滤、稳定排序和limit。只把实际native ZONED DATETIME计为可验证stamp；live可采用missing/unsupported文本stamp并明确unknown，frozen保守拒绝这些行，分别计excluded_unverifiable_import，已知晚导入计excluded_after_cutoff。这是对原partial放行语义的明确收紧，不强行解析坏日期。所有返回行仍计without_timestamp，表示业务历史未知；采用预算另记adopted_without_timestamp。candidate=eligible+两类排除，eligible=returned+truncated；import_timestamp_missing仅候选中的缺stamp，不含unsupported。

响应新增source_status/source_reason及上述计数，200成功/合法空集，图失败503同形JSON；reader另记HTTP与图失败层级。当前行投影包含四类节点业务ID/elementId及kind、account/provider、原展示字段、employee_linked、关系类型来源、native UTC imported_at/status、原stamp hash；row_source_sha256为scoped tenant加全部规范投影字段的sortkeys/紧凑JSON/UTF8摘要，不含自身，不是历史版本或完整图事实证明。

合成图样例仅本批A/B tenant节点/关系：同账户不同tenant、active true/false/unknown、未链接员工、多provider/多员工、跨tenant边和混合global标签、limit前的晚/缺/坏stamp，以及独立历史路径的后来部门/经理修改。后者须展示单Employee旧stamp不能恢复路径历史，不能声称完整冻结。模型用svc-identity-a/R-IDENTITY-A/IDENTITY-HOST-A，无MITRE，旧skill/KB/处置自然无匹配；旧四能力按原查询分别保持。一条新HTTP→Kafka→Fusion→worker→43模型；模型前完整JSON8000预算不变，不预定结论或追加调用。

## 实施结果

最终496项测试（API108、Agents388）及62项显式HTTP检查通过。共享图原0节点/0关系，仅新增27个标记节点/22关系，保留2个lookup索引与0约束。API专用连接、strict tenant、native import筛选先于limit、图查询故障/同session恢复、实际HTTP503无材料与配置恢复均已核；仅两处本批历史样例属性改为v2，证明Employee旧stamp不能还原整条路径。全部业务时间unknown仍保留。

一次真实Fusion→worker→43模型，完整prompt6931字符/身份路径1条，needs_review/自报0.65，1646+135=1781 tokens/费用unknown，网关resolved_model字段仅aisoc-triage别名。独立PG工件故障回滚/同Run恢复与API/Agents定向重启回查通过；原53条告警和既有账本、旧八枚reader及原查询、其他34容器/18卷/134迁移保持，常驻worker/graph/审批/真实响应关闭。

首轮验收脚本在成本表TEXT run_id绑定UUID处失败，尚无probe写入、告警或模型。修正探针str绑定后，从既有matrix检查点继续，未重复矩阵/身份撤销或已受理输入；生产runtime和496项已通过源码未变。失败日志及检查点保留；初版新验收脚本未另存文件/hash，不伪称完整冻结的初版源码，当前清单核最终脚本。下一3A-09仅规划，整体3A及服务端基线未冻结。
