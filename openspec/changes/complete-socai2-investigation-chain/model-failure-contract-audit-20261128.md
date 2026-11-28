# 模型异常路径源码审计与最小后续设计

日期：2026-11-28。归属当前 `complete-socai2-investigation-chain` change。§1–7 保留实施前的源码审计和设计基准；S1、S2 分别按统筹独审通过的窄步在本地实施，结果见 §8、§10。未重放业务或真实模型调用，未调整提示词、输出 Schema、预算上限或运行配置。

## 1. 结论与证据边界

当前已经接通闭合单元接收、部分内容保留和 C3 一次缺项补充。A/I/Deep/C6 没有新增自动续写，符合旧设计的明确范围。真正需要先修的是调用边界：已知未发送、已收到但信封无效、已发送结果未知，部分路径没有得到准确且完整的阶段回执。

本审计以本批冻结的 candidate 源码为核心执行基准，对照实施前工作区。当时所列执行 Python 源码与该冻结副本一致；`incident-input-v1.json` 已存在工作区差异，不能将工作区的提示/配置变化追认为本批已加载。S1 后的源码增量另列，不覆盖此前指纹。HTTP 与页面部分只核对源码和本地替身，不冒充实际页面读回或部署版本验收。

- [源码 SHA-256 与比较范围](../../../docs/operations/evidence/model-failure-contract-audit-20261128-01/source-hashes.json)记录执行代码、读取端代码及测试入口。路径以仓库根为准。
- [既有测试入口](../../../docs/operations/evidence/model-failure-contract-audit-20261128-01/test-entrypoints.json)仅定位，不表示本轮重新运行通过。
- [此前 I 接收合同审计](../../../docs/operations/evidence/incident-receive-contract-audit-20261128-01/README.md)仍适用；本文不读取其关联业务回执。
- 只使用源码、结构和纯设计段落；不包含实际输入、模型正文、业务身份、运行配置值、输入大小或数据派生验收值。实际业务与模型质量结论不由本报告推定。

## 2. S1 实施前各阶段实际接线

以下源码路径均相对 `services/api/app/socai2/`，行号对应上述冻结副本和本次对照工作区。

| 阶段 | 输入超限/发送前检查 | 已收到正文后的处理 | 额外调用与下游使用 |
| --- | --- | --- | --- |
| A 告警分诊 | 输入构建、计量及 `budget_reason`；失败不生成新的模型调用。预算拒绝路径没有保存完整模型请求，不能把没有请求工件当作未检查。 | `ai_delivery_store.receive_payload` → `ai_stage_delivery.receive`；接受 `stop/length`，保留闭合且有效的单元。核心字段齐备才形成结果；缺建议可保留核心，但交付回执明确缺项。 | 请求 `correction=None`，响应 `correction_feedback=None`；没有输出自动重试/续写。模型步骤、结果、交付完整性分别保存。 |
| I 事件诊断 | 同样先构建/计量/预算检查；预算拒绝会保存带 `preflight_error/preflight_passed` 的未发送请求，挂在阶段上。 | 接收诊断、成员、发现等独立单元。结果硬条件仍是诊断四字段 `summary/conclusion/source_ids/limitations` 齐备，且有效成员身份覆盖冻结成员集合。局部发现可保留，但不能代替完整核心结果。 | 与 A 一样不补写；`stage_core_conclusion_unavailable` 是接收后的聚合失败原因，不足以证明具体哪一字段失败。成员缺失、无效与重复必须查看对应结构诊断。 |
| C3 初步分析 | 业务视图与完整请求均有检查，之后调用共享 `ModelSteps.call`。准备大小/上下文容量失败的特定路径保存 `capacity_preflight`，不是模型原答。 | `case_c3_delivery` 接收闭合单元，保留原文跨度、来源、独立有效项及缺项；计划缺依赖时保留内容但不派工具。 | `allow_correction=False`；走 `complete_sections`，按冻结策略最多一次、可禁用的缺项补充。同 Run、同预算，不覆盖已保留项。运输无回复、未进入接收器、未知调用或预算不够时不补；已收到且通过协议检查的空白正文仍可能按缺项补一次。 |
| Deep 问题分析 | 共享预算与 C6 预留；缺少必需前序/输入时不调用。 | 独立 `answer` 即使控制字段不完整仍可保存；只有完整、合法且引用冻结 binding 的 `query` 决策才能派查询。 | `baseline_deep.py` 没有向 `ModelSteps.call` 传 `review`，通用纠正分支不会启用。查询后再次分析是业务查询循环，不能称为截断自动续写。失败停止本问题，已有答复进入后续材料。 |
| C6 最终交付 | 共享预算、实际完整请求计量及最终预留核对；容量失败不发模型。 | `case_c6_delivery` 保留独立单元；可保留部分最终分析。形成可采用结果仍需合格结论及全案成员覆盖；没有核心不制造最终判断。 | 显式 `allow_correction=False`，不自动补写。保存系统收尾报告与模型结果分别处理；存在未知调用时保持 Run 未知、禁止采用/比较，不把收尾阶段完成写成模型成功。 |

主要位置：`alert_basic_executor.py:78,95,105,130,152,165`；`incident_diagnosis_executor.py:84,104,114,124,139,157,169`；`ai_stage_delivery.py:197`；`baseline_analysis.py:184,218,223`；`case_c3_completion_flow.py:56`；`case_c3_delivery.py:214,233`；`baseline_deep.py:70,98,116`；`case_deep_delivery.py:55,79`；`baseline_delivery.py:150,179,225`；`case_c6_delivery.py:199,236`。

输入容量不能只用正文字符数代替：`token_budget.py:84` 分别计量 chat 模板和 wire envelope，记录 `wire_bytes`、预留输入/总 tokens、上下文输入/所需 tokens 及 `context_fits`。`budget_reason`（`baseline_analysis.py:58`）还核对累计额度、调用次数、时限及最终调用预留；测量值与 provider usage 是不同口径。

## 3. 已确认的异常边界缺口

### G1：确定未发送的校验异常可能成为执行未知

`services/llm_safety.py:123` 在网络调用前执行 `LLMInputContract.validate`；该异常是 `_vendor/llm_contract_rules.py:85` 定义的 `LLMContractViolation(RuntimeError)`。DeepSeek 分支也在发送前做相同校验（`model_protocol.py:127`）。

