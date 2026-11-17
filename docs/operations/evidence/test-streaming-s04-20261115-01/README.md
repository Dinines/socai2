# S04：同批增量进入事件与活跃Case后轮

当前 **S04正向更新/比较未通过**，[统一验收记录](acceptance-01.json)保留实际失败。[原生入站](ingress-acceptance-01.json)及A04实际分诊完成，但I真实模型在3000输出tokens处以`length`结束，诊断失败，未产生可用新结论；两Case没有扩员、新Run或新比较。唯一调度在14:09:47Z正常停止、0在途。[134项离线核验](failure-record-validation-01.json)及[44次同源HTTP GET](../streaming-s04-http-20261115-01/result.json)通过仅代表失败记录、停止规则及旧原件完整，不能替代正向验收。来源仍为`s01-ingress-20261115-02`，不重投S01、不覆盖首轮证据。[本步预期](expected.json)与[原件摘要](freeze-01.json)是执行前冻结计划；实际目标使用[当前窗口/profile就绪回执](../streaming-s04-20261115-01/preflight-01.json)，不沿用历史配置推断。

## 要验证的业务效果

E13先真实入湖，A04再经原生Kafka入口进入原I01，新增材料唯一指向E13。A04完成真实分析，事件按实际可用成员形成新的可用业务诊断，原活跃整事件Case才扩员及执行后轮。新Case结果比较自己的上一轮，原首轮/上游结果及原答不改写。固定A01对照仍1成员，无人工check/rerun/H变化，自动检查不从非接收事件触发新任务或Run。

现行`case_update_scanner.follow_current`在自动扩员前检查I诊断当前可用及覆盖；`analysis_case_executor.load_in_store`的自动比较只选显式关联且`active_case_id`指向本案的I。不能把新日志或A04入站本身当作Case自动触发证据。不能以各请求完成时间碰巧递增代替冻结版本和业务变化关系。

## 冻结身份与时间

| 对象 | 本步使用的事实 |
| --- | --- |
| E13 | `324ddc21-7635-5ab6-be3b-c339bd6aeacb`，事件时间2026-11-15 10:39:18Z |
| A04 | 源ID `3d2a3a09-aa5a-524c-8c7a-63232febbef0`，直接来源仅E13；canonical预测`d7bc92ec-691e-5b45-bc03-ccb85367dba8`只作核对，实际ID取读回 |
| I01 | `263a1c58-e9c6-4ba4-9204-3b0568970551`，预期成员3→4，不能错归后修改关系追认 |
| 整事件Case | `58194401-03ca-5383-83b4-ac82886a5acd`，当前3成员/修订1，容量100，预期原案增至4成员且仍是I接收目标，不创建续案 |
| 单A01Case | `bad63e2a-9f03-547b-8a0c-243347807c41`，1成员/修订1，不抢接收目标 |
| 整案上一轮 | Run `d1b17106-0ee7-4265-ac84-beb9ebf048eb`，Result `9cf1a538-ddf2-4df1-aa37-021cbf95d5a2`，accepted/uncertain/partial |
| 单案原轮 | Run `3327b87f-f4d8-451e-b91d-39618622ead9`，Result `2e87d00f-5275-499e-bf03-f851302d5cb3`，accepted/uncertain/partial |

两案基线为[唯一首轮快照](../test-streaming-case-initial-20261115-01/case-pg-01.json)及[统一验收](../test-streaming-case-initial-20261115-01/acceptance-01.json)。保留真实投递/消费/保存/冻结/执行时间，不改写旧事件时间以适应测试。归并按处理时间TTL，原索引合并不刷新TTL；是否还能归入I01由当前实际索引及剩余窗口证明，过期就停止并报告，不能延长旧索引或手改归并。

## 分步执行与直接证据

