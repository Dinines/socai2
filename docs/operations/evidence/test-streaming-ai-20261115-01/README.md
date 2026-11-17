# S01 同批 A/I 真实分析：准备与保存验收

状态：**真实A/I执行、保存核验及62次同源HTTP读取通过，模型正文质量NOT_PASSED。** [统一回执](acceptance-01.json)只收口本子步。本目录沿用 `s01-ingress-20261115-02`，不是第二次告警投递；不表示Case/S04或完整change通过。

输入沿 [通过的入站映射](../test-streaming-s01-ingress-20261115-02/readback/identity-map.json)、[PG基线](../test-streaming-s01-ingress-20261115-02/readback/alerts-pg.json)、[冻结清单](preparation-freeze-01.json)。来源配置为 [sources-plan.json](sources-plan.json)，运行参数只接受根侧 [当前analysis.json](../../../../deploy/aisoc21/streaming-candidate-20261115-01/analysis.json) 与实际装载回执；旧ingress文件中的调度关闭表示入站时点，不当作随后执行profile。

## 最小真实来源与保留缺口

| 来源 | 本步供给和判据 |
| --- | --- |
| assets | 只安装1条本批synthetic host资产，明确host/IP、用途标签和原背景声明。`source-import.sql`只INSERT，不更新/覆盖已有记录；明确库/安装身份/tenant及冲突校验，事务保存。`source-readback.py`以普通reader、TLS及只读事务核全部声明字段。同资产按host与IP匹配两行，distinct资产为1；不能说发现两台主机。 |
| history | 不造历史告警/分诊。真实SQL为同typed namespaced object、`[告警时间-24h,告警时间]`、排除自己。A01预期查空，A02应含A01，A03应含A01/A02；多对象可产生多行。已保存分诊/反馈是否存在取决该查询冻结时点，与来源行一起核，不强制串行顺序。旧失败批connector namespace不同，不能混入。 |
| threat_intel | 冻结夹具无情报声明，导入0条。实际PG查询应`completed`且空rows，不用替身返回空。只验证查空；正命中及外部厂商情报未验。查空不证明安全。 |
| 账号/知识/日志 | background中的账号用途只保留原声明；当前A资产SQL不选user/metadata，不能说已作为独立账号背景传给模型。知识未导入/索引，UEBA/graph关闭，留后续Case。12条湖日志已保存，A不调用C4日志查询，不能把入湖当作A已查。 |

资产criticality显式设为medium，仅作合成字段，不是业务风险真值；授权`not_provided`、维护记录null保持，不构造授权证明。原background/knowledge文件及其状态不改写，实际导入状态由新增回执证明。

[来源验收回执](source-acceptance-01.json)已通过：记录`db23c38e-1802-59d8-ba1e-ee38b2df3d30`在安装事务和普通reader读回中字段全等；[普通reader快照](source-reader-01.json)证明候选同库/TLS1.3/只读事务，host/IP共两行、distinct资产1条。历史/情报插入均0；其分析时真实查询仍待。

首次[安装失败](source-install-invocation-01.json)因候选表必填时间无默认，旧013迁移的默认假设不适用；[实际列检查](source-schema-after-failure-01.json)证明无默认且目标记录0，事务已回滚。保留旧脚本/计划，修正为显式导入事务时间后[第二次安装](source-install-invocation-02.json)通过，不改表、不重派业务；这些时间不表示事件时点库存。整目录传输曾被自动审批拒绝，未执行；随后只传6个经核实必要非密文件并核摘要，凭据始终只在21受控文件中。

## 已冻结的本步通过/失败判据

