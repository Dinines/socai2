# T1：21 调查测试环境只读预检

2026-11-15，观察窗口约北京时间11:24–11:34。**T1检查完成；目标流程测试尚未就绪，等待相应版本发布。** 本轮只读数据库目录/必要状态摘要、Kafka元数据、Redis计数及HTTP GET，未启停服务、部署、迁移、清理、投消息、登录写入、调用模型/嵌入或新建调查。本机仅保存文档和脱敏证据。

负责人在检查中更正“本地环境没有使用了，都用21”，随后要求“先单点再集成”“21版本和设计不一致就等发布”。因此最终目标为`sting-infra21`，本机停用容器不列为21缺陷；不恢复本机环境，也不为旧部署补接口。本轮到T1结束，不开始T2/W1或业务测试。

## 1. 实际就绪情况

| 项目 | 本次实测 | 结论及后续供给 |
| --- | --- | --- |
| 环境身份 | SSH到21；业务库`aisoc`、schema `socai2`，配置租户`00000000-0000-0000-0000-000000000001`；当前基础服务共享现有业务资源 | 当前运行环境明确；本批尚无独占数据库/租户、Topic/group、调度namespace和上下文数据范围，不把共享库当空测试库 |
| PostgreSQL | 实际16.15，迁移123–127，28表450列；450列名称、基础SQL类型及空值与127字典一致；487约束均validated、147索引valid/ready、54业务触发器无disabled | **已部署127结构检查通过**。128任务三表、129排除表及续建/接收字段未部署，不能运行目标异步链。精度/字符长度未单独比对；触发器只查目录，未用写操作验证 |
| 已有调查记录 | Run状态：completed 14、failed 11、pending_update 8、unknown 3；本次汇总无running | 属历史资料，保留。unknown不重投、不改成功；pending_update不是新任务队列。因任务表不存在，不能提供目标task/attempt一致性结论 |
| Kafka | 应用SSL `192.168.1.21:19093`可读Topic/分区/begin/end/committed；Fusion和投影各Stable/1成员，已提交分区lag为0 | 运输与既有投影可观察；尚未投本批数据，不证明新A/I/Case自动链成功。新投影/任务受理配置随目标版本提供 |
| Agents旧消费者 | `AISOC_AGENT_KAFKA_DISABLE=1`；本次查询旧组不存在，无已存位点 | 保持关闭，不将旧Agents作为新调度器，也不把“无组”记成lag=0 |
| Redis | 现有API/Fusion/Agents分别DB8/9/10，PING成功，DBSIZE均0；默认`socai2-analysis:*`无键 | Redis服务可用；无新调度配置，空键不证明任务系统已准备好。须提供本批明确DB/namespace与唯一调度器配置，不能猜用旧DB编号 |
| 湖与上下文 | 通过实际HTTP容器配置连接ClickHouse `aisoc`，读到`raw_events`及48列；PG存在assets/users/tenants/aisoc_kb_documents；图/产品主机来源开关false | 既有来源基础可读，尚无本批告警配套上下文或逐工具命中回执。资产/用户身份、日志查询范围、缺失来源由各模块给出准备/读回方式 |
| 知识 | 当前Qdrant集合`socai2_knowledge_qwen06b_1024` GET 200、green、7 points、1024维；配置embedding为qwen3-embedding:0.6b | 元数据可读，不代表本批三种用途检索或知识后台任务已通过；未调用嵌入 |
| 模型 | 运行alias `aisoc-investigation`→`openai/aisoc-test-investigation`，配置上游`192.168.1.43:8000/v1`；实际策略hash `a3298006…`，已记录单Run额度/时限和输入文件hash | **仅配置核对**，未做连通生成/质量测试。运行策略仍为已发布旧版本，首次真实请求留给对应单模块验收 |
| HTTP | 容器`socai2-http-api:main-a6660267-full`，实际OpenAPI版本`main-a6660267-20261114`；64业务操作，`livez/readyz`均200 | 与历史交接及目标候选不同，按用户要求**待发布**。不能从healthy推断合同就绪 |
| HTTP业务读取 | 无凭据GET告警/事件/Case列表及已有Case均401；实际OpenAPI声明HTTPBearer，`SOCAI2_HTTP_CONTEXT_FILE`确未配置 | 目标默认可信接入尚未在当前进程生效；不新增权限项目，不登录绕过本次观察，不改当前服务 |
| Swagger | `18080/handoff/openapi.json` GET 200，71业务操作；与实际64操作不同 | 静态文档与实际运行合同不一致，统一发布时同步，再复验准确method/path/字段 |
| 新公共HTTP | `/analysis-runs`、主体`analysis-tasks`、Case `related-cases`实测404，实际OpenAPI无挂载；Case更新/定向/综合亦未挂 | 区分候选已有但未发布、核心仍未完成、后置未实现三类，不退回旧同步入口跑目标流程 |
| 4177 | 首页200；`/_workbench/status`返回enabled=false/source=dsn，原三案快照保留；测试API无路由 | 页面可访问；新的测试只读API/调查HTTP适配/批次查阅仍待实现和发布 |

