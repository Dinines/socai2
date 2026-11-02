# 第5段：Case实际输入、模型视图、Tool与历史复用

**2026-11-02实施更新：** [第4批](field-alignment-fix4-20261102.md)已补S5-01：A检测/来源及T同次confidence/判定/建议、Run事件时间进入真实context及hash；新增模型字段值2048字节，guard和省略标记保留。S5-02/03原文语义及Tool明细仍待第7批；以下保留修前事实，尚未线上验收。

日期：2026-11-01。接续[六段核对计划](field-alignment-confirmations-20261101.md)，本段本地核对完成，未实施修复或线上验收。需求仍为远端 `origin/codex/functional-analysis` 的 `48f54abd42d643ff53a71fffbb1f6045a90d9f80`（本段再次只读核对未变）及用户第1—16项决定。源码为 `b758351d7125590c090a751837f96c86df331652` 加现有工作区，不能将未提交的r13修复称为HEAD内容。

边界从Fusion已接收的数据开始。本段只问已有材料怎样被调查消费、能补查哪些字段，不要求上游补数，也不比较调查页面设计。证据目录：[第5段本地观察](../operations/evidence/fusion-field-stage5-20261101/manifest.json)。

## 结论

现有Case已有冻结来源、当前成员范围、模型省略标记、分诊与人工处置分离、历史报告上下文、受限Tool和保存后读回能力。**无需为补字段另建Case文档记忆系统。** 但“数据库有值”“Run有原文”“模型能看见”“Tool能查到”并不等价，确认三组内部消费缺口：

1. **S5-01：已有检测字段与同次分诊评分未进入Case投影。** 规则、ATT&CK、Fusion置信度及其依据、同次分诊confidence等缺少稳定的结构化路径，影响用户第3—6项要求；不能依赖它们恰好重复出现在raw或摘要中。
2. **S5-02：原始材料被完整冻结，仍可能整体不向模型展示。** 现有输入合同会拦截包含原始OCSF结构/编号的文本；其中已收到的PID、命令行等没有单独的、符合合同的语义投影。已有省略标记，所以这是可用内容覆盖缺口，不是静默入库丢失。
3. **S5-03：Tool没有读取部分已存湖字段。** 网络动作/结果、源端口、目标主机名、会话关联，以及保存在OCSF中的进程明细，都不能由当前两种湖Tool完整补回。按调查用途补最小字段或有界明细读取即可，不需要通用查询框架。

S1—S3的身份、事件引用、归并及IOC投影问题沿用原编号；这里说明它们到达调查端后的影响，不重复计数。补上述数据也不能直接解决r13报告的空查询误推断、引用和生成/校验问题，第6段单列。

## 实际路径与逐项支持

