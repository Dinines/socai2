# 新库表建表前第一轮审计

2026-11-04增量核对：Case原表缺固定来源空间，清空成员后无法保留边界。已用124新增source_namespace text/null及不可改绑定触发器；明确来源才回填，旧混合/无来源保NULL并拒范围修改。当前29表459列，原首轮458列审计及123原件保持。[字段/事务/例子与验证](../investigation/socai2-case-relations-20261104.md)说明真实命名空间与未提供来源环境的区别，不把fusion.v1当环境。下方是第一轮历史事实。

2026-11-03。**首轮审计完成，三项业务口径已确认，随后已生成迁移并在独立PG验证。** 原26表草案存在下述明确缺口，本轮在设计阶段一次修正为29表。已逐列定义458列（含每表id/tenant_id）、36组枚举、38种JSON结构；不以数量声称功能已实现。D01–D03已获得用户明确答复，D04是特殊生命周期建议，不作为已确认规则。

用户已允许新建独立库表，并要求建之前做一轮审计，尽量先定义好字段、类型、枚举。本轮不请求重复授权；先把可核对的合同做完整。审计当时尚未建表；确认后的迁移和独立验证库事实见[后续实现交接](socai2-schema-implementation-20261103.md)，原静态审计回执保持。

## 1. 依据和范围

- 最新页面需求：[产品说明](alert-incident-case-product-requirements.md)及本地c71afb5原型：告警/事件、Case资料/概览/故事、调查历史、AI、人工任务、探索、对象证据、响应、评论。未刷新远端，不能称远端此刻无更新。
- 当前服务端：39f4033检查点加case-baseline-history独立工作区已有修改。新表设计分支中的较早服务代码不作最新基线。
- [85项已有字段核对](../investigation/page-field-support-matrix-20261102.md)是48f54abd历史需求的现存数据证据，本轮用作遗漏回查；[36项调查结果字段核对](investigation-result-field-audit-20261103.md)对应新版调查展示。两者不是同一时点的上线验收。
- 五流程仍以[唯一主设计](../architecture/investigation-planning-design.md)为准。Fusion收到数据之前的问题不追查；已有输入被内部丢失/误用仍在范围。页面交互不改；r13报告问题不因新表消失。

## 2. 审计发现与设计修正

