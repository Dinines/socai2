# C03-02B：分诊理由复验与受控停止

2026-10-21。**本批受控停止和凭据收尾通过独立审计，分类通过但授权理由未通过；四例质量与常驻准入仍未通过，worker继续关闭。** [执行卡](c03-triage-quality-recheck-plan.md)、[结构回执](c03-triage-quality-recheck.json)及[证据清单](../handoff/c03-triage-quality-recheck-evidence-manifest.json)保存实际结果。本批不改原[C03-02失败回执](c03-triage-quality.md)，不代表整个C03或服务端迁移完成。

只执行新case01：真实HTTP→raw/Fusion→PG/fused，再复制原信封至独立quality topic，由实际live worker认领、预约、读取五类来源，使用同版v3和生产SDK调用一次模型并持久化。模型返回true_positive/0.95，usage为1808输入+110输出=1918 tokens，美元费用未知。原JSON/schema、材料、usage、PG/API及offset关系通过；同PID加密在用发票、读回失败和付款换密钥材料支持恶意行为分类，但短理由把缺少当次授权证据断言为确定未授权，未承认该项unknown，违反本批冻结理由判据。独立审计因此拒绝完整质量；case02–04未执行，两个批次的旧case01均未重调或改评分。

本批没有启动权限失败或恢复操作。任何业务写之前已用固定候选镜像、UID10001、network=none、只读单脚本挂载做读取/SHA/AST探针，exit0；随后才独立审计与逐phase执行。原02的启动失败和受控恢复继续留在原证据中，本批不继承为自身已发生事件。

新增1 Alert、1 Run、3事件、7工件、1成本、1已responded预约（20000预留单位，非实际tokens）及1原shadow回执，0 QA样本；核心Alert/FusionIncident/Run和来源工件关系已核。三次发送为raw、原Fusion fused、quality各一次；临时消费者直接观测2条交付，另1条常驻raw通过ack→PG/fused→metrics及提交合同推证，总交付推证3，未把metadata或保留slot单独称为精确交付仪表。新quality offset/end均1，DLQ空。旧主group提交、六budget组保持，原02的quality end/commit1及DLQ end0另存metadata基线；helper不额外交付应用记录。旧budget metadata helper沿用assign后读取commit/end的实现，未poll/getone/commit；不将零应用交付外推为零后台网络fetch。独审新metadata探针不assign。

三枚本批操作key已停用且逐枚真实API401，十枚reader及映射保持。旧14表、6预约/120000预留单位/3 unknown及原积压保持；本批不退款或重放。执行前按新卡只增加A一call/20000 policy容量，其余未用额度经新卡重新授权；不把本批4call上限称为新增4份容量，也不把预约记作usage。0源码/prompt/schema/镜像/部署变化、0服务重启/DDL，36容器/18卷/134迁移保持。运行25 Compose层、22来源层、四服务769 Py及非Py prompt lock引用[C03-01来源清单](../handoff/c03-triage-reasoning-source-manifest.json)，不新增源码层。真实HTTP、显式hostSQL和独审读取分别报告，不声称0 HTTP或已统计所有服务内部SQL。

下一项单独规划0真实模型的授权证据prompt澄清；暂不在本批改app或prompt，之后另冻新代表输入和独立判据再作有界复验。原两例的失败与unknown事实保留，不为了旧标签重调模型。四类代表证据未通过前不进入常驻窗口。QA关联等原版非阻塞问题仍条件延期，不扩张为全租户质量、通用授权校验或真实响应已验。
