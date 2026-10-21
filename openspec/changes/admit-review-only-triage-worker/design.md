## Context

继承[原R02执行卡](../../../docs/operations/c03-review-only-profile-plan.md)和[R01回执](../../../docs/operations/c03-triage-review-only.md)，以R01已验镜像与来源为候选。R01的191项断网测试不证明本profile真实main、PG/Kafka/reader分支已验；旧自治质量仍失败。本设计是待冻结执行计划，不是新的执行批准或完成证据。

## Goals / Non-Goals

目标是把所选两条新告警的原建议/effective关系、真实有界消费及同Run恢复验清。无需产品源码、DDL、依赖或新build；不处理旧积压、不重调unknown、不开放永久常驻，不把C04工具/报告或C05知识质量移入本批。

## Decisions

1. 沿用原卡A/B各一条新输入，最多两次实际SDK发送、最多40000预留单位，继承retry0/45秒及单次输出合同。具体输入、model route/prompt/reader/policy/source hash由发送前绑定产物固定；不复用旧质量例。
2. 停worker后记录main fused各partition当前end；原main commit/全部旧group/DLQ先只读快照。仅新operational group显式设冻结end，不改旧组起点。通过本批入口物理输入约束控制窗口，不能证明只有两条时不启用；不为此新建通用allowlist产品功能。
3. 通过真实服务main启动同R01镜像；启动前按原卡recreate并核实际policy bind字节/device/inode、profile/group/source。启动、恢复、最终OFF分别所需的同服务配置/recreate次数须在operator冻结时具体列明；不二次build。
4. 分别核模型可见材料、五类reader实际采用、raw/effective/usage和canonical Alert全字段保持。无成功回复不得将fallback包装成模型建议；模型内容正确与否不替代本profile隔离，也不解除原自治质量门。
5. 定向故障只作用本批连接/consumer，不停止共享PG/Kafka；核保存/确认失败不跨offset、warm恢复及一次fresh进程完整首次结果复用。若请求发出与否不明就停为unknown，不追加SDK以追求恢复成功。
6. 操作key撤销并真实401，最终OFF、无任务/inflight及旧状态保持后由独立审计者核实。只在此后完成tasks和归档；回执继续存原项目文档结构，OpenSpec链接它们。

原R02卡的具体上限继续约束本change：A policy为86400秒/10calls/200000单位/3unsettled，B为86400秒/4calls/80000单位/2unsettled；不增额、不自动重分配，发送前按真实DB时钟和全部旧预约重核，余量不足即停。A一次+B一次，新tenant/reader/closure policy为0，操作key每tenant最多1枚。保留旧12预约/240000单位/3unknown完整原行。新告警/Run≤2、事件≤6、工件≤14、cost/shadow各≤2、预算行≤2，QA及动作/审批/记忆写回新增0。入口确需不同记录数量时，须业务前独审更正规格/设计中的明确上限，不事后放宽。窗口目标≤10分钟，具体watchdog发送前冻结，operator不循环发样例。

## Risks / Trade-offs

- 测试窗口混入其他输入 → 发送前证明物理输入边界，运行出现无关offset立即停；不能仅靠tenant reader失败阻挡模型。
- 计划产物齐全掩盖运行绑定缺失 → 下表全部为执行前阻塞，由任务1.x完成并经独审绑定，未完成保持OFF。
- 恢复误重调模型 → 只复用同Run首次结果；已发/回复未知保留unknown。
- 新profile把原建议当动作依据 → 逐项核0effects、Alert全字段不写及绑定receipt，不以最终NR标签代替。
- CLI归档被当质量通过 → 回执和PROGRESS保留有限窗口、自治失败与后续待验边界。

## Execution Prerequisites

以下不是可留到执行后的开放问题，均为发送/启动前必须完成的冻结项：

| 待冻结项 | 完成证据 |
| --- | --- |
| 两条新输入与判据、tenant及reader身份、费用/预算合同 | 输入及判据hash、受控身份位置/权限、预算及usage来源；不公开秘密 |
| 当前镜像/源码/prompt、policy bind及旧状态 | R01来源对应、运行快照、policy hash/device/inode、旧表/预算/组offset保护集 |
| 唯一operator与计数 | operator hash；HTTP、SQL、发布、物理读取、启动/恢复/最终OFF配置与recreate具体上限 |
| 故障接缝、watchdog与停止恢复 | 明确作用范围、触发/撤销、超时、进程清理、最终OFF定义 |
| 独立运行前审计 | 审计记录精确绑定以上产物且允许进入本批有限步骤 |

## Migration Plan

本次只建档，0运行操作。未来按任务先冻结、独审，再启动有限窗口、实际两条消费、保存恢复、fresh复用和最终OFF。失败先停新输入/worker，保留Run/SDK意图/预算/offset；仅对明确可恢复保存/确认继续。配置恢复为worker/effects OFF；回到legacy默认值不授权开启自治。任何回退不得删除预算、改变旧offset、撤销已确认事实或重放unknown。
