# 调查服务 HTTP API

> 2026-11-14：本轮接口按默认内部可信改动，以下调用示例无需认证信息；本机候选已验证。正式两端18024及在线Swagger仍为上一发布版本，尚未统一切换；本轮不涉及Git提交。
候选合同版本：2026-11-14.docs20-candidate，71个HTTP操作。对应本机18024 `investigation-sync-20261113-r1-local`、21正式18024 `investigation-sync-20261113-r1`。数据库分别为v12_upgrade_dev与aisoc，记录ID不可混用；实际发布回执见[总交接](../../../FRONTEND_BACKEND_HANDOFF.md)。

本轮同步已发布调查核心`v1.2-20261113-r1`。E36分析告警、E37诊断事件、E13启动调查的地址和输入输出保持；内部使用新版分析逻辑。C3模型处理五项问题，程序补充覆盖说明，保存和读取仍六问。调用方继续先取得主体/Run ID，按原operation_key和范围版本调用，再读取运行状态和结果；超时先读原Run，不换key重启。本轮只做现有记录的接口读回，没有新增模型验收，正文质量问题仍后置。
本轮新增[E70告警相似历史复核](../../../docs/integration/alert-review-http.md)：同主机且同战术、同IP或合法算法哈希，默认按所选告警发生时间回看30天、每页5条；返回具体匹配依据，不自动复制判定。已完成本机23次功能GET及10表只读核对，正式本机8GET命中3条，21既有记录5GET为空候选。E65故事、E66候选及E67–E69保存恢复沿既有验收。AI对话暂缓，E19/E20返回501。

