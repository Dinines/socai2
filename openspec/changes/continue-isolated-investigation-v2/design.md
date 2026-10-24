## 2026-10-25 M8a4.2原子手动准入细卡（d4结束保存/本卡独审后实施）

只新增Agents program_start_store/ProgramAlertStartStore及SQL事务替身测试，复用已冻结new intent/full canonical Alert projection/new runtime/publication store；不改旧表/DDL、旧代码或已验runtime函数。输入是可信调用方已认证的current principal/actor＋新完整intent；store另外接收可信server配置的StartBudgetPolicy，并与intent预算完整canonical比较，每请求重核tenant/actor/closed版本，不从Alert正文、caller owner/Run/deadline或retained字符串取得权限。真正HTTP authentication/调查run＋alerts read权限及当前业务启动政策留a4.3，本块只证owned持久原子性，不把纯principal当认证证明。

以既有Run PK承载tenant+operation_key派生的稳定Run，跨族同key仍同身份/异文冲突。首查同tenant目标Run并FOR UPDATE：已有时仅强核唯一新admission event/intent工件及原begin两工件、固定owner/版本/scope/预算/原deadline和原Run字段，完全匹配仅返回只读回执；旧Run/缺marker/半成品/异文/unknown/mixed拒，不补写或重零。不存在时锁canonical Alert行FOR UPDATE（exact四列/显式tenant-id谓词），再重查/INSERT ON CONFLICT DO NOTHING RETURNING并处理并发；不同tenant碰同PK不泄内容、不换ID。原Run case_id必填但不是Case FK，采用明确server命名`v2-alert:<canonicalUUID>`外部引用，不建Case；仅insert实际已核三表合计41列（Run18列）范围内的必需字段，首次status=running/无completed/tokens-cost0，其后不改legacy计费或生命周期。

同一事务内由实际owned Alert全文生成原BusinessProfileRequest，用DB clock建立duration1..180秒内绝对deadline（可被显式server父deadline缩短，不可由caller延长），新manual无triage/history故OpeningUsage固定确认为零；若已有任何Run/ledger不能按新manual零期初重开。复制必要new begin逻辑在同conn执行，调用新store原_append而不嵌套_locked/事务，原begin schema/body/state/receipt保持，输入/owner/全部12版本精确绑定intent。Run INSERT、begin 1event/2artifacts以及独立启动意图1event/1artifact任一失败全部rollback。

启动意图是业务准入标记，kind=`program_alert_start_admitted`、agent=`program_alert_recon_start.v1`、artifact kind=`program_alert_start_intent`；不属于unified_运行状态事件，不伪造新state snapshot。其唯一owned不可变event payload钉住intent正文SHA/工件ID、原begin event/body/state refs、scope hash及新Run/executor，工件schema=`program_alert_start_admission.v1`含完整纯intent和同refs。读取必须从event pin重验实际RETURNING/tenant/Run/event/UTF8-size-hash和唯一性，不能只信工件自hash。现runtime/owned reader继续按原unified_状态读取且后续seq按全Run MAX+1，必须直接测试新2events/3artifacts可以经原ProgramRuntime执行、M7发布及compatible read而无unknown fallback；不为省事放宽unknown managed guard。

同Alert的新手动准入由Alert行锁串行。新准入事务必须显式`conn.transaction(isolation="read_committed")`，不能继承pool/session的repeatable-read默认；取得Alert锁后重新查询operation和同server外部引用下全部目标Run，绝不复用锁前不存在/候选查询结果。按稳定Run ID顺序锁定/强读每个候选，不能先以known marker过滤而漏掉缺marker/坏账本的保留命名空间Run；published使用支持publication的原ProgramReconPublicationStore同conn强读，不用plain writer误判。ready/claimed/blocked、未知或unsettled/无确认handoff都拒另key；只有已确认stopped且未结算0可申请显式新操作，旧费用/unknown不消失。SQLdouble核isolation参数及等待锁后可见新Run的查询顺序，真实隔离行为仍a4.4实证。历史不属于该新准入命名空间的writer未因此取得互斥保证；a4.3开放写入口前须另核目标独立性和旧writer冲突政策，a4.4仅独立受控新Alert。这不是Case自动政策或全系统调度锁。

只有首次全部commit确认回执可标fresh/may_enter_runtime=true，外部调用权仍false，后续controller还需原claim＋M3 reserve确认才可发一次。重复/跨进程只读及ACK未知恢复永不授权重新进入runtime；提交失败/结果未知均外呼0，不自动重试begin/新key或延长deadline。显式read_operation只能核原intent/owned原件与现状态，不接管未发出但owner失联的Run。并发同key仅一个fresh，其余匹配仅读；同key异actor/目标/窗口/budget/版本拒，旧新同key拒升级。

预期SQLdouble：全新准入2/3、正常fullsource有限ready后可发布/双版读取；逐项Run/begin/intent写失败rollback为无Run/无ledger，实际commit后ACK丢失不成功/0派发，cold只读恢复同原件/零副作用；并发同key/不同key同Alert、合法已停后显式新key、unknown未结算阻断、cross tenant/actor/old marker/missing/duplicate/hash/typed字段漂移、原deadline/预算/期初/hash不变均验。先strict/本卡独立审阅，再只本块实现/直接/独立复核/回执保存；无真实PG/HTTP/模型/业务Run/部署，a4.3显式写权限/派发和a4.4实际接缝另门，2.2/2.3/Case/Deep未完。

## 2026-10-25 b2.4d4离线双进程组合细卡（d3结束保存后实施）

只新增受控probe与其合同测试，不改已经冻结的API/Agents源码、注册或服务配置。两个`app`包在不同Python进程加载：API进程使用新program_result_api/CompatibleResultReadGateway及既有service认证/双read权限，Agents子进程使用新program_result_api/CompatibleOwnedReconResultReader和完整SQL账本替身；通过有界stdio请求/响应传递HTTP method/path/headers/body，httpx MockTransport与ASGI执行真正两个独立app。无HTTP socket、PG、CH、模型或后台worker；不得把该组合称真实网络/数据库联测。stdio不是新产品入口，case选择仅测试控制面，不能进入业务request/query或返回DTO。

可移植fixture在运行时由既有tests构造，不依赖`.local`旧回执或任何私密配置。至少fixed/program各published、candidate、progress、observer、cancelled十组，加旧A3 blocked candidate/published两组。每组先冻结全部Run/event/artifact选中列/正文及现有Mock工具调用次数，再API实际GET→一次gateway→Agents内部ASGI→owned读取，并重读；两次完整DTO canonical/manifest/MD/execution/候选与直接owned原输出一致，所有账本/legacyRun列/工具调用数不变。旧actual3111B缓存可作独立API协议参考，但不得充作上述owned账本证明。

拒绝组合至少核：API缺错凭据、缺任一read权限及query/body/nilRun不进入gateway；当前已核外tenant在owned层404，错误内部token的401对API成为502；两族unknown历史managed事件均409无fallback；在transport篡改双族版本/section即使局部重hash也502；内部token轮换后旧token下一请求拒，当前权限撤回后下一请求403且backend0。当前tenant/actor只能取认证主体，确认转发值与Agents构造的principal一致；客户端伪造actor/tenant不能覆盖。所有错误脱敏，无header secret/正文记录在公开回执。

控制器只启动自己Popen句柄，子进程输出每帧上限与读取等待显式有界（单帧含完整DTO但不超3MiB，单交换≤30秒），出错/EOF/超长/超时必须停止，不重发同请求；清理只针对该句柄并wait/terminate/kill逐级有界，不按进程名批量清理。输出仅允许工作区内显式新路径，已有输出拒覆盖；私密过程材料`.local/verification`，公开summary/非私密hash/状态/失败另存docs。原子创建输出文件，任意失败照留结果/未完成状态，不删旧失败。测试故障路径验证无未回收owned进程和无自动重放。

先strict/独立合同审阅，再只实现此probe/直接/独立完整重放/公开回执/保存。d4仅证明这套离线传输和版本组合，不能授权actual Run、调用预算或自动发布；通过后才另立a4.2 Run+begin+启动意图同事务准入卡，随后a4.3显式写权限/确认commit后派发与a4.4受控新Run。2.2/2.3、Case/Deep/真实语义/自动政策仍未完，不部署或合main。

## 2026-10-25 b2.4d3独立API兼容网关/双DTO细卡（d2结束保存后实施）

只新增API app/investigation_v2/program_result_gateway.py和program_result_api.py及tests，不改旧gateway/checked_result/router/认证函数或主app注册。新factory可复用原独立typed query app/common auth基础设施（per-process配置/原生命周期关闭，不建schema/worker/新身份）；同GET /api/v2/investigation/runs/{run_id}只在新显式app中注册。保原_currentUser require cases:read＋alerts:read及显式Bearer前置（禁止demo无凭据shortcut），forward仅current user tenant_id/user_id，客户端tenant/actor/owner/version/scope不能覆盖；query/body全拒、nilRun400/invalidpath422，无身份权限不发backend。

新CompatibleResultReadGateway配置URL_ENV=AISOC_INVESTIGATION_COMPAT_READ_URL和TOKEN_ENV=AISOC_INVESTIGATION_COMPAT_READ_TOKEN，无旧env/default/backend重试或版本fallback；explicit http/https baseURL只host/port/empty-or-slash path，无userinfo/query/fragment/invalidport，token同32..256 ASCII无空白。每read只一次内部GET same d2path，带server token及currenttenant/currentactor UUID，redirectfalse/timeout10；响应最大1MiB（有界读取后再JSON解析），400/401/403等unexpected→502，404/409准确映射，backend HTTP/网络错误→503，不泄返回诊断/URL/token，不自动retry或从v1读。旧gateway不变。

API不能import Agents app包；在新checker固定known两族契约（必要old纯canonical/sha/uuid helpers可只读复用）并独立核与Agents生成的实际DTO一致。仅根据known owned_fixed_recon_result.v1或owned_program_recon_result.v1显式选expected family，unknown/混版拒，不把new DTO改写成old再校。outer common exactkeys/tenant/run/profile=alert_recon/objective/targetalertnonnil/notificationNone/legacyRunstatus string，published与not_published各自exactkeyset，原dict返回不重渲染/规范化合法旧MD或添字段。all JSON结构比较canonical而非Python等值，计数/version/scopeRevision等strict int，flags strictbool，UUID/ref/hash形式完整。

not_published必须manifest/report refs为空/retention progress_only/delivery_gap result_not_published，progress exactphase＋M3stage_usage/run_total typed结构，candidate可空；若有candidate核对应runtime/handoff/result/prep schema/ref和version组合、identity/target/有限nature-auth状态及sha关联（不能返回另一族或未验证未知结构）。published核exact manifest/execution键集合、family renderer/mapping/sections/runtime/completion schemas及prefix；program mandatory closed12 policy_versions exact、fixed无此新增项，manifest version1/scopeRevpositive/tenantRun/profiletargetobjective/investigation_id及retention committed/previousNone。manifest selfref及outermanifest_artifact canonicalSHA、execution self结构和manifest execution artifact SHA、MD UTF8大小/renderer/媒体/SHA都同版；manifest与exec的runtime/plan/scope/source-stopped refs、typed用量/unknown-unsettled-unpriced/三维映射一致；sections questions/analysis/evidence均pin同handoff artifact/hash、对应family artifact schema/sections版/path，section_sha形式有效，program evidence path指program_material_document，绝不伪model_view。合同独审补清封闭result/preparation/evidence组合（不能泛称三section都非空）：fixed fixed_alert_recon.v1/fixed-recon: ＋view_ready→evidence=/preparation/evidence_document；fixed blocked_alert_recon.v1/blocked-recon: ＋material_projection_blocked→evidence=null；fixed fixed_runtime_unadopted_result.v1/unadopted-recon: ＋无preparation/not_adopted→null；program program_alert_recon.v1/program-recon: ＋program_material_validated→/preparation/program_material_document；program program_runtime_unadopted_result.v1/program-runtime-unadopted: ＋无preparation/not_adopted→null。published从result_ref前缀/retention.source_availability/evidence path或null/typed readiness固定此表，null分支必须partial/stopped或cancelled/awaiting_human；非空evidence也不自动ready。未发布candidate必须核完整result.schema/ref与preparation真实state/schema/hash/对应snapshot/null，不能把blocked当无材料或两族混用。补旧A3 blocked published和candidate正例、null证据却ready/错族path/前缀或availability混配等自洽重hash反例。

原state/材料真实来源仍d1可信backend负责；gateway证明format/version/ref/传输一致性，不声称selfhash可证明实际PG或MD语义。

预期API ASGI＋httpx transport：原7owned DTO/旧actual cached3111B DTO reference及new完整DTO/progress/candidate都可校且逐字节canonical/MD不变，new/oldfamily明确。actual require auth的注入测试验证双权限/当前identity转发backend secret不等于用户token；wrong/missingcredential/permission/query/body/nilRun不调用backend。unknown/mixedschema、任何outer及manifest/execution关键字段缺多、typed bool/float伪等值、program版本缺多/旧项、report/manifest/execution hash/refs/section族别/target等漂移均502，即使局部selfhash更新也不混版；合法fixed旧缓存不是PG账本重建。backend404/409/503/redirect/malformed/oversize/timeout一次返回准确无重试，配置缺新env仅old存在拒。实例改变受信当前credentials后旧request权限或token失效下一请求拒，无endpoint/client控制fallback。测试均离线，无真实JWT/RBAC/PG/network/Run/部署；d4组合及a4.2另门。先strict/合同独审再只d3实现/直接/结束保存。

## 2026-10-25 b2.4d2独立内部兼容GET app细卡（d1结束保存后实施）

只新增program_result_api.py/create_app及ASGI合同测试，复制必要原内部GET app骨架，使用CompatibleOwnedReconResultReader；旧result_api/app/路由注册/worker不改，新app须显式加载独立进程，不自动挂旧app。GET路径仍/internal/investigation-v2/runs/{run_id}但仅新process提供fixed/program兼容，不新增POST/查询/模型/Case/写Run/发布；OpenAPI/docs关闭，旧app仍单fixed语义。

新独立配置TOKEN_ENV=AISOC_INVESTIGATION_COMPAT_READ_TOKEN、DSN_ENV=AISOC_INVESTIGATION_COMPAT_PG_DSN、CA_ENV=AISOC_INVESTIGATION_COMPAT_CA_FILE；无旧env fallback/生产默认。factory必须显式有效32..256 ASCII无空白强token（显式read_token或newenv），可只读复用原checked token/HMAC/UUID纯helper；token只认证可信API网关，不是实际用户JWT/RBAC。current tenant/actor由网关已核后X-AiSOC-Tenant-ID/X-AiSOC-Actor-ID断言，body/query无法补scope/owner/version/权限。没有注入reader时仅lifespan读取explicit新PGconfig，TLS默认验证及可选CA、owned asyncpg pool min1/max2/timeouts10；启动失败脱敏不含DSN。owned pool结束close限5秒/timeout terminate且清reader；injected reader不代关。无旧pool/service配置或新常驻启动。

每GET先当前app.state token HMAC认证，再nonnil tenant/actor/Run UUID，拒任何query参数及非空GETbody；无reader503/backend0。构造TenantPrincipal仅当前tenant/verified-api-reader:actor/delegatedtrue给owned兼容reader，不接受owner/profile/scope等客户端额外输入。missing/wrongtoken401、badheader/nilRun或override400、invalidpath UUID422、method405、ownedRun不存在404、其余integrity/version409、脱敏persistence503；无凭据默认demo/bypass，不落旧reader重试。只接受reader dict的known owned_fixed/owned_program schema、exacttenant/run及publication_state published/not_published对应身份；缺/unknown/identity冲突502。该内部最小envelope不是d3完整DTO/manifest/hash证明，d3须另全验；结果实际来源校验由d1owned服务完成。

