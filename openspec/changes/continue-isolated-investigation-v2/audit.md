## 2026-10-24 M6.2b2控制器结束窄审

初始87项及6hash/7观察通过，但fresh_code_audit另复现取消窗口重复blocked抢先finalize的P2，b2不放行。补合同/红测后修：非本次owner blocked仅pending，读回先核观察真实留存再清，冻交接仍不可覆盖。最终独立89项、当前6hash/7观察及竞争结果一致（HTTP1、观察工件1/ref存在、facts0/unsettled1、Cancel传播），原冻结源码hash匹配，限定ACCEPT/0剩余必须修。[当前回执](../../../docs/operations/investigation-fixed-runtime-controller-20261024.json)、[失败/源码](../../../docs/operations/investigation-fixed-runtime-controller-race-20261024.json)。实施97项与独审89子集不相加；仅离线，c真实服务未验，无旧源码/部署或整体核销。

## 2026-10-24 M6.2b1事务store结束窄审

fresh_design_audit先限定合同ACCEPT，fresh_code_audit未参与实现独立复跑115个不同测试（原归类105＋重叠10已据文件清单更正；不与实施105相加），5hash/6观察一致；补核丢ACK、并发finalize、通用store交接后拒绝及unknown不改写。限定ACCEPT/0必须修。[回执](../../../docs/operations/investigation-fixed-runtime-store-20261024.json)。两补充探针失误（提前load消耗注入、Windows event loop socket替换）修后观察通过，未改源码。仅真实store代码/SQL替身，无真实PG/HTTP/CH/模型；b2控制器及c仍待，旧Run/旧源码及2.2/2.3未完保持。

## 2026-10-24 M6.2a纯运行控制结束窄审

fresh_design_audit先限定合同ACCEPT/0，fresh_code_audit未参与实现，独立12新＋68相关共80项、6hash/完整计划/4组claim观察/已知与unknown用量及结束引用一致。补核M3超额、取消并unknown及晚到重复结束：账本保留、不重发、不覆盖。限定ACCEPT/0必须修，见[回执](../../../docs/operations/investigation-fixed-runtime-state-20261024.json)。首次相对解释器路径错误未启动，改绝对路径80通过。仅a纯层，b原子claim/版本隔离/实际reserve与工件保存、c真实接缝仍待；无真实业务/模型，旧services及历史回执未改，不勾2.2/2.3。

## 2026-10-24 A3投影阻断交接结束窄审

fresh_code_audit未参与实现，独立10文件100项通过，4hash/10观察与引用一致；补核末条来源hash/版本及query count错误优先拒绝，自由body/coverage/reason标记未回显，无query回执时unknown/not_attempted保区别。专用内部阻断回执保已核material/query/source版本，facts空、六问题未评估，不伪造EvidenceView/来源不可用；正常路径7种材料与c94eb97 canonical_doc逐字节相同，view_ready不替代I2门。限定ACCEPT/0必须修，详见[A3回执](../../../docs/operations/investigation-material-projection-20261024.json)。仅纯准备/结构化交接，M6.2实际保存/人工投递/运行器未验，无真实业务/模型、旧代码/历史回执改动，不勾2.2/2.3。

## 2026-10-24 A2窗口完成政策结束窄审

fresh_design_audit指出完成政策变更需独立版本，实施前补completion_policy_ref后限定合同ACCEPT/0；fresh_code_audit未参与实现，独立复跑7文件71项、3hash/12观察含result_ref完全一致，另核unknown/not_attempted不计覆盖。子窗保4事实及引用、列遗漏区间，整窗空/截断和停止原阻断保持；限定ACCEPT/0必须修。仅A2纯政策，A3尚待实施、M6.2运行/持久交接未验，旧回执不重算。[回执](../../../docs/operations/investigation-window-policy-20261024.json)。

## 2026-10-24 A1地址身份修复结束窄审

未参与实现的fresh_code_audit核891d07e后的新版地址差异及[公开回执](../../../docs/operations/investigation-network-identity-20261024.json)，独立复跑新8/scope8/caller8/evidence11/Deep9/profile11/fixed13/API records8/query7共9文件83项通过；实施方完整111项包含该子集，不累加。另核8组地址反例，mapped等价而compatible/NAT64/不同zone不误合并；7hash匹配，五种稳定观察一致（新query_id/时间导致新snapshot属预期）。原始来源值/路径、payload及source版本不改，Deep同任务别名指纹一致并拒重复，API/旧源码及历史审计JSON/probe未改。限定ACCEPT、0必须修；仅A1离线功能修复，无真实业务访问/持久提交证明/模型/部署。A2/A3与M6.2—M9仍待，2.2/2.3未勾。初始夹具source_run误用及修前red已登记，不改历史失败。

## 2026-10-24 新一轮独立总体审计

