## ADDED Requirements

### Requirement: Refresh authorizes its possible retained summary before model work
手动概况刷新 SHALL 在同一 summary 行锁下检查最新旧正文来源，并在模型调用和 last_attempt 更新前完成权限判定。请求包含调查，或非空旧正文来源包含调查时 MUST 要求 cases:read；纯基础概况沿用原 alerts:write/read。

#### Scenario: A basic refresh could retain a Case summary
- **WHEN** 旧正文来源 include_investigations=true 且基础刷新调用者没有 cases:read
- **THEN** 在模型/新尝试/成本写入前返回现有权限 403，保留旧正文及记录

#### Scenario: A basic-only reader refreshes a basic summary
- **WHEN** 请求及非空旧正文均不包含 Case 调查，且调用者具有原 alerts 写读权限
- **THEN** 不额外要求 cases:read，沿原基础生成流程处理

### Requirement: Failed refresh uses the retained text source mode
生成失败保旧正文时，系统 SHALL 保留旧正文、generated_at、source_refs 和 source_fingerprint，以旧正文模式的当前材料及对应 source_updated_at 计算 stale；成功则采用本次请求模式。MUST 区分基础与 Case 来源视图，不混用时间戳。

#### Scenario: Basic refresh fails after a Case summary was saved
- **WHEN** 有权限调用者发起基础刷新失败，事件及已有 Case 来源未变
- **THEN** 返回旧 Case 正文及其模式的当前材料，stale=false，与随后 GET 一致，失败尝试仍可见

#### Scenario: Case refresh fails after a basic summary was saved
- **WHEN** Case 模式刷新失败而旧基础来源未变
- **THEN** 返回旧基础正文并用基础材料计算 stale，不因当前加载了 Case 列表就把旧文标旧

#### Scenario: A summary is generated or its old source changed
- **WHEN** 刷新成功，或刷新失败且旧正文的实际来源已变化
- **THEN** 成功保存并返回新模式正文；失败保旧并按真实来源变化标旧；无旧正文的失败保持 not_generated 和 stale=null

### Requirement: Admitted refresh attempts are not rolled back by late fallback authorization
系统 SHALL 在既有事务中保存已准入刷新尝试的时间、错误及可得用量/费用结果，不在模型之后因返回旧正文新增权限拒绝而回滚；未知用量 MUST 保持未知，不要求新增异常恢复或费用补偿。

#### Scenario: A permitted model reply has usage but an invalid summary
- **WHEN** 所需权限已前置通过且模型返回 usage 但正文无效
- **THEN** 保留旧正文并提交本次 invalid_summary_response、可得 usage 和按原成本逻辑取得的结果，不能在模型后触发保旧权限 403
