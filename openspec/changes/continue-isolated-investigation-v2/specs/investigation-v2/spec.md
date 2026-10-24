## ADDED Requirements

### Requirement: Validate explicit fixed or program full DTOs in a separate authenticated API gateway

b2.4d3 SHALL 仅新增API兼容网关/new factory，显式Bearer＋原cases/alerts双read权限、current tenant/actor转发、独立COMPAT backend配置/一次有界GET且无fallback。新checker对known两族DTO exact结构/版本/stricttypes/manifest-execution-MD与section引用做同版校验，旧源码/DTO/MD保持；不将selfhash当实际来源或MD语义证明。

#### Scenario: Current permitted user reads a consistent known result
- **WHEN** 原认证/双权限通过，backend在new config提供完整固定或program DTO/progress，family/schema/identity/typedrefs/hash及五种result/preparation/evidence封闭组合同版（合法fixed A3 blocked/null和unadopted/null均partial）
- **THEN** 原完整dict和MD字节透传，不重渲染/添旧字段；只server currentidentity和backendtoken进入内部GET，无callerowner/version/query控制或读写副作用

#### Scenario: Input configuration backend or versioned DTO is invalid
- **WHEN** 旧env-only、无凭据/权限、覆写参数、unknown/mixed/缺多字段/typedalias/ref或hash错误、null evidence伪ready/错族path/前缀或availability不匹配、超限/非200/redirect/timeout出现
- **THEN** 准确拒绝/脱敏502/503/404/409无重试/旧版回落，不泄配置；真实auth/PG/网络、d4组合和a4.2仍另验

### Requirement: Expose compatible owned results only in a separately configured internal GET app

b2.4d2 SHALL 新增显式独立process内部GET app及COMPAT独立token/PG/CA配置，无旧env默认回落；可信网关Bearer认证后核当前tenant/actor/Run，调用兼容ownedreader，拒body/query/owner/version覆盖。旧app/注册不改，token不等于用户RBAC，完整DTO证明留d3。

#### Scenario: A trusted gateway reads a fixed or program result
- **WHEN** new explicit token和当前tenant/actor/Run有效，ownedreader返回known schema/exactidentity/publication state
- **THEN** 原完整DTO透传/只GET，无新行/调用/发布；ownedpool生命周期独立并有界清理，injectedreader不误关闭

#### Scenario: Credentials configuration input or backend envelope is invalid
- **WHEN** 旧env只有、缺错token、bad/nilidentity、body/query覆盖、reader异常/unknown或identity混包出现
- **THEN** 准确401/400/404/409/503/502且不fallback/泄露配置或重试；旧token轮换后拒，旧app行为保持，后续API gateway/组合及a4.2仍待

### Requirement: Select only a verified owned fixed or program result without caller version control

b2.4d1 SHALL 新增owned兼容reader，在同tenant/Run锁内强核唯一managed begin/full原件/strictseq/canonical身份，再按explicit已核fixed或program版本走各自restore/store同conn；unknown/generic/mixed/双begin拒不fallback；同锁进入branch store前须核该Run所有unified_事件均在所选允许kind集合且agent符合该writer，未知begin/control不论位置都拒。owner来自原件而非caller，旧reader/DTO/MD不改。

#### Scenario: A current permitted reader requests an existing fixed or program Run
- **WHEN** caller已核auth/read permission且current principal允许tenant，owned唯一begin和原件/版本可完整核
- **THEN** 同事务恢复相应原context并读当前manifest或原progress，fixed完整DTO/MD同旧、新owned_program schema明确而公共结构保持；无新行/预算/调用/发布或owner选择

#### Scenario: Owned origin version type or published basis is inconsistent
- **WHEN** nil/foreign/未知或双begin、event/receipt/hash/type/owner/manifest/material断链、late结算等出现
- **THEN** 明确拒或脱敏交易错误，不按客户端mode换版本、不返回旧报告或偷偷publish；后续内部GET/gateway/组合兼容与a4.2另门

### Requirement: Restore only the original new program read context with current read authority

b2.4c SHALL 独立new restore纯函数，从caller已核owned newbegin/body/state重建原M1和new profile/plan，当前tenant许可与历史principal分开，canonical全量比较及严格整数拒typed alias，不读活Alert或改旧restore。结构/hash不替代actual auth/owner/event链。

#### Scenario: Another currently permitted reader restores a retained program context
- **WHEN** current principal允许tenant，原initial newbegin及完整scope_sources/控制/profile/newplan一致
- **THEN** 精确恢复原typed request/全文/refs/窗口/六问，新pub SQLdouble读取可得同manifest/MD/usage，不新增行/预算或I/O；不授予重启或续跑权

#### Scenario: Frozen type source version or current authority is inconsistent
- **WHEN** old/unknown/mixedruntime、自洽重hash控制漂移、bool/float整数别名、缺多source/原文hash或current tenant许可错误
- **THEN** 拒恢复不回落旧版本/当前Alert，不重选预算/owner；oldrestore及旧MD保持，d owned/HTTP和a4.2另验

### Requirement: Persist the new program manifest atomically and read only its complete current basis

b2.4b SHALL 新增独立new publication store继承ProgramReconExecutionStore，显式适配new pub event的latest/body/state校验，保原begin/full原tool-source-handoff链；唯一pub marker/4工件同事务，JSON比较canonical，旧store/Run列不改。只SQLdouble，不发送通知或实际业务访问。

#### Scenario: A current complete new handoff is published or read again
- **WHEN** 原begin/工具/全部retained及当前停止basis完整，或已有唯一new manifest及全部sameevent工件
- **THEN** 首次1event4artifacts全部确认后published/committed，重复只读完整同manifest/MD/execution/sections/usage且无通知/写入；无pub仅progress，不自动发布

#### Scenario: Original chain currentness typed structure or commit is uncertain
- **WHEN** bad event/pointer/owner/hash/source（即未采用也核）、bool/int伪等值、多个pub marker、later结算或rollback/ACK未知出现
- **THEN** 拒旧交付或不确认成功，不回落/重发/刷新预算；原失败保留，完整pub状态与原stopped执行basis必须canonical同，actualtool真实性在newstore完整重建证明，不由selfhash代替

### Requirement: Prepare a separately versioned program publication without changing fixed results

b2.4a SHALL 仅新增pure program publication/renderer，固定new manifest/execution/sections/mapping/renderer/package版本及完整closed组合，核new handoff/source/current全量转换/用量一致，重建ProgramMaterial有限result；不伪EvidenceView/模型资格，不改旧发布/MD。候选不等于持久交付或通知。

#### Scenario: A current owned program handoff has valid material or explicit unadopted state
- **WHEN** caller已核owned三工件、pure版本/引用/hash/当前finish转换相符且新材料有限result重建一致
- **THEN** 生成有限三维状态/完整sections/refs/实际未知用量和确定性安全MD，性质授权全文语义边界明示，report/execution持久ref空；无材料须由None evaluator/固定reason/实际stop/retained refs完整重建unadopted结果并canonical精确比较，sixQ/criticality/coverage自洽rehash也拒，不把observer当source

#### Scenario: A result is mixed stale or rehashed beyond its finite policy
- **WHEN** 新旧或未知版本、错误material/model标记/伪facts、late结算或scope/owner/账/状态转换不符
- **THEN** 拒candidate，不用旧runtime或旧MD解释；b持久、c恢复、d owned/HTTP另验，a不连接PG/HTTP或提交发布

### Requirement: Project canonical Alert data only for the explicit new program intent

b2.3d2 SHALL 新增独立完整source投影，先校new program intent版本，保canonical_program_alert_recon_projection.v1完整原文/hash与真实字段路径、M1限制，不调用旧projection/转换旧intent。仅caller已核tenant/actor/权限及四列owned Alert前提，函数不授予其真实性或I/O权限。

#### Scenario: An unambiguous owned ordinary source is projected and exercised offline
- **WHEN** new intent完整有效且单一telemetry/source UUID和受限字段可核
- **THEN** 保完整source与规范化查询/精确refs；预建Run的newruntime SQL/Mock可一次查询得到有限4facts ready/model资格false，冷读不重派；旧restore对new begin尚拒，未伪称兼容完成

#### Scenario: Old mixed ambiguous or unowned input is supplied
- **WHEN** 旧/未知/混版意图、越权归属、source身份/数量/字段不符或正文混指令/答案
- **THEN** 控制或来源错误直接拒、正文仅原样材料，未按正文改变策略；不回落旧runtime或截原文。无新Run/真实访问/发布，b2.4兼容仍前置

### Requirement: Bind a new explicit program start intent without upgrading old operations

b2.3d1 SHALL 以新request/intent/ref/decision固定manual program路径及完整closed policy_versions，复用语义不变的显式StartBudgetPolicy；同tenant/key保持与旧完全同Run/executor命名空间。旧意图不升级，新旧同key异文必须冲突，未知schema/自洽混版拒绝。纯合同不授予权限、持久性或外呼。

#### Scenario: Equivalent new request or matching owned retained operation is checked
- **WHEN** 当前caller已核tenant/actor及权限，新请求完整结构/窗口/服务端预算/版本合法
- **THEN** 稳定new request hash/ref与同key身份；仅完整相等的原新意图可read_existing_only，缺原件仅requires_atomic_admission，两者may_begin和external_call_authorized都false

#### Scenario: Same operation key is reused across old new or changed request terms
- **WHEN** retained旧意图、新意图异文、混合或未知版本/额外字段出现，即使全部selfhash重算
- **THEN** 验原格式/身份后拒冲突或未知版本，不改变Run身份或刷新预算，不转换成旧版本继续执行；旧函数/意图及报告保持

### Requirement: Dispatch one manual program query only after durable claim and reservation

b2.3c SHALL 新增独立ProgramReconRuntime，constructor钉新ProgramReconExecutionStore/manual plan；仅首次已确认claim再经原DurableActivityRecords的M3 reserve后单次派发，重复/unknown不接管或重跑，不改旧controller/gate/预算内核。交接核实际原件，新模型/Run/Case/发布/真实业务I/O不在本块。

#### Scenario: Confirmed new owner executes or another invocation repeats
- **WHEN** 新运行已有owned begin，首次claim及M3 reserve均确认；或并发/后续重复看到claimed/blocked/stopped
- **THEN** 只有首次可一次MockTransport查询并按真实completion或独立observer交接；重复返回active/pending或只读原交接，无新HTTP/attempt。普通完整Alert有限4facts/ready，模型资格仍false

#### Scenario: Persistence is ambiguous or execution is cancelled
- **WHEN** claim/reserve/complete/handoff回执不确定、保存失败或owner/duplicate取消发生
- **THEN** 不重放/接管，不把控制不变量错伪预算停止；仅owner最佳努力交接已有观察后重抛，重复不抢封cancelled handoff。buffer只在原件确认保全后清，否则保持；未知及迟到结算仍遵原M3，旧行为及报告字节保持

### Requirement: Persist the closed program runtime on the shared M3 ledger without dispatch

b2.3b SHALL 以独立ProgramReconExecutionStore复用M3同Run锁/预算/append/complete，冻结新manual组合并原子保存begin/claim/限定reserve/停止交接；旧store/base/Run列不改。当前scope/limits/opening/input须同唯一owned原始begin核，控制归属/hash错误拒；commit未知不能给外呼许可。没有新Run/HTTP/模型/发布。

#### Scenario: A claimed and settled program query yields a frozen handoff
- **WHEN** 当前actor由caller已核，owned fresh Run和原begin/工具completion全部完整且符合冻结组合
- **THEN** 原子新handoff/state以真实程序prep或明确unadopted保存，normal有限事实可ready、原停止和M3账保持；重复只读原件无新行/预算。raw正文不合格不伪validated，unknown观察另存而不当completion

#### Scenario: Origin integrity reservation retention or commit is uncertain
- **WHEN** tenant/owner/原始begin/plan/预算基线/tool event-kind-hash不符、半写失败、ACK未知、未确认输出或重复观察异文
- **THEN** 拒绝或保明确未采用/不确定，不回落旧runtime、不重置/重放；实际未采用结果无事实/partial、source未确认而非false可用性，held refs保所有已核材料。只有实际owner后续controller在确认claim及真实M3 reserve后可外呼，b本身不执行

