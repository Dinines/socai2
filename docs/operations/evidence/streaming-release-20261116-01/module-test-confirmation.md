# 测试模块正式发布确认

审阅日期：2026-11-16。范围：当前文件、W4/W5及新材料的已保存证据；本次未连接21、未发HTTP、未运行模型/发送器/消费者、未重新执行测试或修改业务代码。仅写本文件，未修改共享根文档或其他模块文件。

**结论：测试/查阅模块0.6.0可纳入本次统一发布，未发现需要修复本模块业务代码的发布阻断。清理后的正式新批验收仍待执行；正式Topic发送入口、4177正式环境配置和新账本登记是执行前必须完成的接线，不能按现有候选示例直接运行。** 本确认不替代发布方最终工件独审、正式切换及实际正常路径读回，不归档整个change。

## 1. 可复用的当前交付

| 项目 | 本次核对与边界 |
| --- | --- |
| W4/W5完整包 | [W5打包回执](../streaming-w5-4177-20261116-01/flow-02/build-03.json)为`test-service-0.6.0-20261116-01`。本次只读重算tar SHA256为`8e31e822e4ea4a0197ea3c70d2f1e8fbdb1c2ff5d3fe95db3302aa859faeae2b`，manifest SHA256为`4ec8b3dfeb6de7584f1d3726a34f5ae2826b8204822eef085d8f90a98d3511f6`；62项文件size/hash全部吻合，服务/页面均0.6.0。与当前工作树共有的54份来源相比，53份相同，差异仅`test-data-design-20261115.md`文档；服务及包内驱动源码相同。本轮没有重打包。 |
| 实际4177 | [W5最终回执](../streaming-w5-4177-20261116-01/flow-02/outcome-summary.json)、[10次GET](../streaming-w5-4177-20261116-01/flow-02/http-final-03.json)及当前[target-readonly](target-readonly-01.json)一致：r4、镜像`sha256:e7a05bac2f3cd7ffecc15be21451bbcdb7a7ad08ea92ef253e081fce38b553e3`，外置配置/账本只读挂载。清理后0活动批次，真实浏览器为空态；不能以此冒称新正式非空流程已验。 |
| 执行布局及逐轮来源 | 当前[页面](../../../../services/investigation_test/web/viewer.js)和[执行流程模块](../../../../services/investigation_test/web/execution_flow.mjs)沿接入/自动触发→任务/attempt→阶段与组件→结果保存→HTTP读回；Case历史/目录完整分页，结果核source_run_id，HTTP接入按subject/task/Run绑定，原答只取实际raw.choices，不用解析或合并输出冒充。清理前[第二轮预览](../streaming-w5-4177-20261116-01/flow-02/preview-round2-entry.ax.txt)明确为周期自动检查，没有挪用首轮POST。 |
| 紫色、领域、跳过原因 | [CSS](../../../../services/investigation_test/web/viewer.css)的test-execution-mark为紫色，红色保留错误；身份/云/钓鱼/内部风险分开显示实际适用性和发现。[领域预览](../streaming-w5-4177-20261116-01/flow-02/preview-domain-detail.txt)及[跳过预览](../streaming-w5-4177-20261116-01/flow-02/preview-skipped-history.ax.txt)保留当时非空证据；source_not_connected与tool_budget_reserved_for_evidence区分，不算查空。最终0.6.0的10项包/页面、14项JS及实际空态证据复用，不把各旧预览版本混称一次最终非空验收。 |
| S04与后置项 | [预算续验](../streaming-budget-20261116-01/README.md)已完成新I、整事件Case第二轮/4成员和本案上一轮比较身份，119项保存核对、48GET通过；原3000/length失败保持历史，不再作为当前功能未完成依据。第8–10步、正文/引用质量NOT_PASSED继续后置，本次不重跑历史矩阵或因质量问题反复采样。 |

## 2. v2材料的模型边界

[新材料核对](../model-blind-data-20261116-01/README.md)与[使用清单](../../../../tools/testdata/CATALOG.md)允许复用：中性来源`telemetry-channel-01`只供程序识别，批次/场景、测试身份、作者说明、答案与映射保存在控制文件；业务观察、原命令、0/false/有效空列表保持。8份实际配置的A/I/C3/Deep/C6输入构造视图未见所列测试身份或预设答案，但这是离线输入检查，未调用模型，也不是对任意未来样本的保证。

