> 历史资料：本文件保留原批次的设计、执行或评审结论，不代表当前状态或新增授权。原路径：`PROGRESS.md`。当前入口见[PROGRESS](../../../../../PROGRESS.md)，迁移位置见[归档索引](../README.md)。

# 当前进度

更新于2026-11-14。按负责人要求完成[三案固定调查展示](../../../../operations/evidence/fixed-investigation-20261114-01/README.md)：本机隔离PG新建4A/2I/3Case共9Run、19次真实生成；C01 accepted/uncertain/partial并采用，C02/C03 rejected/unavailable/partial未采用。E01登录A引用拒收、C02 C3截断及C6依据/范围错误、C03 C6重复引用均保留，模型质量NOT_PASSED。三案20次ASGI读回与数据库快照一致，鉴权/依赖覆盖不冒充正式TCP验收。4177旧静态展示完整备份后清空；随后发现生产实时列表会折叠三案并回填旧记录，已[关闭工作台在线读取并再次清理](../../../../operations/evidence/workbench-display-fix-20261114-01/README.md)，当前本机/21根入口仅本批3条；前端[4173 demo](http://127.0.0.1:4173/#/cases)已同步相同保存快照，原有样例和浏览器编辑保留。未改核心/API/表结构或启用消费者，流式未实施，主31/41保持；本轮未提交或推送Git。

前批人工采用验证（case-result-adoption-20261113-01）新建1个合成Case，4份Result均由程序提供，0模型/外部工具/HTTP调用；人工采用前已启动的旧Run不覆盖较新人工选择，后来显式启动Run仍可自动采用。有效H随后使当前判断stale，不自动重算；旧请求重试返回原回执，不回滚新判断。pg-02脚本误判Case初始状态后停止，实际采用已提交；原失败/快照保持，pg-03从同Case回执继续并通过余项。最终3个判断版本、原Result和活动均可读，限定审计见本批回执。该前批当时本机静态84→85、在线4177未同步；当前展示范围以上述三案批次为准。

采用核心及E21/E63/E64已随独立HTTP发布；固定调查模型修改随后已随核心`v1.2-20261113-r1`发布，独立HTTP侧已同步并完成两端既有记录读回；复用既有表，无迁移或告警字段变更。前批[Deep知识筛选](../../../../operations/evidence/case-deep-knowledge-20261113-01/README.md)、[C6逐问题知识选择](../../../../operations/evidence/case-final-knowledge-20261113-01/README.md)及[09真实Run](../../../../operations/evidence/fixed-investigation-20261113-09/README.md)原件保持，本轮未为正文质量追加模型采样。主调查31/41、正文和知识合理使用NOT_PASSED保持；流式和自动反馈重算继续后置，按2026-11-13负责人明确要求，各页面AI对话（助手入口、提问/追问、会话历史、回答读取与保存）暂缓，E19/E20仍501；告警分诊、事件诊断及Case调查按原计划推进。[交接指南](../../../../../FRONTEND_BACKEND_HANDOFF.md)、[问题清单](../../../../investigation/current-issues.md)。

## 当前运行状态

| 项目 | 已核验结果 |
| --- | --- |
| 分支与远端 | 本地 `V1.1`；Git暂不提交或推送；后续获准时同步目标为 `origin/V1.1` 与 `origin/main`，父项目为 SpiritHub 的 `add-server-submoudle`，按其 `server` gitlink固定版本。源码提交与21已部署镜像分开核对；部署状态见下行 |
| HTTP交接文档 | [71个后端HTTP操作](../../../../../deliverables/investigation-validation-20261106/http-handoff/README.md)，告警/事件/调查三类；docs19，69已实现/2问答暂缓501。162类型、764固定输出字段、35动态说明；125功能保持22/15/88。[本机Swagger](http://127.0.0.1:18080/)、[21 Swagger](http://192.168.1.21:18080/)，[回执](../../../../../deploy/api-docs/deployment-receipt.json) |
| API／处理发布 | 核心`v1.2-20261113-r1`/处理`processing-20261113-r1`保持；独立API`investigation-sync-20261113-r1`已同步，本机-local/v12_upgrade_dev、21内网18024/aisoc。667源码/策略摘要相符，两端各10业务GET与各端旧基线相同，0新模型/0业务写入。[本批回执](../../../../operations/evidence/investigation-http-sync-20261113-01/README.md) |
| 工作台 | 源码保持 `workbench-20261112-graph-cleanup-r1`，兼容28/旧29表快照。11-14按要求切既有无DSN静态模式，online=false，仅重建工作台；镜像/源码/挂载及其他容器保持。当前[展示配置](../../../../../deploy/aisoc21/workbench-display-current.json)，旧Compose和静态目录已备份 |
| 当前测试展示 | [4177](http://127.0.0.1:4177/index.html)本机/21仅11-14三案，211文件/7静态HTTP入口已核；[4173](http://127.0.0.1:4173/#/cases)增加同批4告警/2事件/3Case/9Run，浏览器已核结论、拒收空态及H原文；两者均为保存快照 |
| 正式数据 | `aisoc.socai2` 当前28表450列；25表有业务写入、response_links有读取用途、conversations/messages仍有依赖。告警交接字段、枚举、JSON合同保持 |
| 本机数据 | `v12_upgrade_dev` 与 `socai2_local_20261105` 同样28/450；旧本机数据库容器恢复停止，其他历史验收库未清理 |
| 数据库清理批核验 | 21实际读到1Case、4Run、36工件，4177的首页、状态、列表均200；三个目标保留目录指纹及既有告警/Case/Run/工件数量完全一致 |
| 知识功能 | 前批分诊保存后同步已交付归档，仍为开启/120秒；C2三目的检索、qwen3-embedding:0.6b/1024及专用集合保持，旧operation key不补派 |
| 模型与消费者 | Agents自动分析消费者关闭。11-14三案批4A/2I/3Case、19次生成/140,521tokens；1案采用待复核结论，2案拒收未采用。保存/读取及静态展示通过，正文质量NOT_PASSED；历史01–10批原答/失败不改。核心r1及独立18024版本保持，21生产业务无新增写入 |

[清理回执](../../../../operations/evidence/graph-table-cleanup-20261112-01/delivery-summary.json)记录三个真实目标的结构与业务保留结果；[本项验收](../../../../../openspec/changes/archive/2026-11-12-remove-unused-investigation-graph-table/validation.md)区分本机事务验证、专用空库新装、工作台装载与生产只读复验。冻结V1 SQL及迁移123–126未改，当前新装/增量/核验见[数据库入口](../../../../../deploy/database/CURRENT.md)。独立运行脚本中的公共支撑结构不是业务后端需照搬的建表清单。

前批[知识同步回执](../../../../operations/evidence/knowledge-sync-20261112-01/delivery-summary.json)仍是其直接流程证据。固定01批已证明知识进入请求、历史引用保存/GET读回，C6建议缺依据拒收；02–04批继续暴露I预算和C6完整输入超限，失败与系统收尾均真实保存读回，未追认成功。最后按原C3步骤取件核得04批C6正文63,262字符；当前仅调整查询/材料读取展示后离线为38,152字符，原记录及映射保持，不等于C6实际执行通过。当前本机包及在线4177已切换为11-14三案；10批等旧静态展示已完整备份，数据库记录未删除。[10批回执](../../../../operations/evidence/fixed-investigation-20261113-10/README.md)与本轮核心发布回执分别保留，本轮未重新发布工作台。

产品文档已按现有设计重整为[逐页功能清单](../../../../../deliverables/investigation-validation-20261106/frontend-feature-list.md)，逐项保留目的、操作结果，按后端实现状态和接口链接说明；事件另有展示字段与点击跳转表；[规则确认记录](../../../../design/investigation-product-decisions.md)单列。D07 已由负责人确认：未解决问题随调查结论展示，不单独管理；需要人工确认时由用户创建任务。D01–D06 已按逐项讨论建议一并确认，七类规则均已同步产品说明；未实现功能的状态不变。原字段／跳转移到同目录技术附录，Case 写入及探索存储的过时说明已修正。前期产品规则整理仅改文档；前批按已确认规则实现告警反馈和告警/事件管理，本批补齐列表查询，不核销页面或模型未通过项。随后逐批补齐[HTTP交接包](../../../../../deliverables/investigation-validation-20261106/http-handoff/README.md)：当前125项功能映射71操作，参数、输入输出和错误已同步，两项问答暂缓且预留501。独立正式服务已有71操作，E36/E37已挂载/开启；具体测试和模型质量边界见下段。前批列表查询已提交c1c37dae，并同步V1.1/main及SpiritHub server；CSV交付已提交6c6b98520，V1.1/main及父项目server一致；前批评论已提交ce425f3c1并同步双分支及父项目；本批附件交付按固定Git skill收口，结果以回执为准。

## 未完项与下一步

11-14[当前评审](../../../../investigation/investigation-current-review-20261114.md)已落地：核出生成Schema与接收规则差异、C3截断，明确三案关闭湖查询的取证边界及新材料入口衔接；21只读见投影三分区lag为0、Agents分析关闭。负责人指出的4177“本轮停止原因/stage_output_saved”已补入RV12：正常结束码误归错误，交付节点未直接呈现同Run已保存的A/I业务结论；HTTP源码与快照已核，尚未修复或发布页面。13项发现给出证据和处理建议；正文质量后置、主31/41保持。

当前缺口见[功能缺口表](../../../../investigation/current-issues.md#当前功能缺口与实施入口)。固定调查输入、综合结论/保存读取及独立HTTP同步的既有交付保持；本轮评审建议在主调查中处理直接程序问题，流式仍复用 [schedule-streaming-investigation-updates](../../../../../openspec/changes/schedule-streaming-investigation-updates/tasks.md)：①统一持久化队列及A/I/Case领取保护；②接材料/成员/采用A/告警人工判定变化及事件跟随；③仅H时基于当前采用调查的原证据重算C6，混入新材料则完整调查；④知识维护异步化及受理/状态交接。先补防双跑，再开自动路径，创建Case仍不自动执行首轮。流式尚未实施，评审未改核心/API/表结构或运行开关。质量、对话、真实响应及产品页面完整接线仍按原决定后置；本文以下保留已交付证据，不重复列为待实现。

HTTP当前71操作、764个固定输出字段出现位置、35组动态结构；[原43操作验证](../../../../../openspec/changes/complete-socai2-investigation-chain/http-functional-validation-20261112.md)继续适用。[Case管理change](../../../../../openspec/changes/archive/2026-11-12-manage-investigation-cases/validation.md)已独审归档，完成F23-04/D01：E44读取管理及结案条件，E45局部修改，E46结案，E47重开。两端各20次正常TCP HTTP、全部Case字段SQL及关闭/重开历史读回通过；运行中/unknown拦截、未完任务确认及理由、幂等/冲突有直接证据。实际镜像/源码/目标核对一致，原服务保持，未新增模型调用或迁移。随后[告警/事件管理change](../../../../../openspec/changes/archive/2026-11-13-manage-alert-incident-operations/validation.md)已完成E48–E53：告警人工判定、告警管理、事件管理各单条/批量。两端各86次真实HTTP及6主体SQL逐值读回通过；D02关闭/反向恢复、人工关闭保留判定、事件分配/解决/等级覆盖、幂等与整批拒绝均有证据。原47操作/106个Schema保持，未新增表或模型调用。API及docs7已同步，限定独立结束审计通过并已归档，见[本批回执](../../../../operations/evidence/subject-management-20261112-01/delivery-summary.json)。前批[列表查询](../../../../../openspec/changes/archive/2026-11-13-query-investigation-lists/validation.md)补齐E02/E26/E27筛选、双向排序、稳定游标；仅告警/事件HTTP封套新增已确认filtered_total/next_cursor，数据库和行字段保持。15项定向离线检查、117次候选真实TCP/PG及旧版本兼容对照通过，查询前后目标行一致。前批两端18024曾发布list-query-20261113-r1及Swagger docs8，现由下述CSV版本升级；本机新样本复用、21既有合成记录只读HTTP/SQL核验均通过，不启动模型或消费者。对外HTTP边界和内部直接调用保持，完整导出已由本批完成，统一归并统计已由本批完成，AI对话暂缓，相似历史复核E70和探索保存已完成，同主机近期展示E71已完成，后续范围见[实施计划](../../../../investigation/http-implementation-plan-20261112.md)推进。

前批[完整CSV导出](../../../../../openspec/changes/archive/2026-11-13-export-investigation-lists/validation.md)已实现E54告警/E55事件/E56调查。输入沿用对应列表筛选排序，可明确选公开列；同一只读快照返回全部命中，超过10000行/16MiB拒绝413，SQL超时503，不返回截断文件。17项定向检查、62次候选真实TCP/PG通过，55条告警跨旧分页上限完整导出；104个列与列表逐值一致。本机13次、21既有合成记录12次正式读回通过，两端SQL目标行保持，0模型/0新增21业务写入。[回执](../../../../operations/evidence/list-export-20261113-01/delivery-summary.json)。归并统计及普通评论已完成；附件引用已完成，文件平台由业务后端承接；采用规则由调查模块统一；AI对话暂缓；探索已交付，同主机近期展示E71已交付。

前批[E57归并统计](../../../../../openspec/changes/archive/2026-11-13-summarize-incident-grouping/validation.md)完成F06-06。输入为可选告警来源及真实发生时间范围，在同一只读快照返回总告警、已归并/未归并、去重事件、处理中事件及压缩比例；比例只以已归并成员为分母，空分母null。6项定向检查、本机13次候选HTTP与SQL重算通过；本机正式13次及21既有合成范围12次读回一致，两端目标数据保持，0模型/0新增21业务写入。Swagger docs10及8文件运行核对通过，[回执](../../../../operations/evidence/grouping-summary-20261113-01/delivery-summary.json)。本机首次切换因旧进程退出后端口暂未释放停止，确认空闲后启动并验收通过，初次503记录保留。

前批[采用已有调查结果](../../../../../openspec/changes/archive/2026-11-13-adopt-investigation-results/validation.md)交付E21/E63/E64。两个独立本机批次各20HTTP及SQL通过（工作树和冻结7文件部署基底）；正式本机7GET、21已有数据6GET核对当前判断/预览/历史。0模型、无迁移，未完任务/Run及处理状态保持，生产采用写入未实测。采用批当时Swagger docs13两端相同，该批64操作/62实现/2问答预留；565响应示例。前批评论/附件保持，文件平台归业务后端。同案助手及各页面AI对话按负责人要求暂缓；前批[案件故事查询](../../../../../openspec/changes/archive/2026-11-13-query-case-story/validation.md)E65已完成本机/21发布，30次功能HTTP及补充1次GET/11表原行不变核对通过，正式两端各7GET通过；原64合同保持，核验脚本原失败保留。该批Swagger docs14两端内容一致；当前版本已由调查核心同步/docs19升级，自动反馈重算继续后置。

前批空表清理的结束审计和归档已完成；当前固定流程已通过[限定程序修复独审](../../../../../openspec/changes/complete-socai2-investigation-chain/fixed-flow-audit-20261112.md)，不替代主调查完成。前批列表查询已提交c1c37dae并同步V1.1/main及父项目；前批CSV已提交6c6b98520并同步双分支和父项目；前批评论ce425f3c1已同步；本批附件已发布读回，结束审计及归档后Git同步以固定skill回执核对。并行模型源码与未提交证据保留。

负责人最新顺序：**先做好固定范围调查，再推进更新/流式。** A/I、C3、Deep、C6输入按任务由程序筛选，保留事实、有效必要前序和依据；未查询只显示未查询，后台台账留原件。当前[第32节C3分工](../../../../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md#32-c3业务判断与程序覆盖记录分工)已本地实现五项业务答案→程序补coverage→六问保存，局部保留后重算，旧冻结六问兼容。7项既有定向场景及原09答离线兼容通过；105项材料/引用、108份旧件保持，失败原件保留。详见[程序修复及完整预览](../../../../operations/evidence/case-c3-coverage-20261113-01/README.md)。

发布基线[10批固定流程](../../../../operations/evidence/fixed-investigation-20261113-10/README.md)只新建1个Case Run，复用原A/I、事件关联、H和指定基线，5次生成/65,000tokens。C3五问装配六问保存；授权Deep有效、影响Deep重复引用拒收且未作为C6判断，C6一次纠错后accepted/uncertain/partial并采用为第3版，current；4次ASGI及真实隔离库保存读取一致，旧行/原答/失败保持。知识已检索并按问题选入，但未被结构化引用，合理使用未证明。本机包及21的[4177](http://127.0.0.1:4177/index.html#180439cd6016b0a579cd9526961e226e20ca90f4f14a69683f7e23dcce478a99)当时仅展示这1批；该静态原件已随11-14展示替换完整备份，当前页面见顶部三案链接；10批验收本身没有HTTP字段/表变化、模型服务发布或加预算；随后发布见下段。[限定结束审计通过](../../../../operations/evidence/fixed-investigation-20261113-10/audit.md)；正文质量NOT_PASSED、主31/41保持。[流式规划](../../../../../openspec/changes/schedule-streaming-investigation-updates/proposal.md)尚未实施，队列和自动反馈重算继续后置。

固定调查功能版已发布21核心`v1.2-20261113-r1`及显式处理镜像`processing-20261113-r1`：[发布回执](../../../../operations/evidence/fixed-investigation-release-20261113-01/README.md)。136项调查源码与10批一致，运行源码/策略/健康通过；既有1Case、1Result、当前判断及对应4表原行前后摘要一致。发布后限定独审PASS；独立18024、Swagger、工作台等7个指定保留服务身份不变；无新模型、业务写入、迁移或Git提交推送。接口聊天已按[核心接续说明](../../../../operations/evidence/fixed-investigation-release-20261113-01/handoff.md)完成其71操作服务同步及既有记录读回。流式/队列、自动反馈重算、自动分析消费和模型质量仍未完成，不据阶段发布核销主31/41。 当前[模型输入输出](../../../../investigation/model-input-output-current-20261109.md)、执行账本和固定流程计划已对齐该发布及10批原件，旧六问/工具台账/全量前序说法已更正；[文档收口记录](../../../../operations/evidence/fixed-flow-handoff-20261113-01/README.md)无新增调用或部署。

本轮交接补充[组件/Kafka](../../../../integration/component-handoff-current.md)、[可复用测试数据与操作](../../../../integration/backend-test-guide.md)、[Swagger本地配置](../../../../../deploy/api-docs/README.md)及[4173测试页面](../../../../integration/test-page-4173.md)。21:18024已再核运行版本和71操作；Kafka组只读确认Fusion/UEBA/投影运行、Agents自动分析关闭；现有页面仅用于测试；负责人11-14随后要求同步前端demo，本轮已新增三案快照数据及引用，未扩展产品接线。

正式告警级人工反馈现通过E48/E49保存；Case H任务版本和告警反馈保持各自用途，均不自动重派调查。Q问答、真实响应操作和自动消费仍未完整交付；探索保存恢复与附件关联已交付，实际文件上传/下载由业务后端负责，未据本批验收，不因旧AiSOC模块扩大范围，资产等基础数据由业务后端实现。

负责人最新确认：**模型正文质量后续解决，不阻塞固定流程功能收口与新版发布**，不再为这些问题追加模型采样；原答/失败及NOT_PASSED保留，程序功能阻断仍需修复。F02召回正文相关性／合理使用、F01完整语义质量继续登记后置；P01–P04为历史页面事项，现有页面按用户最新说明仅作测试，不列为当前后端交付前置；M01-A/M01-B保持已知未修复、不反复采样。前批及本轮rejected/null、accepted/uncertain/partial分别保留，不用接受状态追认正文质量。主调查仍31/41，未完成整体任务不因本轮清理核销。[问题清单](../../../../investigation/current-issues.md)。无关未跟踪 `tools/model-preflight/` 保持。
