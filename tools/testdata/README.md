# 有界合成告警工具

2026-10-23已按[迁移修订计划](../../docs/operations/testdata-migration-plan-20261023.md)补场景选择、正式Kafka wire/发送与结果观察，保留原HTTP工具。逐步实际验证及限制见[本批回执](../../docs/operations/testdata-migration-execution-20261023.md)。

`alert_scenarios.py` 将固定上游的场景生成器输出转换成当前 `POST /api/v1/alert-ingress` 的**已有告警**合同。默认只生成本地文件，不发送网络请求。稳定 `run-id + tenant + scenario-id` 产生稳定 UUID；相同输入生成相同字节。`event-time` 必须显式含时区，数量为 1–20（默认 3），输出目录拒绝覆盖。

```sh
.local/conda-envs/socai2/bin/python tools/testdata/alert_scenarios.py generate \
  --run-id local-example-01 --tenant 11111111-1111-4111-8111-111111111111 \
  --event-time 2026-10-22T08:00:00+08:00 --count 3 --out .local/testdata/local-example-01
```

产物是 `manifest.json`、`payloads/001.json` 等单条请求以及单独的 `expected/001.json` 等期望答案。Manifest记录来源提交、数量、文件hash与告警ID。发送端只读取payload，不把 `expected_tactics`、`expected_techniques`、`response_class`、`evidence_keywords` 送入模型输入。host/user/IP只取telemetry明确字段，存在多值时不猜选。不会预置Case、Incident或MITRE期望标签，也不会修改Fusion。

场景标题、描述与telemetry仍是上游人工编写的合成叙述，含有攻击解释；**它们适合接线/材料传递验证，不能据此宣称盲测准确率、检测质量或攻击链质量通过**。上游expectations是模板期望，不是本系统实际结果，也没有提供TP/FP标签。没有实际采集、检测或厂商动作。

只有明确执行 `send` 才发送；凭据从指定环境变量读取，使用当前API的Bearer认证。应先设置指向本批受控租户的短期凭据，并使用隔离测试入口：

```sh
.local/conda-envs/socai2/bin/python tools/testdata/alert_scenarios.py send \
  --input-dir .local/testdata/local-example-01 \
  --url http://127.0.0.1:24930/api/v1/alert-ingress \
  --token-env SOCAI_TESTDATA_TOKEN --receipt .local/testdata/local-example-01-send.json
```

发送最多20条，每条只请求一次，禁止重定向、不自动重试。回执文件拒覆盖，以0600权限创建；请求开始前先落 `started_outcome_unknown`。网络错误、非202、缺少确认坐标或合同不一致就停止，保留未发送数量。202与Kafka坐标只记为 `accepted_not_processed`，不能代表Fusion处理、图写入、分诊或调查成功。中断/超时后也可能已受理，应检查原回执和原告警，勿用新回执盲目重发。

上游 `services/demo-producer/` 四文件整体原样迁入，生成器原件位于 `upstream/generate_eval_incidents.py`，MIT许可及所有原件SHA256见 `upstream/LICENSE`、`upstream/source-manifest.json`。原Go producer面向 `/v1/ingest` 的事件批，不兼容本项目已有告警入口；本轮保留原件，未运行其演示/负载模式。

离线工具检查（使用已安装项目依赖的Conda环境，不访问真实broker/模型）：

```sh
.local/conda-envs/socai2/bin/python -m pytest -q tools/testdata/tests
```

实际验证与边界见[测试工具回执](../../docs/operations/testdata-tools-20261022.md)：2026-10-22的3条新隔离输入已通过真实入口/Kafka/Fusion/PG，未进入模型或调查；离线/替身结果单独列出。逐步恢复及原失败见[执行记录](../../docs/operations/two-projects-resume-20261022.md)。

## Git提交与运行材料

工具源码、直接测试、固定上游原件/许可/来源清单及不含敏感正文的说明应提交。生成的payload/expected/wire、投放回执、PG快照、模型请求/回复、工具结果、私有配置及本地版本快照统一留在`.local/`，该目录已整棵忽略；当前没有`.local`文件被Git跟踪。若在工具目录下临时运行，也可用已忽略的`generated/`、`runs/`、`private/`目录。

