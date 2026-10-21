# 12 从采集完成到反馈改进：完整业务流程与场景

> 用途：固定上游源码与历史证据分析（2026-10-20对齐）。下文保留完整上游场景。当前只验已有告警进入后的数据链；普通事件生成告警和界面步骤不作为本轮退出条件。 当前职责见[范围](../../operations/alert-processing-scope.md)，阶段退出见[路线](../../operations/service-roadmap.md)，执行批次见[依赖计划](../../operations/dependency-migration-plan.md)。

返回[总入口](README.md)或[模块总览](01-system-map.md)。模块编号以 01 为准，本章按实际数据旅程对应具体文档。

## 1. 三条流共同构成后续处理

**事件流：** 规范化事件 → 会话/历史材料、单事件和窗口检测、首见/行为基线、UEBA → findings/异常信号 → Fusion。

**告警流：** Fusion → 风险/优先级、工作队列 → 自动分诊或人工启动 → 调查问题/取证/领域分析 → 验证与报告 → Case 处置。

**改进流：** 响应效果与人工结论 → Case closure/反馈 → 经验和知识、规则调优提案、质量回测 → 经批准后影响下一轮处理。

资产/身份/漏洞与外部情报持续更新，为三条流提供上下文；它们不是每次都按固定顺序重新扫描。Lake 和账本分别记录事件历史与执行事实，不能互相替代。

## 2. 全程输入、中间产品与输出

