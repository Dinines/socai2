# W3 调查测试查阅页面

2026-11-15。本步实现服务/页面 `0.3.0`，复用W2只读账本，经本机临时服务及SSH读取21当前候选。页面主流程通过；S04正向更新/比较及模型质量未由本步通过。没有部署或切换4177。

## 实际来源与配置

- 根侧[当前运行核对](../streaming-w3-viewer-20261115-01/runtime-01.json)：15:35:19Z，HTTP r2/Fusion r3及8配置摘要保持；dispatcher停止、旧9容器停止。测试方没有另查21数据库或变更服务。
- [服务配置](service-config.json)、[代理配置](upstream-config.json)、[页面配置](viewer-config.json)、[临时运行profile](runtime-profile.json)：127.0.0.1:58808；58809转发192.168.1.21:18424，环境streaming-20261115-01。原W2账本`w2-live-s01-s04-20261115-01`原位只读，不重新publish，不修改已结束批次。
- 当前合同80操作/55GET。旧源码、历史模型替身和旧预算未作为本批运行来源。模型和工具记录来自此前S01/S04真实执行；本步新模型调用0。

## 本步结果

[读取核对](readback-validation.json)和[统一回执](acceptance.json)记录：8项Python直接测试、8项明确受控JS检查通过；真实浏览器共51次GET（26业务、14账本、11页面/资源），业务全部200。favicon 404及2次静态304按实际保留，不能报“全部51次200”。113项离线核对仅对应本组响应/来源与读取完整性，不替代业务成功链或模型质量验收。

- 用例到具体操作、7任务及4Run可查；3skip没有虚构attempt/Run。首个F05导航发现两个TestCase共用use_case_id导致显示混入，[原发现](finding-01.json)保留；已修为API按功能过滤、每页再按具体TestCase.id匹配并浏览器定向复验。
- 两Case首轮保持completed/partial、结果accepted/uncertain及initial/null比较；当前采用仍accepted、输入stale/incident_context_changed。A04完成但原理由仍“告”；I current与valid_for_current_input=false分别展示，选入4、覆盖unknown、不造结论。
- Case工件20/20/8三页读齐48条，I完整2步骤；原答沿真实content_url按需读取，length/3000、完整原文和末尾截断保持。C1追溯原I来源/Run/输入摘要及3条冻结范围，未扩大到当前4成员，也不冒称Case上一轮比较。
- 准备/清理事实和4项deferred质量记录独立可读，I问题affects_flow=true保持。登记证据可展开完整原JSON。终态页面可见[30.94秒无新增请求](terminal-idle-after.json)，配置轮询间隔5秒。
- [停止回执](shutdown.json)：SSH exit0，服务SIGTERM后日志正常shutdown，58808/58809均关闭。[读取前](ledger-before.json)/[读取后](ledger-after.json)逐文件hash一致。0新业务写、模型、PG、Kafka、调度、21服务修改；现行4177保持。

## 验证层次与边界

[Python输出](python-tests.txt)覆盖显式页面启停/版本/配置、无启动副作用及受影响的账本/代理入口；[JS输出](javascript-tests.txt)使用受控响应/定时器验证archive/环境门禁、task/Run状态、同Run结果绑定、游标、取消迟到返回、错误/超时、可见性及>1MiB完整字节。受控大原件包含明确初答/补答/合并及field_origins，逐字段/原字节保留；不冒称真实模型补答或21大原件验收。

浏览器完成后收紧“终态重新可见不自动刷新；活动或被中断读取恢复；展开目录/正文暂停父Run轮询”，并补C1的本案选入/覆盖交集摘要。这些末尾改动仅做直接受控或保存数据离线核对，未重新访问业务；截图保留主流程当时版本。[最终源码摘要](source-final.json)与请求日志里的实际浏览器资源摘要分别记录。

真实批次没有活动/pending、unknown、同Case新轮/上一轮比较、直接跨Run reused、>1MiB正文及补答合并；缺口保留，不新投数据或调用模型。页面不存在执行/清理/恢复入口；W4发布包、W5实际部署、change整体结束审计另行处理。

## 证据入口

- [完整实际请求索引](requests.jsonl)及`responses/*.json`为唯一浏览器读取原响应；[离线核验脚本](validate_saved.py)不发网络请求。
- [运行器](run_local.py)/[观察包装](record_server.py)仅保存响应与关闭本次进程，非新增业务/通用测试框架。`stop-request`为该已结束临时运行的停止信号，重新验证应开新批目录。
- [01批次](01-batch.jpg)、[02具体用例](02-operation-filter.jpg)、[03Case交付与当前stale](03-case-initial-stale.jpg)、[05跨Run来源](05-source.jpg)、[06结果](06-case-result.jpg)、[09失败Run](09-incident-failure.jpg)、[11原答](11-original-response.jpg)、[12skip](12-skipped.jpg)、[14质量](14-quality.jpg)。对应AX文本保留可检索字段。
- HTTP方[同组离线复核入口](../streaming-w3-http-cooperation-20261115-01/README.md)，根侧[本步复核入口](../streaming-w3-viewer-20261115-01/)；均不重复业务GET。
