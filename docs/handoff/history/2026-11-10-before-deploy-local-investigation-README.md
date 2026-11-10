> 此文件保存 2026-11-10 整理前的过程快照，仅供追溯。当前说明见仓库入口。

# 本机调查验证环境

**这台 Mac 读取 21 正式数据时：** 使用下方显式远端只读 profile，目标为 `aisoc.socai2`，不选历史或合成测试库。网络说明见[本机 SSH 转发与项目配置说明](../../operations/mac-ssh-relay-20261107.md)。原本机服务已停止、数据保留；不带 `--profile` 的旧启动模式仍固定本机数据库与端口，修改旧 `runtime.env` 或父 shell 的 `DATABASE_URL` 不会自动切到 21。

**V1 接手先读[根目录交接指南](../../../FRONTEND_BACKEND_HANDOFF.md)。** 下文 `prepare.py` 的历史建库流程只准备 123–125（459 列），当前 `initialize.py` 已按 126 校验 462 列；不能按这组旧命令从空库得到完整 V1。本机既有验证库已另行应用 126，继续保留。新环境使用[独立 V1 建表脚本](../../../deploy/database/init_socai2_v1.sql)，再由部署方配置运行身份、授权和基础服务。本文其余连接、运行及模型切换说明仍按对应本机环境使用。

## 21 正式数据只读 profile

本次已准备 `.local/remote-21/profile.toml`，所有运行地址、端口、库名、角色、租户、TLS、超时和开关均来自该文件。模板为 [remote-profile.example.toml](../../../deploy/local-investigation/remote-profile.example.toml)，凭据另存 `.local/remote-21/private/secrets.json`（目录 0700、文件 0600，Git 忽略）。不要将该文件内容复制进日志或提交。

当前目标：数据库 `aisoc`、schema `socai2`、已有只读角色 `socai2_prod_reader`、业务租户 `00000000-0000-0000-0000-000000000001`。这是正式调查数据，不是 `socai2_next_20261104` 或 `socai2_processing_handoff`。它不自动返回 `public.alerts` 的全部旧告警，也不启动接入或调查。

在仓库根目录启动：

```sh
.local/conda-envs/socai2/bin/python -B deploy/local-investigation/run.py api \
  --profile .local/remote-21/profile.toml
```

该命令管理自己的 `25432` SSH 转发及 `127.0.0.1:18022` API；端口已占用会报错，不接管其他隧道。Ctrl-C 同时关闭这两个进程，不影响常驻 4177 工作台。运行时只使用所选文件生成的应用环境，不继承 shell 的数据库或模型配置；`--profile` 不允许配合 Fusion 或模型预检入口。

另一个终端执行只读验证，输出文件须为未存在的新路径：

```sh
.local/conda-envs/socai2/bin/python -B deploy/local-investigation/verify_remote_readonly.py \
  .local/remote-21/profile.toml --output .local/remote-21/verification-new.json
```

客户端访问 `/api/v1/socai2/alerts`、`/incidents`、`/cases` 等 GET 时，使用本机私密配置中的 `access_token` 作为 Bearer token。它代表固定租户的本机读取服务，只有 `alerts:read/cases:read`，不是生产用户会话或生产 API key。该模式不开放登录、写入、调查或模型接口；所有非 GET/HEAD 方法先返回 405，认证缺失/错误返回 401，查询参数和 Header 不能更换租户。原 `app.socai2_main` 禁止连接 `aisoc` 的保护仍保留。

新机器准备步骤：先安装 API 依赖和 [requirements-remote.txt](../../../deploy/local-investigation/requirements-remote.txt)，复制示例为自己的 profile 并核对参数，再运行 `bootstrap_remote_profile.py <profile>`。该工具仅经已验证 SSH 复制 profile 指定的现有只读账号密码及公开 CA，并生成本机访问凭据；不会修改远端密码、用户或授权，不覆盖已有私密文件。当前这台 Mac 已完成，不必重做。

