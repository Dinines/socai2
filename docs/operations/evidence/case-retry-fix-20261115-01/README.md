# F3：Case已知连接失败重试

2026-11-15。本项核心直接验收及[52次HTTP同源读取](http-readback.md)通过；第7步整体尚未通过。未部署、推送或调用真实模型。

完整Case执行器原先先把连接失败写为unknown，使调度器无法应用已确认的60秒/一次重试。现在模型调用边界保存确定未发送的失败回执、结束该模型步骤；确认同Run没有其他running/unknown模型或工具后记Run failed及ended_at。已有unknown不改写，ReadTimeout继续unknown。C3、Deep/C6和完整执行器沿同一收尾判断；完成的步骤和原答保留，不伪造Result。无新DDL，公开状态/接口不变，内部waiting对外仍为accepted。

[pg-03](pg-03/result.json)使用真实隔离v12_upgrade_dev/专用Redis及完整Case执行器，4个Case、6个Run、6份明确模型替身回复、4份受控连接故障、0真实模型：

- C3 ConnectTimeout：首Run failed有结束时间；60秒前不启动，跨过等待后同task新attempt/Run完成；原失败不变。
- C6 PoolTimeout：保留本轮已完成C3及请求/响应；第二次仍失败后retry_exhausted，共一次自动重试。
- ReadTimeout：Run unknown、ended_at为空，任务本地已结束且不重试；N=1的下一Case完整完成。

本批任务仍冻结retry_delay_seconds=60、retry_limit=1。仅测试store.now及C1捕获时间使用一致的0/61/122秒偏移，所有业务取数、保存和调用顺序仍走真实实现；没有修改正式配置或旧记录。[保存后核对](pg-03/saved-readback.json)验证失败/未知/完成步骤及旧原件未被后轮改写。13项原分类/协议检查和6项新增未发送/已有未决操作边界检查通过，Ruff通过。

早期批次保留：pg-01测试误将公开accepted当成内部waiting，实际上完成了默认60秒后的重试，但该测试仍记失败；pg-02测试只移动store.now而未同步C1捕获时间，第二attempt被PG时间约束拒绝，原unknown不复活。修正验证驱动后使用新pg-03，不改写前两批。最初离线检查未指定policy文件的2项环境失败也保留，指定显式policy后13项通过。

复现入口[validate_retry.py](validate_retry.py)，需显式私密配置及新的batch名；[原件](pg-03/snapshot.json)、[模型替身回复](pg-03/calls.json)、[失败回执](pg-03/faults.json)、[源码指纹](pg-03/source-hashes.json)。本项不替代Kafka整链、真实模型、21 TCP或独立结束审计。
