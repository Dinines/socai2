# 调查模块当前审阅指南

**当前工作优先级：** 用户要求保留以下r13问题、暂缓报告修复；[页面需求与完整实现对照](field-alignment-confirmations-20261101.md)的六段本地核对现已完成，见[报告影响与修复顺序](field-alignment-impact-and-repair-plan-20261101.md)。范围从Fusion收到输入开始，上游输入问题排除；调查页面设计比对不纳入，调查后端纳入。下一建议先修事件ID/湖列绑定，再按具体功能补字段及管理链；本轮没有实施。报告质量及5.3仍未通过，不阻断字段对齐，下方历史修复顺序不代表恢复报告开发或重跑r13。

2026-11-01。**r13已部署，报告验收未通过。** A因持续空白输出而截断；B虽completed/partial，仍有空查询反证化、审批语义及Tool标注偏差。C前提未满足而跳过。见[真实回执](../operations/investigation-r13-report-validation-20261101.json)与[原因分析](../operations/evidence/investigation-r13-20261101/review.md)。r12及更早批次原件保留，不重复本批。

来源值、具体协议误拒及一次纠错聚合等[窄修复](report-grounding-fix-20261101.md)已随r13部署。17个不同直接方法最新通过，含6新增，本批复用，未重跑业务测试。它们不构成通用语义保证；本批没有触发真实纠错，不能将该路径或追加质量标记已验。继续沿[后续计划](../../openspec/changes/fix-investigation-audit-gaps/report-followup-plan-20261101.md)处理具体报告缺陷，P3/5.3待办，不新增Case记忆层。

## 审阅基线

| 项目 | 固定值 |
| --- | --- |
| 最近部署 | `20261101-r13`；镜像 `7ca057227526…` |
| 部署代码 | 独立API实际473应用源码与477文件候选一致；[安装核验](../operations/evidence/investigation-r13-20261101/post-install.json) |
| 源码身份 | `b758351`未提交工作区快照，以包/清单hash固定；不能把HEAD当全部修复 |
| Run | A `ba9eb0ff-b7b2-52ff-8d4f-5b99140893f1`；B `f582e350-1a30-58c4-9163-5f00617e33f7` |
| 结果 | A failed/partial，B completed/partial但语义未过；6模型、4真实查询、0复用、20,334tokens；6调用未定价 |
| 数据边界 | 沿既有r11/r10 Case及成员/窗口；无新告警/Case/湖事件，旧响应和r12报告保持；C未派发 |
| 当前完成度 | OpenSpec16/17，5.3未完成；程序completed不等于报告内容验收通过 |

真实调用指数据库、API、模型和Tool实际执行；样本行为不是生产端点采集或攻击检测验收。原raw在各3次模型请求均完整，本次不是输入丢失造成的报告偏差。

## 当前问题登记

| 编号 | 问题与当前证据 | 状态 / 后续审阅判据 |
| --- | --- | --- |
| R11-01 | r12源字段未声明/联合不确定句式误拒已窄修并部署 | 直接用例通过；r13 A截断先于校验，B未输出相应协议句式，完整真实效果未验 |
| R11-02 | 反馈隔离与已知内部码/占位拦截已部署 | r13未触发纠错；B未见原占位乱码，不代表任意输出质量通过 |
| R11-03 | r13 A残稿仍把Tool与原文合称确认PID，并引入无源Confluence；B将未提供审批写成无审批 | 来源值存在不证明Tool独立确认；材料未提供不等于事实不存在。整体未通过 |
| R11-04 | r13 B共同背景及原文PID关系引用A1/A2，但又将空Tool结果写为削弱关联 | 同源原文关联、独立印证与反证分开，不能由无结果降低已给来源的可信度 |
| R10-01 | r13 B查询成功0行；程序来源段正确，模型段引出误报/数据残留 | 仍未通过。保持原因未知，空结果不构成矛盾或反证；待核问题不一律禁用 |
| R12-01 | r13 B两成员覆盖和引用有效，来源引用聚合已部署 | 本批没有真实纠错，不能据直接用例宣称真实多错误反馈有效 |
| R13-01 | A报告3,000输出tokens中出现6,490尾随空白，JSON未闭合，length分支直接停止 | 评估纳入原一次纠错，保持预算；不拼接残稿、加上限或重跑选结果 |
| R13-02 | B缺口写process_activity/E2，实际E1进程、E2网络 | 工具名称与证据编号必须一致；程序来源段正确不能掩盖模型段错误 |

