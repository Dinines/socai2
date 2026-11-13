# 调查结果采用、未完任务与结案：规则及交接

更新于2026-11-13。F11-03已按D01/D03/D07接入E21采用、E63预览及E64判断历史；两端独立HTTP服务及Swagger统一交付见[验收](../../openspec/changes/archive/2026-11-13-adopt-investigation-results/validation.md)。核心与HTTP分工明确，模型质量和自动调度仍不在本项完成范围。[后端调用指南](../integration/result-adoption-http.md)。

## 1. “接受调查”具体指什么

本轮讨论按“采用一份调查结果作为案件当前判断”理解。这个动作选择的是一份已经保存、可追溯的结果，不代表案件已经结案，也不代表所有任务完成。若产品实际要表达“接受并结束调查”，必须另行定义结案和未完工作的处理，不能在采用接口中隐式执行。

| 概念 | 表达的事实 | 当前设计／实现 |
| --- | --- | --- |
| 结果通过程序校验 | 结果结构、引用等满足接收规则 | 已有 `validation_state=accepted`；不是用户点击接受，也不是模型质量通过 |
| 采用结果 | 将指定结果记为案件当前判断，记录来源及采用历史 | 基础调查自动采用保持；人工采用E21、预览E63和历史E64已交付 |
| 一轮程序调查结束 | 这次 Run 的执行结束；交付可能完整、部分或失败 | 已有 Run 和步骤状态；结束不自动结案 |
| 人工任务完成 | 用户提交核实结果及适用范围 | 已有任务与修订；完成任务不直接改写当前判断 |
| 案件结案 | 人工结束案件处理 | E46 已实现，按 D01 检查运行状态和未完人工任务；不取消任务 |

已确认的 D03 要求：采用前展示原判断、新判断、覆盖及未覆盖成员，填写替换理由，保留旧版本；局部回答不能直接覆盖全案判断，普通聊天不能直接采用。D07 要求未解决问题随结论展示，需要人工核实再由用户创建任务，不自动建立问题管理流程。原规则见[产品确认记录](../design/investigation-product-decisions.md)。

## 2. 本轮从代码核对的现状

以下为当前规则；本机真实保存读取及21只读核验分别记录，21生产写入未实测。

| 事项 | 实际行为及来源 |
| --- | --- |
| 人工采用入口 | E63先预览；E21提交operation_key、expected_review_token、reason及必要acknowledge_pending_work；E64读历史。旧expected_scope_revision占位体已停用。[HTTP路由](../../services/api/investigation_http/external_routes/cases.py)、[共享合同](../../services/api/app/socai2/case_adoption_contracts.py) |
| 基础调查自动采用 | 要求本轮 completed、结果 accepted、存在可用模型结论、范围和冻结输入仍有效，并检查成员交付。可能采用 uncertain／partial 结果，不能据此宣称所有问题已解决。若当前判断的采用时间不早于本轮启动时间，返回 `newer_assessment`，不覆盖较新的判断。[现有函数](../../services/api/migrations/125_socai2_baseline_input_freshness.sql) |
| 人工采用后的自动覆盖 | 本地核心沿用原规则，没有永久人工锁定：在途旧Run不能覆盖较新的人工采用，之后明确启动的新Run仍按原资格自动更新。本批用程序提供的Result在真实PG验证这两个顺序；未做并发压力或真实模型测试 |
| 程序待办和执行 | 同案基础调查可以有 pending_update、running 或 unknown；pending_update 是待显式启动，不代表已经排入会自动执行的队列。已经启动的调查由程序执行；当前结束不自动接续下一轮。[准备／启动用例](../../services/api/app/socai2/case_service.py)、[已确认规则](../design/investigation-product-decisions.md) |
| 人工任务 | not_started／in_progress 是未完状态，任务有独立版本。保存完成反馈不会自动启动调查，也不会自动采用新判断。[任务用例](../../services/api/app/socai2/human_task_service.py) |
| 反馈变化后的旧结论 | 基础调查当前判断可保留，同时读取其冻结输入的新鲜度。有效已完成反馈的新增、实质修改或撤回可能使原判断变为 stale／human_feedback_changed；改标题、负责人或只是增加未完成任务不等于新增有效反馈。[新鲜度函数](../../services/api/migrations/125_socai2_baseline_input_freshness.sql)、[当前判断读取](../../services/api/app/socai2/case_reader.py) |
| 结案 | running／unknown 阻止结案；有未完人工任务须明确确认并填写理由，任务保持原状。现有检查不把 pending_update 当作运行中，也不取消它；后续显式启动受已结案状态限制。[结案用例](../../services/api/app/socai2/case_management.py)、[启动用例](../../services/api/app/socai2/case_service.py) |

未来反馈后的自动综合复核、材料变化后的自动更新，已有[更新／流式 OpenSpec](../../openspec/changes/schedule-streaming-investigation-updates/proposal.md)。它们是后续目标；不能用该设计解释成当前已经自动执行。

## 3. 面对未完任务的核心规则

下述规则已纳入本地调查核心，依据既有D01、D03、D07及固定流程范围；已由对外HTTP接口复用，完整参数见Swagger。采用前统一读取预览，提交时在Case锁内重算并核对摘要，随后检查资格及明确确认。

