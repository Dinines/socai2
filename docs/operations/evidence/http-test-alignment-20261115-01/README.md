# HTTP测试对齐与21运行差异

2026-11-15。本轮与「整理调查流程测试需求」协作，按负责人要求结合产品、接口及设计完善测试并处理发现的问题。执行环境以21为准，先模块单点、再接口合同、再局部集成及端到端；测试模块维护[原测试方案](../../../../openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md)，本文件只记录HTTP侧核对和问题处理，不另建测试任务树。

## 本轮实际结果

读取测试模块[21只读回执](../investigation-test-preflight-20261115-01/runtime.json)，观察时间2026-11-15 11:26:30（北京时间）。实际服务为`main-a6660267-20261114`，镜像`main-a6660267-full`，64个业务操作。对照原71操作交接合同，缺少下列7项；当前仓库候选81操作仍含这些功能。当前源码5项无鉴权/公开合同/分层检查通过，OpenAPI无security要求。详见[差异、原响应摘要与源码检查](checks-01.json)。

这证明当前部署与仓库供给不同，不能据此认定候选代码缺失这些功能。5项检查使用离线合同及ASGI替身，未调用21、数据库、模型或队列，也不代替21实际业务验证。

最终[修正核对与问题状态](fix-verification.json)保存静态/实际合同对照、文档摘要及探针复核：文档问题已修正，运行差异仍待发布；OpenSpec strict、受影响diff检查和本报告本地链接检查通过。

| 问题 | 依据及实际结果 | 处理与剩余出口 |
| --- | --- | --- |
| HTTP-T1-01 既有功能在21缺失 | 故事、探索、告警历史查询等7个操作在实际OpenAPI缺失，具体路径见下表 | 当前源码均存在且合同检查通过；21运行缺口未解决，须最终一致版本发布后逐项TCP/业务结果读回，不能只核操作总数 |
| HTTP-T1-02 无凭据业务GET返回401 | 告警/事件/Case列表及既有Case详情返回401，与内部可信目标不符 | 当前候选无鉴权检查通过，实际服务尚未切换；不新增登录、Token或角色方案，也不将健康200当作业务可用 |
| HTTP-T1-03 当前交接仍写21为旧r1/71操作 | 与本次只读观察的实际版本及操作目录矛盾 | 修正README、交接、当前进度HTTP行、部署说明及后端测试指南；历史发布回执保留，文档修正不核销运行问题 |
| HTTP-T1-04 新任务/分配依赖未发布 | 21为迁移127、28表450列，缺128/129；任务/统一Run目录/关联Case GET未挂载 | 列为候选尚未就绪，与01的既有功能缺失分开；不通过改用旧prepare/start、直写表或伪造空列表完成新流程测试 |

上述运行问题本轮均未部署修复。测试模块追加[HTTP原始回执](../investigation-test-preflight-20261115-01/http.json)确认：静态Swagger为docs19/71操作，实际API为64操作；可信配置SOCAI2_HTTP_CONTEXT_FILE未加载。完整[实际OpenAPI](../investigation-test-preflight-20261115-01/live-openapi.json)和[静态Swagger合同](../investigation-test-preflight-20261115-01/swagger-openapi.json)保留。负责人最新要求“21上版本和设计不一致，那就等发布”，因此01/02/04及Swagger差异统一记待发布阻断，本轮停止运行测试，不针对旧服务补实现或切换21。

## 7个缺失操作

路径统一加`/api/v1/socai2`。

| 方法 | 路径 | 产品功能 |
| --- | --- | --- |
| GET | /alerts/{alert_id}/review-candidates | 相似历史告警复核 |
| GET | /alerts/{alert_id}/same-host-alerts | 同主机最近告警 |
| GET | /cases/{case_id}/story | 案件故事查询 |
| GET | /cases/{case_id}/exploration-candidates | 关系图候选查询 |
| GET | /cases/{case_id}/exploration-base | 关系图底图 |
| GET | /cases/{case_id}/exploration | 恢复已保存探索 |
| PUT | /cases/{case_id}/exploration | 保存探索 |

## 测试方案供给及修复规则

用例以[125项功能](../../../../deliverables/investigation-validation-20261106/frontend-feature-list.md)、[产品数据要求](../../../integration/product-api-data-requirements-20261114.md)、[HTTP合同8.19/8.20](../../../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md)为依据，说明操作为什么存在、输入、应保存和返回什么、跳转和空态，以及哪些错误算失败。不能按当前64操作缩减需求，也不能只测200。

已同步IF07只验第6步建案首轮；Case check/rerun属于IF08/第7步。真实首轮闭环通过后才退役外部E11/E13。IF09/IF10/IF12的第8–10步后置、未实现，不作为本期第1–7步最终联验前置；第11步复用已有测试方案，核独立HTTP实际TCP与保存读取。

测试侧每个失败交付合同依据、真实请求/响应、版本/profile摘要、主体/task/Run/原件、影响和副作用状态。HTTP问题由本聊天复现修正；核心问题交调查侧。保留原失败，新回执记录修复后定向复验，未知写入先核保存，不盲目换key重试；模型正文质量NOT_PASSED单列。

已向测试侧指出两处探针问题：可信配置应读`SOCAI2_HTTP_CONTEXT_FILE`；Swagger实际入口为`/handoff/openapi.json`。健康响应正文status不得覆盖HTTP数字状态；其初版回执保留，测试侧已在http.json追加正确的numeric http_status和配置、合同复核结果。本轮不改测试侧文件，不启动服务、不清理、不投放、不调用模型、不提交推送。
