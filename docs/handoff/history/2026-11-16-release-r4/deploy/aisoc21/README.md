# 21部署：当前目标与统一交付

2026-11-16。全模块说明从[部署总入口](../README.md)进入，参数从[配置索引](../../docs/operations/configuration.md)进入。本页只给当前目标与操作顺序，旧批次的prepare/start、单A/单A-I部署和已结束清单不作为新操作路径。

## 当前目标

告警先保存后异步分诊，事件诊断和Case首轮/更新共用唯一A/I/Case调度器；HTTP提供异步受理及task/Run/结果/原件读取，当前源码80操作。第8–10步后置。PostgreSQL连接按负责人确认使用账号密码，无客户端CA/证书/私钥要求，目标模板默认`sslmode=require`；Kafka保持其所选TLS配置。

[本批identity](streaming-candidate-20261115-01/identity.json)明确候选目录、租户/actor、数据库/角色及HTTP端口；它不是已创建资源的证明。候选核心由[processing-build.toml](streaming-candidate-20261115-01/processing-build.toml)和[transport.json](streaming-candidate-20261115-01/transport.json)冻结。HTTP由[唯一部署入口](../http-service/README.md)冻结完整HTTP和共享核心，不拿增量片段代替全包。

当前候选已实际供给独立PG/普通账号、Kafka/Fusion/Redis/湖、真实模型及Case知识来源；S01首轮和原S04的3000/length失败记录保持。本轮[预算与S04续验](../../docs/operations/evidence/streaming-budget-20261116-01/README.md)已完成新I及整事件Case自动第二轮、4成员跟随、比较身份/链接与保存读取；模型质量仍未通过。两份当前policy已调高输出/总预算，候选analysis.json及私密env补齐输入保护额度1 MiB。当前同名调度容器为替代容器、状态created未启动；原实际执行容器改名保留并exited，镜像/资源/挂载/命令及其他环境值保持。禁止同时启动保留容器，当前身份以[最终加载回执](../../docs/operations/evidence/streaming-budget-20261116-01/input-guard-finish-01.json)为准。负责人先前暂停的9个旧业务容器继续停止，共享依赖保留；未统一正式发布，W4/W5及完整change独审仍待，见[PROGRESS](../../PROGRESS.md)。

[W2实际只读核验](../../docs/operations/evidence/streaming-w2-readonly-20261115-01/README.md)已通过：本机临时测试服务经SSH访问当前21候选，34个GET/107项断言及HTTP离线交接完成，原3成员诊断来源没有按当前4成员扩大。沿0.2.0和当前80操作/55GET，未改21服务或配置、未新增业务写入或模型请求；临时服务/隧道已停止。此结果不表示21已部署测试服务，当前4177未切换；后续[W3页面](../../docs/operations/evidence/streaming-w3-viewer-20261115-01/README.md)已本机实现及联验：独立测试服务/页面0.3.0从HTTP取得批次/任务/Run/原件，26业务和14账本GET通过，临时58808/58809停止。页面配置详见[测试服务部署说明](../investigation-test/README.md)，此次不部署21或切换4177。下一步为W4完整包及验证安排，S04正向更新/比较和完整验收/独审条件仍待。

## 本轮执行顺序

1. **配置与依赖。** 按[处理链参数](../../docs/operations/deployment-processing.md)、[数据库](../../docs/operations/deployment-datastores.md)、[模型](../../docs/operations/deployment-models.md)、[HTTP配置](../http-service/CONFIGURATION.md)确认目标。部署必填值按本环境填写，其他保留当前模板；秘密另存受控文件。
2. **数据库。** 新独立空库用`install_reader.py initialize-current --profile <所选文件>`；已有库只应用缺少的128/129等增量，再`verify`。具体顺序见[CURRENT](../database/CURRENT.md)。不清正式库，不把旧安装脚本当新空库入口。
3. **完整包。** `prepare_processing_release.py --profile <本批build>`冻结源码、策略和摘要；`rollout_transport.py --config <本批transport> processing upload`及`processing build`只准备候选镜像。HTTP按自己的完整包入口执行。源码变化须新批冻结，不覆盖结束回执。
4. **候选装配。** 根据实际库/普通账号、入站Topic/group、Redis namespace、湖/知识/模型来源填运行profile，启动明确候选服务。本批实际运行资源已按显式profile供给，后续以当前回执和加载摘要核对；不重新执行准备步骤或使用旧正式runtime文件替代候选。
5. **实际验收。** 从Kafka投放本批材料，核告警持久化、事件关联及上下文路由、A/I真实结果、HTTP建Case、首轮/更新/上一轮比较，并同批读取任务、Run及原件。用测试服务/查阅展示实际结果，失败和模型NOT_PASSED如实保留。
6. **统一正式发布。** 直接验收、HTTP/测试交接和未参与实现者结束审计通过后，生成并冻结本轮完整发布清单，一次更新获准服务；核实际镜像、配置、迁移、HTTP/Swagger/4177并读回。当前`current-rollout.json`记录旧发布，不直接重放。

整个顺序沿[第11步设计](../../openspec/changes/schedule-streaming-investigation-updates/stage11-candidate-design-20261115.md)，不另建任务树。候选镜像构建不等于正式发布，health不等于业务通过，静态页面上传不等于真实模型正确。

## 持久数据与回退

保留数据库、Kafka位点、Redis独立范围、湖记录和Run原件。源码/策略/CA（仅需要证书的其他连接）只读挂载，回执和状态目录按用途持久可写；不要把数据库放有容量限制的tmpfs。各数据库备份及实际挂载见[存储手册](../../docs/operations/deployment-datastores.md)。

应用回退使用本轮发布器保存的上一镜像与profile，按实际任务状态正常收尾后切换，不删除新结果、不重派旧批次、不降级DDL消除新记录。发布器的具体目标服务和回退清单需在候选验收后冻结，当前不假装已有一份可直接执行的最终清单。

整理前部署说明按原字节保存在[历史快照](../../docs/handoff/history/2026-11-15-deployment-docs/README.md)，只供追溯。历史模型、知识或工作台发布结论保持其原范围，不替代本轮新配置的加载与验收。
