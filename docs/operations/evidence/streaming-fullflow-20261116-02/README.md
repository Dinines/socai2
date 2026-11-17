# 21新批完整流程02

状态：本批正常业务流程、HTTP、同包复核及4177实际浏览器均已通过；最终交接见[delivery-receipt.json](delivery-receipt.json)。模型质量问题保留后置，简单材料目录执行入口尚未实现。负责人2026-11-16明确要求“部署到21 并测试完整流程”；本批名已核不存在后新建，按[现有规划§8](../../../../openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md#8-当前21发布后完整流程2026-11-16新批02)逐步执行。协调方负责唯一部署，测试仅在实际部署就绪及历史清理核零两份回执齐备后执行本批，HTTP只读同包复核。

## 本步准备

- 新中性材料：首批3告警/12上下文，后续1告警/1上下文，全部新身份。原始租户、来源和关联键保持，模型材料不暴露批次/测试/答案提示。当前policy及三个输入profile按新发布显式绑定，不用历史参数回落。
- 实际顺序：只读就绪→上下文ACK与湖读回→告警ACK与Fusion/A/I→HTTP整案/单案首轮→新增第四告警与I更新→整案后轮/最近前轮比较→no_changes→完整HTTP/4177及独立同包审阅。
- 模型全部真实调用，不注入截断/空答，不复制旧分析；真实partial/none按当前合同继续，质量单列不重采样。周期保持4h/6h，必要显式HTTP check标source=user，不声称自然到时。
- 负责人追加“部署完整服务并清除历史数据 跑完整的测试”；清理范围和核零由协调方负责，测试侧不另做清理。两份实际回执齐备后从空态投放，不回灌旧业务/旧账本，本机旧证据保留。发送unknown先查回执不盲重发。

## 旧脚本复用核对

| 原批工具 | 本轮处理 |
| --- | --- |
| streaming_fixture、Fusion投影、当前模型builders | 复用当前源码，以新的材料/显式policy生成；离线禁网络，原模型预期不进入wire |
| send-batch及alert_kafka ACK循环 | 复用逐消息ACK和不可覆盖回执；S04等待两首轮真实终结并完成保存读取，不要求模型结论全部可用 |
| prepare-batch/invoke | 去除r3/旧env/容器硬绑定，读取本批新release执行配置；禁止旧start/upload-runtime路径 |
| HTTP建案/更新 | 不照搬A/I全部valid_for_current_input门槛；使用当前实际材料/终态与正式API，201/202及unknown原回执保留 |
| capture/export | 仅本批实际身份；每次request原件关联原答，包括同step多次纠正/补答，不能用step单值字典覆盖前答 |
| ledger/4177 | 等真实结果后按当前Document合同生成新账本及质量记录，清空后的活动账本只加新批；旧首轮失败结论、固定6文件和source_answer含义不照搬 |

[reuse-source-manifest.json](reuse-source-manifest.json)保留参考脚本来源hash。旧批文件原样不动。本轮新准备/执行脚本只操作新目录，所有可变地址、端口、角色、超时、文件路径均在[preparation-config.json](preparation-config.json)及最终batch/profile.json。

## 验证与后续绑定

已绑定协调方落地的`streaming-release-20261116-04` release/identity及其明确沿用的r2运行policy；这是本次显式配置，不是失败后回落。新Fusion/dispatcher/HTTP名均r4，4177本次为r6，实际镜像ID和就绪状态仍待发布回执。发送包只冻结17份业务wire和当前必要合同/ACK实现；预期、生成器控制说明及模型预览不上传为模型输入。生成器的通用runtime_dependencies只标离线依赖，具体执行合同以本批§8为准，绝不据其通用短周期提示改变本轮4h/6h。

准备结果：

- [材料核对](material-checks-01.json)：12项通过，4告警/13上下文全新UUID、租户/来源关联、严格时间边界及不同主机/账号/目标对照保持；业务0/false/[]留在原件和当前C3视图。
- [当前模型视图](input/model-views-02/model-view-checks.json)：4个A、3/4成员I、3成员整案/1成员单案/4成员后轮各C3/Deep/C6，共15份，禁网络。无编造前序模型结论；实际执行时仍须保存本轮真实A/I/C3输出。早期全4成员的8份离线预览原样保留，不当首轮范围证据。
- [发送器检查](sender-checks-01.json)：7项通过，严格12→3→1→1，缺清理或发布回执拒绝发送，首轮终结/读回前拒绝追加，既有ACK回执禁止重发，冻结字节变化拒绝。生产者为明确内存替身，0真实Kafka。
- [HTTP/导出检查](driver-checks-02.json)：5项通过，POST先存意图、unknown不重复、真实保存原答按request身份独立导出；同step多请求使用明确临时派生对照，历史证据不改。初次误以为D3原请求共用step的失败保存在[01](driver-checks-01.json)。
- [完整读取驱动检查](http-driver-checks-01.json)：以保存的D4c HTTP响应离线验证194次缓存后读取、6Run完整46steps/134artifacts及Result/比较，0新HTTP；这是驱动验证，不是本批21执行。

[invoke.py](invoke.py)不提供stop/start/restart等业务服务操作。实际命令需本批activation.json定位协调方两份原回执及SHA和实际处理镜像ID；P0完成时该文件尚不存在，P1已按实际回执生成[activation.json](activation.json)。发送阶段只使用有界临时测试生产者及明确配置，既有业务容器不重建。上传、来源注册、空态核对已见下方P1回执；业务读回/账本仍待对应实际步骤，不以准备证据替代。离线通过不等于21就绪。

资产/账号事实、技术说明目前仅为准备材料；真实导入/索引未发生前不声称模型已获得。外部依赖未接入仍明确未接入。D5故障能力、所有D6异常页面分支及完整change独审不因本批正常流程通过而核销。

## P1 实际起点

2026-11-16 15:58 UTC，[实际预检](preflight-02.json)通过：五服务容器身份/镜像与发布回执一致，旧执行入口均停止；当前三个输入profile、C1 Schema、policy字节匹配；Fusion订阅alerts+raw_events且ready；业务三列表为空，本批PG/湖记录及全局running任务均0。新批26文件上传后逐项hash一致，来源connector以disabled注册并读回。实际Fusion窗口为3600秒；I/Case周期和预算未调整。

[激活绑定](activation.json)、[上传回执](upload-01.json)、[来源注册](connector-01.json)、[当前相关窗口](runtime-context-01.json)均独立保留。本地与远端两份发布/清理回执的JSON逐值相同，文件格式使字节SHA不同，见[比较](release-receipts-comparison.json)；初次预检失败[01](preflight-01.json)保留，后续预检同时校验远端原件SHA和双方内容。P1只有只读核验及本批disabled来源配置，0 Kafka、0业务POST、0模型调用。

## P2 当前通道阻断

北京时间2026-11-17凌晨，首批上下文调用[发送01](send-S01-context-01.json)及随后纯只读[恢复检查01](send-S01-context-recovery-01.json)均在SSH banner exchange超时（exit255），第三次单独连通检查也同样失败。没有取得远端执行/ACK；不能据此声称已入站或明确零发送。已同步协调模块，未重发、未发送告警、未建案，也未操作服务。见[阻断记录](transport-block-01.json)。通道恢复后先查远端out意图/ACK、生产者及湖中本批UUID，再决定是否仍需发送；当前完整链未通过。

2026-11-17恢复后，[只读恢复02](send-S01-context-recovery-02.json)证实远端无S01发送意图/ACK、无临时生产者、本批PG/湖均0，原握手失败未执行。随后[上下文12条ACK](send-S01-context-02.json)、[湖逐值读回](S01-context-readback-01.json)、[告警3条ACK](send-S01-alerts-01.json)均通过。实际事件为新UUID，见[S01范围](S01-scope.json)；A/I正在按当前调度执行，未重采样。原通道失败及阻断记录保持历史状态。

## P2 实际通过

[P2验收](P2-validation.json)：12上下文原文入湖/3告警入PG、1事件3成员；3A/1I四任务和Run均completed，17步骤52工件。4次真实模型/4原答见[S01模型索引](S01-model-io/index.json)，输入无本批身份/答案提示等禁入词；引用诊断0项不代表正文质量通过。I实际期望/分析成员均3，原OCSF/raw_text/source_scope与冻结材料一致；material身份/hash及实时enrichment以实际Fusion保存为准，不采用离线预测冒充保存结果。

[76次正式HTTP读取](S01-http-01.json)覆盖4Run全部目录、步骤和原件，逐值对照[S01快照](S01-snapshot.json)；前后23张本批相关表逐值不变，无在途。核源事件时校验器初次错取manifest字段，已按冻结wire的source_event_ids修正，见[校验器错误](P2-validation-driver-error-01.json)，未修改材料或重跑业务。按冻结计划进入P3，经正式HTTP以事件建整案、以A01建单案，分别保存201和initial_task。

## P3 两案首轮通过

[P3验收](P3-validation.json)：两次201及各自initial_task均走真实HTTP；整案3成员、单案1成员，Case/Run/Result成员一致，均冻结本批I原Run。单案可带关联事件的原范围上下文，不能据此扩大其Case成员。两轮C1–C6完成，各保存accepted/uncertain/partial；共6Run/52步/154工件，累计9次真实模型（Case5次）及9原答，[首轮模型索引](first-round-model-io/index.json)。单案C3保留4项程序质量诊断（1重复引用、3来源成员不符），不重采样、不将程序通过当正文通过。

[213次HTTP读取](first-round-http-01.json)覆盖全部目录/原件、源I及两个Result，逐值对照[first-round-snapshot](first-round-snapshot.json)通过；远端已保存first-round-gate，进入P4按原窗口追加E13/A04。

4177现场[取数核对](viewer-data-path-01.json)：21/r4代理可读2个业务Case、账本0。页面当前以测试批次为入口。负责人随后明确测试模块可以保留此方式，不大改页面；本批结束后，下一可复用交付需将本流程串联为数据包+场景配置驱动入口，不能将当前人工串联称为已自动化。

P4进展：E13/A04均首次ACK通过，E13湖原文读回通过；A04分诊完成，实际事件仍原UUID且4成员。显式I check已202并完成，新I完整分析4成员，见[S04-after-I](S04-after-I-capture-01.json)。随后整案check已[202受理](S04-case-check-01.json)，等待R2实际终结/读回；单案尚未重派。

## P4 与 P5 业务/HTTP直接验证

[P4验收](P4-validation.json)：E13/A04均首次ACK；E13原文入湖，A04同原事件且分诊完成；显式I check产生完整4成员I，整案显式check使scope_revision=2并完成R2。整案4成员/2轮、单案仍1成员/1轮，旧Run、步骤、成员、Result和工件逐值保持。R2 comparison_context与Result均指最近R1及其Result，change_kind=expanded；当前3个Result均accepted/uncertain/partial。

新key[无变化验收](no-changes-validation.json)为skipped/no_changes，无attempt/Run/模型增量。[最终PG](final-pg.json)及[最终直接报告](final-validation.json)记录10任务、9attempt、9Run、77步骤、228工件、3Results。[318次正式HTTP读取](final-http-01.json)覆盖全部9Run的77步和224工件正文、源I、Result及比较链接；另4个无run_id的Fusion入站快照在PG保存，不谎称从Run目录读取，见[范围区分](non-run-artifacts.json)。读取前后23张本批相关表逐值不变。大量只读导出/SSH的调用时限见[readback-config](readback-config.json)，未改冻结sender profile、模型/业务服务或单请求HTTP时限。

[最终模型索引](model-io/index.json)：14次真实调用、14原答、全部stop，reported tokens合计111169；无人工截断/回放注入，输入禁入词0、9Run同当前policy，费用unknown。[质量登记](quality-register.json)去重19项程序诊断（A6、C3四项、C6九项），原答不改、0质量重采样，正文未全面评估。前P3只汇总C3四项，最终登记补齐C6与A04，不能把早期局部诊断数当全批质量通过。

[实际湖查询](context-query-verification.json)核4次返回集合、时间窗和原OCSF，全部通过；未选网络查询不记已执行。13上下文全部实际入湖，但只有被实际查询的记录可称模型已取得工具结果。资产/知识仍按实际空态或未接入记录，不冒称准备文件已索引。未等自然4h/6h，不核销完整D5/D6或change结束审计。

[新账本准备](ledger-preparation.json)已按当前Document合同验证：7流程用例、16操作、19质量、9证据文件；仅准备未发布，后续出版/浏览器回执另记。根侧[本机静态核对](static-verification.json)47→49、原47条保持；测试未重复导入或回灌旧账本。

## 同包独审与4177发布

调查最终[core-02](core-final-bundle-review-02.json)12组67核对、HTTP[http-01](http-final-bundle-review-01.json)16组均通过，无业务阻断。调查初次把228总工件当作Run目录期望数的误报在[core-01](core-final-bundle-review-01.json)/draft保留，02按实际9Run ID筛224并逐集合核实；未为统计分母重复业务或补造读取。4份入站快照有独立来源接口，但本批未单独读取其HTTP正文，不扩写覆盖范围。

[首次实际发布](viewer-publish-01.json)已在21 r6原镜像完成，revision1，仅新增本批、不回灌旧账本。最初本地发布预检引用01恰逢审阅者保留原误报，被正确挡在SSH前，见[预检](viewer-publication-precheck-01.json)；绑定最终02后才第一次实际发布。

[4177实际读回02](viewer-readback-02.json)34 GET通过：唯一新批、7用例/16操作/19质量/9证据文件及内容hash逐值一致；通过4177代理读2个真实Case及R2 C6原答，与最终HTTP原件相同。初检[01](viewer-readback-01.json)误取Case列表item.id，修为当前合同item.case.id后复核通过；原失败保留，不改业务/账本。页面地址<http://127.0.0.1:4177/viewer/>，本机只SSH转发21；浏览器由根侧统一核验，测试未并行操作。

本批仍使用已冻结0.6.0测试页面；材料路径、运行part1、手动追加part的简单入口是负责人本轮确认的后续要求，尚未实施。其范围及分步入口见完整计划§9.1–9.2、数据设计§17，不把本批人工串联称为数据驱动执行器已交付。

## 4177浏览器发现与展示补证

协调方首次浏览器发现HTTP接入节点未显示真实建案/检查回执：新账本缺少页面既有`http-exchanges`证据。业务实际请求与201/202均已保存；本步仅补齐数据接线，不重发业务。当前Store禁止finished批次追加revision，[本地直接核验](display-preparation.json)实证`batch_terminal/409`，不绕过终态保护改写原02。

按[规划§8.1](../../../../openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md#81-当前4177接入证据补齐)新增`streaming-fullflow-20261116-02-viewer-02`，标题为“完整调查流程02 · 补齐HTTP接入展示（同一执行）”，provenance=saved_evidence；live仅表示仍读本轮实际业务HTTP。5条原始请求/受理回执分别关联整案首轮、单案首轮、I更新、整案R2和无变化check；最后一条run_id=null，不借用R2。当前页面matchingExchange实际验证5条匹配及跨task/Run隔离，原9份证据逐字节保持，新增[HTTP回执](viewer-display-input/http-exchanges.json)保留原件路径/hash。

[补证发布](viewer-display-publish-01.json)在原r6镜像发布新观察记录revision1；原02账本11文件及其current指针发布前后逐字节不变。[实际读回](viewer-display-readback-01.json)36次GET核7用例/16操作/19质量/10证据、原件hash、2业务Case及R2 C6原答一致。该观察记录是同一次执行的另一个展示入口，不重复计算14模型、9Run或测试次数；新增Kafka/POST/模型均0。浏览器复验由协调方完成，尚未取得最终回执时不报告页面通过。

## 本批最终交接

[浏览器复验02](viewer-browser-02.json)10项通过：单案唯一首轮、整案首/后轮分别显示真实201/202请求及各自任务，冻结范围1/3/4正确，R2→R1→R2不串轮；C6原答、具体领域、真实跳过原因、质量记录及前轮比较可查。首次[浏览器失败01](viewer-browser-01.json)保留，展示补证不是新增业务测试。

[最终交接回执](delivery-receipt.json)绑定业务、模型、同包复核、发布、HTTP和浏览器证据。原final-validation中的publication pending是生成时点的事实，保持原文件，通过本回执记录后续完成。整案3→4成员两轮、单案1成员一轮、无变化0新增Run/模型已验；累计仍14真实模型/9Run，19质量诊断后置，不认定正文质量或整个change完成。下一步按已确认§9收敛材料目录与part执行入口，先设计一个直接可验子步。
