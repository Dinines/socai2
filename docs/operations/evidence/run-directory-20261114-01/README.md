# R1统一调查目录：基础读取验收

2026-11-14。负责人授权继续实现，并将本聊天范围限定为后端接口。实施前已与调查侧确认：目标task/attempt数据尚未提供，调查侧随后开始第1步核心实现；本聊天不修改其ORM、迁移、调度或模型。落点见[HTTP合同8.11](../../../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#811-r1已有数据读取本轮实施边界)，状态见[接口说明](../../../integration/run-directory-http.md)。

## 实际完成

- 专用核心只读用例RunDirectoryService.read、查询合同、HTTP公开DTO及URL适配。按主体/类型/状态/时间筛选，稳定游标分页；总数、状态、交付及真实Case关系统计与本页同一只读快照。
- 真实A/I/Case结果分开引用，失败/unknown/无结果Run保留；Case多结果版本、显式和共享Case关系不重复计数。输入数量取冻结数据，不读当前成员替代。
- 任务关联不伪填，完整公开DTO拒绝缺task_id/intent的基础结果；intent查询暂为依赖未就绪。没有新增HTTP路由，候选仍74操作；正式两端及静态Swagger仍71操作。

## 直接证据

[pg-04.json](pg-04.json)为最终批次：本机127.0.0.1:28412、v12_upgrade_dev、真实PG、新UUID合成数据。共8个Run，筛选窗内7个，窗外边界1个；9次成功基础读取，并核非法游标/参数及未接intent。7个Run稳定分3页；3个Case经多条关系仍只计3个，2个无Case Run保留。同Run的2个Case结果版本不放大Run数量。明确空输入为0，缺输入为null，冻结1条而当前2条仍报1。

9次ASGI GET实际打开返回的已有Run/结果URL并核身份；这是现有接口读回，新R1没有挂载。12类本批记录在读取前后行数和完整行SHA256一致。无模型/工具调用、无数据库迁移、无生产业务写入、无服务重启或Git提交推送。

早期记录保留：[pg-01](pg-01.json)合成baseline误用固定scope_revision，触发真实领取保护并回滚，改为读取实际版本；[pg-02](pg-02.json)基础读取通过；[pg-03](pg-03.json)追加打开链接时，合成Case结果的case_impact缺既定正文结构，被原ResultView拒绝，改为按现有合同准备测试数据。没有改业务保护、覆盖旧结果或改写失败为成功。

测试为[run_directory PG用例](../../../../services/api/tests/test_socai2_run_directory_pg.py)，复用现有隔离PG runner。另核3项HTTP边界、2项可信接入、Ruff和OpenSpec strict；合同结构、未挂载状态及源码摘要保存于本目录direct-checks.json。公开输入输出Schema单独保存在contract-schemas.json，不混入已发布Swagger。

## 剩余依赖

调查侧负责analysis_tasks/attempts及真实读取。它交付后，接口侧把真实关联与intent过滤接入同一数据库快照，补读取验收，再启用完整GET /analysis-runs。当前仅R1基础读取局部完成，不勾任务2.7，不冒称R1完整接口或整个change完成。发布/最终审计等交付项保持原边界。
