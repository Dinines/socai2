## ADDED Requirements

### Requirement: Model call exceptions preserve local end and dispatch facts

系统 MUST 在已创建并保存请求的实际模型调用边界保存异常结束回执，复用既有错误分类、模型响应工件、阶段交付与读取合同。发送事实 MUST 为有依据的 `true`、`false` 或未确认的 `null`，不能由模型步骤存在或一般异常分类推断。调用建立前的准备失败 MUST NOT 伪造模型调用回执；取消和新增捕获的非预期异常 MUST 在保存后继续向外传播，不成为业务成功。

#### Scenario: A call ends locally without a complete model response

- **WHEN** A/I 或共享 Case 模型调用在实际 `gateway.complete` 边界抛出运输异常、timeout、取消或未包装异常
- **THEN** 保存真实请求关联、`raw=null` 的本地响应和 `local_state=ended` 的阶段交付回执，无可交付结论且接收状态为 `no_response`，S2 已收无效信封仍保留 `unusable`
- **AND** 既有 `Outcome` / 任务 `retryable` 分类保持，未知远端结果不写确定结束时间；发送事实无证据时为 `null`，usage 未知不记零，未知调用保留冻结预留
- **AND** 阶段 `retry_allowed=false` 仅禁止本次调用重放，不取消或扩大队列既有的新 attempt 重试资格

#### Scenario: The gateway deadline expires before any send

- **WHEN** 网关精确 `timeout <= 0` 分支在任何发送前拒绝调用
- **THEN** 使用既有 `ExecutionFailure` 表达 `model_deadline_before_dispatch`、明确未执行及非临时失败，保存 `request_dispatched=false` 的本地回执，并按明确未执行核算预算
- **AND** 该规则不套用到发送后或无法确认发送事实的 timeout；HTTP schema 拒绝的既有未执行预算待遇与请求已发送事实分别保留

#### Scenario: Original reply views distinguish both local response shapes

- **WHEN** 动态原答页读取 A/I 顶层 `raw=null` 或 Case `payload.raw=null` 的已存本地响应
- **THEN** 两者均显示对应的无回复空态，保持缺工件、读取失败、正常原答与 S2 无效信封的区别，不为展示改写保存合同

### Requirement: Received invalid model envelopes have explicit failed receipts

对于调查模型 HTTP 成功响应已完整返回后发生的 JSON 解码失败或非对象顶层，系统 MUST 记录 `model_response_envelope_invalid`、已发送、本地已结束、响应不可用及不可自动重试，且不生成模型结论或新业务结果。该信封解码接点 MUST 仅用于明确选择它的调查调用，不改变其他共享客户端调用者的默认行为。

系统 MUST 保存原请求及关联错误回执和阶段交付回执；证据来自实际 HTTP 响应的状态、错误类别、字节数、SHA-256 和既有允许错误字段的受限脱敏投影。任意非 JSON 正文未保留时 MUST 如实标记，不伪造或将投影称为原文，不保存请求 URL/header、凭据或自由格式异常字符串。usage MUST 保持未知，已发送请求的冻结 token 预留不得按未执行释放。

#### Scenario: A received invalid envelope is different from no response

- **WHEN** 调查模型适配器收到 HTTP 成功响应，但响应 JSON 无法解码或顶层为数组、标量或 null
- **THEN** 本地保存的调用状态为 `failed`、`request_dispatched=true`、`local_state=ended`、`parse.state=unusable`、交付为 `none`，没有模型原答替代物或自动重发
- **AND** A/I、Case 及既有读取适配保留真实 Run/步骤/原件关联，C3 不针对该信封发起缺项补充，动态原答页能与 `no_response` 区分

#### Scenario: Neighboring failures keep existing behavior

- **WHEN** 本地 guard 在发送前拒绝、HTTP 状态非成功、完整响应尚未返回即超时，或合法 JSON 对象内的正文协议不合格
- **THEN** 不套用本条信封错误规则，保留 S1 和已有接收/未知处理，不根据任意 `ValueError/TypeError` 猜测输入错误或发送事实

### Requirement: Model input guard refusal has a known unsent receipt

当共享模型网关在 HTTP 发送前因 `LLMContractViolation` 拒绝输入时，系统 MUST 保留 guard，并通过既有 `ExecutionFailure` 表达 `not_executed=True`、`temporary=False` 和代码拥有的原因 `model_input_contract_rejected`。A、I 及 Case 模型步骤 MUST 保存失败、未发送、本地已结束、无正文、不可自动重试的回执；不得保存 guard evidence、自由格式异常消息或伪造 provider 原答/实测 usage。

该分支 MUST 复用既有模型请求/本地响应工件、`stage_delivery`、原件引用和读取接口。C3 汇总 MUST 继承底层发送事实，不能由模型步骤存在推断已发送。Case 预算核算 MUST 将该明确未执行分支按未执行处理，保持原有预算上限及未知调用的预留规则。外部告警字段合同和旧失败记录 MUST 保持原状。

#### Scenario: A or I guard refuses before sending

- **WHEN** 已保存模型请求的 A 或 I 执行在共享网关收到 `LLMContractViolation`
- **THEN** 网络不会收到该请求，模型步骤与 Run 明确失败，原件读取可取得 `raw=null` 的本地失败回执和关联阶段交付回执
- **AND** 交付回执记录 `request_dispatched=false`、`local_state=ended`、`parse.state=no_response`、无保留单元且不允许重试，原有业务结果不被新判断覆盖

#### Scenario: Case guard refusal preserves local continuation facts

- **WHEN** C3、Deep 或 C6 的共享模型调用因该 guard 被明确拒绝发送
- **THEN** 保存同类本地结束回执，现有独立阶段可依据真实终态继续或收尾；C3 不为该无回复调用发起缺项补充，汇总回执仍记录未发送
- **AND** 预算核算不虚构已用 tokens 为零；未知 usage 与明确未执行分别处理，不能占用后续阶段的 token 预留作为远端消耗

#### Scenario: Adjacent uncertain failures keep their meaning

- **WHEN** 出现其他 RuntimeError、响应信封解码错误、TimeoutError 或发送后的结果未知
- **THEN** 不套用本条 guard 拒绝逻辑，不根据异常名称统一改判为未发送，不扩大自动重试、纠正或续写

### Requirement: 21 Kafka internal client transport

21 上的 Fusion 和 UEBA 使用指定的同机 Kafka 内部监听和原有消费组。启用此 profile 时，客户端 MUST 通过配置的明文协议收发，Kafka Topic 与已提交位点 MUST 保持原业务身份。

#### Scenario: Transition the two deployed Kafka clients

- **GIVEN** 同机监听已经通过合成记录的投递与读回，业务依赖解析与当前实例一致
- **WHEN** 依次替换 21 的 Fusion 和 UEBA 并读取实际 Kafka 配置
- **THEN** 两个实例达到就绪状态，沿原消费组和位点继续工作，Kafka 和转发器保持原在役实例
