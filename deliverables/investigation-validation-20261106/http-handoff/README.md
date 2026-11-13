# 调查服务 HTTP API

合同版本：2026-11-13.docs9。当前本机18024为 `list-export-20261113-r1-local`，21正式18024为 `list-export-20261113-r1`；两端均挂载56操作，本机使用 `v12_upgrade_dev`，21使用 `aisoc`。

本轮新增E54告警、E55事件、E56调查的完整CSV导出；筛选和排序复用E26/E27/E02，独立HTTP包负责文件响应，内部调查服务仍直接调用。参数、可选列、输入输出示例和错误见Swagger。

标准Swagger入口：[本地](http://127.0.0.1:18080/)、[21内网](http://192.168.1.21:18080/)。共56个HTTP操作，按告警、事件、调查分类；适用于告警和事件的共用读取接口会在两组中出现。

## 每个接口怎么看

展开接口即可查看：用途、输入参数、输出结构、操作后的结果、实现状态、请求/响应示例和错误。固定字段解释在Schema中；随分区或工件类型变化的字段在Responses说明中。示例是合成合同示例，需要替换为实际ID和版本。

- **已实现**：接口逻辑已提供。执行结果及结论是否有效以返回状态为准。
- **未实现**：E19发送问题、E20保存回答、E21采用结果目前返回501，不产生对应业务结果。
- E36告警分诊、E37事件诊断在21独立正式服务已挂载并启用；由业务后端显式调用，可以来自页面操作或后端业务逻辑。调用后程序执行该次模型流程，返回Run及实际结果状态。

原40个已实现操作已有本机原HTTP路由和真实隔离数据库的直接验证；E19–E21已确认501。另在本机TCP及21正式HTTP完成建案、人工任务创建/完成修订、当前和历史读取，保存字段与SQL读回一致，Run未启动。分析执行测试使用模型/查询替身，本轮发布未调用真实模型，真实模型质量仍未通过。展开接口可看对应验证范围；HTTP200仍需结合业务状态。

## HTTP接入

业务路径前缀为`/api/v1/socai2`。Swagger的Servers按实际调用环境选择；18080只提供文档。

| 使用环境 | API根地址 | 数据目标 |
| --- | --- | --- |
| 后端内网对接 | `http://192.168.1.21:18024` | 正式`aisoc`；版本`list-export-20261113-r1`，56操作 |
| 本机转发到21 | `http://127.0.0.1:28024` | 同一正式库；需开启`deploy/http-service/relay.json`对应转发 |
| 本机开发验收 | `http://127.0.0.1:18024` | 隔离`v12_upgrade_dev`；本地记录ID与21不通用 |

旧主API18000和旧独立API18020保持运行；后者仍是旧隔离库，不作为本次对接入口。对外查询和业务操作由独立HTTP包维护，调查内部步骤及组件HTTP保持原归属，见[代码与调用边界](../../../docs/design/investigation-http-boundary.md)。本轮没有启动消费者或自动调查。

JSON请求使用`Content-Type: application/json`，身份沿用现有`Authorization: Bearer <有效凭据>`。后端通过HTTP对接，资产基础资料和人员目录由业务后端负责。

## 常见调用顺序

1. 告警：列表E26 → 详情E28 → 分诊目录E22 → 指定Run E24 → 步骤E32/工件E33。
2. 事件：列表E27 → 详情E29 → 诊断目录E23 → 指定Run E25 → 步骤E32/工件E33。
3. 调查：创建E01 → 读取案件E03及Run E12 → 显式启动E13 → 读取结果E14/工件E15。创建本身不执行调查。
4. 人工任务：读取案件版本E03 → 创建E38；更新前读任务E41，完整提交E40；历史版本读取E42/E43。

5. Case管理：E44读取版本和结案条件 → E45局部修改；E46结案、E47重开 → E03/E44读回；历史理由和前后值通过E17读取。当前53个已实现操作、3个预留501。

管理字段省略保持；可空字段传null清空，标签[]清空。关闭时running/unknown禁止操作；未完任务须明确确认及理由，任务保留。重开恢复处理中，不自动启动调查。

## 返回和错误

- 查询参数、必填项、默认值、枚举及空值要求见对应操作；不要加入未声明字段。
- `operation_key`标识一次逻辑写入，同一意图重试沿用原值。遇到409先读取最新版本，保留输入并核对差异。
- 执行异常或结果未知时先读取原Run，不能换key盲目重新执行。
- HTTP200表示读取/操作请求完成，不等于模型结论有效，也不等于原件正文完整；检查执行状态、校验状态和availability。
- 未解决问题是当轮调查结论的一部分；需要人工核实时由用户创建任务。

[下载OpenAPI](openapi.json) · [输入输出示例](examples.json) · [静态接口说明](endpoints.md) · [字段定义](schemas.md)

## 列表查询怎么用

三个GET接口均支持q、状态、等级、负责人、分配状态、time_from/time_to、sort_by/sort_order、limit和cursor；Case另保留metric/classification。时间必须带时区、起点包含而终点不包含，起点必须早于终点。

| 列表 | 日期含义 | sort_by可选值（首项为默认） | 总数 |
| --- | --- | --- | --- |
| 告警 E26 | 真实event_time，缺失不补入库时间 | ingested_at/event_time/severity | filtered_total为筛选数；total为全部告警数 |
| 事件 E27 | 至少一条成员告警event_time在区间内 | created_at/last_activity_at/severity | filtered_total为筛选数；total为全部事件数 |
| 调查 E02 | business_updated_at | business_updated_at/created_at/severity | total为筛选数；metrics保持整体 |

例如 `GET /api/v1/socai2/alerts?severity=high&sort_by=event_time&sort_order=desc&limit=20`。读取items后，将响应的next_cursor原样URL编码为cursor，保留原筛选和排序取下一页；null表示结束。变更条件清空游标。查询不改变overall_stats/metrics统计范围；跨页请求不是同一冻结快照；需要完整文件使用E54/E55/E56。等级排序为info<low<medium<high<critical，空值始终最后，同值按同方向UUID排序。

告警/事件旧limit+before_id调用保留；before_id与新筛选、排序或cursor混用返回422。Case未使用新增日期/排序的原v1游标仍可续页。非法日期、枚举和排序返回422；无效新游标为invalid_list_cursor，跨条件为list_cursor_filters_changed；旧Case错误码保留。

## 完整列表导出

| 功能 | HTTP | 输入和结果 |
| --- | --- | --- |
| 告警 E54 | `GET /api/v1/socai2/alerts/export` | E26同一筛选与排序，导出全部命中告警 |
| 事件 E55 | `GET /api/v1/socai2/incidents/export` | E27同一筛选与排序，返回成员汇总和等级来源 |
| 调查 E56 | `GET /api/v1/socai2/cases/export` | E02同一筛选与排序，保留metric/classification，含成员数和未完任务数 |

`columns`可选，按逗号分隔字段路径并按此顺序输出，例如告警`facts.id,facts.title,facts.severity`。省略时使用接口列出的默认列；全部可选列及逐字段含义在各接口Responses中（告警39、事件34、调查31）。不能传分页参数limit/cursor/before_id/offset；未知参数、重复/非法列或无效时间返回422。

成功为`text/csv`附件，UTF-8 BOM、逗号分隔、CRLF和字段路径表头；空集合200只有表头。响应头`Content-Disposition`给出文件名，`X-Export-Count`为实际记录数，`X-Export-Observed-At`为同一只读快照观察时间，`X-Export-Schema`为`socai2.list-export.v1`。

CSV中的null写为`\N`，空字符串留空，数组/对象为JSON。实际以反斜杠开头的字符串加一个反斜杠，以单引号开头或可能成为公式的字符串加一个单引号；CSV解析后先识别精确`\N`为空值，再对上述转义去掉一个前缀，按字段类型还原。中文、引号和换行按标准CSV引用规则保留，不能按逗号或换行直接拆文件。

当前最多10000行、16MiB，超限返回413（`export_row_limit_exceeded`或`export_size_limit_exceeded`）；SQL限时30秒，超时503 `export_query_timeout`，不返回截断的成功文件。错误仍为JSON。调整筛选后重新下载；接口只读取，不保存文件、不建任务、不调用模型。限制由服务的`list_export.json`配置。

```sh
curl --fail-with-body --get "$API/api/v1/socai2/alerts/export" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'severity=high' \
  --data-urlencode 'sort_by=event_time' \
  --data-urlencode 'sort_order=desc' \
  --data-urlencode 'columns=facts.id,facts.title,facts.severity,facts.event_time' \
  --output alerts.csv
```

`API`选择上述实际环境，`TOKEN`使用已有凭据；先检查HTTP状态，失败保存的内容是错误JSON，不能作为CSV交付。此下载流程不需要先翻页列表。
