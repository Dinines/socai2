# F4：已结束 pg-01 的局部 HTTP 读回

2026-11-15。**本次只读核对通过，F4 整项仍未通过。** 来源 [pg-01](pg-01/result.json) 本身为 failed：前四个场景完成，历史事件关联 Case 的手动检查产生 unknown Run。后续新批完整验证不能由本回执替代；旧失败不重派、不改写。

[http-partial-read-01.json](http-partial-read-01.json)记录59次无鉴权 GET，使用当前独立 HTTP 应用、真实隔离 `v12_upgrade_dev` 数据库和强制只读连接，经 ASGI 调用。19张直接相关表的本租户计数/摘要前后一致，已保存340份工件正文及摘要与核心冻结快照一致。核心使用17次模型回复替身、0真实模型；本次新增执行、模型调用和业务写入均为0。

| 核对内容 | 实际结果与边界 |
| --- | --- |
| 不同请求独立保存 | 排队案件有11个不同 operation_key 的任务，无合并目标；公开列表和详情保留各自身份。相同 key 的重复调用由核心原驱动实际核对，本轮只 GET，没有再发 POST |
| 无变化检查 | 9个后续检查各自 skipped/no_changes，attempts/results 为空、latest_run_id=null；没有另造调查记录 |
| 等待期间材料变化 | 旧轮 C1 冻结1条告警，后轮实际读取2条；旧工件保持。两轮同 Case 串行 |
| 其他案件可执行 | 核心容量 N=2；B 的完成时刻早于仍在运行的 A 结束时刻。HTTP核保存时刻，运行中并发观察来自核心原驱动 |
| 事件驱动更新 | 原三次扫描回执 submitted=0/0/1：晚到首个 A、新成员不会直接绕过 I；新 I 完成后，仅活跃整事件 Case 新增成功调查，C1引用对应 I，范围为2条 |
| 单告警关联 | 仍只有原首轮及1条固定范围，未因所属事件更新自动扩员或调查 |
| 历史事件 Case 手动检查 | 自动检查和手动检查为不同 task；自动 skipped/no_changes，手动 failed/execution_failed，原 Run unknown 且 ended_at=null。失败及原 C1可读，没有成功 Result，**不能判定手动检查通过** |

`full_F4_accepted=false` 固定记录本次边界。核心 pg-02/03 还遇隔离库存储不足；调查侧已定位为本机 OrbStack 隔离 PostgreSQL 的 tmpfs 容量，非21正式磁盘。本轮未调整挂载、重启或清理。新批完整手动/自动范围与重试顺序验证、真实模型、Kafka完整链、21 TCP及结束审计仍待。

检查代码：[test_socai2_case_trigger_partial_http_pg.py](../../../../services/api/tests/test_socai2_case_trigger_partial_http_pg.py)；入口：[validate_http_partial_readback.py](validate_http_partial_readback.py)。传显式受控 `--config`、已结束 `--source` 和全新 `--output`；拒绝覆盖旧回执。6份核心源摘要与原批一致。本次不改业务代码、公开 DTO 或鉴权行为，不发布、不推送。常驻服务与本次 ASGI 验证的区别见[本机实际状态](../http-local-runtime-review-20261115-01/README.md)。
