# 独立结束审阅

日期：2026-10-28。审阅者：`functional_analysis_save_review`，未参与本轮实现。仅审阅本轮历史 AiSOC20 结果追加及必要展示适配；上一轮 V2 页面组织不重复验收。除本审阅记录外未修改文件，未访问远程服务、调用模型、写业务数据或提交/推送。

## 当前结论

**限定 ACCEPT，0 项剩余必须修。** 初审发现的 P2 已修复并窄复核；后续关系图与时序增量亦已审。浏览器验证与最终交接文档由主代理补入，本记录不代其宣称完成。

1. 已关闭 P2：`prototypes/security-pages-v2/app.js:97` 原 Case 低优先级筛选使用 `row.priority < 15`，本轮新增三个本地 Case 的 `priority: null` 被 JavaScript 按 0 比较。只读 Node VM 曾重现 `local-aisoc20-1/2/3` 全部进入低优先级结果。实现者已在数值区间与最低分筛选前使用 `Number.isFinite`，保持 null；新增回归证明三个未评分 Case 不进入任何数值区间或最低分筛选，清空条件后恢复展示。

## 已核范围和证据

- 阅读本 change 的 proposal/design/tasks/spec、页面讨论原则及适用 AGENTS/OpenSpec 结束审阅要求。
- 审阅 `tools/testdata/export_aisoc20_ui.py`、`aisoc20-data.js` 与 manifest、`recorded-examples.js`、`tests/aisoc20.test.cjs`，以及 app、alert-detail、investigation-workspace、入口加载的本轮相关增量。
- manifest 的 17 份来源文件 SHA-256 与本机原件一致；使用同一 collectedAt 离线重新投影（仅内存，不写输出），数据及 manifest 逐值一致。
- 独立逐 Run 对照原 delivery：身份、状态、完整性、发现、置信度、五份报告、Deep 资料和 34 条工具参数/返回一致。报告正文与对应原 Markdown 原件一致。
- 核实 6 告警、6 Run、3 本地整理 Case、71 事件、34 工具、27 工件、5 报告；36 调用、117286 tokens 与已保存成本汇总一致。5 partial、1 未升级调查；源 Case 均为空，单 Run 仍只有其原告警输入。
- 递归检查本次生成数据，未发现 prompt/response/messages、system_prompt、reasoning_content 或凭据类键；步骤载荷经字段白名单裁剪。没有补造缺失的工件 ID/hash/时间、库存身份或附件。
- 同名告警候选按来源环境与租户隔离；实体 ID 包含来源环境/租户；本地 Case 关系只由指定成员决定，图使用已保存的直接邻接边，与 Run 图材料分别展示。阶段 skipped 显示优先于历史模板 completed 摘要。
- 独立执行 V2 `npm test`：30/30 通过；`npm run check` 通过。现有测试包含 291 次 V1/V2 告警 HTML 比较，新增 6 Run × 6 视图、3 Case × 11 页签、6 告警 × 4 详情页签、幂等追加、无渲染写入、来源隔离、图成员范围、阶段跳过及空元数据。

## 修复与关系图增量复核

- 按用户预览反馈追加的设计与分析第14节已阅读。AiSOC20 Run 的 `graphs` 仍为空；“攻击链与路径”直接展示历史快照中已有实体关系和告警时序，明确说明不属于本次 Run 产生的路径。路径已跳过状态保留，不生成分析结果或因果边。
- SVG 只绘制 `aisoc20RecordedData.graph` 的已有边和对应节点；案件图按当前成员过滤，调查页明确区分当前 Case 成员与原 Run 输入，独立 Run 关联范围仅来自该批已有共享对象边。蓝色标识只标原输入告警，时序仅按告警发生时间排列。
- 独立执行三项窄验证：原图随成员过滤、未评分 Case 筛选、新 Run 图页签及独立 Run 展示，3/3 通过；Office 组 7 节点/8 边与输入标识、路径跳过提示、非 Run 结果说明均符合已有测试。渲染前后 store 及 Run.graphs 保持不变。
- `node --check` 检查 app.js 与 investigation-workspace.js 通过；本次指定代码/样式差异 `git diff --check` 通过。没有为此次复核重复来源全量重建或业务测试。主代理报告全套已增至32项，审阅者本次只独立执行上述3项窄验证，不将其写成自己重跑32项。

## 验收边界

此次审阅证明本地历史资料投影与展示适配的上述有限范围，不证明源调查质量、实时取数、后端 Case 创建、调查启动或响应执行。本轮浏览器实测、最终文档及归档状态尚待主代理收尾；历史合成输入与真实运行结果的区别保持。

## 主代理浏览器与最终回执

主代理完成V2浏览器验证：Office Case两次Run切换保留页签，阶段跳过/Deep策略/查询失败实际可见；用户反馈后当前链图页显示7节点8边及原告警时序、本次输入标识和非Run分析说明。最终页面控制台error为空。截图`.local/verification/frontend-v2-recorded-20261028/recorded-graph-full.png`，详细[验证回执](../../../../docs/design/frontend-v2-verification.md)。主代理最终npm语法及32项测试通过，独审不代签浏览器。没有后端/生产/模型/重放/部署或Git提交push。

## 归档后核验

2026-10-28已归档并同步1条主规格。`openspec validate --all --strict --no-interactive`为8/8，`--archived`为29/29；指定前端/文档差异格式检查通过。原审阅“待主代理收尾”反映独审发生时的边界，浏览器和归档实际结果以上述补录为准。
