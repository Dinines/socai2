# W3 HTTP查阅页面：设计、复核与交接

本轮按[第11步W3安排](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-candidate-design-20261115.md#w3本轮设计分工与直接验收)实施，暂不部署。测试模块独占页面、必要服务接线、临时运行与浏览器验证；HTTP模块供给真实字段/来源合同并离线核同一组响应；根会话负责设计、实现与截图复核及交接收口。

开始时分支`V1.1`，5333项既有未提交路径保持；[原19份模块/配置摘要](before-files.json)保存W3修改前状态。OpenSpec在实现前严格校验通过。沿W2既有真实账本及21只读代理，不新增业务Run、告警、Case或模型请求；当前4177及21服务保持。

必要验收分成两类：实际浏览器读取已有A/I/Case任务、结果、步骤/原件与跨Run来源，保存原范围、失败和质量；活动刷新、迟到响应、archive/环境不匹配及未命中的大原件等页面行为用明确组件或归档验证。两种证据不能互相冒充，S04正向自动更新和上一轮比较仍未通过。

W3已在本机实现并完成实际读取联验，测试服务/页面统一为`0.3.0`。新增`--viewer-config`，公开页面配置只有轮询间隔、请求超时、每页条数和版本；原账本存取、8个测试GET及当前80操作/55业务GET保持。页面从HTTP读取所选批次和真实身份，结果与当前采用/新鲜度分开；原件按返回content_url读取，不再依赖生成静态HTML。

[保存响应核验](../test-viewer-w3-20261115-01/readback-validation.json)113项通过。实际浏览器51个GET为26业务、14账本、11页面资源，业务和账本全200；favicon404与两项资源304保留。7任务、4Run、两Case原结果、3skip无Run、I失败原答及质量/准备/登记证据均可查。整事件Case工件按20+20+8三页读满48项，C1沿原I目录/content_url读到3成员冻结输入。终态可见停留30.94秒没有新请求。

根侧独立复核[批次](../test-viewer-w3-20261115-01/01-batch.jpg)、[用例筛选](../test-viewer-w3-20261115-01/02-operation-filter.jpg)、[Case原轮次与当前新鲜度](../test-viewer-w3-20261115-01/03-case-initial-stale.jpg)、[跨Run原来源](../test-viewer-w3-20261115-01/05-source.jpg)及[失败诊断](../test-viewer-w3-20261115-01/09-incident-failure.jpg)截图，身份和状态与保存响应一致。HTTP模块[独立离线复核](../streaming-w3-http-cooperation-20261115-01/browser-readback-review-01.json)核同一组响应，不再发GET。

8项Python接线/受影响测试、8项受控JS通过。明确组件验证活动/终态/隐藏/迟到响应、环境错配和archive门控，以及大于1MiB的初答/补答/合并/field_origins完整读取；这些不是本批21真实业务样本。浏览器结束后进一步收紧终态重显及阅读目录/原件时暂停父轮询，按受控组件复验；C1本案交集摘要按保存字段离线核对，没有再次浏览器读取或改写截图。完整change独立结束审计仍另行完成。

直接复核已修比较原因/身份、I范围摘要、刷新保留旧观察/用例筛选。浏览器发现两个F05用例共用use_case_id而混入另一用例操作，已逐页按Operation.case_id匹配实际TestCase并定向复验，保留[首次发现](../test-viewer-w3-20261115-01/finding-01.json)。原始失败、质量NOT_PASSED、Case初轮空比较和当前stale未被读取成功改写。

[本步运行核对](runtime-01.json)在北京时间23:35确认21镜像/8份配置及原停止状态保持，0业务HTTP/PG/运行变更。[临时进程收尾](../test-viewer-w3-20261115-01/shutdown.json)确认账本摘要不变、58808/58809关闭；SSH exit0，服务SIGTERM -15且日志正常shutdown。测试没有直接SQL、模型、Kafka或业务写入，业务HTTP照常读库。当前4177未切换，未部署/提交/推送。

下一步为W4完整包及明确验证安排。W3读取通过不核销S04正向Case更新/上一轮比较缺口；真实unknown、超过1MiB原件、steps直接跨Run reused及Case后轮没有由本批覆盖。W5部署、整体结束审计与正式发布仍保留原条件，任务仍2/11、主31/41。

[测试统一验收](../test-viewer-w3-20261115-01/acceptance.json)、[HTTP最终冻结核对](../streaming-w3-http-cooperation-20261115-01/final-freeze-review-01.json)、[根侧实现/截图复核](implementation-review-01.json)和[根侧收口](closure-01.json)已对齐同一组请求摘要`d187d615531df3428375a3cdeac65c55d784abe1eb1091de414cb06134d39cf2`及23份最终文件。HTTP独立离线131项通过，无新增请求；OpenSpec、当前进度、测试方案、HTTP交接与部署说明已同步实际范围。
