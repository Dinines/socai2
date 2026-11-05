# C3初始主分析与领域结果：实现及字段交接

2026-11-03。新socai2路径已实现`BaselineService.analyze`：在既有baseline Run中读取冻结C1和C2模型视图，登记模型请求后调用租户模型入口，保存原始回复、用量、主分析、四个领域结果与补查需求。**本批只用合成模型替身验证，没有调用真实模型或接通业务HTTP。** C3是初始分析，不是最终报告或完整基础调查；C4–C6与后续再分析回合仍待接。

## 1. 对现有实现的取舍

旧API的CaseAnalysis已有模型配置、guard、调用上限和有限工具循环；Agents领域Router还会创建自己的调查状态，并由领域runner调用模型/工具。直接整包调用会产生第二套Run/预算和隐含工作，不能接成当前Case的完整流程。

本批复用API侧`resolve_llm_config`、`safe_chat_completions_request`、模型地址解析及airgap检查，保留现有3000输出tokens上限。四领域分析重点参考现有identity/cloud/phishing/insider实现，重新放入本轮主分析合同。**一次共享模型调用输出四个领域视角**，不是四个独立专家执行或四份独立证据；四领域结果分别留存，主分析记录冲突，不做多数票或最高分裁决。

| 领域 | 本轮要求核对 | 未取得材料时 |
| --- | --- | --- |
| identity | 身份、认证方式、MFA、会话、权限变化、授权范围 | 适用性undetermined或发现unresolved，并提出证据需求 |
| cloud | 控制面操作、资源/账号、IAM、配置变化及影响边界 | 不凭云产品名称推断账户接管或影响成立 |
| phishing | 发件身份、邮件头/认证、链接/附件、投递与点击/执行依据 | 不把可疑链接等同于已投递、已点击或已执行 |
| insider | 数据访问/外传、数量/目的地/时间、已知行为基线、业务授权 | 不凭作息、岗位或缺少审批推定恶意意图 |

上述是提示与输出约束，不是已验证的模型推理质量。当前原始材料的必要语义投影仍不完整，C3只能基于本次实际可见视图提出暂定分析和补查需求。

## 2. 新增数据合同

运行时Pydantic合同在`app/socai2/baseline_analysis_contract.py`，专用输出schema为`baseline_analysis.schema.json`，设计树镜像为`socai2-baseline-analysis-v1.schema.json`。额外字段拒收，集合/文本长度有界；不修改原38份通用JSON合同或数据库枚举。

| 字段 | 具体内容/类型 | 约束及页面含义 |
| --- | --- | --- |
| summary | 非空文本 | 初始认识及限制，不自动作为Case当前判断 |
| members | alert_id、state、summary、evidence_ids、limitations | 所有冻结成员恰好一条；state为analyzed/unresolved/not_analyzed。未在模型视图出现的成员不能标已分析；仍不是最终逐成员交付 |
| findings | id、observed/inferred/unresolved、statement、alert_ids、support_ids、counter_ids、alternatives、limitations | 支持/反证分开，保替代解释；超出范围、未见引用、成员与来源错配拒收。非observation来源不能升级成observed |
| questions | id、answered/unresolved/not_applicable、answer、evidence_ids、limitations | 冻结六问题各一条；answered需要来源；未解决/不适用必须说明限制 |
| domains | name、applicability、reason、alert_ids、finding_ids、limitations | identity/cloud/phishing/insider各一条；适用性applicable/not_applicable/undetermined。适用领域需范围；未应用领域不能挂发现 |
| conflicts | id、finding_ids、resolved/unresolved、explanation、evidence_ids | 至少两个不同且已存在的发现；解决矛盾要来源，不能只改状态 |
| followups | question_id、alert_ids、query/deep/graph/human、objective、required_evidence、source_ids、object_keys | 绑定已有问题、冻结成员和对象；仅是证据需求，无可执行SQL、自由工具参数或扩大范围动作 |

模型只返回S1/S2等本次可见来源编号。请求工件保存完整`source_map`：S编号→原工件ID/路径/角色、来源适用成员、实际可见值hash。原始来源路径没有丢失；不能引用仅在数据库中存在、但未送进本次模型输入的内容。人工反馈未声明的范围不自动扩成整案；旧判断仅作用于与本轮重合的成员。

程序做结构、范围、来源和角色检查，不证明正文中的因果、授权或业务解释正确。通过后状态明确为`structure_scope_sources_checked`，不命名为“语义已验证”或“完整调查已完成”。

## 3. 落表与执行顺序

本批不新增业务表/列，继续使用已建29表：