| 编号 | 草案中的缺口/冲突 | 本轮定下的处理 | 仍须实现或验证 |
| --- | --- | --- | --- |
| S01 | runs/artifacts必须有Case，告警基本查询、事件诊断及普通附件无合法归属 | runs.kind分alert_basic/incident_diagnosis/baseline/ai_question；alert/incident/case恰一父对象；人工任务无Run。artifacts同样支持明确父对象 | 四入口适配、父关系约束；不能把四流程都展示成基础调查 |
| S02 | 当前案件判断一段JSON，采用依据及覆盖无强关联 | 新增case_assessments、case_assessment_sources、case_assessment_members；cases只保当前引用 | D02已确认有效基础自动采用、AI明确采用；旧Case.summary不能自动回填为已采用 |
| S03 | 原件、分诊、当前反馈容易错配，且对象会跟随最新材料变化 | 材料不可变版本；对象绑定material；分诊/反馈同次记录；Run绑定当时版本 | 材料投影和模型真正消费仍需接线 |
| S04 | Explain只有“描述”概念，缺生成方式/时间/依据 | alert_explanation工件合同及alerts.latest_explanation_id；与description和分诊理由分开 | 生成入口保存原件，GET不写业务时间 |
| S05 | 处理、判定、执行、交付及结论有效性混作状态 | 各自枚举；completed/partial、failed/partial合法；失败系统交接不算有效结论 | DTO按语义映射，页面completed完整交付标签不反推执行状态 |
| S06 | 时间/评分/用量默认NOW/50/0可造成伪事实 | 发生时间NULL+来源；三种评分各有state/source；usage未知项NULL+调用未知数 | 输入历史不可恢复时保未知，不补造 |
| S07 | “类别”可能错误读category | 告警页面类别读检测战术；category保来源普通分类，技术另列 | 读取合同明确字段，不靠同名猜 |
| S08 | 事件仍可能只是告警metadata聚合，缺独立管理事实 | incidents+incident_alerts+diagnoses独立；标题/状态/负责人/解决说明持久化 | Fusion新写适配与批量事务，不只是改表名 |
| S09 | 事件最高等级与管理编辑含义冲突；旧classification仍在原型兼容数据 | D01已确认；保派生值，人工覆盖四列已纳入迁移。最新PRD未定义事件classification，不照搬旧兼容属性 | D01已落实物理约束；旧分类交页面团队明确去留，不造分类算法 |
| S10 | pending到running存在第一步之前修改范围的窗口 | 锁Case→Run，在启动事务内冻结输入并写running后再执行；单pending+单active唯一索引 | 真实PG两会话竞争、冻结触发器/受控写入验证；本轮未执行 |
| S11 | AI执行与baseline的槽位规则未定 | D03已确认：baseline单活跃，AI并行，无共用槽索引 | 不先假定后补索引 |
| S12 | run_members被误当结果覆盖；新成员可能被旧结论解释 | 四范围分开：case_alerts、run_members、result_members、assessment_members | 每成员分析/缺口及采用来源验证，AI局部答案不得扩整案 |
| S13 | 人工任务当前行更新会改历史引用；完成人容易混负责人 | tasks仅指当前task_revisions；每次有效保存追加版本，completed须反馈/范围/实际完成人时间 | 不重复存两份当前正文；旧完成缺反馈按历史限制 |
| S14 | AI“明确保存”可能再次调用、借最新材料或保留编辑前校验 | 保存引用原message/Run/input；重复返回原结果。用户改正文标human及edited_fields，重新核引用；原答复不改 | 同答复幂等，保存不新调用、不自动采用 |
| S15 | 批量活动只存无约束type/id或数量，易串对象和截断 | activities主对象三选一；targets七类明确FK恰一目标，每个实际目标一行 | before/after白名单，真实主体；表单提示由准确目标数据支撑 |
| S16 | 建议与审批/动作关系靠同名ID猜 | recommendations稳定proposal_id；response_links明确来源/命名空间/审批/动作/回执 | 批准≠已执行；actions.incident_id不当Fusion事件 |
| S17 | FK只验证ID，不保证同租户/同Case；可空父键可能跳过约束 | 内部复合唯一/FK+父对象CHECK；旧用户表仅有id键的限制明确，服务端验证同租户 | JSON引用仍须应用检查；数据库FK不能验证JSON中的来源 |
| S18 | 直接照抄旧RLS会允许缺tenant上下文读取 | 新表USING/WITH CHECK只接受tenant_id=public.current_tenant_id()，不复制NULL旁路；复用db/rls.py事务上下文 | Fusion及后台入口必须设置租户；实际角色/权限部署预检，不声称已验 |
| S19 | tasks↔versions、runs↔artifacts及当前指针会形成建表/插入循环 | 先建表再加FK；任务预生成UUID并用延迟FK；最新指针同事务写入；提交时必须完整 | DDL真实PG建空库/提交验证，不以SQL解析通过代替 |
| S20 | 大JSON字段只写“JSONB”，不能判断字段是否完整 | 38结构合同明确字段、类型、required/nullable、枚举；可变厂商payload是明确例外 | kind选择具体工件schema；结构合法不等于证据语义正确 |

新增3张表都是案件判断的持久事实和引用关系；执行扩展复用runs/steps/artifacts，不再增加四套执行表。无调度器、向量记忆库、专家投票表或额外图数据库。

## 3. 字段、类型和空值已定义到哪里

完整逐列见[字段字典](socai2-field-dictionary-20261103.md)；结构化源为[data contract](socai2-data-contract-20261103.json)，JSON定义见[schema](socai2-json-contracts-20261103.schema.json)。以下是跨表规则，不替代逐列明细。

