# 测试数据工具接入与小批验证

2026-10-22。用户要求接入上游测试数据能力并做一些测试。本批复用固定上游 `34ca18c57dd4175539e5c6dd3d04a72dc057306b`，先接“生成已有告警→本项目入口→Fusion处理”，不把测试工具迁入解释为调查质量通过。实施沿restore 2.1/4.1，原5/15与旧质量失败保持。

## 选择与交付

| 能力 | 本批定位 |
| --- | --- |
| `services/demo-producer` | 原版Go模块原样保留，供后续复用演示/负载机制；原入口仍为Ingest，本批不运行、不部署 |
| `tools/testdata/upstream/generate_eval_incidents.py` | 原版合成场景生成器，原字节及MIT许可保留；本批实际复用其场景 |
| `tools/testdata/alert_scenarios.py` | 项目测试适配器：生成单条ExistingAlert/source-v1请求、单独答案文件，显式有界发送并留受理回执 |
| Purple Team | 当前不迁入/启动。Atomic入口主要登记，Caldera需外部靶场；Self-play为内存/预设结果，不能作为真实检测证据 |
| Honeytokens | 当前不迁入/启动。生成诱饵描述，实际触碰检测依赖外部设施；适合作为未来一种上游告警来源 |

原版Demo Producer发`connector_id/connector_type/source_format/events`批量信封；项目`/api/v1/alert-ingress`要求单条已有告警及稳定UUID、来源事件、发生时间，返回202及canonical ID。不能只改URL复用原请求与accepted/rejected统计。本批适配放在工具中，生产API/Fusion、原算法与运行配置不改。

## 输入与答案分离

每次生成显式指定run标记、测试tenant、带时区的发生时间及小批数量。相同参数生成相同输入身份；新实际测试使用新run标记。原场景的标题、说明与合成telemetry是告警资料，`expected_tactics/expected_techniques/response_class/evidence_keywords`等评分材料单独保存，不放入raw_event或作为告警技术字段预先告知模型。明确且唯一的日志实体才映射到告警实体字段；缺失或歧义保持未知。

这些是合成场景，说明中本来就有攻击叙述，不能叫真实历史、盲测集、独立人工标签或检测成功证据。适配器把它们作为“上游已经产生的告警”投喂，不执行原始检测、不自动创建Case。若未来用于模型质量评估，应另核样本代表性、标注和输入中是否间接暴露答案，不能只据文件分离认定不存在泄漏。

生成默认只落本地文件；发送必须显式指定完整入口、认证环境变量和新回执路径。逐条受理，失败或未确认时停止，不自动重投。HTTP202仅证明入口确认发布，Fusion持久化/后续调查必须单独观察；已有失败输入与旧unknown不重放。

## 本批验证

2026-10-22晚间用户要求恢复执行。attempt02真实联测已通过；本增量结束独审限定ACCEPT、0项本轮必须修项，原change不因此完成或归档。[逐步恢复记录](two-projects-resume-20261022.md) · [机器回执](../handoff/testdata-tools-20261022.json)。此前仅收尾的停点保存在[两会话收尾记录](../handoff/session-closeout-20261022.md)。

- 工具离线8项通过，原日志在`.local/testdata/20261022/tool-tests.txt`；入口和Fusion各1项直接合同通过（每项3条告警），原回执在`.local/testdata/20261022/direct-tests.json`。认证/PG/Redis/Kafka为替身，未运行模型。
- 真实探针attempt01在生成/联网前因不支持的structlog level 100触发KeyError；失败回执保留在`.local/aisoc21/testdata-ingress-20261022-attempt01/receipt.json`。该次0新topic/消息/业务行/模型，未启动本地API。
- 探针先前已改用DropEvent日志处理；本次使用全新attempt02目录和输入ID恢复，未重投attempt01。23:22（Asia/Shanghai）实际执行3条合成告警，真实基础设施联测通过；详细结果和结束独审如下。

本地直接合同核生成数据实际经过API路由、身份信封与Fusion原处理方法；其中认证、PG、Redis、Kafka为明确替身。另准备有界真实基础设施探针，用本地最小API、独立Kafka topic、测试Redis前缀和21项目PG检查新告警受理、融合及持久快照，是否已执行以本节最终回执为准。

本批不发模型、不启常驻Agents、不部署21，不评估分诊理由、自动关闭/升级质量、调查Chain/Path因果或Markdown质量，不进行压力/长稳测试。那些能力不会因为入口数据接通而自动获得质量结论。

## attempt02真实结果（2026-10-22 23:22）

本地Conda运行原最小认证API与原Fusion消息处理方法，连接21项目Kafka TLS/PG TLS及Redis。测试tenant为`5594ae90-f57c-50f5-8332-328b3cad1679`，本轮run标记`7970e947a533`；生产租户及生产topic未使用。创建两个全新单分区topic：`socai2.testdata.7970e947a533.raw`、`socai2.testdata.7970e947a533.fused`，保留期1天。Redis所有键另加`socai2:testdata:7970e947a533:`前缀。