### Requirement: Freeze a closed program runtime policy before any reserved work

b2.3a SHALL 新增独立program runtime纯plan/state合同，固定runtime/state/plan/material/facts/completion/preparation/result/handoff/未采用结果的完整版本组合，纳入plan hash及step/attempt派生；仅已核manual alert profile/fullwindow Q1/activity_records；manual为该新runtime固定控制政策，make/install拒automatic，descriptor由scope＋固定manual重建，不从待核plan读取trigger作为权威。旧state/plan不升级，caller不得混配版本或靠源正文选择策略。复用M3预算/预检/停止语义，不产生实际提交/外呼或新Run。

#### Scenario: First claim or a repeated interrupted request is considered
- **WHEN** owned caller提供已冻结的新runtime state及真实时钟输入
- **THEN** 仅ready首次可产生需提交的claim决策，之后仍需真实M3 reserve；重复claimed/blocked不接管、不追加尝试，stopped只读原handoff。预检、取消、停止保原共享额度/期限/unknown，纯返回外呼未授权且不改原输入

#### Scenario: A closed policy or deterministic dispatch identity is changed
- **WHEN** 新旧或未知版本混搭、额外/缺少policy项、plan/profile/query/step/attempt漂移，即使重算自身hash
- **THEN** 重建受控plan并拒绝，不回落旧runtime、不重设M3预算或制造新attempt；必要存储归属仍由后续新store核验。后续store/controller/start intent及发布读取兼容须各自细卡验收

### Requirement: Evaluate program material under an explicitly new finite completion policy

b2.2 SHALL 仅用已核当前scope/snapshot的独立ProgramMaterial生成有限字段事实及新版本program_alert_recon结果/preparation，不构造EvidenceView或模型候选；新finite_network_program_fields.v1事实政策及bounded_full_window_program_fields.v1完成政策显式入hash/refs。正常完整结构来源查询可有限ready；模型未请求/Alert全文未语义研判明确为非阻断目标外缺口，绝不表示整份Alert或恶意/授权/影响已判。旧fixed/evidence/A3路径保持。

#### Scenario: Normal full Alert text or full model framing blocks the old view
- **WHEN** caller已核owned/committed的来源与整窗查询支持当前有限谓词，无原有blocking gap，即使原Alert512或组合model12KiB门使旧路径受阻
- **THEN** 新纯prep给真实typed有限事实/Q1-Q2-Q5及限定ready，Q3a/Q3b/Q4、性质和授权继续未评估/未知；模型not_requested eligiblefalse，全文可追溯而非已理解，persistence not_attempted，无Run/调用/发布

#### Scenario: Missing uncertain incomplete conflicted or stopped material limits the result
- **WHEN** 空/失败/unknown、无材料、子窗、冲突/缺版本/截断/源正文提取缺口或owner已观察停止
- **THEN** 保真实事实/refs/gaps及停止原因、partial，不增加总结模型；必要来源/材料/hash/scope/版本/当前snapshot或类型错误直接拒，不能降为成功。新runtime和M7/读取的版本选择须后续独立冻结/兼容验证，旧记录不重解释

### Requirement: Separate verified program material from gated model views

b2.1 SHALL 新增独立ProgramMaterial类型/schema/hash/scope/revision，以现必要材料/参数/来源版本合同验证完整结构材料，并只引用原begin的完整Alert正文；程序材料构造不受Alert512B和完整模型视图12KiB门耦合，不复制或截断原Alert，不冒充EvidenceView/模型已消费。所有必要验证仍拒，空/失败/unknown/子窗/截断/冲突/遗漏版本及源正文提取缺口仍保留，后续新事实政策另验。不修改旧model builder和其512/I2门。

#### Scenario: Large retained Alert text or complete model framing prevents a model view
- **WHEN** 原context/工件经caller核owned/committed，来源/查询/hash有效但原Alert全文或组合模型视图超过其门限
- **THEN** 可构造独立程序材料，保完整结构事件/版本/覆盖/缺口/index及原Alert全文ref/hash/字节，模型状态not_requested且不可交旧模型接口；原模型路径仍阻断。本步不产生facts/ready/Run或外呼

#### Scenario: A required source or material integrity check fails
- **WHEN** tenant/scope/source Run/参数/receipt/来源版本/hash/body/关联有错，或程序材料自身schema/ref/hash/revision/scope被改
- **THEN** 明确拒绝，不捕获模型投影异常伪造材料，不把错误改成模型不可用；完整原文/预算不改，无I/O。新runtime/preparation/完成及发布读取组合须后续逐步冻结验证，旧Run仍按旧版本解释

### Requirement: Project an owned canonical Alert into a frozen manual start profile

M8a4.1b SHALL 纯读取caller已核owned的canonical Alert四字段投影及当前intent/tenant，按当前network_observation.v1仅接唯一telemetry和唯一一致source UUID，核tenant/target/类型与TCP443后构造M1/业务profile。来源真实四字段、完整raw_event嵌套正文、原表示及逐字段路径以版本化data-only文档/hash冻结；显式normalized projection解释M1参数路径，不冒称PG有相应实体列。普通非synthetic告警可用，不依赖评测卡/固定测试描述；本块不证明实际认证、owned SQL或持久启动。完整文档会结构性超过现512B Alert消费门；b1仅验冻结/M6 begin/a1及正确partial，b2须另验完整留存与有界消费分离并使正常有限事实/ready通过后才能a4.2。不得用截断原件或提高现门限掩盖此接缝。

#### Scenario: A supported owned source is frozen without executing its text
- **WHEN** 当前允许的tenant与intent/Alert一致，唯一telemetry与唯一source ID精确绑定且字段满足当前政策
- **THEN** 返回同intent Run/窗口/profile的单成员BusinessProfileRequest，实际来源/路径/hash原件可在scope_sources读回；正文中的指令只是材料，不能改profile/范围/预算/结论，无I/O/Run/外呼。与M6 begin/a1恢复保持严格shape兼容；在现A3消费门下明确projection_blocked/partial，不声称本b1已可正常ready

#### Scenario: A source is missing ambiguous inconsistent unsupported or too large
- **WHEN** 多/缺telemetry或source ID、tenant/target/来源绑定不符、非法字段/JSON/协议或超过材料界限
- **THEN** 明确拒绝，不默认取首项、补假值/合并/裁剪或截断；原材料不改。后续匹配重试读已冻结原件，不投影当前Alert覆盖原Run；后续M3/I2大小gate仍独立有效

### Requirement: Normalize stable manual alert start operations without granting execution

M8a4.1 SHALL 在当前已核认证/启动permission及tenant/actor的调用方前提下，纯规范化当前alert_recon操作：稳定tenant内operation UUID、目标Alert、≤5分钟UTC半开窗口、版本和可信服务端有界预算政策。Run身份只能由固定namespace/tenant/key派生，不能将参数、actor或时间变化变成另一Run；完整请求含actor/目标/窗口/所有版本及预算政策，按规范JSON产生hash/ref。owner为内部派生值，不是caller授权。当前仅manual，无Case/自动/Deep或实际持久/外呼。

#### Scenario: The same operation is retried or its terms are changed
- **WHEN** 当前主体仍有该tenant权限且调用方已重新核启动permission，提供与已核owned保留intent相同或不同的规范请求
- **THEN** 相同仅给原Run read_existing_only判定；同key改actor/目标/窗口/预算/版本拒，不能换Run重置额度。无保留intent仅requires_atomic_admission，两者may_begin/external_call_authorized都false；首次持久准入/commit和实际claim/M3才可能执行

#### Scenario: An identity window policy or retained intent is invalid
- **WHEN** 缺/错tenant主体、非法/nil身份、不支持profile/trigger/version、超窗口/非法预算、或保留intent结构/hash/ref/派生身份不符
- **THEN** 明确拒绝，原输入/预算不改，无I/O/Run/调用；canonical比较区分bool与integer。duration不变成当前时间相对deadline，后续首次PG准入冻结一次，匹配重试保原值；纯自hash检查不冒称原件owned或实际认证已验

### Requirement: Verify isolated result GET across two real processes without ledger change

M8a3.3 SHALL 仅对原已发布受控Run4dfd374a-17a6-5fec-833b-803bfbcb85c6执行GET，启动新的loopback API网关/Agents内部读两个进程，分别使用新测试service凭据/专用read token及新最小PG角色。MUST 无POST query/publish/start、model、Run/Case写入或旧服务切换。role仅表SELECT，Agents另Run UPDATE(id)供既有行锁，不授INSERT；旧角色/共享policy不改。

#### Scenario: Real API authentication returns the immutable PG result
- **WHEN** 新API凭据/受控tenant认证通过，经网关发送当前tenant/actor到新内部read app，读原M7结果
- **THEN** 200结果manifest/MD/execution与原M7回执及PG一致；缺/错凭据、缺/非法/未知tenant、GET覆盖及随机缺失Run分别拒绝，内部缺/错token或actor拒绝。前后完整6事件14工件选中列/正文hash相同，原M6基线/用量/旧列/MD3111B保持，额外activity/model/publish0。实际权限撤销不通过生产RBAC改表模拟，ASGI权限测试与真实service认证范围分列

#### Scenario: Read services fail or cleanup must run
- **WHEN** 配置/认证/PG/GET/回包核验失败或任一进程未就绪
- **THEN** 本批留存失败，不回落旧服务或发调查；仅按持有Popen handle和创建时间清理两个新进程，新角色NOLOGIN/撤权/活动0，密码token不进公开回执。真实结束独审后才放行此只读接缝，不能据此宣称启动/Case/Deep或生产部署已完成

### Requirement: Expose fixed results through explicitly isolated authenticated read applications

M8a3 SHALL 按a3.1 Agents内部只读HTTP→a3.2 API认证网关→a3.3受控真实PG/双进程GET逐块推进。旧应用/路由/认证权限默认不改。Agents独立app只接受新的专用read token和显式tenant/actor、Run UUID，调用a2；无共享旧token/dev回落、启动/写入/通知路径。API独立v2 app仅复用既有认证，并要求cases:read及alerts:read；tenant和actor只从CurrentUser得出，向内部read app转发，不采用客户端scope/owner/tenant覆盖。credential/permission在本HTTP接缝验证，纯TenantPrincipal不代替认证。

新API结果GET SHALL 先强制非空Bearer凭据，再复用原get_current_user认证和两项permission；即使旧dev bypass显式开启，无凭据/空Bearer/其他scheme仍拒绝且不转发backend。MUST 不修改旧认证/dev分支或原query路由行为。

#### Scenario: An authorized reader gets the same manifest over the explicit read surface
- **WHEN** API用户已满足两项既有read权限，目标Run属于其当前tenant，内部专用read token及owned材料有效
- **THEN** 仅GET读取同manifest/MD/execution，显式profile/target/旧状态和新publication分开；网关复核返回tenant/Run/schema及已发布MD的manifest hash，未发布无正式MD。无新Run/账本、查询、模型或通知；原旧路径不注册到新版独立应用

#### Scenario: Credentials identity permission or backend result is invalid
- **WHEN** 缺/错read token、缺/非法tenant/actor、当前read权限不足、客户端给scope/owner/body/query覆盖、跨tenant Run或下游响应身份/hash不符
- **THEN** 在相应边界拒绝，读权限不足不转发，客户端字段不改变认证tenant/actor；超时/下游坏件只明确不可用，不回落旧报告、重发查询或暴露token/DSN。token在每次请求核验，实际permission/撤销覆盖按各直接测试和受控回执如实列出

### Requirement: Read owned fixed results without caller-supplied owner or scope

