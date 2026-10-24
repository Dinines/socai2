# socai2 · stingAISOC

**调查新版开发与评审：** 从[调查分支入口](docs/investigation/README.md)查看设计、相对开源的变化、当前进度、已知问题、测试和共享回执。新版在`codex/investigation-working`普通项目目录开发，代码/文档提交并推送供跨机器协作；旧业务源码保持，新版独立目录，当前尚未部署或接入完整流程。下文按日期保留的旧运行状态以PROGRESS及该入口链接的最新回执为准。

本批运行已增加UEBA、enrichment和ThreatIntel/OpenSearch接线；Agents仅更新UEBA上下文，worker仍OFF。报告当前只需Markdown，详细数据流与基本验证见[full配套回执](docs/operations/full-support-migration.md)；下文candidate05等镜像/层数是此前状态。


**报告交付最新口径：** 用户确认当前只需Markdown能生成、持久保存并按Case/Run读取；PDF暂缓，HTML额外交付也不作本轮前置。复用已有Markdown主链证据，不重跑报告模型或增加格式专项；已有PDF源码/依赖/历史结果保留。

**2026-10-21追加范围：** 按原码设计迁入历史补查、Attack Path、UEBA、事件检索及IOC信誉增强的配套服务；只做可运行必需的接线和最少验证，上游未实现的后端先登记。具体源码、数据流及运行状态见[full配套迁移](docs/operations/full-support-migration.md)。


