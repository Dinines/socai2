# 调查概览与每轮结果：展示字段逐项溯源（2026-11-03）

最新进展（2026-11-04）：[36项逐一新出口、九路径和4例](../investigation/socai2-case-api-20261104.md)、[运行时OpenAPI镜像](socai2-case-api-v1.openapi.json)已提供新表Case、pending/正式历史、Run/Result/报告/当前判断和冻结材料读取。D30最后记录取全部保存时钟、步骤/工件，不受目录截断影响；D32保原答复/对话/输入身份；D36历史与详情复用核心合同，启动返回当前状态。新HTTP默认关闭，页面未接。11新+2回归最新通过，真实独立合成PG、身份/模型/湖替身；下方36项保留旧链审计，不能当新字段仍缺出口。

当前补充：下文是39f4033旧HTTP链与页面演示数据的审计原件。新socai2后台现已由[C6](../investigation/socai2-baseline-delivery-20261103.md)实际生成结论/来源/校验、closing_note、成员覆盖、指定历史比较、Case影响及同版正式报告，并原子保存结果与有条件采用；这些不再只是“可存JSON”。表字段和读取位置见该文第2节及顶部新API明细。页面/生产未切换，当前仍partial，真实模型质量未验；下方旧链缺口不能直接当作新服务仍缺字段。

本轮按用户纠正后的重点核对：页面显示的每句话/标签/数字，是否在当前表中保存、是否由调查真正产出、现有读取接口是否提供。不是继续设计启动流程，也不是把“JSON 可以存”算成“目前已有数据”。页面和后台代码均未修改。

## 1. 核对基线与方法

- 页面/产品：本设计分支 `c71afb5`，重点为调查概览、调查发现、调查历史中的同一轮结果。产品文档第8.4、9.1、12章。本轮未刷新远端。
- 后台：检查点 `39f4033` 加独立 `codex/case-baseline-history-20261103` 工作区的待更新执行记录修改。迁移122尚未应用；下文“新基础调查字段已实现”仅指该本地代码，不表示线上表已具备。
- 核对链：页面显示 → 页面字段/缺省文案 → 写入代码 → 表/列/工件JSON → 实际GET/启动返回。复读已授权保存的r13 A/B结果原件，只看字段形状及用量，没有新Run/模型/数据库查询。
- 浏览器读取接口本轮不可用；依据本地实际加载脚本、渲染函数和数据文件核对，并在Node独立上下文调用原页面 `runOutcome` 做只读观察。没有操作页面或修改浏览器存储。
- `case-outcome-data.js` 中6条演示Run均明确 `fixture=true, recorded=false`；它们完整的outcome字段不能作为生产调查已生成字段的证据。

主要来源编号：

| 编号 | 文件及关键位置 |
| --- | --- |
| P | [页面读取/渲染](../../prototypes/security-pages-v2/investigation-workspace.js)：35–43 runOutcome，178–183状态/用量，247–254详情，307–316概览 |
| F | [完整演示数据](../../prototypes/security-pages-v2/case-outcome-data.js)：23–36，outcome七字段与硬编码状态 |
| W | [页面本地保存AI结果](../../prototypes/security-pages-v2/case-workflow.js)：48–57；不是服务端持久接口 |
| R | [Case调查写入与读取](../../services/api/app/investigation_v2/case_analysis.py)：240–249报告模型，280–332上下文，345–361读取，470–498模型记录，605–689结果写入，699–818启动 |
| H | [Case历史读取](../../services/api/app/investigation_v2/case_history.py) |
| X | [统一执行索引](../../services/api/app/investigation_v2/execution_index.py)：25–60，已有摘要截取与截断标记 |
| V | [步骤/报告读取](../../services/api/app/investigation_v2/case_views.py)、[证据读取](../../services/api/app/investigation_v2/case_evidence.py)、[引用导航](../../services/api/app/investigation_v2/case_navigation.py) |
| S | [多告警结果模型与派生](../../services/api/app/investigation_v2/case_synthesis.py)、[来源冻结](../../services/api/app/investigation_v2/case_source_material.py) |
| B | [新增基础调查字段读取](../../services/api/app/investigation_v2/case_baseline.py)、[迁移122](../../services/api/migrations/122_case_baseline_pending.sql) |
| DB | [Run/Event/Artifact ORM](../../services/api/app/models/investigation.py)、[Case/Task ORM](../../services/api/app/models/case.py) |

