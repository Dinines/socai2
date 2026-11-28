# SpiritHub 事件成员汇总前端交接

2026-11-25。8181 工作树候选基线为 `8051df5008af9e711a2c71890ad9bf111ff82301`。本步在事件专属类型中接入 `derived.active_member_count`、`unknown_status_member_count` 和 `detection_sources`，供事件列表和摘要复用。[实施方案](incident-integration-acceptance-plan-20261125.md#当前实施列表活跃成员与检测源汇总) · [检查回执](../../../docs/operations/evidence/incident-member-aggregates-20261125-01/frontend-result.json)

- 活跃和全部分别读取事件聚合。实值零保留，缺字段或空值显示未提供。存在未知状态成员时附简短提示。全部继续读 `derived.member_count`。
- 列表的「服务 / 检测源」为可选列。启用后和摘要都展示服务返回的同一集合，供数为空显示「暂无检测源」，缺字段或空值显示「未提供」。CSV 继续采用既有字段映射，新增导出列及筛选列在后续步骤接入。
- 首次隔离浏览器检查时，事件列设置弹层定位在视口之外，检测源选项无法点击。事件列表启用按触发按钮定位的选项，空间不足时向上翻转，清单按当前视口可用高度滚动。共享组件的默认定位沿原行为。

## 检查范围

严格 OpenSpec 校验、TypeScript、三个受影响的列表及摘要用例通过。用例复用现有合成记录，覆盖双计数、状态未知、空与缺字段、可选列、事件身份和同筛选 CSV 原字段映射。隔离 Chrome 使用既有受控响应，核对弹层在按钮下方打开、空间不足时沿按钮翻转、滚动启用检测源，以及列表字段与同事件摘要显示。

现有 8181 可见列表中，表头和计数单元格位置一致，全部数为零的反馈当时未复现。前端请求路径为 `GET /api/v1/socai2/incidents`，经 Vite `/api` 到 SpiritHub 后端。已确认源码右侧绑定 `derived.member_count`。该次实际页面查看的范围是列结构与零值复现，同记录 HTTP 响应值与 DOM 读回仍待受控连读。21 继续按已发布版本验收。[既有代理核对回执](../../../docs/operations/evidence/incident-detail-ui-20261125-01/user-feedback-review.json)