M8a2 SHALL 在当前已认证读取许可的TenantPrincipal与显式tenant/Run下，由服务端加载owned Run和唯一unified_recon_started事件及原begin输入/state工件，核tenant/run/event、kind/agent、payload/body/state hash/receipt及初始owner，再用a1恢复原读上下文、复用M7精确manifest读取。调用方不得指定owner/scope/source正文或以旧Run.status猜测新完成。该层 SHALL 与M3协调同Run行锁，在同一事务内核上下文/当前版本并返回，不新建Run/事件/工件或派发；当前HTTP认证/permission撤销接线在后续独立入口验证。

#### Scenario: A currently permitted reader obtains a frozen result by Run ID
- **WHEN** 当前principal允许该tenant，Run及唯一begin marker、所有owned工件完整，可能已发布也可能仅有进度
- **THEN** 服务端自行确定历史owner/profile/scope并得到同M7 manifest/MD/execution；返回显式profile/target/objective/Run和publication状态，未发布无正式MD；不加载当前Alert或改账本/预算，另一个同tenant主体也只使用当前读取许可

#### Scenario: Ownership or frozen begin is missing ambiguous or corrupt
- **WHEN** 无当前tenant许可、该tenant无Run、无/重复begin marker，或事件/工件/owner/引用/版本不匹配
- **THEN** 明确拒绝，不接收caller修补上下文、不搜索其他tenant/旧报告、不创建新Run或接管unknown；驱动错误只返回明确持久读取错误，不回显DSN/原文。实际PG/HTTP效果在直接替身与后续受控接缝分别记录

### Requirement: Restore a fixed result read context from its owned frozen input

M8a1 SHALL 先以纯函数从已核归属的M6 begin输入/状态工件恢复alert_recon读上下文，再接正式HTTP与启动。当前读取权限必须来自当前认证主体；旧scope内principal只是冻结来源，不给当前caller授权。恢复 SHALL 验原input_hash、scope_hash、scope_sources各text/hash/UTF-8字节及完整引用、profile/运行和完成政策版本；用现有M1合同重建后，controls/sources/descriptor/plan须与冻结原件精确相等。当前可变Alert正文不参与既有结果读上下文，不因Alert后来编辑改变历史manifest。

#### Scenario: Another currently authorized analyst reads the frozen result
- **WHEN** 当前主体已获同tenant读取许可、原owned begin工件完整，Alert当前正文与当时不同或无需再次加载
- **THEN** 恢复原profile/冻结scope及版本用于同manifest读取，保原principal/字段出处/原文引用；当前主体不同不会重写原调查身份。纯恢复不创建Run/执行查询/模型/重设预算或接管unknown

#### Scenario: Frozen provenance or current tenant permission is invalid
- **WHEN** 当前主体无tenant权限，或原input/scope/source正文hash/字节/引用、问题/能力/窗口/profile/plan/版本不符或缺件
- **THEN** 明确拒绝，不从调用方或当前Alert猜测修补，不放宽M1、不回落旧报告或以冻结principal代替当前认证；来源存储归属/当前读permission由后续持久读取/HTTP接缝另核，纯函数不冒充其已完成

### Requirement: Verify fixed result publication on the existing stopped test Run

M7c SHALL 仅对M6.2c已独审且无unknown/未结算的固定Run4dfd374a-17a6-5fec-833b-803bfbcb85c6追加发布，不创建新调查、重跑查询/模型或开启HTTP服务。使用全新精确PG角色/私密配置，公开opt-in probe先离线guard合同，真实执行前确认原5事件10工件及冻结handoff；原M6.2回执保阶段快照，不反写。

#### Scenario: One PG publication survives a fresh process read
- **WHEN** 同Run/owner/profile原5事件10工件完整且尚无publication，publish前读取无正式报告，再只执行本次发布
- **THEN** 新增1事件4工件后为6事件14工件；同manifest热读、重复publish只读且通知null，新独立进程仅read冷读一致。另以PG READ ONLY核全部14工件字节/hash/event/run/tenant归属、原5事件边不变及新manifest/state/execution/report引用/版本，用量model0/tool1/unknown0/unsettled0与旧Run列不变；没有新增工具或模型调用，通知仅描述未投递

#### Scenario: Publication trial is uncertain or no longer matches its baseline
- **WHEN** 原Run已发布、出现不同状态/缺件/新unknown，或本次提交/子进程结果未知
- **THEN** 原试验留存并停止，不自动换Run/清预算/重发；可用独立只读核实际状态。仅关闭本次新角色并核NOLOGIN/撤权/活动0，子进程按持有handle及创建时间核身份后清理；真实结束独审前不宣称c通过或M8已接

### Requirement: Publish one immutable fixed recon result version

M7 SHALL 按a纯同版包→b同Run事务发布/读取→c真实PG前后冷读推进，仅fixed_alert_recon_runtime.v1。发布前 MUST 核owned handoff指针、scope/profile/plan及相关attempt/M3状态仍与构包基线一致；late settle或新相关状态不许混版，拒绝后保材料。已正常停止后的单纯墙钟跨deadline不重算ready。旧Run status/completed_at/tokens/cost保持，新三维仅发布投影。

manifest SHALL 固定schema、investigation_id（本批首Run=run_id）、tenant/run/profile/target/objective、scope/完成政策/renderer/映射版本、questions/analysis/evidence与execution快照、MD、前manifest=null及留存缺口。前三块 MAY 共用owned handoff的固定versioned section，引用钉住artifact ID/hash/schema/section及section hash；缺preparation、projection blocked或未采用来源时evidence明确null/availability，保held refs。本次execution发布快照独立有界保存，原M3/source state作来源ref，避免manifest与新state哈希循环。

#### Scenario: A finite ready handoff is prepared and published once
- **WHEN** 当前有限来源目标ready且无阻断/执行停止，所需材料有效，按原范围/版本正常停止后发布
- **THEN** 纯准备仅candidate；同事件原子保存execution发布快照、确定性MD、manifest及指向它们的state，提交后才返回published/通知描述。版本fixed_recon_publication_state.v1映射finished/complete_for_scope/none，显式有限objective，性质/授权不升级，Alert/Case不关闭；重复返回原manifest，不新增查询/模型/发布版本

#### Scenario: Partial and cancelled results keep their source gaps
- **WHEN** 合法但缺证/投影阻断/未确认来源/unknown或已观察取消的handoff仍可可靠交付
- **THEN** 映射stopped/partial/awaiting_human，已观察取消为cancelled/partial/awaiting_human；发布工件committed不等于来源完整，原gaps/held/unconfirmed refs/unknown/unpriced及预留保持，不称人工已接管。身份错误/缺必需工件/坏hash及发布失败不能伪装普通partial成功

#### Scenario: All official reads and notification descriptions use one committed manifest
- **WHEN** 发布前、发布后、清内存后或提交不确定后显式读取新版结果
- **THEN** 未发布只显示进度/候选及交付缺口，不用旧report/triage status冒充；已发布按manifest精确引用校验读取，缺件/坏件显式拒绝，无legacy fallback。重复不重渲染覆盖，unknown提交只读原指针、不重查；提交后通知描述携同manifest引用，M8接真实HTTP/stream前不声称已投递

### Requirement: Verify the fixed runtime through one independent real v2 query

M6.2c SHALL 使用全新受控batch/Run与临时最小writer/独立reader、loopback独立v2 API进程，复用当前共享网络场景及既有CH reader，只读canonical Alert/已入湖数据，不新增写湖/模型/Case/旧入口。实际FixedReconRuntime.begin/execute SHALL 经ReconExecutionStore事务/M3 reserve、新HTTP/CH、工具完成/A3、handoff保存；重复新runtime读取不得再查。测试配置 SHALL 显式model0/tool1/tokens0/cost0/unsettled1、DB期限120秒。

#### Scenario: One controlled runtime produces a durable limited handoff
- **WHEN** 当前PG/CH预检与离线合同通过，且新Run尚不存在
- **THEN** 实际只1次认证activity query，匹配1行/排除两对照，结果有限ready并保nature unresolved/authorization unknown；独立PG读回5事件/10工件的UTF-8/hash/Run/tenant/event关联、冻结版本/计划、工具body/来源hash、M3 model0/tool1/unknown0/unsettled0、handoff与冷读一致，重复不增事件/查询。旧Run列及新Run生命周期/计费列保持到M7，不将候选当发布完成

#### Scenario: The controlled process fails or stops
- **WHEN** 校验/查询/保存/提交出现失败或unknown
- **THEN** 留进度/原失败，不自动重放或换Run刷新额度；只核本次PID与创建时间停止API、关闭新PG角色并撤权，原reader/数据和旧Run不变。配置/密码留忽略.local，公开回执不含凭据；真实结果与清理独立核验通过后才放行M6.2有限路径

### Requirement: Persist fixed-recon control and handoff atomically under the owned Run

ReconExecutionStore SHALL 复用原三张ledger表、同Run行锁/tenant/owner及M3预算函数，固定受支持runtime版本和event kinds。begin SHALL 在唯一事务冻结profile/完成政策/运行计划和来源；已有unified阶段、非running/已结束Run或不匹配执行器 SHALL 拒绝。claim仅在事务确认后允许控制器进入既有DurableActivityRecords，工具外呼仍以实际M3 reserve提交为前提；托管reserve只接受冻结请求。通用store SHALL 拒绝托管版本，托管store不能接管旧阶段。

#### Scenario: Two callers claim or finalize one runtime
- **WHEN** 同Run重复或并发claim/finalize
- **THEN** 仅一份claim能进入首次派发，其他只读进行中/原交接；交接正文与指向它的state snapshot同事务保存，只有提交确认后返回committed。已存交接hash/归属核对后重读，不插重复事件或覆盖异文，旧Run状态/计费列保持到M7另验

#### Scenario: A tool response is complete, unknown or not durably confirmed
- **WHEN** 工具已有真实completion工件，或预留仍未结算/完成提交不确定
- **THEN** 仅从当前Run已核工具工件构造CommittedMaterial并走A3；unknown资源保留且不重跑。未确认输出不作来源采用，可单独以unconfirmed观察工件随交接同事务保存；字节/hash/归属明确，不冒充原completion。source语义校验失败单列rejected材料/引用，事实不采用，不降成已核projection block

#### Scenario: Persistence or cancellation interrupts the runtime
- **WHEN** begin/claim/预留/工件读取/交接写入出现异常或明确取消
- **THEN** 未确认提交不给派发权限；取消记录程序观察并传播，保已提交资料和未知预留，不自动重放。最后一份交接需独立读回验证，纯准备中的not_attempted状态不作为实际留存回执，人工仍仅required。M6.2b离线事务替身不等于PG已验，c真实新Run另验

### Requirement: Freeze and claim one bounded fixed-recon runtime plan

M6.2固定告警运行 SHALL 在任何外呼前冻结已核alert_recon业务描述、scope hash、fixed_alert_recon_runtime.v1执行器与bounded_full_window_source_check.v1完成政策、完整冻结窗口的唯一activity_records/Q1参数及确定step/attempt身份。M6.2a纯控制只构造计划/状态转换，MUST NOT 自称已提交预留或获得外呼授权；M6.2b须以同Run单writer事务提交claim，再使用既有M3真实预留门，不能省略或重开stage。

#### Scenario: The same runtime is claimed or revisited
- **WHEN** 初始ready计划准入通过，或同计划处于claimed/blocked/stopped而被再次执行
- **THEN** 首次仅给需持久提交且仍需M3预留的dispatch决策，不增加预算计数；claimed返回进行中或中断待核且不再派发，blocked只允许交接，stopped只读既有交接。不得换attempt刷新次数，不能把重复执行当新查询

#### Scenario: Admission or completion must stop
- **WHEN** 已有unknown/未结算、额度/期限不足或预算breach，或收到明确取消
- **THEN** 保实际M3摘要/预留和停止原因，不释放unknown或发总结模型；预算/时钟取事务权威时间，M3必要合同错误不能吞成一般额度停止。正常已完成的唯一查询恰好用满次数不等于超额，停止评估须区分后续准入与已产生结果

#### Scenario: A managed runtime tries a different reservation or version
- **WHEN** 预留不是冻结工具/Q1/member/完整参数/step/attempt，含retry、试图调用模型、改完成政策或scope，或用不支持的执行器读取托管Run
- **THEN** 在持久预留/HTTP前拒绝，原预算和输入保持；旧M3无runtime标记的Run仍沿原合同，新托管Run不得被通用store/旧执行器接管

