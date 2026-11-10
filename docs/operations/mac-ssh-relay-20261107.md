# 本机 Mac 经 Windows 57 访问 21 的使用说明

适用时间：2026-11-07。适用机器：用户 `lychee` 的这台 Mac，项目目录 `/Users/lychee/Documents/project/socai2`。这是本机开发与测试的连接说明，其他机器需要自己的 SSH 配置和身份。

**现在可以直接使用 `ssh sting-infra21` 登录 21，或打开 <http://127.0.0.1:4177/> 查看远端调查工作台。** Mac 不需要拨业务 VPN；Windows `192.168.3.57` 需要保持开机、网络可达并连接该 VPN。当前常驻隧道只开放工作台；数据库、湖、模型网关等本地端口按本文命令临时开启。

项目使用 21 的数据库分为两种情况：已有 SSH 读回工具继续使用 `sting-infra21`；Mac 当前源码的只读 API 现已支持显式远端 profile 和严格 TLS，读取正式 `aisoc.socai2`。用户随后明确要正式数据，历史/合成测试库不作为默认目标。已完成一次本机 API 只读验证，随后关闭临时进程；无数据库迁移、生产数据/权限修改、模型或 Fusion 启动。配置和命令见[只读 profile 用法](../../deploy/local-investigation/README.md#21-正式数据只读-profile)。

## 一 当前连接关系

```text
Mac → 192.168.3.57:2221 → Windows 经 VPN → 192.168.1.21:22
    → 在这个 SSH 连接中，将所需服务端口转发到 Mac 的 127.0.0.1
```

Windows 的 `2221` 是到 21 SSH 的入口，不是 PostgreSQL 或 HTTP 端口。Windows 自己的 SSH 在 `22`。连接 21 使用 Mac 上原有的 21 密钥，Windows 不保存该私钥。

| 已配置名称 | 用途 | 实际目标 |
| --- | --- | --- |
| `sting-infra21` | 日常登录、已有项目脚本、临时增加服务转发 | Windows `192.168.3.57:2221`，最终登录 21 的 `root` |
| `sting-infra21-tunnel` | 后台工作台隧道，由 LaunchAgent 管理 | 同一条到 21 的连接，转发本机 `127.0.0.1:4177` |
| `sting-infra21-direct` | 本机以后能够直接访问 21 时使用 | `192.168.1.21:22`，不经过 Windows |
| `sting-win57` | 维护 Windows 中转机 | `lychee@192.168.3.57:22` |

Mac 配置时的局域网地址为 `192.168.3.70`。Windows 相关入口的来源范围为 `192.168.3.0/24`，Mac 在该网段内更换地址不需要重新配置来源规则。Windows 地址 `192.168.3.57` 若变化，需要同步核对 Mac 的 SSH 目标和 Windows 转发监听地址；建议在路由器保留该地址。

SSH 别名只影响使用该别名的命令。写死 `192.168.1.21` 的数据库 URL、HTTP URL 或 `ssh root@192.168.1.21` 不会自动改道。

## 二 日常使用工作台和 SSH

```sh
# 登录 21，或执行一次远端命令
ssh sting-infra21
ssh sting-infra21 hostname

# 登录 Windows
ssh sting-win57

# 查看后台工作台隧道
ssh -O check sting-infra21-tunnel

# 只读检查页面是否可用
curl --noproxy '*' --fail --silent --show-error \
  -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:4177/
```

工作台入口为 <http://127.0.0.1:4177/>。这里是 SSH 把 **21 上的工作台**送到本机，并没有重新启动原来的 Mac 工作台服务。工作台校验 `Host` 和 `Origin` 中的端口，故本机也使用 `4177`；换成先前讨论的 `24177` 会返回 403。

后台任务在当前 Mac 用户登录后启动，SSH 检测断线后由 LaunchAgent 重新拉起。Windows 断网、VPN 断开或 Mac 睡眠期间无法访问；网络恢复后会重试，恢复不是即时的。

```sh
# 查看任务状态
launchctl print "gui/$(id -u)/com.lychee.socai2-ssh-tunnel"

# 重启已加载的任务
launchctl kickstart -k "gui/$(id -u)/com.lychee.socai2-ssh-tunnel"

# 查看连接错误
tail -n 60 /Users/lychee/Library/Logs/socai2-ssh-tunnel.log

# 本次登录期间停止；配置文件保留，下次登录仍会自启
launchctl bootout "gui/$(id -u)/com.lychee.socai2-ssh-tunnel"

# 停止后重新加载；已经加载时不要重复执行
launchctl bootstrap "gui/$(id -u)" \
  /Users/lychee/Library/LaunchAgents/com.lychee.socai2-ssh-tunnel.plist
```

需要跨登录停用时，先执行 `launchctl disable "gui/$(id -u)/com.lychee.socai2-ssh-tunnel"`，再对已加载任务执行 `bootout`。恢复时先将 `disable` 换成 `enable`，再执行 `bootstrap`。不要用 `ssh -O exit` 作为长期停止方式，任务仍启用时会自动重连。

## 三 按测试需要开启其他服务端口

下面的本地端口是本机使用约定，**没有加入常驻工作台隧道**。右侧地址由 21 发起连接：数据库和湖绑定在 `192.168.1.21`，工作台/API/网关绑定在 21 的 `127.0.0.1`，不能全部改成同一个目标地址。

| 服务 | Mac 本地 TCP 入口 | SSH 转发目标 | 用途 |
| --- | --- | --- | --- |
| PostgreSQL | `127.0.0.1:25432` | `192.168.1.21:5432` | 按数据库名、账号区分环境；TLS 用法见第四节 |
| ClickHouse native | `127.0.0.1:29000` | `192.168.1.21:9000` | 本项目 `CLICKHOUSE_PORT` 使用的原生协议 |
| ClickHouse HTTP | `127.0.0.1:28123` | `192.168.1.21:8123` | 使用 HTTP 协议的客户端 |
| 模型网关 | `127.0.0.1:24000` | `127.0.0.1:14000` | 本机 Base URL 为 `http://127.0.0.1:24000/v1` |
| 原业务 API | `127.0.0.1:28000` | `127.0.0.1:18000` | 使用已有远端 HTTP 接口，无需本机后端直连数据库 |
| 历史独立验证 API | `127.0.0.1:28020` | `127.0.0.1:18020` | 对应历史独立配置，不是所有测试库的统一 API |
| Redis | `127.0.0.1:26379` | `192.168.1.21:6379` | 保留远端 ACL 账号和逻辑 DB；需要时再核对连通性 |

只需要数据库时，在一个终端运行：

```sh
ssh -N -T -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:25432:192.168.1.21:5432 \
  sting-infra21
```

命令保持前台运行、没有输出是正常现象。在另一个终端运行数据库客户端；测试完成后对这个 SSH 进程按 `Ctrl-C` 即关闭临时隧道，不影响后台工作台。

需要湖和网关时，可以另外运行以下组合，并删除本次不需要的 `-L` 行：

```sh
ssh -N -T -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:29000:192.168.1.21:9000 \
  -L 127.0.0.1:28123:192.168.1.21:8123 \
  -L 127.0.0.1:24000:127.0.0.1:14000 \
  -L 127.0.0.1:28000:127.0.0.1:18000 \
  -L 127.0.0.1:28020:127.0.0.1:18020 \
  -L 127.0.0.1:26379:192.168.1.21:6379 \
  sting-infra21
```

`ExitOnForwardFailure` 可以发现本机端口占用等启动失败，不能证明远端每个服务已就绪；使用具体服务时再检查其响应。开启转发本身不会执行模型请求或数据库测试。

Kafka 另行处理：21 的入口是 `19093`，客户端还会连接 broker 在元数据中返回的广告地址，并校验证书。仅把 bootstrap 改成 `127.0.0.1:某端口` 不足以接通整条消费链。需要 Kafka/Fusion 整链测试时，应先解决所有广告地址的可达性和 TLS，或让相应测试进程在 21 执行；不要直接复用生产 consumer group。

## 四 数据库连接和只读查询

### 选择数据库和身份

所有 21 PostgreSQL 数据库共用 `5432`，开启临时隧道后也共用本机 `25432`。端口变化不改变数据库名、schema、租户或权限。

| 数据环境 | PostgreSQL 数据库 | 对应说明 |
| --- | --- | --- |
| 生产告警与调查 | `aisoc`，调查表在 `socai2` schema | 只读工作台角色为 `socai2_prod_reader`；处理角色为 `socai2_prod_processor`，两者用途不同 |
| 21 的 M01/S02/U03 合成交接样例 | `socai2_processing_handoff`，schema `socai2` | 既有作业角色 `socai2_processing_job`；该库保存既有样例，新写测试需另定范围 |
| 历史独立验证环境 | `socai2_next_20261104` | 21 的 `18020` API 对应这个历史环境，不等于上面的交接样例库 |
| 已停止的 Mac 本机环境 | `socai2_local_20261105`，原端口 `15432` | 本机 Docker 数据保留；不会因 SSH 配置自动迁移到 21 |

生产调查的常用业务租户为 `00000000-0000-0000-0000-000000000001`。交接样例固定租户为 `6aff0ef7-c670-5a84-a2ee-83d73e25b964`。实际查询应使用所选环境和授权范围对应的租户，不能拿本机旧租户、旧 API key 或旧数据库密码套用。环境合同见[根目录交接指南](../../FRONTEND_BACKEND_HANDOFF.md)。

### 现在即可使用的 SSH 数据库读回

这台 Mac 当前没有可用的 `psql` 命令。可以使用 21 容器内的客户端，不需要开启 `25432` 或把数据库密码取到本机：

```sh
ssh sting-infra21 \
  'docker exec -i spirithub-postgres-1 psql -wXAtq -v ON_ERROR_STOP=1 -U socai2_prod_reader -d aisoc' <<'SQL'
BEGIN READ ONLY;
SELECT current_database(), current_user;
ROLLBACK;
SQL
```

该身份查询已实际返回 `aisoc|socai2_prod_reader`。需要读取某个已获准租户的调查表时，在同一个事务内设置租户，例如：

```sql
BEGIN READ ONLY;
SET LOCAL app.current_tenant_id = '00000000-0000-0000-0000-000000000001';
-- 在这里执行本次所需的只读 SELECT，使用 socai2.cases 等完整表名。
ROLLBACK;
```

项目的 [processing_workbench_source.py](processing_workbench_source.py) 中 `ssh_query()` 已使用 `sting-infra21`，因此会沿新的 Windows 通道访问，代码中的目标别名不用改。它还保留只读事务、租户设置及 RLS 检查。其他脚本只有使用这个 SSH 别名时才会自动复用通道。

### 本机 psql 或 libpq 客户端通过 25432 连接

前提是安装客户端、开启第三节的数据库隧道，并取得所选数据库的 TCP 登录凭据和 CA 公证书。SSH 登录密钥不是数据库密码；前面的容器内免密码查询也不代表 TCP 登录不需要密码。

需要 TCP 客户端时，可通过已验证的 SSH 连接把 CA 公证书保存到本机私有配置目录：

```sh
mkdir -p /Users/lychee/Documents/project/socai2/.local/remote-21/private
chmod 700 /Users/lychee/Documents/project/socai2/.local/remote-21/private
scp sting-infra21:/opt/sting-aisoc-socai2/certificates/socai2-ca.crt \
  /Users/lychee/Documents/project/socai2/.local/remote-21/private/ca.crt
```

2026-11-07 在线读取的 PostgreSQL 证书包含 `IP:192.168.1.21` 和 `DNS:kafka`，不包含 `localhost` 或 `127.0.0.1`。因此，libpq 连接必须区分“TCP 连接地址”和“证书中的服务器身份”：

```text
host=192.168.1.21       # 用于校验远端证书身份
hostaddr=127.0.0.1     # 实际连接本机 SSH 隧道
port=25432
sslmode=verify-full
```

下面是 `psql` 模板。将 `REMOTE_READ_ROLE` 换成已发放的远端只读账号，数据库名按本次目标选择；密码由提示输入，不写进命令或文档：

```sh
psql -X -W -v ON_ERROR_STOP=1 \
  "host=192.168.1.21 hostaddr=127.0.0.1 port=25432 dbname=aisoc user=REMOTE_READ_ROLE sslmode=verify-full sslrootcert=/Users/lychee/Documents/project/socai2/.local/remote-21/private/ca.crt"
```

连接后先执行 `SELECT current_database(), current_user;` 确认身份，再按上面的事务方式设置租户并查询。`host` 与 `hostaddr` 的配合是 [PostgreSQL libpq 的正式连接参数](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS)；它不能直接套到项目的所有 Python 驱动中。

## 五 本地项目接入 21 需要改哪些配置

### 已有远端接口和本机运行源码是两种用法

如果测试的是 **21 已部署的 HTTP API**，开启相应 API 转发后，把测试客户端的 Base URL 设置为 `http://127.0.0.1:28000`，或明确选用历史验证 API 的 `http://127.0.0.1:28020`。使用该 API 所属环境的认证身份；客户端无需设置 `DATABASE_URL`。历史 `28020` 不能用来访问任意一个其他库。

如果读取的是 **Mac 当前 checkout 的 API 数据**，使用已实现的 `run.py api --profile .local/remote-21/profile.toml`，目标为正式 `aisoc.socai2`，仅开放已有查询路由。地址/端口/库/角色/租户/TLS 等在 profile 中，凭据在受限私密文件中；原 `.local/local-investigation/` 环境及数据保留。下面同时列出本次已实现的 API 适配和仍未处理的其他服务，不能把它们一起启动。

| 配置或入口 | 当前实际行为 | 接入远端测试环境所需调整 |
| --- | --- | --- |
| [deploy/local-investigation/config.py](../../deploy/local-investigation/config.py) | 旧模式仍固定本机配置，硬编码存量已登记 | 新远端模式使用 [remote_profile.py](../../deploy/local-investigation/remote_profile.py) 加载显式 TOML；不借用本机库名、角色或密码 |
| [deploy/local-investigation/run.py](../../deploy/local-investigation/run.py) | 已增加 API 专用 `--profile`，管理其 SSH 转发和只读 API | 只使用所选文件，禁止混用 Fusion/模型预检；旧 `.env` 或 shell 变量不会隐式切换目标 |
| [services/api/app/db/database.py](../../services/api/app/db/database.py) | 旧 asyncpg 行为保留；新增显式 psycopg URL 透传 libpq TLS 参数 | 已实测 `hostaddr` 为本机隧道、`host` 为 21 证书身份、`verify-full` 和 CA；错身份拒绝 |
| [services/api/app/socai2_main.py](../../services/api/app/socai2_main.py) | 独立 API 仍显式拒绝 `aisoc`，该保护未修改 | 正式读取由新增 [remote_readonly_api.py](../../deploy/local-investigation/remote_readonly_api.py) 复用 GET 路由，校验只读身份及实际库 |
| `CLICKHOUSE_HOST/PORT` | 本机启动器固定为 `127.0.0.1:19000` | Mac 原生进程通过隧道时使用 `127.0.0.1:29000`；HTTP 客户端另用 `28123` |
| `CLICKHOUSE_DATABASE`、`SOCAI2_LAKE_DATABASE` | 本机启动器固定为 `socai2_local_validation` | 与远端测试批次一致；交接样例使用 `socai2_next_validation`，生产使用 `aisoc`；读写账号分别配置 |
| `CLICKHOUSE_USER/PASSWORD` | 本机 reader/writer 身份 | 替换为目标远端空间的身份，不复用本机密码 |
| `REDIS_URL` | 固定 `redis://127.0.0.1:16379/0` | 如该进程需要 Redis，改为本机 `26379` 并保留所分配的远端 ACL 身份和逻辑 DB；不能统一写 DB0 |
| `OPENAI_BASE_URL` | 本机旧批次可指向 DeepSeek | 选择 21 网关时用 `http://127.0.0.1:24000/v1`；同时匹配网关 key、模型、协议和 Schema profile |
| 认证和租户 | 正式只读 profile 绑定业务租户和本机服务访问 token | 使用既有 `socai2_prod_reader`；不复制生产登录密钥，不调用会写 `last_used_at` 的 API key 认证；不创建生产身份/授权 |
| [deploy/local-investigation/fusion_app.py](../../deploy/local-investigation/fusion_app.py) | `verify_route()` 强校验本机 PG/CH/Redis/Kafka 地址、账号、topic/group | 远端入口需要按所选 profile 校验相同的隔离边界，不能只删掉断言；启动 Fusion 会实际消费消息，需先落实 Kafka 路由及本批 topic/group |
| 本地验证和初始化脚本 | `initialize.py`、`validate_flow.py`、`seed_context.py` 等引用固定本机库名、角色、租户和端口 | 不把旧初始化脚本改目标后直接执行；新测试入口明确目标和批次，保留历史材料。结构变更按项目 OpenSpec 与人工确认流程处理 |

**新 profile 使用 psycopg，不能将其 DSN 原样改成 asyncpg。** asyncpg 没有 libpq 等价的 `hostaddr` 参数，直接塞入 DSN 不会自动成为隧道地址。见 [asyncpg 官方连接参数](https://magicstack.github.io/asyncpg/current/api/index.html#asyncpg.connect)。本次通过 SQLAlchemy 异步 psycopg 保持远端证书身份验证，未用关闭 TLS 或忽略证书的方法。

只有网络地址部分可以按下列内容填写；它不是一份可直接启动的完整 `.env`：

```dotenv
# 适用于直接在 Mac 上运行的进程，且对应临时隧道已开启
CLICKHOUSE_HOST=127.0.0.1
CLICKHOUSE_PORT=29000

# 选择 21 模型网关时的候选配置；实际模型路由以本批核对为准
OPENAI_BASE_URL=http://127.0.0.1:24000/v1
OPENAI_MODEL=aisoc-investigation
SOCAI2_MODEL_PROTOCOL=chat_completions
SOCAI2_MODEL_SCHEMA_PROFILE=vllm_grammar_v1
```

数据库 DSN、CA、库名、湖空间、Redis DB、账号、租户及模型 key 都需要按选定环境补齐。不要全局替换仓库中的 `192.168.1.21`、`aisoc`、`15432`，也不要修改已经封存批次的配置或脚本来重跑旧批次。

本地源码接远端测试库的实施顺序是：

1. 选定本轮独立数据库、湖空间、租户和账号，明确本轮读取或写入的范围。
2. 开启所需临时隧道，准备独立私有配置，完成上表中的启动器与数据库 TLS 适配。
3. 用实际应用驱动只读核对数据库名、当前账号、TLS 校验和租户隔离，确认没有误连生产库或旧本机库。
4. 启动独立 API，先验健康状态和授权 GET；需要模型、写操作或 Kafka/Fusion 时，再按该轮测试计划执行。

部分历史工具写死 Windows SSH 路径和目标。例如 [verify_socai2_store_20261103.py](verify_socai2_store_20261103.py) 使用 `C:/Users/lychee/.ssh/...` 与 `root@192.168.1.21`，不会自动复用本机别名。后续应在新的测试入口中参数化 SSH 命令和目标，使用本机 `ssh` 与 `sting-infra21`，同时保留它原来的隔离数据库和角色边界；不为网络切换改写历史证据。

### 如果项目进程在 Docker 中运行

容器里的 `127.0.0.1` 指容器自身。OrbStack 的普通容器可用 `host.docker.internal` 访问 Mac 上的服务，例如湖客户端连接 `host.docker.internal:29000`；实际使用前从目标容器验证对该 loopback 隧道的可达性。PostgreSQL 仍须解决前述证书身份问题，CA 文件也需要挂载进容器，不能直接使用 Mac 文件路径。见 [OrbStack 容器访问 Mac 的说明](https://docs.orbstack.dev/docker/network#connecting-to-servers-on-mac)。

不要为了让容器连接而直接把全部隧道改为监听 `0.0.0.0`。本次配置的工作台只监听 Mac 的 `127.0.0.1`；Windows 允许局域网使用转发入口，不等于 Mac 要向局域网公开全部服务。

## 六 排查顺序

| 现象 | 先检查什么 |
| --- | --- |
| `ssh sting-win57 whoami` 不通 | Windows 是否开机、IP 是否还是 `192.168.3.57`、两机是否同一可达局域网、SSH 是否运行 |
| Windows 可登录，`ssh sting-infra21 hostname` 不通 | Windows VPN 是否连接，`2221 → 21:22` 转发及 Windows 到 21 是否可达 |
| SSH 正常，工作台打不开 | `ssh -O check sting-infra21-tunnel`、LaunchAgent 状态和日志；端口应为 `4177` |
| 工作台返回 403 | 使用 `http://127.0.0.1:4177/`；不要改成本地 `24177` 或外部主机名 |
| `Address already in use` | 用 `lsof -nP -iTCP:端口 -sTCP:LISTEN` 确认占用者；常驻工作台只保留一个隧道实例 |
| `25432` 连接被拒绝 | 数据库临时 SSH 命令是否仍在运行；它不属于常驻工作台配置 |
| 数据库证书名称不匹配 | 实际连接走 `127.0.0.1`，证书身份仍为 21；按驱动区分 libpq 和 asyncpg 的处理 |
| 数据库登录失败或查询为空 | 核对数据库名、远端账号、权限和事务中的 `app.current_tenant_id`；网络通不等于身份正确 |
| API 报独立数据库错误 | 核对 `SOCAI2_SERVICE_DATABASE_NAME`，不要把独立 API 指向生产库 `aisoc` |
| Python 报 `No route to host`，直接 SSH 却成功 | 本机曾出现该差异，且 Python 的本地网络权限关闭。先检查对应程序的 macOS 本地网络权限，不能仅凭该报错认定 Windows 不通 |

## 七 配置文件和本次核验

| 本机文件 | 用途 |
| --- | --- |
| `/Users/lychee/.ssh/config` | SSH 别名和工作台端口映射 |
| `/Users/lychee/Library/LaunchAgents/com.lychee.socai2-ssh-tunnel.plist` | 登录自启、失败后重连 |
| `/Users/lychee/Library/Logs/socai2-ssh-tunnel.log` | 隧道错误日志 |
| `/Users/lychee/.ssh/socai2-relay-install.json` | 安装信息与备份位置 |
| `/Users/lychee/.ssh/config.before-socai2-relay-20261107-124529` | 修改前的 SSH 配置备份；恢复前需比较后来新增的其他配置 |
| `/Users/lychee/.ssh/known_hosts_socai2_win57` | 已核对的 Windows 主机公钥 |

Windows 转发配置备份位于 `C:\ProgramData\socai2-ssh-relay\backup-20261107-124324`。本文不要求再次修改 Windows 防火墙。

2026-11-07 已核验：Windows 公钥登录、经 `57:2221` 登录 21、后台工作台隧道及首页 HTTP 200、21 的 PG/CH/API/网关监听地址。随后已完成本机专用只读 API→SSH 转发→PG 的真实账号认证、严格 TLS 和正式调查数据 GET 验证，见[回执](evidence/remote-readonly-20261107/verification.json)。其余本地服务端口仍按需；完整 API 写入/Fusion/Kafka 消费和模型质量不包含在本次结果中。

本机原 AISOC 容器与旧工作台已按此前指令停止，数据卷保留。本次临时只读 API 和自有数据库转发也已关闭；需要读取正式数据时按第五节选定 profile 启动。无需为查看远端工作台恢复本地整套基础设施，也不应默认切入独立测试库。
