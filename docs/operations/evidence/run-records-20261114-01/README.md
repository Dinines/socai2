# 完整调查步骤与原件读取：本地验收

2026-11-14。对应[已确认HTTP合同8.7–8.10](../../../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#87-r3r4完整步骤与工件目录)和[接口指南](../../../integration/run-records-http.md)。负责人授权“讨论确认后可以实施”；双方合同确认在[协作回执](../http-impact-review-20261114-01/workflow-coordination.json)中。属于任务2.7局部，不代表整个change完成。

## 已实现及验证结果

- 三个独立GET：完整步骤分页、单步定位、完整原件目录；E12/E32只增加steps_url/artifacts_url，既有字段保持。
- 调查核心专用`app/socai2/run_records.py`只读数据库，通过HTTP用例端口连接；URL在外层生成。未改ORM、表、调度、执行器或内部HTTP。
- [pg-06.json](pg-06.json)：本机127.0.0.1:28412的隔离开发库v12_upgrade_dev，真实PG、新UUID合成数据，66次ASGI请求全部通过。没有正式TCP、21、模型或厂商服务验收。
- Case 1001步骤以每页100读11页，201原件读3页；另读无Case的告警failed Run和事件unknown Run，各2步骤/2原件。步骤ID顺序与SQL写入一致，原件相同时间下按ID稳定排序，不重不漏。
- 跨Run复用指向真实告警Run；无Run来源原件使用真实主体URL，正文均实际打开。step_id筛选去重本Run原件，不把其他Run原件加入本目录。缺正文元数据仍可发现。
- 过滤后的total、kind=tool、原件step_id、超旧上限单步、空Run，以及错误父Run/游标/枚举/参数、404/422/503均通过。
- 默认50/最大100来自配置文件，另核7/11配置变化、非法/缺失配置不回退。[direct-checks.json](direct-checks.json)记录配置、3项HTTP边界、2项可信接入及OpenAPI检查；旧摘要结构除两个目录链接外保持。
- 读取前后本批alert/incident/case/run/step/artifact完整行SHA256一致；6类记录总量和摘要保存在pg-06，不以HTTP200替代SQL读回。

[candidate-openapi.json](candidate-openapi.json)仅包含本步3操作及其依赖Schema，供审阅；不是已发布Swagger替换件。当前代码候选74操作，正式本地/21及静态Swagger仍71操作。源代码、配置与两端环境项见[发布清单片段](../../../../deploy/http-service/run-records-release-fragment.json)，本轮未打包、重启、部署、Git提交或推送。

## 保留的早期失败

| 回执 | 实际失败及处理 |
| --- | --- |
| [pg-01](pg-01.json) | 沙箱拒绝本机TCP连接，尚未创建数据；获准本机隔离库访问后新批次继续 |
| [pg-02](pg-02.json) | 合成终态步骤创建后再加引用，被既有不可修改约束拒绝；事务回滚。改为插入时保存全部真实引用，未改约束 |
| [pg-03](pg-03.json) | 合成baseline直接插入完成状态，被既有领取规则拒绝；事务回滚。改为pending→running→completed并保存真实成员 |
| [pg-04](pg-04.json) | 合成成员缺少source_operation_id必填值，事务回滚；补齐测试数据来源键 |
| [pg-05](pg-05.json) | 已通过完整分页/原件链接，后续测试客户端params={}覆盖URL内重复参数，实际请求丢掉该测试输入；修正测试客户端参数传递。该批合成记录保留，没有重派旧Run |
| [pg-06](pg-06.json) | 新UUID完整批次通过，含修正后的重复参数422验证；不改写之前失败 |

测试实现为[专用PG用例](../../../../services/api/tests/test_socai2_run_records_pg.py)，复用既有本机隔离PG runner。查询在REPEATABLE READ/READ ONLY事务中运行；跨请求分页并非冻结整个持续增长的Run，observed_at为各次观察时点。调查结果正文质量不在本步验收范围，原NOT_PASSED结论保持。

剩余：R1统一Run目录/统计、task/attempt读取及主线调度按阶段2继续；统一发布后的实际配置/版本和TCP读回尚未执行。任务2.7及change未勾完成，也未开展整个change的结束审计。
