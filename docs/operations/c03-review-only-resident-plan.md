# C03-R02：review_only_v1 有限真实 main 消费与首次结果恢复

2026-10-21。**执行范围卡；root 冻结采用后按本卡实施，尚未执行/验收。范围采用不等于准入通过。** 本卡细化已采用的人审 profile 卡9512，沿用完成计划，不重开旧自治 resident 四例/质量门。用户持续迁移授权覆盖本批常规隔离验收；执行仍须本卡正式采用、实际资源冻结和未参与实现者的算子/启动门审计通过，不把准备文件当执行许可。

## 已实际闭合的 R01 父

镜像 `sha256:19f8f1a52875b0a16c75890046eeec3fc308995cf73a5bc52899afa076958110`，191项断网测试全过（新增22、既有169）；Agents185/总770 Py、v5/lock不变，28 Compose/25源码层，review_only_v1、worker OFF、原7只读bind/60秒停止宽限。seal `d483df2f9ef40c75c97887c8f65b173e8c83d4bc0cbc147146cc0ab1b12650d6`；来源 `ca3f66270667ce07175550ef1173bb2aaed71558a035e6039b7660f8968559c5`；handoff `c8a5dfc1dff8624d74c9272411446e6afdfc4baae371ed17d773c89a9a960b54`（592项）。public审 `ac74ede2dea1ca9a2bbfcdf3fcefd3d3e335f3cafd0f6285fd82452cb41d1d05`、32文件交付 `82b38648d82e0364cbb04e5a0f2ac9a7920c396e1d91d0cc2d35bf911e7d0108`、交付后独审 `eae9a7eb0a8dedac4e6c9200aefd14902339d000e472156540174ea192fc16ea`均accepted。精确路径/hash及测试log在附件 `parent-bindings.json`。

原15文件采用/bf5夹具、189通过/2失败、fc444单测试修正、observer RLS错误/勘误及原233证据均保留；不能改旧卡/回执/测试历史。R01预算更新double不是实际PG预算持久化；R02才验本批真实链。不build、不改业务Py/SDK/prompt/schema/route/DDL；最终恢复R01正常CMD/entrypoint/restart策略/env/7bind/profile/OFF，临时operator不冒充永久源码层。C04/C05报告/引用质量、后续审批和unknown边界不降低。

## 输入、写入与硬上限

- 沿用A/B tenant和十reader；0新tenant/reader/closure policy。各1枚新操作key、≤3小时，仅alerts:read、alerts:write、cases:read；原reader不作入站key。own200、跨tenant Alert/Run/events404、缺settings:read的credentials403及撤key后各401纳入同一HTTP预算，不另加第三key。
- 两条新A/B身份/body先冻结，不复用旧质量输入或挂预期标签；A可选CloudTrail StopLogging成功/IsLogging=false的受控材料，B为独立tenant资料，具体UUID/source/rule/host/user/时间由实际冻结卡绑定，不在此猜定。正常目标各1次真实SDK回复，合计≤2；少于2只记实际覆盖，失败不补第三例。raw建议只要求合法结构和与工件关系真实，不预定分类、不算自治质量通过。
- **不改额度、不退款/删除/回收unknown。** policy保持A10calls/200000单位/3unsettled、B4/80000/2，窗口86400秒；发送前按真实DB时钟及父12预约/240000单位/3unknown重核各剩1。新增≤2预约/40000单位；正常两responded后共14预约/280000单位，保旧3unknown，预留单位不是usage。新unknown永久保留待独立处理，不盲重发。
- 上限：2 Alert、2 Run、6 events、14 artifacts、2 cost、2shadow、2预约；QA/自动Case/graph/playbook含preview/approval/source/outcome/组织记忆写回全0。旧14材料表旧行、全部旧Alert字段、预算/旧组/十reader/其他35容器/18卷/134迁移保持。API认证/审计遥测按实际单列，不假称全PG不变。
- 唯一业务fixture：OFF且两次HTTP→Fusion→PG/fused确认后，仅新A exact UUID+tenant+完整原row/字段前置条件，row lock下1事务1 UPDATE RETURNING1：ai_score=.37、ai_summary='Controlled preservation marker; not an analyst or model decision'、ai_recommendations=[]、triage_groundedness=.42、triage_ungrounded=true。其余字段必须相同，否则rollback/停；保存原row/SQL/实际row，之后以整row为ON前baseline。不是API PATCH/真实模型或分析员意见；C04不得当事实采用。

