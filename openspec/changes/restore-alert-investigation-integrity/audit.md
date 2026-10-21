# 完整性评估与修复规划独审

2026-10-21。实现/整理：root。三路只读源评估：api_auth_review、fusion_review、triage_review；probes由triage_review保存，root复跑。最终规划独审：未参与文档/探针实现的api_auth_review；triage_review另核I2描述与范围一致性。

## 结论

**accept，仅评估与修复规划通过。** 不认可产品修复完成、自治质量通过或运行启用；change继续活动，不归档。当前4项评估/规划任务完成，11项后续实施/交付任务未完成；旧R02暂缓，原0/17保持。

## 独立复核

- 四服务1578个固定上游原件均在，68修改、0缺失；770运行Py、prompt lock1、Compose28共799项hash零差异。
- 12份原Dockerfile/pyproject/lock保留，未删除原路由声明，API/Fusion双schema一致；静态编译/引用检查不冒充完整运行依赖或所有接口验收。
- api_auth_review和root均复跑未改写生产函数的AST探针：warm/cold提前return跳过升级，graph.complete_run默认0覆盖usage，随后首次分诊投影拒读，与assessment一致。内存替身、0真实网络/PG/Kafka/SDK/模型，不声称21已发生故障。
- I1临时裁剪、I2本地保护与上游graph组合、I3原HTTP入口与本地持久合同组合、I4上游缺源语义归属准确。修复设计保留必要既有修复，不全盘回退或简单解除全部开关。
- R02原五文件hash零差异；旧独审三份绑定仍匹配，0/17，仅新增status暂缓，不作为功能前置。CLI仍列ready的边界已在根说明和context标明。
- 完整告警/调查目标包含自动分诊、自动关闭和自动升级；playbook/反馈一体保留不额外改测；可用性专项后置，不扩大采集、原始检测、前端或真实响应授权。

## 规划校验与修订

严格 `openspec validate --all --strict --no-interactive --json`：两活动change均通过。根入口/本批/相关权威文档395个本地链接无缺失。规划审查中root收紧F3：按原HTTP入口的完整处理合同与Kafka对齐，不另创含糊的预览模式。

原探针第一次缺注入time的NameError明确记为探针错误，修正后才复现I2；原始失败摘要及更正保存在probes/result.json，未当产品运行失败。旧批次回执、来源清单和质量失败未改写。

本轮仅文档、规划和只读源探针；未改运行源码/依赖/Compose，未做部署、模型、消息、业务PG或真实厂商操作，未Git提交/推送。后续产品实施需按本change待办推进，不以本规划独审代替实施结束审计。

## 后续原则同步（2026-10-21）

用户再次明确全部一体模块可整体原样迁入、不额外改测，冗余设计及服务可用性测试/修复后置。proposal/design/tasks/spec及assessment补充段已同步：I2仅正常graph用量/结果问题列当前修复，特殊故障恢复接续后置，不先增加通用阶段/恢复框架。纯文档change prioritize-functional-completeness另经api_auth_review结束独审通过；没有重跑本评估源探针或改写原证据，本change仍4/15，产品修复未实施。

## 后续总规划衔接（2026-10-21）

用户要求整体规划并强调自动调查。当前completion-plan统一B1—B6执行，原F编号改作问题类别；proposal/design/tasks/spec明确自动分诊后实际关闭或自动升级、无需人工再点的取证/知识/分析与结果/报告交付。沿用本产品任务树，4/15不变，未归档或实施产品；总规划文档另由plan-alert-investigation-migration记录审计，不重跑原源码或探针验证。

## 2026-10-21 自动调查触发澄清独审

**本节关于“用户新增规则触发目标”的解读已撤销。** 用户随后明确是在讨论原有代码设计，并非提出新需求。原过程记录保留如下，其规划接受结论不再作为新增规则合同的依据；纠正结果见后续勘误记录。

用户澄清按配置规则（例如告警等级）触发调查，命中启用条件即自动开始。root同步总计划、范围、proposal/design/spec/tasks及PROGRESS；triage_review未参与修改，独立核对源码与规划后accept：目标与当前普通worker未关闭后升级、业务规则无investigate动作、playbook已有severity过滤/investigate步骤分别说明；保留原能力复用候选，未预建新规则平台或扩大可用性矩阵。实际阈值/启用范围尚未指定，当前仍只规划、worker OFF、任务4/15不变。活动change严格校验通过；无产品代码、部署、模型或消息操作，旧归档规划与历史回执未改写。

## 2026-10-21 原版设计讨论勘误

用户明确上述讨论是在核对原代码设计，不是新目标。root撤回误加的规则合同、优先级和命中/未命中/停用专项要求，恢复原spec段落及3.3任务；范围、总计划、proposal/design/PROGRESS同步纠正。只读核固定上游确认：playbook已有severity/tags条件和investigate步骤；普通worker另有分诊未关闭后run_escalation路径，不能因后者没有等级筛选而推断整个原版无规则驱动设计。Case/参数/认证接缝仅按静态事实登记到upstream-issues，未当作真实故障或已验能力，不追加playbook改测任务。

triage_review未参与编辑，结束独审accept：新增需求已撤回、两条原路径及静态限制表述准确，playbook额外改测/可用性后置、4/15及未实施边界保持。活动change严格校验1/1通过。无产品、部署、模型、消息或远端操作；原归档与冻结回执保持。
