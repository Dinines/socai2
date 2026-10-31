# Office启动PowerShell后外联：逐步测试记录

数据：已有模拟案例。批次`INVHTTP-20261028-01`，通过常驻18000/18010真实HTTP与API Key执行。

流程判定：**未全部通过**。Case `be4aeda2-a89b-47e6-a6f9-285b1a7e8723`；来源事件`7bde0c0b-0d18-4abc-9382-9752f2ae5e98`。

## 本例为什么这样走

本例要回答：同一主机 DEMO-FIN-11 的“Office启动隐藏PowerShell”和“脚本外联”是否有来源证据支持、二者能关联到什么程度。先纳入第一条告警，再把第二条加入同一Case，是为了覆盖“已有Case追加成员”；正常业务也可一次选入两条。

**业务主线：看两条告警 → 建Case并补入成员 → 固定两成员与时间窗 → 发起主调查 → 看证据不足的报告 → 手动刷新事件概况 → 用历史报告追加问题。** 最后一次追加失败，如实保留。

| 阶段（对应下方HTTP序号） | 谁触发 / 输入 → 实际输出 | 为什么走到这里、下一步看什么 |
|---|---|---|
| 了解材料：1–5 | 脚本代替用户读取两条告警、分组事件和已有调查上下文；尚未产生本轮Run | 先确认待查对象、已有分诊；据此明确选择Case成员 |
| 建案与补成员：6、8 | 人工明确选择；先创建含第一条告警的Case，再把第二条加入；输出同一个Case ID | 后续深入分析在这个Case中进行。第7步仅核对重复建案请求返回原回执 |
| 预览：11 | 两名成员、2026-10-25 03:28–03:37 UTC及问题 → context/tools/limits | 确认本次材料和工具范围；预览本身不调用模型，也不要求必须先预览才能调查 |
| 主调查：12 | 同一范围加operation_key → Run `218257e8…`；内部2次模型、2次Tool | 问题明确要求查进程和网络；两个Tool都成功返回0条。模型形成partial报告，不能据空结果断定安全 |
| 查看与追溯：13–35 | 利用该Run的结果、报告、步骤、证据、索引链接读取保存内容 | 想知道某个判断凭什么，就从报告引用定位证据，再看实际Tool参数/返回。此阶段不产生新的分析 |
| 回到事件展示：37–38 | 人工手动refresh，include_investigations=true → 引用主调查的已保存AI概况 | 让事件展示本案进展；独立调用一次摘要模型。调查结束不会自动刷新这段概况 |
| 追加新问题：39 | 指定previous_run_id=`218257e8…`，要求沿用H1说明缺口、不重复查询 → 新Run `5d6f28ea…` | 这是另一次明确请求，不是报告链接自动触发；首次回答引用错误，纠正前额度不足，最终failed |
| 查看追加影响：40–61 | 读取失败说明、H1、旧报告和事件概况 | 确认旧报告还在、概况文字未被改写且已标旧；没有在失败后自动重跑 |

第9–10步读取新Case及关联记录，第36步用相同operation_key读回主Run，第62–63步比较原告警。这些是测试核对动作，不增加业务阶段。

例如，[主报告](office-powershell-main-report.md)引用E1说明进程证据缺失 → [E1证据详情](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/031-main-evidence-E1.response.txt)说明process_activity返回0条 → 其中tool_trace分别指向[查询请求（内部步骤4）](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/019-main-step-4.response.txt)和[查询返回（内部步骤5）](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/020-main-step-5.response.txt)。这样跳转是为追溯“缺少进程记录”这一判断的依据；它们都是同一次主调查留下的记录。

**阅读标号：**下面的HTTP序号用于对应原始请求；下节“内部账本步骤”属于一次investigate内部的自动执行。一次内部动作可能在后面被GET读回，不能按GET出现的位置判断动作发生时间。正文文件链接仅用于核对当时保存的输入输出。

## 一次调查内部为什么进入下一步

