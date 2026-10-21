# 初始化过程记录（历史归档）

2026-10-20归档。本文保留当日逐次范围调整与初始化过程，当前状态以[PROGRESS](../../../PROGRESS.md)为准；其中早期全量计划不再是当前目标。

---

# 当前进度

2026-10-20：用户确认新目录 `/Users/lychee/Documents/project/socai2`、GitHub `Dinines/socai2`。最新职责为告警及后续数据处理服务端，前端不考虑；按范围逐步移植、测试冻结、再二次开发。以下较早的全量计划/盘点作为历史记录保留。

- 已准备：需求原件、14 份模块/规划 Markdown、参考 hash 快照、部署说明及本地 embedding 适配、精简协作规则、环境/证据/问题/保留清单。
- 尚未执行：上游完整源码导入、关键服务源码构建、新部署、完整模块/业务验收和二次开发。
- 既有 20 环境记录作为历史实测输入，不把资料复制计作新验收；Chat/embedding 与知识/调查质量分开。
- 已初始化main；origin=Dinines/socai2，upstream=beenuar/AiSOC。GitHub远端核对为空；未提交/推送。
- 用户确认21为新部署目标。旧4个业务容器已正常退出并设restart=no；26其他容器/数据保留。20为参考环境，新应用尚未部署21。
- 旧26个change已历史封存，44未完成任务保持，39增量未同步主规格；回执见docs/handoff/legacy-change-closure.json。
- 2026-10-20补充：已带入旧需求覆盖Markdown（35子组、164功能细项），另提取需求全文（413段/387非空文本段、3表、3图）；旧覆盖状态仅历史参考。见docs/requirements/README.md。
- 同日按用户要求将20运行/管理员、21基础设施及已有模型API实际凭据保存至Git忽略的.local/configuration/2026-10-20，目录0700/文件0600。35个汇总变量及地址/加载说明见docs/operations/configuration.md；未重配服务或调用模型，SOCAI2_*尚未接入应用。
- 上述交接验证：10个私有文件权限/忽略规则及原件hash通过，公开文件未检出所复制密钥；387非空原文段逐段匹配、3图hash及252本地链接通过，交接manifest已更新，diff check通过。
- 同日初始化1A：用户明确以本地 `SOCAI/opensource/AiSOC` 为只读来源，允许复制，逐步迁入、依赖优先，必要删除/修改先讨论。已迁90个依赖原件并核对来源/blob/hash/权限，13个Python服务main/all精确版本导出，上游导出自测26项通过；依赖未安装、镜像未构建、21未部署。
- 20/21只读盘点完成：20基础Compose/官方应用revision/overlay对应；21的30容器（22运行、8退出）、18卷与关闭回执比较无变化。1A—1G及资源规划见docs/operations/dependency-migration-plan.md，证据见initialization.md。
- 初始化中短暂完整导入的13,635文件已按本轮hash核对后移入Git忽略的.local/initialization/full-source-staging/，未删除，未计作业务迁移；原.gitignore按hash恢复。业务源码继续分批迁入。
- 用户指出docs/anal保存此前分析，已纳入阅读和依赖计划入口；复用模块/源码/风险/六阶段结果，保留anal原件与reference交接版，不重复分析或擅自合并。
- 澄清Go为上游ingest/enrichment等部分服务的按需构建工具，Fusion告警核心使用Python；当前不安装Go，宿主机无需Go编译器。已修订依赖计划措辞，未删除服务或改变接入链路。
- 用户进一步限定只处理告警及后续数据、只做服务端。已新增M00—M21职责对齐并收敛1F/1G：取消ingest采集/规范化、前端/控制台、独立Realtime为迁入前置；保留告警受理、Fusion、分诊调查、知识/上下文消费、Case/账本、审批响应和反馈数据能力。未删原件、未改业务/部署；90依赖原件及13服务导出仍属原参考盘点，不全部安装。

**下一单项：** 按依赖计划1B准备独立PostgreSQL/Redis、原初始化脚本及完整API SQL链；核资源归属后仅验该批角色/持久化与标记测试数据。不要自动继续旧SOCAI的Basic任务。
