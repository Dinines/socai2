# C03-01：分诊时间与授权提示词

2026-10-21。**本子change限定验收通过，C03-02/03、整个C03、模型质量与常驻准入仍未完成。** 见[执行卡](c03-triage-reasoning-plan.md)、[来源清单](../handoff/c03-triage-reasoning-source-manifest.json)、[补丁](../../deploy/aisoc21/patches/c03-triage-reasoning.patch)及[机器回执](c03-triage-reasoning.json)。旧p01及原评分/账本不改写。

仅将生产`triage.system`时间/授权指导由v2更新为v3并同步lock。采用event_time而非created_at或接收时间；比较授权窗口须有完整起止、可比较时区/offset及当次动作、账户、目标范围，跨日期按同一时间基准判断。缺端点、时区或匹配job属于证据缺口；窗外不自动证明没有其他授权，在职/职位/组织习惯/历史处置不能单独证明本次批准。短理由须区分材料事实、行为推断和未知项。

## 输入、实际调用与结果

| 验证 | 实际中间产品 | 结果及限制 |
| --- | --- | --- |
| 新6例及直接prompt/request/budget测试 | 实际build_state→agent/safe-call→生产SDK完整messages，外部HTTP/数据库为明确替身 | 唯一first共88项通过；覆盖跨日期offset、窗外直接行为、缺端点/范围、缺时区、缺job；固定回答不评分模型理解 |
| prompt/lock及预算保持 | v3 registry/lock验证，分类/schema前缀及21个其他prompt lock entry精确hash，完整messages | 保留输出512、retry0/45秒、8000字符账本与canonical16000字节边界 |
| 独立baked候选探针 | UID10001、断网、无真实凭据，/app生产模块→一次SDK MockTransport | 实际messages 6560字符、canonical 6502字节；18 tokens仅合成响应fixture，provider费用/usage未知 |
| 实际运行及只读收尾 | 固定候选`sha256:039f2cb09684c29e170b8907572196ff5559c9d7991837fc431a12d113350985`，184Py及非Py lock在测试/候选/运行三方对应，triage.system v3 | 仅Agents一次重建，60秒stop grace继承未改，env/挂载/依赖与其余35容器保持；独立predeploy/final/closeout审计accepted |

唯一缓存测试first为88通过/0失败/0collection errors。root另一次同名入口因独占attempt已存在而在Docker前收到FileExistsError，未重复测试或删除材料，拒绝记录保留。build成功后、启动首个probe前纠正了host调用路径，旧build operator和修正记录保留；该修正没有产生失败probe，也没有重建镜像或更改候选源码。

## 保护与未验范围

真实模型0，新业务PG写/行、broker发布/物理交付/提交、新tenant/key/reader均0。旧14表、5预约/三unknown、六组offset与A积压、十reader、18卷/134迁移保持；不重调旧unknown、不退款。C02 live禁跨告警pattern缓存及同Run首次结果/恢复合同保持，direct/replay旧缓存未修。worker、graph、审批提案、记忆写回仍关闭。

当前25层Compose、22层来源。提示词约束与确切传输不代表模型语义/引用质量或普适授权判定通过，也没有新增真实inflight Docker stop或回滚演练。下一项是[同卡](c03-triage-reasoning-plan.md)C03-02：先冻结新的有界盲样例、预算和判据，再单独审计质量；之后C03-03才考虑受控常驻窗口。未提交或推送。
