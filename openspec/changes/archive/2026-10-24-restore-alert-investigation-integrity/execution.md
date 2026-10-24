## 2026-10-23 测试数据工具迁移及逐步实测

按用户新授权执行：先保工具基线/源码hash，模板选择+wire12检查→sender16检查→真实3条Kafka/Fusion/PG→observer真实只读→2条新tenant自动分诊/调查。44直接测试/39子项，真实两例6回复26492tokens、29工件hash/关联全过，例A自动关闭，例B原graph/Deep4轮8工具后token停止partial/MD可读；内容标记泄漏、软预算和状态展示限制如实保留。未修改188个Agents源码或6上游原件，0新部署/生产group变更/真实动作。详细docs/operations/testdata-migration-execution-20261023.md，原5/15不改。

本地进程及隧道清理，2测试key停用，正确RLS下预算2 responded；初次无RLS空观察及测试探针旧失败保留。Git忽略新运行材料均通过，补三个可选输出目录，不误忽略源码/夹具；用户准备自行push，本轮不提交/push。结束独审和保版见audit。

## 2026-10-23 测试数据迁移重新规划（仅文档）

用户最新要求先找回原设计再规划。回查原会话「继续推进迁移」、10月22日工具/恢复回执、固定原件及当前入口/分诊/评估源码；形成docs/operations/testdata-migration-plan-20261023.md。复用旧8离线＋2替身及attempt02真实接线证据，未重跑。拟补场景选择与source-v1 Kafka wire、有界发送、3条新隔离Fusion接线、只读结果观察、2例自动分诊/调查；保角色/模型/六轮及原预算，逐项改测再推进。

未参与编写的handoff_audit只读独审，要求补独立DLQ/消费起点和业务调用轮次与SDK/网关尝试的区别，已纳入。最终限定ACCEPT，0项本轮必须修项。root核3份相关文档15本地链接/围栏、git diff --check与OpenSpec strict通过，任务仍5/15。选定文档及审阅结论保存于.local/versions/testdata-migration-plan-20261023/；共享记录含此前历史内容，不把整份文件或当前工作区差异当本轮实现。

本轮无工具/业务源码改动、新样本生成投放、业务测试/模型/生产访问/部署、Git提交推送；原调查小修和历史失败保持，计划不构成已实施事实。

## 2026-10-23 调查小修及逐步测试

用户先授权提交实施，后明确仅完成小改动并逐步测试。方案基线5e0ce171；沿2.1/3.1/3.4/4.1完成Forensic校验前移/同一Run身份、最小validation与确定性采用、逐工具SQL事务回执/结构状态、Deep finally与runner局部进度交接、Markdown材料引用。九业务文件内局部修改，保角色/拓扑/参数，不预勾原任务。

详细逐步测试与失败记录见docs/operations/investigation-result-handoff-20261023.md：人工17→38、工具18→87（3PG先跳过）→13、SQL2→串联44无跳过、报告/runner18；重复用例不累计总数。真实模型4尝试/2回复：首2个503无回复用量未知，仅观察进程绕开本机自动代理后新输入2回复2714tokens，模型原文仍有偏离，程序交付合同通过。无生产业务写、部署或常驻更动。未参与实现者结束独审另记audit，原5/15及旧失败保持，后续设计等待讨论。

## 2026-10-23 事件级与跨事件分析研究（仅文档）

用户要求依已有分析评估必要性，并查阅微软等主流产品。root只读核Fusion分组、自动单告警Run、Case多材料、incident_id入口及跨Incident图候选；联网查官方产品文档并标明版本/预览边界。形成docs/architecture/incident-analysis-product-comparison-20261023.md，原产品方案加入口。建议以事件整体结果、持续增量和候选关系验证补齐现有能力，不自动实施或改变原5/15。研究步骤/前稿保存在.local/versions/incident-analysis-research-20261023/。结束文档检查及独审另记audit；无生产访问、业务模型/消息/测试、部署或Git提交推送。

## 2026-10-23 调查优化方案审核修订并保存（非实施）

用户先要求审核意见，随后明确“不是执行，是方案保存”。本次只修订docs/architecture/investigation-product-engineering-roadmap-20261022.md，沿现有2.1/4.1保留文档记录，不新建执行任务树、不改规格行为、不勾原任务。

1. 只读对照原建议、当前相关源码及10月22日v1两例回执；区分实际调用问题、静态缺口、未全发布C2和未来设计。
2. 保存原稿及本次记录文件到.local/versions/investigation-plan-review-20261023/before/；将查询参数/时间语义、认证字段前提、校验顺序、停止留存、Router汇合及分层证据建议融入正文。
3. 将原宽泛首批拆为结果一致与交接、查询有效性与真实场景、共享结构与扩展三批；新增有限验收材料，全部明确尚未执行。异常登录仅为满足数据前提后的候选。
4. 做文档链接/格式及增量核对，独立文档审阅结果另记audit；修订版本保留在上述本地目录。

本次无业务代码、API/DB合同、运行配置或部署修改，无新业务测试/模型/消息/生产访问。原5/15、v1已上线和旧质量失败保持；不归档，不Git提交/推送，保存方案不构成后续实施指令。

## 2026-10-22 两项目恢复实际结果（结束独审已完成）

attempt02于23:22执行：3条新合成输入经本地最小认证API发布独立raw topic，原Fusion方法实际落PG/首次快照并交付独立fused topic，各p0 offset0/1/2，共6消息/3Alert/new/无Case/关联Run0/模型0。未启动Fusion消费循环、无group/offset提交；隔离Redis前缀访问12键，临时本地API与客户端已停且cleanup_errors为空。原8离线＋2替身测试复用未重跑。初次本地材料观察误要求source_event_ids完全相同；核原worker追加上游Alert ID后修观察，失败保留，无业务修改或重发。8字段材料及答案分离核验通过。

产品建议只补后来v1已部署/生产worker已启、两例数据与留存缺口；不实施全部建议，不重复构建/发布。逐步回执见docs/operations/two-projects-resume-20261022.md；测试工具最终交付见docs/operations/testdata-tools-20261022.md及docs/handoff/testdata-tools-20261022.json。未参与实现者resumed_projects_end_audit结束独审限定ACCEPT、0项本轮必须修项；64链接/围栏/JSON/diff/OpenSpec strict通过，选定非私有版本与步骤日志留存.local/versions/two-projects-resume-20261022。原5/15、旧unknown/预算/失败保持，不归档。

## 2026-10-22 两个额度中断项目恢复（执行前登记）

用户要求继续两个暂停项目并逐步记录。沿原2.1/4.1恢复测试工具隔离小批量真实联测，最多3条新输入/独立topic/Redis前缀/测试tenant，0模型、无生产部署或开关修改；保留attempt01。产品建议已审，补v1最新事实并交付，不据此实施未选定方案。步骤、时间与结果见docs/operations/two-projects-resume-20261022.md和.local/versions/two-projects-resume-20261022/steps.jsonl。执行前restore strict通过；结束一次未参与实现者独审，原5/15和旧失败保持。

## 2026-10-22 用户授权两例真实测试与数据交接

正式v1新raw Kafka输入2条，自动关闭及自动调查分别实跑；新增21步骤事件/21工件，正文长度/hash、event关联及8回复31788tokens成本可核。用户随后要求做好表/数据盘点，22:56只读核生产租户25表428字段/约束及实际行数，23:09实际只读执行交接SQL9个SELECT成功。新增[数据盘点](../../../../docs/integration/v1/page-data-mapping.md)、字段/JSON/SQL、[两例回执](../../../../docs/operations/service-v1-functional-20261022.md)；完整逐步原文留存/质量不通过，原5/15保持。未改业务代码/模型配置/预算，不重放旧输入，不部署或Git提交。结束独审限定ACCEPT，范围为本轮测试及交接。

## 2026-10-22 v1.0.0实际发布结果

API/Agents已按固定候选ID定向替换，生产租户/最小身份/生产预算及新组起点就绪，worker与升级开启、模型摘要不变。新raw Kafka告警自动取得Run/partial graph/Markdown，15事件/14工件及提交offset/读取200可回查；7回复28216tokens，质量及原软预算限制保留。未重放旧输入、修改旧group/unknown/预算或启真实响应，未Git提交/推送。详见[发布回执](../../../../docs/operations/service-v1-release-20261022.md)。原5/15不改，结束独审另记。

## 2026-10-22 后端对接发布指引v1（文档增量）

用户要求面向后端的数据/功能对接文档，追加明确正式已有告警走Kafka、HTTP告警仅测试辅助，并要求Kafka/Redis/PG/OpenSearch/ClickHouse等配置，以及告警/调查每一步输入点、输出点、结论/读取入口。本批沿2.1/4.1交接，新增docs/integration/v1/的总指引、配置、Kafka、调查与数据表五篇，以及JSON/env/只读SQL示例，不新增产品任务树或业务行为。两只读研究代理分别核Kafka与表关系，root编写正式文档；结束由未参与编写者独审。

已读受控本地env中的白名单非密钥字段，仅输出地址/端口/库/用户名/CA路径等，不公开密码/token。21 SSH首次受沙箱拒绝后按工具授权重试仍超时；随后用户告知21恢复，已于16:02只读核15个容器的镜像/端口/连接env白名单并保存净化runtime-snapshot.json。湖192.168.1.21:9000/aisoc/socai2_lake、TI OpenSearch主机、TI/enrichment共享Redis DB12及实际worker关闭/升级0已回写；Agents enrichment仍指向禁用目标127.0.0.1:9，不把服务存在写成已接通。全程无业务接口/SQL/broker操作或秘密值输出。文档发布与实际服务发布分开，现有API/Fusion/Agents基线、本地候选未部署、worker OFF、旧质量/unknown及原5/15保持，无消息/模型/业务库写或Git提交推送。最终Raw/Fused合同及canonical/tenant、4JSON/86本地链接/1锚点/2shell语法、diff/OpenSpec strict通过；backend_v1_doc_audit结束独审及新增配置窄复核限定ACCEPT，回执见audit。发布阅读包为.local/releases/stingaisoc-backend-integration-v1-20261022.zip，包内manifest记录选定文档/示例hash，不含私有env或业务源码。

