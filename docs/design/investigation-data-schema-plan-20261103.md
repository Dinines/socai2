# 告警、事件与调查：页面驱动的新数据模型

更新：2026-11-03。用户允许设计并新建自己的库表，要求建表之前先做一轮字段、类型、枚举和约束审计。本文为审计后的唯一模型总览；流程以[最新主设计](../architecture/investigation-planning-design.md)为准，逐项结论见[第一轮审计](frontend-data-model-audit-20261103.md)，完整定义见[字段字典](socai2-field-dictionary-20261103.md)。**迁移、ORM及枚举/schema已生成；已在21现有PostgreSQL的独立验证库实际建成29表，业务服务尚未切换。** 见[本轮建表与验证交接](socai2-schema-implementation-20261103.md)。

## 1. 物理边界

采用现有PostgreSQL数据库内独立的**socai2 schema**：socai2.alerts、socai2.incidents、socai2.cases等。新模块持有自己的业务事实、关系和历史，明确与开源版本实现的public表区分。ORM和原生SQL显式限定schema，不以全局search_path隐式替换旧表。

现有租户/用户、资产/连接器、ClickHouse、审批执行服务继续复用；不新建数据库服务、记忆系统或迁移框架。跨告警/事件/Case的成员和管理事务仍在同库完成。schema仅是命名边界，不替代租户约束和权限。

Fusion输入之前的问题排除；新模型负责收到以后保留、关联、读取及如实表达未知。旧报告/原件保持历史可读；不以新表自动补出旧流程未生成的数据。

## 2. 按页面需要组织29张表

原26表草案经第一轮审计增加3张案件判断表，并扩展执行/材料归属。各表列、类型、空值、默认值、枚举、唯一约束及JSON内部字段均在字段字典中展开。

| 组 | 表 | 独立保存的事实 |
| --- | --- | --- |
| 告警5表 | alerts、alert_materials、alert_source_refs、alert_objects、alert_assessments | 当前管理与来源身份；不可变材料版；原始事件引用；有类型的对象及库存匹配；同次分诊/人工反馈 |
| 事件3表 | incidents、incident_alerts、incident_diagnoses | 自身标题/状态/负责人/解决信息；成员和归并依据；有输入依据的诊断尝试/结果 |
| Case当前范围3表 | cases、case_alerts、case_incidents | 案件资料/业务状态/范围版本；当前告警成员；显式关联事件 |
| 案件判断3表 | case_assessments、case_assessment_sources、case_assessment_members | 每次明确采用的判断版；具体结果/任务版本/材料依据；明确覆盖成员 |
| 执行与结果6表 | runs、run_members、run_steps、artifacts、results、result_members | 执行身份/阶段/实际交换；冻结输入；正式结果及实际分析/结论覆盖 |
| 人工与AI4表 | tasks、task_revisions、conversations、messages | 人工事项当前版本和不可变反馈；同案对话及真实答复，保存进入results |
| 协作5表 | graph_explorations、activities、activity_targets、comments、response_links | 探索基底/画布；真实操作和每个目标；普通评论；建议与真实审批/执行关系 |

不为每个页面、每个Agent或每个统计卡新建表。成员数、战术计数、严重程度汇总、范围差集和用量从基础事实派生。JSON用于明确版本的结构化产物；不是万能extra字段。

## 3. 五条业务流程的归属

| 流程 | 执行/材料归属 | 正式结果与页面 |
| --- | --- | --- |
| 告警基本查询/诊断 | runs.kind=alert_basic，alert_id；步骤/原件同告警 | alert_assessments、alert_explanation工件；与完整Case调查分开 |
| 事件汇聚/诊断 | runs.kind=incident_diagnosis，incident_id | incident_diagnoses；保成功正文和真实失败尝试，不把两次拼成成功 |
| Case完整基础调查 | runs.kind=baseline，case_id；C1–C6全案执行 | results.kind=baseline及逐成员分析；pending也是真实Run行 |
| Case AI按问题分析 | runs.kind=ai_question，case_id；messages关联真实执行和输入 | 明确保存才results.kind=ai_saved；保存不重跑或自动采用 |
| 人工事实确认 | tasks/task_revisions，无伪造Run | 反馈人/完成时间/范围/原版本；后续C/Q明确引用 |