## 新组、真 main 与仅三个 bootstrap hook

唯一新review_only operational group在worker OFF时，把**当前fused三个partition冻结end显式提交为起点**，再接本批新A/B；不用auto_offset_reset=latest。原socai2-agents-triage三个commit=None及父90条历史前缀保留，不处理或静默跳过原group；旧6预算组、4质量组及DLQ不读消息/不改commit。除新group唯一精确seed外，metadata观察者不assign/poll/commit；只准两个已知坐标的独立原wire capture。共享fused end正常增4（新2+cold重投2），原main commit仍None；Fusion raw组仅允许本批已确认raw坐标推进。

服务仍运行R01同镜像的原app.main.app、真实lifespan和其原worker/task。临时bootstrap在同一Python进程使用原serve同款dual-stack socket/uvicorn workers1/reloadFalse；不调用会exec丢patch的serve.main，不另建worker或调用triage冒充main。先核185源码/lock/env，再固定把`/app`加入import path；不改环境/SDK逻辑。

只准三个临时hook：①原lifespan观察并委托一次；②原_process_with_retry前精确tenant/Alert/source/rule/完整fused规范digest/phase guard，合格才原样委托；③仅新A原persist_auto_triage真实True后的一次False失确认。**0 SDK、reader、Kafka client、HTTPX或HTTP计数hook**，不捕获header/key/hidden reasoning，不改body/response。额外/异物交付先安全记录再typedHold，保持offset/退出；不能返回假成功或读源/claim/模型后才核身份。cold最多2次额外原triage_delivery.lookup只读前置核对，生产cold路径仍原样委托。

ON只增加一个非秘密RO operator目录，保原7RO bind/UID10001/read_only/CA/60秒宽限，无额外RW bind；trace/release仅容器/tmp tmpfs，独占0700/0600，跨stop/start前必须pull/hash，不能假定tmpfs保留。trace只安全ID/hash/计数/时间/error class。临时ON **restart:no、RestartCount=0**；任意意外退出/新进程/计数变动失败并OFF，不重启清fault token。新组唯一member/三partition assignment、原main附着worker/task/PID、准确订阅readyz200与实际seed/commit共同证明启动，仅env/readyz不够。

## 无环授权与阶段退出

bootstrap ABI沿r02（历史SHA7229cc…），r03仅补上述固定/app路径；最终算子/bootstrap精确SHA另冻，范围卡不反向hash未来授权或operator。创建命令只带`--directory /operators/r02 --contract-sha256 <contract SHA>`，**不含fresh authorization SHA**。

冻结scope/parent/wires/实际资源与预创建watchdog声明→contract/SHA→create不start（同一ON recreate）→保存实际created完整inspect私有字节/SHA→较早config独审（不引用未来fresh授权）→独占fresh-authorization→单独HOST启动门绑定其SHA/inspect/contract/bootstrap→重核RO目录后仅start一次。contract祖先不得引用未来created inspect、fresh/cold授权或最终start gate。容器自报accepted/audit SHA不证明独立授权，trusted host gate不可省。

