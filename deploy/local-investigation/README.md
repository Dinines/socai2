# 本机调查验证环境

本目录使用当前 checkout 的 API/Fusion 源码和本机 Python 3.12。基础服务复用已安装镜像，数据写入本轮专属 Docker volumes；不复制旧环境的数据。应用只监听 loopback，启动或初始化不会调用模型。

| 服务 | 本机地址 | 数据空间 |
| --- | --- | --- |
| PostgreSQL | `127.0.0.1:15432` | `socai2_local_20261105` |
| ClickHouse native / HTTP | `127.0.0.1:19000` / `18123` | `socai2_local_validation.raw_events` |
| Kafka | `127.0.0.1:19092` | `socai2.local.20261105.*` |
| Redis | `127.0.0.1:16379` | 独立容器的 DB 0 |
| API / Fusion | `127.0.0.1:18020` / `18021` | 本机源码进程 |

在仓库根目录执行：

```sh
.local/conda-envs/socai2/bin/python deploy/local-investigation/prepare.py
docker --context orbstack compose --env-file .local/local-investigation/private/runtime.env -f deploy/local-investigation/compose.yml up -d --pull never
.local/conda-envs/socai2/bin/python deploy/local-investigation/initialize.py
.local/conda-envs/socai2/bin/python deploy/local-investigation/run.py api
```

另一个终端运行：

```sh
.local/conda-envs/socai2/bin/python deploy/local-investigation/run.py fusion
```

`prepare.py` 只运行一次：生成 `.local/local-investigation/private/runtime.env`（0600，目录 0700）、六份 SQL 及 schema 哈希清单。已有私有文件时拒绝重建，不覆盖凭据。应用启动器从私有文件读取各自最小环境，工作目录切到私有目录，避免加载仓库的旧 `.env`；PG/CH 管理密码不传给应用。

`initialize.py` 只能连接上述固定 loopback 端口和数据库。首次创建数据库并标记归属，后续要求归属标记相同；不会删除数据库或表。按顺序执行 support schema、123/124/125、授权、固定本地租户/用户/API keys，再建立湖表和三个 Kafka topic。已应用迁移通过账本跳过。它校验 29 表/459 列、29 表强 RLS、7 张背景表强 RLS、非管理运行角色和实际跨租户拒读（探针回滚）、47 个湖写入列及精确读写权限。回执存于 `.local/local-investigation/evidence/`，失败保留阶段和脱敏原因。可用 `--phase postgres|clickhouse|kafka` 定向重跑；修改已准备 SQL 必须明确重建对应哈希，不能静默绕过校验。

API 使用 `app.socai2_main` 的现有正式路由和 `local_socai2_api` 受限角色。认证只验收普通 `aisoc_` API key，key 绑定实际本地用户；写 key 仅有 `alerts:read/write,cases:read/write`，读 key 仅有 `alerts:read,cases:read`。认证先于租户 session，故 `users/api_keys/RBAC` 保持原认证读取设计；调查和背景数据使用租户 RLS。密码/MFA、workload 登录和通用管理页面不属于此最小环境，未补其依赖表。私有文件不能提交、复制到页面或放进日志。

Fusion 由 `fusion_app.py` 装配现有 `FusionWorker`、去重/归并、`Socai2AlertSink`、`LakeWriter`，真实消费两个 Kafka 输入 topic，再发布 fused topic。只有消费者取得两个分区且 PG/CH 连接完成后 `/readyz` 才成功。它使用 `local_socai2_fusion`，仅可向 7 张 socai2 表读/新增，并更新 alerts/incidents 的指定列；不能创建 Case 或 Run。CH reader 只有本表 SELECT，writer 只有本表 INSERT。未装配外围检测、事件自动提升、session、AI 资产、UEBA 消费和外部 enrichment；本轮输入是明确的合成 raw alert 与 OCSF 日志。无持久 DLQ 时坏消息停止消费且不越过失败 offset；湖写失败仍沿现有 fail-soft 行为，验收必须核 `/metrics` 的 `lake.rows_written/rows_dropped/flush_failures` 和真实数据库行，不能只看健康状态。

背景源支持 `assets`、内部 `threat_intel_iocs`、`user_risk_profiles` 和 `aisoc_kb_documents`，初始化不填合成背景，也不假称已同步真实来源。知识库沿原 C2：冻结告警标题形成检索词，在 PG `to_tsvector/plainto_tsquery` 检索文档内容。C2 仍按原优先级和预算选源，不保证每次查询知识库。没有向量链、Embedding、Qdrant、Neo4j 或 OpenSearch 前置依赖；身份图与产品实时查询关闭。

