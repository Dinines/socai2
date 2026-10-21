# OpenSpec实施说明

2026-10-21起，OpenSpec是本项目的变更实施规范。使用本机OpenSpec 1.13.0的 `spec-driven` schema，由CLI与根AGENTS接入；本次 `init --tools none` 未安装 `/opsx:*` 快捷指令或改写个人工具配置。

## 文档职责

| 内容 | 维护位置 |
| --- | --- |
| 服务端职责、阶段退出、路线依赖 | [范围](../docs/operations/alert-processing-scope.md)、[路线](../docs/operations/service-roadmap.md)、[完成计划](../docs/operations/completion-plan.md) |
| 实际完成、下一项 | [PROGRESS](../PROGRESS.md) |
| 固定输入、判据、原始结果、失败、来源 | 原批次计划/冻结回执及 `docs/handoff/` 清单 |
| 当前增量的需求/场景、设计、任务、审计追踪 | `changes/<change>/` |
| 经实施、验收和独审后同步的规格 | `specs/<capability>/spec.md` |
| 项目上下文和产物/操作规则 | [config.yaml](config.yaml)、[根AGENTS](../AGENTS.md) |

不导入旧SOCAI的change，不把历史回执改写成新任务完成证明。既有验收记录继续有效于原范围；当前未建立全产品规格库，不声称OpenSpec已覆盖全部已迁功能。首次接入是纯工具/文档change，使用 `skip_specs: true`，不虚构产品能力。未来规格按实际change逐批建立或补齐。

## 工作流

实施以功能完整、结果正确为先，采用最小必要适配。所有一体模块/依赖可整体原样迁入，不额外修改或测试；不为拆分暂缓模块、统一架构或补齐专项而增加工作。冗余设计及服务可用性测试/修复登记后置，OpenSpec只追踪本次实际功能变化和最少验证，不引入另一套完整性/恢复框架。未专项验证如实标记，历史失败不改写。

1. 读取根AGENTS、上述权威文档及相关完整规格；运行 `openspec list` 和 `openspec list --specs`，复用合适的活动change。
2. 新变更运行 `openspec new change <name>`，形成proposal、必要规格增量、简短design和tasks。设计仅说明本次影响及必要边界，不默认增加抽象层；原样一体迁入不新增独立改测任务。纯工具/文档/重构且无规格级行为变化时在 `.openspec.yaml` 设置 `skip_specs: true`，不创建空的规格增量。
3. 运行 `openspec validate <name> --strict --no-interactive`，沿用已有受控授权/运行边界，只核本次实际操作必要条件。旧批全量冻结、逐项计数及恢复清单不自动变成新功能前置；旧R02仍暂缓。没有明确运行范围时不改变运行开关，不新增常规逐批用户确认。
4. 按tasks实施和直接验证，留下输入→实际中间产品/调用→最终值/关系。每完成一项再勾选，失败与unknown保留；校验通过仅证明结构，不证明业务通过。
5. 由未参与实现者做结束审计，将结论/限制/证据写入change的 `audit.md` 或链接专用审计回执；补回执、来源清单及PROGRESS。发现本批阻塞先修并复审。
6. 所有实施任务和独审完成后运行 `openspec archive <name> --yes`；工具/文档change加 `--skip-specs`。复核 `openspec validate --all --strict --no-interactive` 与 `openspec validate --archived --strict --no-interactive`，检查新主规格没有把计划写成已交付。tasks只勾选已完成的归档前条件，归档操作与封后校验写入audit记录，避免提前勾选尚未发生的归档。

可用 `openspec status --change <name>` 检查产物、`openspec instructions apply --change <name>`取得CLI上下文。产物齐全不是任务完成；checkbox、证据和独审共同约束归档。按根AGENTS执行，不自动Git提交/推送。

## 当前change

后续业务顺序以[总执行计划](../docs/operations/completion-plan.md)B1—B6为准，映射原六阶段，不另立目标；自动调查包含自动触发、分诊、关闭或升级、实际取证/分析及结果交付。总规划属于纯文档change，不重复建立产品任务树，也不以规划完成代替功能通过。

[restore-alert-investigation-integrity](changes/restore-alert-investigation-integrity/proposal.md)：作为B1—B6的产品实施任务入口，现4项评估完成、11项产品/交付任务未完成。第一项B1，B2独立部分可并行；自动调查完整主线保留。playbook/反馈一体保留不额外改测，可用性专项后置，已有保护不回退。

[admit-review-only-triage-worker](changes/admit-review-only-triage-worker/status.md)对应旧R02，**暂缓、不作为功能迁移前置，0/17未执行或验收**。只新增status侧附，原五文件及hash保留，不归档成完成；CLI仍可能显示in-progress/ready，实施者必须先读status和项目上下文，不据此执行。旧模型失败、unknown和运行OFF保持。