预期ASGI替身：actual兼容reader+SQLtransport fixed/program published/progress/observer/rev2 GET全DTO保持及new/oldschema、MD/usage一致/no行或新Mock工具调用；fake reader只用于auth/identity/error反例，不把它当owned证明。缺错token/header、nilRun、queryowner/version、GETbody、POST、foreigntenant、不匹配backendreply/unknownschema/缺publication_state、persistence/owned/integrity错全准确状态及backend调用计数；token与DSN不出response或ledger。仅oldenv存在时newapp配置不能成功，valid newconfig/fakepool参数/清理/close timeout terminate核，注入reader不关闭/不连库。current token被可信配置轮换后旧token下一请求拒。旧internal API原测试及new7frozen owned DTO保持，无真实网络/PG/Run/部署。先strict/合同独审再d2实现/直接/结束审阅，d3gateway/d4组合及a4.2仍另门。

## 2026-10-25 b2.4d兼容分块及d1 owned双版本只读入口细卡（c修后结束/保存后实施）

d拆d1新owned双版本reader→d2独立内部GET app→d3独立API gateway/DTO强核→d4离线组合兼容（各另卡/独审）；不改旧result_reader/result_api/gateway/已冻结函数、路由注册或部署。未知/混合begin/runtime/schema拒，不能按客户端mode/owner/scope决定版本或失败后换旧路径。所有b2.4d门过后才a4.2，真实GET/启动仍由后续实际受控新Run验。

d1仅新增program_result_reader.py/CompatibleOwnedReconResultReader及测试。caller已核current auth/read permissions，read参数仅current_principal/tenant_id/run_id，无owner/scope/version/profile参数。当前tenant许可及UUID非nil先校，再同一个pool transaction/tenant GUC/owned Run FOR UPDATE精确tenant行；持同锁读唯一managed begin，候选kind覆盖通用M3 KINDS[0]、fixed CONTROL[0]、program CONTROL[0]，len必须1。只有explicit fixed kind+agent+原closedruntime或program kind+agent+newclosedruntime可选，generic/未知/双begin/不一致拒，不fallback。合同独审补清：仅查已知begin集合还不足；新reader在同锁内、分支store调用前，必须检查该Run全部unified_事件都属于所选fixed/program store的完整允许event_kinds且agent与该版本writer一致，使用显式tenant/run过滤的EXISTS拒绝任一未知/其他版本kind或不符agent（含NULL）。不能只检查最新一条，未知future begin/control无论比合法begin更早、更晚或夹在中间都拒；此检查在新reader完成，不改旧store。

先同tenant/run/event JOIN核原begin input/state kind、UTF8/严格整数size/hash、full payload/persistence/实际seq strictpositiveint/canonical identity、event agent/tenant/run/in-out pin；begin.state input_ref/hash原owner等后续pure校。再依据已核原begin执行显式branch：fixed原restore/ReconPublicationStore，program新restore_program_alert_read_request/ProgramReconPublicationStore；owner仅从已核ownedbegin.state.executor_id取得非nilUUID，不能从caller/header/source正文取。当前principal与历史principal分开，无mutableAlert/新查询/时钟/重试/发布。call各store._read_result_locked同conn避免嵌套事务死锁，并沿各自原begin/manifest/currentness全链读；programtyped/canonical/late拒绝保持，fixed合法旧输出语义/MD字节保持，不私改旧函数。

返回旧branch exact owned_fixed_recon_result.v1原DTO字段/值（tenant/run/profile/target/objective/legacy_run_status＋原result/progress/notification-null），新branch owned_program_recon_result.v1但相同公共字段结构、原新manifest/MD/usage/sections，新增版本只用新schema区分、不往旧DTO添字段或重渲染旧MD；Run旧status与v2执行维度继续分列。read_result无pub只progress、pub缺原件/指针错或late等拒，不偷偷publish或返回旧候选冒官方结果。权限/归属错误ExecutionRejected，driver/解析未知交易异常脱敏为ExecutionPersistenceError，不输出凭据。bootstrap对old/new都新建强元数据核验，但合法old完整DTO须同原OwnedReconResultReader逐字段和canonical字节不变。

预期SQLdouble直接：fixed和program各已pub/未pub/observer/取消、program合法revision2原begin恢复均同实际原store读，旧DTO/旧3111B fixture及sample hash不变、programnew4facts有限范围state保；current同tenant另一reader可读，foreign/emptyprincipal/nilRun/不ownedRun拒且无跨tenant lookup。marker0/2/generic/unknown（已知fixed/program begin加未知future begin/control在前/中/后均拒）/mixedagent/runtime/typedfloatseq/payload/两原件hash-kind-event/owner错误及坏最终material/MD/manifest/late全部拒，无fallback。currentAlert修改与正文指令不影响原件读；no caller version/owner接口、无新行/预算/QueryAPI/model或publication，origin/progress/cold只读。固定/新完整frozen输出重放及输入/Run6列/事件工件数/调用计数不变，bootstrap使用同lock+transaction次数核。先strict/合同独审再只d1实现/直接/结束审阅，d2—4另门，0真实PG/HTTP/Run/部署。

**b2.4c审阅修订：** 初74项外，独立合法M1 previous→revision2/newplan/newstore1event2artifact可保存却restore拒；修前源码/合法begin全件/1red0fail1应用error（非Loader错误）保[失败回执](../../../docs/operations/investigation-program-profile-restore-failure-20261025.json)。按既有profile _check_scope语义先重建固定M1 base，再带回caller已核原positive revision并全量canonical比较，不伪造previous或声称验证revision历史链；来源真实性仍caller owned链。当前修后结束独审待续。

## 2026-10-25 b2.4c新冻结只读恢复实施前细卡（b修后结束独审/保存后实现）

只新增program_profile_restore.py/restore_program_alert_read_request及测试，复制必要旧restore的M1 typed重建逻辑，但仅new program _runtime_copy/make_program_recon_plan；旧restore不变且继续拒new begin，新restore拒old/未知runtime/混版，不用版本转换或加载当前可变Alert。只读复用稳定scope/profile/JSON helpers；无真实I/O/Run/claim/外呼/新期限。

caller先核current auth/read权限、tenant/Run、唯一owned newbegin event完整agent/in-out/receipt/body/state hash和实际owner归属；pure输入current_principal、原begin_input/body及原initial begin_state，只证明完整结构/原文/ref/M1/newplan一致，不代替这些来源证明。current principal必须当前允许tenant；原frozen principal只用于重建原M1绑定，不作为当前actor许可，当前其他合法read actor可读同original context。begin必须ready/无attempt/claimed_at空、new closed版本与initial M3账canonical一致；所有JSON重建比较canonical，不用Python ==吞bool/int/float。receipt seq严格positive int、UUID非nil/tenant/run/stage/attemptNone、body hash/ref、scope hash/M1 sources与完整source set都核。

从原scope controls/schema重建唯一checked Alert/member/target、原窗口/六问/principal/revision/字段SourceField，data_only_text只从原scope_sources的sha/UTF8 size/ref还原且不截/不读活Alert；counts/revision/size等控制整数严格int（bool/float不接受），单成员/无omitted/total1保持。本函数不把任意data-only文本schema当控制，也不增全文语义或模型资格；接受已核原newprogram M1材料范围，不凭projection引用字符串证明SQL源。原source字段/UUID/IP原拼写和已冻结规范query/六问/raw全文全部留，fullsource/case/预算控制不从原文推断。

完整scope_snapshot(context)与原controls/sources canonical精确比较，BusinessProfileRequest.descriptor与原profile/newmakeplan及begin_state.recon.plan精确一致；固定manual/alert profile/有限目标，newclosed12版本任何缺多/旧项或state/profile/窗口/fields/source变化即拒，即使selfhash重算。返回等于原请求的typed BusinessProfileRequest、输出脱离输入；不授予start/restart/unknown接管，不能从原Run推新操作或重新选择budget/owner。b中同manifest/MD read无需当前Alert，c只提供纯new恢复合同。

预期：normal newformal fullsource1307B、partial/observer同newbegin均可精确恢复（传原initial begin，非当前stopped/pubstate），当前同tenant另一reader/合法扩大tenant集合不改恢复结果；原全文/refs/descriptor/newquery/newplan逐字节重建，不查询时钟或I/O。old/new/unknown互拒；source文本/ref/hash/size（含错同字节UTF8）、缺多sources、scope/主体现tenant/member/window/revision/profile/plan/closed版本任一漂移拒；self-rehashed bool/float seq/total/revision/counters/criticality等控制变化拒、当前不允许tenant/空principal拒。既有旧restore11及旧MD保持；同原b账本begin恢复后使用新pubstore read能取同newmanifest/MD/usage，SQLdouble只读无新增行/预算（actual owner前提仍caller）。先strict/合同独审再c实现/直接/结束审阅，d owned/HTTP显式分派及a4.2仍后续，不把纯恢复当所有读取兼容完成。

**b2.4b审阅修订：** 初127普通测试外独立发现pub receipt.seq 6.0与实际int6等值被接受的窄类型缺口，修前源码/1red1fail0error保[失败回执](../../../docs/operations/investigation-program-publication-store-failure-20261025.json)。new pub subclass对实际event及receipt seq严格positive int、identity数组canonical，origin/当前非pub回执同核，不改parent源码；不据此称权限/预算绕过或合法MD变化。修后结束独审待续。

## 2026-10-25 b2.4b新持久发布实施前细卡（a修后结束独审/保存后实现）

仅新增program_recon_publication_store.py/ProgramReconPublicationStore，继承新ProgramReconExecutionStore（不是旧fixed store），复制必要旧发布store结构，复用新pure package及原M3锁/append；不改旧pub/store/HTTP或已验Program runtime源。新event=unified_program_result_published、manifest kind=program_result_manifest、execution kind=program_recon_published_execution、report kind=program_recon_report_markdown，均≤40；pointer=program_recon_publication_pointer.v1、manifest_ref=program-recon-manifest:、notification=program_recon_result_notification.v1（仅descriptor/not_attempted，不发送）。

新store.event_kinds扩新pub；由于new runtime _load强核所有最新managed event，必须显式override _check_event_bodies仅接受本pub event的manifest kind/bodyhash/typed payload/persistence/state link，agent/tenant/Run与state owner按新基类校；所有非pub严格delegate super，不绕origin/unknown latest refusal。publication event实际读取完整id/tenant/run/seq/agent/payload/in-out，唯一owned pub event（0或1，重复marker拒）。不能仅改class属性再让基类把manifest误判program_recon_control，也不能让新publication绕过latest/current检查。

publish/read同owned Run锁下先_load/new _bound，所有scope/input/limits/opening原begin锚定保持；调用new _read_handoff(conn,state,request)核unique原begin/actual predecessor/closing/current recon/全部source原件，并再次要求实际tool completion的event-kind-hash/material doc的artifact/run/tenant/hash同原工具，未采用source_rejected也不能略核tool。所有retained/body/observer原件必须存在、UTF8字节/hash、同tenant/run/event、observer provenance/attempt/hash及samehandoffevent全核；prepared ProgramMaterial由新handoff reader从actual tool重建而非信其selfhash。a纯层仅给定材料语义的边界在此补完整实来源链，仍不是实际PG实测。

首次只在stopped/current candidate且无pubpointer/无pubevent时，用a new pure验证原source+实际current stopped state，写1event/4工件（manifest/state/execution/MD）同事务；manifest固定new versions/sections、execution/report持久refs及hash、published/committed、manifest_ref selfhash，state只新增pointer和write元数据，六legacy Run列不变，无查询/模型。事务全部确认后才能返回published/committed及fresh notification descriptor；任何artifact失败rollback，ACK未知不对外成功/通知、不另发查询。再次publish/cold read只读同manifest/MD/execution、repeated=true/notification=null，无新行/预算。

重复read必须核pub event完整receipt/body/state/agent/in-out及唯一marker；pub state去persistence/updated_at后canonical等于当前state，pub state再去publication后canonical等于原stopped basis，阻止pub写改scope/limits/usage/owner。所有JSON重建比较canonical，拒bool/int/float等值。原handoff/new纯package、manifest selfhash及每section/header/ref/MD/execution都按原stopped basis完整重建比较；任何later actual settlement即当前性不符则拒旧published，不把旧MD配新usage、不自动重发或新版本。无pub时read_result只保not_published/progress/已存在candidate，不自动publish；已pub但pointer缺失/错schema/unknown kind/半工件/断source链拒、不回退progress。

预期SQLdouble直接：normal5/10→publish6/14，4facts有限ready、全部4新工件sameevent和精确hash；重复/cold完整输出一致/MD确定性/no新call。空/unknown/observer/取消/source拒均新published partial，未确认不伪事实；bad source即便未采用也pin全部原tool。并发publish只一个fresh；4工件逐项write失败rollback到5/10，实际pub commit后ACK丢失仅显式cold read恢复同manifest/无notification重发。错tenant/owner/begin/current/版本/typed bool/multiple pub markers/指针/seq/event-agent/in-out/所有工件hash、tool/kind/event/材料refs及后续late结算一律拒。new Runtime使用新pub subclass仍能初次执行/同版停止读，旧pub/旧MD保持。只SQLdouble不接PG/HTTP、无新Run/部署/通知投递；c恢复/d owned+HTTP和a4.2仍后续。先strict/独立合同再本b实现/直接/独审保存，a未结束不编码。

**b2.4a实现审阅修订：** 初109普通测试之外，独立发现bool true/int1等值和stopped state冒充pre-source两个P2；修前源码/2red2fail0error保[失败回执](../../../docs/operations/investigation-program-publication-preparation-failure-20261025.json)。改checked/raw、finish current、usage等JSON全部canonical比较，source须claimed/blocked且source/current artifact ID distinct；实际历史seq/原件真实性仍bstore门，a不扩权限承诺。修后结束独审待续。

## 2026-10-25 b2.4兼容分块及a纯新发布细卡（d2结束保存后实现）

d2完成后按a纯program publication/renderer→b新ProgramReconPublicationStore→c新pure restore→d owned reader/HTTP显式版本分派逐门，不改已有fixed publication/store/restore/reader/app/gateway函数、旧源schema/策略或旧MD3111B。未知owned begin/runtime/intent不回落，真实启动a4.2要待b2.4全部通过。b/c/d各自后续细卡/独审，本卡只a。

a仅新program_recon_publication.py/prepare_program_recon_publication及测试，复制必要旧M7a发布校验/状态映射/escape/render骨架，可只读复用checked_artifact、_fact_text等稳定纯helpers；不把ProgramMaterial伪装成EvidenceView。新manifest=program_recon_result_manifest.v1、execution=program_recon_publication_execution.v1、sections=program_recon_handoff_sections.v1、mapping=program_recon_publication_state.v1、renderer=program_recon_markdown.v1、package=program_recon_publication_candidate.v1/ref=program-recon-publication-candidate:。新manifest及execution明确完整closed policy_versions，版本不由caller选；old prefix/schema混入拒，old函数/oldMD保持。

输入为caller已核owned request、handoff/source-state/current-stopped-state三工件；纯checked只字节/hash/格式，不证明实际event/租户归属，后续b新store再核全原件链。new handoff schema/ref/closed versions/plan/profile/scope/目标及result新schema/ref严格，sixQ/性质unresolved/授权unknown/stopped、有限完成政策匹配。source/current经new _runtime_copy，new finish从source按原stopped_at重建current（除persistence），全部账/输入/limits/owner及handoff/event/link一致；有late结算或当前pub/更新就拒stale，不能旧candidate配新usage。candidate.execution须同原current usage/cancel；observer引用保留不作为source。

