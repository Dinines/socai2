# 完整列表导出设计

2026-11-13，目标设计，完成与发布事实另见validation。前置：[列表查询验收](../2026-11-13-query-investigation-lists/validation.md)。

## 1 调用与结果

新增 E54 `GET /api/v1/socai2/alerts/export`、E55 `/incidents/export`、E56 `/cases/export`。分别沿用E26/E27/E02的q、severity、handling_status、owner_id、assignment_state、time_from/time_to、sort_by/sort_order；Case另保留metric/classification。不接受limit、cursor、before_id/offset，以免调用方将某页误认为完整导出。`columns`为逗号分隔的公开字段路径，省略用默认列；空列、重复、未知列或分页参数422。

CSV UTF-8带BOM、逗号分隔、CRLF换行，首行为稳定字段路径。响应Content-Type为text/csv，Content-Disposition为attachment；X-Export-Count为数据行数，X-Export-Observed-At为快照观察时间，X-Export-Schema为socai2.list-export.v1。空结果返回列头及0行，不是404。

## 2 字段范围与表示

告警允许现有AlertFacts全部字段（facts.前缀）及owner_name；默认id/title/severity/event_time/handling_status/category/original_vendor/connector_type/source_namespace/owner_id/owner_name/assignment_state/tags/business_updated_at。事件允许IncidentFacts、owner_name及已有derived中的member_count/first_activity_at/last_activity_at/severity_auto/severity_effective/severity_source；默认展示身份、标题、有效等级及来源、成员数、首尾真实发生时间、状态、负责人/分配、标签与创建/更新时间。Case允许CaseView全部字段（case.前缀）及现有member_count/open_task_count；默认身份、标题、状态、等级、负责人/分配、分类、期限、两项数量、标签与创建/更新时间。

列名直接沿用已有公开JSON字段路径，语义不变；资产标签不混为facts.tags，资产明细仍由业务后端维护与既有E30读取，不复制维护接口。材料原件、模型正文和附件不是列表CSV列。未来扩列按公开合同评审，不由表新增列自动暴露。

null写为`\N`，空字符串保留空单元格，0/false保留，数组/对象为JSON文本，时间保留时区。原字符串开头的反斜杠加倍以区分字面`\N`；可能被表格软件作为公式解释的文本及原先单引号开头文本加一个前导单引号（业务原件不改），交接写明解码规则。标准CSV转义保留逗号、引号、中文和换行。

## 3 读一致性与代码归属

抽出不改变行为的主体选择表达式，由现有列表与导出共用；Case复用queue_filters及排序规则。在同租户REPEATABLE READ/READ ONLY事务内计算命中数、选取全部记录和观察时间，采用实际SQL字段排序及同方向UUID决胜；事件窗口仍为同一成员命中，未知时间不补入库时间，空值最后。

导出核心返回已有字段组成的记录及观察时间；CSV序列化、下载头、参数错误属于investigation_http。独立路由优先于`/{id}`注册，原53操作合同保持。外部适配器直接调用导出用例；调查核心不导入外部HTTP包。

配置文件list_export.json显式设置max_rows=10000、max_bytes=16777216、statement_timeout_ms=30000，profile指定SOCAI2_EXPORT_CONFIG_FILE；服务读取配置，不在路由硬编码预算。超行数或CSV大小返回413 export_row_limit_exceeded/export_size_limit_exceeded；查询超时503 export_query_timeout。所有检查在返回200前完成，失败无半份文件；不为本批引入任务队列或新表。

## 4 直接验收及交付

新本机合成批次覆盖超过旧50行分页、筛选排序与列表逐值对应、事件覆盖/日期、Case原筛选、明确列、空结果、null/空串/0、中文/换行/引号及公式文本；真实TCP读取CSV并与PG及列表对照，前后业务行保持。对配置上限、非法参数和路由优先级做必要定向检查；复用既有列表/HTTP边界测试，不调用模型。

完成文档和未参与实现者独审后，一次发布本地/21独立服务及Swagger；21复用既有合成主体只读验收，不新写正式库。基于已发布list-query镜像只覆盖本批明确文件，排除工作区并行模型修改。读回版本/CSV/源码和Swagger后收口归档，再按本轮继续推进的授权统一Git同步。回退仅恢复上一个独立API和文档版本，无数据迁移。