本次只核21实际资源。开发工作区仍有已验候选和历史本机库，不能据此认定21已具备该能力。源码参考及未提交状态见[source-baseline.json](source-baseline.json)，运行身份见[runtime.json](runtime.json)；凭据未输出。

## 2. 版本差异：等待发布后的复验

当前64操作是静态71的子集，缺少以下7项；属于既有供给在当前运行版本中的差异，**与候选新接口未发布分开登记**。路径均省略`/api/v1/socai2`。

| Method | 当前缺失路径 |
| --- | --- |
| GET | `/alerts/{alert_id}/review-candidates` |
| GET | `/alerts/{alert_id}/same-host-alerts` |
| GET | `/cases/{case_id}/story` |
| GET | `/cases/{case_id}/exploration-candidates` |
| GET | `/cases/{case_id}/exploration-base` |
| GET | `/cases/{case_id}/exploration` |
| PUT | `/cases/{case_id}/exploration` |

记录编号：T1-V01实际64/静态71不一致；T1-V02目标可信接入与实际401不一致；T1-D01迁移128/129未发布；T1-R01新任务/调度/投影接线未发布；T1-W01测试API及4177 HTTP模式待实现。V/D/R项等待统一发布后核版本、配置、增量和实际请求，不在本轮修旧环境。已交[HTTP协作回执](../http-test-alignment-20261115-01/README.md)；HTTP侧维护产品接口交接，本聊天维护测试方案。

原始合同：[实际OpenAPI](live-openapi.json)、[静态Swagger OpenAPI](swagger-openapi.json)；具体请求、状态码、错误体、进程命令、合同差集见[HTTP原始回执](http.json)。无凭据GET可只读复验；本批未提交业务操作，无task/Run可关联，不创建伪造ID来补齐缺陷单。

## 3. 各模块须提供的接口和交付物

接口沿[IF00–13合同](../../../../openspec/changes/schedule-streaming-investigation-updates/test-interface-readiness-20261115.md)，下表是21实际落点。HTTP先与核心明确用例及输入输出，前端按合同使用；内部阶段无需全部HTTP化。

| 责任模块 / IF | 发布或测试前须提供 | 放行范围 |
| --- | --- | --- |
| 运行维护/测试 IF00 | 21显式测试profile；库/schema/tenant、Topic/group、Redis DB/namespace、来源范围及启用服务清单；版本hash；必要清理的精确plan（当前no_cleanup） | 资源就绪后仅放行对应单点测试 |
| 数据库/调查核心 IF03/06 | 128/129增量及同版本核心、任务/attempt/主体状态/Run读取；Case容量/续建/排除用例与样本；保留历史约束 | 生命周期、持久化、分配单点；不因受理成功宣称Case执行完成 |
| 入站/Fusion/投影 IF01 | RawAlert与日志信封、明确Topic及消费组；持久来源身份/事件归并回执、native投影和A受理；重复/held的读回方式 | 先逐模块单点，再Kafka→Fusion→投影局部集成 |
| 上下文/业务后端 IF02 | 日志准备和process/network/auth查询用例及窗口；资产/用户的实际身份映射与读回；知识文档/集合/三用途查询合同；逐源可用/空/失败状态 | 上下文查询单点通过后才让A/Case依赖它；文件服务仍由业务后端负责 |
| 调度/A/I IF03/05 | 唯一调度器profile、已有A/I factory、任务受理/执行/终态及周期用例；真实模型入口、计量、策略、原答工件；I check/rerun及冻结覆盖 | 先任务/调度/A/I各自验证，再A→I局部集成 |
| HTTP IF04/05/06/11 | 发布对应核心版本和可信接入；任务列表/详情、统一Run、完整steps/artifacts及原文链接；异步I、分配回执/related-cases；恢复既有7项供给及一致Swagger | TCP合同单点通过后才能作为集成驱动；HTTP侧列清真实request/response/error样本 |
| Case首轮 IF07 / 原步骤6 | 建案initial task→真实C1–C6/必要Deep→Run/结果/步骤/原件；handler、配置、独立输入样本及持久读回 | 先Case阶段与首轮模块，随后建案→执行集成；check/rerun归步骤7 |
| Case更新/H IF08 / 原步骤7 | `POST /cases/{id}/investigations`的check/rerun、无变化跳过、H/前序变化、持续扫描和比较；新后轮结果可读 | 对应单点及合同通过后，接持续调查集成 |
| 定向/综合/知识队列 IF09/10/12 | 保留合同、测试输入、未实现与后置状态，待各自供给时验证 | 已按最新主线后置，不作为本期1–7验收前置；目标完整覆盖仍保留 |
| 独立测试服务/4177 IF13 | batch/operation/expectation/quality/evidence只读API，调查HTTP读取适配、真实身份映射、live/archive标识和发布包 | 先账本/API/读取适配/页面各自验证，再接完整流程展示 |

