# 湖3d消费配置

这是统一发布候选配置，不是正式Topic已经接通的回执。复用[3c来源配置](../lake-ingress-3c/README.md)和[3b存储/迁移](../lake-storage-3b/README.md)，新增`consumer.json`。例子只有合成目标；实际配置必须明确broker、独立group及ingress中的Topic/tenant/source/database，凭据和CA留受控文件。

选用`AISOC_LAKE_CONSUMER_PROFILE_FILE`后默认示例`enabled=true`；同时要求湖写入开启、来源profile有效、005账本及命名列存在。group/Topic不能与旧信封、告警或UEBA混用。Kafka TLS、CA及认证沿用同一运行env文件中的`KAFKA_SECURITY_PROTOCOL`等既有配置；本文件的broker不回落到其他环境。

首次无已提交位点时，`initial_offset=earliest`明确从仍保留的最早记录读取；`require_committed`要求已存在位点。已有位点越界不自动重置。每次getmany最多batch_size条，空闲最多等待max_wait_ms；不足批量也直接保存。批量限制是消息数，不把offset跨度当作条数。消息大小需与broker实际配置匹配。

只在实际INSERT及该分区整批回执确认后，提交最后处理offset+1。遇到保存/回执/提交失败，停止本接入、ready变false，保留所有已拉取未提交范围；此前已完成分区保留提交，后续分区不再推进。没有DLQ跳过或自动补写。INSERT异常按稳定身份和完整材料摘要读回，结果为present/not_observed/unknown；即使present也不自动将原未知提交为成功。

取消时等待有界native调用结束、核对未知保存，再关闭连接；关闭不提交未确认数据。分区撤销也停止接入，不跨代提交。运维恢复前查看`lake_consumer.stopped`状态和原group已提交位点，先核未知范围，再明确重启；重读沿稳定身份，实际重写按确认口径刷新入湖400天。不要重置group以绕开问题。

发布前必须同版核对005/TTL、API清理profile、Fusion来源/消费profile及实际连接。`CLICKHOUSE_*_TIMEOUT_SECONDS`在env文件显式选择，消费max_poll_interval_ms要覆盖批内串行写入、未知读回和提交所需时间。本步不启用promotion/native detection/模型；旧信封缓冲路径仍是原行为。
