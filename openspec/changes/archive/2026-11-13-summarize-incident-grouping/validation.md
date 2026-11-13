# E57事件归并统计验收

范围F06-06，仅新增同范围只读统计。原56操作、告警交接字段、表结构和内部调查流程保持；本批不调用模型或启动Run。

## 本机候选

6项定向检查通过：来源/UTC日期、空集合/错误/固定路由优先级、原56合同及HTTP边界。两次初始收集错误分别为命令未带PYTHONPATH、测试从未导出的适配器位置导入身份依赖；已修正测试设置，不是业务失败，不改变实现。

新合成批次8告警、4事件、6关系。其中主来源6告警、4条归为2事件、2条未归并，处理中1，compression_rate=0.5；另一来源有跨来源成员和单独事件，另留一个无成员且in_progress事件验证不计入。

13次真实TCP GET，7次200和6次预期422，逐项与独立SQL原行重算一致。覆盖来源、成员去重、跨来源、[起点,终点)、单边、未知时间、空集合、无已归并分母，以及不支持参数和日期错误。前后目标3组SQL原行完全相同。核心在同一REPEATABLE READ/READ ONLY快照计数，外部路由经port直接调用，不调用内部HTTP。

证据见`docs/operations/evidence/grouping-summary-20261113-01/`：fixture/seed、candidate原始请求响应、SQL前后、offline-check以及8文件源码清单。独立审计见audit.md。

## 文档

docs10共57操作，54已实现/3预留501，129Schema。原542固定字段加E57的9顶层和3scope字段共554；CSV仍104个允许列。E57仅JSON、仅来源/时间3参数，规则和错误逐项列明，功能清单F06-06与实际范围一致。示例为合成合同，不代替真实业务证据。

## 发布读回

本机18024实际grouping-summary-20261113-r1-local，PID58801、ARM64原生Python、库v12_upgrade_dev。21实际grouping-summary-20261113-r1，AMD64镜像sha256:487f1ac1177480480b6cfbcd0a189803dec158db50f1027dae7e19bc77830fe0、库aisoc；两端57操作。

本机正式13次GET（7成功/6预期422）、21正式12次GET（6成功/6预期422）与独立SQL原行重算一致。21复用既有synthetic-subject-management的3告警/3事件/3关系，无新增业务写入。两端SQL前后保持。8文件实际源码摘要与候选一致，页面读取开关和实际数据库/版本已读回；36个其他运行容器保持。

本机首次切换：已验证旧PID49309后发送SIGTERM，启动器端口占用探测返回Address already in use，尚未创建新进程；初次local-http读取遇503，仅留下SQL快照。随后只读检查确认无监听者且端口可绑定，再启动一次成功并记录PID58801，local-http-r2完成13次验证。无业务代码变更、无数据库重派，旧失败目录保留。

Swagger两端docs10、57操作/129Schema/554固定字段/125功能，9入口均200且摘要一致，架构分别aarch64/x86_64。根profiles与本批配置相等。delivery-summary、loaded-runtime-config、各HTTP/SQL/runtime/Swagger原件保存在同批证据目录。仅改变独立API及Swagger，没有模型、迁移或消费者恢复。
