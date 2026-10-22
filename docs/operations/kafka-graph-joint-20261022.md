# Kafka入口写图：真实联合验证回执

2026-10-22。在[本地接线](kafka-graph-intake-20261022.md)和[Conda依赖补齐](local-dependencies-20261022.md)之后，用本地API/Agents源码连接21既有Kafka、PG和Neo4j完成一次有界联合观察。**已证明合法Kafka消息在进入分诊前完成真实图投影；未执行本次业务分诊或模型调查，未发布21或启用常驻worker。**

## 输入与执行边界

采用全新合成告警，PG预存一行作为“已持久化fused告警”夹具，再向独立测试topic发布一条信封。该轮没有重跑Fusion，沿用其已有交付证据，不能称为新Fusion端到端测试。tenant和actor复用已有合成测试身份，不修改权限或数据归属。

| 项目 | 实际值 |
| --- | --- |
| 本次观察标记 | `66a9387b708a`（探针标记，不是调查Run） |
| tenant | `5594ae90-f57c-50f5-8332-328b3cad1679` |
| canonical Alert | `2365c4b6-58f2-4b9c-9610-2c0bf0ec62d1` |
| Kafka topic | `socai2.graphintake.66a9387b708a.fused` |
| Kafka group | `socai2.graphintake.66a9387b708a.agents` |
| 发布坐标 | partition `0`、offset `0`；一条发布，分诊观察入口一次 |
| 证据目录 | `.local/aisoc21/kafka-graph-joint-20261022/attempt3/` |

通过`conda run --prefix /Users/lychee/Documents/project/socai2/.local/conda-envs/socai2`执行[有界探针](../../deploy/aisoc21/probe_kafka_graph_intake_local.py)，继承已验证的native库激活配置。只启动本地临时API和单topic消费者，不调用原应用全量启动/DDL。Kafka沿既有SSL客户端配置；PG和Neo4j为21真实存储，没有HTTP/PG/图驱动替身。

本地API只挂原graph路由，保原JWT/service认证、tenant与权限检查。独立writer为新本地随机SECRET_KEY签发的五分钟JWT，按PG活跃用户实际角色/权限认证；reader为另一本地随机七权限只读服务身份。二者仅对该本地API有效，未创建21 API key；原永久服务身份不获写权限。真实LiveShadowModePolicy及其PG查询保留，本次tenant/class及通配策略允许写；`legacy`仅为本地隔离消费者配置，21常驻review-only/worker OFF不变。

## 实际顺序与结果

1. 原`FusedAlertTriageWorker.start`订阅全新空topic，确认本次唯一分区位置为0，再发布新信封。
2. 原schema通过后，`_process_with_retry`执行入口prepare，向本地原API发送canonical Alert和tenant；API核真实PG行并写Neo4j。
3. 原`triage`入口仅由观察接缝代替：`build_state`读内部可信回执，再直读同tenant/Alert的Neo4j邻域，确认写图已经完成，随后主动抛`BudgetHold`。
4. 原循环把本次处理保留为未完成并退出；不假造分诊结果，不进入重试/DLQ或消费确认。原日志中的`LedgerPersistError`为这次主动hold的预期终止，不是图准备失败。
5. 使用reader GET真实上下文并核PG及Kafka组位点，然后关闭本地进程和客户端。

实际API记录按顺序为`POST 403`（reader拒写）、`POST 200`（Kafka入口writer准备）、`GET 200`（reader查询）；没有在GET中再次POST。入口回执为`success`、`owner=kafka_consumer`、`scope=alert`，tenant/Alert及`source_alert_ids`均匹配当前PG告警，`truncated=false`。

该Alert邻域含5个节点、4条关系：

| 起点 | 关系 | 终点 |
| --- | --- | --- |
| 当前Alert | `OBSERVED_ON` | 新合成Host |
| 当前Alert | `INVOLVES_USER` | 新合成User |
| 当前Alert | `CONTAINS_IOC` | `graph-66a9387b708a.example.invalid` |
| 当前Alert | `MAPS_TO` | `Technique T1078` |

四条关系的`source_alert_id`均为当前canonical Alert，Host/User/IOC带同tenant；Technique沿原全局标签设计。这里是**锚点邻域5节点**，不能写成“全库新增5节点”，因为Technique可能已存在。关系表示来源告警报告的关联，不是已验证的攻击因果。

reader上下文返回：PG `attack_chain=empty`、Neo4j `alert_graph=success`、`attack_path=not_linked/no_linked_case`。其直接neighbors为4；另一个原有`blast_radius`遍历返回`total_affected=14`个可达候选，其中包含同tenant历史测试Alert/Case。原查询允许沿共享Technique继续遍历，因此不能把5节点/4边说成GET的全部候选，也不能把14个候选解释为本告警新增/确认受影响实体；本批不改变原遍历算法。

无Case告警能够完成图写入；没有为了准备图自动建Case或把它解释为完整攻击路径。结束时该Alert仍为`new`、`case_id=null`，对应确定性调查Run计数为0，Kafka该新group的committed offset仍为`null`。这条测试消息保留未确认，不进入正式group或重调旧输入。

## 失败与累计影响

| 尝试 | 实际情况及保留材料 |
| --- | --- |
| attempt1 | 沙箱连接预检`PermissionError`；未写PG或发布Kafka消息 |
| attempt2 | 已新增一条合成PG Alert，随后因环境缺greenlet停在API拒写检查；未建测试topic/发布消息，本地进程已停 |
| 原attempt3许可 | 用户要求先查依赖而中断，未执行；目录当时尚未创建 |
| 依赖补齐后attempt3 | 全新输入完成本回执的联合观察；新增一条PG夹具和一个隔离topic/group，发布一条消息并真实写图 |

累计保留两条合成PG夹具（失败attempt2一条、成功attempt3一条），不能只报告成功一条而忽略前次写入。此前失败不追认为通过。无模型、业务分诊/关闭、新调查Run或Case、正式topic/group交付、旧unknown/积压重放、21部署/重启、常驻启用或Git提交推送。本次无需再重复刚通过的85项合同或新模型矩阵；可选OTEL grpc exporter未安装的告警不影响本次数据库/图准备，也未据此扩安装或改配置。

本次真实观察、[机器回执](../handoff/kafka-graph-joint-20261022.json)和既有直接合同共同覆盖新接线的当前功能证据；不代替全分支、模型质量、故障补图/恢复、常驻准入或整个change完成。原5/15和旧质量失败保持，未参与实现者joint_graph_audit结束独审限定**ACCEPT，0项接线阻塞**，范围为本次真实入口准备、hold/未确认保护及清理，不扩大为模型/Fusion新联合或发布准入。

本地选定版本保存在`.local/versions/kafka-graph-joint-20261022/`，15份探针/依赖/真实证据的原件、副本与归档一致；writer/reader映射及私有配置不入归档。该选定增量依赖既有Git基线和此前本地版本，不是独立安装包、镜像或整包发布验收。OpenSpec strict、diff及Fusion/服务依赖锁未改检查通过。
