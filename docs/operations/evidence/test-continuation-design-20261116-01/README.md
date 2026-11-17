# 输入过滤与异常继续：测试设计交接

2026-11-16。本批只完成测试设计和只读资料核对；没有修改业务/测试执行代码，没有访问21、清理数据、部署、投递Kafka或调用真实模型。

当前基线沿processing r3实际引用的r2运行配置及新fullflow回执；4177为0.6.0 HTTP只读服务。旧候选端口、3000输出和短周期值不是本轮目标。正式运行重核仍须在执行时完成，文件/hash核对不代表当前服务已重新探测。

| 文档 | 本轮产出 |
| --- | --- |
| [完整计划§7](../../../../openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md#7-当前增量输入边界与异常后继续2026-11-16已设计待实现) | 当前配置/证据、目标、分层出口及状态/证据要求 |
| [功能用例§10](../../../../openspec/changes/schedule-streaming-investigation-updates/functional-test-cases-20261115.md#10-本轮新增直接用例) | TC-N01–N11，输入过滤、质量问题、完整/非完整length、无有效内容、网关异常、保存/HTTP、页面、后轮与I收尾推动Case |
| [数据设计§15](../../../../openspec/changes/schedule-streaming-investigation-updates/test-data-design-20261115.md#15-本轮输入过滤与异常继续的数据设计) | D-N01–N09、真实母本、关键边界及seed=20261116的有限随机截断；经过接收→恢复→后续模块，不只测JSON |
| [HTTP与4177§11](../../../../openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md#11-异常继续后的读取与页面验收已设计) | 原答/程序回执分离、单节点读取失败兜底、同Run任务/工件、红色错误与紫色测试标识 |
| [供给清单](../../../../openspec/changes/schedule-streaming-investigation-updates/test-interface-readiness-20261115.md#本轮新增供给输入过滤与异常继续) | 调查输入/输出/持续链、HTTP、测试页面和发布各自交接项；不要求内部阶段逐个开放HTTP |

全部TC-N变体当前为**已设计／待实现交接／not_run**。调查侧业务设计、stage_delivery具体字段及依赖/重试规则完成后对齐；不以旧F4或r3正常读回证明新行为。C3一次补答失败须保留初答有效单元；请求已发后的unknown保留、不盲重发；I当前输入的收尾回执可驱动Case属于待实施的新规则。

[来源摘要清单](source-manifest.json)冻结26份配置、最新整链资料及选定模型输入输出；独立核实旧length原答8238字符/8163尾部空白、JSON不完整，source_snapshot与model_response raw一致。旧失败/hash保持，新回放必须标controlled_dependency。该核对是数据来源检查，不是新恢复功能通过。

[设计校验](validation.json)记录新增引用、来源hash及OpenSpec strict结果；只验证文档/规格结构和来源未变。后续按单点→保存与真实HTTP→4177→就绪21必要真实模型链推进，测试模块继续承接实施完成后的直接验证。真实新批才记real_model_21，模型质量仍单列NOT_PASSED，未覆盖分支不核销。
