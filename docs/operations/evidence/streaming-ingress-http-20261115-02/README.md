# S01-r3新批：非空HTTP读取

2026-11-15。**入站主体、来源、关系和待执行任务的35次实际TCP GET通过，无鉴权。** 本步骤不验证模型执行、Case建案或完整调查链，不据此判定整个change结束审计通过。

唯一来源为测试模块已通过的真实Kafka批次`s01-ingress-20261115-02`。采用[实际PG身份映射](../test-streaming-s01-ingress-20261115-02/readback/identity-map.json)，并核其声明的PG快照摘要；直接引用[上下文断言](../test-streaming-s01-ingress-20261115-02/readback/context-readback.json)、[告警断言](../test-streaming-s01-ingress-20261115-02/readback/alerts-readback.json)和[保存原件](../test-streaming-s01-ingress-20261115-02/readback/alerts-pg.json)。HTTP没有另外连接或查询数据库，没有使用离线预测身份。

目标为已运行的`http://192.168.1.21:18424/api/v1/socai2`，HTTP仍为r2/80操作；上游Fusion为修复来源入口后的r3。不重新部署HTTP或Swagger，不改变请求/返回合同。

| 核对对象 | 保存与接口实际结果 |
| --- | --- |
| 3条告警 | `09e85609-d734-5b2a-81ba-d086fc81b619`、`69eff99f-252e-5720-a6d4-ca556f29a557`、`f4542be8-4097-59af-8a68-50c52a10f50b`；详情字段与保存快照一致，处理状态new |
| 1个新事件 | `263a1c58-e9c6-4ba4-9204-3b0568970551`；A→I关联与I→3成员一致，没有归入旧失败事件 |
| 来源范围与分页 | 每条告警恰好1条真实source_event_id；事件成员及来源分别按limit=2读2页，总数3、末页next_offset=null，无重复遗漏 |
| 材料及原件 | 3份材料的raw_text、raw_json、ocsf_json、enrichment与保存值相同；3份来源原件content_json/content_text完整一致，目录content_url指向相同原件 |
| 4条分析任务 | initial、source=ingress、accepted；列表与详情完全一致，status_url可读；started_at/latest_run_id为空，attempts/results为空 |
| 分析目录 | 3A与1I均无当前分析指针/正文、历史entries为空，没有将受理显示成完成 |

本次0业务写入、0数据库查询、0模型/调度启动；没有再PATCH旧失败批或创建Case。旧批关闭回执及错误来源继续保留在[独立证据](../streaming-failed-batch-close-http-20261115-01/README.md)，不计入本批通过范围。数据库和上下文的实际增量、旧批保存断言由测试模块负责，本回执只验证公开HTTP读出的数据。

证据：

- [读取脚本](read_ingress.py)、[目标/来源摘要与请求计划](plan.json)。
- [33次主读取](get-01.json)、[2次分页续读](get-02.json)、[最终断言结果](result.json)。
- [首次离线断言失败](validation-01.json)及[原脚本](read_ingress_initial.py)：错误地要求公开source_ref包含私有tenant_id。35次响应本身均200，其余字段与保存快照相同；已按既有`public(row)`合同修正断言，用`--verify-saved`检查保存响应通过，没有重发HTTP或修改业务代码。

执行前OpenSpec严格校验通过。下一步由调查模块推进真实A/I调度/保存，再由HTTP按同批身份读回分析结果；Case建案、完整链及独立结束审计仍待，未作正式发布或Git推送。
