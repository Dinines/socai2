# 网络记录命中与追加查询复用：逐步测试记录

数据：已有模拟案例。批次`INVHTTP-20261028-01`，通过常驻18000/18010真实HTTP与API Key执行。

流程判定：**未全部通过**。Case `a280c884-0abd-458d-bb66-13c06fe9ca5b`；来源事件`fbbe6415-3d73-5742-a91a-d1a9617d379d`。

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

下面的请求JSON在发送前写入，因此保留pending标记；最终HTTP状态和检查结果以[本例summary](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/summary.json)为准。响应文件是调用脚本去掉其附加换行后的HTTP原始正文。

| 步骤 | 方法与路径 | HTTP | 输入 | 实际返回 |
|---:|---|---:|---|---|
| 1 | `GET /api/v1/alerts/3fcd245d-0496-54f3-875e-f9a7eb90ae2d` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/001-source-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/001-source-0.response.txt) |
| 2 | `GET /api/v1/alerts/5272ae80-b48e-5ef3-8cdd-805885a558a0` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/002-source-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/002-source-1.response.txt) |
| 3 | `GET /api/v2/investigation/incidents/fbbe6415-3d73-5742-a91a-d1a9617d379d` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/003-incident-before.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/003-incident-before.response.txt) |
| 4 | `GET /api/v2/investigation/alerts/3fcd245d-0496-54f3-875e-f9a7eb90ae2d/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/004-alert-context-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/004-alert-context-0.response.txt) |
| 5 | `GET /api/v2/investigation/alerts/5272ae80-b48e-5ef3-8cdd-805885a558a0/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/005-alert-context-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/005-alert-context-1.response.txt) |
| 6 | `POST /api/v2/investigation/case-links` | 201 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/006-create-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/006-create-case.response.txt) |
| 7 | `POST /api/v2/investigation/case-links` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/007-create-repeat.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/007-create-repeat.response.txt) |
| 8 | `GET /api/v1/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/008-case-core-link.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/008-case-core-link.response.txt) |
| 9 | `GET /api/v2/investigation/case-links?incident_id=fbbe6415-3d73-5742-a91a-d1a9617d379d` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/009-case-links.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/009-case-links.response.txt) |
| 10 | `POST /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigation-context` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/010-preview.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/010-preview.response.txt) |
| 11 | `POST /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/011-main.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/011-main.response.txt) |
| 12 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/012-main-result.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/012-main-result.response.txt) |
| 13 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/report` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/013-main-report.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/013-main-report.response.txt) |
| 14 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps?limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/014-main-steps.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/014-main-steps.response.txt) |
| 15 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/015-main-step-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/015-main-step-1.response.txt) |
| 16 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/016-main-step-2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/016-main-step-2.response.txt) |
| 17 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/3` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/017-main-step-3.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/017-main-step-3.response.txt) |
| 18 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/4` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/018-main-step-4.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/018-main-step-4.response.txt) |
| 19 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/5` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/019-main-step-5.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/019-main-step-5.response.txt) |
| 20 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/6` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/020-main-step-6.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/020-main-step-6.response.txt) |
| 21 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/7` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/021-main-step-7.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/021-main-step-7.response.txt) |
| 22 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/8` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/022-main-step-8.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/022-main-step-8.response.txt) |
| 23 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/9` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/023-main-step-9.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/023-main-step-9.response.txt) |
| 24 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/steps/10` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/024-main-step-10.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/024-main-step-10.response.txt) |
| 25 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/025-main-evidence-list.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/025-main-evidence-list.response.txt) |
| 26 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/A1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/026-main-evidence-A1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/026-main-evidence-A1.response.txt) |
| 27 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/A2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/027-main-evidence-A2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/027-main-evidence-A2.response.txt) |
| 28 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/028-main-evidence-E1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/028-main-evidence-E1.response.txt) |
| 29 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/029-main-evidence-E2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/029-main-evidence-E2.response.txt) |
| 30 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/evidence/E2/rows/0` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/030-main-row-E2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/030-main-row-E2.response.txt) |
| 31 | `GET /api/v2/investigation/executions?alert_id=3fcd245d-0496-54f3-875e-f9a7eb90ae2d&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/031-main-index-alert.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/031-main-index-alert.response.txt) |
| 32 | `GET /api/v2/investigation/executions?incident_id=fbbe6415-3d73-5742-a91a-d1a9617d379d&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/032-main-index-incident.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/032-main-index-incident.response.txt) |
| 33 | `GET /api/v2/investigation/executions?case_id=a280c884-0abd-458d-bb66-13c06fe9ca5b&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/033-main-index-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/033-main-index-case.response.txt) |
| 34 | `POST /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/034-main-repeat.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/034-main-repeat.response.txt) |
| 35 | `POST /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigate` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/035-followup.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/035-followup.response.txt) |
| 36 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/036-followup-result.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/036-followup-result.response.txt) |
| 37 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/report` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/037-followup-report.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/037-followup-report.response.txt) |
| 38 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/steps?limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/038-followup-steps.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/038-followup-steps.response.txt) |
| 39 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/steps/1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/039-followup-step-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/039-followup-step-1.response.txt) |
| 40 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/steps/2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/040-followup-step-2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/040-followup-step-2.response.txt) |
| 41 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/steps/3` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/041-followup-step-3.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/041-followup-step-3.response.txt) |
| 42 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/steps/4` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/042-followup-step-4.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/042-followup-step-4.response.txt) |
| 43 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/steps/5` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/043-followup-step-5.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/043-followup-step-5.response.txt) |
| 44 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/steps/6` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/044-followup-step-6.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/044-followup-step-6.response.txt) |
| 45 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/steps/7` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/045-followup-step-7.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/045-followup-step-7.response.txt) |
| 46 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/046-followup-evidence-list.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/046-followup-evidence-list.response.txt) |
| 47 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/A1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/047-followup-evidence-A1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/047-followup-evidence-A1.response.txt) |
| 48 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/A2` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/048-followup-evidence-A2.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/048-followup-evidence-A2.response.txt) |
| 49 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/H1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/049-followup-evidence-H1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/049-followup-evidence-H1.response.txt) |
| 50 | `GET /api/v2/investigation/executions?alert_id=3fcd245d-0496-54f3-875e-f9a7eb90ae2d&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/050-followup-index-alert.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/050-followup-index-alert.response.txt) |
| 51 | `GET /api/v2/investigation/executions?incident_id=fbbe6415-3d73-5742-a91a-d1a9617d379d&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/051-followup-index-incident.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/051-followup-index-incident.response.txt) |
| 52 | `GET /api/v2/investigation/executions?case_id=a280c884-0abd-458d-bb66-13c06fe9ca5b&limit=50` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/052-followup-index-case.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/052-followup-index-case.response.txt) |
| 53 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/H1` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/053-history-evidence.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/053-history-evidence.response.txt) |
| 54 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/d957313e-b528-585c-9254-cd7bb8675da7/report` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/054-original-report-after-followup.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/054-original-report-after-followup.response.txt) |
| 55 | `POST /api/v2/investigation/incidents/fbbe6415-3d73-5742-a91a-d1a9617d379d/overview/refresh?include_investigations=true` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/055-overview-refresh.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/055-overview-refresh.response.txt) |
| 56 | `GET /api/v2/investigation/incidents/fbbe6415-3d73-5742-a91a-d1a9617d379d` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/056-overview-readback.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/056-overview-readback.response.txt) |
| 57 | `GET /api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/057-case-history.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/057-case-history.response.txt) |
| 58 | `GET /api/v2/investigation/incidents/fbbe6415-3d73-5742-a91a-d1a9617d379d/investigations` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/058-incident-investigations.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/058-incident-investigations.response.txt) |
| 59 | `GET /api/v1/alerts/3fcd245d-0496-54f3-875e-f9a7eb90ae2d` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/059-source-after-0.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/059-source-after-0.response.txt) |
| 60 | `GET /api/v1/alerts/5272ae80-b48e-5ef3-8cdd-805885a558a0` | 200 | [请求](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/060-source-after-1.request.json) | [返回](../../operations/evidence/INVHTTP-20261028-01/results/network-positive-reuse/060-source-after-1.response.txt) |

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
