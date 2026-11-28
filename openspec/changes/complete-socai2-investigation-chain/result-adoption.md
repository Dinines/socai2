# 固定调查结果的人工采用

2026-11-13，承接主任务3.12及[Q02 / AD01–AD06](../../../docs/investigation/result-adoption-and-pending-work.md)，先完成调查核心的预览、采用、保存及读取，HTTP模块随后接入。本项属于固定范围结果操作，不增加模型调用、任务队列或流式更新。

## 规则与取舍

- 采用只面向本案已保存的基础调查Result：来源Run必须completed/whole_case，Result必须accepted、有非空模型结论，冻结范围/成员和当前Case一致，完整输入新鲜度必须current。显式unresolved/uncertain及partial交付不独立阻止采用，但每个当前成员都必须有有效结论覆盖；not_analyzed/excluded或缺失成员不能靠人工选择变成全案结论。Q保存、局部探索、过时输入不在本项开放。
- 预览展示原判断、新Result全文中的结论/待核/限制、各成员交付与覆盖、未覆盖成员、新鲜度及拒绝原因；同时列出未完人工任务（not_started/in_progress）和未结束Run（pending_update/running/unknown）。这些事实均由程序读取，不交给模型生成。
- 提交必须提供非空采用理由及预览摘要；有未完工作须明确知晓。程序在Case锁内重新构造预览，摘要不一致拒绝并要求重新查看，避免预览之后当前判断、成员、任务或运行状态变化时盲写。摘要只作版本校验，不替代资格判断或用户身份核验。
- 采用在同一事务新增case_assessments、来源及真实覆盖，更新Case当前指针，并记录实际操作者、理由和幂等活动回执。保留Result模型原文、origin、validation及所有旧判断；同一请求重试返回原回执，不重复采用。同operation_key改变目标/理由报冲突。
- 采用不完成/取消任务、不终止/启动Run、不结案或重开。已结案Case须先按既有独立操作重开，再采用。采用后新有效H反馈使旧判断stale，仍由既有新鲜度读取呈现，不自动重算。
- 自动采用规则保持：早于人工采用启动的在途Run不能覆盖较新的判断；人工采用之后明确启动的新Run仍按原资格自动更新。不新增永久人工锁定。自动采用原有partial覆盖口径不在本项改动。

## 接线与存储

CaseService新增内部读取预览、采用和判断历史用例，独立HTTP仅在后续适配用例。E21现有501及其DTO保持，本项不修改HTTP操作或Swagger。复用case_assessments、case_assessment_sources、case_assessment_members、activities/activity_targets，不新增表/列/迁移，不修改告警字段和原始结果。采用来源仍为model，actor/adopted_by表达人工选择，不把人工采用伪装成人工生成或质量通过。

## 直接验收

在明确的本机隔离PG中新建一个合成Case，使用程序构造的固定Result完成预览→采用→Case/Result/判断历史/活动读回；不调用模型、厂商、HTTP或生产环境。沿这条流程核对未完任务/Run保持、重复提交无重复写、变化后的旧预览拒绝、部分覆盖/过时/未完成来源拒绝，以及旧Run与随后显式启动Run的自动采用顺序。后续H仅验证新鲜度，不启动调查。复用既有结案检查，不重跑结案、全仓或模型质量矩阵。

先完成核心实现及这次直接存取证据，再由未参与实现者做限定结束审计。主调查31/41、质量NOT_PASSED及HTTP未实现状态均不由本项自动核销。

## 实施结果

核心本地实现、[一条单Case隔离PG流程](../../../docs/operations/evidence/case-result-adoption-20261113-01/README.md)及[独立限定审计](../../../docs/operations/evidence/case-result-adoption-20261113-01/audit.md)已完成。初次沙箱连接失败无业务执行；随后人工采用已保存，验收错误假定Case初始状态导致停止，原失败保持；从同Case回执继续余项后通过，没有重启旧Run或重复生成结果。HTTP适配及部署仍待完成，主任务不勾选。

## 后续：HTTP接入

