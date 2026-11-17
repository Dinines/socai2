# Case首轮统一执行

第6步本地候选，暂不部署。设计见[本步OpenSpec](../../openspec/changes/schedule-streaming-investigation-updates/stage6-case-execution-design-20261115.md)，直接回执见[新批次证据](evidence/case-initial-20261115-01/README.md)。

建案和容量续建沿第5步原事务登记initial task；唯一调度器领取后，Case执行器读取最新已关联成员，内部创建并领取Run、保存范围/运行配置、绑定attempt，再执行既有C1–C6。task_id仍是调用方查询身份。运行中新成员不写回本轮输入，当前第6步不接Case周期或手动check/rerun驱动；这些留第7步。

将既有唯一调度器的工厂替换为`app.socai2.analysis_case_executor:executors`，使用[A/I/Case示例](../../deploy/local-investigation/analysis-aic-dispatch.example.json)及[执行器配置](../../deploy/local-investigation/analysis-aic-executors.example.json)。保持同一Redis命名空间、显式租户/PG/profile及总N，不并行启动旧A/I与新A/I/Case两个调度器。示例enabled=false，不自动改变任何运行环境。

| 配置 | 默认 | 实际用途 |
| --- | --- | --- |
| case.query_window.before_seconds / after_seconds | 3600 / 3600 | 根据本轮相关告警source/derived_source时间生成补查窗口；无可靠时间记缺口，不用当前时间代替 |
| case.log_query.max_rows_per_query | 50 | 与冻结Run的max_rows_per_query取较小值；请求构造和SQL校验共用实际上限 |
| investigation_policy_file | 显式绝对路径 | 与进程实际选定政策hash一致；保留完整政策及查询配置原件 |

补查时间不另裁剪或拆窗，主机查询按其关联告警时间生成；条数上限不是模型容量保证。截断保留限内记录及额外探测记录、失败/查空/未查分开。C2/知识原有候选额度保持。本步验证用75条日志额度证明移除隐藏50限制，候选默认仍为50。

模型实际请求超限保留已完成工件与未发送请求/计量，Case失败并停止自动重试，释放额度继续其他任务。早期业务输入字节额度不足也保存未发送材料并明确容量原因；不删除成员或分批生成结论。执行状态、局部交付、采用及模型正文质量分别读取。

129是前置，无新增DDL。按[发布片段](../../deploy/local-investigation/analysis-case-release-fragment.json)收集核心、配置和主机CLI；HTTP同批退役外部E11/E13，内部prepare/claim能力保留。旧CLI的case-prepare/case-start也从候选入口移除；case-create只受理首轮任务。第8–10步保留设计并后置，知识现状不据此改称后台异步已交付。

第11步结合[测试对话既有方案](../../openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md)完成当前1–7步整体验证及独立结束审计，真实模型、独立TCP和4177 HTTP取数按实际供给验收；本步受控依赖/ASGI不能代替最终联验。统一发布仍按当时授权，本说明不启动服务或消费者。