## 2026-10-22 两会话简单收尾与未完进展留存

用户本轮只要求简单收尾。已核「继续推进迁移」最后的测试数据工具增量：8项离线、API/Fusion各1项替身合同已有通过回执；真实attempt01在生成/联网前配置失败，日志配置已改但未重跑。真实联测/最终回执/增量结束独审待续，不勾任务。已找回另一会话产品工程建议最终237行版本的既有结束独审，当前SHA256与审阅回复一致，补记audit；方案仍只是建议。相关文件及非私有证据选择性保存在.local/versions/session-closeout-20261022，具体清单和续接见docs/handoff/session-closeout-20261022.md。

本轮不继续业务实施、联测/模型、消息/业务写或部署，不启worker、不Git提交推送；5/15、未完责任和旧失败保持。本记录不是测试数据增量或整体change的结束验收。

## 2026-10-22 智能调查产品与工程设计建议

用户要求从经验丰富的安全产品经理和开发工程师角度提出急需问题、智能体/调查优化及扩展。沿现有2.1/4.1文档交接补docs/architecture/investigation-product-engineering-roadmap-20261022.md，工程/产品代理只读提出建议，root编写正文。重点为范围与真实资料、证据/finding/报告、停止与交接四个共享合同；保留三编排、复用ToolRegistry/Strategy/customer_tools，定义场景扩展、行为链和人工补证的最小路线与指标。

明确优先级是后续产品化建议，不新增当前迁移前置或任务树，不改原5/15。现有两候选已本地构建、旧C2修正未随之发布；本轮未改业务源码/配置、运行模型或业务测试、消息/业务库/图写、Docker/21发布。外部两篇官方工程文章只作设计参考，现状依据仍为本地源码及已有回执。新增导航/AGENTS/PROGRESS；结束独审与文档核验另记audit。

## 2026-10-22 按标书原件评估迁移设计与后续路线

用户要求当前模块迁移/设计评价，随后明确以标书需求文件为依据。本轮沿2.1/4.1只做需求与证据交接，不改变业务规格/源码/运行，不另建产品任务树。核AI SOC2.docx与XML既有hash、正文/表格/三图，直接从原件生成35子组164功能细项矩阵；旧SOCAI覆盖状态未继承。新增docs/operations/tender-requirements-assessment-20261022.md及docs/requirements/socai2-requirements-matrix-20261022.md，评价UEBA/IOC/知识/Fusion/分诊/调查/链图/报告、范围外平台要求、SFT/RAG/证据/架构选型与P412六项成效。各行保原文、定位、有限判断、后续与证据链接。

未参与实现者migration_evidence_review只读核支撑/分诊源码，确认GET /alerts筛选/search和UEBA最近50条匹配的继承原版限制；只登记原upstream-issues，不以静态发现宣称已发生生产问题。收尾检测到共享仓库新增候选镜像回执，已纳入API5a1e1fd8/Agents49643b84本地构建/离线核验完成事实；后续改为阶段发布准备，不保留过时“尚未构建”待办。

实施前OpenSpec strict通过。原任务15项/5勾及R02保持；本轮无新业务测试/模型/HTTP/消息/图写/Docker/21部署，不重调旧Run。原需求、历史回执和其他进行中的本地改动保留；最终文档核验与未参与编写者独审另记audit。

## 2026-10-22 本地候选镜像构建与离线核验

用户继续并明确授权21两个完整内部父镜像→本项目本地目录。OrbStack启动恢复11既有本地容器，未改其配置；本地缺父镜像，经只读21检查/导出、载入后核精确ID及amd64，不上传源码。首次导出auto-review因缺payload明确授权拒绝且未执行，用户“授权”后才重试；旧拒绝/超时与失败记录保留。

helper执行暴露3个环境接缝：缺省Entrypoint模板错误、classic parent snapshot缺失、Buildx context绑定要求。只修helper可选字段读取及显式校验本地docker-driver单节点/Host、按context执行；无自动fallback/远程builder/pull/依赖重装，19源码/两Dockerfile/锁保持。成功API5a1e1fd8/Agents49643b84，本地父层和启动配置继承通过。镜像内各一次临时非root/只读/禁网Python探针，19源码hash/编译、7排除项、385/129导入与4方法正确，均exit0/stderr空并删除；不启动应用lifespan或worker，不重复100用例/模型。具体回执docs/operations/investigation-candidate-images-20261022.md及JSON；原5/15、旧C2/quality/unknown不改，未部署21/启其worker/提交Git。结束独审另记audit，不外推运行或业务质量。

## 2026-10-22 候选组合与最小构建准备

沿原B5→B6及2.1/3.1/3.4/4.1准备19文件候选。21只读核API/Agents实际父tag/容器ID，定向读取full bundle补hash并核UEBA AST/原五来源不变；没有创建/重启容器或上传业务源码。以核过的candidate05 API439/Agents188运行输入覆盖审查19文件，7项后置保持基线；隔离进程/禁网/清DB环境执行原直接合同，Agents55＋API45＝100 passed，导入树外0。完整router导入/OpenAPI确认4方法，385app模块均来自隔离树，无lifespan；两次检查脚本假设错误日志保留。

API7/Agents12最小context/manifest、显式COPY Dockerfile及默认只读本地助手已准备；本地Docker socket不存在，本轮未构建镜像、部署或启worker。只读SSH首次sandbox拒绝后受控成功，未改运行配置；0业务HTTP/PG/图写、Kafka、Case/Run或模型。原5/15、旧C2质量/unknown与未终审源码保持，不归档。详情与独审见docs/operations/investigation-candidate-build-20261022.md及机器摘要。

## 2026-10-22阶段责任收口与具体候选差异

用户确认按评估继续，root沿现有2.1/4.1、B5→B6整理10项未勾责任；b6_responsibility_closeout只读核原任务与既有回执，release_diff_inventory只读核运行文件来源。记录在docs/operations/investigation-stage-closeout-20261022.md及handoff同名JSON。2.1尾注更新为已累计交接/最终状态确认未完，checkbox仍5/15；completion-plan依赖批“联合尚未成功”明确是当时事实，保旧失败而指向后续成功。

以最新full发布记录为镜像参考；本地candidate05来源比较得到26项运行差异，API7/Agents19。选19项接线（API7/Agents12），另外7项旧C2/未关闭文案排除；fused worker没有混关闭文案。工作区Deep另含旧C2，root在独立.local/review/investigation-stage-closeout-20261022副本中以已匹配candidate05 manifest的原件只加Bundle摘要hunk；移除新增hunk即逐字还原父文件。其他18项与功能/链图/Kafka批最新来源匹配，四份服务声明/lock保持；原业务工作区不改、不删除旧C2。

新变体只复用一个现有直接用例，runner明确装载review副本Deep并阻socket/停OTEL，材料确实追加到user摘要：1 passed、两条pytest导入重写警告，另可选OTEL exporter提示保留。19文件语法解析、逐项来源/副本与原工作区保持、7项排除检查通过；不重跑85合同/模型矩阵，不称19文件整体集成已验。此目录无构建配方/凭据/业务HTTP材料，未造镜像或部署，不是发布包；pure full bundle hash本地缺证、最新运行态未重查及组合/构建审查等余项明确。

本次无新模型/后端HTTP/消息/业务PG/Neo4j、运行/依赖变更或Git提交推送，未复放旧Run/unknown；5/15、worker OFF及旧质量失败保持。root核相关450本地链接/机器清单、diff及OpenSpec strict通过；stage_closeout_audit结束独审限定ACCEPT、0项本轮阻塞，独立核420条不同文件集链接、26差异/19候选/7排除和任务映射。独审发现新导入生成pyc，root仅移除这一个派生缓存并给runner设sys.dont_write_bytecode=True，随后只读确认19物理源码/hash保持，不重跑用例；不扩大为旧C2、组合/构建或发布批准。

## 2026-10-22关联/链图模块评估与推进建议（未实施新行为）

用户要求评估当前模块并看后续路线。root结合module_value_assessment、roadmap_next_step_review两路只读核对，在docs/architecture/attack-chain-path.md第11节记录判断：当前具备相关告警检索、关系上下文及Run留痕，可沿B5→B6收口；不是跨Incident攻击活动/行为路径引擎。Fusion闲置链不是新接线阻塞，原样保留而不强接/默认删除；PG链和关系图按候选材料使用，复用已有真实调查与Kafka准备证据。

建议最近先对照既有责任、整理实际选入的API/Agents候选发布差异；旧C2未终审修改不能因整文件保版或链图局部独审自动获发布批准。下一轮跨事件关联先选少量业务模式及现有证据合同，自动建Case与行为图另作明确取舍；不扩大采集/模型矩阵或复杂可用性前置。当前仅评估/文档，不改变任务勾选、业务源码/配置、运行、消息/写库或发布，原5/15、worker OFF、质量失败保持。339个本地链接、新module-assessment锚点、围栏与diff检查通过；未参与编写者concept_docs_final_audit本轮只读复核限定ACCEPT、0文档阻塞，仅评估文档，不批准实施/发布或常驻启用。

## 2026-10-22链/图概念、例子与结论存档（仅文档）

用户要求把本轮讨论的关键概念、例子和结论全部保存。沿既有架构交接责任维护docs/architecture/attack-chain-path.md第6—10节，不新增产品任务或规格级行为变更；连接Fusion清单、docs导航、AGENTS及PROGRESS。范围包括Alert/Incident/Case/Run/两种Chain标识、真实生成顺序、两套归组四象限和P→A→B同Incident异链例、Chain内部维护/交付/留存与下游未消费、PG链锚点/跨Case窗口/扩展、Neo4j Path及Alert可达图、自动建Case与Playbook现状。

概念及边界来自当前源码；例子明确为规则推演，没有执行新业务样例。记录“Chain搜索相关告警、Path展开已有关系”，不把Path写成已完成行为因果；将事实、设计用途和未决定的取舍分开。没有决定删链、合并Incident/Case、改算法或自动建Case，没有改业务源码/配置、依赖、运行、数据库/消息或模型，没有部署/提交推送。原5/15及旧质量失败/worker OFF保持。变更前OpenSpec strict通过；正文写入后449个本地链接及5个显式锚点、代码围栏与diff检查通过。首个标题检查器把三级标题误计为二级，改为行首匹配后通过，没有为消除误报改正文。未参与编写者concept_docs_final_audit对照本轮前备份及关键源码做结束只读独审，限定ACCEPT、0文档阻塞；不扩大为业务验收，不归档。

