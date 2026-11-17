# S01 Case 首轮：两案真实执行与保存验收

**[本子步流程验收通过，质量问题后置](acceptance-01.json)。** 两份知识正常导入/真实索引检索、两案HTTP创建、2个Case首轮Run及[58次HTTP结果读取](../streaming-case-result-http-20261115-01/result.json)均已完成。4次真实生成、4次C4补查；两案均completed / accepted / uncertain / partial，[质量问题](quality-findings-01.json)保留，不计质量通过。沿用`s01-ingress-20261115-02`，[既有A/I](../test-streaming-ai-20261115-01/acceptance-01.json)不重跑，原件及NOT_PASSED保持。测试管理本目录，调查管理唯一profile/调度，HTTP管理建案及结果读取；本回执不代表S04、W2/W3/W4或完整change通过。

## 本步边界和顺序

1. 核当前来源及两案预期，冻结[expected.json](expected.json)、[source-plan.json](source-plan.json)、[原件/代码摘要](preparation-freeze-01.json)。不从旧生产profile、历史Case或示例填当前参数。
2. 调查提供候选库/湖/知识profile和实际就绪回执后，测试唯一导入[两份原文](knowledge-documents.json)，保存实际块ID、原文/元数据/hash，经真实embedding与专用Qdrant索引，再用当前知识adapter检索。完成来源验收才交HTTP；未通过只修本步阻断，不触发Case。
3. HTTP沿[已冻结请求](../streaming-case-http-20261115-01/requests.json)先创建整事件案并读回，再创建单A01对照并读回。此时唯一调度保持停，201真实受理须先有Case/关系/initial任务，尚无Run；同key与管理编辑按HTTP已定最小范围复用这两案，不另造Case。
4. 两案身份/范围读回通过后，调查启动唯一调度，真实执行首轮；测试不直接调用执行器。全部终态及停止观察后，测试做一次正式Case PG/工件快照并离线验收，再交HTTP核同Run输出。若出现程序阻断，保留失败并定向修正，禁止改原答追认。

本步不重投S01、发送S04、重跑A/I，不新增H/响应操作或后置模块。S04更新/比较及W2/W3/W4另按下一子步推进。

## 两案冻结预期

| 内容 | 整事件案 | 单A01对照 |
| --- | --- | --- |
| 创建选择 | incident_ids仅本批I01 | alert_ids仅本批A01，incident_ids为空 |
| 成员/任务 | A01/A02/A03，共3；当前容量100，无续建，1 initial | 仅A01，共1；独立案，1 initial |
| 后续接收关系 | I01 active_case_id指向本案 | 不抢I接收目标，不自动扩员 |
| C1事件诊断 | linked_from_case=true；原selected/covered3，本案交集3 | 可沿所属事件读取I，linked_from_case=false；原selected/covered仍3，本案交集仅A01，记录diagnosis_scope_extends_beyond_case |
| 默认时间窗 | 2026-11-15 09:14:18Z至11:24:18Z | 09:14:18Z至11:14:18Z |
| 初轮比较 | 无上一完整Case综合，不能用A/I替代 | 同左；不能拿另一独立案结果作上一轮 |

Case/Task/Run ID只能来自实际201/保存，`expected.json`不预造身份。C1固定材料及分诊/诊断版本，完整旧A/I正文和NOT_PASSED状态保持；程序可用性与正文质量分别记录。共享事件信息不能增加单告警案成员，也不能将原跨成员结论改写为A01独有证据。

## 知识、背景和日志供给