基线7b7bb6b，fresh_design_audit/fresh_code_audit/fresh_evidence_audit三位新审阅者分别核原设计演进、实现和证据，不承接原review_response_audit结论。140项合同通过，另25项为重叠复核；39个回执hash条目一致。新增离线反例确认A1 mapped IPv6归一化导致合法结果误拒，P2未修；A2子窗口ready与A3无模型路径的模型投影限制交叉裁定为后续合同边界，不报告为越权或既有I1/I2回归。总体架构可保留，完整调查质量不予追认，详见[审计与逐步计划](../../../docs/investigation/independent-audit-20261024.md)及[观察回执](../../../docs/operations/investigation-independent-audit-20261024.json)。本轮只改报告/索引和公开离线probe，无功能修改、真实业务访问、模型、部署或合main；历史ACCEPT按原范围保留，新发现进入续接门。

## 2026-10-24 M6.1纯固定政策结束窄审

未参与实现的review_response_audit只读核新fixed_recon、专用测试、活动规格/预期及[回执](../../../docs/operations/investigation-fixed-recon-20261024.json)，独立13新/0.096s＋采用13/0.066s＋视图11/0.055s＋业务绑定11/0.027s共48项正常exit0；5份源码/测试hash匹配，6类材料状态和5类execution_stop的公共观察（result_ref/snapshot/事实/六问题/held计数）与实际纯函数重建一致。strict及diff通过，既有services源码/API/data工具和迁移archive未改，本块仅新增两个代码/测试文件。

结论**限定ACCEPT、0必须修**。正常ready仅为Q1/Q5的有限目标，Q2无exactlink保原非critical缺口，Q3a/Q3b/Q4及性质/授权仍未知；冲突、截断、未读正文保合法事实/refs且partial，五停止原因只收紧且不假作M3实际门。旧snapshot/跨scope/Case/未提交视图拒绝，事实和依赖随新snapshot重建；没有伪造模型候选/程序理由、追加查询或总结模型。仅放行查询后纯政策层，不代表完整M6/M6.2、真实M3运行准入/时钟、查询去重、多轮失效传播、持久交接或发布。审阅及本批真实HTTP/PG/CH/模型访问均0，不归档整体change或勾2.2/2.3。

最终文档/回执窄复核仍0必须修，独立核12份Markdown、463个本地链接及围栏通过，纯政策/M6.2运行接线/完整调查边界与实际审计观察一致；该最终窄复核未重跑测试或真实工具/数据库/模型。

## 2026-10-24 共享场景卡与独立v2真实查询结束窄审

未参与实现的review_response_audit只读审阅本批新factory/原认证与权限、新dispatch、共享场景卡、显式telemetry→M1投影和可共享probe，独立复跑API7/records8/caller8/gate9/场景4共36项exit0；18源码hash、5测试hash、5本机观察hash匹配，02公开与本机回执一致。expected未进入scope/args/模型，独立应用不挂旧main，实际SQL观察仅1条且参数/query_id一致。01字段假设失败原件/源码/清理保留，新02批无重放。

另一次经已有SSH配置进行BEGIN READ ONLY的独立PG复核：新Run627b8f1d-c9c2-5c9d-a07d-e918ae6b0001有3事件6工件，全部UTF-8字节/hash/event/run/tenant关联通过；stage tool1/model0/unknown0/unsettled0，query_id21862954-abff-42a8-8734-bc79bcd84e9e对应单匹配事件。Run仍running、completed_at null、旧计费0，01 Run行0。四临时角色NOLOGIN/非super/非bypass，investigation_runs表SELECT/INSERT及id列UPDATE有效权限均false、活动连接0；三表撤权另有runtime清理源码/回执支持。PID9452不存在；PID5708已被backgroundTaskHost复用，创建时间134373101640825200不同于本次API134373098144449413，未碰当前进程。没有业务写入、授权、模型、重放或部署。

最终**限定ACCEPT、0必须修项**，只接受受控新路径scope/query/持久接缝及已核profile输入留存，不认定正式M8启动授权、profile驱动整环、Case继承、模型质量或发布。公开refs/失败/清理/版本详见[机器回执](../../../docs/operations/investigation-v2-query-seam-20261024.json)。活动change strict/diff通过；tasks2.2/2.3未勾，不归档，下一M6固定路径仍先精确合同和预期。旧服务、数据工具与迁移归档保持。

## 2026-10-24 I2完整messages预算结束窄审与2.1核销

I1保存f6a3fa8后，先I2精确合同/strict，再新增共享计量与三处接缝、新6项及原模型15项通过。未参与实现的`review_response_audit`独立新6、原模型15和I1六项exit0，核[回执](../../../docs/operations/investigation-request-budget-20261024.json)的4份hash、1/7/8/10准备观察和实际fake执行结果一致，限定ACCEPT、0必须修。完整messages包含system/任务封装/UTF-8转义，12KiB常量及token公式不改；恰好边界通过/超1字节拒绝，准备与egress超限均预留/外呼0，全部事件/Alert/query引用保留。

