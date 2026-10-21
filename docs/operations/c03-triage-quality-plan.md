# C03-02：四例新分诊理由复验

2026-10-21。状态：**执行前冻结；尚未调用本批真实模型**。承接[C03-01](c03-triage-reasoning.md)及[C03总卡](c03-triage-reasoning-plan.md)，只验四条新的合成受控输入的分类与短理由依据，不外推统计质量、真实组织批准、全五类非空引用或常驻准入。旧p01、旧评分、三条unknown和原积压保持。

## 固定范围与输入

[输入JSON](c03-triage-quality-inputs.json)只含中性编号、材料和调用上限，无预期分类/评分字段；四例分别覆盖直接破坏行为、完整本次授权且跨日期/offset、缺端点/时区/范围及缺job、发生时间在授权窗外而创建时间在窗内。前三例tenant A，第四例B；每例新UUID/source/rule/account/host，不复用旧p01或离线SDK测试例。case01去掉草稿中`controlled`修饰，避免把测试性质当作判别依据；仅修改新输入，不改旧资料。

输入SHA-256：`e2fe2d53ac054e5e5f225782bd501e0cce6591956845fe70c1b8173988044751`。评分判据单独放在受控忽略目录，SHA在执行前清单中冻结；不挂载至模型执行容器，不拼入prompt。期望值和独立评分记录不能作为后续模型输入。

保留当前039f候选所成的25层配置/22源码层、184运行Py与独立prompt lock；不改业务源码、模型角色、prompt/schema、8000字符/16000规范UTF-8字节、retry0/45秒/输出512，不重建服务或执行DDL。graph、审批提案、自动记忆写回和真实响应保持关闭，resident worker继续OFF。使用真实HTTP→项目raw/Fusion→PG/fused，再由新独立quality topic的实际Kafka live worker消费；明确该临时worker不等于主group常驻准入。

## 预算、凭据与资源上限

实施前只读核旧材料、配置和镜像，保存受控项目PG custom备份、原policy字节及恢复位置。A当前2条预约40000单位/2条unknown，B当前3条60000/1条unknown；当前policy均3 calls/60000单位/max_unsettled=2。只增加本批容量：A设5 calls/100000/max_unsettled=3，B设4/80000/2，窗口仍86400秒；保留旧五行及原policy hash，不退款、改写或重放。一次预约仍固定20000单位，新增上限4行/80000单位，不是实际tokens或费用。每tenant仅新增一个同时未确认槽，严格串行。

| 对象 | 本批上限与限制 |
| --- | --- |
| 真实模型 | 最多4次、每例1次；未知/失败/格式或依据错误立即停止，不追加重试来改善成绩 |
| 新业务 | 最多4新告警/4Run/4预算预约、12事件/28工件/4成本行；若原shadow policy采用shadow，另最多4条shadow回执。旧材料不改 |
| 凭据 | 最多3枚3小时操作key；十枚原reader及映射不换。结束撤销新操作key并HTTP拒绝复核 |
| Kafka对象 | 最多2新单分区topic（quality与其DLQ）及1独立group；复制原完整fused信封，不伪造重算Fusion结果 |
| 正常发送/交付 | 最多12次发送尝试：raw HTTP4、Fusion fused4、quality4；正常及绝对物理消息交付上限均12（Fusion常驻raw消费4+原fused捕获4+quality worker4）。遇非预期记录即停，不扩大扫描 |
| 提交 | 仅新quality group初始0及最多4条成功输入的显式确认；主group、六旧budget组、原83条历史不消费、不reset或提交 |
| 只读及观测 | operator HTTP发送尝试最多240（含真实gateway与API，Mock另计）；显式host SQL调用及独立审计分别记数，不把这些计数冒充API/worker内部全部SQL。独立审计不额外物理读broker消息 |
| 其他动作 | 0真实厂商/响应/外部消息/embedding、0旧行删除、0服务重启/DDL。不能宣称本批无HTTP |