模型只通过私有环境的五项切换：`OPENAI_BASE_URL`、`OPENAI_MODEL`、`OPENAI_API_KEY`、`SOCAI2_MODEL_PROTOCOL`、`SOCAI2_MODEL_SCHEMA_PROFILE`。默认是 DeepSeek 官方地址、`deepseek-flash`、`deepseek_responses`、`standard`；`prepare` 留空模型 key，由本机操作者安全写入。验证远端已部署模型时将地址/认证/模型改为该后端，协议用 `chat_completions`，所需 grammar profile 用 `vllm_grammar_v1`；有限值会校验。停止当前 API（确认无运行中的 Run）、修改私有配置、重启 API 即切换；PG/CH/Kafka/Redis 路由和已存 Run/工件不变。已启动 Run 不应中途切后端或重派。此次切换不自动执行 A/I/C，也不扩大每个 Run 的预算。

切换时确认没有 active Run，在 API 终端按 Ctrl-C，然后用本机编辑器打开 `.local/local-investigation/private/runtime.env` 修改这五项（不要复制文件内容进聊天或日志），保持 0600。只重新执行下列 API 命令，Fusion 和数据服务继续运行；单轮验证固定同一个 backend，无需迁移数据：

```sh
.local/conda-envs/socai2/bin/python deploy/local-investigation/run.py api
```

应用配置和验证批次是两个独立步骤。验证驱动默认只准备 DeepSeek；切为已有部署模型后，须给新批次显式指定 `--backend deployed`，不能把旧 a/b/c 计划切后端重派：

```sh
.local/conda-envs/socai2/bin/python deploy/local-investigation/validate_flow.py prepare --batch local-new-model-check --window-start 2026-11-05T12:00:00+00:00 --backend deployed
```

将示例批次名和窗口改为新的固定值。准备过程只读本机私有配置，不连接模型；计划冻结 `backend/model/protocol/schema_profile/base_url_sha256`，不导出地址明文、API key 或 key 指纹。DeepSeek 必须是官方完整 base URL、`deepseek-flash/deepseek_responses/standard`；`deployed` 使用显式配置的 Chat 服务和 `standard` 或 `vllm_grammar_v1`，不预设远端地址。后续阶段按计划核对私有配置，任一冻结项变化会在服务读取之前拒绝，须另建批次。旧的无 profile 计划仅兼容原 DeepSeek 配置，原源码/唯一 intent 的关闭保护仍然有效。该核对证明本机配置与计划一致，不是对运行中 API 进程或远端模型身份的证明；修改配置后须按上文重启 API，再准备和执行新批。

可选的合成背景导入沿已有 KB 函数和真实本机表进行，先固定验证批次 `plan.json`，再执行：

```sh
.local/conda-envs/socai2/bin/python deploy/local-investigation/seed_context.py --plan .local/local-investigation/validation/<batch>/plan.json --prepare-only
.local/conda-envs/socai2/bin/python deploy/local-investigation/seed_context.py --plan .local/local-investigation/validation/<batch>/plan.json --execute
```

前一步生成可审核的 `context-input.json`：仅有该批主机的 inventory 和一般调查 SOP/标题检索词，不读 oracle，不包含 H 结果或该案授权结论。后一步调用真实 `knowledge_base.ingest(IngestRequest, AsyncSession, CurrentUser)` 进行分块/写入，再用受限 API 数据库角色执行正式 C2 标题 FTS SQL 和资产匹配 SQL，保存全部原文块 ID 与匹配行；0 模型。这里是操作者执行的直接函数导入，未验证 HTTP 权限依赖链，也不等于每次 C2 自动选中知识源。一次写入 intent 已存在便拒绝重派，可加 `--verify-only --execute` 单独只读复核。

只做无连接导入检查：

```sh
.local/conda-envs/socai2/bin/python deploy/local-investigation/run.py api --check-import
.local/conda-envs/socai2/bin/python deploy/local-investigation/run.py fusion --check-import
```

停止 API/Fusion 时给对应前台进程正常发送 SIGTERM/Ctrl-C。停止基础服务用同一 compose 的 `stop`；保留 volumes 即保留历史数据，不使用 `down -v`。
