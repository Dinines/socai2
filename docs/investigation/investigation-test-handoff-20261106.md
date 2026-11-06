# 调查测试总表与前后端数据交接

2026-11-06，分支 `codex/case-baseline-history-20261103`。本轮按用户要求再测三组案例，并同步核对数据、字段、页面及对应关系。**现有数据库能够支撑下表已验证的案件资料、当前结论、调查记录、原件及关系图对接；模型判断质量仍未通过。** 接口尚未合并返回或页面尚未接线的功能单列，不能把“表存在”说成完整功能已经实现。

本轮新增6条合成告警、6条湖日志、3事件、3Case、12Run、83Step、199工件；使用真实Kafka/Fusion、PG/ClickHouse、本机执行程序及DeepSeek，模型配置为 `deepseek-flash / deepseek_responses / standard`。三案各5次调用，共15次，15个provider响应均completed；本机累计63次。用户本次追加测试上限21次、绝对累计上限69，未用的6次不继续试探。单C仍为48000保守单位、最多4模型/4工具/120秒，无模型自动重试。

本机API为加载126对应代码作了一次正常重启；没有连接VPN、测试服务器部署模型、改提示词或放宽执行校验。页面只追加三份真实导出数据及脚本引用，保持原模板、布局和业务呈现逻辑。历史结果、原答及失败保留。

## 1. 本轮案例及页面