| 用户采用时的情况 | 核心处理 | 采用后的结果 |
| --- | --- | --- |
| 存在未完人工任务 | 展示未完任务ID、当前修订、标题和状态；须明确知晓后采用符合资格的结果，不把待核事实写成已经核实 | 当前判断更新，人工任务继续保留；核心参数acknowledge_pending_work用于确认 |
| 正在产出所选结果的 Run 尚未结束，或执行状态不明 | 不把阶段产物或执行不明当作可采用的最终结果 | 保留当前判断，继续查看真实执行状态；unknown 不能当作失败后盲目重派 |
| 所选结果已经完成，另有 Run 正在运行 | 允许采用仍适用的已保存结果，明确提示并确认另有调查进行中；不因采用终止运行 | 运行保持；AD03沿既有采用时间和Run启动时间规则控制覆盖 |
| 另有待启动调查 | 显示待启动状态；采用不启动、不取消该 Run | 待启动记录保持，是否继续由后续明确操作或已启用的调度规则决定 |
| 后续人工反馈或材料实质变化 | 保留原结果及采用历史，显示依据已过时／待复核；不伪造旧结论已包含新材料 | 当前仍显式 prepare/start；将来的自动复核由既有更新模块负责 |
| 用户同时想结束案件 | 使用独立结案操作和 D01 检查；界面即使组合操作，也需分别呈现采用与结案的结果 | 采用成功不冒称结案成功；未完任务不会因此自动完成或取消 |

例子：第一轮结论为“存在可疑行为，仍需确认是否为授权维护”，同时有一项人工任务“向运维核实维护窗口”。用户采用后，当前判断仍包含这一待核限制，任务仍未完成。运维后来提交有效反馈，旧结论保留但可提示依据已变化；下一轮复核后保存新结果。新结果是否自动成为当前判断，按 AD03 与更新模块统一，不能从“任务完成”直接推定已经重算、采用或结案。

## 4. AD01–AD06当前规则

核心统一下列规则，不重新打开已确认产品规则，也不增加调度。接口复用既有核心，DTO、Swagger及真实HTTP保存读取已单独验收，不另做一套采用规则。

| 编号 | 需明确的内容 | 当前建议与职责 |
| --- | --- | --- |
| AD01 采用资格 | completed/whole_case基础调查，accepted且有模型结论，当前范围/完整输入新鲜度，全员有效结论覆盖 | uncertain／partial本身可接受，原待核/限制保留；未覆盖、过时、Q/局部结果不允许人工覆盖全案。本地核心已实施 |
| AD02 未完任务提示 | not_started/in_progress人工任务；pending_update/running/unknown Run | 预览列出并要求acknowledge_pending_work，提交时重算预览；任务或Run变化使旧摘要失效，本地已验 |
| AD03 人工选择与后续结果 | 在途旧Run不能覆盖较新人工采用；之后明确启动的新Run按原资格自动更新 | 沿用自动发布时间规则，不引入永久人工锁定；两种顺序已有本地PG证据 |
| AD04 反馈与结案后待办 | 有效反馈何时标旧结论过时、何时自动复核；结案后的 pending_update／人工任务如何展示和处理 | 当前显式启动与 D01 保持；自动接续归现有更新／流式 change。未来调度需要识别已结案案件，不能因保存反馈或采用结果自行重开 |
| AD05 同步修改与重试 | 核心用预览摘要检测变化，并在Case锁内核资格/写入；幂等先返回原回执 | 相同operation_key换目标或理由拒绝；重试旧成功请求不会把当前判断回滚。同案事务及直接变化/重试已验，未做并发矩阵 |
| AD06 输入输出交接 | 内部ResultAdoptionRequest为operation_key、expected_review_token、reason及acknowledge_pending_work；预览及历史DTO见核心合同 | HTTP已适配preview_result_adoption/adopt_result/read_assessment_history；E21正式请求已替换旧501占位体，字段与示例见Swagger |

## 5. 模块交接边界与后续验收

调查模块负责结果资格、当前判断及采用历史、运行竞争、新鲜度、任务与后续调度的业务规则；对外 HTTP 模块位于 `services/api/investigation_http/`，只通过用例端口接入已确定能力，不为实现采用而调用本机 HTTP，也不在路由内操纵内部步骤。现有数据库对象和告警交接合同保持；若核心确需迁移，另按对应 OpenSpec 说明，本文不预建表。

相关问题登记为[问题清单 Q02](current-issues.md)，接口顺序见[HTTP 实施计划](http-implementation-plan-20261112.md)。核心和HTTP接入均已完成，复用核心资格/存取证据并补HTTP直接读回，不重跑模型或核心矩阵。已结案Case须先显式重开再采用，采用本身不结案/重开；结案沿原D01实现。

本轮复用既有表，无表/列/迁移或告警字段变化。E21/E63/E64已随独立HTTP发布，当前64操作/62实现/2问答预留501；质量NOT_PASSED和流式后置不核销。独立审计及原始回执见[本批证据](../operations/evidence/case-result-adoption-20261113-01/README.md)。