本步选择明确阻断和材料缺口，不宣称自动分组、大材料已消费或真实模型质量通过；固定模板开销仅准备阶段可核，egress只报实际完整字节/上限/超额。M1纯绑定、I1、I2各自限定放行后仅勾tasks2.1；后续2.2/2.3未完，change不归档。旧版、API入口、tools/testdata、归档及主规格未改，无真实业务调用或部署。下一块是共同场景卡和独立v2受控查询接缝，不能把本轮离线成果追认为真实新路径通过。

最终交接静态核：本轮11份变动MD的443个本地链接无缺失、围栏平衡；三份新回执共11项源码/测试hash均匹配当前相应文件。相对3fa4be3不存在已在该基线中的services文件修改；相对a3a0108的API、tools/testdata、迁移archive及主specs均无差异。活动change strict与diff检查通过；阶段提交/推送仅调查分支，不归档或合main。

## 2026-10-24 I1可选正文局部降级结束窄审

M1以7e84fe7保存放行后才做本块，先精确规格/设计/预期及strict，再改新版可选摘录和相关事实缺口投影。6新＋11视图＋13采用＋15模型合同均正常exit0，公开[回执](../../../docs/operations/investigation-optional-excerpt-20261024.json)含源码hash、样例和失败历史。未参与实现者`review_response_audit`最初发现转义Unicode编码异常仍整体失败，暂不放行；仅在message编码处捕获invalid_unicode并补正常同批对照后，独立原反例及6项通过，更新为限定ACCEPT、0剩余必须修。正文不替换/透传，必要身份/hash/窗口/版本/前缀校验不放松，有限事实/readable保缺口且无强结论增强。

解析递归测试助手的一次错误假设及修正也原样记入回执。旧源码/API/归档保持，无真实模型/业务HTTP/DB/写入/部署；12KiB及I2此时未改。只放行I1，可进入I2；旧评审probe保原基线用途，历史8模型试验不改写为新语义已验。

## 2026-10-24 M1业务profile纯合同结束窄审

用户授权按既定步骤推进；以`a3a0108`为基线，先spec/design/实施预期与strict，再新增`business_profile.py`和独立测试。未参与实现的`review_response_audit`只读窄审限定ACCEPT、0必须修：独立11新＋原scope8项exit0；3份源码hash及无Case告警/部分选材Case两份descriptor与[公开回执](../../../docs/operations/investigation-profile-contract-20261024.json)一致。profile/target/objective/policy显式，manual/automatic不改变归属；4成员全选/只选3条保最早遗漏，原scope不扩大。目标认证/归属/一致分页均明确为调用方前提，纯结构校核不冒充认证。

新增模块无IO、预算创建/Run写入、执行器接线或旧入口修改；strict及diff检查通过。只放行M1纯绑定，允许进入I1正文降级；profile实际入口、Case继承/启动、新HTTP和M5整环仍未完成，tasks2.1保持未勾。旧源码、历史失败/unknown及迁移归档保持；阶段保存/推送不代表部署。

## 2026-10-24 调查分支对main评审的响应（仅评估/计划）

用户要求拉取最新main、判断调查意见是否合理/采用并制定后续计划，允许新建调查分支。已fetch至`541511ce`，本地main快进后从其建立`codex/investigation-review-20261024`；普通根目录原先clean，原调查469e9467已在main中，未复制旧树、修改Windows分支或合回main。

[评审响应](../../../docs/investigation/review-response-20261024.md)逐项区分独立评审I1—I4与整合审计同名编号，I1/I2采纳修复，I3限定采用，I4落实程序确定性路径与按需Deep分别验收。原架构保留；profile后先补两处材料接缝，再独立v2查询及M6/M7/M8a有限交付，Deep/Case/领域/自动政策分步。tasks的2.1—2.3仅细化计划、保持未勾，未增加业务规格或宣布修复完成；精确spec调整留实际实施前。

新增[断网反例脚本](probes/review_material_contracts.py)与[机器回执](../../../docs/operations/investigation-review-validation-20261024.json)。Python3.12.4实跑：短文成功，513ASCII/对象message整视图失败；10条视图7882B、messages14194B>12288B，7/8条跨界；DurableAnalysis在fake预留/模型调用前拒绝。仅备注不同的两个来源版本保相同字段，但Q1 supported拒绝、Q2/Q5保留。exit0仅表示反例重现，不是修复/质量通过；首次guard误拦Windows内部socketpair的脚本exit1及修正已披露。原运行源码/旧测试不改，0真实业务/模型/写湖/部署；M5.2、新HTTP及分层仍未交付，原迁移归档/失败/unknown保持。

