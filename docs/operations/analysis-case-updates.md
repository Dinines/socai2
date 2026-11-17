# Case持续更新与上一轮比较

第7步沿[详细设计](../../openspec/changes/schedule-streaming-investigation-updates/stage7-case-updates-design-20261115.md)扩展原Case首轮工厂。程序验证见[本批证据](evidence/case-updates-20261115-01/README.md)，HTTP见[提交/查询指南](../integration/analysis-submission-http.md)。当前是本地候选；正式发布在第11步验收和独审后进行。

唯一A/I/Case调度器接收initial、check、rerun。Case自动check比较活跃接收事件的当前可用I结论、依据与实际范围，以及有效H业务内容；单告警首次A晚到不直触Case。手动check读取全部适用关联事件，rerun明确重做。任务执行前重新取材料并保存范围及上一实际完整调查，运行中到达的材料等待下一轮。比较对象不是当前采用判断，上一实际轮失败且无可用结论时保留定位和不可比较原因，不回退更早结果。

| 配置 | 示例/默认 | 用途 |
| --- | --- | --- |
| 执行器case.scan_batch_size | 100 | 单次扫描最多检查的到期Case数；必填正整数 |
| analysis-tasks.case_check_interval_seconds | 21600 | Case检查间隔，沿既有生命周期配置 |
| analysis-tasks.automatic_window_seconds | 604800 | 自动窗口；最近正常完成续期，扫描/失败不续期 |
| 统一调度的poll_interval_seconds及max_running_tasks | 沿所选profile | 所有任务共用轮询和总并发，同Case串行 |

配置真实层级以[生命周期配置](../../deploy/local-investigation/analysis-tasks.json)、[联合执行器](../../deploy/local-investigation/analysis-aic-executors.example.json)和[调度配置](../../deploy/local-investigation/analysis-aic-dispatch.example.json)为准。示例继续禁用。测试可选短周期和短窗口的要求已交测试模块；本步没有修改默认时长，也不要求实际等待六小时或七天。

周期检查先识别活跃事件新的可用I业务结果，再复用分配用例跟随当前成员并检查适用业务内容；事件尚待分析、旧I失效或失败不作为新结论直接重跑Case。满100条沿原容量规则续建，使用服务actor并登记子案首轮任务；旧案及其他独立案不接收同事件的新成员。没有新成员不写分配活动。超期/关闭不自动接收；手动提交仍按现有资格和受理规则处理。排队已受理首试跨期可做一轮，不自动重试；已有运行按原规则结束。

冻结input manifest与Case Run/Result的comparison_context对应；初轮initial、选入可用前轮eligible、前轮不可比unavailable。历史未记录时为null，不读时猜测或回填。HTTP仅按冻结ID增加前轮Run及比较Result链接；pending队列不对调用方暴露，调用方以task_id读取尝试、Run和结果。采用保护及完整输入输出原件仍保留。

无新DDL，依赖129与任务生命周期。发布使用[Case片段](../../deploy/local-investigation/analysis-case-release-fragment.json)和HTTP对应片段，替换原唯一工厂，不能并行再启动一个消费者。第8–10步保持后置；本步替身/ASGI通过不等于真实模型质量或21整体验收通过。

F5候选执行校验：统一工厂要求当前A/I/Case三个输入输出合同及选定政策指纹，启用调度时缺任一实际handler即拒绝。A/I与Case C3/Deep/C6只使用现行装配；缺合同或旧冻结输入报错，不走旧模型分支。历史记录只读保持，合法预算仍可配置。直接验证进度见[第7步修复计划](../../openspec/changes/schedule-streaming-investigation-updates/stage7-case-updates-design-20261115.md)。
