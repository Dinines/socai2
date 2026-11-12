# 独立结束审计

## 结论与范围

2026-11-12，未参与本 change 实现的独立审查者，基线 `V1.1@4d46f4d46a2b65539bf17bb200fa6ba85a28c7a4` 加本工作树增量。

**本地功能范围 ACCEPT，可进入既定的一次统一发布；模型质量仍为 NOT_PASSED。** 未发现历史卡片入库、检索范围、冻结来源身份、保存或读取的剩余功能阻断。该结论不表示已经发布 21、模型已合理采用历史知识，或当前 change 已完成最终归档/Git 交付。

只审查本 change 的 proposal/design/specs/tasks/validation、相关源码差异、配置和本批保存证据；没有重新审查已归档 change，没有调用数据库、模型、嵌入、网络、浏览器或部署，没有操作 Git。除本审计文件外未修改文件。复用现有 12 项直接检查 XML；本次额外执行的只是本机 JSON/hash/HTML 原值比较，没有重跑这些测试或扩大回归。

## 功能与合同核对

- [knowledge_history.py](../../../../services/api/app/socai2/knowledge_history.py) 的源查询同时限制租户、告警与原材料/判断身份；卡片保留材料版本、原判断/人工字段和材料对应状态，未生成新的结论。第 100–132 行的显式入库与索引分开，稳定 ID 包含租户和内容摘要，索引要求卡片与实际源内容一致。材料链接对应现有 `socai2_pages.py` 第 69 行读取路由。
- [knowledge_config.py](../../../../services/api/app/socai2/knowledge_config.py) 第 125–132 行、[knowledge_vectors.py](../../../../services/api/app/socai2/knowledge_vectors.py) 和卡片回读的 `in_scope` 一致使用历史事件下限/排他上限、同租户和全部当前成员排除；缺 Case 时间边界不生成历史目的。原 SQL `history` 路径未替换为知识检索，技术解释/取证指导不套用历史时间过滤。
- [case_source_scope.py](../../../../services/api/app/socai2/case_source_scope.py)、`baseline_enrichment.py`、`baseline_model_view.py`、`incident_model_boundary.py` 保留历史记录主体，查询成员仅为检索出处。卡片整体是 `source_label`，原分诊是 `prior_analysis`，人工原文是 `human_statement`；序列化重复正文从模型视图移除，数据库原件保留。没有把历史行提升为本案 observation 或授权，没有增加 Deep 动态检索或新工具权限。
- 调查表、告警 DTO/返回路径及原始材料合同未改。新数据使用既有 KB 文档与 C2 回执字段；版本状态是与当前源指针的比较，不是对历史判断正确性或所有可变源字段的新认证。
- 发布配置将 API/按需处理 profile 与工作台挂载指向 `v1.2-20261112-r1`，复用已有来源连接、集合和继承服务；本地审计时仍是候选准备阶段。实际镜像/manifest、加载配置、容器保持和发布后读取须由本轮发布回执确认，不由此处预报成功。

## 已保存证据的独立核对

证据根为 [historical-knowledge-20261112-01](../../../../docs/operations/evidence/historical-knowledge-20261112-01/)，直接流程见 [local-flow/export/verification.json](../../../../docs/operations/evidence/historical-knowledge-20261112-01/local-flow/export/verification.json)。本审计用 `.local/conda-envs/socai2/bin/python` 和标准库读取原文件，得到以下结果：

