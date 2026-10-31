# 服务账号归档与上传，验证缺口和来源边界：逐步测试记录

数据：已有模拟案例。批次`INVHTTP-20261028-01`，通过常驻18000/18010真实HTTP与API Key执行。

流程判定：**通过**。Case `183c059b-2413-4d24-a4aa-dcebe3ad1e55`；来源事件`8db5aafa-011a-47db-9beb-9b16a6f97a1d`。

## 本例为什么这样走

本例从“归档”和“上传”两条已有告警直接建Case，要判断告警主张的行为能否得到进程/网络证据支持，以及二者是否只能算共同背景。选择告警入口是为了验证不必先从事件入口建案；它们原有的事件归属仍保留。

**业务主线：选择两条告警 → 直接建Case → 预览材料 → 调查两名成员 → 看查询缺口与关联依据 → 手动刷新原事件概况。**

| 阶段（对应下方HTTP序号） | 谁触发 / 输入 → 实际输出 | 为什么走到这里、下一步看什么 |
|---|---|---|
| 了解来源：1–5 | 读取两条告警、原事件及已有分诊/调查上下文 | 确认来源信息与不同分诊判断；这些判断仍是待核材料 |
| 从告警建案：6 | source.type=alerts、两条alert_ids → Case `183c059b…`及来源事件关联 | 证明从告警也能进入统一Case调查；不需要另外复制一套事件调查 |
| 预览：10 | 两名成员、DEMO-DATA-13、2026-10-25 03:28–03:37 UTC及问题 → 材料、可用Tools、限制 | 固定本次范围，随后发起一次调查；这一步不调用模型 |
| 主调查：11 | 上述范围及operation_key → Run `ebe2c07b…`；2次模型、2次Tool | 模型先要求进程/网络查询，系统返回两项成功空结果，再由模型给出partial报告 |
| 看结论及依据：12–34 | 读取报告、内部步骤、A/T/E证据、三个executions索引 | 看关联依据和未决问题；两项空结果不足以证明归档/外传已发生，也不足以证明安全 |
| 事件概况：36–37 | 人工refresh并读回 → 引用已有调查的事件AI概况 | 把Case的进展摘要展示回事件；不在事件内重新执行深度调查 |
| 历史与关联：38–39 | 读取Case历史和事件关联列表 | 确认后续从原事件仍能找到这个由告警入口建立的Case/Run |

第7步重复建案、第8–9步读取Case/关联、第35步重复主请求、第40–41步比较源告警，均为测试核对动作。此例没有追加问题Run；不存在因空结果而自动扩大窗口或启动新调查的步骤。

**阅读标号：**下面的HTTP序号用于对应原始请求；下节“内部账本步骤”属于一次investigate内部的自动执行。一次内部动作可能在后面被GET读回，不能按GET出现的位置判断动作发生时间。正文文件链接仅用于核对当时保存的输入输出。

## 一次调查内部为什么进入下一步

本例问题明确要求先查process_activity和network_connections。系统把这些工具的定义交给模型；只有收到原生tool_calls后才分派查询。下面列出实际发生的自动步骤；点“记录”读取的是保存内容。

### 主调查的内部步骤

| 内部账本步骤 | 为什么发生 / 输入输出如何承接 | 原始记录 |
|---|---|---|
| 1：已固定Case成员与调查范围 | 固定本Run成员、窗口及材料；把告警A和已有分诊T交给模型。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/015-main-step-1.response.txt) |
| 2：分析第1轮：准备调用模型 | 首次把问题、材料和可用Tool定义发送给模型；接下来保存模型返回的调用或答案。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/016-main-step-2.response.txt) |
| 3：分析第1轮：模型已返回 | 模型按本例问题返回原生调用process_activity、network_connections；系统据此校验并分派下面的Tool步骤。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/017-main-step-3.response.txt) |
| 4：准备查询process_activity | 收到模型的调用要求后，记录工具及参数，再沿固定Case/主机/窗口执行；本链接回看的是已保存请求。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/018-main-step-4.response.txt) |
| 5：process_activity已返回，来源可用=True | 保存实际返回、可用性及行数并分配E编号，再把结果交回模型；0行与来源不可用须区分。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/019-main-step-5.response.txt) |
| 6：准备查询network_connections | 收到模型的调用要求后，记录工具及参数，再沿固定Case/主机/窗口执行；本链接回看的是已保存请求。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/020-main-step-6.response.txt) |
| 7：network_connections已返回，来源可用=True | 保存实际返回、可用性及行数并分配E编号，再把结果交回模型；0行与来源不可用须区分。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/021-main-step-7.response.txt) |
| 8：分析第2轮：准备调用模型 | 把实际Tool返回加入模型输入，请模型继续分析；不是再次执行刚才的查询。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/022-main-step-8.response.txt) |
| 9：分析第2轮：模型已返回 | 模型返回候选结论；系统随后校验字段、成员和引用，返回答案不代表已经采纳。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/023-main-step-9.response.txt) |
| 10：调查已停止：analysis_complete | 记录最终停止状态及报告/缺口；analysis_complete表示本次执行结束，partial仍保留证据不足；其他停止原因见本例结果。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/024-main-step-10.response.txt) |

