# 当前进度

更新于2026-11-17。**任务4a新材料准备和21只读核对已通过直接验证及测试模块限定独审。** [本步记录](docs/operations/evidence/acceptance-fullflow-20261117-01/README.md)包含新进程活动→后续外联场景：两段各1条告警，首段2条父子进程上下文、后段1条网络上下文，只计划1个整事件Case。已交付3d04镜像在禁网环境完成inspect/prepare/status/session EOF/report，原值、关系、摘要和持久读回通过；两个part仍未发送，0新业务写入/模型。21健康、来源登记和新ID/关联范围未占用已核，实际仍processing/HTTP r4和4177 r6，缺本机C1修正及新页面，`ready_to_execute=false`。下一步4b报告精确轮次链接与紫色来源接线，其后4c统一版本/容器连通准入、4d首段和显式追加；不能把本轮准备通过当真实整链或新版本已发布。

3a–3d已完成本机直接验收及限定独审。[3d最终独审](docs/operations/evidence/acceptance-docker-20261117-01/independent-runtime-review-01.json)通过，Python3.11.17/linux-amd64和19依赖、109包文件、32冻结文件及只读挂载/持久重开均已核；[操作指南](deploy/investigation-test/acceptance-docker.md)可用，本轮未改这32份冻结文件。历史3c.2的02仍13保存请求109995tokens、17质量诊断/16步骤问题，01仍503/incomplete及统计未知。

21继续运行已发布D1–D4c的processing/HTTP r4和4177 r6旧布局；[上批完整链02](docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json)的4告警、1事件、2Case及两轮结果和19条质量问题保持原结论，不与3c.2两段02混称。3c.1已独立通过；3c.2直接验收与独立结束复核均通过，3c.3分步实现、直接验证、交接及限定独审已通过；3d两步及最终限定独审已通过；任务4a直接验证与限定独审通过，4b–4d未实施。D5a已有本机修改及有限验证单独保留；D5/D6整体、主31/41、流式2/11与后置8–10不核销。分支V1.1，change未归档。

## 当前运行和数据