runs与artifacts均有alert_id/incident_id/case_id三选一；run.kind决定合法父对象。材料可以没有Run，例如普通附件；有Run时父对象必须一致。已有无Case过程不强造Case，旧执行用带命名空间的兼容引用。

## 4. 调查的四种范围不能合并

| 范围 | 真值 | 变更规则 |
| --- | --- | --- |
| Case当前正式成员 | case_alerts | 成员事务修改，实际集合变化才递增scope_revision |
| 某Run约定及读取的输入 | run_members + input_artifact | pending合并；领取时冻结身份/材料，随后只允许实际进度更新 |
| 某结果实际分析及结论覆盖 | result_members | 交付时固定；未分析/分析未决/已分析分别表达 |
| 案件当前采用判断的覆盖 | case_assessment_members及sources | 明确采用形成新版本；旧版本不因新成员或任务编辑扩大 |

当前Case可以含A1/A2/A3，而R1只分析A1/A2；R1的一项结论又可能仅适用A1。当前判断可采用多个结果与人工材料，但要保存确切版本及覆盖，不用“最新Run”代替。

## 5. pending与启动采用简单事务

**成员事务：** 锁Case（移动两案按ID排序）→完整核所选对象/权限→写当前关系→有告警集合变化才递增scope_revision→更新或新建唯一pending baseline和run_members→写实际活动目标→提交。仅新增事件关联但未改变告警集合，不伪造范围变化。

**启动事务：** 锁Case→锁指定pending Run→校验expected scope/version及活跃槽→冻结本地材料引用/输入工件→写running、started_at和执行版本→提交→调用C1–C6。模型/Tool不占数据库锁事务。单pending和单活跃baseline各有部分唯一索引；输入冻结还需受控写入/触发器，唯一索引不能代替。

R1已领取而第一步未执行时，新增A3仍会建立R2 pending。R1完成不能清掉R2；R2由用户手动启动。running和unknown占基础槽，结束后的人工待核通过任务/未决表达；不增加定时领取、自动接续或自动重试。AI模型/工具问答可并行，不与基础Run共用槽。

## 6. 当前值、原件和历史的责任

- alerts保当前业务值；alert_materials保已收到原文/OCSF、检测标签/评分、完整性；alert_assessments保同次判定/理由/分数，人工反馈不改旧分诊。
- incident独立管理值与成员汇总分开。事件first activity=min成员真实event_time；updated取事件自身/成员业务变化，关系移入/移出也更新自身业务时间；GET和Run进度不污染。
- Case当前判断不存大JSON作为唯一真值：cases.current_assessment_id指已采用版本，来源有明确FK，覆盖逐成员留存。有效基础结果自动采用；AI结果明确采用。自动采用须核范围版本及本轮期间的新判断，旧Run不覆盖较新判断。
- tasks仅保当前revision引用，完整可编辑内容在task_revisions。完成必须反馈/范围/实际完成人时间；修改后旧调查依然引用旧版本。
- 模型实际请求/响应、Tool参数/返回、图和报告存不可变artifacts。成功空查询、失败、未查、截断分别表达；业务分析不能把空查询当安全反证。
- AI保存可改标题/结论；改正文标人工编辑并重新校验，原message和原输入不变。保存幂等，正式结果不等于Case当前采用。
- 当前探索保存graph_explorations，绑定明确起点；新调查不偷偷替换画布，探索加入告警必须走成员事务。
- 响应用稳定proposal_id连接实际approval/action；缺审批要求标unknown，批准不显示已执行。活动每个实际目标逐行保存。

## 7. 已确认页面规则的数据支持

原厂未知留空；接入来源ID与厂商ID分列。规则/ATT&CK/评分有则保留、标来源，检测标签不当事实。历史fp处理状态映射completed且保留误报；人工误报/正常授权反馈与关闭同事务，手动关闭评论选填。

事件改派覆盖所有成员负责人；事件解决关闭所有成员且保留各自判定。实际影响目标持久化，原保存表单可据此提示，无需增加确认弹窗。事件解决说明按既有确认必填。各ATT&CK阶段分别按成员去重计1，和可超过告警总数。