## 2. 用户举例的文案究竟来自哪里

| 展示 | 页面实际来源 | 具体结论 |
| --- | --- | --- |
| 基础调查 | `investigationKind === baseline` | 是执行类型。新后端有 `investigation_kind`，需映射；不能由completed或Case归属猜类型 |
| 已完成 | `status === completed` | 是执行状态。后端有 `investigation_runs.status`；不表示结论正确或材料完整 |
| 完整交付 | `completion === completed` | 是页面另一枚标签。当前Case结果只写 `partial/conclusion_available`，存在取值及语义差异 |
| 建立案件的初始分析 | `runOutcome` 在没有purpose/objective且trigger为case_created时生成 | 是触发原因的缺省说明，不是保存的具体调查目标，更不是分析结论 |
| 本轮未保存结论 | 非活跃/非失败/非取消，且缺少 `outcome.conclusion` 时生成 | 是页面空态，不证明数据库没有报告；当前后端摘要在 `result.report.summary` |
| 未记录与此前结果的对比 | 缺少 `outcome.change` 时生成 | 后端确无统一变化叙述字段；已有previous_run_id不等于已有对比结果 |
| 未记录对案件判断的影响 | 缺少 `outcome.impact` 时生成 | 后端确无独立case impact字段；recommendations、summary或Case状态不能直接代替 |

只读观察直接调用现有页面函数：给一个completed、case_created、已有report文本但没有outcome的对象，仍同时得到上述“初始分析／未保存结论／未记录对比／未记录影响”。这是展示合同观察，不是一次真实调查，也不证明当前页面已经接入后端DTO。

## 3. 36项字段明细

缩写：`Run`=`investigation_runs`；`Result`=`investigation_artifacts`中kind=`case_analysis_result`的content JSON；`Step`=kind=`case_analysis_step`工件，关联 `investigation_events`。JSON工件的数据库列是Text，内容是版本化JSON，并非每个字段都有独立数据库列。

接口简称：`详情GET`=`GET /api/v2/investigation/cases/{case_id}/investigations/{run_id}`；`历史GET`为同路径去掉run_id；`索引GET`=`GET /api/v2/investigation/executions?case_id=...`。本表“已存”指写入路径真实存在，不声称所有历史行都非空。

