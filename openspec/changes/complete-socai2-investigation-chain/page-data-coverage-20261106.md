# 页面功能与数据库数据覆盖核对

用户最新明确：本轮只判断页面需要的数据能否在当前数据库中保存、关联和取回；接口、部署、跨域、算法与执行流程以后可以调整，不作为阻碍前后端推进的理由。此前[实时对接评估](integration-assessment-20261106.md)保留为技术参考，不作为本轮验收门槛。

**结论：核心调查数据可以支撑前后端继续推进，没有发现已核主链的断关联；但不能宣称整套页面数据已经零缺口。明确缺Case分类和Case截止时间的存储字段，另有“判定”“关联威胁数/独立证据条目”的页面数据含义需要固定。** 这几项属于字段/数据合同收口，不要求先重写流程或后端。

## 核对依据及当前实存

依据是当前产品需求、原页面实际字段、结构化字段合同，并于2026-11-06 00:31:48 UTC对本机`socai2_local_20261105`使用现有受限API数据库角色进行只读、可重复读查询。仅核本机验证租户，未写数据库、未调用模型、未修改配置或页面；凭据仅在进程内使用，没有输出。

- 实际29表459列；20告警/20材料/20来源引用/47对象、10事件、10Case、41Run、294步骤、691工件、11正式结果、1任务/1任务版本、65活动/134目标变更记录。
- 10Case中7个指向当前判断，7个均有判断来源；其余3个旧失败Case没有当前判断，不能把样例未产出误判为数据库缺列。11结果中8个有结论，4个有发现，11个有问题列表，4个有响应建议，1个有指定比较及变化摘要。
- 11结果均有关联图和报告；11份alert_graph都保存了节点与边。另保存11份JSON报告和11份Markdown报告，48份模型请求及48份模型返回。记录有值不代表结论正确，03的事实扩大仍是既有质量问题。
- Case严重程度/负责人/优先级当前均无实际值，但对应列存在；7个Case有description。对话、消息、探索保存、评论、响应关联当前均0行，attachment工件也未出现；相关表/字段已经存在，这些属于尚未产生的记录。
- 第二次只读关联检查：当前判断→Case、结果→来源Run、结果→同轮图/报告、任务→当前版本、对象→所属告警材料、当前判断→正式来源七项缺失计数均为0。结论只覆盖这七类现存关联，不宣称已枚举每个JSON内部引用。

## 页面数据去向

“可派生”指从确定的已存事实做关联/计数/排序，不是从模型正文猜出新事实；“已有承载”不表示当前样例已有值。

| 页面功能/字段 | 保存位置或确定的读取关系 | 数据层结论 |
| --- | --- | --- |
| 告警身份、状态、发生时间、来源、原文 | alerts、alert_materials、alert_source_refs | 已存可取；原文版本与告警绑定 |
| 告警解释、分诊、人工判定和理由 | alert_assessments；latest指针及alert_explanation工件 | 已有承载及实际记录；缺解释/失败不补值 |
| 事件成员、共享对象及归并依据 | incidents、incident_alerts.correlation_basis/basis_version、alert_objects | 成员与共同线索可取/派生；规则内容按实际保存值，不由同主机猜rule_id |
| Case名称、背景、状态、等级、负责人、标签、优先级 | cases各对应列，含owner_id/owner_source_value | 有明确保存位置；当前样例空等级/负责人/评分不是结构错误。负责人显示名解析依身份目录合同，本轮未核该目录，不宣称姓名已能完整查回 |
| 当前案件判断、形成者/时间、采用来源与范围 | cases.current_assessment_id→case_assessments；case_assessment_sources/members | 已存可取；系统收尾与模型判断保origin/validity，不用最新Run标题代替 |
| 当前依据、未解决事项 | 沿当前判断的sources取对应Result.findings/questions/case_impact、H版本或artifact_id指定工件 | 可按指定来源关联，含系统收尾的直接工件来源；不能拼接所有历史未决项冒充当前判断 |
| 本轮目的、结论、发现、变化、影响、建议 | runs.purpose；results的purpose/conclusion/findings/questions/comparison_result_id/change_summary/case_impact/recommendations | 结构齐全；部分旧轮没有产生值，不需因此新增字段 |
| 调查历史、实际耗时、步骤、工具和用量 | runs、run_members、run_steps、artifacts | 可读取并聚合；运行中/unknown和缺用量保持原状态 |
| 冻结输入、实际成员覆盖、依据是否变化 | run_members的material/triage/feedback ID；input_snapshot/C1；Case范围与H历史版本 | 所需版本和关系已留存，可比较；外部未跟踪数据不冒称已检查 |
| 案件故事/时间线 | 告警实际时间、正式Result时间、H完成事实及相应来源 | 可排序派生，不必另造一张故事表 |
| 案件图、历史图、节点/边及依据 | results.graph_artifact_id→artifacts.content_json；节点/边/source_refs | 实际图数据已留；无调查图时可由成员—对象关系派生底图 |
| 对象与原始/调查材料 | alert_objects.material_id/source_path；材料、工件及results.findings.support等引用 | 基础材料可回查；独立证据条目与威胁计数另见D3，不能混计 |
| H标题、负责人、期限、状态、结果、范围、实际完成/修改人及版本 | tasks.current_revision_id→task_revisions及历史版本 | 有完整承载及1份实际完成记录；任务due_at不能代替Case截止时间 |
| AI会话、问题/答复、引用、明确保存的结果 | conversations/messages及source_run_id/input_artifact_id/source_refs；results.source_answer_id | 表和引用结构已有，当前0行；业务暂缓不等于数据库缺结构 |
| 保存图谱探索 | graph_explorations的基底Result/输入/图、graph_state及row_version | 可保存节点边、布局、展开/选择，当前0行 |
| 处理活动、批量目标、修改前后值 | activities、activity_targets.before_value/after_value | 已有记录；可按主体/目标回查 |
| 评论与附件 | comments；artifacts(kind=attachment)及文件名/MIME/hash/大小/正文或blob_ref | 结构已有，当前无样例；二进制可在对象存储，数据库保存受控定位，不把只有定位当已经留存文件 |
| 响应建议、审批/执行关联 | results.recommendations；response_links；receipt_artifact_id→artifacts | 建议已有；审批执行当前无记录。若要求只靠本库展示详情，应写入真实回执快照；已有承载，不是必须新增审批表 |
| 列表四指标、成员/对象/调查数量、ATT&CK覆盖 | 状态/分配、tasks、成员关系、objects、runs、材料detection | 可以计数/去重派生；不必为每个卡片另存冗余列 |