未参与本轮编写的`review_response_audit`只读窄审限定ACCEPT、0必须修项：独立重跑probe exit0，错误码、字节大小、fake预留/完成/调用0和Q1/Q2/Q5采用结果均与受控JSON一致；主设计12.7、响应及tasks的依赖一致，任务未提前勾选，I3未放松未读反证，I4未宣称模型无价值。6份MD的246个本地链接无缺失，OpenSpec strict与diff --check通过；services、tools/testdata、迁移archive和主specs相对origin/main无差异。结论仅覆盖本轮文档/计划/复现材料，不是问题已修、业务验收或整体质量通过；无真实业务/模型/数据库/部署操作。

## 2026-10-24 重新独立设计评审

用户要求重新客观审查设计、不改代码。以main a82346dd为基线，从原需求、当前设计及源码重新建立判断，数据与调查由未参与实现者分别审阅，主审复核关键原文和纯内存反例，见[详细评审](../../../docs/operations/independent-design-review-20261024.md)。保留两profile共享内核、来源与判断分离、Case继承及同版发布方向；调查可选正文整视图失败、视图与完整模型消息预算不一致两项P2接缝已复现，命题冲突粒度和模型业务增益另列建议。数据标签可判定性、配对评价与非法分类指标问题分别由数据线后续讨论。

本轮未改设计正文、源码、测试、配置或tasks，不将待实现能力判为设计错误，不给全模块ACCEPT；所有建议未实施。评审只做静态分析和纯内存反例，无真实模型、业务查询/数据写入或部署；用户随后要求提交并推送本次报告、PROGRESS入口及本条引用，其他工作保持。

## 2026-10-24 合并后的双方总审计与协作交接独立复核

用户要求先合并、不影响原开发设计，再统一最新进度与数据湖协作。root在main5c1202b5后编写[统一审计](../../../docs/operations/data-investigation-integration-audit-20261024.md)；未参与编写的merge_audit只读核对后限定ACCEPT、0必须改文档项。确认A1/A2/A3、Python3.11 is_junction兼容、IPv6文本测试失败、新v2未注册及M5.2/v4分层未交付均准确；共享fixture/写湖与scope/query/采用/评分分工保留原设计，不改写原贡献或验收。

额外确认X2：原fixture的告警telemetry已含匹配事件正文，只适合作来源关联与范围验证，不能单凭该夹具声称E3必须补查或工具增益；新盲测预期后续另定，保原判据。root实际合并工具测试112 passed/58 subtests passed/3 failed（同一测试的3个IPv6子项）、exit1，文档未称全绿；85新Agents/8新API独审断网通过，未新跑PG/湖/模型。原源码与测试仍逐字保持，修复留各分支后续。

六份审计入口静态499本地链接/围栏无缺失，OpenSpec strict及diff通过；本条加入后的最终窄校验另按Git检查记录。用户要求main同步给各开发分支续接，本批允许普通提交/推送main，不部署；主工作区其他34份未提交材料继续保持，不混入总审计提交。

## 2026-10-24 main合并候选独立窄审

未参与本轮冲突解决的merge_audit只读核对候选，限定ACCEPT、0本次合并必须修项。调查469e9467的27份Python源码/测试与2份包README字节保持；旧services无改，新API未注册。调查分支原restore六文件的新增非空行完整保留到本独立change，22条Requirement齐全；旧archive与数据合并父提交c41db518保持，无未解决Git冲突。当前导航、历史5/15和main限定核销区分，不改变原设计或追认完整调查。

独立断网Agents85/API8通过；共享工具16项有一项测试的3个IPv6文本表示断言在本机Python3.12失败，实际IP值相同，原测试未改，交后续总审计登记。未运行opt-in PG、真实HTTP/模型/数据湖，不重复业务测试或部署。用户最新要求先合并，再形成双方建议与数据湖协作总审计；合并接受范围仅未启用开发基线，M5.2/v4分层及正式入口仍未完成。

# Audit: 调查分支原独审与本轮集成

2026-10-24 main集成说明：本change接收远端调查`469e9467`的独立v2开发基线及原记录，保留双方已有设计和实现。旧restore迁移已在main限定核销归档，不恢复其活动目录；下述历史原文中的“沿原restore/5/15/不提交”等按原日期解释。D1—M4限定成果、M5.1与未完成M5.2分列，新HTTP未注册，M6—M9和v4分层未交付。当前只合并和审计，不启动后续业务实施、真实测试或部署。

## 2026-10-24跨机器协作实际收口

