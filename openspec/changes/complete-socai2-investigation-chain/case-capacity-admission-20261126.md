# Case 首轮容量阻断：计量候选与最小验证方案

本步骤并入 [Case 列表迁移第二步](case-list-migration-20261126.md)的容量阻断处理及[调查数据规格](specs/socai2-investigation-data/spec.md)。本地候选、离线证明与回执是本轮出口；发布和同案新的独立调查操作由统筹核候选后另行安排。

## 原始事实与原因

批次 `case-create-readback-20261126-01` 只有一笔正常页面创建，Case 的6个成员、1个显式事件及 initial_task/Run 关系已保存。首轮为 `failed / partial`，停止码 `capacity_exceeded`；C3、C6 均保存 `not_sent / model_context_capacity_exceeded`，没有生成请求或模型原答。系统 Result 的 `system_only / uncertain` 不代表模型调查成功，原失败及当前指针保持。

| 阶段 | 原聊天模板计数 | 独立封装计数 | 安全量 | 输出预约 | 原窗口需求 | 聊天＋安全量＋输出 | 窗口 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C3 | 46072 | 18661 | 1024 | 16384 | 82141 | 63480 | 65536 |
| C6 | 45938 | 52436 | 1024 | 16384 | 115782 | 63346 | 65536 |

总 Run token 额度并未耗尽。原准入仅对 I 的限定 `structural_tag` 请求排除服务端约束封装；本笔 C3/C6 使用同一显式 `chat_completions / vllm_grammar_v1` 能力、纯文本聊天和严格 `json_schema`，却把完整封装额外计入窗口。因此当前确定的阻断是准入口径，不需要删除成员、事实或手工压缩样本来解除。这里没有审阅业务正文的语义，也不据此声明输入已无冗余。

