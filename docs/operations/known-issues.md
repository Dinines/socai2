# 已知问题与适配边界

先保留原版进行实际验证；以下用于选测试和记录缺陷，不自动触发大规模架构改造。

以[当前服务端范围](alert-processing-scope.md)筛选直接风险。独立UEBA训练/特征生产、原始事件检测和前端展示相关条目仅保留上游事实；本轮只验证告警处理及已有上下文的读取/消费，不将所有风险自动列为实施任务。

## 已修复的 20 部署阻塞

| 问题 | 已有适配 | 使用前要核对 |
| --- | --- | --- |
| 三条 embedding 默认模型/维度不一致 | 统一到本地 qwen0.6b 原生1024维，新建独立集合 | source hash、模型指纹和当前集合，不能混写旧向量空间 |
| Qdrant 进程 nofile1024 导致集合创建失败 | Compose soft/hard65536 | 重建容器后核实际进程 limit，不只是 shell 值 |
| SDK1.19.1 无上游调用的 search | 两处检索改用服务端 HTTP points/search | 仅当前实际操作已测，不宣称所有版本/API兼容 |
| 旧 TI 向量抽查为全零 | 1,748公开记录重新嵌入，原payload/ID保留 | 没有原始输入文件时不能盲跑 reindex |

## 当前迁移计划的直接检查项

以下按固定源码核对；1B/1C、1F、1D及1E实际结果已补充，其余仍为静态检查/待验。分别进入[批次执行卡](dependency-migration-plan.md)，不把规划写成通过证据。

| 批次 | 源码现状/风险 | 计划处理与通过判据 |
| --- | --- | --- |
| 1B | 原initdb脚本缺SQL挂载/空目录时可退出0；134份SQL有同编号不同文件 | 1B使用受控共享库执行器，134/134原SQL及ledger集合一致；原init脚本仍保留，不将其退出0单独视为成功 |
| 1B | `20_runtime_role_password.sh` 的psql `SELECT set_config(...)` 返回密钥值，默认输出可能进入初始化日志 | 1B原版哨兵输出→补丁静默→原版负对照通过；真实凭据补丁输出不含密码。原件保留，生成副本及差异记录见[1B回执](1b-shared-services.md) |
| 1B/1F | runtime角色非superuser不等于tenant隔离；原RLS保留未绑定上下文的跨tenant worker语义 | 1B实际确认绑定读写/越权拒绝，未绑定仍可跨tenant读取。1F受理HTTP身份/权限、跨tenant拒绝及两租户读隔离已实测；不外推所有路由或broker权限 |
| 1C/1F | 21现有Kafka只有PLAINTEXT，无认证；原resolver拒绝production/staging明文 | 1F新增19093 SSL listener，CA/IP验证及无CA拒绝通过；production无豁免。旧9092保留，broker仍无客户ACL，单节点无高可用背书 |
| 1C/1G | Agents worker默认group_id为aisoc-agents-triage，main只传topic/地址，没有group环境接线 | 1G已显式传项目group_id；worker关闭，实际Kafka消费留3A，不能用静态接线代替消费验收 |
| 1F | API迁移器默认可汇总SQL失败但不失败退出，严格模式需显式开启 | 1F REQUIRED/STRICT独立owner迁移检查通过，134文件/134ledger/0pending。首次macOS伴随文件导致268计数已阻断并修正打包，失败日志保留 |
| 1F | `POST /api/v1/alerts/submit` 为直写库快路径，明确绕过Kafka/Fusion | 1F新认证alert-ingress已实现并实测主链；原submit仍为直写快路径，不算Fusion链验收 |
| 1F/1G | 事件检测/lake与部分后台任务默认启用；Agents可自动消费/升级/记忆写回 | 按执行卡显式关闭范围外/尚未验能力，并检查实际订阅和启动任务；所需能力到对应子批再开启 |
| 1D/1G/3C | 共享Qdrant1.7.0有API key；20生成的部分HTTP/SDK调用没有向21传递密钥 | 1D用受控key和REST验结构/恢复，原20 overlay未挂载；未来业务路径需实际传递密钥、独立集合名并核SDK1.19.1，不能只改QDRANT_URL就宣称接通 |
| 1E/1G | LiteLLM1.106.0在无虚拟密钥DB时，错误master key请求返回400/no_db_connection，非401 | 1E真实拒绝已验；保留原版行为及首次探针判据失败，不以加匿名绕过或额外数据库掩盖。服务key不等于tenant/BYOK隔离 |
| 1G | 原服务可能向缺失的Realtime发送非必要进度；未证明无Realtime仍能交付 | 1G两Run无Realtime均完成，重启后API账本/报告hash保持；Agents本身缓存易失，其他入口未验 |

