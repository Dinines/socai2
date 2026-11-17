# S01 两案首轮结果 HTTP 读回

2026-11-15。21候选18424、80操作、内部可信无鉴权。复用HTTP已创建的两案，由调查唯一执行器完成首轮、测试唯一抓取保存快照后，本模块完成 **58次实际TCP GET：14次详情/目录、44份必要原件正文**。34步骤、96份工件目录、两案任务/Run/Result及当前判断与同源快照一致。没有再次创建案件、调用模型、直接查询数据库、重投Kafka或重读A/I批次。

| 案件 | Case | 实际 Run | 实际 Result | 冻结成员 |
| --- | --- | --- | --- | --- |
| 整事件 | 58194401-03ca-5383-83b4-ac82886a5acd | d1b17106-0ee7-4265-ac84-beb9ebf048eb | 9cf1a538-ddf2-4df1-aa37-021cbf95d5a2 | A01/A02/A03，3条 |
| A01固定范围 | bad63e2a-9f03-547b-8a0c-243347807c41 | 3327b87f-f4d8-451e-b91d-39618622ead9 | 2e87d00f-5275-499e-bf03-f851302d5cb3 | 仅A01，1条 |

两个原initial任务均completed，各1次attempt/Run和1个Result；两Result均为validation accepted、conclusion uncertain、delivery partial。任务、Run、结果和当前assessment关联正确，历史只含各自首轮，previous_run_url/comparison_result_url为空，comparison_context为initial。范围从冻结输入和实际结果成员核对，不用当前事件成员替代。

单A01案C1确有I01来源，但linked_from_case=false；I原选入/覆盖仍是3，本案case_selected_alert_ids/case_covered_alert_ids仅含A01，保留diagnosis_scope_extends_beyond_case。整事件案交集为3。两案C2知识实际返回4/2条，原始回执和C3请求可读取；C4分别实际查询network/process和process/auth，其请求、返回及C6输入与保存一致。模型请求、处理回复及独立原答均逐字核对，未以结构化结果代替原答。

## 证据与后端读取入口

- [结果汇总](result.json)、[读取计划及来源摘要](plan.json)、[14次详情/目录](get-01.json)、[44份原件正文](content-01.json)、[只读脚本](read_cases.py)。
- 测试唯一来源：[实际身份映射](../test-streaming-case-initial-20261115-01/actual-case-run-map-01.json)、[保存快照](../test-streaming-case-initial-20261115-01/case-pg-01.json)、[277项直接核对](../test-streaming-case-initial-20261115-01/case-validation-01.json)。快照SHA为`a30c69fadd2241d96e393bd6be48591dca37231157e808660c0c09e7d1b5421e`。
- [测试统一验收](../test-streaming-case-initial-20261115-01/acceptance-01.json)已纳入本次58GET，结论为flow_passed_quality_deferred，仅适用于S01两案首轮。
- 原创建输入及即时受理：[2次POST/5次GET](../streaming-case-http-20261115-01/README.md)。这些操作已执行，查询现状使用GET，不换operation_key重新建案。
- 当前可只读查看[整事件结果](http://192.168.1.21:18424/api/v1/socai2/cases/58194401-03ca-5383-83b4-ac82886a5acd/results/9cf1a538-ddf2-4df1-aa37-021cbf95d5a2)和[A01结果](http://192.168.1.21:18424/api/v1/socai2/cases/bad63e2a-9f03-547b-8a0c-243347807c41/results/2e87d00f-5275-499e-bf03-f851302d5cb3)。完整步骤/工件沿Run返回的steps_url/artifacts_url及content_url读取，不需要Token。

## 实际限制与保留的失败

partial的实际原因见[测试记录](../test-streaming-case-initial-20261115-01/partial-delivery-01.json)：背景源因预算跳过或尚未接入、输入省略、成员待核及每案3个未解决问题；整事件案另有未定领域和未解冲突。未查不写成查空，待核不写成已解决。

[质量记录](../test-streaming-case-initial-20261115-01/quality-findings-01.json)为NOT_PASSED，4个真实C3/C6回复共10项引用问题保留，正文全面评估为not_checked。本次Case原答为正常多段文本，不能把上游A/I单字质量问题套到Case正文。accepted仅表示结构接收，当前不据此判模型质量通过；不重采样、不改原答。

58次GET全部200后，验证脚本误用A/I trace的steps_total检查Case Run，发生[KeyError](verification-failure-01.json)。[原脚本](read_cases-before-verifier-fix.py)和原回执保持；改为按Case实际分页total及全部ID核对，使用`--verify-saved`离线复验通过，未重复HTTP。该错误不属于业务接口缺陷。

S01首轮的HTTP受理→执行结果读取已闭合；S04后续变化、测试代理/4177及整个change独立结束审计另验。HTTP源码/合同/镜像/运行配置未修改，没有正式发布或Git推送。
