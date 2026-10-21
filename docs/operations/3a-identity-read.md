# 3A-08身份上下文读取回执

2026-10-20，批次`3a-identity-read-20261020`，**限定验收通过**。最终496项（API108/Agents388）、62项显式HTTP检查，图源读取/失败、实际采用、一次真实模型、账本与重启回查已核；五类reader已接通。完整HR历史、调查质量与常驻准入未通过。

字段/hash及失败记录见[机器回执](3a-identity-read.json)、[来源清单](../handoff/3a-identity-read-source-manifest.json)、[本地核验](3a-identity-read-local-verification.json)。来源差异为9个运行文件、4个原测试、18个新输入，无运行依赖或PG DDL变化。113份原始材料受控同步；完整prompt/回复/HR样例字段不在公开回执展开。[原计划](3a-identity-read-plan.md)不能替代实测。

## 输入 → 真实图/API → 采用

21 Neo4j5.15 Community本批前0节点/0关系，新增A/B共27合成节点/22关系；2 lookup索引/0约束保持，无Neo4j重启、全量目录导入或通用schema初始化。样例覆盖同账户不同tenant、跨tenant边/混合global标签、未关联员工、多provider/员工及导入时间边界；不含真实员工隐私。

旧Bearer/X头实际401。新GET graph/identity-context以Bearer/graph:read及tenant交集授权，每个Identity/Employee/部门/经理节点严格同tenant；A/B各读自身1条，越权/缺scope/匿名/坏key/X头和reader写ingress/context-import被拒绝。真实空集、无账户、Identity-only与多关联分别保留含义，不推断异常账户或活动授权。

专用配置按请求lazy READ_ACCESS连接，API仍AISOC_DISABLE_NEO4J=true。真实尝试写入被AccessMode拒绝、回滚后材料相同，但共享高权限账号不是数据库只读租户角色；原Bolt未新增TLS，不能外推其他图接口隔离。

native导入cutoff先过滤再limit：7候选→1可采用，晚3/不可核3，limit1仍得旧行。所有采用行仍计without_timestamp，表示业务历史未知。Employee stamp不等于HR生效日或完整关系版本；本批新部门/经理两属性v1→v2后，旧split也读当前值，明确无法重建旧HR路径。

## 失败、缓存与账本

专用配置移除实际HTTP200→503(graph_not_configured)→恢复200，生产worker投影为unavailable/无材料，不当正常空集。独立生产Cypher读取及探针替换的真实查询错误/同会话恢复另记，不称共享Neo4j outage或生产查询HTTP故障传播。

身份缓存默认300秒，先核专用映射，再绑定tenant/URL/凭据hash/accounts/limit/cutoff；撤销后有效缓存仍成功，TTL0刷新401/无stale、恢复后网络成功。禁用、缺配置、错身份与闭合URL失败分开记录；原四类仍各自120秒，不能宣称即时撤销或图编辑即时可见。

真实503回执经生产prompt投影保存于独立probe-only Run；工件INSERT处SELECT1/0使Run/事件/工件0/0/0，同Run恢复1/1/1，重复不追加且成本行0。失败投影没有调用模型。首次读取事件/工件与verdict事务保护不冻结通用Run/alert更新。

## 唯一模型与持久结果

一条R-IDENTITY-A / IDENTITY-HOST-A / svc-identity-a、无MITRE的合成已有告警，经真实HTTP→SSL Kafka→Fusion→无group/无commit捕获→生产worker→21网关→43。完整literal prompt6931字符≤保留的8000上限，身份1条的source ID/24字段投影hash、一次清理后的display/rendered文本/hash及advisory块与实际safe-call消息、writer输入和持久工件一致。

| 产物 | 实际结果 |
| --- | --- |
| 模型Run | `a79f8e23-2099-5a2d-9d02-64a2856773a0`，shadow/no actions |
| 回复/usage | needs_review，自报0.65；1646输入+135输出=1781 tokens，与Run/成本行一致，unpriced1/费用unknown |
| 其他来源 | org success；skill读取success但selection no_match，KB/近期处置no_match；旧查询另核四类均success |
| 工件关系 | 模型2事件/7工件（五类读取+prompt/response），独立probe另1事件/1身份工件 |

模型精确提到账户及通用词service；其余显示字段未精确提及，不证明因果采用、推理依据或质量。节点ID未显示在prompt，ID提及0仅单列观察，不列失败；来源ID/路径与采用hash供工件追溯。未要求特定分类/引用，也未追加调用。模型与最终部署镜像相同。

## 失败恢复、收尾与限制

初API101及最终API108/Agents388均通过。首次after的新增探针成本查询把UUID绑定到TEXT run_id而DataError，此时无probe行、新输入或模型。仅修operator为字符串绑定，带六个旧检查点hash从已完成矩阵后恢复：复用原16项HTTP/矩阵，不再撤销key，再执行唯一ingress/模型。失败日志/结果保留，runtime/unit未改、无额外构建；初版operator未另存文件或hash，来源清单仅验证最终脚本，不补造初版备份。

API/Agents最终tag为identity-read-3a-20261020，digest及[十七层命令](../../deploy/aisoc21/README.md)见运行说明。仅这两服务更新/定向重启，其他34容器/18卷/134迁移保持；图全hash与history探针后的27/22快照相同。旧53告警/21Run/66事件/38工件/17成本行及旧知识材料保持，新增后54/23/69/46/18、shadow决策13。网关triage12→13、其他角色不增。

新增两枚A/B graph:read reader到期2026-11-19T10:31:59.338283Z、最终200，三操作key401；原八枚key/state/map/scope/env/mount保持。两处新专用目录UID/GID10001、0700/0600、只读挂载，位置与轮换见[配置索引](configuration.md)。重启后非root五类读取及原工件一致。

回退先停相关输入/消费者、核已受理队列并保留图/PG/工件，只撤最上层identity-read恢复3A-07镜像及两处专用env/mount，保留旧四读取层/身份；不清图/库/卷、不启通用初始化、不盲重发模型。下一[3A-09受控分诊复验与worker准入](3a-triage-admission-plan.md)仅规划；常驻worker、自动graph、审批、真实响应仍关闭，旧工具身份、事件/UEBA及完整知识/调查质量另验。
