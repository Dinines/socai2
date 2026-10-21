# 3A-10-02：普通分诊首次结果与重投保护

状态：**3A-10-02限定验收通过，已部署21。** 批次`3a-triage-recovery-20261020`，实际结果见[回执](3a-triage-recovery.md)及[机器记录](3a-triage-recovery.json)。承接[可靠性总计划](3a-worker-reliability-plan.md)、[上批部署](3a-triage-durability.md)及3A-09已冻结缺陷证据。只处理Kafka普通分诊的冷重投、同一Run并发与保存恢复；常驻worker、自动graph、审批、记忆写回和真实响应仍关闭。0次真实模型调用，没有重做质量评分。

## 固定合同与来源

- 保留固定workflow版本及run_id算法，不通过换版本绕开旧Run。Kafka入口的live writer路径先查询持久Run，再进入业务规则、缓存、reader或模型；直接`triage`、历史replay及纯shadow writer保留原入口合同，不据此宣称所有入口都具备新保护。
- 查询按Run ID发现冲突，再严格核tenant、canonical alert、raw alert和自动分诊路径。已完成必须有合法首次seq1 triage_verdict及一致的来源/工件；PG不可用、无pool、身份冲突、结果破损都明确失败，不能解释为未处理。旧完成Run只返回可证实的legacy投影，缺失的原incident、shadow、规则和动作结果不伪造。
- 新guard要求canonical UUID文本与固定workflow推导的Run一致；当前Fusion输出符合此合同。大写或其他非标准UUID文本失败关闭，不偷偷归一并改变历史Run算法，不外推所有旧生产者兼容。
- 普通分诊在业务规则/记忆抑制返回之后、governor/模型之前，使用现有Run主键事务认领，并追加seq=-1、kind=triage_started事件。该事件表示处理开始，不证明模型请求已发出。Run与事件同事务提交后才允许模型方法进入；不新增表、DDL、依赖或自动超时抢占。现库负seq及约束须在操作前只读核实。
- 跨进程仅认领成功者运行普通分诊。已有started/running/failed而无完整结果时视为unknown，停止自动调用并走确认DLQ；进程丢失不靠TTL重调。完整结果与开始状态分别保留，不把唯一Run或缓存称为模型恰好一次。
- 模型/确定性方法返回且groundedness gate完成后，在独立exact `(tenant, run_id)` 槽保存完整待持久材料：深拷贝state、五类读取、原tier、verdict/confidence、transcript、usage和CostSummary及原writer。最多128槽，满时在方法前失败。恢复只重试同一份保存，不重新取来源、过gate、改成cached零token或重做后续动作；进程退出后材料不可恢复则保留unknown。
- 新verdict附schema_version=1恢复投影，明确后续动作未重放；旧字段与五来源工件保留。开始Run在首次成功保存时采用真实tier的model_used。规则抑制沿3A-01独立持久合同，不创建普通claim，不将policy_decision当模型verdict。

保存前的已发生usage/governor支出不删除或重复计入；本批以明确非零单元fixture及旧真实Run只读回查核usage保留，不伪造新的模型usage/成本。原生产SDK重试/超时仍留3A-10-03；unknown不得以自动重算恢复。

## 有界验收及恢复

基线为21四服务健康、Agents `24071dd2…aea1`、18 Compose层；58告警/29Run/78事件/82工件/21成本行，其他35容器、18卷、134迁移及十枚reader保持。先保存本批before源文件和旧材料hash；旧receipt/raw/topic/group不变。

复用上批有效八个原suite和直接新增关键边界，不默认全仓矩阵。真实验收仅使用新批次标记，最多3条新HTTP告警、8次独立broker发布、12次交付、6次方法替身、3个新Run、10个五来源工件，0次真实模型、0新增成本行。每个操作有独占检查点，未知先回查，不盲重发。