本轮继续3.12，直接将已验核心接到独立HTTP端口，业务规则不复制到路由。当前正式服务仍按PROGRESS记录；本轮先在独立本机候选完成接口、直接存取及交接，不启动模型或流式。

| 操作 | 合同 |
| --- | --- |
| E21 `POST /cases/{case_id}/results/{result_id}/adopt` | 替换旧501占位。body为operation_key、expected_review_token、非空reason及默认false的acknowledge_pending_work；返回采用回执。旧operation_key/expected_scope_revision占位body返回422，不静默跳过预览/理由 |
| E63 `GET /cases/{case_id}/results/{result_id}/adoption-preview` | 返回核心的原/新判断、实际覆盖、待核/限制、新鲜度、未完工作、资格/拒绝原因及review_token；读取不写入 |
| E64 `GET /cases/{case_id}/assessments` | limit=20（1–100）、offset=0（非负）；返回判断版本历史、源Result、覆盖、采用人/理由及下一页。原`/history`继续作为Run/Result历史，不改含义 |

路径前缀为`/api/v1/socai2`。GET沿用cases:read和现有读取开关/只读连接；POST沿用cases:write、Case写开关和认证用户actor/tenant。404表示目标不属于本Case/租户或不存在；409表示预览变化、不符合资格、未确认未完工作或幂等冲突，使用核心稳定错误码；422表示请求合同错误。E19/E20仍501，Q/局部结果不能借E21变成全案判断。

直接验证只补：候选真实TCP预览→采用→Case/Result/历史/活动读回及SQL核对，采用前未完任务/待启动Run保持，幂等重试、预览变化及错误body拒绝。用一个新合成Case和一份程序Result，不重跑上批四Run的自动覆盖/H矩阵。复用既有认证/数据库配置；原61个非E21操作和现存告警Schema应保持。更新候选OpenAPI/交接，不把候选通过写成生产已发布；限定结束审计后按主change收口。

## SpiritHub 采用弹窗合同预审 2026-11-28

本轮只做源码与既有合同对照。主线依据本机 `origin/main` `1cd0ff1fd9f7d23c15503c9ef0f6f66812dda449`。原生以当前调查 HTTP 路由、合同源码和既有 OpenAPI 快照交叉核对。等前端概览组合完成，再安排平台合同和采用弹窗配对接线。

| 方法 | 8181 普通平台注册、桥接、公开合同与类型 | main 与原生 |
| --- | --- | --- |
| E63 `GET /api/v1/socai2/cases/{case_id}/results/{result_id}/adoption-preview` | 四层均缺。当前弹窗从结果详情与案件成员自行推算覆盖、局部范围和可采用性。 | 原生已有 `ResultAdoptionPreview`。main 已有 `socai2_adoption_preview` 和 `Socai2ResultAdoptionPreview`。按 `case_id` 与 `result_id` 读取，无查询参数。 |
| E21 `POST /api/v1/socai2/cases/{case_id}/results/{result_id}/adopt` | 注册已有。桥接、公开及类型仍用 `Socai2AdoptCaseAIResult` 和旧 `Socai2AdoptionReceipt`。弹窗发送旧 `expected_scope_revision`、`expected_assessment_id`、`confirm_partial`。 | 原生已有 `ResultAdoptionRequest`、`ResultAdoptionReceipt`。main 已有对应的 `Socai2ResultAdoptionRequest`、`Socai2ResultAdoptionReceipt`。沿用 `socai2_E21` 及正常 Case 更新授权。 |
| E03 `GET /api/v1/socai2/cases/{case_id}` | 已有正常路由、合同和生成类型，包含 `case.current_assessment_id` 及 `current_assessment`。 | 继续用现有 E03 读取当前指针和判断。 |
| E64 `GET /api/v1/socai2/cases/{case_id}/assessments` | 四层均缺。原有 `/history` 用途是结果及活动查阅，现有采用流程缺判断版本读回。 | 原生已有 `AssessmentHistory`。main 已有 `socai2_assessments` 和 `Socai2AssessmentHistory`。分页入参为 `limit`、`offset`，响应为 `items`、`total`、`next_offset`。 |

