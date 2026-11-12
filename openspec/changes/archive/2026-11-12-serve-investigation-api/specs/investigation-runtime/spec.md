## ADDED Requirements

### Requirement: Explicit read and write data target
独立服务 SHALL 由显式配置选择数据库目标；只有读取与所有已启用调查写入连接均匹配该目标时才能就绪，不得按数据库名称硬编码排除正式库，也不得隐式回落至旧隔离库。启动 SHALL 只检查已有连接和结构，不执行DDL或启动消费者。

#### Scenario: Start a current formal or local service
- **WHEN** profile指定了数据库，认证/读取与调查写入连接均指向该目标且连接可用
- **THEN** 服务就绪，并在同一HTTP入口提供现有43操作；Q相关3操作继续返回501

#### Scenario: Reject inconsistent write target
- **WHEN** 已启用写入但缺少写连接，或其主机/端口/数据库与读取目标不一致
- **THEN** 服务启动失败并报告不含凭据的配置错误，不向任何目标写入

### Requirement: Manual stage execution uses the investigation writer
手动告警分诊和事件诊断 SHALL 使用显式调查写连接完成已有编排、保存和读回，保持原请求/响应合同及幂等规则；服务退出 SHALL 释放读取与调查写连接池。

#### Scenario: Execute and read the same persisted run
- **WHEN** 已认证调用者通过启用的独立服务提交手动A/I操作
- **THEN** 原业务服务使用调查写会话保存Run及结果，并从同一数据库读取回执；不会用通用只读连接进行写入

### Requirement: Publish only the verified HTTP entry increment
独立正式服务 SHALL 以已核验的部署业务版本为基础，仅发布本阶段入口/连接增量，并保留原主API、旧隔离服务及其数据。交接文档 SHALL 区分正式与本机数据目标，不把路由存在或模型替身通过表述为真实模型质量通过。

#### Scenario: Read the published service back
- **WHEN** 新正式入口发布完成
- **THEN** 其43操作目录、实际数据库目标及本批Case/H保存读回与回执一致，旧服务保持；无需跨入口混用记录ID

### Requirement: Independent investigation HTTP entry
The current investigation application SHALL expose a liveness response and its actual OpenAPI contract, and SHALL remain independently startable without the legacy application or background workers.

#### Scenario: Inspect the running entry
- **WHEN** a caller requests liveness and the investigation schema
- **THEN** it receives process liveness and the registered Alert/Incident/Case route definitions, without a model call or business write.

### Requirement: Caller preserves the selected API and request identity
The HTTP caller SHALL use the operator-selected investigation/core base, read its Bearer token from environment, send JSON without generating an operation key, and make no automatic POST retry or redirect.

#### Scenario: Follow existing API-relative links
- **WHEN** the operator passes a returned investigation path or core Case path
- **THEN** the caller sends it to the corresponding configured API base with the original body and reports the HTTP result.
