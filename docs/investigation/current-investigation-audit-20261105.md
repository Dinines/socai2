# 当前调查流程审计与修复

当前开发分支 `codex/case-baseline-history-20261103`。四项问题已完成代码修复及针对性验证；C6输入装配已修，但完整请求的剩余额度问题仍未闭环。没有改页面、增加Run预算或重写历史执行记录；常驻独立服务尚未同步本次代码。

| 项目 | 当前状态 | 实现及验证 |
|---|---|---|
| A01 / P1 输入新鲜度 | 已修复 | 采用前检查冻结输入；读取时返回过期原因。隔离PG验证材料、人工反馈、元数据例外、范围与事务回滚 |
| A02 / P1 C6容量 | 部分修复，未闭环 | 必需事实/时间/H/原计划能完整组装；三份冻结材料计入先前usage后仍超共享预算，未发新模型 |
| A03 / P1 明确拒绝占槽 | 已修复 | A/I/C3/Deep/C6明确Schema拒绝收口failed；不确定仍unknown。PG验证无重试、终态和槽释放；独立模型profile绑定已写入Compose，未部署 |
| A04 / P2 SHA256漏读 | 已修复 | 扁平字段与明确算法OCSF投影、来源、冲突、非法值遗漏验证通过 |
| A05 / P2 C2来源饥饿 | 已修复 | 按冻结对象选来源并记录依据；完整PG执行验证情报/资产实际派发，与Deep合计仍4次Tool |

## 1 当前判断与输入版本

[125迁移](../../services/api/migrations/125_socai2_baseline_input_freshness.sql)仅增加/替换函数，29表459列不变，未覆盖123/124迁移。已在21的既有隔离验证数据库 `socai2_schema_review_20261103_a1` 应用，未应用业务库。

`baseline_input_freshness(tenant,run)`在同一SQL语句快照内比较：

- Case范围版本及成员集合。
- `run_members.material_id/triage_id/feedback_id`与成员当前指针。
- C1冻结的相关事件集合、事件诊断指针与事件成员集合。
- 已完成人工任务的结果正文、结果范围、引用、完成者和完成时间；标题、负责人、期限、revision编号不进入反馈签名。

自动采用仍检查结论有效性、同Case、范围、较新判断及交付覆盖；新增输入检查不通过返回 `stale_input` 和 `input_freshness`，本轮报告/Result留历史，当前判断不变。符合要求的partial仍可采用。当前判断读取返回 `input_freshness.state=current/stale/unverified`及reasons，采用后再发生变化也可显示过期。

例：C1冻结M1，随后同一告警收到M2；本轮可以形成基于M1的历史结果，但不能覆盖当前判断。H1只改标题仍新鲜，修改结果正文成为H2则过期。

边界：没有把所有来源写入强制串行化。检查依据该SQL可见的已提交数据；之后提交的新输入由读取端识别过期。历史材料和Run不回写，不把这项检查称为全库并发串行保证。

## 2 C6输入与仍未解决的共享额度

[输入装配](../../services/api/app/socai2/baseline_reanalysis.py)按最终阶段职责划分：原始观察、告警时间、适用人工反馈、实际执行原计划和有效比较结论必须保留。A/I是前序分析参考，按同次判定、评分、理由整组保留或明确省略；不拆配、不改写、不改成行为证据。所有未选项按原来源写省略回执。

原guard及单项2048B、数据8192B、消息12288B均保持。随后还会检查转换后的完整请求，包括输出Schema，以及本Run此前报告的实际usage；总额度仍为4次模型、24000 tokens。`ready=true`只表示输入可组装。

使用三份固定材料离线重建并逐值/引用检查：

| 冻结Run | 必需项 / 丢失 | 数据视图B | 完整C6请求B | 先前已报tokens | 剩余请求允许B | 当前能派发 |
|---|---:|---:|---:|---:|---:|---|
| 4d8356ef-64fa-4331-ad97-34e58eeaf8da | 22 / 0 | 7943 | 16527 | 7286 | 13458 | 否 |
| 44a7863a-5edb-4cab-9480-17b4b0c12121 | 22 / 0 | 7966 | 17262 | 11430 | 9314 | 否 |
| 2dbb194b-5cf0-4f04-aa26-c81928d0eb9b | 23 / 0 | 7894 | 17939 | 7470 | 13274 | 否 |

这些数值是在可选项进一步裁减后的完整wire结果。额度核算沿既有保守算法：请求字节上界 + 3000输出预留 + 256安全余量 + 先前usage。没有把bytes说成实际token消耗，没有重置先前usage。三份材料仍会以 `model_token_budget_insufficient` 停止，而不是生成或采用猜测结论；输入装配修复不能被表述为三条整链已恢复成功。

仍需解决：在原总预算内明确C3、Deep与C6的容量分配，减少重复输入/输出Schema开销，并以新的固定样本验证真实C→H→下一C。仅预留最后一次调用次数不保证还有足够tokens；不能通过删必要反馈、增加预算或反复重跑挑结果核销。

## 3 模型拒绝与终态

