# OpenSpec 实施说明

调查主线见[主调查设计](changes/complete-socai2-investigation-chain/design.md)与[任务](changes/complete-socai2-investigation-chain/tasks.md)。流式更新沿[本期任务](changes/schedule-streaming-investigation-updates/tasks.md)、[范围及归档条件](changes/schedule-streaming-investigation-updates/closeout-scope-20261118.md)和[后置范围](changes/schedule-streaming-investigation-updates/deferred-scope.md)收口；人工定向分析、手动全案综合、知识后台异步维护保留未实施状态。当前运行及分阶段交付见[PROGRESS](../PROGRESS.md)，接口使用见[交接指南](../FRONTEND_BACKEND_HANDOFF.md)。文档或结构审计完成不能代替业务验收与整项交付。

已结束功能的规格、验收及独审在[change归档](changes/archive/)；此前逐批发布说明保留在[11-14整理前记录](../docs/handoff/history/2026-11-14-investigation-cleanup/snapshots/openspec/README.md)。旧批次的版本、授权和完成声明不替代当前状态；模型质量后置仍为NOT_PASSED，局部交付不核销主调查整体。

## 文档职责

当前优先级为[固定范围调查收口](changes/complete-socai2-investigation-chain/fixed-flow-plan.md)与[流式更新交付](changes/schedule-streaming-investigation-updates/proposal.md)；当前目标采用独立任务排队、执行前检查及事件驱动Case更新，跨task合并已取消。反馈复核沿已确认范围，人工定向及知识后台异步维护后置，正式运行行为尚未切换。