标准Swagger入口：[本地](http://127.0.0.1:18080/)、[21内网](http://192.168.1.21:18080/)。按告警、事件、调查分类；适用于告警和事件的共用读取接口会在两组中出现，70为去重后的操作数。

## 每个接口怎么看

展开接口即可查看：用途、输入参数、输出结构、操作后的结果、实现状态、请求/响应示例和错误。固定字段解释在Schema中；随分区或工件类型变化的字段在Responses说明中。示例是合成合同示例，需要替换为实际ID和版本。

- **已实现**：接口逻辑已提供。执行结果及结论是否有效以返回状态为准。
- **未实现**：E19发送问题、E20保存回答目前返回501，不产生对应业务结果。
- E36告警分诊、E37事件诊断在21独立正式服务已挂载并启用；由业务后端显式调用，可以来自页面操作或后端业务逻辑。调用后程序执行该次模型流程，返回Run及实际结果状态。

当前71个操作中69已实现、2问答暂缓且预留501。采用预览→确认→保存→详情/历史/活动的真实HTTP与SQL证据见本轮交付回执；本地程序构造Result不代表模型分析质量。其他接口沿既有验收，模型质量仍未通过。故事已通过本机30次HTTP功能检查及补充1次GET/11表真实行核对，原快照脚本错误保留。实际上线状态以[总交接](../../../FRONTEND_BACKEND_HANDOFF.md)与部署回执为准。

## HTTP接入

业务路径前缀为`/api/v1/socai2`。Swagger的Servers按实际调用环境选择；18080只提供文档。

| 使用环境 | API根地址 | 数据目标 |
| --- | --- | --- |
| 后端内网对接 | `http://192.168.1.21:18024` | 正式`aisoc`；版本`investigation-sync-20261113-r1`，71操作 |
| 本机转发到21 | `http://127.0.0.1:28024` | 同一正式库；需开启`deploy/http-service/relay.json`对应转发 |
| 本机开发验收 | `http://127.0.0.1:18024` | 隔离`v12_upgrade_dev`；本地记录ID与21不通用 |

旧主API18000和旧独立API18020保持运行；后者仍是旧隔离库，不作为本次对接入口。对外查询和业务操作由独立HTTP包维护，调查内部步骤及组件HTTP保持原归属，见[代码与调用边界](../../../docs/design/investigation-http-boundary.md)。本轮没有启动消费者或自动调查。

JSON请求使用`Content-Type: application/json`；内部默认可信，不需要认证头，租户和记录操作人由服务配置提供。后端通过HTTP对接，资产基础资料和人员目录由业务后端负责。

## 常见调用顺序

1. 告警：列表E26 → 详情E28 → 分诊目录E22 → 指定Run E24 → 步骤E32/工件E33。
2. 事件：列表E27 → 详情E29 → 诊断目录E23 → 指定Run E25 → 步骤E32/工件E33。
3. 调查：创建E01 → 读取案件E03及Run E12 → 显式启动E13 → 读取结果E14/工件E15。创建本身不执行调查。
4. 人工任务：读取案件版本E03 → 创建E38；更新前读任务E41，完整提交E40；历史版本读取E42/E43。
5. Case管理：E44读取版本和结案条件 → E45局部修改；E46结案、E47重开 → E03/E44读回；历史理由和前后值通过E17读取。

6. 采用结果：E63预览 → E21提交预览摘要/理由/必要未完确认 → E03当前判断、E64判断历史、E17活动。旧E21占位体expected_scope_revision已停用；完整字段与错误见[采用操作指南](../../../docs/integration/result-adoption-http.md)。

7. 案件探索：E66查询候选 → E28/E30/E31核对详情、全部对象及材料 → E03读最新范围版本 → 明确E08加入 → E03/E66读回；保存画布使用E67读取底图→E68保存→E69恢复；不必加入成员。

8. 相似历史复核：E70查候选 → E28打开候选、E31按材料ID核原件 → 用户确认后E48/E49反馈；当前判定不会自动应用到候选。

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
  --data-urlencode 'severity=high' \
  --data-urlencode 'sort_by=event_time' \
  --data-urlencode 'sort_order=desc' \
  --data-urlencode 'columns=facts.id,facts.title,facts.severity,facts.event_time' \
  --output alerts.csv
```

`API`选择上述实际环境；先检查HTTP状态，失败保存的内容是错误JSON，不能作为CSV交付。此下载流程不需要先翻页列表。

## 事件归并统计

`E57 GET /api/v1/socai2/incidents/grouping-summary`用于事件页顶部的“处理中”和“队列压缩”，不修改任何归并关系，也不启动模型。

输入只支持`source_namespace`、`time_from`、`time_to`，都可省略。来源按告警来源精确匹配、区分大小写；时间按告警真实发生时间，须带时区，起点包含、终点不含，允许单边。时间筛选排除未知时间，无时间筛选则包含。它不接收事件表格的q、负责人、状态、排序或分页，额外参数返回422；不把两个列表统计拼接起来。

| 输出 | 含义 |
| --- | --- |
| schema_version | 固定`socai2.incident-grouping.v1` |
| scope | 实际来源与UTC时间条件，省略项为null |
| alert_count | 范围内告警总数 |
| grouped_alert_count | 其中当前已经关联事件的不同告警数 |
| ungrouped_alert_count | 其中尚未关联事件的告警数，两者合计等于总数 |
| incident_count | 上述已归并告警关联的不同事件数；空事件不计 |
| in_progress_incident_count | 上述事件中业务状态为in_progress的数量 |
| compression_rate | `(grouped_alert_count-incident_count)/grouped_alert_count`，0..1，乘100显示百分比；没有已归并告警时null |
| observed_at | 同一次只读快照的观察时间 |

例如6条告警中4条归为2个事件、2条未归并，压缩比例为0.5，即“4条成员告警归为2个事件，压缩50%；另有2条未归并”。不能说全部6条都压缩了50%。该比例不是准确率、误报率或解决率。

跨时间或来源的事件只计算范围内成员，事件去重计一次；已解决事件仍属于归并数量，处理中只按实际in_progress计算。无范围内成员的事件不计；Case/Run状态不参与。无命中返回各数量0和比例null，不是404。

```http
GET /api/v1/socai2/incidents/grouping-summary?source_namespace=example&time_from=2026-11-13T00%3A00%3A00Z&time_to=2026-11-14T00%3A00%3A00Z
```

非法日期、空白来源、起点不早于终点或不支持的参数返回422；读取功能关闭、依赖缺失/结构不符返回503。错误与完整示例见E57的Swagger Responses。

## Case普通评论

E58 `POST /api/v1/socai2/cases/{case_id}/comments` 输入真实Case ID和JSON：

```json
{"operation_key":"00000000-0000-4000-8000-000000000901","body":"请运维核实维护窗口；本条为协作说明，尚未核实。"}
```

正文非空白、最多20000字符，保留换行与首尾内容，调用方按纯文本显示。服务保存作者ID、当时登录标识和创建时间，返回完整评论；不能从客户端指定作者。操作键相同且作者/正文相同返回原评论，换内容或作者返回409，不重复增加评论。

E59 `GET /api/v1/socai2/cases/{case_id}/comments?limit=20&offset=0` 只读本案评论，按创建时间和ID升序。返回items、total、next_offset和observed_at；按next_offset继续，null表示结束。limit为1–100，offset为0–100000，其他参数422；无评论明确返回空集合，Case不存在404。

普通评论允许补充到已结案Case，更新业务时间及Case行版本；处理状态、当前判断、成员、任务和Run保持，不自动重开或分析。E17读取提交活动；评论自身row_version不是Case版本。现有任务事实仍经任务接口保存。

评论仅支持提交及阅读，不含编辑/删除。文件本体及下载由业务后端承接；附件引用现使用E60–E62。提交评论不能显示成文件上传成功。

## Case附件引用

附件是用户给案件补充的文件，例如运维工单PDF、截图或日志。业务后端负责上传、保存和下载；调查服务负责记录文件与案件的关联。

1. 业务后端先完成文件保存，取得稳定`file_id`，确保文件属于当前业务范围。
2. E60 `POST /api/v1/socai2/cases/{case_id}/attachments`登记`operation_key`、`file_id`、`file_name`、`mime_type`、`size_bytes`及可选`sha256`。返回`id`是附件关联ID，`file_id`仍是业务后端文件ID。
3. E61 `GET`同路径按`limit/offset`读取目录；E62 `GET /api/v1/socai2/cases/{case_id}/attachments/{attachment_id}`读取单项元数据。E17读取登记活动和回执。
4. 用户下载时，由业务后端根据`file_id`提供文件；文件失效也由业务后端处理。本服务不保存或返回下载URL，不抓取文件。

大小、类型和哈希按业务后端提供的值保存；`availability=managed_by_backend`只表示由后端管理，不代表本服务探测文件存在或下载成功。`created_by/created_at`由服务端记录，是登记人/时间。未知哈希返回null；零字节文件允许size_bytes=0。

同key同作者同元数据重试返回原记录；改意图409，同案同file_id另key重复登记409，读取目录获取原关联。文件内容变化须使用新file_id；本批没有附件修改、删除或自动分析。空白/非法元数据422，错误或跨案附件404；正文和任务结论保持。附件登记成功后可以查看关联，不代表上传和下载完整链路已经验收。

[E71同主机最近7条](../../../docs/integration/alert-host-http.md)：仅输入alert_id，无时间窗或分页参数，按当前已存记录发生时间排序，返回原告警和双方主机来源。不同战术仍可匹配；E70相似复核规则保持。