`TenantChatGateway.complete` 只包装 `httpx.HTTPError`（`baseline_analysis_model.py:56`）；Case 的 `ModelSteps.call` 只接收列举的运输/执行/超时异常（`baseline_reasoning.py:244`），不接收该 RuntimeError。因此模型步骤和请求已保存后，这个确定未发送的失败可以直接进入外层 `uncertain`。A/I 外层 `classify_failure(stage="execute")` 对该 RuntimeError 同样落入未知兜底。

此外 `gateway.complete` 在 `timeout<=0` 时直接抛 `TimeoutError`，发生在发送前；现有分类与发送后的超时相同。错误分类不能只看异常名称，必须保留异常发生位置提供的发送事实。不能反过来把全部 RuntimeError/TimeoutError 都改判为未发送。

### G2：HTTP 已返回但 JSON 信封无效，绕过本地调用回执

两个协议分支均执行 `dict(response.json())`（`services/llm_safety.py:134,139`、`model_protocol.py:133`）。JSON 解码或顶层形状错误可抛 `ValueError/TypeError`，既不是 provider HTTPError，也没有进入收到合法 dict 之后的正文接收器。

- A/I：外层分类可将这些异常写成 `failed/invalid_input`，但它们实际发生在 HTTP 返回之后，不能据此认定请求未发送或用户输入错误。
- Case：它们绕过 `ModelSteps.call` 的本地回执保存；外层可能把该阶段/Run 写成未知，独立后续步骤也会受影响。
- 已经返回合法 dict、但 `choices/message/content/finish_reason` 不合约的路径已有显式接收诊断；不要把这类正文协议检查与 JSON 信封异常混成一个新框架。

### G3：A/I 的无回复和中断路径没有统一阶段交付回执

A/I 仅在收到 payload 后调用 `ai_delivery_store.save`。`ModelCallError` 分支会保存 `raw=None` 的本地 `model_response`，但没有对应 `stage_delivery`；直接超时/取消及 G1/G2 还可能连该本地响应工件也没有。外层会记录 Run/步骤失败或未知，不能据此声称“所有异常都没有记录”，但缺少可供交付页使用的本地结束、无正文和发送事实。

Case 已有 `baseline_failure.local_receipt`，并用真实本地结束与原件校验允许独立步骤继续；它调用的是 Case 专属存储接口，不能直接套到 A/I。应复用 `stage_delivery` 合同和验证方式，分别接入已有 A/I 与 Case 工件保存接口。

### G4：C3 汇总回执用步骤存在替代发送事实

`case_c3_completion_flow.py` 汇总回执写 `request_dispatched=bool(first)`。`first` 代表已创建的模型步骤；共享调用层已能将连接池/连接超时等路径标为未发送，且保存在底层调用回执中。两者因此可能给出相反的发送事实。

后续必须继承经核实的底层调用事实，分别保留初次和补充调用；不能根据模型步骤是否存在推断已发出。这里是源码可达路径，未声称本批业务执行命中。

## 4. 已存在的行为边界，不按“未实现功能”追修

1. 旧 [Stage11 设计 §4](../schedule-streaming-investigation-updates/stage11-output-continuation-design-20261116.md)明确限定 C3 一次缺项补充，A/I/Deep/C6 不新增自动续写。因此“有通用 correction 函数”不等于这些真实入口启用了纠正；也不能把没有续写自动列为实现缺陷。
2. C3 补充只针对缺失、未闭合或覆盖缺口；已闭合但无效的任意字段、正文质量问题，不保证触发模型纠正。`completion_fields` 与 `combine` 的这个边界应如实对外说明。
3. A/I 的 usage 未知/不一致或超过预留会在正文提取前阻断接收（`ai_delivery_store.py:29`）；Case 则将 `usage_issue` 单独记录并保留可接收正文（`baseline_reasoning.py:291`）。A/I 既有测试明确覆盖这种拒绝，因此不能无声改成与 Case 一样。若后续要统一“保留正文”和“允许发布”的关系，需要独立明确内部合同及兼容影响；本轮不改。
4. HTTP 4xx 分类、schema 拒绝和是否已执行不是同一个事实：`ModelCallError.rejection_code` 仅识别明确 schema 拒绝；`classify_failure` 还对部分 HTTP 状态返回 `failed/invalid_input`。新增发送事实必须按实际边界给出，不能由 `failed` 一概推出未发送。
5. I 结果目前仍依赖逐成员输出覆盖，输出责任随成员集合增长。后续“以事件结论为中心、约束增长”的设计必须同时评估模型职责、必要证据、逐成员结果要求和现有输出装配；仅调整 JSON 字段顺序、增加预算或换提示词不能解除这一条件。本项仅登记为后续设计，不在当前修正步骤实施。

## 5. HTTP、动态查阅页与 4177 快照分开

- HTTP：`investigation_http/external_routes/run_records.py:31` 提供步骤和工件分页；`RunStepView` 保留 `kind/parent_step_id/error/usage/input_artifact_id/output_artifact_id/artifact_refs`，工件目录提供真实 `step_id/schema_version/content_url`。没有读取即执行或补算模型回执的行为。
- 动态查阅页：`services/investigation_test/web/execution_flow.mjs:109` 按实际 Run、步骤及交付 Schema 找回执；有回执才显示“交付与缺项”。面板分别展示调用状态、本地结束、解析/交付/质量及采用资格（`:112`）。模型原答页区分原件读取失败、保存的 `raw=null` 无正文回执、没有找到原答（`:361`），没有拿合并结果冒充原答。这里仅是该动态 viewer 的源码能力，不是当前 4177 快照页面的实际接线验收。
- 因此 G1–G3 缺回执时，页面无法自动恢复缺失的事实；增加一句“正常空态”并不能修复后台记录。A/I 正常交付回执挂在父 stage，模型请求和响应挂在子 model，这个节点差异也不能被当作无交付。
- C3 不是只检查：`baseline_analysis.py:218` 会调用模型。父 stage 创建时已有准备工件输入（`:179`），正常 `finish` 保存阶段汇总输出（`:294`）；提示词与模型原答在 model 子步骤。某个页面节点两端为空，必须结合其真实步骤及原件引用判断，本次纯源码审计不判某个固定 Run 的空态正常。
- 当前 4177 的 `processing-audit` 是快照路径，静态 `docs/operations/update_processing_audit.py` 与上述动态读取链路分开；本轮没有运行其全量导出或刷新，没有用导出内容补齐缺失回执。4177 实际显示由 HTTP/页面模块独立核对，本报告不代替该验收。

