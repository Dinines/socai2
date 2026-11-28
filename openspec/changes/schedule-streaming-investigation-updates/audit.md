# 独立结构审计

审计日期：2026-11-18。审计者：独立子代理 `d6_change_scope_audit`，未参与本 change 的实现，也未修改本轮范围对齐文件；独审仅新建本文件。

**结论：本轮范围、后置归属和文档结构审计完成，复核后无未关闭的结构问题；整个 change 仍不具备归档条件。** 本结论不新增业务验收、不证明最新写侧已统一发布，不核销原 3.1/3.2/4.1，也不将后置功能记为完成。

## 审计范围与数据边界

依据新版 [AGENTS](../../../AGENTS.md#codex-和-gpt-服务的数据边界)及负责人本轮“不用管真实的数据”的指令，本次只读取约定、需求/任务定义、规格标题与约束、文档入口和链接结构，并补核 D5/D6 关键类、函数、调用、字段与路由结构；对混有业务记录的文件只提取本轮范围声明或结构。代码提取不输出业务字符串、样例或 fixture。未读取业务样本、模型原答、HTTP/SQL 返回、证据封包或数据摘要，未访问 21、HTTP 或浏览器，未运行业务测试、模型、发布或证据重算。

核对对象为[当前范围表](closeout-scope-20261118.md)、[后置原文](deferred-scope.md)、[proposal](proposal.md)、[design](design.md)、[tasks](tasks.md)、当前四份 delta，以及 OpenSpec、进度、交接、调查导航和问题清单入口。56 条要求的实现/测试映射只核定位关系及文件存在；另对下节所列 D5/D6 链路核实际静态调用和字段传递，不扩大为 56 条行为测试或全仓代码审计。静态接线不能证明既有业务证据通过。历史通过、失败、unknown 和质量后置结论保持原记录，不在本轮重新判定。

## 结构核对结果

| 检查项 | 独立复核结果 |
| --- | --- |
| 当前要求逐条归属及 CLI 实际解析 | 当前四份 delta 共 56 条 Requirement，与范围表一一对应，无缺项、多项或重复映射；其中 54 条 ADDED、2 条 MODIFIED。独立运行 `openspec show schedule-streaming-investigation-updates --json --deltas-only`，确认 CLI 实际解析 56 条，逐条规范空白后的要求正文及全部 165 个 Scenario 正文与源文件一致，无遗漏或重复 |
| 能力分布 | `case-human-http-flow` 3 条、`case-purpose-knowledge` 2 条、`investigation-test-service` 15 条、`investigation-update-scheduling` 36 条 |
| 主规格对应关系 | 两条 MODIFIED 均能匹配现行主规格的同名要求；ADDED 没有与现行同名要求冲突。两项新能力仍未同步入主规格，`openspec/specs` 没有本轮改动 |
| 后置完整规格 | 人工定向分析、手动全案综合各一条，以及知识后台异步维护的两条原 Requirement，包含原 Scenario，均在 `deferred-scope.md` 完整保留；与提交基线比较仅忽略空行差异 |
| 混合原任务 | 原 2.4、2.6、2.7 全文逐字保留；任务入口仍使用原号。全部 11 个任务号和勾选状态与提交基线一致：仅 1.1、2.1 保持已勾选，其余未勾选 |
| 后置混合条款 | 知识复用、队列优先级、不同请求意图、异步 HTTP、查询窗口及测试配套的原后置条款继续可追溯；普通 H 与定向/综合的职责区分原句经审计补回 |
| 本期要求保留 | 有效 H 正文/范围/引用及撤回、完整 C1–C6、上一实际调查比较及不可用空态、后续采用保护均仍在 current delta；普通 check/rerun、任务/Run/结果读取、目录分页和统计、配置及 HTTP/4177 要求未随定向/综合移除 |
| D5/D6 静态接线 | 对下节接收、下游构造、保存、HTTP/4177 读取和本地收尾调度链核函数调用、字段及守卫；在该限定范围内未发现具体断接，不推定真实运行通过 |
| 后置边界一致 | proposal、design、tasks、当前规格及入口统一将人工定向分析、手动全案综合、知识后台异步维护标为后置、未实施；它们不是当前归档阻断，其他本期未完项没有随之核销 |
| 当前与历史分开 | 三份长设计顶部明确当前范围入口，tasks 的既有子步记录标为原时点记录；进度、交接、导航和问题清单均保留当前未归档与结构审计限定 |
| 链接与格式 | 检查范围内本地 Markdown 链接的文件/目录目标均存在，兼容 `:行号` 后缀；此项不声称所有历史锚点均已验证。相关文档 `git diff --check` 通过 |

当前 `historical-alert-knowledge` 异步维护 delta 已移出 `specs/`，其原要求仍保存在后置文件；现行主规格的提交后同步合同未被覆盖。当前 `case-human-http-flow` 和 `case-purpose-knowledge` 保留实际本期增量，没有用整个能力的移除代替子范围拆分。测试服务继续保留未来定向/综合场景的设计、数据合同和接口依赖，同时明确依赖未就绪不算真实执行通过。

## D5/D6 有界静态接线核对

以下沿生产代码的函数调用、分支守卫、字段和路由检查，不运行处理逻辑、不读取运行产物。结论是这些接线在当前源码中存在且相互承接；不是保存结果、模型正文或部署状态的重验。

| 链路 | 静态可确认的承接 |
| --- | --- |
| Deep 接收至 C6 输入 | [case_deep_delivery.receive/parser/save_receipt](../../../services/api/app/socai2/case_deep_delivery.py:24) 由 [BaselineDeep.execute](../../../services/api/app/socai2/baseline_deep.py:31) 调用；`finish` 将可用 `unit_delivery.answer` 保存到 `deep_summary.answer`，并保留 `iterations[].stage_delivery`。`BaselineReanalysis.input` 的 `final_delivery` 分支进入 [case_followup_loader.final](../../../services/api/app/socai2/case_followup_loader.py:91)，再由 `case_followup_input.build` 将已有 `deep_summary.answer` 注册为 `prior_analysis` 输入，完整/局部答案没有另走一条未接入的展示路径 |
| C6 接收与交付资格 | [case_c6_delivery.receive](../../../services/api/app/socai2/case_c6_delivery.py:98) 形成 `retained_output`、`retained_units`、`missing_units`、`invalid_units`、`delivery` 和 `use`；`parser` 返回完整 Delivery 或 RetainedFinal。[BaselineDelivery.execute](../../../services/api/app/socai2/baseline_delivery.py:88) 实际使用此 parser 并调用 `save_receipt`，后者核模型步骤终态及原件关联，再通过 `validate_sources` 和 `save_input_artifact` 保存 `stage_delivery`。`use.adoption_eligible`/`comparison_eligible` 与 `delivery.state` 分开保存 |
| 执行、保存与 unknown 收尾 | [BaselineExecutor.execute](../../../services/api/app/socai2/baseline_executor.py:52) 从 `analyze`、`dispatch_followups`、`build_graph` 进入 [BaselineService.finalize](../../../services/api/app/socai2/baseline_service.py:132)，后者实际调用 `BaselineDelivery.execute`；C3 后续派发受 `followup_unit_paths`/`dispatch_paths` 限制。[BaselineDelivery.finish](../../../services/api/app/socai2/baseline_delivery.py:165) 调用 `make_publication`，保存 `delivery_report`、`report_json` 和 `delivery_receipt`，普通终结进入 [BaselineStore.publish](../../../services/api/app/socai2/baseline_store.py:428)。有 unknown 步骤时走 `mark_unknown` 分支，保留收尾工件、`local_state=ended` 及空 `result_id`，不通过普通 publish 补造完成 Result。publish 仍检查步骤收齐、成员集合和引用 |
| 上一轮材料与比较 | [case_comparison.select_previous](../../../services/api/app/socai2/case_comparison.py:12) 先选上一实际完整调查，再判比较资格；不可比时保留 `previous_run_id`、空 `comparison_result_id` 和原因，不继续寻找更早成功轮。[BaselineStore.claim](../../../services/api/app/socai2/baseline_store.py:213) 调用 [case_previous_analysis.freeze/project](../../../services/api/app/socai2/case_previous_analysis.py:174)，经 Sources 的主体/Run、hash、大小和接收回执校验后，保存本轮 `previous_analysis_material`；原范围与 `applicable_alert_ids` 分开，引用角色为 `prior_analysis`。该字段进入 [baseline_model_view.candidates](../../../services/api/app/socai2/baseline_model_view.py:69)，不与比较结论资格混同 |
| task/attempt 本地结束与继续调度 | `AnalysisCaseExecutor.execute` 从保存后的 Run 状态返回 Outcome。[AnalysisDispatcher._collect/_flush_receipts](../../../services/api/app/socai2/analysis_dispatcher.py:108) 收集结束句柄、移出 `active`、释放队列运行索引，并调用 [analysis_dispatch_store.finish](../../../services/api/app/socai2/analysis_dispatch_store.py:107) 与 [finish_attempt](../../../services/api/app/socai2/analysis_task_store.py:211) 保存 `local_state`/`local_ended_at`、outcome 和任务终态；unknown 不具备自动重试资格。`_busy` 同时检查 `active` 与未确认 `receipts`，不会因内存槽已释放就并发启动同主体；`tick` 在收尾后按剩余容量继续领取，未确认回执不占用其他主体的内存执行槽 |
| 保存至 HTTP 读取 | [CaseReader.run/result/artifact](../../../services/api/app/socai2/case_reader.py:350) 按主体/Run 读取，artifact 校验 hash/大小，result 核 C6 receipt/detail 关联；`CaseService` 使用只读事务。[cases.run_detail/result_detail/artifact_content](../../../services/api/investigation_http/external_routes/cases.py:211) 提供 `/socai2/cases/{case_id}/runs/{run_id}`、结果和原件路由，并返回 `comparison_context` 的链接。`RunRecordsReader.page` 经 adapter 的 `content_url` 接入 `/socai2/analysis-runs/{run_id}/steps` 与 `/artifacts`；`AnalysisAttemptView` 保留 `local_state`/`local_ended_at`，沿 `/socai2/{kind}s/{subject_id}/analysis-tasks/{task_id}` 读取 |
| HTTP 至 4177 | [viewer.fetchSelection](../../../services/investigation_test/web/viewer.js:416) 沿目录 URL 分页读取 steps/artifacts，按 Run 核结果身份，读取匹配任务；无 Result 时通过 [readClosingReport](../../../services/investigation_test/web/delivery_view.mjs:14) 沿 C6 receipt→detail 取收尾报告，并核同 Run/step。`deliveryRecord` 核 schema/run/step；[executionFlow.deliveryPanel](../../../services/investigation_test/web/execution_flow.mjs:108) 分开展示调用状态、本地结束、交付、采用/比较资格、保留单元及缺口。`localEndLabel` 使用 attempt 或 report 的本地结束字段，结果读取失败和收尾报告保持独立状态 |

这次补查未发现上述关键接线存在具体结构阻断。仍需原业务证据才能判断的事项包括：实际响应单元能否按期望接收、真实冻结材料/引用是否正确、事务保存及 HTTP 原值读回、运行中的超时和下一任务行为、页面实际呈现及服务实际加载版本。本轮不读取或重评这些证据，既有失败与未验边界不因此关闭。

## 审计发现与复核

初查发现原 `New analyses preserve human scope and later adoption decisions` 混合条款移出的一句“人工定向及手动后续综合 SHALL 保持与有效H更新的区别；”未进入后置原文。主侧已补入[原 H 与定向/综合职责区分条款](deferred-scope.md#原h与定向综合职责区分条款)，注明 Requirement 来源和第 8–9 步归属；独立复核确认原句保留，本期 H 原文/范围和采用保护未误删。此结构问题已关闭。

主侧在最终 CLI 实际解析复核时发现第二项结构问题：[case-human-http-flow delta](specs/case-human-http-flow/spec.md) 在“第7步比较读取增量”后重复声明 `## ADDED Requirements`；虽然 strict 通过，原 CLI 解析只得到 55 条，遗漏 `Case comparison identity is frozen and readable`。主侧移除中间分节标题和重复 ADDED 标题，使新增要求归入同一操作节；这项修正不取消比较要求。

独审在修正后实际运行 `openspec show schedule-streaming-investigation-updates --json --deltas-only`，并按 capability、operation 和规范空白后的正文逐条比对四份当前 delta：CLI 的 `deltaCount` 与条目数均为 56，要求正文全部匹配，全部 165 个 Scenario 正文及数量也匹配，无未匹配条目或重复匹配；上述比较要求恰好出现一次。再运行 `openspec validate schedule-streaming-investigation-updates --strict --no-interactive`，结果通过。第二项结构问题已独立复核关闭；不能仅以标题数量或 strict 通过推定归档解析完整。

另以本地结构提取核对主规格操作类型、后置原文、任务号/勾选和链接目标。未运行归档或封后校验；这些 CLI 检查只证明当前解析和结构有效，不核销业务验收或交付条件。

## 仍未满足的归档条件

1. 原 2.2–2.5、2.7 和 3.1 的本期总项覆盖仍待沿已有分步记录核清。已有子步不能因总项未勾选被否定，也不能由本轮标题映射推定全部业务场景通过。
2. 原 3.2 保留完整 change 的交接和结束审计边界。本文件只补充独立结构审计，不将未读取的业务证据重新判为通过，不整体核销该任务。
3. 原 4.1 的最新本期写侧/HTTP/配置统一交付、实际读回以及 Git/父项目同步仍是未完成条件。此前独立工作台发布不能替代这些交付；本轮未执行或追认它们。
4. 条件具备后才正常执行 OpenSpec 归档和规格同步，不以 `--skip-specs` 或 `--no-validate` 绕过。移动后按原目标重算 change 的外部相对链接，并同步进度、交接、导航和问题入口；保留旧封包路径及内容，再核主规格、active/archived strict 和链接。

人工定向分析、手动全案综合、知识后台异步维护继续按原依赖和验收出口恢复，保持未实施，不作为本期阻断。模型正文质量后置与原 NOT_PASSED 不变。本次没有 archive、主规格同步、业务重验、发布、Git 提交/推送或父项目引用更新。