## 2026-10-22 Kafka入口真实联合观察

用户要求依赖补齐后继续推进，复用前述规格/设计/已审探针，在Conda环境本地运行原worker.start及只挂graph原路由的API，连接21 Kafka/PG/Neo4j。probe run66a9387b708a，Alert2365c4b6-58f2-4b9c-9610-2c0bf0ec62d1，独立topic/group发一条消息(partition0/offset0)。真实JWT/PG权限和独立七RO reader、原LiveShadowModePolicy保持；writer仅本地5分钟JWT，未建21 key或改常驻review-only。

schema后原prepare真实HTTP200 success，canonical/tenant/source_alert_ids一致；在triage观察接缝取内部回执并直读Neo4j，当前Alert直接邻域5节点4边且所有边source_alert_id匹配；Technique可复用全局标签，不能写全库新增5节点。readerPOST403、writerPOST200、readerGET200；GET PG chain empty、Alert图success、CasePath not_linked。原blast_radius另返14可达候选，含同tenant历史测试Alert/Case；不作本案确认影响，问题沿原清单后置、不改算法。

观察入口主动BudgetHold，原循环以预期LedgerPersistError结束、不重试/DLQ/commit，不进入业务triage/模型；Alert仍new、无Case、确定性调查Run0，新group committed offset None，本地进程已停且端口无listener。本次不重跑Fusion或85项已通过合同、不发布或改业务源码/锁文件。模型/调查/常驻完整性不由该接缝替代，5/15、旧质量失败保持。

失败保留：attempt1沙箱连接被拒无业务写；attempt2缺greenlet停在API拒写检查，已留1条PG合成Alert、未建topic/发消息；原attempt3许可被用户中断未执行，依赖补齐后同名新目录首次执行本次观察。累计2条合成PG夹具、1个隔离topic/group、1条消息，不把旧失败擦除或只报1条PG写。原始非凭据证据与公共回执见docs/operations/kafka-graph-joint-20261022.md和对应handoff.json。未参与实现者joint_graph_audit结束独审限定ACCEPT、0接线阻塞；本地15份选定探针/依赖/真实证据保存在.local/versions/kafka-graph-joint-20261022，root核原件/副本/归档一致，排除凭据映射及私有配置；非独立环境、镜像或整包发布验收。OpenSpec strict、diff及Fusion/服务依赖锁未改检查通过。

## 2026-10-22先统一补齐本地Conda依赖

用户要求暂停联合补验，先检查依赖并一次装齐。新增deploy/aisoc21/check_local_dependencies.py同时核API/Agents runtime、dev及必需extras，56唯一直接项，原缺21项/6项版本不符/fastembed extra；原pip check通过不代表声明齐全。先解析后统一安装90项Python包及37项Conda包（含动态库/字体/证书），仅项目.local/conda-envs/socai2，Python3.12.14不变。清理克隆旧SOCAI editable仅新env的入口/元数据，不删旧源码/环境。初次pip冲突输出保留。

两服务25个共享包锁版本不同，本地统一解析，不修改pyproject/lock；PyJWT取API2.15.1。结束只读审查指出SQLAlchemyInstrumentor只支持<2.1，初批锁2.1.4使其跳过；保留初批90项证据，只本地清单覆盖为两服务均允许的2.0.52，再核实际instrumentor启用。最终56直接及传递extras缺口0、精确pin偏离0、pip check无冲突；API33/Agents32离线检查通过（阻网、只导入不进lifespan），SQLA异步内存查询、native内存渲染与Conda激活加载通过。依赖最后调整后已有直接合同71+14=85 passed，不将初批重复结果累加；弃用警告保持。

本轮只环境/检查辅助代码/回执，无业务源码或生产锁修改、模型、Kafka消息、应用lifespan、21部署/常驻启用或Git提交推送。此前联合attempt1连接被沙箱拒；attempt2已留1条合成PG Alert、缺greenlet停在API拒写检查前后，未创建topic/发布消息、子进程已停；attempt3许可被用户中断未执行，未改写成通过。最终机器/文字回执见docs/handoff/local-dependencies-20261022.json和docs/operations/local-dependencies-20261022.md，5/15保持；未参与实现者dependency_final_audit结束独审限定ACCEPT、0剩余阻塞。16份本地选定源码/清单/版本/日志保存在.local/versions/local-dependencies-20261022，root核原件/副本/归档一致；不是完整环境或发布包。

## 2026-10-22 Kafka消费入口统一准备图

用户明确选择Agents读fused Kafka后写图，避免修改Fusion；随后要求使用Conda创建项目环境。先补proposal/design/tasks/spec并strict通过，再实施4个生产文件的必要接线：schema后/原triage前prepare，独立writer及profile/shadow保护；每delivery一次、内部重试共享ContextVar回执，build_state只取匹配tenant/canonical的内部回执；上下文GET-only及Bundle/原Run工件采用。API显式Alert仅投当前已核告警，真实Case仅补成员边，修正Case前50截断会漏当前Alert的接缝。Fusion源码不变，Case人工入口与原算法/编排/模型调用数保持。

源码只读审查先发现新shadow检查从build_state求类会漏category，root改为原message.alert类别并补类别敏感例；新入口回执匹配按UUID规范比较，原ID/Run合同保持。新增用例由kafka_graph_tests实现，生产及已有合同更新由root实现；结束独审由未参与实现者kafka_graph_audit进行，不以设计建议或测试作者代替独审。

环境：原/tmp venv已不存在；conda socai缺respx及部分直接依赖，早期收集失败0测试执行。用户要求Conda后创建.local/conda-envs/socai2（克隆现有socai，源环境不改），补本批直接测试依赖；离线clone缺缓存与公网下载超时均保留为环境准备过程，不记产品失败或测试通过。最终Conda Python3.12.14运行新入口24＋已有Agents三文件47＋API14=85 passed（不同文件、无重叠）。日志及环境版本在.local/aisoc21/kafka-graph-intake-20261022，本地版本在.local/versions/kafka-graph-intake-20261022。

本批全部业务HTTP/PG/图驱动按测试替身执行；无新真实broker/业务PG/Neo4j访问、模型、正式消息、旧Run/unknown重放、部署/重启或Git提交推送，不把昨日真图/模型证据移为新Kafka入口真实联合验收。worker OFF、5/15、旧质量失败与C2未终审范围保持。独审/本地版本核验最终结果见本段后补及audit；具体用法/数据/范围见docs/operations/kafka-graph-intake-20261022.md。

收尾：16份本地增量原件/副本/归档及manifest一致；468个本地链接存在、OpenSpec strict、diff和Fusion源码未改检查通过。未参与实现者kafka_graph_audit独立核三组85 passed日志、源码/保护/范围及版本，限定ACCEPT、0项剩余阻塞；未重跑模型或业务。元数据结论已同步JSON/版本manifest，不把本批局部完成勾为完整任务，不归档。

## 2026-10-22阶段交接与本地保版

沿既有B5→B6、2.1/4.1推进。两路只读核对确认链图已经本地实施/独审，当前基本主链不需要重复模型或新业务查询；补docs/operations/investigation-stage-handoff-20261022.md及机器摘要，映射已有功能→具体Run/回执→读取出口→版本/限制。纠正AGENTS/completion-plan/docs导航“仅规划/下一项”的过时现时表述，OpenSpec入口同步实际5/15；不改原任务勾选和旧失败。

链图最终选定源码、直接测试、依赖声明/lock和原回执保存在.local/versions/attack-chain-path-20261022，逐文件manifest与归档副本核对；不含私有环境或HTTP观察。选定文件依赖Git基线，其整文件可能含既有修改，不是完整源码、部署镜像或已审发布包。此前C2 graph/deep质量修正仍未终审/未部署；已部署I2正常完成/usage保护与其区别列明。

本轮无业务代码/运行变更、新业务测试/HTTP/消息/模型、部署/重启或Git提交推送；不实施假设厂商Tool，不触碰unknown/积压。仅核本地版本与文档/规格结构，随后做一次未参与实现者阶段独审；实际结果补于本段，不提前标验收。当前change5/15、不归档，常驻worker OFF、旧质量失败保持。

本地核验：36份选定文件原件/副本/归档内容及归档hash一致；10份本轮相关入口/交接文档的518个本地链接存在、7个证据回执可读；原链图usage算术及5/15复核正确。首个检查器未解码既有AI%20SOC2.docx链接而误报缺失，补URL解码后通过，未删改原文档以掩盖问题。OpenSpec strict和git diff --check通过；这些是保版/文档检查，不作新业务测试或质量通过计数。

未参与实现者stage_handoff_audit结束独审限定ACCEPT、0剩余阻塞；独立复核36份原件/副本/归档及manifest、Git基线、证据/版本/未完成边界、无私有配置/HTTP观察及高信号凭据，链接0缺失、diff检查通过。审查指出docs/README两处旧现时口径，root修为2026-10-22阶段交接及明确历史后获只读确认。root上段518为修订前检查时的文件集计数，独审另按自己的文件集检查，不混称复现相同总数。无业务测试、网络/模型或部署；本次不代替完整change结束独审/归档或旧C2发布审查。

## 2026-10-21外部HTTP接口与Tool执行验证设计（未实施）

用户要求检索合同设计后澄清：重点是厂商已有HTTP查询接口及自定义Tool的接入/执行证明。交付docs/architecture/third-party-search-contract.md并连接导航、Tool指南和SIEM说明。内部UnifiedQuery由adapter转换既有GET/POST，字段/算子按真实能力收窄，不要求厂商新增统一API。给出精确主机请求、参数/时间/认证映射、响应数组/标准字段及空/失败/截断边界；新Tool仅用不存在的vendor_host_events举例，SIEM同业务优先复用原工具。

