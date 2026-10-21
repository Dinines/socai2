# 3A-10：分诊消费可靠性修复计划

状态：**3A-10-01、02、03-01及03-02持久额度/停止小边界已限定验收；完整质量与worker准入仍未通过；3A-11-01只读复核已完成，3A-11-02配置补齐已限定验收，下一单项为3A-11-03理由提示词修复（继续禁用worker），见文末最新补充。** 03-02见[范围](3a-triage-budget-plan.md)和[回执](3a-triage-budget.md)：263项测试、137项HTTP，真实Kafka/PG与HTTP模型替身；独立表原子预约、三类上限、同group积压恢复、10秒stop及未知不重调限定通过，0真实模型。03-02当时21层、仅Agents新镜像/一policy挂载，134原迁移保持。 03-01见[范围](3a-triage-request-plan.md)及[回执](3a-triage-request.md)：189项测试、71项显式HTTP，0真实模型；生产triage SDK默认retry0/timeout45及整次45秒截止、-1 cursor已部署。整个03与worker准入仍未过。 首批见[持久确认回执](3a-triage-durability.md)。02范围见[执行卡](3a-triage-recovery-plan.md)，实际结果见[回执](3a-triage-recovery.md)：207项测试、真实Kafka/PG跨进程边界与55项显式HTTP通过，0次真实模型，仅更新并重启Agents；完整worker准入仍不通过。承接[3A-09受控复验](3a-triage-admission.md)，实施以实际回执和失败现场为准。不改变已冻结分类或来源材料，不把三例分类匹配当作完整质量通过。目标仍是已有告警及后续处理服务端。

3A-09已完成三个固定新告警的真实模型调用；恶意样例分类符合判据，但理由把11:01行为误写为位于02:00备份授权窗口。该错误保留为质量阻塞，不能以正确分类抵消，也不靠追加调用改善本批成绩。后续质量复验需单独固定时间/授权冲突样例；本计划先处理会丢消息、丢账本或重复花费的消费可靠性边界。

## 实施分批与验收

| 子项 | 拟限定修改与实际验收 |
| --- | --- |
| 3A-10-01 持久失败与坏消息（限定完成） | live writer仅接受ledger明确`True`；已解码信封非法或无处理结果进入schema DLQ，持久失败进入persist DLQ，未确认不提交。tenant/canonical仅校验UUID格式及两处tenant一致，未知来源保留null；不证明PG归属，不覆盖wire非法JSON。已实测未知UUID进入方法后PG FK失败；普通成功保存五类来源工件。旧静默损失事实保留，不宣称冷重投/缓存恢复已修。 |
| 3A-10-02 重投与调用结果保护（限定完成） | 普通live Kafka入口按tenant/alert/workflow核首次verdict、Run及来源工件，完成时只读早返；旧记录透明legacy投影。无pool、PG失败、身份/工件破损不当miss。现有Run PK及seq=-1开始事件同事务认领，无DDL/自动抢占；真实跨进程只一方法进入，退出后重读unknown进确认DLQ。开始事件不证明模型请求发出；direct triage/replay与policy/memory抑制分支仍是原独立合同，不宣称完整业务恰好一次。 |
| 同进程保存恢复（02限定完成） | gate后完整state/五来源/transcript/原tier/CostSummary/usage按exact Run保留，最多128槽。真实工件SQL失败后仅恢复同份保存、tuple hash一致，reader/方法不重入；进程丢失未落库结果仍unknown，不自动重算。旧非零usage只读核1687tokens保持；本批真实方法替身不伪造新usage。 |
| 3A-10-03 调用/停止预算 | 明确生产实例SDK与网关的重试、请求超时、并发、单tenant调用/tokens上限、积压和停止恢复。3A-09仅探针构造实例retry0/45秒；当时生产SDK根client为retry2、timeout None，不能据探针声称生产已受限。明确失败/unknown的额度消耗，费用unknown保持unknown。 |

每一子项先以当前版本重现直接缺陷，再改最小运行路径并补有效测试；保留固定上游/运行依赖，不顺带重写prompt、判据、图模型或知识存储。不删除旧Run/工件、topic/group或共享数据。新的返回合同须区分已持久结果、模型调用已开始但未确认、保存待恢复、坏消息和缺失来源。

## 对应真实边界

沿用3A-09独立tenant与新topic/group思路，但另用新批次标签和新对象；不重置其已冻结group或重放其三条真实样例。以模型方法替身及真实PG/SSL Kafka验证：

