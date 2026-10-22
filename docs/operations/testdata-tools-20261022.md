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

本增量未完成，2026-10-22按用户要求收尾留存；完整续接入口见[两会话收尾记录](../handoff/session-closeout-20261022.md)。

- 工具离线8项通过，原日志在`.local/testdata/20261022/tool-tests.txt`；入口和Fusion各1项直接合同通过（每项3条告警），原回执在`.local/testdata/20261022/direct-tests.json`。认证/PG/Redis/Kafka为替身，未运行模型。
- 真实探针attempt01在生成/联网前因不支持的structlog level 100触发KeyError；失败回执保留在`.local/aisoc21/testdata-ingress-20261022-attempt01/receipt.json`。该次0新topic/消息/业务行/模型，未启动本地API。
- 探针已改用DropEvent日志处理，修后未重跑。真实基础设施联测、最终回执及本测试工具增量结束独审仍待续；本次收尾不补跑，也不把工具迁入认定为整个增量完成。

本地直接合同核生成数据实际经过API路由、身份信封与Fusion原处理方法；其中认证、PG、Redis、Kafka为明确替身。另准备有界真实基础设施探针，用本地最小API、独立Kafka topic、测试Redis前缀和21项目PG检查新告警受理、融合及持久快照，是否已执行以本节最终回执为准。

本批不发模型、不启常驻Agents、不部署21，不评估分诊理由、自动关闭/升级质量、调查Chain/Path因果或Markdown质量，不进行压力/长稳测试。那些能力不会因为入口数据接通而自动获得质量结论。

## 后续如何使用

先用固定小批场景验证接线；后续新增与我们关注点匹配的明确对照样本，例如同主机但不同事件、跨主机的同一攻击、明确授权和缺少授权资料、只有候选关联但缺乏行为证据。期望结果必须独立写在答案侧，实际从Alert/Run、工具返回和报告取结果。Replay评估可复用分诊评分，但原路径不执行完整调查；Agent Quality/指标引用检查也不能独自判断整段结论是否受证据支持。

操作命令与字段说明见[工具README](../../tools/testdata/README.md)，固定原件来源见[来源清单](../../tools/testdata/upstream/source-manifest.json)。后续真实运行使用新输出目录和输入ID，保留原失败回执。
