# 当前 Case 流程实测

## 范围与直接验收

2026-11-10，项目负责人在后续顺序确认后要求“开始推进”。沿现有 3.30／3.7／3.10／3.16 执行独立批次 `case-current-flow-20261110-01`：先验证当前部署的两个 Case 首轮，再选一案核人工反馈后的再次调查。功能必需的读写接线和配置直接随功能处理；告警交接字段、已保存原答及已结束 Run 不改写。

输入复用正式库中两组明确标记的演练告警及已有 A/I 原答，分别来自 `production-multialert-20261108-01` 与 `production-multialert-20261107-01`。每组新建 Case、使用独立 operation key 和 Run；不重派历史任务，不新增原始观测、知识或确定性良恶标签。第一组检查登录、进程、外联之间的关联依据与实际补查；第二组检查未记录的事件归并依据及证据不足。旧 A/I 结果仅作历史判断，不当作独立事实或当前模型的 A/I 验收。

执行前验证部署与本地源文件／策略一致、正式身份、源材料和离线引用映射。模型调用、工具、请求容量和时限按实际加载策略；两个首轮逐案执行，结果明确结束后再推进下一轮。出现连接中断或 unknown 时先核数据库，不盲目重试。没有触发 Deep／知识检索时如实记录未覆盖。

直接验收分别记录：

- C1/C3/Deep/C6 实际可见材料、引用来源／角色／成员范围、必要前序正文及完整请求容量。
- 工具是否实际调用、成功／失败／查空及后续引用；知识指导不作为本案事实或执行授权。
- 原答、纠正、校验、装配、Result、当前判断、证据目录、报告与 GET／数据库逐值对应；交付完整性和正文质量单列。
- H 内容只陈述实际可核的材料缺口及明确范围，不虚构人员授权或调查结论；后轮核新增反馈、历史对照、采用与新鲜度。
- 本机 4177 保留历史并新增本批记录；问题登记、交接和进度同步；结束做独立审计。

本批不以保存成功认定模型正文正确，不因单后端验证勾选整个 3.7，不把手动调查结果推断为自动消费通过。页面写操作和自动流程仍按已确认的顺序另行验收。

## 证据与结果

证据目录：`docs/operations/evidence/case-current-flow-20261110-01/`。两个首轮及一案 H 后调查均已结束，均为 `completed/partial` 且最终结论未采用；原始回执保持。当前模型引用错误由现有校验如实拒收，不通过删改原答追认成功。

用户明确回复“你帮我补充”，授权助手依据实际保存的材料整理 H 内容。本轮反馈限定为“验收过程中的材料完整性核查”，显式说明由助手代拟，不冒充业务人员授权、访谈或额外采集事实。核查覆盖进程启动与命令效果、不同动作 source_ip 的角色区别、关联与因果、实际查询状态及授权缺口。具体正文、三条成员、时间窗口与十项来源见本批 `H-complete-request.json`。

H 验收通过 `production_human_probe.py` 调用当前镜像内的 `HumanTaskService.write`，复用已核对的生产 profile、现有处理账号与正常用户认证；请求和凭据经标准输入传递，凭据只短暂存于容器 tmpfs 私有文件。先创建任务，再完成为独立修订，按既有任务合同保存和 GET 读回。该脚本是服务层验收适配器，不是新的业务接口；`skip_specs: true`，不改 H/告警合同或部署，不宣称已开放 HTTP 写入。后轮仍经当前正式 Case 作业入口启动。

## 本批发现的直接修正

实际 Deep/C6 原答把 `execution_receipt` 用作结论依据，现有接收校验正确拒收，但生成 Schema 的来源枚举也包含这些程序执行回执，前后约束不一致。当前修正限定 `case_followup_output` 的可选证据编号：Deep 的支持／反证和 C6 的 conclusion/comparison/impact/recommendation 依据槽排除执行回执；C6 analysis 仍可引用查询覆盖信息。实际执行状态完整留在输入和来源映射，不能全局删除。无可用证据时仅允许空依据数组，并按原合同说明待核限制。

现有接收校验保持，不修改告警／H／数据库字段，也不改写历史原答或失败。对应规格先严格校验后实施，使用 JSON Schema 与原解析器的配对检查验证，并经统一发布入口部署。此修正不代表事实扩大、C3 成员范围或 C6 发现关联问题已解决。构建目录保留未激活候选，实际生效来源以本报告的激活回执为准。

## 实际调查与质量结论

所有模型调用均发生在发布 `v1.2-20261110-r2`，逐次请求及模型路由由 [run-config.json](../../../docs/operations/evidence/case-current-flow-20261110-01/run-config.json)和保存工件固定。后续部署修正没有重派这些 Run，也没有改写实际执行来源。