1F还补齐API startup对已有图/湖禁用配置的判断，新增war-room worker开关（默认保留上游开启）；本批12项后台worker关闭。未知schema DLQ会在解析tenant/source前拒绝，记录可通过broker坐标取回；不得假设其一定有tenant/source字段。

## 源码事实/待验证风险

- 1F已实际确认：同指纹而event_time/external_id/source不同的发生归入同一canonical Alert；新增来源ID保留，原event_time/raw_event为首条。独立发生语义不宣称通过，2A继续核。
- Fusion PG fail-soft 与 Kafka 发布分离；自动分诊 DLQ 失败可被吞掉，不能假定可靠处置后才确认。
- Case 发起调查只选择/裁剪有限告警材料；报告覆盖不能宣称整个 Case 全量。
- Recon 的非空增强 error dict 可能被后续判断当作有材料；这是静态风险，需实际定向复现。
- Ledger 无 DSN 可 no-op，Actions 保存失败可降级内存；状态完成不证明持久证据齐全。
- `max_tool_calls` 的部分检查实际比较模型调用；不能据名称推断严格工具预算。
- UEBA window_days 不自动实现逐样本淘汰；peer member_count 不一定是人数；CORE 行为模块与独立 UEBA 要分开测。
- ATT&CK 语义函数在已检查的 agents/app 未见调用方；索引可检索不证明调查已用。
- Live effects 验证有条件，其他动作/入口不保证已回读；awaiting_completion 不当 succeeded。

完整逐项定位与测试入口见 [数据/风险分析](../reference/aisoc/07-data-tests-porting.md)、[源码索引](../reference/aisoc/08-source-index.md)。实际可复现缺陷进入新项目问题表后再限定修复，保留原测试与结果。

1G实测缺陷及限制见[回执](1g-service-baseline.md)：缓存读跨tenant及外Case发起缺口已加约束；工具error字典成功标记、同响应usage重复计数已修复并独立复验。首次错误账本保留；API聚合numeric0需结合unpriced provenance解读，费用unknown。报告token上限和可选增强依赖未接保留，未宣称完整调查质量。较大模型和旧数据按[计划](knowledge-data-reuse-plan.md)比较，不混用向量空间。

2A新增[实测回执](2a-dedup-correlation.md)：2A-01不同发生的event_time/raw_event/external_id未独立持久，仍阻塞；需明确独立告警或聚合+发生记录合同。2A-02已修复既有incident成员重投重复计数和容量边界，25项测试及真实3投递通过；完整Redis丢失重建、并发及RBA重投累计不在本次通过范围。保留首次错误快照；只重建Fusion，实际镜像采用2A叠加层。

2A-01后续已按[独立身份合同](2a-source-identity.md)通过限定验收：新source-v1不再按内容合并不同上游UUID；旧legacy事实/历史缺口保留，可匹配旧HTTP及旧Kafka保持ID。无DDL；持久身份/关联存现有enrichment_data项目命名空间，后续增强写入须保留。PG不可用不伪称新身份duplicate持久，但只做故障分支替身检查。完整Redis丢失、并发与风险支路重投到后续，不将正常/单键丢失通过当全面恢复通过。

## 2B-01风险实测与后续边界

- 已修复：Fusion dedup key失效后相同规范ID重复增加RBA分数/计数；改为实体hash+完整贡献集合WATCH/MULTI，promotion同事务，40项测试及限定真实链/Redis并发通过，见[回执](2b-risk-idempotence.md)。旧多计分数不回写。
- 保留：风险非PG持久账本，完整Redis丢失/跨实体原子性/持续活跃实体集合容量/队列时效未验；原fail-soft行为及32次冲突重试上限不等于持久重试保证。
- 实测：Fusion `/ml/status`因租户认证材料未配置返回503；保持拒绝，不将source-consistent启发式值写成直接观察到训练状态。2B-02核所需身份接线。
- 静态后续：业务上下文API的内存snapshot版本、PG的yaml/enabled/updated_at、Agents的tenant缓存并非已证实同一持久版本；自动worker关闭。后续2B-02已对存储指纹/实际方法采用/TTL/恢复与失败缓存作限定验收，见下节；不能以preview代替消费或外推自动worker。

