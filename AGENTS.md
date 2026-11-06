# 调查数据库 V1 与人工确认

2026-11-06，项目负责人已确认告警、事件和调查的 PostgreSQL `socai2` 表设计形成初版。V1 以迁移 123–126 为基准，共 29 表、462 列。[字段字典](docs/design/socai2-field-dictionary-20261103.md) · [部署用建表脚本](deploy/database/init_socai2_v1.sql)

此后任何表设计变更（包括新增、删除、改名，以及字段、类型、默认值、空值规则、键、约束、索引、表关系或隔离规则的调整）都必须先走项目的 [OpenSpec 变更流程](openspec/README.md)。在变更记录中列出原因、涉及的表和字段、对既有数据及页面查询的影响，提交项目负责人逐项或按明确范围**人工确认**，记录确认人、日期及获准范围。确认前只可提出方案，不得修改正式表设计或实施迁移。测试通过、自动评审、一般性的“继续推进”均不能替代这次人工确认。获准后使用新的增量迁移，保留 V1 原件。

# 调查测试的本机运行记录

调查用例跑完并取得落库快照后，使用 `docs/operations/update_processing_audit.py` 将该批实际记录更新到本机 4177 页面。每次独立测试使用独立批次标识，保留已有批次；按存储的 Run 和步骤展示实际输入、输出、错误与空态。具体命令见[运行记录页用法](deliverables/investigation-validation-20261106/README.md#调查运行记录页)。

# 2026-11-06 本轮数据与测试材料提交远程授权

用户明确要求将本轮修改、测试结果、字段对应清单及剩余问题/下轮部署模型计划提交到远程。沿origin/codex/case-baseline-history-20261103，基线5eacb314；本次包含126页面数据增量、共用存取/导出、原页字段绑定、三组追加测试与四数据合同样例、F01—F28、OpenSpec及限定审计，并将原核验ZIP逐字复制到deliverables/investigation-validation-20261106供远端下载。见[发布范围与待办](openspec/changes/complete-socai2-investigation-chain/publication-20261106.md)。

当前累计63/69、19/26及模型质量未通过保持。发布不启新模型/数据库/部署，不合并main；私密配置、API Token与较早tools/model-preflight工作保持本地。下文和包内“未提交/未上传”是各批原快照，最终提交推送结果以Git与远端核对为准，不回写历史证据。

# 2026-11-06 追加三案测试与字段功能交接

用户要求继续测试并同步核数据/页面/字段对应，已追加local-eval-20261106-01/02/03，真实Kafka/Fusion/PG/CH/DeepSeek合计15调用，累计63/69，三案C6均保存。01/02的C3分别领域发现范围/补查对象范围拒收；03格式通过但效果扩大，三案整体语义质量仍未通过。旧原答/失败保持，不用剩余6次试探，部署模型留下一轮。

48次只读GET、674项比较、557原页面数据检查及87视图通过；入湖/原件逐值、当前结论/成员/图谱/执行工件关联可查。13本机模型批次与4无模型合同样例分列；F01—F28列功能→DB字段→读取→原页及空值/未接线。Case历史1条baseline与页面4条含A/I需聚合、活动混合计数、decimal编码和证据索引未生成已交代。见[统一交接](docs/investigation/investigation-test-handoff-20261106.md)和[索引](docs/operations/evidence/additional-tests-20261106/test-index.json)。

本轮只新增有界测试入口、回查脚本/材料和原页数据引用，为加载126代码重启本机API；不改模板、提示或执行逻辑，不连VPN、不新增DDL、不清历史、不提交推送。校验器最初包装/元数据正文比较及数字字符串问题保留，修后用原件复核。19/26不变，模型质量/完整3.12/4.1/4.2不核销。以下为各批当时状态。

本批独立结束审计限定ACCEPT/0剩余必须修，模型语义仍未通过；见[回执](openspec/changes/complete-socai2-investigation-chain/additional-validation-review-20261106.md)。1272文件、约10MB本机交接ZIP已CRC/逐文件SHA及页面本地依赖核对，初包漏Logo目录已修且保留初包；未含已知运行凭据、未上传，见[打包回执](docs/operations/evidence/additional-tests-20261106/package-receipt.json)。

# 2026-11-06 页面数据增量与独立交接

按用户继续推进实施D1—D3：126增加Case分类/期限/当前证据索引指针，复用工件存版本、活动存变更；当前判定复用已采用结论，共用读取/导出处理证据和威胁计数。实际本机29表462列，4案8告警为明确合成合同测试、0Run/0模型；14案含10旧案列表/详情一致，4模型/3系统/3legacy当前判断可读。原模板仅改字段/缺值/五态判定绑定，四样例和旧案例结论已浏览。见[数据交接](docs/investigation/socai2-page-data-handoff-20261106.md)与[公开回执](docs/operations/evidence/page-data-20261106/summary.json)。

来源校验初审指出标签/分析提升和伪造处置回执，已按登记路径、冻结角色及成员范围修复；补unknown/conflicting显示。独立结束复核限定ACCEPT/0必须修，21后端/24前端定向通过。最初PG导出UTC字符串不一致、兼容验证取值错误及测试fixture错误均保留原因，修后只读复核。模型质量与完整3.12/4.1/4.2不核销，19/26、48/50保持；没有重启常驻API、VPN/远端动作或本轮提交推送。以下为各批当时状态。

# 2026-11-05 当前调查审计修复与剩余容量问题

当前分支codex/case-baseline-history-20261103，直接更新既有文档，未新建工作树。用户现已授权提交并推送当前进度至origin同名分支；不合并主分支、不部署，C6剩余额度问题保持未闭环。A01已加125增量函数迁移：按冻结成员材料/triage/feedback、事件诊断/成员、已完成H语义检查输入新鲜度；采用前stale_input不覆盖，Case读取返回input_freshness，标题/负责人等元数据变化不误判。29表459列不变，125只应用21既有隔离验证库，业务库/常驻服务未更新。A03明确400/422 Schema拒绝失败收口、ended_at及释放Run，未知用量保持；超时/其他不确定仍unknown，旧记录不批改。独立小模型Compose绑定vllm_grammar_v1，DeepSeek覆盖standard，预检校验协议/profile；原配置保持。A04补明确SHA256及冲突/遗漏。A05按冻结对象选C2来源，保存选择依据，仍给C4留2次/总4次Tool。

A02仅部分修复：C6必带事实/时间/H/原计划/有效比较，A/I参考整组可省略且留账，不拆同次评分判定理由；C3再分析原规则保持。3固定包22/22/23必需项零遗漏、视图7943/7966/7894B，但完整请求16527/17262/17939B分别超过原usage后的13458/9314/13274B，仍model_token_budget_insufficient，不能说整链通过。共享预算仍24000/4模型/3000输出，未重置usage、删必要值或重派已结束批次。下一先解决C3/Deep/C6容量分配，再固定候选同步独立服务和新批真实验收。

52纯检查与18个不同隔离PG方法最新通过（模型/湖/背景返回替身）；初离线测试调用签名错误、完整wire暴露预算问题、首H测试角色缺用户ID权限均留说明，H定向复核通过。证据见docs/investigation/current-investigation-audit-20261105.md及fix-validation-20261105T023329。124写点/57源指纹已重建。当前执行账本、README、主设计和OpenSpec原位更新；不写并行设计版本。3.7/4.1/4.2未勾选，Q501，旧r13/5.3不核销。无新真实模型/业务湖查询/生产变动；本轮不是结束独审。

# 2026-11-05 当前执行账本作为流程说明唯一入口

实际记录入口docs/investigation/current-execution-records.md：从固定数据库原件只读生成26Run/162Step/361工件目录、关联记录数与4结果/0采用，校核输入输出同Run、原件hash保持；取数2026-11-05 00:13:44UTC，非本次在线刷新。生成器Ruff字符串括号7项修后过；不可把失败/unknown/pending索引说成完整成功验收。

用户明确不要反复旧/新及批次对照，只要当前每一步输入输出、每个Run/调查执行及数据库修改。主入口改为docs/investigation/current-execution-ledger.md；121写点/57源指纹在current-database-write-catalog.md/json；current-execution-readback.sql按tenant/case/run只读查输入、所有Step/工件、成员版本、发布/采用/活动。C1—C6同一baseline Run；A/I单独Run；Deep只有子步骤；H版本不建Run，Q501。逐项列事务及自动采用条件，partial可采用、仅查范围/成员/当前判断时点，不额外复核所有材料/H变化；无通用SQL前后镜像。当前独立Fusion入口未装配外围检测/session/AI资产等，不能把通用main所有可选分支写成必经步骤。

仅文档/离线提取器；Ruff修首轮5项后过；15 SELECT方言/字段静态核对，事务包装解析器不支持未验证、整行to_jsonb限定器用alias.id验证别名；121写点/57hash/135链接核对。无业务改动/DB执行/新模型/远端部署/提交；OpenSpec13/16及3.7/4.1/4.2继续待。批次证据另存原处，不再作为当前流程入口。

# 2026-11-05 Kafka双模型整链已实测，新增40条湖上下文通过查询，完整结论未通过

当前入口docs/investigation/kafka-to-conclusion-validation-20261105.md，含Kafka→Fusion→A→I→Case C1–C6→H/Q的输入/处理/写表/模型、具体例子、页面字段和差距。用户要求复用既有数据构造，已使用tools/testdata的确定身份/时间/JSON/hash/答案分离模式，新增context_fixture.py。k4在4个原Case周边生成40事件（28范围内、12控制），经独立真实Kafka/Fusion写socai2_next_validation.raw_events；18正式LakeGateway查询事件ID全集精确一致，4Case各进程2/网络5/认证2，2空Case全0；96流量计数与来源路径一致。无新告警/Run/模型，原PG计数/保护配置保持，临时INSERT-only角色已撤；新材料.local/testdata/k4-context-20261105，摘要docs/operations/socai2-context-k4-20261105.json。traffic投影仅本地及真实诊断进程验证，未同步常驻API；不得说此前模型已见新日志。

n14已部署独立API，550应用文件核对，验证镜像从硬编码n1改为manifest.image；对照后恢复DeepSeek Flash，旧服务/模型配置不替换。k1同主机使两后端归并成3事件，0模型即停；k2隔离主机后12告警/6事件/6Case/26Run记录，26模型请求（DS14/9B12），23原答+3HTTP400，无重试，已知106851tokens、3错误usage未知。A11/12发布，I5/6发布；4DS基础Run失败，3小模型unknown及1pending。0有效Case结论、4系统交接结果，完整验收未通过。小模型C3明确uniqueItems语法拒绝，已有vllm_grammar_v1未启用，非参数量结论；C6三轮必要输入预算不足发生在调用前，原件重建确认属于输入装配设计；活动成功被扩大和引用范围问题仍保留。14不同executor PG方法最新通过（模型/湖替身，5回执，非首轮全过）。

独立读回发现LakeWriter两SQL硬编码aisoc.raw_events，k1/k2共16合成事件误入旧湖。已逐ID/租户/完整OCSF核同原计划、留回收前材料后精确删除16条；不能仅因配置指纹保持而称旧湖未动。已本地修配置库名及标识符验证，26writer测试过；k3用只有新湖权限的临时writer走真实Kafka恢复16条，新库各1旧库0；k4同样旧库0。修复尚未进入常驻n14/原Fusion镜像。原件位于evidence/socai2-kafka-chain-20261105/{lake-correction,k3-lake}。

下一先同步湖路由/计数投影及独立小模型兼容profile，再修C6必要输入与明确400状态；使用新批次复验最终C/H第二C与模型实际消费补查。旧k1—k4及m1—m4均结束不重派；无生产A/I调度新增，Case手动单活跃、Q501、无页面/DDL/预算提高。OpenSpec13/16，3.7/4.1/4.2未完成，旧r13/5.3不核销；无提交/推送/新工作树。下方n13未部署/m4待授权为历史，已由本条取代。

# 2026-11-05 新增Kafka起点整链与双模型验证，m4兼容检查已完成

用户新增明确要求：从Kafka读取告警开始，展示各阶段输入、处理、写表、输出和模型职责，增加合成测试覆盖完整调查及分支，对比DeepSeek和本地模型。该新增测试要求授权本轮必要的有界模型验证；不再沿用之前仅“网络恢复”时的m4待授权状态。已按原固定包执行m4一次通用Schema请求，无重试，返回通过实际解析和Schema校验，816tokens；原服务/网关/配置指纹保持。见docs/operations/socai2-schema-probe-m4-20261105.json。m1—m4均已结束不重派，m4只证明协议兼容，不代表调查质量。

下一以独立Kafka主题/组及现有新PG/CH空间准备实际消费验证，明确自动、测试驱动、用户手动触发。此前r1—r6从Fusion writer和CH夹具开始，不能称Kafka全链通过。核对n13后仅更新独立新服务；同一组新合成材料进行双模型比较，保原件、真实覆盖和替身分支验证分开。Q继续501，Case仍手动单活跃，不新增生产调度、不动原消费者。测试计划/材料/调用上限先固定，语义按良恶反向误判与可接受needs_review分别评价。完整验收、结束审计及归档仍未完成。

# 2026-11-05 网络恢复，5项隔离PG最新通过，C6预算回归修复并固定n13

用户明确网络恢复后执行原5项：首批20261104T231938为4过1失败（完整DeepSeek协议C6 model_token_budget_insufficient，无C6调用/采纳），角色隧道清理。只读导出本批单个失败合成Run ae80c287-f73f-4a27-bf76-41d00d144390 的步骤和50工件，本地重建确认必要计划加入后，继承C3再追加C6提示使最终请求18871B>原17744B。未改原Run/回执或重派它。

仅改baseline_delivery_contract.PROMPT为独立C6规则，合并重复说明，去掉C3的1800目标、保C6原2200目标和3000硬上限/原总预算。必要4计划、保留事实、来源map、输出Schema逐值保持，最终17657B≤17744；用户数据仅省略原因计数变化。两个中间仍超限版本与原失败保留。新增1离线回放检查过，原44复用，45不同纯检查最新过；元数据初打印遇content_json=null已修选择，未改工件。

定向20261104T233152两方法过：test_final_original_followups_survive_new_reanalysis_proposal和test_full_deepseek_wire_c3_deep_c6_preserves_saved_requests_and_budget，后者C3→Deep→Deep→C6/4模型替身、请求保存一致/原预算，另外3方法复用首批通过。5不同方法最新通过，非一次首过，模型湖替身，真实质量未验。两批角色隧道清理。见docs/operations/socai2-followup-pg-20261105.json及docs/investigation/socai2-m2-followup-fix-20261104.md末节；不再等待网络恢复或重跑5项。

n13在.local/releases/next-20261104-n13固定621文件/550应用，tar31ec3ae4411a…、manifest1e980c01c5ba…；较n12仅C6提示+镜像标签，包字节/hash/0644核验，n12/m2/m3保持。未上传部署，线上最近n9。m4额外1次仍待明确授权（本次答复仅网络），协议未改，原m4包不重做/不先行调用；授权后schema-only upload/preflight/run/export一次无重试，再新候选真实A/I/C/H/第二C。OpenSpec13/16、独审归档待，Q501和旧r13/5.3保持；不提交推送、不建工作树。

# 2026-11-05 后续项声明与C6原计划关联本地修复，n12固定，PG因21超时尚未开始

用户继续后修S03/S04：C3/C6 followup对象须属于声明成员的冻结对象并集；原Case/来源校验保持。新baseline_followup_projection按routing.initial_analysis_artifact_id和followup_index读取原计划，检查索引覆盖/唯一/模式/问题；原建议required、精确来源路径且去旧source_ids，执行状态单独receipt。C6最新再分析建议与原执行计划分开，相同原计划不重复输入；guard/单项/总预算或剩余额度不够明确跳过，不删必要计划后猜测。不改Deep整案问题/binding范围，不自动建H。

A/I/C共用217B活动语义约束，说明success只限定action、启动非完成/授权、连接非外传，已知端点与未知外传分开；followup正文限制声明范围、C6区分completed/answer_available/handoff。未加关键词判真、DDL、页面、调度或记忆。44不同本地检查最新通过：初23过1冻结夹具赋值错误，修夹具后1+18过，另2guard/总预算过；四m2固定材料只替提示，消息均≤12288B、原用户值保持。Ruff/OpenSpec/diff过。详情docs/investigation/socai2-m2-followup-fix-20261104.md末节与docs/operations/socai2-followup-fix-20261105.json。

已选择隔离PG executor 5方法（新2+回归3），首个SELECT current_database预检失败，直接SSH确认192.168.1.21:22超时。0方法开始/角色创建/数据写入，不是审批拒绝；已异步询问网络恢复。恢复后沿verify_socai2_store_20261103.py --suite executor --only：test_final_original_followups_survive_new_reanalysis_proposal、test_final_oversize_required_plan_does_not_call_model_or_adopt、test_full_human_graph_and_no_need_skip_external_queries、test_full_deepseek_wire_c3_deep_c6_preserves_saved_requests_and_budget、test_full_no_model_or_rejected_initial_yields_system_handoff。模型/湖替身，不消耗m4。

n12在.local/releases/next-20261104-n12固定621文件/550应用，tar bf4f2b7f0850…、manifest746e5eec008b…，较n11仅8应用+镜像标签；原n11/m2/m3保持，未上传部署。m4额外1次仍待授权，协议未改、固定包不重做；不能把“继续”当扩展调用额度。n9线上/r7未启/OpenSpec13/16，PG/真实整链/独审归档待，Q501及旧r13/5.3保持。不提交推送，不建工作树。

# 2026-11-05 剩余语义及执行范围已本地核清，未新增调用或业务修改

用户“继续分析”后，沿m2原件和当前代码复核I/C3/H/Deep/C6。见docs/investigation/socai2-m2-followup-fix-20261104.md末节及evidence/socai2-semantic-boundaries-20261105/local-audit.json。原m2目录30文件hash保持；2原答当前解析器仍接受，4离线改写反例明确非模型原答/采纳。I有process_start+success且F2引用，却表述“脚本执行成功”，不是字段漏传；C3写进程启动，但两者使用冻结历史前序，不能称实时纠错。人工建议只声明A0却询问A1网络授权；当前human仅handoff不自动建任务/关闭/确认。insider目的地缺失措辞与已知端点冲突属含混，不计良恶反向误判。

新增明确设计缺口：followup object_keys只校验全Case，不核所选成员，离线A0建议挂A1目标IP仍接受；C6丢routing.followup_index，原建议是可省略prior候选，同问题同模式状态会失去稳定对应，原工件仍完整。六问题Deep均冻结整案scope，按question去重且Tool受固定binding约束，不能误称全案补查本身越权。正式H对显式结果范围/对象校验、版本冻结和不向新增成员扩散保持。

待实施最小顺序：用已有alerts.objects核声明；C6绑定原initial_analysis_artifact_id+followup_index与成员/执行状态，区分最新再分析新建议；再精简补活动成功/建议范围/已知端点语义规则并测预算。无新表需求，不加关键词判真/记忆/调度；未修改业务源码、DDL或页面。脚本Ruff及本地审计通过；初只读输出因Windows未设置UTF8报错、rg文件通配语法错误，修调用后完成，未写原件。

m4单次兼容实测仍待新增授权，不将“继续分析”当许可；m3已结束不可重派。n11固定、n9最近线上、r7未启、OpenSpec13/16及真实C/H/第二C/独审归档待。旧r13/5.3及Q501保持。不提交推送，不建工作树。

# 2026-11-04 m3实测结束，DeepSeek可空引用已本地修复，n11固定、m4待新增1次授权

用户明确允许m3后保存user-authorization，固定包hash核并upload/preflight/run/export完成；2请求/2HTTP400/0原答，0重试，usage两条未知。canonical 0.661秒报anyOf分支missing type；type[object,null] 0.167秒报object不在多type支持列表。7远端JSON/请求intent hash核、CRLF→LF包hash核，原四服务/新容器/网关/原env/DeepSeek profile指纹保持。0业务Run/Tool/采纳/部署。m3初审批拒绝已解除且保留，本批结束不得再run或等待m3许可。见docs/operations/socai2-schema-probe-m3-20261104.json。

据此仅改model_protocol的DeepSeek发送层：计量/持久化前展开anyOf本地ref，保留完整type/required/enum/范围/长度/additionalProperties和null分支，普通refs保持共享，小后端/规范Schema/解析器不改；缺失/循环/非本地/兄弟约束拒绝。33既有+11新纯检查过；A和完整C3→Deep→Deep→C6两个真实隔离PG方法过，模型湖替身、实际发送/保存逐值一致、预算原值。初Ruff新测试一处导入格式已修，角色隧道清理。无DDL/页面/模型配置变更，不声称真实兼容或质量已通过。

n11在.local/releases/next-20261104-n11固定620文件/549应用，tar7f0dfd8f6d09…、manifest8329b0505cc2…；较n10仅8应用路径+镜像标签，含前轮I优先级/错误留痕。tar逐文件hash/0644/应用字节/敏感文件名核过，未上传部署，n10保持。明细docs/investigation/socai2-deepseek-union-fix-20261104.md及同名operations JSON。

下一m4已本地固定1条修正后Schema-only请求，generic消息与m3一致，仅分支表示按实际prepare_request变化；512输出/120秒/一次无重试，无业务材料。目录docs/operations/evidence/socai2-schema-probe-20261104/m4，目标21:/opt/sting-aisoc-socai2/evidence/next-schema-probe-20261104-m4。已异步问允许新增1次，待答复；原因是用户m3明确2次额度已用完，不是原审批仍阻止。不得执行第3次m3或先行m4上传/调用。允许后probe_socai2_schema_m4_20261104.py upload→preflight→run→export，prepare不可重跑。线上最近n9、r7未启，OpenSpec13/16、C/H/第二C及审计归档待；活动成功/后续范围语义、小C3时限仍待，needs_review可接受口径保持。

# 2026-11-04 m3输出格式诊断已固定，上传待明确授权（历史，已授权结束）

用户“继续”后准备schema-only m3：仅当前A字段Schema/通用JSON/N1_S1及安全错误留痕代码，不含告警/事件/Case材料。DeepSeek两条固定请求：当前anyOf(ref DecisionBasis,null)与约束等价的type[object,null]内联，仅此处不同；每条一次、0重试、512输出/120秒，不做业务判定。官方Responses文档不足以确定400关键字，nullable仍是假设。三项本地检查通过（等价边界/固定child一次错误去凭据/请求仅一处变化），runner/child编译及Ruff通过。

固定目录docs/operations/evidence/socai2-schema-probe-20261104/m3，目标21:/opt/sting-aisoc-socai2/evidence/next-schema-probe-20261104-m3。上传命令被自动审批拒绝：新增私有代码/Schema载荷及目的未被m1/m2授权覆盖；命令未执行，0上传/预检/真实模型。已异步询问允许本批2次及范围，尚待答复；不得绕路用本地token或其他入口执行，不把等待当授权。见docs/investigation/socai2-schema-probe-m3-20261104.md；原拒绝另存。允许后沿probe_socai2_schema_m3_20261104.py upload→preflight→run→export，prepare已固定不可重跑，run最多一次，失败先导出不重派。

本轮未改业务代码/配置/DDL，线上最近n9，n10冻结、r7未启、m1/m2已结束。43纯/5PG前批修复证据复用；新3项是离线诊断检查，不是模型效果。误判/needs_review口径保持，OpenSpec13/16及C/H/第二C、最终独审/归档待。

# 2026-11-04 用户明确误判与待复核口径

用户澄清仅良性→恶意、恶意→良性计方向性误判；良性/恶意→needs_review可接受，单列待复核率，不算确定判对。无独立真值的样本不计准确率/误判率；m1/m2两合成成员的9B结果应称无充分依据的良性定性，旧“误判”用语按本条更正。待复核仍须事实/引用/范围正确，HTTP失败和拒收不算待复核，也不自动改写坏答。OpenSpec规格/验收计划及m2报告已同步此决定，旧请求/原答/机器回执保持。继续修m2内部缺口，不重试结束批次、不改页面或模型配置。

本轮已完成m2后两项本地修复：I先保核心行为/有效同次分诊/时间，再各成员detection，再可选背景；固定输入检测组1→2、7926→7966B仍≤8192，共享原值保持，其他省略按来源留痕。新增model_errors仅捕获httpx错误、有界提取去凭据code/type/param/message，A/I/C3/Deep/C6保存raw=null的执行回执与未知usage，沿原unknown、不重试/不覆盖旧判断。无DDL。43不同纯检查最新过（41首批+错误模块新增2后10过，33复用），5不同PG方法最新过（新3方法含C三路径+2回归）；既有隔离PG真实、模型湖替身，角色隧道清理。初guard夹具错误及Ruff导入排序已留说明。见docs/investigation/socai2-m2-followup-fix-20261104.md及同名operations JSON；m2全部原证据/脚本hash保持。

Deep A400具体参数仍未知，不能把错误留痕称协议已修；role不证明授权、活动成功语义/后续项范围、小C3时限归属仍待。0新真实模型/湖/部署，线上最近n9、n10冻结不改、r7未启；新代码未打新候选。OpenSpec13/16，完整真实C/H/第二C、最终独审及归档未完；下一先有界定位A协议再新批质量验证，不重派m2、不改共享配置。

# 2026-11-04 m2授权实测已结束：拦截改善但整体未过，n10/r7保本地

用户明确答复“允许本批m2按此范围验证”后已保存user-authorization并执行8次固定请求，0重试；5完整原答/Deep A两HTTP400/小C3一HTTP408，22328已报tokens，3失败usage未知、费用未定价。5答wire及canonical Schema有效/0截断、程序仅接受Deep I/C3两份，不等于质量全过。0业务Run/Tool/采纳/部署；原四服务、新容器、原api.env/网关/DeepSeek profile指纹一致。19远端JSON，8bodyhash相同；整包/runner CRLF→LF差异归一化核对。m1原38证据hash保持，原审批拒绝留原但本批授权已解除，不再待答复。

9B两A仍benign/.95标签推授权：A0新增decision_basis门拒，A1主直接依据与新门均拒；模型判断未改善。离线反例仅删A0依据中的标签、保用户名/主机名与同一错误授权主张，会被解析器接受，说明role门不是真值证明；原答不改不采用。小I待核但重复N1_S14拒收且无据声称两成员共享用户；Deep I待核通过但把进程启动成功写脚本执行成功。Deep C3两成员/六问题/四待定领域及关联通过，但human followup仅A0范围、目标含A1连接授权；insider“无目的地”也须区分已有连接端点与未证外传。时间+observed例外这份新答未触发，仍仅离线验证；正文编号warning真实A因Deep400未验。

新缺口M2-D01：Deep A0/A1 0.176/0.182秒400，I/C3同入口成功；标准Schema及refs有效，但runner未存HTTP错误响应体，具体参数未知。nullable DecisionBasis只是候选，不能写已定根因；下一先补安全有界code/param/message留痕再定位，不重试m2。M2-D02为角色不证明授权。M2-D03：I从31到33项，新增进程class_uid/两条ocsf.time，预算却省略网络detection整组，原库/冻结材料仍有；内部投影优先级缺口，非上游问题。M2-O01：小C3 45.136秒408，窄49秒窗内有litellm.Timeout，未找到数字timeout配置；确切时限来源待查，不改共享网关/不加预算。不能称9B C3兼容/质量已过。

明细docs/investigation/socai2-model-evaluation-m2-20261104.md及机器回执docs/operations/socai2-model-evaluation-m2-20261104.json。4评估脚本Ruff最新过，诊断脚本成员键/Path实参初错误已修，失败说明为工具输出转录非原始完整日志。业务代码未改，原56纯/11PG证据复用。m2结束不可run/prepare/重派；n10仅固定候选，r7不执行（已知A请求失败，整体验收未过）。下一先解A错误留痕/协议及I检测字段优先级、复核定性边界，固化新候选新批后再全C/H/第二C。线上最近核验n9，OpenSpec13/16、3.7/4.1/4.2待，Q501、旧r13/5.3保持，不提交推送。

# 2026-11-04 用户要求验证：m2/n10已固定，m2上传待明确授权（历史，现已授权执行）

本轮“进行验证”后准备m2：A0/A1/I/C3当前合同各双后端共8次、每格一次无重试；与m1相同r4/r6冻结合成材料/前序，不用m2 A替换I/C前序，0业务Run/Tool/采纳。小后端显式vllm_grammar_v1仅移uniqueItems，Deep standard；wire与canonical Schema分别校验。新脚本docs/operations/evaluate_socai2_m2_20261104.py复用m1传输，不改旧脚本/原件。包在evidence/socai2-model-comparison-20261104/m2，packet sha a7c4ff29e8d5…、runner dedf6985acc3…已固定，prepare不可再运行。

upload+preflight命令被自动审批拒绝：m1授权不自动扩展m2，冻结告警/事件/Case材料到192.168.1.21需本批明确授权。命令未执行，0上传/远端/模型；已异步问“允许本批m2按此范围验证”，待答复。原拒绝保存authorization-block.json；答复另存user-authorization，不绕过、不开替代传输、不把等待当同意。授权后沿m2脚本upload→preflight→run→export→review；8次结束不重派，原答逐项人工核质量。m2期间独立n9容器只作传输，不能部署导致指纹变化。

等待期间完成本地n10候选.local/releases/next-20261104-n10，619文件/548应用，tar57154adb58f9…、manifest e0da3474eddb…；逐字节/0644/无凭据及原修复代码hash核，19路径较n9变化（17应用+compose+验收驱动）。新增prepare --image仅作用新候选，原源compose不改。r7驱动已准备：关闭r1–r6仅export，新键/新Case/原材料核对，A/I后首C，语义通过才H及第二C，理论最多11模型/5业务Run，原额度不增。6驱动检查通过；初m2 unused import已修Ruff，5脚本静态通过。未上传n10、未部署、未启动r7。

见docs/investigation/socai2-contract-validation-plan-20261104.md。下一先处理m2待授权，不得重跑prepare或直接派发。线上最近核验n9，本地v4、OpenSpec13/16、Q501、旧r13/5.3保持。不提交推送、不建工作树，原配置/凭据保持。

# 2026-11-04 m1后设计合同已本地修正，未部署或新增真实模型

用户“继续”后修正14个业务Python文件及工件合同：显式SOCAI2_MODEL_SCHEMA_PROFILE默认standard，vllm_grammar_v1仅发出前移uniqueItems，保本地去重/范围检查且不重试；A/I/C3/Deep/C6来源用输入文本不存在的N前缀，原历史正文保持，字面名豁免限确切原名。新A/I structured_v3以结构化数组作正式引用，合法本轮正文编号仅warning，不从正文补引用；未知/跨成员仍拒绝。A新增decision_basis种类/主张/直接引用门，needs_review为null，标签或旧判断不能独自定性，但仍不证明自然语言主张为真，不能称9B误判解决。

C observed可附本成员确切alert.event_time时间上下文但仍须活动观察及逐成员覆盖；领域适用性与相关finding分开，非适用/未定须限制，新领域工件写applicability。运行/设计/字典三份JSON合同同步analysis_block.applicability及model_exchange.schema_profile可选属性，旧缺失不推算；无DDL/ORM，仍29表459列。准备视图v4、grouped-input v3、A/I executor v3；Deep/C6共享新编号。原预算/页面/Q501/消费者/模型配置保持。

最新56纯检查（新增13参数化场景）、11不同PG方法通过：A4/I2/C3两方法（含15负例）/完整执行器2/C6历史对比1。既有socai2_schema_review_20261103_a1真实PG事务，模型湖替身；角色隧道全部清理。初夹具/断言、编号扫描UUID序列化及两处工件属性Schema漏同步失败保留，不能说一次全绿。m1原件hash保持，Deep C3旧答按新规则不改字解析仅合同诊断、不采纳。固定材料体积A0 4988/A1 5864/I 7926/C3 7946B，I/C必需内容和同次分诊完整，原8KiB及总预算不增。20文件Ruff、三合同一致性和OpenSpec strict通过。

明细docs/investigation/socai2-m1-contract-fix-20261104.md，机器回执docs/operations/socai2-m1-contract-fix-20261104.json。0新增真实模型/湖查询/部署，线上最近核验仍n9；本地v4未发布，m1/r6结束不重试、不改旧失败。下一固化新候选及明确新批，显式核小后端profile兼容/新定性质量，首C合格后H→手动prepare/start→第二C；再结束独审/归档。OpenSpec13/16、3.7/4.1/4.2待，旧r13/5.3保持，不提交推送、不建工作树。C多错误诊断/Deep进一步筛背景/专用覆盖DTO/大Case分批仍未实现。

# 2026-11-04 m1真实两后端对照结束：输入缩短，9B误判未改，确认自身合同缺口

用户明确授权m1合成材料上传21、最多12次后执行，初拒绝及user-authorization原件保留，不再待授权。12HTTP尝试/11完整原答/1HTTP400，无重试；已报37506tokens，失败1次usage未知/费用未定价。11答均符合发送Schema、0截断，当前解析接受7份但不等于语义通过。0业务Run/Tool/业务采纳/部署/DDL；旧四容器、新服务标识、api.env/LiteLLM/DeepSeek profile指纹保持。remote导出27JSON，12请求canonical body hash一致；整包CRLF→LF导致filehash不同已单列。

两A旧/当前各双后端：9B均benign/.95，仍把Synthetic/fixture/测试域名当良性授权依据且四答全被解析器接受；DeepSeek均needs_review，A0 .4→.45、A1 .4保持。旧A1 Deep写HTTPS，当前正确TCP；当前Deep两A因正文/结构化双份引用未齐而拒收，A0“受管”也无据。I两者总体待核，9B覆盖not_reviewed/已有分析矛盾及引用拒收，Deep通过但null窗口不应说无窗口。I/C前序是冻结历史Deep判断，不能称9B完整链纠正。

C3小后端0.162秒400，精确3秒网关日志确认Grammar error: Unimplemented keys uniqueItems，是请求Schema兼容设计问题非模型能力。Deep C3完成两成员/六问题/四领域，2233输出tokens；观察发现附source_label时间S22/S23被拒，离线只移这两时间引用后暴露待定领域finding链接不符（发送Schema允许、本地禁止）；内存再去链接才解析通过，不改原答不采纳。另确认历史理由旧S14与本轮tcp的S14碰撞，旧分析出现S1会错误触发literal-name豁免；非缺数据/截断/需要记忆库。

详见docs/investigation/socai2-model-evaluation-m1-20261104.md及docs/operations/socai2-model-evaluation-m1-20261104.json。m1结束不可再run/重试；6评估脚本Ruff最新通过，离线诊断packet选错初失败保留。本轮未改业务代码/提示词/原配置。下一优先修后端Schema子集（本地唯一性不放宽）、单一结构化引用/历史编号隔离/字面名豁免、时间上下文与领域条件，再补良性/授权定性依据门；用固定原件本地回归后另批真实C→H→第二C。线上仍n9、本地v3未部署，C3真实请求不冒充完整链验收；OpenSpec13/16、Q501、旧r13/5.3保持，不提交推送。

# 2026-11-04 m1准备阶段历史：上传曾被自动审批阻止（现已授权并结束）

用户继续后准备m1：两条A各旧/当前输入×两后端8次，加当前I/C3×两后端4次，最多12次一次不重试。复用隔离租户r4/r6合成材料、冻结前序判断，不建业务Run、不查询Tool、不采纳、不动原服务配置；只评当前C3，不冒充完整Deep/C6/H/第二C。旧A来自实际r4请求，当前A保留全部旧可见字段值；数据字节5594→4870、6455→5743，I7934、C37874。6组双后端messages/schema/temp/上限相同，Schema/guard/原预算检查通过。

本地包docs/operations/evidence/socai2-model-comparison-20261104/m1/plan-and-packets.json hash4b3cb4b70664…，runner hashf016f665662c…；三个评估脚本Ruff最新通过，旧A两原答离线解析检查完成。初UTF8/C2选错工件/静态问题留记录。上传+元数据预检命令被自动审批拒绝：本批冻结材料与21目的地缺明确授权；命令未执行，0上传/远端/模型/DB调用。已异步问用户是否允许该明确范围，等待答复；不能绕过或将等待当授权。

见docs/investigation/socai2-model-evaluation-m1-20261104.md。答复后沿evaluate_socai2_models_20261104.py upload→preflight→run→export，再review_socai2_model_evaluation_20261104.py及语义核对；prepare已固定不能重复，run写唯一intent不可重派。原审批记录留原，答复另增回执。线上n9/本地v3、OpenSpec13/16、Q501、旧r13/5.3不变，无业务代码/部署/提交推送。尚不能声称新版9B已测试或质量改善。

# 2026-11-04 模型对比补核：旧版两条A同输入，新版未回测9B

用户追问小模型测试、大小模型差异及精简对结论的影响。本轮仅核历史原件、生成docs/operations/socai2-model-comparison-20261104.json（脚本compare_socai2_models_20261104.py），0新增模型/服务/DB调用。r3网关上游自报Qwen3.5-9B；r3/r4两条A的messages、Schema、strict、temperature=0、3000输出上限逐项相同，原答均从9B benign/0.95变DeepSeek needs_review/0.4。每模型每样本仅一次，网关Chat与直连Responses协议不同，不能当全流程或通用能力证明；I/C输入及前序判断不同。

最新n9精简后只真实测DeepSeek r6，没有回测9B；本地43纯+6驱动/16PG使用替身，不是小模型效果验证。r5→r6 DeepSeek两A原答判定仍needs_review，A0自报置信度0.4→0.45且均未采纳，A1保持0.4；I总体仍待核。C v3仍仅本地，无最终Case结论可比较。不能声称精简已改善小模型或对结论完全无影响。后续验收应补当前同合同/同冻结材料的两后端对照，并分开内容质量、引用、采纳状态；不重派旧批。n9线上/本地v3、OpenSpec13/16及原边界保持。

# 2026-11-04 输入精简n9已部署，r6未通过，C计量修正仅本地

用户“继续推进”后实现无损分组、必需字段/同次分诊优先、独立时间引用、A/I覆盖与分层校验、I背景引用约束及C3/Deep/C6提示精简。独立n9镜像cb3a317537a3…、548应用hash核对，旧四容器/原配置保持；无DDL/页面/消费者修改，29表459列、deepseek-flash及原预算不变。候选.local/releases/next-20261104-n9-final，最初n9目录为未上传的静态修订前草稿。

r6固定批已结束且未通过：A0正文S20/S21/S27/S28实际可见但未配对结构化引用而failed；A1/I completed，旧A0成功分诊保原来源。首次Case f0f4bcb1-6b00-5bb4-880d-a7e6c4b08574 / Run bcca5931-6522-4dbb-8bbc-dfd3da5e017f在C3前停止，准备视图把审计引用计模型额度并丢第二成员时间，整I诊断对象也超限；C无模型、无有效结论，H/第二C未执行。合计3模型11380tokens/未定价、7实际PG Tool；原合成材料逐行保持。原件最新092702-r6-export，不重派r6，不改历史失败。

随后仅本地补C v3：与C3实际序列化共用计量，完整引用账本单计；有效I投影完整summary/conclusion/limitations且优先；固定六问题重复规则复用系统提示，修改/自定义问题不删；共同limitations组头化；必需内容失败coverage为partial/unavailable。读兼容v1/v2/v3，预算未提高，r6原件回放必需内容可完整装入8KiB。线上仍n9/v2，v3尚未打包部署。

本地最新43纯+6驱动、16不同PG方法通过（不是一次全绿），保旧断言/驱动导入、C6预算、时间引用白名单及r6容量失败。见docs/investigation/socai2-compact-input-fix-20261104.md、docs/operations/socai2-compact-input-fix-20261104.json及socai2-next-r6-validation-20261104.md/json。C多错误诊断、Deep进一步按问题筛背景、专用覆盖DTO、大Case分批仍未实施。下一固化v3并核A0双份引用负担，另立新批验证C→H→手动第二C，随后结束独审/归档；OpenSpec13/16，3.7/4.1/4.2仍待，Q501、旧r13/5.3保持。不新建工作树、不提交推送。

# 2026-11-04 先精简输入，参考开源小任务设计，方案待实施

用户要求思考解决方案，追加“输入能否精简，参考之前AI SOC怎样让小模型输出”。本轮仅设计与离线排布，不修改业务/DDL/部署/模型配置。开源固定版本7份源码LF Git blob匹配1G导入；浅层摘要/任务字段/短输出有价值，宽松解析、默认判定及上游小模型循环/无据编造不能当质量保证。详见docs/architecture/opensource-investigation-implementation.md第7节。

真实固定r4/r5 I输入仅把重复成员/角色移到组头，所有原items逐值可逆、检测字段未删：7860→6232B、7960→6406B；补回原漏传764B分诊后7136/7310B，仍低原7936B预留线。回执docs/operations/socai2-compact-input-measurement-20261104.json，脚本measure_socai2_compact_input_20261104.py通过Ruff；0模型/DB调用，原快照hash保持。是字节排布实验，新增可见性字段/最终提示/guard未验，不声称质量通过。

唯一当前主设计4.3–4.4已整理修法：阶段必需组优先、判定理由评分同次完整；可用/可见/存储完整/分析分开；I事件背景仅顶层evidence_ids、成员来源严格归属；合法且有结构化对应引用的正文编号仅warning，未知/错配/越界仍阻断；分类诊断一次记录可检查错误。29表459列无需新增DDL，版本化artifacts与读取DTO承载；C3仍六问题/四领域但减少重复，C4按问题、C6最终综合，不增Agent/调用/预算，不建记忆框架。OpenSpec设计/规格/执行已同步，13/16保持；实际代码仍n8、r5止于A/I，后续先实施上述输入与校验再新批验收，不重派旧操作。Q501、旧r13/5.3保持，不改原LiteLLM/凭据，不提交推送。

# 2026-11-04 用户要求先辨明设计与模型根因，n8已部署，r5止于A/I

用户最新强调不能把问题笼统归因模型参数量，需辨明自身设计/实现与模型错误。已停止追加真实调用，收取已发出的r5三次A/I，转固定r4+r5共7份原件的离线归因审计；0新增模型/DB调用。主结论docs/investigation/socai2-deepseek-root-cause-audit-20261104.md，机器回执socai2-deepseek-root-cause-audit-20261104.json及citation-scope明细。

确定自身问题：D01发出Schema允许单finding冲突、后置要求2，n8已对齐但真实C未验；D02 I丢进程分诊原因为view_size而非guard或模型漏读，原投影764B、guard双层均false，原数据在库且冻结有效；D03 triage_usable=true不等于实际进入模型，material_state=complete不等于完整审阅；D04正文编号错误阻断整个分诊，r4A1/r5A0离线只停这一规则便过其余解析，不等于语义合格；D05 r4I额外scope错误是两处引用S19=$.parent事件背景且alert_ids=[]，不是引用了另一成员进程；D06只返回首错遮蔽后错。P01 r5A0请求有pattern且供应商回显同Schema，输出却违反pattern，不能假设strict覆盖所有关键词；M01 r4A1 TCP443写HTTPS是确切语义越界，r5该样本已正确保留TCP/未知。7答均未截断，不能归因参数量或输出预算耗尽。当前reasoning.effort=none是自己的运行选择，非模型能力上限评测。

当前线上n8，镜像ed071567296d…，manifest ea5e81d8c128…，546应用hash核对，075720-start确认旧四容器/原api.env/LiteLLM配置保持。r5 A0 a5af51cf-b3a5-5aad-9142-6e4579cd0f36因正文编号failed，A1 887897a0-658e-52f3-8ef4-2de6b2902abf与I 0727d3ef-beca-5eab-9504-ce35425b36ef completed。r5未建Case、无C/H/第二C；证据075920-r5-export。不能因两个completed称质量全过，I输入分诊缺口仍在。n8检查28纯+6驱动全过，C3 PG 15反例通过（075302回执）；原n7 PG4方法复用，非再次全部重跑。

下一先整理并修输入必需字段/取舍/实际可见性，明确事件背景引用与成员证据边界、格式/引用/事实错误分层；用固定7原件离线验证，再立新候选和固定验收批，不追加提示或换模型碰结果。不能把离线反事实移除标签当正式删检测字段方案，也不能线上关闭引用校验。原DS凭据保持新0600profile，start必须--model-profile deepseek；不重跑configure、不打印token、不改原LiteLLM。OpenSpec13/16、质量/独审/归档未完，Q501，旧r13/5.3保持；无新提交推送。

# 2026-11-04 DeepSeek已接独立服务，r4结束；n8/r5准备中

用户改为指定本机dsapi.txt凭据、官方https://api.deepseek.com、deepseek-flash，要求原配置不改，并询问LiteLLM。已回答原链路是新API→共享LiteLLM→自报Qwen；现在仅独立新API直连DeepSeek Responses，原API env/LiteLLM配置及旧四容器核对保持。凭据只经SSH stdin写21新0600 model.deepseek.env，原api.env字节保持；新增Compose overlay，start必须显式--model-profile deepseek，不重跑configure-deepseek（已存在保护）。dsapi.txt已精确gitignore，禁止打印/入候选/证据。

当前线上n7，镜像1abe67cf1b17…，546应用文件核对，073915-start回执；本机及容器/models均200且包含deepseek-flash，0探测推理。小适配把实际Responses body在预留/持久化前构造，原回复原样保存，usage按供应商字段读；默认chat路径保持。显式reasoning.effort=none、max_output_tokens3000、无供应商工具/重试/JSON弱回退，原120秒/24000tokens上限保持。协议18检查最新通过（17首过+1冻结配置测试夹具修后过），部署6检查、受影响真实PG A/I/C3/完整执行4方法通过（模型湖替身），见docs/investigation/socai2-deepseek-adapter-20261104.md。静态sys导入遗漏与lambda警告已修；原记录不覆盖。

r4已结束：同2告警2湖事件核对后复用，新Case5033c555-58d9-5bf6-b7fb-9e44dbd529c1；4真实DeepSeek调用18379tokens，均reported/unpriced。A0 needs_review通过程序，标签非授权/空查询非反证已改善；A1/I因正文来源别名拒收，A1仍将TCP443写HTTPS；C3因单finding冲突拒收且把选定字段读取夸为完整读取。首次Run118ff4a2-e943-476d-90cb-547edb38e7e4 failed/system_only/null/partial，未H/第二C/Deep/真实湖/C6模型。最终证据074438-r4-export，机器汇总docs/operations/socai2-next-r4-validation-20261104.json。

n8在本地修复：Conflict.finding_ids最少2且Schema uniqueItems，与原解析器已有条件对齐，四份C3/C6运行/设计schema同步，无DDL；提示区分未决/实际矛盾、选定字段/完整读取与端口/应用协议。A/I已存在正文别名禁令加入请求Schema，允许真实原值本身叫S1等例外，不删原答或放宽校验。28纯检查全过，6批次驱动过；一项C3 PG反例回归正在执行（14301会话）。r5驱动已准备，旧r1—r4仅export，尚未派发r5、尚未部署n8；下步完成验证/固定n8再保原DeepSeek profile启动，固定同样本新批。

当前主目录/分支不变，无提交推送。OpenSpec13/16；真实质量/结束独审/归档仍未完，不能把切模型或HTTP200算通过。Q仅501，旧r13/5.3仍保持。下方记录均为历史时点，不再等待ergouzi。

# 2026-11-04 n6/r3结束未通过，待配置获准的新模型

继续在主目录codex/case-baseline-history-20261103直接开发，HEAD 39f4033未新增提交/推送。当前独立服务n6镜像95c987cc66ef…，545应用文件核对，21 localhost:18020；PG socai2_next_20261104（29表459列）、CH socai2_next_validation、Redis13不变，旧四容器保持。下方n4/r1是历史时点。

n6修复C3在初始分析前按冻结material_id读取必要原字段、I成员轮流优先行为字段、A/I省略明细有界；添加同合同JSON Schema与显式temperature=0；C6原剩余额度不足时压缩可选输入，必需目录不足仍停止。原预算/表/页面不变。18纯检查和9不同PG方法最新通过，执行器初2失败/定向复核保留；模型湖替身不冒充真实验收。详见docs/investigation/socai2-model-input-projection-20261104.md与socai2-structured-output-20261104.md。

r2/r3均已结束，原输入复用且原失败不删。r3四模型14666tokens/4未定价、7真实PG查询，四答符合记录的provider Schema但语义不通过。A0/I内部来源别名被拒；A1结构接受并保存但错误用示例地址/来源标签推无风险，程序未拦住。C3完整2成员6问题4领域，却以单finding构冲突而拒收，并有无据因果/缺源当不适用/预算跳过当未接通；Case仅system_only/null/partial，未采用。无Deep/真实CH/C6模型/H/第二C。固定明细docs/operations/socai2-next-r3-validation-20261104.md及.json，最终快照070415-r3-export/database-20261104T070419.json。

模型只读元数据自报Qwen3.5-9B，5 alias同后端。用户已授权使用ergouzi API，尚缺入口/已有配置位置，以及“用户所给字符串”是模型名还是token值的确认；异步问题已发，不重复索要密钥、不猜地址发凭据。未修改远端模型配置。本地r4驱动已准备，r1/r2/r3仅允许export；5离线驱动检查通过。新模型确认后只改独立新服务私有配置，再固定新候选/新批，保持原样本/预算/旧判断历史，不动共享网关或原服务。H和第二C须首C有效且人工语义核对通过；不因completed自动核销。

OpenSpec complete-socai2-investigation-chain仍13/16，3.7真实质量、4.1结束独审、4.2归档未完。Q仅501；旧r13/5.3暂停且未完。当前没有新的独立最终审计结论。

# 2026-11-04 独立新服务已运行，真实质量验收正在修复

用户要求持续完成并验收，随后明确“不替代原版，单开服务”。主目录/分支保持codex/case-baseline-history-20261103，不建工作树、不提交推送。OpenSpec complete-socai2-investigation-chain当前13/16；H/prepare 21方法、必要来源12新+2回归最新通过，固定summary为socai2-human-tasks-20261104.json及socai2-external-sources-20261104.json。保原失败与受限PG回执。C3局部发现不再继承整案object_keys；C2原4工具额内留2给C4；产品当前快照source_label不当活动观察。

新服务socai2-next-api已部署n4，21 localhost:18020（本地SSH转发同端口，/readyz ready）；PG socai2_next_20261104含socai2 29表459列和17支持表，CH socai2_next_validation.raw_events，Redis13，无旧Kafka消费。镜像d93be0aa125f…，544应用hash核对；旧四容器ID/镜像/启动时间一致，旧业务/凭据不导出。身份key仅21私有目录。部署工作目录、METRICS_TOKEN、健康探针三个错误已修，n1/n2失败保留；n3只候选，最终n4回执051835-start。

真实r1固定2合成alerts/1incident，由实际Fusion writer入PG；CH loader首失败仅1行，已按缺失eventID单独补第2行，18字段逐项匹配，两条告警不重写。原始CH错误原因未知，恢复回执seed-lake-second-row-recovery。真实HTTP无权401/只读写403/读200通过。A0/A1各1模型技术完成但语义不通过（用Synthetic/fixture标签推良性/授权、A0 TP与benign矛盾，A1内部编号泄漏）；I一次模型因limitations null/string形状拒收且语义亦不合格。3已知调用9189tokens/未定价，原件052345-export。C首次Run a6288c08-b8f5-4881-83d6-d69e9e61986c（Case ebcaf41a-54ba-59cd-a70b-a0689226e726）C2完成、C3外呼45秒后unknown/503，无response/usage，原因待诊断；原件052706-export的最新database-20261104T052710.json。H/第二C未执行，r1不重派；不得把ready/completed当质量通过。

当前继续修A/I判定含义、元数据角色及严格输出合同；root本地给C3补安全异常类别/阶段留痕（n4未部署该新改）。修后固定新候选和新operation批验证，不重写r1或释放其unknown槽冒充成功。独立审计未通过/未归档；3.7、4.1、4.2仍待。Q仅3个501预留、页面不改，旧r13暂停/5.3未完。C当前判断是领取时冻结判断，covers_current_members仅成员覆盖，不保证后来材料/H新鲜度；新反馈须用户prepare/start。下方历史不能覆盖本段。

# 2026-11-04 显式事件关联与Case成员移动完成

本轮在主目录codex/case-baseline-history-20261103完成OpenSpec 3.4：显式事件关联/创建与完整成员并集、双Case移动、幂等、两端版本和有序Case锁、同事务pending/活动已接。只增链接不改范围/Run，目标已有成员不建多余pending，旧C1/Run/结果不改；空Case不能启动，下一pending仍手动。Case详情增显式链接目录。

审计补124单列cases.source_namespace，绑定后不可改，旧明确范围才回填；29表459列，123保持。Fusion的fusion.v1是身份空间，不能当原始来源环境，未提供的环境按输入限制不猜测。迁移只在21原独立合成库，aisoc业务库/生产/页面未动。25字段/4例见docs/investigation/socai2-case-relations-20261104.md。

12新+7回归最新通过，6批受限角色/隧道清理，真实PG事务/并发/MVCC可见性，模型湖仅旧回归替身；首4夹具必填缺失和1测试误读manifest失败保留，定向修复复核。无真实模型/湖/新容器/部署/提交推送。当前11/16，下一3.5 H人工任务写读/版本引用，再来源/迁移/真实验收；Q仅预留，r13暂停、5.3未完。下方历史不覆盖本段。

# 2026-11-04 告警/事件页面字段读取接通

主目录codex/case-baseline-history-20261103完成OpenSpec complete-socai2-investigation-chain 3.3。新增page_contracts/page_reader与socai2_pages的8个GET模板，SOCAI2_PAGE_READ_ENABLED默认false；认证租户/alerts:read，Case目录另核cases:read。主字段及明确派生类型、当前材料/配对分诊、对象/来源/台账资产/关联/评论/准确主体活动/响应引用、A/I步骤用量及正文可读。独立只读快照，GET不写时钟/匹配；事件人工等级与成员最高级分开，首次活动min(event_time)，业务更新时间取事件/成员最大值。分诊score与本次判定配对并核有效性，原厂未知null；基础运行统计只计baseline冻结成员，unknown单列，分页不缩统计/用量。

73项字段明细/4例见docs/investigation/socai2-page-reader-20261104.md，OpenAPI为docs/design/socai2-page-reader-v1.openapi.json。成员关联Case和显式事件链接分开，活动不串共享Case；资产当前精确匹配带依据，不冒充持久身份确认；响应只有稳定引用，外部审批/执行实时状态仍待接。主体列表只固定分页，交互筛选/排序/导出/管理由页面/业务负责人实现。表/迁移/ORM/公共枚举不变，旧public链不回退。

8新+2PG回归最新通过，另Q预留3个ASGI检查/18子场景通过；4批既有独立合成PG，角色/隧道已清理。首7项2过5失败，均为夹具必填/引用约束或Decimal/已有他租户数据预期，修后定向5过；随后补类型/有效性和原型待分配总体口径，3受影响+1新增检查通过。原失败/回执保持。6个业务/测试/runner文件Ruff通过，core/config三项历史lint未扩修。无新容器/DDL/真实模型/湖/厂商/生产数据/页面/部署/提交推送。当前10/16，下一3.4事件Case关联/移动事务，其后H/来源/生产迁移和真实验收。Q仅留接口，旧r13暂停/5.3未完。下方历史不覆盖本段。

# 2026-11-04 I事件诊断执行接通

主目录codex/case-baseline-history-20261103继续完成OpenSpec complete-socai2-investigation-chain 3.2。新增incident_diagnosis_executor/contract及StageResultService.execute_incident；同一SQL快照冻结完整成员及分诊有效性，completed来源Run/current输入/材料配对才进模型，过期/旧无来源Run分诊保原件但不进正文。旧I快照保持旧合同，新快照附triage_validation版本/映射，C1/只读出口均兼容，不回填历史。完整成员目录必须保留，逐成员及跨成员来源校验；正式诊断复用原Finding结构，无公共JSON/DDL/ORM/枚举变化。

I固定1模型/0外部查询/24000tokens/120秒，原8192/2048/12288字节及3000输出不增；请求先提交，原回复/用量/成员覆盖可追踪。诊断/未决/采用/父阶段/Run同事务发布，输入变化只入历史，failed/unknown同步诊断尝试；相同operation_key不重派，不改成员判定、不重复A查询、不启动C。生产消费者未接、页面未改。

9新+5受影响回归首次通过，5批既有独立合成PG，SQL/事务实际、模型替身；全部受限角色/隧道已清理。初次Ruff闭包绑定/导入/规则提示已处理，业务无失败回执。见docs/investigation/socai2-incident-diagnosis-executor-20261104.md（32字段/4例）和docs/operations/socai2-incident-diagnosis-20261104.json。29表458列/迁移123保持，无新容器/真实模型/湖/生产数据/部署/提交推送。OpenSpec当前9/16，下一3.3完整告警/事件字段DTO和逐项页面对照，随后关系/H/来源/真实验收；Q仅留接口，旧r13暂停/5.3未完。下方各批是历史。

# 2026-11-04 A告警基本查询与分诊执行接通

在主目录codex/case-baseline-history-20261103完成OpenSpec complete-socai2-investigation-chain 3.1。新增alert_basic_executor/contract及StageResultService.execute_alert，单告警冻结→资产/同对象24小时历史/内部TI实际SQL→一次模型→同次分诊/Explain，实际请求返回/步骤/usage可追踪。服务端1模型/3查询/24000tokens/120秒/200行，原8192/2048/12288输入上限和3000输出不增；默认截止时间仅首次事务生成，同operation_key不重派。未知事件时间不补NOW而跳过历史，原始字段/标签/旧判断/人工反馈分角色，模型来源别名仅指实际可见值。新增同Run已完成Tool返回引用校验和精确数组路径；原模型回复/用量未知保持，非法输出不覆盖成功分诊。

请求提交后才外呼，发布分诊/解释/父阶段/Run同事务；过期/较新结果保护、人工状态不改。无模型或无有效答复保失败尝试，取消/调用/提交不确定unknown，不自动重试/关闭/创建Case。原29表458列/迁移123/公共合同保持。服务器内部入口已接，旧消费者和生产未切换，现有A/I GET可读结果，完整步骤/调用DTO仍待3.3。

9新+5受影响回归最新通过，见docs/operations/socai2-alert-basic-20261104.json及docs/investigation/socai2-alert-basic-executor-20261104.md（28字段/4例）。首9项测试夹具跨租户事务被RLS拒绝，修夹具后8过1多Run测试驱动45秒超时；增加测试驱动时限并补字段路径guard后定向3项通过，业务120秒和预算未改，原10失败保留。4批既有独立合成PG，三类SQL真实、模型替身；受限角色/隧道清理，无新容器/DDL/真实模型/湖/业务库/页面/部署/提交推送。静态括号/未用导入已修，6文件Ruff通过。下一3.2 I事件诊断执行，随后DTO/关系/H/来源/真实验收；Q仅留接口，旧r13暂停/5.3未完。以下是前批历史。

# 2026-11-04 在主目录直接分支开发，按OpenSpec推进

本轮Q仅预留发送/保存答复/采用结果3条POST与最小类型，已注册但正常请求统一501；Case开关仍默认false，沿用cases:write及用户主体，不查询Case或执行业务。3个ASGI方法首次通过；新测试两处Ruff格式问题修后5文件检查通过。OpenAPI在docs/design/socai2-case-ai-reserved-v1.openapi.json，说明在docs/investigation/socai2-case-ai-reserved-20261104.md。新change strict通过，tasks为7/16、剩余9项，不能当全链完成。下一3.1是A实际执行适配；不恢复Q业务。当前文档链接无缺失，旧功能复盘37处历史引用另列execution记录，不据此重建工作树或扩修旧页面。

用户明确要求不用工作树、直接分支开发。当前唯一开发目录为E:/aisoc/socai2，分支codex/case-baseline-history-20261103；本任务的两个.local/worktrees目录已注销，后台、最新设计及页面预览315文件已逐字节迁入，262个原未提交文件另有.local/workspace-backups/direct-branch-20261104备份。另一会话functional-analysis工作树未动。不要重新创建本任务工作树，历史“兄弟设计树”指向已失效，当前主设计为docs/architecture/investigation-planning-design.md。未自动提交、推送或部署。

用户要求使用OpenSpec；本轮活动change为complete-socai2-investigation-chain，按其proposal/specs/design/tasks推进。AI问答具体实现暂缓，只保留明确未实现的接口；不执行模型/Tool、不伪造成功或生成Run/答复/结果。A/I执行适配、页面数据DTO、事件Case关系、人工任务、外部来源及真实质量验收按任务清单继续。已完成组件保留既有回执及失败；旧r13报告修复仍暂停、5.3未完成，不借新change核销。下文历史批次不覆盖本段最新范围。

# 2026-11-04 A/I只读接口与C1新鲜度接通

新增stage_inputs共享原SOURCE_SQL；freshness比较进入C1原单条快照查询，数据库比完整JSONB只返回current/stale/unverified/unavailable，原文不塞C1/模型。新冻结只给模型current的同次分诊和成功accepted诊断；过期正文/限制留账本，旧冻结Run不改，新字段有兼容默认值。新增stage_reader/read_contracts及4条/api/v1/socai2的alerts/incidents analysis GET，alerts:read、认证租户、默认关闭SOCAI2_ANALYSIS_READ_ENABLED；REPEATABLE READ READ ONLY，当前指针与有效性分开、全状态双键分页、同Run Explain hash/大小/128KiB核对，不返回原文/内部键/blob地址。

7新读取检查+6受影响回归最新通过。首轮UUID参数类型导致5失败，CAST修后4过1测试断言错误（raw_json引用路径误当原文）；定向修断言通过，原件保留。受限独立合成PG/ASGI，身份替身；无真实模型/湖/业务库/新容器/DDL/页面/部署/提交推送。20字段/4接口/3例docs/investigation/socai2-stage-reader-20261104.md，OpenAPI和可兼容C1 schema同步设计树；29表458列/公共合同不变。下一实际A/I执行适配及请求回复/步骤用量、完整页面DTO/事件Case关系/H/Q/外部来源；旧r13暂停/5.3未完。以下批次按历史时点阅读。

# 2026-11-04 A/I输入与结果存储已接通，执行适配仍待

新增stage_results/contract服务器内部服务，begin冻结A材料/对象/反馈，I完整成员/归并依据/同次分诊；Run/input同事务提交，I另有running诊断尝试。finish保存同次分诊/Explain或诊断/未决与回执，校验引用/角色/范围；输入变化或较新启动结果已采用时仅入历史，失败/unknown保尝试不覆盖成功指针。旧分诊不能标observation，人工状态不改，告警→事件锁序保持。freshness只读一致快照已提供，C1仍显式freshness_not_revalidated，下一须接读端。28字段/4例见docs/investigation/socai2-stage-results-20261104.md。

10不同合成PG检查最新通过：首9项过，新增输入快照分诊引用后Case桥接+1角色检查定向通过；无业务检查失败，2角色/隧道已清理。受限现有验证库，无模型/湖/业务库/新容器/DDL/页面/部署/提交推送。29表458列/公共枚举合同不变。业务只在本树，设计主树同步；旧报告暂停/r13不重试/5.3未完。下一实际A常规查询分诊/I诊断执行适配和真实请求/返回/步骤/usage，告警/事件DTO与C1新鲜度接线；不能称A/I业务已上线。旧Agents仍旧表，不能直接替换其记忆/处置/升级调查等副作用。下方批次保历史。

# 2026-11-04 Fusion新表写入与Case衔接已接通

新增Fusion socai2_sink/projection，AISOC_ALERT_STORE_SCHEMA默认public，显式socai2单写、不双写/回退、未部署启用。同事务告警/首次投递快照/不可变材料/来源/对象/事件成员，COMMIT成功才durable。重复同材料不增版/刷新时钟；新材料内容身份增版，旧版重投不回退latest，首行/首快照/人工状态与移动关系保持。初始发生时间未知NULL，first/last取收到已知时间，事件业务时间GREATEST不倒退。规则/ATT&CK/明确Fusion置信度有合同，ML默认分数无计算状态只保原件。归并narrative不冒充事件诊断；A/I结果writer仍待。

RawAlert33字段全存material.raw_json，原日志raw_json.raw_event，原文不塞enrichment背景；FusedAlert20字段保首快照，来源/7主对象及额外OCSF端点明确投影，host/user键及来源namespace隔离。算法只认明确字段，source_refs去重限200但完整收到数组仍在原件，窗口候选保类型/范围/截断。信封与OCSF activity冲突分存。已真实Fusion入库→新Case→C1冻结→原文/C4字段→有界模型视图验证，无模型调用。

9writer/worker+1桥接新检查最新通过，10旧写入/投递本地回归通过；沿原独立合成PG，Redis/Kafka/Fusion引擎部分替身，0真实模型/湖/厂商/业务库。桥接首导入错误0检查、一次固定夹具事件ID冲突保留，修后定向过；所有角色隧道清理，无新容器/DDL/页面/部署/提交推送。53字段明细与4例docs/investigation/socai2-fusion-ingestion-20261104.md，回执operations同名json。原29表458列/迁移/ORM/枚举/通用合同不变，主设计/差距/交接同步，业务源码仅本树。

下一A告警基本查询/分诊/解释和I事件诊断的实际产物写入、评分状态；新告警/事件读取、显式Case事件关系/H/Q/外部来源及真实验收仍待。旧消费者/处置回写依赖public，不能只开此配置称生产可用。Fusion前置输入排除；旧报告暂停/r13不重试/5.3未完。下方“Fusion新writer待接”为历史时点。

# 2026-11-04 新表Case写入、手动HTTP和读取合同已接通

新增CaseService/Reader/contracts及独立/api/v1/socai2/cases九路径，SOCAI2_CASE_API_ENABLED默认false，不改旧路径/页面/部署。认证租户与操作人入服务，public.users仅核id/tenant；创建确定性Case ID+请求指纹，同事务成员/pending/活动，范围变更复用原锁/版本。手动start固定原预算await完整C1–C6后读当前Run，重发不重派，无调度/自动下一轮。GET为REPEATABLE READ READ ONLY同快照；当前判断、历史pending/正式AI、同版Result/详细快照/报告、冻结材料按明确身份读，未知用量不补0、费用分币种/计价版，目录限量有总数/标记；最后记录聚合全部步骤/工件不受截断影响。AI来源答复/对话可读，生成/保存写入仍待。

11新+2回归最新通过，5批现有独立合成PG，认证身份/模型/湖替身；网络首连失败0检查0角色，用户恢复后继续。两轮共4夹具失败原件保留（Run范围/开始必需字段、工件mime/blob_ref类型），修后定向过，非业务约束放宽；原不变通过项复用。回执docs/operations/socai2-case-api-20261104.json，36字段与4例docs/investigation/socai2-case-api-20261104.md，OpenAPI同名json。原29表458列/迁移/ORM/枚举/通用合同保持，所有临时角色隧道清理；0真实模型/CH/业务库/新容器/部署/提交推送。主设计/缺口/交接/入口同步functional-alignment，业务源码只在本树。

下一Fusion告警/材料/对象/来源与事件/成员/诊断的新表writer和字段对照，再显式事件关联Case/移动事务、外部来源、H/Q业务、迁移切换及真实质量验收。当前接口只消费已入新表的数据，生产和页面未切换；旧报告暂停/r13不重试/5.3未完。下方HTTP/读取DTO待接均是历史时点。

# 2026-11-03 统一C1–C6手动执行器已接入

新增baseline_executor及Service.start_full，使用已提交的同Run C1冻结→C2→C3→C4必要字段/按问题Deep→C5→C6。C3 query/deep无可直接执行绑定，交Deep选择服务端B，不猜自由文本SQL；按原序同问题去重，所有需求仍逐条保留。human待确认不建任务，graph仅已有来源图。C1.executor执行计划及C4.routing分配回执用原steps/source_snapshot，最终详细报告execution.followup_dispatch保状态/停止/Deep图关联；工件仅execution_receipt。C6最终综合兼再分析，不另耗一次C3.reanalysis。旧S来源别名从新综合的需求投影去除，原件/引用保持。

持久化executor_version=socai2.baseline-executor.v1决定非C6模型领取预留最后1次调用，C3/Deep/手动再分析均受约束。只是次数预留，没有另设Token/时间池；原4模型/4Tool/24000tokens/120秒/200行上限不增，C2与C4共用Tool。无额度/无初始有效分析/无有效最终答复保系统交接；取消/传输/提交不确定仍unknown占槽。start_full同步执行，返回领取Claim，不是当前Run/Result DTO。相同启动重发不重派，当前范围冻结、下一pending合并且仍需手动启动；无队列/定时领取/自动接续/重试。

10新+6回归最新全通过，6批见docs/operations/socai2-baseline-executor-20261103.json及流程文docs/investigation/socai2-baseline-executor-20261103.md。首8过，旧别名隔离后2项定向复核及2项新增边界通过；其余未变通过项复用。回归C3预算/Deep再分析/C6报告比较原子回滚/提交失败不派发。测试静态未用导入/排序修正后执行，无业务检查失败；独立合成PG、模型/湖/C2返回均替身，临时角色/隧道已清理，无新容器/业务库操作/部署/提交推送。29表458列、迁移、ORM、36枚举、38通用合同保持；主设计/差距/交接/入口同步到functional-alignment，旧批次回执不改。

下一业务writer、手动启动HTTP、Run/Result/详细快照及当前判断读取DTO；没有上线切换，页面不改，外部拓扑/产品主机/认证/UEBA/知识、H/Q业务与真实质量仍待，当前partial。报告修复暂停/r13不重试/5.3未完。主设计仍在兄弟functional-alignment，业务源码只看本树。旧记录下方“下一统一执行器”属于历史。

# 2026-11-03 C6正式交付、比较与原子发布已接入

新增baseline_delivery/contract/projection、Service.finalize及专用输出schema。C6领取同Run唯一阶段，先准备/刷新有来源C5，锁内确认C2完成/C3已尝试，提交请求后最后一次模型同时做整案再分析、结论/closing_note、指定历史比较、Case影响和建议；没有额外写作调用。原全成员/六问题/四领域合同与原额度/guard保持。来源别名必须实际可见；supported结论/影响须逐成员观察或人工陈述，不能仅依图/旧判断/query_binding_only；拒重复/空白/越界/错比较等。建议仅保存，审批unknown，不创建任务/审批/响应动作。

指定comparison_result读取C1冻结结果及不可变旧输入范围，保存新增/移出/共同成员；有历史但没指定基线（含失败未采用、C1没收录的历史）为not_comparable，只有首次无历史才initial。最终影响/发现只声明成员范围，不把Case全部object_keys附为受影响对象。C6发布前再核证据集与图；旧范围结果可保存，但范围过期/较新判断依原函数拒自动覆盖。无额度/有效初始分析/有效最终答复则系统交接，conclusion=null、system_only、无最终成员覆盖，不自动采用；未知用量null。传输/提交不确定unknown占槽，不自动重试。

原29表458列/迁移/ORM/36枚举/38通用合同保持。report_json按原report_result合同，内部预留同一Result ID（公开DTO不加ID）；额外C6来源/比较/用量在source_snapshot，Markdown从同版字段确定渲染并转义。四领域工件、详细快照、JSON/Markdown、Result/member、C6终态及自动采用同事务提交；终态只写一次。Service返回report/detail/markdown三个工件ID与正式result_id，HTTP/读DTO未接。

14新+7回归最新通过，见docs/operations/socai2-baseline-delivery-20261103.json；流程/字段/4例在docs/investigation/socai2-baseline-delivery-20261103.md。首3因Markdown无content_json导致引用校验回滚，原件保留、修后定向过；再完成10项及回归。收尾按旧report_result合同对齐后5项C6和2发布回归过，补失败历史和不扩大对象范围两项定向过；10个输出合同反例、真实延期FK请求提交失败不派发/正式发布全回滚、第四次模型合成流程均验证。10批受限角色/隧道清理，既有独立合成PG，模型/湖全替身，0真实模型/业务数据/新容器/部署/提交推送。专用schema和设计主文/R05/07—09/13/14/字段审计入口/交接/README已同步。

下一统一C1–C6执行器与最终模型额度预留，再业务writer/手动启动HTTP/Result+详细快照读取DTO；当前仅组件接通，外部图/主机产品/认证/UEBA/知识、人工任务及AI问答业务服务仍待，当前为partial，不冒充完整覆盖或真实语义验收。主设计权威在兄弟functional-alignment；页面不改、旧报告修复暂停/r13不重试/5.3未完。

# 2026-11-03 C5来源图与C6剩余字段已核对

新增baseline_graph/projection及Service.build_graph，复用run_steps(kind=graph,C5)和artifacts(alert_graph/source_snapshot)，无DDL/ORM/通用合同变化。C1冻结成员全保锚点，对象按类型/namespace/key/value精确匹配；缺namespace及process/hash/other保局部身份。C4父进程、同记录双端点的network/authentication活动有原字段才生成observed关系，共同对象candidate；PID/session记录内隔离，query节点不直接归告警，配套保存真实事件时间/ID、查询工具/窗口/状态和来源限制。冲突不择值拼边，空查询/缺边非反证，无外部图查询/完整攻击链/影响推断。

Case→Run锁内确定构图、图+快照+步骤同事务；同证据集复用，新增查询另存。构图无外部I/O，失败回滚无需新增恢复状态；其他步骤活跃时拒新构图，旧快照可读。200节点/400边/128KiB、全成员锚点必须保留，可选关系整组限量。C3再分析按prior_analysis读取覆盖当前C4证据集的最新图，旧图stale不输入，底层字段仍observation；原模型/Tool/token/时间/消息预算不增。不发布Result或采用判断。

本批10新+5回归最新通过，见docs/operations/socai2-baseline-graph-20261103.json和docs/investigation/socai2-baseline-graph-20261103.md。首9夹具缺event_time_source被PG拒，修后8处UUID图键序列化失败已修复，原17失败保留；一次错误方法名导致0测试单列不计通过，运行器现拒漏执行，正确test_publish已过。9批受限角色/隧道清理；沿原独立合成PG，无新容器，模型/CH全替身，无业务数据/模型/外部Graph/部署/提交推送。默认沙箱写回执权限不足后经已授权提权保存，不是自动审批拒绝。

C6逐字段确认：结论/来源/校验、交付/成员覆盖、closing_note、比较/变化、case_impact、图/报告关联和采用均有表/合同；缺正式生成与完整编排。下一C6综合/系统交接、跨Run比较、最终图新鲜度和正式报告同版产出，再接完整执行器/HTTP/writers。4次模型可能被C3+Deep+再分析用尽，须预留最后综合或合并职责，耗尽保系统交接，不提高预算。外部拓扑/主机产品/认证/UEBA/知识仍待。主设计/差距/交接在兄弟functional-alignment同步，本树旧主设计非权威；页面不改、旧报告修复暂停、r13不重试、5.3未完。

# 2026-11-03 问题级Deep与补证后再分析已接同Run

新增baseline_deep/contract/reasoning/reanalysis及专用Deep schema，Service.deepen/reanalyze。Deep每Run每冻结六问题之一只领取一次，C4.deep阶段running覆盖模型/Tool间隔；子查询验证同Run/同问题父所有者，C2/C3及直接查询新步骤互斥，读回已结束结果不重派。模型只选本次B绑定或answer/handoff，严格校验JSON/问题/来源，不接SQL/参数。每轮读取实际返回的工具名/主机/窗口/行数/截断，合并冻结C1/C2人工反馈/已有分析与C4观察，保角色、E来源/可见值hash/原件和用量。空查询非反证、host窗口不能直接作成员observed；Deep答案仅prior_analysis。沿用4模型/4Tool/24000tokens/120秒/3000输出，不加预算/自动重试/任务/结案；取消或提交不确定unknown占槽。

再分析C3.reanalysis按材料/查询/Deep不可变工件ID集hash只执行一次，新证据集才新增步骤；记录比较分析ID和实际输入，原C3初始/历次请求答复/领域结果保持。共用原Analysis六问题/全成员/四领域合同，不生成Result或采用判断。字段选取同时计算8192正文和12KiB完整消息（含转义），单项2048/guard不变。原29表458列/迁移/ORM/枚举/38通用合同不变，仅Deep专用schema镜像设计树。

本批10项新检查+9项受影响回归最终状态见docs/operations/socai2-baseline-deep-20261103.json，流程/字段/例子见docs/investigation/socai2-baseline-deep-20261103.md。首9+9过；补查询身份后一个再分析被完整消息上限拦截，已修选取预算（不提高上限），原失败保留；另补冻结人工反馈读取测试并定向复核。模型/CH全替身，PG沿21现有独立合成库，C2来源夹具故意不可用以隔离外部调用；受限角色/隧道清理，无新容器。静态括号/未用导入修复后测试，未部署/提交推送。

下一C5有来源图、C6完整交付及完整编排；产品主机/认证、UEBA/知识/Graph/HTTP和新表writer仍待。当前仅六固定问题与两个湖Tool，不宣称所有开源能力/真实模型质量已达标。页面不改，报告修复暂停/r13不重试/5.3未完。

# 2026-11-03 C4第一批原始字段与确定查询已实现

新增baseline_semantics/evidence_tools/evidence及Service三入口：精确冻结材料读取、显式OCSF进程PID/父进程/命令行/会话和完整网络端点白名单，原标量guard/路径/冲突/遗漏留存，不猜标题或preview。进程/网络新合同socai2.c4-lake.v1固定tenant/冻结host/UTC左闭右开窗口，先去重再限量；旧合同不变不复用。湖无命名空间过滤，相关成员仅查询绑定，不证明逐行归属/因果。Case→Run锁内保存running/request/query_id后提交再派发，同绑定一次；共用Run额度/截止，不足1秒skip，空成功与未执行/省略分开；取消/超时/不确定保unknown占槽，不自动重试。原行/投影/新问题视图复用artifacts/run_steps，run_members仅更新选定字段read_state，不冒充分析。字段observation、原回执/视图根只执行记录；模型视图按记录交错选取，8192/2048及12KiB保持，未调用模型/发布Result/采用。

11项本批+4项原发布/引用回归最终通过，21原独立合成PG库，CH全替身，五批临时角色/隧道清理，无新容器。首9项7过2因工件误用created_at，改captured_at后定向复核；其后1项测试Results.run_id应为source_run_id，修后3视图相关项通过，原失败保留。补真实延期FK提交失败不派发/引用路径/默认值/字节测试，未变通过项复用。见docs/investigation/socai2-baseline-c4-evidence-20261103.md及operations同名json。原29表458列/DDL/ORM/枚举/38合同不变，主设计/R03/R06/交接/入口同步。

下一C4动态问题级Deep与补证后C3新输入/步骤身份，产品主机/认证适配待接，再C5图/C6交付。不能把本批确定查询原语称完整Deep；旧HTTP/新表writer/生产迁移仍待。0真实模型/CH/厂商业务调用，页面不改，报告暂停/r13不重试/5.3未完，无提交推送/部署。

# 2026-11-03 C3初始主分析与四领域结果已实现并验证

新增baseline_analysis.py/contract.py/model.py及专用baseline_analysis.schema.json，BaselineService.analyze接同Run初始C3；Case→Run锁、stage先提交、model running与精确请求提交后才调用。复用resolve_llm_config/safe_chat_completions_request/URL及airgap，凭据不入工件。一次共享模型调用含identity/cloud/phishing/insider视角，不是四个独立专家/第二套Run；全成员、六问题、局部发现、支持/反证/替代解释、冲突和query/deep/graph/human补查需求分别有合同。S来源只来自本次可见模型视图，保存原ID/路径/角色、适用成员及可见值hash；越界/未见/角色升级/成员错配拒收。实际请求/原答/用量、四domain_analysis及主source_snapshot留存；analysis_state可更新，read_state不冒充已读原文，不发布Result/自动采用/结案。

原Run额度不重置；3000输出tokens，原12KiB消息约束；模型预算按实际请求bytes+3000+256保守预留，前序未知用量阻止继续。缺失用量NULL、费用未定价NULL，不补0；失败/截断/拒绝/未提供的tool或function调用留原件不采纳，不自动纠错重试。传输/取消/提交不确定Run及步骤unknown占槽。重复完成/失败/跳过C3读原工件不重查；仍在执行返回冲突。C4补证后的再分析尚未接，不能复用同一C3入口自动重跑覆盖历史。

12不同C3检查+7受影响回归最终通过，含15合同反例、真实PG延期FK导致COMMIT失败不派发，以及并发/范围变化/额度/原件/来源/取消。模型全部明确替身，0真实模型/外部业务Tool；21原独立合成库，不新建容器/夹具表，临时账号/隧道每批清理。首静态括号/导入修正后运行；业务首10与新增2均过。收尾增加timeout≤0传输前拒绝、收紧延期FK约束/提交前标记后定向复核2过，其余复用；测试闭包显式绑定。见docs/investigation/socai2-baseline-c3-20261103.md及operations/socai2-baseline-c3-20261103.json。123迁移/29表458列/ORM/枚举/38通用合同不变，专用输出schema镜像设计树。

下一C4必要原始语义/工具目录绑定/确定查询与问题级Deep，再C5有来源图和C6交付；明确新证据再分析输入/步骤身份。UEBA/知识/Graph适配、新表writer/HTTP/生产迁移仍待，真实模型解释质量未验，不宣称超过开源完整能力。主设计/缺口R05/交接/README已同步；页面不改、旧报告修复暂停、r13不重试、5.3未完，未部署/提交推送。

# 2026-11-03 C2三类背景查询与有界模型视图已实现

新增baseline_enrichment.py/sources.py/model_view.py，BaselineService.enrich/prepare_model_view接同一个已running的新socai2 Run。C2 stage及每来源步骤先提交再查询，重复请求不重查；Case→Run锁顺序，执行中成员变化不污染冻结范围。三类同租户实际SQL：public.assets、socai2同对象/命名空间/窗口历史告警、public内部TI；只读有效非误报未过期TI，未知分数不补0，hash算法须明确。UEBA/知识/Graph未适配留unavailable，旧public告警不查。六来源请求/结果/状态/时间/限制、截断原因及有限fetch计数进既有artifacts/run_steps；共用Run额度/截止，查空、未接通、预算不足、超时、字节省略分开。取消/未知保留unknown占槽，无自动重试。publish禁止未落定步骤完成Run。

模型视图保全成员覆盖、六问题、来源角色/路径/时间/限制；原值递归guard后整项挑选，8192字节正文/2048单项，省略明示，必需范围超限ready=false。不读取整段raw进模型、不标已读、不执行模型。C2来源标签与旧分诊/人工反馈分角色，发布校验引用路径。C3-C6/完整执行器/HTTP及新表业务writer未接，较大材料的必要语义字段消费仍待。页面保持，报告暂停、r13不重试、5.3未完，无业务部署/模型/外部业务Tool/提交推送。

11项本批检查+8项原发布/引用回归最终通过，见docs/investigation/socai2-baseline-c2-20261103.md及docs/operations/socai2-baseline-c2-20261103.json。21现有PG独立合成库，三类SQL实测，错误/大行部分明确替身；每批受限账号/隧道已清理，不建容器。首轮夹具event_time_source缺失、随后error的JSON null写入、后续采用返回对象断言失败均留原件，定向复验/未变通过项复用。无29表458列/123迁移/ORM/枚举/38通用合同变化；仅测试库两张public来源夹具。主设计/缺口/交接/README同步到设计树，后台以本工作树为准。

# 2026-11-03 C1整案数据准备已接入并验证

用户继续后新增app/socai2/baseline_context.py及专用baseline_context.schema.json，接入新BaselineStore.claim。Case→Run锁内用单个PG SELECT读视图选择Case/全成员、材料/对象/来源引用、同次分诊与人工改判、显式或成员关联事件/归并依据/诊断、当前任务版本、当前判断/来源/覆盖及明确选用历史；run_members使用同一次选择的ID，不再次读latest。新增source_snapshot(socai2.baseline-context.v1)，input manifest升v2并引用快照，保存六项open必答问题及omissions。未完成任务只是执行记录，诊断要completed+accepted+成员重合才可用且仍标新鲜度未重验；案外成员不扩Run。当前判断引用的旧任务版本与当前版本分别留存。C1引用路径/role校验，JSON null不作已有raw，超128KiB拒绝准备且不截成员、不提模型额度。

read_context核保存工件/hash；read_material只读已领取baseline冻结版本，不读latest、不写GET状态。旧v1没有C1时明确返回不可用，不用当前资料补造旧输入。C1是数据快照，不是模型提示词；没有调用模型/Tool或接C2-C6、HTTP。

11项C1和10项受影响原存储回归最终通过，见docs/investigation/socai2-baseline-c1-20261103.md及docs/operations/socai2-baseline-c1-20261103.json。首C1 8过2测试问题：在Case锁内等待新任务版本的延迟FK提交而超时，改预建版本后并发更新现有指针；一告警分配多事件违反唯一约束，改不同成员。未放松锁/约束，原件保留。之后定向复核受影响/新增用例；不是一次首过21项。21原独立合成PG库，所有批次临时受限账号/隧道清理，无新容器/业务数据/模型Tool/部署/提交推送。

29表458列、123迁移/ORM/枚举/原38JSON合同不变，与设计树一致。C1专用内容合同已镜像到设计树docs/design/socai2-baseline-context-v1.schema.json；主设计/差距/交接同步，旧schema与17服务测试原回执不改。本后台为代码权威。下一先接有界模型视图和guard及C2背景富化，然后领域/Deep/Graph/C6；诊断新鲜度未重算、材料更新不自动触发新Run。业务HTTP/告警事件writer/人工AI接口/业务库切换仍待。页面不改，r13不重试、报告暂停、5.3未完，已定业务口径不重问。

# 2026-11-03 新socai2表的Case存储事务已实现并验证

用户继续后，将设计工作树已审计123迁移、29表ORM、枚举和JSON合同五文件逐字节同步到本后台分支；迁移SHA仍ceb9a68012f84d6558cd0f75aa67b4047ae6245e1be64e79dd9b86587b8579da，无DDL更改。新增app/socai2/baseline_contracts.py、baseline_store.py、baseline_service.py，实现成员关系/版本/真实活动→同一pending更新或新增下一pending→手动领取完整成员和材料/分诊/反馈版本→提交running后派发→结果/逐成员交付/自动采用同事务发布→历史读取。Case→Run锁序、同请求不重派、409保留pending；未配置完整执行器503不领取；派发不确定标unknown占槽，无定时领取/接续/自动重试。业务时间使用数据库时钟。

17不同Python服务+真实PG检查最终通过，见docs/investigation/socai2-baseline-storage-20261103.md及docs/operations/socai2-baseline-storage-20261103.json。使用21现有PG16.15的独立合成库socai2_schema_review_20261103_a1；临时受限LOGIN角色/本地SSH隧道每批结束删除，不新建容器。首14项9过5因测试角色缺函数EXECUTE失败并回滚；补测试角色权限后5过，随后数据库时钟/冲突处理改动及3新增场景验证10项、复用7项；原件和hash保留，不称一次首过。没有模型/Tool/真实业务Run/部署/提交推送。五新Python Ruff通过。

新服务尚未注册到旧HTTP或替换旧writer；旧122方案及业务源码保留。当前输入工件是成员/材料清单，还不是完整C1 ContextBundle；没有把旧有限CaseAnalysis当完整执行器。下一先补Case说明、事件诊断、人工任务版本/历史判断/遗漏的C1冻结输入，再接C2-C6和必要Tool消费，HTTP鉴权DTO/告警事件新表适配仍待；AI明确采用和人工接口未接。新服务使用Pydantic校验本批子集，测试用jsonschema比对实际JSON；不能声称38合同全部运行时接通。

设计分支入口/主设计/差距/交接已同步状态，代码权威在本后台工作树。D01事件人工覆盖保自动值、D02有效基础自动采用/AI明确采用、D03只基础单活跃及原16项不重问。空Case不启动、已解决Case操作保留限制。页面不改，报告暂停，r13不重试，5.3未完。

# 2026-11-03 基础调查待更新记录本地实现，真实并发待验（旧122方案历史记录）

用户明确要求表内新增/更新基础调查执行记录，并确认“未开始更新同一条；开始后冻结，后续范围变化另建”。本分支 codex/case-baseline-history-20261103 从后台检查点39f4033创建，实施范围仅该后端功能；取代早先只在Case保存待更新状态的建议，不恢复全部页面功能或报告修复。

迁移122复用investigation_runs，新增kind/revision/scope_updated_at，started_at允许空；Case成员触发器同事务维护pending_update，唯一索引每Case一条待更新。启动Case→Run加锁、expected_scope_revision冲突409、同请求读回同ID、已有活跃执行拒绝新启动，开始后范围及来源元数据数据库保护。历史/执行索引/关联读适配空开始时间；无自动派发，无页面修改。合并Case按ID顺序锁定。

用户进一步要求同Case单活跃基础调查及避免“第一步尚未改状态”竞争。已补数据库活跃baseline唯一索引（queued/running/unknown/awaiting_human）；领取事务提交running后才调用执行器，失败不派发。78不同相关用例最新53过25跳过（7新增真实PG、18既有DB测试），另16子场景；初2个失败为新测试替身未识别排除自身的活跃查询，修替身后定向通过，原件保留。新增3文件Ruff通过，旧修改文件10既存诊断无新增；SQLglot不能校验函数体。迁移未应用，本机无PG引擎，真实双事务/RLS/完整服务接入尚未验，不能声称已消除线上竞争。见docs/investigation/baseline-execution-record-20261103.md及本批回执。无真实Run/模型/Tool/部署/提交推送；设计分支单独同步交接文档，原主工作区和旧证据不改。r13不重试、报告暂停、5.3未完。

用户已确认保留手动启动逻辑，并明确不要改页面：没有定时领取或结束自动接续，下一条待更新要明确启动，有活跃执行时返回409并保留待更新，不写failed、不自动重试。页面差异清单记录在设计分支docs/design/baseline-execution-handoff-20261103.md，后续交专门人员讨论实现；不重复询问调度策略。

# 2026-11-03 本地页面与进度提交，转入独立设计分支

用户最新要求 step1：远端功能分支页面本地可访问→本地提交当前进度→在分支继续对齐设计功能。已 fetch origin/codex/functional-analysis 到 c71afb5，创建 codex/functional-alignment-20261103，独立 worktree 为 E:/aisoc/socai2/.local/worktrees/functional-alignment-20261103；未合并进当前后台工作区，也未动另一份功能 worktree。原型 serve.py 隐藏运行，只监听127.0.0.1:4174，HTTP首页及27资源正常，浏览器新版Case资料页已呈现。见 docs/investigation/local-design-preview-20261103.md。

本次提交范围为第1—4批代码/测试/文档/证据、85项对照和本次远端需求快照；不含START_HERE*、ding、inv-review及.local运行资料。不推送/部署。后续在独立设计分支先理解和对齐三类工作：基础调查首次与成员更新、AI发送后处理与明确保存、人工任务确认及引用；同时核页面职责、现表可复用点和流程差异。此项优先于上一轮直接补T字段安排，不立即重构建表或恢复报告开发。原85项为旧48f54abd对照，不冒充新版全验；用户16项口径仍保留，报告暂停、r13不重试、5.3未完。

# 2026-11-02 按用户要求完成字段明细对比

用户要求不要“大多／可能”，要确认明细。已新增 docs/investigation/page-field-support-matrix-20261102.md：37 告警、24 事件、12 操作数据条件、12 Case/Tool，共 85 核对项；每项含语义、存储路径、实际读取出口、明确差异。固定需求仍 48f54abd，本地 b400fd0 加第 1—4 批未提交修改；本轮未刷新远端或线上取数。用户 16 项决定已补当前状态表，旧单项“事实／尚未实施”注明历史时点，不能当当前修复状态。

确认缺口：事件独立 title/description/status/owner/classification/priority/tags/resolution 事实及自身业务时钟，普通 Alert 评论合同，准确活动主体及批量目标；Case 原始 OCSF 必要语义投影、进程 session/PID/父进程/命令行、网络 src_port/dst_hostname/action/outcome/session_id 漏读。状态 fp 分组／反馈关闭／重开时间／Case 启动业务状态是有列但映射或写回不一致，交后端；功能不在本轮实现。补核 approvals 已复用 approval.id 为 action.id，不能称审批与执行无键；通用建议到审批缺稳定关联，actions incident_id 此入口为 Run/审批 ID，不能当 Fusion Incident。

下一从明细 T02/T05/T06/T08—T11 做必要字段消费修复，事件/评论/活动最小数据合同已交接，不扩列表、导出、管理级联。仅新文档及入口/计划同步；业务代码、原四批回执/证据不改，不新增业务测试、真实服务调用、Run、模型、部署、提交/推送。静态来源/链接检查见 docs/operations/page-field-support-matrix-20261102.json；报告暂停、r13不重试、5.3未完。

# 2026-11-02 用户收回到字段与数据支撑，不推进页面功能实现

用户明确“主要管字段，功能让后端自己实现，只要确保数据能够支撑页面功能”。此指令覆盖下方原第5批列表、第6批管理等功能实施安排。继续以远端页面和字段对照为验收参照，从Fusion收到数据后核保留、落库、关联、语义、读取与可派生性；需要的最小字段映射/模型/存储/读取修复仍属范围。筛选/排序/统计/导出/管理表单/流程/负责人或解决级联仅核数据基础、记录合同交后端，不实现功能、不以功能尚未落地阻塞字段结论。

下一先整理字段支撑总表：字段及语义、已存来源/表/列、关系及粒度、现有读取路径、可直接使用/可派生/内部缺口/输入限制；复核第1—4批覆盖和剩余数据断点，再处理仍必要的数据修复。状态/负责人/评论/活动若缺字段或稳定关系，仍列真实数据缺口；派生统计无须为了页面另建冗余计数表。Case/Tool已有字段读取缺口保留在范围；报告生成修复不自动恢复。

本轮仅同步任务记录/计划，没有新业务代码、测试或部署。已完成四批修改保留，不因收口自动回滚；不再扩功能，后续按数据必要性复核。HEAD仍b400fd0，未第二次提交/推送；16项口径不重问，Fusion前置输入排除，r13不重试、5.3未完。原回执保留历史代码/文档指纹。以下是历史过程，旧“下一批实现功能”安排已由本条取代。

# 2026-11-02 第4批共享读取与业务时间本地修复完成

用户继续后完成S1-02、S3-03/04/05及S4-02/07、S5-01读取部分：API映射已有iocs，共享source/detection/objects用于列表详情、事件、Case；原厂只取明确original_vendor/deviceVendor，未知null，接入编号与external_id分开。事件逐成员对象边、战术每阶段各计1及提示；负责人同租户username解析；资产补tags/匹配依据及entities-only查找，include_assets最多20成员并列省略。include_investigations沿cases:read返回当前多Case及截断，旧case_id标兼容；图anchor只认Case.alert_ids。事件first_seen=min(event_time)，updated_at取成员业务时钟，source_updated_at保材料新鲜度；详情GET不写缓存/时钟。事件自身管理写入仍第6批。

Case真实context及hash补检测/来源字段和同次T评分、判定、理由/建议及Run事件时间；模型新增值2048字节有界且先原值guard，省略明确，冻结副本保持。旧评分legacy_unverified；未知/失败/禁用不显示残留值。无DDL/Fusion写入/记忆框架/预算提高。68不同相关用例最新通过，新增9；旧编号预期、GET空串及新增嵌套字段guard三项初失败/错误保留后定向通过。基线读函数同输入对照及资产SQL方言解析通过，非真实PG。见docs/investigation/field-alignment-fix4-20261102.md、docs/operations/fusion-field-fix4-20261102.json。

第1—4批留工作区，HEAD仍b400fd0，未再次提交/推送/部署；0真实业务服务/新Run/模型。下一第5批列表筛选、统计、排序、导出与状态分组；第6—8批待。旧图/旧报告不回填，原16项不重问，上游输入排除，报告暂停、r13不重试、5.3未完。重叠源码以本批回执为当前指纹，前批原件保持。

# 2026-11-02 第3批已有字段、时间、完整性与湖查询本地修复完成

用户继续后完成S1-01/04/05/06/07、S2-03—06：三个生成入口保留已收到时间/对象/规则及来源标签，PG初始first_seen/last_seen绑定时间，未知fallback显式保存；来源引用上限200及截断、范围/更新时间保存。阈值旁路来源仅bounded_observed_references、complete=false，序列保存匹配候选而非因果链；旧原文/首快照不覆盖。评分计算状态明确，未算/禁用/失败入库NULL而非50。activity两形态互补且信封冲突优先，session写实际块；SHA256按明确算法与形态读取，其他hash保普通IOC；超限raw/OCSF合法JSON包装带大小/hash/截断。两Tool同范围去重后限量，process.v3/network.v2旧合同不作新结果复用。API镜像同步，无DDL。

124不同相关用例含参数场景最新通过（Fusion115/API9，新增20）。首Fusion100过3失败，hash夹具补算法、早期epoch本地时区往返改UTC；新增/定向复核及未变通过项复用。网络历史报告测试因新合同不复用而失败，仅在内存适配模拟父结果；另旧提示词断言同步，原失败均保留，不改旧证据/报告逻辑/预算。6组基线字段对照、2组双Tool SQLite查询前后对照通过，PG/CH方言解析通过，23文件Ruff通过。见docs/investigation/field-alignment-fix3-20261102.md、docs/operations/fusion-field-fix3-20261102.json及evidence/fusion-field-fix3-20261102。均本地替身/SQL参数或SQLite验证，非真实PG/CH写入或线上验收，0新Run/模型/部署。

第1—3批留工作区，HEAD仍b400fd0，未再次提交/推送/合并；前两批回执保历史指纹，重叠文件以本批为准。下一第4批共享读投影（原厂、IOC、成员对象/战术、资产标签/匹配、多Case、检测及同次分诊评分、业务时间）；第5—8批待。用户16项不重问，上游输入排除；报告修复暂停，r13不重试，5.3未完，不扩记忆/权限/恢复框架。

# 2026-11-02 第2批身份、归并依据与提升开关本地修复完成

用户继续后完成S1-03/08、S3-01/02：三个规范化事件生成入口有来源ID时采用event-v1，区分事件/连接器/规则/生成路径；legacy-v1/source-v1指纹保持。仅PG首份有效快照能证明同源时复用旧身份，不以追加来源/同标题推定；新Redis entity-v2类型键隔离旧无类型键，无对象按告警隔离。实际归并依据进入FusedAlert、首次快照和alerts.enrichment_data.socai2_fusion，并由事件成员/告警上下文读回；旧记录空。提升开关在执行分支生效，写湖及两类检测保持。API镜像模型同步，HTTP旧入口清空内部事件身份字段；无DDL。

66相关用例含参数场景最新通过（Fusion56、API3+7，新增19）；Fusion初收集因测试导入错误停止，修测试路径后56过，原件保留，其余通过项不重复跑。b400fd0同输入对照3生成入口从不同事件折叠→独立ID，重投稳定；host/user同名和无对象分开；关闭提升原3告警调用→2，写湖函数仍1。API/Fusion模型逐字节一致；Ruff19文件及diff检查通过。见docs/investigation/field-alignment-fix2-20261102.md、docs/operations/fusion-field-fix2-20261102.json。均本地替身/参数验证，无真实DB/Redis/Kafka/湖/模型/Run/部署。

第1、2批均在工作区，基线HEAD仍b400fd0，未再次提交/推送；旧证据/报告保持。旧指纹候选之外的历史重投不声称自动识别；旧键隔离可能使上线后新成员进入新事件，旧成员不重组。下一第3批已有字段/时间/完整性与湖语义，S3-03—05及第4—8批仍待；用户16项决定不重问，输入前置问题排除，报告修复暂停，r13不重试、5.3未完。第一批回执保留原指纹，重叠修改文件以本批新回执为准。

# 2026-11-01 基线已提交，第1批事件ID与湖绑定本地修复完成

用户要求“先提交一版本，然后进行代码修改调整及文件同步，做完再比对确认”，覆盖下方旧不提交/仅核对限制。已本地commit b400fd0，339文件，保存此前r13实现/证据与六段核对；无关START_HERE*、ding、inv-review未加入，无推送。随后完成字段修复第1批S2-01/02：Fusion统一event_id→id→metadata.uid优先级与有效UUID表示；新告警引用规范化；湖默认ID组SQL与行同时省略列；flush失败返回False；laked改为确认INSERT数，lake对象公开缓冲/失败/本地放弃量；未提升日志不再声称入湖成功；Case匹配兼容旧UUID写法、不改旧原文/报告。

39个相关用例含参数场景最新通过：Fusion首34过3测试记录错误、API2过；真实RowOrientedBlock会原地转dict为list，修测试副本后仅复核3过，其余复用。基线源码同输入对照3种ID入口及2行批次：旧驱动KeyError/写入计数0，修后绑定2，不是真实CH入库。见docs/investigation/field-alignment-fix1-20261101.md、docs/operations/fusion-field-fix1-20261101.json及evidence/fusion-field-fix1-20261101。原日志保留，无业务外呼/Run/模型/部署；已有best-effort边界保留，rows_dropped是本地放弃且未确认，不证明服务端无行。

第1批修复仍在工作区，未自动第二次提交/推送/合并。主记录、湖审计顶部、修复顺序、README/审阅入口和PROGRESS已同步；六段审计原件不改写。下一第2批已有身份/归并类型/依据与开关，第3—8批待；用户16项规则不重问，输入前置问题排除，报告修复继续暂停，r13不重试、5.3未完。当前代码本地验证不冒充线上验收，不扩大测试/权限/恢复框架。

# 2026-11-01 六段字段核对完成，下一按功能修复

用户“继续”后完成第5段docs/investigation/case-input-tool-field-audit-20261101.md及第6段field-alignment-impact-and-repair-plan-20261101.md。S5三组缺口：已存检测/同次分诊评分未投影，OCSF raw冻结但模型整段拦截且无必要语义字段，Tool未读取已存动作/结果/完整端点/会话及进程明细。既有冻结/H1/来源绑定/有限查询可复用，不需Case记忆层；保输入guard与预算。4本地观察，首轮观察脚本datetime序列化在首项完成前报错，保初版/错误，修脚本后4项完成，非业务修复。证据fusion-field-stage5-20261101。

复核r13六请求24次来源字段出现均完整、四Tool保存/模型行1/1/0/0、0复用；第6段14份原件对照，A原回复6490尾随空白/3000输出tokens截断，独立txt仅CRLF差异；B仍空查询反证化、未提供审批写不存在、process_activity/E2错配，旧T判断与原始事实须分开。未证明这些语义问题由Fusion缺口导致，沿用R编号，5.3未完。

六段均本地核对完成、未修复/线上验收。建议下一先修S2-01/02统一event_id/id/metadata.uid及UUID表示、湖INSERT列绑定/写入结果，再沿8批功能顺序补身份/关联、保留字段、共享投影、列表、管理级联、Case/Tool、报告。用户16项决定沿用，无新增待问；原厂未知空、选中导出否则前200、事件负责人/解决覆盖全部成员并保存前提示等不重问。仅文档/合成观察/旧证据分析，业务源码未动，无真实DB/Run/模型/湖/厂商调用/部署；报告修复仍暂停，r13不重试、不提交/推送/合并/归档。远端需求48f54abd、本地b758351加原工作区；Fusion前置输入问题继续排除，不扩大审计或框架。

# 2026-11-01 第4段页面API与管理本地核对完成

用户“继续”后完成docs/investigation/page-api-management-field-audit-20261101.md，前四段本地核对完，下一第5段Case实际冻结／模型可见／Tool及复用。8组问题覆盖搜索声明未用、筛选排序／导出不符、字段投影、状态／真实调查统计、反馈只改判定却写resolved SLA、评论／事件管理缺写入、时间口径及活动串Case。已有stats总体聚合可承接前三卡，不能误称完全缺总体统计；v2 Case启动没有Alert状态写回。GET旧告警详情叙述缓存更新updated_at也会污染业务时钟。

用户第16项已确认：手动解决事件同步关闭全部成员、保留各自判定、保存前提示影响；事件解决说明沿用必填，原保存动作，无额外确认弹窗。第14项负责人覆盖提示同样需后台同步／持久化／活动读回，不能仅做提示。11不同本地观察：初9项断言完成，时间线夹具写只读is_automated报错，初脚本只结尾落结果导致9项明细未保存，原件及边界保留；只改actor_type定向跑1项，另新GET时钟1项，未重跑9项。证据docs/operations/evidence/fusion-field-stage4-20261101；源码未改、未修复／线上验收，无真实DB写／模型／Run／部署。远端需求仍48f54abd，输入问题继续排除，r13不重试、5.3未完，不推送／合并／归档。

# 2026-11-01 第3段关系与资产本地核对完成

用户“继续”后完成docs/investigation/fusion-relations-field-audit-20261101.md，前三段本地核对完、下一第4段页面API及业务管理。S3-01—05：归并键缺类型使同名host/user并入；PG有归属及snapshot但实际归并依据仅部分保存；sink已写iocs但API Alert ORM未映射、事件只有实体并集无成员边／战术计数；现库存读取漏tags/匹配依据且忽略entities-only主机；旧Alert.case_id与当前Case.alert_ids及旧图并集范围不同。保留PG成员、F4部分／多Case、冻结Run与保存报告读取能力，不新建记忆／图框架。

6项不同本地观察，Fusion2项完成；初API夹具iocs构造TypeError揭示ORM缺口，原件保留，按实际映射列修正后API4项完成、Fusion复用。未改业务代码、未修复／线上验收，无真实业务服务／模型／Run／部署。远端需求ls-remote仍48f54abd，代码为b758351加原工作区，证据docs/operations/evidence/fusion-field-stage3-20261101。输入缺失／错误仍排除；下一核已定页面管理规则及first_seen／Run时间污染更新时间，不重复询问15项决定。r13批次保持结束、5.3未完，不归档／推送／合并。

# 2026-11-01 重新对齐任务：从Fusion入库核对页面与调查能力

最新进展：用户“继续推进”后第2段本地核对完成，见docs/investigation/fusion-lake-field-audit-20261101.md，下一第3段事件／实体／资产／Case关系。S2-01—06：告警和湖ID优先级/UUID文本不一致；有效metadata.uid漏映射后固定INSERT缺列，本地实际driver绑定KeyError导致两行批次丢弃但write_event仍True；顶层与OCSF内activity读取不一致；首个hash误标SHA256；raw静默裁剪可能破坏JSON；Case查询未去除重投副本。13不同本地观察，初会话夹具kind=vendor仅块读取成立，改vendor_session后只复核2项、复用11项，原件保留；无真实故障注入/服务调用。旧r13 A两行分别对应A1/A2，B空，4 QueryFinish复核，手工fixture不证明Fusion写入。未改业务代码、未修复、未核线上触发；输入缺失不列待办，不重跑r13或开启模型/部署。

最新用户边界：“如果是fusion的前置数据也就是输入数据的问题 不用管”。范围从Fusion实际收到输入之后开始；上游缺失、错误、规范化不到位仅标输入限制，不追查、不修复、不要求补数，也不列待办或验收阻塞。保留输入已有值被Fusion及下游漏传、替换、错误合并、未持久化或误用的问题；未知被下游当确定事实仍须处理。第1段8项观察已按此重分类，不能再笼统称8项都需完整修复。后续湖核对只查收到数据之后的写入／映射／查询，不追查上游采集。

用户明确模块名为Fusion，并纠正任务不能只讨论页面提示/规则或Case传参。真正目标：以远端最新告警页、事件页及字段对照为需求，检查当前Fusion接收/处理/入库→PG告警与原始事件湖→事件/实体/Case关系→分诊及人工管理→API/调查输入→Tool与报告是否能完整正确支撑，定位数据缺口、语义偏差和功能影响。调查页面本身不做设计比对，不等于排除调查后端。先追踪实现和已有证据，再问仍未定的业务语义，不继续以连续规则问答替代数据链审查。

用户已要求“规划分段核对”“开始核对”。六段计划已保存至同一主记录的“分段核对计划”：1 Fusion输入到PG告警入库；2 原始事件湖与告警对应；3 事件/实体/资产/Case关系；4 页面API及业务管理；5 调查实际消费与补查；6 报告影响及最小修复汇总。第1、2段本地核对完成，下一第3段。每段沿同一字段表记录来源、转换/入库、下游使用、断点、影响、最小修法和证据范围；阶段核对完成不等于修复或真实验收通过，不新增逐段审批/独审门。手工fixture不能冒充Fusion真实链路，复用已有材料，缺证据再补必要直接验证。

现有第1—15项确认全部保留在docs/investigation/field-alignment-confirmations-20261101.md。第3—6项Case输入重新纳入完整链路评估，之前整体后置过窄；不把所有显示字段无差别塞模型。第15项已确认事件最近更新时间包含事件自身及成员告警变化，单独调查进度不刷新。第10项仍为未勾选导出前200/不足全出、有勾选导出所选；第14项仍为负责人同步全部成员且保存前提示覆盖。当前无待答复问题。

远端基准本轮只读核实仍48f54abd。第1段确认S1-01—08：两类检测漏传时间后NOW替代、原厂独立语义缺失、规范化分支legacy身份折叠不同发生、规则/战术投影不齐、窗口实体漏取可能让Case无湖Tool、来源追加上限/更新时间/窗口参与事件不完整、默认50分缺计算状态、提升开关未在执行分支检查。直接HTTP source-v1已有稳定身份和字段保存路径，不能泛称所有入口都缺。14项明确synthetic本地字段行为观察首次运行确认，非需求通过；0真实业务服务/模型/Run。源码/数据映射及首份快照事实已落文，未改业务代码。当前仓库无ingest normalizer正文，线上Fusion源码/config未核（读取本机SSH配置权限拒绝，未改权限），保留证据边界；下一核湖对应，不用旧配置代当前事实。负责人/评论等后续管理字段另查，不要求Fusion生成。

r13报告问题保留、修复批次不恢复，5.3仍未完成，不重跑旧批次。不因字段补齐声称报告语义通过；保持功能优先、必要直接验证、复用未变证据，不扩权限/恢复/压力或通用框架。本轮仅源码/文档核对及本地映射观察，无新业务调用/导出/分配/部署，不提交/推送/合并。

# 2026-11-01 r13已部署，真实报告验收仍未通过

用户明确允许指定两个Case/四告警及本批原件导出后继续，原自动审批拒绝已解除且保留记录。r13镜像7ca057227526…，477包文件/473容器应用源码与固定候选一致，原17项直接验证复用，0业务重跑。A ba9eb0ff-b7b2-52ff-8d4f-5b99140893f1 failed/partial：报告输出3000tokens，尾随空白6490字符导致JSON未闭合，停止model_response_truncated，未入语义校验/纠错；可读残稿仍把Tool写为确认PID并引入无源Confluence。B f582e350-1a30-58c4-9163-5f00617e33f7 completed/partial但语义不合格：空查询被写为削弱关联、未提供审批变无审批、process_activity误标E2。A/B各一次、各3模型，4真实查询1/1/0/0行、0复用，20334tokens/6调用未定价；raw各3次完整，24事件28工件57HTTP核对，旧告警/Case/r12报告与其他容器/环境文件保持。C前提未满足未绑定/派发，PG核实无Run。见docs/operations/investigation-r13-report-validation-20261101.json及evidence/investigation-r13-20261101/review.md。本批结束不重试；本轮未新增业务修复，下一限定报告截断进入原一次纠错的处理、空查询不构成反证、未提供不等于不存在及Tool名称编号一致性，不提高预算、不拼接残稿、不扩记忆/通用框架。真实纠错/追加及完整语义仍未验，16/17、5.3/P3待办，不归档/提交/推送/合并。

# 2026-11-01 r13候选已固定，原件导出被自动审批拒绝

用户继续后固定r13工作区候选477文件含473应用源码，tar SHA256 40ce764614737e42b7c0cbb72e192a6714eb2257b0403db59e4bbb796e3e67c0，逐字节hash及0644/0755权限已核；相对r12仅3旧业务文件、1新增校验模块及2发布标签变化，复用17项直接验证，本轮0业务测试重跑。A/B新Run计划ba9eb0ff-b7b2-52ff-8d4f-5b99140893f1、f582e350-1a30-58c4-9163-5f00617e33f7，C仍须A报告合格后绑定，最多3Run/12模型/72000tokens，原成员/窗口/单Run预算保持。SSH既有配置入口已连通；随后只读预检脚本被自动审批以“可能含敏感组织数据从21导出到本地缺少明确授权”为由拒绝，脚本未执行。已询问允许两个既有Case/四告警及本批请求、报告、模型/Tool原件保存至本地r13证据目录，凭据不导出，尚待答复；不绕过拒绝。见docs/operations/investigation-r13-preparation-20261101.json及evidence/investigation-r13-20261101/preflight-approval.json。0上传/部署/新Run/模型，线上最近核验仍r12；本轮未核实当前线上源码和业务数据，不归档/提交/推送/合并。

# 2026-11-01 r12后来源值与协议误拒本地修复

用户“继续处理”后新增窄PID/账号来源字段校验：按本条引用的A原文/用户实体及E成功rows核对，T/H/saved_analysis不作事实；明确Tool观察不能借A字段。修正r12源协议未声明和联合不确定句式误拒，已知空查询原因推测及evidence_id_list_占位拒收；成员自身来源引用与其他语义边界错误合并为一次纠错反馈，原码/原答仍留账本不回灌。提示精简并分开原文/观察/推断。17不同受影响方法最新通过含6新增，初解释器依赖错、修前红例、夹具缺kind和提示字段断言问题原件保留；不是一次17项首过。A/B完整离线回放8旧回复/4旧Tool，raw及旧usage25783保持，两坏报告仍failed；无新真实模型/查询/Run/部署。Office14102≤15074、网络12259≤12296预算未提高。见docs/investigation/report-grounding-fix-20261101.md及docs/operations/investigation-report-grounding-20261101.json。线上仍r12；校验不是通用事实/因果证明，真实输出质量未验。下一固定新候选和新批次验证，不重跑r12、不新增记忆框架、不推进P3/5.3、不归档/提交/推送/合并。

# 2026-11-01 r12已部署，A/B报告仍失败，固定批次结束

用户继续后完成P1/P2：r12为b758351工作区快照（未新提交），镜像17cac869d789…，472应用源码与固定候选一致。A Run24ec42ee-05aa-548e-a52e-e056df2bdeeb、B Run8d1b5ac8-962e-5c02-afa0-3badd109f758各派发一次，均failed/partial；A真实查询1/1行、B成功0/0行，4 QueryFinish/0复用、8模型25783tokens且8调用未定价。各两条raw在4次输入完整；纠错反馈隔离生效但报告仍编造：A PID4209/Tool父子链/文档服务器，B admin/清洗丢失/注入及占位乱码；协议未声明/无法确认句式仍误拒，成员来源引用也失败，不能只放宽规则称通过。C前提不满足跳过，未验追加/历史复用。65业务HTTP原件hash核、32事件36工件；旧告警/Case及r10/r11结果报告响应逐字节保持，core/agents/网关/环境文件/凭据保持。无新告警/Case/湖事件、无业务测试重跑；6源码/测试指纹仍同最新通过记录。见docs/operations/investigation-r12-report-validation-20261101.json及evidence/investigation-r12-20261101/review.md。本批结束不重试；P3、5.3仍待，不归档/推送/合并。下一只聚焦来源字段归属、证据强度和具体协议误拒，不新增Case记忆或通用框架。用户问旧开源版：历史固定上游已核有相似证据越界/Deep漏字段/末Tool当报告问题；当前Case协议和引用校验缺陷属于新实现，不能归给上游。

# 2026-11-01 P1完成，r12候选及A/B/C请求材料已固定

用户“继续推进”后完成P1本地准备。r12候选标签20261101-r12，476文件含472应用源码，tar文件0644/目录0755及逐字节hash已核；相对r11仅4业务文件和2标签配置内容变化，另27文件仅换行差异。业务/测试6文件仍同最新通过指纹，0业务重跑。源码是b758351工作区快照、未新建Git提交；以candidate-manifest和tar hash固定，不宣称HEAD含全部修复。A/B各新operation_key并保持既有Case/成员/窗口、真实补查；C非法UUID占位，仅A语义合格后绑定，不可直接派发。报告核对表/历史来源指纹齐备，旧r11建Case脚本不用于本批。见docs/operations/investigation-r12-preparation-20261101.json及openspec/changes/fix-investigation-audit-gaps/retest/r12。无远端访问/上传/镜像构建/部署/新数据/Run/模型；下一P2核对21及样本并仅更新独立API、执行固定最多3Run，旧批次不重跑。5.3仍待，不归档/推送/合并。

# 2026-11-01 后续计划已保存，下一先准备本地候选

用户要求“规划后续”。新增openspec/changes/fix-investigation-audit-gaps/report-followup-plan-20261101.md，任务/审阅入口已链接。P1固化当前候选与A/B请求、C模板；P2拟新批次最多3Run：既有r11Case正向真实补查、既有r10Case成功空查询解释、A合格后同范围追加；新operation_key、原预算、旧数据/批次保持，不反复重跑挑结果。P3报告达标后再处理G01–02来源/必要字段、G03–05状态/关联/时间，事件管理另按实际需求。无新增Case记忆系统。本轮仅规划，无业务代码变更/业务测试/远端访问/部署/新Run；5.3仍未完，后续“继续”先从P1本地准备推进。

# 2026-11-01 报告补充评估，三处漏放已本地修复

用户要求评估并多跑测试。本轮执行22个不同直接方法（4新增，含25个句式/协议/控制文本子场景），最新结果全通过。反例先证实后修正：双重否定被当未知、TLS版本被泛化、中文紧邻内部码漏检。新增r11四原回复/两Tool结果离线回放，完整raw/原usage12728/原预算保持，仍failed且未采纳坏报告；0真实模型/湖查询/新Run。历史缺口仅精确去重、重复压缩不改材料/引用已验证。初失败、测试fixture漏kind及旧反馈断言不适配分别保留，见docs/operations/investigation-report-context-evaluation-20261101.json；前一回执hash属修前快照，不覆盖原件。仍未部署/提交/推送/合并，不新增记忆系统；来源/关系真实语义及5.3继续未完。

# 2026-11-01 报告上下文本地修复，暂不新增Case记忆系统

用户在评估上下文必要性后同意继续本地修复。模型原文保留Case/Alert source_path；H保留原Run引用及最多2048字节完整未决条目，去掉对应重复缺口，原账本不改。纠错仅传字段约束，内部错误码留账本；已知r11指令泄漏拒收。协议空格/状态/引号误拒修正，无据肯定/否定/混合断言仍拒。14个受影响直接方法最新结果通过（3新增），初次额度失败和测试视图假设不适配已修，原件保留；网络纠错12252≤12296，Office追加16752≤17018。无单独Case文档记忆、向量库或额外模型。见docs/operations/investigation-report-context-20261101.json及当前审阅指南。仅本地未提交/部署，0远端访问/新Run/真实模型；r11两原答仍拒，来源推测与关系判断真实语义未验，5.3未完，不重跑已结束批次、不归档/推送/合并。

# 2026-11-01 保留r11问题，仅更新调查文档与审阅指南

用户要求“先保留当前问题，更新调查模块的相关文档和审阅指南”。当前只文档维护：统一r11/a543ad6（功能49a04eb）基线，修正文档仍写r1/r10在线、r11待部署及旧模型/Tool合同的冲突。新入口docs/investigation/review-guide-20261101.md登记R11-01协议误拒、R11-02纠错指令入正文、R11-03来源/无源推测、R11-04关系判断，以及R10-01空查询推理真实效果未验；均保留。原结束独审标明r3本地范围，原请求/响应/失败回执不改。无业务源码/测试修改、业务测试、远端访问、部署或新Run；OpenSpec16/17、5.3未完，不归档/推送/合并。后续“继续”先沿当前文档任务理解，不自动重跑已结束批次。

# 2026-11-01 r11已部署，正向样本真实查询通过但报告仍失败

用户选择新建明确标记测试样本后，r11/a543ad6（功能49a04eb）已部署，镜像59d9fe097588…，472实际源码hash一致；专用fixture租户新增2告警+2湖事件+1Case，唯一Run22b48b78-3716-5a64-994f-788d020dc760为failed/partial。两条raw371/425B在4次模型请求均完整；2正式真实查询各1行、2独立预检查询，全部QueryFinish核实，0复用，12728tokens/4调用未定价。首份与纠错JSON及成员均有效；首份协议待核措辞被拒，纠错后空格/状态/引号句式误拒与无源“文档服务器/故意缺失”、校验指令泄入正文并存，不能只放宽规则称通过。16事件18工件、30HTTP、75远端文件hash核；额外1只读状态查询单列。旧告警整行hash及r10报告字节保持，core/agents/网关/配置/开发Key保持。见docs/operations/investigation-r11-positive-fixture-20261101.json及evidence/investigation-r11-20261101/review.md。本批结束不重试；本轮未新增功能修复，复用7项直接验证；5.3继续待办，不归档/推送/合并。下一聚焦不确定句式误拒与纠错报告质量，不扩大框架。

# 2026-11-01 r11发布准备与样本选择待答复

r11更新包已本地固定，发布准备提交a543ad6（功能修复49a04eb），476文件含472应用源码及tar目录0755/文件0644已核。只读确认线上仍为r10，全部相关容器及配置hash保持。本轮0上传/部署/新数据/Run/模型，复用7项通过结果。已询问正向样本来源，尚无答复；仅准备专用fixture租户2告警+2事件+1Case+1Run的明确synthetic离线草案，未入库。见docs/operations/investigation-r11-preparation-20261101.json及openspec/changes/fix-investigation-audit-gaps/retest/r11/fixture-draft.json。下一先确定样本选择并核对原文与source_event_id/类别/窗口，再实际调查；不更改旧数据或报告。

# 2026-11-01 空查询数据原因与本地边界修复

本地`49a04eb`已修正三阶段共用证据规则、同源分诊摘要去重及程序生成的查询状态/数量，7个受影响直接用例最新结果通过（含2新增），未部署、0新Run/模型。只读核对确认生产湖6行均3002，Office两行raw为user.session.start，另fixture租户仅3条4001；现有完整raw告警没有对应进程/网络湖记录，不能放宽过滤或改造登录数据充数。新提示词真实语义仍未验，未新增通用语义校验器。 线上最近核验仍r10/51086a4，r10批次已结束不重跑。回执docs/operations/investigation-source-boundaries-20261101.json，详解docs/investigation/source-boundaries-20261101.md。原42方法为r10历史证据，本轮7去重方法复用未变通过项；初额度失败保留，最终网络12244≤12296，原预算保持。下一先提供有完整raw且对应真实1007/4001事件的正向样本；不补造旧证据，不归档/推送/合并，5.3仍未完。

# 2026-10-31 r10结构化报告与完整raw真实查询

用户要求按方案改后用完整原始告警跑一次、Tool实际查库不复用。源码`51086a4`已部署r10；首份正式报告使用JSON Schema，模型A引用映射公共UUID，具体校验反馈和原一次纠错/预算保持。唯一完整raw演示告警主Run `4f094ed4-b4f9-5db9-8cc2-b5f8c781858e` 为completed/partial：3模型、2真实湖查询、0复用、10292 tokens；首次报告格式/成员通过、纠错0。两次成功空查询经ClickHouse QueryFinish核实，报告却把空结果当矛盾并猜测采样/丢日志等原因，语义仍未过。 两条raw在三次模型请求完整未截断（canonical219/251B），为已有演示数据。42个受影响方法最新结果通过含7新增；原测试模板按新协议调整，初失败及最后通过日志保留，不计为单次42项重跑。12事件14工件、20HTTP/42原始文件hash核；3调用未定价。首次打包源码0600/目录0700令容器启动失败，未发调查；改应用源码0644/0755后同内容重建成功。472源码核对、core/agents/gateway/配置/原开发Key保持。见docs/operations/investigation-structured-report-20261031.json及live-r10/review.md。一次批次已结束，不重试挑结果；当前16/17、5.3未完，不归档/推送/合并。下一具体问题为空查询推理和告警—湖来源对应，不扩框架/权限专项。

# 2026-10-31 r9已获明确授权并部署，真实报告引用仍失败

用户明确确认后，r9源码bf2bd9c已部署21独立调查API，镜像sha256:d2e509370680cd2f647561ac37e1da4916758af7743324b0761f51b7f8090418，472应用源码核对一致。唯一Run a671b01b-7d2d-51d6-8c43-6eb634bdc5c8为failed/partial：首答json_invalid，一次纠错后关系条目重复A2 UUID，触发invalid_member_reference。3模型回复全部取得、11740已知tokens、1历史复用/0新湖查询；耗时1.36/23.81/26.50秒，未实际覆盖超过45秒等待。12事件14工件、23HTTP/48原件hash核，POST与GET一致，父报告字节保持；3调用未定价。共享网关/core/agents/配置/开发Key保持；6项必要直接验证复用，不重跑、不新增Run。完整报告语义仍未过，OpenSpec16/17、5.3未完，不归档/推送/合并。回执docs/operations/investigation-model-wait-20261031.json；之前自动审批拒绝保留历史，已由本次明确授权解除，不再视为等待部署。下一具体问题是模型JSON/成员引用及来源叙述，不扩大超时或重复本批。

# 2026-10-31 r9调查模型等待修复，本次部署被自动审批拒绝

本地源码bf2bd9c已修复Case模型等待：HTTP及LiteLLM单请求timeout采用原120秒调查循环剩余时间；仅已有bundled gateway携带timeout，直连/BYOK不加该字段。6项必要直接用例首次全通过（3新增）；21已安装LiteLLM 1.106.0超时选择函数替身验证97.25/7.5覆盖45，未调用provider。未改共享网关配置、预算或重试。r9包及唯一追加请求已固定、上传；构建/替换命令被自动审批以缺少本次明确部署授权和重启服务风险为由拒绝，命令未执行。已向用户确认是否更新独立调查API并执行一次原网络Case追加，等待答复，不绕过拒绝。线上仍r8；本轮0新Run/模型/湖查询。回执docs/operations/investigation-model-wait-20261031.json。OpenSpec仍16/17、5.3未完，不归档/推送/合并。

# 2026-10-31 r8协议不确定表述修复，真实纠错遇网关超时

用户继续后已修正有限中文不确定句式：允许TCP/443不直接证明HTTPS、HTTPS尚未确认；仍拒绝无据肯定/否定及同句夹带其他断言。纠错要求完整中文、无围栏JSON，强调未证实攻击≠证实非攻击。10项必要直接用例首次执行全通过（2新增），保一次纠错/24000总预算；源码a41ae07725d3afd7e31fd9c465b6aa586872ac37，r8已部署21，镜像sha256:1f0bfe52f92b402fe2c92ed5b66c1c7250e21c27a900a2299020355b21eb337b，472应用源码一致。

唯一Run f8350f2f-062e-5fd8-b0e3-b39108070726为failed/partial：首份结论在关系/问题中用A1/A2代UUID，原一次纠错已派发但45.25秒后HTTPStatusError；同期网关Timeout、配置45秒相符，未取得第三次回复，精确HTTP状态码未保留。3模型尝试/2成功回复/1历史复用/0新湖查询，7540已知tokens、第三次usage未知不能计零；10事件12工件、21HTTP/44原件hash核，父报告保持。来源标注功能可读；真实语义和不确定句式验收仍未完成。回执docs/operations/investigation-protocol-uncertainty-20261031.json。不重试本批或改网关共享超时；core/agents/配置/开发Key保持，当前change16/17、5.3未完、不归档/推送/合并。下一步聚焦调查调用的上游等待边界和真实纠错输出，不扩恢复/压力框架。

# 2026-10-31 r7来源标注交付，唯一真实Run结论被拒

用户确认后按计划修复来源叙述并只复验一次。源码f19cc70fcc3ebf68e44118acce302caa9f561108，21独立调查API已为r7，镜像sha256:c32e7b6c3979c8750bcb0342fecb14727cd199453c4362244e437c3ed5fb85f5；472源码hash一致。模型Tool增加source_alignment，报告程序生成query_sources和来源/逐行对应段；精确event_id对Alert.source_event_ids，不按同主机猜测，H1摘要/原始行/旧报告保持。30项受影响直接用例首轮29过1额度失败，精简重复提示后只复核3项全过，复用其他27项；旧网络纠错12292≤12296，未提高预算。

Run bbedc422-f659-5e21-8759-5511f0d510a4实际failed/partial，3模型/1历史复用/0新湖查询/11341已知tokens，12事件14工件、23HTTP/48原件hash核。首答Markdown围栏导致json_invalid；一次纠错正确说明复用H1无新查询，但在结论提未核实HTTPS/TLS（含否定/不确定表述），被原保守协议规则拒。还有未证实攻击→非真实攻击/维持closed的倾向和把未匹配称无告警，不能称语义通过；失败报告两成员not_assessed，未采纳模型原答。回执docs/operations/investigation-source-alignment-20261031.json。固定批次已结束，不重试挑结果；当前change16/17，5.3未完，不归档/推送/合并；core/agents/配置/开发Key均保持。

# 2026-10-31 r6协议结论和成员覆盖修复交付

继续按功能优先推进；源码7330a7c66c924addca0d11c59095df8edd972689，r6已部署至21独立调查API，镜像sha256:6b7483b300c09490b6fd311847eaff79ef5d98c02509b7fdf01ebf8327b3941a，472应用源码一致。新增窄协议名称校验及可读成员完整性校验，原一次纠错和预算保持；按HTTPX紧凑JSON核输入字节，29项受影响直接用例通过。仅新增网络追加Run62bb8d8b-c10a-5324-ba1c-1736a92ce20d，completed/partial，3模型/1工具复用/0新湖查询/12780已知tokens；两个成员均unresolved、遗漏0，无HTTPS/TLS/SSL结论；11事件13工件、22HTTP/46原件hash核，父报告字节保持。

回执docs/operations/investigation-network-report-fix-20261031.json。两项具体缺陷已修并实际复验；报告仍误称历史复用为新查、误述H1没有非空网络记录、把3行都说成匹配2成员，并编造英文nuclear引文，完整语义验收仍未过。当前change16/17、5.3保持未完成，不归档/推送/合并，不重跑本批；后续只聚焦这些具体来源叙述问题，不扩额外设计或测试框架。core/agents/配置/长期开发Key保持，无新Key/Case/Alert/概况刷新/worker。

# 2026-10-31 继续推进：r4/r5功能复验完成，报告质量仍部分未过

用户继续推进且要求功能优先。本轮r4更新后Office/网络主调查及追加4 Run全部completed/partial，两个主Run真实进入紧凑纠错并在原预算内完成。报告暴露无源名称/标签后，仅修正来源陈述、处置状态和复用说明，6项受影响直接验证通过，源码本地commit3324fea629d7b1bf9dab46dd9f9cd93ba8f36dd2；r5已部署，镜像sha256:f2555eb2a218e7d115bf98f0a3d212e0088f5e99a472be9e61bac99b1f0c57c3，472应用源码一致。r5只对已有r4主结果追加2 Run，均completed/partial；原报告字节保持。6 Run共16模型/6工具尝试/2实际湖查询/4复用/65209已知tokens，111HTTP、230原件hash核。长期全API开发Key保持有效，无新Key/Case/Alert/概况刷新/worker或其他服务变更。

共享回执docs/operations/investigation-functional-followup-20261031.json。预算、原生Tool、复用和读回功能目标已验证；Office新报告不再有PWS/NavVisor无源标签，网络报告仍把TCP/443称HTTPS、缺两成员判断且对closed状态解释偏强，不能称完整语义验收。旧追加change已5/5；当前审计change16/17，归档完成条件仍未满足，不归档或推送/合并。后续聚焦这类明确功能/报告问题，不扩额外设计或测试框架；不自动重复已结束批次。

# 2026-10-31 长期开发凭据与功能优先

用户最新要求“不要过多的做一些除了功能外的开发设计工作”：只做功能所需实现、必要直接验证和简短进展保存，不扩额外设计、测试框架或逐层审计门。用户在一年/两个原租户含生产的具体询问后明确授权“给你完整的全部的”，21已创建两枚一年有效scopes=["*"]的开发Key，至2027-10-31；私有映射文件/opt/sting-aisoc-socai2/private/investigation-dev-keys.json，root:0600，目录0700。键为原tenant UUID、值为Bearer，后续通过既有SSH在21读取并放入AISOC_API_TOKEN环境，绝不输出明文/复制进仓库；正常开发不再要求临时Key授权。只验证4次GET/200，未新增Run；原短期Key仍禁用。初次长期创建被自动审批拒绝，用户补充明确全权限授权后重试获准并成功。

r3实际已部署，固定批次已结束：3个主Run中LSASS completed/partial，Office和网络因纠错输入预算失败；两追加因前提不足未派发。8模型/6湖查询/29824已知tokens，8调用未定价；157原件hash核对、临时Key撤销401和删明文、core/agents/配置保持已核。共享回执docs/operations/investigation-audit-live-r3-20261031.json。随后仅本地修复超预算纠错视图，6项受影响直接用例通过：原真实输入和usage重放Office14007≤15074、网络12237≤12296；保原来源/结果/strict schema/预算/账本。模拟纠错通过不代表新真实模型已验，线上仍r3；不复跑原5body，不归档、推送或合并。

# 2026-10-31 r3更新与5个Run复验已获准，连接仍阻断

用户对“连接恢复后仅更新21调查API为r3，并使用现有有效凭据执行固定5个Run”的具体确认回复“继续推进”，按此限定范围继续执行，不再重复请求同一部署/调用授权。仅现有身份，不新建Key/用户/角色，不恢复权限专项、F5、worker、推送或合并。新SSH前提尝试192.168.1.21:22在10秒连接阶段超时，未执行远端命令；本机Wi-Fi为192.168.3.57，到目标走默认网关192.168.3.1，未观察到专用路由，未改网络设置。见docs/operations/evidence/investigation-audit-fixes-20261031/authorized-preflight-20261031.json。待恢复该入口连通或获知有效新入口后沿固定5body继续；本轮0上传/构建/部署/新Run/真实业务调用，既有凭据可用性未核实。源码/测试无变，复用31项及独审0必须修，任务仍14/17，不归档。

# 2026-10-31 调查本地交付与结束独审完成

用户再次要求“继续推进”。源码/测试/部署准备10文件已本地提交bb8dbc321dca574ce19b37ec524051f5ed16b421；独立investigation_end_review结束审阅0必须修，见openspec/changes/fix-investigation-audit-gaps/audit.md，复用已有31项结果、业务测试重跑0。476候选文件绑定源码commit：36逐字节相同、440仅Git换行规范化，冻结tar/manifest不重写。已固定两个租户/三个已有Case的5份定向请求，静态校验通过、0派发；旧全案例runner含建案/概况刷新不用于此次限定复验。任务完成14/17，4.3/4.4/5.3仍待。既有SSH alias的只读docker inspect前提检查在连接192.168.1.21:22时超时，未确认在线版本；不是审批拒绝。不部署/改权限/真实业务调用/推送/合并，下一实际更新及调用沿原授权边界处理。

# 2026-10-31 调查审计计划推进执行

用户随后要求“推进执行”，覆盖下方同日仅规划限制。本地实现A01进程类型/查询版本、A02同锁前置权限与失败来源模式、D01原始来源冻结/模型视图/指纹兼容；31个不同受影响直接用例最终通过。Office冻结样例当前纠错16929≤17018，完整历史不变；原始OCSF编号保账本、模型使用语义类别并说明省略，原guard未关闭。见docs/investigation/audit-fixes-implementation-20261031.md及docs/operations/investigation-audit-fixes-20261031.json。准备独立r3候选，未构建镜像/部署/真实调用/提交/推送；未参与实现者结束复审待安排。两个change真实任务均保留，未归档；F5/JWT/worker/恢复压力和旧2.2/2.3不扩展或核销。

# 2026-10-31 调查审计后OpenSpec规划

用户要求“做好规划 openspec”。新增openspec/changes/fix-investigation-audit-gaps，proposal/design/3项capability规格/tasks/validation齐备；按A01进程类型与查询版本→A02锁内前置权限与失败来源模式→D01有界原始材料/模型视图/指纹兼容→组合验证及一次结束审阅推进，17项实施任务均未执行。已有fix-case-followup-gaps保持4/5，真实更新/复验与新change共用一次实际批次回执，不重复实现或测试；仅为旧规格补缺失Scenario。仓库本地OpenSpec1.13.0可用，不再将PATH无命令理解为工具不存在。当前仅规划和CLI/文档静态校验，不开始功能编码、业务测试、远端更新、提交/推送或合并；新规格未同步主库、未归档。原2.2/2.3及F5/JWT/worker/恢复压力边界不变，详细校验见新change的validation.md。

# 2026-10-31 调查模块设计到实现详细审计

用户要求在已对齐资料上做完整详细审计。报告docs/investigation/design-implementation-audit-20261031.md，静态清单docs/operations/investigation-static-audit-20261031.json；业务源码仍为5b95138。确认A01进程Tool缺事件类别过滤、A02基础概况刷新失败保留Case旧文时stale/权限与提交顺序不一致；D01为已有告警正文/原始材料未进入Case投影的设计缺口，均未改业务代码。文档模型输出上限1200修为3000、主设计顶部F4/事件回显状态修正。47实现/依赖文件哈希、11测试文件51定义、19业务method/path静态索引；207响应及3冻结文件hash一致，475部署文件470同5不同。没有运行业务或测试、真实访问、部署、权限变更、推送或合并；旧证据保留，最新本地6项不能替代r2真实复验。后续仅按具体功能缺陷补必要验证，不扩恢复/压力/JWT专项或F5。

# 2026-10-31 调查文档与测试基线对齐

用户要求核对文件是否最新并对齐指南。当前入口docs/investigation/audit-guide-20261031.md；本地业务源码基线5b95138（2026-10-29）。F4、事件Case结果关联、公共索引/证据导航及产品主机Tool已有代码，120/121已有安装回执。最近真实四案例为512c004/r1：207次HTTP、111项检查3项失败、2/4案例流程通过；最新追加修复仅本地6项直接用例通过，r2常驻更新和真实复验待做。远端状态仅据已有回执，本轮未连接确认。下方旧日期的未实现/未部署状态按历史基线解释，不覆盖此入口。

本轮仅对齐文档、链接和已有证据，不改业务源码、不重跑业务测试或真实调用；历史失败/请求/响应保持原件。权限专项、部署、推送、合main不恢复；F5/自动Case政策不纳入当前目标。后续审计逐功能对照代码与证据，已通过且未变化的部分复用，不扩展冗余测试。

# 2026-10-27 调查详细审计文档补全

用户最新要求“细化设计的细节到接口，具体实现暂时不用”。新增docs/investigation/interface-contracts-20261027.md，逐项定义已有F1/F2/F3及拟新增F4、Case历史列表、F5内部HTTP、模型/Tool和产品HTTP映射，含字段/错误/状态/示例/调用顺序；拟新增均未实现。仅文档静态检查，不运行代码或测试，不恢复权限/部署/推送。

用户后续要求先对齐当前设计；设计入口docs/investigation/current-design-alignment-20261027.md，整理Alert/Incident/Case/Run职责、自动/手动、流程及例子，标明F4/F5和事件Case结果回显尚未接通。旧主设计保留历史语义；F3直接验证终点修为Case/Run读回，F4输出限定成员转Case，报告归F3。本轮仍仅文档/静态核对，不扩展设计或功能编码。

用户本轮要求提供完整审计文档链接并补不足。入口docs/investigation/audit-guide-20261027.md，当前实现详解current-implementation-reference-20261027.md，完整相关文件目录evidence-catalog-20261027.md。源码基线6044615；仅静态核对/文档/链接检查，无业务源码改动、业务测试或真实调用。已明确F1/F2/F3代码与旧fixed/program/Agents Deep的区别、现有替身证据及真实未验范围，修正旧下一步/路径易混处。F4/F5和OpenSpec 2.2/2.3保持未完成，权限/部署/远端推送不恢复。

# 2026-10-25 调查模块功能实施原则与继续开发

用户最新确定业务边界：事件只需保留现有汇总与AI概况，真正调查分析统一放Case（案件）。F3改为Case内实际分析/补查/报告（首个场景可为单Alert Case），F4改为告警/事件选择成员创建或关联Case；不新增Incident调查profile/另一套事件分析循环。此条覆盖下方历史“单Alert独立深入调查/事件直接Run/Case关系待定”建议。功能逐个直接验证原则继续适用。

F3第一版已写入独立API v2 case_analysis/模型协议/进程与网络工具/Case路由；Case成员和窗口固定，原ledger留存模型/Tool消息/证据/报告，真实Case ID归属，不改旧fixed/program解释。4直接ASGI+ledger/模型HTTP/事件湖替身用例修后通过：完整链路及重读、空/失败区分、同源历史查询复用、unknown usage停止；无真实PG/模型/CH或部署，不称真实模型自主选工具/业务质量已验。见docs/investigation/case-investigation.md。下一F4告警/事件成员转Case入口，专项Deep/产品HTTP等能力尚未全部接入；不扩展事件分析、权限或冗余测试。

当前进度F2：事件AI概况功能代码及直接验证已完成，见docs/investigation/incident-ai-overview.md。新增incident_summary/独立incident_summary_worker、GET附概况元数据和POST手动refresh；新表迁移120尚未执行，后台任务/部署尚未启用。8项相关ASGI/DB与模型HTTP替身用例通过，实际模型/PG调用0；首次仅尝试一次，后续手动刷新，变化只标旧，失败保旧文本。深入调查结果尚未接入，source_refs明确not_linked；下一F3单Alert主分析/必要查询/报告及事件Run结果关联，不返回权限或冗余测试专项。

用户已要求继续之前的调查功能计划，并明确把以下要求写入模块原则：以实现功能为目标；逐个功能实现、逐个必要直接验证、通过后推进；不开展冗余、可用性/恢复/压力/复杂并发或故障注入扩展测试，不为验证写过多辅助代码/框架；已通过且未变部分不重复测试，评审不再新增逐层前置门。主原则见docs/architecture/investigation-planning-design.md的implementation-principles，README和五批计划已链接。从F1事件/分诊汇总开始实施，历史“本轮只文档”不再阻止开发。权限专项仍暂停，无自动部署/合main或真实厂商动作授权；本地阶段保存，远端推送不自动恢复。

F1现已完成：新增API v2 incident_reader/incident_api，兼容结果/启动factory挂GET /api/v2/investigation/incidents/{incident_id}；PG告警归属取canonical成员，raw_alert.id明确对应的最新triage_verdict与当前Alert处置分开显示，不猜Run.case_id、不自动关事件。4个直接ASGI/SQL替身用例通过，0业务外呼/模型/新表/部署；未称真实PG或权限验收。见docs/investigation/incident-investigation-implementation-plan-20261025.md。下一F2首次/手动AI概况，F3实际分析/Run结果关联等未完，不回到旧权限专项。

# 2026-10-25 事件概况与调查流程落文档，先评审规划

用户要求先保存当前业务流程，再做一轮评审与实现规划，本轮不开始功能编码。见docs/architecture/incident-investigation-flow-20261025.md及docs/investigation/incident-investigation-implementation-plan-20261025.md：Fusion Incident汇总展示所有成员分诊及调查进展/结果，动态事件数据与AI概况分开，真正分析/补查放调查；Incident不等同Case。功能顺序F1事件当前数据/分诊汇总、F2首次及手动AI概况、F3单Alert主分析补查报告、F4事件成员调查、F5原自动入口接线。权限专项仍暂停，不以历史下一b恢复；不加可用性/恢复/冗余测试或逐层独审门。后续实现以直接功能验证为准，本轮只文档链接/差异检查；历史2.2/2.3仍未完成，无业务调用、配置变更、部署或合main。

# 2026-10-25 用户要求按功能收尾，停止扩展冗余测试

用户再次明确以功能完成为准，不做过多可用性、恢复、故障注入或冗余测试，本轮进行阶段收尾。必要的直接功能验证及具体缺陷修复仍保留，已通过且未变化的合同不反复重跑；审查建议不自动变成新的功能前置门。M8a4.4b真实JWT/RBAC继续暂停，不因下方历史“下一b”自动恢复。审查基线7908f73，结果见docs/investigation/design-implementation-review-20261025.md；上一轮124项离线合同和独立审阅已完成，本轮直接复用，不增加业务测试或真实访问。当前手动单Alert/TCP443固定来源核对、持久发布读取按已实现范围收尾；Case/Deep/自动政策、完整业务判断及新启动真实整链仍如实保留未完成，不核销整个change的2.2/2.3。保存审查/证据与阶段提交推送，无业务源码修改、部署或合main。

# 2026-10-25 调查M8a4.4a真实PG零外呼限定通过

abf3d58后已审a卡，新program_admission_pg_seam/13新＋相关134=147直接/独立同147，13源码SHA/2本机helper/实际PG原件结束独审限定ACCEPT0，见docs/operations/investigation-program-admission-pg-20261025.json及evidence同名完整原件。PG16.15/41ledger列10约束实际兼容、Alert无自定义trigger；实际旧reaper/Hunt均原有关闭、Kafka0保持，0部署/旧改/schema改。新3合成Alert：normal721b6c99-26f4-55d5-b773-21ca9c618400实际precommit2/3不可见、三独立PID有传递锁等待、同key只读/不同key无Run，释放后0tool/0model发布partial5/11/MD2113B；rollback b6e4…0；ACK b7f95ff4-0be1-5465-89f3-9f4cfb204b85保真实commit2/3/ready，显式read/repeat不入runtime，严禁补跑/重置。两Run legacy running/null/0/0是原合同，不计业务完成。新普通TLS角色锁前拒/仅Run.iterations与Alert.updated_at单列grant后成功且rollback，结束两role NOLOGIN/所有表列effective及explicit ACL0/memberships active0，无遗留连接。独审真实只读核3目标恰2Run、28新旧工件/所有选中列/fullintent/actualAlert→M1-plan/owned+独立API三DTO同，旧6/14/3111B不变。代码P2提前owner错被timeout/cleanup遮盖已修并保原件，3Loader错名和审计JSONB表现/SSH沙箱差异分列非业务fail。下一b真实JWT/RBAC卡顺序P2修后ACCEPT0，a保存后实施；新tenant/viewer精确权限、原Redis独立helper bump且排除TTL自然到期，不用stub409宣称business200。b/cHTTP-CH/Case/Deep/自动政策及2.2/2.3未完，无合main。

# 2026-10-25 调查M8a4.3d双进程离线启动组合限定通过

0041f3c后已审d卡再仅新program_start_offline_seam及14直接，API120＋独立Agents59共179直接/独立同179、10SHA/6新隔离SQLdouble账本80API44Mockbackend62stdio、35事件74工件限定ACCEPT0，见docs/operations/investigation-program-start-offline-20261025.json。actual新factory/auth依赖/当前注入用户→新内部app/coordinator→完整event-pin intent actor/预算→runtime/pub/owned/GET链核，客户spoof头无效、换currentactor/窗口409；normal7/15/Mock1、zero5/11/0、queryunknownpartial、admissionACK5032/3/pubACK5037/15/父丢一次完整回包503后显式read/repeat/GET同且0新增。6ledger互相隔离同稳定Run公式，非共享库6不同Run/真实PG并发。原API请求/header/body/hash及实际注入CurrentUser、全回包/ledger/cold hydrate保。独审P2 cleanup异常遮primary/0B回执已修，1red0fail1应用error/完整原件保failure8文本；2子目录Windows tempfile权限未进probe的未完成轮单列，已核自有句柄清理，不计应用fail/通过。仅Mock/ASGI无真实访问/业务Run/模型/部署，旧源/MD保持。下一a4.4a真实PG零外呼卡初并发假阳性P2补precommit真实锁等待＋postcommit双barrier后独审ACCEPT0，d保存后实施；b真实JWT-RBAC/c实际HTTP-CH另门，2.2/2.3/Case/Deep未完，无合main。

# 2026-10-25 调查M8a4.3c现用户写网关限定通过

086e0bb后已审c卡再仅新增API program_start_gateway/program_start_api及可移植15实际producer outcomes；41新＋API相关65/Agents独立59共165直接/独立同165、9SHA/38原API响应和31Mock请求重放限定ACCEPT0，见docs/operations/investigation-program-start-gateway-20261025.json。原explicitBearer/CurrentUser run＋alertsread，原shared read service403/backend0，伪Xactor/tenant无效、下请求权限/凭据重核；完整knownoutcome/admission/run-owner/原compatibleDTO全核，合法MD保持。HTTP只一次、4KiB/1MiB/总200秒、response和client关闭各5秒；独审1P2为HTTPX正常EOF隐式close绕清理界，修stream代理后原完整12867B例200/HTTP1，gzip保持。原11文本保failure（初38的2fail1测试error、两Loader误模块名、P2完整源/反例/观察），原业务旧源/MD保持。仅ASGI/FakeDB/Mock及producer缓存，API不凭request_hash证明原actor/budget来源；d双进程实际intent绑定细卡已独审ACCEPT0，保存后实施，再a4.4真实JWT-RBAC/PG/运营隔离。2.2/2.3/Case/Deep未完，无真实访问/业务Run/模型/部署/合main。

# 2026-10-25 调查M8a4.3b独立内部写HTTP限定通过

5b7c0db后先合同/strict/独审（两个POST协调器拒统一409，原GET404不改）再新program_start_api及先config后HTTP。10policy/config＋30HTTP及相关146共186直接/独立同186、7hash/8actual＋14fake冻结限定ACCEPT0，见docs/operations/investigation-program-start-api-20261025.json。先当前专用HMAC/tenantactor再4KiB流读/重复key/Pydanticstrict/servernormalize；controlled target config/ref不证明真实legacy隔离。独审发现轮换write token误复用当前read/tool后两例200/SQLMock7/15，已补逐请求动态分离；2red2fail/修前完整源/独立原件保failure，修后401/SQL0/Mock0，明确为可信运营误配置非客户端改state。另config10首1fail（顶层array下游本已拒）/HTTP语法0tests单列保。独审原6账本+2空case+14fake共28 ASGI raw/hash同、33原响应hash/取消无响应记录核，未冒称重做首次写/取消；normal7/15/Mock1、ACK503后readonly，旧源码/MD保持。新TLS/cleanup/注入不误关已验，无真实PG/network/userauth/业务Run/部署。下一c用户run＋alertsread写gateway合同已审（200s整次POST/stream、收尾有界），保存后实施；d/a4.4实际门及2.2/2.3/Case/Deep未完，无合main。

# 2026-10-25 调查M8a4.3a一次启动协调器限定通过

160b0b9后先合同/strict/独审再仅新program_start_coordinator/23直接，＋admission29/runtime25/pub29/owned19总125直接/独立同125、7hash/14原件（12原ledger全outcome冷读/repeat同、2guard拒0SQL）限定ACCEPT0，见docs/operations/investigation-program-coordinator-20261025.json。mandatory server guard/current身份→仅fresh committed入原claim/M3 reserve→confirmed stopped才pub；不再begin，repeat/read即使已停未pub也不补跑/发布，cancel/ACK未知保持。normal7/15/Mock1，zero5/11/0HTTP，unknown/错误partial，失败保缺口。独审额外两取消接缝及独立API全12 ownedDTO兼容通过不累计125；URL空白配置前置拒。guard仅替身/引用不证明实际legacy隔离，旧service scopes不扩，无真实PG/network/auth/业务Run/模型/部署。下一b独立write-only HTTP+受控目标配置合同修POST拒绝统一409后已独审ACCEPT0，保存后实施，再c用户run+read/d组合/a4.4真实接缝；2.2/2.3/Case/Deep未完，无合main。

# 2026-10-25 调查M8a4.2原子手动准入限定通过

5d6d129后先合同/strict/独审（READ COMMITTED/Alert锁后全Run重查P2修后ACCEPT0），仅新program_start_store/SQLdouble。29新＋相关107总136直接/独立同136、7hash/11完整原账本hydrate→晚3天repeat→owned全request/receipt/DTO不变，限定ACCEPT0，见docs/operations/investigation-program-admission-20261025.json。稳定tenant/key Run+原begin1/2+独立nonunified immutable-event-pin意图1/1同TX2/3；逐写失败全rollback/ACK未知0进入，重复不重开owner/期限/预算；同Alert active/unknown阻新key，已停显式新key可准入，reserved坏marker不漏。正常原runtime→pub7/15/Mock1，旧源码/Run列/MD保持；初21的1fail14应用error为重建limits漏原USD项已修，全部原source/tests/log保failure。独审额外Decimal PG Numeric及第三key连续场景通过不累计136。0真实PG/network/业务Run/模型/部署；下一a4.3a协调器合同已独审ACCEPT0，保存后实施，再b内部HTTP/c原用户run+read权限/d组合及a4.4真实接缝；不扩大只读service权限，2.2/2.3/Case/Deep未完，无合main。

# 2026-10-25 调查b2.4d4双进程离线组合限定通过

dc50569后先合同/strict/独审再仅新增offline probe/9直接，API74＋独立Agents40总114直接/独立同114、8hash限定ACCEPT0，见docs/operations/investigation-compatible-offline-20261025.json。12合法完整账本双读24次、2unknown账本拒，39完整观察＋nil单列=40API请求/32Mock backend/34stdio。独审hydrate原14账本/原UUID跨两进程完整复放39row/主体/全body同，不用随机新fixture冒充；原PID10960/独审4264 exit0回收，真实HTTP和DurableTool guard0。整次write/read≤30秒、EOF/JSON/帧限/读写timeout无重放/failed receipt保存及owned Popen清理通过；测试会话tenant adapter不称RLS。0实际PG/network/业务Run/模型/部署，旧源码/MD保持。下一a4.2 Run+unchanged begin+独立event-pin意图原子准入合同修READ COMMITTED/锁后重查P2后已独审ACCEPT0，保存后实施，再a4.3权限/启动政策与a4.4受控真实新Run；2.2/2.3/Case/Deep未完，无合main。

# 2026-10-25 调查b2.4d3独立API兼容网关限定通过

2e95081后先合同再仅新API program_result_gateway/program_result_api，原Bearer/CurrentUser双read权限及独立COMPAT配置，无旧app注册/fallback。45新＋oldAPI13/query7及独立Agents40共105直接/独立同105、8hash/34完整HTTP重放（25producer DTO/9边界、32Mock调用）限定ACCEPT0，见docs/operations/investigation-compatible-gateway-20261025.json。旧3111B为缓存协议参考非PG账本重建。初3P2/7自洽反例修ready必要门/已知问题事实/typed材料；后4合法error误拒修nullable未知count/limit/window及声明与确认分离，4red4fail＋3red3fail＋4red4应用error及完整源码/原件保failure。所有25合法输出保持，未知不改0/false；原7全拒。0真实PG/network/UserRBAC/Run/发布/部署，旧源码/MD保持。下一已审d4两独立app包有界stdio离线组合，之后a4.2原子准入，2.2/2.3/Case/Deep未完，无合main。

# 2026-10-25 调查b2.4d2独立兼容内部GET限定通过

673f225后合同/spec/strict/独审ACCEPT0先行，仅新program_result_api factory/独立COMPAT token/PG/CA配置，无oldenv fallback/旧app注册。21新＋oldAPI13/compatibleReader19/newpubstore29共82直接/独立同82、6hash/24ASGI完整重放（actual reader SQL7/fake边界17），receipt docs/operations/investigation-compatible-internal-api-20261025.json限定ACCEPT0。Bearer/currenttenantactor/nilRun/bodyquery拒、known双schema/exactidentity/pubstate最小envelope；fake只边界不代owned，实际来源d1、完整DTO/hash仍d3。pool TLS/optionalnewCA/启动脱敏/close timeout terminate/injected不关闭，独审真实asyncio超时额外核不加第83项。0真实PG/network/UserRBAC/Run/写/部署；oldAPI/MD保持。下一d3 API网关五类result/evidence组合合同修后已ACCEPT0，后d4组合再a4.2；2.2/2.3未完，无合main。

# 2026-10-25 调查b2.4d1双版本owned读取限定通过

ce4c14a后先合同/strict/独审；仅known begin查询会漏unknown历史事件的合同缺口补为同锁全Run unified_ kind+agent检查后ACCEPT0，再新CompatibleOwnedReconResultReader。19新＋oldreader13/newrestore16/newpubstore29/oldpub21共98直接/独立同98、7hash/7完整账本双次cold/所有原件pin/DTO canonical/Run6列核，receipt docs/operations/investigation-compatible-owned-reader-20261025.json限定ACCEPT0。显式known ownedbegin分旧/newrestore-store，owner仅原serverstate、不caller选版；unknown前中后/混版/wrong或NULLagent拒无fallback，同conn不嵌套lock。旧3 SQLfrozen全部raw/DTO/MD同旧（3087/1847B），新pub/progress/observer/rev2同；真实旧3111B仅cache/原文件SHA核不称PG账本重建。0真实访问/Run/新调用/写/发布，旧源码/入口/MD保持。下一d2独立COMPAT内部GET合同已ACCEPT0，d3gateway/d4组合后a4.2；2.2/2.3未完，无部署/合main。

# 2026-10-25 调查b2.4c新版冻结恢复限定通过

8724920后合同/spec/strict/独审先行，仅新program_profile_restore。16新＋oldrestore11/newpubstore29/M1scope8/profile11共75直接/独立同75、6hash/原6冻结+新增rev2全request重建、3SQL全读同DTO/MD/usage，receipt docs/operations/investigation-program-profile-restore-20261025.json限定ACCEPT0。初74外合法M1 previous→rev2/plan/newstore1/2可保存却restore拒P2已修，原合法begin/源码/1red0fail1应用error保failure；先重建固定M1base再带回caller已核positive原revision+canonical全比，不伪造previous或证明历史链，额外合法rev3也通过。当前tenant许可与frozen principal分开，无liveAlert/clock/查询/重启权；oldrestore不改。下一d1 owned双版本入口（合同待审）→d2内部GET/d3gateway/d4组合，再a4.2；2.2/2.3未完，无真实访问/新Run/部署/合main。

# 2026-10-25 调查b2.4b新持久发布限定通过

41bc92e后先合同/spec/strict/独审ACCEPT0，再新ProgramReconPublicationStore，29新＋oldpubstore21/newpub24/newstore30/newruntime25共129直接/独立同129、7hash/7完整cold/repeat/所有event工件/Run6列重建，receipt docs/operations/investigation-program-publication-store-20261025.json限定ACCEPT0。初127外seq float/int回执窄缺口修后strictint/canonical identity及原begin/current同核，1red1fail0error原件保failure。actualtool→材料/handoff原件完整重建含未采用、唯一newmarker/4工件1TX，ACK未知不成功、repeat无通知重发；late保账而read/republish拒stale，plainprogramwriter拒unknown pub不回退。normal6/14/MD3381B，observer5/13，late7/16；仅SQLdouble未真实发布/访问/新Run/通知。下一c新恢复合同已ACCEPT0→d owned/HTTP→a4.2逐门；旧源码/MD3111B保持，2.2/2.3未完，无部署/合main。

# 2026-10-25 调查b2.4a新发布候选限定通过

ec460ae后先spec/design/strict/合同独审，unadopted完整结果重建合同缺口修后限定ACCEPT0再实现，仅新program_recon_publication。24新＋oldpub16/newstore30/newruntime25/newrecon16共111直接/独立同111、7hash/9完整package/MD/section重建及额外8反例拒，receipt docs/operations/investigation-program-publication-preparation-20261025.json限定ACCEPT0。独审初109外bool/int等值与stopped冒充source两个P2已修canonical和distinct pre-stop，修前2red2fail0error保failure；collector Request deepcopy身份误断言原件单列非源码。newmanifest/exec/full版本/安全MD明确有限目标/全文未语义核/模型资格false，normal4facts ready、escaped21facts ready，其余7partial；旧MD3111B保持。纯candidate、持久ref空无发布/通知；原tool/owned/event真实链后续b新pubstore→c恢复→d owned/HTTP，再a4.2，2.2/2.3未完，无真实访问/新Run/部署/合main。

# 2026-10-25 调查b2.3d2新版来源投影限定通过

fbd1b1d后合同/spec/strict/独审先行，仅新program_alert_projection及15新＋旧projection13/newstart18/newruntime25/oldrestore11共82直接/独立同82、6hash/6完整投影/两冻件及预建Run SQLMock接缝cold完整重建，receipt docs/operations/investigation-program-alert-projection-20261025.json限定ACCEPT0。新意图先完整核/新doc schema，无旧转换；原source/hash/路径及IP/UUID原拼写保全，normal1307B/最大17759B不截，新4facts有限ready/model false、旧仍partial。预建Run1/2→5/10/Mock1，重复不增，oldrestore明确拒新begin。BusinessProfileRequest不证明真实auth/owned或intent-budget-owner-Run原子绑定；0真实访问/新Run/发布。下一b2.4 a纯newpub→b持久→c恢复→d owned/HTTP显式版本，各另门后a4.2；2.2/2.3未完，旧源码/MD保持，无部署/合main。

# 2026-10-25 调查b2.3d1新版启动意图限定通过

b90cb80后spec/design/strict/合同ACCEPT0先行，仅新program_start_contract及18直接；＋oldstart13/newstate18/profile11共60直接/独立同60、6hash/6完整意图决定重建/UUID公式核验及27额外类型/旧原件/混版反例拒，receipt docs/operations/investigation-program-start-contract-20261025.json限定ACCEPT0。newrequest/intent/ref/decision含closed12版本，tenant/key Run/executor同旧；旧新同key异文冲突不升级/转换，StartBudgetPolicy语义/schema不改。pure双授权false，不造deadline/Run/持久性；下一d2显式新投影（合同待审）→b2.4兼容→a4.2，2.2/2.3未完，旧源码不改、无真实I/O/部署/合main。

# 2026-10-25 调查b2.3c单次控制器限定通过

503f75e后c合同/strict/独审先通过再新增ProgramReconRuntime，仅接newstore/manual/closedplan并复用原M3 gate。25新＋旧Fixed18/newstore30/M3gate9共82直接/独立同82、7hash/8完整账本与cold全输出重建，限定ACCEPT0，receipt docs/operations/investigation-program-runtime-20261025.json。预留实际回滚与已提交ACK未知分开验均0HTTP，重复/owner取消/duplicate竞态/observer buffer不误采用；独审另验reserve已commit未返回取消保unsettled/partial。normal全文1299B/一次Mock可4facts有限ready，旧报告3111B不改。初扩测试1fail1error为Case profile与M2 checked-error误断言，原件已留；审计助手包装比较失误单列，不归源码。0真实PG/HTTP/Run/发布，d1合同已ACCEPT0后新意图→d2投影→b2.4兼容→a4.2逐门；2.2/2.3未完，无部署/合main。

# 2026-10-25 调查b2.3b持久层限定通过

f4429e0后先spec/design/strict/合同独审，新增ProgramReconExecutionStore/新30＋相关61共91和独立同91、7hash/8完整SQL账本冷读重建，receipt docs/operations/investigation-program-runtime-store-20261025.json限定ACCEPT0。初审85之外4个P2及作者unknown-kind回退缺口已修，修前3red3fail与另1red1fail/源码保failure receipt；当前/原begin/原tool/真正前一source/closing state链完整核，late actual只账变不改候选。normal1299B有限4facts ready，observer不采用/未知保持，失败和ACK未知不重派，旧Run六列不变。仅SQLdouble，0实际PG/HTTP/新Run/发布；c合同已ACCEPT0后薄controller/MockTransport→d新intent投影→b2.4兼容，再a4.2实际准入。2.2/2.3未完，无部署/合main。

# 2026-10-25 调查b2.3a新运行状态限定通过

e2b0291后先spec/design/strict/独审，trigger权威缺口已以新runtime固定manual关闭；新增program_runtime_state/18新＋旧state12/M3state12/program_recon16/profile11共69及独立同69、5hash/7完整状态重放/7额外重hash反例拒，receipt docs/operations/investigation-program-runtime-state-20261025.json限定ACCEPT0。闭合12组件/scope+manual重建profile/plan/new step-attempt，旧state不升级；M3单账、预检不授权I/O，重复不接管、unknown/late实际结算保原handoff。0真实PG/HTTP/Run/claim提交，下一b持久store/c单次controller/d新intent投影、b2.4兼容后才a4.2，旧automatic路径保持，2.2/2.3未完，无部署/合main。

# 2026-10-25 调查b2.2新有限事实限定通过

984646f后spec/design/strict/合同ACCEPT0，仅新program_recon及16直接＋ProgramMat12/旧fixed13/A3material10/adoption13共64和独立同64、5hash/11完整请求输出重建、额外5源×6停止30对照一致，receipt docs/operations/investigation-program-recon-20261025.json限定ACCEPT0。新事实/完成/result/prep版本，ProgramMaterial仅读结构字段不伪model view；1299B normal新4事实有限ready/十转义同short新21事实ready，旧路径仍partial，模型未请求/无资格、全文未语义核、Q3a/b/Q4与性质授权未知。空/失败/unknown/冲突/截断/子窗/5停止partial，missing not_confirmed/null/unknown。0真实I/O/Run/runtime/发布选择，下一b2.3a状态版本→b store→c controller→d新intent投影，b2.4同版兼容后才a4.2；旧源码不改，2.2/2.3未完，无部署/合main。

# 2026-10-25 调查b2.1独立程序材料限定通过

c253f15后按A窄路线先spec/design/strict/合同独审，新增program_material12新＋projection13/EvidenceView11/A3material10/adoption13共59和独立同59通过，5hash/6完整M1冻件/2同输入对照重建一致，receipt docs/operations/investigation-program-material-20261025.json限定ACCEPT0。ProgramMaterial独立schema/policy/ref，非EvidenceView/无model_view/not_requested eligiblefalse；完整Alert仍scope_sources只ref/hash/size，必要来源校验与旧缺口不变。1299B旧Alert512门仍阻断新材料1record，十转义同短scope旧16842B模型view超12288阻断新材料10records。旧EvidenceView/A3/adoption源码保持，无facts/ready/真实I/O/运行接线。下一b2.2新事实/prep/完成政策→b2.3冻结新runtime组合→b2.4M7/a1/owned/API新旧兼容及旧MD字节不变，全部通过才a4.2；2.2/2.3未完，无部署/合main。

# 2026-10-25 调查M8a4.1b1完整来源冻结限定通过

9bc7498后合同独审先发现完整文档结构性超过Alert512B消费门，已拆b1完整冻结/兼容/当前partial及b2正常消费门；b1修后合同ACCEPT0再实现。alert_projection13新＋start13/restore11/A3material10共47、独立同47/5hash/6完整观察/SourceField路径及原文保全通过，receipt docs/operations/investigation-alert-projection-20261025.json限定ACCEPT0。普通无synthetic来源可完整冻结，M6 begin SQL双1event2artifacts→a1精确恢复；normal1299B仍经现A3 alert_excerpt512阻断、facts0/六问unassessed/partial，绝不计ready/可用启动。下一b2另卡留存/消费分离，正常有限事实ready后才能a4.2原子准入；不截原件/提门，不改旧代码，0真实PG/HTTP/模型/Run，2.2/2.3未完，无部署/合main。

# 2026-10-25 调查M8a4.1纯启动操作限定通过

77e9f4d后先spec/design/strict及fresh_design合同ACCEPT0，新增start_contract/13新＋M3state12/M1scope8/profile11共44与独立同44通过，5hash/4 intent观察重建、6额外类型反例拒，fresh_code代码及公开receipt限定ACCEPT0。回执docs/operations/investigation-start-contract-20261025.json。tenant/key派生唯一操作身份，actor/目标/窗口/版本/服务端预算入独立request hash，同键异文冲突、匹配仅读；both may_begin/external false。duration1..180无生产默认/无真实deadline，0I/O/Run/模型。下一a4.1b正式canonical Alert投影，a4.2同事务Run+M6 begin+独立marker、a4.3写权限/首次commit后派发、a4.4新受控Run；当前不证实际auth/owned/持久唯一/Case/Deep，2.2/2.3未完，无部署/合main。

# 2026-10-25 调查M8a3.3双进程真实只读GET限定通过

基线e55c4d6，先合同/strict/离线12新＋24相关36及probe P2修后独审；原修前源码/12red7子fail0error和首修bool/int缺口保公开failure。新两个loopback apps真实16GET（2成功/14拒绝），实际service当前actor/tenant转发、原6/14全选中列/正文checksum、M7 manifest/MD3111B/execution与原M6基线不变；0新Run/查询/模型/通知。新m8r角色NOLOGIN/显式ACL0/有效ledger和auth权false/活动0，owned三PID已停。fresh_evidence独立36/10source2helper/READ ONLY PG全14和完整DTO/清理核验限定ACCEPT0；回执docs/operations/investigation-result-http-read-20261025.json。三表41列/10约束已核供启动，case_id非Case FK。下一M8a4稳定operation/owned正式Alert投影/原子Run+begin、独立写权限后受控新Run；当前真实用户JWT/RBAC撤销/启动/Case/Deep未验，2.2/2.3未完，无部署/合main。

# 2026-10-25 调查M8a3.2 API只读网关限定通过

c2c50ca后新增API result_gateway/result_api独立factory，强制Bearer再原认证/双read权限、CurrentUser.user_id/tenant_id转发；专用内部read URL/token单GET不redirect/retry，回包身份/manifest/MD/exec版本hash核。新API13＋原query7及另Agent13共33，与独立同33/6hash/12 HTTP完整重放通过，限定ACCEPT/0必须修。合同独审先补关原dev无凭据demo旁路，仅新GET强制凭据、旧认证/query不改。docs/operations/investigation-result-gateway-20261025.json；实际RBAC撤销/PG/network仍未验，下一a3.3两临时loopback服务读原6/14，0新Run/查询/模型/通知，无部署/合main，2.2/2.3未完。

# 2026-10-25 调查M8a3.1内部只读HTTP限定通过

2d92063后新增独立Agents result_api/create_app，仅内部GET+专用新read token/tenant/actor→a2，body/query覆盖拒绝、结果身份核、错误脱敏；显式新PG/TLS池只关闭自建资源。13新＋45相关58及独立同58/6hash/11完整ASGI回执重放、池超时/非法token补查通过，限定ACCEPT/0必须修。docs/operations/investigation-internal-read-api-20261025.json；无旧token/dev/DB回落、旧app/权限默认不改。仅可信网关认证/SQL双集成，外部用户permission在a3.2、真实双进程PG在a3.3待验；无启动/新账本/模型/通知/部署/合main，2.2/2.3未完。

# 2026-10-24 调查M8a2 owned读取限定通过

从9f75772先卡/strict/独立合同，再result_reader及M7内部同锁读helper提取；13新＋43相关56与独立同56/6hash/3完整读重建通过，限定ACCEPT/0必须修。当前tenant许可先验，同Run锁/唯一begin全owned event-body-state核验、a1恢复、owner服务端取、同M7读；无需当前Alert/客户端scope或owner，不改账本/预算。回执docs/operations/investigation-owned-reader-20261024.json。仅SQL替身，actual credential/permission/真实PG/HTTP仍待；下一显式新只读HTTP沿原权限，不改旧路由/权限默认，无部署/合main，2.2/2.3未完。

# 2026-10-24 调查M8a1冻结读上下文限定通过

从2b87675先合同/strict及独立设计审阅，再profile_restore纯层；11新＋40相关51与独立同51/6hash/3组原件重建通过，限定ACCEPT/0必须修。由owned begin恢复原M1 controls/sources/profile/plan并精确核hash/字节/引用，当前读者tenant与frozenprincipal身份分开；改当前Alert不影响历史scope，纯恢复不授予启动/接管权限。docs/operations/investigation-profile-restore-20261024.json；无真实PG/auth/HTTP，后续a2持久归属读取及显式HTTP/启动仍待。旧代码/Run/unknown/费用保持，阶段提交推送，无部署/合main，2.2/2.3未完。

# 2026-10-24 调查M7c真实发布/冷读限定通过

原M6.2c Run4dfd374a-17a6-5fec-833b-803bfbcb85c6仅追加1event/4artifacts，当前6/14；新publish及read两进程同manifest/MD/execution，原选中5/10列与正文校验和前后/跨进程相同，新增查询/模型/Run/HTTP0，通知未投递。新m7角色NOLOGIN/有效三表权限false/活动0，两个子进程exit0。公开回执docs/operations/investigation-publication-pg-seam-20261024.json、exact PG UTF8合成MD例docs/investigation/examples/fixed-recon-published-20261024.md。11新＋149相关160及probe独审43/P2六反例修后通过；真实结束独审限定ACCEPT/0必须修（独立11项/14hash、PG全14及样本/进程/权限核验）。旧M6.2c5/10保阶段快照，不反写；当前新三维finished/complete_for_scope/none只有限来源目标，旧Run列running/null/0/0，M8/真实stream/Case/Deep价值尚未交付。无部署/合main，继续M8精确合同，2.2/2.3未勾。

# 2026-10-24 调查M7b发布/读取限定通过

基线9bf333f按b细卡/strict及独立合同审阅，新增publication store，21新＋128相关149通过；原子1event/4artifacts、重复/cold同manifest/通知描述仅首次确认commit后生成。来源核验P2已按M3 completion event/kind/pinned hash统一修复（含未采用来源），6红反例/源码全文保公开failure JSON，21红测6失败→当前全过。新state→stopped基线不改M3，late settle保真实账本但拒陈旧正式结果，丢指针不重发。docs/operations/investigation-publication-store-20261024.json未参与实现者独立52项/6hash/7组完整只读重建限定ACCEPT、0剩余必须修，未真实PG发布；c在原稳定Run仅追加发布、不重查。旧源码/Run列保持，无模型/部署/合main，2.2/2.3未完。

# 2026-10-24 调查M7a纯同版包限定通过

基线3114609按M7细卡/strict及fresh_design合同审阅，新增recon_publication与16新合同；16新＋112相关128通过，未参与实现者fresh_code当前16/5hash/5组完整包与MD重建一致，限定ACCEPT/0必须修。固定section/缺evidence null，execution独立发布快照，重用finish_recon核当前基线拒late settle，停止后墙钟不回算；typed事实安全显示，来源缺口/unknown保留。纯包publication=candidate/留存not_attempted/正式execution-report refs null，未发布/通知。回执docs/operations/investigation-publication-preparation-20261024.json。前版51不累计，原冻件保留；下一持续b同Run原子发布与按manifest读，再c仅PG，不重查模型。旧源码/Run列不改，无部署/合main，2.2/2.3未完。

# 2026-10-24 调查M6.2c真实接缝已执行，结束独审限定通过

新Run4dfd374a-17a6-5fec-833b-803bfbcb85c6走独立v2实际runtime：一次业务HTTP/CH、5事件10工件全边/hash/UTF-8读回，repeat/cold同交接且无新增事件/查询，model0/tool1/unknown0/unsettled0，有限ready/Q3a-b-Q4未评估/性质授权未知；CH预检另1次。新角色NOLOGIN/有效三表权撤回/活动0，临时API核PID创建时间后停。11新＋101相关112项，probe独审P2关联缺口修后11＋4独立通过；真实证据独审限定ACCEPT/0必须修。见docs/operations/investigation-fixed-runtime-seam-20261024.json。候选未M7发布/人工接手，Run列running/null/0/0保持；无Case/模型/部署/合main，旧失败保持，2.2/2.3不勾。下一持续M7精确合同→纯同版包→原子发布/同版读取逐块推进。

# 2026-10-24 调查M6.2b2控制器限定通过

从b61214a按细卡/strict及合同审阅写单次FixedReconRuntime、M3 gate按attempt内存观察与dispatch_block记录；18新＋79相关97项，未参与实现者独立89子集、6hash/7观察与竞争回归一致，限定ACCEPT/0剩余必须修。审阅P2（cancel标记与观察保存窗口被重复blocked抢先封存）修后非owner blocked只pending，读回先核观察已留存再清；修前源码全文SHA/反例及red保docs/operations/investigation-fixed-runtime-controller-race-20261024.json。正常仅一次MockHTTP，unknown/取消/提交失败不重查；取消重复不接管，观察不当原completion。回执docs/operations/investigation-fixed-runtime-controller-20261024.json；旧入口与历史失败不改。b1独审清单归类已透明补正115独立项，不与实施105相加。下一持续c真实独立PG/HTTP/CH，新临时角色/Run、模型0、只一次查询，实际未验前不称M6.2完成；2.2/2.3不勾，无部署/合main。

# 2026-10-24 调查M6.2b1事务代码限定通过

从5f388ae按合同strict/fresh_design_audit限定审阅后，新增ReconExecutionStore及SQL transport double测试，原M3 store仅可覆写kind/runtime/agent挂点及版本隔离。15新＋90相关105项和fresh_code_audit独审通过，5hash/6观察一致，限定ACCEPT/0必须修；独立实际115项不同测试，清单归类更正见回执，不与实施105相加。原子begin/claim/冻结reserve/工件核验与交接、重复读取、未知预留和未确认观察均在替身验证，真实PG仍待c。回执docs/operations/investigation-fixed-runtime-store-20261024.json；补充审阅探针失误已登记，非源码缺陷。下一持续b2单次控制器/取消传播，再c真实独立v2，不等用户逐块确认，不部署/合main；旧源码/Run计费状态及历史失败不改，2.2/2.3不勾。

# 2026-10-24 调查M6.2a纯运行控制限定通过

持续授权下从239d518先合同/strict与fresh_design_audit限定合同审阅，再仅新增recon_runtime_state及12项测试；12新＋68相关、未参与实现者fresh_code_audit独立同80项/6hash/计划与观察均通过，限定ACCEPT/0必须修。冻结runtime/完成政策/profile/scope/整窗唯一query和step/attempt，纯claim预检不增加预算或授权外呼，仍须原子提交和M3真实预留；重复claimed不接管，unknown/超额/时限/取消及账本保持，已有交接不覆盖。见docs/operations/investigation-fixed-runtime-state-20261024.json。当前仅a纯层，无真实业务/模型/部署/合main；直接继续b事务/调度、c真实接缝，不逐块等待用户。2.2/2.3不勾，旧代码/失败保持；阶段提交/推送。

# 2026-10-24 调查持续推进授权

用户明确授权持续推进，不再每块结束等待继续确认。沿现调查分支与主设计顺序，逐块预期/规格strict→实现→直接测试→必要独立新版真实接缝→未参与实现者复核→回执/阶段提交推送；失败先修复，旧失败/unknown保留，实际单Run额度保持。现在M6.2a纯运行计划/停止与预留限制→M6.2b原子持久/调度→M6.2c独立v2真实查询，随后M7同版交付与M8等既定计划。持续授权不含部署、自动合main或真实厂商动作；旧版严格隔离。仅出现缺少必要业务信息/外部条件且无法独立推进时才说明阻断，不以常规实现选择重复请求许可。

# 2026-10-24 调查A3投影阻断交接限定通过

A2保存c94eb97后按已审合同/strict推进A3：EvidenceView先核material/tenant/Run/scope/来源版本/hash，再以专用异常保投影阻断；新增纯prepare_alert_recon返回正常实际视图/有限结果或blocked_alert_recon.v1 partial，保material/query/全部source版本refs和真实来源状态，不回显自由正文，不伪造视图或新事实，六问题未评估、持久未尝试/人工仅required。10新＋90相关共100项及未参与实现者独立同100项/4hash/10观察通过，7种正常视图与前版canonical_doc逐字节相同，限定ACCEPT/0必须修。见docs/operations/investigation-material-projection-20261024.json。A2政策版本保留，I2完整messages门不变；A3仅最小可交接方案，未分离证据内核。下一M6.2实际M3准入/固定查询/去重/持久交接，2.2/2.3未勾；无真实业务HTTP/PG/CH/模型/部署/合main，旧源码/历史失败不改。阶段提交/推送调查分支。

# 2026-10-24 调查A2整窗完成政策限定通过

基线070e990，先A2/A3合同/strict及独立设计审阅，完成政策缺版本问题已在实施前补清并留记录。A2新增bounded_full_window_source_check.v1，只完整冻结窗口的已确认有界查询才可能有限ready；子窗保事实/refs、列未覆盖区间且partial；空/截断/失败/unknown原阻断不变。7新增＋64相关共71项及未参与实现者独立71项/3hash/12观察均通过，限定ACCEPT/0必须修。见docs/operations/investigation-window-policy-20261024.json。旧回执不回填/重算，A3仅合同已核仍待实现，M6.2实际gate/查询/保存未验，2.2/2.3不勾；无真实业务访问/模型/部署/合main，阶段提交/推送。

# 2026-10-24 调查A1地址接缝已限定修复

用户继续推进后，891d07e先spec/design/预期与strict，再仅Agents v2共享地址身份及scope/caller/evidence/Deep使用点；8新增＋相关103共111合同通过。原始SourceField值/路径、响应/hash保留，mapped与IPv4等价、原生IPv6独立、不同地址/tenant/hash仍拒，别名不绕过去重。未参与实现的fresh_code_audit独立83项/8组反例/7hash与稳定观察复核后限定ACCEPT/0必须修。见docs/operations/investigation-network-identity-20261024.json与统一实施记录；夹具source_run误用及修前red保留。仅离线合同，无真实业务HTTP/PG/CH/模型/部署或合main，API/旧源码/历史审计不改。下一A2有限完成/窗口与A3投影阻断保refs合同，再M6.2；2.2/2.3不勾。阶段提交/推送调查分支。

# 2026-10-24 调查独立总审计与后续流程

用户要求客观独立审计及后续规划；基线7b7bb6b，由三位新审阅者分核架构/代码/证据。见docs/investigation/independent-audit-20261024.md及统一README。保留总体架构，140项合同/39哈希通过；新增反例确认A1 mapped IPv6归一化误拒P2未修，A2子窗口ready及A3模型投影约束程序路径为M6.2前合同门。下一先修A1并明确边界，再M6.2→M7→M8a，Case整体与自动政策前验语义/Deep实际价值。本轮只报告、索引及公开离线probe，不修功能/真实业务访问/模型/部署/合main；原限域ACCEPT保历史，新发现不被旧验收覆盖。调查分支阶段提交/推送授权保持，2.2/2.3不勾。

# 2026-10-24 M6.1固定有限事实与停止交接限定放行

用户继续授权后，基线ad08579先活动spec/design/实施预期和strict，再仅新增Agents v2 fixed_recon及13项直接合同；13新＋采用13＋视图11＋绑定11共48项通过，未参与实现者独立复跑及5hash/6材料状态/5停止原因重建一致，限定ACCEPT、0必须修。程序事实不伪造模型候选，六问题/原criticality保留；正常有限来源目标ready，空/失败/未知/冲突/截断/正文不可读及已观察停止原因保合法事实refs且partial。所有结果stopped，不自动查询/模型/Case或发布Run完成，性质unresolved、授权unknown。当前仅M6.1纯层，停止原因是可信owner已观察输入，不证明实际M3预算/时钟；M6.2再接运行准入/固定查询/重复无进展及持久交接，整体2.2/2.3不勾。回执docs/operations/investigation-fixed-recon-20261024.json；本批真实HTTP/PG/CH/模型/业务写入0，旧源码/入口、历史失败/unknown、归档保持；阶段提交/推送调查分支，无部署或合main。

# 2026-10-24 独立v2查询接缝限定放行

前置三块限定放行后，本块先规格/预期/strict，再共享网络场景卡、独立query_api及36项直接合同。02批新Run627b8f1d-c9c2-5c9d-a07d-e918ae6b0001经真实新HTTP→CH→M3落库，1命中/两对照排除、3事件/6工件独立hash/UTF-8/关联读回通过，模型0。01批PG字段假设失败、无Run/业务查询，保原件并以真实raw_event.telemetry[0]显式映射修复，新批次不重放01。临时进程按PID/创建时间核身份后停止，01/02新PG角色NOLOGIN撤权。公开回执docs/operations/investigation-v2-query-seam-20261024.json；未参与实现者独立36项及只读PG复核后限定ACCEPT、0必须修。仅受控查询接缝，API非M8持久Run授权，profile仅留存已核输入，完整Deep/M6—M9/Case未交付；tasks2.2/2.3不勾。下一单项为M6固定查询/有限事实路径，先合同/预期；M5按需另验。旧源码/入口不改，正常目录调查分支逐阶段提交/推送，无部署或合main。

# 2026-10-24 调查前置三块收口，下一独立v2查询接缝

按用户“按步骤推进、按以前要求”授权，依M1纯profile绑定→I1正文局部降级→I2完整messages预算，每块先规格/预期/strict、再实现直接测试、回执和独审，均限定ACCEPT/0剩余必须修；tasks2.1据实际三块核销。I1的Unicode必须修发现与修复、测试助手一次失败均保留。I2保12KiB并共用三处计量，超限明确阻断/材料缺口，不自动分组或删支持反证；10条未被模型消费。下一单项为主设计12.7的共同场景卡和独立v2受控查询接缝；不拿历史HTTP/纯合同当真实新路径已验。完整Deep/Case继承/发布仍待做，change未完不归档。正常目录调查分支逐阶段提交/推送，旧源码/入口、历史失败/unknown/迁移归档保持，无部署或合main。

# 2026-10-24 调查I1限定放行，下一步I2

M1经独审提交7e84fe7后，按规格/预期/strict→实现→直接验证推进I1。6新＋11视图＋13采用＋15模型合同通过；独审发现可选message转义Unicode编码整体失败，已局部修复并独立复验，限定ACCEPT、0剩余必须修。必要身份/hash/范围及输入隔离保持，未知正文缺口进入readable。下一块I2完整messages预算未实施，须继续同样步骤。无真实模型/业务HTTP/DB/写入/部署或合main；阶段提交/推送。原541511c评审probe保历史用途，不在已修HEAD当回归套件。

# 2026-10-24 调查按步续接授权与M1纯合同放行

用户在流程及新旧对照后明确要求按以往步骤推进。当前普通目录分支codex/investigation-review-20261024；已先合同/strict，再M1业务profile纯绑定，11新＋原scope8项通过，未参与实现者复跑限定ACCEPT、0必须修。仅结构绑定已核目标/成员，不是Case认证/继承/启动或执行器接线。下一步依次I1正文局部降级、I2完整messages预算，各块先预期/规格再实现测试/回执/独审，达标才下一块。调查分支按阶段提交/推送；旧源码/入口、历史失败/unknown、迁移归档保持，无部署或自动合main。当前记录见docs/operations/unified-investigation-implementation.md。

# 2026-10-24 两分支main统一续接入口

用户要求先合并且保留双方原设计，再统一审计数据准备/评估与调查的数据湖协作。已合并数据cec5ea98、调查469e9467至main5c1202b5；续接统一读[总审计及双方建议](docs/operations/data-investigation-integration-audit-20261024.md)。现有网络fixture/lake_probe共享，数据线主责准备/投放/expected/评分，调查线主责scope/查询/证据采用/共享额度；不另造写湖器或统一两种评分。源码/测试原样，A1/A2/A3、Python3.11夹具兼容及IPv6测试问题未修，M5.2/分层/正式新入口未交付。各分支同步main后按各自主设计与适用change推进；本轮仅审计/同步，无新模型/业务数据写入/部署，其他未提交工作保持。

# 2026-10-24 main统一开发基线与后续总审计

用户最新要求先合并数据评估和调查469e9467，保留双方开发设计，再对照最新进展做总审计，分别提出建议并统一数据湖写入/准备/查询等协作。数据评估审计已保存，已知问题未修；调查v2只作为未启用开发基线合入，旧运行源码/入口保持。原迁移归档不重开，调查后续用continue-isolated-investigation-v2。本次允许本地提交与同步main供各开发分支拉取；不改业务设计、不启动真实测试、写湖/模型、生产配置或部署。其他20展示和暂停规划未提交工作保留，不混入本次提交。

# 2026-10-24 数据评估审计与合并授权

用户明确要求保存[审计结果](docs/operations/data-evaluation-audit-20261024.md)并将数据评估阶段成果合入main。96测试/39子项通过；非法分类MCC虚高、完整配对/批次冻结及raw_event截断保持未解决，E1真实模型和本分支E2—E4未完成。本次只保存和本地合并，不修业务/评分、不发模型/写数据/部署/push；旧“不提交”是此前阶段记录。main已归档的迁移保持关闭，后续独立change承接。

# 2026-10-24 后续授权：本地Git提交，之后继续规划

用户在迁移收尾后明确要求做一轮commit，再继续规划后续开发。本次允许将已审的迁移收尾/归档及本条授权记录做一次本地提交，不包含push、业务开发、测试或部署。实际提交结果以Git历史与当轮回执为准。下文“未提交/不提交”是先前收尾阶段边界，不限制此次新授权；独立调查/入湖仍由另一工作承接；用户随后明确呈现相关工作归对应后端模块，本会话不展开列表/筛选/统计/取数对接，后续仅讨论本服务自身功能范围。

# 2026-10-24 最新：迁移收尾，独立调查另行承接

用户明确本会话不再测试背景事件入湖/调查闭环，相关工作已由单独开发的调查模块处理；不复验或代其宣称通过。先结束已选范围的告警与调查服务端迁移基线，后续工作只规划、待讨论。当前收尾与原15项责任核销见[收尾及后续规划](docs/operations/migration-closeout-20261024.md)。原迁移change已完成限定结束独审并归档为`2026-10-24-restore-alert-investigation-integrity`，同步17条合同，封后独立窄复核限定ACCEPT/0必须修；本轮仅文档/OpenSpec静态校核、结束独审及归档，不改业务代码/运行配置，不访问生产、写数据、发模型或消息、部署、Git提交/推送，不创建定时安排。旧partial/质量失败/unknown/积压保持；线上v1与本地小修分开。独立调查后续使用自己的change/分支，本迁移归档后不复用它实施新设计。下文10月23日及更早“当前/5/15/未完成”均为当日历史状态，由本条和收尾回执覆盖当前任务状态。

# socai2 / stingAISOC 工作约定

- **2026-10-24正常目录/Git协作（最高优先最新）：** 用户明确调查是共享功能开发，直接在普通项目目录`E:\aisoc\socai2`的`codex/investigation-working`分支修改、提交并推送服务端供评审；其他机器正常拉分支，后续正常合并main/其他目标分支。禁止再把活动分支/工作树放`.local`下。`.local`只承载私密配置、本机Windows适配及必要本机过程材料，不替代仓库中的设计/进展/问题。统一阅读入口`docs/investigation/README.md`。原隔离工作树方式和旧“不推送”是历史阶段，已被本条覆盖；旧版本源码不改、逐块测试、无部署/不自动合main仍保持。

- **2026-10-24旧版保留/新版严格隔离（最新）：** 用户再次明确两个完全独立的版本线，旧源码/入口/开关/注册不改；需变化的函数复制所需部分到新版新增函数。已将新Agents/API代码迁入各自app/investigation_v2，撤出旧API新增注册、恢复旧工具测试，旧已跟踪services文件相对3fa4be3无差异。先新API8项/旧工具51项通过，再Agents85项直接合同通过；新v2 HTTP路径尚未注册/发布，历史真实回执不算新路径已验。后续独立进程/配置/输入输出，同Run单writer、unknown不回落重跑；不部署、调查本地Git保存已授权。M5定向真实接缝也用独立v2测试进程，不回挂旧API。

- **2026-10-24调查Git保存授权（最新）：** 用户明确此前“不需要提交”针对Windows Local Fix等本机工作，不适用于调查模块。调查设计、功能代码、测试及非私密回执统一在`codex/investigation-working`保存并按阶段本地提交；不混入Windows分支，不自动推送/部署。本条覆盖下文调查各历史批次“无提交/不自动提交”的后续工作限制，不改写其当时事实。当前提交保存D1—M4限定成果、M5.1及M5.2未完成增量、v4设计/对照；不据Git提交追认完整M5或Case分层已交付。

- **2026-10-24调查v4分层重新设计（最新，仅文档）：** 用户要求结合进展与新建议重新设计，主入口仍为[调查规划](docs/architecture/investigation-planning-design.md)。两业务profile共享内核：告警分诊/侦察及20“自动处理过程”保留无Case详情；Case新Run继承已核材料，完整成员快照/局部选材，创建/关联与启动独立政策、四领域按需。当前D1—M4限定通过、M5.1九项纯合同通过，M5.2仅observer问题组增量未测；先讨论v4，未继续实现/业务测试。恢复顺序见12.7：先profile合同，再续M5及告警交付，手动Case衔接后分别接自动政策。开发累计tokens不限、单调查有界；OS后置，无部署/提交/push，原5/15及旧失败保持。20仅核前端构建，不代表其API/21已验。

- **调查M4限定完成与M5续接（最新）：** 2026-10-24 M4限定通过：选定8例原文/采用/可读均通过，23484tokens；其中两例冲突按完整消息/9源码/调用AST等价复用。02开发18回复52185tokens，5个失败原件保持、无unknown/unsettled、费用unpriced。15项直接测试通过，未参与实现者audit_contracts限定ACCEPT/0必须修。仅network_observation.v1/Q1,Q2,Q5，非完整恶意/授权卡或全调查通过。PG临时角色NOLOGIN并撤权；M5待按小步实施，OS后置、无部署/提交/push，原5/15保持。 测试累计tokens不限，实际单调查各子任务仍共享运行期额度；本任务24000转发保留供下一本地阶段，结束按PID/创建时间核身份后清理。见[实施记录](docs/operations/unified-investigation-implementation.md)及[M4回执](docs/operations/unified-investigation-m4-20261024.json)。

- **2026-10-23调查开发测试持续授权与M4.5预期（最新）：** 用户明确开发/调试/测试累计tokens不限，可持续修复复测，不再逐批请求预算；实际一次调查仍有上限。这已覆盖前批pending的8/30000提案，无需再确认。M4.5逐个复测原8个语义组合，每项独立test Run，M3额度仍20000tokens/180秒，请求45秒/completion2048/retry0；测试驱动无累计token硬上限，不绕过单Run gate或自动重放未知请求。失败定位修复并直接测试后，以新版本、新trial留证，不清旧Run/失败/unknown。原文/采用/可读三层均满足8例后才放行M4，未过不进M5。当前仅预期、尚未实测；见[实施卡](docs/operations/unified-investigation-implementation.md)。生产额度不改，OS后置，无部署/提交/push，5/15保持。

- **2026-10-23调查M4前批失败及修订候选：** 7真实回复15042tokens均留存但候选全拒绝，第8未发，21事件/36工件独立读回通过，旧Run列不改、临时PGrole已NOLOGIN撤权。M4.4的13项/离线回放及候选独审通过不追认原M4通过；19文件原冻结与旧失败保持。见[主回执](docs/operations/unified-investigation-implementation.md)与[M4历史摘要](docs/operations/unified-investigation-m4-20261023.json)。当时待预算选择已由顶部新授权覆盖，不重置旧批或采用旧30000提案。

- **2026-10-23调查M3限定完成（前批停止位置）：** 按M3.1→M3.2→M3.3逐步通过12项状态、4项真实PG、9项gate测试及1次真实HTTP；匹配1条，3事件/6工件独立读回hash/UTF-8/关联通过，真实模型0。scope重复正文及未知参数先落库两项审阅问题已修后验证，最终独审限定ACCEPT、0剩余必须修项。共享预算与Run总量只写原子state snapshot，不改Run状态/计费列；测试工具Run保持running为预期，非最终调查完成。API已停，PG临时角色禁登录并撤回权限，CH reader保留。见[主回执](docs/operations/unified-investigation-implementation.md)及[M3摘要](docs/operations/unified-investigation-m3-20261023.json)。当批停止于M3；当时M4、统一调度、M7发布、M8入口/读取projection及OS后置，无部署/提交/push，原5/15与旧失败保持，后续以最新授权为准。

- **2026-10-23调查M1与首个M2查询已通过（前批停止位置）：** D1—D3数据前提通过后再实现M1冻结范围/六问题、M2受限activity_records调用方/API。五块各8项直接测试共40、旧工具51项兼容通过；真实HTTP→原认证→CH五查询/四认证反例通过，原文hash和微秒半开窗口一致，未发模型/持久Run。临时API已停、writer权限已撤回，reader与合成数据保留；未部署/提交推送。M1/M2未参与实现者独审限定ACCEPT、0必须修，主记录见[本批回执](docs/operations/unified-investigation-implementation.md)。当批M3持久/额度、模型及Run入口未实施，后续以顶部M3回执为准；原5/15与旧失败保持。

- **2026-10-23调查ClickHouse场景数据已验证（本批最新）：** 用户确认先补场景数据再接查询，OpenSearch IOC后置。D1离线8项、D2工具8项直接测试通过后，原LakeWriter单次写3合成事件，独立reader核47列/原文hash、匹配1/对照排除；D3原Kafka/Fusion投1告警/2消息，PG canonical Alert与湖UUID/租户/时间/实体精确关联，Run0/模型0。专用writer INSERT已撤回，reader保留查询验证；新账号只有表级权限，tenant条件由程序强制，未改共享row policy。M0有限来源记录核对场景放行，随后先M1范围/问题合同测试再M2工具；不据合成观察判恶意/授权。见[逐步回执](docs/operations/unified-investigation-implementation.md)。原5/15、旧失败保持，无部署/提交推送；下条待讨论为前一阶段。

- **2026-10-23统一调查开始逐模块推进（当前M0）：** 用户已授权按“预期→实现→测试→放行”推进，后追加要求工具影响设计先规划讨论，并核查main测试数据模块。独立调查树/分支不变；已fetch查main到`7ea813a`，仅文档更新、工具/服务未变，未合并覆盖v3未提交稿。M0只读核15字段及既有合成事件1行，外联字段缺失；已形成[工具与场景数据建议](docs/architecture/investigation-tool-data-plan.md)和[逐步记录](docs/operations/unified-investigation-implementation.md)。CH已有入湖/查询、现测试工具未写场景历史事件；OS为共享TI索引，非事件/审批库且未被现enrich工具自动消费。首场景及工具数据计划待讨论，M0尚未放行、M1未编码；原5/15/旧失败保持，无新数据写入/模型/部署/提交推送。下文“等待实施确认”为此前文档阶段，不撤销当前逐模块授权。

- **2026-10-23调查方案v3修订（仅文档，最新）：** 用户确认重新审计后修订方案，主入口仍为[调查模块规划设计文档](docs/architecture/investigation-planning-design.md)。本批在独立工作树`E:\aisoc\socai2\.local\worktrees\investigation-working`、`codex/investigation-working`、基线`3fa4be3`；Windows环境任务留原目录/分支，不提交推送。v3拆分行为性质/授权、结论/查询范围，补材料指令隔离、按问题组调用、调查阶段共享额度与Run总成本、热读/冷读/通知同版和有用判断/安全交付验收。首场景卡为待M0实值化的候选，未核新来源或启动实现、业务/模型测试、生产访问、部署；继续等待实施确认。原5/15、旧失败及unknown保持，具体复核见原change audit/execution，历史ACCEPT不自动覆盖新稿。

- **2026-10-23数据与评估E0本地完成：** 在隔离分支`codex/data-evaluation`完成72条/36对四分类输入与答案分离、原评分器离线复用及工具轨迹核对，见[设计](docs/operations/data-evaluation-design-20261023.md)和[回执](docs/operations/data-evaluation-execution-20261023.md)。79直接测试/39子项通过；独审费用unknown问题已修，限定ACCEPT、0剩余必须修项。旧记录10个模型提议/8个执行，6不可用2错误，8份返回均见已记录后续请求；不证明成功查询或语义采用。E1—E4未执行，登录合同改动先讨论；0新模型/业务查询/业务源码/部署/提交/push，主工作区未覆盖，原5/15与旧失败保持。

- **2026-10-23测试数据迁移已实测：** 用户授权后完成场景选择/Kafka wire有界发送/只读观察和隔离联测，见[回执](docs/operations/testdata-migration-execution-20261023.md)。44直接测试/39子项通过；3条新输入Fusion3Alert/6消息/0模型；另2例自动BTP关闭、NR调查partial，6回复26492tokens/29工件。仅工具侧改动，188个Agents源码与6上游原件hash保持；测试标记干扰理由、21796/20000软预算停止、报告running与Run completed差异登记待讨论，不重调或顺带改调查设计。临时进程/隧道停，2新key停用，预算2 responded。新增Git忽略可选输出目录，实际运行材料均留.local；无部署/提交/push，原5/15保持。

- **2026-10-23调查规划与换账号交接（最新，仅文档）：** 后续调查统一读[调查模块规划设计文档](docs/architecture/investigation-planning-design.md)，已汇总完整四块合同、程序/模型/Deep分工、旧模块复用融合、完整案例及产品参考。未来开发或测试前自行使用`codex/investigation-working`或合适的隔离分支，先核未提交小修和其他任务，禁止漏带或覆盖。严格按M0—M9：每块先明确概念/功能、输入输出与预期样例，再只实现这一块并直接测试，符合预期、留回执后才进入下一依赖模块，不能整流程写完再测；失败先定位，模型原文/程序采用/最终交付分别评价。新账号续接入口与开场指令见主文档第14节。本轮仍在main，只整理文档，不启动统一设计实施、业务/模型测试、生产访问、部署、提交推送；原5/15、旧失败及未提交其他工作保持。

- **2026-10-23统一调查设计（仅方案，最新讨论口径）：** 用户明确四角色及graph/Deep/Router可以融合，不必固定保留；已形成[问题/证据/分析判断/执行状态设计](docs/architecture/unified-investigation-design-20261023.md)，含程序/模型所有权、逐步输入输出、Deep子任务、旧模块迁移、同版结果与停止交接。旧保拓扑约束适用于此前小修，不自动限制新设计；新设计未实施。独立设计审阅修订后限定ACCEPT、0剩余必须修项，只校核文档，不是业务验收。本轮不改代码/配置/运行、模型或业务测试、部署、提交推送，原5/15与旧失败保持。

- **2026-10-23页面与数据库统一交接：** 用户要求先交接库表供自行查询、保留HTTP，并只保留最新文档。已合并为[唯一交接主文档](docs/integration/v1/page-elements.md)：四页90项展示信息、21 PG aisoc/public六核心表、字段/JSON映射、关联及SQL、HTTP说明和实测边界。结构按用户要求调整为页面/功能/字段→数据库表→功能取数与六例→已有HTTP→补充说明。删除本轮两份dated旧稿及旧文档快照包，索引统一；实值JSON/SQL及原始测试证据保留。此前41 GET/21工件/8本地用例复用，本次仅核38列及两例8路径，无新生产查询/模型/改表/部署/提交推送；原5/15与旧失败保持。 增量独审限定ACCEPT、0必须修项；不再另存旧文档副本。
- **2026-10-23测试数据迁移实施授权（最新）：** 用户确认按修订计划开始迁移；若必须修改后续调查设计，先停止并讨论。沿原restore推进测试工具场景选择/Kafka wire与有界发送、隔离Fusion、只读结果观察及两例自动分诊/调查，每步测试留回执；不顺带改模型职责/输入输出合同/编排/算法，不自动部署或Git提交推送。执行及旧失败保留见docs/operations/testdata-migration-execution-20261023.md，原5/15暂不勾完整任务。下条仅规划是前一阶段。



- **2026-10-23测试数据迁移重新规划（仅方案）：** 用户先要求继续迁移测试，随后明确先找回原设计再重新规划。已回查原会话及10月22日回执，保存[修订计划](docs/operations/testdata-migration-plan-20261023.md)：复用已迁生成器/Go原件和已验HTTP→Fusion，拟补场景选择→source-v1 Kafka wire/有界发送→持久结果观察→2例自动分诊/调查。普通payload缺身份字段、旧模板实体复用、内外时间不自动一致及旧探针配置耦合已明示；答案/原文/程序采用分开。当前仅文档，不改码/业务测试/模型/生产访问/部署；Purple Team/Honeytokens/全量Replay和调查后续架构仍另议，原5/15与旧失败保持。

- **2026-10-23调查小修最新范围：** 用户追加“每走一步都测试”及“先完成这几个小改动，后续调查设计再讨论”。本地完成Forensic前置校验与响应/报告采用、工具逐次原子留存/结构状态、异常及内外层时限交接，见[回执](docs/operations/investigation-result-handoff-20261023.md)。保四模型职责、配置、六轮与预算；真实2回复2714tokens证实程序交付约束有效，原文仍有条件处置/无依据描述，首2请求503用量未知保留。未部署/推送，不继续事件级/动态编排/共享结构扩展；原5/15、旧失败及生产v1保持。结束独审限定ACCEPT、0本批必须修项，版本与证据已保留。

- **2026-10-23调查优化实施授权（最新）：** 用户要求“先提交，然后按照规划推进，做好设计和校验”，并明确现有模型分工是为了小模型稳定输出。先提交方案约束，再沿原restore change实施首批结果一致与停止交接；保Recon/Forensic/Responder/Report、graph/deep和Router职责拓扑及模型参数，程序承担范围/状态/预算/留存，各角色读有界材料，不新增必跑总规划模型。先本地直接校验、保版及未参与实现者独审，按阶段发布；事件整体/增量/跨事件另按后续批次设计。此前仅保存是历史阶段；本次Git提交已授权，未要求推送。原5/15、旧失败及生产事实按各批真实回执记录。

- **2026-10-23事件级及跨事件分析研究（仅方案）：** 用户要求参考主流安全产品评估必要性。已核本地入口/分组/图上下文与Microsoft Defender XDR、Sentinel、Security Copilot、CrowdStrike Falcon、SentinelOne官方资料，见[研究](docs/architecture/incident-analysis-product-comparison-20261023.md)。当前有Case多告警和跨Incident候选检索，缺持续事件整体研判；建议事件结果→增量更新→候选关联验证，自动合并/Campaign后置。明确微软Incident cases Preview、Endpoint AIR 2026-09变化及Falcon共享上下文调查Pre-beta。统一证据材料供主分析，补查/领域分析可组合；仅保存文档，不据此启动实施、业务测试/模型/生产访问/部署，原5/15及旧失败保持。

- **2026-10-23优化方案仅保存：** 用户明确“不是执行，是方案保存”。已将审核意见融入[调查产品工程方案](docs/architecture/investigation-product-engineering-roadmap-20261022.md)：三批改为结果一致与停止交接→查询有效性与一个真实场景→共享结构与扩展；补参数来源/绝对窗口、认证字段缺口、校验先于响应和报告、逐次留存与结构化工具状态、Router待核结论汇合。异常登录保留为有数据条件的候选，先审已有未全发布C2；新增验收材料均未执行。本次仅文档，不授权改码/模型/业务测试/运行/部署；原5/15、线上v1及旧失败保持。后续不能因方案已保存自动启动实施。

- **2026-10-22两个暂停项目恢复：** 用户要求继续并逐步记录；测试工具attempt02三条新输入真实入口/Kafka/Fusion/PG通过，3Alert/new/无Case、6消息、关联Run0/模型0，隔离topic/Redis前缀，本地进程已停。原8离线＋2替身结果复用，attempt01及一次source_event_ids观察假设失败保留；产品建议已补v1已上线和两例数据事实，未实施未选定方案。见[逐步记录](docs/operations/two-projects-resume-20261022.md)、[工具回执](docs/operations/testdata-tools-20261022.md)。resumed_projects_end_audit结束独审限定ACCEPT、0本轮必须修项，选定版本与逐步记录已留存；原5/15/旧unknown预算/质量失败保持；无业务源码/部署配置修改、Git提交推送，生产v1维持原授权状态。

- **2026-10-22 v1两例落库及后端数据盘点：** 用户授权正式服务跑1—2例后，已通过raw Kafka新增2条合成告警：例1自动BTP0.95关闭（3事件/7工件/2033tokens），例2自动NR0.85升级调查（18事件/14工件/29755tokens，graph partial）。21工件正文的UTF-8字节/hash均通过，21份event关联完整；成本3行共8回复31788tokens，全部unpriced。22:56真实PG补查生产tenant总计3Alert/3Run/36事件/35工件（含旧发布canary），选定25表428字段/实际约束已留存；23:09实际只读执行后端SQL9个SELECT通过。见[后端盘点](docs/integration/v1/page-data-mapping.md)、[两例回执](docs/operations/service-v1-functional-20261022.md)。graph_step仅node/无输入输出hash，工具200字符preview、prompt副本截断、seq并非严格写入游标已明示；不能宣称所有步骤原文完整或质量通过。原5/15、旧unknown/预算保持，无新部署/业务改码，v1_two_examples_audit限定ACCEPT、0本轮收口阻塞。

- **2026-10-22 v1.0.0服务已上线（最新实际状态）：** API5a1e1fd8/Agents49643b84已部署21，生产租户 `f6a5c700-69b8-44fc-8238-609362fb1a9f`、新组 `socai2-agents-v1-prod-20261022`，常驻worker及自动升级已开启，模型摘要不变。新raw Kafka合成告警自动交付15事件/14工件/MD，7回复28216tokens；graph partial、内容质量未验收，旧问题及原5/15保持。旧租户/group/积压/unknown/预算未修改，真实厂商动作关闭。service_v1_release_audit结束独审限定ACCEPT、0本轮阻塞。当前接入见[生产文档](docs/integration/v1/production.md)、[发布回执](docs/operations/service-v1-release-20261022.md)，下文OFF/未部署是以前事实。

- **2026-10-22 v1.0服务发布授权（最新）：** 用户在接口文档完成后明确授权开启Kafka自动分诊/自动调查，模型沿用当前配置，并选择“新建独立生产租户”。沿原restore change推进[服务发布计划](docs/operations/service-v1-release-20261022.md)：复用已构建API5a1e1fd8/Agents49643b84候选，创建独立生产租户/最小服务身份/预算及新消费组切换起点，定向发布API/Agents。历史worker OFF/不发布是此前事实，不再限制本轮已授权发布；旧租户/积压/unknown、5/15及旧质量失败保持，不启真实厂商动作，不自动Git提交/推送。实际是否上线、自动链是否完成仍须以本批执行回执为准。

- **2026-10-22后端对接发布文档v1：** 用户明确正式已有告警走Kafka，HTTP告警仅测试辅助；已整理[后端对接指引](docs/integration/v1/README.md)，含Kafka/Redis/PG/OpenSearch/ClickHouse/Neo4j/Qdrant配置、各步输入/输出位置、调查入口/节点/结论、核心表及JSON/SQL/env示例。查询API仍供后端读结果；fused不是调查完成通知，无Case自动Run从ledger工件读Markdown。现有worker OFF、本地候选未部署和5/15/旧失败保持；21先SSH超时，用户恢复后16:02已只读核15容器镜像/端口/连接白名单：湖192.168.1.21:9000/aisoc/socai2_lake、TI OpenSearch及TI/enrichment共享Redis DB12已确认；worker实际AISOC_AGENT_KAFKA_DISABLE=1、升级0。Agents enrichment仍127.0.0.1:9，非自动接通；无业务探活。backend_v1_doc_audit结束独审及恢复后配置窄复核限定ACCEPT；本批仅文档及静态校验，不实际发布服务、发消息/模型或Git提交。

- **2026-10-22两会话简单收尾：** 用户本轮只要求保留进展，见[续接记录](docs/handoff/session-closeout-20261022.md)。测试数据工具已有8项离线＋2项替身合同通过；真实attempt01在联网前配置失败，探针日志已修但未重跑，真实联测/最终回执/该增量结束独审待续。产品工程建议237行最终版本的既有独审已找回，限定ACCEPT、0阻塞，已补audit；建议未选定实施。相关文件及非私有回执留存于`.local/versions/session-closeout-20261022/`。本轮不继续实施/模型/联测/部署/启worker或Git提交，原5/15与旧失败保持。

- **2026-10-22智能调查产品/工程建议：** 按用户要求形成[急需问题与优化扩展方案](docs/architecture/investigation-product-engineering-roadmap-20261022.md)：优先范围/真实数据、证据与结论/报告一致性、停止后的可接手结果；三编排先共享四个小合同，保留拓扑，按场景扩展工具/策略后再考虑专业Agent。含代码落点、三场景与指标，属于建议而非已选实施或新增迁移前置；当前候选已本地构建但不含旧C2全部修正、未部署。原5/15、worker OFF与旧失败保持，无业务改动/新模型/发布。

- **2026-10-22标书需求评估：** 用户要求按原件评估模块设计/迁移是否满足标书，已形成[详细评价与推进建议](docs/operations/tender-requirements-assessment-20261022.md)及[35子组164条功能矩阵](docs/requirements/socai2-requirements-matrix-20261022.md)。当前可作告警/调查服务端基础，不能认定整份标书或核心证据/行为攻击链完整满足；SFT、完整RAG、技术选型差异及成效另列。沿B5→B6使用已构建候选做阶段交付，后续优先真实资料/范围和证据/完成语义；这是评估建议，不启动新二开/模型/部署或改变任务。新增告警筛选/UEBA最近50条限制为继承原版的静态发现，入原问题表后置；原5/15、R02、worker OFF及旧失败保持。

- **2026-10-22本地候选镜像已构建：** 用户继续并明确授权完整父镜像21→本地传输后，已生成API5a1e1fd8/Agents49643b84两个linux/amd64候选，见[镜像回执](docs/operations/investigation-candidate-images-20261022.md)。精确父ID/19清单、父层/启动配置继承通过；镜像内19源码编译/hash、Agents7排除项、API385/Agents129导入与4路由方法通过，Python3.11.17，两个临时非root/只读/禁网探针均exit0并删除；candidate_images_end_audit结束独审限定ACCEPT、0项本轮阻塞。构建助手仅修缺省Config字段读取、增加显式核本地Host的BuildKit选项及context调用；3次失败保留，业务源码/锁不改。OrbStack已启动并恢复11既有本地容器，未改其配置；21仍未部署/启worker/新发模型，原5/15与旧失败保持。下文未运行Docker/未构建均为准备阶段事实。

- **2026-10-22候选组合与构建准备：** 已核21 API1be37/Agentsaec3父tag和容器ID，定向补取已发布full bundle/hash并确认UEBA读取接线保持；19文件隔离组合Agents55＋API45通过，完整router登记检查通过，见[本批回执](docs/operations/investigation-candidate-build-20261022.md)。构建输入仅API7/Agents12，Deep使用仅摘要变体，7项旧C2/文案保持父版本；最小Dockerfile及默认只读本地构建助手已准备，candidate_preparation_audit结束独审限定ACCEPT、0项本轮阻塞。当前本地Docker未运行，尚未构建或部署，不启动worker/发模型，原5/15和旧质量失败保持。前一轮缺full bundle与组合未验为当时事实，以本批定向新增证据为准，不能外推完整运行冻结或发布通过。

- **2026-10-22阶段收口与19文件候选：** 用户确认按评估继续，已将原10项未勾责任逐项映射，并在`.local/review/investigation-stage-closeout-20261022`准备API7＋Agents12运行文件审查副本，见[收口清单](docs/operations/investigation-stage-closeout-20261022.md)与[机器摘要](docs/handoff/investigation-stage-closeout-20261022.json)。Deep以匹配candidate05的原件只追加链图摘要，现有材料交接用例对该副本1 passed；7项旧C2/文案差异未复制，工作区原件保留。fused worker实际无关闭文案差异。基线以最近full回执API1be37/Agentsaec3为记录，candidate05/Git HEAD不能当full后整个线上基线；纯full bundle hash本地未留存。候选只是可审源码，不是已构建/可部署包；组合、实际构建及发布仍需相应确认，不重跑模型矩阵/全量冻结，不部署/启worker，原5/15和旧质量失败保持。

- **2026-10-22概念辨析与结论已保存：** 用户要求保留本轮讨论的概念、例子和结论，见[对象/ID](docs/architecture/attack-chain-path.md#concepts)、[四种成员组合](docs/architecture/attack-chain-path.md#membership-examples)、[调查范围](docs/architecture/attack-chain-path.md#investigation-scope)、[Case/Playbook](docs/architecture/attack-chain-path.md#case-automation)及[结论](docs/architecture/attack-chain-path.md#discussion-conclusions)。Incident键为主实体（src_ip优先）＋首战术，Fusion链按host→user→src_ip首个活跃命中，战术仅用于阶段；同Incident异链也能正常出现，不保证层级包含。Fusion链内部续组/交付/留存已实现，当前未接下游业务消费；调查Chain重新查PG Alert，Case Path展开已有关系子图，不等于行为因果。自动写图/调查不建Case，Playbook无原生create_case、investigate需要已有Case；Hunt/KEV另有专用分支。仅文档，不据此删除、合并或改算法/自动建Case，不新发模型/启worker/发布，旧5/15与质量失败保持。

- **Kafka入口真实联合（2026-10-22）：** 依赖补齐后，用本地原worker/API连接21 Kafka/PG/Neo4j，独立topic/group一条新信封，在triage入口前取得真实prepare成功及同Alert直接邻域5节点4边，见[联合回执](docs/operations/kafka-graph-joint-20261022.md)。reader POST403/GET200、无Case/Run，观察入口主动hold，offset未提交、本地进程已停；业务分诊/模型未执行，未发布或改21常驻。GET影响范围另有14个可达候选（含同tenant历史测试资料），不作确认影响；累计PG合成夹具2条含旧失败。5/15、旧质量失败保持，未参与实现者joint_graph_audit结束独审限定ACCEPT、0接线阻塞。

- **本地Conda依赖统一检查（2026-10-22）：** 用户要求先把依赖一次补齐；按API+Agents runtime/dev及必需extras核56项直接声明，原缺21项/6项低版本及fastembed extra，统一安装并处理本地兼容性。详见[环境回执](docs/operations/local-dependencies-20261022.md)。仅项目`.local/conda-envs/socai2`，旧socai环境/源码和21部署不变；不将环境检查当Kafka真实联合通过，后者尚未成功且未发布消息。原5/15、worker OFF和旧失败保持。

- **Kafka入口写图与Conda（2026-10-22）：** 用户选择在Agents读取fused Kafka消息之后、分诊之前统一写图，避免修改Fusion；增量沿restore 2.1/3.1/3.4/4.1已本地完成，Conda环境85项直接合同通过、结束独审限定ACCEPT，见[接线回执](docs/operations/kafka-graph-intake-20261022.md)。schema通过后按tenant/canonical Alert调用原API，独立writer及review-only/shadow保护保持；后续上下文GET只读，人工Case入口仍可准备。用户允许用Conda建立项目环境，本批使用`.local/conda-envs/socai2`，不再依赖已消失的/tmp venv。实施/验证以新回执为准，不发模型、启常驻或发布，旧5/15与质量失败保持。

- **阶段交接（2026-10-22）：** 沿B5→B6汇总已有功能证据并保留链图本地版本，见[交接表](docs/operations/investigation-stage-handoff-20261022.md)。第一步告警→自动实际调查→基本结果/Markdown读取已有实证；本轮不追加模型、重复业务测试或发布。外部HTTP Tool仍仅设计，未指定真实厂商合同，不自动实施假设接口。当前基本交付未发现新接线阻断；原5/15、常驻worker OFF、质量失败和未完责任保持。

- **攻击链/图已本地实施（2026-10-21，未发布）：** 已补可信PG告警定向投影、Case/Alert读取、Bundle/Router/Deep摘要消费及Run工件，见[实际回执](docs/operations/attack-chain-path-local-20261021.md)与[原计划](docs/operations/attack-chain-path-integration-plan.md)。新Case四Agent实际模型消费、Neo4j11节点15边、29事件/4工件及Markdown读取已验，结束独审限定ACCEPT；Router/Deep接缝为直接测试。保原算法/编排，不自动建Case/改raw职责；无Case路径not_linked。原首Run预取失败和两Case共32329tokens保留，不追认质量/全分支通过，不部署或启worker。此前“未自动投影/仅规划”是实施前或旧发布事实。

- **调查模块本地实测（2026-10-21）：** 新四Run三路径、78项直接测试；14次模型尝试/13回复/已知31995tokens，Forensic一条连接失败用量未知；Router Identity/Cloud MD可运行、默认四节点带Forensic兜底MD、Deep7工具/六轮预算停无narrative，不能统称完成或质量通过。认证IPv6查询/单IOC请求字段最小本地修正均有真实接缝验证但未部署，不重调旧Run/不启常驻；连接可用性及其余质量后置。最新[回执](docs/operations/investigation-functional-20261021.md)与JSON为准，原5/15不变，结束独审ACCEPT，本地增量版本已保存（非部署镜像）。

- **2026-10-21模型输入输出交接粒度：** 用户要求每次调用说明目的、模型实际输入、可见输出格式及代码采用；预处理/工具说明须区分固定查询、Router代码领域路由与Deep模型tool_calls。见[专篇](docs/architecture/investigation-preprocessing-tools.md)。Case嵌套alerts不自动flatten，Router分支无工具循环；仅有工具名称/建议文字不能证明执行，需核实际请求/返回/下一轮ToolMessage。当前仅文档，不预定映射/校验/编排改造或新模型测试。

- **2026-10-21 Router讨论澄清：** Router为内置可选编排，`AISOC_INVESTIGATE_USE_ROUTER`仅为Case `/investigate`在默认四节点与Router间二选一，不串跑、不影响Kafka graph/deep。专业分支各一次领域模型，无内部四节点链；Router响应仅确定性dry-run摘要、报告由renderer生成，不能当完整Forensic/响应计划等价替换。graph外层固定、deep内部模型选择查询；固定官方未找到旧四节点明确弃用计划，不擅自迁为新替旧。见[实际流程](docs/architecture/investigation.md#5-router及full-graph的差异)与[设计评价](docs/architecture/investigation-design-review.md)。本次仅同步说明，不改行为/配置。

- **2026-10-21调查设计评价（用户强调）：** 修改前须详细解释自动graph/deep与默认Case四节点的业务目的、输入/输出差异、官方设计依据和四Agent分工价值/限制。核固定版本官方路线/变更日志/Case文档，区分官方声明、源码事实和工程推断；证据支持演进并存，不编造严格互补双架构。graph也可手动发起，人工默认仅是人触发，四Agent不等于四次独立复核或更准；多轮工具不等于有效证据更多。见[评价](docs/architecture/investigation-design-review.md)。当前先分析讨论，不因此合并/删除编排、新发模型或发布，旧失败及未部署边界保持。

- **2026-10-21分诊与逐调用调查梳理（最新）：** Fusion后进入Agents分诊，沿同一方式核支持项、源码默认/实际配置、输入输出/依赖、规则与模型、关闭/升级和具体对比例，再讨论取舍及最小修改。用户明确调查每一步、每个智能体/模型/工具调用均需详细说明：触发、实际输入、服务与查询参数、模型角色/提示、返回与采用、条件/循环/结束、逐步审计和持久输出。按自动post-triage graph、默认人工四节点、Router/full graph分别追踪，不把节点名当模型次数或工具清单当每次必走流程；复用真实Run逐调用实例，缺记录如实说明。见[分诊](docs/architecture/triage.md)、[调查](docs/architecture/investigation.md)。本增量先规划/只读分析，沿restore既有任务，不新发模型/重调旧输入/启worker/部署；本地先测和阶段发布、复杂可用性后置保持。

- **2026-10-21 Fusion阶段判断（最新）：** 已有告警主链职责/规则/输入输出及UEBA真实联合已梳理，复用B1/2A/2B/2C证据，当前可继续下游分诊模块，不再以Fusion全功能质量/复杂可用性作为下一模块前置。阶段结论见[Fusion小结](docs/architecture/fusion.md#六当前阶段小结可以转入下游分诊)。下一步先理解fused输入/上下文、规则/模型、关闭/升级及审计，再讨论取舍；不擅自改算法、开启常驻或新增模型调用。本地保留版本、按阶段发布，整体change未完与旧失败保持。

- **2026-10-21本地验证与阶段发布（最新）：** 用户明确可在本地运行代码、借用21基础设施测试；先本地验证并保留一个版本/回执，需要时构建本地镜像，按阶段统一发布，不每次改动或测试通过都部署21。当前UEBA→Kafka→Fusion真实联合验证走本地源码＋21独立测试topic/group及合成数据，不改常驻服务、不上传本地业务源码、不自动Git提交/推送。

- **2026-10-21 UEBA联动评分例子：** 用户已授权验证及写清开关用法；8个原FusionWorker/cache/评分交付联动例子＋原10项信号测试共18 passed，PG/Redis/Kafka为内存替身，21常驻开关仍false。配置/加分/实际结果见[UEBA第4节](docs/architecture/ueba.md#4-ueba与fusion联动评分开关及实测例子)。本批不等于真实broker、成熟基线异常或常驻启用已验；其余Fusion功能仍先讨论取舍，不继续扩测试或启用。

- **2026-10-21 raw事件支路暂缓（最新）：** 用户明确规范化事件处理交由其他模块，本轮不展开其生产/规范化、入湖、事件检测/提升及派生会话/AI资产功能；当前从已有告警进入Fusion继续分析。`RawAlert`、`alerts.raw`和告警`raw_event`正文属于已有告警合同，不在此次暂缓范围。调查读取其他模块提供的历史事件、使用UEBA结果仍保留；既有源码、配置、测试及full实测保留，本次不改变订阅/运行开关，也不声称已关闭。详见[当前范围](docs/operations/alert-processing-scope.md)。

- **2026-10-21 Fusion当前先理解再取舍：** 用户要求先弄明白Fusion原本做了哪些事情，再共同讨论需要/不需要的功能。当前先整理已有告警主链、normalized事件支路、辅助能力的作用/输入输出及相互区别；不预定删除、改造、修复或启用项，不做运行变更/新测试。功能清单见[说明](docs/architecture/fusion.md)，后续明确取舍再按OpenSpec实施。

- **2026-10-21依赖项交接简化（最新）：** UEBA、威胁情报/IOC、知识库等依赖保持原设计，以基本功能可用和“有哪些功能、如何使用”为当前交付：必要配置/入口、调用样例及输入输出说明即可。复用既有说明与有效证据，不再扩大源码分析、算法改造、复杂测试或为每个依赖另造详细设计；只补阻碍实际使用的直接接线。深入改造留到后续二开，现有源码/测试/保护保留，发现的非阻塞问题登记即可。下文完整模块分析卡主要用于后续Fusion/调查业务，不要求每个支撑依赖全部展开。

- **2026-10-21继续执行与UEBA口径：** 用户已要求按OpenSpec逐步推进change，当前以功能接通为主；已有测试原样保留并按需复用，复杂可用性/冗余专项与审查发现但不阻碍当前功能的问题登记后置。UEBA沿原设计，由上游选择投喂事件/实体；当前先说明什么消息格式发到哪个入口会纳入计算及输入输出，不新增实体名单开关或滑动窗口。先前“本轮只规划”为上一阶段事实，不阻止本次已授权执行；当前原算法、权限、unknown与worker保护保持，不自动提交/推送。

- **2026-10-21二开实施最新顺序：** 用户要求先规划并记录整条路线和关键点，再逐独立模块分析、取舍、修改和功能测试。先可复用支撑能力：UEBA → 威胁情报/IOC → 20上一版既有知识库，再进入Fusion → 分诊 → 调查/攻击路径 → Markdown结果交付。UEBA重点针对哪些实体开启、基线/时间/样本/阈值配置、输入输出及偏离算法；IOC先固定命中/未命中查询，数据量/覆盖率暂不考虑；知识库历史经验相关后看，已有读者/源码保留。基础属性表及讨论纪要见[模块工作说明](docs/operations/module-review-plan.md)，顺序细化唯一总计划B1—B6；本轮只规划，不代表业务代码、运行或验收完成。不预定合并原编排或一次重构全链，复杂可用性和冗余专项继续后置。

- **2026-10-21报告交付：** 当前只要求Markdown生成、持久保存及按Case/Run读取；PDF暂缓，HTML不作本轮前置。不继续格式专项或新报告模型验证；已有代码、依赖和历史结果保留。

- **2026-10-21 full配套补迁：** 按用户最新指示，历史事件补查、Attack Path、UEBA、事件检索、IOC信誉增强及OpenSearch原版索引/检索纳入原版迁移；补enrichment/threatintel/ueba完整模块和直接依赖，沿原接口做必要配置/认证适配并保证基本功能可运行。复用21存储，不另起整套full；不新建上游缺失后端，不扩全量采集/原始检测。复杂可用性、额外质量及未使用分支专项继续暂缓；具体实际验证见[full配套回执](docs/operations/full-support-migration.md)。


## 项目与当前路线

- **full配套运行更新（2026-10-21）：** 历史事件Kafka→Fusion→ClickHouse→API SQL/补查、原UEBA基线→常驻Agents读取、IOC增强接口、OpenSearch项目IOC索引写/搜/精确匹配及TI/API代理已基本实测；无新模型/Feed/厂商调用。API/Fusion同1be37/c52镜像，Agents更新为aec3c54f（candidate05仅COPY bundle）、UEBA 8b04bc64 / enrichment eb59af97 / TI c15d75f4。原图/APOC依赖已接，AttackPath目前实证为PG2节点/1关系回退；UEBA仅1样本，无来源增强不判安全。原worker OFF/7RO/60秒保持，报告只需Markdown。完整运行保原29层后加full-support/ueba/enrichment/threatintel四层；Neo4j插件单独infra overlay。旧“当前镜像/层数/graph关闭”是历史侧注，最新以[本批回执](docs/operations/full-support-migration.md)和PROGRESS为准，整体迁移未完成。



- **2026-10-21最新执行口径（覆盖下文旧优先级和验收前置）：** 当前先完成迁移第一步：从正式输入告警开始，经原告警处理/分诊实际触发并走完调查编排，取得与告警/Run关联的基本调查结果和报告；需要调查时无需人工再次点击。先接通这条完整流程，其他入口、全部分支和常驻运行准入不作为这一步前置。复用已有有效证据，只补实际未接通的环节，不以仅创建Run或调用函数代替走完流程。
- **问题及复杂验证后置：** 用户明确“发现的问题可以做好记录，然后迁移结束后逐步评估解决”，且包括复杂可用性专项、冗余测试和重复校验。质量、算法、报告表述、用量完善、恢复等问题保留原证据并登记迁移后评估；当前仅做走通主链所需的源码/直接依赖/配置/接口接入及最低限度验证。复用相关原测试，不默认重复组合回归、全量hash/水位/表计数/冻结、逐入口模型矩阵、多轮复核或新建验收控制框架；保留change结束的一次必要独审。详细问题沿用[现有登记](docs/operations/upstream-issues.md)，不另建任务树。
- **事实和既有保护保持：** 后置不追认旧质量通过，不撤现有租户/权限、预算和unknown保护，不重放旧unknown或清空积压；未授权真实厂商动作和Git提交/推送不开启。已修源码及已有测试保留，不为回退另造工作；运行启用和第一步是否走通仍按实际证据记录。

- **2026-10-21工作目的与执行授权：** 用户明确开始执行，允许多个worker并行。当前工作有三个共同目的：①迁移告警及后续处理流程，保证实际功能和结果符合预期；②在迁移中理解源码，对照固定版本官方文档核功能点，标清已实现、未接通和声明未实现，不把文档声明当交付事实；③整理当前架构、模块职责、数据/调用关系与扩展点，供后续二次开发。执行与功能对照、架构梳理同步推进；不另开全平台重构或无限上游审计。见[总计划](docs/operations/completion-plan.md)、[官方功能对照](docs/operations/alert-function-alignment.md)、[当前架构](docs/architecture/alert-processing.md)。下列旧“先讨论/仅规划”是历史阶段，当前已进入实施，完成仍以实际证据为准。

- **2026-10-21最新范围/优先级（优先于下列旧批次“下一项”）：** 用户确认完整迁移告警与调查，包括自动分诊、自动关闭告警、自动升级调查及人工调查/报告；playbook和反馈可暂缓，一体源码/依赖原样保留，不额外修改或专项测试。启动顺序、退出、重启/故障恢复等可用性专项登记后置，不作为功能迁移前置；现有保护代码、旧unknown和历史证据保留。[完整性评估](openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/assessment.md)已完成，现按批实施修复和必要定向部署，实际运行与质量以回执为准；R02[侧附暂缓](openspec/changes/admit-review-only-triage-worker/status.md)，原0/17及五文件不改。完整目标不等于自治质量或真实响应已验收，亦不扩大前端/采集/检测职责。
- **实施总原则：功能完整、结果正确优先，最小必要适配。** 所有一体模块/依赖都可整体原样迁入，不因本轮暂不使用就拆分、删改、重构或额外测试，playbook/反馈只是例子。仅改直接缺失的功能、正常业务结果错误及实际接入必需项；复用现有测试，只做本次改动所需的最少代表验证。冗余抽象/多层包装、提前统一架构，以及启动顺序、退出、重启/恢复、故障注入、长稳/压力等服务可用性测试和修复登记暂缓，不再设成功能迁移前置。整体原样迁入可标“未专项验证”，不得改写成已测通过；现有保护与旧证据保留。
- **当前总计划：** [completion-plan](docs/operations/completion-plan.md)按B1告警链、B2默认人工调查、B3知识实际消费、B4自动分诊/关闭/自动调查、B5其他调查及交付、B6整体功能验收推进，沿用现有六阶段及restore产品任务。自动升级后须实际自动取证/分析/结果交付，无需人工再次点击；不是仅创建Run或给建议。当前B1已限定完成，B2/B3已接入并有实际消费/报告证据但质量未全过，B4自动调查的正常结果阻塞正最小修复，R02仍后置。

- **当前运行侧注：** B1已限定验收；candidate03的B4/B5/报告/技能pin修复与原生PDF依赖已部署，组合383项通过并独审。candidate04再修一处KB标记解析并接原七权限只读API服务身份，32项直接测试通过、定向替换API/Agents健康（API1be37c38、Agentsc311a94b、Fusionc52b9aac），部署后独审及六项HTTP通过（200/403/403/401/403/200）。candidate05仅默认Forensic/Report两文件假设/范围/处理时间语义，24项直接测试及独审后已一次替换Agents至4ccf3a6d，env/七RO/60秒保持；0新模型/消息/业务写，不含尚未部署的C2图/deep修复。实际仍用原28层末加integrity的[二十九层命令](deploy/aisoc21/README.md)，772运行Py/lock1。新人工Run四调用10167 tokens、MD/HTML/PDF200，内容质量仍未全过，原失败Run不重调/改写。旧unknown/积压/十reader保持，B1两临时操作key已撤401；后续A/B两操作key及新C六短期key现已全部停用并逐枚真实401，旧十reader及永久服务只读身份保留。C上下文11项只读验收通过；第一条source-v1 C告警经原worker实测BTP0.95/原0.85阈值自动关闭、1真实回复2174tokens，分类/理由/实际关闭独审通过，旧预算/两old组保持；第二条已自动调查，但deep六步截断、graph20451 tokens超过20000边界，报告把知识映射和风险prior写成攻击/确认事实，质量失败后STOP；首NR/告警未关保持。两例8回复24742 tokens，不重调旧输入；最小源码修复/独审进行中，常驻worker仍OFF，整体迁移未完成。下列旧运行层数与“下一项”为历史事实。

- 用户于2026-10-20授权按当前服务端范围持续推进到迁移完成：先落实剩余规划，每个change结束必须由未参与实现者做审计；常规接入、阻塞修复、隔离验收、有界模型和必要定向部署直接推进。上游已有非阻塞问题统一登记暂缓，不扩为无休止优化；本地适配缺陷和已承诺主链/租户/持久/审批阻塞不能用登记替代修复。执行追踪见[完成计划](docs/operations/completion-plan.md)与[上游问题清单](docs/operations/upstream-issues.md)。真实高风险动作仍需明确受控目标/凭据/审批，Git不自动提交或推送。

- 工作目录：`/Users/lychee/Documents/project/socai2`；GitHub：`https://github.com/Dinines/socai2`。
- 产品名称为 **stingAISOC**；AiSOC 是上游来源，服务名、配置名、数据库名暂按原版保留，避免为改名破坏移植基线。
- 当前目标：**告警及后续数据处理服务端**。接收已有告警，交付API、消息与持久化结果；不负责前端、采集、原始事件检测或独立展示推送服务。范围以[模块对齐](docs/operations/alert-processing-scope.md)为准，阶段目标见[迁移路线](docs/operations/service-roadmap.md)。早期全量移植决定已归档，不再约束当前完成条件。
- 本项目是新的独立工作线，不自动继续旧 SOCAI 的 Basic/OpenSpec 任务，不以旧实现合同强制改写原版。
- 用户于2026-10-21明确采用 **OpenSpec 作为本项目实施规范**。后续变更按本项目 `openspec/` 管理，不导入旧工程的 change 或完成证明；入口见[OpenSpec实施说明](openspec/README.md)。
- API/Fusion固定源码及直接测试已迁入并在21跑通1F标记数据链；1D向量和1E五角色网关只完成各自结构/存取/路由验收；1G Agents/Actions已迁入并验人工调查/API持久结果与dry-run，常驻自动worker/完整知识消费/真实响应未启；不能写成整个服务端迁移已完成。当前实测与限制见PROGRESS及各批回执。
- 用户已确认不同上游告警各存一行，再关联到同一事件。2A独立告警source-v1/旧legacy兼容及持久关联已限定验收（95项测试），旧legacy合并事实不重建；2B-01风险重投/并发边界（40项）与2B-02规则内容指纹/实际方法采用/缓存恢复（83项）已限定验收，旧材料/回执不改写。
- 2C-01本地历史IOC经真实HTTP/Kafka/Fusion/PG/API及重启回查已验（62项测试），历史匹配保留日期/弱证据且不增权，见[回执](docs/operations/2c-ioc-consumption.md)。2C-02 PG资产/权限/漏洞/先前告警只读视图及独立评分已限定验收（30项测试），见[上下文回执](docs/operations/2c-processing-context.md)；2C-03已核来源不足及缺源返回，真实事件/UEBA消费仍未接，见[回执](docs/operations/2c-event-ueba-sources.md)。3A-01规则抑制持久回执与DLQ/提交保护已限定验收（83项测试），见[回执](docs/operations/3a-policy-suppression.md)；3A-02有界真实模型/账本/API及盲测分类已限定验收（46项测试，6成功回复/7406 tokens），首轮污染结果保留，完整质量未过，见[回执](docs/operations/3a-model-triage.md)。该批发现的风险分语义问题后续由3A-03修复；当时五类context401后续已逐项处理；旧增强/API工具身份及引用质量仍未解决，常驻worker和响应关闭。
- 3A-03缺失/null与显式0风险分及来源语义已限定验收（184项测试，1次真实模型/1345 tokens），见[回执](docs/operations/3a-risk-score.md)，保留原数值特征算法和旧材料。3A-04每租户组织记忆认证、过期/失败状态、事务工件与真实模型消费已限定验收（194项测试、1次真实模型/1523 tokens），见[回执](docs/operations/3a-org-memory.md)。只配置A/B测试tenant，两枚受控30天只读reader key保留，三操作key停用；缓存120秒不保证服务端即时撤销。3A-05技能读取认证/选择来源、事务工件与实际模型消费已限定验收（347项测试、48项最终HTTP检查、一次真实模型/1677 tokens），v3当前头与原v2工件分离、重启回查保持，见[回执](docs/operations/3a-tenant-skill.md)。两枚新settings:read reader保留30天，三操作key停用；原两枚组织记忆alerts:read key及映射保持。3A-06 KB读取认证、保守cutoff、实际采用文本/引用及事务工件已限定验收（236项测试、一次真实模型/2095 tokens），见[回执](docs/operations/3a-kb-read.md)。真实prompt提供KB1，模型未引用KB标记，不能宣称引用质量通过；两次模型前预算预检失败保留，恢复未重发输入或模型。新增两枚独立knowledge_base:read reader保留30天，原组织记忆/技能四枚key及映射保持。只验A/B合成PG全文资料，不等于已有向量索引或真实SOP质量；该批当时处置/身份两类context401及完整质量未过；处置后续见下条。
- 3A-07近期分析员处置认证读取/采用来源与事务工件已限定验收（396项测试、60项显式HTTP检查、一次真实模型/1909 tokens），见[回执](docs/operations/3a-dispositions.md)。三条个人意见进入7355字符的实际prompt，模型needs_review/自报0.65，未精确提及note或反馈ID，不作因果采用或质量通过。初394项测试后收尾独立读取发现导入环，补两项独立进程测试并仅重建Agents；最终镜像常驻身份读取通过，未重测模型。新增两枚独立alerts:read reader保留30天，原org/skill/KB六枚key保持，三操作key停用；该批当时身份reader401，后续见下条。
- 3A-08身份读取认证/图源失败/确切采用及事务工件已限定验收（496项测试、62项HTTP检查、一次模型1781 tokens），见[回执](docs/operations/3a-identity-read.md)。五类reader已接通，仅A/B合成资料；新增两枚graph:read reader，原八枚保持。导入cutoff不等于HR历史或当前授权，300秒缓存不保证即时撤销。脚本失败与检查点恢复保留；受控复验后续见下条。
- 3A-09三例受控复验与可靠性审计已完成，见[回执](docs/operations/3a-triage-admission.md)。三次真实模型5223 tokens，分类3/3但p01时间/授权理由不受支持，完整质量不通过；broker替身复现冷重投重入模型方法、坏schema无DLQ提交、ledger False仍提交及暖保存恢复丢五类来源语义，worker准入不通过。无运行改动或重启，三操作key401、十枚reader保持；后续修复见下条，旧回执不改写。
- 3A-10-01普通分诊持久确认与坏消息已限定验收（143项测试、26项显式HTTP、0真实模型），见[回执](docs/operations/3a-triage-durability.md)。两文件修复使live持久失败及已解码坏schema不再静默提交；真实broker7次发布/8次交付、4次模型方法替身，正常五类来源工件及Agents重启回查保持。旧57告警/28Run/77事件/77工件/21成本行保留，该批后58/29/78/82/21；仅Agents更新，35其他容器/18卷/134迁移保持，三操作key401、十枚reader保持。该批当时冷重投/缓存来源/SDK预算未修，后续保护见下条，旧回执保留。
- 3A-10-02普通分诊首次结果/重投保护已限定验收（207项测试、55项显式HTTP、0真实模型），见[回执](docs/operations/3a-triage-recovery.md)。三条真实HTTP/Fusion信封经新独立broker对象验证同worker完整保存恢复、fresh进程复用、跨进程单次认领及退出后unknown；3次发布/7次交付/3次方法替身。当前61告警/32Run/83事件/92工件/21成本行，两新Run完成、一条仅保留开始意图；旧14表材料、35其他容器/18卷/134迁移及十枚reader凭据保持，三操作key401。保护仅Kafka普通live路径，direct triage/replay及原抑制分支不扩张；负cursor真实422、生产SDK预算和完整质量仍未过，下一3A-10-03见[总计划](docs/operations/3a-worker-reliability-plan.md)。
- 3A-10-03-01分诊SDK默认retry0/45秒、整次调用45秒截止及-1增量cursor已限定验收（189项测试、71项显式HTTP、0真实模型），见[回执](docs/operations/3a-triage-request.md)。仅更新并重启API/Agents，旧14表材料、34其他容器/18卷/134迁移及十枚reader保持，三操作key401；无新增告警/Run/事件/工件/成本。跨进程租户额度、积压和停止恢复仍待3A-10-03-02，完整质量与worker准入未过。
- 3A-10-03-02持久分诊额度/积压/停止恢复已限定验收（263项测试、137项显式HTTP、0真实模型），见[回执](docs/operations/3a-triage-budget.md)。新增项目预算表，原134迁移及旧14表材料保持；每次20000预留单位非实际usage，未知占位不自动过期。真实broker6发布/14交付/5次HTTP替身开始，保留三未知预约及一条积压；最终67告警/37Run/92事件/106工件/21成本行，5预约/100000预留单位。仅Agents更新/重启，35其他容器/18卷/十枚reader保持、三操作key401；失败与受控额度调整保留。当前A/B测试policy，完整准入与质量仍未过。
- 3A-11-01只读准入复核已完成，见[回执](docs/operations/3a-admission-review.md)：旧p01时间/授权错误未被indicator gate识别；常驻Agents审批提案guard实际True且缺Kafka bootstrap/TLS，旧调查工具身份仍缺。三未知预约及A积压保持，0模型/消息/offset提交/运行改动；完整准入未过。下一[3A-11-02配置补齐](docs/operations/3a-triage-admission-config-plan.md)，保持worker禁用，然后单独修提示词/复验质量。
- 3A-11-02常驻分诊配置补齐已限定验收，见[回执](docs/operations/3a-triage-admission-config.md)：仅Agents同镜像重建一次，新增四项环境值，复用原只读CA；审批提案guard现False、Kafka SSL/主机名校验及六组offset读取通过。旧14表/三unknown/A积压/十reader/其他35容器/18卷/134迁移保持，0模型/消息/提交。当前22层、19源码层，worker仍OFF；下一[3A-11-03理由提示词修复](docs/operations/3a-triage-reasoning-plan.md)，完整准入/质量未过。
- 2026-10-20[已有迁移审核](docs/operations/migration-review-20261020.md)发现Fusion交付确认、source-v1缺行关联恢复、分诊正文/时间投影、校验前缓存及停止异常清理仍有缺陷；源码来源/hash对应不等于整体正确。该轮未修运行代码；后续R1/R3由C01限定修复，R2/R4/R5由C02限定修复，理由复验见C03；此前topic/group/DLQ“未配置”系误判，1G已配置topic/group、DLQ按项目topic派生，旧冻结回执由审核勘误。常驻worker仍禁用，不重调unknown。
- C01 Fusion交付/首次结果恢复已限定验收（107项测试、6项HTTP、0模型），见[回执](docs/operations/c01-fusion-delivery.md)。真实PG故障接缝与独立SDK发送失败均未越过offset，首次完整快照/新legacy兼容及DLQ确认通过；只更新Fusion，新增5告警/1DLQ，旧材料/预算/reader/其他35容器保持，2操作key停用；探针失败与只读恢复保留，最终独立审计通过。有限TTL全部痕迹消失不保证恢复，旧snapshotless行不重建；下一C02见[执行卡](docs/operations/c02-triage-material-cache-stop-plan.md)。
- C02分诊正文/发生时间投影、普通live停跨告警pattern结论复用及异常停止清理已限定验收（118项测试/断网SDK探针/0真实模型），见[回执](docs/operations/c02-triage-material-cache-stop.md)。仅Agents更新并设60秒停止宽限；旧14表/预算/十reader/原积压及其他35容器保持，首轮失败与部署列表顺序断言/只读恢复保留。direct/replay旧缓存、实际在途Docker停止及模型质量未外推；下一[C03](docs/operations/c03-triage-reasoning-plan.md)。
- C03-01分诊时间/授权证据提示词v3已限定验收（88项测试/断网SDK/0真实模型），见[回执](docs/operations/c03-triage-reasoning.md)。21其他prompt、schema及旧数据/预算/reader保持，仅Agents更新一次、继承60秒宽限；完整prompt6560字符/6502字节。原操作入口拒绝及探针前修正保留；不等于理由质量或常驻准入，该批传输验收不替后续质量。C03-02仅case01一次1998 tokens后因冻结分类/理由未过而受控停止，后三例未执行；基础设施通过、3操作key401、原失败/恢复保留，见[回执](docs/operations/c03-triage-quality.md)。C03-02B新case01一次真实模型1918 tokens，TP分类正确但无据断言未授权，理由质量未过；后三例未执行，3操作key已停用/401，见[回执](docs/operations/c03-triage-quality-recheck.md)。02B当时v3/039f及25配置/22源码层保持，worker OFF；后续澄清见下条。
- [C03-02C-01授权事实边界](docs/operations/c03-triage-authorization.md)v4及lock已限定验收：88项直接测试、4个断网生产SDK完整body（7754–7814字符/7669–7729规范UTF-8字节），0真实模型/业务PG写/新消息。只更新Agents一次至9ba6，env/七只读bind/60秒宽限保持，当前26 Compose/23源码层。旧14表/7预约140000单位/3unknown/十reader及其他35容器/18卷/134迁移保持。验收脚本导入副作用已修，早期104只读SQL/4次metrics误追加的112计数文件保留并归本批，旧844冻结字节保持。模型理由质量和常驻准入仍未过，worker OFF；下一02C-02另冻新四例，不重调旧两例。
- [C03-02C-02新复验](docs/operations/c03-triage-authorization-quality.md)受控停止并封存：C03-02C-02三例实际模型共5971 tokens：前两例分类/理由通过，第三例把缺少转移证据误判为FP并推断规则误报，按冻结判据失败停止，第四例未发。三操作key已停用且实际401，技术持久链与结束独审通过；新增3告警/Run、9事件/21工件/3成本/3shadow、3responded预约60000单位，0QA。旧7预约/140000单位/3unknown保持，累计10预约/200000单位；26配置/23源码层保持，0重启。下一C03-02D-01只澄清“无法核查检测条件不等于规则误报”的最小提示词边界，先做0真实模型直接验证和独审；不重调旧三例、不改旧判据。理由/分类质量与常驻准入仍未过，worker OFF，整体迁移未完成。
- [C03-02D-01检测有效性边界](docs/operations/c03-triage-detection-validity.md)v5检测有效性提示词及lock已限定验收：88项直接测试、4次断网生产SDK完整body（7827–7917字符/7742–7832规范UTF-8字节），0真实模型/新业务写。仅Agents一次更新至9cb719，原env/七只读挂载/60秒停止宽限保持，当前27配置/24源码层。旧14表、10预约/200000预留单位/3unknown、十reader、其他35容器/18卷/134迁移保持，部署前/运行/收尾三审通过。下一C03-02D-02另冻四条新对照输入，验证有反证FP、明确授权BTP、缺证NR及事件窗外NR；本四例不复验v5 TP，后续常驻新TP仍须实际独审。旧三批质量失败与七条未发输入保持，worker OFF，质量/常驻及整体迁移未完成。
- [C03-02D-02新对照](docs/operations/c03-triage-validity-quality.md)质量失败后已受控停止并完成结束、撤key后及封后独立审计：两次真实模型回复共4081 tokens；case01 FP分类/理由通过，case02时区换算错误且把窗内已授权活动判为FP，分类/理由失败，case03/04未执行。三操作key已停用并逐枚真实401，十reader及旧10预约/200000单位/3unknown保持。新增2告警/Run、6事件、14工件、2成本/2shadow、2responded预约40000单位，0QA；预约单位不是usage。告警仍new、auto_closed=false，不声称发生错误关闭。当前27配置/24来源层、184Agents/769运行Py及lock保持，0源码/Compose改动、0重启/DDL。首次发送前因本地验收算子遗留旧输入SHA/v4合同被拒绝，0业务/模型；原失败、旧stop与显式恢复审计/独立断网合同probe/新质量stop全部保留，未重复freeze、身份、额度或topic，不重调旧输入。下一先另冻人审profile新准入计划，尚未实施或验收；原自治分类/理由质量及常驻准入未过，worker OFF。原C03质量硬门和本批判据保持，C04/C05调查/知识及后续响应仍待逐批验收，整体迁移未完成。
- [C03-R01](docs/operations/c03-triage-review-only.md)代码隔离与定向部署已限定验收：191项断网测试通过（22项新增、169项既有直接测试），0真实模型/新业务写；仅Agents一次构建、一次替换为19f8f1a5，review_only_v1已配置、worker OFF，七只读挂载/60秒宽限保持。旧14材料表、全部告警字段、12预约/240000预留单位/3unknown、十reader、其他35容器/18卷/134迁移及消息水位保持。首次观察脚本RLS错误与189通过/2夹具失败及恢复均保留。当前28层运行定义、185 Agents/770运行Py，prompt/lock v5不变。下一按[人审准入卡](docs/operations/c03-review-only-profile-plan.md)另冻R02，验两条新A/B输入的有限真实main消费与首次结果恢复；原自治质量失败、C04/C05及后续调查/响应仍待验，整体迁移未完成。
- 当前运行必须使用identity→risk→policy→ioc→context→suppression→risk-score→org-memory→tenant-skill→kb-read→dispositions→identity-read→triage-durability→triage-recovery→triage-request→triage-budget→triage-admission-config→fusion-delivery-c01→triage-material-c02→triage-reasoning-c03→triage-authorization-c03→triage-detection-validity-c03→triage-review-only-c03叠加层，完整二十八层命令见[21操作说明](deploy/aisoc21/README.md)。当前配置差异见[配置来源](docs/handoff/3a-triage-admission-config-source-manifest.json)，当前源码见[C03-R01来源清单](docs/handoff/c03-triage-review-only-source-manifest.json)。专用图读取不启通用schema初始化，READ_ACCESS不是数据库只读租户角色；处置意见按rule优先、创建时间及ID排序，created cutoff不重建后来编辑的旧意见，来源投影hash不是历史版本证明；默认120秒缓存不保证服务端即时撤销或编辑生效。KB为PG全文检索，保守排除split后创建或修改的行，不重建旧正文；最终nonce块/文本/hash与引用记录分开核。技能加法权重不等于严格优先级，deep investigation旧版本pin失败可落当前版本，graph关闭，列入3B准入检查。回退注意旧float-only消费者不兼容新null消息；新读取回执/工件first-write保证不等于整个Run完全冻结。不外推完整缓存丢失、持久风险账本、跨实体事务、无限并发或完整调查质量；Fusion ML状态认证503仍保留。
- 用户于2026-10-20进一步确认：从 `/Users/lychee/Documents/project/SOCAI/opensource/AiSOC` 参考源码直接复制相关代码，**按规划逐步迁入，先迁依赖**；必要的删除或修改先讨论。第一批依赖快照不等于业务源码完整迁入。

## 开始工作先读

1. [项目入口](README.md)、[进度](PROGRESS.md)。
2. [当前服务端范围](docs/operations/alert-processing-scope.md)、[六阶段迁移路线](docs/operations/service-roadmap.md)、[依赖迁移计划](docs/operations/dependency-migration-plan.md)。范围、阶段退出、批次验收、完成状态分别在这些文档及PROGRESS维护，不另立冲突目标。
3. [模块总览](docs/reference/aisoc/01-system-map.md)，再读对应 M 编号的专题。
4. 涉及环境或模型时读 [环境](docs/operations/environment.md)、[配置与凭据索引](docs/operations/configuration.md)及[已有证据](docs/operations/verified-evidence.md)。需求日常阅读见 [需求 Markdown](docs/requirements/README.md)。
5. 用户指出 [docs/anal](docs/anal/README.md) 保存此前分析：复用模块、源码、测试和风险结论，对照固定源码核实。`docs/reference/aisoc`为交接链接版，两份分析保留；其中全量上游结构不扩大当前职责，历史规划不作为当前任务。文档入口见[导航](docs/README.md)。
6. 读[OpenSpec实施说明](openspec/README.md)与[项目配置](openspec/config.yaml)，通过 `openspec list` / `openspec list --specs` 查当前 change 和规格，再读本批相关的完整 spec、proposal、design、tasks及status。迁移change `restore-alert-investigation-integrity` 按10月24日收尾回执归档；后续独立调查应使用自己的change。旧R02目录虽仍可能被CLI列为ready，但按status暂缓，不执行。

## OpenSpec 实施规范

- 行为、API/消息合同、租户/权限、持久化、模型调用、部署及运行准入变更，必须先有本项目 OpenSpec change，形成 `proposal.md`、对应规格增量、`design.md` 和 `tasks.md`，再实施。使用 `spec-driven` schema；纯工具/文档/重构且没有规格级行为变化时，设置 `.openspec.yaml` 的 `skip_specs: true`，不得编造业务需求来凑校验。简单拼写/链接修正可并入相关 change 的记录，不另开重复任务。
- 职责范围仍以 `alert-processing-scope.md`、阶段退出以 `service-roadmap.md`、路线依赖以 `completion-plan.md` 为准；实际完成由 PROGRESS、原批次回执和来源清单证明。OpenSpec追踪本次增量及场景，不复制另一套完成口径；范围冲突先对齐，不静默扩张。
- change按本次实际影响保留需求、必要设计、简短任务、直接业务证据和未参与实现者结束审计。已有受控运行边界沿用，不默认重做每批全量冻结、计数或恢复验收；仅原样迁入的一体模块不新增独立修改/测试任务。创建change或CLI校验不代表业务已通过，也不新增逐批用户确认门。
- 按最新范围，只补本批直接功能/结果及必要身份检查；冗余设计和服务可用性相关测试、修复均后置登记，不将旧R02或旧全链清单重新变为功能前置。正常业务结果错误仍按最小改法修复；只在特殊故障/恢复场景出现的接续问题可后置，不为此先建通用恢复框架。既有已验修复不回退。
- 实施前运行 `openspec validate <change> --strict --no-interactive`；任务仅在实际完成并有证据时勾选。失败、unknown、未执行样例和未验能力原样保留，不以文档齐全替代实施完成。
- 结束独审通过、直接验收和交接更新完成后，才执行 `openspec archive <change> --yes`，将已交付的规格增量同步至 `openspec/specs/`。工具/文档change使用 `--skip-specs`；归档后复核规格和任务。已封存的R01及更早批次只作前置引用，不倒填新change或改写冻结回执。
- 调查模块按顶部最新授权在专用分支逐阶段本地提交；其他任务遵循各自授权，不自动推送Git。OpenSpec不替代明确目标、凭据及高风险响应审批，亦不授权重放旧unknown、清空积压或启用常驻worker。

## 来源与开发边界

- [AI SOC2.docx](docs/requirements/AI%20SOC2.docx)是完整产品需求原件，不改写；本仓库实施其用户确认的服务端职责子集，范围外需求不计作本服务已交付，也不自动转为本轮任务。实际完成与运行行为以证据为准，上游注释、历史建议及旧工程完成状态不能覆盖当前范围或实测事实。
- 固定上游 `https://github.com/beenuar/AiSOC`，初始 revision：`34ca18c57dd4175539e5c6dd3d04a72dc057306b`。测试中途不自动升级。
- 范围内尽量保留上游服务关系、测试和直接构建依赖；不默认迁入采集、原始事件检测、前端和独立展示推送服务，不因范围收敛盲删共享代码/SQL。仅做必要接入/环境适配、真实阻塞修复及基本授权/凭据保护，记录差异；编排合并、存储替换等在基线测试后再决定。
- `SOCAI/opensource/AiSOC` 为旧工程只读参考，不在其中修改移植业务。迁入范围内服务源码时先检查与本目录 README/AGENTS 等同名文件，保留上游原件和本地差异，不直接覆盖。
- 用户授权充分调配已提供资源，复用已有数据及`../SOCAI/knowledge`，模型服务可按负载部署在20、21，43沿用既有对话服务；常规已授权操作直接推进。数据/模型来源及选择见[知识复用计划](docs/operations/knowledge-data-reuse-plan.md)，较大本地4B模型作为比较候选，不能把资源充足写成质量已验。
- 原版持久化、租户、身份和状态语义先实测；调查结论、响应提案、审批、执行和效果验证分别记录。已冻结事实/原始证据不改写。
- 模型建议不直接扩大工具权限；高风险真实响应要求明确目标、基本授权与审批。结果 unknown 不自动重发有副作用操作。
- 日志、文档和 Git 不放密码、token、私钥、隐藏推理或不受控原始敏感材料。凭据仅记录受控位置。

## 环境与测试

- 用户确认新项目部署目标是 `192.168.1.21`；SSH 别名 `sting-infra21`。优先复用21公开数据服务，按项目库/账号、topic/group、集合隔离对象；用户允许必要时适当重启，先核影响、保存配置与状态，仅操作所需单服务并验证恢复。21四个旧业务容器保持关闭；保留其他项目和数据，禁止全库/全卷清理。
- `192.168.1.20` 是已有 AiSOC 参考环境，账号 `lychee`、目录 `/home/lychee/beenuar`；其部署/测试记录可复用为对照，不等于新项目已经部署到21。
- 对话测试服务沿用 43 的现有 OpenAI-compatible 服务；20 本地 Ollama 只做 embedding，21已复现独立同模型实例（16核CPU/32GiB），仅结构/存取已验，未接调查消费。配置和实际可用性以操作前核对为准。
- 开始先检查分支、未提交内容及目标环境，保留已有修改；默认工作分支 main。
- 优先复用有效上游测试和既有证据，只补本次变更所需的最少功能/正确性验证；一体模块原样迁入不额外修改或测试，不默认全仓回归、全部依赖专项或慢速矩阵。冗余设计与服务可用性测试/修复按上述原则登记后置。
- 每条重要验收写输入 → 实际中间产品/调用 → 最终值与关系。区分测试替身、真实基础设施、真实模型、真实厂商和生产观测。
- 用样本/测试 tenant、Case、Run 或可识别测试标签隔离；不清空整个数据库、集合或现有业务数据来方便测试。
- 模型/向量服务连通不等于质量通过；ATT&CK/TI/memory 的索引成功不等于调查已消费结果。费用/usage 未知不写成零。
- 变更行为前按上述OpenSpec规范建立当前批次的范围、规格增量、设计、任务和验收；不复制旧任务树或借用旧 change 作为完成证明。
- 交付时更新最近文档和简短 PROGRESS，说明实际变化、验证限制及下一单项。提交/推送依据本项目明确指令执行。
