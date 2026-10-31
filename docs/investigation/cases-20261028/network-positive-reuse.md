# 网络记录命中与追加查询复用：逐步测试记录

数据：已有模拟案例。批次`INVHTTP-20261028-01`，通过常驻18000/18010真实HTTP与API Key执行。

流程判定：**未全部通过**。Case `a280c884-0abd-458d-bb66-13c06fe9ca5b`；来源事件`fbbe6415-3d73-5742-a91a-d1a9617d379d`。

## 本例为什么这样走

本例有两条网络告警及3条规范化网络记录，用来核对“模型真的调用Tool → 参数正确 → 返回行成为证据 → 报告能追溯到具体来源行”。另外追加一次同参数查询请求，尝试覆盖历史查询复用；这条追加分支实际没有调用Tool，不能算复用已通过。

**业务主线：事件两成员建Case → 查进程/网络 → 网络命中3行 → 从报告追到某行 → 追加同参数补查（未执行到Tool）→ 手动刷新概况。**

| 阶段（对应下方HTTP序号） | 谁触发 / 输入 → 实际输出 | 为什么走到这里、下一步看什么 |
|---|---|---|
| 了解材料：1–5 | 读取两条网络告警、事件及已有调查上下文 | 先确定待核的连接记录和主机；随后人工明确选择两名成员 |
| 建Case：6 | 事件ID及两条alert_ids → Case `a280c884…` | 将两条材料放到同一案件调查；建案不调用模型 |
| 预览：10 | 两名成员、主机investigation-ch-20261023-01-host、2026-10-23 09:58–10:03 UTC及问题 → 固定材料和Tools | 本次进程/网络Tool沿这个范围执行，模型不能自行扩展到其他主机/窗口 |
| 主调查：11 | 同一范围及operation_key → Run `d957313e…`；2次模型、2次Tool | E1进程查询成功但0条，E2网络查询成功且3条；再分析后形成partial报告 |
| 追到来源行：25、29–30 | evidence列表 → E2详情 → rows中的第0行链接 | 因报告引用E2确认连接，继续核对实际时间、源/目标IP、443端口和event_id；读取的是本次已保存行，不会再次查湖 |
| 查看其他结果：12–33 | 报告、内部步骤、其他证据及三个索引 | 说明同一Run的结论、调用过程和查找入口；不是新增的调查分支 |
| 追加同参数补查：35 | previous_run_id=`d957313e…`及明确重查问题 → 新Run `7b43c909…`，2次模型、0次Tool | 这是人工希望补查的原因；实际模型直接作答、引用错误后纠正。没有Tool调用，就没有进入缓存复用判断 |
| 核对历史：36–54 | 读取追加结果/H1并重读原报告 | 看追加失败的检查点，以及旧结果仍保持；H1提及的E1/E2属于历史，不是本次新查询 |
| 事件展示与历史：55–58 | 人工refresh、普通GET及Case/事件历史读取 → 概况、来源Run和关联 | 将已保存的调查进展用于事件展示；不会借概况刷新补做遗漏的network_connections |

第7步重复建案、第8–9步读取Case/关联、第34步重复主请求、第59–60步比较源告警，均为测试核对。

具体追溯路径：[主报告](network-positive-reuse-main-report.md)的E2 → [E2详情](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/029-main-evidence-E2.response.txt)的rows → [第0行](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/030-main-row-E2.response.txt)。该行是09:59:00 UTC、TCP/443、`::ffff:192.0.2.70`到`::ffff:198.51.100.70`；这证明查询结果包含这条连接，不证明它一定恶意或能识别发起进程。

**阅读标号：**下面的HTTP序号用于对应原始请求；下节“内部账本步骤”属于一次investigate内部的自动执行。一次内部动作可能在后面被GET读回，不能按GET出现的位置判断动作发生时间。正文文件链接仅用于核对当时保存的输入输出。

## 一次调查内部为什么进入下一步

主调查要求先查process_activity和network_connections；追加问题只要求重查同参数的network_connections。系统把可用工具的定义交给模型；只有收到原生tool_calls后才分派查询。下面列出实际发生的自动步骤；点“记录”读取的是保存内容。