## 2B-02规则实测及限制

已复现原版重复GET的进程version递增、缺少可跨进程对应的内容身份；新增policy_revision与实际采用来源/状态，保留version兼容。保存失败污染缓存、冷依赖故障被报告成空规则已修复，83项测试与所列真实链通过，见[回执](2b-policy-versions.md)。

保持30秒缓存，故障stale_cache无最大陈旧期限；API行缺失可返回missing_row_cache，多副本/CAS/持久版本历史未验。原抑制在ledger写入前返回，自动worker仍关闭，持久抑制结果必须在3A开启前补验。Fusion状态接口认证503仍保留，2B-02未改该服务。

## 2C-01IOC路径

原matcher连接/查询失败返回[]且连接失败永久丢弃DSN；新生产消费改用带matched/no_match/unavailable/not_requested的lookup，失败保留可重试配置并限时。旧match列表接口为兼容仍保留原限制，其他调用方不能据此判“查过无匹配”。sink/API新增首次冻结lookup及来源/观测/衰减字段，见[回执](2c-ioc-consumption.md)。

仅一条历史参考，不证明实时信誉；来源原报告无数值置信，50只是默认。无外部增强、Go、模型或厂商调用。Agents旧enrich_ioc仍未接，完整上下文到2C-02；并发建池/负载、坏行转换、真实共享PG故障传播、公共IOC CRUD、Fusion ML认证503与旧风险限制未扩验。

## 2C-02当前PG上下文

静态核对：上游priority算法存在，但queue_priority没有传入真实PG资产/权限，build_queue仍用存储priority。本批保留队列行为，新增独立只读processing-context实际查询与评分解释，见[回执](2c-processing-context.md)。不把原算法单测写成队列已接上下文。

已有PG SAVEPOINT真实故障/同会话恢复、合成tenant隔离及时间边界通过；生产资料同步/有效时间/性能/全库故障未验。当前视图非持久历史快照，material_complete只指评分材料候选已解析；员工目录/普通事件日志/UEBA仍未接。下一2C-03核已有外部历史材料，不能用先前alerts当完整事件湖。

## 2C-03来源缺口与工具身份

[盘点与真实缺源回执](2c-event-ueba-sources.md)确认当前没有可接的AiSOC事件历史/UEBA来源；20仅一条未定性Kafka消息，不能当完整历史库。21 lake默认localhost、迁移启动关闭；Agents工具当前缺API调用凭据，空Bearer在发送前产生LocalProtocolError。独立进程用短时受限key收到API缺源结果，不代表生产工作负载身份已接。工具清单backed_by_data是7个静态SQL实现，不能作为runtime ready。后续实际工具接线须处理身份和清单语义，不能以开启采集/湖写入代替外部合同。

[3A-01](3a-triage-entry-plan.md)先处理business-context抑制在ledger前返回的持久性缺口；worker保持关闭，2C真实事件/UEBA消费仍开放。

## 3A-01抑制持久性已限定修复

先前business-context抑制在ledger前返回已由[本批](3a-policy-suppression.md)补规则事件；DLQ改为broker确认，双持久失败不提交并停订阅。新group仍默认latest，不能在未明确起点/控制器恢复/多分区语义前启常驻worker。已有completed Run会含policy标识的规则记录，统计调用方须按event kind/model_used区分模型verdict。来自故障探针的合成f-revision记录保留为probe-only，不代表实际规则采用；完整规则撤销/再分诊、上游可变材料等价性、真实模型/知识/事件源仍未验。

## 3A-02模型可见材料与质量限制

[3A-02实际回执](3a-model-triage.md)发现build_state缺失risk_score默认0.0，模型引用它当作零风险证据；后续[3A-03](3a-risk-score.md)已修缺失/null、显式0及来源语义，并验一次真实模型。旧已默认0不可反推，未知的内部数值特征基线与权重保持，不算重新校准评分。后续[3A-04](3a-org-memory.md)已接A/B组织记忆读取，成功/空结果与失败分开；后续[3A-05](3a-tenant-skill.md)已验技能Bearer/settings:read、读取/选择/失败来源及实际模型采用，重启回查保持；后续[3A-06](3a-kb-read.md)已接A/B KB认证读取、保守cutoff、实际采用文本与工件；后续[3A-07](3a-dispositions.md)已接近期处置认证读取及明确采用来源；后续[3A-08](3a-identity-read.md)已接身份读取及明确图源失败，五类reader接通，完整质量仍未过。

