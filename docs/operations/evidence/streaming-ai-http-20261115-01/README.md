# S01真实A/I：任务、分析结果和原答HTTP读回

2026-11-15。**62次实际TCP GET通过，无鉴权；模型正文质量仍为NOT_PASSED。** 本步证明已执行分析能够按真实身份保存并由接口完整读取，不把completed、结构覆盖3/3或HTTP 200当作有效业务解释或正确安全结论。

来源为测试正式交付的[实际分析映射](../test-streaming-ai-20261115-01/actual-analysis-map-01.json)、[保存快照](../test-streaming-ai-20261115-01/analysis-pg-01.json)及[独立保存断言](../test-streaming-ai-20261115-01/analysis-validation-01.json)。快照SHA-256：`d959c407b2169c633ec2efc22d7e02434853985c4a3a9785661246b3cebf0f96`。沿用入站批`s01-ingress-20261115-02`，HTTP没有直接连接数据库、重投Kafka或重新生成分析。

目标为`http://192.168.1.21:18424/api/v1/socai2`，仍为r2/80操作同一合同；[同批lifecycle只读配置](../streaming-http-lifecycle-20261115-01/README.md)已加载。按[最小HTTP计划](../../../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#已有ai任务执行后的http联验2026-11-15)读取，不重复此前35次入站验证。

| 实际主体 | Run | 已保存结果 |
| --- | --- | --- |
| A01 | `d04f0165-8dbf-533c-bb23-6ea999957689` | 分诊`d7161272-2b1c-5ed4-98cb-7fa9ea9f0e35` |
| A02 | `563de456-0540-523f-95b2-4d6f33d4122a` | 分诊`f6b366aa-3dab-5a60-97f9-bc4a5bd0f055` |
| A03 | `439806fe-b525-5601-bd28-c23a28a38619` | 分诊`53827ec1-8016-5236-9164-633c1bfe30b2` |
| I01 | `b5410c29-8134-544d-94e0-f8d59ee82958` | 诊断`d45f13bd-ce73-5dd0-8907-5dd215455ba1` |

直接核对结果：

- 原4条initial/ingress任务均completed、各1次attempt；task→Run→result和返回链接与同批保存一致，当前指针及历史目录没有串案或替换原轮。
- 17个步骤、45份Run工件元数据全部可读；按真实目录读取29份必要正文：4份冻结输入、4份policy、4组模型请求/校验响应/原始回复、9份真实查询回执。正文及元数据与快照一致，来源/可用性保持。告警解释正文也通过Run响应与保存值核对。
- I冻结选入3条、遗漏0条，采用3个当前A及其查询回执；接口input_selection与原输入一致，analysis_coverage覆盖同3条，未扩大到其他成员。结构覆盖不等于模型正文质量通过。
- 新I任务列表的last_normal_completed_at、next_check_at与保存相同；auto_expires_at实际按同批86400秒窗口返回，eligible/ineligible_reason相符。配置差异已解决并取得业务读回。
- 旧失败批4条任务现在实际返回skipped/closed_before_start，attempts/results为空、latest_run_id为空。没有再次关闭或重写它们，原错误来源及失败记录保留。

**质量事实：** [测试质量记录](../test-streaming-ai-20261115-01/quality-findings-01.json)为NOT_PASSED。3个A的rationale只有“告”且重复引用，I的summary/成员等正文为“A”；HTTP结果和真实provider原答一致。benign/0.95及覆盖complete不构成正确性或安全证明。按已确认范围保留原答和未通过结论，不改写、不重采样。实际生成次数及用量由[测试usage](../test-streaming-ai-20261115-01/usage-01.json)记录：4次真实生成、14022 token，费用未知；本HTTP步骤新增模型调用为0。

请求与断言：

- [执行脚本](read_analysis.py)、[来源摘要/主体请求计划](plan.json)。
- [33次任务/结果/目录GET](get-01.json)、[29次原件正文GET](content-01.json)、[通过结果](result.json)。目录本批各一页可读完整，未强造额外分页请求。

本步骤0业务写入、0直接数据库查询、0新增模型/工具调用；没有创建Case、更新部署或推送Git。OpenSpec严格校验通过，读取步骤未发现需修复的接口程序问题。A/I保存与读回可收口，Case受理/首轮、持续更新及完整change独立结束审计仍待；模型质量继续单独记录未通过。
