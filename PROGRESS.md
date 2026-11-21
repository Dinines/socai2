# 当前进度

更新于 2026-11-21。正式 21 已切换为 c173-release-20261121-03，HTTP 与 Swagger 有 82 个业务操作。同一条真实告警完成独立候选联验，正式服务及数据库读回通过。[联验和正式回执](docs/operations/evidence/c173-bounded-json-20261121-01/README.md)。

2026-11-18 历史记录。**21完整服务和两段流程测试已完成；4b工作台0.6.1/r8及验收工具现已发布，指定Case/轮次与紫色来源实际查阅通过。** [发布/核零](docs/operations/evidence/acceptance-release-20261117-01/README.md)之后，最终3d04验收容器发送2告警/3上下文，形成同一事件、同一Case的两轮结果，成员1→2，后轮比较实际首轮。7任务、6Run、48步骤、142工件及477次HTTP成功回执已核；8次真实模型均stop，共45207tokens，实际并发峰值1、结束时无在途。[本轮完整回执](docs/operations/evidence/acceptance-fullflow-21-20261117-01/README.md)与[输入输出报告](docs/operations/evidence/acceptance-fullflow-21-20261117-01/results/report-01/report.md)可查。

本轮按[§12.14](openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md#1214-负责人明确要求先发布21清历史再测试2026-11-17)执行明确分阶段发布。测试模块与HTTP模块分别完成10组、11组限定独立复核；4177已核三类主体、首轮201/后轮202、冻结输入、具体领域、原答与5项问题。后台tenant/来源关系保留，8份实际模型输入未带控制身份。两轮Case均accepted/uncertain/partial；4项自动引用诊断及1项人工比较正文问题后置，不冒称模型质量通过。

4c发布/准入与4d本次真实两段及限定复核完成。4b[来源识别子步](docs/operations/evidence/workbench-test-source-20261117-01/README.md)随后在本机完成：新测试源默认以lyc开头，页面直接按所选Run冻结来源显示紫色，不再要求先发布账本；无账本浏览器和测试模块限定独审通过。A/I/C3/Deep/C6共20项输入检查未带入注入的lyc后台标记，原件及业务字段保留。随后[报告精确轮次跳转](docs/operations/evidence/workbench-deeplink-20261117-01/README.md)也完成本机直接验收：报告/菜单、6个真实Run链接及8项浏览器通过，Case两轮冻结1/2成员，刷新/重载不串轮，缺失和错环境不回落latest；独立复核关闭IPv6链接问题。4b随后按负责人明确要求完成[4b发布回执](docs/operations/evidence/workbench-4b-release-20261117-01/README.md)：0.6.1/r8及验收镜像已上线，禁网新报告指向实际4177；最终报告两轮点击、冻结1/2、紫色来源、刷新/重载及无效目标不回latest均通过。26GET核6Run/8原答/4副本/两C1；原982份prepared和8账本保持。[测试模块最终7组限定独审](docs/operations/evidence/test-workbench-4b-release-20261117-01/independent-release-review-01.json)通过，未关闭发现0；仅收口4b本次发布。完整后端含D5a修改，但本批没有Deep模型调用，D5a异常PG/C6目标及D5/D6仍未验。旧失败、原答和4a冻结母本保持。分支V1.1；负责人已明确要求将当前积累内容全部提交并同步Git。本轮按已发布版本核对源码、整理正式证据及交接；整个change未完成，不归档。[本批Git发布核对](docs/operations/evidence/git-publication-20261118-01/README.md)保留源码、证据检查及未验边界。

## 当前运行和数据

| 内容 | 当前实际状态与证据 |
| --- | --- |
| 当前已发布版本 | `c173-release-20261121-03`。HTTP、Swagger、Fusion 与联合调度同版，82 个业务操作，调查库 35 表 565 列，湖表 62 列。[正式读回](docs/operations/evidence/c173-bounded-json-20261121-01/README.md) |
| 日常展示 | [4177](http://127.0.0.1:4177/viewer/) 沿 0.6.2/r9 入口，仅监听本机。正式告警、事件和 Case 列表与当前正式数据库空态一致，历史批次资料留对应回执。 |
| 本轮需求落点 | 21部署与新两段测试已完成；4b来源识别在本机完成并限定独审，20项模型输入边界检查通过。4b报告指定Run跳转已完成本机验证、21发布及实际读回，新配置/页面/验收工具已上线；D5/D6保持待办 |
| 历史数据清理 | 本轮明确84业务表521行、湖15条、Redis13键、4个指定Kafka主题25条、24账本文件核零；127非目标表和Schema不变，4向量集合原为0。[核零](docs/operations/evidence/acceptance-release-20261117-01/cleanup-zero.json)；旧批UUID现在不可从正式库读取，离线原答和受控备份保留 |
| 业务服务 | 21 的 HTTP 18024、Swagger 18080、联合调度和 Fusion 已就绪。事件运行配置实际读回 8 字符和 8192 token。UEBA 已恢复，Fusion 和 UEBA 已通过 Kafka 内部明文连接读回，三类业务查询通过。[正式读回](docs/operations/evidence/c173-bounded-json-20261121-01/README.md) · [Kafka 切换回执](docs/operations/evidence/c173-kafka-plaintext-20261121-01/README.md) |
| 其他入口 | 本机58482/58483已由实际4177替代并关闭；临时预览58477/58479/58481已关闭，本机4173旧静态演示已停止。旧源码、包/容器、模型原答及审计回执保留离线，不作为活动输入。旧库清理备份在本机/21 私密目录，不进入模型或索引 |
| 数据库合同 | 21 正式 `aisoc.socai2` 已应用增量 130–134，实际 35 表、565 列。旧候选与本机历史库沿原批次记录。[数据库入口](deploy/database/CURRENT.md) |
| 模型容量 | 实际服务窗口 65536；A/I/Deep 输出8192、C3/C6输出16384，A/I每 Run 总预算各131072、Case393216，输入准备1 MiB。沿[已验预算配置](docs/operations/evidence/streaming-budget-20261116-01/README.md)，D1–D4c及后续发布未改这些预算；D2真实调用3次，D3为受控回放0次新生成，D4a新增真实A/I各1次；D4b新增0次；D4c真实9次、69015tokens，注入不重复计费 |
| 输出兼容修正 | xgrammar兼容及D1–D4c已随r4发布，当前20261117-r1保持这些实现；下列各本机回执保持原验证范围。D2本机将六类缺说明改为独立诊断，程序还原1218字原观察不再受模型正文1200字限误拒收；真实3次stop、C6两项缺说明保留。D3本机C3支持完整JSON length与闭合单元恢复，最多一次补答，不丢初答；原失败不变、质量未全面通过。D4a本机A/I已保存完整、partial/none回执；D4b事件终结材料选择、Case门控/分配/C1冻结已通过，D4c已验partial/none→同Case两轮完整链，其他模型阶段/网络异常待D5 |
| 新测试材料 | 本批2告警/3独立上下文分两段各发送一次；8份实际A/I/C3/C6输入无tenant_uid/tenant_id、来源控制ID/标签、execution/test_batch/expected标记。后台tenant/告警/来源关联保持。旧批16份残留和原答保持历史结论，不改写 |
| 历史新02完整真实链（本轮清理前） | 21 Kafka入站13上下文/4告警，4A/2I/3Case Run；10task、9attempt/Run、77步骤、228工件、3Results，全部Case结果accepted/uncertain/partial。整案3→4且R2比较实际R1，单案保持1轮；no_changes 0新attempt/Run/模型。14真实调用均stop、111169tokens，318GET读取前后23表不变；19条诊断后置，正文未全面通过。[最终验收](docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json)、[输入输出](docs/operations/evidence/streaming-fullflow-20261116-02/model-io/index.json)、[本机静态](docs/operations/evidence/streaming-fullflow-20261116-02/static-verification.json)、[并发核对](docs/operations/evidence/streaming-release-20261116-04/dispatch-concurrency-review-02.json)。[实际4177浏览器](docs/operations/evidence/streaming-fullflow-20261116-02/viewer-browser-02.json)10项通过，补证只关联原HTTP回执，新增业务/模型均0；自然4h/6h、未选择网络查询、未接来源和D5/D6不据此验收 |
| D2实际边界 | 本机隔离PG/真实Redis任务入口/当前真实模型；4告警、1任务/Run/结果、17步骤47工件。50次ASGI GET逐值一致，GET前后19表摘要不变，运行槽释放。未重投Kafka/A/I，未验21 TCP/4177；本机静态记录新增1条至44条，现网展示保持。验证脚本的旧结构/别名假设失败保留，修验同Run未再生成 |
| D3实际边界 | 本机隔离PG/Redis新任务，3次受控回放、0真实模型生成：C3 length保留summary+4成员+F1，半F2不进入下游；空白补答不覆盖初答，C6收到F1后保存accepted/uncertain/partial。4页步骤/9页工件目录找到16/44，再经content_url逐值读回，60 GET全200。静态新增1条至45条，原44条逐值保留；未接新21/4177页面 |
| D4a实际边界 | 本机隔离PG/Redis，4告警及1事件；真实A输出348/I输出3101tokens、均stop，共8475tokens。受控I保留首成员、I空答none、A保留verdict/confidence/rationale但缺evidence_ids不可用；同输入失败未覆盖旧可用I。129直接/53独立接收/92独立保存读取通过；最终77GET/45原件/5回执同源，13表读取前后不变。源码164文件不变，专用模型转发已关闭；未跑Case、未验新21/TCP/4177 |
| D4b实际边界 | 本机隔离PG的完整/partial/none依赖组件，0新模型/HTTP/Redis派发。partial实证4总/3选/1成员分析、Case完整4成员；3选是受控派生，未向模型发送。最终complete08/readback02、partial02/none01/readback01核对C1及源I原件；17表只读摘要不变、组件Run均failed/component_capture_only且无在途。末补前complete07与夹具失败保留；当前源码补验和独立复核见[D4b](docs/operations/evidence/incident-signal-d4b-20261116-01/README.md)。[协调核对](docs/operations/evidence/incident-signal-d4b-20261116-01/root-handoff-validation.json)已保存。未跑C3/C6模型或保存Result，静态46条保持 |
| D4c实际边界 | 本机新隔离租户4告警/1事件/1Case；8task、6Run、46步骤、134工件、2Results。A1/I1前缀及I2空答由本批真实stop原答注入，不能称自然截断；Case R1含Deep，R2按计划仅人工后续。两轮均accepted/uncertain/partial，当前I2 none不回退旧I1，R2比较本案R1；两次check无Run/调用，周期checker使用显式next_check_at时钟。196 ASGI GET、25表读前后摘要一致，9真实调用、69015tokens，0在途。未重投Kafka、未验ASGI POST/21 TCP/真实4或6小时等待/厂商查询；[输入输出](docs/operations/evidence/ai-case-chain-d4c-20261116-01/model-io/index.json)及[静态导入](docs/operations/evidence/ai-case-chain-d4c-20261116-01/static-verification.json)可读，未验新4177浏览器 |
| D5a本机未完 | [本机收尾](docs/operations/evidence/deep-unit-continuation-d5a-20261117-01/README.md)保留68相关检查和独立10切点通过；唯一真实批3调用均stop，但驱动切点错误使收到的Deep答案为空，只验证了无可用答案仍继续C6。原目标失败不改写；同Run69 ASGI GET/25表只读核对通过，有效答案进入C6的真实PG联验及独立存取复核未完成。无新调用/Run，专用隧道已关闭、运行槽0；未部署或更新4177 |
| 知识与查询 | 活动测试知识向量已清空；新材料仅有资产事实与两份技术指导，未重新索引。UEBA/graph/产品来源未接入仍未接入；页面按真实原因展示跳过，不伪造查询结果。知识自动维护第10步后置 |

## 已交付与保留结论

第1–7步及F1–F5已完成本机程序/HTTP联验；[完整测试规划](openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md)、[当前任务](openspec/changes/schedule-streaming-investigation-updates/tasks.md)是唯一实施入口。

历史 S01/Case 首轮、S04 原3000/length失败与预算续验保留原适用时点。[S04续验](docs/operations/evidence/streaming-budget-20261116-01/README.md)当时完成新I、整事件Case自动扩到4成员和第二轮，119项保存核对、48GET及上一轮身份/链接通过；单案保持1成员/1轮。原首轮10项引用问题、C3局部校验及后轮C6两项问题未修复，正文未全面通过。数据库清空不重写这些历史结论，也不能再从当前正式库直接查询旧UUID。

W1–W4的账本/代理/浏览器/独立包证据保持；W5按用户要求恢复执行主线、真实HTTP接入、每轮任务/组件/原答和具体领域，紫色标识测试。清理前样本的功能预览与旧版本读取证据保留；最终0.6.0包10项、页面状态14项及真实4177的10GET/浏览器空态通过，旧批次不回灌。该步不替代模型质量或完整change结束审计。

[阶段一七步交付](openspec/changes/complete-socai2-investigation-chain/stage1-problems-and-plan-20261114.md)的本机验收及历史发布依据保留；RV12同Run结论、C3初答/补答/合并、大原件与当前有效性展示已经过对应本地证据验证。正式统一业务发布仍需按该阶段和流式change范围核清，不以独立4177发布代替。

HTTP侧R1统一目录、R3/R4完整步骤/工件、分析任务、A自动分诊、I异步提交、Case分配/首轮/后轮及比较身份的已验边界见[前后端交接](FRONTEND_BACKEND_HANDOFF.md)。普通管理、评论、附件引用、CSV、归并统计、采用、故事、候选与探索等原交付不重新列缺口；AI对话、真实响应和产品页面接线保持各自未完成边界。告警字段合同未改变。

## 未完项与下一步

C173 页面跳转及 HTTP 入参示例由我方交付。产品联调请业务后端确认人员目录与 `owner_id` 映射、资产源及详情入口、联调环境和脱敏样例。按上游直写我方 Kafka 的接入方案，当前确认过渡转发在运行，正式直写待联验。对方需确认发送环境、事件身份、首批范围和切换边界。[双方交接清单](docs/integration/c173-backend-handoff-20261121.md)

1. 工作台任务1/2、验收脚本3a–3d已完成各自直接验收和限定独审，现已发布21。任务4按§12.14完成4a准备、4c发布/清理/准入及4d本次两段正常链；[测试独审](docs/operations/evidence/acceptance-fullflow-21-20261117-01/independent-test-review.json)与[HTTP独审](docs/operations/evidence/acceptance-fullflow-21-20261117-01/independent-http-review.json)通过。4b来源识别子步已按[§12.15](openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md#1215-4b当前子步按lyc来源直接识别测试材料2026-11-17)完成本机验证和限定独审；直接读取冻结来源替代紫色标识对账本的依赖，辅助账本未改为自动发布。报告指定主体/Run子步现按§12.16完成本机验收和限定复核，4b本机功能收口后，现按§12.17完成21分阶段发布与实际报告/页面/原件读回，测试模块跟进限定复核。新报告32个本地链接及6HTTP链接通过，临时预览已关闭，0新模型。D5a有效Deep答案进入C6的真实PG联验、D5b/c及D6另按原设计继续，本批不核销。
2. 第11步完整覆盖核对、交接及未参与实现者的结束审计仍待。第8–9步人工定向/手动综合与第10步知识后台维护后置；不提前勾整体2.2–2.7或归档。本次D1–D4c分阶段发布已获用户明确授权并执行；不等于整个change完成。2026-11-17 批次的部署与 Git 同步各有独立回执。
3. 模型引用、范围和正文质量按负责人决定后置，保留原答与 `NOT_PASSED`，不追加采样追求通过。程序身份、材料、保存/读取阻断仍需直接修正。[问题清单](docs/investigation/current-issues.md)
4. [内部可信HTTPchange](openspec/changes/trust-internal-investigation-http/tasks.md)保持其已完成本地交付与未完成统一发布/独审边界，不因候选无鉴权已运行就单独核销。

当前配置入口为[全模块部署](deploy/README.md)、[配置索引](docs/operations/configuration.md)、[SSH接入](docs/operations/mac-ssh-relay-20261107.md)。PG普通密码/TLS require及原预算/字段合同沿已验配置；不恢复旧CA必填或旧工作台SQL取数旁路。清理前完整根文档见[历史快照](docs/handoff/history/2026-11-16-test-data-reset/README.md)，早期资料沿[历史索引](docs/handoff/history/README.md)追溯。
