# 3A-09受控分诊复验与worker准入回执

2026-10-20，批次`3a-triage-admission-20261020`。**三例真实分诊复验与可靠性审计已完成；完整质量及worker准入不通过。**运行仍为3A-08镜像及十七层定义，未改运行源码、构建镜像或重启服务。

逐项字段、来源与限制见[机器回执](3a-triage-admission.json)、[来源清单](../handoff/3a-triage-admission-source-manifest.json)及[本地核验](3a-triage-admission-local-verification.json)。162份raw已与21逐字节核对冻结；完整输入/回复及受控评分材料不公开展开。[原计划](3a-triage-admission-plan.md)不是验收证明。

## 三例固定输入 → 实际模型 → 持久交付

三个新输入使用中性ID/source/tag，冻结输入的UUID、时间及正文原样提交；评分材料独立保存，未挂入模型探针。各一次真实HTTP受理→SSL Kafka→Fusion→无group/无commit捕获→生产worker→21网关/43。调用前按实际safe-call消息JSON核8000字符上限，保留完整采用块、prompt/response及首次verdict的五类来源工件；没有因分类或理由不符而追加调用。

| 样例 | 实际分类/自报置信 | 实际usage（输入+输出=总tokens） | 完整prompt字符 |
| --- | --- | --- | --- |
| p01 | true_positive / 0.92 | 1576+111=1687 | 6484 |
| p02 | benign_true_positive / 0.95 | 1726+139=1865 | 7086 |
| p03 | needs_review / 0.95 | 1539+132=1671 | 6421 |

合计4841输入、382输出、5223 tokens；每例一次模型尝试，网关triage13→16，其余角色不变，费用unknown。本批仅在探针构造模型实例时设置max_retries=0/request_timeout=45，并记录默认与实际SDK/client设置，生产默认未修改；调用开始检查点存在后不重试未知结果。safe-call入口捕获不当作传输线抓包，网关别名/响应标识不等于已核上游权重版本。

三个样例均实际采用组织记忆1条；技能读取success但selection no_match，KB和近期处置均no_match。p02另采用身份1条，p01/p03身份no_match；不要求五类材料全非空，也不把未匹配写成未调用。每例正常模型Run为2事件/7工件（五类读取及prompt/response），与实际writer输入、API字段/hash及成本行核对；跨tenant、缺scope、匿名拒绝与原手工告警状态另核。

## 分类符合不等于理由受到支持

分类与预定类别3/3一致，但p01理由把11:01的行为说成处于02:00批准备份窗口，又把缺少匹配作业ID过度表述成已确认未授权。其恶意分类符合样例判据，时间及授权断言未被材料支持，不作完整语义通过；原结果保留，不追加模型。

p02的当次授权来自合成CR输入，身份目录只描述持有人，不能据其在职/职位证明活动授权。p03回复提到的0.10已存在于实际Fusion输入叙事，上游risk_score仍为null，不把未知风险当零。p02/p03的理由支持仅限所给合成材料；少量结果、自报置信或来源提及均不证明完整调查质量、校准、召回或因果采用。

## 真实broker与PG：准入仍被阻止

独立测试topic/group共7次publish、8次delivery；5次模型方法替身及1次失败fallback合计6次替身，无额外真实模型。合成broker信封和方法替身不当实际Fusion/模型质量样例。结果分别为：

- 坏schema返回None，无DLQ却commit1；普通ledger返回False、PG零行，也commit1。两者均为静默丢失阻塞。
- 暖重投不再进入模型方法，原事件/工件保持，但通用Run和shadow行改变。冷进程重投已完成Run仍进入模型方法；只是替身重入，没有真实模型重发。首次工件保护不等于完整不可变或模型恰好一次。
- 真实PG工件错误及注入DLQ未确认时offset0；恢复不重投输入、不重入模型方法，offset前进1。但失败前实际五类读取依次success/success/no_match/no_match/no_match，恢复cached保存却全部为not_requested，原采用来源事实丢失，仍属阻塞。
- 另一真实DLQ确认后才commit1；同group短时idle无新处理/调用。以上不是共享PG/broker outage、rebalance、崩溃或长时吞吐验收。

独立失败fallback使用生产catch与CaptureWriter，仅投影为needs_review，未新增模型、broker消息或PG verdict；不算真实持久fallback成绩。生产SDK默认根client retry2/timeout None尚未修复，本批探针0/45秒不覆盖常驻调用预算。可靠性和结果保存缺口须先处理。

## 失败恢复与运行保持

首次broker prepare漏sys.path，import前停止、0topic/0消息；原脚本/log保留并核无副作用后，只修operator恢复。finish首次误要求measured_call_count=1，实际三行均unpriced1/measured0；原脚本/hash及结构化失败保留，最初独立完整stderr未保存。修正仅新operator，只读恢复未重做撤销、输入、模型或重启，不写成全首次通过。

显式HTTP共51项：3 ingress、42 verify、3撤销、3撤销后只读复核；另3次最终200 poll和SDK内部请求分列，不混计。旧54告警/23Run/69事件/46工件/18成本行及既有知识/图材料保持；新增3告警/5Run/8事件/31工件/3成本行/5 shadow决策，当前57/28/77/77/21、shadow18。其中3个真实模型Run，另2个broker探针Run不算质量样本。

本批运行源码/env/prompt/镜像和十七层不变，服务重启0，36个既有容器/18卷/134迁移保持。三枚新操作key已撤销401，十枚reader及五类原查询/目录/hash/scopes保持。受控位置见[配置索引](configuration.md)，当前运行及一次性工具检查点见[21说明](../../deploy/aisoc21/README.md)；不清topic/group、图、库或卷，不盲重发模型。

下一单项为[3A-10 worker可靠性修复](3a-worker-reliability-plan.md)，**仅规划、未实施**。常驻worker、自动graph、审批、真实响应继续关闭；p01理由缺陷和旧事件/UEBA、工具身份、深调查版本pin等限制保留，不能把三例分类符合或脚本exit0写成准入通过。