不使用全局`*.json`或`testdata/`忽略规则，避免漏掉应审查的来源清单和离线夹具。CLI的`--out`可指定任意路径；选择其他目录时应先用`git check-ignore -v 路径`核实，不能认为命令自动替任意输出目录配置Git规则。原始prompt/响应与凭据不应复制进公开文档；只提交必要的结果摘要。

## 正式Kafka测试输入

可重复`--template-id`选择上游模板，顺序按参数保留；保留模板原索引、场景ID及telemetry。未指定仍取前N条（默认3）；指定模板时数量默认为所选数，若另传`--count`必须一致。不会按新run-id自动替换模板内的主机、用户、IP或日志时间。

```sh
.local/conda-envs/socai2/bin/python tools/testdata/alert_scenarios.py generate \
  --run-id kafka-example-01 --tenant 11111111-1111-4111-8111-111111111111 \
  --event-time 2026-10-23T08:00:00+08:00 --template-id vpn-new-geography \
  --out .local/testdata/kafka-example-01

.local/conda-envs/socai2/bin/python tools/testdata/alert_scenarios.py prepare-kafka \
  --input-dir .local/testdata/kafka-example-01 \
  --tenant 11111111-1111-4111-8111-111111111111 \
  --out .local/testdata/kafka-example-01-wire
```

两步均不联网。wire补`identity_version=source-v1`、`source_alert_id=id`，身份预测使用工程现有Fusion RawAlert模型；记录原payload/wire/hash及模型来源hash。生成器的`run-id`是测试批次标记，不是业务Run UUID。转换及发送不打开expected文件。

Kafka配置从显式`--kafka-env`文件读取，至少包含`KAFKA_BOOTSTRAP_SERVERS`和`KAFKA_SECURITY_PROTOCOL`；TLS沿原校验证书机制，用`KAFKA_SSL_CAFILE`指定CA。可使用原Kafka客户端证书/SASL配置，回执不写凭据。发送器不创建topic、租户或启动消费者，操作者须先准备受控测试租户及独立topic。

```sh
.local/conda-envs/socai2/bin/python tools/testdata/alert_scenarios.py send-kafka \
  --wire-dir .local/testdata/kafka-example-01-wire \
  --tenant 11111111-1111-4111-8111-111111111111 \
  --topic socai2.testdata.kafka-example-01.raw \
  --kafka-env /absolute/private/kafka.env \
  --receipt .local/testdata/kafka-example-01-kafka-send.json
```

仅接受`socai2.testdata.<run-id>.raw`，拒绝误指正式topic。发送前校验全部wire及身份，回执拒覆盖并以0600/原子替换保存。每条先留`started_outcome_unknown`再发送；ACK记录坐标和`accepted_not_processed`；未知/异常停止后续，不应用层重试。Kafka客户端内部可能重试，idempotent producer不代表跨进程exactly-once；超时后禁止换回执盲目重发。后续业务处理仍需观察。

## 真实Fusion接线探针

`fusion_probe.py`在新批次中自行调用发送器，不能先手动`send-kafka`再对同批运行探针。它使用显式基础设施文件，先核测试tenant及身份/topic/Redis前缀未用，再创建raw/fused两个单分区、一天保留topic，验证原Fusion处理方法、PG首次快照与fused材料。没有Agents/模型，也不验证常驻Fusion消费循环或offset恢复。

```sh
.local/conda-envs/socai2/bin/python tools/testdata/fusion_probe.py \
  --wire-dir /absolute/new-batch-wire \
  --env-file /absolute/private/fusion-test.env \
  --out /absolute/new-probe-output
```

