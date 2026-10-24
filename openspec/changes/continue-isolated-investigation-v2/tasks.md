**2026-10-25 M8a4.1限定通过：** 44直接及独立同44、5hash/4intent和额外6类型反例，[回执](../../../docs/operations/investigation-start-contract-20261025.json)。仅纯操作/重试判定，无持久启动；a4.1b来源投影、a4.2原子准入/后续入口及2.2/2.3仍待。

**2026-10-25 M8a3.3真实读取已执行：** probe12新＋24相关36通过、P2完整DTO及JSON类型漏验修后代码独审ACCEPT0；两个新服务16GET、原6/14和原M7结果不变，进程/身份清理。[真实回执](../../../docs/operations/investigation-result-http-read-20261025.json)结束独审限定ACCEPT/0必须修（独立36项、10源码/2helper hash、READ ONLY PG全14及完整DTO/进程/权限核验）；持久启动/Case/Deep及2.2/2.3未完。

# Tasks: 原阶段成果接收与后续逐模块续接

**2026-10-25 M8a3.2限定通过：** 33直接/独立同33及6hash/12 HTTP重放，[回执](../../../docs/operations/investigation-result-gateway-20261025.json)。ASGI/FakePG/transport，无真实网络/PG/启动；a3.3及2.2/2.3仍待。

**2026-10-25 M8a3.1限定通过：** 58直接及独立同58/6hash/11 ASGI重放，[回执](../../../docs/operations/investigation-internal-read-api-20261025.json)。仅内部token读边界，API用户permission/真实PG/启动及2.2/2.3仍待。

**M8a2限定通过：** 56直接/独立同56、6hash/3组读回通过，[回执](../../../docs/operations/investigation-owned-reader-20261024.json)。owned SQL reader不改账本，实际认证/PG/显式HTTP/启动及2.2/2.3仍待。

**M8a1限定通过：** 51直接/独立同51及6hash/3组重建通过，[回执](../../../docs/operations/investigation-profile-restore-20261024.json)。纯冻结上下文，实际owned/认证/HTTP/启动及2.2/2.3未完。

**M7c真实执行：** 当前6/14，两个新进程同版、原M6已核基线不变；160合同/probe独审43通过，[回执](../../../docs/operations/investigation-publication-pg-seam-20261024.json)真实结束独审限定ACCEPT/0必须修（独立11项/14hash、PG全14及样本/进程/权限核验）。无新查询/模型/通知投递，M8/Case/Deep及2.2/2.3仍待。

**M7b代码测试通过：** 149直接，P2原工具pin修后6反例拒；[当前回执](../../../docs/operations/investigation-publication-store-20261024.json)未参与实现者独立52项/6hash/7组完整只读重建限定ACCEPT、0剩余必须修。只SQL替身，c真PG待；2.2/2.3未勾。

**M7a限定通过：** 128直接/当前独审16、5hash/5包重建通过；[回执](../../../docs/operations/investigation-publication-preparation-20261024.json)。仅纯candidate；b原子发布/读取、c真实PG和M8仍待，2.2/2.3未勾。

**M6.2c实际接缝：** 112直接/probe独审15通过；新Run一次业务查询、5事件10工件读回、重复冷读一致与临时身份/进程清理，真实结束独审限定ACCEPT/0必须修。[回执](../../../docs/operations/investigation-fixed-runtime-seam-20261024.json)。仅固定有限目标，M7同版发布及2.2/2.3仍待。
**M6.2b2限定通过：** 97项直接/独立89及取消竞争修复复核通过，[回执](../../../docs/operations/investigation-fixed-runtime-controller-20261024.json)；c真实PG/HTTP/CH仍待，不核销2.2/2.3。

**M6.2b1限定通过：** 105项实际store＋SQL替身及独审放行，见[回执](../../../docs/operations/investigation-fixed-runtime-store-20261024.json)；b2控制器及c真实服务仍待，2.2/2.3保持未完。

**持续推进M6.2a限定通过：** 80项直接及独立同80项/6hash/计划观察一致，[回执](../../../docs/operations/investigation-fixed-runtime-state-20261024.json)。仅纯控制，b原子事务/调度和c真实接缝待验，2.2/2.3不勾；用户已授权连续逐块推进。

**A3限定完成：** 已审材料准备合同→实现→10新＋90相关/独立同100项→4hash/10观察及7正常视图复核通过，见[回执](../../../docs/operations/investigation-material-projection-20261024.json)。A2/A3纯层已放行，实际M6.2准入/固定查询/去重/持久交接仍待，2.2/2.3不勾；不把structured handoff写成已落库/已投递。