主要依据：[页面需求](../../../docs/design/alert-incident-case-product-requirements.md)、[字段字典](../../../docs/design/socai2-field-dictionary-20261103.md)、[结构化数据合同](../../../docs/design/socai2-data-contract-20261103.json)、[JSON内部合同](../../../docs/design/socai2-json-contracts-20261103.schema.json)。实际物理列与本次查询为准，字段字典中的早期阶段状态不替代当前实施记录。

## 需要收口的数据合同

| 编号 | 页面要求及证据 | 当前缺口 | 最小处理方向 |
| --- | --- | --- | --- |
| D1 / 明确字段缺失 | `workspace-view.js:68`的管理Case表单、Case列表/筛选均使用classification：未设置/真实威胁/信息性或预期活动/误报 | 实际cases、case_assessments和results均没有对应的Case级结构化分类；conclusion_state是有依据/未决等状态，不能替代分类，自由文本结论也不能作为稳定筛选值 | 在同一OpenSpec中明确Case级分类、枚举/未设置语义及修改来源，再做最小增量存储；不从告警、Incident或模型正文猜。此轮仅记录，不做DDL |
| D2 / 明确字段缺失 | 同一管理表单及Case列表展示`c.due`案件截止时间 | cases没有due_at等字段；目前只有task_revisions.due_at，两者不是同一事实 | 为Case本身定义可空带时区截止时间及变更记录；不能取最早任务期限冒充，不回填历史假值 |
| D3 / 页面数据含义未固定 | `app.js:350/374/377`有“判定”和“关联威胁”；威胁数按前端独立证据的threat/verdict去重，材料页亦有独立证据条目数 | determination目前默认“未设置”，没有明确对应的已存业务量；新数据合同有对象、材料、Finding及引用，但没有明确承接前端独立证据threat/verdict的统一记录口径 | 先确定判定是否复用当前已存结论，以及威胁/独立证据的单位、稳定ID和来源；能由已存事实定义则派生，否则补最小版本化内容合同。不能把工件数、节点数或Finding数直接当威胁数。尚不能列为完全覆盖，不能仅因有通用JSON便宣称已解决 |

D1/D2是确实需要补的Case数据设计项；D3是必须先定义的数据语义项，不预设要新增表。其余本轮已核项的当前空值、来源尚未写入、流程失败、模型判断不准确，不当作数据库结构阻塞。保存筛选集等个人显示偏好与调查业务事实分开，本次不要求全迁入socai2业务表。

代码依据：[Case管理表单](../../../prototypes/security-pages-v2/workspace-view.js)、[Case列表与派生](../../../prototypes/security-pages-v2/app.js)。原页面保持；此评估不以删页面字段来掩盖数据缺口。

## 推进判断

核心案件/调查/关系图/H/材料的读取可以继续推进；同时把D1/D2的字段定义及D3的读取口径纳入R7数据合同收口，相关页面字段未补前不宣称已验收。后续流程及模型修复仍可沿原计划做，不必等其全部稳定才让前后端开始取这些已有数据。不得将此次数据库核对等同模型质量或全页功能验收；任务状态仍19/26、模型尝试仍48/50。

用户随后要求规划推进，已形成[数据优先修复方案](design.md#页面数据合同优先推进2026-11-06)及[DA01—DA06验收](acceptance-plan-20261104.md#页面数据合同验收da01da06)：分类/期限独立存储，判定复用当前结论，证据采用现有工件表内的明确版本合同和当前指针。上述D1—D3仍是本次实查缺口，后续规划不表示已补列或已有证据索引。

校验与独立复核：OpenSpec strict、diff空白检查、本文7个相对链接及任务19/26状态保持检查通过。未参与撰写的`/root/review_design_audit`核对页面与存储合同，收紧负责人姓名目录的未验证范围并补齐直接工件来源后，结论 **ACCEPT，0剩余必须修**。独审沿用本轮实际只读数据库回执，未另连服务或调用模型；此结论只确认数据覆盖评估准确，不代表D1—D3已修复或全页功能验收。
