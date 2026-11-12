# 设计

- 新增E44 GET管理视图、E45 PATCH管理、E46 POST结案、E47 POST重开，保持E01–E43路径和输入输出。GET提供Case原字段、未完任务数、阻塞Run及结案/重开资格，便于调用方先提示再提交。
- PATCH需要operation_key、expected_row_version及至少一个修改字段；省略保持，description/owner_id/severity可null清空，tags=[]清空；title/tags/handling_status不可null或空白。状态只允许new/in_progress，已结案案件的状态必须用重开接口；负责人设置不自动改状态。owner_id校验现有同租户用户；写人工等级来源，清空等级也清空来源。
- 结案要求当前非resolved，无case级running/unknown（含所有kind）；pending_update不是活跃执行并保留原状。请求有未完任务时必须acknowledge_open_tasks=true且reason非空；无未完任务不强加理由必填。已结案重复新请求返回409，同operation_key同意图重放沿用原回执。
- 重开只允许resolved，设in_progress及reopened_at，清空当前resolved_at/by/note；旧结案说明保留在活动前后值及回执。reason可选，不新增人工确认门。两操作均不修改成员、判断、任务、历史或Run，不调用模型。
- Case行锁串行化管理、任务修改和Run领取。锁后检查row_version和当前未完任务/活跃Run；receipt先于版本检查实现幂等。管理PATCH的哈希只含显式字段，区分省略与null。变化才递增row_version/business_updated_at，无变化也保留幂等活动回执。
- 写活动包含请求hash、actor、理由和前后Case字段，使用既有activity.v1，不新增表列。tenant/actor来自原认证；普通功能读写接线沿用已启用开关/连接。
- 21基于当前独立镜像覆盖本项三文件，保留原主API/旧隔离API。发布工具适配当前容器替换和期望操作数配置，profile显式指定。先本机真实TCP+隔离PG、必要冲突/门槛检查，独审后发布并在新验收Case复验。