| 样本 | Case / Run | 模型调用 | reported tokens | 整轮耗时 |
| --- | --- | --- | --- | --- |
| C01 首轮 | `17fef155-8dc3-532b-891a-b3d362c58fc1` / `6fc71a3d-288a-4a19-a5bb-c70f2c044eb5` | C3、Deep、C6，共 3 次 | 46,862 | 164.465404 秒 |
| C02 首轮 | `f77924b6-be9c-5754-a96e-690db0f904b3` / `a2ffe2df-b311-44e8-a8c5-a6b12bca78d8` | C3、C6，共 2 次；没有触发 Deep | 33,657 | 156.580205 秒 |
| C01 H 后 | 同 C01 / `c0d94909-f0fe-4dbe-9cef-167881c2bb5d` | C3、Deep、C6，共 3 次 | 73,972 | 165.368113 秒 |

合计 8 次、154,491 reported tokens；费用为 unknown/unpriced，不能记零。三轮均保存为 `completed/partial`，`stop_reason=partial_analysis_saved_conclusion_rejected`，最终结论拒收；两案 `current_assessment_id=NULL`。相应 Result 分别为 `c8536bbc-edd9-4bb5-b2c7-ae81ec6abde6`、`086218be-740c-4521-8752-49fb738696d8`、`3b6f9eff-5c8c-4a9a-84de-02ffa76e0e73`。后轮明确比较 C01 首轮 Result，不能把比较对象当作已采用判断。[逐轮统计与工件定位](../../../docs/operations/evidence/case-current-flow-20261110-01/execution-summary.json)

C3 三次都有 `source_member_mismatch`，保留独立有效部分。Deep 两次因 `execution_receipt_is_not_evidence` 拒收。C6 三次分别出现 `invalid_conflict_findings`、`unknown_domain_finding`、`execution_receipt_not_conclusion_evidence`。本批已修正生成 Schema 与接收校验间可确定的执行回执约束差异，成员范围和发现关联没有通过降低校验或伪造引用解决。

正文仍有明确问题：把 `process_start` 成功扩大为 PowerShell 命令完成／用户枚举效果；把登录来源 IP 与外联本机源 IP 的不同角色解释成异常 IP 切换或横向移动；把未执行的资产／历史查询写成查空；把认证活动查询描述为能核实业务授权。H 已指出这些限制，但后轮仍重复部分问题。材料是演练观察，没有独立良恶真值，不报准确率；模型质量为 **NOT_PASSED**。

工具实际状态单列：三轮 threat_intel／ueba 完成且返回 0；两个首轮的 authentication_activity 查询完成且返回 0。assets／history／knowledge 因 `tool_budget_reserved_for_evidence` 跳过，graph 为 `source_not_connected`。没有知识查询或实际使用的正向验收结论，也不因查空认定行为安全。

## 流程与模型问题归因

按用户要求，对本批保存的请求、原答、来源映射和当前校验代码逐项复核。下表区分直接原因与流程放大因素，不按拒收代码的数量统计模型错误；同一 finding 被剔除后，依赖它的领域及冲突引用也会被拒收。此处是已有证据分析，没有新增模型调用或修改原答，不能证明修正后的真实生成效果。

| 现象 | 归因 | 证据及处理方向 |
| --- | --- | --- |
| Deep／C6 可生成执行回执引用，但接收校验禁止其作为结论依据 | 已确认的生成／接收合同不一致，属于流程实现问题；正文把查空当证据另算 | 已修正生成 Schema，查询状态仍留在输入。边界及离线验证通过，真实生成待核；见本报告直接修正部分 |
| C02 的 A1 成员引用 A3 查询返回的 A1 历史记录，被报 `source_member_mismatch` | 已确认的来源归属表达偏差，不能全部归为模型错误 | 保存映射把 `N3_S119/N3_S120/N3_S122` 归到 A3；原始记录的 `record.id`／`triage.alert_id` 却是 A1。查询发起成员与返回行主体需要分别表达、核验；保留查询出处，不按标题猜主体，也不把所有返回行扩为全案证据 |
| C01 跨 A1/A3 比较 IP，却只声明 A3；反馈后同类 finding／followup 重复此问题 | 模型输出范围错误，现有拒收正确 | 原答 F2 同时引两条成员的原始 IP，`alert_ids=[A3]`；应声明实际比较范围。即使范围改正，不同动作的两个 IP 也不能自动证明 IP 切换或横向移动 |
| C6 的 findings 已无 F3，领域／冲突仍引用 F3，或把问题编号 `authorization` 填入 finding_ids | 模型关联输出错误；流程的编号约定和纠正覆盖需要改进 | C01 首轮 C6 只有 F1；C02 C6 只有 F1/F2。当前生成 Schema 的 finding_ids 仍是文本引用，最终接收才检查同一 analysis 内关系；不能补造发现使其通过 |
| 成员错配、悬空 finding 等可定位错误没有针对性纠正 | 流程恢复能力缺口 | 当前只有“已回答／已分析但依据列表为空”会生成一次纠正反馈；其他上述错误走部分保留／拒收。已有一次纠正执行机制不能表述为所有引用错误都已覆盖 |
| assets／history／knowledge 未查，graph 未接通 | 调度策略及接入覆盖问题，不是模型没有学会使用这些结果 | 本批每 Run 最多 4 次工具调用，C2 预留 2 次给后续；固定排序先执行 threat_intel、ueba，另外三项因预留跳过。需要按问题所需证据核优先级及实际可用工具，不以单纯扩大预算代替设计；图接入单列 |
| 用 authentication_activity 查询业务审批／白名单 | 模型选择工具与理解能力错误；流程仍可加强目标与能力的匹配 | C01 首轮请求里的工具说明明确“不提供审批记录，需要审批证据时交人工确认”，模型仍把审批目标绑定 B1。程序只能执行实际认证查询，零行不能回答业务授权是否存在 |
| 进程启动扩大为命令效果、不同角色 IP 被解释成异常切换、未查写成查空、查空或缺授权材料被填作反证／冲突 | 模型证据推理和指令遵循问题 | 保存的系统提示已明确这些边界。C02 原答一边写“查空不构成反证”，一边将相关回执放入 counter_ids，并把“无直接矛盾”写入 conflicts；不是必须填冲突的合同要求。H 后仍重复部分事实扩大，提示词可见性通过不等于正确使用 |