| 内容 | 维护位置 |
| --- | --- |
| 服务端职责与功能顺序 | [范围](../docs/operations/alert-processing-scope.md)、[当前调查设计](changes/complete-socai2-investigation-chain/design.md#后续工作顺序)、[历史迁移计划](../docs/handoff/history/2026-11-11-local-cleanup/operations/) |
| 实际完成、下一项 | [PROGRESS](../PROGRESS.md) |
| 固定输入、判据、原始结果、失败、来源 | 原批次计划/冻结回执及 `docs/handoff/` 清单 |
| 当前增量的需求/场景、设计、任务、审计追踪 | `changes/<change>/` |
| 经实施、验收和独审后同步的规格 | `specs/<capability>/spec.md` |
| 项目上下文和产物/操作规则 | [config.yaml](config.yaml)、[根AGENTS](../AGENTS.md) |

不导入旧SOCAI的change，不把历史回执改写成新任务完成证明。既有验收记录继续有效于原范围；当前未建立全产品规格库，不声称OpenSpec已覆盖全部已迁功能。首次接入是纯工具/文档change，使用 `skip_specs: true`，不虚构产品能力。未来规格按实际change逐批建立或补齐。

交付按一个 change 走一次完整流程：先在本地完成设计、实施、完整流程测试、交接文档和独立结束审计，再统一发布到获准环境；核实部署与读回、补齐回执后，统一推送最终 Git 内容并同步父项目引用。同一 change 不随每次小修反复更新 21 或推送远端，除非用户明确要求分阶段发布。具体长期规则见根 AGENTS；发布节奏不替代验收，也不扩大既有授权。

这里的完整流程指本次功能从输入、处理到保存、读取的业务闭环。验收复用已有证据，只补正常路径及直接受影响的结果；不以测试数量、全量字段对账、多轮模型比较或可用性专项作为功能交付前置。每次只展开下一项功能，不为后续全部模块提前建立测试工程。

## 阶段规划与分步执行

这是全项目的实施约束，适用于后续智能体、会话和各个阶段。每个阶段开始修改前，先在所属 change 的现有设计和任务中理清整体安排；已经写清的内容复用，不另建平行任务树。

| 实施前必须写清 | 所需内容 |
| --- | --- |
| 阶段目标与范围 | 本阶段解决的问题、纳入和排除的范围、完成后用户或调用方会看到的具体效果 |
| 步骤及依赖 | 分成哪些可验证步骤、先后关系、本轮只做哪一步，以及该步的完成边界 |
| 必要测试 | 复用哪些已有测试/原答/快照，本次只补哪些直接行为；区分离线、替身、真实数据库、真实模型、实际来源及页面查看 |
| 验证与判据 | 如何沿输入→处理→保存→读取核对原值和关系，预期结果是什么，用什么证据判断通过；哪些失败或未验状态必须保留 |
| 收口与下一步 | 本步结果记录到哪里，哪些条件满足后才能进入依赖步骤，阶段完整验收还缺什么 |

先向用户说明整体阶段安排及本轮落点，再在已有授权范围内实施。每轮执行一个明确步骤，完成修改后立即做该步直接验证，记录并回报实际结果；发现阻断先定向修复和复验。不得把整个阶段包装成一个大任务，在同一会话执行中同时修改所有独立问题，再把验证集中到最后。整体计划说明必要验证，不要求提前建设后续步骤的测试工程。

分步执行与一个 change 统一交付并行适用：步骤通过不等于整个阶段/change完成，也不触发发布、推送或归档；授权范围内不新增逐步审批。用户明确调整本轮范围时，先同步当前任务落点，保留未验证草稿及其状态，不记为已交付。

## 工作流

实施以功能完整、结果正确为先，采用最小必要适配。所有一体模块/依赖可整体原样迁入，不额外修改或测试；不为拆分暂缓模块、统一架构或补齐专项而增加工作。冗余设计及服务可用性测试/修复登记后置，OpenSpec只追踪本次实际功能变化和最少验证，不引入另一套完整性/恢复框架。未专项验证如实标记，历史失败不改写。

1. 读取根AGENTS、上述权威文档及相关完整规格；运行 `openspec list` 和 `openspec list --specs`，复用合适的活动change。
2. 新变更运行 `openspec new change <name>`，形成proposal、必要规格增量、简短design和tasks；已有change原位补齐。按上述阶段规划先明确整体目标、预期效果、分步范围、必要测试及验收证据，再选择本轮一步。设计仅说明本次影响及必要边界，不默认增加抽象层；原样一体迁入不新增独立改测任务。纯工具/文档/重构且无规格级行为变化时在 `.openspec.yaml` 设置 `skip_specs: true`，不创建空的规格增量。
3. 运行 `openspec validate <name> --strict --no-interactive`，沿用已有受控授权/运行边界，只核本次实际操作必要条件。旧批全量冻结、逐项计数及恢复清单不自动变成新功能前置；旧R02仍暂缓。没有明确运行范围时不改变运行开关，不新增常规逐批用户确认。
4. 按tasks只实施本轮选定的一步，随即直接验证并记录输入→实际中间产品/调用→保存/读取的最终值与关系；本步完成并回报后再推进下一步，不提前同时铺开后续独立修改。每完成一项再勾选，失败与unknown保留；校验通过仅证明结构，不证明业务通过。
5. 由未参与实现者做结束审计，将结论/限制/证据写入change的 `audit.md` 或链接专用审计回执；补回执、来源清单及PROGRESS。发现本批阻塞先修并复审。
6. 所有实施任务和独审完成后运行 `openspec archive <name> --yes`；工具/文档change加 `--skip-specs`。复核 `openspec validate --all --strict --no-interactive` 与 `openspec validate --archived --strict --no-interactive`，检查新主规格没有把计划写成已交付。tasks只勾选已完成的归档前条件，归档操作与封后校验写入audit记录，避免提前勾选尚未发生的归档。

可用 `openspec status --change <name>` 检查产物、`openspec instructions apply --change <name>`取得CLI上下文。产物齐全不是任务完成；checkbox、证据和独审共同约束归档。按根AGENTS执行，不自动Git提交/推送。


归档记录保存在 `changes/archive/`；各批授权和结论只适用于对应范围。当前操作按用户指令、AGENTS 与相关活动 change 执行。
