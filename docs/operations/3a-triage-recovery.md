# 3A-10-02：普通分诊首次结果与重投保护回执

状态：**限定验收通过，完整worker准入与分诊质量仍未通过。** 批次`3a-triage-recovery-20261020`，范围见[执行卡](3a-triage-recovery-plan.md)与[总计划](3a-worker-reliability-plan.md)。实际结果见[JSON](3a-triage-recovery.json)，文件/hash见[来源清单](../handoff/3a-triage-recovery-source-manifest.json)；188份受控raw含三条入口子目录已逐hash封存。测试、部署、broker与收尾均按预定首轮通过，无失败恢复或重跑。

本批新增`workers/triage_delivery.py`并修改worker与ledger，不新增DDL、依赖、prompt或workflow版本。Kafka普通live入口先查可核的首次完成Run/verdict/来源工件；普通新处理在抑制分支之后、governor/模型之前，事务认领Run并写seq=-1 `triage_started`。开始事件只表示处理开始，`model_invocation_established=false`，不能当真实模型请求记录。已有started且无完整结果保留unknown，不靠TTL抢占或自动重调。

## 输入到实际结果

三条新合成已有告警经认证HTTP→SSL Kafka→Fusion→PG，各一次POST202/最终poll200，共6项入口HTTP检查。随后只向本批6个独立topic、5个group发布三个真实捕获信封；group隔离、原信封/hash和实际offset均保留。模型方法为明确替身，无真实LLM请求、伪造exchange、usage或新增成本行。

| 场景 | 真实处理与最终关系 |
| --- | --- |
| 同worker保存恢复 | 方法返回后在实际来源工件INSERT处执行除零；事务回滚只保留claim/start、0 verdict/来源工件，DLQ未确认时offset0。同一worker恢复仅保存原材料，offset1；两次完整persist tuple/hash相同，五来源工件=事件payload=原读取，无reader/方法重入 |
| fresh进程复用完成结果 | 新OS进程/新group读取完成输入，在业务规则、governor、reader、方法及保存前返回首次投影；Run/事件/来源工件/告警/shadow/成本全值保持 |
| 跨进程实际重叠 | A认领后在方法holding，另一PID/B group进入同信封得到unknown并确认DLQ；B退出后才释放A。只有A进入方法，最终一份完成结果及五来源工件 |
| 开始后退出 | 子进程方法入口已能回读提交的seq=-1，再按预定exit23。fresh进程接同group/offset，0次新方法，unknown确认DLQ后提交；无verdict/来源工件，开始事件保持 |

共3次发布/7次交付/3次方法替身、0真实模型。warm原五类状态为组织记忆success、技能success、KB no_match、近期处置no_match、身份success；恢复不重新取源或按cached零token改写。正常两Run各有start/verdict两事件及五工件，一unknown只有start，合计3 Run/5事件/10来源工件/2 shadow决策。

另对生产lookup真实SQL查询注入服务器除零：typed失败不能当“未处理”，恢复查询后取原结果；跨B tenant claim被拒绝，PG材料不变。旧3A-09 p01只调用只读lookup，原1687 tokens/unpriced1、费用unknown及全部材料保持，没有worker或模型重放。legacy缺少的workflow、incident、shadow、规则、模型名等字段明确unknown，不伪造完整原结果，也不修改原理由缺陷。

## 验证与部署

207项窄测试首轮通过；55项显式HTTP=6项入口+49项收尾，包含API来源工件/隔离/权限、重启前后产品及三操作key撤销。故障注入、并发unknown和exit23均为固定验收输入，来源证据与真实模型质量分开记录。

只更新Agents为`socai2-agents:triage-recovery-3a-20261020`，image ID=`sha256:f7737abde83d288702478806103cd011e4c1552c7851ad9c50e6d0410bcd4569`，精确父镜像24071dd2。API仍identity-read的6c5f212b，Fusion仍risk-score、Actions仍1G；19 Compose层/17源码层，完整命令见[21说明](../../deploy/aisoc21/README.md)。原env、五类只读挂载和worker OFF保持，仅Agents更新并完成一次同容器重启。

两完成Run的API整产品在重启前后相同，默认事件时间线可读[-1,1]；unknown时间线只有[-1]、start不变，本次重启后仍running。旧58告警/29Run/78事件/82工件/21成本行及14表材料保持，新增后61/32/83/92/21、shadow21；35其他容器、18卷、134迁移保持，网关计数不增。原十枚reader文件/hash/metadata/scopes保持，未重测十枚各自旧查询；三操作key最终401，受控位置见[配置索引](configuration.md)。

## 保留限制与下一项

显式`events?since=-1`真实返回422；负开始事件的增量cursor仍是准入限制。unknown即使以后由reaper从running标failed，也不能据此自动再次调用。完整待持久材料仅保存在同一worker的最多128槽中，进程退出后不能把缺失结果当未开始；这不是模型恰好一次或跨进程结果可恢复保证。

保护只适用于Kafka普通live分诊；direct triage、历史replay、纯离线shadow及原policy/memory抑制分支保持原合同。没有重放后续审批/响应/写回，也不外推长期吞吐、rebalance或完整调查。下一3A-10-03处理生产SDK/请求/停止预算及负cursor；3A-09 p01时间/授权理由质量未重测。常驻worker、自动graph、审批、记忆写回和真实响应继续关闭。回退保留全部started/verdict/工件与消息，不删除unknown Run或自动重放到忽略开始保护的旧版本。
