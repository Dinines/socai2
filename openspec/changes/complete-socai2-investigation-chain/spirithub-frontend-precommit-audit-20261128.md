# SpiritHub 前端提交前范围核查

## 本次完整 main 整合与发布交接

负责人最新明确要求提交当前项目 `main` 和父项目 SpiritHub `main`，并说明前端、平台后端、调查 HTTP、Fusion、调查执行及 LLM 代理的发布方式。本步完成源码整合与 Git 交付、部署说明，不据此自动重启线上服务，也不将仍未验的功能或模型质量标记为完成。

本次重新取得的 SpiritHub `origin/main` 为 `83a4f5ef3fd893aa7f49f6c71c852cce7428b818`；下文 `1cd0ff1` 及逐路径表是前次源审基线，保留其历史含义。父项目当前 `server` 引用的对象无法由配置的子项目远端获取，应在本次提交中更新为实际已推送且核对过的 socai2 提交；保留父项目历史，不强推或改写旧提交。

1. 模块会话盘点完整源码、必要合同/共享依赖、配置示例、构建/部署入口与既有测试证据；统筹核所有未提交路径。运行配置、原始材料、模型原答和生成的查阅快照留本机，不能随源码批量暂存。工作区其他修改保持。
2. socai2 按完整调查链交付可运行的源码及必要配置/文档，不只提交最近的 18 文件发布补丁。告警交接合同保持既有确认范围，I 输出精简仍为方案。未实施或未验项目明确留在任务清单，不归档整个 change。
3. SpiritHub 使用普通独立工作树 `SpiritHub-main-integration-20261128`，从本次远端 main 整合 8181 实际前端及平台中转改动。前端、后端与共享合同逐项处理冲突，保留 main 的扫描、助手和其他模块更新；不以旧整文件覆盖它们。普通平台的 Q34/Q35、调查 POST、配置工厂和部署传参均纳入依赖核对。
4. 合并后的 OpenAPI 保留非 SOC 方法，生成类型由最终合同重建。复用已有有效测试；仅对冲突解决、依赖接线及最终组合运行必要的桥接测试、前端类型检查/构建和相关组件测试。没有业务特判、伪造默认值或用于测试的生产替身。
5. 在现有 21 部署手册补齐模块、构建/镜像、配置字段、监听与上下游、启动顺序、最小正常验收和按版本回退的对应关系；实际地址和凭据由受控 profile 提供，不写进 Git。
6. 统筹检查暂存内容、凭据/私密材料边界和依赖后提交，普通推送 socai2 `V1.1/main` 与 SpiritHub `main`，核远端 SHA 和父项目 gitlink。固定同步技能的 `plan` 用于核对基线；其默认仅更新父项目 `add-server-submoudle` 的 gitlink，不能代替本次完整前后端 main 合并，因此本次完整父项目使用已审普通 Git 合并/推送，不改写该技能或 Git 配置。
7. Git 交付与实际部署分开记录：代码到达 main 不等于新 HTTP 路由或普通平台 POST 已上线。现有候选服务和恢复点保持，实际发布按手册及明确目标执行。

本步源码整合与直接核对已完成：前端类型检查、live 生产构建及受影响失败项的定向复验通过，平台 bridge 34 项和原生 HTTP 边界 4 项通过。最终源码、生成类型与构建输入指纹已由统筹再次核对，非 SOC 的 212 条路径与 378 个可达组件保持 main 原样。无原生实现的旧 Q 声明撤下，现用页面改接保存身份所指向的正式读取入口；原先候选 Q09 专用测试随退役路径撤下。下面逐路径表保留采集时状态，最终范围及限制以 [完整 main 交付记录](../../../docs/operations/evidence/main-integration-20261128-01/README.md) 为准。

2026-11-28 初始采集。8181 的 Vite 工作目录是 `/Users/lychee/Projects/SpiritHub-web-8181/web`，所属 Git 根目录是 `/Users/lychee/Projects/SpiritHub-web-8181`。实际分支为 `codex/spirithub-4173`，HEAD `8051df5`，本地缓存的同名远端引用相同，当前分支未设置 upstream。已提交的一笔告警变更涉及 45 个路径。采集时工作树有 36 个已跟踪修改和 36 个未跟踪文件，索引与 HEAD 一致。两组去重后共 107 个路径，含浏览器侧文件、平台中转及合同文件。本文及指纹以该次采集为准。 [逐路径指纹、索引与目标树对照](/Users/lychee/Documents/project/socai2/openspec/changes/complete-socai2-investigation-chain/spirithub-frontend-precommit-sources-20261128.json)

## 与 main 的比较

统筹已独立取得 SpiritHub `origin/main` 的 `1cd0ff1`，标准父项目本地缓存一致。告警提交的父提交 `bb368df` 是该 main 的祖先，main 自共同基线有 137 笔提交。`8051df5` 未进入该 main 历史。标准父项目工作区当前在旧 `add-server-submoudle`，其本地 `main` 与当前 `origin/main` 的历史分开。三方核查以实际 8181 源树、共同基线和当前 `origin/main` 为准。8181 工作树为浅克隆，可见 HEAD 和共同基线。 [标准父项目](/Users/lychee/Documents/project/SpiritHub) · [统筹上游路径重叠](/Users/lychee/Documents/project/socai2/.local/validation/model-exceptions-release-coordinator-20261128-01/spirithub-upstream-overlap.json)

| 与 `origin/main` 核对结果 | 路径数 | 核对口径 |
| --- | ---: | --- |
| 当前整文件等同 main | 0 | 按 Git blob 和文件模式核对。方法级相同项单列。 |
| main 上新增文件 | 49 | 共同基线和 main 均无该路径，当前源树有文件。 |
| 仅当前候选修改 | 10 | 共同基线已有文件，main 该路径仍为基线内容。 |
| 两边同路径改动 | 48 | 包含 main 新增、修改或删除的路径。代码归并时逐段核对，文件重叠本身不足以判定冲突。 |

平台 OpenAPI 中候选自基线变更的 12 个方法都在 `/api/v1/socai2/`，其中 8 个与 main 同方法并行修改。main 另有 16 个非 SOC 方法变化。提交时在 main 的合同上合入已核对的 SOC 方法和组件，随后用现有 `api:generate` 生成 `live.ts`，并核对非 SOC 方法和类型。生成脚本也会写 `mock.ts`，其差异以 main 的 mock 合同为准。内部 `bridge_contract.json` 有 19 个并行且不同的方法，`GET /api/v1/socai2/cases` 的定义已与 main 等同。优先核对方法、响应状态和对应组件，生成文件的文本差异仅作定位。 [三方合同明细](/Users/lychee/Documents/project/socai2/openspec/changes/complete-socai2-investigation-chain/spirithub-frontend-precommit-sources-20261128.json) · [生成入口](/Users/lychee/Projects/SpiritHub-web-8181/web/package.json)

旧告警概况组件在候选中已删除，main 也改过该路径。整合时同时核本批 `/alerts`、`/alerts/runs` 和仍在使用的旧入口调用。共享路由、调查 Run 工作区、Case 壳、记录抽屉和两份平台合同也有并行改动。逐文件的比较状态见下表。 [告警路由](/Users/lychee/Projects/SpiritHub-web-8181/web/src/app/router.tsx:59)