validated preparation只能program_alert_recon_preparation.v1/program_material_validated；program_material_document和snapshot_ref及all policy refs一致，构造独立ProgramMaterial并checked/evaluate新有限政策重建result、exact canonical比较，杜绝自洽rehash伪facts或model eligibility；材料工件归属仍caller/后续b核。无preparation只能program_runtime_unadopted_result.v1，prefix正确、facts=[]/partial/validated_source_refs=[]/program_material_state=missing/source_state=not_confirmed/available=null/execution_state=unknown，原实际refs/停止/缺口保持，不伪来源可用性。该分支也必须用new None evaluator＋固定允许material_adoption_reason/source_material_rejected或tool_output_not_confirmed或query_not_started＋实际execution_stop及retained_artifact_refs，重建与ProgramReconExecutionStore._without_source相同的完整结果并canonical精确比较（可只读复用此纯static helper）；不只检查上述局部字段。sixQ状态/criticality/依赖/coverage/held refs/所有gap/handoff等任何自洽rehash漂移均拒，增加Q3a支持/criticality改写/伪整窗已查反例。section evidence指向/preparation/program_material_document（有则typed ProgramMaterial），无材料为空；非旧model_view。

有限ready才finished/complete_for_scope/none；否则stopped或cancelled/partial/awaiting_human，human_acknowledged=false。manifest保profile/target/objective/scope/revision/coverage/new result/runtime/version/原工件sections/hash/held/observer/unknown-unsettled-unpriced；candidate only、report与execution持久refs为空、publication not_attempted。新MD确定性展示实际typed事实值/六问/窗口/有限目标及程序材料状态、全文未语义核/模型未请求与无资格/性质授权未知、缺口/所有refs/实际用量/续接，不回显原自由文或执行源指令，escape所有不可信字符串，不触发Case/关闭/通知/查询或模型。

预期a直接：d2普通source/new handoff产新明确manifest/MD四事实有限ready，反例空/失败/unknown/无确认observer/取消/期限/被拒source均partial且所有refs/未知真实保持；同输入逐字节稳定并输出脱离。old/new schema混搭/缺多版本/错snapshot/ref/hash/文档model标记/伪facts/错ready/陈旧usage/cancel/跨scope/owner与状态不一致拒。old fixed preparation/MD原字节保持，a无PG/HTTP/Run/发布提交。先strict/独立合同再本a实现/直接/结束独审；b之后仍须单独验收，不以candidate声称已发布或通知。

## 2026-10-25 b2.3d2新版正式来源投影实施前细卡（d1结束保存后实现）

只新增program_alert_projection.py/project_program_alert_start及新直接合同。复制必要旧full projection校验/组装，不改旧alert_projection/start函数或用旧intent版本转换；先program_replay_decision完整校new intent/closed版本，之后caller已核current tenant/actor/双权限及owned四列Alert前提同b1。严格单source UUID/单telemetry、source tenant/event一致、TCP443/已核字段和显式路径；普通来源不依赖synthetic/evaluation答案/固定文本，多/重复/缺失/不支持一律拒，原JSONB完整保留无截断/提限。

新完整document schema=canonical_program_alert_recon_projection.v1，其source/source_sha256/normalized projection/field_sources/normalization语义同b1。完整来源字节哈希进入CheckedAlert.data_only_text及checked_projection record_ref#projection/M1 scope sources，原UUID/IP拼写保全，实际查询M1规范化；正文的instruction/profile/budget不作控制。该文档新版本不重写旧已冻结原件，new intent唯一决定manual/new runtime，newcontext目标/Run/window/refs完整对应request；只生成BusinessProfileRequest，无claim/QueryAPI/模型/Run持久操作。

预期纯：普通fullsource/等价JSONB/原路径/原文/大小上限/所有缺失歧义/跨tenant/event/源正文指令等b1反例保留；新projection拒旧/未知/混版intent，旧projection明确拒新intent，新函数不调用旧projection或旧normalize。额外SQLdouble+MockTransport集成以预建owned Run执行newProgramRuntime：begin先1event2artifact、scope_source完整，旧restore明确拒新begin（未兼容不能伪读通过）；随后一次Mock固定查询新有限4facts ready且model eligiblefalse，重复不新调用/行，原Run6列不变。不接真实PG/HTTP/模型，不声称a4.2启动或b2.4恢复发布兼容已验。先strict/合同独审再只d2实现/直接/独审保存；下一b2.4纯发布/持久发布/新restore/owned/API显式版本组合及旧MD字节保持。

## 2026-10-25 b2.3d1新启动意图实施前细卡（c结束放行后实现）

仅新增program_start_contract.py的normalize_program_alert_start/program_replay_decision及新直接测试；旧start_contract原函数/旧request/intent固定版本保持，不重解释既存原意图。只读复用原StartBudgetPolicy及其fixed_alert_start_budget.v1描述（0model/0token/0cost、0或1工具、unsettled1、duration1..180、配置来源全部显式）；这些额度语义未变，不改服务器预算或引入默认。复制必要normalize/checked/replay结构，不用把新请求改写成旧版本后调用旧normalize/旧projection的方式转换。

新request=program_alert_recon_start_request.v1、intent=program_alert_recon_start_intent.v1/ref=program-alert-start-intent:、decision=program_alert_recon_start_decision.v1。请求固定manual/alert/profile version/有限目标及M1政策，新runtime/new completion，新增完整policy_versions由b2.3a代码固定生成并纳入request_hash/intent_ref；调用者不能自选混合版本，未知/缺/多/旧组件即使自洽rehash仍拒。其余current principal/typed非nil tenant/actor/key/alert、UTC窗口≤5min/完整budget重建规则同旧。

operation Run身份继续uuid5(NAMESPACE_URL, canonical[同OPERATION_NAMESPACE, tenant, operation_key])，executor仍uuid5(Run,exclusive-initial-start-owner)：故同tenant/key新旧及不同actor/target/window/budget/版本均落同身份，不靠版本制造新Run或刷新额度。新请求必经完整checked重建；已owned retained新意图仅全量精确相等可read_existing_only，异文冲突。retained旧intent只按旧checked函数验证原格式/身份后明确同key异请求冲突，不能升级或执行；不同key/tenant身份错另拒；未知schema拒。旧replay同样拒新intent，双方无fallback。changed current凭据同actor请求可稳定同一intent，但身份认证/permissions/retained ownership仍是caller前置而非这些selfhash证明。

纯decision仍both may_begin/external_call_authorized=false及not_verified_by_pure_contract，不生成实际deadline/Run/claim/持久marker/查询/模型。预期：新全版本正确、同输入/等价UTC稳定；与旧同key同Run/executor而请求hash/ref不同且双向冲突；actor/target/window/budget变更同Run但拒复用；未知/错/缺/额外版本及结构篡改自洽重hash仍拒、所有严格整数/UUID反例维持。先spec/strict/独立合同再本d1实现/直接/结束独审；d2新projection仍另门，b2.4兼容全部通过才a4.2。

## 2026-10-25 b2.3c薄单次控制器实施前细卡（b结束放行前不实现）

在b修后结束独审/提交后，仅新增program_recon_runtime.py/ProgramReconRuntime及直接测试；复制所需既有FixedReconRuntime控制骨架，新constructor只接ProgramReconExecutionStore及new make_program_recon_plan/manual request，不改旧controller/store/gate/API。复用DurableActivityRecords唯一M3 reserve/settle和activity_records限定查询，不复制预算内核/HTTP业务，不接模型、自动策略、Case、发布或真实PG/HTTP。begin仍只owned既有Run中明确begin_recon；本块不插入Run，不接启动intent。

execute先实际store.claim：首次已确认提交才拥有该调用认领；预检非授权，gate必须原子M3 reserve确认后才单次HTTP。claimed重复in_progress_or_interrupted；stopped只读完整原handoff并核未清进程observation，无HTTP/新行。blocked且非本调用首次认领返回blocked_handoff_pending，不能替owner抢finalize；控制/来源不变量拒不降为预算停止，只有已观察deadline/budget/unknown/retention才明确交接。claim或reserve ACK未知不重派，保原M3 attempt/unsettled；M3 reserve失败类型按原gate报明确控制，不能暴露driver敏感文本。

实际响应有M3确认原completion就用新程序prep；complete无确认而本进程有输出只留独立observer，不采用为source或清unknown。finalize提交/冷读确认全部原件相符后才清process buffer；handoff失败/ACK未知保buffer，不用新请求重试。当owner在HTTP或complete期间取消，最佳努力保存cancel/unknown及已有进程输出后重抛；重复调用被取消不能取消原owner。取消标记与owner observer交接之间，另一重复只能pending，不能抢封无observer结果；如果外部已封不含本观察的记录，read拒且buffer保持。所有这些控制语义保既有已修竞态，新增当前控制/原handoff断链即拒且无HTTP。

预期：完整1299B Alert、一次MockTransport响应经真实newstore/M3/gate得到4有限程序facts/ready且model not_requested/eligiblefalse；冷读samecandidate且calls=1。0额度/到期无HTTP，deadline在claim/reserve间变化能停止；并发重复、claim/reserve ACK丢失/rollback无第二请求；未知/complete失败observer partial；完成ACK丢失读实际原completion不重查；取消HTTP/complete与重复竞态、handoff失败buffer/不重跑均直接核。旧FixedReconRuntime与旧MD字节保持；旧store/genericstore/automatic/Case拒。仅SQLdouble+MockTransport，不算真实I/O、正常启动或b2.4同版发布已验。先strict/合同独审，再本c实现/测试/结束独审；b2.3d及b2.4依次后续。

**b2.3b审阅修订：** 独立85普通测试之外发现4个P2原件完整性反例：最新claim agent、当前stopped区与候选不一致、late后缺handoff state、候选挪用更早begin。修前源码/作者3红测3fail0error与独立第4复现保留[失败回执](../../../docs/operations/investigation-program-runtime-store-failure-20261025.json)。补最新event/payload/body/state完整pin、交接真正前一managed事件、由原source和event时间执行finish重建handoff全state、当前recon停止区与原handoff一致；合法late实际仅账本变化，既有candidate不改。本b结束独审尚待，不作为可用入口。

# Design: 独立调查v2的原设计与集成边界

## 2026-10-25 b2.3b程序运行持久store细卡（f4429e0）

a纯状态已69/独审通过并推送。本b只新增program_runtime_store.py/ProgramReconExecutionStore直接继承ExecutionStore；不改旧store、base M3、controller、HTTP或真实库。新event_kinds=原M3三kind＋五新control kinds，runtime_version/event_agent钉program_alert_recon_runtime.v1；新control为unified_program_recon_started/claimed/cancelled/handoff_saved/dispatch_blocked，artifact kind为program_recon_control/program_recon_handoff/program_recon_unconfirmed_observation，均按40/80列上界核。通用settled和step_input/output/state_snapshot名称保持，不破M3回执。

begin_recon只已存在owned running且completed_at null Run，无任何unified_阶段标记；actual caller负责Run来源，a4.2以后再原子新建Run/操作。原M3 authoritative clock/parent deadline min、BudgetLimits/OpeningUsage及新install冻结manual profile/完整policy_versions/plan，begin仍input={business_profile,runtime_plan}+scope_sources+scope_hash严格shape、1event/2artifact原子，不触Run状态/计费列。通用begin禁用，旧/generic stage存在即拒，不重置。返回只在commit确认后；ACK未知报持久不确定而非授权派发。

新增原始begin归属基线核验（origin）：同Run锁内唯一begin（generic/旧fixed/新program begin集合取最多2且必须唯一新program kind/agent），owned begin input/state两工件kind/event/hash/UTF8及payload/inputHash/receipt/identity/current input_snapshot_ref全部相同；原初state必须ready/无attempt/closed新plan。current scope/scope_hash、limits/deadline、opening_usage不能偏离此原基线，拒同时替换当前scope/request/limits来冒用旧输入。begin输入与请求重建的profile/plan/source全部canonical精确比较，不用bool/int宽松dict等号。读取/claim/reserve/取消/finalize/handoff均核相应基线；只给current_state selfhash不能证明原件归属。M3 complete仍复用原最小owner/attempt/hash路径以留真实迟到结算，之后decision/发布须再核原件和当前性。

claim只首次原子写控制事件才有needs_commit=true，重复claimed/blocked不接管，所有decision仍external_call_authorized=false；reserve先核原基线/scope与纯限定plan，再真实M3 reserve和工件同TX提交，只有其确认回执可给后续gate外呼。取消/dispatch_block保当前实际停止/固定owner、不抢先覆写。所有budget/now来自原M3，M3 complete和unknown/late-settle保持，不新增Run列计费写。

finalize先核control和原工件，原tool需由M3 completion_receipt指向同event/unified_step_output/pinned hash；这些控制或归属不变量错直接拒。仅已核owned工具正文不合格（含不能解析为对象/必要来源字段错误）可以保留原件后明确未采用，不降为模型不可用。合法tool只用新prepare_program_alert_recon，validated prep/version/材料文档与result真实相符；无合法tool或未确认请求用新unadopted分支。未确认进程输出只单独observation，marker=process_observation_not_original_completion，attempt/hash/正文及同handoff event核验，不喂prepare、不当原completion或释放unknown。

未采用结果schema=program_runtime_unadopted_result.v1，ref prefix=program-runtime-unadopted:，从新None evaluator生成；无事实/partial、validated_source_refs=[]、source_state=not_confirmed/source_available=null/execution_state=unknown，reason仅source_material_rejected/tool_output_not_confirmed/query_not_started；held_refs为scope-source refs与所有实际owned begin/current state/tool/observer refs并集，原停止优先。source是否可用/是否SQL执行不能从不合格正文猜成false。handoff schema=program_recon_runtime_handoff.v1/ref=program-runtime-handoff:，封闭policy_versions与plan/profile/scope/版本、prep/result、retained_artifact_refs、原state/M3usage/Run总量及观察引用同事务保存state/handoff（可选observer增加1artifact），未提交不声称committed。

重复finalize/read_handoff只核原artifact hash/event/schema/ref和版本/plan/profile/result，当前状态引用/pinned tool/required held artifacts和observer必要关联逐项核；新观察正文须与原tool或原observer一致，不能覆盖旧handoff或清未留存buffer。late实际结算保新账，不改已保存candidate；陈旧正式发布仍b2.4拒。新store不调用QueryAPI、模型或M7，只有内存SQL transport direct tests。

预期：begin1/2→claim2/4→reserve3/6→settle4/8→handoff5/10，normal全文1299B新有限ready/4事实；两claim只一次first，重复/cold精确同handoff/无新行；0tools/到期/取消/unknown/被拒正文/未确认输出/5类停止保partial和原M3额度。错tenant/owner/初始marker/全部原input/state/plan/limits/opening变更或tool pinned hash/kind/event破坏都拒，不写半段。各artifact写失败rollback；claim/reserve/交接ACK未知不返回外呼许可、显式cold read原件不重开预算；observed未确认单独存且不能伪facts，冲突观察拒。legacy Run六选中列不变/无新Run/真实PG/HTTP/模型/发布。先strict/合同独审，再本b实现/直接/结束审阅；c、d及b2.4仍后续。

## 2026-10-25 b2.3拆分及a纯状态/闭合版本细卡（e2b0291）

b2.2已64/独审限定通过并推送。采用fresh_design只读建议，b2.3a新program_runtime_state纯状态→b新program_runtime_store持久层→c薄ProgramReconRuntime/MockTransport→d1新start intent→d2新projection入口，逐块细卡/测试/独审。不改旧recon_runtime_state/store/FixedReconRuntime/start_contract/alert_projection；只读复用M3通用state/reserve、ExecutionStore锁/append/complete、DurableActivityRecords，不复制HTTP服务/预算内核。b2.4发布/恢复/owned/gateway组合兼容和旧MD字节不变后才a4.2，本b2.3无真实PG/HTTP/部署/发布。

a仅新增program_runtime_state.py纯plan/install/runtime copy/claim/限定reserve/stop/cancel/finish及直接测试。runtime=program_alert_recon_runtime.v1，state schema=program_recon_runtime_state.v1，plan schema=program_recon_plan.v1/ref prefix=program-recon-plan:；scope政策仍network_observation.v1、business profile仍investigation_profiles.v1 alert_recon。完整policy_versions对象固定包含M3 execution_schema=investigation_execution.v1及上述runtime/state/plan、network_program_material.v1/network_program_material_policy.v1、finite_network_program_fields.v1、bounded_full_window_program_fields.v1、program_alert_recon_preparation.v1、program_alert_recon.v1、program_recon_runtime_handoff.v1、program_runtime_unadopted_result.v1。调用方不能逐项自配；未知/缺项/多项/混旧版本即拒，即使自洽重hash也不接受。

