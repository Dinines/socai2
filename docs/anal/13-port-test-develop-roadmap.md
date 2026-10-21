# 13 服务端迁移规划入口

当前目标是**告警及后续数据处理服务端**：已有告警输入，交付API、消息和持久化结果。前端、采集及原始事件检测不在本轮职责。

- [当前模块范围](../operations/alert-processing-scope.md)：M00—M21负责、消费和范围外边界。
- [当前六阶段路线](../operations/service-roadmap.md)：阶段目标与退出标准的维护入口。
- [第一阶段批次](../operations/dependency-migration-plan.md)：1A—1G输入、验收与下一单项。
- [早期全量规划归档](../handoff/history/2026-10-20-anal-full-stack-roadmap.md)：保留此前完整上游/控制台规划，不再作为当前实施要求。

本文只保留入口，避免与当前路线重复维护。固定版本、先迁依赖、逐批测试、冻结基线后二开的方式继续沿用。
