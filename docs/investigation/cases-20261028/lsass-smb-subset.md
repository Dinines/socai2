# LSASS读取与SMB访问，验证成员子集：逐步测试记录

数据：已有模拟案例。批次`INVHTTP-20261028-01`，通过常驻18000/18010真实HTTP与API Key执行。

流程判定：**通过**。Case `623b13e4-7b9e-4de2-8148-c91ff73299a3`；来源事件`ddd24cf9-f413-4de5-bea5-333f8c080187`。

## 本例为什么这样走

本例的事件有“LSASS读取”和“SMB访问”两条告警。两条都进入Case，但本次只选择第一条LSASS告警分析；这样可以核对“Case收录了谁”和“这次Run实际调查了谁”不会混淆。它不是两条告警都已综合调查的示例。

**业务主线：看事件两成员 → 两成员建Case → 明确只选第一条 → 查询该主机进程/网络 → 保存单成员调查 → 事件概况展示覆盖范围。**

| 阶段（对应下方HTTP序号） | 谁触发 / 输入 → 实际输出 | 为什么走到这里、下一步看什么 |
|---|---|---|
| 了解材料：1–5 | 读取两条告警、事件和已有调查上下文 | 知道Case可纳入的材料；读取第二条不等于将它纳入本次Run |
| 建Case：6 | 人工选择事件的两名成员 → Case `623b13e4…`，含两条告警 | Case是案件材料容器；本次调查范围还需单独选择 |
| 预览子集：10 | selected_member_ids只含`c929a0c7…`，窗口为2026-10-25 03:28–03:37 UTC → all成员2、selected/read成员1 | 防止系统把未选的SMB告警也算成已调查。随后使用相同子集发起Run |
| 主调查：11 | 子集、问题、新operation_key → Run `c973bbbb…`；3次模型、2次Tool | 进程和网络查询均成功返回0条。首份结论的关系字段不合法，系统要求模型纠正一次；不是重新查询 |
| 查看与追溯：12–35 | 从Run回包读取报告、13条内部步骤、A1/T1/E1/E2及三个索引 | 看本次究竟读了谁、查了什么。T1表示已有分诊，不是第二名成员 |
| 核对未选成员：37 | 以第二条告警ID查询executions → 这次Run未被归给它 | 专门验证子集边界；它不是发现了新线索后启动的另一项调查 |
| 事件展示：38–39 | 人工刷新概况并读回 → 引用这次单成员调查及其覆盖范围 | 事件仍有两条告警，不能把其中一次单成员调查说成事件全覆盖 |
| 历史与关联：40–41 | 读取Case历史、事件关联调查列表 | 供下次从Case或事件找到原Run；不会另起分析 |

第7步重复建案、第8–9步读取Case/关联、第36步重复主请求、第42–43步比较源告警，均为测试核对。此例没有追加问题Run。

[原主报告](lsass-smb-subset-main-report.md)中的“单成员T1”“查询失败”“告警内容截断”是本次发现的自然语言错误，不能按它理解数据：实际选中的是`c929a0c7…`告警；E1/E2均available=true、0条；被截断的是旧分析摘要。下面保留原输出，并通过用途说明解释真实执行。

**阅读标号：**下面的HTTP序号用于对应原始请求；下节“内部账本步骤”属于一次investigate内部的自动执行。一次内部动作可能在后面被GET读回，不能按GET出现的位置判断动作发生时间。正文文件链接仅用于核对当时保存的输入输出。

## 一次调查内部为什么进入下一步

本例问题明确要求先查process_activity和network_connections。系统把这些工具的定义交给模型；只有收到原生tool_calls后才分派查询。下面列出实际发生的自动步骤；点“记录”读取的是保存内容。

### 主调查的内部步骤

