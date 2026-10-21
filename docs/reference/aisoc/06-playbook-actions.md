# 06 Playbook、审批、响应执行与验证（M09 / M10）

> 用途：固定上游源码与历史证据分析（2026-10-20对齐）。本轮负责服务端剧本、审批响应与效果记录；真实执行仍需明确目标和授权，不因迁移而自动启用。 当前职责见[范围](../../operations/alert-processing-scope.md)，阶段退出见[路线](../../operations/service-roadmap.md)，执行批次见[依赖计划](../../operations/dependency-migration-plan.md)。

返回[总入口](README.md)。本章专门区分建议、批准、执行和效果，防止“界面显示已批准”被误作“目标已隔离”。

## 1. 响应链的对象

```text
调查建议 / Playbook 步骤
→ 带目标和参数的请求
→ 权限、自治与影响范围决定
→ 必要的人工审批
→ 厂商执行尝试
→ 厂商回执
→ 条件性效果回读
→ Case/调查交付记录
```

上游不同入口实现的链长不同；不能拿一处 verifier 的存在为所有执行器背书。补偿/回滚是新的副作用，也不是修改原执行记录。

<a id="m09"></a>

## 2. Playbook：输入、触发与执行

源码：[alert_trigger.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/playbook/alert_trigger.py)、[store.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/playbook/store.py)、[engine.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/playbook/engine.py)、[action_bridge.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/playbook/action_bridge.py)。

| 项目 | 当前实现 |
| --- | --- |
| 输入 | 剧本定义、trigger event 与 tenant、severity、tags、title、verdict、confidence、实体上下文 |
| 匹配 | Store 根据事件与条件选择；当前告警事件名为 `alert`，不是任意猜测的 `alert.created` |
| 执行 | Engine 解释条件、步骤和引用；按 handler 调 enrich/investigate/notify/http/response/close 等具体功能 |
| 输出 | Playbook Run、step_results、状态、匹配/预览/执行摘要、错误与审批暂停 |
| 边界 | 引用、条件与循环边界由实现限制；有步骤类型不代表相应外部服务已经配置 |

三层实际动作控制需分别检查：

| 控制 | 配置 | 作用 |
| --- | --- | --- |
| 告警触发总开关 | `AISOC_ALERT_PLAYBOOKS_ENABLED` | 默认关闭；是否从告警路径匹配运行 |
| live 剧本允许列表 | `AISOC_ALERT_PLAYBOOKS_LIVE` | 未允许的匹配项执行 preview/dry-run；可以指定 tenant:playbook |
| 响应 bridge 执行开关 | `AISOC_PLAYBOOK_ACTIONS_EXECUTE` | 默认关闭；响应 handler 是否真正走执行 |

HTTP、通知等 handler 还有各自开关和目标限制。不能把一个总开关理解成所有外发、查询和响应都已授权或均为 dry-run。

### 暂停与恢复

[pause.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/playbook/pause.py) 与 engine 的 `resume_after_approval/resume_wait/resume_verification` 提供持久暂停/恢复逻辑；相关迁移包括 `081_playbook_pauses.sql`、wait 与 verification 的后续迁移。

审批暂停先创建可引用的 approval，再保存 pause；恢复时查 tenant/approval，先原子解决相应 pause，再继续。拒绝应停在可解释状态。暂停记录不是完整通用 Workflow checkpoint；没有据此验证所有重启、取消、并发和剧本变更恢复。

<a id="m10"></a>

## 3. API 审批模块

入口：[approvals.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/approvals.py)：`decide_approval`、`_dispatch_decision`。

输入：approval ID、approve/deny、comment 与认证 user。查询按 ID + tenant；同一已作决定的重复请求与相反决定分开处理。部分状态允许何种决定以实现为准，不能默认“过期一定不可批准”。

决定会调用 Actions 并将 dispatch 结果放入审批 action 字段，再提交数据库。返回结果区分：

| dispatch state | 含义 |
| --- | --- |
| `not_executable` | 缺 action_type/target 等，没有可执行动作；可用于纯人工步骤 |
| `declined` | 拒绝并将拒绝传递给执行侧 |
| `executed` | Actions 接受并执行了该请求；效果仍需看回读结果 |
| `failed` | Actions 拒绝或不可达；决定可已持久化，但动作未按预期完成，接口可返回 502 |

使用 approval ID 关联 action，便于回答“批准的是哪次执行”。但远程执行发生在本地 commit 前，仍存在外部副作用与本地事务不同步的边界。不能宣称分布式事务或 exactly-once。

## 4. Actions 两类接口

入口：[main.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/main.py) 同时挂载两类路由。

| 路径 | 输入模型 | 路由/能力 | 输出与特点 |
| --- | --- | --- | --- |
| ActionType 路径 | [ActionRequest](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/models/action.py) | `/api/v1/actions`；按动作枚举找执行器；提交、审批、拒绝、查询、ChatOps | 状态、影响范围、approval_tier、output/error；UI 审批主链使用 |
| Live 路径 | [LiveActionRequest](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/live_actions/models.py) | `/api/v1/live-actions` 发现能力、`/dispatch`、`/dry-run`；按 vendor+capability 找执行器 | `LiveActionResult` 和 mode；支持泛化能力与条件性效果验证 |

当前 [Live router](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/api/live_actions_router.py) 已配置 `Depends(require_service_auth)`，旧“Live 无服务认证”的分析已不适用。本地能访问端口也不应默认获得执行权限。

### ActionType 输入输出

