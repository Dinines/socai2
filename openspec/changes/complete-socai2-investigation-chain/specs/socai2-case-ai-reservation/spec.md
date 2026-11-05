## ADDED Requirements

### Requirement: Deferred case AI operations have explicit reserved endpoints

系统 SHALL 预留Case AI发送问题、将答复保存到正式调查记录、明确采用结果的三个POST入口及最小类型合同；Q业务暂缓期间，有效请求 MUST 返回HTTP501和`case_ai_not_implemented`。系统不得返回模拟答复、成功Run/Result ID或声称保存/采用已完成。

#### Scenario: An authorized user sends a question
- **WHEN** Case API开关开启且有写权限的用户向`/{case_id}/ai/messages`提交合法问题
- **THEN** 返回501及明确未实现说明，不生成答复或执行记录

#### Scenario: A user requests saving or adopting an answer
- **WHEN** 用户调用`/{case_id}/ai/messages/{message_id}/save`或`/{case_id}/results/{result_id}/adopt`
- **THEN** 合法请求返回相同501合同，不保存正式结果、不更改Case当前判断，也不据此确认目标实体存在

### Requirement: Reserved operations preserve access controls without execution

预留接口 SHALL 复用现有认证、`cases:write`和Case API默认关闭开关，拒绝非用户工作负载以及客户端注入tenant/actor等额外属性。占位实现 MUST 不进行Case业务读写、模型/Tool调用或领取基础调查活跃槽；认证自身仍沿用现有依赖。

#### Scenario: The API is disabled
- **WHEN** 已认证有权用户调用预留接口但Case API开关关闭
- **THEN** 返回503的禁用状态，不启用任何Q业务

#### Scenario: A read-only caller requests an AI operation
- **WHEN** 用户仅有cases:read而没有cases:write
- **THEN** 返回403，不把预留接口作为权限绕过入口

#### Scenario: A caller supplies a tenant field
- **WHEN** 请求体除最小类型字段外包含tenant_id或其他额外属性
- **THEN** 返回请求校验错误，不接受客户端自报的操作身份或租户