1. **发送准备。** 调查核当前唯一Fusion、同tenant/connector/Topic/Redis及原归并索引目标/剩余TTL、容量、调度停止和无在途；测试核E13/A04未入库。使用原冻结两份S04字节，独立prepared/receipt目录，仅允许S04两阶段。准备和发送都核profile、实际就绪回执及材料hash。
2. **E13上下文。** 仅发1个raw_events信封，留独占intent及ACK。读回E13原件、时间、对象、0/false/空列表；相对首轮基线新增1事件、0告警/事件/任务/attempt/Run。湖中旧12事件保持。ACK不足以放行A04。
3. **A04告警。** 仅在同prepared、同tenant、同E13集合且原业务基线保持的真实读回通过后发1个raw消息。核新增1告警/1材料/1直接来源/1 A initial，归入原I01，I成员4；没有新I/Case、旧Case此时仍3/1成员、0新增attempt/Run。来源范围必须只有E13，不能再次追加A04自身ID。
4. **真实更新。** 将实际A04/材料/任务/I身份交根，根独占启动当前调度。保留全部自然产生的I/Case轮次，不预设恰好各1次，也不手动check/rerun求命中。原A01–A03和两案initial不重派。A04真实调用、I实际冻结输入/分诊配对、诊断保存及采用状态分别核对。
5. **I先更新再Case。** 核新的I诊断及其Run/输入版本确实可用，业务视图相对上轮发生变化；Case的A04关联时间不得先于使其可用的I诊断保存，Case C1必须引用当时已保存的新诊断，冻结范围/覆盖包含A04且不扩大依据。Case新Run启动晚于对应I完成；比较`previous_run_id/comparison_result_id`指向本案实际前轮。若自然多轮，逐轮跟随真实冻结链；旧失败不可比较时保持原因。
6. **终态保存与HTTP。** 根观察全部终态且无在途后正常停止；测试取得一次正式最终PG/工件快照，核新增链和原材料/Run/原答完整不变，形成唯一actual map交HTTP。HTTP只读新增结果、比较和必要原件，沿同snapshot，不能重建身份或重复模型/数据库取数。

每步未通过只处理具体阻断。发送unknown不重派，已成功阶段不重投；业务错归、来源或保存失败保留，不清数据。上下文/入站读回是前两步必要证据，不冒充最终调查保存验收。

## 查询范围与对照

