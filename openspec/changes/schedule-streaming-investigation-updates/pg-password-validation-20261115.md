# 第11步配套：PostgreSQL普通密码连接的独立直接验证

2026-11-15。承接[本步连接简化设计](stage11-candidate-design-20261115.md#postgresql连接简化2026-11-15负责人确认)，仅验证当前连接配置调整，不新增任务树、业务批次或恢复框架。**状态：代码交接后的本步直接验证通过，实际边界见[回执](../../../docs/operations/evidence/pg-password-connection-20261115-01/README.md)。** 21普通reader已证实require无CA/TLS1.3与错误密码拒绝；本机普通LOGIN已证实真实HTTP两池、错误密码拒绝及事务回滚。21候选HTTP同源TLS读写仍未执行，不能由两段异环境证据核销。

## 目标与范围

部署人员提供地址、端口、库名、用户名及密码/私密文件引用；模板默认`sslmode=require`，不要求客户端CA、证书或私钥。验证配置装配、真实TCP密码认证、HTTP查询池/写入池实际加载与最小事务写入。Kafka TLS、模型路由、业务表合同、调度规则和现有21认证均保持；不运行模型、嵌入、Kafka或新调查。

先复用已确认本机隔离资源，证据使用新的验证目录，旧F1–F5任务/原答不重派。2026-11-15本次只读确认本机`127.0.0.1:28413`对应`socai2-case-trigger-db-20261115`，数据库`v12_upgrade_dev`的`SHOW ssl`为off；该查询经容器管理连接，只证明开关状态，**不证明普通账号密码有效**。不为此重启或改造共享测试库。

据当前供给，分成两段证据：21已有普通reader通过真实TCP验证`require`无CA及错误密码拒绝，只读；本机普通写账号通过显式本机传输配置验证实际密码和回滚写入。若本机使用`disable`，回执必须写明，不能将该段算作`require`写入通过。HTTP两池的同一候选TLS端到端连接仍留到候选就绪；本步不拿跨环境结果冒充同一条完整HTTP链。

## 实施方须交付的最小内容

| 提供方 | 本步供给 | 核对点 |
| --- | --- | --- |
| 调查 | 当前连接简化源码/配置及直接测试、冻结文件摘要；普通reader/writer的受控私密引用与准确目标 | `production_profile.py`不再强制verify-full/CA；runtime_values、production_processing、processing_job、安装器及当前调度模板一致；不因缺PGSSLROOTCERT/SSL_CERT_FILE取键失败 |
| HTTP | 当前候选profile、prepare实际装配输出、读写两连接的加载代码及直接检查 | 移除PG专用CA必填/挂载；`DATABASE_URL`与`SOCAI2_CASE_DATABASE_URL`仍明确且同库；当前80操作/业务合同保持，不复用正式旧18024冒充新候选 |
| 运行提供方 | 21普通reader的密码认证连接；本机普通writer与可回滚的已存在隔离记录/tenant；如两角色分别存在则各自给引用 | 不使用postgres管理用户、docker socket trust或先以管理员连接再SET ROLE证明登录；不打印密码、连接原文或服务端密码散列 |
| 测试 | 显式验证profile、预期、原始脱敏回执及前后读回 | profile记录实际环境/传输方式、证据来源、连接身份、允许操作、未验边界；不从旧测试配置猜账号或回落其他数据库 |

本机TLS开关已核。21已有普通reader引用、新供给本机普通LOGIN writer和修改后的连接代码已交接，已据此完成两段直接验证；原NOLOGIN角色+管理员SET ROLE不算普通密码证据。已通过W1/模型验证未重跑。

## 最小验证顺序与判据

| 步骤 | 操作 | 必须保存的判据 |
| --- | --- | --- |
| P1 配置装配 | 以本轮最新五项连接信息和默认require装配处理、HTTP读写及调度所用配置；不提供CA文件。复用实施方离线检查，只复核直接受影响输出 | 明确目标、账号和require；没有PG客户端证书/私钥/CA依赖。继承旧PGSSLROOTCERT不得变为新连接前置，也不能静默降到prefer/disable。私密值不输出 |
| P2 真实只读认证 | 新进程使用21普通reader、正确密码、无客户端CA证书/私钥，通过实际选定客户端TCP连接；再用一个错误密码建立新连接 | 正确密码成功；错误密码在认证阶段失败，不能复用池中成功连接。读回current_database/session_user/current_user/inet_server_addr及自己的pg_stat_ssl.ssl/version，确认目标与TLS；不创建/更新业务记录 |
| P3 本机写池认证与回滚 | 使用本机明确普通writer，经TCP正确密码连接；错误密码新连接应失败。通过实际Case写池入口建立事务，对提供方指定隔离Case的title做一次唯一标记UPDATE RETURNING，随后显式rollback | 本连接session_user就是该普通账号，无管理员SET ROLE旁路；事务内读见新值，回滚后独立查询池读取完整Case行与HTTP管理视图保持。相关事务修改随rollback撤销，不把本步扩展为全审计表对账。实际ssl模式单独记录；不生成新Run/任务/业务对象 |
| P4 HTTP两侧加载 | 在本机明确配置下加载独立HTTP真实lifespan，使用真实查询池与写池，读现有隔离对象；写验证沿P3实际写池，不替换create_async_engine或get_case_write_sessions | 查询/写池均实际连同一目标；不是只验证URL字符串或只SELECT健康。保存两池脱敏身份/目标及查询结果，正确配置可加载；启动本身没有创建调查。若写验证只回滚，不能报告HTTP业务POST/PATCH已提交通过 |
| P5 收尾 | 关闭本次连接/临时HTTP进程，核配置与指定隔离记录前后摘要，保存检查结果及缺项 | 21只有读取；本机事务已回滚；没有重派历史任务、业务提交、模型/Kafka/嵌入。实际默认TLS写入或21候选HTTP未验分别登记，不因本机正常读取核销 |

P3由实施方确认准确Case/tenant及版本后执行，不扫描全库找可写对象，不为简化测试清理旧记录。更新只在明确事务内，异常也必须rollback；无需额外为本步创建完整调查场景。若当前普通writer无法对指定记录回滚写入，保留依赖问题，由提供方供给合法隔离目标，不换管理员连接冒充通过。

HTTP的[当前lifespan](../../../services/api/investigation_http/adapters/runtime.py)会连接两池，但写池只读取current_database；因此它不能独自证明写入能力。当前[普通写池入口](../../../services/api/app/db/case_database.py)与[查询池归一化](../../../services/api/app/db/database.py)都应使用交付后的真实代码。已有mock连接测试可复用为参数检查，不能替代P2/P3。

## 连接参数与证据中的易漏边界

- `require`应继续使用TLS而无需客户端验证CA；本机`ssl=off`的`disable`结果仅证明密码/写入，不代替TLS。使用`pg_stat_ssl`核实际连接，不由URL文字推断。
- libpq在默认root.crt存在时，`require`可能按verify-ca处理；客户端证书也可能从默认文件加载。确认本轮客户端没有隐含PG证书文件/变量依赖；不能删除用户证书或改写HOME来制造通过。asyncpg新require上下文须以交付代码为准。[PostgreSQL 16客户端SSL说明](https://www.postgresql.org/docs/16/libpq-ssl.html)
- 普通TCP账号正确/错误密码使用新连接；日志仅保存身份、目标和脱敏错误类别/SQLSTATE，不记录密码、DSN全文、passfile或认证散列。不能只靠psql退出码或docker内成功断言普通密码有效。
- 若需密码含特殊字符的参数检查，复用实施方URL编码用例，不另造多账号矩阵。五项实际目标不得从shell中旧数据库环境变量补齐。
- PG专用CA删除不能误删Kafka证书或其他HTTPS客户端的独立信任配置；检查被修改的runtime生成和子进程传递范围，而不宣称全仓所有历史CA已清理。
- [pg_stat_ssl](https://www.postgresql.org/docs/16/monitoring-stats.html#MONITORING-PG-STAT-SSL-VIEW)只核自己的连接，不新增全库观测或权限专项；两个环境的结果分别保留。

## 回执与停止条件

证据目录为`docs/operations/evidence/pg-password-connection-20261115-01/`。准备阶段先保存`preflight.json`（本机SSL只读观察）；代码交接后执行结果另存新文件，记录源码/配置摘要、脱敏连接目标、session_user/current_user、TLS、正反密码结果、事务内/回滚后读回及HTTP两池加载。失败/未验保持原状态，不复用旧结束批次追认成功。

本步通过只代表已明确覆盖的连接/认证/回滚路径。源码与配置交接未齐、错误密码未被拒绝、需要CA才能连、读写混库或回滚后记录改变时停在本步，不启动调查、模型或21候选部署补结论。候选完整HTTP/TLS同源提交与Kafka整链仍按原计划后续逐步验证。
