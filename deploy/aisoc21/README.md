# 21部署：当前运行与统一交付

2026-11-17。负责人明确要求“先部署到21 清除历史数据 然后再测试数据”。[acceptance-release-20261117-01](acceptance-release-20261117-01/release.json)已完成完整服务发布、受控备份与明确历史清理；[实际就绪](../../docs/operations/evidence/acceptance-release-20261117-01/deployment-ready.json)核五服务、源码/配置、合同和空态。后端采用3c.2真实正常两段所验的完整组合，工作台1/2及3a–3d入口已发布。[新两段测试](../../docs/operations/evidence/acceptance-fullflow-21-20261117-01/README.md)已完成：2告警/3上下文、同事件/同Case两轮、477份HTTP回执和8次真实模型均stop。5项模型质量问题后置；4b后续按明确指令已[发布0.6.1/r8与验收工具并验实际链接](../../docs/operations/evidence/workbench-4b-release-20261117-01/README.md)，仅更新4177，不再清理或发告警。D5a异常存取及整个change不据此核销。

## 当前资源

| 服务 | 当前实际入口 |
| --- | --- |
| PostgreSQL | aisoc，32表521列，普通密码及TLS require；本轮无迁移 |
| 入站/处理 | socai2-production-fusion-20261117-r1、socai2-production-dispatch-20261117-r1，同一processing镜像、N=1 |
| HTTP | [18024](http://192.168.1.21:18024)，socai2-production-http-acceptance-http-20261117-r1，80业务操作，无鉴权 |
| Swagger | [18080](http://192.168.1.21:18080/)，同版合同及告警/事件/调查三组 |
| 查阅 | [4177](http://127.0.0.1:4177/viewer/)，21的0.6.1/r8容器，经本机SSH隧道访问 |

发布位于21 `/opt/sting-aisoc-socai2/deployments/acceptance-release-20261117-01`。连接、凭据和处理挂载明确沿用release中的prior_runtime_root，没有静默改库或加载旧候选短周期配置。I4h、Case6h、7天窗口及65536上下文预算保持，详见[配置索引](../../docs/operations/configuration.md)。旧消费者、旧r3和旧HTTP/展示入口停止，禁止同时恢复。

## 本轮执行顺序

1. 按[OpenSpec §12.14](../../openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md#1214-负责人明确要求先发布21清历史再测试2026-11-17)冻结来源。完整HTTP730来源、处理742包文件；670共有runtime逐字相同，286份API/Fusion与3c.2已验冻结一致；同包HTTP80操作/181schemas未变。
2. 新包上传和镜像构建期间旧服务保持。处理镜像禁网自检、新4177及3d04验收镜像原生amd64内容核对通过；未触发业务/模型。
3. 核无在途任务及待写回执后停止旧五服务，沿[精确清理清单](acceptance-release-20261117-01/cleanup-scope.json)备份并清理：84业务表521行、湖15条、Redis13键、4Topic25消息、24账本文件核零；127未选表和Schema不变。
4. 启动唯一新版HTTP、调度、Fusion、Swagger及4177，核处理741运行文件（含策略）、HTTP730来源、三类业务/账本空态。新工作台浏览器默认Case空态通过。
5. 最终3d04容器准入后，由协调方在确认尚未发送并保存接管回执后作为唯一执行者完成run首段→检查点→只读TTL→append。测试模块与HTTP模块限定独审通过；同一整事件Case实际1→2成员，R2比较真实R1，8次模型调用均stop。4177三类主体/两轮/HTTP/领域/原答及5项问题已核；随后4b已完成新验收工具/工作台发布；最终报告精确首轮/后轮链接和按冻结来源显示紫色通过实际4177浏览器及26GET核对。

[本轮操作与备份](../../docs/operations/evidence/acceptance-release-20261117-01/README.md)保留清理、发布、首次核对失败及修正回执。不得直接重放此批清理或重发已执行段。数据库新装/升级见[CURRENT](../database/CURRENT.md)，本轮无迁移。清理前部署说明见[历史快照](../../docs/handoff/history/2026-11-17-acceptance-release/deploy/aisoc21/README.md)。

## 回退边界

旧包、容器和受控备份保留。本轮已产生新C1/Run/Result，不适用“无新业务写入”的直接应用回退前提；仍保持单一执行入口，不自动恢复已清历史或重放Kafka。

新版C1含analysis_material，旧r3 Context Schema已实证拒绝该字段。产生新C1/Run后，不直接回退旧核心或HTTP；保留新读侧及记录，暂停新工作后修复当前版本。不能删新字段、改写Run、降级DDL或并行启动旧消费者。

总体状态见[PROGRESS](../../PROGRESS.md)，发布前文档见[历史快照](../../docs/handoff/history/2026-11-16-release-r4/deploy/aisoc21/README.md)。本次不含Git提交、推送或整个change归档。
