# 第7步HTTP受理与比较读取

2026-11-15，按[HTTP合同8.21](../../../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#821-第7步case持续更新与上一轮比较http对齐和验收安排)及[核心第7步设计](../../../../openspec/changes/schedule-streaming-investigation-updates/stage7-case-updates-design-20261115.md)推进。**Case investigations已挂载；三任务已实际顺序消费并完成HTTP读回，周期更新边界只读通过。** 本批20次受理、28次7A只读、41次三任务终态读取/原key回放、47次7B只读均通过，共136次请求；新增实际执行由核心完成，4次模型替身、0真实模型。无部署或Git操作。21/T1仍awaiting_release。

## 受理与真实读取

- [mount-02.json](mount-02.json)：15项受理、可信、分层及旧入口检查通过。首次[mount-01.json](mount-01.json)14通过/1失败仅为测试比较了不同路由生成的422 Schema标题；仅排除标题元数据后核其他合同相同，原失败保留。
- [core-read-pg-02.json](core-read-pg-02.json)：复用核心[7A结束样本](../case-updates-20261115-01/read-7a-01/result.json)，28次无鉴权GET，覆盖8任务、3次no_changes无Run、5轮Run/Result及冻结输入、历史、故事。初始/可比/前轮失败不可比均与保存原件相同；最后一轮指向实际失败前轮，不退回更早成功结果。返回的前轮链接均实际读取，19类记录摘要前后一致，0写入/执行/模型。
- 真实读取发现并修复HTTP错误：E12/E14新增比较链接把核心RunView/ResultView当字典调用`.get()`，导致AttributeError。现按实际结构化对象访问comparison_context及其ID，8个直接场景也改用核心返回对象，通过回归。[core-read-pg-01.json](core-read-pg-01.json)保留原失败，没有重派已结束任务或重写原结果。
- [admission-pg-01.json](admission-pg-01.json)：使用核心[独占来源](../case-updates-20261115-01/http-source-01/result.json)和显式本批verification配置，20请求（15 POST/5 GET）通过。新建1Case、2成员，保存initial/check/rerun三个任务；同key回放返回原任务，换mode/主体409、不存在404、额外参数422，旧prepare/start404。非法请求前后19类记录不变，来源告警原件未改。
- [mounted-openapi.json](mounted-openapi.json)：当前源码实际80个业务操作，无security要求。保留受理阶段时点；消费联验后已生成下述候选包。
- 修复后[direct-final-01.json](direct-final-01.json)合并23项直接检查通过；目标Ruff、OpenSpec strict及566个文档本地链接通过。[阶段回执](admission-readback-summary.json)记录代码摘要、实际数据库调用范围及未验边界。

新案`32ddf37a-6f0c-5571-b22c-40eef480a37f`：initial任务`00caca92-db29-4621-a756-59b91d726746`、check任务`131d7607-99c7-4952-907d-25ed17d50b39`、rerun任务`797431d8-cbac-4cb3-aee3-a927f052c1a1`。受理时均accepted、无Run；现已按initial→check→rerun消费：initial completed、check skipped/no_changes且无attempt/Run、rerun completed，共2Run/2Result，固定请求及key见[sample.json](sample.json)。下方终态回执取代此前“尚未消费”的状态，原受理回执不改写。

本轮真实数据库为独立开发`v12_upgrade_dev`，HTTP使用实际应用和适配器的ASGI调用，显式覆盖隔离会话和配置身份；不是部署后的TCP验收。核心7A来源使用8次模型替身、0真实模型，本HTTP批新增模型调用为0。关闭/空范围错误本轮使用核心错误替身验证映射，真实错误供给复用既有受理证据，尚未把本轮新案改为这些状态。

## 三任务执行与周期读取完成

- 核心[http-consume-01.json](../case-updates-20261115-01/http-consume-01.json)记录唯一一次顺序消费：首轮Run `b115dfd7-12a3-4fc7-8925-e5b5eb64accb`，再次调查Run `7d93face-9616-4efe-9ef9-9a459ecd8789`；4次模型替身、0真实模型，消费者已退出。
- [execution-read-pg-03.json](execution-read-pg-03.json)：41请求（38 GET/3 POST）通过。实际任务终态、Run/Result、冻结成员/比较、完整步骤与工件目录、输入/策略/模型原件及当前判断与SQL一致。再次调查链接进入实际首轮；完成/跳过后回放建案和两个原key，回执保持accepted，GET仍为真实终态，未新增任务或执行，21类记录摘要不变。
- [execution-read-pg-01.json](execution-read-pg-01.json)、[execution-read-pg-02.json](execution-read-pg-02.json)保留两次测试断言错误：第一次把Run每次读取的observed_at当固定值，第二次误要求Result也有该字段。改为仅允许Run读取时间推进、其余字段仍全比对后通过，未改业务返回或重复执行任务。
- [periodic-read-pg-01.json](periodic-read-pg-01.json)：复用核心[7B](../case-updates-20261115-01/read-7b-03/result.json)和[生命周期](../case-updates-20261115-01/lifecycle-02/result.json)已结束样本，47 GET通过，3案10个Case Run；任务来源、冻结成员/原输入、结果/前轮关系、唯一事件接收Case及关闭后自动资格与保存一致。两批各23类记录摘要不变；HTTP未模拟时间、扫描、写入或消费。超期扫描时钟测试属于核心证据，不冒充HTTP在当前时间观察到超期。
- [candidate-openapi.json](candidate-openapi.json)与[三类Swagger包](swagger/manifest.json)：80操作、无security，按告警/事件/调查集中展示；保存实际check/rerun请求、202回执、终态及比较示例。文档仅增展示说明和示例，参数、请求/响应Schema与实际源码一致。[examples.json](examples.json)供离线查阅，不在21重放这些隔离ID。
- [HTTP发布片段](../../../../deploy/http-service/case-update-release-fragment.json)依赖同版核心analysis-case片段；无新DDL，继续依赖128/129，显式业务上下文/任务/分配/读取配置，HTTP不启动调度器。
- 新案从已保存快照导出至[saved-export](saved-export/plan.json)，用update_processing_audit.py加入仓库归档页，原24案保持、现25案；实际4177服务未切换。

本步程序和持久读取验证通过；当前没有新发现的业务bug。前轮结构化对象访问错误已修复并保留原证据。真实模型正文质量、候选独立TCP、21资源/profile准备、整change结束审计及正式发布不在这些开发回执中冒称通过；第8–10步继续后置。本期功能用例及未验边界交给测试模块既有方案。

## 较早准备记录

下列记录为挂载/真实读回前的准备阶段，原回执不改写。

E12/E14在响应顶层补previous_run_url、comparison_result_url。身份只取本Run/Result冻结的comparison_context，不查最新历史、不以当前采用结果替代上一实际调查。shared Case View保持核心四字段，A/I/通用task DTO不变。状态与空值详见[接口指南](../../../integration/run-records-http.md)。

- 8个核心读取替身场景、16次ASGI GET：历史context=null、新首轮initial、eligible，以及5种unavailable原因。核原字段与正文保持、链接属于当前Case、不可比时保留上一Run入口、空ID不伪造链接；HTTP不修改核心返回对象。
- 6项既有可信/合同/分层/旧入口检查：无鉴权，比较增量只进入Case响应，告警和事件合同保持；E11/E13及Case investigations仍404，内部核心准备/执行能力仍在。
- 合并复验[preparation-02.json](preparation-02.json)：14 passed；[preparation-01.json](preparation-01.json)保留首次8通过及边界检查5通过/1失败。失败是测试错误要求OpenAPI显式提供default:null；实际字段为可空且非必填，文档导出省略该元数据。修正检查，不改业务合同或历史失败。

初次准备复用第6步已结束回执的JSON形状作为替身；这不足以证明核心实际返回对象能被正确处理，后续真实读回已发现并修正上述错误。7B边界只读复用，不重建故障矩阵；第7步全部通过后才生成最终Swagger/发布片段及IF08开发供给回执，最终TCP测试按既有方案进行。