合同独审补清trigger权威：本新runtime仅支持manual（匹配当前a4手动范围），make/install拒automatic，runtime copy用受控scope＋固定manual重建完整descriptor，不能从待核plan借trigger自证。未来automatic需独立合同/版本，旧automatic运行路径不变。make_program_recon_plan只接已核manual BusinessProfileRequest，固定全结论窗口Q1/activity_records单成员/现参数限制。用规范scope controls/业务descriptor重建closed plan，scope/profile hash、当前query完整结构、上述版本组合及所有关键字段精确；plan不能额外夹带可改变行为的字段。query fingerprint纳入完整版本组合＋scope hash＋query_input，step UUID5在新program-recon命名空间派生、attempt=uuid5(step,attempt-1)，subtask=program-source-observation-Q1。身份只确定本步请求，不授予I/O；同Run无法借改版本新增可执行attempt。

install只允许已核M3初始state（现SCHEMA_VERSION统一预算）无runtime/无attempt时一次安装；新recon key仍沿phase/plan结构但schema/runtime与旧分开，旧state/plan一律不升级。state/runtime copy核基础owner/stage/scope及新schema/phase/stop/完整版本/plan/profile/step/attempt，按受控原scope重建expected plan再canonical比较，不把自hash等于合法。caller仍须核scope来自owned begin/真实权限，纯层不证明存储归属。

claim/reserve/stop/cancel/finish沿已验M6.2控制语义：只ready首次可提交claim，预检用M3 reserve临时副本、预算/期限/unknown/unsettled依原M3，不另设账；claim不授权外呼，必须提交claim与真实M3 reserve后才可。claimed重复in_progress_or_interrupted、不接管；blocked重复不能抢owner交接；stopped只读原handoff。限定reserve只本plan的Q1 tool/step/attempt/完整参数/0 token和0预留费用，不接新model/其他query/重试。budget/deadline/unknown/retention/cancelled保优先级，真实late settle允许但不重跑；finish只保owner当前实际观察停止及原handoff引用，重复不覆盖。

预期直接：正常fullwindow plan/旧M3预算保持、新组合及ID独立；new/old profile descriptor同M1绑定但不同runtime不可混。任一policy_versions/schema/profile/plan/参数/窗口/step/attempt/额外字段自洽改hash仍拒（必要原件归属另在store核）；ready首次/重复、真实M3预检额度0和deadline/期初unknown、限定reserve所有反例、cancel/finish当前stop/重复引用不变、原输入/预算计费列不变。0 I/O/Run/真实claim/reserve/模型/工具。先strict/合同审阅再只a实现/测试/结束独审；b以后不在本卡批准。

后续b采用新control kinds unified_program_recon_started/claimed/cancelled/handoff_saved/dispatch_blocked（均≤40）及program_recon_control/handoff/unconfirmed_observation工件；通用M3 unified_attempt_reserved/settled与step_input/output/state_snapshot不改。未采用结果必须新program_runtime_unadopted_result.v1，以None新evaluator为基础、validated_source_refs=[]/无事实/partial、held refs并集，不能机械复制旧without_source的false可用性；控制归属/hash不变量错仍拒，已owned内容不合格只可明确未采用。未确认进程输出独立observation，不喂prepare，handoff/state/观察原子、重复只读。c保既有取消竞态修复/单次派发；d新intent显式钉新组合且tenant/key Run命名空间不变，新旧同key冲突、未知schema拒，不把新intent改写旧版本去投影。各块后续另审。

## 2026-10-25 b2.2程序有限事实与preparation细卡（984646f）

b2.1已59/独审限定通过并推送。只新增program_recon.py新evaluator/prepare函数，保fixed_recon/recon_material/EvidenceView原函数和原版本不变，不接runtime/发布/HTTP。新ProgramMaterial仅经checked_program_material校当前scope/当前snapshot/ref后消费；不能接EvidenceView或把ProgramMaterial包装成model_view。复用纯有限谓词的字段/引用规则（内部typed records/query/alert索引），不产生模型候选/自由文判决。

版本明确：fact_policy_ref=finite_network_program_fields.v1，completion_policy_ref=bounded_full_window_program_fields.v1；result schema=program_alert_recon.v1、result_ref prefix=program-recon:，preparation schema=program_alert_recon_preparation.v1、prefix=program-recon-preparation:。每个fact的ID prefix=program-field-finding:且hash含事实政策、当前material snapshot、binding、question/typed predicate/refs；origin=program/assurance=rule_checked，revision依当前材料，源/查询/Alert refs及scope-source refs可追踪，不伪作模型采用或源正文语义判断。

新结果完整保六问题、原criticality/依赖、coverage/held refs、性质unresolved/授权unknown、全Run未发布。仅现有七种有限谓词network_observed/outcome_unknown/alert_linked/source_versions_conflict/bounded_query/query_empty/source_unavailable；来源记录字段动作不支持、冲突/缺版本/截断/正文提取缺口、空/失败/未知或子窗口继续原拒绝/partial约束，不放宽。Q2未精确匹配仍列gap但保原非决策语义；Q1/Q5是有限目标决策项。正常完整查询有typed observation及Q5支持、无blocking gap才ready；不是恶意/授权/影响或全Alert已分析。

program_result明确material_schema/policy/fact/completion refs、program_material_state及snapshot_ref（program-material:）、model_projection={not_requested,eligible_for_model:false}、free_text_semantics=not_assessed_by_program_material；coverage_gaps另外明列alert_free_text_not_semantically_assessed和model_projection_not_requested，这两项在“有限结构字段目标”下为非阻断，不得静默解释为自由文字已读。full source refs只表示已由caller核留存，可追溯全文；不构造模型视图也不声称其门已通过。

evaluate_program_alert_recon(request, material或None, current_snapshot_ref, execution_stop)始终返回stopped和交接，ready停止因limited_objective_answered/否则material_gap，owner已观察budget/deadline/unknown/retention/cancelled优先保原停止原因且partial/保合法事实。execution_stop仍是可信owner输入，不是本纯层证明实际M3预算/时钟。materialNone必须snapshotRefNone，partial/无事实/明确committed_source_material_missing，source_state=not_confirmed/source_available=null/execution_state=unknown，不把unknown当空或不可用已证。材料错误/陈旧snapshot/跨scope/type/hash/不支持profile或stop值直接拒，不降格造成功。

prepare_program_alert_recon只对caller已核owned/committed的tool材料build_program_material→evaluator，不重查/模型/留存。新prep字段material_state=program_material_validated、program_material_document/snapshot_ref和真实新schema、result、version refs、model_projection状态、persistence_status=not_attempted；validated只指结构材料，不等于来源可用或调查ready。必要builder错误传播，不能catch成projection_blocked或回旧report。b2.3未来外呼前冻结这组政策，b2.4再按真实program material section发布/恢复/读取；本块不能交旧M7假装view_ready。

预期：同b1正常1299B/同window/source原A3partial，新纯prepare4条合法有限事实+Q1/Q2/Q5支持/有限ready；原短scope十512B转义消息旧model complete_view受阻，新程序路径可保真实有限事实/ready，模型仍not_requested/不具资格。普通raw Alert指令不选政策/扩大目标。空/failed/unknown/无材料、冲突全部/缺版本、截断、源excerpt缺口、子窗、5类停止逐一保原事实/gap/partial；wrong tenant/hash/scope/源version/当前snapshot/type拒。当前Alert/输入及预算不改，旧同输入输出/schema/MD样例无新写入；这只是纯政策，不代表新runtime/start/发布已接。先strict/合同独审，再仅b2.2实现/直接/结束审阅。

## 2026-10-25 b2分离路线与b2.1已核程序材料细卡（c253f15）

b1完整来源冻结已47/独审限定通过并推送，normal1299B仍受现Alert512消费门。fresh_design技术复核采用A窄路线：保b1全文及scope_sources留存方式，新增独立程序材料类型，不用短摘要替代原件、不catch EvidenceProjectionBlocked后伪造EvidenceView。b2.1纯材料→b2.2新有限事实/preparation→b2.3新版本runtime冻结/接线→b2.4发布/恢复/owned/API同版兼容，四步逐次规格/实现/测试/独审。全部集成和正常有限ready通过后才a4.2，不因本步材料可建称新路径可执行。

b2.1只新增program_material.py：不可变ProgramMaterial/canonical document，schema=network_program_material.v1、正整数revision/scope hash及独立program-material:内容ref。入口build_program_material(context, query_result, CommittedMaterial, revision)；当前context/frozen begin全文及tool工件已owned/committed由可信caller核，纯层沿原材料/hash/参数/来源版本校验不证明实际存储。新类型不继承EvidenceView、没有model_view，不可直接传现模型/采用接口。

校验代码仅在新函数复制所需构建段并只读复用现稳定helper：query payload canonical hash/tenant/source Run/member绑定、参数/范围和receipt/count/执行、M2完整响应/body/hash/UTF8、各source content/version/冲突全版本/重复prefix一致/截断均沿原判据，任何必要错误仍拒而非降为模型不可用。原_message提取及source_excerpt缺口判据保持；本版只解除Alert全文512门及完整模型视图12KiB对程序材料构造的耦合，不顺带放松空/失败/unknown、子窗、截断、冲突、遗漏版本和源正文提取缺口的后续ready约束。现evidence_view及A3/model路径源码/行为不改。

材料文档含完整结构events（所有交付版本/短excerpt或明确提取缺口）、query及coverage/gaps、全index/来源回执/版本/hash；alert只含identity/source IDs、完整data_only_source的scope-source ref/hash/UTF8字节、原record/ownership refs，不复制正文、不把ref当已语义消费。scope_sources只列实际冻结上下文的全部ref/hash/字节，全文仍由原begin保存。program record index字段命名program_record_sha256，不能标为model_visible。model_projection明确not_requested、eligible_for_model=false；free_text_semantics明确not_assessed，不能说整个Alert已理解。材料整体沿现1MiB JSON上限，未造新生产默认。

输出自hash/scope/revision检查函数仅核当前材料结构和当前snapshot引用，不授予auth/owned或执行；模型必仍走原512及完整I2门，程序材料不能用EvidenceView名义绕过。相同输入deterministic且返回嵌套副本，source/index缺口可审查。b2.1没有facts/ready/preparation/Run写入/模型，b2.2才按新政策评价。

预期：b1正常1299B原视图blocked而新材料可建、完整Alert只保原begin refs/sha/size（正文不复制），实际events/query/来源版本及gaps完整，normal/JSONB等价/映射IP/Unicode/指令source均不改scope或政策；旧短Alert可用视图/长Alert阻断保持。十条合法512B转义message导致旧完整视图≥12KiB时，新程序材料仍按自身1MiB合同构造，不称模型可消费。坏tenant/hash/sourceRun/query/scope/源version/body/关联必须拒；多版本冲突/缺版本/截断/空/失败/unknown和子窗口仍原样入材料及gaps，不变成完整。新schema/hash/revision/scope/ref或嵌套bool/int篡改需拒，类型不可交旧checked_view；无I/O/Run/调用、输入不变。先strict/合同独审后仅b2.1实现/直接测试/结束审阅。

b2.2须新material/result/preparation/完成政策ref，固定谓词仅读真实程序材料，正常full-window有限事实ready，保Q3a/b/Q4未评估/性质授权未知/未做自由文语义；b2.3新start intent与begin在外呼前显式冻结新runtime/material/facts/完成组合，源正文不能选策略，unknown/停止/唯一writer不变；b2.4新material section不假装model_view，M7/a1/owned/gateway显式支持新旧组合，旧正常/partial的manifest/MD字节保持、当前Alert编辑不影响历史读、缺原件不补造。只有这些门闭合才进入a4.2，其他Case/Deep/自动政策不在本b2。

## 2026-10-25 M8a4.1b正式Alert纯投影细卡（9bc7498）

a4.1已44直接/独立限定通过并保存。合同独审先发现必须修：完整文档结构性超过现EvidenceView Alert 512B门，极简示例未含field_sources已691B；不只是偶发大小问题。选定拆步：本b1只验完整冻结和与M6 begin/a1恢复，当前正常短来源也会触发消费阻断、本块只能验证明确partial交接；随后b2独立合同/实现分离完整留存与有界消费视图，正常有限事实/ready通过后才进入a4.2，不能据b1放行可用启动。512/I2门不扩大、原件不截断。b1只新增纯alert_projection/project_alert_start，输入为本次规范intent、当前TenantPrincipal、可信caller已owned SELECT所得canonical Alert的四个字段id/tenant_id/source_event_ids/raw_event，以及非空ownership_check_ref。不得把HTTP正文或仅有ref字符串当归属证据；实际认证/permission/同事务SQL在a4.2/3。复用a4.1严格intent重建，current tenant许可独立核；调用方还须将当前actor与intent绑定。本块不读DB/创建Run/派发。

当前network_observation.v1仅支持raw_event为JSON object，telemetry为恰好一个object，root source_event_ids恰好一个非nil唯一UUID且等于该telemetry.event_id，telemetry.tenant_id等于canonical/current tenant。多telemetry/多个source ID先明确unsupported，不能默认第一条/静默裁剪成已覆盖。host/source_ip/dest_ip/dst_port/protocol从该真实telemetry取、类型严格，沿M1已支持TCP/443；无synthetic必需/评分卡参数/固定测试正文。异租户/目标、缺字段/非法JSON/空缺或重复来源/歧义/不支持协议均在首次准入前拒，原Alert不变，不补假字段。此窄支持面不是全量告警解析器。

冻结文档canonical_alert_recon_projection.v1包含source（四字段完整PG选中值，JSONB可由字符串解析，原始嵌套文本值不改）、source_sha256、projection（显式hostname/src_ip/dst_ip、规范source_event_ids，以及原dst_port/protocol的最小raw_event.telemetry[0]映射）、field_sources（逐参数到source中的真实路径）。正文只作data_only，来源中的instruction/profile/预算/结论文字不成为控制；IP原表示留source/SourceField、CheckedAlert沿A1等价归一化。record_ref绑定整个文档hash及/projection，M1参数路径相对该显式projection而非声称PG有hostname/src_ip/dst_ip列；source_event_ids规范UUID另保原JSON数组于source。PG JSONB的canonical快照不能声称原Kafka wire字节已恢复。

输出仅BusinessProfileRequest：原intent tenant/Run/窗口/profile/有限objective，单成员CheckedAlert和target/ownership ref均服务端构造，data_only_text保上述完整文档；make_recon_plan/scope_snapshot沿原M1/M6，不改旧函数或M1路径。canonical_json沿现1MiB材料上界，超限拒且不截断；这不保证后续M3序列化或I2消息门一定通过，各自原gate仍执行。匹配重复应在a4.2读原意图和冻结begin，不再投影当前Alert，故当前Alert后来编辑不改变原Run。

预期直接测试：普通非synthetic/有指令文本完整冻结且控制不变；JSONB字符串与parsed形式同投影；每字段真实路径/原raw hash/Unicode/SourceField原IP与canonical过滤、所有ID/ref/窗口/计划精确。缺/多telemetry、缺/多/重复/错/nil source ID、wrong tenant/alert、非法JSON/端口bool或str/协议/超限均拒且源对象不改；来源后来变化产生不同doc/source hash而非覆盖。与真实M6 begin内存SQL输送及a1恢复至少一例，验证严格begin shape未变，不误写持久或auth已验；另以正常小来源实测文档>512B导致现A3 material_projection_blocked/alert_excerpt、facts空/六问题unassessed/partial，不能写成ready。先strict/合同独审，再只纯b1/直接测试/结束独审；b2分离消费与完整留存是a4.2前必须门，细卡另写。

## 2026-10-25 M8a4启动分块与a4.1纯操作合同（77e9f4d）