| 阶段 | 输入 | 中间业务产物 | 输出/下一步 | 详细模块 |
| --- | --- | --- | --- | --- |
| 事件可分析 | 采集完成的规范化事件、tenant、来源与时间 | 校验、实体、来源定位 | 可查询事件；错误有拒绝原因 | [M00 边界](01-system-map.md#m00)、[M21 历史](10-context-enrichment-risk.md#m21) |
| 检测与行为分析 | 当前/窗口事件、rule、已有基线 | rule match、计数/序列、稀有度、UEBA 特征和分布 | finding/typed signal/anomaly；未命中事件仍可留作证据 | [M01 检测](11-detection-hunting-feedback.md#m01)、[M13 UEBA](09-ueba.md#m13) |
| 融合与风险 | finding、历史摘要、情报/行为信号 | dedup、Incident 关联、score/rationale、RBA | Alert、融合消息、实体风险 | [M02 Fusion](02-fusion.md#m02)、[M17 风险](10-context-enrichment-risk.md#m17) |
| 背景解释 | 实体、CMDB/身份/漏洞、业务规则、Feed | 资产/身份匹配、TI、规则版本与 before/after | 排序与调查上下文、明确 partial | [M14](10-context-enrichment-risk.md#m14)、[M15](10-context-enrichment-risk.md#m15)、[M18](10-context-enrichment-risk.md#m18)、[M07](05-tools-knowledge-model.md#m07) |
| 队列与初判 | Alert、owner、SLA、tenant policy | 队列项目、verdict、confidence、tier、依据 | 自动关闭资格/人工待办/升级任务 | [M03 运营](03-alert-case.md#m03)、[M04 分诊](04-triage-investigation.md#m04) |
| 调查准备 | 明确目标、实际材料、问题、授权/预算 | ContextBundle、已有证据、能力可用清单 | 有界调查任务与工具范围 | [M05 调查](04-triage-investigation.md#m05)、[M06 工具](05-tools-knowledge-model.md#m06) |
| 补证与分析 | 查询参数、领域问题、知识候选 | 实际工具结果、引用、模型输入/输出、支持/反证和未知 | 风险判断、必要补查、响应提案 | [M05](04-triage-investigation.md#m05)、[M20 狩猎](11-detection-hunting-feedback.md#m20)、[M08 模型](05-tools-knowledge-model.md#m08) |
| 校验与交付 | 结构结果及引用 | schema/grounding、账本和报告 | 可回放结果、时间线、证据包 | [M12 交付](03-alert-case.md#m12)、[07 测试卡](07-data-tests-porting.md) |
| 响应 | 提案、目标/参数、预案、权限 | policy/approval、暂停、执行请求与回执 | 拒绝/待批/实际执行/效果验证 | [M09 剧本](06-playbook-actions.md#m09)、[M10 响应](06-playbook-actions.md#m10) |
| Case 结案 | 人工判断、处置效果、残余风险 | 结案状态、责任人、证据、未解事项 | 结案/重开/继续调查 | [M11 Case](03-alert-case.md#m11) |
| 反馈改进 | disposition、理由、closure、固定样本 | 记忆、调优 proposal、eval 结果 | 经审查的知识/规则更新和下一轮效果 | [M19 反馈](11-detection-hunting-feedback.md#m19)、[M16 规则](11-detection-hunting-feedback.md#m16) |

“支持/反证、必要补查”是移植时必须按 stingAISOC 设计落实的业务合同；上游结构中有 findings/根因等字段，并不证明全部上述分析维度已完整实现。

## 3. 四个代表场景覆盖不同分支

### A. 厂商直接告警：Office 启动 PowerShell

厂商已给 finding → M02 保真入库/来源关系 → M17/M14/M15 补充优先级与背景 → M04 分诊 → M05 查询进程/命令行/关联连接 → 依据校验和报告 → 必要审批后响应 → Case 结案。无需先由平台统计到 UEBA 阈值才处理。

必须检查来源事件、原描述和实际工具结果，不因命中 T1059 就直接称已确认攻击；本环境 golden 只验证到告警读取，后续步骤尚未验收。

### B. 无厂商告警：失败登录后成功与异地/罕见行为

规范化普通事件 → M01 窗口/序列判断 → CORE 基线/first-seen 提供稀有度，独立 UEBA 也可并行形成异常 → 条件命中提升 Alert → M02 融合 → M04/M05 查询身份、历史登录、授权变更 → 判断是否账号入侵或合法活动。

这是功能示例，不表示某一条同名上游规则已具备上述全部字段。验收必须选定实际规则和 payload，证明序列来源、时间范围、baseline 样本及实体一致。

### C. 重复低危信号累积成高风险实体

多个真实不同的低/中危告警 → M17 RBA 对同实体累积并衰减 → 实体风险达到阈值 → 队列/解释突出该实体 → 显式调查其贡献告警和时间线。重复投递不能重复加分，promoted 不能冒充 Case 已建。

本场景还检查参考 fingerprint 折叠对贡献列表的影响。移植使用目标已有 PG 风险与 membership，不直接复制参考 Redis 实体队列。

### D. 授权扫描导致告警与反馈调优

检测确实命中 → 业务上下文与分析员确认授权扫描 → disposition 为 benign_true_positive → 当前 Case/告警按策略处理 → M19 保留理由并写可信经验 → 不作为 FP 给规则降级。若是规则真正误检，则形成 exception 等提案，经 M16 回测/批准/运行生效验证。

这个例子同时验证统计分母、人工反馈、记忆与规则控制面，不应为了减少告警数把所有合法行为都当无效检测。

## 4. 什么才算某模块接通

| 观察 | 还缺的证据 |
| --- | --- |
| 容器/health 200 | 真实入口有输入、正确处理、持久结果、下游消费 |
| 有规则/Agent/工具文件 | 调用方实际绑定，字段/后端可用，结果被实际使用 |
| 数据库存在一行 | 来源可信、tenant/目标/版本正确，状态与输出对应 |
| 向量检索命中 | 正确模型空间/ACL、相关性、引用和模型实际消费 |
| 模型给了报告 | 实际取证、依据校验、未知、持久交付和人工可审阅 |
| 审批通过/接口 200 | 动作实际状态与效果 probe，未知不自动重发 |
| Case 已 closed | 结案依据、实际处置、残余问题和反馈来源 |

移植阶段按 [13](13-port-test-develop-roadmap.md)推进；每个接通/测试任务选本章的一条业务旅程或直接阻塞，引用对应 M 编号和 [07 的三段测试卡](07-data-tests-porting.md)。先验证原版行为，冻结可用基线后再决定产品流程和架构改造，不自动恢复旧建设任务。
