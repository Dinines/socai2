# AiSOC 前端 V2：事件与 AI 调查工作区

2026-10-26。用户授权先冻结 V1，再在新端口优化事件和整个 Case 工作区。版本入口与冻结校验见[版本说明](../FRONTEND-VERSIONS.md)，功能设计见[逐项分析](../../docs/design/incident-investigation-page-analysis.md)。

## 启动

```bash
cd /Users/lychee/Documents/project/socai2/prototypes/security-pages-v2
python3 serve.py --port 4174
```

无需安装依赖，也可运行 `npm start`；只监听 `127.0.0.1`。V1 使用 4173，V2 使用 4174 和独立的 `aisoc-workspace-v2` 本地状态键；不清理原版浏览器状态。

## 页面入口与本批变化

| 入口 | 内容 |
| --- | --- |
| [事件上下文](http://127.0.0.1:4174/#/incidents/262144/attack) | 保留告警、实体、关系图和原有筛选；新增材料概况与调查摘要 |
| [事件 Attack Chain](http://127.0.0.1:4174/#/incidents/262144/chain) | 按种子告警、共享实体、前后时间窗口查看候选关系；无因果或恶意概率假设 |
| [Case 工作区](http://127.0.0.1:4174/#/cases/17420/overview) | 首屏为 AI 调查；资料概览、成员告警、资产、图谱、任务、证据、活动和评论保留 |
| [全部调查运行](http://127.0.0.1:4174/#/investigations) | 2 条原设计样例与 6 条既有实际运行；无 Case 的 Run 可独立打开 |
| [实际运行](http://127.0.0.1:4174/#/investigations/d141b0e3-16cc-5a0b-8d7f-35159342efe6/overview) | 保存的输入、结果与范围、分析过程、工具与证据、Chain / Path、报告与响应 |
| [告警](http://127.0.0.1:4174/#/alerts) | 原设计和交互保持，仍为 52 条样例加 6 条实际处理记录 |

选择一次 Run 后，所有调查页签使用同一 Run。Case 当前成员与本次输入分别展示；新增或移动成员不回写旧 Run 输入。明确指定不存在或不在当前范围内的 Run 时显示空态。Case 的调查计数、历史与正文使用同一关联规则。

Run 是否结束、交付是否完整、最终判定、首次分诊、停止原因、调用和 Tokens 分别展示。建议动作与实际执行分别展示。报告使用保存的 Markdown 原文，支持下载；原报告内的历史 `running` 等字段不重写为当前状态。

## 数据来源与边界

- `data.js`、`workspace-model.js` 为既有设计样例；不重新编造模型分析、调用时间、Token 或报告。
- `replayed-alerts.js` 保留 2026-10-25 六条重放的实际告警资料。
- `investigation-data.js` 从本地既有 `observed-final.json` 白名单投影 6 条 Run，不再次访问 20/21 或调用模型。实际输入取该次 `run.raw_alert`，摘要取 `run.alert_summary`，不由当前 Alert 重建。未输出凭据或完整模型 prompt。
- 调查链图读取同 Run 保存的 `attack_chain`、`attack_path`、`alert_graph`，分别显示状态、来源、时间、查询范围及原始结果。链为空、未关联 Case、查询失败、未记录分别表达，不以空图推断安全。
- 事件的 Chain 筛选仅演示已加载样例中的共享实体关系；不等同于 PostgreSQL 的服务端候选链算法，不生成服务端分数。调查中的实际链图保持原值。
- 图可达范围与 blast-radius 原始评分不等于确认受害范围或恶意概率。原有关系图、潜在路径及新 Run 工件视图分别保留。
- v1 工具轨迹可能只有 200 字符摘要，完整模型轨迹、实时服务更新、后端调查 v2 profile 和响应执行不在本批交付范围。实际样例 5 条 partial、1 条未升级调查，不能据页面完整推断调查质量通过。
- 所有管理交互仍只在浏览器本地保存；本批没有后端写回、创建实际 Case、启动调查或执行响应。

## 文件与验证

新增 `investigation-data.js`、`investigation-workspace.js`、限定 `.iv-*` 样式的 `investigation.css`；仅在 `app.js`、`index.html` 接入新视图。原告警渲染模块、数据、基础样式及旧工作区模块字节保持。

```bash
npm run check
npm test
```

18 项定向测试通过，包括 291 次 V1/V2 告警 HTML 一致比较、8 个 Run 的 40 个视图、范围隔离、源字段及保存输入独立性。测试在仓库中与冻结的 `../security-pages-v1` 对照；单独复制本目录仍可预览，跨版本测试需要保留相邻 V1 目录。浏览器核验与独立审阅见[交付回执](../../docs/design/frontend-v2-verification.md)。