| ID | 页面字段/语义 | 当前保存的准确位置 | 当前出口与确认结果 | 额外工作/禁止混用 |
| --- | --- | --- | --- | --- |
| D01 | 本轮ID、所属Case | Run.id/tenant_id/case_id，raw_alert.analysis_profile | 详情/历史/索引均有；当前Case路径能定位同案结果 | 沿现profile与租户读取；历史其他profile的case_id不强当本案UUID |
| D02 | 调查标题 | 当前写Run.alert_summary=Case标题；未保存独立本轮标题 | 详情/历史没有独立调查title；原型title由演示数据赋值 | 可用明确类型+触发原因生成标签；若要“新增跳板机活动”等具体标题，须真正生成/保存，不拿Case标题冒充 |
| D03 | 基础调查/AI调查类型 | 新Run.investigation_kind=baseline；旧行可空 | B、详情/历史/索引有；启动执行结束的POST返回尚未统一带kind | 映射snake_case；AI明确保存对象尚未实现，不能用profile=case_analysis.v1区分三类业务 |
| D04 | 首次/范围变化/用户提问原因 | 新Run.raw_alert.baseline.trigger=case_created/members_changed | 新基础记录详情/历史可读；旧Run未知；普通调查请求不写这套trigger | 触发原因不等于“之前已成功分析过”；members_changed不能单独证明存在可比较的已完成轮次 |
| D05 | 本轮具体调查目标 | Run.raw_alert.intent.request.question；启动Step上下文question | 已写；详情GET/历史GET及Result没有专门投影question；Step详情能读 | 补目标读取映射即可；不能用Case.description代替用户这一次的问题 |
| D06 | “建立案件的初始分析” | 没有这个结论字段；P38按trigger生成固定句子 | 可派生为原因标签，不能列作已有分析产出 | 展示应与D05具体目标、D09结论区分；没有触发信息不靠第几条猜 |
| D07 | 已完成/失败/执行中 | Run.status、error；Result.stop_reason | 状态已有；新的pending_update/awaiting_human未进入页面现activeStatuses集合 | 后续页面明确待更新不进入“已有结论”；完成、交付、结论可信度三者分开 |
| D08 | 完整交付/部分交付 | Result.completion；R672以report.gaps是否为空写partial或conclusion_available | 历史/索引有completion，详情嵌套result；不输出页面的completed完整交付枚举 | 既有字段有值但语义未完全对齐；“结论可用/无gaps”不能直接证明全部材料完整交付，不机械改枚举名 |
| D09 | 本轮结论/卡片主标题 | Result.report.summary | 详情有；索引已有最多800字符summary及summary_truncated；历史GET不读摘要 | 映射至outcome.conclusion或统一DTO；不能把页面空态当DB无摘要；长结论保截断提示 |
| D10 | 实质结论与系统收尾说明 | R606–609在无有效模型结论时写固定summary；stop_reason/gaps同时保留 | 两者共用summary，缺显式conclusion_state/origin；非空不证明是模型有效结论 | 最小补结论状态/来源，区分accepted、fallback、missing；旧数据不得仅凭非空标“形成结论” |
| D11 | 主要发现 | Result.report.findings[].text/evidence_ids | 详情有，历史/索引无完整发现数组；P读outcome.findings或run.findings | 读取映射，保留证据ID；模型文本是否可靠属于另一个验收问题 |
| D12 | 支持依据 | findings[].evidence_ids、Result.evidence，成员判断/关系各自evidence_ids | 已有稳定同Run证据与导航；无单独outcome.basis字符串数组 | 可从真实引用生成简短依据+链接；不能脱离引用新编“支持理由” |
| D13 | 反证 | Result.report.counterevidence[] | 已存且详情返回；原型outcome七字段没有单列counterevidence | 展示合同要保留该语义，不混进一般限制或“无告警”结论 |
| D14 | 与哪一轮比较 | Run.raw_alert.previous_run_id；可有H1 prior_analysis证据 | 明确追问入口有；且R要求成员与时间窗口一致。新范围baseline不自动设置previous_run_id | 缺“本次成员更新对比哪轮”的稳定引用；已有follow-up引用不能冒充全案比较基线 |
| D15 | 新增/移除的输入范围 | 新Run.raw_alert.baseline.initial_member_ids/added_member_ids/removed_member_ids及scope_revision | 新基础记录已写/可读；旧历史无该字段 | 可派生成员变化说明；这是输入差集，不证明证据或判断发生什么变化 |
| D16 | 相比已有结果的变化 | 当前AnalysisConclusion禁止额外字段，未定义comparison/changes/change | 确认缺：写入模型、结果工件和读取均无统一变化叙述 | 增加版本化结果结构：比较对象、范围、输入/证据/判断变化与引用；无比较基线时明确not_compared |
| D17 | 对案件判断的影响 | 当前无case_impact/impact字段 | 确认缺：不能由recommendations、Case.status或净新增数量直接得出 | 增加有依据的影响说明、适用范围与限制；保存在本轮结果，不自动改案件当前判断 |
| D18 | 限制/仍待确认 | Result.report.gaps/open_questions；Result.stop_reason；query_sources/query结果截断状态 | 已有，详情可读；页面期望outcome.limitations/run.stop/depth.unavailable_data | 合并为展示投影时保留性质：失败、未知、截断、待补材料，不能全译成“未记录” |
| D19 | 后续建议 | Result.report.recommendations[]；open_questions[].suggested_action | 当前字符串建议已有；详情返回，未映射原型actions | 可显示文字建议；不是已执行动作，也没有因此获得稳定审批/执行关联 |
| D20 | 本轮输入数、实际读取数、当前成员数 | Run.raw_alert.scope与Result.scope的all/selected/read_member_ids；当前Case.alert_ids | 各数据已有；历史/详情有scope | 页面本轮输入应取selected，实际覆盖看read及member_coverage；不能把当前Case数量覆盖历史输入 |
| D21 | 当时输入原文、窗口、对象 | 启动Step的context及source_material；Result.case_material/evidence；scope.start/end | 已保存且有步骤/证据出口，含明确截断/输入guard边界 | 映射至run.input；不是保证全部raw无限全文，更不能回读当前告警替换历史材料 |
| D22 | 逐告警判断与关联 | Result.report.member_assessments/relationships/member_coverage | 已存且详情返回；与S模型一致 | 保留supporting/background/undetermined等原语义；不直接当Case最终定性 |
| D23 | 记录创建/开始/结束/范围更新时间 | Run.created_at/started_at/completed_at/scope_updated_at | 新详情GET/历史/索引有对应字段；POST结束返回与GET时间字段尚未统一 | 映射requested_at、started、ended；待更新started_at为空，不能用创建时间冒充执行开始 |
| D24 | 本轮总耗时 | started_at、completed_at | 可派生；P按结束-开始且非活跃计算 | 无结束/时间非法保未知，不用最后一条Tool耗时替代整轮 |
| D25 | 模型调用数 | Run.iterations；Result.usage.model_calls；准备/返回Step | 有，但iterations在调用前递增，表示尝试轮数，不是成功返回次数 | 区分尝试/返回口径；不能统计两种Step行数当调用数；历史默认0不证明零调用 |
| D26 | Tokens/未记录 | Run.total_tokens；Result.usage.known_tokens/unknown_usage；每次模型返回Step.usage | 有已知累计及逐次记录；R474/479在后次调用前后重置unknown_usage，早期缺usage标记可被后次正常调用覆盖 | 读取应保“已知值/总量是否完整”；需修累计未知标记或从逐次记录重建，不能仅按总数或最终false宣称完整；本轮只登记 |
| D27 | 工具记录数量 | Result.evidence中kind=tool的已保存条目；工具Step；usage.tool_calls | 记录、实际调用、历史复用三种数据已有，但不是同一计数；P显示tools.length | 按已保存工具材料构建tools数组；不直接拿调用数冒充记录数，不重复算请求/返回Step |
| D28 | 费用/未定价 | Run.total_cost_usd、measured_call_count、estimated_cost_usd、estimated_call_count、unpriced_call_count（063） | 列和原账本读取已存在；本Case详情/历史/索引未投影完整费用 | 补读取并标实测/估算/未定价；默认0不可当免费；用量缺失不补造金额 |
| D29 | 保存材料数量与原件 | investigation_artifacts.id/kind/event_id/content/blob_ref/sha256/size_bytes | 表已有；步骤/证据可读，原账本有工件接口；Case概览未给统一材料目录/计数 | 指定同Run、同租户、材料种类及去重口径，不能把空数组误称数据库0材料 |
| D30 | 已开展工作/最后记录时间 | investigation_events.seq/kind/summary/ts + Step正文 | progress简表无ts；steps GET有recorded_at，步骤详情有data | 最后记录取已存事件ts；不拿页面刷新或Run更新时间补齐；步骤标题可按已存kind/phase映射 |
| D31 | 报告正文/下载 | Result.markdown；kind=case_analysis_markdown工件 | saved_report读取已有，详情有report_url | 可直接接；报告有正文不等于outcome已映射，不从Markdown标题反推所有结构字段 |
| D32 | AI明确保存结果的保存人/时间/对话 | 原型W将savedAt/savedBy/conversation/referenceSnapshot存本地对象 | 当前后台无等价正式保存记录合同；通用Copilot消息不是已经保存到Case的结果 | 沿之前正式保存对象方案补数据身份与快照；不伪造基础Run和调用量 |
| D33 | 人工确认进入本轮依据 | 原型示例直接给task结果和outcome；当前case_context只读Case/Alert/分诊/明确前次结果 | 确认本轮上下文没有读取CaseTask的完成结果/当时版本；示例“脚本用途已人工确认”不是后端已有事实 | 先补人工结果字段及当时引用快照、再让结果引用；不能从任务标题/负责人推断确认内容 |
| D34 | 本轮影响是否已成为Case当前判断 | Case.summary/resolution等旧字段不包含明确的本轮采用/确认范围关系 | 无同原型assessment的统一确认人、来源Run、任务、覆盖成员合同 | 本轮impact是分析意见；当前判断需独立明确采用记录，不能保存报告就自动变更 |
| D35 | 待更新范围及其版本 | 新baseline JSON、Run.scope_revision/scope_updated_at、pending_update | 本地新后台有；原型还读Case.baselineUpdate，并未消费新Run字段 | 页面差异已交接；不在本轮改页面，不自动调度，不能将待更新计为已有分析结论 |
| D36 | 同一数据的读取一致性 | 详情、历史、索引、启动POST现有不同投影 | 明确：历史无summary/目标/发现/用量；索引有截断summary但无完整outcome；详情有Result但无单独question；POST结束缺B元数据/时间 | 后续提供统一结果摘要投影，复用原工件；不因某一个接口没字段就建冗余结果主表 |

