# F4：独立请求与事件驱动的 Case 更新

2026-11-15。核心直接测试、测试会话独立PG/Redis验证及[89次HTTP同源只读](http-readback.md)均通过；F4本机联验完成，第7步仍待F5。未部署或调用真实模型；Kafka整链仍在第11步验收。

不同operation_key不再归并task；同key仍幂等。同一Case/事件运行时，新请求保留独立身份等待；执行前读取并比较最新材料，已被前轮覆盖则skipped/no_changes，无attempt/Run/模型调用。pending按开始长度有限扫描，忙项不占另一空槽。同主体普通请求不能绕过已有失败任务的等待时间或一次重试上限；显式rerun含义保持。

Case自动检查沿“告警范围/分诊/反馈变化→有效事件诊断更新→活跃整事件Case”，单告警关联的首次A晚到不直接触发Case。手动check读取全部适用业务材料，历史关联事件与自动活跃事件范围分别处理。自动成员跟随及满额续建先核有效I，防止续建initial越过事件诊断；Case成员不被I选入范围裁剪。

## 实际验证

[测试会话独立记录](../test-f4-independent-20261115-01/README.md)保留31项离线测试，以及真实本机磁盘PG `127.0.0.1:28413/v12_upgrade_dev`、专用Redis上的两次新执行。模型/查询为明确替身，输入直接构造，不能替代Kafka消费或真实模型结论验证。20份受测源码/配置/驱动摘要前后一致。

[test-pg-01](test-pg-01/result.json)：6 Case、23 task（13 completed、10 skipped/no_changes）、13 attempt/Run（全部completed）、9 Result，22次模型替身回复，0真实模型。六组检查通过：

- N=2时，同案10个更新请求独立排队，另一Case仍能使用第二名额；同key重放不新增任务。
- 前轮固定1条告警，运行中加入的第二条留到后轮；后轮覆盖后其余9个请求跳过，不生成Run。
- 首次A晚到和事件新增成员但I未完成时，自动Case检查不扩员、不提交调查。
- 新I有效完成后只更新当前活跃整事件Case；历史Case和单告警Case保持。
- 历史Case自动check跳过，独立手动check完整完成，未合并丢失范围。
- 测试容量2满后，第三条告警在新I有效完成后进入关联续建Case并执行initial；原Case范围保持。正式100条默认未改。

[test-retry-guard-01](test-retry-guard-01.json)：真实PG/Redis、受控executor/时钟，共3次执行、0模型调用。首次故障后60秒前不重试；同主体新普通请求保留独立pending，其他主体可完成；原任务仅自动重试一次后retry_exhausted，新普通请求同材料跳过为automatic_attempts_stopped。

原始模型输入输出见[test-pg-01/calls.json](test-pg-01/calls.json)、[I调用](test-pg-01/incident-calls.json)；[保存快照](test-pg-01/snapshot.json)、[初轮冻结快照](test-pg-01/queue-snapshot.json)及测试会话包装回执保存实际配置指纹和来源。I模型回复前独立读取已验证事件对象及running任务可查；A和Case的相同边界复用F2/F1证据。

## 保留的失败及环境处理

pg-01前四组通过，历史Case手动检查因Case外事件成员的等级别名KeyError中断；原unknown保留。已修为Case外缺失等级数量，保留后台完整ID与范围，新增跨Case直接测试通过。HTTP对该部分59次只读核对见[原回执](http-partial-readback.md)，不能据此追认旧批完整成功。

pg-02/03及retry-guard-01受旧本机隔离库数据目录256MB tmpfs满影响，错误/不完整记录保留，不恢复旧任务。此问题与21磁盘无关。用户授权后完整备份并恢复到磁盘绑定新容器，34表记录数一致，见[存储定位](storage-readback.json)与[复制核对](storage-copy-readback.json)；原28412容器和数据未停未删。新测试独立tenant/batch，仅本轮配置改用28413。