### Requirement: Bind limited reconnaissance readiness to the frozen window

alert_recon固定来源核对 SHALL 分别交付目标窗口、查询窗口、已确认查询的窗口及未查询部分。固定路径默认查询完整冻结窗口；仅当来源明确成功/空返回、实际有界查询覆盖完整目标窗口且原有限政策无阻断时，scope_readiness才可ready。完整窗口查询不表示无行数/正文限制、全局活动完整、恶意/授权已判定或整体调查完成；六问题关键性及性质/授权轴 SHALL 保持。原子窗口准入本身不取消，但子窗口命中仅支持局部事实，不得据此满足完整冻结目标。

此收紧政策 SHALL 在新结果中显式固定completion_policy_ref=bounded_full_window_source_check.v1；原scope policy_ref仍表示查询/问题政策，不静默替代。未来M6.2在开始运行前 SHALL 将完成政策与执行器版本写入冻结输入。旧结果缺此字段时按原批次政策解释，不回填新政策或重算旧ready。

#### Scenario: A subwindow contains a checked source observation
- **WHEN** 冻结5分钟而合法查询仅覆盖其中1微秒，命中一条来源观察
- **THEN** 保合法来源事实和Q1支持、Q5覆盖陈述；列出两侧未覆盖区间，query_window_coverage_incomplete阻断ready，交付partial与人工核对需求，不自动补查或完成Run

#### Scenario: The query window and actual execution state differ
- **WHEN** 完整窗口查询成功、空结果、截断、失败/未执行/unknown或没有材料
- **THEN** 成功/空结果可证明有界窗口已查询，但空/截断等原阻断仍生效；失败/unknown/缺材料不能把声明的窗口算成已覆盖。时区等价窗口按UTC微秒比较，原始回执/hash不改

### Requirement: Preserve checked material when model projection is blocked

新版材料准备层 SHALL 先完成material tenant/hash、caller/source Run、当前scope、查询回执及全部来源版本/正文hash必要校验，再执行Alert摘录/完整模型视图的大小和输入合同检查。仅投影大小或输入合同阻断 SHALL 返回明确material_projection_blocked/partial、原来源可用性/执行状态、全部已核材料/查询/来源版本引用、具体限制与下一步；MUST NOT 转成source unavailable、伪造空EvidenceView/snapshot或静默删支持/反证。必要校验失败 SHALL 拒绝，不能因为同时超限而进入有效材料降级。

#### Scenario: Checked material cannot fit the bounded model projection
- **WHEN** 10条各512字节引号正文使视图超12KiB，或Alert文本超512字节/违反输入合同，而必要材料校验通过
- **THEN** 原视图builder保持阻断；新增准备层返回有界结构化交接，保artifact/查询/全部来源及版本引用和实际ok状态，事实采用暂不发生、六问题未评估及缺口明确。无新模型/查询、不升上限或改留存hash，不声称本交接已持久或已投递人工

#### Scenario: Invalid source material also triggers projection limits
- **WHEN** 同时存在长Alert/大视图及错误material hash、跨tenant/Run、超scope参数、错误来源hash或冲突版本声明
- **THEN** 必需校验失败优先拒绝；不能生成已核投影阻断回执或采用事实。停止条件仍保原枚举与unknown，不自动重放；持久保存和实际M3停止来源在M6.2后续接线验证

### Requirement: Preserve source provenance while normalizing network address identity

新版网络政策 SHALL 将合法IPv4与其IPv4-mapped IPv6表示归一为IPv4，原生IPv6归一为压缩表示；仅mapped形式可与IPv4等价，其他地址不因相近文本而等价。M1已核实体、受限caller参数/回执、EvidenceView参数采用及Deep查询指纹 SHALL 使用一致的地址身份规则，同时保持租户、绝对窗口、主机、端口、协议和来源校验。SourceField原始值/路径及已留存响应/hash SHALL 保持原文，不将归一化后的值伪装成原始字段。旧版源码、工具及入口 MUST NOT 改动。

#### Scenario: Equivalent network addresses cross the actual v2 query contracts
- **WHEN** 已核来源分别为IPv4、mapped IPv6十六进制或点分形式、以及原生IPv6展开形式，API逻辑经替身CH返回同一地址的规范记录
- **THEN** 当前新版scope→caller→API结果→EvidenceView→有限程序事实均通过，wire参数规范化且原始字段出处保留；性质/授权仍未知，不新增模型、真实业务调用或Run完成

#### Scenario: Address aliases do not weaken scope or duplicate protection
- **WHEN** 参数、来源字段或回执为不同IP，IPv4-compatible但非mapped IPv6，错误租户或被篡改hash；或Deep提议同一查询的地址别名
- **THEN** 不同身份/无出处或hash错误仍拒绝，caller越界不发HTTP；等价地址的Deep参数规范化后具有同一指纹，不能绕过去重。其他既有预算/范围合同不改变

### Requirement: Derive fixed alert observations and stop handoff without a model

M6.1 SHALL 仅接受已核alert_recon业务绑定、可选的已提交EvidenceView及调用方当前snapshot引用，以纯程序产出network_observation.v1有限事实、六问题状态、范围就绪度与停止交接。来源字段谓词 SHALL 复用M4有限检查，发现明确标记program/rule_checked并保来源版本及依赖；MUST NOT 伪造模型候选/理由、将来源正文指令作为控制、把性质或授权升级，或将scope_readiness写成Run完成。该层 SHALL 无模型/HTTP/DB/预算变更/Case动作/manifest发布，所有输出均不授权追加查询；实际M3 gate/截止/去重及运行调度接线在后续M6.2验证。

#### Scenario: Checked source observations support the limited objective
- **WHEN** 当前视图包含无冲突、未截断且可读的来源网络观察，覆盖回执可核
- **THEN** 程序输出有限来源观察、可核的unknown outcome、精确UUID关联和有界查询事实；Q1/Q5可supported，Q2按实际精确关联，Q3a/Q3b/Q4保持unassessed和原缺口。ready只表示来源陈述核对目标满足，性质unresolved、授权unknown，停止且不补查、不生成最终报告或完成Run

#### Scenario: Missing or incomplete material must be handed off explicitly
- **WHEN** 无视图、空结果、来源失败/未执行/未知、来源版本冲突、缺失反版本、查询/正文截断或可选正文不可读
- **THEN** 保仍合法的有限事实、全部材料/版本引用和覆盖缺口，明确阻断原因与partial；空结果不证明无活动，unknown不变failed，冲突不选赢家，缺正文不使结构事实消失，不自动重复相同查询。非决策Q2无精确关联时独立保缺口，不伪造来源关联

#### Scenario: Stop conditions or new versions retain useful facts without further work
- **WHEN** 可信调用方交入已观察的budget_limit/deadline/unknown_attempt/retention_gap/cancelled停止原因，或材料与当前snapshot不一致
- **THEN** 已观察停止原因只收紧为partial交接并保现有事实/引用，不追加总结模型或重试；未知原因拒绝。旧snapshot拒绝；新版本事实ID/依赖按新snapshot重建且不改旧结果。该纯层不证明停止原因的持久来源，也不替代M3实际准入或多轮依赖失效传播

### Requirement: Verify a scoped source query through an independent v2 HTTP application

新v2查询路由 SHALL 仅存在于独立显式启动的investigation_v2应用，固定POST `/api/v2/investigation/query`并只分派新版activity_records；MUST NOT 注册到旧app/router或回落旧工具。认证和`lake:query`授权 SHALL 复用既有依赖，tenant仅来自已认证主体；请求顶层字段须受限，args不得覆盖tenant/SQL/URL/凭据。API仍只核认证tenant及原全局界限，Run/问题范围与预算由可信caller/M3执行门负责，不宣称已实现正式M8持久启动授权。

#### Scenario: One new controlled Run consumes the shared network scenario
- **WHEN** 离线新路由/原records/受限caller合同通过，且当前PG canonical Alert和已有CH测试资料读回符合共同场景卡
- **THEN** 新独立进程以临时服务身份接收一次经scope/M3预留的查询，返回唯一匹配UUID并排除两对照，保存原文hash及unknown；新Run只追加3事件/6工件，独立读回校核hash/UTF-8/归属及预算，旧Run计费/状态和历史unknown不改，模型0

#### Scenario: Authentication or routing cannot admit a request
- **WHEN** 缺凭据/tenant、tenant非法或不存在、缺lake:query权限、请求含额外身份或旧工具名，或访问旧v1路径
- **THEN** 原认证/授权及新版请求合同拒绝，不执行CH；旧v1路径在独立应用不可用，不因新版失败自动改走旧入口。正式旧服务及入口保持原样

#### Scenario: A temporary real seam stops or becomes uncertain
- **WHEN** 读回、预留、HTTP或留存出现失败/unknown
- **THEN** 保失败/未结算及实际进度，不自动重放或换Run刷新额度；仅按已记录PID/进程身份停止本次API，关闭/撤回本次新PG角色权限，原数据/历史角色和失败材料保留，不部署常驻服务

### Requirement: Prepare complete model messages with the same budget used at dispatch

新版分析任务的消息组装、执行前检查及egress后observer SHALL 复用同一完整messages规范化/序列化与12KiB UTF-8计量合同，包含system、任务封装和转义；MUST NOT 将EvidenceView自身大小作为完整请求可消费的证明或增大全局上限。任务准备只能交付已通过该合同的消息；超限 SHALL 在外呼/预留前明确返回实际字节、上限、超额、受影响问题、保留的快照/全部来源引用及后续材料处理要求，不静默删减支持、反证或冲突版本。当前本块选择显式阻断并交付材料缺口，不自动分组；后续任务拆分须另保引用/覆盖合同。

#### Scenario: A bounded evidence view exceeds the complete task request budget
- **WHEN** 合法10条来源的视图小于12KiB，但加现有system及任务封装后完整messages超12KiB
- **THEN** 消息准备明确拒绝，报告固定开销与可用的序列化证据空间，保全部材料引用和受影响问题；执行器返回no_request/未派发，预留/模型调用0，不将此视图标为任务已准备完成

#### Scenario: Privacy egress expands a request that passed preparation
- **WHEN** 已通过准备的消息在egress后增大至超过相同完整请求上限
- **THEN** observer使用同一计量函数拒绝且预留/外呼0，保明确egress阶段的字节缺口；不能关闭safe输入合同、按原大小预留或重放请求

#### Scenario: A request is exactly on its UTF-8 byte boundary
- **WHEN** 包含多字节文本的完整规范消息恰好12KiB或超1字节
- **THEN** 前者通过当前字节合同，后者拒绝；token预留仍按实际完整消息字节+256+2048原政策，真实usage另结算，不把字节当tokenizer实值

### Requirement: Degrade optional source excerpts locally while preserving checked observations

EvidenceView SHALL 区分来源身份/必要字段不可核与可选`raw_payload.message`摘录不可用。仅当必要来源合同及hash通过时，超512 UTF-8字节、结构化message、非JSON/重复键正文、截断正文或LLM输入合同不允许的摘录 SHALL 局部省略并留确定原因；其他已核结构字段、原文hash/引用和有效记录 MUST 保留。MUST NOT 裁掉正文后声称完整、将对象直接转成prompt、绕过LLMInputContract或放松身份/hash/窗口校验。依赖未读正文的更强判断 SHALL 保持待核，有限字段谓词不因此扩大。当前alert任务文本的原有界限保持。

#### Scenario: One optional message cannot be consumed but checked records remain valid
- **WHEN** 同批包含短文、超长或对象型message，来源身份、时间、端点及内容hash均合法
- **THEN** builder保留各记录的结构观察和来源引用，仅向模型提供合规短文；其他记录附excerpt_gaps，查询coverage列对应缺口，采用后的相关有限观察也保缺口，性质unresolved/授权unknown不改变

