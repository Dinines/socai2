# 本机Case续验独立复核

2026-11-17，**本机C1→Case真实执行→Result保存/HTTP读回通过，可核销§12.10本机阻断验证；21原Case未恢复，模型质量未通过。** 本轮仅核已保存实际证据及当前冻结源码，0新服务连接、业务写入、Kafka发送或模型调用。独立结论见[independent-review-01.json](independent-review-01.json)，核对脚本见[review.py](review.py)，原件摘要见[evidence-hashes-01.json](evidence-hashes-01.json)。

成功任务为`7e19b27b-0248-4cb2-aa9a-a62cd206f59f`，Run为`1977d41d-9708-4565-932a-1c286c43a122`，Result为`8b89cb57-f274-47f1-a2cb-c2e5d993f1d4`。task/attempt/Run均completed，Result为accepted/uncertain/partial；程序交付、业务结论和模型质量分开记录。

| 核对边界 | 实际结果 |
| --- | --- |
| 源码及依赖 | 成功执行前后240份源码/配置摘要一致，当前文件匹配；C1核心仍为前次独验的最小别名修正。本案16表46行与21单段02原件一致，导入后业务UUID/tenant及冻结工件保持，A/I仅作复制依赖 |
| C1多事件取数 | 新库保留同租户两个事件，实际C1只含本案1告警和对应I；按保存task/attempt/Run/输入/原答/回执重装的I材料与实际C1完全一致，无关联中性事件未进入本案 |
| 唯一成功执行与保存 | execution-03仅1次ASGI POST202，使用独立operation_key；新Run17步骤、50工件、1个Result。总计7task、6attempt、4Run、41步骤、116工件、1Result；历史任务/步骤/工件逐值保持 |
| HTTP与PG | 按原请求顺序重放168份真实ASGI GET原始响应，无组装/替换响应；任务/Run/全分页步骤/工件正文及摘要匹配PG。Result全部共同投影字段另作逐值核对；26表摘要与保存快照、读取前后摘要一致 |
| 上下文查询 | authentication_activity实际completed、返回2条；解析OCSF后与21原湖读回逐值相同。network_connections实际completed、查空。未查询与查空分开，不能由网络查空推断安全 |
| 真实模型计数 | 成功Run新C3/C6各1次、共23539tokens；含execution-02两次失败保存前的模型请求，本批共4次、39598tokens，均stop。索引另外2条A/I来自复制依赖，不计本批新增。请求/原答导出逐个匹配PG工件，费用未知 |
| 失败与比较 | 三次旧失败保留，精确状态见下表。成功Run冻结previous_run_id指向02的unknown Run，comparison_result_id为null，reason为previous_result_unavailable；Result为not_comparable，没有伪造前轮结果 |
| 收尾和展示 | 保存的N1回执峰值1、最终active/未确认回执/Redis运行槽均0；专用3条转发关闭回执已核，未在本轮重新探测端口。21三服务容器/镜像身份与单段02一致。实际本机静态登记50→51，旧50条及原页面摘要保持；未进行新21/TCP/4177浏览器验证 |

| 历史执行 | task状态 | attempt outcome | Run / Result |
| --- | --- | --- | --- |
| 21原Case：`56dcc7bb…` | failed / execution_failed | failed | 无Run，0Result；C1多事件SQL错误 |
| 本机首次：`4e3df5da…` | failed / execution_unknown | unknown | 无Run，0Result；验证驱动只读轮询错误 |
| 本机execution-02：`bc2f93fe…` | failed / execution_failed | unknown | `4fe74408…`为unknown，0Result；新库函数执行授权遗漏造成保存回滚 |

成功Run的5项程序引用诊断与[原质量登记](../acceptance-case-continuation-20261117-01/quality-register.json)一致；人工登记的“history未查却写查空”也可在C6原答与实际skipped回执中复核。质量仍为NOT_PASSED/后置，不因程序保存通过核销，不追加采样。Deep等实际未执行范围保持原记录。

本轮离线核对脚本首次使用了错误的工件type选择条件，停止在写结论之前；核实真实type为`delivery_report`后修正并完成同一原件复核，见[复核驱动记录](review-driver-note-01.json)。这不涉及业务执行或原件更改。已有C1定向测试不重复运行；此处新增证据是实际保存内容、失败保留、HTTP投影、上下文和模型原件的独立核对。

本结论不核销21整链恢复、3c交互追加/报告、3d镜像、任务4或整个change；后续21验收仍随统一发布安排。