源代码/设计/进度/问题已正常push到远程调查分支，并独立ls-remote核32d00ca；推送不含Windows分支。之前独立窄审覆盖可移植文档和安全清理方案，实际操作随后由执行器完成：382+171份本机原件搬迁前后hash逐项一致，已核根内绝对路径/旧detached状态/clean，移除5个pyc后Git安全删除旧工作树。原件不丢、旧目录不存在，只有普通根目录为活动工作树；不把私密原件承诺为跨机器Git内容。

本次只补实际完成记录并同步，没有业务源码修改、真实模型/基础设施测试或部署；源码隔离结论保持。GitHub直连超时已通过本机现有代理的单命令参数解决，无全局配置变更。主分支合并留后续评审，本次不执行。

## 2026-10-24普通项目目录及跨机器共享交接审阅

用户要求调查直接在普通项目目录开发/提交/推送，其他机器能读取设计、进度、问题并后续正常合并。根目录已切codex/investigation-working，原Windows94bb52f分支保留；本机适配复制到被忽略的.local/windows-local。新增docs/investigation/README.md，入口导航均指Git受控文件，不要求取得原机器.local；私密原始材料与可共享结论的边界明确。

未参与整理的audit_contracts在普通根目录完成窄审，限定ACCEPT、0必须修订；核17个导航相对链接及M4有限/M5未完成/v2 HTTP未接状态，不把读取全部设计/问题等同取得私密原文，也不把文档当新版完整验收。本轮services/tools无源码变化；仅文档/工作目录整理，无业务/模型调用或部署。源代码和公开回执在74d4d90，远程分支核到原3fa4be3；本轮正常推送到同名调查分支，不含Windows分支或main合并。远程确认及旧worktree安全清理以实际后续结果为准。

## 2026-10-24严格双版本源码隔离与本地提交保存

用户明确旧版完全不受影响，需修改旧实现时复制到新版本函数。本批按预期卡分两步：API新records/分派移入独立investigation_v2，旧分派/旧测试恢复原件，8新合同与51原合同通过；随后9个Agents新增模块移入独立investigation_v2，85项直接合同通过。旧已跟踪services源码/旧测试相对3fa4be3无差异，旧入口不导入新包，独立新分派不回落旧工具；新URL预留且未注册。新包不是已经可用的HTTP服务或完整调查，历史真实回执不追认新路径通过。

未参与修改的audit_contracts独立窄审最终限定ACCEPT、0项剩余必须修订。已修主稿第10节“可修改共享能力”的残句，AGENTS/spec/设计均明确旧代码不改、变化复制或新增。隔离回执见docs/operations/investigation-v2-isolation-20261024.json；JSON和源码语法、OpenSpec strict、diff及敏感信息/范围扫描通过。原任务仍5/15；不发真实模型/HTTP/PG、不运行入湖、不部署或push。Windows工作树94bb52f及其干净状态保持。用户调查本地Git提交授权有效，源码/测试/设计及公开回执一并保存，.local私密运行材料不入Git。

## 2026-10-24 开源→当前→v4改动说明审阅

用户要求说明流程及具体细节如何变化。主稿第16节按13环节对照固定开源34ca18、已发布/本地/未测实际和v4目标；源依据为固定来源清单、原版分析和原批回执，未以最早项目提交或20新构建代替纯开源。`audit_contracts`限定事实审阅ACCEPT、0项必须修；两条可读性建议均采纳（candidate05直接链接，M1纯合同/真实接缝区分）。不重审v4设计、M4或全部上游源码。新增说明后的主稿SHA256 `e0ea6bda688d05c7e55d3bc549a7bb8560ace859a1337d8409455ae185c8ed50`；下方旧v4审阅hash仍表示追加第16节以前的版本。

静态40本地链接/35表/围栏/JSON、diff检查与OpenSpec strict通过；任务仍5/15。说明图13主题/52次版本切换、320px全部主题无横向溢出、暗色代表呈现通过且无pageerror；先缺Playwright自带浏览器，后复用已装Chrome临时无头上下文完成检查，未安装/升级环境或使用用户浏览器资料。说明图源码位于本任务允许的visualizations目录，不是产品页面实现或站点发布。全部检查限文档/解释交互，无业务源码修改、模型/业务服务测试、远端访问、部署/提交/push。

## 2026-10-24 v4业务分层设计结束审阅

结论：未参与本稿编写的`audit_contracts`限定设计 **ACCEPT，0项剩余必须修订**。范围为[主设计v4](../../../docs/architecture/investigation-planning-design.md)、相关OpenSpec分层需求及页面/进度一致性，不是实现、模型质量或部署验收。主稿最终SHA256 `2a4ba75d91dc414c109634985b654e3fcf6e51a4d48846ea83ecea0f815664a9`。