## 实际调查结果

| 执行 | Run | 状态/停止原因 | 完整度 | 模型/Tool | 已知tokens |
|---|---|---|---|---:|---:|
| main | `ebe2c07b-cc2d-5062-be00-cd73fccfc9fa` | completed / analysis_complete | partial | 2/2 | 8061 |

### main 输出

针对警案例 INVHTTP-20261028-01 archive-upload 的告警 A1、A2，告警内容描述在主机 DEMO-DATA-13 上涉及用户 demo.export 执行批量文件读取并生成归档操作。告警 A1 被标记为 true_positive，断言为未经授权的活动；告警 A2 被标记为 false_positive，断言为模拟演示行为。当前运行中，使用 process_activity 和 network_connections 针对主机 DEMO-DATA-13 进行了查询，但均返回空结果，无实际可用作进一步分析的证据记录。目前无进程执行的确切时间线、文件路径、账号哈希、连接记录等数据，无法确认活动性质。

[完整Markdown报告原文](archive-upload-main-report.md)

选定成员：`6373220a-2f25-541e-ab89-9c3a2e611140, 4eb06dee-c5a0-5f08-ace7-08caa2952db5`。
成员覆盖：`{"selected_count": 2, "read_count": 2, "addressed_count": 0, "unresolved_count": 2, "not_assessed_count": 0, "source_unavailable_count": 0}`。
时间线2项，关联2项，未决问题3项。

| Tool证据 | 参数 | available / 条数 | 复用来源 |
|---|---|---|---|
| E1 / process_activity | `{"hostname": "DEMO-DATA-13", "limit": 20}` | True / 0 | `null` |
| E2 / network_connections | `{"hostname": "DEMO-DATA-13", "limit": 20}` | True / 0 | `null` |

## 检查结果

全部本例流程检查通过。该判定不等同于模型业务结论质量全面通过。

报告保留分诊判断之间的差异，将两条查询空结果作为缺口，未据此确认恶意归档或外传。本例用于证明流程和材料边界，缺少规范化遥测仍限制业务判断。

## 每一步请求与实际返回

这是测试脚本的请求顺序；“用途与跳转依据”说明每行是在发起业务、读取过程还是做测试核对。第7步等同key重复请求仅为本批核对，不是用户每次必做的流程。

下面的请求JSON在发送前写入，因此保留pending标记；最终HTTP状态和检查结果以[本例summary](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/summary.json)为准。响应文件是调用脚本去掉其附加换行后的HTTP原始正文。

