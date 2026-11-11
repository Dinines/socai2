## ADDED Requirements

### Requirement: Case and human task writes use an explicit configured database

Case/H HTTP 写路径 SHALL 在既有写开关启用时使用 `SOCAI2_CASE_DATABASE_URL` 所选连接，沿用服务端认证的 actor/tenant 和现有事务语义。GET SHALL 使用当前读取连接；系统 MUST NOT 因缺写配置静默回退到另一数据库或读取身份。

#### Scenario: A configured user creates or updates a Case or human task
- **WHEN** 写开关启用、显式写连接存在且请求满足现有合同
- **THEN** 原服务在该连接中按认证租户执行，持久化结果仍能由原 GET 读取，不改变告警材料和交接字段

#### Scenario: Write configuration is missing
- **WHEN** 写开关启用但未配置 Case 写连接
- **THEN** 非 GET 请求明确返回配置不可用，未启动服务写入；已开放 GET 仍按原读取路径工作

### Requirement: Human feedback remains an explicit versioned input to the next investigation

系统 SHALL 沿用 Case 创建、人工任务创建/修订及显式 prepare/start 接口；人工保存 MUST NOT 自动运行调查或代表业务授权。后轮领取时冻结适用的已完成人工版本，保留原文、范围及来源角色。

#### Scenario: A user completes and revises feedback before starting the next run
- **WHEN** 用户在同一 Case 保存人工补充并修订，再显式准备和启动下一轮
- **THEN** 后轮使用领取时选中的适用版本，输入可定位其原文和 human_statement 来源；旧版本和前轮结果仍可读，后轮结果由原 Result 路径读回

### Requirement: Deployment selects Case write configuration without replacing general API identity

发布 SHALL 从显式受控处理 profile 生成 Case 写入配置并单独启用 HTTP 写开关，不改通用 API 数据库连接，不将凭据写入日志、文档或 Git。当前调查/告警字段合同、有限执行和失败状态 MUST 保持。

#### Scenario: The deployment maps the existing processor connection
- **WHEN** 发布清单声明将处理 DATABASE_URL 映射到 Case 写入配置
- **THEN** 只生成允许的目标环境键，实际 Case 写入选择处理连接，通用认证及读取仍使用原连接

### Requirement: Functional evidence and model quality are reported separately

验收 SHALL 记录实际 HTTP、数据库、执行器、模型/传输和认证替身的覆盖范围，核人工版本及保存读取；持续正文问题维持开放和 NOT_PASSED，不将 HTTP 成功或当前采用当成语义质量通过。

#### Scenario: The HTTP loop succeeds while a known model narrative error remains
- **WHEN** 正常操作、冻结版本和保存读取成立，但已登记的模型正文偏差仍出现
- **THEN** 记录具体原答与质量限制，按负责人后置决定继续独立功能交付，不重采样或改写原答追认成功