初审两项必须修：继承段以“版本等变化时才补查”误限新问题/覆盖不足；只要求自动启动幂等而遗漏人工重试。已明确同问题有效查询不重复，新问题/缺料/覆盖不足/冲突按政策补查；人工和自动均稳定操作键、持久意图、唯一Run，已有运行不并发，不重置额度。窄复核另清理表格“自动模式才形成意图”的残句。成员快照建议已采纳：创建仅预览，启动时固定一致成员版本及分页，等待中新增成员纳入。

新增1.9只补Case代表场景必需的多成员PG/CH资料和验证顺序，不铺全领域数据。保留20自动处理过程/无Case详情、旧首次分诊、M4限定通过/M5.1通过/M5.2未测、20只核前端构建等边界。静态检查8文件108本地链接、69表、围栏/JSON无问题，`openspec validate restore-alert-investigation-integrity --strict --no-interactive`与`git diff --check`通过，任务仍5/15。后续新增的审计链接指向已有文件；未改业务源码/测试、发模型/业务查询、访问服务器、部署/提交/push，旧失败和unknown保持。

## 2026-10-24 M4限定结束与后续M5

2026-10-24 M4限定通过：选定8例原文/采用/可读均通过，23484tokens；其中两例冲突按完整消息/9源码/调用AST等价复用。02开发18回复52185tokens，5个失败原件保持、无unknown/unsettled、费用unpriced。15项直接测试通过，未参与实现者audit_contracts限定ACCEPT/0必须修。仅network_observation.v1/Q1,Q2,Q5，非完整恶意/授权卡或全调查通过。PG临时角色NOLOGIN并撤权；M5待按小步实施，OS后置、无部署/提交/push，原5/15保持。 版本、8例清单、失败及复用证据见[主回执](../../../docs/operations/unified-investigation-implementation.md)与[机器回执](../../../docs/operations/unified-investigation-m4-20261024.json)。

## 2026-10-23 M4.5授权与验收边界（预期，非实测结论）

最新用户授权已明确：开发调试测试累计tokens不限，可持续修复复测，无需逐批再确认；真实单次调查仍有上限。原pending复测预算选择已被覆盖，不据旧记录继续等待确认。M4.5须逐个执行8个原语义组合，每个独立test Run沿M3 20000tokens/180秒、单请求45秒/2048/retry0；累计不限不允许绕过预留、单Run额度或自动重放未知请求。失败定位修复后留新版本/new trial，不清旧Run、失败/unknown和原冻结。

验收分别评价模型原文、程序采用、可读结果，8例未达预期不进入M5。当前只是固定预期/授权，尚无M4.5执行或通过结论；旧M4不通过及候选限定ACCEPT保持原范围，OS后置、5/15、不部署/提交/push不变。

## 2026-10-23 M4前批独审：直接合同限定通过，真实矩阵功能门失败

最新授权继续逐步推进M4，前批M3限定ACCEPT仅证明其当批版本与接缝。M4.1a/M4.1b/M4.2依次完成11/13/12项直接测试，版本及失败/修正见[主回执](../../../docs/operations/unified-investigation-implementation.md)。未参与实现的audit_contracts对M4.1b及M4.2最终均给出**限定ACCEPT、0剩余必须修项**；接受固定候选程序采用及持久模型gate合同，不外推真实模型或整个M4。

M4.1b审阅指出assurance与validity混用，已修后13项复测通过：finding为rule_checked/current，assessment为model_assessed/current。所核evidence_view SHA256 `3d32a65d87e11d4b75ce79d2bbf49b1aefb6f3f7975b4a9791b05e53bb472837`；analysis_adoption为`02b429762e2b0e21bfef8ea2af843e56c571e10405635ece4a44da01047c810f`，测试为`253dae6b411e2cbe6265a7e471108663df8c0346cab071fbf03894ee97f214ac`。

M4.2复用safe_ainvoke observer核实际出站预留、恢复前原reply及同complete留存，12项/0.277s通过；旧no-bypass七项直接调用通过，原contract及测试未改。execution_models SHA256 `c1ccbef026005261736e73092466f3e503843b13471cf9144165bee230b27818`，测试为`15f865a5ab4daae04a2d92a08215dfe84b80bb0e6fb01a682f3c64a096269b4e`。审阅保留完成事务中第二次取消可能留下reserved/_active的限制，保守交接且无自动恢复保证。上述直接测试真实HTTP/DB/模型均0。

M4.3沿同stage 8model/0tool/20000tokens/max_unsettled1、DB begin后180秒执行，cost cap None且无估价保unpriced。实际7responded/committed、15042tokens、7unpriced、0unknown/0unsettled；七份answers均object而合同要求list，程序全部以answer_limit拒绝，**M4功能门失败**。第8原reason仅analysis_ExecutionRejected，剩4958<需6790为按状态/冻结输入/预留规则离线推导；实际reserve前阻止、无请求、未扩额，完整8例/指令隔离及整体质量不能宣称通过。PG21事件/36工件独立读回hash/bytes/eventrefs通过，旧Run状态/计费列未改，专用PG角色NOLOGIN及撤权完成。不能用M4.1b/M4.2纯合同或新prompt候选ACCEPT替代原M4失败。详见[主回执](../../../docs/operations/unified-investigation-implementation.md)及[M4 JSON](../../../docs/operations/unified-investigation-m4-20261023.json)。

