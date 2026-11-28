# 4c湖告警持久交付

独立worker读取已落湖材料、登记交付项，再调用4b接收器。与Kafka全量落湖消费者分开：Kafka已提交只证明湖保存，不代表告警已接收。本目录是候选交付，正式服务未启用。

1. 目标PG先有130，再运行`install_reader.py lake-alert-deliveries --profile <显式配置>`应用131。内部新增`lake_alert_deliveries`、`lake_alert_delivery_attempts`，V1及公开告警字段保持；新装current入口在配置analysis_ingress时包含同一130/131，reader verify按迁移账本识别。既有库不得重新初始化。
2. 复制[delivery示例](delivery.example.json)并显式选择selection、receive和受控connection文件；路径相对delivery文件目录。[连接示例](connections.example.json)仅为占位，实际凭据保存在受控、忽略提交的文件。PG与receive库、CH与selection库必须一致。配置普通现有入口角色，按增量脚本提供功能所需读写，不使用其他项目的角色或库。
3. `PYTHONPATH=services/fusion python -m app.workers.lake_alert_delivery --profile <路径> --stage-only`仅做持久登记；`--once`完成一轮有界扫描和交付；省略两者则按显式间隔轮询。每轮交付上限不删除剩余项，后续从队头继续。enabled=false拒绝启动，不静默选择其他配置。
4. [候选compose](compose.candidate.yml)要求明确候选镜像、配置目录及既有网络；配置目录挂载为/config，入口读取delivery.json，其他文件按其相对路径选择。仅在统一交付时使用，不因本目录存在自动启动。发生blocked/unknown时进程退出，不自动重启越过问题；日志默认WARNING/ERROR，状态输出不含记录或数量。

全量有界扫描按稳定湖版本去重，然后一次事务登记全部去向。相同delivery_key不新增项，规则/接收配置变更不能静默覆盖已有绑定；应先处理当前队列并明确后续迁移方案。这里不使用移动事件时间水位，迟到或旧事件仍能被发现；范围超过selection.read_limits则显式停止，需要按实际规模调整或另设计分段发现，不能把截断当扫描完成。

待交付项按固定顺序处理，同来源用PG会话锁避免并行越序。开始接收前保存receiving尝试；4b事务提交并读回证明后，交付确认事务还核130回执、版本和材料关联，再保存delivered。只有确认事务提交成功才计交付完成。lake_only/review是选择去向，不冒称告警交付成功。

failed/held/unknown阻断后项。已知失败在下一次显式运行重试同项；receiving遗留或unknown先只读查询4b回执，证明存在则新记recovered，不重跑Fusion。没有可证明回执时保持unknown，不自动重执行副作用；需先查明旧执行及原文状态，再明确同项处理。旧失败/unknown尝试不可修改为成功，恢复另记尝试。确认事务结果未知时，以数据库已保存的交付状态为准，不能从内存计数推进。

正文继续按4b完整保存和HTTP读回，交付表只保存精确湖引用及判定。原文过期、查不到或查结果未知都不能跳过待交付项；本轮不引入另一份正文存储或自动清理任务。初诊只登记accepted，不运行模型，不创建Case。

本轮直接验证及边界见[4c证据](../../../docs/operations/evidence/lake-alert-delivery-4c-20261119-01/README.md)。
## 独立扫描执行限额

`delivery.json` 可显式提供顶层 `read_limits`，完整包含 `max_records`、`max_result_bytes`、`query_timeout_seconds`、`connect_timeout_seconds`、`send_receive_timeout_seconds`，各项均为正整数。它控制本次原生扫描及 ClickHouse 客户端，仍按完整来源范围检查超限和读取完整性。

旧配置未提供该对象时，完整沿用 `selection.json` 中的 `read_limits`。已有投递账本使用冻结的 selection/receive 绑定；调整运行容量时使用 delivery 的可选对象，保持原 selection/receive 文件内容，不改写旧账本摘要。模型预算不受此配置影响。
