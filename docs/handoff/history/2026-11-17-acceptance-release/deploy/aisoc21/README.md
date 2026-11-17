# 21部署：当前运行与统一交付

2026-11-16。负责人明确授权完整服务部署、清理历史业务数据和新批完整测试。D1–D4c已发布为[streaming-release-20261116-04](streaming-release-20261116-04/release.json)，[实际就绪回执](../../docs/operations/evidence/streaming-release-20261116-04/deployment-ready.json)已核运行文件、配置、合同及清理后空态。业务验收沿[新02批](../../docs/operations/evidence/streaming-fullflow-20261116-02/README.md)继续；D5/D6整体及change结束审计未核销。

## 当前资源

| 服务 | 当前实际入口 |
| --- | --- |
| PostgreSQL | aisoc，32表521列，普通密码及TLS require；本轮无迁移 |
| 入站/处理 | socai2-production-fusion-20261116-r4、socai2-production-dispatch-20261116-r4，同一processing r4镜像、N=1 |
| HTTP | [18024](http://192.168.1.21:18024)，socai2-production-http-20261116-r4，80业务操作，无鉴权 |
| Swagger | [18080](http://192.168.1.21:18080/)，同版合同及告警/事件/调查三组 |
| 查阅 | [4177](http://127.0.0.1:4177/viewer/)，21的0.6.0/r6容器，经本机SSH隧道访问 |

发布位于21 `/opt/sting-aisoc-socai2/deployments/streaming-release-20261116-04`。连接、凭据和处理挂载明确沿用release中的prior_runtime_root，没有静默改库或加载旧候选短周期配置。I4h、Case6h、7天窗口及65536上下文预算保持，详见[配置索引](../../docs/operations/configuration.md)。旧消费者、旧r3和旧HTTP/展示入口停止，禁止同时恢复。

## 本轮执行顺序

1. 先更新[OpenSpec §12](../../openspec/changes/schedule-streaming-investigation-updates/stage11-output-continuation-design-20261116.md#12-d1d4c发布21及新kafka整链验收2026-11-16)、strict及核心/HTTP只读复核，冻结当前工作树来源。
2. 用[processing build](streaming-release-20261116-04/processing-build.toml)、[transport](streaming-release-20261116-04/transport.json)和[完整HTTP profile](streaming-release-20261116-04/http-profile.json)打包、上传、构建新镜像；构建时旧服务继续运行。
3. 核无在途任务及待写回执，停止五个旧服务；按[精确清理清单](streaming-release-20261116-04/cleanup-scope.json)备份并清理。84业务表505行及对应湖/缓存/消息/账本核零，127未选表内容和Schema保持，不清全库或卷。
4. 先启动新HTTP，核80操作、版本和其他容器快照，再启动唯一新调度/Fusion、Swagger及4177。740处理运行文件和729HTTP文件与冻结包一致；三个业务列表和测试账本空态通过。
5. 两份实际回执交给测试后，由其唯一执行新Kafka批次、真实A/I及两Case首轮/后轮，保存原答、结果、HTTP目录及页面证据。质量和功能各自报告，旧批次不回灌。

[操作及备份回执](../../docs/operations/evidence/streaming-release-20261116-04/README.md)保留每步结果和失败尝试。本批配置与脚本不可直接重放清理或重发旧消息；后续发布另建显式批次。数据库新装/升级见[CURRENT](../database/CURRENT.md)，本轮只核已有结构。

## 回退边界

旧包、容器和受控备份保留。尚无新业务写入时，正常排空后可恢复已核旧包，仍保持单一执行入口；应用回退不自动恢复已清历史或重放Kafka。

新版C1含analysis_material，旧r3 Context Schema已实证拒绝该字段。产生新C1/Run后，不直接回退旧核心或HTTP；保留新读侧及记录，暂停新工作后修复当前版本。不能删新字段、改写Run、降级DDL或并行启动旧消费者。

总体状态见[PROGRESS](../../PROGRESS.md)，发布前文档见[历史快照](../../docs/handoff/history/2026-11-16-release-r4/deploy/aisoc21/README.md)。本次不含Git提交、推送或整个change归档。