| 材料/能力 | 当前路径与状态 | 判断及功能影响 |
| --- | --- | --- |
| Case成员与时间范围 | `case_context`从本租户`Case.alert_ids`取成员；请求可选子集，非成员拒绝；Alert按event_time/id读；窗口有时区、转UTC、最长7天 | 已支持显式选成员；未读成员单独记缺口。Case当前成员与历史Run冻结范围不同，不能打开旧报告时自动补新成员 |
| 告警基本信息 | A证据有canonical alert_id、标题、event_time、severity、status、disposition、连接器ID、主机、实体、source_event_ids、摘要和原文 | 当前人工处置随A保存，不能当成攻击事实；实体/IOC缺口承接S3-03 |
| 检测规则及ATT&CK | Alert独立列已有rule_id/name、mitre_tactics/techniques；A投影不取 | **缺口**。有就传、缺失空；标签是来源检测标签，不能转换为已证实攻击阶段 |
| Fusion评分 | Alert已有confidence/label/rationale；A投影不取 | **缺口**。应标Fusion评分和已有依据，不以分诊评分替代；S1-07的默认值/实际计算状态仍需先区分 |
| 分诊判断及评分 | 最新`triage_verdict`按canonical Alert ID关联，按ts/id倒序选一条；T保event_id、verdict/rationale/auto_closed | **部分支持**。confidence、findings、proposed_actions未取；run_id/ts也未进入冻结T。原event_id仍可回查，不能称完全无法追溯 |
| 当前人工判定与旧分诊 | A保当前disposition，T保同一历史事件的verdict/rationale；未把Alert.ai_score混到T | 分离正确。当前问题是漏评分，而非已经把新判定和旧分数拼错；修复要从同一T.payload取confidence |
| 原厂、来源编号、厂商编号 | A只有canonical alert_id、source_connector_id、source_event_ids；Fusion identity和external_id未投影 | 来源解释不完整。原厂含义先按S1-02处理，不能把identity.source/connector_type直接命名为原厂；页上source_alert_id与Tool内部ID不能混用 |
| 来源正文 | 冻结Case.description、Alert.description、Alert.raw_event；原文完整hash和截断信息保存；模型另取有界视图 | 有保留、可读回，但不保证模型拿到全部字段。S5-02详述 |
| 已有IOC/库存资产 | enrichment中的IOC结果没有进入A；API ORM本身又没映射PG iocs；Case没有查询库存tags/匹配依据 | 承接S3-03/04；按必要实体/IOC关联补来源。页面资产标签不应一概塞入模型；产品返回tags也不等于assets.tags |
| 湖补查 | 当前仅process_activity、network_connections；按租户、Case主机、固定半开UTC窗口、类别过滤；limit默认20/最多50并多取1条判断截断 | 约束已实现；查询字段范围仍有限，见S5-03。不支持任意SQL、自动扩窗口或完整父进程链 |
| 产品补查 | CrowdStrike的get_host；canonical Alert→具体connector实例→该告警主机；派发时重读连接器和能力 | 已有来源绑定；只提供当前主机快照，不证明历史在线/隔离状态，不等于库存资产；本段未实调厂商 |
| 空结果/失败/模型裁剪 | Tool有available、query_status、returned_count、model_view_row_count、truncated；空结果coverage/absence_reason均unknown | 程序已有区分。模型视图裁掉所有行也不会将原有行的结果标success_empty；报告误读需另修 |
| 证据对应 | 湖行event_id精确匹配成员source_event_ids→row_alert_refs；同主机不作为精确对应 | 逻辑已支持，受S2-01/02的ID/入湖断点影响；匹配来源不等于证明因果 |
| 历史上下文与复用 | H1引用旧Run/报告并声明旧判断；只在同成员/窗口、材料及版本兼容时考虑复用相同Tool/参数的成功结果 | 已有有界上下文，不需新增通用记忆。湖晚到数据不会自动进入材料hash，要求重新查应使用refresh_queries；产品当前快照不复用 |
| 结果与证据读回 | Run步骤保存实际模型请求、Tool参数/结果及模型视图；GET读保存工件 | 已支持。单行证据GET只能读取Tool当时选回的列，不能把它描述成可取出未查询的完整湖原文 |

主要实现：[case_context及执行/复用](../../services/api/app/investigation_v2/case_analysis.py)、[来源冻结](../../services/api/app/investigation_v2/case_source_material.py)、[湖Tool与模型结果](../../services/api/app/investigation_v2/case_analysis_tools.py)、[产品Tool](../../services/api/app/investigation_v2/case_product_tools.py)、[证据读取](../../services/api/app/investigation_v2/case_evidence.py)、[步骤/报告读取](../../services/api/app/investigation_v2/case_views.py)。

## S5-01 已保存字段未进入调查

断点在`case_analysis.py:244`的`case_context`，核心A字段构造位于270—278，T位于284—289。本地观察使用已有值的实际Alert ORM对象和一个完整的triage事件，替换DB返回行后调用真正的`case_context`/`model_context`：

