## MODIFIED Requirements

### Requirement: Explicit read and write data target
独立服务 SHALL 由显式配置选择数据库目标；只有读取与所有已启用调查写入连接均匹配该目标时才能就绪，不得按数据库名称硬编码排除正式库，也不得隐式回落至旧隔离库。启动 SHALL 只检查已有连接和结构，不执行DDL或启动消费者。

#### Scenario: Start a current formal or local service
- **WHEN** profile指定了数据库，认证/读取与调查写入连接均指向该目标且连接可用
- **THEN** 服务就绪，并在同一HTTP入口提供当前47操作（原43及Case管理4操作）；Q相关3操作继续返回501

#### Scenario: Reject inconsistent write target
- **WHEN** 已启用写入但缺少写连接，或其主机/端口/数据库与读取目标不一致
- **THEN** 服务启动失败并报告不含凭据的配置错误，不向任何目标写入

### Requirement: Publish only the verified HTTP entry increment
独立正式服务 SHALL 以已核验的部署业务版本为基础，仅发布本change已验证的业务增量，并保留原主API、旧隔离服务及其数据。交接文档 SHALL 区分正式与本机数据目标，不把路由存在或模型替身通过表述为真实模型质量通过。

#### Scenario: Read the published service back
- **WHEN** 新正式入口发布完成
- **THEN** 其当前操作目录、实际数据库目标及本change对应业务保存读回与回执一致，旧服务保持；无需跨入口混用记录ID
