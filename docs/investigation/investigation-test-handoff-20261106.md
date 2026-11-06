# 调查测试总表与前后端数据交接

## 前后端联调从这里开始

**部署后的三案功能审计。** 本轮 A 发布 3/4，I 发布 3/3；三次真实 C3 超时后均保存系统交接。可从作业输入追到每步工件、系统判断和页面读取，也可查看 C4、C5 与正式 Result 的独立合约对照。[阶段审计与签收结论](../../deliverables/investigation-validation-20261106/processing-functional-audit.md) · [本机逐步展开](http://127.0.0.1:4177/)

**21 当前部署。** `processing-20261106-r3` 已安装为按需作业，新合成样本已建案并准备了基础调查，模型和工具调用均为 0。固定命令、主体 UUID 及回执口径见[部署与交接手册](../../deliverables/investigation-validation-20261106/processing-deployment.md)；页面功能、已有数据及优先修正项见[前端功能清单](../../deliverables/investigation-validation-20261106/frontend-feature-list.md)。

[下一阶段交接验收、四案结果与页面差异](#下一阶段的前后端交接验收) · [本机四案入口](http://127.0.0.1:4176/)

**告警、事件、调查三个页面可以同时开始读取联调。** 三条线共用 01 案，分别从自己的入口进入。样例文件均在下方命令导出的 `local-eval-20261106-01/` 中。页面链接打开本机静态预览，GET 路径以 `/api/v1/socai2` 为前缀。

现有两种可验收的调查状态。DeepSeek 01 有模型结论；21 上的 Qwen3.5-9B 新案有真实告警分诊和事件诊断，Case 在调用模型前停止，留下系统收尾。可用同一套页面组件分别验两种状态。[21 实测、样例包和接线验收](#21-内网小模型实测)

| 原页面入口（01 案） | 拿哪些文件、接哪个 GET | 首次验收与待接项 |
| --- | --- | --- |
| **告警** · [队列](http://127.0.0.1:4174/#/alerts) · [账户清点告警](http://127.0.0.1:4174/#/alerts/socai2!local-standalone!local-eval-20261106-01!fbe17036-51e4-5d28-a3de-8c93d1f8d634!alert!07247cff-5d9c-5e0d-8edf-e29235ba0bee/overview) | `alerts-1.json` → `/alerts/{alert_id}`，`alerts-1-material.json` → 同告警的 `/materials/{material_id}`，`alerts-1-trace.json` 是这条告警的 A Run 执行记录 | 核标题 `Account enumeration command observed`、`facts.handling_status=new`、`triage.verdict=needs_review` 与 `triage.confidence_percent=40`。第二条告警 `alerts-2.json` 为 35，理由与原件分别跟随各自告警。已验证保存数据的展示，原页面实时获取和操作写回待联调 |
| **事件** · [队列](http://127.0.0.1:4174/#/incidents) · [01 事件概览](http://127.0.0.1:4174/#/incidents/socai2!local-standalone!local-eval-20261106-01!fbe17036-51e4-5d28-a3de-8c93d1f8d634!incident!9ce426e7-fe6f-4fc9-9cb2-32ccaa31c224/summary) | `incidents-1.json` → `/incidents/{incident_id}`，`incidents-1-members.json` → 同事件的 `/records/members`，`incidents-1-trace.json` 是 I Run 的步骤与工件目录 | 核事件标题、`handling_status=new`、`derived.member_count=2`、`derived.object_count=2`。两个成员的 `items[].id` 应分别打开上面的两条告警。事件诊断从本事件的 `analysis_url` 下钻。原页面的实时成员与诊断读取待联调 |
| **调查** · [运行列表](http://127.0.0.1:4174/#/investigations) · [01 基础调查 Run](http://127.0.0.1:4174/#/investigations/socai2!local-standalone!local-eval-20261106-01!fbe17036-51e4-5d28-a3de-8c93d1f8d634!run!43ce26a6-7643-4d83-8ecd-11a932b4548f/overview) | `baseline-run.json` → `/cases/{case_id}/runs/{run_id}`，`result.json` → 同 Case 的 `/results/{result_id}`，`graph.json` 是该 Run 的图工件。另用 `case.json` 核所属 Case 的已采用判断 | 核 `run.state=completed`、`result.delivery_state=partial`、`result.conclusion_state=uncertain` 和图的 8 节点/6 边。详情按 Run 打开；单案调查历史合并 2A、1I、1C。独立运行列表的实时汇总、图节点告警状态及 H 后有效比较是待接或待补样例项 |

### 拿样例和复跑

在当前仓库根目录运行下列命令。Python 从[已分发的 ZIP](../../deliverables/investigation-validation-20261106/README.md)读取保存的响应和导出，Node 使用仓库里的原页面渲染代码。两者都可离线运行。

```sh
python docs/operations/check_investigation_handoff.py --examples-dir .local/investigation-field-examples
node docs/operations/verify_investigation_pages_20261106.cjs --handoff
```

第一条生成一个新目录，已有目录受保护。只想复核时可省略 `--examples-dir` 和路径。打开其中的 `index.json` 可按实际 GET 路径找到响应体。目录含 **48 份保存的 HTTP 响应体**，另有 `contracts/` 下 **4 份数据库导出的 page_data**。需要手动看原页面时，运行 `python prototypes/security-pages-v2/serve.py`，再点击上表任一队列或详情链接。

| 从哪个页面开始 | GET 响应里读什么（路径统一带 `/api/v1/socai2` 前缀） | 在案例里核什么 |
| --- | --- | --- |
| 告警详情与原件 | `/alerts/{id}` 的 `facts.id/title/handling_status/event_time`；同一个 `triage` 的 `verdict/confidence_percent/rationale`；用 `facts.latest_material_id` 读取 `/alerts/{id}/materials/{material_id}` | 01 的两条告警各有自己的材料和分诊。检测源评分从 `material.detection` 读，AI 分诊分数从 `triage` 读。其余告警与事件字段见[逐项清单](socai2-page-reader-20261104.md#逐项字段对照) |
| 事件与成员 | `/incidents/{id}` 的 `facts.id/title`、`derived.member_count/object_count`；`section_urls` 下钻成员，`analysis_url` 下钻诊断 | 01 有 2 个成员告警。`/incidents/{id}/records/members` 的 `items[].id` 是告警 UUID。对象数按去重的对象身份计算 |
| Case 列表、资料、判定 | 列表 `/cases` 的 `items[].case`、`items[].page_data` 和 `metrics`。详情 `/cases/{id}` 的 `case.description` 是背景，`page_data.determination` 是已采用结论。判断版本、来源和新鲜度读 `current_assessment.value.id`、`current_assessment.sources[]`、`current_assessment.input_freshness.state` | 01 列表和详情显示同一句已采用判断。沿 `current_assessment.sources[].result_id` 能回到本案结果。其他类型的来源可指向 `artifact_id` 或 `task_revision_id`；无当前判断时保留空态 |
| 调查历史与过程 | Case `/cases/{id}/history` 读 `items[].id/run/result`；成员告警及关联事件的 `analysis_url` 读 `entries[].run.id`，详情/trace 按该主体与 Run 读取 | 01 显示 2 个 A、1 个 I、1 个 C。Case 历史本身返回 1 条。调查次数在同租户和来源环境内按 Run ID 去重；历史条目保留自己的 `run:<id>` 或 `result:<id>`，以保留同一 Run 的不同已保存结果 |
| 调查结果、图与报告 | `/cases/{id}/results/{result_id}` 读 `result.conclusion/findings/questions/change_summary/case_impact/recommendations` 及 `members[]`。取 `result.source_run_id` 路径上的 `result.graph_artifact_id` 工件，读 `content_json.nodes/edges`；Markdown 由 `delivery.markdown_artifact_id` 定位，正文读 `content_text` | 01 有 8 个节点、6 条边，02 有 8/6，03 有 10/7。图、报告及来源均须属于同 Case 与 Run。工件读取先看 `availability`；首轮无对比结果时保留实际 `change_kind` 和可空的变化说明 |
| 证据、威胁与人工任务 | `/cases/{id}/page-data` 顶层有 `classification/due_at/determination/evidence`；`evidence.state/evidence_count/threat_count` 一起读取。任务 `/cases/{id}/tasks` 读 `items[].current` 中的 `revision/state/result_scope/result_text/completed_at` | 四个合同样例的证据数/威胁数依次是 **2/0、2/1、2/0、null/null**。三份模型案均无独立证据索引。H 有值样例可查原包中的 `local-maintenance-20261105g`，其已完成版本只覆盖所选告警 |

**分页与范围。** Case 队列及历史用各自的 `next_cursor`，A/I 分析目录用 `next_before_run_id`，H 目录和版本用 `next_offset`。Case 详情的 `members_truncated` 或 `linked_incidents_truncated` 为真时，按已返回范围展示。当前 Case 成员、Run 冻结成员、Result 覆盖成员及当前判断覆盖分别有来源。七个小样例覆盖的是已返回的完整小集合。

**样例覆盖。** 01 的 `case-history.json` 和三个主体的 `*-trace.json` 可复核合并后的四个 Run。`/cases` 集合的分页形状和指标见 [CaseQueuePage 合同](../design/socai2-independent-api-v2.openapi.json)；48 份响应体取到了单案详情，列表展示值另外用原页队列与数据库导出核对。H 有值的既有 GET 在 ZIP 内 `.local/local-investigation/validation/local-maintenance-20261105g/exports/20261105T133839907971Z/api-responses.json` 的 `/tasks` 条目。该案覆盖 H 已完成、第二轮容量受限两种状态，有效第二轮比较仍缺样例。

**本次离线复核。** 基于 `34f3374` 保存的三案，按公开字段清单逐案核过 29 个 Case 字段和 29 个 Result 字段。七案用当前原页面渲染器执行 618 项检查，覆盖 95 次视图渲染，全部通过。其中核对了四个历史 Run 的实际链接、采用结论、图的实际节点和边，以及四例的未记录与零值。初次校验把同一 Run 的概览与工具链接都计入历史行数，限定为概览入口后通过。两条复跑命令校验冻结响应、数据库导出与当前页面；换用新的服务实现后，需从候选服务重新取得同案 GET，按相同字段和来源关系核对。

另用 01 案按原 `index.html` 的脚本顺序启动应用，在 Node VM 通过真实 `hashchange` 切换告警概览、事件概览、独立调查列表、独立 Run 概览和关系图。两条概览标题、列表中的 Run 链接、Run 概览的结论和关系图实际绘制的 8 节点/6 边均与该案保存值相符。此项单独验证三个页面可直接进入，使用的是静态导出。

### 接下来双方各做什么

1. **前端**并行核告警概览与原件、事件概览与成员、独立调查运行列表与详情。三个入口各自通过后，按来源 ID 串联三页，再用四个合同样例验 Case 管理字段和证据空态。对接真实 API 时使用后端 UUID，原页面导出的复合 ID 用于隔离来源环境及批次。
2. **后端**在优化调查前保留以上公开字段的类型、含义、可空性和来源。先固定当前版本的页面输出，再用同一批冻结材料核对候选版本。01 案已有一个兼容性反例：只把图工件内部版本从 v1 换成 v2，原页面会隐藏仍有 8 节点/6 边的图。版本变更时在读取/导出适配处明确映射，并验证原页确实显示图和来源。[现有版本判断](../../prototypes/security-pages-v2/socai2-recorded-import.js)
3. **联合回查**优先处理图上告警的处理状态、历史聚合及新旧工件的展示。待有 H 后有效第二轮时，补选定比较结果、变化说明及相应任务版本的有值样例。实时写操作、附件上传、保存图谱探索和 Q 等另按 F22—F27 的状态安排。证据冲突裁决和模型语义沿原调查任务处理，前述读取联调可并行。

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

## 下一阶段的前后端交接验收

本轮只核对**页面需要的值是否已存、来自哪条记录，以及缺值时能查到什么状态**。依据是四案已有的数据库导出和保存的响应。现有样例可以交给前后端做字段对照。

[逐字段取数清单](../../deliverables/investigation-validation-20261106/page-field-samples.md)给出告警、事件、调查 81 个字段的有值与空值计数、原件定位及四案主体 UUID。分类、截止时间、独立证据及人工确认另引用有值样本；负责人等尚缺正例的字段注明了排查范围。

| 四案数据 | 有值的范围 | 缺值时的实际记录 |
| --- | --- | --- |
| 告警 | 8/8 条有基本信息和原件，7/8 条有已发布的分诊及理由 | 卷影副本删除告警有分诊校验失败记录 |
| 事件 | 4/4 个有事件基本信息、有效严重度和成员，每个关联两条告警；2/4 个有已发布诊断摘要 | 凭据转储案有诊断超时回执，文件改名案有诊断校验失败记录 |
| Case / 调查 | 3/4 案已建 Case，三案均保存了来源为系统的“待核实”文字。账户清点案有正式 Result，另两案的文字来源可回查到系统工件 | 凭据转储案停在事件阶段，0 个 Case。有效模型结论的有值样例见既有 DeepSeek 三案 |

| 验收对象 | 真实字段与必须可见的状态 |
| --- | --- |
| 告警 | 用 UUID 核列表/详情标题、严重度、发生时间、来源 ID、处理状态；沿 `latest_material_id` 回原件。分诊有值时用同一次评分和理由，校验拒收时仍显示原件，并给出当前无有效分诊及本次执行记录。 |
| 事件 | `derived.member_count`、成员 UUID、`severity_effective`、归并依据及时间来自事实；当前 AI 摘要来自 `analysis_url` 的已发布诊断。入口同时提供最新尝试的状态与详情，可分别展示已发布摘要、失败、状态待确认和未开始。有旧诊断时保留来源及时间。 |
| Case / 独立调查 | Case 的当前文字取 `page_data.determination`，并读 `assessment.origin/validity/sources`。Run 的状态、停止原因、交付范围来自本 Run；若有 Result，才展示其覆盖、结论和图报告。要分别验“有模型结论”“仅系统收尾、有 Result”“仅系统收尾、无 Result”“尚未建 Case”。 |

**21 的 Qwen3.5-9B 已跑完现行四种不同场景**，其中后三案为本次新增。每案两份告警和原件、一个事件及其成员；02 无 Case，03、04 各有一个 Case 和系统工件。[可直接查看的原页](http://127.0.0.1:4176/) · [四案及原始响应交接包](../../deliverables/investigation-validation-20261106/21-qwen9b-handoff-cases-20261106.zip)

| 案例 | 告警及事件 | 最后实际留下什么 |
| --- | --- | --- |
| 01 账户清点与报表复制 | 两条分诊待核，事件诊断已发布 | Case 必需输入超过剩余视图容量，C3、C6 均未发给模型。Run 为 `failed/partial`，有系统收尾、1 份 Result、图和报告，模型结论覆盖 0/2。 |
| 02 凭据转储与归档 | 两条分诊待核，事件归并成功；事件诊断网关 45 秒超时，状态 `unknown` | 本次驱动在建案前停止。能查看两份事实及诊断尝试，Case 列表为空。此时应在事件页交代原因，C6 收尾只适用于已经进入调查的 Case。 |
| 03 卷影副本删除与文件改名 | 删除卷影告警的定性依据被拒收，改名告警分诊已发布；事件诊断因引用范围被拒收 | Case 的 C3 网关 45 秒超时。Run 为 `unknown/none`，Case 当前“待核实”来自系统工件，0 份正式 Result、0 次 C6 推理。 |
| 04 运维脚本与外连 | 两条告警分诊和事件诊断均已发布 | C3 网关 45 秒超时。Case 也是系统工件收尾，0 份正式 Result。按原测试设计，首轮无有效模型结论，人工确认和第二轮未触发。 |

后三案共 11 次模型尝试，8 份完整原答、3 次 HTTP 408（这三次用量未知）。逐案核了原始 GET 和 29 表导出；四案按案去重合计 89 个 GET 路径全部返回 200。Chrome 核对 36 个明细入口、4 个全局事件链接、5 个异常或待确认画面。原件、成员、已发布摘要及 Case 当前文字的按案核对通过。另按重点字段独立检查 105 项，其中 17 项差异可归为以下四类。HTTP 成功、页面能打开、必需值显示正确是三个分别核验的条件。

| 页面观察（供接手方参考） | 已存数据与当前显示的差异 |
| --- | --- |
| 事件概览缺诊断入口与状态 | 4 案的事件概览均缺指向该次 I Run 的入口；02 超时、03 拒收要下钻才能看清。概览直接显示已发布摘要或明确空态，并能点开这次尝试；成员列表始终可读。 |
| 事件严重度丢值 | 4 个事件的 GET 均返回 `derived.severity_effective=medium`，原页队列及详情头显示“未记录”。两处都按有效值显示“中”；真正缺值才显示未记录。 |
| 执行与交付枚举映射 | 5 个失败或未知 Run 明确返回 `delivery_state=none`，详情却显示“完整性未记录”。分别映射 `none` 为未交付、`partial` 为部分交付，保留 null 为未记录；单列 Run 状态和结论来源。 |
| 无效告警链接回到混合队列 | 4 个上下文中的无效告警 UUID 均回到包含演示条目的队列。应显示“告警未找到”，带显式返回入口。事件和 Case 已有未找到状态可供对照。 |

**数据交接结论。** 四案已经提供告警原件、事件成员、诊断有值和失败、Case 系统收尾及未建案样例。已有 DeepSeek 样例另提供模型形成的 Case 结论。按同案 ID 对照这些记录即可检查取值。上表页面差异作为接手方备注，与数据是否存在分别登记。

## 21 内网小模型实测

### 页面上的“部分交付”怎么看

| 对象 | 为什么会标为部分交付 | 页面取数时怎么区分 |
| --- | --- | --- |
| 告警 A、事件 I | 服务在保存分析结果、提交发布事务时把 Run 写为 `state=completed, delivery_state=partial`。成功发布也用这个组合。 | 查主体的 `latest_triage_id` 或 `latest_diagnosis_id` 以及对应结果；这才说明用户看到的是哪次分诊或诊断。[发布逻辑](../../services/api/app/socai2/stage_results.py) |
| Case 有有效模型结论 | C6 已接受模型结论，但只要还有一项覆盖限制，结果就标为 `partial`。当前 C5 用已保存材料建图，仅此范围即标为 `partial`，C6 会记录外部拓扑未查。未答问题、部分背景数据源、输入省略或成员覆盖不足还会产生各自的原因。 | 查 `conclusion_origin=model`、`validation_state=accepted`、结果成员的 `conclusion_covered` 和问题状态。DeepSeek 11 月 6 日三案均覆盖 2/2 个成员，每案留 5 个未答问题，这些案都有可显示的模型结论。[关系图交付](../../services/api/app/socai2/baseline_graph.py) · [C6 限制与结果](../../services/api/app/socai2/baseline_delivery_projection.py) |
| Case 只保存系统收尾 | 执行失败或 C6 缺有效模型回复时，系统仍可保存已留存的图、报告和待核实文本，结果也会标为 `partial`。 | 同看 `run.state/stop_reason`、`conclusion_origin=system`、`validation_state=system_only`。即使两条原件已读取，结果也可能只覆盖 0/2 个成员。实际原因可沿 Run 的步骤和输入工件回查。 |

联调建议将**运行状态、结论来源、成员覆盖**并列取数；详情再列本案仍缺的材料或待答问题。单看 `delivery_state` 无法区分以上三种情况。原型中的 `explore-case-01` 是“财务终端与跨主机活动核查”模拟案；21 的真实结果按批次和 Run ID 进入。

2026-11-06，基于 `34f3374`，批次 `local-deployed-20261106-01`。取既有 01 案的两条进程启动记录，逐条核对命令行、父子进程和活动字段相同。使用新身份、时间、专库与由本模型新生成的前序分析。真实 Kafka、Fusion 将两条告警归到同一事件，验证湖 2 条事件各 47 个字段与输入相符，旧湖中这两个 ID 命中 0 条。随后经带鉴权的独立 API 跑完本批；29 表快照和两组 GET 共 27 条，按路径去重为 25 条，均为 200。[打包的页面、响应与读回](../../deliverables/investigation-validation-20261106/21-qwen9b-pilot-20261106.zip)

| 页面 | 本案可交付的值 | 联调验收 |
| --- | --- | --- |
| 告警 | 账户清点、报表复制两条详情及原件。Qwen 两份分诊均为 `needs_review`，各 65%；DeepSeek 01 对应为 40%、35% | 按告警 ID 同时核判定、置信度、理由与来源材料。65% 是该模型给这次分诊的置信度。样例的恶意概率没有标注。 |
| 事件 | 事件 `9173ab28-8dd7-4be7-97ac-897e728d23e8` 的两个成员、对象计数、已发布 I 诊断及其执行记录均可读取 | 两个成员链接应指向各自的告警。模型给出英文摘要，于摘要中丢失了复制路径的反斜杠。原件保有完整命令，页面应能单独回看。 |
| 调查 | 独立 Run `3ece2370-1f19-4c60-9b59-5731d5ef43e7` 的状态为 `failed`；Result 有 2 个成员，`partial / uncertain / system_only`，图 8 节点、6 边。Case 当前展示系统收尾“案件性质待核实”，判断的成员覆盖数为 0。对照案同样可显示待核实，判断来源为 `model` | 独立调查列表和详情按 Run ID 进入；并列核 Run 状态、结果来源和当前判断。Case 中能读到文本、图或报告，都不能单独证明模型调查成功。 |

本批保存 4 个 Run、25 个步骤、55 个工件。模型仅收到 A、A、I 三次业务请求，三份原答都保存并发布，共报 11,553 tokens。C1 冻结两条材料，C2 实查的资产与 UEBA 均为 0 行，知识查询因预留工具预算而跳过。C3 的必需输入含事件诊断，这次它在 8 KiB 视图装配时被记为 `model_view_budget_exhausted`，最终视图 `ready=false / required_model_input_unavailable`。执行器以 `model_view_not_ready` 停止并在 C6 保存系统收尾。C3/C6 均为 0 次推理，Case 模型效果仍待验证。此前 DeepSeek 01 的 C3 曾收到模型回复但被范围校验拒收，随后 C6 有有效模型回复，可作为另一条展示路径。两案前序输入各自生成，无法据此比较模型总体准确率。

**图谱联调需要保留来源引用。** C5 把成员告警的来源节点编码为 `type=other`。原页面的 `graphContextView` 根据同一 Run 的冻结材料和精确来源路径，将这两个节点及其边关联回告警 ID。C5 回执 `c67537a3-ce55-4b80-b6b0-3bc66d3161e5` 也保存了两组 `member_anchor.alert_id/node_ids`。首次逐点核对跳过了原页面的这层转换，得到 10 个节点；该数字属于中间数据。[C5 生成字段](../../services/api/app/socai2/baseline_graph_projection.py) · [页面读取与归一化](../../prototypes/security-pages-v2/socai2-recorded-import.js)

真实 Chrome 从本地文件分别打开两条告警、事件、独立调查列表、Run 详情、图谱及 Case 内调查，7 个入口均到达预期页面。独立图谱初始画面显示 8 个节点控件、6 个可点击的边控件，与 C5 工件数量一致。

沿原页面的归一化读取链逐点核对，两条输入告警分别保留 2 条边，均与 C5 来源节点对应。逐点回执见包内 `preview/graph-field-readback.json`。

**后续顺序。** 前端现在即可用上述两案同时接告警详情与原件、事件成员与诊断、独立调查列表与详情；先固定 UUID、字段类型、空值及来源。前后端优先明确独立调查列表跨三类 Run 的分页与去重方式；把原有图谱归一化和处理状态列入接口回归。调查执行侧另用本批冻结材料离线回放完整事件诊断和两条分诊如何装入 C3，再用新案验 C6。这个问题不阻塞已有页面字段交接。前端操作写回、H 后的有效第二轮和证据判断策略分开排期。

### 部署小模型与既有案例的对照口径

上文三案由 DeepSeek 生成。追加的 21 内网小模型试验选用 01 的账户清点、报表复制场景。21 上的既有网关提供 `aisoc-investigation`，上游报告 `Qwen3.5-9B`。`n15` 是调查 API 镜像的版本号。本次用它提供运行依赖，挂载本次核过指纹的调查代码。Kafka、Fusion、验证湖和单独的试验数据库均在 21 环境中。新案使用独立主机、账户和来源 ID，按两条告警、一次事件诊断、一轮 Case 调查预留最多 7 次调用。下表是两套结果的比较口径。

| 配对项目 | 已固定的DeepSeek对照 | 下一轮要求 |
| --- | --- | --- |
| 场景 | 本轮01/02/03的plan与expected及hash | 复用相同事件结构、行为字段和预期边界，另建模型专属主机、源ID、Case/Run及映射表 |
| 上下文 | 每轮C1冻结工件、A/I请求及工具返回 | 全部保存；共享operator-0及顺序历史会改变输入，需隔离账号或冻结历史，注明差异。不能声称仅模型不同的逐字对照 |
| A/I/C | 15份实际请求/原答、两个C3拒收原因、3C6 | A/I须由待测模型重新产生；不能复用DeepSeek分析充当前序结果。另做固定请求对照时须单列，不能冒充全链 |
| 预算 | 单C48k保守单位/4模型/4工具/120秒 | 先固定新campaign的允许ID、次数和累计上限；当前旧deployed默认全局50已低于累计63，不能直接照旧命令派发或清零账本 |
| 场景检查 | 原件/关联/GET/page验证脚本与本表F01—F28 | 同步跑同样读回；增加部署模型结果列，失败先分服务/输入/输出/容量/质量，不自动重试 |
| 判据 | 启动≠完成，命令参数≠产物，缺源≠不适用，关系≠因果 | 分开记录良恶反转、待核、证据扩大、范围错误；保原答，不人工补成成功 |

本机数据用例和查询脚本可先交接；H后容量、知识实际消费、语义约束、实时表单、Q执行及部署模型对照继续沿[现有OpenSpec任务](../../openspec/changes/complete-socai2-investigation-chain/tasks.md)推进。任务仍19/26，3.7/3.10/3.12/3.14/3.16/4.1/4.2未核销，不归档完整change。