总体统计不随下方筛选变化；未选择导出当前筛选/排序前200条，有选择导出所选。这些是查询合同，不为其新增计数/导出事实表。最新PRD未定义事件独立classification，原型兼容属性不直接照搬。

## 8. 建表与现有实现衔接

1. D01–D03已确认，socai2 schema DDL、ORM、API枚举与JSON schema已生成，物理约束已在独立PG验证。字段类型见[逐列字典](socai2-field-dictionary-20261103.md)，不是留给实现时临时决定。
2. 使用现有SQL迁移执行器，但显式schema；新表同租户/同案/同轮FK、RLS、权限、唯一索引和冻结检查一起验证。旧用户表只有id唯一键，引用用户仍需服务端同租户检查；不宣称普通FK自动完成授权。
3. Fusion默认仍写旧alerts；已新增可选socai2写入器，同事务落告警/材料/来源/对象/事件成员及首次结果，接入编号与原厂语义保持。材料版本与人工管理不被重投覆盖，真实Fusion材料到Case/C1已验证，见[53字段明细](../investigation/socai2-fusion-ingestion-20261104.md)。A/I实际诊断结果写入、旧消费者/处置回写、新告警/事件读取及生产切换仍待。
4. 新socai2生命周期、单活跃/下一pending、冻结及发布事务已在独立PG验证；Case创建/成员更新/手动HTTP与只读快照已接默认关闭的新路径。迁移122绑定public旧表，不作为新表迁移；[当前接口及36字段](../investigation/socai2-case-api-20261104.md)记录实际出口。
5. 同Run C1–C6、原始字段/两个湖Tool、来源图/结果/比较及读取已实现；外部来源、真实模型/湖质量仍待验收。当前合成验证不证明完整能力，新表不自动解决r13问题。旧报告保持，修复批次不自动恢复。
6. 人工/AI/探索接新数据合同；审批/资产/身份服务沿用实际来源关联。旧数据显式兼容读取，不长期双写两套真值，不失败后隐式切回旧表。

## 9. 贯穿案例的落表

设计示例，非真实执行：

1. A1/A2入alerts，材料v1、来源P01/N01、对象边分别入materials/refs/objects。各自alert_basic Run产生分诊及Explain。I1持久化incidents及实际成员/归并依据，事件诊断自己的Run产生诊断记录。
2. 创建C100并纳入A1/A2/I1，同事务写Case当前关系、scope_revision=1、R1 pending及成员、活动。
3. 手动领取R1，冻结材料/历史判断，写running；C1–C6步骤和实际交换留存。R1运行中新增A3，当前scope变2，建立R2 pending，R1仍只含A1/A2。
4. R1交付结果与两成员的实际分析/结论覆盖；失败也保存真实部分产物及收尾。若R1是有效且范围仍适用的基础结果则自动生成case_assessments/sources/members并改current指针；范围已变化或已有更新采用时只留历史。AI结果仍需用户明确采用。
5. H1完成产生task_revision v1；Q1提问冻结这版事实和所选结果，经ai_question Run产生答复。明确保存才产生ai_saved结果，保存不新增调用。
6. R2手动启动对A1/A2/A3完整执行，比较基线明确R1结果；交付变化与Case影响，不覆盖R1。H1后来编辑成v2，R2/Q1仍指当时v1。
7. 新探索引用明确底图，保存只改graph_explorations；批量管理活动保存实际全部目标；只有真实回执才能展示已执行响应。

## 10. 已确认决定与剩余边界

- D01已确认：保留成员最高等级的自动汇总，允许人工事件覆盖，保存理由/人/时间，不修改成员。
- D02已确认：有效基础调查结果自动更新当前判断；AI结果仍需明确采用，保存本身不采用。
- D03已确认：只限制基础调查单活跃；AI问答可并行，无共用槽唯一索引。
- D04空/已解决Case特殊策略：建议空案禁止启动、已解决案不静默重开；相关动作尚未开放，不以建议冒充确认。

本轮原26表草案见[审计前副本](../operations/investigation-data-schema-plan-20261103.pre-audit1.txt)；此前67组“扩原表”建议见[更早记录](../operations/investigation-data-schema-plan-20261103.pre-new-schema.txt)。旧事实/回执保留，当前物理设计以本文及字段字典为准。
