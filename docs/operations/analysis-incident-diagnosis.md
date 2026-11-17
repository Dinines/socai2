# 事件自动诊断运行说明

本步为[流式实施第4步](../../openspec/changes/schedule-streaming-investigation-updates/stage4-incident-diagnosis-design-20261115.md)，本地实施/验收证据见[本批回执](evidence/analysis-incident-auto-20261115-01/README.md)。正式服务尚未启用；本说明不构成部署指令。

正常native入站新建事件和首个成员后，同一PG事务登记事件initial任务。已有事件新增告警仍只登记新告警的A任务；已登记事件随后按周期检查选入告警范围、有效人工反馈及可用A业务结论。事件自己的诊断输出不会触发自己。周期检查在唯一调度循环内执行，先比较再登记，实际执行再次取最新输入；没有A全部结束的等待屏障，晚到A由后续检查覆盖。

使用[A/I调度配置](../../deploy/local-investigation/analysis-ai-dispatch.example.json)、[执行器配置](../../deploy/local-investigation/analysis-ai-executors.example.json)和[生命周期配置](../../deploy/local-investigation/analysis-tasks.json)。将唯一进程的工厂选为`app.socai2.analysis_incident_executor:executors`，同时注册A和I；不要另开I进程。旧A-only配置只供第3步历史边界复现，新的联合入站应配套A/I工厂。

| 配置 | 默认及作用 |
| --- | --- |
| dispatch.max_running_tasks | 1，共享A/I及未来已注册种类的总执行额度 |
| dispatch.poll_interval_seconds | 60，队列及到期扫描的调度轮询间隔 |
| incident_check_interval_seconds | 14400，事件材料检查周期；检查无变化不续活动窗口 |
| automatic_window_seconds | 604800，正常完成时间起7天；未完成过则创建时间起7天 |
| retry_delay_seconds / retry_limit | 60 / 1，仅明确临时故障；关闭/超期不继续重试 |
| incident.max_alerts_per_diagnosis | 100，每次执行前按归并时间倒序、ID升序选择；不删除其他成员 |
| incident.scan_batch_size | 100，每次调度最多检查的到期事件数 |
| investigation_policy_file | 选择实际I模型视图、输出额度、请求Token预算及执行时限；文件hash须与加载策略一致 |

七天内已受理的首试即使排队跨期仍执行一次；关闭后未开始的请求跳过，已开始的完成但不重开、不重试。手动check/rerun开放事件不受7天限制。失败/unknown只结束本地占用，不设人工解除步骤；正常完成才更新last_normal_completed_at，首次失败也安排下次材料检查，允许新内容进入。

每轮先保存选择回执、原始材料及摘要、运行策略和Run/attempt绑定，再调用I。最近100条不是Token容量保证；完整请求超限保存准备后的请求和测量，task失败capacity_exceeded，不发模型、不分批、不重试。同内容同容量配置停止反复尝试；容量配置变化允许重新预检。

旧production_processing/processing_job直接incident动作已移除，人工发起通过E37登记任务。事件E37返回202任务回执；事件E23/E25提供input_selection与analysis_coverage，后者区分实际分析、待核及未分析成员。100/260可完整交付选入成员而仅部分覆盖事件；原告警DTO不变。详见[HTTP交接](../integration/incident-analysis-http.md)。

新装/升级复用128迁移和既有analysis-ingress安装项，无新增迁移；打包将[事件发布片段](../../deploy/local-investigation/analysis-incident-release-fragment.json)与HTTP、Swagger和静态审计页面一并纳入完整change发布。当前示例默认disabled，未变更21模型服务、消费者或真实4177。