| 阶段 | 最小实际退出条件 |
| --- | --- |
| prepare/freeze | 父19f8/770/185/lock、实际正常CMD/restart/env/7bind及private rollback、旧表/全Alert/QA/12预算/十reader/134迁移/环境/旧组metadata基线；DB时钟容量、输入、source HTTP上界和0请求HTTPX依赖检查；scope及完整最终算子独审accepted。此时0模型/业务写。 |
| seed+ingress | 新两key/唯一新group精确seed；OFF下各一次POST/capture，202/canonicalID/tenant/source/PG首次snapshot/原wire字节与坐标全确认；unknown即停不重发；再做唯一A fixture并封A/B整row。 |
| fresh ON | create/start无环门过，独立watchdog已armed；原main真实消费A/B，SDK各≤1，五源authenticated状态/实际采用工件、strict raw advice+versioned receipt独立于effective NR/null/review_required=true；规范原回复不伪造provider-wire证明。 |
| A ackloss/warm | 原真实PG事务已True，才消耗一次fault token。≤15秒pause中host确认A completed首次Run/seq0/1/来源/回复/usage及A commit未过原offset，保存首次快照后写绑定token/Run/hash的一次release，再False；原pending暖确认True后才commit，0额外SDK/reader/Run/event/artifact/Alert写；shadow可能此时首次落1行，仍总≤2。过期/异常typedHold，不能伪报注入或恢复通过。 |
| fresh containment | 两Run产品/usage/cost/observed_tokens与首次关系、A/B整row、全部效果0、两个commit精确，安全trace归档；未参与实现者独审accepted后才可cold。A/B可不同分区/顺序，不能要求B必须在A的15秒pause前完成。 |
| normal stop+cold start | 正常stop60，原main cancel/join/cleanup及组无member；先封tmpfs。独占cold授权绑定fresh SHA、首次产品/wire/offset/独审，单独HOST cold门后**start同CID/同镜像/同组**一次、新PID/StartedAt；无故障注入，不改CMD/原授权。 |
| cold A→B | 原wire各一次send_and_wait、每次确认commit=新offset+1才发下一条；原PG首次Run/完整advice/effective/source/usage/工件/Alert整row不变，0额外SDK/reader/产品/cost/budget/shadow。已开始不明/unknown不重发。 |
| OFF/finish | 安全OFF无需等待业务/质量门：停确切本批actor→第二次recreate恢复R01正常配置/profile/OFF/7bind、无临时mount/hook/task/inflight/groupmember→只撤本批2key并各401；旧状态保持，保所有失败/新产品，不清数据。结束及撤key后独审/seal均过才有限通过。 |

本fixture模拟**PG commit后ack丢失**，不是PG rollback/SQL故障或broker outage验收。正常模型usage须Run.total_tokens=成本输入+输出=预约observed_tokens；费用未知保持null，SDK-visible/egress恢复内容与provider物理wire/hidden reasoning分开。effective confidence未知；旧简化timeline的0仅兼容sentinel，canonical Alert所有AI字段不由profile更新。Run completed不等于人工复核或Case结案。

## 时间、计数与结论

一条不可延长lease从ON前watchdog armed开始≤600秒；420秒soft stop，保60秒停止宽限，独立host watchdog不依赖业务gate，必要一次hard kill即失败。正常最多2次Agents-only recreate（ON/OFF，同19f8）、中间同CID正常stop/start一次，0build/其他服务restart；不能意外fresh重启再试模型。

业务publish调用正常6（raw2+Fusion fused2+原wire cold2）；交付slots上限8：main fresh/cold入口4、capture2为实际分别记录，Fusion raw2仅合约/ack+commit推证，不把reserve当物理yield。任何已发生意外先计坐标/hash/over-cap再停，不能漏报。

**HTTP只计host/独审自身真实attempt，main不加计数hook。** 五fetch源码每fresh各≤1GET，fresh2最多10GET；SDK调用仍≤2，但production OpenAI SDK底层可能follow redirects，每次按`1+max_redirects≤1+20`保守预留21次网络请求，故`10+2*(1+20)=52`为**main物理HTTP上界，非实际52，也不是增加模型授权**；warm/cold源请求上界0。必须先以实际production triage factory做0请求实例资格：SDK max_retries=0、实际HTTP client max_redirects≤20、transport retries=0；五reader普通HTTPX follow_redirects=False/transport retries0保持，不能用普通client默认值代替SDK根client证明；source/45秒/单intent门同在。准入/运行恒守`host实际+独审实际+52≤200`，所以两者合计最多148；失败/取消/无状态的已开始attempt也计。未用reserve不是actual或可退款额度。自动healthcheck/共享无关后台流量另述，不能宣称观测全网HTTP。PG显式helper上限host600/独审160，不冒充应用内部SQL逐条计数；不用旧E全局hook。细目在附件 `write-action-budget.json`。

仅所选两新输入、有限窗口的review_only交付/隔离准入可在真实退出与独审后通过；raw分类/理由质量、原自治C03、永久无人值守/自动响应及整体迁移仍false，C11再决定同profile日后常驻。未选旧入口/历史积压不外推，非阻塞上游问题集中延期，本卡不扩大算法优化或通用扫描。