### 主调查的内部步骤

| 内部账本步骤 | 为什么发生 / 输入输出如何承接 | 原始记录 |
|---|---|---|
| 1：已固定Case成员与调查范围 | 固定本Run成员、窗口及两条告警A1/A2；本例主调查没有T分诊证据。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/015-main-step-1.response.txt) |
| 2：分析第1轮：准备调用模型 | 首次把问题、材料和可用Tool定义发送给模型；接下来保存模型返回的调用或答案。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/016-main-step-2.response.txt) |
| 3：分析第1轮：模型已返回 | 模型按本例问题返回原生调用process_activity、network_connections；系统据此校验并分派下面的Tool步骤。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/017-main-step-3.response.txt) |
| 4：准备查询process_activity | 收到模型的调用要求后，记录工具及参数，再沿固定Case/主机/窗口执行；本链接回看的是已保存请求。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/018-main-step-4.response.txt) |
| 5：process_activity已返回，来源可用=True | 保存实际返回、可用性及行数并分配E编号，再把结果交回模型；0行与来源不可用须区分。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/019-main-step-5.response.txt) |
| 6：准备查询network_connections | 收到模型的调用要求后，记录工具及参数，再沿固定Case/主机/窗口执行；本链接回看的是已保存请求。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/020-main-step-6.response.txt) |
| 7：network_connections已返回，来源可用=True | 保存实际返回、可用性及行数并分配E编号，再把结果交回模型；0行与来源不可用须区分。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/021-main-step-7.response.txt) |
| 8：分析第2轮：准备调用模型 | 把实际Tool返回加入模型输入，请模型继续分析；不是再次执行刚才的查询。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/022-main-step-8.response.txt) |
| 9：分析第2轮：模型已返回 | 模型返回候选结论；系统随后校验字段、成员和引用，返回答案不代表已经采纳。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/023-main-step-9.response.txt) |
| 10：调查已停止：analysis_complete | 记录最终停止状态及报告/缺口；analysis_complete表示本次执行结束，partial仍保留证据不足；其他停止原因见本例结果。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/024-main-step-10.response.txt) |

### 追加问题的内部步骤

| 内部账本步骤 | 为什么发生 / 输入输出如何承接 | 原始记录 |
|---|---|---|
| 1：已固定Case成员与调查范围 | 固定本Run成员、窗口及材料；加入H1历史报告，供回答追加问题。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/039-followup-step-1.response.txt) |
| 2：分析第1轮：准备调用模型 | 首次把问题、材料和可用Tool定义发送给模型；接下来保存模型返回的调用或答案。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/040-followup-step-2.response.txt) |
| 3：分析第1轮：模型已返回 | 模型返回候选结论；系统随后校验字段、成员和引用，返回答案不代表已经采纳。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/041-followup-step-3.response.txt) |
| 4：模型结论未通过格式或引用校验 | 候选结论被拒：`unknown_evidence_reference`；系统仅在剩余额度允许时纠正一次，不把原答当报告结论。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/042-followup-step-4.response.txt) |
| 5：分析第2轮：准备调用模型 | 上一份结论未通过校验；把错误及合法引用交给模型纠正一次，本轮不再提供Tool。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/043-followup-step-5.response.txt) |
| 6：分析第2轮：模型已返回 | 模型返回候选结论；系统随后校验字段、成员和引用，返回答案不代表已经采纳。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/044-followup-step-6.response.txt) |
| 7：调查已停止：analysis_complete | 记录最终停止状态及报告/缺口；analysis_complete表示本次执行结束，partial仍保留证据不足；其他停止原因见本例结果。 | [记录](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/045-followup-step-7.response.txt) |

## 实际调查结果

| 执行 | Run | 状态/停止原因 | 完整度 | 模型/Tool | 已知tokens |
|---|---|---|---|---:|---:|
| main | `d957313e-b528-585c-9254-cd7bb8675da7` | completed / analysis_complete | partial | 2/2 | 7300 |
| followup | `7b43c909-a450-55da-9a20-c6123dab7658` | completed / analysis_complete | partial | 2/0 | 10720 |

### main 输出