a3.3已真实/独审限定通过并保存推送，只读不代表已启动。fresh_design只读预审后采用a4.1纯操作→a4.1b正式Alert投影→a4.2同库原子准入→a4.3显式写权限/派发→a4.4受控新Run顺序；新业务只手动alert_recon/现网络有限目标，不接Case/自动策略/Deep。实际PG三表41列/10约束已定向核：Run PK可竞争，case_id必填文本非Case FK，events(run_id,seq)唯一/append-only；优先评估确定性Run PK+独立不可变操作工件方案，但a4.1不证明持久唯一、不执行DDL。

a4.1仅新增纯start_contract。可信调用方每请求先核当前认证/租户/actor和investigation:run＋alerts:read；TenantPrincipal/actor结构检查不是实际permission验证。只收tenant、当前actor UUID、operation key UUID、Alert UUID、显式UTCWindow及可信服务端选定的版本化预算政策；manual/profile/request版本明确，只支持当前alert_recon。后续HTTP不得接受自定Run/owner/scope/source正文或任意预算数值；策略选择/正式body与权限在a4.3另卡，不改既有service read权限。

操作key在tenant内的统一调查启动命名空间唯一。Run ID只由固定namespace＋tenant＋operation key派生，owner只由该Run派生；不能把actor/目标/窗口/预算/时间混入身份以绕开同键冲突。request hash包含actor、目标、规范UTC半开窗口（复用M1≤5分钟）、profile/请求/运行/完成政策版本及完整预算政策；同键改actor/目标/窗口/预算均为冲突，不派生新Run。不同当前凭据映射到同actor可核原回执，换actor持同key不接管。IDs和hash不授予执行权。

预算政策由服务端可信配置传入、无隐式生产默认。当前固定程序路径只准max_model_calls=0、max_tool_calls为0或1、max_tokens=0、max_cost_microusd=0、max_unsettled=1及duration_seconds为1—180整数/明确config_ref和旧映射说明（沿既有M3受控180秒上界，无生产默认）；0工具可保留到限交接语义。借用M3 BudgetLimits核类型/组合，纯操作只有duration，无now/absolute deadline。首次a4.2才用PG时钟冻结accepted_at/deadline；匹配重试用原保留政策/原deadline，不按当前时间重建额度。原始请求不得补交不同政策正文；明确选择不同预算政策仍是同key冲突。

输出规范化alert_recon_start_intent.v1（完整请求、request_hash、稳定run/executor、intent_ref）。纯replay_decision只接调用方已核owned/hash的保留intent，先核完整结构/版本/规范hash和派生身份，再canonical JSON精确比较：无原件仅requires_atomic_admission、有匹配原件仅read_existing_only；两者may_begin/external_call_authorized均false，claimed/unknown的处理留持久层，不能纯函数冒称去重已提交。坏原件/同键异文/不同身份明确拒；输入不变，0 I/O/Run/额度/查询/模型。

直接预期：同一操作及等价时区表达规范一致；更换key或tenant才更换Run；同key改actor/Alert/窗口/预算内容或config ref身份不变而hash变/replay冲突；空/跨tenant主体、nil/非法UUID、非manual/其他profile/不支持版本、超5分钟或非法窗口、bool预算/无界或非法政策拒。保留intent hash/owner/run/版本/嵌套多字段及bool/int伪等拒，匹配只返回原Run的只读判定，不测试DB并发/真实认证或执行。先strict/独立合同，再只本块实现/测试/独审/回执提交。

a4.1b需另明当前canonical Alert字段和完整实际data-only正文的冻结投影，多telemetry不能默认第一条、缺源/非TCP443明确拒，不复用带synthetic和评分卡依赖的旧probe build_context。a4.2需Run+原M6 begin+独立操作工件同事务、重复先查原回执不读当前Alert、空marker/坏件/旧Run拒及ACK未知不派发；不得直接复用旧probe两事务insert/begin。a4.3使用现有investigation:run＋alerts:read、独立内部start凭据，匹配重试仅进度；只有本次首次确认commit者进入既有M3 claim/reserve，commit后claim前中断明确已接纳未派发，不自动恢复。真实a4.4另用新明确授予权限的测试身份（现service read token无run权限，API key原last_used_at写入需计入），不扩大旧权限矩阵；Case同目标互斥不自动套给Alert。

## 2026-10-25 M8a3.3双进程真实GET实施前细卡（e55c4d6）

a3.2独审33/6hash/12观测后保存。c只读原M7 Run4dfd374a-17a6-5fec-833b-803bfbcb85c6，原accepted manifest/MD3111B及6/14全选中列/正文checksum为基线。公开opt-in probe先离线guards/核验合同，再新批investigation-result-http-20261025-01；新PG角色socai2_inv_m8r_20261025_01_w（SELECT三账本+UPDATE(id)锁，无INSERT）及_r（仅SELECT tenants供API原认证），不改旧角色/policy/数据。公开配置只loopback两个URL、显式本次两个token/DSN/TLS，私密值.local。

独立Agents进程只加载新result_api factory/显式新read token及PG配置，API进程只加载新result_api factory/READ_URL/read token和新API service credential、旧认证DB reader连接；ENV生产/dev OFF，二者PID/创建时间留存。无worker/模型/schema初始化/旧app注册，API继承query路由但本次不调用任何POST，CH配置不新增。探针先PG READ ONLY核6/14/MD/accepted refs与当前用量，再API正确GET及认证负例（缺/错credential，缺/非法/未知tenant，body/query覆盖，随机不存在Run）；内部直接GET负例缺/错token、缺/非法actor/tenant。服务凭据仍原read权限列表，不修改权限矩阵或生产RBAC；JWT/真实用户撤销未实测边界保留。

成功响应需同原manifest/MD/execution，Raw PG再核14工件全部边/hash及scope/current publication state、原M6校验和，6/14全选中列/正文前后逐值/字节hash不变、旧Run列与M3tool1/model0/unknown0/unsettled0不变。可重复GET核同版，无新publish/Run/查询/模型/Case/通知。若失败只读定位/保留本批，不启动旧路径或补查。

最后按本次Popen handle＋creation time确认身份后停两子进程/close连接，本次roles NOLOGIN撤回所有新显式权限并查有效三表权限false/活动0；公开回执含真实正/负HTTP、PG不变、过程身份/清理及独立结束审计，不含实际token/DSN。先probe离线测试/独审，后真实c，前后不重放M6/M7动作；此仅显式只读入口验收，后续持久启动/M5语义与Case另步。

## 2026-10-25 M8a3.2 API只读网关实施前细卡（c2c50ca）

a3.1已独审保存。只新增API investigation_v2/result_gateway.py/result_api.py及独立factory；保query_api原实现/原应用注册不改。新factory可组合原独立v2 query app及新GET /api/v2/investigation/runs/{run_id}，没有启动/Case/动作路由；新结果GET复用require_permission(cases:read)，再CurrentUser.require_permission(alerts:read)。当前tenant/actor只取user.tenant_id/user.user_id，忽略用户伪造的tenant/actor头，拒绝任何GET query/body；权限不足不调用backend。

独立合同审阅发现原get_current_user在credentials=None且is_dev_mode()时返回demo主体。新结果GET单独先要求非空Bearer（含正确scheme/非空token），再调用原认证/permission，阻断demo bypass；旧认证与query路由不改。源码确认dev分支仅credentials=None，提供Bearer后仍走原workload/APIkey/service/JWT核验；不得只看到header就自建user。补“dev bypass开且无凭据/空/Basic仍401、backend0”和坏Bearer不变demo反例。

ResultReadGateway只从显式AISOC_INVESTIGATION_V2_READ_URL/READ_TOKEN取backend配置（测试可注入transport或gateway），URL为HTTP(S)无userinfo/query/fragment且根path，token同a3.1专用只读密钥，无旧AGENTS/API/service URL或token fallback。httpx单次GET发内部token及当前tenant/actor、Run，不转发外部bearer、不跟redirect、10秒timeout且无重试。404/409可固定原因映射，backend401/其他异常502、持久/连接超时503；不透传raw错误/token/DSN。

返回必须是owned_fixed_recon_result.v1，同tenant/Run、alert_recon/alert target与有限objective，read notification=null。published时manifest身份/profile/target/版本及逻辑ref自hash、manifest_artifact的完整manifest hash、execution snapshot身份/schema/hash、Markdown UTF8/hash与对应refs全部一致，后再返回原JSON；not_published时manifest/MD/artifact为空，保进度/候选，不拼旧report。网关只复核传输/归属/同版合同，M7 owned/来源语义仍由Agents原reader负责。

先API单独解释器直接测试实际既有service认证/租户解析（PG session替身）→MockTransport内部GET、缺/错credential/tenant、两read permission分别拒绝、逐请求permission收回、伪header不覆盖、body/query拒绝、response身份/MD/manifest/execution哈希反例、redirect/timeout/状态错误脱敏及旧路径404；查询router原7项保持。此块不执行真实PG/网络，也不把mock permission收回当生产RBAC撤权已实证；a3.3两个loopback进程与PG实证另卡。先strict/独立合同，再只本块实现/直接测试/结束审阅，无旧源码/权限默认/部署变化。

## 2026-10-24 M8a3显式只读HTTP分块细卡（2d92063）

a2同锁owned读取已独审保存。保持API/Agents两个app包与进程独立，a3.1先Agents内部只读app/认证并直接测、独审；a3.2再API v2认证网关及直接/独审；a3.3用原M7稳定Run做真实GET/PG读回，不重查/新Run。没有正式启动、Case、自动策略、真实通知或生产部署；旧main/router/权限矩阵不改。

a3.1新增Agents investigation_v2/result_api.py独立create_app，仅GET /internal/investigation-v2/runs/{run_id}。专用AISOC_INVESTIGATION_V2_READ_TOKEN显式强值（至少32字节、无缺省），hmac比较且每请求校验；不使用旧AISOC_SERVICE_TOKEN/开发回落。认证后要求X-AiSOC-Tenant-ID与X-AiSOC-Actor-ID均非零UUID，可信网关主体构造当前TenantPrincipal再调用a2。tenant/actor由内部read token的可信网关声明，真正外部用户permission由a3.2 API验证；actor只是当前读者标识，不改原冻结principal。GET不收body/query/scope/owner，POST/旧路径无新写动作。owned Run缺失404、其他完整性/陈旧拒绝409、持久不可用503，错误不带DSN/原文；返回身份/schema需吻合当前请求。

app可在测试显式注入reader/token；实际独立进程lifespan从新AISOC_INVESTIGATION_V2_PG_DSN/CA_FILE创建有界asyncpg池（TLS校验、command timeout，沿M3最小UPDATE(id)锁权限）并只关闭本进程所建池，无旧全局worker/模型/schema初始化。提供reader时不隐式建池或关闭外部资源。读token配置缺失则app启动拒绝，不默默接旧服务。

a3.2另新增API v2 read gateway/factory，保原query app可复用的认证与受限query路由，新GET /api/v2/investigation/runs/{run_id}要求cases:read和alerts:read，不新增旧服务token权限。backend read URL/token显式配置；仅可信配置地址、不跟重定向、有限timeout，发送认证后的tenant/actor及Run，拒body/query覆盖。返回校schema/tenant/Run及pub状态，published时MD SHA须匹配manifest.report.sha，manifest tenant/Run一致；不把下游错误正文原样给外部。未发布只返回进度/候选。现共享service token本来已有两read权限，可用于受控真实GET；写/启动permission另步，不扩本token。

直接测试a3.1先缺/错token、缺/非法tenant/actor、GET覆盖、错误映射、同owned输出/通知null/无写/旧路径404及显式配置/资源所有权；当前仅先这一块实现。a3.2后再测API当前permission/伪造header不覆盖、下游身份/MD/hash/timeout；真实a3.3另卡用两个新loopback进程与临时PG角色、原6/14和MD不变，真实credential与mock permission范围分别留证。

## 2026-10-24 M8a2 owned持久读取实施前细卡（9f75772）

a1已独审保存。新增OwnedReconResultReader，仅接受当前可信认证许可载体、tenant_id/run_id；当前tenant必须在principal允许集合且Run按id+tenant命中。同M3锁定该Run并设置事务tenant；查唯一unified_recon_started（取最多2条并要求恰1），验证event agent/kind/input-output hash及begin正文/state工件的owned join、kind、字节/hash、payload和state.persistence全部对应，owner只取已核初始snapshot。缺标记/legacy/重复拒绝，不fallback。

调用a1恢复原request；实例化该已核owner的ReconPublicationStore，复用其M7只读逻辑。为避免嵌套事务/第二次行锁，将M7现read_result内部原逻辑抽成同包_locked读helper，旧public read_result仍经原锁/同helper返回原格式；owned reader在已有同Run锁内调用该helper，当前版本/late settle和manifest全核规则不变。新增返回仅加read_model schema、tenant/Run/profile/target/objective及明确legacy状态字段，原M7 publication/manifest/MD/execution完整保留；旧status不推导新完成。

当前a2只是持久服务函数，current TenantPrincipal及读取permission已由可信调用方核验为前提；正式认证、token撤销和HTTP状态映射在后续独立v2入口验，不伪称本层已验实际auth。DB连接沿原M3最小Run UPDATE(id)锁权限，逻辑操作只有SELECT/set_config/行锁，不改任何账本或预算；不读取当前Alert，不允许caller owner/scope或接管运行。驱动错误包装为无DSN/正文的持久错误，必要拒绝仍明确。

先SQL替身测试已发布/未发布、另读者/权限空与foreign Run、无/重复begin、event/工件hash/kind/关联/owner错、自洽重新hash的控制漂移、下游缺件/late settle/旧writer丢指针、driver失败保密；核所有GET前后rows/usage/工具次数不变，M7公共read原行为不变。先strict/合同独审，再仅a2实现/直接测试/结束审阅；真实PG与HTTP另卡，无部署/旧路由变化。

## 2026-10-24 M8a1冻结读上下文实施前细卡（2b87675）

M7c已独审限定通过并保存推送。显式业务入口先补一个必要纯接缝：M7 read_result接checked request，不能每次从“当前Alert”重建历史scope，否则告警后来改动会让已发布结果不可读或混版。a1仅restore frozen alert profile，后续a2持久读取/当前认证、a3持久启动与显式独立HTTP逐块细化；无前端/旧路由/生产配置修改。

输入为当前已认证TenantPrincipal与caller已核owned begin输入/初始state；存储归属/读权限必须先由可信持久caller核，纯层不能把来自客户端的JSON当已核工件。原state/input中保存的principal只用于忠实重建原scope及hash，当前主体的tenant许可独立验证，恢复结果不授予新运行或未知Run接管权。当前Alert不加载也可还原，预算/旧成本均不变。

新profile_restore纯层核begin input_hash、scope_hash、scope_sources中每个scope-source引用的正文SHA/字节数且集合精确；只接受当前固定alert profile/版本。重建SourceField/CheckedAlert/CheckedMemberSnapshot/UTCWindow和TenantPrincipal后走原initialize_scope及BusinessProfileRequest/CheckedBusinessTarget，再要求scope_snapshot控制/来源、descriptor及make_recon_plan与冻结原件完全相等，不另写放宽版M1。初始state须为该Run begin/ready、空attempt且owner/原input引用有效；输入源metadata不能被data_only_text指令改变。

预期正常及当前另一个同tenant读者都精确恢复原request；Unicode/data-only文本保持原字节；当前无tenant、错run/profile/version、正文hash/大小/缺ref/多source、字段/窗口/能力/问题漂移皆拒；输入/预算不变，0I/O/Run/查询/模型。先合同strict/独立复核，再仅a1实现/直接测试/独审，a2以后另卡/真实接缝，不因纯函数通过称正式读取已认证。

## 2026-10-24 M7c真实PG实施前细卡（f6ac2a2）