## 6. 下一步只做 S1：LLMContractViolation 未发送回执

业务效果：明确 guard 以 `LLMContractViolation` 在本地拒绝发送的模型调用，页面能看到“未发送、为何失败、本地已结束”；不再由该异常制造执行未知。保留 guard、原始业务输入、告警交接字段、预算限制和既有队列重试边界。

步骤与依赖：

1. **先更新本 change 的规格增量及任务。** 将该 guard 异常明确到既有执行/交付合同；定义代码自有原因码，记录 `request_dispatched=false`、本地结束、无正文、不可重试。不记录异常 evidence、提示词或自由格式错误文本。保持原有 `ExecutionFailure` / `ModelCallError` / `stage_delivery` 的职责，不另建执行框架。
2. **仅归一 guard 的明确未发送事实。** 由 gateway/adapter 将 `LLMContractViolation` 转为既有 `ExecutionFailure` 的 `not_executed=True`、`temporary=False` 事实，接入 A/I 和共享 Case 调用层；不批量捕获所有 RuntimeError。同步核对 `accounted_steps` 对该未执行分支的预留处理，既不伪造实测 usage 为零，也不把确定未执行的错误当成远端消耗未知。不得把已经保存 running 步骤等同于已发送。
3. **补必要保存和读取接线。** 复用各阶段原有工件存储接口保存本地失败/交付回执；修正同一路径上的 G4 汇总发送事实。校验请求、响应/本地回执、stage_delivery 的引用及 hash；A/I 与 Case 各自保留既有挂载位置和父子身份。复用原有 HTTP 和动态 viewer 读取；4177 快照验证单列，不新增业务兜底数据。
4. **本地直接验证后停止本步。** 测试替身证明网络没有发送、调用不自动重试、状态与回执一致；HTTP 读回同一已保存工件，页面能区分未发送与原件缺失。保留发送后超时的原有未知处理作为相邻反例。由未参与实施者做独立复核，回报证据后再推进下一项。

本步不做：G2 的信封边界修正、`timeout<=0` 及其他无回复分支归一、I 输出重设计、自动续写扩展、真实模型比较、部署/重启/推送。后续独立处理信封错误与真实 timeout/unknown，不能借 S1 统一改判。

## 7. 可复用测试与本轮验证

| 目标 | 既有直接测试入口 | 后续需要补的最小断言 |
| --- | --- | --- |
| 发送前 guard | `test_llm_safety.py::test_a_breaching_prompt_never_reaches_the_provider` | 现有测试只证明 guard 不发送；需延伸至实际 A/I/Case 执行入口的终态和保存回执。 |
| gateway/错误分类 | `test_socai2_model_errors.py`；`test_socai2_analysis_dispatch.py::test_error_facts_and_retry_after`；`test_socai2_baseline_retry.py` | 已知未发送与发送后未知分别落入正确路径；同一请求不重发，错误只保留代码拥有的字段。 |
| 未知预算、本地结束 | `test_socai2_transport_continuation.py`；`test_socai2_capacity_model_steps.py` | 复用原件校验与额度断言；不改变既有未知调用的冻结预留或本地结束要求。 |
| C3 补充/部分保留 | `test_socai2_c3_continuation.py::test_live_completion_controller_is_bounded_and_saves_receipt`；`test_socai2_d3_continuation_independent.py` | 增加底层明确未发送时，C3 汇总也明确未发送且不补写；已保留项不被覆盖。 |
| A/I、Deep、C6 接收 | `test_socai2_ai_units.py`；`test_socai2_deep_units.py`；`test_socai2_c6_units.py` | 只复用受影响的接口/断言，保留核心依赖、闭合单元及发布资格规则。 |
| 实际 Case 调用链 | `test_socai2_baseline_executor.py` 中 provider/schema 错误及 unavailable-model-view 测试 | 在已有执行夹具上验证该本地拒绝与后续收尾，不另建故障矩阵。 |
| 动态 viewer（非 4177 快照验收） | `services/investigation_test/tests/test_execution_flow.mjs` | 原件身份、父子节点、原答不替换及真实空态；只对本步新增的回执路径补直接断言。 |

初始源码审计仅完成调用链核对、源文件指纹与测试入口登记，当时未运行这些业务测试。审计文档修改前后 `openspec validate complete-socai2-investigation-chain --strict --no-interactive` 均通过，文档链接和源文件指纹核对通过。该严格校验仅说明 change 文档结构有效；后续 S1 实际验证另见 §8。

## 8. S1 本地交付结果

统筹先独审设计，再按既有用户授权实施。仅接通 `LLMContractViolation`：共享 gateway 将其转为 `ExecutionFailure(not_executed=True, temporary=False)`；不携带 guard 的 evidence 或原始异常文本。A/I 保存本地 `raw=null` 响应及父 stage 的交付回执，模型步骤和 Run 明确失败，无新 Result、无自动重试。Case 复用原有本地结束回执；确定未执行的调用不作为未知 token 消耗，实测 usage 仍为空，原有调用次数和预算上限口径不变。

C3 汇总从显式发送事实或经原件校验的已收到响应判断发送状态；无法证明时保留 `None`。初次/补充聚合为“任一 true → true、全 false → false、其余 → None”，不再用步骤存在推出已发送。动态 viewer 仅在现有交付 facts 增加“请求发送：已发送／未发送／未确认”；没有新增组件或业务兜底。

