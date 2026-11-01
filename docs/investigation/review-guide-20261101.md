# 调查模块当前审阅指南

2026-11-01。用户要求先保留当前问题；本文整理现状和已有证据，不启动新一轮功能修复或真实调查。模块总入口见 [最新指南](audit-guide-20261031.md)。

## 审阅基线

| 项目 | 固定值 |
| --- | --- |
| 最近部署 | r11，发布源码 `a543ad6d043c35ec17fe792885ab48a11d325e4e`；功能修复 `49a04eb73d765b42bb23ea0ae0b2cfc4a50a1845` |
| 代码 | 独立 API 的 472 应用文件与候选清单一致；[安装核验](../operations/evidence/investigation-r11-20261101/post-install.json) |
| 最新证据保存提交 | `d7ff5d2`；这是文档/证据提交，不是另一次服务发布 |
| Case / Run | `5fbb643b-975b-4798-8729-801b50ba956f` / `22b48b78-3716-5a64-994f-788d020dc760` |
| 结果 | `failed/partial`，`invalid_or_unreferenced_conclusion`；4 模型、2 正式湖查询、0 复用、12,728 已知 tokens；4 调用未定价 |
| 数据边界 | 用户选择新增的 synthetic 样本；2 告警、2 对应湖事件、1 Case、1 Run，旧数据和报告保持 |
| 当前完成度 | OpenSpec 16/17，5.3 未完成；原 r3 独立结束审阅不替代 r11 报告质量检查 |

本次真实调用指数据库、API、模型和 Tool 实际执行；示例行为不是生产端点上发生的事实，也不是采集/检测验收。r11 本批已结束，不重试挑选报告。

## 当前问题登记

以下编号用于文档追踪，均保留未解决或未验证状态，不表示已新增实现任务或测试门。

| 编号 | 问题与当前证据 | 状态 / 后续审阅判据 |
| --- | --- | --- |
| R11-01 | 有限协议句式校验会拒绝 `HTTPS/TLS 状态尚未确认` 及带空格/结束引号的不确定表述；首答的“需确认协议为”也有歧义 | **未修复**。需区分明确未知、待核与无依据肯定/否定；不能把所有含协议名的文字一律放行 |
| R11-02 | 纠错原答把“在总结中必须明确指出”等写作要求及内部错误码写进报告 | **未修复**。校验反馈用于纠错，不能成为用户报告中的证据或业务结论；保持原一次纠错/预算 |
| R11-03 | 混淆 Case 描述与告警原文；忽略 raw 中的 synthetic 标记；从 documentation address 猜“文档服务器”、断言“故意缺失或环境未集成”，并出现无来源工具名称及 `Expect ` 残句 | **未修复**。每项来源陈述、缺口和建议须能回到实际材料；未知原因继续未知，结构通过不能关闭此问题 |
| R11-04 | 首答将 shared_context 标 not_supported，纠错改为 supported behavioral_link 并称“合成攻击链”，依据与判断不稳定 | **未修复**。区分精确来源对应、共同主机/时间、原文 PID 陈述、行为因果和攻击目的 |
| R10-01 | r10 将成功空查询当矛盾，并猜采样、阻断、丢日志；已部署共用提示和程序查询事实字段 | **真实模型效果未验证**。r11 两查询非空、没有 T 分诊摘要，不能证明空查询推理或同源摘要去重效果已通过 |

R11-01 的误拒与 R11-02–04 的报告内容缺陷同时存在。即使协议校验放过原答，现有报告仍不具备完整语义验收依据。上述问题没有在本轮文档更新中修复或关闭。

## 已验证且可复用的证据

- 两条 raw canonical 长度为 371/425 字节，在冻结材料和全部 4 次模型请求中完整，未截断。
- 两个正式 Tool 分别返回 1 行，event_id 精确对应 A1/A2；ClickHouse QueryFinish 均成功、无异常。另 2 次预检单列，未复用为调查结果。
- 两份正式模型输出均符合当次 JSON Schema，A1/A2 成员各出现一次。r9 的 JSON/重复 UUID 缺陷在本样本中未重现。
- 最终 GET/报告/步骤可读取，16 事件、18 工件；30 个批次 HTTP 原件、75 个远端文件 hash 已核。额外 1 次只读状态查看不计作有完整响应原件的批次请求。
- 旧 fixture 告警 hash、r10 报告字节保持；其他服务和配置保持。原业务测试按已有结果复用，本轮不新增通过项。

## 审阅顺序

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

## 当前文档维护范围

本轮只对齐说明、链接和问题状态；没有业务源码/测试改动、业务测试、远端访问、部署或新模型/Tool 调用。OpenSpec 严格校验属于规格文档检查，不能替代报告验收；5.3 保持未完成，不归档或同步主规格。后续若恢复修复，从 R11-01–04 的实际字段问题继续，R10-01 的未验证边界保留。

文档静态核对：本轮17份Markdown的938个本地链接、33个锚点已检查，调查文档目标均存在；PROGRESS中2个其他任务的旧压缩包链接原已缺失，保持原记录。75份r11远端原件及r10报告字节未变。`fix-investigation-audit-gaps --strict --no-interactive`与`git diff --check`通过；业务测试执行0次。