输入含 `id/incident_id/tenant_id/action_type/target/parameters/principal/rationale/confidence` 等。`auto_rollback` 等字段的存在不证明当前路由自动调用回滚。

submit 执行 `authorize_action`、BlastRadiusGate、approval matrix；保存请求，再对允许自动执行的动作调用 executor，最后保存执行结果。审批路径绑定有权限、非申请人的 approver，并恢复原 parameters 后执行。默认是否要求审批人由对应配置决定。

存储入口：[action_store.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/services/action_store.py)。有 DSN 时写 `aisoc_action_records`；也保留进程内缓存/无库 fallback。**DB 连接或写入失败会记录降级，不是所有失败都阻止执行。** `_DB_CONFIRMED` 改变故障日志级别，并没有使存储自动变成 fail-closed。

此外，`get(action_id, tenant_id=None)` 允许不带 tenant 读取，而 submit/approve 等调用方需逐条检查作用域；不能因为存储支持 tenant 参数就认为所有路由已使用。针对目标产品，应从可信身份始终绑定 tenant，不用 UUID 难猜替代授权。

### Live 输入输出

请求含 `request_id/capability/vendor_id/target/params/auth_config/dry_run/confidence/case_id/playbook_run_id/playbook_step_id/tenant_id/requested_by`。凭据字段由服务端解析；模型输出和普通日志不应携带真实密钥。

ActionType 状态含 pending/awaiting_approval/approved/rejected/running/completed/failed/rolled_back；Live 使用 succeeded/failed/simulated/blocked/pending_approval/**awaiting_completion** 等。后者表示厂商已接收而效果未完成，不能映射成 succeeded，也不能与“尚未批准所以根本没执行”混淆。

dispatcher 顺序：参数/凭据转换 → 能力与策略门禁 → 选择执行器 → 可能强制 dry-run/阻止/待审批 → 调用 → 规范 request ID/vendor/capability 回显 → 条件性验证 → 结构结果。HTTP 200 可以包裹业务 `failed`，调用方必须读结果状态。

## 5. 效果验证和回滚

源码：[dispatcher.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/live_actions/dispatcher.py)、[verification.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/services/verification.py)、[rollback.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/services/rollback.py)。

当前 Live dispatcher 在 `decision.requires_verification`、非 dry-run 且执行结果成功时调用 `_verify_effect`。没有相应 ActionType/probe 的能力会明确标 `unverified`。不是所有动作、所有入口都无条件回读。

| 观测 | 可以陈述 | 不能陈述 |
| --- | --- | --- |
| Responder plan | 建议隔离/封禁 | 已提交执行 |
| Approval approved | 人工决定已记录 | 厂商接口成功 |
| Vendor accepted/succeeded | 接口接受/执行器报告成功 | 一定已达到预期效果 |
| Verification confirmed | 某次 probe 观测到目标状态 | 全域风险已消除 |
| Verification missing/failed | 效果未确认/验证失败 | 可以无条件重发有副作用动作 |

`reverse_action` 有逆操作实现，但本次没有证明通用自动回滚链或所有执行器逆操作均可用。移植需以新请求引用原 Action，重新检查权限、审批、before state 和验证；不能覆盖既有执行事实。

## 6. 厂商适配的二次开发清单

1. 明确 vendor/capability 的目标格式、允许参数、读写类型、影响范围与权限。
2. 通过服务端 credential_ref/连接器解析凭据；不从 Prompt 任意获取 URL 或密钥。
3. 区分 dry-run、simulation、实际执行；测试检查真实写接口调用次数为零或一，而不是只看返回文案。
4. 保存 operation ID、时间、输入 hash 和回执；超时后 unknown，先查证，不自动重发。
5. 选择可表达“效果已达到”的 read-back；设备存在不代表设备已隔离。
6. 如需补偿，定义逆操作资格和新审批，不把恢复原状当无风险。

## 7. 直接相关测试

| 测试 | 关注的实际断言 |
| --- | --- |
| `test_alert_triggered_playbooks.py` | 真实 trigger 名、总开关与 preview/live |
| `test_playbook_pause_resume.py` | 暂停关联 approval、批准继续、拒绝停止 |
| `test_playbook_action_bridge.py`、`test_playbook_bounds.py` | 动作开关、步骤执行与边界 |
| API `test_approval_dispatch.py` | 决定传给 Actions、结果如实保存与错误反馈 |
| Actions `test_approval_identity.py`、`test_approval_matrix.py` | 审批身份、权限、影响/置信度门禁 |
| `test_action_store_columns.py` | 状态/审批等级的实际列值 |
| `test_live_action_dispatcher.py`、`test_live_action_router_auth.py` | 路由、异常、ID 规范、dry-run、服务认证 |
| `test_verification.py`、`test_verification_coverage.py`、`test_rollback.py` | probe 与逆操作合同；不代表厂商真机结果 |

这些是现有测试源码；本轮没有跑真实响应。20 目前也没有真实资产隔离、账号停用或回滚的验收证据。

## 8. 采用决定的建议

保留建议与执行分离、审批身份和参数恢复、preview 默认、明确 dispatch 回执、效果验证与未知状态。对 stingAISOC，只选当前有真实业务用途的一种能力接入；高风险响应按目标需求执行人工审批，不照搬上游任意自治阈值。

不建议为兼容上游同时引入两套 Actions API、两套审批事实和所有 vendor executor。优先选一个请求合同，复用现有权限/Artifact/记录机制；统一门禁与调用事实属于功能正确性，复杂接管和全故障矩阵后置。