C02 归属偏差的原件在 [C02 数据快照](../../../docs/operations/evidence/case-current-flow-20261110-01/published/C02/database.json)：C3 请求工件 `390faabb-07b4-4e4a-82d7-fbc5b873a515`，原答工件 `9d874568-5bf6-4b0f-b3d8-4b2b1b903446`。A1 为 `51382dcd-deac-54f5-9fa5-e7724f935402`，A3 为 `f8513c4d-5f58-55d2-bda1-983f60b83bb0`。上述三项来源在冻结工件 `19ef57c8-46b6-4e71-838b-9fe941124ce3` 的 `$.alerts.<A3 UUID>.queries.2.content_json.rows` 下，返回记录实际指向 A1。当前 [source_members](../../../services/api/app/socai2/model_input_view.py) 按 `$.alerts.<id>` 容器取成员，接收端 [refs](../../../services/api/app/socai2/baseline_analysis_contract.py) 按该成员集合拒收；冻结来源本身没有丢失。

C01 的具体原答及工具说明在 [C01 数据快照](../../../docs/operations/evidence/case-current-flow-20261110-01/published/C01/database.json)。纠正边界见 [empty_reference_feedback](../../../services/api/app/socai2/analysis_review.py) 和 [ModelSteps.call](../../../services/api/app/socai2/baseline_reasoning.py)；工具预留与排序见 [C2 执行](../../../services/api/app/socai2/baseline_enrichment.py)和[来源选择](../../../services/api/app/socai2/baseline_enrichment_sources.py)。

证据缺少真实业务授权、进程完成结果或因果链时，保持待核是合理结果，不以强制输出良性／恶意来验收。H 是材料完整性核查，没有补入新的业务授权事实；它已完整传递，当前问题是模型未正确利用其中的限制。现有结构／引用校验也不证明正文真实，部分保留内容进入后续时仍只能作为历史判断。

后续先修来源归属表达并对齐生成／接收约束，再完善有限纠正与取证优先级，随后以独立批次验收正文是否仍扩大事实。编号关联复杂度、历史分析重复、输入长度可能影响生成，但本批没有受控对照，不能据此断言是上下文长度或模型型号导致。上述记录不改变告警交接字段或数据库设计，也不核销 M01／M02／F01／F02。

## H 保存、传递与新鲜度

任务 `77f645bf-a6a4-56fc-aa54-1c1f968bb37b`：创建为修订 1，完成为修订 2，随后只修改负责人／期限为修订 3。范围包含 3 个告警、明确时间窗口及 10 个来源（3 项观察材料、7 项查询执行回执）。核查正文保持来源角色，不把执行回执升级成行为证明。

完成修订 `3a88fefd-a3af-4bc9-8bad-9fdf03ef384c` 的正文完整进入后轮 C3、Deep、C6，分别映射为 `human_statement` 来源；映射依托 C1 输入工件中的冻结反馈路径，并非虚构新的 `task_revision` 来源类型。修订 3 保持正文、范围、来源、完成人和完成时刻；首轮新鲜度为 `stale/human_feedback_changed`，后轮保持 `current`，没有把管理字段变化算作新证据。[修订检查](../../../docs/operations/evidence/case-current-flow-20261110-01/H-metadata-check.json)

