# 异步提交受理层准备验收

2026-11-14。调查规划聊天明确第2步调度尚在实现，无I/Case真实队列业务handler。稳定方法为AnalysisTaskService.submit，PG受理成功返回原任务，未来调度补投；I/Case handler分别在原步骤4、6接入。本批属于HTTP目标合同8.15，不是异步执行交付。

实现两个未注册路由的DTO、端口和核心适配。业务上下文从可信配置获得，不需要登录/Token/权限；来源固定user。HTTP不访问Redis、不创建attempt/Run、不调用旧执行器。

[pg-01.json](pg-01.json)首次即通过：独立测试ASGI应用加真实本机隔离PG `v12_upgrade_dev`，26次请求（5×202、3×200、6×409、1×404、10×422、1×503），创建两个新UUID任务。

- Case check与事件rerun真实保存后，status_url读到对应原任务、意图、accepted状态及空尝试/结果。
- 同key同内容重复POST只产生原任务；换mode、换主体产生operation_conflict，原数据保持。
- 空范围、关闭、对象缺失及无效UUID/mode/多余字段/查询参数都按目标合同返回，不增加任务。
- 核心显式把一条check记为no_changes后，POST重放仍返回原accepted回执，GET为真实skipped。该skip用于验证终态重放，不证明自动无变化判断已经接通。
- 查询数据库确认2任务、2主体登记、0attempt、0Run；已有告警、事件、Case、两类成员关系及人工任务共6类记录摘要保持。记录人为配置ACTOR，source=user，不接受客户端传入身份字段。
- 503测试使用实际HTTP依赖缺任务policy，不假装数据库故障。模型、工具、Redis调用均为0。
- 主应用Case POST未注册，E37仍原同步200；主应用候选仍81操作。5项HTTP边界/内部可信检查及目标Ruff、strict通过，见[检查回执](checks.json)。

入口：`.local/conda-envs/socai2/bin/python .local/v1.2-reader-validation/run_pg.py test_socai2_analysis_submission_pg docs/operations/evidence/analysis-submit-preparation-20261114-01/pg-01.json analysis_submission_preparation`。私密连接文件不入证据；所有数据都是新合成批次，未清库或改旧批次。

[请求响应示例](examples.json)、[未注册合同OpenAPI](submission-contract.openapi.json)、[对接说明](../../../integration/analysis-submission-http.md)。测试应用挂载两个目标POST和六个已有task GET以验证请求/读回，不是主应用，也未部署到本地18024或21。通用runner中的model_and_lake标签不表示本批进行了模型调用。

尚未完成：I/Case真实handler接入、经调度执行和结果闭环、主应用启用、正式服务/Swagger同步。待调查侧给出对应验收和配置再进入下一接线步骤。本批不勾整个2.7，不部署、重启、提交或推送。