现有模块历史证据可作为单点基线，但须核版本与适用边界；不能将历史ASGI、真实模型或本机库结果写成此次21通过。完整单点与集成准入见[测试规划§2.1](../../../../openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md#21-先单点再集成的执行层次)。

## 4. 清理预览与等待发布期间的边界

本轮清理计划为 **no_cleanup，预计删除0**。当前资源中有历史失败/unknown、已保存上下文及其他模块资料，且本批尚未分配执行身份；没有证据说明需要删除任何记录。保留PG全部既有记录、Kafka Topic/分区/提交位点、Redis资源、湖数据、知识向量/原文和4177三案。Redis空库、lag=0均不是清理必要性的依据。

后续准备优先使用新batch/来源身份以及在21明确隔离的测试资源；由显式profile决定范围。若必须重置，再列具体资源、过滤条件、预计数量、外部引用、历史保护约束、备份和保留核对；共享Topic不能按tenant删除，不能套用旧31张public表/全部`socai2.*`Topic重置脚本。等待发布期间只完善单点数据/预期/合同，不向旧环境投放；发布完成后先重验T1受影响项，再按单点→合同→局部集成→端到端推进。

## 5. 证据、复用及未验边界

- [target.json](target.json)：本次显式目标及超时，不含凭据；[run_readonly.py](run_readonly.py)经SSH stdin执行已审核探针，不在21落脚本，输出须选未存在路径。三个可复用入口为[目录/结构](inspect_remote.py)、[Kafka](inspect_kafka.py)、[HTTP](inspect_http.py)；[依赖检查](inspect_dependencies.py)包含首次Kafka失败，单独Kafka补证为准。
- [runtime.json](runtime.json)保存结构与初次HTTP，辅以[schema-comparison.json](schema-comparison.json)；[dependencies.json](dependencies.json)保存Redis/湖/知识/模型配置；[kafka.json](kafka.json)保存所有指定Topic位点及组成员；[http.json](http.json)为最后补证。均为时间点观察，未进行写入型业务验收。
- [readiness.json](readiness.json)为IF00–13的机器可读快照，开发供给与21运行状态分别记录；后续候选交付不自动成为runtime_ready。[资料检查](checks.json)确认strict、相关diff、JSON/Python语法及本地链接检查通过；不作为业务测试通过。
- Kafka首探针使用无group客户端加AdminClient失败，记录`KafkaConnectionError`；后续已部署status及同模式无订阅消费者读取成功，组状态由broker内部`kafka:29092`元数据命令读取。未改broker/服务/超时配置，不将探针失败冒称生产故障；未订阅、消费消息或提交位点。
- 初版HTTP探针把health正文`status`覆盖到同名HTTP字段，旧回执保留；`http.json`用独立`http_status`补证200。初探测根`/swagger-config.json`与`/api/config`为404，非实际合同地址；正确Swagger与4177状态入口已补证，不将猜测路径404列为服务故障。
- 元数据可读不等于数据语义、真实模型、幂等、任务执行或完整链通过。只读身份为现有运维角色；业务连接目标来自实际容器配置，未用写操作验权限。未检查或清理其他项目资源，也未声称全库/全接口数据对账。

本次保存探针/文档属于验收证据，不建设通用测试框架。原任务勾选、旧失败、模型质量结论保持；T1完成不等于整个change验收或可发布。