3A-03还保留原finding文字`confidence0.95 < threshold0.85`不准确的问题：needs_review分支实际要求升级，不是数值比较成立；自动graph仍关闭。新number|null消息不兼容旧float-only Fusion，不能直接撤层后继续消费积压，恢复步骤见回执。

3A-04组织记忆只有两个测试tenant配置了受控30天reader key，语句直接合成入PG，不等于真实多分析员编译写入或全tenant部署。默认缓存120秒内不重验服务端撤销/到期与编辑删除；逐条核缓存expires_at、映射移除/轮换在缓存前生效。真实撤销失败探针强制TTL0，不能宣称默认即时撤销。新first-write回执/工件原子性不外推原通用Run/alert重试更新。失败状态只验证实际读取→prompt投影→probe-only账本；只有正常材料调用了真实模型，完整质量未过。

首轮raw_event评分标签/synthetic来源污染已保留；另3条新告警盲测分类符合预期，但模型恶意回答有ATT&CK名称错配，授权只来自输入变更单，置信未校准。模型连接失败没有成功响应/成本行；cost日志persisted=True只表配置意图，不是行存在或零费用证明。完整模型质量、常驻自动分诊、多分区和崩溃中模型重复调用未验。

## 3A-05技能读取与保留边界

本批使用独立每tenant settings:read reader，保留组织记忆alerts:read的key/映射；仅A/B测试tenant配置，不代表全tenant部署。默认缓存120秒，映射移除/轮换在缓存前生效，API端单独撤销/到期、技能编辑/退休须刷新后生效；逐条检查缓存expires_at，刷新失败不采用旧材料。选择保留加法分数（rule20、technique10、source5、每keyword2，同分按ID），不是严格优先级。生产worker保留source，技能选择可回退原始MITRE标签，不代表已修复整体技术映射质量。

真实模型采用v2，事后合成头v3与历史v2工件分开；不外推deep investigation版本pin：原逻辑在指定旧版本不可得时仍可能落当前版本，graph保持关闭，列为3B开放前的检查/修复门槛。技能指导语的确切采用文本/hash、读取事件和工件同首次写入事务保存，不能据此宣称整个Run/alert完全不可变。

8条预激活样例及后续2条读取样例、版本轮换均为合成测试；4条replay行是failed/probe-only、无score/报告且未执行replay，仅满足原FK，不是实际编写/回测/激活流程通过。失败状态验证真实读取→prompt投影→独立probe-only账本，只有正常采用材料调用一次真实模型；347测试与1677 tokens不证明技能内容或完整调查质量。重启回查与身份生命周期已核，失败尝试按[回执](3a-tenant-skill.md)保留。

## 3A-06 KB读取与引用边界

KB内部GET已使用Bearer/knowledge_base:read及tenant交集；reader有独立受控映射，按tenant/地址/身份/query/limit/cutoff隔离缓存，失败不采用过期材料，禁用/无配置/无命中/失败分别记录。默认120秒缓存仍不能保证API端单独撤销、到期、文档删除或编辑即时生效；本批已实际验证撤销后仍命中有效缓存，强制刷新才401且无材料，不能写成默认即时撤销。仅A/B测试tenant，原org/skill权限与映射保持。

当前检索是aisoc_kb_documents的PG english全文content匹配，保留原query生成、kind和排序；不使用embedding或已有ATT&CK/TI向量索引。六条KB行、含必要检索词的正文及后续压缩均为本批合成资料，不是真实SOP、产品检索或知识质量。created/updated cutoff保守排除后来新增或修改的行，创建/修改拒绝数不双计；没有正文历史重建，不能还原被改旧文本。API文档详情只有200字符preview，核完整采用依据须看冻结工件。

守卫扫描、清理、JSON转义、UNTRUSTED_DATA与nonce边界保持；统一采用子集后保存文本、来源、引用表及hash。KB局部使用ensure_ascii=False避免中文经二次转义触发隐藏截断，编码体最多3400字符；inline boundary note等义精简，保留原“suspected prompt-injection attempt”措辞和原断言。字符预算不是token预算，也不代表注入守卫检测质量已全面通过。

