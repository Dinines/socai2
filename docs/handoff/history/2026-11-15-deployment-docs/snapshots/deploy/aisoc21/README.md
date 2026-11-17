# 21 调查服务部署

第6步本地候选的[Case首轮发布片段](../local-investigation/analysis-case-release-fragment.json)继承129分配和A/I调度片段，新增A/I/Case联合工厂及冻结查询配置，并退役候选CLI case-prepare/case-start。只准备统一交付清单，不改变21运行profile/服务；与HTTP E11/E13退役一起发布，Case周期和check/rerun留第7步。详见[运行说明](../../docs/operations/analysis-case-initial.md)。第11步结合测试对话方案最终验证，按当时授权发布。

当前主发布为`v1.2-20261113-r1`，处理镜像`processing-20261113-r1`。固定A/I、C3/Deep/C6输入筛选和程序装配已发布，只切换核心API一次，显式处理入口已激活。生产健康、源码/策略及既有Case/Result/当前判断只读核对通过；7个指定保留服务身份不变，消费者继续关闭。[交付回执](../../docs/operations/evidence/fixed-investigation-release-20261113-01/README.md)。无新模型、业务写入或迁移；质量NOT_PASSED后置。

独立18024/E71、Swagger docs18和工作台没有随本次切换，由接口侧依据[核心接续说明](../../docs/operations/evidence/fixed-investigation-release-20261113-01/handoff.md)后续同步。历史知识同步保持开启/120秒，旧r5回执保留在原证据目录。
## 发布来源与步骤

[统一清单](release-v1.2.json)给源码、固定镜像、Compose 来源和变化服务；[传输配置](current-rollout.json)给目标、独立目录和证据位置；[生产 profile](production-v1.2.toml)选择模型、库和[调查策略](../local-investigation/investigation-policy-case-v1.toml)。凭据只从已有 private 文件生成。

当前核心构建已包含`additional_packages.investigation_http`，两包均已冻结和核验。处理组件直接调用调查核心，不加载对外HTTP运行入口。独立18024版本以[专用部署说明](../http-service/README.md)为准，不因核心发布视为已同步。

本地待发布的[阶段一步骤3](../../docs/operations/evidence/stage1-c3-contract-20261114-01/README.md)已在同一Case策略入口将C3输出额度改为8192，配套`case-input-v1.json`的版本化最多5发现和一次七部分合同；其他阶段、Case总预算及C6预留保持。现有清单/构建入口已包含这些源码和策略路径，新装或升级应随整个change统一冻结发布。此次只完成本地隔离PG保存读取，未更新21镜像、冻结profile或发布清单；步骤3当轮未实施补答。

Case策略的A/I最多两次模型调用（首答及一次引用纠正），各24000tokens/300秒；Case6次/131072tokens/1500秒。实际生产profile取统一清单的`processing.profile`，本轮为冻结证据目录下的`production-profile.toml`；仓库根profile是同值的操作入口副本。已完成目录不可复用或覆盖，新发布使用新目录。
1. 处理组件有实际变化时使用 `prepare_processing_release.py --profile <构建配置>` 冻结，再执行 `rollout_transport.py --config <传输配置> processing upload/build`；把镜像和 manifest 回执填入清单。本次按 processing-build-case-v1.toml 构建并核验固定镜像。
2. `release_12.py freeze --config <发布清单> --directory <独立目录>`；通过传输入口执行 `unified upload`、`build`、`preflight`、`prepare`。
3. 本次只执行 `unified rollout --project main --service api`。外部18024、Swagger、工作台及其他服务保持，自动消费者继续关闭；不沿用旧知识发布的工作台切换步骤。
4. 执行 `unified activate`，其已包含源码／配置及服务核验；仅在有新的核验需要时另行 `verify`，不重复全量检查。再完成本次功能的直接生产读回；本次复用已验保存链路，仅只读比较既有数据。每个 change 收口后只统一发布一次。

构建使用已缓存固定基础镜像，不拉取外网依赖。`prepare` 保存有效 Compose 和处理配置到受控 private 目录；不输出其内容。回退执行该冻结目录的 `release_12.py rollback --directory <目录>`，保留所有业务数据、原答和验收任务。发布不执行 DDL、清库或重派历史 Run。

## Case/H 功能配置