所有发送与模型开始均独占检查点；202/ack未确认先只读回查，不重复POST/publish。新topic/group、测试行及失败现场保留，不清全库/卷或改旧offset。备份和回退定义不代表本批演练恢复；旧预算批已验的项目备份恢复仅按原版本证据引用。

## 执行顺序与停止条件

1. 冻结本卡、输入/独立rubric、operator hash和资源上限，核当前运行与C03-01收尾一致，保存基线/备份；准备新操作key、原子更新受控policy并核原五预约不变。
2. 每例开始前独立记录fused末尾坐标，单次HTTP ingress；捕获匹配的真实Fusion信封与PG/API结果，保存完整首次材料/hash；源fused.alert.created_at与PG alerts.created_at入行时间分别记录，不要求二者相同。无匹配、非预期消息或结果不确认即停，不重发。
3. 用同一信封、当前v3和五reader预检实际完整prompt与SDK body；在独立进程使用MockTransport、无Invocation/claim、CostTracker persist=False，明确0真实模型/Run/预约/成本写入。保留生产egress处理；只保存body，绝不保存Authorization。A材料不得夹带评分元数据，B既有组织背景中一个Synthetic标记透明保留，不将其当分类依据；不编辑旧资料消除标记。
4. 预检通过后单次复制至quality topic，显式初始offset0。fresh实际worker按当前main的BusinessContext/默认Live writer及shadow policy运行，不以关闭原策略提高成绩；实际PG claim/预算/SDK调用与持久确认均走生产路径。保存真实SDK egress body、选定的短回复content/usage/finish reason；不收集隐藏推理、完整provider body或秘密headers。
5. 单例完成并停止临时进程后，核输入→消息坐标→实际prompt/来源→原短回复/最终verdict→Run/events/artifacts/成本/预约及owner API关系。由未实现该批的审计者核原始回复schema和理由，写绑定输入/输出hash的独立通过gate，才运行下一例；不自动循环四次。
6. 任意预算/来源内容或状态变化、长度超限、provider不确认、持久失败、格式错误或理由不受支持即停止后续例，保留当前新Run/预约/offset。不能用生产修JSON、normalize、clamp或fallback后结果抵消原回复质量失败；无第二请求。
7. 所有已执行例结束后做最终独立运行/数据审计，撤新操作key并核拒绝，更新回执/PROGRESS。仅四例全部通过才满足本批质量退出；否则记录实际失败并另立后续最小修复，不覆写旧结果。本批不启resident、不处理主group起点。

## 独立质量判据

原短回复须符合当前JSON/schema：verdict为五个合法枚举，confidence为非bool有限数且在0..1，rationale为短文本；额外字段照原合同记录，不擅自扩schema。分类与理由分别评分，不因分类命中即通过。理由不得捏造查询、授权、拒绝、端点、时区或动作/账户/目标范围；在职/职位、组织习惯、旧意见及缺匹配job不能独立证明本次批准或从未批准。

完整端点允许比较时，offset/跨日及窗内外计算必须正确。授权例须体现发生时刻等价16:10Z在15:55–16:25Z内且范围匹配；反例须体现发生时刻02:20Z早于02:45Z，created_at 02:55Z不能代替发生时间；允许等价时区表述，不能只说authorized或needs_review。窗外只排除所供窗口，不能独立证明恶意或所有授权不存在。未知端点/时区/范围应保留证据缺口，直接破坏行为则可依据行为支持升级。

准备盘点中的三次observer失败与第四次成功、PG确认33/上界40及context HTTP确认30/上界60均保留为设计历史；其v2长度投影不是本批实际v3预检证据。中性查询仅组织记忆非空，其余来源有认证但无匹配，不称全部来源非空消费/引用质量通过。B的Synthetic背景限制单列，评分必须基于确切行为/时间/授权依据，不能靠测试标记得分。