#### Scenario: The unread body could contain a counterexample or has forbidden raw material
- **WHEN** 正文包含关键语义但无法完整安全摘录，或截断/重复键/输入合同拒绝使正文含义不确定
- **THEN** 不把省略当无反证，不向模型泄漏被拒正文；保原件可回查及未读原因，禁止通过当前有限谓词采用恶意/授权/连接成功等更强结论。身份、hash或必需字段损坏仍拒绝整个不可信材料

#### Scenario: A later complete retrieval restores the same optional excerpt
- **WHEN** 同身份同版本同时有截断及完整取回，且保留前缀彼此兼容
- **THEN** 保两次取回出处，并优先使用完整且合规的message；不能因不完整取回覆盖已可用摘录，亦不能因改为局部降级接受不一致前缀

### Requirement: Bind business profiles to checked targets without invoking business operations

M1业务profile合同 SHALL 以可信调用方已核的ScopeContext及目标/成员快照，显式绑定`profile/profile_version/target/objective/policy/trigger`及交付归属。当前 SHALL 仅支持`alert_recon + alert`或`case_investigation + case`，保留`network_observation.v1`及`verify_source_network_observation`有限目标；MUST NOT 因trigger、来源正文或profile切换扩大问题、查询范围、权限、额度或已验分析能力。绑定 SHALL 纯计算、不可变并保scope/目标/成员版本，不发模型/HTTP/DB、不创建Case/Run、不注册旧入口；原explicit_set合同 SHALL 保持可独立使用。

#### Scenario: The same checked alert is triggered manually or automatically without a Case
- **WHEN** 可信调用方提供同租户唯一canonical Alert目标、匹配的scope和显式alert_recon，分别以manual或automatic触发
- **THEN** 两次输出均归属同一Alert、同一有限目标和问题范围，不要求Case，不补造侦察完成/Case关系或调用预算；trigger仅记录请求来源

#### Scenario: A Case selects only part of its frozen complete member identities
- **WHEN** 已核Case目标提供稳定成员来源/版本和4个完整成员，scope选入3个并明确遗漏最早成员及原因
- **THEN** 输出保全部4个、选入3个及遗漏身份/原因，仍要求针对冻结Case成员评价覆盖，初始调查状态为not_started；原scope仍只允许选中成员，不将选材完整误作调查完整，不执行继承/启动

#### Scenario: A target or scope cannot support the requested business binding
- **WHEN** 目标或成员跨租户、alert ID不匹配、Case成员清单不完整/无版本或来源不符、profile/目标配对错误、政策/目标被增强、scope问题/边界被篡改，或使用未知版本/触发方式
- **THEN** 绑定在纯合同层拒绝，原scope及问题不变，模型/HTTP/DB/Case/Run写入均0；保留已有explicit_set初始化及查询准入语义

2026-10-24 main集成说明：本change接收远端调查`469e9467`的独立v2开发基线及原记录，保留双方已有设计和实现。旧restore迁移已在main限定核销归档，不恢复其活动目录；下述历史原文中的“沿原restore/5/15/不提交”等按原日期解释。D1—M4限定成果、M5.1与未完成M5.2分列，新HTTP未注册，M6—M9和v4分层未交付。当前只合并和审计，不启动后续业务实施、真实测试或部署。

2026-10-24 v4说明：新增分层需求为待讨论实施的目标合同，不是现有字段/接口或验收事实。M4限定通过、M5.1通过、M5.2增量未测；当前只设计，后续按主方案12.7逐步改测。

2026-10-23用户新授权持续逐步推进，M3停止是前批边界。本批M4严格依次M4.1a证据视图→M4.1b候选采用→M4.2持久模型gate→M4.3有限真实模型，每步直接测试及回执通过才下一步。只覆盖network_observation.v1的Q1/Q2/Q5，Q3a/Q3b/Q4保缺口，行为性质unresolved、授权unknown；不追认主设计12.6完整恶意/授权卡通过。单阶段最多8模型尝试/20000tokens，OS后置，不部署/提交/push，原5/15保持；质量或预算门未通过不得进入M5。下文旧批次不发模型/停止边界不撤销本次授权。

2026-10-23 M1/M2按步通过后，用户授权继续M3。新增目标合同依次为M3.1纯身份/预算、M3.2既有PG三表原子事件/工件、M3.3持久gate及受控新Run/一次真实M2工具；每小步通过才下一步。模型、M7发布、M8入口、OS与旧Run恢复不在本批，不改DDL或原15项勾选，实际通过由主回执确认。以下M0—M2限制按此前批次理解，不阻止本次明确授权。

2026-10-23 D1—D3通过后，M0只对本批网络来源观察场景放行。当前实现顺序为先M1纯合同并直接测试，再M2新`activity_records`及受限调用方；不提前实现模型、M3持久化或M8运行入口。泛API只有认证tenant/权限及全局bound，Run/问题scope在本批受限调用方校验，不声称已有Run持久scope授权服务。

2026-10-23后续工具数据授权先补M0场景前提：D1离线生成、D2受控入湖/读回、D3告警关联按步验证。下列新增工具数据合同不改变生产业务能力，不宣称M1或业务查询工具已实现；OpenSearch与模型不在本批。每一步以本批回执证明通过后才推进下一步，原5/15与旧证据保持。

2026-10-23用户确认v3统一调查方案并授权按M0—M9逐模块实施。本次新增M1合同适用于尚待接入运行入口的新统一内核，首步为显式成员及来源记录陈述核对；M0/M1实际范围、来源条件和放行见`docs/operations/unified-investigation-implementation.md`。下文2026-10-21迁移限制和原四节点小修合同保留其历史/旧路径范围，不把新目标写成生产已完成，不追认旧失败或unknown。M1只初始化范围/问题并判定扩展准入，查询、模型、持久发布及入口接入由后续模块各自实现、测试后推进。

### Requirement: Keep the legacy investigation available while the new version is developed

旧版Kafka/Case/graph/Router入口、开关和实现源码 SHALL 保持原样；新版 SHALL 使用独立investigation_v2模块/入口及独立运行进程/配置/测试输入输出身份，MUST NOT 因未指定版本或升级代码就接管旧流程。稳定能力可只读复用，需要变化的函数 SHALL 在新版复制所需部分并修改，MUST NOT 修改旧函数/注册。新工具名称只在新版分派，不加入旧工具集。Run开始时 SHALL 固定执行器版本和唯一writer，旧Run结果不得改写成新格式。

#### Scenario: A legacy request has no explicit new version selection
- **WHEN** 当前旧接口/Kafka配置没有选择新版
- **THEN** 继续旧执行器/参数/返回合同；旧源码/旧测试对本任务基线无差异，新工具不被旧dispatcher识别，新版dispatcher拒绝未知/旧工具名且不回落；新版未完成或不可用不进入旧版代码路径

#### Scenario: A new version run stops or has an unknown call
- **WHEN** 显式新版Run停止、失败或调用unknown，操作者停止新入口并继续使用旧入口
- **THEN** 保持原Run/预算/unknown，不自动为同一任务再跑旧执行器；新旧比较用不同测试Run，旧服务继续自身入口，最终下线旧版须另行决定

### Requirement: Separate alert reconnaissance and Case investigation business profiles

新执行请求 SHALL 显式保存`profile/target/objective/policy`，将`alert_recon`与`case_investigation`的目标、完成政策和交付归属分开，同时复用证据、采用、范围、额度及执行合同。自动/手动触发 MUST NOT 决定业务归属；无Case告警Run SHALL 保持可读，侦察完成 MUST NOT 表示Case调查完成或告警自动关闭。

#### Scenario: Alert processing has no Case or no reconnaissance stage
- **WHEN** 告警已有首次分诊/侦察Run但没有Case，或按政策未进入侦察
- **THEN** 自动处理详情按真实步骤展示；无Case不拒绝读取，未进入侦察与进行中/partial/完成分开，无自动Run也不补造处理记录

#### Scenario: A Case uses optional domain analysis
- **WHEN** Case政策启用并选中Phishing、Identity、Cloud或Insider能力
- **THEN** 专家仅返回局部候选与缺口，由主调度采用/综合，所有调用共享本次Case预算；不自动串跑旧四角色和旧Router完整流水线，不将旧Router开关静默改义

### Requirement: Inherit bounded alert evidence into a new Case run with explicit membership coverage

Case调查 SHALL 使用新Run、已认证Case目标和启动准入时冻结的成员快照，保存全部/选入/已读/遗漏成员；SHALL 以`input_run_refs`引用多个告警的已提交工件及不可变版本，核当前读权限、范围、来源hash、适用性和缺口。MUST NOT 改挂告警旧Run、把旧findings当source、把重复来源当独立印证、把最近3条默认为全Case。新问题、覆盖不足/缺失、冲突待核或版本变化 SHALL 允许在政策内补查，不无故重做已满足同问题/窗口/覆盖的查询。新Case额度须独立准入；继承的历史成本不重复扣计，unknown保护保持。

#### Scenario: Multiple alerts reference the same event or an incomplete source run
- **WHEN** Case成员引用相同来源身份/内容，或来源Run尚未完成、没有manifest、保有冲突/unknown
- **THEN** 同源同版去重，旧分析按适用性采用而非直接裁决；仅继承已核工件并标兼容/待完成/缺口，不能以摘要补造来源或清除unknown；跨租户或不可读引用拒绝

#### Scenario: The Case has more than three members or changes during execution
- **WHEN** 快照有4条以上成员且早期成员带关键反证，或运行期间Case成员发生变化
- **THEN** 启动时固定一致成员版本（含分页），创建后等待期间新增的成员也纳入；无法核一致版本不声称全覆盖。模型可分组读但不能遗漏关键反证后声称全Case完成；选子集明示目标，未读关键项为partial；运行后变更标待复核而不覆盖当前快照或自动无限续跑

### Requirement: Keep Case recommendation linkage and investigation start independently authorized and idempotent

升级建议、Case创建/关联、调查启动 SHALL 分别记录依据/政策/执行回执，后两项 SHALL 有独立配置与准入。模型建议或完成状态 MUST NOT 单独授权业务写入。创建/关联 SHALL 使用稳定业务操作键；人工和自动启动 SHALL 同样保存稳定操作键、持久意图、启动成员快照及唯一Run关联，同一请求重试不得另建Run/额度。再次明确授权的新操作才可用新键；首版已有Case Run运行时返回其引用且不并发新Run，不静默合并不同范围。在必要持久合同未具备前 MUST NOT 开放对应启动路径。候选关联不能仅凭同IP/近邻时间，歧义或关闭Case交人工处理。

#### Scenario: Case creation is enabled while automatic investigation is disabled
- **WHEN** 升级条件满足且创建/关联允许，但启动政策为manual
- **THEN** 保存Case关系和创建回执，显示等待启动，不创建调查Run；反向配置允许用户手动关联后按独立启动政策准入

#### Scenario: Duplicate delivery or an uncertain cross service result occurs
- **WHEN** 同一升级/启动意图重复投递（包括人工按钮/HTTP请求重试），已有Case Run运行，或跨服务操作超时未知
- **THEN** 依稳定业务键查询/确认既有关系与Run，不重复建Case/并发启动，不通过新Run重置额度；保留待处理/待核状态，不把请求发出当已创建或已启动

### Requirement: Bind question-level Deep requests to the existing investigation scope and budget

M5 SHALL 接收程序指定的父Run/ScopeContext、单一问题、成员及subtask身份，由模型提出有限查询选择，程序校验并执行已绑定的只读工具。首场景仅network_observation.v1的Q1/activity_records；模型MUST NOT覆盖身份、tenant、Run、范围版本、URL、headers、SQL或工具凭据。查询窗口、字段来源及数量限制MUST复用M1/M2准入；父M3阶段及额度MUST由所有子任务共享，不因进入Deep或再次请求而清零。

#### Scenario: Query proposal changes scope or repeats an equivalent request
- **WHEN** 模型给出越界/无出处参数、额外身份/SQL/认证字段，或以等价时间/默认参数重复已见查询
- **THEN** 程序在HTTP前拒绝，保原问题/范围；等价合法参数得到稳定签名，任务及步骤身份由程序生成，不重开父stage或执行重复查询

