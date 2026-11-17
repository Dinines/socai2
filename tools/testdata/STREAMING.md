# 流式调查测试数据与执行入口

2026-11-16。当前新批使用 v2：中性固定来源、测试控制文件与业务材料分离，详见[材料清单](CATALOG.md)与[实际输入核对](../../docs/operations/evidence/model-blind-data-20261116-01/README.md)。历史活动数据已清空，Fusion 停止、调度未启动；新材料仅离线生成，没有重新投递或调用模型。后文 S01/S04 运行参数和 offset 是原批历史记录，不能视为当前启动基线；新批须重新冻结资源/时间/实体。

## 生成与验证

在仓库根目录运行。示例配置引用当前候选identity，全部生成参数必填；示例时间及batch仅用于离线材料验证，实际测试另选当时的时间和新batch。源码、候选身份/连接目标或配置改变时生成新目录，已有输出拒覆盖。

```sh
.local/conda-envs/socai2/bin/python tools/testdata/streaming_fixture.py generate \
  --config tools/testdata/streaming-fixture.example.json \
  --out .local/t2-streaming-dataset-example

.local/conda-envs/socai2/bin/python tools/testdata/streaming_fixture.py validate \
  --input .local/t2-streaming-dataset-example

.local/conda-envs/socai2/bin/python -m pytest tools/testdata/tests/test_streaming_fixture.py -q
```

`S01/alerts.jsonl`为3条实际RawAlert/source-v1格式；`S01/context-events.jsonl`为12条事件信封。S04两文件各1条，仅在第二阶段准备/投递。`background.json`和`knowledge.json`是待导入声明，未预造资产ID、索引或查询回执。`expected.json`只给核对器，`identity-map.json`实际映射为空，`actions.json`只表达步骤；输入加载不打开这三个文件。manifest保存合同源码/配置及产物摘要，`live_ready=false`不代表21已准入。

校验会拒绝输入、预期或当前合同摘要变化，即使重新计算文件hash也不能追认改写后的关联。此命令不读取服务实际结果，不能证明消息被消费或模型质量通过。完整直接回执见[T2离线批次](../../docs/operations/evidence/test-streaming-data-t2-20261115-01/README.md)。

## 21最小执行顺序及缺项

当前参数从[候选入站配置](../../deploy/aisoc21/streaming-candidate-20261115-01/ingress.json)和[候选身份](../../deploy/aisoc21/streaming-candidate-20261115-01/identity.json)读取，运行结论以同批实际回执为准。历史T1、旧发布配置及离线示例只说明原范围，不能作为本批运行值；配置与运行不一致时先记录差异，待提供方修复并读回后冻结新批。配置存在、资源创建和消费者就绪分别核对。

| 顺序 | 完成条件与供给责任 |
| --- | --- |
| 1 候选入口 | [独立库/身份](../../docs/operations/evidence/streaming-candidate-20261115-01/database-prepare-01.json)为123–129、32表/521列；[HTTP r2实际18424/18480](../../docs/operations/evidence/streaming-http-runtime-20261115-01/final-readback-01.json)通过TLS同库双池/TCP空态及80操作合同。r3新批3A/1I已由Kafka原生保存，HTTP成功建案及调查执行仍待；旧服务保持暂停 |
| 2 入站资源 | 当前[r3 ready-02](../../docs/operations/evidence/streaming-ingress-20261115-01/ready-02.json)核唯一Fusion、Stable/1成员及raw/raw_events分区0，沿既有位点继续；PG TLS/Redis认证/湖/Kafka SSL已验。旧r2 ready-01和启动失败保持历史，不作当前运行依据。实际AISOC_ALERT_STORE_SCHEMA=socai2，consumer→Socai2AlertSink同事务保存材料/initial任务，旧projection停止 |
| 3 归并门控 | 核`primary-entity-v2`的src_ip+首tactic，四告警同组、容量>=4、空起点。实际`correlation_window_seconds`必须覆盖首条消费至S04消费的完整耗时；合并不刷新索引TTL。超出则停止并记录新事件，不改关系/expected |
| 4 上下文单点 | 按真实湖导入入口写S01十二条并读回，核同租户/主机/类型、时间精度及`[start,end)`；核导入是否会额外提升成告警。背景/知识须真实来源准备与读回，缺项明确记录，不直接填调查结果表 |
| 5 业务单点及相邻链 | 冻结操作参数、预期与空起点后，先验证来源/A/I、HTTP受理读取/Case首轮的直接合同，再串代表性整链。必要单点身份与正式整链分开，不重派已结束批次 |
| 6 S01整链 | Kafka只发A01–A03；保存发送意图、ACK/offset与消费回执，通过真实HTTP读canonical、事件、任务、Run、结果。成功业务写读并入A/I之后的首次整事件建案，同key/管理编辑复用该Case；受理读回和启调度观察点由调查/HTTP统一安排，不提前另造案例。真实模型与真实查询均须有回执，模型未选工具记未查询 |
| 7 S04增量 | 先读回E13，再Kafka发A04；必须先发生I有效业务更新，再看到活跃Case检查/更新/上一轮比较。单A01 Case成员仍只有A01；固定成员不等于永久冻结同主机查询上下文 |
| 8 查阅/收口 | W2读取同环境真实ID，W3展示批次/任务/Run/原件及质量，W4独立打包；当前仍未完成。最后独立结束审计、统一正式发布及读回由负责人推进 |