M4.3准备新增的6份衍生样例在新Run `eb431eb2-6c62-5b61-8178-ae1b14580b0f`先保存6事件/6工件并独立核对；19文件模型前冻结manifest保留不覆盖。首次run命令在CreateProcess前被自动审批拒绝，当时模型0且无started标记；补充合成来源和既配目的地证据后，同一原命令重审获批准，未绕过审批。模型失败原文/采用/用量完整保留。

独立审读原回复还发现focused整体assessment、把5分钟写成1分钟、错误冲突predicate、空/缺源的空refs肯定finding，以及execution未知写failed，不能把失败简化为数组形状。M4.4仅澄清prompt、不变采用合同，13项/0.316s和8份prompt离线合同检查通过；7原reply回放与保存采用结果一致、仍全失败，真实新模型0。新源码hash `767c6e94cdd5d3aaafc344f5d93e5844c041162f9de1311a152fad289ae44c80`，测试hash `d4f34776c1e765cd39b13fecf3f5f65c733de45109de19f9814e1cd174b6a236`；audit_contracts对该候选限定ACCEPT/0必须修，原M4不通过及第8未测保持。

audit_contracts最终明确：**M4本批不通过，修订候选限定ACCEPT/0必须修，真实复测未做。** 未见越界恶意/授权/完成定论，不替代有用交付；combined/focused均结构失败，暂不能择优或宣称成本优势。费用cost_complete=false，不能把已知费用小计0称为0成本。

当时提出新Run最多8次/30000tokens/180秒的复测预算选择，pending期间未新发模型或建身份；此为历史事实。用户后续明确测试累计tokens不限且持续修复复测无需逐批确认，已覆盖该待选事项，不再要求新确认；按顶部M4.5每Run 20000tokens/180秒推进，不采用原30000提案或重置旧批。未过M4不进M5，OS后置，5/15、旧失败/unknown及不部署/提交/push边界保持。

## 2026-10-23 M3阶段结束独审（前批限定ACCEPT）

本批按M3.1→M3.2→M3.3小步推进，25项测试及一次真实HTTP结果见[主回执](../../../docs/operations/unified-investigation-implementation.md)和[M3摘要](../../../docs/operations/unified-investigation-m3-20261023.json)。审阅发现两项问题已修正：M3.2 scope重复嵌正文改为单份原文工件与refs，随后真实PG4项通过；M3.3未知参数先持久的问题改为reserve前schema required/properties校验，新增拒绝secret/sql键的第9项后9项通过。不能将最初8项通过当作该问题已被覆盖。

真实回执为1query/1match、3events/6artifacts、独立PG读回hash/UTF-8/event refs通过、0真实模型；临时API已停，PG专用角色已NOLOGIN并撤回三表及Run UPDATE(id)授权，旧CH reader保留。Run状态/计费列不变，测试Run running非最终调查完成；程序tenant条件不等于数据库硬tenant沙箱。

未参与实现的`audit_contracts`已只读核最终state/store/wrapper及9项测试源码指纹与实测版本一致，复核JSON/SQL/probe代码、独立PG连接工件hash/UTF-8/event refs和清理回执均passed，结论为**限定ACCEPT、0剩余必须修项**。完整源码指纹见M3机器摘要，接受范围仅为M3有限模块和一次真实M2接缝，不覆盖模型、完整调查或正式发布。M3限定实现/测试完成后停止，M4/调度/M7 manifest/M8入口及读取projection/OS后置；无部署、Git提交推送，原5/15及历史失败不变，不归档整体change。

## 2026-10-23 M1/M2首工具阶段结束独审（前批）

未参与实现的`audit_contracts`分别复核M1纯范围/版本政策合同及M2 API/受限caller，结论均为**限定ACCEPT，0本批必须修项**；接受范围是本批有限网络来源观察的程序合同与查询接缝，不是模型判断、恶意/授权裁决或完整统一调查验收。主回执见[逐模块实施记录](../../../docs/operations/unified-investigation-implementation.md)。

复核依据为D1/D2/M1/API/caller各8项共40直接测试、旧工具51兼容正常exit0，D2真实3行字段/hash、D3一告警/2消息与精确关联，以及M2真实5次HTTP查询（2匹配3空，含子毫秒边界）和4认证拒绝。caller越scope在HTTP前拒绝；泛API只有认证tenant及全局bound，Run持久scope/M8接线后置。大正文、去重/冲突及上限属于直接测试证明，未冒充额外真实数据验证。pytest挂起exit1、缓存权限及历史unknown保留。

