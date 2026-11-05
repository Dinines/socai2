# n6 / r3 真实验收：结构改善，语义未通过

本批已经结束，不重派原操作。独立新服务仍为 `socai2-next-api`，镜像 `95c987cc66ef…`，545 个应用文件与固定 n6 候选一致；旧四个容器保持。新库仍为 PG `socai2_next_20261104`、CH `socai2_next_validation`，没有 DDL 或旧业务迁移。

## 本轮实际改了什么

- C3 在初次分析前读取 C1 冻结的原材料必要字段；I 按成员轮流优先提供行为字段。原值、成员归属和路径保留，标签与已有判断分开。
- A/I/C3/Deep/C6 使用同一业务合同生成的 JSON Schema，保留返回后的引用、归属和角色校验。所有请求记录 `temperature=0`，预算不增、无弱约束回退。
- C6 仅在剩余额度不足时按原优先级移除可选输入，并同步来源枚举和省略记录；必需目录仍放不下时继续失败。

同一份 r2 输入的离线对照中，I 可见原记录行为字段从 6 个变为 19 个，C3 从 0 个变为 18 个。它们是字段数，不是独立证据数。见[字段投影明细](../investigation/socai2-model-input-projection-20261104.md)和[结构约束说明](../investigation/socai2-structured-output-20261104.md)。

## 四次真实输出逐项结论

| 阶段 | 程序结果 | 人工核对原材料的结果 |
| --- | --- | --- |
| A 第一条进程告警 | failed，正文泄漏内部来源别名 | 仍用 Synthetic/fixture 等来源标签推导良性或授权，不能通过 |
| A 第二条网络告警 | completed，已保存分诊 | 结构合格，但用示例地址和标签推导“无风险、无需调查”；现有程序校验未拦住，不能通过 |
| I 事件诊断 | failed，正文泄漏内部来源别名 | 数组和成员结构改善，仍有旧判定混淆、来源标签支撑良性等问题 |
| C3 首次完整调查的初始分析 | failed，invalid_conflict_findings | 两个成员、六个问题、四个领域结构齐全；仅一个 finding 不能形成冲突。另有进程导致网络连接的无据关联、预算跳过写成未接通、缺少材料写成不适用等语义问题 |

四份回复均符合本次请求记录的 provider JSON Schema，但不等于通过业务校验或结论正确。C3 的交叉字段约束由本地解析器拒收；不能靠放宽它来宣称完成。

本批 4 次模型调用共 14666 tokens，均返回完整 usage，费用未定价；完成 7 次实际 PG 查询。Case 只保存 `system_only / null / partial` 交付，没有采用为当前判断。没有执行 Deep、真实 CH 补查、C6 模型、H 或第二轮 C，因此这些端到端环节仍待验收。

原始两告警、两湖事件逐字段核对后复用，没有改写样本；新建了 r3 专属 Case 和操作编号。上游服务只读元数据自报 Qwen3.5-9B，五个 alias 均指向同一后端；不能把换 alias 当换模型。

## 证据与下一步

- [固定机器汇总及快照 hash](socai2-next-r3-validation-20261104.json)
- [n6 修复验证汇总（保留初失败）](socai2-next-n6-fixes-20261104.json)
- [最终合成数据快照](evidence/socai2-next-acceptance-20261104/20261104T070415-r3-export/database-20261104T070419.json)
- [n6 部署与原容器核对](evidence/socai2-next-service-20261104/20261104T065940-start/receipt.json)
- [前一批 r2 原失败](socai2-next-r2-validation-20261104.md)

用户已允许使用 ergouzi API。项目现有配置中未找到对应入口，API 地址/配置位置及“用户所给字符串”是模型名还是 token 值仍待确认；此时未改模型配置、未向未知地址发送凭据。r4 仅准备本地驱动，[5 项离线检查通过](evidence/socai2-next-service-20261104/r4-driver-offline/receipt.json)，复用同一原始材料、新建操作，首轮语义达标后才允许 H 和第二轮 C；失败历史及已有分诊不删除。

OpenSpec 仍为 13/16，3.7 真实验收、4.1 结束审计、4.2 归档未完成。Q 保留 501，旧 r13/5.3 不在本批核销。