`server` 是独立 gitlink。8181 的共同基线、HEAD 和索引均指向 `09010dc`，`origin/main` 的 gitlink 为 `39917f9`。`origin/add-server-submoudle` 的 `dcd5f99` 自其与 `origin/main` 的共同基线 `048668b` 变更了 `README.md` 和 `server`。前端与中转的合入以适用代码和合同的树差异为准，`server` 引用由统筹单独核对。 [各树的 gitlink 指纹](/Users/lychee/Documents/project/socai2/openspec/changes/complete-socai2-investigation-chain/spirithub-frontend-precommit-sources-20261128.json)

## 平台配套与当前边界

### 本轮整合顺序与直接验收

用户已要求先完成当前调查测试与独立验收，再提交 SpiritHub 前端、中转及必要依赖，并尝试合入 main。此前仅授权评估、尚未授权 main 的记录不作为本轮限制。当前先做源码范围和依赖核查，不提前提交或推送。

1. 当前 21 的 S1/S2/S3 限定发布和唯一正常 Case 新任务先收口；保留原失败记录，运行结果按数据边界集中核验。事件输出精简未实施，不混入该批。
2. 8181 实际源树的前端、平台中转和合同按本文清单形成候选，两处共享图扩展纳入当前完整提交范围。Q34/Q35 普通中转补接按独立增量收录。核对 socai2 Git 内的原生路由、用例、适配和合同依赖，并按本文记录的实际功能边界确认交付。
3. Git 操作由统筹执行。提交前复核候选指纹、共享默认行为和最少相关检查；保留其他工作树修改，不整仓暂存。使用普通独立工作区合并最新 main，逐段解决源码及合同差异，不以旧整文件覆盖非 SOC 变化。保留 main 的其他模块和同路径已有业务方法，再由合并后的 Schema 生成类型。
4. 对最终组合仅运行本文所列受影响入口的现有定向测试、类型检查和必要平台桥接检查；异常或合同失败只修该阻断。通过后普通推送对应分支并尝试合入 main，复核远端提交和 server gitlink。若远端推进或主分支保护阻断，保留已完成候选并按实际状态续做，不强推。

统筹的只读三方预检已区分真实内容冲突与路径重叠，包含正文冲突、删除/修改冲突、两个 JSON 合同的语义整合和生成类型重建；这只是整合输入，不是已经完成合并或验证。源码级明细见 `.local/validation/model-exceptions-release-coordinator-20261128-01/parent-preflight-01/source-preflight.json`，预检不修改原工作树或 Git 索引。

已有 28085 运行回执绑定本机验证候选 `platform-local-candidate`。原始采集快照的平台注册和转发合同缺 Q34/Q35 两个 GET，平台 OpenAPI 与前端类型已有声明。本轮再核时，这两个 GET 已出现于 8181 工作区的平台路由和桥接合同，统筹按独立增量收录。正式 `POST /cases/{case_id}/investigations` 已在平台源码完成 202 登记及独核，实际平台发布和业务读回仍待。原指纹清单记录初采内容和当时的图扩展范围判断，当前纳入范围见本文。 [已保存运行候选回执](/Users/lychee/Documents/project/socai2/docs/operations/evidence/case-info-migration-20261127-01/platform-runtime.json) · [原始指纹](/Users/lychee/Documents/project/socai2/openspec/changes/complete-socai2-investigation-chain/spirithub-frontend-precommit-sources-20261128.json) · [当前平台登记](/Users/lychee/Projects/SpiritHub-web-8181/backend/src/spirithub/api/routes/socai2.py:73)

M0g 已完成普通 8181 的页面只读回读并复核 4177 固定 Run 元数据。对象证据的 Q12、旧 Q08 在本批仍有读取缺口，原生失败来源保留未核实。调查概览仍挂旧 E11/E13，正式 `POST /cases/{case_id}/investigations` 的检查更新前端接线待安排。G1 关系图覆盖已有底图只读能力，探索候选及保存仍属于后续阶段。固定轮原件正文继续按已核实的路径和可用性记证。 [M0g 页面清单](/Users/lychee/Documents/project/socai2/openspec/changes/complete-socai2-investigation-chain/case-m0g-frontend-audit-20261128.md) · [两轮更新交接](/Users/lychee/Documents/project/socai2/openspec/changes/complete-socai2-investigation-chain/case-multirun-frontend-handoff-20261127.md:18) · [关系图 G1 回执](/Users/lychee/Documents/project/socai2/docs/operations/evidence/case-graph-migration-20261127-01/README.md:19)

## 纳入本轮的两处共享图形扩展

- `AlertObjectGraph.tsx` 的增量包括 `MemberWorkspace`、`memberWorkspace`、`memberRefs`、成员联动和来源检查。可选模式只从实际成员行的 `latest_material_id` 补一个未重复的材料引用，物证边仍按成员及对象原引用生成。缺失的来源路径用未记录状态展示。原模式继续接受成员与对象输入，链接编码也适用于原模式。 [成员工作区参数](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/AlertObjectGraph.tsx:9) · [来源引用](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/AlertObjectGraph.tsx:25) · [共享图调用](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/AlertObjectGraph.tsx:38)
- `RelationGraph.tsx` 的增量包括 `GraphWorkspace`、`workspace`、`selectNodeFromPanel` 和成员面板、关系列表、页脚、来源检查。节点和连线取真实输入，面板选择可解除遮挡节点的类型筛选。当前 CSS 仅有双列网格，可选模式增加第三个直接子项后会在宽屏换行，画布落入固定侧栏宽度。后续若启用该模式，限定在 `data-leading-panel` 下补布局，并验证宽窄容器及筛选、来源联动。 [工作区布局代码](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/RelationGraph.tsx:82) · [现有网格样式](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/RelationGraph.css:5)

核查覆盖 8181 的生产导入、JSX 调用和参数透传，含未跟踪源码。8181 当前路由无 `AlertObjectGraph` 挂载，固定 Run 直接使用 `RelationGraph` 的默认模式。旧 `CaseExploration` 内经 `CaseRelationGraph` 透传的调用也沿用默认模式，现有 Case G1 页由 `CaseGraphView` 渲染，事件关系页由 `IncidentRelations` 渲染。`origin/main` 的旧 Case 成员图仍调用 `AlertObjectGraph` 默认模式。两处增量可按共享组件合入，现有页面按真实调用取数，可选模式的产品接线仍未完成。 [固定 Run 图入口](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:236) · [Case 图包装](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseRelationGraph.tsx:29) · [旧 Case 探索组件](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseExploration.tsx:72) · [Case G1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseGraph.tsx:116) · [事件关系页](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentWorkbenchDetail.tsx:129)

复用 `RelationGraph.test.tsx` 的 4 项组件检查全部通过，验证默认筛选、键盘来源选择、布局保存边界及图上告警材料绑定。该文件使用测试替身，当前用例均走默认模式。 [组件检查](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/RelationGraph.test.tsx:8)

## 生产入口与业务真实性审计

107 个路径包括 71 个浏览器生产 TS/TSX、11 个样式、1 个生成类型、1 个已删除旧入口、6 个平台配套和 17 个测试。以正常路由及可达组件核对取数、写入、错误、空态和字段投影。扫描了固定身份或样本值分支、模拟响应、异常替代和默认数值，再逐入口复核命中分支。当前核查范围内未发现按测试样本选择业务逻辑或回填模拟业务响应的生产实现。下列真实问题涉及正式回执读取、未完成的合同接线和状态展示。 [路由](/Users/lychee/Projects/SpiritHub-web-8181/web/src/app/router.tsx:35) · [业务 HTTP 客户端](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/api.ts:44)