- [本地验证回执](../../../docs/operations/evidence/model-input-guard-s1-20261128-01/verification.json)：36 项 Python、15 项动态 viewer 检查通过；修改文件 Ruff 与 OpenSpec 严格校验通过。覆盖实际 gateway、A/I `execute`、C3/Deep/C6 `ModelSteps.call`、C3 补充控制器、原件 hash/身份保存读取和既有 Run 记录适配，以及实际动态面板渲染。输入构建、台账和计量使用明确测试替身，不计真实模型质量验收。
- [精确增量指纹](../../../docs/operations/evidence/model-input-guard-s1-20261128-01/source-increment-manifest.json)：既有脏测试文件未修改，新增测试分别放在 `test_socai2_model_input_guard.py` 与 `test_guard_delivery_view.mjs`。已保存只含本步源码变化的 diff；动态 viewer 的逆向单行差异与实施前指纹一致，保留其余已有修改。
- [未参与实施者的独立验收](../../../docs/operations/evidence/model-input-guard-s1-coordinator-20261128-01/review.json)：已关联统筹源码与直接测试独审，所覆盖源码 SHA-256 与最终源码一致。

验证中的早期失败日志原样保留：新 C3 测试夹具缺少冻结策略 `system`、动态面板测试选错按钮，以及相邻旧 gateway 测试未显式选择 policy；均在本地修正测试夹具/调用方式后通过，没有更改旧失败或运行配置。旧 gateway 检查显式选用仓库 `deploy/local-investigation/investigation-policy-case-v1.toml`，未修改旧测试。

未验边界：真实 PostgreSQL 事务、在线 HTTP 服务、当前 4177 `processing-audit` 快照、远端运行版本和真实模型。未建库、未操作 21、未重新调用模型、未提交或推送。G2、其他 G3 路径、发送前零时限与 I 输出职责设计仍留后续独立步骤；本步收口不等于整个 change 完成或已发布。

## 9. S2 设计：已返回的无效 JSON 信封

状态：设计已获统筹独审通过，已完成本地实施及直接验证，见 §10。沿用 S1 与现有工作区，不重放业务、不读取实际模型正文。

**目标与范围。** 仅处理模型 HTTP 成功响应已完整返回，但 `response.json()` 解码失败或 JSON 顶层不是对象的路径。数组即使能被 `dict()` 转换，也不是合法对象信封。将其明确为 `model_response_envelope_invalid`：本地已结束、已发送、响应不可用、没有可交付结论、不可自动重试。它既不是 S1 的未发送，也不是发送后未收到完整响应的 timeout/unknown。合法对象内 `choices/message/content` 的既有接收规则不变；HTTP 非成功状态保持原分类。

| 事实 | S1 guard 拒绝 | S2 无效信封 | 已发送结果未知 |
| --- | --- | --- | --- |
| 调用状态 / 发送事实 | `failed / false` | `failed / true` | 保留既有 `unknown` 与实际发送事实 |
| 接收状态 | `no_response` | `unusable` | 保留既有 `no_response` |
| 可用结论 / 自动重试 | 无 / 不允许 | 无 / 不允许 | 不推定 / 不扩大 |
| usage 与预留 | usage 未知；明确未执行不计未知消耗 | usage 未知；保留已发送请求的冻结预留 | 沿用旧预留规则 |

**最小实现边界。**

1. `TenantChatGateway` 的 chat-completions 调用显式选择一个 response decoder；共享 `safe_chat_completions_request` 只增加可选 decoder 接点，其他调用者保持原默认行为，不反向依赖调查核心。DeepSeek 调查适配器使用同一 decoder。只在已持有 `httpx.Response`、HTTP 状态检查通过后的解码语句内捕获 JSON/编码错误，不批量捕获上游 `ValueError/TypeError`。
2. 复用 `ModelCallError`，由代码拥有的“已收到响应 + 信封无效”标记生成上述原因码；`classify_failure` 对该明确分支返回不可重试的失败，不改现有 HTTP 拒绝、guard 或 timeout 分支。错误证据只取实际响应的 HTTP 状态、异常类型/解码类别、响应字节数和 SHA-256，以及现有错误字段允许列表经脱敏后可保存的内容；复用 `model_errors` 既有 `MAX_ERROR_BODY/FIELD_LIMITS` 上限与脱敏，不增加新保留策略。非 JSON/不支持形状的任意正文明确记为未保留，不把摘要或脱敏字段标成原文；不保存 URL、header、凭据或自由格式异常字符串。本步不新增任意响应原文导出能力。
3. A/I 在该 `ModelCallError` 分支保存本地响应和 `stage_delivery`，保持父 stage / 子 model 及原请求关联。复用 S1 保存器的必要公共部分，S1 原分支保持不变。Case 复用 `ModelSteps.call` 和 `local_receipt`，仅为已收到无效信封写 `parse.state=unusable`，保留原请求预算；C3 汇总继承已发送事实和不可用状态，不发缺项补充。没有 provider 可解析模型原答时 `raw=null` 仍是本地回执，不伪造 `model_original_response` 或新 Result。
4. 现有 HTTP 记录适配直接读回该原因、原件和交付回执。动态 viewer 为 S2 同时识别 A/I 顶层本地回执与 Case 的 `payload` 回执，按保存的信封失败状态显示“收到响应但信封无效”，不为页面改保存形状。复用现有面板；实际 4177 快照不刷新、不计入本步验收。现有 A/I 顶层 `raw=null` 的普通无回复空态尚未覆盖，S1 只验父阶段交付面板；该普通无回复分支登记 S3，不能借本步声称已经全部修复。

**直接验证与通过证据。** 复用 S1 的台账/计量替身，不建新测试框架：两个协议各验证非法 JSON 和非对象顶层；A/I 与共享 Case 入口验证失败/已发送/本地结束、无 Result、原件身份/hash、无重试、usage 不记零及冻结预留未释放。用同一已保存记录走既有读取适配；动态面板只补区分无效信封的直接断言。相邻 guard、HTTP 错误与发送后 timeout 复用 S1/既有测试，不展开故障矩阵。保存精确 S2 增量与测试退出状态，由统筹独审；真实 PG、在线 HTTP、4177 快照与模型质量仍列未验。

**不做项。** S3 其他无回复/中断路径、发送前零时限、I 输出结构、更多自动续写/重试、上游服务行为重整、外部告警合同变更、建库、21 操作、真实模型、发布或推送。

## 10. S2 本地交付结果

共享 chat helper 仅增加显式选择的 response decoder，默认解码行为保持原状；调查两个协议在 HTTP 成功返回后的精确解码位置识别 JSON/编码/递归解析失败及非对象顶层，复用 `ModelCallError`。没有在 gateway 批量捕获 `ValueError/TypeError`。