验证方法区分手工HTTP合同、registry直接执行、脚本模型→真实包装器/HTTP→下一轮匹配ToolMessage，以及按需一次真实模型选择。没有实现或运行这些步骤，不把假模型当真实选择；当前call id不自动传HTTP、event.id/上游截断元数据不自动透传的接缝明确保留。仅设计文件6个JSON解析、12处本地文件引用、两Unix毫秒时间换算、OpenSpec strict及diff检查通过。未参与编写者deep_functional_tests只读结束独审ACCEPT。无业务源码/配置/新接口/替身服务/功能测试/HTTP/模型/部署，不新增产品任务或勾选，原5/15及worker OFF保持；后续实施先补必要规格/任务。

## 2026-10-21Tool使用说明与假设SIEM接入

用户要求列清Tool设计、执行、配置、测试，并追问未提供真实实例的第三方SIEM如何接入，以及Elastic/Sentinel是否接收SQL。本轮仅文档，沿2.1/4.1维护交接，不新增产品规格/任务或勾选；无业务源码、运行配置、依赖和部署修改。

新增docs/operations/investigation-tools.md、docs/architecture/investigation-tool-catalog.md、docs/operations/siem-tool-integration.md，连接文档导航和配置索引。目录区分16内置（7事件查询、4占位、5基础）、条件customer与MCP；指南说明schema/模型tool_calls/registry/HTTP/ToolMessage及逐步读取。SIEM写明tenant PG配置、凭据与非秘密配置、缺失独立查询服务、字段映射及四层最少验证；Elastic/Sentinel例子按固定源码静态推导统一条件→ES|QL/KQL→认证/HTTP→表格展平，自研后端可直接映射JSON。没有真实SIEM、没有执行示例；Sentinel scope/workspace/固定表字段等限制保留，不包装成现有可用或新修复。

仅必要订正旧预处理文档：Case携case_id及可选preparation、Router条件Bundle、Deep有界摘要和认证查询缺事件类别过滤；旧回执/模型失败不改写。三新文档12个JSON解析、5段shell的bash -n、92处本地文件引用通过；首版引用检查器未识别:行号后缀，更正检查器后通过，未误删源码链接。OpenSpec strict、git diff --check通过。结束独审ACCEPT，具体见audit；不用本轮文档校验代称业务测试通过。原5/15保持，worker OFF、不归档、不发布、不Git提交/推送。

## 2026-10-21链/图本地实施回执

用户本地实施授权已执行，实际改动与逐步输入输出见[本批完整案例](../../../../docs/operations/attack-chain-path-local-20261021.md)，配置/接口见[模块用法](../../../../docs/architecture/attack-chain-path.md)。原算法和三种编排保留；新Case真Neo4j11节点15边，原链5候选（含其他Case同tenant共享IP候选），4次真实输入同一摘要、三链图工件及Markdown持久读回一致；29事件/4工件，18388tokens。第一条Run因新增来源被原3.5秒Bundle截止取消，链图消费失败，4回复13941tokens保原；仅新source给22秒截止，保其他源3.5秒，另冻全新输入4调用复验，本批累计8请求/8回复32329tokens，无更多模型。不是对旧失败输入重试或报告润色。

必要直接验证API109 passed/7原livePG skipped；Agents兼容120 passed后新增2项修正用例通过，最终相关context/orchestration22 passed（重叠不累加）。无发布、21容器重启、worker/正式Kafka、旧unknown/积压或厂商动作；不提交Git。未参与实现者deep_functional_tests结束独审限定ACCEPT、0阻塞。本批只完成2.1/3.1/3.4/4.1链图责任部分，原5/15不提前勾选、change不归档。下文“最多4次”是第一条观察预算，发现正常接线阻塞后按本段扩为两个全新Case各4次并保旧证据；其他历史仅规划段保留。

## 2026-10-21链/图接入开始实施（本地，不发布）

用户已明确按既定计划实施、保原算法/流程，本地测通后用一个完整新告警案例解释逐步输入/输出/读取，复杂可用性后置，暂不发布。本次授权覆盖此前“仅规划”限制；原任务2.1/3.1/3.4/4.1记录本批成果，不预先勾完整任务或归档。

必要接口接缝具体化：除计划中的Alert薄链入口，沿graph路由增GET investigation-context读取同tenant链/图资料，增POST同路径仅作有权限的确定性定向投影；复用原算法/upsert/查询，无新表或通用框架。Case调查POST在可信API内投影后启动原编排；自动Alert可用单独配置的tenant写入凭据调用受限prepare，模型及永久七权限只读身份不获写权限。读取与写入凭据分开，缺写凭据明确未投影/回退，不借GET隐式写Neo4j。新接线以AISOC_ATTACK_CONTEXT_ENABLED显式开启，本地开启、现21常驻配置保持。

API返回统一的有界attack_context：明确Case/Alert锚点、原链、CasePath或Alert邻居/影响范围、source/status/error/查询范围；Agents Bundle显式采用，默认/Router/Deep原模型调用不增加固定步骤，按Run保存attack_chain/attack_path（Alert图另型）工件及实际摘要。真实验证只用本批新Case/三告警和必要控制，优先跑默认四节点一个完整案例，最多4次模型请求、每次completion2048/SDK retry0/45秒；失败不自动重试。必要直接测试覆盖其他消费接缝，不跑三套模型矩阵。旧失败/unknown、算法、预算、工作者开关与正式topic保持，无部署/Git提交推送/厂商动作。

规划收尾（2026-10-21）：deep_functional_tests未参与链图计划编写，仅读规划/相关源码做一次限定独审，ACCEPT、0阻塞；核Case/Alert分型、原算法/对称时间窗、可信投影来源、不可信材料及模型/Run交接与待实施状态。strict、本地链接及diff检查通过；0新业务实现、配置/图写/模型/功能测试/部署，5/15保持，不归档。

## 最新规划：攻击链/Attack Path接入调查（2026-10-21）

用户本轮要求规划，并询问是否只是既有功能未开启。已核原算法/查询/图写入函数和配置都有，但固定原版及当前Case/告警业务均未自动调用图投影；Router/Deep与Case路径材料也未完整交接。不是只翻开关，也不是迁移时删掉已有自动图逻辑。详细实施顺序与最少验证见[专项计划](../../../../docs/operations/attack-chain-path-integration-plan.md)。

沿原2.1/3.1/3.4/4.1及B5：先已有Case/同tenant输入与可信PG材料，调查准备阶段定向复用upsert补图，原Attack Chain/Path预取一次，有界摘要进入默认/Router/Deep实际模型消息，原G4复用材料；按Run事件/工件与Markdown交付。不合并编排、不改链评分/时间默认、不新建raw采集或图平台，不新增固定模型调用。直接缺口只修Case/Alert/tenant交接、当前投影的节点/边ID和来源状态合同。模型不可写图，原写接口权限不扩大。

本批先Case调查，再接自动Alert起点：无Case或Case关联有歧义时，候选链通过计划中的薄Alert读取入口调用原seed算法，图上下文复用已有Alert邻居/影响范围；Case专用路径明确not_linked，不伪造Case/改写旧Run。薄入口是本次明确的必要接线增量，不称已有开关。计划规定代表三告警Case、原直接测试、一个代表真实模型消费及按Run读取；复杂恢复/冗余/压力、全库回填及模型质量矩阵后置。

**当前仅规划和只读源码核对**，未改业务代码、开关、写数据库/图、发模型或部署；原5/15不变，不创建另一套产品任务树、不归档未完成change。此前78项和31995tokens是上批实测，不能用于追认本计划实现。

## 本批实测结果（2026-10-21）

用户同意各类案例来源后，本地按原机制完成四个新Run/三路径观察：78项直接测试（Router12、Deep8、认证API51、单IOC7）通过；14次模型尝试收到13回复、已知31995tokens，Forensic一次OpenAIConnectionError没有回复，不能把其执行/usage写为0。Router实验输入提前关闭，独立公开事件叙述选择Identity/Cloud后完成模板MD；默认四Agent交付带Forensic兜底MD；Deep六轮执行7工具，21540/20000预算停止、narrative空。不是三套质量/整链均通过，不用原completed/reached_depth标签代验。

真实定位两原版接口合同，依前置strict校验后仅修API IPv6非空过滤与Agents单IOC字段；局部测试及本地原函数借21真实只读API/增强验证通过，未部署。另UEBA失效连接/Forensic连接错误、原IOC regex、Router缺证/Deep空结果及软预算/原占位能力登记后置，无恢复/模型矩阵。源码与原结果保留；自动审批拒绝lake.env导出未执行，改现有只读API验证成功。

公开逐步回执见[实测说明](../../../../docs/operations/investigation-functional-20261021.md)及[机器摘要](../../../../docs/handoff/investigation-functional-20261021.json)，原2.1/3.1/3.3/3.4/4.1只记部分成果，5/15不变。全部组件无DB DSN，只保存本地工件，不创建线上Case/Run、不代验Kafka触发/PG持久。没有部署、Git提交/推送、常驻启用、旧unknown/输入重放或厂商响应动作。未参与源码/报告实现的case_source_review结束独审ACCEPT，核原调用、tool_call_id、计数、边界及无公开凭据/非空隐藏推理，0阻塞、未追加模型/业务SQL。本地13文件增量快照（Git基线/hash，无凭据）已实际保存于.local/versions/investigation-functional-20261021/，不是完整镜像。

本批默认调查另真实复现单项IOC增强HTTP400：Agents发送type，原Go服务要求ioc_type。沿3.1同批只修这一请求字段（保原工具签名/返回/固定增强流程），复用已有直接工具测试并以一个保留文档域名经现有无provider服务验证HTTP合同；不重跑模型、不改IOC提取算法、默认端口或开启厂商来源。原400及报告保持，单项/批量增强分别记录。

### 本地实测发现的最小功能修正

本批Deep真实请求已穿过认证/API到ClickHouse；authentication_events原SQL以IPv6列source_ip比较空字符串，真实query_log确认CANNOT_PARSE_IPV6。沿3.1/4.1仅修该参数化查询与IPv6空值合同，复用原直接测试并追加该SQL回归；不改表/算法/占位后端、不部署。模型旧结果不重调，本地原查询函数借21已有只读湖仓验证一次新查询；其余缺源/预算和质量问题记录后置。

## 最新增量：调查模块本地功能实测（2026-10-21）

