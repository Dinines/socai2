# S01实际入站：上下文通过，告警来源范围失败

2026-11-15，21候选`streaming-20261115-01`，新执行批`s01-ingress-20261115-01`。本批按[分阶段发送与即时持久化设计](../../../../openspec/changes/schedule-streaming-investigation-updates/test-data-design-20261115.md#t2后续子步s01分阶段kafka发送与即时持久化)执行，真实Kafka、ClickHouse和PostgreSQL；**上下文单点通过，告警来源范围断言失败，整体未通过**。无模型调用、attempt、Run或Case，调度保持关闭；没有投S04、清理或重派已发送输入。

## 冻结来源

- [本批入站配置快照](ingress.json)、[发送配置](sender.json)、[输入与独立预期](dataset/manifest.json)、[两阶段发送manifest](prepared/manifest.json)；实际候选r2镜像/配置从当时最新ingress读取，不沿旧T1/public投影路径。
- 唯一准入为[ready-01](../streaming-ingress-20261115-01/ready-01.json)，SHA256=`18d87b25a03a962b158e7b176c33e4453d4cf3276c4ca771cc80d76453d31b9d`。prepared manifest SHA256=`65a525874a6e430c072fb96b51b23d337949044face0ffd82e407e529b0138d8`，本批全过程未变。
- 本批`base_time=2026-11-15T09:45:20Z`，冻结时设为当前时间前80分钟，使最晚上下文仍在过去。主机/账号及来源UUID使用新batch；IP属于文档测试网段。
- 实际来源connector由调查方按冻结输入登记，[来源读回](connector-readback.json)和[reader必要接线](support-final-readback.json)独立保存。未修改业务DTO或直接插入调查结果。

## 两道真实结果

| 阶段 | 实际结果 | 判定与证据 |
| --- | --- | --- |
| 投放前 | 普通PG reader/TLS、CH reader、connector同租户；湖0行，本步13类调查记录均0 | [preflight_03](readback/preflight_03-readback.json)通过 |
| S01-context发送 | raw_events分区0、offset 0–11，共12条ACK，无未尝试 | [固定发送回执](prepared/receipts/S01-context.json)仅证明接受 |
| S01-context保存/读取 | 12条完整原件、租户/主机/账号、毫秒时间、0/false/空数组保留；认证/进程/网络查询各命中3条，另一目的与另一账号正确纳入，异主机、起点外1毫秒和右端点正确排除 | [真实读回](readback/context-readback.json)、[湖快照](readback/context-lake.json)、[PG零额外业务](readback/context-pg.json)通过；不是模拟查询返回，也不等于C4已被调查执行 |
| S01-alerts发送 | raw分区0、offset 0–2，共3条ACK，无未尝试 | [固定发送回执](prepared/receipts/S01-alerts.json)，引用同批上下文门控摘要 |
| S01-alerts保存/读取 | 3告警/3材料/3首次工件、1事件/3成员、3A+1I共4条initial任务，accepted/source=ingress；0attempt/Run/分析结果/Case | [PG快照](readback/alerts-pg.json)及[失败回执](readback/alerts-readback.json)；来源引用为6而非3，不能判本阶段通过 |

进一步对保存快照逐项核对：三条canonical身份与冻结预期一致，原始raw_event/OCSF/raw_text保持，latest_material关联和未启动任务状态正确；三条**exact_source_scope均失败**。见[实际观察映射与检查](identity-map-observed.json)，该文件明确`failed_source_scope`，不作为通过的HTTP交接映射。HTTP方尚未执行本批联验。

## 确认的程序阻断

每条告警输入仅包含一个实际上下文事件ID，保存后却为“该上下文ID + 告警信封自身ID”。三个额外ID不在12条湖事件中，`source_scope.received_count/retained_count`均从1变2且`complete=true`。

当前路径是`event_schema.validate_raw_alert()`把`payload.id`解析成`source_event_id`，再由`consumer._fuse_and_persist()`追加到原`source_event_ids`；原生sink把两项都保存为`relation_kind=source_event`。这会扩大来源范围，属于程序问题，不能记为模型质量后置或把冻结预期改为6。

调查方已接手入口边界修复。原批材料、refs、任务和失败保持；不得回写原件追认、启动这四条任务、重派旧消息或清空资源。修复及新候选实际加载回执供给后，再冻结有界新批直接复验；若复用此candidate，须记录旧批基线、使用新的归并IP/来源身份，分别核新批增量与旧失败记录保持，不把同租户旧记录当成新批污染或新成果。

## 已解决的测试准备问题

1. 首次临时核对容器的用户身份无法写证据目录；尚无连接/消息。调整为目录所有者的UID/GID后，保留[原启动失败](invocation-preflight.json)。
2. 普通reader缺少`public.connectors`的SELECT，调查方随功能补齐；[原失败](readback/preflight-readback.json)、[定向权限证据](reader-access-02.json)及成功preflight_03分别保留。另一次辅助探针自身语法失败保存在reader-access-01，不作运行缺陷或通过计数。
3. 文件包漏传空`prepared/receipts`目录，首次发送进程在创建回执、实例化producer之前失败；[诊断](send-context-failure-diagnostic-01.json)、[原invocation](invocation-send_context.json)及[目录修复](packaging-repair-01.json)保留。补原目录后才发生首次实际发送；未改阶段固定回执路径、输入或expected，没有重发已有发送意图。

[freeze-01](freeze-01.json)至[freeze-05](freeze-05.json)记录投递前准备脚本/运行包修正，prepared manifest保持不变；源脚本和必要旧版保留。`readback.py`只以普通reader读取，`remote.py`只启动候选镜像临时进程，未改Fusion/HTTP镜像或重启服务。原始stderr留在21受控private目录，不收集凭据正文。

本批不是完整调查验收。真实模型仍是后续必测，正文质量另记；W2非空/跨Run、W3/4177和W4、S04、Case首轮/更新/比较及后置功能维持未验状态。
