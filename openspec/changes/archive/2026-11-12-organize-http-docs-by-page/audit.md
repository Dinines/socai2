# 功能整理与 HTTP 字段核对的限定独立审阅

审阅者：未参与本项文档实现的 `http_docs_review`。时间：2026-11-12。

## 审阅范围

静态阅读原功能清单的新分组、`http-handoff-audit` 的 README/interfaces/response-fields/dynamic-fields/coverage、原字段跳转附录与业务交接的增补，对照现有路由、固定 DTO、Case/Page 读取装配、当前字段字典和 freshness 实现。未运行测试，未调用业务 API、数据库或模型，未执行部署，也未修改业务代码。

125 项按告警22、事件15、调查88归组，仍保留原功能标识、用途、操作结果、页面与后端状态；没有根据43个已有操作新增产品需求。新资料明确是本地审计补充，原 OpenAPI 与已发布 docs1 保留，未把字段数量或 HTTP 成功当作产品/模型验收。版本化工件、厂商原件及未固定动态正文继续沿原合同解释，没有声称穷举所有历史/外部正文。

主要核对方向包括：Case/A-I 工件外壳与完整性错误不同、E18冻结材料整行、当前判断两种 sources 投影、RunView与trace原行差异、统计分母、H读写引用类型、D07 questions状态及读取截断。相应主要说明与实现一致。

## 初审发现

1. 固定字段表的 CaseQueueMetrics 中，awaiting_assignment/high_severity/awaiting_human漏写 active 条件（handling_status 为 new/in_progress）；awaiting_assignment 还需 owner_id 为 null。实际计数条件必须完整，否则接手人重算指标会不同。
2. AIUnavailable.detail、HTTPValidationError.detail沿用了通用错误的三种detail形状说明。各自字段应明确为固定AIUnavailableDetail对象、ValidationError数组；通用HTTP错误处理在总说明中保留。
3. assessment-sources正文已说明page_data投影含tenant_id，但字段表遗漏该行。应补仅page_data路径包含的tenant_id，同时说明E02/E03嵌套page_data与E05同口径。
4. activity合并说明遗漏operation_id投影差异：E17使用without_internal，实际保留activities.operation_id；E30使用public，剔除此字段。应补字段与适用路径。

以上已反馈主实现者。另建议将input_freshness从“至少state/reasons”明确为当前实现的state（current/stale/unverified）和reasons数组，避免将已知计算字段也泛化为未知正文。

初审结论：修正上述四项后完成限定复阅；不将本审阅表述为全部原页面设计绝无遗漏，也不替代全量运行验证。

## 修正后限定复阅

同日只读复看本次指出的字段：

- CaseQueueMetrics 已完整注明三个 active 条件和待分配的 owner_id=null；处理中指标仍按其实际独立谓词说明。
- AIUnavailable.detail 固定对象与 HTTPValidationError.detail 字段校验数组分开；其他服务错误没有被强套该 DTO。
- assessment-sources 新增 tenant_id 行，明确 E02/E03 内嵌 page_data 和 E05 返回，E03 current_assessment.sources 不返回。
- activity 新增仅 E17 返回的 operation_id，明确 E30 剔除此字段。
- input_freshness.state/reasons 已分别展开，三种状态及已知原因来源明确。required 同时说明原 OpenAPI 规范与当前默认/显式装配的区别，未把规范允许省略误写为服务一定缺字段。

**结论：本 change 的限定文档结束审阅通过，所报阻塞均已修正。** 本结论覆盖当前功能分组和接口审计补充中的上述直接合同问题，不等于原页面设计穷尽审查、每种历史工件正文完全展开或真实运行验收。已发布 docs1 与本地审计补充继续区分；本审阅没有部署、运行测试或调用业务 API、数据库、模型。