**A2限定完成：** 新完成政策版本、整窗/子窗及真实查询覆盖纯政策经71项直接和独立同71项放行，见[回执](../../../docs/operations/investigation-window-policy-20261024.json)。A3仅合同已核待实现，2.2/2.3保持未完，未实际接M6.2。

**2026-10-24 A1修复续接：** 已按规格/strict→实现→测试→独审完成新版地址身份接缝，111项直接通过、独立83项/7hash/反例限定ACCEPT，见[回执](../../../docs/operations/investigation-network-identity-20261024.json)。本块只修A1；A2/A3合同和M6.2—M9待推进，不新增勾选或核销2.2/2.3。下段A1未修是前一审计基线事实。

**2026-10-24独立总审计续接：** [报告](../../../docs/investigation/independent-audit-20261024.md)登记A1地址归一化误拒（P2待修），A2完成/窗口与A3投影阻断合同须在M6.2前确定；先修接缝，再运行/同版交付/显式入口，Case整体与自动政策前验证语义和Deep收益。此处只登记审计计划，不新增或勾选任务，2.2/2.3保持未完；功能代码未改，历史限域验收保留。

2026-10-24 main集成说明：本change接收远端调查`469e9467`的独立v2开发基线及原记录，保留双方已有设计和实现。旧restore迁移已在main限定核销归档，不恢复其活动目录；下述历史原文中的“沿原restore/5/15/不提交”等按原日期解释。D1—M4限定成果、M5.1与未完成M5.2分列，新HTTP未注册，M6—M9和v4分层未交付。当前只合并和审计，不启动后续业务实施、真实测试或部署。

## 1. 已接收的阶段证据

- [x] 1.1 保存D1—M4、M5.1与M5.2未完成状态的源码及公开回执；不把历史HTTP验证算新v2路径已验。
- [x] 1.2 核旧运行代码无改，v2尚未注册；本轮平台测试问题与总体复核另见集成审计。

## 2. 后续逐块推进（M1 profile合同已获实施授权）

- [x] 2.1 先确定profile合同并纯合同验证；随后按[评审响应](../../../docs/investigation/review-response-20261024.md)依次补可选正文局部降级、完整messages预算合同及直接测试。2026-10-24 M1纯绑定11新＋8兼容、I1正文45项、I2预算6新＋15模型合同及各自结束独审均限定通过；证据见[实施记录](../../../docs/operations/unified-investigation-implementation.md)及三份机器回执。仅核销这三个前置，不表示profile接执行器、真实新版入口或自动分组已交付。
- [ ] 2.2 逐小步完成M5.2模型步骤与Deep循环；用独立v2接缝验证，不改旧入口。原固定首例只验接缝，另以结果确会改变后续查询的有界场景评价Deep增量价值。
- [ ] 2.3 推进M6—M9、同版交付、告警与Case入口及领域能力，每块保原验收顺序和边界。固定查询/有限事实路径不强制等待M5选工具模型；需要Deep的路径仍须2.2通过。M7先同版发布/读取，再M8显式入口，Case及自动政策后续分别验证。具体顺序见评审响应第4节，实施前补精确规格增量。

2026-10-24续接前提进度：共享场景卡、独立v2 query_api及36项离线合同通过；02新Run真实1query/3events/6artifacts、4认证拒绝及hash/UTF-8/关联读回通过，模型0，进程/角色已清理。01字段假设失败及改为真实raw_event.telemetry映射的修复保留，未重放。仅完成主设计12.7顺序2的受控M2/M3接缝，结束独审另记audit；不核销2.2 Deep或2.3整体，不归档。详见[公开回执](../../../docs/operations/investigation-v2-query-seam-20261024.json)。

2026-10-24 M6.1当前增量：新纯固定政策13＋采用13＋视图11＋业务绑定11共48直接通过；程序有限事实、六问题及停止交接已实现，结束窄审另记audit。只是查询后的纯层，M6.2实际M3/query/去重/持久接缝及多轮失效传播仍待做，不勾完整2.3；五类停止输入不冒充真实预算/时钟验证。证据见[M6.1回执](../../../docs/operations/investigation-fixed-recon-20261024.json)。

## 原分支任务历史（保留原文，不作为当前任务状态）

## 2026-10-24 v4告警侦察与Case调查分层（当前设计，未实施）

