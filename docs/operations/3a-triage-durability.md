# 3A-10-01：分诊持久确认与坏消息回执

状态：**限定验收通过，完整worker准入与分诊质量仍未通过。** 批次`3a-triage-durability-20261020`，承接[3A-09复现](3a-triage-admission.md)，范围见[执行卡](3a-triage-durability-plan.md)。机器结果见[JSON](3a-triage-durability.json)，文件/hash与必要差异见[来源清单](../handoff/3a-triage-durability-source-manifest.json)；138份受控raw已封存。

只修改Agents的`workers/fused_alert_consumer.py`与`workers/triage_persistence.py`，另适配三个直接成功测试替身。live writer只接受ledger明确True，False/None等均为持久失败；离线shadow writer的None合同保留。严格格式校验在Kafka入口、先于业务规则/reader/模型，选定canonical UUID无效不能偷偷换目标；直接`triage`、纯`build_state`及历史非UUID finding回放合同保持。没有依赖、SQL/schema、评分或prompt变更。

## 输入、实际处理与结果

一次A租户认证HTTP受理已有合成告警，risk_score显式null、无MITRE，规则`R-DURABILITY-A`、主机`DURABILITY-HOST-A`、用户`svc-identity-a`。202只表示发布受理；随后PG-backed API一次轮询200，独立SSL Kafka consumer从三个分区end offset开始，以group=None、0 commit捕获相同canonical告警：`socai2.alerts.fused`分区0/offset22。完整信封与原消息字节hash/坐标保留，匹配后再观察2秒只见一条，不外推无限去重。

该真实Fusion信封随后作为正常样例进入独立新broker topic，由生产worker处理。模型方法为明确替身，读五类真实来源，产出一Run、一verdict事件、五个来源工件及一shadow决策；工件内容/hash与事件payload、实际读取状态一致，0 prompt/response工件、0新成本行。没有真实模型调用，也不将替身needs_review当作判断质量。

| 新独立broker样例 | 实际结果 |
| --- | --- |
| 旧镜像坏schema、no-pool | 各自无DLQ却commit1；后者ledger False、PG零行，原缺陷保留 |
| 新镜像已解码坏schema、缺全部alert标识 | 模型方法/reader前拒绝，schema DLQ得到真实确认后commit1 |
| 新镜像格式正确的未知UUID tenant | 已进入模型方法替身，随后真实PG FK失败→persist DLQ确认→commit1，PG零行 |
| 新镜像no-pool、DLQ未确认 | offset0、PG零行；不重新发布，只恢复DLQ确认，pool仍None，同一消息到offset1 |
| 新镜像正常信封 | 实际PG材料与五来源关系通过，commit1且无DLQ，源告警手工状态保持 |

共14个独立topic、7个group，7次发布/8次交付、4次模型方法替身、0真实模型。无pool及DLQ不确认是明确注入，不是共享PG/broker outage。有效UUID不证明tenant存在、告警数据库归属或业务授权；未知tenant先方法后FK的限制已实测。坏消息边界是已JSON解码schema，不涵盖非法wire JSON。

## 验证、部署与保留

143项窄测试通过，使用缓存测试镜像、network none和只读源码；八个原suite及新增durability测试覆盖worker/writer/ledger/replay直接影响面。初次136通过/7个新增替身失败保留，仅修新增测试后重跑，期间运行源码未变。

只更新Agents为`socai2-agents:triage-durability-3a-20261020`，image ID=`sha256:24071dd2817c34cc7108f38ae931cee43a831c3c5f01f49a65812fb87f51aea1`，精确父镜像为原identity-read的dd64bd75。API仍6c5f212b、Fusion仍risk-score、Actions仍1G。当前18 Compose层、16运行源码层，完整命令见[21操作说明](../../deploy/aisoc21/README.md)。env、五类只读挂载、依赖及worker OFF保持。

首次部署已完成构建/重建，随后因Env列表顺序断言失败停止，原脚本/log保留。排序hash与挂载核验相同后只读`verify-existing`恢复，没有再次构建或重建。最终做一次同容器Agents重启：Run/事件/工件/API和手工告警状态保持，同group一秒idle无新交付，不外推崩溃、rebalance或长期运行能力。26项显式HTTP含1次ingress、1次最终poll及24次收尾检查；十枚原reader及各自原查询保持，三枚操作key最终401。

旧57告警/28Run/77事件/77工件/21成本行和14表旧材料保持；新增1告警/1Run/1事件/5工件/1shadow决策，当前58/29/78/82/21、shadow19。35其他容器、18卷、134迁移保持；网关各角色计数不变，没有追加模型或成本行。受控位置见[配置索引](configuration.md)，不公开凭据。

## 仍未通过与下一项

冷进程重投仍可能重入模型方法，暖恢复仍可能丢五类来源或改通用Run；生产SDK重试/超时及调用预算未修。3A-09 p01时间窗和授权过断言没有重测或改写，整体质量保持未过。下一单项为3A-10-02持久结果与来源保持，见[可靠性总计划](3a-worker-reliability-plan.md)。常驻worker、自动graph、审批与真实响应继续关闭；回退仅撤新增顶层并保留数据，未知/已受理消息不自动重发。