[model_errors](../../services/api/app/socai2/model_errors.py)仅识别明确的400/422 Schema错误代码、已知Grammar拒绝或明确非法Schema消息。A/I/C3/Deep/C6保存去凭据回执，`raw=null`、usage未知；模型步骤及父流程失败收口并写结束时间。C的最终系统交接不覆盖当前判断；完成失败收口后不再占用单活跃槽。

超时、连接中断、其他不能确认执行结果的错误及提交结果不明继续unknown，不重试，不推定零消耗。没有将历史unknown批量改成failed。

独立小模型Compose绑定 `chat_completions/vllm_grammar_v1`，仅发送层去掉不支持的uniqueItems，本地约束仍检查；DeepSeek覆盖为 `deepseek_responses/standard`。预检同时核模型名、协议和profile。原服务/网关配置没有修改。

## 4 补查字段与来源选择

SHA256：读取明确 `hash_sha256`，以及 `file.hashes/file.fingerprints`中声明SHA-256算法的值。只接受64位十六进制，保留原值与路径；大小写差异不算冲突，真正冲突保留双方。无算法、未知算法、非法或超大值留下遗漏原因，不从长度猜SHA256。原查询工件保持完整；进入模型还受本阶段预算选择，不声称每个新增字段都已被真实模型阅读。

C2：冻结的明确IOC优先情报，带命名空间的用户优先UEBA，主机优先资产；只有检测线索时优先知识，通用历史作补充。未连接/无对象不占调用；所有来源仍有执行或跳过回执。Tool参数保存selection，C2汇总保存selection_plan。固定优先级是选择策略，不是对恶意程度的评分。

例：IOC＋主机选择情报/资产；用户＋文件IOC选择情报/UEBA；仅检测标题选择知识。完整执行器仍从4次Tool总额度中给C4留2次，空结果也计调用。真实PG流程验证情报/资产两次与Deep两次合计4次，历史来源明确跳过。

## 5 验证与证据边界

52项离线检查与18个不同隔离PG测试方法的最新结果通过，首次失败不隐去。PG测试内含多个情景；以下按方法计数，不把清理测试角色算业务用例。

- [52项离线检查与逐源指纹](../operations/evidence/current-investigation-audit-20261105/fix-validation-20261105T023329/validation.json)，[测试输出](../operations/evidence/current-investigation-audit-20261105/fix-validation-20261105T023329/pytest.txt)。包含三份C6原件回放、完整wire和剩余额度、原值/引用/省略、SHA256、来源选择、协议/错误、流量及原计划预算回归。实际源数据库原件hash保持。
- [存储/采用/互斥/回滚](../operations/evidence/socai2-store-20261103/20261105T022304/receipt.json)和[人工反馈定向复核](../operations/evidence/socai2-store-20261103/20261105T022515/receipt.json)。首批H测试因临时测试角色没有读取用户ID的权限失败；补齐该测试权限后定向通过，不修改业务权限。
- [分诊与人工改判版本变化](../operations/evidence/socai2-store-20261103/20261105T023549/receipt.json)：分别新增同次判断并更新当前指针，均返回stale_input且不采用。三项数据库函数[安装指纹核对](../operations/evidence/current-investigation-audit-20261105/fix-validation-20261105T023329/migration125-installed.json)与本地125一致。
- [C3/Deep/C6终态与完整协议执行](../operations/evidence/socai2-executor-20261103/20261105T022424/receipt.json)。三种Schema拒绝各一次，终态失败/无活跃步骤/无采用；通用错误仍unknown；完整C3→Deep→Deep→C6协议替身路径通过。
- [A阶段](../operations/evidence/socai2-alert-basic-20261104/20261105T022703/receipt.json)与[I阶段](../operations/evidence/socai2-incident-diagnosis-20261104/20261105T022718/receipt.json)：明确拒绝失败、重复操作不派发、旧判断保持，未知错误仍unknown。
- [C2与Deep共享额度、必要计划超限、剩余额度停止](../operations/evidence/socai2-executor-20261103/20261105T022901/receipt.json)。

PG为既有隔离数据库真实事务；模型、湖和背景返回使用替身，没有新真实模型或业务湖查询，没有重派结束批次。初次离线测试含测试调用签名错误；随后完整wire断言揭示上述真实剩余额度缺口，因此只报告输入保留通过及预算停止正确，不报告最终派发通过。源码目录已更新为124写点/57源指纹；不是逐SQL前后镜像系统。

## 6 后续工作

先解决C6共享额度分配，再固定候选并同步独立API/Fusion及125迁移；以新增固定样本做Kafka→A→I→C→H→下一C及双模型真实验证，保留每步输入/输出/写表与实际用量。旧批次与原服务保持。Q仍501，Case仍手动单活跃，不改页面。

OpenSpec 3.7、4.1、4.2未完成。本轮修复复核不是实施完成后的独立结束审计；不归档；用户已授权提交推送当前分支，不改变未完成验收状态。真实模型事实语义与新增湖上下文是否实际进入最终结论尚需验收。