### 页面与实际依赖

下表省略 HTTP 前缀 `/api/v1/socai2`。既有真实验收沿用其对应回执。本次复核结果是源码和本地组件证据，页面的运行验收按实际候选与对应入口确认。

| 入口 | 已接线的真实数据和操作 | 当前差异与最低限度修正 |
| --- | --- | --- |
| 告警列表与人工操作 | `GET /alerts`、人员目录、正式告警导出，E48/E49 判定和 E50/E51 管理使用实际行版本和操作键。 | 初载、失败、权限和成功空列表有独立状态。列表和详情共用下列已挂载的分配回执入口。 [列表](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/AlertWorkbenchList.tsx:70) · [写入](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/SubjectCommands.tsx:49) |
| 告警概览与相似历史 | E28/E22 读事实及原分诊，E30/E31 读对象、资产、原件，Fusion、来源 OCSF、AI 置信度各取原字段。E70 读相似历史，人工判定继续走 E48/E49。 | 概览相关告警当前读 E30 `related_alerts`。交接指定该区域使用 E71 `GET /alerts/{alert_id}/same-host-alerts`。当前平台注册、桥接合同、公开合同和页面均缺这条接线。 [告警概览](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/AlertWorkbenchDetail.tsx:192) · [相似历史](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-alerts/alertReviewApi.ts:10) · [E71 交接](/Users/lychee/Documents/project/socai2/docs/integration/alert-host-http.md:3) |
| 告警原始材料、时间线及响应 | E31 读指定材料，E30 读来源、工件和活动，E22 读分诊目录。响应页读关联调查、原建议、已保存审批与执行回执。 | 材料版本界面显示当前及已指定的历史材料，完整目录和历史材料来源仍有缺口。关联调查仍用旧 Q08 `GET /runs?alert_id=…`。响应记录按保存回执展示。 [原件](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-alerts/AlertWorkbenchRaw.tsx:35) · [活动](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/AlertWorkbenchDetail.tsx:299) · [响应](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-alerts/AlertResponse.tsx:25) |
| 告警固定分诊和原件 | `/alerts/runs/:runId` 经 Q27/Q28/Q29、E24 与 trace，核主体、轮次、步骤和工件身份并读取返回的原件地址。 | 有分页、明确来源和不可用展示。共享 Run 子视图中的目录状态误报见下文。 [固定分诊](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/AlertTriageRunPage.tsx:21) · [分页和原件合同](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/alertTriageApi.ts:22) |
| 事件列表与预览 | E27 列表、E57 归并统计、正式导出。预览读 E29 和 E30 成员与资产。活跃数、成员数、来源和归并率使用服务端字段。 | 来源缺失、输入未记录和读取错误分别展示。E57 在平台注册和桥接合同中存在，公开平台 OpenAPI 尚缺。 [列表与统计](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentWorkbenchList.tsx:115) · [预览](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentPreview.tsx:67) |
| 事件详情、关系与活动 | E29 及 E30 的成员、对象、资产、活动、关联 Case。已发布诊断从保存指针进入固定事件 Run。事件图按成员与对象来源生成关系，E52/E53 执行真实管理。 | 成员和活动页面的部分筛选作用于已载入记录。对象风险等未提供字段仍显示未提供。该详情的诊断入口是保存内容读取，正式重新受理 E37 尚无本页实现或验收。关联、建案见旧回执差异。 [事件入口](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentWorkbenchDetail.tsx:65) · [诊断](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentDetailContext.tsx:109) · [事件图](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentRelations.tsx:143) |
| Case 队列、创建、关联与移动 | E02 队列及过滤导出、E01 创建、E08 关联、移动接口。Case 队列和案内选择器校验实际分配、接收案与 `initial_task`，随后 Q31 回读任务。 | 类别与来源栏目前显示未提供，维持合同缺项。平台对外 OpenAPI 的 E01/E08 成功体仍声明旧 `Socai2AssociationReceipt`，桥接已声明 `Socai2CaseAllocationReceipt`。相同正式回执应覆盖告警、事件与 Case 的正常入口。 [队列](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchList.tsx:63) · [分配校验](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-entry-api.ts:64) · [正式分配合同](/Users/lychee/Documents/project/socai2/docs/integration/case-allocation-http.md:33) |
| 告警／事件发起 Case | 8181 共享 `CaseAssociation` 已复用 `caseEntryApi` 与 `caseAllocationTarget`，E01/E08 正式回执确定实际接收案及首轮任务。 | 初采源码读取旧 `receipt.case_id` 的问题已在 8181 挂载修正。两文件后像与独核候选一致，配合现有 E03/Q31 读回。 [已挂载入口](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/SubjectCommands.tsx:157) · [正常告警按钮](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/AlertWorkbenchDetail.tsx:170) · [正常事件按钮](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentWorkbenchDetail.tsx:104) |
| 案件资料 | E03、Q36、保存判断的 Result／任务修订及引用原件。按 `scope_revision` 检查汇总，采用来源、原范围、覆盖及当前范围分开。 | Q36 汇总与已采用依据有既有本机验收。跨轮覆盖和材料聚合仍缺，事件类别显示未记录。 [资料与范围](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInfo.tsx:34) · [原结果和任务修订](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInfoAssessmentSource.tsx:96) |
| 案件故事 | Q13 `GET /cases/{case_id}/story?view=related`、Q33 焦点成员关系，告警材料、精确 Run 与人工修订按保存来源读。 | 当前已挂载的只读故事区分失败、真实空目录、材料版本变化和受限范围。已独验切片按其原指纹复用。 [故事入口](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseStory.tsx:65) · [Q33 校验](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/workbench-api.ts:35) |
| 调查概览 | 8181 源码已挂载正式 `check/rerun`、Q30/Q31 及固定轮入口，沿 E03/E10 读取既有记录。 | 文件与组合依赖均通过独核并匹配原检查指纹，Q31 终态刷新同案 Q36 摘要。正式平台新 POST 的实际上线和普通入口仍待核验。 [当前提交入口](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigationOverview.tsx:26) · [正式提交路由](/Users/lychee/Documents/project/socai2/services/api/investigation_http/external_routes/analysis_submissions.py:29) · [前端方案和结果](/Users/lychee/Documents/project/socai2/openspec/changes/complete-socai2-investigation-chain/case-multirun-frontend-handoff-20261127.md:18) |
| 调查历史及成员告警 | 历史用 Q34/Q35，固定轮再读 E12/E14 或告警、事件原主体。成员读 E03 及关联的告警资产，明确提示成员截断。 | Q34/Q35 已在当前平台源码补齐。旧仅 Result 链接通过 E14 解析原轮。普通历史与对象证据的旧按调查入口分别使用不同目录。 [历史入口](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigationHistory.tsx:70) · [成员与资产](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchDetail.tsx:86) |
| 案件图与关联探索 | Case G1 用 E69/E67 读已保存快照和底图，Q34/Q35 选轮与显示原轮。默认底图只在快照明确为空时加载。 | G2/G3 的候选、加入和保存还没有正常页面接线，旧 `CaseExploration` 文件当前无路由挂载。固定 Run 仍链接 `?explore=1`，当前目标页只显示 G1。将链接改为真实可读的固定轮底图入口，或在探索未接线时收起该按钮。 [G1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseGraph.tsx:28) · [旧探索](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseExploration.tsx:39) · [Run 跳转](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:236) |
| 对象与证据 | Q12 对象、E05 证据目录、告警资产和原材料。按调查仍走 E10 加旧 Q08 `GET /runs?case_id=…`。 | Q12 和旧 Q08 的 8181 原验证有读取缺口，原生失败来源待核。保持错误展示，查 Q12 实际上下游响应。按调查可复用已核身份的 Q34/Q35 与固定轮读，验证需要保留的事件和告警来源。 [对象取数](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseEvidence.tsx:20) · [旧目录](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigations.tsx:16) · [既有只读审计](/Users/lychee/Documents/project/socai2/openspec/changes/complete-socai2-investigation-chain/case-m0g-frontend-audit-20261128.md:61) |
| 人工任务、活动、评论与附件 | E38–E43 任务和修订，E17 活动，正式评论及附件目录、登记与字节接口。 | 已有 HTTP 接线。完整写入与读回依各入口验收，文件字节联调仍按现有安排后置。 [任务](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseTasks.tsx:28) · [活动](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseReadPanels.tsx:13) · [评论和附件](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseCommentsAttachments.tsx:24) |
| 案件管理、采用与助手 | 管理页走 E44–E47、E05 的对应读写。采用弹窗目前读取 E10/E14 并向 E21 提交旧字段。助手沿既有消息入口。 | 正式采用缺 E63 `adoption-preview` 及 `expected_review_token`，旧本地覆盖预览不能代表服务端可采用条件。按正式预览展示待确认项，失败留原状态并以 E03 及活动读回。助手、定向问答和新响应执行沿既有交付边界。 [管理](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseManagementDialog.tsx:58) · [旧采用提交](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/AdoptResultDialog.tsx:18) · [正式采用合同](/Users/lychee/Documents/project/socai2/docs/integration/result-adoption-http.md:8) |
| 通用调查目录与固定 Run | Q32 目录直接用服务端统计、游标和时间。Q09 定位主体后读指定 E12/E14、E24/E25、trace 与保存工件。五类视图保留发现、过程、查询、关系图和报告的真实读取入口。 | 目录停止原因目前固定显示未记录，导出该列留空。固定 Run 实际原件可读范围沿原回执，仍需校正下述目录状态及跳转。 [Q32 调用](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationListPage.tsx:42) · [固定 Run 入口](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationDetailPage.tsx:15) · [停止原因](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationListPage.tsx:143) |

