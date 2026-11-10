# Case Finding 来源角色验收

2026-11-10。本 change 处理 C3/C6 生成与接收的角色约束、一次纠正反馈之间的缺口。本地直接验收、独立结束审计、统一发布与生产读回已完成。模型整体质量仍为 **NOT_PASSED**，不能将结构接收或当前判断采用解释为质量通过。

## 原问题与修正

前批 `real-model-03` 的 C3 seq 11、C6 seq 19/20 都有把行为与 synthetic 来源说明混在同一个 observed Finding 的原答。三条 Finding 均能通过当时的 Finding 生成 Schema，接收端却拒绝非 observation 支持；反馈遗漏这个角色错误。完整答复中 seq 20 还存在重复 conflict finding_ids，不能称三份完整答复都通过原生成合同。[原始回放](../../../../docs/operations/evidence/case-evidence-roles-20261110-01/baseline-replay.json)

生成器共用 `case_finding_schema.py`：observed 支持限定有本案成员归属、非 query_binding_only 的直接观察，inferred 至少有一项支持，unresolved 至少有一项限制；每个分支保留完整必填项与长度限制。没有可用观察时不提供 observed 分支。生成约束不能替代逐成员范围和正文检查。原接收端保持兼容，包括合法观察加 C1 event_time 上下文；材料、来源原文和历史工件不改。

`socai2.case-citation-correction.v2` 在原有一次纠正中补角色、直接观察覆盖、查询绑定及支持反证重叠诊断，给出路径、来源角色和可用观察编号。配置要求模型重新核正文、状态、范围及引用，必要时拆分行为与带来源的说明；程序不删引用、不换状态、不改正文来使其通过。unknown、截断、预算及最终阶段预留沿用原限制。

三份原答离线回放均被生成约束排除混合角色的 Finding，原接收拒收保持，反馈增加准确角色位置；原文件 hash 不变，0 模型调用。[修正后回放](../../../../docs/operations/evidence/case-evidence-roles-20261110-01/candidate-replay.json)

## 直接检查与完整 PostgreSQL 流程

17 项角色专项检查和原有相关检查合计 **86 项通过**；Ruff 通过。覆盖三种状态、各非观察角色、没有来源、仅查询绑定、成员覆盖、支持反证重叠、合法时间上下文、原答回放、unknown/截断/预算及局部保留。[测试回执](../../../../docs/operations/evidence/case-evidence-roles-20261110-01/contract-tests-01.xml)

本机 `v12_upgrade_dev` 用独立批次执行 A/I 材料准备及 C1→C2→C3→Deep→C5→C6，两项完整场景通过：

- 角色用错后一次纠正成功，C3/C6 正常保存并采用最终判断。
- 纠正仍错时不再调用，保留有效局部，拒绝无效最终结论。

每案 6 次 Case 模型替身调用，真实模型 0 次；Deep 两次、数据湖一次均为替身。6 项服务层读取通过，原描述、身份业务值和 `0/false` 保持，数据库结构前后仍为 **29 表、462 列**。[PG 结果](../../../../docs/operations/evidence/case-evidence-roles-20261110-01/local-pg-02/summary.json)

`local-pg-01` 的两项断言失败原件保留：测试注入器选中了接收合同允许的 C1 时间上下文，实际没有产生预期角色错误，所以调用数断言不成立。仅将注入器改为非时间的 source_label 后用新批次 `local-pg-02` 验证；没有放宽业务接收合同，也没有覆盖原记录。

## 独立真实模型 Run

冻结最终业务源码、配置及原材料后，使用已有 C02 演练材料的新本地身份，正常执行一个独立 Run。没有复制前序 A/I 判断或伪造新工具回执。数据库是真实本机 PostgreSQL，模型经现有 21 网关；未接 ClickHouse 或厂商服务。assets/knowledge 实际完成零行，其他查询按实际跳过／未接入保存，不能称非空知识使用成功。