1. 同进程方法返回后真实工件SQL失败：claim仍存在，0首次verdict/来源工件；DLQ未确认保持offset。仅恢复保存后五类来源、原tuple与最终工件逐值/hash一致，reader/方法不再进入。
2. 新进程重复完成输入：在业务规则、reader、governor和方法前返回持久投影；Run、告警、事件、工件、shadow及成本全保持。另只读核旧真实非零usage Run的legacy恢复。
3. 两个独立进程/独立group处理同一新输入，制造实际重叠：仅一个认领并进入方法，另一个unknown或在完成后复用，不能以同group单分区串行替代并发证据。
4. 已提交开始意图后退出进程：新进程接同offset，0次新方法，unknown进入确认DLQ才提交，不自动重算。
5. 真实PG查询错误/恢复、tenant冲突及坏结果均不触新方法；恢复后取首次结果。测试故障只影响本批查询/事务，不宣称共享PG outage。

仅在有效测试及真实PG/Kafka边界通过后更新Agents；原env/五类受控只读挂载与worker OFF保持，API/Fusion/Actions不重建。保存原镜像和新顶层，单服务重启后核材料与身份。回退撤新增顶层，保留所有已写started/verdict/工件和消息，不删除未知Run或自动重放到旧版本；旧版本忽略开始保护，故回退后常驻消费继续关闭。

本批通过也不代表生产SDK预算、长期吞吐、rebalance、所有调查入口或完整质量通过。3A-09 p01理由缺陷保留，下一单项仍以实际结果确定。

## 实际完成

207项相关测试首轮全部通过，保留八个原suite与上批durability边界；仅两处旧测试补新port替身，原故障断言保持。修改worker和ledger两个运行文件，新增专用lookup/claim模块；固定模型prompt、依赖、评分、schema、env及五类挂载不变。实际PG只读核负seq为0、三表无CHECK限制，复用现有主键及追加事件，不执行DDL。

三条独立新告警均经过真实认证HTTP→SSL Kafka/Fusion→PG。六个独立topic、五个group实际3次发布/7次交付/3次方法替身，0真实模型与新成本行。真实工件SQL错误后保留1个开始Run/事件且0 verdict/来源工件，DLQ未确认offset0；同一worker仅恢复保存，完整tuple hash相同、五reader和方法未重入。新进程冷读完成结果时各接缝tripwire均未进入；两个独立OS进程重叠竞争只有一个进入方法。另一个进程在确认开始意图后退出23，新进程接同offset停unknown，确认DLQ后提交1，没有再进入方法。

真实PG查询除零→typed失败→仅恢复查询取原结果；跨tenant claim拒绝且无写。对旧真实Run仅直接lookup，1687个原tokens和原材料保持，没有worker重放或新调用。55项显式HTTP检查（6受理/轮询、49收尾）及同容器Agents重启回查通过；两份完成产品、五类工件和源告警人工状态保持。仅开始的未知Run保留原开始事件，不把其通用状态当可重试依据。

当前61告警/32Run/83事件/92工件/21成本行，新增3Run中两份完成、一份未知；旧14表材料hash、其他35容器、18卷、134迁移和十枚reader的原文件/metadata/scopes保持，三操作key均401。十枚reader保持不等于本批重启后逐一重做五类旧查询。Agents为`triage-recovery-3a-20261020`、镜像`sha256:f7737abde83d288702478806103cd011e4c1552c7851ad9c50e6d0410bcd4569`，使用19层Compose/17层源码；188份原始材料封存，各阶段首轮通过，无恢复重跑。

新增明确限制：默认完整事件查询返回seq=-1的开始事件；只有该事件时next_seq=-1，但当前API的since参数要求非负，实测`since=-1`为422，不能直接用该cursor长轮询。未知Run后续可由原reaper变为failed，该状态仍不授权重新调用。首次保存后的副作用不由completed复用补做，不宣称完整业务恰好一次。下一单项3A-10-03先限定SDK/请求/停止预算，并修正负开始游标后再讨论常驻准入；3A-09理由质量仍未通过。