b已修P2/独立52项及7账本复核后保存推送。c只对M6.2c稳定Run4dfd374a-17a6-5fec-833b-803bfbcb85c6、原owner/profile/batch引用追加发布，无新查询/模型/Run/Case/HTTP应用。source batch固定investigation-fixed-runtime-20261024-01，scope构造仍用当时live-pg-alert-read引用并重新核当前canonical Alert/合成标记/来源绑定；若已变更/已发布即拒，不借新ID刷新。

公开fixed_recon_publication_seam.py仅PG，phase=publish先独立reader READ ONLY核5/10、原M6.2全部边/hash/handoff及unknown0/unsettled0，再publication store pre-read not_published/report null→publish→hot read及repeat（notification null）→独立reader核6/14。phase=read在全新Python进程只执行read_result与原始PG只读验证，不调用publish；预期同manifest/report/execution字节及旧Run列/实际用量不变。首次publication notification只是delivery not_attempted的内部描述，无stream投递。两进程都不得调用runtime.execute/模型/HTTP/CH，原M6.2五事件和十工件版本仍原样。

本机新batch investigation-publication-seam-20261024-01，精确角色socai2_inv_m7_20261024_01_w/r，全新密码/TLS；writer仅原三表SELECT/INSERT和Run UPDATE(id)行锁权限，reader tenants/alerts/三账本SELECT及默认READ ONLY。私密helper.local新目录只创建本次身份并运行公开probe两阶段，记录子进程PID/创建时间、完成后关闭所有连接，再本次新角色NOLOGIN/撤权/活动0。无旧角色重开/旧失败重放/DDL/共享配置或常驻进程变化。

先probe guard与只读phase合同/strict/未参与实现者核，再真实执行。任何异常保留progress/失败原批，不自动重新publish；提交未知只读诊断，身份/进程清理不能扩大目标。结束独审核真实6/14、全部引用/MD值/预算及phase冷读和清理后才限定c；不据此宣称M8入口、Case、模型/Deep质量或真实通知已交付。

## 2026-10-24 M7同版交付分块细卡（基线3114609）

### b实施前细化（基线9bf333f）

a已独审并保存。新增ReconPublicationStore继承托管store，只增加unified_result_published支持、publish/read_result，不接旧应用。锁内读当前state/bound与已存publication event；若存在发布event但当前state丢失指针，明确拒绝，不能当未发布再次创建。首次仅stopped且owned handoff有效，读取候选引用的source/current快照及所有retained urn:uuid工件，必要tool/未确认观察另外核kind/hash/关联；再调用a构包。发布工件以同event绑定，manifest ID/hash写新版state.publication，执行快照与MD另各一件，总1event/4artifacts；无Run旧列/M3资源变更。

读回必须核publication event→manifest/state edges、manifest自引用hash/身份/版本，以及其handoff/source/stopped refs、全部section、execution和MD的kind/hash/同event归属。用a从原stopped基线重建，执行快照/MD/manifest须逐值/字节等价，不能拼最新。原publication state与当前相关状态比较，只容许persistence/updated_at变化；late settle真实账本仍可保留，但正式当前读取/再次发布明确拒绝陈旧版，不改历史manifest、不把旧MD当当前。仅丢指针或坏件也拒绝，不回落旧报告。

publish首次提交确认后才返回published及同manifest内部notification descriptor（delivery=not_attempted）；重复publish仅读原版，notification=null，cold read也不生成通知。提交ACK未知抛持久错误，显式read可核已提交版，不再发工具/模型。未发布的read_result仅progress/候选与not_published，正式report=null，不借旧status/report冒充。内存调用与新store冷读共用同一方法，无全局可变报告缓存。直接SQL替身测试正常/重复并发/前后冷读、MD/manifest/execution缺件异文、回滚/ACK丢失、partial/unknown/取消保资源、late settle/丢指针与跨owner/tenant；过后未参与实现者独审，再c真实PG。

M6.2c已限定ACCEPT/0并保存推送。M7a纯包→b原子发布/选定读取→c真实PG前后冷读，不先接M8认证/HTTP/stream。fresh_design_audit草案复核要求钉住section、当前性、逻辑身份/版本及来源留存，以下落实，代码尚未写。

a输入为checked profile、已核owned handoff及source/current M3快照与不可变artifact引用。纯层校hash/ref/schema/tenant/run/profile/plan和snapshot identity；当前attempt/limits/opening/用量/实际停止相关状态必须与handoff源快照一致，phase→stopped与handoff指针为允许结束增量。单纯墙钟流逝不使旧ready失效；late settle等改变相关状态则拒绝，不覆盖冻handoff、不自动恢复重分析。

固定section版本fixed_recon_handoff_sections.v1：questions=/result/questions，analysis=/result；只有preparation.material_state=view_ready且evidence_document真实存在才有evidence=/preparation/evidence_document。projection_blocked/未采用各有明确availability且evidence=null，保原held refs。引用含artifact_id/sha256、artifact_schema、section及section_sha256；三块共用handoff，不复制正文。execution发布快照另存fixed_recon_publication_execution.v1，含三维状态、原stage/run用量与source/current M3 state refs；manifest引用它，避免与指向manifest的新runtime state互相算hash。

映射fixed_recon_publication_state.v1、renderer=fixed_recon_markdown.v1，manifest首版investigation_id=run_id/previous_manifest_ref=null。有限ready无block/execstop→finished/complete_for_scope/none；其余合法partial→stopped/partial/awaiting_human；cancellation_observed_at或execution_stop=cancelled→cancelled/partial/awaiting_human。报告明确有限目标/窗口/事实、六问题/缺口、性质未定/授权未知、实际用量/unknown/unpriced及未确认材料，人工仅required；动态字段作为安全文本，不执行正文指令。纯包始终candidate，不声称持久成功。

b新publication store同Run锁内重读全部owned材料、确认当前基线并构包，原子增加1个unified_result_published事件与4工件（execution发布快照、MD、manifest正文、M3 state snapshot）。只增加新版state publication指针，不改旧Run列/M3账本。一个不可变manifest；重复按同Run/handoff/发布版本返回原版，不因新ID另起版。retention分别表达publication artifacts committed与source availability/gaps/unknown，不统一写全来源ok。提交不确定无成功/通知，后续显式读回原manifest、不重查；缺件/hash/身份失败不当partial成功。

正式读取按manifest读全部必需工件/section及版本；发布前not_published/进度候选，旧报告不参与；发布后和清内存后同版。仅提交确认后生成同manifest内部通知描述，M8前无真实stream/外部投递。c拟仅在M6.2c稳定Run追加发布、不重查：5/10为M6.2历史快照，发布后预期6事件14工件；新临时角色单独关闭，独审后放行。先仅a实现/直接测试/独审，a过才b、b过才c。

## 2026-10-24 M6.2c真实独立接缝细卡

b2保存d06bf3a并独审P2闭合后才c。公开探针fixed_recon_runtime_seam.py复用旧共享场景卡和build_context显式telemetry映射，强制传新batch Run，不调用旧探针run方法/旧Run。私密进程助手在.local/verification/investigation-fixed-runtime-20261024-01，复用已验最小角色/SSH/独立API启动方式但新精确角色名与新随机密码，角色创建一事务、关闭NOLOGIN/撤权；无新api_key行/DDL/写湖/模型。先public probe离线结构/身份合同，再本机prepare与新独立进程。

新Run id由batch确定、已存在即拒绝；PG读取当前canonical Alert/实际source projection及matching raw/ocsf hash后，创建running合成ledger Run（case_id仅标签非Case），用实际runtime.begin/execute。source/业务输入不含evaluation_only预期；评分在执行后独立比较。预算显式0模型/1工具/0tokens/0费用/1未结算，DB now+120秒及父deadline，查询窗口仍场景冻结5分钟。成功候选后用新runtime对象重读，须HTTP本次false、候选逐字段同版、服务端仅1条业务SQL；startup GET405不计业务查询，另一次CH预检单列。

独立reader READ ONLY核5事件10工件，所有bytes/hash/event/run/tenant关联及state payload引用完整，begin profile/运行和完成版本/整窗计划已冻结；M3实际工具1/模型0/unknown0/unsettled0，源原文hash/精确关联、有限ready、Q3a/Q3b/Q4未评估。用新store冷读及通用store拒托管验证不写新事件；新Run状态仍running/计费列原样，M7未发布。失败原批保留，不盲重试；进程按本次Popen handle创建时间核身份后停止，新角色关闭且活动连接0/有效三表权限撤回。全部达标和未参与实现者复核后限定M6.2，不外推智能分析价值或正式M8入口。

## 2026-10-24 M6.2b原子store与调度细卡

b1已保存b61214a并限定独审通过，现做b2。控制器先claim，只有本次确认首次claim（needs_commit=true）才持有本次执行权；重复claimed返回进行中/中断不派发，stopped读原交接，blocked仅finalize。未确认claim或重复请求的取消不调用Run取消，避免接管另一个执行者；已确认自己claim的取消尽力mark_cancelled/finalize后继续传播CancelledError，无后台shield任务。claim提交不确定不给HTTP授权，也不自动重新claim。

b2代码独审发现取消留存竞争：mark_cancelled提交blocked后，重复blocked调用可抢先finalize无观察，原owner的观察随后被冻交接拒绝。修订为：只有本次首次claim的调用可继续finalize；重复blocked返回blocked_handoff_pending，不抢先封存，显式operator存储接口仍按原权限/职责使用。读取已存交接时，若本进程尚有观察，必须先核其hash确已包含于owned completion或unconfirmed观察工件再清理；不匹配则保内存并拒绝，不能为兼容而覆盖冻交接。须加取消屏障并发回归，保持HTTP1、CancelledError、未确认观察artifact/refs存在且未采用、unknown预留不释放。

原DurableActivityRecords仅新增按attempt索引的内存tool-result观察读取/清理，不代表持久；在结果形成后、等待complete前捕获canonical副本，因此complete取消/失败时仍能单独留存观察，重复被拒的attempt不清掉原观察。无法规范化的观察不伪装有效结果；原M3完成/unknown/预算规则不改。blocked回执增加固定reason_type，用于区分ExecutionPersistenceError和必要控制拒绝，不回显新凭据。控制器仅在自己的claim内调用原gate一次，保存交接后才清观察；实际HTTP状态与本次是否调用gate分别记录，不把重复读取说成全Run HTTP0。

若gate预留被阻断，新增mark_dispatch_block仅据当前权威M3停止原因写控制事件；仅确认为持久提交失败的程序观察可补retention_gap，未知资源不释放。其他不变量拒绝不能吞成一般预算/留存停止。该事件也需原子提交才finalize；写入不确定不再尝试派发。先定向真实gate＋SQL替身/MockTransport核正常、重复/并发、无预算、claim/预留/完成/交接失效、取消发生在HTTP/complete、取消重复请求及原输入保密，再独审与保存；c再验证真实服务。

a保存5f388ae后实施b。原ExecutionStore仅增加可覆写event_kinds/runtime_version/event_agent，_load按实例支持的kind读取并核runtime版本，通用begin拒绝托管store调用；无runtime标记的M3原行为保持。新增ReconExecutionStore使用同Run行锁、原tenant/owner/hash校验，事件为unified_recon_started/claimed/cancelled/handoff_saved加原M3三类预算事件，不改DDL/旧服务。begin_recon仅新鲜running且completed_at为空Run、无已有unified阶段，在同事务冻结scope来源、profile、运行计划及版本；claim用a纯转换，只有新claim/block需要新事件，两并发者仅一个得到首次派发决策。reserve在锁内先a冻结请求校验，再实际M3 reserve；complete继续原M3幂等/unknown合同。

finalize在锁内核当前profile/scope、源于当前attempt的completion引用和工具工件kind/event/hash/UTF-8，才构CommittedMaterial调用A3。若没有已确认工具工件，停止原因据实际M3状态；不采用未确认输出，可用单独fixed_recon_unconfirmed_observation工件保存本进程观察及hash/attempt关联，明确不是原completion。若已留存来源的必要语义校验失败，生成source_material_rejected部分交接，保owned artifact引用但validated_source_refs为空，不称source unavailable或已核projection block。stage已用满唯一调用不自动算budget_limit；deadline后仍可保存已得结果/交接，但不得新增外呼。

handoff为fixed_recon_runtime_handoff.v1封装，含固定plan/profile/scope、正常A3准备或明确拒绝/未确认状态、有限result及M3用量/来源state引用；candidate/handoff/state引用同事务写入，存在未确认观察时同事件增加单独工件。内部纯准备not_attempted字段保持其组件含义，actual retention以提交后方法回执及独立读回为准。重复finalize只读原artifact并核hash/归属，不重新准备或覆盖；finish先检查权威停止原因。Run旧状态/计费列不在b修改，M7再做完成与同版发布。

新增FixedReconRuntime控制器只接已开始的托管store：claim首次成功→原DurableActivityRecords一次→finalize；重复claimed仅读in_progress_or_interrupted，已停止读原交接。取消先尽力记录cancelled/部分交接后仍传播CancelledError，写入不确定保留状态且不重试；API地址/凭据只在运行对象，不入artifact。先b1存储合同/直接事务替身，过后b2控制器合同/真实M3与MockTransport，再c临时身份/独立v2真实HTTP/CH/PG。b1/b2不外推真实事务已验，c须核原始行数/关联/状态/用量且只运行新批次。

## 2026-10-24 M6.2固定运行接缝逐块合同

持续推进授权后，先M6.2a纯运行计划/状态，直接测试/独审通过才M6.2b原子持久/调度，最后M6.2c独立v2真实PG/HTTP/CH。先只接alert_recon有限网络路径，Run由可信调用方预先创建，正式启动认证/业务去重仍属M8。模型0、无Case动作；固定查询仅一次，M5不是前提。初始冻结runtime版本、完成政策、profile描述与scope hash；计划参数来自已核member和完整冻结窗口，确定step/attempt不能换ID重跑。

M6.2a新增纯recon_runtime_state：make plan、安装托管状态、claim、冻结预留校验、实际停止判断与结束引用。输入是M3 state、已核profile和注入的权威now；复用M3状态完整性/用量重算与reserve做只读预检，不另算预算。ready首次准入只产需提交claim且仍需M3 reserve的决策；claimed重复只报in_progress_or_interrupted，不接管原调用；blocked仅准备交接，stopped仅读原交接。unknown/未结算禁止新派发，预检已知额度/时限失败映射明确停止，其他不变量错误仍抛出。已知查询恰好耗尽调用上限不使已得结果自动变partial；after-call只按unknown、真正breach、期限或已记录取消收紧。结束只保存引用/phase，不变更M3账本/旧Run终态。

M6.2b拟新增ReconExecutionStore复用原ExecutionStore行锁/tenant/原子事件与工件，新增受支持event kinds和runtime版本校验，通用store拒绝托管版本，旧无标记合同保持。begin冻结profile/完成政策/执行器及计划，claim原子唯一，托管reserve仅允许冻结一次工具请求并再用M3 reserve；调用用既有DurableActivityRecords。返回后只读真实已提交工具工件，校验归属/hash后调用A3；未结算/留存缺口只部分交接，不采用未确认来源或重新查。handoff正文与state引用同事务提交，重复读取原引用，异文不覆盖；停止可晚于deadline保存，不追加模型/工具。Run状态/同版发布仍留M7；基础中断回查保持claimed可见且不自动重放，不建设通用恢复平台。

每块先预期/strict、直接测试、独审、回执与Git保存；真实接缝新Run及临时身份，不重放旧批，PG独立读回hash/UTF-8/归属/状态及用量，未知提交不得换Run继续。M6.2a无IO不代替原子claim/真实预算，M6.2b替身不代替PG，M6.2c通过后才M7。具体持久实现前还须细化本小块输入输出。

## 2026-10-24 A2窗口完成与A3投影阻断合同