A/I、共享 Case 模型步骤保存 `failed / request_dispatched=true / local_state=ended / parse.state=unusable`，无可用结论、无自动重试。C3 汇总仍为 `unusable`，不因缺少模型正文改回 `no_response`、不发缺项补充。实测 usage 为空，已发送请求的冻结预留保留。动态 viewer 兼容 A/I 顶层与 Case `payload` 两种既有回执形状，显示收到无效信封；正常原答和读取失败仍分开。

错误证据是实际响应的状态、解码类别、字节数和 SHA-256 及受限诊断；任意非 JSON/非对象正文明确未保留，没有新增原文导出或伪造 `model_original_response`。真实业务输入、告警外部合同和已有失败未改。

- [本地直接验证](../../../docs/operations/evidence/model-envelope-s2-20261128-01/verification.json)：48 项 Python（含 S2、S1 与相邻错误行为）及 16 项动态 viewer 检查通过；OpenSpec 严格校验、定向 diff whitespace 检查通过。实际保存/读取仍使用 S1 台账与计量替身，不新增数据库或测试框架。
- [S2 精确增量指纹](../../../docs/operations/evidence/model-envelope-s2-20261128-01/source-increment-manifest.json)：与 S2 开始前源码逐文件比较，S1 两份测试文件未修改；新增 `test_socai2_model_envelope.py`、`test_envelope_reply_view.mjs`。精确 diff 保存在验证记录所指的本机交接目录。
- Ruff：本轮其余修改文件通过；共享 `llm_safety.py` 的五条既有 `PLC0414` 导出别名告警与修改前逐条一致，未顺手更改其他调用者的既有导出。本地初轮新测试 fixture 导入告警已用显式导出修正；旧日志保留，没有新增业务失败。
- [统筹正式独审](../../../docs/operations/evidence/model-envelope-s2-coordinator-20261128-01/review.json)通过，已核对最终源指纹与对应入口/读取测试。测试文件最后仅增加共享 fixture 的 `__all__` 导出，统筹对该最终模块单独复验；业务源码与 renderer 无后续变动。S2 已本地收口，未扩展到后续异常步骤。

未验边界仍为真实 PostgreSQL 事务、在线 HTTP、实际 4177 快照、远端版本与真实模型；未建库、未操作 21、未调用真实模型、未提交/推送。S3 的普通无回复/中断路径（含 A/I 顶层 `raw=null` 的子模型原答空态）、发送前零时限及 I 输出职责仍留后续，不据本步核销整个 change。

## 11. S3 短设计：模型调用异常的本地结束回执

状态：统筹已独审本小节与规格，双方 strict 通过；实施与正式结束独审均已完成，见 §12。依据当前源码，不读取业务记录或模型原答。

**目标。** 已创建并保存请求的模型调用在无回复、运输异常、取消或未预期异常后，留下能读回的本地结束回执；明确区分本地已结束、远端调用结果和发送事实。复用既有 `classify_failure`、错误类型、A/I 保存器、Case `local_receipt` 及 `stage_delivery`，不增设执行框架。

**调用边界与事实。** 仅扩大 A/I 与共享 `ModelSteps.call` 中包住实际 `gateway.complete` 的异常接收边界，捕获 `Exception` 和显式 `CancelledError`；准备输入、配置、计量、数据库和返回后解析不纳入该 catch。没有创建模型调用的外层异常不得补造调用回执。既有 `Outcome` / `retryable` 分类原样复用；例如未包装 `RuntimeError` 保持 `unknown`，原 `ValueError/TypeError` 分类不借本步重定义，更不能因此推定未发送。

| 可证明事实 | `request_dispatched` | 调用与预算处理 |
| --- | --- | --- |
| 网关精确 `timeout <= 0` 检查，或已有明确未执行标记/发送前连接失败 | `false` | 零时限使用既有 `ExecutionFailure`、`model_deadline_before_dispatch`、`not_executed=True`、`temporary=False`；其他分类不变 |
| 实际 HTTP 响应已返回，包括既有 HTTP 拒绝及 S2 信封错误 | `true` | HTTP/S2 原分类不变，不将错误响应当作可用结论 |
| timeout、取消或其他异常没有提供已发送/未发送证据 | `null` | 沿用原分类；发送后结果未知仍为 `unknown`，不因步骤存在推定 `true` |

Case 的 usage 仍未知，未知调用继续保留冻结请求预留；只把精确发送前零时限加入明确未执行核算。已有 schema 拒绝的未执行预算待遇保留，但与 HTTP 请求确已发出的事实分开，不能为了释放预留继续写假 `false`。不改预算上限、计量、调用次数和自动重试规则。

**保存、传播与读取。** A/I 从已有 `save_local_failure` 传入实际 outcome、三值发送事实与接收状态，保存真实请求关联、本地 `raw=null` 响应、阶段交付回执及步骤输出引用；无完整模型响应的接收状态为 `no_response`，S2 仍为 `unusable`。`unknown` 的远端步骤/Run 不写确定结束时间，本地结束时间只落本地回执；不生成 Result。Case 在同一实际调用边界沿用原保存器，补齐未包装异常的回执。取消保存后必须重抛；新增捕获的非预期异常保存后也重抛到既有外层终态处理，不转成业务成功。错误只存原因码、类型等既有受限字段，不存自由格式异常文本。

阶段 `execution.retry_allowed=False` 表示该次本地调用已结束、不得从回执自动重放；任务 `Outcome.retryable` 仍按既有 classifier 和队列限制决定后续新 attempt。已知临时失败的任务重试资格不被新回执取消，也不新增其他自动重试。动态原答页沿用 S2 的 `saved.payload ?? saved`，同时识别 A/I 顶层和 Case `payload` 内的显式 `raw=null`；缺工件、读取失败、普通无回复和 S2 无效信封保持可区分。实际 4177 快照不刷新。

**步骤与直接验证。**