## 4. 已保存返回记录的直接核对

使用后端工作区 `docs/operations/evidence/investigation-r13-20261101/{A,B}/003-result.response.txt`，未改原件、未重跑：

| 已保存样本 | 执行/交付 | 摘要和发现 | 比较/影响 | 用量 |
| --- | --- | --- | --- | --- |
| A | failed / partial | summary非空、findings=0；这是程序生成的未形成完整结论收尾，不能当有效模型结论 | 两者都无字段 | model_calls=3、tool_calls=2、known_tokens=10647、unknown_usage=false |
| B | completed / partial | summary非空、findings=4 | 两者都无字段 | model_calls=3、tool_calls=2、known_tokens=9687、unknown_usage=false |

两份report实际键包括summary/findings/counterevidence/gaps/recommendations/member_assessments/relationships/open_questions/member_coverage/timeline/query_sources，没有purpose、comparison、change、case_impact。目标在请求/Run意图里，不在这两份结果中。它们均为旧r13原件，没有后来新增的baseline类型/范围版本字段。

**这证明的是已保存字段存在/缺失，不是报告内容验收。** r13 A/B的旧语义问题与质量不通过结论保持，B执行completed不意味着其内容正确。也不能用这两份旧记录证明迁移122已执行或所有历史行的字段状况。