| 位置 | 写入/更新内容 |
| --- | --- |
| run_steps | 一个C3 stage、一次model子步骤；父子关系、顺序、provider、版本、状态、起止、请求/响应工件、用量及错误 |
| artifacts.model_request | 真正发送的body（model/messages/max_tokens/response_format）、输入视图ID/hash、source_map、保守token预留量；不保存凭据、认证头或含凭据URL |
| artifacts.model_response | 原provider JSON、校验错误码、request_id和真实上报用量；无效/截断/拒绝回复仍保留，不拼接残稿 |
| artifacts.domain_analysis | 四个领域各一份，符合既有analysis_block；发现中的S编号解析回完整证据引用。领域适用性、替代解释、冲突和问题完整正文在同轮主分析快照中 |
| artifacts.source_snapshot | C3主分析及来源表、领域工件ID、状态/原因、验证范围、未执行领域及系统限制 |
| run_members | 仅在候选通过合同检查后更新analysis_state；不把只看过元数据视图的成员标成原文已读，不写最终conclusion_covered |
| runs / case_assessments / results | C3正常结束保持Run running；不发布最终Result、不自动采用、不解决Case。传输/提交结果不确定时Run标unknown占槽 |

顺序为：Case→Run加锁核身份和已有C3→准备固定输入并提交C3 stage→解析租户模型配置→同锁内核本Run全部模型用量并保存model running/请求→提交成功后发起调用→原回复、用量、领域/主分析和步骤终态同事务保存。

并发第二次调用遇到running/unknown返回冲突；已完成、失败或跳过的C3重复请求读取原工件，不自动重试、不重新解析配置或调用模型。C3期间Case新增成员进入下一pending，旧输入及输出范围保持。步骤未落定时，原发布服务继续拒绝完成Run。

## 4. 预算、异常和来源角色

- 读取既有Run.limits，不新增C3独立预算。统计本Run所有已尝试model步骤；先前用量未知或不一致时不继续派发。调用次数、总tokens和绝对截止时间都须已定义。
- 请求按实际JSON字节数＋3000输出上限＋256余量做保守预留；模型消息不超过既有12KiB程序消息限额，C1/C2的8192/2048视图限额不提高。实际返回用量仍另存，超预留或不一致拒绝采纳。
- prompt/completion/total缺失保持NULL；可以从已知prompt＋completion计算total，不把未知补0。费用没有定价依据时cost=NULL、cost_state=unpriced；父stage不重复计费。
- 模型未配置、输入不满足合同、预算不足或已到截止，保存skipped及原因，不伪造分析。回复不完整、拒绝、未提供的tool/function调用、无效JSON/范围/引用，保存failed及原件，不自动纠错重试。
- 传输、取消或提交结果不确定时保留unknown，阻止自动重派；本批没有增加定时领取或恢复模块。原始输出结构通过后也只作为prior_analysis引用，不能当独立观察。

当前只接初始C3。C4取得新证据后的再分析，需要显式的新输入版本与步骤身份，不能覆盖本轮原请求/原答或把重复C3当成自动重跑。

## 5. 一个具体例子

以下说明合同，不是线上模型结论：R1冻结A1脚本告警和A2外联告警；C2拿到主机当前资产，TI查空，图接口未接。C3看到来源标签后，对A1保留“可能是维护脚本”和“授权仍待核”两个解释，不能写observed攻击；identity适用，cloud/phishing/insider缺材料则undetermined。

主分析保留这两个发现及未解决矛盾；授权问题unresolved；followup建议由人工提供明确对象、时间和授权范围，网络归属问题可建议query/deep，关系核验可建议graph。此时用户纳入A3，R1仍只保存A1/A2的分析，A3进入R2待更新。

数据库中留下同R1的一条C3 stage、一条model步骤、请求/原答、四份领域工件和一份主分析快照；Case当前判断不变。接下来的C4/C5负责补证和关系核验，C6才形成最终交付。

## 6. 验证与后续

12项不同C3检查＋7项受影响旧流程回归最终通过，另含15个输出合同反例。使用21既有PostgreSQL独立合成库，所有模型响应及传输均为明确替身，0真实模型/外部业务Tool调用；受限账号和SSH隧道每批结束清理，没有新容器。延期外键造成真实COMMIT失败的测试确认请求未持久化且没有调用模型。原回执见[本批汇总](../operations/socai2-baseline-c3-20261103.json)。

首轮静态检查发现一个多余括号和导入顺序，运行数据库检查前修正；12项业务检查分首10项与后补2项执行，均通过。收尾增加传输前timeout≤0拒绝，并把延期FK测试收紧到实际约束名和提交前已插入标记，对这两项定向复核通过；其余已通过项复用。测试循环闭包另显式绑定变量。既有C1/C2/schema回执保持原件，不改成当前代码指纹。

下一先处理C4的必要语义字段读取、可用工具目录与绑定、确定参数查询和问题级Deep；复用同Run步骤与总预算，并设计新证据后的C3再分析。随后接C5有来源图、C6比较/影响/完整性和交付，再接业务HTTP/新表writer及迁移。UEBA/知识/Graph来源仍未适配。真实模型质量、完整基础流程和页面DTO均未验；不声称已优于开源版本完整能力。页面、业务库和线上部署未改，未提交推送；旧报告修复继续暂停，r13不重试，5.3未完。
