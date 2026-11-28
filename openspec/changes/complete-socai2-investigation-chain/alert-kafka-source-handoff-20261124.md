# 冻结 OCSF 告警的 Kafka 来源与接续

2026-11-24。沿[告警验收数据来源与发送职责](es-ocsf-test-chain-20261124.md#当前告警验收的数据来源与发送职责)完成本组告警的来源核对、21 入站、A 分诊及同源 HTTP 读回。本步归主 change 3.7、3.21；8181 使用受控交接，业务写入由前端独占。事件归并沿现有入站流程，事件诊断、Case 与跨模块验收按各自阶段安排。

## 已核来源

唯一输入为 `.local/testdata/es-ocsf-chain-20261124-01/alerts.jsonl` 及同目录 `dataset-manifest.json`。10 条裸 OCSF Detection Finding 与第二批评审前 10 行逐字节相同，UID 唯一，原始时间保留。`alerts.jsonl`、`context.jsonl` 和汇总文件的 SHA-256 均与冻结清单一致。上下文已有独立直写回执，Kafka 告警输入只取 `alerts.jsonl`。

21 首段归档包的候选文件与本机冻结文件逐字节一致。实际发布者为 [`tools/testdata/alert_kafka.py`](../../../tools/testdata/alert_kafka.py) 的 `send_records`，已核归档代码与当前版本同摘要。原 `kafka-send.json` 有 1 条 ACK，逐行摘要、来源、Topic 与在运目标 profile 绑定相符。该条湖原件和坐标核对通过。首次告警交付失败保留，后续从同一湖记录恢复并成功保存告警及材料，原批已完成 A 和正式读回。该条沿原回执复用。

其余 9 条在已核首段、分页、资产发布账本及原独立数据集运行目录中无发送尝试或未知 ACK。分页组 26 条与资产组 1 条的 UID 与冻结组无交集。已撤回的三条合成夹具、其他 OCSF 批次和历史直写上下文均排除。逐行判定、归档定位和摘要比较结果保存在 `.local/validation/alert-kafka-source-handoff-20261124-01/`。发送前再用新批次的目标 Topic、现有正式租户和指定 UID 查重，已有或未知记录先对账。

## 本步执行及直接验收

| 顺序 | 实施与依赖 | 直接验收 |
| --- | --- | --- |
| 1. 绑定目标及冻结发送清单 | 复用已验的 21 Fusion、ClickHouse、PostgreSQL 和调查 HTTP 配置，从实际运行服务读取目标及身份。接续批次根在 21 的 `/opt/sting-aisoc-socai2/validation/alert-kafka-source-handoff-20261124-02/`，用同批 `runtime.json`、`profiles/ingress.json`、`consumer.json`、`selection.json`、`receive.json` 与 `delivery.json` 显式绑定专用 Topic、消费组、`lyc` 来源和正式 `aisoc`。连接配置留同批 `private/`。原独立数据集的 profile 仍保留。 | 按冻结行和原 ACK 确认排除已发送行，验证候选均可通过既有入站选择及接收投影。目标和正式 HTTP 同租户，专用 Topic 未使用。仅按该组 UID 和对应时间范围核对湖、告警来源或接收回执。 |
| 2. 一次 Kafka 发布和落湖 | 在核准的专用 Topic 启动有界消费，使用原 `send_records` 逐条发布剩余冻结裸 OCSF，原字节、UID、时间保持。归档逐条 ACK，未知即停止并沿既有记录核对。 | 核每条 ACK 的 Topic、Partition、Offset 与消费提交，ClickHouse 按同 UID 和坐标读回与冻结行完全一致的原件。消费限本批 Topic。 |
| 3. 告警和首诊登记 | 用既有湖告警选择、Fusion 接收及持久交付，每次至多两条，确认提交后进入下一次。负责人明确保留在运联合调度。入站可按原规则登记关联事件及其任务，同租户 A、I、Case 依在运策略处理，无专门派发。 | 用 PostgreSQL 核回执、告警、当前材料和自动 A 任务同源且只登记一次。按既有 HTTP 列表、详情、材料、当前 A 和精确 Run 核原文及身份。已有 A 复用原执行，附带自动任务状态仅记事实。 |
| 4. 交接 | 在受控目录保存冻结行→ACK→湖→告警、材料、A 任务与 Run 的对照，交统筹供调查 HTTP 与 8181 使用。 | 两段回执能共同覆盖批准的 10 条，已确认告警 ID 与当前 A 可逐条读回。页面联验由指定会话完成，核心本步在交出实际读回后结束。 |

沿现有 IC07 记录区分本组有界交付与持续接收能力。遇实际阻断时，先核已提交边界，保留原失败并仅修本组阻断。原始业务数据、配置值和模型输入／原答保存在受控目录。

首次 21 预检目录后缀为 `-01`。该次核实联合调度启用，和告警入站共用正式租户，领取接受及等待任务的路径涵盖 A、I、Case。预检脚本随后误将正式 18024 的既有绑定限制为 loopback，停止在发布前。原记录保留，接续以当期 HTTP 容器和部署回执端口校验正式入口。

## 实际接续结果

`-02` 预检按冻结 UID 在正式 PostgreSQL 与 ClickHouse 各确认 1 条已保存，剩余 9 条无冲突并通过原输入投影。已保存条目的同源材料、现行 A 结果和指定 Run 均经 18024 实际读回，其映射位于远端同批 `private/existing-alert-handoff.json`。

正式目标和原账本一致后，原发布者仅一次接续发送 9 条。9 条全部取得 ACK，消费提交核至最后位点，湖中原文字节与 ACK 的逐条坐标均一致。沿既有持久交付分 5 次成功提交全部 9 条。`private/kafka-send.json`、`lake-confirmed.json` 与各交付回执留同批目录。联合调度继续按原策略处理。

首个全组快照已核 PostgreSQL 告警、材料及初诊登记 10 条。18024 列表、详情和原件均按同一 ID 读回。A 当时为 8 完成、1 运行中、1 已受理，新告警关联 4 个已受理 I 首次任务。

续读确认 10 个原 A 任务及对应 10 个指定 Run 全部完成，交付状态均为 `complete`。正式 18024 在列表、详情、材料、当前 A 和指定 Run 核对 10 条通过。与首个快照逐行相比，ACK、告警、材料和任务身份一致。新入站告警关联的 4 个 I 首次任务观察为 2 已受理、1 运行中、1 失败，其中 2 个已有 Run。复用首条的关联 I 首次任务已完成。全组在该快照未见关联 Case。以上 I 和 Case 状态随原调度产生，本步验收范围为告警。

## 交接和历史清理保护范围

本机 `.local/validation/alert-kafka-source-handoff-20261124-01/alert-http-handoff-private.json` 保留 10 行冻结原件、ACK、湖引用、当前材料和 A 任务／Run 的首个对照快照。`retention-scope-private.json` 列出本组 10 条、首条原批及新批 Topic 与账本、关联事件和已登记任务，并保护独立湖已验的 52 条上下文。清理时从这些精确根读取当前依赖，以包含快照后新保存的 Run 与工件。

同目录 `history-separation-private.json` 列出已比对的两个历史批次，共 27 条。分页与资产归档的 UID、Topic、来源均与保护集合无交集，附其 Kafka、湖及交付账本位置。旧合成夹具沿调查 HTTP 的原回执。清理操作由调查 HTTP 会话执行，使用明确批次边界。

完整交接为同目录 `alert-http-handoff-1795524843952048578-private.json`，并已生成 `retention-scope-final-private.json`，含当前任务、Run、事件依赖和 52 条既有上下文的保护范围。原阶段快照保留。调查核心在正式 HTTP 读回和受控交接处收口，8181 由页面执行方接续。