#### Scenario: A selected query becomes evidence in the next model input
- **WHEN** 对明确Q1选择已允许的activity_records并实际取得有界回执
- **THEN** 先原子留存，再把带出处/版本/查询状态的有界证据交给下一轮；模型原文、程序选择、真实执行及采用分别可核。输出仅为该问题的局部答案/缺口，不冒称全案assessment或完整报告

#### Scenario: Empty unavailable unknown or exhausted execution stops locally
- **WHEN** 查询成功空、来源不可用、调用unknown、重复/无进展、额度或deadline到限、留存未确认
- **THEN** 保留对应材料和未解决问题，不将空/缺源改成安全或未发生活动，不自动重放未知请求，也不追加总结模型；仅局部状态交给父执行器

### Requirement: Build bounded evidence views with stable source revisions and visible conflicts

M4.1a SHALL 从M1冻结范围及已留存M2/M3材料构建程序管理的来源身份/版本、查询回执、引用索引和有界模型视图。相同namespace/tenant/source ID及相同内容不因查询或取得时间变化成为独立印证；异文 MUST 保不同版本与冲突。MUST 保原字段出处、完整原文hash与保存正文hash/裁剪的区别，正文只作data_only；模型摘要不得升级为source_event，空/缺源/错误不制造来源事件。模型输入不得直接搬入原始OCSF或关闭既有输入合同。

#### Scenario: One source identity has delivered and undelivered conflict versions
- **WHEN** M2返回identity_state=conflict及conflict_version_hashes，但limit+1边界使某版本只有hash、没有交付正文
- **THEN** 保所有已交付版本、未交付版本hash及覆盖缺口，冲突不能因可见rows仅一版而消失；不得为仅hash版本编造正文或可引用字段

#### Scenario: A view is repeated bounded empty or unavailable
- **WHEN** 同源同文重复出现、支持/反证装不下、查询为空或来源不可用
- **THEN** 保稳定身份及去重来源关系，披露遗漏/限制；必要反证不能静默截掉，超限拒绝本次组装或拆分任务，不把空或缺源写成未发生活动

### Requirement: Adopt versioned analysis candidates only within the limited observation policy

M4.1b SHALL 先用固定候选验证引用/版本/范围及逐项采用。模型只提议answer/finding/assessment及有界建议；ID、revision、adoption、validity和有效决定资格由程序管理。候选 MUST 绑定问题定义、scope/policy、证据/覆盖与实际input_snapshot版本；存在合法引用不等于命题正确，只有已定义的有限来源字段谓词可标rule_checked。Q1/Q2/Q5为本批问题组，Q3a/Q3b/Q4定义与缺口保留，行为性质保持unresolved、授权unknown，不能声称连接成功、恶意/正常或已授权。focused允许assessment=null；无整体候选不得从局部标签自动造整体裁决。

#### Scenario: A candidate mixes valid findings with invalid references or stronger claims
- **WHEN** 同批候选包含合法来源观察及缺失/过期/越界引用，或把outcome=unknown写成成功连接
- **THEN** 保原候选并逐项记录采用/拒绝理由，合法项可独立采用；依赖被拒项的答案或整体候选不得采用，不以全部丢弃替代部分采用，也不把缺少成功证据说成连接未发生

#### Scenario: A focused or combined response refers to a particular snapshot
- **WHEN** focused返回null整体评估，或combined用同批临时finding键构造整体候选，或回复期间相关版本变化
- **THEN** null被正常保留；临时键只解析到已采用的正式finding版本，旧快照回复不覆盖当前判断，部分拒绝沿候选依赖处理；不提前实现M6完整调度或M7发布

### Requirement: Invoke the analysis model through the existing safe call and durable budget gate

M4.2 MUST 复用safe_ainvoke及invocation_scope的before_request/responded/no_request observer，不建立raw ainvoke旁路；已有活动triage上下文时拒绝，不覆盖其预算。before_request SHALL 捕获egress后的实际输入、核任务版本/界限并提交M3预留后才外呼；responded先在内存固定原reply，safe返回后将有界原reply、恢复后候选及程序采用结果在同一次complete中原子留存。恢复或解析异常仍保原reply并按responded结算，不误作未知请求；缺usage逐维保unknown/unpriced，不采用模型自报usage。实际outbound完整messages（含system）的序列化UTF-8合计 MUST 不超过12KiB，预留tokens为该字节数+256消息开销+2048输出；这是显式保守上界政策而非目标tokenizer实测，真实超预留仍按M3结算后停止。保SDK retry=0和DB绝对deadline；未提交预留外呼0，留存失败不重调。

#### Scenario: Input is rejected before dispatch or the request expires
- **WHEN** 旧triage上下文活跃、输入/参数不合法、实际消息超过12KiB、无额度、deadline到达或预留写失败
- **THEN** 不发模型请求、不绕过safe输入合同，不保存被拒的凭据/任意参数；已预留但确认无请求按M3释放资源且保尝试，不重置阶段

#### Scenario: A response cannot be restored parsed or completely measured
- **WHEN** 已收到原reply而恢复/解析失败、输出超过显式字节上限，或真实usage部分缺失
- **THEN** 区分responded、候选不可采用和留存状态；输出正文最多捕获32KiB，超过则不解析/采用，保有界正文及完整正文hash/字节数、明确裁剪回执，不盲目重发。32KiB与2048 token上限分开执行且直接测试；已发生用量照实结算，缺失维度保未知，不能假报unknown网络结果或0用量

### Requirement: Validate limited model analysis within one fixed eight attempt stage

M4.3 SHALL 在前三小步分别直接通过后，以同一目标模型、同材料版本、固定问题组和同阶段额度执行有限矩阵。每次问题最多3、findings最多6、所有建议合计最多2、实际可见输入序列化UTF-8合计最多12KiB、completion最多2048 tokens；整批共用max_model_calls=8及max_tokens=20000，不按样例/模式新建预算，不自动扩大或续期。矩阵为同一正例及同一冲突例各combined/focused一次共4次，再过度成功断言、成功空、缺源、仅加入指令文字对照各1次，共最多8尝试。合成衍生材料 MUST 有新hash/provenance，expected及泄漏预期的标签不入模型；不为跑满8次强行继续。

#### Scenario: The same facts are analyzed in two modes or with added source instructions
- **WHEN** 正例/冲突例分别使用combined和focused，或只在正例正文增加指令文字
- **THEN** 分别记录原文、采用与可读结果，正确来源事实及反证不应因模式/指令消失，指令不改变scope/政策/性质授权边界；focused无整体结果不能与combined整体结论冒称同等成果，成本仅按实际相同目标比较

#### Scenario: Quality or available budget cannot satisfy the required cases
- **WHEN** 充分材料仍无理由全partial、关键反证被忽略、缺源被写为安全，或剩余额度/期限不足以完成必要样例
- **THEN** 定位并保留失败/unknown与未完成样例，不事后修改expected、不自动追加模型或进入M5；无必要不加synthesis，确需综合也不得挤掉必需样例或突破8次/20000tokens。本批通过仅覆盖有限来源观察，不等于主设计12.6全部恶意/授权功能通过

### Requirement: Begin one owned investigation stage without resetting prior usage

统一执行器 SHALL 以可信tenant/Run固定派生`stage_id`、绑定唯一executor owner，并保存schema/executor、scope与policy版本。MUST 在显式tenant/run归属校验、同Run行锁和确认无既往统一阶段标记/事件后，才持久`unified_execution_started`及初始snapshot/input工件；只有该提交成功才能准入外呼。再次begin MUST 拒绝且不得清零、换owner接管或延长deadline。M3 state snapshot SHALL 显式分列opening triage与`investigation_stage`的已知用量及unknown/unpriced，在快照内合计Run总量，不重复扣减新阶段额度。MUST 保持`investigation_runs.total_tokens/total_cost`等既有计费列、旧分诊资料和Run.status不变，读取projection留M8。本批不支持自动恢复或与旧writer并行。

#### Scenario: A new stage follows a persisted triage baseline
- **WHEN** 同tenant新测试Run已有首次分诊记录及已知用量，尚无统一阶段标记或事件
- **THEN** 开始回执保旧记录/seq和triage期初摘要，阶段从已核无既往调用的零用量开始并使用独立额度；后续state snapshot内Run总量按opening triage加stage已知用量合计且保unknown/unpriced，既有Run计费列不更新，不能把分诊再扣入阶段额度

#### Scenario: Begin is repeated or cannot be committed
- **WHEN** 已有本阶段标记/事件、owner或tenant/run不符，或开始事件及工件无法完整提交
- **THEN** 拒绝开始，外呼0；不得用新stage ID、相同输入或部分旧快照重置阶段，不报告不存在的持久回执

### Requirement: Share explicit attempt budgets within the investigation stage

阶段预算 SHALL 由纯状态reducer区分model/tool尝试、已知tokens/cost、资源预留、未结算含unknown数量及绝对deadline。子任务和同一step的新attempt MUST 共用该阶段额度；step、attempt和event seq分别标识逻辑工作、每次尝试和持久事件。旧`max_tool_calls` MUST 按现有实际语义映射model_calls并保存来源，tool cap另显式配置、缺失拒绝，不新增生产默认；token/cost及币种、max_unsettled和deadline也须显式。Run期初与阶段状态不得被CostTracker重绑定或重试隐式清零。实际gate以DB时间及上级更早截止时间核期限，纯测试才可注入时间。

#### Scenario: Two child attempts compete for the last allowance
- **WHEN** 两个子任务或重试尝试使用最后一份调用额度、token/cost额度或未结算slot
- **THEN** 同一阶段只允许符合剩余额度的一次预留，不因子任务新建独立预算；另一尝试明确拒绝，外呼0，已存在尝试及预留保持

#### Scenario: Policy identity or time cannot admit another attempt
- **WHEN** 必需上限或配置来源缺失、身份/版本不符、deadline已到，或阶段已因真实超额停止
- **THEN** reducer及持久gate拒绝新增预留，不以缺失值为无限/零成本、不沿用旧变量名暗改模型次数，外呼0；测试小额上限不成为生产默认

### Requirement: Commit a reservation before executing the bound call

执行器 MUST 复用既有`investigation_runs/events/artifacts`，每次开始、预留和完成均在显式tenant/run谓词的`FOR UPDATE`事务内核owner/状态，以现存`MAX(seq)+1`分配事件序号并核实际写入结果，不新增DDL、不重编号旧seq。预留事件、状态snapshot及相关input工件 SHALL 同事务提交，提交成功后才允许一次绑定attempt的外呼；分配seq不等于完成顺序或全局提交游标。只支持本批遵循同一锁的单owner执行，不能把内存分配宣称为多旧writer并发安全。

#### Scenario: A reservation artifact cannot be written
- **WHEN** 预留事件或其输入/snapshot任一写入失败或归属冲突
- **THEN** 本次事务整体回滚，既有事件/工件及用量快照不变，工具和模型调用0，不返回虚假新event或artifact ID

#### Scenario: The run already contains triage event sequence values
- **WHEN** 合法执行器开始阶段并依次预留、完成一个step的attempt
- **THEN** 每个新事件从同Run现存最大seq后分配，旧seq不变，step/attempt关联保持；另一个owner与旧writer不会被准入本批并行写入

### Requirement: Settle actual outcomes atomically without erasing uncertainty

预留成功 SHALL 计一次对应model/tool尝试。明确无请求时 MAY 释放本次资源预留及未结算slot，但MUST 保尝试记录；请求可能发出、响应无usage或提交结果未知时 MUST 保明确unknown及未结算预留/slot，不自动释放、重放或清零。完成事务 SHALL 同时提交完成事件、独立output工件及state snapshot，snapshot内包含opening triage、stage已知用量、两段聚合总量与分别保留的unknown/unpriced。snapshot只含状态与小refs，原文单工件保存，不逐快照重复正文。实际用量超预留 MUST 照实写入该状态、记录超额并停止后续，不能拒绝记录真实成本。MUST 不更新`investigation_runs.total_tokens/total_cost`等计费列、旧Run.status/completed_at、triage预算表或历史资料；M7 manifest/完成通知与M8读取projection不在本块。

