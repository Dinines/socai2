# 4b 发布到21及报告轮次查阅

2026-11-17，按负责人本轮明确要求及[设计§12.17](../../../../openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md#1217-4b明确分阶段发布到21及读回2026-11-17)，已将工作台0.6.1/r8和同包验收工具部署到21。[4177](http://127.0.0.1:4177/viewer/)通过既有SSH转发访问，核心业务服务、正式数据和原账本保持。

[最终报告](report-02/report.md)的Case链接可直接打开[第1轮](http://127.0.0.1:4177/viewer/?subject_type=case&subject_id=8bf67e9e-a46a-58ba-a3ad-73a70ca64258&run_id=c068a7b9-b33d-45a5-b0c0-c2b296ba5d5d&environment=acceptance-release-20261117-01)与[第2轮](http://127.0.0.1:4177/viewer/?subject_type=case&subject_id=8bf67e9e-a46a-58ba-a3ad-73a70ca64258&run_id=57683158-b770-4697-8ca3-a2707ed0af1b&environment=acceptance-release-20261117-01)。首轮冻结1条、后轮2条；紫色“测试数据”按本轮冻结来源显示。后轮比较实际首轮，刷新/重载保持目标；缺Run或环境错误不会改选最新执行。

| 步骤 | 实际结果与证据 |
| --- | --- |
| 发布前检查 | [原环境读回](preflight-02.json)及[24项包/页面/报告检查](package-check-01.log)通过；新包版本0.6.1，119文件，归档SHA `b442eb8cfadcb4c6f5315a49bc3f6cbd639e71596d636c1adbdb4bb113f4ee7d`，manifest `cd655d03dea2d58bc603672473afb47862ba7dd51ba0dd2f910653edda02e3a2` |
| 固定镜像 | 工作台在21构建；验收工具在21两次下载超时后，用本机相同Dockerfile/依赖锁/基础引用的已有缓存构建linux/amd64镜像。[本机构建](local-acceptance-build-01.json)、[导出](local-image-export.json)、[21加载](load-image-01.json)完整保留，未换依赖或配方 |
| 镜像运行/报告 | [两镜像内容及禁网报告](images-report-01.json)核119文件和0.6.1一致；Python3.11.17。原prepared/材料只读、不挂连接秘密，仅report，0业务连接/写入/模型；[最终保持](final-preservation.json)另核19锁定依赖和pipcheck |
| 切换与读回 | [r8就绪](deployment-ready.json)核实际镜像、配置、80操作合同及静态资源GET摘要；只替换4177，r7停止但保留。四核心容器身份/启动时间/重启数/挂载/端口不变，原配置、8账本及Case详情保持 |
| 最终报告交付 | [report-02](report-02/report.md)来自同镜像禁网生成，6个真实Run链接。01复制后6个原件相对链接不匹配仓库目录；调整容器挂载展示目录生成02，未改产品/包或覆盖01。[转存检查](report-transfer-validation.json)核32个本地链接可解析，26manifest文件正确，结构报告除生成时间外与01相同 |
| 实际浏览器 | [浏览器回执](browser-verification.json)及[首轮截图](case-r1.png)、[最终后轮截图](case-r2-final.png)：点击最终报告→实际4177，1/2成员及紫色分别正确；R1刷新、R2重载、前轮比较、缺Run与错环境均通过。先读到的loading中间态单独保留，待加载完成后才验收 |
| 实际HTTP原件 | [26GET](live-http-verification.json)全200：6Run身份/终态与冻结输入一致，8模型原答、4份冻结上游副本及2份C1逐值保持。脚本原先混用A/I详情投影与trace身份、把副本算作原答的失败分别保留，修正的是验证脚本 |
| 保持与收尾 | [最终保持](final-preservation.json)核982份prepared文件及8账本不变；4核心容器保持、r8仍运行。独立复核另外覆盖含原报告的1036份母本，两者统计范围不同。[预览收尾](preview-cleanup.json)关闭58482/58483，文件保留，日常入口为4177 |

本次实际viewer显式配置`lyc`与旧批`telemetry-channel-02`；旧来源不改写，也不声称已投放新lyc数据。新测试来源默认仍为lyc，模型输入边界沿[20项已验检查](../test-lyc-source-20261117-01/input-boundary-review.json)。来源/tenant后台关联保留，展示配置不进入模型。本次新增告警、任务、模型调用、清理均0。

固定基础镜像的索引摘要与平台摘要不同，最初构建前校验被拒；[平台blob原始SHA核对](base-identity-01.json)通过后继续，不把不同层级ID直接等同。preflight-01的Swagger名称假设失败、build-images-01/02/03和两个HTTP驱动失败原件均保留。

测试模块分组独立复核入口：[包/配置](../test-workbench-4b-release-20261117-01/independent-package-review-01.json)、[构建主机变化](../test-workbench-4b-release-20261117-01/build-host-addendum-01.json)、[运行/切换](../test-workbench-4b-release-20261117-01/independent-runtime-review-01.json)、[报告与浏览器](../test-workbench-4b-release-20261117-01/independent-report-browser-review-01.json)。[最终限定独立复核](../test-workbench-4b-release-20261117-01/independent-release-review-01.json)7组通过、未关闭发现0，报告路径问题已修验关闭；只收口本次§12.17发布，不替代完整change结束审计。

模型原有4项自动诊断和1项人工比较问题后置，两轮仍为accepted/uncertain/partial。D5/D6及整个change未完成，本次不新增模型采样、不改变告警合同，不提交推送或归档。
