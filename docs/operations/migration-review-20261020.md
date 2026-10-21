# 已有迁移合理性与正确性审核

2026-10-20。审核对象是本仓库当前迁移结果、固定上游`34ca18c57dd4175539e5c6dd3d04a72dc057306b`及21实际运行版本。结论：**迁移路线和来源控制合理，源码迁入准确；处理语义仍有缺陷，不能判为整体正确或可开启常驻worker。** 本轮暂停3A-11-03实现，只审核及更新审核文档，没有修改运行代码、部署、模型或业务数据。

## 审核覆盖与证据等级

- 441项既有交付文件hash、19源码层合并后1803项文件hash匹配；1578个迁入原件的Git blob/SHA对应固定revision，90份依赖原件检查通过。没有发现services文件脱离来源清单。固定来源并不保证上游业务逻辑正确。
- 21四服务均健康、镜像与最新回执一致；当前API439、Agents184、Fusion55、Actions90个Python文件，共768个，逐文件与本地hash匹配。Agents仍显式disable1、审批提案0；没有为审核启动消费者。
- 四份离线探针执行当前生产函数的AST原文，以内存基础设施替身复现下述故障；不是重写一份预期实现自测。数据探针五场景、缓存/停止/跨失败offset各一组，均无真实网络/PG/Kafka/模型调用。另只读核实际aiokafka `send()` 返回交付Future的依赖实现。
- 预算hold、取消及五reader认证/来源/事务逻辑按当前源码核对。本轮未发现新的跨租户reader漏洞；这不等于对全API、所有工具、并发或真实故障做过全面验证。没有重复全仓回归或注入21共享服务故障。

## 发现（按修复优先级）

### R1 / P1：Fusion在没有持久交付结果时提交输入

[consumer.py](../../services/fusion/app/workers/consumer.py)的`_fuse_and_persist`在488—494行遇sink `UNAVAILABLE/FAILED`只计数，继续返回，`_consume_loop`在257行提交raw输入offset。PG短故障时，已经202受理的告警可能没有PG行，却失去正常消费者自动重投机会。两种状态的替身复现均为`commits=1`；这里的“丢失”指自动交付链越过输入，不是Kafka物理数据已被删除。

同文件504—507行只`await producer.send()`，未等待该调用返回的交付Future。独立于PG失败：即使sink已经INSERTED，后续fused发布Future失败，raw仍提交。实际安装的aiokafka实现最后`return fut`；替身复现为`inserted + delivery error + commits=1`，可出现PG有行但下游分诊消息缺失。

而且不能只在上述失败处加raise：248—250行捕获处理异常后只记日志并继续，同分区后续成功消息的commit仍越过失败项。补充探针模拟offset0失败、offset1成功，观察到`committed_positions=[2]`。这里Kafka位置由显式替身模拟，未验真实broker/rebalance。

两条方法与固定上游AST相同，是**上游继承缺陷**。移植原样正确不能替代已有告警服务的持久交付合同。修复须保护失败项后的连续确认水位或停止消费等待明确恢复，并同时定义PG结果、broker确认、重投与DLQ后何时可提交，不能只把计数/信封字段当作持久确认。还须与R3一起核恢复，避免仅延迟提交后重投仍丢关联。

### R2 / P1：普通分诊输入丢失告警正文和发生时间

[fused_alert_consumer.py](../../services/agents/app/workers/fused_alert_consumer.py)的`build_state`在336—364行手工投影字段，未携带`description/event_time/created_at`。合法输入若把破坏行为写在description、真实发生时间写在event_time，title简短且raw_event为空，产生的state和后续模型prompt均没有这些事实。

探针实际得到summary只含标题，raw state中description和event_time均不存在；它们在任何prompt长度截断或模型调用前已经丢失。**该遗漏继承上游**，本地风险分等适配没有补齐。不代表现有每个样例都受影响：旧p01把事实另写进raw_event，恰好绕过了此遗漏。只修改系统提示词不能恢复丢失的证据，应先修输入投影并限定验证。

### R3 / P2：source-v1缺行恢复永久丢失关联

首次Fusion处理已登记dedup/关联，但在PG插入前进程退出，重投会命中暖dedup。[fusion_engine.py](../../services/fusion/app/services/fusion_engine.py)169行直接返回`incident_id=None`，即使原关联缓存仍在。本地source-v1 [alert_sink.py](../../services/fusion/app/services/alert_sink.py)330行允许duplicate继续INSERT修复缺行，285行却把这个null写进首次元数据。

