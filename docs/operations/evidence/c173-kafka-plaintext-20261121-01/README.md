# 21 Kafka 客户端免 SSL 切换

2026-11-21，停止过的 UEBA 已先恢复为原容器。随后将 21 的 Fusion 和 UEBA 的 Kafka 客户端切换到同机 Docker 网络内的 `kafka:29092`，协议为 `PLAINTEXT`。现网配置随发布保存。[客户端配置](../../../../deploy/aisoc21/c173-release-20261121-03/kafka-internal.json) · [UEBA 恢复记录](../c173-ueba-disabled-20261121-01/README.md#当日恢复)

两套现用镜像各通过一次独立测试 Topic 的合成投递与同位点读回。候选解析到原数据库、缓存和湖服务。逐一切换后，Fusion 和 UEBA 的就绪接口正常，原消费组均为稳定状态，原已提交位点均可读且未回退。正式 HTTP 就绪和告警、事件、Case 列表读取通过。

Kafka 与 SpiritHub 转发器在役，broker 的共享 SSL 监听仍可用。两套客户端的 `KAFKA_SSL_CAFILE` 均已去掉。Fusion 的 Kafka 专用证书挂载已移除，UEBA 的同一证书挂载仍供 `PGSSLROOTCERT` 使用。原实例和详细位点回执保留在 21 的受控部署目录。

## PostgreSQL 核验

UEBA 当前通过 asyncpg 使用账号密码和 `verify-full`。在同容器复用应用连接，实际 PostgreSQL 会话启用了 TLS，客户端要求服务端证书和主机名验证。仅在一次性核验进程移除 `PGSSLROOTCERT` 后，连接返回 `ClientConfigurationError`。Kafka 切换后的在役 UEBA 仍使用原 PostgreSQL 连接模式。