旧`alert_kafka.send_kafka`仍要求Topic=`socai2.testdata.<run_id>.raw`。当前[S01分阶段发送器](streaming_send.py)已适配独立batch和明确candidate Topic，复用原逐消息ACK循环；新命令见下节，只有资源就绪通知及新批冻结之后才能实际运行。默认新batch、`no_cleanup`，不恢复旧清库脚本。

## 当前S01分阶段投递入口

分工：调查方独占资源/profile、Fusion启动和运行阻断修复；测试方负责发送器、新批冻结、实际Kafka投放及CH/PG断言/真实identity-map；HTTP方复用该映射和落库回执做只读联验。原T2/W2已过检查不重跑；[发送器直接验证](../../docs/operations/evidence/test-streaming-sender-20261115-01/README.md)已完成。首批来源范围失败保留，经[窄修复21项直接检查](../../docs/operations/evidence/test-source-scope-fix-20261115-01/README.md)及r3就绪后，[新批s01-ingress-20261115-02两道真实通过](../../docs/operations/evidence/test-streaming-s01-ingress-20261115-02/README.md)：12上下文、3A/1I/3真实来源/4accepted任务，0Run/模型，旧批原件与关闭基线保持。[HTTP同批35次GET](../../docs/operations/evidence/streaming-ingress-http-20261115-02/README.md)已通过来源/材料/双向成员/任务及无Run读取；不得重派两个已结束批次。后续进度由调查根对话统一维护PROGRESS。

步骤：①调查供给真实资源回执、候选profile及私密连接引用；②测试另选新batch/时间/实体生成材料，事前冻结expected；③prepare生成两阶段独立wire；④只发送S01-context十二条，核CH真实落库与0额外业务；⑤该读回通过后才发S01-alerts三条，核3A/1I及3A+1I共4条initial/accepted/source=ingress，0attempt/Run/模型；⑥将真实身份及原件一次性交HTTP核双向关联、成员及无分析结果。A/I/Case调度保持关闭，本子步不建Case或投S04。

### profile字段

[streaming-send.example.json](streaming-send.example.json)是未绑定资源的模板，包含REPLACE和零摘要，不能直接执行。12个字段全部必填，私密env内容不进入发送包；读取profile后不继承父进程KAFKA配置。资源回执至少`status=passed`，完整实际资源/起点由调查供给文件及其摘要追溯，程序不会把“能准备wire”当“服务已就绪”。

| 字段 | 分类与含义 |
| --- | --- |
| `schema_version` | 保留固定合同`socai2.streaming-send.v1` |
| `candidate_id`、`batch_id`、`tenant_id` | 部署必填；candidate绑定已准备资源，batch必须是本次新执行身份且与dataset一致，tenant与候选一致 |
| `topics` | 部署必填；raw/raw_events/fused/dlq四个准确名称，限定为`socai2.testdata.<candidate_id>.<role>`；本步只发前两个，CLI不能改topic |
| `producer_env_file` | 部署必填；**实际运行发送进程所在机器**的私密env绝对路径，由调查供给bootstrap/TLS配置；prepare不读取该私密文件，send时复用现行kafka_config加载 |
| `expected_bootstrap_servers`、`security_protocol` | 部署必填；与实际加载env严格一致，变化拒绝发送。SSL/SASL等材料沿当前Kafka合同，不因PG免CA而改变Kafka TLS |
| `timeout_seconds`、`request_timeout_ms` | 保留模板20.0秒/10000毫秒，字段必存；producer超时不超过单次发送等待，unknown不应用重试 |
| `resource_readback_file`、`resource_readback_sha256` | 部署必填；调查提供的实际就绪回执及原字节摘要。prepare复制原件并冻结，send再次核摘要 |