基线070e990，先合同/预期/strict及独立设计复核，再依次实现两个纯层增量，不一次性接完整运行器。A2沿M6.1有限政策：仅alert_recon，目标为冻结成员/窗口内的来源核对；固定查询使用完整窗口。输出coverage区分target_window、query_window、covered_window、uncovered_windows及full_window_queried；query_window是回执所列请求范围，covered_window只在status ok/empty且executed true时成立。子窗口事实保留，剩余区间阻断ready；整窗empty/截断不绕过原缺证/截断阻断。ready仍只指有限目标，review_required也仅属于该目标，不解释成无需后续整体调查。没有多查询窗口合并、自动补查或生命周期映射。

新输出固定completion_policy_ref=bounded_full_window_source_check.v1，区别于原M6.1仅存在性核对的历史结果；scope policy_ref网络问题/查询合同不改。M6.2必须在任何外呼前将完成政策与执行器版本存入冻结运行输入，不据代码升级更改旧Run政策。无新字段的旧回执按原批次解释，不补写/重算。

A3采用最小可交接方案，暂不分离完整证据内核：EvidenceView必要校验全部完成后，才检查Alert摘录/完整模型视图；投影阻断用专用异常携带canonical结构化回执，含scope/revision/material、全部index引用、真实query及限制原因，不带自由正文/输入合同命中的原文。原builder继续拒绝不可消费的视图；新增纯准备函数只在内部捕获此类已核投影阻断，返回可供M6.2保存的partial交接，source_state保持真实状态且evidence_snapshot_ref null，不伪造缺失视图或来源不可用；不从未形成的视图采用新事实，六问题保未评估及材料阻断。正常视图走已验M6.1。错误hash/tenant/Run/scope/必要来源不能转投影缺口。已观察execution_stop只收紧且不外呼；持久性/人工投递尚无回执，不称已提交本交接或已接手。

A3具体纯接口为prepare_alert_recon(request, query_result, material, revision, execution_stop可选)，返回alert_recon_preparation.v1封装：material_state、原material引用、正常时实际evidence_document/evidence_snapshot_ref、阻断时projection_block回执，以及对应有限result。阻断result用独立blocked_alert_recon.v1，携完成政策版本/业务绑定/窗口与全部held_refs，facts为空、六问题unassessed，保真实source_state/source_available与execution_state；交接为required而非delivered，持久保存为not_attempted。长Alert使用身份/原文hash/字节元数据形成引用，不复制超长或不可消费原文进交接；正常视图的文档与引用格式保持。该接口不收外部构造的投影阻断证明，只捕获自身builder抛出的专用异常。

直接预期分两块：A2整窗、内含/边界子窗、UTC等价、空/截断/失败/unknown/缺视图及事实不丢；A3正常、10条引号/反斜杠/中文、长Alert/输入合同阻断，保全部refs/版本/原响应hash，不泄漏自由正文；长材料叠加各类必要校验失败拒绝，停止枚举只收紧。每块直接测试和独审通过才进入下一块；A3结构化交接可序列化不等于实际M3持久保存。M6.2再接真实准入、固定查询/规范化去重、停止及交接留存，M7再映射Run状态/同版发布。本批不改旧源码/注册/预算/历史失败，无真实HTTP/PG/CH/模型。

## 2026-10-24 A1地址身份接缝修复合同

基线891d07e，承接独立审计A1，只修新版网络地址身份。Agents v2新增共享纯函数：输入必须为地址字符串，IPv4与IPv4-mapped IPv6输出IPv4，原生IPv6输出压缩形式；受限过滤比较保原类型检查。M1的实体使用规范值，但SourceField保原始值/路径并按地址身份核对应关系；caller入参/回执及EvidenceView查询参数同规比较，不重写已留存响应或source content hash。API records原有规范化已符合此规则，先以真实函数/替身CH跨进程结果验证，无需修改API业务代码。

Deep既有纯准入也使用同规匹配，输出参数取已核member规范值后再计算指纹，防地址别名绕过重复查询；不实现模型循环。直接测试覆盖IPv4、mapped十六进制/点分、原生IPv6压缩/展开，及不同IP/compatible非mapped/错误tenant/来源值/hash反例；跨实际API records、caller、证据与M6.1有限事实，业务HTTP/PG/CH/模型0。先规格/实施预期/strict，再代码、直接测试、独立复核与公开回执；A2/A3及M6.2—M9不据本块核销。

## 2026-10-24 M6.1固定有限事实与停止交接（实施前合同）

基线ad08579，新建Agents v2 `fixed_recon.py`，不改M4旧采用代码或任何旧服务。输入为BusinessProfileRequest(alert_recon)、EvidenceView或None、当前snapshot引用，以及可选可信调用方已观察的停止枚举；重新校核业务绑定、视图hash/scope和版本，非alert profile/旧snapshot拒绝。M6.1是查询之后的纯政策层，无调度/IO；M6.2后续才接实际M3 gate、固定查询/重复与无进展停止、持久交接，不能据本层通过勾完整2.3。

复用M4 checked_view与有限_predicate检查，但不构造模型候选；每个fact保origin=program、assurance=rule_checked、当前revision/snapshot、evidence_refs及snapshot依赖，ID受业务binding和当前snapshot约束。按可见来源逐版本保network_observed、outcome_unknown、alert_linked；冲突按身份合并列全可见/缺失版本；查询按成功bounded_query/empty或source_unavailable保真实执行状态。保持全部held refs与coverage gaps，来源自由文本不成为程序理由或下一步控制。

输出始终stopped且automatic_query/model=false，scope_readiness仅ready/partial，nature unresolved/authorization unknown。六问题完整保留：Q1依据观察/冲突/缺证，Q2仅精确UUID关联，Q3a/Q3b/Q4 unassessed及原政策缺口，Q5报告可核覆盖。Q1/Q5为原有限目标的决策问题；Q2缺失独立保gap且不擅改其criticality。查询/正文截断、不可读摘录、冲突/缺反版本、不可分类action、无观察或视图缺失均阻断ready，保合法结构事实。已观察的budget_limit/deadline/unknown_attempt/retention_gap/cancelled只收紧partial；原因真实性与时钟由后续可信运行层保证，本层不开放任何新调用。

先本合同/实施预期/strict，再实现和直接测试：正常/unknown outcome/空/各类来源失败及未执行、两版本冲突和hash-only反版本、截断及混合摘录、无精确关联、注入对照、停止枚举、跨scope/旧snapshot/不支持profile、不可变与新版本依赖。再跑受影响M4采用/视图、M1业务绑定合同，结束未参与实现者窄审与公开回执后放行。无模型/真实HTTP/PG/CH访问、写湖、预算或旧Run变更；阶段提交/推送调查分支，不合main或部署。

## 2026-10-24 独立v2 HTTP与持久查询接缝实施合同

承接03cb3c3三个前置块。共享场景卡在`docs/investigation/scenarios/network-observation.v1.json`，明确业务输入/评估预期/实际观察合同分离，复用现有三湖事件和canonical Alert，不再造数/写湖。原telemetry已含匹配事件，只验证范围/关联/留存，不评价补查增益。

顺序：先卡与规格/预期、strict；再新增独立`query_api.py`、离线路由直接测试及原records/caller/gate相关验证；通过后才创建新临时PG最小writer/reader与随机本进程服务token，读回实际Alert/CH资料；最后新Run→原M3.begin→受限caller→新v2 HTTP→原records/CH→原子完成→独立PG读回。M1 profile descriptor只作为测试Run开始输入留存，不声称接了正式业务启动入口。

独立应用复用原`get_current_user/require_permission('lake:query')`，不覆盖认证依赖、不启旧app.main/startup/worker，仅新路径。API读身份使用SELECT权限且默认只读的新reader；writer只对既有三张ledger表SELECT/INSERT及Run的UPDATE(id)行锁所需权限，新角色无super/bypassrls，不改共享policy或DDL。原CH reader只读保留；角色创建/关闭通过已有21SSH管理路径，密码不入Git/日志。

测试控制器/探针作为可共享源码放活动change的probes；本机配置、临时进程/角色准备材料放忽略.local。真实Run/步骤/attempt以全新批次固定ID，新Run已存在即拒绝，不重放旧测试驱动。显式model cap0/tool cap1、tokens/cost0、unsettled1、DB绝对期限120秒；仅一次成功CH业务查询。认证反例及旧路径/工具拒绝不得触发CH；其他拒绝/越界在离线合同验证，不扩实测矩阵。

真实读回核3事件/6工件、两类scope/初始profile输入、完整tool output等于工件正文、原始hash/字节及事件关联、stage模型0/工具1/无unknown、Run四列不变。Run保持running为测试资料预期，不发布manifest或宣布调查完成。结束按本次Popen身份停止API，新角色NOLOGIN并撤权，保Run与湖资料。先离线放行、再真实放行、最后未参与实现者窄审；旧版源码/注册/生产不动，不合main/部署。

首批01在PG读取阶段因探针假定hostname/src_ip/dst_ip独立列而UndefinedColumnError，未创建Run或发业务HTTP；进程已核PID/创建时间停止，新角色NOLOGIN/撤权。只读核真实列及JSON键后，改从`alerts.raw_event.telemetry[0]`取材，先核telemetry tenant/event_id与canonical Alert归属/source_event_ids一致，再显式映射成M1既有规范化投影（hostname/src_ip/dst_ip）。SourceField.record_ref标checked_projection，PG真实路径、原raw_event hash及映射一起留存，不冒称这些是PG独立列。旧失败驱动快照保本机，新02用新角色/Run；不是重放unknown。CH资料只读核对1次与正式API activity查询1次分别计数，成功批合计2次CH SELECT，不写湖。

## 2026-10-24 I2完整messages预算最小合同（I1放行后）

基线`f6a3fa8`，I1经修复/独审/保存后进入本块。新增纯`request_budget.py`作为完整消息规范化、canonical序列化与12KiB常量的唯一来源；M4消息组装、执行前检查、egress后的预留前检查共用。可消费对象是通过完整任务检查的messages，EvidenceView仍是可用于不同任务的有界材料视图，不承诺单独满足某任务开销。

保留现有system/模板，不用缩短提示词或提高上限掩盖问题。组装时用同一实际模板计算完整请求，以及仅将evidence置空时的固定开销；两者差额是含JSON转义的序列化证据贡献，不是原始view字节或token数。超限异常仅携带安全数值和范围引用，执行器提供准备/egress阶段、原快照、全部held来源refs、受影响问题及需要拆任务/补明确材料缺口的状态，预留/调用0。

本步采用原建议允许的“显式阻断/交付材料缺口”，不自动拆分冲突或推断哪些反证可以丢弃，不实现新调度/分组框架。后续M6需要分组时须按问题和支持/反证组合保独立快照/覆盖；当前不能声称10条已被模型消费。egress可变化，准备成功不替代observer最终检查。M3 token预留公式及unknown/计费不改。

直接预期：现模板1/7条可准备，8/10条完整超限时组装已明确阻断；固定开销+可用序列化证据空间=12KiB，held refs未丢。UTF-8/转义、恰好边界/超1字节、combined/focused、冲突版本不裁、egress膨胀和DurableAnalysis预留/调用0直接验证，再核原15模型合同及受影响采用/视图接口。不发真实模型/业务查询。

## 2026-10-24 I1正文局部降级最小合同（M1放行后）

基线`7e84fe7`，M1纯绑定经独审放行后才进入本块。只改新版EvidenceView可选raw.message处理及相关有限事实缺口投影，不动M2来源校验、scope/预算、旧源码或入口；模型调用0，I2预算尚不在本块。

message短且合规为present，无message为absent；截断正文不推断可解析完整含义，记not_extractable；非JSON/重复键/不支持的顶层结构/解析嵌套超限/对象值/超512字节/LLM合同拒绝分别记not_json/ambiguous_json/unsupported_body_shape/json_nesting_limit/unsupported_type/over_limit/input_contract_rejected。异常摘录不直接入模型，也不截前512字节冒充完整。每次retrieval保message_extraction；同源同版先验证保留前缀一致，汇总后若有完整合规present/absent可使用该状态，否则在event.excerpt_gaps及query.coverage.gaps披露实际原因，其他结构字段保持。有限network_observed/outcome_unknown事实若有摘录缺口，向readable投影保该缺口，不能增加任何更强谓词。截断取回的历史限制继续保留。

合法UTF-8原文中的JSON转义也可能解码成不可编码的Unicode；只在可选message编码处捕获并记invalid_unicode，不替换字符、不透传正文，其他结构字段和同批正常记录保留。此项由结束窄审反例发现后补入本块，不涉及放宽身份或输入规则。

直接先测短文/512字节边界、513/中文超界、对象、非JSON/重复键、转义Unicode编码失败、原始OCSF/XML签名、截断中可能关键正文、完整/部分同版合并及必要字段/hash失败。再核采用/可读结果仍有限、缺口不丢，以及现有视图/采用/模型合同受影响兼容；不以旧8模型样例当新语义已验。直接通过和独审后才进入I2。

## 2026-10-24 M1业务profile最小实现合同

在新Agents包新增`business_profile.py`，以不可变`CheckedBusinessTarget`表达可信调用方已核的alert/case目标、租户、目标记录/归属检查引用、完整成员身份及成员来源/版本；纯函数绑定原`ScopeContext`，输出profile/版本、目标、objective、policy、trigger、交付归属和成员选材覆盖描述。不改变scope.py的explicit_set初始化、问题、准入、预算或任何旧版文件；新绑定不会将内部scope.target_type改成已解析的Case入口。

- 当前只接受`alert_recon + alert`或`case_investigation + case`；trigger显式为manual/automatic，两种触发不能决定profile或授权Case写入。objective必须显式等于既有有限目标`verify_source_network_observation`，policy必须匹配原网络政策；未知profile/版本、目标类型和更强目标拒绝。
- 绑定时重新核ScopeContext与原M1规范初始化结果一致（允许已有正整数revision），防止直接替换问题/查询范围绕过原合同；这仍是结构校核，不是认证/数据库归属证明。主体认证及目标/成员归属必须在调用前完成。
- 告警目标ID必须等于唯一所选canonical Alert，完整成员必须正好该Alert；交付归属为该Alert，无Case前提。Case需非空已核目标/归属引用、稳定成员版本及与ScopeContext相同的成员来源引用；完整成员ID必须唯一且非nil，scope中的selected/omitted必须完整分割该清单，total不能未知、不能有未列身份。只选子集合法，但交付必须保全部/选中/遗漏ID及原因，初始调查覆盖仍not_started，不能扩大原conclusion_scope。
- 输出钉住scope hash和目标/成员版本，提供分离副本；原始告警正文不能指定profile、删除问题或改变交付归属。不生成complete、已启动、已创建或已授权的业务结果；调用与预算均0。Case成员解析/分页一致性核验、继承、同请求唯一Run和实际发布留M8/M6/M7。

直接预期：同一告警manual/automatic归属相同；无Case告警合法；4成员Case全选与仅选3条均有明确覆盖，缺最早成员仍可见；租户、目标ID/类型、成员来源/版本/分割、目标升级、scope篡改及未知值均拒绝；原explicit_set八项保持。直接测试通过并留回执/结束窄审后才放行此合同块，不能计作Case入口或profile已接执行器。

2026-10-24 main集成说明：本change接收远端调查`469e9467`的独立v2开发基线及原记录，保留双方已有设计和实现。旧restore迁移已在main限定核销归档，不恢复其活动目录；下述历史原文中的“沿原restore/5/15/不提交”等按原日期解释。D1—M4限定成果、M5.1与未完成M5.2分列，新HTTP未注册，M6—M9和v4分层未交付。当前只合并和审计，不启动后续业务实施、真实测试或部署。

## 2026-10-24严格双版本隔离（最新，覆盖共享接线方案）

旧业务源码/注册/入口不改，需要变化的函数在新版复制所需部分；新版两个独立investigation_v2包，旧app不导入、不注册。已撤出旧API新增分派并恢复旧测试。运行后续独立进程/配置及测试输入输出；v2调用路径为预留的/api/v2/investigation/query，尚未注册/发布。历史M2/M3/M4真实回执仍对应旧位置快照，不算新HTTP路径已验；迁移后仅直接合同。M5真实查询需独立受控v2测试处理器，不回挂旧v1。M8正式业务入口、完整M5仍待逐块实施。旧版下线另决，当前调查本地提交授权有效，不push/部署。