在[原Cases页面](http://127.0.0.1:4174/#/cases)搜索 `local-eval-20261106`。页面内容是数据库实际保存的结果，包含尚未修复的模型错误，不是人工改好的标准答案。

| 场景与页面 | 输入真实支持的事实 | 执行与当前结论 | 质量评估 |
| --- | --- | --- | --- |
| [01 账户清点与报表复制](http://127.0.0.1:4174/#/cases/socai2!local-standalone!local-eval-20261106-01!fbe17036-51e4-5d28-a3de-8c93d1f8d634!case!8b77d34f-e788-5fe9-8e41-abb5b2307b3d/case-info) | whoami与robocopy的process_start success；命令包含共享目录，不证明复制完成或授权 | A×2/I完成；C3领域范围拒收；C6已采用，结论为启动已观察、授权/外传/恶意性未证实，待核 | C6主结论保守；A1却把文件复制写为真实发生，部分领域缺资料仍写not_applicable；全链质量不通过 |
| [02 进程内存转储与文件归档](http://127.0.0.1:4174/#/cases/socai2!local-standalone!local-eval-20261106-02!fbe17036-51e4-5d28-a3de-8c93d1f8d634!case!0f27670e-c43d-584c-9e3d-c53c900c8f4e/case-info) | rundll32转储PID688与7z命令的启动；lsass.dmp仅是路径名，PID归属及文件产物未证实 | A×2/I完成；C3补查对象范围拒收；C6已采用，可疑、影响不确定 | C6的observed发现写“写至/打包为”，与同答复“仅启动”矛盾；缺资料领域问题仍在；质量不通过 |
| [03 恢复副本删除与文件改名](http://127.0.0.1:4174/#/cases/socai2!local-standalone!local-eval-20261106-03!fbe17036-51e4-5d28-a3de-8c93d1f8d634!case!0660179d-eb25-59fd-be63-373d6bd59173/case-info) | vssadmin process_start success；一个notes.docx.locked的file_rename success；命令含加密及note参数 | A×2/I/C3/C6结构均接受；C6已采用，称勒索特征明显，影响待核 | A0/A1/C3/C6存在效果扩大；I明确单次改名不证明全部完成，但未纠正A1既有扩大理由。质量不通过 |

三案的已保存C6均为 `model / accepted / partial / uncertain`；accepted是结构/来源校验接受，partial是交付完整性，uncertain是本次结论状态，都不是“正确率”。预期正常/恶意是独立构造答案中的意图，未送入模型；资料不足时待核符合已确认口径，不算良恶反向误判，也不能算明确判对。三样本不计算总体准确率。

### C3失败的准确原因

- 01：`domain_finding_scope_mismatch`。模型insider领域只声明成员B，却引用涉及A+B的F3。已发送格式Schema通过，应用层跨字段范围检查拒收。
- 02：`followup_binding_object_mismatch`。模型在B1补查填入user对象，实际发出的B1动态约束只允许host；原答也违反该wire Schema。不是工具目录没传。
- 两次均有完整provider响应和原答，属于**模型输出未满足约束**；不能写成服务不可用、Kafka/OCSF格式错误或数据库丢数据。阶段wrapper和model子步骤是同一次失败的两层记录，不能算两次调用。
- 两案C6仍实际调用并保存全案当前判断。C3失败及工具跳过原因保存在步骤/工件，当前案件资料读取业务结论。未伪造C3成功、未覆写原答。

逐阶段语义证据、输入可见性及引用路径见[独立语义审阅](../operations/evidence/additional-tests-20261106/semantic-review.json)。这些问题进入原R1—R8质量修复路线，不要求重做前端布局或新增结果表。

## 2. 同步核对的结果

| 核对层 | 本轮实际检查与结果 | 回执 |
| --- | --- | --- |
| 入湖与原件 | 6条计划事件与CH读回逐值一致；6份告警raw/OCSF与计划一致；保2原件/案及2来源快照/案 | 每案`lake-readback.json`、公开[01](../operations/evidence/additional-tests-20261106/local-eval-20261106-01.json)/[02](../operations/evidence/additional-tests-20261106/local-eval-20261106-02.json)/[03](../operations/evidence/additional-tests-20261106/local-eval-20261106-03.json) |
| 关系 | Case↔Alert/Incident、Incident↔Alert、Run/Result/Assessment成员与来源、对象→材料、活动→目标，以及步骤/图谱工件同Run/Case/租户检查无违例 | 同上`relations_checked`、`relationship_violations` |
| 实际GET | 48次只读GET；674项状态、字段、派生计数、成员、步骤、结论及原文比较，0不一致；时间作时区归一，已知数字字段按数值比较 | 同上`live_readback`与[补充读取回执](../operations/evidence/additional-tests-20261106/extended-readback.json) |
| 原页面投影 | 557项检查通过；87视图渲染：30 Case页、18基础调查视图、15事件页、24告警页。当前结论、原件、步骤及工件正文保持 | [页面核对](../operations/evidence/additional-tests-20261106/page-verification.json) |
| 实际浏览 | 三案列表及案件资料当前判断；01关系图8节点6边、C3失败/C6完成与执行明细；03原件含file_rename和notes.docx.locked。未点业务保存或执行 | [总索引browser部分](../operations/evidence/additional-tests-20261106/test-index.json) |
| 缺值 | 三案classification、due_at、独立证据索引指针均null；页面显示未设置/未记录；没有把原件数或图节点数当独立证据数 | `case-page-data.json`及前述实际GET/页面检查 |

674是多层比较次数，不是674个不同业务字段；87是离线真实页面渲染数量，不表示87页逐一浏览。图谱分别为8/6、8/6、10/7节点/边；材料页去重对象为每案2个主机/用户，数据库对象行每案4条。图中进程节点来自已保存原始进程字段，因此这些计数不同并不表示丢失。

## 3. 功能—字段—读取—页面交接清单

表名默认新`socai2` schema；API统一前缀 `/api/v1/socai2`。下表“已验证”只指列明的数据和读取范围，原导出页面为只读。逐字段基础清单见[告警31项、事件23项、共享19项](socai2-page-reader-20261104.md#逐项字段对照)，Case新增字段见[126数据交接](socai2-page-data-handoff-20261106.md)。实际类型以[OpenAPI](../design/socai2-independent-api-v2.openapi.json)、[字段字典](../design/socai2-field-dictionary-20261103.md)和JSON合同为准。

| 编号/功能与页面 | 数据库存储或确定计算 | 读取出口/导出 | 实现与本次验证边界 |
| --- | --- | --- | --- |
| F01 告警列表/概览 | `alerts`身份、title、severity、状态、owner、优先级、来源及各时间；`latest_material_id` | `/alerts`、`/alerts/{id}`的facts；`database.json.alerts` | 6告警事实逐值通过；未知原厂/负责人不借连接器/受影响用户补值 |
| F02 检测标签/置信度 | `alert_materials.detection`；当前材料指针 | SubjectView.material；原页告警概览/原件 | 检测数据保存读回；本批未提供ATT&CK标签，页面空态合理，不把模型战术当检测标签 |
| F03 告警AI基本分析 | `alerts.latest_triage_id/latest_explanation_id`、`alert_assessments`、解释工件 | `/alerts/{id}` triage及`analysis_url`；A主体trace | 6个A结果保存；判定、评分、理由保持同次；内容存在不等于判断正确 |
| F04 原始告警材料 | `alert_materials.raw_json/raw_text/ocsf_json/enrichment/retention` | `/alerts/{id}/materials/{material_id}`；`#/alerts/{pageId}/raw` | 6份完整原件逐值通过，03浏览可查；大小限制/外部正文缺失必须显式返回 |
| F05 来源快照/来源ID | `alert_source_refs`、非Run的`artifacts.kind=source_snapshot` | 主体records/sources；导出sourceArtifacts及原件页 | 6来源引用/6快照保存；来源ID与内部Alert UUID分开 |
| F06 事件概览/成员 | `incidents`、`incident_alerts`、当前成员alerts | `/incidents/{id}`、`records/members`；事件5页 | 3事件成员均2，时间/去重对象读回通过；单条告警严重程度不自动写Case严重程度 |
| F07 事件诊断 | `incidents.latest_diagnosis_id → incident_diagnoses`、I Run/工件 | 主体analysis及trace；事件分析/Case历史的I记录 | 3诊断及各I步骤可取；不把归并依据当恶意结论 |
| F08 对象与关系 | `alert_objects.namespace/object_type/object_key/object_role/material_id`；`incident_alerts.correlation_basis` | 主体records/objects、members；对象页/事件图 | 当前材料去重2对象/案；全对象行、归并依据在库/导出；关系不证明因果 |
| F09 Case列表/详情基本信息 | `cases.title/description/handling_status/owner_id/severity/priority_*/tags/created_at/business_updated_at` | `/cases`、`/cases/{id}`；列表与case-info | 三案真实读取并呈现；severity/priority当前未赋值，页面未记录，不是缺列 |
| F10 Case分类/截止时间 | `cases.classification/due_at`（126） | `/cases` items.page_data、详情及`/page-data`；PATCH同路径 | 本批三案均null；前批DA01实测保存/清空/版本冲突，4合同样例有值。原只读页不承诺保存接线 |
| F11 当前案件结论 | `cases.current_assessment_id → case_assessments.conclusion/origin/validity/formed_at` | Case详情.current_assessment、page_data.determination、`case-page-data.json` | 3案列表/资料同一已采用文本；不取最新Run或失败理由冒充结论 |
| F12 判断来源/覆盖/新鲜度 | `case_assessment_sources/members`、`run_members`冻结指针、输入工件与125新鲜度函数 | Case详情.current_assessment的sources/members/input_freshness；页面结论下方 | 每案覆盖2/2，来源Result同Case；新鲜度表示输入未变化，不表示语义正确 |
| F13 Case成员/关联事件 | `case_alerts/case_incidents`及scope_revision | Case详情.members/linked_incidents；`/associations`、`/members/move` | 三案读取关系通过；添加/移动写链已有代码，本轮未新增交互写验收。事件全成员与显式关联不要互相推导 |
| F14 调查历史 | `runs`三种父主体、`results`及成员关系 | Case `/history` + Alert/Incident analysis目录/trace；导出runs | **本批Case history返回1条baseline，原页4条由2A+1I+1C合并。后端需按主体组合并去重，不可仅取Case history就说缺3条** |
| F15 调查状态/耗时/用量 | `runs.state/delivery_state/started_at/ended_at/stop_reason/limits`；`run_steps.usage` | Case Run详情、主体trace；历史/执行明细 | 12Run已结束，15实际model步骤；阶段父节点不得重复计费；cost unpriced不是0费用 |
| F16 本轮发现/变化/影响 | `results.conclusion/findings/questions/recommendations/change_*/case_impact`及result_members | `/cases/{id}/results/{result_id}`；调查发现/概览 | 3份结果所有返回字段逐值通过；本轮首轮无有效前轮对照，不能补造变化结论 |
| F17 执行原因/错误 | `run_steps.state/error/input_artifact_id/output_artifact_id`、输出工件 | Run详情.steps、主体trace、工件正文；AI分析→执行明细 | 两C3拒收完整保留；原因可专门回查，Case当前字段仍是业务结论 |
| F18 输入/原答/工具返回 | `artifacts.content_json/content_text/sha256/size_bytes/source_refs/retention` | Case `/runs/{run}/artifacts/{artifact}`或主体artifact；查询与证据 | 199工件目录/正文进入导出；C6原答与图谱通过实时正文GET；未生成/超限不可悄悄替换摘要 |
| F19 关系图/来源材料 | `results.graph_artifact_id → artifacts`的nodes/edges/source_refs | 工件GET；Case attack、Run graphs | 三图保存且同Run；01实际浏览8/6。图中告警状态显示未记录，alerts.handling_status已有值，属显示映射待接，不是缺列 |
| F20 案件故事 | 告警event_time、已保存Result时间、完成H版本；原件/Run引用 | 组合前述读取；Case story | 时间线可渲染且来源保留；本轮无完成H，不编人工故事 |
| F21 独立证据/关联威胁 | `cases.current_evidence_artifact_id → artifacts.kind=case_evidence_index`，entries/verdict/source_refs/threat | `/page-data`、`/evidence-index`写入；对象与证据/列表 | 本批未自动产出索引，null；前批4合同样例已核clean/恶意/unknown/缺记录、去重和版本。调查发现不会自动变成独立证据 |
| F22 人工任务/H版本 | `tasks.current_revision_id → task_revisions`及result_scope/source_refs/result_text/completed_* | `/cases/{id}/tasks`及revisions；Case tasks | 新三案0任务；g有已完成人工范围确认，原H→第二C容量失败保留；本轮未测新H |
| F23 活动与修改前后值 | `activities`、`activity_targets.before_value/after_value/result_state/reason` | 主体records/activities；Case导出及activity投影 | 三案18条数据库活动/39目标保存；页面35/35/37还合并83Step和6告警记录，不等于DB活动行数；完整目标前后值需读导出/专门出口，原抽屉未全显 |
| F24 评论与附件 | `comments.body/author_*/edited_*`；`artifacts.kind=attachment/file_name/blob_ref/retention`及Case归属 | 主体comments出口；Case导出/后续聚合；comments页 | 本批均0；表及身份字段存在，未验附件上传、文件保管或Case通用评论CRUD，不得宣称完整实现 |
| F25 图谱探索保存 | `graph_explorations.base_* / graph_state / row_version` | 当前导出保留表；原页面探索交互 | 本批0；持久结构预留，正式服务保存接线未验。已完成的C5图读取与此功能不同 |
| F26 助手问答/明确保存/人工采用 | `conversations/messages`、`results.kind=ai_saved/source_answer_id`、assessment来源 | `/ai/messages`、save/adopt合同；当前路由明确501 | 数据结构存在但本批0，真实Q执行未实现；原对话演示不能算服务闭环。本轮C6自动采用不经过这三个501入口 |
| F27 响应建议/执行回执 | `results.recommendations`；`response_links.*`、receipt_artifact_id | Result、主体records/responses、导出；报告与响应 | 建议保存；本批0执行引用，不等于已审批/执行。外部响应系统继续负责执行，不能从建议补造回执 |
| F28 知识/资产/历史/湖查询 | `public.aisoc_kb_documents/assets`；C1/C2快照、tool_request/response、CH事件 | 调查查询工件及实际返回行；PG标题FTS | 本批C2知识为预算保留而跳过；资产查询0行，图源未连接，不能声称消费SOP/向量/图。已有库准备证据独立保留 |

### 接线必须保留的区别

1. **当前成员、冻结输入、结果覆盖、当前判断覆盖是四套关系。** 分别读取case_alerts、run_members、result_members、case_assessment_members；不是全用Case成员列表替换。
2. **null/0/partial分开。** 没有独立证据索引为null；有效空索引为0；部分覆盖只表示已知部分。原件、图节点、发现、独立证据、威胁计数不能混用。
3. **来源完整字段不一定已全部摆在页面。** source_refs/JSON路径、case_incidents关联元数据、activity_targets前后值、证据索引版本均已保留；原页只显示主要摘要/链接。后续可以补展示而不改存储结构。
4. **数值编码按合同转换。** 当前SubjectView的triage.confidence来自JSON字典，会出现`"0.40000"`，DB导出为`0.4`；页面百分数使用confidence_percent数值。同一次评分与理由必须绑定，不能跨来源拼接。
5. **模型输出和当前Case管理状态分开。** 自动保存调查判断不会自行把案件改成已解决，也没有给未分配案件自动找负责人。
6. 原页面模板已支持这些显示区，但测试入口是已保存导出。接实时服务时还需完成接口组合、分页、原页面按钮写入及鉴权接线；这些实现待办不会使已保存字段消失。

## 4. 所有相关测试的索引

本机13个模型批次按各批**最后保存的导出**聚合，原较早导出仍保留。去重后26告警、13事件、13Case、53Run、377Step、890工件、14Result、1H/1版本，共63次实际模型尝试。此处是历史快照集合，不是本轮重新读取全部旧Case的当前状态；a/b/c后续legacy页面判断在前批数据交接快照中另有记录，不改早期导出。

| 批次 | 模型尝试 | 主要覆盖/保留结果 |
| --- | ---: | --- |
| local-maintenance-20261105a | 5 | 首轮A/I/C，C6缺followups而拒收；保系统交接及原答 |
| local-maintenance-20261105b | 4 | C3对象绑定拒收，当时C6未调用；该历史行为不被新强制收尾回填 |
| local-maintenance-20261105c | 5 | C6格式拒收；查询投影/预算诊断材料保留 |
| local-maintenance-20261105d | 5 | I范围拒收、C6拒收，系统当前收尾业务字段可查 |
| local-maintenance-20261105e | 5 | C3成员绑定拒收、C6响应不完整；系统收尾 |
| local-maintenance-20261105f | 4 | C6调用前输入容量受限；系统收尾，不能计C6真实调用 |
| local-maintenance-20261105g | 5 | 首轮模型判断和湖查询；H完成后第二C在调用前受容量限制，原判断保留 |
| local-eval-20261105-01 | 5 | 正常意图回归；待核，A1复制效果扩大 |
| local-eval-20261105-02 | 5 | 转储/归档；敏感但待核，PID/产物/外传未证实 |
| local-eval-20261105-03 | 5 | A1/I/C3依据校验失败；C6已形成判断但效果扩大，质量失败 |
| local-eval-20261106-01 | 5 | 本轮01；C3领域范围拒收后C6收尾，数据与原页读回 |
| local-eval-20261106-02 | 5 | 本轮02；C3对象绑定拒收后C6收尾，数据与原页读回 |
| local-eval-20261106-03 | 5 | 本轮03；格式均接受但语义扩大，数据与原页读回 |
| page-data-20261106T013645Z | 0 | 独立4Case/8告警/6证据目录条目；固定legacy文本，专测分类/期限/证据/威胁/缺值；不是模型案例 |

可机器读取的[总索引](../operations/evidence/additional-tests-20261106/test-index.json)逐批列Case ID、原件目录、plan/expected/database/manifest SHA256、状态与错误，避免只保留成功样本。每批目录在`.local/local-investigation/validation/{batch}/`；`plan.json`固定输入/限制/候选源码，`expected.json`仅评估用，`lake-readback.json`证明入湖，`exports/{时刻}/database.json`保存29表，manifest及伴随GET/错误分类/新鲜度/page-data保留来源。不能重新运行已结束批次。

| 其他验证 | 索引及边界 |
| --- | --- |
| 本轮驱动/模型配置 | 31项定向通过；增加新批预算界限用例、补齐旧导出测试fixture。首次30过1失败是fixture缺Case tenant/scope新字段，修测试后通过，不是模型或数据库失败 |
| 页面数据与导出回归 | [前批21后端/24前端及真实PG回执](../operations/evidence/page-data-20261106/summary.json)；21后端本轮复用，24前端在新增样例后复跑通过，不叠加成更多不同测试。见[本轮验证摘要](../operations/evidence/additional-tests-20261106/verification-summary.json) |
| 原C6业务字段/系统收尾 | [限定汇总](../operations/evidence/investigation-repair-20261105/local-c6-business-fields-summary.json)及[前轮三案](../operations/evidence/investigation-repair-20261105/local-comparison-summary.json)；保最初失败 |
| 旧21环境Kafka双模型/补充上下文 | [Kafka到结论记录](kafka-to-conclusion-validation-20261105.md)、[k4上下文](../operations/socai2-context-k4-20261105.json)；是历史m/k/r证据，未在本轮重跑，不混入本机63次 |
| 旧协议/范围/预算回归 | [m3](../operations/socai2-schema-probe-m3-20261104.json)、[m4](../operations/socai2-schema-probe-m4-20261105.json)、[后续PG](../operations/socai2-followup-pg-20261105.json)、[当前审计](current-investigation-audit-20261105.md)；各自时点和替身/真实边界保持 |

本轮新增校验器的初次不一致也保留：页面校验曾把assessment包装层及分开的工件元数据/正文误当整行比较；补充GET校验曾把decimal字符串和数字直接比较。已修校验器并对同一原件复核，没有修改业务结果。两次中间数值校验和首次页面回执保存在本批evidence目录。报告脚本首轮7项Ruff问题已修；不是产品运行失败。

## 5. 下一轮部署模型如何复用

本轮不开始服务器模型测试。下一轮只将模型连接切换到确认后的地址、认证、协议和schema profile；PG/CH/Kafka、工件和页面仍留本机。预检只核就绪/身份/协议，任何实际模型请求计入新的明确批次额度，不把当前未用6次自动转入下一轮。

| 配对项目 | 已固定的DeepSeek对照 | 下一轮要求 |
| --- | --- | --- |
| 场景 | 本轮01/02/03的plan与expected及hash | 复用相同事件结构、行为字段和预期边界，另建模型专属主机、源ID、Case/Run及映射表 |
| 上下文 | 每轮C1冻结工件、A/I请求及工具返回 | 全部保存；共享operator-0及顺序历史会改变输入，需隔离账号或冻结历史，注明差异。不能声称仅模型不同的逐字对照 |
| A/I/C | 15份实际请求/原答、两个C3拒收原因、3C6 | A/I须由待测模型重新产生；不能复用DeepSeek分析充当前序结果。另做固定请求对照时须单列，不能冒充全链 |
| 预算 | 单C48k保守单位/4模型/4工具/120秒 | 先固定新campaign的允许ID、次数和累计上限；当前旧deployed默认全局50已低于累计63，不能直接照旧命令派发或清零账本 |
| 场景检查 | 原件/关联/GET/page验证脚本与本表F01—F28 | 同步跑同样读回；增加部署模型结果列，失败先分服务/输入/输出/容量/质量，不自动重试 |
| 判据 | 启动≠完成，命令参数≠产物，缺源≠不适用，关系≠因果 | 分开记录良恶反转、待核、证据扩大、范围错误；保原答，不人工补成成功 |

本机数据用例和查询脚本可先交接；H后容量、知识实际消费、语义约束、实时表单、Q执行及部署模型对照继续沿[现有OpenSpec任务](../../openspec/changes/complete-socai2-investigation-chain/tasks.md)推进。任务仍19/26，3.7/3.10/3.12/3.14/3.16/4.1/4.2未核销，不归档完整change。
