# 3A-10-03-02：持久分诊额度、积压和停止恢复回执

2026-10-20，批次 `3a-triage-budget-20261020`。**本批限定边界通过，常驻worker与完整质量准入仍未通过。** [执行范围](3a-triage-budget-plan.md)、[机器记录](3a-triage-budget.json)、[来源差异](../handoff/3a-triage-budget-source-manifest.json)。263项直接相关测试、137项显式真实API HTTP检查；真实SSL Kafka/PG中6次发布、14次交付、5次HTTP模型传输替身开始，真实模型0次。

## 实际修改与合同

旧版本探针实测：原governor累计5个合成tokens后，新实例为0；其check在token超过配置上限后仍allow。旧worker.stop返回时仍有1个未完成子任务。原证据保留，没有以美元governor或上一批SDK0/45代替持久额度。

新增独立表 `socai2_triage_budget_reservations`，原134份上游SQL/迁移登记不变。项目库934592字节custom备份保存在受控private，在独立临时库恢复并核对旧14表材料及134迁移，核对后仅删除该临时库，再执行一份项目增量SQL。新增表由aisoc持有、RLS/FORCE RLS、3个索引；quota字段及已结算行不可变。没有runtime建表逻辑。

五份旧运行文件及一个新增额度模块：

- 普通Kafka live路径在原completed复用之后决定是否走LLM。确定性、governor缓存及原policy/memory抑制不预约；direct triage/replay及其他角色/HTTP/stream不据本批扩张。配置文件存在时缺tenant、坏配置失败关闭；未配置文件的旧部署保留原合同。
- LLM的Run/start和额度预约同事务提交。tenant advisory lock后以新READ COMMITTED快照核滚动调用数、固定预留token总额及所有未结算预约。按tenant统计跨policy版本，不以换文件hash清账。额度claim拒绝/PG失败不留下Run或预约，BudgetHold不重试、不进DLQ、不提交offset，消费窗口停止。前置首次结果lookup的失败/unknown仍按3A-10-01/02持久错误与确认DLQ合同，不宣称全部PG错误均走新BudgetHold。
- 调用数计获准LLM尝试，每次固定预留20000个准入单位；这不是实际usage或费用。出站规范消息JSON最多16000 UTF-8字节、输出512、SDK0/45、同一Invocation只允许一次请求；受此上下文约束时禁用通用纯文本response cache。未启新上下文时原cache保持。模型厂商忽略参数或不同tokenizer不属于绝对实际token上界保证。
- 请求前持久保存意图，意图不证明远端收到。响应返回后记responded及可证实的usage，usage缺失为null；解除该预约未确认占位但不退还额度。明确LLM输入合同拒绝可记no_request；其余未确认、超时、取消、崩溃或确认保存失败保留额度和未结算占位。占位不因窗口到期、TTL或Run被标failed自动释放。
- stop阻止新处理/新请求，关闭consumer、给任务10秒保存宽限，再取消并join子任务，最后关闭DLQ producer。主消费退出清理子任务，lifespan等待主task退出。只覆盖本批协作取消路径，不宣称任意不响应取消的第三方代码、rebalance或全局严格10秒停机上界。

## 输入到实际产品与关系

六条标记告警均由认证HTTP受理，经真实SSL Kafka/Fusion写PG，再捕获信封；五条首批输入冻结在inputs.json，第六条补充保存在inputs-extra.json，没有修改原五条。输入为合成访问告警，不是生产事件或模型质量样本。两个响应经过实际SDK/agent/prompt/parser及账本，但HTTP transport为替身；五类reader显式替身not_requested。成本记录接缝仅在probe中禁用，未向真实成本表伪造usage或费用。

| 样例 | 实际中间产品/调用 | 最终值与关系 |
| --- | --- | --- |
| b_done | B首个Run/start、20000预约、一次HTTP替身响应 | completed，seq[-1,0,1]、7工件；fresh group复用完整结果不新增预约或请求，即使当时B已到token上限 |
| a_unknown | 首次探针权限拒绝后同offset恢复；请求意图落库后operator断言退出 | 仅start、预约reserved/request_started非null，无响应工件；不重调，后续同group确认DLQ后offset1，额度保持 |
| a_done | 新独立进程请求开始；另一operator快速拒绝处理断言失败，容器退出 | 第二份仅start/未确认预约，保留并冷读至确认DLQ；未重发输入/请求，不能作为成功停机样例 |
| a_denied | 旧A未知占位及随后两占位均阻止新认领 | 0 Run/0预约/0请求，group offset0/end1保留为积压 |
| b_denied | B先因token上限拒绝且0 Run，明确增加测试token额度后同group进入HTTP等待 | 与独立b_extra进程真实重叠；后者仅因未确认并发上限拒绝。stop实测10.012917秒、0子任务、offset0，预约未结算；fresh进程无新请求，确认DLQ后offset1 |
| b_extra | 并发拒绝时0 Run、offset0/end1；明确调整测试并发额度后同group恢复 | 无重发消息，增加一份20000预约并收到替身响应，completed及7工件，offset1；先前未知预约完全保持 |