| 核对对象 | 独立核对结果 |
| --- | --- |
| 保存导出 | manifest 的 3 个文件 SHA-256 与现文件一致；Case `20bff447-7e9e-5cd0-8081-9c348f3cf8c3`、Run `306f930e-7788-479f-9109-ee62b45eccb1` 对应 |
| 历史卡片 | 两份实际 GET 卡片相同；重新计算稳定 UUID 得到 `91f7daf1-fb43-5812-aea9-1300fa94eb0d`；原分诊/人工字段与明确的 fixture 相符，选取的原观察值保持 |
| C2 范围与行 | 3 目的各 3 查询；历史的 3 个过滤均排除完整本案成员集合，区间为 Case 开始前 90 天至开始时刻之前。2 条历史命中均回到同一卡片，序列化原件与拆分的 history/triage/feedback 对应，不能计为 2 个独立历史案例 |
| 实际请求与原答 | 5 份数据库请求 body 与 call intent 逐值相同，5 份原答 raw 与传输回执逐值相同；每份请求 6 个历史来源，角色各 2 个，`alert_ids=[]`、`record_alert_ids` 为历史告警。两段原 rationale 均进入实际正文；reported tokens 合计 98,629，未把未知费用记零 |
| 引用边界 | 5 份原答的四类结构化引用数组均无历史引用。Deep seq16 正文含 `N3_S96/N3_S103`，C6 正文含 `N4_S96/N4_S103`；正文提及与结构化引用不能混为一谈，也不能据此认定合理采用 |
| 保存/GET | Result 的 `id/source_run_id/delivery_state/validation_state/conclusion_state/conclusion` 六字段与实际 GET 一致；`partial/rejected`、`conclusion=null`，Case `current_assessment_id=null` |
| 原件与页面 | 3 份本案材料与冻结 plan 的全部材料字段一致；新 Case HTML 的 49 个工件 JSON 与导出数据库逐值一致。复读已有 local-ui-check.json，不另做浏览器验收 |
| 实现冻结 | plan 的 103 个源码/配置文件 hash 均一致；额外冻结 4 项中只有验收 driver 修改，其前后 hash 与 `driver-correction.json` 精确对应，其他 3 项一致。该修改为保存回执方式修正，不是模型或业务实现变更 |
| 既有直接检查 | direct-checks.xml 为 12 tests、0 failure、0 error；只读取结果及相关直接用例，不重新执行 |

C3 首次 `source_member_mismatch` 原失败保留，第二次纠正后接受；两次 Deep 为 handoff/unresolved。C6 只有一次请求，错误为 `recommendation_needs_sources`，并非前批 `duplicate_source`；不能把执行 completed 当作结论接受。卡片来源是明确构造的本地历史演练 fixture，不能冒称真实业务授权或独立真值。重复入库后的验收 driver 排他写失败与前置 fixture 对象约束失败均保留，不混入业务/模型成功计数。

## 本次审计发现及收口

发现一处展示与摘要用词不够精确：原 `processing_audit_inspector.py` 第 210 行仅统计四类结构化数组，却显示“未见引用”；实际 Deep/C6 正文确实提及历史来源别名。最小修正是限定为“未见结构化引用”，说明统计 `source_ids/evidence_ids/support_ids/counter_ids`，不新增自由正文引用识别器或模型调用。

实施者已修正第 210/217 行及 validation、PROGRESS、问题清单、执行账本和历史交接，本审计已复读确认。随后已重新生成静态页面：当前 index 与 static-manifest 同时指向 `cases/34041b7953e2ce57aaf5d22d8402c9e4488cd38703c0c4514e430b1cf3ab5ece.html`；独立核对新页面包含限定文字和正文提示，49 份工件仍与数据库逐值相同，旧 `000571...` 页面保留。该问题已消除，没有改写原答，也没有重新运行模型。

没有其余本地发布阻断。M01-A/M01-B/M02、F01/F02 仍按负责人决定后置，召回相关性、正确比较历史条件及实际调查质量未通过；登录主题也命中进程卡的事实保留。本审计不验收自动入库/消费、A/I 新历史检索、Deep 动态检索、产品页面或真实处置，不核销主调查 31/41 的未完任务。发布后在同一审计追加实际交付核对，再按真实完成情况归档和同步 Git/父项目。

## 发布补审

2026-11-12，[独立发布补审](release-audit.md)已完成，限定 ACCEPT。21 `v1.2-20261112-r1`、3 次知识业务 HTTP、一次只读历史检索、实际来源/配置及静态记录读回成立；四项继承容器保持，临时 key 撤销并核 401。模型质量仍为 NOT_PASSED。归档及最终 Git/父项目同步不由发布补审预报。

## 归档与封后校验

2026-11-12，7/7 归档前任务具有对应证据后，执行 `openspec archive use-historical-alert-knowledge --yes`，同步三项能力并归档到本目录。归档首次全量结构校验指出 CLI 新建主规格的 Purpose 占位说明，已补为实际已交付用途；未改变需求或扩大验收。

最终 `openspec validate --all --strict --no-interactive` 为 19/19，`--archived` 为 13/13，`git diff --check` 通过。已修正迁移后的交接/证据链接；没有重跑业务、模型或可用性测试。Git 统一推送与父项目 server 引用的最终 hash 由交付时远端读回记录，避免在本提交中自引用尚未产生的 hash；父项目使用独立普通检出，保留用户已有分叉工作树。
