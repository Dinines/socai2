# Office启动PowerShell后外联：逐步测试记录

数据：已有模拟案例。批次`INVHTTP-20261028-01`，通过常驻18000/18010真实HTTP与API Key执行。

流程判定：**未全部通过**。Case `be4aeda2-a89b-47e6-a6f9-285b1a7e8723`；来源事件`7bde0c0b-0d18-4abc-9382-9752f2ae5e98`。

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

下面的请求JSON在发送前写入，因此保留pending标记；最终HTTP状态和检查结果以[本例summary](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/summary.json)为准。响应文件是调用脚本去掉其附加换行后的HTTP原始正文。

| 步骤 | 方法与路径 | HTTP | 输入 | 实际返回 |
|---:|---|---:|---|---|
| 1 | `GET /api/v1/alerts/4c71eec2-77da-5b81-b68a-72801d55ea24` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/001-source-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/001-source-0.response.txt) |
| 2 | `GET /api/v1/alerts/f7af404b-26a6-5d15-bd6c-3a872bdaf451` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/002-source-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/002-source-1.response.txt) |
| 3 | `GET /api/v2/investigation/incidents/7bde0c0b-0d18-4abc-9382-9752f2ae5e98` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/003-incident-before.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/003-incident-before.response.txt) |
| 4 | `GET /api/v2/investigation/alerts/4c71eec2-77da-5b81-b68a-72801d55ea24/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/004-alert-context-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/004-alert-context-0.response.txt) |
| 5 | `GET /api/v2/investigation/alerts/f7af404b-26a6-5d15-bd6c-3a872bdaf451/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/005-alert-context-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/005-alert-context-1.response.txt) |
| 6 | `POST /api/v2/investigation/case-links` | 201 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/006-create-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/006-create-case.response.txt) |
| 7 | `POST /api/v2/investigation/case-links` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/007-create-repeat.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/007-create-repeat.response.txt) |
| 8 | `POST /api/v2/investigation/case-links` | 201 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/008-attach-members.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/008-attach-members.response.txt) |
| 9 | `GET /api/v1/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/009-case-core-link.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/009-case-core-link.response.txt) |
| 10 | `GET /api/v2/investigation/case-links?incident_id=7bde0c0b-0d18-4abc-9382-9752f2ae5e98` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/010-case-links.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/010-case-links.response.txt) |
| 11 | `POST /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/011-preview.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/011-preview.response.txt) |
| 12 | `POST /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/012-main.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/012-main.response.txt) |
| 13 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/013-main-result.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/013-main-result.response.txt) |
| 14 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/report` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/014-main-report.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/014-main-report.response.txt) |
| 15 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps?limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/015-main-steps.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/015-main-steps.response.txt) |
| 16 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/016-main-step-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/016-main-step-1.response.txt) |
| 17 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/017-main-step-2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/017-main-step-2.response.txt) |
| 18 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/3` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/018-main-step-3.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/018-main-step-3.response.txt) |
| 19 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/4` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/019-main-step-4.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/019-main-step-4.response.txt) |
| 20 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/5` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/020-main-step-5.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/020-main-step-5.response.txt) |
| 21 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/6` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/021-main-step-6.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/021-main-step-6.response.txt) |
| 22 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/7` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/022-main-step-7.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/022-main-step-7.response.txt) |
| 23 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/8` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/023-main-step-8.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/023-main-step-8.response.txt) |
| 24 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/9` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/024-main-step-9.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/024-main-step-9.response.txt) |
| 25 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/steps/10` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/025-main-step-10.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/025-main-step-10.response.txt) |
| 26 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/026-main-evidence-list.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/026-main-evidence-list.response.txt) |
| 27 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/A1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/027-main-evidence-A1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/027-main-evidence-A1.response.txt) |
| 28 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/T1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/028-main-evidence-T1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/028-main-evidence-T1.response.txt) |
| 29 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/A2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/029-main-evidence-A2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/029-main-evidence-A2.response.txt) |
| 30 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/T2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/030-main-evidence-T2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/030-main-evidence-T2.response.txt) |
| 31 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/E1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/031-main-evidence-E1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/031-main-evidence-E1.response.txt) |
| 32 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/E2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/032-main-evidence-E2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/032-main-evidence-E2.response.txt) |
| 33 | `GET /api/v2/investigation/executions?alert_id=4c71eec2-77da-5b81-b68a-72801d55ea24&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/033-main-index-alert.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/033-main-index-alert.response.txt) |
| 34 | `GET /api/v2/investigation/executions?incident_id=7bde0c0b-0d18-4abc-9382-9752f2ae5e98&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/034-main-index-incident.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/034-main-index-incident.response.txt) |
| 35 | `GET /api/v2/investigation/executions?case_id=be4aeda2-a89b-47e6-a6f9-285b1a7e8723&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/035-main-index-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/035-main-index-case.response.txt) |
| 36 | `POST /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/036-main-repeat.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/036-main-repeat.response.txt) |
| 37 | `POST /api/v2/investigation/incidents/7bde0c0b-0d18-4abc-9382-9752f2ae5e98/overview/refresh?include_investigations=true` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/037-overview-refresh.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/037-overview-refresh.response.txt) |
| 38 | `GET /api/v2/investigation/incidents/7bde0c0b-0d18-4abc-9382-9752f2ae5e98` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/038-overview-readback.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/038-overview-readback.response.txt) |
| 39 | `POST /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/039-followup.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/039-followup.response.txt) |
| 40 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/040-followup-result.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/040-followup-result.response.txt) |
| 41 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/report` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/041-followup-report.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/041-followup-report.response.txt) |
| 42 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/steps?limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/042-followup-steps.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/042-followup-steps.response.txt) |
| 43 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/steps/1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/043-followup-step-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/043-followup-step-1.response.txt) |
| 44 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/steps/2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/044-followup-step-2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/044-followup-step-2.response.txt) |
| 45 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/steps/3` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/045-followup-step-3.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/045-followup-step-3.response.txt) |
| 46 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/steps/4` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/046-followup-step-4.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/046-followup-step-4.response.txt) |
| 47 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/steps/5` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/047-followup-step-5.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/047-followup-step-5.response.txt) |
| 48 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/evidence` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/048-followup-evidence-list.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/048-followup-evidence-list.response.txt) |
| 49 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/evidence/A1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/049-followup-evidence-A1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/049-followup-evidence-A1.response.txt) |
| 50 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/evidence/T1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/050-followup-evidence-T1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/050-followup-evidence-T1.response.txt) |
| 51 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/evidence/A2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/051-followup-evidence-A2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/051-followup-evidence-A2.response.txt) |
| 52 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/evidence/T2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/052-followup-evidence-T2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/052-followup-evidence-T2.response.txt) |
| 53 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/evidence/H1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/053-followup-evidence-H1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/053-followup-evidence-H1.response.txt) |
| 54 | `GET /api/v2/investigation/executions?alert_id=4c71eec2-77da-5b81-b68a-72801d55ea24&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/054-followup-index-alert.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/054-followup-index-alert.response.txt) |
| 55 | `GET /api/v2/investigation/executions?incident_id=7bde0c0b-0d18-4abc-9382-9752f2ae5e98&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/055-followup-index-incident.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/055-followup-index-incident.response.txt) |
| 56 | `GET /api/v2/investigation/executions?case_id=be4aeda2-a89b-47e6-a6f9-285b1a7e8723&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/056-followup-index-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/056-followup-index-case.response.txt) |
| 57 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/5d6f28ea-d7f4-572e-b2e5-5c0013475396/evidence/H1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/057-history-evidence.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/057-history-evidence.response.txt) |
| 58 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/report` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/058-original-report-after-followup.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/058-original-report-after-followup.response.txt) |
| 59 | `GET /api/v2/investigation/incidents/7bde0c0b-0d18-4abc-9382-9752f2ae5e98` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/059-overview-after-new-run.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/059-overview-after-new-run.response.txt) |
| 60 | `GET /api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/060-case-history.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/060-case-history.response.txt) |
| 61 | `GET /api/v2/investigation/incidents/7bde0c0b-0d18-4abc-9382-9752f2ae5e98/investigations` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/061-incident-investigations.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/061-incident-investigations.response.txt) |
| 62 | `GET /api/v1/alerts/4c71eec2-77da-5b81-b68a-72801d55ea24` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/062-source-after-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/062-source-after-0.response.txt) |
| 63 | `GET /api/v1/alerts/f7af404b-26a6-5d15-bd6c-3a872bdaf451` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/063-source-after-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/office-powershell/063-source-after-1.response.txt) |

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
