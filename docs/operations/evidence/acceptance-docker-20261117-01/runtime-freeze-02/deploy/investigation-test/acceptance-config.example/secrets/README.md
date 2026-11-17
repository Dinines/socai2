# 运行时文件

此目录不提供凭据。复制配置示例到受控目录后，按实际目标填写所需文件，并让配置的非root UID可读：

- `analysis-database-url`：完整PostgreSQL连接URL，仅此文件保存数据库凭据。
- `lake-password`：湖查询账号的实际密码。
- `producer.env`：明确`KAFKA_BOOTSTRAP_SERVERS`、`KAFKA_SECURITY_PROTOCOL`，以及实际TLS/SASL配置；地址必须与kafka.json一致。CA、客户端证书及私钥若使用，也放在这个只读目录，环境字段引用容器内的`/run/acceptance-config/secrets/...`路径。

配置和凭据都从宿主只读挂载，不写入镜像、业务材料、报告或Git。离线转换、准备、状态及报告不读取这些文件，可不提供。示例中的`.invalid`主机只说明字段格式，实际执行前必须由操作者明确替换。