### 状态和合同的最小修正

- 固定 Run 的 `RunWorkspace` 在已取得 Run 时继续渲染子视图。若 trace 尚在读取或失败，`RunQueries` 可先显示 0 项，`RunGraph` 与 `RunReport` 可显示没有已保存工件。告警的工件目录尚在分页时也会落入后两个提示。携带步骤、trace 和工件目录各自的读取状态，只有已成功读全且确认没有对应条目才显示无记录。部分目录可显示已载入范围，已有结果和已知原件可独立展示。 [Run 工作区](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunWorkspace.tsx:30) · [查询计数](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:121) · [图和报告](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:229) · [告警工件分页](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/AlertTriageRunPage.tsx:107)
- 固定告警分诊有真实单告警主体，但共享视图在有 Result 时把“结果范围”写死为 `1`，该值未从覆盖合同取得。可用明确的告警主体标签或正式范围字段表达。采用旧弹窗在候选详情无数据时用本地过滤得出 `0`，应等待正式预览再展示覆盖。对象证据使用 E03 的真实 `page_data` 作初值，E05 刷新失败时旧值和失败提示会并列，宜标明当前显示的是先前保存版本。 [结果范围](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:62) · [采用覆盖](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/AdoptResultDialog.tsx:22) · [证据初值与错误](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseEvidence.tsx:31)
- 平台路由和桥接当前均登记了 E57、Q30/Q31、Q32 与 Q33–Q36。公开平台 OpenAPI 缺 E57、Q30/Q31、Q32，前端调用 E57、Q31 和 Q32 时使用局部类型。合并时按登记和原生返回同步公开合同，更新 E01/E08 的正式分配响应，再生成 live 类型。E63 和 Case 异步受理 POST 需要正式中转与合同，随相关页面接线核对。 [平台登记](/Users/lychee/Projects/SpiritHub-web-8181/backend/src/spirithub/api/routes/socai2.py:70) · [平台 OpenAPI](/Users/lychee/Projects/SpiritHub-web-8181/schemas/platform-api.v1.json) · [Q32 局部类型](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/api.ts:8) · [Q31 局部类型](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-entry-api.ts:35)

### 测试替身与开发启动

- 17 个测试文件含浏览器组件、HTTP 和桥接替身。源码中现有 MSW 启动受开发模式和显式 API 模式控制。生产构建要求 `live`，开发默认 `hybrid` 的平台处理器列表为空，请求透传。启用 `mock` 时明确加载演示处理器。组件和桥接替身用于验证请求、条件和渲染，真实业务验收采用正式 HTTP 的保存和读回证据。 [API 模式](/Users/lychee/Projects/SpiritHub-web-8181/web/src/app/config/apiMode.ts:5) · [应用入口](/Users/lychee/Projects/SpiritHub-web-8181/web/src/main.tsx:10) · [开发处理器](/Users/lychee/Projects/SpiritHub-web-8181/web/src/mocks/handlers/index.ts:15) · [浏览器测试](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbench.test.tsx) · [桥接测试](/Users/lychee/Projects/SpiritHub-web-8181/backend/tests/soc/test_bridge.py)

### 告警与事件发起 Case 的分配回执接线

本步只处理 `SubjectCommands` 的 `CaseAssociation`。目标是用户从告警或事件新建、关联后，进入本次实际接收的案件，按保存回执查看各分配案及已有首轮任务。使用现有 Case 队列与案内选择器的 `caseEntryApi`、`caseAllocationTarget` 及案件页头状态。两处共享图增量仍在提交范围内。正式后轮受理、证据目录状态、采用预览和图样式各沿独立步骤。

| 环节 | 输入、处理和通过证据 |
| --- | --- |
| 创建 | E01 提交真实 `alert_ids/incident_ids`、用户填写的标题及描述、既有操作键。用 `allocations` 核对 `primary_case_id/receiving_case_id`，以实际接收案加入地址与导航状态。 |
| 关联 | E03 核对所选案件身份和现有 `scope_revision`，E08 提交该版本、成员和操作键。正式回执可返回另一接收案及多案分配，保留全部已返回的案件及各自的首轮任务身份。 |
| 读回 | 导航到已核对的接收案，适用时从本案 `initial_task` 传递任务参数，复用已有 E03/Q31 读取和首轮状态组件。用户原来可选的助手入口随同保留。 |
| 失败 | 请求失败或分配身份核对失败时保留表单和错误，沿现有操作键及非自动重投路径处理。仅以正式回执导航和关联任务。 |

