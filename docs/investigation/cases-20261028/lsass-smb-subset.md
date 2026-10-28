# LSASS读取与SMB访问，验证成员子集：逐步测试记录

数据：已有模拟案例。批次`INVHTTP-20261028-01`，通过常驻18000/18010真实HTTP与API Key执行。

流程判定：**通过**。Case `623b13e4-7b9e-4de2-8148-c91ff73299a3`；来源事件`ddd24cf9-f413-4de5-bea5-333f8c080187`。

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

下面的请求JSON在发送前写入，因此保留pending标记；最终HTTP状态和检查结果以[本例summary](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/summary.json)为准。响应文件是调用脚本去掉其附加换行后的HTTP原始正文。

| 步骤 | 方法与路径 | HTTP | 输入 | 实际返回 |
|---:|---|---:|---|---|
| 1 | `GET /api/v1/alerts/c929a0c7-69b5-5617-b830-a701e8bae72f` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/001-source-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/001-source-0.response.txt) |
| 2 | `GET /api/v1/alerts/6b9b6217-fdd6-59a0-b02f-93267050cd5f` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/002-source-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/002-source-1.response.txt) |
| 3 | `GET /api/v2/investigation/incidents/ddd24cf9-f413-4de5-bea5-333f8c080187` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/003-incident-before.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/003-incident-before.response.txt) |
| 4 | `GET /api/v2/investigation/alerts/c929a0c7-69b5-5617-b830-a701e8bae72f/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/004-alert-context-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/004-alert-context-0.response.txt) |
| 5 | `GET /api/v2/investigation/alerts/6b9b6217-fdd6-59a0-b02f-93267050cd5f/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/005-alert-context-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/005-alert-context-1.response.txt) |
| 6 | `POST /api/v2/investigation/case-links` | 201 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/006-create-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/006-create-case.response.txt) |
| 7 | `POST /api/v2/investigation/case-links` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/007-create-repeat.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/007-create-repeat.response.txt) |
| 8 | `GET /api/v1/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/008-case-core-link.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/008-case-core-link.response.txt) |
| 9 | `GET /api/v2/investigation/case-links?incident_id=ddd24cf9-f413-4de5-bea5-333f8c080187` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/009-case-links.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/009-case-links.response.txt) |
| 10 | `POST /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/010-preview.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/010-preview.response.txt) |
| 11 | `POST /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/011-main.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/011-main.response.txt) |
| 12 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/012-main-result.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/012-main-result.response.txt) |
| 13 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/report` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/013-main-report.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/013-main-report.response.txt) |
| 14 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps?limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/014-main-steps.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/014-main-steps.response.txt) |
| 15 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/015-main-step-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/015-main-step-1.response.txt) |
| 16 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/016-main-step-2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/016-main-step-2.response.txt) |
| 17 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/3` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/017-main-step-3.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/017-main-step-3.response.txt) |
| 18 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/4` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/018-main-step-4.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/018-main-step-4.response.txt) |
| 19 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/5` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/019-main-step-5.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/019-main-step-5.response.txt) |
| 20 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/6` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/020-main-step-6.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/020-main-step-6.response.txt) |
| 21 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/7` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/021-main-step-7.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/021-main-step-7.response.txt) |
| 22 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/8` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/022-main-step-8.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/022-main-step-8.response.txt) |
| 23 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/9` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/023-main-step-9.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/023-main-step-9.response.txt) |
| 24 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/10` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/024-main-step-10.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/024-main-step-10.response.txt) |
| 25 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/11` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/025-main-step-11.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/025-main-step-11.response.txt) |
| 26 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/12` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/026-main-step-12.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/026-main-step-12.response.txt) |
| 27 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/steps/13` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/027-main-step-13.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/027-main-step-13.response.txt) |
| 28 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/evidence` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/028-main-evidence-list.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/028-main-evidence-list.response.txt) |
| 29 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/evidence/A1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/029-main-evidence-A1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/029-main-evidence-A1.response.txt) |
| 30 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/evidence/T1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/030-main-evidence-T1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/030-main-evidence-T1.response.txt) |
| 31 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/evidence/E1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/031-main-evidence-E1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/031-main-evidence-E1.response.txt) |
| 32 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations/c973bbbb-7bfb-599b-9cc9-56051ec378b2/evidence/E2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/032-main-evidence-E2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/032-main-evidence-E2.response.txt) |
| 33 | `GET /api/v2/investigation/executions?alert_id=c929a0c7-69b5-5617-b830-a701e8bae72f&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/033-main-index-alert.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/033-main-index-alert.response.txt) |
| 34 | `GET /api/v2/investigation/executions?incident_id=ddd24cf9-f413-4de5-bea5-333f8c080187&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/034-main-index-incident.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/034-main-index-incident.response.txt) |
| 35 | `GET /api/v2/investigation/executions?case_id=623b13e4-7b9e-4de2-8148-c91ff73299a3&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/035-main-index-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/035-main-index-case.response.txt) |
| 36 | `POST /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/036-main-repeat.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/036-main-repeat.response.txt) |
| 37 | `GET /api/v2/investigation/executions?alert_id=6b9b6217-fdd6-59a0-b02f-93267050cd5f&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/037-unselected-index.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/037-unselected-index.response.txt) |
| 38 | `POST /api/v2/investigation/incidents/ddd24cf9-f413-4de5-bea5-333f8c080187/overview/refresh?include_investigations=true` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/038-overview-refresh.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/038-overview-refresh.response.txt) |
| 39 | `GET /api/v2/investigation/incidents/ddd24cf9-f413-4de5-bea5-333f8c080187` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/039-overview-readback.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/039-overview-readback.response.txt) |
| 40 | `GET /api/v2/investigation/cases/623b13e4-7b9e-4de2-8148-c91ff73299a3/investigations` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/040-case-history.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/040-case-history.response.txt) |
| 41 | `GET /api/v2/investigation/incidents/ddd24cf9-f413-4de5-bea5-333f8c080187/investigations` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/041-incident-investigations.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/041-incident-investigations.response.txt) |
| 42 | `GET /api/v1/alerts/c929a0c7-69b5-5617-b830-a701e8bae72f` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/042-source-after-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/042-source-after-0.response.txt) |
| 43 | `GET /api/v1/alerts/6b9b6217-fdd6-59a0-b02f-93267050cd5f` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/043-source-after-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/lsass-smb-subset/043-source-after-1.response.txt) |

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