| 内部账本步骤 | 为什么发生 / 输入输出如何承接 | 原始记录 |
|---|---|---|
| 1：已固定Case成员与调查范围 | 固定本Run成员、窗口及材料；把告警A和已有分诊T交给模型。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/015-main-step-1.response.txt) |
| 2：分析第1轮：准备调用模型 | 首次把问题、材料和可用Tool定义发送给模型；接下来保存模型返回的调用或答案。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/016-main-step-2.response.txt) |
| 3：分析第1轮：模型已返回 | 模型按本例问题返回原生调用process_activity、network_connections；系统据此校验并分派下面的Tool步骤。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/017-main-step-3.response.txt) |
| 4：准备查询process_activity | 收到模型的调用要求后，记录工具及参数，再沿固定Case/主机/窗口执行；本链接回看的是已保存请求。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/018-main-step-4.response.txt) |
| 5：process_activity已返回，来源可用=True | 保存实际返回、可用性及行数并分配E编号，再把结果交回模型；0行与来源不可用须区分。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/019-main-step-5.response.txt) |
| 6：准备查询network_connections | 收到模型的调用要求后，记录工具及参数，再沿固定Case/主机/窗口执行；本链接回看的是已保存请求。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/020-main-step-6.response.txt) |
| 7：network_connections已返回，来源可用=True | 保存实际返回、可用性及行数并分配E编号，再把结果交回模型；0行与来源不可用须区分。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/021-main-step-7.response.txt) |
| 8：分析第2轮：准备调用模型 | 把实际Tool返回加入模型输入，请模型继续分析；不是再次执行刚才的查询。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/022-main-step-8.response.txt) |
| 9：分析第2轮：模型已返回 | 模型返回候选结论；系统随后校验字段、成员和引用，返回答案不代表已经采纳。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/023-main-step-9.response.txt) |
| 10：模型结论未通过格式或引用校验 | 候选关系的alert_ids不足2名成员（`too_short`）；本Run只选1名成员，不能构造多成员关系。系统把错误交给模型纠正。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/024-main-step-10.response.txt) |
| 11：分析第3轮：准备调用模型 | 上一份结论未通过校验；把错误及合法引用交给模型纠正一次，本轮不再提供Tool。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/025-main-step-11.response.txt) |
| 12：分析第3轮：模型已返回 | 模型返回候选结论；系统随后校验字段、成员和引用，返回答案不代表已经采纳。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/026-main-step-12.response.txt) |
| 13：调查已停止：analysis_complete | 记录最终停止状态及报告/缺口；analysis_complete表示本次执行结束，partial仍保留证据不足；其他停止原因见本例结果。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/027-main-step-13.response.txt) |

## 实际调查结果

| 执行 | Run | 状态/停止原因 | 完整度 | 模型/Tool | 已知tokens |
|---|---|---|---|---:|---:|
| main | `c973bbbb-7bfb-599b-9cc9-56051ec378b2` | completed / analysis_complete | partial | 3/2 | 9168 |

### main 输出

选定的单成员 T1（LLM分诊结果）因缺乏过程活动记录（E1显示返回0行）和网络连接记录（E2显示返回0行）证实，且告警内容截断，无法证实指控。过程活动查询失败不提供授权证据。

[完整Markdown报告原文](lsass-smb-subset-main-report.md)

选定成员：`c929a0c7-69b5-5617-b830-a701e8bae72f`。
成员覆盖：`{"selected_count": 1, "read_count": 1, "addressed_count": 0, "unresolved_count": 1, "not_assessed_count": 0, "source_unavailable_count": 0}`。
时间线1项，关联0项，未决问题2项。

| Tool证据 | 参数 | available / 条数 | 复用来源 |
|---|---|---|---|
| E1 / process_activity | `{"hostname": "DEMO-APP-12", "limit": 20}` | True / 0 | `null` |
| E2 / network_connections | `{"hostname": "DEMO-APP-12", "limit": 20}` | True / 0 | `null` |

## 检查结果

全部本例流程检查通过。该判定不等同于模型业务结论质量全面通过。

**内容审阅未通过：**模型摘要把T1分诊编号称作成员，并写“过程活动查询失败”；实际E1/E2均available=true且0条，属于成功空结果。本次源材料标记的是保存的分析文本截断，摘要却泛称“告警内容截断”。字段/引用校验和流程检查未捕获这些自然语言偏差，不能把本例作为分析质量通过。

## 每一步请求与实际返回

这是测试脚本的请求顺序；“用途与跳转依据”说明每行是在发起业务、读取过程还是做测试核对。第7步等同key重复请求仅为本批核对，不是用户每次必做的流程。

下面的请求JSON在发送前写入，因此保留pending标记；最终HTTP状态和检查结果以[本例summary](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/summary.json)为准。响应文件是调用脚本去掉其附加换行后的HTTP原始正文。

