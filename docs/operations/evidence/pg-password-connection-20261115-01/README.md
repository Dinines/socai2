# PostgreSQL普通密码连接：独立直接验证

2026-11-15北京时间16:55–16:58。**21普通只读账号的TLS require无CA连接，以及本机普通账号的实际HTTP两池/事务回滚均通过。** 两段使用不同环境、不同传输模式，不能合并宣称21候选HTTP同源TLS读写已通过。未部署候选、改变21认证或运行调查/模型/Kafka。

## 21：真实TCP、TLS、普通密码

[reader-01.json](reader-01.json)与[实际驱动](validate_reader.py)：通过新建临时SSH转发到21现有`aisoc`，使用已有普通`socai2_prod_reader`和受控密码文件。实际调用本轮`app/db/database.py`的`_normalize_async_pg_url`，未以测试实现替代连接代码。

- `sslmode=require`生成`SSLContext`，`verify_mode=CERT_NONE`、`check_hostname=false`、加载CA数0；未配置客户端证书或私钥。测试进程故意继承一个不存在的`PGSSLROOTCERT`路径，仍能成功连接，未改写HOME或删除本机证书。
- 真实会话`session_user=current_user=socai2_prod_reader`，非superuser，数据库`aisoc`，事务只读；自己的`pg_stat_ssl.ssl=true`、协议`TLSv1.3`。
- 同目标新建错误密码连接，返回`InvalidPasswordError`/SQLSTATE `28P01`；没有复用已认证连接或管理员SET ROLE。
- 新旧源码摘要一致。临时转发已停止；21仅查询会话身份/TLS，业务写入0。

私密验证配置为`.local/pg-password-connection-20261115-01/reader-config.json`，其中只引用既有凭据文件，公开回执无密码或完整DSN。原只读profile仍保留原件，本验证按新目标单独组装连接，没有运行旧verify-full配置入口。

## 本机：普通LOGIN、真实HTTP两池、最小回滚

[只读预检](preflight.json)确认`127.0.0.1:28413/v12_upgrade_dev`的SSL开关为off；此容器管理查询不计密码验证。原F5的`v12_developer`是NOLOGIN且通过管理员SET ROLE使用，故没有沿用它冒充普通密码。

调查方随后[供给普通LOGIN账号](../pg-password-config-20261115-01/local-writer-preparation.json)`socai2_password_writer_20261115`及受控密码；测试没有修改账号、HBA或重启现有库。[writer-01.json](writer-01.json)与[实际驱动](validate_writer.py)使用这个账号、明确`sslmode=disable`：

| 核对 | 实际结果 |
| --- | --- |
| HTTP加载 | 独立应用真实lifespan连接实际查询池和Case写池；没有替换engine、session或用例实现 |
| 登录身份 | 两池session_user/current_user都是该普通LOGIN账号，非superuser、无BYPASSRLS、无SET ROLE；同一隔离库，ssl=false |
| 正确密码 | 两池均成功连接；两个不同池使用同一普通账号，不据此声称读写角色隔离已验 |
| 原记录 | 复用F5已结束Case `75808044-78a5-5e4c-b57d-cf93fad8cb92`，tenant `a7367ebc-823f-4fe7-a0a0-8b54c00cf9bd`；不重派旧Run |
| 写入与回滚 | 实际Case写池事务内修改该Case title，UPDATE RETURNING及同事务SELECT均读到新标记，随后显式rollback；没有提交 |
| 保存边界 | 独立查询池回滚后读到完整Case行与此前相同，前后SHA均`ba896981…`；仅临时事务内有变化 |
| HTTP读取 | `/api/v1/socai2/cases/{id}/management`前后各一次真实PG/ASGI GET，均200、JSON摘要相同；无HTTP POST/PATCH提交，无外部HTTP监听端口 |
| 错误密码 | 全新TCP连接明确28P01拒绝，不能用trust通过解释正确密码结果 |
| 源码与资源 | 归一化、Case写池及HTTP runtime三个受测文件前后摘要相同；应用lifespan退出并关闭两池 |

实际配置为`.local/pg-password-connection-20261115-01/writer-config.json`，引用已供给私密writer文件和既有F5身份；配置与脚本分开。没有新Case、Run、业务提交或清理；本机证据只证明密码/两池/回滚，**不证明TLS require写入**。

## 复用证据及未验范围

处理方[36项通过、3项跳过的原输出](../pg-password-config-20261115-01/direct-03.txt)与HTTP方[13项部署检查、r2完整包/两池装配](../streaming-http-pg-password-20261115-01/README.md)按其原范围复用，跳过项不计通过；测试侧没有重新执行这些检查或W1/模型测试。本批两份直接驱动Ruff通过，[同change安排](../../../../openspec/changes/schedule-streaming-investigation-updates/pg-password-validation-20261115.md)strict通过；不能将这些数量累计为业务整链覆盖。

21候选新库与迁移、普通读写供给、实际18424/18480、同候选TLS业务提交/读取、W2与Kafka真实模型整链仍待。Kafka TLS及其他组件证书保持；模型和测试服务说明本就没有PG CA强制项，本次未改它们的运行配置。旧失败/证据保持，未提交或推送。
