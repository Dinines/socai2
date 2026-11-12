# 调查执行账本

当前部署、读取权限和运行参数见[交接指南](../../FRONTEND_BACKEND_HANDOFF.md)。正式存储为 21 `aisoc.socai2`，湖查询使用 `aisoc.raw_events`；配置来自生产 profile。下表描述程序职责，实际发生过的动作以 Run、Step 和工件为准。

| 环节 | 输入与职责 | 保存与读取 |
| --- | --- | --- |
| 入站／Fusion | 保存告警原件、归并依据及来源，投影告警／事件关系；归并不作为攻击因果证明 | `alerts/alert_materials/alert_source_refs/alert_objects/incidents/incident_alerts`；来源快照在 `artifacts` |
| A | 程序冻结单告警、当前材料、基本查询和人工事实；模型给判定、置信度、理由、引用与待核建议 | `runs.kind=alert_basic`、`run_steps`、`artifacts`；有效结果保存到 `alert_assessments` 并按新鲜度更新对应指针 |
| I | 程序冻结事件成员、所选 A 结果及其同 Run 实际查询回执；模型判断整体解释、成员、发现和问题 | `incident_diagnoses`、Run／步骤／工件；交付、待复核、采用分别记录 |
| Case 准备／C1 | 显式准备并启动；同 Case 单活跃，冻结成员、材料、A/I/H 与来源映射 | `runs/run_members`、初始输入工件，成员变化和操作回执保留 |
| C2／材料组织 | 按需求读取已配置来源；知识从冻结材料按技术解释/取证指导及配置的历史案例参考查询本地嵌入索引，回读原文/hash并保留非观察身份 | 查询状态及材料工件；目的/查询/片段在实际参数与 tool_response，检索回执在 C2 source_snapshot；未查、失败、查空分别记录 |
| C3 | 全案初步判断、发现、六类问题、领域适用性与补查建议；短号由程序恢复 | 请求、原答、有效部分和拒收原因均保存；有效局部可继续交接 |
| C4／Deep | 程序按既有绑定执行明确查询；Deep 围绕指定问题选择补查、回答或交人工确认 | 每次模型／工具单独 Step；保留真实查询回执、支持／反证和未决状态 |
| C5 | 从已保存且可引用的发现生成关系图 | 图工件及来源引用；连线不自动证明因果 |
| C6 | 冻结业务材料、有效 C3、Deep、原计划及实际执行进入最终判断；程序补身份和比较元数据 | `results/result_members`、报告和证据工件；有效基础结果按新鲜度和采用规则更新当前判断；无有效模型结果时保留系统收尾 |
| H | 保存明确范围的反馈及陈述来源；助手代拟验收材料核查不等于业务授权或新增观察。修改追加不可变版本 | `tasks/task_revisions` 与活动；后续调查需再次明确准备／启动，不自动改当前判断 |
| Q | 预留问答、保存和采用合同 | 业务暂未开放，不产生模型、工具或调查结果 |

GET 使用授权租户的只读事务，不隐式启动处理或修改判断。Case、Run、Result、当前判断分别有稳定身份；历史材料不切换成当前材料。输入、输出、引用与数据库恢复的详细合同见[模型输入输出](model-input-output-current-20261109.md)及[数据交接](socai2-page-data-handoff-20261106.md)。

历史知识功能已完成 21 发布读回，并在本地完成[一条实际流程](../../openspec/changes/archive/2026-11-12-use-historical-alert-knowledge/validation.md)：历史演练来源经 HTTP 入库/索引/GET，C2 9 查询/10 命中，其中历史 2 命中/1 卡，5 次请求均可见原分诊与人工正文，结构化引用数组未引用历史，部分正文有提及；保存/GET 六字段一致。C3 首次成员归属引用错误纠正后接受，C6 建议缺来源拒收，partial/rejected、conclusion=null，模型质量保持 NOT_PASSED。[知识交接](case-knowledge-handoff.md) · [历史卡片字段/消费](historical-alert-knowledge-handoff.md)

[Case/H HTTP 已交付](../../openspec/changes/archive/2026-11-11-enable-case-human-http-flow/validation.md)，第 2 个任务修订进入后轮冻结与实际请求。观察原值装配、coverage 和 C3 两项上限保持；M01-A/M01-B、F01 质量、知识召回/方法使用效果、产品页面和自动消费者仍开放。当前发布及远端回执以根交接和 PROGRESS 为准。
