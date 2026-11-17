# 既有调查执行约束核对：后续调度参考

2026-11-14。按负责人要求，将此前误放在阶段一交接说明中的启动、领取及读取设计反馈移至流式change。本文保留当时的仓库代码/DDL核对及建议，供后续设计取舍参考，不代表目标合同已确认或程序已改动；最终规则以本change最新正式设计为准。不新增实施任务，不改变阶段一“本地验收完成，待统一发布”的收口状态，也不构成阶段一发布或关闭条件。

### 1. Case pending、领取冻结与幂等

当前pending Run承担待执行身份及可更新成员范围。[case_service.py](../../../services/api/app/socai2/case_service.py)的`create_case`（54行）通过关联成员取得pending Run，`prepare_baseline`（114行）复用或建立pending；[baseline_store.py](../../../services/api/app/socai2/baseline_store.py)的`replace_members`（146行起）随范围变化刷新它。它们尚未冻结完整分析输入，也不执行模型。

`Store.claim`（baseline_store.py 213行）先锁Case和Run，检查状态、scope_revision及幂等意图；243行起读取领取时最新材料，保存上下文、配置及输入快照，并在同一事务冻结成员来源后转running。[baseline_service.py](../../../services/api/app/socai2/baseline_service.py)的`start`（41行）提交冻结事务后，仅在`newly_claimed=True`时调用执行器；同一Run/操作键重放返回旧领取结果，不重新冻结或执行。

复用pending可以保留既有Run身份，但仍须在领取时冻结最新材料。领取时才建Run也可设计为内部一次事务，先插入pending、写入成员及快照、再claim；外部不必看到这个中间状态。该方案须同时调整建案、成员变更、prepare这几个提前建立pending的入口，不能留下旧pending再插入第二个，也不能直接插入running baseline。队列请求的幂等与执行尝试的幂等须区分：重放旧执行键不会产生重试；新的尝试需独立执行身份并保留原失败。排队等待不应消耗实际执行时才生成的Run时限。

| 当前硬约束 | 迁移/代码位置 | 对后续领取与结束设计的影响 |
| --- | --- | --- |
| `runs_pending_baseline` | [迁移123](../../../services/api/migrations/123_socai2_page_data_model.sql)2311行 | pending阶段的started_at、ended_at、input_artifact_id、operation_key、request_hash必须为空；请求排队身份不能直接塞进这些执行字段 |
| `runs_one_pending_baseline` | 迁移123 3933行；[V1建表原件](../../../deploy/database/init_socai2_v1.sql)4312行 | 同租户/Case最多一个pending baseline |
| `guard_run`及成员冻结 | 迁移123 4037行；4045行禁止baseline直接以running插入；4061行冻结已领取输入；4068行核当前完整Case范围；4103/4132行约束成员修改及同事务发布 | 新建pending、成员/输入冻结、claim应在一次内部领取事务完成；V1原件对应4416、4482、4511行 |
| `runs_one_active_baseline` | 迁移123 3935行；V1建表原件4314行 | `running`和`unknown`均占用同Case唯一执行槽，与是否已有本地执行进程无关 |
| `runs_end_fields` | 迁移123 2323行；V1建表原件2702行 | 只有completed/failed/cancelled且必须有ended_at；当前unknown不能写ended_at，不能仅补结束时间来表达“已结束unknown” |
| 领取检查及异常保存 | baseline_store.py 229行、529行；baseline_service.py 51行起；[stage_results.py](../../../services/api/app/socai2/stage_results.py)324行 | Case领取拒绝已有running/unknown；Case异常保存unknown，A/I的unknown显式保持ended_at为空 |
| 结案检查 | [case_management.py](../../../services/api/app/socai2/case_management.py)14行、64行 | running/unknown均阻止结案；释放策略须与领取及数据库约束一致 |

若按最新目标将调用超时收尾为本次执行失败、保留结果未知事实，需统一Run终态与业务未知的表示，并核对以上检查；若另选“unknown带结束时间”，则现有时间约束也需调整。具体终态/字段由规划侧定稿，本轮不代选、不改旧unknown。后续确需DDL变更时走增量迁移，保留迁移123及V1建表原件。