调用数另用真实PG、无Run的新a_denied及更严格独立Policy单独触发，其他token/未确认条件均允许，证明调用数判断；token边界B calls1<max3且unsettled0，只有预留额度不足；最终并发边界B已用2次/40000、上限3次/60000，只有未确认1→2超过当时上限1。两个独立OS进程的PID、owner pending和stop屏障均保留。

真实额度INSERT注入除零后，Run/start与预约全回滚；无pool直接claim、跨tenant claim拒绝且无新增。不是共享PG outage。实际runtime连接的跨tenant预算读取为空；额度字段UPDATE触发不可变保护、SAVEPOINT回滚，原行不变。结果复用、额度拒绝和未知恢复均没有新增HTTP模型方法。

最终policy仅映射A/B测试tenant，各为24小时、3次、60000预留单位、最多2个未结算。由operator明确分步提高测试额度，以保留失败产生的未知占位并完成剩余受控边界；所有旧预约/charge均未退款、删除或抢占。这些是测试配置，不是生产额度推荐。5份预约合计100000预留单位，其中2份responded、3份未结算，5行observed_tokens均null；不能写成实际花费100000 tokens或零成本。

## 保留、部署与失败事实

旧14表材料hash全部保持。新增6告警/5Run/9事件/14工件/2shadow，现67告警/37Run/92事件/106工件/21成本行、23shadow；新预算表5行。网关五角色计数保持，新增真实模型/usage测量/成本行均0。137项真实HTTP为12受理/回查和125收尾；包含scope/tenant/匿名拒绝、开始cursor、全部新完成工件及Agents重启回查。两份完成产品逐值保持；三未知start及预约保持。十枚reader原文件/hash/metadata/scopes及图配置保持、常驻五映射可读，没有重做十枚全部旧查询；三操作key最后均停用401。

仅Agents更新为 `socai2-agents:triage-budget-3a-20261020`，最终image ID=`sha256:ab6f563f65455d4f4bdf0b40f2373d5bf0e6b4303acc69795483a29419ce10f5`，父镜像d6b9c7bb。首次7a8db768候选后，明确补额度claim错误类型并复跑263项，再受控更新一次，未盲重建；最终再做一次同容器重启。API保持triage-request，Fusion risk-score，Actions 1G。仅新增policy环境变量和只读目录挂载，原env/五reader挂载保持。21层Compose、19层运行源码差异；35其他容器/18卷保持，固定依赖未变。

未将首轮失败改写为成功：

1. 旧baseline probe缺/app路径，修probe后只读重现。首轮unit有4个导入收集错误；改为lazy import，补三种新进程import顺序后263通过；预算错误类型修正后最终263再通过。
2. `--no-owner`恢复库由admin持有表，初次用aisoc身份校验被拒绝；保留原恢复库/备份，改为admin只读核对完成，无重复恢复或原库改写。
3. root probe丢弃全部cap后不能读取UID10001的0700 policy，生产常驻UID10001本身可读；probe仅对显式挂载补DAC_OVERRIDE，第一次broker交付未认领、未请求，恢复同offset没有再发布。
4. operator晚置断言及快速拒绝task检查导致两次并发阶段停止，产生的两条未知预约保留。修operator后用剩余已受理样例及第六条有界补充完成实际重叠和10秒stop，不重发未知请求。Rich失败traceback的locals在本批冻结前脱敏，保留原hash、尺寸、失败诊断与脱敏记录，不保留凭据明文；之后operator使用不含locals的结构化异常日志。旧批原件未改。

## 限制与下一单项

这不是完整worker准入或模型质量通过：调用/费用未知不自动退款，当前A积压和3个未确认预约有意保留，后续须明确裁定；没有自动清账或重调工具。只验A/B测试配置及上述短期PG/Kafka边界；自然24小时过期、长期吞吐、跨服务统一额度、真实provider失败/撤销、非协作取消、完整生产prompt/reader字节覆盖均未验。早于额度表的Run和direct/replay/graph等入口不纳入本表追溯或全局成本封顶。

下一单项为3A准入剩余阻塞复核：固定p01时间窗/授权理由修复范围，核实际材料与工具身份、当前未知预约/积压处置合同，再确定有界质量复验。常驻worker、自动graph、审批、记忆写回和真实响应保持OFF，不自动追加真实模型调用。

回退先停新输入/消费，保留额度表、全部预约、Run/start/verdict/工件/topic/group，撤最顶budget恢复triage-request Agents及原20层/env/reader挂载；旧镜像不执行本表约束，回退后常驻仍OFF。正常管理使用[二十一层命令](../../deploy/aisoc21/README.md)，不对共享库/卷做清理或回滚上游SQL。
