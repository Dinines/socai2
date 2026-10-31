# 2026-10-31 事件统计文案与说明浮层回执

用户要求缩短常驻文字、右上角放info并浮动显示详情。常驻“活跃事件、待分配、24h有新告警、高严重程度”；单个ⓘ集中完整定义和全量统计/相互重叠口径。保持原右对齐与四项数字，不改统计函数、数据或其他页面设计。

## 范围与保留

- 页面：prototypes/security-pages-v2/app.js、styles.css、index.html；既有alert-flow.test.cjs仅更新两处短名称预期。
- 改前四文件及hash：.local/versions/incident-metric-labels-before-20261031/；未覆盖历史版本。
- 只改本地前端与交接；无后端、模型、真实数据查询/写入、部署、Git提交推送。

## 直接验证

- npm run check：通过；npm test：71通过、0失败。
- 默认宽度与700px宽度：四指标右边界差0，窄屏两列；浮层宽310px，700px下x=350…660，完整位于视口内。
- 实际浏览器点击/聚焦显示，Tab离开但鼠标仍悬停时保持可见；鼠标和焦点均离开后收起；Escape隐藏且焦点仍在ⓘ，重新聚焦显示。
- .local/verification/incident-metric-help-20261031/保存default.png、tooltip.png、narrow.png、narrow-tooltip.png及geometry.json。
- 未参与实现者current_workspace_review独立窄审：限定ACCEPT、0项必须修；另跑两项定向测试通过、四份改前hash一致，核对统计函数逐字节不变及四张截图。结论仅覆盖本批呈现增量。