| 项目 | 固定定义 |
| --- | --- |
| 内部身份 | UUID应用生成；外部厂商/湖/审批ID为TEXT，带命名空间；原型17420等不强转UUID，迁移留legacy_ref |
| 租户 | 所有29表tenant_id非空；服务端注入；同案/同轮引用带父身份校验 |
| 时间 | TIMESTAMPTZ；真实发生、接收、业务变化、执行、材料取得分别存；缺发生时间NULL |
| 评分 | 来源检测0..100、分诊0..1、已有优先级0..100分开；全部状态/来源配套，无默认50 |
| 标量 | 计数/版本BIGINT；金额明确币种与计价版，JSON decimal按Decimal处理；端口0..65535；PID保来源文本 |
| 枚举 | TEXT+命名CHECK，API共享字典；合法状态变更另有规则，不能枚举合法就允许任意跳转 |
| 空集合 | 已明确读取无项才[]；未记录/失败为NULL或专门状态；查询空行不是全案安全证据 |
| 不可变性 | 原材料、结果、任务版本、已结束步骤/诊断及活动追加；当前关系可变；已领取Run身份/材料不可变 |
| 展示派生 | 数量、ATT&CK多阶段计数、成员最高等级、首次活动、差集、耗时及用量从事实派生，不另建计数表 |
| 字段上限 | 存储TEXT不静默裁剪；模型输入限额和省略单独记录，不改变原件；附件保大小/hash/类型/名称 |