告警A1和A2针对主机investigation-ch-20261023-01-host在09:59:00和10:01:00分别报告网络活动，对应事件ID c9ee6c8a-d44d-5ffe-a456-594b5555a87c和951c5352-2df4-53d8-a431-b2763fea5e6e。网络细节E2显示这两次连接均为TCP/443至::ffff:198.51.100.70，来源IP均为::ffff:192.0.2.70。进程活动E1在相同时间窗口返回空结果，提示该窗口可能缺少进程活动记录或工具未覆盖相关进程。

[完整Markdown报告原文](network-positive-reuse-main-report.md)

选定成员：`3fcd245d-0496-54f3-875e-f9a7eb90ae2d, 5272ae80-b48e-5ef3-8cdd-805885a558a0`。
成员覆盖：`{"selected_count": 2, "read_count": 2, "addressed_count": 0, "unresolved_count": 2, "not_assessed_count": 0, "source_unavailable_count": 0}`。
时间线5项，关联1项，未决问题3项。

| Tool证据 | 参数 | available / 条数 | 复用来源 |
|---|---|---|---|
| E1 / process_activity | `{"hostname": "investigation-ch-20261023-01-host", "limit": 20}` | True / 0 | `null` |
| E2 / network_connections | `{"hostname": "investigation-ch-20261023-01-host", "limit": 20}` | True / 3 | `null` |

### followup 输出

告警 A1 与 A2 基于同一主机（3fcd...）、相同源 IP 和目标 IP 段，时间间隔 2 分钟，且详情 E2 确认事件 ID 匹配，存在强共享上下文。然而，进程活动证据 E1 查询结果为空，导致无法确认发起连接的进程身份及业务意图。无法区分是采集盲区、权限不足还是真实存在无对应进程的网络活动（如内核模块直连等）。当前证据不足以断定攻击成功或正常业务，案例保持待核状态。

[完整Markdown报告原文](network-positive-reuse-followup-report.md)

选定成员：`3fcd245d-0496-54f3-875e-f9a7eb90ae2d, 5272ae80-b48e-5ef3-8cdd-805885a558a0`。
成员覆盖：`{"selected_count": 2, "read_count": 2, "addressed_count": 0, "unresolved_count": 2, "not_assessed_count": 0, "source_unavailable_count": 0}`。
时间线2项，关联1项，未决问题2项。

| Tool证据 | 参数 | available / 条数 | 复用来源 |
|---|---|---|---|
| 无本次Tool调用 | — | — | — |

## 检查结果

- followup: matching query reused

主调查命中3条网络记录。追加要求再次调用相同network_connections，但模型直接回答、未发出任何Tool调用；引用错误经一次纠正后报告完成。故本例没有缓存命中证据，不能称查询复用已通过，也不能据此断定缓存实现错误。

内容审阅还发现追加摘要写“同一主机（3fcd...）”，其中3fcd开头的是告警UUID，实际主机名为investigation-ch-20261023-01-host。这是自然语言实体称谓错误，结构化范围校验没有捕获；摘要中的E1/E2也是H1里的历史编号，不代表本次新增查询。

## 每一步请求与实际返回

这是测试脚本的请求顺序；“用途与跳转依据”说明每行是在发起业务、读取过程还是做测试核对。第7步等同key重复请求仅为本批核对，不是用户每次必做的流程。

下面的请求JSON在发送前写入，因此保留pending标记；最终HTTP状态和检查结果以[本例summary](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/summary.json)为准。响应文件是调用脚本去掉其附加换行后的HTTP原始正文。

