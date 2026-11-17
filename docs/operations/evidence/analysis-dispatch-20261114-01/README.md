# 统一调度第2步本地验收

批次起于2026-11-14，最终检查于2026-11-15完成。OpenSpec：[schedule-streaming-investigation-updates](../../../../openspec/changes/schedule-streaming-investigation-updates/tasks.md)，仅第2步队列与有限失败处理，未进入自动业务接线。

## 已验证结果

[pg-redis-05](pg-redis-05.json) **17项通过**，代码在运行期间未变化。真实本机隔离PostgreSQL `v12_upgrade_dev`、专用回环Redis容器及新租户；执行器、时钟和指定故障为可控替身，真实模型调用0、部署false。没有向4177加入这些程序合成Run。

| 核对内容 | 实际结果 |
| --- | --- |
| 队列与N | N=1/2；pending十条忙A后普通B启动；pending前两条A、第三条C能继续取到C；同tick填满N，Case/A/I顺序生效 |
| 串行/材料 | 同主体串行，普通通知归并；开始前最新材料进入实际保存的输入，运行中变化留下一轮；无变化不建attempt/Run |
| 有限失败 | 失败60秒后最多再尝试一次，同task、新attempt/Run/执行键；等待不加次数；T2归入T1不刷新时间/预算；耗尽后同材料停止，实际新材料可继续 |
| 明确意图 | 显式rerun不被普通通知合并/停止摘要跳过；它已覆盖材料时旧待重试跳过、原失败和次数保留 |
| 时间与状态 | 已受理首试跨7天仍执行且失败不重试；关闭未开始跳过，等待重试关闭/跨期终止；有效Retry-After晚于60秒时遵守更晚时间 |
| unknown及准备失败 | N=1时unknown本地结束后下一任务继续；原Run保持unknown/NULL ended_at。材料准备失败有attempt、无假模型Run |
| 最小收尾 | PG完成补写失败释放槽、不重复执行；Redis不可用仍保存已结束调用、不新领；重启重放完成回执或记中断/发现时间，不填假结束，不删除其他key |

[pg-redis-01](pg-redis-01.json)13项、[pg-redis-02](pg-redis-02.json)15项原回执保留；[03](pg-redis-03.json)16项新增“已覆盖的待重试保留失败并跳过”直接用例。05最终17项补验首次准备失败无摘要时，持续失败仍跳过、后来材料可读后可以继续；修正了未知摘要误挡以后新材料的边界。[04](pg-redis-04.json)因专用Redis重启后端口重新分配，在ping阶段连接失败、未进入业务用例；按实际端口更新私密测试profile后运行05，失败原件保留。各业务验证批次使用新UUID和租户，未重派旧Run、改写旧结果或清理数据库。控制故障导致的failed/unknown属于预期用例，不能当模型失败率或准确率。

[direct-checks](direct-checks-02.json)记录配置/错误边界/单实例入口与既有任务策略共10项离线检查、Ruff、OpenSpec严格校验和文档核对。[最终读回](readback-02.json)保存本批任务、attempt、Run和输入工件的实际关联；不把合成Run等同真实模型结论。

最终只读回14个本批租户：48个task、33个attempt、31个Run和31份输入；任务状态为22 completed、8 failed、11 merged、7 skipped，无遗留活动attempt。第一次只读汇总脚本在连接数据库前因某条同组记录未重复tenant字段而失败，已保留[原错误](readback-01-failed.json)；修正提取后读回成功，原业务用例及数据未改写。

验收后已[停止本批专用Redis容器](redis-stop-02.json)，退出码0；未删除容器、触碰其他Redis或清理PG记录。

## 实现及交接

核心入口`analysis_dispatch_runtime`、`AnalysisDispatcher.tick/serve`及FIFO/PG适配已接通。普通队列和pending只使用逐条LPOP/RPUSH及Hash/Set提示；pending按本轮开始长度扫描，N由本地活动句柄统一约束；没有Lua、多消费者领取或分布式事务。任务保存在PG，Redis丢失通知由待办补投弥补，原task_id持续可查。

新增[禁用配置示例](../../../../deploy/local-investigation/analysis-dispatch.example.json)、[发布片段](../../../../deploy/local-investigation/analysis-dispatch-release-fragment.json)及[运行/适配指南](../../analysis-dispatch.md)。默认N=1、轮询60秒、执行外层时限3600秒，全部显式配置。只允许一个配置租户、一个领取实例；同配置OS锁保护重复启动，不能把多个独立profile的各自N冒充全局N。

本步没有DDL增量、公共DTO改动或真实handler。HTTP对接已确认保持原submit/任务查询，公共pending及补写字段不新增；Case/I异步POST受理层已验证但继续不注册，必须等第4/6步实际handler闭环后才联验启用。HTTP候选81、正式71维持各自状态。

HTTP侧另以本批真实skipped/原failed attempt保存回执完成[DTO离线核对](../analysis-task-http-20261114-01/skipped-retry-contract-20261115.json)：reason=no_changes、原Run/失败、retry_count=0、next_retry_at=null均可保留，字段无需改变。任务指南已说明skipped也可能只是后续重试被跳过，不能断言此task从未执行。

原任务2.1的通用调度范围本地完成；2.3真实A/I/Case执行、2.2生产者及其余功能继续待办，整个change未完成或独审/归档。未部署21、提交或推送；主调查31/41和模型质量NOT_PASSED保持。下一主线为第3步新告警自动分诊接入。
