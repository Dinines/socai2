# 本机调查验证环境

当前数据、功能和字段合同见[交接指南](../../FRONTEND_BACKEND_HANDOFF.md)。Mac 读取 21 正式数据使用显式只读 profile；网络走[SSH 转发](../../docs/operations/mac-ssh-relay-20261107.md)。本机隔离验证与正式库分别配置，数据均保留。

## 21 正式数据只读 profile

本次已准备 `.local/remote-21/profile.toml`，所有运行地址、端口、库名、角色、租户、TLS、超时和开关均来自该文件。模板为 [remote-profile.example.toml](remote-profile.example.toml)，凭据另存 `.local/remote-21/private/secrets.json`（目录 0700、文件 0600，Git 忽略）。不要将该文件内容复制进日志或提交。

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

新机器准备步骤：先安装 API 依赖和 [requirements-remote.txt](requirements-remote.txt)，复制示例为自己的 profile 并核对参数，再运行 `bootstrap_remote_profile.py <profile>`。该工具仅经已验证 SSH 复制 profile 指定的现有只读账号密码及公开 CA，并生成本机访问凭据；不会修改远端密码、用户或授权，不覆盖已有私密文件。当前这台 Mac 已完成，不必重做。

TLS 使用 psycopg 的 `hostaddr` 连接本机隧道，使用 `host` 和 CA 验证 21 的证书，强制 `verify-full`。启动核对实际数据库/角色、TLS、只读事务、强制 RLS、无调查表写权限及 V1 字段。此前 asyncpg 的连接行为保持兼容。依据：[SQLAlchemy 异步 psycopg](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg)、[PostgreSQL host/hostaddr](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS)。

## 读取权限与安装

正式 `socai2` schema 共 29 表、462 列；读取角色具有这些表的 SELECT、两项新鲜度函数的 EXECUTE，以及 `public.assets/public.users` 的必要 SELECT，关联始终限定认证租户。当前生产两案 299 次 GET 与 13,098 项数据／字段核对通过，无结构或业务数据变化。[本批证据](../../docs/operations/evidence/current-release-20261110-01/readback-03/summary.json)

[reader-install.example.toml](../database/reader-install.example.toml)显式设置目标、管理员、schema owner 和 reader，凭据通过私密 PGPASSFILE 提供。新建空库和已有库使用不同入口；日常核验只执行 `verify`：

```sh
python deploy/database/install_reader.py verify --profile '<读取安装配置>'
```

空库的 `initialize` 使用冻结建表原件及共用读取授权；已有库的 `upgrade` 仅应用获准的读取授权，不重置 schema。两者共用 [upgrade_socai2_v1_2_reader.sql](../database/upgrade_socai2_v1_2_reader.sql)。新增表设计或权限范围仍遵守项目规则，不能由日常验证自行扩大。

## 当前模型处理策略

**当前处理策略：** 显式选择 [investigation-policy-case-v1.toml](investigation-policy-case-v1.toml)，其中 `[case_io] profile = "case-input-v1.json"` 启用 C1 冻结、C3/Deep/C6 结构文本和输出恢复。C1 保存 profile 与字段映射指纹，同一冻结 Run 不静默换规则。Deep 由程序恢复问题号；C6 恢复身份、生成建议编号和首次固定比较。未配置 `case_io` 的 Run 按其冻结 JSON 合同执行；可选 C3.reanalysis 使用独立装配。构建文件 [processing-build-case-v1.toml](../aisoc21/processing-build-case-v1.toml)对应 `processing-20261112-r3`，已随 `v1.2-20261112-r5` 部署 21。当前知识选择按阶段目的／范围／字符预算提供可选内容，并优先恢复前序引用依赖；前序模型质量 NOT_PASSED 保留；本轮新分诊提交后同步仅一次本地模板判断流程，生产核加载与处理连接，无新模型或 Run。[同步验收](../../openspec/changes/archive/2026-11-12-sync-saved-alert-knowledge/validation.md)。[本轮核验](../../openspec/changes/archive/2026-11-12-refine-purpose-aware-knowledge-use/validation.md)。

执行隔离调查时使用明确策略：

```sh
.local/conda-envs/socai2/bin/python deploy/local-investigation/run.py api --investigation-policy deploy/local-investigation/investigation-policy-case-v1.toml
```

应用进程的 `SOCAI2_INVESTIGATION_POLICY` 由所选文件设置。当前 Case 预算为 6 次模型、4 次工具、131072 累计 tokens、1500 秒，最终阶段预留 300 秒；模型单次 300 秒。容量需计量完整消息、Schema／协议包络、安全余量和输出；工件保留上限 1 MiB 是字节值，与 token 预算分开。

当前计量器支持已核实的 `chat_completions` 后端；不匹配的协议应明确拒绝。模型路由、认证和协议保存在本机私密配置中，切换前核无活跃或未知执行，再正常停止并重启对应应用；不重派已结束批次。新批次固定配置和实际材料，不以读取、测试替身或生成工件认定质量通过。

21 按需处理使用[生产 profile](../aisoc21/production-v1.2.toml)与相同策略，通过[统一发布入口](../aisoc21/README.md#发布来源与步骤)冻结源码、镜像及策略 hash；本机修改文件不会自动改变 21。

## 隔离数据与原件

本机已保存的调查数据库和 Docker volumes 继续保留。创建新的专用环境时使用[冻结建表 SQL](../database/init_socai2_v1.sql)和明确的本机运行配置；现有 `prepare.py` 生成材料不能代替已确认的完整 123–126 结构。`initialize.py` 会校验 462 列，结构不符应停止并查明原因，不能清库绕过。

运行 API/Fusion 的来源与参数取当前 checkout 和私密配置；不带 `--profile` 的启动器仍指向本机隔离环境。只做无连接导入检查：

```sh
.local/conda-envs/socai2/bin/python deploy/local-investigation/run.py api --check-import
.local/conda-envs/socai2/bin/python deploy/local-investigation/run.py fusion --check-import
```

模型、工具替身与真实数据库的证据分别登记。导出后用[运行记录页说明](../../deliverables/investigation-validation-20261106/README.md#调查运行记录页)更新本机静态资料；已有批次、失败、unknown 和原答保持。停止前台进程使用 SIGTERM／Ctrl-C；基础服务使用原 compose 的 `stop`，保留数据卷。