首次完整literal prompt8717、第二次8105字符均在8000上限前预检停止，未调用模型；只改本批合成KB内容/标题并保留旧新hash与updated_at，另作等义note精简，从检查点恢复同一已受理告警。最终7861字符、一次真实模型2095 tokens未截断，提供KB1但model_citations与unresolvable_citations均为空；这是实际提供来源，不是已证明模型引用准确。中间prompt-v2测试197过/1措辞断言失败保留，恢复原短语后prompt-v3重测198过，未删断言。

新KB回执随verdict首次事务保存，真实PG故障/同Run恢复及重启回查已验，不外推整个Run/alert完全冻结。该批当时处置/身份reader401，处置后续见下文；deep investigation版本pin、真实事件/UEBA、宽样本质量和常驻消费仍未过；详见[回执](3a-kb-read.md)。


## 3A-07近期个人处置意见边界

近期处置GET已使用Bearer/alerts:read及tenant交集和显式RLS，独立每tenant凭据映射在缓存前选择。仅A/B测试tenant配置两枚30天reader，原org/skill/KB六枚凭据保持；alerts:read是已有较粗的只读scope，不是本接口专属权限。默认120秒缓存不即时重验服务端撤销/到期或反馈编辑删除；已实际复现撤销后缓存成功、强制TTL0刷新401且不采用旧材料，不能宣称默认即时撤销。闭合地址失败与恢复为真实reader证据，坏格式/缺时间/错误cutoff echo等为单元或投影证据。

五条反馈是直接合成PG读样例，alert_id为空且符合真实表约束，不是分析员实际结案、纠正、第二人佐证或编译组织记忆。保留同rule优先于仅entity匹配、再按created_at及ID排序；原prompt标题含newest first，实际是各优先级内时间顺序，不能解释成跨组全局最新。表只有created_at且非空，没有updated_at/历史或数据库禁止UPDATE；cutoff只能核记录创建时间，不能重建后来编辑的旧note。row_source_sha256是带tenant及请求匹配标记的当前API来源投影hash，不是完整DB行版本、历史证明或认证签名。

最多5条、note最多240字符，完整原heading与个人意见advisory共同受原3000字符上限约束；采用行、实际清理note、rendered文本/hash、完整prompt块/hash一致。本次3条意见/1336字符块进入7355字符的真实safe-call输入；一次模型needs_review/自报0.65、1909 tokens，未精确提及note或反馈ID，rationale仅概括参考过往意见，不证明因果采用、分类正确或引用质量。原org读取success，技能读取success但selection no_match、KB no_match是该新rule/entity的自然结果；另外用旧查询验证原三能力保持。

初394项测试通过后，收尾独立进程导入reader触发app.agents包初始化依赖环。保留失败证据，移除该包初始化依赖、使用固定的闭合词表并补两种新进程导入顺序核对，最终396项（API91/Agents305）通过；仅额外重建Agents，env/mount/依赖/DDL不变。最终镜像非root读取A/B处置及原三能力通过；唯一真实模型和原重启工件核对发生在首镜像，最终镜像没有重测模型。后半只读检查点恢复没有追加重启、key操作、输入或模型，不能写成全程首次通过。

真实PG工件INSERT除零回滚/同Run恢复/重复不追加保护的是首次读取事件与工件，不冻结通用Run/alert更新。生产SQL同会话SAVEPOINT故障恢复不是HTTP/共享PG故障或API503传播验收。该批当时身份reader401，现已由3A-08接通；旧增强/工具身份、事件/UEBA、完整知识/调查质量仍开放；常驻worker、graph、审批和真实响应关闭。详见[回执](3a-dispositions.md)，身份后续见下条，imported_at不能当HR有效期或完整历史。


## 3A-08身份读取的时间、权限与质量限制

五类reader已接通，但只验A/B合成资料。身份imported_at是Employee导入stamp，不是HR生效日；native cutoff先过滤再limit，7候选只1可采用（晚3、不可核3），所有采用行仍计业务历史未知。新样例部门/经理两属性v1→v2后旧split也读当前值，明确不能重建旧HR路径；is_active/职位不证明当前活动授权。

专用lazy READ_ACCESS不启通用图初始化/schema。Community共享高权限凭据不是数据库只读租户角色，原Bolt未新增TLS；隔离依赖本查询每节点严格tenant，不外推其他图接口。身份默认300秒缓存不即时感知撤销或图修改，刷新失败无stale。真实配置移除503、图查询错误及恢复与PG账本探针分别留证，不是共享服务outage。