实施前执行该 change 的严格校验。独立候选只改共享入口及其现有测试。复用 `SubjectCommands.test.tsx`，用正式形状覆盖告警创建、事件关联到实际接收案及失败后不导航、不自动重投。使用现有案件正常入口的 E03/Q31 用例核对导航状态确实能触发已保存任务的读取。通过标准是请求、回执身份、地址、分配状态和任务关联一致。类型检查及用例结果写在本小节，替身证据与既有真实读回按各自范围使用。组合候选由统筹独核后进入下一步。 [正式分配合同](/Users/lychee/Documents/project/socai2/docs/integration/case-allocation-http.md:33) · [共享分配校验](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-entry-api.ts:64) · [首轮查询](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkspaceFrame.tsx:147)

独立候选已完成。告警／事件入口通过 `caseEntryApi.detail` 校验所选案，通过同一分配解析确定导航、初始任务和多案列表。正式回执校验失败或请求失败时显示错误并保留表单，定向检查仅观察到原提交一次。OpenSpec 实施前严格校验通过，`npm run typecheck` 通过，`SubjectCommands.test.tsx` 9 项通过，既有 Case 队列 E03/Q31 的接收案任务读回 1 项通过。组件验证使用替身传输。精确补丁在初始两文件副本上回放，结果等同测试源码。 [两文件源码补丁](/Users/lychee/Documents/project/socai2/.local/validation/spirithub-case-association-20261128-01/frontend-case-association.patch) · [直接检查与指纹](/Users/lychee/Documents/project/socai2/.local/validation/spirithub-case-association-20261128-01/direct-checks.json)

统筹已独核两文件源码与复用条件。再次核对原文件和候选指纹后，两文件已精确挂载到 8181。实际 8181 源码含当前 `live.ts` 的一次组合类型检查通过，应用与 Node/Vite 两个项目均通过。两文件、三处复用依赖与生成类型在检查期间指纹一致，原组件证据按相同后像复用。 [统筹独核](/Users/lychee/Documents/project/socai2/.local/validation/model-exceptions-release-coordinator-20261128-01/ordinary-post-case-association-source-review.json) · [8181 挂载与类型检查指纹](/Users/lychee/Documents/project/socai2/.local/validation/spirithub-case-association-20261128-01/8181-mounted-typecheck.json)

## 可复用定向证据及源文件边界

匹配数仅统计该回执列出的文件指纹。浏览器验收仍按测试环境、请求入口和原受理范围使用。模拟用例、实际 8181 读回和 21 发布证据各自保留原口径。 [逐文件 SHA-256 与回执指纹](/Users/lychee/Documents/project/socai2/openspec/changes/complete-socai2-investigation-chain/spirithub-frontend-precommit-sources-20261128.json)

| 范围 | 已有定向证据与绑定 | 当前复用边界 |
| --- | --- | --- |
| 告警页面与固定分诊 | 将 21 Web 冻结补丁应用于内存中的共同基线，所得 37 个路径与 `8051df5` 相同，31 个仍与工作树快照相同。复用提交基线的类型、构建和定向告警入口证据。 [冻结构建回执](/Users/lychee/Documents/project/socai2/docs/operations/evidence/alert-git-21-release-20261125-01/frontend-build.json) | 构建回执记录组件测试未重跑。当前不同文件涉及 Run 壳、Case 引用、主体命令、主体字段、生成类型和筛选条。 |
| 告警相似历史 | 既有相似历史候选的独立定向测试通过，最终候选含定向测试和类型检查。候选绑定 4 个指纹，当前匹配 2 个。 [最终候选](/Users/lychee/Documents/project/socai2/docs/operations/evidence/integration-coordination-audit-20261124-01/alert-review-final-candidate-check.json) · [独立测试](/Users/lychee/Documents/project/socai2/docs/operations/evidence/integration-coordination-audit-20261124-01/alert-review-independent-tests.json) | 按完整文件匹配复用，受 main 改动影响的正常入口和共享依赖待集成确认。 |
| 事件 | 已发布诊断的 3 项定向测试及类型检查通过，当前源码匹配原候选 3/9。图选择定向通过，图组件匹配，测试文件后续有变，整体 1/2。成员活跃数与检测源有独立定向回执。 [诊断源码与测试](/Users/lychee/Documents/project/socai2/docs/operations/evidence/incident-saved-diagnosis-read-20261126-01/frontend-result.json) · [关系图测试](/Users/lychee/Documents/project/socai2/docs/operations/evidence/incident-graph-selection-clarity-20261126-01/frontend-result.json) · [成员聚合测试](/Users/lychee/Documents/project/socai2/docs/operations/evidence/incident-member-aggregates-20261125-01/frontend-result.json) | 事件链现有回执支持各自源码切片。页内诊断、列表和共享合同已变化，组合后的当前入口待定向复验。 |
| Case 队列和通用调查目录 | `CaseWorkbench.test.tsx` 和 `Investigations.test.tsx` 既有合计 10 项定向通过，类型检查通过，候选指纹当前匹配 11/14。通用调查目录四个已记录文件均匹配。 [队列与目录测试](/Users/lychee/Documents/project/socai2/docs/operations/evidence/case-list-migration-20261126-01/frontend-implementation.json) · [创建回读](/Users/lychee/Documents/project/socai2/docs/operations/evidence/case-create-readback-20261126-01/README.md) | Case 选择弹窗、详情壳和 Case 测试文件此后有变。创建按已保存 E01/Q31 读回证据复用，原运行结果按其回执保留。 |
| Case 故事 | 挂载候选的 15 项定向通过，当前匹配 5/7，含故事组件、样式、测试和接口帮助。 [挂载与测试](/Users/lychee/Documents/project/socai2/.local/validation/case-story-migration-20261126-01/frontend/story-mount-readback.json) · [已有独立验收](/Users/lychee/Documents/project/socai2/docs/operations/evidence/case-story-migration-20261126-01/README.md) | Case 详情壳及生成类型已变。历史与单条来源请求按各自已核路径判断。 |
| Case 历史和固定 Run | 四项历史路由测试、一项旧仅 Result 链路测试及类型检查通过。当前匹配 5/7，含历史入口、测试、接口和 Run 壳。 [源码与测试回执](/Users/lychee/Documents/project/socai2/docs/operations/evidence/case-history-migration-20261126-01/coordinator-frontend-source-review.json) · [恢复后读回](/Users/lychee/Documents/project/socai2/docs/operations/evidence/case-history-migration-20261126-01/coordinator-browser-acceptance-20261127.json) | 详情壳与生成类型后来变化。当前源树的中转登记与被验运行版本有差异。 |
| Case 关系图 G1 | 挂载候选的四项图入口及三项既有图问答与轮次链接测试通过。当前匹配 7/8。 [挂载回执](/Users/lychee/Documents/project/socai2/docs/operations/evidence/case-graph-migration-20261127-01/frontend-g1-mount.json) · [候选定向测试](/Users/lychee/Documents/project/socai2/docs/operations/evidence/case-graph-migration-20261127-01/frontend-g1-candidate.json) | 生成类型后续变化。覆盖 G1 只读底图与保存来源，候选探索、加入和保存的边界见原验收。 |
| Case 资料补齐 | 类型与复核候选的定向测试通过，挂载八个文件的当前指纹全部相同。 [独立源码及测试复核](/Users/lychee/Documents/project/socai2/docs/operations/evidence/case-info-migration-20261127-01/coordinator-reopen-candidate-review.json) · [挂载指纹](/Users/lychee/Documents/project/socai2/docs/operations/evidence/case-info-migration-20261127-01/frontend-case-info-reopen-mount.json) | 仍按回执范围复用已采用依据、原范围和工件引用。最终 Case 壳、平台合同和运行版本另核。 |

