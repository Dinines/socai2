# 21 调查服务部署

当前主发布为 `v1.2-20261112-r3`，C2 三目的适用条件筛选、模型知识去重／任务选择及历史当前版本资格配置已实际加载；处理镜像 `processing-20261112-r2`，4177 源码随统一发布。API 与工作台各切换一次，其余四项容器身份保持；自动消费者暂停。实际来源见 [PROGRESS](../../PROGRESS.md)及[交付回执](../../docs/operations/evidence/knowledge-selection-20261112-01/delivery-summary.json)。首次 r2 冻结在 preflight 因旧基线失败、未执行 rollout；核实基线后重新冻结 r3，保留原失败和冻结目录。

## 发布来源与步骤

[统一清单](release-v1.2.json)给源码、固定镜像、Compose 来源和变化服务；[传输配置](current-rollout.json)给目标、独立目录和证据位置；[生产 profile](production-v1.2.toml)选择模型、库和[调查策略](../local-investigation/investigation-policy-case-v1.toml)。凭据只从已有 private 文件生成。

1. 处理组件有实际变化时使用 `prepare_processing_release.py --profile <构建配置>` 冻结，再执行 `rollout_transport.py --config <传输配置> processing upload/build`；把镜像和 manifest 回执填入清单。知识 change 的处理代码有变化，按 processing-build-case-v1.toml 构建并核验固定镜像。
2. `release_12.py freeze --config <发布清单> --directory <独立目录>`；通过传输入口执行 `unified upload`、`build`、`preflight`、`prepare`。
3. 知识 change 一次发布内依次执行 `unified rollout --project main --service api` 和 `unified rollout --project workbench --service workbench`；其他四项服务沿用已有容器，自动消费者保持暂停。
4. 执行 `unified activate`，其已包含源码／配置及服务核验；仅在有新的核验需要时另行 `verify`，不重复全量检查。再完成本次功能的生产写读回执。每个 change 收口后只统一发布一次。

构建使用已缓存固定基础镜像，不拉取外网依赖。`prepare` 保存有效 Compose 和处理配置到受控 private 目录；不输出其内容。回退执行该冻结目录的 `release_12.py rollback --directory <目录>`，保留所有业务数据、原答和验收任务。发布不执行 DDL、清库或重派历史 Run。

## Case/H 功能配置

正式库为 `aisoc.socai2`，29 表、462 列。新装沿[建表及安装入口](../database/install_aisoc21_v1.py)完成既有库和处理 profile 后，升级沿既有 profile 复用连接；本 change 无额外迁移、角色或 GRANT。

统一清单明确启用 `SOCAI2_CASE_API_ENABLED=true`，把处理 runtime.env 的 `DATABASE_URL` 映射为 API 的 `SOCAI2_CASE_DATABASE_URL`。同时传入该 profile 的四项可选来源开关及 SOCAI2_LAKE_DATABASE；只复制已列出的键，通用 API DATABASE_URL 和已有湖连接保持；原 TLS 证书挂载直接复用。运行值存入 21 private 的 api-model.env 和有效 Compose，仓库仅保留映射。[配置示例](case-http.env.example)也适用于本地显式配置。

Case/H 非 GET 使用现有处理连接，GET 保持原读取连接；缺写入配置返回明确 503，不猜另一数据库。API 的 `AISOC_STARTUP_SCHEMA_MIGRATIONS=false`。权限专项不是功能前置，现有读写接线随功能处理。

后续操作使用原接口：[Case/H 交接](../../openspec/changes/archive/2026-11-11-enable-case-human-http-flow/handoff.md)。建案→start→人工完成/修订→prepare/start 后轮，人工保存本身不触发模型。生产验收入口 [production.py](../../tools/testdata/case_human_http/production.py)只在新建的明确验收 Case 保存和修订一项任务，再读取比对；正常登录使用既有账号，初始 Run 保持 pending_update，无生产模型调用。

## C2 知识与工作台

知识功能已接通技术解释、取证指导与历史案例参考。生产配置在 API 与处理入口挂载相同的 [knowledge-profile.json](../local-investigation/knowledge-profile.json)，使用已有 Ollama 本地 qwen3-embedding:0.6b/1024 和独立 Qdrant 集合，原情报/组织记忆集合保留。受控 key 来自既有 vector-1d 私密配置，只通过 knowledge 配置指定的文件挂载，不进镜像/Git。新装/升级步骤与字段见[知识交接](../../docs/investigation/case-knowledge-handoff.md)及[历史卡片交接](../../docs/investigation/historical-alert-knowledge-handoff.md)。原 Case/H 写连接保持，告警合同与 V1 表结构不变。历史卡片只由显式入口入库和索引，未启用自动沉淀。

4177 沿 [Mac SSH 接入](../../docs/operations/mac-ssh-relay-20261107.md)访问。知识 change 的工作台源码随统一 API/处理发布切换，根源码挂载与两个既有单文件挂载同步指向同一 release。通过[静态配置](workbench-current.json)追加已保存案例并读回；不额外调用独立 runtime 发布入口或再次重启。`workbench-runtime-current.json` 是前次独立发布回执的配置，当前统一发布以 release-v1.2.json 为入口。

前批技术解释/取证指导的本地实际 6 条知识查询/8 条命中、5 次模型请求及保存读回；C6 duplicate_source 仍失败。20 项直接检查与一次浏览器功能查看通过，质量 NOT_PASSED，未做复杂测试或新生产调查。生产验收工具 [production.py](../../tools/testdata/case_knowledge/production.py)以该批临时 scope key 导入/索引两份有来源资料，读回块元数据，再使用已保存查询文本做只读 C2 adapter 检索；不建 Case、不写 Run、不调用分析模型。与本地完整链路证据合并说明接线边界，不把探针当成生产完整调查。[前批验收](../../openspec/changes/archive/2026-11-11-enable-purpose-aware-case-knowledge/validation.md)

前批两目的知识与历史卡片的生产回执保留在各自归档中。本轮历史已有卡 3 次业务 HTTP、方法资料 4 次业务 HTTP，通过显式入库／索引／GET；3 个只读目的查询返回 5 行（历史 1 卡、两个目的各 2 个方法块）。验收入口 [production.py](../../tools/testdata/knowledge_selection/production.py)及[配置](../../tools/testdata/knowledge_selection/production.json)复用既有路径；没有生产 Case／Run／分析模型，临时 key 撤销并核 401。4177 从实际 38→39 份，79 文件／80 静态 HTTP 读回，静态发布不重启服务。浏览器查看候选筛除及合并出处通过；原答及模型质量 NOT_PASSED 保留。
