# F2：管理字段编辑不使Case使用的分诊失效

2026-11-15。本批使用真实隔离PG`v12_upgrade_dev`及Redis、实际A/Case执行器和管理用例；模型与查询为明确替身，未调用真实模型，未部署。属于直接模块验证，不是Kafka整链验收。

- [修复前](before-01/result.json)：真实管理用例修改owner/tags后，C1错误地把同材料已完成A标为不可用；[前](before-01/before-context.json)/[后](before-01/after-context.json)保留。该批只完成1次A替身，Case已受理未执行，未重派或改写失败。
- 修复内部C1及配对查询新鲜度检查：使用同租户/告警/已选分诊、completed A Run及同原材料ID判断下游可用性。负责人、标签及之后的人工判断不再使A被剔除；人工反馈独立比较。不增加活动时间字段，不改A公开DTO或其原输入快照。
- [正常新批次](pg-01/result.json)：1轮A、Case首轮、管理编辑后check无变化跳过、有效人工反馈后手动check完成完整Case。5次模型替身（1 A+4 Case），0真实模型。owner/tags修改保留A正文及查询回执，跳过任务无attempt/Run、模型次数不增加。反馈后C1同时包含原A和新人工判定。
- A模型回复前在独立PG连接读取告警原材料及running task；告警已持久保存，尚未有分诊关联，符合先保存再异步分析。
- [管理回执](pg-01/management.json)、[修改前C1](pg-01/before-context.json)、[修改后C1](pg-01/after-context.json)、[反馈C1](pg-01/feedback-context.json)、[模型IO](pg-01/calls.json)、[完整快照](pg-01/snapshot.json)。HTTP同源读回待模块回执。

上述人工反馈使用明确的手动check验证输入保留；单告警晚到A/反馈不绕过事件自动触发Case的新规则仍在F4实施，不把本批当作自动链已通过。
