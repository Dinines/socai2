# C02：分诊材料、普通live缓存与停止清理

2026-10-21收尾，批次于2026-10-20开始，标识保持`c02-triage-material-cache-stop-20261020`。**本change限定验收通过，整体迁移及常驻分诊准入尚未完成。** 对应[审核R2/R4/R5](migration-review-20261020.md)及[执行卡](c02-triage-material-cache-stop-plan.md)；来源/差异见[manifest](../handoff/c02-triage-material-cache-stop-source-manifest.json)、[补丁](../../deploy/aisoc21/patches/c02-triage-material-cache-stop.patch)，实际输入/调用/保护及审计见[机器回执](c02-triage-material-cache-stop.json)。

分诊state保留description、event_time和created_at的有无/null原值；实际untrusted telemetry独立展示描述及来源发生时间，不回退created_at、不替缺失时区推定UTC。描述采用前1200字符及可辨认裁剪标记，完整采用messages可查。普通Kafka live停止跨告警pattern结论缓存，保留同Run PG首次结果/暖恢复/unknown保护；共享指纹及Run版本保持。consumer.stop异常后仍完成有界lane drain/cancel/join、producer清理；main保证cancel/await主worker后再关闭账本池。

## 输入、实际调用与结果

| 验证 | 实际中间产品 | 结果及限制 |
| --- | --- | --- |
| 正文/时间与缺失/null/显式偏移 | build_state→真实safe-call/SDK→MockTransport完整messages | 独立untrusted段保留事件时间与偏移，created_at不冒充事件时间；长描述明确裁剪 |
| 同pattern不同Alert/Run，首条FP/.99含未支持指标 | 实际普通live ContextVar/CostGovernor/gate，持久与模型传输为明确替身 | 首条降级，后一条重新按材料处理，不从旧pattern缓存复活；同Run PG完成复用及unknown不重发保持 |
| consumer/producer失败、drain/cancel及main生命周期 | 实际worker/EntityLanes/main函数，外部启动依赖替换 | 清理完成、错误/取消可见、无迟到提交；不外推非协作任务或真实inflight Docker stop |
| 独立baked候选探针 | UID10001、断网、不挂真实凭据；/app生产模块→一次SDK MockTransport | 实际messages 5628字符、canonical 5570字节，输出512/retry0/45s；18 tokens仅合成响应fixture，不是模型usage |
| 部署与恢复 | 固定候选`sha256:c9cf8920a8ac2a601acf6f8cab5033f448f22a4aec103f43e94ddfd707ce98d5`，184Py对应测试/候选/实际运行 | 仅Agents一次重建，stop grace60；env/挂载/依赖及其余35容器保持 |

最终缓存测试118项通过。首轮112通过/6失败：五个新fixture漏传ClosureDecision.threshold，一项旧恢复测试仍期待live跨告警缓存；直接修测试后用新attempt复测。首轮`errors=1`来自旧计数器误匹配日志`attempt=1 error=`，实际collection errors为0；原JSON/log不覆盖，后续只解析pytest最终summary。

首次部署后断言因HostConfig.Binds七个字符串顺序变化失败，此时候选已健康。原部署operator及`deployment-first-assertion-failure.json`保留；独立只读恢复按排序后的同一组Binds及其余HostConfig/env/mounts核对，补恢复检查点，没有重复compose up或再次重建。该失败不写成原部署命令首次完整通过。

## 保护、审计与未验范围

真实模型0，业务PG写/新行、broker发布/交付/提交、新tenant/key/reader均0。未改的真实持久化/重投合同复用C01及3A既有证据，本批不将替身写成新的真实PG/Kafka验证。旧14表、5预约/三unknown、旧六group及A积压、十reader、18卷/134迁移保持；不重调unknown，不记真实费用为零。候选与最终运行独立审计accepted；worker、graph、审批提案及记忆写回仍关闭。

当前24层Compose、21层来源。容器宽限60秒用于有界合作清理，不改变模型45秒截止或保证强制中断。direct/replay旧pattern缓存未修，全文/时区正确传递不等于模型理解、引用或完整质量通过；实际回滚未演练。下一项为[C03执行卡](c03-triage-reasoning-plan.md)的C03-01零模型提示词修复，随后另批质量及有界常驻准入分别审计；旧p01回执保持，另用新证据验收。未提交或推送。
