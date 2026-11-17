# F4：独立新批完整 HTTP 读回

2026-11-15。**F4的本机直接验证和HTTP读回已通过；F5及整个change验收仍未完成，未部署。** 主来源是测试模块亲自执行的 [test-pg-01](test-pg-01/result.json)，重试来源是独立 [test-retry-guard-01](test-retry-guard-01.json)。[测试执行及源码摘要](../test-f4-independent-20261115-01/README.md)保留离线31项、真实PG/Redis执行命令和配置指纹。

两批使用本机磁盘绑定的新隔离库 `127.0.0.1:28413/v12_upgrade_dev`。主批6个Case、23个任务、13次attempt/Run、9份Case Result；实际A/I/Case执行器使用22次模型回复替身，0真实模型。重试批另有2个Case、3个任务、3次attempt/Run，使用受控执行器与时钟，不是Case模型整链。新库由旧库完整复制后以新租户运行新批；不是重执行旧记录。旧28412容器、旧pg-01/02/03失败及unknown保留。

HTTP使用当前独立应用、真实核心读取器、显式可信上下文与强制只读连接，经ASGI访问；新增模型、执行及写入均为0。不是常驻18024、21 TCP、Kafka或真实模型验收。

| 检查 | 同源公开接口结果 |
| --- | --- |
| 不同请求独立及无变化 | 相同案件11个不同key任务无归并目标；9个后续检查分别skipped/no_changes，无attempt、Run及Result。核心同key回放只保留原任务，本轮只GET，不另发POST |
| 等待和冻结范围 | A首轮冻结1条、后轮2条，原输入保持；同案串行。核心容量N=2时B在A结束前完成，HTTP核对应保存时刻 |
| 自动更新范围 | 晚到首个A和事件新成员未绕过I触发Case；新I业务变化后，活跃整事件Case更新为2条，单告警Case仍只有1条和原首轮 |
| 历史案件手动检查 | 自动检查skipped/no_changes，独立手动检查completed且有Result。C1使用新的I，但本案告警范围仍为原1条，未把事件外部成员变成本案覆盖 |
| 容量续建 | 测试容量2，第三条成员在新I完成后进入新Case；新案有自己的initial任务、Run和Result，只含新增1条。原案previous/receiving关系、事件接收目标、优先展示的续建关联一致 |
| 上游来源 | 全部23个A/I/Case任务和13个Run的公开来源可读；Case冻结引用的I与对应诊断和实际选入范围一致，最新事件3条不改写旧Case冻结输入 |
| 重试等待与独立请求 | 原task冻结等待60秒后只重试一次，最终failed/retry_exhausted，两次attempt及Run均failed；同主体新请求独立保留，最终skipped/automatic_attempts_stopped且无Run。另一主体completed；三个受控输入工件可读，无模型Result如实为空 |

主批 [http-full-read-02.json](http-full-read-02.json) **78次无鉴权GET通过**，19张直接相关表的本租户计数/摘要前后一致，408份保存工件正文及摘要与原快照一致。重试批 [http-retry-guard-read-01.json](http-retry-guard-read-01.json) **11次GET通过**，10张直接相关表摘要一致。等待期间的accepted/retry_scheduled及60秒门槛来自核心原等待快照、受控时钟与最终保存时间；不冒称HTTP实时等了60秒或观察了全部中间态。

首次主批读取 [http-full-read-01.json](http-full-read-01.json) 的第70次关联列表GET返回503：本次HTTP测试入口漏加载既有 `allocation_policy_file`，前69次GET已成功。入口补显式 `SOCAI2_CASE_ALLOCATION_CONFIG_FILE` 后，沿同一已结束批次重新读取通过；没有修改业务代码或重派任务。失败回执保留；旧批 [59次局部读回](http-partial-readback.md) 的 `full_F4_accepted=false` 与旧unknown也不改写。

入口：[主批读取](validate_http_readback.py)、[重试读取](validate_http_retry_guard_readback.py)；直接检查代码：[主批](../../../../services/api/tests/test_socai2_case_trigger_http_pg.py)、[重试批](../../../../services/api/tests/test_socai2_case_retry_guard_http_pg.py)。均使用显式私密profile和新的输出路径，拒绝覆盖旧回执。读取时6份核心源摘要与主批一致。

公开接口保持80操作、无鉴权，OpenAPI与原第7步候选一致，本项不新增字段。任务语义见[任务指南](../../../integration/analysis-tasks-http.md#不同检查请求和无变化结果)，F5完成后再统一核发布包。中间验证在本机，最终Kafka/真实模型/TCP测试在21目标版本执行，完整change还需独立结束审计；本回执不代表已发布或审计整体通过。