A/I与Case不能机械套用同一路径：`StageResultService.begin`（stage_results.py 132行）按tenant+operation_key生成Run身份，读取当前输入并直接插入running，已有键则返回`newly_claimed=False`。[alert_basic_executor.py](../../../services/api/app/socai2/alert_basic_executor.py)57行及[incident_diagnosis_executor.py](../../../services/api/app/socai2/incident_diagnosis_executor.py)68行会据此直接返回。因此不能先替它建立Run，再原样调用execute并期待继续执行；现有A/I begin也不能替代统一调度的同主体执行串行约束。

### 2. 内部用例与外部HTTP

`CaseService.start_case`（102行）和`StageResultService.execute_alert/execute_incident`（314/319行）是可由内部服务调用的执行入口。当前外部HTTP通过[ports.py](../../../services/api/investigation_http/ports.py)的`CaseOperations`、`StageExecution`及[adapters/services.py](../../../services/api/investigation_http/adapters/services.py)接入；未来worker直接调用调查核心，不反向依赖外部HTTP包。`Store.claim`、`StageResultService.begin/finish`、`start_full`以及C1–C6/Deep内部阶段、模型/湖客户端和预算注入均不应变成外部路由。已确认的告警自动分诊不需要保留对外手动启动；异步受理由接口及规划侧形成统一合同，不把调度器装入每个API进程。

### 3. Run、Result和原件读取

现有追溯链足以读取阶段一已验流程：Case `Result.source_run_id → Run`，Run的input、步骤input/output、工件run_id/step_id/source_refs连接冻结材料、请求、原答、派生和最终报告；C3初答/补答/合并及field_origins分别保存。A/I结果按subject+source_run_id读取，不能当成Case Result表。`source_refs`按artifact、alert_material、task_revision、result等类型读取，不能全部按工件路由或用latest替换历史。

后端应先跟踪Run，再读取其实际Result/原件；failed、unknown或无结果Run仍可查，不能只等Result或拿当前采用判断代替本次结果。[case_reader.py](../../../services/api/app/socai2/case_reader.py)283/338/384/432行分别为历史、Run、原件、Result；[stage_reader.py](../../../services/api/app/socai2/stage_reader.py)52行为A/I结果入口；[page_reader.py](../../../services/api/app/socai2/page_reader.py)346/367行为trace/原件读取。

读取边界仍需明示：Run/trace目录最多返回1000步骤、200工件，提供truncated标志但没有该目录的分页；单个已知ID原件可完整读回，外部blob仍标未加载。若业务要求枚举超出上限的全部目录，需要接口侧明确分页合同，不能把阶段一大原件读取通过当成任意目录全量能力。未来异步请求的受理/等待/重试状态及request→多次Run关系尚不由现有Run读取提供；这部分随请求/尝试关联设计定稿，内部pending队列无需向前后端暴露。

### 4. 人工操作与正在执行的输入

[human_task_service.py](../../../services/api/app/socai2/human_task_service.py)81行写新任务修订并更新当前指针；[subject_management.py](../../../services/api/app/socai2/subject_management.py)31行的人工反馈另存assessment并更新latest_feedback_id，均不覆盖旧模型结论或已冻结输入。领取时由[baseline_context.py](../../../services/api/app/socai2/baseline_context.py)198行捕获当时版本，可用完成反馈标human_statement，执行回执及历史判断保持各自角色。运行中新增材料/反馈影响新鲜度和后续一轮，不替换本轮冻结版本。

[case_adoption.py](../../../services/api/app/socai2/case_adoption.py)107行重新检查采用预览令牌/条件，创建判断历史并变更当前指针，不修改Result、Run或触发执行；[迁移125](../../../services/api/migrations/125_socai2_baseline_input_freshness.sql)101/106行分别检查输入新鲜度和Run启动后形成的新判断，防止旧Run自动覆盖较新的采用。结案/重开目前只处理业务状态，不启动调查；结案的unknown阻塞规则见上表，后续与新调度目标统一。

完整后台快照不等于模型输入。A/I/Case继续经各自[alert_model_boundary.py](../../../services/api/app/socai2/alert_model_boundary.py)、[incident_model_boundary.py](../../../services/api/app/socai2/incident_model_boundary.py)、[case_model_boundary.py](../../../services/api/app/socai2/case_model_boundary.py)筛选业务视图；队列对象、Run/数据库DTO、执行台账不能整包透传模型。原核对仅形成设计反馈，未修改业务代码、路由、DDL、运行配置或任务勾选，未调用模型或写业务数据。