TLS 使用 psycopg 的 `hostaddr` 连接本机隧道，使用 `host` 和 CA 验证 21 的证书，强制 `verify-full`。启动核对实际数据库/角色、TLS、只读事务、强制 RLS、无调查表写权限及 V1 字段。此前 asyncpg 的连接行为保持兼容。依据：[SQLAlchemy 异步 psycopg](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg)、[PostgreSQL host/hostaddr](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS)。

2026-11-07 首次只读实测（历史时点）：TLSv1.3，29 表/462 列；上述租户 1 告警、1 事件、0 Case、2 Run，SQL 与 HTTP 数量一致；错误证书身份拒绝、13 项 HTTP 检查通过。当时 Case 列表为空，未用非空 Case 验证详情，也未补造测试数据；首次验证后关闭了临时 API/数据库隧道。[原只读回执](../../operations/evidence/remote-readonly-20261107/verification.json)

随后按用户授权执行了一批多告警流程，并保留本机只读 API 供查询。非空 Case 详情暴露出两项函数 EXECUTE 缺失，已另经明确授权以[增量 SQL](../../../deploy/database/reader_freshness_access_20261107.sql)补齐并恢复 200；其他权限未变。新核对 135 GET 中 127 正常成功、4 错父子 ID 正确 404、4 资产读取因 `public.assets` SELECT 不足返回 500。首次连通性验证不代表所有有值分支均已验证；复验已存数据请按[交接指南第 8.1 节](../../../FRONTEND_BACKEND_HANDOFF.md#81-2026-11-07-正式库数据库与-get-核对)运行配置化只读核对程序。不要为了消除资产错误给只读角色授予全库权限。

## 1.2 开发读取与部署入口（2026-11-07）

按用户“给足开发所需权限、优先完成开发”的追加授权，现有 reader 已增加 `public.assets/public.users` SELECT。当前实现直接读取两表，查询仍使用认证租户和必要字段；未安装之前讨论的专门读取函数。已修两项新鲜度函数授权一并保留。新增脚本不会写业务数据或修改 V1 表结构。

部署方复制 [reader-install.example.toml](../../../deploy/database/reader-install.example.toml) 为自己的配置，填写实际连接目标、管理员、schema 所有者和已创建的 reader。密码通过私密 PGPASSFILE 等部署文件提供。空库先准备 reader LOGIN 及 schema 所有者账号；调查处理/Fusion 角色仍由原业务部署管理，本入口只负责 V1 数据结构和读取能力。

```bash
# 新的独立空库：冻结 V1 原件 → reader 基础读取 → 同一 1.2 增量
python deploy/database/install_reader.py initialize --profile /path/to/reader-install.toml
# 已有 V1 库（包括既有 public 业务表环境）：只应用读取增量
python deploy/database/install_reader.py upgrade --profile /path/to/reader-install.toml
python deploy/database/install_reader.py verify --profile /path/to/reader-install.toml
```

新建和升级共用 [upgrade_socai2_v1_2_reader.sql](../../../deploy/database/upgrade_socai2_v1_2_reader.sql)，包含两份授权 SQL；`--print-sql` 可查看完整展开结果。升级授权可重复执行；新建入口遇到已有 schema 会明确失败，不能用于重置现有库。V1 原件不改。配置缺目标时安装器拒绝；SQL 拒绝返回非零退出码，不能把错误提示当成功。

先完成授权和 `verify`，再启动新读取 API。新代码会检查资产/负责人及 Case 函数依赖；旧 profile 需显式增加示例中的 `[read_sources]`。本轮初始化/升级 7 项、本机读取/profile 20 项通过；正式库的实际复验见[实施证据](../../operations/evidence/v1.2-implementation-20261107)，不等于调查模型整链验收。

## 原本机隔离环境

**2026-11-10 Case 本地候选：** 显式选择 [investigation-policy-case-v1.toml](../../../deploy/local-investigation/investigation-policy-case-v1.toml)，其中 `[case_io] profile = "case-input-v1.json"` 启用 C1 冻结、C3/Deep/C6 结构文本和输出恢复。新 C1 保存 profile 与业务字段映射指纹；同一冻结 Run 不静默换规则。Deep 四项输出由程序恢复问题号；C6 由程序恢复成员/对象、生成建议编号，首次调查的固定 comparison 不再要求模型输出。未配置 `case_io` 的 Run 继续旧 JSON/输出合同；可选 C3.reanalysis 保持旧实现。候选构建文件为 [processing-build-case-v1.toml](../../../deploy/aisoc21/processing-build-case-v1.toml)，标签 `processing-case-20261110-c2`，逐字收录规则 JSON、业务模块和策略；不是仅在线改文件。本地验证包含真实隔离 PG、模型/工具替身及同材料离线比较，**未部署或新增真实模型调用**，21 最近仍为 A/I r5。[Deep/C6 接入报告](../../../openspec/changes/complete-socai2-investigation-chain/case-followup-integration-20261110.md)。

执行调查的 API 须显式选取 `--investigation-policy deploy/local-investigation/investigation-policy.toml`；部署进程设置同文件绝对路径为 `SOCAI2_INVESTIGATION_POLICY`。它提供已确认的 300/1500/300 秒时限、模型容量与输入输出额度；更换文件后重启进程，不能运行途中更改预算。当前容量分配仍为本地验证候选。只读 `--profile` 通过 `investigation_policy_file` 选同一文件供工件读取大小限制使用，无须重复传 CLI 参数，不因此启用调查。

事件输入输出适配候选使用 [investigation-policy-incident-v1.toml](../../../deploy/local-investigation/investigation-policy-incident-v1.toml)。其`[incident_io] profile = "incident-input-v1.json"`选择随服务源码打包的结构映射和任务指令，未配置该节继续旧模式；不要仅在服务器手改提示词。构建时在既有build profile的`policy_file`选择此文件，生产profile也须选择同一策略并核包内SHA后再切换，不能沿用旧策略指纹。新Run冻结同A实际查询回执，模型短号在保存前还原原ID/字段；旧快照保持原新鲜度规则。当前仅本机隔离存取验证通过，尚未在21启用，未包含A五字段切换、I交付状态修复或Case改造。见[本轮验证摘要](../../operations/evidence/incident-boundary-integration-20261108-01/summary.json)。

1.2 候选把准备上限设为 256KiB、工件保留上限设为 1MiB；这些是字节边界。是否能发给模型由真实 `/tokenize` 计量完整消息、模板、Schema/协议包络、安全余量和输出后决定，当前目标窗口 65536 tokens。Case 候选为 6 次模型/4 次工具/131072 累计 tokens，A/I 各 1 次/24000 tokens；C3 输出 4096、C6 输出 8192，默认保留两次 C6 额度与 300 秒。空引用反馈纠正计入该额度，不在 unknown 后重发。

目前该计量器只支持所核实的 `chat_completions` 后端；DeepSeek 计量适配尚未完成，配置会明确拒绝。旧三告警材料在加入程序事实/时间后重建，C3/C6 含输出及安全预留分别为 16146/22403 tokens，29 个必需值未遗漏；原26项/12688/18945回执属于前候选。这不是生成质量验收。

21 按需处理启动器已改为强制加载 [production profile](../../../deploy/aisoc21/production-profile.example.toml)，安装前核完整 policy，挂载文件并验证 profile/policy SHA；发布包和调用端一起改动。[候选构建入口](../../../deploy/aisoc21/README.md#12-按需处理候选与配置文件)冻结完整 API/Fusion 源码并核实际镜像文件。当前只构建候选、未切换正式处理服务；新批须选定候选、只读检查实际加载版本，再固定材料与额度。

以下流程使用当前 checkout 的 API/Fusion 源码和本机 Python 3.12。基础服务复用已安装镜像，数据写入本轮专属 Docker volumes；不复制旧环境的数据。应用只监听 loopback，启动或初始化不会调用模型。

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
