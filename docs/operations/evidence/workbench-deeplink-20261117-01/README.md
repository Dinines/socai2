# 4b 报告定位指定主体和轮次

2026-11-17，按[§12.16](../../../../openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md#1216-4b报告直接打开指定主体与轮次2026-11-17)完成本机实现与直接验收。实际[新报告](report-01/report.md)为已存同一会话的4个主体、6个Run生成链接，Case首轮和后轮分别指向自己的真实Run；[公开展示配置](report-config.json)指向本机58482预览。原4177/21仍是上批r7，未替换服务或镜像。

`report`和`session`增加可选`--report-config`，独立于冻结profile。报告及manifest保存展示配置，源会话环境与目标工作台环境显式对应；链接携带主体类型、主体ID、Run及目标环境。页面核环境、主体/Run归属和完整目录，支持当前列表首页之外的主体。无Run不生成链接，缺失/错环境/读取失败保留目标和错误，不选latest。刷新、重载、隐藏恢复和明确换轮均保留正确目标。无配置继续生成原报告，未改变业务HTTP或模型输入。

| 步骤 | 结果和证据 |
| --- | --- |
| 报告与菜单 | [首轮24项](report-check-01.log)通过：6条实际链接、CLI/菜单、旧无配置、环境拒绝、离线原件保持。测试模块发现合法IPv6地址的authority被错误编码，已修为只编码path；[修后7项定向复验](report-check-02.log)通过，不重复累计为31项 |
| 页面直接检查 | [10组Node](viewer-check-01.log)通过，包含5组新跳转及5组既有来源检查；[7项挂载](viewer-mount-check.log)通过。六个实际报告Run逐一核ID，缺失/外主体Run不回落，未列在首页的目标可直接解析 |
| 浏览器 | [8项实际观察](browser-verification.json)通过。点击Markdown渲染后的Case首轮/后轮链接，分别读取冻结1/2告警、17步骤50工件；后轮比较实际首轮。刷新首轮/重载后轮保持；不存在Run和错误环境均明确空态，没有显示最新执行 |
| 报告独立复核 | [定向复验](../test-workbench-deeplink-20261117-01/independent-report-review-02.json)通过，关闭IPv6发现；前轮7组证据及原失败保留。独立报告/菜单/旧入口核对1036份原件不变、24份可见模型导出字节相同，0网络或连接配置读取 |
| 页面独立复核 | [实际viewer.js启动/导航/渲染的离线回放](../test-workbench-deeplink-20261117-01/boot-review-02.json)5组通过，包括目标不在首页、Run在目录第二页、隐藏恢复及明确换轮。此为最小内存DOM和已存HTTP回放，真实浏览器证据另列 |
| 打包和合同 | [5个新入口纳入检查](package-source-check.json)通过；模块、Schema、配置示例及说明已同步。OpenSpec strict、Ruff和本步diff格式检查通过；没有重建Docker镜像或部署21 |

原始测试会话、旧报告、旧失败及模型原答不变。新的报告生成过程0网络/业务写/模型，浏览器和补充两份HTTP正文只读当前21；[能力声明](http/capabilities.json)与[Case详情](http/case-detail.json)均GET200。本机预览用显式旧来源前缀识别当前历史批，交付来源示例仍只有lyc，不把旧数据冒充新lyc投放。

报告HTML仅为浏览器点击验证时对已存Markdown的本机渲染，完整离线原件相对链接按仓库中的`report.md`查阅。本机58482留作本次预览，依赖现有4177隧道；它不是21新发布。无新增告警、任务或模型调用，不改变既有质量问题、D5/D6或整个change验收结论。4b本机功能由本步与前一步来源识别共同完成，统一发布后仍需核实际21链接。

[测试模块最终限定独立复核](../test-workbench-deeplink-20261117-01/independent-review-01.json)已通过，未关闭发现0；[本轮交接核对](handoff-validation.json)记录当前实现与报告证据摘要。独审只核已保存的真实浏览器回执，事件/告警和列表外目标沿直接离线验收；不扩大为21已发布、真实新lyc投放或整个change完成。