集成候选的最少直接核对按最终差异确定。先让平台路由登记、桥接合同、主 OpenAPI 与生成类型对应，运行现有类型检查。共享图归并后复用 `RelationGraph.test.tsx` 的现有默认模式用例。其他组合变化按入口选现有用例，事件用 `IncidentWorkbench.test.tsx`，队列或详情壳用 `CaseWorkbench.test.tsx`，固定轮衔接用 `CaseInvestigationHistory.test.tsx`。合并触及告警共享命令或固定轮读取时，分别选 `SubjectCommands.test.tsx` 或 `AlertTriageRunPage.test.tsx` 的相关用例。平台端由统筹按最终路由差异选择现有桥接用例。提交时点待当前核心 S1/S2/S3 真实测试与独验完成后由统筹确定。

## 逐文件范围

下表的已提交列指 `bb368df8` 到 `8051df5`，未提交列指当前工作树相对 HEAD，`—` 表示该层无变更。main 列对应上方的四类路径级比较。共享项按实际调用和需保留的既有行为判断。前端提交候选仅关联浏览器代码、指定共用支撑及对应合同，中转代码由统筹一起核对。

### 告警

| 文件 | 已提交 | 未提交 | main | 归属与接线 |
| --- | --- | --- | --- | --- |
| [AlertExplanation.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/AlertExplanation.tsx) | 新增 | — | 新增文件 | 分诊解释按固定结果呈现，沿来源引用定位。 |
| [AlertPageLayout.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/AlertPageLayout.tsx) | 新增 | — | 新增文件 | 告警页面导航和页壳，连接现有列表与详情入口。 |
| [AlertRecommendations.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/AlertRecommendations.tsx) | 新增 | — | 新增文件 | 展示同轮已保存的建议及引用。 |
| [AlertTriageRunPage.test.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/AlertTriageRunPage.test.tsx) | 新增 | — | 新增文件 | 固定告警 Run 的目录、原件引用和状态回归用例。 |
| [AlertTriageRunPage.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/AlertTriageRunPage.tsx) | 新增 | — | 新增文件 | 固定分诊 Run，读步骤目录、精确步骤、trace 和分页原件。 |
| [AlertWorkbenchDetail.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/AlertWorkbenchDetail.tsx) | 新增 | — | 新增文件 | 告警正常详情入口，联读 E28、分诊结果、当前材料、来源及回执。 |
| [AlertWorkbenchList.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/AlertWorkbenchList.tsx) | 新增 | — | 新增文件 | 告警正常列表入口，读正式筛选、列表字段和分页。 |
| [alert-page.css](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/alert-page.css) | 新增 | — | 新增文件 | 正常告警列表、详情及固定轮布局。 |
| [alertAttck.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/alertAttck.ts) | 新增 | — | 新增文件 | 归属和标记检测战术及同轮 AI 映射。 |
| [alertListApi.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/alertListApi.ts) | 新增 | — | 新增文件 | 告警查询和导出参数，复用正式 HTTP 客户端。 |
| [alertTriageApi.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/alertTriageApi.ts) | 新增 | — | 新增文件 | 固定分诊 GET 和主体、轮次、工件身份校验。 |

### 告警旧入口与相似历史

| 文件 | 已提交 | 未提交 | main | 归属与接线 |
| --- | --- | --- | --- | --- |
| [AlertPreview.css](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-alerts/AlertPreview.css) | 修改 | — | 候选独有改动 | 现有告警预览抽屉与新告警入口共用样式。 |
| [AlertResponse.test.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-alerts/AlertResponse.test.tsx) | 修改 | — | 同路径改动 | 告警响应回执及同轮建议定向覆盖。 |
| [AlertResponse.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-alerts/AlertResponse.tsx) | 修改 | — | 同路径改动 | 分诊建议、响应保存记录及直接关联轮次的读与定位。 |
| [AlertWorkbench.test.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-alerts/AlertWorkbench.test.tsx) | 修改 | — | 同路径改动 | 告警管理、列表预览和分诊相关正常入口用例。 |
| [AlertWorkbenchDetail.css](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-alerts/AlertWorkbenchDetail.css) | 修改 | — | 候选独有改动 | 正常告警概要、时间线、检测和分诊状态样式。 |
| `/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-alerts/AlertWorkbenchDetail.tsx` | 删除 | — | 同路径改动 | 基线旧详情组件删除。main 修改过此路径，按当前两类告警入口调用核对处置。 |
| [AlertWorkbenchList.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-alerts/AlertWorkbenchList.tsx) | 修改 | — | 同路径改动 | 旧告警列表及现用告警预览入口的桥接。 |
| [AlertWorkbenchRaw.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-alerts/AlertWorkbenchRaw.tsx) | 修改 | — | 同路径改动 | 按材料身份读取原始 OCSF、扩充和来源引用。 |
| [SimilarAlertReview.test.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-alerts/SimilarAlertReview.test.tsx) | — | 未跟踪 | 新增文件 | 正式相似历史查询、窗口与候选字段定向用例。 |
| [SimilarAlertReview.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-alerts/SimilarAlertReview.tsx) | — | 修改 | 同路径改动 | 相似历史筛选、真实候选与原来源材料入口。 |
| [alertReviewApi.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-alerts/alertReviewApi.ts) | — | 未跟踪 | 新增文件 | 封装正式 review-candidates 读取和时间窗字段。 |

### 事件

| 文件 | 已提交 | 未提交 | main | 归属与接线 |
| --- | --- | --- | --- | --- |
| [IncidentAssets.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentAssets.tsx) | — | 未跟踪 | 新增文件 | 读事件资产匹配，区分权限、部分加载、无匹配和失败。 |
| [IncidentDetail.css](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentDetail.css) | — | 修改 | 候选独有改动 | 事件概览、成员、涉及对象和活动布局。 |
| [IncidentDetailContext.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentDetailContext.tsx) | — | 未跟踪 | 新增文件 | 事件概览、共同线索、关联 Case 通路及发布诊断和最近尝试。 |
| [IncidentDetailRecords.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentDetailRecords.tsx) | — | 未跟踪 | 新增文件 | 成员、对象与资产及活动记录的筛选、分页和查看。 |
| [IncidentDetailSources.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentDetailSources.tsx) | — | 未跟踪 | 新增文件 | 材料、告警与对象来源定位，以及分页状态支撑。 |
| [IncidentPreview.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentPreview.tsx) | — | 未跟踪 | 新增文件 | 事件预览和列表共用的活跃数、检测源、资产及诊断呈现。 |
| [IncidentRelations.css](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentRelations.css) | — | 未跟踪 | 新增文件 | 已接线的事件关系图节点、画布、成员及来源面板样式。 |
| [IncidentRelations.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentRelations.tsx) | — | 未跟踪 | 新增文件 | 事件真实成员和对象关系，含筛选、选择、画布和来源检查。 |
| [IncidentWorkbench.test.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentWorkbench.test.tsx) | — | 修改 | 同路径改动 | 事件列表、预览、管理冲突、发布诊断及各详情子页定向用例。 |
| [IncidentWorkbenchDetail.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentWorkbenchDetail.tsx) | — | 修改 | 同路径改动 | 事件正式详情壳和当前事件范围内的分区查询依赖。 |
| [IncidentWorkbenchList.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/IncidentWorkbenchList.tsx) | — | 修改 | 同路径改动 | 事件正式目录、聚合卡、筛选、行内摘要及预览入口。 |
| [incident-workbench.css](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/incident-workbench.css) | — | 修改 | 候选独有改动 | 事件队列及预览等当前工作台样式。 |
| [incidentListApi.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/security-events/incidentListApi.ts) | — | 未跟踪 | 新增文件 | 事件队列、聚合摘要和导出合同，显式保留可空服务字段。 |