唯一模型同最终镜像，身份1已提供、回复提到账户及通用service词，不证明因果采用或质量。来源ID未显示在prompt，仅供工件追溯；未提ID不列失败。初次operator成本表TEXT参数传UUID而失败，未发输入/模型；仅修字符串绑定并从已完成矩阵后恢复。初版operator未另存文件/hash，不能声称具备该版本冻结备份；失败日志/检查点保留。3A-09实际复验与阻塞见下条，常驻、graph和响应未开放。


## 3A-09历史复现与仍存准入阻塞

三例真实分类符合判据，但p01把11:01行为说成处于02:00批准窗口，且把缺少job当确认未授权；完整质量不通过。p02授权只来自合成CR，身份不是活动授权；p03的0.10已在Fusion叙事中，risk_score仍null。未追加模型改善成绩。

真实broker以模型方法替身复现：坏schema返回None，无DLQ却commit1；ledger返回False且PG零行，也commit1；冷进程重投已完成Run仍重入模型方法。暖重投原事件/工件保持，但通用Run/shadow行变化，不能宣称完整不可变或模型恰好一次。PG错误后的同进程暖恢复虽不重入模型，却将原先实际读取的五类回执全部写成not_requested，来源事实丢失；该历史事实保留，普通live路径的后续保护见3A-10-02。

真实工件错误与注入DLQ未确认时offset0，恢复后1；实际DLQ确认后才commit1。这是限定小边界，不抵消上述静默提交，也不是共享PG/broker outage。生产SDK根client默认retry2/timeout None，本批只在探针实例设0/45秒，生产仍未受该限制。静默提交的后续修复见下节；[总计划](3a-worker-reliability-plan.md)其余子项仍为规划。

首次broker工具在import前失败、无topic/消息，保留原脚本/log后只修操作工具。finish误要求measured1而实际unpriced1/measured0，保留原脚本与结构化失败；首次独立完整stderr未保存。只读恢复未重复撤销、输入、模型或重启，不能写成全首次通过。详见[回执](3a-triage-admission.md)。

## 3A-10-01修复范围与保留缺口

[本批回执](3a-triage-durability.md)限定通过：live writer只认明确True，False/None等为持久失败；Kafka入口先验证已JSON解码的schema，坏消息和无处理结果不再正常提交，DLQ未确认保留offset。只改两处运行源码，143项直接测试和真实broker/PG小边界已验；不覆盖非法wire JSON、直接triage/build_state或全部其他消费者。

有效UUID不证明tenant在PG存在或告警归属。3A-10-01当时未知tenant先进入模型方法替身，再因PG FK失败进入持久DLQ；后续普通live claim另核告警归属，不能外推所有入口授权。无pool样例仅恢复DLQ确认，pool仍为None，不是PG恢复成功。该批当时冷重投/来源恢复问题后续见下节；生产SDK retry2/timeout None及p01时间/授权理由错误仍保留。

初次测试136通过/7个新增替身失败，只修新测试后143通过，运行源码不变。首次部署已构建并重建Agents后因Env列表顺序断言停下；原脚本/log保留，改按排序hash核相同配置后只读verify-existing恢复，没有再次构建或重建。最终再做一次同容器重启回查，不能写成全首次通过。常驻worker/自动graph/审批/真实响应继续关闭。

## 3A-10-02保护边界及新增准入限制

[回执](3a-triage-recovery.md)限定普通Kafka live分诊：先核合法首次结果及来源工件，新处理持久claim/seq=-1后才进入方法；同worker保存恢复保留完整五来源/usage/原tuple，fresh进程遇已开始而无结果则unknown，不能靠TTL重调。三个真实broker样例及207项测试通过，但不是模型恰好一次、长期吞吐或rebalance保证；direct triage、replay、纯离线shadow和原policy/memory抑制入口不据此扩张。

默认事件时间线实际包含[-1,1]或仅[-1]；显式`events?since=-1`仍422，负开始事件增量cursor在修复前是准入限制。seq=-1只证明处理开始，不能写成模型请求已发送；unknown Run即使被reaper从running改failed也不授权自动重调。旧legacy首次结果只回可证明字段，原incident/shadow/规则/模型名等缺失保持unknown；p01只读lookup保留1687 tokens，没有worker或模型重放。