1. 设计独审与 strict 通过后，保存 S3 前源码；先实现精确零时限事实与必要预算接线，以禁止 POST 的网关替身、Case 已保存请求核对未发送/usage 未知/预留规则。
2. 补齐三个实际调用边界与 A/I 公共保存器；复用 S1 台账、S2 计量替身和既有读取适配，选取连接失败、读超时、取消、未包装 `RuntimeError` 的少量直接例子，核对原件身份/hash、local ended、三值发送事实、无 Result、取消/非预期异常重抛。额外核对调用建立前失败没有伪造回执；不展开故障矩阵。
3. 补普通原答空态并直接测试两种保存形状；复用 S1/S2 相邻检查，保留 HTTP 拒绝、信封错误和读取失败。核对任务重试资格与阶段禁止重放各自保持。保存精确增量、测试退出状态与未验边界，提交统筹独立结束审计后收口。

**范围限制。** 仅本地源码/结构和测试替身；不新增数据库，不操作 21，不调用真实模型，不发布/推送；不更改外部告警合同、旧记录、正常返回解析或模型业务判断。真实 PG、在线 HTTP、实际 4177、远端版本、真实模型仍未验。I 输出职责/结构审计在本步验收后另行推进。

小步 1 已通过：网关精确零时限改为上述明确未发送失败，共享 Case 保存本地结束回执且不把未知 usage 写零；冻结请求仍可核验，预算只按明确未执行处理。两个协议零时限、Case 实际入口及相邻 S1 guard 共 8 项替身检查通过，日志位于 `.local/validation/model-local-end-s3-20261128-01/step1-attempt-01/`。A/I 其他异常接线和动态空态尚未实施，不能据此宣称 S3 完成。

小步 2 已通过：A/I 与共享 Case 的实际调用边界覆盖未包装异常，并在保存后保留取消/非预期异常传播。发送事实使用三值，HTTP schema 拒绝明确 `true`，仅给该既有明确拒绝增加内部 `not_executed` 事实以维持原预算待遇；未知调用预留不释放。新模块 17 项直接检查、S1/S2 与相邻错误/重试 48 项检查通过，修改 Python 文件 Ruff 通过。日志分别位于同批次 `step2-attempt-02/`、`step2-adjacent-01/`、`step2-lint-02/`；首轮 import 排序检查失败保留，已按检查结果仅整理导入。独审指出的原答类型断言已同时核对 Case `type` 和 A/I `artifact_role`，新模块复验通过。动态空态及 S3 结束独审尚未完成。

## 12. S3 本地交付结果

三个实际模型调用边界已统一保存本地结束回执，A/I 保持父 stage / 子 model 原挂载；精确发送前零时限、普通无回复、已收到的 HTTP 错误及 S2 信封无效分别记录。未知远端步骤/Run 保留空结束时间，取消和未包装程序异常继续抛出；未建立调用的准备失败不伪造请求或响应。`classify_failure` AST 与 S3 前一致，任务重试资格与阶段禁止重放分别保留。

Case 把 HTTP schema 拒绝的已发送事实与明确未执行预算事实分开，其他已发送/发送未确认的未知调用仍保留冻结预留，usage 不记零。动态原答页在 S2 原逻辑中以 `saved.payload ?? saved` 识别显式 `raw=null`，兼容 A/I 和 Case；缺内容、缺工件、读取失败及已收无效信封均有直接区分检查，没有改保存合同或刷新实际 4177。

[本地验证](../../../docs/operations/evidence/model-local-end-s3-20261128-01/verification.json)记录新模块 17 项与相邻 48 项 Python、16 项动态 viewer、修改 Python 文件 Ruff、strict 与定向 whitespace 通过；[精确增量指纹](../../../docs/operations/evidence/model-local-end-s3-20261128-01/source-increment-manifest.json)对应 S3 前本地源码，已有他人及 S1/S2 修改保留。真实 PG、在线 HTTP、实际 4177、远端版本和真实模型仍未验；未建库、未动 21、未调用模型、未提交/推送/发布。

[统筹正式独立结束审计](../../../docs/operations/evidence/model-local-end-s3-coordinator-20261128-01/review.json)已通过，独立 27 项 Python 及原答渲染 8 种状态通过；清单、统筹基线、测试源码与当前最终源码指纹一致。S3 仅本地收口，不核销整个 change。后续进入 I 输出职责/结构源码审计，先给可审方案，不直接修改输出合同或执行新模型测试。

## 13. S1/S2/S3 限定发布与单笔 Case 验证安排

负责人要求继续已有 S1/S2/S3 限定发布：把已验的前轮材料核验窄修纳入候选，在同一已确认 Case 上安排一笔全新正常 rerun。本节保留本批的准备、切换与验收方案；已按准备独审、限定切换、独立加载核验、单笔任务顺序执行，每一步以前步明确回执为条件，没有重跑已完成的本地测试或追加模型任务。负责人授权读取本批脱敏最小报告后，统筹已核实际任务、保存及 8181 读回；交付限制和剩余读取项见 §13.5。统筹负责 Git/index、远端分支、main、父项目同步及根 PROGRESS，本执行线程不操作这些内容。I 输出精简仍未实施，不进入发布。保持 21 目标及既有数据库/profile、模型和预算/重试边界，不建库、不清旧记录。

本批连接按[现行手册 §2](../../../docs/operations/investigation-manual-deployment-21-20261127.md)既有显式跳板 `ssh -J sting-win57 sting-infra21-direct`，跳板/目标/时限只从私密配置读取；不生成密钥或调整 Windows 服务，不把旧别名转发入口与现行直接跳板混用。仅安排一次有界只读采集，运行回执留私密。

### 13.1 目标、候选及必要依赖

目标是将已独审的 S1 输入 guard 未发送回执、S2 已收到无效信封回执、S3 实际调用异常本地结束/三值发送事实，以及 `previous_analysis` 原生受理归一化重放修正带到现役调查执行路径。完成后，在已确认材料所在 Case 上用一笔全新正常调查任务验证接线；不复用旧任务或旧 operation key，不把本地整个脏工作树当成发布包。

以下为 S1/S2/S3 审核增量涉及的生产 Python 文件；候选必须以本批只读取得的现役源码为基线，逐项核对精确增量及依赖。不能因为这 11 个本地文件经过测试，就连带发布它们包含的其他未在本批范围内的改动。