用户已要求开始测试，并同意真实部署样例、公开案例和新隔离样例均可使用。本增量覆盖此前“仅文档/不发模型”的阶段限制，沿原2.1/3.3/3.4/4.1记录，不新增产品任务树或预先勾完成。先复用Router 12项及Deep 8项直接测试，再本地运行原默认四节点、Router与Deep各一次，使用21既有模型网关及只读查询服务，保存各步真实可见输入/输出、工具请求/返回、usage与Markdown；不把替身测试当真实模型/工具证明。

20仅有已调查的Golden pipeline样例，本次只作历史对照，不重调。公开事件只取官方叙述事实，测试实体/字段明确标为派生或合成，不伪称原始日志。三种路径先用三条新输入；Router首例因明确lab来源在分诊即关闭，另加一次独立公开事件叙述以观察领域分支，四个新Run累计最多16次模型回复，每次completion沿原2048上限，SDK测试进程显式retry=0/timeout=45秒，Deep沿原6轮/120秒及20k预算接缝；累计观察usage达60k即不开始后续路径。所有执行逐路径串行，不为得到预期答案重调。无DATABASE_URL的本地组件测试只保存本地工件，不声称新增生产Case/Run持久或Kafka自动触发已验；原主链证据另引用。

不改常驻worker、部署、正式topic或旧unknown/积压，不做厂商动作、全链恢复/可用性矩阵、PDF/HTML专项。仅准备一次性观察脚本，不改变业务源码；如发生当前主功能阻塞，按原change先记录最小差异再修。结束做一次未参与实现者审计，保留本地版本，按阶段发布，不自动提交/推送Git。

# 迁移实施记录

## 预处理、逐模型输入输出和工具执行文档（2026-10-21）

按用户要求写明预处理怎样做、模型如何判断并请求工具及后端怎样执行，随后补充“每次调用目的、输入、输出”，新增[专篇](../../../../docs/architecture/investigation-preprocessing-tools.md)，连回调查说明、评价及文档导航。逐模型覆盖Router分诊/四领域、默认人工四节点、Deep每轮；工具部分区分代码固定预取与结构化tool_calls，给schema→调用→HTTP身份/固定查询→ToolResult→ToolMessage的静态示意，示例不是新实测。

只读核到Case发嵌套alerts、Router未flatten/预取Bundle，模型字段投影与实际可见材料不能混同；registry没有完整JSON-schema运行时验证，认证工具函数默认168小时而shared hours描述24。已按真实源码记录/更正文档并登记，未改输入映射、函数、配置或新建验证框架。沿2.1/4.1部分交付，原15任务及5/15不变；本次0业务测试/模型/线上操作/部署，不重调旧样例，不归档/提交。

收尾：strict/diff及10份文档477个本地文件引用、专篇6个JSON示例语法校验通过。未参与编辑的router_docs_review完成一次定向结束独审ACCEPT，目的/输入/输出与采用、路由/工具/结果区别、嵌套材料、参数/身份及静态示例边界准确，无需更正或追加业务验证。

## Router与调查方式讨论结论同步（2026-10-21）

用户随后询问官方何时推荐启用及相对四节点的优势，已在设计评价补原T2.2目标、两个独立开关及证据边界：生产待eval通过再开的是Router内部并行，不是Case选择Router的官方统一准入条件；mock/sleep并行提速只与Router顺序参考比较，不能代证旧四节点对比或模型质量。本次只读/文档，不运行基准或增设本轮测试前置，不更改配置/任务。

该说明增量strict/diff检查通过，未参与文档编辑的router_official_guidance一次定向结束复核ACCEPT；官方建议、比较对象及工程判断的区分准确，无需更正或新增验证。