主调查的问题明确要求先查process_activity和network_connections；追加问题则要求沿用H1，不再查询。系统把可用工具的定义交给模型；只有收到原生tool_calls后才分派查询。下面列出实际发生的自动步骤；点“记录”读取的是保存内容。

### 主调查的内部步骤

| 内部账本步骤 | 为什么发生 / 输入输出如何承接 | 原始记录 |
|---|---|---|
| 1：已固定Case成员与调查范围 | 固定本Run成员、窗口及材料；把告警A和已有分诊T交给模型。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/016-main-step-1.response.txt) |
| 2：分析第1轮：准备调用模型 | 首次把问题、材料和可用Tool定义发送给模型；接下来保存模型返回的调用或答案。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/017-main-step-2.response.txt) |
| 3：分析第1轮：模型已返回 | 模型按本例问题返回原生调用process_activity、network_connections；系统据此校验并分派下面的Tool步骤。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/018-main-step-3.response.txt) |
| 4：准备查询process_activity | 收到模型的调用要求后，记录工具及参数，再沿固定Case/主机/窗口执行；本链接回看的是已保存请求。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/019-main-step-4.response.txt) |
| 5：process_activity已返回，来源可用=True | 保存实际返回、可用性及行数并分配E编号，再把结果交回模型；0行与来源不可用须区分。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/020-main-step-5.response.txt) |
| 6：准备查询network_connections | 收到模型的调用要求后，记录工具及参数，再沿固定Case/主机/窗口执行；本链接回看的是已保存请求。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/021-main-step-6.response.txt) |
| 7：network_connections已返回，来源可用=True | 保存实际返回、可用性及行数并分配E编号，再把结果交回模型；0行与来源不可用须区分。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/022-main-step-7.response.txt) |
| 8：分析第2轮：准备调用模型 | 把实际Tool返回加入模型输入，请模型继续分析；不是再次执行刚才的查询。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/023-main-step-8.response.txt) |
| 9：分析第2轮：模型已返回 | 模型返回候选结论；系统随后校验字段、成员和引用，返回答案不代表已经采纳。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/024-main-step-9.response.txt) |
| 10：调查已停止：analysis_complete | 记录最终停止状态及报告/缺口；analysis_complete表示本次执行结束，partial仍保留证据不足；其他停止原因见本例结果。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/025-main-step-10.response.txt) |

### 追加问题的内部步骤

| 内部账本步骤 | 为什么发生 / 输入输出如何承接 | 原始记录 |
|---|---|---|
| 1：已固定Case成员与调查范围 | 固定本Run成员、窗口及材料；加入H1历史报告，供回答追加问题。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/043-followup-step-1.response.txt) |
| 2：分析第1轮：准备调用模型 | 首次把问题、材料和可用Tool定义发送给模型；接下来保存模型返回的调用或答案。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/044-followup-step-2.response.txt) |
| 3：分析第1轮：模型已返回 | 模型返回候选结论；系统随后校验字段、成员和引用，返回答案不代表已经采纳。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/045-followup-step-3.response.txt) |
| 4：模型结论未通过格式或引用校验 | 候选结论被拒：`unknown_evidence_reference`；系统仅在剩余额度允许时纠正一次，不把原答当报告结论。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/046-followup-step-4.response.txt) |
| 5：调查已停止：input_or_token_limit | 上一步原答被拒；纠正请求预检需要19137、剩余17018，因此未再调用模型，保存failed状态及缺口。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/047-followup-step-5.response.txt) |

## 实际调查结果

| 执行 | Run | 状态/停止原因 | 完整度 | 模型/Tool | 已知tokens |
|---|---|---|---|---:|---:|
| main | `218257e8-0611-5a59-b13d-6d86f06a9413` | completed / analysis_complete | partial | 2/2 | 8269 |
| followup | `5d6f28ea-d7f4-572e-b2e5-5c0013475396` | failed / input_or_token_limit | partial | 1/0 | 6982 |

### main 输出