环境文件必需`DATABASE_URL`、`REDIS_URL`、Kafka bootstrap/protocol、`KAFKA_TOPIC_ALERTS_RAW/FUSED`及`SOCAI_TESTDATA_REDIS_PREFIX`；topic必须匹配本批`.raw/.fused`，Redis前缀为`socai2:testdata:<run-id>:`。允许原Kafka证书/SASL及`PGSSLMODE/PGSSLROOTCERT`，拒绝其他字段和变量插值。文件使用0600；探针不读取旧actor草稿或隐式私有目录。

## 调查来源记录场景（ClickHouse）

`investigation_fixture.py generate`离线生成一条告警和三条固定网络观察事件：匹配目标、另一目标、窗口外。要求显式`--run-id`、`--tenant`、带时区`--window-start`和新的`--out`目录；不联网、不读取答案参与投放。事件UUID、主机/IP、绝对时间和来源原文与告警一致，action仅为观察、outcome为unknown。

`lake_fixture_probe.py --input-dir <fixture> --tenant <uuid> --config <private.json> --out <new-attempt>`用原LakeWriter写入准确三条，再用独立reader读回47列、原文hash和匹配/反例。配置仅接受writer、reader两对象，各含host/port/database/user/password；两者必须同后端但不同账号。执行前须准备独立测试tenant和表级INSERT-only/SELECT-only身份；本工具不建立数据库行级隔离。一次flush、先落attempt，失败或结果未知不自动重试。完成后撤回writer权限；私有配置及原文留.local。

入湖验证通过后，才对同fixture运行原`prepare-kafka`与`fusion_probe`；后者仍关闭LakeWriter，避免重复入湖。PG source_event_ids中Fusion追加的输入Alert UUID与湖事件UUID分别核对，控制事件不得列为来源。本批实际回执见[逐模块实施记录](../../docs/operations/unified-investigation-implementation.md)。这不证明常驻事件Kafka消费、调查模型或恶意判定已验。

## 持久结果读取（原工具）

```sh
.local/conda-envs/socai2/bin/python tools/testdata/observe_results.py \
  --manifest /absolute/batch/manifest.json \
  --receipt /absolute/kafka-send.json \
  --dsn-env SOCAI_TESTDATA_READ_DSN --ssl-ca /absolute/ca.crt \
  --out /absolute/new-observed.json
```

DSN由指定环境变量提供；单个只读事务限定tenant和canonical ID。支持原HTTP回执、Kafka身份预测或显式`--canonical-map`（同批tenant/run_id与records中的alert_id/canonical_alert_id）。预测与PG来源身份核对分别记录；批次中未发送项保持未尝试/缺失。可用`--snapshot /absolute/observed.json`替换DSN/CA离线重读。

观察包括实际Alert/Run、事件、工件正文/hash、MD及成本。`Run completed`与调查`partial`分开，自动关闭不要求调查报告；未记录用量、未知调用及unpriced不填成0。工具不读取expected、不自动判语义质量。完整正文输出只保存在私有本地文件。

## 两例自动分诊/调查探针

`agents_probe.py`是临时本地原worker/API运行器，先启动并等待`consumer-ready.json`，再由驱动通过raw→原Fusion投放。观察`progress.json.committed_count`后才发下一例，原worker完成两条并提交offset后退出；不直接写fused、创建Run或替代业务分支。本批专用驱动和合成对照样本随回执保留。

私有配置显式提供`run_id,tenant_id,fused_topic,group,dlq,env_file,api_port,reader_keys_file,writer_keys_file,neo4j_config`，相关文件均0600。`neo4j_config`沿现有`uri/username/password/database`合同；所有topic/group属于本批，启动核空topic起点。env须接原预算/只读资料身份及必要图准备权限，并明确关闭外部动作；不以空数据冒称工具来源可用。

```sh
.local/conda-envs/socai2/bin/python tools/testdata/agents_probe.py \
  --config /absolute/private/agents-config.json --out .local/verification/new-agents-probe
```

保角色/模型/提示和业务限制；仅测试包装器设SDK retry0/45秒、出站请求最多14次，逐次保存请求正文、可见回复及真实工具结果（不含认证header）。网关内部provider尝试仍须另核。写入输出目录的`stop-request.json`可协作停止；不把断点续跑或调查质量当作本探针保证。
