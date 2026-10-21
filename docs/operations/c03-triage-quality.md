# C03-02：新分诊理由复验与受控停止

2026-10-21。**本批受控停止及凭据收尾已获独立审计通过，四例理由质量未通过；常驻 worker 继续关闭。** [执行卡](c03-triage-quality-plan.md)、[结构回执](c03-triage-quality.json)和[证据清单](../handoff/c03-triage-quality-evidence-manifest.json)保留原失败、恢复及结束审计。没有完成整个C03或服务端迁移。

实际只执行case01：真实HTTP→raw/Fusion→PG/fused，再复制原信封至独立quality topic，由实际live worker认领、预约、读取当前五类来源、使用v3及生产SDK调用模型并持久化。返回needs_review/0.65，usage为1829输入+169输出=1998 tokens，美元费用未知。原JSON/schema、完整材料、usage及PG/API/offset关系通过；冻结rubric要求true_positive，独立审计拒绝质量。短理由把另一个账号/主机的历史组织背景称为明确授权并作为冲突材料，未满足原定直接破坏行为判据。保守needs_review不能代替该批质量通过，也不改原评分；case02–04未执行，case01未重调。

首次ingress容器因root0600脚本对UID10001不可读而在Python入口前exit2，当时0发送/模型/业务写。原log、before/after、退出及stop完整归档；独审确认字节不变、只改0644，使用断网无私密挂载读探针后才释放新的实际phase。原启动失败没有被改写成通过。

新增1 Alert、1 Run、3事件、7工件、1成本行、1已responded预约（20000预留单位，非实际tokens）、1原shadow回执，0 QA样本。Alert/FusionIncident/Run及来源工件关系已核。三次发送为raw、原Fusion fused、quality各一次；临时消费者直接观测2条交付，另1条常驻raw通过ack→PG/fused→metrics及commit合同推证，总交付推证3，未把metadata或保留slot单独当精确交付仪表。quality offset/end均1，DLQ空；旧主group提交和六budget组保持。

三枚本批操作key均停用，各一次真实API401复核；十枚reader与映射保持。旧14表、5预约/100000预留单位/3 unknown及原积压保持，未退款或重放。只有凭据停用这一收尾外部写；0服务重启/DDL，36容器/18卷/134迁移保持。当前镜像、25 Compose层、22来源层、四服务769 Py及非Py prompt lock均引用[C03-01来源清单](../handoff/c03-triage-reasoning-source-manifest.json)，本批不增加运行源码层。实际HTTP与显式host/独审SQL分别计数，见结构回执，不宣称0 HTTP或已计全部内部SQL。

下一项另行冻结更明确恶意工件/加密或勒索事实的新阳性，以及明确授权、材料不足、时间反例的新有界输入和独立判据；不为旧TP标签修改prompt或重写历史。四类代表证据未通过前，不进入常驻窗口。QA关联等原版非阻塞问题继续条件延期。本批不是通用时间/授权校验、全租户模型质量、真实响应或迁移完成证明。