Case `349ddca1-f064-5659-9b82-663fadf24e56`，Run `98dda2b8-5346-47d0-bbf0-d17857866cd6`。4 次模型调用，**38,844 reported tokens**，费用未知，未触发纠正。4 份实际 wire Schema 校验及保存校验通过；C3/C6 共 **6 条 observed Finding** 的支持均为有相应成员依据的 observation，现有接收器回放通过。实际最终状态 **completed/partial**，C6 采用；执行初始响应 `execution.json.outcome.state=running` 只是启动时回执，终态读取数据库快照。

保存 47 工件、19 步骤、1 Result、1 当前判断及 3 个成员；原 GET 处理函数 **52 次读取、3,225 项字段／原文／关联核对通过**，读取前后数据库不变。这是本地实测，不是新生产调查，不是受控 A/B，也不报告准确率。[逐调用汇总](../../../../docs/operations/evidence/case-evidence-roles-20261110-01/execution-summary.json) · [字段读回](../../../../docs/operations/evidence/case-evidence-roles-20261110-01/real-model-01/export/field-summary.json)

## 正文质量与下一范围

以下按[原数据库工件](../../../../docs/operations/evidence/case-evidence-roles-20261110-01/real-model-01/export/database.json)的步骤与字段定位，保留原答。引用角色正确不保证正文正确。

| 位置 | 观察与结论 |
| --- | --- |
| C3 seq 11 / findings F1、C6 seq 19 / analysis.findings F1 | 写“执行了 PowerShell 命令”，同时限制明确无法确认执行结果；下一步需统一到日志实际证明的进程启动和命令行层次，不能报已取得命令输出或读取效果 |
| C3 seq 11 / findings F2 | “成功登录”引用 N1_S38（action）、N1_S39（outcome）和 N1_S41（src_ip），已有成功状态依据；“建立了会话”及“外部”定语仍需逐项对照材料，不能仅凭合法角色扩大行为描述 |
| Deep seq 13 / answer | 授权问题保留 unresolved，明确“未提供审批记录不等于不存在审批”；这是正确边界，不应把本轮所有答复笼统判为相同错误 |
| Deep seq 15 / answer.text | 将缺少演练计划／配置／审批列为“支持非演练（恶意/误操作）”，把缺口当反证；将验收 Case 的“独立本地调查”描述推断为原行为非生产环境，混淆执行场景与业务事实 |
| Deep seq 15 / reason | “若 synthetic 标签可信，则行为为演练”仍把来源标签提升为业务判断，缺独立核实；unresolved 状态没有消除正文依据问题 |
| C6 seq 19 / conclusion.limitations | “工具查询查空”合并了实际查空、跳过和未接入，应按具体来源状态说明 |
| C6 seq 19 / impact.summary | 条件性列举数据泄露／配置变更，缺本案对应内容／变更观察；这是缺乏个案依据的外推，并非已经断言实际发生损害。supported_changes 为空，cannot_generalize 仍明确连接成功不等于外传、命令执行不等于配置变更 |

本 change 收口的是生成和反馈的可定位合同缺口。M01 正文依据、M02 持续质量观察、真实非空知识与 H 正确使用仍保留；主调查 3.7/3.10/3.23/3.30 等不因此勾选。下一独立范围先处理上述正文主张与缺口／反证的区分，再验证非空知识和 H 使用；产品 HTTP/页面操作、自动消费分别推进。

## 交接与发布

告警 API 字段、HTTP 返回、数据库设计、当前策略预算均未改变；内部请求的来源表与响应中的原答／反馈／校验继续沿 `artifacts.content_json` 查询。4177 已追加两份 PG 替身和一份真实模型材料，共 29 份；233 文件／234 HTTP 验证通过，原记录保持。独审 ACCEPT 后统一发布 21 r6，一次 API 更新，五项继承服务容器未变；365 GET／16,820 字段关联检查通过，8 次预期错误归属 404 单列，生产数据与前批快照及读取前后保持一致。

发布后首个容器核验探针误假设写开关必须显式存在于 Env；已有配置中未设置该变量，由应用默认关闭。该探针断言失败未改服务，随后读取应用实际 settings 确认 Case 写 false、页面／分析读取 true，原失败单列 `runtime-probe-initial.json`。

实际来源、读回与容器身份见[交付回执](../../../../docs/operations/evidence/case-evidence-roles-20261110-01/delivery-summary.json)，具体审计和归档见 [audit.md](audit.md)。