PostgreSQL的CHECK不能替代跨行/跨表一致性，应以唯一约束、外键及必要触发器/事务实现；可空复合FK还必须配父对象CHECK。[官方约束文档](https://www.postgresql.org/docs/current/ddl-constraints.html)。

## 4. 调查状态和并发审计

| 当前状态 | 允许动作/下一状态 | 数据规则 |
| --- | --- | --- |
| pending_update | 合并当前范围；明确启动→running；明确取消→cancelled | 仅baseline；最多一条；未领取不占活跃槽，无模型/Tool |
| running | completed/failed/cancelled，或执行结果待定→unknown | started_at在领取事务已写；输入/成员不变；取消只有确认停止才结束 |
| unknown | 经过执行器核实后确认终态 | 保持占槽，不靠超时自动放行另一个基础Run；不设计自动重跑 |
| completed/failed/cancelled | 历史只读；用户明确重试另建Run | 后续范围变化保留下一条pending；旧Run完成不能清新pending |

事务顺序固定Case→Run→成员/输入→活动；移动两案按ID排序锁Case。外部模型和Tool调用在事务提交之后。所有竞争入口使用相同锁顺序，条件更新检查expected revision/state，唯一索引兜底。单靠事务隔离或只在执行第一步写状态都不够。[PostgreSQL行锁说明](https://www.postgresql.org/docs/current/explicit-locking.html)。

若提交running后进程退出、未能确认是否发出外部请求，记录unknown并保留槽，需明确核实后终结；本轮不新增周期领取/恢复模块。基础Run全案执行，人工反馈无Run，AI问答范围明确。

当前判断更新也锁Case并校验row_version/当前成员范围；旧Run可以发布自己的历史结果，但不能覆盖较新的采用判断。其后新增成员仅使覆盖不足，不改旧结果。

## 5. 与页面字段逐项对应

### 5.1 告警、事件、操作数据条件与Tool：85项

下表是新设计映射，不是新实现通过率；“派生”“既有服务”“待确认”“输入限制”均明确保留。历史85项中的分类等字段须按最新PRD核去留，不自动扩新需求。

| 编号 | 核对字段 | 新设计保存/读取或明确限制 |
| --- | --- | --- |
| A01 | 告警名称 | alerts.title/id |
| A02 | 严重程度 | alerts.severity；critical/high→高、medium→中、low/info→低，仅显示派生 |
| A03 | 告警时间 | alerts.event_time/event_time_source；未知不拿ingested_at代替 |
| A04 | 资产标签 | alert_objects.asset_ref/match_basis→既有库存tags；不是alerts.tags |
| A05 | 处理状态 | alerts.handling_status + disposition；完成和误报分别保存 |
| A06 | 类别 | alert_materials.detection.tactics；页面类别不是alerts.category |
| A07 | 检测源 | alerts.original_vendor；未知NULL，connector_type不替代 |
| A08 | 资产／账户 | alert_objects(type,namespace,value,attributes)；匹配库存另有match_state |
| A09 | 分配给 | alerts.owner_id/assignment_state/owner_source_value |
| A10 | 侧栏描述 | alerts.description |
| A11 | 所属事件 | incident_alerts.incident_id |
| A12 | 已关联 Case | case_alerts.case_id；多案，不使用旧单case_id |
| A13 | 平台告警 ID | alerts.id |
| A14 | 源记录 ID | alerts.source_alert_id |
| A15 | 外部告警编号 | alerts.vendor_alert_id |
| A16 | 原始事件引用 | alert_source_refs + alert_materials.source_scope |
| A17 | 检测规则 ID、名称 | alert_materials.detection.rule_id/rule_name |
| A18 | ATT&CK 技术 | alert_materials.detection.techniques |
| A19 | Fusion 置信度分数 | alert_materials.detection.confidence_value/state/source |
| A20 | Fusion 置信度等级、依据 | alert_materials.detection.confidence_label/confidence_rationale |
| A21 | 页面分诊评分 | alerts.latest_triage_id→alert_assessments.confidence/score_state；0..1按百分比显示 |
| A22 | 当次分诊判定、理由、时间 | 同一alert_assessments的verdict/rationale/assessed_at |
| A23 | 当前判定 | alerts.disposition；采用反馈或分诊的同次判定 |
| A24 | Explain 正文 | alerts.latest_explanation_id→artifacts(kind=alert_explanation).body |
| A25 | Explain 生成时间／方式 | alert_explanation.generated_at/generation_method；历史不编时间 |
| A26 | Explain 关键依据 | alert_explanation.source_refs |
| A27 | Explain 建议动作 | alert_explanation.recommendations |
| A28 | 原始数据 | alert_materials.raw_text/raw_json/ocsf_json/retention |
| A29 | IOC 候选 | alert_objects.object_role= ioc/both；类型与hash算法明确 |
| A30 | IOC 查询结果 | alert_basic Run的tool step+tool_response；当前查询与旧来源标签分开 |
| A31 | 租户 | 全部表tenant_id；API显示授权租户 |
| A32 | 反馈判定和核查理由 | alert_assessments(kind=human_feedback).verdict/rationale/actor |
| A33 | 响应建议 | alert_assessments.recommendations或result建议；proposal_id稳定 |
| A34 | 审批状态 | response_links真实approval_id→既有审批状态，unknown不等于无需 |
| A35 | 执行结果 | response_links真实action_id/receipt_artifact→实际回执 |
| A36 | Run、步骤、Tool、报告 | runs(kind=alert_basic)/run_steps/artifacts，保无Case归属 |
| A37 | 调用次数／token／成本 | 实际run_steps叶子调用usage；缺记录不补0 |
| I01 | 事件 ID／成员集合 | incidents.id+incident_alerts |
| I02 | 事件名称 | incidents.title，真实独立标题 |
| I03 | 事件说明 | incidents.description及latest_diagnosis_id→summary；管理说明与生成诊断分开 |
| I04 | 严重程度 | 成员severity最大值保留；人工覆盖值/理由/人/时间已定义并验证 |
| I05 | 处理状态 | incidents.handling_status |
| I06 | 事件负责人 | incidents.owner_id/assignment_state；改派影响目标写活动 |
| I07 | 涉及资产 | 成员alert_objects.asset_ref→库存；来源对象可展示但不伪装库存 |
| I08 | 活跃／全部告警 | count incident_alerts及成员handling_status过滤派生 |
| I09 | 最近更新时间 | max(incidents.business_updated_at,当前成员business_updated_at)；关系移入/移出更新事件自身时钟 |
| I10 | 首次活动 | min当前成员真实event_time；全未知则NULL |
| I11 | 最近活动／发生范围终点 | max当前成员真实event_time；与last_seen_at字段口径分开 |
| I12 | 分类 | 最新PRD未定义事件独立classification；原型仍有兼容属性，不照搬成业务事实。待页面团队移除或另定需求 |
| I13 | 优先级 | incidents.priority_value/state/source，无值NULL |
| I14 | 优先级评分／因素 | incidents.priority_basis；不平均告警分诊分数 |
| I15 | 事件标签 | incidents.tags；资产标签另读库存 |
| I16 | 解决说明、解决人、解决时间 | incidents.resolution_note/resolved_at/resolved_by |
| I17 | ATT&CK 阶段数量 | 按成员distinct alert_id在每个detection.tactics中计1 |
| I18 | 检测技术并集 | 成员detection.techniques去重并集 |
| I19 | 实际归并依据 | incident_alerts.correlation_basis/basis_version；历史活动保旧依据 |
| I20 | 共同线索 | 按有类型alert_objects及correlation_basis派生，仅表示共享对象 |
| I21 | 告警—对象关系图 | incident_alerts+alert_objects；边带来源，不当因果 |
| I22 | 库存信息／匹配依据 | alert_objects.asset_ref/match_basis/state→既有库存 |
| I23 | 关联调查／Case | case_incidents明确关系 + case_alerts成员交集；DTO分清显式关联与部分成员命中 |
| I24 | 处理活动 | activities/targets按实际incident及成员目标读取 |
| D01 | 告警统计、过滤、排序、导出 | alerts+对象关系和字段索引；顶部总体统计独立，未选导出筛选前200，不建统计事实表 |
| D02 | 调查进行中统计／事件关联调查卡 | case_alerts/run_members/runs.state关联实际执行；AI是否算卡片需DTO定义，不用Alert旧状态猜 |
| D03 | 普通告警评论 | comments.alert_id/body/author/created_at |
| D04 | 告警完整时间线 | activities+activity_targets精确告警；自动过程来自同告警Run，禁止串别案 |
| D05 | 反馈 fp／authorized 同步关闭 | 同事务写human_feedback、disposition、handling_status、closed_at及所选目标活动 |
| D06 | 手动关闭／重开告警 | alerts.handling_status/closed_at/reopened_at+活动；处理说明选填 |
| D07 | 事件改派／解决及保存前覆盖提示 | incidents及全部incident_alerts目标状态/负责人同事务写；活动存实际覆盖列表供提示 |
| D08 | 建议→审批→执行 | results.recommendations稳定ID→response_links→审批/动作/回执 |
| D09 | 检测时间／完成取证时间 | 来源event_time与真正步骤ended_at分别保存；缺取证阶段不虚构耗时 |
| D10 | 事件队列卡片 | incidents业务状态/derived_severity/真实成员/真实Run关系，独立总体统计 |
| D11 | 事件压缩率／攻击中断 | 压缩率需要明确分母及完整来源计数；已接收计数不足则NULL。攻击中断必须真实响应回执，不从批准或Run完成推定 |
| D12 | 启动调查与告警业务状态 | runs.state不等于alerts.handling_status；启动是否回写业务状态交后端明确动作，不另造状态字段 |
| T01 | 来源、规则、战术／技术、Fusion 评分、同次分诊评分 | 材料detection及同次alert_assessments→input_snapshot→实际model_request；字段不无差别塞模型 |
| T02 | OCSF 进程 PID、命令行、父进程等 | alert_materials.ocsf_json+object_attributes投影；实际模型视图/省略记录在artifacts |
| T03 | 进程名称、路径、SHA256、账户 | object_attributes process_name/path/hash_algorithm/hash_value/username；湖工具仍需完善读取 |
| T04 | 进程类别、活动、动作、结果 | OCSF原文+detection.ocsf_class_uid及action/outcome；工具合同须按实际类读取 |
| T05 | 进程会话 ID | object_attributes.session_id+tool_response原返回 |
| T06 | 进程 PID／父进程／命令行细节 | object_attributes.pid/parent_pid/command_line/parent_command_line；不能从标题补 |
| T07 | 网络源／目标 IP、目标端口、协议、进程、主机、时间／ID | object_attributes端点/协议/进程及source_refs；tool_args固定窗口和类别 |
| T08 | 网络源端口 | object_attributes.src_port及工具返回；端口0..65535 |
| T09 | 网络目标主机名 | object_attributes.dst_hostname |
| T10 | 网络动作／结果 | object_attributes.action/outcome |
| T11 | 网络会话 ID | object_attributes.session_id |
| T12 | 告警—查询行对应及重投去重 | alert_source_refs命名空间+事件ID；tool_args范围及去重；tool_response逐行来源；原件与模型视图分开 |

### 5.2 调查展示：36项

| 编号 | 核对字段 | 新设计保存/读取 |
| --- | --- | --- |
| D01 | 本轮ID、所属Case | runs.id/case_id |
| D02 | 调查标题 | runs.title；results.title可有正式保存标题 |
| D03 | 基础调查/AI调查类型 | runs.kind / results.kind映射baseline、ai_saved |
| D04 | 首次/范围变化/用户提问原因 | runs.trigger |
| D05 | 本轮具体调查目标 | runs.purpose；messages.user.content |
| D06 | “建立案件的初始分析” | 由case_created展示的入口说明，不当结论 |
| D07 | 已完成/失败/执行中 | runs.state/stop_reason/stop_detail |
| D08 | 完整交付/部分交付 | runs.delivery_state/results.delivery_state + 实际阶段/覆盖检查 |
| D09 | 本轮结论/卡片主标题 | results.conclusion/conclusion_state |
| D10 | 实质结论与系统收尾说明 | conclusion_origin/validation_state+closing_note |
| D11 | 主要发现 | results.findings[].statement |
| D12 | 支持依据 | findings.support/evidence_refs |
| D13 | 反证 | findings.counterevidence |
| D14 | 与哪一轮比较 | runs/results.comparison_result_id，冻结同案基线 |
| D15 | 新增/移除的输入范围 | 两个run_members集合差 + scope_revision；pending修改过程见活动 |
| D16 | 相比已有结果的变化 | results.change_kind/change_summary |
| D17 | 对案件判断的影响 | results.case_impact |
| D18 | 限制/仍待确认 | questions/limitations、read_state和tool失败/截断回执 |
| D19 | 后续建议 | results.recommendations稳定ID及questions |
| D20 | 本轮输入数、实际读取数、当前成员数 | run_members约定/已读/实际分析；case_alerts当前数分别派生 |
| D21 | 当时输入原文、窗口、对象 | input_artifact+材料版本+实际model_request；固定窗口 |
| D22 | 逐告警判断与关联 | result_members及graph中来源/强度 |
| D23 | 记录创建/开始/结束/范围更新时间 | requested_at/started_at/ended_at/scope_updated_at |
| D24 | 本轮总耗时 | ended_at-started_at；运行中仅elapsed不是final |
| D25 | 模型调用数 | 真实kind=model steps计数，非父stage |
| D26 | Tokens/未记录 | steps.usage已知和+未知调用数，NULL不补0 |
| D27 | 工具记录数量 | 真实tool steps/保存工具工件数量分开 |
| D28 | 费用/未定价 | steps.usage.cost/currency/price_version/cost_state；不跨币种盲加 |
| D29 | 保存材料数量与原件 | artifacts.id/kind/content/blob_ref/retention/sha256 |
| D30 | 已开展工作/最后记录时间 | steps.seq/state/timestamps，最后记录max取得时间 |
| D31 | 报告正文/下载 | results.report_artifact_id→同版Markdown/JSON |
| D32 | AI明确保存结果的保存人/时间/对话 | results.source_answer_id/saved_at/saved_by + messages/conversation |
| D33 | 人工确认进入本轮依据 | input_snapshot.task_revisions + artifacts实际模型视图；不可变反馈版 |
| D34 | 本轮影响是否已成为Case当前判断 | cases.current_assessment_id→assessment_sources/members；不能最后结果自动代替 |
| D35 | 待更新范围及其版本 | runs.pending_update/scope_revision/scope_updated_at + run_members |
| D36 | 同一数据的读取一致性 | 统一result/history DTO和物理字段字典；UI实现另交接 |

### 5.3 新版页面增加的协作数据

| 需求 | 审计后支撑 |
| --- | --- |
| Case当前判断、依据、覆盖与过时提示 | case_assessments/sources/members，current指针；当前集合与覆盖集合比较 |
| Case成员添加、移动及关联事件 | case_alerts/case_incidents+scope_revision；pending同事务；移动双案固定锁顺序 |
| 故事、业务活动、执行过程各自时间 | 源告警event_time、结果形成/保存、人工完成/编辑、activities、steps分开；故事是组合视图 |
| AI问题、答案与重试 | conversations/messages/ai_question Run；重试新执行/新答复，保旧错误 |
| AI明确保存及人工编辑结论 | results.source_answer/input/edited_fields；原回答不变、不重跑、不自动采用 |
| 人工任务完整编辑/反馈 | tasks+task_revisions，结果/范围/实际完成人/时间必需，附件可选 |
| 对象证据与无对象材料 | alert_objects+来源refs+Run工件；无法归对象也保留，不能过滤丢弃 |
| 历史图与当前探索 | 不可变图artifact对比graph_explorations；明确base result/graph；保存探索不改成员 |
| 评论、附件 | comments三类父对象；artifacts attachment支持无Run；没有上传服务不宣称已接入 |
| 响应卡片 | 稳定proposal→真实approval/action/receipt；未对应回执保持未执行/未知 |

## 6. 已确认决定与剩余边界

| 项目 | 原因 | 当前建议与物理影响 |
| --- | --- | --- |
| D01 事件等级 | PRD既写成员最高又写可编辑 | 已确认保汇总且允许事件人工覆盖；四个override列保留，不能修改成员等级 |
| D02 当前判断采用 | 不能默认最新Run/保存AI就是当前判断 | 已确认有效基础结果自动采用、AI明确采用；范围/有效性/较新采用保护已实现数据库函数 |
| D03 Case执行互斥 | 只限制baseline还是同时限制AI实际执行 | 已确认只限制baseline单活跃，AI可并行；索引明确不含AI |
| D04 空案/已解决案 | PRD仍未定特殊场景 | 建议空案不能启动、已解决案变更不静默重开；保存历史和schema不受影响，相关动作未确认前不开放 |

D01–D03已答复并同步到合同、DDL和主设计。D04属于流程开放策略，本轮不新增表或臆造状态；保留为后续需要明确的边界。

## 7. 创建前后必须做什么

1. 已根据D01–D03答复固定合同；若页面团队保留事件独立classification，再先定义语义，不能照搬旧字段。D04约束相应API开放，不以时间经过当作确认。
2. 从这份字段字典生成显式socai2 schema DDL、ORM、API枚举/JSON校验；遵循现有SQL迁移入口。旧122迁移绑定public旧表，需移植语义，不能原样运行假定覆盖新表。
3. 在隔离PostgreSQL做建表、真实FK/空值/唯一/冻结/RLS及两会话竞争验证。SQL静态解析不是PG事务验证；线上版本与角色尚未核实。
4. 按告警/事件→Case及待更新→完整C1–C6→AI/人工/探索对接写入和读取；当前业务列/Tool漏读仍要修，表齐不等于产出齐。
5. 用既有样本做明确来源的迁移/读回对照；不长期两套真值双写、不自动将旧summary升级为已采用、缺失结果不补造。页面实现交接专门团队，原先已确认的保存前影响提示保持。

新schema拟使用严格租户策略；缺上下文拒绝访问。旧函数current_tenant_id()返回NULL本身不代表授权，新policy不沿用NULL旁路。应用所有实际入口必须设置事务租户，并核运行角色不绕过策略。[PostgreSQL行级安全文档](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)。

## 8. 本轮证据边界

本轮完成的是页面/代码/候选模型静态审计及合同结构验证。没有执行数据库DDL、写入真实记录、创建Run、模型/Tool调用、部署或提交推送。34项静态检查最终通过，原54份后台/原型来源指纹未变。首轮33/34：检查脚本漏识别sha256中的数字且要求文档列顺序与JSON一致，修正检查后通过；[初始回执](../operations/frontend-data-model-audit-20261103.initial.json)保留。实际检查项和结果见[审计回执](../operations/frontend-data-model-audit-20261103.json)。未确认项和真实PG验证不记为通过。原26表建议另存[审计前草案](../operations/investigation-data-schema-plan-20261103.pre-audit1.txt)，当前主方案已统一到审计后结构。