资源/profile明确后，在能够访问实际broker广告地址的运行位置执行；本机prepare可生成随后完整传递的prepared目录，send读取该目录冻结profile和wire，必须提供匹配合同源码，不能只转发bootstrap后假定Kafka全链可达。以下为接口用法；实际新批及原回执见下方，**已结束批次不得重复执行send**：

```sh
.local/conda-envs/socai2/bin/python tools/testdata/streaming_send.py prepare \
  --dataset .local/NEW-BATCH/dataset --profile .local/NEW-BATCH/sender.json \
  --out .local/NEW-BATCH/prepared

.local/conda-envs/socai2/bin/python tools/testdata/streaming_send.py validate \
  --prepared .local/NEW-BATCH/prepared

# 首道：只投上下文，ACK不等于入湖
.local/conda-envs/socai2/bin/python tools/testdata/streaming_send.py send \
  --prepared .local/NEW-BATCH/prepared --phase S01-context

# 完成真实CH/PG读回后才执行第二道
.local/conda-envs/socai2/bin/python tools/testdata/streaming_send.py send \
  --prepared .local/NEW-BATCH/prepared --phase S01-alerts \
  --context-readback .local/NEW-BATCH/context-readback.json
```

`prepared/receipts/S01-context.json`和`S01-alerts.json`为各阶段固定、独占回执；存在即拒再发，不提供另选receipt路径绕过的CLI，不复制prepared目录用于重派。确定发送前失败也保留回执，本轮不自动恢复；unknown或错误ACK停止后续消息，先按身份/offset读回调查。stdout只报告batch/阶段/状态/接受及未尝试数量，不打印异常秘密或env内容。

context-readback必须由真实CH/PG检查产生，字段为`status=passed`、`source=real_lake_readback`、同一`batch_id/tenant_id/prepared_manifest_sha256`、完整12个`event_ids`，以及`unexpected_alerts/unexpected_incidents/unexpected_tasks/attempts/runs/model_calls`均为0；文件可以附原件/查询/PG证据引用。只有Kafka的12个ACK不能生成这份通过回执。CH需另核原始正文、时间/实体/0值和查询命中排除；PG/HTTP按实际字段与业务身份核对，不从predicted canonical反填实际映射。

## 参数状态

| 参数 | 当前选择与实际状态 |
| --- | --- |
| 候选身份 | `deploy/aisoc21/streaming-candidate-20261115-01/identity.json`；生成时核tenant一致并存hash，服务实际就绪以负责人回执为准 |
| 四Topic与消费 | socai2.testdata.streaming-20261115-01的raw/fused/raw_events/dlq各1分区，生产端192.168.1.21:19093/SSL；Fusion group=socai2-streaming-20261115-fusion。r3沿旧批位点继续；S01新批ACK为raw_events 12–23、raw 3–5；同批S04为raw_events24、raw6，不重置起点 |
| Redis | 独立`socai2-streaming-redis-20261115`，内部6379、无主机映射、Fusion DB0、调度DB1、持久化开启；密码认证及A/I唯一调度实际执行已通过，调度容器已正常停止。**18479是test_api端口，并非Redis端口** |
| 湖来源与C4上下文 | 专用socai2_streaming_20261115.raw_events为48列，DateTime64(3, UTC)；S01两批24条，S04仅新增E13后25条。查询按tenant/src_hostname/class_uid及[start,end)，无账号/目的/namespace过滤；首轮Case C4实际已验，S04直接扩窗查询已验但因I失败没有新Case C4，不混记 |
| Fusion归并与执行 | 入站配置correlation/attack_chain窗口均86400秒、dedup窗口300秒、事件容量500；r3 ready-02核实际窗口和容量。新批source_ip=192.0.2.11，与旧失败批分开；原生保存和湖写入开启，额外提升/检测关闭。ingress.json的dispatcher/models=false是入站时点；随后独立analysis.json已真实执行本批4个A/I任务，结束后正常停调度 |
| 短周期 | 实际analysis profile为I20s、Case30s、retry5s最多1次、dispatch poll1s、自动窗口86400s；根侧装载及Run policy、HTTP同份lifecycle读回均已通过。原task按受理时保存的重试值核对；120s仍只供独立边界变体 |
| 模型 | 当前A/I单Run300s/24000 token、最多2次生成，A最多3查询、I0查询；Case1500s及单次模型300s等保持。实际aisoc-investigation→aisoc-test-investigation、tokenizer65536和policy已读回，本批4真实生成已完成。正文质量NOT_PASSED，不能由配置/结构成功推断内容通过 |
| 4177与HTTP取数 | 现有4177仍是静态快照；W1账本/8GET及[W2代理组件/TCP空态和错误](../../docs/operations/evidence/test-http-proxy-w2-20261115-01/README.md)已通过，W2非空/跨Run、W3页面和W4运行包仍待。候选HTTP18424/Swagger18480为r2/80操作，旧71操作合同不作本批代理依据 |