| HTTP序号 | 用途与跳转依据 | 方法与路径 | HTTP | 输入 | 实际返回 |
|---:|---|---|---:|---|---|
| 1 | 读取来源：确认第1条告警内容；下一步据此选Case成员。 | `GET /api/v1/alerts/c929a0c7-69b5-5617-b830-a701e8bae72f` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/001-source-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/001-source-0.response.txt) |
| 2 | 读取来源：确认第2条告警内容；下一步据此选Case成员。 | `GET /api/v1/alerts/6b9b6217-fdd6-59a0-b02f-93267050cd5f` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/002-source-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/002-source-1.response.txt) |
| 3 | 读取事件：确认原分组成员、分诊汇总及旧概况；没有重新分组/生成概况。 | `GET /api/v2/investigation/incidents/ddd24cf9-f413-4de5-bea5-333f8c080187` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/003-incident-before.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/003-incident-before.response.txt) |
| 4 | 读取告警调查入口：查看已有来源/Case/Run关联；为选择调查范围提供上下文。 | `GET /api/v2/investigation/alerts/c929a0c7-69b5-5617-b830-a701e8bae72f/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/004-alert-context-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/004-alert-context-0.response.txt) |
| 5 | 读取告警调查入口：查看已有来源/Case/Run关联；为选择调查范围提供上下文。 | `GET /api/v2/investigation/alerts/6b9b6217-fdd6-59a0-b02f-93267050cd5f/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/005-alert-context-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/005-alert-context-1.response.txt) |
| 6 | 人工业务动作：按请求的成员和来源建Case；输出Case ID供后续预览/调查，尚不调用模型。 | `POST /api/v2/investigation/case-links` | 201 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/006-create-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/006-create-case.response.txt) |
| 7 | 仅测试：相同operation_key读回同一建案回执；不再建第二个Case。 | `POST /api/v2/investigation/case-links` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/007-create-repeat.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/007-create-repeat.response.txt) |
| 8 | 回执链接核对：沿case_url查看同一Case；确认对象可读取，不启动调查。 | `GET /api/v1/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/008-case-core-link.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/008-case-core-link.response.txt) |
| 9 | 关联核对：按原事件查建案关联，确认从事件可以找到刚建的Case。 | `GET /api/v2/investigation/case-links?incident_id=ddd24cf9-f413-4de5-bea5-333f8c080187` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/009-case-links.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/009-case-links.response.txt) |
| 10 | 可选材料预览：返回本次context/tools/limits；确认范围后才另发investigate，不调用模型。 | `POST /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/010-preview.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/010-preview.response.txt) |
| 11 | 人工业务动作：一次请求发起主Run；模型/Tool循环在内部自动执行，返回保存结果及读取链接。 | `POST /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/011-main.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/011-main.response.txt) |
| 12 | 沿result_url读回同一Run的状态、范围和结构化结果；不重新分析。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/012-main-result.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/012-main-result.response.txt) |
| 13 | 沿report_url查看/下载同一Run的Markdown，便于阅读结论；不是第二份模型输出。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/report` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/013-main-report.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/013-main-report.response.txt) |
| 14 | 沿steps_url列出已记录的模型/Tool步骤；取得detail_url后才能逐条回看过程。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps?limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/014-main-steps.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/014-main-steps.response.txt) |
| 15 | 回看主调查内部步骤1：已固定Case成员与调查范围；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/015-main-step-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/015-main-step-1.response.txt) |
| 16 | 回看主调查内部步骤2：分析第1轮：准备调用模型；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/016-main-step-2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/016-main-step-2.response.txt) |
| 17 | 回看主调查内部步骤3：分析第1轮：模型已返回；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/3` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/017-main-step-3.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/017-main-step-3.response.txt) |
| 18 | 回看主调查内部步骤4：准备查询process_activity；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/4` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/018-main-step-4.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/018-main-step-4.response.txt) |
| 19 | 回看主调查内部步骤5：process_activity已返回，来源可用=True；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/5` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/019-main-step-5.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/019-main-step-5.response.txt) |
| 20 | 回看主调查内部步骤6：准备查询network_connections；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/6` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/020-main-step-6.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/020-main-step-6.response.txt) |
| 21 | 回看主调查内部步骤7：network_connections已返回，来源可用=True；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/7` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/021-main-step-7.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/021-main-step-7.response.txt) |
| 22 | 回看主调查内部步骤8：分析第2轮：准备调用模型；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/8` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/022-main-step-8.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/022-main-step-8.response.txt) |
| 23 | 回看主调查内部步骤9：分析第2轮：模型已返回；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/9` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/023-main-step-9.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/023-main-step-9.response.txt) |
| 24 | 回看主调查内部步骤10：模型结论未通过格式或引用校验；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/10` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/024-main-step-10.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/024-main-step-10.response.txt) |
| 25 | 回看主调查内部步骤11：分析第3轮：准备调用模型；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/11` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/025-main-step-11.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/025-main-step-11.response.txt) |
| 26 | 回看主调查内部步骤12：分析第3轮：模型已返回；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/12` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/026-main-step-12.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/026-main-step-12.response.txt) |
| 27 | 回看主调查内部步骤13：调查已停止：analysis_complete；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/13` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/027-main-step-13.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/027-main-step-13.response.txt) |
| 28 | 沿evidence_url列出本Run证据及detail_url，供按报告引用追溯。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/evidence` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/028-main-evidence-list.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/028-main-evidence-list.response.txt) |
| 29 | 按编号A1查看来源告警材料；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/evidence/A1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/029-main-evidence-A1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/029-main-evidence-A1.response.txt) |
| 30 | 按编号T1查看已有分诊判断；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/evidence/T1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/030-main-evidence-T1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/030-main-evidence-T1.response.txt) |
| 31 | 按编号E1查看实际Tool结果与tool_trace；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/evidence/E1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/031-main-evidence-E1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/031-main-evidence-E1.response.txt) |
| 32 | 按编号E2查看实际Tool结果与tool_trace；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/evidence/E2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/032-main-evidence-E2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/032-main-evidence-E2.response.txt) |
| 33 | 查找入口核对：按告警筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?alert_id=c929a0c7-69b5-5617-b830-a701e8bae72f&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/033-main-index-alert.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/033-main-index-alert.response.txt) |
| 34 | 查找入口核对：按事件筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?incident_id=ddd24cf9-f413-4de5-bea5-333f8c080187&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/034-main-index-incident.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/034-main-index-incident.response.txt) |
| 35 | 查找入口核对：按Case筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?case_id=623b13e4-7b9e-4de2-8148-c91ff73299a3&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/035-main-index-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/035-main-index-case.response.txt) |
| 36 | 仅测试：按原operation_key读回同一主Run，不额外调用模型或Tool。 | `POST /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/036-main-repeat.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/036-main-repeat.response.txt) |
| 37 | 子集核对：从未选告警查Run列表，确认这次单成员Run没有错误归属给它。 | `GET /api/v2/investigation/executions?alert_id=6b9b6217-fdd6-59a0-b02f-93267050cd5f&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/037-unselected-index.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/037-unselected-index.response.txt) |
| 38 | 人工业务动作：手动刷新事件摘要，引用已有调查结果；会调用摘要模型，不重跑Case调查。 | `POST /api/v2/investigation/incidents/ddd24cf9-f413-4de5-bea5-333f8c080187/overview/refresh?include_investigations=true` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/038-overview-refresh.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/038-overview-refresh.response.txt) |
| 39 | 展示读回：查看刚保存的事件概况和来源Run；普通GET不会再生成概况。 | `GET /api/v2/investigation/incidents/ddd24cf9-f413-4de5-bea5-333f8c080187` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/039-overview-readback.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/039-overview-readback.response.txt) |
| 40 | 历史入口：列出这个Case的Run，供以后定位主调查/追加；不创建Run。 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/040-case-history.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/040-case-history.response.txt) |
| 41 | 事件入口：列出关联Case/Run和范围，让事件层展示调查进展；不执行分析。 | `GET /api/v2/investigation/incidents/ddd24cf9-f413-4de5-bea5-333f8c080187/investigations` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/041-incident-investigations.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/041-incident-investigations.response.txt) |
| 42 | 测试核对：重读原告警，与开始时比较关键字段；不会再分诊。 | `GET /api/v1/alerts/c929a0c7-69b5-5617-b830-a701e8bae72f` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/042-source-after-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/042-source-after-0.response.txt) |
| 43 | 测试核对：重读原告警，与开始时比较关键字段；不会再分诊。 | `GET /api/v1/alerts/6b9b6217-fdd6-59a0-b02f-93267050cd5f` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/043-source-after-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/043-source-after-1.response.txt) |

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
| unselected member not attributed to this Run | 通过 |
| overview: generated and saved | 通过 |
| overview: new Run cited | 通过 |
| overview: GET preserves text and source metadata | 通过 |
| source Alert unchanged: c929a0c7-69b5-5617-b830-a701e8bae72f | 通过 |
| source Alert unchanged: 6b9b6217-fdd6-59a0-b02f-93267050cd5f | 通过 |
