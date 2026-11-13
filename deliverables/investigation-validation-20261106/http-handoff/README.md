# 调查服务 HTTP API

合同版本：2026-11-13.docs8。当前本机18024为 `list-query-20261113-r1-local`，21正式18024为 `list-query-20261113-r1`；两端均挂载53操作，本机使用 `v12_upgrade_dev`，21使用 `aisoc`。

本轮补齐E02调查、E26告警、E27事件的全库筛选、排序和分页；外部HTTP路由仍独立于内部调查服务。列表仅查询，不启动调查或修改记录。完整字段、输入输出示例及422错误见Swagger；两端发布状态以[本轮验收](../../../openspec/changes/archive/2026-11-13-query-investigation-lists/validation.md)为准。

标准Swagger入口：[本地](http://127.0.0.1:18080/)、[21内网](http://192.168.1.21:18080/)。共53个HTTP操作，按告警、事件、调查分类；适用于告警和事件的共用读取接口会在两组中出现。

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
| 后端内网对接 | `http://192.168.1.21:18024` | 正式`aisoc`；版本`list-query-20261113-r1`，53操作 |
| 本机转发到21 | `http://127.0.0.1:28024` | 同一正式库；需开启`deploy/http-service/relay.json`对应转发 |
| 本机开发验收 | `http://127.0.0.1:18024` | 隔离`v12_upgrade_dev`；本地记录ID与21不通用 |

旧主API18000和旧独立API18020保持运行；后者仍是旧隔离库，不作为本次对接入口。对外查询和业务操作由独立HTTP包维护，调查内部步骤及组件HTTP保持原归属，见[代码与调用边界](../../../docs/design/investigation-http-boundary.md)。本轮没有启动消费者或自动调查。

JSON请求使用`Content-Type: application/json`，身份沿用现有`Authorization: Bearer <有效凭据>`。后端通过HTTP对接，资产基础资料和人员目录由业务后端负责。

## 常见调用顺序

1. 告警：列表E26 → 详情E28 → 分诊目录E22 → 指定Run E24 → 步骤E32/工件E33。
2. 事件：列表E27 → 详情E29 → 诊断目录E23 → 指定Run E25 → 步骤E32/工件E33。
3. 调查：创建E01 → 读取案件E03及Run E12 → 显式启动E13 → 读取结果E14/工件E15。创建本身不执行调查。
4. 人工任务：读取案件版本E03 → 创建E38；更新前读任务E41，完整提交E40；历史版本读取E42/E43。

5. Case管理：E44读取版本和结案条件 → E45局部修改；E46结案、E47重开 → E03/E44读回；历史理由和前后值通过E17读取。当前50个已实现操作、3个预留501。

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

例如 `GET /api/v1/socai2/alerts?severity=high&sort_by=event_time&sort_order=desc&limit=20`。读取items后，将响应的next_cursor原样URL编码为cursor，保留原筛选和排序取下一页；null表示结束。变更条件清空游标。查询不改变overall_stats/metrics统计范围；不提供冻结快照导出。等级排序为info<low<medium<high<critical，空值始终最后，同值按同方向UUID排序。

告警/事件旧limit+before_id调用保留；before_id与新筛选、排序或cursor混用返回422。Case未使用新增日期/排序的原v1游标仍可续页。非法日期、枚举和排序返回422；无效新游标为invalid_list_cursor，跨条件为list_cursor_filters_changed；旧Case错误码保留。