A残稿未发布为有效结论，两成员not_assessed；B模型文本已经保存，两成员unresolved，内容偏差如实保留。见[A原答](../operations/evidence/investigation-r13-20261101/A-model-report-step-11.txt)、[B原答](../operations/evidence/investigation-r13-20261101/B-model-report-step-11.txt)与[B实际报告](../operations/evidence/investigation-r13-20261101/B/004-report.response.txt)。

## 已部署上下文修复与记忆取舍

沿用Case/Run已有账本，不新增独立Case文档、向量库或摘要模型。当前失败不是原文未送达；单独记忆层不能补出不存在的审批、脚本或协议证据，也不能自动纠正关系推断。

- 模型视图保留 `Case.description`、`Alert.description`、`Alert.raw_event` 的 `source_path`，分开来源陈述、Tool记录和既有判断。
- H保留原报告摘要/发现/反证/缺口；另外按未决问题→未决成员→假设关系的顺序选择完整条目，累计序列化条目上限2048字节。超限、非当前成员或已给出判断的条目计入 `omitted_report_items`；这不是整份历史上下文的字节上限。
- 保留条目的成员UUID、原Run证据编号、缺口及下一步不改写。仅去掉与保留条目逐字相同的程序生成缺口文字；完整旧报告和旧原文仍留账本。
- 纠错反馈与证据分开；完整内部诊断保留在原步骤工件。已拒原答不回灌，最多纠错一次。

以下上下文验证属于r12之前的历史阶段。最新来源值等17方法及指纹见[修复回执](../operations/investigation-report-grounding-20261101.json)。

首轮14个受影响直接方法的最新结果通过，其中3个新增；首次失败及后续必要复核分别保留，未全量重跑。原网络纠错输入预算估算12252≤12296，Office追加16752≤17018；总预算、查询/模型次数上限保持。验证使用ASGI/模型HTTP/库替身和历史原件，只证明实现行为与预算，不证明新提示词的真实业务质量。

用户要求补充评估后，本轮实际执行22个不同直接方法（4新增，含25个句式/协议/控制文本子场景），最新结果均通过；其中5项与首轮重复，用于复核本轮修复，不能将两批计数直接相加。发现并修复了三处漏放：

| 反例 | 修正后的行为 |
| --- | --- |
| `不能不确认 HTTPS` / `不得不确认 TLS` 被当成未确认 | 无支持记录时拒绝这些双重否定；明确不确定表述继续允许 |
| 只有TLS 1.2或无版本TLS，却断言TLS 1.3 | 特定版本必须来自返回记录；TLS 1.2可支持不指定版本的TLS，`TLSv1.2`视作同一版本 |
| `触发unobserved_application_protocol_use_gaps错误` 未命中Unicode词边界 | 已知内部码按ASCII标识符边界识别，紧贴中文也拒绝；正常业务规则/补证说明不受该匹配影响 |

新增r11完整四轮响应离线回放沿用原两Tool结果和12728已知tokens，四次请求保持原始raw且在原预算内；两份坏报告仍拒收，失败报告不含“文档服务器”推测。该计数是历史usage回放，新增真实模型调用和新Run均为0。另外验证超长历史问题不被截成残句、仅删除与保留条目精确重复的缺口、连续两次压缩不改H引用和材料；多成员、不可读成员、来源变更、显式刷新及输入合同用例均通过。

以上为部署前直接验证记录。r12输入核对进一步证明全部raw保留、反馈隔离生效；来源推理、关系与空查询解释真实复验仍失败。C未派发，历史未决条目的真实追加效果未覆盖。继续沿用现有账本，无需增加独立Case记忆层；R11-03/04与5.3不关闭。首轮回执hash保留为修前快照，最新源码/测试hash仍同补充评估回执。

## r11历史证据（原批次范围）

- 两条 raw canonical 长度为 371/425 字节，在冻结材料和全部 4 次模型请求中完整，未截断。
- 两个正式 Tool 分别返回 1 行，event_id 精确对应 A1/A2；ClickHouse QueryFinish 均成功、无异常。另 2 次预检单列，未复用为调查结果。
- 两份正式模型输出均符合当次 JSON Schema，A1/A2 成员各出现一次。r9 的 JSON/重复 UUID 缺陷在本样本中未重现。
- 最终 GET/报告/步骤可读取，16 事件、18 工件；30 个批次 HTTP 原件、75 个远端文件 hash 已核。额外 1 次只读状态查看不计作有完整响应原件的批次请求。
- r11批次已核旧 fixture 告警 hash、r10 报告字节保持，其他服务和配置保持。本轮不重做该批远端核验，新增本地验证另见上述回执。

## 审阅顺序