## 5. 最小补齐方向：复用现表，区分生产与读取

1. **先补已有字段的读取合同。** summary、findings与引用、question、scope、limits、时间、用量、报告链接均沿现Run/Event/Artifact读取。概览/故事/详情共用同一含义；统一索引已有summary，不能重新判成所有摘要出口都缺。
2. **确实新增结果内容。** 为Result定义新版本，补对比对象/变化与case_impact、结论来源/有效性。相应模型输出schema、输入上下文、写入、引用验证和读取要一起补；只在DTO或JSON里加空键没有实际意义。已有 `AnalysisConclusion(extra=forbid)` 不接受这些新键，不能让模型“自行多写几项”。
3. **基础记录元数据映射已有新增字段。** kind/trigger/成员差集/版本/时间来自迁移122对应写入。首次/更新所比较的历史基线仍缺，不通过给旧行猜类型来补齐。
4. **交付枚举先定真实判定规则。** 执行状态、有效结论、材料交付完整性分别表达。未决业务问题不必然等于技术材料缺件，缺件也不能因status=completed而变完整。保留原completion原值，后续实施明确映射/新增字段，不能简单把conclusion_available换成completed。
5. **修累计未知用量与缺失表示。** 明确0、未知、部分已知三种值；保留逐次模型usage。此为字段语义问题，本轮只登记，不扩到报告质量修复。
6. **人工与AI正式保存是独立缺口。** 先有结果/确认范围/引用快照，才能合法产生样例中的“人工确认改变了判断”；不得用完整演示对象代替真实数据合同。

上述本轮结果内容可以保存在现 `case_analysis_result` JSON工件中，**无需为summary、对比、影响各建一张表或给Run复制一套报告列**。JSON能承载与代码已产出是两回事。正式AI保存对象、人工结果、Case当前判断关系则沿已有专项计划单独实施，不能宣称本次Run元数据修复已经解决。

本轮只新增明细、入口记录与静态/只读观察回执；无页面、业务代码、DDL、数据库写入、模型/Tool/新Run、提交/推送或部署。手动启动决定保持；报告修复继续暂停。来源指纹及观察输出见 [核对回执](../operations/investigation-result-field-audit-20261103.json)。
