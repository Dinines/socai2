# AiSOC 前端页面交接

**直接双击本文件夹中的 `index.html`，即可浏览当前页面。** 默认进入告警列表，左侧可以切换告警、事件和 Case。也可以先打开 [guide.html](guide.html)，点击页面或文档入口。

这是当前 `127.0.0.1:4173` 静态前端的完整副本，包含 HTML、CSS、JavaScript、图标和展示数据。无需登录、后端连接、Node 或 npm 安装。请发送和保留**整个文件夹**，不要只发送一个 HTML 文件。

## 打开方式

### 方式一：直接打开

双击 [index.html](index.html)。页面链接、弹窗、抽屉、筛选等仍可操作；修改只影响当前浏览器的本地数据。浏览器禁止本地保存时，本次打开仍可浏览，关闭后修改不会保留。

### 方式二：和当前 4173 预览一样

如果本机浏览器限制本地 HTML，或希望通过 `http://127.0.0.1:4173` 浏览，在**这个文件夹**打开终端，运行：

```bash
python3 serve.py
```

Windows 安装了 Python 3 时也可使用：

```powershell
py -3 serve.py
```

然后打开 [本地预览](http://127.0.0.1:4173/)。这个命令只启动静态文件服务，并不是业务后端。结束时在终端按 Ctrl+C。

若 4173 已被占用，运行 `python3 serve.py --port 4174`（Windows 对应 `py -3 serve.py --port 4174`），然后打开 `http://127.0.0.1:4174/`。

## 页面与文档入口

| 想查看什么 | 页面 | 对应说明 |
| --- | --- | --- |
| 告警列表、抽屉 | [告警](index.html#/alerts) | [页面功能](docs/page-guide.html#alerts)、[九列字段对照](docs/data-mapping.html#list) |
| 告警详情：概况 / 时间线 / 原始数据 / 响应 | [Office 告警详情](index.html#/alerts/4c71eec2-77da-5b81-b68a-72801d55ea24/overview) | [详情字段对照](docs/data-mapping.html#detail) |
| 未关联 Case 的设计样例 | [Web 服务器告警](index.html#/alerts/alert-unassigned-case-001/overview) | [Case 关联交互](docs/page-guide.html#detail) |
| 事件列表与详情 | [事件列表](index.html#/incidents)、[事件详情](index.html#/incidents/262144/attack) | [事件功能](docs/page-guide.html#incidents) |
| Case 列表与详情 | [Case 列表](index.html#/cases)、[Case 详情](index.html#/cases/17420/overview) | [Case 功能](docs/page-guide.html#cases) |
| 微软产品、图谱和Case功能拆解 | — | [详细分析](docs/microsoft-incident-case-analysis.html) |
| 资产详情占位页 | [资产详情](index.html#/assets/d1) | [资产说明](docs/page-guide.html#assets) |
| 原先逐项讨论的完整字段文档 | — | [详细对照参考](docs/alert-ui-data-contract.html) |
| 数据文件与实际处理边界 | — | [数据说明](data/README.html) |

## 文件位置

- `index.html`、`styles.css`、`icons.js`、`assets/`：页面入口、样式、图标。
- `workspace-model.js`、`workspace-view.js`、`workspace.css`：事件/Case图谱关系、调查材料、任务及局部样式。
- `app.js`：列表、事件、Case、抽屉和路由；`alert-detail.js`：告警详情。
- `data.js`：原来的设计样例；`replayed-alerts.js`：后来追加的 6 条测试告警实际处理结果。页面直接读取这两个文件，**不会请求 JSON 文件或数据库**。
- `docs/`：页面功能、当前字段对照，以及原详细文档的便携参考副本。`.html` 可直接浏览，`.md` 可编辑。
- `data/`：同一批数据的 JSON 阅读副本、实际 Explain 返回、20/21 比较和只读 SQL。
- `serve.py`：可选静态预览服务；`package.json`、`tests/`：已有前端检查入口。
- `MANIFEST.json`：文件摘要和复制来源。

## 交接口径

初始数据保留 **52 条设计样例 + 6 条实际处理结果，共 58 条告警**。事件、Case 仍各有 12 条设计样例；其后台取数尚未在本次页面中对接。6 条实际处理结果来自测试输入，不代表真实攻击。

管理告警、分配、Case 关联、反馈、响应审批等按钮是前端交互演示，不会写回数据库或启动新调查。Explain 展示已保存的接口返回，不会在这个离线包中重新调用模型。后台应按字段对照文档继续实现取数与写回。

本地修改会保存在浏览器里。如要恢复交付时的数据，点击页面左下角“重置数据”。请勿手工更改原始 JS 数据来代替后台接口。

交付日期：2026-10-25。当前对接口径以 [data-mapping.html](docs/data-mapping.html) 为准；原详细文档保留了带日期的讨论过程，旧 ID、旧库存数量及已被后续决定覆盖的说明只作历史参考。

本批事件/Case对齐：关系可查看实体和关联告警；关联范围仅扩展视图；潜在路径与已发生的活动分开。调查按成员告警计算，任务可本地添加和更新，管理Case可保存期限和结案说明，关闭Case不自动关闭告警。20不纳入本批；详细来源和限制见微软分析文档。