| HTTP序号 | 用途与跳转依据 | 方法与路径 | HTTP | 输入 | 实际返回 |
|---:|---|---|---:|---|---|
| 1 | 读取来源：确认第1条告警内容；下一步据此选Case成员。 | `GET /api/v1/alerts/6373220a-2f25-541e-ab89-9c3a2e611140` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/001-source-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/001-source-0.response.txt) |
| 2 | 读取来源：确认第2条告警内容；下一步据此选Case成员。 | `GET /api/v1/alerts/4eb06dee-c5a0-5f08-ace7-08caa2952db5` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/002-source-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/002-source-1.response.txt) |
| 3 | 读取事件：确认原分组成员、分诊汇总及旧概况；没有重新分组/生成概况。 | `GET /api/v2/investigation/incidents/8db5aafa-011a-47db-9beb-9b16a6f97a1d` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/003-incident-before.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/003-incident-before.response.txt) |
| 4 | 读取告警调查入口：查看已有来源/Case/Run关联；为选择调查范围提供上下文。 | `GET /api/v2/investigation/alerts/6373220a-2f25-541e-ab89-9c3a2e611140/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/004-alert-context-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/004-alert-context-0.response.txt) |
| 5 | 读取告警调查入口：查看已有来源/Case/Run关联；为选择调查范围提供上下文。 | `GET /api/v2/investigation/alerts/4eb06dee-c5a0-5f08-ace7-08caa2952db5/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/005-alert-context-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/005-alert-context-1.response.txt) |
| 6 | 人工业务动作：按请求的成员和来源建Case；输出Case ID供后续预览/调查，尚不调用模型。 | `POST /api/v2/investigation/case-links` | 201 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/006-create-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/006-create-case.response.txt) |
| 7 | 仅测试：相同operation_key读回同一建案回执；不再建第二个Case。 | `POST /api/v2/investigation/case-links` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/007-create-repeat.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/007-create-repeat.response.txt) |
| 8 | 回执链接核对：沿case_url查看同一Case；确认对象可读取，不启动调查。 | `GET /api/v1/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/008-case-core-link.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/008-case-core-link.response.txt) |
| 9 | 关联核对：按原事件查建案关联，确认从事件可以找到刚建的Case。 | `GET /api/v2/investigation/case-links?incident_id=8db5aafa-011a-47db-9beb-9b16a6f97a1d` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/009-case-links.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/009-case-links.response.txt) |
| 10 | 可选材料预览：返回本次context/tools/limits；确认范围后才另发investigate，不调用模型。 | `POST /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/010-preview.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/010-preview.response.txt) |
| 11 | 人工业务动作：一次请求发起主Run；模型/Tool循环在内部自动执行，返回保存结果及读取链接。 | `POST /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/011-main.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/011-main.response.txt) |
| 12 | 沿result_url读回同一Run的状态、范围和结构化结果；不重新分析。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/012-main-result.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/012-main-result.response.txt) |
| 13 | 沿report_url查看/下载同一Run的Markdown，便于阅读结论；不是第二份模型输出。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/report` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/013-main-report.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/013-main-report.response.txt) |
| 14 | 沿steps_url列出已记录的模型/Tool步骤；取得detail_url后才能逐条回看过程。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps?limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/014-main-steps.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/014-main-steps.response.txt) |
| 15 | 回看主调查内部步骤1：已固定Case成员与调查范围；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/015-main-step-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/015-main-step-1.response.txt) |
| 16 | 回看主调查内部步骤2：分析第1轮：准备调用模型；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/016-main-step-2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/016-main-step-2.response.txt) |
| 17 | 回看主调查内部步骤3：分析第1轮：模型已返回；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/3` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/017-main-step-3.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/017-main-step-3.response.txt) |
| 18 | 回看主调查内部步骤4：准备查询process_activity；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/4` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/018-main-step-4.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/018-main-step-4.response.txt) |
| 19 | 回看主调查内部步骤5：process_activity已返回，来源可用=True；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/5` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/019-main-step-5.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/019-main-step-5.response.txt) |
| 20 | 回看主调查内部步骤6：准备查询network_connections；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/6` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/020-main-step-6.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/020-main-step-6.response.txt) |
| 21 | 回看主调查内部步骤7：network_connections已返回，来源可用=True；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/7` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/021-main-step-7.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/021-main-step-7.response.txt) |
| 22 | 回看主调查内部步骤8：分析第2轮：准备调用模型；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/8` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/022-main-step-8.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/022-main-step-8.response.txt) |
| 23 | 回看主调查内部步骤9：分析第2轮：模型已返回；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/9` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/023-main-step-9.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/023-main-step-9.response.txt) |
| 24 | 回看主调查内部步骤10：调查已停止：analysis_complete；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/10` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/024-main-step-10.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/024-main-step-10.response.txt) |
| 25 | 沿evidence_url列出本Run证据及detail_url，供按报告引用追溯。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/025-main-evidence-list.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/025-main-evidence-list.response.txt) |
| 26 | 按编号A1查看来源告警材料；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/026-main-evidence-A1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/026-main-evidence-A1.response.txt) |
| 27 | 按编号T1查看已有分诊判断；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/T1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/027-main-evidence-T1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/027-main-evidence-T1.response.txt) |
| 28 | 按编号A2查看来源告警材料；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/028-main-evidence-A2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/028-main-evidence-A2.response.txt) |
| 29 | 按编号T2查看已有分诊判断；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/T2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/029-main-evidence-T2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/029-main-evidence-T2.response.txt) |
| 30 | 按编号E1查看实际Tool结果与tool_trace；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/E1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/030-main-evidence-E1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/030-main-evidence-E1.response.txt) |
| 31 | 按编号E2查看实际Tool结果与tool_trace；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/E2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/031-main-evidence-E2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/031-main-evidence-E2.response.txt) |
| 32 | 查找入口核对：按告警筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?alert_id=6373220a-2f25-541e-ab89-9c3a2e611140&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/032-main-index-alert.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/032-main-index-alert.response.txt) |
| 33 | 查找入口核对：按事件筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?incident_id=8db5aafa-011a-47db-9beb-9b16a6f97a1d&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/033-main-index-incident.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/033-main-index-incident.response.txt) |
| 34 | 查找入口核对：按Case筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?case_id=183c059b-2413-4d24-a4aa-dcebe3ad1e55&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/034-main-index-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/034-main-index-case.response.txt) |
| 35 | 仅测试：按原operation_key读回同一主Run，不额外调用模型或Tool。 | `POST /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/035-main-repeat.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/035-main-repeat.response.txt) |
| 36 | 人工业务动作：手动刷新事件摘要，引用已有调查结果；会调用摘要模型，不重跑Case调查。 | `POST /api/v2/investigation/incidents/8db5aafa-011a-47db-9beb-9b16a6f97a1d/overview/refresh?include_investigations=true` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/036-overview-refresh.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/036-overview-refresh.response.txt) |
| 37 | 展示读回：查看刚保存的事件概况和来源Run；普通GET不会再生成概况。 | `GET /api/v2/investigation/incidents/8db5aafa-011a-47db-9beb-9b16a6f97a1d` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/037-overview-readback.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/037-overview-readback.response.txt) |
| 38 | 历史入口：列出这个Case的Run，供以后定位主调查/追加；不创建Run。 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/038-case-history.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/038-case-history.response.txt) |
| 39 | 事件入口：列出关联Case/Run和范围，让事件层展示调查进展；不执行分析。 | `GET /api/v2/investigation/incidents/8db5aafa-011a-47db-9beb-9b16a6f97a1d/investigations` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/039-incident-investigations.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/039-incident-investigations.response.txt) |
| 40 | 测试核对：重读原告警，与开始时比较关键字段；不会再分诊。 | `GET /api/v1/alerts/6373220a-2f25-541e-ab89-9c3a2e611140` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/040-source-after-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/040-source-after-0.response.txt) |
| 41 | 测试核对：重读原告警，与开始时比较关键字段；不会再分诊。 | `GET /api/v1/alerts/4eb06dee-c5a0-5f08-ace7-08caa2952db5` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/041-source-after-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/041-source-after-1.response.txt) |

## 逐项判定

| 检查 | 结果 |
|---|---|
| create: same key returns receipt | 通过 |
| preview: Case members and selection distinct | 通过 |
| main: result readback identical | 通过 |
| main: downloaded report identical | 通过 |
| main: Tool exchange links E1 | 通过 |
| main: Tool exchange links E2 | 通过 |
| main: alert index agrees | 通过 |
| main: incident index agrees | 通过 |
| main: case index agrees | 通过 |
| main: valid conclusion completed | 通过 |
| main: member coverage count | 通过 |
| main: selected members assessed or unresolved | 通过 |
| main: requested native Tools executed | 通过 |
| main: Tools available within host scope | 通过 |
| main: expected source record count | 通过 |
| main: repeated operation reads original result | 通过 |
| overview: generated and saved | 通过 |
| overview: new Run cited | 通过 |
| overview: GET preserves text and source metadata | 通过 |
| source Alert unchanged: 6373220a-2f25-541e-ab89-9c3a2e611140 | 通过 |
| source Alert unchanged: 4eb06dee-c5a0-5f08-ace7-08caa2952db5 | 通过 |
