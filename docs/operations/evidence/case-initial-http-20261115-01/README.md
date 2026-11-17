# Case首轮HTTP联验（第6步）

2026-11-15，按[HTTP安排8.19](../../../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#819-第6步case首轮执行http配合与切换安排)及[核心设计](../../../../openspec/changes/schedule-streaming-investigation-updates/stage6-case-execution-design-20261115.md)完成本步，待统一发布。当前候选79操作，无鉴权；Case check/rerun、周期更新及整个change未完成，不部署或推送。

## 业务验证

| 输入与操作 | 实际保存和读回 | 证据 |
| --- | --- | --- |
| 独占2条来源告警，经E01创建Case | 1 Case和1 initial accepted；受理时无attempt/Run，原来源材料不改 | [sample](sample.json)、[创建4请求](create-pg-01.json) |
| 唯一调度器消费该tenant一次 | 实际Case执行器/C1–C6，2次模型替身，0真模型；task/attempt/Run completed，队列drained | [consume](consume-01.json) |
| 沿task→Run→Result→当前判断→完整步骤/工件/正文读取 | 18 GET通过；同一来源及范围，原文/hash一致；19类记录摘要前后相同 | [正常读取](read-pg-02.json)、[SQL快照](snapshot.json) |
| 只读复用核心5个已结束Case：容量、后续Case、查询失败、缺时、成员时序 | 17 GET通过；容量failed/capacity_exceeded及输入原件保留；当前3成员与Run冻结2成员如实区分；其余任务/Run/Result与核心读回一致 | [边界读取](boundary-pg-04.json)、[核心来源](../case-initial-20261115-01/readback-02/result.json) |
| 删除对外E11/E13；检查真实HTTP边界 | 6项定向测试通过；两个旧POST404、无外部端口/DTO导出，核心内部原语仍在，Case investigations仍404；无鉴权，核心不依赖HTTP | [检查摘要](checks.json)、[79操作OpenAPI](candidate-openapi.json) |

成功验收共**39请求＝1 POST＋38 GET**。只读复用的5案此前由核心完成10次模型替身，本HTTP步骤未重派或新增调用。独占tenant唯一task completed、attempt ended/completed，无在途任务；已通知核心可停止专用Redis并保留数据。21/T1预检状态不因本批变化。

HTTP代码仅撤下已确认退役入口；已有读取器通过数据核对，本轮没有复现需修改的新增业务读取缺陷。查询时间、容量收尾等核心修复由调查模块独立记录在其[第6步回执](../case-initial-20261115-01/README.md)。

## 保留的失败及修正

| 原回执 | 原因、修正与复验 |
| --- | --- |
| [read-pg-01](read-pg-01.json) | 6 GET后测试错误要求current_assessment为空。核对实际首轮自动采用和SQL来源，改为逐字段核判断/来源/覆盖；read-pg-02通过。 |
| [boundary-pg-01](boundary-pg-01.json) | 测试未显式选择任务policy，第一请求依赖构造失败；补SOCAI2_ANALYSIS_TASKS_CONFIG_FILE，不修改服务默认行为。 |
| [boundary-pg-02](boundary-pg-02.json) | 第4请求把Run输入工件当作Case独立证据读取，真实404；改用合同中的含run_id路径。 |
| [boundary-pg-03](boundary-pg-03.json) | 第4请求已200，但测试直接比较核心JSON的时间字符串与HTTP ISO时间字符串；按同一时刻核对，正文/hash保持严格比较。boundary-pg-04通过。 |

这些均是测试配置/预期/请求/比较修正，不能列为已修复的业务服务bug。失败回执未覆盖，未重新建案或消费；额外14次已返回HTTP响应及1次依赖构造失败单独记录，不混入39次成功验收计数。

## 证据边界与复用

真实隔离PG `v12_upgrade_dev`、专用Redis、实际Case执行器与HTTP ASGI适配；模型/湖/背景为受控替身。未验证真实模型正文质量、部署后的TCP服务及21新版本，不能写成端到端验收或改变NOT_PASSED。发布前后测试沿[测试模块方案](../../../../openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md)，先模块单点再集成；21与设计不一致时等待发布。

[examples](examples.json)取自本批真实接口回执，仅适用于本隔离数据；不得把这些UUID用于21。[对接指南](../../../integration/case-initial-http.md)给出输入、输出、错误、查询顺序与未实现边界。[checks](checks.json)保存源文件摘要、调用数及无鉴权/接口检查结果。[Swagger候选包](swagger/manifest.json)按告警/事件/调查三组展示，只有说明和示例扩展，业务合同与原始79操作一致，可按[Docker说明](../../../../deploy/api-docs/README.md)单独预览。旧批OpenAPI和失败保持原字节。
