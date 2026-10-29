# 只读功能审计回执

日期：2026-10-29。结论与逐项依据见 [功能审计](../../../../docs/design/frontend-functional-audit-20261029.md)。

## 实际执行

- 浏览器：当前FIN告警列表/侧栏/详情→事件attack→Case overview→指定Run tools；切换另一Run仍为tools，随后graphs/report；历史联合Case图中A3选择、详情链接及Chain/Path来源展开。Unknown管理状态弹窗打开后取消；Case data=aisoc重置/刷新复现7→19→7；告警日期弹窗10月24日固定值后取消；创建Case只出现占位toast。最后停回全部Case列表。
- `npm run check`：通过。
- `npm test`：65通过，0失败。未新增正式前端测试或修改前端。
- `verification.cjs`：独立Node VM执行实际脚本/事件处理器，使用无网络、无存储的副本；结果见results.json。渲染858对象/视图组合，1095本地链接，0渲染异常/缺目标/范围外Run链接；多项操作反例仍失败，不能据路由覆盖宣称操作通过。
- CSV：仅内存生成AiSOC筛选结果，7数据行+表头，1358bytes。
- SHA256：审计前后V2全部36文件无变化、无新增文件。完整本机基线与对照在 `.local/verification/v2-functional-audit-20261029/`。
- OpenSpec：本change strict通过，skip_specs仅文档/审计工具。

## 发现而未修

9项问题（4P1、4P2、1P3），含既有未实现反馈同步。现有占位、后端未接、无Case路径、摘要截断和源报告状态分别列出，不当作新数据丢失。

## 限定

未在用户浏览器保存业务编辑，未重置localStorage；没有远端业务查询/写入、模型调用、重放、后端源码变更、部署、Git提交或推送。其他未提交工作及统一图change保持。本次审计不修复已发现问题，也不关闭其他开发change。

独立复核与最终归档校验见audit.md。