- 正常来源入口为`knowledge_base.ingest(IngestRequest, db, CurrentUser)`及`knowledge_source.index`，直接复用业务分块/保存及真实向量实现；明确为内部来源管理函数调用，不冒称18424 HTTP验收，不混入调查Swagger，不恢复旧服务。每次写入前留独占intent，部分成功/unknown不重派；保存实际ID后读回。
- 原`technical_explanation`正文保持，使用当前目的标签；原`evidence_guidance`只映射目的名到`investigation_guidance`，不改正文。技术解释仅适用logon；取证指导按logon/process_start/network_flow_observed适用。标签取当前profile的action facet，不能为命中降低阈值或绕过条件。
- `historical_reference`只是未绑定历史来源的文字，保留原件而不索引；不伪造历史告警、分诊或人工核实。历史目的启用并验证真实查空，其正命中仍未覆盖。关闭分诊后历史自动同步，既有差质量A/I不导入知识。
- 目标profile由调查方从当前完整模板生成并实际核验：qwen3-embedding:0.6b/1024，独立集合`socai2_streaming_20261115_knowledge`，既有阈值/候选上限/facets保持。凭据只引用21受控文件；普通writer的KB SELECT/INSERT与普通reader读回、Qdrant集合和embedding调用分别留证据。
- 检索selector来自本批真实已保存材料及两案预计范围，经当前`knowledge_config.selectors`生成；不复用旧案例查询，不注入expected。核实际目的、条件匹配/排除、PG原文hash、向量payload一致。相似度低导致查空要照实记录，不等同失败，也不宣称非空传递已验；两类非空覆盖须有实际命中。
- 复用已验证的1条资产和9份A查询回执，不重导、不重复A/I查库。账号用途仍只是声明，授权未知/维护记录缺失，未接UEBA/graph；不为使来源看似完整而造数据。
- 复用12条已入湖日志。根侧Case普通来源连接及真实LakeGateway预检只证明依赖就绪，不算Case C4已查询。C4依据实际选中binding的成员时间重算窗，按tenant/src_hostname/class_uid和`[start,end)`核命中；不能假定每个绑定使用全案窗口。对整案/单A01当前窗，三类预期分别auth E01/E02/E12、process E03/E04/E08、network E05/E06/E07；E06/E12不因目的/账号不同被排除，E09/E10/E11在本窗外，E13尚未投放。

## 首轮保存验收出口

核两案task→全部实际attempt→Run→policy/C1→阶段/工具/模型原答/校验→Result/graph/report→采用及HTTP读回。C2预算内实际查询/跳过要与来源选择表一致，已有A回执可被配对复用；知识命中、进入模型、被引用、合理使用是四个不同结论。

C3、Deep、C6按真实路径记录生成及有界补答，C1/C2/C4/C5等程序步骤不虚构模型调用。C4/Deep未被模型选择时保留未查询/未走状态，不伪造成功步骤；未覆盖路径仍由原直接证据或后续必要场景承担。结果归属和引用范围不得超过真实成员/所选工具；0/false/有效空列表及原材料不丢失，未查/查空/失败/unknown保持区别。

初轮无有效上一综合时，比较按当前合同标不可比较；建议不等于执行。程序通过、交付完整性、待复核、采用状态与模型质量独立报告。既有单字正文问题记录后置，不以反复生成求好答案；如果格式、范围、预算或保存错误阻断流程，就报告本步未通过。最后只交一次真实map/快照给HTTP，保留所有失败及原答，尚不宣布完整change完成。

## 来源准备实况

- [K1导入](knowledge-ingest_K1-01.json)和[K2导入](knowledge-ingest_K2-01.json)均已真实保存，后续不重导。
- [读回01](knowledge-readback-01.json)为测试脚本的SQLAlchemy/asyncpg连接参数适配失败；已按当前dispatcher明确TLS参数修正。[读回02](knowledge-readback-02.json)已连接候选库，实际报`permission denied for table aisoc_kb_documents`，调查侧已[补齐普通reader必要SELECT](../streaming-case-20261115-01/knowledge-reader-access-01.json)，[读回03](knowledge-readback-03.json)通过；未替换为高权限账号。两次失败回执和原脚本保留。
- [唯一索引](knowledge-index-01.json)与[一次来源检索](knowledge-retrieve-01.json)通过：真实embedding请求2次，输入分别为2文档和9个selector；向量搜索9次。技术解释仅A01命中，取证指导3成员均命中，共4行/2文档；技术解释对A02/A03因适用条件冲突排除，历史目的3次真实查空。未降低当前0.45阈值，PG原文与索引payload、检索记录hash一致。
- [离线核验脚本](verify_knowledge.py)按这些实际回执生成来源验收；原脚本初次核验的单A01键名已更正为冻结预期中的`single_A01_case`，未重复任何远端调用。费用未知保留null，embedding不计为调查生成调用。来源探针不证明Case已使用知识或模型合理使用；Case阶段继续分别核。

## 两案受理后保存核对准备