告警 A1 和 A2 均指向主机 DEMO-FIN-11 上的可疑活动，涉及 Office 启动隐藏 PowerShell 和脚本进程向 198.51.100.41 建立连接。然而，工具查询（E1, E2）在告警指定的时间窗口内均未返回任何进程或网络连接记录。网络锥和记录存在显著的证据缺口：告警主张的具体进程（如 WINWORD.EXE、PowerShell、脚本进程）无法在工具结果中得到验证，且网络连接工具的无结果无法排除历史流失或采集失败。现有材料难以确认攻击是否发生或仅共享上下文。

[完整Markdown报告原文](office-powershell-main-report.md)

选定成员：`4c71eec2-77da-5b81-b68a-72801d55ea24, f7af404b-26a6-5d15-bd6c-3a872bdaf451`。
成员覆盖：`{"selected_count": 2, "read_count": 2, "addressed_count": 0, "unresolved_count": 2, "not_assessed_count": 0, "source_unavailable_count": 0}`。
时间线2项，关联1项，未决问题2项。

| Tool证据 | 参数 | available / 条数 | 复用来源 |
|---|---|---|---|
| E1 / process_activity | `{"hostname": "DEMO-FIN-11", "limit": 20}` | True / 0 | `null` |
| E2 / network_connections | `{"hostname": "DEMO-FIN-11", "limit": 20}` | True / 0 | `null` |

### followup 输出

本次Case调查未形成完整结论，请结合已保存材料和缺口继续处理。

[完整Markdown报告原文](office-powershell-followup-report.md)

选定成员：`4c71eec2-77da-5b81-b68a-72801d55ea24, f7af404b-26a6-5d15-bd6c-3a872bdaf451`。
成员覆盖：`{"selected_count": 2, "read_count": 2, "addressed_count": 0, "unresolved_count": 0, "not_assessed_count": 2, "source_unavailable_count": 0}`。
时间线2项，关联0项，未决问题2项。

| Tool证据 | 参数 | available / 条数 | 复用来源 |
|---|---|---|---|
| 无本次Tool调用 | — | — | — |

## 检查结果

- followup: valid conclusion completed
- followup: selected members assessed or unresolved

主调查及保存/跳转通过。追加首轮引用不存在的证据被拒；准备一次纠错时预检需要19137，剩余17018，超出2119，所以没有第二次模型请求。两个失败检查属于同一停止原因；未评估成员是其后果。旧报告保持，旧概况只标旧。

## 每一步请求与实际返回

这是测试脚本的请求顺序；“用途与跳转依据”说明每行是在发起业务、读取过程还是做测试核对。第7步等同key重复请求仅为本批核对，不是用户每次必做的流程。

下面的请求JSON在发送前写入，因此保留pending标记；最终HTTP状态和检查结果以[本例summary](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/summary.json)为准。响应文件是调用脚本去掉其附加换行后的HTTP原始正文。