| 场景 | 输入Alert ID | canonical Alert ID | raw/fused各自坐标 | PG/首次快照 |
| --- | --- | --- | --- | --- |
| INC-EVAL-001 | `83851c04-4c0c-55a7-92d8-ef5dbf152f29` | `84b9d9fb-23e4-5311-a738-d02fe69b1185` | p0/0 → p0/0 | inserted / new / snapshot一致 |
| INC-EVAL-002 | `84330c09-6d3b-5285-9706-7aa05275b5ea` | `95fa20d8-ee85-568e-be10-b03e629e50bc` | p0/1 → p0/1 | inserted / new / snapshot一致 |
| INC-EVAL-003 | `8515036f-a9d9-5c01-bbde-7ef9131da979` | `c43f40a0-d66c-55be-b2c3-b37a0b178307` | p0/2 → p0/2 | inserted / new / snapshot一致 |

输入→实际调用→输出逐步如下：

1. 从固定生成器选3个场景，生成3份payload与3份独立expected文件；保留manifest/hash。生成材料为合成叙述，仍非盲测集。
2. 联网前读核活跃测试用户同tenant、新canonical行不存在、Redis/Kafka可用、两个新topic不存在。仅在这些条件满足后创建本轮topic并启动本地24930端口的最小API；不运行API完整lifespan/迁移/后台任务。
3. 用仅对本地API有效的五分钟随机JWT逐条发送一次。3次HTTP202，`processing_confirmed=false`；真实raw消息offset0/1/2逐条与入口确认坐标匹配。
4. 显式调用原`FusionWorker._process_message`。真实PG插入3条Alert，status均new、case_id均null；三个不同incident由原规则给出。本次未启动Fusion消费循环，两个观察消费者均无group、不提交offset。
5. 原持久快照从PG取回并真实restore，与独立fused topic的3份原FusedAlert正文一致；信封另加的`alert_row_id/persist_outcome`分别核为canonical ID/inserted，不包含在快照正文比较中。两topic end均3，不以HTTP202代替这个判断。
6. 捕获材料本地核验：标题、描述、严重性、raw_event、事件时间、host/user/IP共8字段从生成输入→raw→fused保留；时间以同一时刻比较。预期答案四类键未进入raw/fused。`source_event_ids`保留原事件引用并按原worker追加上游Alert ID；最初观察误要求列表完全相同而失败，已核原源码合同后修正观察，保留失败，不改业务或重新发送。
7. 本次关联Run数0、模型调用0，未进入Agents/图/调查。原MLScorer未训练，采用原启发式回退；数值只记录实际结果，不评价模型、关联或检测质量。临时本地API和客户端均已停止，cleanup_errors为空。

原始回执及捕获文件在`.local/aisoc21/testdata-ingress-20261022-attempt02/`：`receipt.json`、`send-receipt.json`、`raw-observed.json`、3份`fused-*.json`、3份`snapshot-*.json`、`material-checks.json`和可重放本地文件检查的`check_materials.py`。`private.json`含临时本地签名配置，保持私有，不进入版本快照/公开交接。新增6条Kafka消息、3条PG测试告警及12个被访问Redis键；仅当前观察时的实际状态，不清理旧数据。新topic保留，Redis沿原TTL自然过期。

这次是测试工具接线验收，不是常驻Fusion消费循环/offset恢复测试，也不覆盖生产自动分诊、调查内容、图因果或性能。生产v1已启用状态沿原发布授权保持，本次无部署或运行配置更改。

## 结束独审与留存

未参与实现者`resumed_projects_end_audit`只读独立核三条payload/expected的manifest hash、HTTP/raw/fused坐标、三份snapshot规范hash及正文、8字段保留、答案分离和原source_event_ids转换合同，限定**ACCEPT，0项本轮必须修项**。未重新联网、发模型或跑业务/测试；结论只覆盖本次工具接线及文档交付，不代表完整change或调查质量通过。原工具8项离线＋2项替身合同仅复用，未重复运行。

本轮工具和探针与恢复前快照字节相同；相关工具/测试/文档、原attempt01失败、attempt02合成回执及逐步记录选择性留存在`.local/versions/two-projects-resume-20261022/`。不含私有签名/凭据，不是独立运行包或发布镜像。根检查的64个相关本地链接、Markdown围栏、JSON、diff和OpenSpec strict通过；原任务5/15、旧失败/unknown/预算保持，不归档或Git提交推送。

## 后续如何使用

先用固定小批场景验证接线；后续新增与我们关注点匹配的明确对照样本，例如同主机但不同事件、跨主机的同一攻击、明确授权和缺少授权资料、只有候选关联但缺乏行为证据。期望结果必须独立写在答案侧，实际从Alert/Run、工具返回和报告取结果。Replay评估可复用分诊评分，但原路径不执行完整调查；Agent Quality/指标引用检查也不能独自判断整段结论是否受证据支持。

操作命令与字段说明见[工具README](../../tools/testdata/README.md)，固定原件来源见[来源清单](../../tools/testdata/upstream/source-manifest.json)。后续真实运行使用新输出目录和输入ID，保留原失败回执。
