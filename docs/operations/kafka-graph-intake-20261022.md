# Kafka消费入口统一准备告警图

2026-10-22。用户选择在调查/Agents模块收到fused Kafka消息后统一写图，避免回改Fusion。本批沿restore 2.1/3.1/3.4/4.1本地实施；验证及结束独审结果见文末，**未发布21、未启常驻worker，不代表当前线上Kafka已经执行这条新接线**。原[阶段交接](investigation-stage-handoff-20261022.md)、旧Run及质量失败保持。

后续补验：依赖补齐后已完成本地原消费者/API连接21 Kafka、PG、Neo4j的[有界真实联合](kafka-graph-joint-20261022.md)，一条新消息在triage入口前准备成功；该后续证据与下文本批85项替身合同分开记录，不扩大为已部署或模型调查通过。

## 实际职责与顺序

```text
Fusion处理/PG持久化/发布fused（本批不改）
  → Agents收到消息，校验schema及tenant/canonical Alert
  → 核原profile/shadow禁写范围与独立writer配置
  → POST原API /graph/investigation-context，以Alert为锚点
  → API从同tenant PG行投影当前Alert及其实体，真实Case存在时补成员边
  → 原分诊：恢复/抑制/分类/关闭/升级
  → 需要Graph/Deep时只GET已有图，准备回执与查询事实共同进入原Run工件
```

写图触发在`FusedAlertTriageWorker._process_with_retry`通过schema后、调用triage之前，覆盖之后可能抑制、关闭、不升级或复用首次结果的告警。每次delivery准备一次，内部triage重试不会再POST；Kafka重新投递仍可重复upsert同一tenant/Alert，沿原节点/边ID保持一致。它不是“每条Kafka消息新建一个图节点”：坏消息走原DLQ，legacy折合原PG告警行，未提升raw事件不在本范围。

Agents仅传tenant及canonical Alert ID，写图仍由API的`prepare_investigation_graph`/`graph_service`负责；不接受Kafka或模型提供任意节点/SQL/Cypher。显式Alert只投当前已核告警，避免自动解析Case后重复投整个Case、或当前Alert排在Case第51条后被截断。解析到真实Case时补该Case节点/成员边，保留已有边；没有真实Case不新建。显式人工Case准备仍保留原50条上限。

## 配置与保持的边界

- API与Agents均需`AISOC_ATTACK_CONTEXT_ENABLED=true`；默认false不新增请求。
- `AISOC_INVESTIGATION_PREPARE_KEYS_FILE`为现有tenant→独立writer映射，普通文件且权限0600或更严。准备Alert需要`alerts:write`；reader及永久七权限服务身份不因本批获得写权限。
- `API_SERVICE_URL`指向API；原context reader配置继续用于GET。即使writer存在，`fetch_attack_context`也只GET，不在升级或查询时再写。
- 原review-only、shadow和非live writer的禁写范围保持。worker关闭或没有消费时，这条入口也不会执行；本批没有开启它们。
- 缺writer、reader冒充writer、政策禁写、HTTP拒绝/失败、回复身份错配均保留明确状态/原因，不能视作投影成功。普通准备失败记录缺口后沿原分诊继续，不改变原budget/DLQ/offset合同；本批不保证故障后自动补齐所有图或新增恢复框架。

准备响应不仅检查HTTP200，还核顶层及projection内部tenant/Alert/scope；成功来源必须包含当前Alert。回执经当前delivery的ContextVar传入`build_state`，只接受匹配tenant/Alert的内部值，finally复位；消息里自带的`attack_context_preparation`不会被采纳。Bundle把入口回执与GET查询结果分开保存，三类Run工件继续记录实际准备状态和模型可见摘要。

## 当前验证范围

本批只做新增入口及直接消费/投影的本地合同验证，不发模型、不访问正式broker或业务PG/Neo4j、不改Fusion或原调查算法。HTTP/模型/PG/图驱动按对应测试使用替身；昨日真实Case图、四模型及Markdown证据保留原范围，不移作本批Kafka入口真实联合证明。

用户随后要求使用Conda项目环境，已创建`.local/conda-envs/socai2`；原/tmp临时venv不存在及初轮缺respx/opentelemetry/bcrypt的收集失败不计测试通过。新环境的依赖版本与最终日志保存在`.local/aisoc21/kafka-graph-intake-20261022/`；不修改原socai环境、部署依赖声明或lock以迁就本机环境。

源码审查发现并修正一个本批保护问题：shadow类别必须取原消息`alert.category`，不能从省略category的build_state投影求类；补类别敏感的定向例。另对新入口回执匹配按UUID规范比较，保留原Run/告警ID合同。更广的旧查询ID格式兼容、既有质量/图同步问题不扩成本批改造。

Conda最终直接测试共85 passed，三组文件不重叠：新Kafka入口24项，原context/orchestration/worker三文件47项，API投影合同14项。包含真实_process_with_retry与被拦截的HTTP POST、原信封tenant/canonical ID、准备先于恢复/早返回、重试仅一次、坏schema不写、reader不升writer、外/内回复身份及来源检查、profile/shadow禁写、回执隔离/防伪、Bundle纯GET与三工件采用；API验证当前Alert在Case前50条之外仍写当前告警。原弃用警告保留，不作为本批新失败或质量通过。

测试解释器为`.local/conda-envs/socai2/bin/python`（Python 3.12.14）；最终日志为`.local/aisoc21/kafka-graph-intake-20261022/`下`kafka-intake-tests.txt`、`agents-direct-tests.txt`和`api-direct-tests.txt`，早期收集失败另存。软件依赖下载发生过网络超时并在同一新环境补齐，未为运行测试更改项目pyproject/lock。实际包版本由本批environment.json与requirements-tested.txt记录，不能当成部署锁版本逐项一致。

本地增量版本保存在`.local/versions/kafka-graph-intake-20261022/`，16份选定源码/测试/依赖声明及测试环境版本、日志的原件/副本/归档一致；依赖既有Git基线和此前本地批次，不是独立安装包、镜像或整包发布验收。整文件中此前C2修改仍保留原未终审/未部署状态。机器回执见[本批JSON](../handoff/kafka-graph-intake-20261022.json)。

结束独审：未参与实现者kafka_graph_audit限定**ACCEPT，0项剩余阻塞**；核源码接点/身份/禁写保护、shadow修正、三组85项日志及16份版本原件/副本/归档。root的468个本地链接、OpenSpec strict、diff检查和Fusion源码未改检查通过。独审不扩大为真实Kafka/业务PG/Neo4j联合、模型质量、部署或常驻准入通过；完整change原5/15保持，不归档。