- rule_id/name、mitre_tactics/techniques、confidence/label/rationale、ai_score/recommendations、connector_type、external_id均存在于输入对象，却不在A或模型A字段中；Fusion identity/IOC结果也没有投影。raw特意不重复这些独立列，排除偶然兜底。
- T保留原事件的true_positive判定和理由，而A当前人工判定是benign_true_positive；T的confidence/findings/proposed_actions被丢在投影之外。没有证明两个判定被错误合并。
- 只改变未投影的rule_name/confidence，实际材料指纹不变。这说明指纹只覆盖已消费材料，不代表发生了缓存查询错误或湖数据变化；补字段时必须同时纳入冻结材料/指纹和兼容版本判断。

最小修法：依据第3—6项增加有来源含义的检测对象和同事件T字段，保留canonical ID、来源事件ID、接入来源编号的区别。分诊confidence从该T.payload取，附原Run/事件/时间；不要从Alert.ai_score配当前人工disposition。findings/proposed_actions按已有分析建议标注并限额，不提升为独立原始证据。原厂只消费已明确的原厂值，未知留空；外部ID/原厂不能凭连接器猜。

并非所有页面字段都必须成为模型输入：负责人、全量评论、所有资产标签及处理活动应先有可靠API保存/读取，只有本次调查需要的处置背景才作为带来源的历史判断。S4的管理持久化缺口不能靠手写Case文档长期弥补。

## S5-02 冻结原文不等于模型可见

实际限额：Case/Alert说明各最多4096字节、单告警raw最多16384字节、整Run冻结材料131072字节；hash覆盖裁剪前完整文本，但**hash不能恢复未保存全文**。模型来源总预算8192字节，Case说明最多1024，其余按告警分配，单说明最多1024、单raw最多2048。限额和省略原因已标注，不建议扩大总预算。

另有独立输入合同：完整字段在嵌套和裁剪前经过`classify_message`，命中则冻结原文仍在、模型text为空，`model_omission_reason=llm_input_contract`。本地第4项观察给出一个已收到的OCSF进程对象：原文中的PID 24601、命令行、父进程PID均保存；模型raw为空，其他字段也没有这些内容。

最小修法是从**已有且明确的业务字段**生成有界、带来源路径的语义投影，并沿用现有输入合同与非指令标记；保留原始编号及原件供证据查看，不关闭guard、不编码绕过，也不要求上游改变材料格式。哪些字段应投影由调查功能决定，不能只删掉编号就把未知原文整体当成可直传内容。

现有`model_context`对同源重复摘要去重、对H1未决项限额并标省略；纠错压缩也保留来源正文，省略元数据另有声明。这些不是新增丢数问题。已有用例覆盖原文界限、合同拦截、完整hash变化、旧版复用兼容及H1；本段只读复核实现/既有结果，不重跑未变用例。

## S5-03 补查字段不足以恢复已存业务信息

| Tool | 当前查询/模型字段 | 已存但未被该Tool读取的例子 | 对调查的影响 |
| --- | --- | --- | --- |
| process_activity | event_id/time、主机、进程名、文件路径、SHA256、账号、class/activity、action/outcome；模型以event_kind替代两个原始编号 | OCSF原文内已有的PID、命令行、父进程等；session_id | 能核对进程记录，不具备完整进程明细/父子链。不能因Tool未返回就说来源没有这些数据 |
| network_connections | event_id/time、主机、进程名、source_ip、dest_ip、dst_port、protocol | 湖列src_port、dst_hostname、action、outcome、session_id以及原文 | 难以核对完整连接端点、已记录的允许/阻断或结果与同会话关系；TCP/443仍不能推出HTTPS |
| product_host_details | 当前device_id、hostname、平台/版本、IP、最近/首次在线、隔离状态、tags等白名单 | 历史进程、历史网络、历史设备状态 | 这是现有产品能力边界，不是假定已有这些数据却丢失；不纳入上游补数任务 |

