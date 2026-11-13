# OpenSpec 实施说明

本项目使用 `spec-driven`。主调查变更为 [complete-socai2-investigation-chain](changes/complete-socai2-investigation-chain/tasks.md)，实际部署见 [PROGRESS](../PROGRESS.md)。当前 [Case/H HTTP 操作交付](changes/archive/2026-11-11-enable-case-human-http-flow/validation.md)已完成本地功能、限定独审和一次 21 r2 发布，并已归档；主调查整体仍 31/41，模型质量、产品页面和未验范围不由局部功能核销。

已有[独立流程审查](changes/archive/2026-11-11-review-current-investigation-flow/audit.md)及[有据结论程序修正](changes/archive/2026-11-11-ground-case-conclusions/validation.md)继续作为证据。持续模型问题按负责人决定后置并保持 NOT_PASSED，不重复采样追求通过。

[按目标的 Case 知识与 4177](changes/archive/2026-11-11-enable-purpose-aware-case-knowledge/validation.md)及[历史告警知识与模型消费](changes/archive/2026-11-12-use-historical-alert-knowledge/tasks.md)均已完成限定功能、独审、发布读回和归档；历史知识已完成 Git／父项目同步。后续 [refine-purpose-aware-knowledge-use](changes/archive/2026-11-12-refine-purpose-aware-knowledge-use/tasks.md)已完成用途／条件筛选、模型去重／任务选择及显式历史版本更新，经一次本地直接流程和独审后发布 `v1.2-20261112-r3`，实际配置、知识写读及 4177 已核验并归档，封后状态见任务和审计。模型质量 NOT_PASSED、产品页面 P01–P04及自动处理继续保留；只做最少直接验证，不新增权限专项或复杂可用性测试。

[sync-saved-alert-knowledge](changes/archive/2026-11-12-sync-saved-alert-knowledge/tasks.md)已完成新采用 A 分诊提交后同步、本地一次直接流程、独审及 21 r5 实际加载读回；知识回执独立，旧请求不重派。生产未新增分析 Run，消费者保持关闭；发布审计及归档已完成，主调查完成数不变。

[独立HTTP入口](changes/archive/2026-11-12-serve-investigation-api/validation-20261112.md)已统一21:18024的43操作和正式数据目标，Case/H真实TCP及SQL读回通过、docs5同步两端；仅发布入口/写连接两文件，不包含并行模型修改。后续业务按[HTTP实施计划](../docs/investigation/http-implementation-plan-20261112.md)逐项推进，主调查31/41保持。

[Case基本管理](changes/archive/2026-11-12-manage-investigation-cases/validation.md)已完成E44–E47、两端各20次HTTP及SQL、限定独审和一次服务/Swagger发布；该批为47操作、docs6。随后[告警/事件管理](changes/archive/2026-11-13-manage-alert-incident-operations/validation.md)已完成E48–E53及两端各86次HTTP、SQL逐值读回，服务和docs7均已发布；该批53操作、50已实现/3预留501，主调查31/41保持。

[对外HTTP代码分离](changes/archive/2026-11-13-separate-investigation-http/validation.md)已完成两端18024发布、直接读回、限定独审及归档。对外查询和业务操作由独立HTTP包维护，调查内部步骤及必要内部HTTP保持原归属，53操作合同不变；本机真实保存读取、21既有数据只读复验，Swagger保留一致的docs7。[列表查询增量](changes/archive/2026-11-13-query-investigation-lists/design.md)已完成三类列表筛选、排序和分页，仅告警/事件封套新增获准两键；15项离线检查及117次候选HTTP/PG通过，两端服务与docs8已同步，发布只读复验和独审见本change。

[完整CSV导出](changes/archive/2026-11-13-export-investigation-lists/validation.md)已完成E54–E56及两端docs9。当前[事件归并统计](changes/archive/2026-11-13-summarize-incident-grouping/validation.md)补E57/F06-06，同一只读范围计数和明确压缩比例；已完成两端发布、实际读回和独立结束审计，Swagger docs10同步；发布事实以PROGRESS及本批验收为准。

[Case普通评论](changes/archive/2026-11-13-add-case-comments/validation.md)已完成E58提交、E59分页读取，本机/21真实HTTP与SQL读回通过，Swagger docs11共59操作；原57合同及任务/Run保持。发布后独立复核及归档按本change记录，采用规则由调查模块统一，附件仍未交付。

[Case附件引用](changes/archive/2026-11-13-link-case-attachments/validation.md)完成E60登记、E61目录、E62单项，两端真实HTTP/SQL及Swagger docs12同步，原59合同保持。文件上传/保存/下载已由负责人确认交业务后端，本服务不抓取文件或触发调查；独立结束审计及归档按本change记录。

## 文档职责

当前优先级为[固定范围调查收口](changes/complete-socai2-investigation-chain/fixed-flow-plan.md)；[schedule-streaming-investigation-updates](changes/schedule-streaming-investigation-updates/proposal.md)已规划更新触发、队列合并、反馈复核和知识使用，按负责人最新指令在固定流程完成后实施，尚未改变运行行为。

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

## 工作流

实施以功能完整、结果正确为先，采用最小必要适配。所有一体模块/依赖可整体原样迁入，不额外修改或测试；不为拆分暂缓模块、统一架构或补齐专项而增加工作。冗余设计及服务可用性测试/修复登记后置，OpenSpec只追踪本次实际功能变化和最少验证，不引入另一套完整性/恢复框架。未专项验证如实标记，历史失败不改写。

1. 读取根AGENTS、上述权威文档及相关完整规格；运行 `openspec list` 和 `openspec list --specs`，复用合适的活动change。
2. 新变更运行 `openspec new change <name>`，形成proposal、必要规格增量、简短design和tasks。设计仅说明本次影响及必要边界，不默认增加抽象层；原样一体迁入不新增独立改测任务。纯工具/文档/重构且无规格级行为变化时在 `.openspec.yaml` 设置 `skip_specs: true`，不创建空的规格增量。
3. 运行 `openspec validate <name> --strict --no-interactive`，沿用已有受控授权/运行边界，只核本次实际操作必要条件。旧批全量冻结、逐项计数及恢复清单不自动变成新功能前置；旧R02仍暂缓。没有明确运行范围时不改变运行开关，不新增常规逐批用户确认。
4. 按tasks实施和直接验证，留下输入→实际中间产品/调用→最终值/关系。每完成一项再勾选，失败与unknown保留；校验通过仅证明结构，不证明业务通过。
5. 由未参与实现者做结束审计，将结论/限制/证据写入change的 `audit.md` 或链接专用审计回执；补回执、来源清单及PROGRESS。发现本批阻塞先修并复审。
6. 所有实施任务和独审完成后运行 `openspec archive <name> --yes`；工具/文档change加 `--skip-specs`。复核 `openspec validate --all --strict --no-interactive` 与 `openspec validate --archived --strict --no-interactive`，检查新主规格没有把计划写成已交付。tasks只勾选已完成的归档前条件，归档操作与封后校验写入audit记录，避免提前勾选尚未发生的归档。

可用 `openspec status --change <name>` 检查产物、`openspec instructions apply --change <name>`取得CLI上下文。产物齐全不是任务完成；checkbox、证据和独审共同约束归档。按根AGENTS执行，不自动Git提交/推送。


归档记录保存在 `changes/archive/`；各批授权和结论只适用于对应范围。当前操作按用户指令、AGENTS 与相关活动 change 执行。