先看[r13分析](../operations/evidence/investigation-r13-20261101/review.md)、[输入与保存核对](../operations/evidence/investigation-r13-20261101/verification.json)、[实际查询/用量](../operations/evidence/investigation-r13-20261101/query-and-cost-proof.json)，再看A残稿与B保存报告。57份业务HTTP响应hash已核，原件不改写。此前[r12分析](../operations/evidence/investigation-r12-20261101/review.md)及下方r11路径保留历史。

## r11历史审阅顺序

1. **看当前状态和范围。** 先读 [批次回执](../operations/investigation-r11-positive-fixture-20261101.json)、[核验](../operations/evidence/investigation-r11-20261101/verification.json)；区分发布 commit、证据 commit、测试数据与真实系统调用。
2. **看完整输入。** 对照 [固定样本](../../openspec/changes/fix-investigation-audit-gaps/retest/r11/fixture.json)、[入库及预检读回](../operations/evidence/investigation-r11-20261101/live/seed-result.json)、[冻结上下文](../operations/evidence/investigation-r11-20261101/live/results/014-synthetic-full-raw-main-step-1.response.txt)。源字段不在模型中、源字段为空、源字段本身不存在须分别表述。
3. **看实际 Tool。** 读取 [运行汇总](../operations/evidence/investigation-r11-20261101/live/results/summary.json) 和 [QueryFinish/SQL](../operations/evidence/investigation-r11-20261101/post-batch-proof.json)。检查租户、主机、半开时间窗口、1007/4001 类别、query_id、返回数量和精确 event_id；同主机候选关系不替代来源对应。
4. **并排看两份原答和反馈。** [首份原答](../operations/evidence/investigation-r11-20261101/first-model-report.json) → [第一次拒绝](../operations/evidence/investigation-r11-20261101/live/results/025-synthetic-full-raw-main-step-12.response.txt) → [纠错实际输入](../operations/evidence/investigation-r11-20261101/live/results/026-synthetic-full-raw-main-step-13.response.txt) → [纠错原答](../operations/evidence/investigation-r11-20261101/correction-model-report.json) → [第二次拒绝](../operations/evidence/investigation-r11-20261101/live/results/028-synthetic-full-raw-main-step-15.response.txt)。正则命中细节见 [匹配分析](../operations/evidence/investigation-r11-20261101/protocol-match-analysis.json)。
5. **最后看用户实际得到的结果。** [最终报告](../operations/evidence/investigation-r11-20261101/final-report.md) 是程序保存的失败报告，包含来源/时间线和 not_assessed 成员；被拒模型原答只作审阅材料，未作为有效结论发布。
6. **逐问题作结论。** 记录问题编号、字段/来源、已验证范围和仍未知部分。复用未变证据；只有恢复具体修复后才选择相应必要直接验证，不全量重跑、不新增恢复/压力/权限专项。

## 代码定位

| 核对内容 | 实现入口 |
| --- | --- |
| 冻结来源与模型字段裁剪 | [case_source_material.py](../../services/api/app/investigation_v2/case_source_material.py) |
| 三阶段提示、同源摘要去重、纠错反馈、报告保存 | [case_analysis.py](../../services/api/app/investigation_v2/case_analysis.py)：`model_context`、`compact_correction`、`CaseAnalysis.execute/finish` |
| JSON Schema、A→UUID 映射、模型请求/等待 | [case_analysis_models.py](../../services/api/app/investigation_v2/case_analysis_models.py)：`conclusion_format`、`translate_report`、`call_model` |
| 真正 SQL、来源对应、空/失败模型视图 | [case_analysis_tools.py](../../services/api/app/investigation_v2/case_analysis_tools.py)：`CaseTools.execute`、`source_alignment`、`model_result` |
| 引用/成员/协议校验、程序补全与时间线 | [case_synthesis.py](../../services/api/app/investigation_v2/case_synthesis.py)：`validate_synthesis`、`complete_synthesis`、`build_timeline` |

完整原件保留在 [r11 证据目录](../operations/evidence/investigation-r11-20261101/)，历史空查询原因见 [来源边界记录](source-boundaries-20261101.md)。不修改原答、原请求、查询记录或旧报告以消除差异。

## 历史文档维护记录

此前文档维护批次只对齐说明、链接和问题状态，没有业务源码/测试改动、业务测试、远端访问、部署或新模型/Tool调用。后续本地修复见本文顶部；两批记录分开。OpenSpec严格校验不替代报告验收，5.3保持未完成，不归档或同步主规格；R10-01的真实效果边界保留。

此前文档批次静态核对：17份Markdown的938个本地链接、33个锚点已检查，调查文档目标均存在；PROGRESS中2个其他任务的旧压缩包链接原已缺失，保持原记录。75份r11远端原件及r10报告字节未变。`fix-investigation-audit-gaps --strict --no-interactive`与`git diff --check`通过；该批业务测试执行0次。