| 内容 | 当前实际状态与证据 |
| --- | --- |
| 当前已发布版本 | 既有r4发布已通过，新候选尚未发布：processing r4与HTTP r4来自同一当前源码，公共HTTP合同保持80操作；Swagger r4和4177 r6已接正式18024。[实际就绪](docs/operations/evidence/streaming-release-20261116-04/deployment-ready.json) |
| 日常展示 | [4177](http://127.0.0.1:4177/viewer/)为21的0.6.0只读服务，经本机SSH隧道访问；r4环境/上游和清理后空态已验。新02批及同一执行展示补证已发布，浏览器10项通过；补证保留原终态账本，旧历史账本不回灌 |
| 本轮需求落点 | 3c.2显式append及同Case两轮已通过真实本机直接验收；[结果与问题](docs/operations/evidence/acceptance-append-20261117-02/final-validation.json)、[原答](docs/operations/evidence/acceptance-append-20261117-02/model-io/index.json)保留。13次均stop、109995tokens，四Result为accepted/uncertain/partial，C6九项引用诊断后置。01另2次4013tokens，两批总15次114008tokens。静态51→53且旧记录/页面不变；本轮服务和专用转发已停，数据保留。独立结束复核已通过；3c.3原件汇总及交互已交付，未发布21或新4177 |
| 历史数据清理 | 本轮仅21明确清单：84业务表505行、1湖表16行、11缓存键、4Topic共26条消息和8账本文件核零，4向量集合原为0；127其他表逐值摘要及Schema不变。[本轮核零](docs/operations/evidence/streaming-release-20261116-04/cleanup-zero.json)。此前本机/21大范围清理只属[旧批证据](docs/operations/evidence/test-data-reset-20261116-01/README.md) |
| 业务服务 | 唯一r4 Fusion/联合调度运行，HTTP18024、Swagger18080、4177均就绪；旧r3与其他旧执行入口停止。新02唯一投放与完整业务链已通过；实际任务并发上限1，9执行尝试峰值1；I4h/Case6h及7天窗口不改，增量采用显式HTTP check，不冒称自然周期已验 |
| 其他入口 | 临时预览 58477/58479 已关闭；本机 4173 旧静态演示已停止。旧源码、包/容器、模型原答及审计回执保留离线，不作为活动输入。旧库清理备份在本机/21 私密目录，不进入模型或索引 |
| 数据库合同 | 正式 `aisoc.socai2` 已通过128/129增量和verify，当前32表521列；候选 `socai2_streaming_20261115` 仍32表521列。本机旧库保持其原schema。清理不改字段合同、迁移、账号/凭据及其他项目。[结构入口](deploy/database/CURRENT.md) |
| 模型容量 | 实际服务窗口 65536；A/I/Deep 输出8192、C3/C6输出16384，A/I每 Run 总预算各131072、Case393216，输入准备1 MiB。沿[已验预算配置](docs/operations/evidence/streaming-budget-20261116-01/README.md)，D1–D4c及本次r4发布未改这些预算；D2真实调用3次，D3为受控回放0次新生成，D4a新增真实A/I各1次；D4b新增0次；D4c真实9次、69015tokens，注入不重复计费 |
| 输出兼容修正 | xgrammar兼容及D1–D4c已随当前r4统一发布；下列各本机回执保持原验证范围。D2本机将六类缺说明改为独立诊断，程序还原1218字原观察不再受模型正文1200字限误拒收；真实3次stop、C6两项缺说明保留。D3本机C3支持完整JSON length与闭合单元恢复，最多一次补答，不丢初答；原失败不变、质量未全面通过。D4a本机A/I已保存完整、partial/none回执；D4b事件终结材料选择、Case门控/分配/C1冻结已通过，D4c已验partial/none→同Case两轮完整链，其他模型阶段/网络异常待D5 |
| 新测试材料 | D1输入过滤已随r4发布，后台tenant/告警/来源关系保留。新02的4告警/13上下文及15份离线模型视图已核无测试批次/答案/tenant_uid，14份真实请求也已核无禁入标记；r3旧16份残留与所有原答保持历史结论 |
| 新02完整真实链 | 21 Kafka入站13上下文/4告警，4A/2I/3Case Run；10task、9attempt/Run、77步骤、228工件、3Results，全部Case结果accepted/uncertain/partial。整案3→4且R2比较实际R1，单案保持1轮；no_changes 0新attempt/Run/模型。14真实调用均stop、111169tokens，318GET读取前后23表不变；19条诊断后置，正文未全面通过。[最终验收](docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json)、[输入输出](docs/operations/evidence/streaming-fullflow-20261116-02/model-io/index.json)、[本机静态](docs/operations/evidence/streaming-fullflow-20261116-02/static-verification.json)、[并发核对](docs/operations/evidence/streaming-release-20261116-04/dispatch-concurrency-review-02.json)。[实际4177浏览器](docs/operations/evidence/streaming-fullflow-20261116-02/viewer-browser-02.json)10项通过，补证只关联原HTTP回执，新增业务/模型均0；自然4h/6h、未选择网络查询、未接来源和D5/D6不据此验收 |
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

1. 按[统一需求§12.11](openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md#1211-3c会话读回显式追加与报告2026-11-17)逐步推进：3c.1已收口；3c.2实现、本机真实两段验收与独立结束复核已收口，3c.3实现、直接验证、交接和限定独审已收口；3d镜像/依赖、容器挂载、交接与限定独审已收口；[任务4整体设计§12.13](openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md#1213-任务4整体安排与4a材料环境核对2026-11-17)已明确4a→4b→4c→4d；4a材料和当前21只读核对直接验证及限定独审通过，下一步4b最小展示接线，4c统一目标版本及最终容器连通后才进入4d真实两段。21单段02原Case失败不改写，恢复及TCP/4177随既定统一发布验证，不逐小修替换21。D5a保持已有未完边界，D5b/c及D6不据本次正常Deep调用核销。
2. 第11步完整覆盖核对、交接及未参与实现者的结束审计仍待。第8–9步人工定向/手动综合与第10步知识后台维护后置；不提前勾整体2.2–2.7或归档。本次D1–D4c分阶段发布已获用户明确授权并执行；不等于整个change完成或Git同步授权，本轮没有提交推送。
3. 模型引用、范围和正文质量按负责人决定后置，保留原答与 `NOT_PASSED`，不追加采样追求通过。程序身份、材料、保存/读取阻断仍需直接修正。[问题清单](docs/investigation/current-issues.md)
4. [内部可信HTTPchange](openspec/changes/trust-internal-investigation-http/tasks.md)保持其已完成本地交付与未完成统一发布/独审边界，不因候选无鉴权已运行就单独核销。

当前配置入口为[全模块部署](deploy/README.md)、[配置索引](docs/operations/configuration.md)、[SSH接入](docs/operations/mac-ssh-relay-20261107.md)。PG普通密码/TLS require及原预算/字段合同沿已验配置；不恢复旧CA必填或旧工作台SQL取数旁路。清理前完整根文档见[历史快照](docs/handoff/history/2026-11-16-test-data-reset/README.md)，早期资料沿[历史索引](docs/handoff/history/README.md)追溯。
