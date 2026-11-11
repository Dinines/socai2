## Context

`socai2_cases.get_service` 和 `socai2_tasks.get_service` 当前总是构造基于 `app.db.database.AsyncSessionLocal` 的服务。正式环境该连接用于认证和调查只读查询。`CaseService.start_case` 已读取服务端策略并等待现有 `start_full` 执行器；`HumanTaskService.write` 已保存不可变修订，保存反馈不会自动启动调查。

既有处理 profile 已生成具备所需读写能力的 `DATABASE_URL`，并保护租户和不可变原件；本次复用该连接，不更改 V1 表列或原角色权限。当前 API 读取账号及其他服务连接保持原职责。

## Decisions

1. 增加私密运行配置 `SOCAI2_CASE_DATABASE_URL`，仅 Case/H 非 GET 路径选择该连接。复用当前 PostgreSQL URL/TLS 处理和已有连接池配置，按需建立一个进程内会话工厂，应用结束时释放。没有配置返回明确 503；GET 不依赖写入配置。HTTP 写开关仍由明确 profile 启用。
2. 发布入口对允许的 API 环境键支持显式来源映射，将受控处理 `DATABASE_URL` 映射为上述 Case 配置，不能覆盖通用 `DATABASE_URL`，不复制整份私密环境。同时传入该 profile 的四项可选来源开关和 SOCAI2_LAKE_DATABASE，避免 HTTP 路径静默使用缺省关闭值；API 已有湖连接目标同为 aisoc，保持其原连接。新装/升级说明、配置示例及实际发布清单同步。
3. 继续使用现有建案、prepare/start、任务 create/edit 和 GET 路径，不新建并行编排。鉴权提供的 actor/tenant、operation_key、scope_revision、row_version、冻结版本、unknown/失败和现有限额全部沿用。
4. 本地 HTTP 完整路径使用实际 PostgreSQL、实际服务/执行器/存储；真实模型沿既有内网传输。若本地认证或网关传输使用适配器，明确其范围，不声称完整登录或厂商实连验收。人工正文注明材料核查/测试用途，不能代造业务授权。
5. 直接核反馈的所选版本、原文及 human_statement 来源进入后轮输入，结果保存与读取一致。模型是否正确理解另按原答记录；已知正文问题不触发反复采样，F01 质量未完范围保持。程序错误导致不能保存、读取或冻结正确版本则先修正。
6. 负责人再次明确当前放开功能读写，不做权限专项或复杂处理。本次直接复用已有连接与接口，不新增角色、审批、GRANT 或权限框架。发布后在独立验收 Case 中创建和修订一项人工任务，原 Case 只读，避免人工补充使原调查输入过期；该验收 Case 的初始 Run 保持待启动，不增加生产模型调用。

## Validation and delivery

- 小量直接检查覆盖 GET/写入连接选择、缺配置及关闭开关、私密环境映射；复用既有 H 版本/操作键合同，不重跑全仓或权限/可用性矩阵。
- 一条本地实际 HTTP 闭环覆盖两次调查及其间一次人工任务完成/修订；仅检查该路径数据与关联，同一证据用于模型、保存、读取和 4177。
- 独立结束审查后统一发布一次。发布后核实际开关、连接身份/数据库及 profile，使用一项明确标注的验收人工任务写入/修订/读取核对接线，不默认追加生产模型调用或重发历史 Run。
- 回退为原发布配置/镜像，已有 Case/H 数据与模型原答保留；不得清库。旧 r1 作为发布前来源，其他五个服务和自动消费者保持。