阶段一步骤6本地原件存取变更见[回执](../../docs/operations/evidence/stage1-original-retention-20261114-01/README.md)。新装及升级共用的`prepare_processing_release.py`、HTTP构建和统一发布入口会冻结socai2源码与所选策略；下次整change发布须一起带入新loader及`views.max_graph_bytes`配置，移除旧`model.max_artifact_bytes`。原件PG存取不设应用级裁剪，模型额度/准备上限和C6预留保持；无新增迁移、角色或服务。当前镜像、运行配置和发布清单未更新，不能把本地验证视为已上线。

正式库为 `aisoc.socai2`，迁移 127 后 28 表、450 列；当前安装/增量/核验见[数据库入口](../database/CURRENT.md)。新装沿[建表及安装入口](../database/install_aisoc21_v1.py)完成既有库和处理 profile 后，升级沿既有 profile 复用连接；知识同步批次没有额外迁移或角色；知识维护仅对既有处理身份增加 KB INSERT，见下节。

统一清单明确启用 `SOCAI2_CASE_API_ENABLED=true`，把处理 runtime.env 的 `DATABASE_URL` 映射为 API 的 `SOCAI2_CASE_DATABASE_URL`。同时传入该 profile 的四项可选来源开关及 SOCAI2_LAKE_DATABASE；只复制已列出的键，通用 API DATABASE_URL 和已有湖连接保持；原 TLS 证书挂载直接复用。运行值存入 21 private 的 api-model.env 和有效 Compose，仓库仅保留映射。[配置示例](case-http.env.example)也适用于本地显式配置。

Case/H 非 GET 使用现有处理连接，GET 保持原读取连接；缺写入配置返回明确 503，不猜另一数据库。API 的 `AISOC_STARTUP_SCHEMA_MIGRATIONS=false`。权限专项不是功能前置，现有读写接线随功能处理。

后续操作使用原接口：[Case/H 交接](../../openspec/changes/archive/2026-11-11-enable-case-human-http-flow/handoff.md)。建案→start→人工完成/修订→prepare/start 后轮，人工保存本身不触发模型。生产验收入口 [production.py](../../tools/testdata/case_human_http/production.py)只在新建的明确验收 Case 保存和修订一项任务，再读取比对；正常登录使用既有账号，初始 Run 保持 pending_update，无生产模型调用。

## C2 知识与工作台

知识功能已接通技术解释、取证指导与历史案例参考。生产配置在 API 与处理入口挂载相同的 [knowledge-profile.json](../local-investigation/knowledge-profile.json)，使用已有 Ollama 本地 qwen3-embedding:0.6b/1024 和独立 Qdrant 集合，原情报/组织记忆集合保留。受控 key 来自既有 vector-1d 私密配置，只通过 knowledge 配置指定的文件挂载，不进镜像/Git。新装/升级步骤与字段见[知识交接](../../docs/investigation/case-knowledge-handoff.md)及[历史卡片交接](../../docs/investigation/historical-alert-knowledge-handoff.md)。原 Case/H 写连接及告警合同保持；后续迁移 127 仅清理未用探索表。分诊保存后同步已完成本地验收、独审及实际加载读回；开启 profile 后仅新提交且采用的 A 结果触发，原显式维护仍可用。新装知识表 INSERT 已并入既有脚本，现有安装执行 `knowledge_history_write_access.sql`，参数由生产 profile 提供；保持消费者关闭。

4177 沿 [Mac SSH 接入](../../docs/operations/mac-ssh-relay-20261107.md)访问。2026-11-14按负责人要求，工作台已切换为既有无DSN静态查看模式，关闭生产库实时列表及自动导入，当前只显示本轮三案；本机4177转发同一服务。[当前展示配置](workbench-display-current.json)与[回执](../../docs/operations/evidence/workbench-display-fix-20261114-01/README.md)记录新Compose/容器身份；后续发布不得直接重放旧固定容器/Compose条件。源码和镜像不变，数据库及其他服务保持。知识 change 的工作台源码随统一 API/处理发布切换，根源码挂载与两个既有单文件挂载同步指向同一 release。通过[静态配置](workbench-current.json)追加已保存案例并读回；该知识批次未额外重启工作台。后续空表清理已通过[当前 runtime 配置](workbench-runtime-current.json)仅发布一次工作台 `workbench-20261112-graph-cleanup-r1`，5 个查询/导入文件适配当前 28 表并保留旧快照兼容；空表清理当时API/处理服务仍为r5，现已由上述固定功能版核心r1更新。涉及工作台的下一次发布须从该实际工作台 Compose/挂载核基线，不重放 r5 的旧工作台配置。