本批首轮测试、broker、部署与finish通过，无失败恢复或重跑。生产SDK预算、负cursor及3A-09 p01理由质量未修，完整worker准入仍false，下一3A-10-03见[总计划](3a-worker-reliability-plan.md)。十枚reader只核原文件/hash/metadata/scopes保持，未重测十枚各自旧查询，不能写成重启后完整reader查询矩阵通过。

## 3A-10-03-01请求界限与cursor修复，额度仍待验

[回执](3a-triage-request.md)的189项测试/71项HTTP限定通过：当前triage角色factory默认SDK retry0/timeout45，原auto-triage另有整次45秒截止；既有开始事件next_seq=-1可直接增量读取，-2仍422。客户端截止/取消不证明远端停止或零usage，其他角色/显式参数覆盖/原始HTTP及stream入口不外推。本批未新增模型调用，未验43真实超时。

仅API/Agents更新及重启、当前二十层，14表旧材料/十枚reader保持、三操作key401。当前仍无持久单tenant调用/tokens额度，跨进程并发、积压/停止恢复留03-02；完整质量和worker准入false。一次过早finish由部署检查点拒绝、无副作用，待部署成功后完整finish；无重复部署/模型。

## 3A-10-03-02持久预约/停止的限定边界

[回执](3a-triage-budget.md)的263项/137项HTTP、真实SSL Kafka/PG与模型HTTP替身已通过；只有普通live且配置policy的LLM尝试才受新表约束。call与固定预留token/未确认上限跨进程共享，quota claim失败保留offset，旧前置lookup仍沿原确认DLQ合同。一次20000为准入单位，非实际usage；出站16000 UTF-8字节/512输出/SDK0/45不外推任意tokenizer或厂商忽略参数。未知预约不自动过期，当前三份保留，A积压仍offset0/end1。

实际10.012917秒停止后任务清空、offset保持，fresh未知无新请求；显式调整测试policy后同group恢复没有退款或重发消息。初始import环、恢复校验身份、probe读取policy权限及operator屏障/快速拒绝断言失败均留证，故不是首轮全过。当前21层、原134迁移保持，另有一项目表；scope外模型入口、自然窗口过期、长期吞吐/rebalance、非协作取消、生产完整prompt覆盖和整体质量未验。下一为3A准入剩余阻塞复核，worker仍OFF。

## 3A-11-01最新只读准入复核

3A-11-01只读准入复核已完成，见[回执](3a-admission-review.md)：旧p01时间/授权错误未被indicator gate识别；常驻Agents审批提案guard实际True且缺Kafka bootstrap/TLS，旧调查工具身份仍缺。三未知预约及A积压保持，0模型/消息/offset提交/运行改动；完整准入未过。下一[3A-11-02配置补齐](3a-triage-admission-config-plan.md)，保持worker禁用，然后单独修提示词/复验质量。

审批提案guard未显式禁用、常驻Agents缺Kafka bootstrap/TLS；worker关闭使其未作为常驻消费者运行，隔离探针通过不证明这些环境项已接。五reader不替代旧工具service身份。旧回执保持；本批无运行改动，三未知预约及A积压不清理/重调。

## 3A-11-02最新配置验收

3A-11-02常驻分诊配置补齐已限定验收，见[回执](3a-triage-admission-config.md)：仅Agents同镜像重建一次，新增四项环境值，复用原只读CA；审批提案guard现False、Kafka SSL/主机名校验及六组offset读取通过。旧14表/三unknown/A积压/十reader/其他35容器/18卷/134迁移保持，0模型/消息/提交。当前22层、19源码层，worker仍OFF；下一[3A-11-03理由提示词修复](3a-triage-reasoning-plan.md)，完整准入/质量未过。

当前补齐的是transport及审批提案禁用，不含常驻topic/group/DLQ项目映射；五reader与通用工具身份仍分开。A积压与unknown不清理/重调；p01理由仍未修，不能将配置就绪当质量或常驻准入。

## 2026-10-20迁移正确性复核

[审核报告](migration-review-20261020.md)确认R1 Fusion保存/发布未确认仍提交、R2普通分诊丢description/event_time、R3 source-v1缺行修复保存空关联、R4 gate前缓存使下一新告警复用被拒绝的原结论、R5 consumer.stop报错漏任务清理。均待修，本轮使用原方法内存替身复现，未注入真实PG/Kafka故障或模型；不把既有局部通过外推。R6更正项目映射未配置的旧判断：1G已接topic/group，DLQ派生为项目topic，尚缺常驻准入证据。
