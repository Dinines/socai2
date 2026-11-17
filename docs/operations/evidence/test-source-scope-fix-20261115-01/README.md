# 来源范围修复的直接检查

2026-11-15，承接[S01真实来源范围失败](../test-streaming-s01-ingress-20261115-01/README.md)及[同一change窄修复](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-candidate-design-20261115.md#s01来源范围阻断与窄修复)。调查方修改consumer和Fusion内部HTTP入口；测试方只修改既有`test_consumer_dlq.py`、`test_process_delivery.py`，未改app源码、接口字段或业务数据。

新增6个参数化直接用例：Kafka RawAlert入口和HTTP `/process`入口各验证1条、多条和空的显式`source_event_ids`。测试走真实入口处理代码，核实际保存snapshot、发布fused、HTTP返回（对应HTTP入口）以及当前projection的source_scope/source_refs；空列表须保持unknown/complete=null，不能添加告警自身ID。既有normalized raw_event到湖/保存的同一event_id检查一并复用。

| 对照 | 结果与范围 |
| --- | --- |
| 冻结r2包 | [包来源及摘要](before-sources.json)，原归档SHA256核对后提取到临时只读来源目录，不覆盖工作树。显式预载并记录两个旧模块路径；[red-02](red-02.json)/[完整输出](red-02.txt)：新增6项全部失败，normalized raw_event既有1项通过 |
| 修复后工作树 | [green-01](green-01.json)/[完整输出](green-01.txt)：两个受影响测试文件共21项通过；包含新增6项。记录实际模块路径及4份源码摘要，测试期间摘要未变 |
| 静态校验 | 两测试文件Ruff通过，保留既有未启用SLF001的noqa；仅该既有RUF100告警不计入本次检查，未批量改动旧测试。OpenSpec strict通过 |

首次旧版验证只设置PYTHONPATH，没有锁定已加载模块，`red-01`的7通过**不作为r2对照证据**；原文件保留，改用明确预载和实际模块路径的red-02。模型、PG、Redis和Kafka边界均为明确内存/异步测试依赖；本检查没有真实模型/网络/数据库调用。

结论仅为当前程序边界修复通过。S01旧批失败不核销、不回写、不重派；等新候选包及唯一Fusion实际加载回执后，以不同来源身份和归并IP的有界新批完成Kafka/CH/PG/HTTP复验。