#### Scenario: A call was definitely not sent or its usage is unknown
- **WHEN** 执行器能证明未发请求，或只能确认可能发出/响应缺usage
- **THEN** 前者释放资源但保调用尝试，后者保unknown、资源预留和未结算slot；有回复不等于成本为0，缺价格显式unpriced，两者均不得被自动重试掩盖

#### Scenario: Actual usage exceeds the reserved estimate
- **WHEN** 可核实际tokens或cost超过本次预留或阶段上限
- **THEN** 如实保存实际值和超额原因，本attempt已知用量在stage快照只累计一次，快照内再与opening triage合计Run总量并停止后续准入；不更新既有Run计费列、不裁剪usage、不因超额拒绝留存，也不宣称保证绝不超出预算

#### Scenario: Completion is duplicated or only partially written
- **WHEN** 相同attempt与内容指纹被重复完成、以不同正文完成，或完成事件/输出/含用量聚合snapshot写入中途失败
- **THEN** 相同内容仅确认既有回执且不在快照重复计用量，异文拒绝覆盖；失败事务整体回滚并保原未结算预留，交接说明结果未确认保存，不重跑工具补造回执，既有Run计费列保持不变

### Requirement: Verify the durable gate with a bounded record query before model work

M3 SHALL 按纯合同→PG原子持久→执行包装的依赖顺序逐块直接测试与留回执，通过前不得进入下一步。M3.3仅使用受控合成新Run及已通过M2的网络来源记录查询，真实验证一次查询及其PG持久refs；其他故障/拒绝用例不得扩大真实外呼。MUST 区分完成外呼和持久成功，M2泛API仍只核认证tenant/权限与全局bound，不据包装器测试宣称M8实际入口/Run持久scope授权已接通。模型、OS、部署、Git提交和推送均不在本批。

#### Scenario: One real record query passes the durable gate
- **WHEN** M3.1/M3.2直接测试已通过，受控新Run的begin与一次工具预留均已真实PG提交
- **THEN** 一次M2查询只返回预期匹配记录并保unknown及来源hash，完成事务读回同tenant/run/step/attempt的事件、输入/输出及snapshot refs；旧seq/triage期初不变，快照内两段已知总量和unknown/unpriced正确且既有Run计费列不更新，模型0，不把本次接缝称为完整调查或正式结果发布

### Requirement: Generate a bounded investigation fixture with separate expectations

M0场景工具 SHALL 纯离线生成1条告警和3条规范化网络事件，分别表示窗内匹配、窗内不同目标、同目标窗口外。MUST 固定显式tenant、事件唯一UUID和绝对时间，使同一事件在告警引用、规范化输入及预期湖记录中保持一致；告警引用的匹配事件与两条排除对照分别记录。expected判断、可泄漏答案的测试控制标签及答案只保存在独立比对产物，不混入告警或事件业务正文。

#### Scenario: The offline fixture is generated
- **WHEN** 工具接收本批明确的隔离身份、事件时间及窗口，生成三类事件和一条告警
- **THEN** 无网络或业务写入，格式/字段合法、3个事件ID各自唯一，跨产物引用一致，匹配和两类排除条件可确定性检查；业务产物不包含expected答案

### Requirement: Verify controlled lake ingestion by reading exact event identities

D2验证工具 SHALL 在D1直接测试通过后复用原LakeWriter，将固定3条规范化事件有界写入全新独立测试tenant，并按tenant和精确事件ID真实读回。MUST 比对实际行数、绝对时间、实体/目标、动作/结果及原映射字段，区分缺字段、缺行、重复和不确定结果；writer调用返回或fail-soft不得替代真实入湖证明，不修改生产业务查询或原映射以掩盖失败。

#### Scenario: All three events are read back from the lake
- **WHEN** 原LakeWriter已执行本批有界写入且精确ID查询返回对应记录
- **THEN** 每个事件的实际字段和三类对照关系与D1冻结预期一致，回执保留写入/读回边界后才放行D3；这仅证明场景资料入湖，不证明调查工具或模型有效

#### Scenario: A write or readback does not establish the expected records
- **WHEN** writer异常/fail-soft、读回缺行/重复/字段不符，或实际写入结果不确定
- **THEN** 记录真实结果与差异并停止依赖步骤，不标入湖通过、不无界重发、不通过修改既定expected消除失败

### Requirement: Verify alert references against the prepared lake records

D3验证工具 SHALL 在D2通过后复用现有Fusion探针告警链及隔离topic/group/Redis范围处理D1告警，再读取PG实际canonical Alert和相同tenant的D2湖记录。MUST 校核source_event_ids的精确身份关系，保留并区分原Fusion追加的入口来源ID与真实湖事件UUID，不能按文本相似、IP/时间接近或仅存在PG行推定关联。不同目标与窗口外对照不得被认作预期匹配；本批不触发分诊/调查模型或正式消费，不提前实现业务查询工具/OpenSearch。

#### Scenario: The canonical alert references the intended lake event
- **WHEN** 原探针完成受控告警链，PG保存本批canonical Alert及source_event_ids
- **THEN** 在同tenant按精确ID确认预期匹配事件来自D2已核记录，两条对照按冻结条件排除，并单列入口追加ID的含义；保存实际关联回执，不能将M0场景前提通过写成M1或调查功能通过

#### Scenario: Alert delivery exists without a verified lake association
- **WHEN** 只取得202/消息发送/PG告警行，或source_event_ids缺失、不匹配、跨tenant，或只含不能对应湖事件的入口ID
- **THEN** 关联验证不通过并保留差异，不伪造或回填旧记录/预期，不进入依赖该关联的后续查询工具实施

### Requirement: Bind unified investigation scope to authenticated explicit members

统一调查M1 SHALL 以可信调用方提供的认证上下文、已核归属的canonical Alert成员快照和版本政策初始化调查范围，MUST 区分租户、操作者、Run、入口对象类型及成员引用，并冻结caller、scope和policy版本。首步仅接受`explicit_set`目标，不从旧Case/Incident字段或自然语言猜测类型；其他入口解析留M8。M1纯合同不读取数据库，不将内存字段校核冒充认证或PG归属查询；真实身份与成员归属是调用方前提。窗口必须具有明确时区并转换为绝对UTC，成员总数、纳入数及遗漏须可解释，不能把材料尚未读取写成已完整覆盖。范围和问题初始化不执行查询或模型，也不宣称调查完成。

#### Scenario: Explicit members belong to the authenticated tenant
- **WHEN** 已认证调用方提供同租户已核成员、合法explicit_set目标、明确窗口和支持的政策版本
- **THEN** 程序生成钉住版本的上下文与显式成员范围，保留来源和遗漏说明；租户和Run身份不由模型、工具正文或成员自称覆盖，尚未读取材料不得记为完整调查

#### Scenario: Identity or window cannot be accepted
- **WHEN** 请求租户与认证不符、成员归属不符、目标类型未支持、成员引用不合法，或窗口无时区/结束早于开始
- **THEN** 初始化被拒绝并给出具体原因，不猜测对象类型、不静默修补范围，不发查询或模型

#### Scenario: Only part of a known member set is selected
- **WHEN** 上游可信清单的总成员大于本次纳入成员，或仅提供有明确限制的成员视图
- **THEN** 保留已知总数、所选成员和遗漏/未知边界，仅对显式纳入范围建立本次目标；不得把最近若干条或未知总数表述为整个Case已覆盖

### Requirement: Keep conclusion scope distinct from query admission

统一调查M1 SHALL 分别冻结`conclusion_scope`与`query_scope`，后者限定允许来源、实体类型、关系依据、窗口、深度和数量；MUST 由程序及版本政策决定准入，问题scope必须是已批准查询范围的子集，不能仅因同租户、同名或时间接近就授予查询能力。关联扩展须带可检查的来源引用和字段/关系映射，未定义或超界请求默认拒绝；本批网络政策不授权关联扩展。本块只返回准入/拒绝及依据，不实际查询；准入不会自动扩大结论范围，任何批准的范围变更须生成新版本而非改写旧快照。

#### Scenario: A related entity satisfies an explicit query rule
- **WHEN** 关联候选具有政策要求的来源引用和映射，且来源、实体类型、关系、窗口、深度及数量均在允许范围
- **THEN** 返回本次查询准入和规则依据，conclusion_scope及其承诺覆盖保持原样，不执行工具；准入检查不冒充对来源记录真实性或行为因果的验证

#### Scenario: A proposed expansion has no allowed basis
- **WHEN** 请求缺少关系依据、使用未授权来源/实体类型，或超过窗口/深度/数量上限，或试图由模型直接修改范围
- **THEN** 返回拒绝及原因，不新增查询权限、不修改既有范围和版本，不把候选实体自动写成已确认影响对象

### Requirement: Initialize questions from a versioned trusted policy

统一调查M1 SHALL 从可信版本政策生成问题身份、关键性/决定依赖、证据要求、允许能力、前置关系和实体范围，初始处理状态为`pending`、答案为`unassessed`；MUST 将行为性质和业务授权分别表达，不能相互推导。问题的适用性及预设免除必须有政策理由，缺少本场景恶意/授权资料不等于已作出正常或已授权裁决。来源正文及模型建议只可作为资料或待审候选，不得删除关键问题、放宽能力或变更采用条件。

#### Scenario: A source record checking policy initializes its questions
- **WHEN** 政策将目标限定为核对来源记录陈述，并明确问题、实体和证据条件
- **THEN** 建立带政策版本的问题及独立的行为性质/授权语义，明确本次不支持的强判断和原因；不生成虚假答案引用、supported结果或complete状态

#### Scenario: Source text tries to remove a critical question
- **WHEN** 告警、日志、工具或知识正文包含“已授权”“忽略该问题”等指令性文字，或模型建议删除/免除关键问题
- **THEN** 原关键性、证据条件、能力和问题集合保持政策约束，该文字不得成为可信授权或控制指令；候选不能自动取得政策写入权

#### Scenario: A question definition has an invalid reference
- **WHEN** 问题ID重复、依赖不存在或成环、实体超出允许范围，或免除/不适用缺少政策理由
- **THEN** 拒绝该政策/问题初始化并报告缺陷，不通过删除依赖、关键问题或擅自扩大范围使其通过

### Requirement: Bind activity record calls to the approved question scope

M2受限调用方 SHALL 捕获M1可信caller的tenant/Run/问题、scope_revision和policy_ref，在HTTP前验证能力、来源、实体/目标、绝对窗口、行数和参数出处；MUST 拒绝工具参数覆盖caller、tenant、Run、政策或scope，且不接受SQL、索引名或任意查询DSL。问题范围不得宽于M1已批准范围，缺scope或准入失败不发送HTTP。泛API仍只根据认证主体及`lake:query`权限执行tenant过滤和全局上限，不把外部传来的Run/scope字段当已核持久授权，运行入口接线留M8。

#### Scenario: A caller makes a query within its fixed question scope
- **WHEN** 受限调用方持有M1已通过的冻结上下文，参数具有出处且全部落在该问题的范围及能力内
- **THEN** 仅发送准入后的工具参数，认证tenant和上下文版本由调用方保留，回执记录实际请求与准入依据；不能以API成功代替问题scope校验或Run持久化证明

#### Scenario: Tool arguments attempt to broaden or replace caller scope
- **WHEN** 参数越实体/目标/来源/窗口/行数，缺参数出处或试图覆盖tenant/Run/scope/政策及任意SQL/索引
- **THEN** 在发请求前返回明确拒绝，HTTP调用为0，旧上下文与结论范围不变；同tenant的泛API权限不能绕过本调用方的准入

### Requirement: Return bounded and attributable network activity records