### Case

| 文件 | 已提交 | 未提交 | main | 归属与接线 |
| --- | --- | --- | --- | --- |
| [CaseGraph.css](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseGraph.css) | — | 未跟踪 | 新增文件 | 案件关系图 G1 布局、画布与来源检查。 |
| [CaseGraph.test.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseGraph.test.tsx) | — | 未跟踪 | 新增文件 | 默认及指定轮底图、已保存快照和失败边界的定向用例。 |
| [CaseGraph.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseGraph.tsx) | — | 修改 | 同路径改动 | G1 保存快照、默认底图、固定轮 Q35 定位和来源导航。 |
| [CaseGraphQuestioning.test.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseGraphQuestioning.test.tsx) | — | 修改 | 同路径改动 | 保留图和原轮入口的定向检查，覆盖当前探索控件边界。 |
| [CaseGraphView.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseGraphView.tsx) | — | 未跟踪 | 新增文件 | 现用 Case 图的节点、关系、图层、布局和原件链接。 |
| [CaseInfo.css](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInfo.css) | — | 未跟踪 | 新增文件 | 案件资料、来源详情和评级等当前页面样式。 |
| [CaseInfo.test.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInfo.test.tsx) | — | 未跟踪 | 新增文件 | 资料汇总、固定来源、截断、失败和保存判断的正常入口定向用例。 |
| [CaseInfo.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInfo.tsx) | — | 未跟踪 | 新增文件 | E03/Q36 汇总读取、范围版本校验、成员和对象预览。 |
| [CaseInfoAssessment.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInfoAssessment.tsx) | — | 未跟踪 | 新增文件 | 已采用判断、原适用范围和当前范围差异。 |
| [CaseInfoAssessmentSource.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInfoAssessmentSource.tsx) | — | 未跟踪 | 新增文件 | 按确切 Result、任务修订和工件身份读保存依据。 |
| [CaseInfoRating.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInfoRating.tsx) | — | 未跟踪 | 新增文件 | 现行等级、初始等级、已生效和最新意见的原来源呈现。 |
| [CaseInfoSavedDetails.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInfoSavedDetails.tsx) | — | 未跟踪 | 新增文件 | 原范围、发现、待核事项及类型化保存引用。 |
| [CaseInvestigationHistory.css](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigationHistory.css) | — | 未跟踪 | 新增文件 | 案内历史目录及固定 Run 布局。 |
| [CaseInvestigationHistory.test.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigationHistory.test.tsx) | — | 未跟踪 | 新增文件 | Q34/Q35、精确轮次和旧仅 Result 链接定向用例。 |
| [CaseInvestigationHistory.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigationHistory.tsx) | — | 未跟踪 | 新增文件 | 案内历史、精确轮次选择和同轮结果入口。 |
| [CaseManagementDialog.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseManagementDialog.tsx) | — | 修改 | 同路径改动 | Case 资料壳与案件管理弹窗联动，保存字段依现有合同。 |
| [CasePreview.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CasePreview.tsx) | — | 未跟踪 | 新增文件 | 案件队列的精确条目预览及详情连接。 |
| [CaseQueueControls.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseQueueControls.tsx) | — | 未跟踪 | 新增文件 | Case 队列日期、时间字段及已保存筛选控件。 |
| [CaseReadPanels.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseReadPanels.tsx) | — | 修改 | 同路径改动 | 保留现有 Case 活动读取，故事迁至独立 CaseStory 入口。 |
| [CaseReferences.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseReferences.tsx) | 修改 | 修改 | 同路径改动 | 已提交版引入引用读取共用逻辑，当前版限定 Case 原件路径和父身份。 |
| [CaseSelectionDialog.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseSelectionDialog.tsx) | — | 修改 | 同路径改动 | 创建、关联和移动的现有弹窗，校验分配回执及实际接收案。 |
| [CaseStory.css](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseStory.css) | — | 未跟踪 | 新增文件 | 案件故事时间线与焦点关系布局。 |
| [CaseStory.test.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseStory.test.tsx) | — | 未跟踪 | 同路径改动 | 故事翻页、焦点成员和同轮已保存结果读取定向用例。 |
| [CaseStory.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseStory.tsx) | — | 未跟踪 | 新增文件 | 相关故事 Q13、焦点 Q33、告警材料和固定阶段摘要入口。 |
| [CaseWorkbench.test.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbench.test.tsx) | — | 修改 | 同路径改动 | Case 列表、预览、新建首轮、成员和详情入口的定向用例。 |
| [CaseWorkbenchDetail.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchDetail.tsx) | — | 修改 | 同路径改动 | 案内路由壳，挂载资料、故事、历史、关系图及证据。 |
| [CaseWorkbenchList.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchList.tsx) | — | 修改 | 同路径改动 | Case 正式列表、筛选、导出、预览、创建和同案导航。 |
| [CaseWorkspaceFrame.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkspaceFrame.tsx) | — | 未跟踪 | 新增文件 | 案件头部、子页、Case 切换、Q31 首轮任务及固定轮进度入口。 |
| [case-entry-api.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-entry-api.ts) | — | 未跟踪 | 新增文件 | E01/E08 分配返回、E03 详情与 Q31 初始任务身份校验。 |
| [case-graph-api.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-graph-api.ts) | — | 未跟踪 | 新增文件 | E67/E69 GET 类型与案、轮、来源校验。 |
| [case-graph-model.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-graph-model.ts) | — | 未跟踪 | 新增文件 | 区分成员或调查底图，保留图状态、展开和精确来源。 |
| [case-history-api.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-history-api.ts) | — | 未跟踪 | 新增文件 | Q34/Q35 正式历史目录、游标与固定轮读取。 |
| [case-info-api.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-info-api.ts) | — | 未跟踪 | 新增文件 | Q36 同案范围摘要及所需字段校验。 |
| [case-queue.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-queue.tsx) | — | 未跟踪 | 新增文件 | Case 列表筛选、列与统计口径、回到列表的导航状态。 |
| [case-workbench.css](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-workbench.css) | — | 修改 | 同路径改动 | Case 队列、壳、预览和管理控件样式。 |
| [workbench-api.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/workbench-api.ts) | — | 修改 | 同路径改动 | Case 故事及成员焦点关系读取，复用既有工作台查询前缀。 |

### 调查执行