按用户要求将刚刚讨论的说明写入[调查调用说明第5节](../../../../docs/architecture/investigation.md#5-router及full-graph的差异)及[设计评价](../../../../docs/architecture/investigation-design-review.md)，同步模块计划、AGENTS/PROGRESS及本change设计。内容包括：默认四节点/graph-deep/Router三者关系；无明确旧链弃用计划；Case `/investigate`开关二选一而非串跑，且不影响Kafka graph/deep；专业分支每个一次领域模型而非内部四节点；响应仅摘要、报告由renderer生成；graph外层固定、deep仅在受限工具内选择补查。

本增量仅文档，没有更改源码、开关、规格级行为或既有任务，不增加业务测试/模型/部署，不创建重复change。原R01/C2失败、运行OFF和未部署修正边界保持；原15任务及5/15不变。OpenSpec strict、diff空白及7份文档286个本地文件引用校验通过；未参与编辑的router_docs_review完成一次定向结束独审，结论ACCEPT，新增源码引用/锚点及上述解释准确，无需更正或追加业务验证。不归档、不自动Git提交/推送。

## 分诊规划、调查逐调用及设计评价（2026-10-21）

用户同意Fusion后继续下一模块，先规划并以同样方式分析；追加要求调查每步/每次Agent调用详细说明，并强调自动与默认人工调查的目的、输出、设计依据和四Agent客观评价。已形成[分诊工作卡](../../../../docs/architecture/triage.md)、[调查逐调用说明](../../../../docs/architecture/investigation.md)、[设计评价](../../../../docs/architecture/investigation-design-review.md)，同步路线/AGENTS/PROGRESS及本change设计/任务上下文。沿原2.1/4.1部分交接及3.3/3.4准备，原15任务与5/15保持，不新建重复任务树。

并行只读核分诊规则/关闭与升级、人工四节点、graph/router/deep/ledger及固定上游官方历史，复用原C2工件复原六轮工具选择，不新查线上或发送模型。明确默认Case四节点与graph/deep产物侧重、graph可手动发起、四Agent不等于独立复核；官方路线/变更日志支持多代演进并存，不足以证明严格互补双架构。记录route_to字段消费、单项IOC增强字段、Router bundle及审计持久边界，未擅自修复/合并/裁剪。旧人工R01/C2质量失败、工作区修正未部署及当前worker OFF保持。

本轮0业务源码/功能测试/模型/消息/部署，仅读源码和既有回执、编辑文档；OpenSpec strict、diff空白及3新文档67个本地引用检查通过。未参与文档实现的api_auth_review完成结束独审，指出explain参数应为step而非seq，已按API定义修正；其余分析/规划与证据边界接受，无需新增业务验证。triage_review此前的字段上限、写回/groundedness顺序及审计更正已采纳，最终因模型capacity未返回，不据此冒称其正式accept；本轮结束结论以api_auth_review为准。原产品任务不勾、不归档/提交，下一步共同取舍后只做直接差异，本地验证、保留版本、按阶段发布。

## Fusion阶段总结与后续判断（2026-10-21）

按用户要求复用已有证据总结：B1/2A身份、独立告警、关联和PG/fused交付，2B实体风险、2C本地历史IOC，以及最新UEBA本地原服务＋21真实基础设施5例联合，足以继续下游分诊输入与接线分析。当前没有阻断已有告警主链交接的已知Fusion问题，不将外部来源、候选链/标签/固定算法取舍、声明未实现参数或复杂可用性追加为下一模块前置。[总结](../../../../docs/architecture/fusion.md#六当前阶段小结可以转入下游分诊)已区分已验、原样保留及未启用/未验；总计划及现有问题登记同步，下一模块先理解分诊输入/规则/模型/关闭升级和逐步审计。

api_auth_review独立复核推进判断，结论可继续，无本轮必须阻塞项；明确21关闭的是Fusion UEBA融合而非UEBA服务，候选链不证明因果，旧质量失败保持。本次只作阶段记录，0新测试/模型/业务源码/部署；不宣称全功能或上线准入，不勾完整change任务、不归档，按本地验证、阶段统一发布原则继续。

## 本地源码与21基础设施真实联合验证（2026-10-21）

用户明确“联合验证”，随后要求本地先测、借用21基础设施，保留本地版本/必要时镜像，按阶段统一发布而非逐更新部署。本批运行1c84658ebb88：本地原BaselineService给3个唯一实体各录30次80/120样本，真实PG count30/mean100/std20.3419；原UEBA Kafka消费者实际消费171/192/232并保存/发布3.4903 medium、4.5227 high、6.4891 critical。原Fusion实际消费异常并缓存于21 Redis，后续5个新告警经真实PG/消息核对：基准0.656/0.15，medium0.726/0.45、high0.796/0.75、critical0.856/1，OFF控制回0.656/0.15；priority1/risk0.5、PG severity high/status new保持。各基线最终count31。基线准备不是90条Kafka学习，不以手写异常代替原服务输出。

仅新建5个本批topic与3个本批group（初始化至0只针对新group），不使用正式topic/group；本地禁不相关RBA/chain/prior/enrichment以隔离UEBA，raw支路仍后置。两个本地进程已停止，合成数据保留，0模型/源码上传/21业务实例重建；常驻开关false及旧unknown/积压未动。原18项替身测试保留，各自证明范围不混写。直接脚本、消息坐标和真实PG关系见[联合回执](../../../../docs/handoff/ueba-fusion-joint-20261021.json)及[UEBA第5节](../../../../docs/architecture/ueba.md#5-本地真实联合验证异常带来了什么改变)。沿2.1/4.1部分交付，不勾完整任务或归档；发布留阶段收尾。

本批唯一结束独审由未参与probe/文档实现的api_auth_review读取实际回执完成，结论ACCEPT：基线准备与真实消费分别表述、source/event/anomaly/alert对应及5个分数对照相符，无本批功能阻塞；不重跑测试。strict/diff/本地链接检查通过。本地版本保存在Git忽略的`.local/versions/ueba-fusion-20261021-1c84658ebb88/`，不自动提交或发布21。

## UEBA/Fusion联动评分例子（2026-10-21）

按用户最新授权完成8个联动例子，复用原10项信号测试，共18 passed（0.34秒）。新用例走原worker异常消息分支→原cache→原worker告警主链/Engine去重关联、启发式和置信度→内存保存/发布；复用B1 MemoryRedis/MemorySink，未改业务源码或原测试。关闭及无匹配不加分；medium/high/critical在基础confidence0.656上分别得0.726/0.796/0.856；多实体只取最高，跨tenant/实体不误用，priority及上游risk/身份保持。实际行结果、环境版本和限制见[回执](../../../../docs/handoff/ueba-fusion-examples-20261021.json)，配置/加分/应用方法见[UEBA第4节](../../../../docs/architecture/ueba.md#4-ueba与fusion联动评分开关及实测例子)。

原上传源码至21隔离容器方案被自动审批以私有源码跨主机传输拒绝，未执行；转本地临时venv安装公开依赖。首次新增用例因辅助夹具绝对导入错误而收集失败，改为相对导入后18项通过，原日志保留；23条原utcnow弃用警告未扩修。无真实broker/PG/Redis业务连接、模型、业务消息、21运行变更；常驻开关仍false。未重验UEBA基线生成、过期/恢复或完整调查，沿原2.1/4.1部分交付，不勾完整产品任务、不归档。

本批由未参与用例及文档实现的api_auth_review完成唯一结束独审，结论ACCEPT：实际处理链、分数、替身边界、配置和未启用事实相符，无本批阻塞；未重跑测试。OpenSpec strict、diff空白和本地引用检查通过，不追认完整change完成。

## raw规范化事件处理交由其他模块（2026-10-21）

用户明确raw处理暂不开展，由其他模块负责。本轮从已有告警进入Fusion继续分析，不展开规范化事件生产/规范化、入湖、事件检测/提升或派生会话/AI资产；`RawAlert`、`alerts.raw`及告警`raw_event`正文仍是当前输入。历史事件检索/调查补查及UEBA结果读取仍保留，消费其他模块提供的数据。本次仅在既有2.1/4.1下澄清职责并同步范围/模块说明，原源码、配置、测试和full实测不改；没有运行停用、业务合同变更或新增功能交付，不新增任务树、不勾产品任务、不归档本change。

## Fusion先理解再取舍（2026-10-21）

用户先要求下一模块规划，随后澄清主要是弄明白Fusion到底做什么，再共同讨论要/不要的功能。已复用现有源码分析、B1及full证据形成[功能说明](../../../../docs/architecture/fusion.md)：已有告警的身份/去重/关联/增强/评分/候选链/RBA/交付，规范化事件的入湖/提升/检测/规则上下文/session/AI资产，以及原辅助接口；明确各类分数、关联组、候选链与Case/Run区别，附一条告警流程实例。

当前只整理理解材料，不预定修复/启用/裁剪方案，不改源码/部署/开关，不发模型、业务消息或运行测试。原已知问题继续在既有登记，B1/full证据不重跑；只沿2.1/4.1更新，未勾完整任务或归档/提交。

功能说明由未参与文档实现的api_auth_review核对，结论ACCEPT；OpenSpec strict和本地引用检查通过。仅确认功能解释与源码边界相符，不是功能取舍或新运行验收。

## 依赖简明用法：TI/IOC与KB（2026-10-21）

按用户“保持原设计、功能能用、说明如何使用”的口径继续推进，沿2.1/4.1补[简明使用说明](../../../../docs/operations/dependency-usage.md)：原TI按值精确查询、API租户IOC列表/Feed浏览、原信誉增强与仅PG检索KB（synthesise=false、recall_memory=false）。复用full已有运行及测试证据，没有重跑测试/模型/质量或可用性专项。本轮无规格级行为变化，不新增spec或产品任务。

一次SSH只读20原项目元数据：`/home/lychee/beenuar`的api/postgres/qdrant服务找到；PG `aisoc_kb_documents`表存在、has_documents=false；ATT&CK两集合、TI IOC两集合/actor集合及语义记忆集合存在。只确认位置/存在状态，未查正文或复测向量内容，不导入21、不嵌入、不改服务。原TI search无tenant过滤边界登记，未新开放入口/新增私有数据，不能称跨租户泄露已复现或隔离已验。用法交接完成后下一模块为Fusion，整体2.1及change仍未完，不归档或自动提交。

本增量由未参与文档实现的api_auth_review核用法，修正Go响应字段名为risk_score后其余ACCEPT；OpenSpec strict及文档引用检查通过，无新功能测试。原整体任务完成状态不变。

## 依赖交接范围进一步简化（2026-10-21）

按用户最新要求，依赖项保持原设计，基本可用并说明功能及使用方式即可；只补必要接线，复用现有UEBA说明和有效证据，不继续扩展原理/源码分析、算法改造及复杂测试。深入工作留待二开，原代码/测试保留，非阻塞问题登记。已同步项目约定、总计划和本change设计；本次仅范围澄清，未新增产品任务、实现、测试、部署或完成勾选。

## 当前增量：UEBA上游触发合同（2026-10-21）

用户要求继续按OpenSpec逐模块推进，并明确只围绕功能接通、原测试保留/复用，复杂可用性与冗余问题登记后置。随后澄清UEBA按原设计由上游选择投喂，当前只需学清“什么格式发送会纳入计算”，不新增实体名单或真正滑动窗口。本批沿2.1/4.1更新proposal/design及UEBA合同场景，strict通过后只做代表输入核对。

[UEBA模块说明](../../../../docs/architecture/ueba.md)已包含配置与实体选择、normalized/预提取/HTTP三个JSON、来源字段差异、基线/异常及下游交接、简单偏离算法。当前共享`socai2.raw_events.v1`推荐normalized信封；预提取是原UEBA兼容合同，但不满足同topic Fusion的ocsf_event校验，不能作共享消息推荐。上游数据接入决定提供哪些观测，UEBA无单独登记启用步骤。

直接核对仅3 JSON语法、原extract对2个Kafka示例：normalized选user:alice，提取hour8/day2/is_failure0/bytes_sent1024；预提取取得login_count3/bytes_sent1024，两者event_id均正确投影为内部source_event_id。未写新测试文件或跑测试套件，复用full原122+7及已有Kafka/HTTP基线与Agents读取证据。0新HTTP/Kafka/PG/模型/部署，未改业务源码、topic、实体策略、算法或运行开关。真实异常→Fusion加分仍未证，旧unknown/积压/质量失败及workerOFF保持；部分说明完成不勾整项2.1或归档总change。

本增量结束独审：未参与实现的api_auth_review给出ACCEPT，核输入合同、字段差异、样本不足与累计窗口表述准确，无新增策略或过度测试。OpenSpec strict、文档引用及本次diff检查通过；这是触发合同说明与代表解析的限定成果，不外推真实异常交接或整体迁移完成。未自动Git提交/推送。

## 2026-10-21支撑能力先行：路线与讨论记录（最新，仅规划）

用户纠正顺序并明确本轮首先完成整个实施路线、记录关键点。已将[总计划](../../../../docs/operations/completion-plan.md)重排为UEBA → 威胁情报/IOC → 20上一版既有知识库 → Fusion → 分诊 → 调查/攻击路径 → Markdown结果交付；沿用B1—B6及原任务，不新增产品树。共享能力基础属性表与讨论纪要保存在[模块说明](../../../../docs/operations/module-review-plan.md)，项目入口/架构/AGENTS/OpenSpec上下文同步。

本次确定：UEBA首先解释针对哪些实体启用、基线时间/样本/阈值配置、输入输出和偏离算法；IOC先固定查询命中/未命中，数据量与覆盖率暂不考虑；知识库先复用20上一版已采集资料，实际库表/索引待只读确认，历史经验相关后看。空结果为可接受合同，但来源未配置、不可用或失败不能伪装成查无匹配；UEBA不可评分不等于正常。

只读核源码确认UEBA目前无按tenant/实体名单启用配置，normalized输入按user→device→ip固定择一；window_days仅初始化时间标签，无超期样本淘汰。机制边界已记原问题表，后续明确配置需求再提出最小适配；本轮未改算法或业务源码、数据、运行配置，无新测试/模型/消息/部署。原主链/质量失败、unknown及workerOFF保持，产品仍5/15，不归档未完成change。

本轮规划结束独审：未参与文档实现的api_auth_review给出ACCEPT，确认顺序、UEBA配置重点、IOC数据规模暂缓及KB历史经验后看均符合用户说明，无提前实施或新框架；按建议澄清“20上前一版”资料措辞。OpenSpec strict通过，11份本次文档引用检查无缺失，UEBA工作卡已置于Fusion前；仅为文档/结构校验，不是业务验收。

## 前一版二开逐模块方案（历史设计，顺序以上节为准）

用户要求以独立模块推进，先Fusion职责/输入输出/依赖；必要独立依赖先梳理再交回主模块，调查说明输入、所查服务、执行步骤及逐步审计。已结合固定源码及需求形成[模块设计](../../../../docs/operations/module-review-plan.md)：Fusion边界与依赖初稿、UEBA输入/配置/启动/两种输出交接、调查步骤/审计表、标书差距及最少功能验证方式。总计划/架构/项目上下文同步，不新增第二套产品任务树。

静态新发现登记到原问题表：UEBA HTTP基线与Fusion Kafka异常是两条合同，promotion执行门、自动Case/AttackPath身份/图材料及历史查询窗口仍需模块内评估。没有修改业务源码/运行配置、启动服务、发送消息、调用模型或做功能测试；尚未确定的新行为不新增spec或勾任务，当前仍5/15。既有主链已通、质量失败、unknown和workerOFF保持；后续二开按具体模块合同再实施。

文档结束独审由未参与文档实现的api_auth_review完成：主设计ACCEPT，无业务改测阻塞；按审查修正导航旧“尚未实测”与架构旧“正在修复”的现时表述，明确限定实证/质量失败及本地修正未部署状态。`openspec validate restore-alert-investigation-integrity --strict --no-interactive`通过；新文档及本次顶部引用10份文档本地链接检查无缺失。上述是文档/结构校验，不是新功能或模型验收；未归档未完成change。

## 当前优先口径：第一步主链接通已有实证

用户最新要求先走通正式告警输入到调查结果/报告：只补缺源码/直接依赖/环境或接口接线导致无法执行、基本结果取不回的环节。其他入口/全部分支、质量修完、常驻准入及复杂可用/冗余校验不作为前置。复用B4 case02已实测的正式输入→Fusion/分诊→原worker自动graph/deep/工具/MITRE→MD/HTML与关联持久工件读取，第一步已有走通证据；原partial和质量失败保持，不追认质量。

已通知全部worker停止质量/用量补修、重复组合/全量hash水位计数冻结、模型矩阵、多轮审计及新控制脚本。已发出的最后同组仅读取结果157passed/4.02秒；新源码未终审/未部署，155及此前记录保留。未再新建批次树或change，不为回退已修代码另做工作。现有租户/预算/unknown及高风险授权边界不变，workerOFF。整体change余项留后续，当前第一步不以15项全部勾选为前置，复用既有独审技术证据收尾。下文阶段修复/质量门及候选动作均为当时记录。


2026-10-21用户明确开始实施，允许并行worker。沿用本change原任务与B1—B6，不新建重复实施树。

## 本轮并行范围

- fusion_review：B1/I3，统一HTTP/Kafka canonical身份、首次材料、持久确认及tenant合同，保留FusedAlert响应和C01交付保护。直接验证两入口先后顺序和跨tenant写前拒绝。
- api_auth_review：B2/I1，默认Case调查身份与临时baseline解耦，必要结果/报告入口的Case/Run归属；不简单关闭baseline或连带启用厂商执行。直接验证同/跨tenant。
- triage_review：B2/I4及B3，沿既有上下文链补实际token接缝，区分缺源/失败/合法空结果；复用已有KB读取与来源封装接默认四节点，同Run读取一次并记录实际材料、引用和报告关系，只补直接影响的测试。
- root：运行/测试环境、I2正常graph用量及首次分诊读取组合、跨批接线、按实际成果更新回执与完成任务。真实验证使用受控tenant与新输入，旧unknown/积压/回执保持。

并行修改按文件分工，部署由root串行执行。完成后安排未参与对应实现者交叉审计，审计阻塞在本批修复。playbook/反馈原样保留、额外改测和可用性专项后置；只做本次功能正确性必要验证，不默认重跑全仓。

## candidate02阶段快照（历史）

B1已限定完成：119项直接测试及10次真实HTTP验两入口顺序、首次材料和tenant，Fusion一次更新至c52b9aac；源码/部署/运行结束独审通过，任务2.4完成，当前5/15，见[回执](../../../../docs/operations/integrity-b1.md)。

B2身份/上下文和B3知识消费已完成直接测试与独审。I2初轮隔离PG79缺普通SQL状态断言，后由PG日志发现死CASE错误；初轮结果与错误保留，其充分性已撤销。最小修正后candidate02去重组合232项Agents、25项API共257项通过，独审确认状态/iterations/error实际写入。

API已定向部署至1be37c38、Agents至9f74c4a8，Fusion c52保持；自动worker仍OFF。B2/B3/I2的真实人工调查、知识材料/实际引用、usage和报告验证尚待，部署及直接测试不计作整链完成，相关跨批任务暂不勾选。官方声明与源码差距见[功能对照](../../../../docs/operations/alert-function-alignment.md)，结构及扩展点见[当前架构](../../../../docs/architecture/alert-processing.md)。

首次只读SSH连接限制及超时是此前环境接入过程，保留原操作日志；不据此改写产品通过，也不覆盖上述后续实际部署。

## B2/B6 正常报告修复（实施中）

真实新Run `7bc46722`已完成四节点/8062 tokens技术链，报告质量失败；原输出、0个KB marker及失败结论保留，不重调。triage_review负责四个默认调查system prompt及lock、ReportWriter材料传递与实际截断处理和必要直接测试；不改schema、triage v5、其他18个prompt或B4/B5编排文件。先记录本备注，再做最小源码修复；维持有界completion，截断不重发模型，缺证保持未知、动作未执行。真实新输入/部署由root另行推进，最终由未参与实现者独审；不提前勾选整链任务。

root随后授权追加Forensic单文件：修仅error增强被当作有证据的正常语义缺陷，保留错误详情，补零primary/全失败回到原inconclusive分支的直接测试；知识定义不冒充事件事实。工具/增强服务、其他编排与旧Run仍保持。

当时运行completion配置为1024，源码默认仍为2048；旧报告尾文截断，但旧事件未保存finish_reason，不能追称已观察到length。新代码只按实际返回的length处理；本轮直接测试区分源码默认与环境上限，后续由root做有界配置适配，不设无限上限。

本批实现已冻结待独审：4个运行文件（prompt registry/lock、ReportWriter、Forensic）及1个直接测试文件。最终56项断网真实模块测试通过（2.12秒），包含现有知识四节点/来源引用、LLMOps、报告HTML、groundedness、audit helpers及新增正常报告边界；真实SDK客户端经内存HTTP替身分别验证1024配置与2048默认均只调用一次并传递length、原文及usage。首轮55项通过原件保留，第二轮仅增加1024/默认2048区分及原usage断言。测试不等于真实模型内容质量通过；0真实模型/业务写/部署，原Run质量失败保持。冻结清单见本地受控 `.local/aisoc21/completion-integrity-20261021/report-integrity-test-result.json`，21私有 `report-integrity-test/attempt01`、`attempt02`保留原回执，后续独审与新输入由root推进。

## B3 引用格式接缝（实施中）

新Run36bd18e0的实际报告明确使用裸KB1，原parser只识别[KB1]，与实际prompt“marker(KB1)”不一致。root仅扩大完整独立marker识别，保括号格式、未知引用及identifier边界；用捕获原句纯函数验证，不重调模型、不改旧Run或旧0个“已解析引用”事实。后续仅单文件发布，先直接验证与未参与者独审。模型以知识推测本案意图等质量缺陷另保留，不以格式修复追认完整质量。

## candidate04引用与原只读身份接入

2026-10-21，[限定回执](../../../../docs/operations/integrity-citations-tools.md)：单parser文件差异32项直接测试，保旧R01的实际裸标记/0parsed记录不改写。原七权限API服务身份接入，无新工具/API；部署前后独审及六HTTP通过。API1be、Agentsc311健康，仅两服务定向替换；773来源匹配、29层、旧env/七RO/60秒/2048/关闭开关保持，0模型/新业务消息。新C五读者11HTTP通过，尚无C告警/模型；B4下一有界业务，不因源码或认证通过勾完整自治任务。

## 默认调查R01证据与最小语义修正

[R01](../../../../docs/operations/integrity-investigation-r01.md)四次真实调用10167 tokens及MD/HTML/PDF200技术成立，三内容缺陷不改写。两默认节点最小调整hypothesis/observed-scope/unknown及调查处理时间的呈现，保原模型response；明确naive审计时间zone未记录，不补Z或借源事件时区。最终24项直接测试/独审通过，首23与后续修正分别留证；0模型/PG/消息、未部署，待B4当前c311绑定结束后再定向。该修正不等同未来模型内容质量通过。

## B4有限算子预备与首条受理（未启模型）

C上下文11项与common身份六项HTTP通过后，控制算子暴露目录挂载、标准库operator同名、Kafka空metadata缓存三个假设错误，均未到业务；原STOP/脚本/日志保留，明确根审接续且不重冻spec/IDs/time。metadata改公开Admin先查存在后取分区，实际c311/188源码/TLS/PG/Cpolicy/预算及两旧组只读核对通过，未改产品worker或阈值。

随后case01仅一次alert-ingress 202：source51d8a02c-e601-4459-8a74-bbbd63e2b603→canonical756fca9f-cf30-57e6-82b3-a14c4ab59602，raw p0/35；API实证初态new（原schema不暴露resolved_at，不将缺键当实测null）。原Fusion唯一信封fused p2/38，外id、alert_row_id、内alert.id都是canonical，内source_alert_id保原source-v1身份；算子误把内id当source而止于观察，未启worker/模型或重POST。该错误属于验收算子，固定源码与实际消息一致；保留原失败后仅纠观察合同。不得将已受理写成自动关闭通过。

case01首次原worker消费/原API回查及独审通过：BTP0.95、threshold0.85 env、shadowfalse、auto_closedtrue，APInew→resolved/BTP/.95，最终PGresolved_at非空；初始PG该时间字段未单独取证，原API缺键不等于null。1真实回复2174tokens/1unpriced，20000预留单位不是usage，C预约responded；旧A/B预算/两old组commit保持。根审仅批准case02同冻结输入继续，不等同完整自治准入或整批完成。


## B4第二条失败与正常结果修复

case02源4e169979→canonical17254632→Run e3d019ae经真实入口/原worker自动升级调查，无需人工再点；首分诊NR0.85/auto_closedfalse保持，告警triaged、消费前后PG resolved_at均null。七回复22568 tokens（首次2117+graph六次20451）、六工具及11工件的PG/API内容/hash匹配。缺实际lake/厂商资料明确availableFalse/unknown，MITRE查询实际进入后续模型ToolMessage。

完整验收失败：deep六轮仍请求工具，graph20451超过冻结20000 token边界，结果partial；原版确定性risk prior错误派生confirmed_incident/.94，附T1110映射被写成已观察攻击阶段/单阶段事实，末ToolMessage被当narrative；deep摘要还遗漏原raw_event/username字段。保留此次失败和既定边界，不抬限额、不重调旧输入。常驻仍workerOFF/review_only。两例合计8回复24742 tokens；C两预约40000预留单位、observed4291只计首次分诊，不能当整Run usage。

本批仅修实际正常结果问题：fusion_review负责已有investigation/scoring/tool_loop/deep/runner的证据语义、原始材料投影及实际用量边界，保持原编排和cap；triage_review负责关闭兜底finding在NR=阈值时的错误比较文案，不改关闭决策。只补直接测试，0真实模型/旧输入重放，由未参与实现者独审。candidate05仅修默认调查两个报告节点，不声称覆盖本次graph缺陷；独立预构建已过，B4有限窗口退出封存后再定向部署。


## candidate05定向部署与临时身份收尾

C2质量失败STOP后已确认两个有限窗口退出、0活动有限容器。candidate05已预构建4ccf/完整773来源和部署脚本独审通过，root一次定向替换Agents；健康、全部env/七RO/60秒/2048/workerOFF及其余托管容器ID保持，仍29层。只有两个默认报告文件变化，不包含未部署C2修复；0新模型/消息/业务写，详见[回执](../../../../docs/operations/integrity-report-semantics.md)。运行后独审另记，不外推未来内容质量。

八枚本批临时key（A/B两操作、C六）已按独审脚本一次停用，逐枚真实401；事务核所有其他api_key行逐对象保持，旧十reader和永久七权限服务身份不在目标。旧三unknown/原积压、失败输入/判据和工件保持；不重复旧输入或放宽限额。


部署后candidate05独立只读审计accepted：实际773运行输入、远端source及完整父层/两COPY匹配M05；全部env/7RO/60秒、关闭开关/2048/common身份及其他托管容器ID保持。净化记录见[运行回执](../../../../docs/handoff/integrity-candidate05-runtime.json)，原始SHA8f8e72b5a3620d1d2fef6dd838d61723ec32279943d1215d0e51cc39a3f931f9；0新增HTTP/模型/消息/业务写，不外推内容质量。


## 2026-10-21 full配套与Markdown范围

已按用户指示整体补迁enrichment/threatintel/ueba共101固定原件和图schema资源，沿原依赖最小接线。历史事件、参数化调查补查、UEBA实际消费/Agents读取、IOC增强、OS索引/查询及TI/API代理已基本运行验证；原缺失后端不补，0模型/厂商/Feed调用。报告当前只要求Markdown，复用原生成/持久/读取证据，PDF/HTML额外交付不作前置。严格校验通过；本批实录与最后独审见docs/operations/full-support-migration.md/json。沿用任务2.1/3.1/4.1的本批部分，不勾选未完成的完整change任务、不归档，整体迁移仍未完成。

本批结束：未参与实现者api_auth_review最终限定ACCEPT，无新增功能接通阻塞；仅更新本批回执，未额外验证/归档或勾选总change未完成项。
# 2026-10-22 服务 v1.0 发布增量（执行前登记）

用户已授权开启Kafka自动分诊和自动调查、模型沿用现有配置、新建独立生产租户。按[服务发布计划](../../../../docs/operations/service-v1-release-20261022.md)复用既有19文件候选镜像；仅生产租户新增服务身份/预算及新消费组起点，定向发布API/Agents，做一条全新合成告警代表验证和结束独审。不重调旧输入，不覆盖旧unknown/预算/消费组，不扩真实响应或Git推送。本文先登记授权/计划，执行结果另附；原5/15及旧质量失败不据此改写。


## 2026-10-23 V1页面字段对接说明与实值核验

用户要求从产品经理角度逐字段确定告警和调查展示，并确认当前线上/本地确有数据。新增[页面说明](../../../../docs/integration/v1/page-elements.md)及[字段实值](../../../../docs/integration/v1/ui-field-verification-20261023.json)，README增加入口。参考20已部署页面的信息组织，实际数据以21 API5a1e1fd8/Agents49643b84的两既有合成样例为准：41 GET200、21工件正文hash/字节匹配；PG两目标只读查询补核source快照/负责人/解决时间。

本地独立临时PG两例先完成工具查询后模拟超时/模型异常，原runner/Deep/ledger持久化与read_persisted_run冷读通过；与6个已有handoff直接用例共8 passed。模型/工具是替身，临时表不是完整生产schema/RLS；复用当天真实人工采用样例，不重跑模型。临时容器已stop并自动删除。本地source哈希和测试日志哈希见字段实值JSON。

两个初始失败如实保留：线上探针误查不存在source列，改用enrichment_data身份后通过；首次本地PG连接遭沙箱网络拒绝，允许隔离本地连接后通过。线上search无匹配串仍返回3为确认问题，不判成功。本批仅文档和取数验证，不实施页面/后端新合同，不发Kafka/模型、不部署或Git提交推送，原5/15及旧质量/unknown/预算失败保持。结束独审另记audit。


## 2026-10-23 数据库直查交接补充

用户要求保留HTTP但先给数据库表/位置，由后端自行查。新增[直查指引](../../../../docs/integration/v1/page-elements.md)及[告警SQL](../../../../docs/integration/v1/examples/ui-alert-fields.sql)，六核心表及90项展示信息映射；明确派生HTTP键没有同名表/列、工件正文TEXT、成本关联TEXT、目标关联及租户范围。本次只复用实测数据，38个SQL列对照实际catalog、8条JSON路径逐例核既有原件，链接/只读语句检查通过；新增展开SQL未重跑生产，已有production-two-examples.sql原9 SELECT通过记录保持。不新建接口/账号、改表/部署/模型或Git提交推送。原5/15及所有旧失败保持；独审另记audit。


### 用户追加：只保留一份最新交接文档

页面与数据库两稿合并为[page-elements.md](../../../../docs/integration/v1/page-elements.md)，HTTP、90项展示定义、表/字段映射和实测边界均保留；SQL和字段实值作为附件。删除两份dated旧稿与本轮旧文档快照包4文件，README/数据库索引/根记忆/本change链接统一到新文件。不删除其他主题基础文档或原始测试证据。独审发现first_seen_at当前由首次claim写入，已明确为首次人工认领/确认时间，非页面打开或自动分诊时间。本次仍仅文档清理，无业务操作。


### 2026-10-23 统一文档按使用顺序重排

用户要求顺序为页面/功能/字段、数据库表、按功能取数并举例、已有HTTP，其他信息后置。已原地调整唯一主文档：第1章四页及90字段纯产品定义；第2章库/六表/工件与支撑；第3章保留字段映射并补六组现有样例的SELECT取法/实际结果；第4章集中查询与操作接口并区分已读/仅源码入口，escalate仅提高等级；第5章保留口径/本地/验证边界。README章节索引同步。仅静态校核，不新建旧版本副本，不重跑生产SQL/调查/模型，无产品改码/发布或Git提交。


### 2026-10-23 页面示意独立附件

用户要求以独立Markdown/Mermaid直观看页面布局、菜单、字段与实值，且与原交接文档一致。新增 `docs/integration/v1/ui-wireframes/` 下7张图及1份索引：四页面，调查详情四页签分别展示；复用两条既有合成告警，未访问生产、调用模型、改业务代码或部署。原主文档SHA256保持 `5fb8885e8ab241d3c97af7ae79698610bedf5fbf4534e292aafd2308318d3a9d`。

90项编号/名称精确对应且各落位一次，39处相对链接通过；Mermaid 11.12.0及本机无头Chrome实际解析/渲染7/7通过，并检查预览改正长标题换行。临时依赖位于 `/private/tmp/socai2-ui-wireframe-check`，未改项目依赖；本地验证首次受DNS/回环监听沙箱限制，升级后渲染通过，临时服务和浏览器随脚本退出。结果在 `.local/verification/ui-v1-20261023/wireframes/document-check.json`、`render-check.json`；此为文档验证，不是前端实现或业务验收。


### 2026-10-23 功能示意用途澄清及取消截图

用户最新明确取消网页截图/对照，原截图尝试只到浏览器控制超时，未形成网页截图或对照文档，获准的Playwright替代尚未执行即取消。已在7份MD文首及Mermaid图内标注仅功能要素/字段对照，非UI或交互设计依据；索引与对接README同步，后续模块不得照图确定布局/导航/样式/交互。主文档与90项字段保持，只做文字/编号/相对链接核对，不再次截图、渲染或访问网页。检查在 `.local/verification/ui-v1-20261023/wireframes/scope-notice-check.json`；此前渲染回执仅对应此前版本，不改写为本次新验收。


## 2026-10-23 页面功能必要性与可取数据完整审计

用户要求对完成的主文档与七份功能示意做最详细对照。本批沿原change补[审计](../../../../docs/integration/v1/ui-functional-data-audit.md)与[机器矩阵](../../../../docs/integration/v1/ui-functional-data-audit.json)：90字段组各列必要性、原页面源码依据或新增理由、库表/JSON定位、实值与空子项、派生及未部署限制。原版前端为本地参考副本，本批没有重新证明其与20部署镜像一致；独立Run页面属于适配自动无Case调查的必要新增，不称原版现成页面。

16:42在21执行PG只读事务和10个reader GET；六表167列与目录一致，既有两例21事件/21工件/3成本行可读、21正文hash/字节及Run/事件关联通过。无匹配搜索仍3条，明确为缺陷。processing-context沿14:39原读回；本地8项用例与人工采用样例仅复用。首个SSH探针被沙箱拒绝，后续授权只读取数通过，未改写失败。

主文档及图05/07同步修A27空值、I29技能无统一采用数、I41旧工具默认0ms与缺status、报告空态；90编号/名称与七图一致。截图取消且示意不约束UI/交互；无新业务输入/模型/业务改码/DDL/部署或Git提交推送。原5/15、质量/预算/unknown保持，结束两路独审见audit。


## 2026-10-24 迁移收尾执行

用户取消本会话的背景事件入湖/调查联测并说明独立调查侧承接，要求先收尾，后续工作先规划再讨论。本批基线main/7ea813a638bd78d8e1ed56791c1bc5f3ff9271eb，执行前工作区干净。新增收尾回执，按原15编号逐项列已有证据和转出责任；更新当前入口/工作约定/进度，独立调查不再沿本change实施。

只编辑Markdown/OpenSpec元数据并静态核对，不改业务/测试/部署/模型，不访问生产/网络、不发消息/写库/新测或Git提交推送。旧回执内容及失败保持，原5个已勾任务原文不改。结束独审先指出2处规格过宽，修为本次所需入口、实际已留存材料及截断缺口后限定ACCEPT/0必须修。4.2据此结算；严格校验、665链接及diff检查通过，正式归档另记audit。


### 实际归档完成

已完成归档前检查并执行正常archive（未用skip-specs/no-validate），迁移归档目录为`2026-10-24-restore-alert-investigation-integrity`，主规格17项；修复归档出入119条Markdown链接。主规格Purpose实际保留线上/本地与验证边界，未代验独立调查。活动清单仅剩原暂缓R02；原R02五文件、0/17、冻结历史和4份非Markdown归档原件保持。封后strict为active/spec2项、archive4项全部通过；1028本地链接0缺失、合同正文/任务及变更范围通过。第一次纯文本比较的空行差异及修正验证器记录保留，未改业务或规格合同。最终限定审阅见audit。


封后独立审阅已完成：migration_closeout_audit限定ACCEPT/0必须修，静态证据与规格/任务/R02保护一致，最终迁移基线收尾。后续仅按用户要求保留规划供讨论，独立调查及背景事件工作不在本会话重做；没有Git提交推送。