## 2026-10-24 v4告警侦察与Case调查分层（当前设计，未实施）

用户要求结合实施进度和新建议重新设计，以[主设计v4](../../../docs/architecture/investigation-planning-design.md)第1节为准。告警profile负责分诊后的有界侦察、缺口与升级建议，保留20自动处理过程及无Case详情；Case profile固定完整成员快照，在新Run引用多个告警的不可变材料并整体调查。Case创建/关联与启动是独立政策，Router四领域按需参与，不串跑两套完整编排。

D1—M4限定回执及M5.1九项纯合同通过保留；M5.2仅observer问题组参数增量未测，完整Deep/循环/发布/分层入口尚未交付。当前仅文档，不继续实现/业务或模型测试。累计开发tokens不限、单调查有界，OS后置；无部署/提交/push，原5/15和旧失败保持。

新增合同为profile/target/objective、input_run_refs、Case成员快照、升级建议/政策决定/业务回执及启动意图。多告警不塞进单个parent_run_id；继承facts/findings分开，同源去重，范围/权限/版本/覆盖可核。Case新授权准入额度，历史成本不重复计算，unknown不因换层消除。人工和自动启动均须稳定请求键、持久意图及唯一Run，重试先查回执；已有运行不并发新Run。最终成员在启动准入时按一致版本冻结，创建时仅预览。新问题或覆盖/冲突缺口可按政策补查，已有效满足同问题的查询不无故重做。表/索引及20 API精确增量在实施对应步骤前核实，不假称已有字段或无需DDL。

实际续接按主稿12.7：M1 profile增量→M5未测增量验证/模型步骤/单问题循环→M6告警策略→M7同版发布→M8a告警入口及读投影→M8b手动Case材料与整体调查→M9按需领域→M8c自动创建/关联→M8d自动启动。每步先目标/IO/预期，再只实施及测试此步；Case多成员分析前移为Case可用的必要条件，自动持续增量/合并/真实响应后置。

## 2026-10-23 M4有限来源分析与采用（实现前合同）

用户新授权持续逐步推进，前批M3停止不限制本批。沿原2.1/3.1/3.4/4.1，按[主回执预期卡](../../../docs/operations/unified-investigation-implementation.md)依次M4.1a→M4.1b→M4.2→M4.3，每小步直接测试/回执通过才写下一步。network_observation.v1仅回答Q1/Q2/Q5；六问题定义保持，Q3a/Q3b/Q4保缺口，性质unresolved、授权unknown，不声称主设计12.6完整恶意/授权卡通过。当前仅文档，不实现业务或发模型。

1. **M4.1a证据视图。** 从既有M2 query_receipt/rows及M3持久refs构建来源身份/版本、冲突索引和实际模型视图。来源键按namespace/tenant/source ID，内容版本以原字段及来源hash固定，不随查询ID/取得时间制造独立印证。保同源异文；尤其M2 limit+1可能只交付一个版本但已标conflict：未交付hash和coverage gap仍保留，不补造正文。原始/保存/模型可见正文及hash分层，不直接把OCSF送给模型，不关闭safe输入合同。空/缺源/错误不造事件；必要反证装不下则拒绝组装/拆任务，不静默丢失。先纯直接测试。
2. **M4.1b候选采用。** 固定候选先测输入版本、引用、部分拒绝、同批临时finding键及依赖。程序分配ID/版本和adoption/validity，只有明确的来源字段谓词可rule_checked；模型复杂解释保model_assessed，不把有引用当验真。局部合法项保留，被拒finding的依赖不能采用；旧input_snapshot不覆盖当前结果。focused可assessment=null，combined有候选才校核整体，不机械拼裁决。仅本块版本/依赖采用，不先实现M6失效调度或M7发布。
3. **M4.2持久模型gate。** 复用safe_ainvoke现有invocation_scope observer；拒绝活动旧triage上下文，禁止raw ainvoke旁路。before_request取得egress后实际消息，完成输入/版本/额度校核及M3预留commit后才外呼；observer使本次走实际调用而非无usage缓存。responded在恢复前固定原reply于内存，safe返回后把原reply、恢复候选和采用结果同一次complete原子保存；恢复/解析失败照存原reply并结算responded，网络结果未知与回复不可采用分开。SDK retry=0，显式字节/次数/token/deadline上限；缺usage保unknown，留存失败不重放。先用替身核原子留存、到期、超输入/输出及恢复/解析异常。
4. **M4.3有限真实矩阵。** 每次问题≤3、发现≤6、建议合计≤2、实际消息序列化UTF-8≤12KiB、completion≤2048tokens。所有样例/模式共享一个stage，max_model_calls=8、max_tokens=20000；其他M3期限、未结算和费用条件显式记录，不因样例切换清零、延长或加预算。正例和冲突例各combined/focused一次共4次，过度成功断言/空/缺源/仅添指令对照各一次，共最多8尝试；不另开必跑总结。衍生材料新hash/provenance，不覆盖原来源，expected与预期标签不入模型。分别评分模型原文、采用、交付，记录实际usage/成本/unknown；必要质量或预算门未过则定位留存，不进入M5。

复用现有M1范围、M3三表/Run锁/单owner预算、模型factory/safe合同，不接生产入口或更改旧Run状态/计费列。12KiB是egress后完整outbound messages（含system）序列化UTF-8上限，不只是evidence_view；证据视图可取更小上限以留prompt空间。token预留使用实际outbound字节数+256消息开销+2048输出，是显式保守上界政策，不冒充目标tokenizer实测；真实超预留仍按M3记账后停止。输出token上限2048，同时原reply正文捕获≤32KiB；超字节限不解析/采用，保存有界正文、完整hash/字节数及明确截断，不盲目重发。输入/输出恰好边界、UTF-8、system与egress后增大均直接验证。无OS、部署、Git提交/push，原5/15保持。下面M3及更早说明保历史范围。

## 2026-10-23 M3最小身份、预算与持久执行门槛（历史预期）

本批承接已通过的M1范围/M2网络记录工具，只实现[主设计](../../../docs/architecture/investigation-planning-design.md)6.3与9节的必要执行合同。逐步预期及实际结果见[主回执](../../../docs/operations/unified-investigation-implementation.md)；每小步测试通过再下一步，不把本设计当实际验收。旧M0未放行及M2停止说明保留为此前阶段事实。

### M3.1 纯身份与预算状态

- `stage_id`由可信tenant/Run固定派生，`budget_scope=investigation_stage`，固定executor owner UUID；同一Run本阶段不能用随机新stage ID清零。`step_id`表示逻辑工作，`attempt_id`区分每次尝试，重试复用step而新建attempt；event seq是每次持久事件的顺序，两者不得混用。保存问题/scope/policy版本、调用种类及输入版本。
- 纯reducer接收冻结政策、当前快照、显式动作和由持久层提供的DB时间，输出新状态或明确拒绝；本块无DB/HTTP/模型。预算分别记录model/tool调用尝试、已知用量、预留tokens/cost、未结算含unknown数量和绝对deadline；子任务与重试共享同一状态，不创建嵌套独立额度。纯测试注入时间，不能把进程时钟当持久gate时钟。
- 旧`AISOC_INVESTIGATION_MAX_TOOL_CALLS`实为模型调用上限，只映射model_calls并保存配置来源；工具次数另显式提供，缺失拒绝，不能新增或暗换生产默认。token/cost及币种、max_unsettled、deadline同样明确；测试中的小额上限只是用例配置。真正无成本的工具可显式为0，缺失模型usage/价格不得伪装0。
- 预留成功即计本类尝试；只有明确无请求才可释放该次资源预留和未结算slot，但尝试不退回。请求可能发出或usage不可知时保unknown及预留/slot，不自动释放、重放或重置；有回复而无usage不等于零成本。已知实际用量超过预留仍如实记入状态、标超额并拒绝后续调用，不能为保持上限而拒绝真实结算。
- M3 state snapshot显式保存opening triage的已知tokens/cost、unknown与unpriced，以及stage用量；阶段仅扣本阶段消耗和预留，快照内Run总量由两段已知用量合计且未知仍显式。例如用例triage已知2000、阶段独立上限100，stage实际70时快照内Run已知2070而stage已知70，不把旧2000重复扣至本阶段。该100为测试输入，不是新默认；此合计不写回`investigation_runs.total_tokens/total_cost`等旧计费列。

### M3.2 既有三表的原子事件与工件

复用`ledger.py`的pool、事务和RLS上下文，以及`persist_graph_result`等的显式归属/实际RETURNING/冲突校验模式；不把fail-soft的`start_run`、`record_event`与单独`record_artifact`串联冒充原子成功。现`triage_budget`是一Run一次的首次分诊预留，charge与旧unknown不可重置，不用于新阶段多attempt；本批不改该表、不新增DDL。

所有开始/预留/完成在事务内先以显式tenant+Run谓词锁对应`investigation_runs`行`FOR UPDATE`，核固定owner及阶段状态，再分配该Run现存`MAX(seq)+1`并写事件、snapshot和相关input/output工件；任一写入失败整体回滚。现有triage事件和seq原样保留，不重编号。三个操作各有自己的seq；seq不等于外呼完成顺序或全局提交游标。只支持本批单一owner与遵循该锁的执行器，不允许旧graph/Deep writer并行，也不声称支持多进程恢复。

开始事件`unified_execution_started`保存schema/executor版本、身份、初始scope/policy、预算配置/来源及triage期初摘要；必须确认该Run无既往统一阶段标记或事件后才可zero-start。第二次begin即拒绝，不因输入相同返回一个新零状态；归属、begin或工件写入失败时外呼0。deadline以DB时间建立/核对，并受上级截止时间约束，保留收尾时间；不通过重开执行器延长。

预留事务提交成功后才允许执行一次对应外呼，固定attempt与输入hash/ref；并行子任务经同一Run锁不能多取最后一份额度/slot。调用结果在完成事务中与输出原文工件、完成事件及state snapshot一起提交；该snapshot含opening triage、stage已知用量、两段聚合总量和分别保留的unknown/unpriced，不另更新Run计费列。snapshot只放状态与小refs，输入/输出正文各存独立工件，不在每个snapshot重复嵌入。工件归属须显式核tenant/run/event，保完整已保存正文hash/字节；M2来源完整hash与其有界正文层次继续区分。

完成同attempt同指纹的重送只确认原回执，不在快照中重复累计；异文拒绝覆盖。完成失败保原未结算预留和留存缺口，不假称结果已持久、不重新查询；若提交结果未知，也不自动重放或释放。本阶段每次已知用量仅计入state snapshot一次，再与显式opening triage合计，unknown/unpriced另列；M3只锁定/读取Run，不更新`total_tokens/total_cost`等计费列、status或completed_at，也不改triage记录或历史工件。旧计费列不能完整表达unknown/unpriced，不能拿它们代替本快照；读取projection留M8讨论。M7统一manifest、正式交付与完成通知不在本块。

### M3.3 持久gate与一次受控工具接缝

M3.1离线直接测试通过才写持久层；M3.2直接合同通过才接包装器。包装器只接受已开始且owner匹配的阶段，经持久预留提交后执行已受M1约束的M2 `activity_records`；开始/预留失败、超限、到期或身份不符时实际外呼0。调用后必须原子完成才返回持久refs；失败交接区分已执行结果与未保存结果。M2泛API仍只做认证tenant/权限及全局bound，本包装器不声称已完成M8生产入口/持久scope授权服务。

最少验证先以替身检查事务中途失败全回滚、并发最后slot、旧seq保留、重复begin与重复完成、未知/无请求/超额及快照内Run两段汇总，并核Run计费列不变；随后受控合成新Run（必要的分诊期初/旧seq也是新测试资料）真实PG验证同样原子性，并只发一次已验M2查询核正确UUID/来源hash及原子refs。所有故障/拒绝对照不发模型或新增真实外部请求，原triage及历史unknown不动；真实读回成功才放行M3。无模型、OS、部署、提交推送，不接完整循环或旧Run恢复。

## 2026-10-23 统一调查M0起步与检索前提

用户已授权逐模块实施，后追加工具影响设计先讨论。沿本change 2.1/3.1/3.4/4.1，预期与实际统一见[逐步记录](../../../docs/operations/unified-investigation-implementation.md)。本轮固定M0只读范围及M1目标合同；M0核既有合成湖事件后，发现其无外联目标，不能代替候选复合场景。main最新7ea813a只有文档变化，测试工具尚无成套历史事件投放。

[工具数据建议](../../../docs/architecture/investigation-tool-data-plan.md)提出复用CH原入湖/typed查询、增加同批告警和真实来源UUID夹具，逐个补绝对窗口/逐条ID/语义字段；OS只按场景接IOC来源，独立测试索引与确定查询路线，原始事件全文/审批另议。该建议尚待讨论，M0未放行，不开始M1代码或M2工具/数据写入；spec中新增M1条款为目标，不是已实现。下文保原批次范围及历史事实。

## 2026-10-23 调查统一设计v3修订（仅文档）

用户确认先修订方案，再讨论是否推进。最新设计以[调查模块规划设计文档](../../../docs/architecture/investigation-planning-design.md)为唯一主入口；本次在基线`3fa4be3`、分支`codex/investigation-working`的独立工作树`E:\aisoc\socai2\.local\worktrees\investigation-working`整理，原目录`E:\aisoc\socai2`中的Windows环境工作及未提交内容留在原处，不混入本设计批次。

本次修订七项合同：

1. 行为性质与业务授权分别判断，未知授权不自动推出恶意，有授权记录也不自动推出行为安全。
2. 可信任务指令与告警、日志、工具返回、知识等来源材料隔离；来源正文不能更改策略、范围、能力或采用规则。
3. 结论适用范围与允许查询范围分开，查询发现的关联实体不自动成为已确认影响对象或扩大交付范围。
4. 小模型按相关问题分组调用；单组输入输出有界，跨组引用与最终综合保留来源，不要求一次输出全案全部结构。
5. 首版建议使用后续调查阶段共享预算：主分析、Deep、领域解释、修复及可选写作共用该阶段额度，Run总成本汇总首次分诊与调查两段；明确预算作用域、期初用量及unknown，不改当前配置数值。
6. manifest统一约束选定的热读、冷读、报告、流式终态通知及主API/Case投影；进度与正式发布结果分开，旧Run状态不能替代统一调查状态。
7. 分别验收模型分析质量、程序安全与交付合同、成本和时延；程序拦截错误并降为partial不计为模型判断正确。

首场景策略卡须留待M0核对实际来源与字段后确定，本次不启动M0实施或真实查询。上述内容仅为设计修订，不新增业务规格、不勾原任务、不启动业务实现/测试/模型/部署或Git提交推送；原5/15、旧失败及unknown保持。本次文档检查与独立审阅回执另行记录，不以方案修订代替通过结论。

## 2026-10-24 M5最小实施合同

M4限定放行后的下一块按M5.1纯任务/参数/去重合同→M5.2持久模型选择→M5.3单问题查询循环及真实接缝推进。第一场景只绑定Q1、一个已选成员和activity_records，程序固定父Run/scope/身份，模型仅给结构化tool/parameters/reason选择；选择不是实际执行回执。参数校验复用M1/M2，不新增任意SQL或后端。后续局部候选仅回答任务问题，保全案其他问题及未知，不形成全案报告。

父M3.begin由调用方负责，Deep不begin/重置stage。首个循环最多一次查询、两次模型选择/回答，仍消耗父调查共同额度；程序任务ID及查询签名稳定，多任务步骤/尝试身份不同。下一轮只能消费留存已确认的有界材料；unknown/留存缺口/到限不重调或追加总结。详细逐步输入输出和实值预期在唯一实施主文档；本段是实施前合同，不宣称M5已实现。沿原责任3.1/4.1分步留证，不新增任务清单完成数，5/15保持，无部署/提交/push，OS后置。
