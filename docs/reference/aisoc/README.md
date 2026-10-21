# AiSOC模块分析参考

本目录保留固定上游源码的模块、状态、测试入口、历史证据和风险分析。分析覆盖面大于本项目职责，不能把所有能力描述或历史改造建议当成本轮任务。

**本项目目标：告警及后续数据处理服务端。** 已有告警输入，交付API、消息及持久化结果；前端、采集、原始事件检测和独立展示推送服务不在本轮职责。

- [负责范围](../../operations/alert-processing-scope.md)：M00—M21职责及服务组件。
- [当前迁移路线](../../operations/service-roadmap.md)：六阶段目标和退出标准。
- [当前依赖批次](../../operations/dependency-migration-plan.md)：第一阶段实施顺序和验收。
- [实际进度](../../../PROGRESS.md)：已完成、未完成和下一单项。

## 分析导航

| 文档 | 用途 |
| --- | --- |
| [13 规划入口](13-port-test-develop-roadmap.md) | 当前服务端路线及早期全量规划归档 |
| [01 系统与模块地图](01-system-map.md) | 上游模块、输入输出和当前职责导航 |
| [02 Fusion](02-fusion.md) | 告警归并、关联、持久化与风险 |
| [03 告警与Case](03-alert-case.md) | 队列、Case及服务端交付数据 |
| [04 分诊与调查](04-triage-investigation.md) | 调查入口、编排与实际取证 |
| [05 工具/知识/模型](05-tools-knowledge-model.md) | 查询、检索、角色路由与成本 |
| [06 剧本与动作](06-playbook-actions.md) | 服务端剧本、审批、执行与回读 |
| [07 数据/证据/风险](07-data-tests-porting.md) | 原关系、测试线索与已知限制 |
| [08 源码索引](08-source-index.md) | 固定版本的符号、接口和测试位置 |
| [09 UEBA分析](09-ueba.md) | 上游生产逻辑参考；本轮只消费已有信号 |
| [10 上下文/增强/风险](10-context-enrichment-risk.md) | 已有材料查询与风险解释 |
| [11 检测/补查/反馈](11-detection-hunting-feedback.md) | 检测为参考；告警相关补查与反馈按范围取用 |
| [12 场景](12-end-to-end-scenarios.md) | 完整上游场景参考；本轮验告警后续数据链 |

## 使用边界

来源revision：`34ca18c57dd4175539e5c6dd3d04a72dc057306b`。源码链接固定到上游revision；历史工程链接只作对照。本目录是既有分析的交接链接版。 [源码快照](source-snapshot.json)只证明引用文件字节，不证明功能运行正确。源码/测试存在、Mock通过、真实基础设施、真实模型及真实厂商验收分别记录。

20的部署/登录/模型/embedding/golden记录仅证明原证据范围，见[已有证据](../../operations/verified-evidence.md)。它们不证明21已部署，也不要求本服务建设控制台。

本项目不继承旧SOCAI对象合同、Outbox设计或Basic/OpenSpec任务。范围内先保留原服务关系和直接构建依赖，必要改动按实测问题限定。早期全量路线已归档，当前退出标准只在服务端路线维护。
