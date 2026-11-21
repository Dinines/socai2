# 21 告警、事件和 Case 后端联调清单

适用发布版本为 `c173-release-20261121-03`，业务代码提交为 `3fe265d07`。告警、事件和 Case 页面通过 21 的正式 HTTP 联调。

## 我方交付

| 资料 | 地址或用法 |
| --- | --- |
| 正式 API | `http://192.168.1.21:18024/api/v1/socai2`。带 JSON 请求体时用 `Content-Type: application/json`。 |
| 接口文档与导入 | OpenAPI 可导入接口工具或用于生成客户端。服务器填 `http://192.168.1.21:18024`，文档路径已含 `/api/v1/socai2`。[在线 Swagger](http://192.168.1.21:18080/) · [OpenAPI JSON 下载](http://192.168.1.21:18080/handoff/openapi.json) · [仓库同版 OpenAPI](../../deploy/aisoc21/c173-release-20261121-03/contract/openapi.json) |
| 页面功能逐项映射 | 按告警、事件、Case 三类页面和功能编号查取数、写入、跳转及分页接口。功能目的与字段对照参见两份索引，接口路径和请求字段以本次正式 OpenAPI 为准。[页面功能映射](product-api-data-requirements-20261114.md#7-125项逐项归属) · [页面跳转规格](../../deliverables/investigation-validation-20261106/frontend-data-navigation-contract.md#跳转与关联规格) |
| 异步任务与调查记录 | [发起事件诊断与案件调查](analysis-submission-http.md#目标功能与路径) · [分析任务字段](analysis-tasks-http.md#任务详情字段) · [统一 Run 目录](run-directory-http.md#输入参数) · [步骤与工件](run-records-http.md#用途与调用) |
| 验收回执 | 正式 HTTP 和 Swagger 同版，共 82 个操作。已完成隔离环境的真实告警联验，以及正式告警、事件和 Case 的读取核对。[正式发布清单](../../deploy/aisoc21/c173-release-20261121-03/release.json) · [联验与正式读回](../operations/evidence/c173-bounded-json-20261121-01/README.md) |

## 页面怎么调用

以下路径均相对于 `/api/v1/socai2`。

| 页面功能 | HTTP 接口和参数 |
| --- | --- |
| 实时告警列表、详情、导出 | 页面刷新时带当前筛选调用 `GET /alerts` 取库中数据，取告警的 `facts.id` 调用 `GET /alerts/{alert_id}`。CSV 导出用 `GET /alerts/export`，沿用列表筛选和排序。 |
| 告警原文、分诊和关联 | 从详情沿材料的 `content_url` 取原文，或用 `GET /alerts/{alert_id}/materials/{material_id}`。分诊和历史用 `GET /alerts/{alert_id}/analysis`。事件、Case、对象和资产等沿详情的 `section_urls` 读取。 |
| 告警复核和管理 | `GET /alerts/{alert_id}/review-candidates`、`GET /alerts/{alert_id}/same-host-alerts` 读取相似告警与同主机告警。分诊反馈用 `POST /alerts/{alert_id}/feedback`，管理用 `PATCH /alerts/{alert_id}/management`，批量操作用 `POST /alerts/feedback-batch`、`POST /alerts/management-batch`。 |
| 事件列表、归并、详情与管理 | `GET /incidents`、`GET /incidents/grouping-summary`、`GET /incidents/{incident_id}`、`GET /incidents/export`。用事件的 `facts.id` 打开详情。管理用 `PATCH /incidents/{incident_id}/management` 或 `POST /incidents/management-batch`。成员、活动、资产及关联 Case 使用 `section_urls`。 |
| 事件诊断 | `POST /incidents/{incident_id}/diagnose` 提交 `mode=check` 或 `rerun`，返回 202。当前及历史诊断用 `GET /incidents/{incident_id}/analysis`，单轮沿任务返回的结果地址读取。 |
| Case 列表、详情与概览 | `GET /cases`、`GET /cases/{case_id}`、`GET /cases/{case_id}/page-data`、`GET /cases/export`。用 Case 的 `case.id` 打开详情，读取当前采用的判断、成员和关联事件。案件故事用 `GET /cases/{case_id}/story`。 |
| 建案、关联与后轮调查 | `POST /cases` 返回 201 和 `allocations[]`。按分配项的 `case_id`、`case_url` 进入案件，首轮进度沿 `initial_task.status_url` 读取。关联、替换、移动成员分别用 `POST /cases/{case_id}/associations`、`PUT /cases/{case_id}/members`、`POST /cases/{case_id}/members/move`。已有案件后轮用 `POST /cases/{case_id}/investigations`，返回 202。 |
| Case 管理与协作 | 管理用 `GET /cases/{case_id}/management` 和 `PATCH /cases/{case_id}/management`，关闭或重开用 `POST /cases/{case_id}/close` 或 `POST /cases/{case_id}/reopen`。普通人工任务用 `GET /cases/{case_id}/tasks` 和 `POST /cases/{case_id}/tasks`，评论用 `GET /cases/{case_id}/comments` 和 `POST /cases/{case_id}/comments`。 |
| Case 结果与采用 | `GET /cases/{case_id}/history` 读历史，`GET /cases/{case_id}/results/{result_id}` 读指定结果。用户采用前先 `GET /cases/{case_id}/results/{result_id}/adoption-preview`。允许采用时调用 `POST /cases/{case_id}/results/{result_id}/adopt`，提交 `operation_key`、`reason`，并把 `review_token` 原值传为 `expected_review_token`。如预览要求确认未完成工作，在用户确认后提交 `acknowledge_pending_work=true`。 |
| Case 证据与探索 | Case 概览的 `evidence` 返回证据索引，发布索引用 `POST /cases/{case_id}/evidence-index`。`GET /cases/{case_id}/related-cases` 查关联案件。探索候选和基础图用 `GET /cases/{case_id}/exploration-candidates`、`GET /cases/{case_id}/exploration-base`，已保存视图用 `GET /cases/{case_id}/exploration` 读取、`PUT /cases/{case_id}/exploration` 保存。 |
| 任务、轮次与原件 | 三类主体的任务详情都跟随 `status_url`，轮次跟随尝试中的 `run_url` 或统一目录的 `detail_url`，已保存结果跟随 `results[].url`。统一查询用 `GET /analysis-runs`，步骤和工件用服务返回的 `steps_url`、`artifacts_url`，原件用 `content_url`。 |
| 日志湖取数 | `POST /lake/events/search` 按明确的来源、映射版本、带时区时间范围和可选对象查询。需要原文时跟随 `material_url`，保留查询返回的版本和时间参数。 |

事件诊断和 Case 后轮使用相同请求结构。每次新操作生成新的 `operation_key`，同一请求重放沿用原键和原参数。

```json
{
  "operation_key": "00000000-0000-4000-8000-000000000701",
  "mode": "check"
}
```

从事件建 Case 的请求示例。以下 UUID 只用于说明格式，联调时使用所选事件的真实 `incident_id` 和本次操作 UUID。

```json
{
  "operation_key": "00000000-0000-4000-8000-000000000902",
  "title": "示例调查",
  "incident_ids": ["00000000-0000-4000-8000-000000000901"]
}
```

查询旧日志湖的请求示例。替换为页面选择的带时区时间范围。查询其他已配置来源时使用该来源的 `source_namespace`、`mapping_version` 和时间口径。

```json
{
  "source_namespace": "",
  "mapping_version": "",
  "time_basis": "legacy_event",
  "start": "2026-11-20T00:00:00+08:00",
  "end": "2026-11-20T01:00:00+08:00",
  "limit": 1
}
```

## 页面跳转示例

以下 C173 原型路由由我方提供。原型地址用页面记录的显示 ID，HTTP 用接口返回的业务 UUID。HTTP 路径的公共前缀为 `/api/v1/socai2`。

| 点击目标 | C173 原型地址 | 正式 HTTP 与入参 |
| --- | --- | --- |
| 告警详情 | `#/alerts/{A}/overview` | 用选中告警的 `facts.id` 请求 `GET /alerts/{alert_id}`。 |
| 事件详情 | `#/incidents/{I}/summary` | 用选中事件的 `facts.id` 请求 `GET /incidents/{incident_id}`。 |
| Case 详情 | `#/cases/{C}/case-info` | 用 `case.id` 请求 `GET /cases/{case_id}`。建案回执的 `allocations[]` 提供对应的 `case_id` 和 `case_url`。 |
| Case 历史中的指定轮次 | `#/cases/{C}/investigations?run={R}&view=overview` | 用所属 `case_id` 和所选 `run_id` 请求 `GET /cases/{case_id}/runs/{run_id}`。成员告警或事件的轮次沿各自的 `run_url` 或 `detail_url`。打开已保存结果时沿 `results[].url`。 |

产品前端接线时沿用上表的业务 ID 和接口返回链接。联调按同一组参数核对 HTTP 响应、记录归属及空态。[现有跳转与关联规格](../../deliverables/investigation-validation-20261106/frontend-data-navigation-contract.md#跳转与关联规格)

## 联调时保留的业务状态

- 201 表示完成建案分配，202 表示任务已受理。显示最新进度时读取 `status_url`。排队或准备阶段 `latest_run_id` 可以为 `null`，结果未形成时 `results` 为 `[]`。
- 告警、事件和 Case 的 ID 分开传递。轮次、结果、材料和工件保留所属主体和响应链接，页面回退后仍定位到原来那一轮。保持筛选不变，按列表合同用 `next_cursor` 或 `next_offset` 请求下一页。
- 处理状态、任务状态、交付状态和业务判定分开展示。事件详情读 `business_verdict`，Case 概览读 `assessment.business_verdict`，指定 Case 结果读 `result.business_verdict`。值为 `malicious`、`benign`、`false_positive`、`needs_review` 或 `null`。诊断失败时仍可读事件、告警、失败原因和已保存原件。该轮未生成的判定和正文显示为空态，既有结论沿原记录读取。Case 可以基于现有材料继续调查，并保留上游缺口。
- 管理写入按 Schema 带 `operation_key` 和相应版本，例如 `expected_row_version`。收到 409 时先读最新主体或范围，重新确认操作。404 显示记录不存在，422 展示字段校验问题，读取超时或依赖错误保留失败状态。HTTP 请求结果不明时沿原操作键查询或重放原请求。

## 请业务后端提供

| 待回填 | 请业务后端确认 |
| --- | --- |
| 人员 | 确认负责人搜索和按 ID 查询的入口，给出可写入 `owner_id` 的人员 UUID、显示名和可分配状态。 |
| 资产 | 确认资产查询和详情入口，给出 `asset_id` 对应的主键、主机名/FQDN、IP、标签和页面所需详情字段的映射。说明无匹配、多匹配的返回。 |
| 联调数据 | 确认实际联调地址和对应租户或组织。给一组脱敏样例，覆盖可分配人员、资产命中及查无匹配。若实际使用库表或视图供数，请给数据库地址、库名、schema、表或视图名和字段映射。 |

SpiritHub 已有人员列表及详情 `GET /api/v1/admin/users` 和 `GET /api/v1/admin/users/{user_id}`，以及资产列表及详情 `GET /api/v1/assets` 和 `GET /api/v1/assets/{asset_id}`。请确认采用的现有入口。[SpiritHub OpenAPI](https://github.com/wangjuelong26/SpiritHub/blob/14053d46bb362e5c45441d87699c0e3c44f84a45/schemas/platform-api.v1.json)

## Kafka 日志接入

当前由 Vector 从 SpiritHub 的 Redpanda 转发。上游直写待联验。发送服务位于 21 且接入同机 Kafka Docker 网络时，可以使用下面的已核对配置。其他部署环境按发送端所在位置核实可达入口。[21 Kafka 内部连接](../operations/deployment-datastores.md#21-kafka-内部连接)

| 项目 | 21 同机接入 |
| --- | --- |
| Docker 网络 | `sting-infra21_default` |
| Broker | `kafka:29092` |
| 协议 | `PLAINTEXT` |
| 正式接收 Topic | `socai2.spirithub.events-ocsf-v1` |
| 消息格式 | OCSF 1.9.0，每条消息承载一个 JSON 对象 |

请后端确认发送服务所在环境及联调时间，提供一条脱敏 OCSF 样例、时间字段和单位、`metadata.uid` 与 Kafka Key 的规则。重试发送同一记录时保持 ID 和 Key。正式切换前确认首批范围和源端分界。

我方提供独立测试 Topic。试发后对照投递回执的 Topic、分区、offset 和 `metadata.uid` 核验接收。正式切换时，等 Vector 确认分界前的记录已送达后停用，直写从分界后的记录开始。双方按 `metadata.uid` 核对切换窗口的漏发和重复。

调查报告、步骤记录和已保存的模型回执沿 Run 的步骤及工件接口读取。按已确认范围，附件、登录、来源与执行次数统计移出本期，AI 聊天、人工定向分析和真实响应审批执行继续暂缓。

## 联调检查

从能访问 21 的环境进行只读检查。

```sh
api='http://192.168.1.21:18024'
curl -fsS "$api/readyz"
for resource in alerts incidents cases; do
  curl -fsS "$api/api/v1/socai2/$resource?limit=1"
done
```

- [ ] 列表、详情和关联跳转沿返回的真实 ID。同一事件改动后的读取仍对应原事件，同一调查轮次的工件能回到原轮次。
- [ ] 用测试记录验证建案首轮或已有对象的检查任务。由受理回执读任务、Run 和已保存结果，并验证重复键和版本冲突。
- [ ] 核对正常、有数据但待复核、未生成、失败和空列表的展示。正式库空态按实际返回读取。
- [ ] 人员按返回 ID 分配并读回名称。资产分别核一组命中和无匹配，确认标签及资产详情跳转。
