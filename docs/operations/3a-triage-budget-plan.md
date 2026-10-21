# 3A-10-03-02：持久分诊额度、积压和停止恢复

批次 `3a-triage-budget-20261020`，2026-10-20。承接[总计划](3a-worker-reliability-plan.md)、[请求界限](3a-triage-request.md)及[重投保护](3a-triage-recovery.md)。本批已限定验收，实际结果见[回执](3a-triage-budget.md)，操作前原件另存受控scope-plan-before.md；下述保留实施范围，常驻worker及完整质量不据本批自动开放。

## 明确合同

现有美元governor是进程内对象：新实例的spend为空，token数只是累计、不参与check。旧stop关闭consumer/producer，但不等待EntityLanes；lifespan随后只取消主消费task，已创建子task不由该取消自动结束。先保存这些直接证据，不重做旧模型质量或改写原始回执。

新增一份本项目SQL `deploy/aisoc21/migrations/001_triage_budget.sql`，创建独立 `socai2_triage_budget_reservations` 表、索引、RLS和额度字段不可变保护；不修改固定134份上游迁移或其登记表。首次执行前备份本项目aisoc，并在独立临时库恢复核对旧14表材料，再仅删除该临时恢复库；原库/其他项目/卷保持。无runtime DDL/schema bootstrap。

只覆盖已启用本批policy配置的普通Kafka live分诊。operator在受控文件逐tenant配置滚动窗口、调用数、预留token总额、每次预留和未确认并发上限；缺tenant、坏文件/数值、PG错误失败关闭。无该配置时原入口合同保留，不能外推全入口预算。A/B测试配置进入新只读挂载，不是新reader凭据。

Run认领前确定普通分诊是否会走LLM；同一PG事务在tenant advisory lock下核额度/未确认数，并完成原claim/start与额度预约。已有完成结果先复用，不扣新额度；确定性、缓存及原policy/memory抑制不扣本表额度。额度claim拒绝/PG失败事务不留下Run或预约；不调用模型、不确认DLQ、不提交offset，停止消费窗口形成积压。恢复只能在原因实际解除后重启同group，不自动清账/移offset。

调用次数按**获准LLM尝试**计，token额度按每次固定保守预约单位计，均不是实测usage/费用。本批每次预留20000、实际prompt UTF-8规范消息序列化最多16000字节、输出上限512；该预留是准入计费合同，不宣称任意第三方tokenizer/忽略参数的厂商绝对token上界。safe_ainvoke的请求接缝校验一次调用、SDK retry0/timeout45及512输出，并在调用前持久标记request意图；此标记也不证明远端收到。只对当前预算上下文禁用通用纯文本response cache，保留旧入口cache合同。始终只承认已有安全输入/隐私处理后的实际出站消息。

响应返回后持久记responded、可证实的usage（缺失为null），解除该预约的未确认并发占位；不退还固定预约。合约/输入在请求前明确拒绝可记no_request并解除占位，但不退额度。超时、连接失败、取消、进程退出或响应确认保存失败均保留未确认占位及全部额度；不靠TTL、Run状态或窗口到期抢占未知调用。额度窗口可自然过期，但未知并发占位不自动过期。此保守合同可能需要后续人工裁定，不新增自动退款/重发工具。费用unknown仍unknown。

停止先阻止新处理/新请求，关闭consumer唤醒等待，给已在处理的任务10秒完成保存；超时取消子task并等待其退出，再关闭DLQ producer。主消费task退出须清理残余子task；不提交未确认窗口。已保存首次结果沿旧只读复用，同worker保存失败仍用原tuple；丢失进程结果保留unknown。本批不扩大到rebalance、高可用或非协作取消代码。

## 有界验证与恢复

先跑直接相关测试和新关键边界；沿用缓存生产锁依赖。真实环境基线61告警/32Run/83事件/92工件/21成本行、36容器/18卷/134迁移、十枚reader保持。最多6条新标记HTTP告警、12次broker发布、16次交付、6个Run、6次HTTP模型响应替身，真实模型0次。模型替身无真实usage/费用声明，原43网关计数应保持；单元合成usage另标注。

真实PG核原子回滚、A/B隔离、跨进程额度竞争、相同Run不重扣、无pool/查询错误拒绝；真实SSL Kafka核额度拒绝offset/积压、同group恢复、停止取消后unknown且不重调、完成结果重启复用。既有API读取证明Run/start/首次结果关系；预算表原始行另存受控取证，不新增万能API身份。仅更新Agents和一个policy挂载顶层，API/Fusion/Actions不重建；显式HTTP认证/隔离和旧产品回查，收尾停用三操作key。保留输入/模型方法替身失败、检查点与原材料，不盲重跑。

回退先停新输入/消费，撤新顶层恢复triage-request Agents及原二十层/env/reader挂载；保留新表、预约、Run/事件/工件和消息，不删未知占位或盲重放旧模型。旧镜像不执行本表约束，回退后常驻仍OFF。后续准入仍需质量/旧工具身份/来源缺口等单独通过。