| 文件 | 已提交 | 未提交 | main | 归属与接线 |
| --- | --- | --- | --- | --- |
| [AlertRunRecords.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/AlertRunRecords.ts) | 新增 | — | 新增文件 | 已提交告警固定轮的分页目录和定位上下文。 |
| [InvestigationListPage.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationListPage.tsx) | — | 修改 | 同路径改动 | 正式通用 Run 目录、筛选、统计、时间线和选择入口。 |
| [Investigations.test.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/Investigations.test.tsx) | — | 修改 | 同路径改动 | 通用目录筛选、状态与固定轮链接回归。 |
| [RunReading.test.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunReading.test.tsx) | 修改 | — | 同路径改动 | 已提交固定轮、工件可用性及原来源读取回归。 |
| [RunViews.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx) | 修改 | — | 同路径改动 | 已提交固定 Run 发现、过程、查询、图、报告和告警工件渲染。 |
| [RunWorkspace.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunWorkspace.tsx) | 修改 | 修改 | 同路径改动 | 已提交告警目录共用壳，当前增加 Case 历史内嵌及同 Run/Result 校验。 |
| [api.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/api.ts) | — | 修改 | 同路径改动 | 在现有 Run 读取旁接正式 analysis-runs 目录及筛选类型。 |
| [runPresentation.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/runPresentation.ts) | — | 修改 | 同路径改动 | 统一目录状态、来源主体链接及按保存时间计算用时。 |

### 共享路由与工作台

| 文件 | 已提交 | 未提交 | main | 归属与接线 |
| --- | --- | --- | --- | --- |
| [router.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/app/router.tsx) | 修改 | — | 同路径改动 | 接线正常告警和固定分诊公开浏览器入口，整合时保留 main 的其他路由。 |
| [ActivityChanges.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/ActivityChanges.tsx) | 修改 | — | 同路径改动 | 固定告警活动归属和字段展示，与既有 Case/事件活动调用共用。 |
| [AlertObjectGraph.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/AlertObjectGraph.tsx) | — | 修改 | 候选独有改动 | 纳入成员工作区和原材料链接增量。8181 可选模式无页面挂载，main 既有默认调用需复核。 |
| [AnalysisContent.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/AnalysisContent.tsx) | 修改 | — | 候选独有改动 | 固定分诊解释复用保存分析、建议与限制呈现。 |
| [AttackStages.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/AttackStages.tsx) | — | 修改 | 候选独有改动 | 现用事件概览启用 exactLabels，保留其他入口的既有方式。 |
| [PeoplePicker.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/PeoplePicker.tsx) | 修改 | — | 同路径改动 | 告警管理负责人选择所需标签、显示名和小范围筛选。 |
| [RecordTable.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/RecordTable.tsx) | — | 修改 | 候选独有改动 | 事件成员和活动传入已筛选行、表头及空态，分页仍对服务已载入行。 |
| [RelationGraph.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/RelationGraph.tsx) | — | 修改 | 同路径改动 | 纳入可选 workspace 增量，按 main 和 8181 的现有调用复核默认行为。 |
| [SubjectCommands.test.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/SubjectCommands.test.tsx) | 修改 | — | 同路径改动 | 已提交告警管理和冲突后的提交保护回归。 |
| [SubjectCommands.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/SubjectCommands.tsx) | 修改 | 修改 | 同路径改动 | 告警原管理与事件列表共用，现有增量涉及最小主体类型、刷新和提交状态。 |
| [SubjectFields.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/SubjectFields.tsx) | 修改 | 修改 | 同路径改动 | 告警关联分区及现用事件严重度投影所需的最小参数声明。 |
| [SubjectPreview.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/SubjectPreview.tsx) | 修改 | — | 候选独有改动 | 告警预览标题、元数据和详情链接的共用能力。 |
| [api.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/api.ts) | — | 修改 | 同路径改动 | 事件详情返回类型、主体命令形状与正式记录 GET 共同入口。 |
| [presentation.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/presentation.ts) | 修改 | — | 同路径改动 | 按已保存来源读取告警判定，保留未提供与未分类等状态。 |
| [queries.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/queries.ts) | 修改 | — | 同路径改动 | 提交键和结果回调供告警管理及现有工作台共同使用。 |
| [referenceContent.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/referenceContent.ts) | 新增 | — | 新增文件 | 共享来源内容的准确路径和字段定位。 |
| [live.ts](/Users/lychee/Projects/SpiritHub-web-8181/web/src/shared/api/generated/live.ts) | 修改 | 修改 | 同路径改动 | 由合并后的平台 OpenAPI 生成，所需 SOC 投影与 main 的其他类型一并保留。 |
| [ColumnChooser.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/shared/ui/ColumnChooser.tsx) | — | 修改 | 候选独有改动 | 事件和 Case 列选择器使用视口锚点定位，其他列表保留默认入口。 |
| [ListFilterBar.tsx](/Users/lychee/Projects/SpiritHub-web-8181/web/src/shared/ui/ListFilterBar.tsx) | 修改 | 修改 | 同路径改动 | 告警复用 onClear，当前事件和 Case 使用 clearLabel，扫描 hideAdd 为既有属性。 |

### 平台中转与合同

| 文件 | 已提交 | 未提交 | main | 归属与接线 |
| --- | --- | --- | --- | --- |
| [.env.example](/Users/lychee/Projects/SpiritHub-web-8181/.env.example) | 修改 | — | 同路径改动 | 已提交 SOC 受信读取及源地址配置示例，属于平台配套。 |
| [socai2.py](/Users/lychee/Projects/SpiritHub-web-8181/backend/src/spirithub/api/routes/socai2.py) | 修改 | 修改 | 同路径改动 | 显式中转路由、固定 Run 和事件投影衔接，快照中 Q34/Q35 缺登记，定向修正另记。 |
| [config.py](/Users/lychee/Projects/SpiritHub-web-8181/backend/src/spirithub/config.py) | 修改 | — | 同路径改动 | 已提交 SOC 受信读取相关配置声明。 |
| [bridge.py](/Users/lychee/Projects/SpiritHub-web-8181/backend/src/spirithub/soc/bridge.py) | 修改 | — | 同路径改动 | 已提交的 SOC 读取、中转策略和响应约束配套。 |
| [bridge_contract.json](/Users/lychee/Projects/SpiritHub-web-8181/backend/src/spirithub/soc/bridge_contract.json) | 修改 | 修改 | 同路径改动 | SOC 专用内转合同，逐方法核对原生结构和平台路由。 |
| [test_alert_run_records.py](/Users/lychee/Projects/SpiritHub-web-8181/backend/tests/soc/test_alert_run_records.py) | 新增 | — | 新增文件 | 已提交固定告警步骤和工件目录的桥接定向测试。 |
| [test_bridge.py](/Users/lychee/Projects/SpiritHub-web-8181/backend/tests/soc/test_bridge.py) | 修改 | 修改 | 同路径改动 | 告警、事件、Case 正式中转、请求和响应的回归验证。 |
| [test_incident_run_context.py](/Users/lychee/Projects/SpiritHub-web-8181/backend/tests/soc/test_incident_run_context.py) | — | 未跟踪 | 新增文件 | 事件固定诊断 Run 的主体定位与错误状态测试。 |
| [platform-api.v1.json](/Users/lychee/Projects/SpiritHub-web-8181/schemas/platform-api.v1.json) | 修改 | 修改 | 同路径改动 | 平台公开 OpenAPI，按 SOC 方法和组件与 main 整合，覆盖前端生成类型输入。 |
