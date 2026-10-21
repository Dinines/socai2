# 03 告警运营、Case 与结果交付（M03 / M11 / M12）

> 用途：固定上游源码与历史证据分析（2026-10-20对齐）。本轮只迁队列、Case和交付的服务端数据能力，不建设工作台、页面或独立Realtime展示服务。 当前职责见[范围](../operations/alert-processing-scope.md)，阶段退出见[路线](../operations/service-roadmap.md)，执行批次见[依赖计划](../operations/dependency-migration-plan.md)。

返回[总入口](README.md)。本章关注分析员实际工作入口，而不是只列后端服务。

<a id="m03"></a>

## 1. 告警运营模块

入口：[alerts.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/api/v1/endpoints/alerts.py)、[alert_queue.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/services/alert_queue.py)、[Alert ORM](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/models/alert.py)。公开 API 还需叠加主路由的 `/api/v1` 前缀。

| 操作 | 代表路由 | 输入与主要行为 | 输出/副作用 |
| --- | --- | --- | --- |
| 查询 | `GET /alerts`、`GET /alerts/{alert_id}` | 用户身份、租户、筛选、分页；从存储读取 | 告警与详情、来源、实体、AI 信息 |
| 统计/工作队列 | `GET /alerts/stats`、`GET /alerts/queue` | 当前用户、状态、时间范围、SLA 配置 | 统计、队列项和待办顺序 |
| 人工更新 | `PATCH /alerts/{alert_id}` | 状态/字段更新与权限检查 | 新状态、相应时间和审计行为 |
| 升级/认领 | `POST /alerts/{alert_id}/escalate`、`/claim` | 告警 ID 与分析员操作 | 运营状态/归属改变；不是完整调查完成 |
| 暂缓/批量关闭 | `POST /alerts/{alert_id}/snooze`、`POST /alerts/bulk-close` | 截止时间或告警集合及关闭信息 | 暂缓/关闭结果；须检查部分拒绝与租户 |

Alert ORM 与 Fusion 枚举并不一致。API 模型、路由允许值、数据库历史值要一起核对，不能拿 Fusion 的 `AlertStatus` 当全平台状态机。

### 队列规则

队列优先显示分派给当前用户的未关闭告警，再显示未分派 critical/high；各组按 SLA 紧迫程度排序。未分派 medium/low/info 不在这个队列里，仍可从普通告警列表批量处理。虚拟 SLA 基于 `first_seen + severity target` 计算，并非每条告警固定写死的 deadline。

退出队列状态包含 `resolved/closed/false_positive/fp`。二次开发改变状态词汇时，应同时修改队列、列表统计、批量操作和 UI，避免已经关闭的对象仍显示为待办。

<a id="m11"></a>

## 2. Case 模块的职责与数据

入口：[cases.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/api/v1/endpoints/cases.py)、[Case ORM](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/models/case.py)、[case_orchestration.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/services/case_orchestration.py)。

| 输入 | 功能 | 中间/最终产物 |
| --- | --- | --- |
| 标题、严重度、负责人、关联告警 | 创建和维护分析员工作项 | `aisoc_cases`、case number、归属、状态 |
| Alert IDs | 关联告警和 Case | Case 告警集合及 Alert 的 Case 关系；读取时仍需租户约束 |
| 评论、observables、任务、证据 | 协作和调查材料整理 | 评论、任务、可观察实体、证据和时间线 |
| 队列匹配规则、SLA policy | 决定队列与响应/解决/关闭期限、升级判断 | queue 选择、多个 SLA 时钟、升级结论 |
| 分析员发起调查 | 加载关联告警、构造上下文、代理 Agents | 新 run_id、进行中状态，后续调查结果 |
| 结案/重开请求 | 校验状态转换、保留结案依据和重新开启原因 | Case 状态、时间、关联告警变化及后续反馈 |

当前 ORM 使用 `aisoc_cases`；不要从旧文档或同名历史表推断写入位置。迁移 `083_one_case_table.sql` 也提示历史上存在过 Case 表分裂问题。单个 ORM 文件不是完整数据库 schema。

### 状态转换

`update_case` 先规范化请求状态，再按 `_TRANSITIONS` 检查；非法转换返回 422。向后移动需通过显式 `/reopen`。本分析不把注释中的状态列表当唯一有效合同，准确允许值以该版本函数与迁移约束为准。

当前 [case_status.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/services/case_status.py) 的正常状态机是 `new → triaged → investigating → contained → resolved → closed`，其中 investigating 也可以直接到 resolved。只有 closed 属于终态；resolved 仍是尚未最终关闭的工作项。直接发起调查的专用前进逻辑与普通 PATCH 允许边不同，修改时要一起核对。

修改状态时需要同时检查：Case 时间戳、关联 Alert、队列和统计、结案摘要/记忆以及重开后的历史保留。不要让一个 UI 标签同时承担调查执行状态与 Case 生命周期。

## 3. 从 Case 发起调查的真实材料链

`POST /cases/{case_id}/investigate` 的重要步骤：

