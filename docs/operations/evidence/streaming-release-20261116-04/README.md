# 21 完整服务发布与历史业务清理

2026-11-16。负责人明确要求“部署完整服务并清除历史数据，跑完整的测试”。按现有 OpenSpec [§12](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-output-continuation-design-20261116.md#12-d1d4c发布21及新kafka整链验收2026-11-16)执行本次分阶段发布；D1–D4c已部署，D5/D6整体及change结束审计没有据此核销。没有提交、推送或归档。

## 已完成的发布和清理

| 项目 | 实际结果 |
| --- | --- |
| 正式目标 | 21，`aisoc`，32表521列；本次无迁移、无字段合同变化 |
| 处理服务 | `processing-20261116-r4`，Fusion与唯一联合调度器均运行；镜像`a820fc793fa1` |
| HTTP | `streaming-http-20261116-r4`，完整729来源文件，80个操作，无鉴权；镜像`f2dd49cd5ca5`，18024 |
| Swagger | 新r4容器、同版80操作/告警事件调查三组，18080；合同及浏览器CORS核对通过 |
| 4177 | 复用已验证0.6.0镜像，新r6容器和r4显式配置，经本机隧道访问；业务上游18024；历史账本已清空，当前新02及同一执行展示补证已发布 |
| 运行核对 | 740个处理运行文件（含挂载policy）、729个HTTP文件匹配冻结包；三份模型输入JSON与C1 Schema均已核对 |
| 停写 | 停止前后task/Run/attempt均无在途，待写completion为0；旧消费者、调度器和旧展示入口保持停止 |
| PostgreSQL | 明确列出的84张业务表共505行清空并核零；127张未选表内容摘要不变，Schema不变 |
| 湖/缓存/消息 | `aisoc.raw_events`16行、11个业务Redis键、4个指定Kafka Topic共26条保留消息清除；Topic/分区及其他命名空间保留 |
| 知识与展示 | 4个本项目向量集合原本均为0，配置保持；活动4177账本8文件清除 |
| 备份 | 21 `/opt/sting-aisoc-socai2/private/streaming-release-20261116-04-cleanup`，离线受控；原模型答复与旧失败也留在本机历史证据 |

清理对象包括当前正式租户的告警、事件、Case、任务、Run、结果及工具材料，另含已确认属于socai2早期测试租户的4条身份/情报材料。保留账号、租户、连接器配置、权限、凭据、规则、迁移及安全审计；与租户技能配置关联的回测评价保留，不属于本次调查Run。没有清空全库、删除卷或操作其他项目。

[清理范围](../../../../deploy/aisoc21/streaming-release-20261116-04/cleanup-scope.json)、[停写回执](stop-services-02.json)、[逐步清理](cleanup-execution-01.jsonl)、[核零汇总](cleanup-zero.json)、[实际发布就绪](deployment-ready.json)、[HTTP版本与合同](http-start-01.json)。初次停写预检误用了attempt的旧列名，在任何启停前退出；按实际迁移改用`local_state`后重新检查通过，失败记录保留。预检01/02的失败输出不作成功证据。

## 新批完整流程

新批为[streaming-fullflow-20261116-02](../streaming-fullflow-20261116-02/README.md)，测试模块取得上述核零和就绪回执后唯一执行。北京时间11月17日用户确认中转恢复后，先核远端out、发送意图、发送器及湖/库，确认上次失败未进入远端发送，再完成唯一投放；未重新部署或清理。原[连接中断记录](connectivity-interruption-01.json)和失败回执保留，[恢复回执](connectivity-restored-01.json)记录SSH及4177实际读回。

新02业务链已通过：[最终验收](../streaming-fullflow-20261116-02/final-validation.json)记录13上下文/4告警真实入站、4A/2I/3Case Run；整事件Case从3扩至4成员并完成R2，单案保持1成员1轮。10task、9attempt/Run、77步骤、228工件、3Results；no_changes新增0attempt/Run/模型，旧Run/原件逐值保持。318次正式HTTP GET与快照一致，读取前后23张本批表不变。14次模型全部stop、111169tokens，原输入输出保存；19条引用/展示诊断保留，三结果均accepted/uncertain/partial，正文未全面通过。4177正常流程展示与同包复核已通过，不能把正常业务链通过当异常覆盖或完整change完成。

[4177浏览器复验](../streaming-fullflow-20261116-02/viewer-browser-02.json)10项通过：两案首轮POST201、整案后轮check202分别关联自身任务；整案首轮3成员/后轮4成员与单案1成员不混用，具体领域、查询跳过原因、C6原答和上一轮比较可读。首次账本漏接`http-exchanges`的[失败回执](../streaming-fullflow-20261116-02/viewer-browser-01.json)保留；终态批次不可改写，沿既有合同发布“完整调查流程02 · 补齐HTTP接入展示（同一执行）”，原02全部11文件摘要不变。补证[36次GET](../streaming-fullflow-20261116-02/viewer-display-readback-01.json)及10份证据读回通过，新增业务、Kafka和模型调用均0。[最终交付回执](../streaming-fullflow-20261116-02/delivery-receipt.json)绑定本批业务、独立复核和页面证据。

本机[静态导入](../streaming-fullflow-20261116-02/static-verification.json)已47→49，原47条保持、382本地链接无缺失，旧静态未回灌21。[并发核对](dispatch-concurrency-review-02.json)实读21配置max_running_tasks=1及共享状态锁挂载，最终9次执行尝试的并发峰值为1；该限额依赖当前单调度器，Redis为运行索引，未实现跨主机全局容量抢占。

预算保持窗口65536，A/I/Deep输出8192、C3/C6输出16384，A/I/Case每Run总预算131072/131072/393216，输入保护1MiB；I4小时、Case6小时及7天窗口不变。增量验收用正式HTTP `mode=check`，不冒称真实周期等待已验。质量问题只登记，保留原答并继续合法下游。

[调查同包复核02](../streaming-fullflow-20261116-02/core-final-bundle-review-02.json)12组/67项与[HTTP同包复核](../streaming-fullflow-20261116-02/http-final-bundle-review-01.json)16组通过。Run目录实际224份工件，另4份无Run的Fusion入站快照只在PG快照核对；初审误以228作Run目录分母的记录保留于01，02按实际Run身份集合纠正。没有为此重跑业务或补造读取证据。该复核不替代整个change未参与实现者的结束审计。

新版C1含`analysis_material`。新业务写入后不得直接切回旧r3核心/HTTP；发生阻断时保留新版读侧和记录，停止新派发后定向修复。历史业务数据不会随应用回退自动恢复或重放。
