当前仅建档，以下任务全部未完成；产物齐全或CLI显示apply-ready不代表执行绑定、冻结或准入已通过。

## 1. 运行前冻结与独审

- [ ] 1.1 核分支、未提交内容、R01及相关完整规格/原R02卡；记录当前运行源码/镜像/prompt和worker OFF证据。
- [ ] 1.2 冻结A/B两条全新输入、判据/hash及同链ID；核没有复用旧失败样例或假定模型分类。
- [ ] 1.3 冻结tenant/reader实际身份、policy bind hash/device/inode与预算；按DB时钟及旧预约重核A一次+B一次/40000预留单位且不增额，核旧12预约/240000/3unknown完整原行，凭据只记受控位置。
- [ ] 1.4 冻结唯一operator/hash、具体HTTP/SQL/发布/物理读取上限、watchdog、故障接缝和启动/恢复/最终OFF配置/recreate次数；绑定design的各类记录/key上限及0新增tenant/reader/closure policy，产出执行清单。
- [ ] 1.5 只读封存旧材料、旧预约/unknown、全部相关group/DLQ/offset及其他容器/卷/迁移保护集；以快照核对范围。
- [ ] 1.6 完成未参与实现者的运行前独审，精确绑定1.1—1.5产物；严格CLI校验且所有冻结条件满足后才进入第2节。

## 2. 有限main消费与交付

- [ ] 2.1 在worker OFF下记录main fused每partition end，创建本批新operational group并显式设该起点；核旧main/历史组offset不变且输入边界可证明。
- [ ] 2.2 按冻结次数recreate同R01 Agents镜像，由main实际startup启动；核group/subscription/readiness、profile/source及policy挂载一致。
- [ ] 2.3 只发送本批A/B两条新输入，经真实HTTP/Fusion/PG/Kafka到resident/Run/API；核各tenant reader与实际模型可见来源、usage/成本及预算分列。
- [ ] 2.4 核原建议未审核、effective NR/null及完整绑定receipt；canonical Alert全部AI/状态/处置字段保持，所有自动效果调用为0。

## 3. 持久恢复与最终停止

- [ ] 3.1 用冻结的本批故障接缝核保存/确认失败不越过offset，warm仅恢复保存，保首次材料且额外SDK为0。
- [ ] 3.2 在最多一次停止→fresh进程恢复周期核已完成输入复用同Run/完整首次快照，API/工件/usage关系保持，无额外模型调用。
- [ ] 3.3 恢复worker/effects OFF，核无消费任务/inflight；核旧组offset、旧unknown、其他容器/卷/迁移及全部保护材料保持。
- [ ] 3.4 撤销本批操作key并逐枚真实401；核原十reader及映射保持，以实际记录验证。

## 4. 结束审计与归档

- [ ] 4.1 整理输入→实际中间产品/调用→最终值/关系，保留失败与unknown及预算/usage区分；生成本批回执和来源/证据清单。
- [ ] 4.2 由未参与实现者做结束及撤key后独审，核0effects/最终OFF/旧事实保留与所有冻结上限；阻塞修复并复审。
- [ ] 4.3 仅在实际验收及独审通过后更新PROGRESS/能力边界并完成归档前检查，核未声称自治质量、永久常驻或整体迁移完成；随后归档与规格同步/封后校验另记audit，不预先勾选。
