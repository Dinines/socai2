# V1 冻结与 V2 事件/调查前端交付回执

日期：2026-10-26。授权：用户要求将当前前端保存为 V1，再在新端口修改优化；告警页面保持。前置[功能分析](incident-investigation-page-analysis.md)的全部规划不作为本批全部实现承诺。

## 版本与实现

- 冻结 `prototypes/security-pages-v1` 与 `deliverables/aisoc-frontend-v1`，共 52 份源文件；ZIP 298943 字节，SHA-256 `ae2e2c5898469431152ecc748002be42e730e5dd6f98560a995ca5004a394fe9`。清单见 `deliverables/frontend-v1-manifest.json`。原目录未覆盖。
- V1 在本机 4173，V2 在 4174；独立目录与 localStorage 键。浏览器原状态未清理，文件快照不包含用户本地存储导出。
- 事件保留原功能，攻击故事入口改为事件上下文，补材料概况、调查摘要及按种子/窗口查看候选关系的 Chain 页签。
- Case 首屏改为 AI 调查，旧概览移至资料概览；原告警、资产、关系图、任务、证据、活动、评论保留。新增全部运行及无 Case Run 入口。
- 调查按 Run 组织结果与范围、实际输入、分析过程、工具与证据、Chain / Path、报告与响应。6 条实际 Run 从已有回执白名单投影，另保留 2 条设计样例。
- 实际保存输入来自 `run.raw_alert`；输入摘要来自 `run.alert_summary`。不根据当前告警重建历史输入；标题与长摘要分开展示。

## 数据与状态核对

样例 `d141b0e3-16cc-5a0b-8d7f-35159342efe6`：Run completed，调查 partial，判定 needs_review，Graph confidence 0.75；首次分诊 TP/0.85，7 次调用、29025 tokens、7 次未定价。停止原因保留 `token budget exhausted (26922 of 20000)`，不改写旧预算或运行结果。

同 Run 的 attack_chain 为 empty/PostgreSQL，候选 0、24h；attack_path 为 not_linked/no_linked_case；alert_graph 为 success/Neo4j，邻居 5、可达 6、最大深度 3、原始评分 3.1。IOC 使用 `indicator_value`，关系类型使用 `rel_type`；不套用 0—1 评分假设。工具返回中的空行、不可用、查询失败及 200 字符摘要限制保持。

事件 Chain 属于本地设计样例的共享实体/时间窗口筛选，不是正式服务端候选链算法。实际 Run 工件独立展示。报告保持已保存原文，可能保留当时 `running` 和历史措辞；当前 Run 状态和完整性另列，不追认报告语义质量。建议隔离与实际执行 0 分开。

## 直接验证

| 检查 | 结果及范围 |
| --- | --- |
| V1 文件与 ZIP | 52 份源文件/冻结文件逐字节 SHA-256 一致，ZIP 每个成员一致；原目录保持 |
| JavaScript 语法 | `npm run check` 通过 |
| 定向回归 | `npm test` 18/18 通过 |
| 告警保持 | 同输入下 1 个列表、58 个抽屉、58×4 个详情，291 次 HTML 与 V1 一致；告警模块、数据、基础样式原文件未改 |
| 调查视图 | 8 个 Run × 5 页签可渲染，状态不混写、无 Case 不补造 Case、无效/越界 Run 不回落其他运行 |
| 关系与输入 | Case 计数和正文关联一致，候选链筛选不改成员、不造分数；历史输入不受当前告警修改影响；HTML 转义通过 |
| 源值独审 | 6 条真实 Run 140 项字段/工具/图/报告比较无差异；6 条原始输入白名单投影一致 |
| 浏览器 | V1 原事件页面可打开；V2 Case 首屏及调查图谱实际可见；实际工具参数/摘要、报告/建议/执行可见；运行切换到未升级调查时工具数变为 0，标题、结果和范围同步切换 |
| Chain 交互 | 种子切换为未关联 Case 的 Web 告警、窗口切为 1 小时，显示没有候选关系；URL 保留种子和窗口 |

截图留于 `.local/verification/frontend-v2-20261026/case-overview.png` 和 `run-graphs.png`。浏览器核验只证明本地展示与相应交互，不代表服务端流程验收。报告下载入口已展示；未单独验证浏览器下载落盘。

## 问题修正与独立审阅

首次本地服务器绑定因沙箱限制失败，随后使用已批准的同一 loopback 启动命令成功。一次源码替换定位断言失败发生在写入前，随后按实际源码接线；没有覆盖原版文件。

未参与实现的 `workspace_review` 复核了 V1、实际投影、Run 范围和回归，提出 IOC/关系字段、真实 Run 计数、错误 Run 回落、历史输入缺少以及过长标题问题；均修正并复核。最终结论为限定 ACCEPT、0 项剩余必须修。独审执行 17 项既有测试通过；随后追加输入独立性用例，主验 18 项通过。最终交接文档及新增用例窄复核通过，13 个本地链接有效，维持限定 ACCEPT、0 个新增必须修。

## 交接与限制

入口见[版本说明](../../prototypes/FRONTEND-VERSIONS.md)与[V2 README](../../prototypes/security-pages-v2/README.md)。没有后端源码/运行配置变更、新查询/模型/数据重放、生产写入、部署或 Git 提交/推送。此次不是全 22 项调查规划验收；实时状态刷新、完整模型材料、调查 v2 后端入口/领域 profile、Case 服务端关联与响应执行仍由各自模块承接。

OpenSpec 已归档：[`2026-10-26-version-frontend-v1-optimize-v2`](../../openspec/changes/archive/2026-10-26-version-frontend-v1-optimize-v2/verification.md)，新增 3 条规格已同步；严格检查结果见该批回执。