本批M2审阅/实测/当前文件hash一致：caller `services/agents/app/tools/activity_records.py` SHA256 `312a4d243b867e43b454fc79a22c0d7c41124a9915088e369d224607dbf6f971`；API `services/api/app/services/investigation_records.py` SHA256 `add5e5f3053606a59823b47dda9b7b4d31af10a3cb23a8483379d2995dfad937`。`m2-runtime.json`确认临时API已停、临时token随进程失效；writer INSERT已撤回，reader与本批合成资料保留，未改旧账号或row policy。本次收口OpenSpec1.13.0 `validate restore-alert-investigation-integrity --strict`及`git diff --check`均通过，CLI仍5/15与R02 0/17；不以格式校验代替上述验收。

当批停止于M2首工具，M3持久/额度、M4模型、统一调度和实际Run入口尚未实施接入，OS后置。无模型、部署、Git提交推送，原5/15及旧失败保持；不归档整体change，也不把局部ACCEPT外推为剩余任务完成。M3后续事实见顶部；下文M0未放行是后续数据补齐之前的历史结论。

## 2026-10-23 M0来源盘点与工具数据规划结束独审（历史阶段）

未参与本轮编写的audit_contracts只读审阅工具数据规划、M0回执及相关Git/源码，给出**限定ACCEPT，0项本轮必须修订**；仅接受来源盘点与待讨论方案，不构成M0放行或M1实施验收。另由m0_source_map/search_backends分别核最新main测试工具和检索后端，均未业务访问或改源码。用户最新要求涉及工具方案先讨论，故当前首场景/工具数据范围未定，M0尚未放行；不会绕过该门槛实现后续代码。

本批主方案[工具数据建议](../../../docs/architecture/investigation-tool-data-plan.md) SHA256 `c698c0945376d4fbe38867f6a0726544c8f098b77a3d368f9bf4c7721bc221f2`；[逐步记录](../../../docs/operations/unified-investigation-implementation.md) SHA256 `2a3cfb65d17794c9ff3c8aeaeff3f2db6d6d63c90556d661f7e28f84086c5c70`。两份文档12处本地链接及36条表格数据行结构通过、来源JSON可解析且明确M0待讨论；git diff --check通过。OpenSpec1.13.0在调查worktree执行`validate restore-alert-investigation-integrity --strict --no-interactive`有效，list仍5/15、R02 0/17；新增M1规格是目标而非已交付。

真实新增检查仅为测试tenant中旧合成湖事件的只读核查：15字段/1行，外联字段缺失。沙箱阻止及本轮探针UUID别名错误/修正均保留于回执；未把它归为旧network_connections根因。无新业务数据、模型、部署或Git提交推送；下方v3原hash与当时CLI未发现记录保留为历史，不追认旧失败。

## 2026-10-23 调查规划v3文档修订结束独审

root修订主文档、示例与交接入口，audit_integration只补design/execution本轮记录；未参与本轮编写的audit_contracts与audit_practicality分别只读审阅v3增量及相邻合同，均给出**限定ACCEPT，0项本轮必须修订**。前者核两维判断/范围、模型模式、预算、发布和七项意见落实；后者核材料信任边界、小模型负担、首场景验收及仅文档授权。两者均未改文件、运行业务/模型/测试或访问生产。

审阅对象为[调查模块规划设计v3](../../../docs/architecture/investigation-planning-design.md)，SHA256 `1deac54a5cfc3d764b2ec601c7993949d006060166f6e36a50365446e059e194`，695行。审阅后主文内容与该hash保持；第15节历史ACCEPT只作原范围记录，不代替本次审阅。首场景仍draft/source_unverified，恢复专项后置，接受范围仅为本次设计修订一致性和合理性，不代表来源可用、模型效果、实施或上线验收。

root另做静态校核：主文26处本地链接、1段JSON、24张Markdown表、代码围栏、修改段新增链接及冲突标记检查通过；git diff --check通过，原tasks与HEAD内容一致，仍5/15。变更限于7份Markdown设计/审计/交接文件，没有业务源码或规格变更。当前Windows环境未找到OpenSpec CLI，因此未执行本轮strict，也未安装工具；此次为文档修订，后续实施前仍须按项目要求完成strict校验。

工作树为`E:\aisoc\socai2\.local\worktrees\investigation-working`、分支`codex/investigation-working`、基线`3fa4be3`。PROGRESS普通写入曾被本机文件权限拒绝，随后获准完成相同文档写入；没有因此修改权限或扩展业务操作。Windows原分支未提交工作留原处；未启动M0来源核实、业务/模型测试、生产访问、部署或提交推送，旧失败与unknown保持。不另存设计旧稿副本。