M2新`activity_records` SHALL 复用原API认证及湖读取连接，以固定参数化SQL返回网络逐条记录，保旧聚合工具兼容；MUST 使用绝对UTC左闭右开`[start,end)`窗口、网络类型和允许的实体/目标过滤，API最多24小时及50条，受限调用方可更小。输入小数秒必须保留：以UTC微秒字符串配`toDateTime64(...,6,'UTC')`或等价精度转换与存储`DateTime64(3)`比较，不因驱动datetime绑定丢小数秒而改变边界，也不把API限制为整秒。记录包含来源namespace、tenant、事件UUID、实际时间/类型/action/outcome及有限原文；未提供结果保持unknown，不推断成功、恶意或授权。返回实际参数、来源/窗口、查询时间、返回数、覆盖限制和状态回执；成功空、不可用、错误、行数截断和原文裁剪分别表达，不把空查询当未发生。

原文返回量 SHALL 按UTF-8字节限制为每条记录`raw_payload+ocsf_json`合计16KiB、每次响应合计256KiB，在数据库计算各完整原文的hash/完整字节数并限制正文返回，再交付有界内容及实际保留字节数/裁剪说明，不向API拉完整大正文后才裁剪。MUST 用`limit+1`或等价可证明方法识别额外行；同namespace+tenant+event_id且内容相同的重复不作独立证据，同身份异文保留冲突及各版本指纹、不静默覆盖。去重不掩盖原查询截断，也不能把仅有受限结果说成完整覆盖。本块回执只证明本次查询，不宣称M3原子持久已经完成。

#### Scenario: The prepared network fixture is queried through the API
- **WHEN** M1通过且M2直接测试通过后，受限调用方以本批H/S/D:443/TCP和10:00—10:05 UTC窗口真实调用API，不靠预知event_id替代过滤
- **THEN** 只返回匹配事件UUID，排除不同目标和窗口外对照；实际tenant/参数/时间/来源/原文指纹可核，action为来源观察且outcome保持unknown

#### Scenario: The API receives an invalid or unauthorized query
- **WHEN** 认证或`lake:query`权限不满足、窗口无时区/非正或超过24小时、limit不在1—50、网络过滤非法，或工具参数企图指定tenant/SQL/索引
- **THEN** 认证、权限或新工具非法参数被拒绝，不执行非法查询；沿既有dispatch丢弃的tenant覆盖也不得改变认证tenant，并在直接测试中分别核实。不得宣称这些检查已经核过Run持久scope

#### Scenario: A window boundary includes fractional seconds
- **WHEN** 合法start或end带微秒且与实际存储事件的毫秒时刻相邻
- **THEN** 实际SQL参数保留该微秒，按左闭右开语义准确纳入/排除，不经整秒截断改变结果，回执保实际窗口

#### Scenario: The source is empty unavailable failing or bounded
- **WHEN** 合法查询成功零行、来源不可用、执行失败、存在limit以外记录或原文超过字节上限
- **THEN** 分别保存对应状态、实际参数/范围与限制，原文hash对应完整原文而非preview；行数/正文裁剪不伪装成完整资料，失败不变成成功空

#### Scenario: The source repeats or conflicts on one event identity
- **WHEN** 已取结果中同namespace+tenant+event_id重复出现且正文相同或不同
- **THEN** 相同内容仅算一份来源并保重复信息，异文标冲突并保可区分指纹和有界内容，不静默采用最后一条；原始行数和截断边界仍可见
## ADDED Requirements

### Requirement: Compatible offline result composition preserves both version families
The investigation v2 verification probe SHALL load the API and Agents `app` packages in separate owned Python processes, compose their explicit compatible read apps through bounded stdio HTTP transports and SQL doubles, and SHALL preserve complete DTOs, retained ledger rows and legacy Run fields without new external calls or publication. This offline composition SHALL NOT be reported as actual network or PG verification.

#### Scenario: Published and unpublished fixed and program results cross both apps unchanged
- **WHEN** the offline probe reads fixed and program published, candidate, progress, observer and cancelled cases, plus legacy material-projection-blocked candidate and published cases twice
- **THEN** each result matches its direct owned result in canonical bytes and Markdown UTF-8, and all selected ledger rows and Mock tool-call counts remain unchanged

#### Scenario: Auth, tenant ownership and unknown version failures stay closed
- **WHEN** current API credentials or either read permission fail, request overrides occur, the internal token changes, a foreign tenant reaches owned lookup, or either family's historical managed event or result version is unknown
- **THEN** the proper layer refuses without fallback, automatic replay, leaked diagnostics or ledger mutation, and forwards only the current authenticated tenant and actor for authorized requests

#### Scenario: Owned verification process or frame fails
- **WHEN** a probe-owned subprocess has an EOF, oversized frame, timeout or other failure
- **THEN** the probe records an incomplete or failed result without overwriting prior evidence, does not replay the request, and cleans up only its own Popen handle using bounded waits

### Requirement: Program manual start admission atomically binds one owned Run and original begin
The new program manual admission store SHALL persist a stable tenant-operation-key Run, its unchanged program runtime begin and a separately pinned business admission intent in one transaction. It SHALL NOT change legacy source or runtime schema, automatically replay an unknown commit, upgrade an existing Run, or grant external call authority. Authentication and production target-writer policy remain separate entry requirements.

#### Scenario: Fresh program admission commits all identity and budget anchors
- **WHEN** a trusted current tenant and actor request a new supported manual operation for an owned canonical Alert with explicit server budget
- **THEN** one transaction saves the Run and two events with three artifacts, including the complete original source, immutable event-pinned intent, fixed owner, closed program versions, zero confirmed manual opening usage and a DB-time bounded deadline

#### Scenario: Repeated or conflicting operation does not reset execution
- **WHEN** an operation already has an owned Run, or two requests concurrently use the same operation key
- **THEN** only a fully confirmed first admission may enter the runtime once, an identical repeat only reads verified original anchors, and any old, mixed, partial or conflicting operation refuses without rewriting budget or deadline

#### Scenario: Other operation for the same program admission target is still active
- **WHEN** another operation within the new manual admission namespace has a ready, claimed, blocked, unknown or unsettled execution for that Alert
- **THEN** an explicitly READ COMMITTED admission transaction re-queries the operation and all target Runs after obtaining the Alert row lock, refuses missing or invalid anchors instead of filtering them out, and uses publication-aware verified current state to prevent admitting another key; legacy writers outside this namespace require separate policy before a write entry opens

#### Scenario: Admission transaction fails or commit acknowledgement is unknown
- **WHEN** Run, begin or pinned intent persistence fails, or the commit acknowledgement is lost
- **THEN** uncommitted rows roll back, an unknown outcome grants no dispatch, and an explicit cold read may only recover the original committed operation without automatic replay or owner takeover

### Requirement: Manual program start coordinator enters runtime only for its confirmed fresh admission
The new manual start coordinator SHALL require an explicit server target eligibility guard and current trusted caller identity, and SHALL use unchanged program runtime, publication and compatible owned-read contracts. It SHALL NOT register an HTTP route, widen existing service permissions, begin a second stage, infer eligibility from source text, or retry unknown work.

#### Scenario: Confirmed first admission executes the bounded runtime and publishes one version
- **WHEN** the current guard accepts and this invocation receives a confirmed committed fresh admission
- **THEN** only that invocation may enter the original claim and M3 reservation path, publish a confirmed stopped handoff once, and return the same owned result and Markdown without replacing owner, scope, budget or deadline

#### Scenario: Repeated start and explicit operation read cannot resume or publish work
- **WHEN** an existing operation is repeated or explicitly read, including recovery after an unknown acknowledgement
- **THEN** the coordinator only returns the owned candidate, progress or published version and does not call runtime begin, execute or publish, even if the earlier operation has stopped without publication

#### Scenario: Eligibility or persistence fails
- **WHEN** the guard refuses, is unknown or fails, or admission/execution/publication persistence is not confirmed
- **THEN** no unconfirmed step grants later execution, no call or notification is replayed, retained unknowns and gaps remain visible, and real user authorization and legacy-writer policy remain separate HTTP-entry verification requirements

### Requirement: Isolated internal manual write HTTP accepts only trusted gateway identity and bounded server-normalized requests
The new internal start application SHALL expose only its explicit start and operation-read POSTs with a dedicated current write token, independent configuration, a concrete controlled-test target policy and the existing coordinator. It SHALL NOT register in a legacy app, reuse a configured read/tool credential for write authority, accept client budgets or intents, or claim that configured isolation references prove real writer exclusion.

#### Scenario: Gateway submits a bounded manual request
- **WHEN** the current dedicated write credential, gateway tenant and actor, canonical Alert path and strict bounded operation/window/version body pass
- **THEN** the server normalizes the known manual program intent with its explicit budget and target guard and invokes exactly the selected start or read operation without retries or old-path fallback

#### Scenario: A caller supplies credential or control overrides
- **WHEN** the token is missing, stale or wrong, the request contains query overrides, forbidden or duplicate body fields, nil identity or an invalid window, or exceeds 4096 UTF-8 bytes
- **THEN** the application rejects before coordinator dispatch and does not infer permission, budget or target policy from source text or client input

#### Scenario: Controlled target configuration or persistence is unavailable
- **WHEN** controlled target policy/configuration is absent or invalid, real admission or publication confirmation fails, or the coordinator reply has the wrong known identity or flags
- **THEN** no default allow, replay, deployment or notification occurs; truthful errors and read-only recovery preserve the original ledger, while real user authorization and operational isolation remain later verified gates

### Requirement: Explicit user start gateway requires existing run and alert permissions without widening service scopes
The new API start factory SHALL require an explicit bearer followed by existing investigation:run and alerts:read checks, forward only the current authenticated tenant and user identity to the dedicated internal write endpoint, and validate its known outcome plus complete program owned DTO without importing Agents code or changing legacy permission defaults.

#### Scenario: Current user is permitted to submit a bounded start or operation read
- **WHEN** both existing permissions and the strict bounded request pass
- **THEN** exactly one normalized POST uses the dedicated backend write credential and current server-resolved identity; a full valid result and Markdown are preserved byte-for-byte, with read-only recovery never granting runtime entry

#### Scenario: Read-only service or current user lacks permission
- **WHEN** the caller is the existing shared read service principal, lacks either permission, has invalid credentials, or supplies a forged identity header
- **THEN** current authentication and authorization decide the identity and denial before backend dispatch, without granting service write scopes or accepting client identity overrides

#### Scenario: Backend outcome or transport cannot be confirmed
- **WHEN** the reply mixes versions or identities, contains invalid flags or refs or a failing nested DTO/hash, is oversized, redirects or times out
- **THEN** the gateway rejects without fallback or retry, treats a timeout as a potentially executed operation, and leaves recovery to the existing operation-read or owned GET rather than restarting

#### Scenario: Response streaming or implicit close continues slowly
- **WHEN** chunks keep arriving or HTTPX closes the response automatically at the end of a complete body
- **THEN** one whole POST-and-body deadline bounds waiting, every response and client close is independently bounded including implicit close, and a cleanup timeout never causes a second dispatch

### Requirement: Offline manual start composition proves current actor binding across independent app processes
The offline probe SHALL use separate API and Agents Python processes with actual new factories, coordinator and SQL doubles, preserve full requests, original ledgers and results, and bound each complete stdio exchange. It SHALL NOT call real services, replay unknown requests, modify legacy code or represent injected current users as real JWT/RBAC verification.

#### Scenario: A first request traverses the complete manual start and read path
- **WHEN** the test current user passes the original permissions and one controlled scenario enters the real new internal app and coordinator
- **THEN** its actual normalized actor and server budget are pinned in the original admission intent, the program runtime executes only once, and subsequent repeat, operation read and compatible GET return verified original results without extra calls or publication

#### Scenario: Commit acknowledgement or parent response reception is unknown
- **WHEN** a controlled admission/publication acknowledgement is lost, or the parent loses one actual completed child response
- **THEN** the original ledger and unknown outcome remain, no automatic replay occurs, and only a separately explicit read may recover the original operation

#### Scenario: A pipe or owned process fails
- **WHEN** a frame is oversized, malformed, incomplete, slowly streamed beyond the total deadline or reaches EOF
- **THEN** the probe preserves a failed receipt, never retries the request, and performs bounded shutdown only on its own Popen handle