实际`process → persist → _insert_args`探针得到`INSERTED`和`socai2_fusion.incident_id=null`。之后ON CONFLICT和首次元数据保护不会自动补回它。这是**本地source-v1修复分支与新增关联元数据组合引入的缺陷**，无需假设整个Redis丢失。应验证崩溃后的缺行恢复仍采用可证明的原关联，不能靠重新生成任意事件号过关。

### R4 / P2：缓存重新采用被groundedness否定的原结论

[fused_alert_consumer.py](../../services/agents/app/workers/fused_alert_consumer.py)1032行先缓存原verdict/confidence，1048行才执行gate。下一条同指纹、不同Alert/Run在906—909行取回原结论，但没有原理由，1533行因理由为空跳过gate。

实际探针第一条FP/.99因虚构IP降为needs_review/0；第二条经broker lookup/claim仍变为cached FP/.99、groundedness=null、findings空。新Run持久保护不阻止不同告警的这种缓存复用。两次`auto_closed`均False，**本轮没有证明自动关闭或实际响应**；可确认的问题是错误高置信分类和理由丢失。顺序与gate均继承上游。缓存应采用最终受检结果及可追溯依据，不能复活被拒绝的原判断。

### R5 / P2：停止消费者报错会跳过子任务清理

[fused_alert_consumer.py](../../services/agents/app/workers/fused_alert_consumer.py)763—764行的`consumer.stop()`在drain/cancel保护之外；立即抛异常会直接退出。[main.py](../../services/agents/app/main.py)177—183行随后取消/await主task也在同一个try内，因此被跳过，后续却可能继续关闭PG池。

实际stop/EntityLanes函数探针使用协作、立即报错的consumer替身，stop返回异常时仍有一个运行child和一个lane，最后由审核脚本额外cancel/join才清掉。不是“不响应取消的第三方永远挂住”。上游已存在consumer.stop异常会短路的顺序，本地新增lane清理、10秒保护及main取消逻辑仍放在其后，未覆盖这条异常路径。应让必要清理在finally中独立完成；尚未对真实aiokafka注入此故障。

### R6 / P2：项目topic/group/DLQ缺失的准入判断错误

[3A-11-02旧回执](3a-triage-admission-config.md)37行及其机器回执，把常驻topic/group/DLQ称为默认且未配。实际[prepare_services_1g.py](../../deploy/aisoc21/prepare_services_1g.py)29行已设置`KAFKA_TOPIC_ALERTS_FUSED=socai2.alerts.fused`、`KAFKA_CONSUMER_GROUP=socai2-agents-triage`；[main.py](../../services/agents/app/main.py)128/130行读取，DLQ由worker455行派生为`socai2.alerts.fused.dlq`。

原1G私有env、11-02变更前快照和本轮21当前env三者一致。这一判断是此前协作助手审核不完整造成的误判，**不是运行代码新缺少功能**。正确限制为：项目映射已存在，常驻消费起点、逐tenant准入与持续消费尚未验；不能只移除disable开关启用。当前PROGRESS、工作约定和待实施计划据本审计纠正；旧冻结回执不覆盖，以本条作为勘误。

## 合理性判断与修复顺序

固定上游、先迁依赖再迁主链、按告警服务端范围收敛、复用21资源并隔离项目对象、保留旧事实/失败/unknown，均合理。源码、依赖、镜像和差异可追溯；没有证据支持全盘回退或重写上游。

不足是可靠性验收集中在Agents后半段，Fusion前半段的PG失败和发布确认仍有缺口；正常输入的材料投影也没有被现有合成样例覆盖。多批测试数量不能累加成整个服务端正确性的证明，提供某段来源也不等于模型采用或结论质量通过。

建议下一单项优先修R1/R3的Fusion持久交付与缺行恢复，再修R2输入投影；随后处理R4/R5并推进原提示词小批/新盲测。已记录的p01时间/授权理由、旧工具身份、事件/UEBA缺源和完整引用质量仍是既有未通过事项，本轮不重复当作新发现。保持worker关闭，三unknown及A积压不重调/退款，不为审核覆盖旧账本。

本轮新证据仅存工作站Git忽略目录`.local/aisoc21/migration-review-20261020`，0700/0600。机器摘要见[migration-review-20261020.json](migration-review-20261020.json)，内存探针和source/runtime hash可回查。审核没有修复上述代码，也没有重新验完整业务质量；未提交或推送。
