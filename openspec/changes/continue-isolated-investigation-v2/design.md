# Design: 独立调查v2的原设计与集成边界

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