[HTTP实际身份](../streaming-case-http-20261115-01/actual-case-map-01.json)与冻结3/1成员、1/0显式事件预期一致；单A01案未抢I01接收目标。[捕获配置](capture-config.json)只取这两案及原3A/1I，运行参数来自最新Case `analysis.json`，来源批次与Case执行批次分别记录。[准备回执](capture-preparation-01.json)不计数据库读取；[只读脚本](case-capture.py)复用已验repeatable-read入口并加入Case关系、assessment和result成员。实际执行已按这一顺序完成，唯一快照及核验见下节。

## 首轮实际保存结果

根侧[全部终态正常停止](../streaming-case-20261115-01/stop-01.json)后，以当前候选普通reader/TLS在一次只读repeatable-read事务中取得[正式PG快照](case-pg-01.json)，SHA `a30c69fadd2241d96e393bd6be48591dca37231157e808660c0c09e7d1b5421e`。[277项直接核对](case-validation-01.json)通过，另核[上游完整ID集合及原记录](upstream-preservation-01.json)均未改写。没有重采样、额外DB快照或S04投放。

| 项目 | 整事件案 | 单A01案 |
| --- | --- | --- |
| Case | `58194401-03ca-5383-83b4-ac82886a5acd` | `bad63e2a-9f03-547b-8a0c-243347807c41` |
| Run | `d1b17106-0ee7-4265-ac84-beb9ebf048eb` | `3327b87f-f4d8-451e-b91d-39618622ead9` |
| 真实调用 | C3、C6各1次，0重试 | C3、C6各1次，0重试 |
| 实际C2 | 资产2匹配/1资产、知识4行 | 资产2匹配/1资产、知识2行 |
| 实际C4 | network E05/E06/E07；process E03/E04/E08 | process E03/E04/E08；auth E01/E02/E12 |
| 保存 | 17步骤、48工件、1Result、1采用判断、3成员 | 17步骤、48工件、1Result、1采用判断、1成员 |
| 首轮比较 | initial，无上一Run/Result | initial，无上一Run/Result |

[工具回执](case-log-queries-01.json)的租户、主机、实际成员窗口、完整命中/排除均与冻结预期一致；E06/E12不被额外目的/账号条件误排，E07的0/false/有效空列表保留。未选工具和Deep未走路径不计通过。C1继续保留I原选入/覆盖3，仅单案交集为A01，并有超出本案范围限制。C2实际读取正常知识，K1/K2原文均进入两案C3和C6；不据此推断正文合理使用。

[4次真实生成usage](case-model-usage-01.json)为输入34684、输出13555、合计48239 token；费用未知保持null。每次请求/原答/校验/派生输出及其Run归属完整，4次finish_reason均stop。新Case有完整正文，不沿用上游A/I单字描述；A/I原件及NOT_PASSED未变。

[partial具体依据](partial-delivery-01.json)：两案实际TI/history因预留C4预算跳过，UEBA/graph未接；C1/C6输入有明确省略，外部拓扑未查，成员未决且各有3个未解问题。整案另有领域适用性未定和未解冲突。两案均已正常保存模型结论和报告、采用判断；partial不能改成complete，也不能把其本身判作执行失败。

[质量记录](quality-findings-01.json)包含4模型原引用审查的10条问题及处理（缺原始支持、缺覆盖、缺来源和重复引用等），程序保留判断、未改结论；正文质量标not_checked。另保留单A01 closing_note可能把未选网络查询说成已补查的措辞疑点，后续专门复核，不增加查询或采样。程序保存通过不核销这些质量问题。

## 同Run HTTP出口

[58次无鉴权TCP GET](../streaming-case-result-http-20261115-01/result.json)已通过：14详情/目录与44必要原件，34步骤/96工件目录及正文与唯一PG快照一致；task→attempt→Run→Result/当前assessment和首轮比较空态均匹配。[统一验收](acceptance-01.json)再次核Case/Run/Result三元组和快照SHA一致。HTTP首次离线断言误取不存在的`steps_total`字段，其失败保留；修正后只对已保存响应复验，没有重复HTTP/DB/模型请求。S04和后续测试服务步骤继续独立推进。

调查侧已复用这份唯一快照[离线追加2份查阅卡](../streaming-case-20261115-01/audit-export-01.json)，原38卡/83历史Case文件保持，现40卡；未访问数据库/模型或切换实际4177服务，不能计W3 HTTP接线完成。