用户要求结合实施进度和新建议重新设计，以[主设计v4](../../../docs/architecture/investigation-planning-design.md)第1节为准。告警profile负责分诊后的有界侦察、缺口与升级建议，保留20自动处理过程及无Case详情；Case profile固定完整成员快照，在新Run引用多个告警的不可变材料并整体调查。Case创建/关联与启动是独立政策，Router四领域按需参与，不串跑两套完整编排。

D1—M4限定回执及M5.1九项纯合同通过保留；M5.2仅observer问题组参数增量未测，完整Deep/循环/发布/分层入口尚未交付。当前仅文档，不继续实现/业务或模型测试。累计开发tokens不限、单调查有界，OS后置；无部署/提交/push，原5/15和旧失败保持。

本轮完成设计及相关展示/规格/进度文档的一致性修订和一次独立设计审阅，不新增勾选树、不勾原整项。讨论选定后按主稿12.7续接，不因旧段落从M0重跑或一次完成整条M8。以下各日期为历史范围，当前停点见实施记录顶部。

## 2026-10-23 M3逐小步推进（最新授权，未实施验收）

用户已授权继续M3；沿原2.1/3.1/3.4/4.1，不另加勾选树，原15项/5勾保持。先按[主回执M3预期卡](../../../docs/operations/unified-investigation-implementation.md)固定IO及判据；本段和strict只是实现前合同，不能作为业务通过。

1. M3.1只实现纯身份/预算reducer并直接离线测试：固定stage/owner、step与attempt区别、两段用量、显式model/tool预算和旧配置映射、并发预留语义、无请求释放但保尝试、unknown占位、真实超额记账并停、绝对deadline。DB/HTTP/模型0；小上限明示为用例配置。通过留回执才写M3.2。
2. M3.2只接既有PG三表及同Run FOR UPDATE：显式tenant/run归属，MAX(seq)+1保旧seq；begin/预留/完成及相关snapshot/input/output工件各自原子，写失败不虚报成功。验证重复begin拒绝、不清零、最后slot互斥、完成幂等不重复累计、异文拒绝、半写回滚；在state snapshot内分列opening triage、stage已知用量及unknown/unpriced并合计Run总量，与完成事件/工件同事务保存。核`investigation_runs.total_tokens/total_cost`等计费列、旧Run.status和triage表不变，不新增DDL；读取projection后置M8。直接测试通过留回执才接M3.3。
3. M3.3持久gate包装仅本批M2工具，预留commit后外呼，失败/超限/到期/身份不符外呼0；完成失败保未结算与缺口且不重查。用受控新合成Run在真实PG核事件/工件/含用量聚合snapshot的原子性、Run计费列不变及旧seq，再一次真实M2查询读回匹配记录和持久refs；无模型，其他拒绝/故障用替身完成，不扩真实查询矩阵。结果/命令/版本/失败及独立复核记主回执和原execution/audit后才放行M3，不自动进入M4/M8或OS，不部署、提交、推送。

## 2026-10-23 M0—M2首个工具实际收口（前批原任务部分交付）

D1/D2/M1/M2调用方/API各8项共40直接测试正常exit0，旧工具51项兼容正常exit0；每块通过才进入下一依赖模块。D2真实3行、D3一告警/2消息及精确来源关联通过；M2真实5次HTTP查询（2匹配3空，包含子毫秒半开边界）、4认证拒绝通过。M1/M2独审分别限定ACCEPT、0必须修；临时API已停止。详见[实际回执](../../../docs/operations/unified-investigation-implementation.md)及本change execution/audit。

本批到M2首工具停止后续实施；M3持久/额度、M4模型、统一调度和M8实际Run入口未进，OS后置。未发模型、部署、提交或推送，原15项/5勾及旧失败/unknown保持；旧pytest显示通过但挂起exit1不算通过，后续禁cacheprovider的正常51项只证明该次兼容结果。下列预期顺序保留，不因本批局部完成提前勾原整项。

## 2026-10-23 M1纯合同→M2首个记录工具（本批已按步执行的顺序）

D1—D3已按步通过，M0只对本批有限来源观察场景放行，非恶意/授权裁决；真实结果及新预期见[实施记录](../../../docs/operations/unified-investigation-implementation.md)。以下仍沿原2.1/3.1/3.4/4.1，不新增勾选树，保持5/15；M1/M2是否通过必须由各自实际回执确认。

