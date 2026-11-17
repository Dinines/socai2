# W2真实非空读取：根侧运行核对与交接

本轮只读验证现有测试服务代理到21候选HTTP的真实非空任务/Run/原件及跨Run来源。测试方独占临时代理、live身份接线与TCP读取，HTTP方核合同/已存返回链接，根侧核当前运行来源和总交付。沿[本步设计](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-candidate-design-20261115.md#下一独立子步w2真实非空及跨run来源读取)；S04原失败及未完成的Case后轮比较保持。

[本轮实际读取](../test-http-proxy-w2-live-20261115-01/tcp-02/result.json)通过：2026-11-15北京时间22:37:52–56，9次账本GET、24次业务代理GET、1次当前OpenAPI核对，共34个200及107项直接断言。测试服务保持`0.2.0`，当前80操作/55业务GET合同一致；现有能力足够，本步没有修改服务源码、DTO或版本。

[运行来源核对](runtime-01.json)确认候选HTTP/Fusion镜像及8份配置与前轮一致，唯一调查调度与9个旧业务容器停止。测试以新live查阅账本保存3用例、7真实操作、4质量记录、6证据引用，源S04仍failed；GET前后账本摘要保持。调查业务状态不由测试账本重建。

实际跨Run路径是Case `d1b17106…`的C1 `bf3a8ed9…`保存的diagnosis_scope → 原事件Run `b5410c29…` → 该Run工件目录返回的content_url → 输入原件`1b43bb64…`。原件内容/摘要与冻结来源相同，选入范围保持原3成员，没有按当前事件4成员扩大；源Run与当前Case Run不同。8份既有steps目录没有直接跨Run reused artifact_refs，故该具体形式未覆盖；本步也不是同Case上一轮比较。I失败/原答length、3个跳过任务无Run、两Case原initial比较null和当前stale均保持，S04正向更新仍未通过。

首次临时调用[tcp-01](../test-http-proxy-w2-live-20261115-01/tcp-01/result.json)因隧道目标误填远端回环地址失败，仅本机capabilities读到200，尚无成功业务读取；改为当前实际`192.168.1.21:18424`的显式profile后完成tcp-02，不改变21服务或旧失败。原本机准备错误也保留在测试目录。

临时测试服务收到SIGTERM后日志正常shutdown，进程返回-15；SSH返回0，两个端口均已关闭。0业务写入、直接SQL查询、模型或Kafka请求，调度和4177未变。业务HTTP仍正常读取其数据库。既有24项组件及TCP空态证据复用，本步不额外重复该矩阵；真实大原件/直接reused引用等未命中分支不由本次替代。

W2非空和跨Run来源读取出口已完成。下一步W3页面按HTTP取数，再做W4包/候选启动；当前4177仍是原静态入口。本次通过不核销S04缺口、整体独审或正式发布，任务仍2/11、主31/41；未提交推送。

[测试统一回执](../test-http-proxy-w2-live-20261115-01/acceptance-01.json)、[HTTP独立离线复核](../streaming-w2-http-cooperation-20261115-01/tcp-readback-review-01.json)及[根侧收口](closure-01.json)使用同一TCP结果摘要`d2768823bd636f3854d70816d0d5bde26050c70c708c8299bf5f2f1338ce15ce`。HTTP复核34份已保存响应字节和来源字段，没有重复发请求；OpenSpec、测试计划、前后端交接及部署说明已同步本步实际范围。
