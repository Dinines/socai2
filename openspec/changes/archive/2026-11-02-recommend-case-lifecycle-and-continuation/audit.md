# Case生命周期与多轮调查建议回执

2026-11-02。仅文档：第32节推荐规则、第31.5后续指引、顶部入口及AGENTS/PROGRESS续接。当前Case本地赋值、已有未发布v4设计与本轮新增建议分别注明；不将用户事件规则自动套给Case或告警。

## 只读依据
核workspace-view.js管理表单、workspace-model.js updateCase、app.js save-scope；v4调查规划1.3—1.4已有单一活跃Case Run/新轮继承材料设计。复用第30节已核A/B/C初始样例，不访问实时系统或改变样例。

## 验证与边界
实施前OpenSpec strict通过。文档结构/链接/场景、代码未改与独立结束审阅结果在实际完成后补记。不运行前端或业务测试，不操作浏览器，无新查询、模型、Case/Run/任务、响应、部署、提交推送；不以旧94测试证明本提案已实现。

第32节6小节、4处本地来源链接、A/B/C场景标识及顶部锚点检查通过；`git diff --check`及`git diff --quiet HEAD -- prototypes/security-pages-v2 services`通过；增量OpenSpec strict通过。首次检查输出把链接数固定写为5，随后按实际集合重数确认4处，链接有效性检查本身通过；未据该文字计数扩大证据。业务政策仍是建议，未新增行为合同。

## 结束独审
未参与编写者current_workspace_review限定ACCEPT、0必须修。核管理源码、v4 1.3—1.4及A/B/C保存数据，确认本地行为/未发布设计/新推荐分开；Case提案不改告警事件已定规则，单轮、未知启动、历史及遗留工作一致，未虚构执行或授权。链接/锚点/diff-check通过，前端/services相对HEAD无差异。审阅只读，无文件修改、业务测试、浏览器或网络。

## 归档结果
归档前strict通过，使用`openspec archive recommend-case-lifecycle-and-continuation --yes --skip-specs`完成归档，无主规格更新。封后all为9通过/0失败，archived为59通过/0失败；仅文档结构检查，不代表页面或后端功能已验。无Git提交推送。