模型正文质量单独记录原答与问题；格式、引用范围、超时分类、保存/读回等程序阻断仍需修正。T2离线成功不核销真实Kafka/模型/HTTP或完整change。

S01 A/I阶段出口：[同批A/I统一回执](../../docs/operations/evidence/test-streaming-ai-20261115-01/acceptance-01.json)已通过4task/4attempt/4Run、9真实查询、原答与保存，以及[62次同源HTTP读取](../../docs/operations/evidence/streaming-ai-http-20261115-01/result.json)。I配对3A/9回执且结构覆盖3/3，旧4任务实际跳过无attempt/Run；模型正文问题独立NOT_PASSED。后续两Case及S04实际结果见下方，不沿用当时“尚未建案”的状态；W2代理非空/跨Run和4177新HTTP接线仍待。

## S04同批增量阶段

沿[S04冻结方案](../../docs/operations/evidence/test-streaming-s04-20261115-01/README.md)使用原dataset的S04两份字节，在独立prepared目录设置`phase_set=S04`和`baseline_snapshot_sha256`（已验两案首轮唯一快照）。默认`phase_set=S01`保留原入口；不同阶段不能混发。prepare只准备选定阶段，S04各1条，不复制或重派S01发送回执。当前root[实际归并窗口/profile回执](../../docs/operations/evidence/streaming-s04-20261115-01/preflight-01.json)已通过，原I索引仍有效；实际S04投递和入站结论以新目录回执为准。

S04-context必须带`--preflight-readback`，核同prepared/tenant/batch/首轮基线hash、实际E13/A04均不存在及业务基线保持。S04-alerts必须带`--context-readback`，核1条E13已真实入湖且相对基线的alerts/incidents/tasks/attempts/runs/model_calls增量全部为0；已有6个Run不需要清空。两阶段继续使用固定独占intent，unknown或已有回执拒重派。此阶段发送器及既有S01直接检查共16项通过，单点使用明确producer替身，不算真实投递。

两Case首轮已完成[统一验收](../../docs/operations/evidence/test-streaming-case-initial-20261115-01/acceptance-01.json)及58次结果GET；历史S01章节中的“未建Case”只描述该阶段。当前S04目标为I先有可用业务诊断再推动活跃Case后轮；单A01案保持固定范围。整案扩窗后network如果被选应包含E11/E13，不能照搬首轮排除集合。W2非空跨Run、4177 HTTP接线和发布仍后续。

实际S04来源两阶段通过，A04完成；I真实请求max_tokens3000、原答finish_reason=length/output3000，诊断失败并停止同输入自动尝试，无新Case任务/Run/比较。两案仍3/1成员，原6Run和原答保持。[134项失败保存核验](../../docs/operations/evidence/test-streaming-s04-20261115-01/failure-record-validation-01.json)不替代成功路径；2次真实生成共12027tokens，0重试、费用未知。原失败/单字质量问题保留，不修改配置或重派追认。发送封包须包含当前`services/fusion/app/core/kafka_security.py`；本次缺文件导致的发送前失败与补齐后的首次实际投递回执分别保留。
