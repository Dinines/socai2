# 统一分析调度运行入口

2026-11-15，第2步已完成[隔离PG/Redis本地验证](evidence/analysis-dispatch-20261114-01/README.md)。生产消费者未启用，A/I/Case真实业务适配器仍分别在第3、4、6步接入；此文不是已上线回执。

## 配置和启动

配置从[禁用示例](../../deploy/local-investigation/analysis-dispatch.example.json)复制到受控私密路径，显式指定租户、数据库/Redis URL文件、生命周期策略、执行器工厂及其配置。URL文件保存连接串和凭据，不写日志或Git。代码不回落到另一环境，不从HTTP worker启动调度。

```sh
PYTHONPATH=services/api python -m app.socai2.analysis_dispatch_runtime --profile /absolute/private/analysis-dispatch.json
```

默认`enabled=false`，只校验配置并退出，不读取连接凭据或连接服务。启用必须有明确的`executor_factory=module:factory`。工厂接收`(显式JSON配置, task_service)`，复用所选数据库会话，返回`kind -> executor`映射。第3步已提供真实A工厂`app.socai2.analysis_alert_executor:executors`，见[A示例](../../deploy/local-investigation/analysis-alert-dispatch.example.json)和[入站运行说明](analysis-alert-ingress.md)。第4步新增联合A/I工厂`app.socai2.analysis_incident_executor:executors`及同循环事件检查，见[事件运行说明](analysis-incident-diagnosis.md)；Case/知识工厂尚未接入。未注册种类保留已受理任务，并报告`unconfigured_executor`，不伪造完成。

| 配置 | 默认示例及作用 |
| --- | --- |
| dispatch.max_running_tasks | 1；可设3、5等正整数，控制本进程所有种类的活动句柄总数 |
| dispatch.poll_interval_seconds | 60；收尾/补投/领取的轮询，与4小时/6小时材料检查及60秒重试分别配置 |
| dispatch.execution_timeout_seconds | 3600；本地适配器外层时限，取消必须实际结束后才释放；模型/工具仍沿自己的策略 |
| dispatch.priorities | Case、告警、事件、知识；同级FIFO，不承诺持续高负载下公平性 |
| dispatch.replenish_limit | 每轮最多补投100条持久待办；不是pending扫描额度，pending按开始长度扫描 |
| dispatch.namespace / tenant_id | Redis部署命名空间和本实例唯一租户，队列值只放task UUID |
| dispatch.receipt_directory / lock_file | 受控持久目录及唯一实例进程锁；升级保留目录/路径 |
| database_connect_args / database_pool_size、Redis超时 | 均在文件中指定，示例含连接/SQL/锁等待时限；部署时选择实际TLS及角色 |

运行部署只允许**一个领取进程/一个实例**，全部种类共享N。独立HTTP及其他生产者只持久受理任务；可追加UUID，未追加者由调度补投。不能通过多开租户profile、独立容器或不同锁路径获得另一个N。本期不做跨主机分布式领取；替换实例先结束旧进程，再用同一租户、命名空间、持久目录及锁路径启动。入口使用OS进程锁拒绝同路径重复启动，不能以Python GIL充当多实例保护。

新装/升级均先应用128，再合并[生命周期发布片段](../../deploy/local-investigation/analysis-lifecycle-release-fragment.json)和[调度发布片段](../../deploy/local-investigation/analysis-dispatch-release-fragment.json)至统一发布清单。当前片段保持待发布/不激活；真实适配器闭环、整体交接和结束审计完成后按统一授权发布，不逐步启动消费者。

## 核心适配边界

- `load(task) -> Material(digest, value, capacity_changed=False)`：读取最新业务材料，按业务规则生成摘要及本轮固定视图；仅准备，不调用模型。摘要构造和真实A/I/Case材料筛选由对应步骤实现，队列不整包序列化原始记录。
- 普通initial/check与上次实际完成输入比较，无变化只保存skipped，不造attempt或Run；显式rerun保持独立意图。同材料停止标记约束自动重复尝试。
- 首次准备失败尚未得到摘要时，持续读取失败只跳过，不重复创建失败尝试；以后能构造材料后按实际摘要判断，不能把未知摘要当作所有未来材料。
- `execute(context, material) -> Outcome`：取得真实attempt，使用`context.operation_key`（同task每次尝试不同）创建新Run；在任何分析/工具调用前保存本轮范围、完整输入和配置，并绑定attempt。运行中新材料不得修改该快照。实际业务执行器继续保存模块IO、原答及局部结果。
- 业务适配器正常交付时先保存Run/结果，再返回completed；未知如实保存。返回错误只用固定短码/阶段/脱敏明细。单独HTTP 5xx不能证明未执行；适配器有明确未执行或已失败事实时才用`ExecutionFailure`声明临时可重试。读取响应超时不自动重试。
- 执行协程不读写Redis、不领取下一任务。PG事务不跨模型调用；Redis索引只是提示，受理和原task_id查询都以PG记录为准。

## 收尾与状态读取

每tick先收尾，再补投持久待办；pending优先但最多检查开始时条数，之后进入普通队列。活动字典决定N和主体串行，Redis running Hash/Set为镜像。等待不占槽、不增加次数。

本地执行真正结束后保存小型脱敏完成回执，释放活动占用和Redis镜像，写回PG。若PG补写失败，保留文件及内存回执，下tick只重写同一次完成记录；同主体等待补写，其他主体继续。日志`analysis_completion_persistence_unconfirmed`和调度状态`completion_writes_unconfirmed`说明未确认，公共GET保持最后真实PG状态，不提前宣称成功；不向HTTP增加pending或文件回执字段。

Redis不可用则停止新领取，已结束调用仍独立写回PG；恢复后补投待办。启动先重放已有完成回执，其余本租户遗留running attempt记interrupted及发现时间，不编造local_ended_at；原running Run转unknown，已存unknown保留NULL ended_at。之后清本命名空间运行提示并补投，不清全库，不要求人工解除队列。此处理不构成自动故障转移或通用恢复平台。

第2步通用队列验证使用可控执行器、时间和故障注入。第3步A接线已另做真实PG/Redis、现有A执行器及一条真实模型验证，见[独立回执](evidence/analysis-alert-auto-20261115-01/README.md)。这不证明生产消费者已上线；I/Case、厂商HTTP和持续负载未由上述证据覆盖。
