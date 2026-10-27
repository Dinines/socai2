# Design
按本轮已知编辑逐项逆向恢复app.js/index.html/styles.css/package.json及README；data.js、alert-detail.js与浏览器localStorage保持原状。撤出的快照和渲染器保存到.local证据目录，不再由页面加载。恢复前后均保存hash，不Git reset整目录。服务端数据及重放历史不撤销。

# Validation
语法检查、浏览器确认原列表与操作恢复、无21快照/缺口面板；独立结束审阅后归档。