| HTTP序号 | 用途与跳转依据 | 方法与路径 | HTTP | 输入 | 实际返回 |
|---:|---|---|---:|---|---|
| 1 | 读取来源：确认第1条告警内容；下一步据此选Case成员。 | `GET /api/v1/alerts/3fcd245d-0496-54f3-875e-f9a7eb90ae2d` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/001-source-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/001-source-0.response.txt) |
| 2 | 读取来源：确认第2条告警内容；下一步据此选Case成员。 | `GET /api/v1/alerts/5272ae80-b48e-5ef3-8cdd-805885a558a0` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/002-source-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/002-source-1.response.txt) |
| 3 | 读取事件：确认原分组成员、分诊汇总及旧概况；没有重新分组/生成概况。 | `GET /api/v2/investigation/incidents/fbbe6415-3d73-5742-a91a-d1a9617d379d` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/003-incident-before.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/003-incident-before.response.txt) |
| 4 | 读取告警调查入口：查看已有来源/Case/Run关联；为选择调查范围提供上下文。 | `GET /api/v2/investigation/alerts/3fcd245d-0496-54f3-875e-f9a7eb90ae2d/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/004-alert-context-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/004-alert-context-0.response.txt) |
| 5 | 读取告警调查入口：查看已有来源/Case/Run关联；为选择调查范围提供上下文。 | `GET /api/v2/investigation/alerts/5272ae80-b48e-5ef3-8cdd-805885a558a0/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/005-alert-context-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/005-alert-context-1.response.txt) |
| 6 | 人工业务动作：按请求的成员和来源建Case；输出Case ID供后续预览/调查，尚不调用模型。 | `POST /api/v2/investigation/case-links` | 201 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/006-create-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/006-create-case.response.txt) |
| 7 | 仅测试：相同operation_key读回同一建案回执；不再建第二个Case。 | `POST /api/v2/investigation/case-links` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/007-create-repeat.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/007-create-repeat.response.txt) |
| 8 | 回执链接核对：沿case_url查看同一Case；确认对象可读取，不启动调查。 | `GET /api/v1/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/008-case-core-link.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/008-case-core-link.response.txt) |
| 9 | 关联核对：按原事件查建案关联，确认从事件可以找到刚建的Case。 | `GET /api/v2/investigation/case-links?incident_id=fbbe6415-3d73-5742-a91a-d1a9617d379d` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/009-case-links.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/009-case-links.response.txt) |
| 10 | 可选材料预览：返回本次context/tools/limits；确认范围后才另发investigate，不调用模型。 | `POST /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/010-preview.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/010-preview.response.txt) |
| 11 | 人工业务动作：一次请求发起主Run；模型/Tool循环在内部自动执行，返回保存结果及读取链接。 | `POST /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/011-main.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/011-main.response.txt) |
| 12 | 沿result_url读回同一Run的状态、范围和结构化结果；不重新分析。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/012-main-result.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/012-main-result.response.txt) |
| 13 | 沿report_url查看/下载同一Run的Markdown，便于阅读结论；不是第二份模型输出。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/report` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/013-main-report.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/013-main-report.response.txt) |
| 14 | 沿steps_url列出已记录的模型/Tool步骤；取得detail_url后才能逐条回看过程。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps?limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/014-main-steps.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/014-main-steps.response.txt) |
| 15 | 回看主调查内部步骤1：已固定Case成员与调查范围；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/015-main-step-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/015-main-step-1.response.txt) |
| 16 | 回看主调查内部步骤2：分析第1轮：准备调用模型；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/016-main-step-2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/016-main-step-2.response.txt) |
| 17 | 回看主调查内部步骤3：分析第1轮：模型已返回；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/3` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/017-main-step-3.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/017-main-step-3.response.txt) |
| 18 | 回看主调查内部步骤4：准备查询process_activity；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/4` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/018-main-step-4.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/018-main-step-4.response.txt) |
| 19 | 回看主调查内部步骤5：process_activity已返回，来源可用=True；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/5` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/019-main-step-5.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/019-main-step-5.response.txt) |
| 20 | 回看主调查内部步骤6：准备查询network_connections；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/6` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/020-main-step-6.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/020-main-step-6.response.txt) |
| 21 | 回看主调查内部步骤7：network_connections已返回，来源可用=True；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/7` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/021-main-step-7.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/021-main-step-7.response.txt) |
| 22 | 回看主调查内部步骤8：分析第2轮：准备调用模型；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/8` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/022-main-step-8.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/022-main-step-8.response.txt) |
| 23 | 回看主调查内部步骤9：分析第2轮：模型已返回；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/9` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/023-main-step-9.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/023-main-step-9.response.txt) |
| 24 | 回看主调查内部步骤10：调查已停止：analysis_complete；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/10` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/024-main-step-10.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/024-main-step-10.response.txt) |
| 25 | 沿evidence_url列出本Run证据及detail_url，供按报告引用追溯。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/025-main-evidence-list.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/025-main-evidence-list.response.txt) |
| 26 | 按编号A1查看来源告警材料；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/A1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/026-main-evidence-A1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/026-main-evidence-A1.response.txt) |
| 27 | 按编号A2查看来源告警材料；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/A2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/027-main-evidence-A2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/027-main-evidence-A2.response.txt) |
| 28 | 按编号E1查看实际Tool结果与tool_trace；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/028-main-evidence-E1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/028-main-evidence-E1.response.txt) |
| 29 | 按编号E2查看实际Tool结果与tool_trace；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/029-main-evidence-E2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/029-main-evidence-E2.response.txt) |
| 30 | 沿E2的rows链接读取已保存第0行及来源ID；因为结果有行才可这样追溯，不再次查湖。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E2/rows/0` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/030-main-row-E2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/030-main-row-E2.response.txt) |
| 31 | 查找入口核对：按告警筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?alert_id=3fcd245d-0496-54f3-875e-f9a7eb90ae2d&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/031-main-index-alert.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/031-main-index-alert.response.txt) |
| 32 | 查找入口核对：按事件筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?incident_id=fbbe6415-3d73-5742-a91a-d1a9617d379d&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/032-main-index-incident.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/032-main-index-incident.response.txt) |
| 33 | 查找入口核对：按Case筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?case_id=a280c884-0abd-458d-bb66-13c06fe9ca5b&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/033-main-index-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/033-main-index-case.response.txt) |
| 34 | 仅测试：按原operation_key读回同一主Run，不额外调用模型或Tool。 | `POST /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/034-main-repeat.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/034-main-repeat.response.txt) |
| 35 | 人工业务动作：带previous_run_id和新问题创建新Run，H1承接旧报告；实际分支见上方说明。 | `POST /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/035-followup.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/035-followup.response.txt) |
| 36 | 沿result_url读回同一Run的状态、范围和结构化结果；不重新分析。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/036-followup-result.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/036-followup-result.response.txt) |
| 37 | 沿report_url查看/下载同一Run的Markdown，便于阅读结论；不是第二份模型输出。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/report` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/037-followup-report.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/037-followup-report.response.txt) |
| 38 | 沿steps_url列出已记录的模型/Tool步骤；取得detail_url后才能逐条回看过程。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/steps?limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/038-followup-steps.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/038-followup-steps.response.txt) |
| 39 | 回看追加内部步骤1：已固定Case成员与调查范围；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/steps/1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/039-followup-step-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/039-followup-step-1.response.txt) |
| 40 | 回看追加内部步骤2：分析第1轮：准备调用模型；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/steps/2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/040-followup-step-2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/040-followup-step-2.response.txt) |
| 41 | 回看追加内部步骤3：分析第1轮：模型已返回；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/steps/3` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/041-followup-step-3.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/041-followup-step-3.response.txt) |
| 42 | 回看追加内部步骤4：模型结论未通过格式或引用校验；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/steps/4` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/042-followup-step-4.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/042-followup-step-4.response.txt) |
| 43 | 回看追加内部步骤5：分析第2轮：准备调用模型；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/steps/5` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/043-followup-step-5.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/043-followup-step-5.response.txt) |
| 44 | 回看追加内部步骤6：分析第2轮：模型已返回；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/steps/6` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/044-followup-step-6.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/044-followup-step-6.response.txt) |
| 45 | 回看追加内部步骤7：调查已停止：analysis_complete；动作早已发生，此GET仅读记录。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/steps/7` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/045-followup-step-7.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/045-followup-step-7.response.txt) |
| 46 | 沿evidence_url列出本Run证据及detail_url，供按报告引用追溯。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/046-followup-evidence-list.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/046-followup-evidence-list.response.txt) |
| 47 | 按编号A1查看来源告警材料；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/A1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/047-followup-evidence-A1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/047-followup-evidence-A1.response.txt) |
| 48 | 按编号A2查看来源告警材料；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/A2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/048-followup-evidence-A2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/048-followup-evidence-A2.response.txt) |
| 49 | 按编号H1查看历史调查报告；这是该Run保存的依据，不触发新调查。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/H1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/049-followup-evidence-H1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/049-followup-evidence-H1.response.txt) |
| 50 | 查找入口核对：按告警筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?alert_id=3fcd245d-0496-54f3-875e-f9a7eb90ae2d&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/050-followup-index-alert.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/050-followup-index-alert.response.txt) |
| 51 | 查找入口核对：按事件筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?incident_id=fbbe6415-3d73-5742-a91a-d1a9617d379d&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/051-followup-index-incident.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/051-followup-index-incident.response.txt) |
| 52 | 查找入口核对：按Case筛选executions，确认可找到同一Run；不是下一次分析。 | `GET /api/v2/investigation/executions?case_id=a280c884-0abd-458d-bb66-13c06fe9ca5b&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/052-followup-index-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/052-followup-index-case.response.txt) |
| 53 | 历史核对：沿追加Run的H1查看完整旧报告，确认历史判断仍保留；不补查来源。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/H1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/053-history-evidence.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/053-history-evidence.response.txt) |
| 54 | 历史核对：重读主Run原报告，确认追加没有覆盖它。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/report` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/054-original-report-after-followup.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/054-original-report-after-followup.response.txt) |
| 55 | 人工业务动作：手动刷新事件摘要，引用已有调查结果；会调用摘要模型，不重跑Case调查。 | `POST /api/v2/investigation/incidents/fbbe6415-3d73-5742-a91a-d1a9617d379d/overview/refresh?include_investigations=true` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/055-overview-refresh.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/055-overview-refresh.response.txt) |
| 56 | 展示读回：查看刚保存的事件概况和来源Run；普通GET不会再生成概况。 | `GET /api/v2/investigation/incidents/fbbe6415-3d73-5742-a91a-d1a9617d379d` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/056-overview-readback.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/056-overview-readback.response.txt) |
| 57 | 历史入口：列出这个Case的Run，供以后定位主调查/追加；不创建Run。 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/057-case-history.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/057-case-history.response.txt) |
| 58 | 事件入口：列出关联Case/Run和范围，让事件层展示调查进展；不执行分析。 | `GET /api/v2/investigation/incidents/fbbe6415-3d73-5742-a91a-d1a9617d379d/investigations` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/058-incident-investigations.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/058-incident-investigations.response.txt) |
| 59 | 测试核对：重读原告警，与开始时比较关键字段；不会再分诊。 | `GET /api/v1/alerts/3fcd245d-0496-54f3-875e-f9a7eb90ae2d` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/059-source-after-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/059-source-after-0.response.txt) |
| 60 | 测试核对：重读原告警，与开始时比较关键字段；不会再分诊。 | `GET /api/v1/alerts/5272ae80-b48e-5ef3-8cdd-805885a558a0` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/060-source-after-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/060-source-after-1.response.txt) |

## 逐项判定

| 检查 | 结果 |
|---|---|
| create: same key returns receipt | 通过 |
| preview: Case members and selection distinct | 通过 |
| main: result readback identical | 通过 |
| main: downloaded report identical | 通过 |
| main: Tool exchange links E1 | 通过 |
| main: source row E2 | 通过 |
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
| followup: result readback identical | 通过 |
| followup: downloaded report identical | 通过 |
| followup: alert index agrees | 通过 |
| followup: incident index agrees | 通过 |
| followup: case index agrees | 通过 |
| followup: valid conclusion completed | 通过 |
| followup: member coverage count | 通过 |
| followup: selected members assessed or unresolved | 通过 |
| followup: previous Run link | 通过 |
| followup: complete historical report retained | 通过 |
| followup: matching query reused | 未通过 |
| followup: original Markdown unchanged | 通过 |
| overview: generated and saved | 通过 |
| overview: new Run cited | 通过 |
| overview: GET preserves text and source metadata | 通过 |
| source Alert unchanged: 3fcd245d-0496-54f3-875e-f9a7eb90ae2d | 通过 |
| source Alert unchanged: 5272ae80-b48e-5ef3-8cdd-805885a558a0 | 通过 |