H 服务写入、三版不可变保存和五项详情／修订 GET 逐值核对通过。该结论限定传递与保存；模型正确利用、业务人员确认和前端写操作没有因此完成。

## 修正验证及数据库对应

- 模型边界 20 项测试通过，包含执行回执唯一来源／混合来源、Deep 和 C6 四个受限槽、C6 analysis 保留查询覆盖引用的配对 Schema／解析检查。
- 处理及统一发布 26 项测试通过；Ruff、OpenSpec strict 均通过。5 份保存的 Deep/C6 原答离线复验确认受影响引用被修正后的生成 Schema 拒绝；这不是新的真实生成或质量验收。
- 核验器支持空当前判断并拒绝伪造判断，补齐 H 全字段核对；Case 及活动集合从同一只读快照的同租户主体关系取值，不假定只有一个 Case。
- `readback-01` 因核验器未处理空判断中止；`readback-02` 的 365 个 HTTP 状态均符合预期，但有 42 个跨 Case 对账误判。原回执保留，不能称首轮全过。修正后的 `readback-03` 为 365 GET、357 个 200、8 个预期 404，**16,820 项检查零失败**，读取前后快照一致。
- 独立活动检查覆盖 25 条活动、52 个匹配目标，另有 **1,083 项通过**，不混入上述检查数。
- 两组来源原有 199＋167 行没有变更或丢失；ORM、机器字典、JSON 合同及 V1 建表原件与已发布基准一致。本批无 DDL／GRANT，无告警交接字段变化。正常验收身份的临时 API key 使用既有 scopes，有效期一天，凭据仅存私密文件。

[初验](../../../docs/operations/evidence/case-current-flow-20261110-01/local-validation.json) · [最终核验脚本及完整离线重放](../../../docs/operations/evidence/case-current-flow-20261110-01/final-validation.json) · [原答离线复验](../../../docs/operations/evidence/case-current-flow-20261110-01/wire-repair-check.json) · [最终读回](../../../docs/operations/evidence/case-current-flow-20261110-01/readback-03/summary.json) · [独立活动检查](../../../docs/operations/evidence/case-current-flow-20261110-01/independent-activities.json) · [来源保持](../../../docs/operations/evidence/case-current-flow-20261110-01/source-preservation.json)

## 21 与 4177 交付

已激活 `v1.2-20261110-r4`，处理组件 `processing-20261110-r4`，处理镜像 `sha256:c68c72a9cfe6fa04f6963582d65ce49d73cbf5355c0d72dcf1905d3ecb84776c`。统一 manifest 为 `907207f5972c8f20344088ebffbdf01e23425ac309cff9ae9d85b36b5ebf8787`；策略 hash `ea886f6aba7858d7a894efb2659d78d11299e2e30ca40956fcbd80ef0b2f2130` 保持。API、工作台更新，其他继承服务容器身份保持，6 服务健康；实际 A/I/Case profile 核验通过。[激活回执](../../../docs/operations/evidence/case-current-flow-20261110-01/unified-activate-20261110T104633458561Z.json)

Case HTTP 写开关仍关闭，自动消费者暂停，迁移关闭。模型单次 300 秒、Case 1500 秒、C6 预留 300 秒及实际单 Run 上限保持；本批没有通过放大预算追认质量。

4177 从本批最终读回追加两个 Case 的原件和页面：本机保留 49 份记录，21 保留 18 份。静态发布核对 199 个文件和 200 次 HTTP 读取，原有记录／文件及容器保持；三轮均显示部分交付和拒收，不把工件存在当作质量成功。[静态发布回执](../../../docs/operations/evidence/case-current-flow-20261110-01/workbench-publication.json)

## 结束边界与后续

本批完成真实流程执行、H 传递、直接缺陷修正、部署、数据库／字段读回及交接更新。独立结束审计为限定实现与交接 ACCEPT、0 项必须修正，模型质量 NOT_PASSED；[审计回执](../../../docs/operations/evidence/case-current-flow-20261110-01/independent-audit.json)保留边界。源码、文档与证据已推送 `origin/V1.1`，父项目 `add-server-submoudle` 仅更新 `server` 引用，非强推且未修改本机父项目工作树。[发布回执](../../../docs/operations/evidence/case-current-flow-20261110-01/publication-initial.json)固定代码交付提交；收尾记录随后同步同一分支及父项目。3.7、3.23、3.30 的整体质量范围未完成，不归档 change。

下一步先处理 C3 成员范围、C6 发现关联和正文事实扩大，用独立批次核真实效果；另取适用样本核知识实际查询与使用。页面写操作及 P01–P04、自动流程按既定顺序推进，权限设计不作为独立前置。[当前问题](../../../docs/investigation/current-issues.md)保留各项验收落点。
