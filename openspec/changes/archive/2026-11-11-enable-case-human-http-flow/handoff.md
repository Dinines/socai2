# Case 与人工反馈操作交接

本 change 接通已有 HTTP 操作和数据库连接，不增加表、列、枚举或 DTO，不修改告警交接合同。生产开放状态以根交接指南和发布回执为准。

## 调用顺序

以下路径以 `/api/v1/socai2` 为前缀，actor/tenant 取已有登录上下文。

| 操作 | 请求与读取关系 |
| --- | --- |
| 建案 | `POST /cases` 提交 `operation_key,title,alert_ids` 等原字段；保存 `cases/case_alerts` 并返回 `case_id,scope_revision,pending_run_id` |
| 首轮调查 | `POST /cases/{case_id}/runs/{run_id}/start` 提交新的 `operation_key,expected_scope_revision,window_start,window_end`；等待现有 C1–C6，沿 Run/Result GET 读取实际状态和结果 |
| 人工完成 | `POST /cases/{case_id}/tasks` 提交 `state=completed,result_text,result_scope` 和操作键/范围版本；返回 `task.id,current_revision_id,row_version,current` |
| 人工修订 | `PUT /cases/{case_id}/tasks/{task_id}` 提交完整任务字段和 `expected_row_version`；追加 `task_revisions`，`tasks.current_revision_id` 指向本次保存版本，原版本保留 |
| 后轮调查 | 显式 `POST /cases/{case_id}/baseline/prepare`，使用返回的 `pending_run_id` 调用 start；保存人工反馈本身不会自动发起调查 |
| 核版本与结果 | `GET /cases/{case_id}/tasks/{task_id}` 及 `/revisions`；`GET /cases/{case_id}/runs/{run_id}`、`/results/{result_id}`；不要将界面草稿当已保存版本 |

每轮 C1 从适用的已完成人工任务选中修订，冻结在输入工件的 `task_revisions` 以及 `source_materials` 引用中。来源角色是 `human_statement`，正文及范围来自该不可变修订。后续任务修订不覆盖历史 Run 的输入或结果；人工核查不代表业务授权，模型是否正确利用反馈仍由原答判断。

前端分别表达 `run.state`、`delivery_state`、Result 的 `validation_state/conclusion_state` 和当前采用状态。本轮局部传递成立不核销 F01 的语义质量、产品页面 P01–P04、真实非空知识或自动消费。

## 运行配置

`SOCAI2_CASE_API_ENABLED=true` 与私密 `SOCAI2_CASE_DATABASE_URL` 接通 Case/H 写操作；GET 和普通 API 仍用已有 `DATABASE_URL`。配置缺失时返回 `case_write_database_not_configured`，不会猜另一连接。参考 [配置示例](../../../../deploy/aisoc21/case-http.env.example)。沿用已有预算和原业务合同，不新增权限设计。

21 发布清单通过 `processing.api_environment_sources` 将现有处理连接 `DATABASE_URL` 映射到 Case 键；同批传入四项 SOCAI2_SOURCE_*_ENABLED 与 SOCAI2_LAKE_DATABASE，保持显式来源选择；API 已有湖连接继续使用原配置。受控私密文件承接凭据，仓库只保存键与来源关系。新装时在已有数据库安装和处理 profile 配置完成后生成这些键；升级复用原身份和数据，无额外迁移或 GRANT。API 应用结束时关闭新增连接池。

本次只更新 API 镜像，处理镜像复用 `processing-20261111-r1`；其余服务、模型策略与额度保持。发布后用正常登录在独立验收 Case 保存并修订人工任务，读回原/当前版本；不启动生产调查。