| HTTP序号 | 用途与跳转依据 | 方法与路径 | HTTP | 输入 | 实际返回 |
|---:|---|---|---:|---|---|
| 1 | 读取来源：确认第1条告警内容；下一步据此选Case成员。 | `GET /api/v1/alerts/4c71eec2-77da-5b81-b68a-72801d55ea24` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/001-source-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/001-source-0.response.txt) |
| 2 | 读取来源：确认第2条告警内容；下一步据此选Case成员。 | `GET /api/v1/alerts/f7af404b-26a6-5d15-bd6c-3a872bdaf451` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/002-source-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/002-source-1.response.txt) |
| 3 | 读取事件：确认原分组成员、分诊汇总及旧概况；没有重新分组/生成概况。 | `GET /api/v2/investigation/incidents/7bde0c0b-0d18-4abc-9382-9752f2ae5e98` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/003-incident-before.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/003-incident-before.response.txt) |
| 4 | 读取告警调查入口：查看已有来源/Case/Run关联；为选择调查范围提供上下文。 | `GET /api/v2/investigation/alerts/4c71eec2-77da-5b81-b68a-72801d55ea24/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/004-alert-context-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/004-alert-context-0.response.txt) |
| 5 | 读取告警调查入口：查看已有来源/Case/Run关联；为选择调查范围提供上下文。 | `GET /api/v2/investigation/alerts/f7af404b-26a6-5d15-bd6c-3a872bdaf451/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/005-alert-context-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/005-alert-context-1.response.txt) |
| 6 | 人工业务动作：按请求的成员和来源建Case；输出Case ID供后续预览/调查，尚不调用模型。 | `POST /api/v2/investigation/case-links` | 201 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/006-create-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/006-create-case.response.txt) |
| 7 | 仅测试：相同operation_key读回同一建案回执；不再建第二个Case。 | `POST /api/v2/investigation/case-links` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/007-create-repeat.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/007-create-repeat.response.txt) |
| 8 | 人工业务动作：把第二条告警补入刚建的Case；原已加入成员不重复添加。 | `POST /api/v2/investigation/case-links` | 201 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/008-attach-members.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/008-attach-members.response.txt) |
| 9 | 回执链接核对：沿case_url查看同一Case；确认对象可读取，不启动调查。 | `GET /api/v1/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/009-case-core-link.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/009-case-core-link.response.txt) |
| 10 | 关联核对：按原事件查建案关联，确认从事件可以找到刚建的Case。 | `GET /api/v2/investigation/case-links?incident_id=7bde0c0b-0d18-4abc-9382-9752f2ae5e98` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/010-case-links.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/010-case-links.response.txt) |
| 11 | 可选材料预览：返回本次context/tools/limits；确认范围后才另发investigate，不调用模型。 | `POST /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/011-preview.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/011-preview.response.txt) |
| 12 | 人工业务动作：一次请求发起主Run；模型/Tool循环在内部自动执行，返回保存结果及读取链接。 | `POST /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/012-main.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/012-main.response.txt) |
| 13 | 沿result_url读回同一Run的状态、范围和结构化结果；不重新分析。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/013-main-result.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/013-main-result.response.txt) |
| 14 | 沿report_url查看/下载同一Run的Markdown，便于阅读结论；不是第二份模型输出。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/report` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/014-main-report.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/014-main-report.response.txt) |
| 15 | 沿steps_url列出已记录的模型/Tool步骤；取得detail_url后才能逐条回看过程。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps?limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/015-main-steps.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/015-main-steps.response.txt) |
| 16 | 回看主调查内部步骤1：已固定Case成员与调查范围；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/016-main-step-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/016-main-step-1.response.txt) |
| 17 | 回看主调查内部步骤2：分析第1轮：准备调用模型；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/017-main-step-2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/017-main-step-2.response.txt) |
| 18 | 回看主调查内部步骤3：分析第1轮：模型已返回；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/3` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/018-main-step-3.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/018-main-step-3.response.txt) |
| 19 | 回看主调查内部步骤4：准备查询process_activity；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/4` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/019-main-step-4.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/019-main-step-4.response.txt) |
| 20 | 回看主调查内部步骤5：process_activity已返回，来源可用=True；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/5` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/020-main-step-5.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/020-main-step-5.response.txt) |
| 21 | 回看主调查内部步骤6：准备查询network_connections；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/6` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/021-main-step-6.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/021-main-step-6.response.txt) |
| 22 | 回看主调查内部步骤7：network_connections已返回，来源可用=True；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/7` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/022-main-step-7.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/022-main-step-7.response.txt) |
| 23 | 回看主调查内部步骤8：分析第2轮：准备调用模型；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/8` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/023-main-step-8.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/023-main-step-8.response.txt) |
| 24 | 回看主调查内部步骤9：分析第2轮：模型已返回；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/9` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/024-main-step-9.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/024-main-step-9.response.txt) |
| 25 | 回看主调查内部步骤10：调查已停止：analysis_complete；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/10` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/025-main-step-10.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/025-main-step-10.response.txt) |
| 26 | 沿evidence_url列出本Run证据及detail_url，供按报告引用追溯。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/026-main-evidence-list.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/026-main-evidence-list.response.txt) |
| 27 | 按编号A1查看来源告警材料；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/A1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/027-main-evidence-A1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/027-main-evidence-A1.response.txt) |
| 28 | 按编号T1查看已有分诊判断；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/T1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/028-main-evidence-T1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/028-main-evidence-T1.response.txt) |
| 29 | 按编号A2查看来源告警材料；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/A2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/029-main-evidence-A2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/029-main-evidence-A2.response.txt) |
| 30 | 按编号T2查看已有分诊判断；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/T2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/030-main-evidence-T2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/030-main-evidence-T2.response.txt) |
| 31 | 按编号E1查看实际Tool结果与tool_trace；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/E1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/031-main-evidence-E1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/031-main-evidence-E1.response.txt) |
| 32 | 按编号E2查看实际Tool结果与tool_trace；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/E2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/032-main-evidence-E2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/032-main-evidence-E2.response.txt) |
| 33 | 查找入口核对：按告警筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?alert_id=4c71eec2-77da-5b81-b68a-72801d55ea24&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/033-main-index-alert.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/033-main-index-alert.response.txt) |
| 34 | 查找入口核对：按事件筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?incident_id=7bde0c0b-0d18-4abc-9382-9752f2ae5e98&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/034-main-index-incident.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/034-main-index-incident.response.txt) |
| 35 | 查找入口核对：按Case筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?case_id=be4aeda2-a89b-47e6-a6f9-285b1a7e8723&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/035-main-index-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/035-main-index-case.response.txt) |
| 36 | 仅测试：按原operation_key读回同一主Run，不额外调用模型或Tool。 | `POST /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/036-main-repeat.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/036-main-repeat.response.txt) |
| 37 | 人工业务动作：手动刷新事件摘要，引用已有调查结果；会调用摘要模型，不重跑Case调查。 | `POST /api/v2/investigation/incidents/7bde0c0b-0d18-4abc-9382-9752f2ae5e98/overview/refresh?include_investigations=true` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/037-overview-refresh.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/037-overview-refresh.response.txt) |
| 38 | 展示读回：查看刚保存的事件概况和来源Run；普通GET不会再生成概况。 | `GET /api/v2/investigation/incidents/7bde0c0b-0d18-4abc-9382-9752f2ae5e98` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/038-overview-readback.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/038-overview-readback.response.txt) |
| 39 | 人工业务动作：带previous_run_id和新问题创建新Run，H1承接旧报告；实际分支见上方说明。 | `POST /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/039-followup.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/039-followup.response.txt) |
| 40 | 沿result_url读回同一Run的状态、范围和结构化结果；不重新分析。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/040-followup-result.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/040-followup-result.response.txt) |
| 41 | 沿report_url查看/下载同一Run的Markdown，便于阅读结论；不是第二份模型输出。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/report` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/041-followup-report.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/041-followup-report.response.txt) |
| 42 | 沿steps_url列出已记录的模型/Tool步骤；取得detail_url后才能逐条回看过程。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/steps?limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/042-followup-steps.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/042-followup-steps.response.txt) |
| 43 | 回看追加内部步骤1：已固定Case成员与调查范围；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/steps/1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/043-followup-step-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/043-followup-step-1.response.txt) |
| 44 | 回看追加内部步骤2：分析第1轮：准备调用模型；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/steps/2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/044-followup-step-2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/044-followup-step-2.response.txt) |
| 45 | 回看追加内部步骤3：分析第1轮：模型已返回；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/steps/3` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/045-followup-step-3.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/045-followup-step-3.response.txt) |
| 46 | 回看追加内部步骤4：模型结论未通过格式或引用校验；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/steps/4` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/046-followup-step-4.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/046-followup-step-4.response.txt) |
| 47 | 回看追加内部步骤5：调查已停止：input_or_token_limit；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/steps/5` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/047-followup-step-5.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/047-followup-step-5.response.txt) |
| 48 | 沿evidence_url列出本Run证据及detail_url，供按报告引用追溯。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/evidence` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/048-followup-evidence-list.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/048-followup-evidence-list.response.txt) |
| 49 | 按编号A1查看来源告警材料；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/evidence/A1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/049-followup-evidence-A1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/049-followup-evidence-A1.response.txt) |
| 50 | 按编号T1查看已有分诊判断；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/evidence/T1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/050-followup-evidence-T1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/050-followup-evidence-T1.response.txt) |
| 51 | 按编号A2查看来源告警材料；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/evidence/A2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/051-followup-evidence-A2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/051-followup-evidence-A2.response.txt) |
| 52 | 按编号T2查看已有分诊判断；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/evidence/T2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/052-followup-evidence-T2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/052-followup-evidence-T2.response.txt) |
| 53 | 按编号H1查看历史调查报告；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/evidence/H1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/053-followup-evidence-H1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/053-followup-evidence-H1.response.txt) |
| 54 | 查找入口核对：按告警筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?alert_id=4c71eec2-77da-5b81-b68a-72801d55ea24&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/054-followup-index-alert.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/054-followup-index-alert.response.txt) |
| 55 | 查找入口核对：按事件筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?incident_id=7bde0c0b-0d18-4abc-9382-9752f2ae5e98&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/055-followup-index-incident.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/055-followup-index-incident.response.txt) |
| 56 | 查找入口核对：按Case筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?case_id=be4aeda2-a89b-47e6-a6f9-285b1a7e8723&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/056-followup-index-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/056-followup-index-case.response.txt) |
| 57 | 历史核对：沿追加Run的H1查看完整旧报告，确认历史判断仍保留；不补查来源。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/evidence/H1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/057-history-evidence.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/057-history-evidence.response.txt) |
| 58 | 历史核对：重读主Run原报告，确认追加没有覆盖它。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/report` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/058-original-report-after-followup.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/058-original-report-after-followup.response.txt) |
| 59 | 标旧核对：新Run后读取旧概况，确认is_stale；本次GET不刷新文字。 | `GET /api/v2/investigation/incidents/7bde0c0b-0d18-4abc-9382-9752f2ae5e98` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/059-overview-after-new-run.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/059-overview-after-new-run.response.txt) |
| 60 | 历史入口：列出这个Case的Run，供以后定位主调查/追加；不创建Run。 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/060-case-history.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/060-case-history.response.txt) |
| 61 | 事件入口：列出关联Case/Run和范围，让事件层展示调查进展；不执行分析。 | `GET /api/v2/investigation/incidents/7bde0c0b-0d18-4abc-9382-9752f2ae5e98/investigations` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/061-incident-investigations.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/061-incident-investigations.response.txt) |
| 62 | 测试核对：重读原告警，与开始时比较关键字段；不会再分诊。 | `GET /api/v1/alerts/4c71eec2-77da-5b81-b68a-72801d55ea24` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/062-source-after-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/062-source-after-0.response.txt) |
| 63 | 测试核对：重读原告警，与开始时比较关键字段；不会再分诊。 | `GET /api/v1/alerts/f7af404b-26a6-5d15-bd6c-3a872bdaf451` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/063-source-after-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/063-source-after-1.response.txt) |

## 逐项判定

| 检查 | 结果 |
|---|---|
| create: same key returns receipt | 通过 |
| attach: added versus existing | 通过 |
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
| followup: result readback identical | 通过 |
| followup: downloaded report identical | 通过 |
| followup: alert index agrees | 通过 |
| followup: incident index agrees | 通过 |
| followup: case index agrees | 通过 |
| followup: valid conclusion completed | 未通过 |
| followup: member coverage count | 通过 |
| followup: selected members assessed or unresolved | 未通过 |
| followup: previous Run link | 通过 |
| followup: complete historical report retained | 通过 |
| followup: original Markdown unchanged | 通过 |
| overview: new Run marks old text stale without regeneration | 通过 |
| source Alert unchanged: 4c71eec2-77da-5b81-b68a-72801d55ea24 | 通过 |
| source Alert unchanged: f7af404b-26a6-5d15-bd6c-3a872bdaf451 | 通过 |
