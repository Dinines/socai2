# 任务结果引用合同补齐

2026-11-14。HTTP侧实施task GET时发现第1步核心读取的results把容器类型放入kind，并且没有结果自身kind，无法准确构造已确认[合同8.1](../../../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#81-通用类型任务身份和分页)的ResultRef。此处补齐原定合同，不增加兼容别名或新业务规则。

`AnalysisTaskService.read_task/list_tasks`的每条results现在统一提供`result_type/id/source_run_id/kind`，URL仍由独立HTTP生成：Case读取Results.kind；告警读取AlertAssessments.kind且只选triage，排除human_feedback；事件表只有诊断一种结果类型，kind固定为incident_diagnosis。没有改告警原表/原公共字段、数据库、执行或调度。

[pg-01](pg-01.json)为新UUID、真实本机隔离PG批次，13项通过。新增三类结果的实际保存/详情读回及列表核对，告警同Run另存一条human_feedback作为排除对照；精确断言四字段，无旧result_id/run_id别名。读取前后摘要覆盖任务、尝试、主体状态和三类结果表，内容一致；既有生命周期和采用检查继续通过。没有模型/工具/Redis/正式服务调用，未清数据或重派旧Run。

本轮代码仅改[任务核心读取](../../../../services/api/app/socai2/analysis_tasks.py)和[已有定向PG用例](../../../../services/api/tests/test_socai2_analysis_tasks_pg.py)。Ruff、OpenSpec strict及限定文档链接检查通过；未修改HTTP侧文件。原[第1步pg-05](../analysis-lifecycle-20261114-01/pg-05.json)保留其范围，不能用当时空results用例冒充已验证本次类型合同。

已向HTTP对接方交付真实四字段和本批回执；其负责URL及公共路由验收。此回执不声明task GET已发布，不改变流式1/11、主调查31/41或模型NOT_PASSED，未部署或提交Git。
