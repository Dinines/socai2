# F1：事件诊断范围传入Case的HTTP读回

2026-11-15。**F1同源HTTP读回通过，可与核心直接证据一起收口本项；第7步整体审计仍未通过，F2–F5继续逐项修复。** 无业务代码修改、DDL、发布或任务重派。

来源为核心已结束[pg-04](pg-04/result.json)及其[保存快照](pg-04/snapshot.json)。只读连接真实隔离`v12_upgrade_dev`，数据库连接强制`default_transaction_read_only=on`；独立HTTP应用使用真实核心读取器、显式可信业务上下文和该批目标策略配置。HTTP为ASGI传输，不能当作21 TCP验证。核心原批4次模型替身、0真实模型，本次0模型/0执行/0写入。

最终[http-read-03.json](http-read-03.json)共22次GET，全程无Authorization。读取前后仅核本批直接涉及的19张表，计数及摘要保持一致；6份核心源码/Schema摘要与[执行时版本](pg-04/source-hashes.json)相同。

| 核对项 | 实际结果 |
| --- | --- |
| 真实对象和任务 | Case保留3条成员；当前事件已有4条。两个I任务和一个Case首轮任务均保持原completed身份，共3Run；没有重复受理/执行 |
| I的旧轮与新轮 | 旧I捕获3条、选入1条、遗漏2条；覆盖1条且待核（analyzed=0、unresolved=1），不等于未分析。新I捕获4条，选入后来新增的一条；目录当前指针与历史来源分别可读 |
| Case C1冻结来源 | `incidents.<id>.diagnosis_scope`保留旧I的Run、输入工件、source_fingerprint、选入/覆盖及Case交集。Case成员仍3，不能用当前事件4条或新I覆盖旧范围 |
| C3及C6引用 | 两份实际保存model_request中的事件结论引用均只关联旧I实际覆盖的1条；original_scope保留该来源完整选入范围，来源仍为prior_analysis及原C1工件 |
| Case最终结果与工件 | E12/E14、Case输入manifest/C1、I输入及C3/C6原件沿现有真实链接读回，与核心保存正文/sha256一致；最终Result与核心同对象读回一致 |
| 无副作用 | 22次均GET；19表本租户行数及摘要前后一致，连接强制只读。没有Redis消费、模型调用、POST或数据修补 |

保留[http-read-01.json](http-read-01.json)和[http-read-02.json](http-read-02.json)：各11次GET后测试断言报KeyError，原因是测试把I工件的`metadata`误按Case工件的`artifact`读取，随后一次修正仍误取顶层id。两次已发GET均200；修正测试按两种既有合同分别取元数据，并按IncidentInputSelection既有日期类型比较，最终通过。未改API、原件或旧失败。

测试代码：[F1 HTTP直接检查](../../../../services/api/tests/test_socai2_incident_case_scope_http_pg.py)；入口：[validate_http_readback.py](validate_http_readback.py)。使用显式受控配置`--config`、已结束来源`--source`和新的`--output`路径运行；输出已存在时拒绝覆盖。测试不创建新业务样本。发布仍依赖同版核心F1模块，见[HTTP发布片段](../../../../deploy/http-service/case-update-release-fragment.json)；既有80操作/DTO保持，待本change全部修复收口后统一冻结最终发布包，不改写原7C快照。

本次不重新验证核心缺范围/无交集/跨Case/部分覆盖的8项离线边界，不重跑其已结束任务；这些与受影响64项核心检查、已知未通过历史展示测试分别保留。Kafka源头、真实模型、21 TCP及最终独立审计仍待整阶段测试，不以本批PG/替身/ASGI读回替代。
