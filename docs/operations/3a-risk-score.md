# 3A-03：缺失风险分与显式零分

2026-10-20；批次`3a-risk-20261020`。**缺失/null保留未知、显式0及0.8保留原值的限定验收通过。** 已部署21，仅更新并定向重启API、Fusion、Agents；常驻worker和自动响应保持关闭。

## 实际变化

API/Fusion共享输入字段改为可空有限数值。缺失或null传为null；Agents生产worker及replay不再补0，replay中的显式0也不会被原始行的其他分数覆盖。实际模型prompt将未知写为`not provided or unknown (not zero)`，提供值写明来自publisher、来源与量纲未独立核实。后端启发式结果明确标为heuristic，不称为厂商测量。

保留原数值特征基线、RBA加权及confidence权重。未知时内部计算仍可用数值基线，但Fusion解释标为“未提供；仅数值特征基线”。因此未知和零分可能得到相同数值贡献；本批修复的是输入真实性与来源表述，不是重新校准评分。既有0无法反推当时是否缺失，不改历史告警、Run或工件。未全面重做API数值转换、范围或来源合同。

9个已有运行文件和1个原测试预期修改，新增1个stdlib解析模块，无依赖、DDL或常驻env变化。原注册system prompt与lock保持；动态告警prompt随合同修复。差异及16个新增输入见[来源清单](../handoff/3a-risk-score-source-manifest.json)。两份固定上游Connectors文件只用于原replay测试的静态AST读取，不部署Connectors服务。

## 输入 → 中间产品 → 结果

四条新合成告警分别经认证ingress→现有项目SSL Kafka→实际Fusion→PG/API。独立无group消费者在发送前读取各分区末尾位置，捕获真实fused消息，核生产`build_state`和实际prompt投影，不提交offset。四条不同上游ID各存一行并关联同一事件。

| 输入risk_score | 实际fused/worker值 | API中upstream解释 | 实际prompt分数行 |
| --- | --- | --- | --- |
| 缺失 | null | 未提供，仅数值基线 | unknown，明确不是零分 |
| null | null | 未提供，仅数值基线 | unknown，明确不是零分 |
| 0 | 0.0 | 0.00，来源未核实 | 0，publisher提供 |
| 0.8 | 0.8 | 0.80，来源未核实 | 0.8，publisher提供 |

独立非有限数值输入实际HTTP422，在发布前拒绝。缺失/null/零分的Fusion confidence均59，0.8样例72；这里只核原算法继续可运行及解释一致，不据此证明质量或概率。

对捕获的缺失分fused信封，用生产worker分诊、真实21网关→43模型和原writer实际执行一次shadow调用。模型实际收到unknown，返回`needs_review`、自报confidence0.95，理由是缺少认证历史、进程及具体佐证。Run为`90060dec-0dd6-589e-8617-cb89b3cef757`；prompt/response未截断，全文只在受控证据，公开JSON保留hash及工件关系。评分标签在模型输入之外；这是一个真实样例，不能外推完整质量。

原始usage→CostTracker→Run→成本行均为1239输入/106输出/**1345 tokens，unpriced1，费用unknown**。网关triage成功计数7→8，其他角色不增。API可查Run、2事件、2工件及原告警关系；跨租户404、缺scope403、匿名401。三服务定向重启后同样结果可查，无新增输入或模型调用。共33项明确HTTP检查，不计中间轮询。

184项相关测试通过（Agents112/Fusion53/API19），包括缺失/null/0/正值、非有限值、fallback严重告警留待复核、replay零值优先级与原有直接影响路径。首次原测试缺静态Connectors来源、首次只读挂载缺目标目录均保留；补齐固定上游测试依赖后没有删除或跳过原断言。两次Kafka探针metadata错误均在投递/模型前失败，修正探针后仅接受四条新输入、一次真实模型调用，失败日志保留。

45条旧告警、12Run、52事件、14工件、12成本行、2shadow配置、7shadow决策和2规则集的既有摘要保持。本批新增4告警、1Run、2事件、2工件、1成本行、2测试shadow配置、1shadow决策；总告警49。其他33容器/18卷及134迁移保持，三服务锁依赖99/52/142与运行源码hash相符，3测试key已停用。

## 限制、恢复与下一项

组织记忆、技能、知识、近期处置和身份五类reader仍401；不能称为已经消费知识。技术引用质量、真实事件/UEBA源及宽样本模型质量仍未通过。旧finding还存在`0.95 < threshold0.85`的不准确文字；实际因needs_review进入待升级分支，自动graph未执行。本批不声称验证常驻worker提交、rebalance或崩溃中断恢复。

当前十二层命令见[部署说明](../../deploy/aisoc21/README.md)。回退先停新输入和相关消费者、保留队列及持久事实；旧float-only Fusion不能解析新null消息，须用兼容消费者排空或保留新schema层后再撤其他层，不能将未知改写成0来回退。

下一单项：[3A-04组织记忆认证读取及失败语义](3a-org-memory-plan.md)。完整3A/2C及服务端基线保持未冻结。机器回执见[JSON](3a-risk-score.json)；原始材料在工作站`.local/aisoc21/evidence/3a-risk-20261020/`及21同名evidence目录，旧批次证据原样保留。
