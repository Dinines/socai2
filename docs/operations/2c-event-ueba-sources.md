# 2C-03：已有事件历史与UEBA来源

日期：2026-10-20；批次：`2c-sources-20261020`。本批完成来源盘点和缺源返回验证，**普通事件/UEBA实际数据消费未通过，整个2C仍未完成**。没有新增采集、检测、UEBA生产或事件湖。

## 输入 → 实际读取 → 结果

| 输入/入口 | 实际读取 | 结果及边界 |
| --- | --- | --- |
| 21共享ClickHouse | 原受控账号查数据库、业务表及全表读取授权 | 账号具有全表读取授权；存在`sting`库，无业务表，也无`aisoc.raw_events`。不是权限受限导致的空表清单 |
| 21旧`sting_ueba_test` | 只读事务精确计数`sting_ueba`下6表 | anomalies、entity_baselines、event_results、input_events、peer_baselines、signal_current均0行；没有可用旧UEBA材料 |
| 21 Kafka | topic清单 | 56个非内部topic中没有标准`aisoc.raw_events`/`ueba.anomalies`；旧测试链topic保留，未冒充外部日志源 |
| 20参考环境 | 容器/有效API设置/DNS、PG表统计、Kafka起止offset | 无ClickHouse容器，API内`clickhouse`无法解析；UEBA topic起止均0。raw_events仅分区0 offset `[0,1)`一条消息 |
| 20保留消息 | 无group、无提交、显式分区读取一条，仅导出hash/字段名 | 保留`connector_id/id/normalization_version/ocsf_event/tenant_id`字段；未发现简单test标记，但这不能证明是真实业务日志。没有复制消息体、接入新API、扩建历史库或宣称质量通过 |
| 新项目API | 认证`POST /api/v1/graph/investigate/query`，两个测试tenant调用entity_timeline | HTTP200，`available=false`、`rows=[]`、`row_count=0`及明确lookup failure；缺源与成功无匹配分开。当前lake host为localhost，启动迁移关闭，未改指向共享服务 |
| Agents当前工具 | 在已安装生产镜像中独立调用`call_investigation_tool` | 当前有效配置因空Bearer产生`LocalProtocolError`，返回available=false，尚未抵达API。不得写成“已成功调用、查无记录”或HTTP401 |
| Agents受限探针 | 仅独立进程stdin传入短时`lake:query`测试key，调用相同方法 | A/B两个tenant均收到API同一缺源结构；未改变运行中服务凭据、配置或自动worker，不等于生产工作负载身份已接通 |

PG的investigation_events/run_events是调查账本，2C-02的alert_history是先前告警，都不是普通事件遥测。本次未遍历其他项目OpenSearch的业务文档；没有外部tenant/字段合同，不能据此宣称所有资源均无日志。

## 验证与保留

原版`services/api/tests/test_investigation_tools.py`在既有锁依赖测试镜像、禁网环境中**50项通过**。其中tenant参数绑定、忽略注入tenant、行数/时间限制和故障区分使用查询替身；不作为真实事件库跨租户验收。

真实HTTP共12项：两次清单、两次查询、一次请求参数tenant注入、缺失数据类、未知工具、匿名401、缺scope403及三次key停用401；另有三次停用后复核401。Agents实际生产方法另调用3次。因实际库缺失，请求tenant注入没有泄露数据，也**不能证明真实数据行隔离**。

36条已有告警不可变材料摘要保持，134迁移记录保持；21原36容器与18卷、20原16容器元数据在各自盘点前后保持。未重建/重启服务，未改变镜像/配置/schema，未投递新告警，未触发模型或厂商动作；网关原13次成功调用计数保持，费用仍unknown。两测试tenant/用户保留，3个测试key均停用；凭据仅在受控私有文件。

首次盘点分别因旧UEBA schema和Kafka容器端口假设失败，修正探针后完成，未改服务。主探针完成全部请求并停用key后，末尾容器快照相等断言失败；当时失败快照未落盘，原因未确立，可能有并行测试的临时容器。随后只执行finish-only复核，原始/复核36容器和18卷完全相同、旧告警hash相同、key仍停用；未重建样本或重复工具调用。失败事实保留在[机器回执](2c-event-ueba-sources.json)。

## 后续门槛

本轮缺源适配停在明确未接状态，保留2C开放项；有可用只读来源及tenant/字段/时间/来源合同后再恢复。至少需要一个真实可引用事件、另一tenant同名实体、合法无匹配和依赖失败四种输入，经认证API及Agents实际消费；UEBA还需生产方时间/有效期/来源语义，不以重放刷新TTL证明新鲜。当前不开启Fusion UEBA订阅或lake writer。

工具清单的`backed_by_data`静态列出7个已实现SQL工具，**不能当作本环境数据已接通或ready指标**。返回值目前准确报告缺源；清单及生产Agents API身份在后续实际工具接线时处理，不能用清单标志推动自动启用。

下一单项为[3A-01受控自动分诊前置](3a-triage-entry-plan.md)：先解决规则抑制在ledger写入前返回的问题并验证持久回执/重投/失败；保持常驻worker关闭。它不依赖补造事件历史，不能据此宣告完整调查质量或2C通过。

来源与操作输入见[清单](../handoff/2c-sources-input-manifest.json)。受控证据位于工作站`.local/aisoc21/evidence/2c-sources-20261020/`及21的`/opt/sting-aisoc-socai2/evidence/2c-sources-20261020/`；秘密仅在对应private目录，不随公开交付复制。