湖已有列/原文写入见[lake_writer.py](../../services/fusion/app/services/lake_writer.py)的`_INSERT_COLUMNS`及`_ocsf_to_row`；S2-03/05会影响动作映射和大原文可读性，先沿原编号修复，不把未成功写入的字段当作可查现值。

最小修法：优先补已落列且直接支撑判断的网络action/outcome、完整端点/会话字段；必要时按已返回event_id读取有界进程明细，仍限制同租户、主机和窗口。若只有原始activity编号，需明确语义投影，不能靠`event_kind=process_activity`宣称具体动作已核实。返回字段变化要更新查询合同/复用兼容，防止旧窄结果被当成新字段已查询；保留空/失败、裁剪、来源对应及观察时间。

产品参数`source_alert_id`实际是canonical Alert UUID，枚举与运行时配对检查一致。它与页面第2项的Fusion接入来源编号同名但不同义；这是接口命名注意项，**不能为对齐页面而直接替换这个Tool参数的值**。本段未发现因该参数发生串连接器查询。

## 冻结、复用和上下文应保留的边界

- 原始Run固定all/selected/read成员、窗口、来源正文、完整hash及模型/Tool记录；新的Case资料不覆盖旧工件。当前Alert链接与冻结来源分开。
- A是当前告警材料；T和saved_analysis是既有判断；H1属于旧Run；E是查询结果。历史引用编号保留旧Run作用域，不把旧A1等改成本次A1。
- H1选取与当前成员有关的未决问题、未解决成员及关系，合用2048字节预算；省略报告段/项有计数。仍保存完整历史报告，不需要再复制成另一套记忆文档。
- `material_hash`排除新问题、包含当前已投影来源；显式追加要求同成员集合/窗口。`refresh_queries=True`可要求新查；湖成功结果还需同Tool/精确参数，进程合同须为v2；产品当前状态不能复用。未宣称r13覆盖复用，本批实际0复用。
- 执行已有4模型/4Tool/24000 token/120秒边界、未知usage停止、required_tools及失败缺口；“要求某Tool”或“尝试过”不代表成功取得证据。本段不扩大预算、超时或框架。

## 本地证据及未验范围

1. [四项投影观察](../operations/evidence/fusion-field-stage5-20261101/observations.json)：实际函数、替代DB返回、纯合成字段。首轮尚未完成第1项时，观察脚本`json.dumps`未处理datetime而报错；保留[初始脚本](../operations/evidence/fusion-field-stage5-20261101/probe.initial.py)和[错误回执](../operations/evidence/fusion-field-stage5-20261101/observations.initial.json)。仅将观察序列化改为`default=str`后四项完成，每项立即保存；不是业务修复，也不是四项验收通过。
2. [既有r13原件复核](../operations/evidence/fusion-field-stage5-20261101/saved-r13-review.json)：读取A/B各3个模型请求和2个Tool结果。4告警×3请求×说明/raw两字段＝24次来源字段出现，全部与该Run冻结短原文相同且未截断。Tool保存行与模型行均1/1/0/0，A分别对应A1/A2，B为success_empty、覆盖及空原因unknown，0复用。各原件hash记在派生文件，不改旧原件。
3. 这只能证明r13的短样本已展示及实际查询返回；A是人工fixture，不证明所有Fusion OCSF原文都可进入模型，也没有证明字段补齐后的报告质量。
4. 本段无业务代码修改、真实DB访问/写入、新Run、模型、湖/厂商查询或部署。既有测试只读复核，不新增通用测试框架。真实字段流转/修复验收留待最小修复实施后按具体功能验证。

同轮已接续完成[第6段报告影响与修复顺序](field-alignment-impact-and-repair-plan-20261101.md)，将内部数据缺口与生成/校验缺陷分开排序。r13批次保持结束，OpenSpec 5.3不核销，不归档、推送或合并。