1. 无pool/ledger False和真实工件SQL错误均不产生“已成功”回执；无DLQ确认时offset保持，确认后才前进。
2. 坏schema有明确DLQ，tenant/源身份未知与可识别tenant分开；失败不能被吞为正常空集。
3. 暖重投、冷进程重投及相同输入并发只采用已持久首次结果，替身计数不增加，Run/事件/五类工件/usage关系保持。
4. 模型方法已返回后保存失败，恢复不再次进入模型方法；首次结果的确切来源文本/hash、预算和usage不丢失。若在进程退出后只剩调用开始意图，应停止而非自动重算。
5. 同group无新增输入的停止/恢复不增加处理或调用；限定单分区结果不外推rebalance、高可用或长时间吞吐。

这些可靠性修复优先不新增真实模型调用。需要新增模型、修改schema或改变已有读写语义时，先明确本子批输入/差异/预算/验收和恢复边界，旧证据保持。运行源码改变后复用直接受影响的有效上游测试和本批关键边界，不默认全仓慢速矩阵。

## 退出与后续

交付须包含最小来源差异、正常路径及每个失败/恢复的真实broker/PG坐标、首次与重投产物对比、调用额度与未解决限制。即使可靠性小边界通过，也不自动开启常驻worker；逐tenant凭据、来源可靠性、默认缓存撤销延迟、预算/积压与停机恢复仍需明确。

3A-09理由时间矛盾、完整知识/引用质量、旧调查工具身份、缺失事件/UEBA和调查技能pin等另列质量或3B准入事项。本计划不扩展到前端、采集/检测或真实响应；自动graph、审批与真实厂商动作保持关闭。

02新增准入问题：默认完整timeline可读取seq=-1开始事件，但start-only返回next_seq=-1，现API since>=0拒绝该cursor（真实422）。03须同时明确/修正该增量读取合同。未知Run可被原reaper标failed，仍不能据状态或TTL自动重新调用；completed复用不补做首次持久保存后的副作用。当前19层运行定义见[21说明](../../deploy/aisoc21/README.md)，常驻worker继续关闭。

03-01补充：总表03调用/停止预算分步执行，先完成请求界限与cursor，没有实现持久单tenant调用/tokens额度。上段负cursor422为02当时事实，03-01当前-1已接受且-2仍422；旧证据不改写。当前20层仅API/Agents新增镜像，worker仍OFF；下一03-02先明确失败/unknown的额度保留、跨进程并发与积压/停止恢复，再做限定真实PG/Kafka验证。

03-02实际补充：每次20000固定预留单位是保守准入合同，不是实测usage/费用或任意厂商绝对token上界；仅配置A/B普通live路径。保留三未知预约和A group offset0/end1，5预约共100000单位，实际usage仍null。operator失败、两次受控镜像更新、明确额度调整均保留，不能写成首轮全通过。下一先只读核准入剩余阻塞及p01时间/授权理由修复范围、实际材料/工具身份与未知/积压处置合同，不自动开常驻、重放unknown或追加真实模型。

## 3A-11-01最新只读准入复核

3A-11-01只读准入复核已完成，见[回执](3a-admission-review.md)：旧p01时间/授权错误未被indicator gate识别；常驻Agents审批提案guard实际True且缺Kafka bootstrap/TLS，旧调查工具身份仍缺。三未知预约及A积压保持，0模型/消息/offset提交/运行改动；完整准入未过。下一[3A-11-02配置补齐](3a-triage-admission-config-plan.md)，保持worker禁用，然后单独修提示词/复验质量。

审批提案guard未显式禁用、常驻Agents缺Kafka bootstrap/TLS；worker关闭使其未作为常驻消费者运行，隔离探针通过不证明这些环境项已接。五reader不替代旧工具service身份。旧回执保持；本批无运行改动，三未知预约及A积压不清理/重调。

## 3A-11-02最新配置验收

3A-11-02常驻分诊配置补齐已限定验收，见[回执](3a-triage-admission-config.md)：仅Agents同镜像重建一次，新增四项环境值，复用原只读CA；审批提案guard现False、Kafka SSL/主机名校验及六组offset读取通过。旧14表/三unknown/A积压/十reader/其他35容器/18卷/134迁移保持，0模型/消息/提交。当前22层、19源码层，worker仍OFF；下一[3A-11-03理由提示词修复](3a-triage-reasoning-plan.md)，完整准入/质量未过。

当前补齐的是transport及审批提案禁用，不含常驻topic/group/DLQ项目映射；五reader与通用工具身份仍分开。A积压与unknown不清理/重调；p01理由仍未修，不能将配置就绪当质量或常驻准入。