1. M1先实现并离线直接测试：仅explicit_set中的已核canonical Alert成员快照，可信caller身份、冻结结论/查询范围、版本policy/questions及query admission；不查DB、不发HTTP/模型。核不变性、跨tenant/目标类型/绝对窗口/成员遗漏、问题依赖/关键性、参数出处与两类scope边界；Case/Incident解析留M8。通过并留回执才写M2代码。
2. M2只新增网络`activity_records`及受限调用方，先按本批政策捕获caller/问题scope并在HTTP前拒绝越界，再由泛API执行认证tenant/`lake:query`和50条/24小时全局bound；不把泛API当Run持久scope授权点。核实际参数化SQL及UTC微秒左闭右开边界、raw_payload+ocsf_json合计16KiB/条与256KiB/次原文上限；数据库生成完整hash/字节数并限制正文返回，不拉完整大正文后裁剪。另核空/不可用/错误/截断、重复/冲突与来源回执。
3. M2直接测试通过后，用本批D2/D3资料真实走API→湖，按实体/目标/窗口检索而不靠预知event_id替代过滤，必须只返回匹配UUID并排除不同目标与窗外记录；必要精确ID关联另核。来源结果`unknown`保留，调用方越界HTTP0、API跨tenant边界分别举证。M1/M2结束留一次独立复核，M3持久化/预算、M4模型、M8运行入口和OS均不提前实现或宣称通过。

## 2026-10-23 M0工具数据三步执行（已执行部分范围，结果另见回执）

用户已授权先实值化ClickHouse场景数据并验告警关联，再接查询工具；OpenSearch后置。按[实施记录](../../../docs/operations/unified-investigation-implementation.md)保存每步预期、实际结果与放行，沿原2.1/3.1/3.4/4.1记录，5/15不变。本段不表示下列步骤已完成，也不将尚未实现的M1写成通过。

1. D1离线生成：只生成1条告警和3条规范化网络事件，覆盖窗内匹配、窗内不同目标及同目标窗口外；事件UUID各自唯一且引用跨产物一致，时间为固定绝对值，expected独立于业务输入。直接验证格式、字段、ID/窗口关系及答案隔离；本步通过后才允许真实写入。
2. D2入湖及字段：复用原LakeWriter，对新独立测试tenant有界写入D1的3条事件，不重写生产业务模块。按tenant及精确事件ID真实读回，核行数、时间、实体、目标、动作/结果和原字段映射；原writer fail-soft或仅返回调用成功不作入湖证明。部分失败/不确定保留回执，不为凑通过无界重发；字段及三条控制关系通过后才进入D3。
3. D3告警关联：复用现有原Fusion探针及独立topic/group/Redis范围，处理D1的一条告警，读取PG实际canonical Alert，核tenant、source_event_ids与D2三条湖记录的精确ID关系，区分原入口追加ID与真正湖事件ID。留存匹配和两条排除对照；不触发分诊/调查模型或正式消费，不将202、Kafka发出或PG有行单独当关联通过。通过后先记录M0数据前提结果，再按模块依赖写后续预期，不跳过M1而提前实现完整查询/调查流程。

## 2026-10-23 统一调查M0—M1起步（原任务部分交付）

用户已确认v3方案并授权逐模块实施。沿原2.1/3.1/3.4/4.1记录，原15项和5/15保持；下列为本批执行顺序及放行依据，不是新增勾选任务树。统一预期/回执见[实施记录](../../../docs/operations/unified-investigation-implementation.md)，当前是否完成按其实际结果，不以规格或CLI通过代替。

1. M0：核调查分支/未提交工作和已有小修，只读核选定隔离资料的实际字段、来源、成员及窗口，固定“来源记录陈述核对”的有限目标与不作恶意/授权完整裁决的边界；先保存支持例、反例、缺源/冲突及材料指令对照的预期。未知来源不写成可用，M0场景条件成立后才进入M1。
2. M1：先固定认证上下文、显式成员、两类scope、版本policy/questions的输入输出和预期，只实现本块；扩展仅作准入/拒绝，不查源、不调用模型、不接现有入口。直接核跨租户/对象类型、绝对窗口、成员遗漏、结论范围不随查询扩展、未定义扩展拒绝、两维问题分离及关键问题保护。失败先定位并重测本块，不能带阻断项进入M2。
3. M1通过后保留文件版本、命令、预期与实际、限制和放行结论，再为M2另写所选工具的预期并逐个接入/验证；本次文档不宣称M1或后续已通过，不提前实现M2—M9。阶段结束由未参与实现者复核本批差异与证据，更新原execution/audit及PROGRESS，不改历史失败，不自动提交、推送或部署。