vLLM 的[固定版本协议源码说明](https://docs.vllm.ai/en/v0.15.1/api/vllm/entrypoints/openai/chat_completion/protocol/)将 `json_schema` 与 `structural_tag` 都转换成结构化输出采样参数；[官方结构化输出说明](https://github.com/vllm-project/vllm/blob/main/docs/features/structured_outputs.md)将其定义为生成约束。该资料解释协议分工，不冒称本轮新核了服务端软件版本。本笔冻结配置与此前已核能力一致；本轮只复用冻结请求/后端原计数，新增模型、tokenizer 和业务查询调用均为0。

## 范围、效果与依赖

生产候选只改 `services/api/app/socai2/token_budget.py`：根据显式协议、Schema能力和已识别纯文本请求结构决定窗口口径，移除 I 阶段特判，同时识别严格 `json_schema` 与既有 `structural_tag`。不改模型路由、容量、输出预约、累计预算、时间/次数限制、请求正文、输出Schema或保存合同。

未知格式、未声明能力、额外工具/模板/多模态字段继续保守计算。独立封装计数及完整wire累计预约原样保留；不能用窗口放行绕过总额度检查。后台 tokenizer 的实际窗口校验及输出预留检查保持。

预期效果仅是：相同已确认协议的有效请求能够继续后续预算检查；真正超出聊天＋输出窗口或总预算的请求仍被拒绝。本地候选不代表新模型生成、正文质量或整个 Case 流程已通过。

## 单步实施与直接验证

1. 保存本轮前源码，保持共享工作区已有 I 修复；先运行 OpenSpec strict。
2. 只修改准入识别和直接受影响的 `test_socai2_token_budget.py`。复用既有 token 计量和执行合同测试，验证两种格式、阶段无关、真实窗口边界、未知结构回落及总预约不减记；不加通用验证框架。
3. 从私密落库快照读取本笔 C3/C6 完整请求、冻结模型配置和原后端计数，用本地替身回放计数。逐项核候选窗口需求、原请求/Schema/消息哈希、完整预约、原数据库快照及原失败不变，0网络/模型调用。公开只给工程计数、布尔和哈希。
4. 保存精确增量补丁、源码指纹、检查结果、未验边界和待发布范围，交统筹独立审阅。只在候选明确后由统筹安排发布及新操作，不重复原 initial_task。

## 待发布范围与风险

若候选获准，业务代码只需更新当前唯一调查调度使用的 `app/socai2/token_budget.py`，并按原配置切换该调度进程使模块重新加载；不需要更新HTTP业务服务、模型服务、数据库迁移或运行预算。具体加载路径和空闲切换回执在发布前核实，本轮不执行发布。

本方法依赖显式 `vllm_grammar_v1` 所声明的服务端约束语义；未知配置保持保守。新真实调用仍可能出现输出、结构约束编译、时间或正文问题，必须按实际回执判断；本次离线准入通过不能核销这些边界。

## 本地候选交接结果

本地候选及限定独审已完成，正式21未更新，未产生新调查操作、模型或tokenizer网络调用。

- 直接检查34项通过，Ruff与限定diff检查通过。保留原有I上下文/持久化合同检查，确认未知格式、工具、模板和多模态回落；真实超限及更小累计预算仍拒绝。
- 原快照C3/C6离线对照通过：窗口需求为63480/63346，完整wire累计预约仍为82141/115782；消息、Schema和完整body哈希不变，原失败快照不变。来源、原计数及对照见[离线回执](../../../docs/operations/evidence/case-create-readback-20261126-01/core-capacity-offline-replay.json)。
- 统筹独立核唯一生产函数差异、原body与计数及检查XML，7项通过；[独立回执](../../../docs/operations/evidence/case-create-readback-20261126-01/coordinator-capacity-candidate-review.json)。这仅结束本地候选验收，不代表真实调查或正文质量通过。
- 4177正常接口的8次GET核对同一失败Run、13步、35个同Run工件及系统Result一致；私密审计记录由74增至75，旧批次保留。[4177回执](../../../docs/operations/evidence/case-create-readback-20261126-01/core-4177-readback.json)与[首轮保存回执](../../../docs/operations/evidence/case-create-readback-20261126-01/core-run-readback.json)分别记录读取通过与业务执行失败。

生产文件前后哈希、精确增量补丁、命令、现行profile适用关系、协议来源和待发布进程见[候选交接](../../../docs/operations/evidence/case-create-readback-20261126-01/core-capacity-candidate.json)。后续仅由统筹按可审阅候选安排正式更新，再决定同Case的新独立操作；原initial_task及失败不重派、不核销。主任务清单保留真实首轮未成功的边界。

## 2026-11-27 解决方案：先解除已证实的误拦，再验同案真实调查

负责人要求说明为何少量告警触发容量停止，以及如何解决。本次只补方案和工作台配套展示，不发布21、不派发任务、不新增模型或tokenizer调用，不扩大测试。现有候选和原失败保持。本段不新增测量值；该笔分项计数、余量及原请求身份保存在 `.local/validation/case-failure-workbench-20261127-01/` 的配套报告。

### 告警条数、单次窗口与整轮预算

告警条数不等于token容量。`chat_tokens` 是最终 `messages` 经后端聊天模板后的合计，包含阶段提示和筛选后的业务材料；材料长度、对象与证据量、必要前序分析都会影响它。现有计数没有把消息内部各类材料分别计量，不能把聊天合计都称为“告警原文大小”，也不编造分摊。

| 项目 | 作用及本笔处理 |
| --- | --- |
| messages与聊天模板 | 使用原后端计数，属于实际窗口输入；没有删除本案成员或事实。 |
| 输出Schema及非消息封装 | 本笔已声明的服务端grammar约束，不作为提示文本加入窗口；完整wire预约仍保留其计数。未知能力或形状保持保守。 |
| 输出预留 | 从当前阶段配置读取，在调用前计入窗口需求，不能假定最终答案会很短。 |
| 安全量 | 沿原tokenizer配置保留，不为通过准入而扣减。 |
| 整Run预算 | 累计各次调用的实际usage或既有预约，并保留C6额度；与单请求窗口分别检查，不能用总额度替代窗口限制。 |

对本笔支持的请求形状，窗口判据是“聊天模板计数＋阶段输出预留＋安全量”；完整wire预约仍为上述项目加非消息封装。对应代码为 [token_budget.py](../../../services/api/app/socai2/token_budget.py) 的 `context_admission` / `BackendTokenMeter.measure` 和 [baseline_analysis.py](../../../services/api/app/socai2/baseline_analysis.py) 的 `budget_reason`。

原计量会把本笔C3、C6判为窗口超限；修正口径后，两份**原封存请求**都在窗口内，总预算检查也通过。正余量足以使这两份请求通过准入，但余量有限，不是后续扩员的容量保证。尤其原C6来自C3未发送的失败轮：新轮若取得有效C3或Deep结果，C6输入会变化，必须对新请求重新执行现有计量。不能用旧失败轮C6的离线通过代替新轮完整流程验收。[baseline_capacity.py](../../../services/api/app/socai2/baseline_capacity.py) 已区分最小最终阶段预约与最终请求的实际窗口/剩余额度检查。

### 已完成与尚未执行

| 项目 | 当前状态及直接证据 |
| --- | --- |
| 通用协议能力计量修正 | 已完成。唯一生产候选为 `services/api/app/socai2/token_budget.py`；同请求、同Schema、同配置和同预算验证通过。 |
| 直接检查、原请求离线复算、独立审查 | 已完成，复用既有34项检查和双阶段原输入复算。本次不重跑或扩大检查。 |
| 输入或运行配置变更 | 本笔解除误拦没有证据要求这些变更，不附带修改。输入业务相关性、正文质量和更大规模能力并未因此得到证明。 |
| 21实际加载 | 尚未执行候选发布。前轮只读前检确认目标仍为前像、唯一调度及原profile一致；这不是持续有效的空闲证明。 |
| 同案新调查及采用/页面读回 | 尚未执行。须在发布加载核对后，使用新的独立operation验一次正常流程；旧initial失败保持。 |
| 4177查阅 | 同Run原始错误、步骤、容量回执和系统结果可读。本机静态审计配套说明独立保存事后原因；不能宣称它已自动挂入经SSH转发的21 viewer。[展示回执](../../../docs/operations/evidence/case-failure-workbench-20261127-01/core-display-receipt.json) |

### 最小发布和一笔新调查的顺序

1. **核对待发布内容与切换条件。** 复用已审源码/精确增量，实施前做本change严格校验；不从共享脏工作区打包其他改动。切换时重新核唯一调度、实际模块文件与前像指纹、挂载影响、原命令/image/profile及运行和待处理任务。确认空闲才能进入下一步。原目标与恢复路径见 `.local/validation/case-story-capacity-live-20261126-01/core-release-prep/release-rollback-plan-private.json`。
2. **只使这一文件生效。** 保存实际目标文件及权限元数据，在原加载位置安装已审候选，按原profile重载现有唯一调度。核对实际解释器解析到的模块路径、加载文件候选指纹、唯一运行实例及原配置指纹；文件已复制但原进程仍缓存旧模块，不计生效。HTTP服务、模型服务、数据库及运行预算不随此步更新。
3. **提交同Case的新独立操作。** 复用正式Case重新调查入口 `POST /api/v1/socai2/cases/{case_id}/investigations`，请求按既有合同传新 `operation_key` 和 `mode="rerun"`，核心任务对应人工 `intent=rerun`，只提交一次；不是重派原initial任务。[路由](../../../services/api/investigation_http/external_routes/analysis_submissions.py)与[请求合同](../../../services/api/investigation_http/analysis_submission_contracts.py)均不改变。这里只改计量代码，`analysis_case_executor.capacity_profile()` 未必变化，普通 `check` 对相同已停止材料可被 `automatic_attempts_stopped` 合法跳过，因此不以反复换key的check试出一个Run。先核同案当前范围、原失败与无活动执行；受理响应未知时先读原operation/任务，不盲目重复提交，不修改自动停止台账。
4. **走通实际调用与保存。** 记录新的task/attempt/Run关系；对实际C3、Deep（如果发生）和C6请求逐步采用现有窗口、总预算、次数及时限门槛。保留实际发送状态、模型原答、校验、有效片段、组装、Result和收尾。最小通过标准是确有模型请求/返回，新Run正常收尾，保存真实模型Result，且来源、冻结成员、交付完整性与校验状态可回查；系统说明或仅HTTP成功不算通过。
5. **核采用及两处页面。** 沿现有保存/采用规则核 `cases.current_assessment_id → case_assessment_sources → results.source_run_id`，确认指向同一新轮的合格结果；不强制覆盖人工判断，不因产生Result就声称已采用。若规则拒绝，保留具体拒绝原因。用正式HTTP、8181和4177读回同一新轮身份、原文及状态，刷新/切回旧轮时旧失败仍可读；按既有导出更新流程追加本轮材料。只核本次流程，不扩到全仓、全表或多模型矩阵。

上述步骤的完成状态依次确认，不能用计划替代回执，也不能边验证一个步骤边铺开其他独立问题。发布和这笔新调查等待统筹执行信号；本次方案不触发它们。

一次操作的验收目标是一笔实际新Run，还须读回真实attempt/Run数量。`CaseTaskExecutor.execute` 对正常返回的失败不设 `retryable`，但[既有调度错误分类](../../../services/api/app/socai2/analysis_dispatch_types.py)会将部分已知未执行的临时连接失败标为可重试，[任务收尾](../../../services/api/app/socai2/analysis_task_store.py)依当前策略决定是否安排下一attempt。因此“一次提交”不能保证任何故障下都只有一次attempt；本次不改重试配置。若实际产生额外attempt/Run，按原关联如实记录，停止新增人工操作并交统筹判断，不能将多轮写成单Run通过，也不能为凑数量改台账或强停活动执行。

### 不通过时如何保留和处理

- 加载或健康核对失败：不派新调查；在无活动任务时恢复备份前像，按原profile恢复同一调度，读回前指纹和实际状态。保留失败发布回执，不把复制文件等同上线。
- 新请求按修正口径仍真正超限：保留本轮 `not_sent`、分项计量和范围，停在该阶段具体阻断；不删成员、不截断原文、不抬预算，也不再自动派新operation。
- 已产生独立有效结果而后续失败：按既有局部结果保存规则保留原答、有效片段、失败/unknown及部分交付，不补造完整结论或覆盖旧记录。传输或受理结果未知时先查真实状态，不盲目重发；不得在活动Run中途为恢复代码而强停执行。
- 模型正文质量与程序流程分别判定；已有后置项继续留档，新的真实失败按实际范围说明，不用一次准入通过宣称模型质量或整个change完成。

### 成员更多时的后续条件

仅在后续实际请求出现正确计量下的容量阻断，或有明确输入相关性问题证据时，再开启一个边界明确的输入整理步骤。沿既有 [baseline_model_view.py](../../../services/api/app/socai2/baseline_model_view.py)、[case_c3_input_selection.py](../../../services/api/app/socai2/case_c3_input_selection.py)、[case_followup_input.py](../../../services/api/app/socai2/case_followup_input.py) 和 [case_input_hierarchy.py](../../../services/api/app/socai2/case_input_hierarchy.py) 按C3/Deep/C6职责检查字段用途和来源。

先在本地按结构定位哪类提示、业务视图、前序结论或查询结果增长；随后仅移除已识别的后台元数据和无用重复表达，按环节筛选必要证据并保持引用/冻结映射。保留原件、有效未知字段、`0`、`false`及有意义的空列表，不按特定告警值删字段，不做语义改写或手工压缩测试样本。若全部必要材料仍无法进入单次窗口，再按既有阶段职责设计有证据的分步输入；不在本轮新增通用分片/摘要框架，也不简单增大预算或承诺支持某个固定告警条数。任何后续改变都需在本change写明业务效果，直接核输入→处理→保存→读取与跨成员来源边界。

## 本轮授权发布与同案新调查回执（2026-11-27）

负责人随后明确授权“让调查核心执行模块重试一下，可以发布”，统筹确认执行上述最小分阶段方案。此授权取代本页前段方案整理时的未发布边界；不包含其他共享工作区改动或viewer修改。

- **最小发布已核对生效。** 发布前strict通过，实时前检确认唯一原调度、原前像、原配置及无在途/待处理任务。仅安装已独审 `token_budget.py`，候选SHA-256为 `5abaf30f6fcf656996a2cbe8b4526e0c0f60a9b7ba59a264ce99bed831190e5f`；备份原文件及权限元数据，按原profile重载同一容器。新进程启动晚于安装，实际模块与导入函数源码匹配候选，运行配置和四份profile指纹不变，重载后仍空闲。HTTP、模型和数据库未重启。[发布结构回执](../../../docs/operations/evidence/case-capacity-live-retry-20261127-01/core-release-receipt.json)。
- **同案一笔新调查已结束，整体部分交付。** 新operation先保存于 `.local/validation/case-capacity-live-retry-20261127-01/case-binding.json`，正式HTTP只提交一次 `mode=rerun`，受理身份与PG一致；实际为1个新task、1次attempt、1个新Run，task/Run均completed，attempt已ended。C3及C6各有实际请求和原答，C4补查及C5关系处理完成，没有额外人工操作或自动重试。模型Result已保存，validation为accepted，并沿既有规则成为当前采用来源。冻结成员/材料及静态Run预算保持，原失败Run整行、原initial任务与attempt关系未改写。[执行与PG读回](../../../docs/operations/evidence/case-capacity-live-retry-20261127-01/core-run-readback.json)。
- **完整性与质量分别记录。** C3/C6原答均为完整JSON、未截断，stage delivery均complete，无missing/invalid units，保存原件哈希及保留单元原文span核对通过；Run/Result仍为partial。发布层保留输入省略、背景/图范围、成员与问题未决及领域待定等限制，完整限制在私有原件中。C6引用检查记录 `empty_sources`、`delivery_source_coverage_missing`，正文质量仍为 `not_checked`。这次已验证本笔输入可进入C3及包含新分析结果的实际C6，并走到保存/采用；不据此宣称完整交付、正文质量或整个change通过，不新增采样来核销这些问题。
- **4177读回与历史保留。** 按既有 `update_processing_audit.py` 追加本轮快照，保留此前75条记录与原页面；导出含同Case的旧Run历史，实际新增执行数只按本批binding核对。4177完整步骤/工件目录、实际请求、交付回执、C3输入及分析输出、Result与PG快照一致。[工作台读回](../../../docs/operations/evidence/case-capacity-live-retry-20261127-01/core-workbench-readback.json)。正式导航及本机配套回执保存在本批 `.local`；8181页面与独立结束核对由统筹另记，不以HTTP内容可读代替页面渲染验收。
- **展示问题单列。** 原C3步骤已有输入与程序输出工件；输入含messages，模型analysis为空，另有not_sent容量回执。4177整块空白需要沿读回/展示定位，不把“程序阶段完成”当作模型成功，不附带viewer发布。

统筹随后完成本步独立结束核对：实际模块加载的8项检查、同案HTTP/只读PG的24项检查及普通8181/4177的17项检查均通过。新判断与已存Result、原位依据/未决和精确原轮一致；4177实际C3输入、分析输出及模型原答可打开，原失败仍可读。页面回执不改变上述partial及正文未检查的边界，不改viewer，也不新增调查。[本步独验汇总](../../../docs/operations/evidence/case-capacity-live-retry-20261127-01/README.md)