源码入口见 [当前弹窗](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/AdoptResultDialog.tsx:12)、[旧 E21 封装](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/workbench-api.ts:34)、[普通注册](/Users/lychee/Projects/SpiritHub-web-8181/backend/src/spirithub/api/routes/socai2.py:84)、[原生 E63/E21/E64](/Users/lychee/Documents/project/socai2/services/api/investigation_http/external_routes/cases.py:236)、[原生类型](/Users/lychee/Documents/project/socai2/services/api/app/socai2/case_adoption_contracts.py:34) 和 [正式调用指南](/Users/lychee/Documents/project/socai2/docs/integration/result-adoption-http.md:7)。

### 配对接线的最小范围

1. 以统筹选定的 main 整合候选为准，保留 main 的 E63、E21、E64 路由、成功响应、现有 Case 读取及更新权限和桥接错误语义。若需将现行 8181 来源作为候选，只纳入本领域的两个 GET、E21 请求和响应投影及其依赖。E63、E64 沿用普通 GET 机制。E03 原有读取继续使用。
2. 收口生成类型只涉及 `socai2_adoption_preview`、`socai2_E21`、`socai2_assessments` 的方法及必需引用。8181 相对 main 缺 `Socai2ResultAdoptionPreview`、`Socai2ResultAdoptionRequest`、`Socai2ResultAdoptionReceipt`、`Socai2AssessmentHistory`、`Socai2AdoptedAssessment`、`Socai2AssessmentSourceReference`。main 的原生成功及请求递归闭包已核同形。8181 的共享 `Socai2ResultView`、`Socai2RunView` 及其 `EvidenceRef`、`Finding`、`Impact`、`Question`、`Recommendation`、`Scope`、`Target` 也有版本差异。合入以 main 真实闭包为源逐项处理共享引用，生成范围以保留当前概览消费者为约束。
3. 弹窗可继续使用已有结果列表选择候选。选定后从同一 Case/Result 的 E63 读取 `current_assessment`、`candidate`、`source_run`、`members`、`uncovered_alert_ids`、`outside_alert_ids`、`input_freshness` 和未完工作。由 `can_adopt`、`refusal_reasons` 和 `requires_pending_work_acknowledgement` 控制提交与确认。E21 发送 `operation_key`、从预览 `review_token` 原样取得的 `expected_review_token`、去除首尾空白后长度为 1–4000 的 `reason`，以及需要时的 `acknowledge_pending_work`。收到 `result_adoption_preview_changed` 时保留理由并重新预览，用户复核后才再次提交。成功回执为 `case_id`、`result_id`、`assessment_id`、`previous_assessment_id`、`assessment_revision`、`case_row_version`。读 E03 的当前指针，并在 E64 按回执 `assessment_id` 和 `assessment_revision` 核对判断版本。相同意图的受理重放仍按原键与原请求体走已有规则。

### 可复用的直接检查

- 复用原生采用用例检查失效预览、未完工作确认、同请求重放和判断版本读回。它证明调查核心合同，平台接线仍需对应普通路由验证。 [原生采用用例](/Users/lychee/Documents/project/socai2/services/api/tests/test_socai2_case_adoption_pg.py:24)
- 复用普通路由 `case_proxy` 及既有原生错误映射用例，核 E63 的 GET、E21 的原 token 与请求体、E64 的 offset 透传及平台错误类型。对 E03 保留现有 Case 读取断言。 [平台替身与错误映射](/Users/lychee/Projects/SpiritHub-web-8181/backend/tests/soc/test_bridge.py:191)
- 延用 `AdoptResultDialog.test.tsx` 的冲突保留理由场景，把局部覆盖模拟改为 E63 正式可采用和未完确认字段。定向核对预览拒绝时不提交、冲突时刷新 E63、成功后 E03/E64 读取。 [现有弹窗用例](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/AdoptResultDialog.test.tsx:10)

本次记录为预审和计划，现行源码及生成类型继续供前端概览使用。
