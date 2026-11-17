# R1统一分析记录HTTP：本地验收

2026-11-14，属于`schedule-streaming-investigation-updates`任务2.7的R1一步。新增`GET /api/v1/socai2/analysis-runs`，由独立HTTP端口调用只读用例，使用调查侧已提供的真实任务/尝试关联；未修改任务执行、调度、模型或数据库迁移。

## 实际结果

- [pg-03.json](pg-03.json)：本机隔离PostgreSQL `v12_upgrade_dev`，新UUID共11个Run。8个历史合成Run验证混合目录、时间边界、失败/unknown/无结果、历史task/intent为null；另外3个Run由真实核心任务受理、start_attempt、保存输入、bind_run和finish_attempt产生。没有调用模型或取证工具。
- 3个任务中，initial任务有两次尝试（失败重试、unknown），rerun任务有一轮完成，check任务仍accepted且无Run。HTTP正确返回前三个Run及真实任务ID/意图，未造check目录行；unknown保留空结束时间。
- 32次ASGI请求包含23次新R1（分页、筛选、空集、422、503）及9次已有Run/结果URL读回；503是显式依赖替身，只验证HTTP错误表达，不冒充数据库故障测试。其余正常查询使用真实PG提供方。另10次基础用例读取通过。
- 分页及intent作用于同一完整统计范围；多个结果版本、Case多路径关联不放大Run数。当前成员2而冻结输入1时返回1，保存的空输入数组为0，未知数量为null。
- 15类测试记录完整行内容摘要在GET前后一致，含真实任务/尝试/主体状态。合成数据保留，不清表、不改旧批次。
- 5项HTTP边界与可信接入检查、目标Ruff和OpenSpec strict通过。新接口字段说明和125项功能映射已核对；[检查与源码摘要](checks.json)、[候选OpenAPI](candidate-openapi.json)、[实际输入输出示例](examples.json)。

PG命令为`.local/conda-envs/socai2/bin/python .local/v1.2-reader-validation/run_pg.py test_socai2_run_directory_pg docs/operations/evidence/run-directory-http-20261114-01/pg-03.json run_directory_http`。HTTP检查为`test_socai2_http_boundary.py`及`test_socai2_trusted_http.py`，使用本机私密测试环境文件，不把凭据写入证据。

## 失败及边界

[首次执行记录](pg-01-runner-failure.json)：测试返回False后，runner因证据目录尚未存在而未能写出详细回执；详细测试trace未返回，不能补造。保留这一失败，不将该轮称为通过。[pg-02.json](pg-02.json)记录测试误把核心submit回执当成原始task取`id`而失败；改用回执`task_id`后，以新的UUID批次通过pg-03。没有回填或改写旧失败数据。

本批是ASGI加真实隔离数据库，不是正式服务TCP验收；runner通用标记`model_and_lake=explicit_substitutes`不表示本批使用了模型替身产生结论，本批实际模型和工具调用数均为0。测试核心策略仅将重试等待设为0，未改变运行配置或自动消费。

正式本地/21服务和静态Swagger仍71操作；本地候选包含R1/R3共75操作。需在整个change统一发布时应用配套迁移128/ORM、显式读取配置及可信上下文，并核对实际版本/读回。本批未部署、重启、提交或推送；任务详情、异步调度、整个2.7及change仍未完成。
