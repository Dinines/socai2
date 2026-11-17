# 当前进度

更新于 2026-11-16。**D1–D3、D4a/b及[D4c完整任务链](docs/operations/evidence/ai-case-chain-d4c-20261116-01/README.md)已完成本机执行与直接验证。** D4c使用新隔离PG/Redis和当前真实模型，9次调用均stop、共69015tokens；3处受控截断/空答注入另存完整原答。A不可用仍推进I，I partial/none分别推进同一Case两轮C1–C6；两Result均accepted/uncertain/partial，前轮身份及无变化不重复执行已核。196次ASGI GET与25表快照一致，227份源码/配置不变，运行槽已释放；独立复核见本批回执。9份实际模型输入无tenant_uid及测试执行身份，后台原件/关联保留。两轮正文均把05:50流量说成早于05:46进程，4项引用诊断另记，模型质量不算通过。本机静态46→47且旧记录逐值保持；实时4177及21仍旧版本。下一步D5，D6页面随后，主31/41、流式2/11、后置8–10保持；未归档、部署或提交推送，分支V1.1。

## 当前运行和数据

| 内容 | 当前实际状态与证据 |
| --- | --- |
| 发布准备 | 必要修正统一为processing r3，独立审计及包/镜像核对通过；仅替换Fusion/联合调度，HTTP/Swagger/4177复用r2接线。新链回执见[本批](docs/operations/evidence/streaming-fullflow-20261116-01/README.md)；32表521列及普通账号/TLS合同保持 |
| 日常展示 | [4177](http://127.0.0.1:4177/viewer/) 为21的0.6.0只读服务，经本机隧道访问；新增“登录、进程与外联：首轮及增量调查”revision1。首轮/后轮各自HTTP受理、3/4冻结范围、C6原答字节一致，领域和跳过原因可见。[页面核对](docs/operations/evidence/streaming-fullflow-20261116-01/viewer-verification.json) |
| 历史数据清理 | 负责人在明确共享 aisoc 整表范围后授权执行。本机与 21 共 18 数据库、635 张选定业务表、106415 行清空并核零；表结构保持。4 湖表、8 向量集合、socai2 Topic、选定缓存和 4177 活动账本一并清理。[范围与逐步回执](docs/operations/evidence/test-data-reset-20261116-01/README.md) |
| 业务服务 | 21新r3 Fusion和联合调度运行，旧r2处理容器与旧执行入口保持停止；18024/18080/4177继续现版本。最新批次10task/9Run/80步骤/225工件，最后观察0在途；I4h/Case6h到时分支未等到，本批增量由显式HTTP check触发，不冒称自动周期已验 |
| 其他入口 | 临时预览 58477 已关闭；本机 4173 旧静态演示已停止。旧源码、包/容器、模型原答及审计回执保留离线，不作为活动输入。旧库清理备份在本机/21 私密目录，不进入模型或索引 |
| 数据库合同 | 正式 `aisoc.socai2` 已通过128/129增量和verify，当前32表521列；候选 `socai2_streaming_20261115` 仍32表521列。本机旧库保持其原schema。清理不改字段合同、迁移、账号/凭据及其他项目。[结构入口](deploy/database/CURRENT.md) |
| 模型容量 | 实际服务窗口 65536；A/I/Deep 输出8192、C3/C6输出16384，A/I每 Run 总预算各131072、Case393216，输入准备1 MiB。沿[已验预算配置](docs/operations/evidence/streaming-budget-20261116-01/README.md)，D1–D4b未改这些预算；D2真实调用3次，D3为受控回放0次新生成，D4a新增真实A/I各1次；D4b新增0次；D4c真实9次、69015tokens，注入不重复计费 |
| 输出兼容修正 | xgrammar兼容修正已发布r3。D2本机将六类缺说明改为独立诊断，程序还原1218字原观察不再受模型正文1200字限误拒收；真实3次stop、C6两项缺说明保留。D3本机C3支持完整JSON length与闭合单元恢复，最多一次补答，不丢初答；原失败不变、质量未全面通过。D4a本机A/I已保存完整、partial/none回执；D4b事件终结材料选择、Case门控/分配/C1冻结已通过，D4c已验partial/none→同Case两轮完整链，其他模型阶段/网络异常待D5 |
| 新测试材料 | r3旧批16份请求的tenant_uid残留原样保留。D1本机已排除OCSF主字段及raw_event副本，五阶段15变体和3项直接检查通过；D2新Case三份、D4c九份实际请求也无该字段，D4c无测试执行身份。原件、tenant_id/alert_id/tenant_uid与来源归属保留，业务同名字段不误删。未发布到21，不宣称历史请求或正式运行已清理。[D1](docs/operations/evidence/input-boundary-d1-20261116-01/README.md)、[D2](docs/operations/evidence/quality-continuation-d2-20261116-01/README.md) |
| D2实际边界 | 本机隔离PG/真实Redis任务入口/当前真实模型；4告警、1任务/Run/结果、17步骤47工件。50次ASGI GET逐值一致，GET前后19表摘要不变，运行槽释放。未重投Kafka/A/I，未验21 TCP/4177；本机静态记录新增1条至44条，现网展示保持。验证脚本的旧结构/别名假设失败保留，修验同Run未再生成 |
| D3实际边界 | 本机隔离PG/Redis新任务，3次受控回放、0真实模型生成：C3 length保留summary+4成员+F1，半F2不进入下游；空白补答不覆盖初答，C6收到F1后保存accepted/uncertain/partial。4页步骤/9页工件目录找到16/44，再经content_url逐值读回，60 GET全200。静态新增1条至45条，原44条逐值保留；未接新21/4177页面 |
| D4a实际边界 | 本机隔离PG/Redis，4告警及1事件；真实A输出348/I输出3101tokens、均stop，共8475tokens。受控I保留首成员、I空答none、A保留verdict/confidence/rationale但缺evidence_ids不可用；同输入失败未覆盖旧可用I。129直接/53独立接收/92独立保存读取通过；最终77GET/45原件/5回执同源，13表读取前后不变。源码164文件不变，专用模型转发已关闭；未跑Case、未验新21/TCP/4177 |
| D4b实际边界 | 本机隔离PG的完整/partial/none依赖组件，0新模型/HTTP/Redis派发。partial实证4总/3选/1成员分析、Case完整4成员；3选是受控派生，未向模型发送。最终complete08/readback02、partial02/none01/readback01核对C1及源I原件；17表只读摘要不变、组件Run均failed/component_capture_only且无在途。末补前complete07与夹具失败保留；当前源码补验和独立复核见[D4b](docs/operations/evidence/incident-signal-d4b-20261116-01/README.md)。[协调核对](docs/operations/evidence/incident-signal-d4b-20261116-01/root-handoff-validation.json)已保存。未跑C3/C6模型或保存Result，静态46条保持 |
| D4c实际边界 | 本机新隔离租户4告警/1事件/1Case；8task、6Run、46步骤、134工件、2Results。A1/I1前缀及I2空答由本批真实stop原答注入，不能称自然截断；Case R1含Deep，R2按计划仅人工后续。两轮均accepted/uncertain/partial，当前I2 none不回退旧I1，R2比较本案R1；两次check无Run/调用，周期checker使用显式next_check_at时钟。196 ASGI GET、25表读前后摘要一致，9真实调用、69015tokens，0在途。未重投Kafka、未验ASGI POST/21 TCP/真实4或6小时等待/厂商查询；[输入输出](docs/operations/evidence/ai-case-chain-d4c-20261116-01/model-io/index.json)及[静态导入](docs/operations/evidence/ai-case-chain-d4c-20261116-01/static-verification.json)可读，未验新4177浏览器 |
| 知识与查询 | 活动测试知识向量已清空；新材料仅有资产事实与两份技术指导，未重新索引。UEBA/graph/产品来源未接入仍未接入；页面按真实原因展示跳过，不伪造查询结果。知识自动维护第10步后置 |

## 已交付与保留结论

第1–7步及F1–F5已完成本机程序/HTTP联验；[完整测试规划](openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md)、[当前任务](openspec/changes/schedule-streaming-investigation-updates/tasks.md)是唯一实施入口。

历史 S01/Case 首轮、S04 原3000/length失败与预算续验保留原适用时点。[S04续验](docs/operations/evidence/streaming-budget-20261116-01/README.md)当时完成新I、整事件Case自动扩到4成员和第二轮，119项保存核对、48GET及上一轮身份/链接通过；单案保持1成员/1轮。原首轮10项引用问题、C3局部校验及后轮C6两项问题未修复，正文未全面通过。数据库清空不重写这些历史结论，也不能再从当前空库直接查询旧UUID。

W1–W4的账本/代理/浏览器/独立包证据保持；W5按用户要求恢复执行主线、真实HTTP接入、每轮任务/组件/原答和具体领域，紫色标识测试。清理前样本的功能预览与旧版本读取证据保留；最终0.6.0包10项、页面状态14项及真实4177的10GET/浏览器空态通过，旧批次不回灌。该步不替代模型质量或完整change结束审计。

[阶段一七步交付](openspec/changes/complete-socai2-investigation-chain/stage1-problems-and-plan-20261114.md)的本机验收及历史发布依据保留；RV12同Run结论、C3初答/补答/合并、大原件与当前有效性展示已经过对应本地证据验证。正式统一业务发布仍需按该阶段和流式change范围核清，不以独立4177发布代替。

HTTP侧R1统一目录、R3/R4完整步骤/工件、分析任务、A自动分诊、I异步提交、Case分配/首轮/后轮及比较身份的已验边界见[前后端交接](FRONTEND_BACKEND_HANDOFF.md)。普通管理、评论、附件引用、CSV、归并统计、采用、故事、候选与探索等原交付不重新列缺口；AI对话、真实响应和产品页面接线保持各自未完成边界。告警字段合同未改变。

## 未完项与下一步

1. 按[输出继续设计D1–D6](openspec/changes/schedule-streaming-investigation-updates/stage11-output-continuation-design-20261116.md)分步推进。D4c已完成当前真实A/I→同Case两轮的执行、保存、完整HTTP目录与静态导入；模型正文错误保留，不重采样。下一步先核D5的Deep/C6自身异常、网络异常和比较规则设计，再实施一个可直接验证的子步；D6实际4177另行推进，不同时铺开、不逐步部署。旧失败、原答与已结束批次不改写。
2. 第11步完整覆盖核对、交接及未参与实现者的结束审计仍待。第8–9步人工定向/手动综合与第10步知识后台维护后置；不提前勾整体2.2–2.7或归档。完整change通过后按既定授权统一正式发布、读回并同步Git；本轮没有提交推送。
3. 模型引用、范围和正文质量按负责人决定后置，保留原答与 `NOT_PASSED`，不追加采样追求通过。程序身份、材料、保存/读取阻断仍需直接修正。[问题清单](docs/investigation/current-issues.md)
4. [内部可信HTTPchange](openspec/changes/trust-internal-investigation-http/tasks.md)保持其已完成本地交付与未完成统一发布/独审边界，不因候选无鉴权已运行就单独核销。

当前配置入口为[全模块部署](deploy/README.md)、[配置索引](docs/operations/configuration.md)、[SSH接入](docs/operations/mac-ssh-relay-20261107.md)。PG普通密码/TLS require及原预算/字段合同沿已验配置；不恢复旧CA必填或旧工作台SQL取数旁路。清理前完整根文档见[历史快照](docs/handoff/history/2026-11-16-test-data-reset/README.md)，早期资料沿[历史索引](docs/handoff/history/README.md)追溯。