以 [beenuar/AiSOC](https://github.com/beenuar/AiSOC) 为参考，完整迁移**告警及调查服务端功能**，优先保证功能完整、结果正确，按原服务关系做最小必要适配。输入为已有告警，交付API、消息和持久化结果；前端、采集及原始事件检测不在本轮职责。

GitHub：[Dinines/socai2](https://github.com/Dinines/socai2)。固定参考 revision：`34ca18c57dd4175539e5c6dd3d04a72dc057306b`。

当前优先完成第一步：正式告警输入到自动实际调查及基本结果/报告可取。[已有主链证据](docs/operations/integrity-autonomy-r01.md)已覆盖；原partial/质量失败保持。其他入口/分支和问题修复放后续，复用已有测试与实测，复杂可用/冗余及重复校验后置。

迁移统一按[总执行计划](docs/operations/completion-plan.md)六批推进：告警链 → 默认人工调查 → 知识消费 → 自动分诊/关闭/自动调查 → 其余调查及交付 → 整体功能验收。用户已授权并行实施；自动升级后实际自动执行调查，无需人工再次点击，实际交付状态见PROGRESS。

当前工作的三个目的：迁移告警处理流程并保证功能/结果正确；结合源码对照固定版本官方文档，核清实现与声明的差距；整理架构和扩展点，方便二次开发。对应产物为[官方功能对照](docs/operations/alert-function-alignment.md)与[当前架构梳理](docs/architecture/alert-processing.md)，随实际迁移更新。

实施原则：所有一体模块可原样整体迁入，不额外修改或测试；冗余设计及服务可用性相关测试/修复登记暂缓。只补当前功能和正确性所需的最少验证，不以重构、全依赖专项或恢复矩阵阻塞迁移；原样迁入且未专项验证的能力如实标记。

**2026-10-21当前范围与下一项：** 完整迁移告警/调查（含自动分诊、自动关闭和自动升级），playbook/反馈一体源码保留、专项暂缓；启动/退出/恢复专项后置。[完整性评估](openspec/changes/restore-alert-investigation-integrity/assessment.md)已完成，现按批实施修复，实际运行/质量状态以新回执和PROGRESS为准；旧R02[暂缓](openspec/changes/admit-review-only-triage-worker/status.md)，不作为功能前置。下文R01结果及旧“下一R02”为历史交接事实，未被追认成完整功能或自治质量通过。

此前[C03-R01](docs/operations/c03-triage-review-only.md)代码隔离与定向部署已限定验收：191项断网测试通过（22项新增、169项既有直接测试），0真实模型/新业务写；仅Agents一次构建、一次替换为19f8f1a5，review_only_v1已配置、worker OFF，七只读挂载/60秒宽限保持。旧14材料表、全部告警字段、12预约/240000预留单位/3unknown、十reader、其他35容器/18卷/134迁移及消息水位保持。首次观察脚本RLS错误与189通过/2夹具失败及恢复均保留。当前28层运行定义、185 Agents/770运行Py，prompt/lock v5不变。下一按[人审准入卡](docs/operations/c03-review-only-profile-plan.md)另冻R02，验两条新A/B输入的有限真实main消费与首次结果恢复；原自治质量失败、C04/C05及后续调查/响应仍待验，整体迁移未完成。

## 当前内容

这是新项目的知识、部署适配及首批依赖迁移包。包含需求原件、模块分析、分期规划、20/21环境盘点、已知问题和本地嵌入适配；已从指定本地AiSOC参考迁入90个依赖声明/锁/构建配方。1B另迁入137个原件（134份SQL、2个初始化脚本和LICENSE），复用21现有PG/Redis完成基础设施验收。API/Fusion共987个原版构建输入/测试（含此前134份SQL）已迁入，保留来源与最小差异；已在21从源码构建两个镜像并跑通标记告警主链，见[1F回执](docs/operations/1f-alert-chain.md)。Agents/Actions另迁入591个原件并完成1G受控调查/API持久结果和dry-run验证，见[1G回执](docs/operations/1g-service-baseline.md)；完整服务端基线尚未冻结。

| 入口 | 用途 |
| --- | --- |
| [AGENTS.md](AGENTS.md) | 本项目精简工作规则 |
| [PROGRESS.md](PROGRESS.md) | 当前交接状态与下一项 |
| [OpenSpec实施规范](openspec/README.md) | 当前完整性评估/修复规划；旧R02侧附暂缓，原计划与证据保留 |
| [文档导航](docs/README.md) | 当前目标、路线、批次、分析与证据的阅读顺序 |
| [当前模块范围](docs/operations/alert-processing-scope.md) | M00—M21职责、服务组件与输入/数据交付边界 |
| [此前分析结果](docs/anal/README.md) | 用户指定的既有模块、源码、风险和六阶段分析；复用其结论 |
| [当前六阶段路线](docs/operations/service-roadmap.md) | 服务端阶段目标和退出标准，不要求全量上游或控制台 |
| [M00—M21 上游总览](docs/reference/aisoc/01-system-map.md) | 各模块源码输入输出与专题，不等同本轮迁移清单 |
| [哪些带入、哪些留旧项目](docs/handoff/retention-map.md) | 可保留知识与旧工程边界 |
| [部署适配](deploy/aisoc20/HANDOFF.md) | 既有补丁、前置文件与使用限制 |
| [需求 Markdown](docs/requirements/README.md) | 全文阅读版及之前整理的逐条需求/历史覆盖对照 |
| [配置与凭据索引](docs/operations/configuration.md) | 模型/API地址、21基础设施、私有密钥文件与加载方式 |
| [依赖优先迁移计划](docs/operations/dependency-migration-plan.md) | 第一阶段1A—1G顺序、资源映射及每批验收 |
| [首批依赖包](deploy/aisoc21/dependencies/README.md) | 依赖快照、来源校验与版本导出，未安装或部署 |

## 下一步

2026-10-21起使用[本项目OpenSpec](openspec/README.md)管理实施。后续按[总执行计划](docs/operations/completion-plan.md)继续B4自动调查正常结果修复、B2/B3质量及B5交付；B1已限定完成，产品任务继续用[现有change](openspec/changes/restore-alert-investigation-integrity/tasks.md)；旧C03-R02暂缓，不导入旧SOCAI任务或完成证明。

从 `/Users/lychee/Documents/project/SOCAI/opensource/AiSOC` 只读参考直接复制范围内代码，先迁依赖、逐批验收，必要的删除或修改先讨论。1A的90文件为依赖参考快照，包含范围外原件，不等于全部安装目标。1B已复用21 PG/Redis完成SQL、角色和Redis重启恢复验收，见[1B回执](docs/operations/1b-shared-services.md)。1C已复用21 Kafka验证消息与重启后offset恢复，见[1C回执](docs/operations/1c-shared-kafka.md)。1F当时主链与已列边界已验，原版归并事实保留；1D向量/embedding结构存取与单服务恢复已验，见[回执](docs/operations/1d-vector-embedding.md)；21独立实例16核/32GiB，Qdrant进程nofile65536。1E五角色网关真实路由/JSON结构已验，见[回执](docs/operations/1e-model-gateway.md)；1G人工调查/API持久结果与dry-run已验，2A已完成原版核对和成员重投计数修复，见[回执](docs/operations/2a-dedup-correlation.md)；2A-01后续独立身份与持久材料/关系已验，见[回执](docs/operations/2a-source-identity.md)，2B-01风险重投修复及限定验收已通过，见[风险回执](docs/operations/2b-risk-idempotence.md)，2B-02处理规则实际版本/消费/恢复限定验收已通过，见[规则回执](docs/operations/2b-policy-versions.md)，2C-01本地历史IOC证据限定验收已通过，见[IOC回执](docs/operations/2c-ioc-consumption.md)，2C-02 PG上下文读取/独立评分限定验收已通过，见[回执](docs/operations/2c-processing-context.md)，2C-03已核来源不足并验证缺源返回，见[回执](docs/operations/2c-event-ueba-sources.md)；真实事件/UEBA消费仍未通过，3A-01规则抑制持久记录及提交保护已限定验收，见[回执](docs/operations/3a-policy-suppression.md)，3A-02消息/真实模型/账本/API及盲测分类已限定验收，见[回执](docs/operations/3a-model-triage.md)，完整质量未过；3A-03缺失风险分/显式0及来源语义已限定验收（184项测试、一次真实模型），见[回执](docs/operations/3a-risk-score.md)；3A-04组织记忆认证/失败状态及真实模型消费已限定验收（194项测试、一次真实模型），见[回执](docs/operations/3a-org-memory.md)；3A-05技能认证/读取选择、真实模型消费及重启回查已限定验收（347项测试、1677 tokens），见[回执](docs/operations/3a-tenant-skill.md)；3A-06 KB认证读取、保守cutoff、实际采用文本/引用及重启回查已限定验收（236项测试、一次真实模型2095 tokens），见[回执](docs/operations/3a-kb-read.md)。KB1已进入真实prompt，模型未引用KB标记，不能外推引用或向量检索质量；3A-07近期分析员处置认证读取/采用来源及重启回查已限定验收（396项测试、一次真实模型1909 tokens），见[回执](docs/operations/3a-dispositions.md)。三条个人意见进入实际prompt，模型needs_review/自报0.65，未精确引用note或反馈ID，不作因果采用或质量通过；独立导入失败恢复保留，最终镜像只读验证通过、模型未重测。3A-08身份认证读取/失败来源/实际采用与重启回查已限定验收（496项、一次模型1781 tokens），见[回执](docs/operations/3a-identity-read.md)；五类reader已接通，图样例不证明HR历史、当前授权或完整质量。3A-09三例真实复验/5223 tokens及可靠性审计已完成，见[回执](docs/operations/3a-triage-admission.md)；分类3/3仍有p01理由缺陷，broker复现提交/重投/来源恢复阻塞，完整质量与worker准入不通过。3A-10-01持久确认/坏消息已限定验收（143项测试、26项HTTP、0真实模型），见[回执](docs/operations/3a-triage-durability.md)；只更新Agents，静默提交缺陷在所列边界已修。3A-10-02普通分诊持久结果/重投保护已限定验收（207项、55项HTTP、0真实模型），见[回执](docs/operations/3a-triage-recovery.md)，限定同worker完整材料保存恢复、fresh进程复用及unknown停止；3A-10-03-01分诊SDK0/45秒、整次45秒截止及-1 cursor已限定验收（189项、71项HTTP、0真实模型），见[回执](docs/operations/3a-triage-request.md)；3A-10-03-02持久预约/积压/停止恢复已限定验收（263项、137项HTTP、0真实模型），见[回执](docs/operations/3a-triage-budget.md)；3A-11-01复核及11-02配置已完成，当时原计划为[3A-11-03理由修复](docs/operations/3a-triage-reasoning-plan.md)，C02现已限定通过，C03-01提示词已限定通过，C03-02已按质量失败封存，02B分类通过但授权理由失败已受控停止，v4传输已限定通过，下一另冻新四例质量复验；完整调查/知识/响应按后续阶段验收。阶段一要求范围内服务构建输入齐全、可复现构建，不迁控制台或要求完整上游全栈。当前不合并旧stingAISOC业务实现与OpenSpec。

新项目部署目标为 **192.168.1.21**；21 的4个旧业务容器已经正常关闭，保留基础设施和数据。20 是已有 AiSOC 参考环境。新API/Fusion仅绑定21 loopback的18000/18003，真实Bearer认证、非demo；使用方法与限制见1F回执。Agents/Actions已部署到21 loopback18004/18005，自动worker和真实响应关闭；API当前为integrity-20261021，Agents为integrity-report-semantics-20261021，Fusion为integrity-b1-20261021，须使用[二十九层运行命令](deploy/aisoc21/README.md)。[B1入口](docs/operations/integrity-b1.md)已限定验收；[首轮人工调查](docs/operations/integrity-b2b3.md)原质量失败保留；新人工Run四模型10167 tokens、MD/HTML/PDF已可交付，内容质量仍有边界问题。实际已部署B4/B5源码与引用/工具身份修复，有限自动C1正确关闭，C2已自动调查但partial/内容失败，保留失败并最小修复；candidate05默认报告两文件修复已部署，0新模型，不追认原报告通过。完整迁移尚未完成。

旧工程 `/Users/lychee/Documents/project/SOCAI` 留作历史代码、证据和数据归档；26个旧 change 已封存且未同步主规格。这里不复制旧 `.git` 和调查大目录。用户授权复用已有知识和本地模型，已核旧知识429文件约5GB及本地4B候选；按[知识复用与负载计划](docs/operations/knowledge-data-reuse-plan.md)选材/索引和分配20、21，不默认整目录迁入。用户于2026-10-20要求保留配置后，现有秘密配置已单独保存在被 Git 忽略的 `.local/configuration/2026-10-20/`，不提交到GitHub。