| 文件（均位于 `services/api/app/`） | 本批改动职责 |
| --- | --- |
| `services/llm_safety.py` | 显式 opt-in decoder 接点，其他调用者默认行为保持 |
| `socai2/model_errors.py`、`baseline_analysis_model.py`、`model_protocol.py` | 明确 guard/零时限/信封错误事实、调查两个协议的解码边界 |
| `socai2/analysis_dispatch_types.py` | 发送事实三值辅助与 S2 明确错误；既有任务重试分类保持 |
| `socai2/ai_delivery_store.py`、`alert_basic_executor.py`、`incident_diagnosis_executor.py` | A/I 调用异常的原请求、本地响应及父阶段交付回执 |
| `socai2/baseline_reasoning.py`、`baseline_failure.py`、`case_c3_completion_flow.py` | Case 本地结束、取消/异常传播、冻结预留及 C3 汇总事实 |

原候选另含既有 M0f 的 6 项依赖，以已审候选清单为准：`case-input-v1.json`、`case_c3_input_selection.py`、`case_followup_input.py`、`case_input_text.py`、`case_program_output.py`、`runtime_policy.py`。本批冻结复用原已审文件内容，不重新从当前脏工作区选取它们。本批只新增 `case_previous_analysis.py`，候选内容 SHA-256 固定为 `c12836891ee4fc8655aa85eb14a1ed785a98966f2b0d4f0b205512cb475c7721`；其余既有来源/正文校验不变，键序兼容、v3 和 I 输出精简均不纳入。

新增文件的实现与直接验证复用 [P2 记录](../../../docs/operations/evidence/previous-analysis-normalization-p2-20261128-01/README.md)，不重复 C3/C6 测试或已保存工件重放。既有定向组的旧夹具身份检查失败继续后置，不通过修改真实配置或身份校验规避。

必要合同依赖为既有 `stage_delivery`、原件保存/读取适配、Run/步骤模型及调用方；准备时比较这些依赖的现役和已验版本。若现役在前批结束后恢复旧版而缺少已完成/已推送的 M0f unmapped 输入过滤或本笔正常路径必需的已验基础修正，应列出具体文件、HEAD 对应及既有独审出处，作为明确依赖候选交统筹审；不能机械将新异常补丁放到已知不兼容的旧组合。没有新增输入设计或 I 输出精简的实施范围，也不能带入未知脏改动。若审核增量不能干净应用到现役基线，先记录准确冲突与最小依赖，再交统筹独核，不强制整文件覆盖。

`execution_flow.mjs` 的 S1/S2/S3 动态查看器增量单列：先核当前查阅服务的实现。不能将动态源码替换等同于更新实际 4177 静态 processing-audit 快照，也不因此发布平台页面。本笔 Case 结束并取得快照后，按既有审计页更新入口保存该新批次，不覆盖旧批次。

### 13.2 只读核对与发布/恢复顺序

1. 在新独立目录中复用已审只读采集脚本，仅进行一次有界采集；私密记录当前目标服务的容器/镜像、启动命令、实际工作目录/源码挂载、profile/配置原件与加载路径、网络/端口、重启策略及原恢复点。当前运行值与判断结果均只落私密文件，不进入任何会话；历史文档只作入口，不能充当当前核对结论。
2. 从现役源构造隔离候选，对照 S1/S2/S3 精确审核增量生成文件清单、逐文件 diff、最终源码指纹与必要依赖说明。核已有本地检查覆盖候选的关系；新依赖或需移植的改动只做直接必要检查，不重跑整仓或制造线上故障。现有 HTTP 是否需同步仅由真实调用/读取依赖决定，不默认全部服务重启。
3. 本次准备先交目标、18 项候选内容清单及精确源差异、直接合同依赖、配置保持策略、恢复命令和唯一新任务入口，由统筹源码独核后再进入切换步骤；实际所需覆盖文件由与现役的逐项比较决定，不能用候选项数冒充实际覆盖项数。切换前核唯一相关执行器及本地任务空闲条件；不并行启动两个消费者，不中断正在执行的模型调用。
4. 使用本批明确清单的隔离候选目录/只读覆盖或既有发布机制；保留原容器、镜像、源码/profile，不覆盖原恢复材料。候选加载核对、必要健康/读取检查先通过，再创建唯一测试任务。该笔正常测试及独立验收通过后将获准候选保留为正式新版，不为另一次“正式发布测试”重建第二笔 Case，也不机械恢复旧版撤回修复。失败则按明确回执停止候选、恢复原服务及配置；没有明确终态的有副作用创建不重试。
5. 若测试开始后需要恢复，先跟踪原任务和执行句柄至本地已结束或明确未知回执，保留全部工件与错误；不靠停止后新建任务追认成功，不改原失败/unknown，不删业务数据。恢复原实例后只读核对唯一在役执行器及原配置，不自动重放本笔任务。

### 13.3 单笔正常 Case 与字段核对

复用已确认 OCSF 材料所在 Case，业务合同为 `POST /api/v1/socai2/cases/{case_id}/investigations`，请求仅含本批新生成并冻结的 `operation_key` 与 `mode: rerun`；不再次创建 Case。新 key 必须区别于所有已知前批 key，旧批次、旧 task/attempt/Run 和旧 intent 均不复用。具体身份和请求值只从受控私密材料取用，不写公共计划。提交前落本批独立 intent，受理后只跟踪该全新原生 task / attempt / Run；响应未知时只按本批同 key 查询，不自动重复 POST、不在该批再次换 key、不重派旧任务。旧 Case、失败记录及采用指针按原生规则保留，不手动修数据。沿当前单 Run 预算和工具边界执行，不增加预算、重试或额外故障注入。

统筹按既定部署边界确定，本轮唯一正常 Case 经 **21 已发布的正式原生 HTTP 服务**验证；不为此重部署 SpiritHub 整栈，也不增加 8181 私有 POST 分流。平台普通入口缺口由平台会话修正、定向测试并纳入代码交付，未上线范围单独保留。HTTP 会话负责给出明确的原生连接、正常认证及当前 profile 身份方案，统筹先独审，再由核心执行下列受控顺序：

