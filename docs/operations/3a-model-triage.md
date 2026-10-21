# 3A-02：有界真实模型分诊

2026-10-20；批次`3a-model-triage-20261020`。**消息/真实模型/账本/API限定链路与三条盲测分类通过；完整模型质量和常驻自动分诊未通过。** 本批无运行源码、prompt、依赖、镜像或常驻配置变化，无服务重启。首轮污染样例保留，没有覆盖原Run后重测。

## 输入与实际调用

先经认证ingress→项目Kafka→Fusion→PG接收四条合成告警，另三条为盲测对照。独立单分区测试topic/group在空topic上显式提交起点0，再启动实际`FusedAlertTriageWorker.start()`；逐条等待持久结果及commit后再发下一条，不消费业务积压。

实际模型请求使用当前`aisoc-triage`→21 LiteLLM→43 `aisoc-test-investigation`。生产applier、上下文reader、模型构造/调用、解析、writer与PG均实际运行；观察器只保存真实返回值，未提供模型替身。两个新tenant在已有PG shadow表中明确开启观察模式，原告警人工状态/处置不变，无playbook、审批、源端回写、自动graph升级或响应。

| 样例 | 首轮真实结果 | 移除评分标签后的独立盲测 |
| --- | --- | --- |
| 删除卷影副本并加密247个canary文件 | true_positive / 0.95 | true_positive / 0.95 |
| 有变更单背景的有效扫描检测 | benign_true_positive / 0.95 | benign_true_positive / 0.95 |
| 仅unusual活动标签，无佐证遥测 | **false_positive / 0.95，不符合验收** | needs_review / 0.95，保留不确定性 |
| critical告警，独立进程模型地址为本地闭合端口 | 实际连接失败→原deterministic fallback→needs_review / 0.05 | 不重复调用失败样例 |

首轮测试的`raw_event.label`、synthetic及来源标签进入了模型可见材料；恶意回答直接引用了“malicious标签”，不足样例将synthetic误当检测无效。因此首轮只证明真实链路，不能作为质量通过证据。另建三个新告警/Run，保留相同业务证据，将评分标签、expected和测试来源标记放在模型输入之外，source_event_ids使用不含类别的UUID。不是修改原输入、改prompt或改模型答案。

盲测前核实际prompt投影包含完整简短evidence_summary；实际调用后核无`raw_event.label/synthetic`或synthetic来源引用，prompt/response未截断。全部字面材料、输出及hash在受控证据中。授权背景只是合成输入提供的变更单信息，**未查询真实审批系统或独立核实授权**。模型0.95只是本次自报置信，不是校准质量或真实事件结论。

用户再次确认“不同上游告警各存一行，再关联同一事件”。本轮两组中三对同特征样例也实际保留不同告警ID，各对关联同一非空fusion_incident_id，关系见机器回执；这是配对复核，不重建旧legacy事实。

## 持久产品与API

六次成功回复的原始usage→CostTracker→Run/`aisoc_run_costs`逐项相等：6629输入、777输出、**7406 tokens，unpriced6，费用unknown**。响应header实际指向43；网关triage成功计数1→7，其他角色保持，未偷偷追加调参调用。

七个Run均可经认证API读取事件及原告警关系。成功模型Run各有一条llm_call、一条triage_verdict及prompt/response工件；模型失败Run只有fallback verdict、无成功响应工件或成本行，失败信息在findings中。日志`persisted=True`是成本持久化模式，不能当作实际存在成本行；首次finalizer错误预期失败也有成本行，断言停止后修正只读检查，未重复模型/输入/账本写入。

另tenant查A Run为404、缺scope403、匿名401。共66项明确对应HTTP验收检查（含7次最终告警轮询读取和两轮各3次key停用检查，不计中间404轮询）。两测试group最终commit分别4/3；停止并以同group重启独立worker、不追加输入，position仍4/3、processed0，模型计数不增。不是常驻服务重启或多分区恢复验收。

46项原版相关测试通过，覆盖分类词表、截断JSON和prompt账本。此前38告警、5Run、39事件、2工件、6成本行、2规则集全部摘要保持；新增7告警、7Run、13事件、12工件、6成本行、2shadow配置和7shadow决策。36个既有容器/18卷/134迁移保持，3key停用；7天retention的两个测试topic及各自DLQ保留。没有真实厂商动作，常驻worker仍关闭。

## 未通过的事项与下一项

- 本批未提供risk_score，`build_state()`却默认0.0，prompt显示“vendor risk score 0.0”；模型多次将其作为已测零分引用。缺失与零混淆是实际输入真实性问题，盲测分类符合预期不能抵消它。
- 组织记忆、技能、知识、近期处置及身份五类真实HTTP reader均返回401，实际未消费这些材料。不能把空列表当“确认没有历史”，本批不宣称完整上下文/知识质量通过。
- 恶意回答包含ATT&CK名称/编号错配，例如T1490被称为Inhibit Execution；行为分类正确不等于技术引用正确。
- 授权信息来自测试输入，未做第三方核实；缺少普通事件/UEBA源、实际工具结果及宽样本质量验证。无多分区、rebalance、崩溃中断模型调用或重复模型Run持久性验收。

下一单项：[3A-03缺失风险分语义](3a-missing-risk-plan.md)，先让缺失/未知与显式0分可区分，再验证fallback和实际prompt；上下文身份/失败状态及引用质量之后逐批处理。保持常驻worker、自动升级与真实响应关闭，完整3A/服务端基线不冻结。

来源见[操作输入清单](../handoff/3a-model-triage-input-manifest.json)，详细回执见[JSON](3a-model-triage.json)。受控材料位于工作站`.local/aisoc21/evidence/3a-model-triage-20261020/`及21同名evidence目录；全文prompt/response不随公开交付复制。