1. **身份和执行入口。** 复用原3条A与1条I initial task，不再发Kafka、不另建Case/执行器。原材料、来源引用、事件成员不改变。根侧提供实际模型路由、IO合同、tokenizer、预算和调度profile/hash；运行及Run中的policy快照需一致。20秒I检查、30秒Case检查、5秒重试/最多1次、1秒poll以实际装载为准，正常自动窗口须覆盖单Run时限，不以等待时间代替profile。不得预填总Run或模型次数；自然新增I检查按真实task记录。
2. **A输入和真实来源。** 每个A Run只有对应告警与其固定material；原正文、OCSF、对象、来源ID与入站快照一致。三类工具的请求/真实状态/参数/行/截断/原件须保存。assets命中和history成员按上表核；threat_intel真实查空。失败、未查和查空不同，来源失败不能改写为空成功。查询回执与原件按各自Run/step链接，不能串批。
3. **真实模型及保存。** 同一task→attempt→Run→输入/policy→step→model_request/原答/validation/model_response→装配结果可追溯。原请求含实际模型、提示/Schema、输入边界与来源映射；实际响应和usage有证据。模型原答、校验错误、补答前后内容都保存；不能由HTTP200、model_request或工件存在推断模型成功。成功A保存triage、解释及采用状态，成功I保存诊断；latest指针、历史Run与各自来源保持一致。usage未知保持未知，不记零。
4. **I前序与实际覆盖。** I自身不执行工具（max_tool_calls=0）。核每个I冻结的selected members、triage_validation与paired query receipts：可用A必须同alert/material/Run；不借用随后产生的较新结果补写旧输入。每轮按真实冻结时点记录A可用/缺失，不要求初轮等待3A。最终自然更新若使用了A，需要已保存证据证明。`selected_alert_ids`、模型成员映射、验证后的`member_coverage`及输出covered IDs相互对应，覆盖不超过实际选入范围；待复核和未分析分别保留。
5. **旧失败批实际跳过。** 原3A completed/1I resolved保持；4个旧task应由正常资格检查变成skipped/closed_before_start且无attempt/Run/模型/新结果。此前只关闭主体，不是已执行跳过。若出现任何旧批分析或原件改写，判程序阻断，保留失败，先修本步。
6. **结论分层与交接。** 成功流程、交付完整性/采用、待复核、模型正文质量分列。格式、范围或调用失败若阻断程序，就不能声称流程通过；正文质量另记原答/问题/范围，保持NOT_PASSED，不反复采样求好答案。测试只做一次PG/原件快照和真实map，交HTTP核task/Run/结果/覆盖/原答。无需重复35次入站GET、空态或未变单测。若首次保存检查失败，保留该证据，仅定向复验具体修复。

执行后出口须含每条真实task的全部attempt、Run状态、输入与policy原件、工具/模型请求响应、结果ID、I选择/覆盖及最新/历史关系；旧4任务实际终态；本步调用数/已报告usage及未知项；未覆盖与质量问题。S04、Case首轮/更新/比较、W2非空/跨Run、W3/W4另按阶段推进。

## 实际执行与保存结果

根侧[实际运行及停止](../streaming-ai-20261115-01/stop-01.json)后，测试以普通reader/TLS1.3/只读重复读事务取得[正式PG快照](analysis-pg-01.json)，摘要`d959c407b2169c633ec2efc22d7e02434853985c4a3a9785661246b3cebf0f96`。[离线核验](analysis-validation-01.json)全部通过，[真实map](actual-analysis-map-01.json)已一次性交HTTP；没有重跑模型或更改原件。

[HTTP实际读取](../streaming-ai-http-20261115-01/result.json)62次无鉴权GET全部200：4个实际Run/task/result、17步骤、45份Run工件目录、29份必要正文与本快照一致；9查询回执、I冻结成员/覆盖及旧4任务跳过均读回。生命周期摘要按同份86400秒实际核对。测试只交叉核验回执ID与摘要，未重复GET或数据库查询；W2代理和4177尚不在本次直接HTTP验收中。

| 项目 | 实际观察 |
| --- | --- |
| 新批 | 原4 initial task→4 attempt→4 completed Run，3条triage及解释、1条diagnosis；当前采用指针和原始输入/查询/模型工件可追溯 |
| A查询 | 9次真实PG查询均completed。每A资产两行/distinct1；A01/A02/A03历史分别0/3/6行，对应0/1/2个不同告警；情报均真实查空 |
| I | 3A均usable/current，冻结配对9份真实查询回执；自身0工具查询。保存的结构覆盖为3/3、delivery complete，同时3条finding和1条问题待核；不把结构覆盖当正文分析质量 |
| 旧批 | 4 task实际skipped/closed_before_start，无attempt/Run/新结果，旧关闭主体、来源失败及原材料保持 |
| 配置 | Run policy快照均匹配根侧实际预检；HTTP已由HTTP方对齐同一1天/I20秒/Case30秒/重试5秒配置，原task重试参数未改 |
| 调用与费用 | [4次真实生成](usage-01.json)，provider报告输入10,652、输出3,370、合计14,022 token；费用未知。未把tokenizer测量计为生成或把未知费用计零 |

[质量问题](quality-findings-01.json)明确NOT_PASSED：3A的rationale只有“告”，伴随重复引用，却返回benign/0.95；I摘要、结论、成员分析等正文为“A”。原答来自真实provider并保存在原件中，结构校验/保存成功不证明内容有效。按已确认范围单独记录后置，未改答、未追认安全、未反复采样。

[已保存请求的来源核对](saved-view-source-check-01.json)还确认4份请求均包含资产用途标签，各A来源映射指向本Run真实资产回执；后台background元数据未整包透传。此检查仅证明输入可见性和来源配对，不证明模型理解或结论正确。

首次只读快照脚本误以`results.run_id`查询，实际列为`source_run_id`，事务失败且未产出快照；[失败回执](analysis-capture-invocation-01.json)和旧脚本保留，定向修正后[读取通过](analysis-capture-invocation-02.json)。这是测试查询错误，不计业务/模型失败，也不隐去失败历史。