本次拟用的[investigation_fixture.py v2](../../../../tools/testdata/investigation_fixture.py)生成1告警/3上下文，`load_fixture`不打开expected目录，输入可独立核tenant、原始字段/身份/字节摘要。它**不在0.6.0的62文件包中**；包内现有生成/发送入口是streaming_fixture/streaming_send。正式读回前应将该v2生成器、material-source及实际导入依赖、选定发送入口单独冻结为本批执行材料，记录摘要；无需因此重做当前只读页面镜像，也不能声称现有包已经包含此1+3驱动。

新批使用正式tenant、新run_id/绝对UTC时间及生成器产生的新主机/UUID，先离线核本次实际payload及A输入投影，再从实际保存的I/Case模型请求核后续输入；不伪造前序模型答案来凑检查。测试标题/操作说明留账本，Case业务标题、告警正文和知识内容不加入“测试/fixture”、预设善恶或作者暗示。紫色标识只出现在查阅层。当前知识索引已清空；开启知识查询不等于已有正命中，不回灌旧评估或历史事故答案；空结果/未接入/未查询分别保存。

**断言须适配当前真实查询。** 该fixture的expected把不同目的地和早于自定义5分钟窗口的记录列为排除项；它们只能用于指定过滤合同。当前[Case查询](../../../../services/api/app/socai2/baseline_evidence_tools.py)按tenant、主机、class_uid和实际`[start,end)`取数，不按目的IP过滤；正式executor配置前后各3600秒，样本-1/+1/+2分钟记录可能都落在范围内。因此本次不机械断言“仅命中1条、另2条必须排除”，应依实际保存的工具参数核对应结果。告警直接source_event_ids仍应只关联生成器指定的那1条来源，直接来源与补查上下文分开。

## 3. 执行前接线项

| 接线 | 当前事实与必要动作 | 性质 |
| --- | --- | --- |
| 正式Topic发送 | [alert_kafka.send_kafka](../../../../tools/testdata/alert_kafka.py)限制`socai2.testdata.<run_id>.raw`；[streaming_send.Profile](../../../../tools/testdata/streaming_send.py)限制`socai2.testdata.<candidate_id>.*`且S01固定12上下文/3告警、S04固定1/1。两者均不能仅换profile发送本次正式1+3。正式[fusion-env](../../../../deploy/aisoc21/streaming-release-20261116-01/fusion-env.json)是`socai2.raw_events.v1`与`socai2.alerts.raw`，broker192.168.1.21:19093/SSL。需一个本批明确入口，加载v2材料并复用send_records的逐消息ACK、独占发送意图、unknown停止机制，显式绑定这两个Topic、tenant、数量、就绪回执hash、私密transport与超时；上下文真实入湖后才发告警。保留原CLI限制，不改字符串/伪造candidate ID绕过；先做最小离线目标/字节/阶段门控检查再投递。 | **正式读回执行前缺口**，不是页面发布代码阻断；禁止拿现有候选发送CLI直接投。 |
| 4177正式代理 | [release.json](../../../../deploy/aisoc21/streaming-release-20261116-01/release.json)已明确r5复用同镜像，指向18024。已存W5实际仍为18424、候选tenant及`streaming-20261115-01`。切换时须生成新的外置service/upstream/viewer三份配置；service与upstream环境标签相同，新批batch.environment同标签，upstream tenant为`00000000-0000-0000-0000-000000000001`、base_url为`http://192.168.1.21:18024`，OpenAPI文件/hash对应本次正式包并核实际服务80操作/55GET。建议标签明确为本次release ID，不能只换URL保留候选tenant/标签。 | **正式切换配置必做**；启动capabilities只是配置声明，必须由正式HTTP context/运行配置佐证。 |
| 新账本与HTTP接入原件 | 继续既有state_root、只读服务挂载，保持`initial_state_import=false`；另用显式publish写新批，不回灌历史账本。记录真实A/I/Case主体、task、attempt关联Run/result，未发生身份为空，按实际状态更新后再结束批次。0.6.0执行首页从账本operations发现对象，并不会自动枚举新业务库。需登记id=`http-exchanges`、schema=`socai2.test-http-exchanges.v1`的公开证据，保存本次Case POST的实际路径/请求/201响应及后来关联的task/Run；自动A/I用其真实任务来源，不伪造HTTP入口。 | **4177非空验收必做**；业务库有新Case而账本为空，不能算页面已读回。 |
| 正式数据与依赖 | 核aisoc实际128/129、所需普通账号读写接线及正式tenant/actor、湖aisoc.raw_events、唯一Fusion/调度、Kafka起点和Redis命名空间。当前正式28表450列，候选32表521列不是正式结果；迁移后以安装verify为准。按本批身份记录起点，不再清库/清Topic/恢复旧备份。 | 已纳入发布计划的必要就绪条件，测试模块不重复执行迁移或起服务。 |

