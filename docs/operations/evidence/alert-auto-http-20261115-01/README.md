# 告警自动分诊HTTP查询联验

2026-11-15，本批告警自动分诊HTTP查询联验及E36移除完成；本地候选80操作，正式两端仍71操作，未发布。

调查侧完成正常Fusion入站→首轮任务→真实A执行器→分诊保存，本聊天仅以已有HTTP查询读取同一批数据，不调用模型或新增业务数据。实施安排见[目标合同8.16](../../../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#816-告警自动分诊查询联验与事件异步入口的推进顺序)。

[准备检查](preparation-checks.json)保留实施前时点。最终直接验证如下：

- [pg-02.json](pg-02.json)：复用调查侧[正常入站/真实执行器批次](../analysis-alert-auto-20261115-01/pg-redis-05/result.json)，模型明确为受控替身。28次GET全部200且不带凭据；同一告警的材料、分诊、任务/尝试/Run来源一致，5步/13份Run原件均可读。专用租户6告警/6任务/7尝试/7Run的十类记录摘要前后不变。HTTP不重新运行核心测试或模型。
- [pg-03.json](pg-03.json)：复用调查侧[一条真实模型样本](../analysis-alert-auto-20261115-01/real-01/result.json)，28次同源读取通过。模型调用由调查侧完成，HTTP模型调用为0。
- [pg-04.json](pg-04.json)：发现该样本另有1份`run_id=null`的入站原件，因此补验告警级`source_artifacts`及正文链接。30次GET全部通过；5步、13份Run原件和1份入站原件均按SQL原值可读，十类记录前后不变。没有补采样或修改原答。
- E36手动告警分析路由及外部适配器的A执行分支已删除；内部`StageResultService.execute_alert`与A执行器保留。9项HTTP边界/内部可信/独立应用检查通过，旧入口404、不进入执行服务；剩余同步I入口仍保留原合同。告警公共字段与已有读侧Schema保持。
- Ruff/OpenSpec strict及[候选OpenAPI](candidate-openapi.json)通过：80操作，无security/securitySchemes；Case新POST未注册，E37仍为同步200，不冒称已完成事件异步执行。见[最终检查与源码摘要](checks.json)。

真实样本模型原答rationale为“告”、建议reason为“需”，正文不可用，**模型质量NOT_PASSED**保留；程序完成、保存正确和HTTP同源读取均不代表质量通过。未修改正文、未反复调用模型。

[pg-01.json](pg-01.json)保留第一次本机连接被沙箱阻止的失败，发生在读取前，0次HTTP请求/0次业务写入。后续获准连接本机隔离PG后只读复验通过；没有清理数据或覆盖失败。

联验入口为`services/api/tests/test_socai2_alert_auto_http_pg.py`，使用显式`SOCAI2_ALERT_HTTP_SAMPLE_FILE`指定已结束样本的`tenant_id/actor_id/alert_id/task_id/run_id/source_evidence`；复用本机私密PG runner连接隔离库。样本文件及回执保留真实非私密身份，不含连接凭据。

上述请求使用ASGI实际路由和真实隔离PG，服务依赖显式绑定该PG会话，业务上下文指定样本租户/测试记录人。这不是已部署18024/21的TCP验收，也不是调度吞吐、生产消费或模型质量测试。

本步未发布服务、未提交或推送。事件E37仍同步；两个未来异步提交入口尚未激活，须等调查侧事件/Case真实执行器。后端说明见[告警查询指南](../../../integration/alert-auto-http.md)，整个change及2.7仍未完成。