1. 本批仅沿既有私密引用冻结同一 Case 身份、新 operation key 和请求体；旧平台请求、原生请求、失败回执及恢复证据保持原件。
2. 后续发送前使用经独审的原生连接/正常认证配置，核它与实际 profile 身份及已确认 Case 范围一致；不借平台转发头或猜测身份绕过认证，不更改库、预算或业务配置。
3. 新候选加载和必要读取检查通过后，按本批 key 做受理核对。若已有任务只跟踪该任务；结果未知时不发送。新批次不能凭旧 key 查无或旧任务终态冒充未受理。
4. 条件通过后，为本批发送保存独占 intent，以冻结的新 key/body 仅发送一次；响应未知后只读核对，不自动重投，不再创建第二笔正常测试。
5. 保存该新 task/attempt/Run 的输入、调用、保存及读取证据，并按实际执行情况追加 4177 本批快照。区分未产生 Run、步骤未调用、失败及交付缺项；该验证不能追认为 8181 普通 POST 已上线、异常分支在线触发或整栈入口已验收。

| 核对层 | 需保存/关联的字段结构 |
| --- | --- |
| 发布加载 | 服务/镜像/入口、挂载与实际源路径、文件指纹、profile 及实际配置指纹、恢复点 |
| 原生新调查任务 | 本批冻结 operation key、已有 Case/新 rerun task/attempt/Run 关联，任务状态、retryable 与本地结束字段；旧任务身份不得复用 |
| 冻结输入 | Run.input_artifact_id 指向的当前输入清单，以及其 source_materials/同 Run 来源快照的实际引用、hash、成员身份和原始 OCSF 路径；按当前保存层级走引用，不能沿用历史检查器错误的顶层查找 |
| 每次模型调用 | model_request/model_response/original_response 的 Run/步骤/父步骤引用、Schema/profile、实际提示与响应、usage 状态和冻结预留；正文只存私密证据 |
| 阶段交付 | execution.call_state/local_state/local_ended_at/request_dispatched/retry_allowed、parse/delivery/use、原件引用及完整性；区分本地已结束与远端确定结果 |
| 保存/读取 | Result/诊断/材料与当前指针、版本/采用状态、读取适配返回及源工件关联、4177 该批次展示。失败、unknown、质量与交付完整性分开保留 |

这笔正常流程只能验证实际已部署版本的原生入口、常规调用、保存/读取及相关 Case 接线，不能证明 guard、无效信封、运输中断或取消分支在线触发通过。那些异常分支仍使用 S1/S2/S3 的本地替身直接检查与独审证据；不能以正常 Case 一笔通过替代异常分支或模型质量验收。

### 13.4 证据边界与本小步交付

本批私密根目录为 `.local/validation/model-exception-release-rerun-prep-20261128-01/`。首批 `.local/validation/model-exception-release-prep-20261128-01/` 及 P1/P2 证据只作冻结来源，不覆盖或重跑。远端运行、配置、业务、模型原答和查询派生的值/状态/布尔项只留受控私密文件，不向本对话或任何跨对话输出；统筹此前的根会话报告授权不覆盖本执行会话或本批新结果。可交付源码/结构、工作安排、文件清单和私密证据路径；数据结果如需进入会话，必须另按本批用户确认范围处理。

准备结果应包含源清单/精确候选差异、依赖说明、私密配置保持与恢复清单、一次性测试入口及上述字段结构检查计划。具体操作、加载核验和受理结果只以本批私密回执为准，不能用这份准备说明替代结果。验证通过后的正式保留及 Git 后续按上述职责分工执行。

首批精确候选与操作入口见[原发布准备交接](../../../docs/operations/evidence/model-exception-release-prep-20261128-01/README.md)，本批复用其已审脚本并另存计划、候选和回执。准备交接只覆盖源清单/精确 diff、配置保持、恢复方案和一次性新任务的结构；不代表已切换、已提交或业务通过。

首批平台 transport 与原生 HTTP 校正证据仍保留在原批次 `task-reconciliation-01/` 等目录，仅适用于首批；其同 key 校正过程不能用于复活已结束批次。本批直接使用经独审的正式原生入口，已完成唯一新任务的提交和终态跟踪。原生 `status_url`、平台前缀和平台普通 POST 的部署边界仍分别保留，不能因正常原生测试推断平台整栈已交付。

### 13.5 本批已获准结果与剩余边界

负责人回复“继续 授权”后，统筹读取已审阅脱敏的最小报告，并授权执行本批 exact-Run 原件的本机私密导出；原文不进入聊天或 Git。[统筹记录](../../../docs/operations/evidence/previous-normalization-release-coordinator-20261128-01/review.json)只保留获准状态、程序码和检查项。

- 独立加载检查通过；原生任务以 HTTP 202 受理，产生实际 Run，并以 `completed` 结束。前轮材料已进入本 Run，冻结成员、版本、引用及摘要的保存链核对通过。
- C3/C6 模型调用正常结束，返回 `complete_json`，未截断。最终结果为模型来源、`accepted`、`uncertain/partial`，当前 Case 已采用该结果；这是实际部分交付，不能写成完整调查质量通过。
- 原生任务、Case 页面数据、模型工件目录与前后 PG 快照一致。8181 调查概览、调查历史及固定轮次的 Run/Result 读回与保存值一致。
- 原生 `GET /cases/{case_id}/investigations/{run_id}` 返回 404。取证脚本路径符合当前合同；本批冻结的现役 HTTP `main.py` 尚未注册 `case_investigations.router`，本次执行器切换也未更新 HTTP 服务。保留原回执，不用 `/runs/{run_id}` 详情请求替代定位接口的验收；新调查目录/定位接线须纳入统一 HTTP 发布范围。
- 4177 原件导出已有新增明确授权，已执行本批私密导出、离线归档及动态查看器的同 Run 必要只读核对；统筹复核实际执行的源码指纹与私密 Git 忽略边界。负责人随后审阅脱敏并明确允许读取最终最小报告的阶段、HTTP 状态和布尔检查项，统筹已完成限定读回：实际动态请求成功，同 Run/步骤目录、所选模型输入/输出原件和保存错误的读取核对通过。只读取配置的首个目录页，工件目录未读全；离线归档与现役动态服务保持分开，没有浏览器视觉验收、服务/隧道变更或额外模型调用。此结论限本次有界查阅，不等同全部工件分页或整个页面验收完成。

本笔正常任务不替代异常分支的线上故障验证；异常分支仍由 S1/S2/S3 本地直接检查支撑。模型正文质量、普通平台 POST 上线、统一 HTTP 发布与 Git/main 整合不因本报告自动核销。