1. 按认证 tenant 解析 Case；载入关联 Alert，而不是完全相信调用方自带的摘要。
2. 选择最多 3 条关联告警，按事件时间倒序；描述最多 1,000 字符，原 `full_log` 最多 4,000 字符，实体列表最多 20 项，组成 `raw_alert={"alerts":[...]}`。
3. 对较早阶段的 Case/Alert 尝试向前推进至 `investigating`，不把已解决对象拉回；这些更新与远程调查启动不是一个事务。
4. 调用 Agents 的同名入口，传真实 tenant，附 `X-AiSOC-Tenant-ID` 服务作用域。
5. 返回远程启动结果。后续查询、报告和持久回放分别从相应读取入口获取。

**采用注意：** 摘要裁剪有助于控制模型输入，但会丢掉事件和字段。移植时应保留完整原材料引用、实际展示范围及截断说明；不能只给模型三条文本，却宣称分析覆盖全部 Case。Case 已显示 `investigating` 也不证明远端 Run 已成功创建。

<a id="m12"></a>

## 4. 运行状态、持久记录与报告是不同读取面

| 读取面 | 入口 | 实际用途/边界 |
| --- | --- | --- |
| Agents 运行缓存 | [api/investigate.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/agents/app/api/investigate.py) 的 `_runs` | 轮询当前进度、结构结果、报告；内存内容不能单独承担持久恢复 |
| 调查账本 API | [investigations.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/api/v1/endpoints/investigations.py) | 从持久 Run/Events/Artifacts 查询、回放、时间线、解释和证据包 |
| Case 代理接口 | `cases.py` 的 investigations/report 相关路由 | 在 Case 关系和认证范围内获取结果，部分路径具有持久查询 fallback |
| Realtime | [index.ts](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/realtime/src/index.ts) | 分租户转发融合事件和调查进度；不是数据库权威状态 |
| 报告导出 | Agents report.md/html/pdf；API summary/bundle | 面向分析员和审计的交付物；格式成功不等于结论正确 |

`GET /investigations/{run_id}/replay` 回放已记录事件，不表示重新执行模型、工具或厂商动作。运行缓存和持久账本可能处于不同阶段，读取与展示应表达状态来源。

## 5. 结案与反馈

Case 结案、Investigation close 和 Alert disposition 是不同操作。调查完成只表示本次执行终止，不能自动等同威胁已消除或案件已关闭。

反馈相关入口：[feedback.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/api/v1/endpoints/feedback.py)、[semantic_memory.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/services/semantic_memory.py)、[memory/manager.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/agents/app/memory/manager.py)。

- 人工处置可成为历史 disposition、组织记忆或其他 prior 的来源；需保留谁在何时给出哪一种判断。
- `remember_closed_case` 有结案记忆的写入/索引实现，数据库记录与 embedding 状态需分开检查。
- 人工修正、自动分诊和模型推断的可信度不应混为一谈；自动关闭再写入 prior 的循环尤其需要明确产品策略。
- 上游按 key 更新的记忆不能替代 stingAISOC 对不可变反馈事实、冻结结果和证据引用的要求。

## 6. 证据与实时交付

[evidence_bundle.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/services/evidence_bundle.py) 构造规范序列化的证据包、摘要和 HMAC-SHA256 校验；[evidence_custody.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/api/app/services/evidence_custody.py) 提供 custody 链相关逻辑。HMAC 是共享密钥防篡改校验，不应描述成公钥不可否认签名。本文未独立核验导出包所声明标准版本的全部外部规范。

证据包默认让 prompt 以 hash 形式出包，受控原件和外部导出是不同访问面。校验 hash 只能说明内容是否一致，不能证明输入事实真实或模型结论正确。

Realtime 独立消费融合 topic，按事件 tenant 分发；调查 API 还会向内部 agent-event 入口发送进度。服务健康不等于 WebSocket 认证、跨租户隔离、重连和最终状态展示都已实测。

## 7. 测试与移植入口

| 场景输入 | 应检查的中间结果 | 应检查的最终行为 | 相关测试源码 |
| --- | --- | --- | --- |
| 我的告警、未分派高/低危、已关闭告警 | 筛选后的 ID 集合、SLA 排序 | 队列只含应处理项目，顺序与规则一致 | `test_alert_queue.py` |
| 同时匹配多个 Case 队列/SLA | precedence、匹配条件、创建时间 | 队列确定；期限不因重读而延后 | `test_case_orchestration.py` |
| Case 关联多条 Alert 后启动调查 | 传给 Agents 的 tenant、材料和裁剪 | 原始材料实际进入 Run；非只传标题 | `test_investigation_payload.py` |
| Run 已写账本、运行缓存不存在 | PG 查询结果、Case/tenant 关系 | 可读取允许的历史；不能跨 Case/tenant 获取 | `test_investigation_replay.py` |
| 导出、修改字节、再次校验 | canonical payload、签名/hash | 相同输入稳定；改动被检测 | `test_evidence_bundle.py`、`test_evidence_custody.py` |

建议复用工作台职责拆分、来源追踪、前向状态规则和证据包思想；重新对接 stingAISOC 的身份、授权、Result 冻结与 Artifact 体系。不要整体复制 Case 大路由和所有历史迁移；先限定一个分析员入口到结果交付的纵向场景。