整案新成员最大事件时间为10:39:18Z，默认前后1小时的全案窗为09:14:18Z–11:39:18Z；如果该绑定选中network，预期E05/E06/E07/**E11/E13**。E11在首轮右边界外，但本轮扩窗后合法进入。process预期E03/E04/E08，auth预期E01/E02/E12。实际若只选部分成员，按该binding成员重算窗口再核，不能强行套全案窗或要求所有工具都被选中。

单A01固定成员窗不变，同主机上下文在将来合法查询时可能看到E13，但本步不触发该案新查询以验证它；本步对照是自动无新Run/无扩员。旧原件和结果不因湖中新数据而回写。

## 发送器最小缺口及验证安排

实施前`tools/testdata/streaming_send.py`仅支持S01的12/3消息及“全零初始业务”门控；现已补齐本步最小选择及增量门控。在原入口增加明确的S04阶段选择，准备仅1上下文/1告警；复用`alert_kafka.send_records`的幂等producer、独占intent、逐条ACK和unknown停止规则，不建立新框架。S04门控使用冻结首轮基线及**增量为零**的业务读回，不把已有6 Run误判为必须清空。

必要直接验证仅覆盖：选择S04不会准备或发送S01；E13/A04唯一直接来源和原字节；不读取expected/control生成消息；缺少/错误基线、E13读回、阶段或hash拒发；一次intent后拒重派、unknown不继续；复跑受修改影响的既有S01发送器直接检查。这里的单点测试使用受控Kafka producer和预构造的读回JSON，不涉及模型替身，也不记作实际S04运行证据。21发送使用真实SSL Kafka，来源验证使用真实数据库和数据湖；后续分析使用真实模型请求。实现前OpenSpec strict；通过后才用根侧最新实际回执准备发送。

原A/I单字问题和两Case首轮10项引用问题原样保留。新轮执行/交付/业务判定/采用/引用和正文质量分开记录，质量问题单列后置，不重采样。S04只覆盖当前增量链，不包含H/定向/手动综合、容量矩阵、W2/W3/W4接线或正式发布。

当前配置新增`phase_set=S04`与首轮`baseline_snapshot_sha256`；S04-context额外要求实际不存在/基线不变的preflight-readback，S04-alerts要求真实E13回执与全零业务增量。16项直接检查及Ruff通过，独立source overlay本地validate通过；prepared只含S04两条原字节。旧S01目录及源码快照不覆盖。

## 已取得的实际来源证据

[预检](readback/preflight-readback.json)证明E13/A04不存在、湖24行、原6个Run及两Case不变。[E13读回](readback/context-readback.json)证明湖仅新增E13、旧行不变，PG快照摘要与预检一致；扩窗network命中E05/E06/E07/E11/E13，原件及false/空列表保留。[A04读回](readback/alerts-readback.json)证明仅新增1告警/1材料/1直接来源/4对象/1事件成员/1 initial任务/1来源工件，0新I/Case/attempt/Run。实际身份见[identity-map](readback/identity-map.json)，随后分析沿此身份继续。

首次发送调用因测试封包漏带`kafka_security.py`在创建Kafka客户端之前失败，[原失败回执](invocation-send_context.json)保留；远端不存在发送intent或ACK。补齐当前源码后另存[调用回执02](invocation-send_context-02.json)，首次实际E13发送成功，[修复记录](packaging-recovery-01.json)保留文件摘要。没有重派消息、修改原字节或重写旧失败。分析结束后仅取一次正式快照，独立记录实际保存/查询/模型质量及HTTP结果。

## 实际失败链与尚未覆盖的成功分支

最终[PG快照](analysis-pg-01.json)SHA为`0af1dc0ae2b9b709070459c1d74e669d31a375a36514322dd25276d5ee8e4af3`，在根侧正常停止后使用当前候选普通reader/TLS/只读repeatable-read取得一次。新增5任务：A04完成、I失败、3条等待I检查因`automatic_attempts_stopped`跳过；仅2个新attempt/Run，0重试。[实际映射](actual-analysis-map-01.json)记录真实身份，未预填Case下一轮。

- A04 Run `e2e3e80e-031c-5641-909e-6f913cf50e16`：3次真实查询、1次真实生成，completed/complete；结构成功，理由仍单字“告”，质量NOT_PASSED。
- I Run `c119d6be-e735-5189-a6d2-8db8490ab84d`：冻结4成员、4份当前可用分诊和12条配对查询回执；1次真实生成，failed/none，错误`model_response_not_complete`。原响应`finish_reason=length`、output3000与实际请求`max_tokens=3000`一致，正文停在source_refs列表中；[失败分析](failure-analysis-01.json)及[根侧离线复核](../streaming-s04-20261115-01/saved-response-review-01.json)均保留原答，没有保存时截断的证据。
- 新失败诊断`8f82c04a-4e3b-53f8-9d97-8eed33cd9180`的summary/diagnosis/generated_at均为null、错误明确；旧I当前指针保留，但不把旧3成员诊断冒称适用于当前4成员。
- 两Case仍分别3/1成员、原scope_revision/采用/初始比较不变，无新task/Run/Result/C4；原6 Run及模型原答逐行保持，[旧记录核验](upstream-preservation-01.json)。这验证失败边界，不能证明I成功更新、Case跟随扩员或上一轮比较成功。

[实际调用统计](model-usage-01.json)：2次生成，输入8709/输出3318/合计12027tokens；费用未知，不记零。A/I实际单次输出3000、Run合计24000和Case C3/C6单次8192分别是不同层次/环节配置，本轮没有改限额。[质量记录](quality-findings-01.json)单列单字、引用和截断；原首轮问题不改写，不加额度或重采样追认本批通过。

首次离线断言误将I的`change_view`字段用于A，KeyError已保留在[验证器失败回执](offline-validator-invocation-01.json)及原脚本；按实际A整份输入/I业务视图摘要分别核对后，同一快照134项通过，0新增PG或模型请求。预先准备的成功分支脚本`verify_success_path_not_executed.py`未执行、不计覆盖。W2非空/跨Run、4177 HTTP接线、结束审计及统一发布仍未由本步完成。

HTTP同快照44次GET均200：31项详情/目录/来源、13份新增Run必要正文，5新任务/2Run/7步骤/18工件目录一致。新失败诊断、原答及停止原因可读，旧I指针仍在但`valid_for_current_input=false`/stale；两案当前assessment的动态新鲜度均为stale、原因`incident_context_changed`，旧保存记录本身未改。无新比较，不重复旧58次读取，不追加业务写入/数据库取数/模型调用。
