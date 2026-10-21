# 3A-10-01：普通分诊持久确认与坏消息

状态：**3A-10-01限定验收通过，已部署21。** 批次`3a-triage-durability-20261020`，实际结果见[回执](3a-triage-durability.md)及[机器记录](3a-triage-durability.json)。承接[3A-09实测](3a-triage-admission.md)及[可靠性总计划](3a-worker-reliability-plan.md)。本批只修静默成功/提交，冷重投、缓存保存恢复丢来源和生产SDK预算仍按后续子项处理；常驻worker、自动graph、审批与真实响应保持关闭。

## 固定变更边界

- 仅修改Agents的`workers/fused_alert_consumer.py`和`workers/triage_persistence.py`及直接受影响测试。原`ledger.persist_auto_triage`的bool合同、SQL、依赖、prompt/lock及评分不变。保存本项目当前两文件及原测试before副本和hash，新增差异单独接在既有15层运行源码后。
- `LiveTriageWriter`仅接受ledger的明确`True`，False、None或其他值均为持久失败。独立离线`ShadowTriageWriter`的None合同保留，不能在任意writer端口上强制True。数据库未配置和未确认tenant不再被live调用者当正常成功。
- 严格格式校验只在Kafka消费者`_process_with_retry`入口，先于业务规则、reader和模型。要求有效alert对象、显式UUID tenant及canonical alert标识；tenant两处提供时须一致；alert按现有`alert_row_id→envelope.id→alert.id`优先级，选中无效不偷偷换目标。source-v1的canonical与内层上游ID可以不同。保留直接`triage`及纯`build_state`供历史replay使用的合同，不能以本批宣称所有入口都新增校验。
- 非法格式及无处理结果仅一次schema DLQ，不通过重试把坏消息当成功。DLQ保留解码原值、可核格式的tenant/canonical标识和可用来源，无法判定的字段保持unknown/null，不生成default tenant或随机Run。DLQ无确认则失败并保留offset。

格式校验不证明tenant在PG存在、alert的数据库归属或上游真实性。一个格式正确但不存在的tenant实际先进入分诊方法替身，最终由真实PG FK失败→持久DLQ；本批实测这个限制，不宣称它在模型前已完成数据库授权。测试坏消息均已JSON解码；`value_deserializer`中的非法wire JSON未纳入本批修复或真实验收。未知调用结果仍不自动重发。

## 输入及验收上限

复用A/B测试tenant及现十枚五类reader，三枚新操作key三小时，结束撤销。部署前核四镜像/已有36容器/18卷/134迁移、旧57告警/28Run/77事件/77工件/21成本行及知识材料hash；不重放3A-09的topic、输入、Run或评分材料。

1. 旧固定Agents镜像只做两条新before broker样例：坏schema、记录阶段无pool的False持久结果；保存原静默commit事实，0真实模型。
2. 新固定镜像做五条after broker样例：坏schema、缺全部alert标识、格式正确的未知UUID tenant、no-pool False、正常持久。no-pool先注入DLQ不确认保持offset0，再仅恢复DLQ确认，读取同offset到1，不重新发布输入。
3. 正常样例另有且仅有一次新认证HTTP ingress→SSL Kafka/Fusion→PG；先捕获实际fused，再向独立broker topic发布供生产worker处理，核正常verdict/五类来源工件、API读取、tenant/scope拒绝和手工状态。模型方法仅受控替身，无LLM exchange或伪造模型prompt/response，不计质量样本。
4. 每类独立新单分区topic/group及DLQ，共14个topic/7个group，最多7次broker发布/8次处理/8次模型方法替身，最多1个新正常probe Run、1事件、5来源工件、0成本行、0真实模型调用。消费后同group短时恢复无新处理；所有开始/发送/受理检查点独占创建，未知先回查，不盲重发。

只重建并更新Agents，在既有十七层后增加第十八层，原env、五类只读挂载和worker OFF保持，API/Fusion/Actions及其他35容器不动。缓存精确父镜像`sha256:dd64bd753333f1cf705225534b1d0a2430fa43ff38f06a1196f39c67b709e645`，构建不拉取/升级依赖。先用缓存测试镜像跑worker、writer、ledger/replay的直接影响面及新增关键边界，保留失败尝试与真实/替身区分。

## 退出及恢复

通过须有2文件最小来源差异、最终实际测试输入hash、before→after的真实broker offset/DLQ坐标、PG成功/失败材料、API关系、key生命周期、旧材料保持及Agents重启后回查。本批即便通过也不扩大为worker常驻准入或完整分诊质量。

失败先停本批探针，保留topic/消费组/PG材料与未确认offset。回退只撤新增第十八层恢复旧Agents镜像，保留env/挂载/数据；旧镜像有已知静默提交缺陷，回退后继续关闭常驻消费。修复后的DLQ/原消息不自动重放到旧版本。

## 实际完成与限制

- 两个运行文件与三个直接受影响原测试形成新增第16层源码差异；无SQL、依赖、prompt、评分或凭据映射变更。最终143项直接测试通过。首次136通过/7失败是新增测试替身未满足既有配置/生产TLS合同，原失败、当时测试源码及hash保留；仅改新替身后通过，运行源码未随测试恢复改变。
- 真实SSL Kafka/PG使用7次独立发布、8次交付、4次模型方法替身，0次真实模型调用。旧版本两个新样例复现静默提交；新版本坏schema/缺ID进入schema DLQ，未知UUID tenant实际PG FK失败进入persist DLQ。no-pool且DLQ未确认时offset保持0，仅恢复DLQ确认后同offset重读并提交1。正常样例通过真实HTTP→Kafka/Fusion→PG后进入独立worker探针，生成1个probe Run、1事件及五类来源工件；不计模型质量。
- 26项显式HTTP检查及Agents同容器重启回查通过；全部旧14表材料hash、十枚reader、其他35容器、18卷、134迁移保持。当前58告警/29Run/78事件/82工件/21成本行，三操作key均401。本批模型tokens及新增成本行均0，旧模型账本保留。
- Agents更新为`triage-durability-3a-20261020`，镜像`sha256:24071dd2817c34cc7108f38ae931cee43a831c3c5f01f49a65812fb87f51aea1`，使用18层Compose。原部署脚本在构建/单服务更新已成功后，因`Config.Env`列表顺序断言失败；保留原脚本/失败记录，核env值及挂载相同后以`verify-existing`只读恢复，没有再次构建或重建。之后仅作计划内一次Agents重启验证。
- 冻结138份原始材料。短时同group恢复未处理新消息，不代表冷重投、并发认领、rebalance或长期负载通过。冷重投模型方法重入、暖保存恢复丢来源、通用Run可变及生产SDK预算仍未解决；3A-09理由时间矛盾未重测。下一单项为3A-10-02持久首次结果与来源保护，完整worker准入及完整质量继续不通过。
