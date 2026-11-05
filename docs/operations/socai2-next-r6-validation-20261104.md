# n9 / r6 固定真实验收

状态：**本批结束，未通过，不重派**。来源仍为r1固定两条合成告警和两条湖事件；复用预检逐项一致。独立服务n9，不改原服务及配置。

| 阶段 | 实际结果 | 判断 |
| --- | --- | --- |
| 鉴权 | 无凭据401、只读写403、只读GET200 | 通过 |
| A0 PowerShell | Run `a3adcc2e-60db-5a63-947a-ec0f69614bc6` failed；2821tokens | 正文引用S20/S21/S27/S28，分别是用户/主机/动作/结果，均实际可见，但未进入对应evidence_ids；不是不存在来源，按当前合同拒收。原成功分诊未覆盖 |
| A1外联 | Run `70954c25-60fc-5cb2-b18b-2815675bfa61` completed；3234tokens | needs_review，说明TCP443不证明HTTPS、历史同主机不证明该进程发起连接、查空不构成反证；合法绑定编号为warning，原答保存 |
| I事件 | Run `577795ed-87ea-5f2e-9a4b-f3987a3a0459` completed；5325tokens | 正确保留同主机15秒背景而不推因果/授权；两份分诊可见。A0使用旧成功Run `a5e92421-9fb4-5eb3-be42-612e5c184bbe`，A1使用本批成功Run；不能把A0称本批成功 |
| 首轮C | Case `f0f4bcb1-6b00-5bb4-880d-a7e6c4b08574`，Run `bcca5931-6522-4dbb-8bbc-dfd3da5e017f` failed | C2完成2个实际PG查询；准备视图required_model_input_unavailable，C3未调用模型；C6为system_only/null/partial系统交接。不是模型语义失败 |
| H/第二C | 未执行 | 首轮无有效结论，不满足后续前提 |

C停止的实际断点：准备视图按完整引用账本计8KiB，第二成员时间被model_view_budget_exhausted省略；整个事件诊断对象又因whole_field_exceeds_budget省略。必需内容保护按预期阻止派发，但计量对象和诊断投影是自身设计问题。该失败视图的complete_required标记也不准确。随后本地v3修正，详情见[实施记录](../investigation/socai2-compact-input-fix-20261104.md)，未重写本批工件或部署后续修正。

总计3模型、11,380tokens；7次实际PG Tool查询（A合计5、C2为2），无Deep模型、无C4湖Tool、无C6模型。复用预检额外有两次PG及两次CH只读校验，不能混作调查Tool。没有新增/改写原始告警材料或湖行；模型费用未定价，不能把固定样例改善泛化为质量保证。

原件：[部署核验](evidence/socai2-next-service-20261104/20261104T092432-start/receipt.json)、[A/I批](evidence/socai2-next-acceptance-20261104/20261104T092507-r6-stages/receipt.json)、[首轮C批](evidence/socai2-next-acceptance-20261104/20261104T092700-r6-first/receipt.json)、[最后导出](evidence/socai2-next-acceptance-20261104/20261104T092702-r6-export/receipt.json)。[结构化汇总](socai2-next-r6-validation-20261104.json)保留快照hash、各Run状态及用量。
