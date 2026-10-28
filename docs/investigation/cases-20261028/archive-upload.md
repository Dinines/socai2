# 服务账号归档与上传，验证缺口和来源边界：逐步测试记录

数据：已有模拟案例。批次`INVHTTP-20261028-01`，通过常驻18000/18010真实HTTP与API Key执行。

流程判定：**通过**。Case `183c059b-2413-4d24-a4aa-dcebe3ad1e55`；来源事件`8db5aafa-011a-47db-9beb-9b16a6f97a1d`。

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

下面的请求JSON在发送前写入，因此保留pending标记；最终HTTP状态和检查结果以[本例summary](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/summary.json)为准。响应文件是调用脚本去掉其附加换行后的HTTP原始正文。

| 步骤 | 方法与路径 | HTTP | 输入 | 实际返回 |
|---:|---|---:|---|---|
| 1 | `GET /api/v1/alerts/6373220a-2f25-541e-ab89-9c3a2e611140` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/001-source-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/001-source-0.response.txt) |
| 2 | `GET /api/v1/alerts/4eb06dee-c5a0-5f08-ace7-08caa2952db5` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/002-source-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/002-source-1.response.txt) |
| 3 | `GET /api/v2/investigation/incidents/8db5aafa-011a-47db-9beb-9b16a6f97a1d` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/003-incident-before.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/003-incident-before.response.txt) |
| 4 | `GET /api/v2/investigation/alerts/6373220a-2f25-541e-ab89-9c3a2e611140/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/004-alert-context-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/004-alert-context-0.response.txt) |
| 5 | `GET /api/v2/investigation/alerts/4eb06dee-c5a0-5f08-ace7-08caa2952db5/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/005-alert-context-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/005-alert-context-1.response.txt) |
| 6 | `POST /api/v2/investigation/case-links` | 201 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/006-create-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/006-create-case.response.txt) |
| 7 | `POST /api/v2/investigation/case-links` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/007-create-repeat.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/007-create-repeat.response.txt) |
| 8 | `GET /api/v1/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/008-case-core-link.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/008-case-core-link.response.txt) |
| 9 | `GET /api/v2/investigation/case-links?incident_id=8db5aafa-011a-47db-9beb-9b16a6f97a1d` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/009-case-links.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/009-case-links.response.txt) |
| 10 | `POST /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/010-preview.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/010-preview.response.txt) |
| 11 | `POST /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/011-main.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/011-main.response.txt) |
| 12 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/012-main-result.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/012-main-result.response.txt) |
| 13 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/report` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/013-main-report.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/013-main-report.response.txt) |
| 14 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps?limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/014-main-steps.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/014-main-steps.response.txt) |
| 15 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/015-main-step-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/015-main-step-1.response.txt) |
| 16 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/016-main-step-2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/016-main-step-2.response.txt) |
| 17 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/3` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/017-main-step-3.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/017-main-step-3.response.txt) |
| 18 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/4` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/018-main-step-4.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/018-main-step-4.response.txt) |
| 19 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/5` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/019-main-step-5.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/019-main-step-5.response.txt) |
| 20 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/6` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/020-main-step-6.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/020-main-step-6.response.txt) |
| 21 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/7` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/021-main-step-7.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/021-main-step-7.response.txt) |
| 22 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/8` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/022-main-step-8.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/022-main-step-8.response.txt) |
| 23 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/9` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/023-main-step-9.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/023-main-step-9.response.txt) |
| 24 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/steps/10` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/024-main-step-10.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/024-main-step-10.response.txt) |
| 25 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/025-main-evidence-list.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/025-main-evidence-list.response.txt) |
| 26 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/026-main-evidence-A1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/026-main-evidence-A1.response.txt) |
| 27 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/T1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/027-main-evidence-T1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/027-main-evidence-T1.response.txt) |
| 28 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/028-main-evidence-A2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/028-main-evidence-A2.response.txt) |
| 29 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/T2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/029-main-evidence-T2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/029-main-evidence-T2.response.txt) |
| 30 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/E1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/030-main-evidence-E1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/030-main-evidence-E1.response.txt) |
| 31 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/E2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/031-main-evidence-E2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/031-main-evidence-E2.response.txt) |
| 32 | `GET /api/v2/investigation/executions?alert_id=6373220a-2f25-541e-ab89-9c3a2e611140&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/032-main-index-alert.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/032-main-index-alert.response.txt) |
| 33 | `GET /api/v2/investigation/executions?incident_id=8db5aafa-011a-47db-9beb-9b16a6f97a1d&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/033-main-index-incident.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/033-main-index-incident.response.txt) |
| 34 | `GET /api/v2/investigation/executions?case_id=183c059b-2413-4d24-a4aa-dcebe3ad1e55&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/034-main-index-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/034-main-index-case.response.txt) |
| 35 | `POST /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/035-main-repeat.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/035-main-repeat.response.txt) |
| 36 | `POST /api/v2/investigation/incidents/8db5aafa-011a-47db-9beb-9b16a6f97a1d/overview/refresh?include_investigations=true` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/036-overview-refresh.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/036-overview-refresh.response.txt) |
| 37 | `GET /api/v2/investigation/incidents/8db5aafa-011a-47db-9beb-9b16a6f97a1d` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/037-overview-readback.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/037-overview-readback.response.txt) |
| 38 | `GET /api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/038-case-history.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/038-case-history.response.txt) |
| 39 | `GET /api/v2/investigation/incidents/8db5aafa-011a-47db-9beb-9b16a6f97a1d/investigations` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/039-incident-investigations.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/039-incident-investigations.response.txt) |
| 40 | `GET /api/v1/alerts/6373220a-2f25-541e-ab89-9c3a2e611140` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/040-source-after-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/040-source-after-0.response.txt) |
| 41 | `GET /api/v1/alerts/4eb06dee-c5a0-5f08-ace7-08caa2952db5` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/041-source-after-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/archive-upload/041-source-after-1.response.txt) |

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
