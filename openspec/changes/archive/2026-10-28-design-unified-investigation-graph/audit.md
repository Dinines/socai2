# 设计结束审阅

2026-10-28，本轮仅设计与会话内可点击样稿，未修改4174 V2源码或发布规格。主方案见功能分析第16节；以已有三输入、五候选的同Run历史测试回执核对数据。

未参与实现者 `functional_analysis_save_review` 只读核原件、设计和样稿，并执行本地Node VM窄回归。首项P2为点击关系依据实际选中目标实体，导致多余连线高亮或隐藏层中无高亮。已改为关系ID选择，仅聚焦该边和两端，显示所需图层，关闭所选关系层时清除聚焦。9项交互回归通过。随后发现同端点来源显示混同谓词，修正为分别展示Neo4j原关系和PG TOUCHES（相同端点），不把同端点绘制视为同谓词去重；4项来源回归和语法检查通过。

最终独审限定ACCEPT，0剩余必须修。范围仅数据对应、设计语义与样稿交互，不追认后端、调查质量或现有V2页面已接入统一图。

主代理浏览器确认告警、技术分类、单边两端聚焦、关闭实体层后候选依据恢复可见端点及E3孤立候选说明。1024px桌面与390px窄屏布局已查看，320px内容宽度286/scrollWidth286无横向溢出；控制台error为空，视口已恢复。截图位于 `.local/verification/frontend-v2-unified-graph-design-20261028/alert-focus.png`。

会话样稿位于 `/Users/lychee/.codex/visualizations/2026/10/27/01a17da5-d0fd-79c2-b6b9-ee69095a66ac/investigation-graph-design.html`。临时4175只在本机提供核验，结束停止；原4174保持。过程一次脚本拼接多一个括号，被语法检查捕获后已修正；一次跨iframe DOM读取不支持，改用正式frame locator。没有新业务访问、模型、后端修改、部署、Git提交或推送。

已按纯设计归档，未更新发布规格；封后 `openspec validate --all --strict` 8/8、`--archived --strict` 31/31通过，`git diff --check`无错误。
