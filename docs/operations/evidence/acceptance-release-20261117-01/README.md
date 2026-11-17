# 21新版发布、授权历史清理及新测试入口

2026-11-17，负责人明确要求“先部署到21 清除历史数据 然后再测试数据”。[本轮设计§12.14](../../../../openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md#1214-负责人明确要求先发布21清历史再测试2026-11-17)调整了发布顺序；4b报告精确跳转和自动紫色映射仍待，不冒称随本次发布完成。

**发布和清理已完成，[新两段测试及查阅](../acceptance-fullflow-21-20261117-01/README.md)也已完成。** 目标为21正式`aisoc.socai2`；没有切到本机隔离库，没有提交、推送或归档。[实际就绪回执](deployment-ready.json)、[清理核零](cleanup-zero.json)、[浏览器空态](viewer-empty-browser-01.json)已保存。

| 项目 | 本轮实际结果 |
| --- | --- |
| 处理服务 | `processing-20261117-r1`，Fusion和唯一联合调度器；741个运行文件（含挂载策略）匹配冻结来源 |
| HTTP | `acceptance-http-20261117-r1`，730个来源文件、80操作，入口18024；公共合同及告警DTO保持 |
| Swagger | 18080，同版合同、三类分组及CORS核对通过 |
| 4177 | r7，新三类主体/轮次及冻结流程布局，默认Case；实际浏览器空态通过，标签`acceptance-release-20261117-01` |
| 验收容器 | 3d04原镜像，原生linux/amd64、Python3.11.17；109份包文件和不可变摘要在21核对通过，默认帮助不发送 |
| PostgreSQL清理 | 明确84张调查业务表共521行清空并核零；127张非目标表内容摘要不变，32表521列及原结构不变 |
| 关联清理 | 湖15条、Redis13键、4个指定Kafka主题共25条记录、展示账本24文件清理；主题、集合和其他命名空间保留 |
| 备份 | `/opt/sting-aisoc-socai2/private/acceptance-release-20261117-01-cleanup`，受控保存，不进入模型或新展示 |
| 切换状态 | 停旧服务前后均无在途task/Run/attempt或待写completion；旧五服务保持停止，新五服务running、0重启 |

发布采用与3c.2真实正常两段验收一致的当前完整后端组合；[来源冻结](source-freeze-01.json)、[核心来源复核](core-package-review-01.json)和[HTTP独立同包复核02](http-package-review-02.json)核670份共同runtime来源一致、286份API/Fusion与3c.2冻结一致，C1修正和新增Deep接收文件均入包。该组合包含D5a相关修改，但D5a异常截断后的真实PG/C6存取目标仍未完成，本次正常链发布不核销D5a/D5/D6。没有回退或覆盖工作树。

HTTP审核01因专有Markdown/SQL文件集合假设错误失败，原回执保留，02按各包自身完整清单与共同runtime比较通过。验收镜像导入01误将Docker manifest ID与platform config ID比较，未重新导入；[02](acceptance-image-verify-02.json)核原始不可变摘要、平台、109份内容和默认入口通过。两者均为核对脚本假设问题，未靠改包、改原答或重跑模型消除失败。

预算保持窗口65536，A/I/Deep输出8192、C3/C6输出16384；A/I/Case每Run总预算131072/131072/393216。I4h/Case6h、7天窗口及Fusion关联窗口3600秒保持。清理保留账号、租户、来源配置、规则、凭据、迁移与全部本机历史原件，不清全库或卷。新数据发送前必须再从最终验收容器核连接，发布就绪不替代真实业务链或模型质量验收。

新测试复用[4a冻结材料](../acceptance-fullflow-20261117-01/README.md)及唯一execution；原4a母本不修改。最终容器准入后，协调方确认无发送记录并保存[唯一执行接管](../acceptance-fullflow-21-20261117-01/execution-takeover.json)，实际完成首段1告警+2上下文和追加1告警+1上下文。首段保存/HTTP及追加前TTL通过，最终同事件/同Case两轮1→2，后轮比较真实首轮；测试模块及HTTP模块完成限定独审。

[最终业务核对](../acceptance-fullflow-21-20261117-01/final-validation.json)通过19项，8模型均stop；两轮Case待复核/部分交付，4自动+1人工质量问题保留，不追加采样。4177已通过实际两轮、HTTP接入、具体领域、原答与问题查阅；此次辅助账本发布不等于4b自动接线完成。全部输入/Schema/原答见[程序生成报告](../acceptance-fullflow-21-20261117-01/results/report-01/report.md)。