正式配置按当前文件保持I4小时/Case6小时/活动7天、poll60秒、N1；A/I/Deep8192、C3/C616384、64K服务窗。首次initial任务按正常受理/调度验收，不为赶读回改短周期，不等待4/6小时周期或另造第二轮来替代本期已有S04证据。

## 4. 最小正式正常路径与通过证据

“新独立批次、1条v2告警＋3上下文→正式Kafka→A/I→HTTP创建1案→Case首轮→4177”**足够用于本次发布与新材料影响的正常路径读回**。它是对已验第1–7步/F1–F5及S04续验的发布补验，不重新声称覆盖后轮、容量分案、故障恢复或第8–10步。

1. **冻结并确认起点。** 发布方给正式运行/迁移/配置及唯一执行器回执；按新批/源UUID/主机/归并键确认不存在同批旧对象，记Topic partition/offset和账本修订。冻结1+3业务字节、控制预期和当前配置摘要，时间位于当前活动窗口，避免旧日期样本自动过期。只核需要的来源，不全表重复对账。
2. **先上下文。** 三条只投正式raw_events一次，保存每条意图、ACK/partition/offset；真实湖读回核tenant、主机、时间、event_id和原件字段/摘要。确认未因上下文额外生成告警/任务；ACK不等于入湖。该门通过再投告警。
3. **告警与事件。** 一条source-v1告警只投正式alerts.raw一次；从实际存储/HTTP取得canonical告警、事件和任务ID，不把预测ID当实测。核1A/1I、直接来源1条、A/I task→attempt→Run、真实模型请求配置/原答/usage和结果保存读回。允许按实际终态观察，不强制捕获短暂accepted状态；首次程序分析需能形成可用结果。输出截断、解析失败或无法保存是流程未通过，不能作为正文质量后置勾通过。
4. **一案首轮。** A/I有效后，用新operation_key经正式`POST /api/v1/socai2/cases`关联该真实incident；保存完整201及allocations/initial_task，无预造Run。沿真实status_url观察Case首轮，核1案/1成员、当轮模型/工具/原件、结果和当前采用关系，initial/null前轮比较保持。partial/uncertain与执行完成、结构采用和正文质量分别判断；不强迫善恶结论或所有领域都适用。
5. **账本与实际4177。** 发布新live_execution账本及脱敏HTTP接入证据；核4177服务/页面0.6.0与正式环境/租户/合同绑定。打开新案当轮，核POST→本轮任务/步骤/组件→结果，至少读取一个实际模型请求和原答、已有领域工件及真实跳过原因（有则展示，无则标本批未命中）。UEBA/graph/product保持未接入，知识空态/未选用按实际回执；不以新增调用制造展示样本。截图及HTTP响应与同一组真实Run对应，终态不额外启动执行。
6. **收口。** 保存本批输入/运行配置、发送与湖回执、task/Run映射、必要落库快照、HTTP/4177证据和模型质量记录。冻结终态后按同批读取前后摘要核保存未被查阅改写。若unknown先读原身份/offset，不换key或重发；仅修实际程序阻断并定向复验，质量问题单独保留，不反复采样。是否保持正式消费者运行由发布方既定运行计划决定，测试模块不自行停止或恢复。

## 5. 模块出口

- **可发布：** 当前0.6.0只读服务、页面与既有完整包；已有功能/历史真实证据按对应版本复用。
- **当前执行前必补：** 1+3正式Topic入口及冻结依赖、正式环境三份4177配置、新批账本和HTTP接入记录；补齐后按上述最小路径实际读回，不能仅凭health、空态或包hash宣告正式验收完成。
- **继续后置：** 第8–10步、模型正文/引用质量及没有真实命中的展示分支；不恢复旧语料，不将整个change勾完或归档。

本轮只读重算包摘要与查看源文件/历史证据，没有产生新业务验收结果；无需重跑W1–W5全量矩阵。本文件供正式发布聊天读取并并入最终审计/发布回执。
