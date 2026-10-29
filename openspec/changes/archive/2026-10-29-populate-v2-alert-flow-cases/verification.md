# Case已有材料填充验证

2026-10-29（Asia/Shanghai）。用户明确无自动建Case但有相关材料则补齐。只用本机保存的10月25日结果，无新远端查询/模型/重放/后端改动/部署/提交push。

## 输入与交付

源文件`.local/verification/alert-reset-replay-20261025/replay/observed-final.json` SHA-256仍为`e751eb2e57790dbc696c931d5179b4e780bcdb8bab089286c880ec497eae1ec9`。导出器核同租户、源Alert无Case、Run锚点、77工件字节/hash/event关系，并要求显式带时区organized-at。

新增3个local-socai2集合，源Case均null、源Alert/Run归属不改，6Run仍各1条输入。组织时间2026-10-29 07:51:56（上海）；原采集时间10月25日11:59:33。

- FIN：2成员/2Run/28过程/12工具/28工件/2报告，2partial。
- APP：2成员/2Run/44过程/28工具/28工件/2报告，2partial。
- DATA：2成员/2Run/20过程/9工具/21工件/1报告，1partial＋1分诊关闭。
- 共92过程/49工具/77工件/5报告；原16Case保留，总19Case/67Alert/15Run/15事件。

补案件级逐Run概览、当前成员资料/对象关系、按Run工件目录和原文入口、报告/工具链接、来源活动。本地源Run引用与当前成员分开，按ID+环境+租户核；移除成员不抹历史输入。空任务/评论/附件/执行不造值，Path未关联状态保持。本地状态New与调查partial分开。

## 验证

1. `npm run check`通过。
2. 主线程`npm test` 59/59（旧52＋本批7），其中alert-flow文件16项；含3Case×11区域、6Run×6视图、来源隔离、成员变更/重载、统计/活动、修改/重置、日期筛选及原291告警HTML比较。
3. 浏览器4174列表筛选local-socai2显示3项；FIN首页2Run/2partial/28工件/12工具；证据页按Run列28工件，llm_response可展开ID/hash/event与业务回复。工具入口保持在同Case与指定Run，实际失败摘要仍显示。
4. DATA首页显示2Run、1次后续调查/1次仅分诊、21工件/9工具；没有补联合结论。最终回到FIN概览，截图`.local/verification/v2-case-flow-20261029/case-overview.png`。
5. 独审重算投影与manifest一致；核63保护文件hash保持，包括V1、原告警模块和另一统一图JS/CSS。
6. 修正日期预置固定10月24日的问题，改截至已保存案件最新创建日；7天含3新集合，自定义25日排除3新集合，测试已过。

## 开发中失败保留

首次新增视图脚本因导出函数排列不匹配而断言退出、未写文件；修正后成功。一次测试编辑命令工作目录不匹配，未改测试；后续实际测试发现替换误落事件队列导致flowRuns未定义，以及旧总Case数断言16需更新19。已限定位Case队列、保持事件原逻辑并补测试；最终59/59通过。无原件丢失或后端副作用。

## 结束边界

文档第19节、V2README/回执、工具README、docs索引及PROGRESS同步。独审见audit.md。此处未覆盖实时接入、后台Case创建、真实联合调查、内容质量或另一统一图change验收。