前批技术解释/取证指导的本地实际 6 条知识查询/8 条命中、5 次模型请求及保存读回；C6 duplicate_source 仍失败。20 项直接检查与一次浏览器功能查看通过，质量 NOT_PASSED，未做复杂测试或新生产调查。生产验收工具 [production.py](../../tools/testdata/case_knowledge/production.py)以该批临时 scope key 导入/索引两份有来源资料，读回块元数据，再使用已保存查询文本做只读 C2 adapter 检索；不建 Case、不写 Run、不调用分析模型。与本地完整链路证据合并说明接线边界，不把探针当成生产完整调查。[前批验收](../../openspec/changes/archive/2026-11-11-enable-purpose-aware-case-knowledge/validation.md)

前批两目的知识与历史卡片的生产回执保留在各自归档中。前序用途筛选批次的历史已有卡 3 次业务 HTTP、方法资料 4 次业务 HTTP，通过显式入库／索引／GET；3 个只读目的查询返回 5 行（历史 1 卡、两个目的各 2 个方法块）。验收入口 [production.py](../../tools/testdata/knowledge_selection/production.py)及[配置](../../tools/testdata/knowledge_selection/production.json)复用既有路径；没有生产 Case／Run／分析模型，临时 key 撤销并核 401。4177 从实际 38→39 份，79 文件／80 静态 HTTP 读回，静态发布不重启服务。浏览器查看候选筛除及合并出处通过；原答及模型质量 NOT_PASSED 保留。

2026-11-14阶段一步骤4本地待发布：`case-input-v1.json`增加版本化`c3_completion`（最多1次、补答指令及字段依赖），新C3冻结相同业务材料和短号，按既有ModelSteps预算门执行缺字段补答。Run/C3额度与C6预留均未修改；配置校验兼容现有发布器的独立加载，构建入口自动收集新增三个C3补答模块及profile。真实模型补答与隔离PG保存读取见[步骤4回执](../../docs/operations/evidence/stage1-c3-completion-20261114-01/README.md)。21镜像、冻结profile及发布清单未切换，当前服务仍以原发布回执为准。

2026-11-14阶段一步骤5本地待发布：profile新增`followup_routing`并冻结到C3/Deep提示；C4/Deep额外保留`socai2.followup-activity.v1`实际查询记录，新增`followup_activity.py`随既有打包目录收集。预算、C3输出/补答及C6预留保持。用户明确授权的6条合成演练湖记录已写入21，新增上下文通过真实查询进入本机隔离C6；47次GET通过，首轮unknown及33次读取保留。镜像/profile/服务配置未切换，详见[步骤5回执](../../docs/operations/evidence/stage1-followup-routing-20261114-01/README.md)。


阶段一步骤7同Run结论及原件查阅已[本地验收](../../docs/operations/evidence/stage1-viewer-20261114-01/README.md)，未发布。下一次统一工作台发布须将[展示配置](../../docs/operations/processing_audit_view.json)与渲染源码一并带入release，预览长度为独立配置，不限制原件存取或模型输入；renderer_revision已包含该配置。待同步源码清单及hash见[runtime-files.json](../../docs/operations/evidence/stage1-viewer-20261114-01/runtime-files.json)。发布器仅新增允许这一个展示JSON文件并校验JSON，不扩大其他路径；本轮只做语法检查，未执行远程发布。不要重放旧workbench-runtime-current.json；正式Compose及挂载仍按实际当前基线核对，本机4178仅为本轮静态预览。

新告警自动分诊的本地目标版本、入站授权、A工厂及投影配置见[运行说明](../../docs/operations/analysis-alert-ingress.md)和[统一发布片段](../local-investigation/analysis-alert-release-fragment.json)。本地验收不激活生产；镜像、源代码和profile随整个流式change统一发布。

流式第4步当前已本地接入事件自动诊断；统一发布应选[联合A/I运行配置](../../docs/operations/analysis-incident-diagnosis.md)和[事件发布片段](../local-investigation/analysis-incident-release-fragment.json)。旧直接`incident`处理命令已移除，事件通过E37异步受理并由唯一dispatcher执行；Case命令保持当前阶段。此项没有部署或启用21服务。
