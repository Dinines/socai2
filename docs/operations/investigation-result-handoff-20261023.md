# 调查结果一致与停止交接：小范围实施回执

2026-10-23。用户要求先提交、按规划推进并逐步测试；随后明确仅先完成小改动，调查后续设计另讨论。方案基线已提交`5e0ce171`，此前工作区干净且原方案在`2207dc79`。本批改动仅保存在本地，未部署、未推送。

本批范围：人工Forensic前置校验及响应/报告采用；工具逐次留存和结构状态；Deep及graph停止后的已有材料交接。保持Recon→Forensic→Responder→Report四阶段、角色映射、模型参数、六轮及既有预算。沿原restore change，不新增事件对象、动态编排或共享结构平台；后续设计等待讨论。

## 实施及影响

- **人工路径**：Forensic返回前应用原标识存在性校验，两入口共用；initial.run_id与ledger一致。Forensic新增程序维护的validation，Responder/Report输入各增加至多1500字符校验材料及短约束，输出格式不变。降级分支仍保留原两次调用及原文审计，程序交付核验来源的计划和待核报告；正常分支沿原行为。
- **工具留存**：每次执行完成即保存tool_call事件与tool_result工件，同一事务检查Run/tenant及插入结果；冲突不覆盖、失败不重查，留存缺口显式记录。每次工具增加一次存储事务，仍受原时间上限约束；没有新增表或数据库迁移。
- **状态与材料**：顶层error/available/ok和列表区分success/empty/unavailable/error/unknown，不再解析preview。无已知包络的普通字典保守unknown（包括部分既有工具），不计成功pivot，可能降低深度计数。empty仅说明空响应，不能判断安全；存储gap与业务调查完成度分开披露。
- **停止交接**：Deep自身时限、异常及外层graph时限保留已完成材料；Markdown列状态、工件引用、停止原因及未决问题。普通外部取消继续传播，已提交工件保留，但不承诺取消后一定生成最终报告。未新增模型总结调用。

留存正文是原4000字符ToolMessage通道的有界表示，另留完整序列化UTF-8字节/hash、截断标记和200字符preview；不是外部结果完整备份。若后续直接停止，不一定有模型读过该ToolMessage，实际消费仍看下一轮llm_exchange。留存工件不保存临时pending状态，引用只在事务成功后返回。graph_step和既有prompt截断/seq分页限制不因本批消失；Run completed仍是执行结束，业务是否完整看graph_result.completion与报告。

这是局部行为变化，没有合并模型职责或要求小模型承担更多任务。标识检查并非业务语义验真；本批交付合同通过不代表全部模型、场景或调查质量通过。

## 逐步校验

设计：[本批OpenSpec](../../openspec/changes/restore-alert-investigation-integrity/design.md)。证据目录：`.local/verification/investigation-result-handoff-20261023/`。表内是各步结果，部分复用测试重叠，不能相加当唯一用例数。

| 步骤 | 校验与日志 | 结果 |
| --- | --- | --- |
| 0 方案提交、设计 | `5e0ce171`；OpenSpec strict | 通过 |
| 1 校验前移、Run身份 | 真实编译图＋四节点替身，run/stream；manual-step1.log | 17 passed |
| 2 下游采用与截断保真 | 正常/降级/对抗性回复替身；manual-step2.log | 38 passed |
| 3 工具回调/状态/正文 | deep-step1.log | 18 passed |
| 3a Deep异常/取消/留存缺口 | deep-step2.log | 87 passed，3项PG测试初次因无DSN跳过，见步骤4补验 |
| 3b 缺口用语 | deep-step3.log | 13 passed，27 deselected |
| 3c 原子SQL、租户、UTF-8/hash、失败回滚/冲突 | 独立临时PostgreSQL；ledger-step1.log | 2 passed |
| 4 真实Deep循环＋SQL＋外层超时/模型异常＋Markdown及原C2合同 | ledger-runner-step3.log | 44 passed，0 skipped，含上述3项PG补验 |
| 4a runner/报告既有直接回归 | runner-report-regression.log | 18 passed |
| 5 当前模型实际IO与程序采用 | model-io-direct/；下表详述 | 交付合同通过；原文遵循仍有缺陷 |
| 6 未参与实现者独审 | independent-audit.md | 限定ACCEPT，0项本批必须修项；独立70 passed及真实LangGraph并发取消隔离PASS |

首次串联测试`ledger-runner-step2.log`为2 failed/42 passed，原因是新断言将JSON转义文本当原始中文，以及将Run状态误设为业务partial（后者在复核中修正，未单独运行）；修正测试为解析JSON、检查graph_result.completion后通过。没有据此改变原ToolMessage序列化或数据库状态枚举。失败日志保持。

## 两次模型输入输出观察

先用原观察方式发起2请求，均503/无回复，用量未知；tracker零记录不表示零消耗，材料在`model-io/`。只读对照确认同一loopback通道自动代理发现返回503，显式trust_env=False的健康及五模型别名查询均200（`model-connectivity.json`）。仅测试脚本换直连client，另用新合成样例，不重放原输入。业务传输、服务器、模型配置保持。

第二样例实际Run `462244c2-7fdd-4ec4-beb0-937058fd9cc1`，仅本地内存/工件，非生产Run；合成输入给出来源IP `192.0.2.144`，上游假设却引用`203.0.113.178`，原校验降为needs_review。实际消息记录在安全合同处理之后，原可见回复、程序采用state和Markdown分别保存，未保存凭据或私有推理。

| 调用 | 目的、实际输入 | 可见输出及代码采用 | tokens |
| --- | --- | --- | --- |
| Responder / aisoc-investigation | 新合成摘要、原假设、降后置信度0%、最小validation与原提示；输入498 | 返回可解析JSON，但仍给条件性隔离/清除/恢复和risk low，原文遵循未全过。代码保存原文后采用verify-only、risk unknown、三类处置步骤为空 | 498＋526＝1024 |
| Report / aisoc-report | 上述同一降级Forensic及已采用计划、原报告上下文；输入1134 | Markdown识别needs_review，但仍补写无来源的enrichment描述。代码保存原文，最终采用确定性待核报告，未交付该补写 | 1134＋556＝1690 |

两个角色别名本次均解析为`openai/aisoc-test-investigation`，不是两种底层模型对比。两次均finish_reason=stop，总计2714tokens，网关报告2次measured、cost0（仅转述网关返回，不解释成模型普遍免费）。各次2048输出上限、retry0/45秒；无第三次调用或模型配置调整。整个批次4请求尝试/2回复，前两次用量未知。本例验证的是改动后的实际输入输出接缝及程序约束，不是小模型全部业务能力验收。

## 收口边界

未部署/启停常驻服务/发Kafka业务消息/写生产PG/调用厂商动作；原迁移5/15、旧unknown/预算/质量失败与生产v1事实保持。本批独立临时PostgreSQL已停止并自动删除，临时SSH通道已停止；原有容器/常驻配置未更改。结束独审`handoff_audit`限定ACCEPT、0项本批必须修项。源码、文档、逐步日志、模型原文/采用与审计副本保留在`.local/versions/investigation-result-handoff-20261023/`（含hash清单）；实施增量未再次Git提交。后续调查设计不自动继续。
